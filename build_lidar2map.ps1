# build.ps1 — Build complet du launcher lidar2map.exe
#
# 3 étapes :
#   1. PyInstaller onedir         → dist/lidar2map_build/ (la vraie app, ~617 Mo)
#   2. Compress-Archive (zip)     → build/lidar2map_bundle.zip (~250 Mo)
#   3. PyInstaller launcher onefile → dist/lidar2map.exe (livrable final, ~250 Mo)
#
# Usage :
#   PowerShell -ExecutionPolicy Bypass -File build.ps1
#
# Comportement utilisateur du livrable :
#   - Premier lancement : extraction dans %LOCALAPPDATA%\lidar2map (~5-10 s, une fois)
#   - Lancements suivants : skip extract si SHA bundle inchangé (~1 s)
#   - Mise à jour (nouveau .exe livré) : SHA différent → ré-extraction propre
#   - Console transparente, args CLI forwardés à l'exe interne
$root  = "C:\Users\Nico\Documents\lidar\var"
$venv  = "C:\Users\Nico\.lidar2map\venv"
$pyi   = "$venv\Scripts\pyinstaller.exe"

# Dossiers de travail
$onedirOut   = "$root\dist_onedir"        # build onedir intermediaire
$bundleZip   = "$root\build\lidar2map_bundle.zip"
$finalOut    = "$root\dist"                # livrable final ici

# ─────────────────────────────────────────────────────────────────────────────
# 1. PyInstaller onedir (la vraie app)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[1/3] PyInstaller onedir (lidar2map.spec)..." -ForegroundColor Cyan
$out = & $pyi "$root\lidar2map.spec" `
    --noconfirm --clean `
    --distpath $onedirOut `
    --workpath "$root\build" 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host $out
    throw "PyInstaller onedir a echoue (exit $LASTEXITCODE)"
}
($out -split "`n")[-4..-1] | ForEach-Object { "    $_" }
$onedirRoot = "$onedirOut\lidar2map"
if (-not (Test-Path "$onedirRoot\lidar2map.exe")) {
    throw "$onedirRoot\lidar2map.exe introuvable apres build"
}
$onedirSize = (Get-ChildItem $onedirRoot -Recurse | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("    Onedir : {0:N1} Mo" -f $onedirSize)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Zip du onedir
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/3] Compression onedir -> bundle.zip..." -ForegroundColor Cyan
if (Test-Path $bundleZip) { Remove-Item $bundleZip }
New-Item -ItemType Directory -Force -Path (Split-Path $bundleZip) | Out-Null
# Compress-Archive de PowerShell utilise .NET ZipArchive (deflate niveau optimal).
# Plus rapide que 7z et compatible zipfile Python (qui lit le bundle au runtime).
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Compress-Archive -Path "$onedirRoot\*" -DestinationPath $bundleZip -CompressionLevel Optimal -Force
$sw.Stop()
$bundleSize = (Get-Item $bundleZip).Length / 1MB
Write-Host ("    Bundle : {0:N1} Mo en {1:N1}s" -f $bundleSize, $sw.Elapsed.TotalSeconds)

# ─────────────────────────────────────────────────────────────────────────────
# 3. PyInstaller launcher onefile (avec le bundle en data)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/3] PyInstaller launcher onefile (launcher.spec)..." -ForegroundColor Cyan
$out = & $pyi "$root\launcher.spec" `
    --noconfirm --clean `
    --distpath $finalOut `
    --workpath "$root\build" 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host $out
    throw "PyInstaller launcher a echoue (exit $LASTEXITCODE)"
}
($out -split "`n")[-4..-1] | ForEach-Object { "    $_" }

$finalExe = "$finalOut\lidar2map.exe"
if (-not (Test-Path $finalExe)) {
    throw "$finalExe introuvable apres build launcher"
}
$finalSize = (Get-Item $finalExe).Length / 1MB

Write-Host ""
Write-Host "=== BUILD TERMINE ===" -ForegroundColor Green
Write-Host ("  Livrable : $finalExe") -ForegroundColor Green
Write-Host ("  Taille   : {0:N1} Mo" -f $finalSize) -ForegroundColor Green
