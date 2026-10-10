"""Split the cut body shell into its real panels.

The shut-line gaps are already cut through the shell (openings.py), so the
panels are separate islands along every visible joint.  Each face is
classified by its centroid against the same shut-line tables:

    Hood, Cowl (black plastic strip in front of the windscreen), Bumper_F,
    Fender.L/R, Door_FL/FR/RL/RR, Skirt.L/R (S line side skirts),
    Tailgate, Bumper_R and Shell (roof, body sides, pillars, quarter panels).
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np

from ..core import mesh, scene
from . import openings as op

COL = "Exterior/Body"


def _interp_xz(line, z, key=1):
    """x(z) along a side-view polyline [(x, z), ...] (mm) -> metres."""
    p = np.asarray(line, float) * 1e-3
    o = np.argsort(p[:, key])
    return np.interp(z, p[o, key], p[o, 1 - key])


def _poly_contains(poly, pts):
    """Vectorised point-in-polygon (even-odd), poly (N, 2), pts (M, 2)."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cond = (y0 > y) != (y1 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
        inside ^= cond & (x < xi)
    return inside


def _hood_plan():
    side = np.asarray(op.HOOD_SIDE, float)                    # rear -> front (x, y)
    front = np.array([(540, 805), (620, 740), (700, 650), (765, 550), (792, 445),
                      (796, 390), (800, 0)], float)
    rear = np.asarray(op.HOOD_REAR, float)[::-1]              # (-400,775) -> (-306,0)
    half = np.vstack([side, front])                           # from rear corner to front centre
    poly = np.vstack([half, (half[::-1] * [1, -1])[1:],       # down the other side
                      (rear * [1, -1])[1:], rear[::-1][1:-1]])
    return poly * 1e-3


def _cowl_plan():
    rear = np.asarray(op.HOOD_REAR, float)                    # (-306,0) -> (-400,775)
    ws = np.asarray(op.WINDSCREEN[:4], float)                 # (-350,0) -> (-440,760)
    half = np.vstack([rear, ws[::-1] + [-40, 40]])
    poly = np.vstack([half, (half[::-1] * [1, -1])])
    return poly * 1e-3


