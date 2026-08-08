# Formats de sortie et applications mobiles

*[English](formats.md) | **Français** · [Index de la documentation](README.fr.md)*

Les formats produits ne sont pas interchangeables. Choisissez le format de
l’application cible avant de lancer un traitement important. Pour
l’installation et le parcours graphique, voir
[Bien démarrer](getting-started.fr.md).

## Familles de cartes

### LiDAR et cartes raster

Les visualisations du relief LiDAR et les imageries classiques sont écrites
sous forme de cartes raster tuilées. Les sources raster classiques comprennent :

- **IGN, France uniquement :** Plan IGN, orthophotos actuelles, orthophotos
  historiques de 1950, 1965 et 1980, cartes d’État-Major du XIXe siècle,
  imagerie satellite Pléiades, infrarouge couleur et autres couches IGN.
- **USGS, USA (`--layer naip`) :** imagerie aérienne dérivée de NAIP dans le
  domaine public, d’environ 1 m. Le cache est complet jusqu’au zoom 16 et
  complète le LiDAR 3DEP du fournisseur `us-tnm`.

Les livrables raster peuvent être des MBTiles, des SQLiteDB OsmAnd/RMaps ou des
RMAP.

Pour le raster IGN, `--provider fr-ign` utilise WMTS et `--layer` accepte un
alias ou l’identifiant WMTS complet. `planign` est l’alias par défaut. Les alias
publics sont :

| Famille | Alias raster IGN |
|---|---|
| Topographie | `planign etatmajor40 etatmajor10 pentes` |
| Imagerie | `ortho ortho_1950 ortho_1965 ortho_1980 ortho_irc pleiades spot edugeo_marseille_1969 edugeo_marseille_1980 edugeo_marseille_1987 edugeo_marseille_1988 edugeo_marseille_2010 edugeo_toulon_1972` |
| Thématique | `cadastre ombrage` |

Les alias professionnels `scan25`, `scan25tour`, `scan100` et `scanoaci`
exigent une clé `cartes.gouv.fr` fournie avec `--api-key` ; les couches
publiques n’en ont pas besoin. Pour l’imagerie des USA, utiliser
`--provider us-tnm --layer naip`. Le téléchargement raster utilise huit
connexions parallèles par défaut.

### Cartes vectorielles

lidar2map peut créer une carte OSM internationale au format Mapsforge `.map`,
ou exploiter les données vectorielles IGN BD TOPO en France. La sélection
automatique d'un extrait Geofabrik couvre actuellement la France ; pour un
autre pays, fournissez le fichier `.osm.pbf` correspondant avec `--source`.
Les données vectorielles peuvent aussi être exportées en GeoJSON.

Les sélections OSM et IGN peuvent toutes deux être rendues en
`transparent-raster` : les entités choisies, par exemple chemins, routes et
cours d’eau, sont dessinées en tuiles PNG transparentes dans un fichier
`.sqlitedb`. Ce rendu est destiné à flotter au-dessus du relief LiDAR comme
surcouche OsmAnd, puisque l’application ne sait pas superposer directement des
données vectorielles arbitraires.

Avec `--osm`, `--layer` accepte n’importe quel tag OSM libre `clé=valeur`. Si
l’option est omise, la sélection est :

```text
highway=* waterway=* boundary=administrative natural=water
natural=coastline waterway=river waterway=stream waterway=canal
```

Le catalogue graphique propose aussi `natural=*`, `landuse=*`, `building=*` et
`historic=*`. Pour une `--zone-region` française, le PBF régional Geofabrik est
déjà découpé suivant la vraie limite administrative : il est utilisé
directement au lieu d’être redécoupé sur une emprise rectangulaire.

Avec `--vector`, la couche WFS IGN par défaut est `cadastre`. Les alias
disponibles sont :

```text
cadastre cours_eau troncons_eau plans_eau detail_hydro batiments
constructions cimetieres routes chemins lignes_orog detail_orog forets
reserves lieux_dits communes rpg
```

Les téléchargements WFS IGN utilisent au maximum quatre connexions parallèles ;
au-delà, des couches commencent à échouer. `--vector-simplify M` fixe une
tolérance Douglas–Peucker en mètres ; sinon lidar2map la choisit automatiquement.

La fusion vectorielle accepte plusieurs sources GeoJSON, y compris un glob, et
peut réunir des traitements voisins ou les couches IGN et OSM d'une même zone.
`--output-file` fixe le nom du résultat. Les données fusionnées peuvent rester
en GeoJSON ou produire directement une carte Mapsforge ou une surcouche raster
transparente.

