"""Geometry helpers shared by the interior modules.

All helpers build numpy geometry and hand it to ``a3.core.mesh`` so that the
interior follows the same single creation path as the rest of the car.  The
interior adds a few higher-level primitives:

* local frames (``frame`` / ``place``): parts are modelled around their own
  origin with local +Z as their "facing" axis and then placed in the car;
* ``pillow``: quad-sphere superellipsoid (no poles, no degenerate faces) used
  for upholstery, knobs, buttons and soft shapes;
* ``rbox``: bevelled box;
* ``loft``: skin through ordered 3D sections;
* ``lathe``: surface of revolution about an arbitrary axis;
* ``Batch``: accumulates many small pieces (stitches, ticks, slats) into one
  object to keep the object count low;
* ``stitches``: real dashed-thread geometry snapped to a surface with a BVH;
* ``text_mesh``: Blender font converted to a mesh (labels on gauges, PRNDS...).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from ..core import mesh, scene
from ..core.curves import catmull_rom, resample


# ---------------------------------------------------------------------------
# frames
# ---------------------------------------------------------------------------

def _n(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-12)


def frame(origin=(0, 0, 0), z_axis=(0, 0, 1), x_axis=None):
    """4x4 local->world matrix. Local +Z maps to z_axis; local +X as close as
    possible to x_axis (default: world +Y projected, i.e. 'to the left')."""
    z = _n(z_axis)
    if x_axis is None:
        x_axis = (0, 1, 0) if abs(z[1]) < 0.9 else (1, 0, 0)
    x = np.asarray(x_axis, float)
    x = _n(x - np.dot(x, z) * z)
    y = np.cross(z, x)
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = x[i], y[i], z[i], origin[i]
    return M


def place(ob, origin=(0, 0, 0), z_axis=(0, 0, 1), x_axis=None):
    ob.data.transform(frame(origin, z_axis, x_axis))
    ob.data.update()
    return ob


def apply_np(pts, M):
    """Apply a mathutils 4x4 to an (...,3) numpy array."""
    A = np.array(M)
    p = np.asarray(pts, float)
    return p @ A[:3, :3].T + A[:3, 3]


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# ---------------------------------------------------------------------------
# object creation
# ---------------------------------------------------------------------------

def mk(name, verts, faces, col, mat, smooth=35.0):
    ob = mesh.object_from_pydata(name, verts, faces, col, mat, smooth=False)
    if smooth is None:
        mesh.shade_flat(ob)
    else:
        mesh.shade_smooth(ob, smooth)
    return ob


def finish(ob, smooth=35.0, recalc=True):
    if recalc:
        mesh.recalc_normals(ob)
    if smooth is None:
        mesh.shade_flat(ob)
    else:
        mesh.shade_smooth(ob, smooth)
    return ob


def single_material(ob, mat):
    """Reset an object to exactly one material on every face (cleans the empty
    slot an EXACT boolean with material-less cutters leaves behind)."""
    me = ob.data
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.material_index = 0
    return ob


def verts_of(ob):
    return mesh.mesh_arrays(ob)


def set_verts(ob, v):
    mesh.set_mesh_arrays(ob, v)


def deform(ob, fn):
    """Apply fn(verts Nx3)->Nx3 to an object's mesh."""
    set_verts(ob, fn(verts_of(ob)))
    return ob


def _quad_sphere_bm(n):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    if n > 1:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n - 1, use_grid_fill=True)
    return bm


_QS_CACHE = {}


def _quad_sphere(n):
    """(verts on cube surface in [-1,1]^3, faces) cached by n."""
    if n not in _QS_CACHE:
        bm = _quad_sphere_bm(n)
        v = np.array([tuple(x.co) for x in bm.verts])
        f = [tuple(x.index for x in face.verts) for face in bm.faces]
        bm.free()
        # tangent warp -> more even spacing once projected
        v = np.tan(v * (math.pi / 4) * 0.85) / math.tan(math.pi / 4 * 0.85)
        _QS_CACHE[n] = (v, f)
    return _QS_CACHE[n]


