# lidar2map — Documentation build & déploiement

## Table des matières

1. [Architecture](#1-architecture)
2. [Fichiers du projet](#2-fichiers-du-projet)
3. [Paramètres CLI spéciaux](#3-paramètres-cli-spéciaux)
4. [Préparer une machine de build](#4-préparer-une-machine-de-build)
5. [Builder l'application](#5-builder-lapplication)
6. [Livrer une version](#6-livrer-une-version)
7. [Lancer l'application](#7-lancer-lapplication)
8. [Désinstaller](#8-désinstaller)
9. [Dépannage](#9-dépannage)

---

## 1. Architecture

### Programme livré tel quel

Depuis la 1.55, chaque archive de release contient le programme lui-même,
comme celles de blink2video et de watch2notif : le dossier onedir de
PyInstaller sous Windows et Linux, un `.app` sous macOS.

```
lidar2map-windows-x86_64/          (lidar2map-linux-x86_64/ sous Linux)
  lidar2map.exe                    entry point = _loader.py
  _internal/
    lidar2map.py                   exécuté en texte par _loader.py
    rasterio/
    gui/          index.html + app.js + style.css (servis en HTTP local)
    osmosis/      embarqué si présent au moment du build
    jre/          embarqué si présent au moment du build
    ...
  lidar2map_icon.png

LIDAR2MAP.app/                     (macOS)
  Contents/MacOS/lidar2map
  Contents/Frameworks/             sys._MEIPASS : binaires (dont le JRE),
                                   liens vers les données
  Contents/Resources/              données (osmosis, gui, lidar2map.py...)
```

Dans le `.app`, PyInstaller range tout fichier Mach-O, même ajouté comme
donnée, sous `Contents/Frameworks`, le reste sous `Contents/Resources`, et
relie les deux par des liens symboliques : vu de `sys._MEIPASS`,
l'arborescence reste celle du dossier onedir. Un nom de dossier à point y
devient `__dot__` (`.dylibs` → `__dot__dylibs`), ce dont tient compte le
correctif libtiff du build Intel.

Jusqu'à la 1.54, un lanceur onefile contenait ce dossier zippé
(`lidar2map_bundle.zip`) et l'extrayait au premier lancement dans
`%LOCALAPPDATA%\lidar2map\`, `~/Library/Application Support/lidar2map/` ou
`~/.local/share/lidar2map/` : deux exemplaires sur disque, 30 à 60 s
d'attente après chaque mise à jour, et une dualité lanceur / exe interne à
l'origine des bugs de « Redémarrer » et du démarrage automatique (option C
de D2, [docs/preconisations_evolution.md](docs/preconisations_evolution.md)).

Au démarrage, la 1.55 retire ce qu'un tel lanceur a laissé : son
extraction, reconnue à sa marque `.bundle_sha`, et le `lidar2map_bundle.zip`
resté à côté du programme quand l'archive est décompressée par-dessus
(`_bootstrap_runtime.nettoyer_ancienne_extraction`). Si une ancienne
instance tourne encore depuis l'extraction, son renommage échoue sous
Windows et le ménage attend le lancement suivant. Le nom des archives et de
leur dossier racine n'a pas changé : décompressée par-dessus, une archive
met le programme au chemin du lanceur, et les raccourcis comme le démarrage
automatique restent valables.

`_loader.py`, qui exécute `_internal/lidar2map.py` en texte, servait au
patch sans reconstruction retiré en 1.53 (D2) ; il reste en place.

### Interface graphique

Depuis la 1.49.0, il n'y a plus de backend graphique embarqué (pywebview,
PyQt6/QtWebEngine et Cocoa retirés, plus collectés par les specs) : un
lancement sans argument équivaut à `--serve-gui`. `_serve_web.py` (stdlib,
`ThreadingHTTPServer`) sert `gui/` sur `http://127.0.0.1:8766/` et le
navigateur par défaut l'affiche. Les appels de `app.js` passent par
`gui/web_bridge.js` (fetch vers `/api/*`).

| Élément | Implémentation |
|---------|----------------|
| Sécurité | `Handler.hote_autorise()` : `Host`, adresse TCP du client et `Origin` vérifiés ; pas de compte |
| Icône de zone de notification | `pystray` + Pillow, menu Ouvrir / Redémarrer / Arrêter ; `--no-tray` pour s'en passer, repli automatique sans icône si elle ne peut pas être créée |
| Seconde instance | `_instance_existante()` interroge `/api/init` : question dans le terminal s'il est visible (`_terminal_interactif()`), sinon dans la page (`?deja-ouverte=1`) ; rien avec `--no-browser`. `--new-instance` et le bouton « Nouvelle instance » (`/api/new-instance`, `_demarrer_nouvelle_instance()`) démarrent un serveur parallèle (10 ports) |
| Console Windows | `lidar2map.exe` reste une application console (`console=True`) avec `hide_console="hide-early"` : double-clic sans fenêtre de console, CLI inchangée depuis un terminal. La console (même masquée) reste nécessaire à l'arrêt propre des traitements (`CTRL_BREAK_EVENT`). Changement de spec : rebuild |
| Démarrage automatique | `_autostart.py` : raccourci `.lnk` (dossier Démarrage, comme blink2video et watch2notif), agent `launchd`, service `systemd --user`. En mode figé, lance le programme en cours (`sys.executable`) ; aucune variable d'environnement à transmettre, et celles d'un lanceur ≤ 1.54 sont ignorées. Le `.vbs` d'une version ≤ 1.53 est remplacé au démarrage du serveur (exécutable seulement) |
| Dossiers de données | `_dossiers.py` : état (préférences, historique, `lidar2map.env`, journaux) dans `platformdirs.user_data_dir("lidar2map-data")`, sorties (`Projets/`, `cache/`, `production/`) dans `Documents/lidar2map` ; `LIDAR2MAP_HOME` regroupe les deux. Reprise unique de l'état d'une version ≤ 1.53 au lancement (`_preparer_etat()`, sous `__main__` seulement), sorties laissées en place via le réglage `dossier_sorties` |
| Accès distant | `--trusted-host` (réglage enregistré) : `_serve_web.EcouteHoteConfiance` écoute en plus sur son adresse (même port, IPv4/IPv6), réessaie toutes les 30 s tant qu'elle n'existe pas (VPN arrêté), suit les changements à chaud ; le serveur principal reste sur 127.0.0.1. `--bind` sur une autre adresse désactive ce complément |

### Osmosis et JRE

- **Embarqués** si présents dans `~/.lidar2map/` au moment du build (via `setup_build_*.sh/ps1`)
- **Téléchargés automatiquement** au premier besoin s'ils manquent au programme, sauf le greffon mapwriter, que le programme figé tient pour embarqué : `tests/exe_smoke.py` fait écrire un `.map` à la chaîne Java de chaque binaire avant publication
- À préparer avant le build : `python3.12 lidar2map.py --telecharger-outils`

---

## 2. Fichiers du projet

### Fichiers source

| Fichier | Rôle |
|---------|------|
| `lidar2map.py` | Script principal : façade, CLI, API du GUI web |
| `_*.py` | Modules extraits de `lidar2map.py` (pipelines, formats, `_serve_web.py`, `_autostart.py`…), compilés dans le programme |
| `providers/` | Un fichier par source LiDAR/raster |
| `gui/` | Front-end servi par `_serve_web.py` (`index.html`, `app.js`, `style.css`, `web_bridge.js`) |
| `_loader.py` | Entry point PyInstaller : exécute `_internal/lidar2map.py` |
| `lidar2map_mac.spec` | Build macOS (arm64 ou x86_64) : onedir puis `LIDAR2MAP.app` (`BUNDLE`) |
| `lidar2map_mac_build.sh` | Script de build macOS (3 étapes : PyInstaller, signature du `.app`, archive ditto ; notarisation optionnelle) |
| `lidar2map_win.spec` | Build onedir Windows (+ Linux) |
| `lidar2map_win_build.ps1` | Script de build Windows (une passe PyInstaller) |
| `lidar2map_linux_build.sh` | Script de build Linux (miroir bash) |
| `setup_build_mac.sh` | Setup machine de build macOS vierge (5 étapes, pile Intel dédiée) |
| `setup_build_windows.ps1` | Setup machine de build Windows vierge (4 étapes) |
| `setup_build_linux.sh` | Setup machine de build Linux vierge |
| `deploy.py` | **Déploiement unifié en 1 commande** (cross-platform Win/Mac/Linux) : tests, commit et push depuis ce dépôt, puis tag et suivi du build de release |

### Livrables à distribuer

| OS      | Livrables |
|---------|-----------|
| macOS   | `LIDAR2MAP.app` |
| Windows | dossier `lidar2map` : `lidar2map.exe` + `_internal/` |
| Linux   | dossier `lidar2map` : `lidar2map` + `_internal/` |

### `.gitignore` recommandé

```gitignore
dist/
build/staging/
__pycache__/
*.pyc
.DS_Store
logs/
```

### Tests de non-régression

Le runner local lance chaque suite dans un processus isolé et vérifie que tout
nouveau fichier `_test_*.py` ou `test_*.py` est explicitement enregistré :

```bash
python tests/run_tests.py fast        # contrats, atomicité, CLI, docs (~30 s)
python tests/run_tests.py scientific  # calculs/tuilage/interactions (~2 min)
python tests/run_tests.py             # toutes les suites hors réseau
```

La CI exécute le profil `fast` sur Windows, macOS et Linux, puis le profil
`scientific` une seule fois sous Linux pour ne pas tripler les compilations
Numba. `tests/smoke_providers.py` reste séparé : il contacte les services
externes et appartient au workflow hebdomadaire `smoke.yml`.

---

## 3. Paramètres CLI spéciaux

Ces paramètres sont interceptés tôt dans le script (avant la GUI et avant argparse).
Ils fonctionnent aussi bien depuis le script Python que depuis le `.app`/`.exe`.

### `--installer-deps`

Installe TOUTES les dépendances Python (critiques + optionnelles + lazy)
sans ouvrir la GUI. Utilisé par les scripts `setup_build_*`.

```bash
python3.12 lidar2map.py --installer-deps
```

Installe les critiques : Pillow, pyproj, numpy, scipy, ijson, rasterio, fiona,
certifi, pystray ; puis les optionnelles (un échec ne bloque pas) : osmium,
numba, laspy, lazrs, py7zr, mapbox-vector-tile, cloth-simulation-filter.

### `--telecharger-outils`

Télécharge osmosis et le JRE dans `~/.lidar2map/` sans lancer aucun pipeline.
Nécessaire avant un build PyInstaller pour les bundler dans `_internal/`.

```bash
python3.12 lidar2map.py --telecharger-outils
```

### `--desinstaller`

Supprime proprement tous les fichiers créés par lidar2map :

| Élément supprimé | Chemin |
|------------------|--------|
| Ancienne extraction d'un lanceur ≤ 1.54 (macOS) | `~/Library/Application Support/lidar2map/` |
| Ancienne extraction d'un lanceur ≤ 1.54 (Windows) | `%LOCALAPPDATA%\lidar2map\` |
| Ancienne extraction d'un lanceur ≤ 1.54 (Linux) | `~/.local/share/lidar2map/` |
| Venv Python | `~/.lidar2map/venv/` |
| osmosis | `~/.lidar2map/osmosis/` |
| JRE | `~/.lidar2map/jre/` |

L'ancienne extraction est d'ordinaire déjà partie : la 1.55 la retire à son
premier démarrage. Une cible qui contient le programme en cours (installé,
par exemple, dans `%LOCALAPPDATA%\lidar2map\`) est gardée : le programme ne
se supprime jamais lui-même, ni son dossier ni son `.app`.

```bash
python3.12 lidar2map.py --desinstaller
# ou depuis le programme livré
lidar2map.exe --desinstaller
```

### `--smoketest`

Vérifie que les 5 modes du pipeline fonctionnent end-to-end sur une petite
zone (Garéoult, rayon 1 km). Outputs dans `Projets/smoke/` sous la racine des
sorties (`Documents/lidar2map` par défaut, voir `_dossiers.py`). Caches dalles
LiDAR et tuiles WMTS préservés entre les runs (cf. `cache/`).

```bash
# Sur la machine du développeur (script direct)
python3.12 lidar2map.py --smoketest

# Sur la machine de l'utilisateur (post-déploiement)
lidar2map.exe --smoketest                            # Windows
LIDAR2MAP.app/Contents/MacOS/lidar2map --smoketest   # macOS
```

Modes testés (sur le binaire courant, via subprocess) :

| Test | Args supplémentaires | Output attendu |
|------|----------------------|----------------|
| LiDAR     | `--ignlidar --ombrages multi --zoom-min 10 --zoom-max 13` | `smoke_multi_ombrage_z10-13.mbtiles` |
| WMTS      | `--ignraster --couche planign --zoom-min 12 --zoom-max 14` | `smoke_planign_z12-14.mbtiles` |
| WFS       | `--ignvecteur --couche routes` | `smoke_ign_troncon_de_route.geojson.gz` |
| OSM       | `--osm --couche highway=* --formats-fichier map gz` | `smoke.map` + `smoke_osm_highway.geojson.gz` |
| Fusion    | `--fusionner --source <output OSM>` | `smoke_fusion.geojson.gz` |

Exit `0` si les 5 modes passent (présence + taille non-nulle des outputs),
`1` si au moins un échec. Durée typique : ~80 s avec caches existants,
~5 min au 1er run (DL Geofabrik 400 Mo).

Utile pour :
- Valider une nouvelle release avant de la distribuer
- Diagnostiquer chez un utilisateur final qui rapporte un bug
- Détecter une régression après modification de `lidar2map.py`

---

## 4. Préparer une machine de build

Le script de setup fait 4 étapes sur les 3 OS :
1. Python 3.12
2. `--installer-deps` → toutes les dépendances Python dans `~/.lidar2map/venv`
3. `--telecharger-outils` → osmosis + JRE dans `~/.lidar2map/`
4. PyInstaller

Le bootstrap (`_bootstrap_venv_si_besoin` mode `auto`, défaut) crée
**systématiquement** `~/.lidar2map/venv` même si le Python système a déjà
les deps. Permet une désinstallation propre (`rm -rf ~/.lidar2map`) et un
test fresh reproductible. Pour utiliser un autre env (conda, venv perso) :
passer `--bootstrap=pip` (install dans l'env courant) ou `--bootstrap=none`
(assume que les deps sont déjà là, échoue clairement si manquantes).

### macOS (ARM64)

```bash
# Copier les fichiers sur la VM Mac
# tagmapping-min.xml est optionnel mais améliore le tagging OSM —
# sans lui, osmosis utilise son tagmapping par défaut (résultat dégradé).
scp lidar2map.py _loader.py tagmapping-min.xml \
    lidar2map_mac.spec lidar2map_mac_build.sh setup_build_mac.sh \
    m1@<ip-vm>:~/Downloads/

# Setup (installe Python 3.12 si absent, toutes les deps, osmosis, JRE, PyInstaller)
ssh m1@<ip-vm> "bash ~/Downloads/setup_build_mac.sh"
```

### Windows

```powershell
# Autoriser les scripts (une fois)
Unblock-File .\setup_build_windows.ps1
.\setup_build_windows.ps1
```

### Linux (Ubuntu/Debian)

```bash
bash setup_build_linux.sh
```

Note : `python3.12-venv` est un paquet système séparé sur Ubuntu/Debian.
Le script le détecte et affiche `sudo apt install python3.12-venv` si absent.

---

## 5. Builder l'application

### macOS

```bash
# Sur la VM Mac
bash ~/Downloads/lidar2map_mac_build.sh

# Récupérer l'archive depuis Windows, pas le .app lui-même : scp -r suit ses
# liens symboliques et casserait sa structure comme sa signature
scp m1@<ip-vm>:~/Downloads/dist/lidar2map-macos-arm64.zip .
```

Étapes du script :
1. `pyinstaller lidar2map_mac.spec` (2 passes : détection deps + build loader), puis `BUNDLE` → `dist/LIDAR2MAP.app`
2. Correctif libtiff (Intel seulement), puis signature du `.app` complet, dernière mutation avant l'archive
3. `ditto -c -k --keepParent` → `dist/lidar2map-macos-<arch>.zip`, notarisé si `LIDAR2MAP_NOTARY_PROFILE` est fourni

### Windows

```powershell
Unblock-File .\lidar2map_win_build.ps1
.\lidar2map_win_build.ps1
```

Livrable : `dist\lidar2map\`, soit `lidar2map.exe` et `_internal\` (runtime Python, dépendances, JRE et osmosis ; plus de Qt depuis la 1.49.0). `release.yml` en fait le dossier racine de `lidar2map-windows-x86_64.zip`.

### Deux passes PyInstaller (macOS et Windows)

Depuis le passage à `_loader.py` comme entry point, `lidar2map.py` est un
fichier texte non analysé. Les specs lancent donc 2 analyses :

- **Passe 1** : `Analysis("lidar2map.py")` → détecte tous les imports
  (sqlite3, ssl, xml, urllib…)
- **Passe 2** : `Analysis("_loader.py")` → build réel
- Fusion des TOC **après** les deux analyses (pas en entrée — erreur "too many values")

---

## 6. Livrer une version

Toute livraison passe par une **release reconstruite** : `release.yml`
construit les 4 archives (Windows, Linux, macOS Apple Silicon et Intel) sur
des runners neufs, lance chaque binaire (`tests/exe_smoke.py`), puis publie.
Le patch d'un bundle existant sans reconstruction (`update_app.py`,
`update.yml`) a été retiré en 1.53.0 : depuis la v1.45.0, toutes les releases
avaient de toute façon exigé une reconstruction (décision D2 de
[docs/preconisations_evolution.md](docs/preconisations_evolution.md)).

Côté utilisateur, l'application signale la nouvelle version ; il suffit de
décompresser la nouvelle archive par-dessus l'ancienne. Par-dessus, et non à
côté : depuis la 1.54, le programme reprend l'état d'une version antérieure
depuis son propre dossier (voir `_dossiers.py`), et depuis la 1.55, il retire
au démarrage ce que l'ancien lanceur laissait.

Une branche qui touche au build se valide avant l'étiquette : `release.yml`
lancé à la main sur cette branche, `publier` décoché, construit et éprouve
les 4 binaires sans rien publier.

```bash
gh workflow run release.yml --ref ma-branche -f tag=essai -f publier=false
```

### Déploiement en une commande : `deploy.py`

Ce dossier de travail est un clone du dépôt GitHub. `deploy.py` y lance les
20 suites de tests et `ruff`, commit, pousse sur `main` et, avec `--new-tag`,
pose le tag `v<VERSION>` qui déclenche `release.yml`, dont il suit le build.

```bash
python deploy.py -m "mon correctif"            # tests + push, pas de release
python deploy.py -m "..." --new-tag            # tests + push + tag v<VERSION> + suivi du build
python deploy.py -m "..." --dry-run            # voir le diff sans rien pousser
```

- La version a une **source unique**, la constante `VERSION` de
  `lidar2map.py` : `--new-tag` en dérive le tag et refuse toute autre valeur.
- `deploy.py` refuse de partir si la branche n'est pas `main`, si `origin`
  n'est pas le dépôt officiel ou si `HEAD` diffère de `origin/main` (commit
  poussé ailleurs, par exemple une PR fusionnée : `git pull` d'abord).
- Seuls les fichiers déjà suivis partent. Un fichier nouveau non ignoré bloque
  le déploiement : l'ajouter (`git add`) ou l'ignorer (`.gitignore`, ou
  `.git/info/exclude` pour un fichier personnel).

Sous Mac/Linux : `python3 deploy.py ...` ou `./deploy.py ...` (shebang
`#!/usr/bin/env python3`, `chmod +x deploy.py` la première fois).

### Build local

Les scripts `lidar2map_*_build.*` servent à itérer et déboguer sur sa propre
plateforme. Ne jamais publier un build local comme asset : dérive de la
machine (versions des dépendances) et un seul OS. `release.yml` reste la
source de vérité des binaires distribués.

L'icône officielle `lidar2map_icon.png` est utilisée par les builds Windows et
macOS et reste incluse dans l'archive Linux pour les lanceurs de bureau.

---

## 7. Lancer l'application

### Prérequis pour le script Python direct

| OS      | Prérequis |
|---------|-----------|
| Windows | Python 3.12 |
| macOS   | Python 3.12 |
| Linux   | `sudo apt install python3.12 python3.12-venv` |

### Script Python direct (mode développement)

```bash
python3.12 lidar2map.py            # ouvre la GUI
python3.12 lidar2map.py --help     # liste des modes CLI
python3.12 lidar2map.py --ignlidar --help   # aide d'un mode précis
```

Premier lancement : crée `~/.lidar2map/venv` et installe les dépendances critiques.
Lancements suivants : re-exec direct dans le venv (~1 s).

### Application buildée — macOS (ou Linux) à distance, en SSH

Le GUI étant une page web, VNC n'est plus nécessaire. Sur la machine distante,
lancer le serveur sans navigateur ni icône (pas de session graphique en SSH),
puis ouvrir un tunnel depuis le poste local :

```bash
# Sur la machine distante, depuis SSH :
~/Downloads/dist/LIDAR2MAP.app/Contents/MacOS/lidar2map --serve-gui --no-browser --no-tray

# Sur le poste local :
ssh -N -L 8766:127.0.0.1:8766 utilisateur@machine-distante
# puis ouvrir http://127.0.0.1:8766/ dans le navigateur local
```

Le tunnel arrive sur `127.0.0.1` côté distant avec `Host: 127.0.0.1:8766` :
les contrôles de provenance de `_serve_web.py` l'acceptent sans
`--trusted-host`.

### Zoom dans la GUI

| Action | Raccourci |
|--------|-----------|
| Zoom in/out | Ctrl + molette |
| Réinitialiser | Ctrl + 0 |

---

## 8. Désinstaller

```bash
python3.12 lidar2map.py --desinstaller
```

Supprime : venv, osmosis, JRE et, s'il en reste, l'ancienne extraction d'un
lanceur ≤ 1.54.
Ne supprime pas : le script, le dossier du programme, le `.app`.

Après désinstallation, relancer le script repart de zéro (bootstrap complet).
Utile pour vérifier une installation propre ou libérer de l'espace disque.

---

## 9. Dépannage

### Premier réflexe : `--smoketest`

Avant de chercher l'origine d'un bug, faire tourner les 5 modes sur une
zone tampon :

```bash
lidar2map.exe --smoketest   # ou python lidar2map.py --smoketest
```

Si les 5 passent, le squelette est sain — le problème est probablement
dans les arguments ou la zone du run qui pose souci. Si un mode précis
échoue, c'est par là qu'il faut creuser.

### Build : `osmium absent — pip install osmium` au runtime du bundle

Cas observé sur Windows : la wheel osmium vendor ses DLL via `delvewheel`
dans `osmium.libs/` (sibling) avec suffixe de hash. PyInstaller dédupliquait
`msvcp140-<hash>.dll` contre `msvcp140.dll` système → DLL absente au
runtime → `ImportError: DLL load failed while importing _osmium`.

Résolu : `lidar2map_win.spec` utilise désormais `collect_all("osmium")` (pour
les `.py` du package) ET force la copie complète de `osmium.libs/` (pour
les DLL hashées). `lidar2map_mac.spec` a le même bloc défensif (no-op
sur macOS où delocate met les dylibs dans `osmium/.dylibs/` inside).

### `--formats-image jpeg` → 0 tuiles téléchargées, 0 erreur

Cas observé : `--ignraster --couche planign --formats-image jpeg` →
toutes tuiles « absentes », MBTiles vide. Le serveur IGN renvoyait
`HTTP 400 — Format image/jpeg unknown` pour la couche `planign` (servie
uniquement en PNG par IGN).

Résolu : `img_fmt` reste sur le format natif de la couche (PNG pour
planign, JPEG pour ortho/scan). `--formats-image` ne contrôle plus que
le re-encodage **côté client** dans le MBTiles. Plus de 400 du serveur.

### Build Windows : `too many values to unpack`

Les `a_detect.binaries` / `a_detect.datas` (TOC 3-tuples) ne peuvent pas être
passés en entrée d'une nouvelle `Analysis` (attend des 2-tuples).
Fusion correcte : après les deux analyses, via `a.binaries += a_detect.binaries`.

### Build Windows : `ModuleNotFoundError: No module named 'sqlite3'`

Résolu par les 2 passes PyInstaller — la passe 1 analyse `lidar2map.py`
et détecte automatiquement `sqlite3`, `ssl`, `xml`, `urllib`, etc.

### Fichiers créés à l'intérieur du .app (macOS)

Le dossier du programme (`_runtime_paths.dossier_programme`) est calculé en
remontant depuis `Contents/MacOS/` jusqu'au dossier parent du `.app`.
Jusqu'à la 1.53, les fichiers utilisateur
(Projets/, logs/, cache/) y étaient créés, à côté du `.app`. Depuis la 1.54,
ils vont dans `~/Library/Application Support/lidar2map-data/` (état) et
`~/Documents/lidar2map/` (sorties), jamais dans le `.app` ; ce dossier ne sert
plus qu'à reprendre l'état d'une version antérieure.

### PermissionError [Errno 13] ou slice is not valid mach-o (macOS)

L'archive a été extraite par un outil qui ne restitue ni les liens
symboliques, ni les bits d'exécution, ni les attributs du `.app` (le module
`zipfile` de Python, par exemple). Réextraire avec le Finder ou `ditto` :

```bash
ditto -x -k lidar2map-macos-arm64.zip .
```

### Ancienne extraction toujours présente (Windows)

La 1.55 la retire à son premier démarrage, sauf si une instance d'une
version ≤ 1.54 y tourne encore : le renommage échoue et le ménage attend le
lancement suivant. Pour forcer, arrêter toutes les instances de lidar2map,
puis supprimer `%LOCALAPPDATA%\lidar2map\` (jamais `lidar2map-data`, qui
contient les réglages et l'historique).

### Fichiers mbtiles vides (16 Ko, 0 tuiles)

Une exception transitoire dans le calcul SVF a produit un TIF partiellement écrit.
Le script supprime désormais le fichier partiel automatiquement et avertit
si 0 tuiles sont générées depuis une source > 1 Mo.

Pour relancer les morceaux concernés :
1. Supprimer les TIF `_svf_*_ombrage_tuilage_z18.tif` et `.mbtiles`
2. Passer `"termine": false` dans `manifeste.json` pour ces morceaux
3. Relancer

### Dalles LiDAR corrompues (VM)

Coupures TCP silencieuses sur VM → TIF tronqués.
Le script vérifie `Content-Length` et le header TIFF.
Les dalles corrompues sont automatiquement retéléchargées.

### python3.12-venv absent (Linux/Ubuntu)

```bash
sudo apt install python3.12-venv
```

### Gatekeeper bloque le .app (macOS)

Le script signe toujours le `.app` complet en dernier, après le correctif
libtiff du build Intel. Sans certificat Apple, cette signature reste ad hoc et
Gatekeeper demande une autorisation au premier téléchargement :

```bash
xattr -dr com.apple.quarantine LIDAR2MAP.app
```

Ou clic droit → Ouvrir → Ouvrir quand même.

Pour une release publique sans avertissement, définir
`LIDAR2MAP_CODESIGN_IDENTITY` et `LIDAR2MAP_NOTARY_PROFILE` avant le build. Le
workflow GitHub configure automatiquement ces variables lorsque les secrets
`MACOS_CERTIFICATE_BASE64`, `MACOS_CERTIFICATE_PASSWORD`,
`MACOS_KEYCHAIN_PASSWORD`, `MACOS_CODESIGN_IDENTITY`, `APPLE_ID`,
`APPLE_TEAM_ID` et `APPLE_APP_PASSWORD` sont présents.

### Spécifique Linux

- **`error: externally-managed-environment`** (PEP 668, Linux récent) : le
  bootstrap tente déjà `--break-system-packages` puis `--user`. Si tout
  échoue : créer un venv et relancer :
  ```bash
  python3 -m venv ~/.venv-lidar && source ~/.venv-lidar/bin/activate
  ```
- **Distribution sans `apt`** (Fedora, Arch, openSUSE) : le script ne sait
  pas installer GDAL automatiquement. Installer à la main puis relancer :
  ```bash
  sudo dnf install gdal                # Fedora
  sudo pacman -S gdal                  # Arch
  sudo zypper install gdal             # openSUSE
  ```
- **Machine sans affichage (SSH, serveur, service)** : `pystray` tente de se
  connecter au serveur X dès l'import (`Xlib.error.DisplayNameError`). Le
  serveur continue alors sans icône (« System tray icon unavailable ») ;
  `--no-tray` évite la tentative. Arrêt par `Ctrl+C` :
  ```bash
  python3 lidar2map.py --serve-gui --no-browser --no-tray
  ```
- **Pas d'icône dans la zone de notification** (GNOME sans zone de
  notification) : installer et activer l'extension AppIndicator
  (`gnome-shell-extension-appindicator` sur Debian/Ubuntu/Fedora), ou lancer
  avec `--serve-gui --no-tray` et arrêter par `Ctrl+C`.

### Spécifique macOS

- **`"java" cannot be opened because the developer cannot be verified`** :
  Gatekeeper bloque le JRE Temurin téléchargé automatiquement. Soit :
  - Préférences Système → Sécurité → Autoriser (sur le binaire bloqué).
  - **Ou** installer Java système (`brew install openjdk@21`) ; le script
    détecte un Java système valide et l'utilise au lieu du JRE téléchargé.
- **Apple Silicon, crash au démarrage / `mach-o, but wrong architecture`** :
  vérifier que `python3` est arm64 :
  ```bash
  python3 -c "import platform; print(platform.machine())"   # doit dire arm64
  ```
  Si non, soit lancer en arm64 forcé (`arch -arm64 python3 lidar2map.py ...`),
  soit réinstaller Python depuis python.org / Homebrew ARM.
