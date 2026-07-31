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
# "-" = signature ad hoc gratuite. Pour une release notarisee, fournir le nom
# exact du certificat, ex. "Developer ID Application: Example (TEAMID)".
CODESIGN_IDENTITY="${LIDAR2MAP_CODESIGN_IDENTITY:--}"
ENTITLEMENTS_FILE="$ROOT/macos.entitlements"
NOTARY_PROFILE="${LIDAR2MAP_NOTARY_PROFILE:-}"
NOTARY_KEYCHAIN="${LIDAR2MAP_NOTARY_KEYCHAIN:-}"

# Archi du livrable : celle du Python du venv, pas celle du shell. PyInstaller
# produit un binaire pour l'interpreteur qu'il utilise ; sous Rosetta, `uname -m`
# mentirait (x86_64 alors que le venv peut etre arm64, ou l'inverse).
ARCH="$("$VENV/bin/python" -c 'import platform; print(platform.machine())')"
echo "Architecture cible : $ARCH"
if [ "$CODESIGN_IDENTITY" = "-" ]; then
    echo "Signature finale : ad hoc"
else
    echo "Signature finale : Developer ID ($CODESIGN_IDENTITY)"
fi

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

# Les wheels Intel de pyproj et rasterio embarquent chacune un
# libtiff.6.dylib sous le même install-name. Sur le build Intel observé en
# conditions réelles, dyld choisit la copie pyproj, incompatible avec les
# extensions rasterio ; la compression TIFF échoue alors avant même la GUI.
# Conserver la copie rasterio qui exerce effectivement l'I/O TIFF, à
# l'emplacement attendu par pyproj. Le correctif est limité à x86_64 et n'est
# appliqué que si les deux dylibs existent.
if [ "$ARCH" = "x86_64" ]; then
    PYPROJ_TIFF=$(find "$ONEDIR_ROOT/_internal/pyproj/.dylibs" \
        -name 'libtiff.6.dylib' -type f -print -quit 2>/dev/null || true)
    RASTERIO_TIFF=$(find "$ONEDIR_ROOT/_internal/rasterio/.dylibs" \
        -name 'libtiff.6.dylib' -type f -print -quit 2>/dev/null || true)
    if [ -n "$PYPROJ_TIFF" ] && [ -n "$RASTERIO_TIFF" ]; then
        echo "  Intel : harmonisation libtiff pyproj <- rasterio"
        cp "$RASTERIO_TIFF" "$PYPROJ_TIFF"
        if [ "$CODESIGN_IDENTITY" = "-" ]; then
            codesign --force --sign - "$PYPROJ_TIFF"
        else
            codesign --force --timestamp --sign "$CODESIGN_IDENTITY" "$PYPROJ_TIFF"
        fi
        codesign --verify --strict --verbose=2 "$PYPROJ_TIFF"
    else
        echo "  ATTENTION : paire libtiff pyproj/rasterio introuvable ; audit requis"
    fi
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

# PyInstaller signe le .app avant la copie ci-dessus. Cette copie modifie le
# resource seal et provoquait "LIDAR2MAP.app is damaged" une fois le ZIP
# marque com.apple.quarantine par le navigateur. La signature du bundle COMPLET
# doit donc impérativement être la dernière mutation avant l'archivage.
echo "  Signature du bundle complet..."
if [ "$CODESIGN_IDENTITY" = "-" ]; then
    codesign --force --deep --all-architectures --sign - "$FINAL_APP"
else
    if [ ! -f "$ENTITLEMENTS_FILE" ]; then
        echo "ERREUR : entitlements introuvables : $ENTITLEMENTS_FILE" >&2
        exit 1
    fi
    codesign --force --deep --all-architectures --options runtime --timestamp \
        --entitlements "$ENTITLEMENTS_FILE" \
        --sign "$CODESIGN_IDENTITY" "$FINAL_APP"
fi
codesign --verify --deep --strict --verbose=2 "$FINAL_APP"

FINAL_SIZE=$(du -sm "$FINAL_APP" | cut -f1)

# Supprimer l'exécutable brut intermédiaire (artefact PyInstaller EXE,
# déjà embarqué dans LIDAR2MAP.app/Contents/MacOS/lidar2map)
rm -f "$FINAL_OUT/lidar2map"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Archive zip pour distribution (ditto preserve permissions + symlinks +
#    xattrs, indispensable pour une .app extractable sur un autre Mac)
# ─────────────────────────────────────────────────────────────────────────────
RELEASE_ZIP="$FINAL_OUT/lidar2map-macos-$ARCH.zip"
echo ""
echo "[4/4] Archive distribution (ditto)..."
rm -f "$RELEASE_ZIP"
ditto -c -k --keepParent "$FINAL_APP" "$RELEASE_ZIP"

# Notarisation optionnelle : le profil est créé une fois avec
# `xcrun notarytool store-credentials`. Après acceptation, stapler modifie le
# .app ; recréer le ZIP est donc nécessaire pour distribuer le ticket agrafé.
if [ -n "$NOTARY_PROFILE" ]; then
    if [ "$CODESIGN_IDENTITY" = "-" ]; then
        echo "ERREUR : notarisation demandee avec une signature ad hoc." >&2
        exit 1
    fi
    echo "  Notarisation Apple..."
    if [ -n "$NOTARY_KEYCHAIN" ]; then
        xcrun notarytool submit "$RELEASE_ZIP" \
            --keychain-profile "$NOTARY_PROFILE" \
            --keychain "$NOTARY_KEYCHAIN" --wait
    else
        xcrun notarytool submit "$RELEASE_ZIP" \
            --keychain-profile "$NOTARY_PROFILE" --wait
    fi
    xcrun stapler staple "$FINAL_APP"
    xcrun stapler validate "$FINAL_APP"
    spctl --assess --type execute --verbose=4 "$FINAL_APP"
    rm -f "$RELEASE_ZIP"
    ditto -c -k --keepParent "$FINAL_APP" "$RELEASE_ZIP"
fi

ZIP_SIZE=$(du -sm "$RELEASE_ZIP" | cut -f1)
ZIP_SHA=$(shasum -a 256 "$RELEASE_ZIP" | awk '{print $1}')

echo ""
echo "=== BUILD TERMINE ==="
echo "  Livrables :"
echo "    $FINAL_APP   (${FINAL_SIZE} Mo)"
echo "    $RELEASE_ZIP (${ZIP_SIZE} Mo)"
echo "    sha256       $ZIP_SHA"
echo ""
if [ "$CODESIGN_IDENTITY" = "-" ]; then
    echo "  Note : signature ad hoc valide, mais application non notarisee."
    echo "  Gatekeeper demandera une autorisation au premier lancement."
    echo "  Contournement pour un build de confiance :"
    echo "    xattr -dr com.apple.quarantine \"$FINAL_APP\""
else
    echo "  Signature Developer ID valide."
    if [ -n "$NOTARY_PROFILE" ]; then
        echo "  Notarisation acceptee et ticket agrafe."
    else
        echo "  ATTENTION : notarisation non demandee (LIDAR2MAP_NOTARY_PROFILE vide)."
    fi
fi
