#!/usr/bin/env bash
# Creates the Python venv with Blender as a module (bpy) + helpers.
set -euo pipefail
VENV=${VENV:-/opt/bpyenv}
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install "bpy==5.2.*" numpy scipy pillow
"$VENV/bin/python" -c "import bpy; print('Blender', bpy.app.version_string)"
