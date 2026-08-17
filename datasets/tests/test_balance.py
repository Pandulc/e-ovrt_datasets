"""Guard de la regla de balance de clases en TRAIN (G6/G7 del reinicio v2).

✎ 2026-08-15: `build_role_views.py` se archivó en `legacy/scripts/curate/` junto con
los manifiestos de rol que producía (`legacy/splits/v2/`) — ver
`datasets/splits/DEPRECATED.md`. El test se conserva porque lo que verifica no es el
script sino la **regla metodológica** (mínimos por clase para evitar el desbalance
histórico de `vest`), que sigue siendo el criterio con el que se juzga cualquier
corpus de entrenamiento. Se importa por ruta explícita para no reactivar `legacy/`
como paquete importable.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = REPO_ROOT / "legacy" / "scripts" / "curate" / "build_role_views.py"

_spec = importlib.util.spec_from_file_location("legacy_build_role_views", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
meets_min_per_class = _module.meets_min_per_class


def test_balance_pass():
    assert meets_min_per_class({"person": 500, "helmet": 400, "vest": 200, "bare_head": 300}, minimum=150)


def test_balance_fail_on_vest():
    assert not meets_min_per_class({"person": 500, "helmet": 400, "vest": 50, "bare_head": 300}, minimum=150)
