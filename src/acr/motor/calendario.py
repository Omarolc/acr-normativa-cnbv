"""Calendario de obligaciones — función pura derivada del registro normativo.

No hay fechas cableadas: los meses de corte y de entrega vienen del YAML. Si
la norma cambia la periodicidad, cambia el dato y el calendario se recalcula.

CORRECCIÓN RESPECTO DEL PLAN ORIGINAL
-------------------------------------
El plan asumía cuatro eventos anuales. Al incorporar el Anexo C Bis quedó claro
que son DOCE calificaciones mensuales de cartera más cuatro cómputos
trimestrales de capitalización más dos entregas semestrales impresas. Una
cooperativa que solo atienda los trimestres incumple el Anexo C Bis once veces
al año sin darse cuenta.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from acr.normativa.esquema import Registro


@dataclass(frozen=True)
class EventoObligacion:
    id_obligacion: str
    fecha_corte: date
    fecha_limite: date
    destinatario: str
    medio: str
    fundamento: str
    dias_restantes: int | None = None

    def vencido(self, hoy: date) -> bool:
        return hoy > self.fecha_limite


def _ultimo_dia(anio: int, mes: int) -> date:
    return date(anio, mes, monthrange(anio, mes)[1])


def _mes_de_entrega(meses_corte: list[int], meses_entrega: list[int], mes: int) -> int:
    """Empareja por posición: el n-ésimo corte se entrega en el n-ésimo mes."""
    return meses_entrega[meses_corte.index(mes)]


def generar_agenda(
    reg: Registro, desde: date, hasta: date, *, hoy: date | None = None
) -> list[EventoObligacion]:
    """Obligaciones cuya FECHA LÍMITE cae en el rango [desde, hasta].

    `hoy` es opcional y solo alimenta `dias_restantes`. Nunca se lee del reloj
    del sistema: el calendario debe ser reproducible.
    """
    if desde > hasta:
        raise ValueError("La fecha inicial no puede ser posterior a la final.")

    eventos: list[EventoObligacion] = []
    for obligacion in reg.obligaciones_de_entrega:
        if len(obligacion.meses_corte) != len(obligacion.meses_entrega):
            raise ValueError(
                f"{obligacion.id}: meses_corte y meses_entrega deben tener la misma "
                f"longitud para poder emparejarlos."
            )
        for anio in range(desde.year - 1, hasta.year + 2):
            for mes in obligacion.meses_corte:
                fecha_corte = _ultimo_dia(anio, mes)
                mes_entrega = _mes_de_entrega(
                    obligacion.meses_corte, obligacion.meses_entrega, mes
                )
                anio_entrega = anio + 1 if mes_entrega < mes else anio
                fecha_limite = _ultimo_dia(anio_entrega, mes_entrega)
                if not (desde <= fecha_limite <= hasta):
                    continue
                eventos.append(
                    EventoObligacion(
                        id_obligacion=obligacion.id,
                        fecha_corte=fecha_corte,
                        fecha_limite=fecha_limite,
                        destinatario=obligacion.destinatario,
                        medio=obligacion.medio,
                        fundamento=obligacion.fundamento,
                        dias_restantes=(
                            None if hoy is None else (fecha_limite - hoy).days
                        ),
                    )
                )
    return sorted(eventos, key=lambda e: (e.fecha_limite, e.id_obligacion))


# =============================================================================
# OBLIGACIONES DERIVADAS DE LA CLASIFICACIÓN — Art. 15, fracc. II
# =============================================================================


@dataclass(frozen=True)
class ObligacionDerivada:
    concepto: str
    fecha_origen: date
    fecha_limite: date
    plazo_dias: int
    fundamento: str


def obligaciones_por_clasificacion(
    reg: Registro, categoria: str, fecha_notificacion: date
) -> list[ObligacionDerivada]:
    """Plazos que dispara una clasificación en C o D.

    No son fechas de calendario: cuentan desde la notificación del Comité de
    Supervisión Auxiliar, que ocurre cuando ocurre.
    """
    n = reg.clasificacion.notificacion_asamblea
    if categoria not in n.categorias_con_plazo:
        return []
    limite_asamblea = fecha_notificacion + timedelta(days=n.plazo_dias)
    return [
        ObligacionDerivada(
            concepto="Notificar la clasificación a la Asamblea",
            fecha_origen=fecha_notificacion,
            fecha_limite=limite_asamblea,
            plazo_dias=n.plazo_dias,
            fundamento=n.fundamento,
        ),
        ObligacionDerivada(
            concepto="Entregar al CSA convocatoria y acta protocolizada",
            fecha_origen=limite_asamblea,
            fecha_limite=limite_asamblea + timedelta(days=n.evidencia_al_csa_dias),
            plazo_dias=n.evidencia_al_csa_dias,
            fundamento=n.fundamento,
        ),
    ]


# =============================================================================
# DISPARADOR DEL ART. 16 — exceso del límite de activos
# =============================================================================


@dataclass(frozen=True)
class DisparadorArt16:
    activado: bool
    fecha_corte: date
    fecha_limite_solicitud: date | None
    plazo_dias: int
    dias_restantes: int | None
    fundamento: str


def evaluar_disparador_art16(
    reg: Registro, *, fecha_corte: date, excede_limite: bool, hoy: date | None = None
) -> DisparadorArt16:
    """Al rebasar el límite del Art. 13 corre el plazo del Art. 16 para presentar
    solicitud de autorización ante el Comité de Supervisión Auxiliar."""
    p = reg.parametros.limite_activos
    if not excede_limite:
        return DisparadorArt16(
            activado=False,
            fecha_corte=fecha_corte,
            fecha_limite_solicitud=None,
            plazo_dias=p.plazo_solicitud_dias,
            dias_restantes=None,
            fundamento=p.fundamento_plazo,
        )
    limite = fecha_corte + timedelta(days=p.plazo_solicitud_dias)
    return DisparadorArt16(
        activado=True,
        fecha_corte=fecha_corte,
        fecha_limite_solicitud=limite,
        plazo_dias=p.plazo_solicitud_dias,
        dias_restantes=None if hoy is None else (limite - hoy).days,
        fundamento=p.fundamento_plazo,
    )
