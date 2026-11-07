"""Message Ship cast: sailor heroes, Captain Naama, keepers Uri / Talia / Barak (Humans from v2_parts) and Bit.

Modesty: long sleeves, ankle-length skirt or long trousers, a hat / cap / scarf on every head. Nobody holds a weapon.
"""
import math

import bpy
from mathutils import Vector

from v2lib import *
from v2_parts import Human, darker, lighter
from v2_cast import SKIN
from v2_cast_npc import beard, soft_cap, scarf_neck

NAVY = "#25386a"
GOLD = "#e8b04a"


def neckerchief(h, color="#d9483a"):
    up = h.P['upper']
    th = h.torso_h
    W = h.W
    m = mat(color, pat='weave', P=dict(nu=30, fv=60), var=0.1)
    ellipsoid("nk_knot", 0.045 * W, m, up, loc=(0, -0.17 * W, th * 0.8), scale=(1.2, 0.6, 0.9))
    for s in (-1, 1):
        tube("nk_tail", [Vector((s * 0.01, -0.175 * W, th * 0.78)), Vector((s * 0.025, -0.19 * W, th * 0.68)),
                         Vector((s * 0.03, -0.188 * W, th * 0.62))], [0.034, 0.03, 0.02], m, up, seg=8, flat=0.35)


def sailor_collar(h, color=NAVY, stripe="#f4f2ec"):
    """Square middy collar on the back + V front edges."""
    up = h.P['upper']
    th = h.torso_h
    W = h.W
    m = mat(color, pat='weave', P=dict(nu=30, fv=60), var=0.08)
    box("collar_back", (0.3 * W, 0.03, 0.2), m, up, loc=(0, 0.17 * W, th * 0.86), rot=(-0.25, 0, 0), bevel=0.01)
    box("collar_st", (0.26 * W, 0.034, 0.012), mat(stripe, kind='flat', rim=0), up, loc=(0, 0.175 * W, th * 0.79),
        rot=(-0.25, 0, 0))
    for s in (-1, 1):
        tube("collar_v", [Vector((s * 0.14 * W, -0.09 * W, th * 1.0)), Vector((s * 0.05 * W, -0.172 * W, th * 0.78))],
             [0.03], m, up, seg=6, sub=1, flat=0.4)


# ====================================================================== heroes (sailor versions of game 1 looks)
def hero_girl():
    sp = dict(skin=SKIN['a'], R=0.25, iris="#4a6a8a", brow_col="#2a1a14", lip="#c0565a", blush_amt=0.5,
              head=dict(jaw=0.3, cheek=0.05, nose=0.07, chin=0.05), eye_h=0.16, flick=1.2)
    h = Human(sp)
    h.feet_only(shoe="#3a2a2a")
    h.skirt(NAVY, pat='weave', P=dict(nu=60, fv=80), hem="#f4f2ec", hem2="#d9483a", flare=1.0, folds=11)
    h.torso("#f6f4ee", pat='weave', P=dict(nu=40, fv=80), collar=NAVY, belt=NAVY)
    sailor_collar(h)
    neckerchief(h)
    h.arms("#f6f4ee", cuff=NAVY, P=dict(nu=18, fv=90))
    h.satchel(color="#8a5a36", side=1)
    h.head()
    h.hair_cap("#1e1a1a", hairline=0.5, back_len=-0.6, sides=-0.3, fringe=(4, 0.2))
    h.headscarf("#3f7fc0", color2="#f2f6fa", pat='vstripes', P=dict(nu=36, fv=30, thr=0.78), z_front=0.5)
    h.flags = dict(kind='dress', stride=1.0)
    h.portrait = dict(yaw=-24)
    return h


