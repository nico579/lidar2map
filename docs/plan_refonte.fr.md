# Plan de refonte de `lidar2map.py`

Dernier lot déployé : 24 août 2026, **v1.46.0**. Il regroupe les phases 15h à
15s-b : téléchargements et caches terrain, transactions par morceau, tuilage et
orchestration complète des ombrages, avec façades compatibles et dépendances
reconstruites à chaque appel. Les quatre bundles Windows, Linux, macOS Intel et
macOS Apple Silicon ont été reconstruits par `release.yml`.

Ce document est la source de vérité de la modularisation de `lidar2map.py`.
Il décrit l’ordre des extractions, leur état réel et les contrôles de
non-régression requis. Une phase n’est marquée **terminée** qu’après validation
du code et de ses contrats.

## Objectif

Le fichier principal concentre encore la CLI, la GUI, les fournisseurs, les
algorithmes raster et plusieurs orchestrateurs. La refonte doit réduire ce
couplage progressivement, sans modifier en même temps le comportement métier.

Les règles suivantes sont obligatoires :

- conserver `lidar2map.py` comme façade compatible pendant la transition ;
- réexporter les noms historiques utilisés par les runners et les tests ;
- extraire d’abord les composants purs, puis les orchestrateurs ;
- ne jamais déplacer le runner classique et le runner glissant dans la même
  phase ;
- conserver les publications atomiques et la reprise après interruption ;
- valider chaque phase avant de commencer la suivante.

## Architecture visée du cœur en cours d’extraction

```text
lidar2map.py                 façade, CLI et intégration des modes
├── _bootstrap_policy.py    résolution argv/environnement et dépendances GUI pures
├── _bootstrap_runtime.py   orchestration, venv, relance du processus et pip
├── _bootstrap_tls.py       configuration CA et restauration TLS strictes
├── _smoketest.py           orchestration du diagnostic intégré sans réseau en tests
├── _logging_helpers.py     rédaction des secrets et formatage des logs
├── _tee_logger.py          logger atomique, progressions et préfixes de blocs
├── _log_activation.py      activation stdout/stderr, atexit et hook d'exception
├── _atomic_files.py        staging atomique et validation SQLite fermée
├── _http_helpers.py        ouverture URL et téléchargement streaming contrôlé
├── _runtime_paths.py       chemins source/frozen et indicateurs de plateforme
├── _provider_runtime.py    catalogue, pré-flags et chargement des providers
├── _disk_guard.py          sonde de capacité et arrêt propre avant un chunk
├── _wfs_pipeline.py        pagination WFS et publication GeoJSON atomique
├── _bdtopo_bulk.py         découverte, téléchargement et extraction GPKG bulk
├── _bdtopo_layers.py       conversion GPKG et publication GeoJSON multi-format
├── _vector_acquisition.py  sélection bulk/WFS et acquisition des couches
├── _vector_outputs.py      fusion et livrables dérivés du mode vecteur
├── _osm_outputs.py         sélection et statut all-of des livrables OSM
├── _osm_map_pipeline.py    génération Mapsforge en trois passes Osmosis
├── _osm_policy.py          filtres, validation et signatures OSM
├── _osm_runtime.py         découverte, installation et exécution Java/Osmosis
├── _terrain_sources.py     sources autonomes LiDAR/OSM et raster WMTS
├── _terrain_zones.py       primitives pures de résolution des zones terrain
├── _terrain_geocoding.py   géocodage de zone injecté et testable hors réseau
├── _terrain_resolution.py  orchestration des cinq modes de zone et sharding
├── _terrain_chunks.py      découverte et téléchargement par morceau glissant
├── _terrain_download.py    pool, routage, preuve et inventaire des dalles terrain
├── _terrain_prefetch.py    préchargement terrain profondeur un et best-effort
├── _terrain_shading.py     planification et orchestration des ombrages
├── _terrain_index.py       planches d'assemblage et contours administratifs
├── _geojson_merge.py       fusion GeoJSON streamée et publication atomique
├── _geojson_merge_cli.py   sélection des sources et livrables de --merge
├── _geojson_osm_export.py  export PBF OSM vers GeoJSON multi-fichier atomique
├── _split_manifest.py      état persistant et suivi des intermédiaires
├── _split_deliverables.py  résultats et validation des livrables
├── _split_planning.py      grille, sharding, identifiants et signature
├── _split_mbtiles.py       découpage postérieur des magasins MBTiles
├── _deliverable_lifecycle.py  fraîcheur, reprise et nettoyage des livrables
├── _split_runner.py        runner classique et dépendances injectées
├── _split_sliding.py       runner LiDAR glissant et voisinage 3×3
├── _raster_formats.py      conversions RMAP/SQLiteDB et orchestration
├── _mbtiles_wmts.py        producteur MBTiles WMTS/XYZ (téléchargement, cache)
├── _mbtiles_lidar.py       producteur MBTiles LiDAR (warp, overviews, tuilage)
├── _mbtiles_wmts_helpers.py  grille XYZ, URL, connexions, fetch HTTP
├── _ombrages_pures.py      IO raster, kernels numba, hillshade/SVF/LRM/RRIM
├── _ombrages_provider.py   fetch WCS provider, composites VAT/MSTP
├── _shading_specs.py       types d'ombrages, presets, parsing --shading
├── _geojson_geometry.py    tags/styles et algorithmes géométriques purs
├── _geojson_osm_xml.py     streaming GeoJSON IGN → OSM XML atomique
├── _geojson_raster.py      overlay PNG transparent → SQLite OsmAnd atomique
└── _geojson_mapsforge.py   cache, Java/osmosis et publication .map atomique
```

Tous ces modules sont privés (préfixe `_`). Leur interface stable est la façade
conservée dans `lidar2map.py`. Le préfixe `_split_` est réservé aux composants du
traitement découpé ; les producteurs et convertisseurs raster portent un nom de
domaine (`_raster_formats`, `_mbtiles_wmts`, `_mbtiles_lidar`,
`_mbtiles_wmts_helpers`, `_ombrages_pures`, `_ombrages_provider`,
`_shading_specs`, `_geojson_geometry`, `_geojson_osm_xml`, `_geojson_raster`,
`_geojson_mapsforge`, `_bootstrap_policy`, `_bootstrap_runtime`,
`_bootstrap_tls`, `_atomic_files`, `_http_helpers`, `_runtime_paths`,
`_disk_guard`, `_wfs_pipeline`, `_bdtopo_bulk`, `_bdtopo_layers`,
`_vector_acquisition`, `_vector_outputs`, `_geojson_merge`,
`_geojson_merge_cli`, `_geojson_osm_export`, `_osm_outputs`,
`_osm_map_pipeline`, `_osm_policy`, `_osm_runtime`).
Le domaine terrain commence avec `_terrain_sources`.

## Volume déjà transféré

L’indicateur ci-dessous suit la **réduction nette du monolithe**, en lignes
physiques (commentaires, docstrings et lignes vides compris). Le périmètre de
référence est figé au 9 août 2026 à **21 315 lignes**. Cette méthode évite de
compter comme du code transféré les imports, la documentation et les adaptateurs
ajoutés dans les nouveaux modules. Lors du gel, les quatre premiers modules
représentaient le stock initial de 797 lignes externalisées et `lidar2map.py`
comptait 20 518 lignes ; pour chaque phase suivante, seule la baisse nette du
fichier principal est ajoutée à ce stock.

**La seule valeur qui fait foi est `wc -l lidar2map.py`.** Les colonnes par phase
sont informatives ; le total et le reste sont mesurés, jamais dérivés de la somme
des lignes. C’est ce qui a été corrigé le 10 août 2026 : le tableau précédent
annonçait un reste de 19 741 lignes calculé par soustraction alors que le fichier
en comptait 19 803. Les 62 lignes d’écart sont les façades et les blocs d’import
réintroduits dans le monolithe après coup, invisibles pour une somme.

| Module ou phase | Lignes sorties du monolithe | Part du périmètre de référence |
|---|---:|---:|
| `_split_manifest.py` | 244 | 1,14 % |
| `_split_deliverables.py` | 128 | 0,60 % |
| `_split_planning.py` | 191 | 0,90 % |
| `_split_runner.py` | 234 | 1,10 % |
| `_split_sliding.py` | 219 | 1,03 % |
| `_raster_formats.py` | 558 | 2,62 % |
| Façades et imports réintroduits (mesuré) | -62 | -0,29 % |
| `_mbtiles_wmts.py` (7b, mesuré) | 375 | 1,76 % |
| Nettoyage d’imports morts des phases 5 et 7 | 2 | 0,01 % |
| `_mbtiles_lidar.py` (7e, mesuré) | 828 | 3,89 % |
| `_mbtiles_wmts_helpers.py` (7c, mesuré) | 307 | 1,44 % |
| Phase 8 (8a-d, en-fichier par design) | 0 | 0,00 % |
| Relocalisation 9a (en-fichier, pas d'extraction) | 0 | 0,00 % |
| `_ombrages_pures.py` (9b, mesuré) | 1 961 | 9,20 % |
| `_ombrages_provider.py` (9c, mesuré) | 412 | 1,93 % |
| `_shading_specs.py` (9d, mesuré) | 111 | 0,52 % |
| `_geojson_geometry.py` (10a, mesuré) | 254 | 1,19 % |
| `_geojson_osm_xml.py` (10b, mesuré) | 296 | 1,39 % |
| `_geojson_raster.py` (10c, mesuré) | 369 | 1,73 % |
| `_geojson_mapsforge.py` (10d, mesuré) | 81 | 0,38 % |
| `_bootstrap_policy.py` (11a, mesuré) | 47 | 0,22 % |
| `_bootstrap_runtime.py` (11b, mesuré) | 499 | 2,34 % |
| Politique CLI et orchestration bootstrap (11c, mesuré) | 79 | 0,37 % |
| `_bootstrap_tls.py` (11d, mesuré) | 36 | 0,17 % |
| Maintenance `--installer-deps` (11e, mesuré) | 45 | 0,21 % |
| Désinstallation top-level (11f, mesuré) | 39 | 0,18 % |
| Parité launcher de désinstallation (11f-b, mesuré) | 25 | 0,12 % |
| `_smoketest.py` (11g, mesuré) | 116 | 0,54 % |
| `_logging_helpers.py` (12a, mesuré) | 22 | 0,10 % |
| `_tee_logger.py` (12b, mesuré) | 215 | 1,01 % |
| `_log_activation.py` (12c, mesuré) | 47 | 0,22 % |
| `_atomic_files.py` (12d, mesuré) | 41 | 0,19 % |
| `_http_helpers.py` (12e, mesuré) | 45 | 0,21 % |
| `_runtime_paths.py` (12f, mesuré) | 11 | 0,05 % |
| `_disk_guard.py` (12g, mesuré) | 9 | 0,04 % |
| `_wfs_pipeline.py` (13a, mesuré) | 229 | 1,07 % |
| `_bdtopo_bulk.py` (13b, mesuré) | 202 | 0,95 % |
| `_bdtopo_layers.py` (13c, mesuré) | 258 | 1,21 % |
| Orchestration bulk BD TOPO (13d, mesuré) | 5 | 0,02 % |
| `_vector_acquisition.py` (13e, mesuré) | 21 | 0,10 % |
| `_vector_outputs.py` (13f, mesuré) | 4 | 0,02 % |
| `_geojson_merge.py` (13g, mesuré) | 186 | 0,87 % |
| `_geojson_merge_cli.py` (13h, mesuré) | 2 | 0,01 % |
| `_geojson_osm_export.py` (13i, mesuré) | 336 | 1,58 % |
| Statuts OSM et pipeline Mapsforge (13j-k, mesuré) | 197 | 0,92 % |
| `_osm_policy.py` (13l, mesuré) | 52 | 0,24 % |
| `_osm_runtime.py` (14a, mesuré) | 68 | 0,32 % |
| Découverte et cache Java/Osmosis (14b, mesuré) | 25 | 0,12 % |
| Installations transactionnelles (14c, mesuré) | 183 | 0,86 % |
| Mapwriter et commande outils (14d, mesuré) | 59 | 0,28 % |
| `_terrain_sources.py` (15a, mesuré) | 78 | 0,37 % |
| `_terrain_zones.py` (15b, mesuré) | 79 | 0,37 % |
| Nominatim extrait (15c-1, mesuré) | 62 | 0,29 % |
| Overpass et régions extraits (15c-2, mesuré) | 104 | 0,49 % |
| Transformations CRS provider-aware (15d, mesuré) | 16 | 0,08 % |
| Résolveur de zone LiDAR (15e, mesuré) | 162 | 0,76 % |
| Orchestration téléchargement terrain (15f, mesuré) | 118 | 0,55 % |
| Preuve et inventaire `dalles_zone` (15g, mesuré) | 29 | 0,14 % |
| Staging et téléchargement direct (15h, mesuré) | 135 | 0,63 % |
| Téléchargement COPC fenêtré (15i, mesuré) | 18 | 0,08 % |
| Téléchargement COG fenêtré (15j, mesuré) | 116 | 0,54 % |
| Chemins et validation des dalles (15k, mesuré) | 96 | 0,45 % |
| Cache, profilage LAZ et préchargement (15l, mesuré) | 78 | 0,37 % |
| Découverte et téléchargement par morceau (15m, mesuré) | 5 | 0,02 % |
| Orchestration d'ombrage par morceau (15n, mesuré) | 28 | 0,13 % |
| Orchestration du tuilage glissant (15o, mesuré) | 29 | 0,14 % |
| Transaction raster WMTS par morceau (15p, mesuré) | 25 | 0,12 % |
| Transaction LiDAR autonome `--block` (15q, mesuré) | 75 | 0,35 % |
| Tuilage commun des ombrages (15r, mesuré) | 2 | 0,01 % |
| Planification des instances d'ombrage (15s-a, mesuré) | 56 | 0,26 % |
| Orchestrateur d'ombrage (15s-b, mesuré) | 610 | 2,86 % |
| **Total sorti du monolithe (mesuré)** | **11 444** | **53,69 %** |
| **Reste dans `lidar2map.py` (mesuré)** | **9 871** | **46,31 %** |

`_split_sliding.py` contient 421 lignes physiques, mais seulement 219 lignes ont
disparu de `lidar2map.py` : le reste correspond à ses imports, sa documentation,
ses dépendances explicites et à un formatage plus lisible. Le pourcentage mesure
donc la progression structurelle nette, pas la taille artificiellement cumulée
des nouveaux fichiers. Le même périmètre figé sera utilisé pour les phases
suivantes.

`_raster_formats.py` contient 699 lignes physiques pour une réduction nette de
558 lignes du monolithe. Les 141 lignes d’écart sont les imports, la
documentation et les façades nécessaires à l’injection des publications
atomiques.

`_mbtiles_wmts.py` contient 482 lignes physiques pour une réduction nette mesurée
de 375 lignes (`lidar2map.py` : 19 803 → 19 426, dont 2 lignes de nettoyage
d’imports devenus morts aux phases 5 et 7). Les 107 lignes d’écart sont l’en-tête
du module, la structure de dépendances et la réouverture des noms injectés en
début de fonction.

`_mbtiles_lidar.py` contient 933 lignes physiques (le producteur *et* ses trois
helpers directs, colocalisés) pour une réduction nette mesurée de 828 lignes
(`lidar2map.py` : 19 426 → 18 598, dont 1 ligne de nettoyage d'un import `io`
devenu mort). Les 105 lignes d'écart sont l'en-tête du module, la structure de
dépendances et la réouverture des noms injectés en début de fonction — un ratio
d'écart quasi identique à celui de `_mbtiles_wmts.py`, ce qui confirme que le
coût fixe d'une extraction avec injection de dépendances est stable d'un
producteur à l'autre (~105-110 lignes), indépendamment de sa taille.

`_mbtiles_wmts_helpers.py` contient 418 lignes physiques pour une réduction
nette mesurée de 307 lignes (`lidar2map.py` : 18 598 → 18 291). L'écart de 111
lignes est plus élevé, en proportion, que sur les deux producteurs : ce module
n'a pas une seule façade mais trois (`_wmts_fetch`, `_lire_zoom_limites_wmts`,
`telecharger_tuile`), plus le dataclass `_DependancesTelechargementWmts`
partagé — le coût fixe d'injection se paie une fois par point d'entrée, pas
une fois par module, contrairement aux deux extractions précédentes qui
n'avaient qu'un seul point d'entrée chacune.

`_geojson_geometry.py` contient 246 lignes physiques pour une réduction nette
mesurée de 254 lignes (`lidar2map.py` : 15 895 → 15 641). Le module est ici
légèrement plus court que le bloc sorti : les longues explications historiques
restent dans le plan et les docstrings du module ont été resserrées, sans
modifier les algorithmes ni leurs valeurs de configuration.

`_geojson_osm_xml.py` contient 370 lignes physiques pour une réduction nette
mesurée de 296 lignes (`lidar2map.py` : 15 641 → 15 345). Les 74 lignes d'écart
sont l'en-tête, la dataclass de six dépendances, leur réouverture locale et le
coût de la façade reconstruite à chaque appel. Elles incluent aussi le
durcissement explicite du nettoyage si la création du staging XML final échoue.

`_geojson_raster.py` contient 565 lignes physiques pour une réduction nette
mesurée de 369 lignes (`lidar2map.py` : 15 345 → 14 976). Les 196 lignes d'écart
viennent du formatage des blocs historiquement compactés, de la dataclass de
douze dépendances, de la façade et du garde transactionnel qui ferme SQLite puis
nettoie le fichier `.part` et ses sidecars sur toute sortie exceptionnelle.

`_geojson_mapsforge.py` contient 187 lignes physiques pour une réduction nette
mesurée de 81 lignes (`lidar2map.py` : 14 976 → 14 895). Les 106 lignes d'écart
correspondent aux imports, à la dataclass de onze dépendances, à leur réouverture
locale, au formatage de la commande osmosis et à la façade. Ce ratio confirme le
faible gain net anticipé pour un orchestrateur de seulement 119 lignes.

## Cible structurelle : 30 à 35 % dans le script principal

La cible de fin de refonte est désormais fixée à **30–35 % du périmètre de
référence** dans `lidar2map.py`. Avec la référence constante de 21 315 lignes,
cela correspond à un script principal d'environ **6 395 à 7 460 lignes**. L'état
post-15s-b est de 9 871 lignes (46,31 %) : il reste donc à sortir **2 411 à 3 476
lignes nettes** pour atteindre cette zone.

Cette cible est un intervalle d'arrêt, pas un quota à atteindre au détriment de
la lisibilité. Sous 30 %, il faudrait probablement déplacer la façade publique,
le dispatch ou des adaptateurs de compatibilité dont la présence dans le point
d'entrée reste utile. Toute poursuite sous ce seuil demandera une décision
explicite et un nouveau plan.

### Feuille de route indicative après la phase 11d

Les gains ci-dessous sont des **réductions nettes estimées du monolithe**, et non
la taille brute des futurs modules. Chaque phase pourra être divisée en lots plus
petits après audit et caractérisation.

| Phase future | Frontière principale | Gain net indicatif | Contrats préalables |
|---|---|---:|---|
| 11e–g. Maintenance précoce | `--installer-deps`, puis désinstallation et diagnostic dans des lots séparés | 300–500 lignes | codes de sortie, catalogue de paquets, cibles de suppression, ordre top-level |
| 12. Infrastructure partagée | plateforme, configuration, logger, secrets, HTTP et helpers atomiques encore centraux | 1 000–1 400 lignes | imports précoces, TLS, redaction des secrets, publications atomiques |
| 13. Pipelines vectoriels restants | OSM, WFS, BD TOPO, fusion et générateurs GeoJSON encore dans la façade | 1 500–1 900 lignes | caches/signatures, streaming, géométries et sorties partielles |
| 14. Runtime Java/Osmosis | exécution, découverte et installations transactionnelles Java/Osmosis/mapwriter | 350–500 lignes | caches, archives sûres, codes de retour, streaming et atomicité |
| 15. Orchestration terrain restante | `generer_ombrages`, téléchargement de dalles, zones, planches et sources autonomes | 1 600–2 100 lignes | équivalence scientifique, historique, reprise, nettoyage et logs par bloc |
| 16. CLI et points d'entrée | builders argparse, résolution des modes, `main*` et dispatch applicatif | 1 400–1 800 lignes | surface CLI, valeurs par défaut, codes d'erreur et façades monkeypatchables |
| 17. GUI | déplacement de `lancer_gui` et de son état vers le paquet `gui` | 1 100–1 350 lignes | commandes générées, persistance, VM, masquages pays et smoke sans affichage |

La somme indicative dépasse volontairement le besoin minimal : la refonte doit
s'arrêter dès que `lidar2map.py` entre durablement dans la zone 30–35 % avec une
façade cohérente. Les lots les plus risqués ou les moins rentables pourront alors
rester dans le script principal.

### Critères de sortie à 30–35 %

- `lidar2map.py` conserve l'entrée CLI, le dispatch, les réexports historiques et
  les adaptateurs nécessaires, mais plus aucun moteur métier massif ;
- chaque extraction possède des dépendances explicites et une façade de signature
  compatible lorsqu'un nom historique est public ou monkeypatché ;
- les profils FAST et scientifique, les contrats de livraison et les builds
  multiplateformes restent verts à chaque palier ;
- la progression continue d'être mesurée par la baisse nette du monolithe ;
- aucune phase ne combine déplacement structurel, nouveau comportement métier et
  suppression destructive sans tests correctifs séparés.

## Avancement

| Phase | État | Contenu | Validation principale |
|---|---|---|---|
| 0. Caractérisation | Terminée | Runner hors réseau explicite et contrats de façade | 16 suites hors réseau |
| 1. Fiabilisation du split | Terminée | Historique succès/échec, conversion multi-format, reprise et nettoyage 3×3 | `_test_split_history.py`, `_test_interactions.py` |
| 2. Manifeste | Terminée | `Manifeste`, contexte thread-local et enregistrement des fichiers dans `_split_manifest.py` | concurrence, imbrication et reprise |
| 3. Livrables | Terminée | `_ResultatChunk`, normalisation et validation MBTiles/RMAP/SQLiteDB dans `_split_deliverables.py` | stems attendus, fichiers périmés et MBTiles corrompus |
| 4. Planification | Terminée | `--block`, grille, clés `001x001` et signature de configuration dans `_split_planning.py` | contrats de planification et interactions |
| 5. Runner classique | Terminée | `_run_split_priori` extrait dans `_split_runner.py` avec ses dépendances explicites | reprise, overwrite, hors couverture, échec partiel |
| 6. Runner glissant | Terminée | Ordonnancement ombrage/tuilage, voisinage 3×3 et purge différée extraits dans `_split_sliding.py` | reprise après perte d’un livrable, préchargement et coutures |
| 7. Pipelines raster | **Terminée** | Conversions RMAP/SQLiteDB, producteur MBTiles WMTS, producteur MBTiles LiDAR et helpers WMTS extraits | tuilage, publications atomiques et formats multiples |
| 8. Points d’entrée | **Terminée** | `main()` (8a-c) et `main_wmts()` (8a+8d) allégées à leur parsing/résolution ; corps de dispatch déjà atteint ; autres points d'entrée audités, extraction non justifiée | tests d’historique monolithique et CLI |
| 9. Bloc ombrages/COG | **Terminée** | IO raster + kernels numba + algorithmes par type (9b), fetch provider + composites VAT/MSTP (9c), types/presets/parsing (9d) ; `generer_ombrages` volontairement laissée en orchestrateur | `_test_corrections.py`, 83 contrats de façade, profils `fast`/`scientific` |
| 10. GeoJSON/Mapsforge | **Terminée** | Noyau géométrique, conversion GeoJSON IGN→OSM XML, rasteriseur transparent et runner Mapsforge extraits (10a-d) | matrices OSM XML/overlay/Mapsforge, publications atomiques, contrats de façade, profils `fast`/`scientific` |
| 11. Bootstrap et maintenance précoce | **Terminée localement** | Politique GUI/CLI, moteur venv/pip, TLS, maintenance, désinstallation et smoketest extraits (11a-g) | 80 contrats hors réseau, façades, launcher et profil FAST complet |
| 12. Infrastructure partagée | **Terminée localement** | Helpers, logger, activation, primitives atomiques, HTTP, chemins et garde disque extraits (12a-g) | secrets, concurrence, publication SQLite, réseau, plateforme, frozen/source, disque et hooks |
| 13. Pipelines vectoriels restants | **Terminée** | WFS, bulk, acquisition, livrables, fusion, export OSM, statuts all-of, pipeline Mapsforge et politiques OSM extraits (13a-l) | pagination, streaming, sécurité des filtres, signatures, statuts réels, Osmosis et publication atomique |
| 14. Runtime Java/Osmosis | **Terminée** | Options JVM, découverte, installations transactionnelles, mapwriter, commande outils, exécution streamée et nettoyage extraits (14a-d) | archives locales, rollback, priorités de cache, buffer stderr borné, coutures tardives et garde de livraison |
| 15. Orchestration terrain restante | **En cours** | Sources autonomes, primitives, géocodage, transformations CRS, résolveur de zone, ordonnanceur, inventaire, moteurs direct/COPC/COG, chemins, cache, préchargement, découverte, ombrage, tuilages commun/glissant, transactions WMTS/LiDAR autonome, planification des instances et orchestrateur d'ombrage extraits (15a–15s-b) | contrats de sortie, historique, cache atomique, réseau simulé, repli France borné, 24 branches de résolution, routage direct/COG/COPC, preuve de zone, voisinage 3×3, halos `--block`, suffixes/collisions d'ombrage, VRT temporaire, publication atomique, cache WMTS, agrégation multi-TIFF et concurrence profondeur un |

