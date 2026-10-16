"""Rear end: tail lamps, S line diffuser with twin left tail pipes, licence
plate, rear rings, S line roof spoiler with third brake light, rear wiper and
roof antenna."""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..body import surftools as st
from ..core import mesh, scene
from ..core.curves import catmull_rom, resample, rounded_polygon
from . import front_end as fe

COL = "Exterior/Rear"
LCOL = "Exterior/Lights"


def _rear_x(surf, y, z):
    P, N = surf.project([(y, z)], "YZ", side=-1)
    return (P[0], N[0]) if P[0] is not None else (None, None)


def _eye_frame(P, eye):
    """Per-point frame for content placed in a lamp seen from `eye`."""
    D = P - eye
    return D / np.linalg.norm(D, axis=1)[:, None]


def _shrink(loop, eye, d):
    """Move loop points towards its centre in the eye's image plane by d (m)."""
    c = loop.mean(0)
    D = _eye_frame(loop, eye)
    lat = c - loop
    lat -= (lat * D).sum(1)[:, None] * D
    lat /= np.linalg.norm(lat, axis=1)[:, None] + 1e-12
    return loop + lat * d


def _longest_run(loop, mask):
    """Longest contiguous run of a closed loop where mask is true (in order)."""
    n = len(loop)
    if mask.all():
        return loop
    start = int(np.argmin(mask))            # a False index: unroll from there
    idx = [(start + k) % n for k in range(n)]
    best, cur = [], []
    for i in idx:
        if mask[i]:
            cur.append(i)
        else:
            if len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) > len(best):
        best = cur
    return loop[best]


