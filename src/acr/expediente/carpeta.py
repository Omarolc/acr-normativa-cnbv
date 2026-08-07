"""Estructura de la carpeta de entrega y del expediente de auditoría.

ESTRUCTURA CORREGIDA
--------------------
La original decía "Carpeta de entrega a CNBV" e incluía el A-2113 como
entregable de la cooperativa y un "Acuse_Recibo_Simulado.pdf".

Tres correcciones:
  1. La contraparte es el Comité de Supervisión Auxiliar, no la CNBV
     (Disposiciones Arts. 1 Bis 1 y 1 Bis 6).
  2. El A-2113 lo presenta el CSA a la Comisión (Art. 1 Bis 7). La cooperativa
     no lo genera y no debe aparecer en su carpeta.
  3. Un acuse simulado dentro de un expediente regulatorio es un riesgo, no una
     funcionalidad. Se sustituye por `manifiesto_de_entrega.json`: misma función
     probatoria, cero ambigüedad sobre su naturaleza.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from acr.entrada import escribir_texto
from acr.expediente.bitacora import EntradaBitacora, encadenar
from acr.expediente.manifiesto import ArchivoInsumo, construir_manifiesto, describir_insumo
from acr.expediente.memoria import generar_memoria
from acr.normativa.esquema import Registro

SUBCARPETAS = (
    "01_Trimestral_CSA",
    "02_Semestral_Impreso_Firmado",
    "03_Divulgacion_a_Socios",
    "04_Gobierno_Corporativo",
    "05_Monitoreo_Umbrales",
    "99_Expediente_Auditoria",
)


@dataclass(frozen=True)
class ExpedienteGenerado:
    raiz: Path
    archivos: list[Path]
    manifiesto: dict[str, Any]
    bitacora: list[EntradaBitacora]


def _json(datos: Any) -> str:
    return json.dumps(datos, sort_keys=True, ensure_ascii=False, indent=2, default=str)


def generar_expediente(
    *,
    reg: Registro,
    resultado: dict[str, Any],
    destino: Path,
    periodo: str,
    fecha_generacion: date,
    operador: str,
    version_motor: str,
    commit: str,
    sha256_registro: str,
    rutas_insumos: list[Path],
) -> ExpedienteGenerado:
    """Genera la carpeta completa. Determinista: mismos parámetros, mismos bytes."""
    raiz = destino / f"{resultado['fecha_corte']}_{periodo}_Entrega_CSA"
    for sub in SUBCARPETAS:
        (raiz / sub).mkdir(parents=True, exist_ok=True)

    insumos: list[ArchivoInsumo] = [describir_insumo(r) for r in rutas_insumos]

    manifiesto = construir_manifiesto(
        reg=reg,
        periodo=periodo,
        fecha_generacion=fecha_generacion,
        operador=operador,
        version_motor=version_motor,
        commit=commit,
        sha256_registro=sha256_registro,
        insumos=insumos,
        resultado=resultado,
    )

    eventos: list[tuple[str, str]] = [
        ("registro_cargado", f"version {reg.meta.version_registro} sha {sha256_registro}"),
        ("insumos_verificados", ", ".join(f"{i.nombre}:{i.sha256[:12]}" for i in insumos)),
        ("computo_realizado", f"corte {resultado['fecha_corte']}"),
        ("clasificacion", f"categoria {resultado['clasificacion']['categoria']}"),
        ("expediente_generado", f"periodo {periodo} operador {operador}"),
    ]
    bitacora = encadenar(eventos, semilla=resultado["hash_insumos"])

    memoria = generar_memoria(
        reg=reg,
        resultado=resultado,
        periodo=periodo,
        fecha_generacion=fecha_generacion,
        operador=operador,
        commit=commit,
    )

    entrega = {
        "periodo": periodo,
        "fecha_corte": resultado["fecha_corte"],
        "fecha_generacion": fecha_generacion.isoformat(),
        "destinatario": reg.ambito.supervisor_directo,
        "documentos": sorted(f"{s}/" for s in SUBCARPETAS),
        "advertencia": (
            "Este manifiesto NO es un acuse de recibo. Documenta qué se generó y con "
            "qué insumos. El acuse lo emite el Comité de Supervisión Auxiliar al "
            "recibir la información."
        ),
        "nota_a2113": (
            "El reporte A-2113 no forma parte de esta entrega: lo presenta el CSA a "
            "la CNBV conforme a Disposiciones Art. 1 Bis 7."
        ),
    }

    escritos: list[Path] = []
    plan: list[tuple[Path, str]] = [
        (raiz / "99_Expediente_Auditoria" / "manifiesto.json", _json(manifiesto)),
        (
            raiz / "99_Expediente_Auditoria" / "bitacora_ejecucion.json",
            _json([e.como_dict() for e in bitacora]),
        ),
        (raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md", memoria),
        (
            raiz / "99_Expediente_Auditoria" / "computo_anexo_u.json",
            _json(resultado),
        ),
        (raiz / "manifiesto_de_entrega.json", _json(entrega)),
        (
            raiz / "01_Trimestral_CSA" / "LEEME.md",
            _formato_pendiente("Balance general y estado de resultados", "Anexo U, apartado I"),
        ),
        (
            raiz / "02_Semestral_Impreso_Firmado" / "LEEME.md",
            _formato_pendiente(
                "Versión impresa firmada por el Presidente del Consejo y el "
                "Director o Gerente General",
                "Disposiciones Art. 1 Bis 1, párrafo 4",
            ),
        ),
        (
            raiz / "03_Divulgacion_a_Socios" / "LEEME.md",
            _formato_pendiente(
                "Cartel de divulgación en sucursales",
                "Disposiciones Art. 1 Bis 1, párrafo 1",
            ),
        ),
        (
            raiz / "04_Gobierno_Corporativo" / "LEEME.md",
            _formato_pendiente(
                "Reporte de personas relacionadas y evidencia de asamblea",
                "LRASCAP Arts. 15 fracc. II y 26",
            ),
        ),
        (
            raiz / "05_Monitoreo_Umbrales" / "LEEME.md",
            _formato_pendiente(
                "Seguimiento de activos en UDIS y disparador del Art. 16",
                "LRASCAP Arts. 13 y 16",
            ),
        ),
    ]
    for ruta, contenido in plan:
        escribir_texto(ruta, contenido)
        escritos.append(ruta)

    return ExpedienteGenerado(
        raiz=raiz, archivos=sorted(escritos), manifiesto=manifiesto, bitacora=bitacora
    )


def _formato_pendiente(descripcion: str, fundamento: str) -> str:
    return (
        f"# Pendiente de renderizado\n\n"
        f"**Contenido:** {descripcion}\n\n"
        f"**Fundamento:** {fundamento}\n\n"
        f"El renderizado fiel al formato del Anexo U se implementa en el sprint "
        f"ACR-07. Esta carpeta queda como esqueleto con su fundamento declarado; "
        f"no se rellena con un formato aproximado.\n"
    )
