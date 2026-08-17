"""Runtime effectif du bootstrap precoce de lidar2map.

Le module ne produit aucun effet lors de son import. Les operations de processus,
venv et pip ne sont executees que par les facades historiques de lidar2map.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# Catalogue unique : les noms de paquets pip ne sont pas systématiquement les
# noms importables. Il est partagé par le bootstrap normal et l'installation
# explicite ``--installer-deps`` de la façade.
MODULE_PAR_PAQUET = {
    "Pillow": "PIL",
    "pyproj": "pyproj",
    "numpy": "numpy",
    "scipy": "scipy",
    "ijson": "ijson",
    "rasterio": "rasterio",
    "fiona": "fiona",
    "certifi": "certifi",
    "pywebview": "webview",
    "osmium": "osmium",
    "numba": "numba",
    "laspy": "laspy",
    "lazrs": "lazrs",
    "py7zr": "py7zr",
    "mapbox-vector-tile": "mapbox_vector_tile",
    "cloth-simulation-filter": "CSF",
    "PyQt6": "PyQt6",
    "PyQt6-WebEngine": "PyQt6.QtWebEngineWidgets",
    "qtpy": "qtpy",
    "pyobjc-framework-WebKit": "WebKit",
    "pyobjc-framework-Cocoa": "Cocoa",
}


def chemins_desinstallation(*, systeme, home, localappdata=None):
    """Retourne les cibles de désinstallation sans accéder au disque."""
    home = Path(home)
    lidar2map_home = home / ".lidar2map"
    if systeme == "Windows":
        base = Path(localappdata) if localappdata else home / "AppData" / "Local"
        app_data = base / "lidar2map"
    elif systeme == "Darwin":
        app_data = home / "Library" / "Application Support" / "lidar2map"
    else:
        app_data = home / ".local" / "share" / "lidar2map"
    return (
        (app_data, "dossier d'extraction du bundle"),
        (lidar2map_home / "venv", "venv Python"),
        (lidar2map_home / "osmosis", "osmosis"),
        (lidar2map_home / "jre", "JRE Java"),
    )


def _taille_arbre_sans_suivre_liens(chemin):
    """Mesure un arbre sans parcourir les liens vers des données externes."""
    total = 0
    for racine, dossiers, fichiers in os.walk(chemin, followlinks=False):
        racine = Path(racine)
        for nom in dossiers:
            entree = racine / nom
            if not entree.is_symlink():
                continue
            try:
                total += entree.lstat().st_size
            except OSError:
                pass
        for nom in fichiers:
            try:
                total += (racine / nom).lstat().st_size
            except OSError:
                pass
    return total


def desinstaller_lidar2map(
    *,
    systeme,
    home,
    localappdata=None,
    supprimer_arbre=shutil.rmtree,
    ecrire=print,
):
    """Supprime les seules cibles planifiées et retourne ``True`` si complet."""
    cibles = chemins_desinstallation(
        systeme=systeme,
        home=home,
        localappdata=localappdata,
    )
    total = 0
    complet = True
    ecrire("")
    ecrire("  ── lidar2map uninstall ──────────────────────────────────")
    ecrire("")
    for chemin, label in cibles:
        if not chemin.exists() and not chemin.is_symlink():
            ecrire(f"  {label} : absent ({chemin})")
            continue
        taille = (
            chemin.lstat().st_size
            if chemin.is_symlink()
            else _taille_arbre_sans_suivre_liens(chemin)
        )
        total += taille
        ecrire(f"  Removing {label} ({taille / 1e6:.0f} MB)")
        ecrire(f"    {chemin}")
        try:
            if chemin.is_symlink():
                chemin.unlink()
            else:
                supprimer_arbre(chemin)
        except OSError as exc:
            complet = False
            ecrire(f"    ⚠ partial ({exc})")
            continue
        if chemin.exists() or chemin.is_symlink():
            complet = False
            ecrire("    ⚠ partial")
        else:
            ecrire("    ✓ removed")
    ecrire("")
    ecrire(f"  {total / 1e6:.0f} MB freed.")
    ecrire("")
    ecrire("  Note: lidar2map.py, the .app/.exe and the zip are not removed.")
    ecrire("  Remove them manually if needed.")
    ecrire("")
    return complet


def verifier_venv_linux():
    """Sur Linux/Ubuntu, vérifie que le module venv est disponible.

    Sur Debian/Ubuntu, python3-venv est un paquet système SÉPARÉ de python3
    (décision de packaging Debian). Il est donc absent sur un Python nu, ce
    qui fait planter la création de venv sans message clair.

    Cette fonction est appelée AVANT toute tentative de création de venv.
    Elle détecte l'absence du module et imprime les instructions apt.
    """
    if platform.system() != "Linux":
        return
    try:
        import venv as _venv_test  # noqa: F401
        return  # module présent, tout va bien
    except ImportError:
        pass
    # Détecter aussi via subprocess pour couvrir les cas où le module
    # est présent mais pas importable depuis le Python courant.
    r = subprocess.run(
        [sys.executable, "-m", "venv", "--help"],
        capture_output=True)
    if r.returncode == 0:
        return  # disponible
    # Module absent : message clair et arrêt propre
    _py = f"python{sys.version_info.major}.{sys.version_info.minor}"
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ERROR: module Python 'venv' absent                        ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()
    print("  On Ubuntu/Debian, this module is in a separate package.")
    print("  Install it with (once):")
    print()
    print("    sudo apt install python3-venv")
    print(f"    # or, if you use Python {sys.version_info.major}.{sys.version_info.minor} explicitly:")
    print(f"    sudo apt install {_py}-venv")
    print()
    print("  Then relaunch the script.")
    sys.exit(1)


def bootstrap_venv_si_besoin(
    *,
    resoudre_mode,
    gui_deps_plateforme,
    verifier_venv_linux,
    relancer_dans_venv,
):
    """Bootstrap automatique d'un environnement Python isolé.

    Comportement par défaut : crée un venv dans ``~/.lidar2map/`` (Mac/Linux)
    ou ``%USERPROFILE%\\.lidar2map\\`` (Windows) au 1er lancement, y installe
    les dépendances, et y relance le script. Comportement uniforme sur les 3 OS.

    Avantages du venv par défaut sur toutes plateformes :
      - Isolation : zéro pollution du Python système
      - Désinstallation propre : suppression d'un dossier suffit
      - Cohérent avec la bonne pratique Python (un venv par projet)
      - Évite les conflits de versions de modules avec d'autres outils
      - Contourne PEP 668 sur Mac/Linux récents nativement

    Flags utilisateur (lus directement depuis sys.argv pour bypasser argparse
    qui n'est pas encore initialisé à ce stade du démarrage) :

      --bootstrap=auto    : venv automatique (défaut, recommandé). Si un env
                            isolé est déjà actif (conda / venv), s'arrête et
                            oriente vers --bootstrap=pip|none au lieu de créer
                            un venv parallèle.
      --bootstrap=pip     : install directe dans l'env Python courant
                            (utilise --break-system-packages si PEP 668)
      --bootstrap=none    : pas d'install — vérifie les imports et plante
                            avec un message clair si manquants. Utile pour
                            ceux qui gèrent leur propre env (conda, venv
                            manuel, install système contrôlée).
      --help-bootstrap    : affiche cette aide et quitte

    Variables d'environnement équivalentes :
      LIDAR2MAP_BOOTSTRAP=auto|pip|none

    Suppression du venv à tout moment :
      rm -rf ~/.lidar2map                       (Mac/Linux)
      rmdir /s /q %USERPROFILE%\\.lidar2map     (Windows)
    Le script en recréera un au prochain lancement si besoin.
    """
    mode = resoudre_mode()

    # Deps réellement critiques pour le pipeline LiDAR principal.
    # numba et osmium sont optionnelles (numba accélère SVF, osmium pour
    # OSM→GeoJSON) — leur absence ne doit pas planter le bootstrap.
    deps_critiques = ["PIL", "pyproj", "numpy", "scipy", "ijson",
                      "rasterio", "fiona", "certifi"]

    # ── Mode "none" : juste vérifier les imports, planter clairement si KO ─
    if mode == "none":
        manquantes = []
        for mod in deps_critiques:
            try:
                __import__(mod)
            except ImportError:
                manquantes.append(mod)
        if manquantes:
            pkg_map = {"PIL": "Pillow", "pyproj": "pyproj", "numpy": "numpy",
                       "scipy": "scipy", "ijson": "ijson",
                       "rasterio": "rasterio", "fiona": "fiona",
                       "numba":    "numba",     "certifi": "certifi"}
            pkgs_pip = [pkg_map.get(m, m) for m in deps_critiques]
            print()
            print("  ╔══════════════════════════════════════════════════════════════╗")
            print("  ║  Mode --bootstrap=none: auto-install disabled              ║")
            print("  ╚══════════════════════════════════════════════════════════════╝")
            print(f"  Missing Python modules: {', '.join(manquantes)}")
            print()
            print("  Install them yourself with your preferred method:")
            print(f"    pip install {' '.join(pkgs_pip)} pywebview")
            print(f"    # ou : conda install -c conda-forge {' '.join(pkgs_pip)} pywebview")
            print()
            sys.exit(1)
        return

    # ── Mode "pip" : install dans l'env Python courant ───────────────────
    # Délégué à _installer_deps() plus bas (avec stratégie 3 niveaux :
    # standard → --break-system-packages → --user)
    if mode == "pip":
        return  # rien à faire ici, _installer_deps() prend le relais

    # ── Mode "auto" : créer/utiliser un venv ─────────────────────────────
    # Tout le runtime lidar2map (venv Python, JRE Java, osmosis, etc.) est
    # centralisé dans ~/.lidar2map/ — un seul dossier à supprimer pour
    # un nettoyage complet, et partagé entre tous les dossiers de travail.
    is_windows  = platform.system() == "Windows"
    lidar_home  = Path.home() / ".lidar2map"
    venv_path   = lidar_home / "venv"

    # Détecter si on est déjà dans le bon venv (ré-entrance après os.execv)
    try:
        if Path(sys.prefix).resolve() == venv_path.resolve():
            return
    except Exception:
        pass

    # ── Garde : environnement Python actif (conda / venv) ────────────────
    # Si l'utilisateur a déjà un env isolé actif, créer en silence un venv
    # parallèle dans ~/.lidar2map/ le surprend (cas signalé par un
    # utilisateur conda). On s'arrête et on l'oriente vers les modes adaptés
    # plutôt que de piétiner son env. Détection par variables d'env standard
    # (déterministe — contrairement à un scan des deps dans sys.path, cf.
    # NB ci-dessous). Non atteint en ré-entrance : le check venv ci-dessus a
    # déjà return quand sys.prefix == ~/.lidar2map/venv.
    _env_actif = os.environ.get("CONDA_PREFIX") or os.environ.get("VIRTUAL_ENV")
    if _env_actif:
        print()
        print("  ╔" + "═" * 62 + "╗")
        print("  ║ " + "Active Python environment detected (conda / venv)".ljust(60) + " ║")
        print("  ╚" + "═" * 62 + "╝")
        print(f"  Env actif : {_env_actif}")
        print()
        print("  To avoid creating a parallel venv in ~/.lidar2map/:")
        print("    python lidar2map.py --bootstrap=pip    # install the deps in this env")
        print("    python lidar2map.py --bootstrap=none   # if the deps are already there")
        print()
        print("  (or deactivate the active env to use the isolated venv by default)")
        print()
        sys.exit(1)

    # NB : on ne shortcut PAS sur "deps importables dans le Python courant".
    # Avant ce refactor, la présence des deps quelque part dans le sys.path
    # courant (système, conda, autre venv) faisait que ~/.lidar2map/venv
    # n'était jamais créé → comportement non-déterministe selon l'historique
    # de la machine. Maintenant, le mode "auto" crée toujours le venv.
    # Pour utiliser un autre env, passer explicitement par :
    #   --bootstrap=pip   (install dans l'env Python courant)
    #   --bootstrap=none  (assume que tout est déjà là)

    # Sous Windows : Scripts/ au lieu de bin/
    venv_bin    = venv_path / ("Scripts" if is_windows else "bin")
    venv_python = venv_bin / ("python.exe" if is_windows else "python")
    venv_pip    = venv_bin / ("pip.exe"    if is_windows else "pip")

    # Si le venv existe déjà avec les déps : juste re-exécuter dedans
    if venv_python.exists():
        check_cmd = [str(venv_python), "-c",
                     "import " + ", ".join(deps_critiques)]
        r_check = subprocess.run(check_cmd, capture_output=True)
        if r_check.returncode == 0:
            print(f"  Relaunching in venv : {venv_path}")
            relancer_dans_venv(venv_python, is_windows)
            # Ne retourne pas — soit os.execv (Unix), soit sys.exit (Windows)

    # Créer le venv s'il n'existe pas encore
    if not venv_python.exists():
        # Sur Linux/Ubuntu : vérifier python3-venv AVANT de tenter la création
        verifier_venv_linux()
        suppr_cmd = ("rmdir /s /q %USERPROFILE%\\.lidar2map" if is_windows
                     else "rm -rf ~/.lidar2map")
        print()
        print("  ╔══════════════════════════════════════════════════════════════╗")
        print("  ║  First launch - creating an isolated Python environment".ljust(63) + " ║")
        print("  ║  (~50 MB once deps are installed). This env is local to".ljust(63) + " ║")
        print("  ║  the project and does not touch your system Python.".ljust(63) + " ║")
        print("  ║".ljust(63) + " ║")
        print(f"  ║  To remove it: {suppr_cmd}".ljust(63) + " ║")
        print("  ║".ljust(63) + " ║")
        print("  ║  To use a direct install (no venv):".ljust(63) + " ║")
        print("  ║    python lidar2map.py --bootstrap=pip".ljust(63) + " ║")
        print("  ╚══════════════════════════════════════════════════════════════╝")
        print(f"  Creating venv {venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True)
        except subprocess.CalledProcessError as e:
            print(f"  ERROR creating venv: {e}")
            print("  Install Python 3.8+ with the venv module.")
            sys.exit(1)

    # Déps installées dans le venv. numba est inclus systématiquement :
    # il accélère le calcul SVF de ×15 à ×50. osmium est inclus pour le
    # pipeline OSM → GeoJSON (sans, ce pipeline n'est pas disponible).
    # Si l'install d'une dep optionnelle (osmium, numba) échoue, on retry
    # sans elle plutôt que de bloquer tout le script.
    #
    # Deps GUI : spécifiques à la plateforme (Qt sur les trois OS, avec
    # Cocoa/WebKit en plus sur macOS).
    _gui_crit, _gui_opt = gui_deps_plateforme()
    deps_critiques  = ["Pillow", "pyproj", "numpy", "scipy", "ijson",
                       "rasterio", "fiona", "pywebview", "certifi"] + _gui_crit
    deps_optionnelles = ["osmium", "numba"] + _gui_opt
    deps_pip = deps_critiques + deps_optionnelles
    print("  Installing dependencies in the venv (3-5 min)...")

    def _pip_install(pkgs):
        """Tente pip install. Retourne (success, stderr_msg)."""
        try:
            r = subprocess.run(
                [str(venv_pip), "install", "-q",
                 "--disable-pip-version-check"] + pkgs,
                capture_output=True, text=True, timeout=900)
            return r.returncode == 0, (r.stderr or "")[-500:]
        except subprocess.TimeoutExpired:
            return False, "pip install timeout (>900s, reseau bloque ?)"
        except subprocess.CalledProcessError as e:
            return False, str(e)

    install_ok, err_msg = _pip_install(deps_pip)
    if not install_ok:
        # Retry sans les deps optionnelles : si l'une d'elles est cassée
        # (cas pyrosm 0.6.2 sur Python 3.12), on garde au moins le pipeline
        # principal (LiDAR + raster).
        print("  Bulk install failed, retrying without optional deps...")
        install_ok, err_msg = _pip_install(deps_critiques)
        if install_ok:
            # Tenter ensuite chaque optionnelle individuellement.
            print("  Critical deps installed. Trying optional deps one by one...")
            opt_failed = []
            for opt in deps_optionnelles:
                ok_one, _ = _pip_install([opt])
                if not ok_one:
                    opt_failed.append(opt)
                    print(f"    ⚠ {opt} : install failed - associated pipeline unavailable")
                else:
                    print(f"    ✓ {opt} : OK")
            if opt_failed:
                print(f"  ⚠ Optional deps not installed: {', '.join(opt_failed)}")
                print(f"     Retry manuel possible : {venv_pip} install {' '.join(opt_failed)}")
        else:
            print("  ERROR installing critical deps in the venv:")
            print(f"  {err_msg}")
            print("  Check your internet connection, then try:")
            print(f"    {venv_pip} install {' '.join(deps_critiques)}")
            sys.exit(1)
    print("  ✓ Dependencies installed.")

    # Relancer le script avec le Python du venv
    print("  Relaunching in venv...")
    relancer_dans_venv(venv_python, is_windows)


def relancer_dans_venv(venv_python, is_windows):
    """Relance le script avec le Python du venv, comportement OS-spécifique.

    Unix : os.execv remplace le process courant — le shell ne récupère
           la main qu'après terminaison du child. C'est le comportement
           attendu, économique en RAM (pas de double process).

    Windows : os.execv y a un comportement différent de Unix — le parent
              termine immédiatement et le child tourne en arrière-plan, ce
              qui fait que le shell affiche son prompt avant la sortie du
              child. Pour éviter cette confusion d'affichage, on utilise
              subprocess.run + sys.exit : on attend la fin du child et on
              propage son code retour avant de rendre la main au shell.

              IMPORTANT : on passe explicitement stdout=sys.stdout et
              stderr=sys.stderr au child, sinon quand le parent est lancé
              par la GUI avec stdout=PIPE, le pipe ne se propage pas au
              child venv, et la GUI ne voit jamais rien des messages que
              le child écrit. Sans ce flush du parent au préalable, les
              traces "[trace]" et "[init]" du parent se mélangent avec
              celles du child à cause du buffering.
    """
    if is_windows:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            r = subprocess.run([str(venv_python)] + sys.argv,
                               stdout=sys.stdout, stderr=sys.stderr,
                               stdin=sys.stdin)
            sys.exit(r.returncode)
        except KeyboardInterrupt:
            sys.exit(130)
    else:
        os.execv(str(venv_python),
                 [str(venv_python)] + sys.argv)


def bootstrap_pip():
    """S'assure que pip est disponible via ensurepip si nécessaire."""
    r = subprocess.run([sys.executable, "-m", "pip", "--version"],
                       capture_output=True)
    if r.returncode == 0:
        return  # pip déjà disponible
    print("  pip missing, bootstrap via ensurepip...")
    try:
        import ensurepip
        ensurepip.bootstrap(upgrade=True)
        print("  pip installed.")
    except Exception as e:
        print(f"  ERROR bootstrap pip: {e}")
        print("  Install pip manually: https://pip.pypa.io/en/stable/installation/")
        sys.exit(1)


def installer_deps(*, gui_deps_plateforme):
    """Vérifie et installe les dépendances Python requises au démarrage.

    Stratégie d'installation, par ordre d'essai :
    1. ``pip install <deps>`` standard
    2. ``pip install --break-system-packages <deps>`` (PEP 668 — Linux récent,
       Homebrew Mac récent)
    3. ``pip install --user <deps>`` (fallback dernière chance)

    Si toutes échouent, on s'arrête PROPREMENT avec un message clair plutôt
    que de continuer pour planter sur le premier ``import pyproj`` venu.
    """
    # Deps GUI spécifiques à la plateforme (Qt partout, Cocoa/WebKit sur macOS)
    _gui_crit, _gui_opt = gui_deps_plateforme()

    # find_spec ne charge pas le module — beaucoup plus rapide que __import__
    # pour les modules lourds (rasterio, scipy, PIL, PyQt6 prennent 200-500 ms
    # chacun à l'import). Gain typique au démarrage à froid : 2-3 s.
    import importlib.util as _ilu

    def _module_present(name: str) -> bool:
        try:
            return _ilu.find_spec(name) is not None
        except (ImportError, ValueError):
            # ValueError : module parent absent (PyQt6.X quand PyQt6 manque)
            return False

    deps = []
    for pkg in [
        "Pillow", "pyproj", "numpy", "scipy", "ijson", "rasterio",
        "fiona", "certifi", "pywebview", "osmium", "numba",
    ]:
        mod = MODULE_PAR_PAQUET[pkg]
        if not _module_present(mod):
            deps.append(pkg)

    # Ajouter les deps GUI plateforme non encore installées
    for pkg in _gui_crit + _gui_opt:
        _mod = MODULE_PAR_PAQUET.get(pkg, pkg)
        if not _module_present(_mod):
            if pkg not in deps:
                deps.append(pkg)

    if not deps:
        return

    # Distinguer deps critiques (sans elles, le script ne tourne pas) et
    # deps optionnelles (utiles pour certains pipelines spécifiques).
    # Les deps optionnelles ne doivent pas bloquer si elles échouent à
    # s'installer — sinon un wheel buggé empêcherait toute utilisation
    # du script (cas vécu avec pyrosm 0.6.2 cassé sur Python 3.12).
    # Les deps GUI optionnelles (pyobjc sur macOS) sont aussi dans ce set.
    DEPS_OPTIONNELLES = ({"osmium", "numba", "py7zr", "mapbox-vector-tile"}
                         | set(_gui_opt))
    deps_crit = [d for d in deps if d not in DEPS_OPTIONNELLES]
    deps_opt  = [d for d in deps if d in DEPS_OPTIONNELLES]

    print(f"  Installing dependencies: {', '.join(deps)}...")

    # Détecter si on est dans un venv. Dans un venv, --user n'a aucun sens
    # (pip refuse) — il faut juste tenter l'install standard.
    in_venv = (hasattr(sys, "real_prefix")
               or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix))

    base_cmd = [sys.executable, "-m", "pip", "install", "-q",
                "--disable-pip-version-check"]

    def _strategies_pour(paquets):
        if in_venv:
            # Dans un venv : --user n'a aucun sens et PEP 668 ne s'applique pas.
            return [(base_cmd + paquets, "standard (venv)")]
        return [
            (base_cmd + paquets, "standard"),
            (base_cmd + paquets + ["--break-system-packages"],
             "--break-system-packages (PEP 668)"),
            (base_cmd + paquets + ["--user"],
             "--user (install locale)"),
        ]

    def _imports_critiques_manquants(paquets):
        rates = []
        for pkg in paquets:
            mod = MODULE_PAR_PAQUET.get(pkg, pkg)
            try:
                __import__(mod)
            except ImportError:
                rates.append(pkg)
        return rates

    strategies = _strategies_pour(deps)

    last_stderr = ""
    install_ok = False
    for cmd, label in strategies:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        except (OSError, FileNotFoundError) as e:
            last_stderr = f"pip not found : {e}"
            continue
        except subprocess.TimeoutExpired:
            last_stderr = f"pip install timeout (>900s) : {label}"
            continue
        if r.returncode == 0:
            # Vérifier que les imports critiques fonctionnent.
            # Les deps optionnelles ne sont PAS dans cette vérification —
            # leur absence ne doit pas bloquer.
            rates = _imports_critiques_manquants(deps_crit)
            if not rates:
                print(f"  ✓ Install succeeded ({label})")
                install_ok = True
                break
            print(f"  Tentative {label} : pip OK but critical imports fail ({', '.join(rates)})")
            last_stderr = f"installation faite mais imports {rates} indisponibles"
        else:
            last_stderr = (r.stderr or r.stdout or "").strip()
            if last_stderr:
                last_stderr = last_stderr.split("\n")[-3:]
                last_stderr = "\n  ".join(last_stderr)

    # Si install groupée a échoué, retry avec deps_crit seules (sans les
    # optionnelles qui peuvent être en cause). Cas typique : osmium Cython
    # cassé sur Python 3.12 → l'install groupée plante, mais les autres
    # deps critiques s'installent très bien seules.
    if not install_ok and deps_opt and deps_crit:
        print(f"  Retry without optional deps ({', '.join(deps_opt)})...")
        for cmd, label in _strategies_pour(deps_crit):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            except (OSError, FileNotFoundError) as e:
                last_stderr = f"pip not found : {e}"
                continue
            except subprocess.TimeoutExpired:
                last_stderr = f"pip install timeout (>900s) : {label}"
                continue
            if r.returncode == 0:
                rates = _imports_critiques_manquants(deps_crit)
                if not rates:
                    print(f"  ✓ Critical deps installed (without: {', '.join(deps_opt)})")
                    print("  ⚠ Optional deps not installed: associated pipelines unavailable")
                    print("     - osmium : --osm --file-formats geojson")
                    print("     - numba  : SVF lent (×15 fois plus)")
                    install_ok = True
                    break
                print(f"  Tentative {label} : pip OK but critical imports fail ({', '.join(rates)})")
                last_stderr = f"installation faite mais imports {rates} indisponibles"
            else:
                last_stderr = (r.stderr or r.stdout or "").strip()
                if last_stderr:
                    last_stderr = last_stderr.split("\n")[-3:]
                    last_stderr = "\n  ".join(last_stderr)

    # Cas limite : il ne restait QUE des deps optionnelles à installer et elles
    # ont échoué. Rien de critique ne manque, donc rien ne justifie d'arrêter.
    # Sans ce garde-fou, le retry ci-dessus est sauté (il exige deps_crit non
    # vide) et on tombe dans le message d'erreur fatal avec un "Missing
    # modules:" VIDE. Cas vécu : macOS x86_64, llvmlite n'a plus de wheel donc
    # numba ne s'installe pas, et tout le build s'arrêtait là.
    if not install_ok and deps_opt and not deps_crit:
        print(f"  ⚠ Optional deps not installed: {', '.join(deps_opt)}")
        print("     Reduced functionality, nothing critical is missing.")
        print("     - osmium : --osm --file-formats geojson")
        print("     - numba  : SVF lent (×15 fois plus)")
        install_ok = True

    if install_ok:
        return

    # Toutes les tentatives ont échoué — on arrête ici avec un message clair.
    import platform as _plat
    _is_mac   = _plat.system() == "Darwin"
    _is_linux = _plat.system() == "Linux"
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ERROR: cannot install the Python dependencies      ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(f"  Missing modules: {', '.join(deps_crit)}")
    if last_stderr:
        print(f"  Dernier message pip :\n  {last_stderr}")
    print()
    print("  Solutions possibles :")
    if _is_mac:
        print("    1. Install in a venv:")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps_crit)}")
        print("       Then relaunch: python lidar2map.py --bootstrap=none")
        print()
        print("    2. Force a system install (not recommended):")
        print(f"       pip install --break-system-packages {' '.join(deps)}")
    elif _is_linux:
        print("    1. Install via the package manager:")
        print(f"       sudo apt install python3-{' python3-'.join(d.lower() for d in deps)}")
        print()
        print("    2. Use a venv:")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps)}")
    else:
        print(f"    pip install {' '.join(deps)}")
    print()
    sys.exit(1)


