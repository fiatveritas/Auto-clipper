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
        "description": "Sci-fi co-op shooter \u2014 detects kills, Arc enemies, damage, explosions",

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
                "weight": 0.20,
                # Red vignette at screen edges
                "lower": np.array([0, 120, 100]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 120, 100]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
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

    "destiny_2": {
        "name": "Destiny 2",
        "description": "FPS looter shooter — detects super abilities, precision kills, exotic drops, raid wipes, crucible kills",
        "detectors": {
            "kill_feed": {
                "label": "Crucible Kill / Precision Kill",
                "weight": 0.30,
                # Crucible kill feed: top-right, shows player names + weapon icon
                # Precision kills: yellow damage numbers pop near crosshair
                # "Guardian Down" red text when teammate dies
                "lower": np.array([20, 130, 200]),
                "upper": np.array([35, 255, 255]),
                # Also catch red "Guardian Down" text
                "lower2": np.array([0, 140, 170]),
                "upper2": np.array([10, 255, 255]),
                # Kill feed top-right
                "region": [0.01, 0.18, 0.65, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage / Low HP",
                "weight": 0.15,
                # Red vignette at screen edges when taking damage
                # Critical health: red pulse overlay
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Precision Hit / Crit",
                "weight": 0.20,
                # White crosshair hit marker on body shots
                # Yellow numbers for precision (headshot) damage
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 6,
            },
            "explosion": {
                "label": "Super Ability / Explosion",
                "weight": 0.25,
                # Super abilities: varied bright VFX per class
                # Solar: orange flames, Arc: blue lightning, Void: purple, Strand: green
                # Rocket launcher explosions: orange-yellow burst
                "lower": np.array([10, 120, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Exotic Drop / Engram",
                "weight": 0.10,
                # Exotic engram: bright gold glow on ground
                # Legendary engram: purple glow
                # Raid loot chest: golden beam of light
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.30, 0.80, 0.20, 0.80],
                "multiplier": 7,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Destiny 2 gameplay analyst. Destiny 2 is a sci-fi FPS looter shooter by Bungie.

Key visual cues:
- **Precision kills**: Yellow damage numbers near crosshair, enemies disintegrate
- **Super abilities**: Screen-filling VFX — Solar (orange fire), Arc (blue lightning), Void (purple), Strand (green threads), Stasis (blue ice)
- **Exotic drops**: Gold engram with bright glow on ground — the rarest and most exciting loot
- **Raid mechanics**: Complex boss encounters, team wipe = red "Wipe" text, darkness zones
- **Crucible kills**: Kill feed top-right, "Guardian Down" red text for teammate deaths
- **Multikill medals**: "Double Down", "Triple Down", "Seventh Column" text
- **Resurrection**: Ghost revive animation, white glow

Look for: Super ability multi-kills, exotic engram drops, raid boss DPS phases, clutch revives, Crucible streaks, Trials of Osiris flawless moments, dungeon boss kills, raid wipe recoveries.
Score 0.0 for: orbit, character menu, tower walking, inventory management, shader preview.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Destiny 2 gameplay frame. Is this an exciting moment?",
    },

    "diablo_4": {
        "name": "Diablo IV",
        "description": "ARPG — detects legendary drops, uber boss fights, massive AoE kills, level-ups, helltide events",
        "detectors": {
            "kill_feed": {
                "label": "Legendary / Unique Drop",
                "weight": 0.30,
                # Legendary drop: orange star beam shooting into the sky
                # Unique drop: gold beam, rarest items
                # Item text: orange for legendary, gold for unique
                "lower": np.array([12, 130, 180]),
                "upper": np.array([25, 255, 255]),
                # Gold unique beam
                "lower2": np.array([22, 140, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage / Low HP",
                "weight": 0.15,
                # Red vignette overlay when taking heavy damage
                # Health globe depletes — bottom-left orb
                "lower": np.array([0, 110, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 110, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.12,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "AoE Kill / Damage Numbers",
                "weight": 0.20,
                # Massive AoE: screen fills with white damage numbers
                # Critical hits: larger yellow numbers
                # Mob packs dying: bright disintegration VFX
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Skill VFX / Boss Attack",
                "weight": 0.25,
                # Skill effects: varied colors per class
                # Sorcerer: blue/white lightning, orange fire
                # Barbarian: red/orange slam effects
                # Necromancer: green/purple corpse explosions
                # Uber boss attacks: massive red/orange AoE markers
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Level Up / Helltide",
                "weight": 0.10,
                # Level-up: bright golden flash centered on character
                # Helltide: red ambient filter, increased enemy density
                # Uber Lilith: distinct purple/red arena
                "lower": np.array([20, 100, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 6,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.35,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Diablo IV gameplay analyst. Diablo IV is an action RPG by Blizzard Entertainment.

Key visual cues:
- **Legendary drops**: Orange star beam shooting skyward from item on ground
- **Unique drops**: Gold beam — rarest items, extremely exciting
- **Uber boss fights**: Large health bars (Duriel, Lilith), arena-wide AoE attacks
- **Massive AoE kills**: Screen fills with damage numbers, mob packs evaporate
- **Level-up**: Golden flash centered on character, XP bar fills
- **Helltide events**: Red ambient overlay, increased enemy density, rare material farming
- **Critical hits**: Large yellow damage numbers vs normal white
- **Death**: Character falls, respawn UI appears

Look for: Uber boss kills, unique/legendary drops, massive mob pack clears, Helltide chest openings, Nightmare Dungeon completions, PvP kills in Fields of Hatred, near-death boss victories, level 100 ding.
Score 0.0 for: walking, inventory management, skill tree, map screen, town NPCs.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Diablo IV gameplay frame. Is this an exciting moment?",
    },

    "helldivers_2": {
        "name": "Helldivers 2",
        "description": "Co-op shooter — detects strategem call-ins, big kills, orbital strikes, extractions, friendly fire",
        "detectors": {
            "kill_feed": {
                "label": "Bug / Bot Kill",
                "weight": 0.25,
                # Kill confirmation: XP numbers pop up on enemy death
                # Charger/Bile Titan kills: large enemies with dramatic death animations
                # Friendly fire notification: red skull icon
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 100, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.30, 0.70, 0.30, 0.70],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage / Down",
                "weight": 0.15,
                # Red screen edges when taking damage
                # Blood splatter on screen
                # Death: ragdoll, respawn via reinforcement stratagem
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Stratagem / Reinforcement",
                "weight": 0.20,
                # Stratagem call-in: blue beam from sky marking drop location
                # Reinforcement beacon: blue/white flare shot into sky
                # Eagle airstrike: red smoke grenade
                "lower": np.array([100, 80, 170]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "explosion": {
                "label": "Orbital Strike / Explosion",
                "weight": 0.30,
                # Orbital strikes: massive screen-filling orange explosions
                # Eagle napalm: wall of orange fire
                # 500kg bomb: huge white flash then fireball
                # Hellbomb: enormous detonation
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 7,
            },
            "special": {
                "label": "Extraction / Countdown",
                "weight": 0.10,
                # Extraction shuttle: bright thruster glow descending
                # Extraction timer: countdown UI element
                # Mission complete: summary screen
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.10, 0.40, 0.30, 0.70],
                "multiplier": 5,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -12,
        "audio_ceiling_db": -2,
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 55, "clip_extension": 10, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Helldivers 2 gameplay analyst. Helldivers 2 is a co-op third-person shooter by Arrowhead Game Studios.

Key visual cues:
- **Strategem call-ins**: Blue beam from sky marks incoming support weapon/vehicle/strike
- **Orbital strikes**: Massive explosions filling screen — 380mm barrage, railcannon, laser
- **Charger/Bile Titan kills**: Large armored bugs requiring heavy weapons to kill
- **Friendly fire**: Red skull icon, teammate ragdolls — common and often hilarious
- **Extraction**: Shuttle descending with bright thrusters, frantic last stand with timer
- **Reinforcement**: Blue flare shot into sky to call back dead teammates
- **Eagle airstrikes**: Red smoke grenade, strafing run explosions
- **Death ragdolls**: Exaggerated physics, flying bodies from explosions

Look for: Orbital strike multi-kills, clutch extractions, friendly fire incidents, Charger/Bile Titan solo kills, Hellbomb detonations, last-second reinforcements, team wipes, hilarious ragdolls, Eagle airstrike chains.
Score 0.0 for: ship menu, loadout screen, walking without enemies, map screen.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Helldivers 2 gameplay frame. Is this an exciting moment?",
    },

    "monster_hunter_world": {
        "name": "Monster Hunter",
        "description": "Action RPG — detects monster staggers, mounts, carts, captures, part breaks, turf wars",
        "detectors": {
            "kill_feed": {
                "label": "Monster Stagger / Topple",
                "weight": 0.25,
                # Monster topple: large creature falls, shows stagger VFX (stars)
                # Part break: sparks fly from broken part, notification text
                # Capture: trap + tranq bomb success, net animation
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 120, 200]),
                "upper2": np.array([40, 255, 255]),
                "region": [0.30, 0.70, 0.25, 0.75],
                "multiplier": 6,
            },
            "damage": {
                "label": "Cart (Death) / Low HP",
                "weight": 0.15,
                # Carting: screen fades to black, "Quest Failed" if 3 carts
                # Low HP: health bar flashes red, character limps
                # Damage taken: red flash at edges
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Weapon Hit / Weak Point",
                "weight": 0.20,
                # Damage numbers: orange for normal, larger numbers for weak points
                # Critical hits: bright spark effects at contact point
                # Mounting: button prompt UI appears, rider animation
                "lower": np.array([12, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Elder Dragon Attack / Turf War",
                "weight": 0.25,
                # Elder dragon attacks: massive elemental VFX filling screen
                # Turf wars: two monsters fighting each other, dramatic animations
                # Barrel bomb explosions: bright orange detonation
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Mount / Capture",
                "weight": 0.15,
                # Mount: button prompt UI, character on monster's back
                # Capture: shock trap/pitfall yellow flash + tranq smoke
                # Quest complete: golden results screen
                "lower": np.array([20, 100, 180]),
                "upper": np.array([35, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 6,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.35,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Monster Hunter gameplay analyst. Monster Hunter is an action RPG series by Capcom.

Key visual cues:
- **Monster stagger/topple**: Large creature falls over, stars/dizzy VFX, opening for attacks
- **Part break**: Sparks fly from broken monster part (horn, tail, wings), notification text
- **Mount**: Character riding on monster's back, button prompts, stabbing animation
- **Carting (death)**: Screen fades, "Fainted" message, cat cart carries hunter back
- **Capture**: Shock trap (yellow flash) or pitfall + tranq bombs, net animation
- **Turf wars**: Two large monsters fighting each other with dramatic attacks
- **Elder dragon attacks**: Screen-filling elemental VFX (fire, ice, thunder, dragon)
- **Quest complete**: Golden banner, reward screen

Look for: Monster captures, elder dragon kills, turf wars, mount finishers, part breaks on tough parts, near-cart clutch wins, speed kills, multi-monster encounters, funny moments with palicos.
Score 0.0 for: gathering, crafting, town hub, canteen eating, menu navigation.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Monster Hunter gameplay frame. Is this an exciting moment?",
    },

    "street_fighter_6": {
        "name": "Street Fighter 6",
        "description": "Fighting game — detects Drive Impact, Super Art, Perfect Parry, Critical Art, KO",
        "detectors": {
            "kill_feed": {
                "label": "KO / Round End",
                "weight": 0.30,
                # KO: large "K.O." text center screen with flash
                # "PERFECT" text if no damage taken
                # Round win: character victory animation
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 40, 255]),
                # Also catch golden "PERFECT" text
                "lower2": np.array([20, 130, 210]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.25, 0.55, 0.25, 0.75],
                "multiplier": 9,
            },
            "damage": {
                "label": "Drive Impact / Hit",
                "weight": 0.20,
                # Drive Impact: blue flash/ink splash on screen impact
                # Hits: white flash at contact point
                # Stun: character dizzy, stars above head
                "lower": np.array([100, 100, 170]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Perfect Parry / Counter",
                "weight": 0.20,
                # Perfect Parry: green flash on defender, time slows briefly
                # Drive Rush: green trail behind rushing character
                # Punish counter: yellow flash
                "lower": np.array([40, 120, 170]),
                "upper": np.array([80, 255, 255]),
                "region": [0.20, 0.80, 0.15, 0.85],
                "multiplier": 7,
            },
            "explosion": {
                "label": "Super Art / Critical Art",
                "weight": 0.25,
                # Super Art: cinematic animation, bright varied VFX per character
                # Critical Art: golden flash, dramatic camera angle
                # Level 3 Super: screen darkens then bright VFX explosion
                "lower": np.array([15, 120, 180]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 8,
            },
            "special": {
                "label": "Drive Rush / Burnout",
                "weight": 0.05,
                # Drive Rush: green trailing VFX on character dash
                # Burnout state: character flashes gray, vulnerable
                # Drive gauge depletion: bottom bar empties
                "lower": np.array([40, 100, 160]),
                "upper": np.array([75, 255, 255]),
                "region": [0.30, 0.80, 0.10, 0.90],
                "multiplier": 4,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.75, "brightness_multiplier": 2,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        # Fighting game rounds are short — shorter clips
        "merge_gap": 4, "min_clip_duration": 8, "max_clip_duration": 30, "clip_extension": 4, "pre_pad": 3,
        "ai_system_prompt": """You are an expert Street Fighter 6 gameplay analyst. SF6 is a fighting game by Capcom with the Drive System.

Key visual cues:
- **Drive Impact**: Blue ink-splash flash on screen, armored attack that can wall splat
- **Super Art**: Cinematic camera angle, bright character-specific VFX
- **Critical Art (Level 3)**: Screen darkens, golden flash, dramatic finisher animation
- **Perfect Parry**: Green flash on defender, time briefly slows, huge punish opportunity
- **KO**: Large "K.O." text center screen with flash, loser falls
- **PERFECT**: Golden text if winner took no damage in the round
- **Drive Rush**: Green trailing VFX on character dash, used for combo extensions
- **Burnout**: Character flashes gray when Drive Gauge depleted, very vulnerable

Look for: Level 3 Super finishes, Perfect Parry into full combo, Drive Impact wall splats, clutch comebacks, Perfect rounds, chip kill finishes, advanced combo extensions, hype tournament moments.
Score 0.0 for: character select, training mode with no action, menu, replay browser.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Street Fighter 6 gameplay frame. Is this an exciting moment?",
    },

    "dota_2": {
        "name": "Dota 2",
        "description": "MOBA — detects team fights, Rampage, Roshan, Aegis steals, ultimates, Ancient destruction",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Rampage",
                "weight": 0.30,
                # Kill feed: top area shows hero icon kills
                # Multikill banners: "DOUBLE KILL", "TRIPLE KILL", "ULTRA KILL", "RAMPAGE"
                # "FIRST BLOOD" text at first kill of the game
                # Red text for dire kills, green for radiant
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed top area
                "region": [0.01, 0.20, 0.30, 0.70],
                "multiplier": 8,
            },
            "damage": {
                "label": "Low HP / Death",
                "weight": 0.15,
                # Health bar: green above hero, turns red when low
                # Death: gray screen, respawn timer
                # Bloodstone/Aegis: golden revive animation
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
                "weight": 0.20,
                # Spells: bright colored VFX
                # Invoker: varied colors per spell combo
                # Black Hole: dark purple vortex, Ravage: blue tentacles
                # Echoslam: orange shockwave
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Teamfight / Ultimate",
                "weight": 0.25,
                # Teamfights: multiple hero abilities create dense VFX
                # Big ultimates: screen fills with colored effects
                # Tidehunter Ravage, Enigma Black Hole, etc.
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Roshan / Aegis",
                "weight": 0.10,
                # Roshan pit: dark area with large monster
                # Aegis pickup: golden glow on hero
                # Ancient destruction: massive golden explosion
                "lower": np.array([20, 120, 190]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.35,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Dota 2 gameplay analyst. Dota 2 is a 5v5 MOBA by Valve.

Key visual cues:
- **Kill feed**: Top area, hero icons showing killer and victim
- **Multikill banners**: "DOUBLE KILL", "TRIPLE KILL", "ULTRA KILL", "RAMPAGE" — center text
- **First Blood**: Special announcement for the first kill of the game
- **Teamfights**: Screen fills with colored ability VFX from multiple heroes
- **Roshan**: Large monster in pit, drops Aegis of the Immortal (golden glow)
- **Big ultimates**: Black Hole (purple vortex), Ravage (blue tentacles), Echo Slam (orange)
- **Ancient destruction**: Massive golden explosion when base structure dies
- **Buyback**: Hero respawns immediately, golden flash

Look for: Rampage kills, Aegis steals, clutch Black Holes, team wipe combos, fountain dives, base race finishes, courier snipes, Roshan steals, million-dollar plays.
Score 0.0 for: laning without action, walking, shop, jungle farming alone, ward placement.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Dota 2 gameplay frame. Is this an exciting moment?",
    },

    "deadlock": {
        "name": "Deadlock",
        "description": "Hero shooter MOBA — detects soul orb pickups, guardian kills, team fights, urn runs, patron damage",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Soul Orb",
                "weight": 0.30,
                # Kill feed: shows hero eliminations
                # Soul orb pickups: glowing orange/yellow orbs on ground
                # Soul secure: gold particles absorbed by player
                "lower": np.array([15, 120, 180]),
                "upper": np.array([30, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.01, 0.20, 0.60, 0.99],
                "multiplier": 7,
            },
            "damage": {
                "label": "Taking Damage / Death",
                "weight": 0.15,
                # Red edge vignette when hit
                # Death: screen desaturates, respawn timer
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Headshot / Ability Hit",
                "weight": 0.20,
                # Crosshair confirms hits with white markers
                # Headshot: larger impact marker
                # Ability impacts: character-specific VFX
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Team Fight / Ability VFX",
                "weight": 0.25,
                # Team fights: multiple hero abilities, dense VFX
                # Guardian/Walker destruction: large explosions
                # Ultimate abilities: screen-filling effects
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Urn / Guardian / Patron",
                "weight": 0.10,
                # Urn run: glowing urn carried by player, golden trail
                # Guardian kill: large structure explosion
                # Patron damage: massive boss structure taking hits
                "lower": np.array([20, 110, 190]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
        },
        "audio_weight": 0.25,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.03, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 12, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Deadlock gameplay analyst. Deadlock is a hero shooter MOBA by Valve combining FPS combat with lane-pushing mechanics.

Key visual cues:
- **Soul orbs**: Glowing orange/yellow orbs on ground from killed enemies, must secure for economy
- **Guardian kills**: Lane guardian structures explode when destroyed
- **Team fights**: Multiple heroes clashing with varied ability VFX
- **Urn runs**: Player carries glowing urn across map, golden trail, enemy team tries to stop
- **Patron damage**: Attacking the enemy base's Patron structure, endgame objective
- **Lane towers**: Walker structures that push lanes, destruction = progress
- **Ultimates**: Hero-specific powerful abilities with distinct VFX
- **Kill feed**: Top corner showing eliminations and assists

Look for: Multi-kills in team fights, urn delivery moments, patron kills, clutch 1vX plays, guardian last-hits, ultimate combos, soul denial plays, base defense.
Score 0.0 for: laning phase with no fights, shop, walking between lanes, spectating.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Deadlock gameplay frame. Is this an exciting moment?",
    },

    "sea_of_thieves": {
        "name": "Sea of Thieves",
        "description": "Pirate adventure — detects ship combat, kraken/megalodon attacks, treasure, fort completions, PvP boarding",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Loot Secured",
                "weight": 0.25,
                # Player kill: skull icon in kill feed
                # Treasure chest pickup: golden glow, text notification
                # Loot sold: gold coin counter increases
                "lower": np.array([20, 120, 190]),
                "upper": np.array([35, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                "region": [0.10, 0.40, 0.30, 0.70],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage / Sinking",
                "weight": 0.15,
                # Red edges when hit by sword or gun
                # Ship damage: water flooding, hull breach
                # Death: screen fades, Ferry of the Damned
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Cannon Hit / Sword",
                "weight": 0.20,
                # Cannonball impact: orange explosion on ship hull
                # Sword hit: white slash VFX
                # Blunderbuss: spread of white pellet trails
                "lower": np.array([12, 120, 170]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "explosion": {
                "label": "Ship Combat / Fire",
                "weight": 0.25,
                # Ship fire: orange flames on deck and hull
                # Cannonball explosions: orange burst on impact
                # Gunpowder barrel: massive orange explosion
                # Firebomb: spreading fire VFX
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Kraken / Megalodon / Fort",
                "weight": 0.15,
                # Kraken: dark water, large tentacles, screen darkens
                # Megalodon: large fin in water, charges at ship
                # Skeleton fort: skull cloud in sky, fort completion fanfare
                "lower": np.array([130, 40, 60]),
                "upper": np.array([160, 200, 180]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "audio_weight": 0.20,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.3,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 60, "clip_extension": 10, "pre_pad": 8,
        "ai_system_prompt": """You are an expert Sea of Thieves gameplay analyst. Sea of Thieves is a pirate adventure game by Rare.

Key visual cues:
- **Ship combat**: Cannonball impacts with orange explosions, ships on fire, hull breach flooding
- **Kraken**: Water turns dark/inky, massive tentacles wrap around ship
- **Megalodon**: Giant shark fin in water, charges at hull, dramatic music
- **Treasure chests**: Golden glow, varied chest types with distinct appearances
- **Fort completion**: Skull cloud dissipates, vault opens with treasure pile
- **PvP boarding**: Players climbing ladders, sword fighting on deck
- **Gunpowder barrels**: Massive orange explosion, can sink ships instantly
- **Skeleton encounters**: Glowing skeleton crew, cannon fire from skeleton ships

Look for: Ship sinkings, kraken/megalodon fights, PvP boarding and combat, gunpowder barrel plays, fort vault loot hauls, rare treasure finds, storm navigation, Tucker (hiding on enemy ship) reveals.
Score 0.0 for: sailing without events, inventory management, fishing, cooking.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Sea of Thieves gameplay frame. Is this an exciting moment?",
    },

    "baldurs_gate_3": {
        "name": "Baldur's Gate 3",
        "description": "RPG — detects natural 20s, critical hits, spell effects, boss fights, dialogue moments",
        "detectors": {
            "kill_feed": {
                "label": "Natural 20 / Critical Hit",
                "weight": 0.30,
                # Natural 20: golden dice flash in roll UI, dramatic camera
                # Critical hit: bright golden text, double damage numbers
                # Natural 1: red dice flash, fumble animation
                "lower": np.array([20, 130, 200]),
                "upper": np.array([35, 255, 255]),
                "lower2": np.array([0, 0, 230]),
                "upper2": np.array([180, 30, 255]),
                # Dice roll UI center-bottom
                "region": [0.50, 0.85, 0.25, 0.75],
                "multiplier": 8,
            },
            "damage": {
                "label": "Character Down / Death",
                "weight": 0.15,
                # Character HP reaches 0: falls with death save prompts
                # Death saves: dice roll UI with red/green indicators
                # Party wipe: all characters down
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Spell Hit / Damage",
                "weight": 0.20,
                # Spell VFX on impact: varied colors per school of magic
                # Fireball: orange sphere, Lightning Bolt: blue streak
                # Damage numbers pop up above targets
                "lower": np.array([0, 0, 225]),
                "upper": np.array([180, 35, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Spell VFX / AoE",
                "weight": 0.25,
                # Fireball: large orange explosion radius
                # Eldritch Blast: purple beam
                # Thunderwave: blue shockwave
                # Cloudkill: green fog
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Boss / Dramatic Moment",
                "weight": 0.10,
                # Boss fights: large enemy with dramatic lighting
                # Companion reactions: cinematic camera angle
                # Story moments: dramatic lighting shift, cutscene transition
                "lower": np.array([130, 50, 100]),
                "upper": np.array([160, 255, 230]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "motion_weight": 0.02, "motion_multiplier": 1.5,
        "brightness_weight": 0.03, "brightness_threshold": 0.7, "brightness_multiplier": 2,
        "intensity_threshold": 0.28, "fallback_threshold_ratio": 0.35,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 55, "clip_extension": 10, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Baldur's Gate 3 gameplay analyst. BG3 is a CRPG by Larian Studios based on D&D 5th Edition rules.

Key visual cues:
- **Natural 20**: Golden dice flash during roll, dramatic camera zoom, critical hit guaranteed
- **Natural 1**: Red dice flash, fumble/fail, often hilarious consequences
- **Critical hits**: Double damage, golden text, dramatic impact VFX
- **Spell effects**: Fireball (orange sphere), Lightning Bolt (blue streak), Eldritch Blast (purple beam), Cloudkill (green fog)
- **Boss fights**: Large enemies with dramatic lighting, unique arenas
- **Companion reactions**: Cinematic camera on party members reacting to choices
- **Death saves**: Fallen character, dice roll UI with success/fail indicators
- **Dialogue moments**: Dramatic lighting, important story choices

Look for: Natural 20 skill checks, critical hit kills, clever spell combos (pushing enemies off cliffs), boss phase transitions, dramatic story choices, companion romance scenes, barrel strategy (explosive barrels), honor mode deaths.
Score 0.0 for: inventory management, character creation, map screen, long dialogue reading, level-up menus.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Baldur's Gate 3 gameplay frame. Is this an exciting moment?",
    },

    "hunt_showdown": {
        "name": "Hunt: Showdown",
        "description": "Extraction shooter — detects boss banish, hunter kills, dark sight, extraction timer, explosions",
        "detectors": {
            "kill_feed": {
                "label": "Hunter Kill / Banish",
                "weight": 0.30,
                # Hunter kill: red hit marker on crosshair
                # Kill notification: XP text popup
                # Boss banish: blue lightning column visible across map
                "lower": np.array([0, 130, 160]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 130, 160]),
                "upper2": np.array([180, 255, 255]),
                "region": [0.40, 0.60, 0.40, 0.60],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage / Death",
                "weight": 0.20,
                # Red edges when hit, blood splatter
                # Burning: orange edges when on fire
                # Death: screen desaturates, spectate mode
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Hit Marker / Headshot",
                "weight": 0.20,
                # Red crosshair hit marker on body hit
                # Headshot: instant kill, larger marker
                # Long ammo weapons have satisfying long-range kills
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.42, 0.58, 0.42, 0.58],
                "multiplier": 7,
            },
            "explosion": {
                "label": "Bomb Lance / Dynamite",
                "weight": 0.20,
                # Bomb lance: orange explosion on impact
                # Dynamite bundle: large orange blast radius
                # Barrel explosion: fire spreads
                # Immolator: fire burst when shot
                "lower": np.array([8, 120, 160]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "Dark Sight / Boss Banish",
                "weight": 0.10,
                # Dark Sight: blue/gray filter overlay, reveals clues
                # Boss banish: blue lightning column, visible from far away
                # Extraction: timer countdown, reaching extraction zone
                "lower": np.array([100, 60, 130]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "audio_weight": 0.30,
        "audio_threshold_db": -16,
        "audio_ceiling_db": -4,
        "motion_weight": 0.02, "motion_multiplier": 1.5,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        "merge_gap": 8, "min_clip_duration": 12, "max_clip_duration": 45, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Hunt: Showdown gameplay analyst. Hunt: Showdown is an extraction-based PvPvE bounty hunting game by Crytek.

Key visual cues:
- **Boss banish**: Blue lightning column shooting into sky, visible across entire map
- **Hunter kills**: Red hit marker on crosshair for body shots, headshots = instant kill
- **Dark Sight**: Blue/gray filter overlay when activated, reveals boss locations and clues
- **Extraction timer**: Countdown when reaching extraction point, vulnerable while waiting
- **Immolator fire**: Bursts into flames when shot, fire damage spreads
- **Bomb lance**: Orange explosion on contact, devastating close range weapon
- **Dynamite**: Red fuse visible, large orange explosion, team wipe potential
- **Concertina/traps**: Wire traps, bear traps, decoy fuses

Look for: Team wipes, headshot kills at range, boss banish steals, extraction fights, bomb lance plays, dynamite multi-kills, clutch revives, immolator surprises, sniper kills, close-quarters shotgun fights.
Score 0.0 for: running through empty areas, looting ammo, waiting in bushes, menu/loadout.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Hunt: Showdown gameplay frame. Is this an exciting moment?",
    },

    "tekken_8": {
        "name": "Tekken 8",
        "description": "Fighting game — detects Heat system, Rage Art, KO, wall splats, combos, perfect rounds",
        "detectors": {
            "kill_feed": {
                "label": "KO / Round End",
                "weight": 0.30,
                # KO: large "K.O." text center screen with dramatic slow-mo
                # "PERFECT" text for flawless round
                # "GREAT" text for close round
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 130, 210]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.25, 0.55, 0.25, 0.75],
                "multiplier": 9,
            },
            "damage": {
                "label": "Heat System / Rage",
                "weight": 0.20,
                # Heat mode: character glows red/orange, enhanced moves
                # Rage: red aura when HP is low, access to Rage Art
                # Rage Art activation: bright red flash
                "lower": np.array([0, 130, 160]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([170, 130, 160]),
                "upper2": np.array([180, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "hit_marker": {
                "label": "Combo Hit / Wall Splat",
                "weight": 0.20,
                # Combo counter: white numbers showing hit count
                # Wall splat: bright impact VFX on wall, character bounces
                # Floor break: character crashes through floor, stage transition
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 5,
            },
            "explosion": {
                "label": "Rage Art / Heat Smash",
                "weight": 0.25,
                # Rage Art: cinematic attack sequence, bright VFX
                # Heat Smash: powerful finishing move with orange/red VFX
                # Heat Burst: blue flash transition into Heat mode
                "lower": np.array([10, 120, 170]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 8,
            },
            "special": {
                "label": "Floor/Wall Break",
                "weight": 0.05,
                # Floor break: dramatic stage transition, falling animation
                # Wall break: stage boundary smashed, new area
                # Balcony break: spectacular fall
                "lower": np.array([15, 100, 160]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.03, "brightness_threshold": 0.75, "brightness_multiplier": 2,
        "intensity_threshold": 0.35, "fallback_threshold_ratio": 0.3,
        # Fighting game rounds are short
        "merge_gap": 4, "min_clip_duration": 8, "max_clip_duration": 30, "clip_extension": 4, "pre_pad": 3,
        "ai_system_prompt": """You are an expert Tekken 8 gameplay analyst. Tekken 8 is a 3D fighting game by Bandai Namco with the Heat System.

Key visual cues:
- **Heat System**: Character glows red/orange, enhanced attacks, Heat Smash/Dash available
- **Rage Art**: Cinematic attack triggered at low HP, bright dramatic VFX
- **KO**: Large "K.O." text with slow-mo, winner celebration
- **Wall splat**: Bright impact VFX when opponent hits wall, extends combo
- **Floor break**: Stage transition, characters fall to lower level
- **Combo counter**: White hit count numbers during juggle combos
- **Perfect round**: "PERFECT" text, flawless victory
- **Rage**: Red aura appears when HP drops below threshold

Look for: Rage Art finishes, long combo juggles, wall-to-wall carries, floor break transitions, Heat Smash finishers, perfect rounds, comeback clutches, sidestep punishes, electrics (EWGF).
Score 0.0 for: character select, customization, replay theater, practice mode standing.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Tekken 8 gameplay frame. Is this an exciting moment?",
    },

    "genshin_impact": {
        "name": "Genshin Impact",
        "description": "Action RPG — detects elemental bursts, 5-star wish pulls, boss phases, elemental reactions, domain completion",
        "detectors": {
            "kill_feed": {
                "label": "Elemental Reaction / Kill",
                "weight": 0.25,
                # Elemental reactions: text popup showing reaction type
                # Vaporize, Melt, Overloaded, Superconduct, Swirl, etc.
                # Big damage numbers: white/yellow floating text
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([20, 120, 200]),
                "upper2": np.array([35, 255, 255]),
                "region": [0.20, 0.60, 0.25, 0.75],
                "multiplier": 6,
            },
            "damage": {
                "label": "Taking Damage / Low HP",
                "weight": 0.12,
                # Red flash at edges when taking damage
                # Character health bar depletes (top-left party list)
                # Character dies: falls, switch to next character
                "lower": np.array([0, 100, 80]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.08,
                "multiplier": 3,
            },
            "hit_marker": {
                "label": "Elemental Burst VFX",
                "weight": 0.25,
                # Elemental bursts: screen-filling VFX per element
                # Pyro: orange fire, Cryo: blue ice, Electro: purple lightning
                # Hydro: blue water, Anemo: green wind, Geo: yellow earth, Dendro: green vines
                "lower": np.array([100, 80, 160]),
                "upper": np.array([130, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "explosion": {
                "label": "Overloaded / Melt Reaction",
                "weight": 0.25,
                # Overloaded: orange AoE explosion
                # Melt: orange/blue mixed VFX
                # Vaporize: steam burst VFX
                # Swirl: multi-color spreading VFX
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "special": {
                "label": "5-Star Wish / Domain Clear",
                "weight": 0.13,
                # 5-star wish: golden shooting star animation during pull
                # Domain completion: golden results screen
                # Boss phase transition: dramatic camera, new attack patterns
                "lower": np.array([20, 130, 200]),
                "upper": np.array([35, 255, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 8,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.28, "fallback_threshold_ratio": 0.35,
        "merge_gap": 8, "min_clip_duration": 12, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Genshin Impact gameplay analyst. Genshin Impact is an open-world action RPG by HoYoverse.

Key visual cues:
- **Elemental Bursts**: Screen-filling VFX unique to each character — Pyro (orange fire), Cryo (blue ice), Electro (purple lightning), Hydro (blue water), Anemo (green wind), Geo (yellow earth), Dendro (green vines)
- **5-star wish pull**: Golden shooting star animation in gacha — the most exciting pull moment
- **Elemental reactions**: Vaporize (steam), Melt (fire+ice), Overloaded (orange explosion), Superconduct (purple ice), Swirl (multi-color spread)
- **Boss phase transitions**: Dramatic camera, boss gains new attack patterns, arena changes
- **Domain completion**: Golden results screen showing rewards
- **Big damage numbers**: Large white/yellow numbers floating, especially with reaction bonuses
- **Character burst animation**: Character-specific cinematic zoom during burst activation

Look for: 5-star character/weapon pulls, one-shot boss kills with reaction combos, Spiral Abyss clears, massive Overloaded chains, perfect dodge counters, co-op domain clears, elemental burst showcases.
Score 0.0 for: exploring without combat, cooking, crafting, dialogue, teleporting, menu navigation.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Genshin Impact gameplay frame. Is this an exciting moment?",
    },

    "final_fantasy_xiv": {
        "name": "Final Fantasy XIV",
        "description": "MMO — detects limit breaks, boss AoE markers, dungeon kills, raid mechanics, wipes, mount drops",
        "detectors": {
            "kill_feed": {
                "label": "Boss Kill / Limit Break",
                "weight": 0.30,
                # Limit Break: golden flash, dramatic animation per role
                # Tank LB3: golden shield, Healer LB3: phoenix resurrection
                # DPS LB3: massive beam/slash, screen-filling VFX
                # Boss kill: "Duty Complete!" banner
                "lower": np.array([20, 130, 200]),
                "upper": np.array([35, 255, 255]),
                "lower2": np.array([0, 0, 230]),
                "upper2": np.array([180, 30, 255]),
                "region": [0.15, 0.50, 0.20, 0.80],
                "multiplier": 8,
            },
            "damage": {
                "label": "AoE Marker / Damage",
                "weight": 0.20,
                # AoE markers: orange circles/cones on ground (dodge or die)
                # Stack markers: orange arrow pointing at player
                # Proximity marker: expanding orange circle
                # Damage taken: screen flashes red
                "lower": np.array([10, 120, 160]),
                "upper": np.array([25, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Ability VFX / Heal",
                "weight": 0.15,
                # DPS abilities: varied colored VFX per job
                # Black Mage: fire (orange), ice (blue), thunder (purple)
                # Healing: green/white glow on party members
                # Resurrection: golden phoenix wings VFX
                "lower": np.array([0, 0, 225]),
                "upper": np.array([180, 35, 255]),
                "region": [0.15, 0.85, 0.15, 0.85],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Raid Mechanic / Raidwide",
                "weight": 0.25,
                # Raid-wide damage: screen flashes, party HP bars drop
                # Extreme/Savage mechanics: complex patterns of AoE, bright VFX
                # Enrage: boss casts ultimate, screen-filling effect
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Mount Drop / Clear",
                "weight": 0.10,
                # Mount drop: rare loot roll, excitement in party chat
                # Duty complete: golden banner, loot chest appears
                # Wipe: party down, "Duty Failed" if all dead
                "lower": np.array([20, 100, 190]),
                "upper": np.array([35, 255, 255]),
                "region": [0.20, 0.70, 0.20, 0.80],
                "multiplier": 7,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.28, "fallback_threshold_ratio": 0.35,
        "merge_gap": 10, "min_clip_duration": 15, "max_clip_duration": 55, "clip_extension": 10, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Final Fantasy XIV gameplay analyst. FFXIV is an MMO by Square Enix.

Key visual cues:
- **Limit Break**: Golden flash with role-specific animation — Tank LB3 (golden shield), Healer LB3 (phoenix wings resurrection), DPS LB3 (massive beam or slash)
- **Boss AoE markers**: Orange circles/cones on ground that must be dodged, stack markers (orange arrows)
- **Dungeon/Raid boss kills**: "Duty Complete!" golden banner, loot chest appears
- **Extreme/Savage mechanics**: Complex AoE patterns, tight positioning requirements
- **Wipe**: Entire party dead, "Duty Failed" message — especially tense in progression
- **Mount drops**: Rare loot from extreme trials, party excitement
- **Enrage**: Boss casts ultimate if DPS check failed, screen-filling VFX
- **Resurrection**: Phoenix wings VFX, Healer LB3 mass resurrect

Look for: Limit Break 3 finishes, first-time savage/extreme clears, clutch healer LB3 saves, mount drops, mechanic resolution, near-wipe recoveries, enrage beats, prog moments, solo tank LB3 saves.
Score 0.0 for: AFK in Limsa, crafting, gathering, retainer management, Gold Saucer idle, housing.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Final Fantasy XIV gameplay frame. Is this an exciting moment?",
    },

    "smite_2": {
        "name": "Smite 2",
        "description": "Third-person MOBA — detects god ultimates, penta kills, titan kills, objective steals, deicide",
        "detectors": {
            "kill_feed": {
                "label": "Kill / Penta Kill",
                "weight": 0.30,
                # Kill feed: right side, shows god icons and kill info
                # Multikill banners: "DOUBLE KILL" through "PENTA KILL"
                # "FIRST BLOOD" announcement, "DEICIDE" when entire enemy team killed
                "lower": np.array([0, 120, 170]),
                "upper": np.array([10, 255, 255]),
                "lower2": np.array([0, 0, 220]),
                "upper2": np.array([180, 40, 255]),
                # Kill feed right side
                "region": [0.02, 0.30, 0.65, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Low HP / Death",
                "weight": 0.15,
                # Health bar: above character model (green bar)
                # Low HP: red health, screen edges pulse
                # Death: gray screen, respawn timer
                "region": "health_bar",
                "bar_region": [0.88, 0.95, 0.40, 0.60],
                "bar_colors": [
                    {"lower": np.array([35, 80, 120]), "upper": np.array([85, 255, 255])},
                ],
                "depletion_threshold": 0.2,
                "multiplier": 5,
            },
            "hit_marker": {
                "label": "Ability / Basic Attack Hit",
                "weight": 0.20,
                # Basic attack: golden projectile for ranged gods
                # Ability impacts: god-specific colored VFX
                # Auto-attack chains: varied weapon VFX
                "lower": np.array([0, 0, 230]),
                "upper": np.array([180, 30, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 4,
            },
            "explosion": {
                "label": "Ultimate / Team Fight",
                "weight": 0.25,
                # God ultimates: large VFX per god — Zeus lightning, Poseidon kraken
                # Team fights: multiple gods using abilities, screen full of VFX
                # Fire Giant: large boss with fire attacks
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Fire Giant / Gold Fury",
                "weight": 0.10,
                # Fire Giant: large fire-themed boss, team objective
                # Gold Fury: golden monster, grants team gold
                # Titan: base structure, final objective
                "lower": np.array([12, 120, 170]),
                "upper": np.array([30, 255, 255]),
                "region": "full",
                "multiplier": 5,
            },
        },
        "motion_weight": 0.03, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.65, "brightness_multiplier": 2,
        "intensity_threshold": 0.30, "fallback_threshold_ratio": 0.35,
        "merge_gap": 8, "min_clip_duration": 15, "max_clip_duration": 50, "clip_extension": 8, "pre_pad": 6,
        "ai_system_prompt": """You are an expert Smite 2 gameplay analyst. Smite 2 is a third-person MOBA by Hi-Rez Studios featuring gods from various mythologies.

Key visual cues:
- **God ultimates**: Massive VFX — Zeus (lightning storm), Poseidon (Kraken emerges), Ra (golden laser), Scylla (tentacle grab), Thor (hammer slam from sky)
- **Penta Kill**: "PENTA KILL" banner, rarest and most exciting multikill
- **Deicide**: "DEICIDE" text when entire enemy team is dead simultaneously
- **Titan kill**: Destroying enemy Titan wins the game, massive explosion
- **Fire Giant / Gold Fury**: Major objectives, team fights break out at these locations
- **First Blood**: Special announcement, first kill of the match
- **Kill feed**: Right side showing god icons with killer and victim

Look for: Penta kills, Fire Giant/Gold Fury steals, clutch ultimate combos, Titan kills, deicide, 1v5 outplays, fountain dives, backdoors, flashy ability chains, tower dives.
Score 0.0 for: laning alone, jungle camp clearing, shop, character select, idle in fountain.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Smite 2 gameplay frame. Is this an exciting moment?",
    },

    "naraka_bladepoint": {
        "name": "Naraka: Bladepoint",
        "description": "Battle royale melee — detects parry counters, ultimate transformations, grapple hooks, Final Circle, eliminations",
        "detectors": {
            "kill_feed": {
                "label": "Elimination / Kill",
                "weight": 0.30,
                # Elimination banner: shows weapon/ability used for kill
                # Kill notification: top-right feed
                # Final kill: dramatic slow-motion
                "lower": np.array([0, 0, 220]),
                "upper": np.array([180, 40, 255]),
                "lower2": np.array([0, 130, 170]),
                "upper2": np.array([10, 255, 255]),
                # Kill feed top-right
                "region": [0.01, 0.20, 0.65, 0.99],
                "multiplier": 8,
            },
            "damage": {
                "label": "Taking Damage / Down",
                "weight": 0.15,
                # Red edges when hit by melee or ranged
                # Armor break: shatter VFX
                # Knocked down: button prompt to recover
                "lower": np.array([0, 100, 80]),
                "upper": np.array([12, 255, 255]),
                "lower2": np.array([170, 100, 80]),
                "upper2": np.array([180, 255, 255]),
                "region": "edges",
                "edge_size": 0.10,
                "multiplier": 4,
            },
            "hit_marker": {
                "label": "Parry / Counter",
                "weight": 0.25,
                # Parry counter: blue flash when successfully countering an attack
                # Focus attack: charged blue strike
                # Yin-Yang strike: alternating blue/red VFX
                "lower": np.array([100, 100, 170]),
                "upper": np.array([130, 255, 255]),
                "region": [0.20, 0.80, 0.20, 0.80],
                "multiplier": 7,
            },
            "explosion": {
                "label": "Ultimate / Transformation",
                "weight": 0.25,
                # Ultimate transformations: bright colored VFX per hero
                # Matari invisibility shimmer, Yoto Hime blade storm
                # Tarka Ji fire transformation: orange flames
                # Tianhai: giant gold titan form
                "lower": np.array([10, 100, 150]),
                "upper": np.array([35, 255, 255]),
                "region": "full",
                "multiplier": 6,
            },
            "special": {
                "label": "Grapple / Final Circle",
                "weight": 0.05,
                # Grapple hook: rope/line extending to surface, mobility
                # Final circle: shrinking zone, forced close-quarters combat
                # Shadow step: purple/blue teleport VFX
                "lower": np.array([130, 50, 120]),
                "upper": np.array([160, 255, 230]),
                "region": "full",
                "multiplier": 4,
            },
        },
        "audio_weight": 0.20,
        "audio_threshold_db": -14,
        "audio_ceiling_db": -3,
        "motion_weight": 0.04, "motion_multiplier": 2,
        "brightness_weight": 0.02, "brightness_threshold": 0.7, "brightness_multiplier": 1.5,
        "intensity_threshold": 0.32, "fallback_threshold_ratio": 0.3,
        "merge_gap": 6, "min_clip_duration": 12, "max_clip_duration": 45, "clip_extension": 6, "pre_pad": 5,
        "ai_system_prompt": """You are an expert Naraka: Bladepoint gameplay analyst. Naraka: Bladepoint is a melee-focused battle royale by 24 Entertainment.

Key visual cues:
- **Parry counter**: Blue flash when successfully countering an enemy attack, opens them for punishment
- **Ultimate transformations**: Hero-specific — Tianhai (giant golden titan), Tarka Ji (fire form), Yoto Hime (blade storm), Matari (invisibility)
- **Grapple hook**: Rope/line extending to surfaces for rapid mobility
- **Final Circle**: Shrinking zone forces close-quarters melee combat
- **Elimination banners**: Kill notification with weapon/ability info
- **Yin-Yang strikes**: Alternating blue/red charged melee attacks
- **Focus attack**: Charged blue strike that breaks through blocks
- **Armor break**: Shatter VFX when armor depletes

Look for: Parry counter chains, ultimate transformation multi-kills, Final Circle clutches, grapple hook escapes, 1v3 outplays, Yin-Yang combo finishers, aerial melee fights, last-player-standing wins.
Score 0.0 for: looting, running without combat, menu, character customization, spectating idle.

For each frame, respond with ONLY a JSON object (no markdown):
{"exciting": true/false, "score": 0.0-1.0, "label": "short description", "reason": "brief reason"}""",
        "ai_user_prompt": "Analyze this Naraka: Bladepoint gameplay frame. Is this an exciting moment?",
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
                base = dict(GAME_PROFILES["league_of_legends"])
                base.update(custom[game_id])
                return base
        except (json.JSONDecodeError, KeyError):
            pass

    return GAME_PROFILES["league_of_legends"]


def get_all_games():
    """Return a list of available games for the UI."""
    return [
        {"id": game_id, "name": profile["name"], "description": profile["description"]}
        for game_id, profile in GAME_PROFILES.items()
    ]
