"""Cargador del registro normativo.

Es el único punto del sistema que lee de disco. El motor recibe el objeto
`Registro` ya validado como parámetro, y por lo tanto sigue siendo puro.
"""

from __future__ import annotations

import hashlib
from calendar import monthrange
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from acr.normativa.esquema import Registro

RUTA_REGISTRO = Path(__file__).parent / "registro_normativo_nivel_basico.yaml"


class RegistroNoVigenteError(RuntimeError):
    """La fecha de corte cae fuera de la vigencia del registro cargado.

    No se degrada a "usar el registro más cercano": producir un cómputo con
    parámetros derogados es peor que no producirlo.
    """


class VigenciaBloqueadaError(RuntimeError):
    """Una alerta de vigencia bloqueante aplica a la fecha de corte solicitada."""


@lru_cache(maxsize=4)
def cargar_registro(ruta: Path | None = None) -> Registro:
    """Carga y valida el registro. Cacheado: el archivo no cambia en ejecución."""
    destino = ruta or RUTA_REGISTRO
    if not destino.exists():
        raise FileNotFoundError(f"Registro normativo no encontrado en {destino}")
    datos = yaml.safe_load(destino.read_text(encoding="utf-8-sig"))
    return Registro.model_validate(datos)


def hash_registro(ruta: Path | None = None) -> str:
    """SHA-256 del archivo de registro, para el manifiesto del expediente."""
    destino = ruta or RUTA_REGISTRO
    return hashlib.sha256(destino.read_bytes()).hexdigest()


def verificar_vigencia(reg: Registro, fecha_corte: date) -> None:
    """Falla ruidosamente si la fecha de corte no está cubierta por el registro.

    Fundamento operativo: la Resolución DOF 09-04-2024, diferida al 01-01-2027,
    sustituye los Anexos T y U. Un cómputo con corte posterior usando parámetros
    de 2026 tendría apariencia válida y contenido derogado.
    """
    for alerta in reg.alertas_vigencia:
        if alerta.bloqueante and fecha_corte >= alerta.fecha_entrada_vigor:
            raise VigenciaBloqueadaError(
                f"[{alerta.id}] Fecha de corte {fecha_corte.isoformat()} alcanzada por "
                f"una alerta de vigencia bloqueante con entrada en vigor "
                f"{alerta.fecha_entrada_vigor.isoformat()}.\n"
                f"{alerta.descripcion.strip()}\n"
                f"Cargar los anexos sustituidos en el registro normativo antes de "
                f"generar cómputos con esta fecha de corte."
            )

    if not (reg.meta.vigencia_desde <= fecha_corte <= reg.meta.vigencia_hasta):
        raise RegistroNoVigenteError(
            f"Fecha de corte {fecha_corte.isoformat()} fuera de la vigencia del "
            f"registro {reg.meta.version_registro} "
            f"({reg.meta.vigencia_desde.isoformat()} a {reg.meta.vigencia_hasta.isoformat()})."
        )


def verificar_fecha_corte_trimestral(reg: Registro, fecha_corte: date) -> None:
    """Art. 1 Bis 6: saldos al día último de marzo, junio, septiembre o diciembre."""
    meses = reg.parametros.capitalizacion.meses_corte
    if fecha_corte.month not in meses:
        raise ValueError(
            f"Fecha de corte {fecha_corte.isoformat()} no corresponde a un cierre "
            f"trimestral. {reg.parametros.capitalizacion.fundamento_computo}: "
            f"meses válidos {meses}."
        )
    if fecha_corte.day != monthrange(fecha_corte.year, fecha_corte.month)[1]:
        raise ValueError(
            f"Fecha de corte {fecha_corte.isoformat()} no es el día último del mes. "
            f"{reg.parametros.capitalizacion.base_saldos} "
            f"({reg.parametros.capitalizacion.fundamento_computo})."
        )
