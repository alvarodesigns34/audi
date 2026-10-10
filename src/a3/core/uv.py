"""UV generation for textured materials.

* Tileable surface textures (materials with ``uv_tile``): box projection in
  the object's local space - every face uses the two axes perpendicular to
  its dominant normal axis, scaled to tiles (metres / tile size).  Grain-like
  textures hide the seams between projection directions.
* Content images (``uv_content``: screens) are mapped by the part that
  creates them (planar, in the screen's own frame); see set_planar().
"""
from __future__ import annotations

import numpy as np


def _loops(me):
    nl = len(me.loops)
    vi = np.zeros(nl, int)
    me.loops.foreach_get("vertex_index", vi)
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    np_ = len(me.polygons)
    ls = np.zeros(np_, int)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(np_, int)
    me.polygons.foreach_get("loop_total", lt)
    nrm = np.zeros(np_ * 3)
    me.polygons.foreach_get("normal", nrm)
    mi = np.zeros(np_, int)
    me.polygons.foreach_get("material_index", mi)
    face_of_loop = np.repeat(np.arange(np_), lt)
    return co[vi], face_of_loop, nrm.reshape(-1, 3), mi


def box_project(me, tiles_per_mat):
    """tiles_per_mat: list (per material slot) of tile size in metres or None."""
    if not me.polygons:
        return
    P, f, N, mi = _loops(me)
    tile = np.array([t if t else 0.1 for t in tiles_per_mat] or [0.1])
    t_loop = tile[np.clip(mi[f], 0, len(tile) - 1)]
    ax = np.argmax(np.abs(N), 1)[f]
    uv = np.zeros((len(P), 2))
    for a, (i, j) in enumerate(((1, 2), (0, 2), (0, 1))):
        m = ax == a
        uv[m, 0] = P[m, i]
        uv[m, 1] = P[m, j]
    uv /= t_loop[:, None]
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", uv.ravel())


def set_planar(me, origin, u_axis, v_axis, size, mat_index=None):
    """Planar UVs: uv = ((p-o).u / size_u + 0.5, (p-o).v / size_v + 0.5)."""
    P, f, N, mi = _loops(me)
    d = P - np.asarray(origin)
    uv = np.stack([d @ np.asarray(u_axis) / size[0] + 0.5, d @ np.asarray(v_axis) / size[1] + 0.5], 1)
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    if mat_index is not None:
        old = np.zeros(len(P) * 2)
        layer.data.foreach_get("uv", old)
        old = old.reshape(-1, 2)
        keep = mi[f] != mat_index
        uv[keep] = old[keep]
    layer.data.foreach_set("uv", uv.ravel())


def apply_all():
    """Box-project every mesh that uses a tiled material (shared mesh data is
    processed once)."""
    import bpy
    done = set()
    n = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.data.name in done:
            continue
        me = ob.data
        tiles = [(m.get("uv_tile") if m else None) for m in me.materials]
        if not any(tiles):
            continue
        if any(m and m.get("uv_content") for m in me.materials):
            continue
        box_project(me, tiles)
        done.add(me.name)
        n += 1
    print(f"[uv] box-projected {n} meshes")
