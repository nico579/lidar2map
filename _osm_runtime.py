"""Runtime local et exécution d'Osmosis.

Ce module ne télécharge ni Java ni Osmosis. Il orchestre les outils découverts
par la façade, construit les options JVM du bundle, diffuse les diagnostics
utiles d'un processus Osmosis et nettoie ses index temporaires orphelins.
"""

from collections import deque
from pathlib import Path
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile


OSMOSIS_INTERESSANT = (
    "ERROR", "SEVERE", "FATAL", "Exception", "Caused by",
    "WARNING", "AVERTISSEMENT", "WARN ",
)
MAPWRITER_VERSION = "0.25.0"
MAPWRITER_JAR = (
    f"mapsforge-map-writer-{MAPWRITER_VERSION}-jar-with-dependencies.jar"
)
MAPWRITER_URL = (
    "https://repo1.maven.org/maven2/org/mapsforge/mapsforge-map-writer/"
    f"{MAPWRITER_VERSION}/{MAPWRITER_JAR}"
)


def bin_outil(racine, pattern):
    """Retourne le premier binaire trié situé sous un dossier ``bin``."""
    for candidate in sorted(Path(racine).rglob(pattern)):
        if candidate.is_file() and "bin" in candidate.parts:
            return candidate
    return None


def trouver_java(
    *,
    frozen,
    bundle_dir,
    lidar2map_home,
    windows,
    telecharger_jre_local,
):
    """Trouve Java dans le bundle puis le cache, sinon le télécharge."""
    java_bin = "java.exe" if windows else "java"
    if frozen:
        for candidate in sorted((Path(bundle_dir) / "jre").rglob(java_bin)):
            if candidate.exists():
                return str(candidate)

    for candidate in sorted((Path(lidar2map_home) / "jre").rglob(java_bin)):
        if candidate.exists():
            return str(candidate)

    java = telecharger_jre_local()
    if not java:
        print("  ERROR: cannot obtain a JRE.")
        print("  Installez Java manuellement : https://adoptium.net/")
    return java


def trouver_osmosis(
    *,
    frozen,
    bundle_dir,
    lidar2map_home,
    windows,
    telecharger_osmosis_local,
):
    """Trouve Osmosis dans le bundle puis le cache, sinon le télécharge."""
    pattern = "osmosis.bat" if windows else "osmosis"
    if frozen:
        candidate = bin_outil(Path(bundle_dir) / "osmosis", pattern)
        if candidate is not None:
            return str(candidate)

    local_name = "osmosis.bat" if windows else "osmosis"
    local = Path(lidar2map_home) / "osmosis" / "bin" / local_name
    if local.exists():
        return str(local)
    return telecharger_osmosis_local()


def promouvoir_dossier(
    tmp_dir,
    dest_dir,
    *,
    getpid=os.getpid,
    uuid4=uuid.uuid4,
    rmtree=shutil.rmtree,
):
    """Promeut un dossier validé et restaure l'ancien sur toute exception."""
    dest_dir = Path(dest_dir)
    tmp_dir = Path(tmp_dir)
    ancien_part = None
    if dest_dir.exists():
        ancien_part = dest_dir.parent / (
            f"{dest_dir.name}.previous.{getpid()}.{uuid4().hex[:12]}.part"
        )
        dest_dir.replace(ancien_part)
    try:
        tmp_dir.replace(dest_dir)
    except BaseException:
        if (
            ancien_part is not None
            and ancien_part.exists()
            and not dest_dir.exists()
        ):
            ancien_part.replace(dest_dir)
        raise
    if ancien_part is not None:
        rmtree(ancien_part, ignore_errors=True)


