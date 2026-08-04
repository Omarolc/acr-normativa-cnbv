"""Capa 2 — Motor de calculo. Funciones puras, sin I/O, sin estado.

Fundamentos: Disposiciones Arts. 1 Bis 2 a 1 Bis 6; LRASCAP Arts. 13, 15, 16, 26.

Reglas duras de esta capa (verificadas por las compuertas de CI):
  1. Ninguna funcion hace I/O, lee archivos ni llama datetime.now().
     Todo lo temporal entra como parametro -> resultado reproducible.
  2. Prohibido dict.get(clave, 0) sobre insumos regulatorios.
     Insumo ausente = excepcion. Un cero silencioso se firma y se entrega.
  3. Decimal, nunca float.
  4. Todo resultado carga su fundamento legal.

DEUDA CONOCIDA (ACR-01): este modulo aun declara constantes normativas en
codigo. Esta registrado en tools/deuda_literales.txt con vencimiento en ACR-02,
sprint en el que pasan al registro YAML. La compuerta D falla si aparecen
literales en cualquier archivo fuera de esa lista.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CERO = Decimal("0")
FACTOR_REQUERIMIENTO = Decimal("0.08")      # Disposiciones Art. 1 Bis 3
LIMITE_ACTIVOS_UDIS = Decimal("2500000")    # LRASCAP Art. 13
PLAZO_SOLICITUD_DIAS = 150                  # LRASCAP Art. 16
UMBRAL_UDIS_RELACIONADAS = Decimal("100000")  # LRASCAP Art. 26


class InsumoFaltanteError(ValueError):
    """Un insumo requerido por la norma no fue provisto. Nunca asumir cero."""


class EstadoInconsistenteError(RuntimeError):
    """El motor alcanzo un estado que la norma no contempla. Nunca degradar."""


def _d(valor: object, nombre: str) -> Decimal:
    """Convierte a Decimal fallando ruidosamente si el insumo esta ausente."""
    if valor is None:
        raise InsumoFaltanteError(
            f"'{nombre}' es requerido. La norma no permite asumir cero: "
            f"un renglon ausente y un renglon en cero son hechos distintos."
        )
    return Decimal(str(valor))


def _pct(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# CAPITAL NETO — Disposiciones Art. 1 Bis 4
# =============================================================================


@dataclass(frozen=True)
class CapitalNeto:
    capital_contable: Decimal
    certificados_no_elegibles: Decimal
    financiamientos_para_partes_sociales: Decimal
    valor: Decimal
    fundamento: str = "Disposiciones Art. 1 Bis 4"

    def desglose(self) -> list[tuple[str, Decimal, str]]:
        return [
            ("Capital contable", self.capital_contable, "Art. 1 Bis 4, fracc. I"),
            (
                "(-) Certificados excedentes/voluntarios no elegibles",
                -self.certificados_no_elegibles,
                "Art. 1 Bis 4, fracc. II (remite a 1 Bis 5)",
            ),
            (
                "(-) Financiamientos destinados a adquirir partes sociales propias",
                -self.financiamientos_para_partes_sociales,
                "Art. 1 Bis 4, fracc. III",
            ),
            ("= Capital neto", self.valor, "Art. 1 Bis 4"),
        ]


def calcular_capital_neto(
    capital_contable: object,
    certificados_no_elegibles: object,
    financiamientos_para_partes_sociales: object,
) -> CapitalNeto:
    """Art. 1 Bis 4. SOLO estos tres componentes.

    NO se restan activos intangibles ni creditos a contraventores: son
    conceptos del regimen de niveles I-IV, no de Nivel Basico.
    """
    cc = _d(capital_contable, "capital_contable")
    cert = _d(certificados_no_elegibles, "certificados_no_elegibles")
    fin = _d(financiamientos_para_partes_sociales, "financiamientos_para_partes_sociales")

    if cert < CERO or fin < CERO:
        raise ValueError("Las deducciones se expresan en valor absoluto positivo.")

    return CapitalNeto(cc, cert, fin, cc - cert - fin)


# =============================================================================
# NIVEL DE CAPITALIZACION — Disposiciones Arts. 1 Bis 3 y 1 Bis 6
# =============================================================================


@dataclass(frozen=True)
class Capitalizacion:
    capital_neto: Decimal
    cartera_bruta: Decimal
    provisiones: Decimal
    cartera_neta: Decimal
    requerimiento: Decimal
    nivel_pct: Decimal | None
    sin_requerimiento: bool
    fecha_corte: str
    fundamento: tuple[str, ...] = ("Disposiciones Art. 1 Bis 3", "Art. 1 Bis 6")


def calcular_capitalizacion(
    capital_neto: CapitalNeto,
    cartera_bruta: object,
    provisiones: object,
    fecha_corte: str,
) -> Capitalizacion:
    """Requerimiento = 8% de la cartera neta de provisiones (Art. 1 Bis 3).

    Caso borde: requerimiento == 0 (sociedad sin cartera). Sin cartera no hay
    requerimiento que incumplir; NO es categoria D.
    """
    cb = _d(cartera_bruta, "cartera_bruta")
    pr = _d(provisiones, "provisiones")
    if pr < CERO:
        raise ValueError("Las provisiones se expresan en positivo; se restan aqui.")

    cartera_neta = cb - pr
    if cartera_neta < CERO:
        raise ValueError(
            f"Provisiones ({pr}) exceden la cartera bruta ({cb}). "
            "Revisar signos en el mapeo de la cuenta de estimacion preventiva."
        )

    requerimiento = cartera_neta * FACTOR_REQUERIMIENTO
    sin_req = requerimiento == CERO
    nivel = None if sin_req else _pct(capital_neto.valor / requerimiento * Decimal("100"))

    return Capitalizacion(
        capital_neto=capital_neto.valor,
        cartera_bruta=cb,
        provisiones=pr,
        cartera_neta=cartera_neta,
        requerimiento=requerimiento,
        nivel_pct=nivel,
        sin_requerimiento=sin_req,
        fecha_corte=fecha_corte,
    )


# =============================================================================
# CLASIFICACION — LRASCAP Art. 15
# =============================================================================


@dataclass(frozen=True)
class Clasificacion:
    categoria: str
    motivo: str
    fundamento: str
    requiere_notificacion_30_dias: bool
    debe_abstenerse_captacion: bool
    obligaciones_derivadas: list[str] = field(default_factory=list)


def clasificar(
    cap: Capitalizacion,
    *,
    eeff_cumplen_reglas_presentacion: bool,
    eeff_presentados_en_plazo: bool,
    historial_categorias: Sequence[str] = (),
) -> Clasificacion:
    """Art. 15 LRASCAP.

    Los tres parametros keyword son OBLIGATORIOS y sin default a proposito:
    la categoria no se puede determinar sin ellos. La clasificacion NO es
    funcion numerica pura.
    """
    if cap.sin_requerimiento:
        return Clasificacion(
            categoria="A" if eeff_cumplen_reglas_presentacion else "C",
            motivo=(
                "Sin cartera de credito neta: requerimiento de capitalizacion = 0. "
                "No existe requerimiento que incumplir."
            ),
            fundamento="Disposiciones Art. 1 Bis 3; LRASCAP Art. 15",
            requiere_notificacion_30_dias=not eeff_cumplen_reglas_presentacion,
            debe_abstenerse_captacion=False,
        )

    nivel = cap.nivel_pct
    if nivel is None:
        raise EstadoInconsistenteError(
            "nivel_pct es None sin sin_requerimiento. Estado imposible: "
            "revisar calcular_capitalizacion()."
        )

    historial = list(historial_categorias)

    # Art. 15, fracc. III: dos clasificaciones consecutivas en C -> D
    if historial[-2:] == ["C", "C"]:
        return Clasificacion(
            categoria="D",
            motivo="Dos clasificaciones consecutivas en categoria C.",
            fundamento="LRASCAP Art. 15, fracc. III",
            requiere_notificacion_30_dias=True,
            debe_abstenerse_captacion=True,
            obligaciones_derivadas=[
                "Abstenerse de operaciones de captacion desde el dia siguiente a que "
                "surta efectos la notificacion (Art. 15, fracc. IV y Art. 15 Bis).",
                "Iniciar disolucion y liquidacion (Art. 15, fracc. I, inciso d).",
                "Notificar a la Asamblea en maximo 30 dias (Art. 15, fracc. II).",
            ],
        )

    if nivel < Decimal("50"):
        cae_en_d = (not eeff_presentados_en_plazo) or (
            historial[-1:] == ["C"] and not eeff_cumplen_reglas_presentacion
        )
        if cae_en_d:
            return Clasificacion(
                categoria="D",
                motivo=(
                    f"Nivel de Capitalizacion {nivel}% (< 50%) con incumplimiento en la "
                    "presentacion de estados financieros basicos."
                ),
                fundamento="LRASCAP Art. 15, fracc. I, inciso d)",
                requiere_notificacion_30_dias=True,
                debe_abstenerse_captacion=True,
                obligaciones_derivadas=[
                    "Abstenerse de operaciones de captacion (Art. 15, fracc. IV).",
                    "Iniciar disolucion y liquidacion.",
                    "Notificar a la Asamblea en maximo 30 dias (Art. 15, fracc. II).",
                ],
            )
        return Clasificacion(
            categoria="C",
            motivo=(
                f"Nivel de Capitalizacion {nivel}% (< 50%). No se actualizan los supuestos "
                "de presentacion del inciso d), por lo que no procede D por esa via. "
                "Sujeto a determinacion del Comite de Supervision Auxiliar."
            ),
            fundamento="LRASCAP Art. 15, fracc. I, incisos c) y d)",
            requiere_notificacion_30_dias=True,
            debe_abstenerse_captacion=False,
            obligaciones_derivadas=[
                "Adoptar medidas correctivas inmediatas.",
                "Notificar a la Asamblea en maximo 30 dias (Art. 15, fracc. II).",
                "ALERTA: una segunda C consecutiva deriva en categoria D (Art. 15, fracc. III).",
            ],
        )

    if not eeff_cumplen_reglas_presentacion:
        return Clasificacion(
            categoria="C",
            motivo=(
                f"Nivel de Capitalizacion {nivel}% (>= 50%) pero la informacion financiera "
                "no se apega a las reglas de elaboracion y presentacion."
            ),
            fundamento="LRASCAP Art. 15, fracc. I, inciso c), segunda hipotesis",
            requiere_notificacion_30_dias=True,
            debe_abstenerse_captacion=False,
            obligaciones_derivadas=[
                "Corregir la elaboracion y presentacion de los estados financieros basicos.",
                "Notificar a la Asamblea en maximo 30 dias.",
                "ALERTA: una segunda C consecutiva deriva en categoria D.",
            ],
        )

    if nivel < Decimal("100"):
        return Clasificacion(
            categoria="C",
            motivo=f"Nivel de Capitalizacion {nivel}% (>= 50% y < 100%).",
            fundamento="LRASCAP Art. 15, fracc. I, inciso c)",
            requiere_notificacion_30_dias=True,
            debe_abstenerse_captacion=False,
            obligaciones_derivadas=[
                "Adoptar medidas correctivas inmediatas.",
                "Notificar a la Asamblea en maximo 30 dias.",
                "ALERTA: una segunda C consecutiva deriva en categoria D.",
            ],
        )

    if nivel < Decimal("150"):
        return Clasificacion(
            categoria="B",
            motivo=f"Nivel de Capitalizacion {nivel}% (>= 100% y < 150%).",
            fundamento="LRASCAP Art. 15, fracc. I, inciso b)",
            requiere_notificacion_30_dias=False,
            debe_abstenerse_captacion=False,
            obligaciones_derivadas=[
                "Notificar la clasificacion en la asamblea inmediata siguiente."
            ],
        )

    return Clasificacion(
        categoria="A",
        motivo=f"Nivel de Capitalizacion {nivel}% (>= 150%).",
        fundamento="LRASCAP Art. 15, fracc. I, inciso a)",
        requiere_notificacion_30_dias=False,
        debe_abstenerse_captacion=False,
        obligaciones_derivadas=["Notificar la clasificacion en la asamblea inmediata siguiente."],
    )


# =============================================================================
# LIMITE DE ACTIVOS — LRASCAP Arts. 13 y 16
# =============================================================================


@dataclass(frozen=True)
class LimiteActivos:
    activos_totales: Decimal
    valor_udi: Decimal
    activos_en_udis: Decimal
    limite_udis: Decimal
    excede: bool
    holgura_pct: Decimal
    plazo_solicitud_dias: int = PLAZO_SOLICITUD_DIAS
    fundamento: tuple[str, ...] = ("LRASCAP Art. 13", "LRASCAP Art. 16")


def evaluar_limite_activos(
    activos_totales: object,
    valor_udi_a_fecha_corte: object,
) -> LimiteActivos:
    """Art. 13: Nivel Basico opera bajo 2'500,000 UDIS de activos totales.

    Art. 16: al rebasarlo hay 150 dias para presentar solicitud de autorizacion
    ante el Comite de Supervision Auxiliar.
    """
    act = _d(activos_totales, "activos_totales")
    udi = _d(valor_udi_a_fecha_corte, "valor_udi_a_fecha_corte")
    if udi <= CERO:
        raise ValueError("El valor de la UDI debe ser positivo (fuente: Banco de Mexico).")

    en_udis = act / udi
    return LimiteActivos(
        activos_totales=act,
        valor_udi=udi,
        activos_en_udis=_pct(en_udis),
        limite_udis=LIMITE_ACTIVOS_UDIS,
        excede=en_udis > LIMITE_ACTIVOS_UDIS,
        holgura_pct=_pct((LIMITE_ACTIVOS_UDIS - en_udis) / LIMITE_ACTIVOS_UDIS * Decimal("100")),
    )


# =============================================================================
# PERSONAS RELACIONADAS — LRASCAP Art. 26
# =============================================================================


@dataclass(frozen=True)
class PersonasRelacionadas:
    montos_dispuestos: Decimal
    lineas_irrevocables: Decimal
    exposicion_total: Decimal
    capital_contable: Decimal
    porcentaje: Decimal | None
    limite_pct: Decimal
    cumple: bool
    umbral_exencion: Decimal
    fundamento: str = "LRASCAP Art. 26"


def evaluar_personas_relacionadas(
    montos_dispuestos: object,
    lineas_de_credito_irrevocables: object,
    capital_contable: object,
    capital_social_pagado: object,
    valor_udi_a_fecha_corte: object,
) -> PersonasRelacionadas:
    """Art. 26 LRASCAP. Aplica a Nivel Basico (Titulo II, Cap. III, Seccion Tercera,
    "De las disposiciones comunes").

    Base del limite: montos DISPUESTOS + LINEAS IRREVOCABLES CONTRATADAS.
    Limite: 10% del CAPITAL CONTABLE (no neto, no social).
    Umbral de exencion de aprobacion del Consejo: el MENOR entre 100,000 UDIS
    y 2% del capital social pagado.
    """
    disp = _d(montos_dispuestos, "montos_dispuestos")
    lin = _d(lineas_de_credito_irrevocables, "lineas_de_credito_irrevocables")
    cc = _d(capital_contable, "capital_contable")
    csp = _d(capital_social_pagado, "capital_social_pagado")
    udi = _d(valor_udi_a_fecha_corte, "valor_udi_a_fecha_corte")

    total = disp + lin
    pct = None if cc <= CERO else _pct(total / cc * Decimal("100"))
    umbral = min(UMBRAL_UDIS_RELACIONADAS * udi, csp * Decimal("0.02"))

    return PersonasRelacionadas(
        montos_dispuestos=disp,
        lineas_irrevocables=lin,
        exposicion_total=total,
        capital_contable=cc,
        porcentaje=pct,
        limite_pct=Decimal("10"),
        cumple=(pct is not None and pct <= Decimal("10")),
        umbral_exencion=umbral,
    )
