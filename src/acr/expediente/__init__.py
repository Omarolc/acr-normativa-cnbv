"""Capa 4 — Expediente de auditoría.

El activo defendible del sistema. Disposiciones Art. 1 Bis 6: el cómputo de la
sociedad rige salvo que el Comité de Supervisión Auxiliar obtenga uno distinto.
Este expediente es lo que sostiene el cómputo ante esa verificación.
"""
from acr.expediente.bitacora import EntradaBitacora, encadenar, verificar_cadena
from acr.expediente.carpeta import SUBCARPETAS, ExpedienteGenerado, generar_expediente
from acr.expediente.manifiesto import ArchivoInsumo, construir_manifiesto, describir_insumo
from acr.expediente.memoria import generar_memoria

__all__ = [
    "SUBCARPETAS",
    "ArchivoInsumo",
    "EntradaBitacora",
    "ExpedienteGenerado",
    "construir_manifiesto",
    "describir_insumo",
    "encadenar",
    "generar_expediente",
    "generar_memoria",
    "verificar_cadena",
]
