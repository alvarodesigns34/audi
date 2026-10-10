"""Characteristic lines of the A3 Sportback 8V body (S line), in millimetres.

The outer skin is described by a set of key points K0..K8 per transverse
section (constant x).  Each key point traces a longitudinal "characteristic
line" whose half-width w(x) and height z(x) are tabulated here.  Going round a
half section (+Y side) from the bottom centre line to the roof centre line:

    K0  underbody centre             (0, zBot)
    K1  underbody outer edge          floor pan -> sill radius
    K2  sill / bumper lower corner
    K3  rocker (side skirt) face
    K4  lower body, ~max width        (bumper corners at the ends)
    K5  "tornado" shoulder crease     (wraps onto the hood leading edge and
                                       the tailgate crease at the ends)
    K6  belt line / glass base        (on the hood and tailgate at the ends)
    K7  roof edge / glass top         (A-pillar and D-pillar edges)
    K8  roof centre                   (0, zTop)

Sources: overall dimensions from a3.spec (C); all other numbers are
estimates (E) taken from photographs of 8V Sportbacks and refined by
camera-matched overlays (see tools/camera_match.py).  X is measured from
the front axle (+ forward), Z from the ground (S line sport suspension).
"""


import numpy as _np


def plan_end(x_tip, w_max, depth, m=3.2, n=1.4, samples=14, rear=False):
    """Plan-view end rounding (superellipse-like), returns [(x_mm, w_mm)].

    dx/depth = 1 - (1 - (w/w_max)^m)^(1/n): flat across the middle, tight
    radius at the corners - matches the 8V bumper plan shape.
    """
    out = []
    for t in _np.linspace(0.0, 1.0, samples):
        w = w_max * t
        dx = depth * (1.0 - (1.0 - t ** m) ** (1.0 / n))
        out.append((x_tip + dx if rear else x_tip - dx, w))
    return out


def merged(front, mid, rear):
    """Join front-end, mid-body and rear-end tables (all sorted by x desc)."""
    pts = {}
    for x, v in front + mid + rear:
        pts[round(x, 3)] = v
    return sorted(pts.items(), key=lambda t: -t[0])

# Split stations: the central body is lofted from transverse sections between
# these planes; beyond them the nose and tail are closed by EndCap surfaces.
X_FRONT_SPLIT = 600
X_REAR_SPLIT = -3080

FRONT_CAP = dict(
    centre_z=455,          # nose point height (bumper/plate centre)
    rings=90,
    # plan rounding exponents vs height z (mm): g(u) = (1-u^m)^(1/n)
    plan_m=[(150, 2.6), (300, 3.0), (500, 3.2), (700, 2.8), (800, 2.4)],
    plan_n=[(150, 1.5), (500, 1.4), (800, 1.5)],
)
REAR_CAP = dict(
    centre_z=600,
    rings=90,
    plan_m=[(200, 3.0), (400, 4.2), (800, 4.2), (1000, 3.0), (1350, 2.4)],
    plan_n=[(200, 1.5), (700, 1.4), (1350, 1.6)],
)

# Centre-line silhouette, top (zTop) ------------------------------------------
Z_TOP = [
    (869, 455), (867, 520), (862, 580), (853, 638), (840, 690), (824, 726),
    (808, 742), (790, 752), (760, 760), (700, 772), (600, 790), (400, 822),
    (200, 855), (0, 886), (-200, 916), (-310, 933), (-360, 945),
    (-600, 1062), (-800, 1158), (-1000, 1244), (-1150, 1302), (-1280, 1345),
    (-1350, 1366), (-1500, 1393), (-1750, 1408), (-2100, 1407), (-2500, 1392),
    (-2850, 1366), (-3080, 1344), (-3160, 1332), (-3195, 1312), (-3240, 1238),
    (-3290, 1150), (-3330, 1080), (-3348, 1058), (-3372, 1030), (-3392, 990),
    (-3410, 935), (-3424, 860), (-3433, 780), (-3438, 700), (-3440, 640),
    (-3441, 570),
]

# Centre-line silhouette, bottom (zBot) ---------------------------------------
Z_BOT = [
    (869, 455), (868, 400), (864, 340), (856, 285), (842, 240), (820, 208),
    (790, 192), (700, 182), (500, 165), (300, 150), (0, 140), (-400, 132),
    (-2400, 132), (-2750, 150), (-3000, 185), (-3150, 210), (-3300, 222),
    (-3380, 232), (-3415, 262), (-3430, 320), (-3437, 420), (-3440, 520),
    (-3441, 570),
]

# Key point lines: name -> (w table, z table) ------------------------------------
K1_W = merged(plan_end(869, 700, 230, m=2.6, n=1.5), [(300, 700), (-2636, 700)],
              plan_end(-3441, 680, 330, m=2.6, n=1.5, rear=True))
K1_DZ = 12  # floor edge rises 12 mm above zBot

K2_W = merged(plan_end(869, 855, 330, m=3.0, n=1.4), [(300, 855), (-2636, 855)],
              plan_end(-3441, 852, 420, m=3.0, n=1.4, rear=True))
K2_Z = [(869, 455), (867, 395), (861, 330), (845, 265), (805, 228), (720, 215),
        (500, 205), (300, 190), (-400, 178), (-2400, 178), (-2800, 195),
        (-3100, 240), (-3300, 290), (-3400, 330), (-3430, 400), (-3441, 570)]

