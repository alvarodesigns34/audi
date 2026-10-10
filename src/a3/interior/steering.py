"""Leather multifunction steering wheel, conventional 4-spoke (8V 2013-2016),
column shroud and stalks.

Wheel frame W: origin at the wheel centre, +Z along the steering axis toward
the driver, +X to the driver's right (world -Y), +Y up the wheel plane.
4-spoke layout (as in the reference photo): two horizontal spokes carrying
the multifunction pads, two lower spokes converging in a 'V' that frames an
aluminium-trimmed trapezoid insert, round airbag with chrome ring and rings.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from . import _geo as g
from . import layout

COL = "Interior/Steering"

RIM_A = 0.0158     # E rim half-thickness in the wheel plane (31.5 mm)
RIM_B = 0.0138     # E rim half-thickness along the axis (27.5 mm)


def _rim(ctx, L):
    Rc = L.sw_diameter / 2 - RIM_A
    nu, nv = 192, 28
    th = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    t = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    # slightly egg-shaped section: flatter on the inside, fuller on the driver side
    p = 2.25
    cr = np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / p)
    cz = np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / p)
    pr = RIM_A * cr * np.where(cr < 0, 0.94, 1.0)
    pz = RIM_B * cz + 0.0015 * (1 - cr ** 2) * (cz > 0)
    # thumb-rest swelling at 9/3 o'clock just above the horizontal spokes
    pts = np.zeros((nu, nv, 3))
    for i, a in enumerate(th):
        sw = 1.0 + 0.10 * (math.exp(-((a - math.radians(18)) / 0.18) ** 2)
                           + math.exp(-((a - math.radians(162)) / 0.18) ** 2))
        r = Rc + pr * sw
        pts[i, :, 0] = r * math.cos(a)
        pts[i, :, 1] = r * math.sin(a)
        pts[i, :, 2] = pz * (1 + 0.5 * (sw - 1))
    ob = mesh.grid_object("Steering_Rim", pts, closed_u=True, closed_v=True,
                          collection=COL, material=ctx.mat("leather_black"), smooth=False)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 80)
    return ob, Rc


def _spoke(name, a0, r0, r1, w0, w1, th, z0, z1, mat, nlen=14):
    """Spoke from radius r0 (hub) to r1 (rim) at angle a0 (rad) in the wheel
    plane: rounded section (superellipse), tapering width, dished in z."""
    nv = 20
    t = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    sx = np.sign(c) * np.abs(c) ** (2 / 3.0)
    sz = np.sign(s) * np.abs(s) ** (2 / 2.6)
    d = np.array([math.cos(a0), math.sin(a0), 0])
    n = np.array([-math.sin(a0), math.cos(a0), 0])
    pts = []
    for k in range(nlen):
        u = k / (nlen - 1)
        r = r0 + (r1 - r0) * u
        w = w0 + (w1 - w0) * u ** 0.8
        z = z0 + (z1 - z0) * u
        sec = (r * d)[None] + (w / 2) * sx[:, None] * n[None] + (np.array([0, 0, 1]) * (z + th / 2 * sz[:, None]))
        pts.append(sec)
    ob = mesh.grid_object(name, np.array(pts), closed_v=True, collection=COL, material=mat,
                          smooth=False, cap_u=True)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 50)
    return ob


def _mf_pad(ctx, side, objs):
    """Multifunction button pad on a horizontal spoke (local wheel coords)."""
    cx = side * 0.098
    pad = g.pillow(f"Steering_MF_Pad_{'R' if side > 0 else 'L'}", (0.058, 0.044, 0.010),
                   (cx, 0.004, 0.0085), (3.5, 3.5, 2.5), 8, COL, ctx.mat("black_satin"))
    objs.append(pad)
    fr = g.prism(f"Steering_MF_Frame_{'R' if side > 0 else 'L'}",
                 g.rrect(0.060, 0.046, 0.009, 5, (cx, 0.004)), 0.0115, 0.0128, COL,
                 ctx.mat("chrome"))
    # hollow the frame: inner plate covers the centre
    objs.append(fr)
    inner = g.prism("tmp", g.rrect(0.055, 0.041, 0.007, 5, (cx, 0.004)), 0.0118, 0.0131, COL,
                    ctx.mat("piano_black"))
    objs.append(inner)
    btns = g.Batch(f"Steering_MF_Buttons_{'R' if side > 0 else 'L'}", COL, ctx.mat("black_satin"))
    for bx, by in ((-0.016, 0.011), (0.016, 0.011), (-0.016, -0.004), (0.016, -0.004)):
        b = g.rbox("tmp", (0.012, 0.009, 0.004), (cx + bx * 0.9, 0.004 + by, 0.0140), 0.0016, 2, COL)
        btns.add_object(b)
    objs.append(btns.build())
    # thumb roller in the middle
    roll = g.lathe(f"Steering_MF_Roller_{'R' if side > 0 else 'L'}",
                   [(0, -0.0045), (0.0062, -0.0045), (0.0068, -0.003), (0.0068, 0.003),
                    (0.0062, 0.0045), (0, 0.0045)],
                   origin=(cx, 0.0035, 0.0128), axis=(1, 0, 0), segments=28, col=COL,
                   mat=ctx.mat("black_textured"))
    objs.append(roll)
    icons = g.Batch(f"Steering_MF_Icons_{'R' if side > 0 else 'L'}", COL, ctx.mat("screen_ui_dim"),
                    smooth=None)
    for bx, by in ((-0.016, 0.011), (0.016, 0.011), (-0.016, -0.004), (0.016, -0.004)):
        v, f = g.box_verts((cx + bx * 0.9, 0.004 + by, 0.01615), (0.0025, 0, 0), (0, 0.0005, 0),
                           (0, 0, 0.00008))
        icons.add(v, f)
    objs.append(icons.build())


def _rings(ctx, centre, objs, R=0.0094, r=0.0015, gap=0.0136):
    for k in range(4):
        cx = centre[0] + (k - 1.5) * gap
        path = np.array([(cx + R * math.cos(a), centre[1] + R * math.sin(a), centre[2])
                         for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)])
        objs.append(g.tube(f"Steering_Audi_Ring_{k}", path, r, 10, COL, ctx.mat("badge_chrome"),
                           closed=True))


def build(ctx):
    L = layout.get(ctx)
    axis = L.sw_axis()
    W = g.frame(L.sw_centre, axis, (0, -1, 0))
    leather = ctx.mat("leather_black")
    objs = []

    rim, Rc = _rim(ctx, L)
    objs.append(rim)
    hub_z = -0.024                         # E airbag centre sits behind the rim plane
    # horizontal spokes (3 and 9 o'clock)
    for s, nm in ((1, "R"), (-1, "L")):
        a0 = 0.0 if s > 0 else math.pi
        sp = _spoke(f"Steering_Spoke_{nm}", a0, 0.055, Rc - 0.004, 0.050, 0.036, 0.019,
                    hub_z + 0.010, -0.004, leather)
        objs.append(sp)
        _mf_pad(ctx, s, objs)
    # lower spokes converging into the 'V'
    for s, nm in ((1, "LR"), (-1, "LL")):
        a0 = math.radians(-90 + s * 27)
        sp = _spoke(f"Steering_Spoke_{nm}", a0, 0.050, Rc - 0.004, 0.028, 0.024, 0.017,
                    hub_z + 0.004, -0.004, leather)
        objs.append(sp)
    # trapezoid insert between the lower spokes: black gloss centre, alu frame
    trap = [(-0.030, -0.066), (0.030, -0.066), (0.066, -0.140), (-0.066, -0.140)]
    from ..core.curves import rounded_polygon
    tp = rounded_polygon(trap, 0.008, 5)
    base = g.prism("Steering_V_Insert_Base", tp, hub_z - 0.006, hub_z + 0.010, COL, leather,
                   bevel=0.003)
    objs.append(base)
    tp_in = rounded_polygon([(-0.018, -0.075), (0.018, -0.075), (0.050, -0.134), (-0.050, -0.134)],
                            0.006, 5)
    alu = g.prism("Steering_V_Insert_Alu", tp_in, hub_z + 0.010, hub_z + 0.0135, COL,
                  ctx.mat("aluminium_brushed"), bevel=0.0012)
    objs.append(alu)
    blk = g.prism("Steering_V_Insert_Black", rounded_polygon(
        [(-0.0145, -0.0785), (0.0145, -0.0785), (0.0455, -0.1305), (-0.0455, -0.1305)], 0.004, 5),
        hub_z + 0.0135, hub_z + 0.0145, COL, ctx.mat("black_satin"))
    objs.append(blk)

    # airbag: domed, rounded-square module
    bag = g.pillow("Steering_Airbag", (0.150, 0.130, 0.058), (0, -0.004, hub_z), (3.2, 3.2, 2.6), 16,
                   COL, ctx.mat("soft_touch"))
    objs.append(bag)
    zf = hub_z + 0.029
    ring = g.lathe("Steering_Airbag_Ring", [(0.0405, zf - 0.0025), (0.0405, zf + 0.0006),
                                            (0.0418, zf + 0.0016), (0.0445, zf + 0.0016),
                                            (0.0458, zf + 0.0006), (0.0458, zf - 0.0030)],
                   origin=(0, 0.0, 0), segments=72, col=COL, mat=ctx.mat("chrome"))
    objs.append(ring)
    disc = g.lathe("Steering_Airbag_Badge", [(0, zf + 0.0002), (0.0405, zf - 0.0006),
                                             (0.0405, zf - 0.003)],
                   segments=72, col=COL, mat=ctx.mat("soft_touch"))
    objs.append(disc)
    _rings(ctx, (0, 0.0, zf + 0.0012), objs)
    # 'AIRBAG' embossing below the ring
    em = g.text_mesh("Steering_Airbag_Text", "AIRBAG", size=0.0045, col=COL,
                     mat=ctx.mat("black_satin"), extrude=0.0002)
    g.set_verts(em, g.verts_of(em) + np.array([0, -0.054, zf - 0.006]))
    objs.append(em)
    # hub back cover and gloss trim ring
    back = g.lathe("Steering_Hub_Cover", [(0.000, -0.070), (0.045, -0.070), (0.058, -0.055),
                                          (0.066, -0.035), (0.070, -0.018), (0.068, -0.010)],
                   segments=48, col=COL, mat=ctx.mat("black_textured"))
    objs.append(back)
    trim = g.lathe("Steering_Hub_TrimRing", [(0.066, -0.012), (0.071, -0.018), (0.071, -0.030),
                                             (0.067, -0.032)],
                   segments=48, col=COL, mat=ctx.mat("piano_black"))
    objs.append(trim)

    for o in objs:
        o.data.transform(W)
        o.data.update()
    _rim_stitches(ctx, L, rim, W, Rc)
    _column(ctx, L, W)


def _rim_stitches(ctx, L, rim, W, Rc):
    """Cross ('baseball') stitching along the rim's inner seam on the driver
    side, interrupted where the spokes join."""
    surf = g.Surface(rim)
    b = g.Batch("Steering_Rim_Stitching", COL, ctx.mat("stitch_grey"))
    t_seam = math.radians(118)           # section angle of the seam (inner, driver side)
    gaps = [0.0, math.pi, math.radians(-63), math.radians(-117)]
    segs = []
    bounds = sorted([(a % (2 * math.pi)) for a in gaps])
    for i, a in enumerate(bounds):
        a2 = bounds[(i + 1) % len(bounds)] + (2 * math.pi if i == len(bounds) - 1 else 0)
        segs.append((a + 0.16, a2 - 0.16))
    for a0, a1 in segs:
        n = max(10, int((a1 - a0) * Rc / 0.002))
        th = np.linspace(a0, a1, n)
        r = Rc + RIM_A * 0.94 * math.cos(t_seam) * 0.85
        z = RIM_B * math.sin(t_seam) * 1.02
        loc = np.stack([r * np.cos(th), r * np.sin(th), np.full(n, z)], 1)
        hint_l = np.stack([np.cos(th) * math.cos(t_seam), np.sin(th) * math.cos(t_seam),
                           np.full(n, math.sin(t_seam))], 1)
        P = g.apply_np(loc, W)
        H = g.apply_np(hint_l, W) - g.apply_np(np.zeros((1, 3)), W)
        Ps, Ns = surf.snap(P, H)
        for lat, yaw in ((0.0016, 0.55), (-0.0016, -0.55)):
            Q = g.offset_curve_3d(Ps, Ns, lat)
            g.add_stitch(b, Q, Ns, pitch=0.0040, length=0.0034, width=0.0008, height=0.0004,
                         lift=0.0002, yaw=yaw)
    b.build()


def _column(ctx, L, W):
    """Column shroud (two-piece look), stalks: indicator (left), wipers
    (right), cruise control (lower left)."""
    objs = []
    tex = ctx.mat("black_textured")
    sat = ctx.mat("black_satin")
    # shroud: lofted rounded rectangles along -Z (away from driver)
    secs = []
    for k, z in enumerate(np.linspace(-0.065, -0.36, 12)):
        u = k / 11
        w = 0.105 + 0.040 * u
        h = 0.095 + 0.035 * u
        cy = -0.020 - 0.012 * u
        ring = g.rrect(w, h, 0.030 + 0.01 * u, 6, (0, cy))
        secs.append(np.stack([ring[:, 0], ring[:, 1], np.full(len(ring), z)], 1))
    shroud = g.loft("Steering_Column_Shroud", secs, COL, tex, closed=True, cap=True, smooth=50)
    objs.append(shroud)
    # split line between upper/lower halves (thin dark groove ring)
    stalk_root_z = -0.095
    for s, nm, dy, ang in ((-1, "Indicator", 0.004, 6), (1, "Wiper", 0.004, 6),
                           (-1, "Cruise", -0.040, -28)):
        L0 = 0.135 if nm != "Cruise" else 0.095
        a = math.radians(ang)
        d = np.array([s * math.cos(a), math.sin(a), -0.10])
        d = d / np.linalg.norm(d)
        p0 = np.array([s * 0.050, dy, stalk_root_z])
        path = np.array([p0 + d * L0 * t for t in np.linspace(0, 1, 10)])
        rad = np.linspace(0.0075, 0.0058, 10)
        st = g.tube(f"Steering_Stalk_{nm}", path, rad, 16, COL, sat)
        objs.append(st)
        tipc = p0 + d * L0
        tip = g.lathe(f"Steering_Stalk_{nm}_Tip", [(0, 0.024), (0.0045, 0.023), (0.0068, 0.019),
                                                   (0.0072, 0.0), (0.0, 0.0)],
                      origin=tuple(tipc - d * 0.020), axis=tuple(d), segments=20, col=COL,
                      mat=tex)
        objs.append(tip)
        if nm != "Cruise":
            # sliding/rotary band with white marks
            band = g.lathe(f"Steering_Stalk_{nm}_Band", [(0.0068, 0.0), (0.0072, 0.002),
                                                         (0.0072, 0.010), (0.0068, 0.012)],
                           origin=tuple(tipc - d * 0.038), axis=tuple(d), segments=20, col=COL,
                           mat=sat)
            objs.append(band)
    for o in objs:
        o.data.transform(W)
        o.data.update()
