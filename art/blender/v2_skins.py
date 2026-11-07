"""Shop skins for the two apprentices: the same models with other colours, hair and headwear (10 per look).
Names are `skin_<girl|boy>_<id>`; render with `v2_render.py sprite <names> <rawdir>`. Modesty rules are unchanged:
long sleeves, long skirt or trousers, a hat, cap or scarf on every head."""
from v2lib import *
from v2_parts import Human, darker, lighter
from v2_cast import SKIN

# id: (he name, dress, hem, apron, hair, headwear kind, color, color2)
GIRLS = {
    'amber': ("אמבר", "#d9822b", "#f0c45a", "#f6ecd2", "#3a2418", 'hat', "#e1b865", "#8a3b1e"),
    'sea': ("ים", "#2f5f9a", "#d8e6f0", "#f3efe4", "#1e1a1a", 'scarf', "#5a9ad0", "#f2f6fa"),
    'rose': ("ורד", "#c25a7d", "#f5d6a0", "#fff3e0", "#c9a35a", 'hat', "#f0d9a8", "#c25a7d"),
    'forest': ("יער", "#3d7a4f", "#d9b660", "#efe6c8", "#9a4a22", 'hat', "#b89a5a", "#2d5a3a"),
    'violet': ("סגול", "#7a56b0", "#e8c8f0", "#f4ecf8", "#2a1a3a", 'scarf', "#b69be0", "#f6e6a8"),
    'sun': ("שמש", "#e8b82e", "#a8521e", "#fff6dc", "#5a3020", 'hat', "#f2d27a", "#a8521e"),
    'night': ("לילה", "#243a6a", "#9ab4e8", "#cfd8ec", "#101018", 'scarf', "#2c3f78", "#ffd86a"),
    'berry': ("פירות יער", "#8a2a4a", "#e8a0b0", "#f6e4dc", "#4a2016", 'hat', "#c8a070", "#8a2a4a"),
    'snow': ("שלג", "#8fb6d9", "#ffffff", "#ffffff", "#d8d8e0", 'scarf', "#c4dcef", "#6f9cc4"),
    'poppy': ("פרג", "#c8402e", "#f6e0a0", "#fff0d8", "#3a2014", 'hat', "#e8c878", "#2a6a4a"),
}
# id: (he name, coat, trousers, hair, headwear kind, color, color2)
BOYS = {
    'moss': ("אזוב", "#5d7a3a", "#4a3a2a", "#2e2020", 'cap', "#8a6a3a", "#5a4020"),
    'navy': ("כחול עמוק", "#2a4a8a", "#3a3a4a", "#1e1414", 'cap', "#d8d8e0", "#9aa4b8"),
    'rust': ("חלודה", "#b5532a", "#4a3a30", "#5a3a20", 'hat', "#6a4a3a", "#2a1e1a"),
    'sand': ("חול", "#c8a468", "#6a5a46", "#3a2a1a", 'cap', "#8a6a3a", "#5a4020"),
    'plum': ("שזיף", "#6a3a6a", "#3a2a40", "#1a1218", 'hat', "#4a3a4a", "#e8b04a"),
    'sky': ("שמיים", "#5a9ad0", "#4a5a7a", "#c9a35a", 'cap', "#f2d27a", "#b08a30"),
    'ember': ("גחלת", "#9a2a22", "#3a2a26", "#2a1a14", 'cap', "#2a2a2a", "#e8b04a"),
    'teal': ("טורקיז", "#2f9a8a", "#2a4a4a", "#6a3a20", 'hat', "#e1b865", "#2f7d6f"),
    'ash': ("אפר", "#6a6e78", "#3a3c44", "#1a1a1a", 'cap', "#aab0bc", "#7a8090"),
    'gold': ("זהב", "#d9a22e", "#5a4030", "#3a1e10", 'hat', "#f0d078", "#8a3b1e"),
}


