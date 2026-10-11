"""Engine-bay detail around the 2.0 TDI (exterior/engine.py builds the engine,
gearbox and the main bay volumes): sculpted engine cover with oil filler and
dipstick, strut-tower domes with top-mount caps, brake booster and master
cylinder on the driver's (left, LHD) side, ABS/ESC hydraulic unit, battery
terminals and fuse box, front lock carrier (slam panel) with bonnet latch,
bonnet prop rod, bonnet inner frame with insulation pad and hinges, plenum
cover with pollen-filter lid, wiring looms and coolant hoses.

MQB-typical layout and sizes (E): no photograph of an 8V 2.0 TDI engine bay
is among the references; positions are consistent with the body, engine and
radiator volumes of the model.
"""
from __future__ import annotations

import math

import numpy as np

from ..interior import _geo as g

COL = "Exterior/Engine"


def _cover(ctx):
    """EA288 engine cover: wide faceted shell over the head (replaces the
    simple pillow), oil filler cap and orange dipstick handle."""
    cover = ctx.mat("engine_cover")

    def fn(p):
        p = p.copy()
        # flat top with a raised central spine and chamfered front corners
        top = p[:, 2] > 0
        p[top, 2] *= 0.75 + 0.25 * np.exp(-(p[top, 1] / 0.12) ** 2)
        p[:, 0] -= 0.04 * (p[:, 1] / 0.30) ** 2
        return p
    ob = g.pillow("Engine_Cover_Shell", (0.40, 0.60, 0.075), (0.05, -0.235, 0.80), (5, 5, 2.4),
                  16, COL, cover, fn=fn)
    # tilt with the engine (rear edge lower)
    import mathutils
    M = mathutils.Matrix.Translation((0.05, -0.235, 0.80)) @ mathutils.Matrix.Rotation(
        math.radians(-6), 4, "Y") @ mathutils.Matrix.Translation((-0.05, 0.235, -0.80))
    ob.data.transform(M)
    ob.data.update()
    g.lathe("Engine_OilFillerCap", [(0, 0), (0.030, 0), (0.031, 0.012), (0.026, 0.020),
                                    (0, 0.021)], origin=(0.06, -0.40, 0.825), axis=(0, 0, 1),
            segments=28, col=COL, mat=ctx.mat("black_satin"))
    g.tube("Engine_Dipstick_Tube", [(0.16, -0.08, 0.40), (0.18, -0.07, 0.62), (0.19, -0.07, 0.78)],
           0.006, 10, COL, ctx.mat("black_satin"))
    g.lathe("Engine_Dipstick_Handle", [(0, 0), (0.014, 0), (0.016, 0.012), (0.010, 0.026),
                                       (0, 0.028)], origin=(0.19, -0.07, 0.78), axis=(0, 0, 1),
            segments=20, col=COL, mat=ctx.mat("plastic_orange"))


def _towers(ctx):
    paint, rubber = ctx.mat("paint"), ctx.mat("rubber_seal")
    for s in (1, -1):
        sfx = "L" if s > 0 else "R"
        c = (-0.025, s * 0.565, 0.79)
        g.lathe(f"Strut_Tower_Dome_{sfx}", [(0.0, 0.020), (0.075, 0.018), (0.095, 0.004),
                                            (0.110, -0.04), (0.125, -0.10)], origin=c,
                axis=(0, 0, 1), segments=40, col=COL, mat=paint)
        g.lathe(f"Strut_Tower_Cap_{sfx}", [(0, 0), (0.034, 0), (0.036, 0.018), (0.028, 0.026),
                                           (0, 0.027)], origin=(c[0], c[1], c[2] + 0.018),
                axis=(0, 0, 1), segments=28, col=COL, mat=rubber)
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            g.lathe(f"Strut_Tower_Bolt_{sfx}{k}", [(0, 0), (0.008, 0), (0.008, 0.008), (0, 0.009)],
                    origin=(c[0] + 0.062 * math.cos(a), c[1] + 0.062 * math.sin(a), c[2] + 0.012),
                    axis=(0, 0, 1), segments=6, col=COL, mat=ctx.mat("steel_dark"))


