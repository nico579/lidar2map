# Correctif proposé — parallélisation du warp et des overviews MBTiles

Date : 2026-07-28  
Statut : étape 1 implémentée (2026-09-24 : `_gdal_threads()` borné par
`tile_workers` et les CPU visibles, passé au warp, à la compression GTiff et
aux overviews via `GDAL_NUM_THREADS`, threads et version GDAL journalisés ;
overviews déjà construites sur le `.part` avant publication). Restent :
validation des facteurs d'overviews d'un cache réutilisé, verrou par cible,
benchmark sur VM. NB : `tile_workers` n'est plus dérivé de `--workers`
(cf. `_tile_workers_defaut`), la « Cause 3 » ci-dessous est donc caduque.  
Périmètre : étape `STEP: 3/3 MBTiles` de `lidar2map.py`

## Résumé

La phase de préparation du GeoTIFF Mercator utilise actuellement un seul cœur
pour deux opérations coûteuses :

1. la reprojection vers EPSG:3857 ;
2. la construction de la pyramide d'overviews avec le filtre gaussien.

Le comportement observé est donc normal au regard du code actuel :

```text
Warp EPSG:3857 ...
...
Overviews (gauss) [2, 4, 8, ...]...
```

Le correctif consiste à :

- calculer un nombre de threads GDAL explicite et borné ;
- passer cette valeur à `rasterio.warp.reproject()` ;
- définir localement `GDAL_NUM_THREADS` autour de l'ouverture du GeoTIFF et de
  `build_overviews()` ;
- ne jamais lancer plusieurs constructions d'overviews concurrentes sur le
  même fichier ;
- construire et valider le warp et ses overviews avant de publier le cache
  final.

Le nombre de threads doit être une valeur entière supérieure ou égale à 1.
Dans Rasterio, `num_threads=0` ne signifie pas « tous les processeurs ».

## Symptôme

Exemple réel :

```text
STEP:3/3 MBTiles
  gareoult_40_lrm_s2p5m_ombrage.tif
  Tile format: JPEG  Q=85
  Estimated size: ~4.5 Go -> single warp (rasterio streaming)
  Warp EPSG:3857  res=0.597 m/px  (rasterio, zoom 18)...
  gareoult_40_lrm_s2p5m_ombrage_tuilage_z18.tif [] 100%  4m49s  6937 Mo
  warped dims : 95361 × 95700 px
  Overviews (gauss) [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]...
```

Pendant `Overviews (gauss)`, l'utilisation CPU reste proche de 100 % d'un seul
cœur au lieu d'utiliser les vCPU disponibles sur la VM Hetzner.

La charge est pourtant très importante :

```text
95 361 × 95 700 = environ 9,13 milliards de pixels à pleine résolution
```

Pour une pyramide de facteurs 2, 4, 8, etc., le nombre total de pixels des
overviews tend vers un tiers du niveau principal :

```text
9,13 milliards / 3 = environ 3,04 milliards de pixels
```

Chaque pixel doit être filtré, écrit et compressé. La parallélisation de cette
phase est donc pertinente, même si le stockage peut ensuite devenir le facteur
limitant.

## Chemin de code actuel

La fonction concernée est :

```python
generer_mbtiles_lidar(...)
```

Elle se trouve vers la ligne 7591 de `lidar2map.py`.

Le pipeline est :

```text
TIF d'ombrage
  |
  +-- rasterio.warp.reproject
  |      -> GeoTIFF EPSG:3857, tiled, DEFLATE
  |
  +-- Dataset.build_overviews
  |      -> facteurs 2, 4, 8... avec Resampling.gauss
  |
  +-- lectures fenêtrées Rasterio
  +-- encodage JPEG/PNG avec Pillow
  +-- insertion SQLite
  +-- MBTiles final
```

Les points principaux se trouvent actuellement vers :

- lignes 7591-7608 : définition et documentation de
  `generer_mbtiles_lidar()` ;
