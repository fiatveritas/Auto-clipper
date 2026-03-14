# ARC Raiders Twitch Stream — Clip-Worthy Moment Detection Guide

## Purpose

This document is a comprehensive prompt/reference for an AI computer vision system that analyzes frames from an ARC Raiders Twitch stream to identify clip-worthy moments. It is derived from analysis of **1,019+ annotated frames** spanning scene numbers 2–3341 (extracted from a full VOD), plus **~120 labeled frames** from an "ARC Raiders WTF Funny Moments Ep. 2" compilation video. The dataset was exported via Roboflow (indicated by the `_rf_` hash suffix on all filenames), meaning these frames were selected and labeled as containing notable events.

-----

## 1. About the Game: ARC Raiders

ARC Raiders is a **third-person cooperative PvPvE extraction shooter** set in a sci-fi post-apocalyptic world. Key visual elements:

- **Perspective**: Third-person over-the-shoulder camera. The player character is typically visible in the lower-center or lower-right of the frame.
- **Setting**: Ruined industrial/urban environments, open wastelands, underground bunkers, alien-tech structures. Expect debris, destroyed vehicles, overgrown ruins, metallic structures.
- **Enemies**: Both AI-controlled robotic/mechanical enemies (ARC machines — drones, walkers, large boss-tier mechs) and other human players (PvP).
- **Player Characters**: Human characters in tactical/survival gear with sci-fi elements. Various skins and loadouts.
- **Weapons**: Mix of conventional firearms (rifles, shotguns, SMGs) and sci-fi energy weapons. Visible muzzle flash, tracer rounds, energy projectile effects.
- **HUD Elements**: Health bar, ammo counter, minimap, squad info, interaction prompts, kill feed, loot notifications, extraction timer.

-----

## 2. What Makes a Clip-Worthy Moment

Based on the dataset (frames deliberately selected from a "WTF Funny Moments" compilation and key stream scenes), here are the categories of clip-worthy moments to detect:

### 2.1 Combat Highlights

| Signal | What to Look For |
|---|---|
| **Kill moments** | Kill feed popups, XP/reward notifications, enemy death animations (ragdoll, explosion, disintegration), damage numbers |
| **Multi-kills** | Multiple kill notifications in rapid succession, multiple enemies dying in frame |
| **Clutch fights** | Player health bar very low (red/critical) during active combat, close-quarters engagement |
| **Boss encounters** | Unusually large enemy filling significant portion of frame, unique boss health bars, dramatic lighting/effects |
| **Sniper shots / long range** | Scope overlay, distant enemy being hit, long sight lines |
| **Explosions** | Large particle effects, screen shake indicators (motion blur), fire/smoke filling portions of the frame |
| **Vehicle destruction** | Burning/exploding vehicles, mechanical wreckage |

### 2.2 Funny / WTF Moments

| Signal | What to Look For |
|---|---|
| **Ragdoll physics** | Bodies in unnatural positions, enemies/players launched into the air, objects clipping through geometry |
| **Glitches** | Characters in T-pose, objects floating, texture glitches, characters stuck in geometry |
| **Unexpected deaths** | Player death screen appearing suddenly, death from off-screen, fall damage splats |
| **Absurd situations** | Multiple players stacked/clustered unnaturally, emotes during combat, unusual player positioning |
| **Friendly fire / team chaos** | Teammates in crossfire, team damage indicators |

### 2.3 Epic / Dramatic Moments

| Signal | What to Look For |
|---|---|
| **Extraction sequences** | Extraction zone markers, countdown timers, helicopter/ship arrival VFX, intense lighting changes |
| **Loot discovery** | Rare item pickup notifications (gold/purple/legendary color coding), loot chest opening animations |
| **Close calls** | Bullets/projectiles visible near player, near-miss particle effects, dodging/rolling with enemies in frame |
| **Dramatic scenery** | Unusual camera angles, cinematic environmental moments, massive structures revealed |
| **Squad wipes** | Multiple team death notifications, "squad eliminated" messages |

### 2.4 High-Action Density Frames

| Signal | What to Look For |
|---|---|
| **Screen clutter** | Many particle effects simultaneously (explosions + gunfire + abilities), indicates chaotic peak-action |
| **Multiple actors** | 3+ characters (friend or foe) visible and active in frame simultaneously |
| **HUD urgency** | Low health + low ammo + enemies on minimap = high tension |
| **Movement indicators** | Motion blur, sprint effects, slide/dodge animations = fast-paced action |

