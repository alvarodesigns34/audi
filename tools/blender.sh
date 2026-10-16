#!/usr/bin/env bash
# Run a tools/*.py script with a desktop Blender instead of the bpy venv
# (Windows / Git Bash or any machine with Blender installed).
#   tools/blender.sh tools/run.py --views front34
#   tools/blender.sh --setup          # installs scipy + pillow into out/pydeps
# BLENDER overrides the executable path.
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER=${BLENDER:-"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"}
win() { if command -v cygpath >/dev/null; then cygpath -w "$1"; else echo "$1"; fi; }
if [ "${1:-}" = "--setup" ]; then
  PYB=$(ls "$(dirname "$BLENDER")"/*/python/bin/python* | head -1)
  "$PYB" -m pip install --target "$(win "$PWD/out/pydeps")" --no-deps scipy pillow
  exit 0
fi
A3_CWD=$(win "$PWD") exec "$BLENDER" -b --factory-startup --python-exit-code 1 \
  -P "$(win "$PWD/tools/blender_run.py")" -- "$@"
