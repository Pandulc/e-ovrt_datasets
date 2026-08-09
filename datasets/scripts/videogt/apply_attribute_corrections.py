"""Aplica CORRECCIONES de atributos explícitos declaradas en `clip.yaml`.

Hermano de `apply_adjudications.py`, y **deliberadamente separado**: aquel solo
convierte `unknown` y se NIEGA a pisar un valor explícito del anotador, que es la
garantía de que una automatización no fabrique evidencia. Pero existe un caso
legítimo que esa garantía bloquea: **el anotador se equivocó y, tras revisar el
video, decide corregirse**. Eso no es adjudicar incertidumbre — es corregir un
hecho, y merece más ceremonia, no menos.

Por eso este script es aparte, usa otra clave (`annotation.attribute_corrections`)
y exige un campo que el otro no tiene: **`previous_value`**. El guard central es
que el valor que hay en el XML COINCIDA con el declarado como previo; si no
coincide, corta. Eso hace la operación:

  - **auditable**: la corrección dice de qué a qué, no solo "poné true";
  - **idempotente**: si el valor ya es el nuevo, es no-op (permite re-correr la
    cadena sin acumular cambios);
  - **a prueba de deriva**: si el XML cambió por debajo (p.ej. se re-exportó de
    CVAT con OTRA cosa), el guard salta en vez de pisar en silencio.

Esquema (los 8 campos son obligatorios):

    annotation:
      attribute_corrections:
        - track_id: 110              # OBLIGATORIO: se corrige a UNA persona
          attr: has_vest             # has_helmet | has_vest
          from_frame: 10272          # inclusive, frames LOCALES del clip
          to_frame: 10665            # inclusive
          previous_value: "false"    # lo que dice hoy el XML — se verifica
          value: "true"              # lo que debe decir
          decided_by: simonll4       # quién lo decidió mirando el video
          decided_at: "2026-08-06"
          rationale: "..."           # por qué; queda en el GT y en el banco

**`track_id` es obligatorio y no tiene default a propósito.** Una corrección es
sobre el estado de UNA persona, no sobre un intervalo de tiempo: en un clip con
varios sujetos, el mismo rango de frames contiene cajas de todos. Sin scoping, una
corrección firmada para un sujeto pisaría a los demás. (Pasó en la primera
redacción de la corrección de `v06_c01`: 7 tracks tenían cajas en el rango; el
guard de `previous_value` lo atajó, y de ahí salió este campo.)

Flujo:  (split_cvat_project) → apply_adjudications → apply_attribute_corrections
        → derive_clip_gt

Uso:
    python3 datasets/scripts/videogt/apply_attribute_corrections.py \\
        --xml datasets-videos/corrected/<clip>.xml \\
        --clip-yaml datasets-videos/<clip>.clip.yaml \\
        [--out <xml de salida>]   # default: in-place
"""
from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

CAMPOS = ("track_id", "attr", "from_frame", "to_frame", "previous_value", "value",
          "decided_by", "decided_at", "rationale")
ATRIBUTOS = {"has_helmet", "has_vest"}
VALORES = {"true", "false", "unknown"}


class CorrectionError(Exception):
    """Corrección mal declarada, rango que no matchea, o valor previo distinto."""


def _validar(c: dict, i: int) -> None:
    # 0 es un track_id válido y no cae en ("", None), así que este chequeo lo acepta.
    faltan = [k for k in CAMPOS if k not in c or c[k] in ("", None)]
    if faltan:
        raise CorrectionError(
            f"attribute_corrections[{i}]: faltan campos obligatorios: {', '.join(faltan)}. "
            f"Una corrección que pisa un valor explícito del anotador exige los {len(CAMPOS)}: "
            f"{', '.join(CAMPOS)}.")
    if c["attr"] not in ATRIBUTOS:
        raise CorrectionError(f"attribute_corrections[{i}]: attr '{c['attr']}' inválido "
                              f"(esperado {sorted(ATRIBUTOS)})")
    for k in ("previous_value", "value"):
        if str(c[k]).lower() not in VALORES:
            raise CorrectionError(f"attribute_corrections[{i}]: {k} '{c[k]}' inválido "
                                  f"(esperado {sorted(VALORES)})")
    if str(c["previous_value"]).lower() == str(c["value"]).lower():
        raise CorrectionError(f"attribute_corrections[{i}]: previous_value == value "
                              f"('{c['value']}'): no es una corrección")
    if int(c["from_frame"]) > int(c["to_frame"]):
        raise CorrectionError(f"attribute_corrections[{i}]: from_frame > to_frame")


