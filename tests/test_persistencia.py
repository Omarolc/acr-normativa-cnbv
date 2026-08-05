"""Persistencia e historial. El sistema adquiere memoria entre periodos.

La prueba central es la secuencia de seis trimestres: sin base de datos, el
Art. 15, fracc. III es inimplementable.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from acr.cli.principal import calcular, main
from acr.persistencia import (
    Almacen,
    EsquemaIncompatibleError,
    PeriodoDuplicadoError,
)

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"


def _caso(nivel_objetivo: str, fecha: str) -> dict[str, object]:
    """Caso con nivel de capitalizacion dirigido y cifras coherentes."""
    base = json.loads(CASO.read_text(encoding="utf-8"))
    cartera_neta = Decimal(base["cartera_vigente"]) + Decimal(
        base["cartera_vencida"]
    ) - Decimal(base["estimacion_preventiva"])
    requerimiento = cartera_neta * Decimal("0.08")
    capital = requerimiento * Decimal(nivel_objetivo) / Decimal(100)
    base["capital_contable"] = str(capital + Decimal(base["certificados_no_elegibles"]))
    base["fecha_corte"] = fecha
    return base


# =============================================================================
# LA PRUEBA CENTRAL DEL SPRINT
# =============================================================================


def test_seis_trimestres_reproducen_el_escalamiento_c_c_d(tmp_path: Path) -> None:
    """Art. 15, fracc. III: dos clasificaciones consecutivas en C derivan en D.

    Sin historial persistido esta regla no se puede implementar: una calculadora
    de un disparo no sabe que paso el trimestre anterior.
    """
    base = tmp_path / "acr.db"
    secuencia = [
        ("2026-03-31", "200", "A"),   # holgada
        ("2026-06-30", "120", "B"),   # se deteriora
        ("2026-09-30", "80", "C"),    # primera C
        ("2026-12-31", "75", "C"),    # segunda C consecutiva
        ("2027-03-31", "90", "D"),    # bloqueado por vigencia, se prueba aparte
    ]
    resultados: list[tuple[str, str]] = []

    for fecha, nivel, _ in secuencia[:4]:
        with Almacen(base) as almacen:
            historial = almacen.historial_categorias(date.fromisoformat(fecha))
            r = calcular(_caso(nivel, fecha), historial=historial)
            almacen.registrar_periodo(
                fecha_corte=date.fromisoformat(fecha),
                nivel_pct=Decimal("0"),
                categoria=r["clasificacion"]["categoria"],
                motivo=r["clasificacion"]["motivo"],
                fundamento=r["clasificacion"]["fundamento"],
                hash_insumos=r["hash_insumos"],
                version_registro=r["registro"]["version"],
                sha256_registro=r["registro"]["sha256"],
            )
            resultados.append((fecha, r["clasificacion"]["categoria"]))

    assert [c for _, c in resultados] == ["A", "B", "C", "C"]

    # Quinto trimestre: con historial [A, B, C, C] la categoria es D por el
    # Art. 15 fracc. III, sin importar que el nivel haya mejorado a 90%.
    with Almacen(base) as almacen:
        historial = almacen.historial_categorias(date(2027, 3, 31))
        assert historial == ["A", "B", "C", "C"]
        r = calcular(_caso("90", "2026-09-30"), historial=historial)
        assert r["clasificacion"]["categoria"] == "D"
        assert "fracc. III" in r["clasificacion"]["fundamento"]
        assert r["clasificacion"]["debe_abstenerse_captacion"] is True


def test_el_historial_excluye_la_fecha_consultada(tmp_path: Path) -> None:
    """Un periodo no forma parte de su propio historial."""
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        a.registrar_periodo(
            fecha_corte=date(2026, 6, 30), nivel_pct=Decimal("80"), categoria="C",
            motivo="m", fundamento="f", hash_insumos="h", version_registro="v",
            sha256_registro="s",
        )
        assert a.historial_categorias(date(2026, 6, 30)) == []
        assert a.historial_categorias(date(2026, 9, 30)) == ["C"]


def test_c_no_consecutivas_no_escalan(tmp_path: Path) -> None:
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        for fecha, cat in [("2026-03-31", "C"), ("2026-06-30", "B"), ("2026-09-30", "C")]:
            a.registrar_periodo(
                fecha_corte=date.fromisoformat(fecha), nivel_pct=Decimal("80"),
                categoria=cat, motivo="m", fundamento="f", hash_insumos="h",
                version_registro="v", sha256_registro="s",
            )
        historial = a.historial_categorias(date(2026, 12, 31))
    assert historial == ["C", "B", "C"]
    r = calcular(_caso("200", "2026-12-31"), historial=historial)
    assert r["clasificacion"]["categoria"] == "A"


def test_no_sobrescribe_un_periodo_sin_permiso_explicito(tmp_path: Path) -> None:
    """Sobrescribir destruiria evidencia del expediente."""
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        kw = {
            "fecha_corte": date(2026, 6, 30), "nivel_pct": Decimal("80"),
            "categoria": "C", "motivo": "m", "fundamento": "f", "hash_insumos": "h",
            "version_registro": "v", "sha256_registro": "s",
        }
        a.registrar_periodo(**kw)  # type: ignore[arg-type]
        with pytest.raises(PeriodoDuplicadoError, match="destruiría evidencia"):
            a.registrar_periodo(**kw)  # type: ignore[arg-type]
        a.registrar_periodo(**kw, sobrescribir=True)  # type: ignore[arg-type]
        assert len(a.periodos()) == 1


def test_esquema_incompatible_aborta(tmp_path: Path) -> None:
    import sqlite3

    base = tmp_path / "vieja.db"
    con = sqlite3.connect(base)
    con.executescript("CREATE TABLE esquema (version INTEGER); INSERT INTO esquema VALUES (99)")
    con.commit()
    con.close()
    with pytest.raises(EsquemaIncompatibleError, match="esquema v99"), Almacen(base):
        pass


def test_uso_fuera_del_context_manager_aborta(tmp_path: Path) -> None:
    a = Almacen(tmp_path / "x.db")
    with pytest.raises(RuntimeError, match="fuera de su context manager"):
        _ = a.con


def test_registra_excesos_del_art13_y_su_fecha_limite(tmp_path: Path) -> None:
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        a.registrar_activos(
            fecha_corte=date(2026, 6, 30), activos_totales=Decimal(30_000_000),
            valor_udi=Decimal("8.52"), activos_en_udis=Decimal("3521126.76"),
            excede=True, fecha_limite_art16=date(2026, 11, 27),
        )
        a.registrar_activos(
            fecha_corte=date(2026, 3, 31), activos_totales=Decimal(1_000_000),
            valor_udi=Decimal("8.50"), activos_en_udis=Decimal("117647.06"),
            excede=False, fecha_limite_art16=None,
        )
        excesos = a.excesos_art13()
    assert len(excesos) == 1
    assert excesos[0][0] == date(2026, 6, 30)
    assert excesos[0][2] == date(2026, 11, 27)


def test_registra_incumplimientos_del_art26(tmp_path: Path) -> None:
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        a.registrar_relacionadas(
            fecha_corte=date(2026, 6, 30), exposicion=Decimal(550_000),
            porcentaje=Decimal("55.00"), cumple=False,
        )
        a.registrar_relacionadas(
            fecha_corte=date(2026, 3, 31), exposicion=Decimal(50_000),
            porcentaje=Decimal("5.00"), cumple=True,
        )
        incumple = a.incumplimientos_art26()
    assert [f.isoformat() for f, _ in incumple] == ["2026-06-30"]


def test_periodo_sin_requerimiento_guarda_nivel_nulo(tmp_path: Path) -> None:
    base = tmp_path / "acr.db"
    with Almacen(base) as a:
        a.registrar_periodo(
            fecha_corte=date(2026, 6, 30), nivel_pct=None, categoria="A",
            motivo="sin cartera", fundamento="f", hash_insumos="h",
            version_registro="v", sha256_registro="s",
        )
        assert a.periodos()[0].nivel_pct is None


# =============================================================================
# CLI
# =============================================================================


def test_cli_registrar_e_historial(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    base = tmp_path / "acr.db"
    caso = tmp_path / "caso.json"
    caso.write_text(json.dumps(_caso("80", "2026-06-30")), encoding="utf-8")

    assert main(["registrar", "--caso", str(caso), "--base", str(base)]) == 0
    salida = capsys.readouterr().out
    assert "categoria C" in salida

    assert main(["historial", "--base", str(base)]) == 0
    assert "2026-06-30" in capsys.readouterr().out


def test_cli_historial_vacio(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["historial", "--base", str(tmp_path / "v.db")]) == 0
    assert "Sin periodos" in capsys.readouterr().out


def test_cli_registrar_duplicado_falla(tmp_path: Path) -> None:
    base = tmp_path / "acr.db"
    caso = tmp_path / "caso.json"
    caso.write_text(json.dumps(_caso("80", "2026-06-30")), encoding="utf-8")
    main(["registrar", "--caso", str(caso), "--base", str(base)])
    with pytest.raises(PeriodoDuplicadoError):
        main(["registrar", "--caso", str(caso), "--base", str(base)])
    assert main(["registrar", "--caso", str(caso), "--base", str(base), "--sobrescribir"]) == 0


def test_cli_historial_reporta_art13_y_art26(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = tmp_path / "acr.db"
    caso_dict = _caso("80", "2026-06-30")
    caso_dict["activos_totales"] = 40_000_000          # excede el limite del Art. 13
    caso_dict["relacionadas_dispuestos"] = 900_000     # excede el limite del Art. 26
    caso = tmp_path / "caso.json"
    caso.write_text(json.dumps(caso_dict), encoding="utf-8")
    main(["registrar", "--caso", str(caso), "--base", str(base)])
    capsys.readouterr()
    main(["historial", "--base", str(base)])
    salida = capsys.readouterr().out
    assert "EXCESOS DEL LIMITE DEL ART. 13" in salida
    assert "INCUMPLIMIENTOS DEL ART. 26" in salida
