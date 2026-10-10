"""Door mirrors (8V): body-coloured upper cap, black lower housing with the
LED indicator along its front edge, black foot on the door shoulder behind the
mirror sail.  Width over mirrors 1966 mm (S) -> tip at |y| = 0.983 m.
Shape and proportions from the white S line reference photo (E)."""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh

COL = "Exterior/Mirrors"
TIP_Y = 0.983
ROOT_Y = 0.792
X_GLASS = -0.858     # glass plane (rear face)
Z_C = 1.036          # head centre height
SPLIT_DZ = -0.012    # paint / black split below the centre line


def _profile(t):
    """Height, depth and centre-z of the head at normalised span t (0 root, 1 tip)."""
    end = 1.0 - max(0.0, t - 0.80) / 0.20
    roundness = math.sqrt(max(end, 0.0)) if t > 0.8 else 1.0
    h = (0.122 + 0.012 * math.sin(math.pi * min(t, 0.8) / 0.8 * 0.5)) * roundness
    d = (0.110 - 0.022 * t) * (0.55 + 0.45 * roundness)
    zc = Z_C + 0.004 * t
    return max(h, 0.004), max(d, 0.004), zc


def _section(t, n=48):
    h, d, zc = _profile(t)
    pts = []
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        if c <= 0:      # front: rounded, upper front sloping back (wind shape)
            x = X_GLASS + d * abs(c) ** (2 / 2.4) * (1.0 - 0.18 * max(s, 0) ** 2)
        else:           # rear: flat glass face with a small radius at the rim
            x = X_GLASS - 0.008 * abs(c) ** 6
        z = zc + h / 2 * np.sign(s) * abs(s) ** (2 / 3.0)
        pts.append((x, z))
    return np.array(pts)


def _mirror(ctx, side):
    sfx = ".L" if side > 0 else ".R"
    paint, black = ctx.mat("paint"), ctx.mat("black_textured")
    ts = np.concatenate([np.linspace(0, 0.8, 24), 0.8 + 0.2 * np.sin(np.linspace(0.05, math.pi / 2, 10))])
    grid = []
    for t in ts:
        y = ROOT_Y + (TIP_Y - ROOT_Y) * t
        grid.append([(x, side * y, z) for x, z in _section(t)])
    grid = np.array(grid)
    head = mesh.grid_object("Mirror_Head" + sfx, grid, closed_v=True, cap_u=True,
                            collection=COL, material=paint, flip=side < 0)
    bi = mesh.material_index(head, black)
    for p in head.data.polygons:
        c = p.center
        if c.z < Z_C + SPLIT_DZ or c.x < X_GLASS + 0.004:
            p.material_index = bi
    mesh.shade_smooth(head, 45)

    # glass (slightly recessed in the rear face) with black surround
    pts = []
    for a in np.linspace(0, 2 * math.pi, 48, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        t = 0.45 + 0.43 * np.sign(c) * abs(c) ** 0.35
        h, d, zc = _profile(t)
        pts.append((side * (ROOT_Y + (TIP_Y - ROOT_Y) * t), zc + (h / 2 - 0.010) * np.sign(s) * abs(s) ** 0.5))
    pts = np.array(pts)
    mesh.extrude_polygon("Mirror_Glass" + sfx, pts, 0.002, plane="YZ", offset=X_GLASS - 0.0095,
                         collection=COL, material=ctx.mat("mirror"))

    # LED indicator strip along the lower front edge
    path = []
    for t in np.linspace(0.25, 0.97, 30):
        sec = _section(t)
        h, d, zc = _profile(t)
        a = math.radians(212)
        x = X_GLASS + d * abs(math.cos(a)) ** (2 / 2.4) - 0.002
        z = zc + h / 2 * -abs(math.sin(a)) ** (2 / 3.0)
        path.append((x, side * (ROOT_Y + (TIP_Y - ROOT_Y) * t), z))
    mesh.tube_along("Mirror_Indicator" + sfx, np.array(path), 0.0032, sides=8,
                    collection=COL, material=ctx.mat("lens_amber"))

    # foot: tapered black stalk from the door shoulder up into the head
    secs = []
    for t in np.linspace(0, 1, 12):
        y = 0.775 + (ROOT_Y + 0.05 - 0.775) * t
        z = 0.930 + (Z_C - 0.045 - 0.930) * t
        xc = -0.780 - 0.020 * t
        w = 0.074 - 0.022 * t      # along x
        th = 0.030 + 0.006 * t     # along y
        secs.append([(xc + w / 2 * math.cos(a), side * (y + th / 2 * math.sin(a)) , z)
                     for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)])
    mesh.grid_object("Mirror_Foot" + sfx, np.array(secs), closed_v=True, cap_u=True,
                     collection=COL, material=black, flip=side < 0)


def build(ctx):
    for side in (1, -1):
        _mirror(ctx, side)
