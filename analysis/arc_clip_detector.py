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
    # Classes 0/1/5 are HUD digit artifacts in the v0.11 dataset — no scoring weight.
    "0": {"base": 0, "multi": 1.0, "count_bonus": 0, "cat": "routine", "boss": False},
    "1": {"base": 0, "multi": 1.0, "count_bonus": 0, "cat": "routine", "boss": False},
    "5": {"base": 0, "multi": 1.0, "count_bonus": 0, "cat": "routine", "boss": False},
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

    # ARC scanner beam detection — main gameplay area (exclude HUD corners)
    # Scanner beams appear in the 3D world, typically from center to upper areas
    SCAN_AREA = (0.10, 0.10, 0.90, 0.80)

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

    # ARC scanner beams — distinct saturated narrow beams
    # Blue scanner (passive/searching): bright cyan-blue, very saturated
    SCAN_BLUE_LO = np.array([85, 120, 140])
    SCAN_BLUE_HI = np.array([115, 255, 255])
    # Red scanner (aggro/attacking): bright red, very saturated
    # ARC scanner beams turn RED when they detect and engage the player
    SCAN_RED1_LO = np.array([0, 150, 150])
    SCAN_RED1_HI = np.array([8, 255, 255])
    SCAN_RED2_LO = np.array([172, 150, 150])
    SCAN_RED2_HI = np.array([180, 255, 255])
    # Yellow/amber scanner (transitional — some ARCs flash yellow briefly)
    SCAN_AMBER_LO = np.array([15, 120, 160])
    SCAN_AMBER_HI = np.array([25, 255, 255])

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
        self.menu_suppress = True  # Can be toggled off via detection_overrides
        # Temporal tracking: store previous frame data for change detection
        self._prev_brightness = None
        self._prev_center_brightness = None
        self._prev_health_pct = None
        self._prev_flash_pct = None
        self._prev_vignette_pct = None
        self._prev_xp_pct = None
        self._prev_ammo_gray = None   # Previous ammo region for frame diff
        self._prev_edge_brightness = None
        self._brightness_history = []  # last N center brightness values
        # ARC scanner tracking
        self._prev_scan_red_pct = 0.0
        self._prev_scan_blue_pct = 0.0
        self._scan_red_history = []   # last N red scan values for sustained detection

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

        # --- ARC Scanner Beam Detection ---
        # ARC enemies emit visible scanner beams that are VERY saturated and distinct
        # Blue = passive (searching), Red = aggro (detected player), Amber = transitional
        scan_area = self._region(frame, self.SCAN_AREA)
        scan_red = (self._hsv_pct(scan_area, self.SCAN_RED1_LO, self.SCAN_RED1_HI) +
                    self._hsv_pct(scan_area, self.SCAN_RED2_LO, self.SCAN_RED2_HI))
        scan_blue = self._hsv_pct(scan_area, self.SCAN_BLUE_LO, self.SCAN_BLUE_HI)
        scan_amber = self._hsv_pct(scan_area, self.SCAN_AMBER_LO, self.SCAN_AMBER_HI)
        r["scan_red_pct"] = round(scan_red, 4)
        r["scan_blue_pct"] = round(scan_blue, 4)
        r["scan_amber_pct"] = round(scan_amber, 4)

        # Detect scanner beam shape: narrow bright lines in the gameplay area
        # Scanner beams are thin (2-8px wide) and elongated (aspect ratio > 4:1)
        scan_hsv = cv2.cvtColor(scan_area, cv2.COLOR_BGR2HSV)
        # Red scanner mask (both ends of hue wheel)
        red_mask1 = cv2.inRange(scan_hsv, self.SCAN_RED1_LO, self.SCAN_RED1_HI)
        red_mask2 = cv2.inRange(scan_hsv, self.SCAN_RED2_LO, self.SCAN_RED2_HI)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        # Blue scanner mask
        blue_mask = cv2.inRange(scan_hsv, self.SCAN_BLUE_LO, self.SCAN_BLUE_HI)

        # Check for elongated beam shapes (characteristic of scanner beams)
        arc_beam_detected = False
        scan_beam_count = 0
        for mask, color_name in [(red_mask, "red"), (blue_mask, "blue")]:
            beam_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in beam_contours:
                area = cv2.contourArea(cnt)
                if area < 50:
                    continue
                # Check elongation — scanner beams are narrow lines
                x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
                aspect = max(w_c, h_c) / max(min(w_c, h_c), 1)
                if aspect > 3.0 and area > 80:
                    scan_beam_count += 1
                    arc_beam_detected = True

        r["arc_beam_detected"] = arc_beam_detected
        r["scan_beam_count"] = scan_beam_count

        # Scanner state classification
        has_red_scan = scan_red > 0.003 or (arc_beam_detected and scan_red > 0.001)
        has_blue_scan = scan_blue > 0.005
        has_amber_scan = scan_amber > 0.003

        if has_red_scan:
            r["arc_scan_state"] = "aggro"      # ARC has spotted you — combat imminent
        elif has_amber_scan:
            r["arc_scan_state"] = "alert"      # ARC is transitioning — about to detect
        elif has_blue_scan:
            r["arc_scan_state"] = "searching"  # ARC nearby, scanning passively
        else:
            r["arc_scan_state"] = "none"

        r["arc_scanning"] = r["arc_scan_state"] != "none"

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
            if self.menu_suppress and center_b > self.MENU_CENTER_MIN:
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

        # === TEMPORAL ANALYSIS (frame-to-frame changes) ===
        # These detect CHANGES which are far more reliable than static thresholds

        center_b = self._avg_brightness(self._region(frame, self.CENTER))
        r["center_brightness"] = round(center_b, 1)

        # --- Brightness delta: sudden brightness spike = combat VFX ---
        # A bright outdoor scene has STABLE brightness. An explosion/flash has a SPIKE.
        if self._prev_brightness is not None:
            brightness_delta = avg_b - self._prev_brightness
            center_delta = center_b - (self._prev_center_brightness or center_b)
            r["brightness_delta"] = round(brightness_delta, 1)
            r["center_delta"] = round(center_delta, 1)
            # Sudden brightness increase > 15 = likely VFX (flash, explosion)
            r["sudden_flash"] = brightness_delta > 15 or center_delta > 25
            # Sudden brightness drop > 20 = likely post-flash or getting hit
            r["sudden_dark"] = brightness_delta < -20
        else:
            r["brightness_delta"] = 0.0
            r["center_delta"] = 0.0
            r["sudden_flash"] = False
            r["sudden_dark"] = False

        # --- Health change: health dropping = taking damage ---
        current_health_pct = r.get("health_white_pct", 0.0)
        if self._prev_health_pct is not None:
            health_delta = current_health_pct - self._prev_health_pct
            r["health_delta"] = round(health_delta, 4)
            # Health dropped significantly = actively taking damage
            r["health_dropping"] = health_delta < -0.02
            # Health dropped a lot = big hit
            r["big_health_drop"] = health_delta < -0.05
        else:
            r["health_delta"] = 0.0
            r["health_dropping"] = False
            r["big_health_drop"] = False

        # --- Center brightness variance: flickering = sustained gunfire ---
        self._brightness_history.append(center_b)
        if len(self._brightness_history) > 5:
            self._brightness_history.pop(0)
        if len(self._brightness_history) >= 3:
            hist = self._brightness_history
            flicker_var = float(np.std(hist))
            r["center_flicker"] = round(flicker_var, 1)
            # High variance in center brightness over recent frames = sustained combat
            r["sustained_combat"] = flicker_var > 12
        else:
            r["center_flicker"] = 0.0
            r["sustained_combat"] = False

        # --- Localized flash: center delta >> edge delta = muzzle flash ---
        # A muzzle flash blooms from center. A bright sky is uniform.
        edge_l_b = self._avg_brightness(self._region(frame, self.EDGE_L))
        edge_r_b = self._avg_brightness(self._region(frame, self.EDGE_R))
        edge_avg_b = (edge_l_b + edge_r_b) / 2.0
        if self._prev_edge_brightness is not None:
            edge_delta = abs(edge_avg_b - self._prev_edge_brightness)
            center_abs_delta = abs(r.get("center_delta", 0))
            # Center changed a lot more than edges = localized flash (muzzle/explosion)
            r["localized_flash"] = center_abs_delta > 15 and center_abs_delta > edge_delta * 2.5
        else:
            r["localized_flash"] = False

        # --- Vignette onset: red APPEARED this frame (vs already present) ---
        current_vignette = r.get("vignette_red_pct", 0.0)
        if self._prev_vignette_pct is not None:
            vignette_delta = current_vignette - self._prev_vignette_pct
            r["vignette_onset"] = vignette_delta > 0.05  # Red just appeared
        else:
            r["vignette_onset"] = False

        # --- XP appeared: XP notification just showed up this frame ---
        current_xp = r.get("xp_yellow_pct", 0.0)
        if self._prev_xp_pct is not None:
            r["xp_appeared"] = current_xp > 0.01 and self._prev_xp_pct < 0.005
        else:
            r["xp_appeared"] = False

        # --- Ammo counter changed: digits changed = player fired ---
        ammo_region = self._region(frame, self.AMMO_COUNTER)
        if ammo_region.size > 0:
            ammo_gray = cv2.cvtColor(ammo_region, cv2.COLOR_BGR2GRAY)
            if self._prev_ammo_gray is not None and self._prev_ammo_gray.shape == ammo_gray.shape:
                ammo_diff = float(np.mean(cv2.absdiff(ammo_gray, self._prev_ammo_gray)))
                r["ammo_changed"] = ammo_diff > 8.0  # Digits shifted
                r["ammo_diff"] = round(ammo_diff, 1)
            else:
                r["ammo_changed"] = False
                r["ammo_diff"] = 0.0
            self._prev_ammo_gray = ammo_gray.copy()
        else:
            r["ammo_changed"] = False
            r["ammo_diff"] = 0.0

        # --- ARC Scanner Transitions ---
        # The most exciting moment: blue→red = ARC just detected the player
        current_scan_red = r.get("scan_red_pct", 0.0)
        current_scan_blue = r.get("scan_blue_pct", 0.0)
        r["scan_aggro_onset"] = (current_scan_red > 0.002 and self._prev_scan_red_pct < 0.001)
        r["scan_appeared"] = (r["arc_scanning"] and self._prev_scan_red_pct < 0.001 and self._prev_scan_blue_pct < 0.002)
        # Track sustained scanning (red beams present over multiple frames = active fight)
        self._scan_red_history.append(current_scan_red)
        if len(self._scan_red_history) > 5:
            self._scan_red_history.pop(0)
        r["sustained_scan"] = (len(self._scan_red_history) >= 3 and
                               sum(1 for v in self._scan_red_history if v > 0.001) >= 2)

        # Entity label + scan state = can guess ARC type + threat level
        if r.get("entity_label_visible") and r["arc_scan_state"] == "aggro":
            r["arc_encounter"] = True
            # Entity label width hints at which ARC type
            lw = r.get("label_width_px", 0)
            if lw > 0:
                # Map label width to threat level
                # Short names (POP, TICK, WASP): low-medium threat
                # Medium names (HORNET, SNITCH, LEAPER): medium-high threat
                # Long names (BASTION, BOMBARDIER, ROCKETEER, SENTINEL): high threat
                if lw >= 80:
                    r["arc_threat"] = "boss"       # BOMBARDIER, ROCKETEER, SENTINEL-class
                elif lw >= 55:
                    r["arc_threat"] = "heavy"      # HORNET, SNITCH, LEAPER, BASTION, FIREBALL
                else:
                    r["arc_threat"] = "standard"   # POP, TICK, WASP
            else:
                r["arc_threat"] = "unknown"
        else:
            r["arc_encounter"] = False
            r["arc_threat"] = "none"

        # Update previous frame state
        self._prev_brightness = avg_b
        self._prev_center_brightness = center_b
        self._prev_health_pct = current_health_pct
        self._prev_flash_pct = r.get("flash_pct", 0.0)
        self._prev_vignette_pct = current_vignette
        self._prev_xp_pct = current_xp
        self._prev_edge_brightness = edge_avg_b
        self._prev_scan_red_pct = current_scan_red
        self._prev_scan_blue_pct = current_scan_blue

        return r

    def score(self, px: dict, version: str = "v3_temporal") -> float:
        """Score a frame using the selected scoring version.

        Available versions:
          v1_strict     — Very strict, requires strong combat signals + temporal change.
                          Fewest clips, highest quality. May miss some action.
          v2_balanced   — Balanced between false positives and missed clips.
                          Requires at least one strong signal OR two medium signals.
          v3_temporal   — (DEFAULT) Heavily weights temporal changes (frame-to-frame).
                          A bright scene that stays bright = boring. A sudden spike = combat.
          v4_aggressive — More clips, lower quality. Good for long VODs where you
                          don't want to miss anything.
          v5_combat_only — Only clips actual fighting: muzzle flash + health drop,
                           fire + tracers, etc. Ignores everything else.
        """
        versions = {
            "v1_strict": self._score_v1_strict,
            "v2_balanced": self._score_v2_balanced,
            "v3_temporal": self._score_v3_temporal,
            "v4_aggressive": self._score_v4_aggressive,
            "v5_combat_only": self._score_v5_combat_only,
        }
        fn = versions.get(version, self._score_v3_temporal)
        return fn(px)

    def _score_v1_strict(self, px: dict) -> float:
        """V1 STRICT: Very few clips, very high quality.

        Philosophy: Only clip when there's UNDENIABLE combat evidence.
        Requires temporal change + at least one strong static signal.
        Threshold: 45+ to clip.
        """
        s = 0.0
        state = px.get("screen_state", "gameplay")
        if state in ("inventory",):
            return 0.0
        if state == "death_screen":
            return 40.0

        # Count how many STRONG signals are present
        strong_count = 0

        if px.get("has_fire") and px.get("fire_pct", 0) > 0.03:
            s += 25
            strong_count += 1

        if px.get("sudden_flash"):
            s += 20
            strong_count += 1

        if px.get("big_health_drop"):
            s += 30
            strong_count += 1

        if px.get("sustained_combat"):
            s += 20
            strong_count += 1

        if state == "screen_flash" and px.get("sudden_flash"):
            s += 30
            strong_count += 1

        h = px.get("health", "full")
        if h == "critical" and px.get("health_dropping"):
            s += 30
            strong_count += 1

        if px.get("xp_notification"):
            s += 25
            strong_count += 1

        # Muzzle flash ONLY counts if there's also a temporal change
        if px.get("has_muzzle_flash") and (px.get("localized_flash") or px.get("sustained_combat")):
            s += 20
            strong_count += 1

        # Localized flash (center changed but edges didn't) = explosion/muzzle
        if px.get("localized_flash") and not px.get("sudden_flash"):
            s += 15
            strong_count += 1

        # Ammo counter changed = player is shooting
        if px.get("ammo_changed"):
            s += 15
            strong_count += 1

        # XP just appeared this frame = kill event
        if px.get("xp_appeared"):
            s += 10  # Bonus on top of xp_notification

        # Must have at least 1 strong signal to score above noise
        if strong_count == 0:
            return min(5.0, s)

        # ARC scanner detection — scanner beams = ARC encounter
        if px.get("scan_aggro_onset"):
            s += 35  # Scanner just turned red = ARC detected you
            strong_count += 1
        elif px.get("arc_encounter"):
            s += 25  # Entity label + red scanner
            strong_count += 1
        elif px.get("sustained_scan"):
            s += 15
            strong_count += 1

        # Small bonus for supporting signals
        if px.get("has_tracers") and px.get("tracer_count", 0) > 15:
            s += 5
        if px.get("vignette_onset"):  # Red JUST appeared (not persistent)
            s += 8

        return min(100, s)

    def _score_v2_balanced(self, px: dict) -> float:
        """V2 BALANCED: Good balance between clip count and quality.

        Philosophy: Require at least one strong signal OR two medium signals.
        Static-only signals (no temporal change) are heavily discounted.
        Threshold: 40+ to clip.
        """
        s = 0.0
        state = px.get("screen_state", "gameplay")
        if state in ("inventory",):
            return 0.0
        if state == "death_screen":
            return 38.0

        # TEMPORAL SIGNALS (worth more because they indicate CHANGE)
        if px.get("sudden_flash"):      s += 22
        if px.get("big_health_drop"):   s += 25
        if px.get("health_dropping"):   s += 12
        if px.get("sustained_combat"):  s += 18
        if px.get("sudden_dark"):       s += 8   # Post-explosion

        # STATIC COMBAT SIGNALS (discounted without temporal support)
        has_temporal = (px.get("sudden_flash") or px.get("health_dropping")
                        or px.get("sustained_combat"))

        if px.get("has_fire"):
            s += 28 if has_temporal else 12

        if px.get("has_muzzle_flash"):
            s += 22 if has_temporal else 8

        if state == "screen_flash":
            s += 25 if px.get("sudden_flash") else 10

        h = px.get("health", "full")
        if h == "critical":
            s += 22 if px.get("health_dropping") else 10
        elif h == "low":
            s += 8

        if px.get("xp_notification"):
            s += 20

        # MEDIUM SIGNALS
        if px.get("has_tracers"):
            tc = px.get("tracer_count", 0)
            if tc > 20: s += 10
            elif tc > 10: s += 5

        if px.get("has_motion_blur"):
            s += 4

        # ARC scanner detection
        if px.get("scan_aggro_onset"):
            s += 30  # Scanner just went red
        elif px.get("arc_encounter"):
            s += 20  # Entity label + aggro scan
        elif px.get("sustained_scan"):
            s += 12
        if px.get("arc_beam_detected"):
            s += 5   # Visible beam shape

        # WEAK SIGNALS (barely contribute)
        if px.get("has_damage_vignette"): s += 2
        if px.get("entity_label_visible"): s += 1
        s += px.get("drama_score", 0) * 2

        return min(100, s)

    def _score_v3_temporal(self, px: dict) -> float:
        """V3 TEMPORAL (DEFAULT): Heavily weights frame-to-frame changes.

        Philosophy: A bright outdoor scene is STABLE brightness.
        Combat produces SPIKES and FLICKER. Detect the delta, not the absolute.
        Threshold: 35+ to clip.
        """
        s = 0.0
        state = px.get("screen_state", "gameplay")
        if state in ("inventory",):
            return 0.0
        if state == "death_screen":
            return 35.0

        # === TEMPORAL SIGNALS (primary scoring) ===

        # Sudden brightness spike = explosion, flash, muzzle flash
        if px.get("sudden_flash"):
            s += 25

        # Localized flash (center spiked but edges didn't) = muzzle flash / explosion
        if px.get("localized_flash"):
            s += 20

        # Health actively dropping = taking damage right now
        if px.get("big_health_drop"):
            s += 30
        elif px.get("health_dropping"):
            s += 15

        # Center brightness flickering = sustained gunfire (flash-dark-flash pattern)
        if px.get("sustained_combat"):
            s += 22

        # Ammo counter changed = player is shooting
        if px.get("ammo_changed"):
            s += 18

        # Vignette just appeared = just took a hit (vs always-on ambient)
        if px.get("vignette_onset"):
            s += 12

        # XP just appeared = kill event this frame
        if px.get("xp_appeared"):
            s += 10  # On top of xp_notification below

        # Post-explosion darkness
        if px.get("sudden_dark"):
            s += 10

        # === STATIC SIGNALS (secondary, boosted by temporal) ===
        has_action = (px.get("sudden_flash") or px.get("health_dropping")
                      or px.get("sustained_combat") or px.get("localized_flash")
                      or px.get("ammo_changed"))

        # Fire — always worth something, more if temporal confirms
        if px.get("has_fire"):
            s += 25 if has_action else 12

        # Muzzle flash — only trust with temporal backup
        if px.get("has_muzzle_flash"):
            s += 18 if has_action else 3

        # Screen flash — need temporal to distinguish from bright scene
        if state == "screen_flash":
            s += 28 if px.get("sudden_flash") else 5

        # Health state
        h = px.get("health", "full")
        if h == "critical":
            s += 20 if px.get("health_dropping") else 8
        elif h == "low":
            s += 6

        # XP = kill confirmed, always clip-worthy
        if px.get("xp_notification"):
            s += 22

        # Tracers — worth more with temporal support
        if px.get("has_tracers"):
            tc = px.get("tracer_count", 0)
            if tc > 20: s += 12 if has_action else 5
            elif tc > 10: s += 6 if has_action else 2

        # Motion blur from screen shake
        if px.get("has_motion_blur"):
            s += 5

        # ARC scanner detection (temporal: scanner state CHANGED)
        if px.get("scan_aggro_onset"):
            s += 30  # Scanner JUST went red this frame = most exciting
        elif px.get("arc_encounter"):
            s += 22  # Entity label + red scanner present
        elif px.get("sustained_scan"):
            s += 12  # Red beams over multiple frames = active fight
        if px.get("scan_appeared"):
            s += 8   # Any scanner beam just appeared
        # Beam shape bonus (confirms it's a real beam, not ambient red)
        if px.get("arc_beam_detected") and px.get("arc_scan_state") == "aggro":
            s += 8
        # Boss-class ARC encounter = always clip
        if px.get("arc_threat") == "boss":
            s += 15

        # Weak ambient signals (tiny contribution, only with action)
        if px.get("has_damage_vignette") and has_action: s += 2
        if px.get("entity_label_visible"): s += 1
        s += px.get("drama_score", 0) * 2

        return min(100, s)

    def _score_v4_aggressive(self, px: dict) -> float:
        """V4 AGGRESSIVE: More clips, catch everything.

        Philosophy: Better to clip something boring than miss real action.
        Good for long VODs. Will produce more clips than other versions.
        Threshold: 30+ to clip.
        """
        s = 0.0
        state = px.get("screen_state", "gameplay")
        if state in ("inventory",):
            return 0.0
        if state == "death_screen":
            return 32.0

        # Temporal
        if px.get("sudden_flash"):      s += 25
        if px.get("big_health_drop"):   s += 25
        if px.get("health_dropping"):   s += 15
        if px.get("sustained_combat"):  s += 20
        if px.get("sudden_dark"):       s += 10

        # Static combat (still worth points even without temporal)
        if px.get("has_fire"):
            s += 25 * min(1.0, px.get("fire_pct", 0) * 10)
        if px.get("has_muzzle_flash"):
            s += 18
        if state == "screen_flash":
            s += 22

        h = px.get("health", "full")
        if h == "critical":   s += 22
        elif h == "low":      s += 10
        elif h == "medium":   s += 3

        if px.get("xp_notification"):   s += 20

        # Medium signals worth more
        if px.get("has_tracers"):
            tc = px.get("tracer_count", 0)
            if tc > 15: s += 12
            elif tc > 8:  s += 8

        if px.get("has_damage_vignette"): s += 5
        if px.get("entity_label_visible"): s += 3
        if px.get("callout_visible"):     s += 2
        if px.get("has_motion_blur"):     s += 6
        s += px.get("drama_score", 0) * 4

        # ARC scanner (aggressive catches all scanner activity)
        if px.get("scan_aggro_onset"):   s += 28
        elif px.get("arc_encounter"):    s += 20
        elif px.get("sustained_scan"):   s += 12
        if px.get("arc_scanning"):       s += 6  # Any scan = interesting
        if px.get("arc_beam_detected"):  s += 4
        if px.get("arc_threat") == "boss": s += 15

        return min(100, s)

    def _score_v5_combat_only(self, px: dict) -> float:
        """V5 COMBAT ONLY: Only clips confirmed fighting.

        Philosophy: Requires MULTIPLE combat signals simultaneously, and
        at least ONE must be temporal (proving something CHANGED).
        Static-only signals (muzzle flash + tracers without temporal change)
        are rejected because bright outdoor scenes produce the same static signals.
        Threshold: 40+ to clip.
        """
        s = 0.0
        state = px.get("screen_state", "gameplay")
        if state in ("inventory",):
            return 0.0
        if state == "death_screen":
            return 42.0

        # XP is always clip-worthy (kill confirmed)
        if px.get("xp_notification"):
            return 45.0

        # Separate temporal vs static signals
        temporal_signals = 0
        if px.get("sudden_flash"): temporal_signals += 1
        if px.get("localized_flash"): temporal_signals += 1
        if px.get("health_dropping"): temporal_signals += 1
        if px.get("sustained_combat"): temporal_signals += 1
        if px.get("big_health_drop"): temporal_signals += 1
        if px.get("ammo_changed"): temporal_signals += 1
        if px.get("vignette_onset"): temporal_signals += 1
        if px.get("sudden_dark"): temporal_signals += 1
        # Scanner transitions are temporal (state changed this frame)
        if px.get("scan_aggro_onset"): temporal_signals += 1
        if px.get("scan_appeared"): temporal_signals += 1

        static_signals = 0
        if px.get("has_fire"): static_signals += 1
        if px.get("has_muzzle_flash"): static_signals += 1
        if px.get("has_tracers") and px.get("tracer_count", 0) > 10: static_signals += 1
        if px.get("has_motion_blur"): static_signals += 1
        if state == "screen_flash": static_signals += 1
        h = px.get("health", "full")
        if h in ("critical", "low"): static_signals += 1
        if px.get("has_damage_vignette"): static_signals += 1
        # Sustained scanner is static (already present for multiple frames)
        if px.get("sustained_scan"): static_signals += 1
        if px.get("arc_beam_detected"): static_signals += 1

        total = temporal_signals + static_signals

        # MUST have at least 1 temporal signal (something CHANGED)
        # Pure static signals = could just be a bright scene
        if temporal_signals == 0:
            return min(5.0, total * 2.0)

        # Must have at least 2 total signals
        if total < 2:
            return min(8.0, total * 4.0)

        # Base score from signal count (2 signals = 20, 5+ signals = 50)
        s = min(50, total * 10)

        # Bonus for strong specific combos (all require temporal)
        if px.get("has_fire") and px.get("sudden_flash"):
            s += 15  # Explosion confirmed
        if px.get("health_dropping") and px.get("vignette_onset"):
            s += 18  # Just got hit — vignette appeared + health dropped
        elif px.get("health_dropping") and px.get("has_damage_vignette"):
            s += 12  # Still getting hurt
        if px.get("has_muzzle_flash") and px.get("sustained_combat"):
            s += 15  # Sustained shooting confirmed
        if px.get("ammo_changed") and px.get("localized_flash"):
            s += 15  # Shooting + muzzle bloom confirmed
        if h == "critical" and px.get("big_health_drop"):
            s += 20  # Near death moment
        # ARC scanner combos
        if px.get("scan_aggro_onset") and px.get("has_damage_vignette"):
            s += 20  # ARC spotted you AND you're taking damage
        if px.get("arc_encounter") and px.get("health_dropping"):
            s += 18  # Named ARC attacking + health dropping
        if px.get("arc_threat") == "boss":
            s += 25  # Boss-class ARC = always clip

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
        # Autodetect CUDA > MPS (Apple Silicon) > CPU when caller didn't pin a device.
        if not device:
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
            except Exception:
                pass
        paths = [weights] if weights else []
        paths += ["best.pt", "arc_raiders_best.pt", "runs/segment/train/weights/best.pt", "weights/best.pt"]
        for p in paths:
            if p and Path(p).exists():
                logger.info(f"YOLO weights: {p} (device={device or 'cpu'})"); self.model = YOLO(p)
                if device:
                    try: self.model.to(device)
                    except Exception as e: logger.warning(f"YOLO .to({device}) failed, CPU: {e}")
                return
        raise FileNotFoundError(
            "No YOLO weights. Download from Roboflow:\n"
            "  https://universe.roboflow.com/valorantai/arc-raiders-8tjh4/model/11\n"
            "  Export YOLOv11 weights -> place best.pt in current directory")

    def detect(self, image):
        # image: path (str/Path) or BGR numpy ndarray from cv2.
        # Ultralytics accepts both; ndarray skips a disk round-trip.
        try:
            results = self.model(image, conf=self.conf, verbose=False)
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
        # Primary blend — YOLO-dominant when both signals agree.
        blended = yolo * 0.65 + pixel * 0.35
        # Safety floor: if pixel strongly signals combat (muzzle flash, fire,
        # damage vignette) but YOLO missed the entities, don't let the blend
        # bury a real highlight. Keeps 80% of the pixel score as a floor.
        f = max(blended, pixel * 0.8) if pixel >= 60 else blended
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

    # Recommended thresholds per scoring version
    VERSION_THRESHOLDS = {
        "v1_strict": 45.0,
        "v2_balanced": 40.0,
        "v3_temporal": 35.0,
        "v4_aggressive": 30.0,
        "v5_combat_only": 40.0,
    }

    def __init__(self, game_id="arc_raiders", weights_path=None,
                 confidence=0.25, device="", threshold=None,
                 scoring_version="v3_temporal", detection_overrides=None,
                 clip_mode=None):
        self.game_id = game_id
        self.weights_path = weights_path
        self.confidence = confidence
        self.device = device
        self.scoring_version = scoring_version
        self.overrides = detection_overrides or {}
        # Clipping mode — gates CV / YOLO / voice paths.
        # Deferred import so legacy callers that don't pass a mode still work
        # if clip_modes.py is missing (won't happen, but defensive).
        try:
            from .clip_modes import ClipMode
            self.clip_mode = ClipMode.parse(clip_mode)
        except Exception:
            self.clip_mode = None
        # Use version-specific threshold if not explicitly set
        if "intensity_threshold" in self.overrides:
            # Detection settings panel override takes priority
            self.threshold = self.overrides["intensity_threshold"] * 100  # normalize 0-1 -> 0-100 for clustering
        elif threshold is not None:
            self.threshold = threshold
        else:
            self.threshold = self.VERSION_THRESHOLDS.get(scoring_version, 40.0)
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

        # Initialize components — gated by clip mode.
        # If caller picked "cv" mode, skip YOLO even if weights exist.
        # If caller picked "yolo" mode, skip pixel-only fallback messaging.
        mode = self.clip_mode
        want_yolo = (mode is None) or mode.uses_yolo
        want_cv = (mode is None) or mode.uses_cv

        detector = None
        if want_yolo and self.has_yolo and YOLO is not None:
            try:
                detector = YOLODetector(
                    logger, weights=self.weights_path,
                    conf=self.confidence, device=self.device)
                print(f"  [ArcClipDetector] mode={mode.value if mode else 'auto'} — YOLO + pixel analysis")
            except Exception as e:
                print(f"  [ArcClipDetector] YOLO init failed ({e}), falling back to pixel-only")
                detector = None

        if detector is None:
            if want_cv:
                print(f"  [ArcClipDetector] mode={mode.value if mode else 'auto'} — pixel analysis only")
            else:
                # YOLO-only mode with no weights — warn but keep pixel as safety net.
                print("  [ArcClipDetector] mode=yolo requested but no weights — falling back to pixel")

        pixel = PixelAnalyzer(logger)
        # Apply menu_suppress override to pixel analyzer
        if self.overrides.get("menu_suppress") == "off":
            pixel.menu_suppress = False
            print("  [ArcClipDetector] [Override] menu_suppress = off")
        else:
            pixel.menu_suppress = True

        scorer = ScoringEngine()
        version = self.scoring_version
        print(f"  [ArcClipDetector] Scoring version: {version} (threshold: {self.threshold})")

        # Apply overrides
        ov = self.overrides
        if ov:
            for k, v in ov.items():
                if k not in ("menu_suppress",):
                    print(f"  [ArcClipDetector] [Override] {k} = {v}")

        # Pixel-only mode: use the version's recommended threshold
        threshold = self.threshold if detector else self.VERSION_THRESHOLDS.get(version, 35.0)

        # Clusterer with overridable merge_gap, min/max clip duration
        merge_gap = ov.get("merge_gap", 5)
        min_d = ov.get("min_clip_duration", 3)
        max_d = ov.get("max_clip_duration", 60)
        clusterer = Clusterer(logger, thresh=threshold, gap=merge_gap, min_d=min_d, max_d=max_d)

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or math.isnan(fps) or fps <= 0:
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if total_frames > 0 else 0.0
        # sample_fps override: convert FPS to interval (e.g., 2 fps = 0.5s interval)
        sample_interval = self.SAMPLE_INTERVAL
        if "sample_fps" in ov:
            sample_interval = 1.0 / max(1, ov["sample_fps"])
        frame_skip = max(1, int(fps * sample_interval))

        print(f"  [ArcClipDetector] Analyzing {video_path} ({duration:.0f}s)")

        # Analyze frames
        analyses = []
        frame_idx = 0

        try:
            while True:
                # Fast-skip non-sampled frames: grab() maintains stream state but
                # avoids the cvtColor + numpy copy that read() performs.
                if frame_idx % frame_skip != 0:
                    if not cap.grab():
                        break
                    if progress_callback and total_frames > 0:
                        progress_callback(min(frame_idx / total_frames, 1.0))
                    frame_idx += 1
                    continue

                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_idx / fps

                # YOLO detection (if available)
                dets = []
                yolo_score = 0.0
                counts = {}
                rules = []

                if detector is not None:
                    dets = detector.detect(frame)
                    yolo_score, counts, rules = scorer.score_yolo(dets)

                # Pixel analysis — skipped in YOLO-only mode (saves ~30% wall time
                # when YOLO is the sole signal). Always runs otherwise, including
                # as the fallback when YOLO is unavailable.
                if want_cv or detector is None:
                    px = pixel.analyze(frame)
                    px_score = pixel.score(px, version=version)
                else:
                    px = {}
                    px_score = 0.0

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
            min_clip = ov.get("min_clip_duration", 20)
            max_clip = ov.get("max_clip_duration", 60)
            clip_duration = max(min_clip, min(max_clip, clip_duration + 10))

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
