"""Ensamblado/congelamiento del banco de clips (doc 75 §1.5, gap doc 54 §5.4).

`promote_clip.py` promueve UN clip y `validate_clip_gt.py` valida GT+manifest,
pero nada arma la vista agregada del banco — el análogo de
`bench_v3_manifest.json` para video: composición por escenario/bloque,
positivos vs negativos vs soak (doc 57 G1), episodios por condición,
denominador FAR/hora, gate de estados (un banco reportable exige TODO
`gt_ready` — `gt_preliminary` es bring-up, no números de tesis) y freeze
verificable con `sha256sum`.

Fixtures sintéticos, sin media real (la media es git-ignored y puede no estar:
eso NO debe romper el ensamblado, igual que en validate_clip_gt).
"""
import hashlib
import json

import pytest
import yaml

from bench.build_clip_bench import (
    SOAK_MIN_MS,
    ClipBenchError,
    assemble_clip_bench,
    checksums_text,
    freeze_payload,
    main,
    write_clip_bench,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_gt(clip_id, *, scenario, block, duration_ms, negative, xml_sha256,
             episodes=None, double_annotated=False):
    if episodes is None:
        episodes = [] if negative else [
            {"id": "ep1", "condition_id": "CR-01", "level": "scene",
             "source_id": clip_id, "start_ms": 1000, "end_ms": 15000,
             "subjects_in_evidence": 1, "notes": ""},
        ]
    return {
        "schema_version": "clip_gt.v2",
        "clip_id": clip_id,
        "source_file": f"clips/{clip_id}.mp4",
        "block": block,
        "scenario": scenario,
        "fps_nominal": 30,
        "duration_ms": duration_ms,
        "recording": {"resolution": "1920x1080"},
        "negative": negative,
        "episodes": episodes,
        "sub_threshold_events": [],
        "annotation": {"annotator": "a1", "double_annotated": double_annotated},
        "provenance": {"xml_sha256": xml_sha256,
                       "pattern_set_ms": {"CR-01": 4000, "CR-02": 7000},
                       "tool": "video-gt-lab/derive_clip_gt"},
    }


def _add_clip(bank, clip_id, *, state="gt_ready", scenario="P1", block="A",
              duration_ms=20000, negative=False, episodes=None,
              double_annotated=False, tamper_xml=False, drop_provenance=False):
    """Escribe los artefactos comprometidos de un clip y devuelve su fila."""
    for sub in ("annotations", "gt", "meta", "preann"):
        (bank / sub).mkdir(parents=True, exist_ok=True)
    xml = f"<annotations>{clip_id}</annotations>".encode()
    (bank / "preann" / f"{clip_id}.xml").write_bytes(b"<preann/>")
    (bank / "meta" / f"{clip_id}.clip.yaml").write_text(
        yaml.safe_dump({"clip_id": clip_id, "block": block, "scenario": scenario}))
    row = {
        "clip_id": clip_id,
        "file": f"../../raw/clip_bench/clips/{clip_id}.mp4",
        "sha256": _sha(f"fake media {clip_id}".encode()),
        "fps": 30,
        "duration_ms": duration_ms,
        "resolution": "1920x1080",
        "block": block,
        "scenario": scenario,
        "level": "scene",
        "state": state,
        "preann": f"preann/{clip_id}.xml",
        "meta": f"meta/{clip_id}.clip.yaml",
    }
    with_gt = state in ("gt_ready", "gt_preliminary")
    if with_gt or state == "corrected":
        (bank / "annotations" / f"{clip_id}.xml").write_bytes(xml)
        row["annotations"] = f"annotations/{clip_id}.xml"
    if with_gt:
        declared = _sha(b"otro xml distinto") if tamper_xml else _sha(xml)
        gt = _make_gt(clip_id, scenario=scenario, block=block,
                      duration_ms=duration_ms, negative=negative,
                      xml_sha256=declared, episodes=episodes,
                      double_annotated=double_annotated)
        if drop_provenance:
            del gt["provenance"]
        (bank / "gt" / f"{clip_id}.json").write_text(json.dumps(gt))
        row["gt"] = f"gt/{clip_id}.json"
    return row


def _write_bank(bank, rows):
    bank.mkdir(parents=True, exist_ok=True)
    (bank / "manifest.yaml").write_text(yaml.safe_dump({"clips": rows}))


@pytest.fixture
def bank(tmp_path):
    return tmp_path / "clip_bench"


# ---------------------------------------------------------------------------
# Composición y agregados (el análogo de bench_v3_manifest.json)
# ---------------------------------------------------------------------------

def test_banco_reportable_con_todo_gt_ready(bank):
    rows = [
        _add_clip(bank, "cb_a01_p1", scenario="P1", block="A"),
        _add_clip(bank, "cb_a02_p5", scenario="P5", block="A", negative=True),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["schema_version"] == "clip_bench_manifest.v1"
    assert m["reportable"] is True
    assert m["non_reportable_clips"] == []
    assert m["counts"]["clips_total"] == 2
    assert m["counts"]["by_scenario"] == {"P1": 1, "P5": 1}
    assert m["counts"]["by_block"] == {"A": 2}
    assert m["counts"]["by_state"] == {"gt_ready": 2}
    assert m["counts"]["positive_clips"] == 1
    assert m["counts"]["negative_clips"] == 1
    assert m["episodes"]["total"] == 1
    assert m["episodes"]["by_condition"] == {"CR-01": 1, "CR-02": 0}


def test_conteo_de_episodios_por_condicion(bank):
    eps = [
        {"id": "ep1", "condition_id": "CR-01", "level": "scene", "source_id": "cb_x",
         "start_ms": 0, "end_ms": 8000, "subjects_in_evidence": 1, "notes": ""},
        {"id": "ep2", "condition_id": "CR-02", "level": "scene", "source_id": "cb_x",
         "start_ms": 9000, "end_ms": 18000, "subjects_in_evidence": 1, "notes": ""},
    ]
    rows = [_add_clip(bank, "cb_x", scenario="P8", block="C", episodes=eps)]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["episodes"]["by_condition"] == {"CR-01": 1, "CR-02": 1}
    (clip,) = m["clips"]
    assert clip["n_episodes"] == 2
    assert clip["episodes_by_condition"] == {"CR-01": 1, "CR-02": 1}


def test_soak_es_negativo_de_al_menos_5_min_y_suma_denominador_far(bank):
    # Mezcla negativos cortos + soak: el denominador FAR separa los dos.
    rows = [
        _add_clip(bank, "cb_soak", scenario="P5", block="A", negative=True,
                  duration_ms=SOAK_MIN_MS + 60_000),   # 6 min
        _add_clip(bank, "cb_neg_corto", scenario="P5", block="A", negative=True,
                  duration_ms=15_000),                 # negativo pero NO soak
        _add_clip(bank, "cb_pos", scenario="P1", block="A", duration_ms=20_000),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["counts"]["soak_clips"] == 1
    assert m["counts"]["negative_clips"] == 2
    assert m["duration_ms"]["soak"] == SOAK_MIN_MS + 60_000
    assert m["duration_ms"]["negative"] == SOAK_MIN_MS + 60_000 + 15_000
    # doc 57 §3.2 G1: FAR/hora se mide SOLO sobre los soak (negativos ≥5 min).
    # El negativo corto NO entra al denominador (no es estimador serio).
    assert m["far_denominator_hours"] == round((SOAK_MIN_MS + 60_000) / 3_600_000, 4)
    # El tiempo negativo total queda como campo informativo, separado.
    expected_negative_hours = round((SOAK_MIN_MS + 60_000 + 15_000) / 3_600_000, 4)
    assert m["negative_hours_total"] == expected_negative_hours
    assert "soak" in m["far_denominator_basis"]


def test_sin_soak_denominador_far_es_cero_y_explicito(bank):
    # Sin clips soak el denominador FAR es 0.0 — no se inventa desde negativos
    # cortos (doc 57 §3.2 G1; doc 59 §6: FP/min sobre ventana agregada + cota
    # 3/N; FP/hora solo como extrapolación declarada).
    rows = [
        _add_clip(bank, "cb_neg_corto", scenario="P5", block="A", negative=True,
                  duration_ms=60_000),                 # 1 min: negativo, no soak
        _add_clip(bank, "cb_pos", scenario="P1", block="A", duration_ms=20_000),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["counts"]["soak_clips"] == 0
    assert m["far_denominator_hours"] == 0.0
    assert m["negative_hours_total"] == round(60_000 / 3_600_000, 4)
    assert "soak" in m["far_denominator_basis"]


def test_cobertura_de_escenarios_p1_a_p9(bank):
    rows = [
        _add_clip(bank, "cb_1", scenario="P1", block="A"),
        _add_clip(bank, "cb_5", scenario="P5", block="A", negative=True),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["scenario_coverage"]["present"] == ["P1", "P5"]
    assert m["scenario_coverage"]["missing_p_scenarios"] == [
        "P2", "P3", "P4", "P6", "P7", "P8", "P9"]


def test_doble_anotacion_se_reporta(bank):
    rows = [
        _add_clip(bank, "cb_1", scenario="P1", block="A", double_annotated=True),
        _add_clip(bank, "cb_2", scenario="P2", block="A"),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    assert m["counts"]["double_annotated_clips"] == 1
    assert m["counts"]["double_annotation_ratio"] == 0.5


# ---------------------------------------------------------------------------
# Gate de estados: reportable ⇔ todo gt_ready (doc 54: gt_preliminary es
# bring-up; los números de tesis exigen la pasada humana en CVAT)
# ---------------------------------------------------------------------------

def test_gt_preliminary_sin_flag_es_error(bank):
    rows = [
        _add_clip(bank, "cb_ok", scenario="P1", block="A"),
        _add_clip(bank, "cb_prelim", scenario="P2", block="A",
                  state="gt_preliminary"),
    ]
    _write_bank(bank, rows)
    with pytest.raises(ClipBenchError) as exc:
        assemble_clip_bench(bank)
    assert any("cb_prelim" in e and "gt_preliminary" in e for e in exc.value.errors)


def test_allow_preliminary_construye_pero_marca_no_reportable(bank):
    rows = [
        _add_clip(bank, "cb_ok", scenario="P1", block="A"),
        _add_clip(bank, "cb_prelim", scenario="P2", block="A",
                  state="gt_preliminary"),
        _add_clip(bank, "cb_corr", scenario="P3", block="A", state="corrected"),
    ]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank, allow_preliminary=True)
    assert m["reportable"] is False
    pending = {c["clip_id"]: c["state"] for c in m["non_reportable_clips"]}
    assert pending == {"cb_prelim": "gt_preliminary", "cb_corr": "corrected"}
    # los clips sin GT no aportan episodios ni composición pos/neg
    assert m["counts"]["clips_without_gt"] == 1
    assert m["counts"]["clips_with_gt"] == 2


# ---------------------------------------------------------------------------
# Validaciones de consistencia (fallan cerrado: no se escribe nada)
# ---------------------------------------------------------------------------

def test_xml_corregido_distinto_del_que_derivo_el_gt_es_error(bank):
    # provenance.xml_sha256 del GT ≠ sha del annotations/<id>.xml promovido:
    # el GT se derivó de OTRO XML — la trampa exacta del día del GT.
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A", tamper_xml=True)]
    _write_bank(bank, rows)
    with pytest.raises(ClipBenchError) as exc:
        assemble_clip_bench(bank)
    assert any("cb_x" in e and "xml_sha256" in e for e in exc.value.errors)


def test_gt_sin_provenance_es_error(bank):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A", drop_provenance=True)]
    _write_bank(bank, rows)
    with pytest.raises(ClipBenchError) as exc:
        assemble_clip_bench(bank)
    assert any("cb_x" in e and "provenance" in e for e in exc.value.errors)


def test_fila_sin_block_o_scenario_es_error_amigable(bank):
    # block/scenario no los exige validate_manifest (FIX 7 solo cubre
    # clip_id/file/gt) pero la composición del banco los necesita: sin este
    # chequeo explotaba con KeyError críptico en vez de listar qué falta.
    row = _add_clip(bank, "cb_x", scenario="P1", block="A")
    del row["block"]
    del row["scenario"]
    _write_bank(bank, [row])
    with pytest.raises(ClipBenchError) as exc:
        assemble_clip_bench(bank)
    assert any("cb_x" in e and "block" in e and "scenario" in e
               for e in exc.value.errors)


def test_gt_corrupto_es_error_amigable_y_no_escribe(bank):
    # Un GT con JSON roto propagaba JSONDecodeError crudo; debe listar qué
    # archivo está corrupto y fallar cerrado (sin escribir nada).
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    (bank / "gt" / "cb_x.json").write_text("{esto no es json")
    _write_bank(bank, rows)
    with pytest.raises(ClipBenchError) as exc:
        assemble_clip_bench(bank)
    assert any("cb_x" in e and "gt/cb_x.json" in e and "JSON" in e
               for e in exc.value.errors)
    assert main(["--bank-dir", str(bank)]) == 1
    assert not (bank / "clip_bench_manifest.json").exists()
    assert not (bank / "clip_bench.sha256").exists()


def test_errores_de_validate_manifest_propagan(bank):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    _write_bank(bank, rows)
    # GT apuntando a otro clip_id: lo atrapa validate_manifest (reutilizado)
    gt = json.loads((bank / "gt" / "cb_x.json").read_text())
    gt["clip_id"] = "cb_otro"
    (bank / "gt" / "cb_x.json").write_text(json.dumps(gt))
    with pytest.raises(ClipBenchError):
        assemble_clip_bench(bank)


def test_banco_vacio_es_error(bank):
    _write_bank(bank, [])
    with pytest.raises(ClipBenchError):
        assemble_clip_bench(bank)


# ---------------------------------------------------------------------------
# Freeze: determinismo + verificable con sha256sum (doc 75 §2.4)
# ---------------------------------------------------------------------------

def test_gt_sha256_es_el_de_los_bytes_del_archivo(bank):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    (clip,) = m["clips"]
    on_disk = _sha((bank / "gt" / "cb_x.json").read_bytes())
    assert clip["gt_sha256"] == on_disk  # `sha256sum gt/cb_x.json` verifica directo
    assert m["manifest_yaml_sha256"] == _sha((bank / "manifest.yaml").read_bytes())


def test_escritura_es_determinista_e_idempotente(bank):
    rows = [
        _add_clip(bank, "cb_b", scenario="P2", block="B"),
        _add_clip(bank, "cb_a", scenario="P1", block="A"),
    ]
    _write_bank(bank, rows)
    m1 = assemble_clip_bench(bank)
    json_path, sha_path = write_clip_bench(bank, m1)
    first = (json_path.read_bytes(), sha_path.read_bytes())
    m2 = assemble_clip_bench(bank)
    write_clip_bench(bank, m2)
    assert (json_path.read_bytes(), sha_path.read_bytes()) == first
    # el json escrito ES la serialización hasheada (sin re-serializar)
    assert json_path.read_text() == freeze_payload(m1)


def test_checksums_file_en_formato_sha256sum(bank):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    _write_bank(bank, rows)
    m = assemble_clip_bench(bank)
    text = checksums_text(m)
    lines = [ln for ln in text.splitlines() if ln]
    paths = []
    for line in lines:
        digest, path = line.split("  ", 1)
        assert _sha((bank / path).read_bytes()) == digest  # sha256sum -c pasaría
        paths.append(path)
    assert paths == sorted(paths)
    assert "manifest.yaml" in paths
    assert "gt/cb_x.json" in paths
    assert "annotations/cb_x.xml" in paths


# ---------------------------------------------------------------------------
# CLI (main): exit codes y fail-closed
# ---------------------------------------------------------------------------

def test_main_reportable_escribe_y_devuelve_0(bank, capsys):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    _write_bank(bank, rows)
    assert main(["--bank-dir", str(bank)]) == 0
    assert (bank / "clip_bench_manifest.json").exists()
    assert (bank / "clip_bench.sha256").exists()


def test_main_con_preliminary_sin_flag_devuelve_1_y_no_escribe(bank, capsys):
    rows = [_add_clip(bank, "cb_prelim", scenario="P1", block="A",
                      state="gt_preliminary")]
    _write_bank(bank, rows)
    assert main(["--bank-dir", str(bank)]) == 1
    assert not (bank / "clip_bench_manifest.json").exists()
    assert not (bank / "clip_bench.sha256").exists()


def test_main_dry_run_no_escribe(bank, capsys):
    rows = [_add_clip(bank, "cb_x", scenario="P1", block="A")]
    _write_bank(bank, rows)
    assert main(["--bank-dir", str(bank), "--dry-run"]) == 0
    assert not (bank / "clip_bench_manifest.json").exists()
