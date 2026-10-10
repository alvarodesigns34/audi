"""Instrument cluster with visor (8V analogue cluster + colour FIS).

Local cluster frame: origin at ``L.cluster_c``, +Z towards the driver's eyes,
+X to the driver's right (world -Y), +Y up.
"""
from __future__ import annotations

import math

import numpy as np

from ..core.curves import smoothstep
from . import _geo as g
from . import layout

COL = "Interior/Cluster"

DIAL_R = 0.049          # E dial face radius (Ø ~100 mm, scaled from photos)
DIAL_DX = 0.083         # E dial centre offset from cluster centre
FIS_W, FIS_H = 0.048, 0.072   # E central colour FIS (3.5")
START, SPAN = 215.0, 250.0    # E scale sweep: 0 at lower left, clockwise


def _hood(ctx, L):
    """Visor: arch-shaped shell lofted along x with a rounded rear lip."""
    yc = L.sw_centre[1]
    a = 0.212                         # E half width at the lip
    zb = 0.866                        # base (meets the tub shelf)
    x_lip, x_front = -0.842, -0.585   # E
    p = 3.2
    nu = 41
    u = np.linspace(-1, 1, nu)

    def arch(x, inset=0.0):
        t = smoothstep(x_lip, x_front, x)          # 0 at lip, 1 at front
        top = 1.036 - (1.036 - 0.958) * t ** 1.6   # E visor crest 1.036 -> merges into the dash top
        aw = a + 0.010 * t - inset
        h = top - zb - inset
        f = (1 - np.abs(u) ** p) ** (1 / p)
        # plan curvature of the lip: edges sit 30 mm further forward
        xs = x + 0.030 * np.abs(u) ** 2 * (1 - t)
        return np.stack([xs, yc + aw * u, zb + h * f], 1)

    th = 0.007
    xs = np.linspace(x_front, x_lip + 0.004, 18)
    secs = []
    for x in xs:
        outer = arch(x)
        inner = arch(x, th)[::-1]
        secs.append(np.vstack([outer, inner]))
    # rounded rim: blend outer and inner toward the mid line
    o, i = arch(x_lip + 0.004), arch(x_lip + 0.004, th)
    mid = (o + i) / 2
    for phi in np.linspace(0.35, 1.45, 4):
        c, s = math.cos(phi), math.sin(phi)
        oo = mid + (o - mid) * c
        ii = mid + (i - mid) * c
        oo[:, 0] -= 0.0035 * s
        ii[:, 0] -= 0.0035 * s
        secs.append(np.vstack([oo, ii[::-1]]))
    hood = g.loft("Cluster_Hood", secs, COL, ctx.mat("soft_touch"), closed=True, smooth=55)
    g.finish(hood, 55)
    # stitched seam on the visor crest? (8V: no stitching on the hood; leave plain)
    return hood


def _frame(L):
    c = np.array(L.cluster_c)
    eye = np.array([-1.62, L.sw_centre[1], 1.13])
    z = g._n(eye - c)
    return g.frame(c, z, (0, -1, 0))


