"""Engine bay: 2.0 TDI EA288 (110 kW) with the DQ250 6-speed S tronic.

MQB layout (S/E): transverse inline four, engine on the RIGHT (-Y) with the
timing belt at the right end, gearbox on the LEFT (+Y); the engine is tilted
back 12 deg (exhaust side to the bulkhead), with the turbocharger and the
close-coupled DOC + DPF module behind it and the water-cooled charge-air
cooler integrated in the intake manifold at the front.  Battery left rear
(LHD), air box left front, coolant expansion tank right rear.  Radiator pack
(low-temperature radiator, A/C condenser, main radiator, twin-fan shroud)
behind the bumper.

All dimensions are engineering estimates (E) sized to the engine bay of the
body model (strut towers at |y| 0.555, bulkhead at x -0.36, hood ~0.80 m).
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from ..interior import _geo as g

COL = "Exterior/Engine"
TILT = math.radians(12.0)          # E  rearward tilt of the cylinder axis
CRANK = np.array([0.095, 0.0, 0.33])   # E  crank axis point (x, -, z)
YC = -0.245                        # E  engine block centre (y), right of centre
L_BLOCK = 0.44                     # E  block length along the crank


def _M():
    """engine-local -> world: local X forward, Y along crank, Z up the bores."""
    z = np.array([-math.sin(TILT), 0.0, math.cos(TILT)])
    return g.frame((CRANK[0], 0.0, CRANK[2]), z, (math.cos(TILT), 0, math.sin(TILT)))


def _place(ob):
    ob.data.transform(_M())
    ob.data.update()
    return ob


def _engine(ctx):
    alu = ctx.mat("cast_alu")
    iron = ctx.mat("steel_dark")
    cover = ctx.mat("engine_cover")
    black = ctx.mat("black_satin")
    rubber = ctx.mat("rubber_seal")
    chrome = ctx.mat("aluminium_matt")
    y = YC
    _place(g.rbox("Engine_Block", (0.30, L_BLOCK, 0.27), (0.0, y, 0.10), 0.02, 2, COL, iron))
    # block ribs (front face)
    for k in range(5):
        _place(g.rbox(f"Engine_Block_Rib_{k}", (0.012, 0.02, 0.24),
                      (0.152, y - L_BLOCK / 2 + 0.04 + k * 0.09, 0.10), 0.004, 1, COL, iron))
    _place(g.rbox("Engine_Sump", (0.27, L_BLOCK - 0.04, 0.13), (0.0, y, -0.10), 0.02, 2, COL, alu))
    _place(g.rbox("Engine_Head", (0.27, L_BLOCK - 0.01, 0.12), (0.0, y, 0.295), 0.012, 2, COL, alu))
    _place(g.rbox("Engine_CamCover", (0.22, L_BLOCK - 0.04, 0.06), (-0.005, y, 0.385), 0.02, 2,
                  COL, black))
    # injector / glow plug row under the cover
    for k in range(4):
        cy = y - 0.132 + k * 0.088
        _place(g.lathe(f"Engine_Injector_{k}", [(0, 0), (0.012, 0), (0.012, 0.05), (0, 0.05)],
                       origin=(0.05, cy, 0.39), axis=(0, 0, 1), segments=12, col=COL, mat=chrome))
    # plastic engine cover with "TDI" lettering
    cov = g.pillow("Engine_Cover", (0.36, 0.50, 0.055), (0.03, y + 0.01, 0.445), (3.2, 3.2, 2.2), 14,
                   COL, cover)
    _place(cov)
    t = g.text_mesh("Engine_Cover_Text", "TDI", size=0.06, col=COL, mat=ctx.mat("chrome"),
                    extrude=0.002, bold=True)
    t.data.transform(g.frame((0.05, y + 0.06, 0.474), (0, 0, 1), (0, 1, 0)))
    _place(t)
    # timing belt cover at the right end, crank pulley and accessory drive
    belt = [(0.17, -0.12), (0.17, 0.28), (0.10, 0.40), (-0.10, 0.40), (-0.16, 0.26), (-0.16, -0.12),
            (0.0, -0.18)]
    tb = g.prism("Engine_TimingCover", belt, 0.0, 0.035, COL, black, bevel=0.006)
    tb.data.transform(g.frame((0.0, y - L_BLOCK / 2 - 0.035, 0.0), (0, -1, 0), (1, 0, 0)))
    _place(tb)
    for nm, c, r in (("CrankPulley", (0.0, 0.0), 0.085), ("AltPulley", (0.17, 0.02), 0.03),
                     ("ACPulley", (0.16, -0.16), 0.055)):
        p = g.lathe(f"Engine_{nm}", [(0, 0), (r, 0.0), (r, 0.022), (0, 0.022)],
                    origin=(c[0], y - L_BLOCK / 2 - 0.06, c[1]), axis=(0, -1, 0), segments=32,
                    col=COL, mat=alu)
        _place(p)
    _place(g.lathe("Engine_Alternator", [(0, 0), (0.066, 0), (0.066, 0.14), (0, 0.14)],
                   origin=(0.20, y - L_BLOCK / 2 + 0.02, 0.05), axis=(0, 1, 0), segments=32,
                   col=COL, mat=alu))
    _place(g.lathe("Engine_ACCompressor", [(0, 0), (0.058, 0), (0.058, 0.16), (0, 0.16)],
                   origin=(0.19, y - L_BLOCK / 2 + 0.03, -0.13), axis=(0, 1, 0), segments=32,
                   col=COL, mat=alu))
    # intake manifold with integrated water charge-air cooler (front)
    _place(g.rbox("Engine_IntakeManifold", (0.11, L_BLOCK - 0.06, 0.13), (0.19, y, 0.29), 0.02, 2,
                  COL, black))
    _place(g.rbox("Intercooler_WaterCAC", (0.07, 0.30, 0.10), (0.27, y + 0.02, 0.30), 0.012, 2, COL,
                  alu))
    # EGR cooler and turbo on the exhaust side (rear)
    _place(g.lathe("Engine_EGRCooler", [(0, 0), (0.035, 0), (0.035, 0.28), (0, 0.28)],
                   origin=(-0.17, y - 0.14, 0.26), axis=(0, 1, 0), segments=24, col=COL, mat=chrome))
    tur = g.pillow("Turbo_Housing", (0.15, 0.16, 0.14), (-0.21, y + 0.05, 0.18), (2.2, 2.2, 2.2), 12,
                   COL, iron)
    _place(tur)
    # oil filter housing / dipstick
    _place(g.lathe("Engine_OilFilter", [(0, 0), (0.04, 0), (0.04, 0.10), (0, 0.10)],
                   origin=(0.17, y + 0.17, 0.10), axis=(0, 0, 1), segments=24, col=COL, mat=black))
    # engine mount (right) to the body
    g.rbox("Engine_Mount_R", (0.12, 0.10, 0.08), (0.04, -0.52, 0.62), 0.01, 2, COL, alu)
    g.tube("Engine_Hose_Top", g.spline([(0.12, -0.20, 0.55), (0.30, -0.25, 0.58), (0.55, -0.24, 0.55),
                                        (0.62, -0.22, 0.52)], 30), 0.018, 14, COL, rubber)
    g.tube("Engine_Hose_Charge", g.spline([(0.25, -0.05, 0.38), (0.40, 0.0, 0.30), (0.58, 0.05, 0.28)],
                                          30), 0.026, 14, COL, rubber)


def _gearbox_dpf(ctx):
    alu = ctx.mat("cast_alu")
    can = ctx.mat("exhaust_can")
    pipe = ctx.mat("exhaust_steel")
    # DQ250 6-speed wet dual-clutch: bell housing + case on the left
    g.lathe("Gearbox_Bell", [(0, 0), (0.19, 0.0), (0.19, 0.04), (0.17, 0.12), (0, 0.12)],
            origin=(0.09, -0.02, 0.33), axis=(0, 1, 0), segments=40, col=COL, mat=alu)
    g.pillow("Gearbox_Case", (0.36, 0.26, 0.34), (0.06, 0.20, 0.33), (3, 3, 3), 14, COL, alu)
    g.pillow("Gearbox_Mechatronic", (0.18, 0.16, 0.12), (0.12, 0.25, 0.52), (3, 3, 3), 10, COL, alu)
    g.lathe("Gearbox_Diff", [(0, 0), (0.11, 0), (0.11, 0.08), (0, 0.08)],
            origin=(0.02, 0.10, 0.30), axis=(0, 1, 0), segments=32, col=COL, mat=alu)
    # close-coupled oxidation catalyst + particulate filter behind the engine,
    # then down into the front pipe (chassis.py)
    g.lathe("DPF_Module", [(0, 0), (0.07, 0.0), (0.078, 0.03), (0.078, 0.30), (0.07, 0.33), (0, 0.33)],
            origin=(-0.24, -0.33, 0.60), axis=(0.0, 0.62, -0.78), segments=32, col=COL, mat=can)
    g.tube("DPF_Outlet", g.spline([(-0.24, -0.17, 0.40), (-0.27, -0.13, 0.38), (-0.30, -0.10, 0.36)], 12),
           0.028, 16, COL, pipe)


def _bay(ctx):
    paint = ctx.mat("paint")
    black = ctx.mat("black_satin")
    tex = ctx.mat("black_textured")
    alu = ctx.mat("cast_alu")
    # strut towers and inner fender aprons (painted body)
    for s in (1, -1):
        sfx = "L" if s > 0 else "R"
        g.lathe(f"Strut_Tower_{sfx}", [(0.13, 0.0), (0.12, 0.18), (0.085, 0.27), (0.0, 0.28)],
                origin=(-0.025, s * 0.565, 0.53), axis=(0, 0, 1), segments=40, col=COL, mat=paint)
        apron = [np.array([(x, s * 0.62, z) for z in np.linspace(0.36, 0.73, 6)])
                 for x in np.linspace(0.62, -0.34, 12)]
        g.loft(f"Bay_Apron_{sfx}", apron, COL, paint, flip=s < 0)
    # bulkhead and plenum (scuttle) panel under the cowl grille
    g.rbox("Bay_Bulkhead", (0.03, 1.30, 0.55), (-0.37, 0.0, 0.60), 0.01, 2, COL, black)
    g.rbox("Bay_Plenum", (0.18, 1.30, 0.04), (-0.30, 0.0, 0.84), 0.01, 2, COL, tex)
    # battery (left rear, LHD) with its thermal box
    g.rbox("Battery_Box", (0.20, 0.30, 0.20), (-0.22, 0.38, 0.62), 0.012, 2, COL, tex)
    g.rbox("Battery_Lid", (0.205, 0.305, 0.02), (-0.22, 0.38, 0.73), 0.008, 2, COL, black)
    # air box (left front) and intake snorkel to the grille
    g.pillow("Airbox", (0.30, 0.22, 0.16), (0.20, 0.36, 0.64), (3.5, 3.5, 3), 12, COL, tex)
    g.tube("Airbox_Snorkel", g.spline([(0.35, 0.36, 0.66), (0.50, 0.30, 0.68), (0.62, 0.26, 0.67)], 20),
           0.045, 16, COL, tex)
    g.tube("Airbox_Duct", g.spline([(0.10, 0.30, 0.62), (0.0, 0.10, 0.60), (-0.05, -0.05, 0.56)], 20),
           0.035, 16, COL, ctx.mat("rubber_seal"))
    # coolant expansion tank (right rear), brake fluid reservoir (left, by
    # the bulkhead - LHD), washer filler (right front)
    g.pillow("Coolant_Tank", (0.16, 0.12, 0.10), (-0.24, -0.47, 0.64), (3, 3, 3), 10, COL,
             ctx.mat("plastic_translucent"))
    g.lathe("Coolant_Cap", [(0, 0), (0.025, 0), (0.025, 0.025), (0, 0.025)],
            origin=(-0.24, -0.47, 0.69), axis=(0, 0, 1), segments=20, col=COL, mat=black)
    g.pillow("Brake_Fluid_Reservoir", (0.10, 0.07, 0.07), (-0.31, 0.44, 0.74), (3, 3, 3), 10, COL,
             ctx.mat("plastic_translucent"))
    g.lathe("Washer_Filler", [(0, 0), (0.022, 0), (0.022, 0.03), (0, 0.03)],
            origin=(0.42, -0.53, 0.62), axis=(0, 0, 1), segments=20, col=COL,
            mat=ctx.mat("plastic_blue"))
    # radiator pack: LT radiator + condenser + radiator + fan shroud
    for k, (nm, dx, mat) in enumerate((("Radiator_LT", 0.0, alu), ("Radiator_Condenser", -0.03, alu),
                                       ("Radiator_Main", -0.06, alu))):
        g.rbox(nm, (0.022, 0.66, 0.40), (0.69 + dx, 0.0, 0.43), 0.004, 1, COL, mat)
    g.rbox("Radiator_Shroud", (0.04, 0.70, 0.44), (0.60, 0.0, 0.43), 0.01, 2, COL, black)
    for s in (1, -1):
        g.lathe(f"Radiator_Fan_{'L' if s > 0 else 'R'}", [(0, 0), (0.16, 0.0), (0.16, 0.03), (0, 0.03)],
                origin=(0.585, s * 0.17, 0.43), axis=(-1, 0, 0), segments=40, col=COL, mat=black)
        for b in range(7):
            a = 2 * math.pi * b / 7
            blade = [(0.04 * math.cos(a), 0.04 * math.sin(a)),
                     (0.15 * math.cos(a + 0.25), 0.15 * math.sin(a + 0.25)),
                     (0.15 * math.cos(a + 0.55), 0.15 * math.sin(a + 0.55)),
                     (0.04 * math.cos(a + 0.5), 0.04 * math.sin(a + 0.5))]
            bl = g.prism(f"Radiator_FanBlade_{'L' if s > 0 else 'R'}{b}", blade, 0.0, 0.004, COL, black)
            bl.data.transform(g.frame((0.555, s * 0.17, 0.43), (1, 0, 0), (0, 1, 0)))


def build(ctx):
    _engine(ctx)
    _gearbox_dpf(ctx)
    _bay(ctx)
