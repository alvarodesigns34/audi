#!/usr/bin/env bash
# Downloads the Wikimedia Commons reference photographs used for camera
# matching (reference/match_*.json) into reference/photos/ (git-ignored).
# Licences: see each file page on commons.wikimedia.org (CC BY / CC BY-SA).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/reference/photos"
mkdir -p "$DIR"
UA="A3TwinResearch/0.1 (personal 3D modelling research)"
dl() {  # $1 = Commons file name, $2 = local name
  local enc; enc=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1")
  [ -s "$DIR/$2" ] && return 0
  for i in 1 2 3 4 5 6; do
    if curl -sSfL -A "$UA" "https://commons.wikimedia.org/wiki/Special:FilePath/${enc}?width=1600" \
         -o "$DIR/$2"; then sleep 2; return 0; fi
    echo "  retry $1 in $((10 * i)) s (rate limited?)" >&2; sleep $((10 * i))
  done
  echo "FAILED: $1" >&2; return 1
}
dl "Audi A3 Sportback 8V (side).JPG" side.jpg                      # match_side.json (S line, right side)
dl "Audi A3 8V 1.4 TFSI Ambiente Misanorot Seite.JPG" side2.jpg      # match_side2.json (3-door)
dl "Audi A3 Sportback S-line (8V) – Frontansicht, 21. Dezember 2014, Düsseldorf.jpg" sline_front.jpg  # match_sline_front.json
dl "Audi A3 Sportback S-line (8V) – Heckansicht, 21. Dezember 2014, Düsseldorf.jpg" sline_rear.jpg    # match_sline_rear.json (5-arm rotor wheels)
dl "Audi A3 Sportback 8V (front).JPG" front.jpg                    # S line show car, chrome grille
dl "Audi A3 Sportback 8V (rear quarter).JPG" rearq.jpg
dl "Audi A3 Sportback 1.4 TFSI Ambition S line Imolagelb.JPG" yellow.jpg
dl "Audi A3 Sportback 1.4 TFSI Ambition S line Imolagelb Heck.JPG" yellow_rear.jpg
dl "Audi A3 8V Ambition design selection capriorange 2.0 TDI Gletscherweiß Cockpit.JPG" cockpit.jpg   # 4-spoke wheel
dl "Audi A3 8V Ambition design selection capriorange 2.0 TDI Gletscherweiß Innenraum.JPG" interior.jpg
echo "References in $DIR"
