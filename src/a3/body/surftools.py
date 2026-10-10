"""Tools to derive parts from the body reference surface.

* ``patch``      : exact piece of the skin inside a prism (glass, trims, lamp
                   lenses...), obtained from a cropped copy of the skin.
* ``project``    : project 2D outlines onto the skin (ray casting) to get 3D
                   curves with surface normals, for strips and seals.
* ``offset``     : move a patch along its normals.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ..core import mesh, scene

AXIS = {"XZ": 1, "XY": 2, "YZ": 0}   # projection plane -> extrusion axis


def _crop_copy(ref, bounds_min, bounds_max, name):
    """Copy of the reference skin keeping only faces inside an AABB."""
    bm = bmesh.new()
    bm.from_mesh(ref.data)
    bmin, bmax = np.asarray(bounds_min), np.asarray(bounds_max)
    kill = []
    for f in bm.faces:
        c = np.array(f.calc_center_median())
        if np.any(c < bmin) or np.any(c > bmax):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.link(ob, scene.temp_collection("_tmp_patch"))
    for m in ref.data.materials:
        me.materials.append(m)
    return ob


def patch(ref, poly2d_m, plane, lo, hi, name, collection, material, margin=0.03,
          keep_side=None):
    """Exact skin patch inside a prism (outline in metres in `plane`)."""
    p = np.asarray(poly2d_m, float)
    ax = AXIS[plane]
    lo3 = np.full(3, -10.0)
    hi3 = np.full(3, 10.0)
    other = [i for i in range(3) if i != ax]
    lo3[other[0]], hi3[other[0]] = p[:, 0].min() - margin, p[:, 0].max() + margin
    lo3[other[1]], hi3[other[1]] = p[:, 1].min() - margin, p[:, 1].max() + margin
    lo3[ax], hi3[ax] = lo, hi
    crop = _crop_copy(ref, lo3, hi3, name)
    marker = bpy.data.materials.get("_cutter_marker") or bpy.data.materials.new("_cutter_marker")
    cutter = mesh.extrude_polygon(name + "_cut", p, hi - lo, plane=plane, offset=lo,
                                  collection=scene.temp_collection("_tmp_patch"),
                                  material=marker)
    mesh.boolean(crop, cutter, operation="INTERSECT", hole_tolerant=True,
                 transfer_materials=True)
    # remove the faces contributed by the cutter walls -> pure skin patch
    names = [m.name if m else "" for m in crop.data.materials]
    if marker.name in names:
        mi = names.index(marker.name)
        bm = bmesh.new()
        bm.from_mesh(crop.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == mi],
                         context="FACES")
        bm.to_mesh(crop.data)
        bm.free()
    crop.name = name
    for c in list(crop.users_collection):
        c.objects.unlink(crop)
    scene.link(crop, collection)
    crop.data.materials.clear()
    crop.data.materials.append(material)
    for f in crop.data.polygons:
        f.material_index = 0
    return crop


def offset(ob, d):
    """Move every vertex along its (smoothed) normal by d metres."""
    me = ob.data
    n = len(me.vertices)
    co = np.zeros(n * 3)
    me.vertices.foreach_get("co", co)
    nr = np.zeros(n * 3)
    me.vertices.foreach_get("normal", nr)
    co = co.reshape(-1, 3) + d * nr.reshape(-1, 3)
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    return ob


def boundary_band(ob, width, name, collection, material, lift=0.0):
    """Faces of `ob` within `width` of its open boundary -> new object."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bverts = [v for v in bm.verts if v.is_boundary]
    if not bverts:
        bm.free()
        return None
    bp = np.array([v.co[:] for v in bverts])
    from scipy.spatial import cKDTree
    tree = cKDTree(bp)
    kill = []
    for f in bm.faces:
        d, _ = tree.query(np.array(f.calc_center_median()))
        if d > width:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    new = bpy.data.objects.new(name, me)
    scene.link(new, collection)
    me.materials.append(material)
    if lift:
        offset(new, lift)
    mesh.shade_smooth(new, 40)
    return new


