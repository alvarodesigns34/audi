"""Rear end: tail lamps, S line diffuser with twin left tail pipes, licence
plate, rear rings, S line roof spoiler with third brake light, rear wiper and
roof antenna."""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..body import surftools as st
from ..core import mesh, scene
from ..core.curves import catmull_rom, resample, rounded_polygon
from . import front_end as fe

COL = "Exterior/Rear"
LCOL = "Exterior/Lights"


def _rear_x(surf, y, z):
    P, N = surf.project([(y, z)], "YZ", side=-1)
    return (P[0], N[0]) if P[0] is not None else (None, None)


def _taillight(ctx, ref, surf, mirror):
    sfx = ".R" if mirror else ".L"
    s = -1 if mirror else 1
    tmp = scene.temp_collection("_tmp_patch")
    parts = []
    for cut in op.taillight_prisms(tmp, mirror=mirror):
        parts.append(st.patch_with_cutter(ref, cut, cut.name.replace("Cut_", "") + "_Lens",
                                          LCOL, ctx.mat("lens_red")))
    lens = mesh.join(parts, "Taillight_Lens" + sfx)
    # copies for the inner layers before the lens gets its thickness
    layers = []
    for nm, mat, d in (("Inner", "lens_red_dark", -0.022), ("Housing", "lamp_housing", -0.075)):
        c = lens.copy()
        c.data = lens.data.copy()
        scene.link(c, LCOL)
        c.name = f"Taillight_{nm}{sfx}"
        c.data.materials.clear()
        c.data.materials.append(ctx.mat(mat))
        st.offset(c, d)
        layers.append(c)
    st.offset(lens, 0.0006)
    mesh.solidify(lens, 0.003, offset=-1.0)
    mesh.shade_smooth(lens, 60)
    # LED light bars: follow the lamp's upper edge, wrapping onto the side
    top = np.asarray(op.TAILLIGHT_REAR[:6], float) * 1e-3
    for nm, dz in (("Upper", -0.024), ("Lower", -0.060)):
        pts = []
        for y in np.linspace(0.43, 0.89, 26):
            z = np.interp(y, top[:, 0], top[:, 1]) + dz
            P, N = surf.project([(s * y, z)], "YZ", side=-1)
            if P[0] is not None and P[0][0] < op.TL_SPLIT_X * 1e-3:
                pts.append(P[0] - N[0] * 0.014)
        for x in np.linspace(op.TL_SPLIT_X * 1e-3, -2.97, 6):
            P, N = surf.project([(x, 0.925 + dz * 0.8)], "XZ", side=s)
            if P[0] is not None:
                pts.append(P[0] - N[0] * 0.014)
        if len(pts) > 3:
            mesh.tube_along(f"Taillight_LED_{nm}{sfx}", resample(np.array(pts), 50), 0.0032,
                            sides=8, collection=LCOL, material=ctx.mat("led_red"))
    # reversing lamp reflector (white) in the tailgate section (inner end)
    P, N = surf.project([(s * 0.47, 0.90)], "YZ", side=-1)
    if P[0] is not None:
        mesh.revolve("Taillight_Reverse" + sfx, np.array([[0.0, 0.0], [0.022, 0.0], [0.024, 0.012]]),
                     24, axis="X", center=P[0] + np.array([0.03, 0, 0]), collection=LCOL,
                     material=ctx.mat("reflector"))


def _diffuser(ctx, surf):
    dark = ctx.mat("black_textured")
    grey = ctx.mat("titanium_grey")
    chrome = ctx.mat("chrome")
    rows = []
    for z in np.linspace(0.238, 0.385, 12):
        row = []
        for y in np.linspace(-0.76, 0.76, 60):
            p, n = _rear_x(surf, y, z)
            x = (p[0] if p is not None else -3.30) + 0.025
            row.append((x, y, z))
        rows.append(row)
    mesh.grid_object("Diffuser_Panel", np.array(rows), collection=COL, material=dark, flip=True)
    # vertical fins
    for y in (-0.42, -0.14, 0.14):
        p, n = _rear_x(surf, y, 0.30)
        if p is None:
            continue
        mesh.extrude_polygon(f"Diffuser_Fin_{y:+.2f}", [(p[0] + 0.025, 0.240), (p[0] - 0.004, 0.240),
                                                     (p[0] - 0.004, 0.37), (p[0] + 0.025, 0.37)],
                             0.006, plane="XZ", offset=y - 0.003, collection=COL, material=grey)
    # twin round tail pipes (left), chrome, 76 mm, slightly protruding
    for (yy, zz) in op.EXHAUST_TIPS:
        y, z = yy * 1e-3, zz * 1e-3
        p, n = _rear_x(surf, y, z)
        x = (p[0] if p is not None else -3.38) - 0.012
        r = op.EXHAUST_D * 1e-3 / 2
        prof = np.array([[r * 0.86, x + 0.15], [r * 0.86, x + 0.004], [r * 0.93, x - 0.001],
                         [r, x + 0.004], [r, x + 0.15]])
        tip = mesh.revolve(f"Exhaust_Tip_{yy}", prof, 48, axis="X", center=(0, y, z),
                           collection=COL, material=chrome)
        inner = mesh.revolve(f"Exhaust_Inner_{yy}", np.array([[r * 0.85, x + 0.002],
                                                               [r * 0.85, x + 0.2], [0.0, x + 0.2]]),
                             48, axis="X", center=(0, y, z), collection=COL,
                             material=ctx.mat("steel_dark"))


