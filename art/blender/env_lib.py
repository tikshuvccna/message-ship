"""Environment art helpers: procedural-texture toon materials + building blocks.

All textures are procedural Blender shader nodes (no image files): plaster, wood planks with grain,
brick, fieldstone, thatch, roof tiles, knit/weave fabric, paper with ink lines, stripes.
They are evaluated on OBJECT-space coordinates (so pattern size is in world units, not stretched
by the mesh size) and optional WORLD-space weathering (grime near the ground, moss, soot).
The toon look matches common.toon (blue-violet shadow, warm light, amber rim) but the base colour
comes from the pattern, and bump from the pattern perturbs the diffuse normal so grain/bricks are
visible inside the toon steps.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
from mathutils import Vector
from common import *  # noqa

RAD = math.radians
_TC = {}
TRUTH = False          # facade (False) or "truth" variant (True): set via set_truth()
_common_toon = toon
_common_glow = glow


def set_truth(v):
    global TRUTH
    TRUTH = bool(v)
    _TC.clear()


def truthify(hexv):
    """Desaturate, darken and cool a colour; greens turn dead olive-brown. Teal glows are kept."""
    import colorsys
    h = hexv.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    H, S, V = colorsys.rgb_to_hsv(r, g, b)
    if 0.18 < H < 0.5:
        H, S, V = 0.11, S * 0.45, V * 0.62
    else:
        S, V = S * 0.42, V * 0.78
    r, g, b = colorsys.hsv_to_rgb(H, S, V)
    r, g, b = r * 0.82 + 0.10 * 0.55, g * 0.86 + 0.14 * 0.55, b * 0.95 + 0.22 * 0.55   # cold blue-grey wash
    return "#%02x%02x%02x" % tuple(int(min(1, c) * 255) for c in (r, g, b))


def _hex(c):
    return PAL.get(c, c)


def toon(color, rim=0.35, shade=(0.40, 0.36, 0.66), name=None):
    if TRUTH:
        color = truthify(_hex(color))
        rim *= 0.5
    return _common_toon(color, rim=rim, shade=shade, name=name)


def glow(color, strength=4.0, alpha=1.0, name=None, soft=False):
    m = _glow(color, strength, alpha, name, soft)
    if alpha < 0.999:
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    return m


def _glow(color, strength=4.0, alpha=1.0, name=None, soft=False):
    if TRUTH:
        hv = _hex(color).lstrip('#').lower()
        r, g, b = (int(hv[i:i + 2], 16) for i in (0, 2, 4))
        if g > r and b > r * 0.7 and g > 150:        # teal/green magic stays (but dimmer)
            return _common_glow(color, strength * 0.7, alpha, name, soft)
        return _common_glow(truthify(_hex(color)), strength * 0.22, alpha, name, soft)
    return _common_glow(color, strength, alpha, name, soft)


def _n(nt, typ, **props):
    nd = nt.nodes.new(typ)
    for k, v in props.items():
        setattr(nd, k, v)
    return nd


def _lk(nt, a, b):
    nt.links.new(a, b)


def _mix(nt, blend, fac, a, b):
    """Colour mix node; fac/a/b may be socket or constant."""
    m = _n(nt, "ShaderNodeMix", data_type="RGBA", blend_type=blend)
    for idx, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)) and idx == 0:
            m.inputs[0].default_value = v
        elif isinstance(v, (tuple, list)):
            m.inputs[idx].default_value = v
        elif hasattr(v, "node"):
            _lk(nt, v, m.inputs[idx])
    return m.outputs[2]


def _maprange(nt, val, a0, a1, b0, b1, clamp=True):
    m = _n(nt, "ShaderNodeMapRange", clamp=clamp)
    m.inputs["From Min"].default_value = a0
    m.inputs["From Max"].default_value = a1
    m.inputs["To Min"].default_value = b0
    m.inputs["To Max"].default_value = b1
    _lk(nt, val, m.inputs["Value"])
    return m.outputs["Result"]


def _ramp(nt, fac, stops, interp="LINEAR"):
    """stops = [(pos, '#hex' or rgb tuple), ...]"""
    r = _n(nt, "ShaderNodeValToRGB")
    r.color_ramp.interpolation = interp
    el = r.color_ramp.elements
    while len(el) < len(stops):
        el.new(0.5)
    for e, (p, c) in zip(el, stops):
        e.position = p
        e.color = (*(srgb(c) if isinstance(c, str) else c), 1)
    _lk(nt, fac, r.inputs["Fac"])
    return r.outputs["Color"]


def _noise(nt, vec, scale, detail=4, rough=0.55, dist=0.0):
    nz = _n(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rough
    nz.inputs["Distortion"].default_value = dist
    _lk(nt, vec, nz.inputs["Vector"])
    return nz.outputs["Fac"]


def _bw(nt, col):
    b = _n(nt, "ShaderNodeRGBToBW")
    _lk(nt, col, b.inputs["Color"])
    return b.outputs["Val"]


def _mulk(nt, col, fac, lo, hi):
    k = _maprange(nt, fac, 0, 1, lo, hi)
    return _mix(nt, "MULTIPLY", 1.0, col, k)


def _math(nt, op, a, b=None, clamp=False):
    m = _n(nt, "ShaderNodeMath", operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            _lk(nt, v, m.inputs[i])
    return m.outputs["Value"]


def tex_toon(kind, c1, c2=None, c3=None, scale=4.0, plane="xz", stretch=(1, 1), bump=0.0, wear=0.0,
             moss=0.0, soot=0.0, rim=0.3, seed=0.0, shade=(0.40, 0.36, 0.66), ao=0.5, along="u",
             detail=1.0, name=None):
    """Textured toon material. kind: plain plaster wood brick stone thatch tiles knit weave paper stripes cobble"""
    c2 = c2 or c1
    if TRUTH:
        c1, c2 = truthify(c1), truthify(c2)
        c3 = truthify(c3) if c3 else None
        wear = max(wear, 0.9)
        rim *= 0.5
        shade = (0.32, 0.34, 0.6)
    key = ("tt", TRUTH, kind, c1, c2, c3, scale, plane, stretch, bump, wear, moss, soot, rim, seed, shade, ao, along, detail)
    if key in _TC:
        return _TC[key]
    m = bpy.data.materials.new(name or f"tx_{kind}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial")
    emit = _n(nt, "ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.12
    # --- texture coordinates (object space, remapped to plane)
    tc = _n(nt, "ShaderNodeTexCoord")
    sep = _n(nt, "ShaderNodeSeparateXYZ")
    _lk(nt, tc.outputs["Object"], sep.inputs["Vector"])
    ax = {"xz": ("X", "Z"), "xy": ("X", "Y"), "yz": ("Y", "Z")}[plane]
    comb = _n(nt, "ShaderNodeCombineXYZ")
    _lk(nt, sep.outputs[ax[0]], comb.inputs["X"])
    _lk(nt, sep.outputs[ax[1]], comb.inputs["Y"])
    comb.inputs["Z"].default_value = seed * 3.7 + 0.31
    mp = _n(nt, "ShaderNodeMapping", vector_type="POINT")
    mp.inputs["Scale"].default_value = (scale * stretch[0], scale * stretch[1], scale)
    mp.inputs["Location"].default_value = (seed * 1.3, seed * 0.7, 0)
    _lk(nt, comb.outputs["Vector"], mp.inputs["Vector"])
    uv = mp.outputs["Vector"]

    def stretched(sx, sy):
        mm = _n(nt, "ShaderNodeMapping", vector_type="POINT")
        mm.inputs["Scale"].default_value = (sx, sy, 1)
        _lk(nt, uv, mm.inputs["Vector"])
        return mm.outputs["Vector"]

    A, B = srgb(c1), srgb(c2)
    col = None
    hgt = None
    if kind == "plain":
        n1 = _noise(nt, uv, 0.8, 3)
        col = _mix(nt, "MIX", _ramp(nt, n1, [(0.3, (0, 0, 0)), (0.7, (1, 1, 1))]), (*A, 1), (*B, 1))
        hgt = n1
    elif kind == "plaster":
        n1 = _noise(nt, uv, 0.6, 5, 0.6, 0.4)
        n2 = _noise(nt, uv, 14 * detail, 2, 0.5)
        n3 = _noise(nt, stretched(1, 0.18), 3, 3, 0.5, 0.2)   # vertical water-stain streaks
        col = _mix(nt, "MIX", _ramp(nt, n1, [(0.35, (0, 0, 0)), (0.65, (1, 1, 1))]), (*A, 1), (*B, 1))
        col = _mulk(nt, col, n2, 0.88, 1.08)
        col = _mulk(nt, col, n3, 0.86, 1.04)
        hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", n2, 0.5), _math(nt, "MULTIPLY", n1, 0.3))
    elif kind == "wood":
        # planks (brick texture with long bricks) + stretched grain noise + wave rings
        uvp = uv
        if along == "v":
            sw = _n(nt, "ShaderNodeMapping", vector_type="POINT")
            sw.inputs["Rotation"].default_value = (0, 0, RAD(90))
            _lk(nt, uv, sw.inputs["Vector"])
            uvp = sw.outputs["Vector"]
        br = _n(nt, "ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0)
        br.inputs["Color1"].default_value = (*A, 1)
        br.inputs["Color2"].default_value = (*B, 1)
        br.inputs["Mortar"].default_value = (*(srgb(c3) if c3 else (A[0] * .25, A[1] * .22, A[2] * .3)), 1)
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.018
        br.inputs["Mortar Smooth"].default_value = 0.1
        br.inputs["Bias"].default_value = 0.0
        br.inputs["Brick Width"].default_value = 3.2
        br.inputs["Row Height"].default_value = 0.34
        _lk(nt, uvp, br.inputs["Vector"])
        gv = _n(nt, "ShaderNodeMapping", vector_type="POINT")
        gv.inputs["Scale"].default_value = (0.16, 5.5, 1) if along == "u" else (5.5, 0.16, 1)
        _lk(nt, uv, gv.inputs["Vector"])
        g1 = _noise(nt, gv.outputs["Vector"], 2.4, 5, 0.6, 1.2)
        wv = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y" if along == "u" else "X",
                wave_profile="SIN")
        wv.inputs["Scale"].default_value = 1.6
        wv.inputs["Distortion"].default_value = 5
        wv.inputs["Detail"].default_value = 2
        _lk(nt, uv, wv.inputs["Vector"])
        grain = _math(nt, "ADD", _math(nt, "MULTIPLY", g1, 0.6), _math(nt, "MULTIPLY", wv.outputs["Fac"], 0.4))
        col = _mulk(nt, br.outputs["Color"], grain, 0.78, 1.12)
        hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", grain, 0.35), _math(nt, "MULTIPLY", br.outputs["Fac"], 0.8))
    elif kind == "brick":
        br = _n(nt, "ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0)
        br.inputs["Color1"].default_value = (*A, 1)
        br.inputs["Color2"].default_value = (*B, 1)
        br.inputs["Mortar"].default_value = (*(srgb(c3) if c3 else srgb("#d9c9a8")), 1)
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.035
        br.inputs["Mortar Smooth"].default_value = 0.15
        br.inputs["Bias"].default_value = 0.1
        br.inputs["Brick Width"].default_value = 0.9
        br.inputs["Row Height"].default_value = 0.42
        _lk(nt, uv, br.inputs["Vector"])
        n2 = _noise(nt, uv, 9, 4, 0.6)
        col = _mulk(nt, br.outputs["Color"], n2, 0.82, 1.1)
        hgt = _math(nt, "ADD", br.outputs["Fac"], _math(nt, "MULTIPLY", n2, 0.25))
    elif kind in ("stone", "cobble"):
        wob = _n(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
        wob.inputs["Scale"].default_value = 2.0
        wob.inputs["Detail"].default_value = 3
        _lk(nt, uv, wob.inputs["Vector"])
        vadd = _n(nt, "ShaderNodeVectorMath", operation="ADD")
        _lk(nt, uv, vadd.inputs[0])
        sc = _n(nt, "ShaderNodeVectorMath", operation="SCALE")
        sc.inputs["Scale"].default_value = 0.12
        _lk(nt, wob.outputs["Color"], sc.inputs[0])
        _lk(nt, sc.outputs["Vector"], vadd.inputs[1])
        vv = vadd.outputs["Vector"]
        if kind == "stone":   # squash horizontally: wider than tall courses
            sq = _n(nt, "ShaderNodeMapping", vector_type="POINT")
            sq.inputs["Scale"].default_value = (0.8, 1.25, 1)
            _lk(nt, vv, sq.inputs["Vector"])
            vv = sq.outputs["Vector"]
        ve = _n(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="DISTANCE_TO_EDGE")
        _lk(nt, vv, ve.inputs["Vector"])
        vc = _n(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
        _lk(nt, vv, vc.inputs["Vector"])
        mask = _maprange(nt, ve.outputs["Distance"], 0.03, 0.11, 0.0, 1.0)
        rnd = _bw(nt, vc.outputs["Color"])
        stone = _mix(nt, "MIX", _ramp(nt, rnd, [(0.2, (0, 0, 0)), (0.8, (1, 1, 1))]), (*A, 1), (*B, 1))
        n2 = _noise(nt, uv, 16, 3)
        stone = _mulk(nt, stone, n2, 0.84, 1.08)
        mort = (*(srgb(c3) if c3 else (A[0] * 0.4, A[1] * 0.38, A[2] * 0.45)), 1)
        col = _mix(nt, "MIX", mask, mort, stone)
        # rounded stones: bump dome from edge distance
        hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", mask, 1.0), _math(nt, "MULTIPLY", n2, 0.2))
    elif kind == "thatch":
        # streaks run down the slope (plane xy: slope along v)
        s1 = _noise(nt, stretched(1.0, 0.07 if False else 0.10), 14, 4, 0.6, 0.3)
        s2 = _noise(nt, stretched(0.5, 0.05), 6, 3, 0.5)
        wv = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y", wave_profile="SAW")
        wv.inputs["Scale"].default_value = 0.9
        wv.inputs["Distortion"].default_value = 1.2
        _lk(nt, uv, wv.inputs["Vector"])
        col = _mix(nt, "MIX", _ramp(nt, s1, [(0.3, (0, 0, 0)), (0.7, (1, 1, 1))]), (*A, 1), (*B, 1))
        col = _mulk(nt, col, wv.outputs["Fac"], 0.72, 1.06)
        col = _mulk(nt, col, s2, 0.85, 1.08)
        hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", s1, 0.7), _math(nt, "MULTIPLY", wv.outputs["Fac"], 0.5))
    elif kind == "tiles":
        br = _n(nt, "ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0)
        br.inputs["Color1"].default_value = (*A, 1)
        br.inputs["Color2"].default_value = (*B, 1)
        br.inputs["Mortar"].default_value = (*(srgb(c3) if c3 else (A[0] * .35, A[1] * .3, A[2] * .4)), 1)
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.04
        br.inputs["Mortar Smooth"].default_value = 0.12
        br.inputs["Bias"].default_value = 0.0
        br.inputs["Brick Width"].default_value = 0.8
        br.inputs["Row Height"].default_value = 0.55
        _lk(nt, uv, br.inputs["Vector"])
        # darker lower edge of each tile row (shingle shadow): fract-like via wave saw along v
        wv = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y", wave_profile="SAW")
        wv.inputs["Scale"].default_value = 0.57
        wv.inputs["Distortion"].default_value = 0.0
        _lk(nt, uv, wv.inputs["Vector"])
        n2 = _noise(nt, uv, 6, 4, 0.55)
        col = _mulk(nt, br.outputs["Color"], wv.outputs["Fac"], 0.7, 1.08)
        col = _mulk(nt, col, n2, 0.8, 1.1)
        hgt = _math(nt, "ADD", br.outputs["Fac"], wv.outputs["Fac"])
    elif kind in ("knit", "weave"):
        if kind == "knit":
            br = _n(nt, "ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0)
            br.inputs["Color1"].default_value = (*A, 1)
            br.inputs["Color2"].default_value = (*B, 1)
            br.inputs["Mortar"].default_value = (*(srgb(c3) if c3 else (A[0] * .45, A[1] * .4, A[2] * .5)), 1)
            br.inputs["Scale"].default_value = 1.0
            br.inputs["Mortar Size"].default_value = 0.09
            br.inputs["Mortar Smooth"].default_value = 0.5
            br.inputs["Bias"].default_value = 0.0
            br.inputs["Brick Width"].default_value = 0.6
            br.inputs["Row Height"].default_value = 0.8
            _lk(nt, uv, br.inputs["Vector"])
            n2 = _noise(nt, uv, 3, 3)
            col = _mulk(nt, br.outputs["Color"], n2, 0.85, 1.1)
            hgt = br.outputs["Fac"]
        else:
            wx = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X", wave_profile="SIN")
            wx.inputs["Scale"].default_value = 1.0
            wy = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y", wave_profile="SIN")
            wy.inputs["Scale"].default_value = 1.0
            _lk(nt, uv, wx.inputs["Vector"])
            _lk(nt, uv, wy.inputs["Vector"])
            ck = _n(nt, "ShaderNodeTexChecker")
            ck.inputs["Scale"].default_value = 0.5
            _lk(nt, uv, ck.inputs["Vector"])
            f = _math(nt, "ADD", _math(nt, "MULTIPLY", wx.outputs["Fac"], ck.outputs["Fac"]),
                      _math(nt, "MULTIPLY", wy.outputs["Fac"], _math(nt, "SUBTRACT", 1.0, ck.outputs["Fac"])))
            n2 = _noise(nt, uv, 0.25, 3)
            col = _mix(nt, "MIX", f, (*A, 1), (*B, 1))
            col = _mulk(nt, col, n2, 0.85, 1.1)
            hgt = f
    elif kind == "checker":
        ck = _n(nt, "ShaderNodeTexChecker")
        ck.inputs["Scale"].default_value = 0.5
        _lk(nt, uv, ck.inputs["Vector"])
        ve = _n(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="DISTANCE_TO_EDGE")
        _lk(nt, uv, ve.inputs["Vector"])
        n2 = _noise(nt, uv, 6, 4, 0.55)
        # grout lines where either coordinate is near an integer: use a brick of width 1 height 1 as grout mask
        br = _n(nt, "ShaderNodeTexBrick", offset=0.0, offset_frequency=2, squash=1.0)
        br.inputs["Color1"].default_value = (1, 1, 1, 1)
        br.inputs["Color2"].default_value = (1, 1, 1, 1)
        br.inputs["Mortar"].default_value = (0.25, 0.25, 0.3, 1)
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.03
        br.inputs["Brick Width"].default_value = 1.0
        br.inputs["Row Height"].default_value = 1.0
        _lk(nt, uv, br.inputs["Vector"])
        col = _mix(nt, "MIX", ck.outputs["Fac"], (*A, 1), (*B, 1))
        col = _mix(nt, "MULTIPLY", 1.0, col, br.outputs["Color"])
        col = _mulk(nt, col, n2, 0.86, 1.08)
        hgt = _math(nt, "ADD", br.outputs["Fac"], _math(nt, "MULTIPLY", n2, 0.2))
    elif kind == "paper":
        n1 = _noise(nt, uv, 1.0, 3)
        n2 = _noise(nt, uv, 40, 2)
        ln = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y", wave_profile="SAW")
        ln.inputs["Scale"].default_value = 0.9
        _lk(nt, uv, ln.inputs["Vector"])
        lmask = _maprange(nt, ln.outputs["Fac"], 0.55, 0.62, 0, 1)
        brk = _maprange(nt, _noise(nt, stretched(1.0, 0.3), 5, 2), 0.42, 0.55, 0, 1)
        ink = _math(nt, "MULTIPLY", lmask, brk)
        col = _mulk(nt, (*A, 1) if False else _mix(nt, "MIX", n1, (*A, 1), (*A, 1)), n2, 0.93, 1.04)
        col = _mix(nt, "MIX", ink, col, (*B, 1))
        hgt = n2
    elif kind == "stripes":
        wv = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X", wave_profile="SAW")
        wv.inputs["Scale"].default_value = 0.5
        _lk(nt, uv, wv.inputs["Vector"])
        sm = _ramp(nt, wv.outputs["Fac"], [(0.49, (0, 0, 0)), (0.51, (1, 1, 1))])
        n2 = _noise(nt, uv, 22, 2)
        col = _mix(nt, "MIX", sm, (*A, 1), (*B, 1))
        col = _mulk(nt, col, n2, 0.9, 1.06)
        hgt = n2
    else:
        raise ValueError(kind)

    # --- weathering in WORLD space
    if wear > 0 or moss > 0 or soot > 0:
        geo = _n(nt, "ShaderNodeNewGeometry")
        wsep = _n(nt, "ShaderNodeSeparateXYZ")
        _lk(nt, geo.outputs["Position"], wsep.inputs["Vector"])
        wz = wsep.outputs["Z"]
        if wear > 0:
            low = _maprange(nt, wz, 0.0, 0.9, 1.0 - 0.5 * wear, 1.0)
            col = _mix(nt, "MULTIPLY", 1.0, col, low)
            wn = _noise(nt, geo.outputs["Position"], 4, 5)
            col = _mulk(nt, col, wn, 1.0 - 0.28 * wear, 1.02)
        if moss > 0:
            mn = _noise(nt, geo.outputs["Position"], 5, 6, 0.6, 0.3)
            mm = _math(nt, "MULTIPLY", _maprange(nt, mn, 0.5, 0.72, 0, 1),
                       _maprange(nt, wz, 0.1, 1.6, 1.0, 0.0))
            mm = _math(nt, "MULTIPLY", mm, moss)
            mcol = _ramp(nt, _noise(nt, geo.outputs["Position"], 22, 3),
                         [(0.3, "#46742f"), (0.7, "#7fa84a")])
            col = _mix(nt, "MIX", _math(nt, "MINIMUM", mm, 0.92), col, mcol)
        if soot > 0:
            sn = _noise(nt, geo.outputs["Position"], 7, 4)
            smask = _math(nt, "MULTIPLY", _maprange(nt, sn, 0.35, 0.8, 0, 1), soot)
            col = _mix(nt, "MIX", smask, col, (0.04, 0.03, 0.05, 1))

    if TRUTH and kind in ("plaster", "stone", "brick", "cobble", "plain", "tiles", "thatch"):
        cv = _n(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="DISTANCE_TO_EDGE")
        cv.inputs["Scale"].default_value = 1.6
        wv2 = _noise(nt, uv, 3.0, 3)
        _lk(nt, uv, cv.inputs["Vector"])
        crack = _maprange(nt, cv.outputs["Distance"], 0.0, 0.035, 0.0, 1.0)
        crack = _math(nt, "MAXIMUM", crack, _maprange(nt, wv2, 0.35, 0.65, 0.35, 1.0))
        col = _mix(nt, "MIX", _maprange(nt, crack, 0, 1, 1, 0), col, (0.05, 0.05, 0.09, 1))
        dust = _maprange(nt, _noise(nt, uv, 2.5, 4), 0.45, 0.8, 0.0, 0.35)
        col = _mix(nt, "MIX", dust, col, (0.45, 0.47, 0.52, 1))
    # --- toon shading: diffuse (+bump) -> shader-to-rgb -> luminance -> tint ramp
    diff = _n(nt, "ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    if bump > 0:
        bp = _n(nt, "ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.05
        _lk(nt, hgt, bp.inputs["Height"])
        _lk(nt, bp.outputs["Normal"], diff.inputs["Normal"])
    s2r = _n(nt, "ShaderNodeShaderToRGB")
    _lk(nt, diff.outputs["BSDF"], s2r.inputs["Shader"])
    lum = _bw(nt, s2r.outputs["Color"])
    if ao > 0:
        aon = _n(nt, "ShaderNodeAmbientOcclusion", samples=4)
        aon.inputs["Distance"].default_value = 0.6
        akk = _maprange(nt, aon.outputs["AO"], 0, 1, 1.0 - ao, 1.0)
        lum = _math(nt, "MULTIPLY", lum, akk)
    tint = _ramp(nt, lum, [(0.16, (shade[0], shade[1], shade[2])), (0.55, (0.86, 0.86, 0.86)),
                           (0.92, (1.0, 0.97, 0.88))])
    last = _mix(nt, "MULTIPLY", 1.0, col, tint)
    if rim > 0:
        lw = _n(nt, "ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.35
        rm = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", lw.outputs["Fresnel"], rim), lum)
        last = _mix(nt, "ADD", rm, last, (*srgb("#ffb860"), 1))
    _lk(nt, last, emit.inputs["Color"])
    _lk(nt, emit.outputs["Emission"], out.inputs["Surface"])
    _TC[key] = m
    return m


def reset_env():
    _TC.clear()
    reset_scene()


# ------------------------------------------------------------ lighting rigs
def env_lights(key_col="#ffc98a", key_e=3.2, rim_col="#8fa8ff", rim_e=1.0, world="#7a6fb0", world_e=0.55,
               key_dir=(-0.9, -0.8, 1.2)):
    if TRUTH:
        key_col, key_e, rim_col, rim_e, world, world_e = "#9fb4d8", key_e * 0.62, "#6f8fd0", 1.2, "#4a5a82", 0.5
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb(world), 1)
    bg.inputs["Strength"].default_value = world_e
    sc.world = w

    def sun(name, frm, color, energy, angle=0.25):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = angle
        o = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(o)
        d = -Vector(frm)
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = d.to_track_quat('-Z', 'Y')
        return o
    sun("key", key_dir, srgb(key_col), key_e)
    sun("rim", (0.8, 1.0, 0.7), srgb(rim_col), rim_e)


def project(x, y, z, anchor, ppu=PPU):
    """World point -> pixel (in final cell) for the standard oblique camera."""
    e = math.radians(ELEVATION_DEG)
    return (anchor[0] + x * ppu, anchor[1] - (z * math.cos(e) + y * math.sin(e)) * ppu)


# ------------------------------------------------------------ geometry blocks
def sloped_roof(name, w, d, h, ov, mat, parent, loc=(0, 0, 0), ends=True, ridge_x=True):
    """Gable roof; ridge along X (ridge_x) else along Y. Eaves at z=0 (local)."""
    W, D = w / 2 + ov, d / 2 + ov
    if ridge_x:
        v = [(-W, -D, 0), (W, -D, 0), (W, D, 0), (-W, D, 0), (-W, 0, h), (W, 0, h)]
        f = [(0, 1, 5, 4), (3, 4, 5, 2)] + ([(0, 4, 3), (1, 2, 5)] if ends else [])
    else:
        v = [(-W, -D, 0), (W, -D, 0), (W, D, 0), (-W, D, 0), (0, -D, h), (0, D, h)]
        f = [(0, 4, 5, 3), (1, 2, 5, 4)] + ([(0, 1, 4), (3, 5, 2)] if ends else [])
    return mesh_obj(name, v, f, mat, parent, loc, smooth=False)


def hip_roof(name, w, d, h, mat, parent, loc=(0, 0, 0), ridge_frac=0.0):
    """Four-sided roof with eaves rectangle w x d at z=0 and a ridge of length ridge_frac*w at the top."""
    W, D = w / 2, d / 2
    r = ridge_frac * W
    v = [(-W, -D, 0), (W, -D, 0), (W, D, 0), (-W, D, 0), (-r, 0, h), (r, 0, h)]
    f = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    return mesh_obj(name, v, f, mat, parent, loc, smooth=False)


def cone_roof(name, r, h, mat, parent, loc=(0, 0, 0), seg=24, r_top=0.0, ov=0.0):
    return frustum(name, r + ov, r_top, h, mat, parent, loc=loc, seg=seg, caps=(False, False), smooth=True)


def plane(name, p0, p1, p2, p3, mat, parent=None):
    return mesh_obj(name, [p0, p1, p2, p3], [(0, 1, 2, 3)], mat, parent, smooth=False)


def sphere(name, r, mat, parent, loc, scale=(1, 1, 1), seg=14, rings=10):
    return ellipsoid(name, r, mat, parent, loc=loc, scale=scale, seg=seg, rings=rings)


def tube(name, pts, r, mat, parent=None, res=3):
    """Poly/bezier-free tube through points using bevelled curve (round cross-section)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q[0], q[1], q[2], 1)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.data.materials.append(mat)
    return ob


def soft_glow(parent, loc, r, color="amber", strength=3, alpha=0.9, scale=(1, 1, 1)):
    return ellipsoid("halo", r, glow(color, strength, alpha=alpha, soft=True), parent, loc=loc, scale=scale,
                     seg=14, rings=10)


def no_shadow(obj):
    for o in [obj] + list(obj.children_recursive):
        try:
            o.visible_shadow = False
        except Exception:
            pass


def render_scene(cell, anchor, path, samples=24, lights=None):
    setup_render(samples=samples)
    setup_camera(cell[0], cell[1], anchor=anchor)
    bpy.context.view_layer.update()
    render_to(path)
