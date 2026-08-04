# Bitácora ACR-01 · Fundación y purga

**Sprint:** ACR-01
**Fecha:** 2026-08-04
**Estado:** CERRADO PARCIAL (pendiente de aplicación y CI verde en tu entorno)
**Avance:** 18% → **26%**

---

## 1. Objetivo

Dejar un repo que no mienta. Antes de construir hay que remover lo que bloquea
activamente la construcción: pruebas que validan comportamiento normativamente
incorrecto, catálogos inventados y módulos del régimen equivocado.

---

## 2. Auditoría del código existente

Fuentes auditadas: `config.py`, `validators.py`, `balance_processor.py`,
`cartera_processor.py`, `capitalizacion.py`, `generate_balance.py`,
`session_automation.py`, `test_capitalizacion.py`, `config.json`, manual y
diagrama de flujo.

### Hallazgo estructural que determinó el sprint

Disposiciones **Art. 1, fracc. LXVIII** define "Sociedad" = SOCAP niveles I–IV.
La **fracc. LXIX** define por separado a Nivel Básico. Verificado sobre el texto
compilado al 07-07-2026: fuera del Título Primero Capítulo Único (Arts. 1 Bis a
1 Bis 7), la expresión "nivel de operaciones básico" **no aparece una sola vez**
en el articulado vigente.

Consecuencia: el sistema original implementaba el régimen de niveles I–IV sobre
una entidad de Nivel Básico. No era un conjunto de bugs; era el alcance.

### Defectos que producían cifras falsas

| Defecto | Efecto |
|---|---|
| `_calcular_capital_neto()` → `return 1000000` | Módulo de riesgo común enteramente ficticio |
| `_calcular_personas_relacionadas()` → `capital_contable * 0.05`, `cumple_limite: True` | **Dictamen de cumplimiento fabricado** en expediente regulatorio |
| Mora medida contra vencimiento final del crédito | Crédito a 36 meses sin pagar reporta 0 días de mora durante 3 años. Error de un solo sentido: siempre favorece a la cooperativa |
| Capital neto restando intangibles y créditos a contraventores | Conceptos ajenos al Art. 1 Bis 4 |
| `_procesar_estados()` no calcula `caja`, `bancos`, `dep_vista`… | Balance con casi todos los renglones en cero, pero con firmas y nota de aprobación |
| `capital_contable = capital + ingresos − egresos` | Duplica el resultado del ejercicio si la cuenta 304 ya lo contiene |
| 4 `NameError` latentes (pandas, json, datetime) | El flujo end-to-end nunca corrió |
| `generar_reporte_anexo_u()` devuelve `dict`, la sesión invoca `.to_excel()` | `AttributeError` garantizado |

### Deuda negativa confirmada

`test_capitalizacion.py` afirma como correcto que un nivel <50% siempre es "D" y
que el capital neto resta intangibles. Esas pruebas **bloqueaban la corrección**:
cualquier arreglo normativamente correcto las hace fallar. Se eliminaron, no se
adaptaron. Detalle completo en `REGISTRO_DE_PURGA.md`.

---

## 3. Bloques implementados

### Bloque 1 — Estructura por capas
```
src/acr/normativa/    capa 0 — registro normativo versionado (YAML)
src/acr/mapeo/        capa 1 — BLOQUEADO (Anexo T)
src/acr/motor/        capa 2 — cálculo puro
src/acr/persistencia/ capa 3 — ACR-03
src/acr/salida/       capa 4 — BLOQUEADO (Anexo U)
src/acr/cli/          ACR-02
```

### Bloque 2 — Purga
13 elementos eliminados, 6 defectos corregidos, 3 módulos bloqueados con fallo
ruidoso. Cada entrada con su fundamento en `REGISTRO_DE_PURGA.md`.

Los módulos bloqueados levantan `AnexoNoDisponibleError` con mensaje explícito:
*"Prohibido sustituirlo por un catálogo construido por inferencia."*

### Bloque 3 — Harness
`pyproject.toml` con ruff (10 familias de reglas), mypy `strict`,
pytest + coverage. Paquete instalable.

### Bloque 4 — Compuertas propias del dominio

