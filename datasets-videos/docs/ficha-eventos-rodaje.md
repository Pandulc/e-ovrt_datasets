# Ficha de eventos — rodaje 2026-07-25 (Bloque A)

**Generada:** 2026-07-27, desde los artefactos del recorte.

> ⚠️ **Procedencia de las marcas, leer antes de usar.** Los tiempos de este
> documento están **derivados del `episode_draft`** que escribió la consola —
> es decir, de las marcas que hizo el operador al recortar — y del `ss`
> recuperado por matching de frames contra el master. **No son una medición
> independiente del video.** Sirven como expectativa escrita para el chequeo
> cruzado contra CVAT (detectan clip equivocado, atributo invertido y `unknown`
> que parte un episodio), pero **no detectan un error sistemático de marcado**.
> Las filas verificadas contra el video están marcadas con ✅ en la columna `v`
> (medidas con tira de miniaturas, §5.4); el resto lleva ⋯ y sigue pendiente.

> **La ficha no es el ground truth.** El GT sale de CVAT frame a frame vía
> `derive_clip_gt.py`. Discrepancia ficha↔GT por debajo de 0,5 s: normal, se
> ignora. Por encima de 1,0 s: se investiga antes de promover el clip.

---

## Índice

| clip_id | master | cám | esc | dur master | ss | D | frames | estado |
|---|---|---|---|---:|---:|---:|---:|---|
| `a_p1_c02` | `P1-a-take2.mp4` | OAK-D | P1 | 57.0 s | 4.57 | 37.43 | 1123 | recortado |
| `a_p1_c03` | `P1-a-take3.mp4` | OAK-D | P1 | 34.7 s | 3.84 | 20.60 | 618 | recortado |
| `a_p1_c04` | `P1-a-take4.mp4` | OAK-D | P1 | 42.0 s | 5.23 | 30.67 | 920 | recortado |
| `a_p1_c05` | `P1-a-take5.mp4` | DVR | P1 | 37.9 s | 6.74 | 21.67 | 650 | recortado |
| `a_p1_c06` | `P1-b-take1.mp4` | DVR | P1 | 36.5 s | 4.07 | 25.17 | 755 | recortado |
| `a_p1_c07` | `P1-b-take3.mp4` | OAK-D | P1 | 38.3 s | 4.67 | 20.50 | 615 | recortado |
| `a_p1_c08` | `P1-b-take5.mp4` | OAK-D | P1 | 39.8 s | 5.90 | 23.63 | 709 | recortado |
| `a_p1_c09` | `P1-c-take2.mp4` | DVR | P1 | 36.9 s | 4.51 | 24.07 | 722 | recortado |
| `a_p1_c10` | `P1-c-take4.mp4` | DVR | P1 | 37.0 s | 2.36 | 28.63 | 859 | recortado |
| `a_p1_c11` | `P1-c-take5.mp4` | OAK-D | P1 | 40.2 s | 4.90 | 25.93 | 778 | recortado |
| `a_p1_c12` | `P1-c-take6.mp4` | OAK-D | P1 | 35.6 s | 4.90 | 25.07 | 752 | recortado |
| `a_p2_c01` | `P2-a-take1.mp4` | OAK-D | P2 | 48.5 s | 3.92 | 36.43 | 1093 | recortado |
| `a_p2_c02` | `P2-a-take2.mp4` | DVR | P2 | 50.8 s | 4.01 | 38.17 | 1145 | recortado |
| `a_p2_c03` | `P2-b-take1.mp4` | OAK-D | P2 | 44.9 s | 2.40 | 37.50 | 1125 | recortado |
| `a_p2_c04` | `P2-c-take1.mp4` | OAK-D | P2 | 49.8 s | 3.82 | 42.33 | 1270 | recortado |
| `a_p2_c05` | `P2-c-take2.mp4` | OAK-D | P2 | 51.4 s | 5.07 | 39.47 | 1184 | recortado |
| `a_p3_c01` | `P3-a-take1.mp4` | OAK-D | P3 | 22.3 s | 1.73 | 18.40 | 552 | recortado |
| `a_p3_c02` | `P3-a-take2.mp4` | OAK-D | P3 | 21.6 s | 2.30 | 18.50 | 555 | recortado |
| `a_p4_c01` | `P4-a-take1.mp4` | OAK-D | P4 | 40.1 s | 3.36 | 29.73 | 892 | recortado |
| `a_p4_c02` | `P4-a-take2.mp4` | DVR | P4 | 38.9 s | 3.45 | 31.67 | 950 | recortado |
| `a_p5_c01` | `P5-a-take1.mp4` | OAK-D | P5 | 41.4 s | 2.01 | 39.17 | 1175 | recortado |
| `a_p5_c02` | `P5-a-take2.mp4` | OAK-D | P5 | 55.6 s | 2.88 | 52.77 | 1583 | recortado |
| `a_p6_c01` | `P6-a-take1.mp4` | OAK-D | P6 | 55.4 s | 4.01 | 43.20 | 1296 | recortado |
| `a_p6_c02` | `P6-a-take2.mp4` | OAK-D | P6 | 71.0 s | 4.32 | 56.50 | 1695 | recortado |
| `a_p7_c01` | `P7-a-take1.mp4` | OAK-D | P7 | 50.1 s | 2.73 | 36.17 | 1085 | recortado |
| `a_p7_c02` | `P7-b-take1.mp4` | OAK-D | P7 | 44.7 s | 2.51 | 33.77 | 1013 | recortado |
| `a_p7_c03` | `P7-b-take2.mp4` | OAK-D | P7 | 43.5 s | 2.82 | 32.53 | 976 | recortado |
| `a_p7_c04` | `P7-b-take3.mp4` | DVR | P7 | 45.8 s | 4.26 | 32.80 | 984 | recortado |
| `a_p8_c01` | `P8-a-take1.mp4` | OAK-D | P8 | 54.1 s | 2.98 | 47.17 | 1415 | recortado |
| `a_p9_c01` | `P9-a-take1.mp4` | DVR | P9 | 26.9 s | 0.20 | 26.60 | 798 | recortado |
| `a_p9_c02` | `P9-a-take2.mp4` | OAK-D | P9 | 26.2 s | 0.57 | 25.67 | 770 | recortado |
| `a_p9_c03` | `P9-a-take3.mp4` | OAK-D | P9 | 23.6 s | 0.00 | 23.57 | 707 | recortado |
| `a_p9_c06` | `P9-b-take1.mp4` | OAK-D | P9 | 24.6 s | 0.08 | 24.57 | 737 | recortado |
| `a_p9_c08` | `P9-b-take2.mp4` | OAK-D | P9 | 23.1 s | 0.24 | 22.70 | 681 | recortado |

