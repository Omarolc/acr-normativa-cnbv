"""Pruebas del registro normativo.

Estas pruebas llevan los valores de la norma A MANO, no los leen del YAML.
Si los leyeran del mismo archivo que validan, pasarian aunque alguien
corrompiera el registro. Son el contrapeso independiente.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from acr.normativa import (
    RegistroNoVigenteError,
    VigenciaBloqueadaError,
    cargar_registro,
    hash_registro,
    verificar_fecha_corte_trimestral,
    verificar_vigencia,
)

REG = cargar_registro()


def test_factor_de_requerimiento_es_ocho_por_ciento() -> None:
    """Disposiciones Art. 1 Bis 3."""
    assert REG.parametros.capitalizacion.factor_requerimiento == Decimal("0.08")


def test_limite_de_activos_son_dos_millones_quinientos_mil_udis() -> None:
    """LRASCAP Art. 13."""
    assert REG.parametros.limite_activos.valor_udis == Decimal("2500000")


def test_plazo_del_articulo_16_son_ciento_cincuenta_dias() -> None:
    assert REG.parametros.limite_activos.plazo_solicitud_dias == 150


def test_umbrales_de_categoria_son_150_100_y_50() -> None:
    """LRASCAP Art. 15, fracc. I."""
    assert REG.clasificacion.umbral("A").nivel_min == Decimal("150")
    assert REG.clasificacion.umbral("B").nivel_min == Decimal("100")
    assert REG.clasificacion.umbral("C").nivel_min == Decimal("50")
    assert REG.clasificacion.umbral("D").nivel_max == Decimal("50")


def test_limite_de_personas_relacionadas_es_diez_por_ciento() -> None:
    """LRASCAP Art. 26."""
    p = REG.parametros.personas_relacionadas
    assert p.limite_pct_capital_contable == Decimal("10")
    assert p.umbral_exencion_udis == Decimal("100000")
    assert p.umbral_exencion_factor_capital_social == Decimal("0.02")


def test_factor_maximo_del_ccp_es_ciento_cincuenta_por_ciento() -> None:
    """Disposiciones Art. 1 Bis 5."""
    assert REG.parametros.certificados.factor_maximo_ccp == Decimal("1.50")


def test_tabla_del_anexo_c_bis_completa_y_exacta() -> None:
    esperada = [
        (0, 0, "1"), (1, 7, "2"), (8, 30, "10"), (31, 60, "20"),
        (61, 90, "40"), (91, 120, "70"), (121, 180, "85"), (181, None, "100"),
    ]
    reales = [
        (e.dias_min, e.dias_max, str(e.porcentaje))
        for e in REG.estimaciones_preventivas.estratos
    ]
    assert reales == esperada


def test_supuestos_del_parrafo_57_completos() -> None:
    ids = {s.id for s in REG.cartera_vencida.supuestos}
    assert ids == {
        "PAGO_UNICO_PRINCIPAL_E_INTERESES",
        "PAGO_UNICO_PRINCIPAL_INTERESES_PERIODICOS",
        "PAGOS_PERIODICOS_PARCIALES",
        "AMORTIZACIONES_PERIODICAS",
        "REVOLVENTE",
    }


def test_pago_sostenido_tres_amortizaciones() -> None:
    """Anexo T, parrafo 48."""
    assert REG.pago_sostenido.amortizaciones_consecutivas == 3
    assert REG.pago_sostenido.umbral_dias_periodo_largo == 60


def test_siete_requisitos_de_certificados() -> None:
    assert len(REG.certificados_elegibilidad.requisitos) == 7


def test_calificacion_es_mensual_no_trimestral() -> None:
    """Anexo C Bis: cifras al ultimo dia de cada mes calendario."""
    assert REG.estimaciones_preventivas.periodicidad == "mensual"
    mensual = [o for o in REG.obligaciones_de_entrega if o.id == "OBL-CALIFICACION-MENSUAL"]
    assert len(mensual) == 1
    assert len(mensual[0].meses_corte) == 12


def test_computo_de_capitalizacion_es_trimestral() -> None:
    assert REG.parametros.capitalizacion.meses_corte == [3, 6, 9, 12]
    assert REG.parametros.capitalizacion.meses_entrega == [4, 7, 10, 1]


# --- Vigencia -----------------------------------------------------------------


def test_bloqueo_por_alerta_de_vigencia_2027() -> None:
    with pytest.raises(VigenciaBloqueadaError, match="REF-2027-ANEXOS"):
        verificar_vigencia(REG, date(2027, 3, 31))


def test_corte_dentro_de_vigencia_pasa() -> None:
    verificar_vigencia(REG, date(2026, 6, 30))


def test_corte_anterior_a_la_vigencia_rechazado() -> None:
    """El sistema no extrapola parametros hacia atras."""
    with pytest.raises(RegistroNoVigenteError, match="fuera de la vigencia"):
        verificar_vigencia(REG, date(2025, 12, 31))


def test_fecha_de_corte_debe_ser_cierre_trimestral() -> None:
    verificar_fecha_corte_trimestral(REG, date(2026, 6, 30))
    verificar_fecha_corte_trimestral(REG, date(2026, 12, 31))
    with pytest.raises(ValueError, match="cierre trimestral"):
        verificar_fecha_corte_trimestral(REG, date(2026, 5, 31))
    with pytest.raises(ValueError, match=r"último del mes"):
        verificar_fecha_corte_trimestral(REG, date(2026, 6, 15))


def test_hash_del_registro_es_estable() -> None:
    assert hash_registro() == hash_registro()
    assert len(hash_registro()) == 64


def test_no_aplican_a_basico_registradas_explicitamente() -> None:
    """Las reglas del regimen I-IV quedan documentadas para bloquear su regreso."""
    import yaml

    from acr.normativa import RUTA_REGISTRO

    datos = yaml.safe_load(RUTA_REGISTRO.read_text(encoding="utf-8"))
    excluidas = {e["fundamento"] for e in datos["excluidas_del_regimen_basico"]}
    assert "Disposiciones Art. 44" in excluidas
    assert "Disposiciones Art. 193 Bis" in excluidas
