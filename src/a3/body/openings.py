"""Openings and shut lines cut into the body shell.

All outlines are in millimetres in a principal projection plane and were
digitised from calibrated reference photographs (tools/camera_match.py,
tools/backproject.py) - status E (estimated, +-20..40 mm) unless noted.

Each outline becomes a prism ("cutter") extruded along the projection axis
over a limited range, so it only touches the intended part of the skin.
"""
from __future__ import annotations

import numpy as np

from ..core import mesh
from ..core.curves import catmull_rom, rounded_polygon

GAP = 4.0  # mm, typical 8V shut-line gap (3.5-4.5)


# --------------------------------------------------------------------------
# Outlines (mm)
# --------------------------------------------------------------------------

# Side daylight opening (both door windows + quarter light), XZ plane.
# Starts behind the mirror sail, runs along the belt, up the quarter-light tip,
# along the glass top to the A-pillar and down the A-pillar.
# v0.2: re-digitised on the side photo with the rim-contour calibration
# (tools/make_match.py, rms < 1 px) and ray cast onto the skin; door features
# cross-checked by triangulation side + rear 3/4 (tools/triangulate.py, <= 3 px).
# v0.3: quarter-light rear edge re-measured (tip x -2.806, y 0.725, z 1.022 from
# side + sline_rear + yellow_rear + rearsq; edge back-projected on side.jpg).
DLO_SIDE = [
    (-545, 927), (-1000, 949), (-1500, 971), (-2000, 993), (-2400, 1007),
    (-2700, 1015), (-2775, 1017), (-2808, 1019), (-2790, 1036), (-2769, 1054),
    (-2707, 1123), (-2640, 1181), (-2571, 1233), (-2525, 1265), (-2480, 1293),
    (-2430, 1312), (-2200, 1326),
    (-1800, 1331), (-1500, 1326), (-1300, 1315), (-1205, 1303), (-1150, 1286),
    (-1060, 1246), (-960, 1196), (-860, 1142), (-779, 1094), (-700, 1043),
    (-625, 986), (-575, 950),
]
# Mirror sail: black triangle in the front corner of the front door window
SAIL = [(-548, 928), (-705, 937), (-768, 1084), (-690, 1038), (-612, 980)]

# B-pillar applique (between the two door windows), C-pillar divider
B_PILLAR = [(-1552, 958), (-1622, 958), (-1645, 1336), (-1575, 1336)]
C_PILLAR = [(-2403, 1012), (-2438, 1012), (-2328, 1316), (-2293, 1316)]

# Door shut lines (side view polylines)
FRONT_DOOR_FRONT = [(-478, 928), (-470, 700), (-463, 450), (-457, 298)]
# door bottom = top edge of the S line side skirt, from arch to arch
DOOR_BOTTOM = [(-330, 300), (-448, 300), (-1000, 305), (-1500, 304), (-1900, 303),
               (-2062, 302), (-2310, 300)]
# fender / A-pillar foot: from the front door gap up to the hood rear corner
FENDER_REAR = [(-482, 922), (-452, 938), (-412, 954), (-385, 966)]
B_GAP = [(-1586, 966), (-1565, 600), (-1544, 298)]
REAR_DOOR_REAR = [(-2440, 1012), (-2468, 945), (-2478, 890), (-2431, 807),
                  (-2384, 682), (-2275, 559), (-2178, 444), (-2100, 355),
                  (-2068, 318), (-2050, 300)]
FRONT_BUMPER_SPLIT = [(565, 642), (540, 628), (470, 574), (410, 520), (350, 470),
                      (300, 440)]
# rear bumper / quarter panel seam: from the tail lamp's lower outer corner
# down, then forward along the top of the bumper into the wheel arch.
# v0.3: sline_rear ray casts on the v0.3 skin, checked on yellow_rear / rearsq.
REAR_BUMPER_SPLIT = [(-3069, 786), (-3068, 750), (-3063, 723), (-3062, 672), (-3051, 643),
                     (-3032, 631), (-2941, 615), (-2862, 601), (-2815, 596)]

# Door handle finger recesses (x, z centre mm; semi-axes mm), pressed into the
# door skin behind the grips (v0.3, centres from exterior/trim.HANDLES + 4 mm)
HANDLE_RECESSES = [(-1390, 784), (-2264, 809)]
HANDLE_RECESS_AXES = (75, 22)

# Fuel filler flap: right-hand side (-Y), rounded rectangle (x, z centre)
FUEL_DOOR = dict(cx=-2660, cz=900, w=180, h=112, r=26)

# Hood shut line along the fender (top view, x/y), both sides
# (runs from the windscreen corner forward to the headlight's upper rear corner)
HOOD_SIDE = [(-400, 775), (-250, 795), (-50, 815), (150, 830), (300, 842),
             (420, 850), (470, 853)]