**Total:** 34 clips · 32182 frames a anotar (~17.9 min de video).

---

## Bloques por clip

### a_p1_c02 — master `P1-a-take2.mp4` (OAK-D, 57.0 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.07 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 39.02 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 34446] (ms, ±500)

Recorte: ss = **4.57** · D = **37.43 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c03 — master `P1-a-take3.mp4` (OAK-D, 34.7 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 7.34 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 21.45 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 17606] (ms, ±500)

Recorte: ss = **3.84** · D = **20.60 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c04 — master `P1-a-take4.mp4` (OAK-D, 42.0 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.73 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 32.88 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 27652] (ms, ±500)

Recorte: ss = **5.23** · D = **30.67 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c05 — master `P1-a-take5.mp4` (DVR, 37.9 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 10.24 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 25.38 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 18641] (ms, ±500)

Recorte: ss = **6.74** · D = **21.67 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c06 — master `P1-b-take1.mp4` (DVR, 36.5 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 7.57 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 26.23 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 22156] (ms, ±500)

Recorte: ss = **4.07** · D = **25.17 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c07 — master `P1-b-take3.mp4` (OAK-D, 38.3 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.17 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 22.17 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 17501] (ms, ±500)

Recorte: ss = **4.67** · D = **20.50 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c08 — master `P1-b-take5.mp4` (OAK-D, 39.8 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 9.40 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 26.52 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 20622] (ms, ±500)

Recorte: ss = **5.90** · D = **23.63 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c09 — master `P1-c-take2.mp4` (DVR, 36.9 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.01 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 25.55 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 21036] (ms, ±500)

