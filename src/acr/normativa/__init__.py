"""Capa 0 — Registro normativo versionado.

La norma es DATO, no codigo. Ninguna constante regulatoria vive en un .py.
El cargador con validacion de esquema se implementa en ACR-02.
"""
from pathlib import Path

RUTA_REGISTRO = Path(__file__).parent / "registro_normativo_nivel_basico.yaml"