-----

## 3. Frame-Level Visual Feature Checklist

When analyzing each frame, evaluate these features:

### 3.1 HUD & UI Indicators (Most Reliable)

```
[ ] Kill feed active (top-right, showing recent kills/deaths)
[ ] Player health bar status (full / damaged / critical-red / downed)
[ ] Ammo count (low ammo = tension, zero = critical)
[ ] Notification popups (XP gained, item picked up, objective complete)
[ ] Death screen / respawn screen / spectator mode
[ ] Extraction timer visible and counting down
[ ] Damage direction indicators (red vignette on screen edges)
[ ] Hit markers / crosshair feedback (confirmed hits on enemies)
[ ] Teammate status icons (downed teammates = urgency)
[ ] Minimap activity (red dots = nearby enemies)
[ ] Interaction prompt ("Press E to...", "Hold X to...")
[ ] Score/reward summary screens
```

### 3.2 Visual Effects (Action Indicators)

```
[ ] Muzzle flash (player or enemies firing weapons)
[ ] Tracer rounds / bullet trails visible
[ ] Explosion effects (fire, smoke, debris particles)
[ ] Energy weapon effects (beams, plasma, glowing projectiles)
[ ] Shield/barrier effects
[ ] Healing/ability effects (colored auras, particle rings)
[ ] Environmental destruction (breaking walls, falling structures)
[ ] Dust/debris clouds from impacts
[ ] Screen-wide flash (grenade, large explosion)
[ ] Blood/damage splatter effects
[ ] Electrical/EMP effects on robots
```

### 3.3 Character & Animation States

```
[ ] Player in combat stance (ADS / aiming down sights)
[ ] Player dodging/sliding/rolling
[ ] Player sprinting
[ ] Player downed/crawling
[ ] Enemy death animation in progress
[ ] Enemy attack animation (winding up, charging)
[ ] Ragdoll physics active (body in unnatural trajectory)
[ ] Emote/gesture animations
[ ] Melee attack animation
[ ] Revive animation (player helping teammate)
```

### 3.4 Environmental Context

```
[ ] Indoor vs outdoor (indoor = closer quarters = more intense CQB)
[ ] Vertical combat (elevated positions, falling, jumping)
[ ] Vehicle present (drivable or destroyed)
[ ] ARC machine structure/nest visible (major encounter zone)
[ ] Weather/atmosphere effects (storm, fog, darkness)
[ ] Extraction point visual markers
[ ] Loot containers/crates visible
```

-----

## 4. Temporal Pattern Detection

Individual frames need temporal context. When analyzing sequences of frames:

### 4.1 Scene Transition Detection

The dataset spans scenes 2–3341 with non-uniform sampling, meaning the annotator focused on specific segments. Dense clusters of consecutive scene numbers = sustained action sequences. Gaps = downtime that was skipped.

**High-density frame clusters from the dataset** (likely the most clip-worthy segments):

- **Scenes 500–999**: 216 frames sampled — very high action density
- **Scenes 1500–1999**: 220 frames — sustained engagement period
- **Scenes 2000–2499**: 225 frames — peak action segment
- **Scenes 0–499**: 129 frames — opening/early action
- **Scenes 1000–1499**: 138 frames — mid-session
- **Scenes 2500–2999**: Only 12 frames — likely downtime/transition
- **Scenes 3000–3341**: 79 frames — late-stream segment

### 4.2 Clip Boundary Signals

**Start of a clip:**

- Sudden appearance of enemies/combat after calm frames
- HUD transitioning from idle to combat state
- Player switching from looting/movement to ADS (aiming)
- Audio spike indicators (if available): gunfire, explosions, voice reactions

**End of a clip:**

- Kill feed clearing / combat settling
- Player health stabilizing or death screen
- Transition to looting / inventory screen
- Score/reward summary appearing
- Player returning to idle movement state

### 4.3 Multi-Frame Action Scoring

Rate sequences, not just individual frames:

| Sequence Pattern | Clip Score |
|---|---|
| 3+ consecutive frames with combat VFX | HIGH — sustained firefight |
| Health drops from full to critical across frames | HIGH — intense encounter |
| Multiple kill feed entries appearing across frames | HIGH — multi-kill streak |
| Explosion frame followed by ragdoll frames | HIGH — dramatic kill |
| Death screen after low-health combat frames | MEDIUM — death clip (funny if sudden) |
| Loot notification after combat sequence | MEDIUM — rewarding moment |
| Calm -> sudden combat in 1-2 frames | HIGH — ambush/jump scare moment |
| Single enemy, quick kill, back to calm | LOW — routine engagement |