Recorte: ss = **4.51** · D = **24.07 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c10 — master `P1-c-take4.mp4` (DVR, 37.0 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 5.86 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 27.97 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 25611] (ms, ±500)

Recorte: ss = **2.36** · D = **28.63 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c11 — master `P1-c-take5.mp4` (OAK-D, 40.2 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.40 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 27.82 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 22918] (ms, ±500)

Recorte: ss = **4.90** · D = **25.93 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p1_c12 — master `P1-c-take6.mp4` (OAK-D, 35.6 s) — escenario P1

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 8.40 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 26.97 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 22074] (ms, ±500)

Recorte: ss = **4.90** · D = **25.07 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p2_c01 — master `P2-a-take1.mp4` (OAK-D, 48.5 s) — escenario P2

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `chaleco_fuera` | 7.42 | CR-02 | ⋯ | onset ep. chaleco |
| 2 | `chaleco_puesto` | 35.34 | CR-02 | ⋯ | fin ep. chaleco |

**Episodios esperados en el GT:** CR-02 [3500, 31419] (ms, ±500)

Recorte: ss = **3.92** · D = **36.43 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p2_c02 — master `P2-a-take2.mp4` (DVR, 50.8 s) — escenario P2

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `chaleco_fuera` | 7.51 | CR-02 | ⋯ | onset ep. chaleco |
| 2 | `chaleco_puesto` | 37.17 | CR-02 | ⋯ | fin ep. chaleco |

**Episodios esperados en el GT:** CR-02 [3500, 33162] (ms, ±500)

Recorte: ss = **4.01** · D = **38.17 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p2_c03 — master `P2-b-take1.mp4` (OAK-D, 44.9 s) — escenario P2

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `chaleco_fuera` | 5.90 | CR-02 | ⋯ | onset ep. chaleco |
| 2 | `chaleco_puesto` | 34.91 | CR-02 | ⋯ | fin ep. chaleco |

**Episodios esperados en el GT:** CR-02 [3500, 32507] (ms, ±500)

Recorte: ss = **2.40** · D = **37.50 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p2_c04 — master `P2-c-take1.mp4` (OAK-D, 49.8 s) — escenario P2

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `chaleco_fuera` | 7.32 | CR-02 | ⋯ | onset ep. chaleco |
| 2 | `chaleco_puesto` | 41.16 | CR-02 | ⋯ | fin ep. chaleco |

**Episodios esperados en el GT:** CR-02 [3500, 37343] (ms, ±500)

Recorte: ss = **3.82** · D = **42.33 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p2_c05 — master `P2-c-take2.mp4` (OAK-D, 51.4 s) — escenario P2

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `chaleco_fuera` | 8.57 | CR-02 | ⋯ | onset ep. chaleco |
| 2 | `chaleco_puesto` | 39.55 | CR-02 | ⋯ | fin ep. chaleco |

**Episodios esperados en el GT:** CR-02 [3500, 34476] (ms, ±500)

Recorte: ss = **5.07** · D = **39.47 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p3_c01 — master `P3-a-take1.mp4` (OAK-D, 22.3 s) — escenario P3

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 5.10 | — | ✅ | onset ep. casco |
| 2 | `casco_puesto` | 7.90 | — | ✅ | fin REAL del transitorio (la marca del recorte fue artificial, ver abajo) |

**Episodios esperados en el GT:** ninguno — `sub_threshold_event` [3370, 6170] ms, transitorio de **2800 ms** (< 4000 ms, por eso NO es episodio).

> ⚠️ **La marca `casco_puesto` del recorte fue artificial** (t1 + 12 s = 17.12 s) para estirar el clip a la duración que pide el guion. El transitorio REAL termina a los **7.90 s** del master, que es lo que va a mostrar CVAT. El `episode_draft` del `.clip.yaml` NO refleja esto — usar esta ficha, no el borrador, para el chequeo cruzado.

Recorte: ss = **1.73** · D = **18.40 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p3_c02 — master `P3-a-take2.mp4` (OAK-D, 21.6 s) — escenario P3

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 5.80 | — | ✅ | onset ep. casco |
| 2 | `casco_puesto` | 8.10 | — | ✅ | fin REAL del transitorio (la marca del recorte fue artificial, ver abajo) |

