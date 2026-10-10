"""Glazing and window surrounds.

Glass panes are generated from the body reference surface inside the window
outlines (so they follow the exact body curvature), set 3 mm inboard and given
real thickness (4.5 mm laminated windscreen / 4 mm tempered side glass).  A black
ceramic frit band is added on the inner face of the bonded screens.
"""
from __future__ import annotations

import numpy as np

from ..core import mesh, scene
from ..core.curves import catmull_rom, resample
from . import openings as op
from . import surftools as st

COL = "Exterior/Glass"
TRIM_COL = "Exterior/Trim"

# window surround finish: "black" (standard, matt/gloss black) or "aluminium"
WINDOW_TRIM = "black"


def _mm(p):
    return np.asarray(p, float) * 1e-3


def _glass(ref, name, poly, plane, lo, hi, mat, inset=0.003, thick=0.0045):
    g = st.patch(ref, poly, plane, lo, hi, name, COL, mat)
    st.offset(g, -inset)
    mesh.solidify(g, thick, offset=-1.0)
    mesh.shade_smooth(g, 50)
    return g


def build(ctx):
    ref = ctx.objects.get("skin_ref")
    if ref is None:
        raise RuntimeError("glass needs the body part")
    glass = ctx.mat("glass_clear")
    frit = ctx.mat("glass_ceramic_frit")
    black = ctx.mat("black_gloss")
    trim = ctx.mat("black_satin") if WINDOW_TRIM == "black" else ctx.mat("aluminium_brushed")
    seal = ctx.mat("rubber_seal")

    # ---- side glass (left, mirrored to right) --------------------------------
    side = _glass(ref, "Glass_Side.L", _mm(op.DLO_SIDE), "XZ", 0.55, 1.2, glass)
    mesh.mirror_copy_y(side, "Glass_Side.R", COL)
    for nm, poly in (("Trim_BPillar", op.B_PILLAR), ("Trim_CPillar", op.C_PILLAR),
                     ("Trim_MirrorSail", op.SAIL)):
        t = st.patch(ref, _mm(poly), "XZ", 0.55, 1.2, nm + ".L", TRIM_COL, black)
        st.offset(t, 0.0012)
        mesh.solidify(t, 0.003, offset=-1.0)
        mesh.shade_smooth(t, 40)
        mesh.mirror_copy_y(t, nm + ".R", TRIM_COL)

    # ---- windscreen & rear window -------------------------------------------
    # (outline, projection plane, prism range, thickness, frit band width)
    screens = (("Glass_Windscreen", _mm(op.mirror_outline(op.WINDSCREEN)), "XY", 0.9, 1.6,
                0.005, 0.070),
               ("Glass_RearWindow", _mm(op.mirror_outline(op.REAR_WINDOW_YZ, axis=0)), "YZ",
                op.REAR_WINDOW_X[0], op.REAR_WINDOW_X[1], 0.004, 0.055))
    for name, outer, plane, lo, hi, thick, w in screens:
        g = _glass(ref, name, outer, plane, lo, hi, glass, inset=0.002, thick=thick)
        if mesh.polygon_area(outer) < 0:
            outer = outer[::-1]
        inner = mesh.polyline_offset_2d(outer, -w, closed=True)
        if mesh.polygon_area(inner) < 0 or abs(mesh.polygon_area(inner)) > abs(mesh.polygon_area(outer)):
            inner = mesh.polyline_offset_2d(outer, w, closed=True)
        band = st.patch(ref, outer, plane, lo, hi, name + "_Frit", COL, frit)
        hole = mesh.extrude_polygon(name + "_FritHole", inner, hi - lo + 0.2, plane=plane,
                                    offset=lo - 0.1, collection=scene.temp_collection("_tmp_patch"))
        mesh.boolean(band, hole, hole_tolerant=True)
        st.offset(band, -(thick + 0.0025))     # inner face of the glass
        mesh.shade_smooth(band, 40)

    # ---- DLO surround seal / trim (projected outline) ------------------------
    surf = st.Surface(ref)
    outline = resample(catmull_rom(np.vstack([_mm(op.DLO_SIDE)]), 6, closed=True), 400,
                       closed=True)
    P, N = st.clean_projection(*surf.project(outline, "XZ", side=1))
    prof = np.array([[-0.004, -0.004], [0.010, -0.004], [0.010, 0.0015],
                     [0.004, 0.0028], [-0.004, 0.0028]])
    s = st.strip("Trim_DLO_Surround.L", P, N, prof, TRIM_COL, trim, closed=True)
    mesh.mirror_copy_y(s, "Trim_DLO_Surround.R", TRIM_COL)
    # windscreen / rear window bonding seals
    for nm, outline2d, plane, side in (
            ("Seal_Windscreen", op.mirror_outline(op.WINDSCREEN), "XY", 1),
            ("Seal_RearWindow", op.mirror_outline(op.REAR_WINDOW_YZ, axis=0), "YZ", -1)):
        o = resample(catmull_rom(_mm(outline2d), 6, closed=True), 500, closed=True)
        P, N = st.clean_projection(*surf.project(o, plane, side=side))
        prof = np.array([[-0.003, -0.004], [0.003, -0.004], [0.003, 0.001], [-0.003, 0.001]])
        st.strip(nm, P, N, prof, TRIM_COL, seal, closed=True)
    tmp = scene.temp_collection("_tmp_patch")
    for o in list(tmp.objects):
        scene.delete(o)