-----

## 5. COMPLETE ARC Machine Visual Recognition Guide

ARC (Automated Robotic Combatants) are the primary AI enemies. They are robots/machines with a retro-futuristic aesthetic inspired by sci-fi like Terminator and Horizon Zero Dawn. Every ARC has a **scanner beam** that indicates its aggro state — this is one of the most reliable visual cues for detection:

- **White/Blue beam** = Patrolling, neutral — not clip-worthy
- **Yellow beam** = Alerted, investigating — tension building
- **Red beam** = Combat mode, attacking — action is happening, potential clip

ARC machines do NOT have traditional health bars. The game uses **physics-based visual feedback** instead: you see parts break off, thrusters fail, legs buckle, armor plating shatter. This destruction IS the feedback — look for it as a signal that combat is happening.

ARC have two armor types visible at a glance:

- **Unarmored plating**: Matte, white coloring — any weapon works
- **Armored plating**: Shinier, darker metallic — requires heavy ammo to penetrate

### 5.1 Small / Low-Threat Ground ARC

#### ROLLBOT
- **Shape**: Spherical ball, roughly basketball-sized on screen
- **Visual ID**: Fast-rolling metallic sphere, shoots lasers while rolling
- **Motion**: Rolls rapidly across terrain, bounces off surfaces
- **Color**: Metallic silver/grey with glowing elements
- **Clip signal**: Funny when they surprise players, or when multiple roll at once. Rolling physics = ragdoll comedy potential
- **In frame**: Small, fast-moving spherical object at ground level

#### POP
- **Shape**: Tiny rolling robots, smaller than Rollbots
- **Visual ID**: Small spherical bots that roll toward players aggressively
- **Attack**: Tase/shock on contact — electric spark effects visible
- **Clip signal**: Swarms of Pops charging a player = chaotic and funny. Death-by-Pop is embarrassing/funny clip material
- **In frame**: Multiple small rolling objects converging on player position

#### FIREBALL
- **Shape**: Slightly larger than Pop, also spherical/rolling
- **Visual ID**: Rolls toward Raiders, then opens up and sprays fire
- **Attack**: Flame spray — bright orange/yellow fire particle effects when open
- **Clip signal**: The "opening up" animation is distinctive. Fire effects filling the screen = dramatic. Deaths to Fireballs are funny
- **In frame**: Rolling sphere that unfolds, followed by fire/flame VFX

#### TICK
- **Shape**: Small spider-like robot, very compact
- **Visual ID**: Dark-colored, multi-legged, hides on walls/ceilings/corners inside buildings
- **Motion**: Skittering movement, then sudden LEAP at player's head — latches on
- **Attack**: Jumps onto player's face/head, deals damage over time, then detonates
- **Clip signal**: VERY high clip potential. The facehugger-style latch is visually dramatic and startling. Players frantically meleeing their own face = funny. Can be one-hit killed by melee
- **In frame**: Small dark spider shape on walls/ceilings, or attached to player character's head area. Look for player character swatting at their own head

### 5.2 Aerial ARC (Flying Units)

#### WASP
- **Shape**: Small drone with rotors, similar to a quadcopter
- **Visual ID**: Flying drone with visible rotors/thrusters, equipped with machine gun
- **Motion**: Hovers and strafes in air, buzzes around erratically
- **Scanner**: 45-degree narrow cone vision
- **Destruction feedback**: Shooting off rotors causes it to spin out, lose stability, crash. Losing 2 rotors = crashes immediately. This physics destruction is distinctive
- **Clip signal**: Swarms of Wasps = chaotic combat. Shooting rotors off and watching them spiral/crash = satisfying clip
- **In frame**: Small flying objects in upper portion of frame with visible rotor silhouette, tracer fire coming from them

#### HORNET
- **Shape**: Larger drone than Wasp, similar quadcopter profile but bulkier
- **Visual ID**: 2 armored rotors on front (metallic/shiny), 2 unarmored on back. Visibly beefier than Wasp
- **Attack**: Fires stun/taser rounds — electrical VFX on hit
- **Clip signal**: Stun effect on player (screen distortion/electrical effect) followed by other enemies finishing them off = dramatic
- **In frame**: Larger flying drone, distinguishable from Wasp by size and armored front plating

