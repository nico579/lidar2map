#!/usr/bin/env bash
# setup_build_linux.sh — Prépare un Ubuntu/Debian pour builder lidar2map
#
# 4 étapes (miroir de setup_build_windows.ps1 / setup_build_mac.sh) :
#   1. python3.12 + python3.12-venv via apt
#      (python3.12-venv est un paquet séparé sur Debian/Ubuntu — sans lui,
#       la création de venv est impossible)
#   2. --installer-deps → toutes les dépendances Python dans ~/.lidar2map/venv
#   3. --telecharger-outils → osmosis + JRE dans ~/.lidar2map/
#   4. PyInstaller dans ce venv
#
# Usage : bash setup_build_linux.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.lidar2map/venv"

G="\033[0;32m"; N="\033[0m"
ok()   { echo -e "${G}  ✓ $*${N}"; }
step() { echo -e "\n${G}[$1]${N} $2"; }

# ── 1. Python 3.12 + venv ─────────────────────────────────────────────────────
step "1/4" "Python 3.12 + python3.12-venv"

if ! command -v python3.12 &>/dev/null; then
    echo "  Python 3.12 absent — ajout du PPA deadsnakes..."
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update -qq
fi

# python3.12-venv est OBLIGATOIRE sur Debian/Ubuntu (paquet séparé)
sudo apt install -y python3.12 python3.12-venv
ok "$(python3.12 --version)"

# ── 2. lidar2map.py → bootstrap automatique de toutes les dépendances ─────────
step "2/4" "Bootstrap des dépendances via lidar2map.py"
echo "  Lancement avec --installer-deps pour déclencher l'installation et installe TOUTES les deps y compris lazy..."
python3.12 "$SCRIPT_DIR/lidar2map.py" --installer-deps
ok "Dépendances installées dans $VENV"

# ── 3. osmosis + JRE ─────────────────────────────────────────────────────────
step "3/4" "Téléchargement osmosis + JRE"
python3.12 "$SCRIPT_DIR/lidar2map.py" --telecharger-outils
ok "Outils disponibles dans ~/.lidar2map/"

# ── 4. PyInstaller ────────────────────────────────────────────────────────────
step "4/4" "PyInstaller"
"$VENV/bin/pip" install --quiet --disable-pip-version-check pyinstaller
ok "PyInstaller $("$VENV/bin/pyinstaller" --version)"

echo ""
ok "Setup terminé. Lance maintenant :"
echo "    bash lidar2map_linux_build.sh"
echo "  → dist/lidar2map + dist/lidar2map_bundle.zip"