def installer_toutes_dependances(
    *,
    gui_deps_plateforme,
    importer=__import__,
    lancer=None,
    executable=None,
    ecrire=print,
):
    """Installe les dépendances de maintenance et retourne ``True`` si OK.

    Les paquets optionnels ne bloquent pas la commande. Toute dépendance
    critique qui ne peut pas être importée ou installée fait en revanche
    retourner ``False``. Les coutures injectables gardent ce chemin testable
    sans réseau ni invocation réelle de pip.
    """
    if lancer is None:
        lancer = subprocess.run
    if executable is None:
        executable = sys.executable

    gui_critiques, gui_optionnelles = gui_deps_plateforme()
    critiques = [
        "Pillow", "pyproj", "numpy", "scipy", "ijson", "rasterio",
        "fiona", "certifi", "pywebview", *gui_critiques,
    ]
    optionnelles = [
        "osmium", "numba", "laspy", "lazrs", "py7zr",
        "mapbox-vector-tile", "cloth-simulation-filter", *gui_optionnelles,
    ]
    pip_base = [executable, "-m", "pip", "install", "-q"]

    ecrire("  Full install of all dependencies...")
    for paquet in critiques + optionnelles:
        module = MODULE_PAR_PAQUET[paquet]
        try:
            importer(module)
        except ImportError:
            resultat = lancer(pip_base + [paquet], capture_output=True)
            if resultat.returncode == 0:
                # Le paquet vient d'être ajouté dans un sous-processus. Une
                # réimportation immédiate peut rester aveugle aux nouveaux
                # sous-modules d'un package parent déjà chargé (notamment
                # PyQt6-WebEngine). Le prochain processus, puis PyInstaller,
                # constituent la validation dans un environnement frais.
                ecrire(f"    ✓ {paquet}")
                continue

            if paquet in critiques:
                ecrire(f"    ERROR {paquet} (critical dependency unavailable)")
                return False
            ecrire(f"    ⚠ {paquet} (optional - skipped)")
        else:
            ecrire(f"    ✓ {paquet} (already installed)")

    ecrire("  All dependencies installed.")
    return True