def hero_boy():
    sp = dict(skin=SKIN['b'], R=0.25, iris="#4a2e1e", brow_col="#1a1010", lip="#9a4a44", blush_amt=0.35,
              head=dict(jaw=0.3, cheek=0.04, nose=0.09, chin=0.07), eye_h=0.14, lash_w=0.045, flick=0.3)
    h = Human(sp)
    h.legs(NAVY, shoe="#2a2020", cuff=darker(NAVY, 0.7), pat='weave', P=dict(nu=24, fv=70), boots=True)
    h.torso("#f6f4ee", pat='stripes', color2="#2a4a8a", P=dict(nu=40, fv=36, thr=0.62, weave=False), collar=NAVY,
            belt="#8a5a36")
    sailor_collar(h)
    neckerchief(h)
    h.arms("#f6f4ee", pat='stripes', color2="#2a4a8a", P=dict(nu=18, fv=36, thr=0.62, weave=False), cuff=NAVY)
    h.satchel(color="#8a5a36", side=1)
    h.head(ears=1.0)
    h.hair_cap("#1e1414", hairline=0.56, back_len=-0.5, sides=-0.1, fringe=(7, 0.22), part=0.1)
    h.flat_cap(NAVY, color2="#f4f2ec", tilt=-0.1, z=0.46, pat='weave')
    h.flags = dict(kind='legs', stride=1.0)
    h.portrait = dict(yaw=-24)
    return h


# ====================================================================== Captain Naama
def naama():
    sp = dict(skin=SKIN['e'], R=0.245, iris="#3a5a7a", brow_col="#d8d2d6", lip="#a05a5a", blush_amt=0.45,
              head=dict(jaw=0.3, cheek=0.09, nose=0.12, chin=0.05), eye_h=0.12, eye_w=0.12, wrinkles=True,
              lash_w=0.04, flick=0.2, brow_w=0.055,
              expr_over=dict(neutral=dict(mouth=('smirk', 0.1), sq=0.25)))
    h = Human(dict(sp, H=0.98, W=1.08, torso_k=0.97))
    h.feet_only(shoe="#2a2020")
    h.skirt(NAVY, pat='weave', P=dict(nu=60, fv=70), hem=GOLD, hem2=darker(GOLD, 0.8), flare=0.95, folds=9)
    h.coat_skirt(NAVY, length=0.42, flare=0.55, P=dict(nu=40, fv=70), buttons=(GOLD, 3))
    h.torso(NAVY, P=dict(nu=40, fv=70), collar="#f3e4c4", buttons=(GOLD, 4), belt="#5e3a22")
    # epaulettes
    up = h.P['upper']
    th = h.torso_h
    for s in (-1, 1):
        ellipsoid("epaul", 0.07, mat(GOLD, pat='strands_z', P=dict(nu=10, fv=10), var=0.2), up,
                  loc=(s * 0.19 * h.W, 0.0, th * 0.97), scale=(1.2, 1.1, 0.4))
    scarf_neck(h, "#d9583a", pat='knit', color2="#f2c84a", tail=True)
    h.arms(NAVY, cuff=GOLD, P=dict(nu=18, fv=70))
    h.head()
    h.hair_cap("#dedad8", hairline=0.6, back_len=-0.45, sides=-0.05, fringe=(3, 0.1), P=dict(nu=70, wave=0.6))
    R = h.R
    ellipsoid("bun", R * 0.36, mat("#dedad8", pat='hair', kind='hair', P=dict(nu=40), var=0.3), h.P['head'],
              loc=(0, R * 0.95, -R * 0.2), seg=20, rings=14)
    h.wide_hat(NAVY, GOLD, band2="#f4f2ec", crown_h=0.5, brim=1.85, tilt=-0.32, pat='leather', P=dict(scale=26), bow=False,
               droop=0.05, wav=0.012, z=0.55)
    # little gold anchor badge on the hat band
    hat = h.P['hat']
    ellipsoid("badge", R * 0.12, mat(GOLD, metal=True), hat, loc=(0, -R * 1.06, R * 0.18), scale=(1, 0.4, 1.2))
    h.flags = dict(kind='dress', stride=0.62, elder=True)
    h.sp['eye_x'] = 0.36
    h.portrait = dict(yaw=-24, scale=1.36, dz=-0.04, elev=4)
    return h


