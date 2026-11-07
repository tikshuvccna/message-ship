"""Ship atlas renders (hull, hull_front, mast, sails, stations, props, fx).

blender -b --python art/blender/ship.py -- <ABS rawdir> [group ...]
groups: hull mast sails stations props flags fx   (default: all)
Raw PNGs + meta.json go to <rawdir>/ship ; art/pack_atlas.py ship <rawdir> packs them.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Euler

from v2lib import *
from v2lib import _catmull
from shiplib import *

# ===================================================================== hull geometry
CTRL = [(-8.62, 0.0), (-8.5, 1.45), (-8.1, 2.52), (-7.3, 3.22), (-6.0, 3.48), (-3.0, 3.5), (1.6, 3.5),
        (4.4, 3.34), (6.4, 2.45), (7.75, 1.2), (8.48, 0.0)]


def plan_curve(n=150):
    pts = _catmull([Vector((x, y, 0)) for x, y in CTRL], 20)
    L = [0.0]
    for i in range(1, len(pts)):
        L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    out = []
    j = 0
    for k in range(n):
        t = L[-1] * k / (n - 1)
        while j < len(L) - 2 and L[j + 1] < t:
            j += 1
        f = (t - L[j]) / max(1e-9, L[j + 1] - L[j])
        p = pts[j].lerp(pts[j + 1], f)
        out.append((p.x, max(0.0, p.y)))
    out[0] = (out[0][0], 0.0)
    out[-1] = (out[-1][0], 0.0)
    return out


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def ztop(x):
    return 0.9 + 0.55 * smoothstep(3.0, 8.5, x) ** 1.4 + 0.38 * smoothstep(-5.2, -8.6, x)


def sect(z):
    if z >= 0:
        return 1.0 - 0.03 * z
    b = (1 - min(1.0, -z / 1.85) ** 2.2) ** 0.5
    return b + 0.035 * math.sin(math.pi * min(1.0, -z / 0.8))


def F(x, y, z):
    if z < 0:
        kx = 1 - 0.07 * (-z) ** 1.3
        return Vector((x * kx, y * sect(z), z))
    return Vector((x * (1 + 0.02 * z), y * sect(z), z))


NEAR_SOLID = 0.34


def _soft(d, half, soft):
    return 1.0 if d < half else max(0.0, 1 - (d - half) / soft)


def notch(x, y):
    """Gun ports in the far bulwark: far cannon at x=1.0, stern cannon at y=1.8."""
    n = _soft(abs(x - 1.0), 0.6, 0.25)
    if x < -7.2:
        n = max(n, _soft(abs(y - 1.8), 0.5, 0.25))
    return n * n * (3 - 2 * n)


def zt_far(x, y):
    zt = ztop(x)
    return zt - notch(x, y) * (zt - 0.36)


WATER_Z = -1.0
BELOW = [0.0, -0.08, -0.18, -0.3, -0.42, -0.53, -0.6, -0.68, -0.78, -0.9, -1.0]


def build_hull(front_only_tag=True):
    C = plan_curve()
    hull_wood = wood("#b07240", "#5c3520", axis='z', fv=1 / 0.17, fu=0.32, var=0.3, bump=0.55,
                     P=dict(seam=0.09, seed=3.1))
    coral = wood("#c95a3f", "#7a2a22", axis='z', fv=1 / 0.17, fu=0.32, var=0.18, bump=0.4, P=dict(seam=0.08, seed=5.2))
    teal = wood("#2f8494", "#1a4f5a", axis='z', fv=1 / 0.15, fu=0.25, var=0.18, bump=0.35, P=dict(seam=0.09, seed=7.7))
    cream = wood("#f0e2c2", "#b89a70", axis='z', fv=1 / 0.15, fu=0.25, var=0.12, bump=0.3, P=dict(seam=0.08, seed=2.2))
    cap = mat("#6e4529", pat='wood', P=dict(nu=8, fv=2), var=0.2, bump=0.3)
    deckm = wood("#d9a764", "#8a5530", axis='y', along='x', fv=1 / 0.29, fu=0.38, var=0.3, bump=0.5,
                 P=dict(seam=0.075, butt=0.06, seed=9.9))
    gold = brass()
    objs = []
    for s in (-1, 1):
        side = 'near' if s < 0 else 'far'
        # ---- outer skin below the deck
        P = [[F(x, s * y, z) for (x, y) in C] for z in BELOW]
        o = grid_mesh(f"hull_{side}", P, hull_wood, outward=lambda c, s=s: (0, s, 0) if abs(c.x) < 7 else (c.x, s * 0.3, 0))
        o.data.materials.append(coral)
        for p in o.data.polygons:
            if p.center.z < -0.6:
                p.material_index = 1
        o["front"] = False
        o["line_k"] = 1.5
        # ---- bulwark. Far: solid (cream inner face visible) with gun ports. Near: low solid gunwale + open
        #      balustrade up to the same rail height (cutaway, so deck items near the near rail stay visible).
        V = [i / 6 for i in range(7)]
        if s > 0:
            P = [[F(x, s * y, v * zt_far(x, y)) for (x, y) in C] for v in V]
        else:
            P = [[F(x, s * y, v * NEAR_SOLID) for (x, y) in C] for v in V]
        b = grid_mesh(f"bulwark_{side}", P, teal, outward=lambda c, s=s: (0, s, 0) if abs(c.x) < 7 else (c.x, s * 0.3, 0))
        b.data.materials.append(cream)
        b.data.materials.append(cap)
        solidify(b, 0.13, offset=-1.0, mat_offset=1, rim_offset=2)
        b["front"] = (s < 0)
        b["line_k"] = 1.5
        # ---- rail cap
        top = []
        for (x, y) in C:
            zt = zt_far(x, y) if s > 0 else ztop(x)
            p = F(x, s * y, zt)
            top.append(Vector((p.x, p.y - s * 0.06 * (1 if abs(x) < 7.9 else 0.3), zt + 0.035)))
        rc = tube(f"rail_{side}", top[::2] + [top[-1]], [0.085], cap, seg=10, sub=1)
        rc["front"] = (s < 0)
        if s < 0:
            low = []
            for (x, y) in C:
                p = F(x, s * y, NEAR_SOLID)
                low.append(Vector((p.x, p.y - s * 0.06, NEAR_SOLID + 0.03)))
            t0 = tube("gunwale_cap", low[::2] + [low[-1]], [0.07], cap, seg=10, sub=1)
            t0["front"] = True
            bm_ = mat("#f3e6c6", kind='soft', rim=0.5)
            acc = 0.0
            for k in range(1, len(C) - 1):
                x, y = C[k]
                acc += math.hypot(x - C[k - 1][0], y - C[k - 1][1])
                if acc < 0.55:
                    continue
                acc = 0.0
                if abs(x - 1.0) < 0.78:      # gun port of the near cannon: no balusters
                    continue
                zt = ztop(x)
                p = F(x, s * y, 0)
                h = zt - NEAR_SOLID
                bl = loft(f"bal{k}", [(0, 0.05, 0.05), (h * 0.18, 0.035, 0.035), (h * 0.45, 0.06, 0.06),
                                      (h * 0.75, 0.035, 0.035), (h, 0.045, 0.045)], bm_,
                          loc=(p.x, p.y - s * 0.06, NEAR_SOLID), seg=10)
                bl["front"] = True
            trim = [F(x, s * (y + 0.012), 0.2) for (x, y) in C[2:-2:2]]
            t1 = tube(f"trim_{side}", trim, [0.026], gold, seg=6, sub=1, line=False)
            t1["front"] = True
        wale = [F(x, s * (y + 0.035), -0.02) for (x, y) in C[1:-1:2]]
        t2 = tube(f"wale_{side}", wale, [0.07], mat("#f3e6c6", kind='soft', rim=0.5), seg=8, sub=1)
        t2["front"] = False
        # ---- stanchions inside the far bulwark
        if s > 0:
            for k in range(6, len(C) - 6, 9):
                x, y = C[k]
                if notch(x, y) > 0.05:
                    continue
                x2, y2 = C[k + 1]
                ang = math.atan2(s * (y2 - y), x2 - x)
                zt = zt_far(x, y)
                p = F(x, s * (y - 0.19), 0)
                st = box(f"stan_{side}{k}", (0.11, 0.1, zt), mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.15),
                         loc=(p.x, p.y, zt / 2), rot=(0, 0, ang), bevel=0.015)
                st["front"] = False
    # ---- deck (planks along x)
    rows = []
    K = 14
    for (x, y) in C:
        rows.append([Vector((x * 1.0, -y + 2 * y * k / K, 0.0)) for k in range(K + 1)])
    # transpose: rows across y, cols along curve
    P = [[rows[i][k] for i in range(len(C))] for k in range(K + 1)]
    d = grid_mesh("deck", P, deckm, line=False, outward=lambda c: (0, 0, 1), smooth=False)
    d["front"] = False
    # ---- portholes on the near side
    for i, x in enumerate((-5.4, -3.3, -1.2, 0.9, 3.0)):
        # hull half-width at that x
        yy = max(y for (cx, y) in C if abs(cx - x) < 0.25)
        z = -0.42
        p = F(x, -(yy + 0.0), z)
        rg = ring_tube(f"port{i}", (p.x, p.y - 0.02, z), 0.13, 0.035, gold, axis='y', seg=24)
        rg["front"] = False
        g = ellipsoid(f"portg{i}", 0.11, glow("#ffcf73", strength=1.9), loc=(p.x, p.y + 0.005, z), scale=(1, 0.25, 1),
                      line=False)
        g["front"] = False
    # ---- bowsprit, figurehead scroll, stern lantern
    bsp = tube("bowsprit", [Vector((7.2, 0, 1.05)), Vector((10.5, 0, 2.05))], [0.15, 0.085],
               mat("#7a4c2c", pat='wood', P=dict(nu=6, fv=2), var=0.2), seg=12, sub=1)
    for t in (0.3, 0.62, 0.9):
        q = Vector((7.2, 0, 1.05)).lerp(Vector((10.5, 0, 2.05)), t)
        ring_tube(f"bsband{t}", q, 0.15 - 0.065 * t + 0.012, 0.022, gold, axis='x', seg=16, tseg=5, line=False)
    sc = []
    for i in range(60):
        t = i / 59
        a = 2.6 * TAU * t
        r = 0.32 * (1 - t) + 0.05
        sc.append(Vector((8.62 + 0.05 * t + r * math.cos(a) * 0.9, 0.0, 1.05 + 0.22 + r * math.sin(a))))
    tube("scroll", sc, [0.07, 0.04], gold, seg=8, sub=1)
    lantern("bow_lantern", (10.32, 0, 1.55), scale=0.7)
    tube("bow_lantern_rope", [Vector((10.32, 0, 1.86)), Vector((10.34, 0, 2.0))], [0.012], rope_mat(), seg=5, sub=1,
         line=False)
    # stern lantern on an iron bracket
    tube("stern_post", [Vector((-8.55, 0, 1.0)), Vector((-8.6, 0, 1.6)), Vector((-8.78, 0, 1.95)),
                        Vector((-8.95, 0, 1.92))], [0.05, 0.04], iron(), seg=8, sub=4)
    lantern("stern_lantern", (-8.95, 0, 1.42), scale=0.95)
    # ---- deck decor (flat): rope coils, cleats, ring bolts
    rm = rope_mat()
    spiral_coil("coil_a", (-5.3, 2.75, 0), 0.08, 0.3, 3.2, 0.045, rm)
    spiral_coil("coil_b", (5.5, 1.75, 0), 0.07, 0.26, 2.8, 0.042, rm)
    for (cx, cy) in ((-2.0, 3.12), (3.6, 3.05), (-2.0, -3.12), (3.6, -3.05)):
        cl = box(f"cleat{cx}{cy}", (0.42, 0.1, 0.08), mat("#5a5866", rim=0.4), loc=(cx, cy, 0.09), bevel=0.03)
        cl["front"] = False
        box(f"cleatb{cx}{cy}", (0.1, 0.08, 0.08), mat("#5a5866", rim=0.4), loc=(cx, cy, 0.04), bevel=0.02)
    for (cx, cy) in ((-4.8, 0.0), (2.6, -1.5), (5.4, -0.9), (-0.2, 1.8)):
        ring_tube(f"ringbolt{cx}", (cx, cy, 0.012), 0.07, 0.016, iron(), axis='z', seg=16, tseg=5, line=False)
    # ---- painted compass rose on the deck (subtle)
    rose = []
    for k in range(16):
        a = TAU * k / 16
        r = 0.62 if k % 4 == 0 else (0.34 if k % 2 == 0 else 0.22)
        rose.append(Vector((-5.0 + 0.0 + r * math.cos(a), -2.0 + 0.0 + r * math.sin(a), 0.004)))
    # (kept off: the rose is drawn below by deck_paint)
    return C


def deck_paint(C):
    """Painted compass star on the deck between hatch and mast (flat decal)."""
    cx, cy = 3.0, 0.4
    pts = []
    for k in range(16):
        a = TAU * k / 16 + math.pi / 16 * 0
        r = 0.75 if k % 4 == 0 else (0.36 if k % 2 == 0 else 0.22)
        pts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a), 0.004)))
    verts = [Vector((cx, cy, 0.004))] + pts
    faces = [(0, 1 + i, 1 + (i + 1) % 16) for i in range(16)]
    o = mesh_obj("rose", verts, faces, mat("#e8d4a8", kind='flat', rim=0.0, ao=0.3), smooth=False, recalc=False, line=False)
    fix_normals_out(o, lambda c: (0, 0, 1))
    ring_tube("rose_ring", (cx, cy, 0.006), 0.5, 0.018, mat("#2f8494", kind='flat', rim=0.0), axis='z', seg=40,
              tseg=4, line=False)
    o["front"] = False


def render_hull(job):
    job.scene('day', samples=24)
    C = build_hull()
    deck_paint(C)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and "front" not in o:
            o["front"] = False
    add_lines(t=0.016)
    cell, anchor = (1216, 400), (540, 214)
    sprite_camera(cell[0], cell[1], anchor, ssaa=4)
    sc = bpy.context.scene
    # pass 1: everything except the near bulwark (which still casts its shadow)
    for o in sc.objects:
        if o.type == 'MESH':
            o.visible_camera = not bool(o.get("front"))
    render_to(os.path.join(job.dir, "hull.png"))
    job.meta['hull'] = dict(cell=list(cell), anchor=list(anchor), ssaa=4,
                            note="origin = ship centre (0,0) on the deck (z=0)")
    # pass 2: near bulwark only
    for o in sc.objects:
        if o.type == 'MESH':
            o.visible_camera = bool(o.get("front"))
    render_to(os.path.join(job.dir, "hull_front.png"))
    job.meta['hull_front'] = dict(cell=list(cell), anchor=list(anchor), ssaa=4, note="same origin as hull; draw above characters")
    # pass 3: both (reference for the preview)
    for o in sc.objects:
        if o.type == 'MESH':
            o.visible_camera = True
    render_to(os.path.join(job.dir, "_hull_full.png"))
    job.save()


GROUPS = {}


def main():
    a = args()
    raw = a[0]
    groups = a[1:] or ['hull']
    job = Job(raw, "ship")
    for g in groups:
        if g == 'hull':
            render_hull(job)
        else:
            import ship_items
            ship_items.render_group(job, g)


if __name__ == "__main__":
    main()
