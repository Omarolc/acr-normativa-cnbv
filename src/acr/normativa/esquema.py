"""Esquema del registro normativo. Valida que la norma-como-dato esté completa.

Un registro mal formado es peor que uno ausente: se carga en silencio y produce
cómputos con parámetros parciales. Por eso todo campo que el motor consume es
obligatorio y sin default.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class Meta(_Base):
    """Distingue vigencia normativa de fuente documental.

    `vigencia_desde/hasta` acota las fechas de CORTE que estos parámetros rigen.
    `compilado_fuente` es la fecha del texto contra el que se verificaron.
    Confundirlos hace que el sistema rechace cortes válidos o, peor, acepte
    cortes regidos por una norma distinta.
    """

    version_registro: str
    vigencia_desde: date
    vigencia_hasta: date
    compilado_fuente: date
    fecha_corte_conocimiento: date
    nota_vigencia: str


class AlertaVigencia(_Base):
    id: str
    fecha_entrada_vigor: date
    bloqueante: bool
    descripcion: str


class ParamPresentacion(_Base):
    unidad: str
    fundamento: str
    decimales_porcentaje: int


class ParamCapitalizacion(_Base):
    factor_requerimiento: Decimal
    fundamento_factor: str
    periodicidad_computo: str
    meses_corte: list[int]
    meses_entrega: list[int]
    base_saldos: str
    fundamento_computo: str


class ParamLimiteActivos(_Base):
    valor_udis: Decimal
    fundamento: str
    plazo_solicitud_dias: int
    fundamento_plazo: str


class ParamPersonasRelacionadas(_Base):
    limite_pct_capital_contable: Decimal
    base_calculo: str
    umbral_exencion_udis: Decimal
    umbral_exencion_factor_capital_social: Decimal
    regla_umbral: str
    quorum_aprobacion: str
    fundamento: str


class ParamCertificados(_Base):
    factor_maximo_ccp: Decimal
    base_ccp: str
    fundamento: str


class Parametros(_Base):
    presentacion: ParamPresentacion
    capitalizacion: ParamCapitalizacion
    limite_activos: ParamLimiteActivos
    personas_relacionadas: ParamPersonasRelacionadas
    certificados: ParamCertificados


class ComponenteCapitalNeto(_Base):
    id: str
    signo: str
    renglon_anexo_u: int
    etiqueta: str
    fundamento: str


class CapitalNetoSpec(_Base):
    fundamento: str
    formula: str
    componentes: list[ComponenteCapitalNeto]


class UmbralCategoria(_Base):
    categoria: str
    nivel_min: Decimal | None
    nivel_max: Decimal | None
    fundamento: str
    riesgo: str


class HipotesisAdicional(_Base):
    id: str
    resultado: str
    fundamento: str
    descripcion: str


class NotificacionAsamblea(_Base):
    fundamento: str
    regla_general: str
    categorias_con_plazo: list[str]
    plazo_dias: int
    evidencia_al_csa_dias: int


class ClasificacionSpec(_Base):
    fundamento: str
    evaluador: str
    periodicidad_evaluacion: str
    cifras_base: list[int]
    umbrales: list[UmbralCategoria]
    hipotesis_adicionales: list[HipotesisAdicional]
    notificacion_asamblea: NotificacionAsamblea

    def umbral(self, categoria: str) -> UmbralCategoria:
        for u in self.umbrales:
            if u.categoria == categoria:
                return u
        raise KeyError(f"Categoría '{categoria}' no definida en el registro normativo.")

    def hipotesis(self, ident: str) -> HipotesisAdicional:
        for h in self.hipotesis_adicionales:
            if h.id == ident:
                return h
        raise KeyError(f"Hipótesis '{ident}' no definida en el registro normativo.")


class EstratoMora(_Base):
    dias_min: int
    dias_max: int | None
    porcentaje: Decimal


class EstimacionesSpec(_Base):
    fundamento: str
    periodicidad: str
    base_cifras: str
    base_dias_mora: str
    base_importe: str
    exclusion: str
    estratos: list[EstratoMora] = Field(min_length=1)

    @field_validator("estratos")
    @classmethod
    def _contiguos_y_ordenados(cls, v: list[EstratoMora]) -> list[EstratoMora]:
        """La tabla debe cubrir todos los días sin huecos ni traslapes.

        Un hueco significa un crédito sin porcentaje aplicable, que en la práctica
        se convierte en estimación cero — exactamente el defecto que se corrige.
        """
        esperado = 0
        for i, e in enumerate(v):
            if e.dias_min != esperado:
                raise ValueError(
                    f"Estrato {i}: dias_min={e.dias_min}, se esperaba {esperado}. "
                    "La tabla de mora debe ser contigua desde 0."
                )
            if e.dias_max is None:
                if i != len(v) - 1:
                    raise ValueError("Solo el último estrato puede tener dias_max abierto.")
                return v
            if e.dias_max < e.dias_min:
                raise ValueError(f"Estrato {i}: dias_max menor que dias_min.")
            esperado = e.dias_max + 1
        raise ValueError("El último estrato debe tener dias_max nulo (abierto).")


class SupuestoVencida(_Base):
    id: str
    descripcion: str
    dias_vencido_principal: int | None
    dias_vencido_intereses: int | None
    amortizaciones_vencidas: int | None
    periodos_facturacion_vencidos: int | None
    fundamento: str


class CarteraVencidaSpec(_Base):
    fundamento: str
    regla_general: str
    supuestos: list[SupuestoVencida]

    def supuesto(self, ident: str) -> SupuestoVencida:
        for s in self.supuestos:
            if s.id == ident:
                return s
        raise KeyError(
            f"Esquema de pagos '{ident}' no previsto en el Anexo T, párrafo 57. "
            f"Válidos: {[s.id for s in self.supuestos]}"
        )


class PagoSostenidoSpec(_Base):
    fundamento: str
    definicion: str
    amortizaciones_consecutivas: int
    umbral_dias_periodo_largo: int
    exhibiciones_si_periodo_largo: int
    excluye_pago_anticipado: bool


class RequisitoCertificado(_Base):
    id: str
    descripcion: str


class CertificadosSpec(_Base):
    fundamento: str
    exencion: str
    requisitos: list[RequisitoCertificado]


class Obligacion(_Base):
    id: str
    fundamento: str
    destinatario: str
    meses_corte: list[int]
    meses_entrega: list[int]
    medio: str


class Registro(_Base):
    """Registro normativo completo, validado."""

    meta: Meta
    alertas_vigencia: list[AlertaVigencia]
    parametros: Parametros
    capital_neto: CapitalNetoSpec
    clasificacion: ClasificacionSpec
    estimaciones_preventivas: EstimacionesSpec
    cartera_vencida: CarteraVencidaSpec
    pago_sostenido: PagoSostenidoSpec
    certificados_elegibilidad: CertificadosSpec
    obligaciones_de_entrega: list[Obligacion]
