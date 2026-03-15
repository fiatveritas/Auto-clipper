"""
Game-specific detection profiles for the Auto-Clipper.

Each profile defines:
- Color ranges (HSV) for detecting game-specific visual elements
- Screen regions where those elements appear
- Detection weights (what matters most in each game)
- Scoring multipliers and thresholds
- AI prompt text for Grok Vision analysis
"""

import numpy as np


GAME_PROFILES = {
    "arc_raiders": {
        "name": "Arc Raiders",
        "description": "Simple detection \u2014 Recommended, works best for most streams",

        # NOTE: Arc Raiders has NO kill feed. Deaths emit a RED FLARE in the sky.
        # It's a THIRD-PERSON shooter. No traditional hit markers exist.
        # The original v1 worked well despite "wrong" detectors because:
        # - The broad color ranges catch real combat signals (explosions, flashes)
        # - Simple scoring without penalties lets signals through
        # Keep it simple — that's why it works.
        "detectors": {
            "combat_flash": {
                "label": "Combat / Muzzle Flash",
                "weight": 0.25,
                # Muzzle flash + explosions: orange-yellow bursts
                # Third-person: flash appears on character model (lower-center)
                # Raised sat floor 100->130 to reduce false positives from
                # warm ambient lighting (campfires, sunsets, indoor lamps)
                "lower": np.array([10, 130, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red directional damage indicators + vignette at screen edges
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.15,
                # White health bar + blue segmented shield boxes, bottom-left HUD
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    # White health bar
                    {"lower": np.array([0, 0, 180]), "upper": np.array([180, 40, 255])},
                    # Blue shield segments
                    {"lower": np.array([90, 60, 100]), "upper": np.array([130, 255, 255])},
                ],
                "depletion_threshold": 0.10,
                "multiplier": 6,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.15,
                # When a player dies, a bright RED FLARE shoots skyward
                # Visible from across the map — the game's "kill notification"
                "lower": np.array([0, 150, 180]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 150, 180]),
                "upper2": np.array([180, 255, 255]),
                # Upper portion of screen where flares appear
                "region": [0.0, 0.50, 0.10, 0.90],
                "multiplier": 6,
            },
            "red_scanner": {
                "label": "ARC Enemy Aggro",
                "weight": 0.15,
                # ARC scanner beams turn RED when attacking
                # Universal across all ARC types (Wasps, Bastions, Turrets, etc.)
                "lower": np.array([0, 140, 150]),
                "upper": np.array([8, 255, 255]),
                "lower2": np.array([172, 140, 150]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.10, 0.75, 0.10, 0.90],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.15,
                # Bright explosions, grenade blasts, ARC self-destruct
                "lower": np.array([5, 150, 170]),
                "upper": np.array([25, 255, 255]),
                "region": [0.20, 0.90, 0.10, 0.90],
                "multiplier": 5,
            },
        },

        # Audio: helpful but don't let it dominate
        "audio_weight": 0.30,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,

        # Motion
        "motion_weight": 0.10,
        "motion_multiplier": 3,

        # Brightness spike
        "brightness_weight": 0.05,
        "brightness_threshold": 0.6,
        "brightness_multiplier": 3,

        # Scoring — original v1 values
        "intensity_threshold": 0.35,
        "fallback_threshold_ratio": 0.5,
        "merge_gap": 8,
        "min_clip_duration": 20,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 8,

        # AI prompt
        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. You analyze screenshots from Arc Raiders streams to identify exciting moments worth clipping.

Look for these types of highlights:
- **Kills**: Player eliminating Arc enemies (robots), leapers, or other threats
- **Combat**: Active gunfights, shooting at enemies, taking fire
- **Arc Encounters**: Large Arc enemy appearances, boss-like encounters
- **Explosions**: Big explosions, grenades, environmental destruction
- **Close Calls**: Player at low health, narrow escapes
- **Loot/Rewards**: Finding rare loot, extraction moments
- **Deaths**: Player dying (also exciting/funny content)

Score 0.0 for: menus, inventory screens, loading screens, lobbies, settings UI.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.0 = menu/nothing happening, 0.3 = minor action, 0.6 = good combat, 0.8 = kill/major moment, 1.0 = insane play""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    # ===== ARC RAIDERS V2 — Research-based detection =====
    # Built from deep research of Arc Raiders HUD, enemy visuals, and combat feedback.
    # Key findings:
    #   - THIRD-PERSON shooter — muzzle flash on character model, not center screen
    #   - NO kill feed — deaths emit a RED FLARE skyward (visible across map)
    #   - NO hit markers — crosshair is dynamic (tightens on ADS)
    #   - NO enemy HP bars — physics feedback (stagger, parts breaking off, sparks)
    #   - Health bar (WHITE) bottom-left, shield = BLUE SEGMENTED BOXES above it
    #   - Shield = damage REDUCTION (not a second health pool)
    #   - Red DIRECTIONAL damage indicators point toward damage source
    #   - Enemy scanner beam: White→Blue→Yellow→RED when attacking
    #   - Weak points glow YELLOW (Bastion kneecaps, Rocketeer core, Wasp thrusters)
    #   - Session ID watermark always visible bottom-right (white text, ignore it)
    #   - Stamina bar shrinks from middle, disappears when empty
    # Sources: ARC Raiders Wiki, GameRant, GamingBolt, Steam Community, NerdSchalk,
    #   Beebom, GameSpot, Epiccarry, NeonLightsMedia, The Escapist, Kotaku
    "arc_raiders_v2": {
        "name": "Arc Raiders v2 (Refined)",
        "description": "Research-based detection \u2014 wider color ranges, better audio blend, fewer false negatives",

        "detectors": {
            "muzzle_flash": {
                "label": "Gunfire / Muzzle Flash",
                "weight": 0.22,
                # THIRD-PERSON: muzzle flash on character model
                # Widened hue range to catch energy weapons (bluer flash)
                # Lowered sat floor to catch washed-out muzzle flashes in bright areas
                "lower": np.array([8, 100, 170]),
                "upper": np.array([35, 255, 255]),
                # White/blue energy weapon flash
                "lower2": np.array([0, 0, 230]),
                "upper2": np.array([180, 50, 255]),
                # Wider region — character can be left/right depending on camera
                "region": [0.35, 0.90, 0.25, 0.85],
                "multiplier": 5,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.12,
                # Bright RED FLARE skyward on player death
                # Widened sat range — flares can be partially washed out at distance
                "lower": np.array([0, 130, 160]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 130, 160]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.0, 0.55, 0.05, 0.95],
                "multiplier": 7,
            },
            "red_scanner": {
                "label": "ARC Enemy Aggro",
                "weight": 0.15,
                # ARC scanner beams turn RED when attacking
                # Slightly wider hue range to catch orange-red transition
                "lower": np.array([0, 130, 140]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 130, 140]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.08, 0.80, 0.08, 0.92],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.12,
                # Large explosions, grenades, ARC self-destruct
                # Added wider region and slightly lower sat floor
                "lower": np.array([5, 130, 160]),
                "upper": np.array([28, 255, 255]),
                "region": [0.20, 0.92, 0.10, 0.90],
                "multiplier": 5,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.13,
                # WHITE health bar + BLUE SEGMENTED shield boxes — bottom-left HUD
                "region": "health_bar",
                "bar_region": [0.86, 0.96, 0.01, 0.24],
                "bar_colors": [
                    {"lower": np.array([0, 0, 170]), "upper": np.array([180, 45, 255])},
                    {"lower": np.array([85, 50, 90]), "upper": np.array([135, 255, 255])},
                ],
                "depletion_threshold": 0.08,
                "multiplier": 6,
            },
            "damage_indicators": {
                "label": "Taking Damage",
                "weight": 0.11,
                # Red directional indicators + vignette
                # Wider edge region to catch more subtle indicators
                "lower": np.array([0, 110, 90]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 110, 90]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 4,
            },
            "weak_point_glow": {
                "label": "Weak Point Hit",
                "weight": 0.05,
                # Yellow weak point glow on enemies
                "lower": np.array([18, 90, 140]),
                "upper": np.array([42, 255, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 3,
            },
            "crosshair_activity": {
                "label": "Combat (Crosshair)",
                "weight": 0.10,
                # Dynamic crosshair center screen — bright white
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 30, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 5,
            },
        },

        # Audio: important signal but don't let it overwhelm
        "audio_weight": 0.35,
        "audio_threshold_db": -18,
        "audio_ceiling_db": -3,

        # Motion: slight boost — combat has more movement
        "motion_weight": 0.08,
        "motion_multiplier": 2.5,

        # Brightness: catch explosion whiteouts
        "brightness_weight": 0.04,
        "brightness_threshold": 0.70,
        "brightness_multiplier": 2.5,

        # Scoring — slightly lower threshold to catch more action
        "intensity_threshold": 0.30,
        "fallback_threshold_ratio": 0.35,
        "merge_gap": 6,
        "min_clip_duration": 15,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 8,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Arc Raiders is a PvE co-op extraction shooter by Embark Studios where players fight robot enemies called ARCs.

IMPORTANT GAME KNOWLEDGE:
- THIRD-PERSON shooter — you see your character from behind
- NO kill feed — when a player dies, a bright RED FLARE shoots skyward (visible across map)
- NO enemy health bars — enemies show damage through physics (staggering, parts breaking off, sparks)
- NO hit markers — crosshair dynamically tightens during ADS as accuracy feedback
- ARC scanner beams turn RED when attacking (white=patrol, blue=curious, yellow=alert, red=aggro)
- Weak points glow YELLOW (Bastion kneecaps, Rocketeer glowing red core, Wasp thrusters)
- Player HUD: white health bar + blue segmented shield boxes (bottom-left), ammo (bottom-right)
- Shield is damage REDUCTION, not a second health pool
- Red directional indicators point toward damage source

Look for these highlights:
- **Active Combat**: Muzzle flash on character model, enemies with RED scanners, explosions
- **Kills**: ARC enemies staggering/collapsing/exploding, parts flying off
- **Deaths**: RED FLARE in the sky = someone died
- **Taking Damage**: Red indicators, health/shield depleting
- **Boss Encounters**: Large ARCs (Bastion, Crusher, Matriarch)
- **Close Calls**: Very low health, downed state, crawling
- **Explosions**: Grenades, environmental destruction, ARC self-destruct

Score 0.0 for: menus, inventory, crafting, loading, lobby (Speranza), map, settings.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.0 = menu/nothing, 0.3 = minor action, 0.6 = good combat, 0.8 = kill/major, 1.0 = insane play""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    # ===== ARC RAIDERS V3 — Aggressive / Wide-net =====
    # Strategy: Cast a very wide net. Lower all thresholds, wider color ranges,
    # more generous regions. Produces MORE clips but may include some false positives.
    # Good for short streams where you don't want to miss anything.
    "arc_raiders_v3": {
        "name": "Arc Raiders v3 (Aggressive)",
        "description": "Wide-net detection \u2014 catches more action, may include false positives",

        "detectors": {
            "combat_flash": {
                "label": "Combat / Muzzle Flash",
                "weight": 0.20,
                # Very wide orange-yellow range to catch any flash-like event
                # Includes warm whites from energy weapons
                "lower": np.array([5, 80, 150]),
                "upper": np.array([40, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.15,
                # Wider red range — catches flares, blood, damage indicators all at once
                "lower": np.array([0, 100, 130]),
                "upper": np.array([15, 255, 255]),
                "lower2": np.array([165, 100, 130]),
                "upper2": np.array([180, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "red_scanner": {
                "label": "ARC Enemy Aggro",
                "weight": 0.12,
                # Scanner beam — broader range
                "lower": np.array([0, 120, 120]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 120, 120]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.05, 0.80, 0.05, 0.95],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.12,
                # Bright explosions across most of screen
                "lower": np.array([3, 120, 150]),
                "upper": np.array([30, 255, 255]),
                "region": [0.15, 0.95, 0.05, 0.95],
                "multiplier": 4,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.10,
                "region": "health_bar",
                "bar_region": [0.85, 0.97, 0.01, 0.25],
                "bar_colors": [
                    {"lower": np.array([0, 0, 160]), "upper": np.array([180, 50, 255])},
                    {"lower": np.array([80, 40, 80]), "upper": np.array([140, 255, 255])},
                ],
                "depletion_threshold": 0.06,
                "multiplier": 5,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.10,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 3,
            },
            "yellow_glow": {
                "label": "Weak Point / Alert",
                "weight": 0.08,
                # Yellow glow — weak points + yellow scanner state (alert)
                "lower": np.array([15, 80, 130]),
                "upper": np.array([45, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "blue_energy": {
                "label": "Energy / Shield VFX",
                "weight": 0.08,
                # Blue energy effects — shield recharge, scanner curious state,
                # energy weapon trails
                "lower": np.array([95, 80, 130]),
                "upper": np.array([125, 255, 255]),
                "region": [0.10, 0.90, 0.10, 0.90],
                "multiplier": 3,
            },
            "crosshair": {
                "label": "Combat (Crosshair)",
                "weight": 0.05,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 35, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 4,
            },
        },

        # Audio: strong weight — explosions/gunfire are very reliable
        "audio_weight": 0.40,
        "audio_threshold_db": -20,
        "audio_ceiling_db": -3,

        # Motion: decent weight — action = camera shake
        "motion_weight": 0.12,
        "motion_multiplier": 3,

        # Brightness: moderate
        "brightness_weight": 0.06,
        "brightness_threshold": 0.60,
        "brightness_multiplier": 3,

        # Scoring — LOWER threshold catches more moments
        "intensity_threshold": 0.22,
        "fallback_threshold_ratio": 0.30,
        "merge_gap": 5,
        "min_clip_duration": 12,
        "max_clip_duration": 75,
        "clip_extension": 12,
        "pre_pad": 10,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Arc Raiders is a PvE co-op extraction shooter. THIRD-PERSON, NO kill feed (red flare = death), NO hit markers.

Be GENEROUS with scoring — if in doubt, score higher. The user wants to catch everything.

Look for: combat, explosions, deaths (red flares), ARC aggro (red scanners), taking damage, boss fights, close calls, loot moments, any exciting action.

Score 0.0 ONLY for: menus, inventory, loading screens, lobby.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    # ===== ARC RAIDERS V4 — Audio-Primary =====
    # Strategy: Let audio do most of the heavy lifting. Gunshots, explosions,
    # and combat audio are the most reliable signals. CV provides secondary
    # confirmation but doesn't drive decisions alone.
    "arc_raiders_v4": {
        "name": "Arc Raiders v4 (Audio-Heavy)",
        "description": "Audio-driven detection \u2014 relies on gunshots/explosions audio, CV as backup",

        "detectors": {
            "combat_flash": {
                "label": "Combat Flash",
                "weight": 0.15,
                # Standard muzzle flash — kept tight since audio does the heavy work
                "lower": np.array([10, 130, 180]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.90, 0.20, 0.80],
                "multiplier": 3,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.08,
                "lower": np.array([0, 150, 180]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 150, 180]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.0, 0.50, 0.10, 0.90],
                "multiplier": 5,
            },
            "red_aggro": {
                "label": "ARC Aggro",
                "weight": 0.10,
                "lower": np.array([0, 140, 150]),
                "upper": np.array([8, 255, 255]),
                "lower2": np.array([172, 140, 150]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.10, 0.75, 0.10, 0.90],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.07,
                "lower": np.array([5, 150, 170]),
                "upper": np.array([25, 255, 255]),
                "region": [0.20, 0.90, 0.10, 0.90],
                "multiplier": 4,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.08,
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    {"lower": np.array([0, 0, 180]), "upper": np.array([180, 40, 255])},
                    {"lower": np.array([90, 60, 100]), "upper": np.array([130, 255, 255])},
                ],
                "depletion_threshold": 0.10,
                "multiplier": 5,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.07,
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 3,
            },
        },

        # Audio: DOMINANT — this is the core signal
        "audio_weight": 0.60,
        "audio_threshold_db": -22,
        "audio_ceiling_db": -3,

        # Motion: minor
        "motion_weight": 0.03,
        "motion_multiplier": 2,

        # Brightness: minor
        "brightness_weight": 0.02,
        "brightness_threshold": 0.70,
        "brightness_multiplier": 2,

        # Scoring
        "intensity_threshold": 0.28,
        "fallback_threshold_ratio": 0.35,
        "merge_gap": 6,
        "min_clip_duration": 15,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 8,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Focus on AUDIO cues — this profile relies heavily on sound.

Arc Raiders is a PvE co-op extraction shooter. THIRD-PERSON, NO kill feed (red flare = death), NO hit markers.

Look for: any frame where combat is happening based on visual cues like muzzle flash, explosions, red scanners, damage indicators.

Score 0.0 for: menus, inventory, loading, lobby.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    # ===== ARC RAIDERS V5 — Motion + Brightness =====
    # Strategy: Use motion detection and brightness changes as primary signals.
    # Combat = camera shake, fast movement, explosions creating brightness spikes.
    # Less dependent on exact color matching which can fail with different
    # game settings, color grading, or stream compression.
    "arc_raiders_v5": {
        "name": "Arc Raiders v5 (Motion-Based)",
        "description": "Motion + brightness detection \u2014 works regardless of color settings",

        "detectors": {
            "combat_flash": {
                "label": "Combat Flash",
                "weight": 0.12,
                # Minimal color detection — just catch the most obvious
                "lower": np.array([10, 130, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.08,
                "lower": np.array([0, 150, 180]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 150, 180]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.0, 0.50, 0.10, 0.90],
                "multiplier": 5,
            },
            "red_combat": {
                "label": "Red (Damage/Aggro)",
                "weight": 0.10,
                # Combined red signal — catches scanners AND damage indicators
                "lower": np.array([0, 130, 130]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 130, 130]),
                "upper2": np.array([180, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.08,
                "lower": np.array([5, 140, 160]),
                "upper": np.array([28, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.08,
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    {"lower": np.array([0, 0, 180]), "upper": np.array([180, 40, 255])},
                    {"lower": np.array([90, 60, 100]), "upper": np.array([130, 255, 255])},
                ],
                "depletion_threshold": 0.10,
                "multiplier": 5,
            },
        },

        # Audio: secondary support
        "audio_weight": 0.25,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,

        # Motion: PRIMARY SIGNAL — combat = fast movement, camera shake
        "motion_weight": 0.30,
        "motion_multiplier": 4,

        # Brightness: STRONG SIGNAL — flashes, explosions, whiteouts
        "brightness_weight": 0.15,
        "brightness_threshold": 0.55,
        "brightness_multiplier": 4,

        # Scoring — lower threshold since motion is inherently noisier
        "intensity_threshold": 0.25,
        "fallback_threshold_ratio": 0.35,
        "merge_gap": 6,
        "min_clip_duration": 12,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 8,
        # Higher peak weight — motion spikes are bursty
        "peak_weight": 0.75,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Arc Raiders is a PvE co-op extraction shooter. THIRD-PERSON.

Focus on MOTION and VISUAL INTENSITY — fast camera movement, explosions, flashes, combat chaos.

Look for: combat, explosions, deaths, taking damage, boss fights, chases, any high-action moments.

Score 0.0 for: menus, inventory, loading, lobby, standing still.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    # ===== ARC RAIDERS V6 — Conservative / Precision =====
    # Strategy: Only clip the BEST moments. Very tight color ranges,
    # high thresholds, strict requirements. Fewer clips but higher quality.
    # Best for long streams where you want only the highlights.
    "arc_raiders_v6": {
        "name": "Arc Raiders v6 (Precision)",
        "description": "Conservative detection \u2014 only clips the most intense moments, fewer false positives",

        "detectors": {
            "muzzle_flash": {
                "label": "Gunfire",
                "weight": 0.25,
                # Tight muzzle flash range — only the most obvious
                "lower": np.array([12, 150, 200]),
                "upper": np.array([28, 255, 255]),
                "region": [0.40, 0.85, 0.35, 0.80],
                "multiplier": 6,
            },
            "death_flare": {
                "label": "Death / Kill",
                "weight": 0.15,
                # Very strict red — only catch actual flares
                "lower": np.array([0, 170, 200]),
                "upper": np.array([8, 255, 255]),
                "lower2": np.array([172, 170, 200]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.0, 0.40, 0.15, 0.85],
                "multiplier": 8,
            },
            "red_scanner": {
                "label": "ARC Aggro",
                "weight": 0.15,
                # Strict red scanner — only when very clearly red
                "lower": np.array([0, 160, 170]),
                "upper": np.array([6, 255, 255]),
                "lower2": np.array([174, 160, 170]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.15, 0.70, 0.15, 0.85],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.15,
                # Only large, obvious explosions
                "lower": np.array([8, 170, 190]),
                "upper": np.array([22, 255, 255]),
                "region": [0.25, 0.85, 0.15, 0.85],
                "multiplier": 6,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.15,
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    {"lower": np.array([0, 0, 190]), "upper": np.array([180, 35, 255])},
                    {"lower": np.array([95, 70, 110]), "upper": np.array([125, 255, 255])},
                ],
                # Higher depletion threshold — only clip significant health drops
                "depletion_threshold": 0.15,
                "multiplier": 7,
            },
            "damage_indicators": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Strict damage — only obvious red edges
                "lower": np.array([0, 140, 120]),
                "upper": np.array([8, 255, 255]),
                "lower2": np.array([172, 140, 120]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 5,
            },
        },

        # Audio: moderate support
        "audio_weight": 0.30,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,

        # Motion: minimal — avoid false positives from camera movement
        "motion_weight": 0.05,
        "motion_multiplier": 2,

        # Brightness: moderate
        "brightness_weight": 0.04,
        "brightness_threshold": 0.80,
        "brightness_multiplier": 2,

        # Scoring — HIGH threshold = only the best moments
        "intensity_threshold": 0.45,
        "fallback_threshold_ratio": 0.50,
        "merge_gap": 10,
        "min_clip_duration": 20,
        "max_clip_duration": 50,
        "clip_extension": 8,
        "pre_pad": 6,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Be STRICT — only flag truly exciting moments.

Arc Raiders is a PvE co-op extraction shooter. THIRD-PERSON, NO kill feed (red flare = death), NO hit markers.

ONLY score high for: confirmed kills (parts flying off, enemies collapsing), boss encounters, near-death moments, massive explosions, multiple enemies engaging at once.

Score 0.0 for: menus, lobby, walking, looting (unless rare loot), mild combat, single enemy encounters.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Be conservative: 0.0 = not exciting, 0.5 = decent action, 0.8+ = truly exceptional moment only.""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment? Be strict.",
    },

    # ===== ARC RAIDERS V7 — ARC + Raider PvPvE Focus =====
    # Strategy: Detect BOTH ARC robot enemies AND other Raider players.
    # Arc Raiders is PvPvE — the most exciting moments often involve
    # other players (PvP) during ARC encounters. This profile emphasizes
    # player-vs-player encounters alongside PvE combat.
    # Key PvP signals: other players shooting, player-on-player combat,
    # multiple death flares, extraction zone fights.
    "arc_raiders_v7": {
        "name": "Arc Raiders v7 (PvPvE)",
        "description": "PvPvE-focused \u2014 detects ARC robots AND other Raider players, extraction fights",

        "detectors": {
            "muzzle_flash_close": {
                "label": "Close-Range Gunfire",
                "weight": 0.18,
                # Your character's weapon fire — close range, lower screen area
                "lower": np.array([8, 110, 170]),
                "upper": np.array([35, 255, 255]),
                # White energy weapon flash
                "lower2": np.array([0, 0, 235]),
                "upper2": np.array([180, 45, 255]),
                "region": [0.45, 0.90, 0.30, 0.85],
                "multiplier": 5,
            },
            "muzzle_flash_distant": {
                "label": "Distant Gunfire",
                "weight": 0.10,
                # Other players/ARCs shooting — can be anywhere on screen
                # Smaller, less saturated flashes at distance
                "lower": np.array([10, 100, 160]),
                "upper": np.array([30, 255, 255]),
                "region": [0.10, 0.75, 0.10, 0.90],
                "multiplier": 3,
            },
            "death_flare": {
                "label": "Death Flare (Kill!)",
                "weight": 0.15,
                # Death flares — MORE IMPORTANT here because PvP kills
                # produce the same red flare as PvE kills
                # Multiple flares = intense firefight
                "lower": np.array([0, 140, 170]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 140, 170]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.0, 0.55, 0.05, 0.95],
                "multiplier": 7,
            },
            "red_scanner_aggro": {
                "label": "ARC Enemy Aggro",
                "weight": 0.12,
                # ARC scanner beams in red state
                "lower": np.array([0, 135, 145]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 135, 145]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.10, 0.75, 0.10, 0.90],
                "multiplier": 5,
            },
            "yellow_scanner_alert": {
                "label": "ARC Alert State",
                "weight": 0.06,
                # Yellow scanner = alert state — ARCs detected something
                # Often triggers right before a firefight starts
                "lower": np.array([20, 120, 150]),
                "upper": np.array([35, 255, 255]),
                "region": [0.10, 0.80, 0.10, 0.90],
                "multiplier": 3,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.10,
                "lower": np.array([5, 140, 165]),
                "upper": np.array([28, 255, 255]),
                "region": [0.20, 0.90, 0.10, 0.90],
                "multiplier": 5,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.10,
                "region": "health_bar",
                "bar_region": [0.87, 0.96, 0.01, 0.23],
                "bar_colors": [
                    {"lower": np.array([0, 0, 175]), "upper": np.array([180, 42, 255])},
                    {"lower": np.array([88, 55, 95]), "upper": np.array([132, 255, 255])},
                ],
                "depletion_threshold": 0.08,
                "multiplier": 6,
            },
            "damage_indicators": {
                "label": "Taking Damage",
                "weight": 0.10,
                # Slightly wider edges — PvP can hit from unexpected angles
                "lower": np.array([0, 115, 95]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 115, 95]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.13,
                "multiplier": 4,
            },
            "crosshair_activity": {
                "label": "Aiming (Combat)",
                "weight": 0.09,
                # Crosshair tightening during ADS — sign of active combat
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 30, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 4,
            },
        },

        # Audio: important — especially for PvP (player gunfire from behind)
        "audio_weight": 0.38,
        "audio_threshold_db": -18,
        "audio_ceiling_db": -3,

        # Motion: moderate — PvP has erratic movement
        "motion_weight": 0.10,
        "motion_multiplier": 3,

        # Brightness: moderate
        "brightness_weight": 0.05,
        "brightness_threshold": 0.65,
        "brightness_multiplier": 3,

        # Scoring — balanced threshold
        "intensity_threshold": 0.28,
        "fallback_threshold_ratio": 0.35,
        "merge_gap": 5,
        "min_clip_duration": 12,
        "max_clip_duration": 65,
        "clip_extension": 12,
        "pre_pad": 10,

        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Arc Raiders is a PvPvE co-op extraction shooter.

CRITICAL: This game has BOTH robot enemies (ARCs) and other human players (Raiders). The most exciting moments involve:

PvP (Player vs Player):
- Other Raiders shooting at you — muzzle flash from unexpected directions
- Multiple death flares in quick succession = intense PvP fight
- Extraction zone battles — players fighting over the extract point
- Ambushes, backstabs, third-party attacks during ARC fights

PvE (Player vs Environment):
- ARC robot attacks — red scanner beams, swarming, boss encounters
- Bastion, Crusher, Matriarch boss fights
- Horde-style encounters with many small ARCs

BOTH AT ONCE (best content):
- Fighting ARCs while other Raiders attack you
- Contested extraction with ARCs and Raiders
- Chaotic multi-way fights

THIRD-PERSON, NO kill feed (red flare = death), NO hit markers.

Score 0.0 for: menus, inventory, loading, lobby (Speranza).

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.3 = minor combat, 0.5 = PvE fight, 0.7 = PvP encounter, 0.9 = PvPvE chaos, 1.0 = insane multi-way fight""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting PvPvE moment?",
    },

    "war_thunder": {
        "name": "War Thunder",
        "description": "Military vehicles — detects kills, crits, fires, bomb hits, air combat, ammo racks",
        "detectors": {
            "kill_feed": {
                "label": "Target Destroyed",
                "weight": 0.30,
                # War Thunder kill text: bright yellow/white text center-bottom area
                # "Target Destroyed", "Critical hit", "Hit" messages
                # Kill camera: switches to dramatic angle on kill
                # Ammo rack: turret flies off, huge explosion
                "lower": np.array([18, 80, 200]),
                "upper": np.array([35, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill messages appear center-lower area
                "region": [0.55, 0.85, 0.25, 0.75],
                "multiplier": 5,
            },
            "damage": {
                "label": "Crew Knocked Out / Damage",
                "weight": 0.15,
                # Red damage indicators at screen edges
                # "Crew knocked out" notification
                # Fire warning: vehicle on fire, FPE counter
                # Module damage: yellow/red icons on vehicle diagram
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Penetration / Critical Hit",
                "weight": 0.15,
                # Hit camera: shows shell penetrating armor
                # "Critical hit!" yellow text notification
                # Penetration: sparks and internal damage VFX
                # Ricochet: bounce spark (non-pen, but dramatic)
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Bomb / Rocket / Ammo Rack",
                "weight": 0.20,
                # Bomb impact: massive orange explosion + dirt cloud
                # Rocket strike: orange trail + explosion
                # Ammo rack detonation: turret flies off, huge orange fireball
                # Naval torpedoes: large water + fire explosion
                "lower": np.array([5, 100, 130]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Vehicle on Fire / Smoke",
                "weight": 0.10,
                # Vehicle fire: orange flames from engine/turret
                # Planes trailing smoke: dark trail behind aircraft
                # Engine fire: orange glow from engine compartment
                # Emergency landing: plane descending with smoke trail
                "lower": np.array([0, 130, 140]),
                "upper": np.array([20, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
        },
        "motion_weight": 0.07, "motion_multiplier": 3,
        "brightness_weight": 0.03, "brightness_threshold": 0.65, "brightness_multiplier": 2.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.5,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 6,
        "ai_system_prompt": """You are an expert War Thunder gameplay analyst. War Thunder is a military vehicle combat game with tanks, planes, ships, and helicopters by Gaijin.

Key visual cues:
- **"Target Destroyed"**: Yellow text notification when enemy vehicle killed
- **"Critical hit!"**: Yellow text for module/crew damage
- **Kill camera**: Dramatic angle showing shell penetration on kill
- **Ammo rack**: Turret flies off in massive explosion — most dramatic kill type
- **Vehicle fire**: Orange flames from engine, FPE (Fire Prevention Equipment) counter
- **Bomb impact**: Massive orange explosion + dirt/debris cloud
- **Dogfight**: Plane tracking, lead indicator, gun camera VFX
- **Penetration cam**: Shows shell path through armor in X-ray view
- **Smoke trail**: Damaged plane trailing black smoke

Look for: Ammo rack detonations, multi-kills, long-range snipes, CAS bomb runs, dogfight kills, anti-air vs plane, clutch repairs, funny deaths, turret tosses, nuke (25-kill reward).
Score 0.0 for: driving to position, waiting, hangar, tech tree browsing, queue.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this War Thunder gameplay frame. Is this an exciting moment?",
    },

    "fortnite": {
        "name": "Fortnite",
        "description": "Battle royale — detects eliminations, shield cracks, builds, storm, Victory Royale",
        "detectors": {
            "kill_feed": {
                "label": "Elimination",
                "weight": 0.30,
                # Fortnite kill feed: bottom-left, white text with colored player names
                # Elimination messages appear as white/gray text
                "lower": np.array([0, 0, 210]),
                "upper": np.array([180, 40, 255]),
                # Also catch golden/yellow XP popup text
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([40, 255, 255]),
                # Kill feed is bottom-left in Chapter 5+
                "region": [0.75, 0.95, 0.01, 0.35],
                "multiplier": 8,
            },
            "damage": {
                "label": "Shield Crack / HP Drop",
                "weight": 0.20,
                # Fortnite health/shield: bottom-center HUD
                # Shield = blue bar, Health = green bar, both bottom-center
                "region": "health_bar",
                "bar_region": [0.92, 0.98, 0.30, 0.70],
                "bar_colors": [
                    # Blue shield bar
                    {"lower": np.array([100, 100, 130]), "upper": np.array([125, 255, 255])},
                    # Green health bar
                    {"lower": np.array([40, 80, 100]), "upper": np.array([80, 255, 255])},
                    # White (full shield flash)
                    {"lower": np.array([0, 0, 200]), "upper": np.array([180, 30, 255])},
                ],
                "depletion_threshold": 0.12,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Landing Shots",
                "weight": 0.20,
                # White hit markers appear at crosshair center
                # Red X = elimination confirmed
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion / RPG",
                "weight": 0.18,
                # Orange-yellow explosion VFX
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "storm": {
                "label": "Storm Damage",
                "weight": 0.07,
                # Purple storm vignette at edges
                "lower": np.array([120, 40, 60]),
                "upper": np.array([155, 255, 200]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 3,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Fortnite gameplay analyst. Fortnite is a third-person battle royale with building mechanics.

Key visual cues:
- **Eliminations**: White text kill feed bottom-left, red X hit marker = kill confirmed
- **Shield crack**: Blue shield bar depletes, audible crack sound, blue particle burst
- **Building**: Rapid material placement (wood/brick/metal walls, ramps, floors)
- **Storm**: Purple edges on screen when in storm, health ticking down
- **Victory Royale**: Golden "#1 VICTORY ROYALE" text center screen
- **Damage numbers**: White/yellow numbers pop up near crosshair on hits
- **Low HP**: Health bar flashes red when critical

Look for: Eliminations, build fights, box fights, shotgun edits, sniper shots, Victory Royale, clutch plays, funny moments, storm escapes.
Score 0.0 for: lobby, item shop, loading, creative mode menus.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Fortnite gameplay frame. Is this an exciting moment?",
    },

    "apex_legends": {
        "name": "Apex Legends",
        "description": "Battle royale — detects knocks, kills, abilities, shield cracks, squad wipes",
        "detectors": {
            "kill_feed": {
                "label": "Knock / Kill Banner",
                "weight": 0.30,
                # Apex kill feed: top-right corner, shows colored kill banners
                # Knockdown banner: opponent's banner card slides in from right
                # Squad wipe: "SQUAD ELIMINATED" text center screen
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed is TOP-RIGHT in Apex
                "region": [0.01, 0.25, 0.60, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Shield Crack / Low HP",
                "weight": 0.20,
                # Health/shield bar: bottom-center HUD
                # Shield colors by tier: White S<30, Blue H100-130, Purple H130-160, Gold H20-35, Red H0-10
                # Shield crack: distinct cracking VFX + sound when shield breaks
                "region": "health_bar",
                "bar_region": [0.90, 0.97, 0.35, 0.65],
                "bar_colors": [
                    {"lower": np.array([0, 0, 200]), "upper": np.array([180, 30, 255])},
                    {"lower": np.array([100, 80, 120]), "upper": np.array([130, 255, 255])},
                    {"lower": np.array([130, 60, 120]), "upper": np.array([160, 255, 255])},
                ],
                "depletion_threshold": 0.15,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Damage Numbers",
                "weight": 0.20,
                # White damage numbers float above enemies when hit
                # Shield damage: numbers match shield color (blue/purple/gold/red)
                # Headshot: larger yellow damage numbers
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Grenade / Ability VFX",
                "weight": 0.18,
                # Thermite: bright orange fire, Arc star: blue electricity
                # Fuse knuckle cluster: orange sparks, Bangalore smoke + missile
                # Gibraltar air strike: orange explosions
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Ultimate / Ring Closing",
                "weight": 0.07,
                # Ring closing: orange/red energy wall visible in world
                # Ultimate abilities: bright VFX (Gibby dome blue, Bloodhound red scan)
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Apex Legends gameplay analyst. Apex is a fast-paced squad-based battle royale by Respawn.

Key visual cues:
- **Kill feed**: Top-right, colored kill banners slide in showing knocked/eliminated
- **Damage numbers**: Float above enemies — white for health, colored for shield tier
- **Shield crack**: Distinct cracking VFX when enemy shield breaks completely
- **Squad wipe**: "SQUAD ELIMINATED" text appears center screen
- **Knockdown shield**: Colored shield appears when enemy is downed
- **Ring**: Orange/red energy wall closing in, damages players outside
- **Abilities**: Legend-specific VFX (Wraith portal purple, Octane pad green, Gibby dome blue)
- **Champion banner**: "YOU ARE THE CHAMPION" at match end

Look for: Squad wipes, clutch 1v3s, shield cracks, movement tech (tap-strafing, wall bounces), beam fights, sniper knocks, hot drops, champion wins.
Score 0.0 for: looting, inventory, legend select, lobby, crafting.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Apex Legends gameplay frame. Is this an exciting moment?",
    },

    "valorant": {
        "name": "Valorant",
        "description": "Tactical FPS — detects kills, headshots, abilities, spike, round wins, aces",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Ace",
                "weight": 0.30,
                # Valorant kill feed: top-right corner, shows agent icons + kill info
                # Red text for enemy kills, white for assists
                # Kill banner: red background with white skull icon
                "lower": np.array([0, 130, 160]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 130, 160]),
                "upper2": np.array([180, 255, 255]),
                # Kill feed is top-right
                "region": [0.01, 0.20, 0.65, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red vignette at screen edges when hit
                # Directional damage indicator: red arc pointing toward shooter
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Headshot / Hit",
                "weight": 0.25,
                # White crosshair hit markers, red for headshot kills
                # Headshot makes a distinct "dink" sound + red marker
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 7,
            },
            "ability": {
                "label": "Ability Effect",
                "weight": 0.18,
                # Abilities have distinct colors per agent:
                # Jett: blue/cyan, Phoenix: orange, Sage: green, Omen: purple
                # Most ability VFX are bright saturated colors
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "spike": {
                "label": "Spike Plant/Defuse",
                "weight": 0.07,
                # Spike glow: bright yellow-orange when planted, pulsing
                # Defuse UI: circular progress indicator
                "lower": np.array([15, 120, 200]),
                "upper": np.array([30, 255, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 5,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        # Valorant rounds are short — shorter clips
        "merge_gap": 5, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Valorant gameplay analyst. Valorant is a 5v5 tactical FPS by Riot Games.

Key visual cues:
- **Kill feed**: Top-right corner, red background for your kills, skull icons
- **Headshot**: Red hit marker at crosshair + "dink" sound, instant kill on most weapons
- **Ace**: All 5 enemies killed by one player, "ACE" text banner appears
- **Spike**: Yellow-orange glow when planted, UI timer bar, defuse progress circle
- **Round win**: Large round end banner, score display
- **Abilities**: Agent-specific colors (Jett blue wind, Phoenix orange fire, Sage green heal)
- **Clutch**: 1vX situations, last player alive on team
- **Economy**: Eco/force buy rounds where pistol kills vs rifles are impressive

Look for: Multi-kills, aces, clutches, headshots, one-taps, ability plays, spike plants/defuses, eco round wins, flick shots.
Score 0.0 for: buy phase, agent select, loading screen, settings.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Valorant gameplay frame. Is this an exciting moment?",
    },

    "call_of_duty": {
        "name": "Call of Duty",
        "description": "FPS — detects kills, killstreaks, hitmarkers, multikills, nukes",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Multikill",
                "weight": 0.30,
                # CoD kill feed: top-left corner in MW3/Warzone, shows skull + weapon icon
                # Kill confirmed medal pops up center-right
                # Multikill medals: "Double Kill", "Triple Kill", etc. center screen
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                # Kill feed is top-left
                "region": [0.02, 0.25, 0.02, 0.40],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red blood spatter edges when hit, heavy red overlay at low HP
                # Directional damage indicator: red arc at screen edges
                # "Bloody screen" effect intensifies as HP drops
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitmarker X",
                "weight": 0.25,
                # Iconic white X hitmarker at crosshair center on hit
                # Red/gold hitmarker on kill (kill confirmed)
                # Headshot: distinct "ding" sound + red marker
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Explosion / Scorestreak",
                "weight": 0.18,
                # Killstreak VFX: VTOL orange fire, Cruise missile trail, Chopper gunner
                # Grenades, C4, RPG: bright orange-yellow explosions
                # Nuke: blinding white flash
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Killstreak Reward",
                "weight": 0.07,
                # Killstreak notification: gold/yellow text center-right
                # UAV, VTOL, Chopper Gunner, Nuke countdown
                # Weapon inspect / camo unlock: gold/purple flash
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.25, 0.50, 0.55, 0.98],
                "multiplier": 5,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 5, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Call of Duty gameplay analyst covering MW3, Warzone, and Black Ops.

Key visual cues:
- **Kill feed**: Top-left, skull icon + weapon used, your kills highlighted
- **Hitmarker**: White X at crosshair on hit, red/gold on kill
- **Multikill medals**: "Double Kill", "Triple Kill" etc. pop up center-right
- **Killstreaks**: Gold notification text, UAV/VTOL/Chopper/Nuke callouts
- **Damage**: Red blood spatter edges, directional damage arcs
- **Nuke**: 25-killstreak, countdown timer, blinding white flash
- **Final killcam**: Slow-motion replay of last kill in match
- **Warzone**: Gulag fights, loadout drops, gas circle, bounty contracts

Look for: Feed streaks, quickscopes, trickshots, nuke gameplay, clutch Warzone wins, funny deaths, collateral kills, throwing knife kills.
Score 0.0 for: class setup, lobby, loadout editing, pre-game countdown.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Call of Duty gameplay frame. Is this an exciting moment?",
    },

    "league_of_legends": {
        "name": "League of Legends",
        "description": "MOBA — detects kills, teamfights, objectives, pentakills, baron/dragon",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Multikill",
                "weight": 0.30,
                # LoL kill announcements: right side of screen, show champion icons
                # Multikill banners: "DOUBLE KILL", "TRIPLE KILL", "QUADRA KILL", "PENTA KILL"
                # These appear center-top as large gold/red text
                # Kill text is red for enemy, blue for ally
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill announcements right side
                "region": [0.02, 0.35, 0.65, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Low Health / Death",
                "weight": 0.20,
                # Health bar: above champion model (green bar, turns orange/red when low)
                # Death: screen goes gray with death timer
                # Low HP: screen edges may flash red with some effects
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.40, 0.60],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Ability / Spell VFX",
                "weight": 0.15,
                # Abilities create bright colored VFX on impact
                # Lux ult: rainbow laser, Jinx rockets: red explosion
                # Many abilities produce white/bright flash on hit
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Teamfight VFX",
                "weight": 0.25,
                # Teamfights: screen full of colored ability VFX
                # Multiple champion abilities create saturated colors
                # Ignite: orange burn, Exhaust: yellow slow, Barrier: white shield
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Baron / Dragon / Tower",
                "weight": 0.07,
                # Baron Nashor: purple theme, large monster pit
                # Dragon: elemental colors (Infernal red, Ocean blue, Mountain brown, Cloud white)
                # Elder dragon: large golden buff indicator
                # Tower destruction: gold particles
                "lower": np.array([130, 60, 120]),
                "upper": np.array([160, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert League of Legends gameplay analyst. LoL is a 5v5 MOBA by Riot Games.

Key visual cues:
- **Kill feed**: Right side, champion icons showing killer→victim
- **Multikill banners**: Gold/red text center: "DOUBLE KILL" through "PENTA KILL"
- **Teamfights**: Screen fills with colorful ability VFX from multiple champions
- **Death**: Screen goes gray, death timer appears
- **Baron/Dragon**: Large monster fights in river, purple (Baron) or elemental colors (Dragon)
- **Tower**: Gold explosion particles when destroyed, "TURRET DESTROYED" announcement
- **Ace**: "ACE" text when entire enemy team is dead
- **Inhibitor**: "INHIBITOR DESTROYED" — super minions spawn

Look for: Pentakills, baron/dragon steals with smite, tower dives, 1v5 outplays, flash plays, clutch teamfights, backdoors, funny fails, level 1 invades.
Score 0.0 for: farming minions, walking to lane, shop, loading screen, champion select.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this League of Legends gameplay frame. Is this an exciting moment?",
    },

    "counter_strike": {
        "name": "Counter-Strike 2",
        "description": "Tactical FPS — detects kills, headshots, bomb plant/defuse, clutches, aces",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Headshot",
                "weight": 0.30,
                # CS2 kill feed: top-right corner, shows weapon icon between killer→victim
                # Headshot icon (crosshair) appears next to kill
                # Your kills are highlighted, team kills in team color (CT blue, T yellow)
                "lower": np.array([0, 100, 180]),
                "upper": np.array([15, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed top-right
                "region": [0.01, 0.20, 0.55, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red directional blood overlay at edges when hit
                # Blood spatter effect on screen
                # Aimpunch: crosshair jumps when hit without armor
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Headshot Dink",
                "weight": 0.25,
                # CS2 has no traditional hitmarker — but headshot "dink" is iconic
                # Kill: crosshair briefly flashes, enemy ragdolls
                # Blood spray appears on wall behind enemy
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 20, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "HE / Molotov / Flash",
                "weight": 0.18,
                # HE grenade: orange explosion
                # Molotov/incendiary: bright orange fire on ground
                # Flashbang: screen goes completely white
                # Smoke: gray cloud (not very colorful)
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "special": {
                "label": "Bomb Plant / Defuse",
                "weight": 0.10,
                # Bomb planted: beeping sound, timer bar at top of screen
                # C4 glow: bright yellow-orange on the ground
                # Defuse: progress bar appears, tense moments
                # Round win: large banner "COUNTER-TERRORISTS WIN" / "TERRORISTS WIN"
                "lower": np.array([15, 100, 200]),
                "upper": np.array([30, 255, 255]),
                "region": [0.02, 0.10, 0.30, 0.70],
                "multiplier": 6,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        # CS rounds are short — shorter clips
        "merge_gap": 5, "min_clip_duration": 8, "max_clip_duration": 35, "clip_extension": 5, "pre_pad": 3,
        "ai_system_prompt": """You are an expert Counter-Strike 2 gameplay analyst. CS2 is a 5v5 tactical FPS by Valve.

Key visual cues:
- **Kill feed**: Top-right, weapon icon between killer→victim names, headshot icon for headshots
- **Bomb**: Yellow-orange C4 glow when planted, beeping timer bar at top
- **Round end**: Large banner "COUNTER-TERRORISTS WIN" or "TERRORISTS WIN"
- **Flashbang**: Screen goes completely white
- **Molotov**: Bright orange fire spreading on ground
- **HE grenade**: Orange explosion
- **Death**: Ragdoll physics, death cam showing killer's perspective
- **Ace**: All 5 enemies killed by one player

Look for: Aces, 1vX clutches, AWP flick shots, deagle headshots, ninja defuses, eco round wins, wallbangs, collaterals, knife kills, flashbang plays.
Score 0.0 for: buy phase, freeze time, spectating, loading, warmup.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this CS2 gameplay frame. Is this an exciting moment?",
    },

    "minecraft": {
        "name": "Minecraft",
        "description": "Sandbox — detects combat, boss fights, deaths, explosions, lava, enchanting",
        "detectors": {
            "kill_feed": {
                "label": "Death / Chat Message",
                "weight": 0.20,
                # Minecraft chat: bottom-left, shows death messages and announcements
                # "PlayerName was slain by Zombie", "PlayerName fell from a high place"
                # Death messages are white text on dark background
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                # Chat/death messages bottom-left
                "region": [0.75, 0.95, 0.02, 0.60],
                "multiplier": 5,
            },
            "damage": {
                "label": "Taking Damage / Low HP",
                "weight": 0.20,
                # Hearts HUD: top-left area, red hearts deplete left-to-right
                # Screen flashes RED when taking damage
                # Hardcore: single heart left = intense red vignette
                # Hunger bar: brown meat shanks, right of hearts
                "lower": np.array([0, 150, 150]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 150, 150]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Sword / Bow Hit",
                "weight": 0.15,
                # Mob hit: entity flashes red, knockback
                # Critical hit: star particles around swing
                # Bow shot: arrow trail + impact particles
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 4,
            },
            "explosion": {
                "label": "TNT / Creeper / Bed",
                "weight": 0.25,
                # Creeper explosion: white flash + gray smoke particles
                # TNT: bright orange-white explosion, block debris
                # Bed in Nether: large orange explosion (speedrun strat)
                # Respawn anchor explosion: similar to bed
                "lower": np.array([10, 80, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Ender Dragon / Nether Portal",
                "weight": 0.10,
                # End dimension: purple/black void, Ender Dragon purple particles
                # Nether portal: purple swirl effect fills screen when entering
                # Enchanting table: purple rune particles
                # Wither: dark wither effect, blue skull projectiles
                # End portal: starfield texture
                "lower": np.array([130, 50, 80]),
                "upper": np.array([165, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.05, "motion_multiplier": 2,
        "brightness_weight": 0.05, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Minecraft gameplay analyst covering Java and Bedrock editions.

Key visual cues:
- **Hearts**: Top-left HUD, red hearts deplete when taking damage
- **Damage flash**: Entire screen briefly flashes red when hit
- **YOU DIED**: Red death screen with respawn/title screen buttons
- **Explosions**: Creeper/TNT create white flash + smoke, bed explosions in Nether
- **Ender Dragon**: End dimension purple void, dragon has purple particle trail
- **Nether Portal**: Purple swirl fills screen when entering
- **Enchanting**: Purple rune particles floating around enchanting table
- **Lava**: Bright orange fills screen when submerged, fire overlay
- **XP orbs**: Small green/yellow orbs float toward player on mob kill

Look for: Boss kills (Ender Dragon, Wither), creeper explosions, PvP kills, lava deaths, clutch MLG water bucket saves, rare item finds, speedrun splits, epic builds, funny deaths, hardcore mode close calls.
Score 0.0 for: mining, farming, crafting, inventory management, walking.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Minecraft gameplay frame. Is this an exciting moment?",
    },

    "gta_v": {
        "name": "GTA V / Online",
        "description": "Open world — detects kills, explosions, wanted levels, chases, stunts",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Wasted",
                "weight": 0.25,
                # GTA kill messages: chat box bottom-left
                # "WASTED" screen: large red text center, screen desaturates to gray
                # GTA Online: kill notifications in chat feed
                "lower": np.array([0, 100, 150]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Wasted text appears center screen
                "region": [0.30, 0.70, 0.25, 0.75],
                "multiplier": 7,
            },
            "damage": {
                "label": "Low Health / Armor",
                "weight": 0.20,
                # Health bar: green bar next to minimap (bottom-left)
                # Armor: blue bar above health bar
                # Low HP: screen desaturates, edges darken
                # Getting shot: red directional indicator
                "region": "health_bar",
                "bar_region": [0.92, 0.98, 0.02, 0.22],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Crosshair / Shooting",
                "weight": 0.15,
                # White dot crosshair, turns red when on target
                # Kill: crosshair flashes, enemy ragdolls
                # Headshot: instant ragdoll, distinct hit sound
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Explosion / Vehicle Crash",
                "weight": 0.25,
                # Vehicle explosions: large orange fireball + black smoke
                # RPG: orange trail + big explosion
                # Sticky bomb / C4: orange-white flash
                # Car crashes: sparks + deformation VFX
                # Oppressor missiles: bright trail
                "lower": np.array([8, 120, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Wanted Stars / Police",
                "weight": 0.10,
                # Wanted level: 1-5 stars top-right of minimap, blue/white stars
                # Police: flashing red/blue lights on police cars
                # Heist setup: green $ indicators
                "lower": np.array([100, 120, 180]),
                "upper": np.array([130, 255, 255]),
                "region": [0.88, 0.98, 0.02, 0.22],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert GTA V / GTA Online gameplay analyst.

Key visual cues:
- **WASTED**: Large red text center screen, entire screen goes gray — player died
- **Kill feed**: Chat messages bottom-left showing kills in GTA Online
- **Explosions**: Massive orange fireballs from vehicles, RPGs, sticky bombs
- **Wanted level**: Blue/white stars top-right of minimap (1-5 stars)
- **Police chase**: Flashing red/blue lights, helicopter searchlights
- **Vehicle stunts**: Stunt camera angle changes, "Stunt Jump Completed" text
- **Heists**: Green $ UI elements, setup board, dramatic cutscenes
- **Minimap**: Bottom-left corner, shows blips for enemies, objectives

Look for: Car chases, massive explosions, police shootouts, PvP kills, insane stunts, funny ragdolls, heist finales, jet dogfights, Oppressor griefing/defense, funny glitches.
Score 0.0 for: driving normally, walking, passive mode, loading, cutscenes (unless dramatic).

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this GTA V gameplay frame. Is this an exciting moment?",
    },

    "overwatch": {
        "name": "Overwatch 2",
        "description": "Hero shooter — detects eliminations, ultimates, POTG, team kills, on fire",
        "detectors": {
            "kill_feed": {
                "label": "Elimination",
                "weight": 0.30,
                # OW2 kill feed: top-right corner, horizontal bars showing killer→victim
                # Red skull icons for final blows, assist icons for assists
                # Your kills have red text/highlight
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed is top-right in OW2
                "region": [0.01, 0.18, 0.55, 0.99],
                "multiplier": 7,
            },
            "damage": {
                "label": "Critical Health",
                "weight": 0.15,
                # Red vignette when low HP, screen desaturates
                # Critical health warning: red pulsing edges
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitting Shots",
                "weight": 0.20,
                # OW2 hit markers: white crosshair tick marks that expand on hit
                # Headshot: red tick marks + "dink" sound
                # Kill confirmed: large red X through crosshair
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 5,
            },
            "ultimate": {
                "label": "Ultimate Ability",
                "weight": 0.25,
                # Ultimate VFX are very bright and saturated per hero
                # Genji blade: green, DVa bomb: blue flash, Junkrat tire: orange
                # Nano boost: blue glow, Rally: yellow, etc.
                # Most ults produce bright orange/yellow explosions or flashes
                "lower": np.array([10, 120, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "on_fire": {
                "label": "On Fire / POTG",
                "weight": 0.05,
                # "On Fire" status: orange flame icon bottom-center HUD
                # Portrait border turns orange/flame when on fire
                "lower": np.array([10, 150, 200]),
                "upper": np.array([25, 255, 255]),
                "region": [0.85, 0.98, 0.35, 0.65],
                "multiplier": 4,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Overwatch 2 gameplay analyst. OW2 is a 5v5 hero shooter by Blizzard.

Key visual cues:
- **Kill feed**: Top-right, shows killer→victim with hero icons, red skull = final blow
- **Hit markers**: White ticks at crosshair on hit, red ticks = headshot, red X = kill
- **Ultimate**: Hero-specific VFX (Genji green blade, DVa blue explosion, Pharah rockets)
- **On Fire**: Orange flame border around hero portrait when performing well
- **Critical HP**: Red pulsing screen edges, desaturated vision
- **Team Kill**: All 5 enemies eliminated, "TEAM KILL" text
- **POTG**: Play of the Game replay with special intro animation

Look for: Multi-kills (double, triple, quad, team kill), big ultimates, clutch plays, environmental kills, support clutch saves, funny deaths, POTG moments, nano combos.
Score 0.0 for: hero select, queue, settings, replay viewer (unless showing a highlight).

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Overwatch 2 gameplay frame. Is this an exciting moment?",
    },

    "rocket_league": {
        "name": "Rocket League",
        "description": "Car soccer — detects goals, goal explosions, saves, aerials, demos, overtime",
        "detectors": {
            "kill_feed": {
                "label": "GOAL! / Score Pop-up",
                "weight": 0.35,
                # Goal: large "GOAL!" text center screen, instant replay triggered
                # Score pop-up: points appear center-right (+100 Goal, +50 Assist, etc.)
                # Overtime: "OVERTIME" text, golden filter
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 40, 255]),
                # Goal text appears large center screen
                "region": [0.15, 0.50, 0.20, 0.80],
                "multiplier": 9,
            },
            "damage": {
                "label": "Boost Meter",
                "weight": 0.10,
                # Boost meter: bottom-right circle, orange/yellow fill
                # 100 boost: full orange circle
                # Boost trail: colored flame behind car (orange default, customizable)
                "lower": np.array([15, 100, 180]),
                "upper": np.array([30, 255, 255]),
                # Boost meter bottom-right
                "region": [0.85, 0.98, 0.85, 0.98],
                "multiplier": 2,
            },
            "hit_marker": {
                "label": "Ball Contact / Aerial",
                "weight": 0.20,
                # Ball hit: white impact particles on contact
                # Aerial touch: car flying through air, special "Aerial Hit" notification
                # Ball trail: glowing trail showing ball trajectory
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Goal Explosion / Demo",
                "weight": 0.25,
                # Goal explosion: custom VFX fills half the screen (fire, confetti, etc.)
                # Demolition: car explodes into parts, bright orange flash
                # Goal explosions are extremely bright and colorful
                "lower": np.array([10, 120, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Save / Epic Save",
                "weight": 0.05,
                # "Epic Save!" / "Save!" notification top-right
                # "Aerial Goal!", "Bicycle Hit", "Flip Reset" notifications
                # These are white/blue text notifications
                "lower": np.array([100, 80, 180]),
                "upper": np.array([130, 255, 255]),
                "region": [0.02, 0.20, 0.60, 0.98],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        # Rocket League plays are fast — shorter clips
        "merge_gap": 5, "min_clip_duration": 8, "max_clip_duration": 25, "clip_extension": 4, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Rocket League gameplay analyst. Rocket League is car soccer by Psyonix.

Key visual cues:
- **GOAL!**: Large text center screen, instant replay, goal explosion fills arena
- **Goal explosion**: Custom VFX — can be fire, confetti, black hole, paint splash, etc.
- **Demolition**: Opponent car explodes into parts, bright orange flash
- **Aerial**: Car flying through air, special angle, "Aerial Hit" notification
- **Save**: "Save!" or "Epic Save!" notification when ball cleared from goal
- **Boost**: Orange circle meter bottom-right, glowing trail behind car
- **Overtime**: Golden filter, "OVERTIME" text, sudden death
- **Score pop-ups**: "+100 Goal", "+50 Assist", "+20 Clear" notifications

Look for: Goals (especially aerial goals, flip resets, double taps), epic saves, ceiling shots, demolitions, overtime winners, passing plays, 0-second goals, team plays, freestyle goals.
Score 0.0 for: kickoff waiting, replays of boring goals, free play training, menu screens.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Rocket League gameplay frame. Is this an exciting moment?",
    },

    "dead_by_daylight": {
        "name": "Dead by Daylight",
        "description": "Horror — detects skill checks, hooks, chases, escapes, moris",
        "detectors": {
            "kill_feed": {
                "label": "Hook / Sacrifice / Mori",
                "weight": 0.25,
                # Hook notification: survivor icon changes state on left side HUD
                # Sacrifice: entity claws animation, survivor removed from game
                # Mori: special kill animation, camera zooms in
                # "Entity Displeased/Pleased" at end
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                # Survivor status icons are on the LEFT side of screen
                "region": [0.30, 0.70, 0.02, 0.20],
                "multiplier": 6,
            },
            "damage": {
                "label": "Injured / Terror Radius",
                "weight": 0.25,
                # Injured state: red edges pulsing, blood drops on screen
                # Terror radius: heartbeat sound + red vignette intensifies
                # Dying state: heavy red overlay, crawling
                # Deep wound: bright red timer bar on screen
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Skill Check Circle",
                "weight": 0.20,
                # Skill check: circular UI element center screen
                # Great skill check: smaller bright zone within circle
                # Failed skill check: generator regresses, loud noise notification
                # Skill checks appear during gen repair, healing, hook attempts
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                # Skill check appears center screen
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Generator Complete / Flashlight",
                "weight": 0.20,
                # Gen complete: bright yellow flash, lights turn on around map
                # Flashlight blind: bright white cone aimed at killer
                # Firecracker: bright flash + bang
                # Endgame Collapse: entity claws close in from edges, orange/red
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Hatch / Exit Gate",
                "weight": 0.10,
                # Hatch: trapdoor with orange/yellow glow on ground
                # Exit gate: red/green switch, bright opening
                # Endgame collapse: orange entity tendrils at screen edges
                "lower": np.array([0, 80, 60]),
                "upper": np.array([10, 255, 200]),
                "region": "edges",
                "edge_size": 0.2,
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.5, "brightness_multiplier": 2,
        "intensity_threshold": 0.25, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Dead by Daylight gameplay analyst. DbD is an asymmetric horror game (1 killer vs 4 survivors).

Key visual cues:
- **Hook**: Survivor impaled on hook, entity claws appear on 2nd/3rd stage
- **Mori**: Special kill animation, camera zooms in on killer performing finisher
- **Skill check**: Circular UI center screen during gen repair/healing, bright zones to hit
- **Terror radius**: Red vignette edges intensify as killer approaches, heartbeat sound
- **Generator complete**: Bright yellow flash, area lights turn on, notification pop-up
- **Injured state**: Red pulsing screen edges, blood drops, darker vision
- **Endgame collapse**: Orange entity tendrils at screen edges, timer counting down
- **Hatch**: Trapdoor with orange/yellow glow, last survivor's escape

Look for: Flashlight saves, pallet stuns, hooks, moris, gen pops, clutch escapes, hatch escapes, endgame collapses, killer grabs, 360 jukes, locker escapes, head-on stuns.
Score 0.0 for: walking between gens, hiding in lockers (unless tense), loading, lobby.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Dead by Daylight gameplay frame. Is this an exciting moment?",
    },

    "escape_from_tarkov": {
        "name": "Escape from Tarkov",
        "description": "Hardcore FPS — detects firefights, headshots, bleeds, extractions, deaths",
        "detectors": {
            "kill_feed": {
                "label": "PMC / Scav Kill",
                "weight": 0.30,
                # Tarkov has no traditional kill feed — kills confirmed by looting dog tags
                # "Killed" notification appears briefly bottom-right for scav kills
                # PMC kill: no UI indicator, just the body dropping
                # After-raid screen shows kills, but in-raid it's mostly visual
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                # Kill text bottom-right when it does appear
                "region": [0.80, 0.98, 0.60, 0.98],
                "multiplier": 8,
            },
            "damage": {
                "label": "Bleeding / Fracture",
                "weight": 0.25,
                # Heavy bleeding: red blood drops on screen, red vignette
                # Fracture: screen wobbles, can't sprint
                # Contusion (head hit): blurry/dark vision, ear ringing
                # Dehydration/energy: darkening edges
                # Pain: gray/blurry screen overlay
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Muzzle Flash / Shots Fired",
                "weight": 0.20,
                # Muzzle flash: bright yellow-white flash from gun barrel
                # No hitmarkers in Tarkov — intentionally hardcore
                # Tracer rounds: bright colored streaks through air
                # Ricochet: bright sparks on metal surfaces
                "lower": np.array([15, 80, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Grenade / GL / Mine",
                "weight": 0.18,
                # F-1/RGD grenade: orange flash + shrapnel
                # GL-40: direct impact explosion
                # Flashbang: screen goes completely white
                # Landmine: bright flash under feet
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Extraction Timer",
                "weight": 0.07,
                # Extraction: green countdown timer center screen
                # Double-tap O to check extracts: green text overlay
                # Successful extract: fade to black, raid summary
                "lower": np.array([35, 80, 150]),
                "upper": np.array([85, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 4,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -18,
        "audio_ceiling_db": -5,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Escape from Tarkov gameplay analyst. EFT is a hardcore tactical FPS with permadeath loot.

Key visual cues:
- **No kill feed**: Tarkov intentionally has no kill confirmations — you must loot to confirm
- **Muzzle flash**: Bright flashes from weapon fire, tracers streaking through air
- **Bleeding**: Red blood drops on screen, red vignette intensifying
- **Contusion**: Blurry/darkened vision after head hits, ear ringing
- **Flashbang**: Screen goes completely white for several seconds
- **Grenades**: Orange explosion flash, shrapnel damage
- **Extraction**: Green countdown timer when in extract zone
- **Looting menu**: Inventory screen overlay (indicates found a body or container)
- **Health status**: Body part icons bottom-left showing damage states

Look for: PMC kills (especially multi-kills), squad wipes, "head-eyes" deaths, juicy loot from PMC bodies, close-range fights, sniper shots, grenade plays, successful extractions with valuable loot, scav boss encounters.
Score 0.0 for: stash management, flea market, hideout, trader menus, walking quietly.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Escape from Tarkov gameplay frame. Is this an exciting moment?",
    },

    "pubg": {
        "name": "PUBG",
        "description": "Battle royale — detects kills, blue zone, supply drops, chicken dinners",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Knock",
                "weight": 0.30,
                # PUBG kill feed: top-left corner, shows weapon icon + kill/knock
                # "You knocked down PlayerName" / "You finally killed PlayerName"
                # Kill feed text is white with weapon icons
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                # Kill feed top-left
                "region": [0.02, 0.20, 0.02, 0.40],
                "multiplier": 7,
            },
            "damage": {
                "label": "Blue Zone / Blood",
                "weight": 0.15,
                # Blue zone: bright blue energy wall visible in world
                # Blue zone damage: blue tint at screen edges
                # Blood splatter: red directional indicator when hit
                # Downed: red screen edges, crawling
                "lower": np.array([100, 60, 60]),
                "upper": np.array([130, 255, 200]),
                "lower2": np.array([0, 100, 80]),
                "upper2": np.array([10, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 3,
            },
            "hit_marker": {
                "label": "Blood Splatter Hit",
                "weight": 0.25,
                # PUBG hit indicator: red blood mist from enemy on hit
                # Headshot: distinct sound + more blood
                # Hit direction: red arc on crosshair showing hit direction
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Vehicle / Grenade / Red Zone",
                "weight": 0.20,
                # Vehicle explosion: large orange fireball when car/bike destroyed
                # Grenades: orange-white flash
                # Red zone: random bombing area, large orange explosions falling
                # Molotov: orange fire on ground
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Supply Drop / Flare",
                "weight": 0.05,
                # Supply drop: red smoke trail from crate parachuting down
                # Flare gun: bright red flare in sky
                # "WINNER WINNER CHICKEN DINNER" text at victory
                "lower": np.array([0, 100, 180]),
                "upper": np.array([10, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert PUBG gameplay analyst. PUBG is the original battle royale by Krafton.

Key visual cues:
- **Kill feed**: Top-left, weapon icon between killer→victim, knock vs kill distinction
- **Blue zone**: Bright blue energy wall visible in world, blue screen edges when inside
- **Red zone**: Random bombing area, large orange explosions falling from sky
- **Supply drop**: Red smoke crate parachuting down, contains rare weapons
- **Blood hit**: Red blood mist from enemy when bullets connect
- **Knocked**: Downed player crawls, red screen edges, teammate can revive
- **Vehicle**: Cars/bikes can run over enemies, explode when damaged enough
- **Chicken dinner**: "WINNER WINNER CHICKEN DINNER" victory screen

Look for: Squad wipes, long-range snipes, vehicle plays/explosions, chicken dinners, pan kills, red zone dodging, bridge camping, close-range shotgun fights, clutch revives.
Score 0.0 for: parachuting (unless contested), looting empty buildings, driving peacefully, lobby.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this PUBG gameplay frame. Is this an exciting moment?",
    },

    "destiny_2": {
        "name": "Destiny 2",
        "description": "Looter shooter — detects supers, boss DPS, precision kills, raids, exotic drops",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Precision",
                "weight": 0.25,
                # D2 kill feed: left side of screen, shows weapon + enemy name
                # Precision kills: gold damage numbers, yellow crit text
                # Multi-kills create rapid text feed on left
                # "Guardian Down" in PvP/Gambit
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                # Kill feed is left side
                "region": [0.30, 0.60, 0.02, 0.30],
                "multiplier": 6,
            },
            "damage": {
                "label": "Critical Health / Down",
                "weight": 0.15,
                # Red screen edges when low HP, screen goes red on death
                # "Revive Available" ghost icon where you died
                # Darkness zone: red pulsing warning
                # "Last Guardian Standing" — red alert text
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Precision Hits / Crit",
                "weight": 0.20,
                # Precision kills: gold/yellow damage numbers (vs white for body)
                # Headshot: specific gold crit number + enemy head pops in PvE
                # Hit indicator: white reticle ticks
                "lower": np.array([20, 120, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Super / Ability VFX",
                "weight": 0.25,
                # Supers: class-specific bright VFX covering screen
                # Golden Gun: bright orange fire, Stormtrance: blue lightning
                # Nova Bomb: purple explosion, Thundercrash: arc blue streak
                # Well of Radiance: yellow/orange sword + healing circle
                # Rocket launcher: bright orange trail + explosion
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Exotic Drop / Boss Phase",
                "weight": 0.10,
                # Exotic engram: bright gold/yellow glowing item on ground
                # Raid encounter: boss health bar, wipe mechanic warnings
                # Trials: round counter UI, flawless glow
                # Nightfall: timer + score UI
                "lower": np.array([130, 60, 120]),
                "upper": np.array([160, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Destiny 2 gameplay analyst. D2 is a sci-fi looter shooter MMO by Bungie.

Key visual cues:
- **Kill feed**: Left side, weapon icon + enemy name, rapid text during add clear
- **Precision kills**: Gold/yellow damage numbers (vs white body shots), enemy head pops
- **Super activation**: Bright class-specific glow covering entire character
  - Solar: orange fire, Arc: blue lightning, Void: purple energy, Strand: green threads, Stasis: blue ice
- **Exotic engram**: Bright gold glowing item on ground — rare and exciting
- **Raid boss**: Large health bar, DPS phase with massive damage numbers
- **Guardian Down**: Teammate death notification in raids/dungeons
- **Trials of Osiris**: Round counter, flawless card glow, elimination announcements
- **Wipe**: Darkness zone screen wipe, "Joining Allies" / "Respawning Restricted"

Look for: Super kills (especially multi-kills), raid boss DPS phases, exotic drops, Trials clutches, dungeon boss kills, PvP sprees, rocket launcher multi-kills, clutch revives.
Score 0.0 for: orbit, tower/social space, inventory management, shader preview, loading.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Destiny 2 gameplay frame. Is this an exciting moment?",
    },

    "elden_ring": {
        "name": "Elden Ring",
        "description": "Action RPG — detects boss fights, deaths, critical hits, parries, invaders",
        "detectors": {
            "kill_feed": {
                "label": "ENEMY FELLED / GREAT ENEMY FELLED",
                "weight": 0.30,
                # "ENEMY FELLED" / "GREAT ENEMY FELLED": large gold text center screen
                # "DEMIGOD FELLED": gold text with rune reward
                # Rune gain: gold numbers pop up after kills
                # These are bright white/gold text on dark backgrounds
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                # Felled text appears center screen
                "region": [0.30, 0.70, 0.20, 0.80],
                "multiplier": 9,
            },
            "damage": {
                "label": "YOU DIED",
                "weight": 0.25,
                # "YOU DIED": large red text center screen, very saturated red
                # Screen goes dark, red text fades in
                # Also appears on fall deaths, status deaths, invader kills
                "lower": np.array([0, 120, 150]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 150]),
                "upper2": np.array([180, 255, 255]),
                # YOU DIED text center screen
                "region": [0.35, 0.65, 0.25, 0.75],
                "multiplier": 7,
            },
            "hit_marker": {
                "label": "Critical / Riposte / Backstab",
                "weight": 0.15,
                # Critical hit: bright white flash on weapon impact, unique animation
                # Riposte after parry: white flash + camera zoom
                # Backstab: camera angle change + white flash
                # Guard counter: white spark animation
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Magic / Incantation / Ash of War",
                "weight": 0.20,
                # Sorceries: blue/purple glintstone VFX (Comet Azur, Stars of Ruin)
                # Incantations: golden/red dragon fire, lightning, holy light
                # Ash of War: weapon art VFX (Moonveil blue slash, RoB red slashes)
                # Comet Azur: massive blue beam fills screen
                "lower": np.array([15, 100, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Boss Health Bar",
                "weight": 0.05,
                # Boss health bar: long white bar at very bottom of screen
                # Boss name in gold text above health bar
                # Phase transition: boss health bar refills, cutscene
                # Grace discovered: golden particles + "Site of Grace" text
                "lower": np.array([0, 0, 180]),
                "upper": np.array([180, 40, 255]),
                # Boss health bar is at the very bottom
                "region": [0.92, 0.99, 0.10, 0.90],
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 90, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Elden Ring gameplay analyst. Elden Ring is an open-world action RPG by FromSoftware.

Key visual cues:
- **YOU DIED**: Large red text center screen — iconic death screen
- **ENEMY FELLED**: Gold text center screen when boss/enemy killed + rune reward
- **GREAT ENEMY FELLED**: Gold text for major boss kills (demigods, shardbearers)
- **Boss health bar**: Long white bar at bottom of screen with boss name above
- **Phase transition**: Boss health bar refills, dramatic cutscene
- **Critical hit**: Bright white flash, unique riposte/backstab animation
- **Sorcery**: Blue/purple glintstone VFX (Comet Azur is a huge blue beam)
- **Incantation**: Golden/red VFX (dragon breath, lightning spear, healing)
- **Invader**: "You have been invaded" notification, red phantom appears
- **Grace**: Golden light particles at rest sites

Look for: Boss kills (especially first tries), YOU DIED montages, clutch parries, Comet Azur one-shots, invader fights, speed kills, funny deaths, no-hit runs, Rivers of Blood spam, gravity deaths.
Score 0.0 for: riding Torrent peacefully, crafting, map browsing, level-up screen, site of grace rest.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Elden Ring gameplay frame. Is this an exciting moment?",
    },

    "helldivers_2": {
        "name": "Helldivers 2",
        "description": "Co-op shooter — detects stratagems, bug kills, extractions, friendly fire, orbital strikes",
        "detectors": {
            "kill_feed": {
                "label": "Bug / Bot Kill",
                "weight": 0.25,
                # Bug kills: green blood splatter, dismemberment
                # Automaton kills: sparks + metal debris
                # Kill notifications in bottom-left feed
                # Teammate death: skull icon + name
                "lower": np.array([35, 80, 100]),
                "upper": np.array([85, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed bottom-left
                "region": [0.75, 0.95, 0.02, 0.40],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage / Down",
                "weight": 0.20,
                # Red screen edges when hit, blood overlay
                # Down: screen goes red, ragdoll death, respawn timer
                # Friendly fire: same red indicators
                # Charger charge: screen shakes
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Gunfire / Muzzle Flash",
                "weight": 0.15,
                # Muzzle flash: bright yellow-white from weapon
                # Tracer rounds: bright streaks
                # Autocannon: larger flash, explosive rounds
                # Railgun: bright blue energy beam
                "lower": np.array([15, 80, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Stratagem / Orbital Strike",
                "weight": 0.30,
                # Orbital strikes: MASSIVE orange explosion from sky
                # Eagle airstrikes: bright orange napalm/cluster bombs
                # 500kg bomb: huge white flash + shockwave
                # Hellpod reinforce: bright trail + impact
                # Bile Titan acid: green pool on ground
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Extraction Shuttle / Objective",
                "weight": 0.07,
                # Extraction: blue beacon light, Pelican shuttle incoming
                # Objectives: blue/yellow waypoint markers
                # Sample pickup: green/orange/purple orbs
                # SEAF artillery: bright flash in sky
                "lower": np.array([100, 80, 150]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Helldivers 2 gameplay analyst. HD2 is a co-op third-person shooter about spreading democracy.

Key visual cues:
- **Orbital strikes**: Massive orange explosions from sky, screen-filling VFX
- **Eagle airstrikes**: Bright orange napalm trails, cluster bombs
- **500kg bomb**: Huge white flash + shockwave, kills everything in radius
- **Bug splatter**: Green blood, dismemberment (Terminids)
- **Automaton debris**: Sparks, metal flying (robots)
- **Charger**: Large armored bug charges at player, ground shaking
- **Bile Titan**: Massive enemy, acid spit green pools
- **Extraction**: Blue beacon light, Pelican shuttle descending
- **Reinforce**: Hellpod drops from sky with teammate respawn
- **Friendly fire**: Red damage from teammate, very common and funny

Look for: Orbital strike multi-kills, 500kg bomb plays, charger/bile titan takedowns, clutch extractions, friendly fire deaths, team wipes, stratagem combos, railgun shots, funny deaths, democracy spreading.
Score 0.0 for: walking to objective, calling in loadout (unless under fire), ship bridge, customize screen.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Helldivers 2 gameplay frame. Is this an exciting moment?",
    },

    "rainbow_six_siege": {
        "name": "Rainbow Six Siege",
        "description": "Tactical FPS — detects kills, breaches, drones, clutches, aces",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Headshot",
                "weight": 0.30,
                # R6 kill feed: top-right corner, shows operator icon + kill info
                # Headshot icon (crosshair) next to kill
                # Your kills highlighted in white, assists in gray
                # "ACE" notification when all 5 killed
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 100, 180]),
                "upper2": np.array([15, 255, 255]),
                # Kill feed top-right
                "region": [0.01, 0.20, 0.55, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "DBNO / Taking Damage",
                "weight": 0.20,
                # DBNO (Down But Not Out): red screen, crawling state
                # Taking damage: red directional indicator at edges
                # Blood spatter on screen when hit
                # White screen flash on death
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Kill Confirm X",
                "weight": 0.20,
                # White X at crosshair on kill confirmation
                # Hitmarker: small white ticks at crosshair on hit
                # Headshot: different sound + instant kill
                # Injure: DBNO notification pop-up
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 20, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Breach / C4 / Impact",
                "weight": 0.18,
                # Breach charge: orange explosion on wall/floor
                # C4 (Nitro cell): orange-white explosion
                # Impact grenade: orange flash on wall
                # Thermite: bright orange exothermic charge
                # Fuze cluster charge: multiple orange explosions
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Drone / Gadget Spotted",
                "weight": 0.07,
                # Drone view: yellow/white outline on spotted enemies
                # Camera: yellow "DETECTED" warning to enemy
                # Operator gadgets have unique colored effects
                # Clash shield: electric blue sparks
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.02, 0.12, 0.75, 0.98],
                "multiplier": 3,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        # Siege rounds are short — shorter clips
        "merge_gap": 5, "min_clip_duration": 8, "max_clip_duration": 35, "clip_extension": 5, "pre_pad": 3,
        "ai_system_prompt": """You are an expert Rainbow Six Siege gameplay analyst. R6 is a 5v5 tactical FPS by Ubisoft.

Key visual cues:
- **Kill feed**: Top-right, operator icons + kill info, headshot icon for headshots
- **Kill confirm**: White X at crosshair when enemy killed
- **DBNO**: Red screen overlay when downed, crawling state
- **Breach**: Orange explosion blowing open walls/floors/hatches
- **C4/Nitro**: Orange-white explosion, can kill through walls
- **Thermite**: Bright orange exothermic breach on reinforced walls
- **Drone view**: Yellow outlines on scanned enemies
- **ACE**: All 5 enemies killed by one player
- **Clutch**: 1vX situation, last operator alive

Look for: Aces, 1v5 clutches, wallbangs, C4 kills, spawn peeks, Thermite breach kills, headshot flicks, Fuze cluster kills, Montagne plays, nitro cell plays.
Score 0.0 for: drone phase, operator select, prep phase (unless spawn peeking), loading.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Rainbow Six Siege gameplay frame. Is this an exciting moment?",
    },

    # ===== NEW GAMES =====

    "dota_2": {
        "name": "Dota 2",
        "description": "MOBA — detects kills, teamfights, Roshan, buybacks, rampages",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Rampage",
                "weight": 0.30,
                # Kill notifications: top area, shows hero icons killer→victim
                # Multikill banners: "DOUBLE KILL", "TRIPLE KILL", "ULTRA KILL", "RAMPAGE"
                # These appear large center-top with gold/red text
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.02, 0.25, 0.30, 0.70],
                "multiplier": 8,
            },
            "damage": {
                "label": "Low HP / Death",
                "weight": 0.20,
                # Health bar above hero: green bar depleting
                # Death: gray screen, respawn timer
                # Bloodseeker Rupture: red screen edges
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.40, 0.60],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Spell / Ability VFX",
                "weight": 0.15,
                # Abilities create massive VFX: Invoker Sun Strike, Enigma Black Hole
                # Spell impacts produce bright colored flashes
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Teamfight VFX",
                "weight": 0.25,
                # Teamfights: screen full of spell VFX from multiple heroes
                # Earthshaker Echo Slam, Tidehunter Ravage, Enigma Black Hole
                # Crystal Maiden ult: blue blizzard
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Roshan / Aegis",
                "weight": 0.07,
                # Roshan pit: dark area, boss fight
                # Aegis pickup: golden glow
                # Buyback: gold cost, respawn flash
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Dota 2 gameplay analyst. Dota 2 is a 5v5 MOBA by Valve with deep strategy and hero abilities.

Key visual cues:
- **Kill feed**: Top area, hero portraits showing killer→victim with gold bounty
- **Multikill banners**: "DOUBLE KILL" through "RAMPAGE" (5 kills) in gold/red text
- **Teamfights**: Screen fills with colored spell VFX from 10 heroes fighting simultaneously
- **Death**: Screen goes gray, respawn countdown timer
- **Roshan**: Large boss in pit, drops Aegis of the Immortal (gold glow)
- **Buyback**: Hero instantly respawns by spending gold, flash of light
- **Aegis resurrection**: Hero dies then resurrects with golden particle effect
- **Black Hole**: Enigma's iconic purple/black vortex that sucks enemies in
- **Rampage**: All 5 enemies killed by one hero in short time, dramatic banner

Look for: Rampages, teamfight wins, Black Hole combos, Roshan steals, 1v5 plays, fountain dives, courier snipes, Techies mines, million dollar Echo Slams, buyback plays, base race finishes.
Score 0.0 for: farming jungle, laning phase (unless kills happening), shop, hero select, paused.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Dota 2 gameplay frame. Is this an exciting moment?",
    },

    "rust": {
        "name": "Rust",
        "description": "Survival — detects raids, PvP fights, airdrops, helicopter, base defense",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Down",
                "weight": 0.30,
                # Kill notification: bottom-right chat area
                # "PlayerName was killed by PlayerName"
                # PvP kills show weapon used
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.75, 0.95, 0.50, 0.98],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage / Bleeding",
                "weight": 0.20,
                # Red screen edges when hit, blood overlay
                # Radiation: green tint at edges (rad zones)
                # Cold: blue tint at edges
                # Bleeding: red pulsing, HP decreasing
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Gunshot / Muzzle Flash",
                "weight": 0.20,
                # Red X hitmarker at crosshair on kill
                # White hitmarker on hit
                # Muzzle flash: bright yellow-white from weapon
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Raid / C4 / Rockets",
                "weight": 0.25,
                # C4 explosion: bright orange flash on base walls
                # Rocket: orange trail + large explosion
                # Satchel charge: smaller orange explosion
                # MLRS rocket: massive orange explosion
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Helicopter / Airdrop",
                "weight": 0.07,
                # Attack helicopter: red tracers, rockets
                # Supply drop: red smoke, parachute
                # Chinook: large helicopter event
                # Patrol helicopter shoots at armed players
                "lower": np.array([0, 100, 180]),
                "upper": np.array([10, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Rust gameplay analyst. Rust is an open-world survival PvP game by Facepunch.

Key visual cues:
- **Kill feed**: Chat area bottom-right, death messages with weapon used
- **Hitmarker**: White X on hit, red X on kill at crosshair
- **Raid**: C4/rocket explosions on base walls, orange flash + debris
- **Attack helicopter**: Red tracer fire from sky, rockets, explosion VFX
- **Airdrop**: Red smoke beacon, parachute crate descending
- **Radiation**: Green tint/icons in rad zones near monuments
- **Bleeding**: Red pulsing screen edges, blood drops
- **Base building**: Construction/upgrade VFX
- **Recycling/crafting**: UI overlay screens

Look for: Online raids, PvP fights (especially roof camps, compound fights), helicopter takedowns, airdrop contests, door camping kills, eoka plays, naked plays, compound bow flicks, counter raids, base defense.
Score 0.0 for: farming nodes/trees, building alone, crafting, running naked, cooking.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Rust gameplay frame. Is this an exciting moment?",
    },

    "the_finals": {
        "name": "The Finals",
        "description": "FPS — detects kills, cashouts, destruction, abilities, team wipes",
        "detectors": {
            "kill_feed": {
                "label": "Elimination / Cashout",
                "weight": 0.30,
                # Kill feed: top-right corner with player names
                # Cashout progress: center UI element
                # Team wipe: all enemies eliminated
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 120, 170]),
                "upper2": np.array([10, 255, 255]),
                "region": [0.01, 0.20, 0.60, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red directional damage indicator
                # Low HP: red screen edges
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitting Shots",
                "weight": 0.25,
                # White hitmarker ticks at crosshair
                # Red for kill confirmed
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Destruction / Ability",
                "weight": 0.25,
                # Building destruction: massive debris, dust clouds
                # RPG/C4: orange explosions
                # Abilities: various colored VFX
                # Floor collapse: buildings crumbling
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Cashout Station",
                "weight": 0.05,
                # Cashout: gold/yellow UI elements, progress bar
                # Vault: gold glowing container
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 4,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert The Finals gameplay analyst. The Finals is a team-based FPS with destructible environments by Embark Studios.

Key visual cues:
- **Kill feed**: Top-right, shows eliminations with player names
- **Destruction**: Buildings crumble, floors collapse, walls blown open — massive debris VFX
- **Cashout**: Gold-colored station, progress bar, teams fighting over vault
- **Hitmarker**: White ticks at crosshair, red for kill
- **Abilities**: Class-specific VFX (Light grapple, Medium heal, Heavy shield)
- **RPG/C4**: Large orange explosions destroying environment
- **Revive**: Teammate resurrection with VFX
- **Vault**: Gold glowing container carried by team

Look for: Multi-kills during cashout fights, insane destruction plays (collapsing buildings on enemies), TPV kills, C4 ambushes, clutch cashout steals, squad wipes, goo plays, sniper flicks.
Score 0.0 for: running between objectives, menu, character customization, waiting.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this The Finals gameplay frame. Is this an exciting moment?",
    },

    "marvel_rivals": {
        "name": "Marvel Rivals",
        "description": "Hero shooter — detects kills, abilities, ultimates, team plays",
        "detectors": {
            "kill_feed": {
                "label": "Elimination / KO",
                "weight": 0.30,
                # Kill feed: top-right showing hero icons killer→victim
                # Multi-kill notifications
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.01, 0.20, 0.55, 0.99],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red damage indicators at screen edges
                # Low HP warning
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitting / Crit",
                "weight": 0.20,
                # Hitmarker at crosshair
                # Critical hits show larger markers
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Ultimate / Super",
                "weight": 0.25,
                # Hero ultimates: bright screen-filling VFX
                # Iron Man beams, Spider-Man web attacks, Thor lightning
                # Team-up abilities: coordinated hero combos
                "lower": np.array([10, 120, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Team-Up Ability",
                "weight": 0.07,
                # Team-up abilities: special combo between specific heroes
                # Bright colored VFX unique to each combo
                "lower": np.array([100, 80, 150]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Marvel Rivals gameplay analyst. Marvel Rivals is a 6v6 hero shooter featuring Marvel characters by NetEase.

Key visual cues:
- **Kill feed**: Top-right, hero portraits showing killer→victim
- **Ultimates**: Hero-specific VFX — Iron Man repulsor blast, Spider-Man web attacks, Thor lightning, Hulk ground slam
- **Team-up abilities**: Special combo VFX between specific hero pairs (unique to Marvel Rivals)
- **Hitmarker**: Ticks at crosshair on hit, larger for crits
- **Multi-kill**: "DOUBLE KILL", "TRIPLE KILL" etc. notifications
- **Map objectives**: Capture point progress, payload movement
- **Death**: Respawn timer, spectate view

Look for: Multi-kills, big ultimates (especially team-wipes), team-up ability combos, clutch plays, impressive aim/tracking, environmental kills, funny moments with hero abilities.
Score 0.0 for: hero select, lobby, walking to point, settings.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Marvel Rivals gameplay frame. Is this an exciting moment?",
    },

    "diablo_4": {
        "name": "Diablo IV",
        "description": "ARPG — detects boss kills, legendary drops, PvP, dungeon clears, world bosses",
        "detectors": {
            "kill_feed": {
                "label": "Kill / World Boss",
                "weight": 0.25,
                # Mass kills: enemies explode in blood/particles
                # World boss: massive health bar at top
                # Boss kill: "Boss Defeated" notification
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 120, 150]),
                "upper2": np.array([10, 255, 255]),
                "region": [0.20, 0.50, 0.25, 0.75],
                "multiplier": 6,
            },
            "damage": {
                "label": "Low HP / Death",
                "weight": 0.15,
                # Red vignette when low HP
                # Health globe: red orb bottom center
                # Death: screen darkens, respawn UI
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Skill Impact / Crit",
                "weight": 0.15,
                # Critical hits: large yellow/gold damage numbers
                # Skill impacts: bright colored flashes per skill
                # Overpower: blue damage numbers
                "lower": np.array([20, 120, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Ultimate / AoE Skill",
                "weight": 0.30,
                # Ultimate abilities: massive screen-filling VFX
                # AoE skills: bright colored ground effects
                # Barbarian: earth-shattering, Sorcerer: meteor, Necro: corpse explosion
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Legendary / Unique Drop",
                "weight": 0.10,
                # Legendary drop: orange star beam shooting up from ground
                # Unique drop: gold star beam
                # Uber Unique: extremely bright gold beam
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Diablo IV gameplay analyst. D4 is an ARPG with dark gothic themes by Blizzard.

Key visual cues:
- **Monster kills**: Enemies explode in blood and bone, satisfying splatter VFX
- **Legendary drop**: Orange star beam shooting up from ground — exciting loot moment
- **Unique/Uber Unique**: Gold star beam — extremely rare and exciting
- **World boss**: Massive creature with huge health bar at top of screen (Ashava, Wandering Death, Avarice)
- **Ultimate**: Class-specific massive VFX (Barbarian earth slam, Sorcerer meteor, Druid wolf form, Necro army)
- **Critical hits**: Large yellow/gold damage numbers
- **Overpower**: Blue damage numbers
- **PvP**: Fields of Hatred, player markers turn hostile red
- **Dungeon completion**: Boss defeated, loot explosion

Look for: World boss kills, Uber Unique drops, pit clears, PvP kills, massive AoE skill combos, Uber Lilith kills, dungeon speed clears, Torment difficulty first clears, hilarious deaths.
Score 0.0 for: walking between zones, vendor/inventory, character customization, town hub.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Diablo IV gameplay frame. Is this an exciting moment?",
    },

    "cyberpunk_2077": {
        "name": "Cyberpunk 2077",
        "description": "Action RPG — detects combat, hacking, boss fights, vehicle chases",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Neutralize",
                "weight": 0.25,
                # Enemy health bar above their head, depletes
                # "Neutralized" notification on kill
                # XP gain notification
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 120, 170]),
                "upper2": np.array([10, 255, 255]),
                "region": [0.20, 0.50, 0.60, 0.98],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage / Low HP",
                "weight": 0.20,
                # Red edges when hit, directional indicator
                # Low HP: heavy red overlay + warning sounds
                # Cyberpsychosis effects at edges
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Crosshair / Headshot",
                "weight": 0.20,
                # Crosshair hit feedback on enemy
                # Critical hits: larger damage numbers in yellow
                # Headshot: distinct sound + large damage
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Grenade / Quickhack / Vehicle",
                "weight": 0.25,
                # Grenade: orange explosion
                # Quickhack VFX: cyan/teal digital effects
                # Vehicle explosion: large orange fireball
                # Sandevistan (slow-mo): screen color shift
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Quickhack / Cyberware",
                "weight": 0.10,
                # Breach Protocol: teal/cyan digital matrix
                # Quickhack: teal digital lines on enemies
                # Kerenzikov (slow-mo): time warp effect
                # Mantis Blades: red swing VFX
                "lower": np.array([80, 80, 150]),
                "upper": np.array([100, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Cyberpunk 2077 gameplay analyst. CP2077 is an open-world action RPG in a futuristic dystopia by CD Projekt Red.

Key visual cues:
- **Combat**: First-person shooting, melee combat with Mantis Blades/Gorilla Arms
- **Quickhacking**: Teal/cyan digital VFX on enemies, Breach Protocol matrix
- **Sandevistan**: Slow-motion time dilation effect, enemies frozen, fast kills
- **Kerenzikov**: Slow-mo while dodging, matrix-style bullet time
- **Vehicle combat**: Car chases, motorcycle combat, vehicle explosions
- **Boss fights**: Large HP bars, unique arena encounters
- **Mantis Blades**: Red/orange swing VFX, impale animation
- **Grenades**: Orange explosions, tech weapon charge shots
- **Cyberpsychosis**: Screen glitch effects, distortion

Look for: Sandevistan killstreaks (slow-mo multi-kills), quickhack combos, Mantis Blade executions, vehicle chases, boss fights, Kerenzikov dodges, stealth kills, funny glitches, dramatic story moments.
Score 0.0 for: driving peacefully, shopping, inventory, phone calls, walking around Night City, crafting.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Cyberpunk 2077 gameplay frame. Is this an exciting moment?",
    },

    "street_fighter_6": {
        "name": "Street Fighter 6",
        "description": "Fighting game — detects combos, supers, perfects, drive impacts, comebacks",
        "detectors": {
            "kill_feed": {
                "label": "KO / Perfect / Round Win",
                "weight": 0.35,
                # "K.O." text: large centered text when round ends
                # "PERFECT": gold text for flawless round
                # "YOU WIN" / "YOU LOSE" at match end
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.20, 0.80],
                "multiplier": 9,
            },
            "damage": {
                "label": "Health Bar Depletion",
                "weight": 0.20,
                # Health bars at top of screen, left vs right
                # Yellow damage shows before health depletes
                # Critical health: bar flashing red
                "region": "health_bar",
                "bar_region": [0.02, 0.08, 0.10, 0.90],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                    {"lower": np.array([0, 150, 150]), "upper": np.array([10, 255, 255])},
                ],
                "depletion_threshold": 0.15,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Combo Hits / Drive Impact",
                "weight": 0.15,
                # Hit sparks: bright flash on impact
                # Combo counter: number showing hits center screen
                # Drive Impact: purple/blue flash, wall splat
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Super Art / Critical Art",
                "weight": 0.25,
                # Super Art: massive VFX, dramatic camera angle, screen freeze
                # Critical Art (Level 3): cinematic attack, huge damage
                # Drive Rush: blue dashing VFX
                # Burnout: purple aura when Drive Gauge empty
                "lower": np.array([10, 120, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Drive System VFX",
                "weight": 0.05,
                # Drive Impact: purple/blue circular impact
                # Parry: green flash on successful parry
                # Drive Gauge at bottom of screen
                "lower": np.array([130, 60, 120]),
                "upper": np.array([160, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "motion_weight": 0.05, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        # Fighting game rounds are very short
        "merge_gap": 3, "min_clip_duration": 8, "max_clip_duration": 30, "clip_extension": 3, "pre_pad": 2,
        "ai_system_prompt": """You are an expert Street Fighter 6 gameplay analyst. SF6 is a competitive fighting game by Capcom with the Drive system.

Key visual cues:
- **K.O.**: Large centered text when a round is won, dramatic slow-motion
- **PERFECT**: Gold text for flawless round (no damage taken)
- **Super Art**: Cinematic attack VFX, screen freeze, dramatic camera angles
- **Critical Art (Level 3)**: Extended cinematic super with massive damage
- **Drive Impact**: Purple/blue circular flash, can wall splat opponent
- **Drive Rush**: Blue dashing forward with cancel potential
- **Parry**: Green flash on successful parry timing
- **Burnout**: Purple aura when Drive Gauge is empty — vulnerable state
- **Combo counter**: Hit number displayed during combos
- **Health bars**: Top of screen, yellow damage before depletion

Look for: Long combos, Super Art finishes, Perfects, Drive Impact wall splats, clutch comebacks from low HP, parry reads, chip damage KOs, tournament-level plays, disrespect moves.
Score 0.0 for: character select, training mode (unless showcasing tech), menu, loading.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Street Fighter 6 gameplay frame. Is this an exciting moment?",
    },

    "fall_guys": {
        "name": "Fall Guys",
        "description": "Party game — detects eliminations, wins, close finishes, funny fails",
        "detectors": {
            "kill_feed": {
                "label": "Qualified / Eliminated",
                "weight": 0.35,
                # "QUALIFIED!" text: large green text center screen
                # "ELIMINATED!" text: large red text center screen
                # "WINNER!" text: gold crown animation at end
                "lower": np.array([35, 100, 180]),
                "upper": np.array([85, 255, 255]),
                "lower2": np.array([0, 0, 230]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.25, 0.60, 0.20, 0.80],
                "multiplier": 8,
            },
            "damage": {
                "label": "Falling / Obstacle",
                "weight": 0.15,
                # Falling: camera follows bean falling off course
                # Slime: pink/magenta slime covering screen
                # Bonk: impact stars on head hit
                "lower": np.array([0, 100, 150]),
                "upper": np.array([15, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "hit_marker": {
                "label": "Grab / Push",
                "weight": 0.15,
                # Grabbing other players: arm extending
                # Being pushed: camera shakes
                # Diving: forward dive VFX
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 3,
            },
            "explosion": {
                "label": "Crown / Win VFX",
                "weight": 0.25,
                # Crown grab: golden particles, celebration
                # Final round win: confetti, "WINNER" with crown
                # Rewards: colorful VFX at end
                "lower": np.array([20, 100, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Finish Line / Timer",
                "weight": 0.10,
                # Finish line: bright barrier that players dive through
                # Timer running out: red countdown
                # Elimination count reducing
                "lower": np.array([100, 80, 150]),
                "upper": np.array([130, 255, 255]),
                "region": [0.02, 0.15, 0.30, 0.70],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.05, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 5, "min_clip_duration": 10, "max_clip_duration": 35, "clip_extension": 5, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Fall Guys gameplay analyst. Fall Guys is a battle royale party game with bean-shaped characters by Mediatonic.

Key visual cues:
- **QUALIFIED!**: Large green text when player passes round
- **ELIMINATED!**: Large red text when player fails round
- **WINNER!**: Gold crown animation, confetti, celebration VFX
- **Obstacles**: Spinning hammers, swinging pendulums, moving platforms, slime
- **Grabbing**: Players grabbing each other near edges
- **Diving**: Forward dive to reach platforms/finish line
- **Team games**: Color-coded teams competing
- **Finish line**: Bright barrier that players dive through
- **Crown grab**: Final round crown floating, players jumping for it

Look for: Crown wins, close finishes (barely qualifying), funny eliminations, griefing grabs at edges, perfect obstacle runs, last-second qualifications, team game comebacks, Hex-A-Gone clutches.
Score 0.0 for: queue, customization, spectating (unless something amazing), loading.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Fall Guys gameplay frame. Is this an exciting moment?",
    },

    "lethal_company": {
        "name": "Lethal Company",
        "description": "Horror co-op — detects monster encounters, deaths, loot collecting, ship departures",
        "detectors": {
            "kill_feed": {
                "label": "Player Death / Missing",
                "weight": 0.25,
                # Death: screen goes dark/red, spectate view
                # "PlayerName has died" notification
                # End of quota: score tally screen
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.30, 0.70, 0.20, 0.80],
                "multiplier": 6,
            },
            "damage": {
                "label": "Monster Attack / Injury",
                "weight": 0.25,
                # Screen shakes on hit
                # Red flash when damaged
                # Dark environments suddenly lit by flashlight
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Flashlight / Scanner",
                "weight": 0.10,
                # Flashlight beam: bright white cone in dark facility
                # Scanner beep: walkie-talkie static
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 3,
            },
            "explosion": {
                "label": "Landmine / Lightning",
                "weight": 0.20,
                # Landmine: bright orange flash
                # Lightning: bright white flash on moon surface
                # Ship departure: engine glow
                "lower": np.array([10, 80, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Monster Encounter",
                "weight": 0.20,
                # Monsters appear suddenly in dark hallways
                # Screen often goes from dark to monster close-up
                # Bracken: sudden grab, Coil-Head: freeze mechanic
                "lower": np.array([0, 60, 60]),
                "upper": np.array([15, 255, 200]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "audio_weight": 0.35,
        "audio_threshold_db": -20,
        "audio_ceiling_db": -5,
        "motion_weight": 0.05, "motion_multiplier": 2,
        "brightness_weight": 0.05, "brightness_threshold": 0.5, "brightness_multiplier": 3,
        "intensity_threshold": 0.25, "fallback_threshold_ratio": 0.4,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Lethal Company gameplay analyst. Lethal Company is a co-op horror game about collecting scrap on dangerous moons by Zeekerss.

Key visual cues:
- **Monster encounters**: Sudden appearance of creatures in dark facilities — extremely clip-worthy
- **Deaths**: Screen goes dark/red, often with a jumpscare from monster
- **Dark facilities**: Mostly dark with flashlight beams cutting through
- **Landmine**: Bright orange explosion, usually kills player
- **Lightning**: Bright white flash on outdoor moon surface during storms
- **Bracken**: Tall black figure that grabs and kills, very scary
- **Coil-Head**: Mannequin-like creature that moves when not looked at
- **Ship departure**: Engine glow, door closing, leaving moon
- **Scrap collection**: Picking up various items, quota goal
- **Quota failure**: Being ejected into space, dramatic ending

Look for: Monster jumpscares, player deaths (especially dramatic ones), last-second ship departures, landmine kills, Bracken grabs, Coil-Head encounters, funny teamkills, shovel bonks, quota failures, midnight sun escapes.
Score 0.0 for: walking through empty hallways, ship interior, buying equipment, moon selection.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Lethal Company gameplay frame. Is this an exciting moment?",
    },

    "among_us": {
        "name": "Among Us",
        "description": "Social deduction — detects kills, meetings, votes, ejections, sabotages",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Ejection",
                "weight": 0.30,
                # Kill animation: impostor kills crewmate, brief animation
                # Ejection: "PlayerName was ejected" / "PlayerName was not An Impostor"
                # Body found: alarm sound, report screen
                "lower": np.array([0, 120, 150]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.25, 0.75, 0.15, 0.85],
                "multiplier": 8,
            },
            "damage": {
                "label": "Sabotage / Alert",
                "weight": 0.20,
                # Reactor meltdown: red flashing screen
                # O2 depletion: red warning UI
                # Lights sabotage: dark screen with small vision circle
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Task Completion",
                "weight": 0.10,
                # Task bar progress: green bar at top
                # Task completion: brief animation/mini-game
                "lower": np.array([35, 80, 150]),
                "upper": np.array([85, 255, 255]),
                "region": [0.02, 0.05, 0.20, 0.80],
                "multiplier": 2,
            },
            "explosion": {
                "label": "Emergency Meeting",
                "weight": 0.25,
                # Emergency meeting: red button slam, screen flashes
                # Body report: alarm, body icon
                # Voting screen: colored characters, chat
                "lower": np.array([0, 150, 180]),
                "upper": np.array([10, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Vent / Suspicious Activity",
                "weight": 0.15,
                # Vent animation: player entering/exiting vent
                # Kill animation: brief murder animation
                # Security cameras: green indicator light
                "lower": np.array([35, 100, 120]),
                "upper": np.array([85, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.25, "fallback_threshold_ratio": 0.4,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Among Us gameplay analyst. Among Us is a social deduction game where impostors try to eliminate crewmates.

Key visual cues:
- **Kill animation**: Brief murder animation — impostor stabs/shoots crewmate
- **Body report**: Alarm sound, body icon, triggers emergency meeting
- **Emergency meeting**: Red button slam, screen flashes red
- **Voting screen**: All players shown, chat messages, voting arrows
- **Ejection**: "PlayerName was ejected" — flying into space animation
- **"Was (not) An Impostor"**: Text revealing if ejected player was impostor
- **Sabotage**: Reactor/O2/Lights — red flashing warnings, dark vision
- **Vent**: Animation of player entering/exiting vents (impostor only)
- **Task bar**: Green progress bar at top of screen

Look for: Kill moments (especially bold kills in front of others), big brain plays, successful ejections, wrong ejections (crewmate ejected), vent catches, stack kills, lights kills, self-report accusations, clutch wins.
Score 0.0 for: doing tasks alone, walking through empty rooms, lobby, settings.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Among Us gameplay frame. Is this an exciting moment?",
    },

    "path_of_exile": {
        "name": "Path of Exile",
        "description": "ARPG — detects boss kills, massive pack clear, currency drops, deaths",
        "detectors": {
            "kill_feed": {
                "label": "Boss Kill / Level Up",
                "weight": 0.25,
                # Boss death: health bar depletes, death VFX
                # Level up: bright golden flash, text notification
                # Act boss kills: dramatic transitions
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.25, 0.55, 0.25, 0.75],
                "multiplier": 7,
            },
            "damage": {
                "label": "Low HP / Death",
                "weight": 0.15,
                # Health/mana: red and blue globes bottom corners
                # Low HP: globe nearly empty, red tint
                # Death: "YOU HAVE DIED" text
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Skill Impact / Pack Clear",
                "weight": 0.15,
                # Skill VFX: bright colored explosions per skill
                # Pack clear: multiple enemies dying simultaneously
                # Shattering: frozen enemies exploding into pieces
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Skill / Herald VFX",
                "weight": 0.30,
                # Skills: massive screen-filling VFX during mapping
                # Herald effects: colored aura/explosions on kill
                # Righteous Fire: orange burning circle around character
                # Cyclone: spinning VFX, Lightning Arrow: blue/white bolts
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Currency / Unique Drop",
                "weight": 0.10,
                # Mirror of Kalandra: most valuable drop, beam of light
                # Exalted Orb: golden glow on ground
                # Unique items: brown text label
                # Map boss portal: swirling portal VFX
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Path of Exile gameplay analyst. PoE is a complex ARPG with deep build customization by Grinding Gear Games.

Key visual cues:
- **Pack clear**: Screen fills with VFX as dozens of monsters die simultaneously
- **Boss phases**: Health bar at top, phase transitions with special mechanics
- **Currency drops**: Exalted Orbs (gold glow), Divine Orbs, Mirror of Kalandra (rarest item in game)
- **Death**: "YOU HAVE DIED" text, XP penalty
- **Skills**: Build-specific VFX — some skills fill entire screen with color
- **Herald effects**: Colored explosions/aura on every kill
- **Level up**: Golden flash, notification
- **Map boss**: Boss arena, unique mechanics, portal to map
- **Breach/Legion/Delirium**: League mechanic spawning massive monster packs

Look for: Boss kills (especially pinnacle bosses: Maven, Uber Elder, Sirus), Mirror drops, Exalt drops, massive pack clear with screen-filling VFX, deaths in hardcore (character deleted!), speed clearing, league mechanic encounters.
Score 0.0 for: hideout, trading, passive tree, stash organizing, town.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Path of Exile gameplay frame. Is this an exciting moment?",
    },

    "warframe": {
        "name": "Warframe",
        "description": "Action shooter — detects kills, abilities, boss fights, loot, extraction",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Affinity",
                "weight": 0.25,
                # Kill counter: bottom-right, accumulates rapidly
                # Affinity notifications: XP gain
                # Boss phase transitions
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.80, 0.98, 0.70, 0.98],
                "multiplier": 5,
            },
            "damage": {
                "label": "Shield/Health Down",
                "weight": 0.15,
                # Shield: blue bar depletes
                # Health: red bar below shield
                # Death: bleedout state, teammate can revive
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Crit / Status Proc",
                "weight": 0.15,
                # Critical hits: yellow/orange large damage numbers
                # Status procs: colored icons (fire, electric, etc.)
                # Headshot multiplier
                "lower": np.array([20, 120, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Warframe Ability",
                "weight": 0.30,
                # Warframe abilities: massive VFX per frame
                # Saryn: green spore explosions, Mesa: golden gun streams
                # Volt: blue electric discharge, Ember: orange fire waves
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Prime Drop / Extraction",
                "weight": 0.10,
                # Rare relic rewards: golden light
                # Extraction: green marker, countdown
                # New prime part: reward screen highlight
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 12, "max_clip_duration": 45, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Warframe gameplay analyst. Warframe is a free-to-play co-op action shooter with space ninjas by Digital Extremes.

Key visual cues:
- **Kill counter**: Bottom-right, rapidly accumulating during missions
- **Warframe abilities**: Massive VFX per Warframe — Saryn green spores, Mesa golden peacemakers, Volt electric discharge, Mirage clones, Wisp reservoirs
- **Bullet jumping**: Acrobatic movement with energy trails
- **Melee combos**: Flashy slash effects, finisher animations
- **Boss fights**: Phase-based encounters with special mechanics (Eidolons, Profit-Taker)
- **Extraction**: Green waypoint, countdown timer
- **Rare drops**: Golden/silver light for rare mods/blueprints
- **Operator/Drifter mode**: Void beam, transference
- **Steel Path**: Harder content, steel essence drops

Look for: Massive ability room clears, Eidolon hunts, boss kills, rare drops, high kill count missions, parkour chains, clutch revives, Arbitration saves, Railjack combat.
Score 0.0 for: orbiter/ship interior, foundry, modding screen, relay/hub, trading.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Warframe gameplay frame. Is this an exciting moment?",
    },

    "halo_infinite": {
        "name": "Halo Infinite",
        "description": "FPS — detects kills, multikills, power weapons, flag captures, Slayer",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Multikill",
                "weight": 0.30,
                # Kill feed: top-right corner
                # Multikill medals: "Double Kill", "Triple Kill", "Overkill", "Killtacular"
                # Medals pop up bottom center
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 120, 170]),
                "upper2": np.array([10, 255, 255]),
                "region": [0.01, 0.20, 0.60, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Shield Down / Low HP",
                "weight": 0.20,
                # Shield: blue/cyan overlay, crackle VFX when broken
                # Shield broken: red health bar exposed
                # Low HP: red screen edges
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Shield Pop / Headshot",
                "weight": 0.25,
                # Hitmarker: white reticle ticks on hit
                # Shield pop: distinct crackle sound + VFX
                # Headshot: red reticle + "Perfect" medal
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Rocket / Grenade / Vehicle",
                "weight": 0.18,
                # Rocket launcher: bright orange explosion
                # Frag grenade: orange flash
                # Plasma grenade: blue stick + explosion
                # Vehicle explosion: large fireball
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Medal / Power Weapon",
                "weight": 0.07,
                # Medal notifications: gold/silver icons bottom center
                # Power weapon spawn: glowing pickup
                # Overshield: golden glow
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.80, 0.98, 0.30, 0.70],
                "multiplier": 4,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 5, "min_clip_duration": 10, "max_clip_duration": 40, "clip_extension": 6, "pre_pad": 4,
        "ai_system_prompt": """You are an expert Halo Infinite gameplay analyst. Halo Infinite is an FPS by 343 Industries/Xbox Game Studios.

Key visual cues:
- **Kill feed**: Top-right, weapon icon between killer→victim
- **Medals**: Gold/silver icons at bottom center — "Double Kill", "Triple Kill", "Overkill", "Killtacular", "Killamanjaro"
- **Shield pop**: Blue crackle VFX when enemy shield breaks — distinctive Halo mechanic
- **Headshot**: Red reticle feedback, "Perfect" medal for all-headshot kill
- **Power weapons**: Rocket Launcher, Sniper, Energy Sword, Gravity Hammer — glowing spawn locations
- **Grenades**: Orange (frag), blue (plasma stick), white (spike)
- **Vehicles**: Warthog, Scorpion tank, Banshee — vehicular kills
- **Grappleshot**: Spartan grappling across map, grabbing weapons/players
- **Repulsor**: Blue blast pushes objects/players

Look for: Multikill sprees (especially Killamanjaro+), Energy Sword rampages, sniper no-scopes, Grappleshot plays, tank kills, Gravity Hammer sprees, Oddball clutches, flag captures under fire.
Score 0.0 for: customization, menu, loading, spectating idle players.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Halo Infinite gameplay frame. Is this an exciting moment?",
    },

    "palworld": {
        "name": "Palworld",
        "description": "Survival — detects Pal captures, boss fights, raids, base defense",
        "detectors": {
            "kill_feed": {
                "label": "Pal Capture / Kill",
                "weight": 0.30,
                # Pal capture: sphere throw, capture animation, success/fail
                # Boss defeat: large Pal/boss health bar depletes
                # XP gain notification
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.20, 0.50, 0.30, 0.70],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red edges when hit
                # Low HP warning
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Gun / Pal Attack",
                "weight": 0.15,
                # Gunshot: muzzle flash, hit indicator
                # Pal abilities: colored VFX per element (fire, water, electric, etc.)
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Pal Ability / Explosion",
                "weight": 0.25,
                # Fire Pal abilities: orange flames
                # Electric abilities: blue lightning
                # Rocket launcher: orange explosion
                # Base raid: multiple explosions
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Capture / Legendary",
                "weight": 0.15,
                # Pal Sphere: bright capture animation
                # Legendary Pal: special aura, unique model
                # Successful capture: celebration VFX
                "lower": np.array([100, 80, 150]),
                "upper": np.array([130, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 6,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Palworld gameplay analyst. Palworld is a survival game with creature capture mechanics (Pals) by Pocketpair.

Key visual cues:
- **Pal Sphere throw**: Throwing capture sphere at weakened Pal, shaking animation
- **Successful capture**: Celebration VFX, Pal added to party
- **Failed capture**: Sphere breaks, Pal escapes
- **Boss fights**: Large Pal/tower boss with big health bar
- **Pal abilities**: Element-specific VFX — fire (orange), water (blue), electric (yellow), dragon (purple)
- **Gunplay**: Assault rifles, rocket launchers, shotguns with muzzle flash
- **Base raids**: Enemies attacking your base, alarms, defense
- **Legendary/Alpha Pals**: Special aura, larger models, harder to catch
- **Butchering**: Dark humor element of the game

Look for: Legendary/Alpha Pal captures, boss tower defeats, base raid defense, PvP fights, Pal combo attacks, funny Pal interactions, massive explosions, clutch captures with low-percentage spheres.
Score 0.0 for: base building, crafting, walking, breeding menu, inventory management.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Palworld gameplay frame. Is this an exciting moment?",
    },
}


def get_profile(game_id):
    """Get a game profile by ID. Checks custom profiles first, falls back to arc_raiders."""
    if game_id in GAME_PROFILES:
        return GAME_PROFILES[game_id]

    # Check custom profiles
    import os, json
    custom_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "custom_profiles.json")
    if os.path.exists(custom_file):
        try:
            with open(custom_file) as f:
                custom = json.load(f)
            if game_id in custom:
                # Merge with arc_raiders defaults so all keys exist
                base = dict(GAME_PROFILES["arc_raiders"])
                base.update(custom[game_id])
                return base
        except (json.JSONDecodeError, KeyError):
            pass

    return GAME_PROFILES["arc_raiders"]


def get_all_games():
    """Return a list of available games for the UI."""
    return [
        {"id": game_id, "name": profile["name"], "description": profile["description"]}
        for game_id, profile in GAME_PROFILES.items()
    ]
