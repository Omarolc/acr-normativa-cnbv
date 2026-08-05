"""Trazabilidad: ninguna cifra sale del motor sin su fundamento legal.

Es lo que hace defendible el computo ante verificacion del Comite de
Supervision Auxiliar (Disposiciones Art. 1 Bis 6).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from acr.motor import (
    Credito,
    calcular_capital_neto,
    calcular_capitalizacion,
    calificar_cartera,
    clasificar,
    evaluar_certificados,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
)
from acr.normativa import cargar_registro

REG = cargar_registro()
CORTE = "2026-06-30"


def _cn():
    return calcular_capital_neto(
        REG, capital_contable=1_000_000, certificados_no_elegibles=50_000,
        financiamientos_partes_sociales=0,
    )


def _cap():
    return calcular_capitalizacion(
        REG, _cn(), cartera_vigente=4_500_000, cartera_vencida=500_000,
        estimacion_preventiva=260_500, fecha_corte=CORTE,
    )


def test_capital_neto_carga_fundamento() -> None:
    assert _cn().fundamento.strip() != ""
    assert "1 Bis 4" in _cn().fundamento


def test_capitalizacion_carga_fundamentos() -> None:
    cap = _cap()
    assert all(f.strip() for f in cap.fundamento)
    assert any("1 Bis 3" in f for f in cap.fundamento)


def test_toda_clasificacion_posible_carga_fundamento() -> None:
    cap = _cap()
    for reglas in (True, False):
        for plazo in (True, False):
            for hist in ([], ["C"], ["C", "C"]):
                c = clasificar(
                    REG, cap, eeff_cumplen_reglas_presentacion=reglas,
                    eeff_presentados_en_plazo=plazo, historial_categorias=hist,
                )
                assert c.fundamento.strip(), f"{reglas} {plazo} {hist}"
                assert c.motivo.strip()
                assert c.obligaciones_derivadas


def test_limite_activos_y_relacionadas_cargan_fundamento() -> None:
    lim = evaluar_limite_activos(
        REG, activos_totales=18_000_000, valor_udi_a_fecha_corte="8.52"
    )
    assert all(f.strip() for f in lim.fundamento)
    pr = evaluar_personas_relacionadas(
        REG, montos_dispuestos=40_000, lineas_de_credito_irrevocables=15_000,
        capital_contable=1_000_000, capital_social_pagado=800_000,
        valor_udi_a_fecha_corte="8.52",
    )
    assert "Art. 26" in pr.fundamento


def test_cada_credito_calificado_carga_fundamento() -> None:
    creditos = [
        Credito(
            id_credito="C-1", esquema_pagos="AMORTIZACIONES_PERIODICAS",
            saldo_insoluto=Decimal(100_000), intereses_devengados=Decimal(0),
            fecha_primera_amortizacion_no_cubierta=None, amortizaciones_vencidas=0,
            dias_vencido_intereses=0, periodos_facturacion_vencidos=0,
        )
    ]
    r = calificar_cartera(REG, creditos, date(2026, 6, 30))
    assert all(c.fundamento.strip() for c in r.creditos)
    assert r.fundamento.strip()


def test_certificados_cargan_fundamento() -> None:
    r = evaluar_certificados(REG, [])
    assert "1 Bis 5" in r.fundamento


def test_formulario_anexo_u_tiene_los_diez_renglones() -> None:
    cn, cap = _cn(), _cap()
    filas = cap.formulario_anexo_u(cn)
    assert [n for n, _, _ in filas] == list(range(1, 11))
    assert all(concepto.strip() for _, concepto, _ in filas)
