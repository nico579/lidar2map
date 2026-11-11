# Mapterhorn, Sonny et services comparables

Évaluation du 3 octobre 2026 pour lidar2map. Le [catalogue des providers](providers.fr.md)
reste la référence utilisateur ; cette page conserve les décisions et leurs preuves.

Le périmètre est la prospection archéologique à partir de LiDAR précis. Les
nouveaux providers doivent préserver le microrelief, avec priorité aux sources
LiDAR natives à 0,5–1 m et aux nuages classés denses. Résolution réelle, précision
verticale et effets des traitements doivent être vérifiés. L'onglet Raster sert
aux fonds de cartes et aux orthophotos. L'accès à un modèle d'altitude mondial
grossier ne justifie pas un nouveau provider LiDAR.

## Candidats et statut de validation

| Prototype | Données utilisées | Accès testé | Statut |
|---|---|---|---|
| `be-wallonie` | MNT LiDAR SPW 2021–2022, source 0,5 m | Mapterhorn Terrarium WebP z17, source `bewallonie`, grille EPSG:3812 à 0,5 m | Retiré : conservation du microrelief non qualifiée |
| `sk-ugkk` | DMR 5.0 LiDAR ÚGKK, source 1 m | Mapterhorn Terrarium WebP z16, source `sk`, grille EPSG:5514 à 1 m | Retiré : conservation du microrelief non qualifiée |
| `de-sachsen` | DGM1 GeoSN natif, 1 m | ZIP GeoTIFF officiel de 2 km, EPSG:25833 à 1 m | Candidat natif, ajout soumis à validation de l'utilisateur |

Les trois prototypes sont conservés dans [tools/provider_candidates](../tools/provider_candidates/)
et sont exclus du catalogue actif, de la GUI/CLI et de la carte de couverture.
Tout nouvel ajout nécessite désormais la validation explicite de l'utilisateur.
Un téléchargement correct et un export LRM/SVF valide prouvent le fonctionnement
du code, pas la précision archéologique des données.

