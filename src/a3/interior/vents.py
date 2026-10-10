"""Round 'jet' air vents of the 8V dashboard (2 central + 2 lateral).

Local frame of each vent: origin on the dash face at the vent centre, +Z
towards the cabin.  Layers (front to back):
    chrome bezel ring  -> black adjustable ring -> central push/turn hub with
    chrome tip -> radial twisted vanes -> dark duct barrel with back wall.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from . import _geo as g
from . import dashboard, layout

COL = "Interior/Vents"


def _vanes(name, n, r0, r1, z0, z1, twist_deg, curve_deg, col, mat):
    """n radial vanes as a thin solidified surface (twisted turbine blades)."""
    nr, nz = 7, 3
    V, F = [], []
    for k in range(n):
        base = 2 * math.pi * k / n
        off = len(V)
        for i in range(nr):
            r = r0 + (r1 - r0) * i / (nr - 1)
            for j in range(nz):
                z = z0 + (z1 - z0) * j / (nz - 1)
                th = (base + math.radians(curve_deg) * (r - r0) / (r1 - r0)
                      + math.radians(twist_deg) * (z - (z0 + z1) / 2) / (z1 - z0))
                V.append((r * math.cos(th), r * math.sin(th), z))
        for i in range(nr - 1):
            for j in range(nz - 1):
                a = off + i * nz + j
                F.append((a, a + nz, a + nz + 1, a + 1))
    ob = g.mk(name, V, F, col, mat, smooth=30)
    mesh.solidify(ob, 0.0009, offset=0.0)
    return ob


def build_vent(ctx, name, centre, axis, L):
    R = L.vent_ring_d / 2          # 45 mm  (E)
    rh = R - 0.006                 # hole radius in the dash (matches dashboard cut)
    chrome = ctx.mat("chrome")
    blk = ctx.mat("black_satin")
    gloss = ctx.mat("piano_black")
    dark = ctx.mat("hard_plastic")
    parts = []
    # chrome bezel: inner wall -> rolled top -> outer skirt into the dash
    ring = g.lathe(f"{name}_Ring", [(rh, -0.006), (rh, 0.004), (rh + 0.0012, 0.0085),
                                     (rh + 0.0035, 0.0103), (R - 0.0018, 0.0098),
                                     (R - 0.0002, 0.0072), (R, 0.003), (R + 0.0004, -0.004)],
                   segments=72, col=COL, mat=chrome, smooth=60)
    parts.append(ring)
    # adjustable black ring sitting inside the bezel
    ar = g.lathe(f"{name}_AdjRing", [(rh - 0.0005, 0.0045), (rh - 0.0045, 0.0050),
                                      (rh - 0.0060, 0.0030), (rh - 0.0060, -0.0060),
                                      (rh - 0.0005, -0.0060)],
                 segments=64, col=COL, mat=gloss, smooth=60)
    parts.append(ar)
    # duct barrel (inward facing) + back wall
    barrel = g.lathe(f"{name}_Duct", [(rh - 0.0005, -0.006), (rh - 0.0015, -0.040),
                                       (rh - 0.012, -0.048), (0.0, -0.050)],
                     segments=48, col=COL, mat=dark, smooth=60)
    mesh.recalc_normals(barrel, inside=True)
    parts.append(barrel)
    # turbine vanes
    vanes = _vanes(f"{name}_Vanes", 10, 0.0085, rh - 0.0060, -0.016, -0.002, 38, 9, COL, blk)
    parts.append(vanes)
    # central hub with chrome tip
    hub = g.lathe(f"{name}_Hub", [(0.0, 0.0072), (0.0050, 0.0072), (0.0068, 0.0066),
                                  (0.0082, 0.0050), (0.0090, 0.0010), (0.0090, -0.022),
                                  (0.0, -0.022)],
                  segments=40, col=COL, mat=blk, smooth=50)
    parts.append(hub)
    tip = g.lathe(f"{name}_HubRing", [(0.0060, 0.0076), (0.0082, 0.0062), (0.0094, 0.0040),
                                      (0.0094, 0.0020), (0.0086, 0.0028), (0.0068, 0.0060)],
                  segments=40, col=COL, mat=chrome, smooth=60)
    parts.append(tip)
    # fine knurl ridges on the adjustable ring (grip)
    kn = g.Batch(f"{name}_Knurl", COL, blk)
    for k in range(36):
        a = 2 * math.pi * k / 36
        c = np.array([(rh - 0.0028) * math.cos(a), (rh - 0.0028) * math.sin(a), 0.0052])
        v, f = g.box_verts(c, np.array([math.cos(a), math.sin(a), 0]) * 0.0016,
                           np.array([-math.sin(a), math.cos(a), 0]) * 0.0004, (0, 0, 0.00025))
        kn.add(v, f)
    parts.append(kn.build())
    M = g.frame(centre, axis, (0, 1, 0) if abs(axis[1]) < 0.9 else (1, 0, 0))
    for p in parts:
        p.data.transform(M)
        p.data.update()
    return parts


def build(ctx):
    L = layout.get(ctx)
    shape = ctx.data["dash"]["shape"]
    for nm, c, ax in dashboard.vent_positions(L, shape):
        build_vent(ctx, f"Vent_{nm}", c, ax, L)