- lignes 7691-7693 : calcul de `overview_levels` ;
- lignes 7744-7750 : pool Pillow piloté par `tile_workers` ;
- lignes 7894-7903 : appel à `rasterio.warp.reproject()` ;
- lignes 7931-7944 : appel à `build_overviews()` ;
- lignes 8007-8093 : lectures et encodage des tuiles.

## Cause 1 — `build_overviews()` ne reçoit aucune configuration de threads

Le code actuel est équivalent à :

```python
with _rio_o.open(str(warped), "r+") as ds_o:
    ds_o.build_overviews(overview_levels, _Res_o.gauss)
    ds_o.update_tags(ns="rio_overview", resampling="gauss")
```

L'API Rasterio :

```python
build_overviews(factors, resampling)
```

n'expose pas de paramètre Python `num_threads`.

Rasterio appelle en interne `GDALBuildOverviews()`. Sans option de
configuration, GDAL utilise un seul thread pour le calcul.

Depuis GDAL 3.2, la configuration suivante permet de paralléliser le calcul des
overviews :

```text
GDAL_NUM_THREADS=N
```

ou :

```text
GDAL_NUM_THREADS=ALL_CPUS
```

Pour une application, une valeur numérique bornée est préférable à
`ALL_CPUS`.

## Cause 2 — `num_threads=0` ne signifie pas « tous les CPU »

Le warp contient actuellement :

```python
_reproject(
    ...,
    num_threads=0,  # 0 = tous les CPUs
)
```

Ce commentaire est incorrect pour Rasterio.

L'implémentation Rasterio sélectionne son chemin multithread uniquement lorsque
la valeur est strictement supérieure à 1 :

```text
num_threads > 1 -> ChunkAndWarpMulti
sinon           -> ChunkAndWarpImage
```

Avec `num_threads=0`, le warp emprunte donc le chemin mono-thread.

Le warp de 4 min 49 observé dans l'exemple est probablement lui aussi limité à
un seul cœur.

## Cause 3 — `--workers` ne pilote pas actuellement GDAL

Le paramètre CLI :

```text
--workers N
```

est transmis à `generer_mbtiles_lidar()` sous le nom `tile_workers`.

Il pilote le `ThreadPoolExecutor` utilisé plus tard pour encoder les tuiles
JPEG/PNG avec Pillow :

```python
_pool = ThreadPoolExecutor(max_workers=tile_workers)
```

Il n'est transmis ni au warp Rasterio, ni à GDAL pour les overviews.

Augmenter `--workers` ne change donc pas l'utilisation CPU des deux phases
observées tant que le correctif n'est pas implémenté.

## Parallélisme supporté par GDAL

Il faut distinguer trois opérations :

### Calcul du warp

`rasterio.warp.reproject()` accepte un nombre entier de workers :

```python
num_threads=N
```

La valeur doit être supérieure à 1 pour activer le chemin multithread.

### Calcul des overviews

`GDALBuildOverviews()` utilise :

```text
GDAL_NUM_THREADS=N
```

depuis GDAL 3.2.

Le filtre `GAUSS` est supporté. Les facteurs actuels :

```text
2, 4, 8, 16, ...
```

sont adaptés au noyau gaussien recommandé par GDAL.

### Compression GeoTIFF

Le fichier warpé est écrit avec :

```text
TILED=YES
COMPRESS=DEFLATE
PREDICTOR=2
```

Le pilote GeoTIFF peut également paralléliser la compression DEFLATE. Sa valeur
par défaut est un thread. `GDAL_NUM_THREADS` peut servir d'alternative à
l'option `NUM_THREADS` du pilote.

Un contexte Rasterio local autour de l'ouverture du dataset permet donc
d'activer le calcul parallèle et la compression sans modifier globalement
l'environnement du processus.

## Nombre de threads recommandé

### Correctif minimal

Réutiliser `tile_workers`, déjà alimenté par `--workers` :

```python
gdal_threads = max(
    1,
    min(int(tile_workers), os.cpu_count() or 1),
)
```

Exemples :

