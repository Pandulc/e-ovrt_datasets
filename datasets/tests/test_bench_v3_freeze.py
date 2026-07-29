"""Verificabilidad del freeze de bench_v3 (doc 75 §2.4 del repo docs).

El congelamiento solo sirve si la herramienta obvia lo verifica:
`sha256sum bench_v3.json` DEBE dar el `bench_v3_sha256` del manifest. Para eso el
script tiene que escribir exactamente la misma serialización que hashea
(`freeze_payload`, sort_keys=True) — hashear una re-serialización distinta de la
que se escribe produce un freeze no reproducible por el jurado.

Los tests de artefacto real se skippean si los archivos congelados no están en
disco (la suite sintética corre limpia sin datos procesados).
"""
import hashlib
import json
from pathlib import Path

import pytest

from curate.build_bench_v3 import STRATUM_SOURCES, freeze_payload, manifest_sha256

REPO = Path(__file__).resolve().parents[1]  # datasets/
CURATED = REPO / "processed/coco/bench/curated"
BENCH_V3 = CURATED / "bench_v3.json"
MANIFEST = CURATED / "bench_v3_manifest.json"

needs_frozen_artifacts = pytest.mark.skipif(
    not (BENCH_V3.exists() and MANIFEST.exists()
         and all(p.exists() for p in STRATUM_SOURCES.values())),
    reason="artefactos congelados de bench_v3 no presentes (suite sintética)",
)


# ---------------------------------------------------------------------------
# Sintético: la serialización que se escribe es la misma que se hashea
# ---------------------------------------------------------------------------

def test_freeze_payload_es_hasheable_y_estable_ante_orden_de_claves():
    a = freeze_payload({"images": [], "annotations": [], "categories": []})
    b = freeze_payload({"categories": [], "annotations": [], "images": []})
    assert a == b  # sort_keys: el orden de inserción no cambia los bytes congelados
    assert manifest_sha256(a) == hashlib.sha256(b.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Artefacto real congelado: pin de sha256 (skip si falta en disco)
# ---------------------------------------------------------------------------

@needs_frozen_artifacts
def test_sha256sum_de_bench_v3_json_coincide_con_el_manifest():
    """`sha256sum bench_v3.json` == `bench_v3_sha256` del manifest, sin re-serializar."""
    manifest = json.loads(MANIFEST.read_text())
    on_disk = hashlib.sha256(BENCH_V3.read_bytes()).hexdigest()
    assert on_disk == manifest["bench_v3_sha256"], (
        "los bytes de bench_v3.json no hashean al bench_v3_sha256 del manifest: "
        "el freeze no es verificable con sha256sum"
    )


@needs_frozen_artifacts
def test_sha256_de_las_4_fuentes_coincide_con_el_manifest():
    manifest = json.loads(MANIFEST.read_text())
    assert set(manifest["source_sha256"]) == set(STRATUM_SOURCES)
    for name, path in STRATUM_SOURCES.items():
        on_disk = hashlib.sha256(path.read_bytes()).hexdigest()
        assert on_disk == manifest["source_sha256"][name], (
            f"la fuente '{name}' cambió respecto del freeze declarado en el manifest"
        )


@needs_frozen_artifacts
def test_conteos_congelados_de_bench_v3():
    """Los conteos del freeze del 23-jul no deben moverse (doc 66)."""
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["total_images"] == 6477
    assert manifest["total_annotations"] == 55165
    assert manifest["images_by_stratum"] == {
        "bench_obra_test": 62, "bench_obra_val": 85, "chv": 1330, "shel5k": 5000,
    }
    merged = json.loads(BENCH_V3.read_text())
    assert len(merged["images"]) == 6477
    assert len(merged["annotations"]) == 55165
