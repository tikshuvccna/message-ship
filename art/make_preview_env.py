"""python art/make_preview_env.py -> art/preview_env_tiles.png (each mood tiled 2x2: seams visible if any),
art/preview_env.png (day scene: sea tile + islands, lighthouse lit + beam, reefs, foam, waves, ship, a few creatures),
art/preview_env_items.png (every env frame)."""
import json
import math
import os

from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "public", "assets")
SIN35, COS35 = math.sin(math.radians(35)), math.cos(math.radians(35))


def atlas(p):
    return json.load(open(p + ".json", encoding="utf-8")), Image.open(p + ".png").convert("RGBA")


def fr(at, n):
    js, im = at
    f = js["frames"][n]
    r = f["frame"]
    return im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])), f.get("anchorPx", {"x": r["w"] / 2, "y": r["h"] / 2})


env = atlas(os.path.join(A, "env", "env"))
ship = atlas(os.path.join(A, "ship", "ship"))
cre = atlas(os.path.join(A, "creatures", "creatures"))

# tiles
moods = ["day", "dusk", "storm", "noise"]
strip = Image.new("RGBA", (4 * 522, 522), (0, 0, 0, 255))
for i, m in enumerate(moods):
    t = Image.open(os.path.join(A, "env", f"sea_tile_{m}.png")).convert("RGBA")
    for dx in (0, 256):
        for dy in (0, 256):
            strip.alpha_composite(t, (i * 522 + 5 + dx, 5 + dy))
strip.save(os.path.join(ROOT, "art", "preview_env_tiles.png"))

W, H = 1600, 900
bg = Image.new("RGBA", (W, H))
t = Image.open(os.path.join(A, "env", "sea_tile_day.png")).convert("RGBA")
for y in range(0, H, 256):
    for x in range(0, W, 256):
        bg.alpha_composite(t, (x, y))


def put(at, n, x, y, alpha=1.0, add=False):
    img, a = fr(at, n)
    if alpha < 1:
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    pos = (int(x - a["x"]), int(y - a["y"]))
    if add:
        layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        layer.alpha_composite(img, pos)
        rgb = ImageChops.add(bg.convert("RGB"), ImageChops.multiply(layer.convert("RGB"), Image.merge("RGB", [layer.getchannel("A")] * 3)))
        bg.paste(rgb.convert("RGBA"))
    else:
        bg.alpha_composite(img, pos)


for i, (x, y) in enumerate(((1200, 160), (300, 120), (1450, 520), (900, 820), (150, 760), (700, 80))):
    put(env, f"wave_{i % 4}", x, y)
for i, (x, y) in enumerate(((1000, 380), (450, 860), (1300, 760))):
    put(env, f"foam_{i}", x, y)
put(env, "island_d", 1330, 260)
put(env, "reef_b", 1120, 620)
put(env, "buoy", 1000, 520)
put(env, "bottle", 1400, 700)
put(env, "crate_float", 1200, 820)
put(env, "lighthouse_lit", 1500, 880)
lj = env[0]["frames"]["lighthouse_lit"]["lampPx"]
put(env, "lighthouse_beam", 1500 + lj[0], 880 + lj[1], add=True)
O = (560, 560)
put(ship, "ship_shadow", *O)
put(ship, "waterline_foam", *O)
put(ship, "hull", *O)
put(ship, "hull_front", *O)
put(ship, "mast", O[0] + 56, O[1])
put(ship, "sail_0", O[0] + 56, O[1], alpha=0.85)
put(cre, "tide_whale_noise_0", 1180, 470)
put(cre, "garble_squid_noise_1", 1000, 700)
put(cre, "static_jelly_friend_0", 1050, 250)
put(env, "fog_1", 250, 300, alpha=0.7)
bg.save(os.path.join(ROOT, "art", "preview_env.png"))

# all items
sheet = Image.new("RGBA", (2048, 1300), (58, 132, 160, 255))
x = y = rowh = 0
for n in sorted(env[0]["frames"]):
    img, a = fr(env, n)
    if x + img.width > 2048:
        x, y, rowh = 0, y + rowh + 8, 0
    sheet.alpha_composite(img, (x, y))
    x += img.width + 8
    rowh = max(rowh, img.height)
sheet.crop((0, 0, 2048, y + rowh)).save(os.path.join(ROOT, "art", "preview_env_items.png"))
print("ok")
