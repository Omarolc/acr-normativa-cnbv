#!/usr/bin/env python3
"""Compuerta X — Determinismo del expediente de auditoria.

Genera el mismo expediente dos veces y compara byte a byte. Si difiere, el
expediente no prueba nada: un tercero no podria reconstruirlo.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from acr import __version__
from acr.cli.principal import calcular
from acr.entrada import leer_json
from acr.expediente import generar_expediente, verificar_cadena
from acr.normativa import cargar_registro, hash_registro

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"


def _generar(destino: Path):
    reg = cargar_registro()
    return generar_expediente(
        reg=reg,
        resultado=calcular(leer_json(CASO)),
        destino=destino,
        periodo="2026-Q2",
        fecha_generacion=date(2026, 8, 4),
        operador="compuerta",
        version_motor=__version__,
        commit="gate",
        sha256_registro=hash_registro(),
        rutas_insumos=[CASO],
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="acr_gate_"))
    try:
        a = _generar(tmp / "a")
        b = _generar(tmp / "b")
        diferencias = [
            ra.name
            for ra, rb in zip(a.archivos, b.archivos, strict=True)
            if hashlib.sha256(ra.read_bytes()).hexdigest()
            != hashlib.sha256(rb.read_bytes()).hexdigest()
        ]
        if diferencias:
            print(f"COMPUERTA X FALLO — expediente no determinista: {diferencias}")
            return 1

        semilla = json.loads(
            (a.raiz / "99_Expediente_Auditoria" / "computo_anexo_u.json").read_text(
                encoding="utf-8"
            )
        )["hash_insumos"]
        if not verificar_cadena(a.bitacora, semilla):
            print("COMPUERTA X FALLO — la bitacora encadenada no verifica.")
            return 1

        conjunto = hashlib.sha256(
            b"".join(sorted(r.read_bytes() for r in a.archivos))
        ).hexdigest()
        print(f"COMPUERTA X OK — expediente determinista. SHA-256 conjunto: {conjunto}")
        print(f"    archivos   : {len(a.archivos)}")
        print(f"    bitacora   : {len(a.bitacora)} entradas verificadas")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
