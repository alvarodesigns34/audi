"""Luggage compartment (380 l VDA, S): carpeted load floor (variable floor
in its upper position), side trims with the wheel-house humps, rear panel
trim with the stainless load-sill protector, tie-down eyes, boot light and
the spare-wheel well cover.  Envelope from the body shell (E)."""
from __future__ import annotations

import numpy as np

from . import _geo as g

COL = "Interior/Boot"
X0, X1 = -2.93, -3.30          # E  behind the rear backrest -> tailgate seal
Z_FLOOR = 0.640                # E  load floor (upper position, flush with the sill)
Y_HALF = 0.50                  # E  half width between the side trims


def build(ctx):
    carpet = ctx.mat("carpet")
    hard = ctx.mat("hard_plastic")
    steel = ctx.mat("aluminium_brushed")
    # load floor panel
    g.rbox("Boot_Floor", (X0 - X1, 2 * Y_HALF, 0.016), ((X0 + X1) / 2, 0.0, Z_FLOOR - 0.008), 0.004, 2,
           COL, carpet)
    g.rbox("Boot_Floor_Handle", (0.03, 0.12, 0.006), (X1 + 0.05, 0.0, Z_FLOOR + 0.002), 0.002, 1, COL,
           hard)
    # side trims: vertical carpeted panels with the wheel-house hump
    for s in (1, -1):
        sfx = "L" if s > 0 else "R"
        secs = []
        for x in np.linspace(X0, X1, 14):
            hump = 0.10 * np.exp(-((x + 2.64) / 0.20) ** 2)
            secs.append(np.array([(x, s * (Y_HALF + 0.02), Z_FLOOR - 0.02),
                                  (x, s * (Y_HALF - hump), Z_FLOOR + 0.05),
                                  (x, s * (Y_HALF - hump * 0.9), Z_FLOOR + 0.28),
                                  (x, s * (Y_HALF + 0.06), Z_FLOOR + 0.42)]))
        g.keep_inside(ctx, g.loft(f"Boot_SideTrim_{sfx}", secs, COL, carpet, flip=s < 0), 0.010)
        for k, x in enumerate((X0 - 0.05, X1 + 0.06)):
            g.lathe(f"Boot_TieDown_{sfx}{k}", [(0.004, 0), (0.016, 0), (0.016, 0.004), (0.004, 0.004)],
                    origin=(x, s * (Y_HALF - 0.01), Z_FLOOR + 0.04), axis=(0, -s, 0), segments=16,
                    col=COL, mat=steel)
    g.rbox("Boot_Light", (0.06, 0.012, 0.025), (X0 - 0.15, Y_HALF - 0.005, Z_FLOOR + 0.30), 0.003, 1,
           COL, ctx.mat("lens_clear"))
    # rear panel trim and load-sill protector
    g.rbox("Boot_RearTrim", (0.04, 2 * Y_HALF + 0.08, 0.10), (X1 - 0.02, 0.0, Z_FLOOR - 0.04), 0.008, 2,
           COL, hard)
    g.rbox("Boot_SillPlate", (0.07, 2 * Y_HALF, 0.004), (X1 - 0.03, 0.0, Z_FLOOR + 0.012), 0.002, 1,
           COL, steel)
    # well beneath (seen when the floor is lifted / exploded)
    g.rbox("Boot_Well", (0.62, 0.66, 0.14), ((X0 + X1) / 2, 0.0, Z_FLOOR - 0.10), 0.03, 2, COL,
           ctx.mat("underbody"))
