# setup_build_windows.ps1 — Prepare un PC Windows pour builder lidar2map.exe
#
# 1. Installe Python 3.12 si absent (via winget ou python.org)
# 2. Lance lidar2map.py --installer-deps -> installe toutes les dependances
# 3. Telecharge osmosis + JRE via lidar2map.py --telecharger-outils
# 4. Installe PyInstaller
#
# Usage (PowerShell) :
#   Unblock-File .\setup_build_windows.ps1
#   .\setup_build_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = "$env:USERPROFILE\.lidar2map\venv"

function ok($msg)      { Write-Host "  [OK] $msg" -ForegroundColor Green }
function warn($msg)    { Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function step($n,$msg) { Write-Host "" ; Write-Host "[$n] $msg" -ForegroundColor Cyan }

# -- 1. Python 3.12 ------------------------------------------------------------
step "1/4" "Python 3.12"

$pyOk = $false
try {
    $ver = & python --version 2>&1
    if ($ver -match "3\.12") { $pyOk = $true; ok "Python trouve : $ver" }
} catch {}

if (-not $pyOk) {
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        Write-Host "  Installation via winget..."
        winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    } else {
        $installer = "$env:TEMP\python-3.12.10-amd64.exe"
        Write-Host "  Telechargement Python 3.12..."
        Invoke-WebRequest "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" `
            -OutFile $installer -UseBasicParsing
        Start-Process $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        Remove-Item $installer
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" `
              + [System.Environment]::GetEnvironmentVariable("Path","User")
    ok "Python 3.12 installe"
}

# -- 2. Bootstrap dependances --------------------------------------------------
step "2/4" "Bootstrap des dependances via lidar2map.py"
Write-Host "  Lancement avec --installer-deps..."
& python "$ScriptDir\lidar2map.py" --installer-deps

# Sanity check : depuis le refactor "venv systématique en mode auto", le
# bootstrap crée toujours ~/.lidar2map/venv. Si on arrive ici sans venv,
# c'est un cas anormal (--bootstrap=pip/none utilisé sans qu'on l'ait
# voulu, ou bug du bootstrap) → on échoue clairement plutôt que de
# masquer le problème en réinstallant à la main.
if (-not (Test-Path "$VENV\Scripts\pip.exe")) {
    Write-Host ""
    Write-Host "  ERREUR : venv attendu introuvable a $VENV" -ForegroundColor Red
    Write-Host "  Le bootstrap aurait du le creer. Causes possibles :"
    Write-Host "    - LIDAR2MAP_BOOTSTRAP=pip ou =none dans l'environnement"
    Write-Host "    - --bootstrap=pip ou --bootstrap=none passe a python.exe"
    Write-Host "    - bug interne du bootstrap (voir log ci-dessus)"
    exit 1
}
ok "Dependances installees dans $VENV"

# -- 3. osmosis + JRE ----------------------------------------------------------
step "3/4" "Telechargement osmosis + JRE"
Write-Host "  Necessaires pour les bundler dans lidar2map_bundle.zip..."
& python "$ScriptDir\lidar2map.py" --telecharger-outils
ok "Outils disponibles dans $env:USERPROFILE\.lidar2map"

# -- 4. PyInstaller ------------------------------------------------------------
step "4/4" "PyInstaller"
& "$VENV\Scripts\pip.exe" install --quiet pyinstaller
$pyiVer = & "$VENV\Scripts\pyinstaller.exe" --version
ok "PyInstaller $pyiVer"

Write-Host ""
ok "Setup termine. Pour builder :"
Write-Host "    .\lidar2map_win_build.ps1"
