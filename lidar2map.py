# lidar2map.py — Prospection LiDAR archéologique & cartes offline pour Locus Map / OsmAnd
# Copyright (C) 2025 Nicolas Martin
#
# Ce logiciel a été conçu, architecturé et dirigé par Nicolas Martin.
# Le code source a été développé avec l'assistance de Claude (Anthropic),
# utilisé comme outil de développement.
#
# Licence : GNU General Public License v3.0
# https://www.gnu.org/licenses/gpl-3.0.html
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou
# le modifier selon les termes de la GNU GPL telle que publiée par la
# Free Software Foundation (version 3 ou toute version ultérieure).
#
# Ce programme est distribué dans l'espoir qu'il sera utile, mais SANS
# AUCUNE GARANTIE, sans même la garantie implicite de COMMERCIALISATION
# ou d'ADÉQUATION À UN USAGE PARTICULIER.
#
"""
lidar2map.py — Prospection archéologique LiDAR & cartes offline
======================================================================

Script unifié multi-modes pour Locus Map / OsmAnd / TwoNav.
Plateformes : Windows 10+, macOS 11+, Linux (Debian/Ubuntu testés).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONCEPT ET WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Les types de cartes sont INDÉPENDANTS et complémentaires. Dans le GUI, ce
  sont les onglets LiDAR, Raster, Vectoriel, Fusion vectorielle (plus un onglet
  utilitaire Découpage raster).

  ① LiDAR       Fond principal d'analyse archéologique. On commence par
                 ici : téléchargement des dalles (surface MNT, ou nuage de
                 points LAZ en mode LAZ « structures debout »), calcul des
                 ombrages (multi-directionnel, SVF, LRM, RRIM…), export en
                 MBTiles. Multi-provider / multi-pays (fr-ign HD préselectionné
                 dans le GUI ; --provider explicite en CLI). On expérimente
                 les manques.

  ② Raster      Fond alternatif ou de recalage (Scan 25, orthophotos,
                 NAIP US…). Peut remplacer le LiDAR quand les données
                 manquent, ou servir de fond de référence topographique.
                 Se superpose aux overlays vectoriels.

  ③ Vectoriel   Overlay de précision. Deux sources au choix :
                 IGN (cadastre, hydrographie, chemins… en WFS) ou
                 OSM (routes, cours d'eau, patrimoine… en Mapsforge/GeoJSON).
                 Superposition sur n'importe quel fond raster.
                 En CLI, deux modes distincts : --ignvecteur et --osm.

  ④ Fusion vectorielle
                 Outil utilitaire : fusionne plusieurs GeoJSON (IGN + OSM)
                 en un seul overlay unifié avec traçabilité de la source.

  Flux typique :
    1. Générer le LiDAR → charger dans Locus
    2. Selon les besoins : ajouter overlay Vectoriel (IGN et/ou OSM)
    3. Si couverture LiDAR insuffisante : générer Raster (Scan 25/Ortho)
    4. Fusionner les GeoJSON si besoin d'un overlay unique combiné

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --ignlidar      Dalles LiDAR → ombrages → MBTiles/RMAP/SQLiteDB
                    (--provider obligatoire en CLI ; fr-ign préselectionné au GUI)
  --ignraster     Tuiles WMTS raster (Scan 25, Ortho, NAIP US…) → MBTiles/RMAP/SQLiteDB
  --ignvecteur    WFS IGN (cadastre, hydrographie…) → GeoJSON(.gz)
  --osm           PBF Geofabrik → carte Mapsforge (.map) + GeoJSON(.gz)
  --fusionner     Fusion de GeoJSON/GeoJSON.gz en un seul fichier
  --serve         Sert les livrables d'un projet sur le WiFi (URL + QR)
                  pour import direct sur le téléphone (OsmAnd/Locus)

  Sans argument   → GUI pywebview (interface HTML/JS)

  Pré-flags globaux (lus AVANT argparse, tel un préfixe de commande :
  ils sélectionnent la source ou le pipeline, puis sont retirés de argv) :
--provider CODE   Source LiDAR/raster (obligatoire avec --lidar). 27 pays câblés :
                        fr-ign, ch-swisstopo, nl-ahn, us-3dep, no-kartverket…
                        Liste vivante = un fichier par source dans providers/.
    --laz             Mode LAZ « structures debout » (voir MODE --ignlidar).
                        Bascule vers le jumeau <provider>-laz.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ZONE GÉOGRAPHIQUE (commune à tous les modes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --zone-ville NOM            Géocodage Nominatim (ex: gareoult)
  --zone-gps   LAT,LON        Coordonnées WGS84  (ex: 43.3156,6.0423)
  --zone-bbox  W,S,E,N        BBox WGS84 en degrés
  --zone-departement NUM      Département français (ex: 83)
  --zone-region SLUG          Région Geofabrik, ex: provence-alpes-cote-d-azur
                                (emprise = bbox de ses départements ; avec
                                 --osm : une seule carte régionale, PBF complet)
  --zone-largeur KM           Largeur (côté du carré) de la zone autour du
                                point, en km (défaut: 20)
  --zone-nom   NOM            Nom du dossier de sortie (ex: aa)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FORMATS DE SORTIE (communs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --formats-fichier FMT...    Formats de fichiers de sortie (multi-valeurs) :
                                ignlidar/ignraster : mbtiles rmap sqlitedb
                                osm                : map geojson gz transparent-raster
                                ignvecteur/fusion  : geojson gz transparent-raster
                              transparent-raster = tuiles PNG à fond transparent
                                (.sqlitedb) rasterisant le vecteur (OSM ou IGN),
                                pour superposition dans OsmAnd par-dessus le LiDAR
  --formats-image   FMT       Format des images dans les tuiles (ignlidar/ignraster) :
                                auto (défaut) | jpeg | png
  --qualite-image   Q         Qualité JPEG des images (1-100, défaut: 85)
                                75 = -35% taille, quasi invisible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignlidar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Pipeline (décrit pour le défaut fr-ign ; les autres providers varient sur
  l'étape 1, via STAC ou tuiles LAZ, et sur le CRS natif, mais la suite est commune) :
    1. Dalles LiDAR (fr-ign : HD par WMS ; cache permanent dans --dossier-dalles)
       → dalles_zone.txt (liste bbox-versionnée, reconstruite si zone change)
    2. rasterio.merge → mosaïque globale des dalles (CRS natif du provider, ex. EPSG:2154, < 1 s)
    3. numpy/scipy → TIF ombrages (étape "ombrage")
       → <nom>_multi_ombrage.tif, <nom>_slope_ombrage.tif…
    4. rasterio.warp + build_overviews + tuilage Pillow → MBTiles/RMAP/SQLiteDB
       → <nom>_multi_ombrage_tuilage_z18.tif (cache Mercator, réutilisable)
       → <nom>_multi_ombrage_z13-18.mbtiles   (plage --zoom-min/--zoom-max ;
       → <nom>_multi_ombrage_z13-18.rmap       z18 ≈ 0,43 m/px en métropole,
       → <nom>_multi_ombrage_z13-18.sqlitedb   plus fin que la native 0,5 m
                                               → z19 n'apporte rien)
       ATTENTION au facteur latitude : une tuile Web Mercator fait
       156543,03·cos(φ)/2^z m/px. Le 156543,03/2^z qu'on lit partout est la
       valeur À L'ÉQUATEUR (z18 = 0,597 m/px) ; sans le cos(φ) on conclut à
       tort que z18 est trop grossier pour du 0,5 m et qu'il faut z19. En
       métropole cos(43-49°) ≈ 0,70 et z18 passe à ~0,42-0,44 m/px.
       Zoom natif = ceil(log2(156543,03·cos(φ)/résolution)) : 0,25 m → z19,
       0,5 m → z18, 1 m → z17, 2 m → z16, 5 m → z15.

  Paramètres spécifiques :
    --telechargement            Télécharger les dalles manquantes
    --telechargement-forcer     Re-télécharger même les dalles existantes
    --no-telechargement-compresser  Désactiver la compression DEFLATE du cache
                                (active par défaut : ~2× moins de disque)
    --dossier-dalles CHEMIN     Cache dalles séparé (défaut: ign_lidar/dalles/)
    --workers N                 Connexions parallèles (défaut: 8)
    --laz                       Mode LAZ « structures debout » (pré-flag global,
                                  comme --provider) : bascule vers le jumeau
                                  <provider>-laz (France : nuage LAZ ~205 Mo/km²,
                                  révèle les murs que le MNT efface, zone petite).
                                  Le nom de projet est suffixé (laz_dfm / laz_csf
                                  selon le socle) : MNT et LAZ ne se mélangent jamais.
    --laz-hmin M / --laz-hmax M Tranche de hauteur réintroduite (déf. 0,4–2,5 m)
    --laz-classes 1,2,3,4,9,66  Classes LAS participantes (déf. 1,2,3,4,9,66).
                                  2/9/66 = socle terrain (2 obligatoire) ; les
                                  autres sont réinjectées dans les trous du sol
                                  (tranche hmin-hmax). Essayer 1,2,3,4,5,9,66
                                  si les murs sortent incomplets.
    --laz-ground classes|csf    Socle terrain (mode LAZ) (déf. classes) :
                                  csf = Cloth Simulation Filter (Zhang 2016),
                                  ignore les classes du producteur, fond plus
                                  propre, ~3 min/dalle (hmin/hmax/classes
                                  alors ignorés — le tissu fait le tri).
    --laz-csf-threshold M       Seuil d'absorption point-tissu (déf. 0,5 m) :
                                  monter = murs plus dégradés absorbés (et
                                  plus de maquis), baisser = plus strict.
    --laz-csf-resolution M      Maille du tissu (déf. 0,5 m).
    --laz-csf-rigidness 1|2|3   Type de terrain (Zhang) : 1 pentu (déf.),
                                  2 relief doux, 3 plat (proche bare-earth,
                                  efface les murs — pas pour les ruines).
    --laz-parallel N            Conversions CSF/DFM simultanées (déf. 1).
                                  Chaque conversion pique ~3 Go de RAM, donc
                                  N>1 exige la RAM (N×3 Go) et les cœurs. Pour
                                  une VM multi-cœurs ; laisser 1 sur 8 Go.
    --ombrages TYPE...          Shadings to generate (ordre d'utilité) :
                                  lrm vat e4mstp svf opos oneg rrim
                                  multi 315 045 135 225 slope | tous | aucun
                                  LRM = Local Relief Model (ici SLRM, Simple LRM)
                                  VAT = Visualization for Archaeological Topography
                                  SVF = Sky-View Factor ; RRIM = Red Relief Image Map
                                  e4MSTP = Multiscale Topographic Position,
                                  enhanced version 4 (variante lidar2map)
                                  (opos/oneg = openness ± Yokoyama 2002,
                                   rayon --svf-dist, gamma --svf-gamma)
    --shading TYPE[:k=v,...]    Instance d'ombrage PARAMÉTRÉE, répétable —
                                  permet plusieurs instances du même type :
                                  --shading svf:dist=20 --shading svf:dist=100
                                  --shading oneg:gamma=1.5 --shading lrm:sigma=10
                                  Params : elevation (directionnels/multi),
                                  conv/dist/gamma/sweep (svf),
                                  dist/gamma/sweep (opos/oneg),
                                  dist/gamma (vat/e4mstp),
                                  sigma en m (lrm/rrim). Dans e4mstp, dist ne
                                  règle que SVF/O+/O− et gamma vaut 0,8 par
                                  défaut. Plusieurs instances coexistent tant
                                  que leurs noms de sortie normalisés diffèrent.
    --shading-preset auto|micro|standard|landscape
                                Stack d'ombrages calibré sur la RÉSOLUTION
                                  (opt-in, params en mètres) : svf + opos + lrm
                                  dimensionnés pour le MNT, plus multi + slope.
                                  'auto' choisit micro (≤0,75 m), standard
                                  (>0,75 à ≤2,5 m), sinon landscape.
    --svf-conv flux|rvt         Convention SVF (flux cos²γ / rvt 1−sin γ ; déf. flux)
    --svf-dist M                Rayon d'horizon SVF/openness/composites en mètres,
                                  plage GUI 10–200 (déf. 20)
    --svf-sweep / --no-svf-sweep  Kernel sweep-horizon SVF (déf. activé)
    --ombrages-elevation DEG    Angle solaire en degrés (défaut: 25)
    --svf-gamma G               Gamma SVF/O+/O−/VAT (déf. 2.0 ; O− en miroir).
                                  e4mstp garde son gamma final propre (déf. 0,8).
    --ombrages-compresser       Compresser les TIF ombrages existants (DEFLATE)
    --ombrages-ecraser          Recalculer les ombrages même s'ils existent
    --tuiles-ecraser            Réécrire les tuiles / MBTiles / .map existants
    --index-map / --no-index-map  Planche d'index <nom>_planche.png à côté des
                                  livrables (emprise + contour départemental +
                                  cellules numérotées si découpage). Défaut: activé.
                                  Sur un projet existant : --index-sheet DOSSIER
                                  (alias --planche).
    --zoom-min N                Zoom minimum MBTiles (défaut: 13 — inclut z8-12 via --zoom-min 8)
    --zoom-max N                Zoom maximum MBTiles (défaut: 18)
    --cols-decoupe N            Découpe le MBTiles final en N colonnes (avec --rows-decoupe)
    --rows-decoupe N            Découpe le MBTiles final en N lignes   (avec --cols-decoupe)
    --split-largeur KM          Alternative : découpe en carrés de ~KM km de côté
    --source CHEMIN             Source alternative :
                                  .tif   → ombrage existant → tuilage direct
                                  .mbtiles → conversion → RMAP/SQLiteDB
    --osm                       Générer overlay OSM vectoriel (standalone ou après LiDAR)

  Maintenance du cache de dalles (lancer SANS --telechargement) :
    --dalles-purger-invalides   Supprimer les dalles < 2 Mo (mer, erreurs partielles)
    --dalles-purger-hors-zone   Supprimer du cache les dalles hors zone courante
                                  (libère la place prise par d'autres départements)

  Arborescence de sortie :
    Projets/<nom>/
      ign_lidar/
        dalles_zone.txt             liste dalles (# bbox:x1,y1,x2,y2 en tête)
        manifeste.json              état de reprise (découpage à priori)
        <nom>_multi_ombrage.tif     ombrage CRS natif du provider, 0.5 m/px
        <nom>_multi_ombrage_tuilage_z18.tif  cache Mercator (réutilisable)
        <nom>_multi_ombrage_z13-18.mbtiles
        <nom>_multi_ombrage_z13-18.rmap
        <nom>_multi_ombrage_z13-18.sqlitedb
    <cache>/lidar/<pays>/           cache dalles permanent, partagé entre projets :
                                     .tif MNT (download) + nuage .laz du mode LAZ
                                     (<cache> = cache/ sous le dossier de travail
                                      par défaut, déplaçable par --cache-dir)
    <production>/lidar/<pays>/       mode LAZ : le .tif est un PRODUIT (calculé
                                     du nuage avec tes réglages) → il descend ici,
                                     hors du cache (déplaçable par --production-dir).
                                     Le nuage .laz, lui, reste au cache ci-dessus.

  Temps indicatifs (zone 4 km², i3-8130U) :
    Téléchargement (9-12 dalles)       : ~30 s
    Ombrage multi (numpy)              : ~5-10 s
    Ombrage SVF (numpy, 4 km²)         : ~5 min
    Ombrage LRM (scipy)                : ~2 min
    Ombrage RRIM (slope + LRM)         : ~8 min
    MBTiles z13-18 (495 tuiles)        : ~5 s
    MBTiles z13-18 (zone 400 km²)      : ~5-10 min

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignraster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Télécharge des tuiles WMTS dans un MBTiles.
  Sortie dans Projets/<nom>/raster/. Cache permanent : <cache>/ign_raster/<z>/<x>/<y>.<ext>
  (<cache> = cache/ sous le dossier de travail par défaut, déplaçable par --cache-dir).

  Couches disponibles (catalogue fr-ign ci-dessous ; un autre --provider expose
  ses propres couches, ex. us-tnm → naip) :
    planign     Plan IGN v2 (png, public, z6-18)              ← recommandé particuliers
    etatmajor40 État-Major 1/40000 (jpeg, public, z6-15)
    etatmajor10 État-Major 1/10000 (jpeg, public, z8-16)
    pentes      Carte des pentes (png, public, z6-14)
    ortho       Orthophotos actuelles (jpeg, public, z10-20)
    ortho_1950  Orthos historiques 1950-1965 (png, z10-18)    ← archéo, exploration
    ortho_1965  Orthos historiques 1965-1980 (png, z10-18)
    ortho_1980  Orthos historiques 1980-1995 (png, z10-18)
    ortho_irc   Orthos infrarouge couleur (jpeg, z10-19)      ← végétation, humidité sol
    pleiades    Satellite Pléiades 50cm 2024 (jpeg, z10-19)
    spot        Satellite SPOT 1.5m 2024 (jpeg, z8-16)
    cadastre    Parcellaire express (png, public, z12-19)
    ombrage     Ombrage IGN (png, public, z6-14)
    edugeo_marseille_*  Orthos historiques Marseille-Martigues
                  (1969, 1980, 1987, 1988, 2010 — emprise urbaine restreinte)
    edugeo_toulon_1972  Ortho historique Toulon-Hyères 1972 (emprise urbaine)
    scan25      Scan 25 000 (jpeg, z8-18)    ⚠ PRO — clé API requise
    scan25tour  Scan 25 Tourisme (jpeg, z8-18) ⚠ PRO — clé API requise
    scan100     Scan 100 000 (jpeg, z6-14)   ⚠ PRO — clé API requise
    scanoaci    Scan OACI (jpeg, z6-15)       ⚠ PRO — clé API requise

  Note : scan25 au-delà de z16 → IGN bascule automatiquement vers planIGN.
  Note : orthos historiques — couverture variable selon département/période.
    Pour la PACA : 1950-1965 et 1965-1980 généralement disponibles, mais
    tester d'abord sur petite zone. Si la couche est vide à votre date sur
    votre département, le téléchargement renverra des tuiles transparentes.
  ⚠ Les couches Scan sont réservées aux professionnels (CGU IGN).
    Compte sur cartes.gouv.fr avec SIRET requis. Les particuliers doivent
    utiliser planign ou ortho, accessibles sans clé.

  Paramètres spécifiques :
    --couche NOM        Couche WMTS (défaut: scan25)
    --apikey CLE        Clé API IGN — réservée aux professionnels (scan* uniquement)
                          Vide par défaut. Variable d'env IGN_APIKEY aussi acceptée.
    --zoom-min N        Zoom minimum (défaut: selon couche)
    --zoom-max N        Zoom maximum (défaut: selon couche)
    --workers N         Connexions parallèles (défaut: 8)
    --cols-decoupe N    Découpe le MBTiles final en N colonnes (avec --rows-decoupe)
    --rows-decoupe N    Découpe le MBTiles final en N lignes   (avec --cols-decoupe)
    --split-largeur KM  Alternative : découpe en carrés de ~KM km de côté
    --source CHEMIN     .mbtiles existant → conversion RMAP/SQLiteDB directe

  Arborescence de sortie :
    Projets/<nom>/
      raster/
        <nom>_scan25_z8-18.mbtiles
        <nom>_scan25_z8-18.rmap
        <nom>_scan25_z8-18.sqlitedb
    <cache>/ign_raster/             cache tuiles WMTS permanent, partagé (--cache-dir)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignvecteur
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Télécharge des couches WFS IGN vers GeoJSON(.gz).

  Couches disponibles :
    cadastre          Parcelles cadastrales
    cours_eau         Cours d'eau (hydrographie)
    detail_hydro      Hydrographie détaillée
    bati              Bâtiments (BDTOPO)
    voie_ferre        Voies ferrées
    (typename complet accepté directement)

  Paramètres :
    --couche NOM...     Couche(s) à télécharger (multi-valeurs)
    --workers N         Connexions parallèles (défaut: 4)
    --formats-fichier   geojson | gz | transparent-raster (défaut: gz)

  Arborescence de sortie :
    ign_vecteur/
      <nom>/
        <nom>_cadastre.geojson.gz
        <nom>_cours_eau.geojson.gz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --osm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  PBF Geofabrik → carte Mapsforge (.map) + GeoJSON de superposition.
  Utilise osmosis + plugin mapwriter (téléchargés automatiquement).
  Le PBF filtré <nom>_filtered.pbf est conservé pour la réutilisation.

  Paramètres :
    --source CHEMIN     PBF source (téléchargé depuis Geofabrik si absent)
    --couche TAGS       Tags OSM inclus (défaut: rando)
                          ex: "highway=* waterway=* natural=water"
    --formats-fichier   map geojson gz transparent-raster (défaut: map gz)

  Arborescence de sortie :
    osm_vecteur/
      provence-alpes-cote-d-azur-latest.osm.pbf   (cache régional)
      <nom>/
        <nom>.map                  carte Mapsforge
        <nom>_filtered.pbf         PBF filtré (réutilisable)
        <nom>_osm.geojson.gz       GeoJSON de superposition
        <nom>_osm_transparent.sqlitedb  overlay raster transparent (OsmAnd)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --fusionner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Fusionne plusieurs GeoJSON(.gz) en un seul fichier.
  Ajoute la propriété 'source' = nom du fichier source.

  Paramètres :
    --source FICHIER...   Fichiers GeoJSON/.gz à fusionner (glob accepté)
    --sortie FICHIER      Fichier de sortie (défaut: dossier du 1er fichier)
    --formats-fichier     geojson | gz (défaut: gz)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PARAMÈTRES COMMUNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --dossier CHEMIN      Racine de sortie (défaut: Projets/<nom>/)
  --dossier-cache CHEMIN  Racine de TOUS les caches persistants : dalles, tuiles
                          WMTS, PBF OSM, index de découverte (alias --cache-dir).
                          Défaut : cache/ sous le dossier de travail. Permet de
                          poser cache et sorties sur des disques différents.
  --dossier-production CHEMIN  Racine des artefacts CALCULÉS mais partagés entre
                          projets (alias --production-dir). Aujourd'hui = le .tif
                          du mode LAZ, produit du nuage avec tes réglages (le
                          .tif MNT, lui, vient du serveur → reste au cache ; le
                          nuage .laz aussi). Défaut : production/ sous le dossier
                          de travail. LiDAR uniquement.
  --nettoyage           Supprimer les fichiers intermédiaires après chaque
                          morceau (dalles, TIF ombrages, TIF warpé).
                          Conserve les sorties finales (.mbtiles .rmap .sqlitedb).
                          Indispensable pour les grandes zones (département entier).
  --version             Afficher la version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GUI (mode interactif sans arguments)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Lancer sans argument : python lidar2map.py
  Onglets : LiDAR, Raster, Vectoriel, Fusion vectorielle, Découpage raster.

  Structure commune aux onglets :
    • Zone géographique : sélecteur de PAYS (issu des providers) qui limite
      l'autocomplétion des villes ; puis ville / GPS / bbox / département / région.
    • Bloc « Source des données » : provider + surface MNT ou LAZ (LiDAR),
      couche (Raster), source IGN/OSM (Vectoriel).
    • Cadres numérotés : Télécharger → Découpage à priori → Générer la carte,
      chacun avec sa case d'activation.
    • Masquages selon le pays : l'onglet Raster disparaît si le pays n'a pas
      de données raster ; la source IGN se cache dans Vectoriel hors France.

  Fonctionnalités :
    • Bouton Aide (❓) : affiche cette documentation (source UNIQUE = ce docstring)
    • Historique : 50 dernières commandes, rappel par clic, vidable
    • Partage LAN (📲) : QR + URL pour import direct sur le téléphone
    • Zoom interface : Ctrl+molette (Windows/macOS), Ctrl++/Ctrl+-
    • Annulation : 1er Ctrl+C demande l'arrêt propre, 2nd force la sortie
    • Logs en temps réel + erreurs en boîte de dialogue à la fin
    • Validation des paramètres : zoom_min ≤ zoom_max, etc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DÉCOUPAGE À PRIORI (--ignlidar et --ignraster uniquement)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Modes raster uniquement. Les modes vectoriels (--ignvecteur, --osm,
  --fusionner) n'en ont pas besoin : leurs données sont légères et ne
  saturent pas la RAM ni le disque.

  Principe : traitement séquentiel morceau par morceau avec reprise
  automatique. Un fichier manifeste.json enregistre l'état de chaque
  morceau. En cas d'interruption, relancer la même commande reprend
  exactement là où le traitement s'est arrêté.

  --cols-decoupe N      Colonnes de la grille (Est-Ouest)
  --rows-decoupe N      Lignes de la grille (Nord-Sud)
                          Ce même paramètre sert à la fois au découpage
                          à priori (traitement séquentiel par morceaux)
                          et au découpage des fichiers de sortie.
  --nettoyage           Supprimer dalles + TIF intermédiaires après chaque
                          morceau. Indispensable pour les grandes zones
                          (département entier).
  --cleanup-keep-tiles  Avec --nettoyage : garder les dalles dans le cache
                          partagé, ne purger que les autres intermédiaires.
                          Utile quand une tâche +file suivante les réutilise.
  --min-disque-go GO    Arrêt propre avant un morceau si l'espace libre passe
                          sous GO (0 = désactivé). À régler au-dessus du pic
                          disque d'un morceau.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DÉPENDANCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Python 3.8+    Python 3.12+ recommandé pour les patches sécurité tarfile.
                 Dépendances pip auto-installées au 1er lancement :
                   Pillow, pyproj, numpy, scipy, ijson, certifi
                 Optionnelles (auto-installées à la demande) :
                   numba (accélération SVF ~15×), py7zr (BD TOPO bulk),
                   mapbox-vector-tile (lecture vector tiles)

  GDAL           Plus de dépendance GDAL système requise depuis le refactor
                 rasterio (étapes 1-7). Tous les outils (gdalinfo, gdalwarp,
                 gdaldem, gdalbuildvrt, gdal_translate, gdaladdo, ogr2ogr)
                 sont remplacés par rasterio.warp / rasterio.merge / numpy /
                 fiona, dont les wheels pip embarquent leur propre libgdal.
                 → Plus aucun `brew install gdal` ni GISInternals à télécharger.

  osmosis        Téléchargé dans ~/.lidar2map/osmosis/ (toutes plateformes)
                 Partagé entre tous les dossiers où le script est lancé.
  JRE Temurin 21 Téléchargé dans ~/.lidar2map/jre/
                   Windows x64 : zip   |   macOS x64/arm64 : tar.gz
                   Linux x64/arm64 : tar.gz
                 Pour nettoyer complètement le runtime : rm -rf ~/.lidar2map
  mapwriter      Téléchargé automatiquement (plugin osmosis)

  GUI (mode sans arguments) :
                 Windows : PyQt6 + PyQt6-WebEngine + qtpy (auto-installés)
                 macOS   : PyQt6 + PyQt6-WebEngine + qtpy, plus les backends
                           natifs Cocoa/WebKit (auto-installés)
                 Linux   : PyQt6 + PyQt6-WebEngine + qtpy (auto-installés via pip)
                           Pré-requis système (Ubuntu/Debian, une seule fois) :
                             sudo apt install python3-venv
                           voir messages au démarrage si import échoue)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXEMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Mode GUI
  python lidar2map.py

  # LiDAR : zone 2 km, ombrage multi, MBTiles + RMAP + SQLiteDB
  python lidar2map.py --ignlidar --provider fr-ign --zone-ville gareoult --zone-width 2 \
      --zone-nom aa --telechargement --ombrages multi \
      --formats-fichier mbtiles rmap sqlitedb --zoom-min 8 --zoom-max 18

  # LiDAR : zone 20 km, plusieurs ombrages
  python lidar2map.py --ignlidar --provider fr-ign --zone-ville gareoult --zone-width 20 \
      --zone-nom gareoult --telechargement --ombrages multi slope svf lrm \
      --formats-fichier mbtiles rmap --qualite-image 75

  # LiDAR : depuis TIF existant → RMAP uniquement
  python lidar2map.py --ignlidar --provider fr-ign --zone-ville gareoult --zone-width 2 \
      --zone-nom aa --source ign_lidar/aa/_warped_aa_multi_ombrage_z18.tif \
      --formats-fichier rmap --zoom-min 8 --zoom-max 18

  # IGN Raster public (pas de clé requise)
  python lidar2map.py --ignraster --zone-ville gareoult --zone-width 20 \
      --zone-nom aa --couche planign \
      --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18

  # IGN Raster Scan 25 (professionnel uniquement — clé API requise)
  # python lidar2map.py --ignraster --zone-ville gareoult --zone-width 20 \
  #     --zone-nom aa --couche scan25 --apikey VOTRE_CLE_PRO \
  #     --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18

  # Vecteur IGN : cadastre + hydrographie
  python lidar2map.py --ignvecteur --zone-ville gareoult --zone-width 10 \
      --zone-nom aa --couche cadastre cours_eau detail_hydro

  # OSM : carte rando + GeoJSON
  python lidar2map.py --osm --zone-ville gareoult --zone-width 20 \
      --zone-nom aa --couche "highway=* waterway=* natural=water" \
      --formats-fichier map gz

  # Fusion GeoJSON
  python lidar2map.py --fusionner \
      --source ign_vecteur/aa/*.geojson.gz osm_vecteur/aa/*.geojson.gz \
      --formats-fichier gz

  # Zone par département entier (Var)
  python lidar2map.py --ignlidar --provider fr-ign --zone-departement 83 \
      --telechargement --workers 8 --ombrages multi --formats-fichier mbtiles

  # A-priori splitting: grande zone en 4×4 morceaux avec nettoyage disque
  python lidar2map.py --ignlidar --provider fr-ign --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage

  # Reprise après interruption (même commande — les morceaux terminés sont ignorés)
  python lidar2map.py --ignlidar --provider fr-ign --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage

  # Linux/macOS : la commande est identique, sauf 'python' → 'python3'
  python3 lidar2map.py --ignlidar --provider fr-ign --zone-ville Gareoult --zone-width 2 \
      --ombrages svf --formats-fichier mbtiles
"""
import os
import uuid
import re
import sys
import ssl
from pathlib import Path

# ``spec_from_file_location`` n'ajoute pas le dossier du script à sys.path.
# Le TLS est configuré avant le launcher et avant le bootstrap des dépendances :
# rendre les modules privés importables dès ce point préserve aussi ce scénario.
_MODULE_DIR = str(Path(__file__).resolve().parent)
while _MODULE_DIR in sys.path:
    sys.path.remove(_MODULE_DIR)
sys.path.insert(0, _MODULE_DIR)

import _bootstrap_tls as _bootstrap_tls_impl
import _bootstrap_runtime as _bootstrap_runtime_impl

_SSL_CTX_CERTIFI = _bootstrap_tls_impl.initialiser_tls(
    environnement=os.environ,
    module_ssl=ssl,
)


def _restaurer_tls_strict():
    global _SSL_CTX_CERTIFI
    _SSL_CTX_CERTIFI = _bootstrap_tls_impl.restaurer_tls_strict(
        environnement=os.environ,
        module_ssl=ssl,
    )


_restaurer_tls_strict.__doc__ = _bootstrap_tls_impl.restaurer_tls_strict.__doc__


# Forcer stdout/stderr en UTF-8 dès le démarrage. Sur Windows la code page
# console est cp1252 par défaut ; sans cette reconfigure, les caractères
# accentués et symboles (é, ✓, →) sont écrits en cp1252 et apparaissent en
# mojibake quand la sortie est capturée par un pipe parent qui décode en UTF-8
# (cas du mode frozen GUI → CLI subprocess). PYTHONIOENCODING=utf-8 ne suffit
# pas toujours dans un exe PyInstaller. Doit s'exécuter AVANT le premier print.
for _std in ("stdout", "stderr"):
    _s = getattr(sys, _std, None)
    if _s is not None and getattr(_s, "encoding", "").lower() != "utf-8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

# ─────────────────────────────────────────────────────────────────────────────
# MODE LAUNCHER (build onefile)
# ─────────────────────────────────────────────────────────────────────────────
# Le même lidar2map.py est buildé en DEUX versions :
#   1) onedir (lidar2map_win.spec)        : la vraie app, ~617 MB, lente à packager
#      mais rapide à lancer. C'est ce qui tourne au final.
#   2) onefile (lidar2map_win_launcher.spec) : un petit launcher qui contient le onedir
#      zippé en ressource. À l'exécution il extrait dans %LOCALAPPDATA%\lidar2map
#      (avec contrôle SHA pour détecter les mises à jour), puis spawn le vrai exe
#      onedir avec une sentinelle pour qu'il saute ce bloc.
#
# Le launcher se distingue à l'exécution :
#   - PyInstaller onefile : sys._MEIPASS contient lidar2map_bundle.zip
#   - L'inner spawné a la sentinelle _INNER_FLAG dans sys.argv
_INNER_FLAG = "--__lidar2map_inner__"
if getattr(sys, "frozen", False):
    if _INNER_FLAG in sys.argv:
        # On est l'exe interne : retirer la sentinelle puis continuer normalement
        sys.argv.remove(_INNER_FLAG)
    else:
        # On est peut-être le launcher : vérifier la présence du bundle
        import hashlib, zipfile, platform as _platform
        from pathlib import Path as _Path

        # Ordre de recherche du bundle :
        #   1. À côté de l'exe / dans Contents/Resources/ (bundle fichier séparé)
        #   2. Dans sys._MEIPASS (bundle embarqué, fallback ancienne archi)
        _exe = _Path(sys.executable).resolve()
        _sys = _platform.system()   # une seule détection, réutilisée partout

        if _sys == "Darwin" and ".app" in str(_exe):
            _bundle = _exe.parent.parent / "Resources" / "lidar2map_bundle.zip"
        else:
            _bundle = _exe.parent / "lidar2map_bundle.zip"

        # Fallback _MEIPASS — uniquement si non vide (Path("") = cwd, ambigu)
        if not _bundle.exists():
            _meipass_str = getattr(sys, "_MEIPASS", None)
            if _meipass_str:
                _bundle = _Path(_meipass_str) / "lidar2map_bundle.zip"

        if _bundle.exists():
            # Dossier d'extraction : chemins système standard par OS.
            if _sys == "Windows":
                _app_dir   = _Path(os.environ.get("LOCALAPPDATA",
                                str(_Path.home() / "AppData" / "Local"))) / "lidar2map"
                _inner_exe = _app_dir / "lidar2map.exe"
            elif _sys == "Darwin":
                _app_dir   = _Path.home() / "Library" / "Application Support" / "lidar2map"
                _inner_exe = _app_dir / "lidar2map"
            else:
                _app_dir   = _Path.home() / ".local" / "share" / "lidar2map"
                _inner_exe = _app_dir / "lidar2map"
            _sha_file = _app_dir / ".bundle_sha"
            _lock     = _app_dir.parent / ".lidar2map_extracting"

            # ── --desinstaller intercepté dans le launcher ────────────────────
            # Traité ici AVANT tout calcul de SHA ou extraction.
            # Le launcher supprime tout directement (venv, osmosis, jre, bundle
            # extrait) sans re-spawner — évite l'infinite loop.
            if "--desinstaller" in sys.argv:
                _ok_u = _bootstrap_runtime_impl.desinstaller_lidar2map(
                    systeme=_sys,
                    home=_Path.home(),
                    localappdata=os.environ.get("LOCALAPPDATA"),
                )
                sys.exit(0 if _ok_u else 1)

            def _bundle_sha():
                h = hashlib.sha256()
                with open(_bundle, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                return h.hexdigest()

            # ── Détection de mise à jour avec cache mtime ─────────────────────
            # Calculer le SHA256 d'un zip de 300 MB prend ~0.5-1 s à chaque
            # lancement. On stocke le mtime du bundle dans le fichier SHA pour
            # éviter ce calcul quand le bundle n'a pas changé.
            # Format de _sha_file : "sha256hex\nmtime_float"
            _need_extract = True
            if _sha_file.exists() and _inner_exe.exists() and not _inner_exe.is_dir():
                try:
                    _sha_lines     = _sha_file.read_text(encoding="utf-8").strip().split("\n")
                    _saved_sha     = _sha_lines[0]
                    _saved_mtime   = float(_sha_lines[1]) if len(_sha_lines) > 1 else 0.0
                    _current_mtime = _bundle.stat().st_mtime
                    if abs(_current_mtime - _saved_mtime) < 0.01:
                        # mtime identique → bundle inchangé → pas d'extraction
                        _need_extract = False
                    else:
                        # mtime changé → vérifier SHA pour confirmer
                        _expected_sha = _bundle_sha()
                        _need_extract = (_expected_sha != _saved_sha)
                except Exception:
                    _need_extract = True   # sha_file corrompu → ré-extraire

            if _need_extract:
                _expected_sha = _bundle_sha()   # calcul SHA si pas encore fait

            # Détection robuste : si le zip a été créé avec --keepParent,
            # l'extraction crée un sous-dossier lidar2map/ → l'exe est un niveau
            # plus bas. On corrige automatiquement.
            def _resolve_exe(exe):
                if exe.exists() and exe.is_dir():
                    deeper = exe / exe.name
                    if deeper.exists() and not deeper.is_dir():
                        return deeper
                return exe

            if _need_extract:
                # Lockfile contre les extractions simultanées (double-clic).
                # Prise de verrou ATOMIQUE via os.open(O_CREAT|O_EXCL) : une
                # seule instance peut créer le fichier ; les autres reçoivent
                # FileExistsError et basculent en attente. Remplace l'ancien
                # check-then-act (exists() puis touch()) où deux double-clics
                # voyaient tous deux « pas de lock », le créaient chacun, puis
                # extrayaient en parallèle (course TOCTOU).
                # Durci contre les locks ORPHELINS : si le lock est plus vieux
                # que _LOCK_STALE_S (instance tuée/plantée pendant l'extraction),
                # on le considère périmé et on le retire au lieu d'attendre 60 s
                # puis d'échouer. L'extraction du bundle prend ~30-60 s -> 300 s
                # est une borne haute sûre (pas de faux positif en cas de double-clic).
                import time as _time
                _LOCK_STALE_S = 300
                _app_dir.parent.mkdir(parents=True, exist_ok=True)

                def _prendre_lock():
                    # True si on crée le verrou (on extrait), False s'il existe
                    # déjà (une autre instance l'a pris avant nous).
                    try:
                        _fd = os.open(str(_lock),
                                      os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.close(_fd)
                        return True
                    except FileExistsError:
                        return False

                _lock_pris = _prendre_lock()
                if not _lock_pris:
                    # Verrou déjà présent : périmé (instance morte) ? Si oui,
                    # nettoyer puis retenter la prise atomique une fois.
                    _stale = False
                    try:
                        _stale = (_time.time() - _lock.stat().st_mtime) >= _LOCK_STALE_S
                    except Exception:
                        _stale = True
                    if _stale:
                        print("  Stale lockfile detected - cleaning up and resuming.", flush=True)
                        _lock.unlink(missing_ok=True)
                        _lock_pris = _prendre_lock()
                if not _lock_pris:
                    print("Installation in progress in another instance - waiting...",
                          flush=True)
                    for _ in range(60):
                        _time.sleep(1)
                        if not _lock.exists():
                            break
                    # Re-vérifier que l'autre instance a bien terminé : un
                    # crash mid-extraction laisserait un _inner_exe absent ou
                    # un _sha_file manquant. Si l'état n'est pas sain, on
                    # abandonne plutôt que de spawner un binaire incomplet.
                    _inner_check = _resolve_exe(_inner_exe)
                    if _inner_check.exists() and _sha_file.exists():
                        _need_extract = False
                    else:
                        print("  ⚠ Concurrent install incomplete or failed.",
                              flush=True)
                        print("  Remove the lockfile and relaunch:",
                              flush=True)
                        print(f"    {_lock}", flush=True)
                        sys.exit(1)
                else:
                    try:
                        if _app_dir.exists():
                            import shutil as _sh
                            _sh.rmtree(_app_dir, ignore_errors=True)
                        _app_dir.mkdir(parents=True, exist_ok=True)
                        _bundle_size = _bundle.stat().st_size
                        print(f"First launch - installation ({_bundle_size // 1_000_000} MB)...",
                              flush=True)
                        # Suivi : ditto sur Mac préserve les permissions
                        # exécutables, mais zipfile.extractall (utilisé par le
                        # fallback Darwin et le chemin Linux) les perd → on
                        # remet le bit +x sur l'exe après extraction si on est
                        # passé par zipfile.
                        _used_zipfile = False
                        if _sys == "Darwin":
                            import subprocess as _sp_d
                            _r = _sp_d.run(["ditto", "-x", "-k",
                                            str(_bundle), str(_app_dir)],
                                           capture_output=True)
                            if _r.returncode != 0:
                                # Fallback zipfile si ditto échoue : validation
                                # défensive contre zip-slip (le bundle est
                                # notre artefact, mais on défend par principe).
                                with zipfile.ZipFile(_bundle) as _z:
                                    _t = _Path(_app_dir).resolve()
                                    for _mem in _z.infolist():
                                        if _mem.filename.startswith(("/", "\\")) \
                                                or ":" in _mem.filename[:3]:
                                            raise ValueError(
                                                f"Bundle suspect : {_mem.filename!r}")
                                        _d = (_t / _mem.filename).resolve()
                                        if _d != _t and _t not in _d.parents:
                                            raise ValueError(
                                                f"Bundle suspect : {_mem.filename!r}")
                                    _z.extractall(_app_dir)
                                _used_zipfile = True
                            _sp_d.run(["xattr", "-dr", "com.apple.quarantine",
                                       str(_app_dir)], capture_output=True)
                        else:
                            # Extraction avec compteur de progression.
                            # Validation défensive contre zip-slip.
                            with zipfile.ZipFile(_bundle) as _z:
                                _members = _z.infolist()
                                _n = len(_members)
                                _t = _Path(_app_dir).resolve()
                                for _mem in _members:
                                    if _mem.filename.startswith(("/", "\\")) \
                                            or ":" in _mem.filename[:3]:
                                        raise ValueError(
                                            f"Bundle suspect : {_mem.filename!r}")
                                    _d = (_t / _mem.filename).resolve()
                                    if _d != _t and _t not in _d.parents:
                                        raise ValueError(
                                            f"Bundle suspect : {_mem.filename!r}")
                                for _i, _m in enumerate(_members, 1):
                                    _z.extract(_m, _app_dir)
                                    # zipfile ne restaure PAS les permissions
                                    # POSIX. zip -r (Unix) les stocke dans
                                    # external_attr (16 bits hauts). On les
                                    # réapplique → préserve +x sur tous les
                                    # binaires bundlés (QtWebEngineProcess,
                                    # JRE java, osmosis, …).
                                    _mode = (_m.external_attr >> 16) & 0xFFFF
                                    if _mode and _sys != "Windows":
                                        try:
                                            (_Path(_app_dir) / _m.filename).chmod(_mode & 0o777)
                                        except Exception:
                                            pass
                                    if _i % max(1, _n // 20) == 0:
                                        print(f"  {_i * 100 // _n}%",
                                              end="\r", flush=True)
                            print("  100%", flush=True)
                            _used_zipfile = True

                        # Filet de sécurité : si le zip a été créé sans
                        # permissions POSIX (external_attr == 0, ex: Windows),
                        # forcer au moins +x sur l'exe interne pour qu'il
                        # puisse être spawné.
                        if _used_zipfile and _sys != "Windows":
                            import stat as _stat
                            _inner_exe_resolved = _resolve_exe(_inner_exe)
                            if _inner_exe_resolved.exists():
                                _inner_exe_resolved.chmod(
                                    _inner_exe_resolved.stat().st_mode
                                    | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)

                        # Vérifier que l'exe interne existe avant d'écrire le SHA
                        # (ditto peut retourner 0 avec une extraction incomplète)
                        _inner_resolved = _resolve_exe(_inner_exe)
                        if not _inner_resolved.exists():
                            raise RuntimeError(
                                f"Extraction incomplète : {_inner_exe} not found")

                        _sha_part = _sha_file.with_name(
                            f"{_sha_file.name}.{os.getpid()}."
                            f"{uuid.uuid4().hex[:12]}.part"
                        )
                        try:
                            _sha_part.write_text(
                                f"{_expected_sha}\n{_bundle.stat().st_mtime}",
                                encoding="utf-8")
                            os.replace(_sha_part, _sha_file)
                        finally:
                            _sha_part.unlink(missing_ok=True)
                        print("Installation complete.", flush=True)
                    except Exception as _e_extract:
                        print(f"\n  ⚠ Erreur d'extraction : {_e_extract}", flush=True)
                        print("  Restart the application to try again.", flush=True)
                        sys.exit(1)
                    finally:
                        _lock.unlink(missing_ok=True)

            # Résoudre le vrai chemin de l'exe (gère --keepParent)
            _inner_exe = _resolve_exe(_inner_exe)

            # ── LIDAR2MAP_WORK_DIR : dossier contenant le .app/.exe ───────────
            # Sur macOS, sys.executable est dans .app/Contents/MacOS/ →
            # remonter jusqu'au dossier parent du .app pour que les fichiers
            # utilisateur (Projets/, logs/, cache/) soient créés à côté du .app.
            if _sys == "Darwin" and ".app" in str(_exe):
                _work_dir = _exe.parent.parent.parent.parent
            else:
                _work_dir = _exe.parent

            # Spawn l'exe interne avec la sentinelle et les args utilisateur.
            import subprocess as _sp
            _env = os.environ.copy()
            _env["LIDAR2MAP_WORK_DIR"] = str(_work_dir)
            _rc = _sp.call([str(_inner_exe), _INNER_FLAG] + sys.argv[1:], env=_env)
            sys.exit(_rc)
        # Pas de bundle.zip → exe onedir lancé directement → continuer.

# ─────────────────────────────────────────────────────────────────────────────
# EXÉCUTION DISTANTE (rlidar2map_CLI / rlidar2map_GUI) — dispatch précoce
# ─────────────────────────────────────────────────────────────────────────────
# --remote-cli / --remote-gui délèguent immédiatement aux outils
# d'orchestration SSH/RDP, avant le bootstrap (venv) et les imports lourds :
# ce sont des scripts stdlib pur, sans dépendance vers le pipeline LiDAR.
# Arguments propres à chaque mode : voir tools/README_rlidar2map.md.


def _import_patchable_source_module(package_name, module_name):
    """Charge explicitement une ressource Python patchable depuis le disque.

    Les specs PyInstaller embarquent aussi ces modules dans le PYZ pour que
    leurs dépendances soient détectées au build. Un import normal peut donc
    préférer cette copie compilée à `_internal/<package>/*.py`, précisément le
    fichier que `update_app.py` remplace. Le chargeur explicite garantit que
    les outils distants et providers livrés par un patch sont ceux exécutés.
    En mode source, il conserve la même sémantique et facilite le test.
    """
    import importlib as _runtime_importlib
    import importlib.util as _runtime_importlib_util
    from pathlib import Path as _RuntimePath

    root = _RuntimePath(__file__).resolve().parent
    package_dir = root / package_name
    module_path = package_dir / f"{module_name}.py"
    if not module_path.is_file():
        return _runtime_importlib.import_module(
            f"{package_name}.{module_name}"
        )

    def _load(full_name, path, package_paths=None):
        current = sys.modules.get(full_name)
        try:
            current_path = _RuntimePath(getattr(current, "__file__", "")).resolve()
        except (OSError, TypeError, ValueError):
            current_path = None
        if current is not None and current_path == path.resolve():
            return current

        spec = _runtime_importlib_util.spec_from_file_location(
            full_name,
            path,
            submodule_search_locations=package_paths,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load patchable module {full_name} from {path}")
        previous = sys.modules.get(full_name)
        module = _runtime_importlib_util.module_from_spec(spec)
        sys.modules[full_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            if previous is None:
                sys.modules.pop(full_name, None)
            else:
                sys.modules[full_name] = previous
            raise
        return module

    package_init = package_dir / "__init__.py"
    if package_init.is_file():
        _load(package_name, package_init, [str(package_dir)])

    # Tous les providers qui mutualisent réseau/cache importent common. Le
    # précharger explicitement empêche leur source fraîche de retomber sur un
    # ancien providers.common compilé dans le PYZ.
    if package_name == "providers" and module_name != "common":
        common_path = package_dir / "common.py"
        if common_path.is_file():
            _load("providers.common", common_path)

    return _load(f"{package_name}.{module_name}", module_path)


if len(sys.argv) > 1 and sys.argv[1] in ("--remote-cli", "--remote-gui"):
    os.environ["LIDAR2MAP_REMOTE_MODE"] = "1"
    _remote_argv = sys.argv[2:]
    if sys.argv[1] == "--remote-cli":
        _remote_tool = _import_patchable_source_module(
            "tools", "rlidar2map_CLI")
        sys.exit(_remote_tool.main(_remote_argv))
    else:
        _remote_tool = _import_patchable_source_module(
            "tools", "rlidar2map_GUI")
        _relaunch = [sys.executable]
        if not getattr(sys, "frozen", False):
            _relaunch.append(__file__)
        _relaunch.append("--remote-gui")
        sys.exit(_remote_tool.cli_main(_remote_argv, relaunch=_relaunch))

import queue
import shutil
import argparse
import threading
import json
import gzip
import sqlite3
import math
import time
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

import _bootstrap_policy as _bootstrap_policy_impl
from _bootstrap_policy import dependances_gui_plateforme as _dependances_gui_plateforme
import _smoketest as _smoketest_impl
import _logging_helpers as _logging_helpers_impl
import _tee_logger as _tee_logger_impl
import _log_activation as _log_activation_impl
import _atomic_files as _atomic_files_impl
import _http_helpers as _http_helpers_impl
import _runtime_paths as _runtime_paths_impl
import _disk_guard as _disk_guard_impl

# Vérification version Python
# Python 3.9 minimum RÉEL : argparse.BooleanOptionalAction (utilisé par
# --download-compress / --index-map) n'existe qu'à partir de 3.9. L'ancien
# garde annonçait 3.8 alors que le parser plantait à la construction sous 3.8.
if sys.version_info < (3, 9):
    print("ERROR: Python 3.9 minimum required (current version: "
          + str(sys.version_info.major) + "." + str(sys.version_info.minor) + ")")
    print("Download Python 3.9+ from https://www.python.org/downloads/")
    sys.exit(1)

# ============================================================
# INSTALLATION AUTOMATIQUE DES DÉPENDANCES
# ============================================================

def _resoudre_mode_bootstrap():
    """Détermine le mode de bootstrap et nettoie ``sys.argv`` en place."""
    try:
        resolution = _bootstrap_policy_impl.resoudre_mode_bootstrap(
            sys.argv,
            os.environ,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    if resolution.aide:
        print(_bootstrap_venv_si_besoin.__doc__)
        sys.exit(0)
    sys.argv[:] = resolution.argv
    return resolution.mode


def _gui_deps_plateforme():
    """Façade historique relisant la plateforme à chaque appel."""
    return _dependances_gui_plateforme(platform.system())


def _verifier_venv_linux():
    return _bootstrap_runtime_impl.verifier_venv_linux()


_verifier_venv_linux.__doc__ = _bootstrap_runtime_impl.verifier_venv_linux.__doc__


def _bootstrap_venv_si_besoin():
    return _bootstrap_runtime_impl.bootstrap_venv_si_besoin(
        resoudre_mode=_resoudre_mode_bootstrap,
        gui_deps_plateforme=_gui_deps_plateforme,
        verifier_venv_linux=_verifier_venv_linux,
        relancer_dans_venv=_relancer_dans_venv,
    )


_bootstrap_venv_si_besoin.__doc__ = (
    _bootstrap_runtime_impl.bootstrap_venv_si_besoin.__doc__
)


def _relancer_dans_venv(venv_python, is_windows):
    return _bootstrap_runtime_impl.relancer_dans_venv(
        venv_python,
        is_windows,
    )


_relancer_dans_venv.__doc__ = _bootstrap_runtime_impl.relancer_dans_venv.__doc__


def _bootstrap_pip():
    return _bootstrap_runtime_impl.bootstrap_pip()


_bootstrap_pip.__doc__ = _bootstrap_runtime_impl.bootstrap_pip.__doc__


def _installer_deps():
    return _bootstrap_runtime_impl.installer_deps(
        gui_deps_plateforme=_gui_deps_plateforme,
    )


_installer_deps.__doc__ = _bootstrap_runtime_impl.installer_deps.__doc__


def _bootstrap_environnement():
    return _bootstrap_runtime_impl.orchestrer_bootstrap(
        frozen=getattr(sys, "frozen", False),
        resoudre_mode=_resoudre_mode_bootstrap,
        bootstrap_venv_avec_mode=_bootstrap_venv_si_besoin_avec_mode,
        bootstrap_pip=_bootstrap_pip,
        installer_dependances=_installer_deps,
        restaurer_tls_strict=_restaurer_tls_strict,
    )


_bootstrap_environnement.__doc__ = (
    _bootstrap_runtime_impl.orchestrer_bootstrap.__doc__
)


def _bootstrap_venv_si_besoin_avec_mode(mode):
    return _bootstrap_runtime_impl.bootstrap_venv_avec_mode(
        mode,
        environnement=os.environ,
        bootstrap_venv=_bootstrap_venv_si_besoin,
    )


_bootstrap_venv_si_besoin_avec_mode.__doc__ = (
    _bootstrap_runtime_impl.bootstrap_venv_avec_mode.__doc__
)


_INSTALL_ALL_DEPS   = "--installer-deps"     in sys.argv
_DESINSTALLER       = "--desinstaller"       in sys.argv
_TELECHARGER_OUTILS = "--telecharger-outils" in sys.argv  # exécuté après _trouver_java
_SMOKETEST          = "--smoketest"          in sys.argv  # exécuté après bootstrap

_bootstrap_environnement()

# ── --installer-deps ─────────────────────────────────────────────────────────
# Force l'installation de TOUTES les dépendances (critiques + optionnelles +
# lazy) puis quitte. Utilisé par les scripts setup_build_*.
# Le flag est préservé dans sys.argv lors du re-exec dans le venv, ce qui
# garantit que l'install complète se fait bien DANS le venv cible.
def _installer_toutes_dependances():
    """Installe les dépendances de maintenance via le runtime testable."""
    return _bootstrap_runtime_impl.installer_toutes_dependances(
        gui_deps_plateforme=_gui_deps_plateforme,
    )


if _INSTALL_ALL_DEPS:
    sys.exit(0 if _installer_toutes_dependances() else 1)

# ── --desinstaller ────────────────────────────────────────────────────────────
# Supprime le venv (~/.lidar2map/venv) et le dossier d'extraction du bundle
# (~/Library/Application Support/lidar2map/ sur macOS, etc.).
# Ne supprime PAS le script lui-même ni le .app/.exe.
def _desinstaller_installation():
    """Désinstalle les données gérées et signale tout retrait partiel."""
    return _bootstrap_runtime_impl.desinstaller_lidar2map(
        systeme=platform.system(),
        home=Path.home(),
        localappdata=os.environ.get("LOCALAPPDATA"),
    )


if _DESINSTALLER:
    sys.exit(0 if _desinstaller_installation() else 1)

# ── --smoketest ──────────────────────────────────────────────────────────────
# Exécute les 5 modes du pipeline sur une petite zone (Garéoult 1 km) et
# vérifie que les outputs existent + non-vides. Présent dans le bundle →
# testable post-déploiement sur la machine de l'utilisateur.
#
# Le test invoque le SAME binaire (sys.executable en frozen, ou `python <ce
# script>` sinon) pour chaque mode via subprocess. LIDAR2MAP_WORK_DIR est
# hérité dans l'env → outputs dans <DOSSIER_TRAVAIL>/Projets/smoke/.
#
# Durée typique : ~1 min sur Windows (caches PBF/dalles présents), ~5 min
# au premier run (DL Geofabrik 400 MB).
def _executer_smoketest():
    """Exécute le diagnostic intégré via son orchestrateur testable."""
    return _smoketest_impl.executer_smoketest(
        frozen=getattr(sys, "frozen", False),
        executable=sys.executable,
        script_path=__file__,
        environnement=os.environ,
    )


if _SMOKETEST:
    sys.exit(0 if _executer_smoketest() else 1)

# ── suite du script ───────────────────────────────────────────────────────────

_TeeLogger = _tee_logger_impl.TeeLogger

# Flags portant un secret : leur valeur est masquée dans tout ce qu'on écrit
# (log fichier, historique, log GUI). La clé scan25 (IGN pro) ou us-3dep
# (OpenTopography) apparaissait sinon en clair dans des fichiers partagés
# pour débuguer. Défini AVANT _activer_log (appelé au chargement du module).
_SECRET_FLAGS = _logging_helpers_impl.SECRET_FLAGS


def _rediger_secrets(texte: str) -> str:
    return _logging_helpers_impl.rediger_secrets(texte)


def _activer_log():
    import atexit
    return _log_activation_impl.activer_log(
        sys_module=sys,
        environnement=os.environ,
        script_path=__file__,
        classe_logger=_TeeLogger,
        rediger_secrets=_rediger_secrets,
        enregistrer_atexit=atexit.register,
    )

_activer_log()


def _definir_chunk_log(cle):
    """Signale à _TeeLogger le chunk en cours (découpage à priori), pour
    préfixer chaque ligne du log qui suit (cf. _TeeLogger.definir_chunk).
    No-op si le log n'est pas actif (tests, sys.stdout non remplacé)."""
    _t = sys.stdout
    if isinstance(_t, _TeeLogger):
        _t.definir_chunk(cle)

# ── Requêtes HTTP via urllib (stdlib, zéro dépendance) ──────────────────────
_HTTP_UA = "lidar2map/1.0 (IGN WMTS/WMS)"

# Version applicative — SOURCE UNIQUE : utilisée par --version (les 3 mains),
# par le check de mise à jour du GUI (Api.check_update) ET par le titre de la
# fenêtre GUI (create_window). Le bump de release se fait ICI, nulle part
# ailleurs (fini les 3 chaînes argparse à synchroniser).
VERSION      = "1.44.0"
VERSION_DATE = "2026-08"


def _urlopen(url, headers=None, timeout=15):
    """Ouvre une URL avec urllib, retourne la réponse. Gère User-Agent par défaut."""
    return _http_helpers_impl.ouvrir_url(
        url,
        headers=headers,
        timeout=timeout,
        user_agent=_HTTP_UA,
        request_cls=urllib.request.Request,
        urlopen=urllib.request.urlopen,
    )


def _hms(seconds):
    return _logging_helpers_impl.formater_duree(seconds)


# Outils GDAL dont les appels subprocess sont affichés dans le terminal
def _log_req(url_or_cmd, label=""):
    """Log une requête externe (HTTP ou subprocess) — toujours via print/TeeLogger."""
    print(_logging_helpers_impl.formater_requete(url_or_cmd, label), flush=True)

# ============================================================
# PLATEFORME
# ============================================================

WINDOWS, LINUX, MACOS = _runtime_paths_impl.indicateurs_plateforme(
    platform.system()
)

# ── Manifest de fichiers créés (découpage à priori) ───────────────────────────
# Classe Manifeste : JSON local au projet, universel LiDAR/WMTS.
# _creer_fichier() fonctionne via un context manager thread-local —
# silencieux en dehors d'un contexte actif.

import threading as _threading
from contextlib import contextmanager as _contextmanager

from _split_manifest import (
    Manifeste,
    _contexte_manifeste,
    _creer_fichier,
    _creer_fichiers,
)


def _supprimer_fichiers(fichiers: list, dossiers_garder=None, noms_garder=None):
    """
    Supprime tous les fichiers créés par un morceau (--nettoyage).
    Cela inclut : dalles LiDAR, nuages .laz cachés, tuiles WMTS, TIF ombrages,
    TIF warpé. Conserve uniquement les sorties finales (.mbtiles, .rmap, .sqlitedb).

    But : permettre le traitement d'une grande BBox sans saturer le disque —
    chaque morceau libère son espace avant que le suivant démarre.

    Sont supprimés TOUS les fichiers enregistrés au manifest pour ce morceau via
    _creer_fichier. ATTENTION (R1#5/#9) : cela inclut une dalle ou un nuage .laz
    qui PRÉEXISTAIT (run antérieur, ou dalle de bord partagée avec un morceau
    voisin) — depuis que le cleanup .laz les enregistre pour libérer le disque,
    la garantie « les fichiers préexistants ne sont pas touchés » ne tient plus
    en général. Le cas du morceau SUIVANT immédiat (glissant, profondeur 1) est
    couvert par *noms_garder* (analyse de dépendance minimale, cf.
    _noms_dalles_morceau_suivant dans _run_split_priori_lidar_glissant) : au-delà
    de ce voisin direct, un morceau plus lointain peut toujours re-télécharger une
    dalle de bord. --cleanup-keep-tiles épargne le cache entièrement pour
    contourner ce cas résiduel.

    *dossiers_garder* non nul (--cleanup-keep-tiles) : un dossier OU un itérable
    de dossiers dont les fichiers sont ÉPARGNÉS (le cache de dalles, et en mode
    LAZ le cache de nuages .laz — partagés entre runs), les autres intermédiaires
    supprimés normalement. Sert quand une tâche ultérieure de la même file
    retraite la même zone : sans ça elle re-télécharge (ou reconvertit) des
    dalles qu'on vient d'effacer.

    *noms_garder* non nul (R1#5/#9) : ensemble de BASENAMES (indépendant du
    dossier) épargnés en plus de *dossiers_garder* — sert à protéger une
    dalle de bord dont le morceau SUIVANT (glissant) a encore besoin, sans
    épargner tout le cache comme le ferait --cleanup-keep-tiles.
    """
    suppr = 0
    gardees = 0
    dirs_a_verifier = set()
    _noms_garder = noms_garder or ()
    # Normaliser en liste de racines résolues à épargner (accepte Path unique,
    # itérable, ou None). None dans l'itérable = ignoré (provider sans cache LAZ).
    if dossiers_garder is None:
        _caches = []
    elif isinstance(dossiers_garder, (str, Path)):
        _caches = [Path(dossiers_garder).resolve()]
    else:
        _caches = [Path(d).resolve() for d in dossiers_garder if d is not None]
    for chemin in fichiers:
        p = Path(chemin)
        if p.name in _noms_garder:
            gardees += 1
            continue          # réclamé par le morceau suivant → gardé
        if _caches:
            _epargne = False
            for _c in _caches:
                try:
                    p.resolve().relative_to(_c)
                    _epargne = True
                    break
                except (ValueError, OSError):
                    continue      # hors de ce cache → tester le suivant
            if _epargne:
                gardees += 1
                continue          # sous un cache épargné → intermédiaire gardé
        # Tous les fichiers du manifest sont intermédiaires.
        # Les sorties finales (.mbtiles, .rmap…) ne sont jamais enregistrées
        # via _creer_fichier → elles ne se retrouvent jamais ici.
        if p.exists():
            try:
                p.unlink()
                dirs_a_verifier.add(p.parent)
                suppr += 1
            except Exception:
                pass
    for d in sorted(dirs_a_verifier, key=lambda x: len(x.parts), reverse=True):
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass
    if suppr or gardees:
        _kept = f", {gardees} cached tile(s) kept" if gardees else ""
        print(f"  Cleanup: {suppr} intermediate file(s) removed{_kept}")


# Code de sortie dédié au garde-fou disque (--min-free-gb). Permet à un
# orchestrateur multi-département (boucle shell « lance et oublie ») de
# distinguer un arrêt PROPRE « disque bas, relançable » d'une vraie erreur de
# traitement (exit 1). Convention proche de rsync/borg qui réservent des codes
# par catégorie d'arrêt.
EXIT_DISK_LOW = 3


def _espace_libre_go(chemin) -> float:
    return _disk_guard_impl.espace_libre_go(
        chemin, disk_usage=shutil.disk_usage
    )


_espace_libre_go.__doc__ = _disk_guard_impl.espace_libre_go.__doc__


def _garde_disque(chemin, seuil_go: float, cle: str, nb_ok: int, n_total: int):
    return _disk_guard_impl.garder_disque(
        chemin,
        seuil_go,
        cle,
        nb_ok,
        n_total,
        sonde=_espace_libre_go,
        exit_code=EXIT_DISK_LOW,
        ecrire=print,
        quitter=sys.exit,
    )


_garde_disque.__doc__ = _disk_guard_impl.garder_disque.__doc__


class _PrefetchDalles:
    """Précharge en tâche de fond la découverte+download des dalles du
    morceau SUIVANT pendant que l'ombrage (LRM/SVF/opos) du morceau courant
    tourne (_run_split_priori_lidar_glissant) — recouvre le download (réseau,
    throttle IGN) avec le calcul (CPU), qui peut être du même ordre de
    grandeur que le download sur un shading lourd (SVF sweep, opos).

    Profondeur 1 strictement : jamais plus d'un morceau d'avance (lancer()
    est un no-op si un préchargement est déjà en vol). Best-effort : toute
    erreur réseau/disque dans le thread de fond est avalée avec un message,
    le morceau se retéléchargera normalement à son tour (recuperer() renvoie
    None, chemin identique à si aucun préchargement n'avait été tenté).

    N'appelle jamais debut_morceau : le préchargement est invisible à la
    machine à états de reprise (Manifeste), seul le thread principal marque
    un morceau comme démarré/fini. Un crash pendant un préchargement laisse
    juste des dalles orphelines en cache, retrouvées comme cache-hit par le
    téléchargement normal au tour de ce morceau (aucune perte, aucune
    incohérence de reprise)."""

    def __init__(self):
        self._thread = None
        self._cle = None
        self._resultat = None

    def lancer(self, args, manifeste, racine_pr, nom_zone, sz, cle):
        if self._thread is not None:
            return  # profondeur 1 : un préchargement déjà en vol
        seuil = getattr(args, "min_free_gb", 0.0) or 0.0
        if seuil > 0 and _espace_libre_go(racine_pr) < 2 * seuil:
            # Marge insuffisante pour tenir DEUX morceaux à la fois sur le
            # disque (le courant, pas encore nettoyé, + celui-ci en approche).
            # Dégradation silencieuse vers le comportement synchrone existant.
            return
        nom_z = f"{nom_zone}_{cle}"
        bbox = tuple(sz[2:])

        def _travail():
            try:
                # nom_zone sert de nom_zone_base : même convention que
                # l'appel synchrone (_etape_ombrage -> _traiter_bbox_lidar_ombrage).
                self._resultat = _decouvrir_et_telecharger_ombrage(
                    args, bbox, nom_z, nom_zone, manifeste, cle, quiet=True)
            except Exception as e:
                print(f"  ⚠ Prefetch {cle}: {type(e).__name__}: {e} "
                      f"(ignoré, retéléchargement normal à son tour)")
                self._resultat = None

        self._cle = cle
        self._resultat = None
        self._thread = _threading.Thread(target=_travail, daemon=True)
        self._thread.start()

    def recuperer(self, cle):
        """Rejoint le préchargement en vol s'il correspond à cle et renvoie
        son résultat, sinon None (pas de préchargement en cours pour ce
        morceau, ou il a échoué) — le chemin synchrone normal prend le relais."""
        if self._thread is None or self._cle != cle:
            return None
        self._thread.join()
        resultat = self._resultat
        self._thread = None
        self._cle = None
        self._resultat = None
        return resultat

    def purger(self):
        """Rejoint un éventuel préchargement résiduel (fin de run) : évite un
        thread de fond qui traînerait après le retour de la boucle glissante."""
        if self._thread is not None:
            self._thread.join()
            self._thread = None
            self._cle = None
            self._resultat = None

# ============================================================
# CONFIGURATION
# ============================================================

# ── Chemins ─────────────────────────────────────────────────────────────────
# En mode frozen (PyInstaller) : __file__ pointe dans le bundle temporaire
# (sys._MEIPASS sous --onefile). On utilise sys.executable pour que les
# Projets/, cache/, logs/ etc. soient créés à côté de l'exe (cwd utilisateur).
# _MEIPASS reste utilisable séparément pour retrouver les ressources bundlées
# (tagmapping-min.xml).
DOSSIER_TRAVAIL, BUNDLE_DIR, LIDAR2MAP_HOME, DOSSIER_CACHE, DOSSIER_PRODUCTION = (
    _runtime_paths_impl.calculer_chemins(
        frozen=getattr(sys, "frozen", False),
        environnement=os.environ,
        executable=sys.executable,
        script_path=__file__,
        meipass=getattr(sys, "_MEIPASS", None),
        home=Path.home(),
    )
)

# Racine UNIQUE de tous les caches persistants (dalles LiDAR, tuiles WMTS, PBF
# OSM, index de découverte, contours de départements, BD TOPO). Déplaçable d'un
# geste via --cache-dir : utile pour poser le cache (potentiellement des dizaines
# de Go) sur un autre disque que les sorties. Défaut = <dossier de travail>/cache.
# Modifiée AU DÉBUT de chaque main via _appliquer_cache_dir(args). --tiles-dir
# reste le réglage FIN des seules dalles LiDAR, prioritaire sur cette racine.
def _appliquer_cache_dir(args):
    """Repointe la racine du cache si --cache-dir est passé. À appeler tôt dans
    chaque main, avant tout accès au cache. Idempotent (relance = même valeur)."""
    global DOSSIER_CACHE
    _cd = getattr(args, "cache_dir", None)
    if _cd:
        DOSSIER_CACHE = Path(_cd).resolve()
        DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)


# 3e tier : la PRODUCTION. Règle Nico : cache = ce qu'on TÉLÉCHARGE des serveurs
# (.laz, tuiles, PBF) ; production = ce qu'on PRODUIT à partir des réglages mais
# qui reste PARTAGÉ entre projets (indexé par provider+méthode+réglages+dalle,
# pas par zone). Aujourd'hui seul le .tif du mode LAZ est concerné : calculé
# du nuage avec tes réglages, il n'a rien à faire au cache (cf. le .tif MNT qui,
# lui, vient tel quel du WMS et RESTE au cache). Défaut : frère de cache/.
def _appliquer_production_dir(args):
    """Repointe la racine de production si --production-dir est passé. Miroir de
    _appliquer_cache_dir. À appeler tôt dans main (LiDAR uniquement l'utilise)."""
    global DOSSIER_PRODUCTION
    _pd = getattr(args, "production_dir", None)
    if _pd:
        DOSSIER_PRODUCTION = Path(_pd).resolve()
        DOSSIER_PRODUCTION.mkdir(parents=True, exist_ok=True)

# ── Provider LiDAR (par défaut : France IGN HD) ──────────────────────────────
# POC d'abstraction : tout ce qui est spécifique à une source nationale
# (URLs, CRS, nommage des dalles, géométrie) vit dans providers/<pays>.py.
# Le reste du pipeline (SVF, ombrages, MBTiles) reste agnostique.
#
# Sélection : --provider <code> en CLI, ou variable d'env LIDAR2MAP_PROVIDER.
# Codes disponibles : fr-ign (défaut), nl-ahn (POC).
import os as _os

def _discover_providers():
    """Liste les providers disponibles dans providers/*.py.

    Retourne une liste de dicts {code, name, country, country_rank,
    country_fr, country_en, ...} (sans erreur si un module est cassé). Utilisé
    par la GUI pour peupler son sélecteur de provider, groupé par pays selon
    country_rank.
    """
    try:
        _common_provider = _import_patchable_source_module(
            "providers", "common")
        _COUNTRY_INFO = _common_provider.COUNTRY_INFO
    except Exception:
        _COUNTRY_INFO = {}
    providers_dir = Path(__file__).resolve().parent / "providers"
    result = []
    if not providers_dir.exists():
        return result
    for f in sorted(providers_dir.glob("*.py")):
        if f.stem.startswith("_"):
            continue
        # Les modules *_laz sont des MODES (jumeaux LAZ d'une source), pas des
        # sources : ils ne vont pas dans le dropdown. La GUI les atteint via la
        # case « mode LAZ » du provider parent (champ "laz" ci-dessous).
        if f.stem.endswith("_laz"):
            continue
        try:
            mod = _import_patchable_source_module("providers", f.stem)
            # Un module SANS CODE n'est pas un provider mais un utilitaire
            # partagé (ex. providers/common.py) — ne pas le lister.
            if not hasattr(mod, "CODE"):
                continue
            # Pays : nom + rang d'affichage lus de la table unique
            # providers.common.COUNTRY_INFO (même ordre que les READMEs et la
            # carte de couverture). La GUI groupe sa dropdown là-dessus ; un
            # pays inconnu tombe en fin de liste sous son code brut.
            _cc = getattr(mod, "COUNTRY", "")
            _rank, _cn_en, _cn_fr = _COUNTRY_INFO.get(
                _cc, (9999, _cc.upper(), _cc.upper()))
            entry = {
                "code":           getattr(mod, "CODE",           f.stem),
                "name":           getattr(mod, "NAME",           f.stem),
                "country":        _cc,
                "country_rank":   _rank,
                "country_fr":     _cn_fr,
                "country_en":     _cn_en,
                "apikey_requise": bool(getattr(mod, "APIKEY_REQUISE", False)),
                "resolution_m":   float(getattr(mod, "RESOLUTION_M", 0.5)),
            }
            # Capacité LAZ : jumeau providers/<stem>_laz.py présent → la GUI
            # affiche la case « mode LAZ » + réglages (défauts lus du jumeau =
            # source de vérité unique, anti-drift GUI×pipeline).
            if (providers_dir / f"{f.stem}_laz.py").exists():
                try:
                    twin = _import_patchable_source_module(
                        "providers", f"{f.stem}_laz")
                    entry["laz"] = {
                        "hmin":    float(getattr(twin, "LAZ_HMIN", 0.4)),
                        "hmax":    float(getattr(twin, "LAZ_HMAX", 2.5)),
                        "classes": ",".join(str(c) for c in
                                            getattr(twin, "LAZ_CLASSES", (1, 3, 4))),
                        "ground":  str(getattr(twin, "LAZ_GROUND", "classes")),
                        "csf_threshold":  float(getattr(twin, "LAZ_CSF_THRESHOLD", 0.5)),
                        "csf_resolution": float(getattr(twin, "LAZ_CSF_RESOLUTION", 0.5)),
                        "csf_rigidness":  int(getattr(twin, "LAZ_CSF_RIGIDNESS", 1)),
                        # Plafond de download parallèle (gros nuages LAZ) : la GUI
                        # l'affiche en mode LAZ. 0 = pas de plafond annoncé.
                        "download_workers_max": int(getattr(twin, "DOWNLOAD_WORKERS_MAX", 0)),
                    }
                except Exception:
                    pass
            result.append(entry)
        except Exception as e:
            print(f"  [provider scan] {f.name} skipped: {type(e).__name__}: {e}",
                  file=sys.stderr)
    return result


def _pre_valeur_suivante(argv, i):
    """Valeur du token qui suit un pré-flag `--x VAL`, ou None si absente ou si
    c'est un autre flag (`--…`) / le séparateur `--` (R2#39 : le pré-parser
    manuel avalait `--` ou le flag suivant comme valeur, ex. `--provider --laz`
    posait code=`--laz`, `--provider --` posait code=`--`). Les nombres négatifs
    (`-0.5`, simple tiret) restent des valeurs valides."""
    if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
        return argv[i + 1]
    return None


_PROVIDER_CLI_EXPLICIT = False


def _load_provider():
    global _PROVIDER_CLI_EXPLICIT
    code = None
    # CLI scan léger (sans dépendre d'argparse qui n'est pas encore configuré).
    # --provider est un pré-flag GLOBAL : on le lit puis on le RETIRE de sys.argv
    # pour qu'aucun des parsers par-mode (raster, vecteur, fusion, découpe…) n'ait
    # à le déclarer. Sinon `--raster --provider us-tnm` → "unrecognized arguments".
    # Accepte les deux formes : `--provider code` et `--provider=code`.
    #
    # Pré-flags LAZ (mode « structures debout », cf. providers/fr_ign_laz.py) :
    #   --laz            bascule vers le provider jumeau <code>-laz (module
    #                    providers/<code>_laz.py — convention de nommage)
    #   --laz-hmin/--laz-hmax  tranche de hauteur réintroduite (m)
    #   --laz-classes    classes LAS réintroduites (ex. 1,3,4)
    #   --laz-ground     socle terrain : "classes" (défaut) ou "csf" (Cloth
    #                    Simulation Filter — hmin/hmax/classes alors ignorés)
    #   --laz-csf-threshold/-resolution/-rigidness  réglages du tissu (mode
    #                    csf seulement ; surface standard CloudCompare)
    # Réglages appliqués au module via set_laz_params() après import.
    _laz_mode = False
    _laz_params = {}
    _argv = sys.argv
    _i = 0
    while _i < len(_argv):
        _a = _argv[_i]
        if _a == "--provider":
            _v = _pre_valeur_suivante(_argv, _i)
            if _v is None:
                print("  ERROR: --provider requires a code "
                      "(e.g. --provider us-tnm).", file=sys.stderr)
                sys.exit(1)
            code = _v
            _PROVIDER_CLI_EXPLICIT = True
            del _argv[_i:_i + 2]
            continue
        if _a.startswith("--provider="):
            code = _a.split("=", 1)[1]
            _PROVIDER_CLI_EXPLICIT = True
            del _argv[_i]
            continue
        if _a == "--laz":
            _laz_mode = True
            del _argv[_i]
            continue
        _m = None
        for _k in ("hmin", "hmax", "classes", "ground",
                   "csf-threshold", "csf-resolution", "csf-rigidness"):
            if _a == f"--laz-{_k}":
                _v = _pre_valeur_suivante(_argv, _i)
                if _v is None:
                    print(f"  ERROR: --laz-{_k} requires a value.",
                          file=sys.stderr)
                    sys.exit(1)
                _laz_params[_k] = _v
                del _argv[_i:_i + 2]
                _m = True
                break
            if _a.startswith(f"--laz-{_k}="):
                _laz_params[_k] = _a.split("=", 1)[1]
                del _argv[_i]
                _m = True
                break
        if _m:
            continue
        _i += 1
    code = code or _os.environ.get("LIDAR2MAP_PROVIDER") or "fr-ign"
    if (_laz_mode or _laz_params) and not code.endswith("-laz"):
        code = code + "-laz"
    # Mapping code → module (kebab-case → snake_case)
    module_name = code.replace("-", "_")
    _pdir = Path(__file__).resolve().parent / "providers"
    try:
        _mod = _import_patchable_source_module("providers", module_name)
        # Réglages LAZ (--laz-hmin/hmax/classes) → posés sur le module jumeau.
        if _laz_params:
            _setp = getattr(_mod, "set_laz_params", None)
            if _setp is None:
                print(f"  ERROR: provider '{code}' has no LAZ settings "
                      f"(set_laz_params).", file=sys.stderr)
                sys.exit(1)
            try:
                _setp(hmin=float(_laz_params["hmin"]) if "hmin" in _laz_params else None,
                      hmax=float(_laz_params["hmax"]) if "hmax" in _laz_params else None,
                      classes=tuple(int(c) for c in _laz_params["classes"].split(","))
                              if "classes" in _laz_params else None,
                      ground=_laz_params.get("ground"),
                      csf_threshold=_laz_params.get("csf-threshold"),
                      csf_resolution=_laz_params.get("csf-resolution"),
                      csf_rigidness=_laz_params.get("csf-rigidness"))
            except ValueError as _e_v:
                print(f"  ERROR: invalid --laz-* value: {_e_v}", file=sys.stderr)
                sys.exit(1)
        return _mod
    except ModuleNotFoundError as _e_imp:
        _missing = getattr(_e_imp, "name", "") or ""
        _pkg = f"providers.{module_name}"
        # (a') --laz sur un provider sans jumeau LAZ : message dédié (la liste
        #      brute mélangerait sources et modes).
        if _missing == _pkg and _pdir.exists() and code.endswith("-laz") and _laz_mode:
            print(f"  ERROR: provider '{code[:-4]}' has no LAZ mode (no module "
                  f"providers/{module_name}.py). LAZ is available for: "
                  + ", ".join(sorted(p.stem[:-4].replace("_", "-")
                                     for p in _pdir.glob("*_laz.py"))),
                  file=sys.stderr)
            sys.exit(1)
        # (a) code inconnu (module absent alors que le package providers/ est
        #     présent) = faute de frappe -> échouer + lister, au lieu de devenir
        #     silencieusement FR-IGN (mauvais CRS/source de données).
        if _missing == _pkg and _pdir.exists():
            _dispo = sorted(p.stem.replace("_", "-") for p in _pdir.glob("*.py")
                            if not p.stem.startswith("_"))
            print(f"  ERROR: unknown provider '{code}'. Available: "
                  f"{', '.join(_dispo)}", file=sys.stderr)
            sys.exit(1)
        # (b) dépendance INTERNE au module provider manquante (ex. laspy pour
        #     cz-cuzk) : échouer clairement, ne pas masquer en FR-IGN.
        if _missing not in ("providers", _pkg):
            print(f"  ERROR: provider '{code}' failed to load: missing "
                  f"dependency '{_missing}'. Install it or choose another "
                  f"provider.", file=sys.stderr)
            sys.exit(1)
        # (c) package providers/ entièrement absent (distribution minimale) :
        #     fallback FR-IGN inline pour ne pas crasher.
        import types as _types
        _p = _types.SimpleNamespace(
            CODE               = "fr-ign",
            NAME               = "France IGN LiDAR HD",
            COUNTRY            = "fr",
            CRS_NATIF          = "EPSG:2154",
            RESOLUTION_M       = 0.5,
            DALLE_KM           = 1,
            PX_PAR_DALLE       = 2000,
            SEUIL_DALLE_VALIDE = 50_000,
            APIKEY_REQUISE     = False,
            WMS_URL            = None,
            WMS_LAYER          = None,
            WFS_URL            = None,
        )
        # discover_dalles : retourne {} — les call sites font déjà `or {}`
        # et le téléchargement est sauté si dalles_dict est vide.
        _p.discover_dalles = lambda bbox_wgs84, bbox_natif, cache_path, workers=1: {}
        # subdir_from_name : None → chemin_dalle retombe sur la racine (ok)
        _p.subdir_from_name = lambda nom: None
        # post_download / set_apikey : no-op silencieux
        _p.post_download    = lambda chemin: None
        _p.post_fetch       = None   # None = pas de conversion pre-validation
        _p.set_apikey       = lambda key:    None
        return _p
    except ImportError as _e_imp2:
        # ImportError autre que ModuleNotFound (rare) : ne pas la masquer.
        print(f"  ERROR loading provider '{code}': "
              f"{type(_e_imp2).__name__}: {_e_imp2}", file=sys.stderr)
        sys.exit(1)

PROVIDER = _load_provider()

# Sous-dossier provider-spécifique pour cache et Projets (rétrocompat : si le
# user a un ancien cache/ign_lidar/ ou Projets/<zone>/ign_lidar/, ils ne sont
# plus utilisés automatiquement — migration manuelle requise).
# Convention : "lidar/<country>" pour disambigüer par pays
# (cache/lidar/fr/, cache/lidar/nl/, ...).
LIDAR_SUBDIR = f"lidar/{PROVIDER.COUNTRY}"

# Re-exports pour compat avec le code existant — éviter de toucher des
# centaines de call sites en aval pendant ce POC.
RESOLUTION_M       = PROVIDER.RESOLUTION_M
# Les jumeaux LAZ à tuilage DYNAMIQUE (discover_dalles + bounds_fn : us-3dep-laz,
# ca-*-laz, pl/ee/be/fr-craig/dk-*-laz) ne définissent PAS de grille fixe
# DALLE_KM/PX_PAR_DALLE — seuls fr-ign-laz et ch-swisstopo-laz (1 km régulier) le
# font. getattr + défaut 1 km (le smoke _select le faisait déjà ; le chemin main
# lisait en dur → AttributeError sur un run CLI réel de ces jumeaux).
DALLE_KM           = getattr(PROVIDER, "DALLE_KM", 1)
PX_PAR_DALLE       = getattr(PROVIDER, "PX_PAR_DALLE",
                             int(round(DALLE_KM * 1000 / RESOLUTION_M)))
SEUIL_DALLE_VALIDE = PROVIDER.SEUIL_DALLE_VALIDE

# ── Réseau — tentatives et délais ─────────────────────────────────────────────
MAX_TENTATIVES = 3    # essais avant abandon d'un téléchargement
DELAI_RETRY    = 5    # secondes entre deux tentatives
NB_WORKERS     = 8    # workers parallèles par défaut (téléchargement dalles/tuiles)


# ── Validateurs argparse (type=…) ────────────────────────────────────────────
# Fonctions `type=` : argparse les appelle sur chaque valeur brute et, si elles
# lèvent ArgumentTypeError, affiche l'erreur + usage et sort en code 2. Bien
# plus propre que des checks post-parse éparpillés. Deux bugs couverts :
#   R2#41 : `--workers 0/négatif` plantait ThreadPoolExecutor (max_workers<1).
#   R2#25 : nan/inf passaient float() (littéraux valides) puis neutralisaient
#           silencieusement les features (nan>0 == False → --split-width/
#           --min-free-gb désactivés sans le dire).
def _arg_int_positif(s):
    """int ≥ 1 (workers, laz-parallel : max_workers<1 plante l'executor)."""
    try:
        v = int(s)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"invalid int value: {s!r}")
    if v < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {v}")
    return v


def _arg_float_fini(s):
    """float rejetant NaN/inf (params non finis, R2#25)."""
    try:
        v = float(s)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"invalid float value: {s!r}")
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def _arg_float_non_negatif(s):
    """float fini ≥ 0 (largeurs/seuils : 0 = désactivé, négatif = absurde)."""
    v = _arg_float_fini(s)
    if v < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {v}")
    return v


def _arg_float_positif(s):
    """float fini > 0 (distances/gamma : 0 ou négatif = absurde)."""
    v = _arg_float_fini(s)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {v}")
    return v


# ── MBTiles / WMTS — paramètres de batch ─────────────────────────────────────
SEUIL_ERR_CONSEC      = 30   # erreurs consécutives → abandon WMTS (panne systémique)
SEUIL_HORS_COUVERTURE = 300  # tuiles toutes en 204 avec 0 succès → bbox hors couche
BATCH_MBTILES_INSERT  = 2000 # tuiles par INSERT executemany dans MBTiles WMTS
BATCH_SQLITEDB_INSERT = 2000 # tuiles par batch lors de la conversion vers .sqlitedb
SEUIL_RMAP_PADDING    = 1_000_000  # tuiles vides de remplissage max avant refus RMAP
HTTP_CHUNK_SIZE       = 65536  # taille de lecture par chunk HTTP (téléchargement dalles)

# ── URL WFS IGN (re-export du provider) ──────────────────────────────────────
# getattr avec fallback None. AHN expose WCS_URL au lieu de WFS_URL : les chemins
# qui utilisent WFS_URL (BDTOPO, etc.) retombent alors sur None (à adapter).
WFS_URL   = getattr(PROVIDER, "WFS_URL",   None)

# ── Geofabrik : département → région (URL slug) ──────────────────────────────
# Table statique (135 entries) construite une seule fois à l'import au lieu
# d'être recréée à chaque appel d'`if args.osm:` dans main().
_GEOFABRIK = {
    # !! Geofabrik utilise les ANCIENNES régions administratives (pré-réforme 2016).
    # Les nouvelles régions (Occitanie, Nouvelle-Aquitaine, Grand Est, etc.)
    # n'existent PAS sur Geofabrik — chaque département pointe vers son ancienne région.
    # Source : https://download.geofabrik.de/europe/france.html

    # Rhône-Alpes (≠ Auvergne-Rhône-Alpes)
    "01": "rhone-alpes",           # Ain
    "07": "rhone-alpes",           # Ardèche
    "26": "rhone-alpes",           # Drôme
    "38": "rhone-alpes",           # Isère
    "42": "rhone-alpes",           # Loire
    "69": "rhone-alpes",           # Rhône
    "73": "rhone-alpes",           # Savoie
    "74": "rhone-alpes",           # Haute-Savoie
    # Auvergne (≠ Auvergne-Rhône-Alpes)
    "03": "auvergne",              # Allier
    "15": "auvergne",              # Cantal
    "43": "auvergne",              # Haute-Loire
    "63": "auvergne",              # Puy-de-Dôme
    # Bourgogne (≠ Bourgogne-Franche-Comté)
    "21": "bourgogne",             # Côte-d'Or
    "58": "bourgogne",             # Nièvre
    "71": "bourgogne",             # Saône-et-Loire
    "89": "bourgogne",             # Yonne
    # Franche-Comté (≠ Bourgogne-Franche-Comté)
    "25": "franche-comte",         # Doubs
    "39": "franche-comte",         # Jura
    "70": "franche-comte",         # Haute-Saône
    "90": "franche-comte",         # Territoire de Belfort
    # Bretagne (inchangée)
    "22": "bretagne",              # Côtes-d'Armor
    "29": "bretagne",              # Finistère
    "35": "bretagne",              # Ille-et-Vilaine
    "56": "bretagne",              # Morbihan
    # Centre (Geofabrik utilise "centre", pas "centre-val-de-loire")
    "18": "centre",                # Cher
    "28": "centre",                # Eure-et-Loir
    "36": "centre",                # Indre
    "37": "centre",                # Indre-et-Loire
    "41": "centre",                # Loir-et-Cher
    "45": "centre",                # Loiret
    # Corse (inchangée)
    "2A": "corse",                 # Corse-du-Sud
    "2B": "corse",                 # Haute-Corse
    # Alsace (≠ Grand Est)
    "67": "alsace",                # Bas-Rhin
    "68": "alsace",                # Haut-Rhin
    # Champagne-Ardenne (≠ Grand Est)
    "08": "champagne-ardenne",     # Ardennes
    "10": "champagne-ardenne",     # Aube
    "51": "champagne-ardenne",     # Marne
    "52": "champagne-ardenne",     # Haute-Marne
    # Lorraine (≠ Grand Est)
    "54": "lorraine",              # Meurthe-et-Moselle
    "55": "lorraine",              # Meuse
    "57": "lorraine",              # Moselle
    "88": "lorraine",              # Vosges
    # Nord-Pas-de-Calais (≠ Hauts-de-France)
    "59": "nord-pas-de-calais",    # Nord
    "62": "nord-pas-de-calais",    # Pas-de-Calais
    # Picardie (≠ Hauts-de-France)
    "02": "picardie",              # Aisne
    "60": "picardie",              # Oise
    "80": "picardie",              # Somme
    # Île-de-France (inchangée)
    "75": "ile-de-france",         # Paris
    "77": "ile-de-france",         # Seine-et-Marne
    "78": "ile-de-france",         # Yvelines
    "91": "ile-de-france",         # Essonne
    "92": "ile-de-france",         # Hauts-de-Seine
    "93": "ile-de-france",         # Seine-Saint-Denis
    "94": "ile-de-france",         # Val-de-Marne
    "95": "ile-de-france",         # Val-d'Oise
    # Haute-Normandie (≠ Normandie)
    "27": "haute-normandie",       # Eure
    "76": "haute-normandie",       # Seine-Maritime
    # Basse-Normandie (≠ Normandie)
    "14": "basse-normandie",       # Calvados
    "50": "basse-normandie",       # Manche
    "61": "basse-normandie",       # Orne
    # Aquitaine (≠ Nouvelle-Aquitaine)
    "24": "aquitaine",             # Dordogne
    "33": "aquitaine",             # Gironde
    "40": "aquitaine",             # Landes
    "47": "aquitaine",             # Lot-et-Garonne
    "64": "aquitaine",             # Pyrénées-Atlantiques
    # Limousin (≠ Nouvelle-Aquitaine)
    "19": "limousin",              # Corrèze
    "23": "limousin",              # Creuse
    "87": "limousin",              # Haute-Vienne
    # Poitou-Charentes (≠ Nouvelle-Aquitaine)
    "16": "poitou-charentes",      # Charente
    "17": "poitou-charentes",      # Charente-Maritime
    "79": "poitou-charentes",      # Deux-Sèvres
    "86": "poitou-charentes",      # Vienne
    # Languedoc-Roussillon (≠ Occitanie)
    "11": "languedoc-roussillon",  # Aude
    "30": "languedoc-roussillon",  # Gard
    "34": "languedoc-roussillon",  # Hérault
    "48": "languedoc-roussillon",  # Lozère
    "66": "languedoc-roussillon",  # Pyrénées-Orientales
    # Midi-Pyrénées (≠ Occitanie)
    "09": "midi-pyrenees",         # Ariège
    "12": "midi-pyrenees",         # Aveyron
    "31": "midi-pyrenees",         # Haute-Garonne
    "32": "midi-pyrenees",         # Gers
    "46": "midi-pyrenees",         # Lot
    "65": "midi-pyrenees",         # Hautes-Pyrénées
    "81": "midi-pyrenees",         # Tarn
    "82": "midi-pyrenees",         # Tarn-et-Garonne
    # Pays de la Loire (inchangé)
    "44": "pays-de-la-loire",      # Loire-Atlantique
    "49": "pays-de-la-loire",      # Maine-et-Loire
    "53": "pays-de-la-loire",      # Mayenne
    "72": "pays-de-la-loire",      # Sarthe
    "85": "pays-de-la-loire",      # Vendée
    # Provence-Alpes-Côte d'Azur (inchangée)
    "04": "provence-alpes-cote-d-azur",  # Alpes-de-Haute-Provence
    "05": "provence-alpes-cote-d-azur",  # Hautes-Alpes
    "06": "provence-alpes-cote-d-azur",  # Alpes-Maritimes
    "13": "provence-alpes-cote-d-azur",  # Bouches-du-Rhône
    "83": "provence-alpes-cote-d-azur",  # Var
    "84": "provence-alpes-cote-d-azur",  # Vaucluse
    # DOM/TOM (extraits Geofabrik séparés)
    "971": "guadeloupe",
    "972": "martinique",
    "973": "guyane",
    "974": "reunion",
    "976": "mayotte",
}
_GEOFABRIK_BASE_URL      = "https://download.geofabrik.de/europe/france"
_GEOFABRIK_BASE_URL_ROOT = "https://download.geofabrik.de/europe"


from _terrain_zones import (
    regions_disponibles as _regions_disponibles_impl,
    departements_de_region as _departements_de_region_impl,
)


def _regions_disponibles():
    """Liste triée des slugs de régions Geofabrik (dédupliqués depuis _GEOFABRIK).

    L'unité = la région Geofabrik (anciennes régions pré-2016), pas la région
    administrative actuelle : chaque slug correspond à exactement un PBF, ce qui
    évite toute fusion. Ex: 'provence-alpes-cote-d-azur'."""
    return _regions_disponibles_impl(_GEOFABRIK)


def _departements_de_region(slug):
    """Departments (codes INSEE) appartenant à la région Geofabrik `slug`."""
    return _departements_de_region_impl(_GEOFABRIK, slug)

# ── Rendu archéologique ───────────────────────────────────────────────────────
ELEVATION_SOLEIL = 25   # degrés — 25° révèle micro-reliefs ; 45° usage général

def _valider_zooms(args, parser):
    """Vérifie zoom_min ≤ zoom_max avant lancement du pipeline.

    Sans ce check, l'utilisateur qui saisit `--zoom-min 18 --zoom-max 13`
    voit un calculer_grille_xyz() vide et un MBTiles à 0 tuile sans message
    d'erreur, ou pire (sur dept-scale) tourne longtemps sur des plages
    invalides avant de produire un fichier vide. parser.error() affiche un
    message argparse standard et sort en code 2.
    """
    zmin = getattr(args, "zoom_min", None)
    zmax = getattr(args, "zoom_max", None)
    if zmin is None or zmax is None:
        return
    if zmin > zmax:
        parser.error(
            f"--zoom-min ({zmin}) > --zoom-max ({zmax}). "
            f"Inversez les valeurs ou retirez l'un des deux pour utiliser le défaut."
        )
    if zmin < 0 or zmax > 22:
        parser.error(
            f"Zoom hors plage : --zoom-min={zmin} --zoom-max={zmax} "
            f"(valeurs valides : 0 à 22)."
        )


# Cache des Transformer pyproj : leur création prend ~10 ms (lecture proj.db,
# parsing CRS, init de la chaîne d'opérations). Inutile de les recréer à chaque
# appel — ils sont thread-safe et réutilisables.
# 5 sites du code créaient le même Transformer 4326↔2154 ; gain marginal mais
# code plus propre. On utilise functools.lru_cache pour mémoriser par paire
# (src_crs, dst_crs).
import functools as _functools

@_functools.lru_cache(maxsize=8)
def _get_transformer(src_crs, dst_crs, always_xy=True):
    """Retourne un pyproj Transformer mémorisé pour la paire (src, dst).

    Utilisation :
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        x_l93, y_l93 = t.transform(lon, lat)

    Note : ne pas appeler avec always_xy=False et always_xy=True alternativement
    sur la même paire — le cache verra ça comme deux entrées distinctes (correct).
    """
    from pyproj import Transformer
    return Transformer.from_crs(src_crs, dst_crs, always_xy=always_xy)


def _ecrire_json_atomique(path, data, indent=None):
    """Écrit data en JSON dans path de façon atomique.

    Pattern : sérialiser en RAM, écrire dans path.part, fsync, replace path.
    Garantit que path est soit l'ancienne version, soit la nouvelle complète,
    jamais une troncature. Critique pour les caches (manifeste, dep_bbox,
    TMS) où une corruption silencieuse fait perdre l'état entre runs.

    En cas d'OSError (disque plein, permission, etc.), le tmp est nettoyé
    et l'exception remonte. Pas de swallow silencieux comme l'ancien
    `except Exception: pass` du Manifeste.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _chemin_part(path)
    try:
        # Sérialisation en RAM d'abord (un seul write atomique sur le tmp)
        if indent is not None:
            payload = json.dumps(data, ensure_ascii=False, indent=indent)
        else:
            payload = json.dumps(data, ensure_ascii=False)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            try:
                os.fsync(f.fileno())  # garantit que le contenu est sur disque
            except (OSError, AttributeError):
                pass  # fsync indisponible (ramdisk, certains FS) — non critique
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _ecrire_texte_atomique(path, texte, encoding="utf-8"):
    """Ã‰crit un petit fichier texte via un ``.part`` voisin puis replace.

    L'ancien fichier reste intact si l'Ã©criture, le fsync ou la publication
    Ã©choue. Ce helper couvre notamment les listes de dalles et signatures,
    qui servent de source de vÃ©ritÃ© aux reprises suivantes.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = _chemin_part(path)
    try:
        with open(part, "w", encoding=encoding) as f:
            f.write(str(texte))
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass
        os.replace(part, path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _chemin_part(path):
    """Chemin temporaire unique `<nom>.<pid>.<token>.part`.

    Pattern .part + rename : le fichier final n'existe jamais à l'état
    partiel. Un kill mi-écriture (Ctrl+C, taskkill du stop GUI, crash) ne
    laisse qu'un .part ignoré par les consommateurs, au lieu d'un artefact
    tronqué que les checks "already present" prendraient pour complet.
    Le nom unique empêche deux processus visant le même cache partagé de
    supprimer ou d'écraser le staging l'un de l'autre.
    """
    return _atomic_files_impl.chemin_part(path)


def _nettoyer_sqlite_part(path):
    """Supprime un chantier SQLite et ses sidecars, sans toucher au final.

    Les bases de sortie sont construites sous un nom ``*.part``. SQLite peut
    toutefois créer ``-wal``, ``-shm`` ou ``-journal`` à côté. Centraliser leur
    nettoyage évite qu'un Ctrl+C ou une erreur laisse un handle/sidecar pris
    pour une sortie autonome par un outil de synchronisation.
    """
    return _atomic_files_impl.nettoyer_sqlite_part(path)


def _publier_groupe_atomique(paires):
    """Promeut plusieurs fichiers en conservant un rollback complet."""
    return _atomic_files_impl.publier_groupe_atomique(
        paires, creer_sauvegarde=_chemin_part,
    )


def _valider_sqlite_part(path, tables_attendues):
    """Valide une base staging fermée avant son ``replace`` final.

    ``tables_attendues`` associe chaque table à son nombre de lignes attendu.
    La réouverture explicite en lecture seule prouve aussi que le fichier
    principal se suffit à lui-même après fermeture (aucun WAL requis).
    """
    return _atomic_files_impl.valider_sqlite_part(path, tables_attendues)


def _safe_zip_extractall(zf, target):
    """zipfile.extractall(target) protégé contre les chemins absolus et
    les traversées ``..`` (zip-slip).

    Python 3.12+ a ``filter='data'`` pour zipfile mais notre minimum est
    3.8 → on valide manuellement. Pour les tarfiles on utilise déjà
    ``filter='data'`` natif (cf. ``_telecharger_jre_local``).
    """
    target = Path(target).resolve()
    for m in zf.infolist():
        # Refuser absolu (Windows drive + Unix slash absolu) et drive letter
        if m.filename.startswith(("/", "\\")) or ":" in m.filename[:3]:
            raise ValueError(f"Chemin absolu dans le zip : {m.filename!r}")
        dest = (target / m.filename).resolve()
        # dest doit être sous target (ou exactement target pour un nom vide)
        if dest != target and target not in dest.parents:
            raise ValueError(f"Chemin sortant du dossier cible : {m.filename!r}")
    zf.extractall(target)


def _gunzip_vers_fichier(src_gz, dst_raw, chunk=1 << 20):
    """Décompresse src_gz → dst_raw en streaming (1 MB à la fois).

    Remplace le pattern `fout.write(fin.read())` qui charge intégralement
    en RAM. Sur un GeoJSON dept-scale (1-3 Go en clair), la version naïve
    fait peser 1-3 Go de RAM Python pour zéro raison ; la version streamée
    travaille avec ~1 MB en pic.

    Écriture atomique via .part + replace : si la décompression est interrompue,
    le fichier final n'est jamais en état partiel.
    """
    src_gz  = Path(src_gz)
    dst_raw = Path(dst_raw)
    dst_raw.parent.mkdir(parents=True, exist_ok=True)
    tmp = _chemin_part(dst_raw)
    try:
        with gzip.open(src_gz, "rb") as fin, open(tmp, "wb") as fout:
            shutil.copyfileobj(fin, fout, length=chunk)
        os.replace(tmp, dst_raw)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _gzip_depuis_fichier(src_raw, dst_gz, compresslevel=6, chunk=1 << 20):
    """Compresse src_raw → dst_gz en streaming (1 MB à la fois).

    Pendant l'écriture, le contenu va dans dst_gz.part puis replace : un Ctrl+C
    en cours de compression ne laisse pas un .gz tronqué à la place de
    l'ancien fichier valide.
    """
    src_raw = Path(src_raw)
    dst_gz  = Path(dst_gz)
    dst_gz.parent.mkdir(parents=True, exist_ok=True)
    tmp = _chemin_part(dst_gz)
    try:
        with open(src_raw, "rb") as fin, \
             gzip.open(tmp, "wb", compresslevel=compresslevel) as fout:
            shutil.copyfileobj(fin, fout, length=chunk)
        os.replace(tmp, dst_gz)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


import signal as _signal
def _on_sigint(sig, frame):
    """Soft cancel : 1er Ctrl+C demande l'arrêt, 2nd force la sortie.

    Pattern standard Unix (git, rsync, etc.) : on laisse l'opération en cours
    finir proprement (cleanup .part, fermeture sqlite, etc.) plutôt que de
    couper sec. Si l'utilisateur insiste avec un 2nd Ctrl+C, on quitte direct.

    Limites connues :
    - Subprocess fils (osmosis, ogr2ogr) ne sont PAS tués — ils tournent
      jusqu'au bout de leur opération courante (Java buffer flush, etc.)
    - Kernel Numba (SVF, RRIM) est intuable pendant son exécution.
      L'interruption est respectée APRÈS le kernel courant, entre directions
      sur le fallback numpy uniquement.
    """
    if _stop_event.is_set():
        # 2ème Ctrl+C → sortie immédiate (code 128+SIGINT par convention POSIX)
        print("\n\nForcing - immediate exit.", flush=True)
        sys.exit(130)
    _stop_event.set()
    print("\n\nInterruption requested - finishing the current operation.", flush=True)
    print("  Press Ctrl+C again to force exit.", flush=True)
_signal.signal(_signal.SIGINT, _on_sigint)
# Windows : le bouton Arrêter du GUI envoie CTRL_BREAK_EVENT au groupe de
# processus (seul signal envoyable à un child console sous Windows). Python
# le reçoit en SIGBREAK, dont l'action PAR DÉFAUT est une sortie sèche sans
# cleanup : on le route vers le même soft-cancel que Ctrl+C.
if WINDOWS and hasattr(_signal, "SIGBREAK"):
    _signal.signal(_signal.SIGBREAK, _on_sigint)

# ============================================================
# UTILITAIRES

from _terrain_zones import (
    normaliser_nom as _normaliser_nom_impl,
    nom_zone_gps_auto as _nom_zone_gps_auto_impl,
    nom_zone_bbox_auto as _nom_zone_bbox_auto_impl,
    zone_cli_presente as _zone_cli_presente_impl,
    wgs84_to_lamb93_approx as _wgs84_to_lamb93_approx_impl,
    lamb93_to_wgs84_approx as _lamb93_to_wgs84_approx_impl,
    bbox_enveloppe_transform as _bbox_enveloppe_transform_impl,
    exiger_pyproj_hors_france as _exiger_pyproj_hors_france_impl,
    wgs84_vers_natif as _wgs84_vers_natif_impl,
    natif_vers_wgs84 as _natif_vers_wgs84_impl,
)
# ============================================================

def _exiger_pyproj_hors_france(cible):
    return _exiger_pyproj_hors_france_impl(
        getattr(PROVIDER, "CRS_NATIF", "EPSG:2154"), cible,
    )


def _wgs84_vers_natif(lon, lat):
    return _wgs84_vers_natif_impl(
        lon, lat, crs_natif=PROVIDER.CRS_NATIF, get_transformer=_get_transformer,
    )


def _natif_vers_wgs84(x, y):
    return _natif_vers_wgs84_impl(
        x, y, crs_natif=PROVIDER.CRS_NATIF, get_transformer=_get_transformer,
    )



# ============================================================
# GÉOCODAGE
# ============================================================

def normaliser_nom(texte):
    return _normaliser_nom_impl(texte)


def _nom_zone_gps_auto(lat, lon):
    return _nom_zone_gps_auto_impl(lat, lon)


def _nom_zone_bbox_auto(lon_min, lat_min, lon_max, lat_max):
    return _nom_zone_bbox_auto_impl(lon_min, lat_min, lon_max, lat_max)


def _zone_cli_presente(args):
    return _zone_cli_presente_impl(args)


def wgs84_to_lamb93_approx(lon, lat):
    return _wgs84_to_lamb93_approx_impl(lon, lat)


def lamb93_to_wgs84_approx(x, y):
    return _lamb93_to_wgs84_approx_impl(x, y)


def _bbox_enveloppe_transform(transform_fn, x1, y1, x2, y2, densify=21):
    return _bbox_enveloppe_transform_impl(transform_fn, x1, y1, x2, y2, densify)


from _terrain_geocoding import geocoder_ville_wgs84 as _geocoder_ville_wgs84_impl


def geocoder_ville_wgs84(nom_ville):
    """Façade historique vers le géocodeur Nominatim extrait."""
    return _geocoder_ville_wgs84_impl(
        nom_ville,
        country=getattr(PROVIDER, "COUNTRY", "fr"),
        http_ua=_HTTP_UA,
        log_req=_log_req,
        urlopen=urllib.request.urlopen,
    )


def geocoder_ville_natif(nom_ville):
    """Géocode une ville → (x, y) dans le CRS natif du provider (pipeline LiDAR).
    Retourne (None, None) si échec."""
    lat, lon = geocoder_ville_wgs84(nom_ville)
    if lat is None:
        return None, None
    x, y = _wgs84_vers_natif(lon, lat)
    print(f"  {PROVIDER.CRS_NATIF} -> X={x:.0f}, Y={y:.0f}")
    return x, y


from _terrain_geocoding import geocoder_departement as _geocoder_departement_impl


def geocoder_departement(num_dep):
    """Façade historique vers le géocodeur département Overpass extrait."""
    return _geocoder_departement_impl(
        num_dep,
        cache_dir=DOSSIER_CACHE,
        bbox_transform=_bbox_enveloppe_transform,
        wgs84_vers_natif=_wgs84_vers_natif,
        ecrire_json_atomique=_ecrire_json_atomique,
        http_ua=_HTTP_UA,
        log_req=_log_req,
        urlopen=urllib.request.urlopen,
        sleep=time.sleep,
    )


from _terrain_geocoding import geocoder_region as _geocoder_region_impl


def geocoder_region(slug):
    """Façade historique vers l'agrégateur régional extrait."""
    return _geocoder_region_impl(
        slug,
        departements_de_region=_departements_de_region,
        regions_disponibles=_regions_disponibles,
        geocoder_departement=geocoder_departement,
        crs_natif=PROVIDER.CRS_NATIF,
    )

from _terrain_zones import parser_departements as _parser_departements_impl


def _parser_departements(valeur: str) -> list:
    """Façade historique vers le parseur de codes INSEE extrait."""
    return _parser_departements_impl(valeur)


from _split_planning import (
    _calculer_sous_zones_priori as _calculer_sous_zones_priori_impl,
    _cle_chunk,          # noqa: F401 - réexport de façade (contrat historique)
    _identite_chunk,     # noqa: F401 - réexport de façade (contrat historique)
    _parse_block as _parse_block_impl,
    _signature_config as _signature_config_impl,
)


def _parse_block(spec: str):
    """Façade historique vers le parseur de sharding extrait."""
    return _parse_block_impl(spec)


# ============================================================
# GRILLE DE DALLES
# ============================================================

def calculer_grille_bbox(x1, y1, x2, y2):
    """Retourne la bbox (x1, y1, x2, y2) telle quelle, dans le CRS natif du
    provider. Le NOMBRE de dalles et l'estimation disque ne sont PLUS calculés
    ici par un appel provider dalles_pour_bbox (l'ancien point d'interface grille, encore
    exécuté par le cœur) : le compte fiable vient de PROVIDER.discover_dalles()
    en aval, uniforme pour les providers-grille ET dynamiques (avant, ces
    derniers annonçaient « 0 dalle » puis découvraient plus tard). Revue code
    mort 2026-07-22, point 5. dalles_pour_bbox reste un helper INTERNE des
    discover_dalles à grille (de_mv, etc.), plus une interface cœur→provider."""
    return (x1, y1, x2, y2)


def _crs_natif_geographique():
    """True si CRS_NATIF est GÉOGRAPHIQUE (lon/lat en degrés, ex. ca-nrcan/
    ca-quebec 4617, us-3dep 4269) plutôt que projeté (mètres)."""
    try:
        from pyproj import CRS
        return CRS.from_user_input(PROVIDER.CRS_NATIF).is_geographic
    except Exception:
        return False


def calculer_grille(cx, cy, rayon_km):
    """Retourne la bbox (x1, y1, x2, y2) depuis un centre CRS natif et un rayon en km.
    Le rayon (km) est converti dans l'UNITÉ du CRS_NATIF : mètres si le CRS est
    PROJETÉ, DEGRÉS s'il est GÉOGRAPHIQUE (ca-nrcan/us-3dep/ca-quebec cadrent en
    lon/lat). Sans ça, r=km·1000 était traité comme des DEGRÉS → bbox hors domaine
    → transform WGS84 = inf → découverte cassée (les 3 providers géographiques,
    jamais testés en CLI complet ; revue 2026-07-22). Projetés : inchangés."""
    if _crs_natif_geographique():
        dy = rayon_km / 111.0
        dx = rayon_km / (111.0 * max(0.01, math.cos(math.radians(cy))))
    else:
        dx = dy = rayon_km * 1000
    return calculer_grille_bbox(cx - dx, cy - dy, cx + dx, cy + dy)


def _rglob_tif_robuste(dossier):
    """rglob("*.tif") avec gestion des erreurs d'accès disque (WinError 121)."""
    resultats = []
    try:
        for sous_dossier in sorted(dossier.iterdir()):
            try:
                if sous_dossier.is_dir():
                    for f in sous_dossier.glob("*.tif"):
                        resultats.append(f)
                elif sous_dossier.suffix.lower() == ".tif":
                    resultats.append(sous_dossier)
            except OSError as _e:
                print(f"  WARNING: inaccessible directory {sous_dossier.name} ({_e}) - skipped")
    except OSError as _e:
        print(f"  WARNING: tiles folder inaccessible ({_e})")
    return resultats


def _nom_dalle_sur(nom):
    """True si `nom` est un BASENAME sûr (pas de traversée de chemin).

    Les noms de dalles proviennent d'un index DISTANT du fournisseur (WFS/JSON/
    ATOM). Un nom piégé (`../…`, séparateur, chemin absolu ou lettre de lecteur)
    servirait à écrire HORS du cache via `dossier / nom` (traversée, R2#3). On
    exige un composant de chemin unique, non `.`/`..`, sans NUL."""
    if not nom or nom in (".", ".."):
        return False
    s = str(nom)
    if "\x00" in s or "/" in s or "\\" in s:
        return False
    if os.path.isabs(s) or os.path.splitdrive(s)[0]:
        return False
    return os.path.basename(s) == s


def chemin_dalle(dossier_dalles, nom):
    """
    Retourne le Path complet d'une dalle dans la structure sous-dossiers.
    Les dalles sont organisées par colonne X : dossier_dalles/XXXX/nom.tif
    ex: D:/Lidar/Dalles/0958/LHD_FXX_0958_6279_MNT_O_0M50_LAMB93_IGN69.tif

    Fallback transparent : si la dalle existe à la racine (ancienne structure),
    retourne le chemin racine. Sinon retourne le chemin sous-dossier.
    """
    # Invariant de sécurité : jamais construire un chemin à partir d'un nom qui
    # échapperait le dossier (traversée, R2#3). Lève plutôt que de retourner un
    # chemin hors cache ; les boucles de consommation pré-filtrent pour dégrader
    # proprement (cf. _telecharger_dalles_zone / _lister_dalles_zone).
    if not _nom_dalle_sur(nom):
        raise ValueError(f"unsafe tile name (path traversal): {nom!r}")
    # Chemin racine (ancienne structure)
    chemin_racine = dossier_dalles / nom
    if chemin_racine.exists():
        return chemin_racine
    # Délégation au provider pour extraire le sous-dossier depuis le nom
    sub = PROVIDER.subdir_from_name(nom)
    if sub:
        return dossier_dalles / sub / nom
    return chemin_racine  # fallback si nom non reconnu


def _dossier_dalles_actif(args, dossier_ville=None):
    """Racine des dalles LiDAR, selon la NATURE du .tif :
      - MNT : le .tif vient du serveur (WMS) = DOWNLOAD → cache ;
      - LAZ : le .tif est CALCULÉ du nuage avec tes réglages = PRODUIT →
        production (partagé entre projets, hors du cache). Le nuage .laz, lui,
        RESTE au cache (posé par _configurer_cloud_cache → set_cloud_cache_dir).
      - FENÊTRÉ (COPC/COG) : le .tif est une FENÊTRE propre à la zone mais nommée
        par l'ASSET distant. Cache/production PARTAGÉS le feraient réutiliser
        entre zones DIFFÉRENTES du même asset → relief d'une autre zone servi en
        silence (#1, revue 2026-07-22). On le range DANS LE PROJET (dossier_ville)
        → isolation par zone ; le skip par nom redevient correct (même zone =
        même dossier). Prioritaire sur cache/production.
    --dossier-dalles force la racine (prioritaire, tous modes)."""
    if args.dossier_dalles:
        return Path(args.dossier_dalles).resolve()
    if dossier_ville is not None and (getattr(PROVIDER, "COG_WINDOWED", False)
                                      or getattr(PROVIDER, "COPC_WINDOWED", False)):
        return Path(dossier_ville)
    if PROVIDER.CODE.endswith("-laz"):
        return DOSSIER_PRODUCTION / LIDAR_SUBDIR
    return DOSSIER_CACHE / LIDAR_SUBDIR


def _configurer_cloud_cache(args):
    """Mode LAZ : le .tif descend en production (cf. _dossier_dalles_actif),
    mais le nuage .laz est un download → il RESTE au cache. On indique au
    LazProvider où garder le nuage. Si --dossier-dalles force la racine des .tif,
    le nuage la suit (co-localisé, sémantique historique du flag « tout le LiDAR
    de cette dalle ici »). Idem pour un provider FENÊTRÉ (COPC) : le nuage .laz
    est une fenêtre propre à la zone → il suit le .tif EN PROJET (co-localisé),
    pas le cache partagé (même collision cross-zone que le .tif sinon, #1).
    No-op pour un provider sans mode LAZ."""
    _set = getattr(PROVIDER, "set_cloud_cache_dir", None)
    if _set:
        _windowed = (getattr(PROVIDER, "COG_WINDOWED", False)
                     or getattr(PROVIDER, "COPC_WINDOWED", False))
        _val = (None if (args.dossier_dalles or _windowed)
                else DOSSIER_CACHE / LIDAR_SUBDIR)
        _set(_val)
        # Racine du cache .laz mémorisée pour --cleanup-keep-tiles : le cœur ne
        # peut pas la relire sur PROVIDER (c'est le MODULE provider, qui ne
        # ré-exporte pas l'attribut MUTABLE cloud_cache_dir de son _P ; un
        # ré-export figerait la valeur à None, posée après par le setter).
        args._cloud_cache_dir = _val


def _download_to_tmp(url, chemin_tmp, timeout=60):
    """
    Télécharge url vers chemin_tmp (streaming).
    Retourne le nombre d'octets écrits, ou lève une exception.
    404 → 0 (dalle absente) ; réponse d'erreur XML/HTML en 200 → IOError
    (erreur de service, retry côté caller — pas une absence).
    timeout : tuple (connexion_s, lecture_s) ou entier.

    Protection contre les coupures TCP silencieuses (typiques sur VM/macOS) :
    si le serveur annonce Content-Length, on vérifie que la taille reçue
    correspond exactement — sinon on lève IOError pour déclencher le retry.
    Sur Windows, urllib/WinINet lève une exception dans ce cas ; sur macOS/Linux
    la socket BSD renvoie b"" sans erreur, ce qui sans cette garde produirait
    un fichier tronqué accepté silencieusement comme valide.
    """
    return _http_helpers_impl.telecharger_vers_tmp(
        url,
        chemin_tmp,
        timeout=timeout,
        ouvrir_url=_urlopen,
        taille_bloc=HTTP_CHUNK_SIZE,
    )


def _valider_tif_dalle(chemin):
    """
    Vérifie qu'un fichier TIF téléchargé est un GeoTIFF valide et lisible.

    Deux niveaux de vérification :
      1. Magic bytes (rapide, sans dépendance) : les 4 premiers octets d'un
         TIFF sont toujours 49 49 2A 00 (little-endian) ou 4D 4D 00 2A
         (big-endian). Un fichier tronqué au milieu du transfert n'aura pas
         ces octets, ou aura un IFD invalide.
      2. Ouverture rasterio (si disponible) : tente de lire les métadonnées
         (width, height, CRS) pour détecter les TIF dont le header est intact
         mais dont les données sont corrompues ou tronquées.

    Retourne True si le fichier est valide, False sinon.
    Ne lève jamais d'exception.
    """
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
        # TIFF magic = II/MM (byte order) + 42 ou 43 (BigTIFF, supporté par
        # rasterio/GDAL). BigTIFF est utilisé par certains COG (ex: AHN PDOK)
        # même pour des fichiers < 4 Go. Refuser BigTIFF = faux négatif.
        # - TIFF classique LE : II + 2A 00  (42)
        # - TIFF classique BE : MM + 00 2A  (42)
        # - BigTIFF LE        : II + 2B 00  (43)
        # - BigTIFF BE        : MM + 00 2B  (43)
        if magic[:2] not in (b"II", b"MM"):
            return False
        if magic[2:4] not in (b"\x2a\x00", b"\x00\x2a", b"\x2b\x00", b"\x00\x2b"):
            return False
    except OSError:
        return False

    # Vérification approfondie via rasterio si disponible
    try:
        import rasterio as _rio_v
    except ImportError:
        return True   # rasterio absent : on se fie au magic seul
    try:
        with _rio_v.open(str(chemin)) as ds:
            if ds.width == 0 or ds.height == 0:
                return False
            # Bande d'élévation présente + géotransform non dégénérée (audit
            # providers #2 : l'ancien contrôle ne vérifiait ni le nombre de
            # bandes ni la résolution). Volontairement PAS de contrôle CRS ici :
            # ce validateur tourne AUSSI avant post_download (cf. at-bev, COG
            # LOCAL_CS réétiqueté ENSUITE) ; exiger un CRS rejetterait ces dalles
            # à tort. L'exigence CRS/résolution est portée par le smoke test,
            # par provider.
            if ds.count < 1:
                return False
            rx, ry = ds.res
            if not (0 < rx < 1e9) or not (0 < ry < 1e9):
                return False
            # Lire 1 bloc pour détecter une troncature des données
            ds.read(1, window=_rio_v.windows.Window(
                0, 0, min(64, ds.width), min(64, ds.height)))
    except Exception:
        # Header intact mais métadonnées/données illisibles (troncature
        # deflate, IFD cassé) : c'est PRÉCISÉMENT le cas que ce niveau 2
        # doit attraper. L'ancien `pass` validait ces fichiers.
        return False

    return True


@_contextmanager
def _stage_dalle_part(chemin_final):
    """Crée un espace de staging voisin dont le nom finit par ``.part``.

    Le fichier qu'il contient conserve le basename/extension de la cible. C'est
    indispensable aux hooks provider qui reconnaissent les dalles par une regexp
    ``*.tif$`` ou construisent leurs temporaires avec ``with_suffix()``. Tous ces
    artefacts restent néanmoins confinés dans un dossier ``*.part`` ignoré par la
    synchronisation, et la cible finale n'est remplacée qu'après validation.
    """
    chemin_final = Path(chemin_final)
    dossier_part = _chemin_part(chemin_final)
    dossier_part.mkdir(parents=False, exist_ok=False)
    chemin_part = dossier_part / chemin_final.name
    try:
        yield chemin_part
    finally:
        shutil.rmtree(dossier_part, ignore_errors=True)


def _chemins_nuage_stage(chemin_final, chemin_part):
    """Retourne ``(nuage_final, nuage_stage)`` pour un provider LAZ, sinon
    ``(None, None)``.

    Quand ``cloud_cache_dir`` est désactivé (dossier forcé ou COPC fenêtré), le
    provider co-localise volontairement le nuage avec le TIF. Le dossier de
    staging changerait alors son emplacement sans cette correspondance.
    """
    _cloud_path = getattr(PROVIDER, "cloud_path", None)
    if not callable(_cloud_path):
        return None, None
    try:
        _final = _cloud_path(Path(chemin_final))
        _stage = _cloud_path(Path(chemin_part))
        return ((Path(_final) if _final is not None else None),
                (Path(_stage) if _stage is not None else None))
    except Exception:
        return None, None


def _lier_nuage_existant_au_stage(chemin_final, chemin_part):
    """Rend un nuage co-localisé existant visible au hook ``pre_download``.

    Un hardlink évite de recopier un LAZ de plusieurs centaines de Mo. Son
    retrait avec le dossier ``.part`` ne touche pas le cache final.
    """
    nuage_final, nuage_stage = _chemins_nuage_stage(chemin_final, chemin_part)
    if (nuage_final is None or nuage_stage is None
            or nuage_final == nuage_stage or not nuage_final.exists()
            or nuage_stage.exists()):
        return
    try:
        nuage_stage.parent.mkdir(parents=True, exist_ok=True)
        os.link(nuage_final, nuage_stage)
    except OSError:
        # Le hook ne trouvera simplement pas le cache et le téléchargement réseau
        # normal prendra le relais. Ne jamais recopier un énorme nuage ici.
        pass


def _publier_nuage_stage(chemin_final, chemin_part):
    """Publie atomiquement le nuage co-localisé produit dans le dossier .part.

    Le nuage est un cache indépendant et déjà complet à ce stade. S'il s'agit du
    hardlink posé pour ``pre_download``, seul le lien de staging est retiré.
    """
    nuage_final, nuage_stage = _chemins_nuage_stage(chemin_final, chemin_part)
    if (nuage_final is None or nuage_stage is None
            or nuage_final == nuage_stage or not nuage_stage.exists()):
        return
    nuage_final.parent.mkdir(parents=True, exist_ok=True)
    try:
        if nuage_final.exists() and os.path.samefile(nuage_stage, nuage_final):
            nuage_stage.unlink(missing_ok=True)
            return
    except OSError:
        pass
    nuage_stage.replace(nuage_final)


def _comprimer_dalle_deflate(chemin):
    """Recomprime une dalle GeoTIFF en DEFLATE (tiled) en place, best-effort.

    - Déjà compressée (DEFLATE/LZW, cas des COG fenêtrés) : no-op.
    - Predictor selon le dtype : 3 pour flottant (DEM float32), 2 pour entier.
    - Copie par blocs (block_windows) pour borner la RAM sur les grandes
      dalles (nl-ahn : ~300 Mo décompressé).
    - Sur échec, le fichier d'origine est conservé tel quel (warning).
    Appelée en fin de telecharger_dalle_directe quand --download-compress est
    actif, APRÈS post_fetch/post_download (qui peuvent réécrire le fichier)."""
    chemin = Path(chemin)
    tmp = _chemin_part(chemin)
    try:
        import rasterio as _rio_c
        with _rio_c.open(str(chemin)) as src:
            if (src.profile.get("compress") or "").lower() in ("deflate", "lzw"):
                return
            profile = src.profile.copy()
            profile.update({
                "compress":   "deflate",
                "predictor":  3 if src.dtypes[0].startswith("float") else 2,
                "tiled":      True,
                "blockxsize": 256,
                "blockysize": 256,
                "BIGTIFF":    "IF_SAFER",
            })
            with _rio_c.open(str(tmp), "w", **profile) as dst:
                for _ji, win in src.block_windows(1):
                    for b in range(1, src.count + 1):
                        dst.write(src.read(b, window=win), b, window=win)
        tmp.replace(chemin)
    except Exception as _e_cmp:
        tmp.unlink(missing_ok=True)
        print(f"  ⚠ compression skipped for {chemin.name}: "
              f"{type(_e_cmp).__name__}: {_e_cmp}", flush=True)


# Instrumentation R1#6 (LIDAR2MAP_LAZ_PROFILE=1) : mesure le temps-mur DOWNLOAD
# vs CONVERSION (post_fetch CSF/DFM) par dalle, pour décider du découplage des
# pools (aujourd'hui la conversion tourne DANS la tâche de download = pool
# partagé, donc --laz-parallel est bridé au plafond de download). No-op quand la
# variable n'est pas posée. Accumulateur thread-safe (appelé depuis le pool de dl).
_LAZ_PROFILE = os.environ.get(
    "LIDAR2MAP_LAZ_PROFILE", "").strip() not in ("", "0", "false", "False", "no")
_laz_prof_lock = threading.Lock()
_laz_prof = {"dl_n": 0, "dl_s": 0.0, "conv_n": 0, "conv_s": 0.0, "conv_max": 0.0}


def _laz_prof_add(dl_s=None, conv_s=None):
    """Accumule un temps de download et/ou de conversion (R1#6). No-op si off."""
    if not _LAZ_PROFILE:
        return
    with _laz_prof_lock:
        if dl_s is not None:
            _laz_prof["dl_n"] += 1
            _laz_prof["dl_s"] += dl_s
        if conv_s is not None:
            _laz_prof["conv_n"] += 1
            _laz_prof["conv_s"] += conv_s
            _laz_prof["conv_max"] = max(_laz_prof["conv_max"], conv_s)


def _laz_prof_resume(wall_s, n_dl_workers, laz_parallel):
    """Résumé profiling R1#6 : cumuls download/conversion, temps-mur ACTUEL (pool
    couplé) et borne théorique d'un modèle DÉCOUPLÉ pipeliné
    max(dl/workers, conv/laz_parallel). Le rapport des deux = gain potentiel."""
    if not _LAZ_PROFILE:
        return
    with _laz_prof_lock:
        p = dict(_laz_prof)
    if p["dl_n"] == 0 and p["conv_n"] == 0:
        return
    dl, conv = p["dl_s"], p["conv_s"]
    borne = max(dl / max(n_dl_workers, 1), conv / max(laz_parallel, 1))
    print(f"  [PROFILE R1#6] download {p['dl_n']} dalles, cumul {dl:.0f}s "
          f"({dl / max(p['dl_n'], 1):.1f}s/dalle) | conversion {p['conv_n']}, "
          f"cumul {conv:.0f}s ({conv / max(p['conv_n'], 1):.1f}s/dalle, "
          f"max {p['conv_max']:.1f}s)")
    print(f"  [PROFILE R1#6] mur actuel {wall_s:.0f}s @ {n_dl_workers} dl-workers, "
          f"laz_parallel={laz_parallel} | borne découplé ~{borne:.0f}s "
          f"(gain potentiel x{wall_s / max(borne, 1e-9):.1f})")


def telecharger_dalle_directe(nom, url_wms, dossier, ecraser=False, compresser=False):
    """Télécharge une dalle depuis son URL WMS fournie par le TMS IGN.

    compresser : recompression DEFLATE de la dalle après validation
    (--download-compress). Les COG fenêtrés (telecharger_cog_fenetre) sont
    déjà écrits compressés et n'ont pas besoin de ce paramètre."""
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser:
            return "skip"
        # Même en overwrite, conserver l'ancienne dalle valide jusqu'à la
        # publication atomique de sa remplaçante.
    for tentative in range(1, MAX_TENTATIVES + 1):
        with _stage_dalle_part(chemin) as chemin_part:
            try:
                # Hook pre_download (optionnel) : le provider peut matérialiser
                # la dalle SANS réseau depuis son nuage LAZ en cache. Le basename
                # reste identique dans le dossier .part, donc ses regexp *.tif$
                # continuent de fonctionner.
                _pre = (getattr(PROVIDER, "pre_download", None)
                        if (tentative == 1 and not ecraser) else None)
                _materialise = False
                if _pre is not None:
                    _lier_nuage_existant_au_stage(chemin, chemin_part)
                    try:
                        _materialise = bool(_pre(chemin_part)) and chemin_part.exists()
                    except Exception as _e_pre:
                        print(f"  WARN pre_download {nom}: "
                              f"{type(_e_pre).__name__}: {_e_pre}", flush=True)
                if not _materialise:
                    _t_dl = time.time()
                    taille = _download_to_tmp(
                        url_wms, chemin_part, timeout=(10, 45))
                    _laz_prof_add(dl_s=time.time() - _t_dl)   # R1#6 profiling
                    if taille == 0:
                        # 404 propre. Provider à découverte EXACTE (index WFS/
                        # STAC/registre : dalle promise) → erreur et retry.
                        if getattr(PROVIDER, "DISCOVER_EXACT", False):
                            raise IOError("HTTP 404 sur dalle indexée "
                                          "(provider à découverte exacte)")
                        return "absent"
                    if taille < SEUIL_DALLE_VALIDE:
                        with open(chemin_part, "rb") as _fh:
                            _head = _fh.read(200)
                        # Erreur serveur déguisée en HTTP 200 → retry.
                        if (_head.lstrip().startswith(b"{")
                                and b'"error"' in _head):
                            raise IOError(
                                f"server error payload: {_head[:120]!r}")
                        return "absent"
                    _t_cv = time.time()
                    _post_fetch_si_besoin(chemin_part)
                    _laz_prof_add(conv_s=time.time() - _t_cv)   # R1#6 profiling
                if not _valider_tif_dalle(chemin_part):
                    raise IOError(
                        "GeoTIFF invalide après écriture "
                        "(fichier tronqué ou corrompu)")
                # Hook post-download (reprojection/réétiquetage) sur le staging.
                if hasattr(PROVIDER, "post_download"):
                    try:
                        PROVIDER.post_download(chemin_part)
                    except Exception as _e_pd:
                        raise IOError(f"post_download {nom}: "
                                      f"{type(_e_pd).__name__}: {_e_pd}")
                    if not _valider_tif_dalle(chemin_part):
                        raise IOError(
                            f"GeoTIFF invalide après post_download ({nom})")
                if compresser:
                    _comprimer_dalle_deflate(chemin_part)
                    if not _valider_tif_dalle(chemin_part):
                        raise IOError(
                            f"GeoTIFF invalide après compression ({nom})")

                # Les éventuels caches LAZ co-localisés puis le TIF sont publiés
                # seulement après le succès de tous les hooks/validateurs.
                _publier_nuage_stage(chemin, chemin_part)
                chemin_part.replace(chemin)
                _creer_fichier(chemin)
                return "ok"
            except KeyboardInterrupt:
                # Le context manager supprime uniquement notre dossier .part.
                raise
            except Exception as _e:
                if tentative < MAX_TENTATIVES:
                    # Retry silencieux : seul l'échec final reste visible.
                    time.sleep(DELAI_RETRY)
                else:
                    print(f"\n  ERROR {nom} ({type(_e).__name__}, "
                          f"attempt {tentative}): {_e}")
                    return "erreur"
    return "erreur"


def _cog_cache_couvre(chemin, bbox_natif):
    """True si le GeoTIFF fenêtré déjà en cache `chemin` couvre ENTIÈREMENT
    `bbox_natif` (bbox demandée, en CRS_NATIF du provider).

    Les providers COG (ca-nrcan, us-tnm, nz-linz, gb-scotland) nomment le
    fichier local par ASSET distant, stable, alors que le CONTENU écrit est la
    fenêtre (intersection bbox∩COG). Sans ce contrôle, une 2e zone dans le même
    COG réutilisait le fragment de la 1re → relief faux servi en silence (#1).
    Conservateur : illisible ou bbox non couverte → False (re-télécharge)."""
    try:
        import rasterio as _rio
        with _rio.open(str(chemin)) as ds:
            b = ds.bounds
            fcrs = ds.crs.to_epsg() if ds.crs else None
        x1, y1, x2, y2 = bbox_natif
        ncrs = (int(PROVIDER.CRS_NATIF.split(":")[1])
                if ":" in getattr(PROVIDER, "CRS_NATIF", "") else None)
        if fcrs and ncrs and fcrs != ncrs:
            _tf = _get_transformer(PROVIDER.CRS_NATIF, f"EPSG:{fcrs}")
            x1, y1, x2, y2 = _bbox_enveloppe_transform(_tf.transform, x1, y1, x2, y2)
        tol = 1.0   # tolérance arrondi (1 unité CRS)
        return (b.left - tol <= min(x1, x2) and b.right + tol >= max(x1, x2)
                and b.bottom - tol <= min(y1, y2) and b.top + tol >= max(y1, y2))
    except Exception:
        return False


# #9 : au-delà de cette taille, la fenêtre COG est copiée par bandes de lignes
# (RAM bornée) au lieu d'un read unique. Le split a-priori borne déjà la bbox par
# chunk en pratique ; ce garde-fou protège le cas d'une bbox non splittée (petit
# provider COG, run mono-chunk) × plusieurs workers. 4096² px ≈ 67 Mo/bande f32.
_MAX_COG_WINDOW_PX = 4096 * 4096


# R1#10 : la conversion COPC-fenêtrée pose le CRS UTM PAR TUILE sur le provider
# PARTAGÉ (set_crs → self.crs_epsg), lu ensuite par post_fetch (las_to_dfm). En
# multi-UTM (couverture straddlant une frontière de zone UTM) deux tuiles
# concurrentes se corrompaient → las_to_dfm plantait sur _verifie_crs_las (le
# header LAS d'une tuile ne matche plus le CRS posé par l'autre). Ce lock rend le
# couple set_crs + post_fetch ATOMIQUE ; le DOWNLOAD (hors lock, vrai goulot des
# COPC = range-requests) reste parallèle. Ne sérialise QUE la conversion
# COPC-fenêtrée (ca-nrcan/us-3dep) ; les providers mono-zone posent leur CRS une
# fois à la découverte, hors de ce chemin.
_copc_crs_lock = threading.Lock()


def _copc_post_fetch_crs(epsg, chemin_part):
    """Pose le CRS UTM de la tuile puis convertit, sous _copc_crs_lock (R1#10).
    Extrait pour être testable (course de concurrence multi-UTM)."""
    _set = getattr(PROVIDER, "set_crs", None)
    with _copc_crs_lock:
        if _set and epsg:
            _set(int(epsg))
        _post_fetch_si_besoin(chemin_part)


def telecharger_copc_fenetre(nom, url, dossier_dalles, bbox, ecraser=False):
    """Lecture FENÊTRÉE d'un COPC distant (nuage LAZ octree, ex. ca-nrcan) :
    ne lit QUE les points de la bbox zone via range-requests, écrit le sous-
    ensemble, puis PROVIDER.post_fetch le convertit en GeoTIFF DFM/CSF. Évite de
    rapatrier un COPC entier (200-750 Mo) pour une petite zone. Le CRS (UTM PAR
    ZONE) est lu dans le header du COPC et posé sur le provider (set_crs) → sortie
    dans la bonne zone ; le warp du cœur lit ensuite le CRS du fichier produit.
    `bbox` = bbox zone en CRS_NATIF du provider."""
    from providers import common as _common
    chemin = chemin_dalle(dossier_dalles, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    _seuil = getattr(PROVIDER, "SEUIL_DALLE_VALIDE", SEUIL_DALLE_VALIDE)
    if chemin.exists() and chemin.stat().st_size > _seuil and not ecraser:
        return "skip"
    with _stage_dalle_part(chemin) as chemin_part:
        try:
            # bbox zone (CRS_NATIF) → WGS84 pour le fenêtrage COPC.
            bx1, by1, bx2, by2 = bbox
            lo1, la1, lo2, la2 = _bbox_enveloppe_transform(
                _natif_vers_wgs84, bx1, by1, bx2, by2)
            # Signature d'URL propre au provider (SAS courte durée, si besoin).
            _sign = getattr(PROVIDER, "sign_url", None)
            _url = _sign(url) if callable(_sign) else url
            n, epsg = _common.copc_window_to_las(
                _url, (lo1, la1, lo2, la2), chemin_part)
            if not n or n < 50_000:
                return "absent"      # zone hors de ce COPC (ou quasi vide)
            # R1#10 : CRS du run = zone UTM de la tuile, posé + converti sous lock
            # (self.crs_epsg est partagé ; 2 tuiles de zones UTM différentes le
            # corrompaient en concurrence). Le LAS puis sa conversion GeoTIFF
            # restent dans le dossier .part.
            _copc_post_fetch_crs(epsg, chemin_part)
            if not _valider_tif_dalle(chemin_part):
                raise IOError(
                    f"GeoTIFF COPC invalide après post_fetch ({nom})")
            _publier_nuage_stage(chemin, chemin_part)
            chemin_part.replace(chemin)
            _creer_fichier(chemin)
            return "ok"
        except KeyboardInterrupt:
            raise
        except Exception as _e:
            print(f"\n  ERROR COPC {nom} ({type(_e).__name__}): {_e}")
            return "erreur"


def telecharger_cog_fenetre(nom, url, dossier_dalles, bbox, ecraser=False):
    """Lecture FENÊTRÉE d'un COG distant (mosaïque régionale) via /vsicurl/.

    Pour les providers servant de grandes mosaïques COG (ex. ca-nrcan : un COG
    par levé couvrant des centaines de km²), télécharger le fichier entier pour
    une petite zone est prohibitif (Go + heures). Un COG (Cloud-Optimized
    GeoTIFF) supporte les requêtes HTTP par plage (range requests) + le tuilage
    interne : rasterio/GDAL lisent UNIQUEMENT la fenêtre bbox sans rapatrier le
    reste. On écrit un GeoTIFF local clippé à l'intersection (bbox zone ∩ COG).

    bbox : (x_min, y_min, x_max, y_max) en CRS natif du provider (= CRS du COG).
    Retourne "ok" / "skip" / "absent" (pas d'intersection) / "erreur".
    """
    import rasterio
    from rasterio.windows import from_bounds as _win_from_bounds, Window

    chemin = chemin_dalle(dossier_dalles, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser and _cog_cache_couvre(chemin, bbox):
            return "skip"
        # Overwrite ou fragment d'une autre zone : conserver l'ancien fichier
        # jusqu'à ce que sa nouvelle fenêtre soit intégralement validée.

    bx1, by1, bx2, by2 = bbox
    vsi = "/vsicurl/" + url
    for tentative in range(1, MAX_TENTATIVES + 1):
        with _stage_dalle_part(chemin) as chemin_part:
            try:
                # Options GDAL propres au provider (auth Basic, extensions VRT),
                # limitées à cet environnement.
                _prov_gdal = getattr(PROVIDER, "gdal_env_options", None)
                _gdal_extra = _prov_gdal() if callable(_prov_gdal) else {}
                _env_gdal = {
                    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
                    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
                    "VSI_CACHE": True,
                    "GDAL_HTTP_TIMEOUT": "60",
                }
                _env_gdal.update(_gdal_extra)
                with rasterio.Env(**_env_gdal):
                    with rasterio.open(vsi) as src:
                        # La bbox provider peut devoir être reprojetée vers le
                        # CRS réel du COG.
                        rbx1, rby1, rbx2, rby2 = bx1, by1, bx2, by2
                        try:
                            _se = src.crs.to_epsg() if src.crs else None
                            _ne = (int(PROVIDER.CRS_NATIF.split(":")[1])
                                   if ":" in getattr(
                                       PROVIDER, "CRS_NATIF", "") else None)
                            if _se and _ne and _se != _ne:
                                _tf = _get_transformer(
                                    PROVIDER.CRS_NATIF, f"EPSG:{_se}")
                                _xs, _ys = [], []
                                for _px, _py in (
                                        (bx1, by1), (bx1, by2),
                                        (bx2, by1), (bx2, by2)):
                                    _tx, _ty = _tf.transform(_px, _py)
                                    _xs.append(_tx)
                                    _ys.append(_ty)
                                rbx1, rby1 = min(_xs), min(_ys)
                                rbx2, rby2 = max(_xs), max(_ys)
                        except Exception:
                            pass
                        b = src.bounds
                        l = max(rbx1, b.left)
                        r = min(rbx2, b.right)
                        bot = max(rby1, b.bottom)
                        t = min(rby2, b.top)
                        if l >= r or bot >= t:
                            return "absent"
                        win = _win_from_bounds(l, bot, r, t, src.transform)
                        win_i = (win.round_offsets(op="floor")
                                 .round_lengths(op="ceil"))
                        win_h, win_w = int(win_i.height), int(win_i.width)
                        if win_h <= 0 or win_w <= 0:
                            return "absent"
                        if win_h * win_w > _MAX_COG_WINDOW_PX:
                            profil = src.profile.copy()
                            profil.update(
                                driver="GTiff",
                                height=win_h, width=win_w,
                                transform=src.window_transform(win_i),
                                compress="deflate", predictor=2, tiled=True,
                                blockxsize=256, blockysize=256,
                                bigtiff="IF_SAFER")
                            with rasterio.open(
                                    chemin_part, "w", **profil) as dst:
                                r0 = 0
                                while r0 < win_h:
                                    h = min(1024, win_h - r0)
                                    sub = Window(
                                        win_i.col_off, win_i.row_off + r0,
                                        win_w, h)
                                    dst.write(
                                        src.read(window=sub),
                                        window=Window(0, r0, win_w, h))
                                    r0 += h
                        else:
                            data = src.read(window=win)
                            if data.size == 0:
                                return "absent"
                            profil = src.profile.copy()
                            profil.update(
                                driver="GTiff",
                                height=data.shape[1], width=data.shape[2],
                                transform=src.window_transform(win),
                                compress="deflate", predictor=2, tiled=True,
                                blockxsize=256, blockysize=256,
                                bigtiff="IF_SAFER")
                            with rasterio.open(
                                    chemin_part, "w", **profil) as dst:
                                dst.write(data)
                if not _valider_tif_dalle(chemin_part):
                    raise IOError("COG fenêtré invalide après écriture")
                # Reprojection/réétiquetage également confinés dans .part.
                if hasattr(PROVIDER, "post_download"):
                    try:
                        PROVIDER.post_download(chemin_part)
                    except Exception as _e_pd:
                        raise IOError(f"post_download {nom}: "
                                      f"{type(_e_pd).__name__}: {_e_pd}")
                    if not _valider_tif_dalle(chemin_part):
                        raise IOError(
                            f"GeoTIFF invalide après post_download ({nom})")
                chemin_part.replace(chemin)
                _creer_fichier(chemin)
                return "ok"
            except KeyboardInterrupt:
                raise
            except Exception as _e:
                if tentative < MAX_TENTATIVES:
                    time.sleep(DELAI_RETRY)
                else:
                    print(f"\n  ERROR window {nom} "
                          f"({type(_e).__name__}): {_e}")
                    return "erreur"
    return "erreur"


# NB : l'ancienne telecharger_dalle(x_km, y_km, ...) (grille interne +
# construire_url_wms) a été supprimée : plus appelée depuis le refactor
# multi-provider, toutes les URLs viennent de PROVIDER.discover_dalles.
# Sa gestion de --download-compress vit désormais dans
# _comprimer_dalle_deflate, appliquée par telecharger_dalle_directe.

# ============================================================
# ASSEMBLAGE COG (rasterio)
# ============================================================


from _ombrages_pures import (
    SVF_GAMMA,
    _NUMBA_KERNELS_CACHE,   # noqa: F401 - réexport de façade, muté directement par les tests
    _stop_event,
    _build_vrt_xml as _build_vrt_xml_impl,
    _get_numba_svf_opos_kernel,   # noqa: F401 - réexport de façade, testé directement
    _hillshade_chunked,
    _hillshade_chunked_multi,
    _hillshade_multi_numpy,       # noqa: F401 - réexport de façade, testé directement
    _hillshade_numpy,             # noqa: F401 - réexport de façade, testé directement
    _lire_dem_rasterio,
    _lrm_array,
    _lrm_chunked,
    _nodata_mask,                  # noqa: F401 - réexport de façade, testé directement
    _publier_tif_atomique as _publier_tif_atomique_impl,
    _rrim_chunked,
    _sauver_array_georef as _sauver_array_georef_impl,
    _slope_numpy,                 # noqa: F401 - réexport de façade, testé directement
    _source_a_des_donnees,
    _svf_chunked,
    _svf_numpy,
    _svf_opos_chunked,
)


def _sauver_array_georef(arr, src_tif, dst_tif):
    """Façade compatible : injecte le formateur de durée courant."""
    return _sauver_array_georef_impl(arr, src_tif, dst_tif, formater_duree=_hms)


def _publier_tif_atomique(chemin_part, chemin_final):
    """Façade compatible : injecte le validateur TIFF courant (contrat
    historique des suites qui monkeypatchent `_valider_tif_dalle`)."""
    return _publier_tif_atomique_impl(
        chemin_part, chemin_final, valider_tif=_valider_tif_dalle)


def _build_vrt_xml(cogs, vrt_path, target_res):
    """Façade compatible : injecte l'écriture atomique de texte courante."""
    return _build_vrt_xml_impl(
        cogs, vrt_path, target_res,
        ecrire_texte_atomique=_ecrire_texte_atomique)



from _ombrages_provider import (
    _DependancesFetchProvider,
    _e4mstp_compose,
    _extraire_tiff_multipart as _extraire_tiff_multipart_impl,
    _fetch_provider_shadings as _fetch_provider_shadings_impl,
    _mstp_chunked,
    _post_fetch_si_besoin as _post_fetch_si_besoin_impl,
    _vat_compose,
)


def _extraire_tiff_multipart(chemin):
    """Façade compatible : injecte la taille de chunk HTTP courante."""
    return _extraire_tiff_multipart_impl(chemin, http_chunk_size=HTTP_CHUNK_SIZE)


def _post_fetch_si_besoin(chemin):
    """Façade compatible : injecte le provider actif et la désencapsulation
    multipart courante (contrat historique des suites qui monkeypatchent
    `_extraire_tiff_multipart` puis appellent une fonction qui en dépend)."""
    return _post_fetch_si_besoin_impl(
        chemin, provider=PROVIDER, extraire_tiff_multipart=_extraire_tiff_multipart)


def _dependances_fetch_provider():
    """Reconstruit les coutures du fetch provider à chaque appel."""
    return _DependancesFetchProvider(
        provider=PROVIDER,
        extraire_tiff_multipart=_extraire_tiff_multipart,
        chemin_part=_chemin_part,
        creer_fichier=_creer_fichier,
        formater_duree=_hms,
        valider_tif=_valider_tif_dalle,
        normaliser_nom=normaliser_nom,
        http_chunk_size=HTTP_CHUNK_SIZE,
    )


def _fetch_provider_shadings(choix, bbox_natif, dossier_ville, nom_zone,
                              ecraser_ombrages, provides_shadings):
    """Façade compatible vers le fetch d'ombrages provider extrait."""
    return _fetch_provider_shadings_impl(
        choix, bbox_natif, dossier_ville, nom_zone,
        ecraser_ombrages, provides_shadings,
        dependances=_dependances_fetch_provider(),
    )




from _shading_specs import (
    SHADING_TOUS,
    SHADING_TYPES_ORDRE,
    _SHADING_TYPES,
    _resoudre_preset_shading,
    parser_shading_spec,
)


def generer_ombrages(cogs, dossier_ville, choix=None, elevation_soleil=None, nom_zone=None, ecraser_ombrages=False, ecraser_tuiles=False, use_sweep=False, svf_gamma=None, svf_conv=None, svf_dist=None, bbox_natif=None, instances=None):
    """
    Génère les ombrages depuis le VRT/COG source (MNT EPSG:2154).

    Types gdaldem  : 315, 045, 135, 225, multi, slope
    Types numpy/scipy (sans WhiteboxTools) :
        svf  — Sky-View Factor paramétrique (conv flux cos²γ / rvt 1−sin γ,
               distance svf_dist, gamma svf_gamma) : micro-relief, fossés, murs
        opos — Openness positive (Yokoyama 2002, rayon/gamma du SVF) : crêtes
        oneg — Openness négative inversée : fossés/chemins creux sombres
        rrim — Red Relief Image Map  : composite RGB couleur (R=pente, G=B=LRM)
        lrm  — Local Relief Model    : SLRM = DEM − gaussienne(σ auto 15 pixels
               natifs, ou valeur explicite en mètres) — scipy requis
        vat  — Visualization for Archaeological Topography : variante VAT-style
               en niveaux de gris, SVF + openness positif + pente
        e4mstp — Multiscale Topographic Position, enhanced version 4 : variante
               lidar2map multi-échelle (SVF, O+/O−, pente, MSTP et deux SLRM)

    Deux chemins d'entrée, cumulables :
      choix     : liste de TYPES (--shadings, GUI historique) — chaque type
                  devient une instance aux paramètres GLOBAUX ci-dessous ;
      instances : liste (type, params explicites) du flag répétable
                  --shading TYPE:cle=val,... (cf. parser_shading_spec) —
                  permet plusieurs instances du même type (svf 20 m + 100 m).
    Les suffixes de fichier sont normalisés et certains paramètres sont arrondis.
    Si deux instances aboutissent au même nom, la première sortie est conservée.

    elevation_soleil : angle solaire des hillshades directionnels (défaut: 25°).
    svf_conv  : "flux" (cos²γ, contraste) ou "rvt" (1−sin γ, archéo).  Défaut flux.
    svf_dist  : rayon SVF/openness en mètres (GUI : 10–200).  Défaut 20.
    svf_gamma : gamma après stretch (défaut: SVF_GAMMA ; miroir pour oneg).
    use_sweep : kernel sweep-horizon (SVF uniquement).
    SVF/LRM/RRIM : implémentés en numpy/scipy — aucun outil externe requis.
    """

    if elevation_soleil is None:
        elevation_soleil = ELEVATION_SOLEIL
    if svf_gamma is None:
        svf_gamma = SVF_GAMMA
    if svf_conv is None:
        svf_conv = "flux"
    if svf_dist is None:
        svf_dist = 20.0

    if choix is None:
        choix = ["315", "045", "135", "225", "multi", "slope"]

    if isinstance(cogs, Path):
        cogs = [cogs]

    # Aucune dalle valide pour ce chunk (hors couverture IGN, ou
    # téléchargements tous en échec). On retourne proprement plutôt que
    # de planter sur `sources[0]` plus bas — la boucle des chunks
    # poursuit avec les morceaux suivants. Le chunk ne produira pas
    # de .tif d'ombrage donc pas de mbtiles non plus.
    if not cogs:
        print("  ⚠ No tile available in this chunk "
              "(outside LiDAR coverage or downloads failed), "
              "shadings skipped.", flush=True)
        return []

    # Ombrages precalcules fournis par le provider (PROVIDES_SHADINGS) :
    # telecharges directement depuis le WCS du provider (ex. Digitaal Vlaanderen
    # SVF/Hillshade 25cm) AVANT la resolution en instances, pour que les cles
    # ainsi servies soient retirees de choix et NON recalculees localement.
    # Seules les instances "par defaut" (issues de choix) sont servies — une
    # instance --shading aux params explicites est toujours calculee localement.
    _cles_provider = []   # clés servies par le provider (pour la liste des cibles)
    if bbox_natif is not None and hasattr(PROVIDER, "PROVIDES_SHADINGS") and choix:
        _choix_avant = list(choix)
        choix = list(choix)
        _fetch_provider_shadings(
            choix, bbox_natif, dossier_ville, nom_zone, ecraser_ombrages,
            PROVIDER.PROVIDES_SHADINGS
        )
        _cles_provider = [c for c in _choix_avant if c not in choix]

    # ── Résolution en instances (typ, params_explicites, params_résolus, suffixe)
    # Le suffixe encode un param uniquement s'il est EXPLICITE et différent du
    # défaut canonique : les noms historiques (multi_ombrage, lrm_ombrage…)
    # restent inchangés aux réglages par défaut → caches préservés.
    HORN_TYPES     = ("315", "045", "135", "225", "multi", "slope")
    sigma_defaut_m = 15 * RESOLUTION_M   # = 15 px quel que soit le provider (compat)

    def _resoudre_params(typ, prm):
        p = dict(prm or {})
        if typ in ("315", "045", "135", "225", "multi"):
            p.setdefault("elevation", float(elevation_soleil))
        if typ == "svf":
            p.setdefault("conv", "rvt" if str(svf_conv).lower() == "rvt" else "flux")
        if typ in ("svf", "opos", "oneg"):
            p.setdefault("dist", float(svf_dist))
            p.setdefault("gamma", float(svf_gamma))
        if typ == "vat":
            # dist = rayon SVF/openness ; gamma = gamma FINAL du composite,
            # défaut = --svf-gamma comme SVF (les composantes entrent linéaires
            # dans le blend → pas de double gamma).
            p.setdefault("dist", float(svf_dist))
            p.setdefault("gamma", float(svf_gamma))
        if typ == "e4mstp":
            # gamma FINAL du composite couleur : défaut 0.8 (éclaircit),
            # PAS svf_gamma (2.0 par défaut écraserait un composite déjà blendé,
            # rendu très sombre). Le blend interne porte déjà le contraste.
            p.setdefault("dist", float(svf_dist))
            p.setdefault("gamma", 0.8)
        if typ in ("lrm", "rrim"):
            p.setdefault("sigma", float(sigma_defaut_m))
        return p

    def _suffixe_instance(typ, prm, p):
        def _tag(v):
            return f"{v:g}".replace(".", "p").replace("-", "m")
        if typ == "slope":
            return "slope_ombrage"
        if typ in ("315", "045", "135", "225", "multi"):
            if "elevation" in (prm or {}) and p["elevation"] != ELEVATION_SOLEIL:
                return f"{typ}_e{_tag(p['elevation'])}_ombrage"
            return f"{typ}_ombrage"
        if typ in ("svf", "opos", "oneg"):
            gtag = f"{p['gamma']:.1f}".replace(".", "p")
            base = (f"svf_{p['conv']}" if typ == "svf" else typ)
            return f"{base}_{int(round(p['dist']))}m_g{gtag}_ombrage"
        if typ in ("vat", "e4mstp"):
            if prm:   # params explicites → encoder dist/gamma, sinon nom canonique
                gtag = f"{p['gamma']:.1f}".replace(".", "p")
                return f"{typ}_{int(round(p['dist']))}m_g{gtag}_ombrage"
            return f"{typ}_ombrage"
        # lrm / rrim : encode sigma dès qu'il est explicite (comme svf/opos/vat),
        # pour que le nom porte toujours l'échelle. Bare `--shading lrm` (sans
        # sigma) reste canonique `lrm_ombrage`.
        if "sigma" in (prm or {}):
            return f"{typ}_s{_tag(p['sigma'])}m_ombrage"
        return f"{typ}_ombrage"

    insts, _vus = [], {}
    for typ, prm in ([(t, {}) for t in choix] + list(instances or [])):
        if typ not in _SHADING_TYPES:
            print(f"  ⚠ unknown shading type ignored: {typ}")
            continue
        p = _resoudre_params(typ, prm)
        sfx = _suffixe_instance(typ, prm, p)
        if sfx in _vus:
            # Le nom encodé est volontairement grossier (mètres entiers, gamma
            # à une décimale) : deux réglages distincts peuvent retomber sur le
            # même suffixe. Si les params diffèrent réellement, on prévient au
            # lieu d'abandonner en silence (le second serait un fichier écrasant
            # le premier). Sinon c'est un vrai doublon → silencieux.
            if _vus[sfx] != (typ, p):
                print(f"  ⚠ shading '{typ}' {prm} collapses to the same name "
                      f"'{sfx}' as an earlier setting; keeping the first, "
                      f"ignoring this one")
            continue
        _vus[sfx] = (typ, p)
        insts.append((typ, p, sfx))

    horn_insts  = [i for i in insts if i[0] in HORN_TYPES]
    numpy_insts = [i for i in insts if i[0] not in HORN_TYPES]

    # ── Construction VRT global (seamless, évite jointures gdaldem) ─────────
    # VRT dans un dossier de transaction unique finissant par .part sous
    # dossier_ville : la synchronisation distante ignore tout le chantier.
    import shutil as _shutil_vrt
    _vrt_tmpdir = None
    # ── Merge des dalles via rasterio (remplace gdalbuildvrt + gdal_translate) ──
    # Au lieu de produire un VRT puis de le convertir en GeoTIFF avec
    # gdal_translate, on fait un merge direct rasterio en GeoTIFF compressed.
    # Avantages : un seul passage, plus de dépendance à GDAL CLI, sortie
    # immédiatement utilisable par numpy (les hillshades sont calculés ensuite
    # en numpy, cf. étape ombrage).
    if len(cogs) > 1:
        _vrt_tmpdir = _chemin_part(dossier_ville / "_tmp")
        _vrt_tmpdir.mkdir(parents=True, exist_ok=True)
        # VRT XML : vue logique sur les dalles, ~200 o/dalle, construction <1 s.
        # Évite la matérialisation d'une mosaïque physique multi-Go (le merge
        # rasterio sur 2000+ dalles avec compression deflate est pathologique).
        # rasterio lit le VRT transparemment via libgdal — les calculs chunked
        # en aval reçoivent leurs fenêtres comme depuis un raster ordinaire.
        vrt_path      = _vrt_tmpdir / "_mnt_complet.vrt"
        filelist_path = _vrt_tmpdir / "_dalles.txt"
        try:
            filelist_path.write_text(
                "\n".join(str(c) for c in cogs), encoding="utf-8")
            _creer_fichier(filelist_path)
            print(f"  Building VRT ({len(cogs)} tiles)...", flush=True)
            _t0_vrt = time.time()
            _build_vrt_xml(cogs, vrt_path, RESOLUTION_M)
            _creer_fichier(vrt_path)
            print(f"  VRT OK  ({_hms(time.time()-_t0_vrt)}, "
                  f"{vrt_path.stat().st_size // 1024} Ko)", flush=True)
            sources = [vrt_path]
        except BaseException as e:
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            # Hard-fail au lieu du fallback `sources = cogs` : sources[0] ne
            # garderait que la 1ère dalle, produisant un MBTiles vide.
            raise RuntimeError(
                f"Construction VRT échouée : {e}\n"
                f"  → vérifier l'accès disque sur {_vrt_tmpdir}"
            ) from e
    else:
        sources = cogs

    source   = sources[0]
    nom_base = normaliser_nom(nom_zone) if nom_zone else normaliser_nom(dossier_ville.name)

    # Garde-fou zone tout-nodata : si le DEM assemble n'a aucun pixel d'altitude
    # valide, tous les kernels sont inutiles (et le SVF planterait sur un
    # percentile de tableau vide). On saute les ombrages avec un message clair
    # plutot qu'un traceback. Vider les listes suffit : les deux boucles ne
    # s'executent pas et le nettoyage de fin a quand meme lieu.
    if (horn_insts or numpy_insts) and not _source_a_des_donnees(source):
        print("  WARNING: no valid elevation data in the zone "
              "(tiles are entirely nodata).")
        print("  Likely cause: no LiDAR data published here yet, or the tile "
              "index was unavailable at download time (empty tiles fetched).")
        print("  Shadings skipped.")
        horn_insts  = []
        numpy_insts = []

    # Chaque sortie demandée est d'abord écrite dans un nom unique finissant
    # par .part. Le final éventuellement présent reste lisible pendant tout le
    # recalcul et n'est remplacé qu'après fermeture + validation.
    _parts_ombrages_actifs = {}
    _sorties_a_regenerer = set()

    def _preparer_sortie_ombrage(chemin_final):
        chemin_part = _chemin_part(chemin_final)
        _parts_ombrages_actifs[chemin_part] = chemin_final
        _sorties_a_regenerer.add(chemin_final)
        return chemin_part

    def _abandonner_sortie_ombrage(chemin_part):
        chemin_final = _parts_ombrages_actifs.pop(chemin_part, None)
        if chemin_part.exists():
            chemin_part.unlink(missing_ok=True)
            nom_affiche = chemin_final.name if chemin_final else chemin_part.name
            print(f"  Partial file removed: {nom_affiche}")

    def _publier_sortie_ombrage(chemin_part, chemin_final):
        _publier_tif_atomique(chemin_part, chemin_final)
        _parts_ombrages_actifs.pop(chemin_part, None)
        _sorties_a_regenerer.discard(chemin_final)

    try:
        # ── Hillshades numpy chunked (RAM bornée — voir _hillshade_chunked_multi)
        # Traitement par fenêtres 2048×2048 px avec halo 1 px (Horn 3x3).
        # Tous les types demandés sont calculés en UNE passe de lecture :
        # sur une grande zone le coût dominant est l'I/O + décompression
        # deflate des dalles derrière le VRT, pas les kernels.
        if horn_insts:
            jobs_h = []
            publications_h = []
            for typ_h, p_h, sfx_h in horn_insts:
                nom_fichier = nom_base + "_" + sfx_h + ".tif"
                chemin_out  = dossier_ville / nom_fichier
                if chemin_out.exists() and not ecraser_ombrages:
                    print("  " + nom_fichier.ljust(56) + " -> already present")
                    continue
                chemin_part = _preparer_sortie_ombrage(chemin_out)
                publications_h.append((chemin_part, chemin_out))
                if typ_h == "multi":
                    jobs_h.append(("hillshade_multi",
                                   {"altitude_deg": float(p_h["elevation"])},
                                   chemin_part))
                elif typ_h == "slope":
                    jobs_h.append(("slope", {}, chemin_part))
                else:
                    jobs_h.append(("hillshade",
                                   {"azimuth_deg":  float(int(typ_h)),
                                    "altitude_deg": float(p_h["elevation"])},
                                   chemin_part))

            if jobs_h:
                print(f"  Hillshades chunked: {len(jobs_h)} type(s),"
                      f" single read pass...", flush=True)
                t0_hill = time.time()
                try:
                    ok_h = _hillshade_chunked_multi(
                        Path(str(source)), jobs_h,
                        dx=RESOLUTION_M, dy=RESOLUTION_M)
                    if not ok_h:
                        raise RuntimeError("chunked failed (rasterio absent ?)")
                    for chemin_part, chemin_out in publications_h:
                        _publier_sortie_ombrage(chemin_part, chemin_out)
                        _creer_fichier(chemin_out)
                        print(f"  {chemin_out.name.ljust(56)}"
                              f"  {_hms(int(time.time() - t0_hill))}"
                              f"  {chemin_out.stat().st_size / 1e6:.0f} Mo")
                except BaseException as e_hill:
                    # Fichiers partiellement écrits (structurellement valides
                    # mais incomplets) → supprimer, sinon ils seraient pris
                    # pour des caches sains au prochain lancement (même
                    # logique que le SVF).
                    for chemin_part, _chemin_out in publications_h:
                        _abandonner_sortie_ombrage(chemin_part)
                    if isinstance(e_hill, (KeyboardInterrupt, SystemExit)):
                        raise
                    print(f"\n  ERROR hillshades chunked: {e_hill}")

        # ── SVF / openness / LRM / RRIM — numpy/scipy ────────────────────────
        # NB : rasterio.merge (étape 2 du refactor) produit déjà un GeoTIFF
        # directement utilisable par numpy/PIL/rasterio en aval. Plus aucune
        # conversion intermédiaire VRT→GTiff nécessaire.
        src_str = str(source)

        for cle, p_i, sfx_i in numpy_insts:
            # Cancellation propre entre 2 ombrages : si l'utilisateur a fait
            # Ctrl+C pendant le précédent (kernel Numba intuable), l'ombrage
            # courant a été sauvegardé mais on n'enchaîne pas le suivant.
            if _stop_event.is_set():
                print("  Interruption - remaining shadings skipped.")
                break

            # Params résolus de L'INSTANCE (et plus des args globaux) : deux
            # instances du même type avec des réglages différents coexistent,
            # le suffixe sfx_i encodant les params.
            if cle in ("svf", "opos", "oneg"):
                _svf_dist_px = max(1, int(round(p_i["dist"] / RESOLUTION_M)))
                _gamma_i     = float(p_i["gamma"])
                # sweep par instance (svf:sweep=0|1) ; défaut = --svf-sweep
                # global. Pas encodé dans le nom : même produit, autre kernel.
                _sweep_i = (bool(p_i["sweep"]) if "sweep" in p_i else use_sweep)
                if cle == "svf":
                    _svf_conv_str = p_i["conv"]
                    _svf_conv_i   = 1 if _svf_conv_str == "rvt" else 0
                else:
                    _svf_conv_str = cle   # libellé pour les prints
                    _svf_conv_i   = 2 if cle == "opos" else 3
            elif cle in ("lrm", "rrim"):
                _sigma_px = max(1, int(round(p_i["sigma"] / RESOLUTION_M)))

            nom_fichier  = nom_base + "_" + sfx_i + ".tif"
            chemin_out   = dossier_ville / nom_fichier

            if chemin_out.exists() and not ecraser_ombrages:
                print("  " + nom_fichier.ljust(56) + " -> already present")
                continue
            chemin_part = _preparer_sortie_ombrage(chemin_out)

            t0_numpy = time.time()

            if cle in ("svf", "opos", "oneg"):
                # ── SVF / openness chunked (RAM bornée) ──────────────────────
                # Traitement par fenêtres 2048×2048 avec halo = max_dist_px.
                # Permet de traiter des zones de département entier sans OOM.
                max_dist_px  = _svf_dist_px
                n_directions = 16
                conv = _svf_conv_i
                dist_m = max_dist_px * RESOLUTION_M
                _lbl_svf = "SVF" if cle == "svf" else f"Openness {cle}"
                print(f"  {_lbl_svf} chunked ({n_directions} dir, rayon {dist_m:.0f} m"
                      f" = {max_dist_px} px, conv={_svf_conv_str}, gamma={_gamma_i:g})...", flush=True)
                try:
                    ok = _svf_chunked(
                        src_path     = Path(src_str),
                        dst_path     = chemin_part,
                        max_dist_px  = max_dist_px,
                        n_directions = n_directions,
                        resolution   = RESOLUTION_M,
                        gamma        = _gamma_i,
                        use_sweep    = _sweep_i,
                        conv         = conv,
                    )
                    if not ok:
                        # Repli pleine mémoire (numba absent ou échantillon
                        # trop petit) — limité aux zones modestes.
                        import numpy as np
                        # Garde OOM : le fallback charge le DEM entier + plusieurs
                        # tableaux pleine taille par direction (ThreadPool). Au-delà
                        # d'un seuil on refuse plutôt que de risquer l'OOM sur une
                        # grande zone sans numba.
                        _MAX_SVF_FULLMEM_PX = 6000 * 6000   # ~36 Mpx (~3 km à 0,5 m)
                        try:
                            import rasterio as _rio_sz
                            with _rio_sz.open(src_str) as _dsz:
                                _npx = _dsz.width * _dsz.height
                        except Exception:
                            _npx = 0
                        if _npx > _MAX_SVF_FULLMEM_PX:
                            print(f"  SVF: numba unavailable and zone too large "
                                  f"({_npx / 1e6:.0f} Mpx) for the full-memory "
                                  f"fallback. Install numba, or split the zone "
                                  f"with --split-cols/--split-rows.", flush=True)
                            continue
                        print("  SVF chunked KO → fallback to full memory", flush=True)
                        dem_arr, _nd = _lire_dem_rasterio(src_str)
                        arr_svf = _svf_numpy(dem_arr, max_dist_px, n_directions,
                                             RESOLUTION_M, use_sweep=_sweep_i,
                                             conv=conv, nodata=_nd)
                        # > 0 strict : les nodata valent exactement 0.0 et
                        # tireraient p2 vers 0 (stretch délavé).
                        svf_valid = arr_svf[arr_svf > 0]
                        if svf_valid.size == 0:
                            print("  SVF: no valid pixel (nodata zone), shading skipped")
                            continue
                        p2  = float(np.percentile(svf_valid, 2))
                        p98 = float(np.percentile(svf_valid, 98))
                        if p98 > p2:
                            arr_stretched = np.clip((arr_svf - p2) / (p98 - p2), 0, 1)
                        else:
                            arr_stretched = np.clip(arr_svf, 0, 1)
                        if conv == 3:
                            # Gamma miroir pour l'openness négative inversée
                            # (cf. _svf_chunked) : creux renforcés, fond clair.
                            arr_u8 = ((1.0 - (1.0 - arr_stretched) ** _gamma_i)
                                      * 255).astype(np.uint8)
                        else:
                            arr_u8 = (arr_stretched ** _gamma_i * 255).astype(np.uint8)
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_part)
                except Exception as e_svf:
                    import traceback as _tb
                    print(f"  ERROR SVF: {e_svf}")
                    print("  --- full traceback ---")
                    _tb.print_exc()
                    print("  ---------------------------")
                    # Supprimer le fichier partiellement écrit : _svf_chunked
                    # écrit chunk par chunk via rasterio. Si une exception
                    # survient au milieu, le TIF résultant est incomplet (ex :
                    # 109 MB au lieu de 300 MB) mais structurellement valide.
                    # Sans suppression, le tuileur l'accepte et produit 0 tuile
                    # silencieusement. Sur le prochain lancement, le fichier
                    # "already present" est réutilisé → bug persistant.
                    _abandonner_sortie_ombrage(chemin_part)
                    continue

            elif cle == "lrm":
                # ── Local Relief Model — filtre gaussien ─────────────────────
                # LRM = DEM − gaussienne(σ) → normalisation p5-p95 → uint8 (128=plat)
                # Traitement par blocs avec overlap pour borner la RAM :
                #   chemin 1 : _lrm_chunked() si rasterio + scipy disponibles
                #   chemin 2 : pleine mémoire (fallback)
                sigma_px = _sigma_px   # défaut 15 px ; --shading lrm:sigma=M en mètres
                print(f"  LRM gaussien (σ={sigma_px} px = {sigma_px * RESOLUTION_M:.0f} m)"
                      f" — peut prendre 3-7 min...", flush=True)

                # ── Chemin 1 : traitement chunké (RAM bornée) ───────────────
                _lrm_ok = _lrm_chunked(
                    src_path = Path(src_str),
                    dst_path = chemin_part,
                    sigma_px = sigma_px,
                )

                if not _lrm_ok:
                    # ── Chemin 2 : fallback pleine mémoire ─────────────────
                    try:
                        import numpy as np
                        dem_arr, _nd_val = _lire_dem_rasterio(src_str)
                        lrm, nodata_mask = _lrm_array(dem_arr, _nd_val, sigma_px)
                        lrm_valid = lrm[np.isfinite(lrm)]
                        p1  = float(np.percentile(lrm_valid,  5))
                        p99 = float(np.percentile(lrm_valid, 95))
                        if p99 > p1:
                            arr_f     = np.clip((lrm - p1) / (p99 - p1), 0, 1) * 255
                            clip_info = f"p5={p1:.2f}m p95={p99:.2f}m"
                        else:
                            clip_val  = max(0.1, 2.0 * float(np.nanstd(lrm)))
                            arr_f     = (np.clip(lrm, -clip_val, clip_val) + clip_val) / (2 * clip_val) * 255
                            clip_info = f"±{clip_val:.2f}m (σ fallback)"
                        arr_u8 = arr_f.astype(np.uint8)
                        arr_u8[nodata_mask] = 128
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_part)
                        _lrm_ok = True
                        print(f"  LRM scipy (full memory): σ={sigma_px} px, {clip_info}")
                    except ImportError:
                        print("  scipy missing - LRM skipped (pip install scipy)", flush=True)
                        continue
                    except Exception as e_scipy:
                        print(f"  ERROR scipy LRM: {e_scipy}")
                        continue

            elif cle == "rrim":
                # ── Red Relief Image Map (RRIM) ───────────────────────────────
                # Composite RGB couleur — Chiba et al. (2008), standard
                # archéo-LiDAR européen :
                #   R = pente, rampe ABSOLUE 0–45° + gamma 0.7 (relief en
                #       amplitude, comparable d'une zone à l'autre)
                #   G = B = LRM normalisé p5–p95 + gamma 0.8 (micro-relief ;
                #       choisi plutôt que le SVF du RRIM canonique : sur
                #       terrain ouvert SVF ≈ 0.97 partout → dominance bleue)
                # Révèle simultanément creux ET bosses — optimal prospection.
                print("  RRIM: Red Relief Image Map (slope × LRM)"
                      ", may take 5-10 min...", flush=True)

                sigma_rrim = _sigma_px   # défaut 15 px ; --shading rrim:sigma=M en mètres

                # Slope temporaire (réutilisé si already present)
                slope_rrim_path = dossier_ville / (nom_base + "_slope_ombrage.tif")
                slope_tmp_path  = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp")
                )
                _slope_src = None
                try:
                    if slope_rrim_path.exists():
                        _slope_src = slope_rrim_path
                        print("  RRIM: existing slope reused", flush=True)
                    else:
                        # Slope chunked (RAM bornée) — même moteur que
                        # l'ombrage slope standalone.
                        try:
                            ok_sl = _hillshade_chunked(
                                Path(src_str), slope_tmp_path, "slope", {},
                                dx=RESOLUTION_M, dy=RESOLUTION_M)
                            if not ok_sl:
                                raise RuntimeError(
                                    "slope chunked failed (rasterio absent ?)")
                            _slope_src = slope_tmp_path
                        except Exception as _e_sl:
                            print(f"  ERROR slope for RRIM: {_e_sl}")
                            continue

                    # ── Chemin 1 : composite chunked (RAM bornée) ───────────
                    try:
                        ok_rrim = _rrim_chunked(
                            Path(src_str), _slope_src, chemin_part,
                            sigma_px=sigma_rrim)
                    except Exception as e_rrim:
                        print(f"  ERROR composite RRIM: {e_rrim}")
                        # Fichier partiellement écrit → supprimer (sinon pris
                        # pour un cache sain au prochain lancement).
                        _abandonner_sortie_ombrage(chemin_part)
                        continue

                    if not ok_rrim:
                        # ── Chemin 2 : fallback pleine mémoire ──────────────
                        # (rasterio/scipy absent, ou échantillon dégénéré) —
                        # limité aux zones modestes.
                        try:
                            import numpy as np

                            slope_arr, _ = _lire_dem_rasterio(str(_slope_src))
                            dem_rrim, _nd_rr = _lire_dem_rasterio(src_str)
                            lrm_r, nd_mask_r = _lrm_array(dem_rrim, _nd_rr,
                                                          sigma_rrim)

                            # Aligner dimensions
                            h = min(slope_arr.shape[0], lrm_r.shape[0])
                            w = min(slope_arr.shape[1], lrm_r.shape[1])
                            slope_arr = slope_arr[:h, :w]
                            lrm_r     = lrm_r[:h, :w]
                            nd_mask_r = nd_mask_r[:h, :w]

                            # R : pente décodée (uint8 1–255 → 0–90°), rampe
                            # absolue 0–45° + gamma 0.7 (cf. _rrim_chunked).
                            slope_deg = np.clip(slope_arr - 1.0, 0.0, None) \
                                        * (90.0 / 254.0)
                            r_chan = (np.clip(slope_deg / 45.0, 0, 1) ** 0.7
                                      * 255).astype(np.uint8)

                            # G = B : LRM normalisé p5–p95, gamma 0.8
                            # LRM > 0 = élévation → clair ; < 0 = creux → foncé
                            lrm_valid = lrm_r[np.isfinite(lrm_r)]
                            if len(lrm_valid) == 0:
                                raise RuntimeError("LRM vide (tout nodata)")
                            lo = float(np.percentile(lrm_valid, 5))
                            hi = float(np.percentile(lrm_valid, 95))
                            if hi > lo:
                                lrm_n = np.clip((lrm_r - lo) / (hi - lo), 0, 1)
                            else:
                                lrm_n = np.zeros_like(lrm_r)
                            gb_chan = (np.nan_to_num(lrm_n) ** 0.8
                                       * 255).astype(np.uint8)

                            r_chan[nd_mask_r]  = 0
                            gb_chan[nd_mask_r] = 0
                            r_chan[slope_arr == 0] = 0   # nodata du slope

                            rgb = np.stack([r_chan, gb_chan, gb_chan], axis=2)
                            _sauver_array_georef(rgb, Path(src_str), chemin_part)
                            print(f"  RRIM (full memory): {chemin_out.name}"
                                  f" — RGB 3 canaux")
                        except Exception as e_rrim:
                            print(f"  ERROR composite RRIM: {e_rrim}")
                            continue
                finally:
                    if slope_tmp_path.exists():
                        slope_tmp_path.unlink(missing_ok=True)

            elif cle == "vat":
                # ── VAT — composite SVF + openness positif + slope ────────────
                # Même patron que RRIM : calcule les 3 composantes en temp (SVF
                # conv=0 et openness conv=2 via _svf_chunked, slope via
                # _hillshade_chunked), blende avec _vat_compose, nettoie. Les
                # composantes entrent LINÉAIRES (gamma 1) ; le gamma final est
                # appliqué par le composite.
                _vat_dist_px = max(1, int(round(p_i["dist"] / RESOLUTION_M)))
                _vat_gamma   = float(p_i["gamma"])
                print(f"  VAT: composite SVF + openness + slope"
                      f" (radius {_vat_dist_px * RESOLUTION_M:.0f} m)"
                      f", may take 10-20 min...", flush=True)
                _svf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_svf_tmp"))
                _opos_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_opos_tmp"))
                _slope_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp"))
                try:
                    # SVF (conv=0) et openness positif (conv=2) en UN seul scan
                    # d'horizon (kernel fusionné) : ~43% plus rapide que deux
                    # passes _svf_chunked, sorties numériquement identiques.
                    _ok_comp = (
                        _svf_opos_chunked(Path(src_str), _svf_t, _opos_t,
                                          _vat_dist_px, 16, RESOLUTION_M, 1.0)
                        and _hillshade_chunked(Path(src_str), _slope_t, "slope",
                                               {}, dx=RESOLUTION_M, dy=RESOLUTION_M))
                    if not _ok_comp:
                        print("  VAT: components unavailable (numba required for"
                              " SVF/openness), shading skipped.", flush=True)
                        continue
                    if not _vat_compose(_svf_t, _opos_t, _slope_t, chemin_part,
                                        gamma=_vat_gamma):
                        _abandonner_sortie_ombrage(chemin_part)
                        continue
                except Exception as e_vat:
                    print(f"  ERROR composite VAT: {e_vat}")
                    _abandonner_sortie_ombrage(chemin_part)
                    continue
                finally:
                    for _t in (_svf_t, _opos_t, _slope_t):
                        if _t.exists():
                            _t.unlink(missing_ok=True)

            elif cle == "e4mstp":
                # ── Variante lidar2map inspirée de l'e4MSTP publié (Kokalj
                # 2025/RVT), sans reproduire son preset exact. Même patron que
                # VAT : composantes en temp, blend, nettoie. Combine la couleur
                # multi-échelle du MSTP et la netteté du SVF. Lourd (openness
                # pos+neg + SVF + slope + 2 LRM + MSTP) ; réservé aux zones et
                # chunks, pas le défaut.
                _e4_dist_px = max(1, int(round(p_i["dist"] / RESOLUTION_M)))
                _e4_gamma   = float(p_i["gamma"])
                _slrm_fine_px = max(1, int(round(1.5 / RESOLUTION_M)))  # micro-relief
                _slrm_path_px = max(1, int(round(8.0 / RESOLUTION_M)))  # échelle chemin
                print(f"  e4MSTP-style (lidar2map variant):"
                      f" composite MSTP + coloured relief + SVF"
                      f" (radius {_e4_dist_px * RESOLUTION_M:.0f} m)"
                      f", may take 15-30 min...", flush=True)
                _svf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_svf_tmp"))
                _opos_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_opos_tmp"))
                _oneg_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_oneg_tmp"))
                _slope_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp"))
                _mstp_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_mstp_tmp"))
                _slf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slf_tmp"))
                _slp_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slp_tmp"))
                _e4_tmps = (_svf_t, _opos_t, _oneg_t, _slope_t, _mstp_t, _slf_t, _slp_t)
                try:
                    _ok = (
                        _svf_opos_chunked(Path(src_str), _svf_t, _opos_t,
                                          _e4_dist_px, 16, RESOLUTION_M, 1.0)
                        and _svf_chunked(Path(src_str), _oneg_t, _e4_dist_px, 16,
                                         RESOLUTION_M, 1.0, False, 3)
                        and _hillshade_chunked(Path(src_str), _slope_t, "slope",
                                               {}, dx=RESOLUTION_M, dy=RESOLUTION_M)
                        and _mstp_chunked(Path(src_str), _mstp_t, res=RESOLUTION_M)
                        and _lrm_chunked(Path(src_str), _slf_t, _slrm_fine_px)
                        and _lrm_chunked(Path(src_str), _slp_t, _slrm_path_px))
                    if not _ok:
                        print("  e4MSTP: components unavailable (numba/scipy"
                              " required), shading skipped.", flush=True)
                        continue
                    if not _e4mstp_compose(_mstp_t, _svf_t, _opos_t, _oneg_t,
                                           _slope_t, _slf_t, _slp_t, chemin_part,
                                           gamma=_e4_gamma):
                        _abandonner_sortie_ombrage(chemin_part)
                        continue
                except Exception as e_e4:
                    print(f"  ERROR composite e4MSTP: {e_e4}")
                    _abandonner_sortie_ombrage(chemin_part)
                    continue
                finally:
                    for _t in _e4_tmps:
                        if _t.exists():
                            _t.unlink(missing_ok=True)

            if not chemin_part.exists():
                print(f"  ERROR {nom_fichier}: no complete temporary output")
                continue
            try:
                _publier_sortie_ombrage(chemin_part, chemin_out)
            except Exception as e_publication:
                print(f"  ERROR publishing {nom_fichier}: {e_publication}")
                _abandonner_sortie_ombrage(chemin_part)
                continue
            _creer_fichier(chemin_out)
            taille = chemin_out.stat().st_size / 1e6
            elap_numpy = int(time.time() - t0_numpy)
            print(f"  {nom_fichier.ljust(56)}  {_hms(elap_numpy)}  {taille:.0f} Mo")

    finally:
        # Couvre aussi les ``continue`` précoces et Ctrl+C : seule la version
        # temporaire de ce processus est supprimée, jamais l'ancien final.
        for _chemin_part_actif in tuple(_parts_ombrages_actifs):
            _abandonner_sortie_ombrage(_chemin_part_actif)
        # Suppression du dossier transactionnel .part (VRT + dalles.txt).
        if _vrt_tmpdir and _vrt_tmpdir.exists():
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)

    print("\n  Shadings in: " + str(dossier_ville))
    # Fichiers cibles de CE run (instances + pré-calculés provider) : permet à
    # l'étape MBTiles de ne tuiler QUE les ombrages demandés au lieu de tout le
    # dossier projet (sinon --tiles-overwrite re-tuile aussi les anciens).
    #
    # R2#23 : ne pas rendre de chemins théoriques. On lève aussi quand une
    # régénération demandée a échoué mais qu'un ancien final existe encore :
    # l'ancien reste volontairement intact pour la sécurité atomique, sans pour
    # autant masquer l'échec du recalcul.
    _cibles = [dossier_ville / f"{nom_base}_{sfx}.tif" for _t, _p, sfx in insts]
    _manquants = [
        p.name for p in _cibles
        if not p.exists() or p in _sorties_a_regenerer
    ]
    if _manquants:
        raise RuntimeError(
            "shading(s) failed"
            " (previous complete output preserved when present): "
            + ", ".join(_manquants) + " - rerun to complete"
        )
    _prov = [dossier_ville / f"{nom_base}_{c}_ombrage.tif" for c in _cles_provider]
    return _cibles + [p for p in _prov if p.exists()]


from _mbtiles_lidar import (
    _DependancesMbtilesLidar,
    _bbox_depuis_gdalinfo,   # noqa: F401 - réexport de façade (contrat historique)
    _tile_workers_defaut,
    _warped_3857_valide,     # noqa: F401 - réexport de façade, testé directement
    generer_mbtiles_lidar as _generer_mbtiles_lidar_impl,
)


def _dependances_mbtiles_lidar():
    """Reconstruit les coutures du producteur LiDAR à chaque appel.

    Les attributs sont relus sur le module : les monkeypatches des suites
    (`PROVIDER`, `_creer_fichier`, `_mbtiles_a_regenerer`,
    `_bbox_enveloppe_transform`, `_valider_sqlite_part`, `_chemin_part`)
    restent donc actifs après l'extraction."""
    return _DependancesMbtilesLidar(
        chemin_part=_chemin_part,
        nettoyer_sqlite_part=_nettoyer_sqlite_part,
        valider_sqlite_part=_valider_sqlite_part,
        mbtiles_a_regenerer=_mbtiles_a_regenerer,
        creer_fichier=_creer_fichier,
        formater_duree=_hms,
        stop_event=_stop_event,
        get_transformer=_get_transformer,
        natif_vers_wgs84=_natif_vers_wgs84,
        bbox_enveloppe_transform=_bbox_enveloppe_transform,
        batch_insert=BATCH_MBTILES_INSERT,
        crs_natif=PROVIDER.CRS_NATIF,
    )


def generer_mbtiles_lidar(tif_source, dossier_ville, nom_ville,
                    zoom_min=13, zoom_max=17, format_tuiles="auto",
                    jpeg_quality=85, bbox_natif=None, tampon_coin_max_m=0,
                    source_already_warped=False, ecraser_tuiles=False,
                    tile_workers=8):
    """Façade compatible vers le producteur MBTiles LiDAR extrait."""
    return _generer_mbtiles_lidar_impl(
        tif_source, dossier_ville, nom_ville,
        zoom_min=zoom_min, zoom_max=zoom_max, format_tuiles=format_tuiles,
        jpeg_quality=jpeg_quality, bbox_natif=bbox_natif,
        tampon_coin_max_m=tampon_coin_max_m,
        source_already_warped=source_already_warped,
        ecraser_tuiles=ecraser_tuiles, tile_workers=tile_workers,
        dependances=_dependances_mbtiles_lidar(),
    )


# ============================================================
# PIPELINE WMTS — SCAN 25 / ORTHO
# ============================================================

WMTS_URL     = "https://data.geopf.fr/private/wmts"
WMTS_URL_PUB = "https://data.geopf.fr/wmts"
# Clé API IGN — chargée depuis lidar2map.env si présent, sinon valeur par défaut.
# Pour utiliser votre propre clé, créez lidar2map.env (non versionné) avec :
#   IGN_APIKEY=votre_cle
_apikey_env_path = DOSSIER_TRAVAIL / "lidar2map.env"
if _apikey_env_path.exists():
    for _line in _apikey_env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line.startswith("IGN_APIKEY=") and not _line.startswith("#"):
            os.environ.setdefault("IGN_APIKEY", _line.split("=", 1)[1].strip())
            break
APIKEY_DEFAUT = os.environ.get("IGN_APIKEY", "")
# ⚠ Les couches Scan (scan25, scan25tour, scan100, scanoaci) sont réservées aux
# professionnels (CGU IGN). Leur clé d'accès n'est pas distribuable aux particuliers.
# Source : réponse IGN du 31/03/2026 — geoplateforme@ign.fr
# Les couches publiques (planign, ortho, cadastre…) ne nécessitent aucune clé.
WMTS_HEADERS  = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/49.0"}

# Couches WMTS IGN — (identifiant_layer, style, format, clé_privée_requise)
# Endpoint public  : https://data.geopf.fr/wmts
# Endpoint privé   : https://data.geopf.fr/private/wmts
# ⚠ Les couches avec clé_privée_requise=True nécessitent une clé API professionnelle.
COUCHES = {
    # ── Cartes topographiques (public, sans clé) ──────────────────────────────
    "planign":       ("GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",         "normal", "image/png",  False),
    "etatmajor40":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR40",       "normal", "image/jpeg", False),
    "etatmajor10":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR10",       "normal", "image/jpeg", False),
    "pentes":        ("GEOGRAPHICALGRIDSYSTEMS.SLOPES.MOUNTAIN",   "normal", "image/png",  False),
    # ── Imagerie (public, sans clé) ───────────────────────────────────────────
    "ortho":         ("ORTHOIMAGERY.ORTHOPHOTOS",                  "normal", "image/jpeg", False),
    # Orthophotographies historiques métropole — clé pour archéo et exploration
    # (restanques avant déprise, anciens chemins encore parcourus, cabanons).
    # Couverture variable selon les departments: tester avant de se fier dessus.
    "ortho_1950":    ("ORTHOIMAGERY.ORTHOPHOTOS.1950-1965",        "normal", "image/png",  False),
    "ortho_1965":    ("ORTHOIMAGERY.ORTHOPHOTOS.1965-1980",        "normal", "image/png",  False),
    "ortho_1980":    ("ORTHOIMAGERY.ORTHOPHOTOS.1980-1995",        "normal", "image/png",  False),
    # Infrarouge couleur — distingue feuillus/résineux, repère humidité du sol
    # (utile pour trouver d'anciens drainages, fossés, cours d'eau dévoyés).
    "ortho_irc":     ("ORTHOIMAGERY.ORTHOPHOTOS.IRC",              "normal", "image/jpeg", False),
    # Imagerie satellitaire (vrai satellite, pas avion)
    "pleiades":      ("ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2024",      "normal", "image/jpeg", False),
    "spot":          ("ORTHOIMAGERY.ORTHO-SAT.SPOT.2024",          "normal", "image/jpeg", False),
    # Orthos EDUGEO PACA — emprises locales restreintes aux centres urbains.
    # Tester d'abord la couverture pour Toulon-Hyères ou Marseille-Martigues
    # selon ta zone (Garéoult/Mazaugues est entre les deux, hors emprises).
    "edugeo_marseille_1969": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1969", "normal", "image/png", False),
    "edugeo_marseille_1980": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1980", "normal", "image/png", False),
    "edugeo_marseille_1987": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1987", "normal", "image/png", False),
    "edugeo_marseille_1988": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1988", "normal", "image/png", False),
    "edugeo_marseille_2010": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES2010", "normal", "image/png", False),
    "edugeo_toulon_1972":    ("ORTHOIMAGERY.EDUGEO.TOULON-HYERES1972",      "normal", "image/png", False),
    # ── Données thématiques (public, sans clé) ────────────────────────────────
    "cadastre":      ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS",      "normal", "image/png",  False),
    "ombrage":       ("ELEVATION.ELEVATIONGRIDCOVERAGE.SHADOW",    "normal", "image/png",  False),
    # ── Imagerie hors-France (tuiles XYZ ArcGIS, public, sans clé) ────────────
    # Convention "XYZ:<template>" : URL de tuile XYZ avec {z}/{y}/{x} (même
    # schéma Web Mercator que les WMTS IGN). Gérée par construire_url_wmts.
    # naip = USGS Imagery (dérivé NAIP, ortho sub-métrique sur les USA contigus,
    # domaine public) — complément image du LiDAR 3DEP (us-tnm).
    "naip":          ("XYZ:https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", "normal", "image/jpeg", False),
    # ── Cartes topographiques — RÉSERVÉES AUX PROFESSIONNELS ─────────────────
    # Accès restreint : compte pro sur cartes.gouv.fr + SIRET requis
    "scan25":        ("GEOGRAPHICALGRIDSYSTEMS.MAPS",              "normal", "image/jpeg", True),
    "scan25tour":    ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR",   "normal", "image/jpeg", True),
    "scan100":       ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN100",      "normal", "image/jpeg", True),
    "scanoaci":      ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-OACI",    "normal", "image/jpeg", True),
}


from _mbtiles_wmts_helpers import (
    _DependancesTelechargementWmts,
    _bbox_valide_wgs84,
    _est_image_valide,
    _wmts_close_all_conns,
    _wmts_fetch as _wmts_fetch_impl,
    _wmts_get_conn,        # noqa: F401 - réexport de façade (contrat historique)
    calculer_grille_xyz,
    compter_tuiles_xyz,
    construire_url_wmts,   # noqa: F401 - réexport de façade (contrat historique)
    deg_to_tile,
    estimer_taille,
    telecharger_tuile as _telecharger_tuile_impl,
    _lire_zoom_limites_wmts as _lire_zoom_limites_wmts_impl,
)


def _wmts_fetch(url):
    """Façade compatible vers le fetch HTTP keep-alive extrait.

    Signature à un seul argument, INCHANGÉE : certaines suites remplacent cette
    fonction en bloc (`l2m._wmts_fetch = lambda url: ...`, sans réseau ni
    `mock.patch.object`). `telecharger_tuile` reçoit ce nom comme dépendance
    injectée (`wmts_fetch`), donc un tel remplacement direct reste vu."""
    return _wmts_fetch_impl(url, headers=WMTS_HEADERS)


def _dependances_telechargement_wmts():
    """Reconstruit les coutures du téléchargement WMTS à chaque appel.

    Les attributs sont relus sur le module : les monkeypatches des suites
    (`MAX_TENTATIVES` notamment, patché par `_test_atomic_downloads.py` pour
    les jumeaux LiDAR de ce paramètre ; `_wmts_fetch`, remplacé en bloc par
    `_test_robustesse.py`/`_test_interactions.py`) restent donc actifs après
    l'extraction."""
    return _DependancesTelechargementWmts(
        wmts_url=WMTS_URL,
        wmts_url_pub=WMTS_URL_PUB,
        wmts_fetch=_wmts_fetch,
        http_ua=_HTTP_UA,
        max_tentatives=MAX_TENTATIVES,
        delai_retry=DELAI_RETRY,
    )


def _lire_zoom_limites_wmts(layer, apikey_requis, apikey=""):
    """Façade compatible vers l'interrogation GetCapabilities extraite."""
    return _lire_zoom_limites_wmts_impl(
        layer, apikey_requis, apikey=apikey,
        dependances=_dependances_telechargement_wmts(),
    )


def telecharger_tuile(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """Façade compatible vers le téléchargement de tuile WMTS extrait."""
    return _telecharger_tuile_impl(
        z, x, y, layer, style, fmt, apikey, apikey_requis,
        dependances=_dependances_telechargement_wmts(),
    )

# ============================================================
# GÉNÉRATION MBTILES
# ============================================================

class ZoneHorsCouvertureWMTS(RuntimeError):
    """Abort couverture WMTS : la zone est (quasi) entièrement hors de la couche
    (que des 204). Distincte d'une panne I/O systémique (qui reste un RuntimeError
    nu). En run simple, elle remonte : bbox probablement erronée, message d'aide
    utile. En chunk de grille auto-généré, la boucle de split la rattrape et
    saute la cellule (mer, hors frontière) : légitimement vide, pas une erreur."""
    pass


def _jpeg_quality_sortie(img_fmt, formats_image, qualite_image):
    """Qualité de re-encodage PNG→JPEG côté client, ou None si aucun re-encodage.

    SOURCE DE VÉRITÉ UNIQUE partagée par la passe simple (main_wmts) et le split
    (_traiter_bbox_wmts) : les deux jumeaux avaient divergé (le split convertissait
    toujours PNG→JPEG en ignorant --image-format png, R2#14). Règles :
      - serveur JPEG natif (ortho, scan*…) → None (jamais reconverti ; --image-format
        png sur ces couches est signalé puis ignoré, cf. la note dans main_wmts) ;
      - PNG natif + --image-format png → None (l'utilisateur garde le PNG lossless) ;
      - PNG natif + --image-format jpeg/auto → la qualité demandée (conversion).
    """
    _native_png = img_fmt.lower() in ("image/png", "png")
    return qualite_image if (_native_png and formats_image != "png") else None


def _nom_mbtiles_wmts(nom, couche, zoom_min, zoom_max, jpeg_q):
    """Nom de base du MBTiles WMTS (sans extension). SOURCE DE VÉRITÉ UNIQUE
    partagée par la passe simple (main_wmts) et le split (_traiter_bbox_wmts),
    pour que les deux jumeaux nomment identiquement (cf. R2#14).

    Encode un segment qualité `_q<Q>` quand une conversion PNG→JPEG a lieu
    (jpeg_q non None), sinon rien. Sans ce segment, relancer avec un
    --image-quality/--image-format différent réutilisait le MBTiles obsolète :
    le fichier existait, `_mbtiles_a_regenerer` le validait, la nouvelle qualité
    était ignorée en silence (R2#18). couche/zoom sont déjà dans le nom ; le
    natif (jpeg_q None) est pleinement déterminé par la couche → pas de segment,
    donc aucun MBTiles déjà en cache n'est orphelin pour les couches JPEG."""
    _q = f"_q{int(jpeg_q)}" if jpeg_q is not None else ""
    return f"{nom}_{couche}_z{zoom_min}-{zoom_max}{_q}"


from _mbtiles_wmts import (
    _DependancesMbtilesWMTS,
    generer_mbtiles_wmts as _generer_mbtiles_wmts_impl,
)


def _dependances_mbtiles_wmts():
    """Reconstruit les coutures du producteur WMTS à chaque appel.

    Les attributs sont relus sur le module : les monkeypatches des suites
    (`telecharger_tuile`, `_valider_sqlite_part`, `_chemin_part`, `_log_req`)
    restent donc actifs après l'extraction."""
    return _DependancesMbtilesWMTS(
        chemin_part=_chemin_part,
        nettoyer_sqlite_part=_nettoyer_sqlite_part,
        valider_sqlite_part=_valider_sqlite_part,
        telecharger_tuile=telecharger_tuile,
        est_image_valide=_est_image_valide,
        fermer_connexions_wmts=_wmts_close_all_conns,
        log_req=_log_req,
        formater_duree=_hms,
        stop_event=_stop_event,
        zone_hors_couverture=ZoneHorsCouvertureWMTS,
        endpoint_prive=WMTS_URL,
        endpoint_public=WMTS_URL_PUB,
        batch_insert=BATCH_MBTILES_INSERT,
        seuil_err_consec=SEUIL_ERR_CONSEC,
        seuil_hors_couverture=SEUIL_HORS_COUVERTURE,
    )


def generer_mbtiles_wmts(chemin, tuiles_iter, total, nom_zone, fmt_ext,
                    zoom_min, zoom_max, layer, style, img_fmt,
                    apikey, apikey_requis, workers,
                    bbox_wgs84=None, jpeg_quality=None,
                    dossier_cache=None, ecraser_tuiles=False, ecraser_dalles=False):
    """Façade compatible vers le producteur MBTiles WMTS extrait."""
    return _generer_mbtiles_wmts_impl(
        chemin, tuiles_iter, total, nom_zone, fmt_ext,
        zoom_min, zoom_max, layer, style, img_fmt,
        apikey, apikey_requis, workers,
        bbox_wgs84=bbox_wgs84, jpeg_quality=jpeg_quality,
        dossier_cache=dossier_cache, ecraser_tuiles=ecraser_tuiles,
        ecraser_dalles=ecraser_dalles,
        dependances=_dependances_mbtiles_wmts(),
    )

# ============================================================
# GÉNÉRATION RMAP
# ============================================================

# ── Helpers LE ────────────────────────────────────────────────────────────────
from _raster_formats import (
    _blob_vers_jpeg,
    _build_map_info,
    _convertir_formats as _convertir_formats_impl,
    _convertir_un_mbtiles as _convertir_un_mbtiles_impl,
    _empty_jpeg_256,
    _sqlitedb_schema_courant,
    _tile_to_geo,
    _wi,
    _wl,
    generer_rmap_depuis_mbtiles as _generer_rmap_depuis_mbtiles_impl,
    generer_sqlitedb_depuis_mbtiles as _generer_sqlitedb_depuis_mbtiles_impl,
)


def generer_rmap_depuis_mbtiles(mbtiles_path, ecraser=False):
    """Façade compatible vers le convertisseur RMAP extrait."""
    return _generer_rmap_depuis_mbtiles_impl(
        mbtiles_path,
        ecraser=ecraser,
        chemin_part=_chemin_part,
        formater_duree=_hms,
        seuil_rmap_padding=SEUIL_RMAP_PADDING,
        pack_int32=_wi,
        pack_int64=_wl,
        tile_to_geo=_tile_to_geo,
        empty_jpeg=_empty_jpeg_256,
        blob_vers_jpeg=_blob_vers_jpeg,
        build_map_info=_build_map_info,
    )


def generer_sqlitedb_depuis_mbtiles(mbtiles_path, ecraser=False):
    """Façade compatible vers le convertisseur SQLiteDB extrait."""
    return _generer_sqlitedb_depuis_mbtiles_impl(
        mbtiles_path,
        ecraser=ecraser,
        chemin_part=_chemin_part,
        nettoyer_sqlite_part=_nettoyer_sqlite_part,
        valider_sqlite_part=_valider_sqlite_part,
        batch_sqlitedb_insert=BATCH_SQLITEDB_INSERT,
        formater_duree=_hms,
        schema_courant=_sqlitedb_schema_courant,
    )


import _osm_runtime as _osmosis_runtime_impl


# ── Bootstrap osmosis / JRE / mapwriter (téléchargement, découverte) ──────
# Regroupé ici (10 août 2026, sous-phase 9a) : ces fonctions vivaient
# égarées au début de la section ombrages/COG, sans rapport avec les
# ombrages — seul le pipeline Mapsforge (--osm, generer_map_depuis_geojson_ign)
# les consomme, via _preparer_osmosis()/_java_opts_extra() juste en dessous.
def _promouvoir_dossier(tmp_dir, dest_dir):
    """Promeut un dossier ``.part`` sans supprimer l'ancien avant succès.

    Un système de fichiers ne sait généralement pas remplacer atomiquement un
    dossier final non vide. On déplace donc d'abord l'ancien vers un backup
    voisin ``.part``, on promeut le nouveau, puis seulement on efface le backup.
    Si la seconde opération échoue, l'ancien est remis à sa place. Ainsi une
    erreur de rename ne détruit jamais l'installation encore utilisable.
    """
    return _osmosis_runtime_impl.promouvoir_dossier(
        tmp_dir,
        dest_dir,
        getpid=os.getpid,
        uuid4=uuid.uuid4,
        rmtree=shutil.rmtree,
    )


def _bin_outil(racine, pattern):
    """Retourne le 1er binaire `pattern` sous `racine` situé dans un dossier
    `bin/` (osmosis/java sont extraits dans un sous-dossier versionné variable),
    ou None si absent — sert de validateur d'install complète."""
    return _osmosis_runtime_impl.bin_outil(racine, pattern)


def _telecharger_osmosis_local():
    """Télécharge et installe Osmosis localement de façon transactionnelle."""
    return _osmosis_runtime_impl.telecharger_osmosis_local(
        lidar2map_home=LIDAR2MAP_HOME,
        windows=WINDOWS,
        chemin_part=_chemin_part,
        safe_zip_extractall=_safe_zip_extractall,
        promouvoir=_promouvoir_dossier,
        trouver_binaire=_bin_outil,
        urlretrieve=urllib.request.urlretrieve,
        remplacer=os.replace,
        rmtree=shutil.rmtree,
        getpid=os.getpid,
        uuid4=uuid.uuid4,
    )


def _telecharger_jre_local():
    """Télécharge et installe un JRE Temurin local de façon transactionnelle."""
    return _osmosis_runtime_impl.telecharger_jre_local(
        lidar2map_home=LIDAR2MAP_HOME,
        windows=WINDOWS,
        platform_system=platform.system,
        platform_machine=platform.machine,
        chemin_part=_chemin_part,
        safe_zip_extractall=_safe_zip_extractall,
        promouvoir=_promouvoir_dossier,
        request=urllib.request.Request,
        urlopen=urllib.request.urlopen,
        remplacer=os.replace,
        rmtree=shutil.rmtree,
        getpid=os.getpid,
        uuid4=uuid.uuid4,
    )


def _trouver_java():
    """
    Retourne le chemin vers le binaire java local (~/.lidar2map/jre/).
    Télécharge le JRE Temurin si absent. Jamais le Java système.

    Mode frozen : cherche d'abord dans BUNDLE_DIR/jre/ (JRE embarqué).
    """

    return _osmosis_runtime_impl.trouver_java(
        frozen=getattr(sys, "frozen", False),
        bundle_dir=BUNDLE_DIR,
        lidar2map_home=LIDAR2MAP_HOME,
        windows=WINDOWS,
        telecharger_jre_local=_telecharger_jre_local,
    )


def _trouver_osmosis():
    """Retourne le chemin vers osmosis (installation locale ou téléchargement).
    Même logique que GDAL : pas de fallback PATH système.
    Prérequis : appeler _trouver_java() avant (responsabilité de l'appelant).

    Mode frozen : cherche d'abord dans BUNDLE_DIR/osmosis/ (osmosis embarqué,
    avec le plugin mapwriter pré-installé dans son lib/)."""
    return _osmosis_runtime_impl.trouver_osmosis(
        frozen=getattr(sys, "frozen", False),
        bundle_dir=BUNDLE_DIR,
        lidar2map_home=LIDAR2MAP_HOME,
        windows=WINDOWS,
        telecharger_osmosis_local=_telecharger_osmosis_local,
    )


_MAPWRITER_VERSION = _osmosis_runtime_impl.MAPWRITER_VERSION
_MAPWRITER_JAR = _osmosis_runtime_impl.MAPWRITER_JAR
_MAPWRITER_URL = _osmosis_runtime_impl.MAPWRITER_URL


def _verifier_mapwriter():
    """Vérifie ou installe atomiquement le plugin mapsforge-map-writer."""
    return _osmosis_runtime_impl.verifier_mapwriter(
        frozen=getattr(sys, "frozen", False),
        home_dir=Path.home(),
        chemin_part=_chemin_part,
        jar_name=_MAPWRITER_JAR,
        url=_MAPWRITER_URL,
        urlretrieve=urllib.request.urlretrieve,
        remplacer=os.replace,
    )


def _telecharger_outils():
    """Orchestre la préparation locale de Java, Osmosis et mapwriter."""
    return _osmosis_runtime_impl.telecharger_outils(
        trouver_java=_trouver_java,
        trouver_osmosis=_trouver_osmosis,
        verifier_mapwriter=_verifier_mapwriter,
        jar_name=_MAPWRITER_JAR,
    )


# Le flag est détecté avant bootstrap pour traverser le re-exec venv, puis
# exécuté ici une fois toutes les façades outils disponibles.
if _TELECHARGER_OUTILS:
    _telecharger_outils()
    sys.exit(0)


def _java_opts_extra():
    """Options JVM additionnelles à passer à osmosis.

    Mode frozen : pointe `user.home` vers BUNDLE_DIR (sans `.openstreetmap/`)
    pour empêcher osmosis de scanner `%USERPROFILE%\\.openstreetmap\\osmosis\\plugins\\`.
    Sinon le plugin mapwriter serait chargé deux fois (CLASSPATH bundlé +
    plugins dir utilisateur) → OsmosisRuntimeException "Task type already exists".
    """
    return _osmosis_runtime_impl.java_opts_extra(
        frozen=getattr(sys, "frozen", False),
        bundle_dir=BUNDLE_DIR,
    )


def _preparer_osmosis(dossier_hint=None):
    """
    Vérifie mapwriter, trouve java + osmosis, retourne (osmosis_exe, java_home).
    Retourne (None, None) en cas d'échec.
    dossier_hint : Path optionnel pour la recherche de tagmapping-min.xml (non utilisé ici).
    """
    return _osmosis_runtime_impl.preparer_osmosis(
        dossier_hint,
        verifier_mapwriter=_verifier_mapwriter,
        trouver_java=_trouver_java,
        trouver_osmosis=_trouver_osmosis,
    )


# Tokens d'intérêt : seules les lignes qui contiennent un de ces marqueurs
# sont AFFICHÉES en live. Le reste est silencieux (le terminal reste propre,
# comme avant l'étape 5 quand on faisait capture_output=True).
# Les lignes silencieuses sont quand même conservées dans stderr_diag pour
# le diagnostic en cas de returncode != 0.
# Couvre Java util.logging FR/EN, exceptions, et causes chaînées.
_OSMOSIS_INTERESSANT = _osmosis_runtime_impl.OSMOSIS_INTERESSANT


def _run_osmosis_streaming(cmd_or_str, shell, env):
    """Lance osmosis en streaming live.

    Remplace `subprocess.run(capture_output=True)` qui buffer toute la sortie
    en RAM (problème sur dept-scale où Java peut produire des MB de logs).

    Stratégie de filtrage : whitelist. Seules les lignes contenant un marqueur
    de _OSMOSIS_INTERESSANT (ERROR, WARNING, Exception, AVERTISSEMENT…) sont
    affichées en temps réel. Les lignes ordinaires (timestamps Java, classes
    org.mapsforge, INFO, SLF4J, etc.) sont silencieuses — comportement
    identique à l'ancien capture_output=True en cas de succès.

    Garde les 500 dernières lignes stderr (accumulation totale, pas filtrée)
    pour diagnostic en cas d'échec. Buffer borné, ~50 Ko max.

    Returns: (returncode, stderr_diagnostic_string)
    """
    return _osmosis_runtime_impl.run_osmosis_streaming(
        cmd_or_str,
        shell,
        env,
        subprocess_module=subprocess,
        marqueurs=_OSMOSIS_INTERESSANT,
    )


def _nettoyer_osmosis_temp_orphelins(verbose=False, min_age_s=300):
    """Nettoie les fichiers d'index temporaires osmosis orphelins du dossier %TEMP%.

    Sur Windows, osmosis (Java) laisse parfois ses fichiers d'index
    ``idxNodes*.tmp`` et ``idxWays*.tmp`` dans ``%LOCALAPPDATA%\\Temp\\``
    parce que la JVM ne libère pas tous ses handles à la fermeture. Ces
    fichiers s'accumulent au fil des runs OSM (jusqu'à plusieurs Go).

    Sécurités :
      - On ne touche pas les fichiers modifiés dans les ``min_age_s`` dernières
        secondes (défaut 5 min) — ils peuvent appartenir à un osmosis en
        cours d'exécution dans une autre instance.
      - ``PermissionError`` swallow silencieusement (fichier verrouillé par
        un processus encore actif) — on retentera au prochain run.

    Retourne (nb_supprimes, octets_liberes).
    """
    return _osmosis_runtime_impl.nettoyer_osmosis_temp_orphelins(
        verbose=verbose,
        min_age_s=min_age_s,
    )


# Grammaire d'un filtre osmosis `accept-ways` : `clé` ou `clé=valeur[,valeur…]`.
# Les clés/valeurs OSM légitimes n'utilisent QUE lettres (unicode, accents ok),
# chiffres, `_ : - . *` (wildcard) et l'espace. Aucun métacaractère shell n'y a
# sa place. Sur Windows l'osmosis est un .bat lancé via cmd.exe (shell=True) : une
# valeur `--layer` contenant `& | > ^ " %`… serait interprétée par le shell
# (injection de commande, R2#1). On valide en amont par ALLOWLIST (rejet strict)
# plutôt que d'échapper au cas par cas : plus sûr et indépendant de la plateforme.
import _osm_policy as _osm_policy_impl


_OSM_TAG_RE = _osm_policy_impl.OSM_TAG_RE


def _valider_osm_tags(osm_tags):
    """Rejette les filtres hors grammaire Osmosis (anti-injection)."""
    invalide = _osm_policy_impl.valider_osm_tags(osm_tags)
    if invalide is not None:
        print(f"  ERROR: invalid --layer filter {str(invalide)!r} : only "
              f"osmosis tag filters are allowed (key or key=value[,value]), "
              f"no shell metacharacters.")
        sys.exit(1)
    return osm_tags


def _osm_filtre_cles(osm_tags):
    return _osm_policy_impl.osm_filtre_cles(osm_tags)


def _osm_cle_match(tags, cles, vals_par_cle):
    return _osm_policy_impl.osm_cle_match(tags, cles, vals_par_cle)


def _hash_config(payload):
    return _osm_policy_impl.hash_config(payload)


def _sig_sidecar_stale(chemin, sig):
    return _osm_policy_impl.sig_sidecar_stale(chemin, sig)


def _sig_sidecar_ecrire(chemin, sig):
    return _osm_policy_impl.sig_sidecar_ecrire(
        chemin, sig, ecrire_texte_atomique=_ecrire_texte_atomique,
    )


def _signature_osm(bbox_wgs84, osm_tags, osm_pbf, skip_bbox):
    return _osm_policy_impl.signature_osm(
        bbox_wgs84,
        osm_tags,
        osm_pbf,
        skip_bbox,
        hash_configurer=_hash_config,
    )


from _osm_map_pipeline import (
    DependancesCarteOsm as _DependancesCarteOsm,
    generer_carte_osm as _generer_carte_osm_impl,
)


def _dependances_carte_osm():
    return _DependancesCarteOsm(
        bundle_dir=BUNDLE_DIR,
        dossier_travail=DOSSIER_TRAVAIL,
        windows=WINDOWS,
        osmosis_interessant=_OSMOSIS_INTERESSANT,
        chemin_part=_chemin_part,
        formater_duree=_hms,
        java_opts_extra=_java_opts_extra,
        nettoyer_osmosis_temp=_nettoyer_osmosis_temp_orphelins,
        preparer_osmosis=_preparer_osmosis,
        sidecar_ecrire=_sig_sidecar_ecrire,
        sidecar_stale=_sig_sidecar_stale,
        signature_osm=_signature_osm,
        valider_osm_tags=_valider_osm_tags,
        verifier_mapwriter=_verifier_mapwriter,
        generer_geojson=generer_geojson_osm,
        journaliser_requete=_log_req,
        executer_osmosis=_run_osmosis_streaming,
        publier_groupe_atomique=_publier_groupe_atomique,
    )


def generer_carte_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                      osm_tags=None, export_geojson=True, ecraser_tuiles=False,
                      skip_bbox=False, geojson_formats=None, want_map=True):
    return _generer_carte_osm_impl(
        bbox_wgs84,
        dossier_ville,
        nom_zone,
        osm_pbf,
        osm_tags=osm_tags,
        export_geojson=export_geojson,
        ecraser_tuiles=ecraser_tuiles,
        skip_bbox=skip_bbox,
        geojson_formats=geojson_formats,
        want_map=want_map,
        dependances=_dependances_carte_osm(),
    )


generer_carte_osm.__doc__ = _generer_carte_osm_impl.__doc__


def _resoudre_choix_ombrages(args):
    """Résout --shadings/--shading en (choix, instances) : 'all'/'tous' →
    SHADING_TOUS, 'none'/'aucun' → rien du tout (instances comprises), et les types
    couverts par une instance --shading explicite sont retirés de choix
    (l'instance porte SES params — sinon ils seraient AUSSI générés aux
    params par défaut). Partagé par main() et _traiter_bbox_lidar : la
    résolution était dupliquée dans les deux mains (sites jumeaux)."""
    ombrages   = args.ombrages or []
    spec_insts = getattr(args, "shading_instances", None) or []
    if any(v in ombrages for v in ("aucun", "none")):
        return [], []
    choix = (list(SHADING_TOUS)
             if any(v in ombrages for v in ("tous", "all"))
             else list(ombrages))
    if spec_insts:
        _types = {t for t, _ in spec_insts}
        choix = [c for c in choix if c not in _types]
    return choix, spec_insts


def _lister_tifs_ombrages(dossier_ville, tifs_run):
    """TIF d'ombrage à tuiler dans un dossier projet. Exclut les caches de
    tuilage `_tuilage_z<N>.tif` (produits par generer_mbtiles_lidar — sans ce
    filtre le cache devient sa propre source, boucle infinie en pratique) et,
    quand l'étape shadings a tourné (tifs_run fourni, même vide), restreint aux cibles
    de CE run (sinon --tiles-overwrite re-tuilait aussi les anciens ombrages
    du dossier). Un run SANS étape shadings (tifs_run None) convertit tout le
    dossier — comportement historique. Partagé main() ↔ _traiter_bbox_lidar."""
    tifs = [t for t in sorted(dossier_ville.glob("*.tif"))
            if not t.name.startswith("_")
            and not re.search(r'_tuilage_z\d+\.tif$', t.name)]
    if tifs_run is not None:
        noms_run = {p.name for p in tifs_run}
        tifs = [t for t in tifs if t.name in noms_run]
    return tifs


def _tuiler_tifs_ombrages(args, tifs, dossier_ville, nom_zone, bbox,
                          decoupe_sortie=True, verbose=False, tampon_coin_max_m=0,
                          mbtiles_attendus=None):
    """Tuile chaque TIF d'ombrage (make-like via _mbtiles_a_regenerer :
    détecte aussi mbtiles corrompu/vide et TIF plus récent) puis applique les
    conversions RMAP/SQLiteDB. Partagé par main() (decoupe_sortie=True) et
    _traiter_bbox_lidar (False : le découpage est déjà fait par les chunks).
    Ce bloc était dupliqué entre les deux mains, avec du drift déjà mordu.

    tampon_coin_max_m : cf. generer_mbtiles_lidar. 0 (défaut, cas non
    découpé) : aucune incidence, cette zone n'a pas de coin partagé avec un
    voisin. Retourne False si au moins une génération/conversion demandée
    échoue sans lever d'exception."""
    ok = True
    for tif in tifs:
        if verbose:
            print("  " + tif.name)
        stem   = re.sub(r'_tuilage_z\d+$', '', tif.stem)
        suffix = stem[len(nom_zone) + 1:] if stem.startswith(nom_zone + "_") else stem
        nom_base = f"{nom_zone}_{suffix}"
        mbt_path = dossier_ville / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
        if mbtiles_attendus is not None:
            mbtiles_attendus.append(mbt_path)
        mbt_neuf = _mbtiles_a_regenerer(mbt_path, args.tuiles_ecraser, source=tif)
        if mbt_neuf:
            mbt_out = generer_mbtiles_lidar(
                tif, dossier_ville, nom_base,
                zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                format_tuiles=args.formats_image,
                jpeg_quality=args.qualite_image,
                bbox_natif=bbox, tampon_coin_max_m=tampon_coin_max_m,
                ecraser_tuiles=args.tuiles_ecraser,
                tile_workers=_tile_workers_defaut())
        else:
            print(f"  Existing MBTiles: {mbt_path.name}, direct split/conversion")
            mbt_out = mbt_path
        ok = (_convertir_formats(
            mbt_out, args, decoupe_sortie=decoupe_sortie,
            mbtiles_neuf=mbt_neuf) and ok)
    return ok


def _appliquer_defauts_cli_lidar(args):
    """Applique le contrat par défaut d'un run LiDAR en ligne de commande.

    Un traitement normal télécharge les données manquantes, calcule LRM et
    produit MBTiles. Une commande de maintenance seule ou une conversion de
    source ne télécharge pas les données implicitement. Les choix explicites
    priment (la découverte d'index du provider peut toujours vérifier la zone).
    """
    maintenance_demandee = any((
        args.dalles_purger_invalides,
        args.dalles_purger_hors_zone,
        args.ombrages_compresser,
    ))
    produit_explicitement_demande = bool(
        args.ombrages is not None
        or args.shading_specs
        or args.shading_preset
        or args.formats_fichier
    )
    maintenance_seule = (
        maintenance_demandee and not produit_explicitement_demande
    )

    if args.telechargement_forcer or args.telechargement_ecraser:
        args.telechargement = True
    elif args.telechargement is None:
        args.telechargement = bool(
            args.ignlidar and not args.source and not maintenance_seule
        )

    if (args.ignlidar and not args.source and not maintenance_seule
            and args.ombrages is None and not args.shading_specs
            and not args.shading_preset):
        args.ombrages = ["lrm"]

    source_tif = bool(
        args.source and Path(args.source).suffix.lower() in (".tif", ".tiff")
    )
    ombrage_productif = bool(
        args.ombrages
        and not any(v in args.ombrages for v in ("aucun", "none"))
    )
    if (args.ignlidar and not args.formats_fichier
            and (ombrage_productif or args.shading_specs
                 or args.shading_preset or source_tif)):
        args.formats_fichier = ["mbtiles"]
    return args


def _valider_contrat_cli_lidar(args, parser, *, provider_explicit=None):
    """Valide les paramètres qui rendent un run LiDAR reproductible.

    Le provider ne doit pas dépendre d'un défaut géographique implicite. Une
    ville ou un point GPS définit un centre, pas une emprise : sa largeur est
    donc obligatoire. Les zones surfaciques (bbox, département, région) sont
    déjà entièrement définies et n'ont pas besoin de ``--zone-width``.
    """
    if not getattr(args, "ignlidar", False):
        return
    if provider_explicit is None:
        provider_explicit = _PROVIDER_CLI_EXPLICIT
    if not provider_explicit:
        parser.error(
            "--provider is required with --lidar "
            "(for example: --provider fr-ign)"
        )
    if ((getattr(args, "zone_ville", None)
         or getattr(args, "zone_gps", None))
            and getattr(args, "zone_width", None) is None):
        parser.error(
            "--zone-width is required with --zone-city or --zone-gps"
        )


def _construire_parser_lidar():
    """Construit le parser argparse du workflow LiDAR/OSM (--lidar/--osm)."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py
  python lidar2map.py --lidar --provider fr-ign --zone-city gareoult --zone-width 5
  python lidar2map.py --lidar --provider fr-ign --zone-department 83 --shadings multi --file-formats mbtiles
  python lidar2map.py --osm --zone-city gareoult
        """
    )
    parser.add_argument("--version", action="version",
                        version=f"lidar2map {VERSION} ({VERSION_DATE}), multi-provider")
    parser.add_argument("--lidar", "--ignlidar", action="store_true", dest="ignlidar",
                        help="LiDAR terrain-processing workflow")

    # ── Découpage à priori (raster uniquement) ──────────────────────────────
    grp_priori = parser.add_argument_group(
        "A priori splitting — --lidar only",
        "Sequential chunk processing with automatic resume (manifeste.json).\n"
        "The same parameters also control the splitting of output files.")
    grp_priori.add_argument("--split-cols", "--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Number of grid columns (East-West).")
    grp_priori.add_argument("--split-rows", "--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Number of grid rows (North-South).")
    grp_priori.add_argument("--split-width", "--split-largeur", type=_arg_float_non_negatif, default=0.0, metavar="KM",
                            dest="split_width",
                            help="Alternative: split into ~KM km squares (KM = the side).")
    grp_priori.add_argument("--block", "--bloc", default="", metavar="i/M", dest="block",
                            help="Process only block i of M: M-way geographic split of the "
                                 "zone, this run does block i only. For sharding one area "
                                 "across several machines (same command each, only i changes). "
                                 "Composes with --split-width (internal chunking of the block).")
    grp_priori.add_argument("--cleanup", "--nettoyage", action="store_true", dest="nettoyage",
                            help="Delete intermediate tiles + TIFs after each chunk. "
                                 "Essential for large areas (a whole department).")
    grp_priori.add_argument("--cleanup-keep-tiles", action="store_true",
                            dest="nettoyage_garder_dalles",
                            help="With --cleanup: keep the downloaded tiles in the shared "
                                 "cache, delete the other intermediates. Use when a later "
                                 "run reprocesses the same area (the GUI queue sets it "
                                 "automatically) to avoid re-downloading them.")
    grp_priori.add_argument("--min-free-gb", "--min-disque-go", type=_arg_float_non_negatif, default=0.0, metavar="GB",
                            dest="min_free_gb",
                            help="Stop cleanly before a chunk if free disk space drops below GB "
                                 "(0 = disabled). Set it ABOVE one chunk's peak footprint "
                                 "(intermediates + tile pyramid). Exits with code 3 so a shell "
                                 "loop can tell a resumable disk-stop from a real error.")

    # Localisation + zone
    _ajouter_args_zone(
        parser,
        width_default=None,
        bbox_metavar="W,S,E,N",
        bbox_help="WGS84 bbox in degrees: lon_min,lat_min,lon_max,lat_max, "
                  "e.g. 5.9,43.1,6.6,43.8",
        avec_help_full=True,
    )

    # Chemins
    parser.add_argument("--output-dir", "--dossier", metavar="PATH", default=None, dest="dossier",
                        help="Root output folder (default: <script>/ign_lidar/). "
                             "Can be an external drive.")
    parser.add_argument("--tiles-dir", "--dossier-dalles", metavar="PATH", default=None, dest="dossier_dalles",
                        help="IGN tiles cache folder (default: <output-dir>/dalles/). "
                             "Useful to separate cache and outputs on different drives.")

    # Téléchargement
    parser.add_argument("--provider", default=None, metavar="CODE",
                        help="LiDAR provider code (required with --lidar). See the "
                             "GUI selector or docs/providers.md for the current list.")
    parser.add_argument("--api-key", "--apikey", default="", metavar="KEY", dest="apikey",
                        help="Provider API key when required. For us-3dep: "
                             "https://portal.opentopography.org/myopentopo. "
                             "For IGN scan*: cartes.gouv.fr pro account (see --raster). "
                             "Can also be set via env IGN_APIKEY or "
                             "OPENTOPOGRAPHY_API_KEY depending on the provider.")
    parser.add_argument("--workers",  type=_arg_int_positif,   default=NB_WORKERS, metavar="N",
                        help=f"Parallel connections (default: {NB_WORKERS})")
    parser.add_argument("--laz-parallel", type=_arg_int_positif, default=1, metavar="N",
                        dest="laz_parallel",
                        help="LAZ (mode LAZ / --laz) : nb de conversions CSF/DFM "
                             "SIMULTANÉES (défaut 1). Chaque conversion pique ~3 Go "
                             "de RAM, donc N>1 exige la RAM (N x 3 Go) ET des cœurs "
                             "(OMP est réparti à cœurs/N par conversion). Pour une "
                             "VM multi-cœurs ; laisser 1 sur une machine 8 Go.")
    parser.add_argument("--download-compress", "--telechargement-compresser",
                        action=argparse.BooleanOptionalAction, default=True,
                        dest="telechargement_compresser",
                        help="Compress cached tiles (DEFLATE, ~halves the cache: "
                             "a whole department drops from ~90 GB to ~40 GB). "
                             "Enabled by default; --no-download-compress keeps "
                             "raw downloads (slightly faster CPU-wise).")
    parser.add_argument("--download-force", "--telechargement-forcer", action="store_true",
                        dest="telechargement_forcer",
                        help="Re-download tiles already present")
    parser.add_argument("--index-map",
                        action=argparse.BooleanOptionalAction, default=True,
                        dest="index_map",
                        help="Generate <zone>_planche.png next to the deliverables: "
                             "an index sheet (extent + department outline + numbered "
                             "chunk cells for splits). Enabled by default; "
                             "--no-index-map disables it. Standalone on an existing "
                             "project folder: --index-sheet DIR (alias --planche).")

    # Ombrages
    parser.add_argument("--shadings", "--ombrages", metavar="TYPE", nargs="+", dest="ombrages",
                        choices=SHADING_TYPES_ORDRE + ["all", "none", "tous", "aucun"],
                        help=(
                            "Shadings to generate (default for --lidar: lrm). "
                            "Values: " + " ".join(SHADING_TYPES_ORDRE) + " all none "
                            "(French aliases: tous aucun). "
                            "Names: lrm = Local Relief Model (implemented as SLRM, Simple LRM); "
                            "vat = Visualization for Archaeological Topography (VAT-style variant); "
                            "e4mstp = Multiscale Topographic Position, enhanced version 4 "
                            "(lidar2map variant); svf = Sky-View Factor; "
                            "rrim = Red Relief Image Map. "
                            "opos/oneg = positive/negative openness (Yokoyama 2002; "
                            "radius and gamma use the SVF defaults). "
                            "See also --shading-preset. "
                            "SVF is tuned via --svf-conv / --svf-dist / --svf-gamma / --svf-sweep. "
                            "svf/lrm/rrim/vat: computed with numpy/scipy/numba (auto-installed). "
                            "Ex: --shadings multi slope svf rrim"
                        ))
    parser.add_argument("--shading", metavar="TYPE[:k=v,...]", action="append",
                        dest="shading_specs", default=None,
                        help=(
                            "Parameterized shading instance, repeatable. "
                            "Each occurrence requests one output with its own parameters. "
                            "Filename suffixes are canonicalized; if two specifications "
                            "resolve to the same filename, the first output is kept. "
                            "--shading svf:dist=20,gamma=2 --shading svf:dist=100 "
                            "--shading oneg:dist=20,gamma=1.5 --shading 315:elevation=20 "
                            "--shading lrm:sigma=10. "
                            "Params: 315/045/135/225/multi=elevation ; "
                             "svf=conv,dist,gamma,sweep ; "
                             "opos/oneg=dist,gamma,sweep ; "
                            "vat/e4mstp=dist,gamma ; lrm/rrim=sigma(m) ; "
                            "slope=none. Unset params inherit --svf-* / "
                            "--shading-elevation, except e4mstp gamma, which "
                            "defaults to 0.8. "
                            "Combines with --shadings (a type listed in --shading "
                            "is not re-generated at default params)."
                        ))
    parser.add_argument("--shading-preset",
                        choices=["auto", "micro", "standard", "landscape"],
                        default=None, dest="shading_preset",
                        help=("Resolution-tuned shading stack (opt-in, params in "
                              "metres): adds svf + opos + lrm sized for the DEM "
                              "resolution, plus multi + slope. 'auto' picks micro "
                              "(<=0.75 m), standard (>0.75 and <=2.5 m), or landscape "
                              "(>2.5 m) from "
                              "the active provider. Off by default; when set it takes "
                              "precedence over --shadings default params."))
    parser.add_argument("--svf-conv", choices=["flux", "rvt"], default="flux",
                        dest="svf_conv",
                        help=("SVF convention: flux = cos²γ (compressed near 1, "
                              "contrast to the eye); rvt = 1−sin γ (Kokalj/Hesse, "
                              "archaeology standard/openness). Default: flux."))
    parser.add_argument("--svf-dist", type=_arg_float_positif, default=20.0, metavar="M",
                        dest="svf_dist",
                        help=("Horizon-search radius in metres for SVF, openness, "
                              "and their composites (GUI range 10–200). Default: "
                              "20 (micro-relief). 100 = enclosures/roads."))
    parser.add_argument("--shading-elevation", "--ombrages-elevation", type=int, default=None, metavar="DEG",
                        dest="ombrages_elevation",
                        help=(f"Sun angle of directional hillshades in degrees "
                              f"(default: {ELEVATION_SOLEIL}°, archaeology optimal). "
                              f"General use: 45°. Archaeology: 20-30°."))
    parser.add_argument("--svf-gamma", type=_arg_float_positif, default=None, metavar="G",
                        dest="svf_gamma",
                        help=(f"Gamma after percentile stretch for SVF, openness, "
                              f"and VAT (default: {SVF_GAMMA}). <1 lightens, "
                              f"1 = linear, >1 darkens; negative openness uses "
                              f"mirror gamma. e4mstp has its own final gamma "
                              f"(default 0.8)."))

    # Mode non-interactif. None permet de distinguer le défaut du choix explicite :
    # un run --lidar normal télécharge les données manquantes, tandis qu'une
    # opération de maintenance/source ne télécharge rien implicitement.
    parser.add_argument("--download", "--telechargement",
                        action=argparse.BooleanOptionalAction, default=None,
                        dest="telechargement",
                        help="Download missing provider tiles (default for a normal "
                             "--lidar run). --no-download enforces cache-only processing. "
                             "Valid cached tiles are never re-downloaded unless "
                             "--download-force/--download-overwrite is set.")
    parser.add_argument("--tiles-purge-invalid", "--dalles-purger-invalides", action="store_true",
                        dest="dalles_purger_invalides",
                        help="Delete cache tiles < 2 MB (sea tiles, partial errors). "
                             "Omit --download to purge without re-downloading.")
    parser.add_argument("--tiles-purge-out-of-zone", "--dalles-purger-hors-zone", action="store_true",
                        dest="dalles_purger_hors_zone",
                        help="Delete from cache the tiles outside the current zone (bbox/department). "
                             "Useful to free space taken by tiles of other departments. "
                             "Requires --zone-department, --zone-bbox, --zone-city or --zone-gps.")
    parser.add_argument("--shadings-compress", "--ombrages-compresser",  action="store_true",
                        dest="ombrages_compresser", help="Compress existing raw shadings (DEFLATE)")
    parser.add_argument("--download-overwrite", "--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Overwrite & re-download cached tiles, incl. LAZ point clouds (same as --download-force)")
    parser.add_argument("--shadings-overwrite", "--ombrages-ecraser", action="store_true", dest="ombrages_ecraser",
                        help="Overwrite existing shadings")
    parser.add_argument("--svf-sweep", action=argparse.BooleanOptionalAction,
                        default=True, dest="sweep_horizon",
                        help="SVF sweep-horizon kernel with running max on a deque "
                             "(upper convex hull). O(W·H·N) complexity instead of "
                             "O(W·H·N·max_r). Speedup ~×5-15 for SVF20m, ~×30-50 "
                             "for SVF100m, several hundred for large radii. "
                             "Slight NN aliasing at low gradients, imperceptible "
                             "for structures > 1-2 px. Default: enabled "
                             "(--no-svf-sweep to disable).")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Overwrite existing tiles/MBTiles/.map")
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["mbtiles","rmap","sqlitedb","map","gz","geojson",
                                 "transparent-raster"],
                        default=[], metavar="FMT",
                        help="Output file formats (multi-value; default for --lidar: mbtiles): "
                             "mbtiles rmap sqlitedb "
                             "(raster) ; map geojson gz (vector) ; transparent-raster "
                             "(transparent PNG tiles rasterizing OSM/IGN vector -> .sqlitedb "
                             "overlay for OsmAnd over the LiDAR).")
    parser.add_argument("--source", metavar="PATH", default=None,
                        help="Existing source file. MBTiles conversion needs no zone; "
                             "TIF and PBF processing still require a geographic area. "
                             ".tif/.tiff: existing shading → MBTiles/RMAP "
                             "            (CRS auto-detected: 3857=direct tiling, other=warp). "
                             ".mbtiles  : conversion → RMAP (requires rmap format). "
                             ".pbf      : OSM data → map (requires --osm). "
                             "Ex: --source var_83_hillshade_multi.tif --zone-bbox ... --file-formats mbtiles rmap "
                             "Ex: --source provence-alpes-cote-d-azur-latest.osm.pbf --osm")
    parser.add_argument("--zoom-min", type=int, default=13, metavar="N",
                        help="Minimum MBTiles zoom (default: 13)")
    parser.add_argument("--zoom-max", type=int, default=18, metavar="N",
                        help="Maximum MBTiles zoom (default: 18)")
    parser.add_argument("--image-quality", "--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="JPEG quality of tile images (default: 85). "
                             "75 = -35%% size, almost invisible. 60 = -55%%, slight blur.")
    parser.add_argument("--image-format", "--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format of tile images: auto, jpeg or png (default: auto).")
    parser.add_argument("--osm", action="store_true",
                        help="Generate a vector OSM overlay MBTiles "
                             "(paths, place names, hydrography, historical sites). "
                             "The Geofabrik PBF is downloaded automatically if absent.")
    parser.add_argument("--layer", "--couche", metavar="TAGS", nargs="+", default=None, dest="couche",
                        help="For --osm: OSM tags to include. "
                             "Ex: --layer highway=* waterway=* natural=water")
    return parser


from _terrain_sources import (
    DependancesSourcesTerrain as _DependancesSourcesTerrain,
    traiter_source_autonome as _traiter_source_autonome_impl,
    traiter_source_wmts as _traiter_source_wmts_impl,
)


def _dependances_sources_terrain():
    return _DependancesSourcesTerrain(
        generer_rmap=generer_rmap_depuis_mbtiles,
        generer_sqlitedb=generer_sqlitedb_depuis_mbtiles,
        historique=_historique_depuis_argv,
        hist_t_debut=_HIST_T_DEBUT,
    )


def _traiter_source_autonome(args):
    """Façade compatible vers le traitement autonome LiDAR/OSM."""
    return _traiter_source_autonome_impl(
        args,
        dependances=_dependances_sources_terrain(),
    )


from _terrain_resolution import (
    DependancesResolutionTerrain as _DependancesResolutionTerrain,
    resoudre_zone_lidar as _resoudre_zone_lidar_impl,
)


def _resoudre_zone_lidar(args, _osm_seul):
    """Façade historique vers le résolveur de zone terrain extrait."""
    return _resoudre_zone_lidar_impl(
        args,
        _osm_seul,
        dependances=_DependancesResolutionTerrain(
            provider=PROVIDER,
            normaliser_nom=normaliser_nom,
            regions_disponibles=_regions_disponibles,
            geocoder_region=geocoder_region,
            geocoder_departement=geocoder_departement,
            calculer_grille_bbox=calculer_grille_bbox,
            bbox_enveloppe_transform=_bbox_enveloppe_transform,
            wgs84_vers_natif=_wgs84_vers_natif,
            nom_zone_bbox_auto=_nom_zone_bbox_auto,
            nom_zone_gps_auto=_nom_zone_gps_auto,
            geocoder_ville_natif=geocoder_ville_natif,
            calculer_grille=calculer_grille,
            parse_block=_parse_block,
            calculer_sous_zones_priori=_calculer_sous_zones_priori,
        ),
    )


from _osm_outputs import (
    DependancesSortiesOsm as _DependancesSortiesOsm,
    produire_sorties_osm as _produire_sorties_osm_impl,
)


def _produire_sorties_osm(bbox_wgs84, dossier, nom_zone, osm_pbf, *,
                          formats, osm_tags=None, ecraser=False,
                          skip_bbox=False, zoom_min=8, zoom_max=18):
    return _produire_sorties_osm_impl(
        bbox_wgs84, dossier, nom_zone, osm_pbf,
        formats=formats,
        osm_tags=osm_tags,
        ecraser=ecraser,
        skip_bbox=skip_bbox,
        zoom_min=zoom_min,
        zoom_max=zoom_max,
        dependances=_DependancesSortiesOsm(
            generer_carte=generer_carte_osm,
            rasteriser=rasteriser_geojson_transparent,
        ),
    )


_produire_sorties_osm.__doc__ = _produire_sorties_osm_impl.__doc__


def main():
    t_debut = time.time()
    parser = _construire_parser_lidar()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Contrat CLI utile et minimal : un workflow explicite + une zone suffit.
    # Les conversions --source constituent leur propre intention et restent
    # utilisables sans --lidar. --osm est géré dans ce même parser.
    if not args.ignlidar and not args.osm and not args.source:
        parser.error("choose a workflow: --lidar or --osm (or pass --source for a conversion)")

    _valider_contrat_cli_lidar(args, parser)

    _source_ext_cli = Path(args.source).suffix.lower() if args.source else ""
    if (not _zone_cli_presente(args)
            and _source_ext_cli not in (".mbtiles",)):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )

    _appliquer_defauts_cli_lidar(args)

    _valider_zooms(args, parser)
    _appliquer_cache_dir(args)   # avant tout accès au cache (dalles, discover, osm)
    _appliquer_production_dir(args)   # racine des .tif LAZ (produits)
    _configurer_cloud_cache(args)     # nuage .laz au cache, .tif en production

    # --shading TYPE:k=v répétable → instances paramétrées. Les types sont
    # reflétés dans args.ombrages pour que les gates existants (qui testent
    # la présence d'ombrages demandés) voient ces instances ; au dispatch,
    # les types couverts par une instance explicite sont RETIRÉS de choix
    # (sinon ils seraient aussi générés aux params par défaut).
    args.shading_instances = None
    if getattr(args, "shading_specs", None):
        _insts = []
        for _spec in args.shading_specs:
            try:
                _insts.append(parser_shading_spec(_spec))
            except ValueError as _e_spec:
                parser.error(f"--shading : {_e_spec}")
        args.shading_instances = _insts
        args.ombrages = list(dict.fromkeys(
            (args.ombrages or []) + [t for t, _ in _insts]))

    # Preset de stack par resolution (opt-in) : ajoute svf/opos/lrm dimensionnes
    # en metres pour la resolution du provider (+ multi/slope), via le meme
    # mecanisme d'instances (nommage/cache preserves). Les types couverts par une
    # instance ne sont pas re-generes aux params par defaut (cf. dispatch).
    if getattr(args, "shading_preset", None):
        _pname, _pinsts, _pelev = _resoudre_preset_shading(args.shading_preset, RESOLUTION_M)
        args.shading_instances = (args.shading_instances or []) + _pinsts
        args.ombrages = list(dict.fromkeys(
            (args.ombrages or []) + ["multi", "slope"] + [t for t, _ in _pinsts]))
        if args.ombrages_elevation is None:
            args.ombrages_elevation = _pelev
        _pd = _pinsts[0][1]["dist"]; _ps = _pinsts[2][1]["sigma"]
        print(f"  Shadings preset '{_pname}' (res {RESOLUTION_M:g} m): "
              f"svf/opos radius {_pd:g} m, lrm sigma {_ps:g} m, sun "
              f"{args.ombrages_elevation}°")

    # Propage --apikey au provider actif s'il en utilise une (us-3dep, etc.).
    if hasattr(PROVIDER, "set_apikey"):
        PROVIDER.set_apikey(args.apikey)

    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    args.transparent_raster = "transparent-raster" in _ff

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    # Si le pipeline crashe, l'entrée reste → diagnostic facile.
    _historique_debut()

    _osm_seul = args.osm and not args.telechargement and not args.ombrages and not args.mbtiles

    print("=" * 55)
    if _osm_seul:
        print("  OSM vector map")
    else:
        print(f"  LiDAR : {PROVIDER.NAME}")
        print("  Pipeline rasterio + numpy (numba for SVF)")
    print("=" * 55)
    print(f"  Folder : {args.dossier or str(DOSSIER_TRAVAIL / LIDAR_SUBDIR)}")
    print()

    _traiter_source_autonome(args)

    # -------------------------------------------------------
    # Sélection de zone → liste de dalles
    # -------------------------------------------------------
    bbox, nom_zone, cx, cy, _blk = _resoudre_zone_lidar(args, _osm_seul)

    # --laz-parallel N : N conversions LAZ simultanees. On pose OMP_NUM_THREADS
    # (coeurs/N) AVANT le 1er import CSF (lazy) et on elargit le semaphore de
    # conversion. Chaque conversion ~3 Go de RAM : c'est a l'utilisateur de tenir
    # la RAM (N x 3 Go). CSF scale mal en threads -> N conv a OMP=coeurs/N > 1 a
    # OMP=tous, sur une VM multi-coeurs. HISSÉ ICI, avant le branchement découpé :
    # sinon le return du mode --split-* saute cette config et sérialise TOUT un run
    # découpé (le pool de download est bien dimensionné L11208, mais _CONV_SEM reste
    # à 1). Un département SE traite en découpé : c'est là que le bug mordait.
    if getattr(args, "laz_parallel", 1) and args.laz_parallel > 1:
        _cores = os.cpu_count() or 1
        _omp = max(1, _cores // args.laz_parallel)
        os.environ["OMP_NUM_THREADS"] = str(_omp)
        from providers import common as _common_par
        _common_par.set_laz_parallelism(args.laz_parallel)
        print(f"  LAZ parallel : {args.laz_parallel} conversions simultanees "
              f"x {_omp} threads OMP ({_cores} coeurs) — prevoir ~{3*args.laz_parallel} Go RAM")


    # ── A-priori splitting: traitement séquentiel morceau par morceau ────────
    _cols_pr  = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr  = getattr(args, "rows_decoupe", 0) or 0
    _cote_pr  = getattr(args, "split_width", 0.0) or 0.0
    if ((_cols_pr > 0 and _rows_pr > 0) or _cote_pr > 0) and not _osm_seul:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            bbox[0], bbox[1], bbox[2], bbox[3],
            0, _cote_pr, unite_m=True, n_cols=_cols_pr, n_rows=_rows_pr)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR)
            # Overwrite explicite perce la reprise (cf. jumeau WMTS). LiDAR inclut
            # ombrages_ecraser (pas de shadings côté WMTS) : spécialisation gardée.
            # telechargement_forcer (--download-force) converge avec
            # telechargement_ecraser côté download (_force_dl) et la doc les dit
            # équivalents : sans lui ici, --download-force re-tirait la source
            # mais la reprise sautait la reconstruction du chunk → données
            # fraîches jamais reconstruites en mode découpé (R1#10).
            _overwrite_actif = (args.tuiles_ecraser or args.ombrages_ecraser
                                or args.telechargement_ecraser
                                or args.telechargement_forcer)
            def _entete_lidar(c):
                bx1, by1, bx2, by2 = c
                surface = (bx2-bx1)/1000 * (by2-by1)/1000
                return (f"BBox natif : {bx1:.0f},{by1:.0f} → "
                        f"{bx2:.0f},{by2:.0f}  (~{surface:.0f} km²)")
            if _blk:
                # --block : machines séparées, pas de disque partagé entre
                # voisins -> marge fixe garantie (_traiter_bbox_lidar), seul
                # mode qui la justifie (cf. discussion "mode rare, ne doit
                # pas justifier un mouton à 5 pattes pour le cas majoritaire").
                def _chunk_lidar(coords, nom_z, cle, manifeste):
                    return _traiter_bbox_lidar(
                        args, coords, nom_z, nom_zone, manifeste, cle)
                _executer_split_historise(
                    lambda: _run_split_priori(
                        args, sous_zones, mode_desc, nom_zone, racine_pr,
                        _overwrite_actif, _entete_lidar, _chunk_lidar, t_debut),
                    t_debut, racine_pr)
            else:
                # Cas majoritaire : VRT-voisins glissant, zéro téléchargement
                # supplémentaire (cf. _run_split_priori_lidar_glissant).
                _executer_split_historise(
                    lambda: _run_split_priori_lidar_glissant(
                        args, sous_zones, nom_zone, racine_pr,
                        _overwrite_actif, _entete_lidar, t_debut),
                    t_debut, racine_pr)
            return
        print("  A-priori splitting: zone too small -> single pass")

    # R2#38 : --min-free-gb doit aussi garder le mode MONOLITHIQUE. Sans split,
    # _run_split_priori (et son _garde_disque par chunk) n'est jamais appelé →
    # le seuil était silencieusement ignoré. Couvre les deux entrées mono :
    # split non demandé, ou zone trop petite pour être découpée. Vérif AVANT de
    # démarrer (un run mono sur grande zone sature un petit volume comme un chunk).
    _garde_disque(Path(args.dossier).resolve() if args.dossier else DOSSIER_TRAVAIL,
                  getattr(args, "min_free_gb", 0.0) or 0.0, "single-pass", 0, 1)

    etapes_total = sum([bool(args.telechargement),
                        bool(args.ombrages),
                        # rmap/sqlitedb passent aussi par l'étape MBTiles
                        bool(args.mbtiles or args.rmap or args.sqlitedb),
                        bool(args.osm)])
    etapes_total = max(1, etapes_total)
    etape_cur = [0]
    etape_t0  = [time.time()]
    def print_etape(nom):
        # Cancellation au passage entre 2 étapes : si l'utilisateur a fait
        # Ctrl+C pendant l'étape précédente, on finit le print de bilan
        # mais on raise avant d'imprimer le marqueur de la suivante.
        # Le KeyboardInterrupt remonte au main() qui peut faire son cleanup.
        if etape_cur[0] > 0:
            elap  = int(time.time() - etape_t0[0])
            cumul = int(time.time() - t_debut)
            print(f"  ✓ Step {etape_cur[0]} finished in {_hms(elap)}  (cumulative {_hms(cumul)})")
        if _stop_event.is_set():
            raise KeyboardInterrupt("Interruption demandée — étapes restantes skipped")
        etape_cur[0] += 1
        etape_t0[0] = time.time()
        print("STEP:" + str(etape_cur[0]) + "/" + str(etapes_total) + " " + nom, flush=True)

    if args.telechargement:
        print_etape("Downloading tiles")
    if args.telechargement_forcer:
        print("  Update: existing tiles re-downloaded")
    if args.workers != NB_WORKERS:
        print(f"  Workers : {args.workers}")

    # Compression cache : ON par defaut depuis v1.14 (16→7 Mo par dalle FR,
    # ~90→40 Go par departement) ; --no-download-compress pour du brut.
    # Aucun prompt : l'outil est pilote par flags (CLI + GUI), jamais interactif ici.
    compresser = bool(args.telechargement_compresser)
    if args.telechargement:
        print(f"  -> {'Compression enabled' if compresser else 'Raw storage'}")

    racine        = Path(args.dossier).resolve() if args.dossier else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR
    dossier_ville  = racine
    dossier_dalles = _dossier_dalles_actif(args, dossier_ville)
    _sans_telechargement = not getattr(args, "telechargement", False)
    _sans_ombrages = not getattr(args, "ombrages", None)
    if not _osm_seul and not (_sans_telechargement and _sans_ombrages):
        try:
            dossier_dalles.mkdir(parents=True, exist_ok=True)
        except (FileNotFoundError, OSError) as _e_dd:
            print(f"  ERROR: tiles folder inaccessible: {dossier_dalles}")
            print(f"  ({_e_dd})")
            print("  Check that the disk is connected and relaunch.")
            sys.exit(1)
    if not _osm_seul:
        dossier_ville.mkdir(parents=True, exist_ok=True)
    print(f"\n  Root    : {racine}")
    if not _osm_seul:
        _est_laz = PROVIDER.CODE.endswith("-laz")
        print(f"  Tiles   : {dossier_dalles}"
              + ("  (produced .tif -> production)" if _est_laz else ""))
        if _est_laz and not args.dossier_dalles:
            print(f"  Cloud   : {DOSSIER_CACHE / LIDAR_SUBDIR}  (downloaded .laz kept in cache)")
        print(f"  Zone    : {dossier_ville}")

    # -------------------------------------------------------
    # Purge des dalles invalides (< 2 MB = mer, erreurs)
    # -------------------------------------------------------
    if args.dalles_purger_invalides and dossier_dalles.exists():
        SEUIL_VALIDE = SEUIL_DALLE_VALIDE
        invalides = [f for f in _rglob_tif_robuste(dossier_dalles)
                     if f.stat().st_size < SEUIL_VALIDE]
        if invalides:
            print(f"\n  Invalid purge: {len(invalides)} tile(s) < 2 MB...")
            for f in invalides:
                f.unlink()
            print(f"  Purge done. {len(invalides)} files removed.")
        else:
            print("  No invalid tile found (all >= 50 MB).")

    # -------------------------------------------------------
    # Purge des dalles hors zone courante
    # -------------------------------------------------------
    if args.dalles_purger_hors_zone and dossier_dalles.exists():
        # Source de vérité : dalles_zone.txt (généré par le WFS)
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        if dalles_zone_txt.exists():
            noms_zone_purge = set(dalles_zone_txt.read_text(encoding="utf-8").splitlines())
            noms_zone_purge = {n.strip() for n in noms_zone_purge if n.strip()}
            print(f"  Out-of-zone purge: reference {dalles_zone_txt.name}"
                  f" ({len(noms_zone_purge)} zone tiles)")
        else:
            print(f"  ERROR out-of-zone purge: {dalles_zone_txt.name} not found.")
            print("  Relaunch with --download to rebuild the list explicitly.")
            sys.exit(1)
        toutes = _rglob_tif_robuste(dossier_dalles)
        # #2 : le cache est indexé par PAYS (lidar/<pays>), donc plusieurs
        # providers peuvent cohabiter dans dossier_dalles (us-tnm + us-3dep, les
        # DGM1 allemands...). On ne purge QUE les dalles que le provider courant
        # reconnaît comme siennes (son subdir_from_name matche le nommage) : sinon
        # purger la zone A d'un provider effacerait les dalles d'un AUTRE provider
        # du même pays (perte de données silencieuse). Les nommages sont disjoints
        # (préfixes us3dep_/usgs_1m_/he_dgm1_/LHD_FXX_...), la discrimination est
        # fiable. Providers à subdir_from_name=None (dalles à la racine) : purge
        # neutralisée pour eux, dégradation acceptable vs. suppression croisée.
        def _est_du_provider(nom):
            try:
                return PROVIDER.subdir_from_name(nom) is not None
            except Exception:
                return False
        hors_zone = [f for f in toutes
                     if f.name not in noms_zone_purge and _est_du_provider(f.name)]
        if hors_zone:
            taille_go = sum(f.stat().st_size for f in hors_zone) / 1e9
            print(f"\n  Out-of-zone purge: {len(hors_zone)} tile(s) - {taille_go:.1f} GB")
            # Purge declenchee explicitement par --tiles-purge-out-of-zone : on
            # execute sans reconfirmer (pas de prompt interactif).
            for f in hors_zone:
                f.unlink()
            if hors_zone:
                print(f"  {len(hors_zone)} tiles removed, {taille_go:.1f} GB freed.")
        else:
            print("  No out-of-zone tile found.")

    # -------------------------------------------------------
    # Découverte des dalles via le provider — source de vérité unifiée
    # -------------------------------------------------------
    # Calculé une fois ici, utilisé par la cache-check ET le download.
    # Pour FR : TMS + fallback grille → dict {nom: url}.
    # Pour NL : index JSON kaartbladen → dict {nom: url}.
    # Provider-agnostique : aucune hypothèse sur la géométrie des tuiles.
    # OSM-seul : aucune dalle LiDAR nécessaire — NE PAS interroger le provider
    # (discover_dalles déclenche une requête TMS coûteuse : une région entière =
    # des milliers de tuiles d'index pour rien). La section OSM recalcule sa
    # propre bbox WGS84 plus bas, donc bbox_wgs peut rester None ici.
    if _osm_seul:
        bbox_wgs = None
        dalles_dict = {}
        noms_attendus = set()
    else:
        _t_wgs = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
        _lo1, _la1, _lo2, _la2 = _bbox_enveloppe_transform(
            _t_wgs.transform, bbox[0], bbox[1], bbox[2], bbox[3])
        bbox_wgs = (_lo1 - 0.05, _la1 - 0.05, _lo2 + 0.05, _la2 + 0.05)
        # Cache per-provider : schemas incompatibles (TMS dict vs GeoJSON, etc.).
        cache_discover = DOSSIER_CACHE / f"discover_{PROVIDER.CODE}.json"
        # discover_dalles : None = échec réseau/endpoint, {} = pas de couverture.
        # On distingue les deux (sinon une panne de portail ressemble à "rien
        # ici") et on protège l'appel : un provider qui lève ne doit pas casser
        # tout le run, juste signaler la zone comme indisponible.
        try:
            _d = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover)
            if _d is None:
                print("  ⚠ Tile discovery unavailable (network/endpoint),"
                      " zone skipped, retry.", flush=True)
        except Exception as _e_disc:
            print(f"  ⚠ Tile discovery failed ({type(_e_disc).__name__}:"
                  f" {_e_disc}), zone skipped, retry.", flush=True)
            _d = None
        dalles_dict = _d or {}
        noms_attendus = set(dalles_dict.keys())

        # Aucune dalle pour cette zone quand --download est demande :
        #   _d is None  -> echec reseau/endpoint (deja signale "reessayez")
        #   _d == {}     -> zone hors couverture (resultat legitime, ex. IGN
        #                   LiDAR HD non publie : le TMS n'indexe rien)
        # Rien a telecharger ni a assembler : on sort ici plutot que de laisser
        # le pipeline planter plus loin sur dalles_zone.txt absent.
        if args.telechargement and not dalles_dict and not args.source:
            _duree_decouverte = max(0, int(time.time() - t_debut))
            if _d is None:
                _historique_depuis_argv(
                    _duree_decouverte, str(dossier_ville), statut="ko")
                sys.exit(1)   # echec transitoire : code non-zero (re-tenter)
            print("  No LiDAR tile for this zone (out of coverage), "
                  "nothing to download.")
            print(f"  Done! Folder: {dossier_ville}")
            _historique_depuis_argv(
                _duree_decouverte, str(dossier_ville), statut="ok")
            return

    # -------------------------------------------------------
    # Détecter si on peut sauter le téléchargement
    # -------------------------------------------------------
    sauter_telechargement = False

    # Si seul --osm est demandé (pas --ignlidar, pas d'ombrages, pas de mbtiles LiDAR)
    # on peut passer directement à la partie OSM sans vérifier les dalles
    if _osm_seul:
        sauter_telechargement = True

    # Tuiles seules (pas de téléchargement, pas d'ombrages) : pas besoin des dalles
    if not args.telechargement and not args.ombrages:
        sauter_telechargement = True

    if not sauter_telechargement and not args.telechargement:
        # --source .tif ou .mbtiles : pas besoin des dalles IGN
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff", ".mbtiles"):
            sauter_telechargement = True
        else:
            dalles_existantes = _rglob_tif_robuste(dossier_dalles) if dossier_dalles.exists() else []
            if not dalles_existantes:
                print("\n  WARNING: downloads are disabled and no cached tile was found.")
                print(f"  Tiles folder : {dossier_dalles}")
                print("  Remove --no-download (normal --lidar default), or add "
                      "--download to a maintenance command.")
                sys.exit(1)
            # Vérification zone-spécifique : parmi les dalles du cache, combien
            # couvrent réellement la zone demandée ? Le cache peut contenir des
            # dalles d'autres zones (autres tests précédents). Si aucune dalle
            # ne couvre la zone, on plante avec un message clair plutôt que de
            # laisser le pipeline continuer puis échouer plus loin.
            if noms_attendus:  # discover_dalles a retourné une liste non-vide
                dalles_zone_cache = [d for d in dalles_existantes
                                     if d.name in noms_attendus
                                     and d.stat().st_size > SEUIL_DALLE_VALIDE]
                if not dalles_zone_cache:
                    print(f"\n  WARNING: {len(dalles_existantes)} tile(s) in cache,")
                    print("              but NONE covers the requested zone.")
                    print(f"  Global cache: {dossier_dalles}")
                    libelle_zone = args.zone_ville or nom_zone
                    print(f"  Requested zone: {len(noms_attendus)} tile(s) around "
                          f"{libelle_zone}")
                    print("  Remove --no-download (normal --lidar default), or add "
                          "--download to a maintenance command.")
                    sys.exit(1)
                print(f"\n  Download skipped "
                      f"({len(dalles_zone_cache)}/{len(noms_attendus)} zone tile(s) found in cache)")
            else:
                # Provider sans index pour cette bbox (cas dégradé) : juste compter
                print(f"\n  Download skipped ({len(dalles_existantes)} tile(s) in cache)")
            sauter_telechargement = True

    # -------------------------------------------------------
    # Téléchargement + assemblage (pivoté sur PROVIDER.discover_dalles)
    # -------------------------------------------------------
    if not sauter_telechargement:
        # dalles_dict a déjà été calculé plus haut via PROVIDER.discover_dalles.
        # Orchestration download + persistance via le helper provider-agnostique.
        _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args)

    # -------------------------------------------------------
    # Ombrages
    # -------------------------------------------------------
    # Dalles disponibles pour les ombrages :
    # 1. Seulement les dalles de la zone courante (filtre par nom)
    # 2. Seulement les fichiers valides (≥ 50 MB)
    # Le dossier dalles est global — sans filtrage par zone, le VRT couvrirait
    # tous les départements présents et le hillshade serait énorme ou en erreur.
    if dossier_dalles.exists() and not _osm_seul:
        # _osm_seul court-circuité ici : sa bbox vaut le sentinel (0,0,0,0), qui ne
        # matcherait jamais l'en-tête d'un dalles_zone.txt existant et déclencherait
        # sa suppression (revue code mort 2026-07-22, #21). L'OSM-seul n'a de toute
        # façon aucun ombrage LiDAR à assembler → dalles_ombrages = [] (branche else).
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        noms_zone = set()  # initialisé ici — peut rester vide en mode OSM seul
        if dalles_zone_txt.exists():
            # Vérifier que l'en-tête (bbox + provider) correspond au run courant
            _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
            _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
            _bbox_fichier  = _lignes[0].strip() if _lignes else ""
            if not _dalles_zone_hdr_ok(_lignes, bbox):
                print(f"  Zone/provider changed - rebuilding {dalles_zone_txt.name} from cache...")
                print(f"    Ancienne bbox : {_bbox_fichier}")
                print(f"    Nouvelle bbox : {_bbox_courante}")
                # Reconstruire depuis le cache disque sans retélécharger.
                # noms_attendus vient de PROVIDER.discover_dalles (provider-agnostique).
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_attendus and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    _ecrire_dalles_zone(
                        dalles_zone_txt, bbox, noms_zone
                    )
                    print(f"  {dalles_zone_txt.name} rebuilt: {len(noms_zone)} tile(s) in cache")
                else:
                    # L'ancien fichier porte un en-tête différent et sera donc
                    # ignoré, mais on ne le détruit pas tant qu'aucune nouvelle
                    # liste complète n'a pu être publiée.
                    print("  No tile in cache for this zone - enable downloads")
                    noms_zone = set()
            else:
                noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
                print(f"  Zone tiles list: {dalles_zone_txt.name} ({len(noms_zone)} tiles)")
        elif not args.telechargement and noms_attendus:
            # Si seul --osm demandé, pas besoin des dalles
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # on ne cherche pas les dalles
            else:
                # dalles_zone.txt absent mais liste attendue connue → reconstruction
                # depuis le cache disque (la vérification en amont garantit qu'on
                # trouvera au moins une dalle).
                print(f"  Rebuilding {dalles_zone_txt.name} from disk cache...")
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_attendus and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    _ecrire_dalles_zone(
                        dalles_zone_txt, bbox, noms_zone
                    )
                    print(f"  dalles_zone.txt rebuilt: {len(noms_zone)} tile(s) found on disk")
                else:
                    print(f"  ERROR: no tile of the zone found in {dossier_dalles}")
                    print("  Relaunch without --no-download, or pass --download explicitly.")
                    sys.exit(1)
        else:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # mode OSM seul — pas besoin de dalles
            else:
                print(f"\n  ERROR: {dalles_zone_txt.name} not found in {dossier_ville}/")
                print("  This file is created automatically during download.")
                print("  Relaunch without --no-download, or pass --download explicitly.")
                print("  (Tiles already present on disk will be skipped, ~a few seconds)")
                sys.exit(1)
        toutes_dalles    = sorted(_rglob_tif_robuste(dossier_dalles))
        dalles_zone      = [d for d in toutes_dalles if d.name in noms_zone]
        dalles_ombrages  = [d for d in dalles_zone   if d.stat().st_size > SEUIL_DALLE_VALIDE]
        nb_hors_zone     = len(toutes_dalles) - len(dalles_zone)
        nb_invalides     = len(dalles_zone)   - len(dalles_ombrages)
        if not _osm_seul:
            if nb_hors_zone:
                print(f"  {nb_hors_zone} out-of-zone tile(s) skipped (other departments)")
            if nb_invalides:
                print(f"  {nb_invalides} invalid tile(s) skipped (< 2 MB - sea or out of coverage)")
            print(f"  {len(dalles_ombrages)} tile(s) kept for shadings")
    else:
        dalles_ombrages = []
    # -------------------------------------------------------
    # -------------------------------------------------------
    # Compression des ombrages existants (rasterio)
    # -------------------------------------------------------
    if args.ombrages_compresser:
        try:
            import rasterio as _rio_cmp
        except ImportError:
            print("  ERROR: rasterio missing, run pip install rasterio")
        else:
            tifs_bruts = [
                t for t in dossier_ville.glob("*.tif")
                if not t.name.startswith("_")
                and not re.search(r'_tuilage_z\d+\.tif$', t.name)
            ]
            # Filtrer ceux non compresseds (taille > seuil heuristique : >500 MB)
            tifs_a_compresser = [t for t in tifs_bruts if t.stat().st_size > 500e6]
            if not tifs_a_compresser:
                print("  No raw shading found (> 500 MB) to compress.")
            else:
                print(f"  {len(tifs_a_compresser)} file(s) to compress:")
                for chemin_out in sorted(tifs_a_compresser):
                    taille_brut = chemin_out.stat().st_size / 1e6
                    chemin_part = _chemin_part(chemin_out)
                    t0_cmp = time.time()
                    try:
                        # L'ancien final reste la source lisible jusqu'au
                        # remplacement atomique de la copie recompressée.
                        with _rio_cmp.open(str(chemin_out)) as src:
                            profile = src.profile.copy()
                            for _k_cmp in (
                                "driver", "BIGTIFF", "bigtiff",
                                "NODATA", "nodata",
                            ):
                                profile.pop(_k_cmp, None)
                            profile.update({
                                "driver":     "GTiff",
                                "compress":   "deflate",
                                "predictor":  2,
                                "tiled":      True,
                                "blockxsize": 512,
                                "blockysize": 512,
                                "BIGTIFF":    "IF_SAFER",
                            })
                            if src.nodata is not None:
                                profile["nodata"] = src.nodata
                            with _rio_cmp.open(str(chemin_part), "w", **profile) as dst:
                                # Copier bande par bande avec windowed reads
                                # pour borner la RAM (un ombrage 50000×50000 px
                                # uint8 = 2.5 Go en mémoire — trop gros).
                                for ji, window in src.block_windows(1):
                                    for b in range(1, src.count + 1):
                                        dst.write(src.read(b, window=window),
                                                  b, window=window)
                        _publier_tif_atomique(chemin_part, chemin_out)
                        elap = time.time() - t0_cmp
                        taille_cmp = chemin_out.stat().st_size / 1e6
                        gain = int((1 - taille_cmp / taille_brut) * 100)
                        print("  " + chemin_out.name.ljust(56) +
                              str(round(taille_brut)).rjust(6) + " MB -> " +
                              str(round(taille_cmp)).rjust(5) + " MB  (-" +
                              str(gain) + "%)  " + _hms(elap))
                    except BaseException as _e_cmp:
                        chemin_part.unlink(missing_ok=True)
                        if isinstance(_e_cmp, (KeyboardInterrupt, SystemExit)):
                            raise
                        print(f"  ERROR compressing {chemin_out.name}: {_e_cmp}")

    choix_ombrages, spec_insts = _resoudre_choix_ombrages(args)
    if not dalles_ombrages:
        choix_ombrages = []  # pas de dalle disponible → rien à calculer

    tifs_run = None   # cibles du run courant (None = pas d'étape shadings)
    if choix_ombrages or spec_insts:
        surface_km2 = len(dalles_ombrages)  # ~1 dalle = 1 km²
        _libelles = choix_ombrages + [
            t + (":" + ",".join(f"{k}={v:g}" if isinstance(v, float) else f"{k}={v}"
                                for k, v in p.items()) if p else "")
            for t, p in spec_insts]
        print_etape("Shadings " + ", ".join(_libelles))
        print(f"  Shadings : {', '.join(_libelles)}")
        elev = args.ombrages_elevation if args.ombrages_elevation is not None else ELEVATION_SOLEIL
        print(f"  Sun angle : {elev}°")
        print(f"  Area: ~{surface_km2} km²  |  Estimated duration:"
              f" {'5-10 min' if surface_km2 < 100 else '15-45 min' if surface_km2 < 500 else '1h+'}"
              f" (depends on the shading type and machine)", flush=True)
        tifs_run = generer_ombrages(dalles_ombrages, dossier_ville, choix_ombrages,
                         elevation_soleil=elev, nom_zone=nom_zone,
                         ecraser_ombrages=args.ombrages_ecraser,
                         use_sweep=args.sweep_horizon,
                         svf_gamma=args.svf_gamma,
                         svf_conv=args.svf_conv, svf_dist=args.svf_dist,
                         bbox_natif=tuple(bbox),
                         instances=spec_insts or None)

    # ── MBTiles + RMAP ─────────────────────────────────────────────────────────
    # Verdict agrégé du chemin monolithique. Les helpers signalent les échecs
    # sans toujours lever (génération à 0 tuile, conversion RMAP/SQLiteDB
    # refusée...) : perdre ce booléen ferait historiser ``ok`` et sortir 0.
    _livrables_raster_ok = True
    if args.mbtiles or args.rmap or args.sqlitedb:
        # Source : --source .tif ou ombrages générés dans dossier_ville
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff"):
            # --source explicite
            _tif_src = Path(args.source).resolve()
            print_etape(f"{'RMAP' if args.rmap and not args.mbtiles else 'MBTiles'} depuis {_tif_src.name}")
            print(f"  Source : {_tif_src}")
            print(f"  Zone   : bbox natif {bbox[0]:.0f},{bbox[1]:.0f} → {bbox[2]:.0f},{bbox[3]:.0f}")
            # Nom basé sur nom_zone + type d'ombrage détecté dans le nom du fichier
            _SUFFIXES = ("multi_ombrage", "315_ombrage", "045_ombrage",
                         "135_ombrage", "225_ombrage", "slope_ombrage",
                         "svf_ombrage", "svf_100m_ombrage", "lrm_ombrage",
                         "rrim_ombrage")
            _sfx = next((s for s in _SUFFIXES if s in _tif_src.stem), _tif_src.stem)
            _nom_base = f"{nom_zone}_{_sfx}"   # sans zoom — ajouté par generer_mbtiles_lidar
            _nom_mbt  = f"{_nom_base}_z{args.zoom_min}-{args.zoom_max}"
            # Générer MBTiles si demandé explicitement, ou si nécessaire pour RMAP/SQLiteDB
            _mbt_path = dossier_ville / f"{_nom_mbt}.mbtiles"
            _ecraser_l = args.tuiles_ecraser
            _mbt_requis = _mbtiles_a_regenerer(_mbt_path, _ecraser_l, source=_tif_src)
            _mbt_out = None
            if _mbt_requis:
                _mbt_out = generer_mbtiles_lidar(_tif_src, dossier_ville, _nom_base,
                                           zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                                           format_tuiles=args.formats_image,
                                           jpeg_quality=args.qualite_image,
                                           bbox_natif=bbox,
                                           source_already_warped=getattr(args, "_source_already_warped", False),
                                           ecraser_tuiles=_ecraser_l,
                                           tile_workers=_tile_workers_defaut())
            elif _mbt_path.exists():
                print(f"  Existing MBTiles: {_mbt_path.name}, direct split/conversion")
                _mbt_out = _mbt_path
            _livrables_raster_ok = (bool(_convertir_formats(
                _mbt_out, args, mbtiles_neuf=_mbt_requis))
                and _livrables_raster_ok)
        else:
            # Ombrages présents dans dossier_ville — glob/filtre/tuilage
            # factorisés avec le site jumeau _traiter_bbox_lidar
            # (cf. _lister_tifs_ombrages / _tuiler_tifs_ombrages).
            ombrages_tifs = _lister_tifs_ombrages(dossier_ville, tifs_run)
            if ombrages_tifs:
                print_etape("MBTiles")
                _livrables_raster_ok = (bool(_tuiler_tifs_ombrages(
                    args, ombrages_tifs, dossier_ville,
                    nom_zone, bbox, verbose=True))
                    and _livrables_raster_ok)
            else:
                print("  No shading found for MBTiles (generate --shadings first)")
                _livrables_raster_ok = False

    # ── Carte OSM vectorielle de superposition ───────────────────────────────
    dossier_osm = None   # défini si on arrive jusqu'au generer_carte_osm
    if args.osm:
        # Une demande OSM n'est réussie que si sa source, sa bbox et tous ses
        # livrables aboutissent. Les sorties LiDAR d'un run combiné restent
        # préservées, mais ne doivent pas masquer un échec vectoriel.
        _osm_livrables_ok = False
        print_etape("Carte OSM vectorielle")

        # Table département → URL Geofabrik : voir _GEOFABRIK au niveau module

        # Résoudre le PBF source
        pbf = None
        if args.source and Path(args.source).suffix.lower() in (".pbf", ".osm"):
            pbf = Path(args.source)
            if not pbf.exists():
                print(f"  ERROR: PBF file not found: {pbf}")
                pbf = None
        elif (getattr(PROVIDER, "COUNTRY", "fr") or "fr").lower() != "fr":
            # ── Garde-fou : le téléchargement auto est FRANCO-CENTRÉ ──────────
            # Trois maillons français en série : cx/cy convertis par
            # lamb93_to_wgs84_approx (or ils sont dans PROVIDER.CRS_NATIF), le
            # géocodage inverse geo.api.gouv.fr, et la table _GEOFABRIK de codes
            # INSEE — sans compter _GEOFABRIK_BASE_URL qui pointe .../europe/france.
            # Hors de France les trois échouent en chaîne et le repli
            # téléchargeait 4 Go de PBF FRANÇAIS pour produire un overlay vide :
            # échec silencieux et coûteux. On refuse explicitement (pbf reste
            # None → l'étape OSM est sautée, les sorties LiDAR d'un run combiné
            # sont préservées, même mécanisme que « --source introuvable »).
            # Geofabrik publie pourtant bien des sous-régions ailleurs (16 Länder
            # allemands, régions italiennes…) : généraliser demande une table de
            # slugs par pays + des bbox par géocodage Nominatim, pas juste de
            # lever ce garde. En attendant --source reste ouvert à tous les pays.
            print(f"  OSM auto-download is France-only for now "
                  f"(provider country: "
                  f"{(getattr(PROVIDER, 'COUNTRY', 'fr') or 'fr').lower()}).")
            print("  The department lookup and the Geofabrik URL table are "
                  "French; the fallback would fetch a 4 GB FRENCH PBF and "
                  "produce an overlay with no feature in your area.")
            print("  Workaround: grab the PBF for your area at "
                  "https://download.geofabrik.de/ then pass it with "
                  "--source <file>.pbf")
        else:
            # Téléchargement automatique — détecter le département depuis le centre
            _zone_region = getattr(args, "zone_region", None)
            num_dep = getattr(args, "zone_departement", None)

            if _zone_region:
                # Region explicite : slug Geofabrik direct, pas de détection
                # ni de géocodage inverse (on traitera tout le PBF, skip_bbox).
                region_slug = _zone_region.strip().lower()
            else:
                if not num_dep:
                    # Modes ville/gps/bbox : cx, cy sont en Lambert 93
                    # → convertir en WGS84 → requête geo.api.gouv.fr reverse
                    try:
                        clon, clat = lamb93_to_wgs84_approx(cx, cy)
                        url_rev = (f"https://geo.api.gouv.fr/communes"
                                   f"?lon={clon:.5f}&lat={clat:.5f}"
                                   f"&fields=codeDepartement&format=json")
                        with _urlopen(url_rev, timeout=10) as resp_rev:
                            data_rev = json.loads(resp_rev.read())
                        if data_rev:
                            num_dep = data_rev[0].get("codeDepartement")
                            print(f"  Department detected: {num_dep}", flush=True)
                    except Exception as e_rev:
                        print(f"  Reverse geocoding failed ({e_rev})")

                region_slug = _GEOFABRIK.get(num_dep) if num_dep else None
            if not region_slug:
                print(f"  Department {num_dep} not found in the Geofabrik table.")
                print("  Falling back to the national France PBF (~4 GB).")
                url_pbf = f"{_GEOFABRIK_BASE_URL_ROOT}/france-latest.osm.pbf"
                osm_dir = DOSSIER_CACHE / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / "france-latest.osm.pbf"
            else:
                url_pbf = f"{_GEOFABRIK_BASE_URL}/{region_slug}-latest.osm.pbf"
                osm_dir = DOSSIER_CACHE / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / f"{region_slug}-latest.osm.pbf"

            # Téléchargement PBF commun (national ou régional)
            _SEUIL_PBF = 1_000_000  # 1 MB minimum — PBF vide ou tronqué → re-télécharger
            # R2#30 : le PBF Geofabrik est un extrait « -latest » rafraîchi
            # QUOTIDIENNEMENT. L'ancien code le réutilisait indéfiniment dès qu'il
            # dépassait le seuil de taille (données OSM figées à la 1re exécution)
            # et --download-overwrite ne le refaisait pas. On respecte l'overwrite
            # (re-download forcé) et on affiche l'âge du cache (pas de re-download
            # AUTO sur l'âge : un PBF départemental fait 100 Mo-4 Go, ce serait
            # coûteux et surprenant — on avertit et on laisse l'utilisateur
            # décider via --download-overwrite).
            _force_pbf = bool(getattr(args, "telechargement_ecraser", False))
            _pbf_age_j = ((time.time() - pbf.stat().st_mtime) / 86400.0
                          if pbf.exists() else 0.0)
            if pbf.exists() and pbf.stat().st_size >= _SEUIL_PBF and not _force_pbf:
                print(f"  Existing PBF: {pbf.name}  "
                      f"({pbf.stat().st_size/1e9:.1f} GB, {_pbf_age_j:.0f} days old)")
                if _pbf_age_j > 30:
                    print(f"  Note: Geofabrik '-latest' is refreshed daily; this "
                          f"cache is {_pbf_age_j:.0f} days old. Pass "
                          f"--download-overwrite to refresh the OSM data.")
            else:
                if pbf.exists() and _force_pbf and pbf.stat().st_size >= _SEUIL_PBF:
                    print(f"  --download-overwrite: refreshing PBF {pbf.name} "
                          f"({_pbf_age_j:.0f} days old)")
                    pbf.unlink()
                elif pbf.exists():
                    print(f"  Truncated PBF ({pbf.stat().st_size} bytes) - re-downloading.")
                    pbf.unlink()
                _log_req(str(url_pbf), 'Geofabrik')
                print(f"  Downloading {url_pbf}...")
                print(f"  Destination : {pbf}", flush=True)
                # Écriture via .part + rename : un PBF présent est toujours
                # complet (un kill mi-téléchargement laissait un tronqué
                # > 1 Mo réutilisé comme "Existing PBF" au run suivant).
                pbf_part = pbf.parent / (pbf.name + ".part")
                try:
                    taille_dl = 0
                    t0_dl = time.time()
                    _pct_last = -1
                    # timeout : sans lui, une connexion Geofabrik figée
                    # bloque le run indéfiniment (s'applique à chaque read).
                    with _urlopen(url_pbf, timeout=60) as resp, \
                         open(pbf_part, "wb") as f_out:
                        total_size = int(
                            resp.headers.get("content-length", 0))
                        chunk = 65536
                        while True:
                            if _stop_event.is_set():
                                # R2#42 : consulter l'event À CHAQUE bloc. Avant, la
                                # boucle l'ignorait : sur un PBF de 4 Go (France
                                # entière) le 1er Ctrl+C posait juste l'event puis le
                                # download continuait ; il fallait un 2e Ctrl+C (sortie
                                # sèche du handler, .part orphelin). Idiome _stop_event
                                # des ~30 autres boucles interruptibles.
                                raise KeyboardInterrupt("PBF Geofabrik download interrupted")
                            data = resp.read(chunk)
                            if not data:
                                break
                            f_out.write(data)
                            taille_dl += len(data)
                            if total_size:
                                pct = taille_dl * 100 // total_size
                                mb  = taille_dl / 1e6
                                tot = total_size / 1e6
                                # Afficher seulement tous les 5%
                                if pct >= _pct_last + 5:
                                    _pct_last = pct
                                    line = f"  {mb:.0f} / {tot:.0f} MB  {pct}%"
                                    # \r sur le terminal, nouvelle ligne dans le log
                                    sys.stdout.write(f"\r{line}")
                                    sys.stdout.flush()
                    # Effacer la ligne de progression
                    sys.stdout.write("\r" + " " * 40 + "\r")
                    print(f"  Telecharge : {pbf.name}  "
                          f"({taille_dl/1e6:.0f} MB)  "
                          f"{_hms(time.time()-t0_dl)}")
                    # Vérifier que le fichier n'est pas vide/tronqué : sous le
                    # seuil = PBF vide ; taille annoncée non atteinte = coupure
                    # TCP silencieuse (même garde que _download_to_tmp).
                    if (taille_dl < _SEUIL_PBF
                            or (total_size and taille_dl != total_size)):
                        print(f"  ERROR: incomplete PBF ({taille_dl} bytes"
                              + (f" / {total_size} expected" if total_size else "")
                              + ") : download failed (network? Geofabrik access?).")
                        pbf_part.unlink(missing_ok=True)
                        pbf = None
                    else:
                        pbf_part.replace(pbf)
                except KeyboardInterrupt:
                    # R2#42 : nettoyer le .part partiel puis laisser l'interruption
                    # remonter (arrêt propre du run, comme la branche OSError). Sans
                    # ce cleanup, le .part serait laissé et un retry le verrait comme
                    # une reprise valide (il est < seuil ou != content-length → il est
                    # de toute façon jeté par la garde de complétude, mais autant ne
                    # pas laisser de résidu).
                    pbf_part.unlink(missing_ok=True)
                    raise
                except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e_dl:
                    print(f"\n  ERROR downloading PBF ({type(e_dl).__name__}) : {e_dl}")
                    pbf_part.unlink(missing_ok=True)
                    pbf = None

        if pbf and pbf.exists():
            _region_mode = bool(getattr(args, "zone_region", None))
            if _region_mode:
                # Region : on traite TOUT le PBF régional. bbox "monde" → le .map
                # ignore la bbox (skip_bbox) et l'export geojson ne découpe rien.
                bbox_wgs = (-180.0, -90.0, 180.0, 90.0)
            else:
                # Bbox WGS84 depuis la bbox dans le CRS NATIF du provider (bords
                # densifiés : à 2 coins le clip osmosis rognait des features en
                # bordure). R2#29 : passer par _natif_vers_wgs84 (pyproj, tout
                # CRS) et non la formule Lambert 93 en dur — sinon un provider
                # hors métropole (EPSG:2056, UTM ultramarins…) recevait ses
                # coords via les formules France → emprise OSM fausse, découpage
                # décalé. Miroir du chemin LiDAR (_get_transformer plus haut).
                try:
                    bbox_wgs = _bbox_enveloppe_transform(
                        _natif_vers_wgs84, bbox[0], bbox[1], bbox[2], bbox[3])
                except (ValueError, TypeError, ImportError, RuntimeError) as e:
                    print(f"  ERROR bbox WGS84 conversion ({type(e).__name__}): {e}")
                    bbox_wgs = None
            if bbox_wgs:
                # Dossier dédié OSM — pas le dossier LiDAR
                dossier_osm = (Path(args.dossier).resolve() if args.dossier
                               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "osm_vecteur")
                dossier_osm.mkdir(parents=True, exist_ok=True)
                # Liste des formats GeoJSON demandés (parmi "gz" et "geojson")
                # Mode région : traiter tout le PBF régional sans re-clip
                # (le PBF EST déjà la région — c'est le gain vs boucle départements).
                _resultat_osm = _produire_sorties_osm(
                    bbox_wgs, dossier_osm, nom_zone, pbf,
                    formats=args.formats_fichier,
                    osm_tags=(args.couche
                              if getattr(args, 'couche', None)
                              else getattr(args, 'osm_tags', None)),
                    ecraser=args.tuiles_ecraser,
                    skip_bbox=_region_mode,
                    zoom_min=getattr(args, "zoom_min", 8),
                    zoom_max=getattr(args, "zoom_max", 18),
                )
                _osm_livrables_ok = _resultat_osm.complet
        _livrables_raster_ok = _osm_livrables_ok and _livrables_raster_ok

    if etape_cur[0] > 0:
        elap  = int(time.time() - etape_t0[0])
        cumul = int(time.time() - t_debut)
        print(f"  ✓ Step {etape_cur[0]} finished in {_hms(elap)}  (cumulative {_hms(cumul)})")
    total = int(time.time() - t_debut)
    m, s  = divmod(total, 60)
    # Planche d'assemblage : balaie les livrables du dossier (best-effort).
    _dpl = dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville
    # bbox_wgs n'existe (branche OSM) que si un PBF a été téléchargé et traité ;
    # locals().get() évite un UnboundLocalError sur un run LiDAR pur, où la
    # planche continue de fonctionner en best-effort (comportement historique).
    _planche_depuis_dossier(_dpl, args, nom_zone,
                            zone_bbox_wgs84=locals().get("bbox_wgs"))
    print(f"\n  Done! Folder: {dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville}")
    print(f"  Total time: {m}m{s:02d}s")
    dossier_res = str(dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville)
    _historique_depuis_argv(
        total, dossier_res,
        statut=("ok" if _livrables_raster_ok else "ko"))
    if not _livrables_raster_ok:
        raise RuntimeError(
            "requested deliverable generation/conversion incomplete - "
            "partial outputs kept; "
            "rerun to retry failed deliverables")


# ============================================================
# DÉCOUPAGE À PRIORI — FONCTIONS UTILITAIRES
# ============================================================


def _calculer_sous_zones_priori(x1, y1, x2, y2, n_morceaux, cote_km, unite_m=True,
                                n_cols=0, n_rows=0):
    """Façade historique vers le planificateur de grille extrait."""
    return _calculer_sous_zones_priori_impl(
        x1,
        y1,
        x2,
        y2,
        n_morceaux,
        cote_km,
        unite_m=unite_m,
        n_cols=n_cols,
        n_rows=n_rows,
    )

def _lister_dalles_zone(noms_attendus, dossier_dalles, dossier_ville, bbox):
    """Retourne la liste des Path des dalles valides présentes sur disque
    pour cette zone. Source de vérité : dalles_zone.txt si bbox match,
    sinon le set `noms_attendus` (issu de PROVIDER.discover_dalles).

    noms_attendus : iterable de noms de dalles attendus pour la zone
                    (typiquement les keys du dict retourné par discover_dalles).
    """
    # Déterminer les noms de la zone : dalles_zone.txt si l'en-tête correspond
    # (bbox + provider), sinon le set noms_attendus (discover_dalles).
    noms_zone = set()
    dalles_zone_txt = dossier_ville / "dalles_zone.txt"
    if dalles_zone_txt.exists():
        _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
        if _dalles_zone_hdr_ok(_lignes, bbox):
            noms_zone = {n.strip() for n in _lignes if n.strip() and not n.startswith("#")}
    if not noms_zone:
        noms_zone = set(noms_attendus)

    # Résoudre CHAQUE nom directement (chemin_dalle gère le sous-dossier par
    # colonne X) au lieu de rglober TOUT le cache PARTAGÉ. Sur un cache
    # départemental (dizaines de milliers de .tif) × des centaines de chunks,
    # l'ancien scan était en O(chunks × fichiers) ; désormais O(noms de la zone).
    dalles_ombrages = []
    for nom in noms_zone:
        # chemin_dalle lève ValueError sur un nom piégé (dalles_zone.txt altéré) :
        # on saute au lieu de crasher (R2#3, défense en profondeur).
        try:
            p = chemin_dalle(dossier_dalles, nom)
            if p.exists() and p.stat().st_size > SEUIL_DALLE_VALIDE:
                dalles_ombrages.append(p)
        except (OSError, ValueError):
            continue
    return sorted(dalles_ombrages)


def _dalles_zone_entete(bbox):
    """En-tête (2 lignes) de dalles_zone.txt : bbox + provider. La ligne
    provider évite qu'un run MNT et un run LAZ pointés sur le MÊME dossier de
    sortie (--output-dir forcé) se volent la liste de dalles — par défaut, le
    tag de variante dans le nom de zone sépare déjà les projets."""
    return (f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}\n"
            f"# provider:{PROVIDER.CODE}")


def _ecrire_dalles_zone(path, bbox, noms):
    """Publie atomiquement la liste complète des dalles d'une zone."""
    contenu = (
        _dalles_zone_entete(bbox)
        + "\n"
        + "\n".join(sorted(set(noms)))
    )
    _ecrire_texte_atomique(path, contenu)
    _creer_fichier(Path(path))


def _dalles_zone_hdr_ok(lignes, bbox):
    """Valide l'en-tête de dalles_zone.txt : bbox (ligne 0) et, si présente,
    la ligne provider (les anciens fichiers sans elle restent acceptés)."""
    if not lignes or lignes[0].strip() != \
            f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}":
        return False
    for _l in lignes[1:3]:
        if _l.startswith("# provider:"):
            return _l.strip() == f"# provider:{PROVIDER.CODE}"
    return True


def _dl_workers_effectif(workers, dl_cap, lp):
    """Workers de download effectifs (R1#6). dl_cap = plafond provider (None ou
    0 = aucun). --laz-parallel (lp) peut monter les workers pour paralléliser les
    conversions (post_fetch CSF/DFM), mais JAMAIS au-delà du plafond quand il
    existe : au-delà, IGN/swisstopo throttlent et tronquent le transfert (run
    avorté). Sans plafond, lp monte librement. La conversion tourne DANS la tâche
    de download (pool partagé) : sur un provider plafonné elle reste donc bornée
    au plafond tant que les pools ne sont pas découplés (travail futur)."""
    if isinstance(dl_cap, int) and dl_cap > 0:
        return min(dl_cap, max(min(workers, dl_cap), lp))
    return max(workers, lp)


def _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args,
                              quiet=False):
    """Télécharge en parallèle les dalles d'un dict {nom: url} (issu de
    PROVIDER.discover_dalles). Pure orchestration : la découverte et le
    fallback grille sont entièrement délégués au provider.

    dalles_dict : {nom_dalle: url_telechargement_complet}
    bbox        : (x_min, y_min, x_max, y_max) en CRS natif (informatif, pour
                  le header de dalles_zone.txt)
    quiet       : coupe la barre \\r répétée (appelé depuis le thread de fond
                  _PrefetchDalles pendant que le thread principal imprime son
                  propre déroulé (ombrage) — sans coordination entre les deux
                  flux, la barre \\r du préchargement se faisait écraser en
                  plein milieu par une ligne complète du thread principal,
                  produisant une ligne de log fusionnée illisible).
    """
    ok = skip = absent = erreur = 0
    a_telecharger = []

    # Sécurité : `dalles_dict` vient de PROVIDER.discover_dalles (index DISTANT).
    # On écarte tout nom qui n'est pas un basename sûr AVANT de construire un
    # chemin local, sinon une entrée piégée (`../…`) écrirait hors cache (R2#3).
    _dict_sur = {n: u for n, u in dalles_dict.items() if _nom_dalle_sur(n)}
    if len(_dict_sur) < len(dalles_dict):
        _n_drop = len(dalles_dict) - len(_dict_sur)
        print(f"  WARNING: {_n_drop} tile(s) with unsafe name(s) skipped "
              f"(path traversal guard)")
    dalles_dict = _dict_sur

    # Overwrite = VRAI re-download de la source (choix Nico : --download-overwrite
    # doit re-tirer, LAZ inclus). Les deux flags convergent (--download-force et
    # --download-overwrite forcent le re-download) : on re-liste la dalle même si
    # elle est en cache. La suppression du .tif ET le bypass du hook pre_download
    # (qui reconstruit depuis le LAZ caché) sont gérés en aval par
    # telecharger_dalle_directe(ecraser=True) ; sinon un overwrite ne re-tirait
    # jamais le nuage (vécu : Cache 6 / Downloaded 3 sous --download-overwrite).
    _force_dl = bool(args.telechargement_forcer or args.telechargement_ecraser)
    for nom, url in dalles_dict.items():
        cd = chemin_dalle(dossier_dalles, nom)
        if _force_dl or not cd.exists() or cd.stat().st_size < SEUIL_DALLE_VALIDE:
            a_telecharger.append((nom, url))
        else:
            skip += 1

    nb_total = len(a_telecharger)
    largeur  = 30
    done = 0
    t0_dl = time.time()

    def _afficher_barre(done, nb_total, t0_dl):
        if quiet:
            return
        pct  = int(done * 100 / max(nb_total, 1))
        bars = int(done * largeur / max(nb_total, 1))
        elap = int(time.time() - t0_dl)
        barre = "█" * bars + "░" * (largeur - bars)
        print(f"\r  LiDAR tiles [{barre}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
              end="", flush=True)

    # Providers servant de grandes mosaïques COG (ca-nrcan…) : lecture fenêtrée
    # /vsicurl/ sur la bbox zone au lieu de rapatrier le COG entier.
    _cog_windowed = getattr(PROVIDER, "COG_WINDOWED", False)
    # Plafond de download PROPRE AU PROVIDER : les nuages LAZ (fr/ch mode LAZ)
    # pèsent ~200 Mo ; à --workers 8, IGN/swisstopo throttlent et coupent la
    # connexion en silence (transfert tronqué, retry qui repart de zéro → tuile
    # en erreur → run avorté). DOWNLOAD_WORKERS_MAX borne la SEULE phase de
    # download ; le tuilage/ombrage garde args.workers. Défaut providers = pas
    # de plafond (attr absent → args.workers).
    # R1#6 — --laz-parallel ne doit jamais ouvrir plus de connexions que le
    # plafond du provider (avant, max(cap, laz_parallel) laissait --laz-parallel 6
    # ouvrir 6 connexions sur un plafond de 3 → transfert tronqué → run avorté).
    _dl_cap = getattr(PROVIDER, "DOWNLOAD_WORKERS_MAX", None)
    _lp     = getattr(args, "laz_parallel", 1)
    _dl_workers = _dl_workers_effectif(args.workers, _dl_cap, _lp)
    if a_telecharger:
        if _dl_workers < args.workers:
            print(f"  Note: capping downloads to {_dl_workers} parallel "
                  f"(large point-cloud tiles, avoids server throttling)")
        if _lp > _dl_workers:
            print(f"  Note: --laz-parallel {_lp} limited to {_dl_workers} here "
                  f"(provider download cap; conversion shares the download pool)")
        with ThreadPoolExecutor(max_workers=_dl_workers) as ex:
            if _cog_windowed:
                futures = {ex.submit(telecharger_cog_fenetre, nom, url, dossier_dalles,
                                     bbox, _force_dl): (nom,)
                           for nom, url in a_telecharger}
            elif getattr(PROVIDER, "COPC_WINDOWED", False):
                # Nuages COPC (ca-nrcan…) : fenêtrage /vsicurl sur la bbox au lieu
                # de rapatrier le COPC entier, puis conversion DFM/CSF.
                futures = {ex.submit(telecharger_copc_fenetre, nom, url, dossier_dalles,
                                     bbox, _force_dl): (nom,)
                           for nom, url in a_telecharger}
            else:
                futures = {ex.submit(telecharger_dalle_directe, nom, url, dossier_dalles,
                                     _force_dl,
                                     args.telechargement_compresser): (nom,)
                           for nom, url in a_telecharger}
            for fut in as_completed(futures):
                nom = futures[fut][0]
                res = fut.result()
                done += 1
                if res == "ok":   ok += 1
                elif res == "skip": skip += 1
                elif res == "absent": absent += 1
                else: erreur += 1
                _afficher_barre(done, nb_total, t0_dl)

    if nb_total > 0:
        if not quiet:
            print()  # fin barre
            print(f"  Downloaded: {ok}  Cache: {skip}  Missing: {absent}  Errors: {erreur}")
        _laz_prof_resume(time.time() - t0_dl, _dl_workers, _lp)   # R1#6 profiling

    # Invariant (miroir WMTS, revue 2026-07-10) : ne JAMAIS continuer sur une
    # couverture trouée. Sans ce garde, les ombrages/exports étaient générés
    # depuis les seules dalles disponibles, le chunk était marqué fait, et
    # dalles_zone.txt (source de vérité des runs tiles-only, cf. ~l.9443)
    # listait un sous-ensemble — les trous devenaient permanents. Les dalles
    # réussies sont en cache : le re-run ne retélécharge que les échecs.
    if erreur > 0:
        raise RuntimeError(f"{erreur} tile download error(s) - pipeline "
                           f"stopped before shading/tiling (rerun to retry "
                           f"the failed tiles; successful ones are cached)")

    # Persister dalles_zone.txt — utile pour --dalles-purger-hors-zone et la
    # reprise (cf. _lister_dalles_zone qui lit ce fichier).
    noms_persistance = [nom for nom in dalles_dict.keys()
                        if chemin_dalle(dossier_dalles, nom).exists()
                        and chemin_dalle(dossier_dalles, nom).stat().st_size > SEUIL_DALLE_VALIDE]
    if noms_persistance:
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        _ecrire_dalles_zone(
            dalles_zone_txt, bbox, noms_persistance
        )

    # Enregistrer toutes les dalles utilisées par ce chunk dans le manifest
    # pour permettre --nettoyage de les supprimer en fin de chunk. Le
    # téléchargement parallèle ne propage pas _manifest_ctx (threading.local)
    # → registration explicite depuis le main thread, en LOT : l'unitaire
    # réécrivait tout le JSON + fsync PAR dalle (O(n²) sur un chunk de
    # milliers de dalles, dizaines de secondes perdues par chunk).
    _cds = [chemin_dalle(dossier_dalles, _nom) for _nom in noms_persistance]
    _reg = [c for c in _cds if c.exists()]
    # Mode LAZ : le nuage .laz gardé en cache par post_fetch est l'intermédiaire
    # le plus LOURD (~200 Mo/dalle) et ne vit PAS avec le .tif produit (production)
    # → sans déclaration explicite --nettoyage ne le voit jamais et un balayage
    # départemental sature le disque (le .tif, léger, était seul purgé). On l'ajoute
    # au manifeste ; --cleanup-keep-tiles l'épargne (cf. cleanup du chunk, qui garde
    # aussi le dossier cache des nuages). No-op pour un provider sans mode LAZ.
    _cloud_path = getattr(PROVIDER, "cloud_path", None)
    if _cloud_path is not None:
        for c in _cds:
            _lz = _cloud_path(c)
            if _lz is not None and _lz.exists():
                _reg.append(_lz)
    _creer_fichiers(_reg)


from _split_deliverables import (
    _ResultatChunk,
    _chunk_livrable_complet as _chunk_livrable_complet_impl,
    _mbtiles_est_complete as _mbtiles_est_complete_impl,
    _normaliser_resultat_chunk,
)


def _mbtiles_est_complete(mbt_path):
    """Façade historique vers le validateur MBTiles extrait."""
    return _mbtiles_est_complete_impl(mbt_path)


def _chunk_livrable_complet(dossier_chunk, args, mbtiles_attendus=None):
    """Façade historique conservant l'injection du validateur par monkeypatch."""
    return _chunk_livrable_complet_impl(
        dossier_chunk,
        args,
        mbtiles_attendus,
        verifier_mbtiles=_mbtiles_est_complete,
    )


def _morceau_termine_reutilisable(manifeste, cle, dossier_chunk, args):
    """Valide la preuve persistée avant de croire ``termine=True``.

    Les anciens manifests sans ``mbtiles_attendus`` sont rejoués une fois : un
    scan permissif du dossier pourrait prendre un ancien produit pour la sortie
    courante. Une liste vide est au contraire une preuve explicite de zone hors
    couverture et reste réutilisable sans fichier.
    """
    if not manifeste.deja_traite(cle):
        return False
    attendus = manifeste.mbtiles_attendus_morceau(cle)
    if attendus == ():
        return True
    if (attendus is not None
            and _chunk_livrable_complet(dossier_chunk, args, attendus)):
        return True
    raison = ("legacy manifest without output proof" if attendus is None
              else "expected deliverable missing or invalid")
    print(f"  [{cle}] {raison} - replaying chunk")
    manifeste.invalider_morceau(cle)
    return False


def _mbtiles_a_regenerer(mbt_path, ecraser, source=None):
    """Détermine si un mbtiles doit être (re)généré.

    Retourne True si :
    - le fichier n'existe pas,
    - --tuiles-ecraser est passé,
    - `source` (TIF d'ombrage) est PLUS RÉCENT que le mbtiles : un
      --shadings-overwrite sans --tiles-overwrite recalcule l'ombrage, les
      tuiles doivent suivre (sinon l'utilisateur regarde l'ancien rendu),
    - le fichier existe mais contient 0 tuiles (artefact d'un run interrompu),
    - le fichier existe mais est corrompu (SQLite unreadable).

    Sinon retourne False (mbtiles valide, on le réutilise). Logue la raison
    de la regenerating pour éviter les disparitions silencieuses.
    """
    if not mbt_path.exists() or ecraser:
        return True
    if source is not None:
        try:
            if Path(source).stat().st_mtime > mbt_path.stat().st_mtime:
                print(f"  {mbt_path.name} → older than {Path(source).name}, regenerating",
                      flush=True)
                return True
        except OSError:
            pass
    # Distinguer fichier illisible vs vide pour un log clair
    try:
        _c = sqlite3.connect(f"file:{mbt_path}?mode=ro", uri=True)
        try:
            _n = _c.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        finally:
            _c.close()
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as _e:
        print(f"  {mbt_path.name} → SQLite unreadable ({type(_e).__name__}), regenerating", flush=True)
        return True
    if _n == 0:
        print(f"  {mbt_path.name} → exists but empty (0 tiles), regenerating", flush=True)
        return True
    return False


def _bbox_geojson_stream(fh):
    """bbox WGS84 d'un GeoJSON lu en STREAMING (ijson) : un département de
    vecteurs fait des centaines de Mo décompressés — le charger entier en RAM
    juste pour une bbox serait absurde. RAM O(1) : on ne garde que les min/max."""
    import ijson
    from decimal import Decimal   # ijson rend les nombres en Decimal
    lon0 = lat0 = float("inf"); lon1 = lat1 = float("-inf")
    def _walk(c):
        nonlocal lon0, lat0, lon1, lat1
        if isinstance(c, (list, tuple)):
            if (len(c) >= 2 and isinstance(c[0], (int, float, Decimal))
                    and isinstance(c[1], (int, float, Decimal))):
                x = float(c[0]); y = float(c[1])
                if x < lon0: lon0 = x
                if x > lon1: lon1 = x
                if y < lat0: lat0 = y
                if y > lat1: lat1 = y
            else:
                for e in c:
                    _walk(e)
    for coords in ijson.items(fh, "features.item.geometry.coordinates"):
        _walk(coords)
    return (lon0, lat0, lon1, lat1) if lon1 > lon0 else None


def _bbox_sqlite_tiles(path, rmaps=False):
    """bbox WGS84 d'un magasin de tuiles SQLite, best-effort. mbtiles : metadata
    `bounds`, sinon étendue des tuiles. sqlitedb RMaps : selon info.tilenumbering
    ('simple' = z réel + y XYZ, notre writer ; défaut BigPlanet = z stocké 17-zoom).
    IMPORTANT : l'agrégat min/max est fait À UN SEUL NIVEAU de zoom — mélanger
    les colonnes/lignes de zooms différents donnerait une bbox fausse.
    None si illisible/incohérent."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        if not rmaps:
            try:
                row = cur.execute(
                    "SELECT value FROM metadata WHERE name='bounds'").fetchone()
                if row and row[0]:
                    l, b, r, t = (float(x) for x in str(row[0]).split(","))
                    return (l, b, r, t)
            except Exception:
                pass
            zrow = cur.execute("SELECT max(zoom_level) FROM tiles").fetchone()
            if not zrow or zrow[0] is None:
                return None
            z = int(zrow[0])
            xmin, xmax, ytmin, ytmax = cur.execute(
                "SELECT min(tile_column),max(tile_column),"
                "min(tile_row),max(tile_row) FROM tiles WHERE zoom_level=?",
                (z,)).fetchone()
            ymin = (1 << z) - 1 - ytmax     # TMS -> XYZ
            ymax = (1 << z) - 1 - ytmin
        else:
            numbering = "simple"            # notre writer (tilenumbering='simple')
            try:
                row = cur.execute("SELECT tilenumbering FROM info").fetchone()
                if row and row[0]:
                    numbering = str(row[0]).lower()
            except Exception:
                numbering = ""              # pas de colonne = vieux schéma BigPlanet
            if numbering == "simple":
                zrow = cur.execute("SELECT max(z) FROM tiles").fetchone()
                if not zrow or zrow[0] is None:
                    return None
                zst = int(zrow[0]); z = zst
            else:
                zrow = cur.execute("SELECT min(z) FROM tiles").fetchone()
                if not zrow or zrow[0] is None:
                    return None
                zst = int(zrow[0]); z = 17 - zst
            if not (0 <= z <= 25):
                return None
            xmin, xmax, ymin, ymax = cur.execute(
                "SELECT min(x),max(x),min(y),max(y) FROM tiles WHERE z=?",
                (zst,)).fetchone()
        tl = _tile_to_geo(xmin, ymin, z)    # coin NO : (lon_min, lat_min, lon_max, lat_max)
        br = _tile_to_geo(xmax, ymax, z)    # coin SE
        bbox = (tl[0], br[1], br[2], tl[3])
        if -180 <= bbox[0] <= 180 and -85 <= bbox[1] <= 85 and bbox[2] > bbox[0]:
            return bbox
        return None
    except Exception:
        return None
    finally:
        try: con.close()
        except Exception: pass


def _extraire_bbox_wgs84(fichier):
    """Emprise WGS84 (lon0,lat0,lon1,lat1) d'un livrable, ou None. Best-effort."""
    f = Path(fichier)
    nom = f.name.lower()
    try:
        if nom.endswith(".mbtiles"):
            return _bbox_sqlite_tiles(f, rmaps=False)
        if nom.endswith(".sqlitedb"):
            return _bbox_sqlite_tiles(f, rmaps=True)
        if nom.endswith(".geojson"):
            with open(f, "rb") as fh:
                return _bbox_geojson_stream(fh)
        if nom.endswith(".geojson.gz"):
            with gzip.open(f, "rb") as fh:
                return _bbox_geojson_stream(fh)
    except Exception:
        return None
    return None


def _planche_depuis_dossier(dossier, args, nom_zone=None, zone_bbox_wgs84=None):
    """Balaie un dossier projet et génère UNE planche d'assemblage PAR PRODUIT
    (ombrage / couche : lrm, svf, ortho…) : sinon leurs emprises se
    superposeraient sur une même planche, illisible. Groupe par (produit, cellule
    NNNxNNN) ; le produit = le nom de fichier sans le token de cellule ni
    l'extension → le mbtiles et le sqlitedb d'un même produit restent groupés.
    Indépendant du run (mode --planche DIR). Une cellule sans fichier (mer)
    n'apparaît pas : c'est voulu.

    zone_bbox_wgs84 : bbox WGS84 effectivement demandée par l'utilisateur
    (lon_min, lat_min, lon_max, lat_max), si connue de l'appelant. Sert à
    borner l'emprise lue dans les fichiers : le WFS IGN renvoie la géométrie
    ENTIÈRE d'un itinéraire qui traverse seulement la zone (ex. un GR ou une
    véloroute de plusieurs centaines de km pour une zone de quelques km), pas
    la portion locale. Sans ce recadrage, l'emprise calculée peut dériver très
    loin de la zone réelle, faire échouer le reverse-geocoding du département
    et rendre la planche illisible (le point demandé devient invisible à
    l'échelle de l'emprise entière). Absent en mode --planche DIR autonome
    (pas de requête associée) : l'ancien comportement best-effort s'applique."""
    if not getattr(args, "index_map", True):
        return
    try:
        import re as _re

        def _clip(bbox):
            """Intersecte `bbox` avec la zone demandée, si connue. Conserve
            `bbox` tel quel en l'absence d'intersection (défensif : ne doit
            jamais produire une bbox vide ou inversée)."""
            if zone_bbox_wgs84 is None:
                return bbox
            x0 = max(bbox[0], zone_bbox_wgs84[0]); y0 = max(bbox[1], zone_bbox_wgs84[1])
            x1 = min(bbox[2], zone_bbox_wgs84[2]); y1 = min(bbox[3], zone_bbox_wgs84[3])
            return (x0, y0, x1, y1) if (x0 < x1 and y0 < y1) else bbox

        d = Path(dossier)
        if not d.is_dir():
            print(f"  (index sheet: {d} is not a folder)", flush=True)
            return
        nom_zone = nom_zone or d.name
        _SUFS = (".geojson.gz", ".mbtiles", ".sqlitedb", ".rmap", ".map", ".geojson")
        # mbtiles/geojson d'abord (emprise fiable), sqlitedb en dernier recours.
        _prio = {".mbtiles": 0, ".geojson": 1, ".gz": 2, ".sqlitedb": 3}
        fichiers = sorted(
            [p for pat in ("*.mbtiles", "*.sqlitedb", "*.geojson", "*.geojson.gz")
             for p in d.rglob(pat)],
            key=lambda p: _prio.get(p.suffix.lower(), 9))
        produits = {}   # produit -> {cle: bbox}  ('__single__' hors découpage)
        geo_bboxes = []; geo_stems = []
        for f in fichiers:
            stem = f.name
            for suf in _SUFS:
                if stem.lower().endswith(suf):
                    stem = stem[:-len(suf)]; break
            # Famille GeoJSON (vecteur IGN/OSM/fusion) : les couches d'un même
            # run décrivent la MÊME zone → UNE planche pour l'ensemble (demande
            # de Nico), pas une par couche. Collectées à part, groupées après.
            if f.name.lower().endswith((".geojson", ".geojson.gz")):
                bbox = _extraire_bbox_wgs84(f)
                if bbox:
                    geo_bboxes.append(_clip(bbox)); geo_stems.append(stem)
                continue
            m = _re.search(r"(\d{3})x(\d{3})", stem)
            cle = f"{m.group(1)}x{m.group(2)}" if m else "__single__"
            produit = _re.sub(r"_?\d{3}x\d{3}", "", stem).strip("_") or nom_zone
            cells = produits.setdefault(produit, {})
            if cle in cells:
                continue
            bbox = _extraire_bbox_wgs84(f)
            if bbox:
                cells[cle] = _clip(bbox)
        if geo_bboxes:
            # Emprise du groupe = INTERSECTION des couches, pas l'union : les
            # couches d'itinéraires (GR) portent des features ENTIÈRES
            # traversant la région — l'union donnerait une emprise de centaines
            # de km (et un centre potentiellement en mer, vécu). L'intersection
            # approxime la zone réellement demandée. Union en repli si vide.
            ib = (max(b[0] for b in geo_bboxes), max(b[1] for b in geo_bboxes),
                  min(b[2] for b in geo_bboxes), min(b[3] for b in geo_bboxes))
            if not (ib[0] < ib[2] and ib[1] < ib[3]):
                ib = (min(b[0] for b in geo_bboxes), min(b[1] for b in geo_bboxes),
                      max(b[2] for b in geo_bboxes), max(b[3] for b in geo_bboxes))
            import os.path as _osp
            nom_geo = _osp.commonprefix(geo_stems).strip("_") or nom_zone
            produits[nom_geo] = {"__single__": ib}
        produits = {k: v for k, v in produits.items() if v}
        if not produits:
            print("  (index sheet: no readable deliverable found)", flush=True)
            return
        # Contour(s) département : une seule requête Nominatim pour tous les
        # produits (même zone), sur l'emprise globale.
        # Contour département : viser le centre du produit le PLUS LOCAL (plus
        # petite bbox), pas l'union. Les couches d'itinéraires (GR) contiennent
        # des features ENTIÈRES traversant la région : l'union est énorme et
        # son centre peut tomber en mer (vécu : centre en Méditerranée → reverse
        # sans département → aucune planche avec contour). Repli sur l'union si
        # le produit local ne résout rien.
        def _pbbox(cells_d):
            v = list(cells_d.values())
            return (min(b[0] for b in v), min(b[1] for b in v),
                    max(b[2] for b in v), max(b[3] for b in v))
        pb_all = {k: _pbbox(v) for k, v in produits.items()}
        ref_bbox = min(pb_all.values(),
                       key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        allb = [b for v in produits.values() for b in v.values()]
        gbbox = (min(b[0] for b in allb), min(b[1] for b in allb),
                 max(b[2] for b in allb), max(b[3] for b in allb))
        contours = _planche_contours_dept(ref_bbox, args)
        if not contours and gbbox != ref_bbox:
            time.sleep(1.1)   # Nominatim : 1 req/s
            contours = _planche_contours_dept(gbbox, args)
        for produit, cells_d in sorted(produits.items()):
            cells = sorted((k, v) for k, v in cells_d.items() if k != "__single__")
            _generer_planche(pb_all[produit], cells or None, produit, d, args,
                             contours=contours)
    except Exception as e:
        print(f"  (index sheet skipped: {type(e).__name__}: {e})", flush=True)


def _planche_contours_dept(bbox_wgs84, args):
    """Contour(s) RÉEL(s) du/des département(s) couvrant la zone (polygone, pas
    la bbox), best-effort via Nominatim polygon_geojson. Retourne une liste
    d'anneaux extérieurs [(lon,lat), ...] en WGS84, ou [] si rien de résolvable
    (offline, hors FR, etc.) — la planche est alors dessinée sans fond dép."""
    lon0, lat0, lon1, lat1 = bbox_wgs84
    noms = []
    dep_arg = str(getattr(args, "zone_departement", "") or "").strip()
    if dep_arg:
        # Numéros simples séparés par des virgules : nom lu dans le cache rempli
        # par geocoder_departement pendant le run (pas de nouvel Overpass).
        try:
            _cache = json.loads((DOSSIER_CACHE / "dep_bbox_cache.json")
                                .read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
        for tok in dep_arg.replace(";", ",").split(","):
            n = (_cache.get(tok.strip()) or {}).get("nom")
            if n and n not in noms:
                noms.append(n)
    if not noms:
        # Reverse-geocode du centre → département (address.county en FR).
        lonc = (lon0 + lon1) / 2; latc = (lat0 + lat1) / 2
        try:
            url = ("https://nominatim.openstreetmap.org/reverse?"
                   + urllib.parse.urlencode({"lat": f"{latc:.5f}", "lon": f"{lonc:.5f}",
                                             "format": "jsonv2", "zoom": 8}))
            req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                addr = (json.load(r) or {}).get("address", {}) or {}
            n = addr.get("county") or addr.get("state_district") or addr.get("state")
            if n:
                noms.append(n)
            else:
                # Pas d'exception mais rien de résolu (centre en mer, hors
                # couverture admin...) : le dire, sinon indiagnosticable.
                print(f"  (index sheet: no department at "
                      f"{latc:.4f},{lonc:.4f} - outline skipped)", flush=True)
        except Exception as _e_rev:
            # Visible : un best-effort qui échoue en silence est indiagnosticable
            # (leçon du 2026-07-10 : la planche sortait sans département sans
            # aucun indice sur la cause).
            print(f"  (index sheet: reverse geocoding failed: "
                  f"{type(_e_rev).__name__}: {_e_rev})", flush=True)
    # Cache disque des polygones (même logique que dep_bbox_cache.json) : les
    # contours administratifs ne changent pas, les re-télécharger à chaque run
    # coûtait des requêtes Nominatim + les sleep de politesse par planche.
    _cache_path = DOSSIER_CACHE / "dep_contour_cache.json"
    try:
        _cache = json.loads(_cache_path.read_text(encoding="utf-8"))
        if not isinstance(_cache, dict):
            _cache = {}
    except Exception:
        _cache = {}
    contours = []
    _cache_dirty = False
    for nom in noms[:4]:   # borne : ne pas spammer Nominatim
        if nom in _cache:
            contours.extend(_cache[nom])
            continue
        try:
            url = ("https://nominatim.openstreetmap.org/search?"
                   + urllib.parse.urlencode({"q": nom, "format": "jsonv2",
                                             "polygon_geojson": 1,
                                             "polygon_threshold": 0.005, "limit": 1}))
            req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.load(r)
            g = (res[0].get("geojson") if res else None) or {}
            rings = []
            if g.get("type") == "Polygon":
                rings.append(g["coordinates"][0])
            elif g.get("type") == "MultiPolygon":
                for poly in g["coordinates"]:
                    rings.append(poly[0])
            contours.extend(rings)
            if rings:   # ne pas cacher un résultat vide (permet de réessayer)
                _cache[nom] = rings
                _cache_dirty = True
            time.sleep(1.1)   # Nominatim : 1 req/s
        except Exception as _e_sea:
            print(f"  (index sheet: no outline for '{nom}': "
                  f"{type(_e_sea).__name__}: {_e_sea})", flush=True)
    if _cache_dirty:
        try:
            _ecrire_json_atomique(_cache_path, _cache)
        except Exception:
            pass   # cache best-effort, jamais un point de panne
    return contours


def _generer_planche(bbox_wgs84, cells, nom_zone, dossier, args, contours=None):
    """<zone>_planche.png : planche d'assemblage (index/key map) d'UN produit.
    Emprise (cadre) + contour(s) département réels + cellules numérotées (si
    découpage). `contours` pré-calculé (partagé entre produits) sinon récupéré
    ici. PIL seul (bundle app). Entièrement best-effort : toute erreur est
    avalée (l'artefact est un bonus, jamais un point de panne du run)."""
    if not getattr(args, "index_map", True):
        return
    try:
        import math as _m
        from PIL import Image, ImageDraw, ImageFont
        lon0, lat0, lon1, lat1 = bbox_wgs84
        if lon1 <= lon0 or lat1 <= lat0:
            return
        if contours is None:
            contours = _planche_contours_dept(bbox_wgs84, args)

        # Emprise d'affichage = union(zone, contours), mais CAPÉE pour la
        # lisibilité : si l'emprise est minuscule vs le département, les cellules
        # deviennent illisibles (numéros qui se chevauchent). On limite la vue à
        # _CAP× l'emprise, centrée dessus, sans jamais exclure l'emprise. À
        # l'échelle départementale (emprise ≈ département) le cap ne mord pas :
        # tout le contour reste visible. Ratio corrigé du cos(lat) plus bas.
        lons = [lon0, lon1]; lats = [lat0, lat1]
        for ring in contours:
            lons += [p[0] for p in ring]; lats += [p[1] for p in ring]
        ulon0, ulon1 = min(lons), max(lons)
        ulat0, ulat1 = min(lats), max(lats)
        _CAP = 4.0
        ecx = (lon0 + lon1) / 2; ecy = (lat0 + lat1) / 2
        _hw = max(lon1 - lon0, 1e-6) * _CAP / 2
        _hh = max(lat1 - lat0, 1e-6) * _CAP / 2
        dlon0 = min(lon0, max(ulon0, ecx - _hw))
        dlon1 = max(lon1, min(ulon1, ecx + _hw))
        dlat0 = min(lat0, max(ulat0, ecy - _hh))
        dlat1 = max(lat1, min(ulat1, ecy + _hh))
        mlon = (dlon1 - dlon0) * 0.04 or 0.01
        mlat = (dlat1 - dlat0) * 0.04 or 0.01
        dlon0 -= mlon; dlon1 += mlon; dlat0 -= mlat; dlat1 += mlat
        lat_mid = (dlat0 + dlat1) / 2
        w_g = (dlon1 - dlon0) * _m.cos(_m.radians(lat_mid))
        h_g = (dlat1 - dlat0)
        if w_g <= 0 or h_g <= 0:
            return
        MAXPX = 1000
        if w_g >= h_g:
            W = MAXPX; H = max(1, round(MAXPX * h_g / w_g))
        else:
            H = MAXPX; W = max(1, round(MAXPX * w_g / h_g))

        def _px(lon, lat):
            return ((lon - dlon0) / (dlon1 - dlon0) * W,
                    (dlat1 - lat) / (dlat1 - dlat0) * H)

        img = Image.new("RGB", (W, H), (247, 249, 252))
        dr = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default(size=15)
        except Exception:
            font = ImageFont.load_default()

        # Département : contour RÉEL (polygone), léger fond + trait gris.
        for ring in contours:
            pts = [_px(lon, lat) for lon, lat in ring]
            if len(pts) >= 3:
                dr.polygon(pts, fill=(228, 233, 240), outline=(140, 150, 165))

        # Emprise globale des livrables (cadre bleu).
        ex0, ey0 = _px(lon0, lat1); ex1, ey1 = _px(lon1, lat0)
        dr.rectangle([ex0, ey0, ex1, ey1], outline=(37, 99, 235), width=3)

        # Cellules du découpage : rectangle + numéro centré.
        for cle, (clo0, cla0, clo1, cla1) in (cells or []):
            cx0, cy0 = _px(clo0, cla1); cx1, cy1 = _px(clo1, cla0)
            dr.rectangle([cx0, cy0, cx1, cy1], outline=(200, 70, 50), width=1)
            try:
                dr.text(((cx0 + cx1) / 2, (cy0 + cy1) / 2), cle,
                        fill=(120, 30, 20), font=font, anchor="mm")
            except TypeError:   # anchor absent (Pillow < 8) : coin haut-gauche
                dr.text((cx0 + 3, cy0 + 3), cle, fill=(120, 30, 20), font=font)

        titre = nom_zone + (f"  -  {len(cells)} zones" if cells else "")
        dr.text((8, 6), titre, fill=(30, 41, 59), font=font)

        # Carton de localisation (locator inset, standard cartes IGN papier) :
        # quand la vue principale est zoomée (cap 4× sur petite zone), le
        # contour du département est hors-champ — le fond couvre tout et la
        # planche perd son contexte. On dessine alors en coin le département
        # ENTIER avec l'emprise en rouge. Sauté quand la vue montre déjà le
        # département (run départemental : le carton serait redondant).
        if contours:
            klon0 = min(p[0] for ring in contours for p in ring)
            klon1 = max(p[0] for ring in contours for p in ring)
            klat0 = min(p[1] for ring in contours for p in ring)
            klat1 = max(p[1] for ring in contours for p in ring)
            # Test de CONFINEMENT (pas un ratio d'aires : sur un petit
            # département, une vue capée 4× peut en couvrir 30 % et un seuil
            # d'aire sautait le carton à tort) : si le département ne tient
            # pas entier dans la vue, on ajoute le carton.
            _tol = 0.02 * max(klon1 - klon0, klat1 - klat0)
            _dept_visible = (klon0 >= dlon0 - _tol and klon1 <= dlon1 + _tol
                             and klat0 >= dlat0 - _tol and klat1 <= dlat1 + _tol)
            if not _dept_visible:
                kmid = _m.cos(_m.radians((klat0 + klat1) / 2))
                kw_g = (klon1 - klon0) * kmid
                kh_g = (klat1 - klat0)
                iw = int(W * 0.30)
                ih = max(24, int(iw * kh_g / max(kw_g, 1e-9)))
                if ih > int(H * 0.38):          # borne : carton ≤ ~1/3 de haut
                    ih = int(H * 0.38)
                    iw = max(24, int(ih * kw_g / max(kh_g, 1e-9)))
                pad = 6; marge = 8
                x0i = W - iw - 2 * pad - marge
                y0i = H - ih - 2 * pad - marge   # coin bas-droit
                dr.rectangle([x0i, y0i, x0i + iw + 2 * pad, y0i + ih + 2 * pad],
                             fill=(255, 255, 255), outline=(140, 150, 165))

                def _kpx(lon, lat):
                    return (x0i + pad + (lon - klon0) / (klon1 - klon0) * iw,
                            y0i + pad + (klat1 - lat) / (klat1 - klat0) * ih)

                for ring in contours:
                    pts = [_kpx(lon, lat) for lon, lat in ring]
                    if len(pts) >= 3:
                        dr.polygon(pts, fill=(228, 233, 240),
                                   outline=(140, 150, 165))
                # Emprise en rouge, épaissie à 3 px minimum pour rester
                # visible même quand la zone est minuscule vs le département.
                kx0, ky0 = _kpx(lon0, lat1); kx1, ky1 = _kpx(lon1, lat0)
                if kx1 - kx0 < 3: kx1 = kx0 + 3
                if ky1 - ky0 < 3: ky1 = ky0 + 3
                dr.rectangle([kx0, ky0, kx1, ky1], outline=(220, 38, 38), width=2)

        out = Path(dossier) / f"{nom_zone}_planche.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        print(f"  {out.name} : index sheet ({W}x{H})", flush=True)
    except Exception as _e_pl:
        print(f"  (index sheet skipped: {type(_e_pl).__name__}: {_e_pl})", flush=True)


def _signature_config(args, sous_zones):
    """Façade historique injectant le provider actif dans la signature."""
    return _signature_config_impl(args, sous_zones, provider=PROVIDER)


from _split_runner import (
    _DependancesRunnerClassique,
    _run_split_priori as _run_split_priori_impl,
)


def _run_split_priori(args, sous_zones, mode_desc, nom_zone, racine_pr,
                      overwrite_actif, entete_chunk, traiter_chunk, t_debut,
                      vide_sans_couverture_ok=True):
    """Façade compatible vers le runner classique extrait."""
    dependances = _DependancesRunnerClassique(
        fabrique_manifeste=Manifeste,
        signature_config=_signature_config,
        morceau_termine_reutilisable=_morceau_termine_reutilisable,
        garde_disque=_garde_disque,
        definir_chunk_log=_definir_chunk_log,
        normaliser_resultat_chunk=_normaliser_resultat_chunk,
        chunk_livrable_complet=_chunk_livrable_complet,
        dossier_dalles_actif=_dossier_dalles_actif,
        supprimer_fichiers=_supprimer_fichiers,
        formater_duree=_hms,
        zone_hors_couverture=ZoneHorsCouvertureWMTS,
        planche_depuis_dossier=_planche_depuis_dossier,
    )
    return _run_split_priori_impl(
        args,
        sous_zones,
        mode_desc,
        nom_zone,
        racine_pr,
        overwrite_actif,
        entete_chunk,
        traiter_chunk,
        t_debut,
        vide_sans_couverture_ok=vide_sans_couverture_ok,
        dependances=dependances,
    )


def _traiter_bbox_lidar(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle):
    """
    Traite un morceau LiDAR directement en Python (sans subprocess).
    Appelé par la boucle à priori dans main().
    nom_zone_base : nom du projet parent (ex: gareoult2).
    nom_z         : nom du morceau   (ex: gareoult2_001x001).
    """
    bx1, by1, bx2, by2 = bbox_natif

    # Sauvegarder / restaurer les args modifiés temporairement
    _bbox_orig = args.zone_bbox
    _nom_orig  = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom  = nom_z

    # Halo (cf. calcul par blocs / ghost cells) : ce morceau télécharge et
    # calcule ses ombrages sur une emprise élargie d'une marge GARANTIE,
    # au-delà de sa bbox nominale — pas seulement le débord accidentel de
    # l'arrondi aux dalles entières (mesuré 100-900 m selon l'endroit, jamais
    # garanti). generer_mbtiles_lidar CALCULE ensuite (pas une constante,
    # cf. son commentaire) l'ampleur exacte à publier en plus pour fermer le
    # petit trou qui reste au coin partagé par 4 blocs, bornée par cette
    # marge. Toujours de vrais pixels : la marge est dans les dalles
    # réellement téléchargées pour CE morceau, jamais une extrapolation.
    #
    # Proportionnelle à la taille du bloc (10 %, plancher 300 m), pas une
    # constante fixe : --block sert des providers du monde entier avec des
    # tailles de bloc au choix de l'utilisateur, et l'ampleur du trou de
    # coin (cisaillement de la reprojection) croît avec la taille du bloc.
    MARGE_HALO_M = max(300.0, 0.1 * min(bx2 - bx1, by2 - by1))

    traitement_ok = True
    mbtiles_attendus = []
    try:
        with _contexte_manifeste(manifeste, cle):
            bbox = (bx1, by1, bx2, by2)
            bbox_marge = (bx1 - MARGE_HALO_M, by1 - MARGE_HALO_M,
                          bx2 + MARGE_HALO_M, by2 + MARGE_HALO_M)
            # Structure : <racine>/<nom_zone_base>/ign_lidar/<nom_z>/
            # (tous les morceaux sont sous-dossiers du même projet parent)
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / LIDAR_SUBDIR)
            racine = racine_base
            dossier_ville = racine / nom_z
            dossier_dalles = _dossier_dalles_actif(args, dossier_ville)
            dossier_ville.mkdir(parents=True, exist_ok=True)
            dossier_dalles.mkdir(parents=True, exist_ok=True)

            # Découverte des dalles via le provider — retourne {nom: url} en
            # combinant index officiel (TMS pour FR, JSON pour NL, etc.) et
            # éventuel fallback grille interne au provider. Le pipeline reste
            # provider-agnostique : il ne suppose ni grille (x_km, y_km) ni
            # protocole d'accès particulier. bbox_marge (pas bbox) pour le
            # filtre géométrique : voir MARGE_HALO_M ci-dessus.
            _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
            _lo1, _la1, _lo2, _la2 = _bbox_enveloppe_transform(
                _t.transform, *bbox_marge)
            bbox_wgs = (_lo1 - 0.05, _la1 - 0.05, _lo2 + 0.05, _la2 + 0.05)
            cache_discover = DOSSIER_CACHE / f"discover_{PROVIDER.CODE}.json"
            # discover_dalles : None = échec réseau/endpoint, {} = pas de
            # couverture. On DISTINGUE (#5) : None -> lever, sinon le chunk
            # finirait sans erreur et le manifeste le marquerait FAIT (données
            # perdues sur une panne réseau, malgré le message « retry »). La
            # boucle de split rattrape l'exception (fail-fast + reprise) et un
            # re-run rejoue le chunk. {} = hors-couverture légitime -> le chunk
            # se termine vide et fait, comme une cellule mer.
            try:
                _d = PROVIDER.discover_dalles(bbox_wgs, bbox_marge, cache_discover)
            except Exception as _e_disc:
                raise RuntimeError(
                    f"tile discovery failed ({type(_e_disc).__name__}: {_e_disc})"
                    " - rerun to resume this chunk") from _e_disc
            if _d is None:
                raise RuntimeError(
                    "tile discovery unavailable (network/endpoint)"
                    " - rerun to resume this chunk")
            dalles_dict = _d

            if args.telechargement:
                _telecharger_dalles_zone(dalles_dict, bbox_marge, dossier_dalles, dossier_ville, args)

            # tifs_run hoisté HORS du `if args.ombrages` : un run tuiles-seules
            # chunké (mbtiles sans --shadings) levait NameError sur tifs_run.
            tifs_run = None   # cibles du run (cf. site jumeau dans main)
            if args.ombrages:
                choix, _spec_i = _resoudre_choix_ombrages(args)
                if choix or _spec_i:
                    dalles_ombrages = _lister_dalles_zone(dalles_dict.keys(), dossier_dalles,
                                                          dossier_ville, bbox_marge)
                    elev = (args.ombrages_elevation if args.ombrages_elevation is not None
                            else ELEVATION_SOLEIL)
                    tifs_run = generer_ombrages(dalles_ombrages, dossier_ville, choix,
                                     elevation_soleil=elev, nom_zone=nom_z,
                                     ecraser_ombrages=args.ombrages_ecraser,
                                     use_sweep=args.sweep_horizon,
                                     svf_gamma=args.svf_gamma,
                                     svf_conv=args.svf_conv, svf_dist=args.svf_dist,
                                     bbox_natif=tuple(bbox_marge),
                                     instances=_spec_i or None)

            if args.mbtiles or args.rmap or args.sqlitedb:
                # Glob/filtre/tuilage factorisés avec le site jumeau de main()
                # (cf. _lister_tifs_ombrages / _tuiler_tifs_ombrages). bbox
                # (nominale, PAS bbox_marge) pour la frontière exacte avec les
                # voisins directs ; tampon_coin_max_m borne le calcul du
                # tampon de coin dans la marge halo ci-dessus.
                traitement_ok = _tuiler_tifs_ombrages(
                    args, _lister_tifs_ombrages(dossier_ville, tifs_run),
                    dossier_ville, nom_z, bbox, decoupe_sortie=False,
                    tampon_coin_max_m=MARGE_HALO_M,
                    mbtiles_attendus=mbtiles_attendus)
    finally:
        args.zone_bbox = _bbox_orig
        args.zone_nom  = _nom_orig
    return _ResultatChunk(traitement_ok, mbtiles_attendus)


from _split_sliding import (
    _DependancesRunnerGlissant,
    _run_split_priori_lidar_glissant as _run_split_priori_lidar_glissant_impl,
    _voisins_dossiers,
)


def _dalles_zone_lookahead(bbox_natif):
    """Découverte SEULE (pas de téléchargement) des noms de dalles d'une
    zone — sert à savoir, AVANT le cleanup d'un morceau, quelles dalles le
    morceau SUIVANT va réclamer (cf. _supprimer_fichiers, R1#5/#9 : une
    dalle de bord partagée entre deux morceaux adjacents ne doit pas être
    effacée par le cleanup du premier si le second en a encore besoin —
    observé en pratique : un chunk peut re-télécharger ~2000 dalles déjà
    fraîches parce que son voisin venait de les purger). Best-effort :
    toute erreur renvoie None, jamais fatal (le cleanup se rabat alors sur
    son comportement d'avant ce garde-fou, pas de régression possible)."""
    try:
        bx1, by1, bx2, by2 = bbox_natif
        _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
        _lo1, _la1, _lo2, _la2 = _bbox_enveloppe_transform(_t.transform, bx1, by1, bx2, by2)
        bbox_wgs = (_lo1 - 0.05, _la1 - 0.05, _lo2 + 0.05, _la2 + 0.05)
        cache_discover = DOSSIER_CACHE / f"discover_{PROVIDER.CODE}.json"
        _d = PROVIDER.discover_dalles(bbox_wgs, (bx1, by1, bx2, by2), cache_discover)
        return set(_d.keys()) if _d else None
    except Exception:
        return None


def _decouvrir_et_telecharger_ombrage(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle,
                                       quiet=False):
    """Découverte + téléchargement des dalles d'un morceau glissant (cle_dl
    dédié) — factorisé hors de _traiter_bbox_lidar_ombrage pour être appelable
    à la fois en synchrone (chemin normal) et en préchargement tâche de fond
    (_PrefetchDalles) sans dupliquer la logique de découverte/download.

    quiet : voir _telecharger_dalles_zone — coupe sa barre \\r (préchargement
            en tâche de fond, cf. appelant _PrefetchDalles._travail).

    Retourne (dalles_dict, dossier_dalles, dossier_ville).
    """
    bx1, by1, bx2, by2 = bbox_natif
    bbox = (bx1, by1, bx2, by2)
    racine = (Path(args.dossier).resolve() if args.dossier
              else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / LIDAR_SUBDIR)
    dossier_ville = racine / nom_z
    dossier_dalles = _dossier_dalles_actif(args, dossier_ville)
    dossier_ville.mkdir(parents=True, exist_ok=True)
    dossier_dalles.mkdir(parents=True, exist_ok=True)

    cle_dl = cle + "_dl"
    with _contexte_manifeste(manifeste, cle_dl):
        _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
        _lo1, _la1, _lo2, _la2 = _bbox_enveloppe_transform(_t.transform, *bbox)
        bbox_wgs = (_lo1 - 0.05, _la1 - 0.05, _lo2 + 0.05, _la2 + 0.05)
        cache_discover = DOSSIER_CACHE / f"discover_{PROVIDER.CODE}.json"
        try:
            _d = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover)
        except Exception as _e_disc:
            raise RuntimeError(
                f"tile discovery failed ({type(_e_disc).__name__}: {_e_disc})"
                " - rerun to resume this chunk") from _e_disc
        if _d is None:
            raise RuntimeError(
                "tile discovery unavailable (network/endpoint)"
                " - rerun to resume this chunk")
        dalles_dict = _d
        if args.telechargement:
            _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args,
                                      quiet=quiet)
    return dalles_dict, dossier_dalles, dossier_ville


def _traiter_bbox_lidar_ombrage(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle,
                                dalles_precharge=None, on_download_done=None,
                                noms_dalles_a_garder=None):
    """
    Étape 1/2 du découpage à priori LiDAR SANS --block (VRT-voisins glissant,
    cf. _run_split_priori_lidar_glissant) : téléchargement + calcul
    d'ombrage SEUL, sur la bbox EXACTE de ce morceau. Pas de marge de
    téléchargement supplémentaire ici : le contexte de bord viendra du VRT
    avec les TIF d'ombrage réels des voisins à l'étape 2 (_tuilage), pas
    d'un débord de dalles payé par CE morceau (cf. --block : seul mode où
    la marge fixe de _traiter_bbox_lidar se justifie, aucun voisin
    accessible entre machines séparées).

    Les dalles brutes sont nettoyées ICI (sous-scope manifeste dédié), tout
    de suite après le calcul. noms_dalles_a_garder (R1#5/#9) épargne les
    dalles de bord dont le morceau SUIVANT a encore besoin (une dalle de
    bord straddle parfois la frontière de deux morceaux adjacents) ; le
    reste n'est jamais réutilisé, contrairement au TIF d'ombrage produit
    (nettoyé plus tard par l'appelant, une fois les voisins passés à
    l'étape 2 — cf. _purger_rangee dans _run_split_priori_lidar_glissant).

    dalles_precharge : résultat déjà obtenu par _PrefetchDalles pendant le
    calcul du morceau PRÉCÉDENT (recouvrement download/calcul) — si fourni,
    saute la découverte+download (déjà faits en tâche de fond). on_download_done
    est appelé dès que ce morceau a ses dalles en main (fraîches ou préchargées) :
    signal pour lancer le préchargement du morceau SUIVANT.
    """
    bx1, by1, bx2, by2 = bbox_natif
    _bbox_orig = args.zone_bbox
    _nom_orig  = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom  = nom_z
    try:
        bbox = (bx1, by1, bx2, by2)
        if dalles_precharge is not None:
            dalles_dict, dossier_dalles, dossier_ville = dalles_precharge
        else:
            dalles_dict, dossier_dalles, dossier_ville = _decouvrir_et_telecharger_ombrage(
                args, bbox, nom_z, nom_zone_base, manifeste, cle)
        if on_download_done:
            on_download_done()

        if args.ombrages:
            choix, _spec_i = _resoudre_choix_ombrages(args)
            if choix or _spec_i:
                with _contexte_manifeste(manifeste, cle):
                    dalles_ombrages = _lister_dalles_zone(dalles_dict.keys(), dossier_dalles,
                                                          dossier_ville, bbox)
                    elev = (args.ombrages_elevation if args.ombrages_elevation is not None
                            else ELEVATION_SOLEIL)
                    generer_ombrages(dalles_ombrages, dossier_ville, choix,
                                     elevation_soleil=elev, nom_zone=nom_z,
                                     ecraser_ombrages=args.ombrages_ecraser,
                                     use_sweep=args.sweep_horizon,
                                     svf_gamma=args.svf_gamma,
                                     svf_conv=args.svf_conv, svf_dist=args.svf_dist,
                                     bbox_natif=tuple(bbox),
                                     instances=_spec_i or None)

        if args.telechargement and getattr(args, "nettoyage", False):
            if getattr(args, "nettoyage_garder_dalles", False):
                _keep = [_dossier_dalles_actif(args)]
                _cloud_cache = getattr(args, "_cloud_cache_dir", None)
                if _cloud_cache is not None:
                    _keep.append(_cloud_cache)
            else:
                _keep = None
            # cle_dl : même sous-clé que _decouvrir_et_telecharger_ombrage (download,
            # fraîchement fait ou préchargé en tâche de fond, cf. dalles_precharge).
            _supprimer_fichiers(manifeste.fichiers_morceau(cle + "_dl"), _keep,
                               noms_garder=noms_dalles_a_garder)
    finally:
        args.zone_bbox = _bbox_orig
        args.zone_nom  = _nom_orig


def _traiter_bbox_lidar_tuilage(args, bbox_natif, nom_z, nom_zone_base, manifeste, cle,
                                i_lat, i_lon, n_lat, n_lon):
    """
    Étape 2/2 (cf. _traiter_bbox_lidar_ombrage) : pour chaque TIF d'ombrage
    de CE morceau, fusionne en VRT avec le même TIF de ses voisins DÉJÀ
    passés par l'étape 1 (jusqu'à 8, diagonales incluses — le coin partagé
    par 4 blocs a besoin du voisin diagonal, pas seulement N/S/E/O), puis
    warp + tuile depuis ce VRT. generer_mbtiles_lidar CALCULE l'ampleur du
    tampon de coin nécessaire (pas une constante) ; ici on ne borne que le
    MAXIMUM sûr, généreux puisque de vrais voisins couvrent déjà largement
    plus qu'un simple coin (contrairement à la marge de téléchargement
    fixe de l'étape 1 / --block).
    """
    bx1, by1, bx2, by2 = bbox_natif
    TAMPON_MAX_M = min(bx2 - bx1, by2 - by1) / 3.0
    _bbox_orig = args.zone_bbox
    _nom_orig  = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom  = nom_z
    conversion_ok = True
    mbtiles_attendus = []
    try:
        if not (args.mbtiles or args.rmap or args.sqlitedb):
            return
        bbox = (bx1, by1, bx2, by2)
        racine = (Path(args.dossier).resolve() if args.dossier
                  else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / LIDAR_SUBDIR)
        dossier_ville = racine / nom_z
        voisins = _voisins_dossiers(racine, nom_zone_base, i_lat, i_lon, n_lat, n_lon)

        cle_t = cle + "_t"
        with _contexte_manifeste(manifeste, cle_t):
            for tif in _lister_tifs_ombrages(dossier_ville, None):
                stem   = re.sub(r'_tuilage_z\d+$', '', tif.stem)
                suffix = stem[len(nom_z) + 1:] if stem.startswith(nom_z + "_") else stem
                nom_base = f"{nom_z}_{suffix}"

                _cogs = [tif]
                for vd in voisins:
                    vf = vd / f"{vd.name}_{suffix}.tif"
                    if vf.exists():
                        _cogs.append(vf)

                if len(_cogs) > 1:
                    import rasterio as _rio_vres
                    with _rio_vres.open(str(tif)) as _ds_res:
                        _res = _ds_res.transform.a
                    vrt_path = dossier_ville / f"_voisins_{suffix}.vrt"
                    _build_vrt_xml(_cogs, vrt_path, _res)
                    _creer_fichier(vrt_path)
                    tif_source = vrt_path
                else:
                    tif_source = tif   # bord de zone sans voisin encore prêt

                mbt_path = dossier_ville / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
                mbtiles_attendus.append(mbt_path)
                mbt_neuf = _mbtiles_a_regenerer(mbt_path, args.tuiles_ecraser, source=tif)
                if mbt_neuf:
                    mbt_out = generer_mbtiles_lidar(
                        tif_source, dossier_ville, nom_base,
                        zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                        format_tuiles=args.formats_image,
                        jpeg_quality=args.qualite_image,
                        bbox_natif=bbox, tampon_coin_max_m=TAMPON_MAX_M,
                        ecraser_tuiles=args.tuiles_ecraser,
                        tile_workers=_tile_workers_defaut())
                else:
                    print(f"  Existing MBTiles: {mbt_path.name}, direct split/conversion")
                    mbt_out = mbt_path
                conversion_ok = (_convertir_formats(
                    mbt_out, args, decoupe_sortie=False,
                    mbtiles_neuf=mbt_neuf) and conversion_ok)
    finally:
        args.zone_bbox = _bbox_orig
        args.zone_nom  = _nom_orig
    return _ResultatChunk(conversion_ok, mbtiles_attendus)


def _run_split_priori_lidar_glissant(
    args,
    sous_zones,
    nom_zone,
    racine_pr,
    overwrite_actif,
    entete_chunk,
    t_debut,
):
    """Façade compatible vers le runner LiDAR glissant extrait."""
    dependances = _DependancesRunnerGlissant(
        fabrique_manifeste=Manifeste,
        signature_config=_signature_config,
        morceau_termine_reutilisable=_morceau_termine_reutilisable,
        fabrique_prefetch=_PrefetchDalles,
        dalles_zone_lookahead=_dalles_zone_lookahead,
        garde_disque=_garde_disque,
        definir_chunk_log=_definir_chunk_log,
        traiter_ombrage=_traiter_bbox_lidar_ombrage,
        traiter_tuilage=_traiter_bbox_lidar_tuilage,
        normaliser_resultat_chunk=_normaliser_resultat_chunk,
        chunk_livrable_complet=_chunk_livrable_complet,
        supprimer_fichiers=_supprimer_fichiers,
        formater_duree=_hms,
        planche_depuis_dossier=_planche_depuis_dossier,
        dossier_travail=DOSSIER_TRAVAIL,
        lidar_subdir=LIDAR_SUBDIR,
    )
    return _run_split_priori_lidar_glissant_impl(
        args,
        sous_zones,
        nom_zone,
        racine_pr,
        overwrite_actif,
        entete_chunk,
        t_debut,
        dependances=dependances,
    )


def _traiter_bbox_wmts(args, bbox_wgs84, nom_z, nom_zone_base, layer, style, img_fmt, fmt_ext,
                       apikey_requis, manifeste, cle):
    """
    Traite un morceau WMTS directement en Python (sans subprocess).
    Appelé par la boucle à priori dans main_wmts().
    nom_zone_base : nom du projet parent (ex: gareoult2).
    nom_z         : nom du morceau   (ex: gareoult2_001x001).
    """
    lon_w, lat_s, lon_e, lat_n = bbox_wgs84
    _nom_orig = args.zone_nom
    args.zone_nom = nom_z
    traitement_ok = True
    mbtiles_attendus = []
    try:
        with _contexte_manifeste(manifeste, cle):
            zoom_min = min(args.zoom_min, args.zoom_max)
            zoom_max = max(args.zoom_min, args.zoom_max)
            tuiles = calculer_grille_xyz(lat_s, lon_w, lat_n, lon_e, zoom_min, zoom_max)
            total_tuiles = compter_tuiles_xyz(lat_s, lon_w, lat_n, lon_e,
                                              zoom_min, zoom_max)
            # Structure : <racine>/<nom_zone_base>/raster/<nom_z>/
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / "raster")
            dossier = racine_base / nom_z
            dossier.mkdir(parents=True, exist_ok=True)
            # Source de vérité UNIQUE (fin du drift jumeau R2#14) : le split
            # honore --image-format png comme la passe simple, et encode la
            # qualité dans le nom (R2#18) via le même helper.
            _jpeg_q = _jpeg_quality_sortie(img_fmt, args.formats_image,
                                           args.qualite_image)
            nom_fichier    = _nom_mbtiles_wmts(nom_z, args.couche,
                                               zoom_min, zoom_max, _jpeg_q)
            chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
            mbtiles_attendus.append(chemin_mbtiles)
            dossier_cache  = DOSSIER_CACHE / "ign_raster"
            dossier_cache.mkdir(parents=True, exist_ok=True)
            _mbt_neuf = _mbtiles_a_regenerer(chemin_mbtiles, args.tuiles_ecraser)
            if _mbt_neuf:
                generer_mbtiles_wmts(
                    chemin=chemin_mbtiles,
                    tuiles_iter=tuiles,
                    total=total_tuiles,
                    nom_zone=nom_z,
                    fmt_ext=fmt_ext,
                    zoom_min=zoom_min,
                    zoom_max=zoom_max,
                    layer=layer,
                    style=style,
                    img_fmt=img_fmt,
                    apikey=args.apikey,
                    apikey_requis=apikey_requis,
                    workers=args.workers,
                    bbox_wgs84=(lon_w, lat_s, lon_e, lat_n),
                    jpeg_quality=_jpeg_q,
                    dossier_cache=dossier_cache,
                    ecraser_tuiles=args.tuiles_ecraser,
                    ecraser_dalles=args.telechargement_ecraser)
            if chemin_mbtiles.exists():
                traitement_ok = _convertir_formats(
                    chemin_mbtiles, args, decoupe_sortie=False,
                    mbtiles_neuf=_mbt_neuf)
            else:
                traitement_ok = False
    finally:
        args.zone_nom = _nom_orig
    return _ResultatChunk(traitement_ok, mbtiles_attendus)


def decouper_mbtiles(src_mbtiles, cote_km=0.0, n_morceaux=1, n_cols=0, n_rows=0,
                     dossier=None, ecraser=False):
    """
    Découpe un MBTiles source en sous-MBTiles.

    Modes (par ordre de priorité) :
      - n_cols > 0 et n_rows > 0 : grille explicite cols×rows (depuis la GUI).
      - n_morceaux > 1            : N morceaux, grille auto la plus carrée.
      - cote_km  > 0              : carrés de ~cote_km km de côté.
      - sinon                     : retourne [src_mbtiles] sans découpe.

    Nommage des sorties : {stem}_{ligne:03d}x{col:03d}.mbtiles
    Retourne la liste des Path créés.
    """
    import sqlite3 as _sq

    if n_cols > 0 and n_rows > 0:
        # Grille explicite — on force n_morceaux cohérent pour la suite
        n_morceaux = n_cols * n_rows
    if n_morceaux <= 1 and cote_km <= 0:
        return [src_mbtiles]

    if not src_mbtiles.exists():
        print(f"  ERROR splitting: {src_mbtiles.name} not found")
        return []

    out_dir = dossier or src_mbtiles.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    con = _sq.connect(str(src_mbtiles))
    meta = dict(con.execute("SELECT name, value FROM metadata").fetchall())
    fmt      = meta.get("format", "jpeg")
    # Zooms : LIRE les tuiles si les métadonnées manquent, au lieu d'un 0/17
    # arbitraire (R2#12). Un mbtiles z18-seul sans metadata donnait minzoom=0/
    # maxzoom=17 → la boucle range(0,18) ratait z18 → morceaux vides, et les
    # métadonnées des sorties mentaient. Miroir du fix zooms sqlitedb (R2#11).
    _zr = con.execute("SELECT MIN(zoom_level), MAX(zoom_level) FROM tiles").fetchone()
    _z_reel_min = _zr[0] if _zr and _zr[0] is not None else 0
    _z_reel_max = _zr[1] if _zr and _zr[1] is not None else 17
    zoom_min = int(meta["minzoom"]) if "minzoom" in meta else _z_reel_min
    zoom_max = int(meta["maxzoom"]) if "maxzoom" in meta else _z_reel_max

    # Lire la bbox globale depuis metadata ou calculer depuis les tuiles
    if "bounds" in meta:
        lon0, lat0, lon1, lat1 = [float(v) for v in meta["bounds"].split(",")]
    else:
        rows = con.execute(
            "SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
            "FROM tiles WHERE zoom_level=?", (zoom_max,)).fetchone()
        if not rows or rows[0] is None:
            print("  ERROR: MBTiles empty")
            con.close()
            return []
        n = 2 ** zoom_max
        lon0 = rows[0] / n * 360.0 - 180.0          # MIN(col) → ouest
        lon1 = (rows[1] + 1) / n * 360.0 - 180.0    # MAX(col)+1 → est
        # tile_row est en TMS (y=0 au SUD) ; XYZ y = n-1-tms (y=0 au NORD).
        # Nord = plus PETIT y XYZ = n-1-MAX(tms) ; Sud = plus GRAND y XYZ =
        # n-1-MIN(tms). L'ancien code prenait MIN(tms) pour le nord : correct
        # par accident sur UNE tuile (bords de la seule tuile), mais dès ≥2
        # lignes lat1 recevait le bord nord de la tuile SUD → bbox retournée
        # ET rétrécie (R2#12).
        y_nord_xyz = n - 1 - rows[3]   # MAX(tms) → tuile la plus au NORD
        y_sud_xyz  = n - 1 - rows[2]   # MIN(tms) → tuile la plus au SUD
        def _tile_to_lat(y, n):
            return math.degrees(math.atan(math.sinh(math.pi * (1 - 2*y/n))))
        lat1 = _tile_to_lat(y_nord_xyz,     n)   # lat_max = bord nord (haut tuile nord)
        lat0 = _tile_to_lat(y_sud_xyz + 1,  n)   # lat_min = bord sud (bas tuile sud)

    lat_c = (lat0 + lat1) / 2

    # ── Calcul de la grille via la fonction unifiée ────────────────────────
    if n_cols > 0 and n_rows > 0:
        # Grille explicite cols×rows
        r_lat = (lat1 - lat0) / n_rows
        r_lon = (lon1 - lon0) / n_cols
        r_lat_km = r_lat * 111.0
        r_lon_km = r_lon * 111.0 * math.cos(math.radians(lat_c))
        mode_desc = (f"{n_rows}×{n_cols} grille"
                     f" (~{r_lat_km:.0f}×{r_lon_km:.0f} km/morceau)")
        sous_zones = []
        for i_lat in range(n_rows):
            lat_s = lat0 + i_lat * r_lat
            lat_n = min(lat_s + r_lat, lat1)
            for i_lon in range(n_cols):
                lon_w = lon0 + i_lon * r_lon
                lon_e = min(lon_w + r_lon, lon1)
                sous_zones.append((i_lat, i_lon, lon_w, lat_s, lon_e, lat_n))
    else:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            lon0, lat0, lon1, lat1, n_morceaux, cote_km, unite_m=False)

    if len(sous_zones) <= 1:
        print("  Splitting: zone too small -> single file")
        con.close()
        return [src_mbtiles]

    print(f"  Splitting: {mode_desc}")

    # Nom de base : garder le suffixe _z{min}-{max} pour que les morceaux l'incluent
    stem_base = src_mbtiles.stem  # ex: 83_multi_ombrage_z8-18

    # Compter lignes/colonnes pour le padding. Dérivé de sous_zones (et pas de
    # i_lat/i_lon de boucle) : robuste aux DEUX branches — la branche else
    # (rayon / n_morceaux) ne lie jamais i_lat/i_lon → NameError sinon. Le +1
    # donne le COMPTE (pas l'index max), donc pad correct jusqu'aux puissances
    # exactes (1000 lignes → pad 4).
    n_lats = max(z[0] for z in sous_zones) + 1
    n_lons = max(z[1] for z in sous_zones) + 1
    pad = max(3, len(str(max(n_lats, n_lons))))

    sorties = []

    for i_lat, i_lon, lon_w, lat_s, lon_e, lat_n in sous_zones:
        sfx   = f"_{(i_lat+1):0{pad}d}x{(i_lon+1):0{pad}d}"
        nom_z    = f"{stem_base}{sfx}"
        chemin_z = out_dir / f"{nom_z}.mbtiles"

        if chemin_z.exists() and not ecraser:
            print(f"  Existing chunk: {chemin_z.name} - skipped")
            sorties.append(chemin_z)
            continue
        # Sur écrasement, PAS d'unlink préalable : chemin_z_part.replace()
        # écrase atomiquement en fin de découpe. Supprimer maintenant perdrait
        # le morceau précédent si la découpe de celui-ci échoue.

        # Écriture via .part + rename : un sous-mbtiles présent est toujours
        # complet (un kill mi-découpe laissait un partiel repris tel quel par
        # le check "Existing chunk" au run suivant).
        chemin_z_part = _chemin_part(chemin_z)
        con_z = _sq.connect(str(chemin_z_part))
        # Écritures rapides SANS risque : la cible est un .part, jeté sur
        # échec (au pire un crash OS laisse un .part corrompu, purgé par
        # _chemin_part au run suivant). fsync par commit inutile ici.
        con_z.execute("PRAGMA journal_mode=MEMORY;")
        con_z.execute("PRAGMA synchronous=OFF;")
        con_z.executescript("""
            CREATE TABLE metadata (name TEXT, value TEXT);
            CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER,
                                tile_row INTEGER, tile_data BLOB);
            CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
        """)

        cx = (lon_w + lon_e) / 2
        cy = (lat_s + lat_n) / 2
        # Reprendre TOUTES les métadonnées source (attribution, json/vector_layers,
        # scheme, licence...), puis surcharger celles PROPRES au morceau (R2#13).
        # L'ancien code ne recréait que 9 clés → attribution/json/scheme/licence
        # étaient perdues à chaque découpe (contrat MBTiles cassé pour un lecteur
        # qui les attend : couche vecteur sans json = illisible, attribution/
        # licence effacées). type/version/description viennent maintenant de la
        # source telle quelle (avec défauts si absentes).
        _meta_z = dict(meta)
        _meta_z.setdefault("type", "overlay")
        _meta_z.setdefault("version", "1.0")
        _meta_z.setdefault("description", "")
        _meta_z.update({
            "name":    nom_z,
            "format":  fmt,
            "minzoom": str(zoom_min),
            "maxzoom": str(zoom_max),
            "bounds":  f"{lon_w:.6f},{lat_s:.6f},{lon_e:.6f},{lat_n:.6f}",
            "center":  f"{cx:.6f},{cy:.6f},{zoom_max}",
        })
        for k, v in _meta_z.items():
            con_z.execute("INSERT INTO metadata VALUES (?,?)", (k, str(v)))
        con_z.commit()

        # Copier les tuiles de la bbox — itération INCRÉMENTALE (fetchmany) :
        # l'ancien fetchall() chargeait TOUTES les tuiles du zoom (BLOBs
        # compris) en RAM — plusieurs Go au niveau z18 départemental ; le
        # batch de 500 ne bornait que l'INSERT, pas le pic de lecture.
        n_tuiles = 0
        BATCH    = 2000
        for z in range(zoom_min, zoom_max + 1):
            n  = 2 ** z
            # bbox WGS84 → colonnes/lignes XYZ
            x0 = int((lon_w + 180) / 360 * n)
            x1 = int((lon_e + 180) / 360 * n)
            lat_n_r = math.radians(lat_n)
            lat_s_r = math.radians(lat_s)
            y0 = int((1 - math.log(math.tan(lat_n_r) + 1/math.cos(lat_n_r))/math.pi) / 2 * n)
            y1 = int((1 - math.log(math.tan(lat_s_r) + 1/math.cos(lat_s_r))/math.pi) / 2 * n)
            # TMS : tile_row = n-1-y_xyz
            row0 = n - 1 - y1   # lat_s → y_xyz max → tms min
            row1 = n - 1 - y0   # lat_n → y_xyz min → tms max
            cur_src = con.execute(
                "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles "
                "WHERE zoom_level=? AND tile_column BETWEEN ? AND ? "
                "AND tile_row BETWEEN ? AND ?",
                (z, x0, x1, row0, row1)
            )
            while True:
                rows = cur_src.fetchmany(BATCH)
                if not rows:
                    break
                con_z.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", rows)
                con_z.commit()
                n_tuiles += len(rows)
        con_z.close()

        if n_tuiles == 0:
            _nettoyer_sqlite_part(chemin_z_part)
            print(f"  Sub-zone [{i_lat},{i_lon}]: empty - skipped")
            continue

        try:
            _valider_sqlite_part(
                chemin_z_part, {"metadata": None, "tiles": n_tuiles}
            )
        except BaseException:
            _nettoyer_sqlite_part(chemin_z_part)
            raise
        chemin_z_part.replace(chemin_z)
        print(f"  Sub-zone [{i_lat},{i_lon}]: {n_tuiles:,} tiles → {chemin_z.name}")
        sorties.append(chemin_z)

    con.close()
    return sorties


def _convertir_un_mbtiles(sf, args, mbtiles_neuf=True):
    """Façade compatible vers la conversion unitaire extraite."""
    return _convertir_un_mbtiles_impl(
        sf,
        args,
        mbtiles_neuf=mbtiles_neuf,
        generer_rmap=generer_rmap_depuis_mbtiles,
        generer_sqlitedb=generer_sqlitedb_depuis_mbtiles,
    )


def _convertir_formats(
    mbt_out,
    args,
    decoupe_sortie=True,
    mbtiles_neuf=True,
):
    """Façade compatible vers l'orchestration multi-format extraite."""
    return _convertir_formats_impl(
        mbt_out,
        args,
        decoupe_sortie=decoupe_sortie,
        mbtiles_neuf=mbtiles_neuf,
        decouper=decouper_mbtiles,
        convertir_un=_convertir_un_mbtiles,
    )


def _ajouter_args_zone(parser, *, width_default, bbox_metavar, bbox_help=None,
                        avec_dossier=False, avec_help_full=False):
    """Ajoute les flags --zone-{ville,gps,bbox,departement,width,nom}
    au parser fourni, en factorisant la duplication entre main(),
    main_wmts(), main_wfs(). Les divergences réelles sont :

    - width_default : LARGEUR (côté du carré) par défaut, en km. main()
      utilise None (résolu à 20 plus tard), main_wmts/wfs utilisent 20.0 dès
      le parser. NB : c'est un CÔTÉ, pas un rayon (20 km de large = l'ancien
      rayon de 10 km, avant le passage au modèle largeur).
    - bbox_metavar  : libellé de la bbox WGS84 "W,S,E,N".
    - bbox_help     : help textuel propre à chaque mode.
    - avec_dossier  : si True, ajoute aussi --dossier (uniquement pour main()
      qui le mélange avec --dossier-dalles ; les autres l'ajoutent à part).
    - avec_help_full : si True, help détaillé (mode CLI top-level main()).

    Retourne le mutually exclusive group, au cas où l'appelant veut y ajouter
    d'autres flags.
    """
    loc = parser.add_mutually_exclusive_group()
    if avec_help_full:
        loc.add_argument("--zone-city", "--zone-ville",  metavar="NAME", dest="zone_ville",
                         help="City name (Nominatim geocoding)")
        loc.add_argument("--zone-gps",    metavar="LAT,LON",
                         help="GPS coordinates, e.g. 43.3156,6.0423")
        loc.add_argument("--zone-bbox",   metavar=bbox_metavar,
                         help=bbox_help or "")
        loc.add_argument("--zone-department", "--zone-departement", metavar="NUM", dest="zone_departement",
                         help="Department number, e.g. 83, 2A, 971. "
                              "Automatically fetches the bbox from geo.api.gouv.fr. "
                              "The folder name is set automatically (e.g. var_83).")
        loc.add_argument("--zone-region", metavar="SLUG",
                         help="Geofabrik region, e.g. provence-alpes-cote-d-azur. "
                              "Processes the whole region = bounding box of its departments. "
                              "With --osm: single regional map (full PBF, no re-clip).")
    else:
        loc.add_argument("--zone-city", "--zone-ville",       metavar="NAME", dest="zone_ville")
        loc.add_argument("--zone-gps",         metavar="LAT,LON")
        if bbox_help:
            loc.add_argument("--zone-bbox",    metavar=bbox_metavar, help=bbox_help)
        else:
            loc.add_argument("--zone-bbox",    metavar=bbox_metavar)
        loc.add_argument("--zone-department", "--zone-departement", metavar="NUM", dest="zone_departement")
        loc.add_argument("--zone-region", metavar="SLUG")

    _width_contract = (f"default: {width_default}"
                       if width_default is not None
                       else "required with --zone-city/--zone-gps")
    parser.add_argument("--zone-width", "--zone-largeur", type=_arg_float_positif,
                        default=width_default, metavar="KM", dest="zone_width",
                        help=f"Width in km of the square around the point "
                             f"(the side, not a radius; {_width_contract})")
    parser.add_argument("--zone-name", "--zone-nom", metavar="NAME", default=None, dest="zone_nom",
                        help="Output folder name for the processed zone. "
                             "Automatically derived from the city, GPS coordinates, "
                             "bbox, department, or region when omitted.")
    if avec_dossier:
        parser.add_argument("--output-dir", "--dossier", metavar="PATH", default=None, dest="dossier",
                            help="Root output folder.")
    # Racine du cache partagé (dalles, tuiles WMTS, PBF OSM, index…). Commune à
    # tous les modes zone-based, d'où sa place ici. --tiles-dir reste le réglage
    # fin des seules dalles LiDAR, prioritaire.
    parser.add_argument("--cache-dir", "--dossier-cache", metavar="PATH", default=None,
                        dest="cache_dir",
                        help="Root folder for ALL persistent caches (tiles, WMTS, "
                             "OSM PBF, discovery index). Default: <work-dir>/cache. "
                             "Handy to put a large cache on another drive.")
    # Racine de PRODUCTION : les artefacts CALCULES mais partages entre projets.
    # Aujourd'hui = le .tif du mode LAZ (calcule du nuage avec tes reglages ;
    # le .tif MNT, lui, vient du serveur et reste au cache). LiDAR uniquement.
    parser.add_argument("--production-dir", "--dossier-production", metavar="PATH",
                        default=None, dest="production_dir",
                        help="Root folder for COMPUTED-but-shared artifacts "
                             "(LAZ .tif). Default: <work-dir>/production. The "
                             "downloaded point cloud (.laz) stays in the cache.")
    return loc


def _resoudre_zone_wgs84(args):
    """
    Résout la zone géographique depuis les arguments CLI → bbox WGS84 + nom_zone.
    Commun à main_wmts() et main_wfs().
    Retourne (lon_min, lat_min, lon_max, lat_max, nom_zone).
    """
    lat_min = lon_min = lat_max = lon_max = None
    # Normalisation systématique dès l'entrée : élimine les différences
    # de casse et d'accentuation entre pipelines (--ignraster, --ignvecteur,
    # --fusionner) quel que soit ce que l'utilisateur a saisi.
    _zone_nom_raw = getattr(args, 'zone_nom', None)
    nom_zone = normaliser_nom(_zone_nom_raw) if _zone_nom_raw else None

    if getattr(args, "zone_region", None):
        slug = args.zone_region.strip().lower()
        nom_reg, bx1, by1, bx2, by2 = geocoder_region(slug)
        if nom_reg is None:
            sys.exit(1)
        if not nom_zone:
            nom_zone = normaliser_nom(slug)
        # geocoder_region retourne du Lambert 93 — reconvertir en WGS84
        # (enveloppe 4 coins, cf. _bbox_enveloppe_transform)
        lon_min, lat_min, lon_max, lat_max = _bbox_enveloppe_transform(
            _natif_vers_wgs84, bx1, by1, bx2, by2)

    elif args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        if not nom_zone:
            nom_zone = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        # geocoder_departement retourne du Lambert 93 — reconvertir en WGS84
        # pour le WFS (enveloppe 4 coins, cf. _bbox_enveloppe_transform)
        lon_min, lat_min, lon_max, lat_max = _bbox_enveloppe_transform(
            _natif_vers_wgs84, bx1, by1, bx2, by2)

    elif args.zone_bbox:
        try:
            parts = [float(v.strip()) for v in args.zone_bbox.split(",")]
            lon_min, lat_min, lon_max, lat_max = parts
        except (ValueError, IndexError):
            print("  Invalid bbox format. Example: --zone-bbox 5.9,43.1,6.6,43.8")
            sys.exit(1)
        lon_min, lat_min, lon_max, lat_max = _bbox_valide_wgs84(
            lon_min, lat_min, lon_max, lat_max)
        if not nom_zone:
            nom_zone = _nom_zone_bbox_auto(
                lon_min, lat_min, lon_max, lat_max)

    elif args.zone_gps:
        try:
            parts = [p.strip() for p in args.zone_gps.replace(";", ",").split(",")]
            lat_c, lon_c = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            print("  Invalid GPS format. Example: --zone-gps 43.3156,6.0423")
            sys.exit(1)
        if not (math.isfinite(lat_c) and math.isfinite(lon_c)
                and -90 <= lat_c <= 90 and -180 <= lon_c <= 180):
            print("  ERROR: GPS out of range (lat [-90,90], lon [-180,180]).")
            sys.exit(1)
        if not nom_zone:
            nom_zone = _nom_zone_gps_auto(lat_c, lon_c)
        _demi  = (args.zone_width or 20.0) / 2.0   # côté → demi-étendue
        r     = _demi / 111.0
        r_lon = _demi / (111.0 * max(0.01, math.cos(math.radians(lat_c))))  # garde pôle (R2#45)
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    elif args.zone_ville:
        nom_zone = nom_zone or normaliser_nom(args.zone_ville)
        print(f"  Geocoding '{args.zone_ville}'...")
        lat_c, lon_c = geocoder_ville_wgs84(args.zone_ville)
        if lat_c is None:
            sys.exit(1)
        _demi  = (args.zone_width or 20.0) / 2.0   # côté → demi-étendue
        r     = _demi / 111.0
        r_lon = _demi / (111.0 * max(0.01, math.cos(math.radians(lat_c))))  # garde pôle (R2#45)
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    else:
        print("  ERROR: a zone option is required "
              "(--zone-city / --zone-gps / --zone-bbox / --zone-department)")
        sys.exit(1)

    if not nom_zone:
        sys.exit(1)

    return lon_min, lat_min, lon_max, lat_max, nom_zone


def main_decouper():
    """
    Mode --decouper : découpe a posteriori un MBTiles existant.
    Usage : lidar2map.py --decouper --source fichier.mbtiles
            [--cols C --rows R | --split-width KM]
            [--formats-fichier mbtiles rmap sqlitedb]
            [--tuiles-ecraser]
    """
    import argparse
    t_debut = time.time()
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --split",
        description="A posteriori splitting of an existing MBTiles.")
    parser.add_argument("--split", "--decouper", action="store_true", dest="decouper")
    parser.add_argument("--source", required=True, metavar="PATH",
                        help="Source .mbtiles file to split.")
    parser.add_argument("--cols", type=int, default=0, metavar="N",
                        help="Number of grid columns (East-West).")
    parser.add_argument("--rows", type=int, default=0, metavar="N",
                        help="Number of grid rows (North-South).")
    parser.add_argument("--split-width", "--split-largeur", type=_arg_float_non_negatif, default=0.0, metavar="KM",
                        dest="split_width", help="Split into ~KM km squares (KM = the side).")
    # Mode raster uniquement : pas de map/geojson/transparent-raster (sorties
    # vecteur) — spécialisation intentionnelle, cf. le parser principal (l.~8699).
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["mbtiles", "rmap", "sqlitedb"], default=["mbtiles"],
                        metavar="FMT")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser")
    args = parser.parse_args()
    _valider_zooms(args, parser)
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff

    src = Path(args.source)
    if not src.exists():
        print(f"  ERROR: file not found: {src}"); sys.exit(1)
    if src.suffix.lower() != ".mbtiles":
        print(f"  ERROR: --source expects a .mbtiles (got: {src.suffix})"); sys.exit(1)

    _historique_debut()
    dossier_resultat = str(src.resolve().parent)

    print("=" * 55)
    print("  Raster MBTiles splitting")
    print("=" * 55)
    print(f"  Source  : {src}")
    print(f"  Formats : {' '.join(_ff)}")
    if args.cols > 0 and args.rows > 0:
        print(f"  Grille  : {args.cols} cols × {args.rows} lignes")
    elif args.split_width:
        print(f"  Side    : {args.split_width} km/chunk")

    sorties = decouper_mbtiles(src, cote_km=args.split_width,
                               n_cols=args.cols, n_rows=args.rows,
                               ecraser=args.tuiles_ecraser)
    if not sorties:
        print("\n  ERROR: splitting produced no output file.")
        print(f"  Done! Folder: {dossier_resultat}")
        _historique_depuis_argv(
            int(time.time() - t_debut), dossier_resultat, statut="ko")
        sys.exit(1)
    _nb_ko = 0
    for sf in sorties:
        # Livrables finaux régénérés d'office (cf. _convertir_un_mbtiles).
        _conv_ok = True
        if args.rmap:
            _conv_ok = (generer_rmap_depuis_mbtiles(sf, ecraser=True) is not None) and _conv_ok
        if args.sqlitedb:
            _conv_ok = (generer_sqlitedb_depuis_mbtiles(sf, ecraser=True) is not None) and _conv_ok
        # Ne PAS supprimer le mbtiles intermédiaire si une conversion demandée a
        # échoué : sinon on efface la seule donnée survivante (R2#6). On le garde
        # comme filet, même quand l'utilisateur n'avait pas demandé le mbtiles.
        if not _conv_ok:
            _nb_ko += 1
            print(f"  WARNING: conversion(s) failed for {sf.name}; .mbtiles kept.")
            continue
        if not args.mbtiles and sf != src and sf.exists():
            sf.unlink()
    if _nb_ko:
        print(f"\n  Splitting done with {_nb_ko} conversion failure(s).")
        print(f"  Done! Folder: {dossier_resultat}")
        _historique_depuis_argv(
            int(time.time() - t_debut), dossier_resultat, statut="ko")
        sys.exit(1)
    print("\n  Splitting done.")
    print(f"  Done! Folder: {dossier_resultat}")
    _historique_depuis_argv(int(time.time() - t_debut), dossier_resultat)


def _construire_parser_wmts():
    """Construit le parser argparse du workflow raster WMTS (--raster)."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py --raster --zone-city gareoult --zoom-min 12 --zoom-max 16 --file-formats mbtiles
  python lidar2map.py --raster --layer ORTHOIMAGERY.ORTHOPHOTOS --zone-department 83 --zoom-min 14 --zoom-max 17 --file-formats mbtiles
  python lidar2map.py --raster --layer GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2 --zone-city gareoult --zoom-min 10 --zoom-max 16 --file-formats mbtiles
  python lidar2map.py --osm --layer "highway=* waterway=* natural=water" --zone-city gareoult
  python lidar2map.py --raster --source gareoult_scan25_z12-16.mbtiles --file-formats rmap
        """
    )
    parser.add_argument("--version", action="version",
                        version=f"lidar2map {VERSION} ({VERSION_DATE}), multi-provider")
    parser.add_argument("--raster", "--ignraster", action="store_true", dest="ignraster",
                        help="IGN raster mode via WMTS. "
                             "Use --layer for the layer (default: planign). "
                             "Ex: --raster --layer GEOGRAPHICALGRIDSYSTEMS.MAPS")
    # Consommé tôt par _load_provider (scan de sys.argv) ; déclaré ici uniquement
    # pour qu'argparse ne le rejette pas. Le raster US (--layer naip) passe par
    # --provider us-tnm depuis le GUI comme depuis la CLI.
    parser.add_argument("--provider", default=None, metavar="CODE",
                        help="Provider (default: fr-ign). Détermine les couches "
                             "raster disponibles (fr-ign → IGN ; us-tnm → naip).")

    # ── Découpage à priori (raster uniquement) ──────────────────────────────
    grp_priori = parser.add_argument_group(
        "A priori splitting — --raster only",
        "Sequential chunk processing with automatic resume (manifeste.json).\n"
        "The same parameters also control the splitting of output files.")
    grp_priori.add_argument("--split-cols", "--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Number of grid columns (East-West).")
    grp_priori.add_argument("--split-rows", "--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Number of grid rows (North-South).")
    grp_priori.add_argument("--split-width", "--split-largeur", type=_arg_float_non_negatif, default=0.0, metavar="KM",
                            dest="split_width",
                            help="Alternative: split into ~KM km squares (KM = the side).")
    grp_priori.add_argument("--cleanup", "--nettoyage", action="store_true", dest="nettoyage",
                            help="Delete intermediate tiles + TIFs after each chunk. "
                                 "Essential for large areas (a whole department).")
    grp_priori.add_argument("--min-free-gb", "--min-disque-go", type=_arg_float_non_negatif, default=0.0, metavar="GB",
                            dest="min_free_gb",
                            help="Stop cleanly before a chunk if free disk space drops below GB "
                                 "(0 = disabled). Set it ABOVE one chunk's peak footprint "
                                 "(intermediates + tile pyramid). Exits with code 3 so a shell "
                                 "loop can tell a resumable disk-stop from a real error.")

    # Zone
    _ajouter_args_zone(
        parser,
        width_default=20.0,
        bbox_metavar="W,S,E,N",
        bbox_help="WGS84 bbox: lon_min,lat_min,lon_max,lat_max",
    )

    # Couche + clé
    # Pas de choices=COUCHES.keys() : le résolveur (plus bas) accepte AUSSI un
    # identifiant WMTS complet (ex. GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2), ce que
    # la doc annonce ; `choices` transformait cette branche en code mort et
    # rejetait tout id complet avant le résolveur (R2#18). Un alias/id inconnu
    # échoue proprement en 404 au fetch.
    parser.add_argument("--layer", "--couche",  default="planign", dest="couche",
                        metavar="LAYER",
                        help="WMTS layer alias (planign, ortho, scan25…) or full "
                             "id (GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2). Default: "
                             "planign (public, no key). Restricted pro layers: "
                             "scan25 scan25tour scan100 scanoaci.")
    parser.add_argument("--api-key", "--apikey",  default=APIKEY_DEFAUT, metavar="KEY", dest="apikey",
                        help="IGN API key for restricted layers (scan25, scan100…). "
                             "⚠ Professional access only (cartes.gouv.fr account + SIRET). "
                             "Individuals must use the public layers (planign, ortho…). "
                             "Can also be set via the IGN_APIKEY env variable.")

    # Zooms
    parser.add_argument("--zoom-min", type=int, default=10, metavar="N")
    parser.add_argument("--zoom-max", type=int, default=16, metavar="N")

    # Sorties. Mode raster uniquement : pas de map/geojson/transparent-raster
    # (sorties vecteur) — spécialisation intentionnelle, cf. parser principal (l.~8699).
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["mbtiles","rmap","sqlitedb"],
                        default=[], metavar="FMT",
                        help="Output file formats: mbtiles rmap sqlitedb (multi-value).")
    parser.add_argument("--source",   metavar="PATH", default=None,
                        help="Existing .mbtiles file → RMAP conversion "
                             "(standalone mode, no zone required). Requires rmap format. "
                             "Ex: --source gareoult_scan25_z12-16.mbtiles --file-formats rmap")
    parser.add_argument("--output-dir", "--dossier",  metavar="PATH", default=None, dest="dossier",
                        help="Output folder (default: Projets/<name>/raster/)")

    # Comportement
    parser.add_argument("--workers",       type=_arg_int_positif, default=NB_WORKERS, metavar="N")
    parser.add_argument("--image-format", "--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format of tile images: auto, jpeg or png (default: auto).")
    parser.add_argument("--image-quality", "--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="JPEG quality of tile images (default: 85).")
    parser.add_argument("--download-overwrite", "--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Overwrite cached tiles (force re-download)")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Overwrite existing MBTiles")
    return parser


def _traiter_source_wmts(args):
    """Façade compatible vers la conversion autonome raster WMTS."""
    return _traiter_source_wmts_impl(
        args,
        dependances=_dependances_sources_terrain(),
    )


def _resoudre_couche_wmts(args):
    """Résout la couche WMTS demandée (alias court ou identifiant complet)
    et plafonne les zooms selon les capacités réelles de la couche
    (GetCapabilities IGN ou table XYZ). Mute `args.zoom_min`/`args.zoom_max`
    (pour que `_traiter_bbox_wmts` hérite des bornes capées côté split) et
    retourne (layer, style, img_fmt, apikey_requis, fmt_ext, zoom_min, zoom_max)
    pour le reste de `main_wmts()`."""
    # ── Résolution de la couche ───────────────────────────────────────────────
    # --couche peut être un alias court (planign) ou un identifiant complet
    # (GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2). Si absent → planign par défaut.
    if not args.couche:
        args.couche = "planign"
    # Résoudre alias court → identifiant complet si besoin
    if args.couche in COUCHES:
        layer, style, img_fmt, apikey_requis = COUCHES[args.couche]
    else:
        # Identifiant complet passé directement — détection format/clé
        layer = args.couche
        style = "normal"
        img_fmt = "image/jpeg" if any(x in layer for x in
                  ["MAPS", "ORTHOIMAGERY", "ETATMAJOR"]) else "image/png"
        apikey_requis = any(x in layer for x in ["MAPS", "SCAN"])
        print(f"  Layer: {layer} (direct id)")
    # img_fmt = format DEMANDÉ AU SERVEUR (URL WMTS). DOIT rester sur le
    # format natif que l'IGN sert pour cette couche — sinon : HTTP 400
    # "Format image/X unknown" (planign ne sert PAS en JPEG, ortho ne sert
    # PAS en PNG, etc.).
    # L'argument --formats-image contrôle UNIQUEMENT le format de sortie
    # dans le MBTiles via re-encodage côté client (cf. _jpeg_q ci-dessous).
    fmt_ext = "jpg" if "jpeg" in img_fmt else "png"

    # --image-format png sur une couche nativement JPEG (ortho, scan*, étatmajor) :
    # convertir JPEG→PNG ne restaure aucune qualité (PNG lossless d'une image
    # lossy = fichier bien plus lourd, zéro gain). On garde le JPEG en le
    # SIGNALANT, au lieu d'ignorer le flag en silence (R2#14). Le sens inverse
    # (PNG natif → jpeg) fonctionne, lui, via _jpeg_q.
    if "jpeg" in img_fmt and args.formats_image == "png":
        print(f"  Note: layer '{args.couche}' is served as JPEG; --image-format "
              f"png ignored (PNG would only bloat the file, no quality gain). "
              f"Keeping JPEG.")

    # ── Plafonnement zoom selon capacités réelles de la couche ───────────────
    # IGN : GetCapabilities WMTS. XYZ (naip…) : table _XYZ_ZOOM_LIMITS.
    # AVANT le bloc de découpage a-priori (qui `return`) : le capping vivait
    # après, donc les runs chunkés demandaient des zooms hors couche →
    # avalanche de 204 → chunks marqués « hors couverture » et sautés à tort
    # alors qu'ils avaient de la couverture aux zooms valides. Réécrit dans
    # args pour que _traiter_bbox_wmts hérite des bornes capées.
    zoom_min = min(args.zoom_min, args.zoom_max)
    zoom_max = max(args.zoom_min, args.zoom_max)
    _limites_reel = _lire_zoom_limites_wmts(
        layer, apikey_requis, apikey=getattr(args, "apikey", ""))
    if _limites_reel:
        _src_caps = "service" if layer.startswith("XYZ:") else "IGN"
        _zmin_reel, _zmax_reel = _limites_reel
        if zoom_max > _zmax_reel:
            print(f"  ⚠ Layer {args.couche}: {_src_caps} max zoom = {_zmax_reel}, "
                  f"zoom_max lowered from {zoom_max} to {_zmax_reel}.")
            zoom_max = _zmax_reel
            zoom_min = min(zoom_min, zoom_max)
        if zoom_min < _zmin_reel:
            print(f"  ⚠ Layer {args.couche}: {_src_caps} min zoom = {_zmin_reel}, "
                  f"zoom_min raised from {zoom_min} to {_zmin_reel}.")
            zoom_min = _zmin_reel
            zoom_max = max(zoom_max, zoom_min)
    args.zoom_min, args.zoom_max = zoom_min, zoom_max

    return layer, style, img_fmt, apikey_requis, fmt_ext, zoom_min, zoom_max


def main_wmts():
    t_debut = time.time()
    parser = _construire_parser_wmts()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if not args.source and not _zone_cli_presente(args):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )
    _valider_zooms(args, parser)
    _appliquer_cache_dir(args)   # avant le cache WMTS ign_raster
    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    args.transparent_raster = "transparent-raster" in _ff

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    _historique_debut()

    _traiter_source_wmts(args)

    # ── Normalisation des sorties ────────────────────────────────────────────
    # Si aucune sortie explicite → MBTiles par défaut
    if not args.mbtiles and not args.rmap and not args.sqlitedb:
        args.mbtiles = True

    layer, style, img_fmt, apikey_requis, fmt_ext, zoom_min, zoom_max = (
        _resoudre_couche_wmts(args))

    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    # ── A-priori splitting: traitement séquentiel morceau par morceau ────────
    _cols_pr  = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr  = getattr(args, "rows_decoupe", 0) or 0
    _cote_pr  = getattr(args, "split_width", 0.0) or 0.0
    if (_cols_pr > 0 and _rows_pr > 0) or _cote_pr > 0:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            lon_min, lat_min, lon_max, lat_max,
            0, _cote_pr, unite_m=False, n_cols=_cols_pr, n_rows=_rows_pr)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / "raster")
            # Overwrite explicite perce la reprise (cf. jumeau LiDAR). Pas de
            # ombrages_ecraser ici : le WMTS n'a pas d'étape shadings.
            _overwrite_actif = (args.tuiles_ecraser or args.telechargement_ecraser)
            def _entete_wmts(c):
                lon_w, lat_s, lon_e, lat_n = c
                surface = ((lon_e-lon_w)*111*math.cos(math.radians((lat_s+lat_n)/2))) * \
                          ((lat_n-lat_s)*111)
                return (f"BBox WGS84 : {lon_w:.4f},{lat_s:.4f} → "
                        f"{lon_e:.4f},{lat_n:.4f}  (~{surface:.0f} km²)")
            def _chunk_wmts(coords, nom_z, cle, manifeste):
                return _traiter_bbox_wmts(
                    args, coords, nom_z, nom_zone, layer, style,
                    img_fmt, fmt_ext, apikey_requis, manifeste, cle)
            _executer_split_historise(
                lambda: _run_split_priori(
                    args, sous_zones, mode_desc, nom_zone, racine_pr,
                    _overwrite_actif, _entete_wmts, _chunk_wmts, t_debut,
                    vide_sans_couverture_ok=False),
                t_debut, racine_pr)
            return
        print("  A-priori splitting: zone too small -> single pass")

    # R2#38 : --min-free-gb garde aussi le mode MONOLITHIQUE WMTS (jumeau du
    # garde LiDAR) : sans split, _run_split_priori / _garde_disque ne tournent
    # pas → seuil ignoré en silence. Vérif avant de démarrer le tuilage.
    _garde_disque(Path(args.dossier).resolve() if args.dossier else DOSSIER_TRAVAIL,
                  getattr(args, "min_free_gb", 0.0) or 0.0, "single-pass", 0, 1)

    # ── Calcul de la grille ───────────────────────────────────────────────────
    # (zooms déjà normalisés ET capés plus haut, avant le bloc split)
    zoom_min = args.zoom_min
    zoom_max = args.zoom_max

    tuiles = calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max,
                                 zoom_min, zoom_max)
    total  = compter_tuiles_xyz(lat_min, lon_min, lat_max, lon_max,
                                zoom_min, zoom_max)
    taille_est = estimer_taille(total, fmt_ext)

    # Couches XYZ (USGS Imagery…) : source non-IGN → libellé neutre + vrai template.
    _src = layer[4:] if layer.startswith("XYZ:") else layer
    _lbl = "Raster map" if layer.startswith("XYZ:") else "IGN map"
    print("=" * 55)
    print(f"  {_lbl} - {args.couche} ({_src})")
    print("=" * 55)
    print(f"  Zone    : {nom_zone}")
    print(f"  BBox    : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")
    print(f"  Zooms   : {zoom_min}–{zoom_max}")
    print(f"  Tiles: {total:,}  (~{taille_est} MB estimated)")
    print(f"  Workers : {args.workers}")

    # ── Dossier de sortie ─────────────────────────────────────────────────────
    racine  = Path(args.dossier).resolve() if args.dossier \
              else DOSSIER_TRAVAIL / "Projets" / nom_zone / "raster"
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    # Cache tuiles : cache/ign_raster/<z>/<x>/<y>.<ext>. Le dossier de SORTIE est
    # provider-neutre (raster/), mais le cache garde le nom legacy "ign_raster"
    # pour ne pas orpheliner les tuiles WMTS déjà téléchargées des users FR.
    # naip (US) et IGN (FR) y cohabitent sans collision (x/y disjoints).
    dossier_cache = DOSSIER_CACHE / "ign_raster"
    dossier_cache.mkdir(parents=True, exist_ok=True)
    print(f"  Tiles cache: {dossier_cache}")

    # ── Génération MBTiles ────────────────────────────────────────────────────
    # _jpeg_q : quand non-None, déclenche un re-encodage PNG → JPEG côté
    # client dans generer_mbtiles_wmts. Sémantique :
    #   - JPEG natif (ortho, scan*, etc.) : _jpeg_q = None (déjà JPEG)
    #   - PNG natif + --formats-image png  : _jpeg_q = None (l'utilisateur
    #     refuse explicitement la conversion → on garde le PNG natif)
    #   - PNG natif + --formats-image jpeg/auto : _jpeg_q = qualité demandée
    #     → conversion PNG → JPEG (gain ~3-5× sur la taille MBTiles)
    # Source de vérité UNIQUE partagée avec le split _traiter_bbox_wmts (R2#14).
    _jpeg_q = _jpeg_quality_sortie(img_fmt, args.formats_image, args.qualite_image)

    # Nom encodant la qualité (R2#18) : même helper que le split, pour que
    # changer --image-quality/--image-format régénère au lieu de réutiliser un
    # MBTiles obsolète de même nom.
    nom_fichier = _nom_mbtiles_wmts(nom_zone, args.couche, zoom_min, zoom_max, _jpeg_q)
    chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"

    # Le MBTiles source doit être (re)généré si :
    #   - il n'existe pas encore
    #   - OU écraser est demandé explicitement
    # Dans tous les autres cas (fichier existant, pas d'écraser) on l'utilise tel quel
    # pour la conversion / le découpage.
    _ecraser   = args.tuiles_ecraser
    _mbtiles_requis = _mbtiles_a_regenerer(chemin_mbtiles, _ecraser)

    if not _mbtiles_requis and chemin_mbtiles.exists():
        print(f"  Existing MBTiles: {chemin_mbtiles.name}, direct split/conversion")

    if _mbtiles_requis:
        # ── Génération d'un seul MBTiles complet ──────────────────────────────
        # Le découpage éventuel est délégué à _convertir_formats via decouper_mbtiles
        generer_mbtiles_wmts(
            chemin        = chemin_mbtiles,
            tuiles_iter   = tuiles,
            total         = total,
            nom_zone      = nom_zone,
            fmt_ext       = fmt_ext,
            zoom_min      = zoom_min,
            zoom_max      = zoom_max,
            layer         = layer,
            style         = style,
            img_fmt       = img_fmt,
            apikey        = args.apikey,
            apikey_requis = apikey_requis,
            workers       = args.workers,
            bbox_wgs84    = (lon_min, lat_min, lon_max, lat_max),
            jpeg_quality   = _jpeg_q,
            dossier_cache  = dossier_cache,
            ecraser_tuiles = args.tuiles_ecraser,
            ecraser_dalles = args.telechargement_ecraser,
        )

    # ── Découpage + RMAP + SQLiteDB ───────────────────────────────────────────
    _livrables_raster_ok = False
    if chemin_mbtiles.exists():
        _livrables_raster_ok = bool(_convertir_formats(
            chemin_mbtiles, args, mbtiles_neuf=_mbtiles_requis))
    else:
        print(f"  ERROR: expected MBTiles not produced: {chemin_mbtiles.name}")

    # ── Résumé ────────────────────────────────────────────────────────────────
    # Planche d'assemblage : balaie les livrables du dossier (best-effort).
    _planche_depuis_dossier(dossier, args, nom_zone,
                            zone_bbox_wgs84=(lon_min, lat_min, lon_max, lat_max))
    elapsed = int(time.time() - t_debut)
    print(f"\n  Done in {_hms(elapsed)}")
    print(f"  Done! Folder: {dossier}")
    _historique_depuis_argv(
        elapsed, str(dossier),
        statut=("ok" if _livrables_raster_ok else "ko"))
    if not _livrables_raster_ok:
        raise RuntimeError(
            "raster generation/conversion incomplete - partial outputs kept; "
            "rerun to retry failed deliverables")


# ============================================================
# PIPELINE WFS IGN — VECTEUR (GeoJSON)
# ============================================================

# (typename WFS, label FR [GUI + logs runtime], label EN [--help CLI])
COUCHES_WFS = {
    # ── Cadastre ──────────────────────────────────────────────────────────────
    "cadastre":        ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle",
                        "Parcelles cadastrales (PCI)",
                        "Cadastral parcels (PCI)"),
    # ── Hydrographie ──────────────────────────────────────────────────────────
    "cours_eau":       ("BDTOPO_V3:cours_d_eau",
                        "Cours d'eau BD TOPO V3",
                        "Watercourses BD TOPO V3"),
    "troncons_eau":    ("BDTOPO_V3:troncon_hydrographique",
                        "Tronçons hydrographiques BD TOPO V3",
                        "Hydrographic segments BD TOPO V3"),
    "plans_eau":       ("BDTOPO_V3:plan_d_eau",
                        "Plans d'eau BD TOPO V3",
                        "Water bodies BD TOPO V3"),
    "detail_hydro":    ("BDTOPO_V3:detail_hydrographique",
                        "Détails hydrographiques (sources, cascades…)",
                        "Hydrographic details (springs, waterfalls…)"),
    # ── Bâti / structures ─────────────────────────────────────────────────────
    "batiments":       ("BDTOPO_V3:batiment",
                        "Bâtiments BD TOPO V3",
                        "Buildings BD TOPO V3"),
    "constructions":   ("BDTOPO_V3:construction_surfacique",
                        "Constructions surfaciques (murets, terrasses, enclos)",
                        "Surface constructions (low walls, terraces, enclosures)"),
    "cimetieres":      ("BDTOPO_V3:cimetiere",
                        "Cimetières",
                        "Cemeteries"),
    # ── Transport ─────────────────────────────────────────────────────────────
    "routes":          ("BDTOPO_V3:troncon_de_route",
                        "Tronçons de routes BD TOPO V3",
                        "Road segments BD TOPO V3"),
    "chemins":         ("BDTOPO_V3:itineraire_autre",
                        "Chemins et itinéraires anciens",
                        "Tracks and old routes"),
    # ── Relief / orographie ───────────────────────────────────────────────────
    "lignes_orog":     ("BDTOPO_V3:ligne_orographique",
                        "Lignes orographiques (talwegs, crêtes)",
                        "Orographic lines (talwegs, ridges)"),
    "detail_orog":     ("BDTOPO_V3:detail_orographique",
                        "Détails orographiques (rochers, grottes)",
                        "Orographic details (rocks, caves)"),
    # ── Végétation / milieu ───────────────────────────────────────────────────
    "forets":          ("BDTOPO_V3:foret_publique",
                        "Forêts publiques",
                        "Public forests"),
    "reserves":        ("BDTOPO_V3:parc_ou_reserve",
                        "Parcs et réserves naturelles",
                        "Parks and nature reserves"),
    # ── Toponymie / lieux ─────────────────────────────────────────────────────
    "lieux_dits":      ("BDTOPO_V3:lieu_dit_non_habite",
                        "Lieux-dits non habités (toponymie historique)",
                        "Uninhabited place names (historical toponymy)"),
    # ── Admin ─────────────────────────────────────────────────────────────────
    "communes":        ("BDTOPO_V3:commune",
                        "Limites communales",
                        "Municipal boundaries"),
    # ── Agriculture ───────────────────────────────────────────────────────────
    "rpg":             ("RPG.LATEST:parcelles_graphiques",
                        "Registre Parcellaire Graphique (cultures)",
                        "Graphic Parcel Register (RPG, crops)"),
}

WFS_PAGE = 1000   # features par requête (limite serveur IGN — WFS_URL défini ligne ~1274)


from _wfs_pipeline import (
    DependancesWfs as _DependancesWfs,
    telecharger_wfs as _telecharger_wfs_impl,
)


def _dependances_wfs():
    return _DependancesWfs(
        wfs_url=WFS_URL,
        http_ua=_HTTP_UA,
        page_size=WFS_PAGE,
        chemin_part=_chemin_part,
        stop_event=_stop_event,
        gunzip_vers_fichier=_gunzip_vers_fichier,
        gzip_depuis_fichier=_gzip_depuis_fichier,
        log_req=_log_req,
        formater_duree=_hms,
    )


def telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                    nom_zone, dossier_sortie, ecraser_telechargement=False,
                    formats=None):
    return _telecharger_wfs_impl(
        typename,
        lon_min,
        lat_min,
        lon_max,
        lat_max,
        nom_zone,
        dossier_sortie,
        ecraser_telechargement=ecraser_telechargement,
        formats=formats,
        dependances=_dependances_wfs(),
    )


telecharger_wfs.__doc__ = _telecharger_wfs_impl.__doc__


# ============================================================
# CONVERSION GEOJSON IGN → OSM XML → MAPSFORGE .map
# ============================================================

from _geojson_geometry import (
    _IGN_LAYER_TAGS,
    _IGN_SIMPLIFY_EPSILON,
    _OVERLAY_DEFAUT,
    _OVERLAY_STYLE,
    _OVERLAY_TILE_WARN,
    _clip_polygone_rect,
    _douglas_peucker,
    _epsilon_depuis_surface_km2,
    _overlay_sequences,
    _overlay_style_key,
    _seg_inter_box,
    _tags_pour_layer,
)


from _geojson_raster import (
    _DependancesRasterGeojson,
    rasteriser_geojson_transparent as _rasteriser_geojson_transparent_impl,
)


def _dependances_geojson_raster():
    return _DependancesRasterGeojson(
        chemin_part=_chemin_part,
        nettoyer_sqlite_part=_nettoyer_sqlite_part,
        valider_sqlite_part=_valider_sqlite_part,
        stop_event=_stop_event,
        deg_to_tile=deg_to_tile,
        overlay_style=_OVERLAY_STYLE,
        overlay_defaut=_OVERLAY_DEFAUT,
        overlay_tile_warn=_OVERLAY_TILE_WARN,
        overlay_style_key=_overlay_style_key,
        overlay_sequences=_overlay_sequences,
        clip_polygone_rect=_clip_polygone_rect,
        seg_inter_box=_seg_inter_box,
    )


def rasteriser_geojson_transparent(
    geojson_path,
    sqlitedb_out,
    zoom_min,
    zoom_max,
    ecraser=False,
    supersample=2,
    bbox_wgs84=None,
):
    return _rasteriser_geojson_transparent_impl(
        geojson_path,
        sqlitedb_out,
        zoom_min,
        zoom_max,
        ecraser=ecraser,
        supersample=supersample,
        bbox_wgs84=bbox_wgs84,
        dependances=_dependances_geojson_raster(),
    )

from _geojson_osm_xml import (
    _DependancesGeojsonOsmXml,
    geojson_ign_vers_osm_xml as _geojson_ign_vers_osm_xml_impl,
)


def _dependances_geojson_osm_xml():
    return _DependancesGeojsonOsmXml(
        chemin_part=_chemin_part,
        stop_event=_stop_event,
        layer_tags=_IGN_LAYER_TAGS,
        tags_pour_layer=_tags_pour_layer,
        douglas_peucker=_douglas_peucker,
        epsilon_defaut=_IGN_SIMPLIFY_EPSILON,
    )


def geojson_ign_vers_osm_xml(geojson_path, osm_xml_path, epsilon=None):
    return _geojson_ign_vers_osm_xml_impl(
        geojson_path,
        osm_xml_path,
        epsilon=epsilon,
        dependances=_dependances_geojson_osm_xml(),
    )

from _geojson_mapsforge import (
    _DependancesGeojsonMapsforge,
    generer_map_depuis_geojson_ign as _generer_map_depuis_geojson_ign_impl,
)


def _dependances_geojson_mapsforge():
    return _DependancesGeojsonMapsforge(
        convertir_geojson_osm_xml=geojson_ign_vers_osm_xml,
        preparer_osmosis=_preparer_osmosis,
        run_osmosis_streaming=_run_osmosis_streaming,
        chemin_part=_chemin_part,
        hash_config=_hash_config,
        sig_sidecar_stale=_sig_sidecar_stale,
        sig_sidecar_ecrire=_sig_sidecar_ecrire,
        java_opts_extra=_java_opts_extra,
        log_req=_log_req,
        formater_duree=_hms,
        windows=WINDOWS,
    )


def generer_map_depuis_geojson_ign(
    geojson_src,
    dossier_ville,
    nom_zone,
    bbox_wgs84,
    ecraser=False,
    epsilon=None,
):
    return _generer_map_depuis_geojson_ign_impl(
        geojson_src,
        dossier_ville,
        nom_zone,
        bbox_wgs84,
        ecraser=ecraser,
        epsilon=epsilon,
        dependances=_dependances_geojson_mapsforge(),
    )

# ============================================================
# TÉLÉCHARGEMENT BULK BD TOPO IGN (département entier)
# ============================================================
# Pour --zone-departement : l'API IGN fournit un GPKG complet par département
# (~1-2 Go, 1 seule requête HTTP). Beaucoup plus rapide que la pagination WFS
# (415 requêtes pour le Var).
# Pipeline : API discovery → GPKG streamé (cache) → ogr2ogr par couche → GeoJSON.gz
# ──────────────────────────────────────────────────────────────────────────────

BDTOPO_API_URL    = "https://data.geopf.fr/telechargement/resource/BDTOPO"
BDTOPO_DL_BASE    = "https://data.geopf.fr/telechargement/download/BDTOPO"

# Nom de couche GPKG = suffix typename WFS (minuscules, identique)
_BDTOPO_GPKG_LAYER = {
    "cours_d_eau":             "cours_d_eau",
    "troncon_hydrographique":  "troncon_hydrographique",
    "plan_d_eau":              "plan_d_eau",
    "detail_hydrographique":   "detail_hydrographique",
    "batiment":                "batiment",
    "construction_surfacique": "construction_surfacique",
    "cimetiere":               "cimetiere",
    "troncon_de_route":        "troncon_de_route",
    "itineraire_autre":        "itineraire_autre",
    "ligne_orographique":      "ligne_orographique",
    "detail_orographique":     "detail_orographique",
    "foret_publique":          "foret_publique",
    "parc_ou_reserve":         "parc_ou_reserve",
    "lieu_dit_non_habite":     "lieu_dit_non_habite",
    "commune":                 "commune",
}


from _bdtopo_bulk import (
    DependancesBdtopo as _DependancesBdtopo,
    DependancesOrchestrationBdtopo as _DependancesOrchestrationBdtopo,
    decouvrir_url_bdtopo_gpkg as _decouvrir_url_bdtopo_gpkg_impl,
    telecharger_bdtopo_bulk as _telecharger_bdtopo_bulk_impl,
    telecharger_bdtopo_gpkg as _telecharger_bdtopo_gpkg_impl,
)


def _dependances_bdtopo_bulk():
    return _DependancesBdtopo(
        api_url=BDTOPO_API_URL,
        download_base=BDTOPO_DL_BASE,
        http_ua=_HTTP_UA,
        cache_root=DOSSIER_CACHE,
        log_req=_log_req,
        chemin_part=_chemin_part,
        ouvrir_url=_urlopen,
        stop_event=_stop_event,
        formater_duree=_hms,
    )


def _decouvrir_url_bdtopo_gpkg(num_dep):
    return _decouvrir_url_bdtopo_gpkg_impl(
        num_dep, dependances=_dependances_bdtopo_bulk()
    )


_decouvrir_url_bdtopo_gpkg.__doc__ = _decouvrir_url_bdtopo_gpkg_impl.__doc__


def _telecharger_bdtopo_gpkg(num_dep, url, nom_ressource, ecraser=False):
    return _telecharger_bdtopo_gpkg_impl(
        num_dep,
        url,
        nom_ressource,
        ecraser=ecraser,
        dependances=_dependances_bdtopo_bulk(),
    )


_telecharger_bdtopo_gpkg.__doc__ = _telecharger_bdtopo_gpkg_impl.__doc__


from _bdtopo_layers import (
    DependancesCouchesBdtopo as _DependancesCouchesBdtopo,
    extraire_couche_bdtopo as _extraire_couche_bdtopo_impl,
    streamer_geojson_ajout_source as _streamer_geojson_ajout_source_impl,
)


def _streamer_geojson_ajout_source(src_geojson, dst_gz, source_name):
    return _streamer_geojson_ajout_source_impl(
        src_geojson,
        dst_gz,
        source_name,
        chemin_part=_chemin_part,
    )


_streamer_geojson_ajout_source.__doc__ = (
    _streamer_geojson_ajout_source_impl.__doc__
)


def _dependances_couches_bdtopo():
    return _DependancesCouchesBdtopo(
        chemin_part=_chemin_part,
        gunzip_vers_fichier=_gunzip_vers_fichier,
        gzip_depuis_fichier=_gzip_depuis_fichier,
        get_transformer=_get_transformer,
        streamer_geojson=_streamer_geojson_ajout_source,
        formater_duree=_hms,
    )


def _extraire_couche_bdtopo(gpkg_path, layer_name, sortie_gz,
                             bbox_l93=None, ecraser=False, formats=None):
    return _extraire_couche_bdtopo_impl(
        gpkg_path,
        layer_name,
        sortie_gz,
        bbox_l93=bbox_l93,
        ecraser=ecraser,
        formats=formats,
        dependances=_dependances_couches_bdtopo(),
    )


_extraire_couche_bdtopo.__doc__ = _extraire_couche_bdtopo_impl.__doc__


def _telecharger_bdtopo_bulk(num_dep, couches_resolues, nom_zone,
                              dossier_sortie, bbox_l93=None, ecraser=False,
                              formats=None):
    dependances = _DependancesOrchestrationBdtopo(
        decouvrir_ressource=_decouvrir_url_bdtopo_gpkg,
        telecharger_gpkg=_telecharger_bdtopo_gpkg,
        extraire_couche=_extraire_couche_bdtopo,
        correspondance_couches=_BDTOPO_GPKG_LAYER,
    )
    return _telecharger_bdtopo_bulk_impl(
        num_dep,
        couches_resolues,
        nom_zone,
        dossier_sortie,
        bbox_l93=bbox_l93,
        ecraser=ecraser,
        formats=formats,
        dependances=dependances,
    )


_telecharger_bdtopo_bulk.__doc__ = _telecharger_bdtopo_bulk_impl.__doc__


from _vector_acquisition import (
    DependancesAcquisitionVecteur as _DependancesAcquisitionVecteur,
    acquerir_couches_vecteur as _acquerir_couches_vecteur_impl,
)


def _dependances_acquisition_vecteur():
    return _DependancesAcquisitionVecteur(
        telecharger_bulk=_telecharger_bdtopo_bulk,
        telecharger_wfs=telecharger_wfs,
        executor_factory=ThreadPoolExecutor,
    )


def _acquerir_couches_vecteur(couches_resolues, bbox_wgs84, nom_zone, dossier,
                               *, num_dep=None, ecraser=False, formats=None,
                               workers=1):
    return _acquerir_couches_vecteur_impl(
        couches_resolues,
        bbox_wgs84,
        nom_zone,
        dossier,
        num_dep=num_dep,
        ecraser=ecraser,
        formats=formats,
        workers=workers,
        dependances=_dependances_acquisition_vecteur(),
    )


_acquerir_couches_vecteur.__doc__ = _acquerir_couches_vecteur_impl.__doc__


from _vector_outputs import (
    DependancesSortiesVecteur as _DependancesSortiesVecteur,
    produire_sorties_vecteur as _produire_sorties_vecteur_impl,
)


def _produire_sorties_vecteur(sorties, dossier, nom_zone, bbox_wgs84, *,
                              formats=None, ecraser=False,
                              simplification=None, zoom_min=8, zoom_max=18):
    dependances = _DependancesSortiesVecteur(
        fusionner_geojson=_fusionner_geojson_compat,
        epsilon_depuis_surface_km2=_epsilon_depuis_surface_km2,
        generer_map=generer_map_depuis_geojson_ign,
        rasteriser=rasteriser_geojson_transparent,
    )
    return _produire_sorties_vecteur_impl(
        sorties,
        dossier,
        nom_zone,
        bbox_wgs84,
        formats=formats,
        ecraser=ecraser,
        simplification=simplification,
        zoom_min=zoom_min,
        zoom_max=zoom_max,
        dependances=dependances,
    )


_produire_sorties_vecteur.__doc__ = _produire_sorties_vecteur_impl.__doc__


def main_wfs():
    """Point d'entrée mode --ignvecteur."""
    import argparse

    t_debut = time.time()

    parser = argparse.ArgumentParser(
        prog="lidar2map.py --vector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            ["Available layers:"] +
            [f"  {k:<16} {v[2]}" for k, v in COUCHES_WFS.items()] +
            ["",
             "Examples:",
             "  python lidar2map.py --vector --zone-city gareoult --zone-width 10",
             "  python lidar2map.py --vector --layer batiments routes --zone-city gareoult",
             "  python lidar2map.py --vector --layer cadastre --zone-department 83",
            ]
        )
    )
    parser.add_argument("--version", action="version",
                        version=f"lidar2map {VERSION} ({VERSION_DATE}), multi-provider")
    parser.add_argument("--vector", "--ignvecteur", action="store_true", dest="ignvecteur")
    parser.add_argument("--layer", "--couche", metavar="NAME", nargs="+", default=["cadastre"], dest="couche",
                        help="WFS layer(s) to download (default: cadastre). "
                             "Short alias or full typename. "
                             "Multiple layers separated by spaces.")

    # Zone — même logique que --ignraster
    _ajouter_args_zone(
        parser,
        width_default=20.0,
        bbox_metavar="W,S,E,N",
    )
    parser.add_argument("--output-dir", "--dossier",     metavar="PATH", default=None, dest="dossier",
                        help="Output folder (default: ./ign_vecteur/)")
    parser.add_argument("--workers",  type=_arg_int_positif, default=4, metavar="N",
                        help="Parallel WFS connections (default: 4)")
    parser.add_argument("--download-overwrite", "--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Overwrite existing GeoJSON (force re-download)")
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["geojson","gz","map","transparent-raster"],
                        default=["gz"], metavar="FMT",
                        help="Output formats: geojson gz map transparent-raster (default: gz). "
                             "map generates a Mapsforge map via osmosis ; transparent-raster "
                             "rasterizes the vector into transparent PNG tiles (.sqlitedb) "
                             "for OsmAnd overlay over the LiDAR.")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Overwrite existing .map")
    parser.add_argument("--vector-simplify", "--simplification-vecteur", type=_arg_float_non_negatif, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Douglas-Peucker simplification epsilon in metres. "
                             "Without it, computed automatically from the area "
                             "(<200 km²→3 m, <1000→8 m, <15000→15 m, <100000→25 m, else→40 m).")
    args = parser.parse_args()
    if not _zone_cli_presente(args):
        parser.error(
            "one geographic area is required: --zone-city, --zone-gps, "
            "--zone-bbox, --zone-department, or --zone-region"
        )
    _appliquer_cache_dir(args)   # avant le cache bdtopo/discover
    _ff = getattr(args, "formats_fichier", ["gz"])
    # Formats GeoJSON à produire (filtre "map" qui est traité plus loin)
    _gj_formats = [f for f in _ff if f in ("gz", "geojson")] or ["gz"]

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    _historique_debut()

    # ── Résolution des couches ────────────────────────────────────────────────
    couches_resolues = []
    for c in args.couche:
        if c in COUCHES_WFS:
            # (typename, label FR) — desc runtime/logs en FR ; [2]=EN réservé au --help
            couches_resolues.append((COUCHES_WFS[c][0], COUCHES_WFS[c][1]))
        else:
            # typename complet passé directement
            couches_resolues.append((c, c))

    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    racine  = (Path(args.dossier).resolve() if args.dossier
               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_vecteur")
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    # ── Résumé ────────────────────────────────────────────────────────────────
    print("=" * 56)
    print("  Vecteur IGN WFS → GeoJSON")
    print("=" * 56)
    print(f"  Zone     : {nom_zone}")
    print(f"  BBox     : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")
    print(f"  Layer(s): {', '.join(c[1] for c in couches_resolues)}")
    print(f"  Output   : {dossier}")

    # ── Téléchargement ────────────────────────────────────────────────────────
    sorties = _acquerir_couches_vecteur(
        couches_resolues,
        (lon_min, lat_min, lon_max, lat_max),
        nom_zone,
        dossier,
        num_dep=getattr(args, "zone_departement", None),
        ecraser=args.telechargement_ecraser,
        formats=_gj_formats,
        workers=args.workers,
    )

    # Fusion et livrables derives demandes.
    _resultat_vecteur = _produire_sorties_vecteur(
        sorties,
        dossier,
        nom_zone,
        (lon_min, lat_min, lon_max, lat_max),
        formats=getattr(args, "formats_fichier", ["gz"]),
        ecraser=args.tuiles_ecraser,
        simplification=getattr(args, "simplification_vecteur", None),
        zoom_min=getattr(args, "zoom_min", 8),
        zoom_max=getattr(args, "zoom_max", 18),
    )
    _livrables_ok = _resultat_vecteur.complet

    # Bilan
    # Planche d'assemblage : balaie les livrables du dossier (best-effort).
    _planche_depuis_dossier(dossier, args, nom_zone,
                            zone_bbox_wgs84=(lon_min, lat_min, lon_max, lat_max))
    elapsed = int(time.time() - t_debut)
    print(f"\n  Done in {_hms(elapsed)}: {len(sorties)}/{len(couches_resolues)} layers")
    print(f"  Done! Folder: {dossier}")
    for s in sorties:
        print(f"  → {s}")
    # Échec partiel (couches manquantes) = échec visible : les livrables
    # produits restent, mais GUI/scripts/CI doivent le voir. On finalise
    # l'historique avec le statut RÉEL (ko si partiel) AVANT de lever, sinon
    # l'entrée resterait marquée 'ok' pour un run incomplet (R2#50).
    _wfs_partiel = len(sorties) < len(couches_resolues)
    _traitement_ko = _wfs_partiel or not _livrables_ok
    _historique_depuis_argv(elapsed, str(dossier),
                            statut=("ko" if _traitement_ko else "ok"))
    # RuntimeError et PAS sys.exit(1) : SystemExit traverserait la boucle
    # multi-départements (qui ne rattrape que Exception, exprès) et tuerait les
    # départements suivants ; l'Exception y est rattrapée → dept marqué KO, on
    # continue, et le code global non-zéro vient du bilan _deps_ko. En
    # mono-département elle remonte au top-level → code non-zéro aussi.
    if _wfs_partiel:
        raise RuntimeError(f"{len(couches_resolues) - len(sorties)} WFS "
                           f"layer(s) failed - rerun to retry them")
    if not _livrables_ok:
        raise RuntimeError("Requested vector deliverable generation failed")


# ============================================================
# EXPORT GEOJSON DEPUIS PBF OSM (ogr2ogr)
# ============================================================

from _geojson_osm_export import (
    DependancesExportOsm as _DependancesExportOsm,
    generer_geojson_osm as _generer_geojson_osm_impl,
)


def _dependances_export_osm():
    return _DependancesExportOsm(
        osm_filtre_cles=_osm_filtre_cles,
        osm_cle_match=_osm_cle_match,
        chemin_part=_chemin_part,
        gunzip_vers_fichier=_gunzip_vers_fichier,
        publier_groupe_atomique=_publier_groupe_atomique,
        formater_duree=_hms,
    )


def generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                        osm_tags=None, ecraser_tuiles=False, formats=None):
    return _generer_geojson_osm_impl(
        bbox_wgs84,
        dossier_ville,
        nom_zone,
        osm_pbf,
        osm_tags=osm_tags,
        ecraser_tuiles=ecraser_tuiles,
        formats=formats,
        dependances=_dependances_export_osm(),
    )


generer_geojson_osm.__doc__ = _generer_geojson_osm_impl.__doc__


# ============================================================
# PIPELINE FUSION GEOJSON
# ============================================================

from _geojson_merge import (
    DependancesFusionGeojson as _DependancesFusionGeojson,
    fusionner_geojson as _fusionner_geojson_impl,
    lire_geojson as _lire_geojson_impl,
)


def _lire_geojson(chemin):
    """Lit un .geojson ou .geojson.gz — retourne le dict."""
    return _lire_geojson_impl(chemin)


_lire_geojson.__doc__ = _lire_geojson_impl.__doc__


def _dependances_fusion_geojson():
    return _DependancesFusionGeojson(
        chemin_part=_chemin_part,
        stop_event=_stop_event,
        lire_geojson=_lire_geojson,
    )


def fusionner_geojson(fichiers, sortie, fichiers_ignores=None):
    """Fusionne plusieurs GeoJSON en une FeatureCollection streamée."""
    return _fusionner_geojson_impl(
        fichiers,
        sortie,
        fichiers_ignores=fichiers_ignores,
        dependances=_dependances_fusion_geojson(),
    )


fusionner_geojson.__doc__ = _fusionner_geojson_impl.__doc__
def _fusionner_geojson_compat(fichiers, sortie):
    """Compat avec l'ancienne signature : retourne juste le Path (pas la bbox).

    Conservé pour les sites qui n'ont pas besoin de la bbox (ex.
    main_wfs/main_decouper). Préférer fusionner_geojson() directement quand
    on veut éviter une 2e passe pour calculer la bbox.
    """
    res = fusionner_geojson(fichiers, sortie)
    if res is None or res == (None, None):
        return None
    chemin, _bbox = res
    return chemin


from _geojson_merge_cli import (
    DependancesFusionCli as _DependancesFusionCli,
    determiner_sortie_fusion as _determiner_sortie_fusion,
    executer_fusion_cli as _executer_fusion_cli_impl,
    resoudre_sources_fusion as _resoudre_sources_fusion,
)


def _dependances_fusion_cli():
    return _DependancesFusionCli(
        fusionner_geojson=fusionner_geojson,
        epsilon_depuis_surface_km2=_epsilon_depuis_surface_km2,
        epsilon_defaut=_IGN_SIMPLIFY_EPSILON,
        generer_map=generer_map_depuis_geojson_ign,
        rasteriser=rasteriser_geojson_transparent,
    )


def _executer_fusion_cli(fichiers, sortie, *, formats, simplification=None,
                         zoom_min=8, zoom_max=18):
    return _executer_fusion_cli_impl(
        fichiers,
        sortie,
        formats=formats,
        simplification=simplification,
        zoom_min=zoom_min,
        zoom_max=zoom_max,
        dependances=_dependances_fusion_cli(),
    )


_executer_fusion_cli.__doc__ = _executer_fusion_cli_impl.__doc__


def main_fusionner():
    """Point d'entrée mode --fusionner."""
    import argparse

    t_debut = time.time()
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --merge",
        description="Merge several GeoJSON files into one.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py --merge \\
      --source cadastre.geojson cours_eau.geojson osm_gareoult.geojson \\
      --output-file gareoult_fusion.geojson

  python lidar2map.py --merge \\
      --source ign_vecteur/gareoult_*.geojson \\
      --output-file gareoult_complet.geojson
        """
    )
    parser.add_argument("--merge", "--fusionner", action="store_true", dest="fusionner")
    parser.add_argument("--source", nargs="+", metavar="FILE",
                        required=True,
                        help="GeoJSON files to merge (glob accepted)")
    parser.add_argument("--output-file", "--sortie", metavar="FILE", default=None, dest="sortie",
                        help="Output .geojson file")
    parser.add_argument("--output-dir", "--dossier", metavar="PATH", default=None, dest="dossier")
    parser.add_argument("--no-gz", action="store_true",
                        help="Uncompressed .geojson output (default: .geojson.gz)")
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", default=["gz"], dest="formats_fichier",
                        metavar="FMT", help="gz geojson map transparent-raster")
    parser.add_argument("--vector-simplify", "--simplification-vecteur", type=_arg_float_non_negatif, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Douglas-Peucker epsilon in metres (default: auto from area).")
    args, _extra = parser.parse_known_args()  # tolère d'éventuels tokens globaux
    # Signaler les options non reconnues (typos) au lieu de les avaler en
    # silence : `--outut-file x` était sinon ignoré et la sortie retombait sur
    # le nom par défaut sans prévenir (R2#37). On ne signale que les tokens en
    # `--…` (une valeur isolée peut être un reliquat légitime).
    _opts_inconnues = [t for t in _extra if t.startswith("--")]
    if _opts_inconnues:
        print("  WARNING: unrecognized option(s) ignored (typo?): "
              + " ".join(_opts_inconnues))
    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    _historique_debut()

    fichiers = _resoudre_sources_fusion(args.source)

    if not fichiers:
        print("  ERROR: no source file found")
        sys.exit(1)

    sortie = _determiner_sortie_fusion(
        fichiers,
        sortie=args.sortie,
        dossier=args.dossier,
        no_gz=args.no_gz,
    )

    print("=" * 52)
    print("  GeoJSON merge")
    print("=" * 52)
    for f in fichiers:
        print(f"  + {f}")
    print(f"  → {sortie}")

    resultat = _executer_fusion_cli(
        fichiers,
        sortie,
        formats=args.formats_fichier,
        simplification=args.simplification_vecteur,
        zoom_min=getattr(args, "zoom_min", 8),
        zoom_max=getattr(args, "zoom_max", 18),
    )
    if resultat.fusion_ok:
        if resultat.complet:
            print(f"\n  Done in {_hms(int(time.time()-t_debut))}")
    else:
        print("  ERROR: merge produced no output (no readable source feature)")
    # Fusion PARTIELLE (sources sautées) = échec visible : le livrable produit
    # reste, mais GUI/scripts/CI doivent le voir (famille succès silencieux, R2#37).
    if resultat.fichiers_ignores:
        print(f"\n  WARNING: {len(resultat.fichiers_ignores)} source(s) skipped "
              f"(missing/unreadable): "
              + ", ".join(resultat.fichiers_ignores))
    _historique_depuis_argv(
        int(time.time() - t_debut),
        dossier_resultat=str(sortie.parent),
        statut=("ok" if resultat.complet else "ko"),
    )
    if not resultat.complet:
        sys.exit(1)


# ── Persistence d'historique 'crash-safe' ──────────────────────────────────
# Sauver l'entrée AU DÉBUT du run garantit qu'elle existe même si le process
# crashe (NameError, SIGKILL, panne courant, Ctrl+C brutal). À la fin, on
# UPDATE cette entrée pour ajouter durée + statut. Identifiant : run_id
# (timestamp ms + pid, hérité via env LIDAR2MAP_HIST_RUN_ID en mode GUI).
_HIST_RUN_ID    = ""
_HIST_T_DEBUT   = 0.0
_HIST_FINALIZED = False


def _hist_disabled() -> bool:
    """Historique réservé aux runs pilotés par le GUI.

    Le GUI pose LIDAR2MAP_HIST_RUN_ID dans l'env du subprocess CLI qu'il
    spawne ; son absence = run CLI pur → on n'écrit RIEN. Une entrée CLI
    n'apportait rien : ses params reconstruits d'argv ne couvrent qu'un mode
    (~la moitié des clés du formulaire) et polluaient le préremplissage du
    GUI au démarrage. Également désactivé pendant le smoketest
    (LIDAR2MAP_SKIP_HIST : pollue de 5+ entrées par run)."""
    if os.environ.get("LIDAR2MAP_SKIP_HIST"):
        return True
    return not os.environ.get("LIDAR2MAP_HIST_RUN_ID")


def _cfg_depuis_argv() -> dict:
    """Construit le cfg JSON depuis sys.argv. Clés attendues par loadConfig() JS."""
    argv = sys.argv[1:]

    # Helpers variadiques : acceptent plusieurs orthographes du même flag
    # (anglais canonique + alias français) et prennent la 1re présente dans argv.
    def _arg(*flags, default=""):
        for flag in flags:
            try: return argv[argv.index(flag) + 1]
            except (ValueError, IndexError): continue
        return default

    def _arg_int(*flags, default=0):
        v = _arg(*flags, default="")
        try: return int(v) if v else default
        except ValueError: return default

    def _arg_float(*flags, default=0.0):
        v = _arg(*flags, default="")
        try: return float(v) if v else default
        except ValueError: return default

    def _flag(*flags): return any(f in argv for f in flags)

    def _args_after(*flags):
        """Retourne tous les args après le 1er flag présent jusqu'au prochain -- ou fin."""
        for flag in flags:
            try:
                i = argv.index(flag) + 1
            except ValueError:
                continue
            result = []
            while i < len(argv) and not argv[i].startswith("--"):
                result.append(argv[i])
                i += 1
            return result
        return []

    t = ("lidar"   if _flag("--lidar", "--ignlidar")   else
         "scan"    if _flag("--raster", "--ignraster")  else
         "vecteur" if _flag("--vector", "--ignvecteur") else
         "osm"     if _flag("--osm")        else
         "fusion"  if _flag("--merge", "--fusionner")  else
         "decoupe" if _flag("--split", "--decouper")   else "lidar")

    mode = ("region" if _flag("--zone-region")      else
            "dep"  if _flag("--zone-department", "--zone-departement") else
            "gps"  if _flag("--zone-gps")         else
            "bbox" if _flag("--zone-bbox")         else "ville")

    fmts = _args_after("--file-formats", "--formats-fichier")
    ombs = _args_after("--shadings", "--ombrages")
    _source_cli = _arg("--source")
    _maintenance_cli = _flag(
        "--tiles-purge-invalid", "--dalles-purger-invalides",
        "--tiles-purge-out-of-zone", "--dalles-purger-hors-zone",
        "--shadings-compress", "--ombrages-compresser",
    )
    _produit_cli = bool(
        ombs or fmts or _flag("--shading", "--shading-preset")
    )
    _lidar_standard = (
        t == "lidar" and not _source_cli
        and not (_maintenance_cli and not _produit_cli)
    )
    if (_lidar_standard and not ombs
            and not _flag("--shading", "--shading-preset")):
        ombs = ["lrm"]
    if (_lidar_standard and not fmts
            and (ombs and not any(v in ombs for v in ("aucun", "none"))
                 or _flag("--shading", "--shading-preset"))):
        fmts = ["mbtiles"]

    return {
        # Provider — pris du global déjà résolu (PROVIDER.CODE), car _load_provider
        # a strippé --provider de sys.argv ; _arg("--provider") ne le verrait plus.
        "provider": PROVIDER.CODE,
        # Zone
        "type":    t,
        "mode":    mode,
        "nom":     _arg("--zone-name", "--zone-nom"),
        "dossier": _arg("--output-dir", "--dossier"),
        "cache_dir": _arg("--cache-dir", "--dossier-cache"),
        "production_dir": _arg("--production-dir", "--dossier-production"),
        "dep":     _arg("--zone-department", "--zone-departement"),
        "region":  _arg("--zone-region"),
        "ville":   _arg("--zone-city", "--zone-ville"),
        "gps":     _arg("--zone-gps"),
        "bbox":    _arg("--zone-bbox"),
        "zone_width": _arg_float("--zone-width", "--zone-largeur", default=20.0),
        # LiDAR
        "tel":           (_flag("--download", "--telechargement")
                          or (_lidar_standard
                              and not _flag("--no-download",
                                            "--no-telechargement"))),
        # Compression ON par defaut : seule la NEGATION apparait dans argv
        "comp":          not _flag("--no-download-compress",
                                   "--no-telechargement-compresser"),
        "ecraser_tel":   _flag("--download-overwrite", "--telechargement-ecraser"),
        # --workers est UNIQUE en ligne de commande mais la GUI a un champ par
        # type : ne l'appliquer qu'au champ du type réellement lancé, sinon un
        # run LiDAR `--workers 8` repeuplait aussi le champ vecteur (plafonné à
        # 4) et le champ OSM. Même conditionnement que osm_tags_sel /
        # wfs_couches_sel plus bas, qui l'avaient déjà.
        "workers_l":     _arg_int("--workers", default=8) if t == "lidar" else 8,
        "laz_parallel":  _arg_int("--laz-parallel", default=1),
        "dossier_dalles":_arg("--tiles-dir", "--dossier-dalles"),
        "no_omb":        bool(ombs) or _flag("--shadings", "--ombrages", "--shading"),
        "ombrages":      ombs,
        # --shading répétable : collecter CHAQUE occurrence (contrairement à
        # _arg qui ne prend que la première).
        "shading_specs": [argv[i + 1] for i, a in enumerate(argv)
                          if a == "--shading" and i + 1 < len(argv)],
        "elevation":     _arg_int("--shading-elevation", "--ombrages-elevation", default=25),
        "svf_conv":      _arg("--svf-conv") or "flux",
        "svf_dist":      _arg_float("--svf-dist", default=20.0),
        "svf_gamma":     _arg_float("--svf-gamma", default=SVF_GAMMA),
        "sweep_horizon": True,  # coché par défaut (sweep-horizon SVF)
        "ecraser_omb":   _flag("--shadings-overwrite", "--ombrages-ecraser"),
        "mbtiles_l":     "mbtiles" in fmts,
        "rmap":          "rmap"    in fmts,
        "sqlitedb":      "sqlitedb" in fmts,
        "zoom_min_l":    _arg_int("--zoom-min", default=8),
        "zoom_max_l":    _arg_int("--zoom-max", default=18),
        "qualite_l":     _arg_int("--image-quality", "--qualite-image", default=85),
        "ecraser_mbt":   _flag("--tiles-overwrite", "--tuiles-ecraser"),
        "cols_decoupe":  _arg_int("--split-cols", "--cols-decoupe", default=1),
        "rows_decoupe":  _arg_int("--split-rows", "--rows-decoupe", default=1),
        "split_width_l": _arg_float("--split-width", "--split-largeur", default=0.0),
        "nettoyage":     _flag("--cleanup", "--nettoyage"),
        # IGN Raster
        "couche":        _arg("--layer", "--couche"),
        "zoom_min_s":    _arg_int("--zoom-min", default=12),
        "zoom_max_s":    _arg_int("--zoom-max", default=16),
        "mbtiles_s":     "mbtiles" in fmts,
        "rmap_s":        "rmap"    in fmts,
        "sqlitedb_s":    "sqlitedb" in fmts,
        "qualite_s":     _arg_int("--image-quality", "--qualite-image", default=85),
        "workers_s":     _arg_int("--workers", default=8) if t == "scan" else 8,
        # OSM
        "osm_tags_sel":  _args_after("--layer", "--couche") if t == "osm" else [],
        "workers_osm":   _arg_int("--workers", default=4) if t == "osm" else 4,
        # IGN Vectoriel
        "wfs_couches_sel": _args_after("--layer", "--couche") if t == "vecteur" else [],
        "workers_v":     min(_arg_int("--workers", default=4), 4) if t == "vecteur" else 4,
        # Argv complet pour debug (clés API masquées)
        "argv":    _rediger_secrets(" ".join(argv)),
    }


def _historique_debut() -> str:
    """
    Sauvegarde une entrée 'en cours' AU DÉBUT du traitement.

    But : si le process crashe (NameError, OSError, SIGKILL, panne courant,
    Ctrl+C brutal), l'entrée reste avec statut='en cours' → on voit les
    paramètres exacts du run cassé pour debug.

    Si LIDAR2MAP_HIST_RUN_ID est défini (cas GUI : id généré côté GUI pour
    pouvoir mettre à jour l'entrée plus tard depuis poll_log), réutilise cet
    id. Sinon, génère un nouvel id horodaté + pid.
    """
    global _HIST_RUN_ID, _HIST_T_DEBUT, _HIST_FINALIZED
    if _hist_disabled():
        return ""
    run_id = (os.environ.get("LIDAR2MAP_HIST_RUN_ID") or
              f"{int(time.time()*1000)}-{os.getpid()}")
    _HIST_RUN_ID    = run_id
    _HIST_T_DEBUT   = time.time()
    _HIST_FINALIZED = False
    try:
        _sauver_historique(_cfg_depuis_argv(), 0, "",
                           run_id=run_id, statut="en cours")
    except Exception as e:
        # Ne JAMAIS planter le pipeline parce que l'historique a échoué.
        print(f"  History 'in progress' not saved: {e}", flush=True)
    return run_id


def _historique_fin_crash():
    """
    Finalise l'entrée 'en cours' avec statut='ko' depuis le handler crash
    de __main__. No-op si pas de debut, ou si déjà finalisé (succès récent
    dans une boucle multi-département par exemple).
    """
    if not _HIST_RUN_ID or _HIST_FINALIZED or _hist_disabled():
        return
    duree = int(time.time() - _HIST_T_DEBUT) if _HIST_T_DEBUT else 0
    try:
        _sauver_historique(_cfg_depuis_argv(), duree, "",
                           run_id=_HIST_RUN_ID, statut="ko")
    except Exception as e:
        print(f"  History 'ko' not saved: {e}", flush=True)


def _executer_split_historise(traitement, t_debut, dossier_resultat):
    """Exécute un split et finalise son historique sur tous les chemins.

    Les runners renvoient ``True`` uniquement lorsque tous les livrables sont
    complets. Une sortie partielle est enregistrée ``ko`` puis rendue visible
    au lanceur par une exception : sans code processus non nul, le GUI la
    réécrirait en succès. Toute exception ou interruption est marquée ``ko``
    puis propagée intacte au gestionnaire de premier niveau.
    """
    def _finaliser(complet):
        duree = max(0, int(time.time() - t_debut))
        try:
            _historique_depuis_argv(
                duree, str(dossier_resultat),
                statut=("ok" if complet else "ko"))
        except Exception as e:
            # L'historique est auxiliaire : son indisponibilité ne doit ni
            # casser un traitement réussi, ni masquer l'exception d'origine.
            print(f"  History split finalization failed: {e}", flush=True)

    try:
        complet = bool(traitement())
    except BaseException:
        print(f"  Done! Folder: {dossier_resultat}")
        _finaliser(False)
        raise
    print(f"  Done! Folder: {dossier_resultat}")
    _finaliser(complet)
    if not complet:
        raise RuntimeError(
            "Split processing incomplete - rerun to complete missing chunks")
    return complet


def _bilan_historique_processus(code_retour, dossier_resultat):
    """Statut GUI et dossier à conserver dans l'historique après un process."""
    return ("ok" if code_retour == 0 else "ko", str(dossier_resultat or ""))


def _historique_fin_batch_ko(t_debut):
    """Force le bilan agrégé à ``ko`` en conservant le dernier dossier connu."""
    if _hist_disabled():
        return
    dossier_resultat = ""
    for entree in _lire_historique():
        if entree.get("id") == _HIST_RUN_ID:
            dossier_resultat = entree.get("resultat", "")
            break
    _historique_depuis_argv(
        max(0, int(time.time() - t_debut)), dossier_resultat, statut="ko")


def _historique_depuis_argv(duree_s: int, dossier_resultat: str = "",
                             run_id: str = "", statut: str = "ok"):
    """
    Sauvegarde finale depuis CLI. Si run_id non fourni, utilise _HIST_RUN_ID
    posé par _historique_debut() au début du traitement (update de l'entrée
    'en cours' existante).
    """
    global _HIST_FINALIZED
    if _hist_disabled():
        return
    _sauver_historique(_cfg_depuis_argv(), duree_s, dossier_resultat,
                       run_id=run_id or _HIST_RUN_ID, statut=statut)
    if statut in ("ok", "ko"):
        _HIST_FINALIZED = True
# ============================================================
# HISTORIQUE DES TRAITEMENTS
# ============================================================

_HISTORIQUE_PATH = DOSSIER_TRAVAIL / "historique.json"
_HISTORIQUE_MAX  = 50   # nombre max d'entrées conservées

# ── Préférences UI (langue, etc.) ─────────────────────────────────────────────
# Persistées dans l'app data, comme l'historique. Pas en localStorage : sous
# QtWebEngine packagé, le localStorage peut être éphémère selon le profil du
# webview — un desktop range ses prefs dans son dossier de données, pas dans le
# navigateur. La langue est l'override manuel du toggle ; absente = auto-détection
# par navigator.language côté JS.
_PREFS_PATH = DOSSIER_TRAVAIL / "preferences.json"


def _lire_prefs() -> dict:
    try:
        import json as _json
        with open(_PREFS_PATH, "r", encoding="utf-8") as f:
            d = _json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ecrire_pref(cle: str, valeur) -> bool:
    prefs = _lire_prefs()
    prefs[cle] = valeur
    try:
        _ecrire_json_atomique(_PREFS_PATH, prefs, indent=2)
        return True
    except Exception:
        return False


def _sauver_historique(cfg: dict, duree_s: int, dossier_resultat: str = "",
                       run_id: str = "", statut: str = "ok"):
    """
    Sauvegarde une entrée d'historique. Conserve _HISTORIQUE_MAX entrées.

    Sémantique :
      - Si run_id correspond à une entrée existante : UPDATE en place,
        date de début préservée, date_fin posée.
      - Sinon : INSERT en tête.

    statut :
      - 'en cours' : sauvegarde au DÉBUT du traitement. Reste là si le
        process crashe → diagnostique facile.
      - 'ok' / 'ko' : sauvegarde finale (succès / échec).
    """
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    # Ne jamais persister de clé API en clair dans historique.json (le cfg GUI
    # porte des champs apikey/lidar_apikey ; l'argv peut en contenir aussi).
    cfg = dict(cfg or {})
    for _sk in ("apikey", "lidar_apikey"):
        if cfg.get(_sk):
            cfg[_sk] = "***"
    if cfg.get("argv"):
        cfg["argv"] = _rediger_secrets(cfg["argv"])
    entree = {
        "id":        run_id or f"{int(time.time()*1000)}-{os.getpid()}",
        "date":      now_str,
        "statut":    statut,
        "type":      cfg.get("type", ""),
        "nom":       cfg.get("nom", ""),
        "mode":      cfg.get("mode", ""),
        "dep":       cfg.get("dep", ""),
        "ville":     cfg.get("ville", ""),
        "gps":       cfg.get("gps", ""),
        "bbox":      cfg.get("bbox", ""),
        "dossier":   cfg.get("dossier", ""),
        "resultat":  dossier_resultat,
        "duree":     _hms(duree_s) if duree_s > 0 else "",
        "params":    cfg,   # cfg complet pour rappel exact
    }
    historique = []
    if _HISTORIQUE_PATH.exists():
        try:
            historique = json.loads(_HISTORIQUE_PATH.read_text(encoding="utf-8"))
        except Exception:
            historique = []
    # Update si entrée existante (même run_id), sinon insert en tête.
    idx = -1
    if run_id:
        for i, e in enumerate(historique):
            if e.get("id") == run_id:
                idx = i
                break
    if idx >= 0:
        # Préserver la date de début ; poser date_fin si finalisation.
        entree["date"] = historique[idx].get("date", now_str)
        if statut in ("ok", "ko"):
            entree["date_fin"] = now_str
        historique[idx] = entree
    else:
        historique.insert(0, entree)
    historique = historique[:_HISTORIQUE_MAX]
    try:
        _ecrire_json_atomique(_HISTORIQUE_PATH, historique, indent=2)
        # Log discret au début (l'utilisateur n'a pas besoin de savoir), plus
        # explicite à la fin pour confirmer la sauvegarde finale.
        if statut == "en cours":
            print(f"  History: entry '{entree['id']}' (in progress)", flush=True)
        else:
            print(f"  History saved: {_HISTORIQUE_PATH}  ({len(historique)} entries)", flush=True)
    except Exception as e:
        print(f"  History not saved: {e}", flush=True)


def _lire_historique() -> list:
    """Retourne la liste des entrées d'historique (liste vide si absent/corrompu)."""
    if not _HISTORIQUE_PATH.exists():
        return []
    try:
        return json.loads(_HISTORIQUE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

# ============================================================
# INTERFACE GRAPHIQUE (PyWebView)
# ============================================================

# ── Partage LAN (transfert PC → téléphone via QR) ─────────────────────────────
# Sert les livrables (sqlitedb/rmap/mbtiles/map/obf) sur le réseau local via un
# petit serveur HTTP éphémère. Le téléphone (même WiFi) scanne un QR et télécharge
# le fichier ; l'importeur interne de Locus reste la voie fiable, « Ouvrir avec »
# dépendant des associations déclarées par Android. Pas de câble, cloud ni compte.
def _ip_lan():
    """IP LAN de la machine (truc UDP sans trafic réel). 127.0.0.1 en repli."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class _PartageServeur:
    """Serveur HTTP LAN servant une whitelist de fichiers + page d'index mobile.
    Rien hors whitelist n'est exposé ; bind 0.0.0.0 sur port éphémère ; thread
    daemon (s'éteint avec le process). Réutilisable : demarrer() puis arreter()."""
    def __init__(self):
        self._httpd = None
        self.url = None
        self.fichiers = []

    def demarrer(self, fichiers):
        import http.server, shutil, threading
        import html as _html
        from urllib.parse import unquote, quote
        self.arreter()
        # Une passe : whitelist + ordre d'affichage. `fichiers` arrive trié par
        # récence (start_share) ; en collision de nom (même basename dans deux
        # sous-dossiers), le premier vu = le plus récent gagne. L'index téléphone
        # garde cet ordre (le fichier fraîchement généré en tête, pas un tri alpha).
        table, noms = {}, []
        for p in fichiers:
            if p.exists() and p.name not in table:
                table[p.name] = p
                noms.append(p.name)
        self.fichiers = noms

        class _H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass   # silencieux (pas de spam stderr)

            # Page d'index bilingue : langue du TÉLÉPHONE via le header
            # Accept-Language (standard HTTP ; ex. "fr-FR,fr;q=0.9,en;q=0.8").
            _TXT = {
                "fr": {"h": "Fichiers à importer",
                       "p": "Télécharge un fichier. Dans Locus : Gestionnaire de "
                            "cartes → Importer une carte → gestionnaire de fichiers. "
                            "« Ouvrir avec » peut aussi fonctionner selon Android.",
                       "w": "Android peut avertir « Impossible de télécharger de "
                            "façon sécurisée » : choisir <b>Enregistrer</b>. "
                            "Transfert local en WiFi (HTTP sans certificat), "
                            "rien ne sort du réseau."},
                "en": {"h": "Files to import",
                       "p": "Download a file. In Locus: Map Manager → Import map → "
                            "system file manager. ‘Open with’ may also work, "
                            "depending on Android.",
                       "w": "Android may warn the download is insecure: choose "
                            "<b>Save</b>. Local WiFi transfer (plain HTTP, no "
                            "certificate), nothing leaves your network."},
            }

            def do_GET(self):
                name = unquote(self.path.lstrip("/"))
                if name in ("", "index.html"):
                    _al = (self.headers.get("Accept-Language") or "").lower()
                    txt = self._TXT["fr" if _al.startswith("fr") else "en"]
                    items = "".join(
                        f'<li><a href="/{quote(n)}">{_html.escape(n)}</a> '
                        f'<span>{self.server._table[n].stat().st_size // 1024} Ko</span></li>'
                        for n in self.server._noms)
                    page = (
                        "<!doctype html><meta name=viewport "
                        "content='width=device-width,initial-scale=1'>"
                        "<title>lidar2map</title>"
                        "<style>body{font-family:sans-serif;margin:1.5em;font-size:1.15em}"
                        "li{margin:.7em 0}span{color:#888;font-size:.85em}a{color:#1565c0}</style>"
                        f"<h2>{txt['h']}</h2>"
                        f"<ul>{items}</ul>"
                        f"<p style='color:#888'>{txt['p']}</p>"
                        f"<p style='color:#888;font-size:.85em'>{txt['w']}</p>").encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(page)))
                    self.end_headers()
                    self.wfile.write(page)
                    return
                p = self.server._table.get(name)
                if p is None or not p.exists():
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(p.stat().st_size))
                self.send_header("Content-Disposition", f'attachment; filename="{name}"')
                self.end_headers()
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)

        self._httpd = http.server.ThreadingHTTPServer(("0.0.0.0", 0), _H)
        self._httpd._table = table
        self._httpd._noms = self.fichiers
        # Un téléchargement annulé côté téléphone (BrokenPipe) est un événement
        # normal, pas une erreur : sans ça, socketserver imprime une traceback
        # complète dans le terminal à chaque annulation (--serve CLI).
        self._httpd.handle_error = lambda *a: None
        self.url = f"http://{_ip_lan()}:{self._httpd.server_address[1]}/"
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        return self.url

    def arreter(self):
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None


# Extensions des livrables transférables vers le téléphone. Source unique pour
# le GUI (start_share) et le CLI (main_serve) : ne pas dupliquer.
_EXTS_LIVRABLES = {".sqlitedb", ".rmap", ".mbtiles", ".map", ".obf"}


def _base_projets(dossier=None):
    """Racine des projets : dossier de sortie custom, sinon <travail>/Projets.
    Convention UNIQUE (get_projets, start_share, main_serve, fusion GUI) :
    toute résolution d'un chemin de projet passe par ici."""
    return Path(dossier) if dossier else DOSSIER_TRAVAIL / "Projets"


def _dossier_partage_projet(nom, dossier=None):
    """Dossier à parcourir pour le partage LAN d'un projet.

    Le pipeline normalise toujours le nom de projet en slug ASCII minuscule
    quand la sortie est automatique. Sur un système sensible à la casse
    (Linux), rechercher le nom brut saisi dans la GUI ferait donc manquer un
    dossier pourtant valide (``Thones`` vs ``thones``).

    Avec ``--output-dir`` / le champ « Dossier sortie », les pipelines écrivent
    directement dans ce dossier : il ne faut pas lui ajouter le nom du projet.
    """
    if dossier:
        return Path(dossier)
    return _base_projets() / normaliser_nom((nom or "").strip())


def _livrables_projet(proj):
    """Livrables d'un projet (récursif, toutes sorties confondues), du plus
    récent au plus vieux. Partagé par start_share (GUI) et main_serve (CLI)."""
    if not proj.exists():
        return []
    return sorted(
        (p for p in proj.rglob("*") if p.suffix.lower() in _EXTS_LIVRABLES),
        key=lambda p: p.stat().st_mtime, reverse=True)


def main_serve():
    """Mode --serve : sert les livrables d'un projet existant sur le réseau
    local (URL + QR ASCII) pour import direct sur le téléphone. Ctrl+C arrête."""
    import argparse
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --serve",
        description="Partage LAN des livrables d'un projet (téléphone via QR).")
    parser.add_argument("--serve", action="store_true",
                        help="Mode partage LAN (ce mode)")
    parser.add_argument("--zone-name", "--zone-nom", dest="zone_nom", required=True,
                        metavar="NOM", help="Nom du projet (dossier sous Projets/)")
    parser.add_argument("--output-dir", "--dossier", dest="dossier", default=None,
                        metavar="CHEMIN",
                        help="Dossier de sortie custom (défaut : <travail>/Projets)")
    args = parser.parse_args()

    proj = _dossier_partage_projet(args.zone_nom, args.dossier)
    fichiers = _livrables_projet(proj)
    if not fichiers:
        print(f"  No deliverable (sqlitedb/rmap/mbtiles/map) in {proj}")
        sys.exit(1)

    srv = _PartageServeur()
    url = srv.demarrer(fichiers)
    print(f"  Serving {len(srv.fichiers)} file(s) from {proj}:")
    for n in srv.fichiers:
        print(f"    {n}")
    print(f"\n  URL: {url}\n")
    # QR ASCII (lib `qrcode`, installée à la volée ; repli silencieux : l'URL
    # ci-dessus suffit à taper à la main).
    try:
        try:
            import qrcode
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "qrcode", "-q"],
                           check=True, timeout=120)
            import qrcode
        _qr = qrcode.QRCode(border=1)
        _qr.add_data(url)
        _qr.print_ascii(invert=True)
    except Exception:
        pass
    print("  Phone on the same WiFi: scan (or type the URL), download a file.")
    print("  Locus: Map Manager > Import map > system file manager")
    print("  ('Open with' may also work, depending on Android). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.arreter()
        print("\n  Share server stopped.")
        sys.exit(0)


def lancer_gui():
    """
    GUI PyWebView — fenêtre native affichant un formulaire HTML/CSS/JS.
    Communication bidirectionnelle via l'objet Api exposé à JavaScript.
    """
    # threading et queue : imports module-level (l'ancien ré-import local
    # shadowait les mêmes modules sans raison).

    # ── Sélection du backend GUI ───────────────────────────────────────────
    # Forcer le backend Qt AVANT l'import de webview sur les 3 OS (pywebview
    # peut lire PYWEBVIEW_GUI dès l'import) :
    #   macOS   : évite Cocoa (NSScreen None en SSH+VNC -> crash).
    #   Windows : évite WinForms/pythonnet (régression 3.1.0 -> GUI gelée).
    #   Linux   : Qt est le seul backend viable.
    # En frozen, le runtime hook la pose déjà ; ceci fiabilise le mode dev.
    if platform.system() in ("Darwin", "Windows", "Linux"):
        os.environ.setdefault("PYWEBVIEW_GUI", "qt")

    try:
        import webview
    except ImportError:
        print("  PyWebView missing - automatic install...")
        # PyWebView nécessite un backend natif :
        #   Windows : WebView2 (préinstallé Win10+)         → "pywebview"
        #   macOS   : Cocoa WebKit (préinstallé)            → "pywebview"
        #   Linux   : QtWebEngine via PyQt6 (recommandé)    → "pywebview[qt6]"
        #             alternative : GTK via pygobject       → "pywebview[gtk]"
        #
        # Sur Linux, sans extra, pywebview lève RuntimeError au démarrage
        # ("No suitable backend found"). On utilise [qt6] (et non [qt] qui
        # fait du PyQt5 dans pywebview < 6.0) pour rester cohérent avec
        # _installer_deps + lidar2map_mac.spec qui sont sur PyQt6.
        # [gtk] nécessiterait des paquets système (libgirepository1.0-dev,
        # gir1.2-webkit2-4.0…) et n'est donc pas le défaut.
        if LINUX:
            pkg = "pywebview[qt6]"
        else:
            pkg = "pywebview"
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=True, timeout=600)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Fallback : tenter sans --break-system-packages (envs Conda/venv).
            # Un échec/timeout ici ne doit pas crasher : on laisse l'import
            # webview ci-dessous échouer proprement avec un message clair.
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                               check=True, timeout=600)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as _e_wv:
                print(f"  PyWebView install failed ({type(_e_wv).__name__}).")
        try:
            import webview
        except ImportError:
            if LINUX:
                print("  ERROR: pywebview installed but without a working backend.")
                print("  On Linux, also install the required system packages:")
                print("    Debian/Ubuntu : sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine")
                print("    Fedora/RHEL   : sudo dnf install python3-pyqt6 python3-pyqt6-webengine")
                print("    Arch          : sudo pacman -S python-pyqt6 python-pyqt6-webengine")
            raise

    # Supprimer les warnings internes pywebview (AccessibilityObject, COM, etc.)
    import logging as _logging
    for _name in ("pywebview", "pywebview.window", "pywebview.util",
                  "pywebview.platforms", "pywebview.js"):
        _lg = _logging.getLogger(_name)
        _lg.setLevel(_logging.CRITICAL)
        _lg.handlers.clear()
        _lg.propagate = False

    # En mode frozen, l'exe est son propre lanceur (pas de python + .py).
    SCRIPT  = (Path(sys.executable).resolve()
               if getattr(sys, "frozen", False)
               else Path(__file__).resolve())

    # ── Table zooms pour la sélection de couche ───────────────────────────────
    # NB : _lire_zoom_limites_wmts() interroge GetCapabilities au runtime et
    # corrige automatiquement ces valeurs si elles diffèrent de la réalité.
    # Cette table sert seulement à pré-remplir la GUI.
    _ZOOMS_GUI = {
        "scan25": (8, 16), "scan25tour": (8, 16), "scan100": (6, 14),
        "scanoaci": (6, 15), "planign": (6, 18), "etatmajor40": (6, 15),
        "etatmajor10": (8, 16), "pentes": (6, 14), "ortho": (10, 20),
        "cadastre": (12, 19), "ombrage": (6, 14),
        # Orthos historiques métropole (résolution dégradée vs ortho actuelle)
        "ortho_1950": (10, 18), "ortho_1965": (10, 18), "ortho_1980": (10, 18),
        # Infrarouge couleur (couverture identique à ortho)
        "ortho_irc": (10, 19),
        # Satellite : résolution plus faible que aérien → zoom max plus bas
        "pleiades": (10, 19), "spot": (8, 16),
        # EDUGEO : couverture restreinte aux centres urbains, zooms élevés
        "edugeo_marseille_1969": (12, 18), "edugeo_marseille_1980": (12, 18),
        "edugeo_marseille_1987": (12, 18), "edugeo_marseille_1988": (12, 18),
        "edugeo_marseille_2010": (12, 18), "edugeo_toulon_1972": (12, 18),
        # USGS Imagery (USA) : cache complet jusqu'à z16 (~1.8 m), partiel au-delà.
        "naip": (11, 16),
    }

    # ── Données statiques exposées au formulaire ──────────────────────────────
    _COUCHES_PRIVEES = {"scan25", "scan25tour", "scan100", "scanoaci"}
    _COUCHES_LABELS = {"naip": "USGS Imagery (USA, ~1 m)"}
    # Pays propriétaire de chaque couche raster (filtre l'onglet selon le provider).
    _COUCHES_PAYS = {"naip": "us"}   # défaut "fr" (couches IGN)
    _COUCHES_DATA = [
        {"code": k,
         "label": f"{'⚠ [PRO] ' if k in _COUCHES_PRIVEES else ''}{k}  "
                  f"({_COUCHES_LABELS.get(k, v[0])})",
         "zoom_min":  _ZOOMS_GUI.get(k, (8, 16))[0],
         "zoom_max":  _ZOOMS_GUI.get(k, (8, 16))[1],
         "restreinte": k in _COUCHES_PRIVEES,
         "pays":       _COUCHES_PAYS.get(k, "fr")}
        for k, v in COUCHES.items()
    ]
    _WFS_DATA = [{"alias": k, "label": v[1]} for k, v in COUCHES_WFS.items()]
    _OSM_TAGS_DATA = [
        {"tag": "highway=*",              "label": "Routes/chemins"},
        {"tag": "waterway=*",             "label": "Cours d'eau"},
        {"tag": "natural=water",          "label": "Plans d'eau"},
        {"tag": "natural=*",              "label": "Naturel (tout)"},
        {"tag": "boundary=administrative","label": "Limites admin"},
        {"tag": "landuse=*",              "label": "Occupation sol"},
        {"tag": "building=*",             "label": "Bâtiments"},
        {"tag": "historic=*",             "label": "Historique"},
    ]

    # ── Classe API exposée à JavaScript ──────────────────────────────────────
    def _classify_err(line: str) -> bool:
        """True si la ligne ressemble à une erreur (ERREUR/Error/Traceback/argparse).

        Utilisé par les 3 sites de drain stdout du subprocess pour rester
        synchronisés — sans cette factorisation, une évolution du heuristique
        ne se propageait qu'à un site sur trois.
        """
        upbuf = line.upper()
        return (
            any(w in upbuf for w in ("ERREUR", "ERROR", "TRACEBACK"))
            or line.strip().startswith("usage:")
            or ": error:" in line
        )

    class Api:
        def __init__(self):
            self._process   = None
            self._log_queue = queue.Queue()
            self._done      = False
            self._retcode   = None
            self.window     = None  # injecté par pywebview au démarrage
            # Lock pour les attributs partagés entre le thread d'écoute du
            # subprocess (run) et le thread main (poll_log, get_last_error).
            # Le GIL protège les opérations atomiques ; le lock protège la
            # cohérence multi-attributs (ex: lire _retcode et _modal_error_msg
            # ensemble doit voir l'état stable d'un même moment).
            self._lock = threading.Lock()
            self._err_lines       = []
            self._tail_lines      = []
            self._modal_error_msg = ""
            self._partage         = _PartageServeur()   # transfert LAN vers téléphone
            self._stop_t          = None   # horodatage de la demande d'arrêt (stop)
            self._reader_t        = None   # thread lecteur stdout du run courant
            # Verrou + drapeau anti-double-lancement : launch() décide sous ce
            # verrou et pose _launching AVANT de rendre la main. Sans ça, deux
            # clics rapides lisaient tous deux _process=None (le subprocess
            # n'étant créé que plus tard) et lançaient deux traitements.
            self._launch_lock     = threading.Lock()
            self._launching       = False

        # ── Données initiales ─────────────────────────────────────────────
        def get_init_data(self):
            return {
                "couches":    _COUCHES_DATA,
                "wfs":        _WFS_DATA,
                "osm_tags":   _OSM_TAGS_DATA,
                "apikey_def": APIKEY_DEFAUT,
                "historique": _lire_historique(),
                "providers":  _discover_providers(),
                "active_provider": PROVIDER.CODE,
                "resolution_m": RESOLUTION_M,   # défaut LRM/RRIM = 15 px × résolution

                "regions":    _regions_disponibles(),
                "lang":       _lire_prefs().get("lang"),   # None = auto-détection JS
                "ui_zoom":    _lire_prefs().get("ui_zoom"),  # None = 1.0
            }

        def get_help(self):
            """Texte affiché par le bouton Aide du GUI : le docstring d'usage du
            module (source UNIQUE — le même bloc qui documente les modes et les
            paramètres CLI en tête de fichier). Pas de copie à maintenir."""
            import sys as _sys
            return (_sys.modules[__name__].__doc__ or "").strip()

        def get_usage(self, cfg=None):
            """Onglet Usage (LECTURE SEULE) : tailles des 3 tiers (cache /
            production / projets) + leurs sous-dossiers, pour un ménage MANUEL
            via l'explorateur (bouton open_folder). Ne supprime rien — le cache
            est partagé entre projets, une purge auto risquerait de jeter des
            dalles qu'un autre projet réutilise (règle Nico : nettoyage manuel).
            Prend les racines custom du formulaire (cache_dir/production_dir) si
            posées, sinon les défauts."""
            cfg = cfg or {}
            def _walk(p):
                total = 0
                try:
                    for r, _dirs, files in os.walk(p):
                        for f in files:
                            try:
                                total += (Path(r) / f).stat().st_size
                            except OSError:
                                pass
                except OSError:
                    pass
                return total
            def _children(root):
                out = []
                try:
                    for d in sorted(root.iterdir()):
                        if d.is_dir():
                            out.append({"label": d.name, "path": str(d),
                                        "bytes": _walk(d)})
                except OSError:
                    pass
                return out
            def _tier(key, label, root):
                root = Path(root)
                ok = root.exists()
                return {"key": key, "label": label, "path": str(root),
                        "exists": ok,
                        "bytes": _walk(root) if ok else 0,
                        "children": _children(root) if ok else []}
            cache = (Path(cfg["cache_dir"]).expanduser()
                     if cfg.get("cache_dir") else DOSSIER_CACHE)
            prod = (Path(cfg["production_dir"]).expanduser()
                    if cfg.get("production_dir") else DOSSIER_PRODUCTION)
            projets = DOSSIER_TRAVAIL / "Projets"
            return {"tiers": [
                _tier("cache", "Cache", cache),
                _tier("production", "Production", prod),
                _tier("projets", "Projets", projets),
            ]}

        # ── Partage LAN vers le téléphone (QR) ────────────────────────────
        def start_share(self, cfg=None):
            """Sert les livrables du dernier run (ou de `cfg`) sur le LAN.
            Renvoie {ok, url, fichiers} ou {ok:False, error}."""
            cfg = cfg or getattr(self, "_cfg_launch", None) or {}
            nom = (cfg.get("nom") or "").strip()
            if not nom:
                return {"ok": False, "error": "Aucun projet : lance d'abord une génération."}
            # Miroir exact du routage du pipeline : slug minuscule en sortie
            # automatique, dossier direct avec un --output-dir personnalisé.
            proj = _dossier_partage_projet(nom, cfg.get("dossier"))
            fichiers = _livrables_projet(proj)
            if not fichiers:
                return {"ok": False,
                        "error": f"Aucun livrable (sqlitedb/rmap/mbtiles/map) dans {proj}"}
            try:
                url = self._partage.demarrer(fichiers)
            except Exception as e:
                return {"ok": False, "error": f"Partage impossible : {e}"}
            # Liste du serveur (dédupliquée, ordre par récence) : le modal PC
            # affiche exactement ce que la page téléphone sert.
            return {"ok": True, "url": url, "fichiers": self._partage.fichiers}

        def stop_share(self):
            try:
                self._partage.arreter()
            except Exception:
                pass
            return {"ok": True}

        def get_projets(self, dossier=None):
            """Noms des projets existants (sous-dossiers de Projets/, ou du
            dossier de sortie custom), récents d'abord. Alimente la datalist
            du champ Nom (combobox éditable : saisie libre + suggestions)."""
            try:
                dirs = [d for d in _base_projets(dossier).iterdir() if d.is_dir()]
                dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            except OSError:
                return []
            return [d.name for d in dirs]

        def get_historique(self):
            """Retourne la liste historique — appelable depuis JS à tout moment."""
            return _lire_historique()

        def clear_historique(self):
            """Vide intégralement l'historique (action destructive — la confirmation
            est gérée côté JS via confirm() avant l'appel)."""
            try:
                _ecrire_json_atomique(_HISTORIQUE_PATH, [], indent=2)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        def set_lang(self, code):
            """Persiste l'override manuel de langue de l'UI (toggle FR/EN).
            'fr' ou 'en' ; toute autre valeur est ignorée."""
            if code not in ("fr", "en"):
                return {"ok": False, "error": "lang invalide"}
            return {"ok": _ecrire_pref("lang", code)}

        def set_ui_zoom(self, z):
            """Persiste le zoom de l'interface (Ctrl+molette / Ctrl+±),
            restauré au prochain lancement via get_init_data. Borné 0.5–2.5."""
            try:
                z = float(z)
            except (TypeError, ValueError):
                return {"ok": False, "error": "zoom invalide"}
            if not (0.5 <= z <= 2.5):
                return {"ok": False, "error": "zoom hors plage"}
            return {"ok": _ecrire_pref("ui_zoom", round(z, 2))}

        # ── Autocomplétion ville (proxy BAN pour FR, Nominatim sinon) ────
        # Côté JS, fetch() depuis NavigateToString a un Origin "null" que
        # WebView2 traite mal vis-à-vis du CORS — on relaie ici en Python.
        # FR : Geoplateforme BAN (rapide, précis pour communes françaises)
        # Hors FR : Nominatim avec countrycodes=<pays> pour scoper à un pays
        def autocomplete_ville(self, prefix, country="fr"):
            try:
                p = (prefix or "").strip()
                if len(p) < 3:
                    return []
                country = (country or "fr").lower()
                if country == "fr":
                    url = ("https://data.geopf.fr/geocodage/search/"
                           f"?q={urllib.parse.quote(p)}"
                           "&type=municipality&autocomplete=1&limit=8")
                    req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
                    with urllib.request.urlopen(req, timeout=3) as r:
                        data = json.load(r)
                    out = []
                    for f in data.get("features", []):
                        props = f.get("properties", {}) or {}
                        label = props.get("name") or props.get("label") or ""
                        if label:
                            out.append({"label": label,
                                        "context": props.get("context", "")})
                    return out
                # Non-FR : Nominatim international, filtre par pays
                url = ("https://nominatim.openstreetmap.org/search"
                       f"?q={urllib.parse.quote(p)}"
                       f"&countrycodes={country}&format=json&limit=8&addressdetails=1")
                req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.load(r)
                out = []
                for item in data:
                    addr = item.get("address", {}) or {}
                    label = (addr.get("city") or addr.get("town")
                             or addr.get("village") or addr.get("municipality")
                             or item.get("display_name", "").split(",")[0])
                    if label:
                        ctx_parts = [addr.get(k) for k in ("state", "country") if addr.get(k)]
                        out.append({"label": label,
                                    "context": ", ".join(ctx_parts)})
                return out
            except Exception:
                return []

        # ── Dialogs fichiers ─────────────────────────────────────────────
        def _get_window(self):
            if self.window is None and webview.windows:
                self.window = webview.windows[0]
            return self.window

        def pick_dir(self, start="", kind=""):
            """Sélecteur de dossier, positionné sur le dossier COURANT du champ
            (start) ou, si vide (« (auto) »), sur la racine par défaut du tier
            (output/cache/production), créée si absente pour que le dialog s'y
            ouvre. Le dossier choisi est renvoyé au JS qui le pose dans le champ."""
            w = self._get_window()
            if not w: return ""
            s = (start or "").strip()
            if not s:
                s = str({"cache": DOSSIER_CACHE,
                         "production": DOSSIER_PRODUCTION,
                         "output": DOSSIER_TRAVAIL / "Projets"}.get(kind, DOSSIER_TRAVAIL))
            try:
                Path(s).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            try:
                r = w.create_file_dialog(webview.FOLDER_DIALOG, directory=s)
                return r[0] if r else ""
            except Exception as e:
                print(f"  pick_dir erreur : {e}")
                return ""

        def pick_file(self, multiple=False, exts=None):
            w = self._get_window()
            if not w: return [] if multiple else ""
            types = tuple(exts) if exts else ()
            try:
                r = w.create_file_dialog(
                    webview.OPEN_DIALOG, allow_multiple=multiple, file_types=types)
                if not r: return [] if multiple else ""
                return list(r) if multiple else r[0]
            except Exception as e:
                print(f"  pick_file erreur : {e}")
                return [] if multiple else ""

        # ── Construction de la commande CLI ──────────────────────────────
        def _build_cmd(self, cfg):
            # Frozen : l'exe est self-launching, on n'y prépose pas sys.executable.
            cmd = ([str(SCRIPT)] if getattr(sys, "frozen", False)
                   else [sys.executable, str(SCRIPT)])
            t = cfg.get("type", "lidar")

            # Provider (multi-pays) — toujours explicite dans le subprocess.
            # Le contrat CLI LiDAR l'exige, y compris pour fr-ign sélectionné
            # par défaut dans la GUI.
            if cfg.get("provider"):
                cmd += ["--provider", cfg["provider"]]
            # Mode LAZ (structures debout) : case + réglages ≠ défauts
            # (la GUI n'envoie dfm_* que si modifiés, cf. app.js).
            if cfg.get("laz"):
                cmd += ["--laz"]
                if cfg.get("laz_hmin"):
                    cmd += ["--laz-hmin", str(cfg["laz_hmin"])]
                if cfg.get("laz_hmax"):
                    cmd += ["--laz-hmax", str(cfg["laz_hmax"])]
                if cfg.get("laz_classes"):
                    cmd += ["--laz-classes", str(cfg["laz_classes"])]
                if cfg.get("laz_ground"):
                    cmd += ["--laz-ground", str(cfg["laz_ground"])]
                if cfg.get("laz_csf_threshold"):
                    cmd += ["--laz-csf-threshold", str(cfg["laz_csf_threshold"])]
                if cfg.get("laz_csf_resolution"):
                    cmd += ["--laz-csf-resolution", str(cfg["laz_csf_resolution"])]
                if cfg.get("laz_csf_rigidness"):
                    cmd += ["--laz-csf-rigidness", str(cfg["laz_csf_rigidness"])]
            # Clé API LiDAR (us-3dep / OpenTopography). Champ saisi dans la GUI
            # à côté de la dropdown provider, visible quand APIKEY_REQUISE=True.
            if cfg.get("lidar_apikey"):
                cmd += ["--api-key", cfg["lidar_apikey"]]

            # Zone (pas pour fusion / découpe)
            if t != "fusion" and t != "decoupe":
                mode = cfg.get("mode", "ville")
                if mode == "ville"  and cfg.get("ville"):
                    cmd += ["--zone-city", cfg["ville"]]
                elif mode == "gps"  and cfg.get("gps"):
                    cmd += ["--zone-gps", cfg["gps"]]
                elif mode == "bbox" and cfg.get("bbox"):
                    cmd += ["--zone-bbox", cfg["bbox"]]
                elif mode == "dep"  and cfg.get("dep"):
                    cmd += ["--zone-department", cfg["dep"]]
                elif mode == "region" and cfg.get("region"):
                    cmd += ["--zone-region", cfg["region"]]
                if cfg.get("zone_width") is not None and cfg["zone_width"] != "":
                    cmd += ["--zone-width", str(cfg["zone_width"])]
                if cfg.get("nom"):
                    cmd += ["--zone-name", cfg["nom"]]
                if cfg.get("dossier"):
                    cmd += ["--output-dir", cfg["dossier"]]
                # Dossier cache global (--cache-dir) : commun à tous les types,
                # comme --output-dir. Propriété d'installation, saisi dans Projet.
                if cfg.get("cache_dir"):
                    cmd += ["--cache-dir", cfg["cache_dir"]]
                # Dossier production (--production-dir) : racine des .tif LAZ
                # (produits). Saisi dans Projet (ligne des racines), n'a d'effet
                # qu'en mode LAZ, mais émis inconditionnellement comme --cache-dir.
                if cfg.get("production_dir"):
                    cmd += ["--production-dir", cfg["production_dir"]]

            # ── LiDAR ────────────────────────────────────────────────────
            if t == "lidar":
                cmd.append("--lidar")
                # Le CLI télécharge désormais les données manquantes par défaut.
                # La GUI doit donc exprimer aussi le choix négatif : sans ce
                # --no-download, décocher la case n'aurait plus aucun effet.
                cmd.append("--download" if cfg.get("tel", True)
                           else "--no-download")
                # Compression ON par défaut côté CLI : n'émettre que la
                # déviation (case décochée → --no-download-compress).
                if not cfg.get("comp", True):
                    cmd.append("--no-download-compress")
                if cfg.get("ecraser_tel"): cmd.append("--download-overwrite")
                if cfg.get("dossier_dalles"):
                    cmd += ["--tiles-dir", cfg["dossier_dalles"]]
                if cfg.get("workers_l"):
                    cmd += ["--workers", str(cfg["workers_l"])]
                # --laz-parallel : n'émettre que si explicitement > 1 (défaut 1 =
                # sériel, sûr). Le champ GUI est borné (max 8) et n'apparaît qu'en
                # mode LAZ ; le cœur affiche l'estimation RAM (~3 Go × N).
                if cfg.get("laz_parallel", 1) and cfg["laz_parallel"] > 1:
                    cmd += ["--laz-parallel", str(cfg["laz_parallel"])]
                if cfg.get("no_omb"):
                    ombs = cfg.get("ombrages", [])
                    if ombs: cmd += ["--shadings"] + ombs
                    # Instances paramétrées (shuttle list) — répétable
                    for _spec in cfg.get("shading_specs", []) or []:
                        cmd += ["--shading", str(_spec)]
                    if cfg.get("elevation"):
                        cmd += ["--shading-elevation", str(cfg["elevation"])]
                    if cfg.get("svf_conv"):
                        cmd += ["--svf-conv", str(cfg["svf_conv"])]
                    if cfg.get("svf_dist"):
                        cmd += ["--svf-dist", str(cfg["svf_dist"])]
                    if cfg.get("svf_gamma"):
                        cmd += ["--svf-gamma", str(cfg["svf_gamma"])]
                    if cfg.get("ecraser_omb"): cmd.append("--shadings-overwrite")
                    # BooleanOptionalAction : émettre explicitement on/off.
                    # Le sweep concerne désormais svf/opos/oneg (plus aucun
                    # gate ray-cast forcé côté kernel). N'émettre le flag
                    # global que si une de ces instances est présente : sinon
                    # il fuit sur un run sans aucune d'elles (ex. hillshade
                    # seul) et polluerait la commande sans effet utile.
                    if any(str(s).startswith(("svf", "opos", "oneg"))
                           for s in cfg.get("shading_specs", []) or []):
                        cmd.append("--svf-sweep" if cfg.get("sweep_horizon") else "--no-svf-sweep")
                fmts = []
                if cfg.get("mbtiles_l"): fmts.append("mbtiles")
                if cfg.get("rmap"):      fmts.append("rmap")
                if cfg.get("sqlitedb"):  fmts.append("sqlitedb")
                if fmts:
                    cmd += ["--file-formats"] + fmts
                    if cfg.get("zoom_min_l"): cmd += ["--zoom-min", str(cfg["zoom_min_l"])]
                    if cfg.get("zoom_max_l"): cmd += ["--zoom-max", str(cfg["zoom_max_l"])]
                    if cfg.get("fmt_l") and cfg["fmt_l"] != "auto":
                        cmd += ["--image-format", cfg["fmt_l"]]
                    if cfg.get("qualite_l"): cmd += ["--image-quality", str(cfg["qualite_l"])]
                    if cfg.get("ecraser_mbt"): cmd.append("--tiles-overwrite")
                    # La case « 0 — Découpage à priori » est l'interrupteur :
                    # décochée, on n'émet rien même si des valeurs traînent dans
                    # les champs (elles sont conservées pour un recochage).
                    _cols = cfg.get("cols_decoupe", 1) or 1
                    _rows = cfg.get("rows_decoupe", 1) or 1
                    if not cfg.get("decoupe", False):
                        _cols = _rows = 1
                    if _cols > 1 and _rows > 1:
                        cmd += ["--split-cols", str(_cols),
                                "--split-rows", str(_rows)]
                    elif (cfg.get("decoupe", False)
                          and cfg.get("split_width_l", 0) > 0):
                        cmd += ["--split-width", str(cfg["split_width_l"])]
                    if cfg.get("nettoyage"):
                        cmd.append("--cleanup")
                        # Posé par la file d'attente (renderFile/lancerFile) quand
                        # une tâche ULTÉRIEURE retraite la même zone avec la même
                        # source : on garde les dalles pour elle.
                        if cfg.get("cleanup_keep_tiles"):
                            cmd.append("--cleanup-keep-tiles")
                    if cfg.get("min_free_gb", 0) > 0:
                        cmd += ["--min-free-gb", str(cfg["min_free_gb"])]
                    # Sharding multi-VM : quelle tranche géographique CETTE
                    # invocation traite (cf. section « Calcul distant » de
                    # l'Exécution). Sans lien avec la case Découpage à
                    # priori ci-dessus (un découpage interne au run), donc pas
                    # gardé par cfg.get("decoupe").
                    if cfg.get("remote_block"):
                        cmd += ["--block", cfg["remote_block"]]
                if cfg.get("purger_inv"):  cmd.append("--tiles-purge-invalid")
                if cfg.get("purger_zone"): cmd.append("--tiles-purge-out-of-zone")

            # ── IGN Raster ───────────────────────────────────────────────
            elif t == "scan":
                cmd.append("--raster")
                couche = cfg.get("couche", "scan25")
                cmd += ["--layer", couche]
                if cfg.get("apikey"): cmd += ["--api-key", cfg["apikey"]]
                if cfg.get("tel_s"):
                    if cfg.get("workers_s"):
                        cmd += ["--workers", str(cfg["workers_s"])]
                    if cfg.get("ecraser_tel_s"): cmd.append("--download-overwrite")
                if cfg.get("tuiles_s"):
                    fmts = []
                    if cfg.get("mbtiles_s"): fmts.append("mbtiles")
                    if cfg.get("rmap_s"):    fmts.append("rmap")
                    if cfg.get("sqlitedb_s"):fmts.append("sqlitedb")
                    if fmts: cmd += ["--file-formats"] + fmts
                    cmd += ["--zoom-min", str(cfg.get("zoom_min_s", 12)),
                            "--zoom-max", str(cfg.get("zoom_max_s", 16))]
                    if cfg.get("fmt_s") and cfg["fmt_s"] != "auto":
                        cmd += ["--image-format", cfg["fmt_s"]]
                    if cfg.get("qualite_s"):
                        cmd += ["--image-quality", str(cfg["qualite_s"])]
                    if cfg.get("ecraser_tuil_s"): cmd.append("--tiles-overwrite")
                    # Jumeau du LiDAR : la case du cadre est l'interrupteur.
                    _cols = cfg.get("cols_decoupe_s", 0) or 0
                    _rows = cfg.get("rows_decoupe_s", 0) or 0
                    if not cfg.get("decoupe_s", False):
                        _cols = _rows = 0
                    if _cols > 0 and _rows > 0:
                        cmd += ["--split-cols", str(_cols),
                                "--split-rows", str(_rows)]
                    elif (cfg.get("decoupe_s", False)
                          and cfg.get("split_width_s", 0) > 0):
                        cmd += ["--split-width", str(cfg["split_width_s"])]
                    if cfg.get("nettoyage"): cmd.append("--cleanup")
                    if cfg.get("min_free_gb", 0) > 0:
                        cmd += ["--min-free-gb", str(cfg["min_free_gb"])]

            # ── OSM ──────────────────────────────────────────────────────
            elif t == "osm":
                cmd.append("--osm")
                tags = cfg.get("osm_tags_sel", [])
                if tags: cmd += ["--layer"] + tags
                if cfg.get("tel_osm"):
                    if cfg.get("workers_osm", 4) != 4: cmd += ["--workers", str(cfg["workers_osm"])]
                    if cfg.get("ecraser_tel_osm"): cmd.append("--download-overwrite")
                if cfg.get("tuiles_osm"):
                    fmts = []
                    if cfg.get("map"):        fmts.append("map")
                    if cfg.get("osm_geojson"):     fmts.append("gz")
                    if cfg.get("osm_geojson_raw"): fmts.append("geojson")
                    if cfg.get("osm_transparent"): fmts.append("transparent-raster")
                    if fmts: cmd += ["--file-formats"] + fmts
                    if cfg.get("ecraser_tuil_osm"): cmd.append("--tiles-overwrite")

            # ── IGN Vectoriel ─────────────────────────────────────────────
            elif t == "vecteur":
                cmd.append("--vector")
                couches = cfg.get("wfs_couches_sel", [])
                if couches: cmd += ["--layer"] + couches
                if cfg.get("tel_v"):
                    cmd += ["--workers", str(cfg.get("workers_v", 4))]
                    if cfg.get("ecraser_tel_v"): cmd.append("--download-overwrite")
                # Les GeoJSON sont écrits par le téléchargement (marqués
                # « natif » dans la GUI) : ils sortent quel que soit l'état de
                # la case « 2 — Générer la carte ». Celle-ci ne gouverne que les
                # livrables DÉRIVÉS du GeoJSON.
                fmts = []
                if cfg.get("fusion_gz", True):  fmts.append("gz")
                if cfg.get("fusion_gz_raw"):     fmts.append("geojson")
                if not fmts: fmts = ["gz"]  # défaut si rien coché
                _carte_v = cfg.get("carte_v", True)
                if _carte_v and cfg.get("tuiles_v"): fmts.append("map")
                if _carte_v and cfg.get("vec_transparent"):
                    fmts.append("transparent-raster")
                cmd += ["--file-formats"] + fmts
                if _carte_v and cfg.get("tuiles_v") and cfg.get("ecraser_tuil_v"):
                    cmd.append("--tiles-overwrite")
                if _carte_v and cfg.get("tuiles_v") and cfg.get("simplif_v"):
                    cmd += ["--vector-simplify", str(cfg["simplif_v"])]

            # ── Fusion ────────────────────────────────────────────────────
            elif t == "fusion":
                cmd.append("--merge")
                fichiers = cfg.get("fusion_fichiers", [])
                if fichiers: cmd += ["--source"] + fichiers
                nom = cfg.get("nom", "fusion") or "fusion"
                # Extension du GeoJSON intermédiaire
                ext = ".geojson" if cfg.get("fusion_gz2_raw") and not cfg.get("fusion_gz2", True) else ".geojson.gz"
                # Dossier de sortie automatique : <Projets>/<nom>/fusion
                sortie_dir = _base_projets(cfg.get("dossier")) / nom / "fusion"
                cmd += ["--output-file", str(sortie_dir / f"{nom}_fusion{ext}")]
                fmts = []
                if cfg.get("fusion_gz2", True):   fmts.append("gz")
                if cfg.get("fusion_gz2_raw"):      fmts.append("geojson")
                if cfg.get("fusion_map"):          fmts.append("map")
                if cfg.get("fusion_transparent"):  fmts.append("transparent-raster")
                if not fmts: fmts = ["gz"]
                cmd += ["--file-formats"] + fmts
                if cfg.get("fusion_map") and cfg.get("simplif_fusion"):
                    cmd += ["--vector-simplify", str(cfg["simplif_fusion"])]

            # ── Découpage raster (à posteriori) ──────────────────────────
            elif t == "decoupe":
                cmd.append("--split")
                src_d = cfg.get("source_decoupe", "")
                if src_d: cmd += ["--source", src_d]
                if cfg.get("cols_decoupe_d", 0) > 0 and cfg.get("rows_decoupe_d", 0) > 0:
                    cmd += ["--cols", str(cfg["cols_decoupe_d"]),
                            "--rows", str(cfg["rows_decoupe_d"])]
                elif cfg.get("split_width_d", 0) > 0:
                    cmd += ["--split-width", str(cfg["split_width_d"])]
                fmts_d = []
                if cfg.get("mbtiles_d"):  fmts_d.append("mbtiles")
                if cfg.get("rmap_d"):     fmts_d.append("rmap")
                if cfg.get("sqlitedb_d"): fmts_d.append("sqlitedb")
                if fmts_d: cmd += ["--file-formats"] + fmts_d
                if cfg.get("ecraser_d"):  cmd.append("--tiles-overwrite")


            return cmd

        # ── Lancement ────────────────────────────────────────────────────
        def _kill_tree(self, proc):
            """Kill forcé de toute la hiérarchie du subprocess (Windows/Unix).
            Partagé par stop() (escalade après grâce) et launch() (relance
            après un Arrêter : l'intention utilisateur annule la grâce)."""
            try:
                if WINDOWS:
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass

        # Compte SSH d'administration et compte RDP créé sur la VM : fixés en
        # dur (pas de champ GUI). "root" est le défaut universel d'une VM
        # cloud neuve (Hetzner, etc.) ; "userlidar" est un nom de compte
        # interne créé à la volée par le script de déploiement, sans raison
        # de varier. Les exposer n'apportait rien (retour utilisateur
        # 2026-08-04) : qui a besoin d'un autre compte utilise directement
        # rlidar2map_CLI/rlidar2map_GUI en standalone (--ssh-user/--user).
        _REMOTE_SSH_USER = "root"
        _REMOTE_RDP_USER = "userlidar"

        def _wrap_remote_cmd(self, cmd, cfg):
            """Enveloppe `cmd` (sortie de _build_cmd) pour l'exécuter sur une VM
            via --remote-cli au lieu de localement. Le préfixe exécutable est
            conservé tel quel (frozen : 1 élément ; source : 2), --remote-cli et
            ses propres options s'insèrent juste après, puis `--` et les
            arguments lidar2map inchangés. Toujours --bundle (pas de choix
            source dans la GUI, comme --remote-gui qui n'en propose pas non
            plus) : qui veut --source utilise rlidar2map_CLI en standalone."""
            prefix_len = 1 if getattr(sys, "frozen", False) else 2
            prefix, lidar_args = cmd[:prefix_len], cmd[prefix_len:]
            remote_cmd = list(prefix) + ["--remote-cli", "--bundle"]
            if cfg.get("remote_session"):
                remote_cmd += ["--session", cfg["remote_session"]]
            _remote_mode = cfg.get("remote_mode")
            if _remote_mode == "restart":
                remote_cmd.append("--restart")
            elif _remote_mode == "resume":
                remote_cmd.append("--resume")
            if cfg.get("remote_identity"):
                remote_cmd += ["--identity", cfg["remote_identity"]]
            _sync_only = cfg.get("remote_sync_only")
            if _sync_only and _sync_only != "tout":
                remote_cmd += ["--sync-only", _sync_only]
            remote_cmd.append("{}@{}".format(self._REMOTE_SSH_USER, cfg["remote_host"]))
            remote_cmd.append("--")
            remote_cmd += lidar_args
            return remote_cmd

        def _build_remote_gui_cmd(self, cfg):
            """Construit la commande --remote-gui (bureau distant) : aucun des
            paramètres du formulaire (zone, type...) ne s'applique, seules les
            options de préparation de VM (rlidar2map_GUI) comptent."""
            cmd = ([str(SCRIPT)] if getattr(sys, "frozen", False)
                   else [sys.executable, str(SCRIPT)])
            cmd += ["--remote-gui", "--ip", cfg["remote_host"],
                    "--ssh-user", self._REMOTE_SSH_USER,
                    "--user", self._REMOTE_RDP_USER]
            if cfg.get("remote_identity"):
                cmd += ["--identity", cfg["remote_identity"]]
            return cmd

        def launch(self, cfg):
            # Décision de lancement sous verrou : lire l'état, tuer l'ancien run
            # si « Arrêter puis Lancer », puis poser _launching AVANT de rendre
            # la main. Le second clic d'un double-clic bloque sur ce verrou, le
            # relâche, voit _process vivant OU _launching → rejeté. Le Popen
            # lui-même est fait plus bas, SYNCHRONE (avant de lancer le thread
            # lecteur), pour que _process soit posé avant tout autre launch().
            with self._launch_lock:
                proc = self._process
                if proc and proc.poll() is None:
                    if self._stop_t is None:
                        return {"error": "Un processus est déjà en cours."}
                    # Arrêter PUIS Lancer = intention sans ambiguïté : ne pas faire
                    # attendre la grâce de 15 s à l'utilisateur (sinon « Un processus
                    # est déjà en cours » tant que l'arrêt gracieux n'a pas abouti).
                    # Escalade immédiate + courte attente de la mort effective.
                    self._kill_tree(proc)
                    try:
                        proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        return {"error": "Arrêt encore en cours, réessayez dans quelques secondes."}
                elif self._launching:
                    # Un lancement est déjà engagé mais le subprocess n'est pas
                    # encore créé (course double-clic) : rejeter comme un run actif.
                    return {"error": "Un processus est déjà en cours."}
                self._launching = True
            # Laisser le thread lecteur de l'ANCIEN run se terminer avant de
            # réinitialiser l'état : son finally pose _done=True et écraserait
            # le _done=False du nouveau run (course). Le pipe étant clos par la
            # mort du process, il sort en quelques ms.
            if self._reader_t and self._reader_t.is_alive():
                self._reader_t.join(timeout=5)
            self._stop_t = None
            remote_choix = cfg.get("remote_choix", "local")
            if remote_choix in ("cli", "gui") and not cfg.get("remote_host", "").strip():
                with self._launch_lock:
                    self._launching = False
                return {"error": "Hôte manquant pour l'exécution distante (ex. 192.0.2.10)."}
            if remote_choix == "gui":
                # Bureau distant : aucun argument lidar2map, _build_cmd ne
                # servirait à rien (cfg.type/zone n'ont pas été validés côté GUI).
                cmd = self._build_remote_gui_cmd(cfg)
            else:
                cmd = self._build_cmd(cfg)
                if remote_choix == "cli":
                    cmd = self._wrap_remote_cmd(cmd, cfg)
            self._done = False
            self._retcode = None
            self._t_launch = time.time()
            self._cfg_launch = cfg
            # run_id partagé GUI ↔ subprocess via env LIDAR2MAP_HIST_RUN_ID :
            # le subprocess sauve 'en cours' au début (crash-safe), puis 'ok'/'ko'
            # à la fin. poll_log côté GUI peut alors mettre à jour la MÊME entrée
            # avec le cfg complet (qui contient des champs absents de l'argv :
            # tel_v, ecraser_tel_v, etc.) pour rappel exact via loadConfig().
            self._hist_run_id = f"{int(time.time()*1000)}-{os.getpid()}-gui"
            self._hist_saved  = False
            if remote_choix == "gui":
                # Bureau distant : pas de livrable local, rien à ouvrir à la
                # fin (cfg.type/nom n'ont d'ailleurs pas été validés côté GUI,
                # un calcul ici serait arbitraire, cf. open_folder qui ouvrait
                # à tort Projets/ ou une racine sans rapport, bug vécu 2026-08-04).
                self._result_dir = None
            else:
                # Calculer le dossier résultat attendu
                t    = cfg.get("type", "lidar")
                nom  = cfg.get("nom", "")
                # Le pipeline CLI normalise le nom (slug ASCII minuscule) pour le
                # nom de dossier : "Garéoult" → "gareoult". Sans cette normalisation
                # ici, open_folder() pointerait vers un chemin inexistant.
                nom_slug = normaliser_nom(nom) if nom else ""
                base = Path(cfg["dossier"]) if cfg.get("dossier") else DOSSIER_TRAVAIL / "Projets"
                # Le subprocess utilise --provider <code> → ecrit dans lidar/<country>.
                # On reconstruit le meme path ici sinon open_folder pointe ailleurs.
                _cfg_provider = cfg.get("provider", PROVIDER.CODE)
                _cfg_country = "fr"
                for _p in _discover_providers():
                    if _p["code"] == _cfg_provider:
                        _cfg_country = _p.get("country", "fr")
                        break
                _lidar_subdir_cfg = f"lidar/{_cfg_country}"
                _type_dir = {"lidar":_lidar_subdir_cfg, "scan":"raster", "osm":"osm_vecteur",
                             "vecteur":"ign_vecteur", "fusion":"fusion", "decoupe":""}
                if t == "decoupe" and cfg.get("source_decoupe"):
                    self._result_dir = str(Path(cfg["source_decoupe"]).parent)
                elif cfg.get("dossier"):
                    # --output-dir explicite : chaque main CLI l'utilise comme racine
                    # DIRECTE (racine = args.dossier), sans sous-dossier <nom>/<type>.
                    # Sans ce cas, open_folder visait dossier/nom/type inexistant et
                    # l'explorateur ouvrait Mes Documents. Miroir du CLI, tous types.
                    self._result_dir = str(Path(cfg["dossier"]))
                else:
                    self._result_dir = str(base / nom_slug / _type_dir.get(t, t)) if nom_slug else str(base)
            while not self._log_queue.empty():
                try: self._log_queue.get_nowait()
                except queue.Empty: break

            # ── Création SYNCHRONE du subprocess ─────────────────────────────
            # Faite ici (avant de lancer le thread lecteur) pour que _process
            # soit posé avant que launch() rende la main : un second clic voit
            # alors proc.poll() vivant et est rejeté. Tant que Popen n'a pas
            # retourné, c'est _launching (posé plus haut, sous verrou) qui
            # fait barrage.
            self._log_queue.put(
                {"line": "$ " + _rediger_secrets(
                    " ".join(str(c) for c in cmd)) + "\n\n",
                 "tag": "dim"})
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            # Propager le run_id au subprocess pour qu'il sauve 'en cours'
            # SUR la même entrée que celle finalisée par poll_log côté GUI.
            env["LIDAR2MAP_HIST_RUN_ID"] = self._hist_run_id
            # Forcer UTF-8 sur stdout/stderr du child Python.
            # Sans ça, sur Windows le child utilise cp850 ou cp1252 par
            # défaut, et les caractères accentués (é, →, ⚠, ✓, etc.)
            # arrivent corrompus dans le pipe. Ça casse à la fois le
            # log lisible côté GUI ET la détection regex de mots-clés
            # comme "ERREUR" qui contient un É (devient un ? si décodé
            # en cp850 puis lu en utf-8).
            env["PYTHONIOENCODING"] = "utf-8"
            try:
                # Créer un nouveau groupe de processus pour pouvoir signaler
                # toute la hiérarchie (arrêt gracieux puis forcé, cf. stop()).
                if WINDOWS:
                    # CREATE_NEW_PROCESS_GROUP : indispensable pour envoyer
                    # CTRL_BREAK_EVENT au child (arrêt gracieux). La flag
                    # avait été retirée sur un soupçon de blocage du pipe
                    # stdout avec l'ancien backend WebView2 ; sous Qt
                    # (backend forcé depuis), le pipe fonctionne :
                    # revalidé par test dédié le 2026-07-02.
                    self._process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        bufsize=0, env=env,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    self._process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        bufsize=0, env=env,
                        start_new_session=True)
            except Exception as e:
                # Échec du spawn (binaire introuvable, argv trop long...) :
                # remonter l'erreur tout de suite ET lever le drapeau, sinon
                # _launching resterait True et bloquerait tout lancement futur.
                self._log_queue.put({"line": f"\nError: {e}\n", "tag": "err"})
                with self._lock:
                    self._retcode = -1
                self._done = True
                with self._launch_lock:
                    self._launching = False
                return {"error": f"Échec du lancement : {e}"}
            # subprocess vivant → le garde passe de _launching à proc.poll().
            with self._launch_lock:
                self._launching = False

            def run():
                try:
                    buf = ""
                    pct_re = re.compile(r"(\d+)%")
                    # Décodeur incrémental : les chunks de 64 octets peuvent
                    # couper une séquence UTF-8 multi-octets en deux ; un
                    # .decode() par chunk produisait des � sporadiques sur les
                    # accents (et pouvait casser _classify_err sur "ERREUR").
                    import codecs as _codecs
                    _dec = _codecs.getincrementaldecoder("utf-8")("replace")

                    def _emit_ligne(texte):
                        # Ligne complète → log GUI + buffers de diagnostic.
                        # Le run peut MODIFIER le nom de projet (le mode LAZ
                        # suffixe le nom de zone) : le chemin réel imprimé par
                        # le pipeline (« Done! Folder: … ») est la source de
                        # vérité et écrase le _result_dir précalculé — sinon
                        # open_folder ouvre l'ancien dossier (bug vécu
                        # 2026-07-16, même classe que le précédent bug country).
                        # "[VM]" exclu : c'est le journal DISTANT relayé par
                        # --remote-cli (print_remote_log_tail côté
                        # rlidar2map_CLI), son "Done! Folder:" pointe vers un
                        # chemin sur la VM, jamais valide en local (bug vécu
                        # 2026-08-04 : open_folder ouvrait /root/... sur
                        # Windows). Le cas distant est couvert juste après par
                        # "  local :", imprimé par rlidar2map_CLI lui-même.
                        if "Done! Folder:" in texte and "[VM]" not in texte:
                            _rd = texte.split("Done! Folder:", 1)[1].strip()
                            if _rd:
                                self._result_dir = _rd
                        # --remote-cli résume son run avec "  local : <racine
                        # du run>" (rlidar2map_CLI.print_remote_hints) ; les
                        # livrables synchronisés sont dans son sous-dossier
                        # results/ (cf. VmController.sync_once), jamais à la
                        # racine — sans le / "results", open_folder ouvrait le
                        # dossier du run, pas celui des fichiers.
                        elif "  local : " in texte:
                            _rd = texte.split("  local : ", 1)[1].strip()
                            if _rd:
                                self._result_dir = str(Path(_rd) / "results")
                        is_err = _classify_err(texte)
                        with self._lock:
                            if is_err and len(self._err_lines) < 20:
                                self._err_lines.append(texte.strip())
                            # Buffer circulaire des 10 dernières lignes
                            # non-vides : fallback si retcode≠0 sans
                            # ligne marquée "ERREUR".
                            self._tail_lines.append(texte.strip())
                            if len(self._tail_lines) > 10:
                                self._tail_lines.pop(0)
                        self._log_queue.put({"line": texte + "\n",
                                             "tag": "err" if is_err else "ok"})

                    # Reset des buffers de diagnostic (init dans __init__).
                    # Lock pour cohérence avec poll_log / get_last_error.
                    with self._lock:
                        self._err_lines  = []
                        self._tail_lines = []
                    saw_cr = False
                    for chunk in iter(lambda: self._process.stdout.read(64), b""):
                        for ch in _dec.decode(chunk):
                            if saw_cr:
                                # Décision DIFFÉRÉE sur le \r : sous Windows,
                                # CHAQUE print() termine par \r\n. Décider dès
                                # le \r (ancien code) détournait vers la barre
                                # de progression toute ligne de log contenant
                                # un % (bilans "100%", ligne warp), qui
                                # disparaissait alors du log GUI.
                                # \r suivi de \n = fin de ligne normale → log ;
                                # \r nu = repaint de barre de progression.
                                saw_cr = False
                                if ch == "\n":
                                    if buf.strip():
                                        _emit_ligne(buf)
                                    buf = ""
                                    continue
                                m = pct_re.search(buf)
                                if m and buf.strip():
                                    self._log_queue.put({"pct": int(m.group(1)),
                                                         "label": buf.strip()})
                                # Repaint sans % : remplacé par le suivant,
                                # comme sur un terminal (pas de concaténation).
                                buf = ""
                            if ch == "\r":
                                saw_cr = True
                            elif ch == "\n":
                                if buf.strip():
                                    _emit_ligne(buf)
                                buf = ""
                            else:
                                buf += ch
                    buf += _dec.decode(b"", True)   # flush décodeur (EOF)
                    # Drain final : la boucle for-chunk a vu EOF, mais le buffer
                    # interne `buf` peut contenir une dernière ligne sans \n
                    # final (ex : print() Python sans flush avant sys.exit).
                    # Sans ça, ces lignes sont perdues sur Windows quand le
                    # child exit en moins de 100ms.
                    if buf.strip():
                        _emit_ligne(buf)
                        buf = ""
                    self._process.wait()
                    with self._lock:
                        self._retcode = self._process.returncode

                    # Drain final post-wait : sur Windows, le pipe peut contenir
                    # encore des données après que le child ait exit. Sans ce
                    # drain, les dernières lignes (souvent les plus importantes :
                    # message d'erreur final + sys.exit(1)) sont perdues.
                    try:
                        remaining = self._process.stdout.read()
                        if remaining:
                            text = remaining.decode("utf-8", errors="replace")
                            for line in text.split("\n"):
                                line = line.rstrip("\r")
                                if not line.strip():
                                    continue
                                _emit_ligne(line)
                    except Exception:
                        # En cas d'erreur de lecture finale (pipe déjà fermé),
                        # on continue silencieusement avec ce qu'on a.
                        pass

                    sym = "✓" if self._retcode == 0 else "✗"
                    self._log_queue.put({"line": f"\n{sym} Terminé (code {self._retcode})\n",
                                         "tag": "ok" if self._retcode == 0 else "err"})
                    # Si échec : préparer le message modal récapitulatif.
                    # Priorité 1 : lignes marquées comme "ERREUR" (si détectées).
                    # Priorité 2 : 10 dernières lignes non-vides (fallback générique
                    # pour les cas où sys.exit(1) suit un print() libre que le filtre
                    # n'a pas reconnu comme erreur).
                    # On le stocke à la fois dans la queue ET sur l'instance, car
                    # les dictionnaires complexes peuvent être mal sérialisés par
                    # certaines versions de pywebview/WebView2.
                    with self._lock:
                        self._modal_error_msg = ""
                        if self._retcode != 0:
                            if self._err_lines:
                                modal_lines = self._err_lines[-10:]
                            elif self._tail_lines:
                                modal_lines = self._tail_lines[-10:]
                            else:
                                modal_lines = [
                                    f"Le traitement a échoué (code {self._retcode})",
                                    "Aucun message d'erreur n'a été capturé.",
                                    "Vérifiez le panneau de log pour les détails.",
                                ]
                            self._modal_error_msg = "\n".join(modal_lines)
                            _modal_payload = {
                                "modal_error": self._modal_error_msg,
                                "retcode":     self._retcode,
                            }
                        else:
                            _modal_payload = None
                    if _modal_payload is not None:
                        self._log_queue.put(_modal_payload)
                    # Marquer la durée pour la sauvegarde historique (faite
                    # dans poll_log). Mesuré dans tous les cas — y compris
                    # échec — pour que l'entrée 'ko' soit horodatée correctement.
                    self._duree_run = int(time.time() - getattr(self, "_t_launch", time.time()))
                except Exception as e:
                    self._log_queue.put({"line": f"\nError: {e}\n", "tag": "err"})
                    with self._lock:
                        self._retcode = -1
                finally:
                    self._done = True

            self._reader_t = threading.Thread(target=run, daemon=True)
            self._reader_t.start()
            return {"cmd": " ".join(str(c) for c in cmd)}

        def _stop_remote_run(self, purge_remote=False):
            """Arrête le calcul VM associé au subprocess de surveillance."""
            cfg = getattr(self, "_cfg_launch", {}) or {}
            if cfg.get("remote_choix") != "cli":
                return {"ok": False, "error": "Le traitement courant n'est pas un calcul VM."}
            argv = ["--session", cfg.get("remote_session") or "lidar", "--stop"]
            if cfg.get("remote_identity"):
                argv += ["--identity", cfg["remote_identity"]]
            argv.append("{}@{}".format(self._REMOTE_SSH_USER, cfg.get("remote_host", "")))
            stopped = False
            try:
                remote_cli = _import_patchable_source_module(
                    "tools", "rlidar2map_CLI")
                controller = remote_cli.VmController(
                    remote_cli.parse_options(argv))
                stopped = controller.stop_remote()
                purged = False
                if purge_remote:
                    state = controller.query_state()
                    if state.exists:
                        if not state.terminal or state.tmux:
                            raise RuntimeError(
                                "la session est encore active après la demande d'arrêt"
                            )
                        controller.purge_remote(state)
                        purged = True
                if stopped:
                    self._log_queue.put({
                        "line": "\n⚠ Traitement arrêté sur la VM.\n", "tag": "err"
                    })
                else:
                    self._log_queue.put({
                        "line": "\n⚠ Aucun traitement actif sur la VM.\n", "tag": "err"
                    })
                if purged:
                    self._log_queue.put({
                        "line": "⚠ Fichiers de la session supprimés sur la VM.\n",
                        "tag": "err",
                    })
                return {"ok": True, "stopped": stopped, "purged": purged}
            except BaseException as exc:
                # argparse lève SystemExit (BaseException) si une session saisie
                # dans le GUI est invalide ; la convertir en erreur du bridge.
                message = str(exc) or exc.__class__.__name__
                self._log_queue.put({
                    "line": "\n✗ Arrêt sur la VM impossible : {}\n".format(message),
                    "tag": "err",
                })
                return {"ok": False, "stopped": stopped, "error": message}

        def stop(self, stop_remote=False, purge_remote=False):
            """Arrêt gracieux, puis forcé.

            1. Signal doux : CTRL_BREAK au groupe Windows (routé vers le
               soft-cancel _on_sigint du child : l'opération courante finit
               proprement, manifeste/.part/sqlite fermés), SIGINT au groupe
               Unix. L'ancien comportement (taskkill /F immédiat) coupait
               net sans aucun cleanup.
            2. Si le child vit encore après _STOP_GRACE_S (kernel numba
               intuable, child sans console où CTRL_BREAK échoue), kill
               forcé de toute la hiérarchie, comme avant.
            L'escalade tourne dans un thread pour ne pas bloquer le bridge
            JS ; _done est posé par le thread lecteur quand le pipe se ferme.
            """
            remote_result = None
            if stop_remote:
                # Faire l'appel SSH avant de couper le contrôleur local : cette
                # méthode ne rend la main qu'une fois le process VM réellement
                # sorti (ou forcé), et peut encore consigner le résultat au log.
                remote_result = self._stop_remote_run(bool(purge_remote))

            _STOP_GRACE_S = 15
            proc = self._process
            if not (proc and proc.poll() is None):
                return remote_result
            self._stop_t = time.time()   # lu par launch() : relance = escalade immédiate
            self._log_queue.put(
                {"line": f"\n⚠ Stop requested - graceful, forced after {_STOP_GRACE_S} s\n",
                 "tag": "err"})
            doux_ok = False
            try:
                if WINDOWS:
                    proc.send_signal(_signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(os.getpgid(proc.pid), _signal.SIGINT)
                doux_ok = True
            except Exception:
                pass

            def _escalade():
                try:
                    proc.wait(timeout=_STOP_GRACE_S if doux_ok else 0.1)
                    return   # sortie propre : le thread lecteur finalise (_done)
                except subprocess.TimeoutExpired:
                    pass
                self._kill_tree(proc)
                self._log_queue.put({"line": "\n⚠ Forced stop\n", "tag": "err"})
            threading.Thread(target=_escalade, daemon=True).start()
            return remote_result

        def check_update(self):
            """Compare la dernière release GitHub à la version locale.

            Appelé par le JS après l'init (non bloquant côté UI) ; silencieux
            et {"update": False} sur toute erreur (hors ligne, rate-limit de
            l'API GitHub, JSON inattendu). Une requête, timeout court.
            """
            try:
                with _urlopen("https://api.github.com/repos/nico579/lidar2map"
                              "/releases/latest", timeout=6) as r:
                    d = json.loads(r.read())
                tag = str(d.get("tag_name") or "")

                def _triplet(v):
                    n = re.findall(r"\d+", v)
                    return tuple(int(x) for x in n[:3]) if n else (0,)

                if tag and _triplet(tag) > _triplet(VERSION):
                    return {"update": True, "latest": tag,
                            "url": d.get("html_url") or
                                   "https://github.com/nico579/lidar2map/releases/latest"}
            except Exception:
                pass
            return {"update": False}

        def open_url(self, url):
            """Ouvre une URL dans le navigateur système (bandeau update).
            Restreinte au repo du projet : le bridge JS ne doit pas pouvoir
            ouvrir des URLs arbitraires."""
            try:
                if str(url).startswith("https://github.com/nico579/lidar2map"):
                    import webbrowser
                    webbrowser.open(url)
            except Exception:
                pass

        def open_folder(self, path):
            try:
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", Path(path).resolve()])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            except Exception:
                pass

        def get_last_error(self):
            """Retourne le message d'erreur du dernier run (ou chaîne vide).

            Permet au JS de récupérer ce message **après** avoir constaté
            que `done=True && code!=0`, sans dépendre de la transmission par
            la queue (que pywebview/WebView2 sérialise parfois mal pour les
            dicts à plusieurs clés).

            Lecture sous lock pour voir un snapshot cohérent (msg + retcode
            écrits ensemble dans run()).
            """
            with self._lock:
                return {
                    "msg":     getattr(self, "_modal_error_msg", "") or "",
                    "retcode": getattr(self, "_retcode", 0) or 0,
                }

        def poll_log(self):
            items = []
            try:
                while True:
                    items.append(self._log_queue.get_nowait())
            except queue.Empty:
                pass
            # Sauvegarde finale de l'historique côté GUI (thread-safe via
            # poll_log). MET À JOUR l'entrée 'en cours' créée par le subprocess
            # via le même run_id (env LIDAR2MAP_HIST_RUN_ID). Sauvegarde sur
            # succès ET échec : sans ça, un crash du pipeline laissait l'entrée
            # 'en cours' indéfiniment.
            if self._done and not getattr(self, "_hist_saved", False):
                self._hist_saved = True
                try:
                    _duree  = getattr(self, "_duree_run", 0) or \
                              int(time.time() - getattr(self, "_t_launch", time.time()))
                    _statut, _result = _bilan_historique_processus(
                        self._retcode, getattr(self, "_result_dir", ""))
                    _sauver_historique(
                        getattr(self, "_cfg_launch", {}),
                        _duree,
                        _result,
                        run_id=getattr(self, "_hist_run_id", ""),
                        statut=_statut,
                    )
                    items.append({"line": f"  History saved: {_HISTORIQUE_PATH}\n",
                                  "tag": "ok"})
                except Exception as _he:
                    items.append({"line": f"  History error: {_he}\n", "tag": "err"})

            result_dir = getattr(self, "_result_dir", None) if (self._done and self._retcode == 0) else None
            return {"items": items, "done": self._done, "code": self._retcode,
                    "result_dir": result_dir}

    # Front-end (HTML/CSS/JS) extrait dans gui/ : index.html + style.css + app.js.
    # pywebview charge une CHAINE HTML (html=), pas une URL : on reassemble les 3
    # fichiers ici via les sentinelles d'insertion. Les data Python passent par la
    # classe Api (js_api), pas par interpolation, donc le front reste statique.
    _gui_dir = None
    _bases = [BUNDLE_DIR]                      # frozen : _MEIPASS/gui (onedir + onefile)
    if "__file__" in globals():               # source : a cote de lidar2map.py
        _bases.append(Path(__file__).resolve().parent)
    _bases.append(Path(sys.argv[0]).resolve().parent)
    for _base in _bases:
        if (_base / "gui" / "index.html").exists():
            _gui_dir = _base / "gui"
            break
    if _gui_dir is None:
        raise RuntimeError("GUI : gui/index.html introuvable (assets non bundles ?)")
    HTML = (_gui_dir / "index.html").read_text(encoding="utf-8")
    HTML = HTML.replace("/*__LIDAR2MAP_CSS__*/",
                        (_gui_dir / "style.css").read_text(encoding="utf-8"))
    HTML = HTML.replace("//__LIDAR2MAP_JS__",
                        (_gui_dir / "app.js").read_text(encoding="utf-8"))

    api = Api()

    # Muselle l'avertissement bénin de fermeture QtWebEngine
    # ("Release of profile requested but WebEnginePage still not deleted").
    # (PYWEBVIEW_GUI=qt est déjà posé avant `import webview`, dans lancer_gui.)
    if platform.system() in ("Windows", "Linux"):
        try:
            from PyQt6 import QtCore as _QtCore
            _QT_NOISE = ("WebEnginePage still not deleted",
                         "Release of profile requested")

            def _qt_msg_filter(_mode, _ctx, _msg):
                if any(_n in _msg for _n in _QT_NOISE):
                    return
                try:
                    sys.stderr.write(str(_msg) + "\n")
                except Exception:
                    pass

            _QtCore.qInstallMessageHandler(_qt_msg_filter)
        except Exception:
            pass

    # Taille initiale bornée à l'écran : sous Qt + DPI, une hauteur fixe peut
    # dépasser un écran de portable -> fenêtre hors écran. On clampe sur la
    # zone de travail (hors barre des tâches) sous Windows. Redimensionnable.
    _w, _h = 1300, 1000
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            _r = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(_r), 0)  # SPI_GETWORKAREA
            _wa_w, _wa_h = _r.right - _r.left, _r.bottom - _r.top
            if _wa_h > 0:
                # REMPLIR la zone de travail (moins une marge) dans les DEUX
                # dimensions, au lieu de plafonner à une taille fixe. La hauteur
                # bloquée à 850 laissait un ascenseur vertical ; la largeur
                # bloquée à 1300 laissait du vide à droite ET faisait passer les
                # longues lignes (Projet, Zone) à la ligne, ce qui RAJOUTAIT de
                # la hauteur → scroll. Plus large = les lignes tiennent d'un
                # trait = contenu plus court. Cap à 2200 pour ne pas étirer
                # absurdement une fenêtre sur écran ultra-large.
                _h = max(600, _wa_h - 48)
                _w = max(1000, min(2200, _wa_w - 48))
    except Exception:
        pass

    win = webview.create_window(
        f"lidar2map v{VERSION} — Cartes offline LiDAR / raster / OSM",
        html=HTML,
        js_api=api,
        width=_w, height=_h,
        min_size=(1000, 600),
        # Zoom géré en JS (applyUiZoom : Ctrl+molette / Ctrl+± / Ctrl+0) pour
        # pouvoir le PERSISTER (preferences.json). zoomable natif désactivé,
        # sinon les deux zooms se cumuleraient.
        zoomable=False,
    )
    # Assigner la fenêtre immédiatement — disponible dès create_window
    api.window = win

    def _au_close():
        """Fermeture de la fenêtre : extinction garantie de tout l'arbre.

        Accroché à l'événement pywebview `closed`, qui se déclenche AVANT le
        teardown Qt. Indispensable : sous Qt/QtWebEngine, le teardown peut
        fail-faster le process (STATUS_FAIL_FAST observé) sans que
        webview.start() ne retourne, donc tout code placé après start() n'est
        pas fiable. Sans ce handler : (1) un run CLI actif continuait en
        headless, sans log ni stop ; (2) le process GUI pouvait survivre à la
        fenêtre (zombies python + QtWebEngineProcess à tuer à la main).
        """
        try:
            proc = getattr(api, "_process", None)
            if proc and proc.poll() is None:
                print("  Window closed - stopping the running job...", flush=True)
                api.stop()            # doux (CTRL_BREAK/SIGINT), escalade 15 s
                try:
                    proc.wait(timeout=20)   # laisser l'escalade aboutir
                except Exception:
                    pass
        except Exception:
            pass
        print("  GUI window closed - exiting.", flush=True)
        # Publier le log AVANT le os._exit ci-dessous : lui saute aussi les
        # handlers atexit (dont celui qui renomme <log>.part -> <log>), donc
        # sans cet appel explicite le fichier restait bloqué en .part à
        # chaque fermeture normale de la fenêtre (vécu 2026-08-05 : 4/4 logs
        # GUI orphelins, tous terminés proprement sur ce même message). Pur
        # I/O Python (flush + close + rename) : aucun risque de réintroduire
        # le fail-fast Qt que os._exit évite.
        try:
            if isinstance(sys.stdout, _TeeLogger):
                sys.stdout.close()
        except Exception:
            pass
        # os._exit : sortie inconditionnelle AVANT le teardown Qt (évite le
        # fail-fast et les threads non-daemon qui retiennent le process).
        # Les écritures critiques (historique, préférences) sont atomiques
        # et posées au fil de l'eau.
        os._exit(0)

    win.events.closed += _au_close

    # Activable via flag --debug (clic droit → Inspect dans la fenêtre webview,
    # ou F12, pour ouvrir les DevTools et voir la console JS).
    _wv_debug = "--debug" in sys.argv
    webview.start(debug=_wv_debug)

    # Filet de sécurité : si l'événement `closed` n'a pas été délivré (backend
    # exotique) mais que start() retourne, on passe par le même chemin.
    _au_close()


def _normaliser_argv_valeurs_negatives():
    """Recolle les valeurs négatives à leur flag pour qu'argparse les accepte.

    Argparse considère par défaut tout token commençant par '-' comme un nouveau
    flag, ce qui casse les commandes du type :
        --zone-bbox -108.5,37.18,-108.48,37.20
    car '-108.5,...' est vu comme un flag inconnu.

    Solution : pour chaque flag connu qui prend une valeur, si le token suivant
    commence par '-' et contient une virgule (pattern typique bbox/gps), on
    fusionne avec '=' (forme acceptée nativement par argparse).
    """
    FLAGS_VALEUR = (
        "--zone-bbox", "--zone-gps",
        "--bbox",   # alias historique éventuels
    )
    out = []
    i = 0
    while i < len(sys.argv):
        tok = sys.argv[i]
        if (tok in FLAGS_VALEUR and i + 1 < len(sys.argv)
                and sys.argv[i + 1].startswith("-")
                and "," in sys.argv[i + 1]):
            out.append(f"{tok}={sys.argv[i + 1]}")
            i += 2
        else:
            out.append(tok)
            i += 1
    sys.argv = out


if __name__ == "__main__":
    try:
        _normaliser_argv_valeurs_negatives()
        # --debug (DevTools WebView2) est un flag GUI-only. On le détecte tôt
        # pour qu'il ne perturbe pas argparse en aval (qui ne le reconnaît pas).
        # Lu directement dans sys.argv par lancer_gui() avant strip.
        _is_only_debug = (len(sys.argv) == 2 and sys.argv[1] == "--debug")
        if len(sys.argv) == 1 or _is_only_debug:
            lancer_gui()
        else:
            # ── Détection du mode via un PRÉ-PARSER argparse ──────────────────
            # Au lieu de `if "--decouper" in sys.argv: ...` (grep, susceptible
            # de matcher dans la valeur d'un autre argument), on utilise un
            # parser dédié à 1 seul argument actif à la fois. Les flags d'origine
            # sont préservés tels quels (compat ascendante des commandes
            # partagées sur les forums).
            #
            # Note : `argparse` avec parse_known_args() consomme uniquement le
            # mode et laisse intact le reste de sys.argv pour le sub-main.
            _DISPATCH = {
                # mode_key: (sous-main, [flags reconnus : anglais canonique + alias FR])
                "serve":      (main_serve,     ["--serve"]),
                "decouper":   (main_decouper,  ["--split", "--decouper"]),
                "ignraster":  (main_wmts,      ["--raster", "--ignraster"]),
                "ignvecteur": (main_wfs,       ["--vector", "--ignvecteur"]),
                "fusionner":  (main_fusionner, ["--merge", "--fusionner"]),
                # Tous les autres modes (--lidar/--ignlidar, --osm, ou cumulés)
                # tombent sur main() qui sait les gérer.
            }
            _pre = argparse.ArgumentParser(add_help=False)
            for _key, (_fn, _flags) in _DISPATCH.items():
                _pre.add_argument(*_flags, action="store_true",
                                  dest=f"_mode_{_key}")
            # Mode standalone : (re)générer la planche d'assemblage d'un dossier
            # projet existant, sans rejouer le traitement. Balaie les livrables.
            # Anglais canonique + alias FR, comme tous les flags (--split/--decouper).
            _pre.add_argument("--index-sheet", "--planche", dest="_planche_dir",
                              default=None)
            _ns_pre, _ = _pre.parse_known_args()
            if getattr(_ns_pre, "_planche_dir", None):
                _planche_depuis_dossier(
                    _ns_pre._planche_dir,
                    argparse.Namespace(index_map=True, zone_departement=None))
                sys.exit(0)

            def _dispatch():
                # Priorité ordonnée : on prend le 1er mode trouvé dans la liste.
                # Cet ordre matche celui de l'ancien dispatcher (decouper avant
                # ignraster, etc.) pour préserver le comportement.
                for _key, (_fn, _flags) in _DISPATCH.items():
                    if getattr(_ns_pre, f"_mode_{_key}", False):
                        return _fn()
                return main()    # --lidar / --osm / par défaut

            # ── Résolution multi-département ─────────────────────────────────
            # --zone-departement accepte : 83 | 30,35,75 | 1-10 | 1-3,75,83
            # Normaliser la forme accolée --zone-departement=X en deux tokens :
            # le scan + la réécriture par dépt supposent un token valeur séparé.
            # Sans ça, `--zone-departement=1-3` n'est jamais expansé (silencieux)
            # → argparse met "1-3" tel quel → geocoder_departement échoue.
            # Idem --zone-nom/--zone-name : le suffixage _<dep> ci-dessous
            # suppose un token valeur séparé.
            # Transparent pour argparse, qui accepte déjà les deux formes.
            _argv_norm = []
            for _a in sys.argv:
                if _a.startswith(("--zone-departement=", "--zone-department=",
                                  "--zone-nom=", "--zone-name=")):
                    _k, _v = _a.split("=", 1)
                    _argv_norm += [_k, _v]
                else:
                    _argv_norm.append(_a)
            sys.argv = _argv_norm
            _dep_idx = None
            for _i, _a in enumerate(sys.argv):
                if _a in ("--zone-departement", "--zone-department") and _i + 1 < len(sys.argv):
                    _dep_idx = _i + 1
                    break

            _deps = _parser_departements(sys.argv[_dep_idx]) if _dep_idx else None

            if _deps and len(_deps) > 1:
                _argv_base = sys.argv[:]
                _batch_t_debut = time.time()
                _sep = "═" * 55
                # Détecter --zone-nom explicite : sera suffixé par _<dep> pour éviter
                # que les sorties multi-département s'écrasent mutuellement.
                _nom_idx = None
                _nom_base = None
                for _i, _a in enumerate(_argv_base):
                    # Les deux orthographes du flag (l'ancien code ne testait
                    # que --zone-nom : avec --zone-name, les sorties des
                    # départements s'écrasaient mutuellement).
                    if _a in ("--zone-nom", "--zone-name") and _i + 1 < len(_argv_base):
                        _nom_idx  = _i + 1
                        _nom_base = _argv_base[_nom_idx]
                        break
                _deps_ko = []
                for _n, _dep in enumerate(_deps, 1):
                    print()
                    print(_sep)
                    print(f"  Department {_dep}  ({_n}/{len(_deps)})")
                    print(_sep)
                    sys.argv = _argv_base[:]
                    sys.argv[_dep_idx] = _dep
                    # Suffixer le nom explicite avec le numéro de département
                    if _nom_idx is not None:
                        sys.argv[_nom_idx] = f"{_nom_base}_{_dep}"
                    try:
                        _dispatch()
                    except Exception as _e_dep:
                        # SystemExit (garde-fou disque, EXIT_DISK_LOW) et
                        # KeyboardInterrupt dérivent de BaseException → NON captés
                        # ici : ils arrêtent tout proprement. Seules les vraies
                        # erreurs de traitement (Overpass HS, échec d'un dépt…)
                        # sont absorbées → on logge et on continue (fire-and-forget).
                        # Reprise idempotente via le manifeste chunk-level.
                        _deps_ko.append(_dep)
                        print(f"  ✗ Department {_dep} failed: "
                              f"{type(_e_dep).__name__}: {_e_dep}, continuing.")
                if _deps_ko:
                    print(f"\n  ⚠ Failed departments: {','.join(_deps_ko)} "
                          f"(rerun the command to retry them)")
                    # Le dernier département réussi a pu remettre le même
                    # run_id à ``ok``. Restaurer l'argv agrégé puis imposer le
                    # bilan global avant le SystemExit non nul.
                    sys.argv = _argv_base[:]
                    _historique_fin_batch_ko(_batch_t_debut)
                    # Code non-zéro : sans lui, GUI/scripts/CI voyaient un
                    # succès (exit 0) malgré des départements en échec.
                    sys.exit(1)
            else:
                # Mono-département : réécrire l'argv avec le code normalisé
                # (5 → 05, 2a → 2A), sinon geocoder_departement interroge INSEE
                # avec un code non paddé qui ne matche pas. Cohérent avec le
                # chemin multi qui réécrit déjà sys.argv[_dep_idx]=_dep.
                if _deps:
                    sys.argv[_dep_idx] = _deps[0]
                _dispatch()
    except KeyboardInterrupt:
        # Cancellation propre : raisée par print_etape() ou _svf_numpy()
        # quand _stop_event a été set par Ctrl+C. Le finally restaure stdout
        # avant que Python imprime un message synthétique.
        _historique_fin_crash()   # marque l'entrée 'en cours' comme 'ko'
        print("\n\n  Processing interrupted by the user.", flush=True)
        sys.exit(130)
    except SystemExit as _e_sysexit:
        # sys.exit() avec code != 0 = échec → marquer l'entrée 'en cours' 'ko'.
        # (code 0 ou None = succès → ne rien faire ; succès est déjà géré par
        # _historique_depuis_argv dans chaque main_*())
        if _e_sysexit.code not in (None, 0):
            _historique_fin_crash()
        raise
    except BaseException:
        # Toute autre exception non rattrapée par les main_*() : marquer 'ko'
        # avant de laisser Python imprimer la traceback.
        _historique_fin_crash()
        raise
    finally:
        if isinstance(sys.stdout, _TeeLogger):
            _tee = sys.stdout
            _tee.close()
            sys.stdout = getattr(_tee, "_terminal", None) or sys.__stdout__
            # stderr pointe sur le MÊME tee (cf. _activer_log) : le laisser
            # sur un log fermé avalerait les messages de shutdown de Python.
            if sys.stderr is _tee:
                sys.stderr = sys.__stderr__
