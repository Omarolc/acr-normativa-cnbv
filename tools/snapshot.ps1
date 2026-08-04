# Snapshot del repo para subir a una sesion de sprint.
# Compuertas: repo limpio -> sin PII -> aviso de literales -> ZIP.
$ErrorActionPreference = "Stop"
$REPO = Split-Path $PSScriptRoot -Parent
$OUT  = "$env:USERPROFILE\Downloads"
Set-Location $REPO

if ((git status -s)) { Write-Host "ABORTADO: hay cambios sin commitear." -f Red; exit 1 }
git pull --ff-only
if ($LASTEXITCODE -ne 0) { Write-Host "ABORTADO: pull fallo." -f Red; exit 1 }

$fecha   = Get-Date -Format "ddMMyyyy"
$destino = "$OUT\ACR-snapshot_$fecha.zip"

$archivos = Get-ChildItem -Path $REPO -Recurse -File | Where-Object {
  $_.FullName -notmatch '\\\.venv\\|\\venv\\|\\__pycache__\\|\\\.git\\|\\\.pytest_cache\\|\\\.mypy_cache\\|\\\.ruff_cache\\|\\data\\inputs\\|\\data\\output\\|\\htmlcov\\' -and
  $_.Extension -notin @('.xlsx','.xls','.csv','.pdf','.db','.sqlite','.log')
}

$patronPII = '\b([A-ZN&]{3,4}\d{6}[A-Z0-9]{3})\b|\b([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2})\b'
$fugas = $archivos | Select-String -Pattern $patronPII -List
if ($fugas) {
  Write-Host "ABORTADO - posible PII de socios en el snapshot:" -f Red
  $fugas | ForEach-Object { Write-Host "  $($_.Path):$($_.LineNumber)" -f Yellow }
  exit 1
}

$archivos | Compress-Archive -DestinationPath $destino -Force
Write-Host "Snapshot listo: $destino" -f Green
Write-Host "Archivos: $($archivos.Count) | Commit: $(git rev-parse --short HEAD)" -f Green
