"""Carga del valor de la UDI desde archivo. Nunca por red, nunca interpolado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from acr.entrada import ArchivoDeEntradaInvalidoError
from acr.udis import ValorUdiNoDisponibleError, cargar_udis, valor_udi_en

CSV = "fecha,valor\n2026-03-31,8.480000\n2026-06-30,8.520000\n2026-09-30,8.610000\n"


def _archivo(tmp_path: Path, contenido: str = CSV, bom: bool = False) -> Path:
    ruta = tmp_path / "udis.csv"
    datos = contenido.encode("utf-8")
    ruta.write_bytes(b"\xef\xbb\xbf" + datos if bom else datos)
    return ruta


def test_carga_valores(tmp_path: Path) -> None:
    valores = cargar_udis(_archivo(tmp_path))
    assert valores[date(2026, 6, 30)] == Decimal("8.520000")
    assert len(valores) == 3


def test_tolera_bom(tmp_path: Path) -> None:
    """El archivo de UDIS tambien puede venir de Excel."""
    assert len(cargar_udis(_archivo(tmp_path, bom=True))) == 3


def test_valor_exacto_de_la_fecha(tmp_path: Path) -> None:
    valores = cargar_udis(_archivo(tmp_path))
    assert valor_udi_en(valores, date(2026, 3, 31)) == Decimal("8.480000")


def test_no_interpola_ni_toma_el_mas_cercano(tmp_path: Path) -> None:
    """Interpolar produciria un valor que Banco de Mexico nunca publico."""
    valores = cargar_udis(_archivo(tmp_path))
    with pytest.raises(ValorUdiNoDisponibleError, match="no interpola"):
        valor_udi_en(valores, date(2026, 12, 31))


def test_columnas_incorrectas(tmp_path: Path) -> None:
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="dos columnas"):
        cargar_udis(_archivo(tmp_path, "fecha,valor\n2026-06-30,8.52,extra\n"))


def test_fecha_invalida(tmp_path: Path) -> None:
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="fecha o valor inválido"):
        cargar_udis(_archivo(tmp_path, "fecha,valor\n30-06-2026,8.52\n"))


def test_valor_no_positivo(tmp_path: Path) -> None:
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="debe ser positivo"):
        cargar_udis(_archivo(tmp_path, "fecha,valor\n2026-06-30,0\n"))


def test_archivo_vacio(tmp_path: Path) -> None:
    with pytest.raises(ArchivoDeEntradaInvalidoError, match="no contiene valores"):
        cargar_udis(_archivo(tmp_path, "fecha,valor\n"))
