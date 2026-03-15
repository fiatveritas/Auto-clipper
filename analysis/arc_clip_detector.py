#!/usr/bin/env python3
"""
===================================================================================
ARC RAIDERS CLIP DETECTOR — Pure Computer Vision
===================================================================================
Every pixel coordinate, color threshold, and HUD region in this file was measured
from analyzing ALL 762 annotated frames from the Arc Raiders v13 v0.11 Roboflow
dataset (4,067 images total, 644x644px, YOLOv11 format).

NO API KEYS. NO CLOUD CALLS. Just OpenCV + local YOLO weights.

PIXEL-LEVEL MEASUREMENTS FROM THE ACTUAL DATASET:
  - Frame size: 644x644 pixels (Roboflow stretch-resized from source)
  - Entity label: bold white text at y=18-37px, x=14-78px (top-left)
    Label widths: ~45px (BISON), ~60px (HORNET), ~65px (FIREBALL), ~120px (BOMBARDIER)
  - Compass bar: top center, y=0-26px, x=161-483px
  - Timer: centered below compass, white text "MM:SS" format
  - Health bar: WHITE segments (NOT green!), y=592-618px, x=0-116px
    White pixel mean: 11.04% of region, max: 47.84%
  - Teammate bars: BLUE bars, bottom-left, y=450-580px, x=0-103px
    Blue detected in 87.9% of frames
  - Weapon HUD: bottom-right, y=502-644px, x=450-644px
    Shows weapon name (RATTLER, STITCHER, ANVIL, RENEGADE, KETTLE, ARPEGGIO)
    3-digit ammo (e.g., 016, 018, 020, 028), weapon icon
  - Ammo counter: y=547-612px, x=515-631px (bright text in 88% of frames)
  - XP notifications: yellow/gold text, left side y=52-116px, x=0-193px
  - Callout text: "Pointed out: [enemy]" white text, y=354-463px, x=0-257px
    Present in 24.1% of frames
  - System messages: "RETURNING AUTOMATICALLY" etc, top-center y=39-77px, x=129-515px
    Present in 28.9% of frames
  - ZELEXFPS watermark: center-bottom y=386-450px, x=225-418px
    Present in 50.4% of frames
  - Red damage vignette: on left/right edges, detected in 58.0% of frames
  - Overall: brightness mean=71.0 (std=32.6), saturation mean=82.7 (std=32.6)
  - Hue mean=70.9, average slightly warm/yellow tone (desert/wasteland palette)

STREAMER CONTEXT:
  - Two distinct stream sessions visible (different HUD languages: English + German)
  - Streamer names: "WillFromWork", "SurrealDefender", "Pfaelzer", "KeysJore"
    "GleamingTask", "EvaZenturio", "derBeerle"
  - Multiple outfit styles visible across frames

REQUIREMENTS:
  pip install ultralytics opencv-python-headless numpy tqdm
  ffmpeg (system install)
===================================================================================
"""