def pillow_pts(size, exp=(4.0, 4.0, 4.0), n=12):
    """Superellipsoid points |x/a|^p+|y/b|^q+|z/c|^r = 1 from a quad sphere.
    size = full extents (dx, dy, dz)."""
    v, f = _quad_sphere(n)
    p = np.asarray(exp, float)
    d = v / np.linalg.norm(v, axis=1)[:, None]
    # radial scale so that the point lies on the superellipsoid
    s = (np.abs(d[:, 0]) ** p[0] + np.abs(d[:, 1]) ** p[1] + np.abs(d[:, 2]) ** p[2])
    # iterate (non-uniform exponents): solve sum |t d_i|^p_i = 1 for t by Newton
    t = s ** (-1.0 / p.mean())
    for _ in range(12):
        g = np.sum(np.abs(t[:, None] * d) ** p, axis=1) - 1.0
        dg = np.sum(p * np.abs(d) ** p * np.abs(t[:, None]) ** (p - 1), axis=1)
        t = t - g / (dg + 1e-12)
    pts = d * t[:, None] * (np.asarray(size, float) / 2.0)
    return pts, f


def pillow(name, size, center=(0, 0, 0), exp=(4.0, 4.0, 4.0), n=12, col=None,
           mat=None, fn=None, smooth=60.0):
    """Rounded 'cushion' block. fn(local pts)->pts deforms before placement."""
    pts, f = pillow_pts(size, exp, n)
    if fn is not None:
        pts = fn(pts)
    pts = pts + np.asarray(center, float)
    ob = mk(name, pts, f, col, mat, smooth)
    return ob


def rbox(name, size, center=(0, 0, 0), radius=0.002, segments=2, col=None, mat=None,
         smooth=40.0):
    """Box with all edges bevelled."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.link(ob, col)
    if radius > 0:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = min(radius, 0.49 * min(size))
        m.segments = segments
        m.limit_method = "NONE"
        mesh.apply_modifiers(ob)
    if mat is not None:
        mesh.assign_material(ob, mat)
    mesh.shade_smooth(ob, smooth)
    return ob


def prism(name, poly2d, z0, z1, col=None, mat=None, bevel=0.0, segs=2, smooth=40.0):
    """Extrude a 2D polygon (local XY) between z0 and z1 (local Z)."""
    ob = mesh.extrude_polygon(name, poly2d, z1 - z0, plane="XY", offset=z0, collection=col,
                              material=mat, smooth=False)
    if bevel > 0:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = segs
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(30)
        mesh.apply_modifiers(ob)
    mesh.shade_smooth(ob, smooth)
    return ob


def loft(name, sections, col=None, mat=None, closed=False, cap=False, flip=False,
         smooth=40.0):
    """Skin ordered sections (list of (m,3) arrays, same m)."""
    pts = np.stack([np.asarray(s, float) for s in sections])
    ob = mesh.grid_object(name, pts, closed_u=False, closed_v=closed, flip=flip,
                          collection=col, material=mat, smooth=False, cap_u=cap and closed)
    mesh.shade_smooth(ob, smooth)
    return ob


def lathe(name, profile_rz, origin=(0, 0, 0), axis=(0, 0, 1), x_axis=None, segments=48,
          col=None, mat=None, smooth=40.0, angle=2 * math.pi, start=0.0):
    """Revolve (r, z) profile about local Z then place along axis."""
    prof = np.asarray(profile_rz, float)
    ob = mesh.revolve(name, prof, segments=segments, axis="Z", collection=col,
                      material=mat, smooth=False, angle=angle, start=start)
    _fix_poles(ob)
    place(ob, origin, axis, x_axis)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, smooth)
    return ob


def _fix_poles(ob):
    """Remove degenerate faces produced by r=0 profile points."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def tube(name, path, radius, sides=12, col=None, mat=None, closed=False, smooth=50.0,
         up=(0, 0, 1)):
    ob = mesh.tube_along(name, np.asarray(path, float), radius, sides=sides, collection=col,
                         material=mat, closed=closed, smooth=False, up=up)
    mesh.shade_smooth(ob, smooth)
    return ob