def telecharger_osmosis_local(
    *,
    lidar2map_home,
    windows,
    chemin_part,
    safe_zip_extractall,
    promouvoir,
    trouver_binaire,
    urlretrieve=urllib.request.urlretrieve,
    remplacer=os.replace,
    rmtree=shutil.rmtree,
    getpid=os.getpid,
    uuid4=uuid.uuid4,
):
    """Installe Osmosis 0.49.2 dans un staging validé puis promu."""
    osmosis_dir = Path(lidar2map_home) / "osmosis"
    pattern = "osmosis.bat" if windows else "osmosis"
    deja = trouver_binaire(osmosis_dir, pattern) if osmosis_dir.exists() else None
    if deja is not None:
        return str(deja)

    url = (
        "https://github.com/openstreetmap/osmosis/releases/download/0.49.2/"
        "osmosis-0.49.2.zip"
    )
    tmp_dir = Path(lidar2map_home) / (
        f"osmosis.{getpid()}.{uuid4().hex[:12]}.part"
    )
    if tmp_dir.exists():
        rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / "osmosis.zip"
    zip_part = chemin_part(zip_path)

    print(f"  URL  : {url}")
    print("  Downloading osmosis (~35 MB)...", flush=True)
    try:
        def _prog(n, bs, total):
            if total > 0:
                print(
                    "  " + str(min(n * bs * 100 // total, 100)).rjust(3) + "%",
                    end="\r",
                    flush=True,
                )

        urlretrieve(url, zip_part, reporthook=_prog)
        remplacer(zip_part, zip_path)
        print("  100%")
        print("  Extraction osmosis...", flush=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            safe_zip_extractall(archive, tmp_dir)
        zip_path.unlink(missing_ok=True)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        zipfile.BadZipFile,
        ValueError,
    ) as exc:
        print(f"  ERROR downloading osmosis: {type(exc).__name__}: {exc}")
        rmtree(tmp_dir, ignore_errors=True)
        return None
    except BaseException:
        rmtree(tmp_dir, ignore_errors=True)
        raise

    candidate_tmp = trouver_binaire(tmp_dir, pattern)
    if candidate_tmp is None:
        print("  ERROR: osmosis not found after extraction.")
        rmtree(tmp_dir, ignore_errors=True)
        return None
    try:
        if not windows:
            candidate_tmp.chmod(candidate_tmp.stat().st_mode | stat.S_IEXEC)
        promouvoir(tmp_dir, osmosis_dir)
    except BaseException:
        rmtree(tmp_dir, ignore_errors=True)
        raise

    candidate = trouver_binaire(osmosis_dir, pattern)
    if candidate is not None:
        print(f"  osmosis installed: {candidate}")
        return str(candidate)
    print("  ERROR: osmosis not found after extraction.")
    return None


def telecharger_jre_local(
    *,
    lidar2map_home,
    windows,
    platform_system,
    platform_machine,
    chemin_part,
    safe_zip_extractall,
    promouvoir,
    request=urllib.request.Request,
    urlopen=urllib.request.urlopen,
    remplacer=os.replace,
    rmtree=shutil.rmtree,
    getpid=os.getpid,
    uuid4=uuid.uuid4,
):
    """Installe un JRE Temurin 21 dans un staging validé puis promu."""
    jre_dir = Path(lidar2map_home) / "jre"
    tmp_dir = Path(lidar2map_home) / f"jre.{getpid()}.{uuid4().hex[:12]}.part"
    if tmp_dir.exists():
        rmtree(tmp_dir, ignore_errors=True)

    systeme = platform_system().lower()
    if systeme == "windows":
        os_str, ext, java_bin = "windows", "zip", "bin/java.exe"
    elif systeme == "darwin":
        os_str, ext, java_bin = "mac", "tar.gz", "bin/java"
    else:
        os_str, ext, java_bin = "linux", "tar.gz", "bin/java"
    machine = platform_machine().lower()
    arch_str = "aarch64" if machine in ("arm64", "aarch64") else "x64"
    url = (
        "https://api.adoptium.net/v3/binary/latest/21/ga/"
        f"{os_str}/{arch_str}/jre/hotspot/normal/eclipse"
    )

    archive = tmp_dir / f"jre.{ext}"
    archive_part = chemin_part(archive)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    print(f"  URL  : {url}")
    print(
        f"  Downloading JRE Temurin 21 ({os_str}/{arch_str}, ~50 MB)...",
        flush=True,
    )
    try:
        headers = {
            "User-Agent": "lidar2map/1.0 (JRE bootstrap)",
            "Accept": "application/octet-stream",
        }
        req = request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            final_url = response.url
        req2 = request(final_url, headers=headers)
        with urlopen(req2, timeout=120) as response2:
            total = int(response2.headers.get("Content-Length", 0))
            downloaded = 0
            with open(archive_part, "wb") as output:
                while True:
                    buf = response2.read(65536)
                    if not buf:
                        break
                    output.write(buf)
                    downloaded += len(buf)
                    if total > 0:
                        pct = min(downloaded * 100 // total, 100)
                        print(f"  {pct:3d}%", end="\r", flush=True)
        remplacer(archive_part, archive)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"  ERROR downloading JRE: {type(exc).__name__}: {exc}")
        rmtree(tmp_dir, ignore_errors=True)
        return None
    except BaseException:
        rmtree(tmp_dir, ignore_errors=True)
        raise

    print("  Extraction JRE...", flush=True)
    try:
        if ext == "zip":
            with zipfile.ZipFile(archive, "r") as zip_archive:
                safe_zip_extractall(zip_archive, tmp_dir)
        else:
            with tarfile.open(archive, "r:gz") as tar_archive:
                try:
                    tar_archive.extractall(tmp_dir, filter="data")
                except TypeError:
                    dest = Path(tmp_dir).resolve()
                    for member in tar_archive.getmembers():
                        name = member.name
                        if (
                            name.startswith(("/", "\\"))
                            or ".." in Path(name).parts
                            or (len(name) > 1 and name[1] == ":")
                        ):
                            raise ValueError(f"Archive JRE suspecte : {name!r}")
                        if member.isdev():
                            raise ValueError(
                                f"Fichier spécial dans le JRE : {name!r}"
                            )
                        if member.issym() or member.islnk():
                            link = member.linkname
                            if link.startswith(("/", "\\")) or (
                                len(link) > 1 and link[1] == ":"
                            ):
                                raise ValueError(
                                    f"Lien absolu dans le JRE : {name!r}"
                                )
                            base = (
                                dest / Path(name).parent
                                if member.issym()
                                else dest
                            )
                            target = (base / link).resolve()
                            if target != dest and dest not in target.parents:
                                raise ValueError(
                                    f"Lien sortant dans le JRE : {name!r}"
                                )
                    tar_archive.extractall(tmp_dir)
        archive.unlink(missing_ok=True)
    except (
        zipfile.BadZipFile,
        tarfile.TarError,
        ValueError,
        OSError,
    ) as exc:
        print(f"  ERROR extracting JRE: {type(exc).__name__}: {exc}")
        rmtree(tmp_dir, ignore_errors=True)
        return None
    except BaseException:
        rmtree(tmp_dir, ignore_errors=True)
        raise

    candidate = next(
        (path for path in sorted(tmp_dir.rglob(java_bin)) if path.exists()),
        None,
    )
    if candidate is None:
        print("  ERROR: java binary not found after extraction.")
        rmtree(tmp_dir, ignore_errors=True)
        return None
    try:
        if not windows:
            candidate.chmod(candidate.stat().st_mode | stat.S_IEXEC)
        promouvoir(tmp_dir, jre_dir)
    except BaseException:
        rmtree(tmp_dir, ignore_errors=True)
        raise

    for candidate in sorted(jre_dir.rglob(java_bin)):
        if candidate.exists():
            print(f"  JRE installed: {candidate}")
            return str(candidate)
    print("  ERROR: java binary not found after extraction.")
    return None


def verifier_mapwriter(
    *,
    frozen,
    home_dir,
    chemin_part,
    jar_name=MAPWRITER_JAR,
    url=MAPWRITER_URL,
    urlretrieve=urllib.request.urlretrieve,
    remplacer=os.replace,
):
    """Vérifie ou télécharge atomiquement le plugin mapwriter."""
    if frozen:
        return True

    plugins_dir = Path(home_dir) / ".openstreetmap" / "osmosis" / "plugins"
    jar_path = plugins_dir / jar_name
    if jar_path.exists():
        return True

    print(f"  URL  : {url}")
    print(
        f"  mapwriter plugin missing - downloading ({jar_name})...",
        flush=True,
    )
    tmp_jar = chemin_part(jar_path)
    try:
        plugins_dir.mkdir(parents=True, exist_ok=True)

        def _prog(n, bs, total):
            if total > 0:
                print(
                    "  " + str(min(n * bs * 100 // total, 100)).rjust(3) + "%",
                    end="\r",
                    flush=True,
                )

        urlretrieve(url, tmp_jar, reporthook=_prog)
        print("  100%")
        remplacer(tmp_jar, jar_path)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"  ERROR downloading mapwriter: {type(exc).__name__}: {exc}")
        print(f"  Download manually:\n    {url}")
        print(f"  and copy it into:\n    {plugins_dir}")
        try:
            tmp_jar.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    except BaseException:
        try:
            tmp_jar.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    print(f"  Plugin installed: {jar_path}")
    return True


def telecharger_outils(
    *,
    trouver_java,
    trouver_osmosis,
    verifier_mapwriter,
    jar_name=MAPWRITER_JAR,
):
    """Télécharge/vérifie les trois outils et affiche leur statut final."""
    print()
    print("  ── Downloading tools (osmosis + JRE + mapwriter) ──────")
    print()
    java = trouver_java()
    if java:
        print(f"  ✓ JRE already present: {java}")
    else:
        print("  ⚠ JRE: download failed")
    osmosis = trouver_osmosis()
    if osmosis:
        print(f"  ✓ osmosis already present: {osmosis}")
    else:
        print("  ⚠ osmosis: download failed")
    if verifier_mapwriter():
        print(
            "  ✓ mapwriter present: "
            f"~/.openstreetmap/osmosis/plugins/{jar_name}"
        )
    else:
        print("  ⚠ mapwriter: download failed - .map generation will fail")
    print()


def java_opts_extra(*, frozen, bundle_dir):
    """Retourne les options JVM qui isolent les plugins du bundle frozen."""
    if not frozen:
        return ""
    fake_home = str(bundle_dir).replace("\\", "/")
    return f' "-Duser.home={fake_home}"'


def preparer_osmosis(
    dossier_hint=None,
    *,
    verifier_mapwriter,
    trouver_java,
    trouver_osmosis,
):
    """Valide mapwriter et retourne ``(osmosis_exe, java_home)``.

    ``dossier_hint`` reste accepté pour préserver le contrat historique ; la
    sélection du tagmapping appartient au pipeline appelant.
    """
    del dossier_hint
    if not verifier_mapwriter():
        print("  ERROR: mapwriter plugin missing - .map map impossible.")
        return None, None
    java_exe = trouver_java()
    if not java_exe:
        return None, None
    osmosis_exe = trouver_osmosis()
    if not osmosis_exe:
        print("  ERROR: osmosis not found")
        return None, None
    java_home = str(Path(java_exe).parent.parent)
    return osmosis_exe, java_home


def run_osmosis_streaming(
    cmd_or_str,
    shell,
    env,
    *,
    subprocess_module=subprocess,
    marqueurs=OSMOSIS_INTERESSANT,
):
    """Lance Osmosis en direct et conserve les 500 dernières lignes stderr."""
    proc = subprocess_module.Popen(
        cmd_or_str,
        stdout=subprocess_module.PIPE,
        stderr=subprocess_module.PIPE,
        shell=shell,
        env=env,
    )

    stderr_tail = deque(maxlen=500)
    affichees = [0]
    lock = threading.Lock()

    def _reader(stream, is_stderr):
        try:
            for raw in iter(stream.readline, b""):
                try:
                    line = raw.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    continue
                if not line:
                    continue
                if is_stderr:
                    stderr_tail.append(line)
                if not any(tok in line for tok in marqueurs):
                    continue
                with lock:
                    if affichees[0] == 0:
                        print()
                    affichees[0] += 1
                    print(f"  {line}", flush=True)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    th_out = threading.Thread(
        target=_reader, args=(proc.stdout, False), daemon=True
    )
    th_err = threading.Thread(
        target=_reader, args=(proc.stderr, True), daemon=True
    )
    th_out.start()
    th_err.start()

    proc.wait()
    th_out.join(timeout=5)
    th_err.join(timeout=5)
    return proc.returncode, "\n".join(stderr_tail)


def nettoyer_osmosis_temp_orphelins(
    verbose=False,
    min_age_s=300,
    *,
    temp_dir=None,
    maintenant=None,
):
    """Supprime les vieux index ``idxNodes``/``idxWays`` laissés par Osmosis."""
    tmp = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())
    if not tmp.exists():
        return 0, 0

    instant = time.time() if maintenant is None else maintenant
    cutoff = instant - min_age_s
    nb, bytes_freed = 0, 0
    for pattern in ("idxNodes*.tmp", "idxWays*.tmp"):
        for fichier in tmp.glob(pattern):
            try:
                stat = fichier.stat()
                if stat.st_mtime > cutoff:
                    continue
                size = stat.st_size
                fichier.unlink()
                nb += 1
                bytes_freed += size
            except OSError:
                pass
    if nb and verbose:
        print(
            f"  ✓ Cleaned {nb} orphan osmosis temp file(s) "
            f"({bytes_freed / 1e6:.0f} MB)"
        )
    return nb, bytes_freed
