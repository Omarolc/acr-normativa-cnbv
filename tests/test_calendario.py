"""Calendario de obligaciones y disparadores de plazo."""

from __future__ import annotations

from datetime import date

import pytest

from acr.motor import (
    evaluar_disparador_art16,
    generar_agenda,
    obligaciones_por_clasificacion,
)
from acr.normativa import cargar_registro

REG = cargar_registro()


def test_son_doce_calificaciones_mensuales_no_cuatro() -> None:
    """Correccion al plan original. El Anexo C Bis exige calificar la cartera
    con cifras al ultimo dia de CADA MES calendario."""
    eventos = generar_agenda(REG, date(2026, 1, 1), date(2026, 12, 31))
    mensuales = [e for e in eventos if e.id_obligacion == "OBL-CALIFICACION-MENSUAL"]
    assert len(mensuales) == 12
    assert all(e.fundamento == "Anexo C Bis" for e in mensuales)


def test_cuatro_computos_trimestrales_de_capitalizacion() -> None:
    eventos = generar_agenda(REG, date(2026, 1, 1), date(2026, 12, 31))
    computos = [e for e in eventos if e.id_obligacion == "OBL-COMPUTO-CAPITALIZACION"]
    assert len(computos) == 4
    assert [e.fecha_limite.month for e in computos] == [1, 4, 7, 10]


def test_el_corte_de_diciembre_se_entrega_en_enero_del_año_siguiente() -> None:
    eventos = generar_agenda(REG, date(2027, 1, 1), date(2027, 1, 31))
    computo = [e for e in eventos if e.id_obligacion == "OBL-COMPUTO-CAPITALIZACION"]
    assert len(computo) == 1
    assert computo[0].fecha_corte == date(2026, 12, 31)
    assert computo[0].fecha_limite == date(2027, 1, 31)


def test_dos_entregas_semestrales_impresas() -> None:
    eventos = generar_agenda(REG, date(2026, 1, 1), date(2026, 12, 31))
    impresas = [e for e in eventos if e.id_obligacion == "OBL-SEM-IMPRESA"]
    assert len(impresas) == 2
    assert all(e.medio == "impreso" for e in impresas)


def test_todos_los_eventos_van_al_comite_de_supervision_auxiliar_o_a_socios() -> None:
    """Nunca a la CNBV: no es la contraparte de Nivel Basico."""
    eventos = generar_agenda(REG, date(2026, 1, 1), date(2026, 12, 31))
    assert all("CNBV" not in e.destinatario for e in eventos)


def test_agenda_ordenada_por_fecha_limite() -> None:
    eventos = generar_agenda(REG, date(2026, 1, 1), date(2027, 6, 30))
    assert eventos == sorted(eventos, key=lambda e: (e.fecha_limite, e.id_obligacion))


def test_dias_restantes_solo_si_se_provee_hoy() -> None:
    sin_hoy = generar_agenda(REG, date(2026, 8, 1), date(2026, 8, 31))
    assert all(e.dias_restantes is None for e in sin_hoy)
    con_hoy = generar_agenda(REG, date(2026, 8, 1), date(2026, 8, 31), hoy=date(2026, 8, 4))
    assert all(e.dias_restantes is not None for e in con_hoy)


def test_evento_vencido() -> None:
    eventos = generar_agenda(REG, date(2026, 8, 1), date(2026, 8, 31))
    assert eventos[0].vencido(date(2026, 12, 1)) is True
    assert eventos[0].vencido(date(2026, 8, 1)) is False


def test_rango_invertido_rechazado() -> None:
    with pytest.raises(ValueError, match="no puede ser posterior"):
        generar_agenda(REG, date(2026, 12, 31), date(2026, 1, 1))


def test_obligacion_con_meses_desbalanceados_rechazada() -> None:
    obligaciones = [
        o.model_copy(update={"meses_entrega": [1]}) if o.id == "OBL-SEM-IMPRESA" else o
        for o in REG.obligaciones_de_entrega
    ]
    reg_roto = REG.model_copy(update={"obligaciones_de_entrega": obligaciones})
    with pytest.raises(ValueError, match="misma longitud"):
        generar_agenda(reg_roto, date(2026, 1, 1), date(2026, 12, 31))


# --- Art. 15, fracc. II -------------------------------------------------------


@pytest.mark.parametrize("categoria", ["C", "D"])
def test_clasificacion_en_c_o_d_dispara_plazos(categoria: str) -> None:
    obligaciones = obligaciones_por_clasificacion(REG, categoria, date(2026, 9, 15))
    assert len(obligaciones) == 2
    assert obligaciones[0].fecha_limite == date(2026, 10, 15)   # 30 dias
    assert obligaciones[1].fecha_limite == date(2026, 12, 14)   # +60 dias
    assert all("Art. 15" in o.fundamento for o in obligaciones)


@pytest.mark.parametrize("categoria", ["A", "B"])
def test_clasificacion_en_a_o_b_no_dispara_plazo_de_30_dias(categoria: str) -> None:
    assert obligaciones_por_clasificacion(REG, categoria, date(2026, 9, 15)) == []


# --- Art. 16 ------------------------------------------------------------------


def test_disparador_art16_activado_calcula_fecha_limite() -> None:
    d = evaluar_disparador_art16(
        REG, fecha_corte=date(2026, 6, 30), excede_limite=True, hoy=date(2026, 8, 4)
    )
    assert d.activado is True
    assert d.plazo_dias == 150
    assert d.fecha_limite_solicitud == date(2026, 11, 27)
    assert d.dias_restantes == 115


def test_disparador_art16_inactivo_sin_exceso() -> None:
    d = evaluar_disparador_art16(REG, fecha_corte=date(2026, 6, 30), excede_limite=False)
    assert d.activado is False
    assert d.fecha_limite_solicitud is None
    assert d.dias_restantes is None