def _taillight(ctx, ref, surf, mirror):
    """8V Sportback tail lamp (pre-facelift): one lens split by the tailgate shut
    line into an outer unit (quarter panel) and an inner unit (tailgate).
    Inside: dark smoked housing, a light bar along the upper edge (indicator,
    amber) and a red light guide following the lower contour of each unit
    ('U' signature, rearq.jpg lit), reversing lamp in the inner unit (white
    reflector, sline_rear.jpg).  Depths E."""
    sfx = ".R" if mirror else ".L"
    s = -1 if mirror else 1
    tmp = scene.temp_collection("_tmp_patch")
    cut = op.taillight_cutter("TL_cut" + sfx, surf, tmp, mirror=mirror)
    lens = st.patch_with_cutter(ref, cut, "Taillight_Lens" + sfx, LCOL, ctx.mat("lens_red"))
    # inner layers: smoked red inner lens and the black housing behind it
    for nm, mat, d in (("Inner", "lens_red_dark", -0.020), ("Housing", "lamp_housing", -0.055)):
        c = lens.copy()
        c.data = lens.data.copy()
        scene.link(c, LCOL)
        c.name = f"Taillight_{nm}{sfx}"
        c.data.materials.clear()
        c.data.materials.append(ctx.mat(mat))
        st.offset(c, d)
        if nm == "Housing":
            co = mesh.mesh_arrays(c)
            cc = co.mean(0)
            mesh.set_mesh_arrays(c, cc + (co - cc) * 0.97)
    st.offset(lens, 0.0006)
    mesh.solidify(lens, 0.003, offset=-1.0)
    mesh.shade_smooth(lens, 60)
    # housing side walls: lens outline -> housing outline
    P, N, eye = op.taillight_outline(surf, mirror, n=160)
    walls = np.array([P - N * 0.002, P - N * 0.03, P - N * 0.055])
    mesh.grid_object("Taillight_Wall" + sfx, walls, closed_v=True, collection=LCOL,
                     material=ctx.mat("lamp_housing"), flip=mirror)

    def on_lens(loop, depth):
        Q, M = op.project_from(surf, loop, eye)
        return Q - M * depth

    from ..core.curves import catmull_rom as cr
    pts = np.asarray(op.TAILLIGHT_3D, float) * 1e-3 * [1, s, 1]
    split = np.asarray(op.TAILGATE_LOW, float)[[2, 3]] * 1e-3 * [1, s, 1]   # shut line top/bottom
    # upper light bar (amber indicator): along the top edge, 14 mm inside
    top = resample(cr(pts[:6], 8), 60)
    top = _shrink(top, eye, 0.014)
    bar = on_lens(top, 0.010)
    mesh.tube_along("Taillight_Bar" + sfx, bar, 0.0035, sides=10, collection=LCOL,
                    material=ctx.mat("led_amber"))
    # lower 'U' light guides, one per unit, 18 mm inside the outline
    loop = resample(cr(pts, 6, closed=True), 240, closed=True)
    inner = _shrink(loop, eye, 0.020)
    # outer unit: points with x > shut line x at their height
    xs_split = np.interp(inner[:, 2], split[::-1, 2], split[::-1, 0])
    low = inner[:, 2] < 0.905
    for nm, mask in (("Outer", (inner[:, 0] > xs_split + 0.03) & low),
                     ("Inner", (inner[:, 0] < xs_split - 0.03) & low)):
        seg = _longest_run(inner, mask)
        if len(seg) < 6:
            continue
        g = on_lens(resample(seg, 50), 0.012)
        mesh.tube_along(f"Taillight_Guide_{nm}{sfx}", g, 0.0032, sides=10, collection=LCOL,
                        material=ctx.mat("led_red"))
    # reversing lamp: clear lens + reflector in the inner unit (sline_rear)
    rc = np.array([-3.318, s * 0.395, 0.880])
    Q, M = op.project_from(surf, [rc], eye)
    if len(Q):
        q, nrm = Q[0], M[0]
        t = np.cross(nrm, [0, 0, 1.0])
        t /= np.linalg.norm(t)
        u = np.cross(t, nrm)
        w, h = 0.060, 0.016
        quad = [q - nrm * 0.008 + t * a * w / 2 + u * b * h / 2 for a, b in
                ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        back = [p - nrm * 0.022 for p in quad]
        verts = [tuple(p) for p in quad + back]
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        ob = mesh.object_from_pydata("Taillight_Reverse" + sfx, verts, faces, LCOL,
                                     ctx.mat("reflector"), smooth=False)
        mesh.recalc_normals(ob)


def _diffuser(ctx, surf):
    """S line rear diffuser insert (black grained plastic) set 4 mm into the
    bumper opening, twin chrome tail pipes on the left,
    four parking sensors and the tow-eye cover (sline_rear ray casts, S)."""
    dark = ctx.mat("black_textured")
    gloss = ctx.mat("black_gloss")
    chrome = ctx.mat("chrome")
    D = np.asarray(op.DIFFUSER, float)[:-1] * 1e-3
    top = np.vstack([(D[::-1] * [-1, 1])[:-1], D])          # y -> z of the top edge
    rows = []
    for z_frac in np.linspace(0.0, 1.0, 16):
        row = []
        for y in np.linspace(-0.80, 0.80, 81):
            zt = np.interp(y, top[:, 0], top[:, 1]) if abs(y) <= 0.805 else 0.24
            z = zt + (0.232 - zt) * z_frac
            p, n = _rear_x(surf, y, z)
            if p is None:
                row.append((-3.40, y, z))
            else:
                row.append(tuple(p - n * 0.004))
        rows.append(row)
    pan = mesh.grid_object("Diffuser_Panel", np.array(rows), collection=COL, material=dark,
                           flip=True)
    mesh.shade_smooth(pan, 40)
    # (no vertical fins: none on the 8V S line insert, sline_rear / yellow_rear)
    # twin round tail pipes (left), chrome, double-wall, slightly protruding
    for (yy, zz) in op.EXHAUST_TIPS:
        y, z = yy * 1e-3, zz * 1e-3
        p, n = _rear_x(surf, y, z + 0.06)
        x = (p[0] if p is not None else -3.38) - 0.006
        r = op.EXHAUST_D * 1e-3 / 2
        prof = np.array([[r * 0.80, x + 0.12], [r * 0.80, x + 0.003], [r * 0.86, -0.0 + x - 0.002],
                         [r * 0.96, x - 0.002], [r, x + 0.003], [r, x + 0.12]])
        mesh.revolve(f"Exhaust_Tip_{yy}", prof, 64, axis="X", center=(0, y, z), collection=COL,
                     material=chrome)
        mesh.revolve(f"Exhaust_Inner_{yy}", np.array([[r * 0.79, x + 0.003], [r * 0.79, x + 0.2],
                                                       [0.0, x + 0.2]]),
                     48, axis="X", center=(0, y, z), collection=COL, material=ctx.mat("steel_dark"))
    # parking sensors (painted body colour, 18 mm, in a thin dark ring)
    for k, (y, z) in enumerate(((0.686, 0.541), (0.267, 0.559), (-0.267, 0.559),
                                (-0.686, 0.541))):
        p, n = _rear_x(surf, y, z)
        if p is None:
            continue
        for nm, rr, dep, mat in (("Ring", 0.0105, 0.0006, "gap"), ("Head", 0.0090, 0.0010,
                                                                     "paint")):
            ob = mesh.revolve(f"Park_Sensor_R{k}_{nm}", np.array([[0.0, 0.0], [rr, 0.0],
                                                                  [rr, dep], [0.0, dep]]),
                              32, axis="Z", collection=COL, material=ctx.mat(mat))
            _place_on(ob, p, n)
    # tow-eye cover (right side): rounded rectangle shut line
    p, n = _rear_x(surf, -0.373, 0.465)
    if p is not None:
        rr = rounded_polygon([(-0.022, -0.013), (0.022, -0.013), (0.022, 0.013),
                              (-0.022, 0.013)], 0.004, 4)
        ring = np.array([(0.0, a, b) for a, b in rr])
        t = np.cross(n, [0, 0, 1.0])
        t /= np.linalg.norm(t)
        u = np.cross(t, n)
        loop = np.array([p + t * a + u * b + n * 0.0004 for _, a, b in ring])
        mesh.tube_along("Tow_Eye_Cover_Line", np.vstack([loop, loop[:1]]), 0.0008, sides=6,
                        collection=COL, material=ctx.mat("gap"))


def _place_on(ob, p, n):
    """Move an object modelled about +Z at the origin onto point p, +Z -> n."""
    from mathutils import Matrix, Vector
    rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(n))).to_matrix().to_4x4()
    ob.data.transform(Matrix.Translation(Vector(tuple(p))) @ rot)
    ob.data.update()


