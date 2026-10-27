# Scripts de descarga — v2

## Recrear las imágenes de los bancos desde su fuente (✎ 2026-10-27)

Los bancos de imágenes **no son datasets modificados**: `bench_v3.json`, sus estratos y los JSON
curados de obra son anotaciones y listas versionadas en git que apuntan a las imágenes
**originales, sin tocar**. Para reproducir una medición en otra máquina alcanza con bajar cada
fuente con su script y verificar las imágenes por huella: si coinciden byte a byte, son las
mismas con las que se midió.

| Fuente | Qué usa | Script | Clave | Verificación (desde la raíz del repo) |
|---|---|---|---|---|
| CHV | estrato `chv` de bench_v3 (1.330) | `download_chv.sh` | no | `sha256sum -c datasets/registry/bench_v3_imagenes.sha256` |
| SHEL5K | estrato `shel5k` de bench_v3 (5.000) | `download_shel5k.sh` | no | ídem |
| construction_site_safety **v27** | estrato `bench_obra` (147 curadas) y las carpetas `valid`/`test` completas (114 + 82) | `download_construction_site_safety.sh` | `ROBOFLOW_API_KEY` | ídem + `sha256sum -c datasets/registry/imagenes_obra_y_mocs.sha256` |
| MOCS (copia Roboflow `mocs-bowib` v1) | piloto de clase nueva, `valid` (151) | `download_mocs.sh` | `ROBOFLOW_API_KEY` | `sha256sum -c datasets/registry/imagenes_obra_y_mocs.sha256` |

- **La clave de Roboflow** es personal y gratuita: se crea una cuenta en roboflow.com y se copia
  la *Private API Key* de la configuración del workspace. No se commitea.
- **La estructura de `bench_v3`** se verifica sin escribir nada:
  `python3 datasets/scripts/curate/build_bench_strata.py --verify` (estratos byte a byte contra el
  manifiesto).
- **Si una imagen no coincide** (la fuente cambió o el export se regeneró distinto), no se mide
  con ella: se usa la copia de respaldo del equipo, que se pasa por un canal privado y nunca se
  publica, y se declara la diferencia.
- **Los videos** del banco temporal no se recrean desde la fuente: los clips del rodaje propio
  están en la carpeta de evidencia, y los recortes de internet no se pueden regenerar byte a byte
  (la plataforma de origen recodifica). Se verifican contra
  `datasets/processed/clip_bench/manifest.yaml`.

---

Scripts activos para los datasets seleccionados en el pipeline v2. Scripts de datasets v1 (SH17, Construction-PPE) están en [`legacy/scripts/download/`](../../../legacy/scripts/download/). El downloader de SHEL5K **volvió acá** el 2026-08-19 (estaba archivado en `legacy/` desde la era v1): SHEL5K es fuente canonical_v2 y estrato de bench_v3.

## Datasets v2 activos

### construction_site_safety

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_construction_site_safety.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`. Baja la **v27** (la versión por defecto
hasta el 2026-10-27 era la 3, que no existe: la que se usó siempre es la 27, ver `download_log.md`).

### mocs — copia Roboflow de MOCS

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_mocs.sh
```

Descarga vía Roboflow API (`mocs/mocs-bowib`, v1, COCO). Solo para el piloto de clase nueva; uso
evaluativo, sin redistribución (`license_registry.md`).

### chv — Color Helmet and Vest

```bash
datasets/scripts/download/download_chv.sh
```

Descarga directa. Sin credenciales requeridas. Requiere `unzip` para extraer.

### ppe_siabar

```bash
ROBOFLOW_API_KEY=<key> datasets/scripts/download/download_ppe_siabar.sh
```

Descarga vía Roboflow API. Requiere `ROBOFLOW_API_KEY`.

### shel5k

```bash
datasets/scripts/download/download_shel5k.sh
```

Descarga desde Mendeley Data (zip público con verificación sha256). Sin credenciales requeridas.

### construction_safety_hardhat (descartado — URL inválida)

```python
# legacy/scripts/download/download_construction_safety_hardhat.py
```

Script archivado en `legacy/` — el dataset no es accesible (URL de Kaggle inválida, nunca se descargó). Conservado como referencia.

## Después de descargar

Validar la descarga:

```bash
datasets/scripts/validate/summarize_raw_dataset.sh
```

Convertir a canonical_v2:

```bash
python3 datasets/scripts/convert/convert_datasets.py \
    --datasets construction_site_safety chv ppe_siabar shel5k \
    --views canonical_v2
```
