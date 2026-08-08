# Bien démarrer avec lidar2map

*[English](getting-started.md) | **Français** · [Index de la documentation](README.fr.md)*

Ce guide couvre l’installation, le premier lancement et l’usage quotidien de
l’interface graphique. Pour choisir un format et importer une carte sur le
téléphone, voir [Formats et applications mobiles](formats.fr.md). La compilation
et la publication de l’application sont documentées séparément dans
[BUILD.md](../BUILD.md).

## Choisir comment lancer lidar2map

L’application autonome est le choix normal pour l’utilisateur final. Elle
embarque son propre Python, ses dépendances, le runtime Java et osmosis, sans
les installer dans le système.

| | **Application autonome** | **Script Python** |
|---|---|---|
| Prérequis | Aucun en dehors d’un OS pris en charge | Python 3.12 |
| Première préparation | Aucune installation ; le runtime embarqué est extrait au premier lancement | Environ 5 minutes ; bootstrap automatique dans un environnement virtuel privé |
| Mise à jour | Télécharger et extraire la nouvelle release | `git pull`, puis relancer |
| Distribuable | Oui : lanceur/application et `lidar2map_bundle.zip` restent ensemble | Non : chaque ordinateur prépare son environnement Python |
| Recommandé pour | Utilisateur final et redistribution | Développement, usage Linux depuis les sources et contribution |

La publication ou le patch des archives autonomes relève de la maintenance.
Les scripts de compilation, l’architecture du bundle et le workflow release
de `update_app.py` sont décrits uniquement dans [BUILD.md](../BUILD.md).

## Installer l’application autonome

