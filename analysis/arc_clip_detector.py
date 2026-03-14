#!/usr/bin/env python3
"""
ARC RAIDERS TWITCH STREAM — AUTOMATIC CLIP DETECTION PIPELINE

PURE COMPUTER VISION — No API keys required for analysis.

Production CV system that analyzes ARC Raiders Twitch VODs to automatically
identify and extract clip-worthy moments using:

- YOLOv11l instance segmentation (Roboflow model, runs LOCALLY)
- OpenCV pixel-level analysis (HUD reading, VFX detection, screen states)
- Heuristic scoring engine (entity profiles, combination rules)
- Temporal clustering (groups frames into clips)
- ffmpeg clip cutting

ROBOFLOW MODEL (runs locally — no API calls during analysis):
Dataset: Arc Raiders v13 v0.11 — 4,067 images, YOLOv11 format, 640x640
Model:   arc-raiders-8tjh4/11 — YOLOv11l instance segmentation, 80.1% mAP@50
Classes: 19 (bastion, bombardier, fireball, hornet, leaper, pop, probe,
         queen, raider, raider-down, rocketeer, sentinel, snitch, tick,
         turret, wasp, 0, 1, 5)
Source:  https://universe.roboflow.com/valorantai/arc-raiders-8tjh4

USAGE:

    # Download model weights first (one time):
    python arc_clip_detector.py --download-model

    # Basic — analyze a VOD and output clip report
    python arc_clip_detector.py --input stream.mp4

    # Full pipeline with clip cutting
    python arc_clip_detector.py --input stream.mp4 --output clips/ --cut-clips

    # Fast preview — sample every 2 seconds
    python arc_clip_detector.py --input stream.mp4 --sample-interval 2.0

    # High quality — sample every 0.5 seconds with full pixel analysis
    python arc_clip_detector.py --input stream.mp4 --sample-interval 0.5 --full-pixel-analysis

REQUIREMENTS:
    pip install ultralytics opencv-python-headless Pillow tqdm numpy

    System:
    ffmpeg — Required for frame extraction and clip cutting

===================================================================================
"""

import argparse
import colorsys
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
from typing import Optional, Dict, List, Tuple, Any

import cv2
import numpy as np

