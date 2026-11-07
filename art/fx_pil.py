"""Pillow-made frames (no Blender): soft glows, ship shadow. python art/fx_pil.py <ABS rawdir> ship"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIN35, COS35 = math.sin(math.radians(35)), math.cos(math.radians(35))
CTRL = [(-8.62, 0.0), (-8.5, 1.45), (-8.1, 2.52), (-7.3, 3.22), (-6.0, 3.48), (-3.0, 3.5), (1.6, 3.5),
        (4.4, 3.34), (6.4, 2.45), (7.75, 1.2), (8.48, 0.0)]


def radial(size, color, power=1.6, core=0.0, alpha=1.0):
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            dx = (x + 0.5 - w / 2) / (w / 2)
            dy = (y + 0.5 - h / 2) / (h / 2)
            d = math.sqrt(dx * dx + dy * dy)
            if d >= 1:
                continue
            a = (1 - d) ** power
            if core and d < core:
                a = 1.0
            r, g, b = color
            wk = max(0.0, 1 - d / 0.35) * 0.6      # whiter core
            px[x, y] = (int(r + (255 - r) * wk), int(g + (255 - g) * wk), int(b + (255 - b) * wk), int(255 * a * alpha))
    return im


def outline_pts(z=-1.0, k=0.93):
    pts = []
    for x, y in CTRL:
        pts.append((x * k, y * k))
    full = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
    return [(x * 56, -y * 56 * SIN35 - z * 56 * COS35) for x, y in full]


def ship_shadow():
    W, H = 1100, 300
    ox, oy = 520, 60
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    pts = [(ox + x + 14, oy + y) for x, y in outline_pts(-1.0, 0.98)]
    d.polygon(pts, fill=150)
    im = im.filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", (W, H), (18, 40, 70, 0))
    out.putalpha(im)
    return out, (ox, oy)


def main():
    raw, group = sys.argv[1], sys.argv[2]
    gdir = os.path.join(raw, group)
    os.makedirs(gdir, exist_ok=True)
    mp = os.path.join(gdir, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    if group == "ship":
        g = radial((128, 128), (255, 200, 110), power=1.8)
        g.save(os.path.join(gdir, "lantern_glow.png"))
        meta["lantern_glow"] = dict(cell=[128, 128], anchor=[64, 64], pil=True, notrim=True,
                                    note="additive blend (ADD); centre anchored")
        sh, a = ship_shadow()
        sh.save(os.path.join(gdir, "ship_shadow.png"))
        meta["ship_shadow"] = dict(cell=list(sh.size), anchor=list(a), pil=True,
                                   note="same origin as hull (ship centre on deck); draw under the hull, above the sea")
    json.dump(meta, open(mp, "w"), indent=1)


if __name__ == "__main__":
    main()
