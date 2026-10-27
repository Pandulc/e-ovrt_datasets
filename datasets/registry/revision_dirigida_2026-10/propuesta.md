# Propuesta de correcciones — revision-dirigida-2026-10

Revisor: **simon** · terminado: True · guardado 2026-10-26T01:02:10+00:00

**Respuestas sin dar en total: 0.**

Corrida en seco: nada de esto está aplicado al laboratorio. Cada clip se probó sobre una copia con las herramientas reales y se re-derivó el GT.

## c1 · a_p7_c02 — Cruce entre personas (casco)


**Correcciones de identidad:** 12 · **de atributo:** 9 (59 cajas)

- `{"op": "reassign", "from_track": 597, "to_track": 607, "from_frame": 246, "to_frame": 249, "boxes": 4}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja D (trayectoria 597) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 598, "to_track": 607, "from_frame": 267, "to_frame": 287, "boxes": 21}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja E (trayectoria 598) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 599, "to_track": 607, "from_frame": 288, "to_frame": 297, "boxes": 10}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja F (trayectoria 599) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 601, "to_track": 607, "from_frame": 348, "to_frame": 356, "boxes": 9}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja G (trayectoria 601) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 602, "to_track": 607, "from_frame": 357, "to_frame": 363, "boxes": 7}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja H (trayectoria 602) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 603, "to_track": 607, "from_frame": 396, "to_frame": 807, "boxes": 412}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R1: la caja I (trayectoria 603) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 604, "to_track": 607, "from_frame": 810, "to_frame": 978, "boxes": 169}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R2: en la trayectoria 604, las muestras desde 27,60 s son P (antes: «Q»); el cambio de persona se ubica en 27,00 s
- `{"op": "fill", "track": 607, "from_frame": 196, "to_frame": 245, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R3: de 6,53 s a 8,17 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo (lo deja a los ~3,5 s y lo vuelve a tomar a los ~29,5 s).»; has_vest: «Claude: el chaleco naranja se le ve cada vez que asoma (8,2, 8,9–9,9 y 11,6–12,1 s).». Nota del tramo: «Claude: P queda detrás de Q en el mismo lugar; asoma a los 8,2, 8,9–9,9 y 11,6–12,1 s (cajas D a H) y vuelve a aparecer entero a los 13,2 s. No cruza ningún borde de la imagen.»
- `{"op": "fill", "track": 607, "from_frame": 250, "to_frame": 266, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R3: de 8,33 s a 8,87 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo (lo deja a los ~3,5 s y lo vuelve a tomar a los ~29,5 s).»; has_vest: «Claude: el chaleco naranja se le ve cada vez que asoma (8,2, 8,9–9,9 y 11,6–12,1 s).». Nota del tramo: «Claude: P queda detrás de Q en el mismo lugar; asoma a los 8,2, 8,9–9,9 y 11,6–12,1 s (cajas D a H) y vuelve a aparecer entero a los 13,2 s. No cruza ningún borde de la imagen.»
- `{"op": "fill", "track": 607, "from_frame": 298, "to_frame": 347, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R3: de 9,93 s a 11,57 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo (lo deja a los ~3,5 s y lo vuelve a tomar a los ~29,5 s).»; has_vest: «Claude: el chaleco naranja se le ve cada vez que asoma (8,2, 8,9–9,9 y 11,6–12,1 s).». Nota del tramo: «Claude: P queda detrás de Q en el mismo lugar; asoma a los 8,2, 8,9–9,9 y 11,6–12,1 s (cajas D a H) y vuelve a aparecer entero a los 13,2 s. No cruza ningún borde de la imagen.»
- `{"op": "fill", "track": 607, "from_frame": 364, "to_frame": 395, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R3: de 12,13 s a 13,17 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo (lo deja a los ~3,5 s y lo vuelve a tomar a los ~29,5 s).»; has_vest: «Claude: el chaleco naranja se le ve cada vez que asoma (8,2, 8,9–9,9 y 11,6–12,1 s).». Nota del tramo: «Claude: P queda detrás de Q en el mismo lugar; asoma a los 8,2, 8,9–9,9 y 11,6–12,1 s (cajas D a H) y vuelve a aparecer entero a los 13,2 s. No cruza ningún borde de la imagen.»
- `{"op": "fill", "track": 607, "from_frame": 808, "to_frame": 809, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c1 (a_p7_c02), R4: hueco de 2 cuadro(s) entre dos cajas de P con el mismo estado (casco false, chaleco true): oclusión breve, protocolo §7.1
- `has_helmet` trayectoria 607 cuadros 892–896 (29,73 s–29,87 s): false → true
- `has_helmet` trayectoria 607 cuadros 247–249 (8,23 s–8,30 s): unknown → false
- `has_helmet` trayectoria 607 cuadros 296–297 (9,87 s–9,90 s): unknown → false
- `has_vest` trayectoria 607 cuadros 193–195 (6,43 s–6,50 s): unknown → true
- `has_vest` trayectoria 607 cuadros 247–249 (8,23 s–8,30 s): unknown → true
- `has_vest` trayectoria 607 cuadros 268–287 (8,93 s–9,57 s): unknown → true
- `has_vest` trayectoria 607 cuadros 290–297 (9,67 s–9,90 s): unknown → true
- `has_vest` trayectoria 607 cuadros 348–356 (11,60 s–11,87 s): unknown → true
- `has_vest` trayectoria 607 cuadros 358–363 (11,93 s–12,10 s): unknown → true

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-01', 13200, 26933)] | 11 |
| GT con las correcciones | [('CR-01', 3033, 29733)] | 4 |

## c2 · a_p7_c03 — Cruce entre personas (casco), otra toma


**Correcciones de identidad:** 7 · **de atributo:** 8 (55 cajas)

- `{"op": "reassign", "from_track": 608, "to_track": 610, "from_frame": 309, "to_frame": 318, "boxes": 10}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R1: la caja C (trayectoria 608) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 609, "to_track": 610, "from_frame": 327, "to_frame": 975, "boxes": 648}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R1: la caja D (trayectoria 609) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 628, "to_track": 610, "from_frame": 471, "to_frame": 471, "boxes": 1}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R1: la caja E (trayectoria 628) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "drop", "track": 629, "boxes": 1}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R1: la caja F (trayectoria 629) fue respondida «P»; P ya tiene caja en esos cuadros: caja duplicada
- `{"op": "drop", "track": 630, "boxes": 1}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R1: la caja G (trayectoria 630) fue respondida «P»; P ya tiene caja en esos cuadros: caja duplicada
- `{"op": "fill", "track": 610, "from_frame": 245, "to_frame": 308, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R3: de 8,17 s a 10,27 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo.»; has_vest: «Claude: el chaleco naranja asoma a los costados de Q y se ve entero al reaparecer.». Nota del tramo: «Claude: P queda detrás de Q; el naranja de su chaleco asoma a los costados de Q (8,0–9,3 s) y su cabeza asoma a los 10,3 s. No cruza ningún borde de la imagen.»
- `{"op": "fill", "track": 610, "from_frame": 319, "to_frame": 326, "values": {"has_helmet": "false", "has_vest": "true"}}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c2 (a_p7_c03), R3: de 10,63 s a 10,87 s P sigue en cuadro, tapado («Sigue en cuadro, tapado por otra persona o por un objeto»); casco false, chaleco true. Notas del revisor: has_helmet: «Claude: el casco de P está sobre la mesa, a la vista, durante todo el tramo.»; has_vest: «Claude: el chaleco naranja asoma a los costados de Q y se ve entero al reaparecer.». Nota del tramo: «Claude: P queda detrás de Q; el naranja de su chaleco asoma a los costados de Q (8,0–9,3 s) y su cabeza asoma a los 10,3 s. No cruza ningún borde de la imagen.»
- `has_helmet` trayectoria 610 cuadros 327–327 (10,90 s–10,90 s): unknown → false
- `has_helmet` trayectoria 610 cuadros 329–332 (10,97 s–11,07 s): unknown → false
- `has_helmet` trayectoria 610 cuadros 336–347 (11,20 s–11,57 s): unknown → false
- `has_helmet` trayectoria 610 cuadros 856–863 (28,53 s–28,77 s): false → true
- `has_helmet` trayectoria 610 cuadros 242–244 (8,07 s–8,13 s): unknown → false
- `has_vest` trayectoria 610 cuadros 244–244 (8,13 s–8,13 s): unknown → true
- `has_vest` trayectoria 610 cuadros 309–318 (10,30 s–10,60 s): unknown → true
- `has_vest` trayectoria 610 cuadros 327–342 (10,90 s–11,40 s): unknown → true

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-01', 3000, 8067), ('CR-01', 11600, 32533)] | 4 |
| GT con las correcciones | [('CR-01', 3000, 28533)] | 1 |

## c3 · a_p1_c05 — Casco, una persona


**Correcciones de identidad:** 0 · **de atributo:** 1 (18 cajas)

- `has_helmet` trayectoria 566 cuadros 381–398 (12,70 s–13,27 s): true → false

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-01', 3900, 12700), ('CR-01', 13300, 18400)] | 0 |
| GT con las correcciones | [('CR-01', 3900, 18400)] | 0 |

## c4 · a_p2_c01 — Chaleco, una persona


**Correcciones de identidad:** 0 · **de atributo:** 1 (39 cajas)

- `has_vest` trayectoria 574 cuadros 94–132 (3,13 s–4,40 s): true → false

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-02', 4433, 29400)] | 0 |
| GT con las correcciones | [('CR-02', 3133, 29400)] | 0 |

## c5 · a_p2_c02 — Chaleco, una persona (otra toma)


**Correcciones de identidad:** 0 · **de atributo:** 1 (44 cajas)

- `has_vest` trayectoria 575 cuadros 109–152 (3,63 s–5,07 s): true → false

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-02', 5100, 32500)] | 0 |
| GT con las correcciones | [('CR-02', 3633, 32500)] | 0 |

## c6 · a_p9_c08 — Entrada a cuadro (casco)


**Correcciones de identidad:** 0 · **de atributo:** 1 (7 cajas)

- `has_helmet` trayectoria 624 cuadros 69–75 (2,30 s–2,50 s): false → unknown

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-01', 2300, 22033)] | 0 |
| GT con las correcciones | [('CR-01', 2533, 22033)] | 0 |

## c7 · a_p2_c05 — Chaleco, final de la toma


**Correcciones de identidad:** 0 · **de atributo:** 2 (16 cajas)

- `has_vest` trayectoria 578 cuadros 954–967 (31,80 s–32,23 s): true → false
- `has_vest` trayectoria 578 cuadros 1027–1028 (34,23 s–34,27 s): false → true

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-02', 3233, 31800)] | 1 |
| GT con las correcciones | [('CR-02', 3233, 34233)] | 0 |

## c8 · a_p8_c01 — Sale de cuadro y vuelve (casco)


**Correcciones de identidad:** 2 · **de atributo:** 6 (13 cajas)

- `{"op": "reassign", "from_track": 614, "to_track": 616, "from_frame": 873, "to_frame": 918, "boxes": 17}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c8 (a_p8_c01), R1: la caja B (trayectoria 614) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `{"op": "reassign", "from_track": 615, "to_track": 616, "from_frame": 924, "to_frame": 1413, "boxes": 490}` — respuestas propuestas por Claude y validadas por simon; registro en datasets/registry/revision_dirigida_2026-10/), caso c8 (a_p8_c01), R1: la caja C (trayectoria 615) fue respondida «P»; es la misma persona, va en la misma trayectoria (protocolo §7.1, regla C1)
- `has_helmet` trayectoria 616 cuadros 476–480 (15,87 s–16,00 s): false → unknown
- `has_helmet` trayectoria 616 cuadros 492–492 (16,40 s–16,40 s): false → unknown
- `has_helmet` trayectoria 616 cuadros 888–888 (29,60 s–29,60 s): false → unknown
- `has_helmet` trayectoria 616 cuadros 918–918 (30,60 s–30,60 s): false → unknown
- `has_helmet` trayectoria 616 cuadros 927–929 (30,90 s–30,97 s): false → unknown
- `has_helmet` trayectoria 616 cuadros 931–932 (31,03 s–31,07 s): unknown → false

| | Episodios | Sub-umbral |
|---|---|---|
| GT vigente | [('CR-01', 3067, 16033), ('CR-01', 31100, 43300)] | 4 |
| GT con las correcciones | [('CR-01', 3067, 15867), ('CR-01', 31033, 43300)] | 0 |

