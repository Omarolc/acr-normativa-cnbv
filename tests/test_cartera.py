"""Motor de cartera: mora, traspaso a vencida y estimaciones preventivas.

Incluye la PRUEBA ADVERSARIAL que detecta la regresión del defecto original:
un crédito a 36 meses sin un solo pago debe reportar mora desde el día 31,
no en el mes 37.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acr.motor import (
    Credito,
    EsquemaPagosNoPrevistoError,
    InsumoCarteraFaltanteError,
    calificar_cartera,
    calificar_credito,
    dias_mora,
    es_cartera_vencida,
    porcentaje_estimacion,
)
from acr.normativa import cargar_registro

REG = cargar_registro()
CALIF = date(2026, 6, 30)


def _credito(**kw: object) -> Credito:
    base: dict[str, object] = {
        "id_credito": "C-001",
        "esquema_pagos": "AMORTIZACIONES_PERIODICAS",
        "saldo_insoluto": Decimal(100_000),
        "intereses_devengados": Decimal(0),
        "fecha_primera_amortizacion_no_cubierta": None,
        "amortizaciones_vencidas": 0,
        "dias_vencido_intereses": 0,
        "periodos_facturacion_vencidos": 0,
    }
    base.update(kw)
    return Credito(**base)  # type: ignore[arg-type]


# =============================================================================
# LA PRUEBA ADVERSARIAL
# =============================================================================


def test_credito_a_36_meses_sin_un_solo_pago_reporta_mora_desde_el_dia_31() -> None:
    """Regresión del defecto original.

    La implementación anterior medía la mora contra el vencimiento FINAL:
        dias_mora = hoy - (fecha_otorgamiento + plazo)
    Con un crédito a 36 meses otorgado hace 12, eso daba mora cero y provisión
    cero. El Anexo C Bis cuenta desde la primera amortización no cubierta.
    """
    otorgado = date(2025, 6, 30)          # hace 12 meses
    primera_amortizacion = date(2025, 7, 30)  # nunca se pagó
    credito = _credito(
        saldo_insoluto=Decimal(500_000),
        fecha_primera_amortizacion_no_cubierta=primera_amortizacion,
        amortizaciones_vencidas=11,
    )
    d = dias_mora(credito, CALIF)
    assert d == (CALIF - primera_amortizacion).days
    assert d > 300, "El crédito lleva casi un año sin pago"

    calificado = calificar_credito(REG, credito, CALIF)
    assert calificado.es_vencida is True
    assert calificado.porcentaje == Decimal("100")
    assert calificado.estimacion == Decimal("500000.00")

    # El plazo del crédito NO participa en el cálculo: no existe como insumo.
    assert not hasattr(credito, "plazo")
    assert not hasattr(credito, "fecha_vencimiento")
    del otorgado


# =============================================================================
# TABLA DEL ANEXO C BIS
# =============================================================================


@pytest.mark.frontera
@pytest.mark.parametrize(
    ("dias", "pct"),
    [
        (0, "1"), (1, "2"), (7, "2"), (8, "10"), (30, "10"),
        (31, "20"), (60, "20"), (61, "40"), (90, "40"),
        (91, "70"), (120, "70"), (121, "85"), (180, "85"),
        (181, "100"), (5000, "100"),
    ],
)
def test_estratos_anexo_c_bis(dias: int, pct: str) -> None:
    porcentaje, fundamento = porcentaje_estimacion(REG, dias)
    assert porcentaje == Decimal(pct)
    assert "Anexo C Bis" in fundamento


def test_no_existe_estrato_con_cero_por_ciento() -> None:
    """Hallazgo central del Anexo C Bis: una cartera totalmente al corriente
    exige 1% de estimaciones. La implementación original reportaba 0%."""
    porcentajes = [e.porcentaje for e in REG.estimaciones_preventivas.estratos]
    assert Decimal(0) not in porcentajes
    assert porcentaje_estimacion(REG, 0)[0] == Decimal("1")


def test_cartera_al_corriente_exige_estimacion_del_uno_por_ciento() -> None:
    creditos = [
        _credito(id_credito=f"C-{i}", saldo_insoluto=Decimal(1_000_000)) for i in range(5)
    ]
    resumen = calificar_cartera(REG, creditos, CALIF)
    assert resumen.cartera_vigente == Decimal(5_000_000)
    assert resumen.cartera_vencida == Decimal(0)
    assert resumen.estimacion_preventiva == Decimal("50000.00")
    assert resumen.pct_estimacion() == Decimal("1.00")


def test_dias_mora_negativos_rechazados() -> None:
    with pytest.raises(ValueError, match="no pueden ser negativos"):
        porcentaje_estimacion(REG, -1)


def test_intereses_devengados_forman_parte_de_la_base() -> None:
    """El Anexo C Bis califica el importe total 'incluyendo los intereses que generan'."""
    sin_intereses = calificar_credito(REG, _credito(), CALIF)
    con_intereses = calificar_credito(
        REG, _credito(intereses_devengados=Decimal(10_000)), CALIF
    )
    assert con_intereses.base_calificacion > sin_intereses.base_calificacion
    assert con_intereses.estimacion == Decimal("1100.00")


def test_excluye_intereses_devengados_no_cobrados_de_cartera_vencida() -> None:
    """Exclusión expresa del Anexo C Bis."""
    credito = _credito(
        saldo_insoluto=Decimal(100_000),
        intereses_devengados=Decimal(20_000),
        intereses_devengados_no_cobrados_en_balance=Decimal(20_000),
        fecha_primera_amortizacion_no_cubierta=date(2025, 1, 1),
        amortizaciones_vencidas=12,
    )
    c = calificar_credito(REG, credito, CALIF)
    assert c.es_vencida is True
    assert c.base_calificacion == Decimal(100_000)


def test_base_negativa_rechazada() -> None:
    credito = _credito(
        saldo_insoluto=Decimal(100),
        intereses_devengados=Decimal(0),
        intereses_devengados_no_cobrados_en_balance=Decimal(9_999),
        fecha_primera_amortizacion_no_cubierta=date(2025, 1, 1),
        amortizaciones_vencidas=12,
    )
    with pytest.raises(InsumoCarteraFaltanteError, match="base de calificación negativa"):
        calificar_credito(REG, credito, CALIF)


# =============================================================================
# TRASPASO A CARTERA VENCIDA — Anexo T, párrafo 57
# =============================================================================


@pytest.mark.frontera
@pytest.mark.parametrize(
    ("esquema", "dias", "esperado"),
    [
        ("PAGO_UNICO_PRINCIPAL_E_INTERESES", 29, False),
        ("PAGO_UNICO_PRINCIPAL_E_INTERESES", 30, True),
        ("PAGO_UNICO_PRINCIPAL_INTERESES_PERIODICOS", 29, False),
        ("PAGO_UNICO_PRINCIPAL_INTERESES_PERIODICOS", 30, True),
        ("PAGOS_PERIODICOS_PARCIALES", 89, False),
        ("PAGOS_PERIODICOS_PARCIALES", 90, True),
        ("REVOLVENTE", 59, False),
        ("REVOLVENTE", 60, True),
    ],
)
def test_umbrales_de_dias_por_esquema(esquema: str, dias: int, esperado: bool) -> None:
    """Cada inciso del párrafo 57 tiene su propio umbral. No son intercambiables."""
    from datetime import timedelta

    credito = _credito(
        esquema_pagos=esquema,
        fecha_primera_amortizacion_no_cubierta=CALIF - timedelta(days=dias),
    )
    vencida, _ = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is esperado


@pytest.mark.frontera
@pytest.mark.parametrize(("amortizaciones", "esperado"), [(2, False), (3, True)])
def test_tres_amortizaciones_vencidas_inciso_d(amortizaciones: int, esperado: bool) -> None:
    credito = _credito(
        esquema_pagos="AMORTIZACIONES_PERIODICAS", amortizaciones_vencidas=amortizaciones
    )
    vencida, _ = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is esperado


@pytest.mark.frontera
@pytest.mark.parametrize(("periodos", "esperado"), [(1, False), (2, True)])
def test_periodos_facturacion_revolvente_inciso_e(periodos: int, esperado: bool) -> None:
    credito = _credito(esquema_pagos="REVOLVENTE", periodos_facturacion_vencidos=periodos)
    vencida, _ = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is esperado


@pytest.mark.frontera
@pytest.mark.parametrize(("dias_int", "esperado"), [(89, False), (90, True)])
def test_intereses_vencidos_inciso_b(dias_int: int, esperado: bool) -> None:
    credito = _credito(
        esquema_pagos="PAGO_UNICO_PRINCIPAL_INTERESES_PERIODICOS",
        dias_vencido_intereses=dias_int,
    )
    vencida, _ = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is esperado


def test_esquema_de_pagos_desconocido_falla_ruidosamente() -> None:
    credito = _credito(esquema_pagos="INVENTADO")
    with pytest.raises(EsquemaPagosNoPrevistoError, match="párrafo 57"):
        es_cartera_vencida(REG, credito, CALIF)


def test_pago_unico_reestructurado_siempre_vencido() -> None:
    """Anexo T, párrafo 59."""
    credito = _credito(
        esquema_pagos="PAGO_UNICO_PRINCIPAL_E_INTERESES", reestructurado=True
    )
    vencida, fundamento = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is True
    assert fundamento is not None and "59" in fundamento


def test_reestructurado_sin_pago_sostenido_permanece_vencido() -> None:
    """Anexo T, párrafo 58."""
    from datetime import timedelta

    credito = _credito(
        esquema_pagos="PAGOS_PERIODICOS_PARCIALES",
        reestructurado=True,
        tiene_pago_sostenido=False,
        fecha_primera_amortizacion_no_cubierta=CALIF - timedelta(days=10),
    )
    vencida, fundamento = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is True
    assert fundamento is not None and "58" in fundamento


def test_reestructurado_con_pago_sostenido_puede_ser_vigente() -> None:
    from datetime import timedelta

    credito = _credito(
        esquema_pagos="PAGOS_PERIODICOS_PARCIALES",
        reestructurado=True,
        tiene_pago_sostenido=True,
        fecha_primera_amortizacion_no_cubierta=CALIF - timedelta(days=10),
    )
    vencida, _ = es_cartera_vencida(REG, credito, CALIF)
    assert vencida is False


# =============================================================================
# CARTERA COMPLETA
# =============================================================================


def test_cartera_vacia() -> None:
    r = calificar_cartera(REG, [], CALIF)
    assert r.cartera_total == Decimal(0)
    assert r.estimacion_preventiva == Decimal(0)
    assert r.pct_estimacion() == Decimal(0)


def test_identificadores_duplicados_rechazados() -> None:
    with pytest.raises(InsumoCarteraFaltanteError, match="duplicados"):
        calificar_cartera(REG, [_credito(), _credito()], CALIF)


def test_fecha_de_amortizacion_futura_rechazada() -> None:
    credito = _credito(fecha_primera_amortizacion_no_cubierta=date(2027, 1, 1))
    with pytest.raises(InsumoCarteraFaltanteError, match="posterior a la fecha"):
        dias_mora(credito, CALIF)


def test_resumen_alimenta_los_renglones_1_2_y_3_del_anexo_u() -> None:
    from datetime import timedelta

    creditos = [
        _credito(id_credito="V-1", saldo_insoluto=Decimal(1_000_000)),
        _credito(
            id_credito="M-1",
            saldo_insoluto=Decimal(200_000),
            fecha_primera_amortizacion_no_cubierta=CALIF - timedelta(days=200),
            amortizaciones_vencidas=6,
        ),
    ]
    r = calificar_cartera(REG, creditos, CALIF)
    assert r.cartera_vigente == Decimal(1_000_000)
    assert r.cartera_vencida == Decimal(200_000)
    assert r.cartera_total == Decimal(1_200_000)
    # 1% de 1,000,000 + 100% de 200,000
    assert r.estimacion_preventiva == Decimal("210000.00")
    assert len(r.creditos) == 2
    assert all(c.fundamento for c in r.creditos)