| vCPU visibles | `--workers` | Threads GDAL |
|---:|---:|---:|
| 4 | 8 | 4 |
| 8 | 8 | 8 |
| 16 | 8 | 8 |
| 16 | 12 | 12 |
| 8 | 1 | 1 |

Cette règle :

- refuse implicitement les valeurs inférieures à 1 ;
- ne crée pas plus de threads que de CPU visibles ;
- conserve un contrôle utilisateur ;
- évite `ALL_CPUS` sur les grosses VM ou les machines partagées.

Si `--workers` est réutilisé, son aide CLI et son libellé GUI doivent préciser
qu'il gouverne aussi le warp, les overviews et l'encodage des tuiles. Sinon,
l'utilisateur pourrait croire qu'il ne règle que les connexions réseau.

### Évolution possible

Si le même `--workers` ne doit pas gouverner le réseau, Pillow et GDAL, ajouter
ultérieurement :

```text
--gdal-threads N
```

avec une valeur par défaut prudente :

```python
min(8, os.cpu_count() or 1)
```

Cette option dédiée n'est pas nécessaire au correctif minimal.

## Correctif exact du warp

### Avant

```python
_reproject(
    source        = _rio_w.band(src, b),
    destination   = _rio_w.band(dst, b),
    src_transform = src.transform,
    src_crs       = src.crs,
    dst_transform = dst_transform,
    dst_crs       = "EPSG:3857",
    resampling    = _Resampling.bilinear,
    num_threads   = 0,
)
```

### Après

```python
_reproject(
    source        = _rio_w.band(src, b),
    destination   = _rio_w.band(dst, b),
    src_transform = src.transform,
    src_crs       = src.crs,
    dst_transform = dst_transform,
    dst_crs       = "EPSG:3857",
    resampling    = _Resampling.bilinear,
    num_threads   = gdal_threads,
)
```

Le commentaire `0 = tous les CPUs` doit être supprimé.

### Extension pour la compression DEFLATE

Le contexte peut englober la création du fichier destination :

```python
with _rio_w.Env(GDAL_NUM_THREADS=str(gdal_threads)):
    with _rio_w.open(str(tif_source)) as src:
        ...
        with _rio_w.open(str(warped_part), "w", **dst_profile) as dst:
            for b in range(1, src.count + 1):
                _reproject(
                    ...,
                    num_threads=gdal_threads,
                )
```

Cela permet au pilote GeoTIFF de voir la configuration dès l'ouverture.

Le gain réel doit être mesuré : le calcul de reprojection, la compression
DEFLATE et les écritures disque peuvent se limiter mutuellement.

## Correctif exact des overviews

### Avant

```python
with _rio_o.open(str(warped), "r+") as ds_o:
    ds_o.build_overviews(overview_levels, _Res_o.gauss)
    ds_o.update_tags(ns="rio_overview", resampling="gauss")
```

### Après

```python
with _rio_o.Env(GDAL_NUM_THREADS=str(gdal_threads)):
    with _rio_o.open(str(warped), "r+") as ds_o:
        ds_o.build_overviews(overview_levels, _Res_o.gauss)
        ds_o.update_tags(ns="rio_overview", resampling="gauss")
```

Le contexte `Env` doit être placé avant `open()`. Le pilote GeoTIFF lit une
partie de sa configuration à l'ouverture du fichier.

Il ne faut pas tenter ceci :

```python
# INTERDIT : plusieurs writers concurrents sur le même TIFF
executor.map(build_one_overview_level, overview_levels)
```

GDAL n'est généralement pas thread-safe lorsque plusieurs appels modifient la
même instance de dataset. La parallélisation doit rester interne à
`GDALBuildOverviews()`.

## Journalisation proposée

Avant le warp :

```text
Warp EPSG:3857  res=0.597 m/px  zoom=18  threads=8...
```

Avant les overviews :

```text
Overviews (gauss) [2, 4, 8, ...]  threads=8  GDAL=3.9.3...
```

Après chaque phase :

```text
Warp OK       4m49s -> 1m42s  6937 Mo
Overviews OK  12m18s -> 3m31s
```

