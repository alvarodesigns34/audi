"""Procedural textures generated with numpy and saved as images, so they are
embedded in the glTF / USDZ exports (Blender procedural nodes are not).

Tileable surface textures (height field -> tangent-space normal map, plus
optional base-colour / roughness maps) and two "content" images (MMI screen
UI, instrument-cluster FIS).  Every texture is deterministic (fixed seeds)
and cached in out/textures by name + generator version.

Physical tile sizes (m) are stored on the materials (``uv_tile``) and used
by core/uv.py to box-project UVs in metres / tile.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "out", "textures")
VERSION = 4


# --------------------------------------------------------------------------
# tileable noise primitives
# --------------------------------------------------------------------------

def _rng(seed):
    return np.random.default_rng(seed)


def value_noise(n, cells, seed, octaves=1, persistence=0.5):
    """Tileable value noise on an n x n grid (sum of octaves), range ~[0, 1]."""
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    r = _rng(seed)
    for o in range(octaves):
        c = cells * (2 ** o)
        g = r.random((c, c))
        x = np.arange(n) * c / n
        i0 = np.floor(x).astype(int) % c
        i1 = (i0 + 1) % c
        f = x - np.floor(x)
        f = f * f * (3 - 2 * f)
        a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
        b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
        out += amp * (a * (1 - f)[:, None] + b * f[:, None])
        tot += amp
        amp *= persistence
    return out / tot


def worley(n, points, seed, second=True):
    """Tileable Worley noise (F1, F2 distances in pixels)."""
    r = _rng(seed)
    P = r.random((points, 2)) * n
    # replicate for wrapping
    offs = np.array([(dx, dy) for dx in (-n, 0, n) for dy in (-n, 0, n)])
    Q = (P[None] + offs[:, None]).reshape(-1, 2)
    from scipy.spatial import cKDTree
    t = cKDTree(Q)
    yy, xx = np.mgrid[0:n, 0:n]
    d, _ = t.query(np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], 1), k=2 if second else 1)
    if second:
        return d[:, 0].reshape(n, n), d[:, 1].reshape(n, n)
    return d.reshape(n, n), None


def normal_from_height(h, strength):
    """Tangent-space normal map (uint8 RGB) from a tileable height field."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx, ny = -dx * strength, dy * strength      # OpenGL convention (glTF): +Y up in UV
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def _norm(a):
    a = a - a.min()
    return a / (a.max() + 1e-12)


# --------------------------------------------------------------------------
# surface textures: name -> (generator, tile size in metres)
# --------------------------------------------------------------------------

def _leather(n=1024, seed=11):
    """Pebbled leather: rounded pebbles (~1.5-2 mm) separated by narrow
    crevices, plus a faint secondary grain."""
    f1, f2 = worley(n, 1100, seed)
    gap = f2 - f1
    mean = np.mean(f2)
    crevice = np.clip(gap / (0.30 * mean), 0, 1) ** 0.55
    h = 0.8 * crevice + 0.2 * value_noise(n, 96, seed + 1, 3)
    h = np.asarray(Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.3)),
                   float) / 255
    return h


def leather_maps():
    h = _leather()
    nrm = normal_from_height(h, 9.0)
    rough = (150 + 50 * (1 - h)).astype(np.uint8)            # crevices rougher
    return {"normal": nrm, "rough": rough}


def leather_perf_maps(n=1024, holes=8):
    """Perforated leather (S line seat centre panels): 1.2 mm holes on a
    staggered 4.3 mm pitch (E)."""
    h = _leather(n, seed=21)
    yy, xx = np.mgrid[0:n, 0:n] + 0.5
    p = n / holes
    r = p * 0.14
    d = np.full((n, n), 1e9)
    for row in range(-1, holes + 1):
        off = p / 2 if row % 2 else 0
        for col in range(-1, holes + 1):
            cx, cy = col * p + off + p / 4, row * p + p / 2
            d = np.minimum(d, np.hypot(xx - cx, yy - cy))
    hole = np.clip((r - d) / 1.5 + 0.5, 0, 1)
    rim = np.exp(-((d - r) / (r * 0.6)) ** 2) * 0.25
    hh = h * (1 - hole) - hole * 1.2 + rim
    nrm = normal_from_height(hh, 9.0)
    base = (np.clip(1 - hole * 0.9, 0, 1) * 255).astype(np.uint8)   # multiply mask
    rough = (150 + 50 * (1 - h) + 60 * hole).clip(0, 255).astype(np.uint8)
    return {"normal": nrm, "ao": base, "rough": rough}