def _brakes_hydraulics(ctx):
    """Brake servo + tandem master cylinder + reservoir on the left (LHD),
    ESC unit in front of it, brake lines to the bulkhead."""
    black, alu = ctx.mat("black_satin"), ctx.mat("cast_alu")
    g.lathe("Brake_Servo", [(0, 0), (0.115, 0.0), (0.125, 0.02), (0.125, 0.10), (0.115, 0.12),
                            (0, 0.12)], origin=(-0.36, 0.45, 0.62), axis=(1, 0, 0), segments=40,
            col=COL, mat=black)
    g.lathe("Brake_MasterCylinder", [(0, 0), (0.028, 0), (0.028, 0.17), (0.02, 0.18), (0, 0.18)],
            origin=(-0.24, 0.45, 0.62), axis=(1, 0, 0), segments=24, col=COL, mat=alu)
    g.rbox("Brake_ESC_Unit", (0.12, 0.10, 0.09), (-0.08, 0.46, 0.53), 0.008, 2, COL, alu)
    g.rbox("Brake_ESC_ECU", (0.12, 0.03, 0.09), (-0.08, 0.40, 0.53), 0.006, 2, COL, black)
    lines = ctx.mat("brake_line")
    for k, (y0, y1) in enumerate(((0.47, 0.60), (0.45, 0.55), (0.48, 0.30), (0.44, -0.10))):
        g.tube(f"Brake_Line_{k}", g.spline([(-0.06, y0, 0.58), (-0.15, (y0 + y1) / 2, 0.60),
                                            (-0.30, y1, 0.56)], 20), 0.0024, 6, COL, lines)


def _battery_fuses(ctx):
    black, red = ctx.mat("black_satin"), ctx.mat("plastic_red")
    g.rbox("Battery_FuseBox", (0.12, 0.16, 0.05), (-0.20, 0.33, 0.765), 0.006, 2, COL, black)
    g.rbox("Battery_PlusCover", (0.05, 0.04, 0.03), (-0.14, 0.47, 0.755), 0.005, 2, COL, red)
    g.tube("Battery_Cable_Plus", g.spline([(-0.14, 0.47, 0.77), (-0.05, 0.50, 0.78),
                                           (0.10, 0.48, 0.70), (0.20, 0.30, 0.42)], 30), 0.009,
           12, COL, ctx.mat("corrugated"))


def _lock_carrier(ctx):
    """Front lock carrier (black composite slam panel) across the radiator
    with the bonnet latch, buffers and the prop rod clipped along it."""
    tex, steel = ctx.mat("black_textured"), ctx.mat("steel_dark")
    pts = np.array([(0.66, y, 0.665 - 0.03 * (y / 0.62) ** 2) for y in np.linspace(-0.62, 0.62, 25)])
    g.sweep("Bay_LockCarrier", pts, g.rrect(0.07, 0.035, 0.008, 3), COL, tex, up=(0, 0, 1))
    for s in (1, -1):
        g.rbox(f"Bay_LockCarrier_Leg_{'L' if s > 0 else 'R'}", (0.05, 0.05, 0.30),
               (0.665, s * 0.60, 0.50), 0.008, 2, COL, tex)
        g.lathe(f"Bay_Bonnet_Buffer_{'L' if s > 0 else 'R'}", [(0, 0), (0.012, 0), (0.010, 0.018),
                                                              (0, 0.02)],
                origin=(0.64, s * 0.45, 0.682), axis=(0, 0, 1), segments=16, col=COL,
                mat=ctx.mat("rubber_seal"))
    g.rbox("Bay_Bonnet_Latch", (0.05, 0.08, 0.05), (0.665, 0.0, 0.66), 0.006, 2, COL, steel)
    g.tube("Bay_Bonnet_Latch_Lever", [(0.69, 0.03, 0.66), (0.71, 0.08, 0.655)], 0.004, 8, COL,
           ctx.mat("plastic_orange"))
    # bonnet prop rod stowed along the carrier (left), its holder clips
    g.tube("Bay_Bonnet_PropRod", [(0.64, -0.55, 0.69), (0.64, 0.05, 0.69)], 0.0055, 10, COL, steel)
    for y in (-0.50, -0.20):
        g.rbox(f"Bay_Bonnet_PropClip_{int(abs(y) * 100)}", (0.02, 0.012, 0.02), (0.64, y, 0.69),
               0.003, 1, COL, ctx.mat("black_satin"))


