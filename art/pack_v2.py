"""Pack v2 raw renders -> outlined, downsampled sheets + Phaser JSON.

python art/pack_v2.py characters <rawdir>   # rawdir/characters_v2/<name>/<anim>_<DIR>_<i>.png  (SSAA 4)
python art/pack_v2.py npcs <rawdir>         # rawdir/npcs/<name>/idle_<DIR>_<i>.png       (SSAA 4)
python art/pack_v2.py portraits <rawdir>    # rawdir/portraits/<name>_<expr>.png          (SSAA 2)
python art/pack_v2.py creatures <rawdir>    # rawdir/creatures/... (see pack_creatures)
"""
import json
import os
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
OUTLINE = (44, 26, 66)


def finish(path, ssaa=4, outline_px=1.0, out_size=None):
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A")
    r = max(1, int(round(outline_px * ssaa)))
    dil = a.point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(2 * r + 1))
    ol = Image.new("RGBA", im.size, OUTLINE + (0,))
    ol.putalpha(dil)
    comp = Image.alpha_composite(ol, im)
    w, h = im.size
    size = out_size or (w // ssaa, h // ssaa)
    return comp.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")


def save_png(img, path, colors=None, max_kb=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if colors:
        q = img.quantize(colors=colors, method=Image.FASTOCTREE, dither=Image.NONE)
        q.save(path, optimize=True)
    else:
        img.save(path, optimize=True)
    sz = os.path.getsize(path)
    if max_kb and sz > max_kb * 1024 and colors and colors > 64:
        return save_png(img, path, colors // 2, max_kb)
    return sz


def frame_rec(x, y, w, h, **extra):
    d = {"frame": {"x": x, "y": y, "w": w, "h": h}, "rotated": False, "trimmed": False,
         "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h}, "sourceSize": {"w": w, "h": h}}
    d.update(extra)
    return d


def pack_characters(rawdir):
    cell = 128
    base = os.path.join(rawdir, "characters_v2")
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        sheet = Image.new("RGBA", (8 * cell, 16 * cell), (0, 0, 0, 0))
        frames, anims, r = {}, {}, 0
        for anim, n in (("idle", 4), ("walk", 8)):
            for dn in DIRS:
                for i in range(n):
                    fp = os.path.join(d, f"{anim}_{dn}_{i}.png")
                    if not os.path.exists(fp):
                        continue
                    sheet.alpha_composite(finish(fp), (i * cell, r * cell))
                    frames[f"{anim}_{dn}_{i}"] = frame_rec(i * cell, r * cell, cell, cell)
                anims[f"{anim}_{dn}"] = {"frames": [f"{anim}_{dn}_{i}" for i in range(n)],
                                         "frameRate": 6 if anim == "idle" else 10, "repeat": -1}
                r += 1
        out = os.path.join(OUT, "characters_v2", name + ".png")
        sz = save_png(sheet, out, colors=256)
        meta = {"frames": frames,
                "meta": {"app": "too-quiet art pipeline v2", "version": "2.0", "image": name + ".png", "format": "RGBA8888",
                         "size": {"w": sheet.width, "h": sheet.height}, "scale": "1", "origin": {"x": 0.5, "y": 110 / 128},
                         "note": "Same layout as v1: rows 0-7 idle (4 frames, frame 3 = blink) S SW W NW N NE E SE, "
                                 "rows 8-15 walk (8). Ground contact (64,110): setOrigin(0.5, 0.859)."},
                "anims": anims}
        with open(os.path.join(OUT, "characters_v2", name + ".json"), "w") as f:
            json.dump(meta, f, indent=1)
        print(f"{name}: {len(frames)} frames, {sz / 1024:.0f} KB")


NPC_DIRS = ["S", "SE", "E", "SW", "W"]


def pack_npcs(rawdir):
    cell = 128
    base = os.path.join(rawdir, "npcs")
    names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
    # one sheet per NPC (4 cols x 5 rows) + one combined JSON index
    index = {}
    for name in names:
        d = os.path.join(base, name)
        sheet = Image.new("RGBA", (4 * cell, 5 * cell), (0, 0, 0, 0))
        frames, anims = {}, {}
        for r, dn in enumerate(NPC_DIRS):
            for i in range(4):
                fp = os.path.join(d, f"idle_{dn}_{i}.png")
                if os.path.exists(fp):
                    sheet.alpha_composite(finish(fp), (i * cell, r * cell))
                    frames[f"idle_{dn}_{i}"] = frame_rec(i * cell, r * cell, cell, cell)
            anims[f"idle_{dn}"] = {"frames": [f"idle_{dn}_{i}" for i in range(4)], "frameRate": 5, "repeat": -1}
        out = os.path.join(OUT, "characters_v2", "npcs", name + ".png")
        sz = save_png(sheet, out, colors=128, max_kb=120)
        meta = {"frames": frames, "anims": anims,
                "meta": {"app": "too-quiet art pipeline v2", "image": name + ".png", "size": {"w": sheet.width, "h": sheet.height},
                         "scale": "1", "origin": {"x": 0.5, "y": 110 / 128},
                         "mirror": {"NE": "SE flipX", "NW": "SW flipX", "N": "use S/SE"},
                         "note": "Idle only, frame 3 = blink. Rows: S, SE, E, SW, W. Ground contact (64,110)."}}
        with open(os.path.join(OUT, "characters_v2", "npcs", name + ".json"), "w") as f:
            json.dump(meta, f, indent=1)
        index[name] = {"image": name + ".png", "json": name + ".json", "kb": round(sz / 1024)}
        print(f"npc {name}: {sz / 1024:.0f} KB")
    with open(os.path.join(OUT, "characters_v2", "npcs", "index.json"), "w") as f:
        json.dump(index, f, indent=1)


def pack_portraits(rawdir):
    base = os.path.join(rawdir, "portraits")
    files = sorted(f for f in os.listdir(base) if f.endswith(".png"))
    by = {}
    for f in files:
        stem = f[:-4]
        # name_expr, the name itself may contain underscores: expression is the last token
        nm, ex = stem.rsplit("_", 1)
        by.setdefault(nm, []).append(ex)
    order = ['neutral', 'happy', 'worried', 'surprised', 'sad', 'blink', 'truth', 'diary']
    cell = 512
    index = {}
    for nm, exs in sorted(by.items()):
        exs = sorted(exs, key=lambda e: order.index(e) if e in order else 99)
        cols = min(4, len(exs))
        rows = (len(exs) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
        frames = {}
        if nm == "noam" and "neutral" in exs and "diary" not in exs:
            exs.append("diary")
        for k, ex in enumerate(exs):
            src = os.path.join(base, f"{nm}_{'neutral' if ex == 'diary' else ex}.png")
            im = finish(src, ssaa=2, outline_px=1.5, out_size=(cell, cell))
            if ex == "diary":   # sepia ink-wash look for the diary page
                from PIL import ImageOps, ImageEnhance
                a0 = im.getchannel("A")
                g = ImageOps.grayscale(im.convert("RGB"))
                g = ImageEnhance.Contrast(g).enhance(1.25)
                im = ImageOps.colorize(g, black=(58, 36, 24), mid=(150, 112, 72), white=(244, 226, 190)).convert("RGBA")
                im.putalpha(a0)
            # soft fade at the bottom edge of the bust
            a = im.getchannel("A")
            fade = Image.linear_gradient("L").resize((cell, cell))
            fade = fade.point(lambda v: 255 if v < 215 else int(255 * (255 - v) / 40))
            im.putalpha(Image.composite(a, Image.new("L", a.size, 0), fade))
            x, y = (k % cols) * cell, (k // cols) * cell
            sheet.alpha_composite(im, (x, y))
            frames[f"{nm}_{ex}"] = frame_rec(x, y, cell, cell)
        out = os.path.join(OUT, "portraits", nm + ".png")
        sz = save_png(sheet, out)
        if sz > 900 * 1024:
            sz = save_png(sheet, out, colors=256)
        with open(os.path.join(OUT, "portraits", nm + ".json"), "w") as f:
            json.dump({"frames": frames, "meta": {"app": "too-quiet art pipeline v2", "image": nm + ".png",
                                                  "size": {"w": sheet.width, "h": sheet.height}, "scale": "1",
                                                  "facing": "body turned ~25 deg to the viewer's left; flipX to face right",
                                                  "note": "<name>_blink = neutral with closed eyes (swap for 120 ms)"}},
                      f, indent=1)
        index[nm] = exs
        print(f"portrait {nm}: {exs} {sz / 1024:.0f} KB")
    with open(os.path.join(OUT, "portraits", "index.json"), "w") as f:
        json.dump(index, f, indent=1)


CDIRS = ["S", "SE", "E", "N"]


def pack_creatures(rawdir):
    base = os.path.join(rawdir, "creatures")
    od = os.path.join(OUT, "creatures")
    names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
    index = {}
    codex = []
    for nm in names:
        d = os.path.join(base, nm)
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf8"))
        legendary = meta.get("legendary", False)
        frames, anims = {}, {}
        if not legendary:
            cell = 128
            sheet = Image.new("RGBA", (6 * cell, 8 * cell), (0, 0, 0, 0))
            r = 0
            for anim, n in (("idle", 4), ("walk", 6)):
                for dn in CDIRS:
                    for i in range(n):
                        fp = os.path.join(d, f"{anim}_{dn}_{i}.png")
                        sheet.alpha_composite(finish(fp), (i * cell, r * cell))
                        frames[f"{anim}_{dn}_{i}"] = frame_rec(i * cell, r * cell, cell, cell)
                    anims[f"{anim}_{dn}"] = {"frames": [f"{anim}_{dn}_{i}" for i in range(n)],
                                             "frameRate": 5 if anim == "idle" else 9, "repeat": -1}
                    r += 1
            info = {"cell": [cell, cell], "origin": {"x": 0.5, "y": 110 / 128}, "world_scale": 0.667,
                    "directions": CDIRS, "mirror": {"W": "E flipX", "SW": "SE flipX", "NE": "E or N", "NW": "W or N"},
                    "note": "Rendered at 1.5x world scale for readability: setScale(0.667) for exact world size. "
                            "Ground contact (64,110); flyers hover above it (draw the blob shadow at the origin)."}
        else:
            src = Image.open(os.path.join(d, "idle_S_0.png"))
            cw, ch = src.width // 3, src.height // 3
            sheet = Image.new("RGBA", (4 * cw, ch), (0, 0, 0, 0))
            for i in range(4):
                sheet.alpha_composite(finish(os.path.join(d, f"idle_S_{i}.png"), ssaa=3, outline_px=1.2), (i * cw, 0))
                frames[f"idle_{i}"] = frame_rec(i * cw, 0, cw, ch)
            anims["idle"] = {"frames": [f"idle_{i}" for i in range(4)], "frameRate": 3, "repeat": -1, "yoyo": True}
            anc = {"thread_serpent": (192, 360), "cloud_whale": (192, 240), "echo_giant": (128, 360)}.get(nm, (cw / 2, ch - 20))
            info = {"cell": [cw, ch], "origin": {"x": anc[0] / cw, "y": anc[1] / ch}, "world_scale": 1.0,
                    "note": "Legendary: one facing, idle only (yoyo). origin = ground point under it (whale: point under its belly)."}
        sz = save_png(sheet, os.path.join(od, nm + ".png"), colors=None if legendary else 192, max_kb=200)
        out = {"frames": frames, "anims": anims,
               "meta": dict(info, app="too-quiet art pipeline v2", image=nm + ".png", size={"w": sheet.width, "h": sheet.height},
                            scale="1", name_he=meta.get("name_he"), concept_he=meta.get("concept"),
                            legend_he=meta.get("legend"), movement=meta.get("move"), legendary=legendary,
                            codex={"atlas": "codex.png", "frame": nm})}
        with open(os.path.join(od, nm + ".json"), "w", encoding="utf8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        codex.append((nm, finish(os.path.join(d, f"{nm}_codex.png"), ssaa=2, outline_px=1.0)))
        index[nm] = {"name_he": meta.get("name_he"), "concept_he": meta.get("concept"), "legend_he": meta.get("legend"),
                     "legendary": legendary, "kb": round(sz / 1024)}
        print(f"creature {nm}: {sz / 1024:.0f} KB")
    cols = 4
    rows = (len(codex) + cols - 1) // cols
    cs = Image.new("RGBA", (cols * 256, rows * 256), (0, 0, 0, 0))
    cf = {}
    for k, (nm, im) in enumerate(codex):
        x, y = (k % cols) * 256, (k // cols) * 256
        cs.alpha_composite(im, (x, y))
        cf[nm] = frame_rec(x, y, 256, 256)
    sz = save_png(cs, os.path.join(od, "codex.png"))
    with open(os.path.join(od, "codex.json"), "w") as f:
        json.dump({"frames": cf, "meta": {"image": "codex.png", "size": {"w": cs.width, "h": cs.height}, "scale": "1",
                                          "note": "256x256 3/4 collection-card renders, transparent"}}, f, indent=1)
    with open(os.path.join(od, "index.json"), "w", encoding="utf8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"codex: {sz / 1024:.0f} KB")


def pack_head(rawdir):
    R = os.path.join(rawdir, "head")
    sheet = Image.new("RGBA", (2048, 1024), (0, 0, 0, 0))
    fr = {}
    for r, v in enumerate(("benevolent", "truth")):
        for i in range(2):
            sheet.alpha_composite(finish(os.path.join(R, f"the_head_{v}_{i}.png"), ssaa=2, outline_px=1.5), (i * 1024, r * 512))
            fr[f"the_head_{v}_{i}"] = frame_rec(i * 1024, r * 512, 1024, 512)
    od = os.path.join(OUT, "creatures")
    sz = save_png(sheet, os.path.join(od, "the_head.png"), colors=256)
    anims = {v: {"frames": [f"the_head_{v}_0", f"the_head_{v}_1"], "frameRate": 0.5, "repeat": -1, "yoyo": True}
             for v in ("benevolent", "truth")}
    meta = {"image": "the_head.png", "size": {"w": 2048, "h": 1024}, "scale": "1", "name_he": "הראש", "origin": {"x": 0.5, "y": 0.5},
            "legend_he": "הראש הגדול מציץ מבין העננים ומחזיק בקצות אצבעותיו חוטי אור. מלמטה הוא נראה רגוע וטוב. "
                         "מי שרואה בראיית חוטים מגלה שהחוטים יורדים אל כל אנשי העמק.",
            "note": "Sky element, 1024x512 per frame. Frame 1 = slow half-blink. Row 0 benevolent facade, "
                    "row 1 colder truth (thread sight). Strings run off the bottom edge: place it so they reach the village."}
    with open(os.path.join(od, "the_head.json"), "w", encoding="utf8") as f:
        json.dump({"frames": fr, "anims": anims, "meta": meta}, f, ensure_ascii=False, indent=1)
    print(f"the_head: {sz / 1024:.0f} KB")


if __name__ == "__main__":
    what, raw = sys.argv[1], sys.argv[2]
    dict(characters=pack_characters, npcs=pack_npcs, portraits=pack_portraits, creatures=pack_creatures,
         head=pack_head)[what](raw)
