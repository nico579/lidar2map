# lidar2map

**Cartes offline LiDAR archéologique, IGN raster/vecteur et OSM pour Locus Map / OsmAnd / TwoNav**

Script Python autonome qui télécharge les données géographiques publiques de l'IGN (LiDAR HD, orthophotos, BD TOPO) et OpenStreetMap, calcule des ombrages spécialisés pour la prospection archéologique, et génère des cartes utilisables hors-ligne sur smartphone (formats MBTiles, RMAP, SQLiteDB, Mapsforge).

> ⚠️ **Statut** : usage personnel diffusé. Code testé intensivement sur Windows 10/11. Linux et macOS testés partiellement — voir [TEST_LINUX_MAC.md](TEST_LINUX_MAC.md). Les retours sont bienvenus via les [issues GitHub](https://github.com/nico579/lidar2map/issues).

---

## Pour qui ?

- **Randonneurs** qui veulent des cartes IGN topo offline sur leur téléphone (Locus Map Pro, OsmAnd+)
- **Archéologues amateurs** intéressés par la prospection LiDAR : restanques, chemins muletiers, glacières, charbonnières, voies anciennes
- **Prospecteurs paysage** qui combinent orthophotos historiques (1950-1995) et MNT pour repérer les vestiges humains avant la déprise agricole
- **Spéléologues / explorateurs** qui ont besoin de fonds de carte précis dans des zones non couvertes par les apps grand public

L'outil n'est **pas** destiné à la détection métallique. Le code respecte strictement les licences ouvertes (Etalab, ODbL).

## Ce que ça produit

À partir d'une commune, de coordonnées GPS, d'une bbox ou d'un département entier :

- **Ombrages archéo** depuis le LiDAR HD IGN (résolution 50 cm) :
  - Hillshade multidirectionnel (angle solaire 25° pour micro-relief)
  - SVF (Sky-View Factor) 20 m et 100 m — révèle fossés, restanques, enceintes
  - LRM (Local Relief Model) — supprime le relief naturel, garde les anomalies
  - RRIM (Red Relief Image Map) — composite couleur SVF + pente

- **Cartes raster IGN** : Plan IGN, Orthophotos (actuelles + historiques 1950, 1965, 1980), État-Major XIXᵉ, Pléiades satellite, IRC, etc.

- **Cartes vectorielles** : OSM (Mapsforge `.map`) ou IGN BD TOPO

- **Sorties** : MBTiles (universel), RMAP (Locus optimisé), SQLiteDB (TwoNav), Mapsforge `.map` (OsmAnd / Locus)

---

## Installation et utilisation

Deux façons d'utiliser lidar2map :

| | **A. Script Python** | **B. Exécutable autonome** |
|---|---|---|
| **Prérequis** | Python 3.12 | Aucun |
| **Première install** | ~5 min (bootstrap deps) | Aucun |
| **Mises à jour** | `git pull` + relance | Builder un nouveau livrable, ou remplacer `lidar2map.py` dans le zip via [`update_app.py`](update_app.py) |
| **Distribuable** | Non — chaque utilisateur installe Python | Oui — `.exe` / `.app` / binaire Linux + bundle zip côte à côte |
| **Idéal pour** | dev / Linux / contribuer au code | utilisateur final / Windows / distribuer |

### A. Script Python

Au premier lancement, le script crée `~/.lidar2map/venv` et y installe les dépendances critiques (Pillow, pyproj, numpy, rasterio, pywebview…). Téléchargement de GDAL (Windows), du JRE Temurin 21 et d'osmosis à la demande. ~150 Mo total, **une seule fois**.

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

Résolution de problèmes : [TEST_LINUX_MAC.md](TEST_LINUX_MAC.md).

### B. Exécutable autonome

Pas de Python à installer côté utilisateur final. Le livrable contient son propre runtime (Python embarqué, deps, JRE, osmosis).

#### 1. Obtenir le livrable

**Option a — Télécharger depuis [Releases](https://github.com/nico579/lidar2map/releases)** (si la version est publiée pour ta plateforme) :

| OS | Livrable |
|----|----------|
| Windows | `lidar2map.exe` + `lidar2map_bundle.zip` (à placer côte à côte) |
| macOS | `LIDAR2MAP.app` |
| Linux | `lidar2map` + `lidar2map_bundle.zip` (à placer côte à côte) |

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

Linux réutilise les specs Windows. Pas de script de build dédié — étape manuelle après le setup :

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_linux.sh
$HOME/.lidar2map/venv/bin/pyinstaller lidar2map_win.spec --clean --noconfirm
cd dist_onedir/lidar2map && zip -r ../../lidar2map_bundle.zip . && cd ../..
$HOME/.lidar2map/venv/bin/pyinstaller lidar2map_win_launcher.spec --clean --noconfirm
```

Documentation complète du build (architecture du bundle, mise à jour sans rebuild, dépannage) : **[BUILD.md](BUILD.md)**.

#### 2. Lancer le livrable

| OS | Commande |
|----|----------|
| Windows | Double-clic sur `lidar2map.exe` (ou dans un terminal pour voir le log) |
| macOS | Double-clic sur `LIDAR2MAP.app`. Premier lancement bloqué par Gatekeeper : `xattr -dr com.apple.quarantine LIDAR2MAP.app` puis double-clic |
| Linux | `chmod +x lidar2map && ./lidar2map` |

Le premier lancement extrait le bundle (~5-10 s, une fois) dans :
- Windows : `%LOCALAPPDATA%\lidar2map\`
- macOS : `~/Library/Application Support/lidar2map/`
- Linux : `~/.local/share/lidar2map/`

Désinstallation propre : `lidar2map(.exe) --desinstaller`.

---

## Exemples en ligne de commande

**Ombrage SVF + carte topo IGN sur une commune (zone 1 km² autour de Garéoult) :**
```bash
python lidar2map.py --ignlidar --zone-ville Gareoult --zone-rayon 1 \
    --ombrages multi svf --formats-fichier mbtiles --oui
```

**Orthophoto historique 1950-1965 sur une zone de chasse archéo :**
```bash
python lidar2map.py --ignraster --zone-bbox 6.0,43.3,6.1,43.4 \
    --couche ortho_1950 --zoom-min 14 --zoom-max 18 --oui
```

**Carte OSM vectorielle (.map Mapsforge) pour Locus, département entier :**
```bash
python lidar2map.py --osm --zone-departement 83 --formats-fichier map --oui
```

**Carte IGN BD TOPO (routes + bâtiments) en GeoJSON compressé :**
```bash
python lidar2map.py --ignvecteur --zone-departement 83 \
    --couche routes batiments --formats-fichier gz --oui
```

**Mode interactif (GUI) — sans aucun argument :**
```bash
python lidar2map.py
```

(Idem avec `lidar2map.exe` ou `LIDAR2MAP.app` pour l'exécutable autonome.)

## Fonctionnalités principales

- **Auto-bootstrap** : aucune dépendance pré-installée requise. Le script télécharge à la demande Python deps (Pillow, pyproj, numpy, scipy), GDAL (Windows) ou demande l'installation système (Linux/macOS), JRE Temurin 21, osmosis, mapwriter.
- **Streaming mémoire** : traitement département-scale sans saturer la RAM (ijson, rasterio windowed reads, génération MBTiles tuile par tuile).
- **Cancellation propre** : `Ctrl+C` une fois → arrêt après le morceau en cours. `Ctrl+C` deux fois → arrêt immédiat.
- **Reprise après interruption** : la même commande reprend où elle s'est arrêtée, via un manifeste `.json` qui suit les morceaux terminés.
- **Découpage à priori** : pour les grandes zones, découper en grille N×N — utile pour ne pas avoir à régénérer la zone entière en cas de plantage.
- **Historique crash-safe** : chaque exécution est enregistrée *au démarrage* (statut "en cours") puis finalisée en "ok" ou "ko". Un crash dur (kill -9, panne) laisse l'entrée visible dans l'UI — la trace est conservée pour debug.
- **GUI interactive** : 6 onglets (LiDAR, IGN raster, IGN vecteur, OSM, Fusion, Découpage), historique des 50 dernières commandes avec badges de statut, validation des paramètres, log live, modal d'erreur.
- **Cartes orthophotos historiques** : combo unique pour l'archéo — SVF 2024 (LiDAR actuel) + ortho 1950 (avant déprise) → révèle les structures encore lisibles 70 ans après.

## Captures d'écran

> _À ajouter : capture de la GUI, exemple de SVF dans Locus Map sur une zone à restanques, comparaison ortho 1950 vs 2024._

## Documentation

- **README de l'utilisateur** : ce fichier
- **Build & déploiement** : [BUILD.md](BUILD.md) — architecture du bundle, scripts de build par OS, mise à jour sans rebuild, dépannage
- **Procédure de test Linux/Mac** : [TEST_LINUX_MAC.md](TEST_LINUX_MAC.md)
- **Aide intégrée** : `python lidar2map.py --help` (LiDAR), `--ignraster --help` (raster), `--ignvecteur --help` (vecteur), `--osm --help`, `--fusionner --help`

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
