# Bitácora ACR-02 (ampliado) · Registro normativo, motor puro y anexos

**Sprint:** ACR-02 ampliado
**Base:** commit `eeabc2f` (ACR-01 cerrado)
**Fecha:** 2026-08-04
**Estado:** CERRADO PARCIAL (pendiente de aplicación y CI verde en tu entorno)
**Avance:** 26% → **38%**

---

## 1. Objetivo

Que toda la norma sea dato y todo el cálculo sea función pura verificada,
incorporando los tres anexos del DOF que llegaron entre ACR-01 y este sprint.

---

## 2. Bloques implementados

### Bloque 1 — Registro normativo con los tres anexos

`registro_normativo_nivel_basico.yaml` pasa de 12 a 22 secciones. Incorpora:

| Sección nueva | Fuente | Contenido |
|---|---|---|
| `estimaciones_preventivas` | Anexo C Bis | 8 estratos de mora, base de cálculo, exclusiones |
| `cartera_vencida` | Anexo T, párr. 57 | 5 supuestos con sus umbrales propios |
| `pago_sostenido` | Anexo T, párr. 48-50 | 3 amortizaciones, umbral de 60 días |
| `reestructuras` | Anexo T, párr. 58-61 | Reglas de permanencia y el 25% |
| `estimacion_irrecuperabilidad` | Anexo T, párr. 72-73 | Plazos de 60 y 90 días |
| `formulario_computo_anexo_u` | Anexo U, apdo. II | Los 10 renglones con sus fórmulas |
| `rubros_balance` / `rubros_resultados` | Anexo T + U | Catálogo destino completo |
| `certificados_elegibilidad` | Art. 1 Bis 5 | Los 7 requisitos |

### Bloque 2 — Esquema pydantic con validación estructural

`esquema.py` no solo verifica tipos. El validador de `estratos` comprueba que la
tabla del Anexo C Bis sea **contigua desde cero y sin traslapes**. Un hueco en la
tabla significa un crédito sin porcentaje aplicable, que en la práctica se
convierte en estimación cero — exactamente el defecto que este sprint corrige.

### Bloque 3 — Cargador con bloqueo por vigencia

`registro.py` es el único módulo del sistema que lee de disco. Expone:

- `verificar_vigencia()` — aborta con `VigenciaBloqueadaError` para cortes ≥ 2027-01-01.
- `verificar_fecha_corte_trimestral()` — Art. 1 Bis 6: solo día último de marzo, junio, septiembre o diciembre.
- `hash_registro()` — SHA-256 para el manifiesto del expediente (ACR-04).

### Bloque 4 — Motor sin literales

Todos los parámetros provienen del registro. **La deuda de literales quedó
saldada**: `tools/deuda_literales.txt` está vacío y la compuerta D reporta cero.

Cambio de contrato: `calcular_capitalizacion()` ahora recibe `cartera_vigente`,
`cartera_vencida` y `estimacion_preventiva` por separado, porque el formulario
del Anexo U los exige como renglones 1, 2 y 3. Antes recibía una `cartera_bruta`
agregada que no correspondía a ningún renglón del formato.

`Capitalizacion.formulario_anexo_u()` produce los 10 renglones listos para el
formato de entrega.

### Bloque 5 — Motor de cartera (Anexo C Bis + Anexo T párr. 57)

`cartera.py` implementa:

- `dias_mora()` — cuenta desde la **primera amortización no cubierta**. El plazo
  del crédito no existe como insumo, para que el defecto original sea
  estructuralmente imposible de reintroducir.
- `es_cartera_vencida()` — los cinco supuestos del párrafo 57, cada uno con su
  umbral propio (30 / 30-90 / 90 días, 3 amortizaciones, 2 periodos).
- `calificar_credito()` / `calificar_cartera()` — estimaciones sobre el importe
  total incluidos intereses, excluyendo los devengados no cobrados de vencida.

**Nuevo contrato de entrada.** El esquema anterior
(`monto, fecha_otorgamiento, plazo, tasa`) es matemáticamente insuficiente. El
nuevo `Credito` exige `saldo_insoluto`, `fecha_primera_amortizacion_no_cubierta`,
`esquema_pagos`, `amortizaciones_vencidas`, `dias_vencido_intereses` y
`periodos_facturacion_vencidos`.

