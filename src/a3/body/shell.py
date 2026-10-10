"""Body-in-white outer skin (painted shell) of the A3 Sportback 8V."""
from __future__ import annotations

import bmesh
import numpy as np

from ..core import mesh
from . import surface


def skin_object(name="Body_Skin", spacing=0.012, collection="Exterior/Body",
                material=None):
    bl = surface.BodyLines()
    grid, xs = surface.skin_grid(bl, spacing)
    nu, nv, _ = grid.shape
    left = grid
    right = grid.copy()
    right[..., 1] *= -1
    verts = np.vstack([left.reshape(-1, 3), right.reshape(-1, 3)])
    faces = mesh.grid_faces(nu, nv, flip=False)
    off = nu * nv
    faces += [tuple(i + off for i in f[::-1]) for f in mesh.grid_faces(nu, nv)]
    ob = mesh.object_from_pydata(name, verts, faces, collection, material, smooth=False)
    # merge the centre-line seams and the collapsed tip rows
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    mesh.shade_smooth(ob, 28)
    return ob, bl, grid


def build(ctx):
    ob, bl, grid = skin_object(material=ctx.mat("paint"))
    ctx.register("body_skin", ob)
    ctx.data["body_lines"] = bl
    ctx.data["skin_grid"] = grid
