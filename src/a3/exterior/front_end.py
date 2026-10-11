"""Front end details: Singleframe grille (S line, pre-facelift), Audi rings,
licence plate, S line side intakes (honeycomb + blade + fog lamp), lower lip,
headlight-washer covers, parking sensors and the engine-bay closure behind
the openings."""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..body import surftools as st
from ..core import mesh, scene
from ..core.curves import catmull_rom, resample, rounded_polygon

COL = "Exterior/Front"
GRILLE_FRAME = "chrome"       # "chrome" | "black"  (S line pre-facelift: chrome)


def _face_x(surf, y, z):
    P, N = surf.project([(y, z)], "YZ", side=1)
    return (P[0], N[0]) if P[0] is not None else (None, None)


def _outline3d(surf, outline_mm, n=220, closed=True):
    pts = np.asarray(outline_mm, float) * 1e-3
    dense = resample(catmull_rom(pts, 6, closed=closed), n, closed=closed)
    return st.clean_projection(*surf.project(dense, "YZ", side=1), closed=closed)


def _poly_halfwidth(outline_mm, z_mm):
    """Half width at height z of a symmetric outline given as a half outline."""
    p = np.asarray(outline_mm, float)
    best = 0.0
    for (y0, z0), (y1, z1) in zip(p[:-1], p[1:]):
        if min(z0, z1) <= z_mm <= max(z0, z1) and abs(z1 - z0) > 1e-9:
            t = (z_mm - z0) / (z1 - z0)
            best = max(best, y0 + t * (y1 - y0))
    return best * 1e-3


def _grille(ctx, surf):
    chrome = ctx.mat("chrome") if GRILLE_FRAME == "chrome" else ctx.mat("black_gloss")
    black = ctx.mat("black_gloss")
    back = ctx.mat("black_textured")
    g = np.asarray(op.GRILLE, float)
    full = np.vstack([g, (g[::-1] * [-1, 1])[1:-1]])
    P, N = _outline3d(surf, full, 300)
    # frame: rounded profile sitting on the opening edge
    prof = np.array([[-0.004, -0.012], [0.004, -0.012], [0.010, -0.004], [0.012, 0.004],
                     [0.008, 0.009], [0.0, 0.011], [-0.006, 0.008], [-0.008, 0.0]])
    mesh_ob = st.strip("Grille_Frame", P, N, prof, COL, chrome, closed=True)
    mesh.shade_smooth(mesh_ob, 60)

    # recessed back panel (follows the face shape, 55 mm behind it)
    gz = np.asarray(op.GRILLE, float)[:, 1] * 1e-3
    g_lo, g_hi = gz.min(), gz.max()
    zs = np.linspace(g_lo + 0.008, g_hi - 0.004, 26)
    rows = []
    for z in zs:
        w = _poly_halfwidth(op.GRILLE, z * 1000) + 0.01
        ys = np.linspace(-w, w, 40)
        row = []
        for y in ys:
            p, n = _face_x(surf, y, z)
            x = (p[0] if p is not None else 0.84) - 0.055
            row.append((x, y, z))
        rows.append(row)
    mesh.grid_object("Grille_Back", np.array(rows), collection=COL, material=back)

    # horizontal double slats (gloss black), across the full opening width
    # v0.3: slat pitch 53 mm (front.jpg / sline_front: 7 bars between the
    # frame and the plate, scaled with the 92 mm rings), was 33.5 mm
    for k, z in enumerate(np.arange(g_lo + 0.030, g_hi - 0.012, 0.053)):
        w = _poly_halfwidth(op.GRILLE, z * 1000) - 0.006
        if w <= 0.05:
            continue
        ys = np.linspace(-w, w, 48)
        path = []
        for y in ys:
            p, n = _face_x(surf, y, z)
            x = (p[0] if p is not None else 0.84) - 0.012
            path.append((x, y, z))
        path = np.array(path)
        # rounded wedge: front face 11 mm tall, 30 mm deep, tilted down
        prof = np.array([[-0.002, 0.0060], [0.0005, 0.0030], [0.0005, -0.0030], [-0.002, -0.0055],
                         [-0.030, -0.0085], [-0.030, -0.0005]])
        grid = np.array([[p + np.array([pr[0], 0.0, pr[1]]) for pr in prof] for p in path])
        mesh.grid_object(f"Grille_Slat_{k:02d}", grid, closed_v=True, cap_u=True,
                         collection=COL, material=black)
    # vertical rib grid behind the slats (titanium black, S line)
    for y in np.arange(-0.38, 0.381, 0.0475):
        top = g_hi - 0.010
        bot = g_lo + 0.010
        pts = []
        for z in np.linspace(bot, top, 30):
            if abs(y) > _poly_halfwidth(op.GRILLE, z * 1000) - 0.01:
                continue
            p, n = _face_x(surf, y, z)
            if p is not None:
                pts.append((p[0] - 0.048, y, z))
        if len(pts) > 3:
            mesh.sweep_profile(f"Grille_Rib_{y:+.3f}", np.array(pts),
                               np.array([[-0.002, -0.012], [0.002, -0.012], [0.002, 0.012],
                                         [-0.002, 0.012]]),
                               collection=COL, material=back, smooth=False)
    return P


