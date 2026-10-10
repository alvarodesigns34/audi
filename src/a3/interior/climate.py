"""Two-zone automatic climate control panel (8V 'Climatronic', 9AK).

Piano black panel under the switch strip: two temperature rotaries with
aluminium rims and integrated displays, central fan rotary, row of buttons.
Local frame: +Z toward the cabin, +X to the occupant's right (world -Y), +Y up.
"""
from __future__ import annotations

import math

import numpy as np

from . import _geo as g

COL = "Interior/Climate"


def _knob(ctx, name, M, cx, cy, r, h, ring_mat, top_mat, label=None):
    """Rotary knob: knurled aluminium rim, black cap, push button in the centre."""
    parts = []
    k = g.lathe(name, [(0, h), (r * 0.80, h), (r * 0.90, h - 0.001), (r, h - 0.003), (r, 0.0012),
                       (r + 0.0015, 0.0)],
                origin=(cx, cy, 0), segments=48, col=COL, mat=top_mat)
    parts.append(k)
    rim = g.lathe(name + "_Rim", [(r - 0.0002, h - 0.0026), (r + 0.0006, h - 0.0030),
                                   (r + 0.0006, h * 0.35), (r - 0.0002, h * 0.33)],
                  origin=(cx, cy, 0), segments=48, col=COL, mat=ring_mat)
    parts.append(rim)
    kn = g.Batch(name + "_Knurl", COL, ring_mat)
    for i in range(48):
        a = 2 * math.pi * i / 48
        c = np.array([cx + (r + 0.0007) * math.cos(a), cy + (r + 0.0007) * math.sin(a), h * 0.66])
        v, f = g.box_verts(c, np.array([math.cos(a), math.sin(a), 0]) * 0.00035,
                           np.array([-math.sin(a), math.cos(a), 0]) * 0.00035, (0, 0, h * 0.28))
        kn.add(v, f)
    parts.append(kn.build())
    btn = g.lathe(name + "_Push", [(0, h + 0.0012), (r * 0.55, h + 0.0010), (r * 0.62, h)],
                  origin=(cx, cy, 0), segments=32, col=COL, mat=ctx.mat("piano_black"))
    parts.append(btn)
    for p in parts:
        p.data.transform(M)
    if label:
        ob = g.text_mesh(name + "_Label", label, size=r * 0.42, col=COL, mat=ctx.mat("screen_ui"),
                         extrude=0.00008)
        g.set_verts(ob, g.apply_np(g.verts_of(ob) + np.array([cx, cy, h + 0.0013]), M))
    return parts


def build(ctx):
    shape = ctx.data["dash"]["shape"]
    zc = 0.735                      # E panel centre height (below the switch strip)
    Wp, Hp = 0.262, 0.070           # E panel size
    x = shape.face_x(0.0, zc) - 0.014
    nrm = g._n((-1, 0, 0.17))       # panel tilted back ~17 deg towards the driver's eyes
    M = g.frame((x, 0, zc), nrm, (0, -1, 0))
    pb = ctx.mat("piano_black")
    alu = ctx.mat("aluminium_matt")
    sat = ctx.mat("black_satin")

    surround = g.prism("Climate_Surround", g.rrect(Wp + 0.008, Hp + 0.008, 0.008, 6), -0.012, 0.0,
                       COL, alu, bevel=0.0012)
    surround.data.transform(M)
    panel = g.prism("Climate_Panel", g.rrect(Wp, Hp, 0.0065, 6), -0.010, 0.0022, COL, pb,
                    bevel=0.0010)
    panel.data.transform(M)

    kx = 0.104                      # E knob centres
    for s, side in ((-1, "L"), (1, "R")):
        _knob(ctx, f"Climate_Temp_{side}", M, s * kx, -0.004, 0.0165, 0.017, ctx.mat("knurl_alu"),
              sat, "AUTO")
        # temperature display above/inboard of each knob
        dx = s * 0.052
        d = g.prism(f"Climate_Display_{side}", g.rrect(0.040, 0.014, 0.0015, 3, (dx, 0.020)),
                    0.0022, 0.0026, COL, ctx.mat("screen"))
        d.data.transform(M)
        ob = g.text_mesh(f"Climate_Display_{side}_Text", "21.0°C", size=0.0085, col=COL,
                         mat=ctx.mat("screen_ui"), extrude=0.00008)
        g.set_verts(ob, g.apply_np(g.verts_of(ob) + np.array([dx, 0.020, 0.0027]), M))
    _knob(ctx, "Climate_Fan", M, 0.0, -0.006, 0.0115, 0.013, ctx.mat("knurl_alu"), sat)
    # button rows: 4 each side between display and fan knob + one on top centre
    btn = g.Batch("Climate_Buttons", COL, sat)
    icons = g.Batch("Climate_Button_Icons", COL, ctx.mat("screen_ui_dim"), smooth=None)
    leds = g.Batch("Climate_Button_LEDs", COL, ctx.mat("led_amber"))
    for i in range(8):
        s = -1 if i < 4 else 1
        j = i if i < 4 else i - 4
        bx = s * (0.020 + 0.0125 * (3 - j if s < 0 else j))
        by = -0.020
        b = g.rbox("tmp", (0.0105, 0.012, 0.004), (bx, by, 0.0040), 0.0018, 2, COL)
        g.set_verts(b, g.apply_np(g.verts_of(b), M))
        btn.add_object(b)
        v, f = g.box_verts((bx, by + 0.0045, 0.0061), (0.0022, 0, 0), (0, 0.0004, 0), (0, 0, 0.0001))
        leds.add(g.apply_np(v, M), f)
        # simple raised pictograms: 2-3 small bars (seat heat / fan / defrost)
        for k in range(3 if i % 2 else 2):
            v, f = g.box_verts((bx - 0.003 + 0.003 * k, by - 0.0015, 0.0061), (0.0004, 0, 0),
                               (0, 0.0025, 0), (0, 0, 0.0001))
            icons.add(g.apply_np(v, M), f)
    btn.build()
    icons.build()
    leds.build()
    # top centre: air distribution buttons
    for k, dy in enumerate((-0.010, 0.010)):
        b = g.rbox(f"Climate_AirDist_{k}", (0.016, 0.008, 0.0035), (dy, 0.022, 0.0040), 0.0015, 2, COL,
                   sat)
        b.data.transform(M)
