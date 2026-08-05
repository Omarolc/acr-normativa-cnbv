# Bitácora ACR-02.1 · Lectura tolerante a BOM y compuerta de vigencia

**Sprint:** ACR-02.1 (corrección sobre ACR-02)
**Fecha:** 2026-08-04
**Estado:** CERRADO PARCIAL
**Avance:** 38% (sin cambio de porcentaje; corrige un defecto que habría aparecido en el piloto)

---

## 1. Origen: un defecto encontrado ejecutando, no leyendo

Al verificar el bloqueo de vigencia de ACR-02, este comando falló:

```powershell
$c | ConvertTo-Json | Set-Content "$env:TEMP\c2027.json" -Encoding UTF8
python -m acr.cli calcular --caso "$env:TEMP\c2027.json"
```

```
json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig)
```

PowerShell 5.1 con `Set-Content -Encoding UTF8` escribe **BOM**. La CLI leía con
`encoding="utf-8"` estricto y reventaba.

**Por qué importa más de lo que parece.** Las herramientas que escriben BOM en
Windows son PowerShell, el Bloc de notas y las exportaciones de Excel — es
decir, exactamente con las que una cooperativa prepara sus insumos. El sistema
habría fallado con el primer caso real, y con un traceback de la librería
estándar que no dice qué archivo, ni qué pasó, ni qué hacer.

Encontrado en la máquina del usuario, no en pruebas. Es el argumento a favor de
que la batería de verificación se ejecute en el entorno real y no solo en el mío.

---

## 2. Bloques

### Bloque 1 — Capa de entrada (`src/acr/entrada.py`)

- `leer_json()` / `leer_texto()` con `utf-8-sig`: consume el BOM si está y se
  comporta como `utf-8` si no.
- Errores explicativos en lugar de tracebacks: archivo inexistente, JSON
  malformado con línea y columna, y un mensaje que menciona Excel y Latin-1
  cuando la codificación no es UTF-8.
- `escribir_texto()` escribe **sin BOM**: el manifiesto del expediente compara
  hashes, y un BOM cambiaría el hash del mismo contenido.

Aplicado en `cli/principal.py`, `normativa/registro.py` y
`tools/gate_reproducibilidad.py`.

### Bloque 2 — Compuerta V: bloqueo por vigencia (`tools/gate_vigencia.py`)

El instalador de ACR-02 verificaba el rechazo del corte 2027 desde PowerShell.
Como el script llevaba `$ErrorActionPreference = "Stop"` global y Python emite
el rechazo por stderr, **el script abortaba justo cuando la verificación
pasaba**. El paso de commit nunca corrió.

Diseñé una verificación cuyo éxito abortaba el proceso.

Corrección: la verificación vive en Python y se evalúa por código de salida.
Recorre todas las alertas bloqueantes del registro, comprueba que cada una
rechace y que el rechazo **cite el identificador de la alerta**, verifica que un
corte anterior a la vigencia también se rechace, y que un corte vigente pase.
Funciona en ambos sentidos: un sistema que rechaza todo también estaría roto.

### Bloque 3 — Pruebas (`tests/test_entrada.py`)

Fixture `caso_base_bom.json` con BOM real. Primera prueba del archivo:
verificar que la fixture **efectivamente tiene BOM** — si lo perdiera en algún
commit, la prueba de regresión dejaría de probar algo sin avisar.

Incluye la comprobación de que el mismo caso con y sin BOM produce salida
idéntica: el BOM es de codificación, no de contenido, y no puede alterar una
cifra regulatoria.

### Bloque 4 — Automatización del instalador

- Sin `$ErrorActionPreference = "Stop"` global.
- Las ocho compuertas en una tabla, evaluadas por código de salida.
- Limpieza automática de residuos (`resultado_*.txt`, `.coverage`).
- Mueve los instaladores fuera del repo y los agrega a `.gitignore`.
- Detecta descarga incompleta antes de escribir nada.
- Commit automático. Cero pasos manuales.

---

## 3. Evidencia — ocho compuertas

```
A   ruff                     All checks passed
B   mypy --strict            15 archivos, sin errores
C   pytest                   259 pruebas
C2  cobertura                100.00% en motor + entrada (354 sentencias)
D   literales normativos     Deuda declarada: 0
E   reproducibilidad         3b46243e6d2f945040075229f5b50f032642439a4b4ad8ff0c81d1ce6bb65200
V   bloqueo por vigencia     REF-2027-ANEXOS rechaza; corte previo rechaza; corte vigente pasa
PII datos de socios          sin RFC ni CURP
```

Verificación específica del defecto: archivo JSON con BOM → **ACEPTADO**.

El hash de reproducibilidad **no cambió** respecto de ACR-02, lo cual es la
señal correcta: la corrección es de codificación de entrada, no de cálculo.
Si hubiera cambiado, significaría que toqué algo que no debía.

---

## 4. Regla incorporada al playbook

> Una compuerta cuyo **éxito** se manifiesta como error de proceso necesita
> manejo explícito, no herencia de la política global de errores. Si la
> verificación es "esto debe fallar", vive en código, no en el orquestador.

Segunda regla, del mismo incidente:

> Toda lectura de archivo de insumo pasa por `acr.entrada`. Nunca `open()` ni
> `read_text()` directo. Está en CONTRIBUTING.md como regla 7.

---

## 5. Siguiente

**ACR-03 · Persistencia, historial y calendario · 38% → 48%**

Sin cambios de alcance respecto de lo planeado, salvo la corrección ya
identificada: son 12 calificaciones mensuales (Anexo C Bis) más 4 cómputos
trimestrales, no 4 eventos anuales.

**Cuello de botella de gestión, no de código:** ACR-05 necesita una balanza y un
catálogo de cuentas reales anonimizados. Pesa 20 puntos y no se puede construir
a ciegas.
