"""Retractable 7" MMI screen (8V pre-facelift), shown deployed.

The 11 mm thin housing rises out of a slot in the centre of the dash top.
Local frame: origin at the slot centre on the dash top, +Z toward the
occupants along the screen normal, +Y up the screen, +X to the right as seen
by the occupants (world -Y).
"""
from __future__ import annotations

import math

import numpy as np

from . import _geo as g
from . import layout

COL = "Interior/MMI"


def build(ctx):
    L = layout.get(ctx)
    shape = ctx.data["dash"]["shape"]
    W, H = L.mmi_size                  # 175 x 110 mm (E)
    T = L.mmi_thick                    # 11 mm (S/E)
    xs = L.mmi_slot_x
    zs = shape.top_z(xs, 0.0)
    tilt = math.radians(L.mmi_tilt_deg)
    # screen normal leans back: tilt about +Y (top moves forward, +x)
    nrm = np.array([-math.cos(tilt), 0.0, math.sin(tilt)])
    up = np.array([math.sin(tilt), 0.0, math.cos(tilt)])
    # the housing extends ~12 mm into the slot; visible height = H
    origin = np.array([xs, 0.0, zs]) + up * (H / 2 + 0.014)   # E bottom edge clears the lip
    M = g.frame(origin, nrm, (0, -1, 0))
    pb = ctx.mat("piano_black")

    hous = g.rbox("MMI_Housing", (W, H + 0.050, T), (0, -0.025, -T / 2), 0.0045, 3, COL, pb)
    hous.data.transform(M)
    # rear face: satin with slight draft (visible from the windscreen side)
    back = g.rbox("MMI_Housing_Back", (W - 0.010, H - 0.006, 0.0025), (0, 0, -T - 0.0008), 0.002,
                  2, COL, ctx.mat("black_satin"))
    back.data.transform(M)
    # display glass (7", 15:9 -> 154 x 92 mm active) slightly inset
    aw, ah = 0.154, 0.092
    scr = g.prism("MMI_Display", g.rrect(aw, ah, 0.0015, 3, (0, 0.002)), -0.0004, 0.0001, COL,
                  ctx.mat("screen_mmi"))
    # navigation UI baked to an image (core/textures.mmi_screen); planar UVs
    # in the screen frame (+X right as seen by the occupants, +Y up)
    from ..core import uv as uvm
    uvm.set_planar(scr.data, (0, 0.002, 0), (1, 0, 0), (0, 1, 0), (aw, ah))
    scr.data.transform(M)

    # --- slot in the dash top: recessed lip with rubber wiper ----------------
    sl_w, sl_d = W + 0.012, 0.022
    slot = g.prism("MMI_Slot_Bezel", g.rrect(sl_d, sl_w, 0.006, 5), 0.0, 0.0025, COL,
                   ctx.mat("black_satin"), bevel=0.0008)
    slot.data.transform(g.frame((xs + 0.002, 0, zs - 0.0012), (0, 0, 1), (1, 0, 0)))
    wip = g.prism("MMI_Slot_Wiper", g.rrect(sl_d - 0.006, sl_w - 0.006, 0.003, 4), 0.0, 0.0028,
                  COL, ctx.mat("rubber_seal"))
    wip.data.transform(g.frame((xs + 0.002, 0, zs - 0.0005), (0, 0, 1), (1, 0, 0)))
