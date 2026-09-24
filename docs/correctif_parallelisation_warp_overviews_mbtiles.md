# Parallélisation du warp et des overviews MBTiles

Ouvert : 2026-07-28 (investigation)  
Mis à jour : 2026-09-24 (étape 1 implémentée, document aligné sur le code)  
Périmètre : `generer_mbtiles_lidar()` dans `_mbtiles_lidar.py`, étape
`STEP: 3/3 MBTiles`

## État

| Point | État |
|---|---|
| Warp multi-thread (`num_threads` explicite > 1) | Fait |
| Compression DEFLATE du GeoTIFF warpé en parallèle | Fait |
| Overviews multi-thread (`GDAL_NUM_THREADS`) | Fait |
| Nombre de threads borné, jamais `ALL_CPUS` | Fait |
| Threads et version GDAL dans le log | Fait |
| Overviews construites sur le `.part` avant publication | Déjà en place avant ce correctif |
| Rendu identique 1 thread / N threads | Vérifié par test |
| Réglage utilisateur du nombre de threads | À faire |
| Validation des facteurs d'overviews d'un cache réutilisé | À faire |
| Verrou par cible entre deux processus | À faire (optimisation) |
| Benchmark sur VM réelle | À faire |

## Constat d'origine (2026-07-28)

Run réel sur VM Hetzner :

```text
STEP:3/3 MBTiles
  gareoult_40_lrm_s2p5m_ombrage.tif
  Estimated size: ~4.5 Go -> single warp (rasterio streaming)
  Warp EPSG:3857  res=0.597 m/px  (rasterio, zoom 18)...
  gareoult_40_lrm_s2p5m_ombrage_tuilage_z18.tif [] 100%  4m49s  6937 Mo
  warped dims : 95361 × 95700 px
  Overviews (gauss) [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]...
```

Pendant le warp et les overviews, un seul cœur travaillait. Le raster warpé
compte environ 9,13 milliards de pixels. Les overviews en ajoutent environ un
tiers (3,04 milliards), chacun filtré, écrit et compressé.

Deux causes :

1. **Warp** : l'appel passait `num_threads=0`, commenté « 0 = tous les
   CPUs ». Rasterio ne prend le chemin multi-thread (`ChunkAndWarpMulti`) que
   si la valeur est strictement supérieure à 1 : avec 0, le warp tournait sur
   un seul cœur. Mesuré : même durée avec 0 qu'avec 1.
2. **Overviews** : `Dataset.build_overviews()` n'a pas de paramètre de
   threads. Sans `GDAL_NUM_THREADS`, `GDALBuildOverviews()` calcule sur un seul
   thread.

La compression DEFLATE du GeoTIFF warpé restait elle aussi mono-thread (défaut
du pilote GTiff). Une fois le warp parallélisé, c'était le goulot principal.

## Implémentation actuelle

### Nombre de threads

`_gdal_threads(tile_workers)` dans `_mbtiles_lidar.py` :

```python
max(1, min(int(tile_workers), os.cpu_count() or 1))
```

- toujours un entier >= 1 (0, négatif ou valeur invalide donnent 1) ;
- jamais plus que les CPU visibles ;
- jamais `ALL_CPUS` : une valeur numérique explicite.

`tile_workers` vient de `_tile_workers_defaut()`, c'est-à-dire
`os.cpu_count()`. **`--workers` ne le pilote plus** : cette option règle
uniquement les connexions réseau (plafond de throttle des fournisseurs).
Aujourd'hui, la valeur effective est donc le nombre de CPU visibles. Aucune
option ne permet de la réduire (voir « Reste à faire »).

### Warp

- `rasterio.warp.reproject(..., num_threads=gdal_threads)`, pour les bandes
  comme pour le masque de couverture `_cov.tif` ;
- option de création GTiff `NUM_THREADS=<gdal_threads>` sur le fichier
  destination : compression DEFLATE parallèle. Selon la documentation GDAL,
  c'est l'alternative à `GDAL_NUM_THREADS` pour ce pilote.

### Overviews

```python
with rasterio.Env(GDAL_NUM_THREADS=str(ovr_threads)), \
        rasterio.open(str(warped_part), "r+") as ds:
    ds.build_overviews(overview_levels, Resampling.gauss)
```

- `Env` est posé **avant** `open()`, car le pilote GTiff lit sa
  configuration à l'ouverture ;
- `ovr_threads = gdal_threads`, ramené à 1 si le GDAL chargé est antérieur à
  3.2 (`_gdal_overviews_multithread()`). C'est la version embarquée par
  rasterio qui compte, pas celle du système ;
- un seul appel `build_overviews()` : jamais plusieurs niveaux en parallèle
  sur le même dataset (GDAL n'est pas sûr avec plusieurs writers sur une même
  instance).

### Journalisation