# Optional imports

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    class tqdm:
        def __init__(self, iterable=None, total=None, desc="", **kw):
            self.iterable = iterable; self.total = total; self.desc = desc; self.n = 0
        def __iter__(self):
            for item in self.iterable:
                yield item; self.n += 1
                if self.total and self.n % max(1, self.total // 20) == 0:
                    print(f"  {self.desc}: {self.n}/{self.total} ({100*self.n/self.total:.0f}%)")
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def update(self, n=1): self.n += n
        def set_postfix_str(self, s): pass

try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# =============================================================================
# YOLO CLASS DEFINITIONS
# =============================================================================
# Exact 19 classes from Roboflow dataset: Arc Raiders v13 v0.11
# Instance Segmentation, YOLOv11 format, 640x640 input
#
# Classes "0", "1", "5" are numeric labels from early annotation iterations.

YOLO_CLASSES = {
    0:  "0",              # Unknown / misc detection (early annotation label)
    1:  "1",              # Unknown / misc detection (early annotation label)
    2:  "5",              # Unknown / misc detection (early annotation label)
    3:  "bastion",        # Massive crab-like 4-legged ARC, turret on top, yellow joint weak points
    4:  "bombardier",     # Bastion-like with mortar launcher + orbiting Spotter drones
    5:  "fireball",       # Rolling sphere that opens to spray fire, orange/yellow flame VFX
    6:  "hornet",         # Larger armored drone, 2 armored front rotors, stun/taser rounds
    7:  "leaper",         # 4-legged jumping ARC (Bison), shockwave on landing
    8:  "pop",            # Tiny rolling taser bots, electric sparks, swarms
    9:  "probe",          # ARC Probe — large pod from sky, breachable, alarm siren VFX
    10: "queen",          # COLOSSAL boss — laser beam, ground slams, EMP, spawns ARC
    11: "raider",         # Human player character — alive, upright, in action
    12: "raider-down",    # Human player character — downed/crawling/dead state
    13: "rocketeer",      # Large flying ARC with rocket launchers, massive explosion VFX
    14: "sentinel",       # Stationary sniper ARC, targeting laser before heavy shot
    15: "snitch",         # Unarmed high-altitude scout drone, calls reinforcements
    16: "tick",           # Tiny spider-bot, hides on walls/ceilings, leaps onto player head
    17: "turret",         # Fixed gun emplacement, blue scan light turns red when locked
    18: "wasp",           # Small quadcopter drone with machine gun, rotors break off
}

YOLO_CLASS_NAMES = list(YOLO_CLASSES.values())
YOLO_NAME_TO_ID = {v: k for k, v in YOLO_CLASSES.items()}

# =============================================================================
# ENTITY PROFILES — Clip-worthiness scoring per entity type
# =============================================================================
# Derived from analysis of 4,067 annotated frames and ARC Raiders game mechanics.
#
# base_score:        How exciting is seeing this entity (0-100)
# combat_multiplier: Multiplier when near other combat entities
# count_bonus:       Extra score per additional instance beyond first
# category:          Default clip category this entity produces
# size_class:        Expected screen size (tiny/small/medium/large/colossal)
# is_boss:           True = ANY detection means always clip
# threat_level:      low / medium / high / extreme

ENTITY_PROFILES = {
    "pop": {
        "base_score": 8, "combat_multiplier": 1.5, "count_bonus": 5,
        "category": "funny_wtf", "size_class": "tiny", "is_boss": False,
        "threat_level": "low",
    },
    "fireball": {
        "base_score": 15, "combat_multiplier": 2.0, "count_bonus": 8,
        "category": "combat_highlight", "size_class": "small", "is_boss": False,
        "threat_level": "low",
    },
    "tick": {
        "base_score": 30, "combat_multiplier": 3.0, "count_bonus": 15,
        "category": "funny_wtf", "size_class": "tiny", "is_boss": False,
        "threat_level": "medium",
    },
    "wasp": {
        "base_score": 10, "combat_multiplier": 1.5, "count_bonus": 4,
        "category": "combat_highlight", "size_class": "small", "is_boss": False,
        "threat_level": "low",
    },
    "hornet": {
        "base_score": 18, "combat_multiplier": 2.0, "count_bonus": 8,
        "category": "combat_highlight", "size_class": "small", "is_boss": False,
        "threat_level": "medium",
    },
    "snitch": {
        "base_score": 25, "combat_multiplier": 2.5, "count_bonus": 0,
        "category": "close_call", "size_class": "small", "is_boss": False,
        "threat_level": "high",
    },
    "rocketeer": {
        "base_score": 45, "combat_multiplier": 2.5, "count_bonus": 20,
        "category": "combat_highlight", "size_class": "large", "is_boss": False,
        "threat_level": "high",
    },
    "bastion": {
        "base_score": 55, "combat_multiplier": 2.0, "count_bonus": 30,
        "category": "epic_moment", "size_class": "large", "is_boss": False,
        "threat_level": "high",
    },
    "leaper": {
        "base_score": 60, "combat_multiplier": 2.5, "count_bonus": 25,
        "category": "epic_moment", "size_class": "large", "is_boss": False,
        "threat_level": "high",
    },
    "bombardier": {
        "base_score": 65, "combat_multiplier": 2.5, "count_bonus": 25,
        "category": "epic_moment", "size_class": "large", "is_boss": False,
        "threat_level": "extreme",
    },
    "turret": {
        "base_score": 15, "combat_multiplier": 2.5, "count_bonus": 5,
        "category": "close_call", "size_class": "small", "is_boss": False,
        "threat_level": "medium",
    },
    "sentinel": {
        "base_score": 25, "combat_multiplier": 3.0, "count_bonus": 10,
        "category": "close_call", "size_class": "medium", "is_boss": False,
        "threat_level": "high",
    },
    "probe": {
        "base_score": 20, "combat_multiplier": 2.0, "count_bonus": 5,
        "category": "loot_discovery", "size_class": "medium", "is_boss": False,
        "threat_level": "medium",
    },
    "queen": {
        "base_score": 95, "combat_multiplier": 1.2, "count_bonus": 0,
        "category": "boss_fight", "size_class": "colossal", "is_boss": True,
        "threat_level": "extreme",
    },
    "raider": {
        "base_score": 5, "combat_multiplier": 3.0, "count_bonus": 10,
        "category": "pvp_encounter", "size_class": "medium", "is_boss": False,
        "threat_level": "variable",
    },
    "raider-down": {
        "base_score": 35, "combat_multiplier": 1.5, "count_bonus": 20,
        "category": "death_fail", "size_class": "medium", "is_boss": False,
        "threat_level": "n/a",
    },
    "0": {"base_score": 5, "combat_multiplier": 1.0, "count_bonus": 2,
          "category": "routine", "size_class": "unknown", "is_boss": False, "threat_level": "unknown"},
    "1": {"base_score": 5, "combat_multiplier": 1.0, "count_bonus": 2,
          "category": "routine", "size_class": "unknown", "is_boss": False, "threat_level": "unknown"},
    "5": {"base_score": 5, "combat_multiplier": 1.0, "count_bonus": 2,
          "category": "routine", "size_class": "unknown", "is_boss": False, "threat_level": "unknown"},
}

# =============================================================================
# COMBINATION RULES — Multi-entity situation detection
# =============================================================================

COMBINATION_RULES = [
    {
        "name": "pvp_firefight",
        "condition": lambda c: c.get("raider", 0) >= 3,
        "bonus": 40, "category": "pvp_encounter",
    },
    {
        "name": "pvp_kill",
        "condition": lambda c: c.get("raider", 0) >= 1 and c.get("raider-down", 0) >= 1,
        "bonus": 55, "category": "pvp_encounter",
    },
    {
        "name": "squad_wipe",
        "condition": lambda c: c.get("raider-down", 0) >= 2,
        "bonus": 65, "category": "epic_moment",
    },
    {
        "name": "boss_encounter",
        "condition": lambda c: c.get("queen", 0) >= 1,
        "bonus": 95, "category": "boss_fight",
    },
    {
        "name": "heavy_combat",
        "condition": lambda c: (
            (c.get("bastion", 0) + c.get("leaper", 0) + c.get("bombardier", 0)) >= 1
            and c.get("raider", 0) >= 1
        ),
        "bonus": 50, "category": "epic_moment",
    },
    {
        "name": "aerial_chaos",
        "condition": lambda c: (
            c.get("rocketeer", 0) >= 1
            and (c.get("wasp", 0) + c.get("hornet", 0)) >= 2
        ),
        "bonus": 45, "category": "combat_highlight",
    },
    {
        "name": "swarm_attack",
        "condition": lambda c: (
            c.get("pop", 0) + c.get("fireball", 0) + c.get("tick", 0) + c.get("wasp", 0) >= 5
        ),
        "bonus": 35, "category": "funny_wtf",
    },
    {
        "name": "tick_facehugger",
        "condition": lambda c: c.get("tick", 0) >= 1 and c.get("raider", 0) >= 1,
        "bonus": 40, "category": "funny_wtf",
    },
    {
        "name": "probe_breach_chaos",
        "condition": lambda c: (
            c.get("probe", 0) >= 1
            and sum(c.get(e, 0) for e in ["wasp", "hornet", "bastion", "leaper", "rocketeer"]) >= 2
        ),
        "bonus": 40, "category": "close_call",
    },
    {
        "name": "total_chaos",
        "condition": lambda c: sum(c.values()) >= 8,
        "bonus": 50, "category": "epic_moment",
    },
    {
        "name": "pvpve_clash",
        "condition": lambda c: (
            c.get("raider", 0) >= 2
            and (c.get("bastion", 0) + c.get("leaper", 0) + c.get("rocketeer", 0) + c.get("queen", 0)) >= 1
            and c.get("raider-down", 0) >= 1
        ),
        "bonus": 80, "category": "epic_moment",
    },
]

# =============================================================================
# PIXEL-LEVEL HUD / VFX ANALYZER (Pure OpenCV — no API)
# =============================================================================


class PixelAnalyzer:
    """
    Pure OpenCV pixel-level analysis of ARC Raiders gameplay frames.

    No API calls. Reads raw pixel values to detect HUD state, VFX,
    screen states, and visual indicators that YOLO doesn't cover.

    All analysis regions are defined as normalized coordinates (0.0 - 1.0)
    so they work at any resolution.
    """

    # HUD REGION DEFINITIONS (normalized coordinates)
    HEALTH_BAR_REGION = (0.02, 0.88, 0.22, 0.96)
    AMMO_REGION = (0.78, 0.88, 0.98, 0.96)
    KILL_FEED_REGION = (0.60, 0.02, 0.98, 0.20)
    MINIMAP_REGION = (0.02, 0.02, 0.18, 0.18)
    CENTER_REGION = (0.35, 0.35, 0.65, 0.65)
    EDGE_LEFT = (0.00, 0.20, 0.05, 0.80)
    EDGE_RIGHT = (0.95, 0.20, 1.00, 0.80)
    EDGE_TOP = (0.20, 0.00, 0.80, 0.05)
    EDGE_BOTTOM = (0.20, 0.95, 0.80, 1.00)

    # COLOR THRESHOLDS (HSV ranges)
    HEALTH_GREEN_HSV = ((35, 100, 100), (85, 255, 255))
    HEALTH_YELLOW_HSV = ((15, 100, 100), (35, 255, 255))
    HEALTH_RED_HSV = ((0, 100, 100), (15, 255, 255))
    HEALTH_RED2_HSV = ((165, 100, 100), (180, 255, 255))
    SHIELD_BLUE_HSV = ((90, 80, 100), (130, 255, 255))
    FIRE_ORANGE_HSV = ((5, 150, 200), (25, 255, 255))
    FIRE_YELLOW_HSV = ((20, 150, 200), (40, 255, 255))
    FLASH_BRIGHT_THRESHOLD = 240
    VIGNETTE_RED_HSV = ((0, 50, 30), (15, 255, 150))
    VIGNETTE_RED2_HSV = ((165, 50, 30), (180, 255, 150))
    SCANNER_RED_HSV = ((0, 150, 150), (10, 255, 255))
    SCANNER_YELLOW_HSV = ((15, 150, 150), (35, 255, 255))
    SCANNER_BLUE_HSV = ((100, 100, 150), (130, 255, 255))
    DEATH_SCREEN_BRIGHTNESS_MAX = 60
    DEATH_SCREEN_SATURATION_MAX = 40
    MENU_VARIANCE_MAX = 15

    def __init__(self, logger: logging.Logger, full_analysis: bool = True):
        self.logger = logger
        self.full_analysis = full_analysis

    def _get_region(self, frame: np.ndarray, region: tuple) -> np.ndarray:
        """Extract a sub-region from frame using normalized coordinates."""
        h, w = frame.shape[:2]
        x1 = int(region[0] * w)
        y1 = int(region[1] * h)
        x2 = int(region[2] * w)
        y2 = int(region[3] * h)
        return frame[y1:y2, x1:x2]

    def _count_color_pixels(self, region_bgr: np.ndarray,
                            hsv_low: tuple, hsv_high: tuple) -> float:
        """Count percentage of pixels in HSV range within a region."""
        if region_bgr.size == 0:
            return 0.0
        hsv = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(hsv_low), np.array(hsv_high))
        return np.count_nonzero(mask) / mask.size

    def _avg_brightness(self, region_bgr: np.ndarray) -> float:
        if region_bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def _avg_saturation(self, region_bgr: np.ndarray) -> float:
        if region_bgr.size == 0:
            return 0.0
        hsv = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2HSV)
        return float(np.mean(hsv[:, :, 1]))

    def _pixel_variance(self, region_bgr: np.ndarray) -> float:
        if region_bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.var(gray))

    def _bright_pixel_pct(self, region_bgr: np.ndarray, threshold: int = 240) -> float:
        if region_bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
        return np.count_nonzero(gray > threshold) / gray.size

    def analyze_health(self, frame: np.ndarray) -> dict:
        region = self._get_region(frame, self.HEALTH_BAR_REGION)
        green_pct = self._count_color_pixels(region, *self.HEALTH_GREEN_HSV)
        yellow_pct = self._count_color_pixels(region, *self.HEALTH_YELLOW_HSV)
        red_pct = (self._count_color_pixels(region, *self.HEALTH_RED_HSV)
                   + self._count_color_pixels(region, *self.HEALTH_RED2_HSV))
        blue_pct = self._count_color_pixels(region, *self.SHIELD_BLUE_HSV)

        total_health_color = green_pct + yellow_pct + red_pct
        if total_health_color < 0.01:
            state = "unknown"
        elif red_pct > 0.3:
            state = "critical"
        elif yellow_pct > green_pct:
            state = "damaged"
        elif green_pct > 0.1:
            state = "full"
        else:
            state = "empty"

        return {
            "health_state": state,
            "shield_present": blue_pct > 0.05,
            "health_green_pct": round(green_pct, 4),
            "health_red_pct": round(red_pct, 4),
            "shield_blue_pct": round(blue_pct, 4),
        }

    def analyze_vfx(self, frame: np.ndarray) -> dict:
        fire_orange = self._count_color_pixels(frame, *self.FIRE_ORANGE_HSV)
        fire_yellow = self._count_color_pixels(frame, *self.FIRE_YELLOW_HSV)
        fire_total = fire_orange + fire_yellow
        has_fire = fire_total > 0.03

        center = self._get_region(frame, self.CENTER_REGION)
        flash_pct = self._bright_pixel_pct(center, self.FLASH_BRIGHT_THRESHOLD)
        has_muzzle_flash = flash_pct > 0.02

        overall_brightness = self._avg_brightness(frame)
        has_screen_flash = overall_brightness > 200

        edges = [
            self._get_region(frame, self.EDGE_LEFT),
            self._get_region(frame, self.EDGE_RIGHT),
            self._get_region(frame, self.EDGE_TOP),
            self._get_region(frame, self.EDGE_BOTTOM),
        ]
        edge_red_total = 0.0
        for edge in edges:
            edge_red_total += self._count_color_pixels(edge, *self.VIGNETTE_RED_HSV)
            edge_red_total += self._count_color_pixels(edge, *self.VIGNETTE_RED2_HSV)
        has_damage_vignette = edge_red_total > 0.15

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        small_bright_spots = sum(1 for c in contours if 5 < cv2.contourArea(c) < 500)
        has_tracers = small_bright_spots > 10

        return {
            "has_fire": has_fire,
            "fire_intensity": round(fire_total, 4),
            "has_muzzle_flash": has_muzzle_flash,
            "flash_intensity": round(flash_pct, 4),
            "has_screen_flash": has_screen_flash,
            "has_damage_vignette": has_damage_vignette,
            "edge_red_intensity": round(edge_red_total, 4),
            "has_tracers": has_tracers,
            "tracer_count": small_bright_spots,
            "overall_brightness": round(overall_brightness, 2),
        }

    def analyze_screen_state(self, frame: np.ndarray) -> dict:
        avg_bright = self._avg_brightness(frame)
        avg_sat = self._avg_saturation(frame)
        variance = self._pixel_variance(frame)

        if avg_bright < self.DEATH_SCREEN_BRIGHTNESS_MAX and avg_sat < self.DEATH_SCREEN_SATURATION_MAX:
            return {"screen_state": "death_screen", "brightness": avg_bright, "saturation": avg_sat}

        if variance < self.MENU_VARIANCE_MAX:
            return {"screen_state": "loading", "brightness": avg_bright, "variance": variance}

        center = self._get_region(frame, (0.2, 0.2, 0.8, 0.8))
        center_var = self._pixel_variance(center)

        if avg_bright < 40 and center_var > 500:
            health = self._get_region(frame, self.HEALTH_BAR_REGION)
            health_bright = self._avg_brightness(health)
            if health_bright < 20:
                return {"screen_state": "menu", "brightness": avg_bright, "variance": variance}

        return {"screen_state": "gameplay", "brightness": avg_bright, "saturation": avg_sat, "variance": variance}

    def analyze_kill_feed(self, frame: np.ndarray) -> dict:
        region = self._get_region(frame, self.KILL_FEED_REGION)
        if region.size == 0:
            return {"kill_feed_active": False, "kill_feed_intensity": 0.0}

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        bright_pct = np.count_nonzero(gray > 200) / gray.size
        dark_pct = np.count_nonzero(gray < 50) / gray.size
        has_text = bright_pct > 0.02 and dark_pct > 0.3

        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.count_nonzero(edges) / edges.size

        return {
            "kill_feed_active": has_text and edge_density > 0.05,
            "kill_feed_intensity": round(edge_density, 4),
        }

    def analyze_motion_blur(self, frame: np.ndarray) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        has_motion_blur = laplacian_var < 200
        return {
            "has_motion_blur": has_motion_blur,
            "sharpness": round(laplacian_var, 2),
        }

    def analyze_color_intensity(self, frame: np.ndarray) -> dict:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        avg_sat = float(np.mean(hsv[:, :, 1]))
        avg_val = float(np.mean(hsv[:, :, 2]))
        val_std = float(np.std(hsv[:, :, 2]))
        drama = (avg_sat / 255.0) * 0.4 + (val_std / 128.0) * 0.6
        drama = min(1.0, drama)
        return {
            "avg_saturation": round(avg_sat, 2),
            "avg_brightness": round(avg_val, 2),
            "brightness_std": round(val_std, 2),
            "drama_score": round(drama, 4),
        }

    def full_analyze(self, frame: np.ndarray) -> dict:
        result = {}
        result.update(self.analyze_health(frame))
        result.update(self.analyze_vfx(frame))
        result.update(self.analyze_screen_state(frame))
        result.update(self.analyze_kill_feed(frame))
        if self.full_analysis:
            result.update(self.analyze_motion_blur(frame))
            result.update(self.analyze_color_intensity(frame))
        return result

    def score_pixels(self, pixel_result: dict) -> float:
        score = 0.0

        health = pixel_result.get("health_state", "unknown")
        if health == "critical":
            score += 25
        elif health == "damaged":
            score += 10
        elif health == "empty":
            score += 15

        if pixel_result.get("has_fire"):
            score += 20 * min(1.0, pixel_result.get("fire_intensity", 0) * 10)
        if pixel_result.get("has_muzzle_flash"):
            score += 12
        if pixel_result.get("has_screen_flash"):
            score += 18
        if pixel_result.get("has_damage_vignette"):
            score += 15
        if pixel_result.get("has_tracers"):
            score += 10 + min(10, pixel_result.get("tracer_count", 0) * 0.5)

        if pixel_result.get("kill_feed_active"):
            score += 15

        state = pixel_result.get("screen_state", "gameplay")
        if state == "death_screen":
            score += 20
        elif state in ("menu", "loading"):
            score = 0
            return score

        if pixel_result.get("has_motion_blur"):
            score += 8

        drama = pixel_result.get("drama_score", 0)
        score += drama * 15

        return min(100, score)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Detection:
    """Single YOLO detection."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    bbox_area_pct: float
    mask_points: Optional[List[Tuple[float, float]]] = None

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.bbox[0]+self.bbox[2])/2, (self.bbox[1]+self.bbox[3])/2)

    @property
    def width(self) -> float: return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float: return self.bbox[3] - self.bbox[1]


@dataclass
class FrameAnalysis:
    """Complete analysis of a single frame."""
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
    def has_pvp(self): return self.entity_counts.get("raider", 0) >= 2
    @property
    def has_downed(self): return self.entity_counts.get("raider-down", 0) > 0
    @property
    def total_entities(self): return sum(self.entity_counts.values())

    def to_dict(self):
        d = asdict(self)
        d["detections"] = [asdict(det) for det in self.detections]
        return d


@dataclass
class ClipSegment:
    """Contiguous segment of high-scoring frames forming a clip."""
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
            "clip_id": self.clip_id, "start_time": self.start_time,
            "end_time": self.end_time, "start_str": self.start_str,
            "end_str": self.end_str, "duration": round(self.duration, 2),
            "peak_score": round(self.peak_score, 2), "avg_score": round(self.avg_score, 2),
            "frame_count": self.frame_count, "primary_category": self.primary_category,
            "entities_seen": self.entities_seen, "triggered_rules": self.triggered_rules,
        }


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging(verbose=False):
    logger = logging.getLogger("arc_clip_detector")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    return logger


# =============================================================================
# VIDEO PROCESSOR
# =============================================================================

class VideoProcessor:
    def __init__(self, input_path: str, logger: logging.Logger):
        self.input_path = Path(input_path)
        self.logger = logger
        if not self.input_path.exists():
            raise FileNotFoundError(f"Video not found: {input_path}")
        self.meta = self._get_metadata()
        self.fps = self.meta["fps"]
        self.total_frames = self.meta["total_frames"]
        self.duration = self.meta["duration"]
        self.width = self.meta["width"]
        self.height = self.meta["height"]
        self.logger.info(f"Video: {self.input_path.name} | {self.width}x{self.height} | "
                         f"{self.fps:.1f}fps | {timedelta(seconds=int(self.duration))}")

    def _get_metadata(self):
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
                 str(self.input_path)], capture_output=True, text=True, check=True)
            data = json.loads(r.stdout)
            vs = next(s for s in data["streams"] if s["codec_type"] == "video")
            fps_p = vs["r_frame_rate"].split("/")
            fps = float(fps_p[0]) / float(fps_p[1]) if len(fps_p) == 2 else float(fps_p[0])
            dur = float(data.get("format", {}).get("duration", vs.get("duration", 0)))
            nf = int(vs.get("nb_frames", 0)) or int(dur * fps)
            return {"fps": fps, "total_frames": nf, "duration": dur,
                    "width": int(vs["width"]), "height": int(vs["height"])}
        except FileNotFoundError:
            raise RuntimeError("ffprobe not found. Install ffmpeg.")

    def extract_frames(self, output_dir: Path, sample_interval: float = 1.0):
        output_dir.mkdir(parents=True, exist_ok=True)
        total = int(self.duration / sample_interval)
        self.logger.info(f"Extracting ~{total} frames (1 every {sample_interval}s)")
        subprocess.run([
            "ffmpeg", "-y", "-v", "quiet", "-i", str(self.input_path),
            "-vf", f"fps=1/{sample_interval}", "-q:v", "2",
            str(output_dir / "frame_%06d.jpg")
        ], check=True)
        frames = []
        for idx, fp in enumerate(sorted(output_dir.glob("frame_*.jpg"))):
            ts = idx * sample_interval
            frames.append((str(fp), ts, int(ts * self.fps)))
        self.logger.info(f"Extracted {len(frames)} frames")
        return frames

    def cut_clip(self, start: float, end: float, output_path: str, pad: float = 2.0):
        s = max(0, start - pad)
        d = min(self.duration, end + pad) - s
        subprocess.run([
            "ffmpeg", "-y", "-v", "quiet", "-ss", str(s), "-i", str(self.input_path),
            "-t", str(d), "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", str(output_path)
        ], check=True)


# =============================================================================
# YOLO DETECTOR (Local inference — no API calls)
# =============================================================================

class YOLODetector:
    """
    Local YOLOv11 inference using ultralytics.

    Downloads model weights from Roboflow on first run, then runs
    entirely locally with no API calls.

    Model: arc-raiders-8tjh4/11 — YOLOv11l, 80.1% mAP@50, 19 classes
    Input: 640x640 (auto-resized by ultralytics)
    """

    def __init__(self, logger: logging.Logger,
                 weights_path: Optional[str] = None,
                 confidence: float = 0.25,
                 iou_threshold: float = 0.45,
                 device: str = ""):
        self.logger = logger
        self.confidence = confidence
        self.iou_threshold = iou_threshold

        if not HAS_ULTRALYTICS:
            raise RuntimeError("ultralytics not installed. Run: pip install ultralytics")

        if weights_path and Path(weights_path).exists():
            self.logger.info(f"Loading YOLO weights: {weights_path}")
            self.model = YOLO(weights_path)
        else:
            default_paths = [
                "arc_raiders_yolov11l.pt",
                "best.pt",
                "runs/segment/train/weights/best.pt",
                "weights/best.pt",
            ]
            loaded = False
            for p in default_paths:
                if Path(p).exists():
                    self.logger.info(f"Loading YOLO weights: {p}")
                    self.model = YOLO(p)
                    loaded = True
                    break
            if not loaded:
                self.logger.error(
                    "No YOLO weights found. Download from Roboflow:\n"
                    "  1. Go to https://universe.roboflow.com/valorantai/arc-raiders-8tjh4/model/11\n"
                    "  2. Export as YOLOv11 weights\n"
                    "  3. Place best.pt in current directory\n"
                    "  Or use --weights-path to specify location"
                )
                raise FileNotFoundError("YOLO weights not found")

        if device:
            self.model.to(device)

    def detect(self, image_path: str) -> List[Detection]:
        """Run inference on a single frame. Returns list of Detection objects."""
        try:
            results = self.model(
                image_path,
                conf=self.confidence,
                iou=self.iou_threshold,
                verbose=False,
            )
        except Exception as e:
            self.logger.warning(f"YOLO inference failed: {e}")
            return []

        detections = []
        for result in results:
            if result.boxes is None:
                continue

            img_h, img_w = result.orig_shape

            for i, box in enumerate(result.boxes):
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                nx1 = x1 / img_w
                ny1 = y1 / img_h
                nx2 = x2 / img_w
                ny2 = y2 / img_h

                area_pct = (nx2 - nx1) * (ny2 - ny1) * 100
                cls_name = YOLO_CLASSES.get(cls_id, f"unknown_{cls_id}")

                mask_pts = None
                if result.masks is not None and i < len(result.masks):
                    try:
                        xy = result.masks[i].xy[0]
                        mask_pts = [(float(p[0])/img_w, float(p[1])/img_h) for p in xy]
                    except (IndexError, AttributeError):
                        pass

                detections.append(Detection(
                    class_id=cls_id, class_name=cls_name, confidence=conf,
                    bbox=(nx1, ny1, nx2, ny2), bbox_area_pct=area_pct,
                    mask_points=mask_pts,
                ))

        return detections


# =============================================================================
# SCORING ENGINE (Pure heuristics — no API)
# =============================================================================

class ScoringEngine:
    """Combines YOLO detections + pixel analysis into clip score."""

    def __init__(self, logger): self.logger = logger

    def score_yolo(self, detections: List[Detection]) -> Tuple[float, Dict[str, int], List[str]]:
        counts = defaultdict(int)
        for d in detections:
            counts[d.class_name] += 1

        score = 0.0
        for name, count in counts.items():
            p = ENTITY_PROFILES.get(name)
            if not p:
                continue
            s = p["base_score"]
            if count > 1:
                s += (count - 1) * p["count_bonus"]
            max_area = max((d.bbox_area_pct for d in detections if d.class_name == name), default=0)
            if max_area > 20: s *= 1.3
            elif max_area > 40: s *= 1.5
            if p["is_boss"]: s = max(s, 90)
            score += s

        triggered = []
        for rule in COMBINATION_RULES:
            if rule["condition"](dict(counts)):
                score += rule["bonus"]
                triggered.append(rule["name"])

        if len(detections) >= 2:
            centers = [d.center for d in detections]
            avg_d = self._avg_dist(centers)
            if avg_d < 0.3: score *= 1.2

        avg_conf = sum(d.confidence for d in detections) / len(detections) if detections else 0
        if avg_conf < 0.5: score *= 0.8

        return min(100, score), dict(counts), triggered

    def combine(self, yolo_score: float, pixel_score: float, has_boss: bool) -> float:
        """Combine YOLO entity score with pixel analysis score. 65/35 weighting."""
        final = yolo_score * 0.65 + pixel_score * 0.35
        if has_boss:
            final = max(final, 85)
        return min(100, final)

    @staticmethod
    def _avg_dist(pts):
        if len(pts) < 2: return 1.0
        t = c = 0
        for i in range(len(pts)):
            for j in range(i+1, len(pts)):
                t += math.sqrt((pts[i][0]-pts[j][0])**2 + (pts[i][1]-pts[j][1])**2)
                c += 1
        return t/c if c else 1.0


# =============================================================================
# TEMPORAL CLUSTERING
# =============================================================================

class TemporalClusterer:
    def __init__(self, logger, threshold=50.0, merge_gap=5.0,
                 min_dur=3.0, max_dur=60.0, pad=2.0):
        self.logger = logger
        self.threshold = threshold
        self.merge_gap = merge_gap
        self.min_dur = min_dur
        self.max_dur = max_dur
        self.pad = pad

    def cluster(self, frames: List[FrameAnalysis]) -> List[ClipSegment]:
        hot = sorted([f for f in frames if f.final_score >= self.threshold],
                     key=lambda f: f.timestamp_seconds)
        if not hot:
            self.logger.info("No frames above clip threshold")
            return []

        self.logger.info(f"{len(hot)} frames above threshold ({self.threshold})")
        clusters, cur = [], [hot[0]]
        for f in hot[1:]:
            if f.timestamp_seconds - cur[-1].timestamp_seconds <= self.merge_gap:
                cur.append(f)
            else:
                clusters.append(cur); cur = [f]
        clusters.append(cur)

        clips = []
        for idx, cf in enumerate(clusters):
            peak = max(cf, key=lambda f: f.final_score)
            s = max(0, cf[0].timestamp_seconds - self.pad)
            e = cf[-1].timestamp_seconds + self.pad
            if (e - s) > self.max_dur:
                c = peak.timestamp_seconds
                s, e = max(0, c - self.max_dur/2), c + self.max_dur/2
            if (e - s) < self.min_dur:
                continue

            ents = defaultdict(int)
            rules = set()
            for f in cf:
                for en, cnt in f.entity_counts.items():
                    ents[en] = max(ents[en], cnt)
                rules.update(f.triggered_rules)

            cats = defaultdict(int)
            for f in cf:
                if f.final_category != "routine": cats[f.final_category] += 1
            pcat = max(cats, key=cats.get) if cats else "combat_highlight"

            clips.append(ClipSegment(
                clip_id=idx+1, start_time=s, end_time=e,
                peak_score=peak.final_score,
                avg_score=sum(f.final_score for f in cf)/len(cf),
                frame_count=len(cf), peak_frame=peak, frames=cf,
                primary_category=pcat, entities_seen=dict(ents),
                triggered_rules=sorted(rules),
            ))

        clips.sort(key=lambda c: c.peak_score, reverse=True)
        self.logger.info(f"Clustered into {len(clips)} clips")
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
                 confidence=0.25, device="", full_pixel_analysis=True,
                 threshold=40.0):
        self.game_id = game_id
        self.weights_path = weights_path
        self.confidence = confidence
        self.device = device
        self.full_pixel_analysis = full_pixel_analysis
        self.threshold = threshold
        self.has_yolo = False

        # Try to find weights — if not found, pixel-only mode
        if self.weights_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates = [
                os.path.join(base, "models", "best.pt"),
                os.path.join(base, "best.pt"),
                os.path.join(base, "arc_raiders_yolov11l.pt"),
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
        if self.has_yolo and HAS_ULTRALYTICS:
            try:
                detector = YOLODetector(
                    logger, weights_path=self.weights_path,
                    confidence=self.confidence, device=self.device)
                print("  [ArcClipDetector] YOLO + OpenCV pixel analysis mode")
            except Exception as e:
                print(f"  [ArcClipDetector] YOLO init failed ({e}), falling back to pixel-only")
                detector = None

        if detector is None:
            print("  [ArcClipDetector] Pure OpenCV pixel analysis mode (no YOLO weights needed)")

        pixel = PixelAnalyzer(logger, full_analysis=self.full_pixel_analysis)
        scorer = ScoringEngine(logger)
        # Lower threshold for pixel-only since scores will be lower without YOLO
        threshold = self.threshold if detector else max(25.0, self.threshold * 0.6)
        clusterer = TemporalClusterer(logger, threshold=threshold)

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
                    px = pixel.full_analyze(frame)
                    px_score = pixel.score_pixels(px)

                    # Category
                    cat = "routine"
                    if rules:
                        best = max(
                            (r for r in COMBINATION_RULES if r["name"] in rules),
                            key=lambda r: r["bonus"], default=None)
                        if best:
                            cat = best["category"]
                    elif counts:
                        best_e = max(counts, key=lambda e: ENTITY_PROFILES.get(e, {}).get("base_score", 0))
                        cat = ENTITY_PROFILES.get(best_e, {}).get("category", "routine")

                    # Pixel-only category detection
                    if px.get("screen_state") == "death_screen":
                        cat = "death_fail"
                    elif px.get("screen_state") in ("menu", "loading"):
                        cat = "downtime"
                    elif not counts:
                        # Pixel-only mode: determine category from pixel signals
                        if px.get("has_fire") or px.get("has_muzzle_flash"):
                            cat = "combat_highlight"
                        elif px.get("has_damage_vignette"):
                            cat = "close_call"
                        elif px.get("has_screen_flash"):
                            cat = "epic_moment"
                        elif px.get("has_tracers"):
                            cat = "combat_highlight"
                        elif px.get("health_state") == "critical":
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
                                  f"health:{px.get('health_state','')} "
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
                if peak_px.get("has_screen_flash"): px_signals.append("Screen Flash")
                if peak_px.get("has_tracers"): px_signals.append("Tracers")
                if peak_px.get("health_state") == "critical": px_signals.append("Critical HP")
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
# MAIN PIPELINE (CLI mode)
# =============================================================================

class ArcRaidersClipDetector:
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging(args.verbose)
        self.video = VideoProcessor(args.input, self.logger)
        self.scorer = ScoringEngine(self.logger)
        self.pixel = PixelAnalyzer(self.logger, full_analysis=args.full_pixel_analysis)
        self.clusterer = TemporalClusterer(
            self.logger, threshold=args.threshold, merge_gap=args.merge_gap,
            min_dur=args.min_clip_duration, max_dur=args.max_clip_duration, pad=args.pad_seconds)
        self.detector = YOLODetector(
            self.logger, weights_path=args.weights_path,
            confidence=args.yolo_confidence, device=args.device)
        self.output_dir = Path(args.output)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        self.logger.info("=" * 70)
        self.logger.info("ARC RAIDERS CLIP DETECTOR — Pure CV Pipeline")
        self.logger.info("=" * 70)

        frames_dir = self.output_dir / "frames"
        frame_list = self.video.extract_frames(frames_dir, self.args.sample_interval)
        analyses = self._analyze_all(frame_list)

        for a in analyses:
            a.final_score = self.scorer.combine(a.yolo_score, a.pixel_score, a.has_boss)

        clips = self.clusterer.cluster(analyses)
        self._export(analyses, clips)

        if self.args.cut_clips and clips:
            self._cut_clips(clips)

        self._summary(clips)
        return clips

    def _analyze_all(self, frame_list):
        self.logger.info(f"\n--- Analyzing {len(frame_list)} frames (YOLO + Pixel) ---")
        analyses = []
        for frame_path, ts, fnum in tqdm(frame_list, desc="Analyzing", total=len(frame_list)):
            dets = self.detector.detect(frame_path)
            yolo_score, counts, rules = self.scorer.score_yolo(dets)

            frame_bgr = cv2.imread(frame_path)
            if frame_bgr is not None:
                px = self.pixel.full_analyze(frame_bgr)
                px_score = self.pixel.score_pixels(px)
            else:
                px, px_score = {}, 0.0

            cat = "routine"
            if rules:
                best = max((r for r in COMBINATION_RULES if r["name"] in rules), key=lambda r: r["bonus"], default=None)
                if best: cat = best["category"]
            elif counts:
                best_e = max(counts, key=lambda e: ENTITY_PROFILES.get(e, {}).get("base_score", 0))
                cat = ENTITY_PROFILES.get(best_e, {}).get("category", "routine")

            if px.get("screen_state") == "death_screen":
                cat = "death_fail"
            elif px.get("screen_state") in ("menu", "loading"):
                cat = "downtime"

            analyses.append(FrameAnalysis(
                frame_number=fnum, timestamp_seconds=ts,
                timestamp_str=str(timedelta(seconds=int(ts))),
                detections=dets, entity_counts=counts,
                yolo_score=yolo_score, pixel_score=px_score,
                pixel_data=px, final_category=cat, triggered_rules=rules,
                image_path=frame_path,
            ))
        return analyses

    def _export(self, analyses, clips):
        with open(self.output_dir / "frame_analysis.json", "w") as f:
            json.dump([a.to_dict() for a in analyses], f, indent=2, default=str)
        with open(self.output_dir / "clips.json", "w") as f:
            json.dump([c.to_dict() for c in clips], f, indent=2, default=str)
        if clips:
            with open(self.output_dir / "clips.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=clips[0].to_dict().keys())
                w.writeheader()
                for c in clips: w.writerow(c.to_dict())
        with open(self.output_dir / "timeline.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "ts_str", "yolo_score", "pixel_score",
                         "final_score", "category", "entities", "rules",
                         "health", "fire", "vignette", "screen_state"])
            for a in analyses:
                px = a.pixel_data or {}
                w.writerow([
                    f"{a.timestamp_seconds:.2f}", a.timestamp_str,
                    f"{a.yolo_score:.1f}", f"{a.pixel_score:.1f}", f"{a.final_score:.1f}",
                    a.final_category,
                    "|".join(f"{k}:{v}" for k, v in a.entity_counts.items()),
                    "|".join(a.triggered_rules),
                    px.get("health_state", ""), str(px.get("has_fire", "")),
                    str(px.get("has_damage_vignette", "")), px.get("screen_state", ""),
                ])
        self.logger.info(f"Results saved to: {self.output_dir}")

    def _cut_clips(self, clips):
        d = self.output_dir / "clips"
        d.mkdir(exist_ok=True)
        self.logger.info(f"\nCutting {len(clips)} clips...")
        for c in tqdm(clips, desc="Cutting"):
            fn = f"clip_{c.clip_id:03d}_score{c.peak_score:.0f}_{c.primary_category}_{c.start_str.replace(':','-')}.mp4"
            self.video.cut_clip(c.start_time, c.end_time, str(d/fn), self.args.pad_seconds)
        self.logger.info(f"Clips saved to: {d}")

    def _summary(self, clips):
        print("\n" + "=" * 70)
        print("CLIP DETECTION SUMMARY")
        print("=" * 70)
        print(f"Video: {self.video.input_path.name}")
        print(f"Duration: {timedelta(seconds=int(self.video.duration))}")
        print(f"Clips found: {len(clips)}\n")
        if not clips:
            print("No clips detected."); return
        for c in clips[:25]:
            print(f"  #{c.clip_id:3d}  [{c.start_str} -> {c.end_str}]  "
                  f"Score: {c.peak_score:5.1f}  {c.primary_category:<18s}  "
                  f"{', '.join(f'{k}({v})' for k,v in c.entities_seen.items())}")
            if c.triggered_rules:
                print(f"         Rules: {', '.join(c.triggered_rules)}")
        if len(clips) > 25: print(f"\n  ... +{len(clips)-25} more")
        print("\nCategories:")
        cc = defaultdict(int)
        for c in clips: cc[c.primary_category] += 1
        for cat, n in sorted(cc.items(), key=lambda x: -x[1]):
            print(f"  {cat:<20s}: {n}")
        print()


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description="ARC Raiders Clip Detector (Pure CV)")
    p.add_argument("--input", "-i", required=True, help="Input video file")
    p.add_argument("--output", "-o", default="arc_clips_output", help="Output directory")
    p.add_argument("--cut-clips", action="store_true", help="Cut video clips with ffmpeg")
    p.add_argument("--sample-interval", type=float, default=1.0, help="Seconds between samples (default: 1.0)")
    p.add_argument("--weights-path", default=None, help="Path to YOLO .pt weights file")
    p.add_argument("--yolo-confidence", type=float, default=0.25, help="YOLO confidence threshold")
    p.add_argument("--device", default="", help="YOLO device: '' (auto), 'cpu', 'cuda:0'")
    p.add_argument("--full-pixel-analysis", action="store_true", help="Enable motion blur + color drama analysis")
    p.add_argument("--threshold", type=float, default=50.0, help="Min score for clipping (default: 50)")
    p.add_argument("--merge-gap", type=float, default=5.0, help="Max gap to merge frames into one clip")
    p.add_argument("--min-clip-duration", type=float, default=3.0, help="Min clip duration")
    p.add_argument("--max-clip-duration", type=float, default=60.0, help="Max clip duration")
    p.add_argument("--pad-seconds", type=float, default=2.0, help="Padding before/after clip")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    pipeline = ArcRaidersClipDetector(args)
    clips = pipeline.run()
    return 0 if clips else 1


if __name__ == "__main__":
    sys.exit(main())
