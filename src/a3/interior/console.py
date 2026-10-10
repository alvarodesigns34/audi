"""Centre console (8V, S tronic): stack foot with start button and twin
cupholders, S tronic selector (leather knob with release button, gaiter,
P R N D S indicator), MMI terminal with MMI touch rotary, EPB / auto-hold,
leather armrest, rear-end with vents.  Order front -> rear as in the photos.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh, scene
from ..core.curves import Line
from . import _geo as g
from . import layout

COL = "Interior/Console"

# E longitudinal stations of the console (x) and its top height / half width
TOP = Line([(-840, 692), (-880, 675), (-905, 630), (-918, 560), (-930, 500), (-945, 474),
            (-975, 468), (-1460, 466),
            (-1500, 480), (-1535, 520), (-1560, 528), (-1840, 528), (-1890, 515), (-1925, 470),
            (-1945, 380)])
HW = Line([(-840, 138), (-1000, 128), (-1300, 122), (-1550, 118), (-1900, 116), (-1945, 112)])

X_CUP = -0.995      # E cupholders (between stack and selector)
X_SEL = -1.125      # E selector lever axis
X_MMI = -1.285      # E MMI rotary
X_EPB = -1.405      # E EPB / auto hold


def top_z(x):
    return float(TOP(x))


def _body(ctx, L):
    xs = np.concatenate([np.linspace(-0.84, -1.04, 14), np.linspace(-1.06, -1.46, 10),
                         np.linspace(-1.48, -1.58, 7), np.linspace(-1.62, -1.945, 14)])
    secs = []
    fz = L.floor_z
    for x in xs:
        t = top_z(x)
        hw = float(HW(x))
        r = 0.022
        # right side bottom -> up -> top -> left side down (clockwise seen from rear)
        side = [(-(hw + 0.030), fz), (-(hw + 0.014), fz + 0.10), (-(hw + 0.006), t - 0.12),
                (-hw, t - r)]
        arc = [(-hw + r - r * math.cos(a), t - r + r * math.sin(a))
               for a in np.linspace(0.15, math.pi / 2, 5)]
        top = [(-hw + r + 0.01, t), (0.0, t + 0.002), (hw - r - 0.01, t)]
        pts = side + arc + top
        pts += [(-yy, zz) for (yy, zz) in reversed(side + arc)]
        sec = np.array([(x, yy, zz) for (yy, zz) in pts])
        secs.append(sec)
    body = g.loft("Console_Body", secs, COL, ctx.mat("hard_plastic"), closed=True, cap=True,
                  smooth=45)
    g.finish(body, 45)
    return body


def _cutters(L):
    cut = scene.temp_collection("_tmp_console_cut")
    for s in (1, -1):
        g.lathe("cut", [(0, -0.20), (0.039, -0.20), (0.039, 0.05), (0, 0.05)],
                origin=(X_CUP, s * 0.050, top_z(X_CUP) - 0.0), axis=(0, 0, 1), segments=40, col=cut)
    return cut


def build(ctx):
    L = layout.get(ctx)
    body = _body(ctx, L)
    ctx.register("console_body", body)
    alu = ctx.mat("aluminium_matt")

    # --- top trim plate (black satin with aluminium frame) ------------------
    x0, x1 = -0.948, -1.465
    plate_w = 0.205
    zt = top_z(-1.2)
    outline = g.rrect(x0 - x1, plate_w, 0.018, 6, ((x0 + x1) / 2, 0))
    fr = g.prism("Console_TopFrame", outline, zt - 0.004, zt + 0.0035, COL, alu, bevel=0.0012)
    pl = g.prism("Console_TopPlate", g.rrect(x0 - x1 - 0.006, plate_w - 0.006, 0.015, 6,
                                              ((x0 + x1) / 2, 0)),
                 zt - 0.003, zt + 0.0045, COL, ctx.mat("black_satin"), bevel=0.0010)
    _cupholders(ctx, L, [body, fr, pl], zt + 0.0045)
    _start_button(ctx, L)
    _selector(ctx, L, zt + 0.0045)
    _mmi_terminal(ctx, L, zt + 0.0045)
    _epb(ctx, L, zt + 0.0045)
    _armrest(ctx, L)
    _rear_end(ctx, L)
    _side_stitching(ctx, L, body)


def _cupholders(ctx, L, targets, zt):
    import bpy
    for ob in targets:
        cut = _cutters(L)
        mesh.boolean(ob, cut, "DIFFERENCE")
        bpy.data.collections.remove(cut)
        g.single_material(ob, ob.data.materials[0])
        g.finish(ob, 45)
    for s, nm in ((1, "L"), (-1, "R")):
        c = (X_CUP, s * 0.050, zt)
        cup = g.lathe(f"Console_Cup_{nm}", [(0.039, 0.001), (0.0385, -0.010), (0.037, -0.075),
                                            (0.030, -0.080), (0.0, -0.080)],
                      origin=c, segments=40, col=COL, mat=ctx.mat("hard_plastic"))
        mesh.recalc_normals(cup, inside=True)
        mat_ = g.lathe(f"Console_Cup_{nm}_Mat", [(0.0, -0.0785), (0.031, -0.0785), (0.031, -0.0775),
                                                 (0.0, -0.0775)],
                       origin=c, segments=40, col=COL, mat=ctx.mat("rubber_pad"))
        ring = g.lathe(f"Console_Cup_{nm}_Ring", [(0.0388, -0.004), (0.0388, 0.0015),
                                                  (0.0398, 0.0028), (0.0420, 0.0028),
                                                  (0.0428, 0.0012), (0.0428, -0.002)],
                       origin=c, segments=48, col=COL, mat=ctx.mat("chrome"))
    # divider between the cups
    g.rbox("Console_Cup_Divider", (0.050, 0.016, 0.010), (X_CUP, 0, zt - 0.006), 0.005, 2, COL,
           ctx.mat("hard_plastic"))


def _start_button(ctx, L):
    """Engine start/stop button on the stack foot (S tronic, Advanced key)
    plus the ESC/sport switch next to it."""
    z = 0.585
    x = -0.913
    nrm = g._n((-1.0, 0, 0.30))
    c = np.array([x - 0.004, 0.0, z])
    g.lathe("Console_StartStop_Ring", [(0.0115, 0.0), (0.0125, 0.004), (0.0135, 0.006),
                                       (0.0150, 0.006), (0.0160, 0.002), (0.0160, -0.004)],
            origin=c, axis=nrm, segments=40, col=COL, mat=ctx.mat("chrome"))
    g.lathe("Console_StartStop_Button", [(0.0, 0.0065), (0.0090, 0.0060), (0.0110, 0.0045),
                                         (0.0112, -0.003)],
            origin=c, axis=nrm, segments=40, col=COL, mat=ctx.mat("piano_black"))
    g.lathe("Console_StartStop_LED", [(0.0110, 0.0050), (0.0116, 0.0052), (0.0116, 0.0042),
                                      (0.0110, 0.0040)],
            origin=c, axis=nrm, segments=40, col=COL, mat=ctx.mat("led_red"))
    t = g.text_mesh("Console_StartStop_Text", "START", size=0.0032, col=COL, mat=ctx.mat("screen_ui"),
                    extrude=0.00008)
    t.data.transform(g.frame(c + nrm * 0.0066, nrm, (0, -1, 0)))


def _selector(ctx, L, zs):
    """S tronic selector lever."""
    leather = ctx.mat("leather_black")
    alu = ctx.mat("aluminium_matt")
    x = X_SEL
    # gate bezel: aluminium oval frame, piano black insert with slot
    g.prism("Console_Gate_Frame", g.rrect(0.115, 0.082, 0.030, 8, (x, 0.0)), zs - 0.002,
            zs + 0.004, COL, alu, bevel=0.0012)
    g.prism("Console_Gate_Insert", g.rrect(0.107, 0.074, 0.026, 8, (x, 0.0)), zs - 0.001,
            zs + 0.0048, COL, ctx.mat("piano_black"), bevel=0.0008)
    # P R N D S indicator on the driver's side of the gate (left = +y)
    for i, ch in enumerate("PRNDS"):
        m = ctx.mat("screen_ui_red") if ch == "D" else ctx.mat("screen_ui")
        t = g.text_mesh(f"Console_Gate_{ch}", ch, size=0.0068, col=COL, mat=m, extrude=0.0001)
        # letters read from the driver's seat: upright toward -x, stacked front->rear
        t.data.transform(g.frame((x + 0.032 - i * 0.0155, 0.026, zs + 0.0049), (0, 0, 1), (0, -1, 0)))
    # gaiter: leather boot with folds from the slot to the knob collar
    nz, nt = 18, 40
    secs = []
    zb, ztop = zs + 0.004, zs + 0.060
    for k in range(nz):
        u = k / (nz - 1)
        zz = zb + (ztop - zb) * u
        r = 0.030 * (1 - u) ** 1.3 + 0.0115 * u
        fold = 0.0025 * math.sin(u * math.pi * 3.0) * (1 - u)
        th = np.linspace(0, 2 * math.pi, nt, endpoint=False)
        rr = r + fold + 0.0010 * np.sin(th * 5 + u * 4)
        ax_, ay_ = 1.25, 0.95                     # oval (longer in x)
        secs.append(np.stack([x + rr * ax_ * np.cos(th) - 0.006 * u, rr * ay_ * np.sin(th),
                              np.full(nt, zz)], 1))
    boot = g.loft("Console_Selector_Gaiter", secs, COL, leather, closed=True, smooth=60)
    g.finish(boot, 60)
    # knob: leather 'pistol' shape leaning back, alu collar, release button
    collar = g.lathe("Console_Selector_Collar", [(0.0122, 0.0), (0.0128, 0.002), (0.0128, 0.010),
                                                 (0.0120, 0.012)],
                     origin=(x - 0.006, 0, ztop - 0.002), segments=36, col=COL, mat=alu)

    def knob_fn(p):
        p = p.copy()
        h = (p[:, 2] + 0.040) / 0.080                  # 0 bottom .. 1 top
        p[:, 0] *= 0.78 + 0.30 * h                     # flares toward the top
        p[:, 1] *= 0.80 + 0.22 * h
        p[:, 0] -= 0.014 * h ** 2                      # leans back toward the driver
        return p
    knob = g.pillow("Console_Selector_Knob", (0.060, 0.052, 0.080), (x - 0.006, 0, ztop + 0.040),
                    (2.4, 2.4, 2.3), 16, COL, leather, fn=knob_fn)
    cap = g.pillow("Console_Selector_Cap", (0.040, 0.032, 0.008), (x - 0.016, 0, ztop + 0.0795),
                   (2.6, 2.6, 2.0), 10, COL, ctx.mat("black_satin"))
    # release button on the front face of the knob
    btn = g.pillow("Console_Selector_Release", (0.008, 0.020, 0.024), (x + 0.020, 0.0, ztop + 0.046),
                   (2.5, 3.0, 3.0), 6, COL, ctx.mat("black_satin"))
    # leather seams down the knob sides
    surf = g.Surface(knob)
    b = g.Batch("Console_Selector_Stitching", COL, ctx.mat("stitch_grey"))
    for s in (1, -1):
        pts = [(x - 0.006 - 0.006 * t, s * 0.03, ztop + 0.008 + 0.064 * t) for t in np.linspace(0, 1, 30)]
        g.stitch_on(b, surf, pts, (0, s, 0), pitch=0.0035, length=0.0025)
    b.build()


def _mmi_terminal(ctx, L, zs):
    """MMI rotary/push with touchpad top, 4 function keys, 2 softkey rockers,
    MENU/BACK, set in piano black with an aluminium frame."""
    x = X_MMI
    alu = ctx.mat("aluminium_matt")
    sat = ctx.mat("black_satin")
    pb = ctx.mat("piano_black")
    g.prism("Console_MMI_Frame", g.rrect(0.110, 0.120, 0.024, 8, (x, 0)), zs - 0.002, zs + 0.0038,
            COL, alu, bevel=0.0012)
    g.prism("Console_MMI_Base", g.rrect(0.104, 0.114, 0.021, 8, (x, 0)), zs - 0.001, zs + 0.0045,
            COL, pb, bevel=0.0008)
    # rotary: knurled aluminium ring + black glass touch surface
    c = (x, 0.0, zs + 0.0045)
    g.lathe("Console_MMI_Rotary", [(0.0, 0.0190), (0.0170, 0.0190), (0.0200, 0.0175),
                                   (0.0212, 0.0150), (0.0212, 0.0020), (0.0225, 0.0)],
            origin=c, segments=64, col=COL, mat=ctx.mat("knurl_alu"))
    kn = g.Batch("Console_MMI_Rotary_Knurl", COL, ctx.mat("knurl_alu"))
    for i in range(72):
        a = 2 * math.pi * i / 72
        cc = np.array([x + 0.0213 * math.cos(a), 0.0213 * math.sin(a), zs + 0.0045 + 0.009])
        v, f = g.box_verts(cc, np.array([math.cos(a), math.sin(a), 0]) * 0.0004,
                           np.array([-math.sin(a), math.cos(a), 0]) * 0.00035, (0, 0, 0.0055))
        kn.add(v, f)
    kn.build()
    g.lathe("Console_MMI_Touchpad", [(0.0, 0.0198), (0.0160, 0.0196), (0.0168, 0.0190)],
            origin=c, segments=64, col=COL, mat=pb)
    # 4 function keys (NAV/MAP, TEL, RADIO, MEDIA) around the rotary
    keys = g.Batch("Console_MMI_Keys", COL, sat)
    lbl = g.Batch("Console_MMI_Key_Labels", COL, ctx.mat("screen_ui"), smooth=None)
    names = [("NAV", 0.034, 0.036), ("TEL", 0.034, -0.036), ("RADIO", -0.034, 0.036),
             ("MEDIA", -0.034, -0.036)]
    for nm, dx, dy in names:
        b = g.rbox("tmp", (0.018, 0.020, 0.005), (x + dx, dy, zs + 0.006), 0.0025, 2, COL)
        keys.add_object(b)
        t = g.text_mesh("tmp", nm, size=0.0032, col=COL, extrude=0.00006)
        t.data.transform(g.frame((x + dx, dy, zs + 0.0086), (0, 0, 1), (0, -1, 0)))
        lbl.add_object(t)
    # softkey rockers left/right of the rotary
    for s in (1, -1):
        b = g.rbox("tmp", (0.026, 0.008, 0.005), (x, s * 0.034, zs + 0.006), 0.0025, 2, COL)
        keys.add_object(b)
    # MENU / BACK at the rear
    for s, nm in ((1, "MENU"), (-1, "BACK")):
        b = g.rbox("tmp", (0.010, 0.032, 0.0045), (x - 0.044, s * 0.020, zs + 0.0058), 0.002, 2, COL)
        keys.add_object(b)
        t = g.text_mesh("tmp", nm, size=0.0030, col=COL, extrude=0.00006)
        t.data.transform(g.frame((x - 0.044, s * 0.020, zs + 0.0081), (0, 0, 1), (0, -1, 0)))
        lbl.add_object(t)
    keys.build()
    lbl.build()
    # volume knob (front right of the MMI, as in the photos)
    cv = (X_SEL - 0.002, -0.072, zs + 0.0045)
    g.lathe("Console_Volume_Knob", [(0.0, 0.016), (0.0080, 0.016), (0.0092, 0.0145),
                                    (0.0095, 0.0), (0.0110, -0.001)],
            origin=cv, segments=40, col=COL, mat=ctx.mat("knurl_alu"))
    g.lathe("Console_Volume_Top", [(0.0, 0.0163), (0.0078, 0.0161), (0.0082, 0.0155)],
            origin=cv, segments=40, col=COL, mat=pb)


def _epb(ctx, L, zs):
    """Electric parking brake switch (P) and AUTO HOLD, plus a coin tray."""
    x = X_EPB
    sat = ctx.mat("black_satin")
    g.prism("Console_EPB_Surround", g.rrect(0.042, 0.090, 0.008, 5, (x, -0.030)), zs - 0.001,
            zs + 0.0045, COL, ctx.mat("piano_black"), bevel=0.0008)
    epb = g.rbox("Console_EPB_Switch", (0.030, 0.034, 0.010), (x, -0.050, zs + 0.007), 0.004, 3, COL,
                 sat)
    hold = g.rbox("Console_AutoHold_Button", (0.026, 0.030, 0.006), (x, -0.012, zs + 0.0055), 0.003,
                  3, COL, sat)
    lbl = g.Batch("Console_EPB_Symbols", COL, ctx.mat("screen_ui"), smooth=None)
    for txt, y, z in (("(P)", -0.050, zs + 0.0121), ("AUTO", -0.012, zs + 0.0086)):
        t = g.text_mesh("tmp", txt, size=0.0045 if txt == "(P)" else 0.0032, col=COL,
                        extrude=0.00006)
        t.data.transform(g.frame((x, y, z), (0, 0, 1), (0, -1, 0)))
        lbl.add_object(t)
    lbl.build()
    # small storage tray on the driver side (rubber mat)
    g.prism("Console_Tray_Mat", g.rrect(0.040, 0.050, 0.006, 4, (x, 0.040)), zs - 0.002,
            zs + 0.0025, COL, ctx.mat("rubber_pad"))


def _armrest(ctx, L):
    """Leather armrest lid (sliding) with two stitched seams along its sides."""
    xa0, xa1 = -1.505, -1.835
    zt = top_z(-1.70)
    cx = (xa0 + xa1) / 2

    def fn(p):
        p = p.copy()
        u = (p[:, 0] - p[:, 0].min()) / (np.ptp(p[:, 0]) + 1e-9)
        p[:, 2] += 0.012 * np.sin(u * math.pi) * (p[:, 2] > 0)     # soft crown
        p[:, 2] -= 0.010 * (1 - u) ** 3                            # front edge rolls down
        return p
    arm = g.pillow("Console_Armrest", (xa0 - xa1, 0.175, 0.060), (cx, 0, zt + 0.032),
                   (3.2, 3.5, 2.6), 18, COL, ctx.mat("leather_black"), fn=fn)
    ctx.register("console_armrest", arm)
    base = g.rbox("Console_Armrest_Base", (xa0 - xa1 - 0.02, 0.165, 0.030), (cx - 0.005, 0, zt + 0.002),
                  0.008, 2, COL, ctx.mat("hard_plastic"))
    surf = g.Surface(arm)
    b = g.Batch("Console_Armrest_Stitching", COL, ctx.mat("stitch_grey"))
    zz = zt + 0.032 + 0.026
    for s in (1, -1):
        pts = [(x, s * 0.072, zz + 0.010) for x in np.linspace(xa0 - 0.02, xa1 + 0.02, 40)]
        g.stitch_on(b, surf, pts, (0, s * 0.3, 1), lateral=(0.0, 0.004))
    # front transverse seam
    pts = [(xa0 - 0.035, y, zz + 0.01) for y in np.linspace(-0.07, 0.07, 30)]
    g.stitch_on(b, surf, pts, (0.2, 0, 1))
    b.build()


def _rear_end(ctx, L):
    """Rear face of the console: two rectangular rear vents with slats and a
    12 V socket below."""
    x = -1.94
    for s, nm in ((1, "L"), (-1, "R")):
        yc = s * 0.042
        zc = 0.462
        g.rbox(f"Console_RearVent_{nm}_Frame", (0.012, 0.064, 0.042), (x - 0.002, yc, zc), 0.004, 2,
               COL, ctx.mat("black_satin"))
        sl = g.Batch(f"Console_RearVent_{nm}_Slats", COL, ctx.mat("hard_plastic"))
        for k in range(5):
            v, f = g.box_verts((x - 0.0085, yc, zc - 0.014 + k * 0.007), (0.002, 0, 0),
                               (0, 0.028, 0), (0, 0, 0.0007))
            sl.add(v, f)
        sl.build()
        g.rbox(f"Console_RearVent_{nm}_Thumb", (0.006, 0.008, 0.010), (x - 0.011, yc, zc), 0.002, 2,
               COL, ctx.mat("aluminium_matt"))
    g.lathe("Console_12V_Socket", [(0.0, -0.012), (0.0105, -0.012), (0.0105, 0.0), (0.0135, 0.0),
                                   (0.0135, 0.002), (0.0, 0.002)],
            origin=(x - 0.003, 0, 0.38), axis=(-1, 0, 0), segments=32, col=COL,
            mat=ctx.mat("black_satin"))


def _side_stitching(ctx, L, body):
    """Stitched seam running down the knee pads on both console flanks (as in
    the reference photos: from the dash down along the stack side)."""
    surf = g.Surface(body)
    b = g.Batch("Console_Side_Stitching", COL, ctx.mat("stitch_grey"))
    for s in (1, -1):
        ctrl = [(-0.86, 0.66), (-0.93, 0.58), (-1.02, 0.47), (-1.20, 0.43), (-1.45, 0.42),
                (-1.62, 0.43)]
        pts = []
        for x, z in g.spline(ctrl, 60):
            hw = float(HW(x))
            pts.append((x, s * (hw + 0.012), z))
        g.stitch_on(b, surf, pts, (0, s, 0), lateral=(0.0035, -0.0035))
    b.build()
