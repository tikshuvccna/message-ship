"""Ship atlas: mast, sails, stations, props, flags, fx (called from ship.py)."""
import math
import os
import random

import bpy
from mathutils import Vector, Euler

from v2lib import *
from shiplib import *

CANVAS = "#f6ecd4"
TEAL = "#2f8494"
CORAL = "#d9654a"
DARKWOOD = "#7a4c2c"


def dwood():
    return mat(DARKWOOD, pat='wood', P=dict(nu=6, fv=2), var=0.22, bump=0.3)


# ===================================================================== mast
def build_mast():
    w = dwood()
    g = brass()
    loft("mast", [(0, 0.2, 0.2), (3, 0.185, 0.185), (6.8, 0.15, 0.15), (9.6, 0.105, 0.105)], w, seg=20, cap_top=True)
    # partner collar + fife rail with belaying pins
    cyl("collar", 0.34, 0.27, 0.16, mat("#8a5a36", pat='wood', P=dict(nu=10, fv=3), var=0.2), seg=24)
    ring_tube("fife", (0, 0, 0.62), 0.42, 0.045, w, axis='z', seg=28)
    for k in range(3):
        a = TAU * k / 3 + 0.5
        tube(f"fpost{k}", [Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 0)),
                           Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 0.62))], [0.04], w, seg=8, sub=1)
    for k in range(8):
        a = TAU * k / 8 + 0.2
        tube(f"pin{k}", [Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 0.52)),
                         Vector((0.42 * math.cos(a), 0.42 * math.sin(a), 0.78))], [0.022, 0.03], g, seg=6, sub=1, line=False)
    rm = rope_mat()
    spiral_coil("mcoil", (0.0, 0.0, 0.0), 0.36, 0.48, 1.4, 0.04, rm)
    for z in (1.6, 3.4, 5.4):
        ring_tube(f"band{z}", (0, 0, z), 0.2 - 0.008 * z, 0.03, g, axis='z', seg=20, tseg=5, line=False)
    # crow's nest (barrel basket)
    rings = [(6.85, 0.36, 0.36), (6.95, 0.46, 0.46), (7.3, 0.5, 0.5), (7.55, 0.47, 0.47)]
    cn = loft("nest", rings, wood("#b07240", "#5c3520", axis='x', along='z', fv=1 / 0.14, fu=0.2, P=dict(seam=0.1, butt=0.0)),
              seg=28, cap_bot=True)
    ring_tube("nest_hoop1", (0, 0, 7.0), 0.47, 0.03, iron(), axis='z', seg=28, tseg=5, line=False)
    ring_tube("nest_hoop2", (0, 0, 7.5), 0.48, 0.03, iron(), axis='z', seg=28, tseg=5, line=False)
    ring_tube("nest_rim", (0, 0, 7.56), 0.47, 0.045, mat("#6e4529"), axis='z', seg=28, tseg=6)
    lantern("nest_lantern", (0.0, -0.5, 7.0), scale=0.55)
    ellipsoid("truck", 0.13, g, loc=(0, 0, 9.7))
    return 9.6


# ===================================================================== sails
class GaffSail:
    def __init__(self, tack, throat, peak, clew, billow=0.55):
        self.tack, self.throat, self.peak, self.clew = map(Vector, (tack, throat, peak, clew))
        self.B = billow

    def xz(self, u, v):
        a = self.tack.lerp(self.clew, u)
        b = self.throat.lerp(self.peak, u)
        return a.lerp(b, v)

    def bil(self, u, v):
        return -self.B * (math.sin(math.pi * min(1, max(0, u))) ** 0.8) * (math.sin(math.pi * (0.12 + 0.8 * v)) ** 0.7)

    def folds(self, u, v):
        return 0.045 * math.sin((u * 0.9 - v) * 17.0) * u * (1 - v) * 2.2 + 0.03 * math.sin(u * 31 + v * 4) * (1 - v) * u

    def point(self, u, v, off=0.0):
        p = self.xz(u, v)
        return Vector((p.x, self.bil(u, v) + self.folds(u, v) - off, p.z))

    def uv_of(self, x, z):
        # invert the bilinear patch (Newton, it is nearly a parallelogram)
        u, v = 0.5, 0.5
        for _ in range(12):
            p = self.xz(u, v)
            du = (self.xz(u + 1e-3, v) - p) / 1e-3
            dv = (self.xz(u, v + 1e-3) - p) / 1e-3
            ex, ez = x - p.x, z - p.z
            det = du.x * dv.z - du.z * dv.x
            u += (ex * dv.z - ez * dv.x) / det
            v += (du.x * ez - du.z * ex) / det
        return u, v

    def mesh(self, name, material, nu=28, nv=22, u0=0.0, u1=1.0, v0=0.0, v1=1.0, off=0.0, line=None):
        P = [[self.point(u0 + (u1 - u0) * i / nu, v0 + (v1 - v0) * k / nv, off) for i in range(nu + 1)] for k in range(nv + 1)]
        return grid_mesh(name, P, material, line=line, outward=lambda c: (0, -1, 0))

    def decal(self, name, pts2d, material, off):
        """Star-convex polygon given in (x,z) world coords, laid on the surface."""
        cx = sum(p[0] for p in pts2d) / len(pts2d)
        cz = sum(p[1] for p in pts2d) / len(pts2d)
        n = len(pts2d)
        ring = 4
        verts = []
        def P(x, z):
            u, v = self.uv_of(x, z)
            return self.point(u, v, off)
        verts.append(P(cx, cz))
        for k in range(1, ring + 1):
            f = k / ring
            for (x, z) in pts2d:
                verts.append(P(cx + (x - cx) * f, cz + (z - cz) * f))
        faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
        for k in range(ring - 1):
            a, b = 1 + k * n, 1 + (k + 1) * n
            for i in range(n):
                j = (i + 1) % n
                faces.append((a + i, b + i, b + j, a + j))
        o = mesh_obj(name, verts, faces, material, smooth=True, recalc=False, line=False)
        fix_normals_out(o, lambda c: (0, -1, 0))
        return o