Les temps ci-dessus sont uniquement un exemple de format. Aucun facteur
d'accélération ne doit être annoncé avant un benchmark réel.

Les logs doivent contenir :

- version Rasterio ;
- version GDAL réellement embarquée par Rasterio ;
- nombre de CPU visibles ;
- valeur demandée par l'utilisateur ;
- valeur effective retenue ;
- durée séparée du warp ;
- durée séparée des overviews ;
- taille du GeoTIFF avant et après les overviews.

## Version GDAL

La version pertinente n'est pas nécessairement celle installée par Ubuntu.
Les wheels Rasterio embarquent généralement leur propre libgdal.

Diagnostic sur la VM :

```bash
~/.lidar2map/venv/bin/python -c \
  "import rasterio; print(rasterio.__version__, rasterio.__gdal_version__)"
```

Comportement proposé :

- GDAL 3.2 ou plus récent : calcul des overviews multithread ;
- GDAL 3.6 ou plus récent : meilleure prise en charge des options de
  compression et de décodage GeoTIFF utiles ici ;
- GDAL antérieur à 3.2 : forcer un thread et afficher un avertissement.

Exemple :

```python
from rasterio.env import GDALVersion

if GDALVersion.runtime().at_least("3.2"):
    overview_threads = gdal_threads
else:
    overview_threads = 1
```

Dans la pratique, les versions Rasterio récentes utilisées par le projet
embarquent un GDAL suffisamment récent. Le test explicite protège néanmoins les
environnements externes en mode `--bootstrap=pip` ou `--bootstrap=none`.

## Cache et reprise après interruption

### Défaut actuel

La création du warp utilise d'abord un fichier `.part`, mais le publie avant la
construction des overviews :

```text
créer warped.part
valider le raster principal
renommer warped.part -> warped.tif
construire les overviews dans warped.tif
```

Une interruption pendant `build_overviews()` peut donc laisser :

- un niveau principal valide ;
- des overviews absentes, partielles ou incomplètes ;
- un fichier final que `_warped_3857_valide()` considère malgré tout comme
  réutilisable.

Au lancement suivant, `warp_deja_fait=True` peut faire sauter entièrement le
bloc de création des overviews.

Il ne faut donc pas interrompre un calcul déjà engagé uniquement pour activer
les threads.

### Ordre transactionnel recommandé

Pour un nouveau warp :

```text
1. créer warped.part ;
2. terminer la reprojection ;
3. fermer et valider le niveau principal ;
4. construire les overviews dans warped.part ;
5. vérifier tous les facteurs sur toutes les bandes ;
6. renommer atomiquement warped.part -> warped.tif ;
7. seulement ensuite commencer le tuilage MBTiles.
```

Le cache final ne devient visible qu'une fois complet.

### Validation des overviews

Ajouter une fonction :

```python
def _overviews_valides(path, facteurs_attendus):
    try:
        import rasterio
        attendus = set(facteurs_attendus)
        with rasterio.open(str(path)) as ds:
            if ds.count < 1:
                return False
            return all(
                attendus.issubset(set(ds.overviews(b)))
                for b in range(1, ds.count + 1)
            )
    except Exception:
        return False
```

La réutilisation d'un cache doit vérifier :

- CRS EPSG:3857 ;
- dimensions positives ;
- lecture d'un petit bloc ;
- résolution compatible avec `zoom_max` ;
- présence de tous les facteurs nécessaires ;
- présence des facteurs sur toutes les bandes.

### Politique si les overviews échouent

Les overviews sont une optimisation de lecture, pas une condition nécessaire à
la correction du raster principal. Le fallback actuel « native tiling » doit
rester possible.

Deux états doivent cependant être distingués :

```text
warped complet       = niveau principal valide + tous les overviews attendus
warped base-only     = niveau principal valide, overviews absents/incomplets
```

Politique recommandée :

1. si les overviews réussissent, publier le cache complet ;
2. si elles échouent mais que le niveau principal est sain, permettre le
   tuilage natif pour terminer le MBTiles ;
