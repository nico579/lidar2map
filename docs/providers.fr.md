*[English](providers.md) | **Français** · [Index de la documentation](README.fr.md)*

# Providers LiDAR et couverture

Cette page est le catalogue utilisateur des sources LiDAR et altimétriques
actuellement intégrées à lidar2map. Elle rassemble le code à sélectionner, la
résolution nominale, le système de coordonnées natif, la couverture, les
identifiants requis et les contraintes propres à chaque source.

Pour les sources évaluées mais non intégrées et l'historique technique des
décisions, voir la [roadmap des providers](lidar_providers_roadmap.md). Pour
ajouter une source, voir
[Contribuer un provider LiDAR](contributing-providers.fr.md).

## Sélectionner un provider

- Dans la GUI, utiliser la liste des providers en haut du formulaire LiDAR.
- Dans chaque commande CLI LiDAR, passer explicitement `--provider <code>`.
- `LIDAR2MAP_PROVIDER` ne remplace pas cet argument CLI obligatoire.

Utiliser `fr-ign` pour la France métropolitaine. Les codes terminés par `-laz`
dans le tableau sont des jumeaux internes pour les nuages de points :
sélectionner normalement le provider parent, puis activer le **mode DFM** dans
la GUI ou passer `--laz` en CLI.

## Comptes et clés API

La majorité des providers ne demandent aucun compte. Les exceptions exposées à
l'utilisateur sont :

| Provider | Identifiant | Comment le fournir | Remarques |
|---|---|---|---|
| `se-lantmateriet` | Compte GeoTorget gratuit | `LANTMATERIET_USER` et `LANTMATERIET_PASS` | Le catalogue STAC est public ; les identifiants protègent le serveur de téléchargement. |
| `fi-maanmittauslaitos` | Clé API gratuite du National Land Survey | `--api-key <clé>` ou `NLS_FINLAND_API_KEY` | Requise pour les téléchargements WCS. |
| `dk-datafordeler` et son mode LAZ | Clé API Datafordeler gratuite | `--api-key <clé>` ou `DATAFORDELER_API_KEY` | Même clé pour le MNT raster et le nuage de points. |
| `pt-dgt` | Compte DGT gratuit | `DGT_USER` et `DGT_PASS` | Authentification par identifiant/mot de passe, pas par le paramètre de clé API. |
| `us-3dep` | Clé API OpenTopography gratuite | `--api-key <clé>` ou `OPENTOPOGRAPHY_API_KEY` | Pour le 1 m public sans compte, préférer `us-tnm`. `OPENTOPOGRAPHY_DATASET` choisit le produit OpenTopography ; `USGS1m` demande le 1 m, tandis que le repli par défaut du provider est `USGS10m`. |

Le chemin LAZ/DFM de `us-3dep` utilise le nuage public Planetary Computer et
ne demande pas de compte OpenTopography.

## Couverture

![Carte de couverture LiDAR lidar2map](../coverage.fr.png)

La carte colorée résume les couvertures nationales et régionales disponibles.
Son GeoJSON interactif affiche le `NAME` et le code provider de chaque zone au
clic :

