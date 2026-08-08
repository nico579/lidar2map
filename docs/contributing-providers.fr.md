*[English](contributing-providers.md) | **Français** · [Catalogue des fournisseurs](providers.fr.md) · [Index de la documentation](README.fr.md)*

# Contribuer un provider LiDAR

lidar2map isole la logique propre aux sources nationales et régionales dans
`providers/`. Un provider découvre les données sources d'une emprise et fournit
des entrées GeoTIFF normalisées au pipeline commun ; le calcul des reliefs, la
reprojection EPSG:3857, le tuilage et les formats de sortie restent
indépendants du provider.

Ce guide décrit le contrat d'intégration. Il ne répète volontairement pas le
[catalogue utilisateur](providers.fr.md). La
[roadmap des providers](lidar_providers_roadmap.md) consigne les sources déjà
évaluées, y compris les candidates rejetées ou différées.

## 1. Critères d'éligibilité

Une source s'intègre directement lorsqu'un endpoint programmable fournit :

- soit des altitudes sol-nu sous forme de GeoTIFF, COG, ASC ou autre raster
  convertible de façon fiable ;
- soit un nuage LAZ/LAS classé sol, convertible en modèle de terrain.

Les modes de découverte et d'accès déjà pris en charge comprennent :

- les URL de tuiles déterministes ;
- WCS `GetCoverage` par emprise ;
- les catalogues STAC ;
- les COG ou VRT mosaïques lisibles par fenêtre ;
- les index ATOM, WFS, ArcGIS FeatureServer ou de stockage objet ;
- les exports altimétriques ArcGIS ImageServer ;
- les tuiles LAZ, LAS, ZIP, XYZ ou ASC convertibles.

Le pipeline commun sait déjà convertir du LAZ classé en MNT, lire par fenêtre
de très grands COG, utiliser un listing objet comme index spatial, injecter une
authentification HTTP GDAL limitée à l'hôte et gérer les sources à compte ou clé
API gratuits.

### Cas bloquants

Lorsqu'une source ne peut pas être intégrée, consigner l'endpoint testé et une
raison précise :

- **B1 — aucun endpoint programmable :** panier interactif, formulaire ou
  livraison différée par e-mail seulement ;
- **B2 — image rendue seulement :** pixels WMS/WMTS/TPK sans altitude brute ;
- **B3 — donnée inadéquate :** simple bande côtière, trous rédhibitoires ou
  résolution nominale d'environ 10 m ou plus pour cet usage ;
- **B4 — accès ou licence incompatibles :** usage/redistribution restreints,
  indisponibilité depuis l'étranger ou procédure obligatoire non automatisable.

Un CRS absent ou douteux exige un traitement et une validation explicites ; il
ne doit jamais être deviné silencieusement.

Deux intégrations historiques sont des exceptions, pas des précédents :
`au-nsw` est un DEM stéréo-photogrammétrique 5 m conservé comme meilleure source
ouverte de l'État, et `us-3dep` possède un repli par défaut à 10 m alors que son
chemin haute résolution visé est `USGS1m`. Pour le 1 m public américain,
préférer `us-tnm`.

## 2. Partir du mécanisme d'accès le plus proche

Copier le provider fonctionnel le plus proche, puis adapter endpoint, CRS,
nommage et couverture :

| Mécanisme d'accès | Point de départ | Remarques |
|---|---|---|
| WCS 2.0 | `providers/es_cnig.py` ou `providers/de_hessen.py` | Grille synthétique limitée à la couverture ; `GetCoverage` par bbox |
| WCS 1.0 | `providers/es_euskadi.py` ou `providers/it_piemonte.py` | Ancien contrat BBOX/WIDTH/HEIGHT ; valider le type de pixel retourné |
| STAC + COG fenêtré | `providers/ca_nrcan.py` | Choisir l'asset altimétrique et ne lire que la fenêtre demandée via `/vsicurl/` |
| STAC/COG authentifié | `providers/se_lantmateriet.py` | Retourner les options limitées via `gdal_env_options()` ; ne jamais définir d'identifiants globaux |
| Index ATOM | `providers/de_thueringen.py` ou `providers/cz_cuzk.py` | Exemples grille/XYZ et LAZ à deux niveaux |
| ArcGIS ImageServer | `providers/no_kartverket.py` | `exportImage` par bbox ; reprojeter au téléchargement seulement si nécessaire |
| ArcGIS FeatureServer | `providers/ie_gsi.py` ou `providers/si_arso.py` | Index de features menant à des tuiles sources téléchargeables/convertibles |
| Listing de stockage objet | `providers/gb_scotland.py` ou `providers/lv_lgia.py` | Les clés objet ou en-têtes LAS donnent les emprises |
| Metalink | `providers/de_bayern.py` ou `providers/de_rlp.py` | Utiliser l'index lorsque le millésime ou l'URL réelle n'est pas déterministe |
| Grand COG/VRT unique | `providers/lu_act.py`, `providers/es_icgc.py` ou `providers/us_cnmi.py` | Lecture HTTP range fenêtrée ; ne jamais télécharger le fichier national complet |

Le premier provider d'un nouveau mécanisme peut demander nettement plus de
travail ; une fois le patron présent, une variante proche reste généralement un
petit module sans modification du cœur.

## 3. Contrat du module provider

Les codes provider utilisent des tirets (`no-kartverket`) ; les fichiers Python
utilisent des underscores (`providers/no_kartverket.py`). Les modules sont
découverts automatiquement dans `providers/*.py` : aucun registre central
n'est à modifier. Un utilitaire sans `CODE` est ignoré et les jumeaux
`*_laz.py` sont masqués de la liste GUI.

