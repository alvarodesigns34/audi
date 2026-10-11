# Traspaso para una sesión nueva

Estado: **v0.3** (2026-10-11). Qué hay, cómo se trabaja y qué falta: `docs/STATUS.md`.
Convenciones de código: `docs/CONVENTIONS.md`. Uso rápido: `README.md`.

## Mapa del repositorio

| Ruta | Contenido |
|---|---|
| `src/a3/spec.py` | Ficha y cotas globales con etiquetas C/S/E |
| `src/a3/build.py` | Orden de construcción de las piezas (`PARTS`) |
| `src/a3/body/lines.py` | Líneas características en tablas en mm (perfil, tornado, cintura, techo…) |
| `src/a3/body/surface.py` | Piel por secciones + morro/zaga `EndCap` (perfil lateral × planta) |
| `src/a3/body/features.py` | Relieves locales: nervios del capó, aletas, banda del portón |
| `src/a3/body/openings.py` | Contornos medidos (ventanillas, puertas, faros, parrilla, pilotos…) y cortadores |
| `src/a3/body/shell.py` | Espesor + booleanas EXACT una a una; caché en `out/cache` |
| `src/a3/body/panels.py` | División del casco en paneles reales |
| `src/a3/body/glass.py` | Lunas, serigrafía y juntas |
| `src/a3/exterior/` | Frontal, faros, zaga, retrovisores, molduras, bajos, `chassis.py`, `engine.py`, `engine_bay.py` |
| `src/a3/wheels/` | Llanta 5-arm rotor, neumático 225/40 R18, frenos |
| `src/a3/interior/` | Habitáculo completo (`layout.py` centraliza cotas) y `boot.py` |
| `src/a3/core/` | Mallas, materiales PBR, `textures.py` (texturas por código), `uv.py`, render |
| `src/a3/groups.py` | 45 grupos de despiece, etiquetas en español, extras glTF |
| `docs/index.html` | Visor Three.js (HUD, despiece, cámaras, pinturas, luces) |
| `docs/models/` | GLB y USDZ publicados, calidad completa (tamaños en README) |
| `reference/` | Calibraciones `match_*.json`, puntos medidos `features.json`, `side_points.txt` |
| `tools/` | Construcción, medición fotogramétrica, depuración y publicación |

## Herramientas

- `tools/setup_env.sh` → Blender 5.2 como módulo en `/opt/bpyenv` (usar `/opt/bpyenv/bin/python`).
- `tools/fetch_references.sh` → fotos de Wikimedia Commons en `reference/photos/` (no versionadas).
- `tools/run.py` → construir y renderizar (`--views`, `--parts`, `--clay`, `--explode`, `--hide`, `--glb`).
- `tools/publish.sh` → regenera GLB, USDZ y `docs/renders/` (~20 min en CPU).
- Medición: `calib.py` (calibración robusta por contorno de llanta con rejilla de arranques y
  puntos de contacto; sustituye a `make_match.py`), `camera_match.py`, `bundle.py` (ajuste
  conjunto de todas las cámaras, coches y puntos de `reference/features.json`; `--write` guarda),
  `triangulate.py [--joint]`, `raycast_skin.py <foto> --check a,b` (píxel → punto 3D en la piel
  sin booleanas y reproyección en otras fotos), `skin_dist.py`, `lines_plot.py`, `epipolar.py`,
  `reproj_check.py`, `zoom.py` (recorte ampliado con rejilla de píxeles para digitalizar).
- Verificación: `compare.py foto1,foto2 --crop foto:x0,y0,x1,y1` (render completo por la cámara
  calibrada; `out/cmp/<foto>_pair.png` foto arriba / render abajo), `silhouette.py <foto>
  --outlines --lines`, `overlay.py`, `skin_preview.py`, `panel_debug.py`; vistas de detalle en
  `run.py --views hl_close,tl_close,rear_close,rear34_close,intake_close,side_close`.
