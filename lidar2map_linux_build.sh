#!/usr/bin/env bash
# lidar2map_linux_build.sh : build de lidar2map (Linux, PyInstaller onedir)
#
# Miroir bash de lidar2map_win_build.ps1. Reutilise lidar2map_win.spec
# (PyInstaller produit un ELF sous Linux, le nom est trompeur).
#
# Une seule passe PyInstaller -> dist/lidar2map/ (lidar2map + _internal/),
# le programme tel qu'il est livre. release.yml archive ensuite ce dossier.
# Jusqu'a la 1.54, un lanceur l'extrayait dans ~/.local/share au premier
# lancement ; depuis la 1.55, le dossier est livre tel quel.
#
# Usage :
#   bash lidar2map_linux_build.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.lidar2map/venv"
PYI="$VENV/bin/pyinstaller"

DIST_OUT="$ROOT/dist"
APP_ROOT="$DIST_OUT/lidar2map"

C="\033[0;36m"; G="\033[0;32m"; N="\033[0m"

# ── Prerequis ─────────────────────────────────────────────────────────────────
if [[ ! -x "$PYI" ]]; then
    echo "PyInstaller introuvable : $PYI" >&2
    echo "Lance d'abord : bash setup_build_linux.sh" >&2
    exit 1
fi

# ── PyInstaller onedir ────────────────────────────────────────────────────────
echo -e "\n${C}PyInstaller onedir (lidar2map_win.spec)...${N}"
"$PYI" "$ROOT/lidar2map_win.spec" \
    --noconfirm --clean \
    --distpath "$DIST_OUT" \
    --workpath "$ROOT/build"

if [[ ! -x "$APP_ROOT/lidar2map" ]]; then
    echo "$APP_ROOT/lidar2map introuvable apres build" >&2
    exit 1
fi
app_size=$(du -sm "$APP_ROOT" | cut -f1)

echo ""
echo -e "${G}=== BUILD TERMINE ===${N}"
echo "    $APP_ROOT  (${app_size} Mo)"