def _plate_rings(ctx, surf):
    # rings on the tailgate
    chrome = ctx.mat("badge_chrome")
    cz = 0.922     # v0.3: triangulated rings centre z 0.915-0.926 (sline_rear/yellow_rear)
    od, pitch, tw = 0.078, 0.052, 0.009
    sec = rounded_polygon([(-tw / 2, -0.004), (tw / 2, -0.004), (tw / 2, 0.004),
                           (-tw / 2, 0.004)], 0.003, 4)
    for i in range(4):
        cy = (i - 1.5) * pitch
        r = od / 2 - tw / 2
        grid = []
        for t in np.linspace(0, 2 * math.pi, 96, endpoint=False):
            y, z = cy + r * math.cos(t), cz + r * math.sin(t)
            p, n = _rear_x(surf, y, z)
            pnt = np.array([(p[0] if p is not None else -3.40) - 0.006, y, z])
            radial = np.array([0, math.cos(t), math.sin(t)])
            grid.append([pnt + radial * q[0] - np.array([1.0, 0, 0]) * q[1] for q in sec])
        mesh.grid_object(f"Badge_Rings_Rear_{i}", np.array(grid), closed_u=True, closed_v=True,
                         collection=COL, material=chrome, flip=True)
    # licence plate on the tailgate, rotated to face rearwards
    obs = fe._plate(ctx, surf=None, cz=0.780, front=False)
    p, n = _rear_x(surf, 0.0, 0.78)
    for o in obs:
        mesh.transform(o, rot=(0, 0, math.pi))
        o.data.transform(__import__("mathutils").Matrix.Translation((p[0] - 0.012 if p is not None else -3.44, 0, 0)))
        for c in list(o.users_collection):
            c.objects.unlink(o)
        scene.link(o, COL)
        o.name = o.name.replace("Plate", "Plate_Rear")


