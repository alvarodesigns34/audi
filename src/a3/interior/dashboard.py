"""Instrument panel (8V pre-facelift): low horizontal 'wing' upper dash, lower
dash with glovebox and knee panel, aluminium inlay, hazard strip, top grilles.

The upper dash ("wing") is a loft of (x, z) sections along y.  Each section
is a Catmull-Rom curve through control points that are functions of y, so the
same control point index corresponds across stations (no twisting).  In front
of the driver the section dips into the instrument 'tub' that the cluster
hood (cluster.py) covers.

Shared data published in ``ctx.data["dash"]``:
    face_x(y, z) -> x of the occupant-facing dash surface,
    top_z(x, y)  -> height of the dash top,
    surface      -> _geo.Surface for snapping (stitches, vents).
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from ..core.curves import catmull_rom, smoothstep
from . import _geo as g
from . import layout

COL = "Interior/Dashboard"
NSEG = 6   # samples per control segment


def _tub_w(L, y):
    """Mask of the instrument tub in front of the driver (0..1)."""
    yc = L.sw_centre[1]
    d = np.abs(y - yc)
    return 1.0 - smoothstep(0.170, 0.205, d)


def _lip(L, y):
    """Leading edge (x, z) of the wing at station y."""
    ay = abs(y)
    x = L.dash_lip_x - 0.018 * smoothstep(0.05, 0.30, ay)          # E slight sweep back off-centre
    x -= 0.085 * smoothstep(0.50, 0.70, ay)                         # E wraps back to the side vent pods
    z = L.dash_lip_z - 0.010 * smoothstep(0.45, 0.70, ay)
    return x, z


def wing_ctrl(L, y):
    """Control points (x, z) of the upper dash at station y (windscreen -> under)."""
    ay = abs(y)
    # front edge tucked 55 mm behind / 12 mm under the glass base (body cowl)
    xw = L.ws_base[0] - 0.055 + L.ws_base_side_dx * (ay / 0.65) ** 2
    zw = L.ws_base[1] + 0.002 + 0.010 * (ay / 0.70) ** 2
    lx, lz = _lip(L, y)
    w = float(_tub_w(L, y)) if y > 0 else 0.0
    tub_lip_z = 0.872                     # E lower bezel of the cluster (below the gauges)
    lz_e = lz + (tub_lip_z - lz) * w
    lx_e = lx + (-0.838 - lx) * w
    ztop = L.dash_top_z + 0.004 * smoothstep(0.3, 0.7, ay)
    face_low = min(lz_e - 0.070, L.inlay_z + 0.025)
    # the face below the nose is undercut 18-22 mm (the wing overhangs the vents)
    pts = [
        (xw, zw),
        (xw - 0.10, ztop - 0.003),
        (-0.64 + 0.10 * w, ztop - 0.004 * w),
        (lx_e + 0.075 - 0.02 * w, ztop - (ztop - tub_lip_z - 0.004) * w * 0.98),
        (lx_e + 0.016, lz_e - 0.0005),
        (lx_e - 0.0005, lz_e - 0.013),
        (lx_e + 0.008, lz_e - 0.032),
        (lx_e + 0.020, max(lz_e - 0.062, face_low + 0.004)),
        (lx_e + 0.022, face_low),
        (lx_e + 0.024, L.inlay_z - 0.004),
        (lx_e + 0.12, L.inlay_z - 0.020),
        (xw - 0.05, L.inlay_z - 0.010),
    ]
    return np.array(pts)


def lower_ctrl(L, y):
    """Lower dash (below the inlay) control points (x, z), top -> bottom -> under."""
    ay = abs(y)
    lx, _ = _lip(L, y)
    x0 = lx + 0.024
    zb = L.dash_bottom_z
    # centre stack (|y|<0.14) keeps a near-vertical face down to the console
    c = 1.0 - smoothstep(0.125, 0.150, ay)
    # driver knee panel recedes more than the glovebox
    k = float(smoothstep(0.12, 0.17, y)) if y > 0 else 0.0
    pts = [
        (x0 + 0.12, L.inlay_z + 0.004),
        (x0 + 0.001, L.inlay_z - 0.006),
        (x0 - 0.004 - 0.004 * c, L.inlay_z - 0.040),
        (x0 + 0.004 - 0.010 * c + 0.010 * k, 0.700 - 0.02 * c),
        (x0 + 0.030 - 0.035 * c + 0.035 * k, 0.600 - 0.02 * c),
        (x0 + 0.060 - 0.050 * c + 0.050 * k, zb + 0.025 - 0.06 * c),
        (x0 + 0.090 - 0.050 * c + 0.050 * k, zb - 0.06 * c),
        (x0 + 0.160, zb - 0.015 - 0.06 * c),
        (-0.62, zb + 0.02),
    ]
    return np.array(pts)


def _sections(ctrl_fn, L, ys):
    secs = []
    for y in ys:
        c = ctrl_fn(L, y)
        sp = catmull_rom(c, n_per_seg=NSEG, closed=False)
        s3 = np.stack([sp[:, 0], np.full(len(sp), y), sp[:, 1]], 1)
        secs.append(s3)
    return secs


def _stations(L, n=141):
    W = L.dash_half_w
    t = np.linspace(-1, 1, n)
    # denser near the ends where the wing wraps
    return W * np.sign(t) * (np.abs(t) ** 0.9)


class DashShape:
    """Queryable description of the dash used by other modules."""

    def __init__(self, L):
        self.L = L
        self._cache = {}

    def _curve(self, y, which="wing"):
        key = (which, round(float(y), 4))
        if key not in self._cache:
            fn = wing_ctrl if which == "wing" else lower_ctrl
            self._cache[key] = catmull_rom(fn(self.L, y), n_per_seg=24)
        return self._cache[key]

    def face_x(self, y, z):
        """x of the occupant-facing surface at (y, z) (searches wing then lower)."""
        for which in ("wing", "lower"):
            c = self._curve(y, which)
            # occupant side = minimum x among crossings of height z
            xs = []
            for a, b in zip(c[:-1], c[1:]):
                if (a[1] - z) * (b[1] - z) <= 0 and abs(b[1] - a[1]) > 1e-9:
                    t = (z - a[1]) / (b[1] - a[1])
                    xs.append(a[0] + t * (b[0] - a[0]))
            if xs:
                return min(xs)
        return self.L.dash_lip_x

    def top_z(self, x, y):
        c = self._curve(y, "wing")
        k = int(np.argmin(np.abs(c[: len(c) // 2, 0] - x)))
        return c[k, 1]


def build(ctx):
    L = layout.get(ctx)
    shape = DashShape(L)
    ctx.data["dash"] = {"shape": shape}
    soft = ctx.mat("soft_touch")
    hard = ctx.mat("hard_plastic")

    ys = _stations(L)
    wing = g.loft("Dash_Upper_Wing", _sections(wing_ctrl, L, ys), COL, soft, closed=True,
                  cap=True, smooth=50)
    g.finish(wing, 50)
    lower = g.loft("Dash_Lower", _sections(lower_ctrl, L, ys), COL, hard, closed=True,
                   cap=True, smooth=50)
    g.finish(lower, 50)
    ctx.register("dash_wing", wing)
    ctx.register("dash_lower", lower)

    _vent_holes(ctx, L, shape, wing)
    _glovebox(ctx, L, shape, lower)
    _inlay(ctx, L, shape)
    _hazard_strip(ctx, L, shape)
    _top_details(ctx, L, shape)
    _light_switch(ctx, L, shape)
    _knee_panel_details(ctx, L, shape, lower)
    ctx.data["dash"]["surface"] = g.Surface(wing, lower)


# ---------------------------------------------------------------------------

def vent_positions(L, shape):
    """(name, centre, axis) of the 4 round vents. Axis points to the cabin."""
    out = []
    for s, nm in ((1, "L"), (-1, "R")):
        y = s * L.vent_c_spacing / 2
        x = shape.face_x(y, L.vent_c_z)
        out.append((f"C_{nm}", np.array([x, y, L.vent_c_z]), g._n((-1, 0.0, 0.05))))
    for s, nm in ((1, "L"), (-1, "R")):
        y = s * L.vent_s_y
        x = shape.face_x(y, L.vent_s_z)
        # side vents face rearwards and slightly inboard (to the occupant)
        out.append((f"S_{nm}", np.array([x, y, L.vent_s_z]), g._n((-1, -s * 0.22, 0.05))))
    return out


def _vent_holes(ctx, L, shape, wing):
    from ..core import scene
    cut = scene.temp_collection("_tmp_vent_cut")
    r = L.vent_ring_d / 2 - 0.006
    for nm, c, ax in vent_positions(L, shape):
        cyl = g.lathe("cut_" + nm, [(0, -0.08), (r, -0.08), (r, 0.06), (0, 0.06)],
                      origin=c, axis=ax, segments=48, col=cut)
    mesh.boolean(wing, cut, "DIFFERENCE")
    import bpy
    bpy.data.collections.remove(cut)
    g.single_material(wing, ctx.mat("soft_touch"))
    g.finish(wing, 50)


def _glovebox(ctx, L, shape, lower):
    """Glovebox lid on the passenger side: a slightly proud panel following the
    lower dash with rounded edges (the shadow gap reads as the shut line)."""
    hard = ctx.mat("hard_plastic")
    y0, y1 = -0.62, -0.17       # E lid span
    z0, z1 = L.dash_bottom_z + 0.045, L.inlay_z - 0.030
    ny, nz = 46, 26
    yy = np.linspace(y0, y1, ny)
    zz = np.linspace(z0, z1, nz)
    pts = np.zeros((ny, nz, 3))
    for i, y in enumerate(yy):
        for j, z in enumerate(zz):
            pts[i, j] = (shape.face_x(y, z) - 0.0035, y, z)
    # round the lid corners by shrinking the border rows toward the panel
    lid = g.loft("Dash_Glovebox_Lid", list(pts), COL, hard, smooth=50)
    mesh.solidify(lid, 0.006, offset=1.0)
    mesh.add_bevel(lid, 0.003, segments=2, angle_deg=40)
    g.finish(lid, 50)
    # handle: horizontal recess grip with chrome-look strip at the top edge
    yh, zh = -0.40, z1 - 0.035
    xh = shape.face_x(yh, zh) - 0.010
    grip = g.rbox("Dash_Glovebox_Handle", (0.020, 0.105, 0.022), (xh, yh, zh), 0.004, 3, COL,
                  ctx.mat("black_satin"))
    strip = g.rbox("Dash_Glovebox_Handle_Trim", (0.006, 0.100, 0.003), (xh - 0.010, yh, zh + 0.0105),
                   0.001, 2, COL, ctx.mat("aluminium_matt"))


def _inlay(ctx, L, shape):
    """Aluminium inlay: passenger side from the centre stack to the door, and
    the short driver-side piece below the left vent."""
    alu = ctx.mat("inlay_alu")
    prof = g.rrect(0.008, 0.013, 0.0025, 4)     # (depth, height) local N/B
    for nm, ya, yb in (("Pass", -0.145, -0.700), ("Drv", 0.575, 0.700)):
        ys = np.linspace(ya, yb, 70)
        z = L.inlay_z + 0.004
        path = np.array([(shape.face_x(y, z) - 0.004, y, z) for y in ys])
        ob = g.sweep("Dash_Inlay_" + nm, path, prof, COL, alu, up=(0, 0, 1))
        g.finish(ob, 40)


def _hazard_strip(ctx, L, shape):
    """Switch strip under the central vents: hazard + ESC/start-stop/park
    buttons on piano black, chrome end caps."""
    pb = ctx.mat("piano_black")
    col = COL
    z = L.inlay_z + 0.003
    w = 0.29                                       # E strip width (between the inlay ends)
    x = shape.face_x(0.0, z) - 0.006
    body = g.rbox("Dash_SwitchStrip", (0.020, w, 0.022), (x, 0, z), 0.005, 3, col, pb)
    for s in (1, -1):
        g.rbox("Dash_SwitchStrip_Cap_" + ("L" if s > 0 else "R"), (0.022, 0.008, 0.024),
               (x - 0.001, s * (w / 2 + 0.002), z), 0.003, 3, col, ctx.mat("chrome"))
    # 8 rocker buttons
    btn = g.Batch("Dash_SwitchStrip_Buttons", col, ctx.mat("black_satin"))
    n = 8
    bw = (w - 0.03) / n
    for i in range(n):
        yb = -w / 2 + 0.015 + bw * (i + 0.5)
        if i in (3, 4):
            continue
        b = g.rbox("tmp", (0.006, bw - 0.004, 0.015), (x - 0.0105, yb, z), 0.002, 2, col)
        btn.add_object(b)
    btn.build()
    # hazard (centre, double-width, red triangle)
    hz = g.rbox("Dash_Hazard_Button", (0.007, 2 * bw - 0.004, 0.016), (x - 0.011, 0, z), 0.0025,
                2, col, ctx.mat("black_satin"))
    tri = g.prism("Dash_Hazard_Triangle", [(-0.006, -0.004), (0.006, -0.004), (0.0, 0.0065)],
                  0, 0.0006, col, ctx.mat("badge_red"))
    tri_in = g.prism("Dash_Hazard_Triangle_Inner", [(-0.0035, -0.0025), (0.0035, -0.0025), (0.0, 0.0036)], 0,
                     0.0007, col, ctx.mat("black_satin"))
    for o in (tri, tri_in):
        # local XY -> facing -X (cabin) at the button face
        g.place(o, (x - 0.0145, 0, z - 0.001), (-1, 0, 0), (0, -1, 0))
    ctx.register("dash_strip", body)


def _top_details(ctx, L, shape):
    """Defrost slots along the windscreen, centre sensor and the driver-side
    corner tweeter grille (slatted), side window demister outlets."""
    col = COL
    blk = ctx.mat("black_textured")
    # windscreen defrost: long slatted outlet near the glass
    b = g.Batch("Dash_Defrost_Slats", col, blk)
    for i in range(9):
        yi = -0.36 + i * 0.09
        xs = L.ws_base[0] - 0.090 + L.ws_base_side_dx * (yi / 0.65) ** 2
        zt = shape.top_z(xs, yi)
        for k in range(5):
            v, f = g.box_verts((xs - 0.004 * k, yi, zt + 0.0008), (0.0008, 0, 0), (0, 0.040, 0),
                               (0, 0, 0.0012))
            b.add(v, f)
    b.build()
    # light/sun sensor dome at the centre
    xs = L.ws_base[0] - 0.12
    zt = shape.top_z(xs, 0)
    g.lathe("Dash_Sun_Sensor", [(0, 0.0045), (0.004, 0.0040), (0.007, 0.0015), (0.0085, 0)],
            origin=(xs, 0, zt), axis=(0, 0, 1), segments=32, col=col, mat=ctx.mat("black_gloss"))
    # corner grilles (tweeter) both ends: 10 slats in a rounded frame
    for s, nm in ((1, "L"), (-1, "R")):
        yc = s * 0.56
        xc = L.ws_base[0] - 0.20 + L.ws_base_side_dx * (yc / 0.65) ** 2
        zt = shape.top_z(xc, yc)
        frame_ = g.rbox(f"Dash_Grille_Frame_{nm}", (0.11, 0.07, 0.004), (xc, yc, zt + 0.0005),
                        0.0018, 2, col, ctx.mat("hard_plastic"))
        sl = g.Batch(f"Dash_Grille_Slats_{nm}", col, blk)
        for k in range(10):
            v, f = g.box_verts((xc - 0.045 + k * 0.01, yc, zt + 0.0025), (0.0016, 0, 0),
                               (0, 0.03, 0), (0, 0, 0.0012))
            sl.add(v, f)
        sl.build()


def _light_switch(ctx, L, shape):
    """Rotary light switch module left of the steering column (8V: square
    bezel, knob with chrome ring, fog/AUTO pictograms as raised marks)."""
    col = COL
    y, z = 0.610, 0.708                       # E below the left vent, left of the wheel rim
    x = shape.face_x(y, z)
    ax = g._n((-1, -0.10, 0.15))
    bez = g.rbox("Dash_LightSwitch_Bezel", (0.085, 0.075, 0.012), (0, 0, -0.004), 0.006, 3, col,
                 ctx.mat("black_satin"))
    g.place(bez, (x, y, z), ax, (0, 1, 0))
    knob = g.lathe("Dash_LightSwitch_Knob", [(0, 0.022), (0.014, 0.022), (0.0155, 0.020),
                                             (0.0155, 0.004), (0.017, 0.002), (0.017, 0.0)],
                   origin=(x, y, z) + ax * 0.002, axis=ax, segments=40, col=col,
                   mat=ctx.mat("black_satin"))
    ring = g.lathe("Dash_LightSwitch_Ring", [(0.0150, 0.0225), (0.0158, 0.0215), (0.0158, 0.019),
                                             (0.0150, 0.0185)],
                   origin=(x, y, z) + ax * 0.002, axis=ax, segments=40, col=col,
                   mat=ctx.mat("chrome"))
    grip = g.rbox("Dash_LightSwitch_Grip", (0.024, 0.005, 0.010), (0, 0, 0.026), 0.0018, 2, col,
                  ctx.mat("black_satin"))
    g.place(grip, (x, y, z) + ax * 0.002, ax, (0, 1, 0))
    marks = g.Batch("Dash_LightSwitch_Marks", col, ctx.mat("gauge_marks"))
    for k, ang in enumerate((-60, -30, 0, 30)):
        a = math.radians(ang + 90)
        p = np.array([0.026 * math.cos(a), 0.026 * math.sin(a), 0.0025])
        v, f = g.box_verts(p, (0.0012, 0, 0), (0, 0.0012, 0), (0, 0, 0.0004))
        marks.add(v, f)
    m = marks.build()
    g.place(m, (x, y, z), ax, (0, 1, 0))
    # headlight range thumbwheel + dimmer to the left of the knob
    for k in range(2):
        wh = g.lathe(f"Dash_LightSwitch_Wheel_{k}", [(0, -0.003), (0.008, -0.003), (0.008, 0.003),
                                                       (0, 0.003)],
                     origin=(x - 0.006, y + 0.031, z + 0.018 - k * 0.032), axis=(0, 1, 0),
                     segments=24, col=col, mat=ctx.mat("black_textured"))


def _knee_panel_details(ctx, L, shape, lower):
    """Bonnet release handle below the driver's knee panel."""
    col = COL
    y, z = 0.60, L.dash_bottom_z + 0.02
    x = shape.face_x(y, z + 0.03) + 0.02
    g.rbox("Dash_Bonnet_Release", (0.035, 0.050, 0.018), (x - 0.01, y, z - 0.01), 0.004, 2, col,
           ctx.mat("black_satin"))
