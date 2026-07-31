#!/usr/bin/env bash
# setup_build_mac.sh — Prepare un Mac (Apple Silicon ou Intel) pour builder
# LIDAR2MAP.app. Le livrable prend l'archi de la machine : pas de
# cross-compilation possible avec PyInstaller. Le JRE telecharge par
# --telecharger-outils suit deja platform.machine() (aarch64 ou x64).
#
# 1. Installe Python 3.12 si absent (depuis python.org)
# 2. Sur Intel, installe libomp et les versions Python encore publiees en x64
# 3. Lance lidar2map.py --installer-deps -> installe toutes les dependances
# 4. Telecharge osmosis + JRE via lidar2map.py --telecharger-outils
# 5. Installe PyInstaller
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
step "1/5" "Python 3.12"
_python=""
for p in python3.12 \
          /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
          /opt/homebrew/bin/python3.12 \
          /usr/local/bin/python3.12; do   # /usr/local = Homebrew Intel
    command -v "$p" &>/dev/null && { _python="$p"; break; }
done

if [[ -n "$_python" ]]; then
    ok "$($_python --version) -> $_python"
else
    # 3.12.13 est une security release source-only : aucun .pkg macOS officiel.
    # 3.12.10 reste le dernier installeur autonome utilisé par ce fallback ;
    # GitHub Actions fournit directement son propre Python 3.12.
    _pkg="python-3.12.10-macos11.pkg"
    echo "  Telechargement Python 3.12..."
    curl -L --progress-bar \
        "https://www.python.org/ftp/python/3.12.10/$_pkg" -o "/tmp/$_pkg"
    sudo installer -pkg "/tmp/$_pkg" -target /
    rm -f "/tmp/$_pkg"
    _python="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
    ok "$($_python --version)"
fi

# -- 2. Prerequis Intel --------------------------------------------------------
step "2/5" "Prerequis propres a l'architecture"
_arch="$($_python -c 'import platform; print(platform.machine())')"
if [[ "$_arch" == "x86_64" ]]; then
    if ! command -v brew &>/dev/null; then
        echo "  ERREUR : Homebrew est requis sur Intel pour installer libomp." >&2
        exit 1
    fi
    brew list libomp &>/dev/null || brew install libomp
    ok "Intel x86_64 : libomp disponible"
else
    ok "$_arch : aucun prerequis Intel"
fi

# -- 3. Bootstrap dependances --------------------------------------------------
step "3/5" "Bootstrap des dependances via lidar2map.py"
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

# Numba 0.61+ ne publie plus de wheels macOS x86_64. Reposer explicitement la
# derniere pile Intel connue, après le bootstrap générique qui peut avoir
# installé une version arm64-only ou supprimé numba lors de son retry.
if [[ "$_arch" == "x86_64" ]]; then
    echo "  Alignement de la pile numerique Intel..."
    "$VENV/bin/pip" install --quiet --disable-pip-version-check \
        "numpy>=2.0,<2.1" "llvmlite==0.43.0" "numba==0.60.0"
    "$VENV/bin/python" -c \
        'import numpy, numba, llvmlite; print("  Intel Python stack:", numpy.__version__, numba.__version__, llvmlite.__version__)'
fi

# -- 4. osmosis + JRE ----------------------------------------------------------
step "4/5" "Telechargement osmosis + JRE"
echo "  Necessaires pour les bundler dans le .app..."
"$VENV/bin/python" "$SCRIPT_DIR/lidar2map.py" --telecharger-outils
ok "Outils disponibles dans ~/.lidar2map/"

# -- 5. PyInstaller ------------------------------------------------------------
step "5/5" "PyInstaller"
"$VENV/bin/pip" install --quiet --disable-pip-version-check pyinstaller
ok "PyInstaller $("$VENV/bin/pyinstaller" --version)"

echo ""
ok "Setup termine. Pour builder :"
echo "    bash lidar2map_mac_build.sh"
