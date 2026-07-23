"""Mapping canónico de SHEL5K (plan doc 66 §B4 del repo docs, auditoría 2026-07-23).

Verificación empírica sobre los XML reales (400 muestreados): las cajas `head`
están en un 82% contenidas en `person_no_helmet` y solo 2% en
`person_with_helmet` — `head` ES la anotación explícita de cabeza descubierta
del paper (existe `head_with_helmet` aparte), no una derivación por resta, así
que cumple el espíritu del contrato D9. Y `head_with_helmet` solapa 97% con una
caja `helmet` separada: mapearlo a helmet duplicaría el GT de la clase.
"""
import pytest

from convert.convert_datasets import (
    DatasetConfig,
    assert_no_derived_bare_head,
    configs,
)


def test_guard_sigue_rechazando_head_sin_verificacion():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"head": "bare_head"},
    )
    with pytest.raises(ValueError):
        assert_no_derived_bare_head(cfg)


def test_guard_permite_head_declarado_como_negativo_explicito():
    cfg = DatasetConfig(
        dataset_id="x", source_format="yolo", canonical_map={},
        canonical_v2_map={"head": "bare_head"},
        bare_head_explicit_sources={"head"},
    )
    assert assert_no_derived_bare_head(cfg) is None


def test_shel5k_mapea_head_a_bare_head():
    v2 = configs()["shel5k"].canonical_v2_map
    assert v2.get("head") == "bare_head"


def test_shel5k_no_duplica_helmet_con_head_with_helmet():
    v2 = configs()["shel5k"].canonical_v2_map
    assert "head_with_helmet" not in v2
    assert v2.get("helmet") == "helmet"


def test_shel5k_une_las_clases_compuestas_de_persona():
    v2 = configs()["shel5k"].canonical_v2_map
    assert v2.get("person_with_helmet") == "person"
    assert v2.get("person_no_helmet") == "person"
