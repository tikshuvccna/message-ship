"""Post-process raw Blender frames -> outlined, anti-aliased sprite sheets + Phaser JSON.

python art/pack.py characters <rawdir>      # raw/<char>/<anim>_<DIR>_<i>.png
python art/pack.py props <rawdir>           # raw/props/<name>.png  (+ raw/props/props_meta.json)
Needs Pillow. Outline: 1 px dark violet around the silhouette (done at 4x then downsampled).
"""
import json
import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
OUTLINE = (44, 26, 66)


def finish(path, ssaa=4, outline_px=1.0, thr=24):
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A")
    # binarise-ish alpha so the dilation is crisp, then dilate by outline_px (at final res)
    r = int(round(outline_px * ssaa))
    size = 2 * r + 1
    dil = a.point(lambda v: 255 if v > thr else 0).filter(ImageFilter.MaxFilter(size))
    ol = Image.new("RGBA", im.size, OUTLINE + (0,))
    ol.putalpha(dil)
    comp = Image.alpha_composite(ol, im)
    w, h = im.size
    small = comp.convert("RGBa").resize((w // ssaa, h // ssaa), Image.LANCZOS).convert("RGBA")
    return small


def save_png(img, path, colors=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    sz = os.path.getsize(path)
    if colors and sz > 1.5 * 1024 * 1024:
        q = img.quantize(colors=colors, method=Image.FASTOCTREE, dither=Image.NONE)
        q.save(path, optimize=True)
        sz = os.path.getsize(path)
        print("  (quantised to", colors, "colours)")
    return sz


def pack_characters(rawdir):
    cell = 128
    for name in sorted(os.listdir(rawdir)):
        d = os.path.join(rawdir, name)
        if not os.path.isdir(d) or name == "props":
            continue
        rows = [("idle", 4), ("walk", 8)]
        cols = 8
        sheet = Image.new("RGBA", (cols * cell, 16 * cell), (0, 0, 0, 0))
        frames = {}
        r = 0
        anims = {}
        for anim, n in rows:
            for dn in DIRS:
                for i in range(n):
                    fp = os.path.join(d, f"{anim}_{dn}_{i}.png")
                    if not os.path.exists(fp):
                        continue
                    im = finish(fp)
                    x, y = i * cell, r * cell
                    sheet.alpha_composite(im, (x, y))
                    fn = f"{anim}_{dn}_{i}"
                    frames[fn] = {"frame": {"x": x, "y": y, "w": cell, "h": cell}, "rotated": False, "trimmed": False,
                                  "spriteSourceSize": {"x": 0, "y": 0, "w": cell, "h": cell},
                                  "sourceSize": {"w": cell, "h": cell}}
                anims[f"{anim}_{dn}"] = {"frames": [f"{anim}_{dn}_{i}" for i in range(n)],
                                         "frameRate": 6 if anim == "idle" else 10, "repeat": -1}
                r += 1
        sheet = sheet.crop((0, 0, cols * cell, r * cell))
        out = os.path.join(OUT, "characters", name + ".png")
        sz = save_png(sheet, out, colors=256)
        meta = {"frames": frames,
                "meta": {"app": "too-quiet art pipeline", "version": "1.0", "image": name + ".png", "format": "RGBA8888",
                         "size": {"w": sheet.width, "h": sheet.height}, "scale": "1",
                         "origin": {"x": 0.5, "y": 110 / 128},
                         "note": "ground contact at (64,110) of each 128px frame; use setOrigin(0.5, 0.859)"},
                "anims": anims}
        with open(os.path.join(OUT, "characters", name + ".json"), "w") as f:
            json.dump(meta, f, indent=1)
        print(f"{name}: {len(frames)} frames, sheet {sheet.size}, {sz / 1024:.0f} KB")


def pack_props(rawdir):
    pdir = os.path.join(rawdir, "props")
    meta = json.load(open(os.path.join(pdir, "props_meta.json")))
    items = []
    for nm, m in meta.items():
        items.append((nm, finish(os.path.join(pdir, nm + ".png")), m))
    # shelf pack, max width 1536
    W = 1536
    x = y = rowh = 0
    pos = {}
    for nm, im, m in items:
        w, h = im.size
        if x + w > W:
            x, y, rowh = 0, y + rowh, 0
        pos[nm] = (x, y)
        x += w
        rowh = max(rowh, h)
    H = y + rowh
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frames = {}
    for nm, im, m in items:
        px, py = pos[nm]
        sheet.alpha_composite(im, (px, py))
        frames[nm] = {"frame": {"x": px, "y": py, "w": im.width, "h": im.height}, "rotated": False, "trimmed": False,
                      "spriteSourceSize": {"x": 0, "y": 0, "w": im.width, "h": im.height},
                      "sourceSize": {"w": im.width, "h": im.height},
                      "anchor": {"x": m["anchor"][0] / im.width, "y": m["anchor"][1] / im.height}}
    out = os.path.join(OUT, "props", "props.png")
    sz = save_png(sheet, out, colors=256)
    with open(os.path.join(OUT, "props", "props.json"), "w") as f:
        json.dump({"frames": frames, "meta": {"app": "too-quiet art pipeline", "version": "1.0", "image": "props.png",
                                              "format": "RGBA8888", "size": {"w": W, "h": H}, "scale": "1",
                                              "note": "frames[*].anchor = ground contact point (normalised) -> setOrigin(anchor.x, anchor.y)"}},
                  f, indent=1)
    print(f"props: {len(frames)} frames, sheet {W}x{H}, {sz / 1024:.0f} KB")


if __name__ == "__main__":
    what, raw = sys.argv[1], sys.argv[2]
    if what == "characters":
        pack_characters(raw)
    elif what == "props":
        pack_props(raw)
