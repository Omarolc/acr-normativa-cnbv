"""Capa 2 — Motor de cartera: mora, traspaso a vencida y estimaciones preventivas.

Fundamentos:
  - Anexo C Bis: calificación y constitución de estimaciones preventivas.
  - Anexo T, párrafo 57: supuestos de traspaso a cartera vencida.
  - Anexo T, párrafos 48 a 50: pago sostenido.

EL DEFECTO QUE ESTE MÓDULO CORRIGE
----------------------------------
La implementación original medía la mora contra el VENCIMIENTO FINAL del crédito:

    dias_mora = hoy - (fecha_otorgamiento + plazo)

Con ese cálculo, un crédito a 36 meses sin un solo pago reporta cero días de mora
durante tres años. El Anexo C Bis dice lo contrario: los días se cuentan
"a partir del día de la primera amortización del crédito que no haya sido cubierta
por el acreditado a la fecha de la calificación".

El error es de un solo sentido: siempre subestima las estimaciones, siempre infla
el capital neto y siempre mejora la categoría. Por eso `dias_mora()` exige la
fecha de la primera amortización no cubierta y no acepta el plazo del crédito.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from acr.normativa.esquema import Registro

CERO = Decimal(0)
ESCALA_PORCENTUAL = Decimal(100)


class InsumoCarteraFaltanteError(ValueError):
    """Un crédito no trae los insumos que la norma exige para calificarlo."""


class EsquemaPagosNoPrevistoError(ValueError):
    """El esquema de pagos no corresponde a ninguno de los supuestos del Anexo T."""


# =============================================================================
# CONTRATO DE ENTRADA
# =============================================================================


@dataclass(frozen=True)
class Credito:
    """Insumos mínimos para calificar un crédito.

    El esquema anterior (`monto, fecha_otorgamiento, plazo, tasa`) es
    matemáticamente insuficiente: no permite saber qué amortización venció ni
    cuándo. Los campos de abajo son los que la norma realmente requiere.
    """

    id_credito: str
    esquema_pagos: str  # debe coincidir con un supuesto del Anexo T, párrafo 57
    saldo_insoluto: Decimal
    intereses_devengados: Decimal
    fecha_primera_amortizacion_no_cubierta: date | None
    amortizaciones_vencidas: int
    dias_vencido_intereses: int
    periodos_facturacion_vencidos: int
    reestructurado: bool = False
    tiene_pago_sostenido: bool = False
    intereses_devengados_no_cobrados_en_balance: Decimal = CERO


@dataclass(frozen=True)
class CreditoCalificado:
    id_credito: str
    dias_mora: int
    es_vencida: bool
    supuesto_vencida: str | None
    base_calificacion: Decimal
    porcentaje: Decimal
    estimacion: Decimal
    fundamento: str


@dataclass(frozen=True)
class ResumenCartera:
    cartera_vigente: Decimal
    cartera_vencida: Decimal
    cartera_total: Decimal
    estimacion_preventiva: Decimal
    creditos: list[CreditoCalificado]
    fecha_calificacion: str
    fundamento: str

    def pct_estimacion(self) -> Decimal:
        if self.cartera_total == CERO:
            return CERO
        bruto = self.estimacion_preventiva / self.cartera_total * ESCALA_PORCENTUAL
        return bruto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# DÍAS DE MORA — Anexo C Bis
# =============================================================================


def dias_mora(credito: Credito, fecha_calificacion: date) -> int:
    """Días transcurridos desde la primera amortización no cubierta.

    NO se mide contra el vencimiento final del crédito. Ese era el defecto
    original y produce cero mora en créditos que llevan años sin pagar.
    """
    fecha = credito.fecha_primera_amortizacion_no_cubierta
    if fecha is None:
        return 0
    if fecha > fecha_calificacion:
        raise InsumoCarteraFaltanteError(
            f"Crédito {credito.id_credito}: la primera amortización no cubierta "
            f"({fecha.isoformat()}) es posterior a la fecha de calificación "
            f"({fecha_calificacion.isoformat()})."
        )
    return (fecha_calificacion - fecha).days


# =============================================================================
# TRASPASO A CARTERA VENCIDA — Anexo T, párrafo 57
# =============================================================================


def es_cartera_vencida(
    reg: Registro, credito: Credito, fecha_calificacion: date
) -> tuple[bool, str | None]:
    """Evalúa el supuesto del párrafo 57 que corresponde al esquema de pagos."""
    try:
        supuesto = reg.cartera_vencida.supuesto(credito.esquema_pagos)
    except KeyError as exc:
        raise EsquemaPagosNoPrevistoError(str(exc)) from exc

    d = dias_mora(credito, fecha_calificacion)

    if supuesto.dias_vencido_principal is not None and d >= supuesto.dias_vencido_principal:
        return True, supuesto.fundamento
    if (
        supuesto.dias_vencido_intereses is not None
        and credito.dias_vencido_intereses >= supuesto.dias_vencido_intereses
    ):
        return True, supuesto.fundamento
    if (
        supuesto.amortizaciones_vencidas is not None
        and credito.amortizaciones_vencidas >= supuesto.amortizaciones_vencidas
    ):
        return True, supuesto.fundamento
    if (
        supuesto.periodos_facturacion_vencidos is not None
        and credito.periodos_facturacion_vencidos >= supuesto.periodos_facturacion_vencidos
    ):
        return True, supuesto.fundamento

    # Párrafo 59: pago único reestructurado se considera vencido en cualquier momento.
    if credito.reestructurado and supuesto.id.startswith("PAGO_UNICO"):
        return True, "Anexo T, párrafo 59"

    # Párrafo 58: vencido reestructurado permanece vencido sin pago sostenido.
    if credito.reestructurado and not credito.tiene_pago_sostenido and d > 0:
        return True, "Anexo T, párrafo 58"

    return False, None


# =============================================================================
# ESTIMACIONES PREVENTIVAS — Anexo C Bis
# =============================================================================


def porcentaje_estimacion(reg: Registro, dias: int) -> tuple[Decimal, str]:
    """Porcentaje del estrato correspondiente. La tabla no tiene huecos: el
    esquema valida contigüidad desde cero, así que todo crédito cae en un estrato.
    """
    if dias < 0:
        raise ValueError("Los días de mora no pueden ser negativos.")
    for estrato in reg.estimaciones_preventivas.estratos:
        if dias >= estrato.dias_min and (estrato.dias_max is None or dias <= estrato.dias_max):
            return estrato.porcentaje, reg.estimaciones_preventivas.fundamento
    raise ValueError(  # pragma: no cover - imposible por validación de esquema
        f"Sin estrato aplicable para {dias} días de mora."
    )


def calificar_credito(
    reg: Registro, credito: Credito, fecha_calificacion: date
) -> CreditoCalificado:
    """Califica un crédito y determina su estimación preventiva.

    Base de cálculo: importe total incluyendo los intereses que genera, menos
    los intereses devengados no cobrados registrados en balance cuando el
    crédito está en cartera vencida (exclusión expresa del Anexo C Bis).
    """
    d = dias_mora(credito, fecha_calificacion)
    vencida, fundamento_vencida = es_cartera_vencida(reg, credito, fecha_calificacion)

    base = credito.saldo_insoluto + credito.intereses_devengados
    if vencida:
        base -= credito.intereses_devengados_no_cobrados_en_balance
    if base < CERO:
        raise InsumoCarteraFaltanteError(
            f"Crédito {credito.id_credito}: base de calificación negativa. "
            "Los intereses devengados no cobrados exceden el importe del crédito."
        )

    pct, fundamento = porcentaje_estimacion(reg, d)
    estimacion = (base * pct / ESCALA_PORCENTUAL).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return CreditoCalificado(
        id_credito=credito.id_credito,
        dias_mora=d,
        es_vencida=vencida,
        supuesto_vencida=fundamento_vencida,
        base_calificacion=base,
        porcentaje=pct,
        estimacion=estimacion,
        fundamento=fundamento,
    )


def calificar_cartera(
    reg: Registro, creditos: list[Credito], fecha_calificacion: date
) -> ResumenCartera:
    """Califica la cartera completa y produce los renglones 1, 2 y 3 del Anexo U."""
    if not creditos:
        return ResumenCartera(
            cartera_vigente=CERO,
            cartera_vencida=CERO,
            cartera_total=CERO,
            estimacion_preventiva=CERO,
            creditos=[],
            fecha_calificacion=fecha_calificacion.isoformat(),
            fundamento=reg.estimaciones_preventivas.fundamento,
        )

    ids = [c.id_credito for c in creditos]
    if len(set(ids)) != len(ids):
        raise InsumoCarteraFaltanteError("Hay identificadores de crédito duplicados.")

    calificados = [calificar_credito(reg, c, fecha_calificacion) for c in creditos]
    por_id = {c.id_credito: c for c in creditos}

    vigente = sum(
        (por_id[k.id_credito].saldo_insoluto for k in calificados if not k.es_vencida),
        CERO,
    )
    vencida = sum(
        (por_id[k.id_credito].saldo_insoluto for k in calificados if k.es_vencida),
        CERO,
    )
    estimacion = sum((k.estimacion for k in calificados), CERO)

    return ResumenCartera(
        cartera_vigente=vigente,
        cartera_vencida=vencida,
        cartera_total=vigente + vencida,
        estimacion_preventiva=estimacion,
        creditos=calificados,
        fecha_calificacion=fecha_calificacion.isoformat(),
        fundamento=reg.estimaciones_preventivas.fundamento,
    )
