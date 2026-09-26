# Bien démarrer avec lidar2map

*[English](getting-started.md) | **Français** · [Index de la documentation](README.fr.md)*

Ce guide couvre l’installation, le premier lancement et l’usage quotidien de
l’interface graphique. Pour choisir un format et importer une carte sur le
téléphone, voir [Formats et applications mobiles](formats.fr.md). La compilation
et la publication de l’application sont documentées séparément dans
[BUILD.md](../BUILD.md).

## 1. Choisir comment lancer lidar2map

lidar2map peut être lancé depuis une application binaire autonome ou directement
depuis son script Python. Ces deux voies donnent accès à la même interface et à
la même CLI, mais leur installation et leur mise à jour diffèrent.

| | **Application binaire autonome** | **Script Python** |
|---|---|---|
| Prérequis | Aucun en dehors d’un OS pris en charge | Python 3.12 |
| Première préparation | Aucune installation : décompresser l’archive et lancer le programme | Environ 5 minutes ; bootstrap automatique dans un environnement virtuel privé |
| Mise à jour | Télécharger la nouvelle release et l’extraire par-dessus la précédente | `git pull`, puis relancer |
| Distribuable | Oui : le dossier extrait, ou `LIDAR2MAP.app`, est l’application entière | Non : chaque ordinateur prépare son environnement Python |
| Recommandé pour | Utilisateur final et redistribution | Développement, usage Linux depuis les sources et contribution |

### 1.1 Application binaire autonome

L’application binaire autonome est le choix normal pour l’utilisateur final.
Elle embarque son propre Python, ses dépendances, le runtime Java et osmosis,
sans les installer dans le système.

La publication des archives binaires autonomes relève de la maintenance. Les
scripts de compilation, l’empaquetage et le déploiement d’une release sont
décrits uniquement dans [BUILD.md](../BUILD.md).

#### 1.1.1 Télécharger et extraire l’application binaire autonome

