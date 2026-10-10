"""Wheel-arch liners, wheelhouse walls and underbody trays."""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..core import mesh
from ..spec import m

COL = "Exterior/Underbody"


def _liner(name, xc, side, mat):
    """Textured plastic arch liner: partial cylinder just outside the tyre
    envelope, plus the inner wheelhouse wall."""
    r = op.ARCH_R * 1e-3 + 0.008
    cz = op.ARCH_CZ * 1e-3
    y0, y1 = 0.57, 0.90
    a0, a1 = math.radians(-12), math.radians(192)
    n = 64
    rows = []
    for t in np.linspace(a0, a1, n):
        x = xc + r * math.cos(t)
        z = cz + r * math.sin(t)
        rows.append([(x, side * y, z) for y in np.linspace(y0, y1, 6)])
    g = np.array(rows)
    ob = mesh.grid_object(name, g, collection=COL, material=mat, flip=side < 0)
    # inner wall: half disc at y = y0
    pts = [(xc + r * math.cos(t), cz + r * math.sin(t)) for t in np.linspace(a0, a1, n)]
    wall = mesh.extrude_polygon(name + "_Wall", pts, 0.004, plane="XZ",
                                offset=side * y0 - (0.004 if side > 0 else 0.0),
                                collection=COL, material=mat)
    return ob, wall


def build(ctx):
    mat = ctx.mat("black_textured")
    under = ctx.mat("underbody")
    for xc, nm in ((0.0, "F"), (m(-2636), "R")):
        for side, sfx in ((1, "L"), (-1, "R")):
            _liner(f"Arch_Liner_{nm}{sfx}", xc, side, mat)
    # underbody trays between and around the axles
    mesh.extrude_polygon("Underbody_Tray", [(-3.25, -0.60), (0.75, -0.60), (0.75, 0.60),
                                            (-3.25, 0.60)], 0.004, plane="XY", offset=0.142,
                         collection=COL, material=under)
