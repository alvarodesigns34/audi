"""Build orchestrator.

Each part is a module exposing ``build(ctx: BuildContext) -> None``.
Parts are built in the order of ``PARTS``; later parts may query objects of
earlier ones through ``ctx.objects`` (e.g. interior parts use the body shell).
"""
from __future__ import annotations

import importlib
import time
import traceback
from dataclasses import dataclass, field

from .core import materials, scene

# (key, module) in build order
PARTS = [
    ("body", "a3.body.shell"),
    ("glass", "a3.body.glass"),
    ("lights_front", "a3.exterior.headlights"),
    ("front_end", "a3.exterior.front_end"),
    ("rear_end", "a3.exterior.rear_end"),
    ("trim", "a3.exterior.trim"),
    ("mirrors", "a3.exterior.mirrors"),
    ("wheels", "a3.wheels.assembly"),
    ("underbody", "a3.exterior.underbody"),
    ("interior", "a3.interior.assembly"),
]


@dataclass
class BuildContext:
    paint: str = "ibis_white"
    detail: str = "high"          # "high" | "preview"
    objects: dict = field(default_factory=dict)   # name -> bpy object
    data: dict = field(default_factory=dict)      # shared derived data (curves, surfaces)

    def mat(self, key):
        return materials.get(key, paint=self.paint)

    def register(self, key, ob):
        self.objects[key] = ob
        return ob


def build(parts=None, paint="ibis_white", detail="high", strict=False):
    scene.reset()
    materials.reset_cache()
    ctx = BuildContext(paint=paint, detail=detail)
    for key, modname in PARTS:
        if parts and key not in parts:
            continue
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError as e:
            if e.name and e.name.startswith("a3."):
                print(f"[build] skip {key}: module {modname} not present")
                continue
            raise
        t = time.time()
        try:
            mod.build(ctx)
            print(f"[build] {key:14s} ok  {time.time() - t:6.1f}s")
        except Exception:
            print(f"[build] {key:14s} FAILED")
            traceback.print_exc()
            if strict:
                raise
    return ctx
