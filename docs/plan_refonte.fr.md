# Plan de refonte de `lidar2map.py`

Dernière mise à jour : 10 août 2026 (phase 8 en cours, sous-phase 8a).

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
├── _split_manifest.py      état persistant et suivi des intermédiaires
├── _split_deliverables.py  résultats et validation des livrables
├── _split_planning.py      grille, sharding, identifiants et signature
├── _split_runner.py        runner classique et dépendances injectées
├── _split_sliding.py       runner LiDAR glissant et voisinage 3×3
├── _raster_formats.py      conversions RMAP/SQLiteDB et orchestration
├── _mbtiles_wmts.py        producteur MBTiles WMTS/XYZ (téléchargement, cache)
├── _mbtiles_lidar.py       producteur MBTiles LiDAR (warp, overviews, tuilage)
└── _mbtiles_wmts_helpers.py  grille XYZ, URL, connexions, fetch HTTP
```

Tous ces modules sont privés (préfixe `_`). Leur interface stable est la façade
conservée dans `lidar2map.py`. Le préfixe `_split_` est réservé aux composants du
traitement découpé ; les producteurs et convertisseurs raster portent un nom de
domaine (`_raster_formats`, `_mbtiles_wmts`, `_mbtiles_lidar`,
`_mbtiles_wmts_helpers`).

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
| **Total sorti du monolithe (mesuré)** | **3 024** | **14,19 %** |
| **Reste dans `lidar2map.py` (mesuré)** | **18 291** | **85,81 %** |

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

## Avancement

| Phase | État | Contenu | Validation principale |
|---|---|---|---|
| 0. Caractérisation | Terminée | Runner hors réseau explicite et contrats de façade | 12 suites hors réseau |
| 1. Fiabilisation du split | Terminée | Historique succès/échec, conversion multi-format, reprise et nettoyage 3×3 | `_test_split_history.py`, `_test_interactions.py` |
| 2. Manifeste | Terminée | `Manifeste`, contexte thread-local et enregistrement des fichiers dans `_split_manifest.py` | concurrence, imbrication et reprise |
| 3. Livrables | Terminée | `_ResultatChunk`, normalisation et validation MBTiles/RMAP/SQLiteDB dans `_split_deliverables.py` | stems attendus, fichiers périmés et MBTiles corrompus |
| 4. Planification | Terminée | `--block`, grille, clés `001x001` et signature de configuration dans `_split_planning.py` | contrats de planification et interactions |
| 5. Runner classique | Terminée | `_run_split_priori` extrait dans `_split_runner.py` avec ses dépendances explicites | reprise, overwrite, hors couverture, échec partiel |
| 6. Runner glissant | Terminée | Ordonnancement ombrage/tuilage, voisinage 3×3 et purge différée extraits dans `_split_sliding.py` | reprise après perte d’un livrable, préchargement et coutures |
| 7. Pipelines raster | **Terminée** | Conversions RMAP/SQLiteDB, producteur MBTiles WMTS, producteur MBTiles LiDAR et helpers WMTS extraits | tuilage, publications atomiques et formats multiples |
| 8. Points d’entrée | En cours | Parser argparse extrait en fonctions dédiées pour `main()` et `main_wmts()` ; reste : finalisation des args et corps de dispatch | tests d’historique monolithique et CLI |

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

Les nouveaux modules `_split_*.py`, `_raster_formats.py` et `_mbtiles_*.py`
(WMTS et LiDAR) sont copiés vers le dépôt par `deploy.py` et surveillés par la
CI (filtre `paths:` en glob `_mbtiles_*.py`, pour ne pas devoir rééditer
`ci_github.yml` à chaque nouveau producteur `_mbtiles_*`). Ils sont
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

### Reste à faire en phase 8

- **Finalisation des args** : après `parser.parse_args()`, `main()` enchaîne
  ~350 lignes de validation/dérivation (`_valider_contrat_cli_lidar`,
  résolution `--shading`/`--shading-preset`, flags `--file-formats`, etc.) avant
  d'atteindre le corps d'orchestration. Prochaine sous-phase candidate : isoler
  ce bloc dans une fonction `_finaliser_args_lidar(args, parser)`, plus risqué
  que 8a car il a des effets de bord (`parser.error`, mutation d'`args`, prints).
- **Corps de dispatch** : ce qui doit *rester* dans `main()`/`main_wmts()` une
  fois 8a/8b faits — l'enchaînement `_run_split_priori(...)`,
  `generer_mbtiles_lidar(...)`, `generer_geojson_osm(...)`, etc. C'est la
  vraie « orchestration » visée par le nom de la phase.
- **Dette des jumeaux WMTS** (identifiée en phase 7c) : `main_wmts()` et
  `_traiter_bbox_wmts()` construisent tous deux le nom du MBTiles et la
  qualité de sortie via `_nom_mbtiles_wmts` et `_jpeg_quality_sortie`. Ces deux
  jumeaux avaient déjà divergé une fois (R2#14, R2#18) ; leur source de vérité
  commune est en place mais leur appelant ne l'est pas. À traiter quand le
  corps de `main_wmts()` sera retouché.
- `main_decouper()`, `main_wfs()`, `main_fusionner()`, `main_serve()` n'ont pas
  été audités pour un parser aussi volumineux ; à vérifier avant de les
  considérer hors périmètre de la phase 8.
- Le plan mesure des lignes, pas du couplage. Un indicateur complémentaire utile
  pour les sous-phases suivantes : le nombre de symboles de `lidar2map.py`
  référencés depuis les modules extraits (zéro, par construction) et le nombre
  de coutures injectées par façade (12 pour le runner classique, 15 pour le
  producteur WMTS). Une façade qui dépasserait la vingtaine de coutures
  signalerait un découpage fait au mauvais endroit.