class Jib(GaffSail):
    """Triangle: tack, head, clew (head as throat=peak)."""

    def __init__(self, tack, head, clew, billow=0.4):
        super().__init__(tack, head, head, clew, billow)

    def bil(self, u, v):
        return -self.B * (math.sin(math.pi * u) ** 0.8) * (math.sin(math.pi * (0.1 + 0.8 * v)) ** 0.8) * (1 - 0.6 * v)

    def folds(self, u, v):
        return 0.03 * math.sin((u - v) * 15) * u * (1 - v)


def canvas_mat():
    return mat(CANVAS, pat='planks', color2="#d9c9a4", kind='soft', var=0.08, bump=0.25, rim=0.45,
               P=dict(axis='x', along='z', fv=1 / 0.62, fu=0.0, seam=0.035, butt=0.0, seed=4.4))


def circle_pts(cx, cz, r, n=32, a0=0.0):
    return [(cx + r * math.cos(a0 + TAU * i / n), cz + r * math.sin(a0 + TAU * i / n)) for i in range(n)]


def emblem(sail, cx, cz, R):
    """Gold ring, teal disc, cream lantern with a warm light (painted on the sail)."""
    sail.decal("emb_ring", circle_pts(cx, cz, R), mat("#e8b04a", kind='soft', rim=0.3), 0.012)
    sail.decal("emb_disc", circle_pts(cx, cz, R * 0.84), mat(TEAL, kind='soft', rim=0.2), 0.02)
    s = R
    body = [(cx - 0.3 * s, cz - 0.42 * s), (cx + 0.3 * s, cz - 0.42 * s), (cx + 0.34 * s, cz + 0.22 * s),
            (cx - 0.34 * s, cz + 0.22 * s)]
    sail.decal("emb_lan", body, mat("#f6ecd4", kind='soft', rim=0.1), 0.028)
    roof = [(cx - 0.42 * s, cz + 0.22 * s), (cx + 0.42 * s, cz + 0.22 * s), (cx + 0.04 * s, cz + 0.52 * s),
            (cx - 0.04 * s, cz + 0.52 * s)]
    sail.decal("emb_roof", roof, mat("#f6ecd4", kind='soft', rim=0.1), 0.028)
    sail.decal("emb_light", circle_pts(cx, cz - 0.1 * s, 0.19 * s, 20), glow("#ffc94a", strength=1.6), 0.036)
    base = [(cx - 0.38 * s, cz - 0.42 * s), (cx + 0.38 * s, cz - 0.42 * s), (cx + 0.38 * s, cz - 0.5 * s),
            (cx - 0.38 * s, cz - 0.5 * s)]
    sail.decal("emb_base", base, mat("#f6ecd4", kind='soft', rim=0.1), 0.028)
    ring = [(cx + 0.06 * s * math.cos(TAU * i / 12), cz + 0.6 * s + 0.06 * s * math.sin(TAU * i / 12)) for i in range(12)]
    sail.decal("emb_hook", ring, mat("#f6ecd4", kind='soft', rim=0.1), 0.028)


def spar(name, a, b, r0, r1):
    return tube(name, [Vector(a), Vector(b)], [r0, r1], dwood(), seg=10, sub=1)


def line(name, pts, r=0.018):
    return tube(name, [Vector(p) for p in pts], [r], mat("#c9a870", kind='soft', rim=0.2), seg=5, sub=1, line=False)


def furl_bundle(name, a, b, r, ties=6, color=CANVAS):
    a, b = Vector(a), Vector(b)
    pts, rad = [], []
    n = 26
    for i in range(n + 1):
        t = i / n
        pts.append(a.lerp(b, t) + Vector((0, 0, 0.03 * math.sin(t * 19))))
        rad.append(r * (0.55 + 0.45 * math.sin(math.pi * min(1, t * 1.15)) ** 0.6) * (1 + 0.12 * math.sin(t * 37)))
    tube(name, pts, rad, mat(color, pat='noise', kind='soft', P=dict(scale=8), var=0.12, bump=0.6), seg=14, sub=1)
    for k in range(ties):
        t = (k + 0.5) / ties
        c = a.lerp(b, t)
        rr = r * (0.55 + 0.45 * math.sin(math.pi * min(1, t * 1.15)) ** 0.6) + 0.02
        ring_tube(f"{name}_tie{k}", c, rr, 0.018, rope_mat(), axis='x', seg=16, tseg=5, line=False)


