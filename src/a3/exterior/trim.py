"""Small exterior trim: door handles, S line fender badges, windscreen
wipers and cowl panel."""
from __future__ import annotations

import math

import numpy as np

from ..body import surftools as st
from ..core import mesh
from ..core.curves import resample

COL = "Exterior/Trim"

# door handle centres (x, z) from the calibrated side photo (E), length 165 mm
HANDLES = [(-1.335, 0.770), (-2.205, 0.800)]


def _handle(ctx, surf, x0, z0, side, name):
    paint, dark = ctx.mat("paint"), ctx.mat("gap")
    L = 0.165
    pts, nrm = [], []
    for t in np.linspace(-0.5, 0.5, 24):
        x = x0 + t * L
        z = z0 + t * L * 0.10           # follows the rising belt slightly
        P, N = surf.project([(x, z)], "XZ", side=side)
        if P[0] is not None:
            pts.append(P[0])
            nrm.append(N[0])
    pts, nrm = np.array(pts), np.array(nrm)
    n = len(pts)
    prof = []
    for a in np.linspace(0, 2 * math.pi, 18, endpoint=False):
        prof.append((0.0115 * math.cos(a), 0.012 + 0.010 * math.sin(a)))
    prof = np.array(prof)
    taper = np.sin(np.linspace(0.15, math.pi - 0.15, n)) ** 0.35
    rows = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t /= np.linalg.norm(t)
        nn = nrm[i] - np.dot(nrm[i], t) * t
        nn /= np.linalg.norm(nn)
        b = np.cross(nn, t)
        rows.append(pts[i] + taper[i] * (prof[:, 0:1] * b + prof[:, 1:2] * nn))
    ob = mesh.grid_object(name, np.array(rows), closed_v=True, cap_u=True, collection=COL,
                          material=paint)
    mesh.shade_smooth(ob, 60)
    # dark recess behind the handle (finger dish)
    dish = []
    for a in np.linspace(0, 2 * math.pi, 28, endpoint=False):
        dish.append((x0 + 0.06 * math.cos(a), z0 - 0.012 + 0.022 * math.sin(a)))
    P, N = surf.project(dish, "XZ", side=side)
    P = np.array([p for p in P if p is not None])
    from ..body.openings import local_prism
    # thin dark disc slightly inside the paint (reads as shadowed dish)
    c = P.mean(0)
    verts = [tuple(p + np.array([0, -side * 0.0004, 0])) for p in P] + [tuple(c)]
    faces = [(len(P), i, (i + 1) % len(P)) for i in range(len(P))]
    mesh.object_from_pydata(name + "_Dish", verts, faces, COL, ctx.mat("black_satin"))


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
            _handle(ctx, surf, x, z, side, f"Door_Handle_{'FR'[k]}{sfx}")
        _badge(ctx, surf, -0.300, 0.795, side, "Badge_SLine" + sfx)
    _wipers(ctx, surf)
