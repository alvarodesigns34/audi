"""Door mirrors (8V): body-coloured cap with LED indicator strip, black
textured base on the door's mirror sail, chrome-free glass with black frame.
Width over mirrors 1966 mm (S) -> tip at |y| = 0.983 m."""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh

COL = "Exterior/Mirrors"
TIP_Y = 0.983
X_GLASS = -0.850   # rear (glass) face
X_FRONT = -0.690   # foremost point of the cap
Z_C = 1.030        # head centre height (E, photos)
H = 0.128          # head height
Y0 = 0.835         # inboard end of the head


def _head_section(y, nu=40):
    """Closed section (x, z) of the cap at lateral position y."""
    t = (y - Y0) / (TIP_Y - Y0)
    # rounded outboard end and slightly smaller inboard root
    shrink = (1.0 - max(0.0, t - 0.82) / 0.18) ** 0.5 if t > 0.82 else 1.0
    shrink *= 0.86 + 0.14 * min(1.0, t / 0.25)
    h = H * shrink
    depth = (X_GLASS - X_FRONT) * (0.55 + 0.45 * shrink)
    zc = Z_C + 0.006 * t
    pts = []
    for a in np.linspace(0, 2 * math.pi, nu, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        if c >= 0:   # rear half: almost flat glass face
            x = X_GLASS + 0.010 * (1 - abs(c) ** 0.2)
        else:        # front: teardrop
            x = X_GLASS + depth * abs(c) ** (2 / 2.6)
        z = zc + h / 2 * np.sign(s) * abs(s) ** (2 / 3.2)
        pts.append((x, z))
    return np.array(pts)


def _mirror(ctx, side):
    sfx = ".L" if side > 0 else ".R"
    paint, black = ctx.mat("paint"), ctx.mat("black_textured")
    ys = np.concatenate([np.linspace(Y0, TIP_Y - 0.02, 26), TIP_Y - 0.02 + 0.02 * np.sin(
        np.linspace(0.1, math.pi / 2, 8))])
    grid = []
    for y in ys:
        sec = _head_section(y)
        grid.append([(x, side * y, z) for x, z in sec])
    cap = mesh.grid_object("Mirror_Cap" + sfx, np.array(grid), closed_v=True, cap_u=True,
                           collection=COL, material=paint, flip=side < 0)
    mesh.shade_smooth(cap, 50)
    # glass + frame on the rear face
    gy0, gy1 = Y0 + 0.012, TIP_Y - 0.012
    rect = []
    for a in np.linspace(0, 2 * math.pi, 48, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        rect.append(((gy0 + gy1) / 2 + (gy1 - gy0) / 2 * np.sign(c) * abs(c) ** 0.4,
                     Z_C + (H / 2 - 0.012) * np.sign(s) * abs(s) ** 0.5))
    rect = np.array(rect)
    frame = mesh.extrude_polygon("Mirror_Frame" + sfx, rect * [side, 1], 0.006, plane="YZ",
                                 offset=X_GLASS - 0.004, collection=COL, material=black)
    inner = mesh.polyline_offset_2d(rect, -0.004 if mesh.polygon_area(rect) > 0 else 0.004)
    mesh.extrude_polygon("Mirror_Glass" + sfx, inner * [side, 1], 0.003, plane="YZ",
                         offset=X_GLASS - 0.007, collection=COL, material=ctx.mat("mirror"))
    # LED indicator strip along the lower front edge of the cap
    path = []
    for y in np.linspace(Y0 + 0.07, TIP_Y - 0.008, 24):
        sec = _head_section(y)
        k = np.argmin(np.abs(np.arctan2(sec[:, 1] - Z_C, sec[:, 0] - X_GLASS) + math.radians(150)))
        x, z = sec[k]
        path.append((x - 0.002, side * y, z - 0.002))
    mesh.tube_along("Mirror_Indicator" + sfx, np.array(path), 0.0035, sides=8,
                    collection=COL, material=ctx.mat("lens_amber"))
    # base: tapered arm from the door sail to the head (black textured)
    base_secs = []
    for t in np.linspace(0, 1, 10):
        y = 0.775 + (Y0 + 0.03 - 0.775) * t
        w = 0.080 - 0.025 * t
        h = 0.040 - 0.010 * t
        xc = -0.700 - 0.07 * t
        zc = 0.952 + (Z_C - 0.035 - 0.952) * t
        base_secs.append([(xc + w / 2 * math.cos(a), side * y, zc + h / 2 * math.sin(a))
                          for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)])
    mesh.grid_object("Mirror_Base" + sfx, np.array(base_secs), closed_v=True, cap_u=True,
                     collection=COL, material=black, flip=side < 0)


def build(ctx):
    for side in (1, -1):
        _mirror(ctx, side)
