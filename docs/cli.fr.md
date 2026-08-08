*[English](cli.md) | **Français** · [Index de la documentation](README.fr.md)*

# Référence de la ligne de commande

La CLI donne accès à tous les workflows de lidar2map : relief LiDAR, cartes
raster classiques, cartes vectorielles OSM et IGN, fusion vectorielle,
découpage raster, partage vers le téléphone, reconstruction des planches
d’index et exécution distante.

Cette page décrit le comportement des parseurs actuels. Pour l’installation et
l’interface graphique, voir [Bien démarrer](getting-started.fr.md). Pour choisir
un livrable, voir [Formats et applications mobiles](formats.fr.md) ; pour la
disponibilité des sources, voir [Fournisseurs et couverture](providers.fr.md).

## Forme de la commande et choix du mode

Les exemples utilisent la version source Python :

```bash
python lidar2map.py <mode> <zone> [options]
```

Avec une release, remplacer `python lidar2map.py` par `lidar2map.exe` sous
Windows, `./lidar2map` sous Linux ou l’exécutable contenu dans
`LIDAR2MAP.app` sous macOS.

- Sans argument, lidar2map ouvre l’interface graphique.
- Tout argument de traitement sélectionne la CLI sans fenêtre.
- Utiliser un seul mode principal par invocation : `--lidar`, `--raster`,
  `--osm`, `--vector`, `--merge`, `--split` ou `--serve`.
- `--lidar` et `--osm` constituent la seule combinaison utile : une même
  commande peut produire le relief LiDAR et une carte vectorielle OSM de la
  même zone.
- `--remote-cli` et `--remote-gui` sont des préfixes de dispatch précoce : ils
  doivent être le premier argument après l’exécutable.
- `--index-sheet DIR` est un mode de maintenance autonome.

L’aide propre à chaque mode fait foi :

```bash
python lidar2map.py --help
python lidar2map.py --raster --help
python lidar2map.py --vector --help
python lidar2map.py --merge --help
python lidar2map.py --split --help
python lidar2map.py --remote-cli --help
```