# Hood leading edge shut line (front view, y/z): over the grille, then along
# the top edge of the headlight (the 8V headlights sit under the hood edge)
HOOD_FRONT = [(0, 727), (300, 725), (392, 716), (445, 702), (600, 717), (750, 733),
              (850, 743)]

# hood rear edge (top view): ~45 mm ahead of the windscreen base; the strip
# between them is the black cowl panel
HOOD_REAR = [(-306, 0), (-322, 300), (-370, 600), (-400, 775)]

# Windscreen (top view x/y outline, one side, base -> pillar -> header)
WINDSCREEN = [(-350, 0), (-365, 300), (-400, 600), (-440, 760), (-1195, 520),
              (-1280, 500), (-1315, 300), (-1322, 0)]
# Wheel arch openings: circles about the wheel centres (rim-lip edge of the
# red side photo mask: front r 358-367, rear r 333-357, tighter behind the
# wheel)
ARCH_CZ = 306
ARCH_R = 362          # front
ARCH_R_REAR = 352


# --------------------------------------------------------------------------
# Geometry builders
# --------------------------------------------------------------------------

def _mm(p):
    return np.asarray(p, float) * 1e-3


def thick_polyline(pts, width):
    """Closed 2D polygon around an open polyline (constant width)."""
    p = np.asarray(pts, float)
    n = len(p)
    left, right = [], []
    for i in range(n):
        a = p[max(i - 1, 0)]
        b = p[min(i + 1, n - 1)]
        t = b - a
        t /= np.linalg.norm(t)
        nrm = np.array([-t[1], t[0]])
        left.append(p[i] + nrm * width / 2)
        right.append(p[i] - nrm * width / 2)
    # extend the ends slightly so cuts run out cleanly
    return np.array(left + right[::-1])


def annulus_prism(name, outer, inner, y0, depth, col, material=None):
    """Closed ring-shaped prism (outline band) in the XZ plane along Y."""
    outer = np.asarray(outer, float)
    inner = np.asarray(inner, float)
    n = len(outer)
    verts = []
    for y in (y0, y0 + depth):
        verts += [(a, y, b) for a, b in outer]
        verts += [(a, y, b) for a, b in inner]
    o0, i0, o1, i1 = 0, n, 2 * n, 3 * n
    faces = []
    for k in range(n):
        j = (k + 1) % n
        faces.append((o0 + k, o0 + j, i0 + j, i0 + k))        # bottom
        faces.append((o1 + k, i1 + k, i1 + j, o1 + j))        # top
        faces.append((o0 + k, o1 + k, o1 + j, o0 + j))        # outer wall
        faces.append((i0 + k, i0 + j, i1 + j, i1 + k))        # inner wall
    ob = mesh.object_from_pydata(name, verts, faces, col, material, smooth=False)
    mesh.recalc_normals(ob)
    return ob


def mirror_outline(half, axis=1):
    """Make a full symmetric outline from a half outline ending on the axis."""
    h = np.asarray(half, float)
    m = h[::-1].copy()
    m[:, axis] *= -1
    full = np.vstack([h, m[1:-1]]) if abs(h[0, axis]) < 1e-9 and abs(h[-1, axis]) < 1e-9 \
        else np.vstack([h, m])
    return full


def side_prism(name, poly_mm, y0, y1, col, both=True, material=None):
    """Prism of an XZ outline extruded along Y between y0 and y1 (m, >0)."""
    p = _mm(poly_mm)
    obs = [mesh.extrude_polygon(name + ".L", p, y1 - y0, plane="XZ", offset=y0,
                                collection=col, material=material)]
    if both:
        obs.append(mesh.extrude_polygon(name + ".R", p, y1 - y0, plane="XZ", offset=-y1,
                                        collection=col, material=material))
    return obs


def top_prism(name, poly_mm, z0, z1, col, material=None):
    return mesh.extrude_polygon(name, _mm(poly_mm), z1 - z0, plane="XY", offset=z0,
                                collection=col, material=material)


def rear_prism(name, poly_mm, x0, x1, col, material=None):
    return mesh.extrude_polygon(name, _mm(poly_mm), x1 - x0, plane="YZ", offset=x0,
                                collection=col, material=material)


def arch_cutter(name, xc, col, material=None, y0=0.55, y1=1.2, r=None):
    obs = []
    r = (r or ARCH_R) * 1e-3
    for side in (1, -1):
        ob = mesh.revolve(name + (".L" if side > 0 else ".R"),
                          np.array([[r, 0.0], [r, y1 - y0]]),
                          segments=96, axis="Y",
                          center=(xc, y0 if side > 0 else -y1, ARCH_CZ * 1e-3),
                          collection=col, material=material, smooth=False)
        # cap the cylinder into a closed solid
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
        bm.free()
        obs.append(ob)
    return obs