### Bloque 6 — Evaluador de certificados (Art. 1 Bis 5)

Los siete requisitos, con el CCP **a la fecha de emisión**, no el vigente al
corte. Solo la porción que incumple alimenta el renglón 7 del Anexo U; la versión
original deducía la totalidad de los certificados excedentes.

### Bloque 7 — CLI determinista

`acr calcular --caso archivo.json` produce JSON con claves ordenadas, Decimal
como cadena y sin timestamps. `acr registro` muestra versión, hash y alertas.

### Bloque 8 — `.gitattributes`

Normaliza finales de línea a LF. Sin esto, el mismo commit produce hashes de
archivo distintos en Windows y Linux, y el `manifiesto.json` de ACR-04 pierde
exactamente la propiedad por la que existe.

---

## 3. Tres decisiones de diseño que vale documentar

### 3.1 Vigencia normativa ≠ fuente documental

Primera versión del registro llevaba `vigencia_desde: 2026-07-07`, la fecha del
compilado. Con eso, un corte a junio 2026 era rechazado — pero un corte se rige
por la norma vigente **a esa fecha**, no por la del documento consultado.

Corregido separando los campos: `vigencia_desde/hasta` acota las fechas de corte
que los parámetros rigen; `compilado_fuente` es la fecha del texto verificado.
El sistema **no extrapola hacia atrás**: un corte anterior a 2026-01-01 exige
cargar un registro histórico.

### 3.2 El redondeo de presentación no puede determinar el cumplimiento

Una exposición de 100,001 sobre 1,000,000 es 10.0001% y excede el límite del
Art. 26. Al redondear a dos decimales para el formato daba 10.00% y el sistema
la declaraba cumplida. El mismo defecto habría hecho que un nivel real de
149.9999% se clasificara como A.

Corregido: `Capitalizacion` lleva `nivel_pct` (redondeado, para el formulario)
y `nivel_exacto` (sin redondear, para determinar la categoría). El mismo criterio
se aplicó a personas relacionadas.

### 3.3 Ámbito de la compuerta D

La compuerta empezó a marcar los archivos de prueba, que legítimamente contienen
`"150.00"` y `"100.00"` como datos de frontera.

No se relajó el umbral: se acotó el ámbito a `src/` y `tools/`, con este
razonamiento registrado en el propio módulo — en `src/` un umbral literal **es**
comportamiento y está prohibido; en `tests/` es una **afirmación independiente de
lo que dice la norma**. Si las pruebas leyeran los umbrales del mismo YAML que
validan, pasarían aunque alguien corrompiera el registro. Las pruebas son el
contrapeso al registro y por eso llevan los valores a mano.

`tests/test_registro.py` materializa ese contrapeso: verifica a mano el 8%, los
2'500,000 UDIS, los umbrales 150/100/50, el 10% del Art. 26, el 1.50 del CCP y
la tabla completa del Anexo C Bis.

---

## 4. Evidencia — seis compuertas

```
A  ruff                     All checks passed!                    exit=0
B  mypy --strict            no issues found in 14 source files    exit=0
C  pytest                   250 passed                            exit=0
C2 cobertura del motor      100.00%  (331/331 sentencias)         exit=0
D  literales normativos     Deuda declarada: 0                    exit=0
E  reproducibilidad         SHA-256 3b46243e6d2f9450...           exit=0
PII datos de socios         sin RFC ni CURP                       exit=0
```

**Hash de reproducibilidad ACR-02:**
`3b46243e6d2f945040075229f5b50f032642439a4b4ad8ff0c81d1ce6bb65200`

Cambió respecto de ACR-01 porque la salida ahora es el formulario completo del
Anexo U, no un diccionario ad hoc.

### Cobertura por módulo

| Módulo | Sentencias | Cobertura |
|---|---|---|
| `motor/capitalizacion.py` | 166 | 100% |
| `motor/cartera.py` | 101 | 100% |
| `motor/certificados.py` | 60 | 100% |
| `motor/__init__.py` | 4 | 100% |

Las últimas tres líneas sin cubrir eran guardas contra un registro corrupto. En
lugar de excluirlas con `pragma`, `tests/test_guardas.py` construye registros
deliberadamente malformados y demuestra que las guardas abortan. Una guarda no
probada es código muerto, y es donde se esconden los fallos silenciosos.

