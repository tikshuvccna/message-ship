# Message Ship art pipeline (Blender 5.2 headless + Pillow -> Phaser atlases)

Standalone: the scripts here were copied and adapted from game 1 (`v2lib`, `v2_parts`, `v2_face`, `v2_cast*`). Nothing imports from the old repo.
Requirements: Blender 5.2 (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, override with env `BLENDER`), Python 3 with Pillow and numpy.

## Rebuild
```
python art/build_all.py                      # everything, about 6 minutes
python art/build_all.py ship                 # or: creatures | kraken | env | cast (any combination)
```
Raw renders go to `art/_raw/<group>/` (git-ignored) with a `meta.json` per group. Single steps:
```
blender -b --python art/blender/ship.py -- <ABS rawdir> hull mast sails stations props flags fx
blender -b --python art/blender/sea_creatures.py -- <ABS rawdir> [id ...]
blender -b --python art/blender/kraken.py -- <ABS rawdir>
blender -b --python art/blender/env.py -- <ABS rawdir> [name ...]
blender -b --python art/blender/ms_render.py -- portrait|sprite <name,name|all> <ABS rawdir>
python art/fx_pil.py <rawdir> ship|creatures      python art/env_pil.py <rawdir>
python art/pack_atlas.py ship|creatures|kraken|env <rawdir>
python art/pack_cast.py portraits|sprites <rawdir>
python art/view.py out.png <zoom> raw1.png ...    # quick look at raw frames (outline + downscale)
```
Use an ABSOLUTE raw dir (a relative one resolves against Blender's cwd).

## Look and projection
- Ortho camera 35 deg down, 56 px/unit, rendered at 4x and downscaled (Lanczos), 1 px dark violet outline added in the pack step.
  `sx = x*56`, `sy = -y*32.12 - z*45.87` (x = bow/right, y = away from camera, z = up). Same as the contract and game 1.
- `v2lib` toon: luminance ramp of colour multipliers (violet shadow, warm light), AO, amber rim on the upper right, inverted-hull inner lines.
  Lights: warm key from the upper left, cool fill, warm back light. Added here: a `planks` pattern (per-plank tint, grain, seams, butt joints).
  Fixed here: `add_lines` now works on multi-material meshes.
- Rule learned: soft "halo" glow spheres turn into solid discs once outlined. Glows in sprites are solid emissive parts only; soft light is
  the separate `lantern_glow` / `lighthouse_beam` sprites (ADD blend).

## Atlases (Phaser "JSON hash"; every frame has `anchor` {x,y} normalised -> `setOrigin(anchor.x, anchor.y)`, and `anchorPx`)
Frames are trimmed; the anchor is re-expressed in the trimmed frame and can lie outside it (>1), e.g. sails.

### `public/assets/ship/ship.png|json` (64 frames)
- `hull`, `hull_front`, `ship_shadow`, `waterline_foam`: all share the ship origin (deck centre, z=0). Draw order: sea, `ship_shadow`,
  `waterline_foam`, `hull`, deck objects and characters (depth-sorted by y), `hull_front`, `mast`/`sail_*`.
  Far bulwark is solid (0.9 high, cream inner face) with gun ports cut at the far cannon (x=1) and the stern cannon (y=1.8).
  Near side is a cutaway: solid gunwale 0.34 high + open balustrade up to the rail (so items near the near rail stay visible).
  The near cannon (1,-3.2) sits in a gap of the balustrade but its base hides behind the gunwale: draw it above `hull_front` if needed.
- Stations, each anchored at its own ground point (place at the projected station position): `wheel` (disc faces the camera; helmsman
  stands behind it), `wheel_base` + `wheel_disc_0..7` (anim `wheel_spin`, 1/8 of a spoke turn per frame), `cannon_base`
  (`pivotPx` = barrel pivot offset), `cannon_barrel_00..15` (yoke + barrel aimed at world angle i*22.5 deg, 0 = +x bow, 90 = +y far,
  same anchor as the base), `cannon_barrel` (barrel alone pointing +x, anchor = pivot, for 2D rotation), `rack` (`slotsPx`: 7 ball centres
  in px from the anchor), `hatch`, `hatch_open`, `mast` (`topPx` for the flag, `nestPx`), `sail_0|1|2` (full / reefed / furled, anchor = mast
  foot, draw semi-transparent above characters), `flag_0..3` (anim `flag`, anchor = staff, place at mast `topPx`).
- Props: `crate_a`, `crate_b` (stack), `crate_c` (mail crate), `barrel` (water), `bucket`, `bucket_empty`, `plank`, `plank_stack`,
  `ball` (neutral white: `setTint(ammo colour)`), `anchor`, `lantern_glow` (ADD, centre).
- FX: `flame_0..5` (anim `flame`), `leak_0..3` (anim `leak`; hole + spout + puddle).

### `public/assets/creatures/creatures.png|json` (80 frames)
`<id>_noise_0|1` and `<id>_friend_0|1` for all 18 ids of `content/he/creatures.json` (anims `<id>_noise`, `<id>_friend`).
Sprites face screen-LEFT (towards the ship), flipX to face right. Anchor = water point under the creature. Each model is scaled so its body
matches the json `radius` (copied as `radiusPx`). Noise = dark palette, glowing red-orange slit eyes, 3D letters on the body, plus a pack-step
glitch (RGB split, shifted slices, letters flaking upward between frames 0 and 1). Friend = bright and cute.
Looks: squid with letter-tipped tentacles / rainbow squid; static jelly with lightning / glowing jelly; tide whale overstuffed with envelopes
and stitched seams / cloud whale; echo gulls with sound arcs / postman gull; murky cracked bottle / bottle with a letter and address tag;
crumpled-page crab / folder crab; cable eel with torn plug and frayed wires / lightning eel with gold contacts; frame crab with a broken frame /
shell crab; hermit with a crooked house / map house; port urchin with broken doors / numbered doors (80 53 22); session snail with split shell
and cut cord / story snail; cipher jelly in chains + padlock / rainbow jelly; web gull with endless loading ring / browser gull; bare dull pearl
/ golden pearl in a clam; segment barnacle with port tags; packet ray carrying an IP envelope / star ray; frame turtle with header and trailer
bands; bit swarm of 0/1 fish.
FX in the same atlas: `ink`, `bolt_noise`, `clean_burst_0..5` (anim `clean_burst`, repeat 0). Codex singles: `creatures/<id>.png` (friend) and
`<id>_noise.png`.

### `public/assets/creatures/kraken.png|json` (24 frames)
`kraken_head_p1|p2|p3|friend_0|1` (p1: five rule symbols on the forehead, p2: seven stacked layer eyes, p3: nested crates on the head,
friend: lilac with a messenger cap), `kraken_arm_p1_<addr|code|fmt|size|time>_0|1` (rule-coloured glowing bands + symbol),
`kraken_arm_p2_0|1` (7 layer rings), `kraken_arm_p3_0|1` (clutching crates), `kraken_arm_friend_0|1`. Anchor = water point; flipX arms.

### `public/assets/env/` (env.png|json, 40 frames, + 4 tiles)
`sea_tile_day|dusk|storm|noise.png`: 256x256 seamless toon water (3 tone bands + crest lines; noise has faint letters and embers).
Frames: `island_a` (palm), `island_b` (rocky hill + mail hut), `island_c` (sandbar + chest), `island_d` (big green island), `reef_a..c`,
`lighthouse_unlit`, `lighthouse_lit` (`lampPx`), `lighthouse_beam` (ADD, anchor at the lamp end, rotate to sweep), `pier`, `buoy`,
`buoy_dark`, `bottle`, `crate_float`, `cove_a` (rock arch), `cove_b` (cliff bay), `foam_0..3`, `wave_0..3` (anim), `fog_0..3`, `rain`,
`rain_splash_0..2`, `lightning`, `lightning_1` (anchor = top), `whirlpool`, `whirlpool_0..3` (anim). Props have a foam ring baked in and are
anchored at their centre on the water surface.

### Characters and portraits
- `public/assets/characters/<name>.png|json`: `hero_girl`, `hero_boy` (sailor heroes), `naama`, `uri`, `talia`, `barak`: game-1 layout
  (1024x2048, 128 px cells, rows 0-7 idle x4 [frame 3 blink] S SW W NW N NE E SE, rows 8-15 walk x8, origin (64,110)). `bit`: `float_0..3`
  (anim `float`), hovering ~1.25 units above (64,110). Copied from game 1: `apprentice_girl|boy`, `skin_girl_sea`, `skin_boy_navy`
  (these still hold game 1's glowing needle).
- `public/assets/portraits/<who>_<mood>.png`: 512x512, who = naama bit uri talia barak hero_girl hero_boy, mood = neutral happy worried
  surprised (+ `index.json`). Busts turned ~24 deg to the viewer's left.
- Cast: Naama = elder captain, wide navy hat with gold band and badge, navy coat with epaulettes and gold buttons, knitted scarf, ankle-length
  skirt. Uri = older keeper, knit cap, round glasses, white beard, teal sweater, rule-book with five ribbons. Talia = headscarf in red/yellow
  bands, seven-colour bead necklace, teal cardigan, spyglass. Barak = broad dock worker, plaid shirt, orange work vest, cap, short beard.
  Bit = brass lantern with a face on the glass and little hook arms. Modesty rules baked in (head covered, long sleeves, long skirt/trousers).

## Previews (look at these)
`art/preview_ship.png` (stations at the contract coordinates with red markers, characters for scale), `preview_ship_big.png` (2x),
`preview_ship_items.png`, `preview_creatures.png` (noise 0/1 on dark, friend 0/1 on sea), `preview_portraits.png`, `preview_cast.png`,
`preview_env.png` (composed day scene), `preview_env_tiles.png` (each tile 2x2 for seams), `preview_env_items.png`.

## Known limitations
- Characters are lofted primitives (game-1 v2 style). Naama's wide brim shades her face in the S sprite view.
- Fore-and-aft sails necessarily cover part of the far deck; draw them semi-transparent (contract) or fade when a player is under them.
- Creatures are rendered in one facing (left) only; no turn frames. Small creatures (gulls, bit swarm) read mostly by colour and shape.
- Kraken head is a mottled dome; phases differ by details (runes / stacked eyes / crates), not silhouette.
- The waterline foam ring is a 2D approximation of the hull waterline (slightly off at the bow tip).
- Sea tiles repeat visibly over very large areas; mix with `wave_*` and `foam_*` overlays.