# ====================================================================== keepers
def uri():
    """Keeper of lighthouse 1 (the five rules): wise older man, knit cap, round glasses, rule-book."""
    sp = dict(skin=SKIN['d'], R=0.25, iris="#4a3a2a", brow_col="#e8e4e0", lip="#9a5048", blush_amt=0.4, H=1.0, W=1.05,
              head=dict(jaw=0.26, cheek=0.08, nose=0.15, chin=0.03), eye_h=0.11, wrinkles=True, bushy=True, brow_w=0.06,
              lash_w=0.04, flick=0.1, mouth_z=-0.47)
    h = Human(sp)
    h.legs("#4a4a5a", shoe="#2a2020", P=dict(nu=24, fv=60), r=0.09)
    h.torso("#3f8a8a", pat='knit', P=dict(nu=40, fv=50), collar="#f3e4c4", belly=0.03)
    h.arms("#3f8a8a", pat='knit', P=dict(nu=14, fv=50), cuff="#2f6a6a")
    h.head()
    h.hair_cap("#ece8e4", hairline=0.9, back_len=-0.35, sides=-0.05, fringe=None)
    beard(h, "#f0ece8", length=0.5, width=0.52, mustache=True, mk=0.8)
    soft_cap(h, "#2a3a5a", z=0.5, puff=1.18, tilt=-0.08, side=0.05, band="#e8b04a", pat='knit')
    R = h.R
    gm = mat("#c9a040", metal=True, kind='cloth')
    for s in (-1, 1):
        ring = [Vector((s * 0.36 * R + 0.17 * R * math.cos(TAU * i / 20), -R * 1.02, 0.02 * R + 0.16 * R * math.sin(TAU * i / 20)))
                for i in range(21)]
        tube("lens", ring, [0.012], gm, h.P['head'], seg=5, sub=1, line=False)
    tube("bridge", [Vector((-0.19 * R, -R * 1.03, 0.04 * R)), Vector((0, -R * 1.06, 0.07 * R)), Vector((0.19 * R, -R * 1.03, 0.04 * R))],
         [0.01], gm, h.P['head'], seg=5, sub=3, line=False)
    # rule-book with five coloured ribbons in the left hand
    bk = pivot("book", (0, -0.05, -0.02), h.P['handL'], rot=(0.3, 0, 0.2))
    box("bk", (0.16, 0.05, 0.2), mat("#8a3a2a", pat='leather', P=dict(scale=30)), bk, bevel=0.01)
    for i, c in enumerate(("#ffb84a", "#4ad6c8", "#8f7bff", "#ff7f6e", "#7fd957")):
        box("rib", (0.012, 0.01, 0.08), mat(c, kind='soft'), bk, loc=(-0.05 + 0.025 * i, 0.0, -0.12))
    h.flags = dict(kind='legs', stride=0.7, elder=True, hold='L')
    h.portrait = dict(yaw=-24, scale=1.3)
    return h


def talia():
    """Keeper of lighthouse 2 (seven layers): headscarf in seven colour bands, teal cardigan, brass spyglass."""
    sp = dict(skin=SKIN['c'], R=0.245, iris="#5a3a2a", brow_col="#3a2018", lip="#b05a58", blush_amt=0.45,
              head=dict(jaw=0.32, cheek=0.06, nose=0.09, chin=0.05), eye_h=0.15, flick=1.0, H=1.02)
    h = Human(sp)
    h.feet_only(shoe="#4a2e20")
    h.skirt("#5a4a8a", pat='weave', P=dict(nu=60, fv=70), hem="#e8b04a", flare=0.95, folds=11)
    h.torso("#2f8a94", pat='knit', P=dict(nu=40, fv=55), collar="#f6f0e0", buttons=("#e8b04a", 4))
    h.arms("#2f8a94", pat='knit', P=dict(nu=14, fv=55), cuff="#f6f0e0")
    h.head()
    h.hair_cap("#3a2018", hairline=0.5, back_len=-0.6, sides=-0.3, fringe=(4, 0.2))
    h.headscarf("#d94f4f", color2="#e8cf3a", pat='stripes', P=dict(fv=22, thr=0.5, weave=False), z_front=0.5)
    # seven layer beads on a necklace
    up = h.P['upper']
    th = h.torso_h
    for i, c in enumerate(("#d94f4f", "#e98a3d", "#e8cf3a", "#58c46a", "#3fb5c9", "#5a7ee0", "#a566d9")):
        a = -0.9 + 1.8 * i / 6
        ellipsoid("bead", 0.022, mat(c, kind='soft', rim=0.5), up,
                  loc=(0.12 * h.W * math.sin(a), -0.16 * h.W * math.cos(a) - 0.01, th * 0.86 - 0.06 * math.cos(a)))
    sg = pivot("spy", (0, -0.04, -0.02), h.P['handR'], rot=(0.0, 0.3, 0.0))
    loft("spyglass", [(0, 0.03, 0.03), (0.22, 0.028, 0.028), (0.22, 0.035, 0.035), (0.34, 0.035, 0.035)],
         mat("#e2a844", metal=True), sg, seg=14, cap_top=True, cap_bot=True)
    h.flags = dict(kind='dress', stride=0.9, hold='R')
    h.portrait = dict(yaw=-24)
    return h


