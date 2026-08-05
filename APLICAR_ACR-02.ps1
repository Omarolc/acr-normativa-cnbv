param([switch]$SinPush)
$REPO = "C:\Users\Omar Corona\Documents\ACR_Normativa_CNBV"
Set-Location $REPO
$PY = ".\.venv\Scripts\python.exe"
& $PY -m pip install --quiet -e ".[dev]"

$compuertas = @(
  @{ n = "A   ruff";                   c = { & $PY -m ruff check . } },
  @{ n = "B   mypy --strict";          c = { & $PY -m mypy --strict src } },
  @{ n = "C   pytest";                 c = { & $PY -m pytest -q } },
  @{ n = "C2  cobertura 100%";         c = { & $PY -m pytest -q --cov=acr.motor --cov=acr.entrada --cov-fail-under=100 } },
  @{ n = "D   literales normativos";   c = { & $PY tools\gate_literales.py --sprint ACR-02 } },
  @{ n = "E   reproducibilidad";       c = { & $PY tools\gate_reproducibilidad.py } },
  @{ n = "V   bloqueo por vigencia";   c = { & $PY tools\gate_vigencia.py } },
  @{ n = "PII datos de socios";        c = { & $PY tools\gate_pii.py } }
)
$fallo = $false
foreach ($g in $compuertas) {
  Write-Host ("  {0,-28}" -f $g.n) -NoNewline
  $out = & $g.c 2>&1
  if ($LASTEXITCODE -ne 0) { Write-Host "FALLO" -f Red; $out | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" -f DarkGray }; $fallo = $true }
  else { Write-Host "OK" -f Green }
}
if ($fallo) { Write-Host "ABORTADO - no se toca git" -f Red; exit 1 }
Write-Host "OCHO COMPUERTAS VERDES" -f Green
if ($SinPush) { exit 0 }
git add -A
git -c user.email="acr@local" -c user.name="ACR" commit -q -m "ACR-02.1: lectura tolerante a BOM, compuerta de vigencia"
git rev-parse --short HEAD