def _rings(ctx, surf, centre_z=op.RINGS_Z * 1e-3):
    """Audi four rings, chrome, on the grille (ring OD 92 mm, pitch 62 mm)."""
    chrome = ctx.mat("badge_chrome")
    od, pitch, tube_w, tube_d = 0.092, 0.0615, 0.0105, 0.009
    p, n = _face_x(surf, 0.0, centre_z)
    x0 = p[0] + 0.004
    obs = []
    th = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    # rounded-rectangle tube section (flat front face, typical Audi badge)
    sec = rounded_polygon([(-tube_w / 2, -tube_d / 2), (tube_w / 2, -tube_d / 2),
                           (tube_w / 2, tube_d / 2), (-tube_w / 2, tube_d / 2)], 0.0035, 4)
    for i in range(4):
        cy = (i - 1.5) * pitch
        r = od / 2 - tube_w / 2
        path = []
        for t in np.linspace(0, 2 * math.pi, 96, endpoint=False):
            y = cy + r * math.cos(t)
            z = centre_z + r * math.sin(t)
            q, _ = _face_x(surf, y, z)
            path.append((max(q[0] if q is not None else x0, x0 - 0.01) + 0.006, y, z))
        path = np.array(path)
        # profile in (radial, x) plane
        grid = []
        for k, pnt in enumerate(path):
            radial = np.array([0.0, pnt[1] - cy, pnt[2] - centre_z])
            radial /= np.linalg.norm(radial)
            grid.append([pnt + radial * s[0] + np.array([1.0, 0, 0]) * s[1] for s in sec])
        obs.append(mesh.grid_object(f"Badge_Rings_{i}", np.array(grid), closed_u=True,
                                    closed_v=True, collection=COL, material=chrome))
    return obs


def _plate(ctx, surf, cz=op.PLATE_Z * 1e-3, front=True):
    """EU licence plate 520 x 110 mm (Spanish format) on a holder."""
    white, blue, txt = ctx.mat("plate_white"), ctx.mat("plate_blue"), ctx.mat("plate_text")
    holder = ctx.mat("black_satin")
    p, n = _face_x(surf, 0.0, cz) if front else (None, None)
    x = p[0] + 0.010 if front else 0.0
    w, h = 0.520, 0.110
    obs = []
    hold = mesh.extrude_polygon("Plate_Holder", rounded_polygon(
        [(-w / 2 - 0.008, cz - h / 2 - 0.008), (w / 2 + 0.008, cz - h / 2 - 0.008),
         (w / 2 + 0.008, cz + h / 2 + 0.008), (-w / 2 - 0.008, cz + h / 2 + 0.008)], 0.01, 4),
        0.010, plane="YZ", offset=x - 0.012, collection=COL, material=holder)
    obs.append(hold)
    plate = mesh.extrude_polygon("Plate", rounded_polygon(
        [(-w / 2, cz - h / 2), (w / 2, cz - h / 2), (w / 2, cz + h / 2), (-w / 2, cz + h / 2)],
        0.006, 4), 0.0015, plane="YZ", offset=x - 0.002, collection=COL, material=white)
    obs.append(plate)
    band = mesh.extrude_polygon("Plate_EU_Band", [(-w / 2 + 0.003, cz - h / 2 + 0.003),
                                                  (-w / 2 + 0.043, cz - h / 2 + 0.003),
                                                  (-w / 2 + 0.043, cz + h / 2 - 0.003),
                                                  (-w / 2 + 0.003, cz + h / 2 - 0.003)],
                                0.0004, plane="YZ", offset=x - 0.0005, collection=COL,
                                material=blue)
    obs.append(band)
    obs.append(_plate_text("Plate_Text", "1234 ABC", x - 0.0001, cz, txt))
    return obs


