"""Vehicle specification: Audi A3 Sportback 8V (8VA, MY2013-2016, pre-facelift)
2.0 TDI 110 kW (150 PS) S tronic, front-wheel drive, S line.

All values in millimetres unless noted. Status:
    C = confirmed (primary or several concurring sources)
    S = single secondary source
    E = estimate (derived/engineering judgement), refine when better data appears

Coordinate system (ISO 8855): +X forward, +Y left, +Z up; origin on the
ground plane, laterally centred, longitudinally at the FRONT AXLE centre.
Model units are metres (use ``m()``).
"""
from __future__ import annotations

# --- Overall ---------------------------------------------------------------
LENGTH = 4310            # C  Audi UK spec sheet / cars-data
WIDTH = 1785             # C  without mirrors
WIDTH_MIRRORS = 1966     # S  auto-data.net
HEIGHT_STD = 1425        # C  standard ("dynamic") suspension
SPORT_SUSP_DROP = 15     # S  S line sports suspension (-15 mm)
HEIGHT = HEIGHT_STD - SPORT_SUSP_DROP  # 1410, S line sport suspension
WHEELBASE = 2636         # C  Audi UK press spec (2.0 TDI 150)
TRACK_FRONT = 1535       # C
TRACK_REAR = 1506        # C
OVERHANG_FRONT = 869     # S  (869 + 2636 + 805 = 4310)
OVERHANG_REAR = 805      # S
GROUND_CLEARANCE = 115   # E  sources disagree (109..140); S line sport susp.
CD = 0.30                # C  launch press release (0.313 for this engine, A=2.13 m2)

X_FRONT = OVERHANG_FRONT                 # front bumper tip
X_REAR_AXLE = -WHEELBASE
X_REAR = -(WHEELBASE + OVERHANG_REAR)    # rear bumper tip

# --- Wheels / tyres ----------------------------------------------------------
# Audi exclusive 18" "5-arm rotor" gloss black, diamond-turned face
# part 8V0 601 025 AN, 8J x 18 H2 ET46, 5x112, CB 57.1  (C/S)
RIM_DIAMETER_IN = 18
RIM_WIDTH_IN = 8.0
RIM_OFFSET = 46          # ET
PCD = 112
BOLTS = 5
CENTRE_BORE = 57.1
TYRE = (225, 40, 18)     # C 225/40 R18 92Y
TYRE_WIDTH = 225
TYRE_ASPECT = 0.40
TYRE_DIAMETER = 18 * 25.4 + 2 * TYRE_WIDTH * TYRE_ASPECT   # 637.2 unloaded
TYRE_STATIC_RADIUS = 306  # E loaded radius (~4% deflection of sidewall+tread)
WHEEL_CENTER_Z = TYRE_STATIC_RADIUS

# --- Brakes --------------------------------------------------------------------
BRAKE_FRONT_DISC = (312, 25)   # S/E ventilated (PR 1ZA/1ZD)
BRAKE_REAR_DISC = (272, 10)    # S solid, EPB caliper


def m(v):
    """mm -> m (works for scalars and tuples)."""
    if isinstance(v, (tuple, list)):
        return type(v)(x / 1000.0 for x in v)
    return v / 1000.0


def wheel_centres():
    """(x, y, z) in metres for FL, FR, RL, RR."""
    zf = m(WHEEL_CENTER_Z)
    return {
        "FL": (0.0, m(TRACK_FRONT) / 2, zf),
        "FR": (0.0, -m(TRACK_FRONT) / 2, zf),
        "RL": (m(X_REAR_AXLE), m(TRACK_REAR) / 2, zf),
        "RR": (m(X_REAR_AXLE), -m(TRACK_REAR) / 2, zf),
    }