def build_sails(state):
    """state 0 full, 1 reefed, 2 furled. Origin = mast foot."""
    cm = canvas_mat()
    # boom (always)
    spar("boom", (-0.15, 0, 3.05), (-6.0, 0, 2.97), 0.1, 0.075)
    ring_tube("gooseneck", (-0.05, 0, 3.05), 0.21, 0.04, iron(), axis='z', seg=20, tseg=5, line=False)
    top = Vector((0.0, 0, 9.35))
    bow = Vector((9.5, 0, 2.05))      # bowsprit tip relative to the mast
    if state == 0:
        S = GaffSail((-0.3, 0, 3.17), (-0.3, 0, 7.0), (-5.15, 0, 8.45), (-5.85, 0, 3.13), billow=0.6)
        gaff = ((-0.15, 0, 7.05), (-5.35, 0, 8.55))
    elif state == 1:
        S = GaffSail((-0.3, 0, 3.37), (-0.3, 0, 5.6), (-5.15, 0, 6.6), (-5.85, 0, 3.33), billow=0.45)
        gaff = ((-0.15, 0, 5.65), (-5.35, 0, 6.7))
    else:
        S = None
        gaff = ((-0.15, 0, 3.5), (-5.3, 0, 3.7))
    spar("gaff", gaff[0], gaff[1], 0.085, 0.06)
    ring_tube("gaffjaw", (Vector(gaff[0]) + Vector((0.02, 0, 0))), 0.21, 0.035, iron(), axis='z', seg=20, tseg=5, line=False)
    if S:
        S.mesh("main", cm)
        # foot band (teal) + coral stripe, a leech tape, then the emblem
        S.mesh("band_t", mat(TEAL, kind='soft', rim=0.35), u0=0.0, u1=1.0, v0=0.0, v1=0.13, off=0.008, nv=4, line=False)
        S.mesh("band_c", mat(CORAL, kind='soft', rim=0.35), u0=0.0, u1=1.0, v0=0.155, v1=0.2, off=0.008, nv=2, line=False)
        S.mesh("leech", mat("#e8d6ae", kind='soft'), u0=0.965, u1=1.0, v0=0.0, v1=1.0, off=0.006, nu=1, line=False)
        S.mesh("luff", mat("#e8d6ae", kind='soft'), u0=0.0, u1=0.03, v0=0.0, v1=1.0, off=0.006, nu=1, line=False)
        c = S.xz(0.5, 0.6 if state == 0 else 0.62)
        emblem(S, c.x, c.z, 1.0 if state == 0 else 0.7)
        # mast hoops on the luff
        for k in range(4 if state == 0 else 2):
            z = 3.5 + k * (3.2 / 3 if state == 0 else 1.8)
            ring_tube(f"hoop{k}", (0, 0, z), 0.2, 0.02, dwood(), axis='z', seg=18, tseg=5, line=False)
        line("peak_hal", [top, Vector(gaff[1]).lerp(Vector(gaff[0]), 0.45)], 0.016)
        line("peak_hal2", [top + Vector((0, 0, -0.3)), Vector(gaff[1]).lerp(Vector(gaff[0]), 0.08)], 0.016)
        line("sheet", [S.clew + Vector((0, 0, -0.05)), Vector((-6.6, 0, 0.9))], 0.02)
        if state == 1:
            furl_bundle("reef", (-0.3, 0, 3.23), (-5.8, 0, 3.17), 0.16, ties=7)
    else:
        furl_bundle("furl", (-0.25, 0, 3.27), (-5.75, 0, 3.23), 0.26, ties=7)
        line("peak_hal", [top, Vector(gaff[1]).lerp(Vector(gaff[0]), 0.4)], 0.016)
    line("topping", [top + Vector((0, 0, -0.1)), Vector((-5.95, 0, 3.0))], 0.014)
    # forestay + jib
    line("forestay", [top + Vector((0.05, 0, -0.6)), bow], 0.02)
    if state in (0, 1):
        J = Jib(bow + Vector((-0.12, 0, 0.06)), top + Vector((0.12, 0, -0.75 if state == 0 else -1.6)),
                Vector((4.6, 0, 3.0)), billow=0.5 if state == 0 else 0.4)
        J.mesh("jib", cm, nu=22, nv=18)
        J.mesh("jib_band", mat(CORAL, kind='soft', rim=0.3), u0=0.86, u1=1.0, v0=0.0, v1=1.0, off=0.008, nu=3, line=False)
        J.mesh("jib_band2", mat(TEAL, kind='soft', rim=0.3), u0=0.79, u1=0.84, v0=0.0, v1=1.0, off=0.008, nu=2, line=False)
        line("jibsheet", [J.clew, Vector((3.8, 0, 0.95))], 0.018)
    else:
        a, b = bow + Vector((-0.4, 0, 0.18)), top + Vector((0.05, 0, -1.1))
        pts, rad = [], []
        for i in range(21):
            t = i / 20
            pts.append(a.lerp(b, t))
            rad.append(0.13 * (1 - t) ** 0.6 + 0.03)
        tube("jibroll", pts, rad, mat(CANVAS, pat='spiral', color2="#d9c9a4", kind='soft', P=dict(nu=3, fv=10), var=0.1),
             seg=10, sub=1)


# ===================================================================== flag (pennant)
def build_flag(i):
    ph = TAU * i / 4
    L, H = 2.0, 0.55
    nu, nv = 24, 6
    rows = []
    for k in range(nv + 1):
        v = k / nv
        row = []
        for j in range(nu + 1):
            u = j / nu
            x = -u * L
            hz = H * (1 - 0.75 * u)          # tapering pennant
            z = (v - 0.5) * hz - 0.08 * u - 0.18 * u * u
            y = 0.28 * u * math.sin(u * 7.5 - ph)
            z += 0.07 * u * math.sin(u * 6 - ph + 1.0)
            # swallowtail notch
            if u > 0.82:
                d = (u - 0.82) / 0.18
                z = z * (1 + 0.0) + (0.5 - abs(v - 0.5)) * 0
            row.append(Vector((x, y, z)))
        rows.append(row)
    fm = mat(TEAL, pat='stripes', color2="#f2c84a", kind='soft', P=dict(fv=0.0, thr=0.5, weave=False), var=0.0, rim=0.5)
    o = grid_mesh("flag", rows, mat(TEAL, kind='soft', rim=0.5), outward=lambda c: (0, -1, 0))
    # gold stripe along the middle + tail tip coral
    mid = [[rows[k][j] + Vector((0, -0.006, 0)) for j in range(nu + 1)] for k in (2, 4)]
    mid = [[rows[2][j].lerp(rows[4][j], t) + Vector((0, -0.008, 0)) for j in range(nu + 1)] for t in (0.0, 1.0)]
    grid_mesh("flag_stripe", [[rows[3][j].lerp(rows[2][j], 0.55) + Vector((0, -0.01, 0)) for j in range(nu + 1)],
                              [rows[3][j].lerp(rows[4][j], 0.55) + Vector((0, -0.01, 0)) for j in range(nu + 1)]],
              mat("#f2c84a", kind='soft', rim=0.3), line=False, outward=lambda c: (0, -1, 0))
    tube("staff", [Vector((0.03, 0, -0.45)), Vector((0.03, 0, 0.45))], [0.03], brass(), seg=8, sub=1)
    ellipsoid("staffball", 0.06, brass(), loc=(0.03, 0, 0.48))


