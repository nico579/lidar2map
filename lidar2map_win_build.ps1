# lidar2map_win_build.ps1 : build de lidar2map.exe (PyInstaller onedir)
#
# Une seule passe PyInstaller -> dist/lidar2map/ (lidar2map.exe + _internal/),
# le programme tel qu'il est livré. release.yml archive ensuite ce dossier.
#
# Jusqu'à la 1.54, deux passes de plus zippaient ce dossier et construisaient
# un lanceur onefile qui l'extrayait dans %LOCALAPPDATA% au premier
# lancement : deux exemplaires sur disque, et 30 à 60 s d'attente après
# chaque mise à jour. Depuis la 1.55, le dossier est livré tel quel, comme
# ceux de blink2video et de watch2notif.
#
# Usage :
#   PowerShell -ExecutionPolicy Bypass -File lidar2map_win_build.ps1

$root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv  = Join-Path $env:USERPROFILE ".lidar2map\venv"
$pyi   = Join-Path $venv "Scripts\pyinstaller.exe"

$distOut = "$root\dist"
$appRoot = "$distOut\lidar2map"

Write-Host ""
Write-Host "PyInstaller onedir (lidar2map_win.spec)..." -ForegroundColor Cyan
$out = & $pyi "$root\lidar2map_win.spec" `
    --noconfirm --clean `
    --distpath $distOut `
    --workpath "$root\build" 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { Write-Host $out; throw "PyInstaller onedir a echoue" }
($out -split "`n")[-4..-1] | ForEach-Object { "    $_" }

if (-not (Test-Path "$appRoot\lidar2map.exe")) {
    throw "$appRoot\lidar2map.exe introuvable apres build"
}
$appSize = (Get-ChildItem $appRoot -Recurse -File | Measure-Object Length -Sum).Sum / 1MB

Write-Host ""
Write-Host "=== BUILD TERMINE ===" -ForegroundColor Green
Write-Host ("  $appRoot  ({0:N1} Mo)" -f $appSize)
