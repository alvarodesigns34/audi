"""Small exterior trim: door handles, S line fender badges, windscreen
wipers and cowl panel."""
from __future__ import annotations

import math

import numpy as np

from ..body import surftools as st
from ..core import mesh
from ..core.curves import resample

COL = "Exterior/Trim"

# door handle centres (x, z): v0.3 triangulated side + sline_rear (+-3 px):
# front (-1.390, 0.780), rear (-2.264, 0.805) - v0.2 had them 55-60 mm too far
# forward.  Grip length 190 mm, height 24 mm (E from the photos).
HANDLES = [(-1.390, 0.780), (-2.264, 0.805)]


def _handle(ctx, surf, x0, z0, side, name, lock=False):
    """8V door handle: body-coloured grip over a pressed recess in the door
    skin (dark shadowed dish), lock cylinder cap at the rear end of the
    driver's handle."""
    paint, dark = ctx.mat("paint"), ctx.mat("gap")
    L = 0.190
    pts, nrm = [], []
    for t in np.linspace(-0.5, 0.5, 32):
        x = x0 + t * L
        z = z0 + t * L * 0.06            # follows the rising belt slightly
        P, N = surf.project([(x, z)], "XZ", side=side)
        if P[0] is not None:
            pts.append(P[0])
            nrm.append(N[0])
    pts, nrm = np.array(pts), np.array(nrm)
    n = len(pts)
    prof = []
    for a in np.linspace(0, 2 * math.pi, 20, endpoint=False):
        # flat-faced oval: 24 mm tall, standing 21 mm off the skin
        c, sn = math.cos(a), math.sin(a)
        prof.append((0.012 * np.sign(c) * abs(c) ** 0.7, 0.0115 + 0.0095 * sn))
    prof = np.array(prof)
    u = np.linspace(0, 1, n)
    taper = np.minimum(1.0, np.minimum(u, 1 - u) / 0.12) ** 0.5 * 0.85 + 0.15
    lift = np.where(u > 0.8, 1.0, np.where(u < 0.2, 0.75 + 1.25 * u, 1.0))
    rows = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t /= np.linalg.norm(t)
        nn = nrm[i] - np.dot(nrm[i], t) * t
        nn /= np.linalg.norm(nn)
        b = np.cross(nn, t)
        rows.append(pts[i] + taper[i] * prof[:, 0:1] * b + (prof[:, 1:2] * lift[i]) * nn)
    ob = mesh.grid_object(name, np.array(rows), closed_v=True, cap_u=True, collection=COL,
                          material=paint)
    mesh.shade_smooth(ob, 60)
    # finger recess (dish) filling the elliptical hole cut in the door skin
    # (openings.HANDLE_RECESSES), 7 mm deep
    from ..body import openings as op
    k = 0 if x0 > -1.8 else 1
    rx, rz = (v * 1e-3 for v in op.HANDLE_RECESSES[k])
    a, b = (v * 1e-3 for v in op.HANDLE_RECESS_AXES)
    dish = []
    for r in np.linspace(0.0, 1.0, 9):
        ring = []
        for th in np.linspace(0, 2 * math.pi, 48, endpoint=False):
            qx, qz = rx + a * r * math.cos(th), rz + b * r * math.sin(th)
            P, N = surf.project([(qx, qz)], "XZ", side=side)
            if P[0] is None:
                continue
            ring.append(P[0] - N[0] * 0.007 * (1 - r ** 2) ** 0.8)
        dish.append(ring)
    d = mesh.grid_object(name.replace("Door_Handle_", "Door_Handle_Recess_"), np.array(dish),
                         closed_v=True, collection=COL, material=paint, flip=side > 0)
    mesh.shade_smooth(d, 60)
    if lock:
        q = pts[int(n * 0.9)] + nrm[int(n * 0.9)] * 0.0215
        cap = mesh.revolve(name.replace("Door_Handle_", "Door_Handle_LockCap_"), np.array([[0.0, 0.0], [0.009, 0.0], [0.0085, 0.002],
                                                        [0.0, 0.0025]]), 24, axis="Z",
                           collection=COL, material=paint)
        from mathutils import Matrix, Vector
        rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(nrm[int(n * 0.9)]))).to_matrix().to_4x4()
        cap.data.transform(Matrix.Translation(Vector(tuple(q))) @ rot)
        cap.data.update()


def _badge(ctx, surf, x, z, side, name):
    """S line fender badge: small black/silver plaque with red 'S'."""
    P, N = surf.project([(x, z)], "XZ", side=side)
    if P[0] is None:
        return
    p, n = P[0], N[0]
    w, h = 0.052, 0.013
    t = np.array([1.0, 0, 0])
    t -= np.dot(t, n) * n
    t /= np.linalg.norm(t)
    b = np.cross(n, t)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    for nm, (mat, dz, scale) in (("_Base", ("black_gloss", 0.0010, 1.0)),
                                 ("_S", ("badge_red", 0.0016, 0.22))):
        verts = []
        for lift in (0.0, dz):
            for u, v in corners:
                if nm == "_S":
                    u = u * scale - w * 0.36
                verts.append(tuple(p + n * lift + t * u + b * v))
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        ob = mesh.object_from_pydata(name + nm, verts, faces, COL, ctx.mat(mat), smooth=False)
        mesh.recalc_normals(ob)


def _wipers(ctx, surf):
    black = ctx.mat("black_satin")
    # parked along the lower edge of the screen (LHD: driver blade from left)
    for nm, y0, y1, L in (("Wiper_Driver", 0.10, 0.62, 0.65), ("Wiper_Passenger", -0.58, 0.02, 0.55)):
        pts = []
        for y in np.linspace(y0, y1, 30):
            P, N = surf.project([(-0.40 - 0.04 * (y - y0), y)], "XY", side=1)
            if P[0] is not None:
                pts.append(P[0] + N[0] * 0.016)
        if len(pts) > 3:
            mesh.sweep_profile(nm, resample(np.array(pts), 40),
                               np.array([[-0.007, -0.010], [0.007, -0.010], [0.006, 0.006],
                                         [-0.006, 0.006]]), collection=COL, material=black)


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    for side, sfx in ((1, ".L"), (-1, ".R")):
        for k, (x, z) in enumerate(HANDLES):
            _handle(ctx, surf, x, z, side, f"Door_Handle_{'FR'[k]}{sfx}",
                    lock=(k == 0 and side > 0))
        _badge(ctx, surf, -0.300, 0.795, side, "Badge_SLine" + sfx)
    _wipers(ctx, surf)
