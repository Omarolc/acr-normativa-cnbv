"""Expediente de auditoria. El activo defendible ante verificacion del CSA.

Criterio de cierre de ACR-04: dos ejecuciones del mismo periodo generan
manifiestos con hashes identicos, y la memoria permite a un tercero
reconstruir el nivel de capitalizacion sin abrir el codigo.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from acr import __version__
from acr.cli.principal import calcular, main
from acr.expediente import (
    SUBCARPETAS,
    describir_insumo,
    encadenar,
    generar_expediente,
    verificar_cadena,
)
from acr.expediente.bitacora import EntradaBitacora
from acr.normativa import cargar_registro, hash_registro

RAIZ = Path(__file__).resolve().parent.parent
CASO = RAIZ / "tests" / "fixtures" / "caso_base.json"
REG = cargar_registro()


def _generar(destino: Path, operador: str = "Operador Prueba"):
    return generar_expediente(
        reg=REG,
        resultado=calcular(json.loads(CASO.read_text(encoding="utf-8"))),
        destino=destino,
        periodo="2026-Q2",
        fecha_generacion=date(2026, 8, 4),
        operador=operador,
        version_motor=__version__,
        commit="037f8a1",
        sha256_registro=hash_registro(),
        rutas_insumos=[CASO],
    )


# =============================================================================
# CRITERIO DE CIERRE: DETERMINISMO
# =============================================================================


def test_dos_ejecuciones_producen_expedientes_identicos(tmp_path: Path) -> None:
    """Si el expediente cambiara entre corridas, no probaria nada."""
    a = _generar(tmp_path / "a")
    b = _generar(tmp_path / "b")

    for ruta_a, ruta_b in zip(a.archivos, b.archivos, strict=True):
        assert ruta_a.name == ruta_b.name
        assert (
            hashlib.sha256(ruta_a.read_bytes()).hexdigest()
            == hashlib.sha256(ruta_b.read_bytes()).hexdigest()
        ), f"{ruta_a.name} difiere entre ejecuciones"


def test_el_expediente_no_lee_el_reloj(tmp_path: Path) -> None:
    """La fecha de generacion entra como parametro. Con fechas distintas el
    manifiesto cambia; con la misma fecha es identico."""
    a = _generar(tmp_path / "a")
    distinto = generar_expediente(
        reg=REG,
        resultado=calcular(json.loads(CASO.read_text(encoding="utf-8"))),
        destino=tmp_path / "c",
        periodo="2026-Q2",
        fecha_generacion=date(2026, 9, 1),
        operador="Operador Prueba",
        version_motor=__version__,
        commit="037f8a1",
        sha256_registro=hash_registro(),
        rutas_insumos=[CASO],
    )
    assert a.manifiesto["expediente"]["fecha_generacion"] != (
        distinto.manifiesto["expediente"]["fecha_generacion"]
    )


# =============================================================================
# ESTRUCTURA CORREGIDA
# =============================================================================


def test_estructura_de_carpetas(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    for sub in SUBCARPETAS:
        assert (exp.raiz / sub).is_dir()


def test_no_existe_carpeta_de_acuse_simulado(tmp_path: Path) -> None:
    """Un acuse falso en un expediente regulatorio es un riesgo, no una feature."""
    exp = _generar(tmp_path)
    nombres = [p.name.lower() for p in exp.raiz.rglob("*")]
    assert not any("acuse" in n for n in nombres)


def test_el_manifiesto_de_entrega_se_declara_como_no_acuse(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    entrega = json.loads((exp.raiz / "manifiesto_de_entrega.json").read_text(encoding="utf-8"))
    assert "NO es un acuse de recibo" in entrega["advertencia"]
    assert "A-2113" in entrega["nota_a2113"]
    assert entrega["destinatario"] == REG.ambito.supervisor_directo


def test_el_destinatario_nunca_es_la_cnbv(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    entrega = json.loads((exp.raiz / "manifiesto_de_entrega.json").read_text(encoding="utf-8"))
    assert "CNBV" not in entrega["destinatario"]
    assert "Supervisión Auxiliar" in exp.manifiesto["entidad"]["destinatario"]


def test_no_se_genera_el_a2113(tmp_path: Path) -> None:
    """Lo presenta el CSA a la CNBV, no la cooperativa (Art. 1 Bis 7)."""
    exp = _generar(tmp_path)
    assert not any("2113" in p.name for p in exp.raiz.rglob("*"))


def test_carpetas_bloqueadas_declaran_su_fundamento(tmp_path: Path) -> None:
    """Los formatos no se rellenan con una aproximacion: se declaran pendientes."""
    exp = _generar(tmp_path)
    for sub in SUBCARPETAS[:5]:
        texto = (exp.raiz / sub / "LEEME.md").read_text(encoding="utf-8")
        assert "Fundamento:" in texto
        assert "ACR-07" in texto


# =============================================================================
# MANIFIESTO
# =============================================================================


def test_manifiesto_registra_hash_de_cada_insumo(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    insumo = exp.manifiesto["insumos"][0]
    assert insumo["sha256"] == hashlib.sha256(CASO.read_bytes()).hexdigest()
    assert insumo["bytes"] == len(CASO.read_bytes())


def test_manifiesto_registra_version_y_hash_del_registro(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    v = exp.manifiesto["versiones"]
    assert v["registro_normativo"] == REG.meta.version_registro
    assert v["sha256_registro"] == hash_registro()
    assert v["commit"] == "037f8a1"


def test_manifiesto_incluye_clausula_de_responsabilidad(tmp_path: Path) -> None:
    """Art. 1 Bis 1: la formulacion de EEFF es del Consejo de Administracion."""
    exp = _generar(tmp_path)
    assert "Consejo de Administración" in exp.manifiesto["responsabilidad"]
    assert "1 Bis 1" in exp.manifiesto["responsabilidad"]


def test_insumo_inexistente_falla(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="insumo declarado"):
        describir_insumo(tmp_path / "no_existe.json")


# =============================================================================
# BITACORA ENCADENADA
# =============================================================================


def test_cadena_valida(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    resultado = calcular(json.loads(CASO.read_text(encoding="utf-8")))
    assert verificar_cadena(exp.bitacora, semilla=resultado["hash_insumos"])


def test_alterar_una_entrada_rompe_la_cadena() -> None:
    """Es lo que separa un log de evidencia."""
    cadena = encadenar([("a", "1"), ("b", "2"), ("c", "3")], semilla="s")
    assert verificar_cadena(cadena, "s")
    alterada = list(cadena)
    alterada[1] = EntradaBitacora(
        secuencia=2, evento="b", detalle="ALTERADO",
        hash_previo=cadena[1].hash_previo, hash=cadena[1].hash,
    )
    assert verificar_cadena(alterada, "s") is False


def test_reordenar_rompe_la_cadena() -> None:
    cadena = encadenar([("a", "1"), ("b", "2")], semilla="s")
    assert verificar_cadena([cadena[1], cadena[0]], "s") is False


def test_semilla_distinta_invalida_la_cadena() -> None:
    cadena = encadenar([("a", "1")], semilla="s")
    assert verificar_cadena(cadena, "otra") is False


def test_bitacora_vacia_rechazada() -> None:
    with pytest.raises(ValueError, match="no puede estar vacía"):
        encadenar([], semilla="s")
    assert verificar_cadena([], "s") is False


# =============================================================================
# MEMORIA DE CALCULO
# =============================================================================


def test_memoria_lleva_los_diez_renglones_con_formula(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    for numero in range(1, 11):
        assert f"| {numero} |" in memoria
    assert "(1) + (2) - (3)" in memoria
    assert "[(9) / (5)] * 100" in memoria


def test_memoria_documenta_lo_que_no_se_dedujo(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "activos_intangibles" in memoria
    assert "creditos_a_contraventores" in memoria


def test_memoria_documenta_las_reglas_fuera_de_alcance(tmp_path: Path) -> None:
    """Ante una verificacion, decir por que NO se aplico algo vale tanto como
    decir por que si."""
    exp = _generar(tmp_path)
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "fracc. LXVIII" in memoria
    assert "Art. 44" in memoria
    assert "193 Bis" in memoria


def test_memoria_incluye_clausula_de_responsabilidad(tmp_path: Path) -> None:
    exp = _generar(tmp_path)
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "responsabilidad del Consejo de Administración" in memoria
    assert "Art. 1 Bis 6" in memoria


def test_memoria_reporta_el_disparador_del_art16(tmp_path: Path) -> None:
    caso = json.loads(CASO.read_text(encoding="utf-8"))
    caso["activos_totales"] = 40_000_000
    exp = generar_expediente(
        reg=REG, resultado=calcular(caso), destino=tmp_path, periodo="2026-Q2",
        fecha_generacion=date(2026, 8, 4), operador="op", version_motor=__version__,
        commit="c", sha256_registro=hash_registro(), rutas_insumos=[CASO],
    )
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "Disparador del Art. 16 activado" in memoria
    assert "Fecha límite" in memoria or "fecha límite" in memoria


def test_memoria_marca_incumplimiento_del_art26(tmp_path: Path) -> None:
    caso = json.loads(CASO.read_text(encoding="utf-8"))
    caso["relacionadas_dispuestos"] = 900_000
    exp = generar_expediente(
        reg=REG, resultado=calcular(caso), destino=tmp_path, periodo="2026-Q2",
        fecha_generacion=date(2026, 8, 4), operador="op", version_motor=__version__,
        commit="c", sha256_registro=hash_registro(), rutas_insumos=[CASO],
    )
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "| Cumple | **NO** |" in memoria


# =============================================================================
# CLI
# =============================================================================


def test_cli_expediente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    codigo = main([
        "expediente", "--caso", str(CASO), "--salida", str(tmp_path),
        "--periodo", "2026-Q2", "--operador", "Omar Corona",
        "--fecha-generacion", "2026-08-04", "--commit", "037f8a1",
    ])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "Expediente generado" in salida
    assert "5 entradas encadenadas" in salida
    generados = list(tmp_path.rglob("manifiesto.json"))
    assert len(generados) == 1


def test_cli_expediente_con_insumos_explicitos(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    extra = tmp_path / "balanza.csv"
    extra.write_text("cuenta,saldo\n1101,1000\n", encoding="utf-8")
    main([
        "expediente", "--caso", str(CASO), "--salida", str(tmp_path / "out"),
        "--periodo", "2026-Q2", "--operador", "op",
        "--fecha-generacion", "2026-08-04",
        "--insumo", str(CASO), "--insumo", str(extra),
    ])
    assert "insumos        : 2" in capsys.readouterr().out


# =============================================================================
# FORMATEO DE VALORES EN LA MEMORIA
# =============================================================================


def test_memoria_de_sociedad_sin_cartera(tmp_path: Path) -> None:
    """Requerimiento cero: el nivel es nulo y debe imprimirse como guion largo,
    no como 0.00, que insinuaria un incumplimiento inexistente."""
    caso = json.loads(CASO.read_text(encoding="utf-8"))
    caso["cartera_vigente"] = 0
    caso["cartera_vencida"] = 0
    caso["estimacion_preventiva"] = 0
    exp = generar_expediente(
        reg=REG, resultado=calcular(caso), destino=tmp_path, periodo="2026-Q2",
        fecha_generacion=date(2026, 8, 4), operador="op", version_motor=__version__,
        commit="c", sha256_registro=hash_registro(), rutas_insumos=[CASO],
    )
    memoria = (exp.raiz / "99_Expediente_Auditoria" / "memoria_de_calculo.md").read_text(
        encoding="utf-8"
    )
    assert "| 10 | Nivel de capitalización | [(9) / (5)] * 100 | — |" in memoria
    assert exp.manifiesto["resultado"]["categoria"] == "A"
    assert exp.manifiesto["resultado"]["nivel_capitalizacion"] is None


def test_formateador_tolera_valores_no_numericos() -> None:
    from acr.expediente.memoria import _fmt

    assert _fmt(None) == "—"
    assert _fmt("no aplica") == "no aplica"
    assert _fmt(Decimal("1234.5")) == "1,234.50"
