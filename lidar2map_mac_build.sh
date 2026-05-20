#!/usr/bin/env bash
# lidar2map_mac_build.sh — Build complet du launcher LIDAR2MAP.app
#
# 3 étapes (miroir exact de lidar2map_win_build.ps1) :
#   1. PyInstaller onedir         -> dist_onedir/lidar2map/  (la vraie app)
#   2. zip                        -> build/lidar2map_bundle.zip
#   3. PyInstaller launcher .app  -> dist/LIDAR2MAP.app     (livrable final)
#
# Usage :
#   bash lidar2map_mac_build.sh
#
# Comportement utilisateur du livrable :
#   - Premier lancement : extraction dans ~/Library/Application Support/lidar2map/ (~5-10 s, une fois)
#   - Lancements suivants : skip extract si SHA bundle inchangé (~1 s)
#   - Mise à jour (nouveau .app livré) : SHA différent -> ré-extraction propre

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Un seul venv ~/.lidar2map/venv contient à la fois les deps runtime
# (créé par setup_build_mac.sh via --installer-deps) ET pyinstaller
# (ajouté en étape 4 du setup). Aligné sur Windows (lidar2map_win_build.ps1).
VENV="$HOME/.lidar2map/venv"
PYI="$VENV/bin/pyinstaller"

if [ ! -x "$PYI" ]; then
    echo "ERREUR : $PYI introuvable."
    echo "  Lance d'abord :  bash setup_build_mac.sh"
    exit 1
fi

ONEDIR_OUT="$ROOT/dist_onedir"
ONEDIR_ROOT="$ONEDIR_OUT/lidar2map"
BUILD_DIR="$ROOT/build"
BUNDLE_ZIP="$BUILD_DIR/lidar2map_bundle.zip"
FINAL_OUT="$ROOT/dist"
FINAL_APP="$FINAL_OUT/LIDAR2MAP.app"

# ─────────────────────────────────────────────────────────────────────────────
# 1. PyInstaller onedir (la vraie app)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[1/3] PyInstaller onedir (lidar2map_mac.spec)..."
"$PYI" "$ROOT/lidar2map_mac.spec" \
    --noconfirm --clean \
    --distpath "$ONEDIR_OUT" \
    --workpath "$BUILD_DIR"

if [ ! -f "$ONEDIR_ROOT/lidar2map" ]; then
    echo "ERREUR : $ONEDIR_ROOT/lidar2map introuvable apres build"
    exit 1
fi

ONEDIR_SIZE=$(du -sm "$ONEDIR_ROOT" | cut -f1)
echo "    Onedir : ${ONEDIR_SIZE} Mo"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Zip du onedir
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[2/3] Compression onedir -> bundle.zip..."
mkdir -p "$BUILD_DIR"
rm -f "$BUNDLE_ZIP"

START_TS=$(date +%s)
# ditto sans --keepParent : zip le CONTENU de lidar2map/ (pas le dossier lui-même)
# → extraction dans _app_dir donne directement lidar2map + _internal/
# Identique à Windows : Compress-Archive -Path "$onedirRoot\*"
cd "$ONEDIR_OUT/lidar2map"
ditto -c -k . "$BUNDLE_ZIP"
cd "$ROOT"

END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))
BUNDLE_SIZE=$(du -sm "$BUNDLE_ZIP" | cut -f1)
echo "    Bundle : ${BUNDLE_SIZE} Mo en ${ELAPSED}s"

# ─────────────────────────────────────────────────────────────────────────────
# 3. PyInstaller launcher .app (avec le bundle en data)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[3/3] PyInstaller launcher .app (lidar2map_mac_launcher.spec)..."
"$PYI" "$ROOT/lidar2map_mac_launcher.spec" \
    --noconfirm --clean \
    --distpath "$FINAL_OUT" \
    --workpath "$BUILD_DIR"

if [ ! -d "$FINAL_APP" ]; then
    echo "ERREUR : $FINAL_APP introuvable apres build launcher"
    exit 1
fi

# Copier le bundle zip dans Contents/Resources/
# → séparé du binaire launcher → remplaçable depuis Windows sans rebuilder
echo "  Copie du bundle dans Contents/Resources/..."
mkdir -p "$FINAL_APP/Contents/Resources"
cp "$BUNDLE_ZIP" "$FINAL_APP/Contents/Resources/lidar2map_bundle.zip"
echo "  → $FINAL_APP/Contents/Resources/lidar2map_bundle.zip"

FINAL_SIZE=$(du -sm "$FINAL_APP" | cut -f1)

# Supprimer l'exécutable brut intermédiaire (artefact PyInstaller EXE,
# déjà embarqué dans LIDAR2MAP.app/Contents/MacOS/lidar2map)
rm -f "$FINAL_OUT/lidar2map"

echo ""
echo "=== BUILD TERMINE ==="
echo "  Livrable : $FINAL_APP"
echo "  Taille   : ${FINAL_SIZE} Mo"
echo ""
echo "  Note : .app non signe -> macOS affichera une alerte Gatekeeper"
echo "  au premier lancement. Pour contourner :"
echo "    xattr -dr com.apple.quarantine \"$FINAL_APP\""
echo "  Ou clic droit -> Ouvrir -> Ouvrir quand meme."