# ===================================================================== stations
def build_wheel_base():
    w = dwood()
    g = brass()
    box("ped", (0.3, 0.3, 0.78), mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.2), loc=(0, 0.05, 0.39), bevel=0.04)
    box("pedfoot", (0.6, 0.55, 0.12), w, loc=(0, 0.05, 0.06), bevel=0.03)
    ring_tube("pedband", (0, 0.05, 0.66), 0.22, 0.025, g, axis='z', seg=4, tseg=4, line=False)
    cyl("axle", 0.06, 0.06, 0.36, g, loc=(0, 0.18, 0.95), rot=(math.pi / 2, 0, 0), seg=14)
    # little binnacle compass on top (glass dome)
    cyl("binn", 0.15, 0.13, 0.1, g, loc=(0, 0.12, 0.78), seg=18)
    ellipsoid("binng", 0.12, mat("#9fd8e0", kind='soft', rim=0.8), loc=(0, 0.12, 0.88), scale=(1, 1, 0.6))


def build_wheel_disc(rot):
    w = mat("#c08048", pat='wood', P=dict(nu=10, fv=2), var=0.22, bump=0.35)
    g = brass()
    root = pivot("disc", (0, -0.22, 0.95))
    root.scale = (0.8, 0.8, 0.8)
    inner = pivot("discr", (0, 0, 0), root, rot=(0, rot, 0))
    ring_tube("rim", (0, 0, 0), 0.52, 0.055, w, inner, axis='y', seg=40, tseg=10)
    ring_tube("rim2", (0, 0, 0), 0.24, 0.035, w, inner, axis='y', seg=28, tseg=8)
    cyl("hub", 0.11, 0.11, 0.12, g, inner, loc=(0, 0.06, 0), rot=(math.pi / 2, 0, 0), seg=16)
    ellipsoid("hubcap", 0.07, g, inner, loc=(0, -0.08, 0), scale=(1, 0.6, 1))
    for k in range(8):
        a = TAU * k / 8
        c, s = math.cos(a), math.sin(a)
        tube(f"spoke{k}", [Vector((0.08 * c, 0, 0.08 * s)), Vector((0.52 * c, 0, 0.52 * s))], [0.03], w, inner, seg=7, sub=1)
        tube(f"handle{k}", [Vector((0.56 * c, 0, 0.56 * s)), Vector((0.66 * c, 0, 0.66 * s)), Vector((0.76 * c, 0, 0.76 * s))],
             [0.04, 0.05, 0.045], w, inner, seg=9, sub=2)
        ellipsoid(f"knob{k}", 0.05, w, inner, loc=(0.78 * c, 0, 0.78 * s))
        if k % 2 == 0:
            ellipsoid(f"stud{k}", 0.025, g, inner, loc=(0.52 * c, -0.05, 0.52 * s))
    # the top handle carries a brass "king spoke" marker
    ring_tube("king", (0, 0, 0.66), 0.05, 0.015, g, inner, axis='x', seg=12, tseg=4, line=False)


def build_cannon_base():
    w = mat("#8a5a36", pat='planks', color2="#5c3520", var=0.25, bump=0.4,
            P=dict(axis='x', along='z', fv=1 / 0.11, fu=0.0, butt=0.0, seam=0.12))
    loft("drum", [(0, 0.46, 0.46), (0.06, 0.47, 0.47), (0.28, 0.44, 0.44), (0.32, 0.4, 0.4)], w, seg=32, cap_top=True)
    ring_tube("dband", (0, 0, 0.1), 0.475, 0.03, brass(), axis='z', seg=32, tseg=5, line=False)
    ring_tube("dband2", (0, 0, 0.27), 0.448, 0.025, brass(), axis='z', seg=32, tseg=5, line=False)
    cyl("plate", 0.36, 0.34, 0.05, mat("#5a5866", rim=0.4), loc=(0, 0, 0.31), seg=28)
    for k in range(6):
        a = TAU * k / 6
        ellipsoid(f"rivet{k}", 0.025, brass(), loc=(0.3 * math.cos(a), 0.3 * math.sin(a), 0.36))


PIVOT_Z = 0.66


def build_barrel_group(angle_deg, yoke=True, elev=7.0):
    root = pivot("gun", (0, 0, 0), rot=(0, 0, math.radians(angle_deg)))
    if yoke:
        for s in (-1, 1):
            box(f"cheek{s}", (0.42, 0.09, 0.42), mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.2),
                parent=root, loc=(-0.02, s * 0.22, 0.52), bevel=0.04)
        box("yokebase", (0.5, 0.52, 0.08), dwood(), parent=root, loc=(-0.02, 0, 0.36), bevel=0.02)
    tp = pivot("tilt", (0, 0, PIVOT_Z), root, rot=(0, -math.radians(elev), 0))
    g = brass()
    gd = mat("#b8822e", metal=True, rim=0.6)
    loft("tube", [(-0.36, 0.0, 0.0), (-0.34, 0.1, 0.1), (-0.25, 0.155, 0.155), (0.2, 0.14, 0.14), (0.75, 0.115, 0.115),
                  (0.8, 0.13, 0.13), (0.86, 0.13, 0.13)], g, tp, rot=(0, math.pi / 2, 0), seg=24, cap_top=True)
    for x, r in ((-0.22, 0.165), (0.12, 0.15), (0.5, 0.13)):
        ring_tube(f"band{x}", (x, 0, 0), r, 0.022, gd, tp, axis='x', seg=24, tseg=5, line=False)
    ellipsoid("knob", 0.07, g, tp, loc=(-0.44, 0, 0))
    cyl("trun", 0.05, 0.05, 0.52, gd, tp, loc=(0, 0.26, 0), rot=(math.pi / 2, 0, 0), seg=10)
    # lantern muzzle: glass chamber + cage + cap
    cx = 0.86
    loft("mz_glass", [(0.0, 0.135, 0.135), (0.09, 0.16, 0.16), (0.24, 0.16, 0.16), (0.32, 0.12, 0.12)],
         glow("#ffe7a0", strength=2.4), tp, loc=(cx, 0, 0), rot=(0, math.pi / 2, 0), seg=20, cap_top=True, line=False)
    for k in range(6):
        a = TAU * k / 6
        tube(f"cage{k}", [Vector((cx + 0.02, 0.165 * math.cos(a), 0.165 * math.sin(a))),
                          Vector((cx + 0.17, 0.172 * math.cos(a), 0.172 * math.sin(a))),
                          Vector((cx + 0.3, 0.13 * math.cos(a), 0.13 * math.sin(a)))], [0.013], g, tp, seg=5, sub=2,
             line=False)
    ring_tube("mz_ring", (cx + 0.32, 0, 0), 0.125, 0.026, g, tp, axis='x', seg=20, tseg=5, line=False)
    ellipsoid("mz_core", 0.08, glow("#fff6d0", strength=3.2), tp, loc=(cx + 0.16, 0, 0), line=False)
    ellipsoid("mz_halo", 0.3, glow("#ffd27a", strength=1.0, alpha=0.3, soft=True), tp, loc=(cx + 0.18, 0, 0), line=False)
    return root


