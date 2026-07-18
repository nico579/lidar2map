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
- `[x]` Deps laspy/CSF vérifiées AVANT le download (`DfmProvider.discover_dalles`).
- `[x]` Warn si un ZIP contient plusieurs nuages (au lieu du drop silencieux).
- `[x]` Provider CRAIG validé bout-en-bout et intégré (`fr-craig` + `fr-craig-dfm`).

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
- `[x]` **`--dfm-parallel N`** : sémaphore réglable + `OMP_NUM_THREADS=coeurs/N`
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

## A mesurer sur la VM Scaleway (Apple Silicon M-series, macOS ARM)
- `[?]` `--dfm-parallel 2 / 3 / 4` : débit réel. Dépend de combien de coeurs UNE
  conversion utilise, et macOS ARM peut threader autrement que mes mesures
  Windows (build CSF OpenMP différent).