def _plate_rings(ctx, surf):
    # rings on the tailgate
    chrome = ctx.mat("badge_chrome")
    cz = 0.930     # v0.2: sline_rear ray cast (v0.1: 0.946)
    od, pitch, tw = 0.078, 0.052, 0.009
    sec = rounded_polygon([(-tw / 2, -0.004), (tw / 2, -0.004), (tw / 2, 0.004),
                           (-tw / 2, 0.004)], 0.003, 4)
    for i in range(4):
        cy = (i - 1.5) * pitch
        r = od / 2 - tw / 2
        grid = []
        for t in np.linspace(0, 2 * math.pi, 96, endpoint=False):
            y, z = cy + r * math.cos(t), cz + r * math.sin(t)
            p, n = _rear_x(surf, y, z)
            pnt = np.array([(p[0] if p is not None else -3.40) - 0.006, y, z])
            radial = np.array([0, math.cos(t), math.sin(t)])
            grid.append([pnt + radial * q[0] - np.array([1.0, 0, 0]) * q[1] for q in sec])
        mesh.grid_object(f"Badge_Rings_Rear_{i}", np.array(grid), closed_u=True, closed_v=True,
                         collection=COL, material=chrome, flip=True)
    # licence plate on the tailgate, rotated to face rearwards
    obs = fe._plate(ctx, surf=None, cz=0.800, front=False)
    p, n = _rear_x(surf, 0.0, 0.80)
    for o in obs:
        mesh.transform(o, rot=(0, 0, math.pi))
        o.data.transform(__import__("mathutils").Matrix.Translation((p[0] - 0.012 if p is not None else -3.44, 0, 0)))
        for c in list(o.users_collection):
            c.objects.unlink(o)
        scene.link(o, COL)
        o.name = o.name.replace("Plate", "Plate_Rear")


def _spoiler(ctx, ref, surf):
    """S line roof spoiler: extends the roof ~120 mm over the rear window."""
    paint = ctx.mat("paint")
    black = ctx.mat("black_gloss")
    ys = np.linspace(-0.585, 0.585, 61)
    secs = []
    for y in ys:
        P, N = surf.project([(-3.10, y)], "XY", side=1)
        base = P[0] if P[0] is not None else np.array([-3.10, y, 1.34])
        taper = 1.0 - (abs(y) / 0.585) ** 6
        x_te = -3.10 - 0.165 - 0.015 * taper
        z_te = base[2] - 0.050
        top = [(base[0], y, base[2] + 0.001), (-3.19, y, base[2] - 0.010), (x_te, y, z_te)]
        bot = [(x_te + 0.004, y, z_te - 0.007), (-3.19, y, base[2] - 0.040),
               (base[0] - 0.015, y, base[2] - 0.022)]
        sec = catmull_rom(np.array(top), 6)[:-1].tolist() + catmull_rom(np.array(bot), 6).tolist()
        secs.append(sec)
    g = np.array(secs)
    sp = mesh.grid_object("Roof_Spoiler", g, closed_v=True, cap_u=True, collection=COL,
                          material=paint)
    # third brake light strip under the trailing edge
    path = np.array([(-3.255, y, s[11][2] - 0.012) for y, s in zip(ys[15:46], secs[15:46])])
    mesh.tube_along("Brake_Light_High", path, 0.004, sides=8, collection=LCOL,
                    material=ctx.mat("led_red"))


def _wiper_antenna(ctx, surf):
    black = ctx.mat("black_satin")
    # rear wiper: pivot under the glass bottom centre, arm along the glass
    P, N = surf.project([(-3.32, 0.0)], "XY", side=1)
    base = P[0] if P[0] is not None else np.array([-3.33, 0, 1.07])
    arm = np.array([base + np.array([-0.012, 0, 0.01]),
                    base + np.array([0.02, 0.32, 0.06]) * [0, 1, 0] + np.array([-0.0, 0, 0.012])])
    pts = []
    for t in np.linspace(0, 1, 20):
        y = 0.40 * t
        PP, NN = surf.project([(-3.34 + 0.12 * t, y)], "XY", side=1)
        if PP[0] is not None:
            pts.append(PP[0] + NN[0] * 0.012)
    if len(pts) > 2:
        mesh.sweep_profile("Rear_Wiper", np.array(pts),
                           np.array([[-0.006, -0.004], [0.006, -0.004], [0.005, 0.005],
                                     [-0.005, 0.005]]), collection=COL, material=black)
    # shark-fin roof antenna (rear of roof)
    P, N = surf.project([(-2.98, 0.0)], "XY", side=1)
    z0 = P[0][2] if P[0] is not None else 1.39
    L, H, W = 0.175, 0.062, 0.070
    secs = []
    for t in np.linspace(0, 1, 30):
        x = -2.98 + L / 2 - L * t
        h = H * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6 * (1 - 0.25 * t) if t < 0.98 else 0.0
        w = W / 2 * (0.35 + 0.65 * math.sin(math.pi * t) ** 0.5)
        ring = [(x, w * math.cos(a), z0 + max(h, 0.002) * (0.5 + 0.5 * math.sin(a)))
                for a in np.linspace(-math.pi / 2, 3 * math.pi / 2, 20, endpoint=False)]
        secs.append(ring)
    mesh.grid_object("Roof_Antenna", np.array(secs), closed_v=True, cap_u=True,
                     collection=COL, material=ctx.mat("paint"))


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    for mirror in (False, True):
        _taillight(ctx, ref, surf, mirror)
    _diffuser(ctx, surf)
    _plate_rings(ctx, surf)
    _spoiler(ctx, ref, surf)
    _wiper_antenna(ctx, surf)
    tmp = scene.temp_collection("_tmp_patch")
    for o in list(tmp.objects):
        scene.delete(o)