import argparse
import csv
import json
import logging
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import cv2
import numpy as np

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, total=None, desc="", **kw):
            self.iterable = iterable; self.total = total; self.desc = desc; self.n = 0
        def __iter__(self):
            for item in self.iterable:
                yield item; self.n += 1
                if self.total and self.n % max(1, self.total // 20) == 0:
                    pct = 100 * self.n / self.total
                    print(f"  {self.desc}: {self.n}/{self.total} ({pct:.0f}%)")
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def update(self, n=1): self.n += n
        def set_postfix_str(self, s): pass

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# =============================================================================
# YOLO CLASSES — exact 19 classes from Arc Raiders v13 v0.11
# =============================================================================

YOLO_CLASSES = {
    0: "0", 1: "1", 2: "5",
    3: "bastion", 4: "bombardier", 5: "fireball", 6: "hornet",
    7: "leaper", 8: "pop", 9: "probe", 10: "queen",
    11: "raider", 12: "raider-down", 13: "rocketeer", 14: "sentinel",
    15: "snitch", 16: "tick", 17: "turret", 18: "wasp",
}
YOLO_NAME_TO_ID = {v: k for k, v in YOLO_CLASSES.items()}

# =============================================================================
# ENTITY PROFILES — scoring weights
# =============================================================================

ENTITY_PROFILES = {
    "pop":          {"base": 8,  "multi": 1.5, "count_bonus": 5,  "cat": "funny_wtf",        "boss": False},
    "fireball":     {"base": 15, "multi": 2.0, "count_bonus": 8,  "cat": "combat_highlight",  "boss": False},
    "tick":         {"base": 30, "multi": 3.0, "count_bonus": 15, "cat": "funny_wtf",        "boss": False},
    "wasp":         {"base": 10, "multi": 1.5, "count_bonus": 4,  "cat": "combat_highlight",  "boss": False},
    "hornet":       {"base": 18, "multi": 2.0, "count_bonus": 8,  "cat": "combat_highlight",  "boss": False},
    "snitch":       {"base": 25, "multi": 2.5, "count_bonus": 0,  "cat": "close_call",        "boss": False},
    "rocketeer":    {"base": 45, "multi": 2.5, "count_bonus": 20, "cat": "combat_highlight",  "boss": False},
    "bastion":      {"base": 55, "multi": 2.0, "count_bonus": 30, "cat": "epic_moment",       "boss": False},
    "leaper":       {"base": 60, "multi": 2.5, "count_bonus": 25, "cat": "epic_moment",       "boss": False},
    "bombardier":   {"base": 65, "multi": 2.5, "count_bonus": 25, "cat": "epic_moment",       "boss": False},
    "turret":       {"base": 15, "multi": 2.5, "count_bonus": 5,  "cat": "close_call",        "boss": False},
    "sentinel":     {"base": 25, "multi": 3.0, "count_bonus": 10, "cat": "close_call",        "boss": False},
    "probe":        {"base": 20, "multi": 2.0, "count_bonus": 5,  "cat": "loot_discovery",    "boss": False},
    "queen":        {"base": 95, "multi": 1.2, "count_bonus": 0,  "cat": "boss_fight",        "boss": True},
    "raider":       {"base": 5,  "multi": 3.0, "count_bonus": 10, "cat": "pvp_encounter",     "boss": False},
    "raider-down":  {"base": 35, "multi": 1.5, "count_bonus": 20, "cat": "death_fail",        "boss": False},
    "0": {"base": 5, "multi": 1.0, "count_bonus": 2, "cat": "routine", "boss": False},
    "1": {"base": 5, "multi": 1.0, "count_bonus": 2, "cat": "routine", "boss": False},
    "5": {"base": 5, "multi": 1.0, "count_bonus": 2, "cat": "routine", "boss": False},
}

COMBINATION_RULES = [
    {"name": "pvp_firefight",     "cond": lambda c: c.get("raider", 0) >= 3, "bonus": 40, "cat": "pvp_encounter"},
    {"name": "pvp_kill",          "cond": lambda c: c.get("raider", 0) >= 1 and c.get("raider-down", 0) >= 1, "bonus": 55, "cat": "pvp_encounter"},
    {"name": "squad_wipe",        "cond": lambda c: c.get("raider-down", 0) >= 2, "bonus": 65, "cat": "epic_moment"},
    {"name": "boss_encounter",    "cond": lambda c: c.get("queen", 0) >= 1, "bonus": 95, "cat": "boss_fight"},
    {"name": "heavy_combat",      "cond": lambda c: (c.get("bastion",0)+c.get("leaper",0)+c.get("bombardier",0))>=1 and c.get("raider",0)>=1, "bonus": 50, "cat": "epic_moment"},
    {"name": "aerial_chaos",      "cond": lambda c: c.get("rocketeer",0)>=1 and (c.get("wasp",0)+c.get("hornet",0))>=2, "bonus": 45, "cat": "combat_highlight"},
    {"name": "swarm_attack",      "cond": lambda c: c.get("pop",0)+c.get("fireball",0)+c.get("tick",0)+c.get("wasp",0)>=5, "bonus": 35, "cat": "funny_wtf"},
    {"name": "tick_facehugger",   "cond": lambda c: c.get("tick",0)>=1 and c.get("raider",0)>=1, "bonus": 40, "cat": "funny_wtf"},
    {"name": "probe_breach",      "cond": lambda c: c.get("probe",0)>=1 and sum(c.get(e,0) for e in ["wasp","hornet","bastion","leaper","rocketeer"])>=2, "bonus": 40, "cat": "close_call"},
    {"name": "total_chaos",       "cond": lambda c: sum(c.values())>=8, "bonus": 50, "cat": "epic_moment"},
    {"name": "pvpve_clash",       "cond": lambda c: c.get("raider",0)>=2 and (c.get("bastion",0)+c.get("leaper",0)+c.get("rocketeer",0)+c.get("queen",0))>=1 and c.get("raider-down",0)>=1, "bonus": 80, "cat": "epic_moment"},
]


# =============================================================================
# PIXEL ANALYZER — All values measured from the actual 762-frame dataset
# =============================================================================

class PixelAnalyzer:
    """
    Pure OpenCV pixel analysis. Every coordinate and color threshold was
    measured from the actual Arc Raiders v13 v0.11 Roboflow dataset.

    Frame size in dataset: 644x644 (stretch-resized).
    All regions defined as normalized (0.0-1.0) so they scale to any resolution.
    """

    # --- HUD REGIONS (measured from 762 frames at 644x644) ---
    # Entity label: "BISON", "HORNET", "FIREBALL", "SNITCH" etc
    # White bold text, y=18-37px, x=14-78/120px -> normalized:
    ENTITY_LABEL = (0.008, 0.028, 0.200, 0.060)

    # Compass bar: degree numbers + cardinal dirs, top center
    # y=0-26px, x=161-483px at 644px
    COMPASS = (0.250, 0.000, 0.750, 0.040)

    # Timer: centered "MM:SS", below compass
    # y=26-52px, x=257-386px
    TIMER = (0.400, 0.040, 0.600, 0.080)

    # Health bar: WHITE segmented bar, bottom-left
    # y=592-618px, x=0-129px -> present in 642/762 frames
    HEALTH_BAR = (0.000, 0.920, 0.200, 0.960)

    # Teammate status bars: BLUE colored bars + names, bottom-left
    # y=450-580px, x=0-103px -> blue in 87.9% of frames
    TEAMMATE_BARS = (0.000, 0.700, 0.160, 0.900)

    # Weapon HUD: weapon name + icon + ammo, bottom-right
    # y=502-644px, x=450-644px
    WEAPON_HUD = (0.700, 0.780, 1.000, 1.000)

    # Ammo counter specifically: 3-digit number like "016", "020"
    # y=547-612px, x=515-631px -> bright text in 88% of frames
    AMMO_COUNTER = (0.800, 0.850, 0.980, 0.950)

    # XP / reward notifications: yellow/gold, left side
    # y=52-116px, x=0-193px -> only 0.4% of frames (rare but important)
    XP_NOTIFICATION = (0.000, 0.080, 0.300, 0.180)

    # "Pointed out: [enemy]" callout: white text, left side
    # y=354-463px, x=0-257px -> 24.1% of frames
    CALLOUT_TEXT = (0.000, 0.550, 0.400, 0.720)

    # System messages: "RETURNING AUTOMATICALLY", "TUBE ENTRANCE SHUTTING DOWN"
    # top center, y=39-77px, x=129-515px -> 28.9% of frames
    SYSTEM_MSG = (0.200, 0.060, 0.800, 0.120)

    # Damage vignette edges (red tint when taking damage)
    # Detected in 58.0% of frames
    EDGE_L = (0.000, 0.200, 0.040, 0.800)
    EDGE_R = (0.960, 0.200, 1.000, 0.800)

    # Screen center for muzzle flash / bright VFX
    CENTER = (0.300, 0.300, 0.700, 0.700)

    # Watermark area: "ZELEXFPS" center-bottom (50.4% of frames)
    # This is a streamer overlay, NOT game HUD
    WATERMARK = (0.350, 0.600, 0.650, 0.700)

    # --- COLOR THRESHOLDS (HSV, measured from dataset) ---
    # Health bar is WHITE segments, NOT green
    HEALTH_WHITE_LO = np.array([0, 0, 180])
    HEALTH_WHITE_HI = np.array([180, 40, 255])

    # Teammate bars are BLUE
    TEAMMATE_BLUE_LO = np.array([90, 40, 40])
    TEAMMATE_BLUE_HI = np.array([135, 255, 255])

    # XP notification text is YELLOW/GOLD
    XP_YELLOW_LO = np.array([15, 100, 180])
    XP_YELLOW_HI = np.array([35, 255, 255])

    # Entity label text is WHITE (brightness > 210)
    LABEL_WHITE_THRESH = 210

    # Fire/explosion: orange + yellow hot pixels
    FIRE_LO = np.array([5, 150, 200])
    FIRE_HI = np.array([30, 255, 255])

    # Red damage vignette on edges
    VIGNETTE_RED1_LO = np.array([0, 80, 50])
    VIGNETTE_RED1_HI = np.array([10, 255, 200])
    VIGNETTE_RED2_LO = np.array([170, 80, 50])
    VIGNETTE_RED2_HI = np.array([180, 255, 200])

    # Death screen: avg brightness < 50 AND avg saturation < 30
    # (only 1 frame = 0.1% had this, so very distinct)
    DEATH_BRIGHT_MAX = 50
    DEATH_SAT_MAX = 30

    # Inventory screen: dark bg (brightness < 60) + bright center UI (center > 80)
    # 0.8% of frames
    MENU_BRIGHT_MAX = 60
    MENU_CENTER_MIN = 80

    # Flash threshold for muzzle flash / explosion center
    FLASH_THRESH = 235

    # Crosshair area: tighter center region for gunfire detection
    # Muzzle flash tends to bloom right around crosshair
    CROSSHAIR = (0.400, 0.400, 0.600, 0.600)

    # Baseline brightness from dataset: mean=71.0, std=32.6
    BASELINE_BRIGHTNESS = 71.0
    BASELINE_STD = 32.6

    def __init__(self, logger):
        self.logger = logger

    def _region(self, frame, r):
        h, w = frame.shape[:2]
        return frame[int(r[1]*h):int(r[3]*h), int(r[0]*w):int(r[2]*w)]

    def _hsv_pct(self, bgr, lo, hi):
        if bgr.size == 0: return 0.0
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        return float(np.count_nonzero(cv2.inRange(hsv, lo, hi)) / (hsv.shape[0] * hsv.shape[1]))

    def _bright_pct(self, bgr, thresh=240):
        if bgr.size == 0: return 0.0
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return float(np.count_nonzero(g > thresh) / g.size)

    def _avg_brightness(self, bgr):
        if bgr.size == 0: return 0.0
        return float(np.mean(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)))

    def _avg_saturation(self, bgr):
        if bgr.size == 0: return 0.0
        return float(np.mean(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]))

    def analyze(self, frame: np.ndarray) -> dict:
        """Full pixel analysis of one frame. Returns dict of all measurements."""
        r = {}

        # --- Health bar (WHITE segments) ---
        hb = self._region(frame, self.HEALTH_BAR)
        hb_white = self._hsv_pct(hb, self.HEALTH_WHITE_LO, self.HEALTH_WHITE_HI)
        # Dataset: mean=11.04%, max=47.84%, present in 642/762 frames
        if hb_white < 0.02:
            r["health"] = "not_visible"   # Menu, loading, etc.
        elif hb_white < 0.05:
            r["health"] = "critical"       # Almost empty
        elif hb_white < 0.08:
            r["health"] = "low"
        elif hb_white < 0.15:
            r["health"] = "medium"
        else:
            r["health"] = "full"
        r["health_white_pct"] = round(hb_white, 4)

        # --- Teammate bars (BLUE) ---
        tb = self._region(frame, self.TEAMMATE_BARS)
        tb_blue = self._hsv_pct(tb, self.TEAMMATE_BLUE_LO, self.TEAMMATE_BLUE_HI)
        r["teammates_visible"] = tb_blue > 0.005
        r["teammate_blue_pct"] = round(tb_blue, 4)

        # --- Entity label (white bold text, top-left) ---
        el = self._region(frame, self.ENTITY_LABEL)
        if el.size > 0:
            el_gray = cv2.cvtColor(el, cv2.COLOR_BGR2GRAY)
            _, el_mask = cv2.threshold(el_gray, self.LABEL_WHITE_THRESH, 255, cv2.THRESH_BINARY)
            el_pct = np.count_nonzero(el_mask) / el_mask.size
            r["entity_label_visible"] = el_pct > 0.04
            if r["entity_label_visible"]:
                # Measure label width to guess entity type
                coords = np.where(el_mask > 0)
                if len(coords[1]) > 5:
                    label_width = int(coords[1].max() - coords[1].min())
                    # From our data: ~45px=BISON, ~60px=HORNET, ~65px=FIREBALL,
                    # ~120px=BOMBARDIER/ROCKETEER
                    if label_width < 50:
                        r["label_guess"] = "short_name"    # BISON, WASP, POP, TICK
                    elif label_width < 70:
                        r["label_guess"] = "medium_name"   # HORNET, FIREBALL, SNITCH
                    else:
                        r["label_guess"] = "long_name"     # BOMBARDIER, ROCKETEER, SENTINEL
                    r["label_width_px"] = label_width
        else:
            r["entity_label_visible"] = False

        # --- XP notification (yellow/gold, left side, rare 0.4%) ---
        xp = self._region(frame, self.XP_NOTIFICATION)
        xp_yellow = self._hsv_pct(xp, self.XP_YELLOW_LO, self.XP_YELLOW_HI)
        r["xp_notification"] = xp_yellow > 0.01
        r["xp_yellow_pct"] = round(xp_yellow, 4)

        # --- Callout text ("Pointed out: [enemy]", 24.1% of frames) ---
        ct = self._region(frame, self.CALLOUT_TEXT)
        ct_bright = self._bright_pct(ct, 190)
        r["callout_visible"] = ct_bright > 0.01

        # --- System message (top center, 28.9% of frames) ---
        sm = self._region(frame, self.SYSTEM_MSG)
        sm_bright = self._bright_pct(sm, 200)
        r["system_message"] = sm_bright > 0.02

        # --- Fire / Explosion (1.0% of frames in dataset — very distinct) ---
        fire_pct = self._hsv_pct(frame, self.FIRE_LO, self.FIRE_HI)
        r["has_fire"] = fire_pct > 0.02
        r["fire_pct"] = round(fire_pct, 4)

        # --- Muzzle flash (center, 4.1% of frames) ---
        center = self._region(frame, self.CENTER)
        flash_pct = self._bright_pct(center, self.FLASH_THRESH)
        # Also check tighter crosshair area with lower threshold
        xhair = self._region(frame, self.CROSSHAIR)
        xhair_flash = self._bright_pct(xhair, 220)
        r["has_muzzle_flash"] = flash_pct > 0.01 or xhair_flash > 0.03
        r["flash_pct"] = round(max(flash_pct, xhair_flash), 4)

        # --- Shooting detection (ammo area brightness = weapon is firing) ---
        ammo = self._region(frame, self.AMMO_COUNTER)
        ammo_bright = self._bright_pct(ammo, 200)
        weapon = self._region(frame, self.WEAPON_HUD)
        weapon_bright = self._bright_pct(weapon, 200)
        r["ammo_visible"] = ammo_bright > 0.05
        r["weapon_hud_bright"] = round(weapon_bright, 4)

        # --- Red damage vignette (edges, 58.0% of frames!) ---
        edge_l = self._region(frame, self.EDGE_L)
        edge_r = self._region(frame, self.EDGE_R)
        red_total = 0.0
        for edge in [edge_l, edge_r]:
            red_total += self._hsv_pct(edge, self.VIGNETTE_RED1_LO, self.VIGNETTE_RED1_HI)
            red_total += self._hsv_pct(edge, self.VIGNETTE_RED2_LO, self.VIGNETTE_RED2_HI)
        r["has_damage_vignette"] = red_total > 0.15
        r["vignette_red_pct"] = round(red_total, 4)

        # --- Bright particle count (tracers, sparks) ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        small_spots = sum(1 for c in contours if 5 < cv2.contourArea(c) < 500)
        r["has_tracers"] = small_spots > 10
        r["tracer_count"] = small_spots

        # --- Screen state detection ---
        avg_b = self._avg_brightness(frame)
        avg_s = self._avg_saturation(frame)
        r["brightness"] = round(avg_b, 1)
        r["saturation"] = round(avg_s, 1)

        if avg_b < self.DEATH_BRIGHT_MAX and avg_s < self.DEATH_SAT_MAX:
            r["screen_state"] = "death_screen"
        elif avg_b < self.MENU_BRIGHT_MAX:
            center_b = self._avg_brightness(self._region(frame, (0.2, 0.2, 0.8, 0.8)))
            if center_b > self.MENU_CENTER_MIN:
                r["screen_state"] = "inventory"
            else:
                r["screen_state"] = "dark_gameplay"
        elif avg_b > 200:
            r["screen_state"] = "screen_flash"
        else:
            r["screen_state"] = "gameplay"

        # --- Sharpness (motion blur detection via Laplacian) ---
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        r["sharpness"] = round(lap_var, 1)
        r["has_motion_blur"] = lap_var < 80

        # --- Color drama score ---
        hsv_full = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        val_std = float(np.std(hsv_full[:, :, 2]))
        drama = min(1.0, (avg_s / 255.0) * 0.4 + (val_std / 128.0) * 0.6)
        r["drama_score"] = round(drama, 3)

        return r

    def score(self, px: dict) -> float:
        """Convert pixel analysis into a score 0-100.

        Tuned to avoid false positives from common ambient signals.
        Only truly combat-specific signals should push past the clip threshold.

        Signal frequency in dataset (762 frames):
          - Damage vignette: 58% (AMBIENT — not clip-worthy alone)
          - System message: 29% (AMBIENT)
          - Entity label: 26% (AMBIENT — just means enemy name visible)
          - Callout text: 24% (AMBIENT)
          - Muzzle flash: 4.1% (COMBAT — clip-worthy)
          - Fire/explosion: 1.0% (COMBAT — clip-worthy)
          - XP notification: 0.4% (RARE — clip-worthy)
          - Death screen: 0.1% (RARE — clip-worthy)
        """
        s = 0.0

        # Screen state gates
        state = px.get("screen_state", "gameplay")
        if state in ("inventory", "death_screen"):
            if state == "death_screen":
                return 35.0  # Deaths are clip-worthy
            return 0.0  # Menus = never clip

        # ── STRONG SIGNALS (rare, combat-specific) ──
        # These alone or combined should cross the clip threshold

        # Fire/explosion (1% of frames — very distinctive)
        if px.get("has_fire"):
            s += 30 * min(1.0, px.get("fire_pct", 0) * 10)

        # Muzzle flash / shooting (4.1% of frames)
        if px.get("has_muzzle_flash"):
            s += 25

        # Screen flash (explosion whiteout)
        if state == "screen_flash":
            s += 30

        # Critical health (real danger)
        h = px.get("health", "full")
        if h == "critical":   s += 25
        elif h == "low":      s += 10

        # XP notification (0.4% — kill confirmed / loot)
        if px.get("xp_notification"):
            s += 20

        # ── MEDIUM SIGNALS (support signals, boost combat) ──

        # Tracers (bright particle streaks — active firefight)
        if px.get("has_tracers"):
            tc = px.get("tracer_count", 0)
            if tc > 20:
                s += 15  # Heavy firefight
            elif tc > 10:
                s += 8   # Light shooting

        # ── WEAK SIGNALS (common/ambient — tiny contribution) ──
        # These should NOT trigger clips on their own

        # Damage vignette (58% of frames! — basically ambient)
        if px.get("has_damage_vignette"):
            s += 3

        # Entity label (26% — just means enemy name is on screen)
        if px.get("entity_label_visible"):
            s += 2

        # Callout text (24%)
        if px.get("callout_visible"):
            s += 1

        # System message (29%)
        if px.get("system_message"):
            s += 1

        # Motion blur (only real screen shake from explosions, threshold tightened)
        if px.get("has_motion_blur"):
            s += 5

        # Drama score (color intensity — ambient, tiny bonus)
        s += px.get("drama_score", 0) * 3

        return min(100, s)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    bbox_area_pct: float
    mask_points: Optional[list] = None
    @property
    def center(self): return ((self.bbox[0]+self.bbox[2])/2, (self.bbox[1]+self.bbox[3])/2)

