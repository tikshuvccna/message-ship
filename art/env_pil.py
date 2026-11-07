"""Sea tiles + environment overlays (numpy + Pillow, no Blender).

python art/env_pil.py <ABS rawdir>
- public/assets/env/sea_tile_<day|dusk|storm|noise>.png : 256x256 seamless toon water (3 tone bands + crest lines).
- <rawdir>/env/*.png + meta.json (pil frames, packed into env.png by pack_atlas.py env):
  foam_0..3, wave_0..3, fog_0..3, rain, rain_splash_0..2, lightning, lightning_1, whirlpool, whirlpool_0..3, lighthouse_beam.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets", "env")
SIN35 = math.sin(math.radians(35))


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


MOODS = {
    'day': ("#2c86b0", "#3a9cc4", "#4fb0d0", "#d8f4fc", 0.8),
    'dusk': ("#33467a", "#4b5d94", "#c98a86", "#ffd9b8", 0.8),
    'storm': ("#1d333d", "#2a4751", "#47676d", "#cfe0de", 1.3),
    'noise': ("#1c142c", "#271d3e", "#3e2b55", "#ff8a4a", 0.5),
}


def field(N, seed, rough=1.0):
    """Seamless value field on an N x N grid (integer wave numbers)."""
    rnd = random.Random(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    # domain warp (seamless)
    wx = 0.035 * np.sin(2 * np.pi * (2 * y + 1 * x) + 1.3) + 0.02 * np.sin(2 * np.pi * (3 * x - 2 * y) + 0.4)
    wy = 0.02 * np.sin(2 * np.pi * (1 * x + 3 * y) + 2.1)
    X, Y = x + wx * rough, y + wy * rough
    v = np.zeros_like(x)
    # mostly horizontal crests (oblique sea): bigger ky
    for (kx, ky, a) in ((1, 4, 1.0), (2, 5, 0.7), (-1, 6, 0.55), (3, 7, 0.4), (-2, 9, 0.3), (4, 11, 0.22), (1, 13, 0.15)):
        v += a * np.sin(2 * np.pi * (kx * X + ky * Y) + rnd.uniform(0, 6.28))
    v = (v - v.min()) / (v.max() - v.min())
    return v


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def sea_tile(mood, N=256, ss=4):
    deep, mid, light, crest, sparkle = MOODS[mood]
    M = N * ss
    v = field(M, {'day': 1, 'dusk': 2, 'storm': 3, 'noise': 4}[mood], rough=1.6 if mood == 'storm' else 1.0)
    w = 0.012
    col = np.zeros((M, M, 3), np.float32) + hx(deep)
    t1 = smoothstep(0.42 - w, 0.42 + w, v)[..., None]
    col = col * (1 - t1) + hx(mid) * t1
    t2 = smoothstep(0.75 - w, 0.75 + w, v)[..., None]
    col = col * (1 - t2) + hx(light) * t2
    # crest line just above the light band edge
    c = (smoothstep(0.80 - w, 0.80, v) * (1 - smoothstep(0.835, 0.835 + w, v)))[..., None]
    col = col * (1 - c * 0.6) + hx(crest) * c * 0.6
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGB").resize((N, N), Image.LANCZOS).convert("RGBA")
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    if mood != 'noise':
        for i in range(int(14 * sparkle)):
            x, y = rnd.randrange(N), rnd.randrange(N)
            s = rnd.choice((1, 2))
            for dx in (-N, 0, N):     # wrap so the tile stays seamless
                for dy in (-N, 0, N):
                    d.line((x + dx - s, y + dy, x + dx + s, y + dy), fill=(255, 255, 255, 200))
    else:   # faint drifting letters + ember specks
        f = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 13)
        for i in range(10):
            x, y = rnd.randrange(N), rnd.randrange(N)
            ch = rnd.choice("AZQ#?%7@01")
            for dx in (-N, 0, N):
                for dy in (-N, 0, N):
                    d.text((x + dx, y + dy), ch, font=f, fill=(140, 100, 190, 70))
        for i in range(8):
            x, y = rnd.randrange(N), rnd.randrange(N)
            d.point((x, y), fill=(255, 120, 60, 200))
    return img


def ss_canvas(w, h, ss=4):
    return Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)), ss


def down(im, ss):
    return im.resize((im.width // ss, im.height // ss), Image.LANCZOS)


def foam(i):
    im, s = ss_canvas(96, 48)
    d = ImageDraw.Draw(im)
    rnd = random.Random(10 + i)
    for k in range(9):
        x = rnd.uniform(14, 82) * s
        y = (24 + rnd.uniform(-10, 10) * (1 - abs(x / s - 48) / 48)) * s
        r = rnd.uniform(4, 10) * s
        d.ellipse((x - r, y - r * 0.55, x + r, y + r * 0.55), fill=(240, 250, 255, 235))
    im = im.filter(ImageFilter.GaussianBlur(s * 0.6))
    a = im.getchannel("A").point(lambda v: 255 if v > 120 else int(v * 1.6))
    im.putalpha(a)
    return down(im, s)


def wave(i):
    im, s = ss_canvas(120, 40)
    d = ImageDraw.Draw(im)
    ph = i * 0.6
    pts = [(x * s, (22 - 9 * math.exp(-((x - 60) / 26) ** 2) * (1 + 0.15 * math.sin(ph)) + 2 * math.sin(x / 9 + ph)) * s)
           for x in range(8, 113, 2)]
    d.line(pts, fill=(255, 255, 255, 235), width=int(3.2 * s), joint="curve")
    pts2 = [(x * s, y + 5 * s) for x, y in pts[6:-6]]
    d.line(pts2, fill=(200, 236, 248, 150), width=int(2 * s), joint="curve")
    return down(im, s)


def fog(i):
    W, H = 300, 150
    im, s = ss_canvas(W, H)
    d = ImageDraw.Draw(im)
    rnd = random.Random(20 + i)
    for k in range(10):
        x = rnd.uniform(60, W - 60) * s
        y = rnd.uniform(H * 0.4, H * 0.65) * s
        r = rnd.uniform(35, 60) * s
        d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=(236, 232, 248, 150))
    im = im.filter(ImageFilter.GaussianBlur(14 * s))
    return down(im, s)


def rain():
    im, s = ss_canvas(8, 32)
    d = ImageDraw.Draw(im)
    for k in range(28 * s):
        a = int(220 * k / (28 * s))
        d.line((4 * s - k * 0.1, k + 2 * s, 4 * s - k * 0.1 + s, k + 2 * s), fill=(220, 240, 255, a))
    return down(im, s)


def rain_splash(i):
    im, s = ss_canvas(24, 12)
    d = ImageDraw.Draw(im)
    r = (3 + 4 * i) * s
    d.ellipse((12 * s - r, 6 * s - r * 0.45, 12 * s + r, 6 * s + r * 0.45), outline=(225, 245, 255, 220 - 60 * i), width=s)
    return down(im, s)


def lightning(seed):
    W, H = 140, 380
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rnd = random.Random(seed)
    pts = [(W / 2 + rnd.uniform(-10, 10), 0)]
    while pts[-1][1] < H - 10:
        x, y = pts[-1]
        pts.append((min(W - 15, max(15, x + rnd.uniform(-28, 28))), y + rnd.uniform(25, 45)))
    branches = []
    for k in range(2):
        j = rnd.randrange(2, len(pts) - 3)
        b = [pts[j]]
        for _ in range(3):
            x, y = b[-1]
            b.append((x + rnd.choice((-1, 1)) * rnd.uniform(10, 22), y + rnd.uniform(18, 30)))
        branches.append(b)
    glow_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_l)
    gd.line(pts, fill=(160, 190, 255, 200), width=16)
    for b in branches:
        gd.line(b, fill=(160, 190, 255, 150), width=10)
    glow_l = glow_l.filter(ImageFilter.GaussianBlur(7))
    im.alpha_composite(glow_l)
    d = ImageDraw.Draw(im)
    d.line(pts, fill=(255, 255, 240, 255), width=5)
    for b in branches:
        d.line(b, fill=(255, 255, 240, 255), width=3)
    return im


def whirlpool(i):
    W, H = 260, int(260 * SIN35) + 4
    ss = 3
    M = W * ss
    y, x = np.mgrid[0:M, 0:M].astype(np.float32)
    cx = cy = M / 2
    dx, dy = (x - cx) / (M / 2), (y - cy) / (M / 2)
    r = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    ph = i * (np.pi / 2) / 4
    arms = np.sin(4 * (th + 3.2 * np.sqrt(r + 1e-6) * 2.0) - ph * 4)
    col = np.zeros((M, M, 4), np.float32)
    deep = hx("#0f3a52")
    midc = hx("#2a7aa0")
    foamc = np.array([235, 248, 255], np.float32)
    base = deep * (1 - r[..., None]) + midc * r[..., None]
    f = smoothstep(0.55, 0.75, arms) * smoothstep(0.08, 0.25, r) * (1 - smoothstep(0.82, 1.0, r))
    rgb = base * (1 - f[..., None]) + foamc * f[..., None]
    a = (1 - smoothstep(0.85, 1.0, r)) * 255
    col[..., :3] = rgb
    col[..., 3] = a
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA").resize((W, W), Image.LANCZOS)
    return img.resize((W, H), Image.LANCZOS)


def beam():
    W, H = 460, 170
    ss = 2
    M = (W * ss, H * ss)
    y, x = np.mgrid[0:M[1], 0:M[0]].astype(np.float32)
    t = x / M[0]
    half = (0.06 + 0.42 * t) * M[1] / 2
    dy = np.abs(y - M[1] / 2)
    edge = 1 - smoothstep(half * 0.6, half, dy)
    a = edge * (1 - t) ** 1.2 * 200
    col = np.zeros((M[1], M[0], 4), np.float32)
    col[..., 0], col[..., 1], col[..., 2] = 255, 238, 170
    col[..., 3] = a
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA").resize((W, H), Image.LANCZOS)


def main():
    raw = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    for mood in MOODS:
        sea_tile(mood).save(os.path.join(OUT, f"sea_tile_{mood}.png"), optimize=True)
    gdir = os.path.join(raw, "env")
    os.makedirs(gdir, exist_ok=True)
    mp = os.path.join(gdir, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}

    def put(name, im, anchor=None, note=None):
        im.save(os.path.join(gdir, name + ".png"))
        meta[name] = dict(cell=list(im.size), anchor=list(anchor or (im.width / 2, im.height / 2)), pil=True, notrim=True)
        if note:
            meta[name]["note"] = note
    for i in range(4):
        put(f"foam_{i}", foam(i))
        put(f"wave_{i}", wave(i))
        put(f"fog_{i}", fog(i), note="draw with alpha 0.6-0.9, drift slowly")
    put("rain", rain(), note="particle; rotate ~10 deg, tint per mood")
    for i in range(3):
        put(f"rain_splash_{i}", rain_splash(i))
    put("lightning", lightning(3), anchor=(70, 0), note="anchor = top of the bolt; ADD blend, flash 120 ms")
    put("lightning_1", lightning(8), anchor=(70, 0))
    for i in range(4):
        put(f"whirlpool_{i}", whirlpool(i))
    put("whirlpool", whirlpool(0), note="same as whirlpool_0; anim whirlpool cycles 0..3")
    put("lighthouse_beam", beam(), anchor=(0, 85), note="anchor = lamp (left end); ADD blend; rotate to sweep")
    meta.setdefault("_anims", {})
    meta["_anims"]["whirlpool"] = {"frames": [f"whirlpool_{i}" for i in range(4)], "frameRate": 8, "repeat": -1}
    meta["_anims"]["wave"] = {"frames": [f"wave_{i}" for i in range(4)], "frameRate": 5, "repeat": -1, "yoyo": True}
    meta["_anims"]["rain_splash"] = {"frames": [f"rain_splash_{i}" for i in range(3)], "frameRate": 14, "repeat": 0}
    json.dump(meta, open(mp, "w"), indent=1)
    print("env pil ok")


main()