K3_W = merged(plan_end(869, 884, 330, m=3.2, n=1.4), [(400, 884), (250, 878), (-150, 872),
              (-2400, 872), (-2900, 878)], plan_end(-3441, 880, 400, m=3.2, n=1.4, rear=True))
K3_Z = [(869, 455), (868, 420), (863, 380), (850, 345), (815, 318), (740, 305),
        (300, 285), (0, 262), (-2500, 262), (-2900, 290), (-3200, 330),
        (-3380, 370), (-3430, 450), (-3441, 570)]

K4_W = merged(plan_end(869, 890, 340, m=3.2, n=1.4), [(400, 892), (250, 886), (-150, 880),
              (-1300, 878), (-2250, 882), (-2700, 892)],
              plan_end(-3441, 890, 400, m=3.2, n=1.4, rear=True))
K4_Z = [(869, 455), (860, 470), (820, 495), (700, 510), (300, 520),
        (-1500, 525), (-2600, 540), (-3200, 555), (-3441, 570)]

# Tornado line: headlight top -> fender -> doors -> into the tail lamp; wraps
# across the nose as the hood leading edge, and across the tailgate as the
# lamp-level crease.
K5_W = merged(plan_end(793, 852, 260, m=2.4, n=1.6), [(450, 856), (200, 862), (-300, 868),
              (-1200, 872), (-2300, 880), (-2750, 884)],
              plan_end(-3416, 884, 600, m=2.6, n=1.5, rear=True))
K5_Z = [(793, 752), (780, 752), (745, 750), (700, 745), (640, 740),
        (550, 745), (400, 768), (100, 812), (-300, 852), (-1200, 878),
        (-2300, 895), (-2900, 906), (-3200, 912), (-3350, 905), (-3416, 880)]

# Belt / glass base.  Ahead of the A-pillar it runs on the hood, behind the
# D-pillar on the tailgate (glass lower edge).
K6_W = [(787, 0), (783, 120), (770, 260), (740, 400), (690, 500), (600, 560),
        (300, 600), (0, 640), (-250, 700), (-400, 765), (-470, 792),
        (-800, 803), (-1700, 806), (-2600, 800), (-2950, 782), (-3150, 745),
        (-3270, 680), (-3330, 600), (-3360, 470), (-3378, 260), (-3385, 0)]
K6_Z = [(787, 754), (740, 760), (600, 780), (300, 828), (0, 868),
        (-250, 900), (-400, 935), (-470, 958), (-900, 975), (-1700, 1003),
        (-2600, 1040), (-3000, 1060), (-3200, 1066), (-3330, 1064),
        (-3365, 1040), (-3385, 1000)]

# Roof edge (glass top / drip line). Runs on the hood/cowl ahead of the
# A-pillar base, up the A-pillar, along the roof side, down the D-pillar
# (rear glass side edge) and across the tailgate at the glass bottom.
K7_W = [(780, 0), (775, 70), (760, 150), (720, 230), (650, 290), (400, 330),
        (0, 380), (-300, 470), (-420, 620), (-480, 700), (-560, 704),
        (-800, 690), (-1050, 664), (-1280, 625), (-1500, 618), (-2200, 616),
        (-2700, 606), (-2950, 590), (-3120, 562), (-3220, 540), (-3290, 520),
        (-3320, 505), (-3340, 470), (-3350, 260), (-3352, 0)]
K7_Z = [(780, 756), (700, 768), (400, 815), (0, 875), (-300, 925),
        (-420, 970), (-480, 1000), (-560, 1050), (-800, 1160), (-1050, 1268),
        (-1280, 1336), (-1500, 1356), (-2200, 1356), (-2700, 1340),
        (-2950, 1325), (-3120, 1304), (-3220, 1225), (-3290, 1125),
        (-3330, 1075), (-3352, 1056)]

# Crease strength at K6 / K7 (1 = sharp glass/roof junction, 0 = smooth, e.g.
# on the hood and on the tailgate where those points are only construction
# points of the surface).
K6_CREASE = [(787, 0), (-380, 0), (-470, 1), (-3330, 1), (-3380, 1)]
K7_CREASE = [(780, 0), (-330, 0), (-430, 1), (-3330, 1), (-3352, 1)]

# Segment bulge (fraction of chord, + = convex outward) ------------------------------
BULGE = {
    "K0K1": [(869, 0), (-3441, 0)],
    "K1K2": [(869, 0.12), (-3441, 0.12)],
    "K2K3": [(869, 0.10), (-3441, 0.10)],
    "K3K4": [(869, 0.06), (0, 0.04), (-3441, 0.06)],
    "K4K5": [(869, 0.03), (700, 0.03), (300, 0.0), (-3200, 0.0), (-3441, 0.03)],
    "K5K6": [(869, 0.06), (0, 0.10), (-3441, 0.10)],
    "K6K7": [(869, 0.0), (-450, 0.02), (-3441, 0.02)],
    "K7K8": [(869, 0.0), (-3441, 0.0)],
}

# Samples per segment (topology is identical for every section)
SEG_SAMPLES = {
    "K0K1": 14, "K1K2": 8, "K2K3": 10, "K3K4": 18, "K4K5": 28,
    "K5K6": 14, "K6K7": 22, "K7K8": 26,
}