def _spoiler(ctx, ref, surf):
    """S line roof spoiler lip (v0.3).  The top of the tailgate (from the roof
    seam to the trailing edge) is the tailgate panel itself; this object is the
    trailing-edge lip that overhangs the rear glass, body coloured on top and
    gloss black underneath (the black band seen above the glass in
    sline_rear / yellow_rear / rearq), crescent shaped in plan (trailing edge
    from the centre x -3.19 to the ends x -2.80 at the glass corners, E/S),
    with the third brake light under the centre."""
    from mathutils import Vector
    paint, black = ctx.mat("paint"), ctx.mat("black_gloss")
    te = np.asarray(op.SPOILER_TE, float) * 1e-3
    te[0, 0] = -3.190                                # centre at the profile crease (Z_TOP)
    half = te[:, :2]
    full = np.vstack([(half[::-1] * [1, -1])[:-1], half])
    full = resample(catmull_rom(full, 10), 141)
    # the lip only runs across the glass (|y| < 0.53); the spoiler ends at the
    # corners are body (they would otherwise hang down the D-pillars)
    full = full[np.abs(full[:, 1]) < 0.575]
    gtop = np.asarray(op.REAR_GLASS_TOP, float) * 1e-3
    te_abs = np.asarray(op.SPOILER_TE, float)[:, 1:] * 1e-3      # (|y|, z) of the trailing edge
    hits = []
    for k, (x, y) in enumerate(full):
        hit = surf.bvh.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)), 4.0)
        if hit[0] is not None:
            p = np.array(hit[0][:])
            # never below the measured trailing edge: over the glass the ray
            # lands on the (lower) glass and the lip dipped into it
            p[2] = max(p[2], float(np.interp(abs(y), te_abs[:, 0], te_abs[:, 1])))
            hits.append((k, p, np.array(hit[1][:])))
    # v0.4: the lip follows a smoothed seat (gaussian over ~60 mm): the raw hits
    # copied every ripple of the roof end into the trailing edge
    ks = np.array([h[0] for h in hits])
    PP = np.array([h[1] for h in hits])
    NN = np.array([h[2] for h in hits])
    w = np.exp(-0.5 * (np.arange(-12, 13) / 5.0) ** 2)
    for A in (PP, NN):
        pad = np.pad(A, ((12, 12), (0, 0)), mode="edge")
        for c in range(3):
            A[:, c] = np.convolve(pad[:, c], w / w.sum(), mode="valid")
    NN /= np.linalg.norm(NN, axis=1)[:, None]
    secs, tes = [], []
    for k, P, n in zip(ks, PP, NN):
        x, y = full[k]
        # outward horizontal direction, normal to the trailing edge in plan
        j0, j1 = max(k - 1, 0), min(k + 1, len(full) - 1)
        t = np.array([full[j1, 0] - full[j0, 0], full[j1, 1] - full[j0, 1], 0.0])
        t /= np.linalg.norm(t) + 1e-12
        r = np.array([-t[1], t[0], 0.0])             # rearward / outward in plan
        u = abs(y) / 0.575
        fade = min(1.0, (1 - u) / 0.15) if u > 0.85 else 1.0
        over = (0.026 * (1 - u ** 4) + 0.006) * fade + 0.001
        drop = (0.030 * (1 - u ** 3) + 0.010) * fade + 0.002
        zc = P[2]
        prof = [P - r * 0.050 + np.array([0, 0, 0.0015]),        # on the panel, ahead
                P + np.array([0, 0, 0.0035]),
                P + r * over + np.array([0, 0, 0.0012]),         # trailing edge top
                P + r * (over + 0.002) - np.array([0, 0, 0.004]),  # trailing edge
                P + r * (over * 0.4) - np.array([0, 0, drop * 0.75]),
                P - r * 0.004 - np.array([0, 0, drop]),           # meets the glass
                P - r * 0.030 - n * 0.004]                        # inside the skin
        secs.append(prof)
        tes.append(P + r * (over * 0.5) - np.array([0, 0, drop * 0.55]))
    g = np.array(secs)
    sp = mesh.grid_object("Roof_Spoiler", g, closed_v=True, cap_u=True, collection=COL,
                          material=paint)
    mesh.recalc_normals(sp)
    bi = mesh.material_index(sp, black)
    nv = g.shape[1]
    for p in sp.data.polygons:
        if p.loop_total == 4:
            j = min(v % nv for v in p.vertices)
            jm = max(v % nv for v in p.vertices)
            # profile segments 3.. (trailing edge -> under the lip -> inside) are black
            if j >= 3 or (j == 0 and jm == nv - 1):
                p.material_index = bi
    mesh.shade_smooth(sp, 35)
    # third brake light: LED strip under the centre of the lip (|y| < 0.16)
    tes = np.array(tes)
    c = tes[np.abs(tes[:, 1]) < 0.16]
    if len(c) > 3:
        mesh.tube_along("Brake_Light_High", c, 0.0040, sides=8, collection=LCOL,
                        material=ctx.mat("led_red"))


