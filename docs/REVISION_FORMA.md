# Revisión de forma de v0.3 (paso 0)

Fecha: 2026-10-16. Estado de partida: `main` en `4377e21` (v0.3 más el limpialuneta y el labio del
alerón, sin republicar).

## Cómo se ha revisado

* Construcción completa con Blender 5.2.2 de escritorio en Windows (`tools/blender.sh tools/run.py`,
  render con OptiX en una RTX 3070): 858 mallas, 2 001 375 triángulos, 45 grupos, sin booleanas
  fallidas en el registro (`guarded_cut` restauró caras en varios cortes, como estaba previsto).
* Render con materiales (`out/renders`), en arcilla (`--clay`, `out/clay`: 12 vistas, incluidas las
  de detalle) y comparación por las cámaras calibradas de 7 fotos (`tools/compare.py
  sline_rear,yellow_rear,rearsq,sline_front,yellow,side,rearq`).
* El render publicado `docs/renders/rear34.png` muestra los mismos defectos de la zaga: no es un
  efecto de Windows ni de la GPU, el modelo de v0.3 ya estaba así.

La silueta general (longitud, altura, batalla, posición de ruedas, línea de techo, invernadero
lateral) coincide bien con las fotos calibradas. Los errores están en la piel y en el detalle.

## Errores por zona (por gravedad)

### 1. Zaga: luneta, portón y alerón (grave, se ve desde cualquier vista trasera)

* La chapa del portón alrededor de la luneta está rasgada: borde irregular, agujeros por los que
  se ve el interior y triángulos negros (luna o serigrafía) que salen fuera del contorno de la
  luneta hacia los pilares D y hacia la zona de los pilotos (`rear34`, `rear34_close`,
  `tl_close`, `sline_rear`, `yellow_rear`, `rearq`).
* El alerón sale deformado: superficie con pliegues y "aletas" sueltas en sus extremos, sin el
  canto limpio de la foto.
* La parte de los pilotos que va en el portón tiene un parche blanco/transparente en lugar de
  lente (`yellow_rear`, `rearq`, `tl_close`).
* Causa a investigar: el corte de la luneta en la carta radial (`openings.to_xth / radial_cast`)
  y la clasificación del portón en `panels.py`; posiblemente el corte se hace pero la luna
  (`glass.py`) y la serigrafía no siguen el mismo contorno.

### 2. Zaga: pilotos y paragolpes

* Pilotos: lente roja oscura uniforme; falta la gráfica interior que define al 8V (barra LED
  superior, guía en "U", reflector, marcha atrás) visible en `rearq` y `sline_rear`.
* Difusor: banda negra plana demasiado alta y ancha; en las fotos es más estrecha, con rejilla y
  canto inferior gris, y las salidas de escape asoman dentro de su recorte.
* Detrás de la rueda trasera sobresale una pieza negra (faldilla o guardabarros interior) que no
  existe en el coche real (`rear34`, `sline_rear`, `yellow_rear`).
* Moldura cromada a lo ancho del portón sobre el paragolpes: en `sline_rear` (S line blanco) no se
  ve; revisar si existe en el pre-restyling.

### 3. Frontal

* Capó con ondulaciones y facetas visibles en arcilla (`hl_close`, `top`), sobre todo junto a los
  faros y hacia el parabrisas.
* Faro: interior oscuro sin la firma de la luz diurna LED a lo largo del borde inferior, con una
  franja naranja en lo alto que no corresponde a la foto; el proyector y la lama cromada apenas se
  leen.
* Paragolpes: el nervio vertical por fuera de la toma lateral S line sale facetado y con un canto
  irregular (`intake_close`).
* Tras el parabrisas se ve una forma blanca grande en las vistas frontales y un rectángulo blanco
  delante del conductor en `cockpit`: pieza o luz sin identificar (a investigar).

### 4. Lateral

* Línea tornado poco marcada: en la foto `side` es una arista nítida de faro a piloto; en arcilla
  casi no se lee.
* Manetas: el hueco embutido es demasiado grande y difuso (mancha de sombra alrededor de cada
  maneta).
* Retrovisores: cabeza ~25 mm alta y brazo saliendo de la base de la ventanilla; ya medido en
  `docs/STATUS.md`, sin implementar.
* Insignia S line 77 mm adelantada y 33 mm alta (medida en `STATUS.md`, sin implementar).

### 5. Interior (muy simplificado)

* Volante: aro demasiado grueso; los radios y las botoneras son cajas; no se parece al volante de
  cuatro radios de `cockpit.jpg`.
* Salpicadero: bloque plano y cuadrado, sin el "ala" que recorre el salpicadero del 8V ni la
  visera del cuadro bien formada.
* Asientos: volúmenes simples; faltan laterales, costuras y reposacabezas S line.
* Techo interior, asideros, parasoles y retrovisor interior: básicos o ausentes.

### 6. Ruedas, mecánica y bajos

* Llanta 5-arm rotor: forma general correcta; queda revisarla con más detalle al llegar al paso 4.
* Mecánica y bajos: estimados (E), no revisados en esta pasada.

## Orden de corrección propuesto

1. Zaga (luneta, portón, alerón, pilotos): es el defecto más visible y está en todas las vistas
   traseras.
2. Pendientes medidos: retrovisores e insignia S line.
3. Capó, faro, tornado y manetas.
4. Interior.
