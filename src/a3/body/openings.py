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
DLO_SIDE = [
    (-545, 927), (-1000, 949), (-1500, 971), (-2000, 993), (-2400, 1007),
    (-2690, 1016), (-2745, 1021), (-2722, 1058), (-2672, 1118), (-2615, 1183),
    (-2565, 1240), (-2528, 1276), (-2490, 1300), (-2430, 1314), (-2200, 1326),
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
DOOR_BOTTOM = [(-448, 300), (-1000, 305), (-1500, 304), (-1900, 303), (-2062, 302)]
B_GAP = [(-1586, 966), (-1565, 600), (-1544, 298)]
REAR_DOOR_REAR = [(-2440, 1012), (-2468, 945), (-2478, 890), (-2431, 807),
                  (-2384, 682), (-2275, 559), (-2178, 444), (-2100, 355),
                  (-2068, 318), (-2050, 300)]
FRONT_BUMPER_SPLIT = [(540, 628), (470, 574), (410, 520), (350, 470)]
REAR_BUMPER_SPLIT = [(-3260, 830), (-3150, 735), (-3060, 640), (-2995, 540), (-2975, 470)]

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

# Tailgate outline (rear view, y/z), one side, from top to centre bottom
TAILGATE = [(552, 1300), (595, 1160), (640, 1065), (660, 975), (640, 890),
            (598, 800), (560, 728), (505, 672), (380, 674), (0, 678)]

# Windscreen (top view x/y outline, one side, base -> pillar -> header)
WINDSCREEN = [(-350, 0), (-365, 300), (-400, 600), (-440, 760), (-1195, 520),
              (-1280, 500), (-1315, 300), (-1322, 0)]
# Rear window, rear view (y, z) half outline from the top centre round to the
# bottom centre, projected along x (the glass is steep at its corners, so a
# top-view outline does not work).  Bottom corners at |y| 0.69, z 1.045
# (sline_rear/yellow_rear); the top edge hides under the roof spoiler.
REAR_WINDOW_YZ = [(0, 1305), (300, 1302), (520, 1295), (590, 1280), (625, 1230),
                  (655, 1150), (678, 1080), (690, 1046), (660, 1036), (400, 1031),
                  (0, 1029)]
REAR_WINDOW_X = (-3.60, -3.13)   # prism range along x (m)

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
    obs.append(rear_prism("Cut_RearWindow", mirror_outline(REAR_WINDOW_YZ, axis=0),
                          REAR_WINDOW_X[0], REAR_WINDOW_X[1], col, material=material))
    return obs


def gap_cutters(col, material=None):
    g = GAP
    obs = []
    for nm, line in (("FD_Front", FRONT_DOOR_FRONT), ("Door_Bottom", DOOR_BOTTOM),
                     ("B_Gap", B_GAP), ("RD_Rear", REAR_DOOR_REAR),
                     ("FB_Split", FRONT_BUMPER_SPLIT), ("RB_Split", REAR_BUMPER_SPLIT)):
        obs += side_prism("Gap_" + nm, thick_polyline(catmull_rom(line, 6), g), 0.62, 1.2,
                          col, material=material)
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
    tg = np.asarray(TAILGATE, float)
    full = np.vstack([tg, (tg[::-1] * [-1, 1])[1:]])
    obs.append(rear_prism("Gap_Tailgate", thick_polyline(catmull_rom(full, 6), g),
                          -3.60, -3.05, col, material=material))
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
SIDE_INTAKE = [(470, 421), (650, 426), (828, 432), (848, 400), (851, 340),
               (843, 283), (805, 262), (650, 250), (480, 242), (418, 246),
               (432, 300), (452, 370)]
# Headlight washer cover (gap outline), left side
WASHER_COVER = dict(cy=650, cz=510, w=110, h=36, r=16)
FOG_CENTRE = (780, 381)  # fog lamp centre (y, z)
BLADE_Z = 360            # S line intake blade height
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
    return obs


# --------------------------------------------------------------------------
# Rear-end openings, digitised by ray casting the calibrated rear 3/4 photo
# (reference/match_sline_rear.json) onto the skin.  Left side, mm.
# --------------------------------------------------------------------------

# Tail lamp: rear-face part (y, z) from the inner tip outwards along the top,
# then the side part (x, z) and back along the lower edge.
# v0.2: heights from sline_rear (reference car) ray casts, cross-checked on
# yellow_rear (+23 mm ride height) and the side photo.
# S line diffuser (rear view, half outline, top edge from the side to centre)
DIFFUSER = [(0, 378), (300, 378), (560, 376), (660, 372), (710, 355), (742, 320),
            (760, 280), (770, 240), (0, 240)]
# twin round tail pipes on the LEFT (2.0 TDI S line), centres (y, z) and
# diameter: they sit at the outer end of the diffuser (v0.1 had them at
# y 0.27-0.34, far too inboard)
EXHAUST_TIPS = [(490, 285), (570, 285)]
EXHAUST_D = 80


TL_SPLIT_X = -3050   # rear-face part behind, side part ahead of this plane
TAILLIGHT_REAR = [(380, 872), (420, 918), (520, 925), (640, 921), (740, 915),
                  (900, 912), (900, 792), (800, 791), (700, 770), (600, 790),
                  (500, 828), (420, 858)]
TAILLIGHT_SIDE_XZ = [(-3050, 910), (-3000, 905), (-2958, 886), (-2946, 860),
                     (-2960, 830), (-3000, 802), (-3050, 796)]


def taillight_prisms(col, material=None, mirror=False, grow=0.0):
    """Two planar prisms (rear face + side) sharing the plane x = TL_SPLIT_X."""
    xs = TL_SPLIT_X * 1e-3
    rear = np.asarray(TAILLIGHT_REAR, float) * 1e-3
    side = np.asarray(TAILLIGHT_SIDE_XZ, float) * 1e-3
    if grow:
        rear = mesh.polyline_offset_2d(rear, grow if mesh.polygon_area(rear) > 0 else -grow)
    s = -1 if mirror else 1
    sfx = ".R" if mirror else ".L"
    r = mesh.extrude_polygon("Cut_TaillightRear" + sfx, rear * [s, 1], xs + 3.6, plane="YZ",
                             offset=-3.6, collection=col, material=material)
    y0, y1 = (0.70, 1.05) if not mirror else (-1.05, -0.70)
    sd = mesh.extrude_polygon("Cut_TaillightSide" + sfx, side, y1 - y0, plane="XZ",
                              offset=y0, collection=col, material=material)
    return [r, sd]


def rear_cutters(surf, col, material=None):
    obs = []
    for mirror in (False, True):
        obs += taillight_prisms(col, material, mirror)
    g = np.asarray(DIFFUSER, float)
    full = np.vstack([g[:-1], (g[::-1] * [-1, 1])[1:-1]])
    # straight prism along X restricted to the bumper's rear face region
    obs.append(mesh.extrude_polygon("Cut_Diffuser", full * 1e-3, 0.24, plane="YZ",
                                    offset=-3.60, collection=col, material=material))
    return obs
