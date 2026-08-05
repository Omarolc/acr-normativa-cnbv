"""Pruebas de frontera: los valores exactos de los umbrales normativos.

Un umbral mal implementado (>= vs >) cambia la categoría de una cooperativa.
Estas pruebas fijan el comportamiento en el punto exacto, no cerca.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from acr.motor import (
    InsumoFaltanteError,
    calcular_capital_neto,
    calcular_capitalizacion,
    clasificar,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
)
from acr.normativa import cargar_registro

REG = cargar_registro()
CORTE = "2026-06-30"


def _cap(nivel_objetivo: str, cartera_vigente: int = 5_000_000):
    """Construye un caso cuyo nivel de capitalización es exactamente el pedido."""
    req = Decimal(cartera_vigente) * REG.parametros.capitalizacion.factor_requerimiento
    capital = req * Decimal(nivel_objetivo) / Decimal(100)
    cn = calcular_capital_neto(
        REG,
        capital_contable=capital,
        certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    return cn, calcular_capitalizacion(
        REG,
        cn,
        cartera_vigente=cartera_vigente,
        cartera_vencida=0,
        estimacion_preventiva=0,
        fecha_corte=CORTE,
    )


def _clasif(nivel: str, **kw: object) -> str:
    _, cap = _cap(nivel)
    opciones: dict[str, object] = {
        "eeff_cumplen_reglas_presentacion": True,
        "eeff_presentados_en_plazo": True,
        "historial_categorias": [],
    }
    opciones.update(kw)
    return clasificar(REG, cap, **opciones).categoria  # type: ignore[arg-type]


# --- Fronteras de categoría (Art. 15, fracc. I) ------------------------------


@pytest.mark.frontera
@pytest.mark.parametrize(
    ("nivel", "esperada"),
    [
        ("149.99", "B"),
        ("150.00", "A"),
        ("150.01", "A"),
        ("99.99", "C"),
        ("100.00", "B"),
        ("100.01", "B"),
        ("49.99", "C"),
        ("50.00", "C"),
        ("50.01", "C"),
        ("0.01", "C"),
    ],
)
def test_frontera_categoria(nivel: str, esperada: str) -> None:
    assert _clasif(nivel) == esperada


@pytest.mark.frontera
def test_nivel_exacto_en_umbral_es_inclusivo_hacia_arriba() -> None:
    """150.00 es A, no B. 100.00 es B, no C. El umbral pertenece al rango superior."""
    _, cap = _cap("150.00")
    assert cap.nivel_pct == Decimal("150.00")
    assert _clasif("150.00") == "A"
    assert _clasif("100.00") == "B"


# --- Caso borde: requerimiento cero -------------------------------------------


@pytest.mark.frontera
def test_requerimiento_cero_es_cumplimiento_pleno() -> None:
    """Sin cartera no hay requerimiento que incumplir. No es categoría D."""
    cn = calcular_capital_neto(
        REG,
        capital_contable=1_000_000,
        certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    cap = calcular_capitalizacion(
        REG, cn, cartera_vigente=0, cartera_vencida=0, estimacion_preventiva=0,
        fecha_corte=CORTE,
    )
    assert cap.sin_requerimiento is True
    assert cap.nivel_pct is None
    c = clasificar(
        REG, cap, eeff_cumplen_reglas_presentacion=True, eeff_presentados_en_plazo=True
    )
    assert c.categoria == "A"
    assert c.debe_abstenerse_captacion is False


@pytest.mark.frontera
def test_requerimiento_cero_con_eeff_defectuosos_es_categoria_c() -> None:
    cn = calcular_capital_neto(
        REG, capital_contable=1_000_000, certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    cap = calcular_capitalizacion(
        REG, cn, cartera_vigente=0, cartera_vencida=0, estimacion_preventiva=0,
        fecha_corte=CORTE,
    )
    c = clasificar(
        REG, cap, eeff_cumplen_reglas_presentacion=False, eeff_presentados_en_plazo=True
    )
    assert c.categoria == "C"
    assert c.requiere_notificacion_plazo is True


# --- Capital neto negativo ----------------------------------------------------


@pytest.mark.frontera
def test_capital_neto_negativo_produce_nivel_negativo_y_categoria_baja() -> None:
    cn = calcular_capital_neto(
        REG, capital_contable=100_000, certificados_no_elegibles=500_000,
        financiamientos_partes_sociales=0,
    )
    assert cn.valor < 0
    cap = calcular_capitalizacion(
        REG, cn, cartera_vigente=5_000_000, cartera_vencida=0, estimacion_preventiva=0,
        fecha_corte=CORTE,
    )
    assert cap.nivel_pct is not None and cap.nivel_pct < 0
    c = clasificar(
        REG, cap, eeff_cumplen_reglas_presentacion=True, eeff_presentados_en_plazo=False
    )
    assert c.categoria == "D"


# --- Validaciones de insumos ---------------------------------------------------


@pytest.mark.frontera
def test_estimacion_mayor_que_cartera_falla() -> None:
    cn = calcular_capital_neto(
        REG, capital_contable=1_000_000, certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    with pytest.raises(ValueError, match="excede la cartera total"):
        calcular_capitalizacion(
            REG, cn, cartera_vigente=100, cartera_vencida=0, estimacion_preventiva=500,
            fecha_corte=CORTE,
        )


@pytest.mark.frontera
def test_insumo_ausente_levanta_excepcion_no_asume_cero() -> None:
    with pytest.raises(InsumoFaltanteError, match="hechos distintos"):
        calcular_capital_neto(
            REG, capital_contable=None, certificados_no_elegibles=0,
            financiamientos_partes_sociales=0,
        )


@pytest.mark.frontera
def test_deducciones_negativas_rechazadas() -> None:
    with pytest.raises(ValueError, match="valor absoluto positivo"):
        calcular_capital_neto(
            REG, capital_contable=1000, certificados_no_elegibles=-1,
            financiamientos_partes_sociales=0,
        )


@pytest.mark.frontera
def test_cartera_negativa_rechazada() -> None:
    cn = calcular_capital_neto(
        REG, capital_contable=1000, certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    with pytest.raises(ValueError, match="se expresan en positivo"):
        calcular_capitalizacion(
            REG, cn, cartera_vigente=-1, cartera_vencida=0, estimacion_preventiva=0,
            fecha_corte=CORTE,
        )
    with pytest.raises(ValueError, match="se expresa en positivo"):
        calcular_capitalizacion(
            REG, cn, cartera_vigente=1000, cartera_vencida=0, estimacion_preventiva=-1,
            fecha_corte=CORTE,
        )


# --- Límite de activos (Art. 13) ----------------------------------------------


@pytest.mark.frontera
def test_limite_activos_frontera_exacta() -> None:
    """Exactamente 2'500,000 UDIS no excede. Un peso más, sí."""
    udi = Decimal("8.00")
    limite = REG.parametros.limite_activos.valor_udis
    exacto = evaluar_limite_activos(
        REG, activos_totales=limite * udi, valor_udi_a_fecha_corte=udi
    )
    assert exacto.excede is False
    assert exacto.holgura_pct == Decimal("0.00")

    encima = evaluar_limite_activos(
        REG, activos_totales=limite * udi + 1, valor_udi_a_fecha_corte=udi
    )
    assert encima.excede is True
    assert encima.plazo_solicitud_dias == REG.parametros.limite_activos.plazo_solicitud_dias


