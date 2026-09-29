"""Runtime effectif du bootstrap precoce de lidar2map.

Le module ne produit aucun effet lors de son import. Les operations de processus,
venv et pip ne sont executees que par les facades historiques de lidar2map.

Dépendances : déclarées une seule fois, dans requirements.in, et installées
depuis le verrou requirements.txt (versions exactes, empreintes SHA-256,
valable pour Windows, macOS et Linux), par le mode sources comme par la
construction du programme et la CI. Il n'y a plus de liste de paquets ici :
jusqu'à la 1.55, quatre listes codées en dur divergeaient entre elles, et
rien n'était figé.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


RACINE = Path(__file__).resolve().parent
# Dépendances directes (noms seuls), et leur verrou, à côté de lidar2map.py.
DEPENDANCES = RACINE / "requirements.in"
VERROU = RACINE / "requirements.txt"
# Dans le venv du mode sources : empreinte du verrou qu'on y a installé. Un
# verrou changé (nouvelle version de lidar2map) le fait réinstaller.
MARQUE_VERROU = "lidar2map-verrou.sha256"


def nom_normalise(nom: str) -> str:
    """Nom de distribution comparable (PEP 503) : « Pillow », « pillow » et
    « cloth_simulation_filter » / « cloth-simulation-filter » se valent."""
    return re.sub(r"[-_.]+", "-", nom).lower()


def dependances_directes(fichier: Path = DEPENDANCES, *, conditionnelles=False) -> list:
    """Noms des paquets de requirements.in, sans version.

    Un paquet qui porte un marqueur d'environnement (« ; sys_platform ... »)
    est conditionnel : absent à bon droit sur certains systèmes (numba sur
    les Mac Intel, faute de roue), il n'est rendu que sur demande. Le
    contrôle au démarrage ne l'exige donc pas, comme les dépendances dites
    optionnelles d'avant le verrou."""
    noms = []
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne or ligne.startswith("-"):
            continue
        if ";" in ligne and not conditionnelles:
            continue
        noms.append(re.split(r"[\s<>=!~;\[]", ligne, maxsplit=1)[0])
    return noms


def dependances_absentes(noms, distributions=None) -> list:
    """Ceux de ``noms`` qu'aucune distribution installée ne fournit.

    Lit les métadonnées des paquets installés, sans rien importer : pas de
    table paquet-module à tenir (Pillow s'importe PIL, cloth-simulation-filter
    CSF), et aucun module lourd chargé au démarrage."""
    if distributions is None:
        import importlib.metadata
        distributions = importlib.metadata.distributions()
    installes = {nom_normalise(d.metadata["Name"] or "") for d in distributions}
    return [nom for nom in noms if nom_normalise(nom) not in installes]


def empreinte_verrou(verrou: Path = VERROU) -> str:
    return hashlib.sha256(verrou.read_bytes()).hexdigest()


def commande_installation(python, *options, verrou: Path = VERROU) -> list:
    """pip install du verrou, empreintes vérifiées."""
    return [str(python), "-m", "pip", "install", "-q", "--disable-pip-version-check",
            "--require-hashes", "-r", str(verrou), *options]


def retablir_environnement_systeme(*, fige=None, plateforme=None, environ=None):
    """Rend aux programmes du système le LD_LIBRARY_PATH d'origine.

    Sous Linux, le bootloader de PyInstaller préfixe cette variable du dossier
    de ses bibliothèques et garde l'ancienne valeur dans
    LD_LIBRARY_PATH_ORIG. Tout enfant en hérite : systemctl (démarrage
    automatique), xdg-open ou le navigateur chargeaient alors les
    bibliothèques du binaire au lieu des leurs, et le systemd de Debian
    Trixie refuse une libcrypto plus ancienne que la sienne (constaté sur
    blink2video, issue #23). C'est le rétablissement que recommande
    PyInstaller pour les programmes externes :
    https://pyinstaller.org/en/stable/runtime-information.html#ld-library-path-libpath-considerations

    Appelée par lidar2map.py dès son démarrage, avant tout lancement de
    processus : une relance (« Redémarrer ») reçoit ainsi un environnement
    propre, dont elle gardera à son tour la bonne valeur d'origine. Le
    chargeur d'un processus ne lit la variable qu'à son démarrage : la
    rétablir ne change rien pour lui.
    """
    fige = getattr(sys, "frozen", False) if fige is None else fige
    plateforme = sys.platform if plateforme is None else plateforme
    environ = os.environ if environ is None else environ
    if not fige or plateforme in ("win32", "darwin"):
        return
    origine = environ.get("LD_LIBRARY_PATH_ORIG")
    if origine is not None:
        environ["LD_LIBRARY_PATH"] = origine
    else:
        # Variable absente avant le bootloader : il n'a rien gardé à rétablir.
        environ.pop("LD_LIBRARY_PATH", None)


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
        (app_data, "ancienne extraction du lanceur (<= 1.54)"),
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
    executable=None,
    supprimer_arbre=shutil.rmtree,
    ecrire=print,
):
    """Supprime les seules cibles planifiées et retourne ``True`` si complet.

    ``executable`` est le programme figé en cours. Depuis la 1.55, il peut
    être installé n'importe où, y compris dans le dossier où le lanceur d'une
    version <= 1.54 extrayait le sien : une cible qui le contient est gardée,
    sa suppression détruirait le programme lui-même."""
    cibles = chemins_desinstallation(
        systeme=systeme,
        home=home,
        localappdata=localappdata,
    )
    programme = Path(executable).resolve() if executable else None
    total = 0
    complet = True
    ecrire("")
    ecrire("  ── lidar2map uninstall ──────────────────────────────────")
    ecrire("")
    for chemin, label in cibles:
        if not chemin.exists() and not chemin.is_symlink():
            ecrire(f"  {label} : absent ({chemin})")
            continue
        if programme is not None and chemin.resolve() in programme.parents:
            ecrire(f"  {label} : kept, the running program lives there ({chemin})")
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
    ecrire("  Note: lidar2map.py and the program folder (.app/.exe) are not removed.")
    ecrire("  Remove them manually if needed.")
    ecrire("")
    return complet


