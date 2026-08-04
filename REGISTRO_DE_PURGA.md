# Registro de purga — ACR-01

Este documento existe para que las eliminaciones no se deshagan por olvido.
Cada entrada dice **por qué** se removió, con su fundamento. Reintroducir
cualquiera de estos módulos es una regresión normativa, no solo técnica.

## Fundamento del alcance

Disposiciones de carácter general aplicables a las actividades de las SOCAP,
**Artículo 1**:

- **Fracc. LXVIII** — "Sociedad o Sociedad Cooperativa de Ahorro y Préstamo":
  las SOCAP **con niveles de operación I a IV**.
- **Fracc. LXIX** — "SOCAP con Nivel de Operaciones Básico": definición
  **separada**, las del Art. 13 de la Ley.

Cada vez que un artículo de las Disposiciones dice "las Sociedades", **excluye
a Nivel Básico por definición**. Fuera del Título Primero, Capítulo Único
(Arts. 1 Bis a 1 Bis 7), la expresión "nivel de operaciones básico" no aparece
en el articulado vigente.

## Eliminado

| Módulo / elemento original | Motivo | Fundamento |
|---|---|---|
| `validar_liquidez()` — coeficiente 10% | Régimen I–IV | Disposiciones Art. 44, dirigido a "las Sociedades" |
| `_procesar_riesgo_comun()`, `validar_riesgo_comun()` | Régimen I–IV. Y el límite no es 20% plano: 10% PF / 15% PM / 20% SOCAP sobre capital neto. El algoritmo (acumular por monto descendente) tampoco corresponde al concepto | Disposiciones Art. 193 Bis |
| `TABLA_PROVISIONES_CONSUMO/VIVIENDA/COMERCIAL/MICROCREDITO` | Tomadas del Anexo C (I–IV). Para Básico rige el **Anexo C Bis** | Listado de Anexos, Disposiciones |
| `MAPEO_CUENTAS` (101 Caja … 506 Otros Gastos) | Catálogo inventado. El real está en el Anexo T, no disponible | Disposiciones Art. 1 Bis |
| `_calcular_capital_neto()` → `return 1000000` | Valor fijo alimentando cálculos regulatorios | — |
| `_calcular_personas_relacionadas()` → `capital_contable * 0.05` con `cumple_limite: True` | **Dictamen de cumplimiento fabricado** dentro de un expediente regulatorio. El defecto más grave del sistema original | LRASCAP Art. 26 |
| `intangibles` y `creditos_contraventores` en capital neto | No están en el Art. 1 Bis 4 | Disposiciones Art. 1 Bis 4 |
| `generar_acuse()` / `Acuse_Recibo_Simulado.pdf` | Un acuse falso dentro de un expediente regulatorio es un riesgo, no una funcionalidad. Sustituido por `manifiesto_de_entrega.json` (ACR-04) | — |
| `A-2113_Clasificacion_Categoria.xlsx` como entregable | **No es reporte de la cooperativa.** Lo presenta el CSA a la CNBV | Disposiciones Art. 1 Bis 7 |
| Cuotas de supervisión "Art. 47 LRASCAP" | Art. 47 regula funciones del Comité Técnico. Las cuotas son Art. 28-III-c y solo aplican a I–IV | LRASCAP Arts. 28 y 47 |
| Leyenda de aprobación citando Arts. 32, 34, 40 y "niveles I a IV" | Título Tercero, exclusivo de I–IV. En un balance de Nivel Básico es un error visible | LRASCAP Título Tercero |
| **`tests/unit/test_calculators/test_capitalizacion.py` completo** | Sus asserts afirman como correcto que nivel <50% es siempre "D" y que el capital neto resta intangibles. **Bloqueaban activamente la corrección**: cualquier arreglo correcto los hace fallar | — |

## Corregido, no eliminado

| Defecto | Corrección |
|---|---|
| `requerimiento == 0` → categoría D | Sin cartera no hay requerimiento que incumplir → cumplimiento pleno |
| Clasificación numérica pura | Art. 15 depende también del apego a reglas de presentación y del historial |
| Dos fuentes de verdad (calculator + validator recalculaban el 8%) | Una sola: `src/acr/motor/` |
| `NameError` latentes (pandas, json, datetime sin importar) | Módulos afectados eliminados o reescritos |
| `float` en importes | `Decimal` en toda la capa de motor |
| `dict.get(clave, 0)` sobre insumos regulatorios | `InsumoFaltanteError`. Un renglón ausente y uno en cero son hechos distintos |

## Bloqueado, a la espera de insumo del DOF

| Módulo | Insumo | Sprint |
|---|---|---|
| `src/acr/mapeo/` | **Anexo T** | ACR-05 |
| Estimaciones preventivas | **Anexo C Bis** | ACR-06 |
| `src/acr/salida/` (formatos) | **Anexo U** | ACR-07 |

Estos módulos **fallan ruidosamente** (`AnexoNoDisponibleError`). No se rellenan
con catálogos plausibles: un catálogo inventado produce estados financieros con
apariencia válida y contenido falso — el defecto original del sistema.