def build_rack():
    w = mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.2)
    top = wood("#c08048", "#6a3e22", axis='y', along='x', fv=1 / 0.15, fu=0.5, P=dict(seam=0.1, butt=0.05))
    for x in (-1.12, 1.12):
        box(f"end{x}", (0.12, 0.5, 0.82), mat(TEAL, pat='wood', P=dict(nu=4, fv=3), var=0.12), loc=(x, 0, 0.41), bevel=0.03)
        ellipsoid(f"endcap{x}", 0.07, brass(), loc=(x, 0, 0.86))
    box("shelf", (2.3, 0.46, 0.09), top, loc=(0, 0, 0.62), bevel=0.02)
    box("shelf2", (2.3, 0.4, 0.07), top, loc=(0, 0, 0.18), bevel=0.02)
    box("back", (2.3, 0.06, 0.3), w, loc=(0, 0.22, 0.42), bevel=0.015)
    slots = []
    for i in range(7):
        x = -0.9 + 0.3 * i
        ring_tube(f"cup{i}", (x, 0, 0.675), 0.12, 0.03, brass(), axis='z', seg=20, tseg=5, line=False)
        cyl(f"hole{i}", 0.11, 0.11, 0.01, mat("#3a2418", kind='flat', rim=0.0), loc=(x, 0, 0.666), seg=18)
        slots.append(proj(x, 0, 0.67 + 0.17))
    # a few spare balls on the lower shelf (grey, neutral)
    for i, x in enumerate((-0.7, -0.38, 0.5)):
        ellipsoid(f"spare{i}", 0.15, mat("#cfcbd6", kind='soft', rim=0.4), loc=(x, 0.0, 0.22 + 0.15))
    return [[round(a, 1), round(b, 1)] for a, b in slots]


def build_hatch(open_=False):
    w = dwood()
    lid = wood("#c08048", "#6a3e22", axis='x', along='y', fv=1 / 0.22, fu=0.0, P=dict(seam=0.08, butt=0.0))
    # coaming frame
    for (sx, sy, lx, ly) in ((1.34, 0.12, 0, -0.51), (1.34, 0.12, 0, 0.51), (0.12, 1.02, -0.67, 0), (0.12, 1.02, 0.67, 0)):
        box(f"coam{lx}{ly}", (sx, sy, 0.16), w, loc=(lx, ly, 0.08), bevel=0.02)
    if not open_:
        box("lid", (1.24, 0.92, 0.07), lid, loc=(0, 0, 0.15), bevel=0.015)
        for x in (-0.4, 0.4):
            box(f"strap{x}", (0.08, 0.94, 0.02), iron(), loc=(x, 0, 0.195), bevel=0.005)
        ring_tube("ring", (0, -0.28, 0.205), 0.1, 0.02, iron(), axis='z', seg=18, tseg=5, line=False)
        box("ringplate", (0.14, 0.1, 0.02), iron(), loc=(0, -0.18, 0.195))
    else:
        box("dark", (1.22, 0.9, 0.02), mat("#1e1428", kind='flat', rim=0.0, ao=0.0), loc=(0, 0, 0.02))
        # ladder top
        for x in (-0.25, 0.25):
            box(f"lrail{x}", (0.06, 0.06, 0.4), w, loc=(x, 0.1, -0.05))
        box("lrung", (0.56, 0.05, 0.04), w, loc=(0, 0.1, 0.08))
        hinge = pivot("hinge", (0, 0.5, 0.15), rot=(math.radians(-105), 0, 0))
        box("lid", (1.24, 0.92, 0.07), lid, hinge, loc=(0, -0.46, 0.0), bevel=0.015)
        for x in (-0.4, 0.4):
            box(f"strap{x}", (0.08, 0.94, 0.02), iron(), hinge, loc=(x, -0.46, 0.045), bevel=0.005)
    for o in list(bpy.context.scene.objects):
        if o.name.startswith("hole") and o.type == 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)


