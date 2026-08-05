"""Capa de entrada: tolerancia a BOM y errores explicativos.

Regresion de ACR-02.1. En Windows, PowerShell 5.1, el Bloc de notas y las
exportaciones de Excel escriben BOM. Son exactamente las herramientas con las
que una cooperativa prepara sus insumos: si el sistema falla con ellas, falla
con el primer caso real.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from acr.cli.principal import calcular
from acr.entrada import (
    ArchivoDeEntradaInvalidoError,
    escribir_texto,
    leer_json,
    leer_texto,
)

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"
CASO_BOM = RAIZ / "tests" / "fixtures" / "caso_base_bom.json"


def test_la_fixture_con_bom_realmente_tiene_bom() -> None:
    """Si la fixture perdiera el BOM, la prueba de regresion no probaria nada."""
    assert CASO_BOM.read_bytes()[:3] == b"\xef\xbb\xbf"


def test_lee_json_con_bom() -> None:
    datos = leer_json(CASO_BOM)
    assert datos["fecha_corte"] == "2026-06-30"


def test_lee_json_sin_bom() -> None:
    assert leer_json(CASO)["fecha_corte"] == "2026-06-30"


def test_mismo_resultado_con_y_sin_bom() -> None:
    """El BOM es de codificacion, no de contenido: no puede alterar una cifra."""
    a = json.dumps(calcular(leer_json(CASO)), default=str, sort_keys=True)
    b = json.dumps(calcular(leer_json(CASO_BOM)), default=str, sort_keys=True)
    assert a == b


def test_archivo_inexistente_da_mensaje_util() -> None:
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="No existe el archivo"):
        leer_json(RAIZ / "no_existe.json")


def test_json_malformado_indica_linea_y_columna(tmp_path: Path) -> None:
    malo = tmp_path / "malo.json"
    malo.write_text('{"a": 1,}', encoding="utf-8")
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="no es JSON válido"):
        leer_json(malo)


def test_json_que_no_es_objeto_rechazado(tmp_path: Path) -> None:
    lista = tmp_path / "lista.json"
    lista.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="objeto JSON en la raíz"):
        leer_json(lista)


def test_archivo_latin1_da_mensaje_orientado_a_excel(tmp_path: Path) -> None:
    latin = tmp_path / "latin.json"
    latin.write_bytes('{"socio": "Peña"}'.encode("latin-1"))
    with pytest.raises(ArchivoDeEntradaInvalidoError, match=r"Excel|Latin-1"):
        leer_texto(latin)


def test_la_salida_se_escribe_sin_bom(tmp_path: Path) -> None:
    """El manifiesto compara hashes: un BOM cambiaria el hash del mismo contenido."""
    destino = tmp_path / "salida.json"
    escribir_texto(destino, '{"a": 1}')
    assert destino.read_bytes()[:3] != b"\xef\xbb\xbf"