def window_cutters(col, material=None):
    obs = []
    obs += side_prism("Cut_DLO", DLO_SIDE, 0.55, 1.2, col, material=material)
    obs += side_prism("Cut_Sail", SAIL, 0.6, 1.2, col, material=material)
    ws = mirror_outline(WINDSCREEN)
    obs.append(top_prism("Cut_Windscreen", ws, 0.90, 1.60, col, material=material))
    return obs


def clip_to_arches(line_mm, clearance=1.0):
    """Shorten a side-view polyline (mm) so that it stops `clearance` mm
    before entering a wheel-arch opening: the gap and the arch cutters then
    never overlap (overlapping cutters make the EXACT solver fail, v0.3)."""
    p = np.asarray(line_mm, float)
    arches = ((0.0, ARCH_R), (-2636.0, ARCH_R_REAR))

    def outside(q):
        return all(np.hypot(q[0] - xc, q[1] - ARCH_CZ) > r + clearance for xc, r in arches)

    def clip_end(pts):
        # walk from the end towards the start while inside an arch
        k = len(pts) - 1
        while k > 0 and not outside(pts[k]):
            k -= 1
        if k == len(pts) - 1:
            return pts
        a, b = pts[k], pts[k + 1]
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if outside(a + (b - a) * mid):
                lo = mid
            else:
                hi = mid
        return np.vstack([pts[:k + 1], a + (b - a) * lo])

    p = clip_end(p)
    p = clip_end(p[::-1])[::-1]
    return p


def gap_cutters(col, material=None):
    g = GAP
    obs = []
    for nm, line in (("FD_Front", FRONT_DOOR_FRONT), ("Door_Bottom", DOOR_BOTTOM),
                     ("B_Gap", B_GAP), ("RD_Rear", REAR_DOOR_REAR),
                     ("Fender_Rear", FENDER_REAR),
                     ("FB_Split", FRONT_BUMPER_SPLIT), ("RB_Split", REAR_BUMPER_SPLIT)):
        obs += side_prism("Gap_" + nm, thick_polyline(clip_to_arches(catmull_rom(line, 6)), g),
                          0.62, 1.2, col, material=material)
    # door handle recesses
    for k, (cx, cz) in enumerate(HANDLE_RECESSES):
        a, b = HANDLE_RECESS_AXES
        th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
        ell = np.stack([cx + a * np.cos(th), cz + b * np.sin(th)], 1)
        obs += side_prism(f"Cut_HandleRecess_{k}", ell, 0.70, 1.2, col, material=material)
    # fuel door (right side only)
    fd = FUEL_DOOR
    rect = [(fd["cx"] - fd["w"] / 2, fd["cz"] - fd["h"] / 2), (fd["cx"] + fd["w"] / 2, fd["cz"] - fd["h"] / 2),
            (fd["cx"] + fd["w"] / 2, fd["cz"] + fd["h"] / 2), (fd["cx"] - fd["w"] / 2, fd["cz"] + fd["h"] / 2)]
    outer = rounded_polygon(rect, fd["r"], 8)
    inner = mesh.polyline_offset_2d(outer, -g if mesh.polygon_area(outer) > 0 else g, closed=True)
    obs.append(annulus_prism("Gap_FuelDoor", _mm(outer), _mm(inner), -1.2, 0.55, col,
                             material=material))
    # hood side lines (top view) both sides
    hs = catmull_rom(HOOD_SIDE, 6)
    for side in (1, -1):
        p = hs.copy()
        p[:, 1] *= side
        obs.append(top_prism("Gap_HoodSide" + (".L" if side > 0 else ".R"),
                             thick_polyline(p, g), 0.60, 1.05, col, material=material))
    # hood front (front view y/z)
    half = np.asarray(HOOD_FRONT, float)
    full = np.vstack([half[::-1] * [-1, 1], half[1:]])
    obs.append(rear_prism("Gap_HoodFront", thick_polyline(catmull_rom(full, 6), g),
                          0.60, 1.00, col, material=material))
    # tailgate (rear view)
    # top-view gaps across the roof (tailgate top) and the hood rear edge
    for nm, half in (("Gap_HoodRear", HOOD_REAR),):
        h = np.asarray(half, float)
        full = np.vstack([h[::-1] * [1, -1], h[1:]])
        obs.append(top_prism(nm, thick_polyline(catmull_rom(full, 6), g), 0.70, 1.60, col,
                             material=material))
    return obs


