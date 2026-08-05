"""Capa 2 — Motor de cálculo. Funciones puras, sin I/O, sin estado.

Fundamentos: Disposiciones Arts. 1 Bis 3 a 1 Bis 6; LRASCAP Arts. 13, 15, 16, 26;
formulario de cómputo del Anexo U, apartado II.

Reglas duras de esta capa (verificadas por las compuertas de CI):
  1. Ninguna función hace I/O, lee archivos ni llama datetime.now().
  2. CERO constantes regulatorias. Todo parámetro proviene del registro
     normativo, que se recibe como argumento.
  3. Prohibido dict.get(clave, 0). Insumo ausente = excepción.
  4. Decimal, nunca float.
  5. Todo resultado carga su fundamento legal.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from acr.normativa.esquema import Registro

# Escalar aritmético, no umbral normativo: define qué significa "por ciento".
ESCALA_PORCENTUAL = Decimal(100)
CERO = Decimal(0)


class InsumoFaltanteError(ValueError):
    """Un insumo requerido por la norma no fue provisto. Nunca asumir cero."""


class EstadoInconsistenteError(RuntimeError):
    """El motor alcanzó un estado que la norma no contempla. Nunca degradar."""


def _d(valor: object, nombre: str) -> Decimal:
    if valor is None:
        raise InsumoFaltanteError(
            f"'{nombre}' es requerido. La norma no permite asumir cero: "
            f"un renglón ausente y un renglón en cero son hechos distintos."
        )
    return Decimal(str(valor))


def _pct(valor: Decimal, reg: Registro) -> Decimal:
    decimales = reg.parametros.presentacion.decimales_porcentaje
    return valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


# =============================================================================
# CAPITAL NETO — Art. 1 Bis 4 / renglones 6-9 del Anexo U
# =============================================================================


@dataclass(frozen=True)
class CapitalNeto:
    capital_contable: Decimal
    certificados_no_elegibles: Decimal
    financiamientos_partes_sociales: Decimal
    valor: Decimal
    fundamento: str

    def desglose(self) -> list[tuple[int, str, Decimal]]:
        """Renglones 6 a 9 del formulario del Anexo U, apartado II."""
        return [
            (6, "Capital Contable", self.capital_contable),
            (
                7,
                "Certificados excedentes o voluntarios que no cumplen con características",
                -self.certificados_no_elegibles,
            ),
            (
                8,
                "Financiamiento para adquisición de partes sociales",
                -self.financiamientos_partes_sociales,
            ),
            (9, "Capital neto", self.valor),
        ]


def calcular_capital_neto(
    reg: Registro,
    *,
    capital_contable: object,
    certificados_no_elegibles: object,
    financiamientos_partes_sociales: object,
) -> CapitalNeto:
    """Renglón 9 del Anexo U: (6) - (7) - (8).

    No se restan activos intangibles ni créditos a contraventores: no están
    previstos en el Art. 1 Bis 4 y son conceptos del régimen de niveles I-IV.
    """
    cc = _d(capital_contable, "capital_contable")
    cert = _d(certificados_no_elegibles, "certificados_no_elegibles")
    fin = _d(financiamientos_partes_sociales, "financiamientos_partes_sociales")

    if cert < CERO or fin < CERO:
        raise ValueError("Las deducciones se expresan en valor absoluto positivo.")

    return CapitalNeto(cc, cert, fin, cc - cert - fin, reg.capital_neto.fundamento)


# =============================================================================
# NIVEL DE CAPITALIZACIÓN — Art. 1 Bis 3 / renglones 1-5 y 10 del Anexo U
# =============================================================================


@dataclass(frozen=True)
class Capitalizacion:
    cartera_vigente: Decimal
    cartera_vencida: Decimal
    estimacion_preventiva: Decimal
    cartera_neta: Decimal
    requerimiento: Decimal
    capital_neto: Decimal
    nivel_pct: Decimal | None       # redondeado, para el formulario del Anexo U
    nivel_exacto: Decimal | None    # sin redondear, para determinar la categoría
    sin_requerimiento: bool
    fecha_corte: str
    factor_requerimiento: Decimal
    fundamento: tuple[str, ...]

    def formulario_anexo_u(self, cn: CapitalNeto) -> list[tuple[int, str, Decimal | None]]:
        """Formulario completo de cómputo del Anexo U, renglón por renglón."""
        filas: list[tuple[int, str, Decimal | None]] = [
            (1, "Cartera Vigente", self.cartera_vigente),
            (2, "Cartera Vencida", self.cartera_vencida),
            (3, "Estimación preventiva para riesgos crediticios", self.estimacion_preventiva),
            (4, "Total de cartera de crédito neta", self.cartera_neta),
            (5, "Requerimientos de capitalización", self.requerimiento),
        ]
        filas.extend(cn.desglose())
        filas.append((10, "Nivel de capitalización", self.nivel_pct))
        return filas


def calcular_capitalizacion(
    reg: Registro,
    capital_neto: CapitalNeto,
    *,
    cartera_vigente: object,
    cartera_vencida: object,
    estimacion_preventiva: object,
    fecha_corte: str,
) -> Capitalizacion:
    """Renglones 1 a 5 y 10 del Anexo U.

      (4) = (1) + (2) - (3)
      (5) = (4) * factor de requerimiento
      (10) = [(9) / (5)] * 100

    Caso borde: requerimiento cero. Sin cartera no hay requerimiento que
    incumplir; no es categoría D.
    """
    vig = _d(cartera_vigente, "cartera_vigente")
    ven = _d(cartera_vencida, "cartera_vencida")
    est = _d(estimacion_preventiva, "estimacion_preventiva")

    if vig < CERO or ven < CERO:
        raise ValueError("Los saldos de cartera se expresan en positivo.")
    if est < CERO:
        raise ValueError("La estimación preventiva se expresa en positivo; se resta aquí.")

    cartera_neta = vig + ven - est
    if cartera_neta < CERO:
        raise ValueError(
            f"La estimación preventiva ({est}) excede la cartera total ({vig + ven}). "
            "Revisar signos en el mapeo de la cuenta de estimación preventiva."
        )

    factor = reg.parametros.capitalizacion.factor_requerimiento
    requerimiento = cartera_neta * factor
    sin_req = requerimiento == CERO
    # El redondeo es de PRESENTACIÓN. La categoría se determina sobre el valor
    # exacto: un nivel real de 149.9999% no debe clasificarse como A por
    # redondear a 150.00% en el formulario.
    exacto = None if sin_req else capital_neto.valor / requerimiento * ESCALA_PORCENTUAL
    nivel = None if exacto is None else _pct(exacto, reg)

    return Capitalizacion(
        cartera_vigente=vig,
        cartera_vencida=ven,
        estimacion_preventiva=est,
        cartera_neta=cartera_neta,
        requerimiento=requerimiento,
        capital_neto=capital_neto.valor,
        nivel_pct=nivel,
        nivel_exacto=exacto,
        sin_requerimiento=sin_req,
        fecha_corte=fecha_corte,
        factor_requerimiento=factor,
        fundamento=(
            reg.parametros.capitalizacion.fundamento_factor,
            reg.parametros.capitalizacion.fundamento_computo,
        ),
    )


# =============================================================================
# CLASIFICACIÓN — LRASCAP Art. 15
# =============================================================================


@dataclass(frozen=True)
class Clasificacion:
    categoria: str
    motivo: str
    fundamento: str
    requiere_notificacion_plazo: bool
    plazo_notificacion_dias: int | None
    debe_abstenerse_captacion: bool
    obligaciones_derivadas: list[str] = field(default_factory=list)


def _obligaciones(reg: Registro, categoria: str) -> list[str]:
    n = reg.clasificacion.notificacion_asamblea
    dos_c = reg.clasificacion.hipotesis("DOS_C_CONSECUTIVAS")
    if categoria == "D":
        return [
            f"Abstenerse de operaciones de captación: {reg.clasificacion.umbral('D').riesgo}.",
            "Iniciar disolución y liquidación.",
            f"Notificar a la Asamblea en máximo {n.plazo_dias} días ({n.fundamento}).",
            f"Entregar evidencia de asamblea al CSA en {n.evidencia_al_csa_dias} días.",
        ]
    if categoria == "C":
        return [
            "Adoptar medidas correctivas inmediatas.",
            f"Notificar a la Asamblea en máximo {n.plazo_dias} días ({n.fundamento}).",
            f"ALERTA: {dos_c.descripcion.strip()} ({dos_c.fundamento}).",
        ]
    return [n.regla_general]


def clasificar(
    reg: Registro,
    cap: Capitalizacion,
    *,
    eeff_cumplen_reglas_presentacion: bool,
    eeff_presentados_en_plazo: bool,
    historial_categorias: Sequence[str] = (),
) -> Clasificacion:
    """Art. 15 LRASCAP. Los tres parámetros keyword son obligatorios.

    La clasificación no es función numérica pura: depende también del apego a
    las reglas de presentación de estados financieros y del historial.
    """
    n = reg.clasificacion.notificacion_asamblea
    u_a = reg.clasificacion.umbral("A")
    u_b = reg.clasificacion.umbral("B")
    u_c = reg.clasificacion.umbral("C")
    u_d = reg.clasificacion.umbral("D")

    def _res(categoria: str, motivo: str, fundamento: str) -> Clasificacion:
        con_plazo = categoria in n.categorias_con_plazo
        return Clasificacion(
            categoria=categoria,
            motivo=motivo,
            fundamento=fundamento,
            requiere_notificacion_plazo=con_plazo,
            plazo_notificacion_dias=n.plazo_dias if con_plazo else None,
            debe_abstenerse_captacion=(categoria == "D"),
            obligaciones_derivadas=_obligaciones(reg, categoria),
        )

    if cap.sin_requerimiento:
        categoria = "A" if eeff_cumplen_reglas_presentacion else "C"
        return _res(
            categoria,
            "Sin cartera de crédito neta: el requerimiento de capitalización es cero. "
            "No existe requerimiento que incumplir.",
            f"{cap.fundamento[0]}; {reg.clasificacion.fundamento}",
        )

    nivel = cap.nivel_exacto
    if nivel is None or cap.nivel_pct is None:
        raise EstadoInconsistenteError(
            "nivel_exacto es None sin sin_requerimiento. Revisar calcular_capitalizacion()."
        )
    mostrado = cap.nivel_pct

    historial = list(historial_categorias)
    dos_c = reg.clasificacion.hipotesis("DOS_C_CONSECUTIVAS")
    if historial[-2:] == ["C", "C"]:
        return _res("D", dos_c.descripcion.strip(), dos_c.fundamento)

    umbral_d = u_d.nivel_max
    umbral_b = u_b.nivel_min
    umbral_a = u_a.nivel_min
    if umbral_d is None or umbral_b is None or umbral_a is None:
        raise EstadoInconsistenteError(
            "El registro normativo debe definir nivel_max de D y nivel_min de A y B."
        )

    if nivel < umbral_d:
        h_d = reg.clasificacion.hipotesis("D_REQUIERE_INCUMPLIMIENTO")
        cae_en_d = (not eeff_presentados_en_plazo) or (
            historial[-1:] == ["C"] and not eeff_cumplen_reglas_presentacion
        )
        if cae_en_d:
            return _res(
                "D",
                f"Nivel de Capitalización {mostrado}% (< {umbral_d}%) con incumplimiento "
                "en la presentación de estados financieros básicos.",
                u_d.fundamento,
            )
        return _res(
            "C",
            f"Nivel de Capitalización {mostrado}% (< {umbral_d}%). {h_d.descripcion.strip()} "
            "Sujeto a determinación del Comité de Supervisión Auxiliar.",
            f"{u_c.fundamento}; {h_d.fundamento}",
        )

    if not eeff_cumplen_reglas_presentacion:
        h_c = reg.clasificacion.hipotesis("C_POR_PRESENTACION")
        return _res(
            "C",
            f"Nivel de Capitalización {mostrado}% (>= {umbral_d}%) pero la información "
            "financiera no se apega a las reglas de elaboración y presentación.",
            h_c.fundamento,
        )

    if nivel < umbral_b:
        return _res(
            "C",
            f"Nivel de Capitalización {mostrado}% (>= {umbral_d}% y < {umbral_b}%).",
            u_c.fundamento,
        )
    if nivel < umbral_a:
        return _res(
            "B",
            f"Nivel de Capitalización {mostrado}% (>= {umbral_b}% y < {umbral_a}%).",
            u_b.fundamento,
        )
    return _res("A", f"Nivel de Capitalización {mostrado}% (>= {umbral_a}%).", u_a.fundamento)


# =============================================================================
# LÍMITE DE ACTIVOS — LRASCAP Arts. 13 y 16
# =============================================================================


@dataclass(frozen=True)
class LimiteActivos:
    activos_totales: Decimal
    valor_udi: Decimal
    activos_en_udis: Decimal
    limite_udis: Decimal
    excede: bool
    holgura_pct: Decimal
    plazo_solicitud_dias: int
    fundamento: tuple[str, ...]


def evaluar_limite_activos(
    reg: Registro,
    *,
    activos_totales: object,
    valor_udi_a_fecha_corte: object,
) -> LimiteActivos:
    """Art. 13 y disparador del Art. 16."""
    p = reg.parametros.limite_activos
    act = _d(activos_totales, "activos_totales")
    udi = _d(valor_udi_a_fecha_corte, "valor_udi_a_fecha_corte")
    if udi <= CERO:
        raise ValueError("El valor de la UDI debe ser positivo (fuente: Banco de México).")

    en_udis = act / udi
    return LimiteActivos(
        activos_totales=act,
        valor_udi=udi,
        activos_en_udis=_pct(en_udis, reg),
        limite_udis=p.valor_udis,
        excede=en_udis > p.valor_udis,
        holgura_pct=_pct((p.valor_udis - en_udis) / p.valor_udis * ESCALA_PORCENTUAL, reg),
        plazo_solicitud_dias=p.plazo_solicitud_dias,
        fundamento=(p.fundamento, p.fundamento_plazo),
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
    quorum_aprobacion: str
    fundamento: str


def evaluar_personas_relacionadas(
    reg: Registro,
    *,
    montos_dispuestos: object,
    lineas_de_credito_irrevocables: object,
    capital_contable: object,
    capital_social_pagado: object,
    valor_udi_a_fecha_corte: object,
) -> PersonasRelacionadas:
    """Art. 26 LRASCAP. Aplica a Nivel Básico (disposiciones comunes).

    Base: montos dispuestos + líneas irrevocables contratadas.
    Límite sobre capital contable. Umbral de exención: el menor entre el monto
    en UDIS y el factor sobre capital social pagado.
    """
    p = reg.parametros.personas_relacionadas
    disp = _d(montos_dispuestos, "montos_dispuestos")
    lin = _d(lineas_de_credito_irrevocables, "lineas_de_credito_irrevocables")
    cc = _d(capital_contable, "capital_contable")
    csp = _d(capital_social_pagado, "capital_social_pagado")
    udi = _d(valor_udi_a_fecha_corte, "valor_udi_a_fecha_corte")

    total = disp + lin
    # El cumplimiento se determina sobre el valor exacto; el redondeo es de
    # presentación. 100,001 sobre 1,000,000 excede el 10% aunque redondee a 10.00.
    exacto = None if cc <= CERO else total / cc * ESCALA_PORCENTUAL
    pct = None if exacto is None else _pct(exacto, reg)
    umbral = min(
        p.umbral_exencion_udis * udi,
        csp * p.umbral_exencion_factor_capital_social,
    )

    return PersonasRelacionadas(
        montos_dispuestos=disp,
        lineas_irrevocables=lin,
        exposicion_total=total,
        capital_contable=cc,
        porcentaje=pct,
        limite_pct=p.limite_pct_capital_contable,
        cumple=(exacto is not None and exacto <= p.limite_pct_capital_contable),
        umbral_exencion=umbral,
        quorum_aprobacion=p.quorum_aprobacion,
        fundamento=p.fundamento,
    )