3. ne pas enregistrer le cache `base-only` comme pyramide complète ;
4. au lancement suivant, retenter les facteurs manquants ;
5. conserver l'erreur détaillée et la version GDAL dans le log.

Une implémentation simple peut conserver un manifest adjacent :

```json
{
  "base_valid": true,
  "overviews_complete": false,
  "overview_levels": [],
  "overview_resampling": "gauss"
}
```

Le manifest ne remplace jamais la vérification réelle avec `ds.overviews()`.
Il sert à diagnostiquer et à éviter qu'un échec soit pris pour une réussite.

### Cas `source_already_warped`

Lorsque `source_already_warped=True`, `warped` désigne directement
`tif_source`. Le script ne doit pas modifier arbitrairement un fichier fourni
par l'utilisateur.

Comportement proposé :

- si la source possède déjà tous les overviews, la lire directement ;
- si elle appartient au cache lidar2map, compléter les facteurs sous verrou ;
- si elle est externe, créer un cache de travail appartenant à lidar2map ou
  utiliser le tuilage natif ;
- ne jamais ajouter silencieusement des overviews internes dans une source
  externe ;
- appliquer la même validation des facteurs avant de déclarer la pyramide
  complète.

### Changement de plage de zoom

Le nom actuel du cache contient `zoom_max`, mais pas `zoom_min` :

```text
<source>_tuilage_z18.tif
```

Deux exécutions peuvent demander :

```text
premier run  : zoom 15-18 -> overviews 2, 4, 8
second run   : zoom 8-18  -> overviews 2, 4, ..., 1024
```

Le second lancement doit détecter les facteurs manquants et compléter ou
reconstruire la pyramide. Il ne doit pas considérer le cache comme complet
uniquement parce que le TIFF principal existe.

## Concurrence entre deux lancements

Deux processus ne doivent pas modifier le même GeoTIFF simultanément.

Le correctif robuste doit ajouter un verrou par cible :

```text
<warped>.lock
```

Comportement :

1. acquisition atomique avant le warp ou les overviews ;
2. si le verrou est occupé, attendre ou sortir avec un message clair ;
3. revérifier le cache après acquisition ;
4. utiliser un `.part` unique par processus ;
5. publier une seule fois ;
6. libérer le verrou dans un `finally`.

Le pool interne GDAL peut utiliser plusieurs threads. Cela ne signifie pas que
plusieurs processus externes peuvent écrire le même fichier.

## CPU, RAM et disque

La parallélisation n'offre pas un gain linéaire garanti.

### CPU

Le filtre gaussien et DEFLATE profitent de plusieurs cœurs.

### Disque

Avec un TIFF principal de près de 7 Go, les lectures et écritures peuvent
saturer le volume de la VM. Une fois le débit disque maximal atteint, ajouter
des threads n'accélère plus le traitement.

### RAM

Chaque thread ajoute des buffers de calcul et de compression. GDAL possède
également son cache de blocs.

Recommandation initiale :

- 4 threads sur une petite VM ;
- 8 threads sur une VM disposant d'au moins 8 vCPU et d'une RAM confortable ;
- tester avant de dépasser 8 ;
- ne pas imposer `ALL_CPUS`.

Si plusieurs ombrages ou blocs sont calculés en parallèle, respecter
approximativement :

```text
nombre de processus × threads GDAL <= nombre de vCPU
```

## Interaction avec les autres parallélismes

### Encodage Pillow

Le `ThreadPoolExecutor` actuel reste utilisé pour JPEG/PNG après les overviews.
Les phases sont principalement successives, ce qui limite la surallocation.

### CSF / LAZ

`OMP_NUM_THREADS` et `--laz-parallel` concernent la conversion des nuages de
points. Ils ne doivent pas être confondus avec `GDAL_NUM_THREADS`.

### Plusieurs TIF d'ombrage

La boucle traite actuellement les TIF l'un après l'autre.

Il serait possible de traiter plusieurs TIF distincts avec des processus
distincts, mais cette évolution est séparée :

