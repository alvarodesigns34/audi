"""Retractable 7" MMI screen (8V pre-facelift), shown deployed.

The 11 mm thin housing rises out of a slot in the centre of the dash top.
Local frame: origin at the slot centre on the dash top, +Z toward the
occupants along the screen normal, +Y up the screen, +X to the right as seen
by the occupants (world -Y).
"""
from __future__ import annotations

import math

import numpy as np

from . import _geo as g
from . import layout

COL = "Interior/MMI"


def build(ctx):
    L = layout.get(ctx)
    shape = ctx.data["dash"]["shape"]
    W, H = L.mmi_size                  # 175 x 110 mm (E)
    T = L.mmi_thick                    # 11 mm (S/E)
    xs = L.mmi_slot_x
    zs = shape.top_z(xs, 0.0)
    tilt = math.radians(L.mmi_tilt_deg)
    # screen normal leans back: tilt about +Y (top moves forward, +x)
    nrm = np.array([-math.cos(tilt), 0.0, math.sin(tilt)])
    up = np.array([math.sin(tilt), 0.0, math.cos(tilt)])
    # the housing extends ~12 mm into the slot; visible height = H
    origin = np.array([xs, 0.0, zs]) + up * (H / 2 + 0.014)   # E bottom edge clears the lip
    M = g.frame(origin, nrm, (0, -1, 0))
    pb = ctx.mat("piano_black")

    hous = g.rbox("MMI_Housing", (W, H + 0.050, T), (0, -0.025, -T / 2), 0.0045, 3, COL, pb)
    hous.data.transform(M)
    # rear face: satin with slight draft (visible from the windscreen side)
    back = g.rbox("MMI_Housing_Back", (W - 0.010, H - 0.006, 0.0025), (0, 0, -T - 0.0008), 0.002,
                  2, COL, ctx.mat("black_satin"))
    back.data.transform(M)
    # display glass (7", 15:9 -> 154 x 92 mm active) slightly inset
    aw, ah = 0.154, 0.092
    scr = g.prism("MMI_Display", g.rrect(aw, ah, 0.0015, 3, (0, 0.002)), -0.0004, 0.0001, COL,
                  ctx.mat("screen"))
    scr.data.transform(M)

    # --- UI content as geometry (MMI 3G+ main menu look) -------------------
    ui = g.Batch("MMI_UI_Text", COL, ctx.mat("screen_ui"), smooth=None)
    dim = g.Batch("MMI_UI_Lines", COL, ctx.mat("screen_ui_dim"), smooth=None)
    red = g.Batch("MMI_UI_Highlight", COL, ctx.mat("screen_ui_red"), smooth=None)
    z = 0.0003

    def text(t, x, y, size, batch=ui, ax="LEFT"):
        ob = g.text_mesh("tmp", t, size=size, col=COL, extrude=0.00005, align_x=ax)
        g.set_verts(ob, g.apply_np(g.verts_of(ob) + np.array([x, y, z]), M))
        batch.add_object(ob)

    def bar(x0, x1, y0, y1, batch):
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        batch.add(g.apply_np(v, M), [(0, 1, 2, 3)])

    x0 = -aw / 2 + 0.008
    items = ["Navegación", "Teléfono", "Radio", "Media", "Car"]
    for i, t in enumerate(items):
        y = 0.022 - i * 0.0145
        if i == 3:
            bar(-aw / 2 + 0.003, -0.012, y - 0.0055, y + 0.0062, red)
        text(t, x0, y, 0.0062)
        bar(-aw / 2 + 0.003, -0.012, y - 0.0068, y - 0.0063, dim)
    text("Audi", -aw / 2 + 0.008, 0.039, 0.0058)
    text("12:30", aw / 2 - 0.008, 0.039, 0.0058, ax="RIGHT")
    bar(-aw / 2 + 0.003, aw / 2 - 0.003, 0.0335, 0.0340, dim)
    # right pane: 'now playing' card with progress bar and cover art frame
    for (a, b_, c, d) in ((0.000, 0.032, -0.022, -0.0214), (0.000, 0.032, 0.0114, 0.012),
                          (0.000, 0.0006, -0.022, 0.012), (0.0314, 0.032, -0.022, 0.012)):
        bar(a, b_, c, d, dim)
    text("Radio Nacional", 0.036, 0.004, 0.0050)
    text("FM 88.2", 0.036, -0.006, 0.0044)
    bar(0.000, 0.070, -0.030, -0.0292, dim)
    bar(0.000, 0.028, -0.030, -0.0292, red)
    # softkey labels at the bottom corners
    text("Menú", -aw / 2 + 0.008, -0.040, 0.0045)
    text("Ajustes", aw / 2 - 0.008, -0.040, 0.0045, ax="RIGHT")
    # cover-art: concentric 'disc' rings
    for r in (0.013, 0.009, 0.004):
        n = 40
        ring = []
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            c = (0.016, -0.005)
            q = [(c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), z),
                 (c[0] + (r + 0.0006) * math.cos(a0), c[1] + (r + 0.0006) * math.sin(a0), z),
                 (c[0] + (r + 0.0006) * math.cos(a1), c[1] + (r + 0.0006) * math.sin(a1), z),
                 (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1), z)]
            dim.add(g.apply_np(q, M), [(0, 1, 2, 3)])
    ui.build()
    dim.build()
    red.build()

    # --- slot in the dash top: recessed lip with rubber wiper ----------------
    sl_w, sl_d = W + 0.012, 0.022
    slot = g.prism("MMI_Slot_Bezel", g.rrect(sl_d, sl_w, 0.006, 5), 0.0, 0.0025, COL,
                   ctx.mat("black_satin"), bevel=0.0008)
    slot.data.transform(g.frame((xs + 0.002, 0, zs - 0.0012), (0, 0, 1), (1, 0, 0)))
    wip = g.prism("MMI_Slot_Wiper", g.rrect(sl_d - 0.006, sl_w - 0.006, 0.003, 4), 0.0, 0.0028,
                  COL, ctx.mat("rubber_seal"))
    wip.data.transform(g.frame((xs + 0.002, 0, zs - 0.0005), (0, 0, 1), (1, 0, 0)))