#### SNITCH (HIGH PRIORITY FOR CLIPS)
- **Shape**: Unarmed floating reconnaissance drone, floats high above
- **Visual ID**: Hovers at high altitude, constantly scanning. No weapons visible
- **Behavior**: Detects gunfire from extreme range, then calls reinforcements (2 Wasps + 1 Hornet typically)
- **Clip signal**: The moment a Snitch calls reinforcements and enemies flood in = tension spike. Failing to kill a Snitch before it alerts = "oh no" moment
- **In frame**: Small drone hovering high in frame, possibly with visible scanning effect. Followed by multiple new enemy spawns

#### ROCKETEER
- **Shape**: LARGE flying robot — significantly bigger than Wasp/Hornet
- **Visual ID**: Big aerial unit, armed with rocket launchers. Heavily armored
- **Attack**: Fires rockets that create large explosions with area-of-effect damage
- **Clip signal**: VERY high clip potential. Rocket explosions are visually massive. Forces players to constantly move — frantic dodging = exciting footage. Rocket impacts near players = close calls
- **In frame**: Large flying silhouette with visible rocket trail VFX, followed by large explosion effects on ground. Smoke trails in air

#### SHREDDER
- **Shape**: Small, dark, cylindrical floating unit — looks like a hovering "eye"
- **Visual ID**: Dark cylindrical body, hovers, rushes toward players at high speed
- **Attack**: 360-degree AOE shotgun blast at close range — devastating
- **Clip signal**: The rush-in attack is sudden and dramatic. Getting hit by the shotgun AOE = instant drama. Very hard to deal with = lots of death clips
- **In frame**: Dark cylindrical hovering shape rushing toward camera/player, followed by wide spread of projectile effects

#### FIREFLY (Newer Enemy — Patch 1.17.0)
- **Shape**: Flying ARC with flame capability
- **Visual ID**: More aggressive than Wasp/Hornet — actively hunts players into corners. Uses flame attacks from above
- **Attack**: Dive attacks with fire, flushes players from cover
- **Weakness visual**: Yellow gas tank on underside
- **Clip signal**: High — flame attacks from above are visually dramatic. Being flushed from cover into other danger = chaotic

### 5.3 Heavy / Armored ARC (Large, Dangerous)

#### BASTION
- **Shape**: MASSIVE crab-like quadruped machine. One of the largest common enemies
- **Visual ID**: Four thick legs, heavy body, turret/gun mounted on top. Slow-moving but enormous. Distinctive crab/spider silhouette
- **Armor**: Heavy plating everywhere. Yellow spots on leg joints and yellow canister on backside = weak points
- **Attack**: Heavy gunfire from turret, ground slam melee, shield-shredding attacks
- **Destruction feedback**: Legs buckle when damaged at joints, kneels down when staggered. Armor plates visibly break off
- **Clip signal**: EXTREMELY high clip potential. Every Bastion fight is dramatic due to size and danger. Leg-breaking staggers are satisfying visual moments. Squad coordinating to take one down = epic. Deaths to Bastion = dramatic
- **In frame**: Fills large portion of frame. Four-legged silhouette with heavy body is unmistakable. Yellow weak points may be visible on joints

#### LEAPER (also called BISON)
- **Shape**: Four-legged robot, slightly smaller than Bastion but much more mobile
- **Visual ID**: Spider-like quadruped that can JUMP long distances. More agile/lean than Bastion
- **Attack**: Launches itself at players from far away (the jump is very visible — a large robot going airborne), shockwave stomp on landing
- **Weakness visual**: Glowing "eye"/face area, exposed leg joints
- **Clip signal**: VERY high. The jump attack is one of the most dramatic animations in the game — a massive robot launching through the air. Landing shockwave = screen effects. Being landed on = instant death clip
- **In frame**: Large quadruped in mid-air/jumping trajectory, or landing with visible shockwave ring effect on ground

