#!/usr/bin/env bash
# lidar2map_linux_build.sh — Build complet du launcher lidar2map (Linux)
#
# Miroir bash de lidar2map_win_build.ps1. Reutilise les specs _win.spec
# (PyInstaller produit un ELF sous Linux, le nom est trompeur).
#
# 3 etapes :
#   1. PyInstaller onedir       -> dist_onedir/lidar2map/    (la vraie app)
#   2. zip                      -> build/lidar2map_bundle.zip
#   3. PyInstaller launcher     -> dist/lidar2map            (launcher leger)
#      + copie lidar2map_bundle.zip a cote du binaire
#
# Mise a jour sans rebuild :
#   Ouvrir lidar2map_bundle.zip -> _internal/ -> remplacer lidar2map.py
#
# Usage :
#   bash lidar2map_linux_build.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.lidar2map/venv"
PYI="$VENV/bin/pyinstaller"

ONEDIR_OUT="$ROOT/dist_onedir"
ONEDIR_ROOT="$ONEDIR_OUT/lidar2map"
BUNDLE_ZIP="$ROOT/build/lidar2map_bundle.zip"
FINAL_OUT="$ROOT/dist"
FINAL_BIN="$FINAL_OUT/lidar2map"
FINAL_ZIP="$FINAL_OUT/lidar2map_bundle.zip"

C="\033[0;36m"; G="\033[0;32m"; Y="\033[0;33m"; N="\033[0m"

# ── Prerequis ─────────────────────────────────────────────────────────────────
if [[ ! -x "$PYI" ]]; then
    echo "PyInstaller introuvable : $PYI" >&2
    echo "Lance d'abord : bash setup_build_linux.sh" >&2
    exit 1
fi
if ! command -v zip &>/dev/null; then
    echo "zip absent. Installer : sudo apt install zip" >&2
    exit 1
fi

# ── 1. PyInstaller onedir ─────────────────────────────────────────────────────
echo -e "\n${C}[1/3] PyInstaller onedir (lidar2map_win.spec)...${N}"
"$PYI" "$ROOT/lidar2map_win.spec" \
    --noconfirm --clean \
    --distpath "$ONEDIR_OUT" \
    --workpath "$ROOT/build"

if [[ ! -x "$ONEDIR_ROOT/lidar2map" ]]; then
    echo "$ONEDIR_ROOT/lidar2map introuvable apres build" >&2
    exit 1
fi
onedir_size=$(du -sm "$ONEDIR_ROOT" | cut -f1)
echo "    Onedir : ${onedir_size} Mo"

# ── 2. Zip du onedir (contenu sans dossier parent — structure plate) ──────────
echo -e "\n${C}[2/3] Compression onedir -> bundle.zip...${N}"
mkdir -p "$(dirname "$BUNDLE_ZIP")"
rm -f "$BUNDLE_ZIP"
t0=$(date +%s)
( cd "$ONEDIR_ROOT" && zip -rq "$BUNDLE_ZIP" . )
t1=$(date +%s)
bundle_size=$(du -m "$BUNDLE_ZIP" | cut -f1)
echo "    Bundle : ${bundle_size} Mo en $((t1 - t0))s"

# ── 3. PyInstaller launcher (leger — sans bundle embarque) ────────────────────
echo -e "\n${C}[3/3] PyInstaller launcher (lidar2map_win_launcher.spec)...${N}"
"$PYI" "$ROOT/lidar2map_win_launcher.spec" \
    --noconfirm --clean \
    --distpath "$FINAL_OUT" \
    --workpath "$ROOT/build"

if [[ ! -x "$FINAL_BIN" ]]; then
    echo "$FINAL_BIN introuvable apres build" >&2
    exit 1
fi

# Copier le bundle a cote du binaire (separe -> remplacable sans rebuilder)
cp -f "$BUNDLE_ZIP" "$FINAL_ZIP"
echo "    Bundle copie : $FINAL_ZIP"

final_size=$(du -m "$FINAL_BIN" | cut -f1)
final_zip_size=$(du -m "$FINAL_ZIP" | cut -f1)

echo ""
echo -e "${G}=== BUILD TERMINE ===${N}"
echo -e "${G}  Livrables :${N}"
echo "    $FINAL_BIN  (${final_size} Mo)"
echo "    $FINAL_ZIP  (${final_zip_size} Mo)"
echo ""
echo -e "${Y}  Mise a jour sans rebuild :${N}"
echo "    Ouvrir lidar2map_bundle.zip -> _internal/ -> remplacer lidar2map.py"
