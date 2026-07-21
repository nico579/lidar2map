# Suivi des revues LAZ / DFM / CSF

Chaque revue est une liste de **questionnements à trancher**. Ce fichier les suit
pour ne rien oublier et ne pas re-litiger. Statuts :

- `[x]` fait / livré
- `[-]` rejeté (avec motif)
- `[>]` différé roadmap (avec motif)
- `[T]` gated validation TERRAIN (l'oeil de l'archéo tranche, pas le code)
- `[?]` ouvert, décision requise / à mesurer

---

## Revue 1 : contrat multi-provider + critique DFM/CSF (2026-07-18)

Verdict de fond : le pipeline fr/ch actuel n'a pas de bug ; c'est le CONTRAT
multi-provider qui n'était pas assez défensif.

### Livré
- `[x]` Garde CRS/unités (refuse un EPSG horizontal ou une unité != provider ;
  lenient si CRS absent / compound / non résoluble). `common._verifie_crs_las`.
- `[x]` Bruit/withheld (classes ASPRS 7/18 + flag) écartés avant le binning
  (robustesse min-z ; no-op sur données propres, IGN/CRAIG = 0 bruit).
- `[x]` Deps laspy/CSF vérifiées AVANT le download (`LazProvider.discover_dalles`).
- `[x]` Warn si un ZIP contient plusieurs nuages (au lieu du drop silencieux).
- `[x]` Provider CRAIG validé bout-en-bout et intégré (`fr-craig` + `fr-craig-laz`).

### Rejeté
- `[-]` "Cache non reproductible, diffs de plusieurs mètres livrés" : contresens.
  Le code livré (a+b) est bit-identique ; les 3,3 m sont la variante float32
  REJETEE, lue dans la note de rejet et mal attribuée.

### Différé (roadmap)
- `[>]` `ref_ground` paramétrable + nommage tolérant aux noms non-numériques :
  quand un provider concret l'exige (CRAIG ne l'a pas exigé).
- `[>]` Pré-filtre CSF conscient de la pente ; halo de traitement inter-dalles.
- `[>]` Masques témoins (mesuré vs interpolé, DFM moins DTM, densité, confiance).
  Meme famille que "interpolation 200 m opaque" et "sortie 1-bande".
  `tools/dfm_ruines.py` les fournit en standalone.
- `[>]` Dédoublonnage multi-acquisition / choix du millésime (l'union CRAIG
  dédoublonne déjà par clé) ; lecture COPC fenêtrée (futures sources COPC type
  NRCan) ; identité de cache enrichie (version lib CSF + ETag source) ; verrou
  inter-process (cas de bord).
- `[>]` Taxonomie provider-type + colonnes de validation dans la roadmap (polish).

