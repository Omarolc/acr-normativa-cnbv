"""Pruebas de la compuerta anti-PII."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GATE = RAIZ / "tools" / "gate_pii.py"


def _correr() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE)], capture_output=True, text=True, check=False
    )


def test_repo_limpio_de_pii() -> None:
    r = _correr()
    assert r.returncode == 0, r.stdout


def test_detecta_rfc_de_socio() -> None:
    """RFC sintetico, no corresponde a persona real."""
    intruso = RAIZ / "tests" / "fixtures" / "_pii_temporal.md"
    # RFC sintetico ensamblado en ejecucion: el patron no aparece en este archivo.
    rfc = "XAXX" + "010101" + "000"
    intruso.write_text(f"Socio de prueba, RFC {rfc}\n", encoding="utf-8")
    try:
        r = _correr()
        assert r.returncode == 1
        assert "_pii_temporal.md" in r.stdout
    finally:
        intruso.unlink()
