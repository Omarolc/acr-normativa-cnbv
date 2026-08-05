"""Capa 3 — Persistencia. El sistema adquiere memoria entre periodos.

Sin historial persistido el Art. 15, fracc. III (dos clasificaciones
consecutivas en categoría C derivan en D) es inimplementable: una calculadora
de un disparo no puede saber qué pasó el trimestre anterior.

SEPARACIÓN DE RESPONSABILIDADES
-------------------------------
Este módulo hace I/O; el motor no. El motor recibe `historial_categorias` como
parámetro y sigue siendo puro. Aquí se decide de dónde sale ese historial.

DETERMINISMO
------------
Ningún timestamp automático. La fecha de corte es la clave y entra como dato.
Dos ejecuciones de la misma secuencia producen la misma base.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

ESQUEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS esquema (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS periodos (
    fecha_corte       TEXT PRIMARY KEY,
    nivel_pct         TEXT,
    categoria         TEXT NOT NULL,
    motivo            TEXT NOT NULL,
    fundamento        TEXT NOT NULL,
    hash_insumos      TEXT NOT NULL,
    version_registro  TEXT NOT NULL,
    sha256_registro   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activos_udi (
    fecha_corte           TEXT PRIMARY KEY,
    activos_totales       TEXT NOT NULL,
    valor_udi             TEXT NOT NULL,
    activos_en_udis       TEXT NOT NULL,
    excede                INTEGER NOT NULL,
    fecha_limite_art16    TEXT
);

CREATE TABLE IF NOT EXISTS personas_relacionadas (
    fecha_corte     TEXT PRIMARY KEY,
    exposicion      TEXT NOT NULL,
    porcentaje      TEXT,
    cumple          INTEGER NOT NULL
);
"""


class PeriodoDuplicadoError(ValueError):
    """Ya existe un periodo registrado para esa fecha de corte.

    Sobrescribir en silencio destruiría la evidencia del cómputo anterior, que
    forma parte del expediente de auditoría.
    """


class EsquemaIncompatibleError(RuntimeError):
    """La base fue creada por otra versión del sistema."""


@dataclass(frozen=True)
class PeriodoRegistrado:
    fecha_corte: date
    nivel_pct: Decimal | None
    categoria: str
    motivo: str
    fundamento: str
    hash_insumos: str
    version_registro: str
    sha256_registro: str


