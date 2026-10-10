"""Running gear and underbody visible from below / through the wheels:

* Front: MacPherson struts (damper, coil spring, top mount on the strut
  tower), L-shaped lower wishbones, anti-roll bar with drop links, steering
  rack with tie rods, front subframe, driveshafts (inner tripod / outer CV
  boots) from the gearbox to the hubs.
* Rear: four-link independent rear suspension (MQB "modular performance"
  axle used with the 110 kW engines, S/E): trailing arm, upper and lower
  transverse links, separate spring and damper, anti-roll bar, rear subframe.
* Exhaust (2.0 TDI EA288): close-coupled DOC + DPF module behind the engine
  (built by exterior/engine.py), flexible decoupler, front pipe along the
  tunnel, centre silencer, over-axle pipe, transverse rear silencer feeding
  the twin tail pipes on the LEFT (openings.EXHAUST_TIPS), hangers.
* Fuel tank in front of the rear axle, heat shields, underbody trays.

Hard points are MQB-typical estimates (E) consistent with the track widths,
wheelbase and wheel centres of a3.spec; nothing here is visible from the
reference photos except through the wheel spokes.
"""
from __future__ import annotations

import math

import numpy as np

from .. import spec
from ..body import openings as op
from ..core import mesh
from ..interior import _geo as g

COL = "Exterior/Chassis"
XR = spec.m(spec.X_REAR_AXLE)          # rear axle x
ZW = spec.m(spec.WHEEL_CENTER_Z)       # wheel centre height
YF = spec.m(spec.TRACK_FRONT) / 2
YR = spec.m(spec.TRACK_REAR) / 2


def _mirror_pts(p):
    p = np.asarray(p, float).copy()
    p[..., 1] *= -1
    return p


def _both(fn):
    for s, sfx in ((1, "L"), (-1, "R")):
        fn(s, sfx)


def _arm(name, pts, w, h, mat, s, r=0.006):
    """Pressed-steel / forged arm: rounded-rectangle section swept along pts."""
    P = np.asarray(pts, float) * [1, s, 1]
    prof = g.rrect(w, h, min(r, 0.45 * min(w, h)), 3)
    return g.sweep(name, g.spline(P, 40), prof, COL, mat, smooth=50)


def _bush(name, c, axis, r_out, length, mat):
    return g.lathe(name, [(0, -length / 2), (r_out, -length / 2), (r_out, length / 2), (0, length / 2)],
                   origin=c, axis=axis, segments=20, col=COL, mat=mat)