#### BOMBARDIER
- **Shape**: Resembles Bastion (large quadruped) but with mortar equipment
- **Visual ID**: Heavy artillery unit with visible mortar launcher on top. Accompanied by smaller Spotter drones orbiting nearby
- **Attack**: Long-range mortar fire — arcing projectiles visible in sky, large explosion on impact. Spotter drones improve accuracy
- **Clip signal**: Extreme. Mortar explosions are massive. The arcing projectile trail is visible. Being caught in mortar fire = dramatic death. Taking out Spotters first = tactical moment
- **In frame**: Large quadruped with upward-firing weapon, visible arcing projectile trails in sky, companion small drones nearby

#### COMET (Newer Enemy — Patch 1.17.0)
- **Shape**: Heavily armored rolling sphere, larger than Rollbot
- **Visual ID**: Armored sphere of explosives. Armor visibly opens when taking sustained fire, revealing inner machinery
- **Attack**: Explosive detonation with broad blast radius. Positions itself to catch multiple squad members
- **Clip signal**: High — the armor-opening mechanic is visually distinctive. Explosions are large. Squad wipes from blast radius = dramatic
- **In frame**: Large armored sphere, potentially with armor plates splitting open to reveal glowing internals

### 5.4 Support / Stationary ARC

#### TURRET
- **Shape**: Fixed gun emplacement, not mobile
- **Visual ID**: Stationary gun platform found in rooms/buildings. Has a scanning blue light that turns RED when locked on
- **Clip signal**: The blue-to-red scanner transition followed by instant bullet stream = jump scare moments. Walking into a turret room unprepared = funny death
- **In frame**: Stationary mechanical object with visible scanning light beam (blue or red)

#### SENTINEL
- **Shape**: Stationary long-range sniper unit
- **Visual ID**: Fixed position, has a visible targeting LASER beam pointed at player before firing a single heavy shot
- **Clip signal**: The visible laser targeting followed by the heavy shot = dramatic sniper moment. Being one-shot by a Sentinel = rage/funny clip
- **In frame**: Stationary unit with visible red/orange laser beam tracing toward player. Single large projectile/tracer

#### ARC PROBE (Lootable, Not Hostile)
- **Shape**: Large pod that lands from sky
- **Visual ID**: Drops from sky with loud visual/audio cue (bright entry trail). Can be breached and looted. Emits loud siren (visible alarm VFX) when breaching starts
- **Clip signal**: High risk/reward moment — breaching while enemies converge = tension. The siren attracting enemies creates chaotic combat clips
- **In frame**: Large pod/container object with player interacting (breach animation), potentially with alarm/siren VFX active

### 5.5 BOSS ARC (Rare, ALWAYS Clip-Worthy)

#### THE QUEEN
- **Shape**: COLOSSAL war machine — the largest ARC in the game. Towers over everything
- **Visual ID**: Enormous multi-legged machine that dominates the entire frame. Only appears during Harvester events. Multiple weapon systems visible
- **Attack**: Devastating laser beam (bright concentrated beam VFX), ground slams (screen shake + dust clouds), EMP waves (electrical distortion across screen), spawns smaller ARCs continuously
- **Weakness visual**: Yellow leg joints (after breaking armor), top of head glows during laser charge-up
- **Clip signal**: ALWAYS CLIP. Every Queen encounter is dramatic. The laser beam is one of the most visually spectacular effects. Squad coordination or squad wipes are both great content. Massive XP (5000)
- **In frame**: Absolutely massive mechanical entity filling most of the frame. Impossible to miss. Bright laser beam effects, ground impact effects, smaller ARC spawning around it

#### THE MATRIARCH
- **Shape**: Even more imposing than the Queen
- **Visual ID**: Enormous ARC with energy shield visible around it. Appears during specific map conditions on Spaceport map. "Children" (smaller ARCs) visibly protect and surround it
- **Attack**: Homing missiles (visible rocket trails tracking player), flashbangs (screen white-out), gas mines (colored gas clouds on ground), summons advanced ARC reinforcements
- **Clip signal**: ALWAYS CLIP. Rarest and most dangerous encounter. The energy shield visual is distinctive. Gas mines + missiles + children = visual chaos. Squad wipes are very common
- **In frame**: Massive ARC with visible energy shield bubble/barrier effect, surrounded by smaller protective ARC units. Missile trails, gas clouds, flash effects

-----

## 6. RAIDER (Player Character) Visual Recognition Guide

### 6.1 General Player Appearance

Raiders are HUMAN characters. In a frame, they look like:

