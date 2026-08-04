#!/usr/bin/env python3
"""Compuerta E — Reproducibilidad.

Sustituye a la prueba contra produccion del protocolo DEV83: aqui no hay
servidor que probar. La garantia equivalente es que el mismo insumo produce
exactamente la misma salida, siempre. Es lo que hace defendible un computo
ante la verificacion del Comite de Supervision Auxiliar (Disposiciones
Art. 1 Bis 6): sin reproducibilidad no hay expediente que sostener.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from acr.motor import (
    calcular_capital_neto,
    calcular_capitalizacion,
    clasificar,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
)

CASO_BASE: dict[str, Any] = {
    "capital_contable": 1_000_000,
    "certificados_no_elegibles": 50_000,
    "financiamientos_para_partes_sociales": 0,
    "cartera_bruta": 5_000_000,
    "provisiones": 200_000,
    "fecha_corte": "2026-06-30",
    "activos_totales": 18_000_000,
    "valor_udi": "8.52",
    "capital_social_pagado": 800_000,
    "relacionadas_dispuestos": 40_000,
    "relacionadas_lineas": 15_000,
    "eeff_cumplen_reglas": True,
    "eeff_en_plazo": True,
}


def corrida(caso: dict[str, Any]) -> dict[str, Any]:
    cn = calcular_capital_neto(
        caso["capital_contable"],
        caso["certificados_no_elegibles"],
        caso["financiamientos_para_partes_sociales"],
    )
    cap = calcular_capitalizacion(
        cn, caso["cartera_bruta"], caso["provisiones"], caso["fecha_corte"]
    )
    cl = clasificar(
        cap,
        eeff_cumplen_reglas_presentacion=caso["eeff_cumplen_reglas"],
        eeff_presentados_en_plazo=caso["eeff_en_plazo"],
        historial_categorias=[],
    )
    lim = evaluar_limite_activos(caso["activos_totales"], caso["valor_udi"])
    pr = evaluar_personas_relacionadas(
        caso["relacionadas_dispuestos"],
        caso["relacionadas_lineas"],
        caso["capital_contable"],
        caso["capital_social_pagado"],
        caso["valor_udi"],
    )
    return {
        "capital_neto": str(cn.valor),
        "requerimiento": str(cap.requerimiento),
        "nivel_pct": str(cap.nivel_pct),
        "categoria": cl.categoria,
        "fundamento": cl.fundamento,
        "activos_en_udis": str(lim.activos_en_udis),
        "excede_limite_art13": lim.excede,
        "relacionadas_pct": str(pr.porcentaje),
        "cumple_art26": pr.cumple,
    }


def sha(obj: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> int:
    h1 = sha(corrida(CASO_BASE))
    h2 = sha(corrida(CASO_BASE))
    if h1 != h2:
        print(f"COMPUERTA E FALLO — salida no reproducible:\n  {h1}\n  {h2}")
        return 1
    print(f"COMPUERTA E OK — reproducible. SHA-256: {h1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
