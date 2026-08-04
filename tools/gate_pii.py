#!/usr/bin/env python3
"""Compuerta anti-PII — ningun dato personal de socios en el repo versionado.

Los insumos del sistema son balanzas, carteras y padrones con nombre, RFC y
domicilio de socios de una cooperativa. Esos archivos viven en data/inputs/
(excluido por .gitignore) y jamas en el arbol versionado ni en el snapshot
que se sube a una sesion de sprint.

Detecta RFC de persona fisica y moral, y CURP.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

RFC = re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b")
CURP = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2}\b")

EXCLUIR_DIRS = {".venv", "venv", "__pycache__", ".git", "build", "dist", "data"}
EXTENSIONES = {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".ps1", ".toml"}


def main() -> int:
    fugas: list[str] = []
    for ruta in RAIZ.rglob("*"):
        if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
            continue
        rel = ruta.relative_to(RAIZ)
        if EXCLUIR_DIRS & set(rel.parts):
            continue
        if rel.as_posix().startswith("tools/gate_pii.py"):
            continue
        try:
            texto = ruta.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            if RFC.search(linea) or CURP.search(linea):
                fugas.append(f"  {rel.as_posix()}:{n}")

    if fugas:
        print("COMPUERTA PII FALLO — posible dato personal de socios en el repo:")
        print("\n".join(fugas))
        print("\nMover a data/inputs/ (excluido) o anonimizar antes de versionar.")
        return 1

    print("COMPUERTA PII OK — sin RFC ni CURP en el arbol versionado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