- Third-person perspective: Your player character is visible in lower-center/lower-right of frame, seen from behind/over-the-shoulder
- Other players: Human-shaped figures at various distances, wearing various outfits
- **Art style**: Post-post-apocalyptic. Weathered, utilitarian clothing. Muted earth tones (browns, greys, tans, olive). Gear looks scavenged and repurposed. NOT shiny sci-fi armor — more rugged survivalist
- **Body types**: Both male and female character models, various body types available
- **Silhouette**: Human figure + backpack + visible weapon. Backpacks vary in size and shape per outfit and contribute heavily to silhouette recognition

### 6.2 Outfit Recognition (Key Skins to Know)

Outfits are full-set (no mix-and-match). The outfit a player wears is purely cosmetic — it does NOT indicate their actual armor level or combat capability. Common outfits include:

- **Default Jumpsuit**: Basic starting outfit, simple utilitarian jumpsuit. Very common in early game/free loadout players
- **Torpedo**: Clean, flexible design. Very popular, considered one of the safest/best cosmetic choices
- **Driftcoat**: Understated, cool style. Top-tier popular outfit
- **Boonie**: Sleek techwear/ninja aesthetic, very recognizable silhouette
- **Sforza**: Retro sci-fi 80s comic book style, iconic
- **Macrame**: Popular among PvP-aggressive players — seeing this skin signals danger
- **Misthorn**: Creepy, folk-horror inspired. Occult imagery, very distinctive
- **Riot**: Dorky shorts, short sleeves — "the helpful person skin"
- **Ryder-style (bright yellow + face covering)**: Known as a hostile/aggressive player indicator

### 6.3 Distinguishing Players from ARC (CRITICAL)

| Feature | Player (Raider) | ARC Machine |
|---|---|---|
| **Shape** | Humanoid bipedal | Varied: spheres, quadrupeds, drones, spiders |
| **Movement** | Human running/sprinting/crouching/sliding | Rolling, flying, skittering, mechanical locomotion |
| **Color palette** | Earth tones, muted clothing colors | Metallic silver/white/dark with glowing elements |
| **Scanner beam** | NONE | White/Blue/Yellow/Red scanning beam |
| **Weapons** | Held firearms (rifle/shotgun/pistol shape) | Integrated weapons (turrets, rockets, built-in guns) |
| **Size** | Human-sized (~1.7-1.9m equivalent) | Ranges from tiny (Tick/Pop) to colossal (Queen) |
| **Backpack** | Visible backpack on most Raiders | No backpacks |
| **Damage feedback** | Blood/hit effects, shield shimmer | Metal breaking, parts flying off, sparks, armor plating shattering |

### 6.4 Player Actions & Animation States

- **ADS (Aim Down Sights)**: Player raises weapon to eye level, camera zooms in slightly. Active combat indicator
- **Hip-fire**: Weapon at waist, shooting without aiming. Fast-paced combat
- **Sprint**: Forward-leaning run, weapon lowered
- **Crouch/Crouch-walk**: Compressed model, slower movement. Stealth
- **Slide**: Fast low-to-ground sliding animation. Evasive combat maneuver
- **Melee (Pickaxe)**: Arm swing with pickaxe tool. Used to kill Ticks or break objects
- **Downed state**: On ground, crawling. Red/critical. Teammate can revive
- **Revive**: One player kneeling next to downed player, progress bar above
- **Looting/Breaching**: Facing container/probe, interaction animation with hand or tool
- **Extraction**: Standing in extraction zone with visible zone marker, using flare/signal
- **Emote/Gesture**: Dance moves, peace signs, waves. Emoting during combat = funny clip
- **Shield recharge**: Using recharger item, energy effect around character
- **Raider Tool use**: Arm-mounted glowing tool for breaching ARC Probes

### 6.5 Scrappy (Pet Chicken Companion)

- **Visual**: Small chicken/rooster following the player around
- **Customizable**: Can wear hats and cosmetic items
- **Function**: Picks up small materials while exploring
- **Clip signal**: Scrappy in funny situations or surviving chaos = wholesome content

### 6.6 PvP vs PvE Recognition

| Indicator | PvE (Fighting ARC) | PvP (Fighting Players) |
|---|---|---|
| **Enemy shape** | Mechanical/robotic | Humanoid with gear |
| **Enemy movement** | Mechanical patterns | Human sprint/slide/crouch |
| **Damage effects** | Sparks, metal debris, parts breaking | Blood effects, shield break shimmer |
| **Kill feed** | ARC names (Bastion, Wasp, etc.) | Player gamertags |
| **Tension** | Predictable | Unpredictable — HIGHER clip potential |
| **Stakes** | Lower risk | Steal gear on kill — high stakes |