def classify(C, N):
    """Panel label per face from centroids C (M, 3) and normals N (M, 3)."""
    x, y, z = C[:, 0], C[:, 1], C[:, 2]
    ay = np.abs(y)
    lab = np.full(len(C), "Shell", dtype=object)
    side = np.where(y >= 0, ".L", ".R")

    # --- tailgate ------------------------------------------------------------------
    tg = np.asarray(op.TAILGATE, float) * 1e-3
    tz, ty = tg[:-2, 1][::-1], tg[:-2, 0][::-1]                 # side part, z ascending
    y_tg = np.interp(z, tz, ty)
    z_bot = np.interp(ay, [0.0, 0.45, 0.556], [0.652, 0.654, 0.659])
    x_tg_top = np.asarray(op.TAILGATE_TOP, float)[:, 0].mean() * 1e-3
    tailgate = (x < -2.95) & (z > z_bot - 0.002) & (ay < y_tg + 0.002) & (z < 1.33)
    tailgate |= (x < x_tg_top) & (z > 1.25) & (ay < 0.62)
    # the D-pillar/side faces next to the glass stay on the body
    tailgate &= ~((N[:, 1] * np.sign(y + 1e-9) > 0.75) & (ay > 0.55))
    lab[tailgate] = "Tailgate"

    # --- rear bumper ---------------------------------------------------------------
    x_rbs = _interp_xz(op.REAR_BUMPER_SPLIT, z)
    z_rb = np.interp(ay, [0.0, 0.556, 0.60, 0.64, 0.80, 0.95], [0.652, 0.659, 0.712, 0.783,
                                                                  0.792, 0.80])
    rbump = (x < x_rbs) & (z < z_rb) & (x < -2.85) & ~tailgate
    lab[rbump] = "Bumper_R"

    # --- hood and cowl -----------------------------------------------------------------
    hood_front_z = np.interp(ay, np.asarray(op.HOOD_FRONT, float)[:, 0] * 1e-3,
                             np.asarray(op.HOOD_FRONT, float)[:, 1] * 1e-3)
    zmin = np.where(x > 0.45, hood_front_z - 0.004, 0.70)
    xy = np.stack([x, y], 1)
    hood = _poly_contains(_hood_plan(), xy) & (z > zmin)
    lab[hood] = "Hood"
    cowl = _poly_contains(_cowl_plan(), xy) & (z > 0.80) & (N[:, 2] > 0.3) & ~hood
    lab[cowl] = "Cowl"

    # --- front bumper / fenders ----------------------------------------------------------
    split_x = np.interp(z, [0.0, 0.44, 0.47, 0.52, 0.574, 0.628, 0.642, 0.70, 0.745, 1.2],
                        [0.28, 0.30, 0.35, 0.41, 0.47, 0.54, 0.565, 0.50, 0.46, 0.46])
    fbump = (x > split_x) & (z < 0.76) & ~hood
    lab[fbump] = "Bumper_F"
    fdf_x = _interp_xz(op.FRONT_DOOR_FRONT, z)
    fr = np.asarray(op.FENDER_REAR, float) * 1e-3
    z_top = np.where(x < fr[-1, 0], np.interp(x, fr[:, 0], fr[:, 1]), 0.975)
    fender = (x > fdf_x) & (x <= split_x) & (z < z_top) & (z > 0.297) & (ay > 0.40) & ~hood \
        & ~cowl
    lab[fender] = np.char.add("Fender", side[fender].astype(str))

    # --- side skirts ---------------------------------------------------------------------
    skirt = (z < 0.302) & (x < -0.30) & (x > -2.34) & (ay > 0.55)
    lab[skirt] = np.char.add("Skirt", side[skirt].astype(str))

    # --- doors ------------------------------------------------------------------------------
    belt = _interp_xz(op.DLO_SIDE[:7], x, key=0)
    bg_x = _interp_xz(op.B_GAP, z)
    rdr_x = _interp_xz(op.REAR_DOOR_REAR, z)
    in_z = (z > 0.299) & (z < belt + 0.012) & (ay > 0.55)
    dfront = in_z & (x < fdf_x) & (x > bg_x) & ~skirt
    drear = in_z & (x <= bg_x) & (x > rdr_x) & ~skirt
    sfx = np.where(y >= 0, "L", "R")
    lab[dfront] = np.char.add("Door_F", sfx[dfront].astype(str))
    lab[drear] = np.char.add("Door_R", sfx[drear].astype(str))
    return lab


def split(shell, materials=None):
    """Split the Body_Shell object into panel objects; returns {label: object}."""
    me = shell.data
    n = len(me.polygons)
    C = np.zeros(n * 3)
    me.polygons.foreach_get("center", C)
    C = C.reshape(-1, 3)
    Nn = np.zeros(n * 3)
    me.polygons.foreach_get("normal", Nn)
    Nn = Nn.reshape(-1, 3)
    lab = classify(C, Nn)
    out = {}
    for name in sorted(set(lab)):
        idx = np.nonzero(lab == name)[0]
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        keep = set(idx.tolist())
        bmesh.ops.delete(bm, geom=[f for i, f in enumerate(bm.faces) if i not in keep],
                         context="FACES")
        nm = "Body_" + name
        m2 = bpy.data.meshes.new(nm)
        bm.to_mesh(m2)
        bm.free()
        for mat in me.materials:
            m2.materials.append(mat)
        ob = bpy.data.objects.new(nm, m2)
        for c in shell.users_collection:
            c.objects.link(ob)
        mesh.shade_smooth(ob, 28)
        out[name] = ob
    if materials and "Cowl" in out:
        cw = out["Cowl"]
        cw.data.materials.clear()
        cw.data.materials.append(materials["cowl"])
        for p in cw.data.polygons:
            p.material_index = 0
    scene.delete(shell)
    return out
