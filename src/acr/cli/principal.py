"""CLI de ACR Normativa.

La salida es JSON determinista: claves ordenadas, Decimal serializado como
cadena, sin timestamps. Dos ejecuciones del mismo insumo producen bytes
idénticos — requisito de la compuerta E y del expediente de auditoría.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from acr.entrada import escribir_texto, leer_json
from acr.motor import (
    calcular_capital_neto,
    calcular_capitalizacion,
    clasificar,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
)
from acr.normativa import (
    cargar_registro,
    hash_registro,
    verificar_fecha_corte_trimestral,
    verificar_vigencia,
)


def _requerido(caso: dict[str, Any], clave: str) -> Any:
    """Sin defaults. Un insumo ausente es un error, no un cero."""
    if clave not in caso:
        raise KeyError(
            f"El caso no contiene '{clave}'. La norma no permite asumir cero: "
            f"un renglón ausente y un renglón en cero son hechos distintos."
        )
    return caso[clave]


def _serializar(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"No serializable: {type(obj)}")


def calcular(caso: dict[str, Any]) -> dict[str, Any]:
    reg = cargar_registro()
    fecha_corte = date.fromisoformat(str(_requerido(caso, "fecha_corte")))
    verificar_vigencia(reg, fecha_corte)
    verificar_fecha_corte_trimestral(reg, fecha_corte)

    cn = calcular_capital_neto(
        reg,
        capital_contable=_requerido(caso, "capital_contable"),
        certificados_no_elegibles=_requerido(caso, "certificados_no_elegibles"),
        financiamientos_partes_sociales=_requerido(caso, "financiamientos_partes_sociales"),
    )
    cap = calcular_capitalizacion(
        reg,
        cn,
        cartera_vigente=_requerido(caso, "cartera_vigente"),
        cartera_vencida=_requerido(caso, "cartera_vencida"),
        estimacion_preventiva=_requerido(caso, "estimacion_preventiva"),
        fecha_corte=fecha_corte.isoformat(),
    )
    cl = clasificar(
        reg,
        cap,
        eeff_cumplen_reglas_presentacion=bool(_requerido(caso, "eeff_cumplen_reglas")),
        eeff_presentados_en_plazo=bool(_requerido(caso, "eeff_en_plazo")),
        historial_categorias=caso.get("historial_categorias", []),
    )
    lim = evaluar_limite_activos(
        reg,
        activos_totales=_requerido(caso, "activos_totales"),
        valor_udi_a_fecha_corte=_requerido(caso, "valor_udi"),
    )
    pr = evaluar_personas_relacionadas(
        reg,
        montos_dispuestos=_requerido(caso, "relacionadas_dispuestos"),
        lineas_de_credito_irrevocables=_requerido(caso, "relacionadas_lineas"),
        capital_contable=_requerido(caso, "capital_contable"),
        capital_social_pagado=_requerido(caso, "capital_social_pagado"),
        valor_udi_a_fecha_corte=_requerido(caso, "valor_udi"),
    )

    return {
        "registro": {
            "version": reg.meta.version_registro,
            "sha256": hash_registro(),
            "vigencia_desde": reg.meta.vigencia_desde.isoformat(),
            "vigencia_hasta": reg.meta.vigencia_hasta.isoformat(),
        },
        "fecha_corte": cap.fecha_corte,
        "formulario_anexo_u": [
            {"renglon": n, "concepto": c, "importe": v}
            for n, c, v in cap.formulario_anexo_u(cn)
        ],
        "clasificacion": {
            "categoria": cl.categoria,
            "motivo": cl.motivo,
            "fundamento": cl.fundamento,
            "requiere_notificacion_plazo": cl.requiere_notificacion_plazo,
            "plazo_notificacion_dias": cl.plazo_notificacion_dias,
            "debe_abstenerse_captacion": cl.debe_abstenerse_captacion,
            "obligaciones_derivadas": cl.obligaciones_derivadas,
        },
        "limite_activos_art13": {
            "activos_en_udis": lim.activos_en_udis,
            "limite_udis": lim.limite_udis,
            "excede": lim.excede,
            "holgura_pct": lim.holgura_pct,
            "plazo_solicitud_dias": lim.plazo_solicitud_dias,
            "fundamento": list(lim.fundamento),
        },
        "personas_relacionadas_art26": {
            "exposicion_total": pr.exposicion_total,
            "porcentaje": pr.porcentaje,
            "limite_pct": pr.limite_pct,
            "cumple": pr.cumple,
            "umbral_exencion": pr.umbral_exencion,
            "fundamento": pr.fundamento,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acr", description="ACR Normativa — Nivel Básico")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_calc = sub.add_parser("calcular", help="Cómputo del Nivel de Capitalización")
    p_calc.add_argument("--caso", required=True, type=Path)
    p_calc.add_argument("--out", type=Path)

    p_reg = sub.add_parser("registro", help="Información del registro normativo")

    args = parser.parse_args(argv)

    if args.comando == "registro":
        reg = cargar_registro()
        print(f"version   : {reg.meta.version_registro}")
        print(f"sha256    : {hash_registro()}")
        print(f"vigencia  : {reg.meta.vigencia_desde} a {reg.meta.vigencia_hasta}")
        for a in reg.alertas_vigencia:
            marca = "BLOQUEANTE" if a.bloqueante else "informativa"
            print(f"  [{marca}] {a.id} — vigor {a.fecha_entrada_vigor}")
        return 0

    del p_calc, p_reg
    caso = leer_json(args.caso)
    resultado = calcular(caso)
    texto = json.dumps(resultado, default=_serializar, sort_keys=True, ensure_ascii=False, indent=2)
    if args.out:
        escribir_texto(args.out, texto)
    else:
        print(texto)
    return 0
