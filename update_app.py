#!/usr/bin/env python3
# update_app.py — Met à jour lidar2map.py dans le bundle (macOS / Windows / Linux)
#
# Prérequis : lidar2map.py et le bundle dans le même dossier.
#
# Usage :
#   macOS/Linux : python3 update_app.py
#   Windows     : python update_app.py
#
# Mode archive macOS (édition chirurgicale depuis n'importe quel OS) :
#   python update_app.py lidar2map-macos-arm64.zip
#     → patch _internal/lidar2map.py dans le bundle interne tout en préservant
#       les permissions Unix de Contents/MacOS/lidar2map (bit exécutable).
#     Permet de publier un correctif Mac sans accès à un Mac : seules les
#       données du bundle interne sont régénérées, les ZipInfo de toutes les
#       autres entrées (external_attr Unix) sont recopiées verbatim.

import sys, zipfile, hashlib, platform, os, io
from pathlib import Path

# Forcer UTF-8 sur stdout (Windows console est en cp1252 par défaut et le
# script affiche ✓ → UnicodeEncodeError sinon). Idem pattern lidar2map.py.
for _std in ("stdout", "stderr"):
    _s = getattr(sys, _std, None)
    if _s is not None and getattr(_s, "encoding", "").lower() != "utf-8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

HERE   = Path(__file__).resolve().parent
SCRIPT = HERE / "lidar2map.py"
TARGET = "_internal/lidar2map.py"

_sys = platform.system()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

# ── Mode archive macOS ──────────────────────────────────────────────────────
# Si appelé avec un argument pointant vers lidar2map-macos-*.zip, on patche
# le bundle interne en place sans repasser par un build Mac. Indispensable
# pour shipper un fix depuis Windows : Compress-Archive perdrait le bit
# exécutable de Contents/MacOS/lidar2map.
def _update_macos_archive(outer_path, new_script_bytes):
    """Remplace _internal/lidar2map.py dans le bundle interne d'une archive
    macOS, en préservant tous les ZipInfo des entrées non touchées (donc les
    permissions Unix de Contents/MacOS/lidar2map et les symlinks)."""

    # 1. Localiser l'entrée Contents/Resources/lidar2map_bundle.zip dans l'archive
    with zipfile.ZipFile(outer_path, "r") as outer:
        inner_name = next(
            (n for n in outer.namelist()
             if n.endswith("/Contents/Resources/lidar2map_bundle.zip")),
            None)
        if inner_name is None:
            sys.exit(f"ERREUR : aucun Contents/Resources/lidar2map_bundle.zip "
                     f"dans {outer_path.name} — pas une archive .app valide.")
        inner_bytes = outer.read(inner_name)

    # 2. Régénérer le bundle interne avec le nouveau script
    new_inner = io.BytesIO()
    found = False
    with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as in_b, \
         zipfile.ZipFile(new_inner, "w", compression=zipfile.ZIP_DEFLATED) as out_b:
        for item in in_b.infolist():
            if item.filename == TARGET:
                out_b.writestr(item, new_script_bytes)
                found = True
            else:
                out_b.writestr(item, in_b.read(item.filename))
    if not found:
        sys.exit(f"ERREUR : {TARGET} absent du bundle interne.")
    new_inner_bytes = new_inner.getvalue()

    # 3. Réécrire l'archive externe en recopiant verbatim toutes les ZipInfo
    #    (external_attr conserve les permissions Unix encodées par ditto).
    tmp = outer_path.with_suffix(".zip.tmp")
    print(f"Mise à jour de {TARGET} dans {inner_name} de {outer_path.name}...")
    try:
        with zipfile.ZipFile(outer_path, "r") as z_in, \
             zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                data = new_inner_bytes if item.filename == inner_name \
                       else z_in.read(item.filename)
                z_out.writestr(item, data)
        os.replace(tmp, outer_path)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        sys.exit(f"ERREUR : {e}")

    print(f"  ✓ {TARGET} remplacé dans {inner_name}")
    print(f"  ✓ ZipInfo préservés sur les {len(zipfile.ZipFile(outer_path).infolist())} entrées")
    print(f"  SHA256 archive : {sha256(outer_path)[:16]}...")
    print("Terminé. Re-uploader l'archive sur la release.")


