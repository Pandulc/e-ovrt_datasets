# `bench_v3` — bench de imágenes estratificado (2026-07-23)

Ampliación de `bench_obra` (147 imgs) con dos fuentes independientes auditadas: **CHV**
(académica, obra real) y **SHEL5K** (Mendeley, CC BY 4.0). Objetivo: reducir el intervalo de
confianza de las métricas por clase (`docs/operacion/66` del repo `docs`, plan de
ampliación) sin perder la trazabilidad de qué imagen viene de dónde.

## Cómo se arma

```bash
python3 datasets/scripts/curate/build_bench_v3.py
```

Fusiona por referencia los 4 COCOs curados de `processed/coco/bench/curated/` (ids
remapeados a un espacio global único; cada imagen conserva su campo `stratum`), y emite:

- `bench_v3.json` — el COCO fusionado, 4 clases canónicas (person/helmet/vest/bare_head).
- `bench_v3_manifest.json` — conteos por estrato + sha256 de cada fuente y del bench
  fusionado (congelamiento: cualquier cambio en una fuente cambia el sha256 visible).

### Verificar el freeze

El script escribe exactamente la serialización que hashea (`sort_keys=True`), así que la
verificación es directa con la herramienta obvia:

```bash
sha256sum datasets/processed/coco/bench/curated/bench_v3.json
# debe dar el `bench_v3_sha256` del manifest; ídem cada fuente vs `source_sha256`
```

Pinneado en `datasets/tests/test_bench_v3_freeze.py` (sha del agregado, sha de las 4
fuentes y conteos congelados; los tests se skippean si los artefactos no están en disco).
Nota histórica: hasta 2026-07-29 el JSON estaba escrito sin `sort_keys` y `sha256sum`
NO reproducía el `bench_v3_sha256` (había que re-serializar ordenado); el freeze era
válido igual — las fuentes coincidían byte a byte — pero no verificable directo. El
contenido del bench no cambió al alinearlo (mismos conteos, mismo `bench_v3_sha256`:
`4557024e…`), solo el orden de claves del archivo.

## Composición

| Estrato | Origen | Imágenes | Aporta |
|---|---|---|---|
| `bench_obra_test` + `bench_obra_val` | `construction_site_safety` curado (doc 63) | 147 | núcleo con pasada visual muestral, todas las clases con negativos explícitos |
| `chv` | CHV (académico, GitHub ZijianWang; grant "open for free use" de los autores, SIN licencia formal — cita obligatoria `wang2021ppe`, imágenes no redistribuibles; verificado 2026-07-29, ver `license_registry.md`) | 1.330 | 2ª fuente person/helmet/vest; **mejor AP de vest medido en el proyecto** (0.55–0.58) |
| `shel5k` | SHEL5K (Mendeley 9rcv8mm682 v4, CC BY 4.0) | 5.000 | 3ª fuente; **bare_head nativo** (6.120 instancias vs 61 del núcleo) + `person_gt_shel5k.json` (5.248 violadores CR-01) |
| **Total** | | **6.477** | |

## Salvedades por estrato (no se ocultan, se reportan)

- `bench_obra`: pasada visual **muestral** (36/147), no exhaustiva — mismo GT desde Sprint 2.
- `chv`: dominio mixto obra/industrial-adyacente (scoring original: "parcial"); algunas
  imágenes de stock con watermark. Sin negativos explícitos ⇒ no aporta CR-01/CR-02.
- `shel5k`: resolución uniforme 416×416 (preprocesado Roboflow — objetos gruesos, "obra" en
  sentido amplio: incluye industria/mantenimiento, no solo construcción civil);
  mirror-padding horneado en ~2–10% de las imágenes con GT sobre las franjas espejadas;
  `has_vest` no anotado (person_gt_shel5k solo cubre CR-01, nunca CR-02).

## Uso

Reportar SIEMPRE por estrato y agregado (nunca solo el agregado): un modelo puede rendir
distinto en 416×416 uniforme que en `bench_obra` de resolución variable. El agregado
ponderado por n es el número de cierre; el desglose por estrato es el diagnóstico.

Evaluación del media-plane contra el bench completo:

```bash
python -m eovrt_media.tools.evaluate --run runs/<run_id> \
  --bench-coco ../e-ovrt_datasets/datasets/processed/coco/bench/curated/bench_v3.json
```

Para CR-01 con GT persona-nivel, usar `curated/person_gt_bench_obra.json` (núcleo, 262
personas / 60 violadores CR-01) o `person_gt_shel5k.json` según qué imágenes procesó el
run — **no existe un person_gt fusionado** (los formatos son compatibles pero el runner ya
restringe por basename del run, así que evaluar cada fuente por separado y sumar
violadores/detectados es más trazable que fusionar de antemano).

> **PROHIBIDO para evaluación: `processed/coco/bench/person_gt.json` (18-jun) es
> HISTÓRICO.** Se construyó sobre el BENCH contaminado de 196 imágenes: 46 de sus 111
> violadores CR-01 (41%) viven en las 49 imágenes que la curación del 23-jul excluyó
> (selfies COVID, PASCAL VOC, …) — usarlo reintroduce la inflación ≈2× del recall CR-01
> que la curación corrigió. El GT vigente del núcleo es
> `curated/person_gt_bench_obra.json`, regenerable con:
>
> ```bash
> python3 datasets/scripts/bench/build_person_gt.py \
>   --coco datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_val.json \
>          datasets/processed/coco/bench/curated/construction_site_safety_bench_obra_test.json \
>   --out datasets/processed/coco/bench/curated/person_gt_bench_obra.json
> ```
>
> (60 y no 65 violadores: además de las 49 imágenes, la curación removió 4 `bare_head`
> sub-pixel en 2 imágenes conservadas — `curation_bench_obra.md` §2; verificado en
> `datasets/tests/test_person_gt_bench_obra.py`.)
