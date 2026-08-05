"""Guardas contra registro normativo corrupto.

El motor nunca degrada: si el registro no trae un parametro que la norma exige,
levanta excepcion en vez de asumir un valor. Estas pruebas construyen registros
deliberadamente malformados para demostrar que las guardas funcionan.

Sin estas pruebas las guardas serian codigo muerto no verificado, que es
exactamente donde se esconden los fallos silenciosos.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from acr.motor import (
    Capitalizacion,
    Certificado,
    EstadoInconsistenteError,
    RequisitoDesconocidoError,
    clasificar,
    evaluar_certificado,
)
from acr.normativa import cargar_registro

REG = cargar_registro()


def test_capitalizacion_inconsistente_no_degrada() -> None:
    """nivel_exacto nulo sin sin_requerimiento es un estado imposible.

    Si ocurriera, el motor debe abortar. Degradar a nivel cero produciria una
    categoria D fabricada.
    """
    rota = Capitalizacion(
        cartera_vigente=Decimal(1),
        cartera_vencida=Decimal(0),
        estimacion_preventiva=Decimal(0),
        cartera_neta=Decimal(1),
        requerimiento=Decimal("0.08"),
        capital_neto=Decimal(1),
        nivel_pct=None,
        nivel_exacto=None,
        sin_requerimiento=False,
        fecha_corte="2026-06-30",
        factor_requerimiento=Decimal("0.08"),
        fundamento=("x",),
    )
    with pytest.raises(EstadoInconsistenteError, match="nivel_exacto es None"):
        clasificar(
            REG, rota, eeff_cumplen_reglas_presentacion=True,
            eeff_presentados_en_plazo=True,
        )


def test_registro_sin_umbral_de_categoria_aborta() -> None:
    """Un registro al que le falta un umbral no puede clasificar."""
    umbrales = [
        u.model_copy(update={"nivel_min": None}) if u.categoria == "A" else u
        for u in REG.clasificacion.umbrales
    ]
    clasif_rota = REG.clasificacion.model_copy(update={"umbrales": umbrales})
    reg_roto = REG.model_copy(update={"clasificacion": clasif_rota})

    cap = Capitalizacion(
        cartera_vigente=Decimal(1_000_000),
        cartera_vencida=Decimal(0),
        estimacion_preventiva=Decimal(0),
        cartera_neta=Decimal(1_000_000),
        requerimiento=Decimal(80_000),
        capital_neto=Decimal(200_000),
        nivel_pct=Decimal("250.00"),
        nivel_exacto=Decimal("250"),
        sin_requerimiento=False,
        fecha_corte="2026-06-30",
        factor_requerimiento=Decimal("0.08"),
        fundamento=("Disposiciones Art. 1 Bis 3",),
    )
    with pytest.raises(EstadoInconsistenteError, match="debe definir nivel_max"):
        clasificar(
            reg_roto, cap, eeff_cumplen_reglas_presentacion=True,
            eeff_presentados_en_plazo=True,
        )


def test_requisito_de_certificado_ausente_del_registro_aborta() -> None:
    """Si el registro pierde un requisito del Art. 1 Bis 5, el evaluador aborta
    en vez de evaluar de menos y declarar elegible."""
    requisitos = [
        r for r in REG.certificados_elegibilidad.requisitos if r.id != "leyenda_retiro"
    ]
    cert_spec = REG.certificados_elegibilidad.model_copy(update={"requisitos": requisitos})
    reg_roto = REG.model_copy(update={"certificados_elegibilidad": cert_spec})

    cert = Certificado(
        id_emision="E-1",
        importe=Decimal(1000),
        tasa_rendimiento=Decimal("10"),
        ccp_a_fecha_emision=Decimal("8"),
        programa_asamblea=True,
        plazo_definido=True,
        numerados_mismo_valor=True,
        terminos_pago=True,
        leyenda_no_deposito=True,
        leyenda_retiro=True,
    )
    with pytest.raises(RequisitoDesconocidoError, match="leyenda_retiro"):
        evaluar_certificado(reg_roto, cert)


def test_tabla_de_mora_con_hueco_es_rechazada_por_el_esquema() -> None:
    """Un hueco en la tabla del Anexo C Bis deja creditos sin porcentaje
    aplicable, que en la practica se vuelve estimacion cero."""
    from acr.normativa.esquema import EstimacionesSpec

    with pytest.raises(ValueError, match="contigua desde 0"):
        EstimacionesSpec.model_validate(
            {
                "fundamento": "x", "periodicidad": "mensual", "base_cifras": "x",
                "base_dias_mora": "x", "base_importe": "x", "exclusion": "x",
                "estratos": [
                    {"dias_min": 0, "dias_max": 0, "porcentaje": "1"},
                    {"dias_min": 5, "dias_max": None, "porcentaje": "100"},
                ],
            }
        )


def test_tabla_de_mora_sin_estrato_abierto_es_rechazada() -> None:
    from acr.normativa.esquema import EstimacionesSpec

    with pytest.raises(ValueError, match="dias_max nulo"):
        EstimacionesSpec.model_validate(
            {
                "fundamento": "x", "periodicidad": "mensual", "base_cifras": "x",
                "base_dias_mora": "x", "base_importe": "x", "exclusion": "x",
                "estratos": [{"dias_min": 0, "dias_max": 180, "porcentaje": "1"}],
            }
        )