Un provider normal expose au minimum :

```python
NAME = "Nom lisible de la source"
CODE = "cc-source"
COUNTRY = "cc"
LICENSE = "Licence et attribution de la source"
DOC_URL = "https://source-officielle.example/"

CRS_NATIF = "EPSG:0000"
RESOLUTION_M = 1.0
DALLE_KM = 1
PX_PAR_DALLE = 1000
SEUIL_DALLE_VALIDE = 100_000

def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Retourne {nom_de_tuile_sûr: URL_ou_descripteur_source}."""
    ...
```

`discover_dalles` ne doit retourner que les sources recoupant l'emprise
demandée. Les noms de tuiles doivent être déterministes et sûrs comme noms de
fichiers locaux. Réutiliser les aides de `providers/common.py` au lieu de
dupliquer téléchargement, conversion ou logique spatiale.

Pour un nouveau pays, ajouter aussi son ordre d'affichage et ses noms
anglais/français à `providers.common.COUNTRY_INFO` afin que la GUI le groupe
correctement.

### Hooks optionnels

N'utiliser les hooks optionnels que pour le comportement propre à la source :

- `post_fetch` : décompresser ou convertir une entrée ZIP, LAZ, LAS, ASC ou XYZ
  vers le contrat GeoTIFF consommé en aval ;
- `pre_download` : préparer ou réutiliser une source locale dérivée avant le
  téléchargement normal ;
- `gdal_env_options()` : retourner des options HTTP GDAL limitées à l'hôte ;
- `set_apikey(key)` : accepter `--api-key` sans identifiant codé en dur ;
- `sign_url(url)` : signer un asset distant au moment du téléchargement ;
- `subdir_from_name` : répartir un grand cache sans modifier l'identité de la
  tuile.

Copier les signatures exactes depuis le provider actuel le plus proche : le
téléchargeur commun appelle les hooks de façon défensive et accepte plusieurs
types de descripteurs source.

## 4. Nuages classés et jumeaux DFM

Ajouter un jumeau `providers/<stem>_laz.py` uniquement si la source publie le
**nuage de points complet, dense et classé** via un endpoint reproductible. Un
MNT raster ou un nuage sol-seul ne peut pas restituer les structures debout déjà
retirées par le producteur.

Réutiliser `providers.common.LazProvider` pour les paramètres, le nommage de
cache injectif, la construction du socle par classes ou CSF, les gardes CRS et
les hooks de téléchargement/conversion. Le jumeau est sélectionné par `--laz`
sur son provider parent ; ce n'est pas une seconde entrée dans la liste GUI.

Densité, signification des classes, CRS, emprises de tuiles, authentification et
format d'archive doivent être validés séparément pour chaque source. Ne pas
supposer que les codes ASPRS/IGN sont portables ; choisir CSF par défaut lorsque
les classes producteur ne sont pas documentées de façon fiable.

## 5. Découvrir des services candidats

`tools/discover_providers.py` interroge un catalogue CSW INSPIRE pour les
services altimétriques et sonde les capacités WCS :

```bash
python tools/discover_providers.py de
python tools/discover_providers.py es
python tools/discover_providers.py <csw_url> "<mot-clé>" [dc|iso]
```

Le résultat est une présélection, pas une preuve de compatibilité. Les
catalogues nationaux peuvent manquer des services régionaux valides, et un
`DescribeCoverage` réussi ne prouve ni que la couche est un MNT plutôt qu'un
MNS, ni que `GetCoverage` retourne une donnée exploitable. Chercher ensuite
directement sur le site de l'agence cartographique nationale et les géoportails
régionaux.

## 6. Checklist de validation

Avant d'ouvrir une PR :

1. Vérifier licence officielle, attribution, couverture géographique,
   résolution nominale, CRS, unités, convention NoData et cycle de mise à jour.
2. Sonder le vrai endpoint et télécharger au moins une vraie tuile dans la
   couverture. Un catalogue ou un simple en-tête ne suffit pas.
3. Confirmer que les valeurs décodées sont des altitudes, pas une image rendue
   ou un modèle de surface étiqueté terrain par erreur.
4. Exécuter `discover_dalles` sur une petite bbox et vérifier noms
   déterministes sans collision et résultat spatialement borné.
5. Valider chaque conversion jusqu'à un GeoTIFF géoréférencé au CRS et à la
   résolution annoncés.
6. Exécuter un petit traitement lidar2map bout en bout : relief, reprojection et
   sortie tuilée.
7. Ajouter un point de smoke test dans la couverture à
   `Tests/smoke_providers.py`.
8. Régénérer `coverage.png`, `coverage.fr.png` et `coverage.geojson` avec
   `coverage_map.py` lorsque le catalogue géographique change.
9. Mettre à jour le [catalogue des providers](providers.fr.md), la section
   identifiants si nécessaire et les
   [crédits/licences des sources](data-licenses.fr.md).

Ne jamais committer un token privé, identifiant, mot de passe, URL signée ou
cookie de session temporaire. Même une clé publique fournie par la source
officielle doit être documentée explicitement, pas cachée dans un code sans
rapport.

## 7. Consigner les sources rejetées ou différées

Ne pas jeter les résultats d'investigation. Ajouter l'endpoint testé, la date,
le statut et le blocage précis à la
[roadmap des providers](lidar_providers_roadmap.md), avec sa convention
`WATCH`, `STABLE` ou `HARD` lorsque pertinente. Cela évite de recommencer la
même recherche de portail et permet une réévaluation fondée sur des faits.
