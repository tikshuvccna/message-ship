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


def waterline_foam():
    W, H = 1180, 320
    ox, oy = 560, 70
    ss = 3
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = outline_pts(-1.0, 1.0)
    # match the hull waterline (x*0.93, y*0.86 at z=-1) and push slightly outwards
    pts = []
    for x, y in CTRL:
        pts.append((x * 0.95, y * 0.9))
    full = pts + [(x, -y) for x, y in reversed(pts[1:-1])]
    P = [((ox + x * 56) * ss, (oy - y * 56 * SIN35 + 45.87) * ss) for x, y in full]
    P.append(P[0])
    d.line(P, fill=(245, 252, 255, 235), width=7 * ss, joint="curve")
    rnd = __import__("random").Random(3)
    for i in range(70):
        k = rnd.randrange(len(P) - 1)
        x, y = P[k]
        r = rnd.uniform(3, 7) * ss
        d.ellipse((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=(255, 255, 255, 230))
    im = im.resize((W, H), Image.LANCZOS)
    return im, (ox, oy)


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
        fo, a2 = waterline_foam()
        fo.save(os.path.join(gdir, "waterline_foam.png"))
        meta["waterline_foam"] = dict(cell=list(fo.size), anchor=list(a2), pil=True,
                                      note="same origin as hull; draw between ship_shadow and hull (only the near edge shows)")
        sh, a = ship_shadow()
        sh.save(os.path.join(gdir, "ship_shadow.png"))
        meta["ship_shadow"] = dict(cell=list(sh.size), anchor=list(a), pil=True,
                                   note="same origin as hull (ship centre on deck); draw under the hull, above the sea")
    if group == "creatures":
        creature_fx(gdir, meta)
    json.dump(meta, open(mp, "w"), indent=1)


def _blob(size, cx, cy, r, col, alpha=255, blur=0):
    im = Image.new("RGBA", size, col + (0,))
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=alpha)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    im.putalpha(m)
    return im


def creature_fx(gdir, meta):
    import random
    from PIL import ImageFont
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 16)
    OUTL = (44, 26, 66)
    # ink: glossy dark-violet blob with drips (what a squid spits)
    S = (40, 40)
    ink = Image.new("RGBA", S, (0, 0, 0, 0))
    ink.alpha_composite(_blob(S, 20, 20, 13, OUTL))
    ink.alpha_composite(_blob(S, 20, 20, 11, (58, 36, 92)))
    for (x, y, r) in ((9, 26, 4), (31, 13, 3), (28, 29, 3)):
        ink.alpha_composite(_blob(S, x, y, r + 1, OUTL))
        ink.alpha_composite(_blob(S, x, y, r, (58, 36, 92)))
    ink.alpha_composite(_blob(S, 15, 14, 3, (150, 130, 210)))
    ink.save(os.path.join(gdir, "ink.png"))
    meta["ink"] = dict(cell=[40, 40], anchor=[20, 20], pil=True, notrim=True, note="projectile, centre anchored")
    # bolt_noise: dark crackling orb with a glowing glyph core and orange glitch rim
    S = (48, 48)
    bolt = Image.new("RGBA", S, (0, 0, 0, 0))
    bolt.alpha_composite(_blob(S, 24, 24, 20, (255, 106, 42), alpha=120, blur=5))
    bolt.alpha_composite(_blob(S, 24, 24, 14, OUTL))
    bolt.alpha_composite(_blob(S, 24, 24, 12, (40, 28, 56)))
    d = ImageDraw.Draw(bolt)
    d.text((24, 24), "#", font=font, fill=(255, 150, 70, 255), anchor="mm")
    rnd = random.Random(4)
    for i in range(6):
        a = rnd.uniform(0, 6.28)
        x0, y0 = 24 + 13 * math.cos(a), 24 + 13 * math.sin(a)
        x1, y1 = 24 + 20 * math.cos(a + 0.2), 24 + 20 * math.sin(a + 0.2)
        d.line((x0, y0, x1, y1), fill=(255, 200, 120, 230), width=2)
    bolt.save(os.path.join(gdir, "bolt_noise.png"))
    meta["bolt_noise"] = dict(cell=[48, 48], anchor=[24, 24], pil=True, notrim=True, note="noise projectile, centre anchored")
    # clean_burst_0..5: warm light flash ring with sparkles; letters dissolve into light
    for f in range(6):
        t = f / 5
        S = (160, 160)
        im = Image.new("RGBA", S, (0, 0, 0, 0))
        core = radial((int(60 + 90 * t),) * 2, (255, 236, 170), power=1.4, alpha=max(0.0, 1 - t * 0.9))
        im.alpha_composite(core, (80 - core.width // 2, 80 - core.height // 2))
        ring = Image.new("L", S, 0)
        rr = 18 + 58 * t
        ImageDraw.Draw(ring).ellipse((80 - rr, 80 - rr, 80 + rr, 80 + rr), outline=int(255 * (1 - t) ** 0.7),
                                     width=max(2, int(9 * (1 - t))))
        ring = ring.filter(ImageFilter.GaussianBlur(1.2))
        rl = Image.new("RGBA", S, (255, 250, 220, 0))
        rl.putalpha(ring)
        im.alpha_composite(rl)
        d = ImageDraw.Draw(im)
        rnd = random.Random(9)
        for i in range(10):
            a = rnd.uniform(0, 6.28)
            dist = (20 + 55 * t) * rnd.uniform(0.6, 1.1)
            x, y = 80 + dist * math.cos(a), 80 + dist * math.sin(a)
            s = 5 * (1 - t) + 2
            al = int(255 * (1 - t) ** 0.6)
            col = rnd.choice(((255, 240, 160), (180, 255, 240), (255, 200, 230)))
            d.line((x - s, y, x + s, y), fill=col + (al,), width=2)
            d.line((x, y - s, x, y + s), fill=col + (al,), width=2)
        for i in range(5):   # letters fading into light
            a = rnd.uniform(0, 6.28)
            dist = 14 + 40 * t
            al = int(255 * max(0.0, 0.8 - t))
            d.text((80 + dist * math.cos(a), 80 + dist * math.sin(a) - 20 * t), rnd.choice("AQ#?%7"), font=font,
                   fill=(255, 200, 140, al), anchor="mm")
        im.save(os.path.join(gdir, f"clean_burst_{f}.png"))
        meta[f"clean_burst_{f}"] = dict(cell=[160, 160], anchor=[80, 80], pil=True, notrim=True,
                                        note="centre anchored; ADD or NORMAL blend")
    meta.setdefault("_anims", {})["clean_burst"] = {"frames": [f"clean_burst_{i}" for i in range(6)], "frameRate": 14,
                                                    "repeat": 0}


if __name__ == "__main__":
    main()