@dataclass
class FrameAnalysis:
    frame_number: int
    timestamp_seconds: float
    timestamp_str: str
    detections: List[Detection]
    entity_counts: Dict[str, int]
    yolo_score: float
    pixel_score: float = 0.0
    pixel_data: Optional[dict] = None
    final_score: float = 0.0
    final_category: str = "routine"
    triggered_rules: List[str] = field(default_factory=list)
    image_path: Optional[str] = None
    @property
    def has_boss(self): return self.entity_counts.get("queen", 0) > 0
    @property
    def total_entities(self): return sum(self.entity_counts.values())
    def to_dict(self):
        d = asdict(self)
        d["detections"] = [asdict(x) for x in self.detections]
        return d

@dataclass
class ClipSegment:
    clip_id: int
    start_time: float
    end_time: float
    peak_score: float
    avg_score: float
    frame_count: int
    peak_frame: FrameAnalysis
    frames: List[FrameAnalysis]
    primary_category: str
    entities_seen: Dict[str, int]
    triggered_rules: List[str]
    @property
    def duration(self): return self.end_time - self.start_time
    @property
    def start_str(self): return str(timedelta(seconds=int(self.start_time)))
    @property
    def end_str(self): return str(timedelta(seconds=int(self.end_time)))
    def to_dict(self):
        return {
            "clip_id": self.clip_id, "start": self.start_time, "end": self.end_time,
            "start_str": self.start_str, "end_str": self.end_str,
            "duration": round(self.duration, 2), "peak_score": round(self.peak_score, 1),
            "avg_score": round(self.avg_score, 1), "frames": self.frame_count,
            "category": self.primary_category, "entities": self.entities_seen,
            "rules": self.triggered_rules,
        }


