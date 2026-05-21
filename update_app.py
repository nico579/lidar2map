#!/usr/bin/env python3
# update_app.py — Met à jour lidar2map.py dans le bundle (macOS / Windows / Linux)
#
# Prérequis : lidar2map.py et le bundle dans le même dossier.
#
# Modes :
#   1. Local bundle (workflow utilisateur) :
#        python3 update_app.py
#      Patche lidar2map_bundle.zip à côté du script ou dans dist/.
#
#   2. Archive macOS (édition chirurgicale depuis n'importe quel OS) :
#        python update_app.py lidar2map-macos-arm64.zip
#      Patch chirurgical du bundle interne en préservant les permissions
#      Unix de Contents/MacOS/lidar2map (bit exécutable).
#
#   3. Release complète (Windows + Linux + macOS, depuis n'importe quel OS) :
#        python update_app.py --release [--tag v1.1.0] [--dry-run]
#      Télécharge les 3 assets de la release, patche le bundle interne dans
#      chacun, met à jour mode 0o755 sur le launcher Linux (bug fix),
#      réuploade, met à jour le body avec les nouveaux SHA256.
#      Requiert un token GitHub (GH_TOKEN, GITHUB_TOKEN ou git credential).
#      --dry-run : exécute jusqu'au patch local (cache dans dist/release/)
#      sans appeler DELETE/UPLOAD/PATCH sur GitHub.

import sys, zipfile, hashlib, platform, os, io, json, tarfile, re
import urllib.request, urllib.error, subprocess
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

REPO_OWNER = "nico579"
REPO_NAME  = "lidar2map"

_sys = platform.system()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


# ── Helpers : patch chirurgical ──────────────────────────────────────────────

def _patch_inner_bundle(inner_bytes, new_script, extras=None):
    """Régénère un lidar2map_bundle.zip avec _internal/lidar2map.py remplacé.
    extras : dict {path_in_bundle: file_bytes} pour ajouter/remplacer des fichiers
             additionnels (ex: providers/*.py). Si une entrée extras coïncide
             avec un fichier existant dans le bundle, elle l'écrase.
    Renvoie les bytes du nouveau zip ou lève SystemExit si TARGET absent."""
    extras = extras or {}
    new_inner = io.BytesIO()
    found = False
    written_paths = set()
    with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as in_b, \
         zipfile.ZipFile(new_inner, "w", compression=zipfile.ZIP_DEFLATED) as out_b:
        for item in in_b.infolist():
            if item.filename == TARGET:
                out_b.writestr(item, new_script)
                found = True
            elif item.filename in extras:
                # Remplace via le ZipInfo existant pour préserver les permissions
                out_b.writestr(item, extras[item.filename])
            else:
                out_b.writestr(item, in_b.read(item.filename))
            written_paths.add(item.filename)
        # Ajoute les extras qui n'existaient pas (nouveau fichiers, ex: providers/*.py)
        for path, data in extras.items():
            if path not in written_paths:
                out_b.writestr(path, data, zipfile.ZIP_DEFLATED)
    if not found:
        sys.exit(f"ERREUR : {TARGET} absent du bundle interne.")
    return new_inner.getvalue()


def _patch_outer_zip(input_path, inner_name_endswith, new_inner_bytes, output_path):
    """Réécrit un zip externe en remplaçant l'entrée se terminant par
    inner_name_endswith par new_inner_bytes. Recopie verbatim les ZipInfo
    de toutes les autres entrées (external_attr, create_system, etc.) — ce
    qui préserve les permissions Unix de Contents/MacOS/lidar2map etc.
    Renvoie (nb_entries, inner_name) pour log."""
    with zipfile.ZipFile(input_path, "r") as z_in, \
         zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
        inner_name = None
        n = 0
        for item in z_in.infolist():
            n += 1
            if item.filename.endswith(inner_name_endswith):
                inner_name = item.filename
                z_out.writestr(item, new_inner_bytes)
            else:
                z_out.writestr(item, z_in.read(item.filename))
    if inner_name is None:
        sys.exit(f"ERREUR : aucune entrée se terminant par '{inner_name_endswith}' "
                 f"dans {Path(input_path).name}.")
    return n, inner_name