def sweep(name, path, profile2d, col=None, mat=None, closed_path=False, cap=True,
          smooth=40.0, up=(0, 0, 1), frames=None, scale=None):
    ob = mesh.sweep_profile(name, np.asarray(path, float), profile2d, collection=col,
                            material=mat, closed_path=closed_path, cap=cap, smooth=False,
                            up=up, frames=frames, scale=scale)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, smooth)
    return ob


def spline(points, n=64, closed=False):
    """Smooth curve through control points resampled uniformly to n points."""
    c = catmull_rom(np.asarray(points, float), n_per_seg=12, closed=closed)
    return resample(c, n, closed=closed)


def circle(r, n=48, center=(0, 0)):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([center[0] + r * np.cos(t), center[1] + r * np.sin(t)], 1)


def rrect(w, h, r, n_arc=6, center=(0, 0)):
    from ..core.curves import rounded_polygon
    x0, y0 = center[0] - w / 2, center[1] - h / 2
    x1, y1 = center[0] + w / 2, center[1] + h / 2
    return rounded_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], r, n_arc)


def offset_curve_3d(path, normals, d):
    """Offset a 3D path within the surface (perpendicular to tangent & normal)."""
    path = np.asarray(path, float)
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None] + 1e-12
    side = np.cross(normals, t)
    side /= np.linalg.norm(side, axis=1)[:, None] + 1e-12
    return path + side * d


# ---------------------------------------------------------------------------
# batch of many small pieces into one object
# ---------------------------------------------------------------------------

class Batch:
    def __init__(self, name, col, mat, smooth=35.0):
        self.name, self.col, self.mat, self.smooth = name, col, mat, smooth
        self.v = []
        self.f = []
        self.nv = 0

    def add(self, verts, faces):
        verts = np.asarray(verts, float).reshape(-1, 3)
        self.v.append(verts)
        self.f.extend(tuple(i + self.nv for i in fc) for fc in faces)
        self.nv += len(verts)

    def add_object(self, ob):
        """Absorb (and delete) a temporary object's mesh."""
        v = verts_of(ob)
        f = [tuple(p.vertices) for p in ob.data.polygons]
        self.add(v, f)
        scene.delete(ob)

    def build(self):
        if not self.v:
            return None
        ob = mk(self.name, np.vstack(self.v), self.f, self.col, self.mat, self.smooth)
        return ob


