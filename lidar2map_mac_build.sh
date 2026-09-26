#!/usr/bin/env bash
# lidar2map_mac_build.sh : build de LIDAR2MAP.app (PyInstaller onedir + .app)
#
# 3 étapes :
#   1. PyInstaller                -> dist/LIDAR2MAP.app   (le programme livré)
#   2. signature du .app complet
#   3. archive ditto              -> dist/lidar2map-macos-<arch>.zip
#      (notarisée si LIDAR2MAP_NOTARY_PROFILE est fourni)
#
# Jusqu'à la 1.54, LIDAR2MAP.app était un lanceur qui contenait le programme
# zippé et l'extrayait dans ~/Library/Application Support/lidar2map au
# premier lancement. Depuis la 1.55, le .app est le programme lui-même, comme
# les dossiers livrés par blink2video et watch2notif.
#
# Usage :
#   bash lidar2map_mac_build.sh

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

DIST_OUT="$ROOT/dist"
BUILD_DIR="$ROOT/build"
FINAL_APP="$DIST_OUT/LIDAR2MAP.app"
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
# 1. PyInstaller : dossier onedir, puis .app (BUNDLE de lidar2map_mac.spec)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[1/3] PyInstaller (lidar2map_mac.spec)..."
"$PYI" "$ROOT/lidar2map_mac.spec" \
    --noconfirm --clean \
    --distpath "$DIST_OUT" \
    --workpath "$BUILD_DIR"

if [ ! -x "$FINAL_APP/Contents/MacOS/lidar2map" ]; then
    echo "ERREUR : $FINAL_APP/Contents/MacOS/lidar2map introuvable apres build"
    exit 1
fi
# Le dossier onedir intermédiaire, déjà recopié dans le .app.
rm -rf "$DIST_OUT/lidar2map"

# Les wheels Intel de pyproj et rasterio embarquent chacune un
# libtiff.6.dylib sous le même install-name. Sur le build Intel observé en
# conditions réelles, dyld choisit la copie pyproj, incompatible avec les
# extensions rasterio ; la compression TIFF échoue alors avant même la GUI.
# Conserver la copie rasterio qui exerce effectivement l'I/O TIFF, à
# l'emplacement attendu par pyproj. Le correctif est limité à x86_64 et n'est
# appliqué que si les deux dylibs existent.
#
# Dans le .app, PyInstaller range les bibliothèques sous Contents/Frameworks,
# où codesign n'admet de point dans un nom de dossier que pour un .framework :
# .dylibs y devient __dot__dylibs, et un lien symbolique .dylibs y mène. Le
# vrai fichier est cherché sous les deux noms, sans suivre les liens.
libtiff_de() {
    find "$FINAL_APP/Contents/Frameworks" -type f \
        \( -path "*/$1/.dylibs/libtiff.6.dylib" \
           -o -path "*/$1/__dot__dylibs/libtiff.6.dylib" \) \
        -print -quit 2>/dev/null || true
}
if [ "$ARCH" = "x86_64" ]; then
    PYPROJ_TIFF=$(libtiff_de pyproj)
    RASTERIO_TIFF=$(libtiff_de rasterio)
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

# ─────────────────────────────────────────────────────────────────────────────
# 2. Signature du .app complet
# ─────────────────────────────────────────────────────────────────────────────
# PyInstaller signe le .app à la fin de BUNDLE, avant le correctif Intel
# ci-dessus. Toute modification après coup rompt le sceau des ressources, et
# macOS déclarait alors "LIDAR2MAP.app is damaged" une fois le ZIP marqué
# com.apple.quarantine par le navigateur. La signature du bundle COMPLET doit
# donc impérativement être la dernière mutation avant l'archivage.
echo ""
echo "[2/3] Signature du bundle complet..."
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

# ─────────────────────────────────────────────────────────────────────────────
# 3. Archive zip pour distribution (ditto preserve permissions + symlinks +
#    xattrs, indispensable pour une .app extractable sur un autre Mac)
# ─────────────────────────────────────────────────────────────────────────────
RELEASE_ZIP="$DIST_OUT/lidar2map-macos-$ARCH.zip"
echo ""
echo "[3/3] Archive distribution (ditto)..."
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