def _patch_linux_targz(input_path, output_path, new_script, extras=None):
    """Met à jour lidar2map_bundle.zip dans un tar.gz Linux. Bonus : force
    le mode du launcher à 0o755 si trouvé en 0o6xx (bug de packaging
    original — le binaire doit être exécutable).
    extras : dict de fichiers à injecter dans le bundle interne."""
    n_entries = 0
    launcher_fixed = False
    bundle_patched = False
    with tarfile.open(input_path, "r:gz") as tin, \
         tarfile.open(output_path, "w:gz") as tout:
        for member in tin.getmembers():
            n_entries += 1
            if member.isfile():
                data = tin.extractfile(member).read()
                base = member.name.rsplit("/", 1)[-1]
                if base == "lidar2map_bundle.zip":
                    data = _patch_inner_bundle(data, new_script, extras=extras)
                    member.size = len(data)
                    bundle_patched = True
                if base == "lidar2map" and (member.mode & 0o111) == 0:
                    member.mode = 0o755
                    launcher_fixed = True
                tout.addfile(member, io.BytesIO(data))
            else:
                tout.addfile(member)
    if not bundle_patched:
        sys.exit(f"ERREUR : aucun lidar2map_bundle.zip trouvé dans {Path(input_path).name}.")
    return n_entries, launcher_fixed


# ── Mode archive macOS (refactorisé pour utiliser les helpers) ───────────────

def _update_macos_archive(outer_path, new_script_bytes):
    """Patch chirurgical d'un lidar2map-macos-*.zip — préserve les permissions
    Unix encodées par ditto (Contents/MacOS/lidar2map mode 0o755, symlinks
    PyQt6, etc.) car seules les bytes du bundle interne sont régénérées."""

    # 1. Extraire le bundle interne, le patcher
    with zipfile.ZipFile(outer_path, "r") as outer:
        inner_name = next(
            (n for n in outer.namelist()
             if n.endswith("/Contents/Resources/lidar2map_bundle.zip")),
            None)
        if inner_name is None:
            sys.exit(f"ERREUR : aucun Contents/Resources/lidar2map_bundle.zip "
                     f"dans {outer_path.name} — pas une archive .app valide.")
        inner_bytes = outer.read(inner_name)

    new_inner_bytes = _patch_inner_bundle(inner_bytes, new_script_bytes)

    # 2. Réécrire l'archive externe atomiquement
    tmp = outer_path.with_suffix(".zip.tmp")
    print(f"Mise à jour de {TARGET} dans {inner_name} de {outer_path.name}...")
    try:
        n_entries, _ = _patch_outer_zip(outer_path, "/Contents/Resources/lidar2map_bundle.zip",
                                        new_inner_bytes, tmp)
        os.replace(tmp, outer_path)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        sys.exit(f"ERREUR : {e}")

    print(f"  ✓ {TARGET} remplacé dans {inner_name}")
    print(f"  ✓ ZipInfo préservés sur les {n_entries} entrées")
    print(f"  SHA256 archive : {sha256(outer_path)[:16]}...")


# ── GitHub API ───────────────────────────────────────────────────────────────

def _get_github_token():
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=15,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line[len("password="):].strip()
    except Exception:
        pass
    return None