def box_verts(c, ax, ay, az):
    """8 verts + 6 quads of an oriented box: centre c, half-axis vectors."""
    c, ax, ay, az = (np.asarray(a, float) for a in (c, ax, ay, az))
    s = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                  [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    v = c + s[:, :1] * ax + s[:, 1:2] * ay + s[:, 2:3] * az
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


# ---------------------------------------------------------------------------
# surface snapping & stitching
# ---------------------------------------------------------------------------

class Surface:
    """BVH over one or several objects' world-space meshes for snapping."""

    def __init__(self, *obs):
        vs, ps, off = [], [], 0
        for ob in obs:
            v = verts_of(ob)
            M = np.array(ob.matrix_world)
            v = v @ M[:3, :3].T + M[:3, 3]
            vs.append(v)
            ps.extend([tuple(i + off for i in p.vertices) for p in ob.data.polygons])
            off += len(v)
        self.v = np.vstack(vs)
        self.bvh = BVHTree.FromPolygons([tuple(x) for x in self.v], ps, epsilon=0.0)

    def snap(self, pts, hint=None):
        """Nearest surface points + normals. If hint given (vector), normals are
        flipped to point to the same side as hint."""
        P, N = [], []
        for p in np.asarray(pts, float):
            loc, nrm, _, _ = self.bvh.find_nearest(Vector(p))
            if loc is None:
                P.append(p)
                N.append((0, 0, 1))
                continue
            P.append(tuple(loc))
            N.append(tuple(nrm))
        P, N = np.array(P), np.array(N)
        if hint is not None:
            h = np.asarray(hint, float)
            if h.ndim == 1:
                h = np.broadcast_to(h, N.shape)
            flip = np.sum(N * h, axis=1) < 0
            N[flip] *= -1
        return P, N

    def ray(self, origin, direction):
        loc, nrm, _, d = self.bvh.ray_cast(Vector(origin), Vector(direction))
        return (None, None) if loc is None else (np.array(loc), np.array(nrm))


def stitch_geometry(path, normals, pitch=0.0042, length=0.0030, width=0.0009,
                    height=0.0005, lift=0.0002, lateral=0.0, yaw=0.0):
    """Dashed thread: one small rounded-top lozenge per stitch along path.
    yaw (rad) slants each stitch in the surface plane (cross/baseball stitch)."""
    path = np.asarray(path, float)
    normals = np.asarray(normals, float)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < pitch:
        return np.zeros((0, 3)), []
    ts = np.arange(pitch / 2, s[-1] - pitch / 4, pitch)
    P = np.stack([np.interp(ts, s, path[:, k]) for k in range(3)], 1)
    N = np.stack([np.interp(ts, s, normals[:, k]) for k in range(3)], 1)
    N /= np.linalg.norm(N, axis=1)[:, None] + 1e-12
    T = np.stack([np.interp(ts + 1e-4, s, path[:, k]) - np.interp(ts - 1e-4, s, path[:, k])
                  for k in range(3)], 1)
    T -= np.sum(T * N, 1)[:, None] * N
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
    B = np.cross(N, T)
    P = P + B * lateral + N * lift
    if yaw:
        c, sn = math.cos(yaw), math.sin(yaw)
        T, B = T * c + B * sn, B * c - T * sn
    # 6-vertex lozenge: ends pinched, raised ridge -> 8 tris per stitch
    hl, hw = length / 2, width / 2
    loc = np.array([[-hl, 0, 0], [0, -hw, 0], [hl, 0, 0], [0, hw, 0],
                    [-hl * 0.6, 0, height], [hl * 0.6, 0, height]])
    V = (P[:, None, :] + loc[None, :, 0:1] * T[:, None, :] + loc[None, :, 1:2] * B[:, None, :]
         + loc[None, :, 2:3] * N[:, None, :])
    base = [(4, 1, 0), (4, 5, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (4, 0, 3), (0, 1, 2, 3)]
    faces = []
    for i in range(len(P)):
        o = i * 6
        faces.extend(tuple(o + k for k in fc) for fc in base[:6])
    return V.reshape(-1, 3), faces


def add_stitch(batch, path, normals, **kw):
    v, f = stitch_geometry(path, normals, **kw)
    if len(v):
        batch.add(v, f)


def stitch_on(batch, surface, pts, hint, lateral=(0.0,), lift=0.00025, n=None, **kw):
    """Snap a control polyline to a Surface and add one or more stitch rows
    (lateral offsets in m) to batch."""
    pts = np.asarray(pts, float)
    if n is None:
        L = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        n = max(8, int(L / 0.003))
    path = resample(pts, n) if len(pts) != n else pts
    P, N = surface.snap(path, hint)
    for d in lateral:
        if d:
            Q = offset_curve_3d(P, N, d)
            Q, N2 = surface.snap(Q, hint)
        else:
            Q, N2 = P, N
        add_stitch(batch, Q, N2, lift=lift, **kw)


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

def text_mesh(name, text, size=0.01, col=None, mat=None, extrude=0.0002,
              align_x="CENTER", align_y="CENTER", bold=False, spacing=1.0):
    """Font -> mesh in local XY plane (facing +Z)."""
    cu = bpy.data.curves.new(name + "_txt", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align_x
    cu.align_y = align_y
    cu.space_character = spacing
    cu.resolution_u = 3
    cu.fill_mode = "BOTH"
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    scene.link(tmp, scene.temp_collection())
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.name = name
    ob = bpy.data.objects.new(name, me)
    scene.link(ob, col)
    if mat is not None:
        mesh.assign_material(ob, mat)
    if extrude > 0:
        # shift so the back face lies on z=0
        me.transform(Matrix.Translation((0, 0, extrude)))
    mesh.shade_flat(ob)
    return ob


def cleanup_temp():
    col = bpy.data.collections.get("_tmp_cutters")
    if col is not None and not col.objects:
        bpy.data.collections.remove(col)
