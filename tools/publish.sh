#!/usr/bin/env bash
# Rebuild everything published on GitHub Pages (docs/): full-quality GLB
# (never simplified), USDZ for iPhone/iPad, and the verification renders.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-/opt/bpyenv/bin/python}
$PY tools/run.py --glb docs/models/a3_sportback_8v.glb --no-draco \
    --views front34,rear34,side_r,front,rear,top,cockpit,interior_rear,wheel_fl \
    --out docs/renders --samples ${SAMPLES:-64} --res 1600x900
$PY tools/run.py --views front34 --explode 1.0 --tag exploded_ --out docs/renders \
    --samples ${SAMPLES:-64} --res 1600x900
$PY tools/run.py --views bay --tag engine_ --out docs/renders --samples ${SAMPLES:-64} --res 1600x900 \
    --hide "^Body_Hood$|^Body_Cowl$|^Glass_Windscreen|^Wiper|^Seal_Wind"
$PY tools/export_usdz.py docs/models/a3_sportback_8v.usdz
ls -la docs/models docs/renders
