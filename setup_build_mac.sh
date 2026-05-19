#!/usr/bin/env bash
# setup_build_mac.sh — Prepare un Mac ARM64 pour builder LIDAR2MAP.app
#
# 1. Installe Python 3.12 si absent (depuis python.org)
# 2. Lance lidar2map.py --installer-deps -> installe toutes les dependances
# 3. Telecharge osmosis + JRE via lidar2map.py --telecharger-outils
# 4. Installe PyInstaller
#
# Usage : bash setup_build_mac.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.lidar2map/venv"

G="\033[0;32m"; Y="\033[0;33m"; N="\033[0m"
ok()   { echo -e "${G}  OK $*${N}"; }
warn() { echo -e "${Y}  !! $*${N}"; }
step() { echo -e "\n${G}[$1]${N} $2"; }

# -- 1. Python 3.12 ------------------------------------------------------------
step "1/4" "Python 3.12"
_python=""
for p in python3.12 \
          /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
          /opt/homebrew/bin/python3.12; do
    command -v "$p" &>/dev/null && { _python="$p"; break; }
done

if [[ -n "$_python" ]]; then
    ok "$($_python --version) -> $_python"
else
    _pkg="python-3.12.10-macos11.pkg"
    echo "  Telechargement Python 3.12..."
    curl -L --progress-bar \
        "https://www.python.org/ftp/python/3.12.10/$_pkg" -o "/tmp/$_pkg"
    sudo installer -pkg "/tmp/$_pkg" -target /
    rm -f "/tmp/$_pkg"
    _python="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
    ok "$($_python --version)"
fi

# -- 2. Bootstrap dependances --------------------------------------------------
step "2/4" "Bootstrap des dependances via lidar2map.py"
echo "  Lancement avec --installer-deps..."
"$_python" "$SCRIPT_DIR/lidar2map.py" --installer-deps

# Sanity check : depuis le refactor "venv systematique en mode auto", le
# bootstrap cree toujours ~/.lidar2map/venv. Si on arrive ici sans venv,
# c'est un cas anormal → echec clair plutot que reinstall masquee.
if [[ ! -f "$VENV/bin/pip" ]]; then
    echo ""
    echo "  ERREUR : venv attendu introuvable a $VENV"
    echo "  Le bootstrap aurait du le creer. Causes possibles :"
    echo "    - LIDAR2MAP_BOOTSTRAP=pip ou =none dans l'environnement"
    echo "    - --bootstrap=pip ou --bootstrap=none passe a python"
    echo "    - bug interne du bootstrap (voir log ci-dessus)"
    exit 1
fi
ok "Dependances installees dans $VENV"

# -- 3. osmosis + JRE ----------------------------------------------------------
step "3/4" "Telechargement osmosis + JRE"
echo "  Necessaires pour les bundler dans le .app..."
"$VENV/bin/python" "$SCRIPT_DIR/lidar2map.py" --telecharger-outils
ok "Outils disponibles dans ~/.lidar2map/"

# -- 4. PyInstaller ------------------------------------------------------------
step "4/4" "PyInstaller"
"$VENV/bin/pip" install --quiet --disable-pip-version-check pyinstaller
ok "PyInstaller $("$VENV/bin/pyinstaller" --version)"

echo ""
ok "Setup termine. Pour builder :"
echo "    bash lidar2map_mac_build.sh"