`--version` affiche la version puis quitte. Les options anglaises sont
canoniques ; les [alias français](#alias-français) restent acceptés.

## Premier LiDAR en deux minutes

Une commande LiDAR normale ne demande plus qu’un workflow et une zone :

```bash
python lidar2map.py --lidar --zone-city Gareoult
```

Sans question cachée, cette commande :

1. utilise le fournisseur `fr-ign` ;
2. crée un carré de 20 km de côté autour de la commune géocodée ;
3. télécharge uniquement les dalles sources manquantes ;
4. calcule un `lrm` ;
5. écrit une carte MBTiles aux zooms 13–18 ;
6. crée une planche d’index lorsqu’un livrable lisible existe.

Les dalles valides déjà en cache sont réutilisées. Pour exiger un cache déjà
rempli et refuser le téléchargement des données sources :

```bash
python lidar2map.py --lidar --zone-city Gareoult --no-download
```

Si les données nécessaires sont absentes, le traitement cache-only échoue avec
un message indiquant comment autoriser le téléchargement. `--no-download`
contrôle les téléchargements des données LiDAR ; le géocodage ou la découverte
du fournisseur peuvent encore nécessiter un accès réseau.

Les modes GPS et bbox n’exigent plus `--zone-name` :

```bash
python lidar2map.py --lidar --zone-gps 43.3156,6.0423 --zone-width 2
python lidar2map.py --lidar --zone-bbox 6.0,43.3,6.1,43.4
```

Ils reçoivent un nom stable dérivé des coordonnées arrondies à cinq décimales,
par exemple `gps_43_31560_6_04230`. Utiliser `--zone-name` lorsqu’un nom humain
est plus parlant.

## Zones, noms et dossiers

Chaque workflow géographique exige exactement un sélecteur de zone. La seule
exception est la conversion directe d’un fichier `.mbtiles` existant.

| Option | Valeur / défaut | Rôle |
|---|---|---|
| `--zone-city NOM` | sélecteur obligatoire | Géocode une commune avec Nominatim. |
| `--zone-gps LAT,LON` | sélecteur obligatoire | Centre WGS84 ; le point-virgule est aussi accepté comme séparateur. |
| `--zone-bbox O,S,E,N` | sélecteur obligatoire | Ouest, sud, est, nord en degrés WGS84. Les paires inversées sont normalisées ; une bbox nulle ou hors limites est refusée. |
| `--zone-department NUM` | France uniquement | Un département, ou une liste/plage exécutée en traitements successifs ; voir [Zones propres à la France](#zones-et-exemples-propres-à-la-france). |
| `--zone-region SLUG` | France / Geofabrik | Slug d’une ancienne région Geofabrik France. |
| `--zone-width KM` | `20` | Côté du carré autour d’une commune ou d’un point GPS, et non son rayon. Sans effet sur une bbox, un département ou une région. |
| `--zone-name NOM` | automatique | Remplace le nom de projet normalisé. Commune, GPS, bbox, département et région ont tous un nom automatique. |

Le dossier de travail est celui du script avec les sources, et celui de
l’exécutable extérieur avec une release. Chemins par défaut :

```text
<travail>/Projets/<zone>/lidar/<pays>/
<travail>/Projets/<zone>/raster/
<travail>/Projets/<zone>/osm_vecteur/
<travail>/Projets/<zone>/ign_vecteur/
<travail>/cache/
<travail>/production/
```

| Option | Défaut | Rôle |
|---|---|---|
| `--output-dir CHEMIN` | chemin propre au mode sous `Projets/<zone>` | Écrit directement dans `CHEMIN` ; c’est le dossier final du mode, pas une racine à laquelle lidar2map ajoute le nom de projet. |
| `--cache-dir CHEMIN` | `<travail>/cache` | Racine des dalles LiDAR, tuiles WMTS, PBF OSM, index de découverte et autres caches téléchargés persistants. |
| `--production-dir CHEMIN` | `<travail>/production` | Racine des GeoTIFF calculés depuis un nuage LAZ mais réutilisables. Utile pour le mode nuage de points LiDAR. |
| `--tiles-dir CHEMIN` | politique ci-dessous | Remplace l’emplacement des sources LiDAR uniquement et prend priorité sur `--cache-dir` et `--production-dir`. |

Sans `--tiles-dir`, les MNT téléchargés vont dans `cache/lidar/<pays>`. En mode
nuage de points, le LAZ/LAS téléchargé reste au cache, tandis que son GeoTIFF
dérivé va dans `production/lidar/<pays>`. Les fragments COG/COPC fenêtrés sont
propres à une zone et restent donc dans le projet. Voir
[DFM, LAZ et CSF](dfm.fr.md) pour le modèle de stockage complet.

## Workflow LiDAR

### Défauts et acquisition des données

```bash
python lidar2map.py --lidar ZONE [OPTIONS LIDAR]
```

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--lidar` | désactivé | Sélectionne le traitement du terrain. Alias historique : `--ignlidar`. |
| `--provider CODE` | `LIDAR2MAP_PROVIDER`, sinon `fr-ign` | Sélectionne une source du [catalogue des fournisseurs](providers.fr.md). |
| `--api-key CLE` | variable d’environnement du fournisseur si prise en charge | Fournit l’identifiant demandé par certaines sources. |
| `--download` / `--no-download` | téléchargement du manque pour un `--lidar` normal | Autorise le téléchargement manquant ou impose un traitement cache-only. |
| `--workers N` | `8` | Connexions parallèles aux dalles sources ; valeur strictement positive. Un fournisseur peut imposer une limite effective plus basse. |
| `--download-compress` / `--no-download-compress` | activé | Active ou désactive la compression DEFLATE des dalles raster en cache. |
| `--download-force` | désactivé | Retélécharge aussi les données sources valides du cache. |
| `--download-overwrite` | désactivé | Équivalent à `--download-force`, nuages LAZ compris. |

`--download` signifie « télécharger ce qui manque », pas « tout
retélécharger ». Une entrée de cache valide est ignorée sauf si l’un des deux
flags de forçage est présent.

### Choisir les visualisations

Le défaut d’un traitement `--lidar` normal est `lrm`. Sélectionner des
instances ordinaires avec une option multivaleur :

```bash
python lidar2map.py --lidar --zone-city Gareoult \
  --shadings multi svf oneg --svf-dist 20 --svf-gamma 2
```

Ou ajouter des instances paramétrées indépendamment avec `--shading`
répétable :

```bash
python lidar2map.py --lidar --zone-city Gareoult \
  --shading svf:dist=20,gamma=2 \
  --shading svf:dist=100,gamma=1.5 \
  --shading oneg:dist=20 \
  --shading 315:elevation=20 \
  --shading lrm:sigma=10
```

Les paramètres non standards sont encodés dans les noms de sortie : les
instances distinctes ne se collisionnent pas et les visualisations terminées
peuvent être réutilisées.

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--shadings TYPE...` | `lrm` dans un run normal | Types : `lrm vat e4mstp svf opos oneg rrim multi 315 045 135 225 slope`, plus `all`, `none`, `tous`, `aucun`. |
| `--shading TYPE[:k=v,...]` | aucun ; répétable | Ajoute une instance avec ses propres paramètres. Un type couvert ici n’est pas aussi produit depuis `--shadings` avec les réglages globaux. |
| `--shading-preset NOM` | désactivé | Ajoute la pile adaptée à la résolution décrite ci-dessous. Valeurs : `auto`, `micro`, `standard`, `landscape`. |
| `--shading-elevation DEG` | `25` | Élévation solaire globale de `multi` et des hillshades directionnels. |
| `--svf-conv flux\|rvt` | `flux` | Convention SVF globale : flux cos²γ contrasté ou convention RVT 1−sin γ. |
| `--svf-dist M` | `20` | Rayon d’horizon global en mètres pour SVF, openness et composites. Environ 100 m cible des enclos ou chemins plus larges. |
| `--svf-gamma G` | `2.0` | Contraste global de SVF, openness et VAT. e4MSTP possède son propre défaut à `0.8`. |
| `--svf-sweep` / `--no-svf-sweep` | activé | Active ou désactive le noyau accéléré de balayage de l’horizon. |
| `--shadings-overwrite` | désactivé | Recalcule un GeoTIFF d’ombrage existant. |

`all` et son alias français `tous` développent tous les résultats simples sauf
les deux composites lourds `vat` et `e4mstp`, dont les calculs internes
répéteraient du travail déjà demandé. Les demander explicitement si nécessaire.
`none` et `aucun` suppriment tous les ombrages, y compris les instances fournies
avec `--shading`.

Clés acceptées par instance :

| Type | Clés acceptées | Défauts |
|---|---|---|
| `multi 315 045 135 225` | `elevation` | 25° |
| `svf` | `conv`, `dist`, `gamma`, `sweep` | `flux`, 20 m, 2.0, activé |
| `opos oneg` | `dist`, `gamma`, `sweep` | 20 m, 2.0, activé |
| `vat` | `dist`, `gamma` | 20 m, 2.0 |
| `e4mstp` | `dist`, `gamma` | 20 m, 0.8 |
| `lrm rrim` | `sigma` en mètres | `15 × résolution du fournisseur`, soit 15 pixels sources |
| `slope` | aucune | aucun paramètre réglable |

Pour `sweep`, les valeurs booléennes numériques comme `1` et `0` sont
acceptées dans une spécification d’instance. Pour la signification scientifique,
les forces et limites de chaque type, utiliser le
[guide des visualisations](shadings.fr.md).

### Presets par résolution

Chaque preset ajoute `svf`, `opos`, `lrm`, `multi` et `slope`. Ses dimensions
sont en mètres au sol, pas en pixels :

| Preset | Choisi par `auto` | Rayon SVF/openness | Sigma LRM | Élévation solaire |
|---|---|---:|---:|---:|
| `micro` | résolution ≤ 0,75 m | 15 m | 8 m | 25° |
| `standard` | 0,75 m < résolution ≤ 2,5 m | 30 m | 15 m | 25° |
| `landscape` | résolution > 2,5 m | 80 m | 40 m | 30° |

```bash
python lidar2map.py --lidar --provider ch-swisstopo \
  --zone-city Lausanne --shading-preset auto
```

Les paramètres d’instance fournis explicitement restent des sorties séparées
et nommées distinctement.

### Mode nuage de points / DFM

`--laz` bascule le fournisseur parent sélectionné vers son jumeau `-laz`. Ce
mode n’est disponible que lorsque le fournisseur publie un nuage classé dense.
Garder le premier essai petit : la source et la conversion sont beaucoup plus
lourdes qu’un MNT.

| Option | Défaut courant | Rôle |
|---|---:|---|
| `--laz` | désactivé | Utilise le nuage classé plutôt que le MNT bare-earth officiel. |
| `--laz-ground classes\|csf` | propre au fournisseur | Choisit réinjection des classes producteur ou Cloth Simulation Filter. `fr-ign` utilise `classes` par défaut ; la plupart des autres jumeaux utilisent `csf`. |
| `--laz-hmin M` | 0,4 m | Hauteur minimale réinjectée en mode classes. |
| `--laz-hmax M` | 2,5 m | Hauteur maximale réinjectée en mode classes. |
| `--laz-classes LISTE` | propre au fournisseur ; `1,2,3,4,9,66` pour `fr-ign` | Classes LAS participantes, séparées par des virgules. |
| `--laz-csf-threshold M` | 0,5 m | Distance d’absorption point-tissu, valide de 0,1 à 3,0 m. |
| `--laz-csf-resolution M` | 0,5 m | Maille du tissu, valide de 0,1 à 3,0 m. |
| `--laz-csf-rigidness N` | `1` | `1` pentu/souple, `2` intermédiaire, `3` plat/rigide. |
| `--laz-parallel N` | `1` | Conversions simultanées ; prévoir environ 3 Go de RAM par conversion. |

`hmin`, `hmax` et `classes` sont ignorés en mode CSF ; les paramètres `csf-*`
sont ignorés en mode classes. Le nom de projet reçoit le suffixe de la variante
active, afin que MNT, DFM par classes et CSF ne se mélangent pas. Interprétation
et défauts par fournisseur : [Structures debout avec LAZ, DFM et CSF](dfm.fr.md).

### Grandes zones, reprise et contrôle du disque

Le prédécoupage traite un morceau à la fois et conserve l’avancement dans
`manifeste.json`. Relancer la même commande après une interruption reprend les
morceaux terminés.

| Option | Défaut | Rôle |
|---|---:|---|
| `--split-cols N` | `0` | Colonnes de grille. Une grille n’est active que si colonnes et lignes sont toutes deux positives. |
| `--split-rows N` | `0` | Lignes de grille. |
| `--split-width KM` | `0` | Côté alternatif d’un morceau carré ; actif s’il est positif. |
| `--block i/M` | désactivé | Ne traite que le bloc géographique `i` parmi `M`, pour répartir une même zone entre machines. |
| `--cleanup` | désactivé | Supprime les intermédiaires des morceaux réussis, en conservant les livrables finaux. |
| `--cleanup-keep-tiles` | désactivé | Avec cleanup, conserve les dalles sources téléchargées et partagées pour un autre run. |
| `--min-free-gb GO` | `0` | Avant un morceau, quitte avec le code 3 si l’espace libre passe sous le seuil. |

Pour SVF/openness, un premier repère pratique est au plus environ 600 km² par
morceau sur une machine de 32 Go et environ 1 150 km² sur 64 Go. La densité des
dalles sources peut faire diverger deux morceaux de même surface. Voir les
[conseils RAM et découpage distants](remote.fr.md#ram-et-taille-des-morceaux).

### Contrôles de sortie LiDAR

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--file-formats FMT...` | `mbtiles` dans un run LiDAR normal productif | `mbtiles`, `rmap` et/ou `sqlitedb`. Les formats vectoriels ne servent qu’avec `--osm` combiné. |
| `--zoom-min N` | `13` | Zoom raster minimal. |
| `--zoom-max N` | `18` | Zoom raster maximal. Les zooms valides vont de 0 à 22 et le minimum ne doit pas dépasser le maximum. |
| `--image-format FMT` | `auto` | `auto`, `jpeg` ou `png` ; les tuiles de bord avec alpha peuvent rester en PNG. |
| `--image-quality Q` | `85` | Qualité JPEG de 1 à 100. |
| `--tiles-overwrite` | désactivé | Reconstruit une carte tuilée ou conversion existante. |
| `--index-map` / `--no-index-map` | activé | Active ou désactive la planche `<produit>_planche.png` best-effort pour ce parseur. |

La résolution au sol Web Mercator vaut
`156543.03 × cos(latitude) / 2^zoom` mètres par pixel. En métropole, le zoom 18
vaut environ 0,42–0,44 m/px et convient donc à un MNT de 0,5 m. Règle utile pour
le zoom natif : `ceil(log2(156543.03 × cos(latitude) / résolution))`, soit
environ z19 pour 0,25 m, z18 pour 0,5 m, z17 pour 1 m, z16 pour 2 m et z15 pour
5 m.

### Exemples LiDAR

Hillshade multidirectionnel et SVF sur une commune de 2 km de côté :

```bash
python lidar2map.py --lidar --zone-city Gareoult --zone-width 2 \
  --shadings multi svf --file-formats mbtiles
```

Cette commande ne produit que le relief LiDAR. Un fond Plan IGN exige une
invocation `--raster` séparée ; ne pas combiner les modes principaux raster et
LiDAR.

Reproduire les réglages SVF du triptyque du README en remplaçant les
coordonnées :

```bash
python lidar2map.py --lidar \
  --zone-gps <lat>,<lon> --zone-width 2 --zone-name hero \
  --download --workers 8 \
  --shadings svf --svf-conv rvt --svf-dist 20 --svf-gamma 0.8 --svf-sweep \
  --file-formats mbtiles --zoom-min 8 --zoom-max 18 \
  --image-format jpeg --image-quality 85
```

Les coordonnées exactes du site d’exemple ne sont volontairement pas publiées :
ne pas diffuser l’emplacement d’un microrelief archéologique sensible.

## Workflow raster classique

```bash
python lidar2map.py --raster ZONE [OPTIONS RASTER]
```

Le mode raster télécharge automatiquement les tuiles cartographiques ou image
et produit par défaut un MBTiles Plan IGN aux zooms 10–16.

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--raster` | désactivé | Sélectionne le raster tuilé classique. Alias historique : `--ignraster`. |
| `--provider CODE` | `fr-ign` | `fr-ign` pour le WMTS IGN ou `us-tnm` avec la couche `naip`. |
| `--layer COUCHE` | `planign` | Alias court ci-dessous ou identifiant WMTS complet. |
| `--api-key CLE` | environnement / vide | Nécessaire uniquement pour les couches IGN Scan professionnelles restreintes. |
| `--workers N` | `8` | Connexions parallèles aux tuiles. |
| `--download-overwrite` | désactivé | Retélécharge les tuiles raster déjà en cache. |
| `--file-formats FMT...` | `mbtiles` | Valeurs possibles : `mbtiles rmap sqlitedb`. |
| `--zoom-min`, `--zoom-max` | `10`, `16` | Plage demandée, validée entre 0 et 22 et plafonnée à la plage annoncée par la couche. |
| `--image-format FMT` | `auto` | `auto`, `jpeg` ou `png`. Une source JPEG ne retrouve aucune qualité en PNG : cette demande reste donc en JPEG. |
| `--image-quality Q` | `85` | Qualité JPEG. |
| `--tiles-overwrite` | désactivé | Reconstruit un MBTiles existant. |
| `--split-cols`, `--split-rows` | `0`, `0` | Grille de prédécoupage séquentiel ; les deux valeurs doivent être positives. |
| `--split-width KM` | `0` | Côté alternatif d’un morceau carré. |
| `--cleanup` | désactivé | Supprime les intermédiaires d’un morceau réussi. |
| `--min-free-gb GO` | `0` | Arrêt propre avec code 3 sous le seuil disque. |

Alias IGN publics :

| Famille | Valeurs |
|---|---|
| Topographique | `planign etatmajor40 etatmajor10 pentes` |
| Imagerie | `ortho ortho_1950 ortho_1965 ortho_1980 ortho_irc pleiades spot edugeo_marseille_1969 edugeo_marseille_1980 edugeo_marseille_1987 edugeo_marseille_1988 edugeo_marseille_2010 edugeo_toulon_1972` |
| Thématique | `cadastre ombrage` |

Les couches professionnelles `scan25`, `scan25tour`, `scan100` et `scanoaci`
exigent un compte professionnel `cartes.gouv.fr` et `--api-key`. La couverture
historique et EDUGEO varie selon le lieu et la date : tester d’abord une petite
zone. L’imagerie américaine s’utilise ainsi :

```bash
python lidar2map.py --raster --provider us-tnm --layer naip \
  --zone-bbox -108.5,37.18,-108.48,37.20
```

Plan IGN autour d’une commune :

```bash
python lidar2map.py --raster --zone-city Gareoult --zone-width 2
```

Orthophoto historique 1950–1965 :

```bash
python lidar2map.py --raster --zone-bbox 6.0,43.3,6.1,43.4 \
  --layer ortho_1950 --zoom-min 14 --zoom-max 18
```

## Workflow vectoriel OSM

```bash
python lidar2map.py --osm ZONE [OPTIONS OSM]
```

Sans format vectoriel explicite, `--osm` produit une carte Mapsforge `.map`.
Ajouter `geojson`, `gz` ou `transparent-raster` selon le besoin.

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--osm` | désactivé | Sélectionne le traitement OSM depuis un PBF ou un XML `.osm`. |
| `--layer TAG...` | liste ci-dessous | Filtres OSM `key=value` libres, passés comme arguments shell séparés. |
| `--source FICHIER.pbf` | sélection Geofabrik automatique en France | Utilise un `.pbf` ou `.osm` existant ; une zone géographique et `--osm` restent obligatoires. |
| `--file-formats FMT...` | `map` si aucun format vectoriel n’est explicite | `map`, `geojson`, `gz` et/ou `transparent-raster`. |
| `--download-overwrite` | désactivé | Actualise un PBF Geofabrik existant. Sinon il est réutilisé et un cache de plus de 30 jours est seulement signalé. |
| `--tiles-overwrite` | désactivé | Reconstruit la `.map` ou le raster transparent existant. |
| `--zoom-min`, `--zoom-max` | 13–18 pour le raster transparent | Les overlays transparents imposent un zoom minimal d’au moins 13. |

Filtres par défaut :

```text
highway=* waterway=* boundary=administrative natural=water
natural=coastline waterway=river waterway=stream waterway=canal
```

La sélection Geofabrik automatique est actuellement limitée à la France. Hors
de France, télécharger soi-même le PBF régional puis le fournir avec `--source` ;
lidar2map le découpe alors à la zone demandée. Demander uniquement `gz` ou
`geojson` évite Mapsforge/osmosis. `transparent-raster` crée un SQLiteDB PNG
avec alpha pour OsmAnd et conserve aussi le GeoJSON intermédiaire nécessaire.

Département français entier au format Mapsforge :

```bash
python lidar2map.py --osm --zone-department 83 --file-formats map
```

Sélection randonnée et patrimoine en GeoJSON compressé plus `.map` :

```bash
python lidar2map.py --osm --zone-city Gareoult --zone-width 5 \
  --layer highway=* waterway=* historic=* \
  --file-formats gz map
```

Combiner les défauts LiDAR normaux avec la carte OSM par défaut :

```bash
python lidar2map.py --lidar --osm --zone-city Gareoult --zone-width 2
```

## Workflow vectoriel IGN

```bash
python lidar2map.py --vector ZONE [OPTIONS VECTORIEL IGN]
```

Ce mode est réservé à la France. Il utilise le WFS IGN ou, pour un département
entier lorsqu’il est disponible, le paquet BD TOPO en téléchargement groupé.

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--vector` | désactivé | Sélectionne le traitement vectoriel IGN. Alias historique : `--ignvecteur`. |
| `--layer NOM...` | `cadastre` | Un ou plusieurs alias ci-dessous, ou des typenames WFS complets. |
| `--workers N` | `4` | Connexions WFS parallèles. Rester à quatre ou moins : le service rejette l’excès de concurrence. |
| `--download-overwrite` | désactivé | Retélécharge un GeoJSON existant. |
| `--file-formats FMT...` | `gz` | `geojson`, `gz`, `map` et/ou `transparent-raster`. Le GeoJSON reste la source des sorties dérivées. |
| `--vector-simplify M` | automatique | Tolérance Douglas–Peucker en mètres pour Mapsforge. |
| `--tiles-overwrite` | désactivé | Reconstruit une `.map` ou un overlay transparent existant. |

Alias IGN acceptés :

```text
cadastre cours_eau troncons_eau plans_eau detail_hydro batiments
constructions cimetieres routes chemins lignes_orog detail_orog forets
reserves lieux_dits communes rpg
```

La simplification automatique vaut 3 m sous 200 km², 8 m sous 1 000 km², 15 m
sous 15 000 km², 25 m sous 100 000 km², puis 40 m au-delà.

Routes et bâtiments en GeoJSON compressé plus Mapsforge :

```bash
python lidar2map.py --vector --zone-department 83 \
  --layer routes batiments --file-formats gz map
```

Chemins sous forme d’overlay OsmAnd :

```bash
python lidar2map.py --vector --zone-city Gareoult --zone-width 5 \
  --layer chemins --file-formats gz transparent-raster
```

OsmAnd ne lit pas les `.map` Mapsforge : utiliser `transparent-raster` en
overlay ou sa carte OSM intégrée. Locus et OruxMaps peuvent utiliser Mapsforge.

## Fusionner des sources vectorielles

`--merge` combine des sources `.geojson` et `.geojson.gz`, motifs glob compris.
Il ajoute aux entités fusionnées une propriété `source` identifiant le fichier
d’origine.

```bash
python lidar2map.py --merge \
  --source cadastre.geojson cours_eau.geojson osm_gareoult.geojson \
  --output-file gareoult_fusion.geojson
```

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--source FICHIER...` | obligatoire | Entrées ; lidar2map développe les motifs glob si le shell ne le fait pas. |
| `--output-file FICHIER` | dérivé à côté de la première source | Chemin GeoJSON fusionné explicite. |
| `--output-dir CHEMIN` | dossier de la première source | Dossier utilisé uniquement lorsque le nom de sortie est automatique. |
| `--no-gz` | désactivé | Produit un fichier primaire automatique `.geojson` au lieu de `.geojson.gz`. |
| `--file-formats FMT...` | `gz` | Demande une sortie secondaire `map` et/ou `transparent-raster` ; `geojson`/`gz` décrivent les formats vectoriels, tandis que `--no-gz` gouverne la compression du fichier primaire automatique. |
| `--vector-simplify M` | automatique | Tolérance de simplification Mapsforge en mètres. |

Fusionner un ensemble désigné par un glob et créer une carte Mapsforge ainsi
qu’un overlay OsmAnd :

```bash
python lidar2map.py --merge \
  --source "Projets/gareoult/*/*.geojson*" \
  --output-file Projets/gareoult/fusion/gareoult.geojson.gz \
  --file-formats gz map transparent-raster
```

Une entrée absente ou illisible rend l’échec visible, même si un fichier
fusionné partiel a pu être écrit.

## Redécouper un raster existant

`--split` redécoupe un MBTiles sans rejouer son téléchargement ni son rendu :

```bash
python lidar2map.py --split --source large.mbtiles \
  --cols 3 --rows 4 --file-formats mbtiles sqlitedb
```

| Option | Défaut / valeurs | Rôle |
|---|---|---|
| `--source FICHIER.mbtiles` | obligatoire | Raster source. |
| `--cols N`, `--rows N` | `0`, `0` | Grille explicite ; les deux doivent être positifs pour découper. |
| `--split-width KM` | `0` | Côté approximatif alternatif des carrés. |
| `--file-formats FMT...` | `mbtiles` | Conserve chaque morceau en `mbtiles` et/ou le convertit en `rmap` ou `sqlitedb`. |
| `--tiles-overwrite` | désactivé | Remplace les morceaux existants. |

Sans grille complète ni largeur positive, la source est renvoyée telle quelle ;
la commande peut tout de même la convertir vers un autre format demandé.

```bash
python lidar2map.py --split --source large.mbtiles \
  --split-width 10 --file-formats rmap
```

Si une conversion échoue, lidar2map conserve le MBTiles intermédiaire du
morceau au lieu de supprimer les seules données survivantes.

## Réutiliser ou convertir une source existante

Le comportement de `--source` dépend de l’extension :

| Source | Contexte requis | Résultat |
|---|---|---|
| `.mbtiles` | aucune zone ; `--file-formats rmap` et/ou `sqlitedb` explicite | Conversion directe puis sortie. |
| `.tif` / `.tiff` | une zone ; de préférence `--lidar` ; formats explicites sauf si `--lidar` fournit le défaut MBTiles | L’ombrage existant est tuilé directement en EPSG:3857, sinon d’abord reprojeté en Web Mercator. |
| `.pbf` / `.osm` | `--osm` avec une zone | Filtre et rend les données OSM existantes sans sélection Geofabrik automatique. |
| plusieurs GeoJSON | `--merge` | Fusion vectorielle. |

Exemples :

```bash
# MBTiles vers les deux formats raster téléphone ; aucune zone nécessaire
python lidar2map.py --source relief.mbtiles --file-formats rmap sqlitedb

# GeoTIFF d’ombrage existant vers des livrables raster
python lidar2map.py --lidar --source relief.tif \
  --zone-bbox 6.0,43.3,6.1,43.4 --file-formats mbtiles rmap

# PBF téléchargé manuellement, y compris hors de France
python lidar2map.py --osm --source my-region-latest.osm.pbf \
  --zone-bbox 7.4,46.9,7.6,47.1 --file-formats map
```

## Zones et exemples propres à la France

`--zone-department` accepte un code INSEE, une liste séparée par des virgules,
une plage ou un mélange :

```bash
python lidar2map.py --lidar --zone-department 83
python lidar2map.py --raster --zone-department 30,35,75 --layer planign
python lidar2map.py --vector --zone-department 1-3,75,83 --layer chemins
```

Les codes comme `5` sont normalisés (`05`) ; `2A`, `2B` et les codes
ultramarins sont acceptés. Une invocation multi-départements traite chaque zone
à la suite et continue après une erreur de traitement ordinaire ; son code
final est non nul si une zone a échoué. Un `--zone-name base` explicite devient
`base_<département>` pour éviter les collisions.

`--zone-region` utilise les anciennes régions, antérieures à 2016, publiées par
[Geofabrik France](https://download.geofabrik.de/europe/france.html), par
exemple `provence-alpes-cote-d-azur`, `bretagne`, `corse` ou `rhone-alpes`. Un
slug inconnu affiche la liste acceptée.

Pour OSM, le PBF régional sélectionné possède déjà le vrai contour
administratif et est traité comme un fichier unique, sans redécoupage
rectangulaire :

```bash
python lidar2map.py --osm \
  --zone-region provence-alpes-cote-d-azur
```

Pour LiDAR, raster et vectoriel IGN, la région est la bbox englobant tous ses
départements. Chemins IGN en GeoJSON compressé plus Mapsforge :

```bash
python lidar2map.py --vector \
  --zone-region provence-alpes-cote-d-azur \
  --layer chemins --file-formats gz map
```

Les valeurs des couches raster et vectorielles IGN sont listées plus haut dans
leurs workflows. Elles restent limitées à la France, même si LiDAR et OSM avec
source manuelle sont internationaux.

## Maintenance du cache et des ombrages

Les commandes de maintenance exigent encore `--lidar` et une zone, afin de
résoudre le fournisseur actif, le projet et la portée du cache.

| Option | Effet |
|---|---|
| `--tiles-purge-invalid` | Supprime les sources en cache sous le seuil de validité du fournisseur actif, soit 2 Mo pour `fr-ign`. |
| `--tiles-purge-out-of-zone` | Supprime les dalles du fournisseur courant absentes du `dalles_zone.txt` de ce projet ; ne purge pas volontairement un autre fournisseur partageant le cache du pays. |
| `--shadings-compress` | Réécrit en DEFLATE les grands GeoTIFF bruts d’ombrage existants ; les caches de reprojection tuilée sont exclus. |

Lorsqu’une de ces options est demandée sans ombrage, preset ni format de sortie
explicite, lidar2map traite l’invocation comme une maintenance seule : il
n’ajoute **ni** téléchargement, **ni** LRM, **ni** MBTiles par défaut.

```bash
# Purge seule ; aucun téléchargement de dalle ni génération de carte implicite
python lidar2map.py --lidar --zone-department 83 --tiles-purge-invalid

# Purge puis téléchargement explicitement demandé ; toujours aucune carte implicite
python lidar2map.py --lidar --zone-department 83 \
  --tiles-purge-invalid --download

# Compression des ombrages bruts existants sans en demander un nouveau
python lidar2map.py --lidar --zone-city Gareoult --shadings-compress
```

La purge hors zone exige un `dalles_zone.txt` existant. S’il manque, exécuter
une fois un `--download` explicite pour construire la liste. La maintenance
supprime les transferts de données implicites, mais le géocodage et la
découverte/indexation du fournisseur peuvent toujours utiliser le réseau ;
`--no-download` exprime le mode cache-only des dalles sources.

## Servir les cartes au téléphone

`--serve` recherche récursivement les livrables `.sqlitedb`, `.rmap`,
`.mbtiles`, `.map` et `.obf`, les sert uniquement sur le réseau local et affiche
une URL ainsi qu’un QR code. Le téléphone doit être sur le même Wi-Fi. Arrêter
le serveur avec `Ctrl+C`.

```bash
python lidar2map.py --serve --zone-name gareoult
```

Par défaut, cette commande parcourt `Projets/gareoult`. Avec une sortie de
traitement personnalisée, fournir ce dossier exact ; `--zone-name` reste requis
par la commande :

```bash
python lidar2map.py --serve --zone-name gareoult \
  --output-dir D:/cartes/gareoult
```

Dans Locus, utiliser **Gestionnaire de cartes → Importer une carte →
gestionnaire de fichiers système**. Voir
[Formats et applications mobiles](formats.fr.md) pour les conseils par
application.

## Reconstruire une planche d’index

Les traitements géographiques génèrent une planche best-effort
`<produit>_planche.png` à partir des livrables lisibles. Dans le parseur
LiDAR/OSM, `--no-index-map` désactive cette étape automatique. Les traitements
raster et vectoriel IGN la génèrent actuellement sans interrupteur CLI.

Reconstruire les planches d’un dossier existant sans refaire le traitement :

```bash
python lidar2map.py --index-sheet Projets/gareoult
```

`--planche` est l’alias français. La commande parcourt les sous-dossiers et crée
une planche par produit ; l’absence d’un contour administratif récupéré par le
réseau n’empêche pas la création de la planche d’emprise et de cellules.

## Exécution distante, arrêt et purge

Le préfixe distant intégré doit venir en premier. Lancement headless minimal
sur une VM Ubuntu 24.04/26.04 x86-64 :

```bash
lidar2map --remote-cli --bundle --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --zone-city Paris --zone-width 5
```

Tout ce qui suit le `--` isolé est transmis à lidar2map sur la VM. Utiliser un
nom de session explicite différent pour chaque traitement concurrent.

Le renouvellement de clé SSH est géré automatiquement : après une erreur
confirmant le changement, le contrôleur retire uniquement l'entrée
`known_hosts` obsolète de cette VM et réessaie une fois. `--reset-host-key`
n'est que la commande préventive.

Arrêter exactement une session sans la purger :

```bash
lidar2map --remote-cli --session paris-lrm --stop root@192.0.2.10
```

Le contrôleur demande d’abord un arrêt propre puis, après 15 secondes, ne cible
que l’arbre de descendants et la session tmux correspondants. Les autres
sessions ne sont pas touchées. Les fichiers restent disponibles pour le
diagnostic, la reconnexion ou un futur `--resume`.

Une fois la session terminale, effectuer une dernière synchronisation puis
purger uniquement les fichiers du run vérifié :

```bash
lidar2map --remote-cli --session paris-lrm \
  --purge-remote root@192.0.2.10
```

Le cache, la production, le dépôt source, l’environnement virtuel et le runtime
partagés ne sont jamais purgés. Pendant une surveillance interactive,
`Ctrl+C` demande séparément s’il faut arrêter la session distante puis s’il
faut purger ses fichiers. Refuser la purge est le bon choix lorsqu’on arrête à
cause d’un bug et que l’on veut conserver les éléments pour une relance.

Lire le [guide canonique de l’exécution distante](remote.fr.md), notamment
[arrêt ciblé et conservation des fichiers](remote.fr.md#ctrlc-arrêt-ciblé-et-conservation-des-fichiers)
et [purge distante sûre](remote.fr.md#purge-distante-sûre), pour les sessions,
la reconnexion, reprise/redémarrage, synchronisation, préparation VM et
répartition multi-VM.

## Bootstrap et maintenance autonome

Ces options sont consommées avant le parseur du mode :

| Option | Défaut / effet |
|---|---|
| `--bootstrap auto\|pip\|none` | `auto` ; utilise le venv privé de lidar2map, installe dans l’environnement actif ou n’installe aucune dépendance. `LIDAR2MAP_BOOTSTRAP` fournit un défaut de priorité inférieure. |
| `--help-bootstrap` | Affiche l’aide du bootstrap puis quitte. |
| `--installer-deps` | Installe les dépendances critiques et optionnelles de build/runtime puis quitte. |
| `--telecharger-outils` | Télécharge le JRE Temurin, osmosis et mapwriter puis quitte. |
| `--desinstaller` | Supprime le runtime extrait, le venv privé, le JRE et osmosis de lidar2map ; ne supprime ni le script, ni l’exécutable, ni l’archive de release, ni les projets, ni les données utilisateur partagées hors de ces emplacements runtime. |
| `--smoketest` | Lance les petits pipelines de validation intégrés. Il télécharge de vraies données et peut durer plusieurs minutes avec un cache vierge. |

Alias historiques du bootstrap : `--no-bootstrap` → `none`, `--venv` → `auto`
et `--no-venv` → `pip`.

## Alias français

Les options anglaises canoniques sont recommandées dans les scripts. Les alias
de compatibilité suivants sont acceptés par les parseurs actuels :

| Canonique | Alias |
|---|---|
| `--lidar`, `--raster`, `--vector`, `--merge`, `--split` | `--ignlidar`, `--ignraster`, `--ignvecteur`, `--fusionner`, `--decouper` |
| `--zone-city`, `--zone-department`, `--zone-width`, `--zone-name` | `--zone-ville`, `--zone-departement`, `--zone-largeur`, `--zone-nom` |
| `--output-dir`, `--cache-dir`, `--production-dir`, `--tiles-dir` | `--dossier`, `--dossier-cache`, `--dossier-production`, `--dossier-dalles` |
| `--api-key`, `--layer` | `--apikey`, `--couche` |
| `--download`, `--download-force`, `--download-overwrite`, `--download-compress` | `--telechargement`, `--telechargement-forcer`, `--telechargement-ecraser`, `--telechargement-compresser` |
| `--shadings`, `--shading-elevation`, `--shadings-overwrite`, `--shadings-compress` | `--ombrages`, `--ombrages-elevation`, `--ombrages-ecraser`, `--ombrages-compresser` |
| `--file-formats`, `--image-format`, `--image-quality`, `--tiles-overwrite` | `--formats-fichier`, `--formats-image`, `--qualite-image`, `--tuiles-ecraser` |
| `--split-cols`, `--split-rows`, `--split-width`, `--block` | `--cols-decoupe`, `--rows-decoupe`, `--split-largeur`, `--bloc` |
| `--cleanup`, `--min-free-gb`, `--vector-simplify` | `--nettoyage`, `--min-disque-go`, `--simplification-vecteur` |
| `--tiles-purge-invalid`, `--tiles-purge-out-of-zone` | `--dalles-purger-invalides`, `--dalles-purger-hors-zone` |
| `--output-file`, `--index-sheet` | `--sortie`, `--planche` |

Les actions booléennes proposent aussi leur forme négative anglaise, notamment
`--no-download`, `--no-download-compress`, `--no-svf-sweep` et
`--no-index-map`. `--shadings all`/`none` et
`--shadings tous`/`aucun` forment deux paires équivalentes.

## Codes de sortie utiles aux scripts

| Code | Signification |
|---:|---|
| `0` | Traitement terminé avec succès. |
| `1` | Échec de traitement ou sortie partielle dans la plupart des workflows locaux. |
| `2` | Erreur du parseur d’arguments. |
| `3` | Arrêt propre avant un morceau provoqué par `--min-free-gb`. |
| `130` | Interruption utilisateur (`Ctrl+C`). |

Le contrôleur distant distingue aussi les erreurs SSH, de surveillance et de
synchronisation ; voir le [guide distant](remote.fr.md).

---

[Index de la documentation](README.fr.md) ·
[Bien démarrer](getting-started.fr.md) · [Formats](formats.fr.md) ·
[Fournisseurs](providers.fr.md) · [Visualisations](shadings.fr.md)