def orchestrer_bootstrap(
    *,
    frozen,
    resoudre_mode,
    bootstrap_venv_avec_mode,
    bootstrap_pip,
    installer_dependances,
    restaurer_tls_strict,
):
    """Route le démarrage vers le moteur venv/pip approprié.

    La résolution est toujours exécutée en premier afin que l'aide et les
    options précoces soient traitées aussi dans un bundle PyInstaller. Un
    bundle frozen court-circuite ensuite tous les effets venv, pip et TLS car
    ses dépendances Python sont déjà embarquées.

    Séquences hors bundle :

    - ``auto`` : venv, dépendances, restauration TLS ;
    - ``pip`` : venv/no-op, ensurepip, dépendances, restauration TLS ;
    - ``none`` : vérification du moteur venv, sans installation ni TLS.
    """
    mode = resoudre_mode()
    if frozen:
        return
    bootstrap_venv_avec_mode(mode)
    if mode == "pip":
        bootstrap_pip()
    if mode != "none":
        installer_dependances()
        restaurer_tls_strict()


def bootstrap_venv_avec_mode(
    mode,
    *,
    environnement,
    bootstrap_venv,
):
    """Appelle le moteur venv historique avec un mode pré-résolu.

    Le mode transite temporairement par ``LIDAR2MAP_BOOTSTRAP`` afin de ne pas
    modifier la signature publique du moteur. La variable est supprimée à la
    fin, y compris si elle existait avant l'appel : cette sémantique historique
    évite de faire fuir le mode synthétique après le retour dans les futurs
    sous-processus.
    """
    environnement["LIDAR2MAP_BOOTSTRAP"] = mode
    try:
        bootstrap_venv()
    finally:
        environnement.pop("LIDAR2MAP_BOOTSTRAP", None)
