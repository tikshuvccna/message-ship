"""Creatures of the valley (v2). Each creature embodies one networking idea.

blender -b --python v2_creatures.py -- <name|all|small|legend> <rawdir>
Writes <rawdir>/creatures/<name>/<anim>_<DIR>_<i>.png (sprite, SSAA 4) and <name>_codex.png (SSAA 2).
Creatures face -Y at rotation 0. Small creatures are rendered at CPPU px per unit (1.5x the world
scale, so they read well); setScale(0.667) puts them at exact world scale.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

from v2lib import *
from v2_parts import darker, lighter

CPPU = 84.0
CDIRS = [("S", 0), ("SE", 45), ("E", 90), ("N", 180)]


# ---------------------------------------------------------------- helpers
def eye(parent, loc, r, iris="#3a2a1a", rot=(0, 0, 0), look=(0.0, 0.0), sclera="#fbf4ea", glowy=None):
    e = pivot("eye", loc, parent, rot=rot)
    ellipsoid("sclera", r, mat(sclera, kind='soft', rim=0.2), e, scale=(1, 0.62, 1.1), seg=18, rings=12)
    lx, lz = look
    if glowy:
        ellipsoid("iris", r * 0.62, glow(glowy, 2.0), e, loc=(lx * r * 0.3, -r * 0.45, lz * r * 0.3), scale=(1, 0.4, 1.05),
                  seg=16, rings=10)
    else:
        ellipsoid("iris", r * 0.66, mat(iris, kind='soft', rim=0, line=False), e, loc=(lx * r * 0.3, -r * 0.42, lz * r * 0.3),
                  scale=(1, 0.38, 1.05), seg=16, rings=10)
        ellipsoid("pupil", r * 0.38, mat("#140c10", kind='flat', rim=0, line=False), e,
                  loc=(lx * r * 0.32, -r * 0.55, lz * r * 0.32), scale=(1, 0.3, 1.05), seg=12, rings=8)
    ellipsoid("hl", r * 0.2, glow("#ffffff", 1.0), e, loc=(-r * 0.28 + lx * r * 0.3, -r * 0.66, r * 0.32), seg=8, rings=6)
    ellipsoid("hl2", r * 0.09, glow("#ffffff", 1.0), e, loc=(r * 0.25, -r * 0.64, -r * 0.25), seg=6, rings=4)
    return e


def closed_eye(parent, loc, r, color="#2a1a24", up=False):
    m = mat(color, kind='flat', rim=0, ao=0, line=False)
    c = 1 if up else -1
    pts = [Vector((loc[0] - r, loc[1], loc[2])), Vector((loc[0], loc[1] - r * 0.15, loc[2] + c * r * 0.45)),
           Vector((loc[0] + r, loc[1], loc[2]))]
    return tube("ceye", pts, [r * 0.18, r * 0.22, r * 0.18], m, parent, seg=6, sub=4)


def smile(parent, loc, w, color="#5a2a30", curve=0.4):
    m = mat(color, kind='flat', rim=0, ao=0, line=False)
    pts = [Vector((loc[0] - w, loc[1], loc[2] + w * curve)), Vector((loc[0], loc[1] - w * 0.1, loc[2])),
           Vector((loc[0] + w, loc[1], loc[2] + w * curve))]
    return tube("smile", pts, [w * 0.12, w * 0.16, w * 0.12], m, parent, seg=6, sub=4)


def blush(parent, loc, r):
    return ellipsoid("blush", r, mat("#f08a8a", kind='soft', rim=0, line=False), parent, loc=loc, scale=(1, 0.3, 0.6), seg=10, rings=6)


def leg4(root, body_z, pts, r, m, foot_m=None):
    L = {}
    for nm, (x, y) in pts.items():
        p = pivot("leg" + nm, (x, y, body_z), root)
        loft("leg", [(0, r, r), (-body_z * 0.6, r * 0.85, r * 0.85), (-body_z + r * 0.6, r * 0.8, r * 0.8)], m, p, seg=12,
             cap_bot=True)
        ellipsoid("paw", r * 1.1, foot_m or m, p, loc=(0, -r * 0.3, -body_z + r * 0.7), scale=(1, 1.3, 0.7), seg=12, rings=8)
        L[nm] = p
    return L


def walk4(L, ph, amp=0.45):
    for nm, off in (("FL", 0), ("BR", 0), ("FR", math.pi), ("BL", math.pi)):
        if nm in L:
            L[nm].rotation_euler = (amp * math.sin(ph + off), 0, 0)


class C:
    """Creature holder: root pivot, pose(anim, i, n), meta."""

    def __init__(self, name):
        self.name = name
        self.root = pivot("root")
        self.body = pivot("cbody", parent=self.root)
        self.lights = []
        self.meta = {}
        self.fly = 0.0

    def pose(self, anim, i, n):
        pass


# ---------------------------------------------------------------- 1 paper crane
def paper_crane():
    c = C("paper_crane")
    paper = mat("#f6efe0", pat='weave', P=dict(nu=10, fv=40), kind='cloth', var=0.08, rim=0.6)
    paper2 = mat("#d8e8e4", pat='weave', kind='cloth', var=0.08, rim=0.6)
    b = pivot("b", (0, 0, 0.55), c.body)
    # faceted origami body: diamond
    v = [(0, -0.22, 0.0), (0, 0.22, 0.02), (-0.07, 0, 0.0), (0.07, 0, 0.0), (0, 0, 0.1), (0, 0, -0.08)]
    f = [(0, 2, 4), (0, 4, 3), (1, 4, 2), (1, 3, 4), (0, 5, 2), (0, 3, 5), (1, 2, 5), (1, 5, 3)]
    mesh_obj("cbody", v, f, paper, b, smooth=False)
    # neck + head (folded point), tail
    mesh_obj("neck", [(0, -0.18, 0.0), (-0.025, -0.16, 0.04), (0.025, -0.16, 0.04), (0, -0.33, 0.2)],
             [(0, 1, 3), (0, 3, 2), (1, 2, 3)], paper, b, smooth=False)
    mesh_obj("head", [(0, -0.33, 0.2), (-0.02, -0.31, 0.18), (0.02, -0.31, 0.18), (0, -0.42, 0.17)],
             [(0, 1, 3), (0, 3, 2), (1, 2, 3)], paper2, b, smooth=False)
    mesh_obj("tail", [(0, 0.18, 0.0), (-0.025, 0.16, 0.04), (0.025, 0.16, 0.04), (0, 0.36, 0.24)],
             [(0, 1, 3), (0, 3, 2), (1, 2, 3)], paper, b, smooth=False)
    ellipsoid("ceye", 0.012, mat("#2a1a24", kind='flat', line=False), b, loc=(0.018, -0.34, 0.2), seg=6, rings=4)
    ellipsoid("ceye2", 0.012, mat("#2a1a24", kind='flat', line=False), b, loc=(-0.018, -0.34, 0.2), seg=6, rings=4)
    W = {}
    for s in (-1, 1):
        w = pivot("wing", (s * 0.05, 0, 0.05), b)
        mesh_obj("wingA", [(0, -0.12, 0), (0, 0.12, 0), (s * 0.34, 0.02, 0.06), (s * 0.18, -0.05, 0.02)],
                 [(0, 3, 2, 1)], paper, w, smooth=False, recalc=False)
        mesh_obj("wingB", [(0, -0.12, -0.003), (0, 0.12, -0.003), (s * 0.34, 0.02, 0.057), (s * 0.18, -0.05, 0.017)],
                 [(0, 1, 2, 3)], paper2, w, smooth=False, recalc=False)
        W[s] = w
    # glowing envelope in the beak
    env = pivot("env", (0, -0.44, 0.13), b, rot=(0, 0, 0.2))
    box("envelope", (0.12, 0.012, 0.08), mat("#fff4d6", kind='soft', rim=0.5), env, bevel=0.004)
    mesh_obj("flap", [(-0.06, -0.008, 0.04), (0.06, -0.008, 0.04), (0, -0.008, -0.005)], [(0, 2, 1)],
             mat("#f0d8a0", kind='soft'), env, smooth=False, recalc=False, line=False)
    ellipsoid("seal", 0.014, glow("#35d3b0", 3), env, loc=(0, -0.012, 0.0), scale=(1, 0.4, 1), seg=8, rings=6)
    ellipsoid("envhalo", 0.11, glow("#9ffff0", 1.2, alpha=0.13, soft=True), env, seg=12, rings=8)

    def pose(anim, i, n):
        ph = TAU * i / n
        fl = 0.55 * math.sin(ph * (1 if anim == 'idle' else 2))
        for s, w in W.items():
            w.rotation_euler = (0, -s * fl, 0)
        b.location.z = 0.55 + 0.03 * math.sin(ph)
        b.rotation_euler = (0.12 if anim == 'walk' else 0.0, 0, 0)
    c.pose = pose
    c.meta = dict(name_he="עגורן הנייר", concept="חבילת מידע (Packet): עגורן נייר שמוביל מעטפה אחת מהמוסר אל היעד; בלי כתובת על המעטפה הוא לא יודע לאן לעוף.",
                  move="flies", hover=0.55)
    return c


# ---------------------------------------------------------------- 2 lantern moth
def lantern_moth():
    c = C("lantern_moth")
    fur = mat("#e8d4b0", pat='fur', P=dict(scale=90), kind='cloth', var=0.25, rim=0.6)
    b = pivot("b", (0, 0, 0.6), c.body)
    blob("thorax", 0.09, fur, b, scale=(1, 1.1, 1), seg=20, rings=14)
    blob("abd", 0.08, mat("#ffcf7a", pat='stripes', color2="#e8a040", P=dict(nu=8, fv=60, thr=0.6)), b, loc=(0, 0.13, -0.03),
         scale=(0.9, 1.5, 0.9), seg=20, rings=14)
    ellipsoid("abdglow", 0.12, glow("#ffd27a", 1.5, alpha=0.13, soft=True), b, loc=(0, 0.17, -0.03), seg=12, rings=8)
    hd = pivot("h", (0, -0.1, 0.02), b)
    ellipsoid("head", 0.07, fur, hd, seg=16, rings=12)
    for s in (-1, 1):
        eye(hd, (s * 0.04, -0.04, 0.01), 0.032, iris="#2a1a10", rot=(0, 0, -s * 0.5))
        tube("ant", [Vector((s * 0.02, -0.04, 0.05)), Vector((s * 0.08, -0.1, 0.16)), Vector((s * 0.14, -0.08, 0.22))],
             [0.007, 0.005], mat("#8a6a4a"), hd, seg=5, sub=3)
        for k in range(5):
            t = 0.3 + 0.14 * k
            p = Vector((s * (0.02 + 0.12 * t), -0.04 - 0.06 * t, 0.05 + 0.17 * t))
            ellipsoid("plume", 0.02, fur, hd, loc=p, scale=(0.4, 0.4, 1.0), rot=(0.3, s * 0.6, 0), seg=6, rings=4, line=False)
    W = {}
    wm = mat("#c8a0e0", pat='dots', color2="#ffe08a", P=dict(nu=3, fv=6, rad=0.22), kind='soft', var=0.1, rim=0.6)
    for s in (-1, 1):
        w = pivot("wing", (s * 0.06, 0, 0.04), b)
        blob("wingF", 0.2, wm, w, loc=(s * 0.17, -0.04, 0.03), scale=(1.0, 0.75, 0.06), seg=24, rings=10)
        blob("wingB", 0.14, wm, w, loc=(s * 0.12, 0.12, 0.0), scale=(1.0, 0.8, 0.06), seg=20, rings=10)
        ellipsoid("spot", 0.04, glow("#ffe08a", 1.4), w, loc=(s * 0.22, -0.05, 0.05), scale=(1, 1, 0.3), seg=10, rings=6)
        W[s] = w
    # the light it always follows
    ellipsoid("guide", 0.03, glow("#fff2c0", 4), c.root, loc=(0, -0.42, 0.9), seg=10, rings=8)
    ellipsoid("guidehalo", 0.1, glow("#ffe08a", 1.5, alpha=0.13, soft=True), c.root, loc=(0, -0.42, 0.9), seg=12, rings=8)

    def pose(anim, i, n):
        ph = TAU * i / n
        fl = 0.7 * math.sin(ph * (1 if anim == 'idle' else 2))
        for s, w in W.items():
            w.rotation_euler = (0, -s * fl, 0)
        b.location.z = 0.6 + 0.04 * math.sin(ph + 1)
        b.rotation_euler = (-0.25, 0, 0)
    c.pose = pose
    c.meta = dict(name_he="עש הפנס", concept="שידור לכולם (Broadcast): אות אחד נשלח לכל מי שברשת, וכל העשים פונים אל אותו אור.",
                  move="flies", hover=0.6)
    return c


# ---------------------------------------------------------------- 3 echo parrot
def echo_parrot():
    c = C("echo_parrot")
    b = pivot("b", (0, 0, 0.0), c.body)
    red = mat("#e04a4a", pat='fur', P=dict(scale=60), var=0.15)
    blob("pbody", 0.2, red, b, loc=(0, 0.02, 0.3), scale=(0.95, 0.9, 1.15),
         deform=lambda p: Vector((p.x, p.y + 0.15 * max(0, p.z), p.z)), seg=28, rings=18)
    blob("belly", 0.15, mat("#ffd25a", pat='fur', P=dict(scale=60)), b, loc=(0, -0.08, 0.26), scale=(0.9, 0.6, 1.1), seg=22, rings=14)
    hd = pivot("h", (0, -0.04, 0.55), b)
    blob("phead", 0.15, red, hd, seg=24, rings=16)
    beak = mat("#3a3040", metal=True)
    blob("beak", 0.06, beak, hd, loc=(0, -0.15, -0.02), scale=(0.8, 1.0, 1.2),
         deform=lambda p: Vector((p.x, p.y - 0.3 * max(0, -p.z) ** 0.5 * 0, p.z - 0.4 * max(0, -p.y))), seg=14, rings=10)
    ellipsoid("cheekw", 0.07, mat("#fbf4ea", kind='soft'), hd, loc=(0.08, -0.08, 0.0), scale=(0.5, 0.6, 0.8))
    ellipsoid("cheekw2", 0.07, mat("#fbf4ea", kind='soft'), hd, loc=(-0.08, -0.08, 0.0), scale=(0.5, 0.6, 0.8))
    for s in (-1, 1):
        eye(hd, (s * 0.08, -0.1, 0.04), 0.035, iris="#e8b04a", rot=(0, 0, -s * 0.5))
    for k in range(3):
        tube("crest", [Vector((0, 0.0, 0.13)), Vector((0, 0.05 + 0.03 * k, 0.24 + 0.02 * k)), Vector((0, 0.12 + 0.04 * k, 0.28))],
             [0.03, 0.02, 0.006], mat(["#ffd25a", "#35b3e0", "#e04a4a"][k]), hd, seg=8, sub=3)
    W = {}
    for s in (-1, 1):
        w = pivot("wing", (s * 0.17, 0.02, 0.38), b)
        blob("pwing", 0.14, mat("#35b3e0", pat='stripes', color2="#2a6ab8", P=dict(nu=10, fv=50, thr=0.6)), w,
             loc=(s * 0.02, 0.05, -0.08), scale=(0.35, 0.8, 1.2), seg=18, rings=12)
        W[s] = w
    tube("ptail", [Vector((0, 0.15, 0.18)), Vector((0, 0.3, 0.05)), Vector((0, 0.38, -0.05))], [0.06, 0.05, 0.03],
         mat("#35b3e0", pat='stripes', color2="#2a6ab8", P=dict(nu=10, fv=50, thr=0.6)), b, seg=10, flat=0.3)
    F = {}
    for s in (-1, 1):
        f = pivot("foot", (s * 0.07, -0.02, 0.1), b)
        tube("pleg", [Vector((0, 0, 0)), Vector((0, -0.01, -0.08))], [0.02], beak, f, seg=6, sub=1)
        for t in (-0.4, 0, 0.4):
            tube("toe", [Vector((0, -0.01, -0.08)), Vector((math.sin(t) * 0.05, -0.05, -0.095))], [0.012], beak, f, seg=5, sub=1)
        F[s] = f
    # "echo" sound rings
    rings = []
    for k in range(2):
        r = tube("echo", [Vector((0.08 * math.cos(a), -0.3 - 0.06 * k, 0.55 + 0.08 * math.sin(a)))
                          for a in [-1.2 + 2.4 * j / 10 for j in range(11)]], [0.008], glow("#ffd25a", 2.0), b, seg=5, sub=1)
        rings.append(r)

    def pose(anim, i, n):
        ph = TAU * i / n
        hop = abs(math.sin(ph)) * (0.1 if anim == 'walk' else 0.0)
        b.location.z = hop
        b.scale = (1 + 0.03 * math.cos(2 * ph), 1, 1 - 0.03 * math.cos(2 * ph))
        hd.rotation_euler = (0.15 * math.sin(ph), 0, 0.1 * math.sin(ph * 0.5))
        for s, w in W.items():
            w.rotation_euler = (0, -s * (0.3 * abs(math.sin(ph)) if anim == 'walk' else 0.05 * math.sin(ph)), 0)
        for k, r in enumerate(rings):
            r.hide_render = (i + k) % 2 == 1
    c.pose = pose
    c.meta = dict(name_he="תוכי ההד", concept="רכזת (Hub): כל מה שהוא שומע הוא חוזר עליו לכולם בבת אחת, בלי לבדוק למי ההודעה מיועדת.",
                  move="hops")
    return c


# ---------------------------------------------------------------- 4 librarian owl
def librarian_owl():
    c = C("librarian_owl")
    b = pivot("b", parent=c.body)
    fm = mat("#9a7a5a", pat='fur', P=dict(scale=70), var=0.2)
    blob("obody", 0.24, fm, b, loc=(0, 0, 0.3), scale=(1, 0.9, 1.15),
         deform=lambda p: Vector((p.x * (1 + 0.1 * max(0, -p.z)), p.y, p.z)), seg=32, rings=20)
    blob("obelly", 0.18, mat("#f0e0c0", pat='flowers', color2="#c9a878", P=dict(nu=10, fv=24, rad=0.18)), b,
         loc=(0, -0.1, 0.26), scale=(0.9, 0.6, 1.1), seg=24, rings=16)
    hd = pivot("h", (0, -0.01, 0.6), b)
    blob("ohead", 0.21, fm, hd, scale=(1.1, 0.95, 0.9), seg=30, rings=20)
    for s in (-1, 1):
        ellipsoid("disc", 0.1, mat("#f0e0c0", kind='soft'), hd, loc=(s * 0.09, -0.15, 0.0), scale=(1, 0.35, 1), seg=18, rings=10)
        eye(hd, (s * 0.09, -0.19, 0.01), 0.062, iris="#e8a030")
        tube("tuft", [Vector((s * 0.12, -0.02, 0.14)), Vector((s * 0.18, 0.0, 0.24)), Vector((s * 0.2, 0.03, 0.3))],
             [0.04, 0.03, 0.008], fm, hd, seg=8, sub=3)
        # spectacles
        ring = [Vector((s * 0.09 + 0.075 * math.cos(TAU * j / 20), -0.235, 0.01 + 0.075 * math.sin(TAU * j / 20))) for j in range(21)]
        tube("spec", ring, [0.007], mat("#c9a040", metal=True), hd, seg=5, sub=1, line=False)
    blob("obeak", 0.035, mat("#e8b04a", kind='soft'), hd, loc=(0, -0.21, -0.06), scale=(0.8, 0.8, 1.3), seg=12, rings=8)
    W = {}
    for s in (-1, 1):
        w = pivot("wing", (s * 0.22, 0.02, 0.42), b)
        blob("owing", 0.17, mat("#7a5a3e", pat='stripes', color2="#5e432c", P=dict(nu=10, fv=40, thr=0.55)), w,
             loc=(0, 0.03, -0.12), scale=(0.3, 0.75, 1.1), seg=18, rings=12)
        W[s] = w
    # tiny ledger held by the wing
    led = pivot("ledger", (0.0, -0.22, 0.3), b, rot=(0.25, 0, 0))
    box("cover", (0.16, 0.03, 0.12), mat("#6a3f73", pat='leather', var=0.2), led, bevel=0.008)
    box("pages", (0.15, 0.034, 0.11), mat("#fbf4ea", pat='stripes', color2="#c9b48a", P=dict(nu=2, fv=400, thr=0.6, weave=False)),
        led, loc=(0, -0.003, 0.0))
    for k in range(3):
        box("line", (0.09, 0.002, 0.006), mat("#35d3b0", kind='flat', line=False), led, loc=(0, -0.022, 0.03 - 0.025 * k))
    F = {}
    for s in (-1, 1):
        f = pivot("foot", (s * 0.08, -0.05, 0.06), b)
        for t in (-0.5, 0, 0.5):
            tube("ot", [Vector((0, 0, 0)), Vector((math.sin(t) * 0.04, -0.05, -0.05))], [0.014], mat("#e8b04a", kind='soft'), f, seg=5, sub=1)
        F[s] = f

    def pose(anim, i, n):
        ph = TAU * i / n
        b.rotation_euler = (0, 0.12 * math.sin(ph) if anim == 'walk' else 0, 0)
        b.location.z = abs(math.sin(ph)) * 0.03 if anim == 'walk' else 0
        hd.rotation_euler = (0, 0, 0.15 * math.sin(ph) if anim == 'idle' else 0)
        for s, f in F.items():
            f.location.y = -0.05 + (0.05 * math.sin(ph) * s if anim == 'walk' else 0)
    c.pose = pose
    c.meta = dict(name_he="ינשופת הלוח", concept="מתג (Switch): היא רושמת בפנקס מי גר מאחורי כל דלת, ושולחת כל הודעה רק אל הדלת הנכונה.",
                  move="waddles")
    return c


# ---------------------------------------------------------------- 5 trail fox
def trail_fox():
    c = C("trail_fox")
    b = pivot("b", (0, 0, 0.0), c.body)
    om = mat("#e07a30", pat='fur', P=dict(scale=70), var=0.2)
    wm = mat("#fbf0e0", pat='fur', P=dict(scale=70), var=0.15)
    dm = mat("#3a2a2a", pat='fur', var=0.1)
    bz = 0.24
    blob("fbody", 0.16, om, b, loc=(0, 0.02, bz + 0.08), scale=(0.85, 1.5, 0.85), seg=28, rings=18)
    blob("fchest", 0.1, wm, b, loc=(0, -0.16, bz + 0.07), scale=(0.9, 0.7, 1.0), seg=18, rings=12)
    hd = pivot("h", (0, -0.26, bz + 0.22), b)
    blob("fhead", 0.13, om, hd, scale=(1.05, 1.0, 0.92), seg=24, rings=16)
    blob("snout", 0.07, wm, hd, loc=(0, -0.13, -0.04), scale=(0.8, 1.3, 0.7), seg=16, rings=10)
    ellipsoid("nose", 0.022, mat("#2a1a1a", kind='soft'), hd, loc=(0, -0.22, -0.02), seg=8, rings=6)
    for s in (-1, 1):
        eye(hd, (s * 0.06, -0.1, 0.03), 0.032, iris="#5a8a3a", rot=(0, 0, -s * 0.35))
        blob("ear", 0.06, om, hd, loc=(s * 0.08, 0.0, 0.12), scale=(0.7, 0.4, 1.3), rot=(0, s * 0.3, 0),
             deform=lambda p: Vector((p.x * (1 - 0.6 * max(0, p.z)), p.y, p.z)), seg=12, rings=8)
        ellipsoid("earin", 0.035, dm, hd, loc=(s * 0.08, -0.02, 0.12), scale=(0.6, 0.2, 1.2), rot=(0, s * 0.3, 0), seg=8, rings=6)
        blush(hd, (s * 0.09, -0.11, -0.03), 0.02)
    # scarf with a little map-pouch: the route guide
    loft("fscarf", [(-0.03, 0.105, 0.1), (0.04, 0.11, 0.1)], mat("#35b3a0", pat='stripes', color2="#e8b04a",
                                                                    P=dict(nu=12, fv=60, thr=0.7)), hd, seg=24, loc=(0, 0.04, -0.1))
    box("pouch", (0.07, 0.03, 0.06), mat("#8a5a36", pat='leather'), b, loc=(0.0, -0.2, bz + 0.05), bevel=0.01)
    tube("route", [Vector((-0.02, -0.217, bz + 0.05)), Vector((0.0, -0.218, bz + 0.07)), Vector((0.02, -0.217, bz + 0.04))],
         [0.004], glow("#35d3b0", 2), b, seg=4, sub=3, line=False)
    tail = pivot("tail", (0, 0.24, bz + 0.12), b)
    tube("ftail", [Vector((0, 0, 0)), Vector((0, 0.12, 0.08)), Vector((0, 0.22, 0.2)), Vector((0, 0.26, 0.32))],
         [0.05, 0.09, 0.08, 0.02], om, tail, seg=14, sub=4)
    ellipsoid("tailtip", 0.05, wm, tail, loc=(0, 0.255, 0.3), scale=(1, 1, 1.3), seg=12, rings=8)
    L = leg4(b, bz, dict(FL=(0.07, -0.14), FR=(-0.07, -0.14), BL=(0.07, 0.16), BR=(-0.07, 0.16)), 0.035, om, dm)

    def pose(anim, i, n):
        ph = TAU * i / n
        if anim == 'walk':
            walk4(L, ph, 0.5)
            b.location.z = 0.015 * abs(math.cos(ph))
        else:
            walk4(L, 0, 0)
        tail.rotation_euler = (0.1 * math.sin(ph), 0, 0.25 * math.sin(ph))
        hd.rotation_euler = (0, 0, 0.1 * math.sin(ph) if anim == 'idle' else 0)
    c.pose = pose
    c.meta = dict(name_he="שועל השבילים", concept="נתב (Router): הוא מכיר את הדרכים בין הכפרים ובוחר לכל הודעה את השביל שמוביל אל הכפר הנכון.",
                  move="walks")
    return c


# ---------------------------------------------------------------- 6 ant swarm
def ant_swarm():
    c = C("ant_swarm")
    am = mat("#7a3a2a", pat='noise', P=dict(scale=40), var=0.15, rim=0.7)
    ants = []
    spots = [(-0.18, -0.12, 0.0), (0.12, -0.2, 0.6), (0.2, 0.1, 1.2), (-0.1, 0.18, 1.8), (0.0, -0.02, 2.4)]
    colors = ["#35d3b0", "#e8b04a", "#c44b3f", "#6a8ad6", "#35d3b0"]
    for k, (x, y, ph0) in enumerate(spots):
        a = pivot("ant", (x, y, 0.0), c.body, rot=(0, 0, 0.3 * math.sin(k)))
        blob("ah", 0.035, am, a, loc=(0, -0.06, 0.06), seg=12, rings=8)
        blob("at", 0.03, am, a, loc=(0, 0.0, 0.055), scale=(0.9, 1.1, 0.9), seg=12, rings=8)
        blob("aa", 0.045, am, a, loc=(0, 0.07, 0.06), scale=(0.9, 1.3, 0.9), seg=12, rings=8)
        for s in (-1, 1):
            eye(a, (s * 0.017, -0.085, 0.07), 0.012, iris="#2a1a10")
            tube("ant", [Vector((s * 0.01, -0.08, 0.09)), Vector((s * 0.03, -0.1, 0.13)), Vector((s * 0.05, -0.13, 0.13))],
                 [0.004], am, a, seg=4, sub=2, line=False)
        legs = []
        for s in (-1, 1):
            for j, yy in enumerate((-0.02, 0.0, 0.02)):
                lp = pivot("al", (s * 0.02, yy, 0.05), a)
                tube("l", [Vector((0, 0, 0)), Vector((s * 0.04, (j - 1) * 0.03, 0.01)), Vector((s * 0.06, (j - 1) * 0.04, -0.05))],
                     [0.005], am, lp, seg=4, sub=2, line=False)
                legs.append((lp, s, j))
        # carried thread spool + thread
        cyl("carry", 0.03, 0.03, 0.04, mat(colors[k], pat='spiral', color2=darker(colors[k]), P=dict(nu=8, fv=200)), a,
            loc=(0, 0.0, 0.1), rot=(0, math.pi / 2, 0))
        ants.append((a, legs, ph0))
    # the many routes they weave (glowing threads between them)
    pts = [Vector((x, y, 0.13)) for (x, y, _) in spots]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if (i + j) % 2 == 0 or j == i + 1:
                mid = (pts[i] + pts[j]) / 2 + Vector((0, 0, -0.03))
                tube("mesh", [pts[i], mid, pts[j]], [0.004], glow("#35d3b0", 1.6), c.body, seg=4, sub=3)

    def pose(anim, i, n):
        ph = TAU * i / n
        for a, legs, ph0 in ants:
            for lp, s, j in legs:
                lp.rotation_euler = (0, 0, (0.4 * math.sin(ph * 2 + ph0 + j * math.pi + (s > 0) * math.pi)) if anim == 'walk' else 0)
            a.location.z = 0.008 * abs(math.sin(ph * 2 + ph0))
    c.pose = pose
    c.meta = dict(name_he="נחיל הנמלים", concept="טופולוגיית Mesh (רשת שבילים): כל נמלה מחוברת לכמה חברות, ואם שביל אחד נחתך החוט עובר בדרך אחרת.",
                  move="walks")
    return c


# ---------------------------------------------------------------- 7 snail
def slow_snail():
    c = C("slow_snail")
    sk = mat("#b8c8a0", pat='skin', kind='skin', var=0.05, rim=0.6)
    b = pivot("b", parent=c.body)
    foot = loft("sfoot", [(0.0, 0.08, 0.09, 0, -0.16), (0.04, 0.08, 0.12, 0, 0.0), (0.03, 0.06, 0.09, 0, 0.18),
                          (0.0, 0.03, 0.05, 0, 0.26)], sk, b, seg=20, cap_top=True, cap_bot=True)
    hd = pivot("h", (0, -0.17, 0.05), b)
    blob("shead", 0.075, sk, hd, loc=(0, 0, 0.06), scale=(1, 1.0, 1.25), seg=18, rings=12)
    for s in (-1, 1):
        tube("stalk", [Vector((s * 0.03, 0, 0.12)), Vector((s * 0.05, -0.02, 0.22))], [0.012, 0.009], sk, hd, seg=6, sub=1)
        eye(hd, (s * 0.05, -0.03, 0.24), 0.028, iris="#3a2a1a")
    smile(hd, (0, -0.075, 0.05), 0.03)
    blush(hd, (0.05, -0.06, 0.06), 0.015)
    blush(hd, (-0.05, -0.06, 0.06), 0.015)
    # spiral shell
    shm = mat("#d68f3a", pat='spiral', color2="#a8602a", P=dict(nu=3, fv=30, thr=0.5), var=0.25, bump=0.5)
    pts = []
    for k in range(40):
        t = k / 39
        a = t * TAU * 2.2
        r = 0.13 * (1 - 0.8 * t)
        pts.append(Vector((0.0 + 0.02 * t, 0.05 + r * math.cos(a), 0.17 + r * math.sin(a))))
    tube("shell", pts, [0.11, 0.08, 0.05, 0.025], shm, b, seg=20, sub=2, twist_up=(1, 0, 0))
    # glowing thread trail (slow link)
    tube("trail", [Vector((0, 0.24, 0.005)), Vector((0.04, 0.45, 0.005)), Vector((-0.03, 0.7, 0.005))], [0.012, 0.008, 0.003],
         glow("#35d3b0", 1.6), c.body, seg=5, sub=4)
    ellipsoid("dust", 0.03, glow("#fff0c8", 1.5), c.body, loc=(0.05, 0.55, 0.06), seg=6, rings=4)

    def pose(anim, i, n):
        ph = TAU * i / n
        b.scale = (1, 1 + 0.04 * math.sin(ph), 1 - 0.02 * math.sin(ph))
        hd.rotation_euler = (0.1 * math.sin(ph), 0, 0.08 * math.sin(ph * 0.5))
    c.pose = pose
    c.meta = dict(name_he="חילזון החוט", concept="קישור איטי (רוחב פס נמוך): החוט שלו מוביל מעט מידע בכל רגע, ולכן הודעה גדולה מגיעה לאט.",
                  move="crawls")
    return c


# ---------------------------------------------------------------- 8 hedgehog
def spool_hedgehog():
    c = C("spool_hedgehog")
    b = pivot("b", parent=c.body)
    fm = mat("#c9a07a", pat='fur', P=dict(scale=80), var=0.18)
    bz = 0.12
    blob("hbody", 0.2, mat("#8a6a50", pat='fur', var=0.2), b, loc=(0, 0.03, bz + 0.1), scale=(1, 1.15, 0.85), seg=30, rings=20)
    hd = pivot("h", (0, -0.17, bz + 0.07), b)
    blob("hface", 0.11, fm, hd, scale=(1, 1.15, 0.9), deform=lambda p: Vector((p.x, p.y - 0.25 * max(0, -p.y) ** 2, p.z)),
         seg=22, rings=14)
    ellipsoid("hnose", 0.025, mat("#2a1a1a", kind='soft'), hd, loc=(0, -0.16, 0.0), seg=8, rings=6)
    for s in (-1, 1):
        eye(hd, (s * 0.05, -0.08, 0.04), 0.028, iris="#2a1a10", rot=(0, 0, -s * 0.3))
        blush(hd, (s * 0.07, -0.08, -0.01), 0.018)
        ellipsoid("hear", 0.03, fm, hd, loc=(s * 0.08, 0.0, 0.08), scale=(1, 0.4, 1), seg=8, rings=6)
    cols = ["#35d3b0", "#e8b04a", "#c44b3f", "#6a8ad6", "#f3e4c4", "#a94a62"]
    k = 0
    for ring in range(4):
        el = 0.35 + ring * 0.3
        cnt = 6 + ring * 2
        for j in range(cnt):
            a = math.pi * (0.1 + 0.8 * j / max(1, cnt - 1)) + (ring % 2) * 0.1
            # spools on the back hemisphere (y >= 0 side and top)
            dirv = Vector((math.cos(a) * math.cos(el * 0.9), 0.3 + math.sin(el), math.sin(a) * math.cos(el * 0.6) + 0.5)).normalized()
            pos = Vector((0, 0.03, bz + 0.1)) + Vector((dirv.x * 0.2, dirv.y * 0.22, dirv.z * 0.17))
            sp = pivot("sp", pos, b)
            sp.rotation_mode = 'QUATERNION'
            sp.rotation_quaternion = dirv.to_track_quat('Z', 'Y')
            cc = cols[k % len(cols)]
            cyl("thr", 0.024, 0.024, 0.06, mat(cc, pat='spiral', color2=darker(cc), P=dict(nu=6, fv=260)), sp, loc=(0, 0, 0.0))
            cyl("fl", 0.032, 0.032, 0.01, mat("#a06a3e", pat='wood'), sp, loc=(0, 0, 0.06))
            k += 1
    L = leg4(b, bz, dict(FL=(0.08, -0.1), FR=(-0.08, -0.1), BL=(0.08, 0.13), BR=(-0.08, 0.13)), 0.03, fm,
             mat("#3a2a20"))
    # tiny key on a thread around the neck (guards the door)
    tube("keystr", [Vector((-0.06, -0.12, bz + 0.03)), Vector((0, -0.17, bz - 0.02)), Vector((0.06, -0.12, bz + 0.03))], [0.004],
         mat("#c44b3f"), b, seg=4, sub=3, line=False)
    km = mat("#e8b04a", metal=True)
    ellipsoid("keybow", 0.022, km, b, loc=(0, -0.18, bz - 0.04), scale=(1, 0.4, 1), seg=10, rings=6)
    box("keyshaft", (0.01, 0.01, 0.05), km, b, loc=(0, -0.185, bz - 0.08))

    def pose(anim, i, n):
        ph = TAU * i / n
        if anim == 'walk':
            walk4(L, ph, 0.6)
            b.location.z = 0.01 * abs(math.cos(ph))
        else:
            walk4(L, 0, 0)
            b.scale = (1, 1, 1 + 0.02 * math.sin(ph))
        hd.rotation_euler = (0.08 * math.sin(ph), 0, 0)
    c.pose = pose
    c.meta = dict(name_he="קיפוד הסלילים", concept="אבטחה (Security): הוא שומר על הדלת ונותן להיכנס רק למי שמורשה; הסלילים על גבו הם הגנה, לא נשק.",
                  move="walks")
    return c


# ---------------------------------------------------------------- 9 Gargar the cat
def gargar_cat():
    c = C("gargar_cat")
    b = pivot("b", parent=c.body)
    gm = mat("#8a8a96", pat='vstripes', color2="#6a6a78", P=dict(nu=10, fv=10, thr=0.65), var=0.18)
    wm = mat("#e8e4ea", pat='fur', P=dict(scale=80), var=0.1)
    bz = 0.2
    blob("cbody", 0.15, gm, b, loc=(0, 0.04, bz + 0.07), scale=(0.85, 1.45, 0.85), seg=28, rings=18)
    hd = pivot("h", (0, -0.2, bz + 0.2), b)
    blob("chead", 0.14, gm, hd, scale=(1.1, 0.95, 0.9), seg=26, rings=16)
    blob("cmuzzle", 0.06, wm, hd, loc=(0, -0.11, -0.04), scale=(1.2, 0.6, 0.8), seg=14, rings=10)
    ellipsoid("cnose", 0.018, mat("#e88a9a", kind='soft'), hd, loc=(0, -0.15, -0.01), scale=(1.2, 0.6, 0.8), seg=8, rings=6)
    for s in (-1, 1):
        eye(hd, (s * 0.065, -0.1, 0.02), 0.036, iris="#9ac040")
        blob("cear", 0.055, gm, hd, loc=(s * 0.09, 0.0, 0.11), scale=(0.8, 0.4, 1.1), rot=(0, s * 0.35, 0),
             deform=lambda p: Vector((p.x * (1 - 0.7 * max(0, p.z)), p.y, p.z)), seg=12, rings=8)
        ellipsoid("cearin", 0.03, mat("#e8a0b0", kind='soft'), hd, loc=(s * 0.09, -0.02, 0.1), scale=(0.6, 0.2, 1.0),
                  rot=(0, s * 0.35, 0), seg=8, rings=6)
        for k in (-1, 1):
            tube("whisk", [Vector((s * 0.05, -0.15, -0.03 + 0.01 * k)), Vector((s * 0.16, -0.16, -0.02 + 0.03 * k))], [0.0025],
                 mat("#fbf4ea", kind='flat'), hd, seg=4, sub=1, line=False)
    tail = pivot("tail", (0, 0.24, bz + 0.08), b)
    tube("ctail", [Vector((0, 0, 0)), Vector((0.04, 0.1, 0.06)), Vector((0.02, 0.14, 0.2)), Vector((-0.04, 0.12, 0.3))],
         [0.035, 0.032, 0.03, 0.02], gm, tail, seg=10, sub=4)
    L = leg4(b, bz, dict(FL=(0.06, -0.13), FR=(-0.06, -0.13), BL=(0.06, 0.15), BR=(-0.06, 0.15)), 0.032, gm, wm)
    # the blue thread he sits on
    tube("bluethread", [Vector((-0.4, 0.1, 0.01)), Vector((-0.1, 0.02, 0.012)), Vector((0.15, 0.1, 0.01)), Vector((0.45, -0.05, 0.01))],
         [0.012], glow("#4a8af0", 1.6), c.root, seg=5, sub=4)
    loft("collar", [(-0.02, 0.09, 0.085), (0.02, 0.092, 0.087)], mat("#4a78c8", pat='knit', P=dict(nu=20, fv=200)), hd, seg=20,
         loc=(0, 0.03, -0.1))

    def pose(anim, i, n):
        ph = TAU * i / n
        if anim == 'walk':
            walk4(L, ph, 0.5)
            b.location.z = 0.012 * abs(math.cos(ph))
        else:
            walk4(L, 0, 0)
            b.scale = (1, 1, 1 + 0.02 * math.sin(ph))
        tail.rotation_euler = (0, 0.2 * math.sin(ph), 0.3 * math.sin(ph))
        hd.rotation_euler = (0, 0.08 * math.sin(ph) if anim == 'idle' else 0, 0)
    c.pose = pose
    c.meta = dict(name_he="גרגר, החתול של סבתא שושנה", concept="חוט שמור: גרגר יושב תמיד על החוט הכחול של סבתא, וכל עוד החוט חם, החיבור לבית הנכדים קיים.",
                  move="walks")
    return c


# ---------------------------------------------------------------- 10 cloud sheep
def cloud_sheep():
    c = C("cloud_sheep")
    b = pivot("b", (0, 0, 0.25), c.body)
    wool = mat("#f6f4fa", pat='wool', P=dict(scale=22), kind='soft', var=0.25, bump=0.6, rim=0.6)
    import random
    rnd = random.Random(3)
    for k in range(14):
        a = rnd.random() * TAU
        e = rnd.uniform(-0.3, 1.0)
        r = rnd.uniform(0.09, 0.13)
        pos = Vector((math.cos(a) * 0.15 * math.cos(e), 0.05 + math.sin(a) * 0.2 * math.cos(e), 0.12 + 0.1 * math.sin(e)))
        blob("puff", r, wool, b, loc=pos, seg=18, rings=12)
    blob("core", 0.2, wool, b, loc=(0, 0.05, 0.12), scale=(0.9, 1.2, 0.8), seg=24, rings=16)
    hd = pivot("h", (0, -0.22, 0.14), b)
    face = mat("#4a4058", pat='skin', kind='skin', var=0.05)
    blob("shead", 0.085, face, hd, scale=(0.9, 1.1, 1.0), seg=20, rings=14)
    for s in (-1, 1):
        eye(hd, (s * 0.045, -0.07, 0.02), 0.028, iris="#5a4a2a")
        ellipsoid("sear", 0.04, face, hd, loc=(s * 0.09, 0.0, 0.03), scale=(1.2, 0.5, 0.5), rot=(0, s * -0.3, 0), seg=10, rings=6)
    blob("tuft", 0.06, wool, hd, loc=(0, 0.0, 0.08), seg=14, rings=10)
    blush(hd, (0.05, -0.07, -0.02), 0.014)
    blush(hd, (-0.05, -0.07, -0.02), 0.014)
    L = {}
    for nm, (x, y) in dict(FL=(0.08, -0.08), FR=(-0.08, -0.08), BL=(0.08, 0.16), BR=(-0.08, 0.16)).items():
        p = pivot("leg" + nm, (x, y, 0.05), b)
        loft("sleg", [(0, 0.022, 0.022), (-0.18, 0.02, 0.02)], face, p, seg=8, cap_bot=True)
        L[nm] = p
    # little rain-cloud wisps under it (it floats)

    def pose(anim, i, n):
        ph = TAU * i / n
        b.location.z = 0.25 + 0.03 * math.sin(ph)
        walk4(L, ph, 0.4 if anim == 'walk' else 0.08)
        hd.rotation_euler = (0.06 * math.sin(ph), 0, 0)
    c.pose = pose
    c.meta = dict(name_he="כבשת הענן", concept="רוחות האוויר (רשת אלחוטית): כבשה שמרחפת בלי חוט, כמו הודעה שעוברת באוויר בלי כבל.",
                  move="floats", hover=0.08)
    return c


# ---------------------------------------------------------------- 11 spinner spider
def spinner_spider():
    c = C("spinner_spider")
    b = pivot("b", (0, 0, 0.0), c.body)
    fm = mat("#7a5aa8", pat='fur', P=dict(scale=60), var=0.2, rim=0.7)
    lm = mat("#5a4a8a", pat='stripes', color2="#35b3a0", P=dict(nu=8, fv=30, thr=0.75), var=0.15)
    bz = 0.32
    blob("abd", 0.26, mat("#6a4a98", pat='dots', color2="#35d3b0", P=dict(nu=8, fv=8, rad=0.16), var=0.2), b,
         loc=(0, 0.24, bz + 0.1), scale=(1, 1.1, 0.9), seg=32, rings=20)
    hd = pivot("h", (0, -0.08, bz + 0.05), b)
    blob("ceph", 0.19, fm, hd, scale=(1.05, 1.0, 0.85), seg=30, rings=20)
    for s in (-1, 1):
        eye(hd, (s * 0.08, -0.15, 0.05), 0.06, iris="#3a2a5a")
        eye(hd, (s * 0.15, -0.1, 0.11), 0.028, iris="#3a2a5a", rot=(0, 0, -s * 0.5))
        blush(hd, (s * 0.12, -0.15, -0.03), 0.03)
    smile(hd, (0, -0.18, -0.05), 0.045, curve=0.45)
    # little knit beret: she is the valley's weaver
    blob("beret", 0.11, mat("#e8b04a", pat='knit', P=dict(nu=20, fv=90)), hd, loc=(0.04, 0.02, 0.15), scale=(1, 1, 0.4),
         rot=(0.1, 0.3, 0), seg=20, rings=12)
    legs = []
    for s in (-1, 1):
        for j in range(4):
            a = -0.9 + j * 0.55
            lp = pivot("sl", (s * 0.1, -0.05 + j * 0.06, bz), b, rot=(0, 0, s * a))
            pts = [Vector((0, 0, 0)), Vector((s * 0.18, 0, 0.12)), Vector((s * 0.36, 0, 0.02)), Vector((s * 0.42, 0, -bz + 0.02))]
            tube("leg", pts, [0.035, 0.03, 0.025, 0.012], lm, lp, seg=10, sub=3)
            legs.append((lp, s, j, s * a))
    # thread spun between two front legs
    tube("weave", [Vector((0.18, -0.3, bz + 0.1)), Vector((0.0, -0.35, bz + 0.05)), Vector((-0.18, -0.3, bz + 0.1))], [0.006],
         glow("#35d3b0", 2), b, seg=4, sub=3)
    tube("spin", [Vector((0, 0.45, bz + 0.1)), Vector((0.05, 0.6, bz + 0.4)), Vector((0.0, 0.62, bz + 0.8))], [0.005],
         glow("#9ffff0", 1.6), b, seg=4, sub=3)

    def pose(anim, i, n):
        ph = TAU * i / n
        for lp, s, j, a0 in legs:
            sw = (0.25 * math.sin(ph + j * math.pi / 2 + (s > 0) * math.pi)) if anim == 'walk' else 0.03 * math.sin(ph + j)
            lp.rotation_euler = (0, 0.1 * max(0, sw) * 2, a0 + sw)
        b.location.z = 0.015 * math.sin(ph * 2) if anim == 'walk' else 0.01 * math.sin(ph)
        hd.rotation_euler = (0, 0, 0.08 * math.sin(ph))
    c.pose = pose
    c.meta = dict(name_he="אורגת הקורים", concept="תשתית הרשת: העכבישה הגדולה והטובה טווה את החוטים בין כל הבתים, ובלי החוטים אין דרך למסור הודעות.",
                  move="walks")
    return c


# ---------------------------------------------------------------- 12 glow-worm
def glow_worm():
    c = C("glow_worm")
    segs = []
    cols = ["#9ad86a", "#b8e88a"]
    for k in range(7):
        p = pivot("seg", (0, -0.2 + k * 0.07, 0.06), c.body)
        r = 0.065 * (1 - 0.06 * k)
        m = mat(cols[k % 2], pat='skin', kind='soft', var=0.05, rim=0.6) if k < 5 else glow("#d8ff9a", 2.2)
        blob("s", r, m, p, seg=18, rings=12)
        if k >= 5:
            ellipsoid("gh", r * 2.2, glow("#c8ff7a", 1.4, alpha=0.13, soft=True), p, seg=12, rings=8)
        segs.append(p)
    hd = segs[0]
    for s in (-1, 1):
        eye(hd, (s * 0.03, -0.05, 0.03), 0.026, iris="#2a3a1a")
        tube("wa", [Vector((s * 0.02, -0.02, 0.06)), Vector((s * 0.05, -0.04, 0.12))], [0.006], mat("#6a9a4a"), hd, seg=5, sub=1)
        ellipsoid("wab", 0.014, glow("#d8ff9a", 2), hd, loc=(s * 0.05, -0.04, 0.125), seg=6, rings=4)
    smile(hd, (0, -0.064, -0.01), 0.022)
    # the lit thread path behind it
    tube("path", [Vector((0, 0.3, 0.005)), Vector((0.08, 0.5, 0.005)), Vector((-0.05, 0.75, 0.005))], [0.01, 0.007, 0.003],
         glow("#d8ff9a", 1.4), c.body, seg=5, sub=4)
    c.lights.append(None)

    def pose(anim, i, n):
        ph = TAU * i / n
        for k, p in enumerate(segs):
            p.location.z = 0.06 + (0.03 * max(0, math.sin(ph - k * 0.9)) if anim == 'walk' else 0.008 * math.sin(ph - k * 0.6))
            p.location.x = 0.015 * math.sin(ph * 0.5 - k * 0.7)
    c.pose = pose
    c.meta = dict(name_he="תולעת הזוהר", concept="נורית חיבור (Link light): כמו הנורית שנדלקת ליד שקע הרשת, האור שלה מראה שהחיבור בשביל הזה פעיל.",
                  move="crawls")
    return c


# ================================================================ legendary
def thread_serpent():
    c = C("thread_serpent")
    stone = mat("#a29a92", pat='patches', color2="#6f8a5a", P=dict(scale=4, thr=0.62, sharp=8), var=0.3, bump=0.8)
    tower = pivot("tower", parent=c.body)
    loft("tw", [(0, 0.62, 0.62), (2.2, 0.55, 0.55), (2.4, 0.6, 0.6), (2.5, 0.6, 0.6)], stone, tower, seg=40, cap_top=True,
         folds=lambda a, t: 1 + 0.015 * math.sin(14 * a))
    for k in range(6):   # stone courses
        loft("course", [(0.35 * k + 0.2, 0.625 - 0.012 * k, 0.625 - 0.012 * k), (0.35 * k + 0.23, 0.63 - 0.012 * k, 0.63 - 0.012 * k)],
             mat("#857d78", kind='cloth'), tower, seg=40, line=False)
    box("window", (0.14, 0.05, 0.22), glow("#ffc66a", 2.0), tower, loc=(0.0, -0.57, 1.85))
    sm = mat("#2fb8a0", pat='fur', P=dict(scale=30), kind='soft', var=0.15, bump=0.3, rim=0.9)
    pts = []
    N = 80
    for k in range(N):
        t = k / (N - 1)
        a = t * TAU * 2.1 - 2.2
        r = 0.74 + 0.08 * math.sin(t * 7)
        pts.append(Vector((r * math.cos(a), r * math.sin(a), 0.15 + t * 2.05 + 0.08 * math.sin(t * 11))))
    # climb onto the roof and lay the head facing the viewer
    top = Vector((0.0, -0.3, 2.62))
    pts += [pts[-1] + (top - pts[-1]) * 0.5 + Vector((0, 0, 0.12)), top]
    rad = [0.06, 0.15, 0.19, 0.2, 0.19, 0.17, 0.16]
    body = tube("serpent", pts, rad, sm, c.body, seg=22, sub=2)
    halo = body
    # it is made of thread: thin glowing strands wound along the body
    th = glow("#9ffff0", 1.8)
    for k in range(3):
        sp = []
        for j, p in enumerate(pts):
            t = j / (len(pts) - 1)
            tg = (pts[min(j + 1, len(pts) - 1)] - pts[max(j - 1, 0)]).normalized()
            n1 = tg.cross(Vector((0, 0, 1)))
            if n1.length < 1e-3:
                n1 = Vector((1, 0, 0))
            n1.normalize()
            n2 = tg.cross(n1).normalized()
            ang = k * TAU / 3 + t * 40
            rr = (0.06 + 0.13 * min(1, t * 6)) * 1.02
            sp.append(p + (n1 * math.cos(ang) + n2 * math.sin(ang)) * rr)
        tube("strand", sp, [0.008], th, c.body, seg=4, sub=3, line=False)
    hd = pivot("h", top + Vector((0.0, -0.18, 0.08)), c.body)
    blob("shead", 0.34, sm, hd, scale=(0.95, 1.25, 0.62), deform=lambda p: Vector((p.x, p.y - 0.15 * max(0, -p.y) ** 2, p.z)),
         seg=36, rings=24)
    blob("snout", 0.2, mat("#7fe0c8", pat='fur', P=dict(scale=30), kind='soft', var=0.1), hd, loc=(0, -0.3, -0.05),
         scale=(1.0, 0.9, 0.55), seg=24, rings=14)
    for s_ in (-1, 1):
        closed_eye(hd, (s_ * 0.17, -0.28, 0.12), 0.08, color="#0e4a44", up=False)
        blush(hd, (s_ * 0.22, -0.36, 0.0), 0.05)
        tube("horn", [Vector((s_ * 0.14, 0.05, 0.15)), Vector((s_ * 0.24, 0.2, 0.32)), Vector((s_ * 0.2, 0.38, 0.42))],
             [0.05, 0.035, 0.01], mat("#f3e4c4", kind='soft'), hd, seg=8, sub=3)
        tube("whisker", [Vector((s_ * 0.1, -0.48, -0.06)), Vector((s_ * 0.34, -0.56, -0.14)), Vector((s_ * 0.52, -0.5, -0.32))],
             [0.016, 0.012, 0.004], glow("#9ffff0", 1.6), hd, seg=5, sub=3)
    for k in range(5):
        ellipsoid("mane", 0.07, mat("#9ffff0", kind='soft', rim=0.6), hd, loc=(0, 0.1 + 0.09 * k, 0.2 - 0.02 * k), seg=10, rings=6)
    smile(hd, (0, -0.48, -0.08), 0.08, color="#0e4a44", curve=0.3)
    end = top
    zz = []
    for k in range(3):
        o = ellipsoid("dream", 0.03 + 0.012 * k, glow("#cffff6", 2.0), c.body, loc=end + Vector((0.12 + 0.1 * k, -0.15, 0.4 + 0.18 * k)),
                      seg=8, rings=6)
        zz.append(o)

    def pose(anim, i, n):
        ph = TAU * i / n
        body.scale = (1 + 0.012 * math.sin(ph), 1 + 0.012 * math.sin(ph), 1)
        hd.scale = (1 + 0.02 * math.sin(ph), 1 + 0.02 * math.sin(ph), 1 + 0.02 * math.sin(ph))
        for k, o in enumerate(zz):
            o.hide_render = k > (i % 4)
    c.pose = pose
    c.meta = dict(name_he="נחש החוט", concept="עמוד השדרה של הרשת (Backbone): חוט ארוך ועבה שכל החוטים הקטנים מתחברים אליו.",
                  legend="נחש החוט ישן סביב המגדל הישן מאז שנטוו החוטים הראשונים. אומרים שכל עוד הוא נושם, החוטים בעמק לא יקרעו.",
                  legendary=True)
    return c


def cloud_whale():
    c = C("cloud_whale")
    wool = mat("#eef0fb", pat='wool', P=dict(scale=8), kind='soft', var=0.2, bump=0.5, rim=0.8)
    belly = mat("#c8d0f0", pat='stripes', color2="#b0b8e0", P=dict(nu=2, fv=14, thr=0.5, weave=False), kind='soft', var=0.1, rim=0.5)
    b = pivot("b", (0, 0, 0.75), c.body, rot=(0, 0, math.radians(-90)))
    blob("wbody", 1.0, wool, b, scale=(0.55, 1.25, 0.5),
         deform=lambda p: Vector((p.x * (1 - 0.45 * max(0, p.y) ** 1.5), p.y, p.z * (1 - 0.5 * max(0, p.y) ** 1.5))),
         seg=48, rings=32)
    blob("wbelly", 0.9, belly, b, loc=(0, -0.15, -0.18), scale=(0.5, 1.05, 0.33), seg=40, rings=24)
    import random
    rnd = random.Random(7)
    for k in range(16):   # puffy cloud lumps on the back
        y = rnd.uniform(-0.9, 1.0)
        blob("lump", rnd.uniform(0.14, 0.24) * (1 - 0.3 * max(0, y)), wool, b,
             loc=(rnd.uniform(-0.25, 0.25), y, 0.38 * (1 - 0.4 * abs(y)) + rnd.uniform(-0.02, 0.06)), seg=18, rings=12)
    for k in range(22):   # stars on its back
        y = rnd.uniform(-0.8, 0.9)
        ellipsoid("star", rnd.uniform(0.015, 0.035), glow(rnd.choice(["#fff4c0", "#ffffff", "#bfefff"]), 3.0), b,
                  loc=(rnd.uniform(-0.3, 0.3), y, 0.5 * (1 - 0.4 * abs(y)) + 0.06), seg=6, rings=4)
    for s in (-1, 1):
        eye(b, (s * 0.42, -0.75, -0.02), 0.07, iris="#3a4a8a", rot=(0, 0, -s * 1.1))
        blush(b, (s * 0.44, -0.86, -0.12), 0.06)
    smile(b, (0, -1.2, -0.12), 0.25, color="#6a6a9a", curve=0.2)
    fins = []
    for s in (-1, 1):
        f = pivot("fin", (s * 0.45, -0.3, -0.2), b)
        blob("finb", 0.35, wool, f, loc=(s * 0.25, 0.1, -0.05), scale=(0.9, 0.45, 0.12), rot=(0, s * 0.4, 0), seg=24, rings=12)
        fins.append((f, s))
    tail = pivot("tail", (0, 1.2, 0.05), b)
    for s in (-1, 1):
        blob("fluke", 0.4, wool, tail, loc=(s * 0.3, 0.25, 0.08), scale=(0.9, 0.5, 0.1), rot=(0, 0, s * 0.4), seg=24, rings=12)

    def pose(anim, i, n):
        ph = TAU * i / n
        b.location.z = 0.75 + 0.04 * math.sin(ph)
        tail.rotation_euler = (0.18 * math.sin(ph), 0, 0)
        for f, s in fins:
            f.rotation_euler = (0, s * 0.15 * math.sin(ph + 1), 0)
    c.pose = pose
    c.meta = dict(name_he="לוויתן הענן", concept="רשת רחבה (WAN): הוא שט בשמים מעל כל העמקים ומחבר בין מקומות רחוקים.",
                  legend="פעם בשנה לוויתן הענן עובר מעל העמק, ועל גבו כוכבים של כל ההודעות שלא הגיעו. מי שרואה אותו, יודע שעוד יש דרך החוצה.",
                  legendary=True)
    return c


def echo_giant():
    c = C("echo_giant")
    stone = mat("#9a948e", pat='patches', color2="#6a8a4a", P=dict(scale=3, thr=0.6, sharp=7, bscale=14), var=0.3, bump=0.9)
    moss = mat("#5f8f4a", pat='wool', P=dict(scale=30), var=0.3, bump=0.6)
    b = pivot("b", parent=c.body)
    # seated giant: big round body, legs folded
    for s in (-1, 1):
        blob("knee", 0.42, stone, b, loc=(s * 0.45, -0.35, 0.4), scale=(0.85, 1.2, 0.8), seg=28, rings=18)
        blob("foot", 0.3, stone, b, loc=(s * 0.5, -0.75, 0.15), scale=(1.0, 1.2, 0.6), seg=24, rings=14)
    blob("torso", 0.85, stone, b, loc=(0, 0.1, 1.05), scale=(1.0, 0.8, 1.05),
         deform=lambda p: Vector((p.x * (1 + 0.1 * p.z), p.y, p.z)), seg=36, rings=24)
    hd = pivot("h", (0, -0.05, 2.05), b)
    blob("head", 0.48, stone, hd, scale=(1.0, 0.9, 1.0), seg=36, rings=24)
    blob("brow", 0.35, stone, hd, loc=(0, -0.28, 0.12), scale=(1.2, 0.4, 0.35), seg=24, rings=12)
    blob("gnose", 0.1, stone, hd, loc=(0, -0.44, -0.02), scale=(0.9, 0.8, 1.3), seg=14, rings=10)
    for s in (-1, 1):
        closed_eye(hd, (s * 0.17, -0.42, 0.04), 0.09, color="#2e3a2a", up=False)
        blob("garm", 0.3, stone, b, loc=(s * 0.82, -0.05, 1.05), scale=(0.7, 0.75, 1.3), rot=(0.3, s * 0.2, 0), seg=24, rings=16)
        blob("ghand", 0.25, stone, b, loc=(s * 0.55, -0.55, 0.72), scale=(1.0, 0.8, 0.6), seg=20, rings=12)
    mouth = ellipsoid("gmouth", 0.09, mat("#2a2420", kind='flat', line=False), hd, loc=(0, -0.43, -0.2), scale=(1, 0.4, 1.2),
                      seg=16, rings=10)
    # moss caps and little flowers
    blob("mosscap", 0.4, moss, hd, loc=(0.05, 0.05, 0.3), scale=(1.1, 1.0, 0.45), seg=28, rings=14)
    blob("mossshoulder", 0.4, moss, b, loc=(-0.55, 0.1, 1.6), scale=(1.0, 0.9, 0.4), seg=24, rings=12)
    blob("mossknee", 0.3, moss, b, loc=(0.45, -0.4, 0.68), scale=(1.0, 1.0, 0.35), seg=20, rings=10)
    import random
    rnd = random.Random(5)
    for k in range(10):
        p = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.3), 0.45))
        ellipsoid("fl", 0.03, mat(rnd.choice(["#f6f0e6", "#e8b04a", "#c88ad8"]), kind='soft'), hd, loc=p, seg=8, rings=6)
    # glowing runes + echo rings
    for k, (x, z) in enumerate(((0.0, 1.25), (-0.3, 1.0), (0.3, 0.95))):
        tube("rune", [Vector((x - 0.08, -0.62, z)), Vector((x, -0.66, z + 0.08)), Vector((x + 0.08, -0.62, z))], [0.018],
             glow("#35d3b0", 2.2), b, seg=5, sub=3, line=False)
    rings = []
    for k in range(3):
        R = 0.18 + 0.14 * k
        r = tube("echo", [Vector((R * math.cos(a), -0.75 - 0.12 * k, 1.85 + R * math.sin(a) * 0.8))
                          for a in [-1.0 + 2.0 * j / 12 for j in range(13)]], [0.016], glow("#9ffff0", 2.0), b, seg=5, sub=1)
        rings.append(r)

    def pose(anim, i, n):
        ph = TAU * i / n
        for k, r in enumerate(rings):
            r.hide_render = k > i or i == 0
        mouth.scale = (1, 0.4, 1.2 + 0.3 * (i % 2))
    c.pose = pose
    c.meta = dict(name_he="ענק ההד מאבן", concept="בדיקת חיבור (Ping): שולחים אליו קריאה ומחכים שההד יחזור; אם ההד חוזר, הדרך פתוחה, ואם לא, משהו בדרך נחתך.",
                  legend="ענק ההד יושב בעמק מאז שהאבנים היו צעירות. מי שקורא לו בשמו שומע את הקול חוזר, ואם הקול לא חוזר, משהו בדרך נחתך.",
                  legendary=True)
    return c


SMALL = dict(paper_crane=paper_crane, lantern_moth=lantern_moth, echo_parrot=echo_parrot, librarian_owl=librarian_owl,
             trail_fox=trail_fox, ant_swarm=ant_swarm, slow_snail=slow_snail, spool_hedgehog=spool_hedgehog,
             gargar_cat=gargar_cat, cloud_sheep=cloud_sheep, spinner_spider=spinner_spider, glow_worm=glow_worm)
LEGEND = dict(thread_serpent=(thread_serpent, (384, 384), (192, 360), 92.0, 0),
              cloud_whale=(cloud_whale, (384, 256), (192, 250), 100.0, 25),
              echo_giant=(echo_giant, (256, 384), (128, 360), 92.0, 20))


def build(fn, line_t):
    reset()
    STATE['truth'] = False
    STATE['line_t'] = line_t
    render_setup(samples=24)
    world_and_lights('day')
    c = fn()
    return c


def codex(c, od, frame_scale):
    """256px 3/4 'collection card' render."""
    c.root.rotation_euler = (0, 0, math.radians(-30))
    c.pose('idle', 0, 4)
    bpy.context.view_layer.update()
    # frame the bounding box
    pts = []
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and not o.hide_render:
            for v in o.bound_box:
                pts.append(o.matrix_world @ Vector(v))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (mn + mx) / 2
    size = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    portrait_camera(ctr, dist=20, res=512, elev=18, yaw=0, ortho_scale=size * 1.12)
    bpy.context.scene.eevee.taa_render_samples = 32
    render_to(os.path.join(od, f"{c.name}_codex.png"))


def main():
    a = args()
    which, rawdir = a[0], a[1]
    names = list(SMALL) + list(LEGEND) if which == 'all' else (list(SMALL) if which == 'small' else
                                                                 (list(LEGEND) if which == 'legend' else which.split(',')))
    meta_all = {}
    for nm in names:
        t0 = time.time()
        od = os.path.join(rawdir, "creatures", nm)
        os.makedirs(od, exist_ok=True)
        if nm in SMALL:
            c = build(SMALL[nm], line_t=0.008)
            add_lines()
            cam = sprite_camera(128, 128, (64, 110), ppu=CPPU, ssaa=4)
            for anim, n in (('idle', 4), ('walk', 6)):
                for dn, deg in CDIRS:
                    for i in range(n):
                        c.pose(anim, i, n)
                        c.root.rotation_euler = (0, 0, math.radians(deg))
                        bpy.context.view_layer.update()
                        render_to(os.path.join(od, f"{anim}_{dn}_{i}.png"))
            bpy.data.objects.remove(cam, do_unlink=True)
            codex(c, od, 1)
        else:
            fn, cell, anchor, ppu, yaw = LEGEND[nm]
            c = build(fn, line_t=0.016)
            add_lines()
            cam = sprite_camera(cell[0], cell[1], anchor, ppu=ppu, ssaa=3)
            for i in range(4):
                c.pose('idle', i, 4)
                c.root.rotation_euler = (0, 0, math.radians(yaw))
                bpy.context.view_layer.update()
                render_to(os.path.join(od, f"idle_S_{i}.png"))
            bpy.data.objects.remove(cam, do_unlink=True)
            codex(c, od, 1)
        m = dict(c.meta)
        with open(os.path.join(od, "meta.json"), "w", encoding="utf8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
        print(f"CREATURE {nm} {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