# ===================================================================== props
def crate(name, size, loc=(0, 0, 0), rot=0.0, color="#c08048", emblem=False):
    root = pivot(name, loc, rot=(0, 0, rot))
    sx, sy, sz = size
    body = wood(color, "#6a3e22", axis='z', along='x', fv=1 / 0.18, fu=0.0, P=dict(seam=0.1, butt=0.0, seed=len(name)))
    box(name + "_b", (sx, sy, sz), body, root, loc=(0, 0, sz / 2), bevel=0.02)
    fr = mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3), var=0.2)
    t = 0.07
    for (px, py) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        box(name + f"_e{px}{py}", (t, t, sz + 0.01), fr, root, loc=(px * (sx / 2 - t / 2 + 0.01), py * (sy / 2 - t / 2 + 0.01), sz / 2), bevel=0.01)
    for z in (0.04, sz - 0.04):
        box(name + f"_hx{z}", (sx + 0.02, t, t), fr, root, loc=(0, -sy / 2 + t / 2 - 0.01, z), bevel=0.01)
        box(name + f"_hy{z}", (t, sy + 0.02, t), fr, root, loc=(-sx / 2 + t / 2 - 0.01, 0, z), bevel=0.01)
        box(name + f"_hx2{z}", (sx + 0.02, t, t), fr, root, loc=(0, sy / 2 - t / 2 + 0.01, z), bevel=0.01)
        box(name + f"_hy2{z}", (t, sy + 0.02, t), fr, root, loc=(sx / 2 - t / 2 + 0.01, 0, z), bevel=0.01)
    if emblem:   # painted envelope (mail crate)
        cz = sz / 2
        y0 = -sy / 2 - 0.012
        env = [Vector((-0.22, y0, cz - 0.14)), Vector((0.22, y0, cz - 0.14)), Vector((0.22, y0, cz + 0.14)), Vector((-0.22, y0, cz + 0.14))]
        o = mesh_obj(name + "_env", env, [(0, 1, 2, 3)], mat("#f6ecd4", kind='soft', rim=0.2), root, smooth=False, recalc=False, line=False)
        fix_normals_out(o, lambda c: (0, -1, 0))
        tube(name + "_flap", [Vector((-0.2, y0 - 0.004, cz + 0.12)), Vector((0, y0 - 0.004, cz - 0.02)), Vector((0.2, y0 - 0.004, cz + 0.12))],
             [0.014], mat(CORAL, kind='soft'), root, seg=5, sub=1, line=False)
        ellipsoid(name + "_seal", 0.045, mat(CORAL, kind='soft'), root, loc=(0, y0 - 0.01, cz - 0.01), scale=(1, 0.3, 1))
    return root


def build_barrel():
    st = wood("#b87a42", "#5c3520", axis='x', along='z', fv=1 / 0.11, fu=0.0, P=dict(seam=0.12, butt=0.0))
    rings = [(0, 0.27, 0.27), (0.2, 0.32, 0.32), (0.42, 0.335, 0.335), (0.64, 0.32, 0.32), (0.84, 0.27, 0.27)]
    loft("staves", rings, st, seg=36, cap_bot=True)
    for z, r in ((0.08, 0.29), (0.3, 0.33), (0.56, 0.33), (0.77, 0.29)):
        ring_tube(f"hoop{z}", (0, 0, z), r + 0.012, 0.022, iron(), axis='z', seg=36, tseg=5, line=False)
    cyl("water", 0.25, 0.25, 0.01, mat("#4fb8d0", kind='soft', rim=0.9), loc=(0, 0, 0.78), seg=30)
    ring_tube("waterhl", (-0.06, 0.04, 0.795), 0.1, 0.012, glow("#d8f6ff", strength=1.2), axis='z', seg=16, tseg=4, line=False)
    # ladle hanging on the rim
    tube("ladle", [Vector((0.18, -0.12, 0.98)), Vector((0.25, -0.16, 0.86)), Vector((0.3, -0.19, 0.6))], [0.018],
         mat("#8a5a36"), seg=6, sub=3)


def build_bucket(full=True):
    st = wood("#c08048", "#6a3e22", axis='x', along='z', fv=1 / 0.08, fu=0.0, P=dict(seam=0.12, butt=0.0))
    loft("bk", [(0, 0.15, 0.15), (0.3, 0.19, 0.19)], st, seg=28, cap_bot=True)
    for z, r in ((0.05, 0.158), (0.24, 0.185)):
        ring_tube(f"bh{z}", (0, 0, z), r + 0.008, 0.016, iron(), axis='z', seg=28, tseg=4, line=False)
    if full:
        cyl("bw", 0.17, 0.17, 0.01, mat("#4fb8d0", kind='soft', rim=0.9), loc=(0, 0, 0.26), seg=24)
    pts = [Vector((0.19 * math.cos(a), 0, 0.29 + 0.22 * math.sin(a))) for a in [i * math.pi / 12 for i in range(13)]]
    tube("handle", pts, [0.014], rope_mat(), seg=6, sub=1, line=False)


def build_plank(n=1):
    for i in range(n):
        rot = (i % 2) * 0.12 - 0.06 + (0.4 if n > 1 and i % 2 else 0.0) * 0
        box(f"pl{i}", (1.15, 0.26, 0.06),
            wood("#cf9a5a", "#7a4a2a", axis='y', along='x', fv=1 / 0.26, fu=0.3, P=dict(seam=0.0, butt=0.0, seed=i + 1.3)),
            loc=(0.03 * (i % 3) - 0.03, 0.04 * ((i * 7) % 3) - 0.04, 0.03 + 0.062 * i), rot=(0, 0, rot if n > 1 else 0.0),
            bevel=0.012)
        for x in (-0.5, 0.5):
            ellipsoid(f"nail{i}{x}", 0.016, mat("#5a5866"), loc=(x, -0.06, 0.062 + 0.062 * i), scale=(1, 1, 0.4), line=False)
    if n > 1:
        for x in (-0.32, 0.32):
            ring_tube(f"tie{x}", (x, 0, 0.06 * n / 2 + 0.02), 0.17, 0.018, rope_mat(), axis='x', seg=20, tseg=5, line=False)


def build_ball():
    ellipsoid("ball", 0.17, mat("#f2f0f6", kind='soft', rim=0.6, ao=0.3), loc=(0, 0, 0.17), seg=28, rings=18)
    ring_tube("ballband", (0, 0, 0.17), 0.171, 0.012, mat("#c8c4d0", kind='soft', rim=0.2), axis='y', seg=30, tseg=4, line=False)
    ellipsoid("ballhl", 0.045, mat("#ffffff", kind='flat', rim=0.0), loc=(-0.07, -0.1, 0.26), scale=(1, 0.5, 0.7), line=False)


