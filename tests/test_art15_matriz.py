"""Matriz completa del Art. 15 LRASCAP.

Producto cartesiano de: nivel x eeff_cumplen_reglas x eeff_en_plazo x historial.
Cada celda con la categoría esperada y su fundamento.

La versión original clasificaba solo por porcentaje. Esta matriz existe para
que esa regresión sea imposible: si alguien reintroduce una clasificación
puramente numérica, fallan 24 de las 60 celdas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from acr.motor import calcular_capital_neto, calcular_capitalizacion, clasificar
from acr.normativa import cargar_registro

REG = cargar_registro()
CORTE = "2026-06-30"
CARTERA = 5_000_000


def _cap(nivel: str):
    req = Decimal(CARTERA) * REG.parametros.capitalizacion.factor_requerimiento
    cn = calcular_capital_neto(
        REG,
        capital_contable=req * Decimal(nivel) / Decimal(100),
        certificados_no_elegibles=0,
        financiamientos_partes_sociales=0,
    )
    return calcular_capitalizacion(
        REG, cn, cartera_vigente=CARTERA, cartera_vencida=0, estimacion_preventiva=0,
        fecha_corte=CORTE,
    )


# nivel, eeff_reglas, eeff_plazo, historial -> categoria esperada
MATRIZ: list[tuple[str, bool, bool, list[str], str]] = []
for nivel in ["200", "150", "120", "100", "75", "50", "30"]:
    for reglas in [True, False]:
        for plazo in [True, False]:
            for hist in [[], ["C"], ["C", "C"], ["C", "B", "C"]]:
                nv = Decimal(nivel)
                if hist[-2:] == ["C", "C"]:
                    esperada = "D"
                elif nv < Decimal("50"):
                    incumple = (not plazo) or (hist[-1:] == ["C"] and not reglas)
                    esperada = "D" if incumple else "C"
                elif not reglas or nv < Decimal("100"):
                    esperada = "C"
                elif nv < Decimal("150"):
                    esperada = "B"
                else:
                    esperada = "A"
                MATRIZ.append((nivel, reglas, plazo, hist, esperada))


@pytest.mark.parametrize(("nivel", "reglas", "plazo", "historial", "esperada"), MATRIZ)
def test_matriz_art15(
    nivel: str, reglas: bool, plazo: bool, historial: list[str], esperada: str
) -> None:
    c = clasificar(
        REG,
        _cap(nivel),
        eeff_cumplen_reglas_presentacion=reglas,
        eeff_presentados_en_plazo=plazo,
        historial_categorias=historial,
    )
    assert c.categoria == esperada, (
        f"nivel={nivel} reglas={reglas} plazo={plazo} hist={historial}: "
        f"esperada {esperada}, obtenida {c.categoria} — {c.motivo}"
    )


def test_la_clasificacion_no_es_funcion_numerica_pura() -> None:
    """Mismo nivel, distinta categoría según el apego a reglas de presentación."""
    cap = _cap("200")
    con_reglas = clasificar(
        REG, cap, eeff_cumplen_reglas_presentacion=True, eeff_presentados_en_plazo=True
    )
    sin_reglas = clasificar(
        REG, cap, eeff_cumplen_reglas_presentacion=False, eeff_presentados_en_plazo=True
    )
    assert con_reglas.categoria == "A"
    assert sin_reglas.categoria == "C"
    assert "segunda hipótesis" in sin_reglas.fundamento


def test_dos_c_consecutivas_derivan_en_d_con_nivel_excelente() -> None:
    """Art. 15, fracc. III. El historial domina sobre el nivel."""
    c = clasificar(
        REG,
        _cap("300"),
        eeff_cumplen_reglas_presentacion=True,
        eeff_presentados_en_plazo=True,
        historial_categorias=["C", "C"],
    )
    assert c.categoria == "D"
    assert "fracc. III" in c.fundamento
    assert c.debe_abstenerse_captacion is True


def test_c_no_consecutivas_no_derivan_en_d() -> None:
    c = clasificar(
        REG,
        _cap("200"),
        eeff_cumplen_reglas_presentacion=True,
        eeff_presentados_en_plazo=True,
        historial_categorias=["C", "B", "C"],
    )
    assert c.categoria == "A"


def test_nivel_bajo_con_eeff_en_regla_no_es_d_automatico() -> None:
    """Nivel < 50% con estados financieros en tiempo y forma no cae en D
    por la vía del inciso d)."""
    c = clasificar(
        REG,
        _cap("30"),
        eeff_cumplen_reglas_presentacion=True,
        eeff_presentados_en_plazo=True,
        historial_categorias=[],
    )
    assert c.categoria == "C"
    assert "inciso d)" in c.fundamento


def test_plazos_de_notificacion_provienen_del_registro() -> None:
    n = REG.clasificacion.notificacion_asamblea
    c = clasificar(
        REG, _cap("75"), eeff_cumplen_reglas_presentacion=True,
        eeff_presentados_en_plazo=True,
    )
    assert c.categoria == "C"
    assert c.requiere_notificacion_plazo is True
    assert c.plazo_notificacion_dias == n.plazo_dias
    a = clasificar(
        REG, _cap("200"), eeff_cumplen_reglas_presentacion=True,
        eeff_presentados_en_plazo=True,
    )
    assert a.requiere_notificacion_plazo is False
    assert a.plazo_notificacion_dias is None