**`tools/gate_literales.py` (compuerta D)** — la pieza central del sprint.
Escanea todos los `.py` buscando constantes regulatorias (`0.08`, `2500000`,
`100000`, umbrales de categoría) y falla si aparecen fuera del YAML.

Incorpora un **mecanismo de ratchet**: `tools/deuda_literales.txt` declara qué
archivos aún cargan literales y **en qué sprint vence** esa deuda. Si el sprint
actual supera el de vencimiento, la compuerta falla aunque el archivo esté
declarado. La lista solo puede encoger.

Estado actual: 1 entrada — `src/acr/motor/capitalizacion.py`, vence en **ACR-02**.

**`tools/gate_pii.py`** — detecta RFC (persona física y moral) y CURP en el árbol
versionado. Los insumos reales son padrones y carteras con datos de socios.

**`tools/gate_reproducibilidad.py` (compuerta E)** — sustituye a la prueba contra
producción del protocolo DEV83. Aquí no hay servidor; la garantía equivalente es
que el mismo insumo produce el mismo SHA-256. Es lo que hace defendible el
cómputo ante verificación del CSA (Art. 1 Bis 6).

### Bloque 5 — Motor con tipado estricto
Correcciones para pasar `mypy --strict`: `Optional[Decimal]` manejado
explícitamente (`EstadoInconsistenteError` en vez de degradar), `tuple[str, ...]`
parametrizado, excepciones con sufijo `Error`, `Sequence` desde `collections.abc`.

### Bloque 6 — CI
`.github/workflows/ci.yml` con las seis compuertas como pasos independientes.

### Bloque 7 — Documentación operativa
`README.md`, `CONTRIBUTING.md` (7 reglas duras), `REGISTRO_DE_PURGA.md`,
`tools/snapshot.ps1`.

---

## 4. Evidencia — seis compuertas en mi entorno

```
=== COMPUERTA A: ruff ===
All checks passed!                                                  exit=0

=== COMPUERTA B: mypy --strict ===
Success: no issues found in 8 source files                          exit=0

=== COMPUERTA C: pytest ===
.............                                              [100%]   exit=0
13 pruebas

=== COMPUERTA D: literales normativos ===
COMPUERTA D OK — cero literales fuera del registro. Deuda declarada: 1
    src/acr/motor/capitalizacion.py (vence en ACR-02)               exit=0

=== COMPUERTA E: reproducibilidad ===
COMPUERTA E OK — reproducible.
SHA-256: 946f60d7be0b8fb9a19f3dd800d42055d8f6cbc4de292869404dd48f608332be

=== COMPUERTA PII ===
COMPUERTA PII OK — sin RFC ni CURP en el arbol versionado.          exit=0
```

**Cobertura: 5%** — reportada honestamente. Las pruebas de ACR-01 cubren las
compuertas, no el motor. La suite de frontera del motor (cobertura objetivo
100%) es ACR-02.

### Incidente durante la ejecución (registrado por transparencia)

Las tres compuertas nuevas fallaron en su primera corrida **detectándose a sí
mismas**: `tests/test_gate_literales.py` contenía la cadena `0.08` como
centinela, `tests/test_gate_pii.py` contenía un RFC sintético, y
`test_motor_no_hace_io` reportaba violación porque el docstring del motor
menciona `datetime.now()` para prohibirlo.

Corrección aplicada — endurecer, no relajar:
- Centinelas ensamblados en tiempo de ejecución (`"FACTOR = 0." + "08"`), de modo
  que el patrón no exista textualmente en el archivo de prueba.
- `test_motor_no_hace_io` reescrito con **análisis AST** en vez de búsqueda de
  texto: inspecciona nodos `Import`/`ImportFrom` y `Call`. Se agregó
  `test_motor_no_llama_funciones_impuras`.

---

## 5. Smoke funcional del motor

Caso: capital contable 1,000,000 · certificados no elegibles 50,000 ·
cartera bruta 5,000,000 · provisiones 200,000 · corte 2026-06-30 · UDI 8.52