def _gh_api(method, url, token, *, json_body=None, binary=None, content_type=None):
    """Appel API GitHub. json_body : dict → JSON ; binary : bytes ou Path → upload binaire."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    elif binary is not None:
        if isinstance(binary, Path):
            data = binary.read_bytes()
        else:
            data = binary
        headers["Content-Type"] = content_type or "application/octet-stream"
        headers["Content-Length"] = str(len(data))
    else:
        data = None

    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = resp.read()
            return resp.getcode(), (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body.decode("utf-8", "replace")}


def _download_with_progress(url, dest):
    print(f"  ↓ {url}")
    def prog(n, bs, total):
        if total > 0:
            pct = min(n * bs * 100 // total, 100)
            print(f"  {pct:3d}%", end="\r", flush=True)
    urllib.request.urlretrieve(url, dest, reporthook=prog)
    print("  100%")


# ── Mode --release ───────────────────────────────────────────────────────────

# Spec des assets : (suffixe_attendu, type_archive, content_type)
_ASSET_SPECS = [
    ("windows-x86_64.zip",    "zip",   "application/zip"),
    ("linux-x86_64.tar.gz",   "targz", "application/gzip"),
    ("macos-arm64.zip",       "zip",   "application/zip"),
]


def _patch_asset(local_path, kind, new_script, extras=None):
    """Dispatch sur le bon patcher selon le type d'archive. Renvoie une str
    diagnostic pour log.
    extras : dict {path_in_bundle: bytes} de fichiers additionnels à injecter
             dans le bundle interne (ex: providers/*.py pour v1.2+)."""
    tmp = local_path.with_suffix(local_path.suffix + ".tmp")
    if kind == "targz":
        n, launcher_fixed = _patch_linux_targz(local_path, tmp, new_script, extras=extras)
        os.replace(tmp, local_path)
        msg = f"tar.gz {n} entries"
        if launcher_fixed:
            msg += " + launcher mode 0o755 (fix)"
        if extras:
            msg += f" + {len(extras)} extras"
        return msg

    # zip : peut être un outer mac (avec .app/Contents/Resources/...) ou
    # un outer Win (avec dossier/lidar2map_bundle.zip). On détecte au vol.
    with zipfile.ZipFile(local_path, "r") as z:
        mac_inner = next(
            (n for n in z.namelist()
             if n.endswith("/Contents/Resources/lidar2map_bundle.zip")),
            None)
        win_inner = next(
            (n for n in z.namelist()
             if n.endswith("/lidar2map_bundle.zip") and "/Contents/" not in n),
            None)

    if mac_inner:
        suffix = "/Contents/Resources/lidar2map_bundle.zip"
    elif win_inner:
        suffix = "/lidar2map_bundle.zip"
    else:
        sys.exit(f"ERREUR : structure inconnue dans {local_path.name}.")

    with zipfile.ZipFile(local_path, "r") as z:
        inner_name = next(n for n in z.namelist() if n.endswith(suffix))
        inner_bytes = z.read(inner_name)
    new_inner = _patch_inner_bundle(inner_bytes, new_script, extras=extras)

    n_entries, _ = _patch_outer_zip(local_path, suffix, new_inner, tmp)
    os.replace(tmp, local_path)
    return f"zip {n_entries} entries (inner: {inner_name})"


def _patch_release_body(body, sha_by_filename):
    """Remplace les SHA256 dans le body markdown. Le format attendu est
    une ligne contenant `<filename>` puis `<old_sha>` (table markdown
    ou bloc `attendu : ...`). On remplace n'importe quelle string de
    64 hex chars qui suit la mention du filename à <=200 chars de distance."""
    for fname, new_sha in sha_by_filename.items():
        # Pattern : <filename>...{64 hex chars}
        # Limité à 300 chars de fenêtre pour éviter de matcher la mauvaise
        # ligne quand plusieurs filenames sont listés à la suite.
        pat = re.compile(
            re.escape(fname) + r"(.{0,300}?)([0-9a-f]{64})",
            flags=re.DOTALL,
        )
        new_body, n_sub = pat.subn(
            lambda m, s=new_sha: m.group(0)[: -64] + s,
            body,
        )
        if n_sub == 0:
            print(f"  ⚠ {fname} : aucun SHA256 à remplacer dans le body")
        else:
            print(f"  ✓ {fname} : {n_sub} occurrence(s) de SHA256 mises à jour")
        body = new_body
    return body


def _do_release(tag, new_script, dry_run=False):
    print(f"\n── Release {tag} (download/patch/upload{' DRY-RUN' if dry_run else ''}) ─\n")

    token = _get_github_token()
    if not token:
        sys.exit("ERREUR : token GitHub introuvable. Définir GH_TOKEN, "
                 "GITHUB_TOKEN ou configurer git credential helper.")

    # 1. Récupérer les infos de release
    print(f"[1/5] Lecture de la release {tag}...")
    code, rel = _gh_api(
        "GET",
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{tag}",
        token)
    if code != 200:
        sys.exit(f"ERREUR : release {tag} introuvable ({code} : {rel}).")
    release_id = rel["id"]
    print(f"  release id = {release_id}, {len(rel['assets'])} assets")

    # 2. Pour chaque spec, retrouver l'asset correspondant
    targets = []
    for suffix, kind, ctype in _ASSET_SPECS:
        match = next((a for a in rel["assets"] if a["name"].endswith(suffix)), None)
        if not match:
            print(f"  ⚠ aucun asset pour suffix '{suffix}', skip.")
            continue
        targets.append({
            "name": match["name"], "asset_id": match["id"],
            "url": match["browser_download_url"],
            "kind": kind, "ctype": ctype, "remote_size": match["size"],
        })

    if not targets:
        sys.exit("ERREUR : aucun asset à mettre à jour.")

    # 3. Télécharger (cache local dans dist/release/, skip si taille match)
    cache_dir = HERE / "dist" / "release"
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[2/5] Téléchargement (cache : {cache_dir})...")
    for t in targets:
        dest = cache_dir / t["name"]
        if dest.exists() and dest.stat().st_size == t["remote_size"]:
            print(f"  ✓ {t['name']} déjà en cache ({t['remote_size']:,} bytes)")
        else:
            _download_with_progress(t["url"], dest)
        t["local"] = dest

    # 3b. Collecter les fichiers additionnels à injecter (providers/*.py v1.2+).
    # Les bundles v1.1 n'ont pas de providers/ — on l'ajoute via extras.
    extras = {}
    _providers_dir = HERE / "providers"
    if _providers_dir.exists():
        for _f in sorted(_providers_dir.glob("*.py")):
            extras[f"_internal/providers/{_f.name}"] = _f.read_bytes()
        if extras:
            print(f"\n  Extras à injecter (providers/) : {len(extras)} fichiers")
            for path in extras:
                print(f"    + {path}")

    # 4. Patcher chaque archive
    print(f"\n[3/5] Patch des bundles internes...")
    for t in targets:
        print(f"  • {t['name']} :")
        msg = _patch_asset(t["local"], t["kind"], new_script, extras=extras)
        new_sha = sha256(t["local"])
        t["new_sha"] = new_sha
        t["new_size"] = t["local"].stat().st_size
        print(f"      {msg}")
        print(f"      SHA256 = {new_sha}")
        print(f"      taille = {t['new_size']:,} bytes")

    if dry_run:
        print(f"\n[4/5] Upload — DRY-RUN, skip.")
        print(f"\n[5/5] Patch body — DRY-RUN, simulation :")
        sha_by_name = {t["name"]: t["new_sha"] for t in targets}
        _patch_release_body(rel["body"] or "", sha_by_name)  # affiche les remplacements
        print(f"\nDRY-RUN terminé. Archives patchées en cache : {cache_dir}")
        print(f"  Pour pousser : python update_app.py --release  (sans --dry-run)\n")
        return

    # 5. Replace assets : DELETE puis UPLOAD (GitHub n'accepte pas de PATCH
    #    sur le binaire d'un asset existant — il faut delete+upload).
    print(f"\n[4/5] Upload des assets patchés...")
    for t in targets:
        print(f"  • {t['name']} :")
        code, _ = _gh_api(
            "DELETE",
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/assets/{t['asset_id']}",
            token)
        if code != 204:
            sys.exit(f"ERREUR DELETE asset {t['name']} : HTTP {code}")
        print(f"      DELETE old asset (id {t['asset_id']})")

        upload_url = (f"https://uploads.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
                      f"/releases/{release_id}/assets?name={t['name']}")
        code, body = _gh_api("POST", upload_url, token,
                             binary=t["local"], content_type=t["ctype"])
        if code not in (200, 201):
            sys.exit(f"ERREUR UPLOAD asset {t['name']} : HTTP {code} : {body}")
        print(f"      UPLOAD {t['new_size'] / 1e6:.0f} Mo OK")

    # 6. Patcher le body de la release avec les nouveaux SHA256
    print(f"\n[5/5] Mise à jour du body de la release...")
    sha_by_name = {t["name"]: t["new_sha"] for t in targets}
    new_body = _patch_release_body(rel["body"] or "", sha_by_name)
    code, _ = _gh_api(
        "PATCH",
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/{release_id}",
        token, json_body={"body": new_body})
    if code != 200:
        sys.exit(f"ERREUR PATCH body : HTTP {code}")
    print(f"  ✓ body patché ({len(new_body)} chars)")

    print(f"\nTerminé. Release {tag} mise à jour :")
    print(f"  https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/tag/{tag}\n")


# ── Détection mode ──────────────────────────────────────────────────────────

def _find_macos_archive():
    """Auto-discover lidar2map-macos-*.zip à côté du script ou dans dist/."""
    for _a in sys.argv[1:]:
        if _a.startswith("--"):
            continue
        _p = Path(_a)
        if _p.exists() and _p.suffix == ".zip" and "macos" in _p.name.lower():
            return _p.resolve()
    for _c in (HERE / "lidar2map-macos-arm64.zip",
               HERE / "dist" / "lidar2map-macos-arm64.zip"):
        if _c.exists():
            return _c
    return None


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


# ── Vérifications source + dispatch ─────────────────────────────────────────

if not SCRIPT.exists(): sys.exit(f"ERREUR : {SCRIPT} introuvable")
new_content = SCRIPT.read_bytes()

# Validation syntaxique : un .py cassé injecté dans le zip rendrait l'app
# non lançable sans rebuild. compile() lève SyntaxError si invalide.
try:
    compile(new_content, str(SCRIPT), "exec")
except SyntaxError as e:
    sys.exit(f"ERREUR : {SCRIPT.name} contient une SyntaxError ({e}) — abandon")

# Mode --release : download/patch/upload sur les 3 OS
if "--release" in sys.argv:
    _tag = "v1.1.0"
    if "--tag" in sys.argv:
        _i = sys.argv.index("--tag")
        if _i + 1 < len(sys.argv):
            _tag = sys.argv[_i + 1]
    _do_release(_tag, new_content, dry_run="--dry-run" in sys.argv)
    sys.exit(0)

# Mode archive macOS : argument .zip macOS OU lidar2map-macos-arm64.zip auto-détecté
_archive = _find_macos_archive()
if _archive:
    _update_macos_archive(_archive, new_content)
    print("Terminé. Re-uploader l'archive sur la release (ou utiliser --release).")
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

# Réécrire le zip avec le nouveau lidar2map.py — opération atomique
BUNDLE_TMP = BUNDLE.with_suffix(".zip.tmp")
print(f"Mise à jour de {TARGET} dans {BUNDLE.name}...")
try:
    new_inner_bytes = _patch_inner_bundle(BUNDLE.read_bytes(), new_content)
    BUNDLE_TMP.write_bytes(new_inner_bytes)
    os.replace(BUNDLE_TMP, BUNDLE)
except Exception as e:
    BUNDLE_TMP.unlink(missing_ok=True)
    sys.exit(f"ERREUR : {e}")

print(f"  ✓ {TARGET} remplacé")
print(f"  SHA256 bundle : {sha256(BUNDLE)[:16]}...")
print("Terminé. La nouvelle version sera active au prochain lancement.")