- chaque processus doit avoir son propre TIFF et son propre MBTiles ;
- le total des threads doit rester borné ;
- le disque risque de devenir le goulot ;
- deux writers ne doivent jamais viser le même fichier.

La première optimisation à appliquer est le pool interne GDAL sur un seul TIF.

## Bundle et exécution source

Le correctif se trouve dans le pipeline de calcul commun :

```python
generer_mbtiles_lidar()
```

Il profite donc :

- à l'exécution source dans le venv ;
- au bundle PyInstaller, si sa version embarquée de GDAL prend en charge le
  multithreading des overviews.

Le mode frozen évite le bootstrap Python, mais il ne court-circuite pas le
pipeline MBTiles.

Les logs doivent toujours afficher la version GDAL réellement chargée afin de
ne pas supposer que source et bundle embarquent exactement la même version.

## Calcul déjà en cours

Le nombre de threads est lu avant le lancement de l'opération GDAL. Il n'est pas
possible de transformer en multithread un `build_overviews()` déjà commencé.

Pour un run actuellement bloqué sur :

```text
Overviews (gauss) [...]
```

la conduite la plus sûre est de le laisser terminer.

Après implémentation du correctif, les prochains runs utiliseront plusieurs
cœurs. Une interruption volontaire du run courant n'est pas recommandée à
cause de la publication trop précoce du cache warpé décrite plus haut.

## Tests à ajouter

### Tests unitaires

Tester le calcul du nombre de threads :

| `tile_workers` | `os.cpu_count()` | Résultat |
|---:|---:|---:|
| 8 | 4 | 4 |
| 8 | 8 | 8 |
| 8 | 16 | 8 |
| 1 | 8 | 1 |
| 0 | 8 | 1 |
| -2 | 8 | 1 |

Avec mocks :

- vérifier que `reproject(..., num_threads=N)` reçoit `N` ;
- vérifier que `rasterio.Env(GDAL_NUM_THREADS=str(N))` englobe l'ouverture
  destinée aux overviews ;
- vérifier que `open(..., "r+")` est exécuté dans le contexte ;
- vérifier le fallback à 1 avec GDAL antérieur à 3.2 ;
- vérifier que les arguments de zoom produisent les facteurs attendus ;
- partir d'un `GDAL_NUM_THREADS` externe déjà défini et vérifier qu'il est
  restauré après le contexte Rasterio ;
- faire lever `build_overviews()` et vérifier que la configuration précédente
  est restaurée malgré l'exception.

### Test d'intégration sur petit GeoTIFF

Créer un TIFF synthétique tuilé et compressé, puis :

1. exécuter le warp avec 1 thread ;
2. exécuter le même warp avec 2 ou 4 threads ;
3. construire les mêmes overviews ;
4. comparer CRS, transform, dimensions, dtype et nodata ;
5. lire chaque niveau d'overview ;
6. comparer les valeurs de pixels.

Le fichier binaire complet n'a pas besoin d'avoir le même hash : l'ordre de
compression interne peut varier. Le contenu raster lu doit être identique, ou
respecter une tolérance explicitement définie si la version GDAL introduit des
différences d'arrondi.

### Test de cache

- cache sans overview : détecté comme incomplet ;
- cache avec seulement `[2, 4, 8]` pour une demande jusqu'à 1024 : complété ;
- cache avec tous les facteurs : réutilisé sans écriture ;
- facteur présent sur une bande mais absent sur une autre : refusé ;
- `source_already_warped=True` avec source externe : aucune modification
  silencieuse de la source ;
- changement de `zoom_min` : facteurs manquants générés.

### Test d'interruption

Injecter un échec :

- pendant le warp ;
- après le warp, avant les overviews ;
- au milieu de `build_overviews()` ;
- après les overviews, avant publication ;
- pendant le tuilage MBTiles.

Dans chaque cas :

- aucun nouveau cache final incomplet ne doit être publié ;
- un ancien cache valide doit rester intact ;
- le prochain lancement doit reprendre ou reconstruire proprement ;
- aucun MBTiles final partiel ne doit être visible.

### Test de concurrence

