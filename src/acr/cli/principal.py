"""CLI de ACR Normativa.

La salida es JSON determinista: claves ordenadas, Decimal serializado como
cadena, sin timestamps. Dos ejecuciones del mismo insumo producen bytes
idénticos — requisito de la compuerta E y del expediente de auditoría.
"""

from __future__ import annotations

import argparse
import hashlib
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
    evaluar_disparador_art16,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
    generar_agenda,
)
from acr.normativa import (
    cargar_registro,
    hash_registro,
    verificar_fecha_corte_trimestral,
    verificar_vigencia,
)
from acr.persistencia import Almacen


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


def hash_insumos(caso: dict[str, Any]) -> str:
    """SHA-256 de los insumos normalizados. Entra al expediente y a la base."""
    canonico = json.dumps(caso, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def calcular(caso: dict[str, Any], *, historial: list[str] | None = None) -> dict[str, Any]:
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
        historial_categorias=(
            historial if historial is not None else caso.get("historial_categorias", [])
        ),
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

    art16 = evaluar_disparador_art16(
        reg, fecha_corte=fecha_corte, excede_limite=lim.excede
    )

    return {
        "hash_insumos": hash_insumos(caso),
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
            "disparador_art16": {
                "activado": art16.activado,
                "fecha_limite_solicitud": (
                    None
                    if art16.fecha_limite_solicitud is None
                    else art16.fecha_limite_solicitud.isoformat()
                ),
                "fundamento": art16.fundamento,
            },
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

    p_ag = sub.add_parser("agenda", help="Calendario de obligaciones")
    p_ag.add_argument("--desde", required=True)
    p_ag.add_argument("--hasta", required=True)
    p_ag.add_argument("--hoy")

    p_regi = sub.add_parser("registrar", help="Registra un periodo en la base")
    p_regi.add_argument("--caso", required=True, type=Path)
    p_regi.add_argument("--base", required=True, type=Path)
    p_regi.add_argument("--sobrescribir", action="store_true")

    p_hist = sub.add_parser("historial", help="Historial de clasificaciones")
    p_hist.add_argument("--base", required=True, type=Path)

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

    if args.comando == "agenda":
        return _agenda(args.desde, args.hasta, args.hoy)

    if args.comando == "registrar":
        return _registrar(args.caso, args.base, sobrescribir=args.sobrescribir)

    if args.comando == "historial":
        return _historial(args.base)

    del p_calc, p_reg, p_ag, p_regi, p_hist
    caso = leer_json(args.caso)
    resultado = calcular(caso)
    texto = json.dumps(resultado, default=_serializar, sort_keys=True, ensure_ascii=False, indent=2)
    if args.out:
        escribir_texto(args.out, texto)
    else:
        print(texto)
    return 0


def _agenda(desde: str, hasta: str, hoy: str | None) -> int:
    reg = cargar_registro()
    eventos = generar_agenda(
        reg,
        date.fromisoformat(desde),
        date.fromisoformat(hasta),
        hoy=None if hoy is None else date.fromisoformat(hoy),
    )
    print(f"{'LIMITE':<12} {'CORTE':<12} {'OBLIGACION':<28} {'MEDIO':<12} FUNDAMENTO")
    for e in eventos:
        print(
            f"{e.fecha_limite.isoformat():<12} {e.fecha_corte.isoformat():<12} "
            f"{e.id_obligacion:<28} {e.medio:<12} {e.fundamento}"
        )
    print(f"\n{len(eventos)} obligaciones en el rango.")
    return 0


def _registrar(ruta_caso: Path, ruta_base: Path, *, sobrescribir: bool) -> int:
    reg = cargar_registro()
    caso = leer_json(ruta_caso)
    fecha_corte = date.fromisoformat(str(_requerido(caso, "fecha_corte")))

    with Almacen(ruta_base) as almacen:
        historial = almacen.historial_categorias(fecha_corte)
        resultado = calcular(caso, historial=historial)
        cl = resultado["clasificacion"]
        nivel = next(
            (f["importe"] for f in resultado["formulario_anexo_u"] if f["renglon"] == 10),
            None,
        )
        almacen.registrar_periodo(
            fecha_corte=fecha_corte,
            nivel_pct=None if nivel is None else Decimal(str(nivel)),
            categoria=cl["categoria"],
            motivo=cl["motivo"],
            fundamento=cl["fundamento"],
            hash_insumos=resultado["hash_insumos"],
            version_registro=reg.meta.version_registro,
            sha256_registro=hash_registro(),
            sobrescribir=sobrescribir,
        )
        lim = resultado["limite_activos_art13"]
        disparador = lim["disparador_art16"]
        almacen.registrar_activos(
            fecha_corte=fecha_corte,
            activos_totales=Decimal(str(_requerido(caso, "activos_totales"))),
            valor_udi=Decimal(str(_requerido(caso, "valor_udi"))),
            activos_en_udis=Decimal(str(lim["activos_en_udis"])),
            excede=bool(lim["excede"]),
            fecha_limite_art16=(
                None
                if disparador["fecha_limite_solicitud"] is None
                else date.fromisoformat(disparador["fecha_limite_solicitud"])
            ),
        )
        pr = resultado["personas_relacionadas_art26"]
        almacen.registrar_relacionadas(
            fecha_corte=fecha_corte,
            exposicion=Decimal(str(pr["exposicion_total"])),
            porcentaje=None if pr["porcentaje"] is None else Decimal(str(pr["porcentaje"])),
            cumple=bool(pr["cumple"]),
        )

    print(f"{fecha_corte.isoformat()}  categoria {cl['categoria']}  "
          f"historial previo {historial}")
    print(f"  {cl['motivo']}")
    print(f"  {cl['fundamento']}")
    return 0


def _historial(ruta_base: Path) -> int:
    with Almacen(ruta_base) as almacen:
        periodos = almacen.periodos()
        if not periodos:
            print("Sin periodos registrados.")
            return 0
        print(f"{'CORTE':<12} {'NIVEL':>10}  CAT  FUNDAMENTO")
        for p in periodos:
            nivel = "sin req." if p.nivel_pct is None else f"{p.nivel_pct}%"
            print(f"{p.fecha_corte.isoformat():<12} {nivel:>10}   {p.categoria}   {p.fundamento}")
        excesos = almacen.excesos_art13()
        if excesos:
            print("\nEXCESOS DEL LIMITE DEL ART. 13:")
            for fecha, udis, limite in excesos:
                lim = "sin fecha" if limite is None else limite.isoformat()
                print(f"  {fecha.isoformat()}  {udis} UDIS  -> solicitud antes de {lim}")
        incumple = almacen.incumplimientos_art26()
        if incumple:
            print("\nINCUMPLIMIENTOS DEL ART. 26:")
            for fecha, pct in incumple:
                print(f"  {fecha.isoformat()}  {pct}% del capital contable")
    return 0