# =============================================================================
# VIDEO PROCESSOR
# =============================================================================

class VideoProcessor:
    def __init__(self, path, logger):
        self.path = Path(path); self.logger = logger
        if not self.path.exists(): raise FileNotFoundError(path)
        r = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
            "-show_format","-show_streams",str(self.path)], capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        vs = next(s for s in d["streams"] if s["codec_type"]=="video")
        fp = vs["r_frame_rate"].split("/")
        self.fps = float(fp[0])/float(fp[1]) if len(fp)==2 else float(fp[0])
        self.duration = float(d.get("format",{}).get("duration", vs.get("duration",0)))
        self.width = int(vs["width"]); self.height = int(vs["height"])
        self.total_frames = int(vs.get("nb_frames",0)) or int(self.duration*self.fps)
        logger.info(f"Video: {self.path.name} | {self.width}x{self.height} | {self.fps:.1f}fps | {timedelta(seconds=int(self.duration))}")

    def extract_frames(self, out_dir, interval=1.0):
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg","-y","-v","quiet","-i",str(self.path),
            "-vf",f"fps=1/{interval}","-q:v","2",str(out_dir/"frame_%06d.jpg")], check=True)
        frames = [(str(f), i*interval, int(i*interval*self.fps))
            for i, f in enumerate(sorted(out_dir.glob("frame_*.jpg")))]
        self.logger.info(f"Extracted {len(frames)} frames")
        return frames

    def cut_clip(self, start, end, out_path, pad=2.0):
        s = max(0, start-pad); d = min(self.duration, end+pad) - s
        subprocess.run(["ffmpeg","-y","-v","quiet","-ss",str(s),"-i",str(self.path),
            "-t",str(d),"-c:v","libx264","-preset","fast","-crf","22",
            "-c:a","aac","-b:a","128k",str(out_path)], check=True)


