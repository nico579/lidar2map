*[English](README.md) | **Français***

# lidar2map

**Cartes offline LiDAR archéologique multi-pays + IGN raster/vecteur + OSM pour Locus Map / OsmAnd / TwoNav**

Script Python autonome qui télécharge les données LiDAR publiques de plusieurs portails nationaux (IGN France, AHN Pays-Bas, swisstopo Suisse, Kartverket Norvège), calcule des ombrages spécialisés pour la prospection archéologique, et génère des cartes utilisables hors-ligne sur smartphone (formats MBTiles, RMAP, SQLiteDB, Mapsforge). Les cartes raster/vecteur IGN restent France-only.

![Même lieu : satellite, OpenStreetMap, puis relief LiDAR (SVF)](screenshots/hero.png)

*Même emprise sous trois regards : la photo satellite et la carte OSM ne montrent rien du micro-relief — le Sky-View Factor calculé depuis le LiDAR HD le révèle d'un coup.*

> ⚠️ **Statut** : usage personnel diffusé. Code testé intensivement sur Windows 10/11. Linux et macOS testés partiellement — cas connus + dépannage cross-OS dans la section *Dépannage* de [BUILD.md](BUILD.md). Les retours sont bienvenus via les [issues GitHub](https://github.com/nico579/lidar2map/issues).

---

## Pour qui ?

- **Archéologues amateurs** intéressés par la prospection LiDAR — l'outil fonctionne en France (IGN HD), Pays-Bas (AHN4), Suisse (swissALTI3D), Norvège (Nasjonal Høydemodell). Les calculs d'ombrages (multi, SVF, LRM, RRIM) sont identiques d'un pays à l'autre.
- **Randonneurs français** qui veulent des cartes IGN topo offline sur téléphone (Locus Map Pro, OsmAnd+) — les onglets IGN raster/vecteur restent France-only.
- **Prospecteurs paysage** qui combinent orthophotos historiques (1950-1995, France) et MNT pour repérer les vestiges humains avant la déprise agricole.
- **Spéléologues / explorateurs** qui ont besoin de fonds de carte précis dans des zones non couvertes par les apps grand public.

L'outil n'est **pas** destiné à la détection métallique. Le code respecte strictement les licences ouvertes (Etalab FR, CC BY 4.0 NO, CC-0 NL, BGDI CH).

## Ce que ça produit

À partir d'une commune, de coordonnées GPS, d'une bbox, d'un département ou d'une région entière :

- **Ombrages archéo** depuis le LiDAR national (résolution 0.5 m à 1 m selon source) :
  - Hillshade multidirectionnel (angle solaire 25° pour micro-relief)
  - SVF (Sky-View Factor) paramétrable — révèle fossés, restanques, enceintes.
    Convention `flux` (cos²γ, contraste à l'œil, défaut) ou `rvt` (1−sin γ,
    standard archéo Kokalj/Hesse / openness) ; distance d'horizon réglable
    (10–200 m, défaut 20 m) ; gamma d'affichage ; kernel sweep-horizon.
    Flags : `--svf-conv flux|rvt`, `--svf-dist M`, `--svf-gamma G`,
    `--svf-sweep` / `--no-svf-sweep` (ou le panneau SVF dans la GUI).
  - LRM (Local Relief Model) — supprime le relief naturel, garde les anomalies
  - RRIM (Red Relief Image Map) — composite couleur (pente + LRM)

  Sources LiDAR supportées (via flag `--provider <code>`) :
  - **France** (`fr-ign`, défaut) — IGN LiDAR HD, 0.5 m, couverture nationale
  - **Pays-Bas** (`nl-ahn`) — AHN4, 0.5 m, couverture nationale
  - **Suisse** (`ch-swisstopo`) — swissALTI3D, 0.5 m, couverture nationale
  - **Norvège** (`no-kartverket`) — Nasjonal Høydemodell, 1 m, couverture nationale

- **Cartes raster IGN** *(France uniquement)* : Plan IGN, Orthophotos (actuelles + historiques 1950, 1965, 1980), État-Major XIXᵉ, Pléiades satellite, IRC, etc.

- **Cartes vectorielles** : OSM Mapsforge `.map` (international, via Geofabrik) ou IGN BD TOPO *(France uniquement)*

- **Sorties** : MBTiles (universel), RMAP (CompeGPS / TwoNav), SQLiteDB (format RMaps — Locus Map / OsmAnd), Mapsforge `.map` (OsmAnd / Locus)

---

## Installation et utilisation

Deux façons d'utiliser lidar2map :

| | **A. Script Python** | **B. Exécutable autonome** |
|---|---|---|
| **Prérequis** | Python 3.12 | Aucun |
| **Première install** | ~5 min (bootstrap deps) | Aucun |
| **Mises à jour** | `git pull` + relance | Patcher les 3 binaires existants sur la release GitHub en une commande : `python update_app.py --release` (voir [`update_app.py`](update_app.py)) |
| **Distribuable** | Non — chaque utilisateur installe Python | Oui — `.exe` / `.app` / binaire Linux + bundle zip côte à côte |
| **Idéal pour** | dev / Linux / contribuer au code | utilisateur final / Windows / distribuer |

### A. Script Python

Au premier lancement, le script crée `~/.lidar2map/venv` et y installe les dépendances critiques (Pillow, pyproj, numpy, rasterio, pywebview + PyQt6/QtWebEngine…). Téléchargement de GDAL (Windows), du JRE Temurin 21 et d'osmosis à la demande. ~400 Mo total, **une seule fois**.

#### Windows 10+

1. Installer [Python 3.12+](https://www.python.org/downloads/)
2. Récupérer le code :
   ```powershell
   git clone https://github.com/nico579/lidar2map
   cd lidar2map
   python lidar2map.py
   ```

#### macOS 11+

```bash
brew install python@3.12
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

#### Linux (Debian / Ubuntu)

```bash
sudo apt install python3.12 python3.12-venv git
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

Le script demandera l'autorisation d'installer GDAL via `sudo apt install gdal-bin`.

Résolution de problèmes : section *Dépannage* de [BUILD.md](BUILD.md) (incluant les cas spécifiques Linux/macOS : PEP 668, Qt distro packages, Wayland, Gatekeeper sur le JRE…).

### B. Exécutable autonome

Pas de Python à installer côté utilisateur final. Le livrable contient son propre runtime (Python embarqué, deps, JRE, osmosis).

#### 1. Obtenir le livrable

**Option a — Télécharger depuis [Releases](https://github.com/nico579/lidar2map/releases)** (si la version est publiée pour ta plateforme) :

| OS | Archive | Extraire avec |
|----|---------|---------------|
| Windows 10/11 (x86_64) | `lidar2map-windows-x86_64.zip` | `Expand-Archive` (PowerShell) ou double-clic |
| Linux Ubuntu 24.04+ (x86_64) | `lidar2map-linux-x86_64.tar.gz` | `tar xzf` |
| macOS 12+ (Apple Silicon) | `lidar2map-macos-arm64.zip` | `unzip` puis `xattr -dr com.apple.quarantine LIDAR2MAP.app` |

L'archive s'extrait en un dossier `lidar2map-<os>-x86_64/` contenant le binaire et son `lidar2map_bundle.zip` côte à côte. Aucune installation système.

**Option b — Builder soi-même.** Deux scripts par plateforme : un setup machine (à faire **une fois**) puis un build (à relancer à chaque mise à jour de `lidar2map.py`).

##### Windows

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
.\setup_build_windows.ps1     # 1. Setup : Python 3.12, deps, JRE, osmosis, PyInstaller
.\lidar2map_win_build.ps1     # 2. Build : 3 etapes -> dist\lidar2map.exe + dist\lidar2map_bundle.zip
```

##### macOS (Apple Silicon)

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_mac.sh       # 1. Setup
bash lidar2map_mac_build.sh   # 2. Build -> dist/LIDAR2MAP.app
```

##### Linux (Ubuntu / Debian)

Linux réutilise les specs Windows (`_win.spec` produit un ELF sous Linux, le nom est trompeur).

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_linux.sh       # 1. Setup
bash lidar2map_linux_build.sh   # 2. Build -> dist/lidar2map + dist/lidar2map_bundle.zip
```

Prérequis : `sudo apt install zip` si absent. Le binaire produit dépend de la libc de la machine de build (build sur Ubuntu 22.04 → tourne sur Ubuntu ≥ 22.04 / Debian 12+).

Documentation complète du build (architecture du bundle, mise à jour sans rebuild, dépannage) : **[BUILD.md](BUILD.md)**.

#### 2. Lancer le livrable

| OS | Commande |
|----|----------|
| Windows | Double-clic sur `lidar2map.exe` (ou dans un terminal pour voir le log) |
| Linux | `chmod +x lidar2map && ./lidar2map` dans le dossier extrait |
| macOS | Double-clic sur `LIDAR2MAP.app`. Premier lancement bloqué par Gatekeeper : `xattr -dr com.apple.quarantine LIDAR2MAP.app` puis double-clic |
| Linux | `chmod +x lidar2map && ./lidar2map` |

Le premier lancement extrait le bundle (~30-60 s, une fois — il contient Qt) dans :
- Windows : `%LOCALAPPDATA%\lidar2map\`
- macOS : `~/Library/Application Support/lidar2map/`
- Linux : `~/.local/share/lidar2map/`

Désinstallation propre : `lidar2map(.exe) --desinstaller`.

---

## Utilisation

Deux modes, sélectionnés automatiquement selon les arguments (même logique que
le projet jumeau [gpxsolar](https://github.com/nico579/gpxsolar)) :

- **Sans argument → interface graphique** (pywebview / Qt). Mode courant.
- **Avec arguments → calcul en ligne de commande** (headless, sans fenêtre).
  Pratique pour scripter, lancer sur un serveur, ou reproduire un rendu précis.

Tout ce qui suit vaut pour le binaire comme pour le script — remplacez simplement
`python lidar2map.py` par `lidar2map.exe` (Windows), `./lidar2map` (Linux) ou
`LIDAR2MAP.app` (macOS).

### Exemples en ligne de commande

> Les options ci-dessous sont en anglais. Les anciens noms français restent acceptés comme alias, les anciennes commandes continuent donc de fonctionner.

**Ombrage SVF + carte topo IGN sur une commune (zone 1 km² autour de Garéoult, France) :**
```bash
python lidar2map.py --lidar --zone-city Gareoult --zone-radius 1 \
    --shadings multi svf --file-formats mbtiles --yes
```

**Ombrages sur Amsterdam (Pays-Bas, AHN4) :**
```bash
python lidar2map.py --provider nl-ahn --lidar --download \
    --zone-bbox 120000,486000,122000,488000 --zone-name amsterdam \
    --shadings multi --file-formats mbtiles --yes
```

**Ombrages sur Genève (Suisse, swissALTI3D) :**
```bash
python lidar2map.py --provider ch-swisstopo --lidar --download \
    --zone-city Geneve --zone-radius 1 \
    --shadings svf --file-formats mbtiles --yes
```

**Ombrages sur Oslo (Norvège, Kartverket) :**
```bash
python lidar2map.py --provider no-kartverket --lidar --download \
    --zone-city Oslo --zone-radius 1 \
    --shadings multi --file-formats mbtiles --yes
```

**Orthophoto historique 1950-1965 sur une zone de chasse archéo :**
```bash
python lidar2map.py --raster --zone-bbox 6.0,43.3,6.1,43.4 \
    --layer ortho_1950 --zoom-min 14 --zoom-max 18 --yes
```

**Carte OSM vectorielle (.map Mapsforge) pour Locus, département entier :**
```bash
python lidar2map.py --osm --zone-department 83 --file-formats map --yes
```

**Région entière (`--zone-region`) — disponible pour tous les modes :**
```bash
# OSM : une seule carte pour toute la région, sans re-découpe
# (le PBF Geofabrik EST déjà régional — bien plus rapide qu'une boucle par département)
python lidar2map.py --osm --zone-region provence-alpes-cote-d-azur --yes

# IGN vecteur : chemins/itinéraires de toute la région en GeoJSON + carte .map Locus
python lidar2map.py --vector --zone-region provence-alpes-cote-d-azur \
    --layer chemins --file-formats gz map --yes
```
Le slug est celui de [Geofabrik France](https://download.geofabrik.de/europe/france.html) (anciennes régions : `provence-alpes-cote-d-azur`, `bretagne`, `corse`, `rhone-alpes`…). En OSM la région est traitée d'un bloc (le fichier Geofabrik est déjà régional, aucun géocodage de département) ; pour les modes raster/vecteur/lidar la zone est la bbox englobant tous les départements de la région. Un slug inconnu liste les régions disponibles.

**Carte IGN BD TOPO (routes + bâtiments) en GeoJSON compressé + carte .map Mapsforge :**
```bash
python lidar2map.py --vector --zone-department 83 \
    --layer routes batiments --file-formats gz map --yes
```
Le format `map` convertit le GeoJSON IGN en carte Mapsforge `.map` (lisible Locus Map / OsmAnd).

## Providers LiDAR — ajouter un pays

L'abstraction provider permet d'ajouter une source LiDAR nationale sans toucher au cœur du pipeline. Chaque provider vit dans `providers/<code>.py` (~50-200 lignes) et expose :

```python
NAME, CODE, COUNTRY, LICENSE          # métadonnées
CRS_NATIF, RESOLUTION_M, DALLE_KM     # géométrie
discover_dalles(bbox_wgs, bbox_natif, cache)  # → {nom: url}
# + helpers : dalle_filename, dalle_url, subdir_from_name, dalles_pour_bbox
```

Le pipeline en aval (SVF, ombrages, warp EPSG:3857, MBTiles) est provider-agnostique : il consomme les GeoTIFF retournés par `discover_dalles`, peu importe le CRS natif ou le format d'index utilisé en amont.

| Code | Pays | CRS natif | Résolution | Paradigme API |
|---|---|---|---|---|
| `fr-ign` | France | EPSG:2154 (Lambert-93) | 0.5 m | TMS vectoriel PBF + WMS GetMap |
| `nl-ahn` | Pays-Bas | EPSG:28992 (RD New) | 0.5 m | ATOM feed + JSON FeatureCollection |
| `ch-swisstopo` | Suisse | EPSG:2056 (CH1903+/LV95) | 0.5 m | STAC API REST |
| `no-kartverket` | Norvège | EPSG:25833 (UTM33N) | 1 m | ArcGIS ImageServer exportImage |

Sélection : flag `--provider <code>` (CLI), variable d'env `LIDAR2MAP_PROVIDER`, ou dropdown en haut de la GUI.

Pour ajouter un 5e pays (ex. UK Environment Agency, Espagne PNOA-LiDAR, Italie PNRR) : copier le provider le plus proche en paradigme et adapter URLs/CRS/format de nommage. Le 1er provider abouti prend ~½ journée, les suivants ~1-2h chacun.

## Fonctionnalités principales

- **Auto-bootstrap** : aucune dépendance pré-installée requise. Le script télécharge à la demande Python deps (Pillow, pyproj, numpy, scipy), GDAL (Windows) ou demande l'installation système (Linux/macOS), JRE Temurin 21, osmosis, mapwriter.
- **Streaming mémoire** : traitement département-scale sans saturer la RAM (ijson, rasterio windowed reads, génération MBTiles tuile par tuile).
- **Cancellation propre** : `Ctrl+C` une fois → arrêt après le morceau en cours. `Ctrl+C` deux fois → arrêt immédiat.
- **Reprise après interruption** : la même commande reprend où elle s'est arrêtée, via un manifeste `.json` qui suit les morceaux terminés.
- **Découpage à priori** : pour les grandes zones, découper en grille N×N **ou en carrés de ~K km** (`--split-radius`, taille de chunk bornée — recommandé à l'échelle nationale) — utile pour ne pas avoir à régénérer la zone entière en cas de plantage. Nettoyage disque par morceau (`--cleanup`) et garde-fou d'espace libre (`--min-free-gb`) pour les très grandes couvertures.
- **Historique crash-safe** : chaque exécution est enregistrée *au démarrage* (statut "en cours") puis finalisée en "ok" ou "ko". Un crash dur (kill -9, panne) laisse l'entrée visible dans l'UI — la trace est conservée pour debug.
- **Multi-provider LiDAR** : abstraction `providers/<code>.py` permettant de plugger n'importe quelle source LiDAR. Providers fournis : **FR** (IGN), **NL** (AHN), **CH** (swisstopo), **NO** (Kartverket), **DE** (Bavière, NRW, Basse-Saxe), **AT** (Tyrol, Osttirol), **US** (3DEP 1 m, sans compte) — couvrant des paradigmes d'API variés (TMS PBF, JSON FeatureCollection, STAC, ArcGIS ImageServer, Metalink/`index.json`, **WCS `GetCoverage` par dalle**). Ajout d'un pays = ~100-150 lignes dans un nouveau fichier provider (voir *Couverture & sources évaluées* plus bas).
- **GUI interactive** : 6 onglets (LiDAR, IGN raster, IGN vecteur, OSM, Fusion, Découpage), sélecteur de provider en haut du formulaire (onglets IGN Raster/Vecteur masqués automatiquement pour les providers non-FR), historique des 50 dernières commandes avec badges de statut, validation des paramètres, log live, modal d'erreur.
- **Cartes orthophotos historiques** : combo unique pour l'archéo — SVF 2024 (LiDAR actuel) + ortho 1950 (avant déprise) → révèle les structures encore lisibles 70 ans après.

## Couverture LiDAR & sources évaluées

🗺️ **[Carte de couverture interactive](coverage.geojson)** — rendue directement par GitHub (clique sur le fichier). Glissable aussi dans [geojson.io](https://geojson.io) / QGIS pour tester un point.

**Légende** — la couleur ↔ le code `--provider` (= l'entrée dans le sélecteur de provider de la GUI) :

| Couleur | `--provider` | Zone |
|:-:|---|---|
| 🟦 | `fr-ign` | France métropolitaine |
| 🟩 | `nl-ahn` | Pays-Bas |
| 🟥 | `ch-swisstopo` | Suisse |
| 🟪 | `no-kartverket` | Norvège |
| 🟧 | `de-bayern` | Allemagne — Bavière |
| 🟧 | `de-nrw` | Allemagne — Rhénanie-du-Nord-Westphalie |
| 🟧 | `de-niedersachsen` | Allemagne — Basse-Saxe |
| 🟨 | `at-tirol` · `at-osttirol` | Autriche — Tyrol + Osttirol |

Au clic sur une zone, GitHub affiche son `NAME` (celui de la GUI) et son/ses code(s). La carte est régénérée par `coverage_map.py`, qui lit ces noms depuis `providers/*.py` — donc carte et GUI ne peuvent pas diverger.

**🇺🇸 USA** : supportée — 3DEP 1 m via `us-tnm` (sans compte, tuiles S3 directes) ou `us-3dep` (via OpenTopography, clé gratuite). **Absente de la carte** ci-dessus car la couverture 3DEP 1 m est **par projet** (pas tout le territoire) : un polygone « USA » sur-revendiquerait. Vérifie ta zone sur le [TNM Downloader](https://apps.nationalmap.gov/downloader/). NB : les tuiles 1 m USGS font 10×10 km (~150–300 Mo) — gros volume pour une petite zone archéo.

Un provider s'intègre proprement si la source expose des **tuiles déterministes**
(URL par tuile, ~1 km) **ou un WCS** (`GetCoverage` par bbox). Les sources livrées
en **gros blocs** (provinces, feuilles 20–50 km), par **formulaire/email**, en
**WMS seul** (rendu, pas d'altitude brute) ou en **ASC sans CRS** ne collent pas
encore au modèle streamé 1 km — il manquerait une capacité « gros bloc » (download
d'un zip volumineux + lecture par fenêtre), pas encore implémentée.

Sources évaluées **non retenues** à ce stade (documenté pour éviter de re-creuser) :

| Source | Raison |
|---|---|
| DE — BKG DGM1 national | payant (≥ 8 000 €) |
| DE — Vorarlberg | WMS seul (pas d'altitude brute) |
| AT — BEV national | tuiles 50 km via portail |
| ES — CNIG MDT02 | 2 m (trop grossier) + feuilles MTN50 (gros blocs) |
| BE — Wallonie | 0,5 m mais blocs provinciaux ~14 Go, pas de WCS |
| IT — Val d'Aoste / régions | formulaire de portail |
| IT — Tyrol du Sud | 0,5 m zones bâties seulement / 2,5 m ailleurs |
| SI — Slovénie (ARSO) | URLs propres mais ASC sans CRS + index par bloc |

D'autres Länder allemands (Bade-Wurtemberg, Saxe, Hesse…) sont **ajoutables** sur le même modèle.

## Captures d'écran

### Interface graphique

Six onglets pour piloter LiDAR, IGN raster/vecteur, OSM, fusion et découpage.

| LiDAR HD (ombrages archéo) | IGN raster (Plan / ortho / historique) | IGN vecteur (BD TOPO) |
|---|---|---|
| ![Onglet LiDAR](screenshots/GUI/IGN_Lidar.PNG) | ![Onglet IGN raster](screenshots/GUI/IGN_Raster.PNG) | ![Onglet IGN vecteur](screenshots/GUI/IGN_Vectoriel.PNG) |

| OSM vectoriel (Mapsforge) | Fusion vecteur | Découpage raster |
|---|---|---|
| ![Onglet OSM](screenshots/GUI/OSM_Vectoriel.PNG) | ![Onglet Fusion](screenshots/GUI/Fusion_Vectoriel.PNG) | ![Onglet Découpage](screenshots/GUI/Decoupage_Raster.PNG) |

### Rendu sur Locus Map

Ombrages LiDAR archéo affichés en superposition sur le terrain dans Locus Map.

| SVF (Sky-View Factor) | Multi-ombrages superposés |
|---|---|
| ![SVF dans Locus Map](screenshots/LIDAR_Samples/Svf_LocusMap.jpg) | ![Multi-ombrages dans Locus Map](screenshots/LIDAR_Samples/Multi_LocusMap.jpg) |

### Ce que le SVF révèle — même zone, trois sources

Sous le couvert végétal, la photo aérienne et OSM ne montrent rien. Le SVF
LiDAR fait apparaître les restanques (terrasses en pierre sèche) et les
chemins anciens, invisibles vus du ciel.

| Photo satellite | OSM | SVF (LiDAR HD) |
|---|---|---|
| ![Vue satellite](screenshots/LIDAR_Samples/sat.png) | ![Vue OSM](screenshots/LIDAR_Samples/osm.png) | ![Vue SVF](screenshots/LIDAR_Samples/svf.png) |
| Garrigue opaque | Quasi aucun détail | Restanques + chemins nets |

#### Reproduire ce rendu

Le SVF d'en-tête et du triptyque ci-dessus (secteur de Rougiers, 83) a été calculé avec :

```bash
python lidar2map.py \
  --zone-gps <lat> <lon> --zone-radius 1 --zone-name hero \
  --lidar --download --workers 8 \
  --shadings svf --shading-elevation 25 \
  --svf-conv rvt --svf-dist 20 --svf-gamma 0.8 --svf-sweep \
  --file-formats mbtiles --zoom-min 8 --zoom-max 18 \
  --image-format jpeg --image-quality 85 --yes
```

Remplace `<lat> <lon>` par ta propre zone ; les paramètres SVF ci-dessus sont
ceux du visuel. Les coordonnées exactes d'un micro-relief ne sont volontairement
pas diffusées (déontologie : ne pas guider vers un vestige précis — cf. le
disclaimer anti-détection ci-dessous).

## Documentation

- **README de l'utilisateur** : ce fichier
- **Build & déploiement** : [BUILD.md](BUILD.md) — architecture du bundle, scripts de build par OS, mise à jour sans rebuild, dépannage (incluant cas spécifiques Linux et macOS)
- **Aide intégrée** : `python lidar2map.py --help` (LiDAR), `--raster --help` (raster), `--vector --help` (vecteur), `--osm --help`, `--merge --help`

## Licence

Code distribué sous **GNU General Public License v3.0** — voir [LICENSE](LICENSE).

Vous êtes libre d'utiliser, modifier et redistribuer ce logiciel selon les termes de la GPL v3. En particulier : si vous redistribuez une version modifiée, vous devez fournir le code source modifié sous la même licence.

## Auteur

Conçu et architecturé par **Nicolas Martin** ([@nico579](https://github.com/nico579)). Code développé avec l'assistance de Claude (Anthropic) comme outil de développement.

## Remerciements

Données utilisées :
- **IGN** (Institut national de l'information géographique et forestière) — LiDAR HD, BD ORTHO (incluant les versions historiques 1950-1995), BD TOPO, sous licence Etalab 2.0
- **OpenStreetMap** — données vectorielles sous licence ODbL, distribuées par Geofabrik
- **Apache JMapsforge / mapsforge-map-writer** — moteur de rendu vectoriel offline

Outils intégrés : GDAL, osmosis, py7zr, pyproj, numpy, scipy, Pillow, ijson, pywebview.
