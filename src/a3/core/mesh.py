"""Low-level procedural mesh construction helpers.

Every builder returns a ``bpy.types.Object`` already linked to the requested
collection. Geometry is generated with numpy and pushed into Blender through
``Mesh.from_pydata`` so that all modules share one consistent, testable path.

Conventions (ISO 8855 vehicle axes):
    +X forward, +Y left, +Z up, metres, origin on the ground plane at the
    centre of the front axle.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import scene as sc


# --------------------------------------------------------------------------
# Object creation
# --------------------------------------------------------------------------

def object_from_pydata(name, verts, faces, collection=None, material=None,
                       smooth=True, edges=()):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], list(edges),
                   [tuple(int(i) for i in f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.link(ob, collection)
    if material is not None:
        assign_material(ob, material)
    if smooth:
        shade_smooth(ob)
    return ob


def shade_smooth(ob, angle_deg: float | None = 35.0):
    """Smooth shading. If angle given, edges sharper than it stay sharp."""
    me = ob.data
    if not me.polygons:
        return ob
    me.shade_smooth()
    if angle_deg is not None:
        try:
            me.set_sharp_from_angle(angle=math.radians(angle_deg))
        except AttributeError:  # older API
            pass
    return ob


def shade_flat(ob):
    ob.data.shade_flat()
    return ob


def assign_material(ob, material, slot_only=False):
    if material is None:
        return
    mats = ob.data.materials
    if material.name not in [m.name for m in mats if m]:
        mats.append(material)
    if not slot_only:
        idx = [m.name for m in mats].index(material.name)
        for p in ob.data.polygons:
            p.material_index = idx


def material_index(ob, material):
    mats = ob.data.materials
    names = [m.name if m else None for m in mats]
    if material.name not in names:
        mats.append(material)
        names.append(material.name)
    return names.index(material.name)


# --------------------------------------------------------------------------
# Grid / loft
# --------------------------------------------------------------------------

def grid_faces(nu: int, nv: int, closed_u=False, closed_v=False, flip=False):
    """Quad faces for a (nu x nv) vertex grid stored row-major (u major)."""
    faces = []
    u_range = nu if closed_u else nu - 1
    v_range = nv if closed_v else nv - 1
    for i in range(u_range):
        i2 = (i + 1) % nu
        for j in range(v_range):
            j2 = (j + 1) % nv
            a, b, c, d = i * nv + j, i2 * nv + j, i2 * nv + j2, i * nv + j2
            faces.append((a, d, c, b) if flip else (a, b, c, d))
    return faces


def grid_object(name, pts: np.ndarray, closed_u=False, closed_v=False,
                flip=False, collection=None, material=None, smooth=True,
                cap_u=False):
    """pts shape (nu, nv, 3). Optionally caps the two u ends (n-gon fans)."""
    nu, nv, _ = pts.shape
    verts = pts.reshape(-1, 3)
    faces = grid_faces(nu, nv, closed_u, closed_v, flip)
    if cap_u and closed_v:
        first = list(range(0, nv))
        last = list(range((nu - 1) * nv, nu * nv))
        faces.append(tuple(reversed(first)) if not flip else tuple(first))
        faces.append(tuple(last) if not flip else tuple(reversed(last)))
    return object_from_pydata(name, verts, faces, collection, material, smooth)


def revolve(name, profile_rz: np.ndarray, segments=96, axis="Y", center=(0, 0, 0),
            collection=None, material=None, smooth=True, cap=False, flip=False,
            angle=2 * math.pi, start=0.0):
    """Surface of revolution of a (radius, axial) profile.

    axis "Y" means the wheel axis (lateral). The profile is sampled as
    (r, a) pairs with ``a`` measured along the axis.
    """
    prof = np.asarray(profile_rz, float)
    closed = abs(angle - 2 * math.pi) < 1e-9
    n = segments if closed else segments + 1
    th = start + np.arange(n) * (angle / segments)
    pts = np.zeros((n, len(prof), 3))
    r, a = prof[:, 0], prof[:, 1]
    c, s = np.cos(th)[:, None], np.sin(th)[:, None]
    if axis == "Y":
        pts[..., 0] = r[None] * c
        pts[..., 2] = r[None] * s
        pts[..., 1] = a[None]
    elif axis == "X":
        pts[..., 1] = r[None] * c
        pts[..., 2] = r[None] * s
        pts[..., 0] = a[None]
    else:
        pts[..., 0] = r[None] * c
        pts[..., 1] = r[None] * s
        pts[..., 2] = a[None]
    pts += np.asarray(center)
    return grid_object(name, pts, closed_u=closed, closed_v=False, flip=flip,
                       collection=collection, material=material, smooth=smooth)


def polyline_offset_2d(pts: np.ndarray, d: float, closed=True) -> np.ndarray:
    """Offset a 2D polyline by distance d along its left normal (miter)."""
    p = np.asarray(pts, float)
    n = len(p)
    out = np.zeros_like(p)
    for i in range(n):
        if closed:
            a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        else:
            a = p[max(i - 1, 0)]
            b = p[i]
            c = p[min(i + 1, n - 1)]
        t1 = b - a
        t2 = c - b
        if np.linalg.norm(t1) < 1e-12:
            t1 = t2
        if np.linalg.norm(t2) < 1e-12:
            t2 = t1
        t1 = t1 / (np.linalg.norm(t1) + 1e-12)
        t2 = t2 / (np.linalg.norm(t2) + 1e-12)
        n1 = np.array([-t1[1], t1[0]])
        n2 = np.array([-t2[1], t2[0]])
        m = n1 + n2
        ml = np.linalg.norm(m)
        if ml < 1e-9:
            m = n1
        else:
            m = m / ml
        cosang = max(np.dot(m, n1), 0.3)
        out[i] = b + m * d / cosang
    return out


def polygon_area(pts):
    p = np.asarray(pts)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def extrude_polygon(name, poly2d, depth, plane="XZ", offset=0.0, collection=None,
                    material=None, smooth=False, bevel=0.0, bevel_segments=2):
    """Prism from a 2D polygon. plane XZ -> extruded along Y from offset to
    offset+depth. plane XY -> along Z. plane YZ -> along X."""
    p = np.asarray(poly2d, float)
    if polygon_area(p) < 0:
        p = p[::-1]
    n = len(p)
    verts = []
    for k, w in enumerate((offset, offset + depth)):
        for (a, b) in p:
            if plane == "XZ":
                verts.append((a, w, b))
            elif plane == "XY":
                verts.append((a, b, w))
            else:  # YZ
                verts.append((w, a, b))
    faces = []
    bottom = list(range(n))[::-1]
    top = list(range(n, 2 * n))
    # orientation depends on plane handedness; recalc normals afterwards
    faces.append(tuple(bottom))
    faces.append(tuple(top))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    ob = object_from_pydata(name, verts, faces, collection, material, smooth)
    recalc_normals(ob)
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = bevel_segments
        mod.limit_method = "ANGLE"
        apply_modifiers(ob)
    return ob


def tube_along(name, path: np.ndarray, radius: float | Sequence[float], sides=12,
               collection=None, material=None, closed=False, cap=True, smooth=True,
               up=(0, 0, 1)):
    """Circular tube swept along a 3D polyline using parallel transport."""
    path = np.asarray(path, float)
    n = len(path)
    radii = np.full(n, radius) if np.isscalar(radius) else np.asarray(radius)
    frames = parallel_transport_frames(path, closed, up)
    th = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    pts = np.zeros((n, sides, 3))
    for i in range(n):
        t, nn, bb = frames[i]
        pts[i] = path[i] + radii[i] * (np.cos(th)[:, None] * nn + np.sin(th)[:, None] * bb)
    return grid_object(name, pts, closed_u=closed, closed_v=True,
                       collection=collection, material=material, smooth=smooth,
                       cap_u=cap and not closed)


def sweep_profile(name, path: np.ndarray, profile2d: np.ndarray, collection=None,
                  material=None, closed_path=False, closed_profile=True, cap=True,
                  smooth=True, up=(0, 0, 1), scale=None, frames=None):
    """Sweep an arbitrary 2D profile (n x 2, local N/B coords) along a path."""
    path = np.asarray(path, float)
    prof = np.asarray(profile2d, float)
    if frames is None:
        frames = parallel_transport_frames(path, closed_path, up)
    n = len(path)
    pts = np.zeros((n, len(prof), 3))
    for i in range(n):
        t, nn, bb = frames[i]
        s = 1.0 if scale is None else scale[i]
        pts[i] = path[i] + s * (prof[:, 0:1] * nn + prof[:, 1:2] * bb)
    return grid_object(name, pts, closed_u=closed_path, closed_v=closed_profile,
                       collection=collection, material=material, smooth=smooth,
                       cap_u=cap and closed_profile and not closed_path)


def parallel_transport_frames(path, closed=False, up=(0, 0, 1)):
    path = np.asarray(path, float)
    n = len(path)
    tang = np.zeros_like(path)
    for i in range(n):
        if closed:
            d = path[(i + 1) % n] - path[i - 1]
        else:
            d = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
        tang[i] = d / (np.linalg.norm(d) + 1e-12)
    upv = np.asarray(up, float)
    if abs(np.dot(upv, tang[0])) > 0.95:
        upv = np.array([1.0, 0, 0]) if abs(tang[0][0]) < 0.9 else np.array([0, 1.0, 0])
    nrm = np.cross(upv, tang[0])
    nrm /= np.linalg.norm(nrm)
    frames = []
    for i in range(n):
        t = tang[i]
        nrm = nrm - np.dot(nrm, t) * t
        nrm /= (np.linalg.norm(nrm) + 1e-12)
        b = np.cross(t, nrm)
        frames.append((t, nrm.copy(), b))
    return frames


# --------------------------------------------------------------------------
# Modifiers & editing
# --------------------------------------------------------------------------

def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ob_eval = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ob_eval, preserve_all_data_layers=True,
                                         depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def add_bevel(ob, width, segments=3, angle_deg=30, apply=True, harden=False):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle_deg)
    m.harden_normals = harden
    if apply:
        apply_modifiers(ob)
    return ob


def add_subsurf(ob, levels=2, apply=True):
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    if apply:
        apply_modifiers(ob)
    return ob


def solidify(ob, thickness, offset=-1.0, apply=True, even=True, rim=True, material_offset=0):
    m = ob.modifiers.new("solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = even
    m.use_rim = rim
    m.material_offset = material_offset
    if apply:
        apply_modifiers(ob)
    return ob


def boolean(ob, cutter, operation="DIFFERENCE", apply=True, solver="EXACT",
            delete_cutter=True, hole_tolerant=False, transfer_materials=False,
            self_intersect=False):
    m = ob.modifiers.new("bool", "BOOLEAN")
    m.operation = operation
    m.solver = solver
    if solver == "FLOAT":
        m.double_threshold = 1e-6
    if solver == "EXACT":
        m.use_hole_tolerant = hole_tolerant
        m.use_self = self_intersect
        if transfer_materials:
            m.material_mode = "TRANSFER"
    if isinstance(cutter, bpy.types.Collection):
        m.operand_type = "COLLECTION"
        m.collection = cutter
    else:
        m.object = cutter
    if apply:
        apply_modifiers(ob)
        if delete_cutter:
            if isinstance(cutter, bpy.types.Collection):
                for o in list(cutter.objects):
                    sc.delete(o)
            else:
                sc.delete(cutter)
    return ob


def recalc_normals(ob, inside=False):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if inside:
        for f in bm.faces:
            f.normal_flip()
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def transform(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), apply=True):
    """Bake a transform into the mesh data (rotation in radians, XYZ euler)."""
    from mathutils import Euler
    mat = (Matrix.Translation(Vector(loc)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
           @ Matrix.Diagonal(Vector((*scale, 1.0))))
    if apply:
        ob.data.transform(mat)
        if any(s < 0 for s in scale) and (scale[0] * scale[1] * scale[2]) < 0:
            ob.data.flip_normals()
        ob.data.update()
    else:
        ob.matrix_world = mat @ ob.matrix_world
    return ob


def mirror_copy_y(ob, name=None, collection=None):
    """Duplicate an object mirrored across the vehicle centre plane (Y=0)."""
    me = ob.data.copy()
    new = bpy.data.objects.new(name or ob.name.replace(".L", ".R").replace("_L", "_R"), me)
    sc.link(new, collection or ob.users_collection[0])
    me.transform(Matrix.Diagonal(Vector((1, -1, 1, 1))))
    me.flip_normals()
    me.update()
    new.matrix_world = ob.matrix_world.copy()
    return new


def join(objects: Iterable, name=None):
    objs = [o for o in objects if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        if name:
            objs[0].name = name
        return objs[0]
    target = objs[0]
    with bpy.context.temp_override(active_object=target, selected_editable_objects=objs,
                                   selected_objects=objs):
        bpy.ops.object.join()
    if name:
        target.name = name
        target.data.name = name
    return target


def bake_object_transform(ob):
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


def weld(ob, dist=1e-5):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def mesh_arrays(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    return v.reshape(-1, 3)


def set_mesh_arrays(ob, verts):
    ob.data.vertices.foreach_set("co", np.asarray(verts, float).ravel())
    ob.data.update()