Téléchargez l’archive de votre plateforme depuis la
[page GitHub Releases](https://github.com/nico579/lidar2map/releases), puis
décompressez-la sans déplacer les fichiers à l’intérieur du dossier extrait.

| OS | Archive | Extraction |
|---|---|---|
| Windows 10/11, x86-64 | `lidar2map-windows-x86_64.zip` | Explorateur de fichiers ou `Expand-Archive` dans PowerShell |
| Ubuntu 24.04+, x86-64 | `lidar2map-linux-x86_64.tar.gz` | `tar xzf lidar2map-linux-x86_64.tar.gz` |
| macOS 12+, Apple Silicon | `lidar2map-macos-arm64.zip` | Finder (double-clic) ou `ditto -x -k`, puis retirer la quarantaine comme indiqué plus bas si Gatekeeper bloque le premier lancement |
| macOS 12+, Intel | `lidar2map-macos-x86_64.zip` | Idem |

Le dossier extrait est l’application elle-même : `lidar2map.exe` (Windows) ou
`lidar2map` (Linux) à côté du dossier `_internal` dont il a besoin, ou
`LIDAR2MAP.app` sous macOS. Rien n’est installé dans le système : rangez le
dossier où bon vous semble, par exemple dans `%LOCALAPPDATA%\Programs` sous
Windows, et `LIDAR2MAP.app` dans `/Applications`. Sous macOS, préférez le
Finder ou `ditto` aux autres outils de décompression : l’application contient
des liens symboliques qui doivent survivre à l’extraction.

#### 1.1.2 Lancer l’application binaire autonome

| OS | Démarrage |
|---|---|
| Windows | Double-cliquer sur `lidar2map.exe` : aucune fenêtre de console n’apparaît. Lancé depuis un terminal, il y affiche toujours son journal. |
| Linux | Exécuter une fois `chmod +x lidar2map`, puis `./lidar2map` depuis le dossier extrait. |
| macOS | Double-cliquer sur `LIDAR2MAP.app`. Si Gatekeeper le bloque, exécuter `xattr -dr com.apple.quarantine LIDAR2MAP.app`, puis recommencer. |

#### 1.1.3 Premier démarrage du binaire

Le programme démarre directement depuis le dossier extrait, sans rien
décompresser au préalable. Jusqu’à la version 1.54, un lanceur l’extrayait au
premier lancement, en 30 à 60 secondes, dans une seconde copie :

- Windows : `%LOCALAPPDATA%\lidar2map\`
- macOS : `~/Library/Application Support/lidar2map/`
- Linux : `~/.local/share/lidar2map/`

La version 1.55 supprime cette copie à son premier démarrage, ainsi que le
`lidar2map_bundle.zip` que l’ancien lanceur laisse à côté du programme quand on
décompresse la nouvelle archive par-dessus l’ancienne.

### 1.2 Script Python

Au premier lancement, le script crée `~/.lidar2map/venv` et y installe les
dépendances critiques : Pillow, pyproj, numpy, scipy, ijson, rasterio, fiona,
certifi, platformdirs (dossiers standard) et pystray (icône de la zone de
notification). numba (SVF bien plus
rapide) et osmium (pipeline OSM) sont installés si possible ; leur échec ne
bloque pas le lancement. L’environnement Python système n’est pas modifié. Utilisez
`--bootstrap=none` si vous préférez gérer vous-même les dépendances.

Temurin 21 et osmosis sont téléchargés à la demande. Aucun GDAL système n’est
nécessaire, car les wheels rasterio embarquent le leur. Prévoir environ 400 Mo
pour cette préparation effectuée une seule fois.

#### 1.2.1 Windows 10+

1. Installer [Python 3.12 ou plus récent](https://www.python.org/downloads/).
2. Cloner puis lancer :

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
python lidar2map.py
```

#### 1.2.2 macOS 11+

```bash
brew install python@3.12
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

#### 1.2.3 Debian / Ubuntu

```bash
sudo apt install python3.12 python3.12-venv git
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

Les cas Linux/macOS tels que PEP 668, les distributions sans `apt`, un bureau
sans zone de notification ou Gatekeeper sur le runtime Java sont traités dans
la [section Dépannage de BUILD.md](../BUILD.md#9-dépannage).

### 1.3 Où lidar2map range vos données

lidar2map sépare deux sortes de fichiers. Vos sorties, c’est-à-dire les
projets, les caches téléchargés et la production calculée, sont de gros
fichiers que vous voudrez retrouver, copier ou supprimer vous-même : elles vont
dans `Documents/lidar2map`. Son état, c’est-à-dire les réglages, l’historique,
le fichier `lidar2map.env` qui porte une clé API IGN, et les journaux, est
léger et géré pour vous : il va dans le dossier de données standard de votre
système.

- Windows : `%LOCALAPPDATA%\lidar2map-data\`
- macOS : `~/Library/Application Support/lidar2map-data/`
- Linux : `~/.local/share/lidar2map-data/`

Ce dossier s’appelle `lidar2map-data` parce que `lidar2map` était, jusqu’à la
version 1.54, la copie du programme extraite par le lanceur, que la version
1.55 supprime : vos réglages ne partent pas avec elle.

Jusqu’à la version 1.53, tout était rangé à côté du programme. Extrayez la
version 1.54 par-dessus la précédente : à son premier lancement, elle copie les
réglages, l’historique et le fichier de clé API dans le dossier de données, en
laissant les originaux en place, et continue d’écrire les sorties à côté de
vos projets existants. Rien ne bouge sur le disque. Chaque traitement peut toujours écrire ailleurs, avec les
dossiers de sortie, de cache et de production de l’interface ou avec
`--output-dir`, `--cache-dir` et `--production-dir`.

Pour tout garder dans un seul dossier de votre choix, comme une installation
portable, définissez la variable d’environnement `LIDAR2MAP_HOME` : l’état et
les sorties y vont alors tous les deux.

## 2. Premier lancement et parcours graphique — binaire ou script

### 2.1 Ouvrir l’interface graphique

Que lidar2map soit démarré depuis l’application binaire autonome ou depuis le
script Python, un lancement sans argument démarre un petit serveur web local et
ouvre l’interface dans votre navigateur par défaut, à l’adresse
`http://127.0.0.1:8766/`. Il n’y a pas de fenêtre d’application séparée : c’est
le navigateur que vous utilisez déjà qui affiche le formulaire. Fournir des
arguments démarre au contraire un traitement en ligne de commande, sans
interface.

| Mode d’exécution | Ouvrir l’interface graphique |
|---|---|
| Application binaire autonome | Double-cliquer sur l’application, ou exécuter `lidar2map.exe`, `./lidar2map` ou `LIDAR2MAP.app` selon la plateforme. |
| Script Python | Exécuter `python lidar2map.py` sous Windows ou `python3.12 lidar2map.py` sous macOS/Linux. |

L’interface détecte automatiquement le français ou l’anglais et propose aussi
un sélecteur manuel.

Par défaut, le serveur n’écoute que sur cette machine (`127.0.0.1`) et n’accepte
que ses requêtes, plus celles de l’hôte de confiance s’il est défini (voir
2.5) ; il n’y a ni compte ni mot de passe. Fermer l’onglet du
navigateur n’arrête ni le serveur ni un traitement en cours : rouvrez la page
depuis l’icône de la zone de notification ou à la même adresse.

### 2.2 Configurer le premier traitement

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

### 2.3 Suivre le traitement

L’interface valide le formulaire avant le départ et affiche un journal en
direct pendant le traitement.

### 2.4 Icône de la zone de notification, arrêt et second lancement

Tant que le serveur tourne, une icône lidar2map est présente dans la zone de
notification :

| Entrée du menu | Effet |
|---|---|
| **Ouvrir** | Rouvre l’interface dans le navigateur. |
| **Redémarrer** | Arrête proprement le traitement en cours, puis relance le serveur avec les mêmes options. |
| **Arrêter** | Arrête proprement le traitement en cours, puis le serveur. |

Un arrêt propre laisse l’opération en cours se terminer et fermer ses
fichiers ; il est forcé au bout de 15 secondes si le traitement ne s’arrête
pas.

Si lidar2map est relancé alors qu’un serveur répond déjà sur le port 8766 :

- sans terminal visible (double-clic sur `lidar2map.exe` ou `LIDAR2MAP.app`,
  raccourci de bureau Linux), l’interface existante s’ouvre dans un nouvel
  onglet avec la question : **Continuer avec cette instance** (défaut) ou
  **➕ Nouvelle instance**, qui fait de cet onglet un second serveur sur le port
  libre suivant, pour un traitement en parallèle ;
- depuis un terminal, la même question y est posée (Entrée : rejoindre, `N` :
  nouveau serveur), dans la langue choisie dans l’interface ;
- avec `--no-browser` (démarrage automatique), il ne démarre rien.

À tout moment, le bouton **➕ Nouvelle instance** de l’interface démarre un
second serveur et l’ouvre dans un nouvel onglet, avec sa propre icône pour
l’arrêter. Depuis un terminal, `--serve-gui --new-instance` fait de même sans
question.
Jusqu’à dix ports consécutifs sont essayés. Chaque serveur exécute un seul
traitement à la fois.

Si l’icône ne peut pas être créée (Linux sans affichage, par exemple via SSH ou
dans un service démarré avant la session graphique), le serveur continue sans
elle et le signale ; arrêtez-le par `Ctrl+C` dans son terminal. Sur un bureau
sans zone de notification (par exemple GNOME sans l’extension AppIndicator),
lancez avec `--serve-gui --no-tray`, et ajoutez `--no-browser` si aucun
navigateur ne doit s’ouvrir. Les options du serveur sont détaillées dans la
[référence CLI](cli.fr.md#serveur-de-linterface-web).

### 2.5 Démarrage automatique et accès distant

Le bouton **🌐 Accès distant** ouvre deux réglages.

**Démarrage automatique.** Cette case démarre le serveur en arrière-plan à
l’ouverture de session, sans ouvrir le navigateur : un script dans le dossier
Démarrage de Windows, un agent `launchd` sous macOS ou un service
`systemd --user` sous Linux. L’interface est ensuite accessible depuis l’icône
de la zone de notification ou à `http://127.0.0.1:8766/`. Avec l’application
binaire autonome, le serveur démarré automatiquement utilise les mêmes projets,
cache, historique et préférences qu’un lancement manuel. Si vous aviez activé
cette option avec une version antérieure, décochez-la puis recochez-la une fois
pour que l’entrée de démarrage soit réécrite.

**Hôte de confiance.** Pour atteindre l’interface depuis un téléphone via un VPN
maillé comme Tailscale ou WireGuard, indiquez l’adresse de cette machine sur ce
réseau (par exemple `100.x.y.z`, donnée par `tailscale ip`) et enregistrez. Le
serveur écoute alors aussi sur cette adresse, au même port, tout en répondant
toujours sur `127.0.0.1` sur cette machine : ouvrez `http://100.x.y.z:8766/` sur
le téléphone. Le réglage est enregistré, appliqué immédiatement et repris aux
lancements suivants, y compris par le serveur démarré automatiquement. Si
l’adresse n’existe pas encore (VPN non connecté), le serveur réessaie toutes
les 30 secondes. L’équivalent en ligne de commande est
`--serve-gui --trusted-host 100.x.y.z`.

`--bind` n’est pas nécessaire pour cela. Avec une adresse autre que la boucle
locale, le serveur n’écoute que sur celle-ci et y ouvre sa page ; évitez
`--bind 0.0.0.0`, qui expose le serveur sur tous les réseaux.

## 3. Historique, arrêt propre et file d’attente

### 3.1 Historique résistant aux crashs

Chaque exécution reste visible dans l’historique avec son état et ses journaux,
y compris après une interruption ou un échec.

### 3.2 Arrêt et reprise propres

Le traitement peut terminer proprement le morceau courant ; un manifeste
mémorise les morceaux terminés afin qu’une relance les reprenne au lieu de
recommencer.

### 3.3 File d’attente

`＋ File` mémorise plusieurs zones configurées. `Lancer la file` les traite sans
surveillance et l’échec d’un élément n’empêche pas le lancement des suivants.

Les grandes zones peuvent aussi être découpées ou confiées à une ou plusieurs
VM ; voir le [guide d’exécution distante](remote.fr.md).

## 4. Planche d’assemblage

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

## 5. Désinstaller

### 5.1 Depuis l’application binaire autonome

Utilisez `--desinstaller` avec l’application. Sous Windows :

```powershell
lidar2map.exe --desinstaller
```

Sous Linux :

```bash
./lidar2map --desinstaller
```

Sous macOS :

```bash
LIDAR2MAP.app/Contents/MacOS/lidar2map --desinstaller
```

### 5.2 Depuis le script Python

Dans le dépôt source, sous Windows :

```powershell
python lidar2map.py --desinstaller
```

Sous macOS ou Linux :

```bash
python3.12 lidar2map.py --desinstaller
```

### 5.3 Éléments supprimés et conservés

Cette commande supprime l’environnement virtuel privé et les outils/runtime
installés. Elle ne supprime ni le dossier du programme, ni `LIDAR2MAP.app`, ni le script source, ni vos sorties
et votre dossier de données (voir [Où lidar2map range vos données](#13-où-lidar2map-range-vos-données)) :
supprimez-les vous-même si vous n’en avez plus besoin.

---

[Formats et applications mobiles →](formats.fr.md) · [Index de la documentation](README.fr.md)
