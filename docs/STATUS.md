# Estado del gemelo digital

Última actualización: 2026-10-10 (v0.1, primera versión completa: exterior + interior + ruedas).
Modelo publicado: `docs/models/a3_sportback_8v.glb` (32 MB, sin compresión ni simplificación,
1,7 M triángulos, 608 objetos) y `docs/models/a3_sportback_8v.usdz` (40 MB, iPhone/iPad).

## Precisión por zona

| Zona | Base | Precisión estimada | Comentario |
|---|---|---|---|
| Dimensiones globales (L, A, H, batalla, vías, voladizos) | Ficha oficial / fuentes secundarias | ±5 mm | C/S en `spec.py` |
| Silueta lateral, techo, extremos | 4 fotos calibradas (camera matching) | ±20–40 mm | Contrastado con superposiciones |
| Líneas tornado y de cintura | Fotos calibradas | ±20–30 mm | |
| Puertas, pilares B/C, tiradores, tapa combustible | Retroproyección foto lateral + 3/4 | ±30 mm | Las dos fotos difieren ~100 mm en x en algunos puntos; se priorizó la lateral |
| Parrilla, faros, tomas, pilotos, escape | Trazado de rayos desde fotos 3/4 calibradas | ±15–30 mm | |
| Llanta 5-arm rotor | Medición angular sobre foto rectificada | Forma S/E | 8J×18 ET46 (C) |
| Neumático 225/40 R18 | ETRTO | C | Dibujo de banda genérico (sin marca) |
| Frenos | Catálogo (312×25 / 272×10) | S/E | Pinza delante del disco según fotos |
| Interior | Fotos 8V pre-restyling + envolvente medida de la carrocería | E | Punto H y volante estimados |

## Errores y carencias conocidos (por prioridad)

**Carrocería / proporciones**
1. Superficies demasiado "blandas": falta la nitidez de la línea *tornado* (radio real ~3–5 mm),
   el hombro sobre las ruedas y la superficie cóncava bajo la línea.
2. Capó: faltan los dos nervios en V que nacen de las esquinas de la parrilla; el borde
   delantero del capó y la junta con faros/parrilla son aproximados.
3. Pasos de rueda: corte circular simple; faltan el labio enrollado, la leve aleta del 8V y la
   forma real (ligeramente achatada); hueco rueda-aleta a revisar con fotos.
4. Frontal visto de frente: el paragolpes inferior resulta demasiado ancho/abombado; el faro es
   algo bajo y estrecho comparado con la foto; la parrilla debe sobresalir más (marco cromado
   con relieve) y la toma inferior S line tiene detalles simplificados.
5. Zaga: luneta y montantes D aproximados; alerón de techo S line demasiado grueso y largo;
   portón sin el nervio horizontal sobre la matrícula ni el rebaje de matrícula; pilotos con
   gráfica interior genérica (falta la firma LED real del pre-restyling).
6. Retrovisores: forma de carcasa no fiel (la tapa superior y la base negra no coinciden con
   la foto `sline_front.jpg`, zona x≈1180–1320 px).
7. Cristales: cuarto cristal trasero y marco DLO simplificados; sin tiras/canales de goma reales.
8. Faldones S line, molduras de puertas inferiores y emblemas (S line, A3, TDI) básicos o ausentes.
9. Bajos del coche: bandeja plana; faltan suspensión visible, escape completo, depósito, etc.
10. Hueco motor cerrado con paneles oscuros (no hay motor 2.0 TDI modelado).

**Ruedas**: buenas; revisar alojamientos de tornillos (más redondeados en la foto) y añadir
suspensión visible tras la llanta.

**Interior**: correcto en distribución, pero con mucha geometría genérica: salpicadero sin las
superficies reales del 8V (ala y visera), asientos S line simplificados, sin maletero, sin
pasos de rueda traseros interiores, cinturones básicos, botones sin rotulación, pantallas con
gráficos muy simples.

**Materiales**: sin texturas reales (solo ruido procedural para el grano). Faltan: grano de
cuero y perforado, tejido de techo, plásticos texturados, escamas del metalizado, textos del
neumático por textura/normal map, gráficos de pantallas y cuadro.

## Decisiones tomadas (revisables con el propietario)

* **Color**: *Ibisweiß* (blanco sólido, T9). Alternativa: *Gletscherweiß metallic* (`--paint glacier_white`).
* **Parrilla S line**: marco cromado, lamas horizontales negro brillante y nervios verticales.
* **Molduras de ventanas**: negras (de serie). Configurable (`body/glass.py`, `WINDOW_TRIM`).
* **Matrícula**: genérica española `1234 ABC`.
* **Lunas**: sin oscurecer. **Techo**: chapa pintada, sin panorámico ni barras.
* **Escape**: doble salida cromada a la izquierda, integrada en el difusor S line.
* **Neumático**: aplastamiento por carga como *shape key* "Loaded".

## Preguntas abiertas al propietario

1. El primer mensaje se cortó en "IMPORTANTE: el vehículo debe corres…" (¿corresponder a…?).
2. ¿Blanco Ibis (sólido) o Glaciar metalizado?
3. ¿Marco de parrilla cromado o negro? ¿Molduras de ventanas negras o aluminio?
4. ¿Cristales traseros oscurecidos? ¿Techo panorámico / barras?
5. Fotos del coche real (4 ortogonales + 2 a 3/4 + interior) para calibrarlas con
   `tools/camera_match.py` y ajustar el modelo a su unidad.
