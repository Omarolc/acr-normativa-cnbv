# ACR Normativa_CNBV

Sistema de cumplimiento regulatorio para **Sociedades Cooperativas de Ahorro y
Préstamo con Nivel de Operaciones Básico**.

## Alcance normativo (verificado, no re-derivar)

El universo normativo de Nivel Básico es acotado:

- **Disposiciones**, Título Primero, Capítulo Único: Arts. **1 Bis a 1 Bis 7**
- **LRASCAP**: Arts. **13–16** (nivel básico) y **22–28** (disposiciones comunes)

Todo lo demás de las Disposiciones dice "las Sociedades", que por definición
(Art. 1, fracc. LXVIII) son las SOCAP de **niveles I a IV**. Ver
[REGISTRO_DE_PURGA.md](REGISTRO_DE_PURGA.md).

**La contraparte de entrega es el Comité de Supervisión Auxiliar (FOCOOP), no la
CNBV.** El reporte A-2113 lo presenta el CSA a la Comisión (Art. 1 Bis 7); la
cooperativa no lo genera.

## Arquitectura

```
capa 0  src/acr/normativa/    Registro versionado + esquema + vigencia   ACR-02
capa 1  src/acr/mapeo/        Catálogo institucional → Anexo T           ACR-05
capa 2  src/acr/motor/        Cálculo puro, cobertura 100%               ACR-02
capa 3  src/acr/persistencia/ Historial de categorías, umbral UDIS       ACR-03
capa 4  src/acr/salida/       Formatos Anexo U + expediente              ACR-04/07
```

## Estado

| Sprint | Objetivo | Estado |
|---|---|---|
| ACR-01 | Fundación y purga | **CERRADO** — 26% |
| ACR-02 | Registro normativo, motor y anexos | **CERRADO PARCIAL** — 38% |
| ACR-03 | Persistencia y calendario | pendiente |
| ACR-04 | Expediente de auditoría | pendiente |
| ACR-05 | Mapeo contable | requiere balanza real anonimizada |
| ACR-06 | Conciliación de estimaciones | requiere balanza real |
| ACR-07 | Renderizado Anexo U | pendiente |
| ACR-08 | Endurecimiento y piloto | pendiente |

Los tres anexos del DOF (T, U y C Bis) ya están incorporados como dato
versionado en el registro normativo.

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Compuertas

```bash
python -m ruff check .                              # A — estilo
python -m mypy --strict src                         # B — tipos
python -m pytest -q                                 # C — pruebas
python -m pytest -q --cov=src/acr/motor --cov-fail-under=100   # C2 — cobertura
python tools/gate_literales.py --sprint ACR-02      # D — cero literales normativos
python tools/gate_reproducibilidad.py               # E — mismo input, mismo hash
python tools/gate_pii.py                            # PII — sin datos de socios
```

## Responsabilidad

Herramienta de apoyo al cálculo y a la preparación de información. **La
formulación y presentación de los estados financieros es responsabilidad del
Consejo de Administración** (Disposiciones Art. 1 Bis 1, tercer párrafo). El
cómputo de la sociedad rige para todos los efectos legales salvo que el Comité
de Supervisión Auxiliar verifique y obtenga uno distinto (Art. 1 Bis 6).
