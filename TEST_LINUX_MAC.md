# Test lidar2map.py sur Mac et Linux — Procédure de validation

Document à suivre étape par étape. À chaque étape, **note ce qui marche, ce qui plante, et le message exact**.

---

## Avant de commencer

**Prérequis :**

- Python 3.8 minimum, **3.12+ recommandé**. Vérifier :
  ```
  python3 --version
  ```
  Si Python est en version 3.7 ou plus ancien, installer une version récente.

- **Mac uniquement** : Homebrew installé. Si non, suivre https://brew.sh/

- **Linux uniquement** : `apt` doit être disponible (Debian, Ubuntu, Mint, Pop!_OS, etc.). Pour Fedora/Arch/openSUSE le script fonctionne mais demande l'install GDAL manuellement.

**Espace disque** : prévoir ~2 Go libres (Python deps + GDAL + JRE + osmosis + données de test).

**Réseau** : le script télécharge des choses depuis IGN, GitHub, Adoptium, Geofabrik. Pas de proxy d'entreprise bloquant ces domaines.

---

## Étape 1 — Bootstrap minimal (CLI, sans réseau lourd)

Ouvre un terminal dans le dossier où tu as posé `lidar2map.py`. Lance :

```
python3 lidar2map.py --version
```

**Comportement attendu :**

- Au premier lancement, le script va installer ses dépendances pip (`Pillow`, `pyproj`, `numpy`, `scipy`, `ijson`). Ça peut prendre 1-3 minutes.
- À la fin, il affiche `lidar2map.py 1.x.x` (ou similaire) et termine sans erreur.

**Ce qui peut planter :**

| Message | Cause | Action |
|---|---|---|
| `error: externally-managed-environment` | PEP 668 (Linux récent) | Le script tente déjà `--break-system-packages` puis `--user`. Si ça échoue, créer un venv : `python3 -m venv ~/.venv-lidar && source ~/.venv-lidar/bin/activate` puis relancer |
| `ModuleNotFoundError: No module named 'pip'` | Python sans pip | `sudo apt install python3-pip` (Linux) ou réinstaller Python depuis python.org (Mac) |
| `Permission denied` sur le dossier `logs/` | Lancement depuis `/` ou `/usr` | Lancer depuis ton home : `cd ~ && python3 /chemin/vers/lidar2map.py --version` |

**À noter** : le dossier `logs/` créé doit être à côté de `lidar2map.py`, pas dans le `cwd`.

✅ **OK** si le script affiche sa version et quitte avec code 0 (`echo $?` retourne 0).

---

## Étape 2 — GDAL (CLI, premier vrai outil système)

Lance une commande qui n'a besoin que de `gdaldem` et `gdalbuildvrt` (pas de tuilage) :

```
python3 lidar2map.py --ignlidar --zone-ville Gareoult --zone-rayon 1 --ombrages multi --oui
```

**Comportement attendu :**

1. Géocodage de "Gareoult" via Nominatim (réseau)
2. Calcul de la grille (9 dalles)
3. Téléchargement des 9 dalles depuis IGN (~30 s sur connexion correcte)
4. **Si GDAL absent** : message demandant l'autorisation d'installer :
   - Linux : `sudo apt install -y gdal-bin` → répondre `o` puis taper le mot de passe
   - Mac : `brew install gdal` → répondre `o` (peut prendre 5-15 min)
5. Construction du VRT, calcul de l'ombrage `multi`, écriture du `.tif`
6. Message `Terminé !` à la fin

**Ce qui peut planter :**

| Message | Cause | Action |
|---|---|---|
| `Cette distribution Linux n'a pas apt` | Fedora/Arch/openSUSE | Suivre les instructions affichées (`sudo dnf install gdal`, etc.) puis relancer |
| `Homebrew absent` | Mac sans brew | Installer brew d'abord depuis brew.sh |
| `command not found: gdaldem` après install | PATH pas rafraîchi | Ouvrir un nouveau terminal |
| `ERROR 1: PROJ: ...` | proj.db incompatible | Noter le message exact et envoyer à Nicolas |
| Téléchargement IGN qui timeout | Serveur IGN lent ou IP bannie | Attendre 5 min et réessayer |

✅ **OK** si tu obtiens un fichier `~/Documents/lidar/Projets/gareoult/ign_lidar/gareoult_multi_ombrage.tif` (ou équivalent selon `--dossier`).

---

## Étape 3 — Pipeline complet (osmosis + JRE + tuilage)

```
python3 lidar2map.py --ignlidar --zone-ville Gareoult --zone-rayon 1 --ombrages svf --formats-fichier mbtiles --oui
```

**Comportement attendu :**

1. Réutilise les dalles téléchargées à l'étape 2 (sinon les retélécharge)
2. Calcul SVF (peut prendre 1-3 minutes — Numba JIT au premier appel)
3. Tuilage en MBTiles (~30 secondes)
4. Fichier `gareoult_svf_ombrage_z13-18.mbtiles` produit (~30 Mo)

**Ce qui peut planter :**

| Message | Cause | Action |
|---|---|---|
| `numba absent — SVF utilisera numpy` | Numba pas installé | Pas un blocage, juste plus lent. `pip install numba` pour accélérer |
| Crash silencieux pendant SVF | Mémoire insuffisante | Réduire `--zone-rayon` à 0.5 |
| Erreur PROJ_LIB / proj.db | Conflit GDAL système vs pyproj | Noter erreur exacte |

✅ **OK** si le `.mbtiles` est produit et fait > 1 Mo.

---

## Étape 4 — OSM (osmosis + JRE Adoptium)

```
python3 lidar2map.py --osm --zone-ville Gareoult --zone-rayon 1 --oui
```