- Visor sin GPU: servidor `python3 -m http.server` en `docs/` + Chromium headless
  (`/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell`,
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`) con `playwright-core`.

## Lecciones aprendidas (evitar repetir errores)

- Las booleanas EXACT se aplican de una en una; FAST rompe la malla. Cortadores simples y cerrados.
- Un prisma proyectado en un eje se ensancha en superficies oblicuas: para juntas usar
  `openings.ribbon_cutter` (anchura constante sobre la superficie).
- No nombrar objetos definitivos con prefijo `tmp`.
- Anisotropía en mallas sin UV sale negra en three.js (el visor la anula en ese caso).
- Las fotos de distintos coches tienen alturas de carrocería distintas: usar `triangulate.py --joint`.
- La foto lateral (`side.jpg`) no sirve para la zaga: otro coche rojo se funde con la silueta.
- Cambiar archivos de `src/a3/body/` invalida la caché: la carrocería tarda ~4–5 min en rehacerse.
- v0.3: las booleanas EXACT pueden fallar en silencio (borrar regiones enteras, dejar el cortador
  unido, no cortar). `shell.guarded_cut` verifica cada corte; mira el log (`[body] cut ... failed`).
  Causas encontradas: cortadores que se solapan (junta que entra en un paso de rueda o en un
  piloto ya cortado → cortar juntas antes que aberturas y recortarlas), cintas de superficie que
  se retuercen en una esquina (usar prismas), puntos duplicados en las cintas.
- v0.3: proyectar contornos desde un punto de vista falla en superficies que envuelven (pilares D:
  el rayo roza el alerón). Para la luneta se usa una carta radial (x, θ) alrededor de un eje
  longitudinal (`openings.to_xth / radial_cast`), 1:1 con la piel.
- v0.3: en `surface.EndCap.rings` los anillos deben densificarse hacia la sección de empalme
  (r = 1 − t^p, p > 1); al revés el final del techo y del capó era una sola faceta.
- Wikimedia limita peticiones (429): `fetch_references.sh` reintenta; la API de categorías también
  limita — usar la página web de la categoría `Category:Audi_A3_8V` para ver nombres de archivo.
- Fotos de coches distintos: S line blanco WI-RQ 1209 (`sline_front`, `sline_rear`, referencia),
  amarillo (`yellow`, `yellow_rear`, +24 mm de altura), rojo de salón (`side`, `rearq`, `rearsq`).

## Prompt de continuación

Ver el bloque que el propietario pega en la sesión nueva (también abajo). Al empezar: instalar,
bajar fotos, `python tools/run.py --views front34` para poblar la caché y
`python tools/compare.py sline_rear,yellow_rear,rearsq,sline_front,yellow` para ver el estado.

```text
Continúa el proyecto "Audi A3 Sportback 8V — Digital Twin" en el repositorio
alvarodesigns34/audi (rama main). Es la réplica 3D procedural (Blender 5.2 como módulo de
Python, todo generado por código) de MI coche: Audi A3 Sportback 8V pre-restyling (8VA,
2013–2016), 2.0 TDI 150 CV S tronic, tracción delantera, S line, blanco, interior de cuero
negro, volante de 4 radios, MMI con pantalla emergente, climatizador bizona y llantas Audi
exclusive 18" 5-arm rotor negro brillante diamantadas (8J×18 ET46, 225/40 R18). Volante a la
izquierda (España). Se publica en GitHub Pages (main, /docs):
https://alvarodesigns34.github.io/audi/ — visor Three.js con HUD y vista despiezada, GLB y
USDZ de calidad completa.

Antes de tocar nada, lee README.md, docs/HANDOFF.md (mapa del repo, herramientas y lecciones
aprendidas), docs/STATUS.md (estado v0.3, errores conocidos, decisiones y preguntas abiertas)
y docs/CONVENTIONS.md, y revisa el código de src/a3/ y tools/. Instala el entorno con
tools/setup_env.sh y baja las fotos con tools/fetch_references.sh.

El modelo todavía tiene MUCHÍSIMO que mejorar: está muy simplificado y tiene errores de todo
tipo (formas y proporciones, superficies, piezas que faltan, detalle exterior e interior,
materiales, mecánica). Mejóralo muchísimo: corrige errores de forma de toda la carrocería,
añade muchas más piezas y mucho más detalle por todas partes, exterior, interior y mecánica.
Valida cada cambio de forma con renders y superposición sobre las fotos calibradas (calibra
más si hace falta) y no des nada por bueno sin compararlo visualmente.

Reglas: háblame siempre en español; no inventes datos (marca lo estimado como E); busca la
causa raíz de los problemas; nunca simplifiques ni diezmes los modelos publicados (si un
archivo supera 100 MB usa compresión sin pérdida visible o divídelo); haz commits frecuentes
y súbelo todo a main; actualiza README, docs/STATUS.md, docs/HANDOFF.md y docs/renders/ al
terminar; si necesitas una decisión mía, pregúntamela al final con opciones claras.
```
