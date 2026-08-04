"""Capa 1 — Mapeo contable: catalogo institucional -> catalogo Anexo T.

BLOQUEADO: requiere el texto real del Anexo T publicado en el DOF.
Se implementa en ACR-05. No se rellena con un catalogo plausible:
un catalogo inventado produce estados financieros con apariencia valida
y contenido falso, que es el defecto original del sistema.
"""


class AnexoNoDisponibleError(RuntimeError):
    """El anexo del DOF requerido para esta operacion no esta cargado."""


def cargar_catalogo_anexo_t() -> None:
    raise AnexoNoDisponibleError(
        "Anexo T no disponible. Instructivo de informacion financiera para SOCAP "
        "con Nivel de Operaciones Basico. Obtener del DOF antes de implementar "
        "el mapeo contable (sprint ACR-05). Prohibido sustituirlo por un catalogo "
        "construido por inferencia."
    )
