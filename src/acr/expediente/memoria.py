"""Memoria de cálculo — reconstrucción de cada cifra sin abrir el código.

Criterio de cierre de ACR-04: un contador que no programa debe poder tomar la
balanza, la memoria de cálculo y el texto de la norma, y llegar exactamente al
mismo Nivel de Capitalización. Si necesita leer Python, la memoria falló.

Cada renglón lleva su fórmula y su fundamento legal. No hay cifra huérfana.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from acr.normativa.esquema import Registro


def _fmt(valor: Any) -> str:
    if valor is None:
        return "—"
    try:
        return f"{float(str(valor)):,.2f}"
    except (TypeError, ValueError):
        return str(valor)


def generar_memoria(
    *,
    reg: Registro,
    resultado: dict[str, Any],
    periodo: str,
    fecha_generacion: date,
    operador: str,
    commit: str,
) -> str:
    """Markdown determinista. Todo lo variable entra como parámetro."""
    filas = {f["renglon"]: f for f in resultado["formulario_anexo_u"]}
    cl = resultado["clasificacion"]
    lim = resultado["limite_activos_art13"]
    pr = resultado["personas_relacionadas_art26"]
    formulario = {r.numero: r for r in reg.formulario_computo_anexo_u_renglones()}

    lineas: list[str] = [
        f"# Memoria de cálculo — {periodo}",
        "",
        f"**Fecha de corte:** {resultado['fecha_corte']}  ",
        f"**Fecha de generación:** {fecha_generacion.isoformat()}  ",
        f"**Operador:** {operador}  ",
        f"**Registro normativo:** {resultado['registro']['version']} "
        f"(SHA-256 `{resultado['registro']['sha256'][:16]}…`)  ",
        f"**Commit del motor:** `{commit}`  ",
        f"**Hash de insumos:** `{resultado['hash_insumos'][:16]}…`",
        "",
        "> Destinatario: **Comité de Supervisión Auxiliar (FOCOOP)**. La CNBV no es",
        "> receptora directa de la información de Nivel Básico; el reporte A-2113 lo",
        "> presenta el CSA conforme a Disposiciones Art. 1 Bis 7.",
        "",
        "---",
        "",
        "## 1. Cómputo del Nivel de Capitalización",
        "",
        "Formato: Anexo U, apartado II. Cifras en "
        f"{reg.parametros.presentacion.unidad}.",
        "",
        "| # | Concepto | Fórmula | Importe |",
        "|---|---|---|---|",
    ]

    for numero in range(1, 11):
        fila = filas[numero]
        spec = formulario.get(numero)
        formula = "insumo de balanza" if spec is None or spec.formula is None else spec.formula
        lineas.append(
            f"| {numero} | {fila['concepto']} | {formula} | {_fmt(fila['importe'])} |"
        )

    factor = reg.parametros.capitalizacion.factor_requerimiento
    lineas += [
        "",
        "**Fundamentos:**",
        "",
        f"- Renglón 5, factor de requerimiento **{factor}**: "
        f"{reg.parametros.capitalizacion.fundamento_factor}.",
        f"- Renglón 9, capital neto: {reg.capital_neto.fundamento}. "
        f"Fórmula: `{reg.capital_neto.formula}`.",
        f"- Renglón 10, periodicidad y base de saldos: "
        f"{reg.parametros.capitalizacion.fundamento_computo} "
        f"({reg.parametros.capitalizacion.base_saldos}).",
        "",
        "**Conceptos que NO se deducen del capital contable**, por no estar previstos "
        "en el Art. 1 Bis 4:",
        "",
    ]
    for nd in reg.capital_neto_no_deducibles():
        lineas.append(f"- {nd.concepto}: {nd.motivo}")

    lineas += [
        "",
        "---",
        "",
        "## 2. Clasificación",
        "",
        f"**Categoría: {cl['categoria']}**",
        "",
        f"{cl['motivo']}",
        "",
        f"*Fundamento:* {cl['fundamento']}",
        "",
        "La clasificación no es función únicamente del porcentaje: depende también "
        "del apego a las reglas de elaboración y presentación de estados financieros "
        "y del historial de clasificaciones previas.",
        "",
        "**Umbrales aplicados:**",
        "",
        "| Categoría | Nivel mínimo | Nivel máximo | Fundamento |",
        "|---|---|---|---|",
    ]
    for u in reg.clasificacion.umbrales:
        minimo = "—" if u.nivel_min is None else f"{u.nivel_min}%"
        maximo = "—" if u.nivel_max is None else f"{u.nivel_max}%"
        lineas.append(f"| {u.categoria} | {minimo} | {maximo} | {u.fundamento} |")

    if cl["obligaciones_derivadas"]:
        lineas += ["", "**Obligaciones derivadas:**", ""]
        lineas += [f"- {o}" for o in cl["obligaciones_derivadas"]]

    d16 = lim["disparador_art16"]
    lineas += [
        "",
        "---",
        "",
        "## 3. Límite de activos (LRASCAP Art. 13)",
        "",
        "| Concepto | Valor |",
        "|---|---|",
        f"| Activos en UDIS | {_fmt(lim['activos_en_udis'])} |",
        f"| Límite | {_fmt(lim['limite_udis'])} |",
        f"| Excede | {'**SÍ**' if lim['excede'] else 'No'} |",
        f"| Holgura | {_fmt(lim['holgura_pct'])}% |",
        "",
    ]
    if d16["activado"]:
        lineas += [
            f"> **Disparador del Art. 16 activado.** Plazo de "
            f"{lim['plazo_solicitud_dias']} días para presentar solicitud de "
            f"autorización ante el Comité de Supervisión Auxiliar. "
            f"Fecha límite: **{d16['fecha_limite_solicitud']}**.",
            "",
            f"*Fundamento:* {d16['fundamento']}",
            "",
        ]

    lineas += [
        "---",
        "",
        "## 4. Personas relacionadas (LRASCAP Art. 26)",
        "",
        "| Concepto | Valor |",
        "|---|---|",
        f"| Exposición total | {_fmt(pr['exposicion_total'])} |",
        f"| Porcentaje del capital contable | {_fmt(pr['porcentaje'])}% |",
        f"| Límite | {_fmt(pr['limite_pct'])}% |",
        f"| Cumple | {'Sí' if pr['cumple'] else '**NO**'} |",
        f"| Umbral de exención de aprobación | {_fmt(pr['umbral_exencion'])} |",
        "",
        f"Base de cálculo: {reg.parametros.personas_relacionadas.base_calculo}. "
        f"Considerar solo saldos dispuestos subestima la exposición.",
        "",
        f"*Fundamento:* {pr['fundamento']}",
        "",
        "---",
        "",
        "## 5. Reglas del régimen de niveles I a IV que NO se aplicaron",
        "",
        "Disposiciones Art. 1, fracc. LXVIII define «Sociedad» como las SOCAP con "
        "niveles de operación I a IV. La fracc. LXIX define por separado al Nivel "
        "Básico. Todo artículo dirigido a «las Sociedades» queda fuera de alcance.",
        "",
        "| Regla | Fundamento | Motivo |",
        "|---|---|---|",
    ]
    for e in reg.excluidas():
        lineas.append(f"| {e.regla} | {e.fundamento} | {e.motivo} |")

    lineas += [
        "",
        "---",
        "",
        "## 6. Responsabilidad",
        "",
        "Este sistema es herramienta de apoyo al cálculo y a la preparación de "
        "información. **La formulación y presentación de los estados financieros "
        "básicos es responsabilidad del Consejo de Administración**, conforme a "
        "Disposiciones Art. 1 Bis 1, tercer párrafo.",
        "",
        "El cómputo aquí documentado rige para todos los efectos legales salvo que "
        "el Comité de Supervisión Auxiliar, en ejercicio de sus facultades de "
        "verificación, obtenga un cómputo distinto (Art. 1 Bis 6).",
        "",
    ]
    return "\n".join(lineas)