def grain_plastic_maps(n=1024, seed=31):
    """Fine 'leather-look' grain of the moulded dash / door plastics."""
    f1, f2 = worley(n, 2600, seed)
    h = 0.7 * _norm(f1) + 0.3 * value_noise(n, 128, seed + 3, 2)
    return {"normal": normal_from_height(h, 4.0),
            "rough": (175 + 40 * _norm(f1)).astype(np.uint8)}


def soft_touch_maps(n=1024, seed=41):
    h = value_noise(n, 256, seed, 3, 0.6)
    return {"normal": normal_from_height(h, 2.0)}


def carpet_maps(n=1024, seed=51):
    r = _rng(seed)
    h = value_noise(n, 512, seed, 2, 0.7) * 0.6 + r.random((n, n)) * 0.4
    h = np.asarray(Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)),
                   float) / 255
    tufts = value_noise(n, 96, seed + 5, 1)
    return {"normal": normal_from_height(h + 0.3 * tufts, 6.0),
            "albedo_var": (200 + 55 * h).astype(np.uint8)}


def fabric_maps(n=1024, seed=61, threads=96):
    """Knitted headliner fabric: interlaced ribs + fibre noise."""
    yy, xx = np.mgrid[0:n, 0:n] / n
    a = np.sin(2 * np.pi * threads * xx) * np.sin(2 * np.pi * threads * yy * 0.5)
    h = 0.6 * (a * 0.5 + 0.5) + 0.4 * value_noise(n, 300, seed, 2)
    return {"normal": normal_from_height(h, 3.0)}


def webbing_maps(n=512, ribs=48):
    """Seat-belt twill: diagonal ribs."""
    yy, xx = np.mgrid[0:n, 0:n] / n
    h = (np.sin(2 * np.pi * ribs * (xx + yy)) * 0.5 + 0.5) ** 0.7
    h += 0.15 * value_noise(n, 128, 71, 1)
    return {"normal": normal_from_height(h, 4.0)}


def brushed_maps(n=1024, seed=81):
    """Brushed aluminium: streaks along U."""
    r = _rng(seed)
    rows = r.random(n)
    rows = np.convolve(np.concatenate([rows, rows[:9]]), np.ones(9) / 9, "valid")[:n]
    h = np.tile(rows[:, None], (1, n)) * 0.8 + value_noise(n, 8, seed, 2) * 0.2
    return {"normal": normal_from_height(h, 3.0),
            "rough": (60 + 70 * _norm(rows))[:, None].repeat(n, 1).astype(np.uint8)}


def rubber_maps(n=512, seed=91):
    h = value_noise(n, 160, seed, 3, 0.6)
    return {"normal": normal_from_height(h, 2.0)}


def flake_maps(n=1024, seed=101):
    """Metallic paint flakes: random facet normals (Glacier white metallic)."""
    r = _rng(seed)
    f1, _ = worley(n, 30000, seed, second=False)
    lab = (f1 < 3.0)
    tilt = r.normal(0, 0.18, (n, n, 2))
    from scipy import ndimage
    tilt[..., 0] = ndimage.gaussian_filter(tilt[..., 0], 0.7, mode="wrap")
    tilt[..., 1] = ndimage.gaussian_filter(tilt[..., 1], 0.7, mode="wrap")
    nx, ny = tilt[..., 0] * lab, tilt[..., 1] * lab
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    rgb = np.stack([nx, ny, nz], -1) * 0.5 + 0.5
    return {"normal": (rgb * 255).astype(np.uint8)}


def disc_maps(n=512, seed=111):
    """Brake disc friction ring: fine concentric machining marks (along U
    when the ring is box-projected this becomes generic fine scoring)."""
    r = _rng(seed)
    rows = np.convolve(r.random(n + 4), np.ones(5) / 5, "valid")[:n]
    h = np.tile(rows[None, :], (n, 1))
    return {"normal": normal_from_height(h, 2.5)}