def _wiper_antenna(ctx, surf):
    """Rear wiper parked along the lower edge of the glass towards the right
    (-y) side (sline_rear, rear2012, fl_rear), pivot near the centre; arm length
    ~400 mm, blade 330 mm (E)."""
    black, rubber = ctx.mat("black_satin"), ctx.mat("rubber_seal")
    # parked line: 15 mm (in x, ~35 mm up the glass) above the glass bottom
    # edge, found in the radial chart of the rear (no projection that could
    # jump off the glass)
    B = np.asarray(op.REAR_GLASS_BOTTOM, float)[::-1] * 1e-3     # centre -> corner
    ys = np.linspace(0.02, -0.43, 40)
    xb = np.interp(np.abs(ys), B[:, 1], B[:, 0]) + 0.015
    zb = np.interp(np.abs(ys), B[:, 1], B[:, 2]) + 0.035
    P, N = op.radial_cast(surf, op.to_xth(np.stack([xb, ys, zb], 1)) * [1, 1])
    if len(P):
        out = ((P - np.asarray(op.CHART_O)) * N).sum(1) < 0
        N[out] *= -1
    if len(P) > 5:
        arm = P + N * 0.016
        mesh.sweep_profile("Rear_Wiper_Arm", arm,
                           np.array([[-0.007, -0.004], [0.007, -0.004], [0.006, 0.004],
                                     [-0.006, 0.004]]), collection=COL, material=black)
        k = len(P) // 5
        blade = P[k:] + N[k:] * 0.006
        mesh.sweep_profile("Rear_Wiper_Blade", blade,
                           np.array([[-0.003, -0.005], [0.003, -0.005], [0.004, 0.004],
                                     [-0.004, 0.004]]), collection=COL, material=rubber)
        # pivot cover (cap over the spindle nut)
        q, n = P[1], N[1]
        prof = np.array([[0.0, 0.0], [0.020, 0.0], [0.019, 0.016], [0.012, 0.024], [0.0, 0.025]])
        cap = mesh.revolve("Rear_Wiper_Pivot", prof, 32, axis="Z", collection=COL,
                           material=black)
        from mathutils import Matrix, Vector
        rot = Vector((0, 0, 1)).rotation_difference(Vector(tuple(n))).to_matrix().to_4x4()
        cap.data.transform(Matrix.Translation(Vector(tuple(q - n * 0.002))) @ rot)
        cap.data.update()
    _antenna(ctx, surf)


def _antenna(ctx, surf):
    """Short roof fin antenna (8V): body coloured, swept leading edge, tip at
    the rear, black rubber foot.  Tip triangulated on sline_rear /
    sline_front (centre plane): x -2.54, z 1.45 (S, +-20 mm); length 105,
    height 55, base width 30 mm (E, from the same photos)."""
    paint, rubber = ctx.mat("paint"), ctx.mat("rubber_seal")
    X_TIP, L, H, W = -2.540, 0.105, 0.055, 0.030
    x_front = X_TIP + 0.092                     # tip 13 mm ahead of the rear end
    P, N = surf.project([(x_front - L / 2, 0.0)], "XY", side=1)
    z0 = P[0][2] if P[0] is not None else 1.39
    secs = []
    for t in np.linspace(0.0, 1.0, 26):         # height fraction (base -> tip)
        # side profile: leading edge sweeps back, trailing edge almost vertical
        xf = x_front - (x_front - (X_TIP + 0.004)) * t ** 0.85
        xr = x_front - L + (X_TIP - 0.006 - (x_front - L)) * t ** 1.6
        h = z0 + H * t - 0.002
        half = (W / 2) * (1.0 - 0.72 * t) + 0.0015
        ring = []
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            # aerofoil plan section: round nose, thin tail
            u = 0.5 - 0.5 * math.cos(a)            # 0 nose -> 1 tail
            x = xf + (xr - xf) * u
            th = half * (math.sqrt(u) * (1 - u) * 2.6 if u < 1 else 0.0)
            ring.append((x, th * (1 if a < math.pi else -1) * 1.0, h))
        secs.append(ring)
    ob = mesh.grid_object("Roof_Antenna", np.array(secs), closed_v=True, cap_u=True,
                          collection=COL, material=paint)
    mesh.shade_smooth(ob, 50)
    base = rounded_polygon([(x_front - L - 0.004, -W / 2 - 0.004), (x_front + 0.004, -W / 2 - 0.004),
                            (x_front + 0.004, W / 2 + 0.004), (x_front - L - 0.004, W / 2 + 0.004)],
                           0.012, 6)
    mesh.extrude_polygon("Roof_Antenna_Seal", base, 0.004, plane="XY", offset=z0 - 0.003,
                         collection=COL, material=rubber)


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    for mirror in (False, True):
        _taillight(ctx, ref, surf, mirror)
    _diffuser(ctx, surf)
    _plate_rings(ctx, surf)
    _spoiler(ctx, ref, surf)
    _wiper_antenna(ctx, surf)
    tmp = scene.temp_collection("_tmp_patch")
    for o in list(tmp.objects):
        scene.delete(o)