**Episodios esperados en el GT:** ninguno — `sub_threshold_event` [3500, 5800] ms, transitorio de **2300 ms** (< 4000 ms, por eso NO es episodio).

> ⚠️ **La marca `casco_puesto` del recorte fue artificial** (t1 + 12 s = 17.79 s) para estirar el clip a la duración que pide el guion. El transitorio REAL termina a los **8.10 s** del master, que es lo que va a mostrar CVAT. El `episode_draft` del `.clip.yaml` NO refleja esto — usar esta ficha, no el borrador, para el chequeo cruzado.

Recorte: ss = **2.30** · D = **18.50 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p4_c01 — master `P4-a-take1.mp4` (OAK-D, 40.1 s) — escenario P4

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.86 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 23.09 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 19728] (ms, ±500)

Recorte: ss = **3.36** · D = **29.73 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p4_c02 — master `P4-a-take2.mp4` (DVR, 38.9 s) — escenario P4

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.95 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 25.09 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 21642] (ms, ±500)

Recorte: ss = **3.45** · D = **31.67 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p5_c01 — master `P5-a-take1.mp4` (OAK-D, 41.4 s) — escenario P5

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `ambos_en_cuadro` | 5.51 | — | ⋯ | inicio tramo limpio (sin episodio) |
| 2 | `fin_tramo_limpio` | 38.17 | — | ⋯ | fin tramo limpio (sin episodio) |

**Episodios esperados en el GT:** ninguno — `negative: true` (cumplimiento total)

Recorte: ss = **2.01** · D = **39.17 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p5_c02 — master `P5-a-take2.mp4` (OAK-D, 55.6 s) — escenario P5

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `ambos_en_cuadro` | 6.38 | — | ⋯ | inicio tramo limpio (sin episodio) |
| 2 | `fin_tramo_limpio` | 52.73 | — | ⋯ | fin tramo limpio (sin episodio) |

**Episodios esperados en el GT:** ninguno — `negative: true` (cumplimiento total)

Recorte: ss = **2.88** · D = **52.77 s** · onset_rel = **3500 ms**

> ⚠️ solo 2.9 s de cola, se necesitan 3

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p6_c01 — master `P6-a-take1.mp4` (OAK-D, 55.4 s) — escenario P6

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 7.51 | CR-01 | ⋯ | onset ep. casco |
| 2 | `chaleco_fuera` | 12.74 | CR-02 | ⋯ | onset ep. chaleco |
| 3 | `chaleco_puesto` | 39.91 | CR-02 | ⋯ | fin ep. chaleco |
| 4 | `casco_puesto` | 44.21 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 40199] · CR-02 [8732, 35905] (ms, ±500)

Recorte: ss = **4.01** · D = **43.20 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p6_c02 — master `P6-a-take2.mp4` (OAK-D, 71.0 s) — escenario P6

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 7.82 | CR-01 | ⋯ | onset ep. casco |
| 2 | `chaleco_fuera` | 13.13 | CR-02 | ⋯ | onset ep. chaleco |
| 3 | `chaleco_puesto` | 48.06 | CR-02 | ⋯ | fin ep. chaleco |
| 4 | `casco_puesto` | 57.82 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 53501] · CR-02 [8806, 43739] (ms, ±500)

Recorte: ss = **4.32** · D = **56.50 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p7_c01 — master `P7-a-take1.mp4` (OAK-D, 50.1 s) — escenario P7

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.23 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 35.91 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 33178] (ms, ±500)

Recorte: ss = **2.73** · D = **36.17 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p7_c02 — master `P7-b-take1.mp4` (OAK-D, 44.7 s) — escenario P7

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.01 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 33.27 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 30762] (ms, ±500)

Recorte: ss = **2.51** · D = **33.77 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p7_c03 — master `P7-b-take2.mp4` (OAK-D, 43.5 s) — escenario P7

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.32 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 32.36 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 29537] (ms, ±500)

Recorte: ss = **2.82** · D = **32.53 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p7_c04 — master `P7-b-take3.mp4` (DVR, 45.8 s) — escenario P7

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 7.76 | CR-01 | ⋯ | onset ep. casco |
| 2 | `casco_puesto` | 34.04 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 29778] (ms, ±500)

