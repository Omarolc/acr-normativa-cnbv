# Bitácora ACR-04 · Expediente de auditoría

**Sprint:** ACR-04 · **Base:** ACR-03 · **Estado:** CERRADO PARCIAL
**Avance:** 48% → **56%** · **Cierra el tramo autónomo**

---

## 1. Objetivo

Construir el activo defendible. Disposiciones Art. 1 Bis 6: el cómputo de la
sociedad rige para todos los efectos legales **salvo que el Comité de
Supervisión Auxiliar verifique y obtenga un cómputo distinto**, en cuyo caso el
del CSA es definitivo.

Ahí es donde una cooperativa pierde dinero y reputación. El expediente convierte
una verificación de tres semanas en una de tres días.

## 2. Bloques

### Bloque 1 — Manifiesto (`expediente/manifiesto.py`)

SHA-256 y tamaño de cada insumo, versión y hash del registro normativo, versión
del motor, commit, fecha de generación y operador.

**Determinismo:** ningún valor viene del reloj ni del entorno. `fecha_generacion`,
`operador` y `commit` entran como parámetros. Un manifiesto que cambia entre
corridas no prueba nada.

### Bloque 2 — Bitácora encadenada (`expediente/bitacora.py`)

Cada entrada incluye el hash de la anterior, anclada a una semilla que es el
hash de insumos. Alterar o reordenar un evento rompe la cadena y
`verificar_cadena()` lo detecta. Es la diferencia entre un log —que cualquiera
edita— y evidencia.

### Bloque 3 — Memoria de cálculo (`expediente/memoria.py`)

Markdown con los diez renglones del formulario del Anexo U, cada uno con su
**fórmula** y su **fundamento**. Además:

- Los conceptos que **no** se dedujeron del capital contable y por qué.
- La tabla de umbrales del Art. 15 con su fundamento por categoría.
- El disparador del Art. 16 con fecha límite, cuando aplica.
- **Las reglas del régimen I–IV que no se aplicaron**, con la cita de la fracc.
  LXVIII que las deja fuera de alcance. Ante una verificación, explicar por qué
  *no* se aplicó algo vale tanto como explicar por qué sí.
- La cláusula de responsabilidad del Art. 1 Bis 1.

### Bloque 4 — Carpeta de entrega corregida

```
AAAA-MM-DD_PERIODO_Entrega_CSA/
├── 01_Trimestral_CSA/
├── 02_Semestral_Impreso_Firmado/
├── 03_Divulgacion_a_Socios/
├── 04_Gobierno_Corporativo/
├── 05_Monitoreo_Umbrales/
├── 99_Expediente_Auditoria/
│   ├── manifiesto.json
│   ├── bitacora_ejecucion.json
│   ├── memoria_de_calculo.md
│   └── computo_anexo_u.json
└── manifiesto_de_entrega.json
```

Tres correcciones respecto de la estructura original:

1. **No dice "CNBV".** La contraparte es el Comité de Supervisión Auxiliar.
2. **No incluye el A-2113.** Lo presenta el CSA a la Comisión (Art. 1 Bis 7).
   Hay una prueba que verifica que no exista ningún archivo con "2113".
3. **No hay acuse simulado.** Se sustituye por `manifiesto_de_entrega.json`,
   que declara explícitamente que no es un acuse. Hay una prueba que verifica
   que ningún archivo contenga "acuse" en el nombre.

Las cinco carpetas de formatos llevan un `LEEME.md` con su fundamento y la nota
de que el renderizado fiel es ACR-07. **No se rellenan con un formato
aproximado.**

### Bloque 5 — Compuerta X: determinismo del expediente

`tools/gate_expediente.py` genera el expediente dos veces y compara byte a byte,
y verifica la cadena de la bitácora. Novena compuerta del sistema.

---

## 3. Evidencia — nueve compuertas

```
A   ruff                     All checks passed
B   mypy --strict            23 archivos
C   pytest                   323 pruebas
C2  cobertura                100.00%  679 sentencias
D   literales normativos     Deuda declarada: 0
E   reproducibilidad         41a0126cc27f01fa9f57dfbe36ae3e7b4582a6f8a6ba6523e8640a97833b1a13
V   bloqueo por vigencia     funciona en ambos sentidos
X   expediente determinista  10 archivos idénticos, bitácora de 5 entradas verificada
PII datos de socios          sin RFC ni CURP
```

## 4. Criterio de cierre verificado

Un tercero toma la balanza, la memoria de cálculo y el texto de la norma, y
llega al mismo número sin abrir el código:

| # | Concepto | Fórmula | Importe |
|---|---|---|---|
| 4 | Total de cartera de crédito neta | (1) + (2) - (3) | 4,739,500.00 |
| 5 | Requerimientos de capitalización | (4) * 0.08 | 379,160.00 |
| 9 | Capital neto | (6) - (7) - (8) | 950,000.00 |
| 10 | Nivel de capitalización | [(9) / (5)] * 100 | 250.55 |

## 5. Ledger

| Componente | Peso | Antes | Ahora | Δ |
|---|---|---|---|---|
| Expediente de auditoría | 10% | 0% | 80% | +8.0 |
| | | **48%** | | **≈56%** |

El 20% restante del componente es el enlace renglón a renglón con el formato
renderizado del Anexo U, que depende de ACR-07.

## 6. Aquí se detiene el tramo autónomo

**ACR-05 pesa 20 puntos y necesita dos archivos que no puedo generar:**

1. El **catálogo de cuentas** real de una cooperativa, anonimizado.
2. Una **balanza de comprobación** real de la misma cooperativa, anonimizada.

Construir el motor de mapeo sin ver un catálogo real produciría exactamente el
defecto que este proyecto viene corrigiendo: un diccionario plausible e
inventado. La restricción está en el Prompt Maestro y no debe sobreescribirse.

**Criterio de cierre de ACR-05, que tampoco es automatizable:** la balanza real
debe cuadrar y producir un capital contable idéntico al del contador de la
cooperativa. Esa comparación contra el número humano es la prueba, no el test
unitario.
