#!/usr/bin/env python3
"""Compuerta D — Cero literales normativos en codigo Python.

El defecto raiz del sistema original no fue un bug: fue que cada umbral
regulatorio vivia dentro de un `if`. Cuando la norma cambia (los Anexos T y U
se sustituyen el 2027-01-01) hay que reescribir Python y volver a probar todo.

Esta compuerta escanea los .py y falla si encuentra una constante regulatoria
en un archivo que no este declarado en tools/deuda_literales.txt.

MECANISMO DE RATCHET: la lista de deuda solo puede encogerse. Cada entrada
lleva el sprint en que vence. Si el sprint actual es posterior al de
vencimiento, la compuerta falla aunque el archivo este en la lista.

AMBITO: se escanea src/ y tools/. Las pruebas quedan FUERA por diseno, no por
comodidad. En src/ un umbral literal ES comportamiento y esta prohibido. En
tests/ un umbral literal es una afirmacion independiente de lo que dice la
norma: si las pruebas de frontera leyeran los umbrales del mismo YAML que
validan, pasarian aunque alguien corrompiera el registro. Las pruebas son el
contrapeso al registro y por eso deben llevar los valores a mano.

Uso:
    python tools/gate_literales.py                 # sprint actual desde el archivo
    python tools/gate_literales.py --sprint ACR-03
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_DEUDA = Path(__file__).resolve().parent / "deuda_literales.txt"

# Constantes regulatorias que NO pueden aparecer en un .py.
# Cada patron lleva el fundamento que lo hace normativo, no arbitrario.
PATRONES: dict[str, str] = {
    r"\b0\.08\b": "Factor de requerimiento — Disposiciones Art. 1 Bis 3",
    r"\b2[_']?500[_,']?000\b": "Limite de activos en UDIS — LRASCAP Art. 13",
    r"\b100[_']?000\b": "Umbral de exencion personas relacionadas — LRASCAP Art. 26",
    r"\b2500000\b": "Limite de activos en UDIS — LRASCAP Art. 13",
    r"Decimal\(\s*[\"']1?[0-9]{2}[\"']\s*\)": "Umbral de categoria — LRASCAP Art. 15",
    r"\b0\.10\b|\b0\.02\b": "Porcentaje de limite — LRASCAP Art. 26",
    r"\b150\b(?!\s*dias\s*naturales)": "Umbral categoria A / plazo Art. 16",
}

ORDEN_SPRINTS = [
    "ACR-01", "ACR-02", "ACR-03", "ACR-04",
    "ACR-05", "ACR-06", "ACR-07", "ACR-08",
]


def leer_deuda() -> dict[str, str]:
    """Devuelve {ruta_relativa: sprint_de_vencimiento}."""
    if not ARCHIVO_DEUDA.exists():
        return {}
    deuda: dict[str, str] = {}
    for linea in ARCHIVO_DEUDA.read_text(encoding="utf-8").splitlines():
        limpia = linea.split("#")[0].strip()
        if not limpia:
            continue
        partes = [p.strip() for p in limpia.split("|")]
        if len(partes) != 2:
            raise SystemExit(f"Formato invalido en deuda_literales.txt: {linea!r}")
        deuda[partes[0]] = partes[1]
    return deuda


DIRECTORIOS_ESCANEADOS = ("src", "tools")
EXCLUIR = {".venv", "venv", "__pycache__", ".git", "build", "dist"}


def archivos_python() -> list[Path]:
    """Solo codigo de produccion. Ver nota de AMBITO en el docstring del modulo."""
    encontrados: list[Path] = []
    for carpeta in DIRECTORIOS_ESCANEADOS:
        base = RAIZ / carpeta
        if not base.exists():
            continue
        encontrados.extend(
            p for p in base.rglob("*.py") if not EXCLUIR & set(p.relative_to(RAIZ).parts)
        )
    return sorted(encontrados)


def escanear(ruta: Path) -> list[tuple[int, str, str]]:
    hallazgos: list[tuple[int, str, str]] = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        codigo = linea.split("#")[0]
        if not codigo.strip():
            continue
        for patron, fundamento in PATRONES.items():
            if re.search(patron, codigo):
                hallazgos.append((n, codigo.strip(), fundamento))
                break
    return hallazgos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sprint", default="ACR-01", choices=ORDEN_SPRINTS)
    args = parser.parse_args()
    sprint_actual = ORDEN_SPRINTS.index(args.sprint)

    deuda = leer_deuda()
    fallos: list[str] = []
    vencidos: list[str] = []

    for ruta in archivos_python():
        rel = ruta.relative_to(RAIZ).as_posix()
        if rel.startswith("tools/gate_literales.py"):
            continue  # esta herramienta declara los patrones por definicion
        hallazgos = escanear(ruta)
        if not hallazgos:
            continue
        if rel in deuda:
            vence = ORDEN_SPRINTS.index(deuda[rel])
            if sprint_actual > vence:
                vencidos.append(
                    f"  {rel} — deuda vencida en {deuda[rel]}, sprint actual {args.sprint}"
                )
            continue
        for n, linea, fundamento in hallazgos:
            fallos.append(f"  {rel}:{n}\n      {linea}\n      -> {fundamento}")

    if vencidos:
        print("COMPUERTA D FALLO — deuda de literales vencida:")
        print("\n".join(vencidos))
        print("\nMover esas constantes al registro normativo YAML.")
        return 1

    if fallos:
        print("COMPUERTA D FALLO — constantes normativas en codigo Python:")
        print("\n".join(fallos))
        print(
            "\nToda constante regulatoria vive en "
            "src/acr/normativa/registro_normativo_nivel_basico.yaml.\n"
            "Si es deuda aceptada temporalmente, declararla en "
            "tools/deuda_literales.txt con su sprint de vencimiento."
        )
        return 1

    pendientes = len(deuda)
    print(f"COMPUERTA D OK — cero literales fuera del registro. Deuda declarada: {pendientes}")
    for rel, vence in sorted(deuda.items()):
        print(f"    {rel} (vence en {vence})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