🗺️ **[Ouvrir la carte de couverture interactive](../coverage.geojson)**.
GitHub la rend directement ; on peut aussi la glisser dans
[geojson.io](https://geojson.io) ou QGIS pour tester un point.

La carte est régénérée par `coverage_map.py` depuis les titres de zones de
`providers/*.py` : la carte et la GUI partagent donc la même source.

### USA et Canada

**🇺🇸 Les USA et 🇨🇦 le Canada sont supportés et fonctionnels, mais ne sont pas
tracés comme des polygones nationaux pleins.** `us-tnm` / `us-3dep` (3DEP) et
`ca-nrcan` (HRDEM) ont une couverture par projet ou population, pas une
couverture nationale mur-à-mur. Dessiner tout le pays sur-revendiquerait la
disponibilité.

Vérifier une zone américaine avec le
[TNM Downloader](https://apps.nationalmap.gov/downloader/). Les tuiles sources
USGS 1 m sont des COG de 10 × 10 km, mais lidar2map ne lit que la fenêtre de la
bbox demandée via `/vsicurl/` ; il ne télécharge pas chaque tuile source
complète.

## Providers disponibles

La résolution est nominale et la couverture exacte peut varier à l'intérieur
de la zone annoncée.

| Code | Pays | Donnée | Rés. | CRS natif | Accès & particularités |
|---|---|---|---|---|---|
| `fr-ign` | France | IGN LiDAR HD | 0.5 m | EPSG:2154 (Lambert-93) | TMS vectoriel PBF + WMS GetMap, couverture nationale (métropole) |
| `fr-reunion` · `fr-guadeloupe` | France (Réunion, Guadeloupe DROM) | IGN LiDAR HD | 0.5 m | EPSG:2975 / 5490 (UTM40S / UTM20N) | Index WFS `IGNF_MNT-LIDAR-HD:dalle` (chaque dalle porte son `url` de téléchargement direct), GeoTIFF 0,5 m, Licence Ouverte 2.0 (Martinique/Mayotte annoncées mais WFS vide pour l'instant) |
| `fr-ign` + **mode DFM** | France (**mode alternatif « ruines debout »**) | DFM depuis le nuage classé LiDAR HD | 0,5 m | EPSG:2154 (Lambert-93) | Case « mode DFM » dans la GUI (ou CLI `--laz`) : télécharge les dalles **COPC LAZ** (~205 Mo/km²) et reconstruit le modèle depuis le socle par défaut `--laz-ground classes` (ensemble `1,2,3,4,9,66` : 2/9/66 = socle terrain comme le MNT officiel, les autres réinjectées dans les trous du sol) ou `--laz-ground csf`. **Peut réintroduire des retours compatibles avec des murs debout** que le MNT efface (candidats, pas une classification de murs : le maquis revient aussi). Réglages complets : `--laz-hmin/-hmax/-classes` et `--laz-csf-*` ; lancer `python lidar2map.py --help` pour la référence CLI actuelle. Nom de zone auto-suffixé (`_laz_dfm` / `_laz_csf`) : les sorties MNT et nuage ne se mélangent jamais. Le LAZ reste dans le cache : changer les réglages reconvertit sans retélécharger. Prospection ciblée de quelques km², pas de grandes cartes |
| `nl-ahn` | Pays-Bas | AHN4/5 | 0.5 m | EPSG:28992 (RD New) | ATOM feed + JSON FeatureCollection, couverture nationale |
| `ch-swisstopo` | Suisse | swissALTI3D | 0.5 m | EPSG:2056 (CH1903+/LV95) | STAC API REST, couverture nationale |
| `ch-swisstopo` + **mode DFM** | Suisse (**mode alternatif « structures debout »**) | DFM depuis le nuage classé swissSURFACE3D | 0,5 m | EPSG:2056 (CH1903+/LV95) | Case « mode DFM » (ou CLI `--laz`) sur le provider suisse : télécharge les tuiles **swissSURFACE3D `.las.zip`** (~125 Mo/km²) via la même API STAC, dézippe le nuage et reconstruit le modèle « structures debout ». Socle par défaut = **CSF** (`--laz-ground csf`, Cloth Simulation Filter), car les codes de classification swisstopo ne sont pas garantis compatibles IGN ; le mode `classes` reste disponible. Mêmes réglages par site et cache-puis-réajuste que le DFM France (~6 min/tuile). Prospection ciblée, validation terrain conseillée |
| **+ mode LAZ (autres providers)** | Pologne, Estonie, Flandre, Canada (NRCan + Québec), USA, Danemark, France (CRAIG Auvergne) | DFM/CSF depuis les nuages classés nationaux | 0,5 m | *(CRS de chaque provider)* | Le **mode LAZ** (`--laz`) marche aussi là où le nuage de points classé complet est publié : `pl-gugik-laz`, `ee-maaamet-laz`, `be-flanders-laz`, `ca-nrcan-laz` (COPC fenêtré), `us-3dep-laz` (COPC fenêtré, sans compte), `ca-quebec-laz`, `dk-datafordeler-laz` (clé API), `fr-craig-laz`. Densité, classes et CRS varient. Voir la [roadmap des providers](lidar_providers_roadmap.md). Traitement alternatif pour une prospection ciblée ; validation terrain conseillée |
| `no-kartverket` | Norvège | Nasjonal Høydemodell | 1 m | EPSG:25833 (UTM33N) | ArcGIS ImageServer exportImage, couverture nationale |
| `se-lantmateriet` | Suède | Markhöjdmodell (laser) | 1 m | EPSG:3006 (SWEREF99 TM) | STAC + COG mosaïque 10 km (lecture fenêtrée), couverture nationale ; **compte GeoTorget gratuit** (`LANTMATERIET_USER` / `LANTMATERIET_PASS`) requis pour le téléchargement |
| `de-bayern` · `de-nrw` · `de-niedersachsen` · `de-rlp` | Allemagne (4 Länder : Bavière, RNW, Basse-Saxe, Rhénanie-Palatinat) | DGM1 | 1 m | EPSG:25832 (UTM32N) | metalink / index.json / STAC COG, données ouvertes (de-rlp : index Metalink d'environ 21k tuiles GeoTIFF ; `post_fetch` retire le CRS vertical composé pour revenir à 25832) |
| `de-thueringen` · `de-berlin` · `de-sh` | Allemagne (Thuringe, Berlin, Schleswig-Holstein) | DGM / DGM1 | 1–2 m / 1 m | EPSG:25832 / 25833 (UTM32N/33N) | Index spatial (ATOM ou GeoJSON) → tuiles XYZ texte (`post_fetch` → GeoTIFF), données ouvertes (Thuringe/SH CC BY / dl-de/by-2-0, Berlin dl-de/zero-2-0) |
| `de-hessen` · `de-bw` · `de-mv` · `de-st` · `de-brandenburg` | Allemagne (Hesse, Bade-Wurtemberg, Mecklembourg-Poméranie, Saxe-Anhalt, Brandebourg) | DGM1 | 1 m | EPSG:25832/25833 (UTM32N/33N) | WCS 2.0.1 INSPIRE GetCoverage, données ouvertes dl-de/by-2-0 (de-mv/de-st trouvés via l'auto-découverte du catalogue GDI-DE) |
| `at-bev` | Autriche (national) | ALS-DGM | 1 m | EPSG:3035 (LAEA Europe) | Index ATOM + COG mosaïque 50 km (lecture fenêtrée via `/vsicurl`), millésime le plus récent par tuile, CC BY 4.0 (BEV) |
| `at-tirol` · `at-osttirol` | Autriche (Tyrol + Osttirol) | DGM | 0.5 m | EPSG:31254/31255 (MGI M28/M31) | WCS 1.0.0 GetCoverage (tiris), plus fin que `at-bev` sur le Tyrol |
| `gb-england` · `gb-wales` | Royaume-Uni | LIDAR Composite DTM | 1 m | EPSG:27700 (OSGB36) | WCS 2.0.1 / catalogue WFS (EA / NRW) |
| `gb-scotland` | Royaume-Uni (Écosse) | LiDAR secteur public écossais (DTM) | 0,5 m | EPSG:27700 (OSGB36) | Bucket AWS S3 public (sans compte), listing de tuiles OS-grid (`ListObjectsV2`) → COG, couverture 50 cm moderne (programme national + Orcades) |
| `be-flanders` | Belgique (Flandre + Bruxelles) | DHMV II DTM | 1 m | EPSG:31370 (Lambert 1972) | WCS 2.0.1 ; expose aussi SVF 25 cm et hillshade multi 25 cm précalculés |
| `lu-act` | Luxembourg | BD-L-Lidar 2024 (MNT) | 0,5 m | EPSG:2169 (LUREF) | COG national unique (~40 Go) lu en **fenêtré** via HTTP range `/vsicurl`, sans jamais télécharger tout le fichier ; CC0 |
| `fi-maanmittauslaitos` | Finlande | Modèle d'élévation | 2 m | EPSG:3067 (TM35FIN) | WCS 2.0.1, clé API gratuite requise, couverture nationale |
| `dk-datafordeler` | Danemark | DHM DTM | 0.4 m | EPSG:25832 (UTM32N) | WCS 1.0.0, clé API gratuite requise, couverture nationale |
| `ie-gsi` | Irlande | LiDAR DTM | 1 m | EPSG:2157 (ITM) | ArcGIS FeatureServer → ZIP (`post_fetch`), ~60 % du territoire, CC BY 4.0 |
| `cz-cuzk` | Tchéquie | DMR 5G | 1 m | EPSG:5514 (S-JTSK/Krovak) | Atom INSPIRE à deux niveaux → LAZ (`post_fetch`, nécessite `lazrs`), couverture nationale |
| `si-arso` | Slovénie | DMR1 (LiDAR 2011–2015) | 1 m | EPSG:3794 (D96/TM) | Index fishnet ArcGIS REST + dalles texte x;y;z → GeoTIFF (`post_fetch`), couverture nationale |
| `ee-maaamet` | Estonie | DTM 1 m (ALS 2021–2024) | 1 m | EPSG:3301 (L-EST97) | URLs directes par feuille 1:10000 (numérotation calculée, sans index), couverture nationale, données ouvertes |
| `lv-lgia` | Lettonie | DTM 1 m (LiDAR ALS) | 1 m | EPSG:3059 (LKS-92/TM) | Index S3 d'environ 66k dalles LAS classifiées → téléchargement → binning classe 2 vers GeoTIFF avec comblement des trous (nécessite `laspy`), couverture nationale, CC BY 4.0 (emprises mesurées depuis les en-têtes LAS, grille TKS-93) |
| `es-cnig` | Espagne | MDT | 5 m | EPSG:25830 (UTM30N) | WCS 2.0.1 INSPIRE, 5 m = échelle paysage (le LiDAR sol-nu 2 m exige le portail à session CNIG) |
| `es-icgc` | Espagne (Catalogne) | MET LiDAR | 0,5 m | EPSG:25831 (UTM31N) | COG régional unique (~433 Go) lu en **fenêtré** via HTTP range `/vsicurl`, 50 cm, bien plus fin que `es-cnig` 5 m ; CC BY 4.0 (ICGC) |
| `es-euskadi` | Espagne (Pays basque) | MDT LiDAR | 1 m | EPSG:25830 (UTM30N) | WCS 1.0.0 (ArcGIS MapServer WCSServer, geoEuskadi), 1 m sol-nu, bien plus fin que `es-cnig` 5 m ; CC BY 4.0 |
| `es-navarra` | Espagne (Navarre) | MDT LiDAR | 2 m | EPSG:25830 (UTM30N) | WCS 2.0.1 INSPIRE (IDENA), 2 m sol-nu, NoData 3.4e38 ; CC BY 4.0 |
| `pt-dgt` | Portugal | MDT LiDAR (2024) | 0,5 m | EPSG:3763 (PT-TM06) | OGC API + POST `/search` (CQL2), couverture nationale ; **compte DGT gratuit** (`DGT_USER` / `DGT_PASS`) requis pour le téléchargement authentifié |
| `it-emilia-romagna` | Italie (Émilie-Romagne) | DTM (RER) | 5 m | EPSG:7791 (RDN2008/UTM32N) | WCS 2.0.1 GetCoverage, couverture régionale, CC BY 4.0 (le LiDAR 0,5 m 2023/24 sera servi quand sa couverture sera complète) |
| `it-sardegna` | Italie (Sardaigne) | DTM (RAS) | 1 m | EPSG:7791 (RDN2008/UTM32N) | WCS 2.0.1 GetCoverage (GeoServer), mosaïque LiDAR de l'île entière avec des trous (côtes, villes, Gallura, bandes fluviales), nodata propre hors couverture, CC BY 4.0 |
| `it-piemonte` | Italie (Piémont) | DTM (LiDAR ICE) | 5 m | EPSG:32632 (UTM32N) | WCS 1.0.0 GetCoverage (MapServer), `format=image/tiff` pour le vrai Float32 (`GTiff` retourne un UInt8 quantifié), NoData -99, CC BY 4.0 |
| `pl-gugik` | Pologne | NMT (projet ISOK) | 1 m | EPSG:2180 (PUWG 1992) | WCS 2.0.1, données ouvertes, couverture nationale |
| `ca-nrcan` | Canada | HRDEM Mosaic | 1 m | EPSG:3979 (LCC Canada) | STAC + COG mosaïque (lecture fenêtrée), ~95 % de la population |
| `us-tnm` · `us-3dep` | USA | 3DEP | 1 m | EPSG:3857 | TNMAccess S3 direct (sans compte) / OpenTopography (clé gratuite) |
| `us-cnmi` | Îles Mariannes du Nord (territoire US) | Topobathy DEM | 1 m | EPSG:8693 (NAD83(MA11)/UTM55N) | Mosaïque NOAA **VRT** unique lue en fenêtré via `/vsicurl` (bucket `noaa-nos-coastal-lidar-pds`), sol-nu par classe sol à terre + bathymétrie en mer, domaine public (patron d'un provider NOAA générique) |
| `jp-gsi` | Japon (partiel) | DEM5A (GSI 標高タイル) | 5 m | EPSG:3857 | **Tuiles XYZ texte** d'altitude ouvertes, sans compte (`post_fetch` → GeoTIFF), couverture 5 m partielle (cours d'eau, plaines, zones habitées) |
| `ph-taal` | Philippines (zone du volcan Taal seulement) | DTM 1 m (UP TCAGP) | 1 m | EPSG:32651 (UTM51N) | Grille de tuiles GeoJSON statique → GeoTIFF direct sur S3 (`<GRIDREF>_DTM.tif`), environ 20 km autour du volcan Taal, données ouvertes |
| `nz-linz` | Nouvelle-Zélande | DEM national seamless | 1 m | EPSG:2193 (NZTM2000) | STAC LINZ S3 + COG (lecture fenêtrée) |
| `au-qld` · `au-nsw` | Australie (QLD 0.5 m · NSW 5 m) | DEM LiDAR | 0.5–5 m | EPSG:3857 | ArcGIS ImageServer (ELVIS), couverture **par État** |
| `au-ga` | Australie (national, dispersé) | DEM dérivé LiDAR | 5 m | EPSG:3857 (servi en 4283) | WCS 1.0.0 GetCoverage (Geoscience Australia) → reprojeté au téléchargement, ~245 000 km² dans tous les États (littoral + Murray-Darling), ouvre SA/VIC/TAS/WA au-delà de QLD/NSW |

## Sources évaluées et futures

La [roadmap des providers](lidar_providers_roadmap.md) consigne chaque source
évaluée, y compris celles écartées faute d'endpoint programmable, parce
qu'elles ne servent que des images rendues, à cause d'une couverture ou d'une
résolution insuffisante, ou d'une licence incompatible. Elle indique aussi les
candidats à réexaminer.

Pour proposer ou intégrer une source, suivre
[Contribuer un provider LiDAR](contributing-providers.fr.md).