def ribbon_cutter(name, P, N, width, depth, col, material=None, closed=True):
    """Closed solid of constant width *measured on the surface* around a 3D
    curve P (with skin normals N): a rectangular tube, width across the curve
    in the tangent plane, depth along the normal (half outside, half inside).
    Unlike a prism along a fixed axis it does not widen where the skin is
    oblique to the projection direction."""
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    # drop (near) duplicate consecutive points: zero-length tangents give
    # NaN frames and a broken (non-manifold) cutter
    keep = [0]
    for i in range(1, len(P)):
        if np.linalg.norm(P[i] - P[keep[-1]]) > 5e-4:
            keep.append(i)
    if closed and len(keep) > 2 and np.linalg.norm(P[keep[-1]] - P[keep[0]]) < 5e-4:
        keep.pop()
    P, N = P[keep], N[keep]
    # smooth the normals along the curve (facet normals jump between faces)
    Ns = N.copy()
    for _ in range(3):
        Ns[1:-1] = (Ns[:-2] + 2 * Ns[1:-1] + Ns[2:]) / 4
    N = Ns / np.linalg.norm(Ns, axis=1)[:, None]
    n = len(P)
    rows = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t /= np.linalg.norm(t) + 1e-12
        nn = N[i] - np.dot(N[i], t) * t
        nn /= np.linalg.norm(nn) + 1e-12
        b = np.cross(nn, t)
        w, d = width / 2, depth / 2
        rows.append([P[i] - b * w - nn * d, P[i] + b * w - nn * d, P[i] + b * w + nn * d,
                     P[i] - b * w + nn * d])
    grid = np.array(rows)
    ob = mesh.grid_object(name, grid, closed_u=closed, closed_v=True, collection=col,
                          material=material, smooth=False, cap_u=not closed)
    mesh.recalc_normals(ob)
    return ob


def gap_cutters_local(surf, col, material=None):
    """Gaps whose straight prisms would also hit other surfaces or widen on
    oblique skin: projected onto the skin and cut with a surface ribbon."""
    obs = []
    for nm, P, N, closed in tailgate_gap_curves(surf):
        obs.append(ribbon_cutter(nm, P, N, GAP * 1e-3, 0.03, col, material, closed=closed))
    obs += tailgate_top_cutters(col, material)
    return obs


# --------------------------------------------------------------------------
# Front-end openings (front view y/z, left half, mm). Digitised by ray casting
# the calibrated white S line photo onto the model skin
# (tools/raycast_photo.py, reference/match_sline_front.json).
# --------------------------------------------------------------------------

# Singleframe grille (pre-facelift: upper corners chamfered), half outline
# from the top centre round the outer edge to the bottom centre.
# v0.2 (sline_front + yellow, joint solve with the yellow car's +23 mm ride
# height): the whole front end sits ~35-45 mm higher than in v0.1.
GRILLE = [(0, 718), (330, 716), (392, 709), (430, 672), (425, 600), (410, 500),
          (390, 400), (366, 335), (340, 308), (300, 299), (0, 294)]
# Headlight (Xenon plus): it wraps round the front corner (inner tip at
# y 0.44 next to the grille chamfer, upper rear corner at x 0.45 on the
# fender), so it is given as approximate 3D points (x, y, z) that are
# projected onto the skin along the oblique direction of HEADLIGHT_AZ.
HEADLIGHT_3D = [
    (795, 445, 694), (770, 520, 703), (730, 600, 713), (670, 690, 724),
    (600, 765, 731), (530, 820, 737), (472, 846, 738), (460, 856, 726),
    (470, 863, 700), (500, 867, 670), (548, 865, 644), (610, 840, 628),
    (680, 790, 614), (735, 720, 605), (775, 640, 604), (800, 560, 607),
    (808, 515, 612), (806, 490, 628), (802, 468, 655), (798, 452, 678),
]
HEADLIGHT_AZ = 38.0     # deg: projection direction (cos a, sin a, 0)
# S line side air intake (fog lamp housing), closed outline, left side
# v0.3: re-digitised on sline_front (ray casts on the v0.3 skin, checked on
# yellow.jpg <= 8 px): bottom edge ~25 mm higher and the outer side ~20 mm
# further out than v0.2.
SIDE_INTAKE = [(479, 424), (600, 436), (700, 445), (790, 446), (827, 444), (856, 425),
               (868, 395), (872, 329), (866, 290), (859, 273), (800, 272), (741, 273),
               (620, 270), (517, 268), (450, 282), (423, 303), (440, 340), (452, 364)]
# headlight washer cover (front view y/z outline, S): a rounded parallelogram
WASHER_COVER_YZ = [(640, 485), (642, 541), (744, 545), (738, 491)]
FOG_CENTRE = (795, 386)  # fog lamp centre (y, z), S (sline_front ray casts)
FOG_SIZE = (88, 46)      # (w, h) mm, S
# S line intake blade (gloss black): from the pointed inner tip on the bumper
# face next to the grille, rising slightly outwards (y, z mm, S)
BLADE = [(359, 348), (450, 355), (630, 364), (741, 378), (816, 386), (863, 389)]
BLADE_Z = 360            # (v0.2, kept for reference)
FRONT_SENSORS = [(726, 777, 500)]   # (x, y, z) outer front parking sensor, S
# S line bumper side "air curtain" inset (side view x/z, S): recessed painted
# panel at the outer corner of the bumper ahead of the wheel
SIDE_VENT_XZ = [(614, 446), (542, 448), (434, 441), (443, 394), (447, 341), (452, 286),
                (465, 263), (502, 268), (563, 359), (595, 411)]
