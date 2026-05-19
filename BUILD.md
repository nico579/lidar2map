# lidar2map — Documentation build & déploiement

## Table des matières

1. [Architecture](#1-architecture)
2. [Fichiers du projet](#2-fichiers-du-projet)
3. [Paramètres CLI spéciaux](#3-paramètres-cli-spéciaux)
4. [Préparer une machine de build](#4-préparer-une-machine-de-build)
5. [Builder l'application](#5-builder-lapplication)
6. [Mettre à jour le script sans rebuilder](#6-mettre-à-jour-le-script-sans-rebuilder)
7. [Lancer l'application](#7-lancer-lapplication)
8. [Désinstaller](#8-désinstaller)
9. [Dépannage](#9-dépannage)

---

## 1. Architecture

### Pattern launcher + bundle

```
Launcher (~5 Mo)                     ne change jamais
lidar2map.py compilé en onefile minimal (deps lourdes excluded)
bloc `--__lidar2map_inner__` en tête détecte le mode launcher vs inner
        |
        | lit
        v
lidar2map_bundle.zip (~300 Mo)       fichier SÉPARÉ (remplaçable)
  lidar2map(.exe)   binaire interne (entry point = _loader.py)
  _internal/
    lidar2map.py  <── remplaçable depuis Windows sans rebuild
    rasterio/
    PyQt6/
    osmosis/      bundlé si présent au moment du build
    jre/          bundlé si présent au moment du build
    ...
        |
        | extrait dans (1 seule fois, SHA détecte les mises à jour)
        v
Dossier d'installation
  macOS   ~/Library/Application Support/lidar2map/
  Windows %LOCALAPPDATA%\lidar2map\
  Linux   ~/.local/share/lidar2map/
```

### Emplacement du bundle selon l'OS

| OS      | Emplacement du zip |
|---------|--------------------|
| macOS   | `LIDAR2MAP.app/Contents/Resources/lidar2map_bundle.zip` |
| Windows | `lidar2map_bundle.zip` à côté de `lidar2map.exe` |
| Linux   | `lidar2map_bundle.zip` à côté du binaire |

### Comportement au lancement

- **Premier lancement** : calcul SHA + extraction avec progression (`20%... 40%...`) + lockfile anti double-clic
- **Lancements suivants** : comparaison mtime du zip (quelques ms) → démarrage immédiat si inchangé
- **Mise à jour** : mtime différent → recalcul SHA → ré-extraction si SHA différent
- **Double-clic simultané** : lockfile `.lidar2map_extracting` — la deuxième instance attend 60 s que la première termine

Le fichier `.bundle_sha` stocke le SHA256 ET le mtime du zip sur deux lignes.
Les anciens formats (une seule ligne) déclenchent une ré-extraction propre.

### Backends graphiques

| OS      | Backend  | Notes |
|---------|----------|-------|
| Windows | WebView2 | Natif Edge, préinstallé Win10+ |
| macOS   | PyQt6    | Forcé via `PYWEBVIEW_GUI=qt` — fonctionne en SSH+VNC |
| Linux   | PyQt6    | Seul backend viable via pip |

### Osmosis et JRE

- **Bundlés** si présents dans `~/.lidar2map/` au moment du build (via `setup_build_*.sh/ps1`)
- **Téléchargés automatiquement** au premier besoin si absents du bundle
- À préparer avant le build : `python3.12 lidar2map.py --telecharger-outils`

---

## 2. Fichiers du projet

### Fichiers source

| Fichier | Rôle |
|---------|------|
| `lidar2map.py` | Script principal — seul fichier à modifier pour les mises à jour |
| `_loader.py` | Entry point PyInstaller — chargé dans le binaire, ne change jamais |
| `update_app.py` | Met à jour `lidar2map.py` dans le bundle sans rebuild |
| `lidar2map_mac.spec` | Build interne onedir macOS ARM64 |
| `lidar2map_mac_launcher.spec` | Launcher `.app` macOS |
| `lidar2map_mac_build.sh` | Script de build macOS (3 étapes) |
| `lidar2map_win.spec` | Build interne onedir Windows (+ Linux) |
| `lidar2map_win_launcher.spec` | Launcher `.exe` Windows (+ Linux) |
| `lidar2map_win_build.ps1` | Script de build Windows (3 étapes) |
| `setup_build_mac.sh` | Setup machine de build macOS vierge (4 étapes) |
| `setup_build_windows.ps1` | Setup machine de build Windows vierge (4 étapes) |
| `setup_build_linux.sh` | Setup machine de build Linux vierge |

### Livrables à distribuer

| OS      | Livrables |
|---------|-----------|
| macOS   | `LIDAR2MAP.app` (zip dans `Contents/Resources/`) |
| Windows | `lidar2map.exe` + `lidar2map_bundle.zip` côte à côte |
| Linux   | `lidar2map` + `lidar2map_bundle.zip` côte à côte |

### `.gitignore` recommandé

```gitignore
dist/
dist_onedir/
build/*.zip
build/staging/
__pycache__/
*.pyc
.DS_Store
logs/
```

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

Installe : Pillow, pyproj, numpy, scipy, ijson, rasterio, fiona, certifi,
pywebview, PyQt6/WebEngine/qtpy (macOS/Linux), osmium, numba, laspy,
py7zr, mapbox-vector-tile.

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
| Bundle extrait (macOS) | `~/Library/Application Support/lidar2map/` |
| Bundle extrait (Windows) | `%LOCALAPPDATA%\lidar2map\` |
| Bundle extrait (Linux) | `~/.local/share/lidar2map/` |
| Venv Python | `~/.lidar2map/venv/` |
| osmosis | `~/.lidar2map/osmosis/` |
| JRE | `~/.lidar2map/jre/` |

Sur Windows et macOS, le dossier d'extraction est supprimé par le **launcher**
(avant le spawn de l'exe interne) pour éviter le verrouillage de fichiers.

Mécanisme depuis le `.app`/`.exe` : le launcher gère tout directement sans
re-spawn (bundle extrait + venv + osmosis + JRE), puis `sys.exit(0)`.
Pas de re-spawn = pas de boucle infinie possible.

```bash
python3.12 lidar2map.py --desinstaller
# ou depuis le .app/.exe
lidar2map.exe --desinstaller
```

### `--smoketest`

Vérifie que les 5 modes du pipeline fonctionnent end-to-end sur une petite
zone (Garéoult, rayon 1 km). Outputs dans `Projets/smoke/`. Caches dalles
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
scp lidar2map.py _loader.py update_app.py tagmapping-min.xml \
    lidar2map_mac.spec lidar2map_mac_launcher.spec \
    lidar2map_mac_build.sh setup_build_mac.sh \
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

# Récupérer les livrables depuis Windows
scp -r m1@<ip-vm>:~/Downloads/dist/LIDAR2MAP.app .
```

Étapes du script :
1. `pyinstaller lidar2map_mac.spec` (2 passes : détection deps + build loader)
2. `ditto -c -k` → `build/lidar2map_bundle.zip`
3. `pyinstaller lidar2map_mac_launcher.spec` → `dist/LIDAR2MAP.app` (~5 Mo)
4. Copie du zip dans `LIDAR2MAP.app/Contents/Resources/`

### Windows

```powershell
Unblock-File .\lidar2map_win_build.ps1
.\lidar2map_win_build.ps1
```

Livrables dans `dist\` : `lidar2map.exe` (~14 Mo) + `lidar2map_bundle.zip` (~235 Mo)

### Deux passes PyInstaller (macOS et Windows)

Depuis le passage à `_loader.py` comme entry point, `lidar2map.py` est un
fichier texte non analysé. Les specs lancent donc 2 analyses :

- **Passe 1** : `Analysis("lidar2map.py")` → détecte tous les imports
  (sqlite3, ssl, xml, urllib…)
- **Passe 2** : `Analysis("_loader.py")` → build réel
- Fusion des TOC **après** les deux analyses (pas en entrée — erreur "too many values")

---

## 6. Mettre à jour le script sans rebuilder

**Procédure normale** pour toute modification de `lidar2map.py`.
Aucun accès à la VM Mac nécessaire, aucun rebuild.

### Via update_app.py (recommandé)

```bash
# Placer lidar2map.py modifié dans le même dossier que update_app.py
python3 update_app.py   # macOS/Linux
python update_app.py    # Windows
```

Le script détecte l'OS, trouve le bon bundle, remplace `_internal/lidar2map.py`,
vérifie que le contenu a changé avant de modifier, et valide la syntaxe Python
(`compile()`) avant de toucher au zip — un fichier cassé ne sera jamais injecté.

Emplacements recherchés (premier trouvé) :
- macOS : `LIDAR2MAP.app/Contents/Resources/lidar2map_bundle.zip` puis `dist/LIDAR2MAP.app/...`
- Windows/Linux : `lidar2map_bundle.zip` à côté du script puis `dist/lidar2map_bundle.zip`

L'écriture est atomique (tmp + `os.replace`) — un Ctrl+C en cours ne laisse
jamais le zip dans un état partiel.

### Manuellement avec 7-Zip (Windows)

1. Ouvrir `lidar2map_bundle.zip` avec 7-Zip
2. Naviguer dans `_internal/`
3. Glisser-déposer le nouveau `lidar2map.py`
4. Enregistrer

Pour macOS : le zip est dans `LIDAR2MAP.app/Contents/Resources/`
Pour Windows/Linux : le zip est à côté du binaire

Note : le launcher détecte les mises à jour via la **mtime** du zip (puis SHA256
en confirmation). 7-Zip et `update_app.py` mettent tous deux à jour la mtime
au moment de l'écriture, donc la ré-extraction se déclenche automatiquement.

### Quand faut-il rebuilder ?

| Changement | Rebuild nécessaire ? |
|------------|----------------------|
| Modification de `lidar2map.py` | Non — remplacer dans le zip |
| Ajout d'une dépendance Python | Oui |
| Mise à jour de Python, PyInstaller | Oui |
| Changement de `_loader.py` | Oui |
| Mise à jour rasterio, PyQt6, etc. | Oui |

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

### Application buildée — macOS en SSH+VNC

```bash
# VNC doit être actif avant de lancer (indispensable pour la GUI Qt)
# Depuis SSH :
~/Downloads/dist/LIDAR2MAP.app/Contents/MacOS/lidar2map

# Ou via open (arrière-plan)
open ~/Downloads/dist/LIDAR2MAP.app
```

Sans VNC : `QApplication.primaryScreen()` retourne None → crash Qt.
Le backend Qt (PyQt6) est forcé via `PYWEBVIEW_GUI=qt` car le backend
Cocoa par défaut ne voit pas la session VNC depuis SSH.

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

Supprime : venv, osmosis, JRE, dossier d'extraction du bundle.
Ne supprime pas : le script, le `.app`/`.exe`, le zip.

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

`LIDAR2MAP_WORK_DIR` est calculé en remontant depuis `Contents/MacOS/` jusqu'au
dossier parent du `.app`. Les fichiers utilisateur (Projets/, logs/, cache/)
sont créés à côté du `.app`, jamais à l'intérieur.

### PermissionError [Errno 13] au premier lancement (macOS)

```bash
xattr -dr com.apple.quarantine ~/Library/Application\ Support/lidar2map/
chmod +x ~/Library/Application\ Support/lidar2map/lidar2map
```

### slice is not valid mach-o (macOS)

Le zip a été extrait avec `zipfile` au lieu de `ditto`. Le launcher utilise
`ditto -x -k` automatiquement sur macOS.

### _internal/ non supprimé par --desinstaller (Windows)

Résolu. Le launcher traite `--desinstaller` directement (avant tout spawn)
et supprime bundle extrait + venv + osmosis + JRE en une seule passe.
Si le problème persiste, supprimer manuellement `%LOCALAPPDATA%\lidar2map\`.

### Fichiers mbtiles vides (16 Ko, 0 tuiles)

Une exception transitoire dans le calcul SVF a produit un TIF partiellement écrit.
Le script supprime désormais le fichier partiel automatiquement et avertit
si 0 tuiles sont générées depuis une source > 1 Mo.

Pour relancer les morceaux concernés :
1. Supprimer les TIF `_svf_100m_ombrage_tuilage_z18.tif` et `.mbtiles`
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

```bash
xattr -dr com.apple.quarantine LIDAR2MAP.app
```

Ou clic droit → Ouvrir → Ouvrir quand même.
