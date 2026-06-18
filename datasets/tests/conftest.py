"""Fixtures compartidas para los tests de la lógica v2."""
import sys
from pathlib import Path

# Permite importar los scripts standalone como módulos en los tests.
REPO_ROOT = Path(__file__).resolve().parents[1]  # datasets/
sys.path.insert(0, str(REPO_ROOT / "scripts"))
