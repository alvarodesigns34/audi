"""Run any tools/*.py script inside a desktop Blender (e.g. Blender 5.2 on Windows)
instead of the bpy module venv.

Usage:
    blender -b --factory-startup -P tools/blender_run.py -- tools/run.py --views front34

Everything after ``--`` is passed to the target script as its own ``sys.argv``.
Extra Python packages (scipy, pillow) are looked up in ``out/pydeps``; install
them once with Blender's Python (see tools/blender.sh).
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS = os.path.join(ROOT, "out", "pydeps")
if os.path.isdir(DEPS) and DEPS not in sys.path:
    sys.path.insert(0, DEPS)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    sys.exit("usage: blender -b -P tools/blender_run.py -- <script.py> [args]")
# Blender does not keep the caller's working directory (tools/blender.sh passes it).
if os.environ.get("A3_CWD"):
    os.chdir(os.environ["A3_CWD"])
script = os.path.abspath(argv[0])
sys.argv = [script] + argv[1:]
sys.path.insert(0, os.path.dirname(script))
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    sys.stdout.flush()
    os._exit(code)
sys.stdout.flush()