def barak():
    """Keeper of lighthouse 3 (containers): broad dock worker, orange work vest, cap, short beard."""
    sp = dict(skin=SKIN['f'], R=0.255, iris="#2a1a10", brow_col="#1a1010", lip="#8a4038", blush_amt=0.3, H=1.08, W=1.3,
              head=dict(jaw=0.22, cheek=0.06, nose=0.14, chin=0.07), eye_h=0.13, lash_w=0.045, flick=0.1, brow_w=0.065,
              expr_over=dict(neutral=dict(mouth=('smirk', 0.1))))
    h = Human(sp)
    h.legs("#3a4a5a", shoe="#2a1a10", boots=True, P=dict(nu=24, fv=60), r=0.1)
    h.torso("#5a7aa8", pat='plaid', color2="#3a5a88", P=dict(nu=24, fv=30, thr=0.8), collar="#5a7aa8", vest="#ea7a2e",
            vest_pat='weave', vest2="#f2c84a", belt="#3a2a20", bulk=1.08)
    h.arms("#5a7aa8", pat='plaid', color2="#3a5a88", P=dict(nu=10, fv=30, thr=0.8), cuff="#3a5a88", r=0.07)
    h.head(ears=1.1)
    h.hair_cap("#1a1210", hairline=0.5, back_len=-0.5, sides=-0.15, fringe=None)
    beard(h, "#1e1612", length=0.36, width=0.56, mustache=True, mk=0.9)
    h.flat_cap("#e8b04a", color2="#c48a2a", tilt=-0.1, z=0.47, pat='weave')
    # small shipping-container tag on the vest
    box("tag", (0.07, 0.01, 0.05), mat("#4ad6c8", kind='soft'), h.P['upper'], loc=(-0.08 * h.W, -0.185 * h.W, h.torso_h * 0.7))
    h.flags = dict(kind='legs', stride=0.9)
    h.portrait = dict(yaw=-22, scale=1.32)
    return h


CAST = dict(hero_girl=hero_girl, hero_boy=hero_boy, naama=naama, uri=uri, talia=talia, barak=barak)


# ====================================================================== Bit: floating lantern buddy
BIT_EXPR = {
    'neutral': dict(eye=(1.0, 1.0), lid=0.0, mouth='smile', brow=(0.0, 0.0)),
    'happy': dict(eye=(1.0, 0.0), lid=0.0, mouth='open', brow=(0.012, 0.0)),
    'worried': dict(eye=(0.9, 0.95), lid=0.0, mouth='wavy', brow=(0.03, -0.012)),
    'surprised': dict(eye=(1.25, 1.3), lid=0.0, mouth='o', brow=(0.035, 0.035)),
}