RINGS_Z = 632            # front rings centre
PLATE_Z = 460            # front plate centre


def front_view_cutter(name, surf, outline_yz_mm, col, material=None, depth_in=0.09,
                      depth_out=0.06, closed=True, mirror=False):
    """Cutter following the skin: the outline is ray cast onto the skin from
    the front and extruded locally along X (in front of / behind the skin)."""
    from .surftools import Surface  # noqa (type hint only)
    pts = np.asarray(outline_yz_mm, float) * 1e-3
    if mirror:
        pts = pts * [-1, 1]
    from ..core.curves import catmull_rom, resample
    dense = resample(catmull_rom(pts, 6, closed=closed), 160, closed=closed)
    P, N = surf.project(dense, "YZ", side=1)
    P = np.array([p for p in P if p is not None])
    return local_prism(name, P, np.array([1.0, 0, 0]), depth_in, depth_out, col, material)


def local_prism(name, P, d, depth_in, depth_out, col, material=None):
    """Closed solid from a 3D loop P extruded along direction d."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    n = len(P)
    outer = P + d * depth_out
    inner = P - d * depth_in
    verts = list(map(tuple, outer)) + list(map(tuple, inner))
    co, ci = outer.mean(0), inner.mean(0)
    verts += [tuple(co), tuple(ci)]
    a, b = 2 * n, 2 * n + 1
    faces = []
    for k in range(n):
        j = (k + 1) % n
        faces.append((k, j, n + j, n + k))
        faces.append((a, j, k))
        faces.append((b, n + k, n + j))
    ob = mesh.object_from_pydata(name, verts, faces, col, material, smooth=False)
    mesh.recalc_normals(ob)
    return ob


def headlight_dir(mirror=False):
    a = np.radians(HEADLIGHT_AZ)
    return np.array([np.cos(a), -np.sin(a) if mirror else np.sin(a), 0.0])


def headlight_outline(surf, mirror=False, n=220):
    """Headlight outline on the skin (3D, closed), projected along the
    oblique direction from the approximate 3D points."""
    from ..core.curves import catmull_rom, resample
    from mathutils import Vector
    pts = np.asarray(HEADLIGHT_3D, float) * 1e-3
    if mirror:
        pts = pts * [1, -1, 1]
    dense = resample(catmull_rom(pts, 6, closed=True), n, closed=True)
    d = headlight_dir(mirror)
    out = []
    for p in dense:
        hit = surf.bvh.ray_cast(Vector(p + d * 0.4), Vector(-d), 0.8)
        if hit[0] is not None:
            out.append(np.array(hit[0][:]))
    return np.array(out)


def headlight_cutter(name, surf, col, material=None, mirror=False, depth_in=0.16,
                     depth_out=0.06):
    P = headlight_outline(surf, mirror)
    return local_prism(name, P, headlight_dir(mirror), depth_in, depth_out, col, material)


def front_cutters(surf, col, material=None):
    obs = []
    g = np.asarray(GRILLE, float)
    full = np.vstack([g, (g[::-1] * [-1, 1])[1:-1]])
    obs.append(front_view_cutter("Cut_Grille", surf, full, col, material, depth_in=0.12))
    for side, sfx in ((False, ".L"), (True, ".R")):
        obs.append(headlight_cutter("Cut_Headlight" + sfx, surf, col, material, mirror=side))
        obs.append(front_view_cutter("Cut_Intake" + sfx, surf, SIDE_INTAKE, col, material,
                                     depth_in=0.10, mirror=side))
    obs += side_prism("Cut_SideVent", SIDE_VENT_XZ, 0.80, 1.0, col, material=material)
    return obs


# --------------------------------------------------------------------------
# Rear-end openings, digitised by ray casting the calibrated rear 3/4 photo
# (reference/match_sline_rear.json) onto the skin.  Left side, mm.
# --------------------------------------------------------------------------

# S line diffuser (rear view, half outline, top edge from the side to centre)
DIFFUSER = [(0, 394), (280, 392), (500, 392), (640, 390), (690, 378), (731, 343), (766, 316),
            (792, 290), (805, 240), (0, 240)]
# v0.3: top edge of the black insert ray cast on sline_rear (centre z 0.392-0.398,
# outer end dropping to z 0.316 at y 0.766), checked on yellow_rear.
# twin round tail pipes on the LEFT (2.0 TDI S line), centres (y, z) and
# diameter (v0.3: triangulated sline_rear + yellow_rear, y 0.466 / 0.553,
# z 0.270 / 0.274)
EXHAUST_TIPS = [(466, 272), (553, 274)]
EXHAUST_D = 80

# --------------------------------------------------------------------------
# v0.3 rear end: 3D outlines (x, y, z mm, left side) measured by ray casting the
# calibrated sline_rear photo onto the v0.3 skin (tools/raycast_skin.py) and
# checked by re-projection into yellow_rear and rearsq (<= 10-12 px, the yellow
# car rides 24 mm higher).  Projected onto the skin from an eye point, so that
# cutters follow the wrap-around of the rear corners.
# --------------------------------------------------------------------------

REAR_EYE = (-6.5, 0.0, 1.9)          # projection centre for glass / tailgate
LAMP_EYE = (-5.2, 3.4, 0.95)         # projection centre for the left tail lamp

# Tail lamp outline (left), from the outer front-top corner along the top edge
# to the inner tip and back along the lower edge.  The tailgate shut line splits
# it into the outer (body) and inner (tailgate) units.
TAILLIGHT_3D = [
    (-2983, 777, 908), (-3091, 738, 923), (-3201, 654, 928), (-3284, 542, 930),
    (-3322, 433, 928), (-3330, 401, 922), (-3339, 346, 867), (-3337, 358, 851),
    (-3321, 477, 822), (-3297, 584, 792), (-3283, 622, 772), (-3204, 718, 773),
    (-3126, 769, 779), (-3068, 802, 793), (-3031, 799, 821), (-2986, 786, 878),
]

# Rear glass: the side edges and the bottom edge run on the K7 crease (the
# glass is bonded flush; its edge is the tailgate shut line above the glass
# corner).  Top edge hidden under the roof spoiler (E): from the spoiler end
# (trailing-edge end x -2.795, y 0.60, z 1.268, sline_rear/rearsq) to the
# centre under the spoiler.
REAR_GLASS_TOP = [(-2800, 592, 1290), (-2880, 540, 1290), (-2990, 450, 1290),
                  (-3100, 320, 1290), (-3190, 160, 1288), (-3215, 0, 1287)]
REAR_GLASS_X = (-2800, -3095)        # x range of the K7 part (side edge, top -> bottom corner)
# bottom edge from the corner to the centre (sline_rear glass bottom, z 1.025-1.034)
REAR_GLASS_BOTTOM = [(-3095, 640, 1025), (-3180, 560, 1028), (-3260, 420, 1031),
                     (-3310, 220, 1033), (-3325, 0, 1034)]
REAR_GLASS_INSET = 5.0               # mm inside the K7 crease

# Tailgate shut line below the glass: glass bottom corner -> lamp top (split)
# -> through the lamp -> lamp bottom -> tailgate lower corner -> bottom edge.
TAILGATE_LOW = [(-3112, 660, 1015), (-3161, 653, 975), (-3204, 650, 931),
                (-3289, 603, 795), (-3294, 595, 779), (-3310, 564, 728),
                (-3323, 536, 686), (-3334, 507, 657), (-3346, 466, 647),
                (-3364, 276, 642), (-3368, 0, 640)]
# Roof / tailgate seam (spoiler front edge) across the roof and its outer end
# where the spoiler end meets the glass edge.  End point S (rearsq + sline_rear
# agree within 1 px), centre E (x behind the roof fin antenna at -2.54).
TAILGATE_SEAM = [(-2700, 0, 1381), (-2700, 300, 1366), (-2706, 420, 1354), (-2720, 500, 1342),
                 (-2742, 578, 1323)]
SPOILER_END = [(-2742, 578, 1323), (-2760, 590, 1306), (-2785, 592, 1290)]
SPOILER_TE = [(-3160, 0, 1312), (-3130, 250, 1310), (-3060, 400, 1303), (-2960, 500, 1292),
              (-2860, 560, 1278), (-2795, 600, 1268)]


def _eye_dirs(P, eye):
    d = P - np.asarray(eye, float)
    return d / np.linalg.norm(d, axis=1)[:, None]


def project_from(surf, pts, eye, inset=0.0):
    """Ray cast 3D points (m) onto the skin from an eye point; returns hits and
    normals (missing hits dropped)."""
    from mathutils import Vector
    eye = np.asarray(eye, float)
    P, N = [], []
    for p in np.asarray(pts, float):
        d = p - eye
        L = np.linalg.norm(d)
        hit = surf.bvh.ray_cast(Vector(eye), Vector(d / L), L + 1.0)
        if hit[0] is not None:
            P.append(np.array(hit[0][:]))
            N.append(np.array(hit[1][:]))
    return np.array(P), np.array(N)


def persp_cutter(name, P, eye, near, far, col, material=None):
    """Closed solid around a 3D loop P lying on the skin, seen from `eye`: a
    cone from an apex between the eye and the skin through the loop (pushed
    `near` towards the eye), ending `far` beyond the skin.  The near side is
    the cone apex (not a fan through the loop centroid, which would lie inside
    the car for loops that wrap round a corner)."""
    P = np.asarray(P, float)
    eye = np.asarray(eye, float)
    D = _eye_dirs(P, eye)
    dist = np.linalg.norm(P - eye, axis=1)
    md = D.mean(0)
    md /= np.linalg.norm(md)
    apex = eye + md * max(0.2, dist.min() - near - 0.35)
    outer = P - D * near
    inner = P + D * far
    n = len(P)
    verts = list(map(tuple, outer)) + list(map(tuple, inner))
    verts += [tuple(apex), tuple(np.mean(inner, 0))]
    a, b = 2 * n, 2 * n + 1
    faces = []
    for k in range(n):
        j = (k + 1) % n
        faces.append((k, j, n + j, n + k))
        faces.append((a, j, k))
        faces.append((b, n + k, n + j))
    ob = mesh.object_from_pydata(name, verts, faces, col, material, smooth=False)
    mesh.recalc_normals(ob)
    return ob


def slab_cutter(name, surf, P, eye, col, material=None, delta=0.006, nr=40):
    """Closed slab of thickness 2*delta that follows the skin inside the loop
    P (3D points on the skin, seen from `eye`): a grid is built inside the
    loop by interpolating the viewing directions from the loop's mean
    direction to each boundary point, ray cast onto the skin and offset by
    +-delta along the skin normal.  Unlike a cone from the eye it never
    grazes the skin next to a wrap-around opening (rear glass, tail lamps)."""
    from mathutils import Vector
    P = np.asarray(P, float)
    eye = np.asarray(eye, float)
    D = _eye_dirs(P, eye)
    c = D.mean(0)
    c /= np.linalg.norm(c)
    n = len(P)
    rs = np.linspace(0.0, 1.0, nr) ** 0.8
    G = np.zeros((nr, n, 3))
    Nn = np.zeros((nr, n, 3))
    for i, r in enumerate(rs):
        for k in range(n):
            if i == nr - 1:
                hit = surf.bvh.find_nearest(Vector(P[k]))
                G[i, k] = P[k]
                Nn[i, k] = np.array(hit[1][:]) if hit[0] is not None else -D[k]
                continue
            d = c + r * (D[k] - c)
            d /= np.linalg.norm(d)
            hit = surf.bvh.ray_cast(Vector(eye), Vector(d), 20.0)
            if hit[0] is None:
                G[i, k] = G[i - 1, k] if i else P[k]
                Nn[i, k] = Nn[i - 1, k] if i else -D[k]
            else:
                G[i, k] = np.array(hit[0][:])
                Nn[i, k] = np.array(hit[1][:])
    # orient normals towards the eye and smooth them a little
    flip = ((G - eye) * Nn).sum(-1) > 0
    Nn[flip] *= -1
    for _ in range(2):
        Nn[1:-1] = (Nn[:-2] + 2 * Nn[1:-1] + Nn[2:]) / 4
        Nn = (np.roll(Nn, 1, 1) + 2 * Nn + np.roll(Nn, -1, 1)) / 4
    Nn /= np.linalg.norm(Nn, axis=-1)[..., None]
    outer = G + Nn * delta
    inner = G - Nn * delta
    verts = np.vstack([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    off = nr * n
    faces = []
    for i in range(nr - 1):
        for k in range(n):
            j = (k + 1) % n
            a, b, cc, d = i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k
            faces.append((a, b, cc, d))
            faces.append((off + d, off + cc, off + b, off + a))
    i = nr - 1
    for k in range(n):
        j = (k + 1) % n
        faces.append((i * n + k, off + i * n + k, off + i * n + j, i * n + j))
    ob = mesh.object_from_pydata(name, verts, faces, col, material, smooth=False)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-8)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def _k7_edge(bl=None):
    """Points (m) of the K7 crease from the glass top corner round the bottom
    corner to the centre (left side)."""
    from .surface import BodyLines
    bl = bl or BodyLines()
    xs = np.linspace(REAR_GLASS_X[0] * 1e-3, REAR_GLASS_X[1] * 1e-3, 60)
    K = bl.keypoints(xs)
    w, z = K["K7"]
    return np.stack([xs, w, z], 1)


def rear_glass_outline(surf, inset=None, n=360):
    """Closed rear glass outline on the skin (both sides), inset from K7."""
    from ..core.curves import catmull_rom, resample
    inset = REAR_GLASS_INSET if inset is None else inset
    edge = _k7_edge()                                       # top corner -> bottom corner
    bottom = np.asarray(REAR_GLASS_BOTTOM, float) * 1e-3     # bottom corner -> centre
    top = np.asarray(REAR_GLASS_TOP, float) * 1e-3          # corner -> centre top
    half = np.vstack([top[::-1], edge[1:-1], bottom])       # centre top -> corners -> centre bottom
    other = half[::-1] * [1, -1, 1]
    loop = np.vstack([half[:-1], other[:-1]])
    loop = resample(catmull_rom(loop, 4, closed=True), n, closed=True)
    # inset in the eye's image plane: move every point towards the loop centre
    # (as seen from the eye) by `inset` mm measured at the point's distance
    eye = np.asarray(REAR_EYE, float)
    c = loop.mean(0)
    D = _eye_dirs(loop, eye)
    lat = c - loop
    lat -= (lat * D).sum(1)[:, None] * D
    lat /= np.linalg.norm(lat, axis=1)[:, None] + 1e-12
    loop = loop + lat * inset * 1e-3
    P, N = project_from(surf, loop, eye)
    return P, N


def rear_glass_cutter(name, surf, col, material=None, inset=None, delta=0.006):
    P, N = rear_glass_outline(surf, inset)
    return slab_cutter(name, surf, P, REAR_EYE, col, material, delta=delta)


def taillight_outline(surf, mirror=False, n=200, grow=0.0):
    from ..core.curves import catmull_rom, resample
    pts = np.asarray(TAILLIGHT_3D, float) * 1e-3
    eye = np.asarray(LAMP_EYE, float)
    if mirror:
        pts = pts * [1, -1, 1]
        eye = eye * [1, -1, 1]
    loop = resample(catmull_rom(pts, 6, closed=True), n, closed=True)
    if grow:
        c = loop.mean(0)
        D = _eye_dirs(loop, eye)
        lat = loop - c
        lat -= (lat * D).sum(1)[:, None] * D
        lat /= np.linalg.norm(lat, axis=1)[:, None] + 1e-12
        loop = loop + lat * grow
    P, N = project_from(surf, loop, eye)
    return P, N, eye


def taillight_cutter(name, surf, col, material=None, mirror=False, delta=0.006, grow=0.0):
    P, N, eye = taillight_outline(surf, mirror, grow=grow)
    return slab_cutter(name, surf, P, eye, col, material, delta=delta)


def tailgate_gap_curves(surf):
    """(name, P, N, closed) curves of the tailgate shut lines on the skin."""
    from mathutils import Vector
    from ..core.curves import catmull_rom, resample
    out = []
    # lower shut line, both sides joined across the bottom
    # split at the tail lamps: the lamp cutter removes the part in between and
    # the two cutters must not overlap (EXACT solver)
    low = np.asarray(TAILGATE_LOW, float) * 1e-3
    upper = low[:3].copy()
    upper[-1] = upper[-1] + (upper[-2] - upper[-1]) * (0.004 / np.linalg.norm(upper[-2] - upper[-1]))
    lower = low[3:].copy()
    lower[0] = lower[0] + (lower[1] - lower[0]) * (0.004 / np.linalg.norm(lower[1] - lower[0]))
    for nm, part, closed in (("Gap_TailgateUpper.L", upper, False),
                             ("Gap_TailgateUpper.R", upper * [1, -1, 1], False)):
        P, N = project_from(surf, resample(catmull_rom(part, 8), 40), REAR_EYE)
        out.append((nm, P, N, closed))
    full = np.vstack([lower, (lower[::-1] * [1, -1, 1])[1:]])
    P, N = project_from(surf, resample(catmull_rom(full, 8), 300), REAR_EYE)
    out.append(("Gap_TailgateLow", P, N, False))
    return out


def tailgate_top_cutters(col, material=None):
    """Roof / tailgate seam (prism from above across the roof) and the short
    shut lines down the spoiler ends (prisms from the side): closed prisms are
    robust in the EXACT solver; a surface ribbon twisting round the roof
    corner was not."""
    seam = np.asarray(TAILGATE_SEAM, float)
    half = seam[:, :2]
    full = np.vstack([half[::-1] * [1, -1], half[1:]])
    obs = [top_prism("Gap_TailgateTop", thick_polyline(catmull_rom(full, 6), GAP), 1.28, 1.50, col,
                     material=material)]
    end = np.asarray(SPOILER_END, float)
    line = np.vstack([end[:, [0, 2]], end[-1:, [0, 2]] + [-30, -25]])
    obs += side_prism("Gap_SpoilerEnd", thick_polyline(catmull_rom(line, 6), GAP), 0.50, 0.80,
                      col, material=material)
    return obs



def rear_cutters(surf, col, material=None):
    obs = []
    obs.append(rear_glass_cutter("Cut_RearWindow", surf, col, material))
    for mirror, sfx in ((False, ".L"), (True, ".R")):
        obs.append(taillight_cutter("Cut_Taillight" + sfx, surf, col, material, mirror=mirror))
    g = np.asarray(DIFFUSER, float)
    full = np.vstack([g[:-1], (g[::-1] * [-1, 1])[1:-1]])
    # straight prism along X restricted to the bumper's rear face region
    obs.append(mesh.extrude_polygon("Cut_Diffuser", full * 1e-3, 0.24, plane="YZ",
                                    offset=-3.60, collection=col, material=material))
    return obs
