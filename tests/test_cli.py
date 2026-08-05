"""CLI: salida determinista y validaciones de entrada."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from acr.cli.principal import calcular, main
from acr.normativa import RegistroNoVigenteError, VigenciaBloqueadaError

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"


def _caso() -> dict[str, object]:
    return json.loads(CASO.read_text(encoding="utf-8"))


def test_salida_es_reproducible_byte_a_byte() -> None:
    a = json.dumps(calcular(_caso()), default=str, sort_keys=True)
    b = json.dumps(calcular(_caso()), default=str, sort_keys=True)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_insumo_ausente_falla_no_asume_cero() -> None:
    caso = _caso()
    del caso["capital_contable"]
    with pytest.raises(KeyError, match="hechos distintos"):
        calcular(caso)


def test_corte_2027_bloqueado() -> None:
    caso = _caso()
    caso["fecha_corte"] = "2027-03-31"
    with pytest.raises(VigenciaBloqueadaError, match="REF-2027-ANEXOS"):
        calcular(caso)


def test_corte_anterior_a_vigencia_bloqueado() -> None:
    caso = _caso()
    caso["fecha_corte"] = "2025-12-31"
    with pytest.raises(RegistroNoVigenteError):
        calcular(caso)


def test_corte_no_trimestral_rechazado() -> None:
    caso = _caso()
    caso["fecha_corte"] = "2026-05-31"
    with pytest.raises(ValueError, match="cierre trimestral"):
        calcular(caso)


def test_cli_escribe_archivo(tmp_path: Path) -> None:
    salida = tmp_path / "r.json"
    assert main(["calcular", "--caso", str(CASO), "--out", str(salida)]) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["clasificacion"]["categoria"] in {"A", "B", "C", "D"}
    assert len(datos["formulario_anexo_u"]) == 10
    assert datos["registro"]["sha256"]


def test_cli_imprime_a_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["calcular", "--caso", str(CASO)]) == 0
    assert "formulario_anexo_u" in capsys.readouterr().out


def test_cli_comando_registro(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registro"]) == 0
    salida = capsys.readouterr().out
    assert "BLOQUEANTE" in salida
    assert "REF-2027-ANEXOS" in salida
