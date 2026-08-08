*[English](dfm.md) | **Français** · [Providers](providers.fr.md) · [Référence CLI LiDAR](../README.fr.md#31-lidar) · [Guide des visualisations](shadings.fr.md) · [Retour à la documentation principale](../README.fr.md#documentation)*

# Structures debout avec LAZ, DFM et CSF

Les modèles numériques de terrain nationaux sol-nu sont excellents pour les
terrassements, mais ils peuvent effacer précisément la structure recherchée
lorsqu'elle se dresse encore au-dessus du sol. Le mode nuage de points de
lidar2map reconstruit une surface depuis la source LAZ/LAS classée complète,
afin que les structures basses debout restent disponibles pour le LRM, le SVF,
l'ouverture, le VAT et tous les autres reliefs.

> **C'est un outil de génération de candidats, pas un classificateur de murs ou
> de vestiges.** Végétation, rochers, objets modernes et erreurs de
> classification peuvent revenir avec les murs. Garder la zone petite, comparer
> des couches indépendantes et valider les interprétations sur le terrain
> lorsque les règles d'accès et de protection du patrimoine le permettent.

## Pourquoi un MNT sol-nu peut perdre une ruine

Les producteurs nationaux classent volontairement un modèle de terrain comme
**sol nu**. Dans le LiDAR HD IGN, les retours sol/eau/sol virtuel forment le
socle, tandis qu'un mur encore debout au-delà d'environ 1 m est couramment
rangé en végétation ou « non classé ». Le MNT officiel interpole alors dans le
trou obtenu. Une fois le mur retiré de ce raster, aucun hillshade ni autre
visualisation calculée depuis le MNT ne peut le restaurer.

Il faut donc distinguer :

- talus, fossés, restanques et murs très effondrés, qui restent souvent dans le
  MNT officiel et se prospectent mieux avec le workflow lidar2map normal ;
- murs sans toiture et autres structures basses debout, qui peuvent exiger le
  nuage complet et un **Digital Feature Model** (DFM) reconstruit.

Le concept DFM — terrain et structures archéologiques debout dans un même
modèle — vient de
[Štular et al. (2021)](https://doi.org/10.3390/rs13091855). La sélection
automatique par classes et tranche de hauteur de lidar2map est une heuristique
propre au projet, calibrée sur deux sites du Var. Le workflow publié emploie une
reclassification plus délibérée, souvent semi-manuelle. Il faut donc lire cette
implémentation comme une aide à la prospection, pas comme la reproduction exacte
de la méthode publiée.

## Activer le mode nuage de points

Dans la GUI, choisir un provider qui expose un mode nuage de points et activer
le **mode DFM** à côté. En CLI, sélectionner le provider parent normal puis
ajouter `--laz` :

```bash
python lidar2map.py \
  --lidar --provider fr-ign --laz --download \
  --zone-gps <lat>,<lon> --zone-width 1 --zone-name site \
  --shadings lrm svf --file-formats mbtiles
```

Tous les reliefs demandés sont alors calculés depuis la surface reconstruite du
nuage, à la place du MNT officiel. Le DFM change la **surface d'entrée** ; LRM,
SVF, VAT et les autres sorties gardent leur sens normal. Consulter le
[guide des visualisations](shadings.fr.md) pour choisir comment rendre le
résultat.

Commencer par une petite zone autour d'une structure connue ou suspectée. Un
traitement de nuage à l'échelle d'un département ou d'une région est rarement
un premier essai raisonnable.

<p align="center">
  <img src="../screenshots/GUI/lidar_laz_classes.PNG" alt="Formulaire DFM utilisant les classes producteur" width="440">
  <img src="../screenshots/GUI/lidar_laz_csf.PNG" alt="Formulaire DFM utilisant le Cloth Simulation Filter" width="440">
</p>

*La GUI présente séparément les socles par classes et par CSF tout en gardant
les mêmes sorties LiDAR.*

## Deux méthodes de reconstruction

lidar2map expose deux méthodes de socle sous le même mode `--laz`. Les noms de
sortie les distinguent par `laz_dfm` (réinjection de classes) et `laz_csf`
(filtre tissu).

### Réinjection par classes

Choisir `--laz-ground classes`. C'est le défaut sur l'IGN.

Le pipeline :

1. agrège les classes terrain sélectionnées par valeur z minimale pour former
   un socle ;
2. comble temporairement ce socle pour estimer la hauteur de chaque point
   au-dessus du sol ;
3. sélectionne les points non-sol bas dans la tranche `hmin`–`hmax` ;
4. réinjecte ces points **uniquement dans les cellules où le socle terrain
   présente un trou** ;
5. effectue une interpolation finale bornée à 200 m et écrit le GeoTIFF DFM.

Pour `fr-ign`, les classes sélectionnées par défaut sont `1,2,3,4,9,66`. Les
classes `2,9,66` forment le socle terrain ; `1,3,4` sont candidates à la
réinjection entre 0,4 et 2,5 m au-dessus de lui.

Cette méthode est rapide et conserve la connaissance du producteur, mais son
résultat dépend de la signification locale des classes. Un seul retour sol dans
la cellule d'un mur conserve le sol et empêche le mur d'y être réinjecté. Le
maquis dense peut aussi revenir en mouchetis. Si un mur paraît incomplet,
vérifier d'abord le schéma de classes du provider ; sur l'IGN, la classe 5 peut
être testée explicitement lorsque des murs ont été rangés en végétation haute.

### Cloth Simulation Filter

Choisir `--laz-ground csf`. La plupart des providers nuage hors IGN le prennent
par défaut, car leurs classes producteur sont hétérogènes ou insuffisamment
documentées.

Le [Cloth Simulation Filter](https://www.cloudcompare.org/doc/wiki/index.php/CSF_(plugin))
inverse le nuage et y drape un tissu virtuel. lidar2map choisit volontairement
un tissu souple afin que les structures basses continues puissent être absorbées
dans la surface reconstruite tandis que la canopée est rejetée. Un préfiltre
indépendant des classes garde d'abord les points situés à moins de 3,5 m du
minimum local sur une grille 5 m ; il conservait environ 57 % des points sur les
nuages de calibration.

Sur les deux sites du Var, CSF a gardé un signal de murs équivalent avec un fond
plus propre que la réinjection par classes. Il est beaucoup plus lent, reste
sensible au terrain et à la densité, et ne constitue pas un classificateur de
murs.

`hmin`, `hmax` et `classes` sont ignorés en mode CSF. Inversement, les réglages
`csf-*` sont ignorés en mode classes ; lidar2map signale ces deux incohérences.

| Choix | Bon point de départ | Coût ou risque principal |
|---|---|---|
| `classes` | Classes producteur bien documentées, réglage rapide, IGN | Mouchetis et murs manqués lorsqu'un retour sol occupe déjà la cellule |
| `csf` | Classes hétérogènes, fond plus propre, majorité des providers internationaux | Plusieurs minutes par dalle, ~3 Go de RAM par conversion, sensibilité aux paramètres |

## Paramètres

Les défauts peuvent varier selon le provider et sont affichés par la GUI. Les
valeurs ci-dessous sont les défauts communs ; `fr-ign` utilise `classes` par
défaut, tandis que la majorité des autres providers nuage utilisent `csf`.

| Option CLI | Défaut commun | S'applique à | Effet |
|---|---:|---|---|
| `--laz` | désactivé | les deux | Passe du MNT officiel au nuage classé du provider |
| `--laz-ground classes\|csf` | selon provider | les deux | Choisit réinjection par classes ou reconstruction par tissu |
| `--laz-hmin M` | 0,4 m | classes | Hauteur minimale du candidat au-dessus du sol de référence |
| `--laz-hmax M` | 2,5 m | classes | Hauteur maximale du candidat au-dessus du sol de référence |
| `--laz-classes LIST` | selon provider | classes | Classes LAS terrain et candidates, séparées par des virgules |
| `--laz-csf-threshold M` | 0,5 m | CSF | Distance point-tissu maximale absorbée comme sol ; l'augmenter peut retenir davantage de murs dégradés **et** de maquis |
| `--laz-csf-resolution M` | 0,5 m | CSF | Maille du tissu ; plage valide 0,1–3,0 m |
| `--laz-csf-rigidness N` | 1 | CSF | `1` pentu/souple, `2` intermédiaire, `3` plat/rigide ; `3` se rapproche du sol nu et peut effacer les murs debout |
| `--laz-parallel N` | 1 | conversion | Conversions LAZ simultanées ; prévoir environ 3 Go de RAM par conversion |

Le seuil et la maille du tissu acceptent 0,1–3,0 m. Le pas de temps, le nombre
d'itérations et le préfiltre de canopée restent volontairement fixes : ce sont
des contrôles d'implémentation, pas des paramètres interprétables du site.

Comportements avancés du mode classes :

- retirer la classe 2 produit une sortie de type coupe, contenant seulement les
  objets de la tranche sur fond transparent ; les hauteurs restent référencées
  au sol de classe 2 ;
- ne sélectionner aucune classe à réinjecter produit approximativement un MNT
  reconstruit.

Ce sont des configurations de diagnostic, pas des premiers essais recommandés.

## Temps, stockage, RAM et cache

Les coûts dépendent de la densité, du format d'archive, de l'accès serveur, du
CPU et de la méthode. Les mesures suivantes donnent des ordres de grandeur, pas
des garanties :

| Source/exemple | Téléchargement ou densité | Classes | CSF | Remarque mémoire |
|---|---|---:|---:|---|
| LiDAR HD IGN, France | ~205 Mo/km², COPC dense | ~20–25 s/dalle | ~3–4 min/dalle | Pic ~2,9–3 Go sur une dalle d'environ 45 M de points |
| swissSURFACE3D | ~125 Mo/km² | selon provider | environ 6 min/dalle | Garder une emprise ciblée |
| DHM/Punktsky Danemark | ~82 Mo et ~12 M de points/km² | ~19 s/dalle | ~6,4 min/dalle | Un tissu plus dense est plus lent |
| Échantillon COPC NRCan | ~40 points/m² | selon provider | selon provider | 1 km² peut représenter ~1 Go de LAS temporaire et ~3 Go de RAM |

Ces temps ont été mesurés sur des machines et jeux de données précis. Sur une
machine 4 cœurs, plusieurs conversions simultanées n'ont pas apporté de gain
utile : une conversion CSF emploie déjà plusieurs cœurs. N'augmenter
`--laz-parallel` que sur une grosse VM ayant à la fois des cœurs libres et
environ `N × 3 Go` de RAM disponible.

### Comportement du cache

- Le nuage LAZ/LAS téléchargé reste dans le cache de tuiles.
- Le GeoTIFF DFM/CSF dérivé vit dans la production.
- Un même nuage est partagé entre essais de classes, tranches de hauteur et CSF.
- Les réglages non par défaut sont encodés dans les noms des dalles et projets
  dérivés, ce qui empêche le mélange silencieux entre MNT, DFM par classes et
  CSF.
- Un réajustement reconstruit depuis le nuage caché sans nouveau téléchargement.
- N'utiliser `--download-overwrite` que si la source elle-même doit être
  retéléchargée.

Les conversions sont écrites atomiquement via un fichier temporaire : une
conversion interrompue n'est pas acceptée plus tard comme GeoTIFF complet. Les
dépendances (`laspy`, `lazrs` et CSF lorsqu'il est demandé) sont vérifiées avant
un téléchargement lourd et installées à la demande dans l'environnement Python
géré ; les bundles autonomes les embarquent déjà.

## Portée multi-provider

Le mode DFM exige le **nuage de points complet, dense et classé**. Un raster
sol-nu ou un nuage sol-seul a déjà perdu les structures debout et ne peut pas le
supporter. Les implémentations actuelles sont résumées ci-dessous ; le
[catalogue des providers](providers.fr.md) reste la référence pour
disponibilité, identifiants, couverture et tailles de source.

| Provider parent | Particularités du nuage | Défaut | État de validation ou réserve |
|---|---|---|---|
| `fr-ign` | COPC IGN, ~205 Mo/km² | classes | Méthodes classes et CSF contrôlées sur le terrain sur deux sites du Var |
| `ch-swisstopo` | swissSURFACE3D `.las.zip`, ~125 Mo/km² | CSF | Conversion bout en bout ; validation terrain conseillée |
| `pl-gugik` | ~28 points/m², CRS PL-2000 variable selon le fuseau | CSF | Validé bout en bout |
| `ee-maaamet` | ~4 points/m² dans le nuage standard testé | CSF | Techniquement valide mais marginal pour une grille 0,5 m ; validation terrain en attente |
| `be-flanders` | ~11 points/m², nuage classé OpenLidar | CSF | Validé bout en bout |
| `ca-nrcan` | COPC distant lu en fenêtre, jusqu'à ~40 points/m² dans le test | CSF | Seule la bbox demandée est lue ; les fenêtres denses restent lourdes en RAM |
| `ca-quebec` | LAZ direct, ~10 points/m² dans le test, plusieurs fuseaux MTM | CSF | Validé bout en bout, couverture par projet |
| `us-3dep` | COPC Planetary Computer lu en fenêtre ; ~5 points/m² dans le levé ancien testé, souvent davantage sur les projets récents | CSF | Aucun compte pour le LAZ, couverture par projet |
| `dk-datafordeler` | ~12 points/m², clé API requise | CSF | Validé bout en bout ; CSF mesuré à environ 6,4 min/dalle |
| `fr-craig` | Campagnes régionales très denses, jusqu'à ~60 points/m² dans le test | CSF | Campagnes régionales nommées, pas une couverture France mur-à-mur |

« Validé bout en bout » signifie que découverte, téléchargement, gestion du
CRS, conversion et sortie GeoTIFF ont été exercés. Cela ne signifie **pas** que
le rappel archéologique et le taux de faux positifs ont été validés sur le
terrain dans le pays.

## Comparatif visuel

Cette ruine de maison sans toiture dans le Var a des murs d'environ 1,5 m sous
le maquis. L'orthophoto les laisse à peine deviner. Le LRM classique du MNT
officiel montre les restanques voisines mais pas la ruine. Les deux méthodes
nuage font réapparaître l'emprise rectangulaire ; CSF donne le fond le plus
propre.

| Orthophoto | LRM classique depuis le MNT |
|---|---|
| ![Orthophoto, murs cachés sous le maquis](../screenshots/LIDAR_Samples/Ruins/ortho.jpg) | ![LRM depuis le MNT sol-nu, ruine invisible](../screenshots/LIDAR_Samples/Ruins/lrm.jpg) |
| Murs noyés dans la végétation | Les restanques ressortent, pas la ruine |
| **DFM-LRM : réinjection par classes** | **DFM-LRM : socle tissu CSF** |
| ![DFM par réinjection de classes, murs visibles avec mouchetis](../screenshots/LIDAR_Samples/Ruins/dfm_lrm.jpg) | ![DFM avec socle tissu CSF, fond plus propre](../screenshots/LIDAR_Samples/Ruins/csf_lrm.jpg) |
| Le rectangle du bâtiment réapparaît, avec mouchetis | Mêmes murs, fond plus propre |

## Interprétation et validation terrain

Ne jamais interpréter le DFM seul. Une pile de lecture pratique comprend :

1. LRM du MNT officiel ou autre visualisation sol-nu familière ;
2. LRM DFM par classes et/ou CSF à la même échelle ;
3. delta DFM moins MNT lorsqu'il est disponible ;
4. orthophotos actuelles et historiques ;
5. SVF, ouverture, pente ou autre visualisation indépendante ;
6. observation terrain lorsqu'elle est légale et sûre.

Donner plus de poids aux lignes continues, angles, géométries répétées et
accords entre vues indépendantes qu'aux points clairs ou sombres isolés. Le
maquis apparaît souvent en mouchetis ; rochers, escarpements, restanques, traces
forestières, bâtiments et débris modernes peuvent imiter des formes
archéologiques.

Limites connues :

- la réinjection par classes peut manquer un mur lorsqu'un seul retour sol
  occupe sa cellule ;
- CSF peut conserver la végétation ou effacer des murs, surtout avec un seuil
  inadapté ou `rigidness=3` ;
- un nuage peu dense peut ne pas échantillonner une maçonnerie étroite assez
  finement pour une sortie 0,5 m ;
- la sortie intégrée ne fournit pas encore de masques
  mesuré/interpolé, densité, confiance ou réinjection ;
- l'interpolation peut franchir jusqu'à 200 m de lacune : une forme lisse n'est
  pas la preuve d'une mesure directe ;
- l'agrégation par hauteur minimale reste sensible à un retour anormalement bas
  qui ne serait pas marqué bruit/withheld ; une variante par quantile bas
  robuste attend encore une calibration terrain ;
- le tissu n'a pas encore de halo inter-dalles ; inspecter les candidats aux
  limites des tuiles ;
- CSF utilise OpenMP et n'est pas garanti bit-identique entre exécutions.
  Valider le raster final et l'interprétation, pas les listes brutes d'indices
  CSF ;
- millésime, schéma de classes et densité varient entre providers, parfois au
  sein d'un même provider.

Éviter de lancer plusieurs processus distincts sur la même zone et le même
cache de nuages : les fichiers dérivés sont atomiques, mais le verrou de
conversion LAZ inter-processus n'est pas encore implémenté.

Le pipeline refuse automatiquement les combinaisons CRS/unités incompatibles
lorsqu'elles sont résolubles, filtre les classes de bruit ASPRS 7/18 et les
points withheld avant l'agrégation min-z, et emploie les emprises nominales des
tuiles lorsqu'elles existent afin de réduire les coutures. Si un ZIP contient
plusieurs nuages de façon inattendue, il avertit et ne garde actuellement que le
plus gros.

La validation terrain reste décisive. L'heuristique actuelle doit encore être
éprouvée de façon adverse sur des ruines connues et des zones négatives avec
rochers, falaises, restanques et maquis, y compris des structures traversant
plusieurs tuiles sources. Ne pas publier les coordonnées précises de vestiges
sensibles, creuser ou utiliser la sortie pour contourner les règles
archéologiques et d'accès aux terrains.

## Outil autonome de comparaison QGIS

Pour une comparaison ciblée **IGN France** hors du pipeline principal,
[`tools/dfm_ruines.py`](../tools/dfm_ruines.py) télécharge le COPC LAZ,
reconstruit par classes et écrit trois GeoTIFF géoréférencés EPSG:2154 :

- `<prefix>_lrm_mnt.tif` — LRM du MNT sol-seul reconstruit ;
- `<prefix>_lrm_dfm.tif` — LRM du DFM, avec candidats debout et maquis ;
- `<prefix>_delta.tif` — DFM moins MNT en mètres.

```bash
python tools/dfm_ruines.py \
  --center <lon>,<lat> --rayon 150 --out site

python tools/dfm_ruines.py \
  --bbox <ouest>,<sud>,<est>,<nord> --out zone --cache laz_cache
```

Les défauts de l'outil autonome sont : sortie 0,5 m, tranche 0,4–2,5 m,
classes candidates `1,3,4`, sigma LRM 7,5 m et cache `./laz_cache`. La classe 6
peut être ajoutée pour un test ciblé de bâti. Ce script n'exécute pas CSF.

Dans QGIS, un premier comparatif utile consiste à afficher
`*_lrm_dfm.tif` en niveaux de gris autour de −0,5 à +0,5 m sur l'orthophoto,
puis à seuiller `*_delta.tif` autour de 0,4–1 m pour inspecter les candidats.
Adapter ces limites d'affichage au site et toujours comparer à
`*_lrm_mnt.tif`. Les lignes et rectangles sont des candidats ; le mouchetis est
souvent du maquis.

Une tuile IGN pèse environ 205 Mo/km² : l'outil reste destiné à l'inspection de
quelques km². Il utilise `laspy`/`lazrs`, rasterio, SciPy, NumPy et pyproj ;
l'environnement géré de lidar2map fournit déjà ces dépendances.

## Documentation liée

- [Providers LiDAR, couverture, identifiants et sources compatibles DFM](providers.fr.md)
- [Référence CLI LiDAR](../README.fr.md#31-lidar)
- [Choisir et comprendre les visualisations de relief](shadings.fr.md)
- [Journal des revues d'ingénierie LAZ/DFM/CSF](dfm_reviews.md), conservé
  comme historique de décisions plutôt que comme guide utilisateur