class Almacen:
    """Repositorio de periodos. Usar como context manager."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        self._con: sqlite3.Connection | None = None

    def __enter__(self) -> Almacen:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.ruta)
        self._con.execute("PRAGMA foreign_keys = ON")
        with closing(self._con.cursor()) as cur:
            cur.executescript(_DDL)
            cur.execute("SELECT version FROM esquema")
            fila = cur.fetchone()
            if fila is None:
                cur.execute("INSERT INTO esquema (version) VALUES (?)", (ESQUEMA_VERSION,))
            elif fila[0] != ESQUEMA_VERSION:
                raise EsquemaIncompatibleError(
                    f"La base {self.ruta} usa esquema v{fila[0]}; este sistema espera "
                    f"v{ESQUEMA_VERSION}. Migrar antes de continuar."
                )
        self._con.commit()
        return self

    def __exit__(self, *_: object) -> None:
        if self._con is not None:
            self._con.commit()
            self._con.close()
            self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            raise RuntimeError("Almacen usado fuera de su context manager.")
        return self._con

    # -- Periodos --------------------------------------------------------------

    def registrar_periodo(
        self,
        *,
        fecha_corte: date,
        nivel_pct: Decimal | None,
        categoria: str,
        motivo: str,
        fundamento: str,
        hash_insumos: str,
        version_registro: str,
        sha256_registro: str,
        sobrescribir: bool = False,
    ) -> None:
        clave = fecha_corte.isoformat()
        with closing(self.con.cursor()) as cur:
            cur.execute("SELECT 1 FROM periodos WHERE fecha_corte = ?", (clave,))
            if cur.fetchone() is not None and not sobrescribir:
                raise PeriodoDuplicadoError(
                    f"Ya existe un cómputo registrado para {clave}. Sobrescribirlo "
                    f"destruiría evidencia del expediente. Use sobrescribir=True de "
                    f"forma consciente si se trata de una corrección."
                )
            cur.execute(
                "INSERT OR REPLACE INTO periodos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    clave,
                    None if nivel_pct is None else str(nivel_pct),
                    categoria,
                    motivo,
                    fundamento,
                    hash_insumos,
                    version_registro,
                    sha256_registro,
                ),
            )
        self.con.commit()

    def periodos(self) -> list[PeriodoRegistrado]:
        """Todos los periodos en orden cronológico ascendente."""
        with closing(self.con.cursor()) as cur:
            cur.execute("SELECT * FROM periodos ORDER BY fecha_corte ASC")
            return [
                PeriodoRegistrado(
                    fecha_corte=date.fromisoformat(f[0]),
                    nivel_pct=None if f[1] is None else Decimal(f[1]),
                    categoria=f[2],
                    motivo=f[3],
                    fundamento=f[4],
                    hash_insumos=f[5],
                    version_registro=f[6],
                    sha256_registro=f[7],
                )
                for f in cur.fetchall()
            ]

    def historial_categorias(self, anterior_a: date) -> list[str]:
        """Categorías previas en orden cronológico ascendente.

        Es el insumo del Art. 15, fracc. III. Se excluye la fecha consultada:
        un periodo no puede formar parte de su propio historial.
        """
        with closing(self.con.cursor()) as cur:
            cur.execute(
                "SELECT categoria FROM periodos WHERE fecha_corte < ? "
                "ORDER BY fecha_corte ASC",
                (anterior_a.isoformat(),),
            )
            return [f[0] for f in cur.fetchall()]

    # -- Activos y UDIS --------------------------------------------------------

    def registrar_activos(
        self,
        *,
        fecha_corte: date,
        activos_totales: Decimal,
        valor_udi: Decimal,
        activos_en_udis: Decimal,
        excede: bool,
        fecha_limite_art16: date | None,
    ) -> None:
        with closing(self.con.cursor()) as cur:
            cur.execute(
                "INSERT OR REPLACE INTO activos_udi VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fecha_corte.isoformat(),
                    str(activos_totales),
                    str(valor_udi),
                    str(activos_en_udis),
                    int(excede),
                    None if fecha_limite_art16 is None else fecha_limite_art16.isoformat(),
                ),
            )
        self.con.commit()

    def excesos_art13(self) -> list[tuple[date, Decimal, date | None]]:
        """Cortes en los que se rebasó el límite del Art. 13, con su fecha límite."""
        with closing(self.con.cursor()) as cur:
            cur.execute(
                "SELECT fecha_corte, activos_en_udis, fecha_limite_art16 "
                "FROM activos_udi WHERE excede = 1 ORDER BY fecha_corte ASC"
            )
            return [
                (
                    date.fromisoformat(f[0]),
                    Decimal(f[1]),
                    None if f[2] is None else date.fromisoformat(f[2]),
                )
                for f in cur.fetchall()
            ]

    # -- Personas relacionadas -------------------------------------------------

    def registrar_relacionadas(
        self,
        *,
        fecha_corte: date,
        exposicion: Decimal,
        porcentaje: Decimal | None,
        cumple: bool,
    ) -> None:
        with closing(self.con.cursor()) as cur:
            cur.execute(
                "INSERT OR REPLACE INTO personas_relacionadas VALUES (?, ?, ?, ?)",
                (
                    fecha_corte.isoformat(),
                    str(exposicion),
                    None if porcentaje is None else str(porcentaje),
                    int(cumple),
                ),
            )
        self.con.commit()

    def incumplimientos_art26(self) -> list[tuple[date, Decimal | None]]:
        with closing(self.con.cursor()) as cur:
            cur.execute(
                "SELECT fecha_corte, porcentaje FROM personas_relacionadas "
                "WHERE cumple = 0 ORDER BY fecha_corte ASC"
            )
            return [
                (date.fromisoformat(f[0]), None if f[1] is None else Decimal(f[1]))
                for f in cur.fetchall()
            ]
