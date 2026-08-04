"""Pruebas de estructura y de purga.

Verifican que los modulos eliminados en ACR-01 no regresen y que los modulos
bloqueados por falta de anexos fallen ruidosamente en vez de inventar datos.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Modulos purgados en ACR-01. Reintroducirlos es una regresion normativa,
# no solo tecnica: aplican el regimen de niveles I-IV a Nivel Basico.
PURGADOS = [
    "src/acr/motor/liquidez.py",
    "src/acr/motor/riesgo_comun.py",
    "src/acr/motor/provisiones_anexo_c.py",
    "src/acr/salida/acuse_simulado.py",
]


@pytest.mark.parametrize("ruta", PURGADOS)
def test_modulo_purgado_no_regresa(ruta: str) -> None:
    assert not (RAIZ / ruta).exists(), (
        f"{ruta} pertenece al regimen de niveles I-IV (Disposiciones Art. 1, "
        "fracc. LXVIII) y no aplica a Nivel Basico."
    )


def test_mapeo_bloqueado_falla_ruidosamente() -> None:
    """Sin el Anexo T real, el mapeo debe fallar, no devolver un catalogo plausible."""
    from acr.mapeo import AnexoNoDisponibleError, cargar_catalogo_anexo_t

    with pytest.raises(AnexoNoDisponibleError, match="Anexo T no disponible"):
        cargar_catalogo_anexo_t()


def test_registro_normativo_presente() -> None:
    from acr.normativa import RUTA_REGISTRO

    assert RUTA_REGISTRO.exists()
    texto = RUTA_REGISTRO.read_text(encoding="utf-8")
    assert "alertas_vigencia" in texto
    assert "excluidas_del_regimen_basico" in texto


MODULOS_PROHIBIDOS_EN_MOTOR = {
    "os", "io", "pathlib", "datetime", "time", "random",
    "requests", "urllib", "sqlite3", "pandas", "openpyxl",
}


def test_motor_no_hace_io() -> None:
    """El motor debe ser puro: sin I/O, sin reloj, sin aleatoriedad.

    Se analiza el AST, no el texto: el docstring del motor menciona
    datetime.now() precisamente para prohibirlo, y una busqueda textual
    lo reportaria como violacion.
    """
    arbol = ast.parse((RAIZ / "src/acr/motor/capitalizacion.py").read_text(encoding="utf-8"))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])

    prohibidos = importados & MODULOS_PROHIBIDOS_EN_MOTOR
    assert not prohibidos, (
        f"El motor importa modulos que rompen su pureza: {sorted(prohibidos)}. "
        "Todo lo temporal y todo I/O entra como parametro."
    )


def test_motor_no_llama_funciones_impuras() -> None:
    """Ninguna llamada a open() ni a now() dentro del motor."""
    arbol = ast.parse((RAIZ / "src/acr/motor/capitalizacion.py").read_text(encoding="utf-8"))
    llamadas: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            if isinstance(nodo.func, ast.Name):
                llamadas.add(nodo.func.id)
            elif isinstance(nodo.func, ast.Attribute):
                llamadas.add(nodo.func.attr)

    impuras = llamadas & {"open", "now", "today", "read_excel", "read_csv", "connect"}
    assert not impuras, f"El motor llama funciones impuras: {sorted(impuras)}"