SURFACES = {
    # key: (generator, tile size m, normal strength in the material)
    "leather": (leather_maps, 0.060, 0.9),
    "leather_perf": (leather_perf_maps, 0.034, 1.0),
    "grain_plastic": (grain_plastic_maps, 0.080, 0.8),
    "soft_touch": (soft_touch_maps, 0.060, 0.6),
    "carpet": (carpet_maps, 0.050, 1.0),
    "fabric": (fabric_maps, 0.060, 0.6),
    "webbing": (webbing_maps, 0.020, 0.8),
    "brushed": (brushed_maps, 0.150, 0.35),
    "rubber": (rubber_maps, 0.040, 0.5),
    "flake": (flake_maps, 0.012, 0.25),
    "disc": (disc_maps, 0.030, 0.6),
}


# --------------------------------------------------------------------------
# content images
# --------------------------------------------------------------------------

def _font(size, bold=False):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/truetype/freefont/FreeSans%s.ttf" % ("Bold" if bold else "")):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def mmi_screen(w=1536, h=918):
    """7" MMI navigation screen (MMI Navigation plus, 2013 look): dark map
    with roads, route in red, top status bar, right info column."""
    S = w / 1536
    im = Image.new("RGB", (w, h), (8, 10, 13))
    d = ImageDraw.Draw(im)
    r = _rng(7)
    # map area: blocks of slightly lighter grey, parks, river
    mx0, my0, mx1, my1 = 0, int(70 * S), int(1100 * S), h
    d.rectangle([mx0, my0, mx1, my1], fill=(20, 23, 27))
    for _ in range(140):
        x, y = r.integers(mx0, mx1), r.integers(my0, my1)
        bw, bh = r.integers(30, 140) * S, r.integers(20, 110) * S
        d.rectangle([x, y, x + bw, y + bh], fill=(27, 30, 35))
    for _ in range(6):
        x, y = r.integers(mx0, mx1), r.integers(my0, my1)
        d.ellipse([x, y, x + 160 * S, y + 90 * S], fill=(22, 36, 28))
    river = [(0, 640 * S), (300 * S, 600 * S), (520 * S, 700 * S), (800 * S, 650 * S), (1100 * S, 720 * S)]
    d.line(river, fill=(18, 34, 52), width=int(46 * S), joint="curve")
    # road network
    for _ in range(26):
        if r.random() < 0.5:
            y = r.integers(my0, my1)
            d.line([(mx0, y), (mx1, y + r.integers(-80, 80))], fill=(58, 62, 68), width=int(6 * S))
        else:
            x = r.integers(mx0, mx1)
            d.line([(x, my0), (x + r.integers(-120, 120), my1)], fill=(58, 62, 68), width=int(6 * S))
    main = [(80 * S, h), (260 * S, 700 * S), (430 * S, 520 * S), (560 * S, 470 * S), (760 * S, 300 * S),
            (980 * S, 170 * S), (1100 * S, 120 * S)]
    d.line(main, fill=(150, 120, 60), width=int(16 * S), joint="curve")
    route = [(560 * S, 900 * S), (560 * S, 470 * S), (760 * S, 300 * S), (900 * S, 220 * S)]
    d.line(route, fill=(200, 24, 40), width=int(11 * S), joint="curve")
    # vehicle arrow
    cx, cy = 560 * S, 640 * S
    d.polygon([(cx, cy - 30 * S), (cx + 20 * S, cy + 22 * S), (cx, cy + 10 * S), (cx - 20 * S, cy + 22 * S)],
              fill=(240, 240, 240))
    # top bar
    d.rectangle([0, 0, w, int(70 * S)], fill=(14, 16, 19))
    d.line([(0, int(70 * S)), (w, int(70 * S))], fill=(60, 64, 70), width=max(1, int(2 * S)))
    d.text((30 * S, 18 * S), "NAV", font=_font(int(30 * S), True), fill=(230, 230, 230))
    d.text((w - 150 * S, 18 * S), "12:30", font=_font(int(30 * S)), fill=(230, 230, 230))
    d.text((w / 2 - 120 * S, 20 * S), "Paseo de la Castellana", font=_font(int(26 * S)),
           fill=(200, 200, 200))
    # right column: next manoeuvre, distance, ETA
    x0 = int(1100 * S)
    d.rectangle([x0, int(70 * S), w, h], fill=(13, 15, 18))
    d.line([(x0, int(70 * S)), (x0, h)], fill=(60, 64, 70), width=max(1, int(2 * S)))
    ax, ay = x0 + 90 * S, 200 * S
    d.line([(ax, ay + 120 * S), (ax, ay), (ax + 90 * S, ay - 60 * S)], fill=(235, 235, 235),
           width=int(18 * S), joint="curve")
    d.polygon([(ax + 115 * S, ay - 78 * S), (ax + 60 * S, ay - 70 * S), (ax + 95 * S, ay - 25 * S)],
              fill=(235, 235, 235))
    d.text((x0 + 240 * S, 150 * S), "300 m", font=_font(int(54 * S), True), fill=(240, 240, 240))
    d.text((x0 + 40 * S, 380 * S), "Calle de Alcalá", font=_font(int(34 * S)), fill=(210, 210, 210))
    for i, (k, v) in enumerate((("Llegada", "12:52"), ("Distancia", "14,6 km"), ("Destino", "Casa"))):
        y = 520 * S + i * 110 * S
        d.text((x0 + 40 * S, y), k, font=_font(int(26 * S)), fill=(140, 145, 150))
        d.text((x0 + 40 * S, y + 34 * S), v, font=_font(int(38 * S), True), fill=(235, 235, 235))
    # scale bar + compass
    d.text((30 * S, h - 60 * S), "200 m", font=_font(int(24 * S)), fill=(200, 200, 200))
    d.line([(30 * S, h - 25 * S), (160 * S, h - 25 * S)], fill=(200, 200, 200), width=int(4 * S))
    d.ellipse([980 * S, 100 * S, 1060 * S, 180 * S], outline=(200, 200, 200), width=int(3 * S))
    d.text((1008 * S, 115 * S), "N", font=_font(int(36 * S), True), fill=(200, 24, 40))
    return np.asarray(im)


