# Bitácora ACR-03 · Persistencia, historial y calendario

**Sprint:** ACR-03 · **Base:** commit `037f8a1` · **Estado:** CERRADO PARCIAL
**Avance:** 38% → **48%**

---

## 1. Objetivo

El sistema deja de ser una calculadora de un disparo y adquiere memoria. Sin
historial persistido, el Art. 15, fracc. III (dos clasificaciones consecutivas
en C derivan en D) es inimplementable.

## 2. Bloques

### Bloque 1 — Persistencia (`src/acr/persistencia/almacen.py`)

SQLite con tres tablas y versión de esquema: `periodos`, `activos_udi`,
`personas_relacionadas`. Cada periodo guarda el hash de insumos, la versión del
registro normativo y su SHA-256 — los tres campos que ACR-04 necesita para el
manifiesto del expediente.

**Decisión:** `registrar_periodo()` **rechaza sobrescribir** salvo permiso
explícito. Sobrescribir en silencio destruiría la evidencia del cómputo
anterior, que forma parte del expediente de auditoría.

**Determinismo:** ningún timestamp automático. La fecha de corte es la clave y
entra como dato. Dos ejecuciones de la misma secuencia producen la misma base.

`historial_categorias(anterior_a)` excluye la fecha consultada: un periodo no
puede formar parte de su propio historial.

### Bloque 2 — Calendario (`src/acr/motor/calendario.py`)

Función pura derivada del registro. No hay fechas cableadas: los meses de corte
y de entrega vienen del YAML y se emparejan por posición.

**Corrección al plan original.** El plan asumía cuatro eventos anuales. Con el
Anexo C Bis incorporado son **doce calificaciones mensuales** de cartera, cuatro
cómputos trimestrales, cuatro entregas trimestrales, dos semestrales impresas,
cuatro avisos en sucursales y un informe anual. Una cooperativa que solo atienda
los trimestres incumple el Anexo C Bis once veces al año sin notarlo.

### Bloque 3 — Plazos derivados

- `obligaciones_por_clasificacion()`: los 30 días del Art. 15-II y los 60 días
  de evidencia al CSA. No son fechas de calendario: cuentan desde la
  notificación, que ocurre cuando ocurre.
- `evaluar_disparador_art16()`: al rebasar el límite del Art. 13, calcula la
  fecha límite de los 150 días para presentar solicitud ante el CSA.

### Bloque 4 — Valor de la UDI (`src/acr/udis.py`)

Carga desde CSV descargado, **nunca por red**. Dos razones: un expediente debe
reconstruirse dentro de tres años con los mismos insumos, y una llamada de red
no es reproducible ni trazable.

`valor_udi_en()` **no interpola ni toma el más cercano**: produciría un valor que
Banco de México nunca publicó, dentro de un documento que se firma.

### Bloque 5 — CLI

`acr agenda --desde --hasta` · `acr registrar --caso --base` · `acr historial --base`

`registrar` alimenta el historial desde la base, no desde parámetro. El comando
`historial` reporta además los excesos del Art. 13 con su fecha límite y los
incumplimientos del Art. 26.

---

## 3. La prueba central del sprint

`test_seis_trimestres_reproducen_el_escalamiento_c_c_d`

| Corte | Nivel | Categoría | Historial previo |
|---|---|---|---|
| 2026-03-31 | 200% | A | [] |
| 2026-06-30 | 120% | B | [A] |
| 2026-09-30 | 80% | C | [A, B] |
| 2026-12-31 | 75% | C | [A, B, C] |
| siguiente | **90%** | **D** | [A, B, C, C] |

El quinto periodo tiene nivel 90% —que por sí solo sería C— y clasifica **D** por
el Art. 15, fracc. III. La regla solo funciona porque el historial viene de la
base. Sin persistencia, ese periodo se habría reportado como C y la cooperativa
habría seguido captando.

---

## 4. Evidencia — ocho compuertas

```
A   ruff                     All checks passed
B   mypy --strict            18 archivos
C   pytest                   296 pruebas
C2  cobertura                100.00%  motor + entrada + persistencia + udis (534 sentencias)
D   literales normativos     Deuda declarada: 0
E   reproducibilidad         41a0126cc27f01fa9f57dfbe36ae3e7b4582a6f8a6ba6523e8640a97833b1a13
V   bloqueo por vigencia     funciona en ambos sentidos
PII datos de socios          sin RFC ni CURP
```

**El hash de reproducibilidad cambió** respecto de ACR-02.1, y es correcto: la
salida ahora incluye `hash_insumos` y el disparador del Art. 16. Un hash igual
habría significado que los campos nuevos no llegaron a la salida.

---

## 5. Ledger

| Componente | Peso | Antes | Ahora | Δ |
|---|---|---|---|---|
| Persistencia | 6% | 0% | 100% | +6.0 |
| Calendario | 5% | 25% | 100% | +3.75 |
| Pruebas | 3% | 90% | 95% | +0.15 |
| | | **38%** | | **≈48%** |

---

## 6. Siguiente

**ACR-04 · Expediente de auditoría · 48% → 56%.** Manifiesto con SHA-256 de cada
insumo, memoria de cálculo en Markdown enlazada al formulario del Anexo U, log
encadenado por hash, y la estructura de carpetas de entrega corregida.

**El cuello de botella no cambió y no es de código:** ACR-05 necesita una balanza
y un catálogo de cuentas reales anonimizados. Pesa 20 puntos y es el único
componente que no se puede construir sin datos de campo.