def _scale(ctx, name, cx, labels, vmax, major, minor, red_from, M, batch_ticks, batch_red,
           batch_txt, value):
    """Ticks, numbers and needle of one dial. Angles in local dial plane."""
    def ang(v):
        return math.radians(START - SPAN * v / vmax)

    # ticks
    n_minor = int(round(vmax / minor))
    for k in range(n_minor + 1):
        v = k * minor
        a = ang(v)
        is_major = abs((v / major) - round(v / major)) < 1e-6
        r1 = DIAL_R - 0.0025
        r0 = r1 - (0.0060 if is_major else 0.0030)
        w = 0.0007 if is_major else 0.00045
        cc = np.array([cx + (r0 + r1) / 2 * math.cos(a), (r0 + r1) / 2 * math.sin(a), 0.0016])
        d = np.array([math.cos(a), math.sin(a), 0])
        t = np.array([-math.sin(a), math.cos(a), 0])
        v8, f = g.box_verts(cc, d * (r1 - r0) / 2, t * w, (0, 0, 0.0003))
        (batch_red if v >= red_from else batch_ticks).add(g.apply_np(v8, M), f)
    # red zone arc band
    if red_from < vmax:
        a0, a1 = ang(red_from), ang(vmax)
        n = 24
        for k in range(n):
            t0 = a0 + (a1 - a0) * k / n
            t1 = a0 + (a1 - a0) * (k + 1) / n
            r0, r1 = DIAL_R - 0.0025, DIAL_R - 0.0012
            q = [(cx + r0 * math.cos(t0), r0 * math.sin(t0), 0.0013),
                 (cx + r1 * math.cos(t0), r1 * math.sin(t0), 0.0013),
                 (cx + r1 * math.cos(t1), r1 * math.sin(t1), 0.0013),
                 (cx + r0 * math.cos(t1), r0 * math.sin(t1), 0.0013)]
            batch_red.add(g.apply_np(q, M), [(0, 1, 2, 3)])
    # numbers
    for v, txt in labels:
        a = ang(v)
        r = DIAL_R - (0.0150 if len(txt) > 2 else 0.0135)
        ob = g.text_mesh("tmp_lbl", txt, size=(0.0052 if len(txt) > 2 else 0.0068), col=COL, extrude=0.0002)
        tv = g.verts_of(ob) + np.array([cx + r * math.cos(a), r * math.sin(a), 0.0013])
        g.set_verts(ob, g.apply_np(tv, M))
        batch_txt.add_object(ob)
    # needle (tapered, slightly raised) + centre cap
    a = ang(value)
    d = np.array([math.cos(a), math.sin(a), 0])
    t = np.array([-math.sin(a), math.cos(a), 0])
    c0 = np.array([cx, 0, 0.0045])
    pts = [c0 - d * 0.010 - t * 0.0013, c0 + d * (DIAL_R - 0.004) - t * 0.00035,
           c0 + d * (DIAL_R - 0.004) + t * 0.00035, c0 - d * 0.010 + t * 0.0013]
    V = np.array(pts + [p + np.array([0, 0, 0.0008]) for p in pts])
    F = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    nd = g.mk(f"Cluster_{name}_Needle", g.apply_np(V, M), F, COL, ctx.mat("needle_red"), None)
    cap = g.lathe(f"Cluster_{name}_NeedleCap", [(0, 0.0072), (0.0050, 0.0068), (0.0068, 0.0055),
                                                 (0.0072, 0.0030), (0.0072, 0.0)],
                  origin=(cx, 0, 0), segments=32, col=COL, mat=ctx.mat("black_satin"))
    cap.data.transform(M)


