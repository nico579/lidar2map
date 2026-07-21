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

### Suite de la chasse
- **Pologne + Estonie + Flandre LIVRÉES** (3 pays LAZ cette session, jumeaux LAZ
  3 → 6). Reste à valider TERRAIN la densité 4 pts/m² estonienne.
- Non encore sondés : Québec, USGS LPC, NRCan, Danemark, Finlande. `set_crs`
  (Pologne) resservira aux pays multi-zones (Allemagne UTM 32/33, USGS UTM…) ;
  « index caché + année par feuille » (Estonie) aux sources à millésime explicite ;
  « WFS + tile_location + base fixe » (Flandre) aux index à chemin relatif.

## A mesurer sur la VM Scaleway (Apple Silicon M-series, macOS ARM)
- `[?]` `--laz-parallel 2 / 3 / 4` : débit réel. Dépend de combien de coeurs UNE
  conversion utilise, et macOS ARM peut threader autrement que mes mesures
  Windows (build CSF OpenMP différent).
