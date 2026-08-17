# `datasets/splits/` — TODO EL DIRECTORIO ESTÁ DEPRECADO

**No hay splits activos.** Las dos generaciones de manifiestos de rol quedaron
superadas y archivadas; este archivo es lo único que queda acá, como señalización.

## Generación 1 — `splits/cr01_cr02/` (deprecada 2026-06-17)

Deprecada con el reinicio v2 y movida a `legacy/splits/cr01_cr02/`.
Referencia: `datasets/documentation/2026-06-17-reinicio-seleccion-datasets-design.md`.

## Generación 2 — `splits/v2/` (archivada 2026-08-15)

`train.txt` (5.540) · `bench.txt` (196) · `demo.txt` (1.064) · `manifest.json`, y su
generador `datasets/scripts/curate/build_role_views.py`, se movieron a:

```
legacy/splits/v2/
legacy/scripts/curate/build_role_views.py
```

**Por qué:** al relevar el estado el 2026-08-15 se verificó que **los tres roles estaban
huérfanos** — ningún script, config o test del pipeline activo los consumía. Cada uno
había sido superado por su reemplazo:

| Rol | Superado por | Verificación |
|---|---|---|
| **BENCH** (`bench.txt`, 196 imgs) | **`bench_v3`** — 6.477 imgs, 3 fuentes independientes, congelado por sha256 | El split de 196 resultó **~20–25 % fuera de dominio** (selfies COVID, PASCAL VOC, aeropuerto/casino; auditado en `docs/operacion/63`). **Todo resultado reportable usa `bench_v3`** |
| **TRAIN** (`train.txt`, 5.540 imgs) | **`finetuning_v1`** — selección propia por grupos de linaje, con gates anti-leakage verificados | Vive en `e-ovrt_experimental-setup/finetuning/`. Las 5.540 incluyen CHV, que **no puede entrar al fine-tuning** (gate invariante 2) |
| **DEMO** (`demo.txt`, 1.064 imgs) | El catálogo del media-plane apunta **directo a la carpeta raw** | `e-ovrt_media-plane/configs/datasets/demo_v2.yaml` → `raw/chv/CHV_dataset/images`; nunca leyó este manifiesto |

**El riesgo que cierra el archivado:** `bench.txt` no era sólo un archivo viejo — lo
**regeneraba** un script listado como comando activo. Archivar el artefacto sin archivar
su generador habría sido cosmético: la próxima corrida lo reponía. Por eso se movieron
los dos.

**Trampa de lectura que sobrevive:** los números 196 / 5.540 / 1.064 se siguen citando en
documentos históricos como referencia. Están bien **como historia**; lo que nunca debe
hacerse es **citar "el BENCH de 196 imágenes" como benchmark de un resultado**.

**Lo que NO se perdió:** la regla metodológica de balance de clases en TRAIN (G6/G7 —
mínimos por clase para evitar el desbalance histórico de `vest`) sigue con su guard en
`datasets/tests/test_balance.py`, que importa el helper desde `legacy/` por ruta
explícita. 418 tests verdes tras el archivado.

Referencia del cambio: `docs/operacion/121` §4.3.