def _plate_text(name, text, x, cz, mat, height=0.075, y0=0.015):
    import bpy
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.size = height
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.0008
    ob = bpy.data.objects.new(name, cu)
    scene.link(ob, COL)
    ob.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    ob.location = (x, y0, cz)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    mo = bpy.data.objects.new(name, me)
    mo.matrix_world = ob.matrix_world
    scene.link(mo, COL)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    me.materials.append(mat)
    mesh.bake_object_transform(mo)
    return mo


def _hex_insert(name, surf, outline_mm, mirror, mat, cell=0.018, wall=0.0024,
                depth=0.012, recess=0.035):
    poly = np.asarray(outline_mm, float) * 1e-3
    if mirror:
        poly = poly * [-1, 1]

    def inside(y, z):
        c = False
        n = len(poly)
        for i in range(n):
            (y0, z0), (y1, z1) = poly[i], poly[(i + 1) % n]
            if (z0 > z) != (z1 > z):
                yi = y0 + (z - z0) * (y1 - y0) / (z1 - z0)
                if y < yi:
                    c = not c
        return c

    r = cell / 2
    dy = 1.5 * r * 2 / 1.0
    verts, faces = [], []
    ymin, ymax = poly[:, 0].min(), poly[:, 0].max()
    zmin, zmax = poly[:, 1].min(), poly[:, 1].max()
    col_i = 0
    y = ymin
    while y < ymax + r:
        z = zmin + (r * math.sqrt(3) / 2 if col_i % 2 else 0)
        while z < zmax + r:
            if inside(y, z):
                p, n = _face_x(surf, y, z)
                if p is not None:
                    x = p[0] - recess
                    ring_o = [(y + r * math.cos(a), z + r * math.sin(a))
                              for a in np.arange(6) * math.pi / 3]
                    ring_i = [(y + (r - wall) * math.cos(a), z + (r - wall) * math.sin(a))
                              for a in np.arange(6) * math.pi / 3]
                    base = len(verts)
                    for xx in (x, x - depth):
                        verts += [(xx, a, b) for a, b in ring_o]
                        verts += [(xx, a, b) for a, b in ring_i]
                    for k in range(6):
                        j = (k + 1) % 6
                        o0, i0, o1, i1 = base, base + 6, base + 12, base + 18
                        faces.append((o0 + k, o0 + j, i0 + j, i0 + k))    # front face
                        faces.append((i0 + k, i0 + j, i1 + j, i1 + k))    # inner wall
                        faces.append((o0 + j, o0 + k, o1 + k, o1 + j))    # outer wall
            z += r * math.sqrt(3)
        y += 1.5 * r
        col_i += 1
    ob = mesh.object_from_pydata(name, verts, faces, COL, mat, smooth=False)
    mesh.weld(ob, 1e-5)
    return ob


