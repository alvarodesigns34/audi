"""Door mirrors (8V): body-coloured upper cap, black lower housing with the
LED indicator along the split, black arm bolted to the door below the side
window (not to the window base).  Width over mirrors 1966 mm (S) -> tip at
|y| = 0.983 m.

v0.4: head and arm measured on side.jpg (ray casting on the calibrated
camera, C/S), shape of the head in front view from sline_front.jpg (E):
* head z 0.935 .. 1.056 at the root (centre 0.995, 121 mm), paint / black
  split at z 0.967;
* swept head: front of the root x -0.657, glass at the tip x -0.883; glass
  plane from x -0.80 (root) to -0.88 (tip);
* arm on the door below the window, x -0.70 .. -0.78, foot at z ~0.865.
v0.3 had the head ~25 mm too high and the foot on the window base."""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh

COL = "Exterior/Mirrors"
TIP_Y = 0.983        # S  1966 / 2
ROOT_Y = 0.815       # E  inner end of the head, just outboard of the side glass
Z_C = 0.995          # C  head centre at the root (side.jpg)
H_ROOT = 0.121       # C  head height at the root
SPLIT_Z = 0.967      # C  paint / black split at the root
X_FRONT_ROOT = -0.657  # C  front of the head at the root
X_GLASS_ROOT = -0.800  # C  glass plane at the root
X_GLASS_TIP = -0.880   # C  glass plane at the tip (-0.883 outer edge of the cap)
SPAN = TIP_Y - ROOT_Y
# arm (C: x range and foot height on side.jpg; section E)
ARM_X = (-0.700, -0.780)
ARM_Z0, ARM_Z1 = 0.862, 0.950
# door skin y at the arm (ray cast on the body skin at x -0.74, E +-2 mm)
DOOR_Y = ((0.840, 0.8585), (0.865, 0.8565), (0.900, 0.835), (0.930, 0.810), (0.950, 0.7976))


def _end(t):
    """Rounding of the outer end (1 along the head, -> 0 at the tip)."""
    return math.sqrt(max(0.0, 1.0 - (max(0.0, t - 0.78) / 0.22) ** 2))


def _profile(t):
    """x of the glass plane, depth, height and centre z at span t (0 root, 1 tip)."""
    e = _end(t)
    xg = X_GLASS_ROOT + (X_GLASS_TIP - X_GLASS_ROOT) * t
    # swept front: the head is deepest at the root and narrows outwards
    d_full = (X_FRONT_ROOT - X_GLASS_ROOT) * (1.0 - 0.10 * t)
    d = d_full * (0.35 + 0.65 * e)
    h = H_ROOT * (1.0 - 0.18 * t) * (0.30 + 0.70 * e)
    zc = Z_C - 0.006 * t
    return xg, max(d, 0.004), max(h, 0.004), zc


def _section(t, n=56):
    """Closed (x, z) loop of the head at span t: flat glass face at the rear,
    rounded top sloping down to a full round nose (wind shape)."""
    xg, d, h, zc = _profile(t)
    pts = []
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        if c >= 0:      # front half: superellipse, top drawn back
            x = xg + d * c ** (2 / 2.6) * (1.0 - 0.22 * max(s, 0.0) ** 2)
        else:           # rear: glass face with a small radius at the rim
            x = xg - 0.010 * (-c) ** 6
        z = zc + h / 2 * np.sign(s) * abs(s) ** (2 / 3.2)
        pts.append((x, z))
    return np.array(pts)


def _split_z(t):
    xg, d, h, zc = _profile(t)
    return zc + (SPLIT_Z - Z_C) / (H_ROOT / 2) * (h / 2)


def _door_y(z):
    zz, yy = zip(*DOOR_Y)
    return float(np.interp(z, zz, yy))