class Surface:
    """Ray-casting helper on the reference skin."""

    def __init__(self, ref):
        dg = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(ref, dg)

    def project(self, pts2d_m, plane, side=1, far=6.0):
        """Project 2D points along the plane's axis onto the skin.

        side=+1 casts from +axis towards -axis (e.g. left side for XZ)."""
        ax = AXIS[plane]
        other = [i for i in range(3) if i != ax]
        P, N = [], []
        for a, b in np.asarray(pts2d_m, float):
            o = np.zeros(3)
            o[other[0]], o[other[1]] = a, b
            o[ax] = far * side
            d = np.zeros(3)
            d[ax] = -side
            hit, nrm, idx, dist = self.bvh.ray_cast(Vector(o), Vector(d), 2 * far)
            if hit is None:
                P.append(None)
                N.append(None)
            else:
                P.append(np.array(hit[:]))
                N.append(np.array(nrm[:]))
        return P, N

    def nearest(self, p):
        loc, nrm, idx, dist = self.bvh.find_nearest(Vector(p))
        return np.array(loc[:]), np.array(nrm[:])


def clean_projection(P, N, closed=True, jump=4.0):
    """Drop misses and outliers (points far from both neighbours)."""
    idx = [i for i, p in enumerate(P) if p is not None]
    P = np.array([P[i] for i in idx])
    N = np.array([N[i] for i in idx])
    if len(P) < 4:
        return P, N
    d_prev = np.linalg.norm(P - np.roll(P, 1, 0), axis=1)
    d_next = np.linalg.norm(P - np.roll(P, -1, 0), axis=1)
    med = np.median(d_next)
    ok = ~((d_prev > jump * med) & (d_next > jump * med))
    return P[ok], N[ok]


def strip(name, pts, normals, profile, collection, material, closed=False, smooth=True):
    """Sweep a 2D profile (u along surface-perpendicular-to-curve, v along
    normal) along a 3D surface curve."""
    P = np.asarray(pts, float)
    Nn = np.asarray(normals, float)
    # drop (near) duplicate consecutive points - they make tangents vanish
    keep = [0]
    for i in range(1, len(P)):
        if np.linalg.norm(P[i] - P[keep[-1]]) > 1e-4:
            keep.append(i)
    if closed and len(keep) > 2 and np.linalg.norm(P[keep[-1]] - P[keep[0]]) < 1e-4:
        keep.pop()
    P, Nn = P[keep], Nn[keep]
    n = len(P)
    prof = np.asarray(profile, float)
    rows = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t /= np.linalg.norm(t) + 1e-12
        nn = Nn[i] - np.dot(Nn[i], t) * t
        nn /= np.linalg.norm(nn) + 1e-12
        b = np.cross(nn, t)
        rows.append(P[i] + prof[:, 0:1] * b + prof[:, 1:2] * nn)
    grid = np.array(rows)
    return mesh.grid_object(name, grid, closed_u=closed, closed_v=True,
                            collection=collection, material=material, smooth=smooth,
                            cap_u=not closed)


def patch_with_cutter(ref, cutter, name, collection, material, margin=0.03):
    """Exact skin patch inside an arbitrary closed cutter object."""
    v = np.array([c.co[:] for c in cutter.data.vertices])
    crop = _crop_copy(ref, v.min(0) - margin, v.max(0) + margin, name)
    marker = bpy.data.materials.get("_cutter_marker") or bpy.data.materials.new("_cutter_marker")
    cutter.data.materials.clear()
    cutter.data.materials.append(marker)
    mesh.boolean(crop, cutter, operation="INTERSECT", hole_tolerant=True,
                 transfer_materials=True)
    names = [m.name if m else "" for m in crop.data.materials]
    if marker.name in names:
        mi = names.index(marker.name)
        bm = bmesh.new()
        bm.from_mesh(crop.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == mi],
                         context="FACES")
        bm.to_mesh(crop.data)
        bm.free()
    for c in list(crop.users_collection):
        c.objects.unlink(crop)
    scene.link(crop, collection)
    crop.data.materials.clear()
    crop.data.materials.append(material)
    for f in crop.data.polygons:
        f.material_index = 0
    return crop