def _intakes(ctx, surf):
    black = ctx.mat("black_gloss")
    tex = ctx.mat("black_textured")
    chrome = ctx.mat("reflector")
    lens = ctx.mat("lens_clear")
    for mirror, sfx in ((False, ".L"), (True, ".R")):
        s = -1 if mirror else 1
        _hex_insert("Intake_Honeycomb" + sfx, surf, op.SIDE_INTAKE, mirror, tex)
        # back wall behind the honeycomb
        rows = []
        iz = np.asarray(op.SIDE_INTAKE, float)[:, 1] * 1e-3
        iy = np.asarray(op.SIDE_INTAKE, float)[:, 0] * 1e-3
        for z in np.linspace(iz.min() + 0.002, iz.max() - 0.002, 10):
            row = []
            for y in np.linspace(iy.min(), iy.max(), 24):
                p, n = _face_x(surf, s * y, z)
                x = (p[0] if p is not None else 0.7) - 0.06
                row.append((x, s * y, z))
            rows.append(row)
        g = np.array(rows)
        mesh.grid_object("Intake_Back" + sfx, g, collection=COL, material=tex,
                         flip=mirror)
        # S line blade (gloss black): pointed inner tip on the bumper face, then
        # across the intake rising slightly outwards (op.BLADE, S)
        B = np.asarray(op.BLADE, float) * 1e-3
        Bd = resample(catmull_rom(B, 8), 40)
        path = []
        for k, (y, z) in enumerate(Bd):
            p, n = _face_x(surf, s * y, z)
            if p is not None:
                t = k / (len(Bd) - 1)
                path.append((p[0] - (0.002 if t < 0.12 else 0.010), s * y, z, t))
        path = np.array(path)
        grid = []
        for x, y, z, t in path:
            h = 0.004 + 0.007 * min(1.0, t / 0.15)           # pointed inner tip
            dpt = 0.012 + 0.020 * min(1.0, t / 0.15)
            prof = np.array([[0.0, h * 0.6], [0.0, -h * 0.5], [-dpt, -h * 0.3], [-dpt, h * 0.9]])
            grid.append([(x + pr[0], y, z + pr[1]) for pr in prof])
        mesh.grid_object("Intake_Blade" + sfx, np.array(grid), closed_v=True, cap_u=True,
                         collection=COL, material=black)
        # fog lamp above the blade, outer part: rounded reflector + clear lens
        cy, cz = s * op.FOG_CENTRE[0] * 1e-3, op.FOG_CENTRE[1] * 1e-3
        w, h = op.FOG_SIZE[0] * 1e-3, op.FOG_SIZE[1] * 1e-3
        p, n = _face_x(surf, cy, cz)
        if p is not None:
            x = p[0] - 0.024
            outl = rounded_polygon([(cy - w / 2, cz - h / 2), (cy + w / 2, cz - h / 2),
                                    (cy + w / 2 - s * 0.010, cz + h / 2),
                                    (cy - w / 2 + s * 0.006, cz + h / 2)], 0.012, 5)
            mesh.extrude_polygon("Fog_Housing" + sfx, outl, 0.03, plane="YZ", offset=x - 0.03,
                                 collection=COL, material=ctx.mat("lamp_housing"))
            mesh.revolve("Fog_Reflector" + sfx, np.array([[0.020, 0.0], [0.016, -0.008],
                                                          [0.006, -0.018], [0.0, -0.02]]), 32,
                         axis="X", center=(x + 0.0015, cy, cz), collection=COL, material=chrome)
            mesh.extrude_polygon("Fog_Lens" + sfx, outl, 0.003, plane="YZ", offset=x + 0.002,
                                 collection=COL, material=lens)


def _side_vent(ctx, ref, surf):
    """S line 'air curtain' inset at the outer corner of the bumper: recessed
    painted panel 10 mm deep with a black slot at its lower rear end."""
    paint, black = ctx.mat("paint"), ctx.mat("black_textured")
    poly = np.asarray(op.SIDE_VENT_XZ, float) * 1e-3
    for side, sfx in ((1, ".L"), (-1, ".R")):
        y0, y1 = (0.80, 1.0) if side > 0 else (-1.0, -0.80)
        pan = st.patch(ref, poly, "XZ", y0, y1, "Bumper_SideVent" + sfx, COL, paint)
        st.offset(pan, -0.010)
        mesh.shade_smooth(pan, 40)
        # walls: outline on the skin -> 10 mm in
        dense = resample(catmull_rom(poly, 6, closed=True), 160, closed=True)
        P, N = st.clean_projection(*surf.project(dense, "XZ", side=side))
        if len(P) > 10:
            walls = np.array([P + N * 0.0005, P - N * 0.011])
            mesh.grid_object("Bumper_SideVent_Wall" + sfx, walls, closed_v=True, collection=COL,
                             material=paint, flip=side < 0)
        # black slot (lower rear corner of the inset)
        slot = np.array([(0.452, 0.286), (0.465, 0.263), (0.502, 0.268), (0.522, 0.300),
                         (0.470, 0.300)])
        sl = st.patch(ref, slot, "XZ", y0, y1, "Bumper_SideVent_Slot" + sfx, COL, black)
        st.offset(sl, -0.0105)