Recorte: ss = **4.26** · D = **32.80 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p8_c01 — master `P8-a-take1.mp4` (OAK-D, 54.1 s) — escenario P8

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `casco_fuera` | 6.48 | CR-01 | ⋯ | onset ep. casco |
| 2 | `sale_de_cuadro` | 20.60 | CR-01 | ⋯ | fin ep. 1 (sale de cuadro) |
| 3 | `vuelve` | 34.38 | CR-01 | ⋯ | onset ep. 2 (reingresa sin casco) |
| 4 | `casco_puesto` | 47.16 | CR-01 | ⋯ | fin ep. casco |

**Episodios esperados en el GT:** CR-01 [3500, 17619] · CR-01 [31398, 44179] (ms, ±500)

Recorte: ss = **2.98** · D = **47.17 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p9_c01 — master `P9-a-take1.mp4` (DVR, 26.9 s) — escenario P9

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `sujeto_completo_en_cuadro` | 3.70 | CR-01 | ⋯ | onset ep. (entra ya en infraccion) |
| 2 | `fin_accion` | 25.25 | CR-01 | ⋯ | fin ep. (sale de cuadro / termina) |

**Episodios esperados en el GT:** CR-01 [3500, 25051] (ms, ±500)

Recorte: ss = **0.20** · D = **26.60 s** · onset_rel = **3500 ms**

> ⚠️ solo 1.6 s de cola, se necesitan 3

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p9_c02 — master `P9-a-take2.mp4` (OAK-D, 26.2 s) — escenario P9

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `sujeto_completo_en_cuadro` | 4.07 | CR-01 | ⋯ | onset ep. (entra ya en infraccion) |
| 2 | `fin_accion` | 26.05 | CR-01 | ⋯ | fin ep. (sale de cuadro / termina) |

**Episodios esperados en el GT:** CR-01 [3500, 25479] (ms, ±500)

Recorte: ss = **0.57** · D = **25.67 s** · onset_rel = **3500 ms**

> ⚠️ solo 0.2 s de cola, se necesitan 3

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p9_c03 — master `P9-a-take3.mp4` (OAK-D, 23.6 s) — escenario P9

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `sujeto_completo_en_cuadro` | 2.83 | CR-01 | ⋯ | onset ep. (entra ya en infraccion) |
| 2 | `fin_accion` | 22.59 | CR-01 | ⋯ | fin ep. (sale de cuadro / termina) |

**Episodios esperados en el GT:** CR-01 [2832, 22585] (ms, ±500)

Recorte: ss = **0.00** · D = **23.57 s** · onset_rel = **2832 ms**

> ⚠️ solo 2.8 s de pre-roll, se necesitan 3.5 — el TTFD va a salir degradado
> ⚠️ solo 1.0 s de cola, se necesitan 3

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p9_c06 — master `P9-b-take1.mp4` (OAK-D, 24.6 s) — escenario P9

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `sujeto_completo_en_cuadro` | 3.58 | CR-01 | ⋯ | onset ep. (entra ya en infraccion) |
| 2 | `fin_accion` | 22.75 | CR-01 | ⋯ | fin ep. (sale de cuadro / termina) |

**Episodios esperados en el GT:** CR-01 [3500, 22674] (ms, ±500)

Recorte: ss = **0.08** · D = **24.57 s** · onset_rel = **3500 ms**

> ⚠️ solo 1.9 s de cola, se necesitan 3

Cuadro limpio: ⋯ · Notas de anotación: ⋯

### a_p9_c08 — master `P9-b-take2.mp4` (OAK-D, 23.1 s) — escenario P9

| # | marca | t (s) | condición | v | nota |
|---|---|---:|---|:-:|---|
| 1 | `sujeto_completo_en_cuadro` | 3.74 | CR-01 | ⋯ | onset ep. (entra ya en infraccion) |
| 2 | `fin_accion` | 19.95 | CR-01 | ⋯ | fin ep. (sale de cuadro / termina) |

**Episodios esperados en el GT:** CR-01 [3500, 19709] (ms, ±500)

Recorte: ss = **0.24** · D = **22.70 s** · onset_rel = **3500 ms**

Cuadro limpio: ⋯ · Notas de anotación: ⋯