def build_anchor():
    ir = mat("#4f4b5c", kind='cloth', rim=0.6, pat='noise', P=dict(scale=30), var=0.1)
    tube("shank", [Vector((0, 0, 0.18)), Vector((0, 0, 1.2))], [0.06, 0.05], ir, seg=10, sub=1)
    arc = [Vector((0.48 * math.sin(a), 0, 0.5 - 0.42 * math.cos(a) + 0.1)) for a in [(-1.25 + 2.5 * i / 16) for i in range(17)]]
    tube("arms", arc, [0.065, 0.05, 0.065], ir, seg=10, sub=1)
    for s in (-1, 1):
        p = arc[0] if s < 0 else arc[-1]
        ellipsoid(f"fluke{s}", 0.11, ir, loc=(p.x + s * 0.02, 0, p.z + 0.1), scale=(0.6, 0.35, 1.0),
                  rot=(0, s * 0.5, 0))
    box("stock", (0.62, 0.09, 0.09), mat("#8a5a36", pat='wood', P=dict(nu=4, fv=3)), loc=(0, 0, 1.08), bevel=0.03)
    ring_tube("aring", (0, 0, 1.32), 0.11, 0.03, ir, axis='y', seg=20, tseg=6)
    ellipsoid("crown", 0.09, ir, loc=(0, 0, 0.16))
    # rope tied to the ring, coiled at the base
    spiral_coil("arope", (0.32, 0.25, 0.0), 0.1, 0.28, 2.0, 0.04, rope_mat())
    tube("arope2", [Vector((0.1, 0, 1.3)), Vector((0.35, 0.1, 0.9)), Vector((0.45, 0.2, 0.3)), Vector((0.5, 0.3, 0.06))],
         [0.035], rope_mat(), seg=8, sub=4)


# ===================================================================== fx (blender)
def flame_frame(i):
    rnd = random.Random(100 + i)
    ph = TAU * i / 6
    layers = [("#e8452e", 1.0, 0.0), ("#ff8a2a", 0.74, -0.06), ("#ffd04a", 0.48, -0.12), ("#fff4c0", 0.25, -0.17)]
    for li, (col, k, dy) in enumerate(layers):
        for t in range(3 if li < 2 else 1):
            cx = (t - 1) * 0.17 * k if li < 2 else 0.0
            h = (1.0 if t == 1 or li >= 2 else 0.68) * k * (1 + 0.14 * math.sin(ph + t * 2.1 + li))
            sway = 0.16 * math.sin(ph + t * 1.7 + li * 0.6)

            def deform(p, h=h, sway=sway):
                z = (p.z + 1) / 2          # 0..1 bottom -> tip
                # teardrop: round belly low down, long licking tip
                w = (math.sin(math.pi * min(1.0, z * 1.6 + 0.08)) if z < 0.3 else (1 - (z - 0.3) / 0.7) ** 1.3)
                w = max(0.0, w)
                return Vector((p.x * w + sway * z ** 2 * 1.6, p.y * w * 0.7, z * h * 5.0))
            blob(f"fl{li}{t}", 0.25 * (0.75 + 0.25 * k), glow(col, strength=1.6 + 0.4 * li), loc=(cx, dy, 0.0),
                 deform=deform, seg=20, rings=24, line=False)
    # embers
    for e in range(3):
        a = rnd.random()
        ellipsoid(f"em{e}", 0.03, glow("#ffb040", strength=2.5), loc=(rnd.uniform(-0.3, 0.3), -0.2,
                  0.75 + ((i / 6 + a) % 1.0) * 0.7), line=False)


def leak_frame(i):
    # splintered hole in the deck + bubbling water spout
    dk = mat("#22162e", kind='flat', rim=0.0, ao=0.0)
    hole = [Vector((0.34 * math.cos(a) * (1 + 0.18 * math.sin(a * 5)), 0.26 * math.sin(a) * (1 + 0.18 * math.cos(a * 3)), 0.01))
            for a in [TAU * k / 18 for k in range(18)]]
    o = mesh_obj("hole", [Vector((0, 0, 0.01))] + hole, [(0, 1 + k, 1 + (k + 1) % 18) for k in range(18)], dk, smooth=False,
                 recalc=False, line=False)
    fix_normals_out(o, lambda c: (0, 0, 1))
    sp = mat("#d9a764", pat='wood', P=dict(nu=4, fv=3))
    rnd = random.Random(7)
    for k in range(7):
        a = TAU * k / 7 + 0.3
        r = 0.3 + 0.04 * rnd.random()
        tube(f"spl{k}", [Vector((r * math.cos(a), r * 0.78 * math.sin(a), 0.01)),
                         Vector(((r + 0.12) * math.cos(a + 0.12), (r + 0.12) * 0.78 * math.sin(a + 0.12), 0.07 + 0.04 * rnd.random()))],
             [0.035, 0.008], sp, seg=5, sub=1)
    ph = TAU * i / 4
    water = mat("#5fc4dc", kind='soft', rim=0.9)
    hi = glow("#e8fbff", strength=1.1)
    # puddle
    cyl("puddle", 0.62 + 0.04 * math.sin(ph), 0.62, 0.006, mat("#5fb8d4", kind='flat', rim=0.0, ao=0.0), loc=(0, 0, 0.0), seg=28,
        line=False)
    # spout column
    hgt = 0.42 + 0.12 * math.sin(ph)
    pts = [Vector((0.02 * math.sin(ph + z * 6), 0, z)) for z in (0.0, hgt * 0.4, hgt * 0.8, hgt)]
    tube("spout", pts, [0.16, 0.12, 0.09, 0.03], water, seg=12, sub=3)
    ellipsoid("crown", 0.12, water, loc=(0, 0, hgt), scale=(1.2, 1.2, 0.7))
    for k in range(6):
        a = TAU * k / 6 + ph * 0.5
        t = ((i / 4) + k / 6) % 1.0
        r = 0.15 + 0.35 * t
        z = hgt * (1 - (2 * t - 0.4) ** 2) + 0.05
        ellipsoid(f"drop{k}", 0.045 * (1 - 0.4 * t), water, loc=(r * math.cos(a), r * 0.8 * math.sin(a), max(0.03, z)))
    ring_tube("ripple", (0, 0, 0.012), 0.3 + 0.25 * ((i / 4) % 1), 0.014, hi, axis='z', seg=28, tseg=4, line=False)
    ellipsoid("spouthl", 0.04, hi, loc=(-0.05, -0.08, hgt * 0.6), scale=(0.6, 0.6, 1.8), line=False)