## Travail déjà sécurisé

### Manifeste et historique

- Une tentative remet explicitement le morceau à l’état non terminé.
- La preuve des sorties attendues est persistée par chunk.
- Un manifeste ancien sans preuve est rejoué une fois de façon conservatrice.
- Un livrable absent ou un MBTiles corrompu invalide la reprise.
- Une zone explicitement hors couverture reste réutilisable sans fichier.
- Les succès et les échecs des traitements découpés finalisent l’historique.

### Livrables

- Tous les formats demandés doivent appartenir au même stem.
- Les fichiers d’un ancien run ne peuvent pas remplacer le produit courant.
- Les conversions multiples ne s’arrêtent pas au premier échec.
- La façade de `lidar2map.py` conserve l’injection du validateur MBTiles, donc
  les monkeypatches historiques restent fonctionnels.

### Planification

- La grille explicite reste prioritaire sur les autres modes.
- `--split-width` borne la taille des cellules et conserve une signature stable
  quand l’emprise est seulement étendue avec le même pas.
- `--block i/M` conserve sa validation et son indexation.
- Les identifiants sont centralisés au format 1-based `LLLxCCC`.
- La signature inclut la géométrie, les formats, les paramètres de rendu et le
  fournisseur actif.

### Runner classique

- L’orchestration classique est isolée dans `_split_runner.py` sans importer le
  monolithe.
- Les services applicatifs (manifeste, garde disque, validation des livrables,
  nettoyage et journalisation) sont injectés par une structure dédiée.
- `lidar2map.py` conserve `_run_split_priori` comme façade et construit les
  dépendances à chaque appel ; les monkeypatches des tests et des intégrations
  existantes restent donc actifs.
- Cette extraction a été validée isolément avant le déplacement du runner
  glissant.

### Runner glissant

- L’ordonnancement par rangée et sa fermeture de voisinage 3×3 sont isolés dans
  `_split_sliding.py` ; les producteurs raster restent injectés par la façade.
- La prévalidation d’un livrable disparu déclenche aussi la reconstruction des
  ombrages voisins nécessaires aux coutures.
- Le préchargement est toujours purgé dans un `finally`, y compris après une
  exception.
- La purge d’une rangée reste différée tant qu’un tuilage consommateur est
  incomplet.
- `_voisins_dossiers` est réexporté par `lidar2map.py` pour conserver le contrat
  historique.

### Formats raster

- Les générateurs RMAP et SQLiteDB ainsi que l’agrégation multi-format sont
  isolés dans `_raster_formats.py`.
- Les écritures restent transactionnelles : staging `.part`, validation puis
  remplacement atomique du livrable final.
- Une conversion échouée conserve le MBTiles source et n’empêche pas les autres
  formats demandés d’être tentés.
- Les façades de `lidar2map.py` injectent les helpers atomiques et reconstruisent
  les callbacks à chaque appel ; les monkeypatches historiques restent actifs.

### Producteur MBTiles WMTS

- Le téléchargement concurrent à fenêtre glissante, le namespace de cache par
  couche, l'encodage PNG→JPEG et la publication SQLite sont isolés dans
  `_mbtiles_wmts.py`.
- Les quinze coutures applicatives (téléchargement d'une tuile, publication
  atomique, validation SQLite, arrêt coopératif, seuils d'abandon, endpoints)
  sont regroupées dans `_DependancesMbtilesWMTS`, reconstruite à chaque appel par
  `_dependances_mbtiles_wmts()`.
- Deux contrats verrouillent cette reconstruction : le premier compare chaque
  couture à l'attribut courant du module, le second remplace
  `telecharger_tuile` par un mock et vérifie que la façade le voit puis le
  relâche. Sans eux, une capture des dépendances à l'import passerait tous les
  tests existants tout en désarmant silencieusement les monkeypatches.
- Le classement d'une zone hors couverture reste porté par
  `ZoneHorsCouvertureWMTS`, qui demeure défini dans `lidar2map.py` et est injecté
  comme type : la boucle de split continue de le rattraper par identité.

### Producteur MBTiles LiDAR

- Le warp rasterio (Lambert93 → Web Mercator), la pyramide d'overviews, le
  tuilage par bandes avec masque de couverture (padding transparent en bord de
  bloc) et la publication SQLite sont isolés dans `_mbtiles_lidar.py`.
- Ses trois helpers directs (`_bbox_depuis_gdalinfo`, `_warped_3857_valide`,
  `_tile_workers_defaut`) sont **purs** — aucune couture applicative, aucun état
  de module — et colocalisés dans le même fichier plutôt qu'injectés. Ils sont
  réexportés tels quels par `lidar2map.py` : `_warped_3857_valide` reste appelé
  directement par les suites (`_test_interactions.py`), et `_tile_workers_defaut`
  reste appelé à trois autres endroits du monolithe qui n'ont pas bougé.
- Les douze coutures applicatives (fraîcheur `_mbtiles_a_regenerer`, publication
  atomique, validation SQLite, arrêt coopératif, transformations géographiques,
  fournisseur actif) sont regroupées dans `_DependancesMbtilesLidar`,
  reconstruite à chaque appel par `_dependances_mbtiles_lidar()`.
- `PROVIDER` est une exception parmi les coutures : certaines suites le
  remplacent par affectation directe (`L.PROVIDER = ...`) plutôt que par
  `mock.patch.object` (cf. `_test_atomic_downloads.py`). La façade relit donc
  `PROVIDER.CRS_NATIF` à chaque appel plutôt que de capturer l'objet fournisseur
  entier ; un contrat dédié bascule `L.PROVIDER` en cours de test pour vérifier
  que la valeur injectée suit.
- Trois contrats verrouillent cette reconstruction, sur le même modèle que le
  producteur WMTS (7b) : comparaison de chaque couture à l'attribut courant,
  substitution d'une couture par un mock puis vérification qu'elle est vue et
  relâchée, et le contrat `PROVIDER` ci-dessus.
- La caractérisation 7d (`_test_mbtiles_lidar_atomic.py`) a été écrite AVANT
  l'extraction et n'a nécessité aucune modification après coup : les cinq
  scénarios continuent d'exercer le producteur en entier, à travers la façade,
  sans connaître l'existence du module extrait.

### Helpers WMTS (7c)

Nature différente des deux extractions précédentes : pas un producteur unique
mais un regroupement thématique de fonctions de tailles et de couplages
hétérogènes, isolées dans `_mbtiles_wmts_helpers.py` (grille XYZ, validation de
bbox, contrôle des images, pool de connexions keep-alive, construction d'URL,
fetch HTTP, téléchargement d'une tuile, GetCapabilities).

- La majorité (`deg_to_tile`, `calculer_grille_xyz`, `compter_tuiles_xyz`,
  `estimer_taille`, `_bbox_valide_wgs84`, `_est_image_valide`, le pool de
  connexions) est pure et réexportée telle quelle, sans injection — même
  schéma que les trois helpers LiDAR de 7e.
- `telecharger_tuile` et `_lire_zoom_limites_wmts` reçoivent une structure de
  dépendances commune (`_DependancesTelechargementWmts`), reconstruite à
  chaque appel par `_dependances_telechargement_wmts()`.
- **Un bug a été introduit puis corrigé pendant cette extraction**, révélateur
  d'un angle mort du schéma d'injection utilisé jusqu'ici : `_wmts_fetch`
  (le GET HTTP réel) était appelé par bare-name depuis `telecharger_tuile`,
  colocalisé dans le même nouveau module. Deux suites
  (`_test_robustesse.py`, `_test_interactions.py`) remplacent `_wmts_fetch`
  en bloc par une affectation directe (`l2m._wmts_fetch = lambda url: ...`,
  pas `mock.patch.object`) pour simuler le réseau sans le contacter. Un appel
  interne au module extrait ignore ce remplacement, puisqu'il ne passe jamais
  par l'attribut patché sur `lidar2map`. Le premier passage des suites
  scientifiques a immédiatement révélé l'échec (tentative de connexion réseau
  réelle). Correction : `_wmts_fetch` est maintenant injecté comme **callable**
  dans `_DependancesTelechargementWmts` (`wmts_fetch`), au lieu que
  `telecharger_tuile` appelle directement l'implémentation colocalisée — même
  logique que l'injection de `telecharger_tuile` lui-même dans le producteur
  WMTS (7b). Un contrat dédié (`test_telecharger_tuile_facade_reads_directly_reassigned_wmts_fetch`)
  reproduit ce style d'affectation directe pour verrouiller le correctif.
- **Leçon pour toute extraction future** : avant de coloculer deux fonctions
  dans un même module extrait au prétexte qu'"une seule les appelle", vérifier
  si l'une des deux est remplacée par affectation directe dans une suite
  existante (`grep "l2m\.<nom> *="`), pas seulement par `mock.patch.object`.
  L'affectation directe ne survit pas à un appel interne bare-name entre deux
  fonctions désormais colocalisées ailleurs que dans `lidar2map.py`.

## Audit préalable : génération MBTiles

L'audit statique du 9 août 2026 prépare la suite de la phase 7. Il n'a déplacé
aucune ligne de production. Les volumes ci-dessous sont des **lignes physiques
candidates**, et non des lignes déjà transférées : seule la réduction nette de
`lidar2map.py`, mesurée après chaque extraction, alimentera le tableau
d'avancement.

| Bloc audité | Lignes candidates | Périmètre |
|---|---:|---|
| Producteur WMTS `generer_mbtiles_wmts` | 421 | téléchargement concurrent, cache, encodage et publication SQLite |
| Helpers WMTS | 335 | grille XYZ, URL, connexions, contrôle des images et téléchargement |
| Producteur LiDAR `generer_mbtiles_lidar` | 831 | reprojection, encodage, tuilage concurrent et publication SQLite |
| Helpers directs LiDAR | 37 | emprise GDAL, validation du raster reprojeté et nombre de workers |
| **Total examiné** | **1 624** | deux producteurs et leurs dépendances proches |

Les deux producteurs partagent les primitives de staging `.part`, de validation
SQLite, d'arrêt coopératif et de nettoyage, mais pas leur logique métier. Le
WMTS dépend du téléchargement, du cache HTTP et du contrôle des réponses ; le
LiDAR dépend de GDAL, des transformations de coordonnées et de l'encodeur de
tuiles. Ils seront donc extraits dans des sous-phases distinctes.

### Couverture et caractérisation atomique

Le producteur WMTS est déjà exercé avec une génération réelle de trois tuiles,
une erreur HTTP persistante, une zone entièrement hors couverture, la séparation
des caches par couche et leur réutilisation. La sous-phase 7a est terminée : les
tests atomiques verrouillent désormais :

- la conservation d'un MBTiles final préexistant lors d'un overwrite échoué ;
- le nettoyage du staging après arrêt ou `KeyboardInterrupt`, sans remplacer le
  livrable précédent ;
- l'absence de publication et de cache trompeurs si la conversion PNG vers JPEG
  échoue ;
- la conservation du livrable précédent si la validation SQLite finale échoue.

Le producteur LiDAR est déjà exercé sur des tuiles PNG transparentes et des
tuiles mixtes JPEG/PNG, leurs métadonnées et leurs emprises. Les contrôles
scientifiques couvrent aussi le refus d'une source `float32` et la validation du
raster reprojeté. La sous-phase 7d est terminée : `tests/_test_mbtiles_lidar_atomic.py`
exerce le producteur `generer_mbtiles_lidar` en entier (warp réel, tuilage réel,
encodage réel — pas un helper isolé) et verrouille désormais :

- l'échec injecté de validation SQLite après un tuilage réussi, avec
  conservation du livrable précédent et aucun résidu `.part`/`-wal`/`-shm` ;
- une exception dans l'encodeur Pillow (JPEG/PNG), qui se propage sans publier
  de MBTiles tronqué (le chemin séquentiel `tile_workers=1` et le chemin pool
  partagent le même point d'échec `_encode_tile`) ;
- l'arrêt coopératif (`_stop_event`) qui lève `KeyboardInterrupt` dès la
  prochaine rangée et conserve le livrable précédent ;
- la réutilisation du cache warpé (`_tuilage_z*.tif`) à travers le producteur
  complet : un deuxième appel sans `--tuiles-ecraser` sur une source inchangée
  ne re-warpe pas (`mtime` du warpé strictement identique avant/après), il ne
  régénère que le MBTiles manquant. Le seuil réel de réutilisation exige un
  warpé `> 1 Mo` (garde-fou contre un warpé trivial mal formé) : le test utilise
  une source bruitée à zoom 19 pour l'atteindre, un run sinusoïdal à basse
  résolution ne compressant qu'à quelques ko et ne l'exerçant jamais.
- le succès complet (warp + tuilage + publication), sans résidu de staging.

### Ordre de réalisation

| Sous-phase | État | Action | Volume brut | Réduction nette estimée | Progression nette cumulée estimée |
|---|---|---|---:|---:|---:|
| 7a | **Terminée** | Ajouter les caractérisations atomiques WMTS | 0 ligne déplacée | 0 | 7,09 % mesuré |
| 7b | **Terminée** | Extraire seulement `generer_mbtiles_wmts` | 421 lignes | **375 lignes mesurées** | **8,86 % mesuré** |
| 7d | **Terminée** | Ajouter les caractérisations atomiques LiDAR | 0 ligne déplacée | 0 | 8,86 % inchangé |
| 7e | **Terminée** | Extraire le producteur LiDAR et ses trois helpers directs | 873 lignes | **828 lignes mesurées** | **12,75 % mesuré** |
| 7c | **Terminée** | Extraire les helpers WMTS restants | 367 lignes | **307 lignes mesurées** | **14,19 % mesuré** |

Ces estimations ne sont pas ajoutées au volume « déjà transféré ». Elles servent
uniquement à dimensionner les sous-phases ; les chiffres définitifs sont la
différence physique de `lidar2map.py` par rapport à la référence figée, relevée
avant et après chaque déplacement. Le bloc optionnel 7c pourrait porter
l'ensemble aux environs de 14 %, mais ne sera engagé qu'avec une mesure propre.

La progression annoncée pour 7a (7,38 %) reposait sur la somme des colonnes ; la
mesure réelle au même instant était 7,09 %. Les valeurs ci-dessus sont relevées,
pas dérivées.

### Conditions d'arrêt de chaque sous-phase

Une extraction MBTiles est interrompue et corrigée avant toute suite si l'un des
contrats suivants n'est plus démontré :

- les noms historiques restent disponibles dans la façade `lidar2map.py` ;
- les dépendances sont reconstruites à chaque appel afin de préserver les
  monkeypatches et les intégrations existantes ;
- le livrable final n'est remplacé qu'après fermeture et validation de la base ;
- un échec ou une interruption conserve le livrable précédent et ne laisse ni
  `.part`, ni `-wal`, ni `-shm` ;
- les suites ciblées, les contrats de façade et le profil hors réseau approprié
  passent ;
- tout nouveau module est publié par `deploy.py`, surveillé par la CI et force le
  rebuild des bundles.

Pour 7b, les suites minimales sont `_test_robustesse.py`,
`_test_interactions.py`, `_test_split_history.py`, les nouvelles
caractérisations atomiques WMTS et le profil `fast`. Pour 7e, elles comprennent
au minimum `_test_tiling.py`, `_test_corrections.py`,
`_test_mbtiles_lidar_atomic.py` (caractérisations 7d), `_test_split_history.py`,
puis la campagne scientifique ou complète correspondant à ce déplacement plus
important.

## Tests de non-régression

### Commande de référence

Depuis l’arborescence de développement locale :

```bash
python Tests/run_tests.py fast
python Tests/run_tests.py scientific
python Tests/run_tests.py all
```

Dans le dépôt GitHub déployé, `Tests/` est publié sous `tests/` :

```bash
python tests/run_tests.py fast
python tests/run_tests.py scientific
python tests/run_tests.py all
```

Le runner lance chaque suite dans un sous-processus isolé. Il n’utilise pas la
découverte implicite de `unittest`, car plusieurs fichiers historiques portent
le préfixe `_test_`. Sans profil, il exécute également la campagne complète.

### Matrice des contrats

| Suite | Risque couvert |
|---|---|
| `tests/_test_refactor_contracts.py` | façades importables, modules extraits, CLI stable, manifeste concurrent, planification |
| `tests/_test_split_history.py` | historique, statuts non nuls, livrables, reprise classique et glissante |
| `tests/_test_interactions.py` | interactions entre overwrite, manifeste, cache, fournisseurs, GUI et split |
| `tests/_test_corrections.py` | régressions scientifiques et défauts historiques corrigés |
| `tests/_test_tiling.py` | génération et structure des tuiles |
| `tests/_test_robustesse.py` | entrées invalides, fichiers corrompus et comportements conservateurs |
| `tests/_test_mbtiles_lidar_atomic.py` | producteur MBTiles LiDAR complet : validation SQLite, encodeur, arrêt coopératif, réutilisation du cache warpé |
| `tests/_test_atomic_downloads.py` | téléchargements et publications atomiques |
| `tests/_test_atomic_publications.py` | sorties finales atomiques et reprise après erreur |
| `tests/_test_patch_delivery.py` | cohérence entre sources, déploiement et bundles ; enregistrement `MAP`/rebuild/CI de tout module extrait, dérivé de l'AST |
| `tests/_test_docs_links.py` | intégrité des liens de documentation |

Les autres suites du runner couvrent le partage téléphone et la CLI distante.

### Politique de validation d’une phase

Une extraction est terminée lorsque :

1. `py_compile` et Ruff ne signalent aucune erreur fatale ;
2. les contrats dédiés au composant passent ;
3. les suites d’interaction directement concernées passent ;
4. la façade historique reste importable ;
5. le déploiement sait publier le nouveau fichier ;
6. une campagne complète passe au jalon approprié.

La dernière campagne complète de référence a exécuté les 12 suites hors réseau
avec succès le 9 août 2026, après l’extraction des livrables. La phase de
planification a ensuite été contrôlée par les contrats ciblés, la suite
d’interactions et le profil `fast` complet (succès en 25,4 s). L’extraction du
runner classique est validée par les contrats de reprise et la suite
d’interactions, puis par un nouveau profil `fast` complet (succès en 27,8 s).
Le runner glissant est ensuite validé par ses 19 scénarios ciblés, les contrats
de voisinage, la suite d’interactions et le profil `fast` complet (succès en
23,7 s). L’extraction des formats raster est validée par les générations RMAP
et SQLiteDB réelles (`_test_tiling.py`), la suite de corrections scientifiques,
les contrats de conversion et de publication atomique, les interactions, puis
le profil `fast` complet (succès en 26,5 s). Une campagne `scientific` complète
n’est pas répétée pour chaque déplacement structurel. La caractérisation WMTS
7a ajoute quatre contrats au harnais de publication atomique, désormais à 19
tests : panne de téléchargement, arrêt/`KeyboardInterrupt`, échec PNG→JPEG et
échec de validation SQLite. Les suites de robustesse, d’interactions et les 49
tests d’historique/split passent, ainsi que les huit suites du profil `fast`
(succès en 39,4 s). L’extraction 7b du producteur WMTS est validée par les 19
tests de publication atomique (dont les 4 caractérisations de 7a, inchangées),
les 21 contrats de façade (dont 2 nouveaux sur la reconstruction des coutures),
`_test_robustesse.py`, `_test_interactions.py`, `_test_tiling.py`,
`_test_corrections.py`, puis le profil `fast` complet (succès en 27,8 s). Ruff
est passé de 6 signalements F401 à zéro sur `lidar2map.py` : deux imports morts
hérités des phases 5 et 7 (`gc`, `struct`) ont été retirés et les deux réexports
de façade `_cle_chunk`/`_identite_chunk` portent maintenant un `noqa` motivé, de
sorte que le critère 1 de la politique redevient un signal binaire.
La sous-phase 7d ajoute cinq scénarios atomiques sur le producteur MBTiles
LiDAR complet (`_test_mbtiles_lidar_atomic.py`, profil `scientific`), puis le
profil `scientific` entier (5 suites, succès en 158,1 s) et une nouvelle
passe `fast` (succès en 40,0 s) confirment qu'aucune régression n'a été
introduite avant le déplacement 7e. L'extraction 7e du producteur LiDAR est
validée par les 24 contrats de façade (dont 3 nouveaux sur la reconstruction
des coutures et la lecture de `PROVIDER` à l'appel), les 5 caractérisations
atomiques 7d exécutées telles quelles sur le module extrait,
`_test_tiling.py`, `_test_corrections.py`, `_test_split_history.py`, le garde
de déploiement dérivé de l'AST (aucune modification manuelle requise pour
enregistrer `_mbtiles_lidar.py`), puis le profil `scientific` complet (5
suites, succès en 137,8 s) et le profil `fast` complet (succès en 43,3 s).
L'extraction 7c des helpers WMTS a d'abord fait échouer `_test_robustesse.py`
et `_test_interactions.py` (bug `_wmts_fetch` décrit ci-dessus), détecté dès
la première exécution de la campagne `scientific` — exactement le rôle que ces
suites sont censées jouer. Après correction, 28 contrats de façade (dont 3
nouveaux sur `telecharger_tuile`/`_lire_zoom_limites_wmts`), `_test_atomic_downloads.py`,
`_test_atomic_publications.py`, `_test_robustesse.py`, `_test_interactions.py`,
`_test_split_history.py`, `_test_patch_delivery.py`, puis le profil
`scientific` complet (5 suites, succès en 155,1 s) et le profil `fast` complet
(succès en 37,6 s) passent tous.

## Déploiement et compatibilité des bundles

Les nouveaux modules `_split_*.py`, `_raster_formats.py`, `_mbtiles_*.py`
(WMTS et LiDAR) et `_ombrages_pures.py` sont copiés vers le dépôt par
`deploy.py` et surveillés par la CI (filtre `paths:` en glob `_mbtiles_*.py`
pour ne pas devoir rééditer `ci_github.yml` à chaque nouveau producteur
`_mbtiles_*` ; entrée explicite pour `_ombrages_pures.py`, hors de ce glob).
Ils sont
compilés dans les bundles PyInstaller : leur ajout ou leur modification déclenche
donc un **rebuild**, pas un patch limité à `_internal/lidar2map.py`. Le garde de
`deploy.py` empêche de publier un bundle qui contiendrait le nouveau
`lidar2map.py` sans ses modules.

Ce triple enregistrement (`deploy.MAP`, `deploy.is_rebuild_file`, filtres
`paths:` de `ci_github.yml`) était vérifié par une liste recopiée à la main dans
`_test_patch_delivery.py` : un module extrait puis oublié dans l'un des trois ne
faisait échouer aucun test, et le bundle produit importait un fichier absent. La
liste est désormais **dérivée de l'AST de `lidar2map.py`** : tout import d'un
module frère doit être présent dans `MAP`, être rebuild-gated et être couvert par
au moins un motif `paths:`. Les phases 7c à 8 n'ont donc plus rien à ajouter dans
ce test.

## Phase 8 : points d'entrée

**La phase 7 est terminée.** Les deux producteurs MBTiles (WMTS en 7b, LiDAR en
7e) et les helpers WMTS restants (7c) sont extraits et validés. Six modules
`_split_*`/`_raster_formats`/`_mbtiles_*` sortent 3 024 lignes du monolithe,
14,19 % du périmètre figé.

### Une métrique différente

Contrairement à 7b/7c/7e, la phase 8 ne déplace pas de code vers un nouveau
module : `main()` construit son parser argparse à partir de dizaines de
constantes de module (`NB_WORKERS`, `ELEVATION_SOLEIL`, `SVF_GAMMA`,
`PROVIDER`…) en valeurs par défaut. Les extraire vers un fichier séparé
demanderait d'injecter cette dizaine de valeurs pour un gain de couplage nul —
le même travers identifié sur une partie de 7c (`telecharger_tuile` à appelant
unique), mais ici systématique plutôt qu'occasionnel. Décision (validée avec
Nico avant exécution, premier cas de ce type dans le plan) : les fonctions
extraites de la phase 8 restent des fonctions privées **dans `lidar2map.py`**,
pas de nouveau module. L'indicateur « lignes sorties du monolithe » n'avance
donc plus pendant cette phase ; le critère de succès devient la lisibilité et
la testabilité de `main()`/`main_wmts()` elles-mêmes.

### Sous-phase 8a : parsers argparse extraits (terminée)

- `_construire_parser_lidar()` (250 lignes) et `_construire_parser_wmts()`
  (103 lignes) contiennent désormais toute la construction du parser
  (`add_argument`/`add_argument_group`), sans logique ni effet de bord.
  Extraction mécanique : aucun comportement CLI n'est censé changer.
- `main()` passe de ~1407 à ~1157 lignes de corps propre ; `main_wmts()` de
  ~445 à ~342 lignes. Le fichier total reste stable (18 291 → 18 299 lignes,
  +8 : signatures, docstrings, `return parser`), conforme à la décision
  ci-dessus.
- Validation : `--version`/`--raster --help`/`--help` exécutés en CLI réel
  (sous-processus, `LIDAR2MAP_BOOTSTRAP=none`), les 28 contrats de
  `_test_refactor_contracts.py` (dont `test_help_keeps_the_documented_workflow_surface`
  et `test_lidar_aliases_reach_the_same_validation_boundary`, qui exercent le
  parser en profondeur), profil `fast` complet et profil `scientific` complet,
  tous verts. Ruff propre.
- Aucun nouveau fichier : rien à ajouter à `deploy.py`/`ci_github.yml`/au garde
  AST de `_test_patch_delivery.py`.

### Correctif hors-plan : emprise de planche dérivée par un itinéraire WFS

Trouvé pendant le test manuel de 8a par Nico (`--vector --layer chemins`, zone
Garéoult), sans rapport avec l'extraction du parser : `_planche_depuis_dossier`
calcule l'emprise de la planche d'assemblage depuis le contenu réel des
fichiers du dossier. Le WFS IGN "itinéraires anciens" renvoie la géométrie
**entière** d'un tracé qui traverse seulement la zone demandée (constaté :
un export sur Garéoult ~4 km contenait l'EV8 Perpignan-Menton et un itinéraire
équestre de ~50 km). L'emprise calculée dérivait donc à des centaines de km de
la zone réelle, avec deux symptômes : le reverse-geocoding du département
échouait (centre hors de toute commune identifiable → « no department at
43.2046,5.1665 », aucun contour dessiné) et la planche devenait illisible (la
zone de 4 km invisible à l'échelle du tracé entier). Le `.map` de 222 octets
observé dans le même run n'était PAS un bug : osmosis clippe correctement sur
la bbox demandée, et il ne reste presque rien des deux itinéraires longue
distance sur une fenêtre aussi petite — comportement attendu, pas un défaut.

Le code avait déjà un garde-fou partiel (intersection de plusieurs couches au
lieu de leur union), documenté en commentaire, mais qui ne s'applique qu'avec
2+ fichiers geojson à intersecter — avec une seule couche (`--layer chemins`),
il n'y a rien à intersecter et le bug ressurgit intact.

Correctif : `_planche_depuis_dossier` accepte un paramètre optionnel
`zone_bbox_wgs84` (la zone WGS84 effectivement demandée, connue de
`_resoudre_zone_wgs84`) et clippe systématiquement toute bbox lue depuis un
fichier sur cette référence avant de l'utiliser. Câblé aux 3 appelants qui
connaissent la zone demandée (`main()`, `main_wmts()`, `main_wfs()`) ; le 4e
appelant (mode autonome `--planche DIR`, sans requête associée) garde le
comportement best-effort historique, faute de référence.

Validation : nouveau test dédié (`_test_corrections.py`, §23) qui reproduit le
bug avec un LineString synthétique traversant toute la côte méditerranéenne
puis vérifie que l'émprise clippée correspond exactement à la zone demandée
(sans `zone_bbox_wgs84` : largeur >4° reproduisant le bug ; avec : égalité
stricte à la zone). Profils `scientific` (397,8 s) et `fast` (157,1 s)
complets, tous verts.

### Sous-phase 8b : `--source` extrait (terminée)

En relisant le corps de `main()` pour scoper 8b, la « finalisation des args »
que j'avais envisagée s'est révélée être en réalité le cœur métier de
`main()` : résolution de la zone géographique sur 5 branches
(`--zone-region`/`--zone-department`/`--zone-bbox`/`--zone-gps`/`--zone-city`),
conversions CRS, `--block`, décision split/non-split — truffé de `sys.exit()`
conditionnels et de variables (`bbox`, `nom_zone`, `cx`, `cy`) posées
différemment selon la branche puis réutilisées plus loin. Une erreur de
recopie y corromprait silencieusement la zone traitée, pas juste un test.
Ce n'est plus une extraction mécanique comme 8a : reportée (cf. « Reste à
faire » ci-dessous), le temps d'un tour de conception dédié plutôt que de la
faire vite sur du code qui décide silencieusement ce qui est traité.

