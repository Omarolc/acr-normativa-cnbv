"""Pruebas de la compuerta D.

La compuerta que protege la arquitectura tambien se prueba: si falla en
silencio, la deuda vuelve sin que nadie lo note.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GATE = RAIZ / "tools" / "gate_literales.py"
DEUDA = RAIZ / "tools" / "deuda_literales.txt"


def _correr(sprint: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), "--sprint", sprint],
        capture_output=True,
        text=True,
        check=False,
    )


def test_compuerta_pasa_con_repo_limpio() -> None:
    r = _correr("ACR-02")
    assert r.returncode == 0, r.stdout


def test_deuda_esta_saldada_en_acr02() -> None:
    """Objetivo de cierre de ACR-02: cero literales normativos en produccion."""
    r = _correr("ACR-02")
    assert "Deuda declarada: 0" in r.stdout


def test_detecta_literal_en_archivo_no_declarado() -> None:
    """Un archivo nuevo en src/ con el factor de requerimiento debe ser rechazado."""
    intruso = RAIZ / "src" / "acr" / "_intruso_temporal.py"
    # Centinela ensamblado en ejecucion: el patron no existe en este archivo.
    intruso.write_text("FACTOR = 0." + "08\n", encoding="utf-8")
    try:
        r = _correr("ACR-02")
        assert r.returncode == 1
        assert "_intruso_temporal.py" in r.stdout
        assert "Art. 1 Bis 3" in r.stdout
    finally:
        intruso.unlink()


def test_ratchet_falla_cuando_la_deuda_vence() -> None:
    """El ratchet: declarar deuda no basta, tiene fecha de caducidad."""
    intruso = RAIZ / "src" / "acr" / "_intruso_temporal.py"
    intruso.write_text("FACTOR = 0." + "08\n", encoding="utf-8")
    original = DEUDA.read_text(encoding="utf-8")
    DEUDA.write_text(
        original + "\nsrc/acr/_intruso_temporal.py | ACR-02\n", encoding="utf-8"
    )
    try:
        vigente = _correr("ACR-02")
        assert vigente.returncode == 0, "Deuda declarada y no vencida: debe pasar"

        vencida = _correr("ACR-03")
        assert vencida.returncode == 1, "Deuda vencida: debe abortar"
        assert "deuda vencida" in vencida.stdout
    finally:
        DEUDA.write_text(original, encoding="utf-8")
        intruso.unlink()
