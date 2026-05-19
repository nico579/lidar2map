#!/usr/bin/env python3
# update_app.py — Met à jour lidar2map.py dans le bundle (macOS / Windows / Linux)
#
# Prérequis : lidar2map.py et le bundle dans le même dossier.
#
# Usage :
#   macOS/Linux : python3 update_app.py
#   Windows     : python update_app.py

import sys, zipfile, hashlib, platform, os
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
BUNDLE = _find_bundle()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

# Vérifications
if not SCRIPT.exists(): sys.exit(f"ERREUR : {SCRIPT} introuvable")
if not BUNDLE.exists(): sys.exit(f"ERREUR : {BUNDLE} introuvable")

with zipfile.ZipFile(BUNDLE) as z:
    if TARGET not in z.namelist():
        sys.exit(f"ERREUR : {TARGET} absent du zip")
    current = z.read(TARGET)

new_content = SCRIPT.read_bytes()

if current == new_content:
    print("Déjà à jour — aucune modification.")
    sys.exit(0)

# Validation syntaxique : un .py cassé injecté dans le zip rendrait l'app
# non lançable sans rebuild. compile() lève SyntaxError si invalide.
try:
    compile(new_content, str(SCRIPT), "exec")
except SyntaxError as e:
    sys.exit(f"ERREUR : {SCRIPT.name} contient une SyntaxError ({e}) — abandon")

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
