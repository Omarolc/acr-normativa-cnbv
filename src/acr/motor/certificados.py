"""Evaluador de certificados excedentes o voluntarios — Disposiciones Art. 1 Bis 5.

Solo la porción que INCUMPLE el Art. 1 Bis 5 se deduce del capital contable
(renglón 7 del formulario del Anexo U). La implementación original deducía la
totalidad de los certificados excedentes sin evaluar su elegibilidad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from acr.normativa.esquema import Registro

CERO = Decimal(0)


class RequisitoDesconocidoError(KeyError):
    """Se evaluó un requisito que no existe en el registro normativo."""


@dataclass(frozen=True)
class Certificado:
    """Un tramo de certificados excedentes o voluntarios de una misma emisión."""

    id_emision: str
    importe: Decimal
    tasa_rendimiento: Decimal
    ccp_a_fecha_emision: Decimal
    programa_asamblea: bool
    plazo_definido: bool
    numerados_mismo_valor: bool
    terminos_pago: bool
    leyenda_no_deposito: bool
    leyenda_retiro: bool
    capital_no_retirable_programa_gubernamental: bool = False


@dataclass(frozen=True)
class EvaluacionCertificado:
    id_emision: str
    importe: Decimal
    elegible: bool
    exento: bool
    incumplimientos: list[str] = field(default_factory=list)
    fundamento: str = ""


@dataclass(frozen=True)
class ResumenCertificados:
    importe_total: Decimal
    importe_elegible: Decimal
    importe_no_elegible: Decimal
    evaluaciones: list[EvaluacionCertificado]
    fundamento: str


def evaluar_certificado(reg: Registro, cert: Certificado) -> EvaluacionCertificado:
    """Evalúa los siete requisitos del Art. 1 Bis 5."""
    spec = reg.certificados_elegibilidad
    ids_registro = {r.id for r in spec.requisitos}

    if cert.capital_no_retirable_programa_gubernamental:
        return EvaluacionCertificado(
            id_emision=cert.id_emision,
            importe=cert.importe,
            elegible=True,
            exento=True,
            incumplimientos=[],
            fundamento=f"{spec.fundamento}. {spec.exencion.strip()}",
        )

    if cert.importe < CERO:
        raise ValueError(f"Emisión {cert.id_emision}: importe negativo.")

    booleanos = {
        "programa_asamblea": cert.programa_asamblea,
        "plazo_definido": cert.plazo_definido,
        "numerados_mismo_valor": cert.numerados_mismo_valor,
        "terminos_pago": cert.terminos_pago,
        "leyenda_no_deposito": cert.leyenda_no_deposito,
        "leyenda_retiro": cert.leyenda_retiro,
    }
    faltantes = set(booleanos) - ids_registro
    if faltantes:
        raise RequisitoDesconocidoError(
            f"Requisitos evaluados que no existen en el registro: {sorted(faltantes)}"
        )

    incumplimientos: list[str] = []
    por_id = {r.id: r.descripcion for r in spec.requisitos}
    for ident, cumple in booleanos.items():
        if not cumple:
            incumplimientos.append(f"{ident}: {por_id[ident]}")

    factor = reg.parametros.certificados.factor_maximo_ccp
    tope = cert.ccp_a_fecha_emision * factor
    if cert.tasa_rendimiento > tope:
        incumplimientos.append(
            f"tasa_maxima: rendimiento {cert.tasa_rendimiento} excede el tope {tope} "
            f"({reg.parametros.certificados.base_ccp})."
        )

    return EvaluacionCertificado(
        id_emision=cert.id_emision,
        importe=cert.importe,
        elegible=not incumplimientos,
        exento=False,
        incumplimientos=incumplimientos,
        fundamento=spec.fundamento,
    )


def evaluar_certificados(reg: Registro, certificados: list[Certificado]) -> ResumenCertificados:
    """Devuelve el importe no elegible, que alimenta el renglón 7 del Anexo U."""
    evaluaciones = [evaluar_certificado(reg, c) for c in certificados]
    total = sum((e.importe for e in evaluaciones), CERO)
    elegible = sum((e.importe for e in evaluaciones if e.elegible), CERO)
    return ResumenCertificados(
        importe_total=total,
        importe_elegible=elegible,
        importe_no_elegible=total - elegible,
        evaluaciones=evaluaciones,
        fundamento=reg.certificados_elegibilidad.fundamento,
    )