| Concepto | Resultado | Fundamento |
|---|---|---|
| Capital neto | 950,000.00 | Art. 1 Bis 4 |
| Requerimiento (8%) | 384,000.00 | Art. 1 Bis 3 |
| Nivel de Capitalización | 247.40% | Art. 1 Bis 6 |
| Categoría | **A** | Art. 15, fracc. I, inciso a) |
| Activos en UDIS | 2,112,676.06 | Art. 13 |
| Excede límite Art. 13 | No (holgura 15.5%) | Art. 16 |
| Personas relacionadas | 55.00% del capital contable | Art. 26 |
| Cumple Art. 26 | **No** | Art. 26, penúltimo párrafo |

El último renglón es la validación del sprint: ante una exposición de 55% el
sistema **reporta incumplimiento**. La versión original devolvía `cumple_limite:
True` fijo para cualquier entrada.

### Casos borde verificados

| Caso | Antes | Ahora |
|---|---|---|
| Sin cartera (requerimiento = 0) | Categoría D | Categoría A — sin cartera no hay requerimiento que incumplir |
| Nivel 247%, EEFF no apegados a reglas | Categoría A | Categoría C — Art. 15, inciso c), segunda hipótesis |
| Historial `["C","C"]` | No contemplado | Categoría D — Art. 15, fracc. III |
| Insumo ausente | `0` silencioso | `InsumoFaltanteError` |

---

## 6. Comandos de verificación (pegar tras aplicar)

```powershell
cd "C:\Users\Omar Corona\Documents\ACR_Normativa_CNBV"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy --strict src
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gate_literales.py --sprint ACR-01
.\.venv\Scripts\python.exe tools\gate_reproducibilidad.py
.\.venv\Scripts\python.exe tools\gate_pii.py

# Prueba del ratchet: debe FALLAR con "deuda vencida" (comportamiento correcto)
.\.venv\Scripts\python.exe tools\gate_literales.py --sprint ACR-03

git log --oneline -3
Start-Process "https://github.com/<usuario>/acr-normativa/actions"
```

**Hash esperado de la compuerta E:**
`946f60d7be0b8fb9a19f3dd800d42055d8f6cbc4de292869404dd48f608332be`

Si tu entorno produce un hash distinto, hay divergencia de versión de Decimal o
de Python y debe investigarse antes de continuar: la reproducibilidad entre
máquinas es requisito del expediente de auditoría.

---

## 7. Ledger de avance

| Componente | Peso | Antes | Ahora | Δ |
|---|---|---|---|---|
| Deuda negativa (pruebas falsas, catálogo inventado) | — | −7 | 0 | **+7.0** |
| Empaque y CLI | 2% | 60% | 90% | +0.6 |
| Pruebas | 3% | 0% | 30% | +0.9 |
| | | **18%** | | **26%** |

---

## 8. Estado y siguiente sprint

**CERRADO PARCIAL.** Pasa a CERRADO cuando reportes: CI verde + hash de commit +
las seis compuertas en tu entorno + el hash de reproducibilidad coincidente.

### ACR-02 · Registro normativo y motor puro · 26% → 32%

1. Cargador YAML con validación de esquema (pydantic) y bloqueo por
   `alertas_vigencia` (rechazar cortes ≥ 2027-01-01).
2. Motor consumiendo parámetros del registro. **Salda la única entrada de
   `deuda_literales.txt`** — es obligatorio: vence en ACR-02 y la compuerta D
   empezará a fallar.
3. Suite de frontera: 149.99 / 150.00 / 150.01, 99.99 / 100.00, 49.99 / 50.00;
   requerimiento 0; capital neto negativo; provisiones > cartera.
4. Matriz completa Art. 15: nivel × `eeff_cumplen_reglas` × `eeff_en_plazo` ×
   historial, cada celda con su cita textual.
5. Evaluador de certificados Art. 1 Bis 5 (siete requisitos, CCP a fecha de
   emisión).
6. CLI: `acr calcular --caso archivo.json`.
7. Cobertura 100% en `src/acr/motor`.

### Recordatorio de ruta crítica

**ACR-A0 sigue abierto y es la tarea de mayor retorno del proyecto:** conseguir
los Anexos **T**, **U** y **C Bis** del DOF desbloquea 54 puntos porcentuales.
Sin ellos el techo del proyecto es 46%, alcanzable en ACR-04. No es una tarea de
código.