Le [MNT wallon natif](https://geoportail.wallonie.be/catalogue/a004e570-99d6-4fe5-b83d-49b774409278.html)
est décrit comme non lissé, avec une grille à 0,5 m et une précision altimétrique
absolue de l'ordre de 0,12 m. Ces propriétés concernent la donnée officielle et
ne peuvent pas être transférées sans preuve au produit transformé de Mapterhorn.
Ni la Wallonie ni la Slovaquie n'ont été comparées à leur MNT natif dans cette
évaluation. La résolution 0,5/1 m des grilles de calcul ne constitue donc pas
une qualification de leur précision après transformation.

Les références producteur sont le [MNT wallon](https://geoportail.wallonie.be/catalogue/a004e570-99d6-4fe5-b83d-49b774409278.html),
le [DMR slovaque](https://www.geoportal.sk/sk/zbgis/lls-dmr/) et le
[DGM GeoSN](https://www.geodaten.sachsen.de/downloadbereich-digitale-hoehenmodelle-4851.html).
Les crédits SPW et ÚGKK (CC BY 4.0), GeoSN (dl-de/by-2-0) et Mapterhorn figurent
dans les prototypes. Leur ajout à la documentation du catalogue actif reste
soumis à la validation des candidats ; la [page des licences](data-licenses.fr.md)
existante n'a pas été modifiée.

## Comment l'accès Mapterhorn fonctionne

[Mapterhorn distribue](https://mapterhorn.com/data-access/) des altitudes
encodées en Terrarium dans des WebP de 512×512 pixels, par URL XYZ ou archives
PMTiles. Le prototype `tools/provider_candidates/_mapterhorn.py` utilise l'URL
`https://tiles.mapterhorn.com/{z}/{x}/{y}.webp` et décode les mètres avec
`R × 256 + G + B / 256 − 32768`. Il vérifie format, dimensions et coordonnées
avant une conversion atomique en GeoTIFF Float32.

La découverte et le masque utilisent les polygones de source de la couche MVT
`coverage`, au zoom 14, servis à
`https://single-archive-tiles.mapterhorn.com/coverage/14/{x}/{y}.mvt`.
Seuls les pixels de `bewallonie` ou `sk` sont retenus ; le reste devient NoData.
Le fond mondial GLO-30 ne doit pas être présenté comme du LiDAR fin. Ce masque
vectoriel est généralisé : il ne garantit pas une provenance exacte pixel par
pixel aux limites ni l'absence de mélange près des raccords. Son endpoint est
une dépendance externe supplémentaire, vérifiée lors de cette évaluation.

Les tuiles Mercator sont reprojetées bilinéairement sur une grille métrique
locale, alignée globalement, avant LRM/SVF. À 50° de latitude, une distance en
EPSG:3857 est environ 1,56 fois la distance au sol : l'utiliser directement
fausserait les rayons exprimés en mètres et les pentes. Le pas de la grille
locale n'ajoute pas d'information à la source.

Les [pipelines de Mapterhorn](https://github.com/mapterhorn/mapterhorn/blob/main/pipelines/README.md)
reprojettent les données et raccordent les sources ; leur arrondi dépend du
zoom (1/32 m au z16, 1/64 m au z17). Même avec une image sans perte, le produit
distribué n'est donc pas une copie exacte du MNT natif. Il ne contient pas le
nuage classé nécessaire au mode DFM.

## Saxe : accès natif retrouvé

Le [catalogue des sources Mapterhorn](https://github.com/mapterhorn/mapterhorn/tree/main/source-catalog)
a orienté la recherche, mais ses anciennes URL saxonnes de 1 km renvoient 404.
La [page officielle de téléchargement par lot](https://www.geodaten.sachsen.de/batch-download-4719.html)
contient `batchConfig.products` et `batchConfig.mapping`. Le prototype lit le
produit `DGM1_TIFF_2km`, son partage public et la grille compressée, agrège les
cellules de 1 km en dalles de 2 km puis applique les exceptions de disponibilité.
Il met cet index en cache pendant sept jours.

Un GET anonyme vers `public.php/dav/files/<share>/<filename>` fournit le ZIP.
Le test réel a téléchargé `dgm1_33410_5656_2_sn_tiff.zip` (13,35 Mo), contenant
un GeoTIFF 2000×2000 Float32 à 1 m, EPSG:25833, NoData −9999. Le nom du membre
ZIP n'est jamais utilisé comme chemin d'extraction ; CRS, dimensions, résolution
et emprise sont contrôlés avant remplacement du fichier local.

## Vérifications et comparaison

Une [comparaison isolée avec le provider IGN LiDAR HD](mapterhorn-ign-comparaison/README.fr.md)
a ensuite été réalisée sur trois zones françaises, aux zooms 17 et 16, avec
contrôles de grille, d'altitude, LRM et SVF. Au z17, les écarts d'altitude RMSE
sont de 1,6 à 3,0 cm ; l'écart-type des variations fines du LRM sigma 2 m est
réduit de 9,3 à 11,7 %. Ce sont des différences entre produits, pas une
précision absolue terrain. Ce test ne qualifie ni Wallonie ni Slovaquie et
n'active aucun candidat.

Avant leur retrait du catalogue, les trois prototypes ont passé le smoke test
réseau : découverte, téléchargement, conversion et lecture de véritables
altitudes. Trois workflows CLI complets ont
produit chacun des MBTiles LRM (`sigma=10 m`) et SVF (`dist=15 m`, `gamma=1`),
avec contrôle d'intégrité SQLite et tuiles non vides. Les 19 suites rapides et
les six suites scientifiques ont réussi ; les 15 tests ciblés des deux nouveaux
adaptateurs couvrent notamment
les masques, NoData, reprojection métrique, emprises, erreurs réseau et écritures
atomiques. Ces tests ne valident pas la préservation de structures archéologiques.
Les figures de couverture ne présentent désormais aucun de ces trois candidats.

Le contrôle visuel des sorties expérimentales a montré des bandes vides lors
de l'assemblage des dalles reprojetées. Une correction du VRT avait été testée
pendant l'investigation ; elle a été annulée à la demande de l'utilisateur de
ne toucher qu'aux ajouts de cette intervention et de conserver les comportements
préexistants validés. Les tests des candidats restent dans
`tools/provider_candidates/tests/` et ne modifient pas le registre des tests
du projet.

Une comparaison à Dresde porte sur 79 545 pixels : DGM1 natif et tuile
Mapterhorn `16/35268/21925` reprojetés bilinéairement sur la même grille EPSG:25833 à 1 m,
en écartant les bordures de 40 pixels. LRM brut à sigma 10 m et SVF brut à
rayon 15 m, 16 directions, sont calculés avec les fonctions du projet.

| Mesure sur cet échantillon | Résultat |
|---|---:|
| Décalage médian d'altitude, Mapterhorn − natif | +0,0217 m |
| RMSE des altitudes | 0,1031 m |
| 95e percentile de l'écart absolu d'altitude | 0,1190 m |
| RMSE LRM | 0,0919 m |
| Corrélation LRM | 0,707 |
| RMSE SVF, valeur brute sans unité | 0,0135 |

Ce résultat concerne un seul site, relativement plat. Des différences de
millésime peuvent contribuer aux écarts ; il ne permet pas d'attribuer toute
la différence au traitement Mapterhorn ni de généraliser aux autres pays.
Il montre néanmoins que des altitudes proches peuvent donner un LRM différent.
Pour une analyse fine, conserver le natif lorsqu'il est accessible.

Avant de proposer les prototypes Mapterhorn à la validation, comparer leurs
altitudes et LRM/SVF au MNT natif de la même campagne sur plusieurs sites avec
du microrelief connu, dont un site boisé et un raccord de sources. Documenter
l'atténuation des structures, les artefacts, la précision verticale et la
provenance réelle. Une comparaison d'altitudes sur un unique site relativement
plat en Saxe ne qualifie pas les produits Wallonie ou Slovaquie.

## Peut-on simplifier les providers existants ?

Oui pour l'accès aux MNT LiDAR : un adaptateur Terrarium commun et quelques
paramètres de région peuvent remplacer des particularités WCS, STAC, index ou
authentification, à condition de préserver les détails utiles à l'archéologie.
Les candidats suivants sont des pistes d'étude, sans ajout ni remplacement
prévu sans qualification et accord de l'utilisateur. Les
résolutions et couvertures annoncées sont celles du [catalogue Mapterhorn](https://mapterhorn.com/),
consulté le 3 octobre 2026.

| Providers existants | Gain possible | Décision proposée |
|---|---|---|
| Danemark `dk-datafordeler`, Finlande `fi-maanmittauslaitos`, Suède `se-lantmateriet` | Éviter clé/compte pour le MNT ; sources annoncées à 0,4 m, 2 m et 1 m | Conserver les providers natifs ; variante uniquement après qualification et accord de l'utilisateur |
| Länder allemands en DGM1 | Mutualiser les accès en tuiles | Garder les accès natifs qui fonctionnent ; mesurer LRM/SVF avant substitution |
| Portugal `pt-dgt` | Éviter l'authentification sur certaines zones | Conserver le natif ; couverture Mapterhorn partielle et conservation du microrelief non qualifiée |
| Pays-Bas `nl-ahn`, Suisse `ch-swisstopo` | URL unique | Garder le natif 0,5 m : Mapterhorn annonce 5 m aux Pays-Bas, 2 m en Suisse avec certains secteurs à 0,5 m |
| Jumeaux LAZ / mode DFM | Aucun gain pour les retours non-sol | Conserver les nuages classés nationaux |

Pour tout nouvel usage, vérifier l'emprise de source et comparer les véritables
altitudes et reliefs ; une taille de pixel affichée ne prouve pas la résolution
effective. Conserver [les attributions des producteurs et de Mapterhorn](https://mapterhorn.com/attribution/).

## Sonny

[Sonny](https://sonny.4lima.de/) construit des modèles européens notamment à
partir de LiDAR. Ses produits de diffusion sont des HGT à 1″/3″, des GeoTIFF à
20/50 m et des GeoTIFF à 10 m en Autriche/Suisse. Leur résolution ne suffit pas
au microrelief archéologique visé par lidar2map. Sonny est écarté des nouveaux
providers LiDAR.

## Services comparés et décision pour l'archéologie

| Service | Ce qui ressemble à Mapterhorn | Intérêt et limite pour lidar2map |
|---|---|---|
| [Terrain Tiles / Mapzen / Tilezen sur AWS](https://registry.opendata.aws/terrain-tiles/) | Agrégat mondial ouvert, tuiles d'altitude sur S3, format Terrarium disponible | Écarté comme nouveau provider LiDAR générique : les [sources publiées](https://github.com/tilezen/joerd/blob/master/docs/data-sources.md) sont généralement plus grossières en Europe (EUDEM 30 m, Autriche/Norvège 10 m ; Royaume-Uni 2 m), sans garantie de LiDAR sol-nu fin partout |
| [MapTiler Terrain RGB](https://docs.maptiler.com/schema-raster/terrain-rgb/) | Mosaïque mondiale d'altitude en WebP | Écarté comme source de prospection fine : 30 m mondialement, 5 m dans certains secteurs selon la documentation |
| [OpenTopography](https://opentopography.org/developers) | Catalogue international, API de modèles d'altitude et catalogue STAC ; collections LiDAR locales | Retenir uniquement des collections LiDAR fines dont l'origine, la densité, la précision et l'accès sont vérifiés. Modèles mondiaux grossiers écartés ; clés et quotas selon l'API, USGS 1 m actuellement réservé aux utilisateurs académiques |
| [Mapbox Terrain-DEM](https://docs.mapbox.com/data/tilesets/reference/mapbox-terrain-dem-v1/) | Terrain mondial encodé en RGB pour le rendu | Aucun provider archéologique retenu : disponibilité dans les SDK uniquement et absence de validation d'un LiDAR fin pour nos zones. Terrain-RGB dispose d'une [API distincte](https://docs.mapbox.com/data/tilesets/guides/access-elevation-data/), ce qui ne démontre pas sa précision pour le microrelief |

Pour ce projet, Mapterhorn peut ouvrir des régions LiDAR fines sans compte,
après validation de la conservation du microrelief. OpenTopography mérite une
recherche ciblée sur ses collections LiDAR haute résolution. La simplicité
d'accès et la couverture mondiale ne compensent pas une perte de précision.

Le [bilan des pays absents du catalogue actif](mapterhorn-pays-manquants.fr.md)
croise les 151 sources Mapterhorn consultées le 3 octobre 2026 avec les
66 providers actifs. Il distingue trois candidats à qualifier (Slovaquie,
Roumanie, Chypre) de quatre sources trop grossières pour le microrelief.
Une dalle LAKI II du stock Mapterhorn est à 1 m malgré l'annonce de 0,5 m.
