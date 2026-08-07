"""Manifiesto del expediente — la prueba de qué produjo qué cifra.

Fundamento operativo: Disposiciones Art. 1 Bis 6 establece que el cómputo de la
sociedad rige para todos los efectos legales SALVO que el Comité de Supervisión
Auxiliar verifique y obtenga un cómputo distinto, en cuyo caso el del CSA es
definitivo.

Ahí es donde una cooperativa pierde. El manifiesto convierte una verificación
de tres semanas en una de tres días: un tercero puede reconstruir cada cifra
desde los insumos originales sin abrir el código.

DETERMINISMO
------------
Ningún valor proviene del reloj ni del entorno. `fecha_generacion`, `operador`
y `commit` entran como parámetros. Dos ejecuciones del mismo periodo con los
mismos insumos producen manifiestos byte a byte idénticos — y esa es la
propiedad que se verifica en la compuerta E.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from acr.normativa.esquema import Registro


@dataclass(frozen=True)
class ArchivoInsumo:
    nombre: str
    sha256: str
    bytes_totales: int

    def como_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "sha256": self.sha256,
            "bytes": self.bytes_totales,
        }


def describir_insumo(ruta: Path) -> ArchivoInsumo:
    """SHA-256 y tamaño de un archivo de entrada. Único punto de I/O del módulo."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el insumo declarado: {ruta}")
    contenido = ruta.read_bytes()
    return ArchivoInsumo(
        nombre=ruta.name,
        sha256=hashlib.sha256(contenido).hexdigest(),
        bytes_totales=len(contenido),
    )


def construir_manifiesto(
    *,
    reg: Registro,
    periodo: str,
    fecha_generacion: date,
    operador: str,
    version_motor: str,
    commit: str,
    sha256_registro: str,
    insumos: list[ArchivoInsumo],
    resultado: dict[str, Any],
) -> dict[str, Any]:
    """Manifiesto completo. Función pura: todo entra como parámetro."""
    return {
        "expediente": {
            "periodo": periodo,
            "fecha_corte": resultado["fecha_corte"],
            "fecha_generacion": fecha_generacion.isoformat(),
            "operador": operador,
        },
        "entidad": {
            "regimen": reg.ambito.entidad if hasattr(reg, "ambito") else "Nivel Básico",
            "destinatario": "Comité de Supervisión Auxiliar (FOCOOP)",
            "nota": (
                "La CNBV no es receptora directa. El reporte A-2113 lo presenta el "
                "CSA conforme a Disposiciones Art. 1 Bis 7."
            ),
        },
        "versiones": {
            "registro_normativo": reg.meta.version_registro,
            "sha256_registro": sha256_registro,
            "vigencia_registro": (
                f"{reg.meta.vigencia_desde.isoformat()} a "
                f"{reg.meta.vigencia_hasta.isoformat()}"
            ),
            "motor": version_motor,
            "commit": commit,
        },
        "insumos": [i.como_dict() for i in sorted(insumos, key=lambda x: x.nombre)],
        "hash_insumos_normalizados": resultado["hash_insumos"],
        "resultado": {
            "categoria": resultado["clasificacion"]["categoria"],
            "fundamento": resultado["clasificacion"]["fundamento"],
            "nivel_capitalizacion": next(
                (
                    f["importe"]
                    for f in resultado["formulario_anexo_u"]
                    if f["renglon"] == 10
                ),
                None,
            ),
        },
        "responsabilidad": (
            "Herramienta de apoyo al cálculo y a la preparación de información. "
            "La formulación y presentación de los estados financieros básicos es "
            "responsabilidad del Consejo de Administración conforme a Disposiciones "
            "Art. 1 Bis 1, tercer párrafo."
        ),
    }
