# Video Stock PoC

Mini prueba de concepto para buscar videos stock mediante APIs oficiales y generar
artefactos livianos de revision humana para evaluacion temporal del pipeline
E-OVRT.

El objetivo no es construir un dataset de fine-tuning. La salida sirve para
identificar candidatos de video que permitan evaluar persistencia temporal,
ventanas de confirmacion y generacion de alertas en el plano de control.

## Requisitos

- Python 3.12 o compatible.
- `ffmpeg` disponible en el sistema.
- Archivo `.env` local en la raiz del repo `e-ovrt_datasets`.

Ejemplo de `.env`:

```bash
PEXELS_API_KEY=...
PIXABAY_API_KEY=...
```

El archivo `.env` esta ignorado por git.

## Uso Basico

Desde la raiz de `e-ovrt_datasets`:

```bash
python3 datasets/scripts/video_stock/video_stock_poc.py \
  --queries "construction worker" "hard hat worker" \
  --per-query 3 \
  --max-candidates 8 \
  --min-duration 4 \
  --max-duration 25
```

Salida por defecto:

```text
datasets/interim/video_stock_poc/
  videos/
  contact_sheets/
  reports/
    candidates.csv
    candidates.jsonl
    review_manifest.csv
```

Las salidas `datasets/interim/video_stock_poc*/` estan ignoradas por git porque
contienen videos y artefactos generados localmente.

## Segundo Run De Ejemplo

Para usar solo Pixabay y queries mas especificas:

```bash
python3 datasets/scripts/video_stock/video_stock_poc.py \
  --sources pixabay \
  --queries "construction safety vest" "construction hard hat" "road worker safety vest" "industrial worker helmet" \
  --per-query 4 \
  --max-candidates 10 \
  --min-duration 4 \
  --max-duration 25 \
  --out-dir datasets/interim/video_stock_poc_run2
```

## Parametros

- `--sources`: fuentes a consultar, separadas por coma. Valores actuales:
  `pexels,pixabay`.
- `--queries`: lista de queries textuales.
- `--per-query`: cantidad maxima solicitada por query y fuente.
- `--max-candidates`: cantidad maxima total de candidatos a materializar.
- `--min-duration`: duracion minima en segundos.
- `--max-duration`: duracion maxima en segundos.
- `--contact-frames`: cantidad objetivo de frames para la hoja de contacto.
- `--out-dir`: directorio de salida.

## Revision Humana

El archivo principal para revisar candidatos es:

```text
reports/review_manifest.csv
```

Columnas relevantes:

- `decision`: `pending`, `keep`, `discard`, `uncertain`.
- `source`: plataforma de origen.
- `source_id`: id de la plataforma.
- `query`: busqueda que produjo el candidato.
- `duration_s`: duracion del video.
- `source_url`: URL publica del recurso.
- `local_contact_sheet_path`: hoja de contacto generada.
- `expected_condition`: condicion esperada, por ejemplo `CR-01`, `CR-02`,
  `none` o `uncertain`.
- `worker_visible`: si hay trabajador visible.
- `helmet_state`: `worn`, `not_worn`, `unknown`.
- `vest_state`: `worn`, `not_worn`, `unknown`.
- `notes`: observaciones del revisor.

La revision inicial debe hacerse sobre las hojas de contacto, no sobre videos
completos. Solo los candidatos `keep` o `uncertain` deberian pasar a descarga o
normalizacion posterior.

## Consideraciones De Licencia

El script guarda metadata de origen y URLs de licencia:

- Pexels License: https://www.pexels.com/license/
- Pixabay Content License: https://pixabay.com/service/license-summary/

No redistribuir contenido stock como dataset standalone. Para uso academico,
mantener trazabilidad de fuente, autor, URL, fecha de descarga y licencia.

## Estado De La PoC

Durante la primera prueba, Pixabay devolvio candidatos validos y Pexels respondio
`HTTP 403`. El script no aborta si una fuente falla: reporta warning y continua
con las fuentes restantes.