def apply_corrections(xml_path, clip_yaml_path, out_path=None) -> dict:
    """Aplica las correcciones del clip.yaml al XML. Devuelve el resumen."""
    meta = yaml.safe_load(Path(clip_yaml_path).read_text()) or {}
    correcciones = (meta.get("annotation") or {}).get("attribute_corrections") or []
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    resumen = {"correcciones": len(correcciones), "cajas_cambiadas": 0,
               "cajas_ya_corregidas": 0, "detalle": []}
    for i, c in enumerate(correcciones):
        _validar(c, i)
        attr = c["attr"]
        f0, f1 = int(c["from_frame"]), int(c["to_frame"])
        prev, nuevo = str(c["previous_value"]).lower(), str(c["value"]).lower()
        cambiadas = ya = en_rango = 0
        conflictos = []
        tracks = [tr for tr in root.findall("track")
                  if int(tr.get("id")) == int(c["track_id"])]
        if not tracks:
            raise CorrectionError(
                f"attribute_corrections[{i}]: no existe el track id={c['track_id']} "
                f"en {xml_path}.")
        for tr in tracks:
            for b in tr.findall("box"):
                f = int(b.get("frame"))
                if not (f0 <= f <= f1):
                    continue
                for a in b.findall("attribute"):
                    if a.get("name") != attr:
                        continue
                    en_rango += 1
                    actual = (a.text or "").strip().lower()
                    if actual == nuevo:
                        ya += 1                      # idempotencia
                    elif actual == prev:
                        a.text = nuevo
                        cambiadas += 1
                    else:
                        conflictos.append((f, actual))
        if conflictos:
            muestra = ", ".join(f"f{f}={v!r}" for f, v in conflictos[:5])
            raise CorrectionError(
                f"attribute_corrections[{i}] ({attr} {f0}-{f1}): {len(conflictos)} caja(s) "
                f"tienen un valor que NO es ni previous_value ('{prev}') ni value "
                f"('{nuevo}') — p.ej. {muestra}. El XML cambió por debajo de la "
                f"corrección declarada; revisá antes de pisar nada.")
        if en_rango == 0:
            raise CorrectionError(
                f"attribute_corrections[{i}] ({attr} {f0}-{f1}): el rango no matcheó "
                f"ninguna caja. Una corrección firmada que no se aplica es peor que "
                f"ninguna — revisá los frames.")
        resumen["cajas_cambiadas"] += cambiadas
        resumen["cajas_ya_corregidas"] += ya
        resumen["detalle"].append({
            "attr": attr, "rango": [f0, f1], "de": prev, "a": nuevo,
            "cambiadas": cambiadas, "ya_estaban": ya,
            "decided_by": c["decided_by"], "decided_at": str(c["decided_at"]),
        })

    destino = Path(out_path or xml_path)
    if correcciones:
        tree.write(str(destino), encoding="utf-8", xml_declaration=True)
    return resumen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", required=True)
    ap.add_argument("--clip-yaml", required=True)
    ap.add_argument("--out", default=None, help="default: in-place sobre --xml")
    ap.add_argument("--check", action="store_true",
                    help="NO escribe: verifica que las correcciones YA estén aplicadas "
                         "en el XML. Sale 1 si alguna falta (p.ej. porque alguien "
                         "re-exportó de CVAT y revirtió una corrección firmada).")
    a = ap.parse_args(argv)
    try:
        # en --check se escribe a un descartable para no tocar el original
        destino = os.devnull if a.check else a.out
        r = apply_corrections(a.xml, a.clip_yaml, destino)
    except CorrectionError as e:
        if a.check:
            print(f"✗ {a.xml}: {e}")
            return 1
        ap.error(str(e))
    if not r["correcciones"]:
        print("sin attribute_corrections declaradas — nada que hacer")
        return 0

    if a.check:
        faltan = [d for d in r["detalle"] if d["cambiadas"] > 0]
        for d in r["detalle"]:
            estado = "FALTA APLICAR" if d["cambiadas"] else "aplicada"
            print(f"  [{estado}] {d['attr']} [{d['rango'][0]}..{d['rango'][1]}] "
                  f"{d['de']} → {d['a']}  ({d['ya_estaban']} cajas ya corregidas, "
                  f"{d['cambiadas']} sin corregir)")
        if faltan:
            print(f"✗ {len(faltan)} corrección(es) NO aplicada(s) en {a.xml}. "
                  f"Es lo esperable en un export fresco de CVAT: las correcciones "
                  f"viven en el repo, no en la herramienta. Aplicalas (sin --check) "
                  f"antes de derivar el GT.")
            return 1
        print(f"✓ las {r['correcciones']} corrección(es) firmadas están aplicadas")
        return 0

    for d in r["detalle"]:
        print(f"  {d['attr']} [{d['rango'][0]}..{d['rango'][1]}] {d['de']} → {d['a']}: "
              f"{d['cambiadas']} cambiadas, {d['ya_estaban']} ya estaban "
              f"(firma: {d['decided_by']}, {d['decided_at']})")
    print(f"✓ {r['correcciones']} corrección(es), {r['cajas_cambiadas']} cajas modificadas "
          f"→ {a.out or a.xml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
