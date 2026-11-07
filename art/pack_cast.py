"""Pack cast renders.
python art/pack_cast.py portraits <ABS rawdir>  -> public/assets/portraits/<who>_<mood>.png (512x512) + index.json
python art/pack_cast.py sprites <ABS rawdir> [name ...] -> public/assets/characters/<name>.png|json (game-1 layout)
Also writes art/preview_portraits.png / art/preview_cast.png.
"""
import json
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack_atlas import finish

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
EXPRS = ['neutral', 'happy', 'worried', 'surprised']
WHO = ['naama', 'bit', 'uri', 'talia', 'barak', 'hero_girl', 'hero_boy']
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]


def portraits(raw):
    base = os.path.join(raw, "portraits")
    od = os.path.join(OUT, "portraits")
    os.makedirs(od, exist_ok=True)
    index = {}
    sheet = Image.new("RGBA", (4 * 256, len(WHO) * 256), (236, 226, 204, 255))
    for r, who in enumerate(WHO):
        for c, e in enumerate(EXPRS):
            p = os.path.join(base, f"{who}_{e}.png")
            if not os.path.exists(p):
                continue
            im = finish(p, ssaa=2, outline_px=1.5)
            if who != 'bit':   # soft fade at the bottom edge of the bust
                a = im.getchannel("A")
                fade = Image.linear_gradient("L").resize(im.size)
                fade = fade.point(lambda v: 255 if v < 215 else int(255 * (255 - v) / 40))
                im.putalpha(Image.composite(a, Image.new("L", a.size, 0), fade))
            im.save(os.path.join(od, f"{who}_{e}.png"), optimize=True)
            index.setdefault(who, []).append(e)
            sheet.alpha_composite(im.resize((256, 256), Image.LANCZOS), (c * 256, r * 256))
    with open(os.path.join(od, "index.json"), "w") as f:
        json.dump({"moods": EXPRS, "who": index,
                   "note": "512x512 transparent busts, body turned ~24 deg to the viewer's left (flipX to face right)"}, f, indent=1)
    sheet.save(os.path.join(ROOT, "art", "preview_portraits.png"))
    print("portraits:", {k: len(v) for k, v in index.items()})


def sprites(raw, names):
    cell = 128
    base = os.path.join(raw, "characters")
    od = os.path.join(OUT, "characters")
    os.makedirs(od, exist_ok=True)
    for name in names or sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        frames, anims = {}, {}
        if name == 'bit':
            sheet = Image.new("RGBA", (4 * cell, cell), (0, 0, 0, 0))
            for i in range(4):
                sheet.alpha_composite(finish(os.path.join(d, f"float_{i}.png")), (i * cell, 0))
                frames[f"float_{i}"] = {"frame": {"x": i * cell, "y": 0, "w": cell, "h": cell}, "rotated": False,
                                        "trimmed": False, "spriteSourceSize": {"x": 0, "y": 0, "w": cell, "h": cell},
                                        "sourceSize": {"w": cell, "h": cell}}
            anims["float"] = {"frames": [f"float_{i}" for i in range(4)], "frameRate": 6, "repeat": -1}
            note = "Bit hovers ~1.25 units above the ground point (64,110); frame 2 smiles. Add lantern_glow (ADD) behind."
        else:
            sheet = Image.new("RGBA", (8 * cell, 16 * cell), (0, 0, 0, 0))
            r = 0
            for anim, n in (("idle", 4), ("walk", 8)):
                for dn in DIRS:
                    for i in range(n):
                        fp = os.path.join(d, f"{anim}_{dn}_{i}.png")
                        if os.path.exists(fp):
                            sheet.alpha_composite(finish(fp), (i * cell, r * cell))
                            frames[f"{anim}_{dn}_{i}"] = {"frame": {"x": i * cell, "y": r * cell, "w": cell, "h": cell},
                                                          "rotated": False, "trimmed": False,
                                                          "spriteSourceSize": {"x": 0, "y": 0, "w": cell, "h": cell},
                                                          "sourceSize": {"w": cell, "h": cell}}
                    anims[f"{anim}_{dn}"] = {"frames": [f"{anim}_{dn}_{i}" for i in range(n)],
                                             "frameRate": 6 if anim == "idle" else 10, "repeat": -1}
                    r += 1
            note = ("Same layout as game 1: rows 0-7 idle (4, frame 3 = blink) S SW W NW N NE E SE, rows 8-15 walk (8). "
                    "Ground contact (64,110): setOrigin(0.5, 0.859).")
        out = os.path.join(od, name + ".png")
        q = sheet.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)
        q.save(out, optimize=True)
        with open(os.path.join(od, name + ".json"), "w") as f:
            json.dump({"frames": frames, "anims": anims,
                       "meta": {"app": "message-ship art pipeline", "image": name + ".png",
                                "size": {"w": sheet.width, "h": sheet.height}, "scale": "1",
                                "origin": {"x": 0.5, "y": 110 / 128}, "note": note}}, f, indent=1)
        print(name, len(frames), "frames", os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    what, raw = sys.argv[1], sys.argv[2]
    if what == "portraits":
        portraits(raw)
    else:
        sprites(raw, sys.argv[3:])
