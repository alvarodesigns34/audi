"""Body-in-white outer skin (painted shell) of the A3 Sportback 8V."""
from __future__ import annotations

import time

import bmesh
import bpy
import numpy as np

from ..core import mesh, scene
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


def build(ctx):
    paint = ctx.mat("paint")
    dark = ctx.mat("gap")
    skin, bl, grid = skin_object(material=paint)
    ctx.data["body_lines"] = bl
    ctx.data["skin_grid"] = grid

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
    cutters = []
    cutters += openings.arch_cutter("Cut_Arch_F", 0.0, cut_col, material=dark)
    cutters += openings.arch_cutter("Cut_Arch_R", mm(-2636), cut_col, material=dark)
    cutters += openings.window_cutters(cut_col, material=dark)
    cutters += openings.gap_cutters(cut_col, material=dark)
    # cut the closed thin shell one cutter at a time (bounded memory); the
    # FAST solver is reliable here because the shell stays a closed manifold
    # and no cutter face is coplanar with the skin.
    for c in list(cut_col.objects):
        n0 = len(skin.data.polygons)
        mesh.boolean(skin, c, solver=BOOL_SOLVER, transfer_materials=True)
        if DEBUG:
            print("   cut", c.name if False else "", n0, "->", len(skin.data.polygons))
    bpy.data.collections.remove(cut_col)

    print(f"[body] cut {len(cutters)} openings/gaps in {time.time() - t:.1f}s")
    skin.name = "Body_Shell"
    mesh.shade_smooth(skin, 28)
    ctx.register("body_skin", skin)
