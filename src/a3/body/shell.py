"""Body-in-white outer skin (painted shell) of the A3 Sportback 8V."""
from __future__ import annotations

import time

import bmesh
import bpy
import numpy as np

import os

from ..core import cache, mesh, scene
from ..spec import m as mm
from . import openings, surface

SHELL_THICKNESS = 0.0025   # visual sheet + sealer thickness at cut edges
BOOL_SOLVER = "EXACT"
DEBUG = False


def skin_object(name="Body_Skin", spacing=0.012, collection="Exterior/Body",
                material=None):
    bl = surface.BodyLines()
    grid, xs = surface.skin_grid(bl, spacing)
    nu, nv, _ = grid.shape
    right = grid.copy()
    right[..., 1] *= -1
    verts = np.vstack([grid.reshape(-1, 3), right.reshape(-1, 3)])
    faces = mesh.grid_faces(nu, nv, flip=False)
    off = nu * nv
    faces += [tuple(i + off for i in f[::-1]) for f in mesh.grid_faces(nu, nv)]
    ob = mesh.object_from_pydata(name, verts, faces, collection, material, smooth=False)
    # merge the centre-line seams and the collapsed pole rows
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    mesh.shade_smooth(ob, 28)
    return ob, bl, grid


def _outside_count(ob, lo, hi):
    """Painted skin faces (material slot 0) outside the box [lo, hi].  Faces
    contributed by earlier cutters (dark slot) are ignored: walls of a cutter
    can legitimately be removed by a later cut."""
    n = len(ob.data.polygons)
    C = np.zeros(n * 3)
    ob.data.polygons.foreach_get("center", C)
    C = C.reshape(-1, 3)
    M = np.zeros(n, dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", M)
    out = np.any(C < lo, 1) | np.any(C > hi, 1)
    return int((out & (M == 0)).sum())


def _stray_walls(ob, bvh, tol=0.006):
    """Fraction of non-paint faces (cutter walls) farther than tol from the
    reference skin: a correct cut only adds walls inside the sheet thickness;
    a failed one keeps (unions) the cutter."""
    from mathutils import Vector
    n = len(ob.data.polygons)
    M = np.zeros(n, dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", M)
    C = np.zeros(n * 3)
    ob.data.polygons.foreach_get("center", C)
    C = C.reshape(-1, 3)[M != 0]
    if len(C) == 0:
        return 0
    far = 0
    for c in C[:: max(1, len(C) // 4000)]:
        loc, nrm, idx, d = bvh.find_nearest(Vector(c))
        if loc is None or d > tol:
            far += 1
    return far


def _inside_count(ob, cbvh, lo, hi, limit=3000):
    """Painted faces whose centre lies inside the cutter (ray parity test):
    after a correct cut there are none left."""
    from mathutils import Vector
    n = len(ob.data.polygons)
    M = np.zeros(n, dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", M)
    C = np.zeros(n * 3)
    ob.data.polygons.foreach_get("center", C)
    C = C.reshape(-1, 3)
    sel = C[(M == 0) & np.all(C > lo, 1) & np.all(C < hi, 1)]
    if len(sel) > limit:
        sel = sel[:: len(sel) // limit + 1]
    inside = 0
    d = Vector((0.5773, 0.5774, 0.5774))
    for c in sel:
        o = Vector(c)
        k = 0
        for _ in range(64):
            hit = cbvh.ray_cast(o, d)
            if hit[0] is None:
                break
            k += 1
            o = hit[0] + d * 1e-6
        inside += k % 2
    return inside


def _restore_outside(me_before, ob_after, lo, hi):
    """Append to ob_after the faces of me_before that lie outside [lo, hi] and
    are missing in ob_after.  Returns the number of faces restored."""
    import bmesh
    from scipy.spatial import cKDTree
    n0 = len(me_before.polygons)
    C0 = np.zeros(n0 * 3)
    me_before.polygons.foreach_get("center", C0)
    C0 = C0.reshape(-1, 3)
    n1 = len(ob_after.data.polygons)
    C1 = np.zeros(n1 * 3)
    ob_after.data.polygons.foreach_get("center", C1)
    C1 = C1.reshape(-1, 3)
    d, _ = cKDTree(C1).query(C0)
    out = np.any(C0 < lo, 1) | np.any(C0 > hi, 1)
    keep = set(np.nonzero(out & (d > 1e-6))[0].tolist())
    if not keep:
        return 0
    bm = bmesh.new()
    bm.from_mesh(me_before)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for i, f in enumerate(bm.faces) if i not in keep],
                     context="FACES")
    tmp = bpy.data.meshes.new("_restore")
    bm.to_mesh(tmp)
    bm.free()
    bm2 = bmesh.new()
    bm2.from_mesh(ob_after.data)
    bm2.from_mesh(tmp)
    bmesh.ops.remove_doubles(bm2, verts=bm2.verts, dist=1e-6)
    bm2.to_mesh(ob_after.data)
    bm2.free()
    bpy.data.meshes.remove(tmp)
    return len(keep)


def _report_lost(me_before, ob_after, lo, hi):
    from scipy.spatial import cKDTree
    def cen(me):
        n = len(me.polygons)
        C = np.zeros(n * 3)
        me.polygons.foreach_get("center", C)
        M = np.zeros(n, dtype=np.int32)
        me.polygons.foreach_get("material_index", M)
        return C.reshape(-1, 3)[M == 0]
    C0, C1 = cen(me_before), cen(ob_after.data)
    d, _ = cKDTree(C1).query(C0)
    L = C0[(d > 1e-5) & (np.any(C0 < lo, 1) | np.any(C0 > hi, 1))]
    if len(L):
        print("      lost bbox", L.min(0).round(3), L.max(0).round(3), "n", len(L),
              "median", np.median(L, 0).round(3))


def guarded_cut(skin, cutter, margin=0.006, bvh=None):
    """Boolean difference that verifies the result: no face of the shell
    outside the cutter's bounding box (+ margin) may disappear.  The EXACT
    solver occasionally mis-classifies a whole region (v0.3: the tailgate
    ribbon deleted 85 % of the shell).  On failure the cut is retried with a
    sub-millimetre perturbation of the cutter;
    if every attempt fails the cut is skipped and reported."""
    v = np.array([cutter.matrix_world @ x.co for x in cutter.data.vertices])
    lo, hi = v.min(0) - margin, v.max(0) + margin
    before = _outside_count(skin, lo, hi)
    stray0 = _stray_walls(skin, bvh) if bvh is not None else 0
    from mathutils.bvhtree import BVHTree
    inside0 = _inside_count(skin, BVHTree.FromObject(cutter, bpy.context.evaluated_depsgraph_get()),
                            lo, hi)
    n0 = len(skin.data.polygons)
    name = cutter.name
    # (translation m, rotation deg about x/y/z through the cutter centre, scale)
    attempts = [("EXACT", None), ("EXACT", ((0.00013, -0.00009, 0.00011), (0, 0, 0), 1.0)),
                ("EXACT", ((-0.00021, 0.00017, -0.00007), (0, 0, 0), 1.0)),
                ("EXACT", ((0, 0, 0), (0, 0.37, 0), 1.0)),
                ("EXACT", ((0, 0, 0), (0.29, 0, 0.23), 1.0)),
                ("EXACT", ((0.0004, 0.0003, -0.0002), (0.11, 0.53, -0.17), 1.0007))]
    backup = skin.data.copy()
    for k, (solver, jitter) in enumerate(attempts):
        if jitter is not None:
            from mathutils import Euler, Matrix, Vector
            t, r, sc = jitter
            c = Vector(tuple((lo + hi) / 2))
            cutter.matrix_world = (Matrix.Translation(c + Vector(t))
                                   @ Euler(tuple(np.radians(r))).to_matrix().to_4x4()
                                   @ Matrix.Scale(sc, 4) @ Matrix.Translation(-c))
        last = k == len(attempts) - 1
        mesh.boolean(skin, cutter, solver=solver, transfer_materials=True, delete_cutter=False)
        after = _outside_count(skin, lo, hi)
        stray = _stray_walls(skin, bvh) if bvh is not None else 0
        from mathutils.bvhtree import BVHTree
        cb = BVHTree.FromObject(cutter, bpy.context.evaluated_depsgraph_get())
        inside = _inside_count(skin, cb, lo, hi)
        cut_ok = stray <= stray0 + 3 and inside <= max(25, int(inside0 * 0.12))
        if cut_ok and after < before - max(80, before // 2000):
            # the cut itself is right but the solver dropped faces far from the
            # cutter (whole islands such as a door already freed by its shut
            # lines, mis-classified by winding number): put them back from the
            # backup - a cutter cannot legitimately change anything outside
            # its bounding box
            n_back = _restore_outside(backup, skin, lo, hi)
            after = _outside_count(skin, lo, hi)
            print(f"   [body] cut {name}: restored {n_back} faces dropped outside the cutter")
        if after >= before - max(80, before // 2000) and cut_ok:
            if DEBUG or k:
                print(f"   cut {name} {n0} -> {len(skin.data.polygons)} ({solver}, try {k})")
            break
        if DEBUG and k == 0 and before - after > 100:
            _report_lost(backup, skin, lo, hi)
        print(f"   [body] cut {name} failed ({solver}, try {k}): {before - after} faces lost "
              f"outside the cutter, {stray - stray0} stray walls, {inside} faces left inside"
              f" - retrying" if not last else
              f"   [body] cut {name} FAILED, skipped")
        old = skin.data
        skin.data = backup.copy()
        bpy.data.meshes.remove(old)
    bpy.data.meshes.remove(backup)
    scene.delete(cutter)


def _remap_materials(ob):
    for slot in ob.material_slots:
        m = slot.material
        if m and "." in m.name and m.name.rsplit(".", 1)[1].isdigit():
            base = bpy.data.materials.get(m.name.rsplit(".", 1)[0])
            if base:
                slot.material = base


def build(ctx):
    paint = ctx.mat("paint")
    dark = ctx.mat("gap")
    here = os.path.dirname(os.path.abspath(__file__))
    k = cache.key(*(os.path.join(here, f) for f in
                    ("lines.py", "surface.py", "openings.py", "shell.py", "surftools.py",
                     "features.py")))
    ctx.data["body_lines"] = surface.BodyLines()
    got = cache.load("body", k, {"Body_Shell", "Body_Skin_Reference"},
                     lambda ob: scene.collection("_Construction" if "Reference" in ob.name
                                                 else "Exterior/Body"))
    if got:
        for ob in got.values():
            _remap_materials(ob)
        ref = got["Body_Skin_Reference"]
        ref.hide_render = True
        ref.hide_set(True)
        ctx.register("skin_ref", ref)
        ctx.register("body_skin", got["Body_Shell"])
        print("[body] shell loaded from cache")
        return
    skin, bl, grid = skin_object(material=paint)

    # untouched reference surface (glass panes, ray casting, trims)
    ref = skin.copy()
    ref.data = skin.data.copy()
    ref.name = "Body_Skin_Reference"
    scene.collection("_Construction").objects.link(ref)
    ref.hide_render = True
    ref.hide_set(True)
    ctx.register("skin_ref", ref)

    t = time.time()
    mesh.solidify(skin, SHELL_THICKNESS, offset=-1.0)
    mesh.assign_material(skin, dark, slot_only=True)

    cut_col = scene.temp_collection("_cutters_body")
    # v0.3: shut-line gaps first, large openings last.  A gap cutter whose end
    # pokes into an opening that was already cut (wheel arch, rear glass)
    # intersects the opening's walls and the EXACT solver then mis-classifies
    # whole regions of the shell; cut in this order the opening simply
    # removes the end of the gap.
    from .surftools import Surface
    surf = Surface(ref)
    cutters = []
    cutters += openings.gap_cutters(cut_col, material=dark)
    cutters += openings.gap_cutters_local(surf, cut_col, material=dark)
    cutters += openings.arch_cutter("Cut_Arch_F", 0.0, cut_col, material=dark)
    cutters += openings.arch_cutter("Cut_Arch_R", mm(-2636), cut_col, material=dark,
                                    r=openings.ARCH_R_REAR)
    cutters += openings.window_cutters(cut_col, material=dark)
    cutters += openings.front_cutters(surf, cut_col, material=dark)
    cutters += openings.rear_cutters(surf, cut_col, material=dark)
    # cut the closed thin shell one cutter at a time (bounded memory); the
    # FAST solver is reliable here because the shell stays a closed manifold
    # and no cutter face is coplanar with the skin.
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(ref, bpy.context.evaluated_depsgraph_get())
    for c in list(cut_col.objects):
        guarded_cut(skin, c, bvh=bvh)
    bpy.data.collections.remove(cut_col)

    print(f"[body] cut {len(cutters)} openings/gaps in {time.time() - t:.1f}s")
    skin.name = "Body_Shell"
    mesh.shade_smooth(skin, 28)
    ctx.register("body_skin", skin)
    cache.save("body", k, [skin, ref])