def fis_screen(w=512, h=640):
    """Monochrome-look driver information display (centre of the cluster)."""
    im = Image.new("RGB", (w, h), (6, 7, 9))
    d = ImageDraw.Draw(im)
    d.text((w / 2, 40), "12:30", font=_font(44), fill=(230, 235, 240), anchor="mm")
    d.text((w / 2, 95), "18,5 °C", font=_font(34), fill=(180, 186, 192), anchor="mm")
    d.line([(40, 135), (w - 40, 135)], fill=(80, 84, 90), width=2)
    d.text((w / 2, 230), "D", font=_font(130, True), fill=(235, 240, 245), anchor="mm")
    d.text((w / 2, 330), "S tronic", font=_font(32), fill=(160, 166, 172), anchor="mm")
    d.line([(40, 380), (w - 40, 380)], fill=(80, 84, 90), width=2)
    d.text((60, 430), "Autonomía", font=_font(30), fill=(160, 166, 172))
    d.text((w - 60, 430), "820 km", font=_font(34, True), fill=(235, 240, 245), anchor="ra")
    d.text((60, 490), "Consumo", font=_font(30), fill=(160, 166, 172))
    d.text((w - 60, 490), "4,6 l/100", font=_font(34, True), fill=(235, 240, 245), anchor="ra")
    d.text((w / 2, 590), "128 456 km", font=_font(30), fill=(160, 166, 172), anchor="mm")
    return np.asarray(im)


CONTENT = {"mmi_screen": mmi_screen, "fis_screen": fis_screen}


# --------------------------------------------------------------------------
# cache / file access
# --------------------------------------------------------------------------

def _save(arr, path, jpeg=False):
    im = Image.fromarray(arr)
    if jpeg:
        im.convert("RGB").save(path, quality=92)
    else:
        im.save(path, optimize=True)
    return path


def surface(key):
    """Generate (or reuse) the maps of a surface texture.
    Returns dict map -> file path, plus 'tile' and 'strength'."""
    gen, tile, strength = SURFACES[key]
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, f"{key}_v{VERSION}")
    names = {"normal": stem + "_normal.png", "rough": stem + "_rough.png",
             "ao": stem + "_ao.png", "albedo_var": stem + "_albedo.png"}
    marker = stem + ".ok"
    if not os.path.exists(marker):
        maps = gen()
        for k, arr in maps.items():
            _save(arr, names[k])
        open(marker, "w").write(",".join(maps))
    have = open(marker).read().split(",")
    out = {k: names[k] for k in have}
    out["tile"] = tile
    out["strength"] = strength
    return out


def content(key):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{key}_v{VERSION}.png")
    if not os.path.exists(p):
        _save(CONTENT[key](), p)
    return p
