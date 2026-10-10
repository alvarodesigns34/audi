"""Cabin envelope and hard points of the interior (single source of truth).

Every interior module reads its positions from a ``Layout`` instance obtained
through ``get(ctx)``.  Another part (e.g. the body shell once it exists) may
store a modified copy in ``ctx.data["interior_layout"]`` before the interior is
built, so the whole cabin can be re-fitted without touching the modules.

ISO 8855 axes, metres; origin ground / front-axle centre / car centre-plane.
Status of each value: C confirmed, S secondary source, E estimate.
All hard points below were supplied as estimates by the body modeller (E)
unless a comment says otherwise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np


@dataclass(frozen=True)
class Layout:
    # --- glazing / roof (fitted to the body skin, see BodyProbe) ------------
    ws_base: tuple = (-0.345, 0.945)      # C(body) windscreen base (x, z) at centre (openings.WINDSCREEN)
    ws_top: tuple = (-1.318, 1.352)       # C(body) header: outer 1.36 minus glass/inset (inner glass line)
    ws_base_side_dx: float = -0.10        # E base line sweeps back ~100 mm at |y|=0.65 (plan curvature)
    liner_drop: float = 0.062             # E roof skin -> headliner surface (outer 1.40-1.41 -> liner 1.34-1.35)
    a_pillar_base: tuple = (-0.545, 0.735, 0.95)  # E inner A-pillar foot (x, |y|, z), 60 mm inside the skin
    a_pillar_top: tuple = (-1.250, 0.600, 1.280) # E inner A-pillar at the header (skin |y| 0.647 at z 1.30)

    # --- side walls ---------------------------------------------------------------
    # side glass lower edge (= inner belt line) from the body DLO outline (C(body))
    belt_pts: tuple = ((-0.64, 0.928), (-1.0, 0.946), (-1.5, 0.972), (-2.1, 1.002), (-2.7, 1.034),
                       (-2.93, 1.045))
    door_inset: float = 0.125             # E outer skin -> door trim surface (door structure + trim)
    glass_clear: float = 0.014            # E trim window-sill edge stays this far inside the skin/glass
    roof_side_y: float = 0.600            # E headliner edge (skin |y| 0.62-0.65 at z 1.30-1.35)
    front_door_x: tuple = (-0.480, -1.500)  # C(body) front door shut lines -0.46 / -1.51 (trim 10-20 mm inside)
    rear_door_x: tuple = (-1.522, -2.490)   # C(body) rear door: B gap -1.51 -> rear edge (top)
    # rear door rear edge (z -> x), body openings.REAR_DOOR_REAR moved 12 mm inboard of the gap
    rear_door_edge: tuple = ((0.288, -2.173), (0.45, -2.180), (0.62, -2.200), (0.70, -2.238),
                             (0.81, -2.323), (0.925, -2.418), (0.975, -2.458), (1.022, -2.493))
    b_pillar_x: float = -1.550            # C(body) B-pillar applique -1.495..-1.59
    c_pillar_x: tuple = (-2.515, -2.385)  # C(body) C-pillar divider foot (belt) -> top
    quarter_x: tuple = (-2.50, -3.17)     # E rear quarter trim (rear door edge -> tailgate opening)
    # DLO rear edge (quarter light) from the body outline: D-pillar trim starts here
    dlo_rear: tuple = ((-2.935, 1.048), (-2.90, 1.092), (-2.85, 1.17), (-2.79, 1.24), (-2.72, 1.292),
                       (-2.60, 1.320))
    tailgate_x: float = -3.17             # C(body) rear window / tailgate opening at the roof

    # --- floor ------------------------------------------------------------------
    floor_z: float = 0.22                 # E carpet surface (0.20-0.24 given)
    tunnel_w: float = 0.30                # E transmission tunnel width
    tunnel_h: float = 0.12                # E tunnel height above floor
    toe_board_x: float = -0.62            # E toe board / firewall at the pedals (-0.55..-0.70 given)
    heel_x: float = -0.80                 # E accelerator heel point on the carpet
    rear_floor_step_x: float = -2.05      # E front of rear footwell (under front seats)
    seat_cross_member_z: float = 0.27     # E rear footwell raised under front seats

    # --- occupants / seats -------------------------------------------------------
    h_front: tuple = (-1.53, 0.37, 0.43)  # E driver H-point (passenger mirrored)
    h_rear: tuple = (-2.33, 0.38, 0.47)   # E rear outer H-points
    torso_front_deg: float = 24.0         # E backrest angle from vertical (sporty)
    torso_rear_deg: float = 26.0          # E
    seat_w: float = 0.54                  # E S line sport seat overall width incl. bolsters
    rear_cushion_x: tuple = (-1.93, -2.50) # E rear bench front edge -> backrest crease
    rear_back_top: tuple = (-2.80, 1.04)  # E rear backrest top (x, z) ("hasta -2.75..-2.85, 1.05")
    rear_split: float = 0.40              # C 60/40 split; E: the 40 % part sits behind the driver (+y)

    # --- steering ---------------------------------------------------------------
    sw_centre: tuple = (-1.07, 0.37, 0.93)  # E steering wheel centre
    sw_tilt_deg: float = 23.0             # E column angle from horizontal
    sw_diameter: float = 0.375            # E (8V 4-spoke ~375 mm)

    # --- dashboard ----------------------------------------------------------------
    dash_half_w: float = 0.725            # E dash ends just inside the front door trims (|y| >= 0.735)
    dash_lip_x: float = -0.845            # E leading edge ("wing") of the dash top at centre
    dash_lip_z: float = 0.985             # E low, horizontal 8V upper dash
    dash_top_z: float = 0.962             # E top surface near the screen slot
    inlay_z: float = 0.795                # E aluminium inlay / hazard strip height
    dash_bottom_z: float = 0.52           # E lower edge of glovebox / knee panel
    vent_ring_d: float = 0.090            # E chrome ring outer diameter (scaled from photos vs 375 wheel)
    vent_c_spacing: float = 0.150         # E centre-to-centre of the two central vents
    vent_c_z: float = 0.880               # E central vents height
    vent_s_y: float = 0.615               # E side vents |y|
    vent_s_z: float = 0.885               # E side vents height
    mmi_size: tuple = (0.175, 0.110)      # E 7" pop-up screen housing (w, h)
    mmi_thick: float = 0.011              # S/E 11 mm housing thickness
    mmi_slot_x: float = -0.765            # E slot position on the dash top
    mmi_tilt_deg: float = 12.0            # E screen leans back
    cluster_c: tuple = (-0.745, 0.37, 0.940)  # E centre of the gauge faces
    console_x: tuple = (-0.86, -1.88)     # E centre console from dash to rear end of armrest

    # derived helpers ------------------------------------------------------------
    def ws_z(self, x):
        """Inner windscreen height at x (centre line) -- for clearance checks."""
        (x0, z0), (x1, z1) = self.ws_base, self.ws_top
        return z0 + (z1 - z0) * (x - x0) / (x1 - x0)

    def roof_z(self, x, y=0.0):
        """Headliner surface height (roof skin minus liner_drop)."""
        return _probe_tables().roof(x, y) - self.liner_drop

    def belt_z(self, x):
        p = np.array(self.belt_pts)[::-1]
        return np.interp(x, p[:, 0], p[:, 1])

    def sw_axis(self):
        """Unit vector of the steering axis pointing TO the driver."""
        a = math.radians(self.sw_tilt_deg)
        return np.array([-math.cos(a), 0.0, math.sin(a)])

    def h_point(self, side=1, rear=False):
        h = self.h_rear if rear else self.h_front
        return np.array([h[0], side * h[1], h[2]])


_DEFAULT = Layout()


# ---------------------------------------------------------------------------
# body probe: outer skin |y|(x, z) and roof z(x, y)
# ---------------------------------------------------------------------------

# Measured on the body reference skin (src/a3/body, ray casting from the car
# centre plane, 2026-10).  Used when the body part is not built; when it is,
# BodyProbe ray-casts the live skin instead.
_SX = [-0.35, -0.45, -0.55, -0.65, -0.80, -1.00, -1.20, -1.40, -1.55, -1.70, -1.90, -2.10, -2.30,
       -2.50, -2.70, -2.90, -3.10, -3.30]
_SZ = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35]
_SY = """
880 880 880 880 880 880 880 880 881 881 881 881 882 883 884 881 859 644
889 889 889 889 889 889 890 890 890 891 892 893 894 898 901 902 882 755
883 883 882 882 882 882 882 882 883 883 885 886 889 894 899 900 882 761
878 878 878 878 878 877 878 878 878 879 880 881 883 889 892 890 859 740
874 875 875 875 875 875 876 876 877 878 879 881 882 887 890 884 832 713
870 871 871 872 872 873 874 875 875 876 878 879 881 884 887 875 800 682
821 849 855 859 861 864 867 869 871 873 875 877 879 882 884 867 767 628
  0 795 816 823 829 835 841 846 850 853 857 861 864 868 871 858 771 610
  0   0 754 777 789 795 799 802 805 810 818 826 832 838 843 835 767 574
  0   0   0 735 761 773 777 781 783 785 788 790 792 794 795 793 747 500
  0   0   0   0 730 750 754 757 759 761 764 766 767 768 767 759 713 338
  0   0   0   0 696 724 730 733 735 736 738 740 741 740 737 727 675   0
  0   0   0   0   0 696 704 707 709 710 711 712 713 710 705 693 634   0
  0   0   0   0   0   0 676 680 681 682 683 683 683 679 672 657 589   0
  0   0   0   0   0   0 647 651 652 652 652 653 652 646 636 618 448   0
  0   0   0   0   0   0   0 620 621 621 621 620 619 594 472 289   0   0
