"""Capa de entrada: lectura robusta de archivos de insumo.

DEFECTO QUE ESTE MÓDULO CORRIGE (ACR-02.1)
------------------------------------------
La CLI leía con `encoding="utf-8"` estricto. En Windows, PowerShell 5.1 con
`Set-Content -Encoding UTF8`, el Bloc de notas y las exportaciones de Excel
escriben un BOM (byte order mark) al inicio del archivo. El resultado era:

    json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig)

Un traceback de la librería estándar, sin fundamento legal, sin decir qué
archivo ni qué hacer. Y disparado por las herramientas que una cooperativa
usa de forma natural para preparar sus insumos.

`utf-8-sig` acepta ambos casos: consume el BOM si está presente y se comporta
como `utf-8` si no. Las SALIDAS se siguen escribiendo sin BOM, porque el
manifiesto del expediente compara hashes y un BOM cambiaría el hash del
mismo contenido.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArchivoDeEntradaInvalidoError(ValueError):
    """Un archivo de insumo no se pudo leer o interpretar.

    El mensaje explica qué archivo y qué hacer, en vez de propagar el traceback
    de la librería estándar hacia un operador que no programa.
    """


def leer_texto(ruta: Path) -> str:
    """Lee texto tolerando BOM. Nunca falla en silencio."""
    if not ruta.exists():
        raise ArchivoDeEntradaInvalidoError(
            f"No existe el archivo de entrada: {ruta}"
        )
    try:
        return ruta.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArchivoDeEntradaInvalidoError(
            f"El archivo {ruta.name} no está en UTF-8. "
            f"Si se exportó desde Excel o un sistema contable antiguo, puede estar "
            f"en Latin-1 (ANSI). Vuelve a guardarlo como UTF-8. Detalle: {exc}"
        ) from exc


def leer_json(ruta: Path) -> dict[str, Any]:
    """Lee un JSON de insumo tolerando BOM, con error explicativo."""
    texto = leer_texto(ruta)
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ArchivoDeEntradaInvalidoError(
            f"El archivo {ruta.name} no es JSON válido (línea {exc.lineno}, "
            f"columna {exc.colno}): {exc.msg}. "
            f"Revisa comas sobrantes, comillas sin cerrar o comentarios: "
            f"JSON no admite comentarios."
        ) from exc

    if not isinstance(datos, dict):
        raise ArchivoDeEntradaInvalidoError(
            f"El archivo {ruta.name} debe contener un objeto JSON en la raíz, "
            f"no {type(datos).__name__}."
        )
    return datos


def escribir_texto(ruta: Path, contenido: str) -> None:
    """Escribe SIN BOM. El manifiesto del expediente compara hashes: un BOM
    cambiaría el hash del mismo contenido y rompería la reproducibilidad."""
    ruta.write_text(contenido, encoding="utf-8")
