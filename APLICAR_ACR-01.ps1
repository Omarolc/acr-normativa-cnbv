# =============================================================================
# APLICADOR — Sprint ACR-01 · Fundacion y purga
# Patron DEV83 adaptado: copiar -> seis compuertas -> marcadores -> push.
# Aborta sin tocar git si cualquier compuerta falla.
#
# Uso:   .\APLICAR_ACR-01.ps1              (aplica y hace push)
#        .\APLICAR_ACR-01.ps1 -SinPush     (aplica, no toca git)
# =============================================================================
param([switch]$SinPush)
$ErrorActionPreference = "Stop"

$REPO = "C:\Users\Omar Corona\Documents\ACR_Normativa_CNBV"
if (-not (Test-Path $REPO)) {
  Write-Host "Repo no encontrado. Si es la primera vez:" -f Yellow
  Write-Host "  mkdir '$REPO'; cd '$REPO'; git init; git branch -M main" -f Yellow
  exit 1
}

$ARCHIVOS = @(
  "pyproject.toml", ".gitignore", "README.md", "CONTRIBUTING.md", "REGISTRO_DE_PURGA.md",
  ".github\workflows\ci.yml",
  "src\acr\__init__.py",
  "src\acr\normativa\__init__.py",
  "src\acr\normativa\registro_normativo_nivel_basico.yaml",
  "src\acr\motor\__init__.py",
  "src\acr\motor\capitalizacion.py",
  "src\acr\mapeo\__init__.py",
  "src\acr\persistencia\__init__.py",
  "src\acr\salida\__init__.py",
  "src\acr\cli\__init__.py",
  "tools\gate_literales.py", "tools\gate_pii.py", "tools\gate_reproducibilidad.py",
  "tools\deuda_literales.txt", "tools\snapshot.ps1",
  "tests\__init__.py", "tests\test_estructura.py",
  "tests\test_gate_literales.py", "tests\test_gate_pii.py"
)

$MARCADORES = @{
  "src\acr\motor\capitalizacion.py" = "def clasificar"
  "tools\gate_literales.py"         = "MECANISMO DE RATCHET"
  "REGISTRO_DE_PURGA.md"            = "fracc. LXVIII"
}

# --- 1) Copiar archivos completos -------------------------------------------
Write-Host "[1/8] Copiando $($ARCHIVOS.Count) archivos..." -f Cyan
foreach ($f in $ARCHIVOS) {
  $src = Join-Path $PSScriptRoot $f
  if (-not (Test-Path $src)) { Write-Host "FALTA EN EL PAQUETE: $f - abortado" -f Red; exit 1 }
  $dst = Join-Path $REPO $f
  New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
  Copy-Item $src $dst -Force
}
Set-Location $REPO

# --- 2) Entorno --------------------------------------------------------------
Write-Host "[2/8] Instalando dependencias..." -f Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --quiet -e ".[dev]"
if ($LASTEXITCODE -ne 0) { Write-Host "INSTALACION FALLO - abortado" -f Red; exit 1 }
$PY = ".\.venv\Scripts\python.exe"

# --- 3..7) Compuertas --------------------------------------------------------
Write-Host "[3/8] Compuerta A - ruff" -f Cyan
& $PY -m ruff check . > resultado_ruff.txt 2>&1
if ($LASTEXITCODE -ne 0) { Get-Content resultado_ruff.txt; Write-Host "RUFF FALLO - abortado" -f Red; exit 1 }

Write-Host "[4/8] Compuerta B - mypy --strict" -f Cyan
& $PY -m mypy --strict src > resultado_mypy.txt 2>&1
if ($LASTEXITCODE -ne 0) { Get-Content resultado_mypy.txt; Write-Host "MYPY FALLO - abortado" -f Red; exit 1 }

Write-Host "[5/8] Compuerta C - pytest" -f Cyan
& $PY -m pytest -q > resultado_pytest.txt 2>&1
if ($LASTEXITCODE -ne 0) { Get-Content resultado_pytest.txt; Write-Host "PYTEST FALLO - abortado" -f Red; exit 1 }

Write-Host "[6/8] Compuerta D - literales normativos" -f Cyan
& $PY tools\gate_literales.py --sprint ACR-01
if ($LASTEXITCODE -ne 0) { Write-Host "LITERAL NORMATIVO EN CODIGO - abortado" -f Red; exit 1 }

Write-Host "[7/8] Compuerta E - reproducibilidad | PII" -f Cyan
& $PY tools\gate_reproducibilidad.py
if ($LASTEXITCODE -ne 0) { Write-Host "NO REPRODUCIBLE - abortado" -f Red; exit 1 }
& $PY tools\gate_pii.py
if ($LASTEXITCODE -ne 0) { Write-Host "PII DETECTADA - abortado" -f Red; exit 1 }

# --- 8) Marcadores y push ----------------------------------------------------
Write-Host "[8/8] Verificacion cruzada de marcadores" -f Cyan
foreach ($m in $MARCADORES.GetEnumerator()) {
  if (-not (Select-String -Path (Join-Path $REPO $m.Key) -Pattern $m.Value -Quiet)) {
    Write-Host "MARCADOR AUSENTE: $($m.Value) en $($m.Key) - abortado" -f Red; exit 1 }
}
Write-Host "SEIS COMPUERTAS VERDES" -f Green

if ($SinPush) { Write-Host "Aplicado sin push (revision manual)." -f Yellow; exit 0 }

git add $ARCHIVOS
git commit -m "ACR-01: fundacion y purga - estructura, seis compuertas, CI, purga de regimen I-IV"
git push origin main
Write-Host "Commit: $(git rev-parse --short HEAD)" -f Green
