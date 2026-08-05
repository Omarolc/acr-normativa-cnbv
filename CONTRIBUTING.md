# Reglas de contribución — ACR Normativa

## 1. La norma es dato, no código

Ninguna constante regulatoria vive en un `.py`. Todas viven en
`src/acr/normativa/registro_normativo_nivel_basico.yaml`, con su
`fundamento` y su `vigencia`.

La compuerta D (`tools/gate_literales.py`) lo hace cumplir. Si necesitas
introducir deuda temporal, decláralara en `tools/deuda_literales.txt` con su
sprint de vencimiento. **La lista solo puede encoger.**

Razón: los Anexos T y U se sustituyen el 2027-01-01. Un motor con la norma
incrustada en `if`s exige reescritura. Un motor que la lee de un YAML exige
cambiar un archivo.

## 2. El motor es puro

Sin I/O, sin `datetime.now()`, sin lectura de archivos, sin aleatoriedad.
Todo lo temporal entra como parámetro. Verificado por AST en
`tests/test_estructura.py`.

## 3. Fallo ruidoso

Prohibido `dict.get(clave, 0)` sobre insumos regulatorios. Un insumo ausente
levanta `InsumoFaltanteError`. En un entregable que se firma y se entrega, un
cero silencioso es peor que una excepción.

## 4. Decimal, nunca float

Los importes regulatorios no toleran error de redondeo binario acumulado sobre
miles de renglones de balanza.

## 5. Toda cifra carga su fundamento

Ningún resultado sale del motor sin el artículo que lo sustenta. Es lo que
hace defendible el cómputo ante verificación del CSA (Disposiciones Art. 1 Bis 6).

## 6. Prohibido inventar

Si el Anexo real no está cargado, el módulo se marca BLOQUEADO y falla. No se
rellena con valores plausibles, ni con "ejemplos", ni con placeholders que
devuelvan cumplimiento.

## 7. Codificación de archivos

Las ENTRADAS se leen con `utf-8-sig` a través de `acr.entrada`: Windows,
PowerShell, el Bloc de notas y Excel escriben BOM, y son las herramientas con
las que una cooperativa prepara sus insumos. Nunca `open()` ni `read_text()`
directo sobre un archivo de insumo.

Las SALIDAS se escriben sin BOM. El manifiesto del expediente compara hashes:
un BOM cambiaría el hash del mismo contenido.

## 8. Datos de socios

Balanzas, carteras y padrones viven en `data/inputs/`, excluido de git y del
snapshot. Las fixtures son sintéticas o anonimizadas. La compuerta PII detecta
RFC y CURP.

## Compuertas locales antes de cualquier push

```bash
python -m ruff check .
python -m mypy --strict src
python -m pytest -q
python -m pytest -q --cov=acr.motor --cov=acr.entrada --cov-fail-under=100
python tools/gate_literales.py --sprint ACR-02
python tools/gate_reproducibilidad.py
python tools/gate_vigencia.py
python tools/gate_pii.py
```