def nettoyer_ancienne_extraction(*, systeme, home, localappdata=None, executable):
    """Retire ce qu'un lanceur d'une version <= 1.54 a laissé, et rend la
    liste de ce qui a été retiré.

    Deux restes : le programme qu'il extrayait dans le dossier de données de
    l'OS (même chemin que chemins_desinstallation), et son bundle zippé resté
    à côté du programme quand la nouvelle archive a été décompressée
    par-dessus l'ancienne. Le dossier n'est retiré que s'il porte la marque
    du lanceur (.bundle_sha) et que le programme ne tourne pas depuis lui. Il
    est d'abord renommé : sous Windows, le renommage échoue tant qu'une
    ancienne instance y tourne encore, et le nettoyage attend alors le
    lancement suivant."""
    retires = []
    programme = Path(executable).resolve()
    zip_voisin = programme.parent / "lidar2map_bundle.zip"
    if zip_voisin.is_file():
        try:
            zip_voisin.unlink()
            retires.append(zip_voisin)
        except OSError:
            pass

    dossier = chemins_desinstallation(
        systeme=systeme, home=home, localappdata=localappdata)[0][0]
    corbeille = dossier.with_name(dossier.name + ".ancienne-extraction")
    if corbeille.exists():   # reste d'un nettoyage interrompu
        shutil.rmtree(corbeille, ignore_errors=True)
    if not (dossier / ".bundle_sha").is_file():
        return retires
    if dossier.resolve() in programme.parents:
        return retires
    try:
        os.rename(dossier, corbeille)
    except OSError:
        return retires
    shutil.rmtree(corbeille, ignore_errors=True)
    retires.append(dossier)
    return retires


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
    verifier_venv_linux,
    relancer_dans_venv,
):
    """Bootstrap automatique d'un environnement Python isolé.

    Comportement par défaut : crée un venv dans ``~/.lidar2map/`` (Mac/Linux)
    ou ``%USERPROFILE%\\.lidar2map\\`` (Windows) au 1er lancement, y installe
    les dépendances du verrou requirements.txt (versions exactes, empreintes
    vérifiées), et y relance le script. Un verrou changé depuis (nouvelle
    version de lidar2map) est réinstallé au lancement suivant. Comportement
    uniforme sur les 3 OS.

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
      --bootstrap=pip     : install directe du verrou dans l'env Python
                            courant (utilise --break-system-packages si
                            PEP 668), quitte à changer la version de
                            paquets déjà installés dans cet env
      --bootstrap=none    : pas d'install — vérifie que les dépendances de
                            requirements.in sont installées et plante avec
                            un message clair sinon. Utile pour ceux qui
                            gèrent leur propre env (conda, venv manuel,
                            install système contrôlée).
      --help-bootstrap    : affiche cette aide et quitte

    Variables d'environnement équivalentes :
      LIDAR2MAP_BOOTSTRAP=auto|pip|none

    Suppression du venv à tout moment :
      rm -rf ~/.lidar2map                       (Mac/Linux)
      rmdir /s /q %USERPROFILE%\\.lidar2map     (Windows)
    Le script en recréera un au prochain lancement si besoin.
    """
    mode = resoudre_mode()

    # ── Mode "none" : juste vérifier, planter clairement s'il en manque ──
    if mode == "none":
        manquantes = dependances_absentes(dependances_directes())
        if manquantes:
            print()
            print("  ╔══════════════════════════════════════════════════════════════╗")
            print("  ║  Mode --bootstrap=none: auto-install disabled              ║")
            print("  ╚══════════════════════════════════════════════════════════════╝")
            print(f"  Missing Python packages: {', '.join(manquantes)}")
            print()
            print("  Install them yourself, at the exact versions of the lock:")
            print(f"    pip install -r {VERROU}")
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
    marque      = venv_path / MARQUE_VERROU
    empreinte   = empreinte_verrou()

    # Venv déjà installé depuis ce même verrou : juste re-exécuter dedans
    try:
        a_jour = venv_python.exists() and marque.read_text().strip() == empreinte
    except OSError:
        a_jour = False
    if a_jour:
        print(f"  Relaunching in venv : {venv_path}")
        relancer_dans_venv(venv_python, is_windows)
        # Ne retourne pas — soit os.execv (Unix), soit sys.exit (Windows) ;
        # le return ne sert que si cette relance revenait quand même.
        return

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

    # Toutes les dépendances d'un coup, aux versions exactes du verrou, dont
    # pip vérifie les empreintes. Un venv plus ancien est remis aux versions
    # du verrou actuel.
    print("  Installing dependencies in the venv (3-5 min)...")
    commande = commande_installation(venv_python)
    try:
        r = subprocess.run(commande, capture_output=True, text=True, timeout=1800)
        erreur = "" if r.returncode == 0 else (r.stderr or r.stdout or "")[-800:]
    except subprocess.TimeoutExpired:
        erreur = "pip install timeout (>1800s, reseau bloque ?)"
    if erreur:
        print("  ERROR installing the dependencies in the venv:")
        print(f"  {erreur.strip()}")
        print("  Check your internet connection, then try:")
        print("    " + subprocess.list2cmdline(commande))
        sys.exit(1)
    marque.write_text(empreinte + "\n")
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