def girl(spec):
    _, dress, hem, apron, hair, kind, c1, c2 = spec
    sp = dict(skin=SKIN['a'], R=0.25, iris="#5a7a3a", brow_col=darker(hair, 0.8), lip="#c0565a", blush_amt=0.5,
              head=dict(jaw=0.3, cheek=0.05, nose=0.07, chin=0.05), eye_h=0.16, flick=1.2)
    h = Human(sp)
    h.feet_only(shoe="#5a3420")
    h.skirt(dress, pat='weave', P=dict(nu=60, fv=80), hem=hem, hem2=darker(hem, 0.8), flare=1.0, folds=11)
    h.apron(apron, pat='weave', P=dict(nu=40, fv=90), length=0.42, width=0.8, pocket=darker(apron, 0.93))
    h.torso(dress, pat='weave', P=dict(nu=40, fv=80), collar=apron, belt=hem)
    h.arms(apron, cuff=hem, P=dict(nu=18, fv=90))
    h.satchel(side=1)
    h.head()
    if kind == 'hat':
        h.hair_cap(hair, hairline=0.5, back_len=-0.6, sides=-0.3, fringe=(4, 0.2))
        for s in (-1, 1):
            pts = [(s * 0.78, 0.3, -0.4), (s * 0.9, 0.12, -0.8), (s * 0.92, -0.05, -1.2), (s * 0.88, -0.12, -1.5)]
            h.braid(pts, 0.2, hair, tie=c2)
        h.wide_hat(c1, c2, band2=hem, crown_h=0.52, brim=1.9, tilt=-0.16, flower=None, bow=True, droop=0.06, z=0.52)
    else:
        h.hair_cap(hair, hairline=0.5, back_len=-0.6, sides=-0.3, fringe=(4, 0.2))
        h.headscarf(c1, color2=c2, pat='flowers', P=dict(nu=22, fv=30, rad=0.3), z_front=0.5)
    h.needle(h.P['handR'])
    h.flags = dict(kind='dress', stride=1.0, hold='R')
    return h


def boy(spec):
    _, coat, trousers, hair, kind, c1, c2 = spec
    sp = dict(skin=SKIN['b'], R=0.25, iris="#4a2e1e", brow_col=darker(hair, 0.8), lip="#9a4a44", blush_amt=0.35,
              head=dict(jaw=0.3, cheek=0.04, nose=0.09, chin=0.07), eye_h=0.14, lash_w=0.045, flick=0.3)
    h = Human(sp)
    h.legs(trousers, shoe="#5e3a22", cuff=darker(trousers, 0.7), pat='weave', P=dict(nu=24, fv=70), boots=True)
    h.coat_skirt(coat, length=0.2, flare=0.6, P=dict(nu=40, fv=70))
    h.torso(coat, pat='weave', P=dict(nu=40, fv=70), collar="#f3e4c4", belt="#8a5a36", buttons=("#e8b04a", 3))
    h.arms(coat, cuff="#e8b04a", P=dict(nu=18, fv=70))
    h.satchel(side=1)
    h.head(ears=1.0)
    h.hair_cap(hair, hairline=0.56, back_len=-0.5, sides=-0.1, fringe=(7, 0.22), part=0.1)
    if kind == 'cap':
        h.flat_cap(c1, color2=c2, tilt=-0.1, z=0.46)
    else:
        h.wide_hat(c1, c2, crown_h=0.6, brim=1.7, tilt=-0.1, pat='leather', P=dict(scale=30), bow=False, droop=0.05,
                   wav=0.015, z=0.5)
    h.needle(h.P['handR'])
    h.flags = dict(kind='legs', stride=1.0, hold='R')
    return h


CAST = {}
for _k, _v in GIRLS.items():
    CAST[f"skin_girl_{_k}"] = (lambda v=_v: girl(v))
for _k, _v in BOYS.items():
    CAST[f"skin_boy_{_k}"] = (lambda v=_v: boy(v))
NAMES = {f"skin_girl_{k}": v[0] for k, v in GIRLS.items()} | {f"skin_boy_{k}": v[0] for k, v in BOYS.items()}