def _bonnet_inner(ctx):
    """Inner frame (painted) and insulation pad under the bonnet skin, and
    the two hinges at the bulkhead.  Follows the bonnet underside 6-30 mm
    below the outer skin."""
    ref = ctx.objects.get("skin_ref")
    if ref is None:
        return
    from mathutils import Vector
    from ..body import surftools as st
    surf = st.Surface(ref)

    def under(x, y, d):
        hit = surf.bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 3.0)
        return np.array(hit[0][:]) - np.array([0, 0, d]) if hit[0] is not None else None

    paint, felt = ctx.mat("paint"), ctx.mat("felt_black")
    xs = np.linspace(-0.27, 0.70, 28)
    ys = np.linspace(-0.70, 0.70, 41)
    rows = []
    for x in xs:
        w = 0.70 - 0.20 * max(0.0, (x - 0.45) / 0.25) ** 2
        row = [under(x, y * w / 0.70, 0.022) for y in ys]
        if any(r is None for r in row):
            continue
        rows.append(row)
    if len(rows) > 3:
        g.loft("Bonnet_Insulation", [np.array(r) for r in rows], COL, felt)
    # perimeter frame + X braces (hat-section tubes under the skin)
    loop = []
    for x, y in [(-0.27, -0.66), (0.62, -0.58), (0.70, 0.0), (0.62, 0.58), (-0.27, 0.66)]:
        loop.append((x, y))
    for nm, path in (("Frame", loop + [loop[0]]),
                     ("Brace_A", [(-0.27, -0.40), (0.55, 0.30)]),
                     ("Brace_B", [(-0.27, 0.40), (0.55, -0.30)])):
        P = []
        for a, b in zip(path[:-1], path[1:]):
            for t in np.linspace(0, 1, 16, endpoint=False):
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                q = under(x, y, 0.030)
                if q is not None:
                    P.append(q)
        if len(P) > 3:
            g.sweep(f"Bonnet_Inner_{nm}", np.array(P), g.rrect(0.04, 0.016, 0.004, 2), COL, paint)
    for s in (1, -1):
        sfx = "L" if s > 0 else "R"
        q = under(-0.29, s * 0.62, 0.035)
        if q is not None:
            g.rbox(f"Bonnet_Hinge_{sfx}", (0.09, 0.012, 0.05), tuple(q), 0.003, 1, COL,
                   ctx.mat("steel_dark"))


def _plenum(ctx):
    tex = ctx.mat("black_textured")
    for k, y in enumerate(np.linspace(-0.55, 0.55, 12)):
        g.rbox(f"Bay_Plenum_Rib_{k}", (0.15, 0.006, 0.012), (-0.30, y, 0.866), 0.002, 1, COL, tex)
    g.rbox("Bay_PollenFilter_Lid", (0.14, 0.28, 0.02), (-0.30, -0.40, 0.872), 0.006, 2, COL,
           ctx.mat("black_satin"))


def _looms_hoses(ctx):
    loom, hose = ctx.mat("corrugated"), ctx.mat("rubber_seal")
    for s in (1, -1):
        g.tube(f"Bay_Loom_{'L' if s > 0 else 'R'}", g.spline([(0.55, s * 0.58, 0.62),
                                                             (0.20, s * 0.60, 0.66),
                                                             (-0.10, s * 0.58, 0.70),
                                                             (-0.30, s * 0.50, 0.72)], 30),
               0.010, 10, COL, loom)
    g.tube("Bay_Loom_Engine", g.spline([(-0.30, 0.20, 0.72), (-0.15, -0.05, 0.74),
                                        (-0.05, -0.30, 0.72), (0.10, -0.45, 0.66)], 30),
           0.012, 10, COL, loom)
    g.tube("Engine_Hose_Bottom", g.spline([(0.60, 0.25, 0.30), (0.40, 0.10, 0.28),
                                           (0.20, -0.10, 0.30), (0.12, -0.20, 0.36)], 30),
           0.020, 14, COL, hose)
    g.tube("Engine_Hose_Heater", g.spline([(0.0, -0.40, 0.55), (-0.20, -0.30, 0.60),
                                           (-0.35, -0.20, 0.62)], 30), 0.010, 10, COL, hose)


def build(ctx):
    _cover(ctx)
    _towers(ctx)
    _brakes_hydraulics(ctx)
    _battery_fuses(ctx)
    _lock_carrier(ctx)
    _bonnet_inner(ctx)
    _plenum(ctx)
    _looms_hoses(ctx)