**PvPvE Chaos** (both happening simultaneously) = **HIGHEST clip potential**. Both mechanical enemies AND human opponents visible/active = always clip.

-----

## 7. HUD & UI Deep Dive

ARC Raiders has a **minimalist HUD** — devs intentionally kept UI sparse for immersion. Key elements:

### 7.1 Player HUD (Screen Edges)

- **Health/Shield indicators**: Bottom-left area. Shield is separate layer from health. Shield shimmer/break effect on character when hit
- **Ammo counter**: Near crosshair or bottom, shows magazine / reserve
- **Quick-use slots**: Bottom of screen, equipped gadgets (grenades, meds, rechargers)
- **Minimap**: Corner, showing terrain, extraction points as markers, enemy red dots
- **Crosshair/Reticle**: Center, changes per weapon and ADS state. Hit markers flash on hits
- **Interaction prompts**: Contextual "Press [key] to..." near interactable objects

### 7.2 Notification Elements (High Clip-Signal)

- **Kill feed**: Top-right, who killed what/whom
- **XP/reward popups**: After kills/looting, numbers and item names
- **Extraction timer**: Countdown when active — low timer = extreme tension
- **Damage direction**: Red vignette/arc on screen edges showing damage source direction
- **Downed teammate**: Squad status icons for alive/downed/dead teammates
- **ARC detection alert**: Visual cue when ARC has spotted you

### 7.3 Screen States That Signal Events

- **Death screen**: Full-screen overlay showing killer info
- **Spectator mode**: Camera follows teammate after death
- **Inventory/loot screen**: Grid UI overlay — NOT clip-worthy unless extremely rare loot
- **Extraction success**: Summary of loot extracted — end of run
- **Loading/deploy screen**: Pre-match — NOT clip-worthy

-----

## 8. Prompt Template for Vision Model

Use this prompt when feeding frames to the vision model:

```
You are analyzing a frame from an ARC Raiders Twitch stream to determine if it
contains a clip-worthy moment. ARC Raiders is a third-person co-op PvPvE
extraction shooter with sci-fi robotic enemies called ARC machines.

STEP 1 — IDENTIFY ENTITIES IN FRAME:

ARC MACHINES (robotic enemies — look for these specific types):
- Rollbot/Pop/Fireball: Small rolling spheres on ground (low threat, funny if swarm)
- Tick: Tiny spider bot on walls/ceilings or latched onto player's head (high clip value)
- Wasp/Hornet: Small flying drones with rotors (common combat)
- Snitch: High-altitude unarmed scout drone (triggers reinforcements)
- Rocketeer: LARGE flying robot with rocket trails (high danger, big explosions)
- Shredder: Dark cylindrical hovering "eye" rushing players (devastating AOE)
- Firefly: Aggressive flying flame unit diving at players
- Bastion: MASSIVE crab-like 4-legged machine with turret (always dramatic)
- Leaper: 4-legged jumping robot mid-air or shockwave landing (very dramatic)
- Bombardier: Bastion-like with mortar + small Spotter drones orbiting
- Comet: Large armored explosive sphere with opening armor plates
- Turret/Sentinel: Stationary gun/sniper with visible laser beam
- ARC Probe: Large landed pod being breached with alarm siren VFX
- Queen: COLOSSAL multi-legged boss, laser beam, fills most of frame (ALWAYS CLIP)
- Matriarch: Enormous boss with energy shield bubble + child ARC swarm (ALWAYS CLIP)

PLAYERS (human Raiders):
- Humanoid figures in muted earth-tone clothing with backpacks
- Holding visible firearms (rifles, shotguns, launchers)
- Your player: lower-center/lower-right of frame, over-the-shoulder view
- Other players: human figures at various distances — PvP targets

SCANNER BEAM STATE (on any ARC):
- White/Blue = patrol (not clip-worthy)
- Yellow = alerted (tension building)
- Red = combat (clip-worthy)

STEP 2 — EVALUATE CLIP INDICATORS:

COMBAT INDICATORS:
- Muzzle flash, tracers, projectile trails visible?
- Explosions or large VFX events (fire, smoke, debris)?
- ARC destruction feedback visible (parts breaking off, legs buckling, rotors lost)?
- Kill feed active? Player kill or ARC kill?
- Hit markers or damage numbers?

TENSION INDICATORS:
- Player health/shield status? (full/damaged/critical/downed)
- Ammo count? (full/low/empty)
- How many threats visible? Multiple ARC + players = chaos
- Extraction timer visible and low?
- Damage direction vignette on screen edges?

SPECTACLE INDICATORS:
- Boss ARC visible? (Queen/Matriarch = automatic high score)
- Heavy ARC visible? (Bastion/Leaper/Bombardier = dramatic)
- Ragdoll physics or physics-based destruction happening?
- Large enemy mid-jump or mid-attack animation?
- Environmental destruction?
- Tick latched onto player head?
- Multiple simultaneous VFX effects?

EMOTIONAL INDICATORS:
- Death screen visible?
- Downed player being revived?
- Squad status showing teammates dead?
- Extraction success screen?
- Emote being performed during combat?
- Scrappy (pet chicken) visible in chaotic situation?

STEP 3 — PROVIDE ASSESSMENT:

1. clip_score: 0-100 (how clip-worthy is this frame)
2. category: "combat_highlight" | "funny_wtf" | "epic_moment" | "close_call" | "loot_discovery" | "death_fail" | "boss_fight" | "pvp_encounter" | "routine" | "downtime"
3. entities_detected: List ARC types and players visible
4. description: Brief description of what's happening
5. confidence: 0-1 (how confident you are)
6. suggested_clip_type: "highlight" | "funny" | "epic" | "skip"
```