def installer_deps():
    """Vérifie les dépendances au démarrage et installe le verrou s'il en manque.

    Rapide quand tout est là : lit les métadonnées des paquets installés, sans
    rien importer ni lancer pip. Sinon, ``pip install -r requirements.txt``,
    par ordre d'essai :
    1. standard ;
    2. ``--break-system-packages`` (PEP 668 — Linux récent, Homebrew Mac récent) ;
    3. ``--user`` (fallback dernière chance).
    Dans un venv, seul le premier a un sens.

    Si toutes échouent, on s'arrête PROPREMENT avec un message clair plutôt
    que de continuer pour planter sur le premier ``import pyproj`` venu.
    """
    manquantes = dependances_absentes(dependances_directes())
    if not manquantes:
        return

    print(f"  Installing dependencies: {', '.join(manquantes)}...")
    # Dans un venv, --user n'a aucun sens (pip refuse) et PEP 668 ne
    # s'applique pas : seule l'install standard.
    in_venv = (hasattr(sys, "real_prefix")
               or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix))
    if in_venv:
        strategies = [((), "standard (venv)")]
    else:
        strategies = [
            ((), "standard"),
            (("--break-system-packages",), "--break-system-packages (PEP 668)"),
            (("--user",), "--user (install locale)"),
        ]

    derniere_erreur = ""
    for options, libelle in strategies:
        try:
            r = subprocess.run(commande_installation(sys.executable, *options),
                               capture_output=True, text=True, timeout=1800)
        except (OSError, subprocess.TimeoutExpired) as e:
            derniere_erreur = f"{libelle} : {e}"
            continue
        if r.returncode == 0:
            print(f"  ✓ Install succeeded ({libelle})")
            return
        derniere_erreur = "\n  ".join((r.stderr or r.stdout or "").strip().split("\n")[-3:])

    # Toutes les tentatives ont échoué — on arrête ici avec un message clair.
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ERROR: cannot install the Python dependencies      ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(f"  Missing packages: {', '.join(manquantes)}")
    if derniere_erreur:
        print(f"  Dernier message pip :\n  {derniere_erreur}")
    print()
    print("  Solutions possibles :")
    print("    1. Let lidar2map create its own isolated environment (recommended):")
    print("       python lidar2map.py --bootstrap=auto")
    print("    2. Install the lock into a venv of your own, then relaunch with")
    print("       --bootstrap=none:")
    print(f"       pip install -r {VERROU}")
    print()
    sys.exit(1)


def installer_toutes_dependances(
    *,
    lancer=None,
    executable=None,
    ecrire=print,
):
    """``--installer-deps`` : installe le verrou complet dans l'environnement
    courant (celui du venv, après la relance) et retourne ``True`` si pip a
    réussi. Utilisé par les scripts setup_build_*, qui y ajoutent ensuite
    PyInstaller par requirements-build.txt. Les coutures injectables gardent
    ce chemin testable sans réseau ni invocation réelle de pip.
    """
    if lancer is None:
        lancer = subprocess.run
    if executable is None:
        executable = sys.executable

    ecrire("  Installing the locked dependencies (requirements.txt)...")
    resultat = lancer(commande_installation(executable), capture_output=True, text=True)
    if resultat.returncode != 0:
        ecrire("    ERROR: pip could not install the lock:")
        ecrire("    " + (resultat.stderr or resultat.stdout or "").strip()[-800:])
        return False
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