def build(ctx):
    L = layout.get(ctx)
    hood = _hood(ctx, L)
    ctx.register("cluster_hood", hood)
    M = _frame(L)
    face = ctx.mat("gauge_face")
    chrome = ctx.mat("chrome")
    # back plate (dial plate) filling the hood opening
    plate = g.prism("Cluster_Backplate", g.rrect(0.400, 0.150, 0.045, 8, (0, 0.006)), -0.004, 0.0,
                    COL, ctx.mat("hard_plastic"))
    plate.data.transform(M)
    ticks = g.Batch("Cluster_Ticks", COL, ctx.mat("gauge_marks"))
    red = g.Batch("Cluster_RedZone", COL, ctx.mat("needle_red"))
    txt = g.Batch("Cluster_Numerals", COL, ctx.mat("gauge_marks"), smooth=None)
    for side, nm in ((-1, "Tach"), (1, "Speedo")):
        cx = side * DIAL_DX
        # dial face (slightly dished) + chrome ring with inner bevel
        dial = g.lathe(f"Cluster_{nm}_Face", [(0, 0.0012), (DIAL_R, 0.0012), (DIAL_R, -0.002)],
                       origin=(cx, 0, 0), segments=64, col=COL, mat=face)
        dial.data.transform(M)
        ring = g.lathe(f"Cluster_{nm}_Ring", [(DIAL_R - 0.0003, 0.0013), (DIAL_R + 0.0004, 0.0055),
                                              (DIAL_R + 0.0022, 0.0062), (DIAL_R + 0.0038, 0.0050),
                                              (DIAL_R + 0.0045, 0.0005), (DIAL_R + 0.0045, -0.002)],
                       origin=(cx, 0, 0), segments=72, col=COL, mat=chrome, smooth=60)
        ring.data.transform(M)
        if nm == "Tach":
            labels = [(v, str(v)) for v in range(0, 6)]
            _scale(ctx, nm, cx, labels, 6.0, 1.0, 0.5, 4.5, M, ticks, red, txt, 0.0)   # 2.0 TDI: 0-6, red 4.5 (S/E)
        else:
            labels = [(v, str(v)) for v in range(0, 261, 20)]
            _scale(ctx, nm, cx, labels, 260.0, 20.0, 10.0, 999, M, ticks, red, txt, 0.0)
        # coolant temp (tach) / fuel (speedo) LED-segment gauge in the lower dial sector
        for k in range(10):
            a = math.radians(-90 - side * 0 + (k - 4.5) * 7.5)
            r = DIAL_R * 0.52
            c = np.array([cx + r * math.cos(a), r * math.sin(a) - 0.002, 0.0014])
            d = np.array([math.cos(a), math.sin(a), 0])
            t = np.array([-math.sin(a), math.cos(a), 0])
            v8, f = g.box_verts(c, d * 0.0028, t * 0.0011, (0, 0, 0.0002))
            (red if (nm == "Tach" and k > 7) else ticks).add(g.apply_np(v8, M), f)
    ticks.build()
    red.build()
    txt.build()
    # central FIS colour display in a gloss frame
    fr = g.prism("Cluster_FIS_Frame", g.rrect(FIS_W + 0.008, FIS_H + 0.010, 0.006, 6, (0, 0.002)),
                 0.0, 0.0018, COL, ctx.mat("piano_black"), bevel=0.0006)
    fr.data.transform(M)
    scr = g.prism("Cluster_FIS_Screen", g.rrect(FIS_W, FIS_H, 0.002, 4, (0, 0.002)), 0.0018, 0.0021,
                  COL, ctx.mat("screen"))
    scr.data.transform(M)
    ui = g.Batch("Cluster_FIS_Content", COL, ctx.mat("screen_ui"), smooth=None)
    for txt_, y, sz in (("D", 0.026, 0.009), ("12:30", -0.008, 0.0062), ("21.5°C", -0.022, 0.0050),
                        ("0 km/h", 0.008, 0.0062)):
        ob = g.text_mesh("tmp", txt_, size=sz, col=COL, extrude=0.0001)
        g.set_verts(ob, g.apply_np(g.verts_of(ob) + np.array([0, y, 0.0022]), M))
        ui.add_object(ob)
    for k in range(3):   # thin separator lines
        v, f = g.box_verts((0, 0.017 - k * 0.0165 if k < 2 else -0.030, 0.0022), (0.019, 0, 0),
                           (0, 0.00025, 0), (0, 0, 0.0001))
        ui.add(g.apply_np(v, M), f)
    ui.build()
    # warning-lamp strip under the FIS and the two adjuster buttons below the dials
    for s in (-1, 1):
        b = g.lathe(f"Cluster_Button_{'L' if s < 0 else 'R'}", [(0, 0.004), (0.0035, 0.0037),
                                                                 (0.0042, 0.0)],
                    origin=(s * 0.150, -0.062, 0), segments=20, col=COL, mat=ctx.mat("black_satin"))
        b.data.transform(M)