8b s'est donc scopée sur un sous-bloc réellement isolé et sans risque
équivalent : le traitement de `--source` (conversion autonome MBTiles→RMAP/
SQLiteDB, détection CRS d'un TIF, relais PBF/OSM), 66 lignes, extrait tel
quel dans `_traiter_source_autonome(args)`. Contrairement à la résolution de
zone, ce bloc ne lit ni n'écrit `bbox`/`nom_zone`/`cx`/`cy` (la zone n'est pas
encore résolue à ce point) : sa seule interface avec le reste de `main()` est
`args` lui-même et des `sys.exit()` directs, aucune dépendance croisée.

- **Bug pré-existant caractérisé, pas corrigé** : un `--source zone.tif`
  pointant vers un fichier absent affiche « Recompute from tiles... » (laissant
  entendre que le run continue sans source) puis tombe quand même dans la
  branche « unrecognised extension » et sort en code 1 — `ext` devient `""`
  après `args.source = None`, ce qui ne correspond à aucune branche du
  `if/elif`. Existait avant 8b, non introduit par l'extraction. Caractérisé
  par `test_missing_tif_source_exits_despite_recompute_message` pour que
  l'extraction ne le fasse pas dériver ; un vrai correctif reste un changement
  de comportement séparé, pas fait ici par discipline de périmètre.
- Validation : 11 nouveaux contrats (`SourceAutonomeContractTests`) couvrant
  les 4 extensions (`.mbtiles`, `.pbf`/`.osm`, `.tif`/`.tiff`, inconnue), les
  codes de sortie, et le quirk ci-dessus ; CLI réel (`--version`, erreur
  `--source` inexistant) ; 39 contrats de façade au total, profils `fast`
  (26,5 s) et `scientific` (81,1 s) complets, tous verts. Ruff propre.

### Sous-phase 8c : résolution de zone extraite (terminée)

La pièce que j'avais reportée en 8b (5 branches --zone-*, --block, ~190 lignes,
interdépendances `bbox`/`nom_zone`/`cx`/`cy`) est extraite dans
`_resoudre_zone_lidar(args, _osm_seul)`, qui retourne
`(bbox, nom_zone, cx, cy, blk)`.

**Deux bugs trouvés par relecture et par ruff avant tout test, corrigés avant
publication :**

1. Le corps déplacé référence `_osm_seul` (nom de variable historique dans
   `main()`), mais le paramètre de la nouvelle fonction avait été nommé
   `osm_seul` (sans underscore) lors de la rédaction de la signature —
   `NameError` certain à l'exécution, invisible à la compilation (Python ne
   vérifie pas les noms statiquement). Trouvé en relisant le corps généré
   avant de lancer le moindre test. Corrigé en renommant le paramètre
   `_osm_seul` pour matcher le corps déplacé tel quel.
2. `_blk` (résultat de `_parse_block`, calculé en toute fin du bloc extrait)
   est réutilisé PLUS LOIN dans `main()`, dans le dispatch a-priori
   (`if _blk:` conditionne la marge fixe entre blocs voisins,
   `_traiter_bbox_lidar`) — un usage que je n'avais pas repéré en découpant
   les bornes du bloc à extraire. `ruff check` (F821 : nom non défini) l'a
   détecté immédiatement après le premier passage, avant tout test aussi.
   Corrigé en ajoutant `blk` comme 5ᵉ valeur de retour, recapturée par
   l'appelant.

Ces deux bugs valident la prudence prise en 8b (ne pas extraire sans
caractérisation) : une extraction en apparence mécanique sur du code aussi
interdépendant produit des bugs runtime silencieux, que seule une relecture
attentive + linter + tests dédiés attrapent — aucun des deux n'aurait été vu
par `py_compile` seul.

- Validation : CLI réel (mode bbox complet, jusqu'au téléchargement de
  tuiles réelles — bbox/aire/nom de zone corrects, interrompu volontairement
  une fois le comportement confirmé pour ne pas télécharger pour rien) ; 23
  nouveaux contrats (`ResolutionZoneContractTests`) couvrant les 5 branches
  (succès + échecs caractéristiques de chacune), le suffixe de variante
  provider, le calcul largeur/grille (mode ville/gps uniquement), le sharding
  `--block` (narrowing + suffixe + skip en mode OSM-seul) ; géocodeurs réseau
  (`geocoder_region`/`geocoder_departement`/`geocoder_ville_natif`) mockés,
  conversions CRS pures non mockées (déterministes, déjà couvertes ailleurs).
  62 contrats de façade au total, profils `fast` (41,4 s) et `scientific`
  (119,5 s) complets, tous verts. Ruff propre.
- `main()` passe de ~1157 à ~922 lignes de corps propre (8a+8b+8c cumulés :
  1407 → 922, soit -34 %, sans bouger l'indicateur de volume sorti du
  monolithe puisque ces fonctions restent dans `lidar2map.py` par design,
  cf. plus haut).

### Sous-phase 8d : `main_wmts()` allégée (terminée)

Équivalent de 8b+8c côté point d'entrée `--raster`. Contrairement à `main()`,
`main_wmts()` partageait déjà `_resoudre_zone_wgs84(args)` avec `main_wfs()`
(extrait bien avant cette phase) : pas de bloc de résolution de zone à
démêler ici. Deux extractions plus ciblées :

- `_traiter_source_wmts(args)` (25 lignes) : jumeau simplifié de
  `_traiter_source_autonome` (8b) — conversion `.mbtiles`→RMAP/SQLiteDB
  uniquement (pas de cas TIF/PBF côté WMTS).
- `_resoudre_couche_wmts(args)` (59 lignes) : résolution de l'alias/identifiant
  de couche IGN (`layer`/`style`/`img_fmt`/`apikey_requis`/`fmt_ext`) et
  plafonnement des zooms selon les capacités réelles (GetCapabilities ou table
  XYZ), avec mutation de `args.zoom_min`/`args.zoom_max` pour que
  `_traiter_bbox_wmts` hérite des bornes capées côté split.

`main_wmts()` : 342 → 261 lignes (-24 %). Aucun bug d'extraction cette fois
(contrairement à 8c) : le bloc est resté correctement délimité au premier
passage, confirmé par `ruff` propre immédiatement.

- Validation : run CLI réel bout-en-bout (`--raster --layer planign
  --zone-bbox ... --zoom-min 8 --zoom-max 10`, 3 tuiles téléchargées, MBTiles
  + planche produits) ; 12 nouveaux contrats
  (`SourceEtCoucheWmtsContractTests`) couvrant les erreurs `--source`, la
  résolution d'alias/identifiant direct, le plafonnement de zoom (rétréci,
  no-op, bornes inversées normalisées) ; 74 contrats de façade au total,
  profils `fast` (26,4 s) et `scientific` (79,9 s) complets, tous verts. Ruff
  propre.

### Reste à faire en phase 8

- **Corps de dispatch** : ce qui doit *rester* dans `main()`/`main_wmts()` —
  l'enchaînement `_run_split_priori(...)`, `generer_mbtiles_lidar(...)`,
  `generer_mbtiles_wmts(...)`, `generer_geojson_osm(...)`, etc. C'est la vraie
  « orchestration » visée par le nom de la phase ; à ce stade `main()` et
  `main_wmts()` en sont déjà proches (parsing, --source, résolution de
  zone/couche tous extraits).
- ~~**Dette des jumeaux WMTS**~~ **CLOS (vérifié 10 août 2026)** : comparaison
  ligne à ligne des deux appelants (`main_wmts()` passe simple et
  `_traiter_bbox_wmts()` découpé) sur `_jpeg_quality_sortie`,
  `_nom_mbtiles_wmts` et l'appel complet à `generer_mbtiles_wmts` — arguments
  strictement identiques partout, à l'exception du nom de zone et de la bbox
  (`nom_z`/bbox du morceau vs `nom_zone`/bbox entière), une spécialisation
  requise et non une dérive accidentelle. Déjà corrigé dans une session
  antérieure (cf. commentaires R2#14/R2#18 dans le code) ; le plan le
  signalait encore comme ouvert par erreur.
- **Points d'entrée restants audités (10 août 2026)** : `main_decouper()` (90
  lignes) et `main_serve()` (53 lignes) sont déjà légers, rien à extraire.
  `main_fusionner()` (139 lignes) et `main_wfs()` (243 lignes) ont un poids
  marginal comparé aux 1400/450 lignes initiales de `main()`/`main_wmts()` —
  le rapport valeur/risque d'une extraction façon 8a-8d n'est plus favorable
  ici (même travers que la partie basse valeur de 7c). Phase 8 considérée
  fonctionnellement complète pour les points d'entrée : il ne reste que le
  « corps de dispatch » ci-dessus, qui décrit un état déjà largement atteint
  plutôt qu'un chantier restant.
- Le plan mesure des lignes, pas du couplage. Un indicateur complémentaire utile
  pour les sous-phases suivantes : le nombre de symboles de `lidar2map.py`
  référencés depuis les modules extraits (zéro, par construction) et le nombre
  de coutures injectées par façade (12 pour le runner classique, 15 pour le
  producteur WMTS). Une façade qui dépasserait la vingtaine de coutures
  signalerait un découpage fait au mauvais endroit.

## Phase 9 : bloc ombrages/COG

Après la phase 8, `lidar2map.py` contient encore une section de 3758 lignes
("ASSEMBLAGE COG (rasterio)") regroupant les kernels numba, les algorithmes
de calcul par type d'ombrage (hillshade, SVF, LRM, RRIM), les composites
(VAT, MSTP) et leur orchestrateur `generer_ombrages`. Exploration fine menée
le 10 août 2026 (lecture complète + analyse AST des noms libres par
sous-groupe) avant toute extraction, contrairement à la phase 8 où le premier
passage sur `_resoudre_zone_lidar` avait révélé deux bugs après coup.

Constat principal : le module réel (hors bloc mal placé, cf. 9a) a un
couplage externe faible pour sa taille — ~11 dépendances non-stdlib
(`PROVIDER`, `_chemin_part`, `_creer_fichier`, `_hms`, `_valider_tif_dalle`,
`_stop_event`, `normaliser_nom`, `SVF_GAMMA`, `HTTP_CHUNK_SIZE`,
`ELEVATION_SOLEIL`, `RESOLUTION_M`) pour ~3317 lignes, un bien meilleur ratio
que le parser de `main()` (10 dépendances pour 250 lignes). `_valider_tif_dalle`
est déjà monkeypatché 8 fois dans les tests existants : le schéma d'injection
par façade (comme 7b/7e) s'y applique directement. `_test_corrections.py`
contient déjà 140 références aux ombrages : contrairement à la résolution de
zone en 8c, ce domaine est déjà largement caractérisé.

Découpage retenu :

| Sous-phase | État | Action | Volume | Risque |
|---|---|---|---:|---|
| 9a | **Terminée** | Reloger le bootstrap osmosis/JRE/mapwriter mal placé | 394 lignes déplacées | Nul (relocalisation pure) |
| 9b | **Terminée** | Extraire IO raster + kernels numba + algorithmes par type | 1996 lignes | **1961 lignes mesurées** |
| 9c | **Terminée** | Extraire TIFF multipart + fetch provider + composites VAT/MSTP | 460 lignes | **412 lignes mesurées** |
| 9d | **Scindée** | Presets/parsing extraits ; `generer_ombrages` reste en l'état (voir ci-dessous) | 118 lignes | **111 lignes mesurées** |

### Sous-phase 9a : bootstrap osmosis/JRE/mapwriter relogé (terminée)

`_promouvoir_dossier`, `_bin_outil`, `_telecharger_osmosis_local`,
`_telecharger_jre_local`, `_trouver_java`, `_trouver_osmosis`,
`_verifier_mapwriter` (394 lignes, y compris le bloc exécutable
`if _TELECHARGER_OUTILS:` de la commande `--telecharger-outils`) n'avaient
aucun rapport avec les ombrages — dérive historique, avec leur propre jeu de
dépendances distinct (`BUNDLE_DIR`, `LIDAR2MAP_HOME`, `WINDOWS`,
`_TELECHARGER_OUTILS`, `_safe_zip_extractall`) absent du reste de la section.
Relogées juste avant `_java_opts_extra`/`_preparer_osmosis`, leur seul
consommateur réel dans le fichier, consolidant toute la logique
osmosis/JRE/mapwriter en un seul endroit contigu.