### Gated validation terrain
- `[T]` Min-z vers quantile bas robuste (après calibration sur site).
- `[T]` "Un retour sol efface un mur" : faiblesse connue du mode classes (le
  docstring l'avoue ; le CSF la contourne).
- `[T]` Tests adverses réels : mur traversant 2-4 dalles, rappel / faux positifs
  par hectare sur ruines connues + zones négatives (rochers, falaises,
  restanques, maquis).

### Vérifié = non-problème
- `[x]` Seuil 500 ko : géré (le coeur lit `PROVIDER.SEUIL_DALLE_VALIDE`, CRAIG
  le pose à 50 ko).
- `[x]` Veto classe 9/66 : `ref_ground` est déjà découplé à la classe 2.

### Leads providers (chasse à part, valider un par un comme CRAIG)
- `[?]` **A DEMARRER EN DEBUT DE PROCHAINE SESSION (choix Nico 2026-07-18).**
  GUGiK Pologne (WFS EPSG:2180, noms alphanumériques), Estonie Maa-amet
  (EPSG:3301), Québec, USGS LPC, NRCan, Flandre, Danemark, Finlande.
  Méthode = celle de CRAIG : endpoint reproductible + donnée apte + conversion
  réelle, pas juste le header. Le garde CRS/unités déjà en place couvre les CRS
  variables.
- data.europa.eu = outil de DECOUVERTE (métacatalogue), pas un provider.

---

## Revue 2 : performance LAZ / CSF (2026-07-18)

- `[x]` **P0** `exportCloth=False` (`do_filtering(g, ng, False)`) : le wrapper CSF
  écrivait le tissu dans `cloth_nodes.txt` (~188 Mo/dalle 1 km) après la
  classification, sans la modifier. Gain ~40,6 s/dalle 1 km, plus de fichier
  parasite, sortie inchangée. Prouvé sûr (la variance run-to-run est la même
  avec/sans, = non-détermination OpenMP).
- `[x]` **`--laz-parallel N`** : sémaphore réglable + `OMP_NUM_THREADS=coeurs/N`
  + pool download >= N. NEUTRE sur 4 coeurs (une conversion sature déjà via
  lazrs + CSF OpenMP + numpy). Gain sur VM multi-coeurs = a MESURER là-bas.
- `[-]` **P1** lecture LAZ par blocs (RAM /2) : reco SKIP. Le rationale
  "faire tenir 2 conversions" tombe (2 conversions ne gagnent rien sur 4 coeurs) ;
  RAM ample sur VM ; gros build risqué. En réserve si OOM concret sur machine
  contrainte.
- `[-]` Numba pour le binning : inutile (0,18 s gagné, 4,5 s de compile ; le
  goulot est CSF + l'interpolation fillnodata, pas le binning).
- `[>]` P2 micro-opts (index int32, table booléenne de classes, fillnodata en
  place, `del` anticipés) : dixièmes de seconde, bit-identiques. A faire seulement
  si on refactore la conversion (int32 = le plus intéressant, halve la RAM index).
- `[-]` Build CSF "ground-only" (patch C++) : spéculatif, non compilé/testé, veille.
- `[-]` A écarter sous "zéro perte qualité" (ne pas re-proposer) : coords
  relatives/float32, décimation avant CSF, moins d'itérations, changer résolution
  ou time_step, remplacer le nuage par le min d'une grille, découpage en
  sous-tuiles indépendantes, changer le nb de threads OMP par défaut, plusieurs
  dalles CSF en parallèle sur 4 coeurs / 8 Go.
- Finding : CSF est NON-DETERMINISTE (OpenMP). Pour valider : comparer le raster
  final + répéter la référence, PAS exiger des listes d'indices CSF identiques.

---

## Chasse LAZ (2026-07-21) : validation endpoint des leads de la Revue 1

Méthode = celle de CRAIG (endpoint REPRODUCTIBLE + donnée APTE + conversion
réelle). Ici : endpoints CONFIRMÉS par sondage direct des leads de la revue
(pas repartir de zéro). Conversion réelle (download LAZ + las_to_dfm) = étape
suivante, pas encore faite.

### Pologne — `pl-gugik-laz` (LIVRÉ + validé bout-en-bout 2026-07-21)
- `[x]` **Endpoint reproductible CONFIRMÉ** : WFS skorowidze
  `https://mapy.geoportal.gov.pl/wss/service/PZGIK/DanePomiaroweLidarKRON86/WFS/Skorowidze`
  (WFS 2.0.0, un typename par année `gugik:SkorowidzDanychPomiarowychLIDAR<AAAA>`,
  2010-2019 ; il existe aussi le service EVRF2007 2018-2020). GetFeature par bbox
  → chaque feature porte `gugik:url_do_pobrania` = URL LAZ directe
  (`https://opendata.geoportal.gov.pl/NumDaneWys/DanePomiaroweLAZ/<id>/<...>.laz`),
  + `gugik:godlo` (nom feuille alphanumérique), `gugik:char_przestrz` (densité),
  `gugik:blad_sr_wys` (erreur alti), `gugik:uklad_xy`. = pattern IGN/CRAIG (WFS
  index + url par dalle), réutilise `common.ign_lidar_hd_dalles` adapté.
- `[x]` **Donnée APTE** : **20 pts/m²** (2× IGN HD), erreur alti **0,02 m**,
  nuage classé, LAZ. Excellent pour le micro-relief.
- `[?]` **WRINKLE CRS** : le nuage LAZ est en **PL-2000 par zone** (S5-S8 =
  EPSG:2176-2179 selon la longitude), PAS en EPSG:2180 (2180 = CRS de l'INDEX WFS
  seulement). Le `pl-gugik` raster existant est EPSG:2180 (WCS DTM), inadapté ici.
  → besoin d'un CRS PAR RUN (déterminé du bbox : zones aux méridiens 15/18/21/24°E)
  = petite extension `LazProvider` (miroir de `set_cloud_cache_dir`). bounds
  anti-couture : reprojeter la géométrie d'index 2180→zone, ou lire le header LAZ.
  DÉCISION À TRANCHER avant impl (design-avant-déploiement).

### Estonie — `ee-maaamet-laz` (LIVRÉ + validé bout-en-bout 2026-07-21)
- `[x]` **Endpoint** : le LAZ standard (`andmetyyp=lidar_laz_tava`) exige
  l'ANNÉE de scan par feuille (`{NR}_{année}_tava.laz`), non dérivable des coords
  (aucun motif « dernier » : les autres millésimes → HTML). On lit donc l'INDEX
  1:2000 officiel `epk2T_SHP.zip` (~1,3 Mo, caché, `common.ee_maaamet_dalles`) :
  par feuille 1 km, champ `NR` + `ALS_TAVA_1..4` (années standard) + géométrie
  → on prend le millésime le plus récent. `madal` (basse altitude, ~280 Mo/km²)
  ignoré (tava ~30-45 Mo suffit). **CRS EPSG:3301 UNIQUE** → pas de wrinkle ;
  header LAZ compound (3301+EVRF2007) dénoué par le garde.
- `[x]` **Validé** : discover live = 25 tuiles (URLs tava, bon millésime) ; 1
  tuile téléchargée (44 Mo) = **4,1 pts/m²**, classée ; conversion `las_to_dfm`
  = **2000×2000 px EPSG:3301, 100 % valide** (avec bruit 7/18 → re-valide le fix
  withheld). bounds = géométrie de l'index (anti-couture 1 km propre, contrairement
  à la Pologne). Défaut ground=csf (sursol dominé par la classe 5).
- `[?]` **Densité 4 pts/m²** (~0,5 m d'espacement) = APTE mais MARGINAL pour du
  0,5 m (vs 20 PL, 60 CRAIG) : à confirmer en validation terrain sur un site connu.

### Pologne : ce que la CONVERSION RÉELLE a livré + révélé (2026-07-21)
- `[x]` `providers/pl_gugik_laz.py` + helper `common.gugik_dalles` + extension
  `LazProvider.set_crs` (CRS par run). CRS_NATIF=2180 (index/Mercator), tuiles
  produites en zone PL-2000 (le warp du cœur lit le CRS DU FICHIER, l.~7743).
  bounds_fn=None. Défaut ground=csf. Parent raster `pl-gugik` → LAZ-capable auto
  (dropdown Mode LAZ + hachure carte). smoke : point Lubuskie + `--skip` CI.
- `[x]` **Validé** : discover live = 194 tuiles (URLs LAZ réelles) ; 1 tuile
  téléchargée (59 Mo) = **28,4 pts/m²**, header CRS vide (garde lenient), classes
  ASPRS ; conversion `las_to_dfm` = **1600×913 px EPSG:2176, 100 % valide**.
- `[x]` **BUG LATENT CORRIGÉ dans le `las_to_dfm` partagé** (révélé PAR la vraie
  conversion, exactement l'intérêt de la méthode) : `np.asarray(las.withheld)`
  renvoie un **uint8**, donc `bruit(bool) | wh(uint8)` promeut en uint8 → `~bruit`
  = complément BITWISE et `xs[garde]` = indexage ENTIER → l'emprise s'effondrait
  (dalle 1×1). Invisible sur fr/ch (0 bruit → `bruit.any()` False → bloc sauté) ;
  déclenché par la Pologne (classe 7). Fix = `.astype(bool)`. Garde anti-régression
  = classe 7 ajoutée au nuage synthétique 9a de `_test_interactions`.

### Flandre — `be-flanders-laz` (LIVRÉ + validé bout-en-bout 2026-07-21)
- `[x]` **Endpoint** : WFS OpenLidar `openlidar:LiDAR_DHMV_II_LAZtiles` (Digitaal
  Vlaanderen), une feature par tuile 500 m portant `tile_location` (chemin .laz)
  → URL = base fixe `remotesensing.vlaanderen.be/download/openlidar/` + chemin
  (le .laz brut, base extraite du featureInfoHandler.js de l'app). CRS EPSG:31370
  UNIQUE (pas de wrinkle), header vide (garde lenient). `common.be_flanders_dalles`,
  bounds = bloc 500 m nominal. Défaut ground=csf (classif Flandre = 1/2/9, murs
  en « non classé » 1).
- `[x]` **Validé** : discover live 30 tuiles ; tuile 17 Mo = **11,4 pts/m²** (2,86 M
  pts, meilleur que l'Estonie), classée ; conversion 1000×1000 EPSG:31370 100 % valide.
- `[x]` **BUG LATENT CORRIGÉ** `common._geom_bbox` ne gérait que le 2D (`len(o)==2`)
  → géométrie 3D Flandre `[X,Y,Z]` renvoyait None → 0 dalle. Fix `len(o)>=2`
  (X=o[0],Y=o[1], Z ignoré). Rétro-compatible CRAIG (2D). Encore révélé par la
  conversion réelle.

### Canada — `ca-nrcan-laz` (LIVRÉ + validé bout-en-bout 2026-07-21, NOUVELLE CAPACITÉ COPC)
- `[x]` **Capacité COPC fenêtrée construite** (la roadmap l'avait DIFFÉRÉE) :
  `common.copc_window_to_las(url, bbox_wgs84, out_las)` lit via range-requests
  UNIQUEMENT les points de la bbox d'un COPC distant (laspy `CopcReader.open(url)`,
  pas de download du fichier 200-750 Mo) + reprojette la bbox WGS84 → CRS du COPC.
  Branche cœur `telecharger_copc_fenetre` (flag `COPC_WINDOWED`, miroir de
  `telecharger_cog_fenetre`) : fenêtre → .las → `post_fetch` → GeoTIFF.
- `[x]` **Endpoint** : index GPKG des tuiles (407 Mo) requêté À DISTANCE via
  `/vsicurl` (R-tree + range-requests, ~2 s/bbox, champ `URL` = COPC directe).
  Nommage (x,y) = coin SW géographique en entiers positifs ((lon+180)·1e4, lat·1e4).
- `[x]` **CRS multi-zones** : COPC en UTM NAD83(CSRS) compound (+CGVD2013) PAR
  ZONE, dénoué dans le header → posé par run via `set_crs` (le warp lit le CRS du
  fichier). CRS_NATIF = géographique 4617 (cadrage/fenêtrage).
- `[x]` **Validé** : discover live 36 tuiles ; fenêtre 400 m = ~6,6 M pts en 15 s ;
  bout-en-bout `telecharger_copc_fenetre` = CSF → .tif 664×644 EPSG:2956 (UTM 12N)
  100 % valide. **~40 pts/m²** (le plus dense). LIMITE : très dense → zone d'1 km²
  = ~40 M pts (~1 Go .las tmp, ~3 Go RAM). Zone PETITE conseillée.

### USA — `us-3dep-laz` (LIVRÉ + validé bout-en-bout 2026-07-21, hook signature SAS)
- `[x]` **Endpoint** : STAC Planetary Computer, collection `3dep-lidar-copc` (le
  nuage national 3DEP reformaté en COPC ; l'autre forme, l'EPT public sur
  `s3://usgs-lidar-public`, exige PDAL, absent → écartée). Search par bbox →
  un COPC par tuile (asset `data`). Couverture CONUS + Alaska + Hawaii + Guam,
  2012-2022. Dédup par coin SW + tri `datetime desc` (millésime récent, comme EE).
- `[x]` **NOUVEAU vs Canada : signature SAS**. Le blob Azure PC refuse l'accès
  public (HTTP 409). Nouveau **hook cœur `PROVIDER.sign_url(url)`** (défaut
  identité, appelé dans `telecharger_copc_fenetre` juste avant l'ouverture COPC
  → signé à l'instant du DOWNLOAD, pas de péremption ; mirror de
  `gdal_env_options()`). `us-3dep-laz.sign_url` = GET sur l'endpoint public
  anonyme `/api/sas/v1/sign` (stdlib urllib, 0 dépendance, choix Nico ; env
  `PC_SDK_SUBSCRIPTION_KEY` facultative pour lever la limite anonyme). NRCan
  n'expose pas le hook → identité. **Aucun compte requis** (le raster jumeau
  us-3dep, lui, exige une clé OpenTopography et réserve son 1 m à l'académique :
  le mode LAZ est PLUS accessible que le raster).
- `[x]` **CRS multi-zones** : `proj:epsg` absent des propriétés STAC → lu dans le
  header du COPC (UTM NAD83 par zone), posé par run via `set_crs` (identique
  Canada). CRS_NATIF = géographique NAD83 (4269).
- `[x]` **Validé bout-en-bout** (Colorado, projet SoPlatteRiver) via le vrai
  `telecharger_copc_fenetre` : discover STAC (2 tuiles) → sign → fenêtre → conversion.
  Sortie **1029×1332 px EPSG:26913 (UTM 13N), 0,5 m, z=[1586,1604] m**, 1,37 M px
  valides, en mode `classes` ET en mode `csf` (défaut). Densité **~5,3 pts/m²**
  sur un levé 2013 (QL2 ; les projets récents QL1 montent à 8-20), classée ASPRS
  (classes 7/18 bruit présentes → re-valide le fix withheld). Défaut ground=csf
  (1254 projets, classif hétérogène). smoke : point Colorado + `--skip` CI.
- **Carte** : pas de région USA continentale dans `REGIONS` (couverture 3DEP par
  PROJET, comme le Canada/USA) → rien à hachurer, pas de régen carte.

### Québec — `ca-quebec` (MNT 1 m) + `ca-quebec-laz` (validés bout-en-bout 2026-07-21)
- `[x]` **1er provider Québec, et 1er jumeau LAZ qui a DÛ créer son raster parent**
  (tous les `*_laz` en ont un ; aucun `ca-quebec` n'existait). Choix Nico : monter
  les DEUX (MNT + LAZ), comme la France. `common.quebec_wfs_features` partagé.
- `[x]` **Parent `ca-quebec` (MNT 1 m, COG_WINDOWED)** : WFS RGQ
  `Index_Telechargement_Mnt_Pub:IndexTelechargementMNT` par bbox → COG GeoTIFF
  15 km/feuille (~600 Mo, tiled 256 + overviews) lu en FENÊTRE via /vsicurl. CRS
  **UNIQUE EPSG:6622** (Québec Lambert). Dédup par emprise → année récente (pas de
  couche PlusRecent côté MNT). Deux spécificités : `gdal_env_options` autorise
  l'extension `.TIF` MAJUSCULE (filtre GDAL sensible à la casse), et `post_download`
  ESTAMPILLE EPSG:6622 (le COG porte un WKT « Quebec Lambert_SCRS » complet mais
  SANS code EPSG → `to_epsg()`=None ; params identiques à 6622 → assignation, pas
  reprojection). Validé : fenêtre → .tif EPSG:6622 res 1 m, z=[9,23] m.
- `[x]` **Jumeau `ca-quebec-laz`** : WFS `IndexTelechargementLidarPlusRecent`
  (dédup millésime CÔTÉ SERVEUR, une couche dédiée) → `TELECHARGEMENT_TUILE` = URL
  LAZ directe (pattern IGN/Pologne, pas COPC). **CRS MULTI-ZONES MTM par fuseau**
  (CODE_EPSG explicite par tuile, 2949-2952) → `set_crs` au fuseau dominant du lot ;
  contrairement à la Pologne le header LAZ PORTE le CRS → le garde refuse
  ACTIVEMENT une tuile d'un autre fuseau. Défaut csf (classif hétérogène brute
  0,1,2,8 / classée 1,2,7,9). Préfixe cache `qc_laz05` (distinct du `ca_laz05`
  NRCan, même pays 'ca'). Validé bout-en-bout : WFS → set_crs 2949 → download 70 Mo
  → CSF → .tif **2000×2000 EPSG:2949 (MTM 7), 0,5 m, ~10 pts/m²**, classée
  (bruit 7 → re-valide fix withheld), z=[3,24] m.
- Carte : pas de polygone région Québec (couverture par PROJET, un polygone
  provincial surestimerait, comme le Canada). ca-quebec = 1er provider `ca` raster
  hors NRCan → README régénérés au release.

### Finlande — `fi-maanmittauslaitos-laz` (DÉCLASSÉ 2026-07-21, mur d'auth + samples-only)
- `[?]` **Endpoint CARTOGRAPHIÉ** : le nuage laser 5p (≥5 pts/m², LAZ 1.2/1.4,
  EPSG:3067, tuiles 1 km) vit sur le **file download service** (tiedostopalvelu),
  PAS sur le WCS raster du parent. Feed ATOM base
  `https://tiedostopalvelu.maanmittauslaitos.fi/tp/feed/mtp`, param **`api_key=`
  (UNDERSCORE)** (le WCS parent, lui, veut `api-key=` TIRET), feed produit
  `/tp/feed/mtp/<produit>/<version>?api_key=…`, download
  `/tp/lataus/<clé>/1/<filename>`.
- `[-]` **BLOQUÉ : scope de clé.** 2 clés NLS OmaTili testées (avoin-karttakuva) :
  **WCS 200** (clés valides) mais tiedostopalvelu **403** (param `api_key=` reconnu,
  mais NON autorisé) sur TOUS les produits (même l'ortho de référence). Le 403 (≠
  401) = la clé est reconnue mais n'a pas la permission « file download service ».
  À régler côté compte NLS (activer l'interface tiedostopalvelu pour la clé dans
  OmaTili, OU clé séparée ordonnée par email selon le tier). Rien à coder tant que
  le 403 tient (le feed produit reste invisible : identifiant laser + nommage tuiles
  indéterminables). NB : la doc OGC API Features / Basic auth ≠ ce service (feed à
  param URL). Dès le scope OK → discover feed + code + valide (endpoint déjà mappé).
- `[-]` **Alternatives ÉPUISÉES** : la clé accède AUSSI à l'OGC API Features
  `avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot` (Basic auth = 200) mais ce
  service ne sert QUE du VECTORIEL (collections « korkeus » = courbes de niveau,
  PAS le nuage) ; aucun endpoint laser/élévation sur avoin-paikkatieto (tout 404).
  Le nuage laser n'existe QUE sur tiedostopalvelu. Les clés OmaTili WMS/WCS/OGC-API
  n'ouvrent PAS le file download service.
- `[-]` **MUR D'AUTH INFRANCHISSABLE + samples-only (verdict final)** : activer le
  scope tiedostopalvelu passe par OmaTili, qui exige une identification **Suomi.fi**.
  Or la liste des eID étrangers acceptés (NL/BE/ES/IT/AT/HR/CY/LV/LI/LT/LU/MT/PT/PL/
  SE/DE/SK/SI/DK/CZ/EE) **N'INCLUT PAS LA FRANCE** → Nico ne peut pas s'authentifier.
  Le service interactif MapSite (`asiointi.../karttapaikka/tiedostopalvelu`) a une
  API de DÉCOUVERTE OUVERTE (session anonyme : `/karttapaikka/api/spatialDataFiles/
  laser5pProductionAreas` = 149 zones, `/laser5pMapsheets/<tuotantoalueId>` = feuilles
  1 km `karttalehtitunnus`), MAIS le DOWNLOAD laser5p est **login-gated**
  (i18n `laserkeilausaineisto_5p.login` = « Kirjaudu asiointipalveluun » →
  `/kiinteistoasiat/?auth=4`) et **sous restrictions d'usage** (publication/
  redistribution limitées, traitement hors UE/EEE restreint). Le seul chemin PUBLIC
  (`tiedostopalvelu/tp/julkinen/lataus/tuotteet/Avoin_laseraineisto5p`, ZIP par
  feuille sans auth) ne contient que **6 zones ÉCHANTILLONS** (Nurmijärvi, Nuuksio,
  Pieksämäki, Suomutunturi, Forssa), PAS la couverture nationale. VERDICT : pas de
  provider national viable (auth Suomi.fi hors de portée FR + national restreint +
  public = démos). Comme la Wallonie (accès non reproductible/gaté). Ré-ouvrir SEULEMENT
  si NLS ouvre un accès national programmatique sans Suomi.fi.

### Suite de la chasse
- **Pologne + Estonie + Flandre + Canada + USA + Québec LIVRÉES** (jumeaux LAZ
  3 → 9 ; Québec = source de plus sous 'ca', pas un nouveau pays). Reste à valider
  TERRAIN la densité 4 pts/m² estonienne.
- Non encore sondés : Danemark (compte Datafordeler, + risque dépréciation
  Prædefineret LAZ). Finlande = DÉCLASSÉE (mur Suomi.fi sans eID FR + national
  restreint + public samples-only, ci-dessus).
  Patterns dispo : `sign_url` (COPC authentifié), `set_crs` (multi-zones), STAC +
  signature (USA), WFS PlusRecent + LAZ direct (Québec), index caché+millésime
  (Estonie), COG/COPC fenêtré + /vsicurl (Canada/Québec MNT).

## A mesurer sur la VM Scaleway (Apple Silicon M-series, macOS ARM)
- `[?]` `--laz-parallel 2 / 3 / 4` : débit réel. Dépend de combien de coeurs UNE
  conversion utilise, et macOS ARM peut threader autrement que mes mesures
  Windows (build CSF OpenMP différent).
