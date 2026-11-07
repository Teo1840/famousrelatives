# Arma dist\famousrelatives-extension.zip con la carpeta extension\ lista
# para pasarle a la familia.
# Uso (desde la raíz del proyecto):  powershell -File scripts\build-extension.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "extension"
$dist = Join-Path $root "dist"
$manifest = Get-Content (Join-Path $src "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$zip = Join-Path $dist "famousrelatives-extension.zip"

New-Item -ItemType Directory -Force $dist | Out-Null
if (Test-Path $zip) { Remove-Item $zip -Force }

# El zip contiene una carpeta "famousrelatives" con todo adentro: al
# descomprimir queda una sola carpeta para elegir en "Cargar descomprimida".
$staging = Join-Path $dist "famousrelatives"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
Copy-Item $src $staging -Recurse
Compress-Archive -Path $staging -DestinationPath $zip
Remove-Item $staging -Recurse -Force

Write-Host "Listo: $zip (version $($manifest.version))"