def _washer_sensors(ctx, surf):
    """Headlight-washer cover shut line and the outer front parking sensors."""
    gap = ctx.mat("gap")
    for side, sfx in ((1, ".L"), (-1, ".R")):
        q = np.asarray(op.WASHER_COVER_YZ, float) * 1e-3 * [side, 1]
        loop = resample(catmull_rom(rounded_polygon(q, 0.010, 5), 4, closed=True), 120, closed=True)
        P, N = st.clean_projection(*surf.project(loop, "YZ", side=1))
        if len(P) > 10:
            mesh.tube_along("Washer_Cover_Line" + sfx, np.vstack([P, P[:1]]) - 0.0 * N[0], 0.0008,
                            sides=6, collection=COL, material=gap)
        for k, (x, y, z) in enumerate(op.FRONT_SENSORS):
            p, n = _face_x(surf, side * y * 1e-3, z * 1e-3)
            if p is None:
                continue
            from mathutils import Matrix, Vector
            for nm, rr, dep, mat in (("Ring", 0.0105, 0.0006, gap), ("Head", 0.009, 0.0010,
                                                                       ctx.mat("paint"))):
                ob = mesh.revolve(f"Sensor_F{k}_{nm}{sfx}", np.array([[0.0, 0.0], [rr, 0.0],
                                                                      [rr, dep], [0.0, dep]]),
                                  32, axis="Z", collection=COL, material=mat)
                rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(n))).to_matrix().to_4x4()
                ob.data.transform(Matrix.Translation(Vector(tuple(p))) @ rot)
                ob.data.update()


def _lip(ctx, surf):
    """S line lower lip: black splitter strip following the bumper bottom."""
    mat = ctx.mat("black_satin")
    path = []
    for y in np.linspace(-0.70, 0.70, 71):
        # find lowest front point: cast at z=0.215 from the front
        p, n = _face_x(surf, y, 0.212)
        if p is not None:
            path.append((p[0] - 0.012, y, 0.205))
    path = np.array(path)
    prof = np.array([[-0.002, 0.004], [0.000, -0.004], [-0.05, -0.006], [-0.05, 0.004]])
    grid = np.array([[p + np.array([pr[0], 0, pr[1]]) for pr in prof] for p in path])
    mesh.grid_object("Front_Lip_Splitter", grid, closed_v=True, cap_u=True,
                     collection=COL, material=mat)


def _engine_bay_closure(ctx):
    """Dark radiator / bay surfaces so nothing is seen through the openings."""
    mat = ctx.mat("underbody")
    rad = mesh.extrude_polygon("Radiator_Pack", [(-0.62, 0.20), (0.62, 0.20), (0.62, 0.66),
                                                (-0.62, 0.66)], 0.06, plane="YZ",
                               offset=0.70, collection=COL, material=mat)
    # bay box: floor, sides and bulkhead (closes view through to the cabin)
    for nm, poly, plane, off, d in (
            ("Bay_Bulkhead", [(-0.75, 0.15), (0.75, 0.15), (0.75, 0.95), (-0.75, 0.95)], "YZ", -0.36, 0.01),
            ("Bay_Floor", [(-0.36, -0.60), (0.70, -0.60), (0.70, 0.60), (-0.36, 0.60)], "XY", 0.17, 0.01)):
        mesh.extrude_polygon(nm, poly, d, plane=plane, offset=off, collection=COL, material=mat)
    for s in (1, -1):
        mesh.extrude_polygon("Bay_Side" + (".L" if s > 0 else ".R"),
                             [(-0.36, 0.16), (0.55, 0.16), (0.55, 0.72), (-0.36, 0.90)], 0.01,
                             plane="XZ", offset=s * 0.60 - (0.01 if s < 0 else 0),
                             collection=COL, material=mat)
    return rad


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    _grille(ctx, surf)
    _rings(ctx, surf)
    _plate(ctx, surf)
    _intakes(ctx, surf)
    _side_vent(ctx, ref, surf)
    _washer_sensors(ctx, surf)
    _lip(ctx, surf)
    tmp = scene.temp_collection("_tmp_patch")
    for o in list(tmp.objects):
        scene.delete(o)
    # the engine bay is modelled by exterior/engine.py