Relocalisation pure au sein de `lidar2map.py` (aucun nouveau fichier, aucune
ligne créée hors un court commentaire d'explication) : pas de changement de
comportement possible par construction, donc pas de caractérisation dédiée
requise au-delà de la suite existante.

- Validation : CLI réel (`--version`), les tests touchant déjà à
  osmosis/mapwriter (`_test_atomic_publications.py`,
  `_test_corrections.py`), profils `fast` (26,5 s) et `scientific` (83,2 s)
  complets, tous verts. Ruff propre.

### Sous-phase 9b : couche pure extraite (terminée)

`_ombrages_pures.py` (2042 lignes) contient désormais l'IO raster
(`_sauver_array_georef`, `_publier_tif_atomique`, `_lire_dem_rasterio`,
`_nodata_mask`, `_source_a_des_donnees`, `_percentiles_grille`), les kernels
numba (horn, SVF ×3 variantes, cache JIT), et les algorithmes de calcul par
type (`_hillshade_*`, `_slope_numpy`, `_lrm_*`, `_svf_*`, `_rrim_chunked`,
`_build_vrt_xml`). C'est la plus grosse extraction du plan à ce jour — plus
que toute la phase 7 réunie.

**Deux décisions de conception, prises après une analyse AST précise du
couplage (12 noms libres avant transformation, dont 7 stdlib) :**

1. **`SVF_GAMMA` et `_stop_event` ont leur foyer canonique déplacé dans le
   nouveau module**, plutôt qu'injectés. Motif : plusieurs fonctions
   (`_hillshade_chunked_multi`, `_svf_chunked`, `_svf_opos_chunked`,
   `_svf_numpy`, `_rrim_chunked`) lisent `_stop_event` en variable libre et
   sont appelées **directement par les tests** (`_test_corrections.py`,
   des dizaines d'appels positionnels sans façade) — les injecter aurait
   cassé tous ces appels. `lidar2map.py` réexporte les deux noms
   (`from _ombrages_pures import SVF_GAMMA, _stop_event`) : identité
   d'objet préservée, donc le handler SIGINT de `lidar2map.py` continue de
   piloter l'annulation correctement (mutation via `.set()`/`.clear()`,
   jamais de réaffectation — vérifié sur toutes les suites avant de choisir
   cette voie).
2. **3 fonctions (`_sauver_array_georef`, `_publier_tif_atomique`,
   `_build_vrt_xml`) reçoivent une dépendance keyword-only** (`formater_duree`,
   `valider_tif`, `ecrire_texte_atomique` respectivement) **dans le nouveau
   module**, mais leur **façade dans `lidar2map.py` garde la signature
   positionnelle historique** — l'injection est absorbée par la façade,
   aucun appelant existant à modifier. Ce choix a été validé a posteriori :
   le test qui monkeypatche `_build_vrt_xml` en bloc
   (`mock.patch.object(L, "_build_vrt_xml", side_effect=build_vrt)`, avec un
   faux à 3 arguments) est passé sans aucune modification, exactement parce
   que la façade absorbe le 4ᵉ argument avant de déléguer.
3. **8 fonctions purement internes au nouveau module** (`_appliquer_z_factor`,
   `_calc_slope_aspect`, `_ensure_numba`, 3 des 4 accesseurs de kernels numba,
   `_percentiles_grille`, `_remplir_nodata_moyenne`) **ne sont pas réexportées** :
   ruff (F401) a confirmé qu'aucun code restant dans `lidar2map.py` ni aucun
   test ne les référence — les réexporter aurait été du bruit. 4 autres
   fonctions (`_hillshade_numpy`, `_hillshade_multi_numpy`, `_slope_numpy`,
   `_get_numba_svf_opos_kernel`) sont réexportées avec un `noqa` motivé
   (testées directement, mais sans consommateur restant dans `lidar2map.py`).
- `_NUMBA_KERNELS_CACHE` (dict de cache JIT) a été oublié à la première passe
  de la façade — trouvé par `_test_corrections.py` qui le mute directement
  (`l2m._NUMBA_KERNELS_CACHE["horn"] = None`) pour forcer une recompilation
  entre deux scénarios de test. Corrigé en l'ajoutant au réexport (même
  logique de partage d'identité que `_stop_event`).

- Validation : `_test_corrections.py` (140 références au domaine, résultats
  numba bit-exacts confirmés), 4 nouveaux contrats de façade
  (`OmbragesPuresFacadeContractTests`, dont un qui vérifie que le
  monkeypatch direct de `_valider_tif_dalle` est bien vu par
  `_publier_tif_atomique`), 78 contrats au total, profils `fast` (24,3 s) et
  `scientific` (82,1 s) complets, tous verts. Ruff propre. Garde de
  déploiement (`_test_patch_delivery.py`) a détecté le nouveau module
  automatiquement et a d'abord échoué avant l'enregistrement dans
  `deploy.py`/`ci_github.yml` — exactement le rôle qu'il doit jouer.

`lidar2map.py` : 18 379 → 16 418 lignes (**-1961**, dont ~2000 lignes de code
déplacé net d'environ 45 lignes de façades). Total sorti du monolithe :
**4 897 lignes, 22,97 %** du périmètre figé — la plus forte progression
mesurée sur une seule sous-phase de tout le plan.

### Sous-phase 9c : fetch provider + composites VAT/MSTP extraits (terminée)

`_ombrages_provider.py` (508 lignes) regroupe deux familles distinctes
colocalisées : le téléchargement/désencapsulation d'ombrages précalculés WCS
(`_extraire_tiff_multipart`, `_post_fetch_si_besoin`, `_fetch_provider_shadings`)
et les composites qui blendent des couches déjà produites par
`_ombrages_pures` (`_vat_compose`, `_mstp_chunked`, `_e4mstp_compose`).

**Le groupe composite (VAT/MSTP) s'est révélé sans couplage applicatif du
tout** — analyse AST : seuls `_nodata_mask`/`_stop_event` (déjà réexportés
depuis `_ombrages_pures.py`, import cross-module direct, aucune duplication)
et deux constantes propres (`VAT_OPOS_OPACITY`, `VAT_SLOPE_OPACITY`, utilisées
uniquement comme défauts de `_vat_compose`) — réexport pur, aucune façade.

**Le groupe fetch provider a reproduit intentionnellement le correctif
`_wmts_fetch` de la phase 7c**, cette fois anticipé plutôt que découvert après
coup : un test (`_test_atomic_downloads.py`) remplace `L._extraire_tiff_multipart`
en bloc puis appelle `L._fetch_provider_shadings`, et attend que l'appel
interne voie le remplacement. `_extraire_tiff_multipart` est donc injectée
comme *callable* dans `_post_fetch_si_besoin` et `_fetch_provider_shadings`
(pas un bare-name interne), lues depuis la façade `lidar2map.py` à chaque
appel — exactement le schéma qui avait dû être corrigé après un run cassé en
7c. Repéré cette fois par lecture du code AVANT l'extraction (grep des
monkeypatches existants), pas par un test qui casse.

`PROVIDER` est injecté comme objet entier (pas une valeur dérivée comme
`CRS_NATIF` en 7e) : les fonctions font plusieurs `getattr(PROVIDER, "...",
défaut)` sur des attributs différents (`post_fetch`, `WCS_URL`,
`WCS_AXIS_LABELS`, `_SSL_CTX`), donc seul l'objet complet, relu à chaque
appel, couvre tous les cas — validé par un contrat qui réaffecte `L.PROVIDER`
en cours de test.

- Validation : `_test_atomic_downloads.py` (le test `_extraire_tiff_multipart`
  + `_fetch_provider_shadings` mentionné ci-dessus, et les tests d'ombrages
  provider truncated/validated), `_test_corrections.py` (VAT/MSTP/e4MSTP,
  `_extraire_tiff_multipart`, réassignation directe historique de
  `_post_fetch_si_besoin`), 5 nouveaux contrats de façade
  (`OmbragesProviderFacadeContractTests`), 83 contrats au total, profils
  `fast` (25,9 s) et `scientific` (81,3 s) complets, tous verts. Ruff propre.
  Garde de déploiement dérivé de l'AST : détection automatique du nouveau
  module, aucune modification manuelle du test lui-même.

`lidar2map.py` : 16 418 → 16 006 lignes (**-412**, cohérent avec l'estimation
de ~470 lignes candidates). Total sorti du monolithe : **5 309 lignes,
24,91 %** du périmètre figé.

### Sous-phase 9d : presets/parsing extraits, `generer_ombrages` scindée du périmètre (terminée)

Lecture complète de `generer_ombrages` (736 lignes) avant toute extraction —
verdict tranché avec Nico plutôt qu'exécuté directement, décision documentée
ici pour la suite du plan.

**Livré : `_shading_specs.py`** (133 lignes) — `_SHADING_TYPES`,
`SHADING_TYPES_ORDRE`, `SHADING_TOUS`, `SHADING_PRESETS`,
`_resoudre_preset_shading`, `parser_shading_spec`. Analyse AST confirmée :
**zéro dépendance externe**, réexport pur sans façade, même sûreté que les
helpers de 7e.

**`generer_ombrages` elle-même reste dans `lidar2map.py`, décision
délibérée, pas un report technique.** Contrairement à la résolution de zone
de 8c (5 branches indépendantes, 190 lignes), c'est une **seule fonction
continue de 736 lignes** :

- 3 closures internes (`_preparer_sortie_ombrage`, `_abandonner_sortie_ombrage`,
  `_publier_sortie_ombrage`) fermant sur un état partagé
  (`_parts_ombrages_actifs`, `_sorties_a_regenerer`) qui traverse toute la
  fonction ;
- ~9 chemins de dispatch par type d'ombrage (hillshade/slope, SVF/opos/oneg,
  LRM, RRIM, VAT, e4MSTP), chacun avec son propre repli mémoire pleine et son
  propre nettoyage ;
- un `try/finally` global dont la cohérence dépend de tous ces chemins ;
- une couverture de **test directe** de l'orchestrateur elle-même fine (6
  références dans toute la suite, contre 140+ pour les briques déjà extraites
  en 9b) : la sécurité actuelle vient de tester les *pièces* (déjà extraites),
  pas l'*orchestration* (dédoublonnage d'instances, construction VRT,
  complétude finale des cibles).

Extraire cette fonction sans caractérisation dédiée aurait reproduit le
risque déjà signalé deux fois (8c, 9c) — sauf que cette fois aucun test
existant n'aurait détecté une régression de comportement dans la logique
d'orchestration elle-même. Décision : laisser `generer_ombrages` comme
orchestrateur légitime dans `lidar2map.py`, cohérent avec la règle du plan
« extraire d'abord les composants purs, puis les orchestrateurs » — tous les
composants purs du domaine ombrages sont désormais extraits (9b, 9c, 9d),
l'orchestrateur peut attendre un investissement dédié en caractérisation s'il
est un jour repris.

- Validation : CLI réel (`--help`, `--shadings`), `_test_corrections.py`
  (parsing/presets/types), `_test_interactions.py` (cohérence GUI ↔
  `_SHADING_TYPES`), 83 contrats de façade (assertions d'identité ajoutées,
  pas de nouvelle classe puisque réexport pur), profils `fast` (28,0 s) et
  `scientific` (93,1 s) complets, tous verts. Ruff propre.

`lidar2map.py` : 16 006 → 15 895 lignes (**-111**, cohérent avec les 118
lignes du bloc pur). Total sorti du monolithe : **5 420 lignes, 25,43 %**.

### Prochaine étape

Le bloc ombrages/COG (phase 9) est fonctionnellement épuisé de ses
composants purs à risque raisonnable : IO raster, kernels numba, algorithmes
par type (9b), fetch provider et composites (9c), types/presets/parsing
(9d). Il ne reste que `generer_ombrages` elle-même, volontairement laissée en
l'état (voir ci-dessus). Sauf décision de caractériser cet orchestrateur en
profondeur, la phase 9 est considérée terminée à ce niveau de risque
acceptable. Déployée en **v1.35.0** (11 août 2026).

Déployé : bump `VERSION` 1.34.0 → 1.35.0, `deploy.py --new-tag`, tag
`v1.35.0` poussé, `release.yml` déclenché (build Windows/macOS×2/Linux).

## Phase 10 : GeoJSON/Mapsforge (terminée et déployée)

L'état des lieux initial a été corrigé avant d'engager cette phase. La colonne
précédemment nommée « fonctions top-level » comptait en réalité **tous** les
`FunctionDef` de l'AST, y compris les closures et méthodes. Les vrais nombres de
fonctions top-level du snapshot post-phase 9 étaient : bootstrap 15, RMAP 30,
split 36, GeoJSON/Mapsforge 10, bulk BD TOPO 6, fusion 12 et interface graphique
7. Cette correction confirme notamment que `lancer_gui()` reste une fonction de
1 401 lignes et que le bloc GeoJSON est dominé par trois orchestrateurs longs,
pas par 31 petites fonctions indépendantes.

### Audit de frontière

Deux candidats ont été lus intégralement et comparés avant modification :

- **bootstrap** : extraction différée. Sa bannière de 1 348 lignes mélange le
  cœur bootstrap, des commandes top-level et le logger. Le cœur s'exécute à
  l'import, avant l'insertion normale du répertoire des modules, et peut muter
  l'environnement, relancer le processus, installer via pip ou sortir. Les
  suites actuelles le neutralisent avec `LIDAR2MAP_BOOTSTRAP=none` ; elles ne
  caractérisent donc presque aucun de ses chemins actifs ;
- **GeoJSON/Mapsforge** : le bloc initial de 1 128 lignes contenait un noyau pur
  bien séparable, puis `rasteriser_geojson_transparent` (409 lignes),
  `geojson_ign_vers_osm_xml` (320 lignes) et
  `generer_map_depuis_geojson_ign` (119 lignes). Ces trois orchestrateurs ont
  des coutures IO/atomiques et des monkeypatches existants ; l'audit a donc
  imposé une extraction séquentielle avec caractérisation propre à chacun.

### Sous-phase 10a : noyau GeoJSON pur extrait (terminée)

`_geojson_geometry.py` (246 lignes) contient désormais :

- les correspondances IGN→OSM et styles d'overlay (`_IGN_LAYER_TAGS`,
  `_OVERLAY_STYLE`, `_tags_pour_layer`, `_overlay_style_key`) ;
- la décomposition des géométries et le maintien des trous de polygones
  (`_overlay_sequences`) ;
- les algorithmes Liang–Barsky et Sutherland–Hodgman (`_seg_inter_box`,
  `_clip_polygone_rect`) ;
- Douglas–Peucker, sa constante historique et le choix d'epsilon selon la
  surface (`_douglas_peucker`, `_IGN_SIMPLIFY_EPSILON`,
  `_epsilon_depuis_surface_km2`).

Le module ne dépend que de `math` et ne réalise aucune IO. Ses douze symboles
historiques sont réexportés directement par `lidar2map.py`. Les dictionnaires de
styles restent les mêmes objets : `_tags_pour_layer` continue donc de renvoyer
les mêmes valeurs par identité. Aucun de ces symboles n'était réassigné ou
monkeypatché dans les suites existantes.

Tests ajoutés **avant** l'extraction : priorité tags/styles, conservation des
trous dans une `GeometryCollection`, simplification avec coude significatif et
frontières exactes des quatre seuils d'epsilon. La matrice multi-géométries et
le repli `layer_hint` complètent ce contrat. Après extraction, les contrats
d'identité façade↔module ont été ajoutés pour les douze symboles. Les tests déjà
présents continuent de couvrir le clipping de segment, le clipping de polygone,
la rasterisation transparente réelle, les trous, les anneaux dégénérés et les
publications atomiques OSM/Mapsforge.

- Validation ciblée : compilation, Ruff, 10 contrats ciblés, garde de livraison,
  `_test_tiling.py`, `_test_corrections.py` et les 19 tests de
  `_test_atomic_publications.py`, tous verts.
- Validation globale : profil `fast` (27,8 s, 8 suites) et profil `scientific`
  (88,6 s, 5 suites), tous verts.
- Déploiement : `_geojson_geometry.py` ajouté à `deploy.MAP`, rebuild requis par
  le motif `_geojson_*.py`, et même motif ajouté aux filtres push/PR de la CI.
- Mesure : `lidar2map.py` 15 895 → 15 641 lignes (**-254**) ; total sorti
  **5 674 lignes, 26,62 %** du périmètre figé.

### Sous-phase 10b : conversion GeoJSON IGN → OSM XML extraite (terminée)

`_geojson_osm_xml.py` (370 lignes) porte désormais le convertisseur streaming
de 320 lignes. `lidar2map.py` conserve la signature historique exacte
`(geojson_path, osm_xml_path, epsilon=None)` et reconstruit à chaque appel une
dataclass frozen de six coutures :

- `_chemin_part` et `_stop_event`, déjà patchés ou mutés par les tests ;
- la table `_IGN_LAYER_TAGS`, `_tags_pour_layer`, `_douglas_peucker` et
  `_IGN_SIMPLIFY_EPSILON`, relus eux aussi depuis la façade afin qu'une
  réassignation future ne soit pas figée dans le module extrait.

La nouvelle suite `_test_geojson_osm.py`, enregistrée dans le profil `fast`, a
d'abord été exécutée sur l'implémentation monolithique. Ses huit scénarios
verrouillent :

- Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon et les
  cinq sous-types historiquement pris en charge dans `GeometryCollection` ;
- IDs négatifs, fermeture des anneaux, références valides et ordre strict
  `bounds → nodes → ways` ;
- bounds à sept décimales, tags IGN et échappement XML des cinq caractères
  sensibles ;
- epsilon par défaut/explicite, lecture `.geojson.gz`, flux tronqué après une
  première feature, entrée vide, échec de publication et nettoyage des `.part`.

Un défaut préexistant a été révélé par le scénario dédié au troisième appel à
`_chemin_part` (staging XML final) : si cette création de chemin levait,
les bodies `nodes` et `ways` restaient orphelins. Le test a d'abord échoué avec
les deux fichiers présents ; le correctif conserve la propagation de
l'exception mais les supprime désormais systématiquement.

Deux contrats de façade supplémentaires vérifient la signature, l'identité de
l'implémentation et la relecture des six coutures après réassignation. Le patch
historique de `L.geojson_ign_vers_osm_xml` depuis le runner Mapsforge reste
valide, car `generer_map_depuis_geojson_ign` demeure dans `lidar2map.py`.

- Validation ciblée : compilation, Ruff, 12 contrats ciblés, 8 scénarios OSM
  XML, garde de livraison, 19 publications atomiques et suite de corrections,
  tous verts.
- Validation globale : profil `fast` (29,4 s, 9 suites) et profil `scientific`
  (84,9 s, 5 suites), tous verts.
- Déploiement : `_geojson_osm_xml.py` ajouté à `deploy.MAP`; le rebuild et les
  deux filtres CI étaient déjà couverts par `_geojson_*.py` depuis 10a.
- Mesure : `lidar2map.py` 15 641 → 15 345 lignes (**-296**) ; total sorti
  **5 970 lignes, 28,01 %** du périmètre figé.

Limite volontairement conservée : dans une `GeometryCollection`, `MultiPoint`
et une autre `GeometryCollection` imbriquée sont ignorés, comme avant 10b. Une
évolution de ce comportement devra être traitée comme une fonctionnalité, pas
glissée dans une extraction structurelle.

### Sous-phase 10c : rasteriseur GeoJSON transparent extrait (terminée)

`_geojson_raster.py` (565 lignes) porte désormais l'ancien orchestrateur de
409 lignes. La façade conserve strictement la signature historique
`(geojson_path, sqlitedb_out, zoom_min, zoom_max, ecraser=False,
supersample=2, bbox_wgs84=None)` et reconstruit à chaque appel une dataclass
frozen de douze coutures :

- publication atomique : `_chemin_part`, `_nettoyer_sqlite_part` et
  `_valider_sqlite_part` ;
- arrêt et grille : `_stop_event` et `deg_to_tile` ;
- styles/géométrie : les trois valeurs `_OVERLAY_*` et les quatre helpers
  `_overlay_style_key`, `_overlay_sequences`, `_clip_polygone_rect` et
  `_seg_inter_box`.

Les mappings mutables et l'événement partagé sont injectés par identité, jamais
copiés. Pillow reste importé dans la fonction et `ijson` dans l'itérateur :
l'import de `lidar2map` ne gagne donc aucun prérequis. Les trois appelants
`main`, `main_wfs` et `main_fusionner` continuent d'utiliser le nom de façade.

La nouvelle suite `_test_geojson_raster.py`, ajoutée au profil `fast`, a été
exécutée **avant** le déplacement. Sur le monolithe, cinq scénarios passaient et
trois échouaient réellement :

- `KeyboardInterrupt` après ouverture SQLite laissait le `.part` ;
- une exception ordinaire au même endroit produisait la même fuite ;
- un échec du `replace` de publication conservait également le staging.

Le correctif transactionnel ferme maintenant la connexion dans un `finally` et
nettoie le chantier SQLite complet (`.part`, `-wal`, `-shm`, `-journal`) sur
toute `BaseException`, y compris un échec de publication. L'ancien livrable
final n'est jamais supprimé avant le remplacement réussi. Les huit tests sont
désormais verts et couvrent aussi la réutilisation sans `--overwrite`, la source
absente, les géométries non dessinables/hors zone, l'entrée gzip, le schéma
OsmAnd, les PNG RGBA, le rejet du validateur et l'arrêt avant ouverture.

Deux contrats de façade supplémentaires vérifient la signature exacte,
l'identité implémentation/module et la relecture des douze coutures après
réassignation. Les scénarios réels de `_test_tiling.py` confirment en plus les
traits, bâtiments, trous transparents, niveaux de zoom et métadonnées SQLite.

- Validation ciblée : compilation, Ruff, 8 scénarios raster, 14 contrats
  GeoJSON/façade ciblés, rendu réel, garde de livraison et publications
  atomiques, tous verts.
- Validation globale : profil `fast` (32,8 s, 10 suites) et profil `scientific`
  (89,0 s, 5 suites), tous verts.
- Déploiement : `_geojson_raster.py` ajouté à `deploy.MAP`; rebuild, filtres CI
  et analyse PyInstaller déjà couverts par le motif `_geojson_*.py`.
- Mesure : `lidar2map.py` 15 345 → 14 976 lignes (**-369**) ; total sorti
  **6 339 lignes, 29,74 %** du périmètre figé.

### Sous-phase 10d : runner GeoJSON IGN → Mapsforge extrait (terminée)

`_geojson_mapsforge.py` (187 lignes) porte désormais l'ancien orchestrateur de
119 lignes. La façade conserve la signature exacte
`(geojson_src, dossier_ville, nom_zone, bbox_wgs84, ecraser=False,
epsilon=None)` et reconstruit à chaque appel une dataclass frozen de onze
coutures : convertisseur XML, préparation et exécution osmosis, staging,
signature/cache, options Java, journalisation, formatage de durée et indicateur
Windows.

La suite `_test_geojson_mapsforge.py`, enregistrée dans le profil `fast`, a été
exécutée **avant** l'extraction. Sept de ses huit scénarios passaient ; le
huitième révélait qu'un échec du `Path.replace` final préservait bien l'ancien
`.map`, mais laissait le nouveau `.map.part`. Le garde couvre désormais toute
l'exécution et la publication : `RuntimeError`, `KeyboardInterrupt` et échec de
renommage nettoient le staging, tandis que l'OSM intermédiaire reste disponible
pour diagnostic.

Les contrats verrouillent également :

- le payload de signature (nom, mtime arrondi, bbox à six décimales, epsilon),
  la migration douce sans sidecar et l'invalidation du cache ;
- le succès atomique et les trois sorties infructueuses d'une invocation
  osmosis (code non nul, fichier vide, fichier absent) ;
- la commande POSIX, la commande `.bat` quotée, l'ordre de la bbox,
  `JAVA_HOME`, le respect d'un `JAVA_OPTS` existant et son défaut ;
- l'identité implémentation/module et la relecture dynamique des onze coutures
  après monkeypatch de la façade.

Le test historique de publication IGN reste vert : les patches de
`L.geojson_ign_vers_osm_xml`, `L._preparer_osmosis` et
`L._run_osmosis_streaming` continuent donc de traverser la façade.

- Validation ciblée : compilation, Ruff, 8 scénarios Mapsforge, 16 contrats
  GeoJSON/façade ciblés, 19 publications atomiques et garde de livraison, tous
  verts.
- Validation globale : profil `fast` (36,8 s, 11 suites) et profil `scientific`
  (89,8 s, 5 suites), tous verts.
- Déploiement : `_geojson_mapsforge.py` ajouté à `deploy.MAP`; le motif
  `_geojson_*.py` impose le rebuild et couvre déjà les filtres CI/PyInstaller.
- Version de rebuild : `VERSION` passe de 1.35.0 à **1.36.0**. Le code a été
  poussé sur `main`, puis deux hypothèses de tests propres au layout local ont
  été rendues portables (workflow CI renommé dans le clone GitHub et chemins
  temporaires canoniques macOS/Windows). La CI `main` et la CI du tag sont vertes.