```text
  Warp EPSG:3857  res=0.597 m/px  (rasterio, zoom 18, threads=8/8 CPU)...
  Overviews (gauss) [2, 4, 8, ...]  threads=8  GDAL=3.10.3...
  Overviews OK (…)
```

Les durées du warp et des overviews restent affichées séparément.

### Publication et cache

Ordre actuel pour un nouveau warp, tout sur des fichiers `.part` uniques par
processus (`<nom>.<pid>.<jeton>.part`) :

1. reprojection vers `warped.part`, puis masque de couverture vers
   `warped_cov.part` (publié aussitôt) ;
2. overviews construites **dans `warped.part`** ;
3. validation (`_warped_3857_valide` : CRS 3857, dimensions, lecture d'un
   bloc) ;
4. `replace` atomique `warped.part` → `warped.tif` ;
5. tuilage MBTiles.

Une interruption pendant le warp ou les overviews ne publie donc jamais de
cache incomplet. L'ancienne analyse (« overviews construites après
publication ») ne décrit plus le code.

Si la source est déjà en EPSG:3857 (`source_already_warped`), elle est lue
directement. Aucune overview n'y est ajoutée : un fichier fourni par
l'utilisateur n'est jamais modifié.

## Mesures

Machine de développement à 4 vCPU, rasterio 1.4.4, GDAL 3.10.3, données
synthétiques :

| Phase | Donnée | Avant | Après |
|---|---|---:|---:|
| Warp + écriture DEFLATE | float32 8000×8000, peu compressible | 12,7 s | 3,6 s |
| Overviews gauss [2, 4, 8, 16, 32] | uint8 8000×8000 | 1,2 s | 0,4 s |

Pixels du warp et de chaque niveau d'overview comparés : identiques à
l'octet. Ces chiffres ne remplacent pas un benchmark sur la VM de production.
Le gain réel dépend du nombre de cœurs, de la compressibilité et du débit
disque.

## Tests

`tests/_test_mbtiles_lidar_atomic.py`, classe `ThreadsGdalTests` :

- table de `_gdal_threads` : (8, 4 CPU) → 4, (8, 16) → 8, (1, 8) → 1,
  (0, 8) → 1, (-2, 8) → 1, valeur invalide → 1, `cpu_count()` inconnu → 1 ;
- producteur complet en 1 thread puis en 4 threads sur une pyramide z14-16
  réelle (warp + overviews [2, 4]) : tuiles MBTiles identiques, threads
  présents dans le log.

Les garanties de publication (échec de validation, exception d'encodeur,
arrêt coopératif, réutilisation du cache) sont couvertes par
`MbtilesLidarAtomicTests` dans le même fichier.

## Reste à faire

### Réglage utilisateur du nombre de threads

Sur une machine partagée ou une grosse VM, prendre tous les CPU visibles n'est
pas toujours souhaitable. Il faudra aussi respecter approximativement
`processus × threads GDAL <= vCPU` quand plusieurs ombrages ou blocs tournent
en parallèle. Proposition : une option dédiée, sans réutiliser `--workers` qui
règle le réseau :

```text
--gdal-threads N     (défaut : nombre de CPU visibles)
```

### Facteurs d'overviews d'un cache réutilisé

`warp_deja_fait` ne vérifie que la taille, la fraîcheur, la validité 3857 et
la présence de `_cov.tif`. Il ne vérifie **pas** les facteurs d'overviews. Le
cache est nommé d'après `zoom_max` seulement (`<source>_tuilage_z18.tif`),
donc :

```text
premier run  : zoom 15-18 -> overviews 2, 4, 8
second run   : zoom 8-18  -> cache réutilisé, facteurs 16 à 1024 absents
```

Le rendu reste correct : GDAL lit l'overview disponible la plus proche puis
rééchantillonne. Mais les bas zooms sont lus depuis une résolution bien plus
fine que nécessaire, donc lentement. À ajouter : vérifier
`ds.overviews(b)` pour chaque bande, et compléter les facteurs manquants
(sur un `.part`, puis publication atomique) quand le cache appartient à
lidar2map.

### Verrou par cible

Deux processus visant le même warpé écrivent chacun leur `.part` unique, puis
publient par `replace` atomique : pas de corruption, seulement du travail en
double. Sous Windows, le `replace` peut échouer si l'autre processus lit déjà
le fichier final pour son tuilage. Un verrou `<warped>.lock`
(`_atomic_files.verrou_inter_processus`) éviterait le double calcul. Il
faudrait revérifier le cache après l'acquisition.

### Benchmark sur VM

Même TIFF réel, même VM, 1, 2, 4 et 8 threads. Mesurer la durée du warp, des
overviews et du tuilage, le CPU moyen, la RAM maximale et le débit disque.
Choisir ensuite le défaut de `--gdal-threads`.

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
