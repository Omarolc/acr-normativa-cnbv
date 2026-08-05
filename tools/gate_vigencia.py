#!/usr/bin/env python3
"""Compuerta V — Bloqueo por vigencia.

Verifica que el sistema RECHACE fechas de corte alcanzadas por una alerta
bloqueante. Es una compuerta cuyo exito se manifiesta como una excepcion, y
por eso vive en Python: envolverla desde PowerShell hace que la salida por
stderr aborte el script justo cuando la verificacion pasa.

Fundamento: la Resolucion DOF 09-04-2024, diferida al 01-01-2027, sustituye
los Anexos T y U. Un computo con corte posterior usando parametros de 2026
tendria apariencia valida y contenido derogado.
"""

from __future__ import annotations

import sys
from pathlib import Path

from acr.cli.principal import calcular
from acr.entrada import leer_json
from acr.normativa import RegistroNoVigenteError, VigenciaBloqueadaError, cargar_registro

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"


def main() -> int:
    reg = cargar_registro()
    base = leer_json(CASO)
    fallos: list[str] = []

    bloqueantes = [a for a in reg.alertas_vigencia if a.bloqueante]
    if not bloqueantes:
        print("COMPUERTA V FALLO — no hay alertas bloqueantes en el registro.")
        return 1

    for alerta in bloqueantes:
        caso = dict(base)
        caso["fecha_corte"] = f"{alerta.fecha_entrada_vigor.year}-03-31"
        try:
            calcular(caso)
        except VigenciaBloqueadaError as exc:
            if alerta.id not in str(exc):
                fallos.append(f"{alerta.id}: rechazo sin citar la alerta")
            else:
                print(f"    {alerta.id}: rechazo correcto para {caso['fecha_corte']}")
        else:
            fallos.append(f"{alerta.id}: NO rechazo el corte {caso['fecha_corte']}")

    caso_viejo = dict(base)
    caso_viejo["fecha_corte"] = f"{reg.meta.vigencia_desde.year - 1}-12-31"
    try:
        calcular(caso_viejo)
    except RegistroNoVigenteError:
        print("    Corte anterior a la vigencia: rechazo correcto")
    else:
        fallos.append("No rechazo un corte anterior a la vigencia del registro")

    caso_ok = dict(base)
    try:
        calcular(caso_ok)
    except (VigenciaBloqueadaError, RegistroNoVigenteError) as exc:
        fallos.append(f"Rechazo un corte vigente: {exc}")

    if fallos:
        print("COMPUERTA V FALLO:")
        for f in fallos:
            print(f"  {f}")
        return 1

    print("COMPUERTA V OK — el bloqueo por vigencia funciona en ambos sentidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