def bit(expr='neutral', frame=0):
    """Origin at the hover centre of the glass. ~0.55 units tall."""
    E = BIT_EXPR[expr]
    root = pivot("bit")
    b = pivot("bitb", (0, 0, 0.03 * math.sin(TAU * frame / 4)), root, rot=(0.05 * math.sin(TAU * frame / 4 + 1), 0, 0))
    br = mat("#e2a844", metal=True, rim=0.7)
    br2 = mat("#b8822e", metal=True, rim=0.6)
    # glass body (soft warm glow) + inner flame
    loft("glass", [(-0.16, 0.17, 0.17), (-0.1, 0.22, 0.21), (0.08, 0.22, 0.21), (0.16, 0.17, 0.17)],
         glow("#ffe2a0", 1.5), b, seg=28, cap_top=True, cap_bot=True, line=False)
    ellipsoid("core", 0.11, glow("#fff8d8", 2.6), b, loc=(0, 0.06, -0.02), line=False)
    # cage bars at the sides/back (keep the face clear)
    for k in range(6):
        a = math.pi / 2 + (k - 2.5) * 0.6   # around the back half
        a = math.pi * 0.1 + k * math.pi * 0.16
        x, y = math.cos(a + math.pi * 0.05), math.sin(a + math.pi * 0.05)
        tube("bar", [Vector((0.225 * x, 0.215 * y, -0.15)), Vector((0.235 * x, 0.225 * y, 0.0)), Vector((0.225 * x, 0.215 * y, 0.15))],
             [0.014], br, b, seg=6, sub=2, line=False)
    # cap (little roof) + ring handle + base
    loft("cap", [(0.16, 0.24, 0.23), (0.2, 0.25, 0.24), (0.3, 0.12, 0.12), (0.34, 0.04, 0.04)], br, b, seg=28, cap_top=True)
    from shiplib import ring_tube
    ring_tube("handle", (0, 0, 0.42), 0.07, 0.018, br, b, axis='y', seg=18, tseg=6)
    loft("base", [(-0.26, 0.08, 0.08), (-0.22, 0.2, 0.19), (-0.16, 0.24, 0.23)], br2, b, seg=28, cap_bot=True)
    ellipsoid("drop", 0.04, br, b, loc=(0, 0, -0.29))
    # tiny brass "arms" (curled hooks) for gesturing
    for s in (-1, 1):
        tube("arm", [Vector((s * 0.22, 0, -0.02)), Vector((s * 0.32, -0.02, 0.04 + 0.03 * math.sin(TAU * frame / 4 + s))),
                     Vector((s * 0.36, -0.03, 0.12))], [0.02, 0.016], br, b, seg=6, sub=3)
        ellipsoid("hand", 0.035, br, b, loc=(s * 0.36, -0.03, 0.13))
    # face on the glass front (-y)
    ink = mat("#3a2418", kind='flat', rim=0, ao=0, line=False)
    ex, ez = E['eye']
    y0 = -0.222
    for s in (-1, 1):
        if ez < 0.05:   # happy closed arcs
            pts = [Vector((s * 0.08 - 0.04, y0, 0.03)), Vector((s * 0.08, y0 - 0.005, 0.065)), Vector((s * 0.08 + 0.04, y0, 0.03))]
            tube("eyeA", pts, [0.012], ink, b, seg=5, sub=3, line=False)
        else:
            ellipsoid("eye", 0.032, ink, b, loc=(s * 0.08, y0, 0.04), scale=(ex, 0.3, 1.3 * ez), line=False)
            ellipsoid("eyehl", 0.011, glow("#ffffff", 1.2), b, loc=(s * 0.08 - 0.01, y0 - 0.012, 0.06), line=False)
            if E['lid'] > 0:
                tube("lid", [Vector((s * 0.08 - 0.04, y0 - 0.006, 0.07 - 0.02 * s * 0)), Vector((s * 0.08 + 0.04, y0 - 0.006, 0.07))],
                     [0.012], ink, b, seg=5, sub=1, line=False)
        bw = E['brow']
        tube("brow", [Vector((s * 0.05, y0 - 0.002, 0.11 + bw[0])),
                      Vector((s * 0.11, y0 + 0.002, 0.11 + bw[1]))], [0.008], ink, b, seg=4, sub=1, line=False)
        ellipsoid("blush", 0.03, mat("#ff8a6a", kind='flat', rim=0, line=False), b, loc=(s * 0.14, y0 + 0.01, -0.02),
                  scale=(1, 0.3, 0.6), line=False)
    m = E['mouth']
    if m == 'smile':
        tube("m", [Vector((-0.04, y0, -0.03)), Vector((0, y0 - 0.006, -0.055)), Vector((0.04, y0, -0.03))], [0.01], ink, b, seg=5,
             sub=3, line=False)
    elif m == 'open':
        ellipsoid("m", 0.05, mat("#7a2a2a", kind='flat', rim=0, line=False), b, loc=(0, y0, -0.045), scale=(1.0, 0.3, 0.7),
                  line=False)
        ellipsoid("tg", 0.025, mat("#ff8a8a", kind='flat', rim=0, line=False), b, loc=(0, y0 - 0.008, -0.065),
                  scale=(1.0, 0.3, 0.6), line=False)
    elif m == 'wavy':
        tube("m", [Vector((-0.04, y0, -0.045)), Vector((-0.015, y0, -0.035)), Vector((0.015, y0, -0.05)), Vector((0.04, y0, -0.04))],
             [0.009], ink, b, seg=5, sub=3, line=False)
    else:
        ellipsoid("m", 0.03, mat("#7a2a2a", kind='flat', rim=0, line=False), b, loc=(0, y0, -0.05), scale=(0.8, 0.3, 1.0), line=False)
    return root

