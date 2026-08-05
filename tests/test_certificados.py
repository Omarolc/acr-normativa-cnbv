"""Evaluador de certificados excedentes o voluntarios — Art. 1 Bis 5.

Solo la porcion que INCUMPLE se deduce del capital contable. La version
original deducia la totalidad de los certificados excedentes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from acr.motor import Certificado, evaluar_certificado, evaluar_certificados
from acr.normativa import cargar_registro

REG = cargar_registro()


def _cert(**kw: object) -> Certificado:
    base: dict[str, object] = {
        "id_emision": "E-2026-01",
        "importe": Decimal(100_000),
        "tasa_rendimiento": Decimal("10"),
        "ccp_a_fecha_emision": Decimal("8"),
        "programa_asamblea": True,
        "plazo_definido": True,
        "numerados_mismo_valor": True,
        "terminos_pago": True,
        "leyenda_no_deposito": True,
        "leyenda_retiro": True,
    }
    base.update(kw)
    return Certificado(**base)  # type: ignore[arg-type]


def test_certificado_que_cumple_todo_es_elegible() -> None:
    e = evaluar_certificado(REG, _cert())
    assert e.elegible is True
    assert e.incumplimientos == []


@pytest.mark.frontera
def test_tasa_exactamente_en_el_tope_es_elegible() -> None:
    """150% del CCP a la fecha de emision. 8 * 1.50 = 12."""
    assert evaluar_certificado(
        REG, _cert(tasa_rendimiento=Decimal("12"), ccp_a_fecha_emision=Decimal("8"))
    ).elegible is True
    e = evaluar_certificado(
        REG, _cert(tasa_rendimiento=Decimal("12.01"), ccp_a_fecha_emision=Decimal("8"))
    )
    assert e.elegible is False
    assert any("tasa_maxima" in i for i in e.incumplimientos)


def test_ccp_es_el_de_la_fecha_de_emision() -> None:
    """No el vigente al corte. Dos emisiones con misma tasa y distinto CCP
    de emision tienen elegibilidad distinta."""
    alta = evaluar_certificado(
        REG, _cert(tasa_rendimiento=Decimal("14"), ccp_a_fecha_emision=Decimal("10"))
    )
    baja = evaluar_certificado(
        REG, _cert(tasa_rendimiento=Decimal("14"), ccp_a_fecha_emision=Decimal("8"))
    )
    assert alta.elegible is True
    assert baja.elegible is False


@pytest.mark.parametrize(
    "requisito",
    [
        "programa_asamblea", "plazo_definido", "numerados_mismo_valor",
        "terminos_pago", "leyenda_no_deposito", "leyenda_retiro",
    ],
)
def test_cada_requisito_faltante_hace_no_elegible(requisito: str) -> None:
    e = evaluar_certificado(REG, _cert(**{requisito: False}))
    assert e.elegible is False
    assert any(requisito in i for i in e.incumplimientos)


def test_capital_no_retirable_gubernamental_esta_exento() -> None:
    e = evaluar_certificado(
        REG,
        _cert(
            capital_no_retirable_programa_gubernamental=True,
            programa_asamblea=False,
            leyenda_retiro=False,
        ),
    )
    assert e.exento is True
    assert e.elegible is True


def test_importe_negativo_rechazado() -> None:
    with pytest.raises(ValueError, match="importe negativo"):
        evaluar_certificado(REG, _cert(importe=Decimal(-1)))


def test_solo_la_porcion_no_elegible_se_deduce() -> None:
    """El defecto corregido: no se deduce la totalidad de los certificados."""
    resumen = evaluar_certificados(
        REG,
        [
            _cert(id_emision="A", importe=Decimal(300_000)),
            _cert(id_emision="B", importe=Decimal(200_000), leyenda_retiro=False),
        ],
    )
    assert resumen.importe_total == Decimal(500_000)
    assert resumen.importe_elegible == Decimal(300_000)
    assert resumen.importe_no_elegible == Decimal(200_000)


def test_lista_vacia() -> None:
    r = evaluar_certificados(REG, [])
    assert r.importe_total == Decimal(0)
    assert r.importe_no_elegible == Decimal(0)
