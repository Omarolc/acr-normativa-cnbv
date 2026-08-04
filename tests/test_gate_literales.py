"""Pruebas de la compuerta D. La compuerta que protege la arquitectura
tambien se prueba: si falla en silencio, la deuda vuelve sin que nadie lo note.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GATE = RAIZ / "tools" / "gate_literales.py"


def _correr(sprint: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), "--sprint", sprint],
        capture_output=True,
        text=True,
        check=False,
    )


def test_compuerta_pasa_en_sprint_actual() -> None:
    """En ACR-01 la deuda del motor esta declarada y vigente."""
    r = _correr("ACR-01")
    assert r.returncode == 0, r.stdout


def test_compuerta_falla_cuando_la_deuda_vence() -> None:
    """En ACR-03 la deuda del motor (vence en ACR-02) ya debe bloquear.

    Este es el mecanismo de ratchet: no basta con declarar la deuda,
    tiene fecha de caducidad y la compuerta la hace cumplir.
    """
    r = _correr("ACR-03")
    assert r.returncode == 1
    assert "deuda vencida" in r.stdout


def test_detecta_literal_en_archivo_no_declarado() -> None:
    """Un archivo nuevo con el factor del 8% debe ser rechazado."""
    intruso = RAIZ / "src" / "acr" / "_intruso_temporal.py"
    # Centinela construido en tiempo de ejecucion: si el literal apareciera
    # escrito en este archivo, la propia compuerta lo reportaria.
    centinela = "FACTOR = 0." + "08"
    intruso.write_text(centinela + "\n", encoding="utf-8")
    try:
        r = _correr("ACR-01")
        assert r.returncode == 1
        assert "_intruso_temporal.py" in r.stdout
        assert "Art. 1 Bis 3" in r.stdout
    finally:
        intruso.unlink()