-----

## 9. Scoring Rubric

| Score Range | Meaning | Action |
|---|---|---|
| **80-100** | Must-clip: Multi-kill, boss kill, epic fail, perfect WTF moment | Auto-clip, extend +/-5 seconds |
| **60-79** | Strong clip: Good kill, funny death, tense moment | Clip if near other high-scoring frames |
| **40-59** | Moderate: Single kill, minor action, decent moment | Clip only if part of a larger sequence |
| **20-39** | Low: Routine combat, basic gameplay | Skip unless context elevates it |
| **0-19** | Skip: Walking, looting, menus, idle | Skip entirely |

-----

## 10. Common False Positives to Avoid

- **Menu/inventory screens**: Bright, busy UI but not clip-worthy
- **Loading screens / transitions**: Visual noise, no gameplay
- **Idle movement / walking**: Player just traversing without action
- **ADS without combat**: Aiming but nothing happening
- **Chat/overlay elements**: Twitch chat overlay, donation alerts, webcam — ignore these
- **Pause menu**: Game paused, not action
- **Map screen**: Strategic view, not moment-to-moment action
- **Respawn countdown**: Brief UI, only notable if death was interesting

-----

## 11. Frame Sequence Clustering Strategy

When processing the full VOD as frames:

1. **Score every Nth frame** (e.g., every 30th frame = 1 per second at 30fps)
2. **Identify peaks**: Frames scoring >60
3. **Expand peaks**: For any frame >60, also score adjacent frames at full density
4. **Cluster nearby peaks**: Merge peaks within 5-10 seconds of each other into one clip
5. **Set clip boundaries**: Start 2-3 seconds before first high-scoring frame, end 2-3 seconds after last high-scoring frame in cluster
6. **Rank clips**: Sort by peak score x duration bonus (longer sustained action = better)
7. **Deduplicate**: If clips overlap, merge or keep the higher-scoring one

-----

## 12. Dataset Statistics Summary

From the annotated dataset of 1,019+ frames:

- **Source**: ARC Raiders Twitch VOD + "WTF Funny Moments Ep. 2" compilation
- **Frame range**: Scene 2 through Scene 3341 (with ~120 additional compilation frames)
- **Annotation tool**: Roboflow (indicated by `_rf_` filename hashes)
- **Sampling**: Non-uniform — annotator selected frames around interesting moments
- **Densest segments**: Scenes 500-999, 1500-1999, and 2000-2499 (200+ frames each)
- **Sparsest segment**: Scenes 2500-2999 (only 12 frames — likely menu/downtime)
- **Unique frames**: 929 unique scene numbers with some duplicates (multiple annotations per scene)

The presence of duplicates (same scene number, different hashes) indicates multiple labeled objects within a single frame — confirming these frames contain multiple recognizable features (enemies, effects, HUD elements) simultaneously, which is characteristic of high-action moments.