- Livraison : `deploy.py --new-tag` a créé le tag annoté `v1.36.0` sur le commit
  `30f9b7434f7b8ba6456a9268feb9f0af9e385683`. Le
  [workflow de release](https://github.com/nico579/lidar2map/actions/runs/31488074568)
  a construit et publié avec succès les quatre archives Windows x86_64, Linux
  x86_64, macOS arm64 et macOS x86_64. Leurs digests GitHub correspondent tous à
  la table SHA-256 de la [release v1.36.0](https://github.com/nico579/lidar2map/releases/tag/v1.36.0).
- Mesure : `lidar2map.py` 14 976 → 14 895 lignes (**-81**) ; total sorti
  **6 420 lignes, 30,12 %** du périmètre figé.

### Prochaine phase proposée : 11 — bootstrap

Commencer par des tests de caractérisation du bootstrap actif, actuellement
presque toujours neutralisé par `LIDAR2MAP_BOOTSTRAP=none`. Les contrats à poser
avant tout déplacement concernent la résolution CLI/environnement, la relance
Windows/Unix, les codes de sortie, TLS, pip et le mode frozen. Le premier lot de
code éventuel restera volontairement petit et pur ; le cœur bootstrap complet ne
sera déplacé qu'après ces garde-fous.

## Phase 11 : bootstrap (en cours)

### Sous-phase 11a : contrats actifs et politique GUI pure (terminée localement)

L'audit a séparé le vrai cœur bootstrap (726 lignes, de la résolution du mode à
l'orchestrateur) de la bannière beaucoup plus large qui contient aussi des
commandes top-level et le logger. Ce cœur s'exécute avant le logger et peut
modifier `sys.argv`, l'environnement et TLS, créer un venv, lancer pip,
remplacer le processus ou appeler `sys.exit`. Il n'est donc pas déplacé en bloc.

La nouvelle suite FAST `_test_bootstrap.py` exerce **24 contrats hors réseau**.
Tous les subprocessus dangereux sont simulés, à l'exception d'un interpréteur
Python isolé utilisé uniquement pour contrôler l'import. Les scénarios couvrent :

- résolution défaut/environnement, deux syntaxes CLI, priorité et trois alias
  historiques, avec conservation des autres arguments ;
- aide dédiée, routage et ordre exact des modes `auto`, `pip`, `none`, ainsi que
  le court-circuit d'un bundle frozen ;
- portée temporaire de `LIDAR2MAP_BOOTSTRAP`, y compris lorsqu'une exception
  remonte ;
- relance Unix par `execv`, relance Windows avec les trois flux, propagation du
  code enfant et conversion de `KeyboardInterrupt` en code 130 ;
- pip déjà présent, repli `ensurepip`, échec fatal, garde `venv` Linux et les
  trois stratégies d'installation hors venv ;
- matrice GUI Darwin/Linux/Windows/plateforme inconnue, listes indépendantes et
  relecture tardive de `platform.system()` par la façade ;
- import complet de `lidar2map.py` par `spec_from_file_location`, sous `python
  -I` et depuis un répertoire de travail étranger.

Le premier déplacement reste volontairement pur. `_bootstrap_policy.py`
(40 lignes) expose `dependances_gui_plateforme(systeme)` et ne réalise aucune
IO, aucun import tiers et aucune mutation globale. `lidar2map.py` conserve la
façade historique `_gui_deps_plateforme()` sans argument ; celle-ci relit la
plateforme à chaque appel, de sorte que les monkeypatches existants continuent
de fonctionner. L'insertion de `_MODULE_DIR` a été avancée juste avant cet
import précoce, ce qui reproduit aussi le comportement normal de
`python lidar2map.py` pour les intégrateurs utilisant un chargement par spec.

La livraison est préparée sans publication : module ajouté à `deploy.MAP`,
rebuild imposé par `_bootstrap_*.py`, filtres push et pull request de la CI
complétés, suite inscrite dans le profil FAST. Les spécifications PyInstaller ne
nécessitent aucun hidden import puisque l'import est statique. La version reste
**1.36.0** tant qu'aucun déploiement n'est demandé.

Validation locale : compilation Python et Ruff propres, 24 contrats bootstrap,
94 contrats de façade et garde de livraison verts ; profil FAST complet
(12 suites, 34,0 s) et profil scientifique complet (5 suites, 82,7 s), tous
verts.

Mesure nette : `lidar2map.py` 14 895 → 14 848 lignes (**-47**, soit **0,22 %**
du périmètre figé). Total sorti : **6 467 lignes, 30,34 %**. La faible taille est
assumée : cette sous-phase construit d'abord le filet de sécurité du bootstrap.

### Sous-phase 11b : moteur venv/pip extrait (terminée localement)

Dix-neuf contrats supplémentaires ont été ajoutés autour du déplacement.
La suite bootstrap porte désormais **43 tests hors réseau**. Les nouveaux cas
couvrent :

- modes `none` et `pip`, imports critiques présents ou manquants ;
- venv géré déjà actif, priorité de `CONDA_PREFIX`, environnement virtuel
  externe et refus d'un venv parallèle ;
- chemins `bin/python` et `Scripts/python.exe`, contrôle d'un venv existant,
  création réussie ou en erreur et relance avec le bon indicateur OS ;
- installation groupée, retry des seules dépendances critiques, optionnelles
  essayées individuellement et échec critique fatal ;
- signatures et docstrings exactes des cinq façades historiques après
  extraction.

Quatre tests correctifs ont d'abord matérialisé les deux défauts observés à
l'audit : ils donnaient trois `SystemExit(1)` et une absence de revalidation.
Le correctif apporte maintenant :

1. les trois stratégies `standard`, `--break-system-packages` et `--user` au
   retry des seules dépendances critiques, y compris hors venv ; une roue
   optionnelle cassée ne condamne donc plus le pipeline principal ;
2. une table unique paquet pip → module Python, utilisée à la détection comme à
   chaque validation. Elle traduit notamment `Pillow`/`PIL`,
   `pywebview`/`webview` et les frameworks PyObjC vers `WebKit`/`Cocoa`. Le
   retry critique revalide aussi les dépendances GUI et `certifi`.

Les trois branches du retry critique (`standard`, PEP 668 et `--user`) sont
atteintes séparément par les tests ; le mapping `pywebview`/`webview` possède
également son contrat dédié.

`_bootstrap_runtime.py` (570 lignes) contient désormais les cinq fonctions à
effets : garde Linux de `venv`, création/réparation du venv, relance Unix ou
Windows, amorçage d'`ensurepip` et installation des dépendances. Le module
n'exécute aucun effet à son import et ne dépend que de la bibliothèque standard.

`lidar2map.py` conserve cinq façades de signatures historiques. Le moteur reçoit
à chaque appel les coutures courantes — résolveur du mode, politique GUI, garde
Linux et relance — afin que les monkeypatches et intégrateurs existants restent
fonctionnels. Les modules stdlib (`sys`, `subprocess`, `platform`, `os`) et la
classe `Path` sont partagés, ce que les tests Windows/Linux vérifient également.
La docstring du moteur est réaffectée à la façade : `--help-bootstrap` garde son
texte et son code de sortie.

La livraison reste préparée sans publication : `_bootstrap_runtime.py` est dans
`deploy.MAP`; le motif `_bootstrap_*.py` de 11a impose déjà un rebuild et couvre
les deux filtres CI. L'import étant statique et précoce, aucune modification des
spécifications PyInstaller n'est nécessaire. La version reste **1.36.0**.

Validation locale : compilation Python, Ruff, garde de livraison et commande
réelle `--help-bootstrap` verts ; profil FAST complet (12 suites, 33,8 s) et
profil scientifique complet (5 suites, 200,6 s), tous verts.

Mesure nette : `lidar2map.py` 14 848 → 14 349 lignes (**-499**, soit **2,34 %**
du périmètre figé). Total sorti : **6 966 lignes, 32,68 %**.

### Sous-phase 11c : politique CLI et orchestration extraites (terminée localement)

Douze contrats supplémentaires portent la suite bootstrap à **55 tests hors
réseau**. Ils verrouillent la mutation en place de `sys.argv`, l'atomicité des
erreurs, la priorité fixe des alias historiques, l'aide prioritaire, le nettoyage
des options dans un bundle frozen, l'arrêt au premier effet en erreur, la pureté
de la politique et la compatibilité syntaxique Python 3.9.

Le premier run correctif a matérialisé sept échecs attendus : cinq variantes de
valeur CLI invalide étaient silencieusement acceptées ou avalaient l'option
suivante, et les deux scénarios frozen ne résolvaient ni les options ni l'aide.

`_bootstrap_policy.py` expose désormais `ResolutionModeBootstrap` et
`resoudre_mode_bootstrap(argv, environnement)`. La politique travaille sur une
copie, retourne un tuple `argv` immuable et ne modifie aucun objet reçu. Les
valeurs CLI invalides ou absentes produisent maintenant une erreur claire de code
2 sans avaler l'option suivante ; `--help-bootstrap` conserve sa priorité et son
code 0. Une valeur d'environnement invalide reste volontairement assimilée à une
absence pour préserver la compatibilité. Les autres priorités historiques restent
inchangées : CLI moderne sur environnement, puis alias legacy dans leur ordre
fixe, avec `--no-venv` gagnant.

La façade `_resoudre_mode_bootstrap()` conserve sa signature, applique le résultat
par tranche (`sys.argv[:]`) afin de préserver l'identité de la liste, et garde
l'impression de l'aide ou des erreurs. `_bootstrap_runtime.py` contient maintenant
`orchestrer_bootstrap`, qui reçoit toutes ses étapes par injection et conserve
l'ordre `auto`/`pip`/`none` ainsi que la propagation immédiate des exceptions. La
résolution précède désormais le court-circuit frozen : les options précoces et
l'aide fonctionnent aussi dans les exécutables, tandis qu'aucun effet venv, pip ou
TLS n'y est lancé.

Le wrapper `bootstrap_venv_avec_mode` conserve explicitement la sémantique
historique : `LIDAR2MAP_BOOTSTRAP` est visible pendant l'appel puis supprimée,
même si une valeur existait auparavant. Une restauration naïve ferait fuir le
mode synthétique dans l'enfant pendant une ré-exécution ; une éventuelle évolution
de ce protocole reste donc séparée. Les trois façades historiques gardent leurs
signatures et les docstrings des implémentations.

Aucun nouveau fichier livrable n'est créé. `_bootstrap_policy.py` et
`_bootstrap_runtime.py` figurent déjà dans `deploy.MAP` ; le motif
`_bootstrap_*.py` impose le rebuild et couvre les deux filtres CI. Les imports
restent statiques, donc les spécifications PyInstaller n'ont besoin d'aucun hidden
import. La version reste **1.36.0** en l'absence de déploiement.

Validation locale : compilation Python, Ruff, 55 contrats bootstrap, 94 contrats
de façade, garde de livraison et commande réelle `--help-bootstrap` verts ; profil
FAST complet (12 suites, 36,7 s) et profil scientifique complet (5 suites,
102,5 s), tous verts.

Mesure nette : `lidar2map.py` 14 349 → 14 270 lignes (**-79**, soit **0,37 %**
du périmètre figé). `_bootstrap_policy.py` compte maintenant 116 lignes physiques
et `_bootstrap_runtime.py` 624, mais seule la baisse nette du monolithe mesure la
progression. Total sorti : **7 045 lignes, 33,05 %**.

### Sous-phase 11d : TLS précoce extrait et durci (terminée localement)

Neuf contrats supplémentaires portent la suite bootstrap à **64 tests hors
réseau**. Ils couvrent la façade historique, `certifi` présent ou absent, la
distinction entre paquet absent et installation cassée, la priorité d'une CA
utilisateur, la publication transactionnelle, la restauration répétée et la
priorité du vrai module TLS lors d'un import par spec hostile.

Le nouveau module `_bootstrap_tls.py` (108 lignes) ne produit aucun effet à son
import et ne dépend que de la bibliothèque standard. `initialiser_tls` et
`restaurer_tls_strict` reçoivent explicitement l'environnement et le module
`ssl` ; `certifi` reste chargé à l'intérieur des fonctions afin de préserver le
premier lancement sur un Python nu et les launchers qui l'excluent.

Le fallback historique non vérifié a été supprimé. Il ne pouvait pas aider les
installations pip, exécutées dans des sous-processus, et laissait en revanche le
processus courant en mode fail-open. Sans `certifi` ni CA utilisateur, lidar2map
rétablit désormais `ssl.create_default_context` et ne publie jamais
`_create_unverified_context`.

Une CA fournie par l'utilisateur garde priorité ; le chemin `certifi` ne complète
que les variables absentes. Le contexte strict est créé avant toute mutation de
l'environnement ou de la fabrique HTTPS : une CA illisible laisse donc l'état
précédent intact. Seule l'absence réelle du paquet est tolérée ; une installation
`certifi` cassée reste une erreur visible et provoque volontairement un arrêt
fail-closed. Le contexte strict est partagé par choix de performance, afin de ne
pas recharger le bundle CA pour chaque connexion ou tuile HTTPS. `urllib` peut y
répéter ses réglages idempotents ALPN/PHA ; aucun appelant ne doit affaiblir
`verify_mode` ni `check_hostname`.

L'insertion de `_MODULE_DIR` a été avancée avant l'import TLS et le dossier du
script est désormais replacé en tête de `sys.path`. La configuration reste ainsi
exécutée avant le launcher et les modes distants, l'import par spec depuis un
répertoire étranger reste fonctionnel et un module homonyme placé plus tôt dans
`sys.path` ne peut pas détourner ce bootstrap. `lidar2map.py` garde
`_SSL_CTX_CERTIFI` et la
façade `_restaurer_tls_strict()` de signature historique.

La livraison est préparée sans publication : `_bootstrap_tls.py` est ajouté à
`deploy.MAP` ; le motif `_bootstrap_*.py` impose déjà le rebuild et couvre les
deux filtres CI. L'import est statique, `certifi` est déjà collecté par les specs
et aucun hidden import supplémentaire n'est requis. La version reste **1.36.0**.

Validation locale : compilation Python, Ruff, 64 contrats bootstrap, garde de
livraison, 320 liens et commande réelle `--help-bootstrap` verts ; profil FAST
complet (12 suites, 40,4 s) et profil scientifique complet (5 suites, 126,9 s),
tous verts.

Mesure nette : `lidar2map.py` 14 270 → 14 234 lignes (**-36**, soit **0,17 %**
du périmètre figé). `_bootstrap_tls.py` compte 108 lignes physiques, mais seule la
baisse nette du monolithe mesure la progression. Total sorti : **7 081 lignes,
33,22 %**.

### Sous-phase 11e : maintenance `--installer-deps` extraite (terminée localement)

Caractériser puis extraire séparément le bloc top-level `--installer-deps`. Ce
lot devra supprimer la duplication du catalogue paquet pip → module déjà présent
dans le runtime, verrouiller la sélection GUI par plateforme, le traitement non
fatal des dépendances optionnelles et le code de sortie. `--desinstaller` restera
un lot ultérieur distinct en raison de ses suppressions récursives ; `--smoketest`
relève du diagnostic et ne sera pas mélangé au bootstrap. Le futur runtime CPython
3.12 décrit dans `correctif_bootstrap_python312_multiplateforme.md` demeure un
chantier distinct.

#### Contrat de prudence pour 11e (à caractériser avant déplacement)

La commande ne lancera jamais un `pip` réel dans les tests : chaque scénario
injectera le lanceur et les imports. Le catalogue unique devra couvrir les noms
pip qui ne sont pas des noms de modules (`Pillow`/`PIL`, `pywebview`/`webview`,
`PyQt6-WebEngine`, PyObjC, `mapbox-vector-tile` et
`cloth-simulation-filter`). La politique cible est explicite :

- une dépendance critique absente ou dont l'installation échoue termine avec le
  code 1 ; elle ne peut pas être présentée comme « optional - skipped » ;
- une dépendance optionnelle échouée est signalée, mais les autres paquets sont
  traités et la commande termine avec le code 0 ;
- les dépendances déjà importables ne déclenchent aucun appel pip ;
- la sélection GUI provient de la politique de plateforme déjà extraite, sans
  réintroduire de test direct de l'OS dans le point d'entrée ;
- les tests verrouillent l'ordre des paquets, les codes de sortie et l'absence
  d'effet réseau ou système.

L'implémentation est maintenant dans `_bootstrap_runtime.py`, derrière la façade
historique `_installer_toutes_dependances()`. La commande top-level conserve sa
sortie immédiate, mais délègue le code de sortie au booléen du moteur. Le
catalogue `MODULE_PAR_PAQUET` est également réutilisé par l'installation normale
du bootstrap : un nom de module ne peut plus diverger entre les deux chemins.

Validation ciblée : **68 contrats bootstrap** hors réseau, dont quatre dédiés à
la maintenance complète, et Ruff ciblé verts. Aucun appel pip réel n'a été
effectué. Mesure nette : `lidar2map.py` 14 234 → 14 189 lignes (**-45**, soit
**0,21 %** du périmètre figé). Total sorti : **7 126 lignes, 33,43 %**.

Cette sous-phase est locale et sera regroupée avec le prochain lot publié ; la
version distribuée actuelle reste v1.37.0.

### Sous-phase 11f : commande top-level `--desinstaller` extraite (terminée localement)

Caractériser d'abord les cibles par système, le calcul de taille et l'échec
partiel de suppression. Cette commande est destructive : aucun déplacement ne
sera fait avant des tests sur répertoires temporaires et une vérification stricte
des chemins. `--smoketest` reste un lot de diagnostic séparé.

Premier incrément : `_bootstrap_runtime.py` expose
`chemins_desinstallation(...)`, une fonction pure qui ne lit ni n'efface le
disque. Elle verrouille les quatre cibles et les variantes Windows/macOS/Linux
par trois contrats hors réseau.

Le second incrément ajoute `desinstaller_lidar2map(...)` et une façade historique
minimale. Les suppressions réelles des tests sont strictement confinées à des
`TemporaryDirectory`; une sentinelle extérieure prouve que seules les quatre
cibles planifiées sont touchées. Le moteur continue après une erreur de
permission, renvoie `False` et la commande sort alors avec le code 1. La mesure
ne suit pas les liens et un lien cible est détaché sans parcourir sa destination.

Validation : **74 contrats bootstrap**, compilation, Ruff et profil FAST complet
verts.
Mesure nette : `lidar2map.py` 14 189 → 14 150 lignes (**-39**, soit **0,18 %**
du périmètre figé). Total sorti : **7 165 lignes, 33,61 %**.

### Sous-phase 11f-b : parité du launcher (terminée localement)

Le runtime, qui ne dépend que de la bibliothèque standard, est maintenant
importé avant le bloc launcher. L'interception frozen de `--desinstaller`
délègue au même moteur que le script et propage le même code d'échec partiel.
Un contrat exécute le vrai point d'entrée en mode frozen simulé : il vérifie la
délégation puis prouve que le ZIP du bundle n'est pas ouvert et qu'aucun
processus n'est relancé.

Validation ciblée : **75 contrats bootstrap**, compilation et Ruff verts.
Mesure nette : `lidar2map.py` 14 150 → 14 125 lignes (**-25**, soit **0,12 %**
du périmètre figé). Total sorti : **7 190 lignes, 33,73 %**.

### Sous-phase 11g : diagnostic `--smoketest` extrait (terminée localement)

Le nouveau module `_smoketest.py` (145 lignes) porte la construction des quatre
pipelines autonomes et de la fusion, la validation des sorties, les délais et le
bilan agrégé. La façade historique `_executer_smoketest()` conserve une signature
vide et le point d'entrée traduit son booléen en code de sortie.

Cinq contrats supplémentaires simulent tous les sous-processus : réussite des
cinq modes et création des sorties, sorties absentes ou vides, fusion ignorée si
OSM échoue, timeout avec poursuite des autres modes, refus d'utiliser des sorties
anciennes lorsque leur nettoyage échoue, et signature de façade. Aucun réseau ni
pipeline réel n'est appelé. Le nettoyage incomplet est désormais un échec
explicite, ce qui évite qu'un ancien fichier fasse passer le diagnostic à tort.

Le module est enregistré dans `deploy.MAP`, les deux filtres CI et la garde de
rebuild. L'import statique suffit aux analyses PyInstaller.

Validation : **80 contrats bootstrap/maintenance**, compilation, Ruff et garde
de livraison verts. Mesure nette : `lidar2map.py` 14 125 → 14 009 lignes
(**-116**, soit **0,54 %** du périmètre figé). Total sorti : **7 306 lignes,
34,28 %**.

La phase 11 est fonctionnellement terminée localement. La version reste 1.37.0
et aucun déploiement de ces lots locaux 11e-g n'a encore été lancé.

### Prochaine étape proposée : phase 12 — infrastructure partagée

Auditer d'abord logger, secrets, HTTP et helpers atomiques restants, puis choisir
le plus petit cluster pur. La redaction des secrets et les publications
atomiques devront être caractérisées avant tout déplacement.

### Sous-phase 12a : helpers purs de journalisation extraits (terminée localement)

Le nouveau module `_logging_helpers.py` regroupe la rédaction des options
`--api-key`/`--apikey`, le formatage des durées et la construction des lignes de
requête HTTP ou subprocess. Les façades `_rediger_secrets`, `_hms` et `_log_req`
gardent leurs signatures ; `_log_req` conserve l'effet `print(..., flush=True)`
dans le monolithe.

Quatre contrats couvrent les deux syntaxes de secret, les seuils 60 secondes et
une heure, les commandes et URL, ainsi que les signatures de façade. Le module
est enregistré dans `deploy.MAP`, les deux filtres CI et la garde de rebuild.

Validation ciblée : **84 contrats bootstrap/infrastructure** et Ruff verts.
Mesure nette : `lidar2map.py` 14 009 → 13 987 lignes (**-22**, soit **0,10 %**
du périmètre figé). Total sorti : **7 328 lignes, 34,38 %**.

### Sous-phase 12b : logger atomique extrait (terminée localement)

Le nouveau module `_tee_logger.py` (232 lignes) porte la classe `TeeLogger` sans
réécriture de son algorithme. `lidar2map.py` réexporte la même classe sous le nom
historique `_TeeLogger`; l'activation top-level, l'enregistrement `atexit` et le
hook d'exception restent dans la façade pour préserver l'ordre de démarrage.

Les contrats existants de préfixage des blocs et de progression sont complétés
par la publication uniquement à la fermeture, l'idempotence de `close`, la
conservation du `.part` et l'avertissement si le renommage échoue, l'identité de
la classe réexportée et quarante écritures concurrentes sans perte ni mélange.

Le module est enregistré dans `deploy.MAP`, les deux filtres CI et la garde de
rebuild. Validation ciblée : cinq contrats logger, compilation et Ruff verts.
Mesure nette : `lidar2map.py` 13 987 → 13 772 lignes (**-215**, soit **1,01 %**
du périmètre figé). Total sorti : **7 543 lignes, 35,39 %**.

### Sous-phase 12c : activation du log extraite (terminée localement)

Le nouveau module `_log_activation.py` (74 lignes) reçoit explicitement `sys`,
l'environnement, le chemin du script, la classe logger, la rédaction des secrets
et `atexit.register`. Il choisit le dossier source ou frozen, vérifie son accès,
installe stdout/stderr, le hook d'exception et l'en-tête expurgé. L'appel
automatique `_activer_log()` reste exactement au même endroit dans la façade.

Quatre contrats couvrent la source, la priorité de `LIDAR2MAP_WORK_DIR` en
frozen, le maintien des streams si le dossier est inaccessible, la fermeture
`atexit`, le hook d'exception et la relecture dynamique des dépendances.

Validation ciblée : **88 contrats bootstrap/infrastructure**, compilation et
Ruff verts. Mesure nette : `lidar2map.py` 13 772 → 13 725 lignes (**-47**, soit
**0,22 %** du périmètre figé). Total sorti : **7 590 lignes, 35,61 %**.

### Sous-phase 12d : primitives de publication atomique extraites (terminée localement)

Le nouveau module `_atomic_files.py` (70 lignes) centralise la création d'un
staging unique, le nettoyage borné des sidecars SQLite et la validation en lecture
seule avant publication. `lidar2map.py` conserve les trois façades historiques
`_chemin_part`, `_nettoyer_sqlite_part` et `_valider_sqlite_part`, afin que les
pipelines GeoJSON, Mapsforge et MBTiles ainsi que leurs monkeypatches ne changent
pas de couture.

Quatre contrats directs vérifient la délégation des façades, l'unicité des noms,
la préservation du fichier final, le nettoyage exact de `.part`, `-wal`, `-shm`
et `-journal`, les tables et cardinalités attendues, le rejet des sidecars et la
fermeture effective de la lecture SQLite sous Windows. Les curseurs de validation
sont désormais fermés explicitement avant la connexion.

Le module est enregistré dans `deploy.MAP`, la garde de rebuild et les deux
filtres CI. Validation ciblée : **23 tests de publication atomique**, compilation,
Ruff et garde de livraison verts. Mesure nette : `lidar2map.py` 13 725 → 13 684
lignes (**-41**, soit **0,19 %** du périmètre figé). Total sorti : **7 631 lignes,
35,80 %**. La version reste **1.37.0** en l'absence de déploiement.

### Sous-phase 12e : noyau HTTP commun extrait (terminée localement)

Le nouveau module `_http_helpers.py` (64 lignes) contient uniquement l'ouverture
URL avec User-Agent commun et le téléchargement streaming vers un fichier
temporaire. Les décisions métier restent dans `lidar2map.py` et les providers :
aucun retry, cache, parallélisme, validation GeoTIFF ou politique d'absence n'a été
déplacé.

Les façades `_urlopen` et `_download_to_tmp` gardent leurs signatures. Elles
injectent à chaque appel `urllib.request`, `_urlopen` et `HTTP_CHUNK_SIZE`, ce qui
préserve les monkeypatches historiques. Le contrat reste inchangé : 404 retourne
zéro, les autres statuts HTTP lèvent une erreur, XML/HTML en 200 est rejeté,
`multipart/related` WCS reste accepté, le timeout tuple utilise sa valeur maximale,
la réponse est fermée et `Content-Length` protège contre une coupure silencieuse.

Quatre contrats directs portent la suite des téléchargements atomiques à **12
tests**. La suite de robustesse historique couvre en complément les réponses
binaires, XML et multipart. Le module est enregistré dans `deploy.MAP`, la garde
de rebuild et les deux filtres CI.

Validation ciblée : 12 tests de téléchargements, suite de robustesse, compilation,
Ruff et garde de livraison verts. Mesure nette : `lidar2map.py` 13 684 → 13 639
lignes (**-45**, soit **0,21 %** du périmètre figé). Total sorti : **7 676 lignes,
36,01 %**. La version reste **1.37.0** en l'absence de déploiement.

### Sous-phase 12f : chemins et plateforme extraits (terminée localement)

Le nouveau module `_runtime_paths.py` (33 lignes) calcule sans effet de bord les
cinq racines initiales : dossier de travail, bundle, home partagé, cache et
production. Il expose également les trois indicateurs Windows, Linux et macOS.
Le mode source continue d'ignorer `LIDAR2MAP_WORK_DIR`; le mode frozen lui donne
priorité, puis se replie sur le dossier résolu de l'exécutable. `_MEIPASS` reste
réservé aux ressources bundlées.

Cinq contrats couvrent les chemins source, le launcher portable, le fallback de
l'exécutable, l'absence de création de dossiers, les quatre familles de plateforme
et les constantes réellement publiées par le module principal. Les anciens
contrats structurels cache/production ont été redirigés vers le module extrait,
sans supprimer leurs vérifications CLI et GUI.

Les fonctions `_appliquer_cache_dir` et `_appliquer_production_dir` restent dans
`lidar2map.py` : elles mutent les racines et créent les dossiers, donc ne font pas
partie de cette politique pure. Le nouveau module est enregistré dans `deploy.MAP`,
la garde de rebuild et les deux filtres CI.

Validation ciblée : **93 contrats bootstrap/infrastructure**, suite d'interactions,
compilation, Ruff et garde de livraison verts. Mesure nette : `lidar2map.py`
13 639 → 13 628 lignes (**-11**, soit **0,05 %** du périmètre figé). Total sorti :
**7 687 lignes, 36,06 %**. La version reste **1.37.0** sans déploiement.

### Sous-phase 12g : garde-fou d'espace disque extrait (terminée localement)

Le nouveau module `_disk_guard.py` (45 lignes) contient la remontée vers le
premier parent existant, la conversion des octets en Go et la décision d'arrêt
avant un morceau. Une erreur de `disk_usage` reste non bloquante et retourne
l'infini ; un seuil nul ou négatif n'effectue même pas de sonde.

Les façades `_espace_libre_go` et `_garde_disque` gardent leurs signatures et
leurs docstrings, désormais fournies par le module. Elles injectent tardivement
`shutil.disk_usage`, la sonde historique, `print`, `sys.exit` et
`EXIT_DISK_LOW=3`. Le préchargement glissant et sa marge de deux chunks ne sont
pas déplacés.

Cinq contrats couvrent le parent inexistant, la conversion exacte, l'échec de
sonde, le seuil désactivé, l'espace suffisant et l'arrêt avec progression. Les
**56 tests de reprise découpée** confirment que la garde reste placée avant le
démarrage ou le rejeu d'un morceau.

Validation ciblée : **98 contrats bootstrap/infrastructure**, suite complète de
reprise, compilation, Ruff et garde de livraison verts. Mesure nette :
`lidar2map.py` 13 628 → 13 619 lignes (**-9**, soit **0,04 %** du périmètre figé).
Total sorti : **7 696 lignes, 36,11 %**. La version reste **1.37.0** sans
déploiement.

La phase 12 est close localement : les derniers helpers avec effets de bord
(`_appliquer_cache_dir`, `_appliquer_production_dir`) restent volontairement dans
la façade, leur déplacement isolé n'apportant pas de simplification nette.

### Sous-phase 13a : pipeline WFS extrait (terminée)

Le nouveau module `_wfs_pipeline.py` (297 lignes) prend en charge le nommage des
sorties, la reconstruction locale gzip/raw, la pré-requête `RESULTTYPE=hits`, la
pagination streamée et la publication GeoJSON. La dataclass `DependancesWfs`
reçoit les neuf coutures applicatives ; `lidar2map.py` les reconstruit à chaque
appel et conserve la signature historique de `telecharger_wfs`.

Les invariants existants restent inchangés : `numberMatched` pilote la complétude,
`STARTINDEX` avance du nombre réellement reçu, une page plafonnée sous `COUNT`
n'est pas prise pour une fin de flux, une page en panne est retentée trois fois et
aucun résultat tronqué n'est publié. Les namespaces autres que `BDTOPO_V3`
conservent leur hash anti-collision tandis que le nom historique BD TOPO reste
stable.

Trois contrats de façade vérifient la signature, la relecture dynamique des neuf
dépendances et les noms de fichiers. Deux contrats atomiques supplémentaires
couvrent l'interruption et l'échec de `Path.replace`. Ce dernier a révélé puis
corrigé un résidu historique : l'ancien final était préservé mais le `.part`
restait sur disque lorsque la publication gzip échouait.

Validation ciblée : **97 contrats de refonte**, **25 publications atomiques**,
suite de robustesse, compilation, Ruff et garde de livraison verts. Mesure nette :
`lidar2map.py` 13 619 → 13 390 lignes (**-229**, soit **1,07 %** du périmètre
figé). Total sorti : **7 925 lignes, 37,18 %**. La version reste **1.37.0** sans
déploiement.

### Sous-phase 13b : acquisition bulk BD TOPO extraite (terminée)

Le nouveau module `_bdtopo_bulk.py` (279 lignes) porte la découverte Atom avec
repli `HEAD`, le tri numérique des versions, le téléchargement atomique des
archives 7-Zip et l'extraction du GPKG correspondant exactement au département.
La dataclass figée `DependancesBdtopo` reçoit les coutures réseau, cache, journal,
arrêt et staging ; les deux façades historiques reconstruisent ces dépendances à
chaque appel.

Les invariants de cache sont conservés : un fichier voisin n'est jamais choisi,
un ancien GPKG reste disponible si le réseau ou l'extraction échoue, le membre
extrait doit dépasser le seuil attendu et posséder une structure SQLite valide.
Les archives `.part` et le workspace temporaire sont nettoyés sur toutes les
sorties connues. La connexion de validation SQLite est maintenant fermée
explicitement, y compris lorsqu'une requête de contrôle lève une exception.

Trois contrats de refonte couvrent les signatures, la relecture dynamique des
dépendances, la délégation et le choix de la ressource la plus récente, notamment
le cas `3-10` supérieur à `3-9`. La suite de robustesse existante verrouille le
membre départemental exact, la préservation du cache voisin et de l'ancien final,
le nettoyage après panne réseau et le rejet d'un GPKG trop petit.

Validation ciblée : **100 contrats de refonte**, suite de robustesse, compilation,
Ruff et garde de livraison verts. Mesure nette : `lidar2map.py` 13 390 →
13 188 lignes (**-202**, soit **0,95 %** du périmètre figé). Total sorti :
**8 127 lignes, 38,13 %**. Cette sous-phase est intégrée au lot **v1.38.0**.

### Sous-phase 13c : conversion des couches BD TOPO extraite (terminée)

Le nouveau module `_bdtopo_layers.py` (338 lignes) porte le streaming GeoJSON
avec ajout de la propriété `source`, l'extraction Fiona, le filtre spatial natif,
la reprojection WGS84 avec transformateur réutilisé et la production des formats
gzip et GeoJSON brut. La dataclass `DependancesCouchesBdtopo` isole les six
coutures applicatives ; les façades historiques conservent leurs signatures et
relisent ces coutures à chaque appel.

La publication multi-format a été durcie pendant l'extraction. Les anciens
fichiers sont maintenant sauvegardés jusqu'à la promotion du dernier format ; si
la seconde promotion échoue, le premier format est retiré et tous les anciens
finals sont restaurés. Un nouveau contrat atomique reproduit explicitement cet
échec. Les interruptions continuent de propager leur exception après nettoyage
des fichiers de staging.

Deux contrats de façade supplémentaires verrouillent les signatures, la relecture
dynamique des dépendances et la délégation. Validation ciblée : **102 contrats de
refonte**, **26 publications atomiques**, suite de robustesse, compilation, Ruff
et garde de livraison verts. Mesure nette : `lidar2map.py` 13 188 → 12 930 lignes
(**-258**, soit **1,21 %** du périmètre figé). Total sorti : **8 385 lignes,
39,34 %**. Cette sous-phase est intégrée au lot **v1.39.0**.

### Sous-phase 13d : orchestration bulk BD TOPO extraite (terminée)

`_bdtopo_bulk.py` contient maintenant l'orchestrateur qui relie découverte,
téléchargement GPKG et conversion des couches. Une dataclass distincte injecte
ces trois opérations et la table de correspondance des couches. Un échec critique
de découverte ou d'acquisition retourne toujours `None`, tandis qu'une couche
individuelle non produite est omise sans perdre les résultats précédents ; leur
ordre reste celui de la requête.

Deux contrats supplémentaires couvrent l'ordre et les sorties partielles, les
échecs critiques et la délégation de la façade. Le faible gain net est assumé :
`lidar2map.py` 12 930 → 12 925 lignes (**-5**, soit **0,02 %**), car les
dépendances sont désormais explicites. Total sorti : **8 390 lignes, 39,36 %**.
Cette sous-phase est intégrée au lot **v1.39.0**.

### Sous-phase 13e : acquisition du mode vecteur extraite (terminée)

Le nouveau module `_vector_acquisition.py` (95 lignes) choisit entre le bulk
départemental et le WFS, identifie les seules couches absentes par leur nom de
livrable et conserve l'ordre des sorties. La façade injecte tardivement les deux
producteurs et `ThreadPoolExecutor`, sans déplacer le parseur CLI, la résolution de
zone ni les formats dérivés.

Cinq contrats couvrent un bulk complet, un résultat partiel, l'échec critique et
le WFS parallèle. Le cas bulk vide ne retente désormais chaque couche qu'une seule
fois en WFS ; l'ancien flux effectuait immédiatement un second passage complet.
Deux tests d'entrée `main_wfs` verrouillent la finalisation de l'historique :
`ok` avec le dossier résultat si toutes les couches sont présentes, `ko` suivi
d'une `RuntimeError` si le résultat reste partiel.

Mesure nette : `lidar2map.py` 12 925 → 12 904 lignes (**-21**, soit **0,10 %**
du périmètre figé). Total sorti : **8 411 lignes, 39,46 %**. Cette sous-phase
est intégrée au lot **v1.40.0**.

### Sous-phase 13f : livrables dérivés vectoriels extraits (terminée)

Le nouveau module `_vector_outputs.py` (105 lignes) choisit la source GeoJSON
unifiée, pilote Mapsforge et l'overlay transparent, et retourne un résultat
explicite `source_geojson/complet`. Les quatre coutures de fusion, calcul epsilon,
génération `.map` et rasterisation sont injectées par la façade.

Trois tests d'entrée rouges puis verts ont corrigé un défaut de statut : un
échec de fusion, de Mapsforge ou de l'overlay demandé pouvait auparavant finir
avec un historique `ok` et un code nul. Le run finalise maintenant `ko`, lève une
`RuntimeError` et conserve les GeoJSON acquis. Deux contrats directs vérifient la
délégation, l'agrégation all-of des formats et l'epsilon forcé.

Mesure nette : `lidar2map.py` 12 904 → 12 900 lignes (**-4**, soit **0,02 %**
du périmètre figé). Le gain volontairement faible reflète les dépendances et le
statut désormais explicites. Total sorti : **8 415 lignes, 39,48 %**. Cette
sous-phase est intégrée au lot **v1.40.0**.

### Sous-phase 13g : fusion GeoJSON streamée extraite (terminée)

Le nouveau module `_geojson_merge.py` (229 lignes) porte la lecture raw/gzip,
le parcours incrémental `ijson`, le repli JSON, le calcul de bbox et la
publication atomique. `lidar2map.py` conserve les signatures historiques de
`_lire_geojson`, `fusionner_geojson` et `_fusionner_geojson_compat`. Les trois
coutures applicatives (`_chemin_part`, `_stop_event`, `_lire_geojson`) sont
reconstruites à chaque appel afin de préserver les monkeypatches et les appels
existants.

Quatre contrats atomiques supplémentaires couvrent l'interruption, l'échec de
`Path.replace`, le signalement d'une source absente et l'exclusion de la sortie
des sources. Ils ont révélé puis corrigé une fuite réelle : un refus de
publication conservait bien l'ancien fichier final, mais laissait son `.part`.
Le staging est désormais supprimé pour toute `BaseException` de publication.
Trois contrats de façade verrouillent la signature, la délégation et la
résolution tardive des dépendances.

La livraison est préparée sans publication : `_geojson_merge.py` est ajouté à
`deploy.MAP`; le motif `_geojson_*.py` impose déjà le rebuild et couvre les deux
filtres CI. `main_fusionner` et sa CLI restent dans le monolithe.

Mesure nette : `lidar2map.py` 12 900 → 12 714 lignes (**-186**, soit **0,87 %**
du périmètre figé). Total sorti : **8 601 lignes, 40,35 %** ; le script
principal passe sous le seuil de 60 % avec **59,65 %** restants. Cette
sous-phase est intégrée au lot **v1.40.0**.

### Sous-phase 13h : orchestration de la CLI de fusion extraite (terminée)

Le nouveau module `_geojson_merge_cli.py` (133 lignes) développe les globs,
détermine le chemin de sortie historique et orchestre les livrables issus de la
fusion. La construction `argparse`, les bannières, l'historique et le code de
sortie restent dans `main_fusionner`, ce qui limite la surface déplacée.

Les formats demandés suivent désormais un contrat all-of : Mapsforge et
l'overlay raster sont tous deux tentés, mais un seul échec suffit à produire un
historique `ko` et un code 1. Cinq tests d'entrée ont révélé puis corrigé deux
faux succès pour les retours `None` des générateurs `.map` et raster. Le dossier
de résultat est maintenant enregistré dans l'historique, y compris en cas de
fusion partielle. Quatre contrats directs couvrent les globs triés, le nom de
sortie raw/gzip, l'arrêt des dérivés après échec de fusion et la résolution
tardive des dépendances.

La livraison est préparée sans publication : `_geojson_merge_cli.py` est dans
`deploy.MAP` et reste couvert par le rebuild et les deux filtres CI
`_geojson_*.py`.

Mesure nette : `lidar2map.py` 12 714 → 12 712 lignes (**-2**, soit **0,01 %**
du périmètre figé). Ce faible gain net est volontaire : les façades et le
résultat typé rendent les statuts explicites, tandis que 133 lignes
d'orchestration quittent physiquement le monolithe. Total sorti : **8 603
lignes, 40,36 %** ; reste **59,64 %**. Cette sous-phase est intégrée au lot
**v1.40.0**.

### Sous-phase 13i : export PyOsmium extrait (terminée)

Le nouveau module `_geojson_osm_export.py` (399 lignes) porte la lecture
PyOsmium, le filtrage des géométries, les streams thématiques, la construction
du GeoJSON global et les formats raw/gzip. `lidar2map.py` conserve la signature
historique de `generer_geojson_osm` et reconstruit six coutures à chaque appel :
filtres OSM, staging, décompression, publication groupée et durée.

Un test rouge a démontré qu'un échec au milieu des renommages pouvait laisser
un ensemble hybride d'anciens et de nouveaux GeoJSON. La primitive
`publier_groupe_atomique` a été ajoutée à `_atomic_files.py` : elle sauvegarde
tous les finals existants, promeut tous les stagings, puis restaure l'ensemble
complet si une seule promotion échoue. Les sorties thématiques sont toujours
publiées avant le global, qui reste le marqueur final de complétude.

Deux contrats de façade verrouillent signature, délégation et dépendances
tardives. Les trois scénarios atomiques PyOsmium couvrent désormais l'échec de
traitement, le succès complet et la panne au milieu de la publication.

La livraison est préparée sans publication : `_geojson_osm_export.py` est dans
`deploy.MAP`; le motif `_geojson_*.py` couvre déjà rebuild et filtres CI. La
Ce lot est intégré à la release **v1.41.0**.

Mesure nette : `lidar2map.py` 12 712 → 12 376 lignes (**-336**, soit **1,58 %**
du périmètre figé). Total sorti : **8 939 lignes, 41,94 %** ; reste **58,06 %**.

### Sous-phase 13j : statut réel des livrables OSM (terminée)

`_osm_outputs.py` (94 lignes) centralise le choix historique des sorties : carte
par défaut, GeoJSON brut/gzip explicite et overlay transparent. Son résultat
typé applique un contrat all-of et vérifie la présence de chaque fichier
demandé. Une source PBF absente, une bbox non convertible, un export GeoJSON
manquant ou un rasteriseur en échec ne peuvent donc plus être masqués par les
sorties LiDAR d'un run combiné.

Deux tests d'entrée `main()` verrouillent la finalisation `ko` suivie d'une
exception, ainsi que le succès `ok`. Quatre contrats directs couvrent la
délégation tardive, l'échec Mapsforge, la source d'overlay absente et la
tentative de toutes les sorties demandées.

### Sous-phase 13k : pipeline Mapsforge OSM extrait (terminée)

`_osm_map_pipeline.py` (263 lignes) porte maintenant le cache signé, les trois
passes Osmosis, la sélection du tagmapping, la publication `.map`/PBF filtré et
la dégradation GeoJSON historique quand mapwriter manque. Dix-sept coutures
applicatives sont reconstruites par la façade à chaque appel ; la signature
publique de `generer_carte_osm` reste inchangée.

Les contrats de publication atomique continuent de simuler les trois passes :
un échec conserve les anciens `.map` et PBF, nettoie les stagings et les deux
PBF temporaires ; un succès publie les deux sorties. Une panne pendant la
promotion du `.map` restaure désormais aussi l'ancien PBF filtré, au lieu de
laisser une paire hybride. Les contrats R2#26
préservent aussi le mode GeoJSON seul et la dégradation sans plugin mapwriter.

La livraison est préparée sans publication : les deux modules sont dans
`deploy.MAP`; le motif `_osm_*.py` impose le rebuild et figure dans les filtres
push et pull request. Ce lot est intégré à la release **v1.41.0**.

Validation locale : profil FAST complet, 32 publications atomiques, contrats
de refonte et d'historique ciblés, compilation, Ruff, 320 liens documentaires
et garde de livraison verts.

Mesure nette combinée : `lidar2map.py` 12 376 → 12 179 lignes (**-197**, soit
**0,92 %** du périmètre figé). Total sorti : **9 136 lignes, 42,86 %**.

### Sous-phase 13l : politiques OSM extraites (terminée)

`_osm_policy.py` (101 lignes) contient la grammaire anti-injection des filtres,
leur parsing clé/valeur ordonné, la sélection thématique, le hash de
configuration, les sidecars et la signature bbox/tags/PBF. Le module ne dépend
que de la bibliothèque standard. Les façades historiques conservent leurs sept
signatures, le message et le code `SystemExit(1)` des filtres invalides, ainsi
que la résolution tardive du hash et de l'écriture atomique.

Les contrats R2#1, R2#28 et R2#30 restent inchangés : métacaractères shell
refusés, priorité déterministe des clés, wildcard absorbant, bbox ignorée en
mode région et migration douce sans sidecar. Trois contrats de refonte ajoutés
verrouillent les signatures de façade, la délégation et les coutures tardives.

Mesure nette : `lidar2map.py` 12 179 → 12 127 lignes (**-52**, soit **0,24 %**
du périmètre figé). Total sorti : **9 188 lignes, 43,11 %** ; reste **56,89 %**.

La phase 13 est close : les catalogues WFS/BD TOPO et les parsers de
`main_wfs`/`main_fusionner` restent volontairement dans la façade, car leur
déplacement isolé réduirait peu le couplage. Le module est enregistré dans
`deploy.MAP` et couvert par le rebuild et les filtres CI `_osm_*.py`.
La clôture 13i-l est publiée dans **v1.41.0**.

### Sous-phase 14a : runtime Osmosis sans réseau (terminée)

`_osm_runtime.py` (149 lignes) porte les options JVM du bundle, la préparation
ordonnée de mapwriter/Java/Osmosis, l'exécution streamée et le nettoyage des
index temporaires orphelins. Il ne télécharge aucun outil et ne produit aucun
effet à l'import. Les quatre façades historiques conservent leurs signatures ;
la préparation relit `_verifier_mapwriter`, `_trouver_java` et
`_trouver_osmosis` à chaque appel, tandis que le runner reçoit le module
`subprocess` de la façade.

Six contrats hors réseau verrouillent l'ordre et le court-circuit des
prérequis, l'isolation de `user.home` en mode frozen, la whitelist des messages
affichés, le diagnostic limité aux 500 dernières lignes stderr et la
conservation des fichiers récents ou étrangers pendant le nettoyage.

Validation locale : 135 contrats de refonte, 8 scénarios Mapsforge, 32
publications atomiques, garde de livraison, compilation, Ruff, profil FAST,
profil scientifique et 320 liens documentaires verts.

Le module est enregistré dans `deploy.MAP`. Son nom est couvert par le motif
existant `_osm_*.py`, qui impose un rebuild et figure dans les deux filtres CI.
La phase 14 complète est publiée dans la release **v1.42.0**.

Mesure nette : `lidar2map.py` 12 127 → 12 059 lignes (**-68**, soit **0,32 %**
du périmètre figé). Total sorti : **9 256 lignes, 43,42 %** ; reste **56,58 %**.

### Sous-phase 14b : découverte et cache des outils (terminée)

`_osm_runtime.py` contient maintenant `_bin_outil`, `_trouver_java` et
`_trouver_osmosis` sous forme d'implémentations explicites. Les façades
historiques gardent leurs signatures et injectent à chaque appel l'état frozen,
les racines bundle/cache, la plateforme et le téléchargeur courant.

Cinq contrats supplémentaires portent la classe runtime à **11 tests**. Ils
verrouillent le tri déterministe des candidats, l'obligation d'un dossier
`bin/` pour Osmosis, les noms Unix/Windows, la priorité bundle frozen puis cache
persistant et l'appel du téléchargement uniquement en dernier recours. Un échec
du téléchargement Java conserve aussi son diagnostic historique.

Mesure nette : `lidar2map.py` 12 059 → 12 034 lignes (**-25**, soit **0,12 %**
du périmètre figé). Total sorti : **9 281 lignes, 43,54 %** ; reste **56,46 %**.

### Sous-phase 14c : installations transactionnelles (terminée)

`_osm_runtime.py` (487 lignes) porte maintenant `_promouvoir_dossier`,
`_telecharger_osmosis_local` et `_telecharger_jre_local`. Les façades historiques
gardent leurs signatures et injectent les chemins, primitives atomiques,
fonctions réseau, plateforme et générateurs de noms temporaires à chaque appel.

Sept contrats supplémentaires portent la classe runtime à **18 tests**. Ils
créent uniquement des ZIP/TAR locaux et couvrent une installation Osmosis et
JRE valide, les archives corrompues, un `KeyboardInterrupt`, une traversée
`../`, le nettoyage des stagings et la restauration de l'ancien dossier lorsque
la seconde opération de renommage échoue.

Le bit exécutable Unix est désormais posé sur le binaire validé dans le staging,
avant la promotion. Toute interruption ou erreur de promotion nettoie le
staging et propage l'exception ; l'ancien cache reste donc disponible. Les
erreurs réseau ou d'archive prévues conservent le retour historique `None`.

Validation locale : 147 contrats de refonte, 12 téléchargements atomiques,
8 scénarios Mapsforge, compilation, Ruff, garde de livraison, profils FAST et
scientifique, et 320 liens documentaires verts.

Mesure nette : `lidar2map.py` 12 034 → 11 851 lignes (**-183**, soit **0,86 %**
du périmètre figé). Total sorti : **9 464 lignes, 44,40 %** ; reste **55,60 %**.

### Sous-phase 14d : mapwriter et commande outils (terminée)

Le téléchargement atomique du JAR mapwriter et l'orchestration
`--telecharger-outils` sont maintenant dans `_osm_runtime.py` (585 lignes).
La façade conserve les constantes historiques, `_verifier_mapwriter()` et le
nouveau point d'orchestration `_telecharger_outils()`. Le bloc top-level ne fait
plus qu'appeler cette façade puis conserver son `SystemExit(0)` historique.

Cinq contrats supplémentaires portent la classe runtime à **23 tests**. Ils
verrouillent le court-circuit frozen, le cache sans réseau, le passage par un
`.part`, le nettoyage sur erreur de publication ou `KeyboardInterrupt`, la
préservation d'un fichier concurrent et l'ordre Java → Osmosis → mapwriter même
si une étape échoue. Toutes les coutures sont relues à chaque appel.

Validation locale : 152 contrats de refonte, 12 téléchargements atomiques,
8 scénarios Mapsforge, compilation, Ruff, garde de livraison, profils FAST et
scientifique, et 320 liens documentaires verts.

Mesure nette : `lidar2map.py` 11 851 → 11 792 lignes (**-59**, soit **0,28 %**
du périmètre figé). Total sorti : **9 523 lignes, 44,68 %** ; reste **55,32 %**.

La phase 14 est structurellement close : le bloc Java/Osmosis restant dans
`lidar2map.py` est une façade de compatibilité et le point d'appel précoce. Le
module est déjà dans `deploy.MAP` et couvert par le rebuild et les deux filtres
CI `_osm_*.py`. La version reste **1.41.0** tant que le lot n'est pas déployé.

### Prochaine étape proposée : 15 — orchestration terrain restante

Inventorier puis caractériser les frontières autour de `generer_ombrages`, des
téléchargements de dalles, des zones, des planches et des sources autonomes.
Le premier lot devra rester sans changement scientifique et ne déplacer qu'un
orchestrateur dont les dépendances et les effets disque sont déjà injectables.

### Sous-phase 15a : sources autonomes extraites (terminée)

`_terrain_sources.py` (111 lignes) centralise les deux traitements `--source`
autonomes des workflows LiDAR/OSM et raster WMTS. Une dépendance immuable
regroupe les convertisseurs RMAP/SQLiteDB, la finalisation d'historique et son
instant de départ ; la façade la reconstruit à chaque appel.

Les **24 contrats existants et de façade** restent verts : absence de source,
fichier manquant, extension refusée, exigences de formats, succès et échec de
conversion, statut `ok`/`ko`, passage PBF avec `--osm`, et détection CRS TIF
3857 ou natif. Le comportement historique du TIF absent — message de recalcul
puis code 1 — reste volontairement inchangé pendant cette extraction.

Le module est ajouté à `deploy.MAP`; le motif `_terrain_*.py` impose un rebuild
et figure dans les filtres push et pull request. Cette sous-phase est publiée
dans la release **v1.43.0**. Mesure nette : `lidar2map.py`
11 792 → 11 714 lignes (**-78**, soit **0,37 %** du périmètre figé). Total
sorti : **9 601 lignes, 45,04 %** ; reste **54,96 %**.

### Sous-phase 15b : primitives de zone extraites (terminée localement)

`_terrain_zones.py` isole les noms automatiques GPS/bbox, présence d'une zone, repli
Lambert 93 et enveloppe reprojetée. Les façades historiques restent dans
`lidar2map.py` et délèguent à ces primitives ; aucun téléchargement, géocodage
ou changement de contrat CLI n'est introduit. Le parseur des codes INSEE prend
également en charge listes, plages, Corse et outre-mer dans le module pur.

Les règles de catalogue régional (`regions_disponibles` et
`departements_de_region`) sont également déléguées au module pur, avec le
catalogue `_GEOFABRIK` injecté par la façade. Le déplacement des 101 entrées du
catalogue est différé : elles sont encore consommées directement par le choix
des URL PBF et leur déplacement n'apporterait pas, seul, de découplage métier.

Validation locale : **158 contrats de refonte**, profil scientifique ciblé,
compilation et Ruff verts. Mesure nette : `lidar2map.py` 11 714 → 11 635 lignes
(**-79**, soit **0,37 %** du périmètre figé). Total sorti : **9 680 lignes,
45,41 %** ; reste **54,59 %**.

### Sous-phase 15c-1 : Nominatim extrait (terminée localement)

`_terrain_geocoding.py` porte désormais le géocodage Nominatim et son filtrage
des réponses non habitées. La façade conserve la signature historique et injecte
à chaque appel le pays du provider, le User-Agent, le journal réseau et
`urlopen`, ce qui préserve les coutures de test et les providers dynamiques.

Six contrats hors réseau préparent désormais cette extraction : filtrage pays
et type administratif Nominatim, rejet des POI, erreur réseau non fatale,
lecture du cache département sans réseau, trois tentatives Overpass, publication
atomique du cache après succès, marge de 500 mètres et union des départements
d'une région. Overpass, le cache département et l'agrégation régionale restent
encore dans la façade à ce stade.

Validation locale : 7 contrats de géocodage ciblés, compilation, Ruff et garde
de livraison verts. Mesure nette : `lidar2map.py` 11 635 → 11 573 lignes
(**-62**, soit **0,29 %**). Total sorti : **9 742 lignes, 45,70 %**.

### Sous-phase 15c-2 : département et région extraits (terminée localement)

`_terrain_geocoding.py` contient maintenant Overpass, la lecture et publication
du cache département, la marge de 500 mètres et l'union régionale. Les façades
reconstruisent à chaque appel les dépendances de cache, reprojection, réseau,
temporisation et géocodeur département ; les monkeypatches historiques restent
donc observables.

Validation locale : **167 contrats de refonte**, interactions complètes,
compilation, Ruff et garde de livraison verts. Mesure nette : `lidar2map.py`
11 573 → 11 469 lignes (**-104**, soit **0,49 %**). Total sorti : **9 846
lignes, 46,19 %** ; reste **53,81 %**.

### Sous-phase 15d : transformations CRS provider-aware (terminée localement)

Les trois façades `_exiger_pyproj_hors_france`, `_wgs84_vers_natif` et
`_natif_vers_wgs84` délèguent désormais à `_terrain_zones.py`. Le CRS du
provider et le cache de transformers sont injectés à chaque appel. Le repli
pur Python reste limité à EPSG:2154 ; tout autre CRS sans pyproj échoue
explicitement au lieu de produire des coordonnées françaises incorrectes.

Validation locale : **169 contrats de refonte**, interactions complètes et
Ruff verts. Mesure nette : `lidar2map.py` 11 469 → 11 453 lignes (**-16**, soit
**0,08 %**). Total sorti : **9 862 lignes, 46,27 %**.

### Sous-phase 15e : résolveur de zone LiDAR extrait (terminée localement)

Le nouveau module `_terrain_resolution.py` porte l'implémentation active des
cinq modes de zone : région, département, bbox WGS84, GPS et ville. Il conserve
aussi la sélection `--block i/M`, le suffixe stable du nom de zone et le calcul
de grille à partir d'une largeur exprimée comme un côté.

La façade historique `_resoudre_zone_lidar(args, _osm_seul)` reconstruit à
chaque appel une dataclass immuable de 14 dépendances. Les géocodeurs, les
transformations provider-aware, la planification split et les générateurs de
noms restent donc remplaçables par les tests et les intégrations existantes.
L'ancien corps de 176 lignes a été supprimé après comparaison ; il ne subsiste
aucun second chemin de résolution.

Validation locale : les **24 branches du résolveur**, les **170 contrats de
refonte**, les interactions complètes, la compilation, Ruff et la garde de
livraison sont verts. Le profil FAST complet (12 suites isolées) est également
vert. `_terrain_resolution.py` est enregistré dans `deploy.MAP` et couvert par
les motifs de rebuild et de CI déjà applicables à `_terrain_*.py`. La release
préparée pour ce palier porte la version **1.44.0**.

Mesure nette : `lidar2map.py` 11 453 → 11 291 lignes (**-162**, soit **0,76 %**
du périmètre figé). Total sorti : **10 024 lignes, 47,03 %** ; reste **11 291
lignes, 52,97 %**. Il faut encore réduire le point d'entrée de **33,93 %** de sa
taille actuelle pour atteindre la borne haute de la cible (7 460 lignes).

### Sous-phase 15f : orchestration du téléchargement terrain extraite (terminée)

Le nouveau module `_terrain_download.py` sélectionne le moteur direct, COG ou
COPC, calcule le pool de téléchargement sous le plafond du provider, agrège les
statuts et interdit la poursuite sur une erreur. Après succès, il publie la
preuve `dalles_zone.txt` et enregistre en lot les GeoTIFF ainsi que les nuages
LAZ associés dans le manifeste du chunk.

La dataclass immuable `DependancesTelechargementTerrain` reçoit 15 coutures à
chaque appel. Les moteurs réseau et fenêtrés restent dans `lidar2map.py` : leurs
validations atomiques et leurs monkeypatches historiques ne changent pas. La
façade `_telecharger_dalles_zone(...)` conserve exactement sa signature et
réinjecte aussi la politique `_dl_workers_effectif` au lieu de la figer dans le
module extrait.

Huit nouveaux contrats hors réseau couvrent les trois routages, les deux flags
d'overwrite, le cache, la preuve, le nuage LAZ, l'absence de couverture, l'arrêt
avant publication sur erreur, la garde de traversée de chemin et les coutures
tardives. La suite de robustesse existante confirme en plus que toute erreur de
dalle arrête le pipeline et protège l'ancien manifeste.

`_terrain_download.py` est enregistré dans `deploy.MAP` ; le motif
`_terrain_*.py` couvre déjà rebuild et CI. Ce lot est intégré au rebuild
**1.45.0** avec la sous-phase 15g.

Mesure nette : `lidar2map.py` 11 291 → 11 173 lignes (**-118**, soit **0,55 %**
du périmètre figé). Total sorti : **10 142 lignes, 47,58 %** ; reste **11 173
lignes, 52,42 %**.

### Sous-phase 15g : preuve et inventaire `dalles_zone` extraits (terminée)

Les quatre helpers de preuve sont maintenant regroupés dans
`_terrain_download.py` : construction et validation de l'en-tête bbox/provider,
publication atomique de la liste normalisée et résolution des seules dalles de
la zone présentes dans le cache. Le parcours reste proportionnel aux noms de la
zone et ne réintroduit pas de scan global du cache partagé.

Les façades historiques conservent leurs quatre signatures et relisent à chaque
appel le provider, le résolveur sécurisé de chemin, le seuil de validité ainsi
que les primitives de publication et de manifeste. Les anciens inventaires sans
ligne provider restent acceptés ; un provider ou une bbox différents imposent
le repli sur la découverte courante. Les chemins invalides et erreurs locales
sont ignorés dalle par dalle comme avant.

Cinq nouveaux contrats hors réseau portent la suite de refonte à **183 tests**.
Ils couvrent l'en-tête exact, la compatibilité historique, le changement de
provider, le repli sur les noms attendus, les chemins invalides, le seuil de
taille, le tri/dédoublonnage, la publication atomique et les coutures tardives.
Les suites de publications atomiques, robustesse, interactions et livraison
restent vertes, ainsi que compilation et Ruff.

Aucun nouveau fichier de livraison n'est nécessaire : `_terrain_download.py`
était déjà enregistré dans `deploy.MAP` et couvert par les motifs rebuild/CI.
Le lot est livré par le rebuild **1.45.0**.

Mesure nette : `lidar2map.py` 11 173 → 11 144 lignes (**-29**, soit **0,14 %**
du périmètre figé). Total sorti : **10 171 lignes, 47,72 %** ; reste **11 144
lignes, 52,28 %**. Le module `_terrain_download.py` contient désormais 281
lignes physiques ; la faible baisse nette est le coût volontaire des quatre
façades de compatibilité et de leurs injections explicites.

### Sous-phase 15h : staging atomique et téléchargement direct extraits (terminée localement)

Le moteur `telecharger_dalle_directe`, le dossier de staging, la correspondance
des caches LAZ et la recompression DEFLATE résident désormais dans
`_terrain_download.py`. Le moteur conserve l'ordre historique : cache,
`pre_download`, transfert, `post_fetch`, validations, `post_download`,
compression, publication du nuage puis du TIFF et enregistrement au manifeste.
Les retours `ok`, `skip`, `absent` et `erreur`, ainsi que le retry d'un provider à
découverte exacte, sont inchangés.

Une dataclass immuable de quinze dépendances est reconstruite par la façade à
chaque appel. Le provider, les seuils/retries, le téléchargement HTTP, les hooks,
le validateur TIFF, la compression, le staging et le manifeste restent donc
monkeypatchables. Les helpers historiques `_stage_dalle_part`,
`_chemins_nuage_stage`, `_lier_nuage_existant_au_stage`,
`_publier_nuage_stage` et `_comprimer_dalle_deflate` conservent également leurs
signatures ; les façades COG/COPC continuent de les appeler.

Sept contrats ajoutés au cours de 15h portent la suite atomique à **19 tests**.
Ils couvrent le nettoyage sur interruption, le cache sans effet, les retries, le
payload JSON d'erreur, l'absence réelle, la compression invalide, le hardlink
LAZ et la publication d'un nouveau nuage seulement après validation. Un contrat
de façade supplémentaire porte la suite de refonte à **184 tests** et vérifie
toutes les coutures tardives.

Validation locale : suite atomique, 184 contrats de refonte, corrections
scientifiques, robustesse, interactions, garde de livraison, compilation et Ruff
verts. Le contrôle textuel d'overwrite suit maintenant le module extrait au lieu
de rechercher l'algorithme dans la façade.

Aucun nouveau fichier livrable n'est créé : `_terrain_download.py` est déjà dans
`deploy.MAP` et couvert par les motifs rebuild/CI. La version reste **1.45.0** ;
ce lot est postérieur à la release et n'est pas encore déployé.

Mesure nette : `lidar2map.py` 11 144 → 11 009 lignes (**-135**, soit **0,63 %**
du périmètre figé). Total sorti : **10 306 lignes, 48,35 %** ; reste **11 009
lignes, 51,65 %**. `_terrain_download.py` contient désormais 526 lignes
physiques.

### Sous-phase 15i : moteur COPC fenêtré extrait (terminée localement)

`telecharger_copc_fenetre`, son état de dépendances immuable et l'implémentation
du verrou multi-UTM résident désormais dans `_terrain_download.py`. La façade
historique conserve sa signature et reconstruit à chaque appel le provider, le
résolveur sécurisé, la transformation de bbox, le lecteur COPC, le staging, la
validation, la publication LAZ/TIFF et le manifeste. Le lecteur
`providers.common.copc_window_to_las` reste donc remplaçable à chaud dans les
tests et les intégrations.

Le téléchargement distant et l'écriture LAS restent parallèles. Seul le couple
`set_crs` puis `post_fetch` est protégé par le verrou partagé, afin qu'une tuile
d'un autre fuseau UTM ne modifie pas le CRS pendant la conversion. Le cache et
le seuil propre au provider, la signature éventuelle de l'URL, le seuil minimal
de 50 000 points, les statuts `ok`/`skip`/`absent`/`erreur`, la publication
atomique et la propagation de `KeyboardInterrupt` sont inchangés.

Trois nouveaux tests atomiques portent cette suite à **22 tests** : succès avec
URL signée et ordre validation/publication, fenêtre quasi vide sans conversion,
et interruption avec nettoyage. Un contrat de façade supplémentaire porte la
suite de refonte à **185 tests** et vérifie les dépendances tardives ainsi que
les signatures historiques. Le test scientifique concurrent multi-UTM et le
contrôle d'interaction du hook `sign_url` suivent désormais le module extrait.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

Aucun nouveau fichier livrable n'est créé : `_terrain_download.py` est déjà dans
`deploy.MAP` et couvert par les motifs rebuild/CI. La version reste **1.45.0** et
ce lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 11 009 → 10 991 lignes (**-18**, soit **0,08 %**
du périmètre figé). Total sorti : **10 324 lignes, 48,43 %** ; reste **10 991
lignes, 51,57 %**. `_terrain_download.py` contient désormais 624 lignes
physiques. Le faible gain net est assumé : cette petite frontière conserve deux
façades et une injection explicite de onze dépendances.

### Sous-phase 15j : moteur COG fenêtré extrait (terminée localement)

`telecharger_cog_fenetre`, le contrôle de couverture du fragment en cache et une
dataclass immuable de douze dépendances résident désormais dans
`_terrain_download.py`. Les imports rasterio restent locaux au moteur afin que le
module terrain demeure importable sans cette dépendance. La façade historique
conserve sa signature et relit à chaque appel provider, chemins, seuil, retries,
taille maximale, staging, transformeur, cache, validateur, manifeste et horloge.

Les options GDAL par défaut restent confinées dans `rasterio.Env` et les options
du provider les surchargent comme avant. La bbox est reprojetée vers le CRS réel
du COG lorsque nécessaire, intersectée avec ses bornes puis copiée en une passe
ou par bandes de 1 024 lignes au-delà du plafond. L'ancien fragment n'est
remplacé qu'après les validations précédant et suivant `post_download`.
`KeyboardInterrupt` est propagée ; les erreurs transitoires conservent leurs
retries et les statuts `ok`/`skip`/`absent`/`erreur` restent inchangés.

Six contrats COG supplémentaires portent la suite atomique à **28 tests**. Ils
couvrent le succès et l'ordre validation/hook/publication, les options provider,
l'absence d'intersection, le retry, l'interruption, la copie bornée d'une fenêtre
de 2 050 lignes et la reprojection du contrôle de cache. Un contrat de façade
porte la suite de refonte à **186 tests** et verrouille les dépendances tardives
ainsi que les signatures historiques. Le scénario d'interaction avec un vrai
GeoTIFF confirme toujours la couverture, le débordement et le fragment illisible.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

Aucun nouveau fichier livrable n'est créé : `_terrain_download.py` est déjà dans
`deploy.MAP` et couvert par les motifs rebuild/CI. La version reste **1.45.0** et
ce lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 991 → 10 875 lignes (**-116**, soit **0,54 %**
du périmètre figé). Total sorti : **10 440 lignes, 48,98 %** ; reste **10 875
lignes, 51,02 %**. `_terrain_download.py` contient désormais 862 lignes
physiques.

### Sous-phase 15k : chemins et validation des dalles extraits (terminée localement)

Les politiques `_nom_dalle_sur`, `chemin_dalle`, `_dossier_dalles_actif` et
`_valider_tif_dalle` résident désormais dans `_terrain_download.py`. Les quatre
façades historiques gardent leurs signatures et relisent le provider, les
racines cache/production, le sous-dossier LiDAR et le contrôle de basename à
chaque appel.

Un nom issu d'un index distant reste limité à un composant sans séparateur,
lettre de lecteur, chemin absolu, NUL, `.` ou `..`. L'ancienne dalle placée à la
racine conserve sa priorité ; sinon le sous-dossier du provider est utilisé. La
racine explicitement demandée reste prioritaire, puis viennent le projet pour
les providers fenêtrés, la production pour les jumeaux LAZ et enfin le cache
pour les MNT téléchargés.

Le validateur accepte les TIFF classiques et BigTIFF dans les deux endiannesses.
Sans rasterio, le magic reste le repli historique ; avec rasterio, dimensions,
nombre de bandes, résolution finie et lecture d'un bloc 64×64 sont exigés. Un
header correct avec métadonnées ou données tronquées reste donc rejeté sans
exception visible.

Cinq contrats supplémentaires portent la suite de refonte à **191 tests**. Ils
verrouillent la traversée de chemin, le cache racine historique, le sous-dossier
provider, les quatre routes de stockage, les quatre magics TIFF/BigTIFF, les
métadonnées invalides, la lecture en erreur et les dépendances tardives des
façades. La suite atomique reste à **28 tests**.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

Aucun nouveau fichier livrable n'est créé : `_terrain_download.py` est déjà dans
`deploy.MAP` et couvert par les motifs rebuild/CI. La version reste **1.45.0** et
ce lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 875 → 10 779 lignes (**-96**, soit **0,45 %**
du périmètre figé). Total sorti : **10 536 lignes, 49,43 %** ; reste **10 779
lignes, 50,57 %**. `_terrain_download.py` contient désormais 953 lignes
physiques.

### Sous-phase 15l : cache, profilage LAZ et préchargement extraits (terminée localement)

Les politiques `_configurer_cloud_cache` et `_rglob_tif_robuste`, ainsi que
l'accumulation et le résumé du profilage LAZ, résident maintenant dans
`_terrain_download.py`. Elles reçoivent explicitement provider, racines,
verrou, état et sortie texte ; les façades historiques relisent toujours les
globals actifs à chaque appel.

Le préchargement concurrent est volontairement isolé dans le nouveau module
`_terrain_prefetch.py` (84 lignes). `PrefetchDalles` conserve une profondeur
strictement égale à un, refuse l'anticipation quand la marge disque ne peut pas
tenir deux morceaux, attend uniquement la clé correspondante et transforme une
erreur du thread en repli synchrone. Il ne touche jamais au manifeste. La classe
historique `_PrefetchDalles()` reste une façade sans argument et injecte au
moment de son instanciation la sonde disque, le téléchargement, la fabrique de
threads et l'affichage du monolithe.

Six contrats supplémentaires portent la suite de refonte à **197 tests**. Ils
verrouillent le parcours TIFF racine + un niveau, les erreurs d'accès disque,
les routes du cache LAZ partagé/fenêtré/explicite, les cumuls et la borne du
profilage, la profondeur un, la correspondance des clés, la marge disque, le
repli sur erreur et les signatures des façades. Les 68 tests de reprise du
découpage et les 28 tests de téléchargement atomique restent verts.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison est préparée sans publication : `_terrain_prefetch.py` est ajouté
à `deploy.MAP` ; le motif `_terrain_*.py` imposait déjà le rebuild et couvrait
les deux filtres CI. Les imports sont statiques et ne demandent aucun hidden
import PyInstaller. La version reste **1.45.0** et ce lot n'est pas encore
déployé.

Mesure nette : `lidar2map.py` 10 779 → 10 701 lignes (**-78**, soit **0,37 %**
du périmètre figé). Total sorti : **10 614 lignes, 49,79 %** ; reste **10 701
lignes, 50,21 %**. `_terrain_download.py` contient désormais 1 037 lignes
physiques et `_terrain_prefetch.py` 84.

### Sous-phase 15m : découverte et téléchargement par morceau extraits (terminée localement)

Le nouveau module `_terrain_chunks.py` (106 lignes) porte la transformation de
la bbox native vers une enveloppe WGS84 élargie, le chemin du cache de
découverte, le lookahead best-effort, la préparation des dossiers du morceau et
le téléchargement sous la sous-clé manifeste `<chunk>_dl`.

Une dataclass immuable reçoit provider, transformeurs, racines, sélection du
dossier de dalles, contexte manifeste et moteur de téléchargement. Les façades
`_dalles_zone_lookahead(bbox_natif)` et
`_decouvrir_et_telecharger_ombrage(..., quiet=False)` conservent exactement leurs
signatures et reconstruisent ces coutures à chaque appel. Une erreur de
découverte du morceau principal reste fatale et rejouable ; le lookahead absorbe
la même erreur et laisse le chemin synchrone reprendre normalement.

Six contrats supplémentaires portent la suite de refonte à **203 tests**. Ils
verrouillent la marge WGS84, le cache par provider, le résultat vide, le repli
du lookahead, les racines implicite et explicite, la création des dossiers,
l'ordre du contexte manifeste, le flag `quiet`, le mode sans téléchargement et
les deux formes d'échec de découverte. Les 68 tests de reprise du découpage,
interactions, compilation, Ruff et garde de livraison restent verts.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison est préparée sans publication : `_terrain_chunks.py` est ajouté à
`deploy.MAP` et le motif `_terrain_*.py` couvre déjà rebuild et les deux filtres
CI. L'import est statique et n'ajoute aucun hidden import PyInstaller. La version
reste **1.45.0**.

Mesure nette : `lidar2map.py` 10 701 → 10 696 lignes (**-5**, soit **0,02 %** du
périmètre figé). Le faible gain est assumé : les 106 lignes du module sont
presque compensées par la dataclass de neuf dépendances et les deux façades de
compatibilité. Total sorti : **10 619 lignes, 49,82 %** ; reste **10 696 lignes,
50,18 %**.

### Sous-phase 15n : orchestration d'ombrage par morceau extraite (terminée localement)

`_terrain_chunks.py` porte maintenant la transaction
`traiter_bbox_lidar_ombrage`. Elle substitue temporairement la bbox et le nom du
morceau dans `args`, consomme un résultat préchargé ou déclenche la découverte,
signale immédiatement la disponibilité des dalles, résout les instances
d'ombrage, ouvre le contexte manifeste et délègue le calcul scientifique à
`generer_ombrages` injecté.

Le nettoyage reste volontairement postérieur au succès du calcul. Il cible la
sous-clé `<chunk>_dl`, préserve les noms nécessaires au morceau suivant et, avec
`--cleanup-keep-tiles`, conserve à la fois la racine des TIFF et le cache séparé
des nuages LAZ. Une exception de découverte ou d'ombrage restaure toujours
`args.zone_bbox` et `args.zone_nom`, mais garde les téléchargements afin que la
reprise puisse les réutiliser.

Cinq contrats supplémentaires portent la suite de refonte à **208 tests**. Ils
verrouillent la consommation du préchargement, le callback, toutes les options
transmises au générateur, l'élévation par défaut, le contexte manifeste, le
nettoyage sélectif, la conservation après échec, la restauration transactionnelle
et la signature historique. Les noyaux raster et `generer_ombrages` n'ont pas
été déplacés.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison ne crée aucun fichier supplémentaire : `_terrain_chunks.py` est
déjà dans `deploy.MAP` et couvert par `_terrain_*.py` pour le rebuild et les deux
filtres CI. La version reste **1.45.0** et ce lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 696 → 10 668 lignes (**-28**, soit **0,13 %**
du périmètre figé). `_terrain_chunks.py` contient désormais 192 lignes. Total
sorti : **10 647 lignes, 49,95 %** ; reste **10 668 lignes, 50,05 %**.

### Sous-phase 15o : orchestration du tuilage glissant extraite (terminée localement)

`_terrain_chunks.py` contient désormais `traiter_bbox_lidar_tuilage` et une
dataclass séparée de treize dépendances. La transaction calcule le tampon maximal
depuis le plus petit côté du morceau, résout les dossiers voisins via le
planificateur 3×3 déjà extrait, associe les TIFF portant le même suffixe et ne
construit un VRT que lorsqu'au moins un voisin réel est disponible.

Chaque famille d'ombrage conserve son nom historique, sa source de fraîcheur et
son chemin MBTiles attendu. Un MBTiles frais est réutilisé sans rappeler le
générateur ; sinon le moteur MBTiles reçoit la bbox exacte, le tampon, le format,
la qualité et le nombre de workers. Toutes les conversions sont exécutées même
si la première échoue, et leur statut est agrégé dans `_ResultatChunk` avec la
liste complète des livrables attendus. Les arguments temporaires de zone sont
restaurés sur succès, retour anticipé et exception.

Six contrats supplémentaires portent la suite de refonte à **214 tests**. Ils
verrouillent l'absence de formats, le bord sans voisin, la construction et
l'enregistrement du VRT, la résolution raster, le tampon, les chemins attendus,
la réutilisation du cache, plusieurs familles, l'agrégation all-of et la
restauration après échec. Les moteurs MBTiles, rasterio et conversion restent
injectés ou importés localement ; aucun noyau scientifique n'est déplacé.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison ne crée aucun nouveau fichier : `_terrain_chunks.py` est déjà dans
`deploy.MAP` et couvert par `_terrain_*.py` pour rebuild et CI. La version reste
**1.45.0** et le lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 668 → 10 639 lignes (**-29**, soit **0,14 %**
du périmètre figé). `_terrain_chunks.py` contient désormais 323 lignes. Total
sorti : **10 676 lignes, 50,08 %** ; le script principal passe sous la moitié du
périmètre initial avec **10 639 lignes, 49,92 %**.

### Sous-phase 15p : transaction raster WMTS par morceau extraite (terminée localement)

`_terrain_chunks.py` contient désormais `traiter_bbox_wmts` et une dataclass
dédiée de onze dépendances. La transaction normalise les zooms inversés, calcule
la grille et son cardinal, résout la racine explicite ou celle du projet, puis
construit le nom MBTiles avec la qualité JPEG par les mêmes helpers que la passe
WMTS simple. Le cache reste isolé sous `ign_raster` et toutes les options du
téléchargeur historique sont transmises sans modification.

Un MBTiles frais est réutilisé sans rappeler le générateur. Une génération qui
ne publie pas le fichier attendu produit un `_ResultatChunk` incomplet sans
tenter de conversion ; sinon le statut réel de la conversion est propagé. Le
nom de zone temporaire est restauré sur succès comme sur exception. La façade
`_traiter_bbox_wmts` et sa signature historique restent dans `lidar2map.py`, avec
reconstruction tardive des coutures pour préserver les monkeypatches.

Cinq contrats supplémentaires portent la suite de refonte à **219 tests**. Ils
verrouillent les zooms inversés, la bbox et toutes les options de génération, le
nom versionné par qualité, la racine explicite, la réutilisation du MBTiles, le
fichier attendu absent, l'échec de conversion, la restauration après exception
et la signature de façade.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison ne crée aucun nouveau fichier : `_terrain_chunks.py` est déjà dans
`deploy.MAP` et couvert par `_terrain_*.py` pour rebuild et CI. La version reste
**1.45.0** et le lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 639 → 10 614 lignes (**-25**, soit **0,12 %**
du périmètre figé). `_terrain_chunks.py` contient désormais 429 lignes. Total
sorti : **10 701 lignes, 50,20 %** ; reste **10 614 lignes, 49,80 %**.

### Sous-phase 15q : transaction LiDAR autonome `--block` extraite (terminée localement)

`_terrain_chunks.py` contient désormais `traiter_bbox_lidar` et une dataclass
dédiée de seize dépendances. Cette voie est réservée au découpage distribué
`--block`, où les machines ne partagent pas les ombrages voisins. Elle conserve
le halo historique, égal à 10 % du plus petit côté avec un plancher de 300 m,
pour la découverte, le téléchargement et le calcul d'ombrage ; le tuilage reçoit
toujours la bbox nominale et ce halo comme borne du tampon de coin.

La racine explicite et la racine de projet gardent leurs chemins historiques.
La découverte distingue toujours l'absence légitime de couverture `{}` de
l'indisponibilité réseau `None` ou d'une exception, ces deux derniers cas restant
rejouables. La voie « tuiles seules » transmet `tifs_run=None` au sélecteur et
évite le `NameError` déjà corrigé. Toutes les options scientifiques et le statut
réel du tuilage sont propagés, tandis que `zone_bbox` et `zone_nom` sont restaurés
sur succès ou échec. Aucun nettoyage n'a été ajouté : il reste sous la
responsabilité du runner classique, comme avant l'extraction.

Cinq contrats supplémentaires portent la suite de refonte à **224 tests**. Ils
verrouillent les deux régimes de halo, les emprises découverte/ombrage/tuilage,
les chemins et le cache provider, le téléchargement optionnel, toutes les
options d'ombrage, la voie tuiles seules, l'absence de format, les échecs de
découverte, la restauration transactionnelle et la signature de façade.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison ne crée aucun nouveau fichier : `_terrain_chunks.py` est déjà dans
`deploy.MAP` et couvert par `_terrain_*.py` pour rebuild et CI. La version reste
**1.45.0** et le lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 614 → 10 539 lignes (**-75**, soit **0,35 %**
du périmètre figé). `_terrain_chunks.py` contient désormais 578 lignes. Total
sorti : **10 776 lignes, 50,56 %** ; reste **10 539 lignes, 49,44 %**.

### Sous-phase 15r : tuilage commun des ombrages extrait (terminée localement)

`_terrain_chunks.py` contient désormais `tuiler_tifs_ombrages` et une dataclass
de cinq coutures. Le helper reste partagé par le traitement monolithique et la
transaction autonome `--block`. Il normalise le suffixe `_tuilage_zN`, construit
un MBTiles attendu par famille, vérifie sa fraîcheur par rapport au TIFF source,
appelle le producteur uniquement si nécessaire puis exécute chaque conversion.

L'agrégation conserve son ordre historique, avec la conversion courante évaluée
avant le statut accumulé : un premier échec ne court-circuite donc jamais les
familles suivantes. Le mode verbeux, la découpe de sortie, le tampon de coin, le
format, la qualité et le nombre de workers sont transmis sans modification. La
façade `_tuiler_tifs_ombrages` conserve sa signature complète et reconstruit les
coutures à chaque appel.

Quatre contrats supplémentaires portent la suite de refonte à **228 tests**. Ils
verrouillent l'entrée vide, deux conventions de nommage, plusieurs TIFF, la
liste ordonnée des livrables attendus, toutes les options du producteur, le mode
verbeux, l'agrégation all-of, la réutilisation du cache et la signature de façade.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison ne crée aucun nouveau fichier : `_terrain_chunks.py` est déjà dans
`deploy.MAP` et couvert par `_terrain_*.py` pour rebuild et CI. La version reste
**1.45.0** et le lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 539 → 10 537 lignes (**-2**, soit **0,01 %** du
périmètre figé). `_terrain_chunks.py` contient désormais 654 lignes. Le faible
gain est assumé : les 40 lignes historiques sont remplacées par une façade et
une fabrique de dépendances explicites ; cette couture améliore l'isolation mais
n'est pas un lot de réduction. Total sorti : **10 778 lignes, 50,56 %** ; reste
**10 537 lignes, 49,44 %**.

### Sous-phase 15s-a : planification des instances d'ombrage extraite (terminée localement)

L'audit de `generer_ombrages` mesure **726 lignes** et **23 coutures métier** en
plus des builtins. Il confirme que le bloc assemble plusieurs responsabilités :
résolution des instances, VRT transactionnel, publication atomique, passe Horn
multi-sorties, SVF/openness, LRM, RRIM et composites VAT/e4MSTP. Une extraction
monolithique immédiate aurait rendu les régressions difficiles à localiser ; la
phase 15s est donc scindée en un palier pur puis le déplacement de l'orchestrateur.

Le nouveau module `_terrain_shading.py` contient
`resoudre_instances_ombrages`. Cette fonction pure applique les paramètres par
défaut, construit les suffixes historiques et paramétrés, conserve l'ordre
`choix` puis `instances`, ignore les types inconnus et résout les collisions par
la règle « première instance gagnante ». Un vrai doublon reste silencieux ; deux
réglages distincts arrondis vers le même suffixe produisent toujours un warning.
Les dictionnaires reçus sont copiés et ne sont jamais modifiés.

Quatre contrats supplémentaires portent la suite de refonte à **232 tests**. Ils
verrouillent les suffixes canoniques de dix familles, les valeurs par défaut,
les suffixes explicites direction/LRM/VAT/e4MSTP/SVF, l'ordre, l'absence de
mutation, les types inconnus, les deux formes de collision et le câblage tardif
depuis `generer_ombrages`. Les tests scientifiques existants continuent de
couvrir les kernels et composites réels.

Validation locale : profils FAST (12 suites) et scientifique (5 suites),
compilation, Ruff, garde de livraison et 320 liens documentaires verts.

La livraison est préparée sans publication : `_terrain_shading.py` est ajouté à
`deploy.MAP`; le motif `_terrain_*.py` couvrait déjà rebuild et les deux filtres
CI. La version reste **1.45.0** et le lot n'est pas encore déployé.

Mesure nette : `lidar2map.py` 10 537 → 10 481 lignes (**-56**, soit **0,26 %**
du périmètre figé). `_terrain_shading.py` contient 95 lignes. Total sorti :
**10 834 lignes, 50,83 %** ; reste **10 481 lignes, 49,17 %**.

### Sous-phase 15s-b : orchestrateur d'ombrage extrait (terminée et déployée)

Le corps restant de `generer_ombrages` est déplacé mécaniquement dans
`_terrain_shading.py`. `lidar2map.py` ne conserve qu'une façade de signature
strictement identique et reconstruit à chaque appel une dataclass de **30
coutures** : configuration active, provider, VRT et publications atomiques,
kernels, composites, annulation, temps et journalisation. Les fonctions
scientifiques restent dans `_ombrages_pures.py` et `_ombrages_provider.py` ;
elles sont injectées sans duplication ni modification algorithmique.

Cinq contrats supplémentaires portent la suite de refonte à **237 tests**. Ils
verrouillent le transfert intégral des arguments par la façade, la création et
le nettoyage du répertoire VRT transactionnel, l'échec explicite de construction
du VRT, la publication d'un TIFF Horn uniquement après succès et, en cas
d'échec, la suppression du `.part` avec conservation byte-identique de l'ancien
fichier final.

Validation locale : compilation des modules, profil FAST complet (**12/12**) et
profil scientifique complet (**5/5**). La suite scientifique produit réellement
les ombrages paramétrés, les composites et les sorties raster ; elle confirme
donc que l'extraction n'a pas modifié les kernels ni leur orchestration. Ruff
n'est pas installé dans le venv local et n'a pas été compté comme validation.

Mesure nette : `lidar2map.py` 10 481 → 9 871 lignes (**-610**, soit **2,86 %**
du périmètre figé). `_terrain_shading.py` contient désormais 831 lignes. Total
sorti : **11 444 lignes, 53,69 %** ; reste **9 871 lignes, 46,31 %**.

Déploiement : bump `VERSION` 1.45.0 → **1.46.0**, commit `e2621bc`, tag
`v1.46.0` poussé par `deploy.py --new-tag`, puis rebuild des quatre cibles du
workflow `release.yml` (Windows, Linux, macOS Intel et Apple Silicon).

### Sous-phase 15t — planches et contours de restitution (terminée et déployée)

Les corps de `_planche_depuis_dossier`, `_planche_contours_dept` et
`_generer_planche` sont déplacés dans `_terrain_index.py`. Le script principal
conserve les trois signatures historiques et reconstruit à chaque appel une
dataclass de coutures : extraction d'emprise, résolution des contours, rendu,
cache, client HTTP, temporisation Nominatim et écriture JSON atomique. Les
monkeypatchs historiques appliqués à `lidar2map.py` restent donc observés par le
module extrait.

Cinq contrats supplémentaires portent la suite de refonte à **242 tests**. Ils
verrouillent les signatures et dépendances tardives, le recadrage des emprises
WFS à la zone demandée, l'ordre des cellules et le nom du produit, le cas sans
livrable lisible, la réutilisation du cache de contours sans appel HTTP et le
nom du PNG réellement produit. Compilation et suite complète des contrats de
refonte sont vertes. La grammaire Python 3.8 est validée, le profil FAST passe
**12/12** en 43,3 s et le profil scientifique **5/5** en 99,1 s, y compris le
scénario historique de recadrage WFS. Le lot est ajouté à `deploy.MAP`; les
filtres CI et rebuild `_terrain_*.py` le couvrent déjà.

Mesure nette : `lidar2map.py` 9 871 → 9 579 lignes (**-292**, soit **1,37 %**
du périmètre figé). `_terrain_index.py` contient 373 lignes. Total sorti :
**11 736 lignes, 55,06 %** ; reste **9 579 lignes, 44,94 %**.

### Sous-phase 15u — lecteurs d'emprises de livrables (terminée et déployée)

Les corps de `_bbox_geojson_stream`, `_bbox_sqlite_tiles` et
`_extraire_bbox_wgs84` rejoignent `_terrain_index.py`. Les façades du script
principal conservent leurs signatures et résolvent tardivement `_tile_to_geo`,
les deux lecteurs spécialisés et la connexion SQLite. Le parcours GeoJSON
reste streamé avec `ijson`; aucune collection complète n'est chargée en RAM.

Cinq contrats supplémentaires portent la suite de refonte à **247 tests**. Ils
verrouillent les coutures tardives, les coordonnées GeoJSON imbriquées, la
priorité de `metadata.bounds` en MBTiles, le schéma SQLiteDB BigPlanet historique
avec zoom stocké inversé, le dispatch GeoJSON GZip et le repli fermé sur un
fichier illisible. La suite de robustesse multi-zoom existante reste verte et la
grammaire Python 3.8 est validée. Le profil FAST passe **12/12** en 36,0 s et
le profil scientifique **5/5** en 91,1 s, y compris les scénarios SQLite
multi-zoom et le recadrage WFS.

Mesure nette : `lidar2map.py` 9 579 → 9 501 lignes (**-78**, soit **0,37 %**
du périmètre figé). `_terrain_index.py` contient désormais 488 lignes. Total
sorti : **11 814 lignes, 55,43 %** ; reste **9 501 lignes, 44,57 %**.

### Sous-phase 15v — découpage MBTiles postérieur (terminée et déployée)

Le corps de `decouper_mbtiles` rejoint `_split_mbtiles.py`. La façade publique
du script principal conserve exactement sa signature historique et reconstruit
à chaque appel les cinq coutures mutables : calcul de grille, chemin de staging,
nettoyage SQLite, validation SQLite et connexion SQLite. Les monkeypatchs
historiques appliqués à `lidar2map.py` restent donc observables par le module
extrait.

Quatre contrats supplémentaires portent la suite de refonte à **251 tests**.
Ils verrouillent la signature et la résolution tardive des dépendances, le no-op
historique sans demande de découpage, une vraie grille SQLite 2×2 avec noms en
ordre ligne-par-ligne, conservation des métadonnées et comptage des tuiles, ainsi
que la conservation d'un ancien morceau si la validation du nouveau staging
échoue. La grammaire Python 3.8 est validée. Le profil FAST passe **12/12** en
54,1 s et le profil scientifique **5/5** en 115,1 s, dont les régressions R2#12
(zooms et bbox) et R2#14 (formats de sortie). Le module est ajouté à
`deploy.MAP`; les filtres CI et rebuild `_split_*.py` le couvrent déjà.

Mesure nette : `lidar2map.py` 9 501 → 9 313 lignes (**-188**, soit **0,88 %**
du périmètre figé). `_split_mbtiles.py` contient 236 lignes. Total sorti :
**12 002 lignes, 56,31 %** ; reste **9 313 lignes, 43,69 %**.

### Sous-phase 15w — fraîcheur et nettoyage des livrables (terminée et déployée)

Les corps de `_mbtiles_a_regenerer`, `_morceau_termine_reutilisable` et
`_supprimer_fichiers` rejoignent `_deliverable_lifecycle.py`. Trois dataclasses
de coutures distinctes évitent de coupler le nettoyage de fichiers à SQLite ou
au validateur de morceaux. Les façades du script principal conservent leurs
signatures et reconstruisent à chaque appel les chemins, la connexion et les
exceptions SQLite, le validateur de livrables et la sortie de log.

Quatre contrats supplémentaires portent la suite de refonte à **255 tests**.
Ils verrouillent les signatures et coutures tardives, la protection simultanée
des caches de dalles et de nuages avec le nom réclamé par le morceau suivant, le
rejet des manifestes historiques sans preuve de sortie, la preuve explicite
d'une zone hors couverture, ainsi que les quatre décisions de fraîcheur MBTiles
(date source, magasin valide, vide ou illisible). Le premier passage FAST a
signalé l'absence du nouveau module dans le garde de rebuild ; `deploy.py` et
les deux filtres CI, push et pull request, couvrent maintenant
`_deliverable_*.py`.

La grammaire Python 3.8 et Ruff sont verts. Le profil FAST passe **12/12** en
53,1 s et le profil scientifique **5/5** en 123,2 s, y compris R2#22, la reprise
des manifestes et les nettoyages MNT/LAZ avec ou sans conservation des caches.
Le module est ajouté à `deploy.MAP`.

Mesure nette : `lidar2map.py` 9 313 → 9 213 lignes (**-100**, soit **0,47 %**
du périmètre figé). `_deliverable_lifecycle.py` contient 174 lignes. Total
sorti : **12 102 lignes, 56,78 %** ; reste **9 213 lignes, 43,22 %**.

### Sous-phase 15x — catalogue et chargement des providers (terminée et déployée)

Les corps de `_discover_providers`, `_load_provider` et du lecteur pur
`_pre_valeur_suivante` rejoignent `_provider_runtime.py`. Le module extrait
reçoit explicitement le dossier `providers`, l'environnement, le vecteur
d'arguments, l'importeur patchable, la sortie d'erreur et la fonction d'arrêt.
Le script principal conserve les trois signatures historiques, reconstruit les
coutures à chaque appel, met à jour `_PROVIDER_CLI_EXPLICIT` et reste seul
responsable de l'affectation finale de `PROVIDER`.

Cinq contrats supplémentaires portent la suite de refonte à **260 tests**. Ils
verrouillent les façades tardives, l'ordre du catalogue, l'exclusion des helpers
et jumeaux LAZ, la tolérance à un module cassé, les métadonnées pays et capacités
LAZ, la consommation en place des pré-flags, leurs types historiques, les
diagnostics distincts pour code inconnu et dépendance manquante, ainsi que le
fallback France lorsque le paquet `providers` est entièrement absent.

La grammaire Python 3.8 et Ruff sont vertes. Le profil FAST passe **12/12** en
54,7 s et le profil scientifique **5/5** en 148,9 s, dont les 27 pays du
catalogue, les jumeaux LAZ, R2#39 et les contrats CLI réels. Le module est ajouté
à `deploy.MAP`; `deploy.py` et les filtres CI push/pull request couvrent
`_provider_*.py`.

Mesure nette : `lidar2map.py` 9 213 → 9 014 lignes (**-199**, soit **0,93 %**
du périmètre figé). `_provider_runtime.py` contient 315 lignes. Total sorti :
**12 301 lignes, 57,71 %** ; reste **9 014 lignes, 42,29 %**.

### Sous-phase 15y — contrat de zone CLI partagé (terminée et déployée)

Les corps de `_ajouter_args_zone` et `_resoudre_zone_wgs84` rejoignent
`_zone_cli.py`. Deux dataclasses distinctes empêchent la construction argparse
de dépendre des géocodeurs : la première ne reçoit que le validateur de largeur,
la seconde reçoit explicitement les conventions de nommage, les géocodeurs, la
conversion de bbox, la validation WGS84, la sortie et l'arrêt. Le module extrait
ne connaît ni provider ni CRS natif. `lidar2map.py` conserve les deux signatures
historiques et reconstruit toutes les coutures à chaque appel.

Six contrats supplémentaires portent la suite de refonte à **266 tests**. Ils
verrouillent les alias et valeurs par défaut argparse, l'exclusion mutuelle des
modes, la priorité région, les noms explicites et automatiques, les conversions
des régions et départements, les bbox WGS84, la sémantique de largeur des modes
GPS et ville, les sorties d'erreur ainsi que les dépendances relues tardivement.
Le test d'interaction `--cache-dir` et la garde d'absence de `CRS_NATIF` lisent
maintenant le module propriétaire du contrat au lieu d'une fenêtre textuelle
fragile dans le monolithe.

Compilation et Ruff sont verts. Le profil FAST passe **12/12** en 69,2 s et le
profil scientifique **5/5** en 126,9 s, y compris les interactions CLI réelles,
les 27 providers et les scénarios de tuilage. `_zone_cli.py` est ajouté à
`deploy.MAP`; `deploy.py` le classe comme changement exigeant un rebuild et les
filtres CI push/pull request couvrent `_zone_*.py`. Le dry-run de `deploy.py`
reconnaît bien `_zone_cli.py` et le lot cumulatif attendu.

Mesure nette : `lidar2map.py` 9 014 → 8 888 lignes (**-126**, soit **0,59 %**
du périmètre figé). `_zone_cli.py` contient 241 lignes. Total sorti :
**12 427 lignes, 58,30 %** ; reste **8 888 lignes, 41,70 %**.

Déploiement du lot 15t–15y : bump `VERSION` 1.46.0 → **1.47.0**, commit
`22c27c7`, tag `v1.47.0` poussé par `deploy.py --new-tag`, puis rebuild réussi
des quatre cibles (Windows, Linux, macOS Intel et Apple Silicon). La release
publique contient les quatre artefacts attendus.

### Prochaine étape proposée : 16a — construction du parser LiDAR

Caractériser puis extraire `_construire_parser_lidar` et, si les contrats
confirment leur cohésion, `_appliquer_defauts_cli_lidar`, soit environ 300 lignes
brutes. Le corps de `main()` restera hors périmètre : cette première sous-phase
de la phase 16 ne déplacera que la déclaration argparse et les défauts de CLI.
Les contrats devront comparer les alias, valeurs par défaut, groupes exclusifs,
erreurs de validation et l'aide produite avant/après extraction.