def _mirror(ctx, side):
    sfx = ".L" if side > 0 else ".R"
    paint, black = ctx.mat("paint"), ctx.mat("black_textured")
    ts = np.concatenate([np.linspace(0, 0.78, 26), 0.78 + 0.22 * np.sin(np.linspace(0.06, math.pi / 2, 12))])
    grid = []
    for t in ts:
        y = ROOT_Y + SPAN * t
        grid.append([(x, side * y, z) for x, z in _section(t)])
    grid = np.array(grid)
    head = mesh.grid_object("Mirror_Head" + sfx, grid, closed_v=True, cap_u=True,
                            collection=COL, material=paint, flip=side < 0)
    bi = mesh.material_index(head, black)
    for p in head.data.polygons:
        c = p.center
        t = min(max((abs(c.y) - ROOT_Y) / SPAN, 0.0), 1.0)
        xg = _profile(t)[0]
        if c.z < _split_z(t) or c.x < xg + 0.004 or abs(c.y) < ROOT_Y + 0.002:
            p.material_index = bi
    mesh.shade_smooth(head, 45)

    # glass (recessed in the rear face) inside a black rim
    pts = []
    for a in np.linspace(0, 2 * math.pi, 64, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        t = 0.47 + 0.45 * np.sign(c) * abs(c) ** 0.30
        xg, d, h, zc = _profile(t)
        pts.append((ROOT_Y + SPAN * t, zc + (h / 2 - 0.009) * np.sign(s) * abs(s) ** 0.45, xg))
    pts = np.array(pts)
    # the glass plane is swept: build it as a thin grid between two loops
    P = np.array([(x - 0.0085, side * y, z) for y, z, x in pts])
    Q = P + np.array([0.0025, 0.0, 0.0])
    gl = mesh.grid_object("Mirror_Glass" + sfx, np.stack([P, Q]), closed_v=True, cap_u=True,
                          collection=COL, material=ctx.mat("mirror"), flip=side > 0)
    mesh.shade_smooth(gl, 30)

    # LED indicator strip on the split line, along the front, out to the tip
    path = []
    for t in np.linspace(0.30, 0.985, 34):
        sec = _section(t, 96)
        xg = _profile(t)[0]
        zs = _split_z(t)
        front = sec[sec[:, 0] > xg + 0.01]
        k = np.argmin(np.abs(front[:, 1] - zs))
        path.append((front[k, 0] - 0.0015, side * (ROOT_Y + SPAN * t), zs))
    mesh.tube_along("Mirror_Indicator" + sfx, np.array(path), 0.0030, sides=8,
                    collection=COL, material=ctx.mat("lens_amber"))

    # arm: tapered black stalk seated on the door skin below the window,
    # widening outwards into the underside of the head
    secs = []
    for z in np.linspace(ARM_Z0, ARM_Z1, 14):
        u = (z - ARM_Z0) / (ARM_Z1 - ARM_Z0)
        x0 = ARM_X[0] - 0.010 * u          # front edge leans back a little
        x1 = ARM_X[1] + 0.006 * u
        yi = _door_y(z) - 0.006            # inner face just inside the skin
        yo = 0.884 + (0.902 - 0.884) * u ** 1.4   # E  ~45 mm thick in front view
        xc, w = (x0 + x1) / 2, (x0 - x1) / 2
        yc, th = (yi + yo) / 2, (yo - yi) / 2
        loop = []
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            ca, sa = math.cos(a), math.sin(a)
            # rounded rectangle (superellipse exponent 4)
            loop.append((xc + w * np.sign(ca) * abs(ca) ** 0.5,
                         side * (yc + th * np.sign(sa) * abs(sa) ** 0.5), z))
        secs.append(loop)
    foot = mesh.grid_object("Mirror_Foot" + sfx, np.array(secs), closed_v=True, cap_u=True,
                            collection=COL, material=black, flip=side < 0)
    mesh.shade_smooth(foot, 40)


def build(ctx):
    for side in (1, -1):
        _mirror(ctx, side)