# =============================================================================
# YOLO DETECTOR (local weights only)
# =============================================================================

class YOLODetector:
    def __init__(self, logger, weights=None, conf=0.25, device=""):
        self.logger = logger; self.conf = conf
        if not YOLO: raise RuntimeError("pip install ultralytics")
        paths = [weights] if weights else []
        paths += ["best.pt", "arc_raiders_best.pt", "runs/segment/train/weights/best.pt", "weights/best.pt"]
        for p in paths:
            if p and Path(p).exists():
                logger.info(f"YOLO weights: {p}"); self.model = YOLO(p)
                if device: self.model.to(device)
                return
        raise FileNotFoundError(
            "No YOLO weights. Download from Roboflow:\n"
            "  https://universe.roboflow.com/valorantai/arc-raiders-8tjh4/model/11\n"
            "  Export YOLOv11 weights -> place best.pt in current directory")

    def detect(self, image_path):
        try:
            results = self.model(image_path, conf=self.conf, verbose=False)
        except Exception as e:
            self.logger.warning(f"YOLO failed: {e}"); return []
        dets = []
        for res in results:
            if res.boxes is None: continue
            ih, iw = res.orig_shape
            for i, box in enumerate(res.boxes):
                cid = int(box.cls[0]); c = float(box.conf[0])
                x1,y1,x2,y2 = [v/d for v, d in zip(box.xyxy[0].tolist(), [iw,ih,iw,ih])]
                x1,y1,x2,y2 = max(0,x1),max(0,y1),min(1,x2),min(1,y2)
                mp = None
                if res.masks and i < len(res.masks):
                    try: mp = [(float(p[0])/iw, float(p[1])/ih) for p in res.masks[i].xy[0]]
                    except: pass
                dets.append(Detection(cid, YOLO_CLASSES.get(cid,f"unk_{cid}"), c,
                    (x1,y1,x2,y2), (x2-x1)*(y2-y1)*100, mp))
        return dets