---

## 5. La prueba adversarial

`test_credito_a_36_meses_sin_un_solo_pago_reporta_mora_desde_el_dia_31`

Crédito de 500,000 otorgado hace 12 meses, primera amortización vencida hace 335
días, sin un solo pago.

| | Sistema original | ACR-02 |
|---|---|---|
| Días de mora | 0 (faltan 24 meses para el vencimiento final) | 335 |
| Cartera | Vigente | Vencida (Anexo T, párr. 57, inciso d) |
| Porcentaje | 0% (Anexo C, A-1) | 100% (Anexo C Bis, estrato 181+) |
| Estimación | 0 | 500,000.00 |

La clase `Credito` **no tiene** campo `plazo` ni `fecha_vencimiento`. El test lo
verifica con `assert not hasattr`. El defecto no se puede reintroducir sin
cambiar el contrato de datos, que es un cambio visible.

---

## 6. Impacto acumulado de las correcciones

Cartera de 5,000,000 con perfil de mora conservador:

| Concepto | Sistema original | ACR-02 |
|---|---|---|
| Estimaciones preventivas | 0 | 260,500 (5.21%) |
| Nivel de Capitalización | 250.00% | 195.04% |
| Diferencia | | **54.96 puntos inflados** |

Piso irreducible: una cartera **totalmente al corriente** exige 1% de
estimaciones. No existe estrato con 0% en el Anexo C Bis.

---

## 7. Comandos de verificación

```powershell
cd "C:\Users\Omar Corona\Documents\ACR_Normativa_CNBV"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m ruff check .
& $PY -m mypy --strict src
& $PY -m pytest -q
& $PY -m pytest -q --cov=src/acr/motor --cov-fail-under=100
& $PY tools\gate_literales.py --sprint ACR-02
& $PY tools\gate_reproducibilidad.py
& $PY tools\gate_pii.py

# El registro normativo y sus alertas
& $PY -m acr.cli registro

# Cómputo completo con el formulario del Anexo U
& $PY -m acr.cli calcular --caso tests\fixtures\caso_base.json

# Debe FALLAR citando REF-2027-ANEXOS (comportamiento correcto)
& $PY -c "import json,pathlib; c=json.loads(pathlib.Path('tests/fixtures/caso_base.json').read_text()); c['fecha_corte']='2027-03-31'; pathlib.Path('$env:TEMP/c2027.json').write_text(json.dumps(c))"
& $PY -m acr.cli calcular --caso $env:TEMP\c2027.json
```

---

## 8. Ledger

| Componente | Peso | Antes | Ahora | Δ |
|---|---|---|---|---|
| Registro normativo | 15% | 70% | 100% | +4.5 |
| Motor de cálculo | 15% | 80% | 100% | +3.0 |
| Mora y estimaciones | 12% | 0% | 30% | +3.6 |
| Pruebas | 3% | 30% | 90% | +1.8 |
| Empaque y CLI | 2% | 90% | 100% | +0.2 |
| | | **26%** | | **≈38%** |

El componente de mora avanza al 30% y no más: la tabla y las reglas están
implementadas, pero la conciliación contra el saldo contable de la cuenta de
estimación preventiva requiere una balanza real. Se cierra en ACR-06.

---

## 9. Siguiente sprint

**ACR-03 · Persistencia, historial y calendario · 38% → 48%**

1. SQLite: `periodos` (fecha_corte, nivel, categoría, hash_inputs, versión de
   registro), `activos_udi`, `personas_relacionadas`.
2. Regla de dos "C" consecutivas alimentada desde la base, no desde parámetro.
3. Monitor Art. 13 con carga del valor UDI de Banco de México (archivo, no scraping).
4. Disparador Art. 16: cuenta regresiva de 150 días con fecha límite calculada.
5. Calendario generado desde el YAML. **Corrección respecto del plan original:**
   son 12 calificaciones mensuales (Anexo C Bis) más 4 cómputos trimestrales,
   no 4 eventos anuales.
6. `acr agenda --desde --hasta`.

**Cuello de botella siguiente, y no es de código:** ACR-05 necesita una balanza y
un catálogo de cuentas reales anonimizados de una cooperativa. Sin ellos el mapeo
contable se construye a ciegas. Conviene ir consiguiéndolos ahora.
