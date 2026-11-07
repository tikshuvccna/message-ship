"""Pack raw Blender renders (+ Pillow-made frames) into one Phaser "JSON hash" atlas.

python art/pack_atlas.py <group> <ABS rawdir> [--max 2048]
Reads <rawdir>/<group>/meta.json: {frame: {cell:[w,h], anchor:[x,y] (1x px), ssaa, ...extra}}.
Each raw PNG is outlined (1 px dark violet, done at 4x) and downscaled, trimmed, shelf-packed.
Frame JSON: frame/spriteSourceSize/sourceSize (untrimmed size kept as sourceSize? no: frames are trimmed and the
anchor is re-expressed in the trimmed frame), plus `anchor` {x,y} normalised (setOrigin) and `anchorPx`.
Extra keys from meta (slotsPx, pivotPx, topPx, ...) are copied as-is (px relative to the anchor).
Frames whose meta has "pil": true are already 1x finished images (no outline/downscale).
"""
import json
import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
OUTLINE = (44, 26, 66)
DEST = {"ship": "ship/ship", "creatures": "creatures/creatures", "env": "env/env", "kraken": "creatures/kraken",
        "cast": "characters/cast_props"}


def finish(path, ssaa=4, outline_px=1.0, thr=24, outline=True):
    im = Image.open(path).convert("RGBA")
    if outline:
        a = im.getchannel("A")
        r = int(round(outline_px * ssaa))
        dil = a.point(lambda v: 255 if v > thr else 0).filter(ImageFilter.MaxFilter(2 * r + 1))
        ol = Image.new("RGBA", im.size, OUTLINE + (0,))
        ol.putalpha(dil)
        im = Image.alpha_composite(ol, im)
    w, h = im.size
    if ssaa != 1:
        im = im.convert("RGBa").resize((w // ssaa, h // ssaa), Image.LANCZOS).convert("RGBA")
    return im


def shadow_blob(size, center, rx, ry, alpha=0.32, blur=3):
    """Soft contact shadow ellipse (1x px)."""
    from PIL import ImageDraw
    sh = Image.new("L", size, 0)
    d = ImageDraw.Draw(sh)
    cx, cy = center
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=int(255 * alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    img = Image.new("RGBA", size, (40, 30, 70, 0))
    img.putalpha(sh)
    return img


_FONTS = {}


def _font(size):
    from PIL import ImageFont
    if size not in _FONTS:
        try:
            _FONTS[size] = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", size)
        except Exception:
            _FONTS[size] = ImageFont.load_default()
    return _FONTS[size]


def glitch(im, seed, frame):
    """'Noise' look: RGB split, a few sliced bands shifted sideways, letters flaking off the silhouette."""
    import random
    from PIL import ImageChops, ImageDraw
    rnd = random.Random(seed * 7 + 1)
    w, h = im.size
    r, g, b, a = im.split()
    sh = 2
    r = ImageChops.offset(r, -sh, 0)
    b = ImageChops.offset(b, sh, 0)
    ar = ImageChops.offset(a, -sh, 0)
    ab = ImageChops.offset(a, sh, 0)
    a2 = ImageChops.lighter(a, ImageChops.lighter(ar, ab))
    out = Image.merge("RGBA", (r, g, b, a2))
    # sliced bands (different per frame)
    rf = random.Random(seed * 13 + frame * 101)
    bb = a.getbbox() or (0, 0, w, h)
    for _ in range(3):
        y0 = rf.randint(bb[1], max(bb[1] + 1, bb[3] - 4))
        hh = rf.randint(2, 5)
        dx = rf.choice((-5, -4, -3, 3, 4, 6))
        band = out.crop((0, y0, w, y0 + hh))
        out.paste((0, 0, 0, 0), (0, y0, w, y0 + hh))
        out.alpha_composite(band, (dx, y0)) if 0 <= dx else out.alpha_composite(band.crop((-dx, 0, w, hh)), (0, y0))
    # flaking letters: start on the upper silhouette, drift up/out between the frames
    d = ImageDraw.Draw(out)
    chars = "AZQ#?%&7@$kxRG01"
    cx = (bb[0] + bb[2]) / 2
    n = 5 + rnd.randint(0, 3)
    for i in range(n):
        x = rnd.uniform(bb[0], bb[2])
        y = bb[1] + rnd.uniform(0, (bb[3] - bb[1]) * 0.5)
        drift = 6 + 7 * ((frame + i * 0.37) % 1.0) + frame * 5
        x += (x - cx) * 0.12 + rnd.uniform(-3, 3)
        y -= drift
        sz = rnd.randint(9, 14)
        col = rnd.choice(((255, 122, 58), (255, 170, 80), (150, 120, 190), (220, 80, 60)))
        al = int(255 * (0.95 - 0.35 * frame - 0.25 * ((i * 0.37) % 1.0)))
        ch = rnd.choice(chars)
        d.text((x + 1, y + 1), ch, font=_font(sz), fill=(30, 18, 40, al))
        d.text((x, y), ch, font=_font(sz), fill=col + (al,))
    return out


def load_frame(gdir, name, m):
    p = os.path.join(gdir, m.get("file", name + ".png"))
    if m.get("pil"):
        im = Image.open(p).convert("RGBA")
    else:
        im = finish(p, ssaa=m.get("ssaa", 4), outline=m.get("outline", True))
    if m.get("glitch") is not None:
        im = glitch(im, m["glitch"][0], m["glitch"][1])
    if m.get("shadow"):
        rx, ry = m["shadow"][:2]
        dx = m["shadow"][2] if len(m["shadow"]) > 2 else 0
        al = m["shadow"][3] if len(m["shadow"]) > 3 else 0.3
        ax, ay = m["anchor"]
        sh = shadow_blob(im.size, (ax + dx, ay), rx, ry, alpha=al)
        im = Image.alpha_composite(sh, im)
    return im


def trim(im, pad=1):
    bb = im.getchannel("A").point(lambda v: 255 if v > 2 else 0).getbbox()
    if not bb:
        return im.crop((0, 0, 2, 2)), (0, 0)
    x0, y0, x1, y1 = max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)
    return im.crop((x0, y0, x1, y1)), (x0, y0)


def pack(group, rawdir, maxw=2048, dest=None, order=None):
    gdir = os.path.join(rawdir, group)
    meta = json.load(open(os.path.join(gdir, "meta.json")))
    items = []
    names = order or [n for n in meta if not n.startswith("_")]
    for nm in names:
        m = meta[nm]
        im = load_frame(gdir, nm, m)
        if m.get("notrim"):
            off = (0, 0)
        else:
            im, off = trim(im)
        ax, ay = m["anchor"][0] - off[0], m["anchor"][1] - off[1]
        items.append((nm, im, (ax, ay), m))
    # shelf pack, tallest first
    items_sorted = sorted(items, key=lambda t: -t[1].height)
    x = y = rowh = 0
    pos = {}
    W = maxw
    for nm, im, a, m in items_sorted:
        w, h = im.size
        if x + w > W:
            x, y, rowh = 0, y + rowh + 2, 0
        pos[nm] = (x, y)
        x += w + 2
        rowh = max(rowh, h)
    H = y + rowh
    used_w = max(pos[n][0] + im.width for n, im, a, m in items)
    sheet = Image.new("RGBA", (used_w, H), (0, 0, 0, 0))
    frames = {}
    skip = {"cell", "anchor", "ssaa", "file", "pil", "outline", "shadow", "notrim", "glitch"}
    for nm, im, (ax, ay), m in items:
        px, py = pos[nm]
        sheet.alpha_composite(im, (px, py))
        rec = {"frame": {"x": px, "y": py, "w": im.width, "h": im.height}, "rotated": False, "trimmed": False,
               "spriteSourceSize": {"x": 0, "y": 0, "w": im.width, "h": im.height},
               "sourceSize": {"w": im.width, "h": im.height},
               "anchor": {"x": round(ax / im.width, 5), "y": round(ay / im.height, 5)},
               "anchorPx": {"x": ax, "y": ay}}
        for k, v in m.items():
            if k not in skip:
                rec[k] = v
        frames[nm] = rec
    dest = dest or DEST.get(group, group + "/" + group)
    out_png = os.path.join(OUT, dest + ".png")
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png, optimize=True)
    kb = os.path.getsize(out_png) / 1024
    if kb > 3000:
        q = sheet.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)
        q.save(out_png, optimize=True)
        kb = os.path.getsize(out_png) / 1024
        print("  quantised")
    anims = meta.get("_anims", {})
    js = {"frames": frames,
          "meta": {"app": "message-ship art pipeline", "version": "1.0", "image": os.path.basename(out_png),
                   "format": "RGBA8888", "size": {"w": sheet.width, "h": sheet.height}, "scale": "1",
                   "note": "frames[*].anchor = ground point (normalised): setOrigin(anchor.x, anchor.y). "
                           "Projection: sx = x*56, sy = -y*32.12 - z*45.87 (ortho 35 deg)."},
          }
    if anims:
        js["anims"] = anims
    if "_meta" in meta:
        js["meta"].update(meta["_meta"])
    with open(os.path.join(OUT, dest + ".json"), "w", encoding="utf-8") as f:
        json.dump(js, f, indent=1, ensure_ascii=False)
    print(f"{dest}: {len(frames)} frames, {sheet.width}x{sheet.height}, {kb:.0f} KB")
    return frames


if __name__ == "__main__":
    g, raw = sys.argv[1], sys.argv[2]
    mw = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 2048
    pack(g, raw, mw)


