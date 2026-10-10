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
    # --- glazing / roof -----------------------------------------------------
    ws_base: tuple = (-0.33, 0.95)        # E windscreen base (x, z) at centre
    ws_top: tuple = (-1.33, 1.31)         # E windscreen header (x, z): roof 1.33 minus header trim
    ws_base_side_dx: float = -0.10        # E base line sweeps back ~100 mm at |y|=0.65 (plan curvature)
    roof_front: tuple = (-1.6, 1.33)      # E headliner height (x, z)
    roof_rear: tuple = (-2.9, 1.28)       # E
    roof_crown: float = 0.035             # E headliner drop from centre to |y|=0.55 (dome)
    a_pillar_base: tuple = (-0.45, 0.70, 0.98)   # E inner A-pillar foot (x, |y|, z)

    # --- side walls -----------------------------------------------------------
    belt_z_front: float = 1.00            # E inner belt line (top of door trims), front door
    belt_z_rear: float = 1.03             # E rear door
    door_y: float = 0.715                 # E inner door surface at armrest height (0.70-0.73)
    door_y_rear: float = 0.705            # E rear doors slightly narrower (tumblehome / arch)
    roof_side_y: float = 0.60             # E headliner edge (greenhouse tumblehome)
    front_door_x: tuple = (-0.50, -1.86)  # E front door trim span (A-pillar foot -> B-pillar)
    rear_door_x: tuple = (-1.95, -2.82)   # E rear door trim span (B-pillar -> C-pillar)
    b_pillar_x: float = -1.905            # E B-pillar centre (between door shut lines)
    c_pillar_x: tuple = (-2.82, -3.02)    # E C-pillar trim foot (belt) -> top
    d_pillar_x: tuple = (-3.18, -3.05)    # E D-pillar (tailgate opening) at belt / roof

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
    rear_back_top: tuple = (-2.80, 1.05)  # E rear backrest top (x, z) ("hasta -2.75..-2.85, 1.05")
    rear_split: float = 0.40              # C 60/40 split; E: the 40 % part sits behind the driver (+y)

    # --- steering ---------------------------------------------------------------
    sw_centre: tuple = (-1.07, 0.37, 0.93)  # E steering wheel centre
    sw_tilt_deg: float = 23.0             # E column angle from horizontal
    sw_diameter: float = 0.375            # E (8V 4-spoke ~375 mm)

    # --- dashboard ----------------------------------------------------------------
    dash_half_w: float = 0.705            # E dash ends meet the door trims
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
        (x0, z0), (x1, z1) = self.roof_front, self.roof_rear
        zc = z0 + (z1 - z0) * (np.asarray(x) - x0) / (x1 - x0)
        zc = np.minimum(zc, z0 + 0.004)
        return zc - self.roof_crown * (np.asarray(y) / 0.55) ** 2

    def belt_z(self, x):
        t = np.clip((np.asarray(x) - self.front_door_x[0]) / (self.rear_door_x[1] - self.front_door_x[0]), 0, 1)
        return self.belt_z_front + (self.belt_z_rear - self.belt_z_front) * t

    def sw_axis(self):
        """Unit vector of the steering axis pointing TO the driver."""
        a = math.radians(self.sw_tilt_deg)
        return np.array([-math.cos(a), 0.0, math.sin(a)])

    def h_point(self, side=1, rear=False):
        h = self.h_rear if rear else self.h_front
        return np.array([h[0], side * h[1], h[2]])


_DEFAULT = Layout()


def get(ctx=None) -> Layout:
    if ctx is not None and isinstance(getattr(ctx, "data", None), dict):
        L = ctx.data.get("interior_layout")
        if isinstance(L, Layout):
            return L
        if isinstance(L, dict):
            return replace(_DEFAULT, **L)
    return _DEFAULT