Lancer deux processus sur la même cible :

- le premier prend le verrou ;
- le second attend ou échoue proprement ;
- un seul fichier final est publié ;
- aucun `.part` n'est partagé ;
- le résultat est lisible.

### Benchmark Hetzner

Sur une même VM et le même TIFF :

| Threads | Warp | Overviews | CPU moyen | RSS max | Débit disque |
|---:|---:|---:|---:|---:|---:|
| 1 | à mesurer | à mesurer | à mesurer | à mesurer | à mesurer |
| 2 | à mesurer | à mesurer | à mesurer | à mesurer | à mesurer |
| 4 | à mesurer | à mesurer | à mesurer | à mesurer | à mesurer |
| 8 | à mesurer | à mesurer | à mesurer | à mesurer | à mesurer |

Mesurer séparément :

- temps du warp ;
- temps des overviews ;
- temps du tuilage ;
- taille finale ;
- utilisation CPU ;
- pic RAM ;
- lectures/écritures disque.

Le nombre par défaut pourra ensuite être ajusté à partir de mesures réelles.

## Déploiement proposé

### Étape 1 — correction du nombre de threads

- ajouter `gdal_threads` ;
- remplacer `num_threads=0` ;
- ajouter le contexte `GDAL_NUM_THREADS` ;
- afficher les valeurs effectives.

### Étape 2 — validation fonctionnelle

- tests 1 thread contre N threads ;
- comparaison des pixels et des MBTiles ;
- validation source et bundle ;
- test Ubuntu 24.04 et 26.04.

### Étape 3 — cache robuste

- vérifier les facteurs existants ;
- construire les overviews avant publication ;
- gérer les facteurs manquants ;
- ajouter le verrou par cible ;
- tester les interruptions.

### Étape 4 — benchmark

- mesurer 1, 2, 4 et 8 threads sur une VM représentative ;
- retenir un plafond par défaut ;
- documenter les besoins RAM/disque.

## Critères d'acceptation

Le correctif est terminé lorsque :

1. le warp reçoit une valeur `num_threads` explicite supérieure à 1 lorsque
   plusieurs CPU sont autorisés ;
2. les overviews utilisent `GDAL_NUM_THREADS=N` ;
3. `--workers N` influence effectivement les deux phases dans le correctif
   minimal ;
4. la valeur effective ne dépasse pas `os.cpu_count()` ;
5. les versions GDAL/Rasterio et les threads sont affichés ;
6. tous les facteurs attendus existent sur toutes les bandes ;
7. le rendu 1 thread et N threads est équivalent ;
8. aucun writer concurrent ne modifie le même TIFF ;
9. une interruption ne publie pas de cache incomplet ;
10. un changement de `zoom_min` complète correctement la pyramide ;
11. le bundle et le mode source passent les mêmes tests fonctionnels ;
12. le benchmark montre le gain réel sans dépassement de la RAM retenue.

## Références

- GDAL `gdaladdo`, filtres et multithreading :
  <https://gdal.org/en/stable/programs/gdaladdo.html>
- Pilote GDAL GeoTIFF, overviews et threads :
  <https://gdal.org/en/stable/drivers/raster/gtiff.html>
- Règles de sécurité multithread GDAL :
  <https://gdal.org/en/stable/user/multithreading.html>
- Configuration GDAL :
  <https://gdal.org/en/stable/user/configoptions.html>
- Rasterio, API `build_overviews()` :
  <https://rasterio.readthedocs.io/en/stable/api/rasterio.io.html>
- Rasterio, création d'overviews :
  <https://rasterio.readthedocs.io/en/stable/topics/overviews.html>
- Rasterio, configuration avec `Env` :
  <https://rasterio.readthedocs.io/en/stable/topics/configuration.html>
- Rasterio, API `reproject()` :
  <https://rasterio.readthedocs.io/en/stable/api/rasterio.warp.html>
- Implémentation Rasterio du choix mono/multithread :
  <https://github.com/rasterio/rasterio/blob/1.4.4/rasterio/_warp.pyx>