# ===================================================================== groups
def render_group(job, g):
    if g == 'mast':
        job.scene()
        top = build_mast()
        job.shoot("mast", (200, 512), (100, 482), extra=dict(topPx=list(proj(0, 0, top + 0.1)),
                                                             nestPx=list(proj(0, 0, 7.3))), shadow=[22, 11, 4, 0.3])
    elif g == 'sails':
        for st in (0, 1, 2):
            job.scene()
            build_sails(st)
            job.shoot(f"sail_{st}", (1000, 470), (390, 466), line_t=0.012,
                      extra=dict(note="anchor = mast foot (same as mast); draw as a semi-transparent front layer"))
    elif g == 'flags':
        for i in range(4):
            job.scene()
            build_flag(i)
            job.shoot(f"flag_{i}", (180, 90), (160, 45), line_t=0.01,
                      extra=dict(note="anchor = staff centre; place at mast.topPx"))
        job.meta["_anims"] = job.meta.get("_anims", {})
        job.meta["_anims"]["flag"] = {"frames": [f"flag_{i}" for i in range(4)], "frameRate": 7, "repeat": -1}
        job.save()
    elif g == 'stations':
        job.scene()
        build_wheel_base()
        build_wheel_disc(0.0)
        job.shoot("wheel", (160, 160), (80, 138), shadow=[24, 12, 4, 0.3],
                  extra=dict(hubPx=list(proj(0, -0.22, 0.95)), note="disc faces the camera; helmsman stands behind (y+0.6)"))
        job.scene()
        build_wheel_base()
        job.shoot("wheel_base", (160, 160), (80, 138), shadow=[24, 12, 4, 0.3])
        for k in range(8):
            job.scene()
            build_wheel_disc(math.radians(45.0 * k / 8))
            job.shoot(f"wheel_disc_{k}", (160, 160), (80, 138))
        job.scene()
        build_cannon_base()
        job.shoot("cannon_base", (96, 80), (48, 58), shadow=[30, 16, 4, 0.32],
                  extra=dict(pivotPx=list(proj(0, 0, PIVOT_Z))))
        job.scene()
        build_barrel_group(0, yoke=False, elev=0)
        bpy.data.objects["gun"].location = (0, 0, -PIVOT_Z)
        job.shoot("cannon_barrel", (176, 64), (64, 32),
                  extra=dict(note="points +x (screen right); anchor = trunnion pivot; rotate in 2D"))
        for k in range(16):
            job.scene()
            build_barrel_group(22.5 * k)
            job.shoot(f"cannon_barrel_{k:02d}", (176, 150), (88, 100),
                      extra=dict(angleDeg=22.5 * k, note="world aim angle (0=+x bow, 90=+y far); anchor = station ground point"))
        job.scene()
        slots = build_rack()
        job.shoot("rack", (160, 100), (80, 74), shadow=[64, 10, 4, 0.3], extra=dict(slotsPx=slots))
        job.scene()
        build_hatch(False)
        job.shoot("hatch", (100, 70), (50, 38))
        job.scene()
        build_hatch(True)
        job.shoot("hatch_open", (100, 100), (50, 68))
    elif g == 'props':
        job.scene()
        crate("ca", (0.74, 0.74, 0.7))
        job.shoot("crate_a", (90, 100), (45, 72), shadow=[24, 13, 4, 0.3])
        job.scene()
        crate("cb1", (0.74, 0.7, 0.62), rot=0.05)
        crate("cb2", (0.52, 0.5, 0.46), loc=(0.05, 0.02, 0.62), rot=0.35, color="#b87a42")
        job.shoot("crate_b", (90, 120), (45, 92), shadow=[24, 13, 4, 0.3])
        job.scene()
        crate("cc", (1.2, 0.62, 0.56), emblem=True, color="#c9904e")
        job.shoot("crate_c", (110, 90), (55, 64), shadow=[36, 12, 4, 0.3])
        job.scene()
        build_barrel()
        job.shoot("barrel", (70, 90), (35, 70), shadow=[20, 11, 4, 0.3])
        job.scene()
        build_bucket(True)
        job.shoot("bucket", (40, 44), (20, 34), shadow=[11, 6, 2, 0.3])
        job.scene()
        build_bucket(False)
        job.shoot("bucket_empty", (40, 44), (20, 34), shadow=[11, 6, 2, 0.3])
        job.scene()
        build_plank(1)
        job.shoot("plank", (80, 40), (40, 24))
        job.scene()
        build_plank(5)
        job.shoot("plank_stack", (90, 60), (45, 40), shadow=[34, 10, 3, 0.3])
        job.scene()
        build_ball()
        job.shoot("ball", (32, 32), (16, 26), extra=dict(note="neutral white: setTint(ammo colour)"))
        job.scene()
        build_anchor()
        job.shoot("anchor", (80, 90), (40, 76), shadow=[22, 9, 3, 0.3])
    elif g == 'fx':
        for i in range(6):
            job.scene()
            flame_frame(i)
            job.shoot(f"flame_{i}", (90, 110), (45, 96), lines=False)
        for i in range(4):
            job.scene()
            leak_frame(i)
            job.shoot(f"leak_{i}", (90, 70), (45, 48), line_t=0.008)
        job.meta.setdefault("_anims", {})
        job.meta["_anims"]["flame"] = {"frames": [f"flame_{i}" for i in range(6)], "frameRate": 12, "repeat": -1}
        job.meta["_anims"]["leak"] = {"frames": [f"leak_{i}" for i in range(4)], "frameRate": 8, "repeat": -1}
        job.meta["_anims"]["wheel_spin"] = {"frames": [f"wheel_disc_{i}" for i in range(8)], "frameRate": 12, "repeat": -1}
        job.save()


