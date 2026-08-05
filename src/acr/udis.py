"""Valor de la UDI — carga desde archivo, nunca por scraping.

El valor de la UDI lo publica el Banco de México. Se carga desde un CSV
descargado, no de una consulta en vivo, por dos razones:

  1. Reproducibilidad. Un expediente debe poder reconstruirse dentro de tres
     años con los mismos insumos. Una llamada de red no es reproducible.
  2. Trazabilidad. El archivo se versiona y su hash entra al manifiesto.

Formato esperado (CSV con encabezado):  fecha,valor
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from acr.entrada import ArchivoDeEntradaInvalidoError, leer_texto


class ValorUdiNoDisponibleError(LookupError):
    """No hay valor de UDI para la fecha solicitada. Nunca interpolar."""


def cargar_udis(ruta: Path) -> dict[date, Decimal]:
    """Carga el histórico de UDIS. Falla ruidosamente ante formato inválido."""
    texto = leer_texto(ruta)
    valores: dict[date, Decimal] = {}
    for numero, linea in enumerate(texto.splitlines(), 1):
        limpia = linea.strip()
        if not limpia or (numero == 1 and limpia.lower().startswith("fecha")):
            continue
        partes = [p.strip() for p in limpia.split(",")]
        if len(partes) != 2:
            raise ArchivoDeEntradaInvalidoError(
                f"{ruta.name}, línea {numero}: se esperaban dos columnas "
                f"(fecha,valor), se encontraron {len(partes)}."
            )
        try:
            fecha = date.fromisoformat(partes[0])
            valor = Decimal(partes[1])
        except (ValueError, InvalidOperation) as exc:
            raise ArchivoDeEntradaInvalidoError(
                f"{ruta.name}, línea {numero}: fecha o valor inválido ({limpia!r}). "
                f"Formato esperado: AAAA-MM-DD,0.000000"
            ) from exc
        if valor <= Decimal(0):
            raise ArchivoDeEntradaInvalidoError(
                f"{ruta.name}, línea {numero}: el valor de la UDI debe ser positivo."
            )
        valores[fecha] = valor
    if not valores:
        raise ArchivoDeEntradaInvalidoError(f"{ruta.name} no contiene valores de UDI.")
    return valores


def valor_udi_en(valores: dict[date, Decimal], fecha: date) -> Decimal:
    """Valor exacto de la fecha. No interpola ni toma el más cercano.

    Interpolar produciría un valor que Banco de México nunca publicó, dentro de
    un expediente que se firma.
    """
    if fecha not in valores:
        disponibles = sorted(valores)
        raise ValorUdiNoDisponibleError(
            f"No hay valor de UDI para {fecha.isoformat()}. El archivo cubre de "
            f"{disponibles[0].isoformat()} a {disponibles[-1].isoformat()}. "
            f"Descargar el valor de esa fecha del Banco de México; el sistema no "
            f"interpola ni usa el valor más cercano."
        )
    return valores[fecha]