def _coil(name, base, top, r_coil, r_wire, turns, mat):
    base, top = np.asarray(base, float), np.asarray(top, float)
    ax = top - base
    L = np.linalg.norm(ax)
    z = ax / L
    x = np.cross(z, [0, 0, 1.0]) if abs(z[2]) < 0.95 else np.array([1.0, 0, 0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    n = int(turns * 36)
    t = np.linspace(0, 1, n)
    # flattened end coils (closed ends)
    pitch = np.interp(t, [0, 0.08, 0.92, 1], [0, 0.04, 0.96, 1.0])
    a = 2 * math.pi * turns * t
    pts = base + np.outer(pitch * L, z) + r_coil * (np.outer(np.cos(a), x) + np.outer(np.sin(a), y))
    return g.tube(name, pts, r_wire, sides=10, col=COL, mat=mat)


def _damper(name, bottom, top, r_body, r_rod, mat_body, mat_rod, body_frac=0.62):
    bottom, top = np.asarray(bottom, float), np.asarray(top, float)
    ax = top - bottom
    L = np.linalg.norm(ax)
    lb = L * body_frac
    obs = [g.lathe(name + "_Body", [(0, 0), (r_body, 0.004), (r_body, lb - 0.004), (r_body * 0.8, lb),
                                    (0, lb)], origin=bottom, axis=ax, segments=24, col=COL,
                   mat=mat_body),
           g.lathe(name + "_Rod", [(0, lb - 0.01), (r_rod, lb - 0.01), (r_rod, L), (0, L)],
                   origin=bottom, axis=ax, segments=16, col=COL, mat=mat_rod)]
    return obs


# ---------------------------------------------------------------- front axle
def _front(ctx):
    steel = ctx.mat("steel_black")
    alu = ctx.mat("cast_alu")
    chrome = ctx.mat("chrome")
    spring = ctx.mat("spring_black")
    rubber = ctx.mat("rubber_seal")

    def corner(s, sfx):
        y = YF * s
        # strut: from the knuckle clamp (inboard of the wheel, above the hub)
        # up to the top mount under the strut tower (inclined inboard ~11 deg)
        bot = np.array([0.005, s * 0.615, 0.44])
        top = np.array([-0.025, s * 0.555, 0.78])
        _damper(f"Susp_F{sfx}_Strut", bot, top, 0.026, 0.011, steel, chrome, 0.55)
        ax = (top - bot) / np.linalg.norm(top - bot)
        seat_lo = bot + ax * 0.15
        seat_hi = top - ax * 0.035
        for nm, c, r in (("SeatLo", seat_lo, 0.078), ("SeatHi", seat_hi, 0.080)):
            g.lathe(f"Susp_F{sfx}_{nm}", [(0.02, -0.004), (r, -0.004), (r, 0.004), (0.02, 0.004)],
                    origin=c, axis=ax, segments=32, col=COL, mat=steel)
        _coil(f"Susp_F{sfx}_Spring", seat_lo + ax * 0.004, seat_hi - ax * 0.004, 0.066, 0.0062,
              5.2, spring)
        g.lathe(f"Susp_F{sfx}_TopMount", [(0, 0.0), (0.062, 0.0), (0.066, 0.025), (0.040, 0.040),
                                          (0, 0.042)], origin=top, axis=ax, segments=32, col=COL,
                mat=rubber)
        g.lathe(f"Susp_F{sfx}_Bump", [(0.012, 0), (0.022, 0.01), (0.022, 0.06), (0.012, 0.07)],
                origin=top - ax * 0.12, axis=ax, segments=20, col=COL, mat=rubber)
        # lower wishbone (L-shaped): ball joint under the hub, front bush,
        # rear (vertical-axis) bush
        bj = (0.0, 0.705, 0.205)
        fb = (0.06, 0.36, 0.215)
        rb = (-0.26, 0.40, 0.225)
        _arm(f"Susp_F{sfx}_Wishbone_F", [bj, (0.03, 0.55, 0.21), fb], 0.055, 0.022, steel, s)
        _arm(f"Susp_F{sfx}_Wishbone_R", [(0.0, 0.63, 0.208), (-0.12, 0.50, 0.215), rb],
             0.060, 0.020, steel, s)
        _bush(f"Susp_F{sfx}_Bush_F", (fb[0], s * fb[1], fb[2]), (1, 0, 0), 0.025, 0.06, rubber)
        _bush(f"Susp_F{sfx}_Bush_R", (rb[0], s * rb[1], rb[2]), (0, 0, 1), 0.034, 0.05, rubber)
        g.lathe(f"Susp_F{sfx}_BallJoint", [(0, 0), (0.022, 0.0), (0.024, 0.02), (0.012, 0.035),
                                           (0, 0.036)], origin=(bj[0], s * bj[1], bj[2] - 0.01),
                axis=(0, 0, 1), segments=20, col=COL, mat=rubber)
        # tie rod from the rack end to the steering arm (behind the axle)
        g.tube(f"Steer_TieRod_{sfx}", [(-0.13, s * 0.36, 0.30), (-0.135, s * 0.55, 0.305),
                                       (-0.14, s * 0.66, 0.31)], 0.0095, 12, COL, steel)
        g.lathe(f"Steer_RackBoot_{sfx}", [(0.012, 0), (0.024, 0.01), (0.017, 0.02), (0.025, 0.03),
                                          (0.017, 0.04), (0.025, 0.05), (0.017, 0.06),
                                          (0.024, 0.07), (0.012, 0.08), (0.012, 0.11)],
                origin=(-0.13, s * 0.25, 0.30), axis=(0, s, 0), segments=20, col=COL, mat=rubber)
        # anti-roll bar drop link to the strut
        g.tube(f"Susp_F{sfx}_DropLink", [(-0.02, s * 0.58, 0.50), (-0.06, s * 0.55, 0.32)], 0.0075,
               10, COL, steel)
        # driveshaft: gearbox flange (left) / intermediate shaft (right) -> hub
        inner_y = 0.24 if s > 0 else 0.26
        hub = np.array([0.0, s * 0.70, ZW])
        inner = np.array([0.02, s * inner_y, 0.30])
        d = hub - inner
        g.tube(f"Driveshaft_{sfx}_Shaft", [inner + d * 0.12, hub - d * 0.14], 0.0125, 14, COL, steel)
        for nm, c, r, L in (("InnerBoot", inner + d * 0.06, 0.045, 0.12),
                            ("OuterBoot", hub - d * 0.10, 0.042, 0.10)):
            prof = [(0.015, -L / 2)]
            for k in range(6):
                rr = r * (1 - 0.45 * k / 6)
                prof += [(rr, -L / 2 + L * (k + 0.2) / 6), (rr * 0.82, -L / 2 + L * (k + 0.7) / 6)]
            prof += [(0.015, L / 2)]
            g.lathe(f"Driveshaft_{sfx}_{nm}", prof, origin=c, axis=d, segments=24, col=COL,
                    mat=rubber)
    _both(corner)
    # anti-roll bar behind the subframe, rack, subframe
    bar = [(-0.06, 0.55, 0.32), (-0.13, 0.46, 0.25), (-0.16, 0.30, 0.235), (-0.16, -0.30, 0.235),
           (-0.13, -0.46, 0.25), (-0.06, -0.55, 0.32)]
    g.tube("Susp_F_AntiRollBar", g.spline(bar, 60), 0.0105, 14, COL, spring)
    g.tube("Steer_Rack", [(-0.13, -0.27, 0.30), (-0.13, 0.27, 0.30)], 0.027, 20, COL, alu)
    g.rbox("Steer_Rack_Motor", (0.11, 0.09, 0.10), (-0.17, -0.10, 0.27), 0.012, 2, COL, alu)
    g.tube("Steer_Column_Shaft", [(-0.13, 0.20, 0.33), (-0.25, 0.30, 0.52), (-0.40, 0.37, 0.70)],
           0.012, 12, COL, steel)
    sub = [(0.12, -0.42), (0.12, 0.42), (-0.05, 0.45), (-0.30, 0.42), (-0.36, 0.20), (-0.36, -0.20),
           (-0.30, -0.42), (-0.05, -0.45)]
    o = g.prism("Subframe_Front", sub, 0.17, 0.215, COL, steel, bevel=0.006)
    hole = g.prism("tmp_sub_hole", [(0.06, -0.30), (0.06, 0.30), (-0.22, 0.30), (-0.22, -0.30)],
                   0.10, 0.30, COL)
    mesh.boolean(o, hole)
    # front crash beam behind the bumper
    beam = [(0.79, -0.58, 0.47), (0.82, -0.30, 0.47), (0.825, 0.0, 0.47), (0.82, 0.30, 0.47),
            (0.79, 0.58, 0.47)]
    g.sweep("Subframe_CrashBeam", g.spline(beam, 40), g.rrect(0.05, 0.10, 0.01, 3), COL, alu)
    for s in (1, -1):
        g.rbox(f"Subframe_CrashBox_{'L' if s > 0 else 'R'}", (0.16, 0.07, 0.09),
               (0.70, s * 0.50, 0.47), 0.008, 2, COL, alu)


# ---------------------------------------------------------------- rear axle
def _rear(ctx):
    steel = ctx.mat("steel_black")
    chrome = ctx.mat("chrome")
    spring = ctx.mat("spring_black")
    rubber = ctx.mat("rubber_seal")

    def corner(s, sfx):
        x = XR
        # trailing arm (sheet steel blade) from the body bracket ahead of the
        # axle to the wheel carrier
        _arm(f"Susp_R{sfx}_TrailingArm", [(x + 0.46, 0.60, 0.33), (x + 0.22, 0.64, 0.31),
                                          (x + 0.03, 0.665, 0.29)], 0.012, 0.08, steel, s, 0.004)
        _bush(f"Susp_R{sfx}_TrailingBush", (x + 0.47, s * 0.60, 0.33), (0, 1, 0), 0.032, 0.05,
              rubber)
        # lower spring link (wide, carries the spring), upper link, toe link
        _arm(f"Susp_R{sfx}_SpringLink", [(x - 0.03, 0.30, 0.22), (x - 0.04, 0.45, 0.215),
                                         (x - 0.03, 0.64, 0.225)], 0.13, 0.016, steel, s)
        _arm(f"Susp_R{sfx}_UpperLink", [(x + 0.01, 0.33, 0.43), (x + 0.0, 0.62, 0.42)],
             0.035, 0.022, steel, s)
        _arm(f"Susp_R{sfx}_ToeLink", [(x + 0.11, 0.32, 0.24), (x + 0.10, 0.63, 0.25)], 0.026,
             0.020, steel, s)
        # spring on the lower link, damper behind the axle up to the body
        _coil(f"Susp_R{sfx}_Spring", (x - 0.035, s * 0.47, 0.235), (x - 0.03, s * 0.46, 0.42),
              0.055, 0.0058, 4.6, spring)
        _damper(f"Susp_R{sfx}_Damper", (x - 0.06, s * 0.60, 0.24), (x - 0.10, s * 0.56, 0.62),
                0.022, 0.010, steel, chrome, 0.6)
    _both(corner)
    bar = [(XR - 0.08, 0.52, 0.26), (XR - 0.12, 0.40, 0.25), (XR - 0.12, -0.40, 0.25),
           (XR - 0.08, -0.52, 0.26)]
    g.tube("Susp_R_AntiRollBar", g.spline(bar, 40), 0.0085, 12, COL, spring)
    # rear subframe: two cross members joined by side members
    for nm, xx in (("F", XR + 0.11), ("R", XR - 0.07)):
        g.tube(f"Subframe_Rear_{nm}", [(xx, -0.48, 0.30), (xx, -0.30, 0.25), (xx, 0.30, 0.25),
                                       (xx, 0.48, 0.30)], 0.03, 14, COL, steel)
    for s in (1, -1):
        g.tube(f"Subframe_Rear_Side_{'L' if s > 0 else 'R'}", [(XR + 0.14, s * 0.40, 0.27),
                                                               (XR - 0.10, s * 0.40, 0.27)],
               0.028, 12, COL, steel)


# ---------------------------------------------------------------- exhaust
def _exhaust(ctx):
    pipe = ctx.mat("exhaust_steel")
    can = ctx.mat("exhaust_can")
    shield = ctx.mat("aluminium_matt")
    rubber = ctx.mat("rubber_seal")
    r = 0.028
    # from the DPF outlet behind the engine (right of centre), down to the tunnel
    path = [(-0.30, -0.10, 0.36), (-0.42, -0.06, 0.24), (-0.60, -0.02, 0.19), (-1.00, 0.0, 0.185)]
    g.tube("Exhaust_FrontPipe", g.spline(path, 40), r, 18, COL, pipe)
    # decoupling element (braided flex)
    g.lathe("Exhaust_Flex", [(0, 0), (r + 0.006, 0.0), (r + 0.006, 0.18), (0, 0.18)],
            origin=(-0.62, -0.02, 0.19), axis=(-1, 0.05, 0), segments=24, col=COL,
            mat=ctx.mat("aluminium_matt"))
    # centre silencer (oval) under the rear seats
    g.pillow("Exhaust_CentreSilencer", (0.50, 0.17, 0.10), (-1.35, 0.0, 0.19), (4, 2.4, 2.4), 16,
             COL, can)
    path = [(-1.62, 0.0, 0.19), (-2.05, 0.02, 0.19), (-2.35, 0.10, 0.20), (-2.55, 0.18, 0.30),
            (-2.75, 0.20, 0.32), (-2.95, 0.22, 0.27)]
    g.tube("Exhaust_MidPipe", g.spline(path, 60), r * 0.95, 18, COL, pipe)
    g.tube("Exhaust_FrontToCentre", [(-1.0, 0.0, 0.185), (-1.12, 0.0, 0.19)], r, 18, COL, pipe)
    # transverse rear silencer behind the rear axle, on the left
    g.pillow("Exhaust_RearSilencer", (0.24, 0.62, 0.17), (-3.10, 0.30, 0.27), (3, 4, 2.6), 18,
             COL, can)
    # tail pipes to the twin tips (rear_end.py builds the chrome tips)
    for (yy, zz) in op.EXHAUST_TIPS:
        y, z = yy * 1e-3, zz * 1e-3
        g.tube(f"Exhaust_Tailpipe_{yy}", g.spline([(-3.20, y * 0.9, 0.27), (-3.28, y, z),
                                                   (-3.37, y, z)], 20), 0.030, 18, COL, pipe)
    # hangers
    for i, (x, y, z) in enumerate(((-1.1, 0.0, 0.215), (-2.7, 0.2, 0.36), (-3.10, 0.55, 0.36),
                                   (-3.10, 0.06, 0.36))):
        g.lathe(f"Exhaust_Hanger_{i}", [(0, 0), (0.016, 0.0), (0.016, 0.05), (0, 0.05)],
                origin=(x, y, z - 0.025), axis=(0, 0, 1), segments=12, col=COL, mat=rubber)
    # heat shields over the pipe along the tunnel and over the rear silencer
    for nm, x0, x1, w, zz in (("Tunnel", -0.45, -1.70, 0.30, 0.255),
                              ("Rear", -2.95, -3.25, 0.70, 0.37)):
        xs = np.linspace(x0, x1, 2)
        sec = [(0, -w / 2, -0.03), (0, -w / 2 + 0.02, 0.0), (0, w / 2 - 0.02, 0.0), (0, w / 2, -0.03)]
        g.loft(f"Heat_Shield_{nm}", [np.array(sec) + [x, 0.30 if nm == "Rear" else 0.0, zz]
                                     for x in xs], COL, shield)


# ---------------------------------------------------------------- tank / trays
def _tank_trays(ctx):
    tank = ctx.mat("underbody")
    tray = ctx.mat("black_textured")
    # saddle tank under the rear seat (50 l, S), straddling the exhaust tunnel
    g.pillow("Fuel_Tank", (0.50, 1.05, 0.22), (-2.25, 0.0, 0.29), (5, 5, 3), 16, COL, tank)
    # engine undertray and floor trays left/right of the tunnel (the tunnel
    # with the exhaust stays open, as on the car)
    g.prism("Underbody_EngineTray", [(0.66, -0.55), (0.66, 0.55), (-0.38, 0.62), (-0.38, -0.62)],
            0.150, 0.156, COL, tray)
    for s in (1, -1):
        y0, y1 = (0.16, 0.66) if s > 0 else (-0.66, -0.16)
        g.prism(f"Underbody_FloorTray_{'L' if s > 0 else 'R'}",
                [(-0.48, y0), (-0.48, y1), (-2.00, y1), (-2.00, y0)], 0.150, 0.155, COL, tray)


def build(ctx):
    _front(ctx)
    _rear(ctx)
    _exhaust(ctx)
    _tank_trays(ctx)
