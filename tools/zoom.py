"""Crop + enlarge a photo region with a labelled pixel grid (for digitising
feature points by eye).  Optional points to mark: --pts "u,v;u,v".

Usage: python tools/zoom.py photo.jpg x0 y0 x1 y1 out.png [--step 20] [--pts ...]
"""
import argparse

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("box", nargs=4, type=int)
    ap.add_argument("out")
    ap.add_argument("--step", type=int, default=20)
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--pts", default="")
    a = ap.parse_args()
    x0, y0, x1, y1 = a.box
    im = Image.open(a.photo).convert("RGB").crop((x0, y0, x1, y1))
    s = a.width / (x1 - x0)
    im = im.resize((a.width, int((y1 - y0) * s)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for x in range((x0 // a.step + 1) * a.step, x1, a.step):
        X = (x - x0) * s
        major = x % (a.step * 5) == 0
        d.line([(X, 0), (X, im.height)], fill=(0, 255, 255) if major else (0, 140, 160), width=1)
        if major:
            d.text((X + 2, 2), str(x), fill=(255, 255, 0))
    for y in range((y0 // a.step + 1) * a.step, y1, a.step):
        Y = (y - y0) * s
        major = y % (a.step * 5) == 0
        d.line([(0, Y), (im.width, Y)], fill=(0, 255, 255) if major else (0, 140, 160), width=1)
        if major:
            d.text((2, Y + 2), str(y), fill=(255, 255, 0))
    for i, p in enumerate([q for q in a.pts.split(";") if q]):
        u, v = map(float, p.split(","))
        X, Y = (u - x0) * s, (v - y0) * s
        d.ellipse([X - 5, Y - 5, X + 5, Y + 5], outline=(255, 0, 255), width=2)
        d.text((X + 6, Y - 12), str(i), fill=(255, 0, 255))
    im.save(a.out)


if __name__ == "__main__":
    main()
