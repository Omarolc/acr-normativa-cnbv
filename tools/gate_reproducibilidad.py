#!/usr/bin/env python3
"""Compuerta E — Reproducibilidad.

Sustituye a la prueba contra produccion del protocolo DEV83: aqui no hay
servidor que probar. La garantia equivalente es que el mismo insumo produce
exactamente los mismos bytes de salida, siempre.

Es lo que hace defendible un computo ante la verificacion del Comite de
Supervision Auxiliar (Disposiciones Art. 1 Bis 6): sin reproducibilidad no hay
expediente que sostener, porque no se puede demostrar que la cifra entregada
proviene de los insumos declarados.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from acr.cli.principal import calcular
from acr.entrada import leer_json

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"


def _sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    if not CASO.exists():
        print(f"COMPUERTA E FALLO — no existe el caso base en {CASO}")
        return 1
    caso = leer_json(CASO)

    salidas = [
        json.dumps(calcular(caso), default=str, sort_keys=True, ensure_ascii=False)
        for _ in range(2)
    ]
    h1, h2 = _sha(salidas[0]), _sha(salidas[1])

    if h1 != h2:
        print(f"COMPUERTA E FALLO — salida no reproducible:\n  {h1}\n  {h2}")
        return 1

    resultado = json.loads(salidas[0])
    print(f"COMPUERTA E OK — reproducible. SHA-256: {h1}")
    print(f"    registro   : {resultado['registro']['version']}")
    print(f"    categoria  : {resultado['clasificacion']['categoria']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