## Écrans de traitement

Les cinq workflows partagent les mêmes contrôles de zone et de sortie, mais
n'affichent que les réglages propres à la source ou à l'opération choisie.

| Raster classique | Vecteur IGN | Vecteur OSM |
|---|---|---|
| <img src="../screenshots/GUI/raster.PNG" alt="Traitement raster classique" width="300"> | <img src="../screenshots/GUI/vector_ign.PNG" alt="Traitement vectoriel IGN" width="300"> | <img src="../screenshots/GUI/vector_osm.PNG" alt="Traitement vectoriel OSM" width="300"> |

| Fusion vectorielle | Découpage raster |
|---|---|
| <img src="../screenshots/GUI/vector_merge.PNG" alt="Fusion vectorielle" width="440"> | <img src="../screenshots/GUI/raster_split.PNG" alt="Découpage raster" width="440"> |

L'écran LiDAR sur MNT figure dans [Bien démarrer](getting-started.fr.md#premier-lancement-et-parcours-graphique),
et les deux variantes LAZ/DFM dans [DFM, LAZ et CSF](dfm.fr.md#activer-le-mode-nuage-de-points).

## Compatibilité des formats

Le tableau décrit les fichiers tels que lidar2map les écrit : raster tuilé,
carte vectorielle Mapsforge ou GeoJSON d’échange.

| Format produit | Type écrit par lidar2map | Applications principales | Recommandation |
|---|---|---|---|
| **MBTiles** (`.mbtiles`) | Raster tuilé XYZ/TMS en JPEG ou PNG ; les tuiles de bord peuvent conserver de l’alpha | **Locus Map**, **OruxMaps**, **AlpineQuest**, **Guru Maps**, QGIS | Sortie raster la plus polyvalente et format recommandé pour Locus. OsmAnd ne l’utilise pas directement comme raster : demander aussi SQLiteDB ou le convertir. |
| **SQLiteDB OsmAnd/RMaps** (`.sqlitedb`) | Raster tuilé dans le schéma SQLite attendu par OsmAnd | **OsmAnd** comme carte ou surcouche, RMaps, Guru Maps et autres applications compatibles RMaps | Recommandé pour OsmAnd. `transparent-raster` stocke des tuiles PNG avec alpha pour les surcouches. Pour Locus, préférer le MBTiles de lidar2map. |
| **RMAP** (`.rmap`) | Raster géoréférencé en tuiles JPEG dans un format propriétaire | **TwoNav / CompeGPS**, **OruxMaps**, AlpineQuest ; prise en charge limitée dans Locus | Principalement destiné à TwoNav/CompeGPS. lidar2map réencode les tuiles en JPEG comme l’exige RMAP. |
| **Mapsforge** (`.map`) | Carte vectorielle OSM ou IGN au format Mapsforge | **Locus Map**, **OruxMaps** | Placer le fichier dans le dossier des cartes vectorielles de l’application. Ce n’est pas un raster. OsmAnd utilise `.obf` et ne lit pas Mapsforge. |
| **GeoJSON** (`.geojson` ou `.geojson.gz`) | Entités vectorielles : chemins, routes, rivières, bâtiments… | Import de données **Locus Map**, surcouche **Guru Maps**, **QGIS**, geojson.io et autres outils SIG | Le GeoJSON est un format d’échange, pas une carte hors connexion affichée comme un MBTiles ou un `.map`. Décompresser `.gz` si la cible ne gère pas gzip. Pour une vraie carte vectorielle Locus, utiliser Mapsforge. |

## Réglages de sortie

`--file-formats` accepte des valeurs qui dépendent du mode :

- LiDAR, raster et découpage raster : `mbtiles`, `rmap`, `sqlitedb` ;
- vectoriel et fusion vectorielle : `map`, `geojson`, `gz`,
  `transparent-raster`.

Les principaux réglages raster sont :

| Paramètre | Défaut | Effet |
|---|---|---|
| `--zoom-min` | 13 pour le LiDAR, 10 pour le raster classique | Plus faible zoom de la carte tuilée |
| `--zoom-max` | 18 pour le LiDAR, 16 pour le raster classique | Plus fort zoom de la carte tuilée |
| `--image-format` | `auto` | Choisit JPEG ou PNG ; `jpeg` et `png` sont aussi acceptés explicitement |
| `--image-quality` | 85 | Qualité JPEG de 1 à 100 |
| `--tiles-overwrite` | Désactivé | Régénère les fichiers MBTiles, SQLiteDB, RMAP ou Mapsforge existants |

`gz` écrit un GeoJSON compressé. Pendant une fusion vectorielle, `--no-gz`
demande à la place un fichier `.geojson` simple. Le découpage raster peut aussi
prendre un MBTiles existant et convertir chaque morceau obtenu en RMAP ou
SQLiteDB.

La planche d’assemblage déposée à côté de ces fichiers n’est pas elle-même un
format cartographique ; voir [Planche d’assemblage](getting-started.fr.md#planche-dassemblage).

## Envoyer un projet vers le téléphone

Après la génération, sélectionnez le bouton 📲 dans l’interface. lidar2map sert
le dossier des livrables du projet sur le réseau Wi-Fi local et affiche une URL
ainsi qu’un QR code. Scannez-le sur le téléphone, puis téléchargez les fichiers
souhaités. Rien n’est envoyé en dehors du réseau local.

L’équivalent en ligne de commande est :

```bash
lidar2map --serve --zone-name NOM_DU_PROJET
```

![Page de transfert Wi-Fi local et QR code](../screenshots/GUI/phone.PNG)

## Locus Map

- Préférer MBTiles pour un relief LiDAR ou une imagerie raster.
- Utiliser un `.map` Mapsforge pour une vraie carte vectorielle hors connexion.
- Le GeoJSON importe des entités dans le gestionnaire de données ; il ne se
  comporte pas comme un fond de carte hors connexion.
- Après le téléchargement, utiliser **Gestionnaire de cartes → Importer une
  carte → gestionnaire de fichiers**. L’action Android **Ouvrir avec** peut
  aussi fonctionner selon l’appareil et la version.

Le relief LiDAR archéologique peut être affiché directement ou en surcouche :

| SVF | Ombrage multidirectionnel superposé |
|---|---|
| <img src="../screenshots/LIDAR_Samples/Svf_LocusMap.jpg" alt="SVF affiché dans Locus Map" width="300"> | <img src="../screenshots/LIDAR_Samples/Multi_LocusMap.jpg" alt="Ombrage multidirectionnel affiché dans Locus Map" width="300"> |

## OsmAnd

- Préférer `.sqlitedb` pour une carte raster ou une surcouche.
- OsmAnd n’utilise pas directement les MBTiles lidar2map comme cartes raster.
- OsmAnd ne lit pas les `.map` Mapsforge ; il utilise son propre format
  vectoriel `.obf`.
- `transparent-raster` est la sortie adaptée aux chemins, routes, cours d’eau
  ou autres entités sélectionnées au-dessus d’une carte OsmAnd existante.

Pour afficher un relief LiDAR au-dessus de la carte standard, ouvrir
**Configurer la carte → Carte de superposition**, puis placer le curseur de
transparence approximativement au milieu.

<p align="center"><img src="../screenshots/LIDAR_Samples/LRM_OSMAND_Transparent.jpg" alt="Surcouche LRM semi-transparente dans OsmAnd" width="380"></p>

## Autres applications prises en charge

- **TwoNav / CompeGPS :** préférer RMAP.
- **OruxMaps :** accepte MBTiles, RMAP et les cartes Mapsforge.
- **AlpineQuest :** accepte MBTiles et RMAP.
- **Guru Maps :** accepte MBTiles et les SQLiteDB compatibles RMaps ; le
  GeoJSON peut servir de surcouche.
- **QGIS et outils SIG :** MBTiles convient à l’échange de rasters tuilés ;
  GeoJSON convient à l’échange vectoriel.

## Références des applications

- [Locus — formats cartographiques externes](https://docs.locusmap.app/doku.php/manual%3Auser_guide%3Amaps_external)
- [OsmAnd — formats de fichiers](https://www.osmand.net/docs/technical/osmand-file-formats/)
- [TwoNav — RMAP](https://manual.twonav.com/manual/Manual_TwoNav_Tablet_22_en.pdf)
- [OruxMaps](https://www.oruxmaps.com/index_en.html)
- [AlpineQuest](https://www.alpinequest.net/en/help/v2/maps/file-based-select)
- [Guru Maps](https://gurumaps.app/docs/intro)

---

[← Bien démarrer](getting-started.fr.md) · [Index de la documentation](README.fr.md)