Téléchargez l’archive de votre plateforme depuis la
[page GitHub Releases](https://github.com/nico579/lidar2map/releases), puis
décompressez-la sans déplacer les fichiers à l’intérieur du dossier extrait.

| OS | Archive | Extraction |
|---|---|---|
| Windows 10/11, x86-64 | `lidar2map-windows-x86_64.zip` | Explorateur de fichiers ou `Expand-Archive` dans PowerShell |
| Ubuntu 24.04+, x86-64 | `lidar2map-linux-x86_64.tar.gz` | `tar xzf lidar2map-linux-x86_64.tar.gz` |
| macOS 12+, Apple Silicon | `lidar2map-macos-arm64.zip` | `unzip`, puis retirer la quarantaine comme indiqué plus bas si Gatekeeper bloque le premier lancement |
| macOS 12+, Intel | `lidar2map-macos-x86_64.zip` | Idem |

Le dossier extrait contient le lanceur (`lidar2map.exe`, `lidar2map` ou
`LIDAR2MAP.app`) et `lidar2map_bundle.zip` côte à côte. Ils doivent rester
ensemble. Rien n’est installé dans le système.

### Lancer l’application

| OS | Démarrage |
|---|---|
| Windows | Double-cliquer sur `lidar2map.exe`. Un lancement depuis un terminal affiche aussi le journal de démarrage. |
| Linux | Exécuter une fois `chmod +x lidar2map`, puis `./lidar2map` depuis le dossier extrait. |
| macOS | Double-cliquer sur `LIDAR2MAP.app`. Si Gatekeeper le bloque, exécuter `xattr -dr com.apple.quarantine LIDAR2MAP.app`, puis recommencer. |

Le premier lancement extrait une fois le bundle contenant Qt et prend en
général 30 à 60 secondes. Le runtime extrait est stocké dans :

- Windows : `%LOCALAPPDATA%\lidar2map\`
- macOS : `~/Library/Application Support/lidar2map/`
- Linux : `~/.local/share/lidar2map/`

Les lancements suivants réutilisent cette copie.

## Lancer le script Python

Au premier lancement, le script crée `~/.lidar2map/venv` et y installe les
dépendances critiques : Pillow, pyproj, numpy, rasterio, pywebview et
PyQt6/QtWebEngine. L’environnement Python système n’est pas modifié. Utilisez
`--bootstrap=none` si vous préférez gérer vous-même les dépendances.

Temurin 21 et osmosis sont téléchargés à la demande. Aucun GDAL système n’est
nécessaire, car les wheels rasterio embarquent le leur. Prévoir environ 400 Mo
pour cette préparation effectuée une seule fois.

### Windows 10+

1. Installer [Python 3.12 ou plus récent](https://www.python.org/downloads/).
2. Cloner puis lancer :

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
python lidar2map.py
```

### macOS 11+

```bash
brew install python@3.12
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

### Debian / Ubuntu

```bash
sudo apt install python3.12 python3.12-venv git
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

Les cas Linux/macOS tels que PEP 668, les paquets Qt de la distribution,
Wayland ou Gatekeeper sur le runtime Java sont traités dans la
[section Dépannage de BUILD.md](../BUILD.md#9-dépannage).

## Premier lancement et parcours graphique

Lancer lidar2map sans argument ouvre l’interface graphique. Fournir des
arguments démarre au contraire un traitement en ligne de commande, sans
fenêtre. L’interface détecte automatiquement le français ou l’anglais et
propose aussi un sélecteur manuel.

Le formulaire suit l’ordre du traitement :

1. Nommer le projet et choisir les emplacements de sortie et de cache.
2. Définir la zone à partir d’une commune, de coordonnées GPS, d’une emprise,
   d’un département ou d’une région, selon la source et le pays.
3. Choisir l’un des cinq types de traitement : LiDAR, raster, vectoriel,
   fusion vectorielle ou découpage raster.
4. Choisir la source et les options. En mode LiDAR, la surface peut être le MNT
   du fournisseur ou, lorsque la source le permet, un nuage de points classé
   traité en mode DFM avec un socle par classes ou par tissu CSF.
5. Choisir les formats compatibles avec l’application cible, puis lancer. Voir
   [Formats et applications mobiles](formats.fr.md).

![Formulaire LiDAR principal sur une surface MNT](../screenshots/GUI/lidar_dtm.PNG)

L’interface valide le formulaire avant le départ et affiche un journal en
direct pendant le traitement.

## Historique, arrêt propre et file d’attente

- **Historique résistant aux crashs :** chaque exécution reste visible dans
  l’historique avec son état et ses journaux, y compris après une interruption
  ou un échec.
- **Arrêt et reprise propres :** le traitement peut terminer proprement le
  morceau courant ; un manifeste mémorise les morceaux terminés afin qu’une
  relance les reprenne au lieu de recommencer.
- **File d’attente :** `＋ File` mémorise plusieurs zones configurées. `Lancer
  la file` les traite sans surveillance et l’échec d’un élément n’empêche pas
  le lancement des suivants.

Les grandes zones peuvent aussi être découpées ou confiées à une ou plusieurs
VM ; voir le [guide d’exécution distante](remote.fr.md).

## Planche d’assemblage

Chaque traitement crée normalement un `<produit>_planche.png` à côté des
livrables. Il montre l’emprise traitée et les cellules de sortie numérotées, ce
qui est particulièrement utile pour un projet découpé. Les légers
chevauchements entre cellules correspondent aux vraies tuiles de bord communes
aux faibles niveaux de zoom.

Le fond avec la limite administrative est un habillage au mieux : lidar2map
utilise le contour du département en France ou une limite géocodée équivalente
ailleurs. Hors connexion, ou si aucune limite n’est résolue, la planche reste
générée avec l’emprise et les cellules seules.

![Exemple de planche d’assemblage d’un projet VAT découpé en grille 3×4](../screenshots/index_sheet.png)

La planche est activée par défaut. `--no-index-map` la désactive et
`--index-sheet DOSSIER` la régénère depuis un projet existant.

## Désinstaller

Utilisez `--desinstaller` avec le lanceur ou le script, par exemple :

```powershell
lidar2map.exe --desinstaller
```

```bash
./lidar2map --desinstaller
# ou : python3.12 lidar2map.py --desinstaller
```

Cette commande supprime l’environnement virtuel privé et les outils/runtime
installés. Elle ne supprime ni le lanceur ni le script source.

---

[Formats et applications mobiles →](formats.fr.md) · [Index de la documentation](README.fr.md)
