"""Pedal box for S tronic (LHD): wide brake pedal, hanging accelerator,
footrest.  S line: brushed stainless pads with rubber studs (E).
"""
from __future__ import annotations

import math

import numpy as np

from . import _geo as g
from . import layout
from .trim import floor_z

COL = "Interior/Pedals"


def _pad(ctx, name, centre, normal, up, w, h, studs=(5, 3)):
    """Aluminium pad with rubber stud rows, local +Z = pad face normal."""
    objs = []
    base = g.rbox(name, (w, h, 0.006), (0, 0, -0.003), 0.003, 3, COL, ctx.mat("aluminium_brushed"))
    objs.append(base)
    st = g.Batch(name + "_Studs", COL, ctx.mat("rubber_pad"))
    nx, ny = studs
    for i in range(nx):
        for j in range(ny):
            cx = (i - (nx - 1) / 2) * (w - 0.020) / max(nx - 1, 1)
            cy = (j - (ny - 1) / 2) * (h - 0.020) / max(ny - 1, 1)
            o = g.pillow("tmp", (0.009 if nx > 2 else w * 0.7, 0.006 if ny > 2 else 0.006, 0.003),
                         (cx, cy, 0.0012), (2.5, 2.5, 2.5), 3, COL)
            st.add_object(o)
    objs.append(st.build())
    M = g.frame(centre, normal, up)
    for o in objs:
        o.data.transform(M)
    return objs


def build(ctx):
    L = layout.get(ctx)
    tilt = math.radians(48)                       # E pad faces ~parallel to the toe board
    n = np.array([-math.cos(tilt), 0, math.sin(tilt)])
    x_axis = (0, -1, 0)
    steel = ctx.mat("steel_dark")
    # brake: wide pad (two-pedal S tronic layout), arm up to the pivot under the dash
    yb = 0.360                                    # E brake pad centre
    pb = np.array([-0.770, yb, 0.405])
    _pad(ctx, "Pedal_Brake", pb, n, x_axis, 0.105, 0.070)
    arm = [pb + np.array([0.012, 0, 0]), pb + np.array([0.06, 0, 0.10]), np.array([-0.64, yb, 0.62])]
    g.tube("Pedal_Brake_Arm", g.spline(arm, 12), 0.009, 10, COL, steel)
    # accelerator: hanging (organ-like shape but top hinged in the 8V), long narrow pad
    ya = 0.205
    pa = np.array([-0.730, ya, 0.340])
    _pad(ctx, "Pedal_Accelerator", pa, n, x_axis, 0.050, 0.135, studs=(1, 7))
    arm = [pa + np.array([0.010, 0, 0.06]), np.array([-0.665, ya, 0.50]), np.array([-0.64, ya, 0.58])]
    g.tube("Pedal_Accelerator_Arm", g.spline(arm, 12), 0.006, 10, COL, steel)
    g.rbox("Pedal_Accelerator_Module", (0.05, 0.06, 0.08), (-0.635, ya, 0.60), 0.008, 2, COL,
           ctx.mat("hard_plastic"))
    # footrest on the left, on the toe board / wheel arch
    yf = 0.565
    xf = -0.72
    pf = np.array([xf, yf, floor_z(L, xf, yf) + 0.12])
    _pad(ctx, "Pedal_Footrest", pf, np.array([-math.cos(math.radians(40)), -0.10, math.sin(math.radians(40))]),
         x_axis, 0.080, 0.240, studs=(2, 9))