@pytest.mark.frontera
def test_udi_no_positiva_rechazada() -> None:
    with pytest.raises(ValueError, match="Banco de México"):
        evaluar_limite_activos(REG, activos_totales=1000, valor_udi_a_fecha_corte=0)


# --- Personas relacionadas (Art. 26) ------------------------------------------


@pytest.mark.frontera
def test_personas_relacionadas_frontera_del_limite() -> None:
    base = {
        "capital_contable": 1_000_000,
        "capital_social_pagado": 800_000,
        "valor_udi_a_fecha_corte": "8.52",
        "lineas_de_credito_irrevocables": 0,
    }
    exacto = evaluar_personas_relacionadas(REG, montos_dispuestos=100_000, **base)  # type: ignore[arg-type]
    assert exacto.porcentaje == Decimal("10.00")
    assert exacto.cumple is True

    encima = evaluar_personas_relacionadas(REG, montos_dispuestos=100_001, **base)  # type: ignore[arg-type]
    assert encima.cumple is False


@pytest.mark.frontera
def test_lineas_irrevocables_cuentan_para_el_limite() -> None:
    """Considerar solo saldos dispuestos subestima la exposición del Art. 26."""
    solo_dispuesto = evaluar_personas_relacionadas(
        REG, montos_dispuestos=90_000, lineas_de_credito_irrevocables=0,
        capital_contable=1_000_000, capital_social_pagado=800_000,
        valor_udi_a_fecha_corte="8.52",
    )
    con_lineas = evaluar_personas_relacionadas(
        REG, montos_dispuestos=90_000, lineas_de_credito_irrevocables=20_000,
        capital_contable=1_000_000, capital_social_pagado=800_000,
        valor_udi_a_fecha_corte="8.52",
    )
    assert solo_dispuesto.cumple is True
    assert con_lineas.cumple is False


@pytest.mark.frontera
def test_umbral_exencion_es_el_menor_de_los_dos() -> None:
    """El menor entre 100,000 UDIS y 2% del capital social pagado."""
    r = evaluar_personas_relacionadas(
        REG, montos_dispuestos=0, lineas_de_credito_irrevocables=0,
        capital_contable=1_000_000, capital_social_pagado=800_000,
        valor_udi_a_fecha_corte="8.52",
    )
    en_udis = REG.parametros.personas_relacionadas.umbral_exencion_udis * Decimal("8.52")
    por_capital = Decimal(800_000) * (
        REG.parametros.personas_relacionadas.umbral_exencion_factor_capital_social
    )
    assert r.umbral_exencion == min(en_udis, por_capital)
    assert r.umbral_exencion == por_capital


@pytest.mark.frontera
def test_capital_contable_cero_no_divide_entre_cero() -> None:
    r = evaluar_personas_relacionadas(
        REG, montos_dispuestos=100, lineas_de_credito_irrevocables=0,
        capital_contable=0, capital_social_pagado=0, valor_udi_a_fecha_corte="8.52",
    )
    assert r.porcentaje is None
    assert r.cumple is False
