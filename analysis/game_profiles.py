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
        "name": "Arc Raiders v1 (Simple)",
        "description": "Simple detection \u2014 Recommended, works best for most streams",

        "detectors": {
            "kill_feed": {
                "label": "Kill / Elimination",
                "weight": 0.25,
                # Kill notifications: bright white/yellow text top-right
                "lower": np.array([0, 0, 200]),
                "upper": np.array([180, 50, 255]),
                "region": [0.05, 0.25, 0.55, 0.95],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red vignette at screen edges
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
                # Detect health/shield bar depletion bottom-left HUD
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    # White health bar
                    {"lower": np.array([0, 0, 180]), "upper": np.array([180, 40, 255])},
                    # Blue shield bar
                    {"lower": np.array([90, 60, 100]), "upper": np.array([130, 255, 255])},
                ],
                "depletion_threshold": 0.10,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Landing Hits",
                "weight": 0.15,
                # Bright white center crosshair flash
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.4, 0.6, 0.4, 0.6],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion / Combat",
                "weight": 0.15,
                # Orange-yellow muzzle flash / explosions
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "special": {
                "label": "Arc Enemy Encounter",
                "weight": 0.10,
                # Blue glow from Arc enemies
                "lower": np.array([90, 80, 100]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 4,
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
    #   - Health/shield bars: bottom-left, WHITE (health) + BLUE (shield/armor durability)
    #   - No enemy HP bars (by design) — physics-based feedback instead
    #   - No traditional hit markers — crosshair is dynamic (tightens on ADS)
    #   - Enemy scanner beam: White→Blue→Yellow→RED when attacking (universal combat indicator)
    #   - Weak points glow YELLOW on enemies like Bastion
    #   - Muzzle flash: orange-yellow + white energy weapon flash, lower-center screen
    #   - Explosions: screen whites out, orange-red particles
    #   - HUD is predominantly WHITE (community complaint about brightness)
    #   - Ammo counter: bottom-right area
    # Sources: ARC Raiders Wiki, GameRant, Steam Community, Beebom, GameSpot, Epiccarry
    "arc_raiders_v2": {
        "name": "Arc Raiders v2 (Research)",
        "description": "Research-based detection \u2014 tuned to actual HUD colors and enemy visuals",

        "detectors": {
            "muzzle_flash": {
                "label": "Gunfire / Muzzle Flash",
                "weight": 0.30,
                # PRIMARY combat indicator: orange-yellow muzzle flash from weapons
                # fires in the lower-center screen where the weapon model renders
                # Also detect bright white flash from energy weapons
                "lower": np.array([10, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "lower2": np.array([0, 0, 240]),
                "upper2": np.array([180, 40, 255]),
                # Lower half center — weapon/muzzle area
                "region": [0.50, 0.85, 0.30, 0.70],
                "multiplier": 7,
            },
            "red_scanner": {
                "label": "ARC Enemy Aggro",
                "weight": 0.15,
                # ARC enemies switch scanner beam to RED when attacking
                # This is the universal combat indicator across all ARC types
                # (Wasps, Bastions, Turrets, Hornets, etc.)
                # Also detects red damage vignette at screen edges
                "lower": np.array([0, 140, 150]),
                "upper": np.array([8, 255, 255]),
                "lower2": np.array([172, 140, 150]),
                "upper2": np.array([180, 255, 255]),
                # Center gameplay area where enemies appear
                "region": [0.10, 0.75, 0.10, 0.90],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion",
                "weight": 0.15,
                # Large explosions: orange-red with high saturation
                # Restrict to center+lower to avoid sunset/sky false positives
                "lower": np.array([5, 150, 170]),
                "upper": np.array([25, 255, 255]),
                "region": [0.25, 0.90, 0.15, 0.85],
                "multiplier": 5,
            },
            "health_bar": {
                "label": "Health/Shield Drop",
                "weight": 0.15,
                # Health bar (WHITE) + Shield bar (BLUE) — bottom-left HUD
                # Shield = armor durability (damage reduction), not a second health pool
                # Both are bright white/blue per community reports
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.02, 0.22],
                "bar_colors": [
                    # White health bar (very bright, low saturation)
                    {"lower": np.array([0, 0, 180]), "upper": np.array([180, 40, 255])},
                    # Blue shield/armor bar
                    {"lower": np.array([90, 60, 100]), "upper": np.array([130, 255, 255])},
                ],
                "depletion_threshold": 0.10,
                "multiplier": 6,
            },
            "damage_vignette": {
                "label": "Taking Damage",
                "weight": 0.10,
                # Red screen-edge vignette when taking hits
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "weak_point_glow": {
                "label": "Weak Point Hit",
                "weight": 0.05,
                # Enemy weak points glow YELLOW when vulnerable
                # (Bastion kneecaps, rear cylinders, Wasp thrusters)
                "lower": np.array([20, 100, 150]),
                "upper": np.array([40, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "crosshair_activity": {
                "label": "Combat (Crosshair)",
                "weight": 0.10,
                # Dynamic crosshair tightens during ADS/combat
                # Bright white center screen activity during firefights
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 25, 255]),
                # Tight center crosshair region
                "region": [0.43, 0.57, 0.43, 0.57],
                "multiplier": 5,
            },
        },

        # Audio: blend with visual, don't dominate
        "audio_weight": 0.40,
        "audio_threshold_db": -15,
        "audio_ceiling_db": -3,

        # Motion: moderate — gunfights have more motion than walking
        "motion_weight": 0.05,
        "motion_multiplier": 2,

        # Brightness: detect explosion whiteouts
        "brightness_weight": 0.03,
        "brightness_threshold": 0.75,
        "brightness_multiplier": 2,

        # Scoring
        "intensity_threshold": 0.35,
        "fallback_threshold_ratio": 0.4,
        "merge_gap": 8,
        "min_clip_duration": 20,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 8,

        # AI prompt — detailed with Arc Raiders specific knowledge
        "ai_system_prompt": """You are an expert Arc Raiders gameplay analyst. Arc Raiders is a PvE co-op extraction shooter by Embark Studios where players fight robot enemies called ARCs.

IMPORTANT GAME KNOWLEDGE:
- There are NO enemy health bars — enemies show damage through physics (staggering, parts breaking off, rotors failing)
- ARC scanner beams turn RED when attacking (white=patrol, blue=curious, yellow=alert, red=aggro)
- Weak points glow YELLOW (Bastion kneecaps, Wasp thrusters)
- Player HUD: white health bar + blue shield bar (bottom-left), ammo (bottom-right)
- Shield is damage REDUCTION, not a second health pool
- Weapons: Stitcher SMG, Ferro, Rattler, Hullcracker, plus shotguns/energy weapons

Look for these highlights:
- **Active Combat**: Muzzle flash visible, enemies with RED scanners, explosions
- **Kills**: ARC enemies staggering/collapsing/exploding, parts flying off
- **Taking Damage**: Red screen edges, health bar depleting, shield breaking
- **Boss Encounters**: Large ARCs (Bastion, Crusher, Matriarch) in combat
- **Close Calls**: Very low health, downed state, crawling
- **Explosions**: Grenades, environmental destruction, ARC self-destruct
- **Deaths**: Player going down (also entertaining content)

Score 0.0 for: menus, inventory, crafting screens, loading, lobby (Speranza), map screen, settings.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.0 = menu/nothing, 0.3 = minor action, 0.6 = good combat, 0.8 = kill/major, 1.0 = insane play""",
        "ai_user_prompt": "Analyze this Arc Raiders gameplay frame. Is this an exciting moment?",
    },

    "war_thunder": {
        "name": "War Thunder",
        "description": "Military vehicles — detects kills, crits, fires, bomb hits, air kills",

        "detectors": {
            "kill_feed": {
                "label": "Target Destroyed",
                "weight": 0.30,
                # War Thunder kill text: bright yellow/white text center-bottom area
                # "Target Destroyed", "Critical hit", "Hit" messages
                "lower": np.array([18, 80, 200]),
                "upper": np.array([35, 255, 255]),
                # Also check for white text
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.55, 0.85, 0.25, 0.75],  # lower-center where kill msgs appear
                "multiplier": 5,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                # Red damage flash / screen shake indicator
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Critical Hit",
                "weight": 0.15,
                # Crosshair hit confirmation - bright center flash
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion / Bomb Hit",
                "weight": 0.20,
                # Vehicle explosions, bomb blasts — large orange-red bursts
                "lower": np.array([5, 100, 130]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "special": {
                "label": "Vehicle on Fire",
                "weight": 0.10,
                # Fire/smoke from burning vehicles — orange-red with high saturation
                "lower": np.array([0, 130, 140]),
                "upper": np.array([20, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
        },

        "motion_weight": 0.07,
        "motion_multiplier": 3,

        "brightness_weight": 0.03,
        "brightness_threshold": 0.65,
        "brightness_multiplier": 2.5,

        # War Thunder has slower-paced moments, use slightly lower threshold
        "intensity_threshold": 0.35,
        "fallback_threshold_ratio": 0.5,
        "merge_gap": 10,
        "min_clip_duration": 20,
        "max_clip_duration": 60,
        "clip_extension": 10,
        "pre_pad": 6,

        "ai_system_prompt": """You are an expert War Thunder gameplay analyst. You analyze screenshots from War Thunder streams to identify exciting moments worth clipping.

War Thunder is a military vehicle combat game with tanks, planes, ships, and helicopters. Look for:

- **Kills**: "Target Destroyed" messages, enemy vehicles exploding, turrets flying off
- **Critical Hits**: Penetrating shots, ammo rack detonations, one-shot kills
- **Bomb/Rocket Hits**: Air-to-ground strikes, carpet bombing, rocket runs
- **Air Combat**: Dogfights, plane-on-plane kills, anti-air shoots down plane
- **Close Calls**: Near-miss shells, surviving a bomb, clutch repair
- **Vehicle on Fire**: Tanks burning, planes trailing smoke, emergency landings
- **Multi-kills**: Killing several enemies in quick succession
- **Deaths**: Player getting destroyed (can also be funny/dramatic)
- **Sniper Shots**: Long-range kills, satisfying crosshair placement

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}

Score guide: 0.0 = driving around doing nothing, 0.3 = minor combat, 0.6 = good hit or near-miss, 0.8 = kill/destruction, 1.0 = insane multi-kill or clutch play""",
        "ai_user_prompt": "Analyze this War Thunder gameplay frame. Is this an exciting moment?",
    },

    "fortnite": {
        "name": "Fortnite",
        "description": "Battle royale — detects eliminations, shield breaks, builds, storm damage",
        "detectors": {
            "kill_feed": {
                "label": "Elimination",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.02, 0.20, 0.02, 0.40],
                "multiplier": 8,
            },
            "damage": {
                "label": "Shield Break / Damage",
                "weight": 0.20,
                "region": "health_bar",
                "bar_region": [0.92, 0.98, 0.35, 0.65],
                "bar_colors": [
                    {"lower": np.array([100, 80, 120]), "upper": np.array([130, 255, 255])},
                    {"lower": np.array([35, 60, 100]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.15,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Landing Shots",
                "weight": 0.20,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.4, 0.6, 0.4, 0.6],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Explosion / RPG",
                "weight": 0.18,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Storm Damage",
                "weight": 0.07,
                "lower": np.array([130, 60, 80]),
                "upper": np.array([160, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Fortnite gameplay analyst. Look for: Eliminations, build fights, shotgun plays, sniper shots, Victory Royale, close calls, storm escapes, funny moments.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Fortnite gameplay frame. Is this an exciting moment?",
    },

    "apex_legends": {
        "name": "Apex Legends",
        "description": "Battle royale — detects knocks, kills, abilities, shield cracks",
        "detectors": {
            "kill_feed": {
                "label": "Knock / Kill",
                "weight": 0.30,
                "lower": np.array([0, 100, 180]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.05, 0.30, 0.60, 0.98],
                "multiplier": 8,
            },
            "damage": {
                "label": "Shield Crack",
                "weight": 0.20,
                "region": "health_bar",
                "bar_region": [0.02, 0.08, 0.35, 0.65],
                "bar_colors": [
                    {"lower": np.array([0, 0, 200]), "upper": np.array([180, 30, 255])},
                    {"lower": np.array([100, 80, 120]), "upper": np.array([130, 255, 255])},
                    {"lower": np.array([130, 60, 120]), "upper": np.array([160, 255, 255])},
                ],
                "depletion_threshold": 0.15,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Hitting Shots",
                "weight": 0.20,
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Grenade / Ability",
                "weight": 0.18,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Ultimate Ability",
                "weight": 0.07,
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Apex Legends analyst. Look for: Knocks, squad wipes, clutch plays, abilities, movement tech, close-range fights, sniper shots, champion moments.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Apex Legends gameplay frame. Is this an exciting moment?",
    },

    "valorant": {
        "name": "Valorant",
        "description": "Tactical FPS — detects kills, headshots, abilities, spike events",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Ace",
                "weight": 0.30,
                "lower": np.array([0, 120, 180]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 230]),
                "upper2": np.array([180, 30, 255]),
                "region": [0.02, 0.25, 0.60, 0.98],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Headshot",
                "weight": 0.25,
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 20, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 7,
            },
            "explosion": {
                "label": "Ability Effect",
                "weight": 0.18,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "special": {
                "label": "Spike Plant/Defuse",
                "weight": 0.07,
                "lower": np.array([15, 100, 200]),
                "upper": np.array([25, 255, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Valorant analyst. Look for: Kills, aces, clutches, headshots, ability plays, spike plants/defuses, eco round wins.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Valorant gameplay frame. Is this an exciting moment?",
    },

    "call_of_duty": {
        "name": "Call of Duty",
        "description": "FPS — detects kills, killstreaks, hitmarkers, multikills",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Streak",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.15, 0.50, 0.02, 0.35],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                "lower": np.array([0, 80, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 80, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitmarker",
                "weight": 0.25,
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Explosion / Scorestreak",
                "weight": 0.18,
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Killstreak Reward",
                "weight": 0.07,
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.3, 0.7, 0.2, 0.8],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Call of Duty analyst. Look for: Multi-kills, killstreaks, quickscopes, clutch plays, nuke feeds, trick shots, funny deaths.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Call of Duty gameplay frame. Is this an exciting moment?",
    },

    "league_of_legends": {
        "name": "League of Legends",
        "description": "MOBA — detects kills, teamfights, objectives, multikills",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Multikill",
                "weight": 0.30,
                "lower": np.array([0, 100, 180]),
                "upper": np.array([15, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.05, 0.50, 0.70, 0.98],
                "multiplier": 7,
            },
            "damage": {
                "label": "Low Health",
                "weight": 0.20,
                "region": "health_bar",
                "bar_region": [0.90, 0.97, 0.35, 0.55],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Ability Impact",
                "weight": 0.15,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.25, 0.75, 0.25, 0.75],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Teamfight",
                "weight": 0.25,
                "lower": np.array([0, 100, 150]),
                "upper": np.array([180, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Objective / Tower",
                "weight": 0.05,
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.6, 0.9, 0.6, 0.9],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert League of Legends analyst. Look for: Pentakills, baron steals, tower dives, outplays, teamfight wins, close 1v1s, funny fails.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this League of Legends gameplay frame. Is this an exciting moment?",
    },

    "counter_strike": {
        "name": "Counter-Strike 2",
        "description": "Tactical FPS — detects kills, headshots, bomb events, clutches",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Headshot",
                "weight": 0.30,
                "lower": np.array([0, 100, 180]),
                "upper": np.array([15, 255, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.02, 0.25, 0.55, 0.98],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.15,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Crosshair Kill",
                "weight": 0.25,
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 20, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Grenade / Molotov",
                "weight": 0.18,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
            "special": {
                "label": "Bomb Plant / Defuse",
                "weight": 0.07,
                "lower": np.array([15, 100, 200]),
                "upper": np.array([30, 255, 255]),
                "region": [0.7, 0.95, 0.3, 0.7],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert CS2 analyst. Look for: Aces, clutches, AWP flicks, deagle headshots, bomb defuses, ninja defuses, eco round wins.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this CS2 gameplay frame. Is this an exciting moment?",
    },

    "minecraft": {
        "name": "Minecraft",
        "description": "Sandbox — detects combat, boss fights, deaths, lava, explosions",
        "detectors": {
            "kill_feed": {
                "label": "Mob Kill / PvP",
                "weight": 0.20,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.02, 0.15, 0.02, 0.60],
                "multiplier": 5,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.20,
                "region": "health_bar",
                "bar_region": [0.90, 0.97, 0.30, 0.55],
                "bar_colors": [
                    {"lower": np.array([0, 150, 150]), "upper": np.array([10, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Combat / Sword Swing",
                "weight": 0.15,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 4,
            },
            "explosion": {
                "label": "TNT / Creeper",
                "weight": 0.25,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Ender Dragon / Wither",
                "weight": 0.10,
                "lower": np.array([130, 50, 80]),
                "upper": np.array([165, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.05, "motion_multiplier": 2,
        "brightness_weight": 0.05, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Minecraft analyst. Look for: Boss fights, PvP kills, creeper explosions, lava deaths, epic builds, speedrun moments, rare finds, clutch saves.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Minecraft gameplay frame. Is this an exciting moment?",
    },

    "gta_v": {
        "name": "GTA V / Online",
        "description": "Open world — detects kills, explosions, wanted levels, chases",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Wasted",
                "weight": 0.25,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 100, 150]),
                "upper2": np.array([10, 255, 255]),
                "region": [0.02, 0.20, 0.02, 0.40],
                "multiplier": 6,
            },
            "damage": {
                "label": "Low Health",
                "weight": 0.20,
                "region": "health_bar",
                "bar_region": [0.92, 0.98, 0.02, 0.22],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Shooting",
                "weight": 0.15,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Explosion / Crash",
                "weight": 0.25,
                "lower": np.array([8, 120, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Wanted Level",
                "weight": 0.10,
                "lower": np.array([100, 120, 180]),
                "upper": np.array([130, 255, 255]),
                "region": [0.02, 0.08, 0.70, 0.95],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert GTA V analyst. Look for: Car chases, explosions, police fights, PvP kills, stunts, funny ragdolls, heist moments.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this GTA V gameplay frame. Is this an exciting moment?",
    },

    "overwatch": {
        "name": "Overwatch 2",
        "description": "Hero shooter — detects eliminations, ultimates, POTG, team wipes",
        "detectors": {
            "kill_feed": {
                "label": "Elimination",
                "weight": 0.30,
                "lower": np.array([0, 100, 180]),
                "upper": np.array([15, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.02, 0.25, 0.60, 0.98],
                "multiplier": 7,
            },
            "damage": {
                "label": "Critical Health",
                "weight": 0.15,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Hitting Shots",
                "weight": 0.20,
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Ultimate Ability",
                "weight": 0.25,
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "On Fire / POTG",
                "weight": 0.05,
                "lower": np.array([10, 150, 200]),
                "upper": np.array([25, 255, 255]),
                "region": [0.85, 0.98, 0.35, 0.65],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Overwatch 2 analyst. Look for: Team kills, huge ultimates, clutch plays, POTG moments, environmental kills, support saves, funny deaths.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Overwatch 2 gameplay frame. Is this an exciting moment?",
    },

    "rocket_league": {
        "name": "Rocket League",
        "description": "Car soccer — detects goals, saves, aerials, demos, overtime",
        "detectors": {
            "kill_feed": {
                "label": "Goal Scored",
                "weight": 0.35,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 40, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 9,
            },
            "damage": {
                "label": "Boost Pickup",
                "weight": 0.10,
                "lower": np.array([15, 100, 180]),
                "upper": np.array([30, 255, 255]),
                "region": [0.85, 0.98, 0.02, 0.15],
                "multiplier": 2,
            },
            "hit_marker": {
                "label": "Ball Hit / Aerial",
                "weight": 0.20,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Goal Explosion / Demo",
                "weight": 0.25,
                "lower": np.array([10, 120, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Save / Epic Save",
                "weight": 0.05,
                "lower": np.array([100, 80, 180]),
                "upper": np.array([130, 255, 255]),
                "region": [0.02, 0.15, 0.60, 0.98],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 2,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 10, "max_clip_duration": 30, "clip_extension": 5, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Rocket League analyst. Look for: Goals, aerial plays, flip resets, demos, saves, overtime wins, passing plays.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Rocket League gameplay frame. Is this an exciting moment?",
    },

    "dead_by_daylight": {
        "name": "Dead by Daylight",
        "description": "Horror — detects skill checks, hooks, chases, escapes",
        "detectors": {
            "kill_feed": {
                "label": "Hook / Sacrifice",
                "weight": 0.25,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.02, 0.20, 0.60, 0.98],
                "multiplier": 6,
            },
            "damage": {
                "label": "Injured / Dying",
                "weight": 0.20,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.15,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Skill Check",
                "weight": 0.20,
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Generator Pop",
                "weight": 0.20,
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Terror Radius / Heartbeat",
                "weight": 0.10,
                "lower": np.array([0, 80, 60]),
                "upper": np.array([10, 255, 200]),
                "region": "edges",
                "edge_size": 0.2,
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.5, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Dead by Daylight analyst. Look for: Killer grabs, hooks, escapes, pallet stuns, flashlight saves, gen pops, endgame collapse, hatch escapes.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Dead by Daylight gameplay frame. Is this an exciting moment?",
    },

    "escape_from_tarkov": {
        "name": "Escape from Tarkov",
        "description": "Hardcore FPS — detects firefights, looting, extractions, deaths",
        "detectors": {
            "kill_feed": {
                "label": "PMC Kill",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "region": [0.80, 0.98, 0.02, 0.40],
                "multiplier": 8,
            },
            "damage": {
                "label": "Bleeding / Fracture",
                "weight": 0.20,
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Muzzle Flash",
                "weight": 0.20,
                "lower": np.array([15, 80, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Grenade / Explosion",
                "weight": 0.18,
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Extraction",
                "weight": 0.07,
                "lower": np.array([35, 80, 150]),
                "upper": np.array([85, 255, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Tarkov analyst. Look for: PMC kills, squad wipes, juicy loot, close fights, extractions, head-eyes deaths, grenade plays.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Tarkov gameplay frame. Is this an exciting moment?",
    },

    "pubg": {
        "name": "PUBG",
        "description": "Battle royale — detects kills, blue zone, supply drops, vehicle plays",
        "detectors": {
            "kill_feed": {
                "label": "Kill",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([15, 80, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.02, 0.25, 0.02, 0.35],
                "multiplier": 7,
            },
            "damage": {
                "label": "Blue Zone Damage",
                "weight": 0.15,
                "lower": np.array([100, 60, 60]),
                "upper": np.array([130, 255, 200]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 3,
            },
            "hit_marker": {
                "label": "Landing Shots",
                "weight": 0.25,
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Vehicle Explosion",
                "weight": 0.20,
                "lower": np.array([8, 100, 150]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Supply Drop",
                "weight": 0.05,
                "lower": np.array([0, 100, 180]),
                "upper": np.array([10, 255, 255]),
                "region": "full",
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert PUBG analyst. Look for: Kills, squad wipes, vehicle plays, chicken dinners, long range snipes, close calls with blue zone.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this PUBG gameplay frame. Is this an exciting moment?",
    },

    "destiny_2": {
        "name": "Destiny 2",
        "description": "Looter shooter — detects supers, boss DPS, precision kills, raids",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Precision",
                "weight": 0.25,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.15, 0.50, 0.02, 0.30],
                "multiplier": 6,
            },
            "damage": {
                "label": "Low Health / Revive",
                "weight": 0.15,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Precision Hits",
                "weight": 0.20,
                "lower": np.array([20, 120, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Super / Ability",
                "weight": 0.25,
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Exotic / Boss Phase",
                "weight": 0.10,
                "lower": np.array([130, 60, 120]),
                "upper": np.array([160, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Destiny 2 analyst. Look for: Super kills, raid boss DPS, exotic drops, Trials clutches, dungeon clears, PvP sprees.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Destiny 2 gameplay frame. Is this an exciting moment?",
    },

    "elden_ring": {
        "name": "Elden Ring",
        "description": "Action RPG — detects boss fights, deaths, critical hits, summons",
        "detectors": {
            "kill_feed": {
                "label": "Enemy Felled / Boss Kill",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.20, 0.80],
                "multiplier": 9,
            },
            "damage": {
                "label": "YOU DIED",
                "weight": 0.25,
                "lower": np.array([0, 120, 150]),
                "upper": np.array([10, 255, 255]),
                "region": [0.35, 0.65, 0.25, 0.75],
                "multiplier": 7,
            },
            "hit_marker": {
                "label": "Critical / Riposte",
                "weight": 0.15,
                "lower": np.array([0, 0, 235]),
                "upper": np.array([180, 25, 255]),
                "region": [0.3, 0.7, 0.3, 0.7],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Magic / Incantation",
                "weight": 0.20,
                "lower": np.array([15, 100, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 4,
            },
            "special": {
                "label": "Boss Health Bar",
                "weight": 0.05,
                "lower": np.array([0, 0, 180]),
                "upper": np.array([180, 40, 255]),
                "region": [0.92, 0.98, 0.15, 0.85],
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.6, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.4,
        "merge_gap": 10, "min_clip_duration": 20, "max_clip_duration": 90, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Elden Ring analyst. Look for: Boss kills, YOU DIED, clutch dodges, parries, spell combos, invader fights, rare drops.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Elden Ring gameplay frame. Is this an exciting moment?",
    },

    "helldivers_2": {
        "name": "Helldivers 2",
        "description": "Co-op shooter — detects stratagems, bug kills, extractions, friendly fire",
        "detectors": {
            "kill_feed": {
                "label": "Bug Splatter / Kill",
                "weight": 0.25,
                "lower": np.array([35, 80, 100]),
                "upper": np.array([85, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.02, 0.20, 0.60, 0.98],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage",
                "weight": 0.20,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Shooting Bugs",
                "weight": 0.15,
                "lower": np.array([15, 80, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.35, 0.65, 0.35, 0.65],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Stratagem / Orbital Strike",
                "weight": 0.30,
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Extraction / Objective",
                "weight": 0.05,
                "lower": np.array([100, 80, 150]),
                "upper": np.array([130, 255, 255]),
                "region": [0.02, 0.15, 0.02, 0.30],
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 20, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Helldivers 2 analyst. Look for: Orbital strikes, bug breaches, charger kills, bile titan takedowns, team wipes, extractions, friendly fire.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Helldivers 2 gameplay frame. Is this an exciting moment?",
    },

    "rainbow_six_siege": {
        "name": "Rainbow Six Siege",
        "description": "Tactical FPS — detects kills, breaches, drones, clutches",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Headshot",
                "weight": 0.30,
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 100, 180]),
                "upper2": np.array([15, 255, 255]),
                "region": [0.02, 0.25, 0.55, 0.98],
                "multiplier": 8,
            },
            "damage": {
                "label": "DBNO / Damage",
                "weight": 0.20,
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([168, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.1,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Crosshair Kill Confirm",
                "weight": 0.20,
                "lower": np.array([0, 0, 240]),
                "upper": np.array([180, 20, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Breach / C4",
                "weight": 0.18,
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Drone / Camera Spotted",
                "weight": 0.07,
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.02, 0.12, 0.75, 0.98],
                "multiplier": 3,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 15, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Rainbow Six Siege analyst. Look for: Aces, clutches, wall bangs, breach kills, C4 plays, spawn peeks, 1vX clutches.
For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Rainbow Six Siege gameplay frame. Is this an exciting moment?",
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
