"""Interior assembly: builds every interior subsystem in dependency order.

Order matters: the dashboard publishes its shape (``ctx.data["dash"]``) that
vents, cluster, MMI and climate use to sit on the real surface; seats publish
their positions for belts.
"""
from __future__ import annotations

import importlib
import os
import time

MODULES = [
    "dashboard", "vents", "cluster", "mmi", "climate", "steering", "console",
    "seats", "doors", "trim", "pedals", "misc",
]


def build(ctx):
    only = os.environ.get("A3_INTERIOR_ONLY")
    mods = [m for m in MODULES if not only or m in only.split(",")]
    for name in mods:
        try:
            mod = importlib.import_module(f"a3.interior.{name}")
        except ModuleNotFoundError as e:
            if e.name == f"a3.interior.{name}":
                print(f"[interior] skip {name} (not present)")
                continue
            raise
        t = time.time()
        mod.build(ctx)
        print(f"[interior] {name:10s} {time.time() - t:5.1f}s")
    from . import _geo
    _geo.cleanup_temp()
