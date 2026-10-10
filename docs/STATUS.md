# Estado del gemelo digital

Fecha: 2026-10-10. Primera versión completa (exterior + interior + ruedas).

## Precisión por zona

| Zona | Base | Precisión estimada | Comentario |
|---|---|---|---|
| Dimensiones globales (L, A, H, batalla, vías, voladizos) | Ficha oficial / fuentes secundarias | ±5 mm | C/S en `spec.py` |
| Silueta lateral, techo, extremos | 4 fotos calibradas (camera matching) | ±20–40 mm | Contrastado con superposiciones |
| Líneas tornado y de cintura | Fotos calibradas | ±20–30 mm | |
| Puertas, pilares B/C, tiradores, tapa combustible | Retroproyección foto lateral + 3/4 | ±30 mm | Dos fotos difieren ~100 mm en x en algunos puntos; se ha priorizado la lateral |
| Parrilla, faros, tomas, pilotos, escape | Trazado de rayos desde fotos 3/4 calibradas | ±15–30 mm | |
| Llanta 5-arm rotor | Medición angular sobre foto rectificada | Forma S/E | 8J×18 ET46 (C) |
| Neumático 225/40 R18 | Norma ETRTO | C | Dibujo de banda genérico (sin marca) |
| Frenos | Catálogo (312×25 / 272×10) | S/E | Pinza delante del disco según fotos |
| Interior | Fotos 8V pre-restyling + envolvente medida de la carrocería | E | Punto H y volante estimados |

## Decisiones tomadas (revisables)

* **Color**: *Ibisweiß* (blanco sólido, T9). Alternativa disponible: *Gletscherweiß metallic*
  (`--paint glacier_white`).
* **Parrilla S line**: marco cromado, lamas horizontales negro brillante y nervios verticales
  titanio (como el S line de lanzamiento). Configurable en `exterior/front_end.py`.
* **Molduras de ventanas**: negras (de serie). Configurable (`body/glass.py`, `WINDOW_TRIM`).
* **Matrícula**: genérica española `1234 ABC`.
* **Lunas**: incoloras/verdosas (sin cristales traseros oscurecidos).
* **Escape**: doble salida cromada a la izquierda, integrada en el difusor S line.
* **Techo**: chapa pintada (sin techo panorámico ni barras).
* **Neumático**: aplastamiento por carga como *shape key* "Loaded" (valor 1 por defecto).

## Pendiente / siguientes iteraciones

* Afinar retrovisores (forma de la carcasa) y faros (gráfica interior del xenón).
* Paso de rueda: labio enrollado y ligera aleta del 8V.
* Superficie del capó (nervios en V) y relieve del portón.
* Limpiaparabrisas trasero y antena: revisar forma.
* Interior: maletero, pasos de rueda traseros interiores; texturas de perforado reales si se
  desean (ahora solo ruido procedural).
* Validar con fotos del coche real del propietario (lo ideal: 4 fotos ortogonales + 2 a 3/4,
  y fotos del interior) para personalizar detalles (opciones, matrícula, pegatinas, etc.).
