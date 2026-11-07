"""Composite preview of the ship atlas with stations at the contract coordinates and characters for scale.
python art/make_preview_ship.py  -> art/preview_ship.png (1x) and art/preview_ship_big.png (2x crop)"""
import json
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "public", "assets")
SIN35, COS35 = math.sin(math.radians(35)), math.cos(math.radians(35))


def atlas(path):
    js = json.load(open(path + ".json", encoding="utf-8"))
    im = Image.open(path + ".png").convert("RGBA")
    return js, im


def frame(js, im, name):
    f = js["frames"][name]
    r = f["frame"]
    return im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])), f.get("anchorPx") or {"x": 64, "y": 110}


def proj(x, y, z=0.0):
    return x * 56, -y * 56 * SIN35 - z * 56 * COS35


def tint(img, hexc):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    from PIL import ImageChops
    m = Image.new("RGBA", img.size, (r, g, b, 255))
    out = ImageChops.multiply(img, m)
    out.putalpha(img.getchannel("A"))
    return out


def main():
    sj, si = atlas(os.path.join(A, "ship", "ship"))
    W, H = 1600, 900
    O = (560, 560)   # ship origin on screen
    bg = Image.new("RGBA", (W, H), (52, 128, 158, 255))
    # sea tile if present
    tile = os.path.join(A, "env", "sea_tile_day.png")
    if os.path.exists(tile):
        t = Image.open(tile).convert("RGBA")
        for y in range(0, H, t.height):
            for x in range(0, W, t.width):
                bg.alpha_composite(t, (x, y))

    def put(name, x, y, z=0.0, atl=(sj, si), alpha=1.0, tint_hex=None):
        img, a = frame(atl[0], atl[1], name)
        if tint_hex:
            img = tint(img, tint_hex)
        if alpha < 1:
            al = img.getchannel("A").point(lambda v: int(v * alpha))
            img.putalpha(al)
        px, py = proj(x, y, z)
        bg.alpha_composite(img, (int(round(O[0] + px - a["x"])), int(round(O[1] + py - a["y"]))))

    put("ship_shadow", 0, 0)
    put("waterline_foam", 0, 0)
    put("hull", 0, 0)
    ammo = ["#ffb84a", "#4ad6c8", "#8f7bff", "#ff7f6e", "#7fd957", "#ffb84a", "#4ad6c8"]
    chars = {}
    for nm in ("hero_girl", "hero_boy", "naama", "talia"):
        chars[nm] = atlas(os.path.join(A, "characters", nm))
    sprites = []   # (y, callable)

    def S(y, fn):
        sprites.append((y, fn))

    S(0.0, lambda: put("wheel", -6.2, 0))
    S(0.0, lambda: (put("cannon_base", 6.8, 0), put("cannon_barrel_00", 6.8, 0)))
    S(1.8, lambda: (put("cannon_base", -7.4, 1.8), put("cannon_barrel_08", -7.4, 1.8)))
    S(3.2, lambda: (put("cannon_base", 1.0, 3.2), put("cannon_barrel_04", 1.0, 3.2)))
    S(-3.2, lambda: (put("cannon_base", 1.0, -3.2), put("cannon_barrel_12", 1.0, -3.2)))
    S(0.0, lambda: put("mast", 1.0, 0))

    def rack():
        put("rack", -3.2, 2.9)
        f = sj["frames"]["rack"]
        for i, (dx, dy) in enumerate(f["slotsPx"]):
            img, a = frame(sj, si, "ball")
            img = tint(img, ammo[i])
            px, py = proj(-3.2, 2.9)
            bg.alpha_composite(img, (int(O[0] + px + dx - 16), int(O[1] + py + dy - 16)))
    S(2.9, rack)
    S(-2.8, lambda: put("plank_stack", -4.6, -2.8))
    S(-2.8, lambda: put("barrel", 4.2, -2.8))
    S(-2.5, lambda: put("bucket", 4.75, -2.45))
    S(-0.6, lambda: put("hatch", -1.4, -0.6))
    S(2.7, lambda: put("crate_b", -0.6, 2.7))
    S(2.75, lambda: put("crate_c", 3.0, 2.75))
    S(-1.6, lambda: put("leak_1", 2.6, -1.6))
    S(1.0, lambda: put("flame_2", -1.9, 1.0))
    S(0.7, lambda: put("idle_S_0", -6.2, 0.7, atl=chars["naama"]))
    S(-0.7, lambda: put("idle_E_0", 5.9, -0.6, atl=chars["hero_boy"]))
    S(2.2, lambda: put("walk_W_2", -2.6, 2.2, atl=chars["hero_girl"]))
    S(-2.4, lambda: put("idle_SE_0", -0.3, -2.4, atl=chars["talia"]))
    for y, fn in sorted(sprites, key=lambda t: -t[0]):
        fn()
    put("hull_front", 0, 0)
    mt = sj["frames"]["mast"]["topPx"]
    img, a = frame(sj, si, "flag_1")
    px, py = proj(1.0, 0)
    bg.alpha_composite(img, (int(O[0] + px + mt[0] - a["x"]), int(O[1] + py + mt[1] - a["y"])))
    put("sail_0", 1.0, 0, alpha=0.82)
    # station markers
    d = ImageDraw.Draw(bg)
    for (x, y) in ((-6.2, 0), (6.8, 0), (-7.4, 1.8), (1, 3.2), (1, -3.2), (1, 0), (-3.2, 2.9), (-4.6, -2.8), (4.2, -2.8),
                   (-1.4, -0.6)):
        px, py = proj(x, y)
        cx, cy = O[0] + px, O[1] + py
        d.line((cx - 4, cy, cx + 4, cy), fill=(255, 0, 80, 255))
        d.line((cx, cy - 4, cx, cy + 4), fill=(255, 0, 80, 255))
    out = os.path.join(ROOT, "art", "preview_ship.png")
    bg.save(out)
    big = bg.crop((0, 120, 1100, 760)).resize((2200, 1280), Image.NEAREST)
    big.save(os.path.join(ROOT, "art", "preview_ship_big.png"))
    # sails / items sheet
    sheet = Image.new("RGBA", (1600, 1000), (52, 128, 158, 255))
    x, y, rowh = 10, 10, 0
    for nm in sorted(sj["frames"]):
        img, a = frame(sj, si, nm)
        if nm in ("hull", "hull_front", "ship_shadow"):
            continue
        if x + img.width > 1590:
            x, y, rowh = 10, y + rowh + 10, 0
        sheet.alpha_composite(img, (x, y))
        x += img.width + 10
        rowh = max(rowh, img.height)
    sheet = sheet.crop((0, 0, 1600, min(1000, y + rowh + 10)))
    sheet.save(os.path.join(ROOT, "art", "preview_ship_items.png"))
    print("ok")


main()