**Comportement attendu :**

1. **Premier lancement uniquement** : téléchargement automatique de :
   - JRE Temurin 21 (~50 Mo) depuis adoptium.net (redirige vers GitHub)
   - osmosis (~25 Mo)
   - mapwriter (~3 Mo)
2. Téléchargement du PBF Geofabrik PACA (~400 Mo, peut prendre plusieurs minutes selon connexion)
3. osmosis filtre + génère le `.map`
4. Fichier `gareoult.map` produit (~20 Ko pour 1 km²)

**Ce qui peut planter :**

| Message | Cause | Action |
|---|---|---|
| `JRE Temurin : 403 Forbidden` | Adoptium API change | Installer Java système (`brew install openjdk@21` ou `sudo apt install default-jre`) puis relancer — le script utilisera le Java système |
| **Mac uniquement** : `"java" cannot be opened because the developer cannot be verified` | Gatekeeper bloque le binaire téléchargé | Aller dans Préférences Système > Sécurité > Autoriser. **Ou** : utiliser un Java installé via Homebrew |
| `osmosis exit code 1` | PBF corrompu | Supprimer le PBF dans `cache/osm_vecteur/` et relancer |
| `org.mapsforge` errors | Plugin mapwriter absent | Vérifier `~/.openstreetmap/osmosis/plugins/` contient `mapsforge-map-writer-X.jar` |

✅ **OK** si `gareoult.map` est produit et fait > 1 Ko.

---

## Étape 5 — GUI

```
python3 lidar2map.py
```

(sans aucun argument, pour ouvrir la GUI)

**Comportement attendu :**

- **Mac** : fenêtre Cocoa s'ouvre, identique à Windows
- **Linux** : pywebview installe automatiquement le backend Qt (`pywebview[qt]`). Si import échoue, le script affiche les paquets système à installer manuellement.

**Ce qui peut planter (Linux surtout) :**

| Message | Cause | Action |
|---|---|---|
| `No suitable backend found` | Qt absent | Installer paquets système :<br>**Debian/Ubuntu** : `sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine`<br>**Fedora** : `sudo dnf install python3-qt5 python3-qt5-webengine`<br>**Arch** : `sudo pacman -S python-pyqt5 python-pyqt5-webengine` |
| Fenêtre s'ouvre mais blanche | QtWebEngine ne charge pas | Lancer en mode debug : `QTWEBENGINE_CHROMIUM_FLAGS="--single-process" python3 lidar2map.py` |
| `Symbol lookup error` Qt sur Linux | Conflit Qt5 vs Qt6 | Désinstaller Qt6 ou utiliser un venv propre |
| **Mac M1/M2/M3** : crash au démarrage | Architecture mismatch | Vérifier que `python3` est bien arm64 : `python3 -c "import platform; print(platform.machine())"` doit dire `arm64` |

**À tester dans la GUI une fois ouverte :**

1. Cliquer sur "⏱ Historique" en haut → panneau s'ouvre à droite
2. Cliquer sur une entrée → les paramètres se remplissent (si tu as déjà fait des runs CLI)
3. Cliquer sur "🗑 Vider" → confirmation + historique vidé
4. Tester Ctrl+molette pour zoomer/dézoomer l'interface

✅ **OK** si la GUI s'ouvre, l'historique fonctionne, et le bouton "▶ Lancer" déclenche un run.

---

## Étape 6 — Test optionnel : département entier (BD TOPO bulk)

À ne tenter que si toutes les étapes précédentes passent **et** que tu as ~10 Go d'espace libre :

```
python3 lidar2map.py --ignvecteur --zone-departement 83 --couche routes --formats-fichier gz --oui
```

**Comportement attendu :**

- Téléchargement archive `.7z` BD TOPO (~450 Mo)
- Extraction GPKG (~2.7 Go)
- ogr2ogr extrait `troncon_de_route` → `.geojson` (300-800 Mo)
- Streaming via ijson → `.geojson.gz` (~100 Mo)
- ~6-8 minutes sur connexion correcte

**Ce qui peut planter :**

| Message | Cause | Action |
|---|---|---|
| `py7zr non installable` | Pip env exotique | `pip install py7zr` manuellement |
| OOM (out of memory) sur extraction | RAM < 4 Go | Pas testable sur cette machine, passer cette étape |
| Erreur ogr2ogr `Couldn't fetch requested layer` | Nom de couche incorrect | Vérifier que le nom de la couche existe dans le GPKG (lister via `ogrinfo file.gpkg`) |

✅ **OK** si le `.geojson.gz` est produit (~100 Mo pour le Var entier).

---

## Que faire en cas de problème

1. **Note précisément** la commande lancée et le message d'erreur **complet**
2. **Note le contexte** : OS exact (`uname -a` sur Mac/Linux), version Python (`python3 --version`), version pip (`pip3 --version`)
3. Cherche dans le dossier `logs/` à côté de `lidar2map.py` le fichier `.log` correspondant — il contient toute la sortie console
4. Envoie ces 3 infos à Nicolas

---

## Limites connues

- Sur **Apple Silicon (M1/M2/M3)**, certaines dépendances peuvent nécessiter Rosetta. Si erreurs `mach-o, but wrong architecture`, lancer Python via `arch -arm64 python3 lidar2map.py ...`
- Sur **Linux Wayland**, certaines fenêtres Qt peuvent avoir des artefacts d'affichage. Forcer X11 : `QT_QPA_PLATFORM=xcb python3 lidar2map.py`
- Le script n'a **pas été testé** sur FreeBSD, Alpine Linux, ou WSL2. Comportement non garanti.
