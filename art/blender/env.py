"""Sea environment props (Blender): islands, reefs, lighthouse (unlit/lit), pier, buoy, bottle, floating crate, coves.

blender -b --python art/blender/env.py -- <ABS rawdir> [name ...]
Same oblique camera (35 deg, 56 px/unit). Water level z = 0; every prop gets a toon foam ring at the waterline.
Anchor = the prop's centre on the water surface. Pack: art/pack_atlas.py env <rawdir> (Pillow parts: art/env_pil.py).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

from v2lib import *
from shiplib import Job, ring_tube, wood, brass, iron, rope_mat, proj, lantern, spiral_coil

SAND = "#f0d69a"
GRASS = "#6cbf5a"
ROCK = "#9a8e9e"


def foam_ring(rx, ry, z=0.02, seed=1, w=0.12):
    rnd = random.Random(seed)
    pts = []
    n = 48
    for i in range(n + 1):
        a = TAU * i / n
        k = 1 + 0.06 * math.sin(a * 5 + seed) + 0.03 * math.sin(a * 11)
        pts.append(Vector((rx * k * math.cos(a), ry * k * math.sin(a), z)))
    tube("foam", pts, [w], mat("#f4fbff", kind='flat', rim=0.0, ao=0.0), seg=6, sub=1, line=False).scale = (1, 1, 0.35)
    # a few foam blobs
    for i in range(8):
        a = rnd.uniform(0, TAU)
        ellipsoid("fb", rnd.uniform(0.08, 0.16), mat("#ffffff", kind='flat', rim=0.0, ao=0.0),
                  loc=(rx * 1.08 * math.cos(a), ry * 1.08 * math.sin(a), z), scale=(1.4, 1, 0.3), line=False)


def rock(name, r, loc, seed, color=ROCK, moss=True, sq=0.8):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6) for _ in range(4)]
    def deform(p):
        k = 1 + 0.18 * math.sin(p.x * 3 + ph[0]) * math.sin(p.y * 3 + ph[1]) + 0.1 * math.sin(p.z * 5 + ph[2])
        q = Vector((p.x * k, p.y * k, p.z * k))
        # facet: quantise slightly for a chunky stylised rock
        return Vector((q.x, q.y, max(q.z, -0.3)))
    m = mat(color, kind='soft', rim=0.5, pat='patches' if moss else 'noise', color2="#7ab04a" if moss else None,
            P=dict(scale=3, thr=0.68, sharp=8) if moss else dict(scale=6), var=0.12)
    return blob(name, r, m, loc=loc, scale=(1, 0.9, sq), deform=deform, seg=20, rings=14)


def palm(loc, h=2.2, lean=0.4, seed=0):
    rnd = random.Random(seed)
    x, y, z = loc
    pts = [Vector((x, y, z)), Vector((x + lean * 0.3, y, z + h * 0.5)), Vector((x + lean, y, z + h))]
    tube("trunk", pts, [0.14, 0.1, 0.08], mat("#a87a4a", pat='stripes', color2="#7a5232", P=dict(fv=7, thr=0.6, weave=False),
                                             kind='soft', rim=0.5), seg=10, sub=5)
    top = pts[-1]
    for k in range(7):
        a = TAU * k / 7 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.85, 1.1)
        lp = [top, top + Vector((math.cos(a) * 0.5 * L, math.sin(a) * 0.5 * L, 0.22)),
              top + Vector((math.cos(a) * 1.0 * L, math.sin(a) * 1.0 * L, -0.25))]
        tube("leaf", lp, [0.05, 0.17, 0.03], mat("#4fae5a" if k % 2 else "#6cc85e", kind='soft', rim=0.6), seg=8, sub=4, flat=0.25,
             twist_up=(0, 0, 1))
    for k in range(3):
        a = TAU * k / 3
        ellipsoid("coco", 0.09, mat("#7a5232", kind='soft'), loc=top + Vector((0.1 * math.cos(a), 0.1 * math.sin(a), -0.1)))


def bush(loc, r=0.35, col="#5aae4a", seed=0):
    rnd = random.Random(seed)
    for i in range(3):
        ellipsoid("bush", r * rnd.uniform(0.7, 1.0), mat(col, kind='soft', rim=0.6, pat='noise', P=dict(scale=12), var=0.12),
                  loc=Vector(loc) + Vector((rnd.uniform(-r, r) * 0.6, rnd.uniform(-r, r) * 0.4, r * 0.5)), scale=(1, 1, 0.8))


def sand_mound(rx, ry, h, seed=0, col=SAND):
    blob("sand", 1.0, mat(col, kind='soft', rim=0.4, pat='noise', P=dict(scale=20), var=0.08), loc=(0, 0, -0.05),
         scale=(rx, ry, h), deform=lambda p: Vector((p.x * (1 + 0.06 * math.sin(p.y * 4 + seed)), p.y, max(p.z, 0.0))))


def grass_cap(rx, ry, h, z, seed=0):
    blob("grass", 1.0, mat(GRASS, kind='soft', rim=0.5, pat='patches', color2="#8ad36a", P=dict(scale=4, thr=0.5), var=0.1),
         loc=(0, 0.1, z), scale=(rx, ry, h), deform=lambda p: Vector((p.x * (1 + 0.08 * math.sin(p.y * 5 + seed)), p.y, max(p.z, 0.0))))


# ------------------------------------------------------------------ islands
def island_a():   # sandy palm island
    sand_mound(2.4, 1.8, 0.55)
    grass_cap(1.4, 1.1, 0.45, 0.3, 1)
    palm((-0.4, 0.3, 0.6), 2.4, 0.5, 1)
    palm((0.6, 0.6, 0.55), 1.9, -0.4, 2)
    rock("r1", 0.45, (1.6, -0.6, 0.1), 3)
    rock("r2", 0.3, (-1.7, -0.4, 0.05), 4)
    bush((0.3, -0.5, 0.45), 0.3, seed=2)
    foam_ring(2.45, 1.85, seed=1)


def island_b():   # rocky hill with a tiny mail hut and flag
    sand_mound(2.6, 2.0, 0.4, 2)
    rock("hill", 1.6, (0, 0.3, 0.2), 7, sq=0.9)
    grass_cap(1.5, 1.3, 0.6, 1.0, 2)
    hut = Vector((0.3, 0.2, 1.45))
    box("hutw", (0.9, 0.75, 0.6), mat("#f2e2c0", kind='soft', rim=0.5), loc=hut + Vector((0, 0, 0.3)), bevel=0.04)
    for s in (-1, 1):
        box("roof", (0.62, 0.95, 0.07), mat("#d9583a", kind='soft', rim=0.5), loc=hut + Vector((s * 0.24, 0, 0.74)), rot=(0, s * 0.72, 0),
            bevel=0.02)
    box("door", (0.22, 0.04, 0.34), mat("#8a5a36", kind='soft'), loc=hut + Vector((0.15, -0.39, 0.18)), bevel=0.02)
    box("mailslot", (0.2, 0.03, 0.06), mat("#e8b04a", metal=True), loc=hut + Vector((-0.22, -0.39, 0.38)))
    tube("pole", [hut + Vector((-0.5, 0.1, 0)), hut + Vector((-0.5, 0.1, 1.3))], [0.03], mat("#8a5a36"), seg=6, sub=1)
    box("flag", (0.45, 0.02, 0.26), mat("#4ad6c8", kind='soft', rim=0.5), loc=hut + Vector((-0.26, 0.1, 1.17)))
    rock("r1", 0.5, (-1.8, -0.5, 0.1), 8)
    rock("r2", 0.35, (1.9, -0.3, 0.05), 9)
    bush((-1.0, -0.3, 0.6), 0.35, seed=3)
    foam_ring(2.65, 2.05, seed=2)


def island_c():   # tiny sandbar with one palm and a half-buried chest
    sand_mound(1.5, 1.0, 0.3, 3)
    palm((-0.3, 0.2, 0.25), 1.8, 0.45, 5)
    ch = Vector((0.55, -0.15, 0.22))
    box("chest", (0.55, 0.38, 0.3), wood("#a8693a", "#5c3520", axis='z', fv=1 / 0.1, fu=0.0, P=dict(butt=0.0, seam=0.1)),
        loc=ch, rot=(0.1, 0.05, 0.3), bevel=0.03)
    blob("lid", 0.3, mat("#8a5530", kind='soft', rim=0.5), loc=ch + Vector((0, 0, 0.17)), scale=(0.95, 0.65, 0.4), rot=(0.1, 0.05, 0.3),
         deform=lambda p: Vector((p.x, p.y, max(p.z, 0))))
    for x in (-0.18, 0.18):
        box("strap", (0.06, 0.4, 0.34), mat("#e8b04a", metal=True), loc=ch + Vector((x * math.cos(0.3), x * math.sin(0.3), 0.04)),
            rot=(0.1, 0.05, 0.3))
    ellipsoid("coin", 0.07, mat("#ffd36a", metal=True), loc=ch + Vector((0.3, -0.3, -0.12)), scale=(1, 1, 0.3))
    foam_ring(1.55, 1.05, seed=3, w=0.1)


def island_d():   # big green island with a cliff and trees
    sand_mound(4.3, 3.0, 0.45, 4)
    rock("cliff", 2.6, (0.2, 0.6, 0.3), 11, sq=0.75)
    grass_cap(2.9, 2.2, 0.9, 1.6, 4)
    rnd = random.Random(4)
    for i in range(6):
        a = rnd.uniform(0, TAU)
        p = Vector((1.7 * math.cos(a), 1.2 * math.sin(a) + 0.4, 2.2))
        tube("tt", [p, p + Vector((0, 0, 0.6))], [0.1], mat("#7a5232"), seg=6, sub=1)
        ellipsoid("tree", 0.55, mat("#3f9a4f" if i % 2 else "#58b25a", kind='soft', rim=0.6, pat='noise', P=dict(scale=10), var=0.12),
                  loc=p + Vector((0, 0, 1.0)), scale=(1, 1, 1.15))
    palm((-3.2, -0.8, 0.3), 2.0, -0.5, 9)
    palm((3.3, -0.6, 0.3), 2.2, 0.5, 10)
    rock("r1", 0.5, (2.4, -1.9, 0.1), 12)
    foam_ring(4.35, 3.05, seed=4, w=0.14)


# ------------------------------------------------------------------ reefs
def reef(seed, n=4, spread=1.2, coral=True):
    rnd = random.Random(seed)
    for i in range(n):
        p = (rnd.uniform(-spread, spread), rnd.uniform(-spread * 0.6, spread * 0.6), rnd.uniform(-0.1, 0.1))
        rock(f"rk{i}", rnd.uniform(0.35, 0.7), p, seed * 10 + i, color="#6f6680", moss=False, sq=rnd.uniform(0.8, 1.3))
    if coral:
        cols = ["#ff7f9e", "#ffb84a", "#9a7bff", "#4ad6c8"]
        for i in range(5):
            b = Vector((rnd.uniform(-spread, spread), rnd.uniform(-spread * 0.5, spread * 0.5) - 0.2, 0.15))
            col = rnd.choice(cols)
            for k in range(3):
                a = rnd.uniform(0, TAU)
                tip = b + Vector((0.2 * math.cos(a), 0.2 * math.sin(a), rnd.uniform(0.3, 0.55)))
                tube("coral", [b, b.lerp(tip, 0.5) + Vector((0.05, 0, 0)), tip], [0.07, 0.04], mat(col, kind='soft', rim=0.6),
                     seg=6, sub=3)
                ellipsoid("ctip", 0.06, mat(col, kind='soft', rim=0.6), loc=tip)
    foam_ring(spread * 1.1 + 0.4, spread * 0.7 + 0.35, seed=seed)


# ------------------------------------------------------------------ lighthouse
def lighthouse(lit):
    rock("base", 2.0, (0, 0.2, -0.1), 21, sq=0.55)
    sand_mound(2.3, 1.7, 0.25, 7, col="#d8c08a")
    H = 6.6
    z0 = 0.75
    stripes = mat("#f4f0ea", pat='stripes', color2="#d9483a", kind='soft', rim=0.6, P=dict(fv=0.9, thr=0.5, weave=False))
    loft("tower", [(z0 - 0.3, 0.95, 0.95), (z0, 0.92, 0.92), (z0 + H, 0.6, 0.6)], stripes, seg=36)
    loft("plinth", [(z0 - 0.35, 1.15, 1.15), (z0 + 0.25, 1.05, 1.05)], mat("#b8b0b8", kind='soft', rim=0.5, pat='noise',
         P=dict(scale=10), var=0.1), seg=36, cap_top=True)
    # door + little windows
    box("door", (0.45, 0.1, 0.75), mat("#5a3a2a", kind='soft'), loc=(0.0, -0.98, z0 + 0.6), bevel=0.05)
    ellipsoid("doorarch", 0.23, mat("#5a3a2a", kind='soft'), loc=(0, -0.99, z0 + 0.97), scale=(1, 0.2, 0.6))
    for i, z in enumerate((z0 + 2.2, z0 + 3.9)):
        r = 0.92 - 0.32 * (z - z0) / H
        ellipsoid("win", 0.13, glow("#ffd27a", 1.4) if lit else mat("#2a3040", kind='flat'), loc=(0.15, -r - 0.02, z),
                  scale=(0.8, 0.2, 1.2), line=False)
    zt = z0 + H
    cyl("gallery", 0.95, 0.95, 0.14, mat("#3a3446", kind='soft', rim=0.5), loc=(0, 0, zt), seg=36)
    for k in range(16):
        a = TAU * k / 16
        tube("rail", [Vector((0.9 * math.cos(a), 0.9 * math.sin(a), zt + 0.14)), Vector((0.9 * math.cos(a), 0.9 * math.sin(a), zt + 0.5))],
             [0.022], mat("#2a2436"), seg=5, sub=1, line=False)
    ring_tube("railtop", (0, 0, zt + 0.5), 0.9, 0.03, mat("#2a2436"), axis='z', seg=40, tseg=5, line=False)
    cyl("lroom", 0.52, 0.52, 0.12, mat("#3a3446", kind='soft'), loc=(0, 0, zt + 0.14), seg=24)
    if lit:
        cyl("glass", 0.48, 0.48, 0.85, glow("#ffe7a0", 1.6), loc=(0, 0, zt + 0.26), seg=24, line=False)
        ellipsoid("lamp", 0.3, glow("#fffbe8", 3.5), loc=(0, -0.05, zt + 0.68), line=False)
    else:
        cyl("glass", 0.48, 0.48, 0.85, mat("#3a5a6a", kind='soft', rim=0.9), loc=(0, 0, zt + 0.26), seg=24)
        ellipsoid("lamp", 0.22, mat("#8a8496", kind='soft', rim=0.6), loc=(0, -0.05, zt + 0.66))
    for k in range(6):
        a = TAU * k / 6
        tube("mull", [Vector((0.49 * math.cos(a), 0.49 * math.sin(a), zt + 0.26)), Vector((0.49 * math.cos(a), 0.49 * math.sin(a), zt + 1.11))],
             [0.025], mat("#2a2436"), seg=5, sub=1, line=False)
    loft("dome", [(zt + 1.1, 0.62, 0.62), (zt + 1.2, 0.6, 0.6), (zt + 1.5, 0.35, 0.35), (zt + 1.68, 0.06, 0.06)],
         mat("#d9483a", kind='soft', rim=0.6), seg=28, cap_top=True)
    ellipsoid("finial", 0.1, mat("#e8b04a", metal=True), loc=(0, 0, zt + 1.78))
    # keeper's things: a boat bollard and a small rowboat tied up
    tube("bollard", [Vector((1.4, -1.0, 0.25)), Vector((1.4, -1.0, 0.6))], [0.09], iron(), seg=8, sub=1)
    foam_ring(2.35, 1.8, seed=21)
    return proj(0, -0.05, zt + 0.68)


def pier():
    deck = wood("#c9905a", "#6a3e22", axis='x', along='y', fv=1 / 0.25, fu=0.3, P=dict(seam=0.1, butt=0.08))
    box("deck", (4.0, 1.4, 0.12), deck, loc=(0, 0, 0.7), bevel=0.02)
    for x in (-1.8, -0.6, 0.6, 1.8):
        for y in (-0.6, 0.6):
            tube("post", [Vector((x, y, -0.2)), Vector((x, y, 0.95 if y < 0 else 0.7))], [0.11], mat("#7a4c2c", pat='wood',
                 P=dict(nu=4, fv=3)), seg=10, sub=1)
            ring_tube("algae", (x, y, 0.05), 0.12, 0.04, mat("#4a8a5a", kind='soft'), axis='z', seg=12, tseg=4, line=False)
    spiral_coil("rope", (1.2, 0.2, 0.76), 0.06, 0.22, 2.5, 0.04, rope_mat())
    tube("lpost", [Vector((-1.8, 0.55, 0.76)), Vector((-1.8, 0.55, 2.0))], [0.05], mat("#3a3446"), seg=8, sub=1)
    lantern("pl", (-1.8, 0.55, 2.0), scale=0.8, halo=False)
    foam_ring(2.3, 0.95, seed=5, w=0.08)


def buoy(lit=True):
    loft("b", [(-0.1, 0.4, 0.4), (0.15, 0.45, 0.45), (0.3, 0.4, 0.4), (0.35, 0.2, 0.2)], mat("#e8483a", kind='soft', rim=0.6,
         pat='stripes', color2="#f4f0ea", P=dict(fv=4.5, thr=0.5, weave=False)), seg=28, cap_top=True)
    for k in range(3):
        a = TAU * k / 3
        tube("cage", [Vector((0.18 * math.cos(a), 0.18 * math.sin(a), 0.33)), Vector((0.08 * math.cos(a), 0.08 * math.sin(a), 1.05))],
             [0.03], mat("#3a3446"), seg=6, sub=1)
    cyl("lamp", 0.1, 0.1, 0.16, glow("#ffd27a", 2.6) if lit else mat("#5a5a6a"), loc=(0, 0, 1.0), seg=14, line=False)
    ellipsoid("top", 0.09, mat("#3a3446"), loc=(0, 0, 1.2))
    foam_ring(0.5, 0.42, seed=6, w=0.06)


def bottle():
    bt = pivot("bt", (0, 0, 0.12), rot=(0, 1.15, 0.5))
    loft("glass", [(-0.38, 0.0, 0.0), (-0.36, 0.2, 0.2), (-0.2, 0.26, 0.26), (0.25, 0.26, 0.26), (0.42, 0.17, 0.17),
                   (0.52, 0.09, 0.09), (0.72, 0.08, 0.08), (0.75, 0.1, 0.1)], mat("#5fd0c8", kind='soft', rim=0.9), bt, seg=24,
         cap_top=True)
    cyl("cork", 0.075, 0.09, 0.12, mat("#c08048", kind='soft'), bt, loc=(0, 0, 0.73))
    tube("scroll", [Vector((0, 0, -0.22)), Vector((0, 0, 0.22))], [0.12], mat("#fff4d8", kind='soft', rim=0.4), bt, seg=12, sub=1)
    ring_tube("rib", (0, 0, 0), 0.125, 0.02, mat("#ff6a6a", kind='soft'), bt, axis='z', seg=16, tseg=4, line=False)
    foam_ring(0.42, 0.25, seed=7, w=0.05)


def crate_float():
    c = pivot("c", (0, 0, 0.0), rot=(0.12, -0.1, 0.4))
    sz = 0.7
    box("b", (sz, sz, sz), wood("#c08048", "#6a3e22", axis='z', fv=1 / 0.18, fu=0.0, P=dict(seam=0.1, butt=0.0)), c,
        loc=(0, 0, 0.12), bevel=0.02)
    fr = mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.2)
    for (px, py) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        box("e", (0.07, 0.07, sz + 0.01), fr, c, loc=(px * (sz / 2 - 0.03), py * (sz / 2 - 0.03), 0.12), bevel=0.01)
    box("q", (0.3, 0.02, 0.3), mat("#ffd36a", kind='soft', rim=0.5), c, loc=(0, -sz / 2 - 0.012, 0.15))
    from sea_creatures import glyph
    glyph("?", mat("#8a4a1a", kind='soft'), c, (0, -sz / 2 - 0.03, 0.15), 0.26, extrude=0.01)
    foam_ring(0.6, 0.45, seed=8, w=0.07)


def cove(kind):
    if kind == 'a':   # natural rock arch
        rock("leg1", 1.0, (-1.4, 0.2, 0.3), 31, sq=1.6)
        rock("leg2", 0.9, (1.5, 0.3, 0.3), 32, sq=1.7)
        pts = [Vector((-1.4, 0.25, 1.6)), Vector((-0.6, 0.25, 2.5)), Vector((0.6, 0.3, 2.55)), Vector((1.5, 0.3, 1.7))]
        tube("arch", pts, [0.7, 0.55, 0.55, 0.7], mat(ROCK, kind='soft', rim=0.5, pat='patches', color2="#7ab04a",
             P=dict(scale=3, thr=0.6, sharp=8), var=0.12), seg=16, sub=5)
        bush((-0.4, 0.3, 2.9), 0.35, seed=6)
        foam_ring(2.5, 1.2, seed=31)
    else:             # crescent cliff around a sandy beach
        sand_mound(2.4, 1.2, 0.25, 8)
        rnd = random.Random(33)
        for i in range(7):
            a = math.pi * (0.05 + 0.9 * i / 6)
            p = (2.4 * math.cos(a), 1.2 + 0.9 * math.sin(a) - 0.6, 0.3)
            rock(f"c{i}", rnd.uniform(0.7, 1.0), p, 40 + i, sq=rnd.uniform(1.4, 2.0))
        for i in range(4):
            a = math.pi * (0.2 + 0.6 * i / 3)
            bush((2.3 * math.cos(a), 1.2 + 0.9 * math.sin(a) - 0.6, 1.75), 0.32, seed=20 + i)
        palm((-0.6, 0.0, 0.2), 1.7, 0.3, 12)
        foam_ring(2.8, 1.6, seed=33)


ITEMS = {
    'island_a': (island_a, (320, 320), (160, 250)), 'island_b': (island_b, (340, 340), (170, 270)),
    'island_c': (island_c, (220, 220), (110, 170)), 'island_d': (island_d, (560, 480), (280, 380)),
    'reef_a': (lambda: reef(1, 4, 1.0), (220, 160), (110, 110)), 'reef_b': (lambda: reef(2, 6, 1.5), (260, 180), (130, 125)),
    'reef_c': (lambda: reef(3, 3, 0.7, coral=False), (180, 140), (90, 95)),
    'pier': (pier, (300, 220), (150, 150)), 'buoy': (buoy, (80, 120), (40, 100)), 'buoy_dark': (lambda: buoy(False), (80, 120), (40, 100)),
    'bottle': (bottle, (80, 60), (40, 40)), 'crate_float': (crate_float, (100, 100), (50, 70)),
    'cove_a': (lambda: cove('a'), (320, 300), (160, 230)), 'cove_b': (lambda: cove('b'), (420, 320), (210, 220)),
}


def main():
    a = args()
    raw = a[0]
    names = a[1:] or (list(ITEMS) + ['lighthouse_unlit', 'lighthouse_lit'])
    job = Job(raw, "env")
    for nm in names:
        job.scene('day', samples=24)
        STATE['line_t'] = 0.016
        if nm.startswith('lighthouse'):
            lamp = lighthouse(nm.endswith('lit') and not nm.endswith('unlit'))
            job.shoot(nm, (260, 560), (130, 480), line_t=0.016, extra=dict(lampPx=[round(lamp[0], 1), round(lamp[1], 1)],
                                                                           note="lampPx = lamp centre from the anchor; put lighthouse_beam there"))
        else:
            fn, cell, anc = ITEMS[nm]
            fn()
            job.shoot(nm, cell, anc, line_t=0.016)


main()