# Détection du mode archive macOS : argument CLI explicite OU auto-découverte
# d'un lidar2map-macos-*.zip à côté du script (workflow Windows-ship-Mac).
def _find_macos_archive():
    for _a in sys.argv[1:]:
        _p = Path(_a)
        if _p.exists() and _p.suffix == ".zip" and "macos" in _p.name.lower():
            return _p.resolve()
    for _c in (HERE / "lidar2map-macos-arm64.zip",
               HERE / "dist" / "lidar2map-macos-arm64.zip"):
        if _c.exists():
            return _c
    return None

# Recherche du bundle : à côté du script (livrable utilisateur) puis dans
# dist/ (workflow développeur après build). Mac : Contents/Resources/.
def _find_bundle():
    candidates = []
    if _sys == "Darwin":
        candidates += [HERE / "LIDAR2MAP.app" / "Contents" / "Resources" / "lidar2map_bundle.zip",
                       HERE / "dist" / "LIDAR2MAP.app" / "Contents" / "Resources" / "lidar2map_bundle.zip"]
    candidates += [HERE / "lidar2map_bundle.zip",
                   HERE / "dist" / "lidar2map_bundle.zip"]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]   # fallback : 1er candidat → message d'erreur explicite

# Vérifications source
if not SCRIPT.exists(): sys.exit(f"ERREUR : {SCRIPT} introuvable")
new_content = SCRIPT.read_bytes()

# Validation syntaxique : un .py cassé injecté dans le zip rendrait l'app
# non lançable sans rebuild. compile() lève SyntaxError si invalide.
try:
    compile(new_content, str(SCRIPT), "exec")
except SyntaxError as e:
    sys.exit(f"ERREUR : {SCRIPT.name} contient une SyntaxError ({e}) — abandon")

# Mode archive : un argument .zip macOS OU lidar2map-macos-arm64.zip auto-detecte
_archive = _find_macos_archive()
if _archive:
    _update_macos_archive(_archive, new_content)
    sys.exit(0)

# Mode bundle direct (Win/Linux livrable, ou Mac depuis le .app extrait)
BUNDLE = _find_bundle()
if not BUNDLE.exists(): sys.exit(f"ERREUR : {BUNDLE} introuvable")

with zipfile.ZipFile(BUNDLE) as z:
    if TARGET not in z.namelist():
        sys.exit(f"ERREUR : {TARGET} absent du zip")
    current = z.read(TARGET)

if current == new_content:
    print("Déjà à jour — aucune modification.")
    sys.exit(0)

# Réécrire le zip avec le nouveau lidar2map.py
# Opération atomique : écriture dans .tmp puis os.replace() (atomic sur
# même filesystem sur tous les OS). Si interrupted, le zip original est intact.
BUNDLE_TMP = BUNDLE.with_suffix(".zip.tmp")
print(f"Mise à jour de {TARGET} dans {BUNDLE.name}...")

try:
    with zipfile.ZipFile(BUNDLE, "r") as z_in, \
         zipfile.ZipFile(BUNDLE_TMP, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
        for item in z_in.infolist():
            data = new_content if item.filename == TARGET else z_in.read(item.filename)
            z_out.writestr(item, data)

    # os.replace() est atomique sur même filesystem (Linux/macOS/Windows)
    os.replace(BUNDLE_TMP, BUNDLE)

except Exception as e:
    BUNDLE_TMP.unlink(missing_ok=True)   # cleanup si échec
    sys.exit(f"ERREUR : {e}")

print(f"  ✓ {TARGET} remplacé")
print(f"  SHA256 bundle : {sha256(BUNDLE)[:16]}...")
print("Terminé. La nouvelle version sera active au prochain lancement.")