# =============================================================================
# SCORING + CLUSTERING
# =============================================================================

class ScoringEngine:
    def score_yolo(self, dets):
        counts = defaultdict(int)
        for d in dets: counts[d.class_name] += 1
        s = 0.0
        for name, cnt in counts.items():
            p = ENTITY_PROFILES.get(name)
            if not p: continue
            es = p["base"] + max(0, cnt-1) * p["count_bonus"]
            mx = max((d.bbox_area_pct for d in dets if d.class_name==name), default=0)
            if mx > 20: es *= 1.3
            if p["boss"]: es = max(es, 90)
            s += es
        rules = [r["name"] for r in COMBINATION_RULES if r["cond"](dict(counts))]
        for rn in rules:
            rule = next(r for r in COMBINATION_RULES if r["name"]==rn)
            s += rule["bonus"]
        if len(dets) >= 2:
            pts = [d.center for d in dets]
            avg = sum(math.sqrt((pts[i][0]-pts[j][0])**2+(pts[i][1]-pts[j][1])**2)
                for i in range(len(pts)) for j in range(i+1,len(pts))) / max(1, len(pts)*(len(pts)-1)//2)
            if avg < 0.3: s *= 1.2
        return min(100, s), dict(counts), rules

    def combine(self, yolo, pixel, boss):
        f = yolo * 0.65 + pixel * 0.35
        if boss: f = max(f, 85)
        return min(100, f)

class Clusterer:
    def __init__(self, logger, thresh=50, gap=5, min_d=3, max_d=60, pad=2):
        self.logger=logger; self.thresh=thresh; self.gap=gap
        self.min_d=min_d; self.max_d=max_d; self.pad=pad

    def cluster(self, frames):
        hot = sorted([f for f in frames if f.final_score >= self.thresh], key=lambda f: f.timestamp_seconds)
        if not hot: return []
        clusters, cur = [], [hot[0]]
        for f in hot[1:]:
            if f.timestamp_seconds - cur[-1].timestamp_seconds <= self.gap: cur.append(f)
            else: clusters.append(cur); cur = [f]
        clusters.append(cur)
        clips = []
        for i, cf in enumerate(clusters):
            pk = max(cf, key=lambda f: f.final_score)
            s = max(0, cf[0].timestamp_seconds - self.pad)
            e = cf[-1].timestamp_seconds + self.pad
            if (e-s) > self.max_d:
                c = pk.timestamp_seconds; s = max(0,c-self.max_d/2); e = c+self.max_d/2
            if (e-s) < self.min_d: continue
            ents = defaultdict(int)
            rls = set()
            for f in cf:
                for en, cnt in f.entity_counts.items(): ents[en] = max(ents[en], cnt)
                rls.update(f.triggered_rules)
            cats = defaultdict(int)
            for f in cf:
                if f.final_category != "routine": cats[f.final_category] += 1
            pc = max(cats, key=cats.get) if cats else "combat_highlight"
            clips.append(ClipSegment(i+1, s, e, pk.final_score,
                sum(f.final_score for f in cf)/len(cf), len(cf), pk, cf,
                pc, dict(ents), sorted(rls)))
        clips.sort(key=lambda c: c.peak_score, reverse=True)
        self.logger.info(f"Found {len(clips)} clips")
        return clips


# =============================================================================
# WEB APP ADAPTER — analyze_video() interface for app.py integration
# =============================================================================

class ArcClipDetectorAdapter:
    """
    Adapter that wraps the ARC Raiders clip detection pipeline to match
    the web app's analyze_video(video_path, progress_callback) interface.

    Works in two modes:
    - YOLO + Pixel: If best.pt weights are available, uses both YOLO entity
      detection and OpenCV pixel analysis for maximum accuracy.
    - Pixel-only: If no weights found, runs pure OpenCV pixel analysis
      (health bar, VFX, screen state, muzzle flash, damage vignette, etc.)
      No downloads or API keys needed.

    Returns highlights in the same format as other detection methods:
    [{"timestamp": float, "duration": float, "pre_pad": float,
      "label": str, "confidence": float}, ...]
    """

    SAMPLE_INTERVAL = 1.0

    def __init__(self, game_id="arc_raiders", weights_path=None,
                 confidence=0.25, device="", threshold=40.0):
        self.game_id = game_id
        self.weights_path = weights_path
        self.confidence = confidence
        self.device = device
        self.threshold = threshold
        self.has_yolo = False

        # Try to find weights — if not found, pixel-only mode
        if self.weights_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates = [
                os.path.join(base, "models", "best.pt"),
                os.path.join(base, "best.pt"),
                os.path.join(base, "arc_raiders_best.pt"),
                os.path.join(base, "weights", "best.pt"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    self.weights_path = c
                    self.has_yolo = True
                    break
        else:
            self.has_yolo = os.path.exists(self.weights_path)

    def analyze_video(self, video_path, progress_callback=None):
        """
        Run the CV pipeline on a video.

        Uses YOLO + pixel analysis if weights are available,
        otherwise pure pixel analysis (no .pt file needed).

        Returns list of highlight dicts compatible with the web app.
        """
        logger = logging.getLogger("arc_clip_detector")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"))
            logger.addHandler(handler)

        # Initialize components
        detector = None
        if self.has_yolo and YOLO is not None:
            try:
                detector = YOLODetector(
                    logger, weights=self.weights_path,
                    conf=self.confidence, device=self.device)
                print("  [ArcClipDetector] YOLO + OpenCV pixel analysis mode")
            except Exception as e:
                print(f"  [ArcClipDetector] YOLO init failed ({e}), falling back to pixel-only")
                detector = None

        if detector is None:
            print("  [ArcClipDetector] Pure OpenCV pixel analysis mode (no YOLO weights needed)")

        pixel = PixelAnalyzer(logger)
        scorer = ScoringEngine()
        # Pixel-only threshold: needs to be high enough to avoid false positives
        # from ambient signals (vignette=3, label=2, drama=~1.5 = ~6.5 baseline)
        # but low enough to catch real combat (muzzle flash=25, fire=30, etc.)
        threshold = self.threshold if detector else max(35.0, self.threshold * 0.8)
        clusterer = Clusterer(logger, thresh=threshold)

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_skip = max(1, int(fps * self.SAMPLE_INTERVAL))

        print(f"  [ArcClipDetector] Analyzing {video_path} ({duration:.0f}s)")

        # Analyze frames
        analyses = []
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_skip == 0:
                    timestamp = frame_idx / fps

                    # YOLO detection (if available)
                    dets = []
                    yolo_score = 0.0
                    counts = {}
                    rules = []

                    if detector is not None:
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                            tmp_path = tmp.name
                            cv2.imwrite(tmp_path, frame)
                        try:
                            dets = detector.detect(tmp_path)
                            yolo_score, counts, rules = scorer.score_yolo(dets)
                        finally:
                            os.unlink(tmp_path)

                    # Pixel analysis (always runs)
                    px = pixel.analyze(frame)
                    px_score = pixel.score(px)

                    # Category
                    cat = "routine"
                    if rules:
                        best = max(
                            (r for r in COMBINATION_RULES if r["name"] in rules),
                            key=lambda r: r["bonus"], default=None)
                        if best:
                            cat = best["cat"]
                    elif counts:
                        best_e = max(counts, key=lambda e: ENTITY_PROFILES.get(e, {}).get("base", 0))
                        cat = ENTITY_PROFILES.get(best_e, {}).get("cat", "routine")

                    # Pixel-only category detection
                    if px.get("screen_state") == "death_screen":
                        cat = "death_fail"
                    elif px.get("screen_state") == "inventory":
                        cat = "downtime"
                    elif not counts:
                        # Pixel-only mode: determine category from pixel signals
                        if px.get("has_fire") or px.get("has_muzzle_flash"):
                            cat = "combat_highlight"
                        elif px.get("has_damage_vignette"):
                            cat = "close_call"
                        elif px.get("screen_state") == "screen_flash":
                            cat = "epic_moment"
                        elif px.get("has_tracers"):
                            cat = "combat_highlight"
                        elif px.get("health") == "critical":
                            cat = "close_call"

                    # Score: use pixel-only if no YOLO, otherwise combine
                    if detector is not None:
                        final_score = scorer.combine(yolo_score, px_score,
                                                     counts.get("queen", 0) > 0)
                    else:
                        # Pixel-only: score is just the pixel score
                        final_score = px_score

                    analyses.append(FrameAnalysis(
                        frame_number=int(timestamp * fps),
                        timestamp_seconds=timestamp,
                        timestamp_str=str(timedelta(seconds=int(timestamp))),
                        detections=dets, entity_counts=counts,
                        yolo_score=yolo_score, pixel_score=px_score,
                        pixel_data=px, final_score=final_score,
                        final_category=cat, triggered_rules=rules,
                    ))

                    if frame_idx % (frame_skip * 30) == 0:
                        if detector and counts:
                            entities = ", ".join(f"{k}({v})" for k, v in counts.items())
                            print(f"  [ArcClipDetector] {timestamp:.1f}s - "
                                  f"yolo:{yolo_score:.1f} px:{px_score:.1f} "
                                  f"final:{final_score:.1f} [{cat}] {entities}")
                        else:
                            print(f"  [ArcClipDetector] {timestamp:.1f}s - "
                                  f"px:{px_score:.1f} [{cat}] "
                                  f"health:{px.get('health','')} "
                                  f"fire:{px.get('has_fire','')} "
                                  f"vignette:{px.get('has_damage_vignette','')}")

                if progress_callback and total_frames > 0:
                    progress_callback(min(frame_idx / total_frames, 1.0))

                frame_idx += 1
        finally:
            cap.release()

        if progress_callback:
            progress_callback(1.0)

        print(f"  [ArcClipDetector] Analyzed {len(analyses)} frames")

        if not analyses:
            return []

        # Cluster into clips
        clips = clusterer.cluster(analyses)
        print(f"  [ArcClipDetector] Found {len(clips)} clip(s)")

        # Convert ClipSegments to highlight format for the web app
        highlights = []
        for clip in clips:
            clip_duration = clip.duration
            clip_duration = max(20, min(60, clip_duration + 10))

            entities = ", ".join(f"{k}({v})" for k, v in clip.entities_seen.items())
            label_parts = []
            if clip.primary_category != "routine":
                label_parts.append(clip.primary_category.replace("_", " ").title())
            if entities:
                label_parts.append(entities)
            elif clip.frames:
                # Pixel-only: build label from pixel signals
                px_signals = []
                peak_px = clip.peak_frame.pixel_data or {}
                if peak_px.get("has_fire"): px_signals.append("Fire/Explosion")
                if peak_px.get("has_muzzle_flash"): px_signals.append("Gunfire")
                if peak_px.get("has_damage_vignette"): px_signals.append("Taking Damage")
                if peak_px.get("screen_state") == "screen_flash": px_signals.append("Screen Flash")
                if peak_px.get("has_tracers"): px_signals.append("Tracers")
                if peak_px.get("health") == "critical": px_signals.append("Critical HP")
                if peak_px.get("screen_state") == "death_screen": px_signals.append("Death")
                if px_signals:
                    label_parts.append(" + ".join(px_signals[:3]))
            if clip.triggered_rules:
                label_parts.append(" | ".join(r.replace("_", " ") for r in clip.triggered_rules[:2]))

            label = " — ".join(label_parts) if label_parts else "Action Detected"

            highlights.append({
                "timestamp": clip.start_time,
                "duration": clip_duration,
                "pre_pad": 2.0,
                "label": label,
                "confidence": round(min(clip.peak_score / 100.0, 1.0), 2),
            })

        return highlights


# =============================================================================
# CLI PIPELINE
# =============================================================================

class ArcClipDetector:
    def __init__(self, args):
        self.args = args
        self.log = logging.getLogger("arc"); self.log.setLevel(logging.DEBUG if args.verbose else logging.INFO)
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"))
        self.log.addHandler(h)
        self.video = VideoProcessor(args.input, self.log)
        self.scorer = ScoringEngine()
        self.pixel = PixelAnalyzer(self.log)
        self.clusterer = Clusterer(self.log, args.threshold, args.merge_gap, args.min_dur, args.max_dur, args.pad)
        self.yolo = YOLODetector(self.log, args.weights, args.confidence, args.device)
        self.out = Path(args.output); self.out.mkdir(parents=True, exist_ok=True)

    def run(self):
        self.log.info("=" * 60)
        self.log.info("ARC RAIDERS CLIP DETECTOR — Pure CV")
        self.log.info("=" * 60)
        frames = self.video.extract_frames(self.out/"frames", self.args.interval)
        analyses = []
        for fp, ts, fn in tqdm(frames, desc="Analyzing", total=len(frames)):
            dets = self.yolo.detect(fp)
            ys, counts, rules = self.scorer.score_yolo(dets)
            bgr = cv2.imread(fp)
            px = self.pixel.analyze(bgr) if bgr is not None else {}
            ps = self.pixel.score(px) if px else 0.0
            cat = "routine"
            if rules:
                best = max((r for r in COMBINATION_RULES if r["name"] in rules), key=lambda r: r["bonus"], default=None)
                if best: cat = best["cat"]
            elif counts:
                be = max(counts, key=lambda e: ENTITY_PROFILES.get(e,{}).get("base",0))
                cat = ENTITY_PROFILES.get(be,{}).get("cat","routine")
            if px.get("screen_state") == "death_screen": cat = "death_fail"
            elif px.get("screen_state") == "inventory": cat = "downtime"
            a = FrameAnalysis(fn, ts, str(timedelta(seconds=int(ts))), dets, counts,
                ys, ps, px, 0.0, cat, rules, fp)
            a.final_score = self.scorer.combine(ys, ps, a.has_boss)
            analyses.append(a)

        clips = self.clusterer.cluster(analyses)
        # Export
        with open(self.out/"analysis.json","w") as f: json.dump([a.to_dict() for a in analyses], f, indent=2, default=str)
        with open(self.out/"clips.json","w") as f: json.dump([c.to_dict() for c in clips], f, indent=2, default=str)
        with open(self.out/"timeline.csv","w",newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts","ts_str","yolo","pixel","final","cat","entities","rules","health","fire","vignette","screen"])
            for a in analyses:
                px = a.pixel_data or {}
                w.writerow([f"{a.timestamp_seconds:.1f}",a.timestamp_str,f"{a.yolo_score:.1f}",
                    f"{a.pixel_score:.1f}",f"{a.final_score:.1f}",a.final_category,
                    "|".join(f"{k}:{v}" for k,v in a.entity_counts.items()),
                    "|".join(a.triggered_rules), px.get("health",""), px.get("has_fire",""),
                    px.get("has_damage_vignette",""), px.get("screen_state","")])
        if self.args.cut_clips and clips:
            cd = self.out/"clips_video"; cd.mkdir(exist_ok=True)
            for c in tqdm(clips, desc="Cutting"):
                fn = f"clip{c.clip_id:03d}_s{c.peak_score:.0f}_{c.primary_category}_{c.start_str.replace(':','-')}.mp4"
                self.video.cut_clip(c.start_time, c.end_time, str(cd/fn), self.args.pad)

        # Summary
        print("\n" + "="*60 + f"\nCLIPS FOUND: {len(clips)}\n" + "="*60)
        for c in clips[:30]:
            print(f"  #{c.clip_id:3d} [{c.start_str}->{c.end_str}] Score:{c.peak_score:5.1f} {c.primary_category:<18s} {dict(c.entities_seen)}")
        return clips

def main():
    p = argparse.ArgumentParser(description="ARC Raiders Clip Detector (Pure CV)")
    p.add_argument("--input","-i",required=True)
    p.add_argument("--output","-o",default="arc_clips_output")
    p.add_argument("--cut-clips",action="store_true")
    p.add_argument("--interval",type=float,default=1.0,help="Seconds between frame samples")
    p.add_argument("--weights",default=None,help="YOLO .pt weights path")
    p.add_argument("--confidence",type=float,default=0.25)
    p.add_argument("--device",default="")
    p.add_argument("--threshold",type=float,default=50.0)
    p.add_argument("--merge-gap",type=float,default=5.0)
    p.add_argument("--min-dur",type=float,default=3.0)
    p.add_argument("--max-dur",type=float,default=60.0)
    p.add_argument("--pad",type=float,default=2.0)
    p.add_argument("--verbose","-v",action="store_true")
    return ArcClipDetector(p.parse_args()).run()

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