"""
_RX = [-0.40, -0.60, -0.80, -1.00, -1.20, -1.30, -1.40, -1.60, -1.80, -2.00, -2.20, -2.40, -2.60,
       -2.80, -3.00, -3.20, -3.35]
_RY = [0.0, 0.2, 0.4, 0.5, 0.55, 0.6, 0.65]
_RZ = """
959 1062 1158 1244 1319 1351 1377 1402 1408 1407 1405 1397 1386 1370 1353 1268 1056
960 1062 1158 1244 1319 1349 1373 1394 1399 1398 1397 1389 1379 1364 1347 1260 1052
960 1062 1158 1244 1319 1344 1362 1376 1378 1378 1377 1372 1362 1350 1333 1236 1019
960 1062 1158 1244 1319 1342 1357 1366 1367 1367 1367 1362 1353 1342 1326 1201  960
960 1062 1158 1244 1319 1340 1354 1361 1362 1362 1362 1358 1349 1338 1323 1165  960
959 1062 1158 1244 1319 1339 1352 1357 1357 1357 1357 1353 1345 1335 1302 1119  960
957 1062 1158 1244 1294 1296 1301 1303 1304 1304 1304 1299 1288 1272 1241 1069  960
"""


class _Tables:
    def __init__(self):
        from scipy.interpolate import RegularGridInterpolator as RGI
        sy = np.array(_SY.split(), float).reshape(len(_SZ), len(_SX)) / 1000.0
        # fill the cells above the skin (no hit) by continuing the tumblehome
        for j in range(len(_SX)):
            for i in range(1, len(_SZ)):
                if sy[i, j] <= 0:
                    sy[i, j] = sy[i - 1, j] - 0.03
        self._side = RGI((_SZ, _SX[::-1]), sy[:, ::-1], bounds_error=False, fill_value=None)
        rz = np.array(_RZ.split(), float).reshape(len(_RY), len(_RX)) / 1000.0
        self._roof = RGI((_RY, _RX[::-1]), rz[:, ::-1], bounds_error=False, fill_value=None)

    def side(self, x, z):
        return float(self._side([[np.clip(z, _SZ[0], _SZ[-1]), np.clip(x, _SX[-1], _SX[0])]])[0])

    def roof(self, x, y):
        x = np.clip(np.asarray(x, float), _RX[-1], _RX[0])
        y = np.clip(np.abs(np.asarray(y, float)), 0, _RY[-1])
        xb, yb = np.broadcast_arrays(x, y)
        v = self._roof(np.stack([yb.ravel(), xb.ravel()], 1)).reshape(xb.shape)
        return v if v.ndim else float(v)


_TABLES = None


def _probe_tables():
    global _TABLES
    if _TABLES is None:
        _TABLES = _Tables()
    return _TABLES


class BodyProbe:
    """Outer skin queries. Uses the live body (ctx.objects['skin_ref']) when it
    was built, else the tables above."""

    def __init__(self, ctx=None):
        self.bvh = None
        ref = getattr(ctx, "objects", {}).get("skin_ref") if ctx is not None else None
        if ref is not None:
            import bpy
            from mathutils.bvhtree import BVHTree
            self.bvh = BVHTree.FromObject(ref, bpy.context.evaluated_depsgraph_get())
        self.t = _probe_tables()
        self._c = {}

    def side_y(self, x, z):
        """Outer skin |y| at (x, z) (left side; the car is symmetric)."""
        k = (round(float(x), 4), round(float(z), 4))
        if k in self._c:
            return self._c[k]
        v = None
        if self.bvh is not None:
            from mathutils import Vector
            loc, *_ = self.bvh.ray_cast(Vector((x, 0.0, z)), Vector((0, 1, 0)))
            if loc is not None and loc.y > 0.25:
                v = loc.y
        if v is None:
            v = self.t.side(x, z)
        self._c[k] = v
        return v


def probe(ctx):
    if ctx is None:
        return BodyProbe(None)
    p = ctx.data.get("body_probe") if isinstance(getattr(ctx, "data", None), dict) else None
    if p is None:
        p = BodyProbe(ctx)
        ctx.data["body_probe"] = p
    return p


def get(ctx=None) -> Layout:
    if ctx is not None and isinstance(getattr(ctx, "data", None), dict):
        L = ctx.data.get("interior_layout")
        if isinstance(L, Layout):
            return L
        if isinstance(L, dict):
            return replace(_DEFAULT, **L)
    return _DEFAULT
