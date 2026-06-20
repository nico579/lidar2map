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

Script unifié 5 modes pour Locus Map / OsmAnd / TwoNav.
Plateformes : Windows 10+, macOS 11+, Linux (Debian/Ubuntu testés).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONCEPT ET WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Les 4 types de cartes sont INDÉPENDANTS et complémentaires :

  ① LiDAR MNT   Fond principal d'analyse archéologique. On commence par
                 ici : téléchargement des dalles, calcul des ombrages
                 (multi-directionnel, SVF, LRM, RRIM…), export en MBTiles.
                 On expérimente dans Locus, on identifie les manques.

  ② IGN Raster  Fond alternatif ou de recalage (Scan 25, orthophotos…).
                 Peut remplacer le LiDAR quand les données manquent, ou
                 servir de fond de référence topographique pour compléter
                 l'analyse. Se superpose aux overlays vectoriels.

  ③ IGN Vecteur Overlay de précision : cadastre, hydrographie, chemins…
                 Téléchargé en GeoJSON, chargé en superposition dans Locus
                 sur le fond LiDAR ou IGN Raster pour enrichir l'analyse.

  ④ OSM Vecteur Overlay polyvalent : routes, cours d'eau, patrimoine…
                 Généré en Mapsforge (.map) et/ou GeoJSON, utilisable en
                 superposition sur n'importe quel fond raster.

  ⑤ Fusion      Outil utilitaire : fusionne plusieurs GeoJSON (IGN + OSM)
                 en un seul overlay unifié avec traçabilité de la source.

  Flux typique :
    1. Générer le LiDAR → charger dans Locus
    2. Selon les besoins : ajouter overlay IGN Vecteur et/ou OSM
    3. Si couverture LiDAR insuffisante : générer IGN Raster (Scan 25/Ortho)
    4. Fusionner les GeoJSON si besoin d'un overlay unique combiné

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --ignlidar      Dalles LiDAR HD IGN (WMS) → ombrages → MBTiles/RMAP/SQLiteDB
  --ignraster     Tuiles WMTS IGN (Scan 25, Ortho…) → MBTiles/RMAP/SQLiteDB
  --ignvecteur    WFS IGN (cadastre, hydrographie…) → GeoJSON(.gz)
  --osm           PBF Geofabrik → carte Mapsforge (.map) + GeoJSON(.gz)
  --fusionner     Fusion de GeoJSON/GeoJSON.gz en un seul fichier

  Sans argument   → GUI pywebview (interface HTML/JS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ZONE GÉOGRAPHIQUE (commune à tous les modes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --zone-ville NOM            Géocodage Nominatim (ex: gareoult)
  --zone-gps   LAT,LON        Coordonnées WGS84  (ex: 43.3156,6.0423)
  --zone-bbox  W,S,E,N        BBox WGS84 en degrés
  --zone-departement NUM      Department français (ex: 83)
  --zone-rayon KM             Rayon autour du point (défaut: 10)
  --zone-nom   NOM            Nom du dossier de sortie (ex: aa)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FORMATS DE SORTIE (communs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  --formats-fichier FMT...    Formats de fichiers de sortie (multi-valeurs) :
                                ignlidar/ignraster : mbtiles rmap sqlitedb
                                osm                : map geojson gz
                                ignvecteur/fusion  : geojson gz
  --formats-image   FMT       Format des images dans les tuiles (ignlidar/ignraster) :
                                auto (défaut) | jpeg | png
  --qualite-image   Q         Qualité JPEG des images (1-100, défaut: 85)
                                75 = -35% taille, quasi invisible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignlidar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Pipeline :
    1. Dalles IGN LiDAR HD (WMS, cache permanent dans --dossier-dalles)
       → dalles_zone.txt (liste bbox-versionnée, reconstruite si zone change)
    2. gdalbuildvrt → VRT global temporaire (EPSG:2154, < 1 s)
    3. gdaldem / numpy/scipy → TIF ombrages (étape "ombrage")
       → <nom>_multi_ombrage.tif, <nom>_slope_ombrage.tif…
    4. gdalwarp + gdaladdo + tuilage Pillow → MBTiles/RMAP/SQLiteDB
       → <nom>_multi_ombrage_tuilage_z18.tif (cache Mercator, réutilisable)
       → <nom>_multi_ombrage_z8-18.mbtiles
       → <nom>_multi_ombrage_z8-18.rmap
       → <nom>_multi_ombrage_z8-18.sqlitedb

  Paramètres spécifiques :
    --telechargement            Télécharger les dalles manquantes
    --telechargement-forcer     Re-télécharger même les dalles existantes
    --telechargement-compresser Compresser les dalles téléchargées (DEFLATE)
    --dossier-dalles CHEMIN     Cache dalles séparé (défaut: ign_lidar/dalles/)
    --workers N                 Connexions parallèles (défaut: 8)
    --ombrages TYPE...          Shadings to generate:
                                  315 045 135 225 multi slope svf opos oneg
                                  lrm rrim | tous | aucun
                                  (opos/oneg = openness ± Yokoyama 2002,
                                   rayon --svf-dist, gamma --svf-gamma)
    --shading TYPE[:k=v,...]    Instance d'ombrage PARAMÉTRÉE, répétable —
                                  permet plusieurs instances du même type :
                                  --shading svf:dist=20 --shading svf:dist=100
                                  --shading oneg:gamma=1.5 --shading lrm:sigma=10
                                  Params : elevation (directionnels/multi),
                                  conv/dist/gamma (svf), dist/gamma (opos/oneg),
                                  sigma en m (lrm/rrim). Les params explicites
                                  sont encodés dans le nom de fichier.
    --svf-conv flux|rvt         Convention SVF (flux cos²γ / rvt 1−sin γ ; déf. flux)
    --svf-dist M                Rayon SVF en mètres, 10–200 (déf. 20)
    --svf-sweep / --no-svf-sweep  Kernel sweep-horizon SVF (déf. activé)
    --ombrages-elevation DEG    Angle solaire en degrés (défaut: 25)
    --svf-gamma G               Gamma du SVF (défaut: 2.0 ; <1 éclaircit, >1 assombrit)
    --ombrages-compresser       Compresser les TIF ombrages existants (DEFLATE)
    --zoom-min N                Zoom minimum MBTiles (défaut: 13 — inclut z8-12 via --zoom-min 8)
    --zoom-max N                Zoom maximum MBTiles (défaut: 18)
    --cols-decoupe N            Découpe le MBTiles final en N colonnes (avec --rows-decoupe)
    --rows-decoupe N            Découpe le MBTiles final en N lignes   (avec --cols-decoupe)
    --rayon-decoupe KM          Alternative : découpe en carrés de ~KM km
    --source CHEMIN             Source alternative :
                                  .tif   → ombrage existant → tuilage direct
                                  .mbtiles → conversion → RMAP/SQLiteDB
    --osm                       Générer overlay OSM vectoriel (standalone ou après LiDAR)

  Arborescence de sortie :
    Projets/<nom>/
      ign_lidar/
        dalles_zone.txt             liste dalles (# bbox:x1,y1,x2,y2 en tête)
        manifeste.json              état de reprise (découpage à priori)
        <nom>_multi_ombrage.tif     ombrage L93, 0.5 m/px
        <nom>_multi_ombrage_tuilage_z18.tif  cache Mercator (réutilisable)
        <nom>_multi_ombrage_z8-18.mbtiles
        <nom>_multi_ombrage_z8-18.rmap
        <nom>_multi_ombrage_z8-18.sqlitedb
    cache/ign_lidar/                cache dalles IGN permanent (partagé)

  Temps indicatifs (zone 4 km², i3-8130U) :
    Téléchargement (9-12 dalles)       : ~30 s
    Ombrage multi (gdaldem)            : ~5-10 s
    Ombrage SVF (numpy, 4 km²)         : ~5 min
    Ombrage LRM (scipy)                : ~2 min
    Ombrage RRIM (slope + LRM)         : ~8 min
    MBTiles z8-18 (495 tuiles)         : ~5 s
    MBTiles z8-18 (zone 400 km²)       : ~5-10 min

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignraster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Télécharge des tuiles WMTS IGN dans un MBTiles.
  Sortie dans Projets/<nom>/raster/. Cache permanent : cache/ign_raster/<z>/<x>/<y>.<ext>.

  Couches disponibles :
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
    --rayon-decoupe KM  Alternative : découpe en carrés de ~KM km
    --source CHEMIN     .mbtiles existant → conversion RMAP/SQLiteDB directe

  Arborescence de sortie :
    Projets/<nom>/
      raster/
        <nom>_scan25_z8-18.mbtiles
        <nom>_scan25_z8-18.rmap
        <nom>_scan25_z8-18.sqlitedb
    cache/ign_raster/               cache tuiles WMTS permanent (partagé)

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
    --formats-fichier   geojson | gz (défaut: gz)

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
    --formats-fichier   map geojson gz (défaut: map gz)

  Arborescence de sortie :
    osm_vecteur/
      provence-alpes-cote-d-azur-latest.osm.pbf   (cache régional)
      <nom>/
        <nom>.map                  carte Mapsforge
        <nom>_filtered.pbf         PBF filtré (réutilisable)
        <nom>_osm.geojson.gz       GeoJSON de superposition

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
  --nettoyage           Supprimer les fichiers intermédiaires après chaque
                          morceau (dalles, TIF ombrages, TIF warpé).
                          Conserve les sorties finales (.mbtiles .rmap .sqlitedb).
                          Indispensable pour les grandes zones (département entier).
  --version             Afficher la version

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GUI (mode interactif sans arguments)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Lancer sans argument : python lidar2map.py
  Onglets : LiDAR MNT, IGN Raster, IGN Vecteur, OSM Vecteur, Fusion, Découpage.

  Fonctionnalités :
    • Historique : 50 dernières commandes, rappel par clic, vidable
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
                 Windows : WebView2 natif (préinstallé Win10+)
                 macOS   : PyQt6 + PyQt6-WebEngine + qtpy (auto-installés)
                           pyobjc-framework-WebKit (backend natif, optionnel)
                 Linux   : PyQt6 + PyQt6-WebEngine + qtpy (auto-installés via pip)
                           Pré-requis système (Ubuntu/Debian, une seule fois) :
                             sudo apt install python3-venv
                           voir messages au démarrage si import échoue)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXEMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # Mode GUI
  python lidar2map.py

  # LiDAR : zone 1 km, ombrage multi, MBTiles + RMAP + SQLiteDB
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 1 \
      --zone-nom aa --telechargement --ombrages multi \
      --formats-fichier mbtiles rmap sqlitedb --zoom-min 8 --zoom-max 18

  # LiDAR : zone 10 km, plusieurs ombrages
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 10 \
      --zone-nom gareoult --telechargement --ombrages multi slope svf lrm \
      --formats-fichier mbtiles rmap --qualite-image 75

  # LiDAR : depuis TIF existant → RMAP uniquement
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 1 \
      --zone-nom aa --source ign_lidar/aa/_warped_aa_multi_ombrage_z18.tif \
      --formats-fichier rmap --zoom-min 8 --zoom-max 18

  # IGN Raster public (pas de clé requise)
  python lidar2map.py --ignraster --zone-ville gareoult --zone-rayon 10 \
      --zone-nom aa --couche planign \
      --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18

  # IGN Raster Scan 25 (professionnel uniquement — clé API requise)
  # python lidar2map.py --ignraster --zone-ville gareoult --zone-rayon 10 \
  #     --zone-nom aa --couche scan25 --apikey VOTRE_CLE_PRO \
  #     --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18

  # Vecteur IGN : cadastre + hydrographie
  python lidar2map.py --ignvecteur --zone-ville gareoult --zone-rayon 5 \
      --zone-nom aa --couche cadastre cours_eau detail_hydro

  # OSM : carte rando + GeoJSON
  python lidar2map.py --osm --zone-ville gareoult --zone-rayon 10 \
      --zone-nom aa --couche "highway=* waterway=* natural=water" \
      --formats-fichier map gz

  # Fusion GeoJSON
  python lidar2map.py --fusionner \
      --source ign_vecteur/aa/*.geojson.gz osm_vecteur/aa/*.geojson.gz \
      --formats-fichier gz

  # Zone par département entier (Var)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --workers 8 --ombrages multi --formats-fichier mbtiles

  # A-priori splitting: grande zone en 4×4 morceaux avec nettoyage disque
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage

  # Reprise après interruption (même commande — les morceaux terminés sont ignorés)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage

  # Linux/macOS : la commande est identique, sauf 'python' → 'python3'
  python3 lidar2map.py --ignlidar --zone-ville Gareoult --zone-rayon 1 \
      --ombrages svf --formats-fichier mbtiles
"""
import os
import re
import sys
import ssl

# certifi fournit un bundle de certificats CA à jour, indispensable sur
# Windows 11 et macOS où les certificats système sont parfois absents ou
# périmés (erreur "certificate verify failed" sur les API IGN).
#
# Problème d'œuf/poule : cet import arrive AVANT _bootstrap_environnement()
# (ligne ~1088), donc avant que l'auto-installeur ait pu installer certifi.
# On protège donc l'import par un try/except :
#   • certifi déjà installé (cas normal après le 1er lancement)  → setup complet
#   • certifi absent (tout 1er lancement, Python nu)             → fallback propre
#     Le bootstrap installe certifi juste après, puis re-exécute le script
#     (mode auto/venv) ou l'import réussira dès le prochain appel (mode pip).
try:
    import certifi as _certifi
    os.environ['SSL_CERT_FILE']       = _certifi.where()
    os.environ['REQUESTS_CA_BUNDLE']  = _certifi.where()
except ImportError:
    # certifi absent : on laisse Python utiliser ses certificats système.
    # Sur macOS, cela peut provoquer "certificate verify failed" pour les API
    # IGN, mais uniquement lors du tout premier lancement (avant l'install).
    # Le patch ssl._create_default_https_context ci-dessous sert de filet
    # de sécurité dans ce cas transitoire.
    pass

# Patch SSL de dernier recours : certaines bibliothèques ignorent les
# variables d'environnement SSL_CERT_FILE. Ce patch remplace le contexte
# SSL par défaut de Python par un contexte non-vérifiant, ce qui garantit
# que les téléchargements pip (bootstrap) réussissent même si les certificats
# système sont périmés. Il sera surchargé par certifi une fois installé.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


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
                import shutil as _sh_u
                _home_u         = _Path.home()
                _lidar2map_home = _home_u / ".lidar2map"
                _cibles_u = [
                    (_app_dir,                    "bundle extrait"),
                    (_lidar2map_home / "venv",    "venv Python"),
                    (_lidar2map_home / "osmosis", "osmosis"),
                    (_lidar2map_home / "jre",     "JRE Java"),
                ]
                print()
                print("  ── lidar2map uninstall ──────────────────────────────────")
                print()
                _total_u = 0
                for _c_u, _label_u in _cibles_u:
                    if _c_u.exists():
                        _taille_u = sum(
                            f.stat().st_size for f in _c_u.rglob("*") if f.is_file()
                        )
                        _total_u += _taille_u
                        print(f"  Suppression {_label_u} ({_taille_u / 1e6:.0f} MB)")
                        print(f"    {_c_u}")
                        _sh_u.rmtree(_c_u, ignore_errors=True)
                        print(f"    {'✓ removed' if not _c_u.exists() else '⚠ partial'}")
                    else:
                        print(f"  {_label_u} : absent ({_c_u})")
                print()
                print(f"  {_total_u / 1e6:.0f} MB freed.")
                print()
                print("  Note: lidar2map.py, the .app/.exe and the zip are not removed.")
                print("  Remove them manually if needed.")
                sys.exit(0)

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
                # Durci contre les locks ORPHELINS : si le lock est plus vieux
                # que _LOCK_STALE_S (instance tuée/plantée pendant l'extraction),
                # on le considère périmé et on le retire au lieu d'attendre 60 s
                # puis d'échouer. L'extraction du bundle prend ~30-60 s -> 300 s
                # est une borne haute sûre (pas de faux positif en cas de double-clic).
                import time as _time
                _LOCK_STALE_S = 300
                _lock_actif = _lock.exists()
                if _lock_actif:
                    try:
                        _lock_actif = (_time.time() - _lock.stat().st_mtime) < _LOCK_STALE_S
                    except Exception:
                        _lock_actif = False
                    if not _lock_actif:
                        print("  Stale lockfile detected - cleaning up and resuming.", flush=True)
                        _lock.unlink(missing_ok=True)
                if _lock_actif:
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
                    _app_dir.parent.mkdir(parents=True, exist_ok=True)
                    _lock.touch()
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

                        _sha_file.write_text(
                            f"{_expected_sha}\n{_bundle.stat().st_mtime}",
                            encoding="utf-8")
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

import queue
import shutil
import argparse
import threading
import json
import gzip
import sqlite3
import xml.etree.ElementTree as _ET
import math
import time
import struct
import io
import subprocess
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
import platform
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# Vérification version Python
if sys.version_info < (3, 8):
    print("ERROR: Python 3.8 minimum required (current version: "
          + str(sys.version_info.major) + "." + str(sys.version_info.minor) + ")")
    print("Download Python 3.8+ from https://www.python.org/downloads/")
    sys.exit(1)

# ============================================================
# INSTALLATION AUTOMATIQUE DES DÉPENDANCES
# ============================================================

def _resoudre_mode_bootstrap():
    """Détermine le mode de bootstrap (auto|pip|none) et nettoie sys.argv.

    Source de vérité unique pour le mode — appelée par _bootstrap_environnement
    avant tout autre travail d'init. Avant ce refactor le mode était résolu
    en interne dans _bootstrap_venv_si_besoin, ce qui empêchait l'orchestrateur
    de conditionner les autres appels (pip, install_deps) sur ce mode.

    Priorité (du plus faible au plus fort) :
      1. Défaut          : "auto"
      2. Variable d'env  : LIDAR2MAP_BOOTSTRAP={auto|pip|none}
      3. Argument CLI    : --bootstrap={auto|pip|none}
      4. Aliases legacy  : --no-bootstrap → none, --venv → auto, --no-venv → pip

    Effet de bord : retire de sys.argv tous les flags consommés (pour qu'ils
    n'arrivent pas à argparse plus loin).
    """
    mode = "auto"   # défaut

    # Variable d'env (priorité basse)
    env_mode = os.environ.get("LIDAR2MAP_BOOTSTRAP", "").lower().strip()
    if env_mode in ("auto", "pip", "none"):
        mode = env_mode

    # Argument CLI (priorité haute) — supporte --bootstrap=X et --bootstrap X
    args_to_remove = []
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--bootstrap="):
            v = arg.split("=", 1)[1].lower().strip()
            if v in ("auto", "pip", "none"):
                mode = v
            args_to_remove.append(i)
        elif arg == "--bootstrap" and i + 1 < len(sys.argv):
            v = sys.argv[i+1].lower().strip()
            if v in ("auto", "pip", "none"):
                mode = v
            args_to_remove.append(i)
            args_to_remove.append(i+1)

    # Aide
    if "--help-bootstrap" in sys.argv:
        print(_bootstrap_venv_si_besoin.__doc__)
        sys.exit(0)

    # Compatibilité descendante avec les anciens flags
    if "--no-bootstrap" in sys.argv:
        mode = "none"
    if "--venv" in sys.argv:
        mode = "auto"  # = venv (qui est désormais le défaut)
    if "--no-venv" in sys.argv:
        mode = "pip"

    # Retirer tous ces flags de sys.argv pour qu'argparse ne les voit pas
    for _flag in ("--no-bootstrap", "--venv", "--no-venv", "--help-bootstrap"):
        while _flag in sys.argv:
            sys.argv.remove(_flag)
    # Retirer aussi --bootstrap=X et --bootstrap X
    for i in sorted(args_to_remove, reverse=True):
        if i < len(sys.argv):
            del sys.argv[i]

    return mode


def _gui_deps_plateforme():
    """Retourne les dépendances GUI spécifiques à la plateforme.

    pywebview a besoin d'un backend graphique natif selon l'OS :

      Windows  WebView2 natif (EdgeHTML/Chromium), pré-installé depuis Win10.
               Aucune dépendance pip supplémentaire.

      macOS    Backend natif Cocoa/WebKit via pyobjc (léger, ~20 MB).
               pyobjc est inclus avec Python installé depuis python.org, mais
               PAS avec Homebrew, conda, pyenv ou miniforge. Dans ce cas,
               pywebview ne trouve pas de backend et plante au lancement.
               → On installe pyobjc-framework-WebKit en priorité (natif).
               → Si pyobjc est already present, rien n'est installé (pas de Qt).
               → Qt (PyQt6) est en fallback uniquement si pyobjc échoue
                 (cas rare : macOS très ancien, architecture non supportée).

      Linux    Pas de backend natif. Qt (PyQt6 + PyQt6-WebEngine + qtpy) est
               le seul backend disponible via pip de façon fiable.
               GTK est une alternative théorique mais ses wheels pip sont
               inexistants ou cassés — on l'évite.

    Retourne (critiques, optionnelles) :
      critiques    : installées systématiquement, bloquantes si échec total
      optionnelles : tentées une par une, non bloquantes si échec
    """
    _sys = platform.system()
    if _sys == "Darwin":
        # macOS : on installe TOUJOURS les deux backends.
        # • pyobjc (Cocoa/WebKit natif) : léger, fonctionne sur Mac avec display
        # • PyQt6 : requis quand la machine est headless (VM SSH, Scaleway M1)
        #   NB : on ne peut pas savoir au moment du bootstrap si le Mac aura
        #   un display au moment de l'exécution — donc on installe Qt
        #   systématiquement plutôt que de le laisser en fallback optionnel.
        return (
            ["pyobjc-framework-WebKit", "pyobjc-framework-Cocoa",
             "PyQt6", "PyQt6-WebEngine", "qtpy"],   # critiques (tous)
            [],
        )
    elif _sys == "Linux":
        # Linux : Qt est le seul backend viable via pip.
        return (
            ["PyQt6", "PyQt6-WebEngine", "qtpy"],   # critiques
            [],
        )
    else:
        # Windows : on force le backend Qt (PYWEBVIEW_GUI=qt) au lieu de
        # WinForms/WebView2+pythonnet. pythonnet 3.1.0 régresse (récursion
        # infinie dans la sérialisation .NET -> bridge JS<->Python cassé ->
        # GUI gelée) et WinForms freeze par intermittence. Qt = même moteur
        # Chromium que Linux/macOS, plus aucune couche .NET.
        return (["PyQt6", "PyQt6-WebEngine", "qtpy"], [])


def _verifier_venv_linux():
    """Sur Linux/Ubuntu, vérifie que le module venv est disponible.

    Sur Debian/Ubuntu, python3-venv est un paquet système SÉPARÉ de python3
    (décision de packaging Debian). Il est donc absent sur un Python nu, ce
    qui fait planter la création de venv sans message clair.

    Cette fonction est appelée AVANT toute tentative de création de venv.
    Elle détecte l'absence du module et imprime les instructions apt.
    """
    if platform.system() != "Linux":
        return
    try:
        import venv as _venv_test  # noqa: F401
        return  # module présent, tout va bien
    except ImportError:
        pass
    # Détecter aussi via subprocess pour couvrir les cas où le module
    # est présent mais pas importable depuis le Python courant.
    r = subprocess.run(
        [sys.executable, "-m", "venv", "--help"],
        capture_output=True)
    if r.returncode == 0:
        return  # disponible
    # Module absent : message clair et arrêt propre
    _py = f"python{sys.version_info.major}.{sys.version_info.minor}"
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ERROR: module Python 'venv' absent                        ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()
    print("  On Ubuntu/Debian, this module is in a separate package.")
    print("  Install it with (once):")
    print()
    print(f"    sudo apt install python3-venv")
    print(f"    # or, if you use Python {sys.version_info.major}.{sys.version_info.minor} explicitly:")
    print(f"    sudo apt install {_py}-venv")
    print()
    print("  Then relaunch the script.")
    sys.exit(1)


def _bootstrap_venv_si_besoin():
    """Bootstrap automatique d'un environnement Python isolé.

    Comportement par défaut : crée un venv dans ``~/.lidar2map/`` (Mac/Linux)
    ou ``%USERPROFILE%\\.lidar2map\\`` (Windows) au 1er lancement, y installe
    les dépendances, et y relance le script. Comportement uniforme sur les 3 OS.

    Avantages du venv par défaut sur toutes plateformes :
      - Isolation : zéro pollution du Python système
      - Désinstallation propre : suppression d'un dossier suffit
      - Cohérent avec la bonne pratique Python (un venv par projet)
      - Évite les conflits de versions de modules avec d'autres outils
      - Contourne PEP 668 sur Mac/Linux récents nativement

    Flags utilisateur (lus directement depuis sys.argv pour bypasser argparse
    qui n'est pas encore initialisé à ce stade du démarrage) :

      --bootstrap=auto    : venv automatique (défaut, recommandé). Si un env
                            isolé est déjà actif (conda / venv), s'arrête et
                            oriente vers --bootstrap=pip|none au lieu de créer
                            un venv parallèle.
      --bootstrap=pip     : install directe dans l'env Python courant
                            (utilise --break-system-packages si PEP 668)
      --bootstrap=none    : pas d'install — vérifie les imports et plante
                            avec un message clair si manquants. Utile pour
                            ceux qui gèrent leur propre env (conda, venv
                            manuel, install système contrôlée).
      --help-bootstrap    : affiche cette aide et quitte

    Variables d'environnement équivalentes :
      LIDAR2MAP_BOOTSTRAP=auto|pip|none

    Suppression du venv à tout moment :
      rm -rf ~/.lidar2map                       (Mac/Linux)
      rmdir /s /q %USERPROFILE%\\.lidar2map     (Windows)
    Le script en recréera un au prochain lancement si besoin.
    """
    mode = _resoudre_mode_bootstrap()

    # Deps réellement critiques pour le pipeline LiDAR principal.
    # numba et osmium sont optionnelles (numba accélère SVF, osmium pour
    # OSM→GeoJSON) — leur absence ne doit pas planter le bootstrap.
    deps_critiques = ["PIL", "pyproj", "numpy", "scipy", "ijson",
                      "rasterio", "fiona", "certifi"]

    # ── Mode "none" : juste vérifier les imports, planter clairement si KO ─
    if mode == "none":
        manquantes = []
        for mod in deps_critiques:
            try:
                __import__(mod)
            except ImportError:
                manquantes.append(mod)
        if manquantes:
            pkg_map = {"PIL": "Pillow", "pyproj": "pyproj", "numpy": "numpy",
                       "scipy": "scipy", "ijson": "ijson",
                       "rasterio": "rasterio", "fiona": "fiona",
                       "numba":    "numba",     "certifi": "certifi"}
            pkgs_pip = [pkg_map.get(m, m) for m in deps_critiques]
            print()
            print("  ╔══════════════════════════════════════════════════════════════╗")
            print("  ║  Mode --bootstrap=none: auto-install disabled              ║")
            print("  ╚══════════════════════════════════════════════════════════════╝")
            print(f"  Modules Python manquants : {', '.join(manquantes)}")
            print()
            print("  Install them yourself with your preferred method:")
            print(f"    pip install {' '.join(pkgs_pip)} pywebview")
            print(f"    # ou : conda install -c conda-forge {' '.join(pkgs_pip)} pywebview")
            print()
            sys.exit(1)
        return

    # ── Mode "pip" : install dans l'env Python courant ───────────────────
    # Délégué à _installer_deps() plus bas (avec stratégie 3 niveaux :
    # standard → --break-system-packages → --user)
    if mode == "pip":
        return  # rien à faire ici, _installer_deps() prend le relais

    # ── Mode "auto" : créer/utiliser un venv ─────────────────────────────
    # Tout le runtime lidar2map (venv Python, JRE Java, osmosis, etc.) est
    # centralisé dans ~/.lidar2map/ — un seul dossier à supprimer pour
    # un nettoyage complet, et partagé entre tous les dossiers de travail.
    is_windows  = platform.system() == "Windows"
    lidar_home  = Path.home() / ".lidar2map"
    venv_path   = lidar_home / "venv"

    # Détecter si on est déjà dans le bon venv (ré-entrance après os.execv)
    try:
        if Path(sys.prefix).resolve() == venv_path.resolve():
            return
    except Exception:
        pass

    # ── Garde : environnement Python actif (conda / venv) ────────────────
    # Si l'utilisateur a déjà un env isolé actif, créer en silence un venv
    # parallèle dans ~/.lidar2map/ le surprend (cas signalé par un
    # utilisateur conda). On s'arrête et on l'oriente vers les modes adaptés
    # plutôt que de piétiner son env. Détection par variables d'env standard
    # (déterministe — contrairement à un scan des deps dans sys.path, cf.
    # NB ci-dessous). Non atteint en ré-entrance : le check venv ci-dessus a
    # déjà return quand sys.prefix == ~/.lidar2map/venv.
    _env_actif = os.environ.get("CONDA_PREFIX") or os.environ.get("VIRTUAL_ENV")
    if _env_actif:
        print()
        print("  ╔" + "═" * 62 + "╗")
        print("  ║ " + "Active Python environment detected (conda / venv)".ljust(60) + " ║")
        print("  ╚" + "═" * 62 + "╝")
        print(f"  Env actif : {_env_actif}")
        print()
        print("  To avoid creating a parallel venv in ~/.lidar2map/:")
        print("    python lidar2map.py --bootstrap=pip    # install the deps in this env")
        print("    python lidar2map.py --bootstrap=none   # if the deps are already there")
        print()
        print("  (or deactivate the active env to use the isolated venv by default)")
        print()
        sys.exit(1)

    # NB : on ne shortcut PAS sur "deps importables dans le Python courant".
    # Avant ce refactor, la présence des deps quelque part dans le sys.path
    # courant (système, conda, autre venv) faisait que ~/.lidar2map/venv
    # n'était jamais créé → comportement non-déterministe selon l'historique
    # de la machine. Maintenant, le mode "auto" crée toujours le venv.
    # Pour utiliser un autre env, passer explicitement par :
    #   --bootstrap=pip   (install dans l'env Python courant)
    #   --bootstrap=none  (assume que tout est déjà là)

    # Sous Windows : Scripts/ au lieu de bin/
    venv_bin    = venv_path / ("Scripts" if is_windows else "bin")
    venv_python = venv_bin / ("python.exe" if is_windows else "python")
    venv_pip    = venv_bin / ("pip.exe"    if is_windows else "pip")

    # Si le venv existe déjà avec les déps : juste re-exécuter dedans
    if venv_python.exists():
        check_cmd = [str(venv_python), "-c",
                     "import " + ", ".join(deps_critiques)]
        r_check = subprocess.run(check_cmd, capture_output=True)
        if r_check.returncode == 0:
            print(f"  Relaunching in venv : {venv_path}")
            _relancer_dans_venv(venv_python, is_windows)
            # Ne retourne pas — soit os.execv (Unix), soit sys.exit (Windows)

    # Créer le venv s'il n'existe pas encore
    if not venv_python.exists():
        # Sur Linux/Ubuntu : vérifier python3-venv AVANT de tenter la création
        _verifier_venv_linux()
        suppr_cmd = ("rmdir /s /q %USERPROFILE%\\.lidar2map" if is_windows
                     else "rm -rf ~/.lidar2map")
        print()
        print("  ╔══════════════════════════════════════════════════════════════╗")
        print("  ║  First launch - creating an isolated Python environment".ljust(63) + " ║")
        print("  ║  (~50 MB once deps are installed). This env is local to".ljust(63) + " ║")
        print("  ║  the project and does not touch your system Python.".ljust(63) + " ║")
        print("  ║".ljust(63) + " ║")
        print(f"  ║  To remove it: {suppr_cmd}".ljust(63) + " ║")
        print("  ║".ljust(63) + " ║")
        print("  ║  To use a direct install (no venv):".ljust(63) + " ║")
        print("  ║    python lidar2map.py --bootstrap=pip".ljust(63) + " ║")
        print("  ╚══════════════════════════════════════════════════════════════╝")
        print(f"  Creating venv {venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True)
        except subprocess.CalledProcessError as e:
            print(f"  ERROR creating venv: {e}")
            print("  Install Python 3.8+ with the venv module.")
            sys.exit(1)

    # Déps installées dans le venv. numba est inclus systématiquement :
    # il accélère le calcul SVF de ×15 à ×50. osmium est inclus pour le
    # pipeline OSM → GeoJSON (sans, ce pipeline n'est pas disponible).
    # Si l'install d'une dep optionnelle (osmium, numba) échoue, on retry
    # sans elle plutôt que de bloquer tout le script.
    #
    # Deps GUI : spécifiques à la plateforme (Qt sur macOS/Linux).
    # Traitées comme optionnelles au sens du retry (si PyQt6 échoue, on
    # continue — la GUI sera non fonctionnelle mais le CLI marchera).
    _gui_crit, _gui_opt = _gui_deps_plateforme()
    deps_critiques  = ["Pillow", "pyproj", "numpy", "scipy", "ijson",
                       "rasterio", "fiona", "pywebview", "certifi"] + _gui_crit
    deps_optionnelles = ["osmium", "numba"] + _gui_opt
    deps_pip = deps_critiques + deps_optionnelles
    print(f"  Installing dependencies in the venv (3-5 min)...")

    def _pip_install(pkgs):
        """Tente pip install. Retourne (success, stderr_msg)."""
        try:
            r = subprocess.run(
                [str(venv_pip), "install", "-q",
                 "--disable-pip-version-check"] + pkgs,
                capture_output=True, text=True, timeout=900)
            return r.returncode == 0, (r.stderr or "")[-500:]
        except subprocess.TimeoutExpired:
            return False, "pip install timeout (>900s, reseau bloque ?)"
        except subprocess.CalledProcessError as e:
            return False, str(e)

    install_ok, err_msg = _pip_install(deps_pip)
    if not install_ok:
        # Retry sans les deps optionnelles : si l'une d'elles est cassée
        # (cas pyrosm 0.6.2 sur Python 3.12), on garde au moins le pipeline
        # principal (LiDAR + raster).
        print(f"  Bulk install failed, retrying without optional deps...")
        install_ok, err_msg = _pip_install(deps_critiques)
        if install_ok:
            # Tenter ensuite chaque optionnelle individuellement.
            print(f"  Critical deps installed. Trying optional deps one by one...")
            opt_failed = []
            for opt in deps_optionnelles:
                ok_one, _ = _pip_install([opt])
                if not ok_one:
                    opt_failed.append(opt)
                    print(f"    ⚠ {opt} : install failed - associated pipeline unavailable")
                else:
                    print(f"    ✓ {opt} : OK")
            if opt_failed:
                print(f"  ⚠ Optional deps not installed: {', '.join(opt_failed)}")
                print(f"     Retry manuel possible : {venv_pip} install {' '.join(opt_failed)}")
        else:
            print(f"  ERROR installing critical deps in the venv:")
            print(f"  {err_msg}")
            print(f"  Check your internet connection, then try:")
            print(f"    {venv_pip} install {' '.join(deps_critiques)}")
            sys.exit(1)
    print(f"  ✓ Dependencies installed.")

    # Relancer le script avec le Python du venv
    print(f"  Relaunching in venv...")
    _relancer_dans_venv(venv_python, is_windows)


def _relancer_dans_venv(venv_python, is_windows):
    """Relance le script avec le Python du venv, comportement OS-spécifique.

    Unix : os.execv remplace le process courant — le shell ne récupère
           la main qu'après terminaison du child. C'est le comportement
           attendu, économique en RAM (pas de double process).

    Windows : os.execv y a un comportement différent de Unix — le parent
              termine immédiatement et le child tourne en arrière-plan, ce
              qui fait que le shell affiche son prompt avant la sortie du
              child. Pour éviter cette confusion d'affichage, on utilise
              subprocess.run + sys.exit : on attend la fin du child et on
              propage son code retour avant de rendre la main au shell.

              IMPORTANT : on passe explicitement stdout=sys.stdout et
              stderr=sys.stderr au child, sinon quand le parent est lancé
              par la GUI avec stdout=PIPE, le pipe ne se propage pas au
              child venv, et la GUI ne voit jamais rien des messages que
              le child écrit. Sans ce flush du parent au préalable, les
              traces "[trace]" et "[init]" du parent se mélangent avec
              celles du child à cause du buffering.
    """
    if is_windows:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            r = subprocess.run([str(venv_python)] + sys.argv,
                               stdout=sys.stdout, stderr=sys.stderr,
                               stdin=sys.stdin)
            sys.exit(r.returncode)
        except KeyboardInterrupt:
            sys.exit(130)
    else:
        os.execv(str(venv_python),
                 [str(venv_python)] + sys.argv)


def _bootstrap_pip():
    """S'assure que pip est disponible via ensurepip si nécessaire."""
    r = subprocess.run([sys.executable, "-m", "pip", "--version"],
                       capture_output=True)
    if r.returncode == 0:
        return  # pip déjà disponible
    print("  pip absent — bootstrap via ensurepip...")
    try:
        import ensurepip
        ensurepip.bootstrap(upgrade=True)
        print("  pip installed.")
    except Exception as e:
        print(f"  ERREUR bootstrap pip : {e}")
        print("  Install pip manually: https://pip.pypa.io/en/stable/installation/")
        sys.exit(1)


def _installer_deps():
    """Vérifie et installe les dépendances Python requises au démarrage.

    Stratégie d'installation, par ordre d'essai :
    1. ``pip install <deps>`` standard
    2. ``pip install --break-system-packages <deps>`` (PEP 668 — Linux récent,
       Homebrew Mac récent)
    3. ``pip install --user <deps>`` (fallback dernière chance)

    Si toutes échouent, on s'arrête PROPREMENT avec un message clair plutôt
    que de continuer pour planter sur le premier ``import pyproj`` venu.
    """
    # Deps GUI spécifiques à la plateforme (Qt sur macOS/Linux, rien sur Windows)
    _gui_crit, _gui_opt = _gui_deps_plateforme()

    # find_spec ne charge pas le module — beaucoup plus rapide que __import__
    # pour les modules lourds (rasterio, scipy, PIL, PyQt6 prennent 200-500 ms
    # chacun à l'import). Gain typique au démarrage à froid : 2-3 s.
    import importlib.util as _ilu

    def _module_present(name: str) -> bool:
        try:
            return _ilu.find_spec(name) is not None
        except (ImportError, ValueError):
            # ValueError : module parent absent (PyQt6.X quand PyQt6 manque)
            return False

    deps = []
    for mod, pkg in [
        ("PIL",       "Pillow"),
        ("pyproj",    "pyproj"),
        ("numpy",     "numpy"),
        ("scipy",     "scipy"),
        ("ijson",     "ijson"),       # streaming JSON (BD TOPO dept-scale, OSM XML)
        ("rasterio",  "rasterio"),    # I/O raster + reprojection (remplace gdalwarp/gdal_translate)
        ("fiona",     "fiona"),       # I/O vecteur (remplace ogr2ogr CLI)
        ("certifi",   "certifi"),     # bundle CA à jour (fix SSL Windows 11 / macOS)
        ("webview",   "pywebview"),   # GUI (mode sans arguments)
        ("osmium",    "osmium"),      # parseur PBF OSM (remplace ogr2ogr OSM)
        ("numba",     "numba"),       # accélération SVF ×15-50 (LLVM JIT)
    ]:
        if not _module_present(mod):
            deps.append(pkg)

    # Ajouter les deps GUI plateforme non encore installées
    for pkg in _gui_crit + _gui_opt:
        # Correspondance pkg pip → nom de module importable
        _mod_map = {
            "PyQt6":                  "PyQt6",
            "PyQt6-WebEngine":        "PyQt6.QtWebEngineWidgets",
            "qtpy":                   "qtpy",
            "pyobjc-framework-WebKit":"WebKit",
            "pyobjc-framework-Cocoa": "Cocoa",
        }
        _mod = _mod_map.get(pkg, pkg)
        if not _module_present(_mod):
            if pkg not in deps:
                deps.append(pkg)

    if not deps:
        return

    # Distinguer deps critiques (sans elles, le script ne tourne pas) et
    # deps optionnelles (utiles pour certains pipelines spécifiques).
    # Les deps optionnelles ne doivent pas bloquer si elles échouent à
    # s'installer — sinon un wheel buggé empêcherait toute utilisation
    # du script (cas vécu avec pyrosm 0.6.2 cassé sur Python 3.12).
    # Les deps GUI optionnelles (pyobjc sur macOS) sont aussi dans ce set.
    DEPS_OPTIONNELLES = ({"osmium", "numba", "py7zr", "mapbox-vector-tile"}
                         | set(_gui_opt))
    deps_crit = [d for d in deps if d not in DEPS_OPTIONNELLES]
    deps_opt  = [d for d in deps if d in DEPS_OPTIONNELLES]

    print(f"  Installing dependencies: {', '.join(deps)}...")

    # Détecter si on est dans un venv. Dans un venv, --user n'a aucun sens
    # (pip refuse) — il faut juste tenter l'install standard.
    in_venv = (hasattr(sys, "real_prefix")
               or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix))

    base_cmd = [sys.executable, "-m", "pip", "install", "-q",
                "--disable-pip-version-check"]
    if in_venv:
        # Dans un venv : juste tenter standard, pas de --user, pas de --break-system-packages
        strategies = [
            (base_cmd + deps,                                "standard (venv)"),
        ]
    else:
        strategies = [
            (base_cmd + deps,                                "standard"),
            (base_cmd + deps + ["--break-system-packages"],  "--break-system-packages (PEP 668)"),
            (base_cmd + deps + ["--user"],                   "--user (install locale)"),
        ]

    last_stderr = ""
    install_ok = False
    for cmd, label in strategies:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        except (OSError, FileNotFoundError) as e:
            last_stderr = f"pip not found : {e}"
            continue
        except subprocess.TimeoutExpired:
            last_stderr = f"pip install timeout (>900s) : {label}"
            continue
        if r.returncode == 0:
            # Vérifier que les imports critiques fonctionnent.
            # Les deps optionnelles ne sont PAS dans cette vérification —
            # leur absence ne doit pas bloquer.
            rates = []
            for mod, pkg in [("PIL","Pillow"),("pyproj","pyproj"),("numpy","numpy"),
                             ("scipy","scipy"),("ijson","ijson"),("rasterio","rasterio"),
                             ("fiona","fiona"),("certifi","certifi"),("webview","pywebview")]:
                if pkg in deps_crit:
                    try:
                        __import__(mod)
                    except ImportError:
                        rates.append(pkg)
            # Vérifier aussi les GUI deps critiques plateforme
            for pkg in _gui_crit:
                if pkg in deps_crit:
                    _mod_map = {"PyQt6": "PyQt6", "PyQt6-WebEngine": "PyQt6.QtWebEngineWidgets",
                                "qtpy": "qtpy"}
                    try:
                        __import__(_mod_map.get(pkg, pkg))
                    except ImportError:
                        rates.append(pkg)
            if not rates:
                print(f"  ✓ Install succeeded ({label})")
                install_ok = True
                break
            print(f"  Tentative {label} : pip OK but critical imports fail ({', '.join(rates)})")
            last_stderr = f"installation faite mais imports {rates} indisponibles"
        else:
            last_stderr = (r.stderr or r.stdout or "").strip()
            if last_stderr:
                last_stderr = last_stderr.split("\n")[-3:]
                last_stderr = "\n  ".join(last_stderr)

    # Si install groupée a échoué, retry avec deps_crit seules (sans les
    # optionnelles qui peuvent être en cause). Cas typique : osmium Cython
    # cassé sur Python 3.12 → l'install groupée plante, mais les autres
    # deps critiques s'installent très bien seules.
    if not install_ok and deps_opt and deps_crit:
        print(f"  Retry without optional deps ({', '.join(deps_opt)})...")
        cmd_crit_only = base_cmd + deps_crit
        if in_venv:
            try:
                r = subprocess.run(cmd_crit_only, capture_output=True, text=True,
                                   timeout=900)
            except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
                r = None
            if r is not None and r.returncode == 0:
                rates = []
                for mod, pkg in [("PIL","Pillow"),("pyproj","pyproj"),("numpy","numpy"),
                                 ("scipy","scipy"),("ijson","ijson"),("rasterio","rasterio"),
                                 ("fiona","fiona"),("webview","pywebview")]:
                    if pkg in deps_crit:
                        try:
                            __import__(mod)
                        except ImportError:
                            rates.append(pkg)
                if not rates:
                    print(f"  ✓ Critical deps installed (without: {', '.join(deps_opt)})")
                    print(f"  ⚠ Optional deps not installed: associated pipelines unavailable")
                    print(f"     - osmium : --osm --file-formats geojson")
                    print(f"     - numba  : SVF lent (×15 fois plus)")
                    install_ok = True

    if install_ok:
        return

    # Toutes les tentatives ont échoué — on arrête ici avec un message clair.
    import platform as _plat
    _is_mac   = _plat.system() == "Darwin"
    _is_linux = _plat.system() == "Linux"
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ERROR: cannot install the Python dependencies      ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(f"  Modules manquants : {', '.join(deps_crit)}")
    if last_stderr:
        print(f"  Dernier message pip :\n  {last_stderr}")
    print()
    print("  Solutions possibles :")
    if _is_mac:
        print("    1. Install in a venv:")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps_crit)}")
        print("       Puis relancer : python lidar2map.py --bootstrap=none")
        print()
        print("    2. Force a system install (not recommended):")
        print(f"       pip install --break-system-packages {' '.join(deps)}")
    elif _is_linux:
        print("    1. Install via the package manager:")
        print(f"       sudo apt install python3-{' python3-'.join(d.lower() for d in deps)}")
        print()
        print("    2. Use a venv:")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps)}")
    else:
        print(f"    pip install {' '.join(deps)}")
    print()
    sys.exit(1)


def _bootstrap_environnement():
    """Orchestrateur unique du démarrage : mode → venv → pip → install deps.

    Avant ce refactor, trois appels top-level se succédaient sans qu'aucun
    point du code ne décide globalement de la stratégie. Résultat :
    `_bootstrap_pip()` était systématiquement exécuté même en mode `auto`
    où il est inutile (le venv post-re-exec garantit pip), et même en mode
    `none` où c'est en contradiction avec l'intention de l'utilisateur ("je
    gère mes deps moi-même").

    Maintenant : un seul point d'entrée, qui décide en fonction du mode :
      - "auto" : crée un venv si nécessaire (re-exec) puis install deps via
                 le pip du venv (forcément présent, _bootstrap_pip inutile).
      - "pip"  : pas de venv, mais on n'a pas la garantie que pip soit
                 dispo (Python système nu, distrib exotique) → bootstrap pip
                 via ensurepip puis install deps.
      - "none" : ni venv ni install. _bootstrap_venv_si_besoin se charge
                 lui-même de vérifier les imports critiques et d'avorter
                 proprement avec un message si manquants. Pas d'appel à
                 _installer_deps qui forcerait une install non voulue.

    Quand cette fonction retourne, les imports critiques sont garantis pour
    les modes auto et pip. Pour none, soit les imports marchent, soit on a
    déjà sys.exit(1) avec un message clair.
    """
    # En mode frozen (PyInstaller), toutes les deps Python sont déjà embarquées
    # dans le bundle — pas de venv ni de pip à exécuter.
    if getattr(sys, "frozen", False):
        return
    mode = _resoudre_mode_bootstrap()
    _bootstrap_venv_si_besoin_avec_mode(mode)
    if mode == "pip":
        _bootstrap_pip()
    if mode != "none":
        _installer_deps()


# Petit wrapper pour conserver _bootstrap_venv_si_besoin sans paramètre côté
# usage (notamment l'aide accessible via __doc__) tout en évitant la double
# résolution du mode quand il est appelé depuis l'orchestrateur.
def _bootstrap_venv_si_besoin_avec_mode(mode):
    """Appelle _bootstrap_venv_si_besoin avec un mode pré-résolu.

    On stocke le mode dans une variable d'environnement temporaire que la
    fonction lira en priorité, court-circuitant sa propre résolution.
    Solution moins invasive que de modifier la signature publique de
    _bootstrap_venv_si_besoin (qui est documentée et stable).
    """
    os.environ["LIDAR2MAP_BOOTSTRAP"] = mode
    try:
        _bootstrap_venv_si_besoin()
    finally:
        # Nettoyer pour ne pas laisser fuir le mode dans les sub-processes
        # ou le venv post-re-exec qui ferait sa propre résolution.
        os.environ.pop("LIDAR2MAP_BOOTSTRAP", None)


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
if _INSTALL_ALL_DEPS:
    print("  Full install of all dependencies...")
    _pip_base = [sys.executable, "-m", "pip", "install", "-q"]
    _toutes_deps = [
        # Critiques
        "Pillow", "pyproj", "numpy", "scipy", "ijson",
        "rasterio", "fiona", "certifi", "pywebview",
        # GUI selon plateforme
        *([p for p in ["PyQt6", "PyQt6-WebEngine", "qtpy"]
           if __import__("platform").system() in ("Darwin", "Linux")]),
        # Optionnelles / lazy (non installées par le bootstrap standard)
        # lazrs = backend décompression LAZ pour laspy (providers LiDAR cz/se/es)
        "osmium", "numba", "laspy", "lazrs", "py7zr", "mapbox-vector-tile",
    ]
    import subprocess as _sp_id
    # Table de correspondance explicite pkg pip → nom de module importable.
    # La dérivation automatique (split("-")[0]) échoue sur plusieurs packages :
    #   mapbox-vector-tile → "mapbox" (faux), PyQt6-WebEngine → "pyqt6" (faux)
    _pkg_to_mod = {
        "Pillow":             "PIL",
        "pyproj":             "pyproj",
        "numpy":              "numpy",
        "scipy":              "scipy",
        "ijson":              "ijson",
        "rasterio":           "rasterio",
        "fiona":              "fiona",
        "certifi":            "certifi",
        "pywebview":          "webview",
        "PyQt6":              "PyQt6",
        "PyQt6-WebEngine":    "PyQt6.QtWebEngineWidgets",
        "qtpy":               "qtpy",
        "osmium":             "osmium",
        "numba":              "numba",
        "laspy":              "laspy",
        "lazrs":              "lazrs",
        "py7zr":              "py7zr",
        "mapbox-vector-tile": "mapbox_vector_tile",
    }
    for _pkg in _toutes_deps:
        _mod = _pkg_to_mod.get(_pkg, _pkg.replace("-", "_").lower())
        try:
            __import__(_mod)
            print(f"    ✓ {_pkg} (already installed)")
        except ImportError:
            r = _sp_id.run(_pip_base + [_pkg], capture_output=True)
            if r.returncode == 0:
                print(f"    ✓ {_pkg}")
            else:
                print(f"    ⚠ {_pkg} (optional - skipped)")
    print("  All dependencies installed.")
    sys.exit(0)

# ── --desinstaller ────────────────────────────────────────────────────────────
# Supprime le venv (~/.lidar2map/venv) et le dossier d'extraction du bundle
# (~/Library/Application Support/lidar2map/ sur macOS, etc.).
# Ne supprime PAS le script lui-même ni le .app/.exe.
if _DESINSTALLER:
    import shutil as _sh_uninst
    import platform as _plat_uninst
    from pathlib import Path as _P_uninst

    _sys_u  = _plat_uninst.system()
    _home_u = _P_uninst.home()

    _lidar2map_home = _home_u / ".lidar2map"

    # Dossier d'extraction du bundle (même logique que le launcher)
    if _sys_u == "Windows":
        _app_data = _P_uninst(os.environ.get("LOCALAPPDATA",
                              str(_home_u / "AppData" / "Local"))) / "lidar2map"
    elif _sys_u == "Darwin":
        _app_data = _home_u / "Library" / "Application Support" / "lidar2map"
    else:
        _app_data = _home_u / ".local" / "share" / "lidar2map"

    _cibles = [
        (_app_data,                      "dossier d'extraction du bundle"),
        (_lidar2map_home / "venv",       "venv Python"),
        (_lidar2map_home / "osmosis",    "osmosis"),
        (_lidar2map_home / "jre",        "JRE Java"),
    ]

    print()
    print("  ── lidar2map uninstall ──────────────────────────────────")
    print()

    _total = 0
    for _chemin, _label in _cibles:
        if _chemin.exists():
            # Calculer la taille avant suppression
            _taille = sum(f.stat().st_size for f in _chemin.rglob("*") if f.is_file())
            _total += _taille
            print(f"  Suppression {_label} ({_taille / 1e6:.0f} MB)")
            print(f"    {_chemin}")
            _sh_uninst.rmtree(_chemin, ignore_errors=True)
            # Mêmes états ✓/⚠ que le bloc launcher pour cohérence
            print(f"    {'✓ removed' if not _chemin.exists() else '⚠ partial'}")
        else:
            print(f"  {_label} : absent ({_chemin})")
    print()
    print(f"  {_total / 1e6:.0f} MB freed.")
    print()
    print("  Note: lidar2map.py, the .app/.exe and the zip are not removed.")
    print("  Remove them manually if needed.")
    print()
    sys.exit(0)

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
if _SMOKETEST:
    import shutil as _smk_sh
    from pathlib import Path as _smk_Path

    # Calcul de DOSSIER_TRAVAIL en local (la constante globale n'est définie
    # qu'à la ligne ~1880, après ce bloc).
    if getattr(sys, "frozen", False):
        _smk_work = _smk_Path(os.environ.get("LIDAR2MAP_WORK_DIR")
                              or _smk_Path(sys.executable).resolve().parent)
        # En frozen, sys.executable EST le binaire → on le ré-invoque
        _smk_cmd_base = [sys.executable]
    else:
        _smk_work = _smk_Path(__file__).resolve().parent
        _smk_cmd_base = [sys.executable, str(_smk_Path(__file__).resolve())]

    _smk_nom     = "smoke"
    _smk_projets = _smk_work / "Projets" / _smk_nom
    _smk_zone    = ["--zone-ville", "Gareoult", "--zone-rayon", "1",
                    "--zone-nom",   _smk_nom]

    # (nom, args supplémentaires, outputs attendus relatifs à _smk_projets)
    _smk_tests = [
        ("LiDAR",
         ["--ignlidar", "--telechargement", "--workers", "4",
          "--ombrages", "multi", "--formats-fichier", "mbtiles",
          "--zoom-min", "10", "--zoom-max", "13"],
         ["ign_lidar/smoke_multi_ombrage_z10-13.mbtiles"]),
        ("WMTS (planign)",
         ["--ignraster", "--couche", "planign", "--workers", "8",
          "--formats-fichier", "mbtiles",
          "--zoom-min", "12", "--zoom-max", "14"],
         ["raster/smoke_planign_z12-14.mbtiles"]),
        ("WFS (routes)",
         ["--ignvecteur", "--couche", "routes", "--formats-fichier", "gz"],
         ["ign_vecteur/smoke_ign_troncon_de_route.geojson.gz"]),
        ("OSM (highway)",
         ["--osm", "--couche", "highway=*",
          "--formats-fichier", "map", "gz"],
         ["osm_vecteur/smoke.map",
          "osm_vecteur/smoke_osm_highway.geojson.gz"]),
    ]

    def _smk_size(n):
        return f"{n/1e6:.1f} Mo" if n >= 1e6 else f"{n/1024:.0f} Ko"

    # Empêcher chaque sous-test de polluer l'historique de 5+ entrées.
    # _historique_debut/_sauver_historique respectent cet env var.
    _smk_env = os.environ.copy()
    _smk_env["LIDAR2MAP_SKIP_HIST"] = "1"

    def _smk_run(name, extra, expected, timeout=600):
        print(f"\n━━━ {name} ━━━", flush=True)
        t0 = time.time()
        try:
            rc = subprocess.run(_smk_cmd_base + _smk_zone + extra,
                                timeout=timeout, env=_smk_env).returncode
        except subprocess.TimeoutExpired:
            print(f"  ✗ TIMEOUT (> {timeout}s)")
            return False
        dur = time.time() - t0
        if rc != 0:
            print(f"  ✗ exit={rc} en {dur:.0f}s")
            return False
        missing, sizes = [], []
        for f in expected:
            p = _smk_projets / f
            if not p.exists():
                missing.append(f + " (absent)")
            elif p.stat().st_size == 0:
                missing.append(f + " (vide)")
            else:
                sizes.append(f"{_smk_Path(f).name}={_smk_size(p.stat().st_size)}")
        if missing:
            print(f"  ✗ outputs KO en {dur:.0f}s :")
            for m in missing:
                print(f"      {m}")
            return False
        print(f"  ✓ {dur:.0f}s  ({', '.join(sizes)})")
        return True

    def _smk_fusion(timeout=120):
        """Fusion utilise l'output OSM précédent comme input."""
        src = _smk_projets / "osm_vecteur" / "smoke_osm_highway.geojson.gz"
        out = _smk_projets / "fusion"      / "smoke_fusion.geojson.gz"
        print(f"\n━━━ Fusion ━━━", flush=True)
        if not src.exists():
            print(f"  ⊘ SKIP : input OSM absent ({src.name})")
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            rc = subprocess.run(_smk_cmd_base + ["--fusionner", "--source", str(src),
                                                 "--sortie", str(out),
                                                 "--formats-fichier", "gz"],
                                timeout=timeout, env=_smk_env).returncode
        except subprocess.TimeoutExpired:
            print(f"  ✗ TIMEOUT (> {timeout}s)")
            return False
        dur = time.time() - t0
        if rc == 0 and out.exists() and out.stat().st_size > 0:
            print(f"  ✓ {dur:.0f}s  ({_smk_size(out.stat().st_size)})")
            return True
        print(f"  ✗ exit={rc} en {dur:.0f}s")
        return False

    print(f"━━━ Smoke test: Gareoult 1 km ━━━")
    print(f"  Binaire : {' '.join(_smk_cmd_base)}")
    print(f"  Outputs : {_smk_projets}")
    # Wipe Projets/smoke pour isoler les tests (caches dalles/tuiles préservés)
    if _smk_projets.exists():
        _smk_sh.rmtree(_smk_projets, ignore_errors=True)

    _smk_results = []
    for _smk_name, _smk_extra, _smk_expected in _smk_tests:
        _smk_results.append((_smk_name,
                             _smk_run(_smk_name, _smk_extra, _smk_expected)))
    _smk_results.append(("Fusion", _smk_fusion()))

    print(f"\n━━━ RESULTS ━━━")
    _smk_ok   = sum(1 for _, ok in _smk_results if ok is True)
    _smk_fail = sum(1 for _, ok in _smk_results if ok is False)
    _smk_skip = sum(1 for _, ok in _smk_results if ok is None)
    for _smk_name, ok in _smk_results:
        sym = "✓" if ok is True else ("⊘" if ok is None else "✗")
        print(f"  {sym} {_smk_name}")
    print(f"\n{_smk_ok}/{len(_smk_results)} OK"
          + (f"  ({_smk_skip} skipped)" if _smk_skip else "")
          + (f"  ({_smk_fail} échec)"   if _smk_fail else ""))
    sys.exit(0 if _smk_fail == 0 else 1)

# ── suite du script ───────────────────────────────────────────────────────────

class _TeeLogger:
    """
    Duplique stdout vers un fichier log avec horodatage.

    Gestion des \r : les barres de progression terminent par \r (pas \n).
    Pour le terminal, \r écrase la ligne courante — comportement normal.
    Pour le log, on ne conserve que le dernier état de chaque ligne \r
    (la valeur finale), en ignorant les mises à jour intermédiaires.
    """
    def __init__(self, log_path):
        self._terminal = sys.stdout
        self._log = open(log_path, "w", encoding="utf-8", buffering=1)
        self._buf = ""          # buffer jusqu'au prochain \n
        self._cr_buf = ""       # dernier contenu de ligne \r (écrase les précédents)

    def _log_line(self, line):
        """Écrit une ligne dans le fichier log avec horodatage."""
        # Nettoyer les séquences \r résiduelles dans la ligne
        if "\r" in line:
            line = line.split("\r")[-1]
        line = line.strip()
        if line:
            ts = time.strftime("%H:%M:%S")
            self._log.write(f"[{ts}] {line}\n")

    def write(self, msg):
        # ── Terminal ─────────────────────────────────────────────────────────
        # Toutes les opérations sont défensives parce que cette méthode est
        # appelée par Python lui-même au shutdown. Si un de ses appels lève
        # une exception, Windows retourne le code 120 (ERROR_CALL_NOT_IMPLEMENTED)
        # à la place du code passé à sys.exit().
        try:
            self._terminal.write(msg)
        except UnicodeEncodeError:
            try:
                self._terminal.write(msg.encode(self._terminal.encoding or "cp1252",
                                                 errors="replace").decode(
                                                 self._terminal.encoding or "cp1252"))
            except Exception:
                pass
        except Exception:
            pass
        try:
            # Flush sur \r ET \n. Sans flush sur \n, les lignes restent
            # bufferisées dans le pipe quand stdout est redirigé (cas de la
            # GUI qui lance le script comme subprocess). Conséquence : les
            # messages n'arrivent au parent qu'au moment du wait() final,
            # ce qui rend le panneau de log inutile en temps réel.
            if "\r" in msg or "\n" in msg:
                self._terminal.flush()
        except Exception:
            pass

        # ── Log ──────────────────────────────────────────────────────────────
        # Traiter caractère par caractère pour gérer \r et \n proprement
        try:
            for ch in msg:
                if ch == "\r":
                    # \r : écrase le contenu de la ligne courante (barre de progression)
                    # On garde le dernier état dans _cr_buf ; on ne loggue rien encore
                    self._cr_buf = self._buf
                    self._buf = ""
                elif ch == "\n":
                    # \n : fin de ligne — logguer le contenu final
                    # Si la ligne était précédée de \r, prendre le dernier \r
                    line = self._buf or self._cr_buf
                    self._log_line(line)
                    self._buf = ""
                    self._cr_buf = ""
                else:
                    self._buf += ch
        except Exception:
            pass

    def flush(self):
        # Défensif : flush() est appelé par Python au shutdown, après que
        # close() a peut-être déjà fermé self._log. Sans try/except, l'erreur
        # "I/O operation on closed file" remonte → code retour Windows = 120.
        try:
            self._terminal.flush()
        except Exception:
            pass
        try:
            self._log.flush()
        except Exception:
            pass

    def close(self):
        # Flush des buffers résiduels — défensif : pendant le shutdown
        # Python, sys.stdout/sys.stderr peuvent être dans un état partiel,
        # et toute exception ici peut polluer le code retour du process
        # (Windows retourne 120 si l'atexit handler échoue).
        try:
            remaining = self._buf or self._cr_buf
            if remaining:
                self._log_line(remaining)
        except Exception:
            pass
        try:
            self._log.close()
        except Exception:
            pass

def _activer_log():
    import atexit
    # En mode frozen, __file__ est dans le bundle temporaire — on veut les
    # logs à côté de l'exe (dossier utilisateur, persistant).
    # LIDAR2MAP_WORK_DIR : transmis par le launcher onefile pour pointer sur
    # le dossier du launcher au lieu de l'inner (%LOCALAPPDATA%\lidar2map).
    if getattr(sys, "frozen", False):
        _base = Path(os.environ.get("LIDAR2MAP_WORK_DIR")
                     or Path(sys.executable).resolve().parent)
    else:
        _base = Path(__file__).resolve().parent
    log_dir = _base / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _probe = log_dir / ".write_test"
        _probe.touch()
        _probe.unlink()
    except OSError:
        # logs/ inaccessible → log console uniquement, pas de fichier système
        print("  WARNING: logs/ folder inaccessible, console log only.")
        return
    nom = "lidar_" + time.strftime("%Y%m%d_%H%M%S") + ".log"
    log_path = log_dir / nom
    tee = _TeeLogger(log_path)
    sys.stdout = tee
    sys.stderr = tee   # stderr → même log (tracebacks, warnings)
    # atexit : fonction nommée robuste plutôt qu'un lambda. Toute exception
    # ici peut faire que Windows retourne le code 120 (ERROR_CALL_NOT_IMPLEMENTED)
    # au lieu du code passé à sys.exit() — ça casse à la fois le contrat CLI
    # et le mécanisme d'erreur modale GUI qui se base sur retcode != 0.
    def _close_tee_safely():
        try:
            if isinstance(sys.stdout, _TeeLogger):
                sys.stdout.close()
        except Exception:
            pass
    atexit.register(_close_tee_safely)
    # ── Intercepter les exceptions non gérées → log avant exit ───────────────
    import traceback as _tb
    def _excepthook(exc_type, exc_value, exc_tb):
        print("\nUNHANDLED EXCEPTION:")
        print("".join(_tb.format_exception(exc_type, exc_value, exc_tb)))
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _excepthook
    # ── En-tête avec paramètres de lancement ─────────────────────────────────
    ts  = time.strftime("%Y-%m-%d %H:%M:%S")
    cmd = " ".join(sys.argv)
    tee._log.write("=" * 60 + "\n")
    tee._log.write(f"  lidar2map.py — démarrage {ts}\n")
    tee._log.write(f"  Commande : {cmd}\n")
    tee._log.write("=" * 60 + "\n")
    print(f"  Log : {log_path}")

_activer_log()

# ── Requêtes HTTP via urllib (stdlib, zéro dépendance) ──────────────────────
_HTTP_UA = "lidar2map/1.0 (IGN WMTS/WMS)"


def _urlopen(url, headers=None, timeout=15):
    """Ouvre une URL avec urllib, retourne la réponse. Gère User-Agent par défaut."""
    hdrs = {"User-Agent": _HTTP_UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    return urllib.request.urlopen(req, timeout=timeout)


def _hms(seconds):
    """Formate une durée en secondes → h:mm:ss ou m:ss ou Xs."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


# Outils GDAL dont les appels subprocess sont affichés dans le terminal
def _log_req(url_or_cmd, label=""):
    """Log une requête externe (HTTP ou subprocess) — toujours via print/TeeLogger."""
    if isinstance(url_or_cmd, list):
        exe      = Path(url_or_cmd[0]).name if url_or_cmd else ""
        args_str = " ".join(str(a) for a in url_or_cmd[1:]
                            if not str(a).startswith("--config"))
        print(f"  $ {exe} {args_str}", flush=True)
    else:
        print(f"  → {label + ' ' if label else ''}{url_or_cmd}", flush=True)

# ============================================================
# PLATEFORME
# ============================================================

WINDOWS = platform.system() == "Windows"
LINUX   = platform.system() == "Linux"
MACOS   = platform.system() == "Darwin"

# ── Manifest de fichiers créés (découpage à priori) ───────────────────────────
# Classe Manifeste : JSON local au projet, universel LiDAR/WMTS.
# _creer_fichier() fonctionne via un context manager thread-local —
# silencieux en dehors d'un contexte actif.

import threading as _threading
from contextlib import contextmanager as _contextmanager

_manifest_ctx = _threading.local()   # .manifeste et .cle par thread


class Manifeste:
    """Manifeste JSON local au projet — reprise et nettoyage des morceaux."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data = self._charger()

    def _charger(self):
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(d, dict):
                    d.setdefault("morceaux", {})
                    d.setdefault("fichiers", {})
                    return d
                print(f"  ⚠ Manifeste {self.path.name} : structure inattendue "
                      f"(type={type(d).__name__}) — réinitialisation")
            except (OSError, json.JSONDecodeError) as e:
                # Manifeste corrompu (crash disque, écriture interrompue) : on
                # repart d'un état vierge mais on prévient l'utilisateur — la
                # progression précédente sera perdue, pas réinitialisée silencieusement.
                print(f"  ⚠ Manifeste {self.path.name} illisible ({type(e).__name__}: {e}) "
                      f"— réinitialisation (progression antérieure perdue)")
        return {"morceaux": {}, "fichiers": {}}

    def deja_traite(self, cle: str) -> bool:
        return self._data["morceaux"].get(cle, {}).get("termine", False)

    def debut_morceau(self, cle: str, nom: str):
        self._data["morceaux"].setdefault(cle, {}).update(
            {"debut": time.strftime("%Y-%m-%dT%H:%M:%S"), "nom": nom})
        self._sauver()

    def fin_morceau(self, cle: str, duree_s: int):
        self._data["morceaux"][cle].update({"termine": True, "duree_s": duree_s})
        self._sauver()

    def enregistrer_fichier(self, path, cle: str):
        p = str(Path(path).resolve())
        lst = self._data["fichiers"].setdefault(cle, [])
        if p not in lst:
            lst.append(p)
        self._sauver()

    def fichiers_morceau(self, cle: str) -> list:
        return list(self._data["fichiers"].get(cle, []))

    def eta_global(self, n_total: int):
        """ETA *grossier* du run, à partir des duree_s déjà stockées par
        morceau (fin_morceau). Retourne (nb_termine, eta_s) ; eta_s vaut None
        tant qu'aucun morceau n'est terminé (pas de base de calcul).

        Médiane × restants, PAS moyenne : les durées sont très hétérogènes
        (chunk en mer ≈ 0, chunk en relief dense très cher), une moyenne plate
        donnerait un ETA sauvage en début de run. La médiane absorbe ces
        outliers. Reste un ordre de grandeur — étiqueté 'coarse' à l'affichage."""
        durees = sorted(m["duree_s"] for m in self._data["morceaux"].values()
                        if m.get("termine") and isinstance(m.get("duree_s"), (int, float)))
        if not durees:
            return 0, None
        n = len(durees)
        med = durees[n // 2] if n % 2 else (durees[n // 2 - 1] + durees[n // 2]) / 2
        restants = max(0, n_total - n)
        return n, int(med * restants)

    _warned_save_failed = False    # class-level : un seul warn par run

    def _sauver(self):
        try:
            _ecrire_json_atomique(self.path, self._data, indent=2)
        except Exception as e:
            # Le manifeste est best-effort : si le disque est saturé ou
            # si les permissions changent, on n'interrompt pas le pipeline
            # principal — mais on prévient une fois (par run) pour que
            # l'utilisateur sache que la reprise sera incohérente.
            if not Manifeste._warned_save_failed:
                Manifeste._warned_save_failed = True
                print(f"  ⚠ Manifeste {self.path.name} : write failure "
                      f"({type(e).__name__}: {e}). "
                      f"Reprise potentiellement incohérente.")


@_contextmanager
def _contexte_manifeste(manifeste, cle: str):
    """Active le tracking des fichiers créés pour ce morceau dans le thread courant.

    Supporte l'imbrication : sauvegarde le contexte précédent à l'entrée et
    le restaure à la sortie, plutôt que d'écraser avec None (ce qui ferait
    perdre le contexte externe en cas de with ... with).
    """
    _prev_m = getattr(_manifest_ctx, "manifeste", None)
    _prev_c = getattr(_manifest_ctx, "cle",       None)
    _manifest_ctx.manifeste = manifeste
    _manifest_ctx.cle = cle
    try:
        yield
    finally:
        _manifest_ctx.manifeste = _prev_m
        _manifest_ctx.cle = _prev_c


def _creer_fichier(path):
    """
    Déclare un fichier intermédiaire créé dans le pipeline.

    Enregistré dans le manifest du morceau courant → removed par --nettoyage
    après le morceau (dalles, TIF ombrages, TIF warpé, VRT, data.bin, tuiles
    WMTS, etc.).

    Les sorties finales (.mbtiles, .rmap, .sqlitedb, .geojson(.gz)) NE doivent
    PAS être déclarées via cette fonction — elles sont conservées d'office.

    Silencieux si aucun contexte manifeste n'est actif (hors boucle à priori).
    """
    m = getattr(_manifest_ctx, "manifeste", None)
    if m is None:
        return
    cle = getattr(_manifest_ctx, "cle", "global")
    m.enregistrer_fichier(path, cle)


def _supprimer_fichiers(fichiers: list):
    """
    Supprime tous les fichiers créés par un morceau (--nettoyage).
    Cela inclut : dalles LiDAR, tuiles WMTS, TIF ombrages, TIF warpé.
    Conserve uniquement les sorties finales (.mbtiles, .rmap, .sqlitedb).

    But : permettre le traitement d'une grande BBox sans saturer le disque —
    chaque morceau libère son espace avant que le suivant démarre.

    Seuls les fichiers créés/téléchargés PAR ce morceau (enregistrés dans le
    manifest via _creer_fichier) sont removeds. Les fichiers déjà
    présents avant le début du morceau ne sont pas touchés.
    """
    suppr = 0
    dirs_a_verifier = set()
    for chemin in fichiers:
        p = Path(chemin)
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
    if suppr:
        print(f"  Cleanup: {suppr} intermediate file(s) removed")


# Code de sortie dédié au garde-fou disque (--min-free-gb). Permet à un
# orchestrateur multi-département (boucle shell « lance et oublie ») de
# distinguer un arrêt PROPRE « disque bas, relançable » d'une vraie erreur de
# traitement (exit 1). Convention proche de rsync/borg qui réservent des codes
# par catégorie d'arrêt.
EXIT_DISK_LOW = 3


def _espace_libre_go(chemin) -> float:
    """Espace libre (Go) sur le volume de `chemin`. Sonde le premier parent
    existant — au tout premier chunk le dossier cible n'existe pas encore.
    Retourne inf si la sonde échoue : un échec de sonde ne doit JAMAIS bloquer
    le run (le garde-fou est défensif, pas un point de défaillance)."""
    p = Path(chemin)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return shutil.disk_usage(p).free / (1024 ** 3)
    except OSError:
        return float("inf")


def _garde_disque(chemin, seuil_go: float, cle: str, nb_ok: int, n_total: int):
    """Garde-fou disque proactif (--min-free-gb), appelé AVANT de démarrer un
    chunk (avant debut_morceau / téléchargement). Si l'espace libre passe sous
    le seuil, arrêt propre via sys.exit(EXIT_DISK_LOW).

    Invariant de reprise : le chunk n'ayant pas été démarré (aucun
    debut_morceau, aucun fichier enregistré), une relance le rejoue
    proprement. C'est pour ça que le check est ici et pas au milieu du chunk.

    seuil_go <= 0 : désactivé (défaut). Le seuil est fourni par l'opérateur,
    pas auto-calculé : il doit couvrir le pic d'UN chunk (intermédiaires +
    pyramide de tuiles, dominé par le PNG SVF), cf. aide CLI."""
    if seuil_go <= 0:
        return
    libre = _espace_libre_go(chemin)
    if libre < seuil_go:
        print(f"\n  ⚠ Disk space low: {libre:.1f} GB free < {seuil_go:.0f} GB threshold.")
        print(f"  Stopping cleanly before chunk {cle} — {nb_ok}/{n_total} chunks done. "
              f"Free space and relaunch to resume.")
        sys.exit(EXIT_DISK_LOW)

# ============================================================
# CONFIGURATION
# ============================================================

# ── Chemins ─────────────────────────────────────────────────────────────────
# En mode frozen (PyInstaller) : __file__ pointe dans le bundle temporaire
# (sys._MEIPASS sous --onefile). On utilise sys.executable pour que les
# Projets/, cache/, logs/ etc. soient créés à côté de l'exe (cwd utilisateur).
# _MEIPASS reste utilisable séparément pour retrouver les ressources bundlées
# (tagmapping-min.xml).
if getattr(sys, "frozen", False):
    # LIDAR2MAP_WORK_DIR transmis par le launcher onefile : pointe vers le
    # dossier où l'utilisateur a posé l'exe. Sinon, fallback sur le dossier
    # de l'exe courant (cas exe onedir lancé directement).
    DOSSIER_TRAVAIL = Path(os.environ.get("LIDAR2MAP_WORK_DIR")
                           or Path(sys.executable).resolve().parent)
    BUNDLE_DIR      = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    DOSSIER_TRAVAIL = Path(__file__).resolve().parent
    BUNDLE_DIR      = DOSSIER_TRAVAIL

# ~/.lidar2map/ : dossier de runtime partagé entre tous les dossiers de travail.
# Contient venv/, jre/, osmosis/. Permet de ne télécharger qu'une fois ces
# dépendances même si le script est lancé depuis plusieurs emplacements.
# Pour nettoyer complètement lidar2map :  rm -rf ~/.lidar2map
LIDAR2MAP_HOME = Path.home() / ".lidar2map"

# ── Provider LiDAR (par défaut : France IGN HD) ──────────────────────────────
# POC d'abstraction : tout ce qui est spécifique à une source nationale
# (URLs, CRS, nommage des dalles, géométrie) vit dans providers/<pays>.py.
# Le reste du pipeline (SVF, ombrages, MBTiles) reste agnostique.
#
# Sélection : --provider <code> en CLI, ou variable d'env LIDAR2MAP_PROVIDER.
# Codes disponibles : fr-ign (défaut), nl-ahn (POC).
import importlib as _importlib
import os as _os

def _discover_providers():
    """Liste les providers disponibles dans providers/*.py.

    Retourne une liste de dicts {code, name, country} (sans erreur si un
    module est cassé). Utilisé par la GUI pour peupler son sélecteur de
    provider.
    """
    providers_dir = Path(__file__).resolve().parent / "providers"
    result = []
    if not providers_dir.exists():
        return result
    for f in sorted(providers_dir.glob("*.py")):
        if f.stem.startswith("_"):
            continue
        try:
            mod = _importlib.import_module(f"providers.{f.stem}")
            result.append({
                "code":           getattr(mod, "CODE",           f.stem),
                "name":           getattr(mod, "NAME",           f.stem),
                "country":        getattr(mod, "COUNTRY",        ""),
                "apikey_requise": bool(getattr(mod, "APIKEY_REQUISE", False)),
            })
        except Exception as e:
            print(f"  [provider scan] {f.name} skipped: {type(e).__name__}: {e}",
                  file=sys.stderr)
    return result


def _load_provider():
    code = None
    # CLI scan léger (sans dépendre d'argparse qui n'est pas encore configuré).
    # --provider est un pré-flag GLOBAL : on le lit puis on le RETIRE de sys.argv
    # pour qu'aucun des parsers par-mode (raster, vecteur, fusion, découpe…) n'ait
    # à le déclarer. Sinon `--raster --provider us-tnm` → "unrecognized arguments".
    # Accepte les deux formes : `--provider code` et `--provider=code`.
    _argv = sys.argv
    _i = 0
    while _i < len(_argv):
        _a = _argv[_i]
        if _a == "--provider":
            if _i + 1 < len(_argv):
                code = _argv[_i + 1]
            del _argv[_i:_i + 2]
            continue
        if _a.startswith("--provider="):
            code = _a.split("=", 1)[1]
            del _argv[_i]
            continue
        _i += 1
    code = code or _os.environ.get("LIDAR2MAP_PROVIDER") or "fr-ign"
    # Mapping code → module (kebab-case → snake_case)
    module_name = code.replace("-", "_")
    try:
        return _importlib.import_module(f"providers.{module_name}")
    except ImportError:
        # providers/ absent (distribution minimale) ou provider inconnu :
        # on retombe sur un provider FR-IGN inline pour ne pas crasher.
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
        # dalles_pour_bbox : lever NotImplementedError → calculer_grille_bbox
        # attrape cette exception et retourne une liste vide (comportement attendu
        # pour les providers sans grille régulière).
        def _dalles_pour_bbox(x1, y1, x2, y2): raise NotImplementedError
        _p.dalles_pour_bbox = _dalles_pour_bbox
        # dalle_filename / dalle_url : ne devraient pas être appelées en mode --osm
        def _not_available(msg):
            raise RuntimeError(f"Provider fr-ign (fallback) : {msg} — "
                               "dossier providers/ absent.")
        _p.dalle_filename  = lambda x_km, y_km:            _not_available("dalle_filename")
        _p.dalle_url       = lambda x_km, y_km:            _not_available("téléchargement LiDAR")
        # discover_dalles : retourne {} — les call sites font déjà `or {}`
        # et le téléchargement est sauté si dalles_dict est vide.
        _p.discover_dalles = lambda bbox, bbox_l93, cache: {}
        # subdir_from_name : None → chemin_dalle retombe sur la racine (ok)
        _p.subdir_from_name = lambda nom: None
        # post_download / set_apikey : no-op silencieux
        _p.post_download    = lambda chemin: None
        _p.post_fetch       = None   # None = pas de conversion pre-validation
        _p.set_apikey       = lambda key:    None
        return _p

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
DALLE_KM           = PROVIDER.DALLE_KM
PX_PAR_DALLE       = PROVIDER.PX_PAR_DALLE
SEUIL_DALLE_VALIDE = PROVIDER.SEUIL_DALLE_VALIDE

# ── Réseau — tentatives et délais ─────────────────────────────────────────────
MAX_TENTATIVES = 3    # essais avant abandon d'un téléchargement
DELAI_RETRY    = 5    # secondes entre deux tentatives
NB_WORKERS     = 8    # workers parallèles par défaut (téléchargement dalles/tuiles)

# ── MBTiles / WMTS — paramètres de batch ─────────────────────────────────────
SEUIL_ERR_CONSEC      = 30   # erreurs consécutives → abandon WMTS (panne systémique)
SEUIL_HORS_COUVERTURE = 300  # tuiles toutes en 204 avec 0 succès → bbox hors couche
BATCH_MBTILES_INSERT  = 500  # tuiles par INSERT executemany dans MBTiles WMTS
BATCH_SQLITEDB_INSERT = 2000 # tuiles par batch lors de la conversion vers .sqlitedb
HTTP_CHUNK_SIZE       = 65536  # taille de lecture par chunk HTTP (téléchargement dalles)

# ── URLs IGN (re-exports du provider) ────────────────────────────────────────
# getattr avec fallback : tous les providers n'ont pas forcément ces attributs.
# Ex: AHN expose WCS_URL au lieu de WFS_URL — les chemins de code qui utilisent
# WFS_URL retomberont sur None et devront être adaptés (BDTOPO, etc.).
WMS_URL   = getattr(PROVIDER, "WMS_URL",   None)
WMS_LAYER = getattr(PROVIDER, "WMS_LAYER", None)
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


def _regions_disponibles():
    """Liste triée des slugs de régions Geofabrik (dédupliqués depuis _GEOFABRIK).

    L'unité = la région Geofabrik (anciennes régions pré-2016), pas la région
    administrative actuelle : chaque slug correspond à exactement un PBF, ce qui
    évite toute fusion. Ex: 'provence-alpes-cote-d-azur'."""
    return sorted(set(_GEOFABRIK.values()))


def _departements_de_region(slug):
    """Departments (codes INSEE) appartenant à la région Geofabrik `slug`."""
    return sorted(d for d, s in _GEOFABRIK.items() if s == slug)

# ── Rendu archéologique ───────────────────────────────────────────────────────
ELEVATION_SOLEIL = 25   # degrés — 25° révèle micro-reliefs ; 45° usage général

# Gamma appliqué au SVF après stretch percentile (p2→p98) avant ×255.
# <1 éclaircit (√), 1 = linéaire, >1 assombrit. Le SVF flux cos²γ est tassé
# près de 1 : gamma 2.0 assombrit les midtones et fait ressortir le contraste
# (rendu jugé meilleur à l'œil que la variante RVT 1−sin γ). Surchargeable
# via --svf-gamma ou le champ γ du GUI.
SVF_GAMMA = 2.0


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

    Pattern : sérialiser en RAM, écrire dans path.tmp, fsync, replace path.
    Garantit que path est soit l'ancienne version, soit la nouvelle complète,
    jamais une troncature. Critique pour les caches (manifeste, dep_bbox,
    TMS) où une corruption silencieuse fait perdre l'état entre runs.

    En cas d'OSError (disque plein, permission, etc.), le tmp est nettoyé
    et l'exception remonte. Pas de swallow silencieux comme l'ancien
    `except Exception: pass` du Manifeste.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
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
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


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

    Écriture atomique via .tmp + replace : si la décompression est interrompue,
    le fichier final n'est jamais en état partiel.
    """
    src_gz  = Path(src_gz)
    dst_raw = Path(dst_raw)
    dst_raw.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst_raw.with_suffix(dst_raw.suffix + ".tmp")
    try:
        with gzip.open(src_gz, "rb") as fin, open(tmp, "wb") as fout:
            shutil.copyfileobj(fin, fout, length=chunk)
        tmp.replace(dst_raw)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _gzip_depuis_fichier(src_raw, dst_gz, compresslevel=6, chunk=1 << 20):
    """Compresse src_raw → dst_gz en streaming (1 MB à la fois).

    Pendant écrite, le contenu va dans dst_gz.tmp puis replace : un Ctrl+C
    en cours de compression ne laisse pas un .gz tronqué à la place de
    l'ancien fichier valide.
    """
    src_raw = Path(src_raw)
    dst_gz  = Path(dst_gz)
    dst_gz.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst_gz.with_suffix(dst_gz.suffix + ".tmp")
    try:
        with open(src_raw, "rb") as fin, \
             gzip.open(tmp, "wb", compresslevel=compresslevel) as fout:
            shutil.copyfileobj(fin, fout, length=chunk)
        tmp.replace(dst_gz)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


# Événement d'arrêt propre — positionné par Ctrl+C en mode CLI.
# Vérifié dans les boucles longues (pagination WFS, WMTS, etc.)
# pour interrompre entre deux requêtes sans laisser de thread zombie.
_stop_event = threading.Event()

import signal as _signal
def _on_sigint(sig, frame):
    """Soft cancel : 1er Ctrl+C demande l'arrêt, 2nd force la sortie.

    Pattern standard Unix (git, rsync, etc.) : on laisse l'opération en cours
    finir proprement (cleanup .tmp, fermeture sqlite, etc.) plutôt que de
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

# ============================================================
# UTILITAIRES
# ============================================================

def normaliser_nom(texte):
    """'garéoult' -> 'gareoult'"""
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = re.sub(r"[^a-zA-Z0-9_-]", "_", texte.lower())
    texte = re.sub(r"_+", "_", texte).strip("_")
    return texte


def wgs84_to_lamb93_approx(lon, lat):
    a    = 6378137.0
    e    = 0.0818191908426
    n    = 0.7256077650
    F    = 11754255.426
    rho0 = 6055612.050   # a*F*t(φ0)^n  φ0=46.5° — identique à la conversion inverse
    lam0 = math.radians(3.0)
    lam  = math.radians(lon)
    phi  = math.radians(lat)
    e_sin = e * math.sin(phi)
    t = math.tan(math.pi/4 - phi/2) / ((1 - e_sin)/(1 + e_sin))**(e/2)
    rho   = F * t**n  # F inclut déjà a (= a × F_adim)
    theta = n * (lam - lam0)
    x = 700000 + rho * math.sin(theta)
    y = 6600000 + rho0 - rho * math.cos(theta)
    return x, y


def lamb93_to_wgs84_approx(x, y):
    """Conversion Lambert 93 → WGS84 approx. (±50 m) — sans dépendance externe.
    Constantes IGN officielles : n, F*a, rho0 calculées depuis GRS80 + φ0=46.5°.
    """
    n    = 0.7256077650
    F    = 11754255.426  # a * F (F dimensionless × demi-grand axe GRS80)
    rho0 = 6055612.050   # a * F * t(φ0)^n  avec φ0=46.5°
    e    = 0.0818191908426
    lam0 = math.radians(3.0)
    xs, ys = 700000.0, 6600000.0
    dx = x - xs
    dy = rho0 - (y - ys)
    rho   = math.sqrt(dx*dx + dy*dy)
    theta = math.atan2(dx, dy)
    lam   = theta / n + lam0
    t = (rho / F) ** (1.0 / n)
    phi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(5):
        e_sin = e * math.sin(phi)
        phi = math.pi/2 - 2*math.atan(t * ((1-e_sin)/(1+e_sin))**(e/2))
    return math.degrees(lam), math.degrees(phi)


def _lamb93_to_wgs84_safe(x, y):
    """Lambert 93 → WGS84 avec pyproj si dispo, fallback sur l'approximation.

    Retourne (lon, lat) en degrés. Utilisée partout où pyproj peut manquer
    (ex: bootstrap, environnement minimal) pour garantir un résultat même
    sans proj.db. Précision pyproj < 1 m, approximation < 50 m.
    """
    try:
        _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
        return _t.transform(x, y)
    except Exception:
        return lamb93_to_wgs84_approx(x, y)

# ============================================================
# GÉOCODAGE
# ============================================================

def geocoder_ville_wgs84(nom_ville):
    """Géocode une ville et retourne (lat, lon) en WGS84. Retourne (None, None) si échec.

    Filtre le résultat sur le champ ``addresstype`` Nominatim pour rejeter les
    correspondances "fuzzy" non-administratives (POI, commerces, hameaux
    incertains). Sans ça, Nominatim renvoie n'importe quoi pour une chaîne
    non-existante : "yyyy" → un POI au milieu des Deux-Sèvres, "xxxxx" → un
    nom de cheval dans un haras, etc.

    En mode non-interactif, lève une erreur claire si le résultat n'est pas un lieu
    administratif/habité reconnu. En mode interactif, demande confirmation.
    """
    # Le code pays vient du provider actif. Nominatim filtre par ISO code
    # (countrycodes=fr/nl/etc.) — évite "Amsterdam" → "Île d'Amsterdam (TAAF, FR)"
    # quand on travaille avec un provider NL.
    _cc = (getattr(PROVIDER, "COUNTRY", "fr") or "fr").lower()
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(nom_ville)}"
        f"&countrycodes={_cc}"
        "&format=json&limit=1&addressdetails=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
    _log_req(url, "Nominatim")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            OSError, TimeoutError) as e:
        print(f"  ERREUR geocodage ({type(e).__name__}) : {e}")
        return None, None
    if not data:
        print(f"  ERROR: town not found: {nom_ville}")
        return None, None

    # Validation du type de lieu retourné
    # Lieux acceptés sans question : entités administratives ou habitées clairement
    # nommées. "locality" et "isolated_dwelling" sont OSM-spécifiques et marquent
    # respectivement un hameau non-officiel et une habitation isolée — acceptés
    # mais avec un avertissement.
    TYPES_OK    = {"city", "town", "village", "municipality", "administrative",
                   "suburb", "quarter", "neighbourhood"}
    TYPES_DOUTE = {"hamlet", "locality", "isolated_dwelling", "farm"}

    addrtype = (data[0].get("addresstype") or "").lower()
    display  = data[0].get("display_name", "(?)")
    cat      = (data[0].get("class") or "").lower()

    # Rejet immédiat si pas un lieu (boutique, restaurant, route, etc.)
    if cat not in ("place", "boundary", "landuse"):
        msg = (f"  ERROR: lieu '{nom_ville}' non reconnu comme ville/village.\n"
               f"  Nominatim a renvoyé : {display} (type={cat}/{addrtype}).\n"
               f"  Précisez le nom de la commune.")
        print(msg)
        return None, None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    # Type non-administratif → demander confirmation (ou rejeter en mode non-interactif)
    if addrtype not in TYPES_OK:
        if addrtype in TYPES_DOUTE:
            # Lieu-dit ou hameau : signaler mais accepter
            print(f"  ⚠ '{nom_ville}' resolved to {display} (type={addrtype}).")
            print(f"  Check that this is the expected place.")
        else:
            # Type complètement inattendu (industrial, retail, etc.) : rejeter
            print(f"  ERROR: lieu '{nom_ville}' ambiguous - Nominatim returned "
                  f"{display} (type={addrtype}).")
            print(f"  Specify the full name (municipality, not POI).")
            return None, None

    print(f"  {nom_ville} -> lat={lat:.5f}, lon={lon:.5f}")
    return lat, lon


def geocoder_ville_l93(nom_ville):
    """Géocode une ville et retourne (x, y) en Lambert 93 (pour le pipeline LiDAR). Retourne (None, None) si échec."""
    lat, lon = geocoder_ville_wgs84(nom_ville)
    if lat is None:
        return None, None
    try:
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        x, y = t.transform(lon, lat)
    except ImportError:
        x, y = wgs84_to_lamb93_approx(lon, lat)
        print("  (pyproj missing, approximate conversion)")
    print(f"  Lambert 93 -> X={x:.0f}, Y={y:.0f}")
    return x, y


def geocoder_departement(num_dep):
    """
    Retourne (nom, bx1, by1, bx2, by2) en Lambert 93 via Overpass API OSM.
    Requête par ref:INSEE + admin_level=6 (département français) → bounds exact.
    Résultat mis en cache dans dep_bbox_cache.json à côté du script.
    Si Overpass indisponible et cache existant → utilise le cache.
    """
    # ── Cache local ──────────────────────────────────────────────────────────
    _cache_path = DOSSIER_TRAVAIL / "dep_bbox_cache.json"
    _cache = {}
    if _cache_path.exists():
        try:
            _cache = json.loads(_cache_path.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}

    # Si en cache, retourner directement
    if num_dep in _cache:
        c = _cache[num_dep]
        print(f"  Department {num_dep} — {c['nom']} (local cache)", flush=True)
        print(f"  BBox WGS84 : {c['lon_min']:.4f},{c['lat_min']:.4f} → "
              f"{c['lon_max']:.4f},{c['lat_max']:.4f}")
        try:
            t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
            bx1, by1 = t.transform(c['lon_min'], c['lat_min'])
            bx2, by2 = t.transform(c['lon_max'], c['lat_max'])
        except ImportError:
            bx1, by1 = wgs84_to_lamb93_approx(c['lon_min'], c['lat_min'])
            bx2, by2 = wgs84_to_lamb93_approx(c['lon_max'], c['lat_max'])
        MARGE = 500
        bx1 -= MARGE; by1 -= MARGE; bx2 += MARGE; by2 += MARGE
        surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
        print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Estimated area: ~{surface_km2:.0f} km²")
        return c['nom'], bx1, by1, bx2, by2

    # Overpass : relation administrative de niveau département, identifiée par ref:INSEE
    query = (
        f'[out:json];'
        f'relation["boundary"="administrative"]["admin_level"="6"]["ref:INSEE"="{num_dep}"];'
        f'out bb;'
    )
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})

    nom = None
    lat_min = lat_max = lon_min = lon_max = None

    for _tentative_ovp in range(3):
        try:
            _log_req(req.full_url if hasattr(req, "full_url") else str(req.get_full_url()), "Overpass")
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
            elements = data.get("elements", [])
            if elements:
                el = elements[0]
                bounds = el.get("bounds", {})
                lat_min = bounds.get("minlat")
                lat_max = bounds.get("maxlat")
                lon_min = bounds.get("minlon")
                lon_max = bounds.get("maxlon")
                nom = el.get("tags", {}).get("name", f"dep{num_dep}")
            break
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                OSError, TimeoutError) as e:
            if _tentative_ovp < 2:
                print(f"  Overpass unavailable ({type(e).__name__}: {e}) - retry {_tentative_ovp+1}/3...",
                      flush=True)
                time.sleep(5)
            else:
                print(f"  ERREUR Overpass : {type(e).__name__}: {e}")

    if lat_min is None:
        print(f"  ERROR: cannot geocode the department {num_dep}.")
        print(f"  Overpass API unavailable. Use --zone-bbox X1,Y1,X2,Y2 (Lambert 93).")
        print(f"  Exemple Var 83 : --bbox 905000,6214000,1040000,6322000")
        return None, None, None, None, None

    # ── Sauvegarde dans le cache ──────────────────────────────────────────────
    _cache[num_dep] = {
        "nom": nom, "lat_min": lat_min, "lat_max": lat_max,
        "lon_min": lon_min, "lon_max": lon_max
    }
    try:
        _ecrire_json_atomique(_cache_path, _cache, indent=2)
    except Exception:
        pass  # cache non critique

    print(f"  Department {num_dep} — {nom}")
    print(f"  BBox WGS84 : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")

    try:
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        bx1, by1 = t.transform(lon_min, lat_min)
        bx2, by2 = t.transform(lon_max, lat_max)
    except ImportError:
        bx1, by1 = wgs84_to_lamb93_approx(lon_min, lat_min)
        bx2, by2 = wgs84_to_lamb93_approx(lon_max, lat_max)
        print("  (pyproj missing, approximate conversion)")

    # Marge de 500 m pour ne pas couper les dalles en bordure
    MARGE = 500
    bx1 -= MARGE; by1 -= MARGE
    bx2 += MARGE; by2 += MARGE

    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
    print(f"  Estimated area: ~{surface_km2:.0f} km²")
    return nom, bx1, by1, bx2, by2


def geocoder_region(slug):
    """Retourne (nom, bx1, by1, bx2, by2) dans le CRS natif du provider =
    bbox englobante (union) des départements de la région Geofabrik `slug`.

    Réutilise geocoder_departement (donc le cache dep_bbox_cache.json et la même
    conversion CRS). Retourne (None, …) si le slug est inconnu ou si le géocodage
    d'un département échoue."""
    slug = slug.strip().lower()
    deps = _departements_de_region(slug)
    if not deps:
        print(f"  ERROR: region '{slug}' unknown.")
        print(f"  Available regions: {', '.join(_regions_disponibles())}")
        return None, None, None, None, None
    print(f"  Region {slug} — {len(deps)} departments: {', '.join(deps)}", flush=True)
    bx1 = by1 = float("inf")
    bx2 = by2 = float("-inf")
    for d in deps:
        nom_d, dx1, dy1, dx2, dy2 = geocoder_departement(d)
        if nom_d is None:
            print(f"  ERROR: geocoding of department {d} failed - incomplete region.")
            return None, None, None, None, None
        bx1, by1 = min(bx1, dx1), min(by1, dy1)
        bx2, by2 = max(bx2, dx2), max(by2, dy2)
    nom = slug.replace("-", " ").title()
    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  Region bbox {PROVIDER.CRS_NATIF} : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
    print(f"  Surface (bbox englobante) : ~{surface_km2:.0f} km²")
    return nom, bx1, by1, bx2, by2

def _parser_departements(valeur: str) -> list:
    """
    Parse --zone-departement : valeur simple ou liste/plage.

    Formats acceptés (combinables) :
      83            → ['83']
      30,35,75      → ['30', '35', '75']
      1-10          → ['01', '02', ..., '10']
      1-3,75,83     → ['01', '02', '03', '75', '83']

    Les codes non entiers (DOM/TOM : 2A, 2B, 971, 972…) sont passés tels quels.
    """
    import re
    codes = []
    for token in valeur.upper().split(","):
        token = token.strip()
        if not token:
            continue
        m_range = re.match(r'^([0-9]+)-([0-9]+)$', token)
        if m_range:
            a, b = int(m_range.group(1)), int(m_range.group(2))
            for n in range(a, b + 1):
                # Zéro-padding cohérent avec geo.api.gouv.fr (01…09)
                codes.append(str(n).zfill(2) if n < 10 else str(n))
        elif re.match(r'^[0-9]+$', token):
            # Numérique simple : zéro-padding si chiffre seul
            codes.append(token.zfill(2) if len(token) == 1 else token)
        else:
            codes.append(token)   # 2A, 2B, 971, 972, etc.
    return codes


# ============================================================
# GRILLE DE DALLES
# ============================================================

def calculer_grille_bbox(x1, y1, x2, y2):
    """Retourne (dalles, bbox) depuis une BBox dans le CRS natif du provider.

    Si le provider n'utilise pas de grille régulière (système kaartblad
    alphanumérique pour NL AHN, etc.), retourne une liste vide — le
    pipeline downstream utilise alors PROVIDER.discover_dalles() qui ne
    suppose pas de grille."""
    try:
        dalles = PROVIDER.dalles_pour_bbox(x1, y1, x2, y2)
    except NotImplementedError:
        dalles = []
    return dalles, (x1, y1, x2, y2)


def calculer_grille(cx, cy, rayon_km):
    """Retourne (dalles, bbox) depuis un centre CRS natif et un rayon en km."""
    r = rayon_km * 1000
    return calculer_grille_bbox(cx - r, cy - r, cx + r, cy + r)


def nom_dalle(x_km, y_km):
    return PROVIDER.dalle_filename(x_km, y_km)


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


def chemin_dalle(dossier_dalles, nom):
    """
    Retourne le Path complet d'une dalle dans la structure sous-dossiers.
    Les dalles sont organisées par colonne X : dossier_dalles/XXXX/nom.tif
    ex: D:/Lidar/Dalles/0958/LHD_FXX_0958_6279_MNT_O_0M50_LAMB93_IGN69.tif

    Fallback transparent : si la dalle existe à la racine (ancienne structure),
    retourne le chemin racine. Sinon retourne le chemin sous-dossier.
    """
    # Chemin racine (ancienne structure)
    chemin_racine = dossier_dalles / nom
    if chemin_racine.exists():
        return chemin_racine
    # Délégation au provider pour extraire le sous-dossier depuis le nom
    sub = PROVIDER.subdir_from_name(nom)
    if sub:
        return dossier_dalles / sub / nom
    return chemin_racine  # fallback si nom non reconnu


def construire_url_wms(x_km, y_km):
    """Délégation au provider — la logique URL/CRS/format dépend de la source."""
    return PROVIDER.dalle_url(x_km, y_km)


def _lon_lat_to_tile(lon, lat, z):
    """Convertit lon/lat WGS84 en coordonnées tuile XYZ (x, y) au zoom z.

    Convention Google/OSM : y=0 en haut. Alias historique de deg_to_tile
    (ordre des arguments : lon, lat).
    """
    return deg_to_tile(lat, lon, z)


def interroger_tms_dalles(lon_min, lat_min, lon_max, lat_max, bbox_l93=None):
    """Wrapper vers PROVIDER.discover_dalles — voir providers/fr_ign.py.
    Retourne {nom_dalle: url_wms} ou None si erreur totale."""
    cache_path = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
    return PROVIDER.discover_dalles(
        (lon_min, lat_min, lon_max, lat_max), bbox_l93, cache_path)


def _download_to_tmp(url, chemin_tmp, timeout=60):
    """
    Télécharge url vers chemin_tmp (streaming).
    Retourne le nombre d'octets écrits, ou lève une exception.
    Gère les réponses WMS XML/HTML d'erreur → retourne 0 (dalle absente).
    timeout : tuple (connexion_s, lecture_s) ou entier.

    Protection contre les coupures TCP silencieuses (typiques sur VM/macOS) :
    si le serveur annonce Content-Length, on vérifie que la taille reçue
    correspond exactement — sinon on lève IOError pour déclencher le retry.
    Sur Windows, urllib/WinINet lève une exception dans ce cas ; sur macOS/Linux
    la socket BSD renvoie b"" sans erreur, ce qui sans cette garde produirait
    un fichier tronqué accepté silencieusement comme valide.
    """
    # Pas de _log_req(url) ici : cette fonction est appelée des centaines à
    # milliers de fois en parallèle (1 par dalle WMS) → le spam URL noie la
    # console. La progress bar de _telecharger_dalles_zone suffit ; les
    # erreurs sont loguées par le code de retry des callers.
    # Timeout lecture : prendre la valeur max si tuple (connect, read).
    _timeout = max(timeout) if isinstance(timeout, tuple) else timeout
    try:
        resp = _urlopen(url, timeout=_timeout)
    except urllib.error.HTTPError as _e:
        if _e.code == 404:
            return 0
        raise IOError(f"HTTP {_e.code}") from _e

    # `with` ferme la connexion HTTP même sur exception → pas de fuite de FD
    # (cas observé avec 8 workers parallèles × centaines de dalles).
    with resp:
        ct = resp.headers.get("content-type", "").lower()
        # Rejeter les réponses d'erreur WMS/WCS (page XML/HTML) → dalle absente.
        # MAIS un conteneur WCS 2.0 multipart/related annonce type="text/xml"
        # dans ses paramètres (la partie GML) tout en transportant le GeoTIFF
        # binaire — ne pas le confondre avec une erreur (sinon Digitaal
        # Vlaanderen & co. seraient rejetés à tort). Le désencapsulage a lieu
        # ensuite dans _extraire_tiff_multipart.
        if not ct.startswith("multipart") and ("xml" in ct or "html" in ct):
            return 0

        try:
            content_length = int(resp.headers.get("content-length", 0))
        except (ValueError, TypeError):
            content_length = 0

        buf_size = 0
        with open(chemin_tmp, "wb") as f:
            while True:
                chunk = resp.read(HTTP_CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                buf_size += len(chunk)

    # Vérification d'intégrité : si Content-Length était annoncé et ne correspond
    # pas, la connexion a été coupée silencieusement → le fichier est tronqué.
    # On lève une IOError pour que l'appelant déclenche le retry automatique.
    if content_length > 0 and buf_size != content_length:
        raise IOError(
            f"Transfert tronqué : reçu {buf_size} octets, "
            f"attendu {content_length} (Content-Length)"
        )
    return buf_size


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
        with _rio_v.open(str(chemin)) as ds:
            if ds.width == 0 or ds.height == 0:
                return False
            # Lire 1 bloc pour détecter une troncature des données
            ds.read(1, window=_rio_v.windows.Window(
                0, 0, min(64, ds.width), min(64, ds.height)))
    except Exception:
        # rasterio non disponible ou erreur de lecture → on se fie au magic seul
        pass

    return True


def telecharger_dalle_directe(nom, url_wms, dossier, ecraser=False):
    """Télécharge une dalle depuis son URL WMS fournie par le TMS IGN."""
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser:
            return "skip"
        # Mode overwrite : supprimer l'existant pour forcer le retéléchargement.
        # On évite de tirer dans une dalle valide qui pourrait servir de fallback
        # en cas d'échec — mais c'est explicitement ce que l'utilisateur demande.
        chemin.unlink()
    chemin_tmp = chemin.parent / (nom + ".tmp")
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            taille = _download_to_tmp(url_wms, chemin_tmp, timeout=(10, 45))
            if taille == 0:
                chemin_tmp.unlink(missing_ok=True)
                return "absent"
            if taille < SEUIL_DALLE_VALIDE:
                chemin_tmp.unlink(missing_ok=True)
                return "absent"
            chemin_tmp.replace(chemin)
            _post_fetch_si_besoin(chemin)
            if not _valider_tif_dalle(chemin):
                chemin.unlink(missing_ok=True)
                raise IOError("GeoTIFF invalide après écriture (fichier tronqué ou corrompu)")
            # Hook post-download : permet à un provider de transformer le tile
            # (ex: us-3dep reprojette NAD83 -> EPSG:3857 ici).
            if hasattr(PROVIDER, "post_download"):
                try:
                    PROVIDER.post_download(chemin)
                except Exception as _e_pd:
                    print(f"  ⚠ post_download {nom} : {type(_e_pd).__name__}: {_e_pd}",
                          flush=True)
            _creer_fichier(chemin)
            return "ok"
        except KeyboardInterrupt:
            chemin_tmp.unlink(missing_ok=True)
            # Propagation au handler top-level (sys.exit(130)) qui finalise
            # le cleanup global (manifeste, lockfiles…). sys.exit(0) ici
            # masquerait l'interruption derrière un code de succès.
            raise
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, IOError) as _e:
            chemin_tmp.unlink(missing_ok=True)
            chemin.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                # Retry silencieux : IGN renvoie 502/400/timeouts en rafale en
                # journée, chaque retry print bourrait la console. Seul l'échec
                # final (3/3) reste visible — la progress bar montre l'avancée.
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR {nom} ({type(_e).__name__}, tentative {tentative}) : {_e}")
                return "erreur"
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
    from rasterio.windows import from_bounds as _win_from_bounds

    chemin = chemin_dalle(dossier_dalles, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser:
            return "skip"
        chemin.unlink(missing_ok=True)

    bx1, by1, bx2, by2 = bbox
    vsi = "/vsicurl/" + url
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                              CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                              VSI_CACHE=True, GDAL_HTTP_TIMEOUT="60"):
                with rasterio.open(vsi) as src:
                    # La bbox arrive dans PROVIDER.CRS_NATIF ; le COG peut être
                    # dans un AUTRE CRS (ex. 3DEP : tuiles en UTM local alors que
                    # CRS_NATIF=3857). On reprojette la bbox vers le CRS réel du
                    # COG avant de fenêtrer (identité si même CRS, ex. ca-nrcan).
                    rbx1, rby1, rbx2, rby2 = bx1, by1, bx2, by2
                    try:
                        _se = src.crs.to_epsg() if src.crs else None
                        _ne = (int(PROVIDER.CRS_NATIF.split(":")[1])
                               if ":" in getattr(PROVIDER, "CRS_NATIF", "") else None)
                        if _se and _ne and _se != _ne:
                            _tf = _get_transformer(PROVIDER.CRS_NATIF, f"EPSG:{_se}")
                            _xs = []; _ys = []
                            for _px, _py in ((bx1, by1), (bx1, by2),
                                             (bx2, by1), (bx2, by2)):
                                _tx, _ty = _tf.transform(_px, _py)
                                _xs.append(_tx); _ys.append(_ty)
                            rbx1, rby1 = min(_xs), min(_ys)
                            rbx2, rby2 = max(_xs), max(_ys)
                    except Exception:
                        pass
                    b = src.bounds
                    # Intersection bbox zone ∩ étendue du COG (dans le CRS du COG)
                    l = max(rbx1, b.left);   r = min(rbx2, b.right)
                    bot = max(rby1, b.bottom); t = min(rby2, b.top)
                    if l >= r or bot >= t:
                        return "absent"          # le COG ne couvre pas la zone
                    win = _win_from_bounds(l, bot, r, t, src.transform)
                    data = src.read(window=win)
                    if data.size == 0:
                        return "absent"
                    profil = src.profile.copy()
                    profil.update(
                        driver="GTiff",
                        height=data.shape[1], width=data.shape[2],
                        transform=src.window_transform(win),
                        compress="deflate", predictor=2, tiled=True,
                        blockxsize=256, blockysize=256, bigtiff="IF_SAFER")
                    with rasterio.open(chemin, "w", **profil) as dst:
                        dst.write(data)
            if not _valider_tif_dalle(chemin):
                chemin.unlink(missing_ok=True)
                raise IOError("COG fenêtré invalide après écriture")
            # Hook post-download (ex. us-tnm : reproject UTM local -> CRS_NATIF),
            # comme le chemin de download direct.
            if hasattr(PROVIDER, "post_download"):
                try:
                    PROVIDER.post_download(chemin)
                except Exception as _e_pd:
                    print(f"  ⚠ post_download {nom} : {type(_e_pd).__name__}: {_e_pd}",
                          flush=True)
            _creer_fichier(chemin)
            return "ok"
        except (OSError, IOError, rasterio.errors.RasterioIOError) as _e:
            chemin.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR fenêtre {nom} ({type(_e).__name__}) : {_e}")
                return "erreur"
    return "erreur"


def telecharger_dalle(x_km, y_km, dossier, compresser=False, ecraser=False):
    nom    = nom_dalle(x_km, y_km)
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser:
            return "skip"
        chemin.unlink()

    url = construire_url_wms(x_km, y_km)
    chemin_tmp = chemin.parent / (nom + ".tmp")

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            taille = _download_to_tmp(url, chemin_tmp, timeout=(10, 45))
            if taille == 0:
                chemin_tmp.unlink(missing_ok=True)
                return "absent"
            if taille < SEUIL_DALLE_VALIDE:
                chemin_tmp.unlink(missing_ok=True)
                return "absent"

            if compresser:
                # Compression DEFLATE via rasterio (remplace gdal_translate CLI)
                try:
                    import rasterio as _rio_d
                    with _rio_d.open(str(chemin_tmp)) as src:
                        profile = src.profile.copy()
                        profile.update({
                            "compress":   "deflate",
                            "predictor":  2,
                            "tiled":      True,
                            "blockxsize": 256,
                            "blockysize": 256,
                        })
                        with _rio_d.open(str(chemin), "w", **profile) as dst:
                            dst.write(src.read())
                    chemin_tmp.unlink(missing_ok=True)
                except Exception:
                    chemin_tmp.replace(chemin)
            else:
                chemin_tmp.replace(chemin)

            _post_fetch_si_besoin(chemin)
            if not _valider_tif_dalle(chemin):
                chemin.unlink(missing_ok=True)
                raise IOError("GeoTIFF invalide après écriture (fichier tronqué ou corrompu)")
            _creer_fichier(chemin)
            return "ok"

        except KeyboardInterrupt:
            chemin_tmp.unlink(missing_ok=True)
            # Propagation au handler top-level (sys.exit(130)).
            raise
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, IOError) as _e:
            chemin_tmp.unlink(missing_ok=True)
            chemin.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                # Cf. telecharger_dalle_directe : retry silencieux pour éviter
                # le bourrage console quand IGN renvoie 502/400/timeouts en rafale.
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR {nom} ({type(_e).__name__}, tentative {tentative}) : {_e}")
                return "erreur"

    return "erreur"

# ============================================================
# ASSEMBLAGE COG (rasterio)
# ============================================================


def _telecharger_osmosis_local():
    """
    Télécharge osmosis dans ./osmosis/ depuis GitHub releases.
    osmosis est un JAR Java autonome — nécessite Java installé.
    """
    import zipfile

    OSMOSIS_DIR = LIDAR2MAP_HOME / "osmosis"
    pattern = "osmosis.bat" if WINDOWS else "osmosis"
    if OSMOSIS_DIR.exists():
        for candidate in sorted(OSMOSIS_DIR.rglob(pattern)):
            if candidate.is_file() and "bin" in candidate.parts:
                return str(candidate)

    # URL stable osmosis 0.49.2
    URL = "https://github.com/openstreetmap/osmosis/releases/download/0.49.2/osmosis-0.49.2.zip"
    zip_path = OSMOSIS_DIR / "osmosis.zip"
    OSMOSIS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  URL  : {URL}")
    print("  Downloading osmosis (~35 MB)...", flush=True)
    try:
        def _prog(n, bs, total):
            if total > 0:
                print("  " + str(min(n*bs*100//total, 100)).rjust(3) + "%",
                      end="\r", flush=True)
        urllib.request.urlretrieve(URL, zip_path, reporthook=_prog)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERROR downloading osmosis: {type(e).__name__}: {e}")
        return None

    print(f"  Extraction osmosis...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        _safe_zip_extractall(z, OSMOSIS_DIR)
    zip_path.unlink(missing_ok=True)

    # Le ZIP extrait dans un sous-dossier versionné (ex: osmosis-0.49.2/)
    # On cherche le binaire par rglob plutôt qu'un chemin fixe
    pattern = "osmosis.bat" if WINDOWS else "osmosis"
    for candidate in sorted(OSMOSIS_DIR.rglob(pattern)):
        if candidate.is_file() and "bin" in candidate.parts:
            if not WINDOWS:
                import stat as _stat
                candidate.chmod(candidate.stat().st_mode | _stat.S_IEXEC)
            print(f"  osmosis installed: {candidate}")
            return str(candidate)
    print("  ERROR: osmosis not found after extraction.")
    return None


def _telecharger_jre_local():
    """
    Télécharge le JRE Temurin (Eclipse Adoptium) dans ./jre/ — portable,
    sans installation système, sans droits admin.
    Fonctionne sur Windows (zip), Linux et macOS (tar.gz), x64 et arm64.
    """
    import tarfile, zipfile

    JRE_DIR = LIDAR2MAP_HOME / "jre"

    # Détection OS
    sys_os = platform.system().lower()
    if sys_os == "windows":
        os_str, ext, java_bin = "windows", "zip",    "bin/java.exe"
    elif sys_os == "darwin":
        os_str, ext, java_bin = "mac",     "tar.gz", "bin/java"
    else:
        os_str, ext, java_bin = "linux",   "tar.gz", "bin/java"

    # Détection architecture
    machine = platform.machine().lower()
    arch_str = "aarch64" if machine in ("arm64", "aarch64") else "x64"

    # URL stable Adoptium API — JRE 21 LTS
    URL = (f"https://api.adoptium.net/v3/binary/latest/21/ga"
           f"/{os_str}/{arch_str}/jre/hotspot/normal/eclipse")

    archive = JRE_DIR / f"jre.{ext}"
    JRE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  URL  : {URL}")
    print(f"  Downloading JRE Temurin 21 ({os_str}/{arch_str}, ~50 MB)...",
          flush=True)
    try:
        # L'API Adoptium fait une redirection 302 vers GitHub.
        # GitHub exige un User-Agent — urlretrieve seul renvoie 403.
        # On résout d'abord l'URL finale, puis on télécharge avec headers.
        _headers = {"User-Agent": "lidar2map/1.0 (JRE bootstrap)",
                    "Accept":     "application/octet-stream"}

        # Résolution de la redirection
        _req = urllib.request.Request(URL, headers=_headers)
        with urllib.request.urlopen(_req, timeout=30) as _resp:
            _final_url = _resp.url  # URL finale après redirection(s)

        # Téléchargement avec progression
        _req2 = urllib.request.Request(_final_url, headers=_headers)
        with urllib.request.urlopen(_req2, timeout=120) as _resp2:
            total = int(_resp2.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            with open(archive, "wb") as _fout:
                while True:
                    buf = _resp2.read(chunk)
                    if not buf:
                        break
                    _fout.write(buf)
                    downloaded += len(buf)
                    if total > 0:
                        pct = min(downloaded * 100 // total, 100)
                        print(f"  {pct:3d}%", end="\r", flush=True)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERROR downloading JRE: {type(e).__name__}: {e}")
        return None

    print("  Extraction JRE...", flush=True)
    if ext == "zip":
        with zipfile.ZipFile(archive, "r") as z:
            _safe_zip_extractall(z, JRE_DIR)
    else:
        with tarfile.open(archive, "r:gz") as t:
            # Python 3.12+ : filter='data' requis pour bloquer les exploits
            # (chemins absolus, traversée ../, liens symboliques sortants).
            # Python 3.11- : pas de support du paramètre → fallback.
            try:
                t.extractall(JRE_DIR, filter='data')
            except TypeError:
                t.extractall(JRE_DIR)
    archive.unlink(missing_ok=True)

    # Le JRE est extrait dans un sous-dossier au nom variable (ex: jdk-21+35-jre)
    # On cherche le binaire java dans n'importe quel sous-dossier
    for candidate in sorted(JRE_DIR.rglob(java_bin)):
        if candidate.exists():
            if not WINDOWS:
                import stat as _stat
                candidate.chmod(candidate.stat().st_mode | _stat.S_IEXEC)
            print(f"  JRE installed: {candidate}")
            return str(candidate)

    print("  ERROR: java binary not found after extraction.")
    return None


def _trouver_java():
    """
    Retourne le chemin vers le binaire java local (~/.lidar2map/jre/).
    Télécharge le JRE Temurin si absent. Jamais le Java système.

    Mode frozen : cherche d'abord dans BUNDLE_DIR/jre/ (JRE embarqué).
    """

    java_bin = "java.exe" if WINDOWS else "java"

    # 1) Mode frozen : JRE bundlé dans l'exe
    if getattr(sys, "frozen", False):
        for candidate in sorted((BUNDLE_DIR / "jre").rglob(java_bin)):
            if candidate.exists():
                return str(candidate)

    # 2) Installation locale persistante (~/.lidar2map/jre/)
    for candidate in sorted((LIDAR2MAP_HOME / "jre").rglob(java_bin)):
        if candidate.exists():
            return str(candidate)

    # 3) Missing: téléchargement automatique
    java = _telecharger_jre_local()
    if not java:
        print("  ERROR: cannot obtain a JRE.")
        print("  Installez Java manuellement : https://adoptium.net/")
    return java


def _trouver_osmosis():
    """Retourne le chemin vers osmosis (installation locale ou téléchargement).
    Même logique que GDAL : pas de fallback PATH système.
    Prérequis : appeler _trouver_java() avant (responsabilité de l'appelant).

    Mode frozen : cherche d'abord dans BUNDLE_DIR/osmosis/ (osmosis embarqué,
    avec le plugin mapwriter pré-installé dans son lib/)."""
    # 1) Mode frozen : osmosis bundlé dans l'exe
    if getattr(sys, "frozen", False):
        pattern = "osmosis.bat" if WINDOWS else "osmosis"
        for candidate in sorted((BUNDLE_DIR / "osmosis").rglob(pattern)):
            if candidate.is_file() and "bin" in candidate.parts:
                return str(candidate)

    # 2) Installation locale persistante (~/.lidar2map/osmosis/)
    local_bat = LIDAR2MAP_HOME / "osmosis" / "bin" / "osmosis.bat"
    local_sh  = LIDAR2MAP_HOME / "osmosis" / "bin" / "osmosis"
    if WINDOWS and local_bat.exists():
        return str(local_bat)
    if not WINDOWS and local_sh.exists():
        return str(local_sh)

    # 3) Missing: téléchargement automatique
    return _telecharger_osmosis_local()


_MAPWRITER_VERSION = "0.25.0"
_MAPWRITER_JAR     = f"mapsforge-map-writer-{_MAPWRITER_VERSION}-jar-with-dependencies.jar"
_MAPWRITER_URL     = (
    f"https://repo1.maven.org/maven2/org/mapsforge/mapsforge-map-writer"
    f"/{_MAPWRITER_VERSION}/{_MAPWRITER_JAR}"
)


def _verifier_mapwriter():
    """
    Vérifie que le plugin mapsforge-map-writer est installé dans le dossier
    plugins d'osmosis. Télécharge automatiquement si absent.

    Dossier plugins (toutes plateformes) :
      Windows  : %USERPROFILE%\\.openstreetmap\\osmosis\\plugins\\
      Linux    : ~/.openstreetmap/osmosis/plugins/
      macOS    : ~/.openstreetmap/osmosis/plugins/

    Mode frozen : le plugin est embarqué dans osmosis/lib/ (osmosis.bat
    bundlé inclut le jar dans son CLASSPATH) — rien à vérifier ici.
    """
    # Mode frozen : plugin déjà sur le classpath d'osmosis, court-circuit.
    if getattr(sys, "frozen", False):
        return True

    plugins_dir = Path.home() / ".openstreetmap" / "osmosis" / "plugins"
    jar_path    = plugins_dir / _MAPWRITER_JAR

    if jar_path.exists():
        return True

    print(f"  URL  : {_MAPWRITER_URL}")
    print(f"  mapwriter plugin missing - downloading ({_MAPWRITER_JAR})...",
          flush=True)
    try:
        plugins_dir.mkdir(parents=True, exist_ok=True)

        def _prog(n, bs, total):
            if total > 0:
                print("  " + str(min(n * bs * 100 // total, 100)).rjust(3) + "%",
                      end="\r", flush=True)

        urllib.request.urlretrieve(_MAPWRITER_URL, jar_path, reporthook=_prog)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERROR downloading mapwriter: {type(e).__name__}: {e}")
        print(f"  Download manually:\n    {_MAPWRITER_URL}")
        print(f"  and copy it into:\n    {plugins_dir}")
        return False

    print(f"  Plugin installed: {jar_path}")
    return True


# ── --telecharger-outils ──────────────────────────────────────────────────────
# Placé ici car nécessite _trouver_java() et _trouver_osmosis() définis
# ci-dessus. Le flag est détecté tôt (avant bootstrap) pour passer dans
# le re-exec venv, mais exécuté ici pour que les fonctions soient disponibles.
if _TELECHARGER_OUTILS:
    print()
    print("  ── Downloading tools (osmosis + JRE + mapwriter) ──────")
    print()
    _java = _trouver_java()
    if _java:
        print(f"  ✓ JRE already present: {_java}")
    else:
        print("  ⚠ JRE: download failed")
    _osmo = _trouver_osmosis()
    if _osmo:
        print(f"  ✓ osmosis already present: {_osmo}")
    else:
        print("  ⚠ osmosis: download failed")
    # Plugin mapsforge-map-writer : indispensable pour générer les .map OSM.
    # Sans lui, osmosis échoue avec "Task type mapfile-writer doesn't exist".
    # Le spec PyInstaller le récupère depuis ~/.openstreetmap/osmosis/plugins/
    # pour le bundler dans osmosis/lib/ du .app/.exe.
    if _verifier_mapwriter():
        print(f"  ✓ mapwriter present: ~/.openstreetmap/osmosis/plugins/{_MAPWRITER_JAR}")
    else:
        print("  ⚠ mapwriter: download failed - .map generation will fail")
    print()
    sys.exit(0)


def _trouver_outil_gdal(nom):
    """[DEPRECATED après refactor rasterio] Cherche un exe GDAL CLI.

    Cette fonction est conservée pour compatibilité avec les variables
    encore initialisées dans le code (gdaldem, gdalwarp, gdalbuildvrt etc.),
    mais après le refactor rasterio (étapes 1-7) ces exes ne sont plus
    appelés. La fonction retourne maintenant None sans déclencher
    d'auto-installation système de GDAL.

    Si une future version a vraiment besoin d'un outil GDAL CLI (peu probable),
    il faudra restaurer la stratégie 1+2+3+4 d'origine.
    """
    return None


def _geoinfo_depuis_gdalinfo(src_tif, env=None):
    """
    Retourne (geotransform_str, srs_wkt) pour src_tif via rasterio.

    geotransform_str : 6 valeurs séparées par virgules (xmin, xres, 0, ymax, 0, -yres)

    Le paramètre `env` est conservé pour compatibilité historique mais n'est
    plus utilisé : rasterio embarque sa propre libgdal/proj.db via le wheel pip.
    Pas besoin de PROJ_LIB ou GDAL_DATA externes.
    """
    try:
        import rasterio
        with rasterio.open(str(src_tif)) as ds:
            tr = ds.transform   # affine: a, b, c, d, e, f
            # tr.a = xres, tr.b = 0 (pas de rotation), tr.c = xmin
            # tr.d = 0, tr.e = -yres (négatif pour y descend), tr.f = ymax
            gt = [tr.c, tr.a, tr.b, tr.f, tr.d, tr.e]  # ordre GDAL classique
            srs_wkt = ds.crs.to_wkt() if ds.crs else ""
            return ",".join(str(v) for v in gt), srs_wkt
    except Exception:
        return None, None


def _sauver_array_georef(arr, src_tif, dst_tif, gdal_translate_exe=None, env=None):
    """
    Sauvegarde un numpy array uint8 (2D niveaux de gris ou 3D RGB) en GeoTIFF
    en copiant le géoréférencement de src_tif via rasterio.

    arr   : numpy uint8 shape (H,W) pour L, (H,W,3) pour RGB

    Les paramètres `gdal_translate_exe` et `env` sont conservés pour compatibilité
    historique mais ne sont plus utilisés (rasterio est désormais une dépendance
    obligatoire — voir _installer_deps).
    """
    import numpy as np
    import rasterio

    n_bands = 1 if arr.ndim == 2 else arr.shape[2]

    with rasterio.open(str(src_tif)) as src:
        profile = src.profile.copy()

    profile.update(
        dtype     = "uint8",
        count     = n_bands,
        compress  = "deflate",
        predictor = 2,
        tiled     = True,
        blockxsize = 512,
        blockysize = 512,
        bigtiff   = "IF_SAFER",
    )
    # Supprimer les clés incompatibles éventuelles
    for k in ("nodata",):
        profile.pop(k, None)

    _t0 = time.time()
    with rasterio.open(str(dst_tif), "w", **profile) as dst:
        if arr.ndim == 2:
            dst.write(arr.astype(np.uint8), 1)
        else:
            for b in range(n_bands):
                dst.write(arr[:, :, b].astype(np.uint8), b + 1)
    print(f"  rasterio write OK  ({_hms(time.time()-_t0)})", flush=True)


# ── Helpers lecture DEM ───────────────────────────────────────────────────────

def _lire_dem_rasterio(src_path):
    """
    Lit un GeoTIFF DEM (bande 1) et retourne un numpy float32.

    Utilise rasterio en priorité (gestion native du nodata, DEFLATE, BigTIFF).
    Fallback PIL si rasterio absent.

    Retourne : (arr_float32, nodata_value | None)
    """
    import numpy as np
    try:
        import rasterio as _rio
        with _rio.open(str(src_path)) as src:
            arr = src.read(1).astype(np.float32)
            nodata = src.nodata
        return arr, nodata
    except ImportError:
        pass
    except Exception as e_rio:
        print(f"  WARNING rasterio read ({e_rio}) — repli PIL", flush=True)

    from PIL import Image as _Img
    return np.array(_Img.open(str(src_path)), dtype=np.float32), None


def _nodata_mask(arr, nodata=None):
    """Masque nodata unifié : sentinelles hors plage altimétrique (|z| > 9000 m,
    couvre le -9999 IGN comme les ±3.4e38) + valeur nodata déclarée du raster.

    Convention unique partagée par hillshade/SVF/LRM/RRIM — avant ce helper,
    les trois fonctions chunked utilisaient chacune une variante différente
    (magique seul, déclaré seul, ou les deux), donc un provider avec un nodata
    déclaré dans [-9000, 9000] passait au travers du SVF mais pas du LRM.
    """
    import numpy as np
    mask = (arr < -9000) | (arr > 9000)
    if nodata is not None:
        if np.isnan(nodata):
            mask |= np.isnan(arr)
        else:
            mask |= (arr == nodata)
    return mask


def _percentiles_grille(src_path, halo, calc_block, p_lo, p_hi):
    """Percentiles globaux estimés sur une grille 3×3 de fenêtres réparties
    sur toute l'étendue du raster (fractions 0.2/0.5/0.8 en x et y).

    calc_block : fenêtre float32 (avec halo) → array de valeurs, NaN aux
    pixels invalides (nodata). Les valeurs finies de toutes les fenêtres
    sont mises en commun avant le calcul des percentiles.

    Un crop unique rendrait le stretch dépendant de ce que contient ce crop
    (même terrain → rendu différent selon le cadrage) — régression de rendu
    silencieuse déjà rencontrée sur le SVF, d'où la grille. Partagé par
    SVF / LRM / RRIM.

    Retourne (lo, hi, n_valides) ou None si trop peu de pixels valides.
    """
    import numpy as np
    import rasterio as _rio
    from rasterio.windows import Window
    SAMPLE = 192
    s_half = SAMPLE // 2
    _fracs = (0.2, 0.5, 0.8)
    pool = []
    with _rio.open(str(src_path)) as src:
        H, W = src.height, src.width
        for _fy in _fracs:
            cy = int(H * _fy)
            for _fx in _fracs:
                cx = int(W * _fx)
                r0 = max(0, cy - s_half - halo)
                c0 = max(0, cx - s_half - halo)
                r1 = min(H, cy + s_half + halo)
                c1 = min(W, cx + s_half + halo)
                if r1 - r0 < 8 or c1 - c0 < 8:
                    continue
                win = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float32)
                vals = calc_block(win)
                pool.append(vals[np.isfinite(vals)])
    valid = np.concatenate(pool) if pool else np.empty(0, dtype=np.float32)
    if len(valid) < 100:
        return None
    return (float(np.percentile(valid, p_lo)),
            float(np.percentile(valid, p_hi)),
            len(valid))


# ── Hillshade et slope numpy (remplacent gdaldem CLI) ─────────────────────────

# Cache des kernels Numba (compilation paresseuse au 1er appel, partagée entre
# tous les modes — évite la double compilation entre _svf_numpy et _svf_chunked,
# et entre les variantes hillshade/multi/slope).
_NUMBA_KERNELS_CACHE = {}


def _get_numba_horn_kernels():
    """Compile et cache les kernels Numba pour Horn (hillshade, multi, slope).

    Une seule passe sur le DEM par kernel : gradient Horn 3x3 + projection
    solaire + écriture uint8 directement, sans buffers intermédiaires float32
    (slope, aspect, dz_dx, dz_dy, pad). Edge replication via clamp d'indices.

    Retourne (hillshade_kernel, multi_kernel, slope_kernel) ou None si numba
    indisponible.
    """
    if "horn" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["horn"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _hillshade_kernel(dem, dx, dy, az_math_rad, zen_rad, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            cos_z = _math.cos(zen_rad)
            sin_z = _math.sin(zen_rad)
            cos_a = _math.cos(az_math_rad)
            sin_a = _math.sin(az_math_rad)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata remplacé par la valeur centrale
                        # (convention gdaldem) : sans ça, un voisin à -9999
                        # produit un gradient énorme → halo noir/blanc d'1 px
                        # autour des zones hors couverture.
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    g2 = dz_dx * dz_dx + dz_dy * dz_dy
                    # Forme analytique évitant atan/atan2 :
                    # cos(slope)=1/sqrt(1+g²), sin(slope)*cos(aspect)=-dz_dx/sqrt(1+g²),
                    # sin(slope)*sin(aspect)=dz_dy/sqrt(1+g²)
                    # → hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) / sqrt(1+g²)
                    inv_sqrt = 1.0 / _math.sqrt(1.0 + g2)
                    hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) * inv_sqrt
                    if hs < 0.0:
                        hs = 0.0
                    elif hs > 1.0:
                        hs = 1.0
                    out[row, col] = int(hs * 254.0 + 1.0)
            return out

        @_nb.njit(parallel=True, fastmath=True)
        def _multi_kernel(dem, dx, dy, zen_rad, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            cos_z = _math.cos(zen_rad)
            sin_z = _math.sin(zen_rad)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            # Azimuts GDAL : 225, 270, 315, 360 → az_math = 360 - az + 90
            # → 225, 180, 135, 90
            az0_c = _math.cos(_math.radians(225.0)); az0_s = _math.sin(_math.radians(225.0))
            az1_c = _math.cos(_math.radians(180.0)); az1_s = _math.sin(_math.radians(180.0))
            az2_c = _math.cos(_math.radians(135.0)); az2_s = _math.sin(_math.radians(135.0))
            az3_c = _math.cos(_math.radians( 90.0)); az3_s = _math.sin(_math.radians( 90.0))
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata → valeur centrale (cf. _hillshade_kernel)
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    g2 = dz_dx * dz_dx + dz_dy * dz_dy
                    g_len = _math.sqrt(g2)
                    inv_sqrt = 1.0 / _math.sqrt(1.0 + g2)
                    cos_s = inv_sqrt
                    sin_s = g_len * inv_sqrt
                    if g_len > 1e-12:
                        cos_asp = -dz_dx / g_len
                        sin_asp =  dz_dy / g_len
                    else:
                        cos_asp = 1.0
                        sin_asp = 0.0
                    hs_sum = 0.0
                    w_sum  = 0.0
                    # 4 azimuts déroulés
                    for k in range(4):
                        if k == 0:
                            cAz = az0_c; sAz = az0_s
                        elif k == 1:
                            cAz = az1_c; sAz = az1_s
                        elif k == 2:
                            cAz = az2_c; sAz = az2_s
                        else:
                            cAz = az3_c; sAz = az3_s
                        cos_d = cAz * cos_asp + sAz * sin_asp
                        sin_d = sAz * cos_asp - cAz * sin_asp
                        hs = cos_z * cos_s + sin_z * sin_s * cos_d
                        if hs < 0.0:
                            hs = 0.0
                        elif hs > 1.0:
                            hs = 1.0
                        wi = sin_d * sin_d
                        hs_sum += hs * wi
                        w_sum  += wi
                    if w_sum < 1e-6:
                        w_sum = 1e-6
                    hs_avg = hs_sum / w_sum
                    if hs_avg < 0.0:
                        hs_avg = 0.0
                    elif hs_avg > 1.0:
                        hs_avg = 1.0
                    out[row, col] = int(hs_avg * 254.0 + 1.0)
            return out

        @_nb.njit(parallel=True, fastmath=True)
        def _slope_kernel(dem, dx, dy, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    z0 = dem[row, col]
                    if has_nodata and z0 == nodata:
                        out[row, col] = 0
                        continue
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    if has_nodata:
                        # Voisin nodata → valeur centrale (cf. _hillshade_kernel)
                        if a  == nodata: a  = z0
                        if b  == nodata: b  = z0
                        if c  == nodata: c  = z0
                        if d  == nodata: d  = z0
                        if f  == nodata: f  = z0
                        if g  == nodata: g  = z0
                        if hv == nodata: hv = z0
                        if i  == nodata: i  = z0
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    slope_deg = _math.degrees(_math.atan(_math.sqrt(dz_dx * dz_dx + dz_dy * dz_dy)))
                    if slope_deg < 0.0:
                        slope_deg = 0.0
                    elif slope_deg > 90.0:
                        slope_deg = 90.0
                    # Étalement 0–90° → 1–255 (0 réservé nodata, comme les
                    # hillshades). Sans ça, le TIF stocke des degrés bruts
                    # (max 90/255) → tuiles quasi noires.
                    out[row, col] = int(slope_deg * (254.0 / 90.0) + 1.0)
            return out

        kernels = (_hillshade_kernel, _multi_kernel, _slope_kernel)
        _NUMBA_KERNELS_CACHE["horn"] = kernels
        return kernels
    except ImportError:
        _NUMBA_KERNELS_CACHE["horn"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernels Horn : erreur compilation ({_e}) — fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["horn"] = None
        return None


def _get_numba_svf_kernel():
    """Compile et cache le kernel Numba SVF (ray-casting horizon avec interp
    bilinéaire). Réutilisé par _svf_numpy et _svf_chunked — évite la double
    compilation initiale (~20 s × 2).
    """
    if "svf" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_kernel(dem, n_dir, max_r, res, conv):
            # conv : 0 = SVF flux cos²γ (contraste) ; 1 = SVF RVT 1−sin γ ;
            #        2 = openness positive (Yokoyama 2002) : φ/π, φ = π/2 − β
            #            où β = angle d'horizon max (NON clampé : négatif sur
            #            crête) — crêtes claires ;
            #        3 = openness négative INVERSÉE : (π/2 − δ)/π, δ = angle
            #            min (vue la plus descendante) — fossés/chemins creux
            #            sombres, lecture alignée sur le SVF.
            # Argument runtime → une seule compilation gère les 4 variantes.
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            out = _np.zeros((h, w), dtype=_np.float32)
            for row in _nb.prange(h):
                for col in range(w):
                    z0 = dem[row, col]
                    svf_sum = 0.0
                    for k in range(n_dir):
                        angle = k * PI2 / n_dir
                        ddx =  _math.sin(angle)
                        ddy = -_math.cos(angle)
                        max_tan = -1e38
                        min_tan =  1e38
                        for r in range(1, max_r + 1):
                            rr = row + ddy * r
                            cc = col + ddx * r
                            # floor calculé une seule fois (réutilisé pour
                            # l'indice entier ET la partie fractionnaire).
                            rr_fl = _math.floor(rr)
                            cc_fl = _math.floor(cc)
                            r0i = int(rr_fl)
                            c0i = int(cc_fl)
                            r1i = r0i + 1
                            c1i = c0i + 1
                            if r0i < 0:       r0i = 0
                            elif r0i > h - 1: r0i = h - 1
                            if r1i < 0:       r1i = 0
                            elif r1i > h - 1: r1i = h - 1
                            if c0i < 0:       c0i = 0
                            elif c0i > w - 1: c0i = w - 1
                            if c1i < 0:       c1i = 0
                            elif c1i > w - 1: c1i = w - 1
                            fr = rr - rr_fl
                            fc = cc - cc_fl
                            zn = (dem[r0i, c0i] * (1 - fr) * (1 - fc) +
                                  dem[r0i, c1i] * (1 - fr) *      fc  +
                                  dem[r1i, c0i] *      fr  * (1 - fc) +
                                  dem[r1i, c1i] *      fr  *      fc)
                            dist_m = r * res
                            tan_a  = (zn - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a
                            if tan_a < min_tan:
                                min_tan = tan_a
                        if conv == 0:
                            # SVF flux : cos²γ = 1/(1+tan²γ) — contraste
                            mt = max_tan if max_tan > 0.0 else 0.0
                            svf_sum += 1.0 / (1.0 + mt * mt)
                        elif conv == 1:
                            # SVF RVT (Kokalj/Hesse) : 1 − sin γ (archéo)
                            mt = max_tan if max_tan > 0.0 else 0.0
                            svf_sum += 1.0 - mt / _math.sqrt(1.0 + mt * mt)
                        elif conv == 2:
                            # Openness positive : φ/π ∈ (0,1)
                            svf_sum += 0.5 - _math.atan(max_tan) / _math.pi
                        else:
                            # Openness négative inversée : (π/2 − δ)/π
                            svf_sum += 0.5 - _math.atan(min_tan) / _math.pi
                    out[row, col] = svf_sum / n_dir
            return out

        _NUMBA_KERNELS_CACHE["svf"] = _svf_kernel
        return _svf_kernel
    except ImportError:
        _NUMBA_KERNELS_CACHE["svf"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernel SVF : erreur compilation ({_e}) — fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["svf"] = None
        return None


def _get_numba_svf_opos_kernel():
    """Kernel FUSIONNÉ SVF flux (conv=0) + openness positif (conv=2) : un seul
    scan d'horizon produit les DEUX réductions (toutes deux dérivées de max_tan).
    Sert au composite VAT, qui sinon refait le scan coûteux deux fois. Le scan et
    les deux formules sont identiques à ceux de _svf_kernel (conv 0 et 2), donc
    sorties numériquement identiques (min_tan, utile au seul oneg, est omis)."""
    if "svf_opos" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf_opos"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_opos_kernel(dem, n_dir, max_r, res):
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            svf  = _np.zeros((h, w), dtype=_np.float32)
            opos = _np.zeros((h, w), dtype=_np.float32)
            for row in _nb.prange(h):
                for col in range(w):
                    z0 = dem[row, col]
                    svf_sum  = 0.0
                    opos_sum = 0.0
                    for k in range(n_dir):
                        angle = k * PI2 / n_dir
                        ddx =  _math.sin(angle)
                        ddy = -_math.cos(angle)
                        max_tan = -1e38
                        for r in range(1, max_r + 1):
                            rr = row + ddy * r
                            cc = col + ddx * r
                            rr_fl = _math.floor(rr)
                            cc_fl = _math.floor(cc)
                            r0i = int(rr_fl)
                            c0i = int(cc_fl)
                            r1i = r0i + 1
                            c1i = c0i + 1
                            if r0i < 0:       r0i = 0
                            elif r0i > h - 1: r0i = h - 1
                            if r1i < 0:       r1i = 0
                            elif r1i > h - 1: r1i = h - 1
                            if c0i < 0:       c0i = 0
                            elif c0i > w - 1: c0i = w - 1
                            if c1i < 0:       c1i = 0
                            elif c1i > w - 1: c1i = w - 1
                            fr = rr - rr_fl
                            fc = cc - cc_fl
                            zn = (dem[r0i, c0i] * (1 - fr) * (1 - fc) +
                                  dem[r0i, c1i] * (1 - fr) *      fc  +
                                  dem[r1i, c0i] *      fr  * (1 - fc) +
                                  dem[r1i, c1i] *      fr  *      fc)
                            dist_m = r * res
                            tan_a  = (zn - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a
                        # SVF flux : cos²γ = 1/(1+tan²γ), tan clampé >= 0
                        mt = max_tan if max_tan > 0.0 else 0.0
                        svf_sum  += 1.0 / (1.0 + mt * mt)
                        # Openness positive : 0.5 − atan(max_tan)/π (NON clampé)
                        opos_sum += 0.5 - _math.atan(max_tan) / _math.pi
                    svf[row, col]  = svf_sum  / n_dir
                    opos[row, col] = opos_sum / n_dir
            return svf, opos

        _NUMBA_KERNELS_CACHE["svf_opos"] = _svf_opos_kernel
        return _svf_opos_kernel
    except ImportError:
        _NUMBA_KERNELS_CACHE["svf_opos"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernel SVF+opos : erreur compilation ({_e})", flush=True)
        _NUMBA_KERNELS_CACHE["svf_opos"] = None
        return None


def _get_numba_svf_sweep_kernel():
    """Sweep-horizon SVF avec running max sur deque (upper convex hull).

    Algorithme :
    - Pour chaque direction θ, balayage de lignes parallèles grid-aligned
      à travers la grille
    - Chaque pixel visité exactement une fois par direction
    - Maintient une deque des points "skyline" passés (upper convex hull)
    - Pop arrière les points dominés à l'ajout (préserve la propriété de hull)
    - Pop avant les points hors fenêtre max_r (cap distance)
    - Horizon angle = scan du hull, query en O(hull_size) amorti

    Complexité : O(W·H·N·hull_size_moyen) — la query re-scanne tout le hull à
    chaque pixel. hull_size reste petit (~5-10 en terrain naturel), d'où le
    gain massif vs O(W·H·N·max_r) du ray-cast classique.

    Pour terrain naturel (hull_size ~5-10), speedup vs ray-cast bilinéaire :
        max_r=40    (SVF 20m)   → ~×5-15
        max_r=200   (SVF 100m)  → ~×30-50
        max_r=40000 (SVF 20km)  → ~×500+

    Trade-off : nearest-neighbor pixel access le long de la scan-line (pas
    d'interp bilinéaire sub-pixel). Aliasing négligeable pour structures
    > 1-2 px sur DEM 0.5 m/px.

    ⚠ Sémantique des directions : ce kernel balaie en direction (ddx, ddy) et
    accumule l'horizon depuis les pixels passés sur la scan-line, qui sont
    donc en direction -θ par rapport au pixel courant. Pour SVF la somme sur
    N directions équi-réparties est invariante par cette permutation (-θ_k
    ≡ θ_{N-k} mod 2π) — résultat numérique correct. À NE PAS réutiliser tel
    quel pour un calcul asymétrique single-direction (ex: horizon à un
    azimut donné, ombre solaire) : inverser le sens du balayage ou
    réinterpréter k.
    """
    if "svf_sweep" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf_sweep"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_sweep_kernel(dem, n_dir, max_r, res, conv):
            # conv : 0 = flux cos²γ ; 1 = RVT 1−sin γ (cf. _svf_kernel).
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            out = _np.zeros((h, w), dtype=_np.float32)
            # Capacité deque : max_r + petite marge pour gérer push avant pop
            DEQ_CAP = max_r + 8

            for k_dir in range(n_dir):
                angle = k_dir * PI2 / n_dir
                ddx =  _math.sin(angle)
                ddy = -_math.cos(angle)
                abs_dx = abs(ddx)
                abs_dy = abs(ddy)

                if abs_dx >= abs_dy:
                    # ── Direction x-dominante : scan-lines balaient en x ──────
                    sx = 1 if ddx > 0 else -1
                    slope_y = ddy / abs_dx  # |slope_y| <= 1
                    step_dist = res * _math.sqrt(1.0 + slope_y * slope_y)
                    # max_steps = nombre max de steps scan-line correspondant à max_r px le long du rayon
                    max_steps_back = int(max_r / _math.sqrt(1.0 + slope_y * slope_y) + 0.5)
                    if max_steps_back < 1:
                        max_steps_back = 1
                    # slope appliqué dans le sens du balayage
                    slope_y_signed = slope_y if sx > 0 else -slope_y
                    # Couverture des seed_y0 : chaque pixel (r, c) est sur seed_y0 = round(r - c_progress * slope)
                    # où c_progress = c si sx>0 sinon (w-1-c). Etendre la plage pour couvrir tout.
                    extra = int(_math.ceil(abs(slope_y) * w)) + 2
                    y0_min = -extra
                    y0_max = h + extra

                    for seed_y0 in _nb.prange(y0_min, y0_max + 1):
                        # Buffers deque (per-scan-line, alloués par numba dans la prange)
                        deque_step = _np.empty(DEQ_CAP, dtype=_np.int32)
                        deque_z    = _np.empty(DEQ_CAP, dtype=_np.float32)
                        head = 0
                        tail = 0

                        # Itération en x dans le sens sx
                        if sx > 0:
                            c_start = 0
                            c_step = 1
                            c_n = w
                        else:
                            c_start = w - 1
                            c_step = -1
                            c_n = w

                        for step_idx in range(c_n):
                            c = c_start + step_idx * c_step
                            y_real = seed_y0 + step_idx * slope_y_signed
                            r = int(y_real + 0.5) if y_real >= 0.0 else int(y_real - 0.5)

                            if r < 0 or r >= h:
                                continue
                            z_curr = dem[r, c]

                            # Pop avant : points hors fenêtre max_r
                            while head != tail and (step_idx - deque_step[head]) > max_steps_back:
                                head = (head + 1) % DEQ_CAP

                            # Query : max slope du hull vers (step_idx, z_curr)
                            max_tan = 0.0
                            idx = head
                            while idx != tail:
                                past_step = deque_step[idx]
                                past_z    = deque_z[idx]
                                dist = (step_idx - past_step) * step_dist
                                if dist > 0.0:
                                    tan_a = (past_z - z_curr) / dist
                                    if tan_a > max_tan:
                                        max_tan = tan_a
                                idx = (idx + 1) % DEQ_CAP

                            # Pop arrière : maintien upper convex hull
                            # Tant qu'on a >= 2 points en queue, vérifier si l'avant-dernier
                            # est sous la droite (avant-avant-dernier → new). Si oui, pop.
                            while True:
                                # Taille deque
                                sz = (tail - head + DEQ_CAP) % DEQ_CAP
                                if sz < 2:
                                    break
                                tm1 = (tail - 1) % DEQ_CAP
                                tm2 = (tail - 2) % DEQ_CAP
                                s2 = deque_step[tm1]; z2 = deque_z[tm1]
                                s1 = deque_step[tm2]; z1 = deque_z[tm2]
                                # Upper hull : s2 doit être au-DESSUS de la droite (s1,z1)→(step_idx,z_curr)
                                # i.e. (z2 - z1) * (step_idx - s1) > (s2 - s1) * (z_curr - z1)
                                lhs = (z2 - z1) * (step_idx - s1)
                                rhs = (s2 - s1) * (z_curr - z1)
                                if lhs <= rhs:
                                    # s2 sous la droite → dominé, pop
                                    tail = tm1
                                else:
                                    break

                            # Push (step_idx, z_curr)
                            deque_step[tail] = step_idx
                            deque_z[tail]    = z_curr
                            tail = (tail + 1) % DEQ_CAP

                            # Accumulation SVF
                            # conv 0 = flux cos²γ ; conv 1 = RVT 1−sin γ (max_tan = tan γ ≥ 0)
                            if conv == 0:
                                out[r, c] += 1.0 / (1.0 + max_tan * max_tan)
                            else:
                                out[r, c] += 1.0 - max_tan / _math.sqrt(1.0 + max_tan * max_tan)
                else:
                    # ── Direction y-dominante : scan-lines balaient en y ──────
                    sy = 1 if ddy > 0 else -1
                    slope_x = ddx / abs_dy  # |slope_x| <= 1
                    step_dist = res * _math.sqrt(1.0 + slope_x * slope_x)
                    max_steps_back = int(max_r / _math.sqrt(1.0 + slope_x * slope_x) + 0.5)
                    if max_steps_back < 1:
                        max_steps_back = 1
                    slope_x_signed = slope_x if sy > 0 else -slope_x

                    extra = int(_math.ceil(abs(slope_x) * h)) + 2
                    x0_min = -extra
                    x0_max = w + extra

                    for seed_x0 in _nb.prange(x0_min, x0_max + 1):
                        deque_step = _np.empty(DEQ_CAP, dtype=_np.int32)
                        deque_z    = _np.empty(DEQ_CAP, dtype=_np.float32)
                        head = 0
                        tail = 0

                        if sy > 0:
                            r_start = 0
                            r_step = 1
                            r_n = h
                        else:
                            r_start = h - 1
                            r_step = -1
                            r_n = h

                        for step_idx in range(r_n):
                            r = r_start + step_idx * r_step
                            x_real = seed_x0 + step_idx * slope_x_signed
                            c = int(x_real + 0.5) if x_real >= 0.0 else int(x_real - 0.5)

                            if c < 0 or c >= w:
                                continue
                            z_curr = dem[r, c]

                            while head != tail and (step_idx - deque_step[head]) > max_steps_back:
                                head = (head + 1) % DEQ_CAP

                            max_tan = 0.0
                            idx = head
                            while idx != tail:
                                past_step = deque_step[idx]
                                past_z    = deque_z[idx]
                                dist = (step_idx - past_step) * step_dist
                                if dist > 0.0:
                                    tan_a = (past_z - z_curr) / dist
                                    if tan_a > max_tan:
                                        max_tan = tan_a
                                idx = (idx + 1) % DEQ_CAP

                            while True:
                                sz = (tail - head + DEQ_CAP) % DEQ_CAP
                                if sz < 2:
                                    break
                                tm1 = (tail - 1) % DEQ_CAP
                                tm2 = (tail - 2) % DEQ_CAP
                                s2 = deque_step[tm1]; z2 = deque_z[tm1]
                                s1 = deque_step[tm2]; z1 = deque_z[tm2]
                                lhs = (z2 - z1) * (step_idx - s1)
                                rhs = (s2 - s1) * (z_curr - z1)
                                if lhs <= rhs:
                                    tail = tm1
                                else:
                                    break

                            deque_step[tail] = step_idx
                            deque_z[tail]    = z_curr
                            tail = (tail + 1) % DEQ_CAP

                            # conv 0 = flux cos²γ ; conv 1 = RVT 1−sin γ (max_tan = tan γ ≥ 0)
                            if conv == 0:
                                out[r, c] += 1.0 / (1.0 + max_tan * max_tan)
                            else:
                                out[r, c] += 1.0 - max_tan / _math.sqrt(1.0 + max_tan * max_tan)

            # Normalisation : moyenne sur n_dir
            inv_n = 1.0 / n_dir
            for r in _nb.prange(h):
                for c in range(w):
                    out[r, c] *= inv_n
            return out

        _NUMBA_KERNELS_CACHE["svf_sweep"] = _svf_sweep_kernel
        return _svf_sweep_kernel
    except ImportError:
        _NUMBA_KERNELS_CACHE["svf_sweep"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernel SVF sweep : erreur compilation ({_e})", flush=True)
        _NUMBA_KERNELS_CACHE["svf_sweep"] = None
        return None


def _appliquer_z_factor(dem_f, z_factor, nodata):
    """Multiplie le DEM par z_factor en préservant les valeurs nodata.

    Sans cette précaution, nodata × z ≠ nodata et la détection nodata des
    kernels (comparaison d'égalité) échoue silencieusement dès que z ≠ 1.
    """
    import numpy as np
    if z_factor == 1.0:
        return dem_f
    if nodata is None:
        return dem_f * np.float32(z_factor)
    m = _nodata_mask(dem_f, nodata)
    out = dem_f * np.float32(z_factor)
    out[m] = dem_f[m]
    return out


def _remplir_nodata_moyenne(dem_f, nodata):
    """(fallback numpy sans numba) Remplit les nodata par la moyenne des
    pixels valides avant le calcul de gradient Horn — supprime le halo
    noir/blanc d'1 px autour des trous de couverture (les kernels Numba
    appliquent la convention gdaldem exacte : voisin nodata → centre).

    Retourne (dem_rempli, mask_nodata).
    """
    import numpy as np
    m = _nodata_mask(dem_f, nodata)
    if not m.any():
        return dem_f, m
    valid = dem_f[~m]
    fill = float(valid.mean()) if valid.size else 0.0
    out = dem_f.copy()
    out[m] = fill
    return out, m


def _calc_slope_aspect(dem, dx=0.5, dy=0.5):
    """Calcule slope (radians) et aspect (radians) d'un DEM via la formule Horn 1981.

    Horn 1981 utilise une fenêtre 3x3 avec pondération centrale 2× pour
    limiter le bruit. C'est la formule par défaut de gdaldem.

    dx, dy : taille du pixel en mètres (X et Y, identiques pour LiDAR)

    Retourne (slope_rad, aspect_rad) en arrays float32 même shape que dem.
    """
    import numpy as np

    # Convolution 3x3 manuelle via padding + slicing — beaucoup plus rapide
    # que scipy.ndimage.convolve sur ces matrices simples
    dem = dem.astype(np.float32)
    pad = np.pad(dem, 1, mode="edge")  # edge replication (compat GDAL)
    a = pad[0:-2, 0:-2]; b = pad[0:-2, 1:-1]; c = pad[0:-2, 2:  ]
    d = pad[1:-1, 0:-2];                       f = pad[1:-1, 2:  ]
    g = pad[2:  , 0:-2]; h = pad[2:  , 1:-1]; i = pad[2:  , 2:  ]

    # dz/dx (Horn) : ((c + 2f + i) - (a + 2d + g)) / (8 * dx)
    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) / (8.0 * dx)
    # dz/dy (Horn) : ((g + 2h + i) - (a + 2b + c)) / (8 * dy)
    # Note : dans GDAL, l'axe Y est inversé (origine en haut-gauche), donc le
    # signe de dy peut différer selon les conventions. On garde la convention
    # Horn standard ici.
    dz_dy = ((g + 2.0 * h + i) - (a + 2.0 * b + c)) / (8.0 * dy)

    # Slope (radians) : atan(sqrt(dz_dx² + dz_dy²))
    slope = np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))

    # Aspect (radians) : atan2(dz_dy, -dz_dx)
    # Convention GDAL : aspect = 0 vers le Nord (Y+ haut), augmente sens horaire
    aspect = np.arctan2(dz_dy, -dz_dx)

    return slope.astype(np.float32), aspect.astype(np.float32)


def _hillshade_numpy(dem, azimuth_deg, altitude_deg, z_factor=1.0, dx=0.5, dy=0.5,
                     nodata=None):
    """Hillshade directionnel — formule GDAL standard.

    Reproduit la formule de gdaldem hillshade (-alt -az) :
        hillshade = 255 * (cos(zenith) * cos(slope)
                         + sin(zenith) * sin(slope) * cos(azimuth - aspect))

    azimuth_deg : direction du soleil en degrés (0=N, 90=E, 180=S, 270=W)
    altitude_deg : hauteur du soleil au-dessus de l'horizon, en degrés
    z_factor : multiplicateur d'exagération verticale (1.0 = pas d'exagération)

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    Retourne un array uint8 (0-255) même shape que dem.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    zenith_rad  = math.radians(90.0 - altitude_deg)
    az_math_rad = math.radians(360.0 - azimuth_deg + 90.0)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        hs_kernel, _, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return hs_kernel(dem_f, float(dx), float(dy),
                         az_math_rad, zenith_rad, nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, aspect = _calc_slope_aspect(dem_calc, dx, dy)
    hs = (np.cos(zenith_rad) * np.cos(slope)
          + np.sin(zenith_rad) * np.sin(slope) * np.cos(az_math_rad - aspect))
    hs = np.clip(hs, 0.0, 1.0)
    hs_u8 = (hs * 254.0 + 1.0).astype(np.uint8)
    hs_u8[nd_m] = 0
    return hs_u8


def _hillshade_multi_numpy(dem, altitude_deg=45.0, z_factor=1.0, dx=0.5, dy=0.5,
                           nodata=None):
    """Hillshade multidirectionnel — formule GDAL `-multidirectional`.

    Calcule 4 hillshades à 225°, 270°, 315°, 360° et combine via une moyenne
    pondérée par sin²(diff) pour éviter les "stripes" du hillshade simple.

    C'est la méthode "Multidirectional Hillshade" de Mark 1992 / Tait 2010
    qu'utilise GDAL avec --multidirectional.

    Moteur Numba (1 passe, 4 azimuts déroulés) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    zenith_rad = math.radians(90.0 - altitude_deg)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, multi_kernel, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return multi_kernel(dem_f, float(dx), float(dy),
                            zenith_rad, nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, aspect = _calc_slope_aspect(dem_calc, dx, dy)
    cos_z = np.cos(zenith_rad)
    sin_z = np.sin(zenith_rad)
    azimuths = [225.0, 270.0, 315.0, 360.0]
    hs_sum     = np.zeros_like(slope)
    weight_sum = np.zeros_like(slope)
    for az in azimuths:
        az_math_rad = np.radians(360.0 - az + 90.0)
        diff = az_math_rad - aspect
        w = np.sin(diff) ** 2
        hs = (cos_z * np.cos(slope)
              + sin_z * np.sin(slope) * np.cos(diff))
        hs = np.clip(hs, 0.0, 1.0)
        hs_sum     += hs * w
        weight_sum += w
    weight_sum = np.where(weight_sum < 1e-6, 1e-6, weight_sum)
    hs_avg = hs_sum / weight_sum
    hs_u8  = (hs_avg * 254.0 + 1.0).astype(np.uint8)
    hs_u8[nd_m] = 0
    return hs_u8


def _slope_numpy(dem, z_factor=1.0, dx=0.5, dy=0.5, scale=1.0, nodata=None):
    """Slope — formule GDAL standard (Horn 1981), encodage visuel.

    Renvoie un array uint8 : pente 0–90° étalée linéairement sur 1–255
    (0 réservé au nodata, même convention que les hillshades).
    Décodage : degrés = (v − 1) × 90 / 254.

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    dem_f = _appliquer_z_factor(dem_f, z_factor, nodata)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, _, slope_kernel = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return slope_kernel(dem_f, float(dx), float(dy),
                            nd_val, nodata is not None)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    dem_calc, nd_m = _remplir_nodata_moyenne(dem_f, nodata)
    slope, _ = _calc_slope_aspect(dem_calc, dx, dy)
    slope_deg = np.degrees(slope)
    slope_u8 = (np.clip(slope_deg, 0.0, 90.0) * (254.0 / 90.0) + 1.0).astype(np.uint8)
    slope_u8[nd_m] = 0
    return slope_u8


def _build_vrt_xml(cogs, vrt_path, target_res):
    """
    Construit un VRT GDAL (XML) référençant N dalles GeoTIFF, sans matérialiser
    de mosaïque physique. Le fichier produit est de l'ordre de quelques 100 Ko
    (≈ 200 octets/dalle) et la construction prend < 1 s même pour 10 000 dalles.

    Rasterio lit le VRT transparemment : pour chaque fenêtre demandée, libgdal
    dispatche les reads aux dalles concernées. Les calculs chunked en aval
    (_hillshade_chunked, _svf_chunked) fonctionnent à l'identique.

    Hypothèses : toutes les dalles partagent le même CRS, dtype, nodata, et
    sont alignées sur une grille (cas standard des dalles IGN LiDAR HD).
    """
    import rasterio as _rio

    if not cogs:
        raise ValueError("Aucune dalle source pour la construction du VRT")

    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    crs_wkt = None
    nodata  = None
    dtype   = None
    src_info = []

    for src_path in cogs:
        with _rio.open(str(src_path)) as ds:
            b = ds.bounds
            src_info.append({
                "path":   str(src_path),
                "bounds": (b.left, b.bottom, b.right, b.top),
                "width":  ds.width,
                "height": ds.height,
            })
            if b.left   < xmin: xmin = b.left
            if b.right  > xmax: xmax = b.right
            if b.bottom < ymin: ymin = b.bottom
            if b.top    > ymax: ymax = b.top
            if crs_wkt is None:
                crs_wkt = ds.crs.to_wkt() if ds.crs else ""
                nodata  = ds.nodata
                dtype   = str(ds.dtypes[0])

    vrt_w = int(round((xmax - xmin) / target_res))
    vrt_h = int(round((ymax - ymin) / target_res))

    DTYPE_MAP = {
        "uint8":   "Byte",    "uint16": "UInt16",  "int16":  "Int16",
        "uint32":  "UInt32",  "int32":  "Int32",
        "float32": "Float32", "float64": "Float64",
    }
    gdal_dtype = DTYPE_MAP.get(dtype, "Float32")

    def _esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                       .replace(">", "&gt;"))

    lines = []
    lines.append(f'<VRTDataset rasterXSize="{vrt_w}" rasterYSize="{vrt_h}">')
    if crs_wkt:
        lines.append(f'  <SRS>{_esc(crs_wkt)}</SRS>')
    lines.append(f'  <GeoTransform>{xmin}, {target_res}, 0.0, {ymax}, 0.0, {-target_res}</GeoTransform>')
    lines.append(f'  <VRTRasterBand dataType="{gdal_dtype}" band="1">')
    if nodata is not None:
        lines.append(f'    <NoDataValue>{nodata}</NoDataValue>')

    for info in src_info:
        sb = info["bounds"]
        x_dest = int(round((sb[0] - xmin) / target_res))
        y_dest = int(round((ymax - sb[3]) / target_res))
        w_dest = int(round((sb[2] - sb[0]) / target_res))
        h_dest = int(round((sb[3] - sb[1]) / target_res))
        lines.append(f'    <SimpleSource>')
        lines.append(f'      <SourceFilename relativeToVRT="0">{_esc(info["path"])}</SourceFilename>')
        lines.append(f'      <SourceBand>1</SourceBand>')
        lines.append(f'      <SrcRect xOff="0" yOff="0" xSize="{info["width"]}" ySize="{info["height"]}"/>')
        lines.append(f'      <DstRect xOff="{x_dest}" yOff="{y_dest}" xSize="{w_dest}" ySize="{h_dest}"/>')
        lines.append(f'    </SimpleSource>')

    lines.append(f'  </VRTRasterBand>')
    lines.append(f'</VRTDataset>')

    Path(vrt_path).write_text("\n".join(lines), encoding="utf-8")


def _lrm_chunked(src_path, dst_path, sigma_px, gdal_translate_exe, env_dem):
    """
    Local Relief Model calculé par blocs avec overlap pour éviter les artefacts
    de bord gaussien et borner la RAM indépendamment de la taille du raster.

    Stratégie :
      - Taille de chunk : 2048 × 2048 px
      - Overlap (marge) : 4 × sigma_px (≈ 4σ garantit que l'erreur de bord < 0.1 %)
      - Chaque bloc est lu depuis le disque, filtré, puis la zone centrale
        (sans la marge) est écrite dans le TIF de sortie.
      - La normalisation percentile est calculée en deux passes :
          passe 1 (échantillon)  → p5 / p95 globaux sur grille 3×3
                                   (_percentiles_grille — même garde-fou que le
                                   SVF : un crop unique rend le stretch dépendant
                                   du cadrage, régression de rendu silencieuse)
          passe 2 (traitement)   → applique la normalisation bloc par bloc

    Retourne True si succès, False si fallback requis (ex: rasterio absent).
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  LRM chunked: missing import ({_ie}) — fallback to full memory", flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)   # au moins 64 px pour les petits sigma

    with _rio.open(str(src_path)) as src:
        H, W   = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    # ── Passe 1 : percentiles p5/p95 globaux sur grille 3×3 ─────────────────
    # On accumule aussi somme/effectif des altitudes valides : la moyenne
    # globale sert de valeur de remplissage nodata UNIQUE en passe 2 (un
    # remplissage par moyenne de bloc créait une couture dans la gaussienne
    # quand du nodata se trouve à < 4σ d'une frontière de bloc).
    _acc = [0.0, 0]   # [somme, n]
    def _lrm_vals(win):
        nd = _nodata_mask(win, nodata)
        v = win[~nd]
        if v.size:
            _acc[0] += float(v.sum()); _acc[1] += v.size
        fill = float(v.mean()) if v.size else 0.0
        lrm = win - _gf(np.where(nd, fill, win), sigma=sigma_px)
        lrm[nd] = np.nan
        return lrm

    _pcts = _percentiles_grille(src_path, MARGIN, _lrm_vals, 5, 95)
    if _pcts is None:
        return False  # raster trop petit / vide
    p5_g, p95_g, _n_valid = _pcts
    mean_g = _acc[0] / _acc[1] if _acc[1] else 0.0
    if p95_g <= p5_g:
        return False  # relief dégénéré (tout plat / tout nodata)
    print(f"  LRM chunked — p5={p5_g:.2f} m  p95={p95_g:.2f} m (grille 3×3)",
          flush=True)

    # ── Profil de sortie ────────────────────────────────────────────────────
    out_profile = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver     = "GTiff",
        dtype      = "uint8",
        count      = 1,
        compress   = "deflate",
        predictor  = 2,
        tiled      = True,
        blockxsize = 512,
        blockysize = 512,
        bigtiff    = "YES",
        nodata     = None,
    )

    # ── Passe 2 : traitement bloc par bloc ──────────────────────────────────
    total_chunks = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n_done = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:

        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                # Fenêtre centrale (sortie)
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                # Fenêtre étendue avec marge (lecture)
                r0 = max(0, row_off - MARGIN)
                c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN)
                c1 = min(W, col_end + MARGIN)

                win_read  = Window(c0, r0, c1 - c0, r1 - r0)
                block     = src.read(1, window=win_read).astype(np.float32)

                nd_mask = _nodata_mask(block, nodata)
                # Remplissage par la moyenne GLOBALE (passe 1) — pas celle du
                # bloc, qui varierait d'un bloc à l'autre → couture gaussienne.
                block_fill = np.where(nd_mask, mean_g, block)

                smooth    = _gf(block_fill, sigma=sigma_px)
                lrm_block = block - smooth
                lrm_block[nd_mask] = np.nan

                # Normalisation avec les percentiles globaux
                arr_f = np.clip((lrm_block - p5_g) / (p95_g - p5_g), 0.0, 1.0) * 255.0
                arr_u8 = np.nan_to_num(arr_f, nan=128.0).astype(np.uint8)
                arr_u8[nd_mask] = 128   # valeur neutre pour les nodata

                # Découpe de la marge (on ne garde que la zone centrale)
                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                centre = arr_u8[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dst.write(centre[np.newaxis, :, :], window=win_write)

                n_done += 1
                pct = n_done * 100 // total_chunks
                print(f"\r  LRM chunked : {pct:3d} % ({n_done}/{total_chunks} blocs)   ",
                      end="", flush=True)

    print(f"\r  LRM chunked: done ({total_chunks} blocs, σ={sigma_px} px)          ")
    return True


def _lrm_array(dem, nodata_val, sigma_px):
    """Local Relief Model brut (float) : DEM − gaussienne(σ), pleine mémoire.

    Centralise le calcul partagé par le LRM standalone (fallback pleine
    mémoire) et le composite RRIM, qui divergeaient cosmétiquement (l'un
    posait nan avant nanmean, l'autre masquait directement) pour un résultat
    identique. Le trou nodata est rempli par la moyenne des pixels valides
    avant le flou — sinon la gaussienne propagerait le nodata dans le relief.

    dem        : array float (lu via _lire_dem_rasterio).
    nodata_val : valeur nodata du raster source, ou None.
    sigma_px   : écart-type gaussien en pixels.

    Retourne (lrm, nodata_mask) ; lrm vaut np.nan sur les nodata.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter as _gf
    nodata_mask = _nodata_mask(dem, nodata_val)
    mean_val = float(np.nanmean(dem[~nodata_mask])) if (~nodata_mask).any() else 0.0
    dem_fill = np.where(nodata_mask, mean_val, dem)
    lrm = dem - _gf(dem_fill, sigma=sigma_px)
    lrm[nodata_mask] = np.nan
    return lrm, nodata_mask


def _hillshade_chunked_multi(src_path, jobs, dx=0.5, dy=0.5):
    """
    Hillshade / hillshade-multi / slope par fenêtres avec halo = 1 px (Horn 3x3)
    — N sorties calculées en UNE seule passe de lecture.

    jobs : liste de (mode, params, dst_path)
        mode   : "hillshade" | "hillshade_multi" | "slope"
        params : dict — clés selon le mode
            hillshade        : {"azimuth_deg": float, "altitude_deg": float}
            hillshade_multi  : {"altitude_deg": float}
            slope            : {} (vide)

    Sur une grande zone, le coût dominant est l'I/O + la décompression deflate
    des dalles derrière le VRT, pas les kernels Horn : lire chaque bloc une
    fois pour tous les types demandés divise le temps total par ~le nombre de
    types (vs une passe complète par type).

    Borne la RAM indépendamment de la taille du raster (chunks 2048×2048 px).
    Retourne True si succès, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  Hillshade chunked: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = 1

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    out_profile = profile.copy()
    # Purger les clés héritées qui pourraient interférer :
    #  - driver : la source peut être un VRT, on veut écrire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse différente, GDAL choisirait au hasard
    #  - NODATA/nodata : on désactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    lbl = "+".join(m for m, _, _ in jobs)

    src_ds = _rio.open(str(src_path))
    dsts = []
    try:
        for _mode, _params, _dst_path in jobs:
            dsts.append(_rio.open(str(_dst_path), "w", **out_profile))

        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt(f"{lbl} chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - HALO)
                c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO)
                c1 = min(W, col_end + HALO)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src_ds.read(1, window=win_read).astype(np.float32)

                # Canonicalisation nodata : sentinelles magiques ET nodata
                # déclaré ramenés à une seule valeur connue des kernels.
                nd_mask = _nodata_mask(block, nodata)
                if nd_mask.any():
                    block[nd_mask] = np.float32(-9999.0)
                    nd_eff = -9999.0
                else:
                    nd_eff = None

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                win_write = Window(col_off, row_off,
                                   col_end - col_off, row_end - row_off)

                for (mode, params, _dst_path), dst in zip(jobs, dsts):
                    if mode == "hillshade":
                        out = _hillshade_numpy(
                            block, params["azimuth_deg"], params["altitude_deg"],
                            z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    elif mode == "hillshade_multi":
                        out = _hillshade_multi_numpy(
                            block, altitude_deg=params["altitude_deg"],
                            z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    elif mode == "slope":
                        out = _slope_numpy(
                            block, z_factor=1.0, dx=dx, dy=dy, nodata=nd_eff)
                    else:
                        raise ValueError(f"Mode hillshade inconnu : {mode}")

                    centre = out[dr0:dr1, dc0:dc1]
                    dst.write(centre[np.newaxis, :, :], window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  {lbl} chunked : {pct:3d} % ({n}/{total} blocs)   ",
                      end="", flush=True)
    finally:
        src_ds.close()
        for dst in dsts:
            dst.close()
    print(f"\r  {lbl} chunked: done ({total} blocs)                     ")
    return True


def _hillshade_chunked(src_path, dst_path, mode, params, dx=0.5, dy=0.5):
    """Wrapper mono-sortie de _hillshade_chunked_multi (compat appels existants)."""
    return _hillshade_chunked_multi(src_path, [(mode, params, dst_path)],
                                    dx=dx, dy=dy)


def _svf_chunked(src_path, dst_path, max_dist_px, n_directions=16,
                 resolution=0.5, gamma=SVF_GAMMA, use_sweep=False, conv=0):
    """
    Sky-View Factor par fenêtres avec halo = max_dist_px (rayons SVF).

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~2-3× plus
    rapide, léger aliasing aux faibles gradients).

    Stratégie 2 passes :
      1. Échantillon central → percentiles p2/p98 globaux
      2. Traitement bloc par bloc → stretch + gamma + uint8

    Borne la RAM à ~(2048+2*max_dist_px)² × 4 octets ≈ 25 MB pour SVF100.
    Retourne True si succès, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  SVF chunked: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = max_dist_px

    # Kernel SVF mutualisé entre _svf_numpy et _svf_chunked (factory + cache).
    # Évite la double compilation Numba (~20 s × 2 au premier appel).
    # Si use_sweep : variante nearest-neighbor sans bilinéaire (~×2-3 plus rapide).
    # Openness (conv ≥ 2) : ray-cast obligatoire — le sweep ne maintient qu'un
    # running max clampé via upper hull (pas de min, pas d'angles négatifs).
    if use_sweep and conv >= 2:
        print("  Openness : kernel sweep non applicable — ray-cast utilisé.",
              flush=True)
        use_sweep = False
    _kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _kernel is None:
        print("  numba missing - SVF chunked unavailable", flush=True)
        return False
    if use_sweep:
        print("  SVF chunked : kernel sweep-horizon (deque/upper-hull)", flush=True)

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    def _svf_block(block, nd_to=0.0):
        # nd_to : valeur posée sur les pixels nodata — 0.0 pour la sortie
        # (noir), NaN pour l'échantillonnage percentile (un 0.0 dans le pool
        # tirerait p2 vers 0 → stretch délavé dès qu'une fenêtre d'échantillon
        # chevauche du nodata).
        nd_mask = _nodata_mask(block, nodata)
        block_f = block.astype(np.float32, copy=True)
        if nd_mask.any():
            mean_val = float(np.nanmean(block_f[~nd_mask])) if (~nd_mask).any() else 0.0
            block_f[nd_mask] = mean_val
        svf = _kernel(block_f, n_directions, max_dist_px, resolution, conv)
        svf[nd_mask] = nd_to
        return svf

    # ── Passe 1 : compilation Numba + percentiles globaux (grille 3×3) ──────
    # Les p2/p98 calibrent le stretch (point noir/blanc) appliqué à TOUTE
    # l'image — échantillonnage réparti via _percentiles_grille (helper
    # partagé SVF/LRM/RRIM).
    print("  SVF chunked — compilation Numba + percentiles (grille)...", flush=True)
    _pcts = _percentiles_grille(src_path, HALO,
                                lambda w: _svf_block(w, nd_to=np.nan), 2, 98)
    if _pcts is None:
        return False
    p2_g, p98_g, _n_valid = _pcts
    if p98_g <= p2_g:
        p2_g, p98_g = 0.0, 1.0
    print(f"  SVF chunked — p2={p2_g:.3f}  p98={p98_g:.3f} (grille 3×3)", flush=True)

    out_profile = profile.copy()
    # Purger les clés héritées qui pourraient interférer :
    #  - driver : la source peut être un VRT, on veut écrire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse différente, GDAL choisirait au hasard
    #  - NODATA/nodata : on désactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    # ── Passe 2 : traitement bloc par bloc ──────────────────────────────────
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("SVF chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - HALO)
                c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO)
                c1 = min(W, col_end + HALO)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src.read(1, window=win_read).astype(np.float32)
                svf   = _svf_block(block)

                svf_stretched = np.clip((svf - p2_g) / (p98_g - p2_g), 0.0, 1.0)
                if conv == 3:
                    # Openness négative inversée : les features (fossés, chemins
                    # creux) sont les valeurs BASSES, le fond est clair — gamma
                    # en miroir 1−(1−x)^γ : renforce les creux SANS assombrir le
                    # fond. Le x^γ direct (γ=2) assombrissait toute l'image
                    # (fond ~0.5 → 0.27, rendu « très sombre »).
                    arr_u8 = ((1.0 - (1.0 - svf_stretched) ** gamma)
                              * 255.0).astype(np.uint8)
                else:
                    arr_u8 = (svf_stretched ** gamma * 255.0).astype(np.uint8)

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                centre = arr_u8[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dst.write(centre[np.newaxis, :, :], window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  SVF chunked : {pct:3d} % ({n}/{total} blocs)   ",
                      end="", flush=True)
    print(f"\r  SVF chunked: done ({total} blocs, halo={HALO} px)        ")
    return True


def _svf_opos_chunked(src_path, svf_dst, opos_dst, max_dist_px, n_directions=16,
                      resolution=0.5, gamma=1.0):
    """SVF flux + openness positif en UN seul scan d'horizon (kernel fusionné),
    écrits dans svf_dst et opos_dst. Utilisé par le composite VAT pour éviter de
    refaire le scan deux fois (~moitié du temps des deux passes SVF/openness).
    Mêmes 2 passes (percentiles puis blocs), même stretch/gamma que _svf_chunked
    en conv=0 / conv=2 : sorties identiques, une seule traversée. True/False."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  SVF+opos chunked: missing import ({_ie})", flush=True)
        return False
    _kernel = _get_numba_svf_opos_kernel()
    if _kernel is None:
        print("  numba missing - VAT SVF+opos unavailable", flush=True)
        return False

    CHUNK = 2048
    HALO  = max_dist_px
    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    def _blocks(block):
        """(svf, opos, nd_mask) — float, nodata rempli par la moyenne du bloc."""
        nd_mask = _nodata_mask(block, nodata)
        bf = block.astype(np.float32, copy=True)
        if nd_mask.any():
            mv = float(np.nanmean(bf[~nd_mask])) if (~nd_mask).any() else 0.0
            bf[nd_mask] = mv
        svf, opos = _kernel(bf, n_directions, max_dist_px, resolution)
        return svf, opos, nd_mask

    # ── Passe 1 : percentiles p2/p98 par sortie (échantillon grille 3×3) ────────
    print("  VAT SVF+opos chunked — compilation Numba + percentiles (grille)...", flush=True)
    def _samp(idx):
        def f(win):
            svf, opos, nd = _blocks(win)
            return np.where(nd, np.nan, svf if idx == 0 else opos)
        return f
    _pc_s = _percentiles_grille(src_path, HALO, _samp(0), 2, 98)
    _pc_o = _percentiles_grille(src_path, HALO, _samp(1), 2, 98)
    if _pc_s is None or _pc_o is None:
        return False
    p2s, p98s, _ = _pc_s
    p2o, p98o, _ = _pc_o
    if p98s <= p2s: p2s, p98s = 0.0, 1.0
    if p98o <= p2o: p2o, p98o = 0.0, 1.0
    print(f"  VAT SVF+opos — svf p2={p2s:.3f}/p98={p98s:.3f}, "
          f"opos p2={p2o:.3f}/p98={p98o:.3f}", flush=True)

    op = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        op.pop(_k, None)
    op.update(driver="GTiff", dtype="uint8", count=1, compress="deflate",
              predictor=2, tiled=True, blockxsize=512, blockysize=512,
              bigtiff="YES", nodata=None)

    # ── Passe 2 : un seul scan par bloc → stretch des deux sorties → écriture ──
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    nblk = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(svf_dst), "w", **op) as dsv, \
         _rio.open(str(opos_dst), "w", **op) as dop:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("VAT SVF+opos interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)
                r0 = max(0, row_off - HALO); c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO); c1 = min(W, col_end + HALO)
                block = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(np.float32)
                svf, opos, nd = _blocks(block)
                svf[nd] = 0.0; opos[nd] = 0.0
                su8 = (np.clip((svf - p2s) / (p98s - p2s), 0.0, 1.0) ** gamma
                       * 255.0).astype(np.uint8)
                ou8 = (np.clip((opos - p2o) / (p98o - p2o), 0.0, 1.0) ** gamma
                       * 255.0).astype(np.uint8)
                dr0 = row_off - r0; dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off); dc1 = dc0 + (col_end - col_off)
                ww = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dsv.write(su8[dr0:dr1, dc0:dc1][np.newaxis, :, :], window=ww)
                dop.write(ou8[dr0:dr1, dc0:dc1][np.newaxis, :, :], window=ww)
                nblk += 1
                print(f"\r  VAT SVF+opos : {nblk * 100 // total:3d} % "
                      f"({nblk}/{total} blocs)   ", end="", flush=True)
    print(f"\r  VAT SVF+opos: done ({total} blocs, halo={HALO} px)        ")
    return True


def _svf_numpy(dem, max_dist_px, n_directions=16, resolution=0.5, use_sweep=False,
               conv=0, nodata=None):
    """
    Sky-View Factor — pixel-level ray casting.

    SVF(p) = (1/N) × Σ_k cos²(γ_k),  γ_k = angle d'horizon dans la direction k

    Convention flux : cos²γ = 1/(1+tan²γ), avec tan γ = max(pente_horizon, 0).
    C'est la fraction de ciel hémisphérique pondérée par le cosinus (radiance).
    Préférée ici à la variante archéo RVT 1−sin γ : la distribution tassée près
    de 1 (terrain ouvert) donne, après stretch percentile + gamma 2.0, un
    contraste plus marqué jugé meilleur à l'œil sur ce relief.

    Moteurs disponibles par ordre de préférence :
      1. Numba njit + prange  → ×15-50 vs numpy pur, compilation ~20s au 1er appel
      2. numpy vectorisé      → fallback si numba absent

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~×2-3 plus rapide,
    léger aliasing aux faibles gradients).

    SVF faible (sombre) = creux (fossé, fond de vallée)
    SVF élevé (clair)   = ouvert (sommet, plateau)
    """
    import numpy as np

    h, w = dem.shape
    nodata_mask = _nodata_mask(dem, nodata)
    dem_f = dem.astype(np.float32)
    if nodata_mask.any():
        mean_val = float(np.nanmean(dem_f[~nodata_mask])) if (~nodata_mask).any() else 0.0
        dem_f[nodata_mask] = mean_val

    # ── Tentative Numba ──────────────────────────────────────────────────────
    # Kernel mutualisé via _get_numba_svf_kernel() — partagé avec _svf_chunked
    # pour éviter la double compilation (~20 s × 2 au premier appel).
    # Openness (conv ≥ 2) : ray-cast obligatoire (cf. _svf_chunked).
    if use_sweep and conv >= 2:
        use_sweep = False
    _numba_ok = False
    _svf_kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _svf_kernel is not None:
        try:
            print("  SVF Numba JIT — compilation au 1er appel (~20s)...", flush=True)
            svf = _svf_kernel(dem_f, n_directions, max_dist_px, resolution, conv)
            _numba_ok = True
            print(f"\r  SVF Numba JIT - done{' ' * 30}")
        except Exception as e_nb:
            print(f"  numba erreur ({e_nb}) — fallback numpy", flush=True)
    else:
        print("  numba missing - vectorised numpy fallback", flush=True)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    if not _numba_ok:
        try:
            from scipy.ndimage import shift as _shift
            _use_scipy = True
        except ImportError:
            _use_scipy = False

        # Check précoce : si l'utilisateur a déjà fait Ctrl+C avant qu'on arrive
        # ici (ex. pendant l'init Numba), on n'enchaîne pas le fallback.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu avant traitement")

        def _process_direction(k):
            angle   = k * 2.0 * np.pi / n_directions
            dx      =  np.sin(angle)
            dy      = -np.cos(angle)
            # conv 3 (openness négative) suit le MIN des angles le long du
            # rayon ; les autres conventions suivent le MAX (horizon).
            need_min = (conv == 3)
            fill = np.inf if need_min else -np.inf
            ext_tan = np.full((h, w), fill, dtype=np.float32)

            for r in range(1, max_dist_px + 1):
                # Check au sein du rayon : sur dept-scale, max_dist_px peut
                # atteindre 200+ et chaque shift scipy prend 1-3s → permet
                # l'interruption en quelques secondes max.
                if _stop_event.is_set():
                    return None
                dist_m = r * resolution
                if _use_scipy:
                    neighbor  = _shift(dem_f, [dy * r, dx * r],
                                       mode='nearest', order=1, prefilter=False)
                    tan_angle = (neighbor - dem_f) / dist_m
                else:
                    rs = int(round(dy * r)); cs = int(round(dx * r))
                    r_s0 = max(0, -rs); r_s1 = min(h, h - rs)
                    c_s0 = max(0, -cs); c_s1 = min(w, w - cs)
                    r_d0 = max(0,  rs); r_d1 = min(h, h + rs)
                    c_d0 = max(0,  cs); c_d1 = min(w, w + cs)
                    if r_s1 <= r_s0 or c_s1 <= c_s0:
                        continue
                    tan_angle = np.full((h, w), fill, dtype=np.float32)
                    tan_angle[r_d0:r_d1, c_d0:c_d1] = (
                        dem_f[r_s0:r_s1, c_s0:c_s1] -
                        dem_f[r_d0:r_d1, c_d0:c_d1]
                    ) / dist_m
                if need_min:
                    np.minimum(ext_tan, tan_angle, out=ext_tan)
                else:
                    np.maximum(ext_tan, tan_angle, out=ext_tan)

            if conv == 0:
                # SVF flux : cos²γ = 1/(1+tan²γ) — contraste
                mt = np.maximum(ext_tan, 0.0)
                return (1.0 / (1.0 + mt * mt)).astype(np.float32)
            if conv == 1:
                # SVF RVT (Kokalj/Hesse) : 1 − sin γ — archéo
                mt = np.maximum(ext_tan, 0.0)
                return (1.0 - mt / np.sqrt(1.0 + mt * mt)).astype(np.float32)
            # Openness (Yokoyama 2002) — conv 2 : φ/π depuis le max β ;
            # conv 3 : négative inversée (π/2 − δ)/π depuis le min δ.
            return (0.5 - np.arctan(ext_tan) / np.pi).astype(np.float32)

        n_workers = min(n_directions, max(1, os.cpu_count() or 4))
        svf_sum   = np.zeros((h, w), dtype=np.float32)
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_process_direction, k): k
                       for k in range(n_directions)}
            done = 0
            try:
                for fut in as_completed(futures):
                    if _stop_event.is_set():
                        # Annuler les futures non encore démarrées (les autres
                        # finiront leur direction courante mais retourneront None).
                        for f in futures:
                            f.cancel()
                        # On ne raise pas tout de suite — on laisse les workers
                        # actifs se terminer avant de quitter le with-block,
                        # sinon ThreadPoolExecutor.__exit__ va attendre quand même.
                        break
                    res = fut.result()
                    if res is None:
                        # Worker a vu _stop_event en interne et a retourné None
                        break
                    svf_sum += res
                    done += 1
                    pct_svf = done * 100 // max(n_directions, 1)
                    print(f"\r  SVF directions : {pct_svf:3d}%  {done}/{n_directions}",
                          end="", flush=True)
            except KeyboardInterrupt:
                # Signal arrivé pendant l'attente du future — annuler ce qu'on peut
                for f in futures:
                    f.cancel()
                raise
        print()
        # Si l'utilisateur a interrompu, propager l'arrêt à l'appelant.
        # Le résultat partiel n'est pas utilisable (sommation incomplète sur
        # n_directions). KeyboardInterrupt = standard Python, ne sera pas
        # capturé par les `except Exception:` en aval.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu en cours de calcul")
        svf = svf_sum / n_directions

    svf[nodata_mask] = 0.0
    return svf


def _rrim_chunked(src_path, slope_path, dst_path, sigma_px):
    """
    Red Relief Image Map par blocs — RAM bornée (c'était le dernier ombrage
    qui chargeait encore le DEM entier en mémoire : OOM garanti à l'échelle
    d'un département).

    R     = pente décodée du TIF slope (uint8 1–255 → 0–90°), rampe ABSOLUE
            0–45° + gamma 0.7. Rampe fixe (Chiba et al. 2008) et non stretch
            percentile : deux zones adjacentes gardent le même rouge — l'ancien
            code cumulait clip(slope/45) PUIS stretch percentile, le second
            annulant le premier et rendant le rouge relatif au dataset.
    G = B = LRM (DEM − gaussienne σ) normalisé p5–p95 globaux (grille 3×3,
            cf. _percentiles_grille), gamma 0.8.
    Nodata → pixel noir (0,0,0).

    slope_path : TIF slope uint8 produit par _hillshade_chunked (même grille
    que le DEM source). Retourne True si succès, False si fallback requis.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  RRIM chunked: missing import ({_ie}) — fallback pleine mémoire",
              flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata
    with _rio.open(str(slope_path)) as srcsl_chk:
        if (srcsl_chk.width, srcsl_chk.height) != (W, H):
            print(f"  RRIM chunked: slope {srcsl_chk.width}×{srcsl_chk.height}"
                  f" ≠ DEM {W}×{H} — fallback pleine mémoire", flush=True)
            return False

    # ── Passe 1 : percentiles LRM p5/p95 + moyenne de remplissage globale ───
    _acc = [0.0, 0]
    def _lrm_vals(win):
        nd = _nodata_mask(win, nodata)
        v = win[~nd]
        if v.size:
            _acc[0] += float(v.sum()); _acc[1] += v.size
        fill = float(v.mean()) if v.size else 0.0
        lrm = win - _gf(np.where(nd, fill, win), sigma=sigma_px)
        lrm[nd] = np.nan
        return lrm

    _pcts = _percentiles_grille(src_path, MARGIN, _lrm_vals, 5, 95)
    if _pcts is None:
        return False
    p5_g, p95_g, _n_valid = _pcts
    mean_g = _acc[0] / _acc[1] if _acc[1] else 0.0
    if p95_g <= p5_g:
        return False
    print(f"  RRIM chunked — LRM p5={p5_g:.2f} m  p95={p95_g:.2f} m (grille 3×3)",
          flush=True)

    out_profile = profile.copy()
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=3, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    # ── Passe 2 : traitement bloc par bloc ──────────────────────────────────
    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(slope_path)) as srcsl, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("RRIM chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - MARGIN)
                c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN)
                c1 = min(W, col_end + MARGIN)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src.read(1, window=win_read).astype(np.float32)

                nd_mask    = _nodata_mask(block, nodata)
                block_fill = np.where(nd_mask, mean_g, block)
                lrm_block  = block - _gf(block_fill, sigma=sigma_px)

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                lrm_c = lrm_block[dr0:dr1, dc0:dc1]
                nd_c  = nd_mask[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off,
                                   col_end - col_off, row_end - row_off)

                # R : pente décodée (1–255 → 0–90°), rampe absolue 0–45°
                sl_enc = srcsl.read(1, window=win_write).astype(np.float32)
                slope_deg = np.clip(sl_enc - 1.0, 0.0, None) * (90.0 / 254.0)
                r_chan = (np.clip(slope_deg / 45.0, 0.0, 1.0) ** 0.7
                          * 255.0).astype(np.uint8)

                # G = B : LRM normalisé p5–p95 globaux
                lrm_n = np.clip((lrm_c - p5_g) / (p95_g - p5_g), 0.0, 1.0)
                gb_chan = (np.nan_to_num(lrm_n) ** 0.8 * 255.0).astype(np.uint8)

                r_chan[nd_c]  = 0
                gb_chan[nd_c] = 0
                r_chan[sl_enc == 0] = 0   # nodata du slope

                rgb = np.stack([r_chan, gb_chan, gb_chan], axis=0)
                dst.write(rgb, window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  RRIM chunked : {pct:3d} % ({n}/{total} blocs)   ",
                      end="", flush=True)
    print(f"\r  RRIM chunked: done ({total} blocs, σ={sigma_px} px)          ")
    return True


_TIFF_MAGICS = (b'II\x2a\x00', b'MM\x00\x2a', b'II\x2b\x00', b'MM\x00\x2b')


def _extraire_tiff_multipart(chemin):
    """Désencapsule un GeoTIFF d'une réponse WCS 2.0 multipart/related.

    Certains serveurs WCS 2.0 (MapServer : Digitaal Vlaanderen, etc.) renvoient
    GetCoverage en multipart/related : une partie GML (text/xml) puis le GeoTIFF
    binaire, séparés par une frontière MIME (--<boundary>). urllib sauve le flux
    brut tel quel → le fichier n'est pas un TIFF valide. On extrait la partie
    binaire (du magic TIFF jusqu'à la frontière suivante) et on réécrit le
    fichier en GeoTIFF pur. No-op si le fichier est déjà un TIFF brut ou n'est
    pas du multipart. Réponse OGC standard, pas un cas spécifique provider.
    """
    try:
        with open(chemin, "rb") as _f:
            entete = _f.read(2)
        if entete in (b'II', b'MM'):
            return  # déjà un TIFF brut
        if entete != b'--':
            return  # pas une frontière multipart
        data = Path(chemin).read_bytes()
        nl = data.find(b'\n')
        if nl < 0:
            return
        boundary = data[2:nl].strip()                # ex. b'wcs'
        for magic in _TIFF_MAGICS:
            i = data.find(magic)
            if i < 0:
                continue
            fin = data.find(b'--' + boundary, i)     # frontière de clôture
            tiff = data[i:fin] if fin > i else data[i:]
            tiff = tiff.rstrip(b'\r\n')               # CRLF avant la frontière
            Path(chemin).write_bytes(tiff)
            return
    except Exception as _e_mp:
        print(f"  multipart {Path(chemin).name} : {type(_e_mp).__name__}: {_e_mp}",
              flush=True)


def _post_fetch_si_besoin(chemin):
    """Prépare le fichier brut téléchargé avant la validation GeoTIFF :
      1. désencapsulation multipart/related (générique WCS 2.0) ;
      2. PROVIDER.post_fetch(chemin) si défini (LAZ/ZIP → GeoTIFF, reproject…).
    No-op si rien ne s'applique.
    """
    _extraire_tiff_multipart(chemin)
    pf = getattr(PROVIDER, "post_fetch", None)
    if pf is None:
        return
    try:
        pf(chemin)
    except Exception as _e_pf:
        print(f"  post_fetch {chemin.name} : {type(_e_pf).__name__}: {_e_pf}",
              flush=True)


def _fetch_provider_shadings(choix, bbox_natif, dossier_ville, nom_zone,
                              ecraser_ombrages, provides_shadings):
    """Telecharge les ombrages precalcules fournis par le provider via WCS.
    Modifie `choix` en place : retire les cles traitees avec succes.
    provides_shadings : {cle: (coverage_id, resolution_m)} ou
                        {cle: (coverage_id, resolution_m, wcs_url)}
    """
    import urllib.request as _urlreq
    import urllib.parse   as _urlparse
    nom_base = normaliser_nom(nom_zone) if nom_zone else normaliser_nom(dossier_ville.name)
    _SUFFIX = {
        "svf":"svf_ombrage","multi":"multi_ombrage","slope":"slope_ombrage",
        "lrm":"lrm_ombrage","rrim":"rrim_ombrage","315":"315_ombrage",
        "045":"045_ombrage","135":"135_ombrage","225":"225_ombrage",
    }
    for cle, spec in provides_shadings.items():
        if cle not in choix:
            continue
        coverage_id  = spec[0]
        resolution_m = float(spec[1])
        wcs_url      = spec[2] if len(spec) > 2 else getattr(PROVIDER, "WCS_URL", None)
        if not wcs_url:
            continue
        nom_fichier = f"{nom_base}_{_SUFFIX.get(cle, cle+'_ombrage')}.tif"
        chemin_out  = dossier_ville / nom_fichier
        if chemin_out.exists() and not ecraser_ombrages:
            print(f"  {nom_fichier.ljust(56)} -> already present (provider pre-computed)")
            choix.remove(cle)
            continue
        if chemin_out.exists() and ecraser_ombrages:
            chemin_out.unlink(missing_ok=True)
        x1, y1, x2, y2 = bbox_natif
        print(f"  {cle} -> provider pre-computed ({coverage_id}, {resolution_m}m)...",
              flush=True)
        t0 = time.time()
        success = False
        # Labels d'axe WCS : variables selon le serveur (x/y minuscules pour
        # MapServer Digitaal Vlaanderen, E/N ou X/Y ailleurs). On lit ceux
        # déclarés par le provider puis on tente des fallbacks courants.
        _ax_prov = getattr(PROVIDER, "WCS_AXIS_LABELS", None)
        _axes = ([tuple(_ax_prov)] if _ax_prov else []) + \
                [("x","y"),("E","N"),("X","Y")]
        for ax1, ax2 in _axes:
            params = _urlparse.urlencode({
                "service":"WCS","version":"2.0.1","request":"GetCoverage",
                "coverageId":coverage_id,"format":"image/tiff",
                "subset":f"{ax1}({x1},{x2})",
            })
            url = f"{wcs_url}?{params}&subset={ax2}({y1},{y2})"
            try:
                ssl_ctx = getattr(PROVIDER, "_SSL_CTX", None)
                req = _urlreq.Request(url, headers={"User-Agent":"lidar2map/1.0"})
                with _urlreq.urlopen(req, timeout=180, context=ssl_ctx) as r:
                    data = r.read()
                chemin_out.write_bytes(data)
                # WCS 2.0 multipart/related → extraire le GeoTIFF binaire
                _extraire_tiff_multipart(chemin_out)
                with open(chemin_out, "rb") as _fv:
                    if _fv.read(4) not in _TIFF_MAGICS:
                        chemin_out.unlink(missing_ok=True)
                        continue
                _creer_fichier(chemin_out)
                _taille = chemin_out.stat().st_size
                print(f"  {nom_fichier} ({_taille/1e6:.1f} Mo,"
                      f" {_hms(time.time()-t0)})",flush=True)
                choix.remove(cle)
                success = True
                break
            except Exception:
                chemin_out.unlink(missing_ok=True)
                continue
        if not success:
            print(f"  {cle}: provider pre-computed failed -> calcul normal depuis DEM",
                  flush=True)


# ── Instances d'ombrages paramétrées (--shading TYPE:cle=val,...) ────────────
# Types et paramètres admis. Syntaxe répétable façon ffmpeg/GDAL : chaque
# --shading produit UNE instance avec SES paramètres — deux instances du même
# type (ex. svf à 20 m ET 100 m) coexistent, les params étant encodés dans le
# nom de fichier de sortie.
# Opacités du composite VAT (cf. _vat_compose). Tunables : ce sont les seuls
# réglages "esthétiques" du mélange, exposés en constantes pour calage facile.
VAT_OPOS_OPACITY  = 0.5   # overlay openness positif (renforce le micro-relief convexe)
VAT_SLOPE_OPACITY = 0.5   # assombrissement par la pente (contraste des talus/scarps)


def _vat_compose(svf_path, opos_path, slope_path, dst_path,
                 gamma=1.0, opos_opacity=VAT_OPOS_OPACITY,
                 slope_opacity=VAT_SLOPE_OPACITY):
    """Composite VAT-style (Visualization for Archaeological Topography), niveaux
    de gris, à partir de 3 couches uint8 déjà calculées et pixel-alignées :
        base   = Sky-View Factor (micro-relief : fossés sombres, surfaces claires)
        + overlay openness positif  (accentue crêtes / tertres / convexités)
        × assombrissement par la pente (donne du contraste aux talus et scarps)
    C'est l'esprit du défaut archéo du Relief Visualization Toolbox (ZRC SAZU) :
    une seule image qui révèle creux ET bosses sans choisir une méthode. Les
    poids sont dans VAT_*_OPACITY (à calibrer à l'œil / contre RVT).

    Blend par fenêtres 2048² (uint8, RAM bornée). Retourne True/False."""
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  VAT compose: missing import ({_ie})", flush=True)
        return False

    CHUNK = 2048
    with _rio.open(str(svf_path)) as s0:
        H, W = s0.height, s0.width
        profile = s0.profile.copy()
    # Les 3 couches viennent du même DEM donc devraient être alignées ; on le
    # vérifie quand même (cf. _rrim_chunked) : sinon les lectures fenêtrées se
    # désaligneraient silencieusement. En cas d'écart, on annule proprement.
    for _other in (opos_path, slope_path):
        with _rio.open(str(_other)) as _so:
            if (_so.width, _so.height) != (W, H):
                print(f"  VAT compose : {Path(_other).name} {_so.width}×{_so.height}"
                      f" != SVF {W}×{H}, composite annulé", flush=True)
                return False
    for _k in ("BIGTIFF", "bigtiff", "NODATA", "nodata"):
        profile.pop(_k, None)
    profile.update(driver="GTiff", dtype="uint8", count=1,
                   compress="deflate", predictor=2, tiled=True,
                   blockxsize=512, blockysize=512, nodata=None, bigtiff="IF_SAFER")

    def _overlay(b, t):
        return np.where(b < 0.5, 2 * b * t, 1.0 - 2.0 * (1.0 - b) * (1.0 - t))

    with _rio.open(str(svf_path)) as s, _rio.open(str(opos_path)) as o, \
         _rio.open(str(slope_path)) as sl, \
         _rio.open(str(dst_path), "w", **profile) as dst:
        for r in range(0, H, CHUNK):
            for c in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("VAT compose interrompu")
                win = Window(c, r, min(CHUNK, W - c), min(CHUNK, H - r))
                a_u8 = s.read(1, window=win)
                a = a_u8.astype(np.float32) / 255.0
                b = o.read(1, window=win).astype(np.float32) / 255.0
                d = sl.read(1, window=win).astype(np.float32) / 255.0
                v = a * (1.0 - opos_opacity) + _overlay(a, b) * opos_opacity
                v = v * (1.0 - slope_opacity * d)      # pente raide → plus sombre
                if gamma and gamma != 1.0:
                    v = np.clip(v, 0, 1) ** gamma
                out = (np.clip(v, 0, 1) * 255.0).astype(np.uint8)
                out[a_u8 == 0] = 0                     # nodata SVF (= 0) → noir
                dst.write(out, 1, window=win)
    return True


_SHADING_TYPES = {
    "315":   {"elevation"},
    "045":   {"elevation"},
    "135":   {"elevation"},
    "225":   {"elevation"},
    "multi": {"elevation"},
    "slope": set(),
    "svf":   {"conv", "dist", "gamma", "sweep"},
    "opos":  {"dist", "gamma"},
    "oneg":  {"dist", "gamma"},
    "lrm":   {"sigma"},
    "rrim":  {"sigma"},
    "vat":   {"dist", "gamma"},
}


# Presets de stack par résolution : params en METRES (intention indépendante de la
# taille de pixel) pour cibler la même échelle de structures que le MNT soit à
# 0,25 m ou 5 m. Sans ça, à 5 m le rayon SVF de 20 m ne fait que 4 px et le LRM
# enleve 75 m de relief. 'auto' choisit le palier selon RESOLUTION_M. Opt-in
# (--shading-preset) : le comportement par defaut reste inchange. Valeurs a
# l'appreciation de l'archeologue (tunables).
SHADING_PRESETS = {
    # nom          svf/opos rayon (m)   LRM sigma (m)   elevation soleil (deg)
    "micro":       (15.0,               8.0,            25),   # micro-relief, MNT fin (<=0,75 m)
    "standard":    (30.0,               15.0,           25),   # MNT ~1 m
    "landscape":   (80.0,               40.0,           30),   # grandes structures / MNT grossier (>=5 m)
}


def _resoudre_preset_shading(name, res_m):
    """(nom_resolu, [instances (type, params)], elevation) pour un preset.
    'auto' choisit le palier par la resolution du provider. Les instances portent
    les params en metres ; le pipeline existant les nomme/encode (cache preserve)."""
    if name == "auto":
        name = ("micro" if res_m <= 0.75 else
                "standard" if res_m <= 2.5 else "landscape")
    dist, sigma, elev = SHADING_PRESETS[name]
    insts = [("svf", {"dist": dist}), ("opos", {"dist": dist}),
             ("lrm", {"sigma": sigma})]
    return name, insts, elev


def parser_shading_spec(spec):
    """Parse 'TYPE[:cle=val,...]' → (type, params explicites).

    Exemples :
      --shading svf:dist=20,gamma=2,conv=flux --shading svf:dist=100
      --shading oneg:dist=20,gamma=1.5 --shading 315:elevation=20
      --shading lrm:sigma=10 --shading slope

    Paramètres par type :
      315/045/135/225/multi : elevation (degrés)
      svf                   : conv (flux|rvt), dist (m), gamma,
                              sweep (1|0, kernel sweep-horizon — défaut --svf-sweep)
      opos/oneg             : dist (m), gamma
      lrm/rrim              : sigma (m, rayon gaussien — défaut 15 px du provider)
      vat                   : dist (m, rayon SVF/openness), gamma (du composite)
      slope                 : aucun

    Lève ValueError (message clair) si type ou clé inconnus.
    """
    typ, _, reste = spec.strip().partition(":")
    typ = typ.strip().lower()
    if typ not in _SHADING_TYPES:
        raise ValueError(f"type d'ombrage inconnu : {typ!r}"
                         f" (valides : {', '.join(sorted(_SHADING_TYPES))})")
    admis = _SHADING_TYPES[typ]
    params = {}
    for kv in reste.split(","):
        kv = kv.strip()
        if not kv:
            continue
        k, sep, v = kv.partition("=")
        k = k.strip().lower()
        if not sep or k not in admis:
            raise ValueError(
                f"paramètre {k!r} invalide pour {typ}"
                f" (admis : {', '.join(sorted(admis)) or 'aucun'})")
        if k == "conv":
            v = v.strip().lower()
            if v not in ("flux", "rvt"):
                raise ValueError(f"conv={v!r} (attendu : flux ou rvt)")
            params[k] = v
        else:
            try:
                params[k] = float(v)
            except ValueError:
                raise ValueError(f"{k}={v.strip()!r} : nombre attendu")
    return typ, params


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
        lrm  — Local Relief Model    : LRM = DEM − gaussienne(σ 7.5 m) — scipy requis
        vat  — Visualization for Archaeological Topography : composite niveaux de
               gris SVF + openness positif + slope (la "meilleure vue archéo" en
               une seule image ; numba requis pour les composantes SVF/openness)

    Deux chemins d'entrée, cumulables :
      choix     : liste de TYPES (--shadings, GUI historique) — chaque type
                  devient une instance aux paramètres GLOBAUX ci-dessous ;
      instances : liste (type, params explicites) du flag répétable
                  --shading TYPE:cle=val,... (cf. parser_shading_spec) —
                  permet plusieurs instances du même type (svf 20 m + 100 m).
    Les params sont encodés dans le nom de fichier quand ils diffèrent des
    défauts canoniques → pas de collision, caches historiques préservés.

    elevation_soleil : angle solaire des hillshades directionnels (défaut: 25°).
    svf_conv  : "flux" (cos²γ, contraste) ou "rvt" (1−sin γ, archéo).  Défaut flux.
    svf_dist  : rayon SVF/openness en mètres (10–200).  Défaut 20.
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
        print(f"  ⚠ No tile available in this chunk "
              f"(hors couverture IGN LiDAR ou téléchargement échoué) — "
              f"ombrages skipés.", flush=True)
        return

    # Variables conservées pour compatibilité du code existant : après le
    # refactor rasterio (étapes 1-7), aucun de ces exes n'est plus appelé.
    # _trouver_outil_gdal renvoie toujours None (no-op), donc ces variables
    # sont toujours None — c'est OK puisqu'elles ne sont plus testées.
    gdaldem        = None
    gdalbuildvrt   = None
    gdal_translate = None
    env_dem        = None

    # Ombrages precalcules fournis par le provider (PROVIDES_SHADINGS) :
    # telecharges directement depuis le WCS du provider (ex. Digitaal Vlaanderen
    # SVF/Hillshade 25cm) AVANT la resolution en instances, pour que les cles
    # ainsi servies soient retirees de choix et NON recalculees localement.
    # Seules les instances "par defaut" (issues de choix) sont servies — une
    # instance --shading aux params explicites est toujours calculee localement.
    if bbox_natif is not None and hasattr(PROVIDER, "PROVIDES_SHADINGS") and choix:
        choix = list(choix)
        _fetch_provider_shadings(
            choix, bbox_natif, dossier_ville, nom_zone, ecraser_ombrages,
            PROVIDER.PROVIDES_SHADINGS
        )

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
            # dist = rayon SVF/openness ; gamma = gamma FINAL du composite (les
            # composantes entrent linéaires dans le blend → pas de double gamma).
            p.setdefault("dist", float(svf_dist))
            p.setdefault("gamma", 1.0)
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
        if typ == "vat":
            if prm:   # params explicites → encoder dist/gamma, sinon nom canonique
                gtag = f"{p['gamma']:.1f}".replace(".", "p")
                return f"vat_{int(round(p['dist']))}m_g{gtag}_ombrage"
            return "vat_ombrage"
        # lrm / rrim
        if "sigma" in (prm or {}) and p["sigma"] != sigma_defaut_m:
            return f"{typ}_s{_tag(p['sigma'])}m_ombrage"
        return f"{typ}_ombrage"

    insts, _vus = [], set()
    for typ, prm in ([(t, {}) for t in choix] + list(instances or [])):
        if typ not in _SHADING_TYPES:
            print(f"  ⚠ type d'ombrage inconnu ignoré : {typ}")
            continue
        p = _resoudre_params(typ, prm)
        sfx = _suffixe_instance(typ, prm, p)
        if sfx in _vus:
            continue   # doublon exact (même type, mêmes params)
        _vus.add(sfx)
        insts.append((typ, p, sfx))

    horn_insts  = [i for i in insts if i[0] in HORN_TYPES]
    numpy_insts = [i for i in insts if i[0] not in HORN_TYPES]

    # ── Construction VRT global (seamless, évite jointures gdaldem) ─────────
    # VRT dans _tmp/ sous dossier_ville : tous les fichiers restent dans le projet.
    import shutil as _shutil_vrt
    _vrt_tmpdir = None
    # ── Merge des dalles via rasterio (remplace gdalbuildvrt + gdal_translate) ──
    # Au lieu de produire un VRT puis de le convertir en GeoTIFF avec
    # gdal_translate, on fait un merge direct rasterio en GeoTIFF compressed.
    # Avantages : un seul passage, plus de dépendance à GDAL CLI, sortie
    # immédiatement utilisable par numpy (gdaldem reste pour les hillshades —
    # voir étape 4 du refactor).
    if len(cogs) > 1:
        _vrt_tmpdir = dossier_ville / "_tmp"
        _vrt_tmpdir.mkdir(parents=True, exist_ok=True)
        # VRT XML : vue logique sur les dalles, ~200 o/dalle, construction <1 s.
        # Évite la matérialisation d'une mosaïque physique multi-Go (le merge
        # rasterio sur 2000+ dalles avec compression deflate est pathologique).
        # rasterio lit le VRT transparemment via libgdal — les calculs chunked
        # en aval reçoivent leurs fenêtres comme depuis un raster ordinaire.
        vrt_path      = _vrt_tmpdir / "_mnt_complet.vrt"
        filelist_path = _vrt_tmpdir / "_dalles.txt"
        filelist_path.write_text(
            "\n".join(str(c) for c in cogs), encoding="utf-8")
        _creer_fichier(filelist_path)
        print(f"  Building VRT ({len(cogs)} tiles)...", flush=True)
        _t0_vrt = time.time()
        try:
            _build_vrt_xml(cogs, vrt_path, RESOLUTION_M)
            _creer_fichier(vrt_path)
            print(f"  VRT OK  ({_hms(time.time()-_t0_vrt)}, "
                  f"{vrt_path.stat().st_size // 1024} Ko)", flush=True)
            sources = [vrt_path]
        except Exception as e:
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

    try:
        # ── Hillshades numpy chunked (RAM bornée — voir _hillshade_chunked_multi)
        # Traitement par fenêtres 2048×2048 px avec halo 1 px (Horn 3x3).
        # Tous les types demandés sont calculés en UNE passe de lecture :
        # sur une grande zone le coût dominant est l'I/O + décompression
        # deflate des dalles derrière le VRT, pas les kernels.
        if horn_insts:
            jobs_h = []
            for typ_h, p_h, sfx_h in horn_insts:
                nom_fichier = nom_base + "_" + sfx_h + ".tif"
                chemin_out  = dossier_ville / nom_fichier
                if chemin_out.exists() and not ecraser_ombrages:
                    print("  " + nom_fichier.ljust(56) + " -> already present")
                    continue
                if chemin_out.exists():
                    chemin_out.unlink()
                if typ_h == "multi":
                    jobs_h.append(("hillshade_multi",
                                   {"altitude_deg": float(p_h["elevation"])},
                                   chemin_out))
                elif typ_h == "slope":
                    jobs_h.append(("slope", {}, chemin_out))
                else:
                    jobs_h.append(("hillshade",
                                   {"azimuth_deg":  float(int(typ_h)),
                                    "altitude_deg": float(p_h["elevation"])},
                                   chemin_out))

            if jobs_h:
                print(f"  Hillshades chunked — {len(jobs_h)} type(s),"
                      f" une seule passe de lecture...", flush=True)
                t0_hill = time.time()
                try:
                    ok_h = _hillshade_chunked_multi(
                        Path(str(source)), jobs_h,
                        dx=RESOLUTION_M, dy=RESOLUTION_M)
                    if not ok_h:
                        raise RuntimeError("chunked failed (rasterio absent ?)")
                    for _, _, chemin_out in jobs_h:
                        _creer_fichier(chemin_out)
                        print(f"  {chemin_out.name.ljust(56)}"
                              f"  {_hms(int(time.time() - t0_hill))}"
                              f"  {chemin_out.stat().st_size / 1e6:.0f} Mo")
                except BaseException as e_hill:
                    # Fichiers partiellement écrits (structurellement valides
                    # mais incomplets) → supprimer, sinon ils seraient pris
                    # pour des caches sains au prochain lancement (même
                    # logique que le SVF).
                    for _, _, chemin_out in jobs_h:
                        if chemin_out.exists():
                            chemin_out.unlink()
                            print(f"  Partial file removed: {chemin_out.name}")
                    if isinstance(e_hill, (KeyboardInterrupt, SystemExit)):
                        raise
                    print(f"\n  ERREUR hillshades chunked : {e_hill}")

        # ── SVF / openness / LRM / RRIM — numpy/scipy ────────────────────────
        # NB : rasterio.merge (étape 2 du refactor) produit déjà un GeoTIFF
        # directement utilisable par numpy/PIL/rasterio en aval. Plus aucune
        # conversion intermédiaire VRT→GTiff nécessaire.
        src_str = str(source)
        tmp_gtiff = None

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
            # Si on écrase, supprimer l'ancien : évite que rasterio_write
            # tombe sur un fichier figé (Windows file locking) ou demi-écrit.
            if chemin_out.exists() and ecraser_ombrages:
                chemin_out.unlink()

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
                        dst_path     = chemin_out,
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
                        print("  SVF chunked KO → fallback to full memory", flush=True)
                        dem_arr, _nd = _lire_dem_rasterio(src_str)
                        arr_svf = _svf_numpy(dem_arr, max_dist_px, n_directions,
                                             RESOLUTION_M, use_sweep=_sweep_i,
                                             conv=conv, nodata=_nd)
                        # > 0 strict : les nodata valent exactement 0.0 et
                        # tireraient p2 vers 0 (stretch délavé).
                        svf_valid = arr_svf[arr_svf > 0]
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
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_out)
                except Exception as e_svf:
                    import traceback as _tb
                    print(f"  ERREUR SVF : {e_svf}")
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
                    if chemin_out.exists():
                        chemin_out.unlink()
                        print(f"  Partial file removed: {chemin_out.name}")
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
                    src_path         = Path(src_str),
                    dst_path         = chemin_out,
                    sigma_px         = sigma_px,
                    gdal_translate_exe = gdal_translate,
                    env_dem          = env_dem,
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
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_out)
                        _lrm_ok = True
                        print(f"  LRM scipy (full memory): σ={sigma_px} px, {clip_info}")
                    except ImportError:
                        print("  scipy missing - LRM skipped (pip install scipy)", flush=True)
                        continue
                    except Exception as e_scipy:
                        print(f"  ERREUR scipy LRM : {e_scipy}")
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
                print("  RRIM — Red Relief Image Map (slope × LRM)"
                      " — peut prendre 5-10 min...", flush=True)

                sigma_rrim = _sigma_px   # défaut 15 px ; --shading rrim:sigma=M en mètres

                # Slope temporaire (réutilisé si already present)
                slope_rrim_path = dossier_ville / (nom_base + "_slope_ombrage.tif")
                slope_tmp_path  = dossier_ville / (nom_fichier.replace(".tif","_slope_tmp.tif"))
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
                            Path(src_str), _slope_src, chemin_out,
                            sigma_px=sigma_rrim)
                    except Exception as e_rrim:
                        print(f"  ERREUR composite RRIM : {e_rrim}")
                        # Fichier partiellement écrit → supprimer (sinon pris
                        # pour un cache sain au prochain lancement).
                        if chemin_out.exists():
                            chemin_out.unlink()
                            print(f"  Partial file removed: {chemin_out.name}")
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
                            _sauver_array_georef(rgb, Path(src_str), chemin_out)
                            print(f"  RRIM (full memory): {chemin_out.name}"
                                  f" — RGB 3 canaux")
                        except Exception as e_rrim:
                            print(f"  ERREUR composite RRIM : {e_rrim}")
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
                print(f"  VAT — composite SVF + openness + slope"
                      f" (rayon {_vat_dist_px * RESOLUTION_M:.0f} m)"
                      f" — peut prendre 10-20 min...", flush=True)
                _svf_t   = dossier_ville / nom_fichier.replace(".tif", "_svf_tmp.tif")
                _opos_t  = dossier_ville / nom_fichier.replace(".tif", "_opos_tmp.tif")
                _slope_t = dossier_ville / nom_fichier.replace(".tif", "_slope_tmp.tif")
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
                        print("  VAT : composantes indisponibles (numba requis pour"
                              " SVF/openness) — ombrage sauté.", flush=True)
                        continue
                    if not _vat_compose(_svf_t, _opos_t, _slope_t, chemin_out,
                                        gamma=_vat_gamma):
                        if chemin_out.exists():
                            chemin_out.unlink()
                        continue
                except Exception as e_vat:
                    print(f"  ERREUR composite VAT : {e_vat}")
                    if chemin_out.exists():
                        chemin_out.unlink()
                    continue
                finally:
                    for _t in (_svf_t, _opos_t, _slope_t):
                        if _t.exists():
                            _t.unlink(missing_ok=True)

            if chemin_out.exists():
                _creer_fichier(chemin_out)
                taille = chemin_out.stat().st_size / 1e6
                elap_numpy = int(time.time() - t0_numpy)
                print(f"  {nom_fichier.ljust(56)}  {_hms(elap_numpy)}  {taille:.0f} Mo")

        # Nettoyage du GeoTIFF temporaire créé pour WhiteboxTools
        if tmp_gtiff and tmp_gtiff.exists():
            tmp_gtiff.unlink(missing_ok=True)

    finally:
        # Suppression du dossier _tmp/ projet (VRT, dalles.txt, numpy_source_tmp)
        if _vrt_tmpdir and _vrt_tmpdir.exists():
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)

    print("\n  Shadings in: " + str(dossier_ville))


def _bbox_depuis_gdalinfo(chemin, env=None):
    """Retourne (xmin, ymin, xmax, ymax) en unités natives du fichier via rasterio.

    Le paramètre `env` est conservé pour compatibilité mais n'est plus utilisé
    (rasterio embarque sa propre libgdal — pas besoin de PROJ_LIB).
    """
    try:
        import rasterio
        with rasterio.open(str(chemin)) as ds:
            b = ds.bounds   # BoundingBox(left, bottom, right, top)
            return (b.left, b.bottom, b.right, b.top)
    except Exception:
        return None


def generer_mbtiles_lidar(tif_source, dossier_ville, nom_ville,
                    zoom_min=13, zoom_max=17, format_tuiles="auto",
                    jpeg_quality=85, bbox_l93=None,
                    source_already_warped=False, ecraser_tuiles=False,
                    tile_workers=8):
    """
    Pipeline MBTiles — source unique, pyramide GDAL, tuilage par bandes.

    1. gdalwarp  : tif_source (EPSG:2154) → warped_3857.tif (EPSG:3857)
                   à la résolution native de zoom_max, DEFLATE+TILED.
    2. gdaladdo  : overviews gauss pour zoom_min..zoom_max-1.
    3. Tiling    : rangées de tuiles via gdal_translate + Pillow
                   → INSERT OR REPLACE SQLite.

    format_tuiles : 'auto' (JPEG pour hillshades, PNG pour SVF/LRM/RRIM),
                    'jpeg' ou 'png'.
    JPEG à Q=85 divise la taille par 5-8 sur les hillshades sans perte visible.
    PNG conservé pour les analyses à gradient fin (SVF, LRM) et RRIM couleur.
    """
    import sqlite3, shutil
    from PIL import Image

    # Vérification anticipée de rasterio — évite d'attendre la fin du gdalwarp
    try:
        import rasterio as _rio_check  # noqa
    except ImportError:
        print("  ERROR: rasterio missing - required for MBTiles tiling.")
        print("  Install it: pip install rasterio")
        return None

    Image.MAX_IMAGE_PIXELS = None

    # Déterminer le format de tuile effectif
    _nom_lower = tif_source.stem.lower()
    _types_png = ("svf", "opos", "oneg", "lrm", "rrim")   # gradients fins → PNG sans perte
    if format_tuiles == "auto":
        _use_jpeg = not any(t in _nom_lower for t in _types_png)
    elif format_tuiles == "jpeg":
        _use_jpeg = True
    else:
        _use_jpeg = False
    _tile_fmt  = "JPEG" if _use_jpeg else "PNG"
    _tile_ext  = "jpg"  if _use_jpeg else "png"
    print(f"  Tile format: {_tile_fmt}"
          f"{'  Q=' + str(jpeg_quality) if _use_jpeg else '  lossless'}", flush=True)

    EARTH_CIRC = 20037508.3427892
    TILE_SIZE  = 256

    # Nom de base : utiliser nom_ville si fourni (ex: "aa_hillshade_multi"),
    # sinon stem du TIF source
    nom_base = nom_ville if nom_ville else tif_source.stem
    mbtiles  = dossier_ville / (nom_base + f"_z{zoom_min}-{zoom_max}.mbtiles")

    if mbtiles.exists() and not ecraser_tuiles:
        print(f"  {mbtiles.name} → already present")
        return mbtiles
    if mbtiles.exists() and ecraser_tuiles:
        mbtiles.unlink()
        print(f"  {mbtiles.name} → overwrite")

    # Variables conservées pour compatibilité — après refactor rasterio
    # (étapes 1-7), gdalwarp/gdal_translate/gdal_addo ne sont plus appelés
    # comme CLI. Le warp est fait par rasterio.warp plus bas.
    env       = None
    gdalwarp  = None
    gdal_tr   = None
    gdal_addo = None

    # NB : avec rasterio, la base proj.db est gérée en interne par le wheel
    # rasterio (livrée dans rasterio/proj_data/). Plus besoin de configurer
    # PROJ_LIB ou GDAL_DATA externes — c'était nécessaire avec GDAL CLI mais
    # rasterio embarque sa propre lib statique.

    proj_args = []

    def merc_to_tile(mx, my, z):
        n = 2 ** z
        return (int((mx + EARTH_CIRC) / (2 * EARTH_CIRC) * n),
                int((EARTH_CIRC - my) / (2 * EARTH_CIRC) * n))

    def tile_bounds(tx, ty, z):
        n  = 2 ** z
        x0 = tx / n * 2 * EARTH_CIRC - EARTH_CIRC
        y1 = EARTH_CIRC - ty / n * 2 * EARTH_CIRC
        x1 = (tx + 1) / n * 2 * EARTH_CIRC - EARTH_CIRC
        y0 = EARTH_CIRC - (ty + 1) / n * 2 * EARTH_CIRC
        return x0, y0, x1, y1   # xmin ymin xmax ymax

    t0 = time.time()

    # ── Seuil de découpage automatique ───────────────────────────────────────
    # Si la zone est grande, warp par bandes horizontales pour éviter un
    # fichier intermédiaire > SEUIL_WARP_GO en temp.
    # Overlap d'une tuile (res_max × 256) entre bandes → pas de jointure visible.
    # À 20×20 km / z18 : ~160 MB warpé → seuil jamais atteint.
    # Protection transparente pour les zones > ~35×35 km.
    SEUIL_WARP_GO = 0.8   # Go non-compressé estimé

    res_max = 2 * EARTH_CIRC / (TILE_SIZE * 2 ** zoom_max)

    # Bbox source en Lambert93 — fournie directement par main() si connue
    # (évite gdalinfo qui peut échouer sans proj.db sur certaines installations)
    if bbox_l93 is not None:
        bb_src = bbox_l93
    else:
        bb_src = _bbox_depuis_gdalinfo(tif_source, env)
    if bb_src:
        w_src_px = (bb_src[2] - bb_src[0]) / res_max
        h_src_px = (bb_src[3] - bb_src[1]) / res_max
        taille_go_est = w_src_px * h_src_px / 1e9
    else:
        taille_go_est = 0.0

    res_max = 2 * EARTH_CIRC / (TILE_SIZE * 2 ** zoom_max)

    if taille_go_est > 0:
        print(f"  Estimated size: ~{taille_go_est:.1f} Go -> single warp"
              f" (GDAL streaming)", flush=True)

    # Warp unique — GDAL gère le streaming en interne, pas besoin de banding
    # Le banding causait des artefacts car la conversion Lambert93→Mercator
    # des limites de bandes n'était pas cohérente avec le tuilage Pillow.
    tranches = [(None, None, "unique")]

    # Niveaux gdaladdo — gauss > average pour hillshades (rendu 8 bits)
    overview_levels = [2 ** (zoom_max - z)
                       for z in range(zoom_max - 1, zoom_min - 1, -1)]

    # ── MBTiles ───────────────────────────────────────────────────────────────
    mbtiles.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(mbtiles))
    con.execute("PRAGMA journal_mode=WAL;")   # écritures concurrentes sans lock global
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles   (zoom_level INTEGER, tile_column INTEGER,
                              tile_row   INTEGER, tile_data   BLOB);
        CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
    """)
    for k, v in [("name", mbtiles.stem), ("type", "overlay"), ("version", "1.0"),
                 ("description", nom_ville), ("format", _tile_ext),
                 ("minzoom", str(zoom_min)), ("maxzoom", str(zoom_max))]:
        cur.execute("INSERT INTO metadata VALUES (?,?)", (k, v))

    # bounds : requis par la spec MBTiles et par Locus pour positionner la carte
    # "left,bottom,right,top" en degrés WGS84
    if bbox_l93 is not None:
        # Enveloppe des 4 coins — même règle que pour l'étendue du warp plus
        # bas : un rectangle L93 ne reste pas axis-aligné après reprojection,
        # min/max sur 2 coins opposés sous-estimerait l'emprise.
        _pts4 = [_lamb93_to_wgs84_safe(cx4, cy4)
                 for cx4, cy4 in ((bbox_l93[0], bbox_l93[1]),
                                  (bbox_l93[2], bbox_l93[1]),
                                  (bbox_l93[2], bbox_l93[3]),
                                  (bbox_l93[0], bbox_l93[3]))]
        _lons = [p[0] for p in _pts4]
        _lats = [p[1] for p in _pts4]
        _bounds = f"{min(_lons):.6f},{min(_lats):.6f},{max(_lons):.6f},{max(_lats):.6f}"
        _cx = (min(_lons) + max(_lons)) / 2
        _cy = (min(_lats) + max(_lats)) / 2
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("bounds", _bounds))
        cur.execute("INSERT INTO metadata VALUES (?,?)",
                    ("center", f"{_cx:.6f},{_cy:.6f},{zoom_max}"))
    con.commit()

    total_insere = 0
    t_tile = time.time()
    # Initialisé avant la boucle pour rester accessible même si le warp
    # plante avant d'atteindre la phase de tuilage (cf. bloc plus bas
    # qui le décrémente puis affiche un récapitulatif).
    nb_echecs_tr = 0

    # ── Pool d'encodage des tuiles ────────────────────────────────────────
    # Pillow libère le GIL pendant JPEG/PNG save, donc un ThreadPool donne du vrai
    # parallélisme. Le pool est créé une fois pour toute la pyramide et fermé
    # à la fin. Sur petites bandes (<_MIN_PAR_TILES tuiles), on bypass le pool
    # car l'overhead submit/wait l'emporte sur le gain d'encodage.
    _MIN_PAR_TILES = 8
    _pool = ThreadPoolExecutor(max_workers=tile_workers) if tile_workers > 1 else None

    def _encode_tile(args):
        _tile, _z, _tx, _ty = args
        _buf = io.BytesIO()
        if _use_jpeg:
            _tile.convert("RGB").save(_buf, "JPEG",
                                       quality=jpeg_quality, optimize=False)
        else:
            # PNG : conserver le mode natif — une source monobande (SVF, LRM)
            # part en niveaux de gris ("L"), ~2-3× plus petit que le même
            # contenu tripliqué en RGB. PNG grayscale = standard, lu par
            # Locus/OsmAnd/TwoNav. compress_level=6 (défaut zlib) : artefact
            # final écrit une fois, lu mille fois — le niveau 1 économisait
            # quelques secondes d'encodage contre ~20-30 % de taille.
            _img = _tile if _tile.mode in ("L", "RGB") else _tile.convert("RGB")
            _img.save(_buf, "PNG", optimize=False, compress_level=6)
        _y_tms = (2 ** _z - 1) - _ty
        return (_z, _tx, _y_tms, _buf.getvalue())

    for i_tr, (y0_l, y1_l, nom_tr) in enumerate(tranches):
        # Fichier warped persistant dans dossier_ville — préfixe _ pour
        # être ignoré par le glob MBTiles (not t.name.startswith("_")).
        # Nom déterministe : source + zoom_max → réutilisable si on relance
        # avec des zooms différents sur le même TIF source.
        warped = dossier_ville / f"{tif_source.stem}_tuilage_z{zoom_max}.tif"
        lbl    = warped.name

        # Si la source est déjà en EPSG:3857 (ex: _warped_*.tif réutilisé),
        # pas besoin de re-warper — on l'utilise directement comme warped.
        if source_already_warped:
            warped = tif_source
            warp_deja_fait = True
            print(f"  Source already in EPSG:3857 - warp skipped", flush=True)
        else:
            warp_deja_fait = warped.exists() and warped.stat().st_size > 1_000_000 and not ecraser_tuiles
            if warp_deja_fait:
                print(f"  Warped cache : {warped.name}  "
                      f"({warped.stat().st_size/1e6:.0f} MB) — réutilisé", flush=True)

        # ── 1. Warp via rasterio ───────────────────────────────────────────
        # Plus de cmd_warp gdalwarp à construire — voir bloc rasterio.warp
        # plus bas. On garde le calcul de te_xmin/etc. pour la bbox cible.
        # ── Calcul de l'étendue cible en Web Mercator ────────────────────
        te_xmin = te_ymin = te_xmax = te_ymax = None
        # Conversion Lambert 93 → WGS84 → Web Mercator en Python pur.
        def _lamb93_to_merc(x, y):
            lon, lat = lamb93_to_wgs84_approx(x, y)
            mx = math.radians(lon) * 6378137.0
            my = math.log(math.tan(math.pi/4 + math.radians(lat)/2)) * 6378137.0
            return mx, my

        if bb_src is not None:
            x0, y0_bb, x1, y1_bb = bb_src
            # En mode banding : restreindre à la tranche courante
            _y0 = y0_l if y0_l is not None else y0_bb
            _y1 = y1_l if y1_l is not None else y1_bb
            # Enveloppe Mercator des 4 coins : un rectangle L93 ne reste pas
            # axis-aligné après reprojection (la grille tourne légèrement),
            # donc min/max sur 2 coins opposés sous-estimerait l'étendue et
            # rognerait quelques pixels en bordure. gdalwarp -te procède de
            # même (enveloppe des 4 coins).
            corners = [(x0, _y0), (x1, _y0), (x1, _y1), (x0, _y1)]
            try:
                _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:3857")
                pts = [_t.transform(cx, cy) for cx, cy in corners]
            except Exception:
                pts = [_lamb93_to_merc(cx, cy) for cx, cy in corners]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            te_xmin, te_xmax = min(xs), max(xs)
            te_ymin, te_ymax = min(ys), max(ys)
        # NB : l'ancienne branche `elif y0_l is not None` référençait bb_src[0]
        # alors que bb_src est None ici (TypeError garanti) — removede. Si
        # bb_src est None, te_* restent None et le warp retombe proprement sur
        # calculate_default_transform (étendue auto calculée depuis la source).

        if not warp_deja_fait:
            # ── 1. Warp via rasterio (remplace gdalwarp CLI — étape 5) ──────
            # Lambert 93 (EPSG:2154) → Web Mercator (EPSG:3857) avec
            # rééchantillonnage bilinéaire et résolution cible res_max.
            # Conserve le -te (target extent) calculé ci-dessus pour ne pas
            # dépendre de proj.db pour la conversion d'étendue.
            if len(tranches) > 1:
                print(f"\n  [{i_tr+1}/{len(tranches)}] Warp {nom_tr} "
                      f"res={res_max:.3f} m/px (rasterio)...", flush=True)
            else:
                print(f"  Warp EPSG:3857  res={res_max:.3f} m/px"
                      f"  (rasterio, zoom {zoom_max})...", flush=True)

            t0_warp = time.time()
            try:
                import rasterio as _rio_w
                from rasterio.warp import calculate_default_transform as _calc_tr
                from rasterio.warp import reproject as _reproject
                from rasterio.warp import Resampling as _Resampling
                from rasterio.transform import from_bounds as _from_bounds

                with _rio_w.open(str(tif_source)) as src:
                    # Si te_xmin/etc. fournis : on impose la bbox cible.
                    # Sinon : calculate_default_transform calcule l'étendue
                    # automatiquement à partir des bounds de la source.
                    if te_xmin is not None:
                        # Dimensions cible à partir de la bbox + résolution
                        dst_width  = int(round((te_xmax - te_xmin) / res_max))
                        dst_height = int(round((te_ymax - te_ymin) / res_max))
                        dst_transform = _from_bounds(
                            te_xmin, te_ymin, te_xmax, te_ymax,
                            dst_width, dst_height)
                    else:
                        dst_transform, dst_width, dst_height = _calc_tr(
                            src.crs, "EPSG:3857",
                            src.width, src.height, *src.bounds,
                            resolution=res_max)

                    # Profil de sortie compatible avec le code en aval
                    dst_profile = src.profile.copy()
                    dst_profile.update({
                        "driver":     "GTiff",
                        "crs":        "EPSG:3857",
                        "transform":  dst_transform,
                        "width":      dst_width,
                        "height":     dst_height,
                        "compress":   "deflate",
                        "predictor":  2,
                        "tiled":      True,
                        "blockxsize": 512,
                        "blockysize": 512,
                        "BIGTIFF":    "YES",
                    })

                    with _rio_w.open(str(warped), "w", **dst_profile) as dst:
                        for b in range(1, src.count + 1):
                            _reproject(
                                source        = _rio_w.band(src, b),
                                destination   = _rio_w.band(dst, b),
                                src_transform = src.transform,
                                src_crs       = src.crs,
                                dst_transform = dst_transform,
                                dst_crs       = "EPSG:3857",
                                resampling    = _Resampling.bilinear,
                                num_threads   = 0)  # 0 = tous les CPUs
                _creer_fichier(warped)
                taille_w = warped.stat().st_size / 1e6
                elap = time.time() - t0_warp
                print("  " + lbl.ljust(36) + " [" + "█"*30 +
                      f"] 100%  {_hms(elap)}  {taille_w:.0f} Mo")
            except Exception as _e_warp:
                print(f"  ERREUR rasterio.warp {nom_tr} : {_e_warp}")
                continue

            # ── 2. Diagnostic dimensions warped (rasterio) ──────────────────
            bb_diag = _bbox_depuis_gdalinfo(warped)
            if bb_diag:
                try:
                    import rasterio as _rio_dx
                    with _rio_dx.open(str(warped)) as ds_diag:
                        _sz = (ds_diag.width, ds_diag.height)
                    print(f"  warped dims : {_sz[0]} × {_sz[1]} px  "
                          f"bbox merc : {bb_diag[0]:.0f},{bb_diag[1]:.0f}"
                          f" → {bb_diag[2]:.0f},{bb_diag[3]:.0f}", flush=True)
                except Exception:
                    print(f"  warped bbox : {bb_diag}", flush=True)

            # ── 3. Overviews via rasterio (remplace gdaladdo — étape 6) ──────
            # Resampling.gauss reproduit -r gauss de gdaladdo.
            if zoom_max > zoom_min and overview_levels:
                print(f"  Overviews (gauss) {overview_levels}...", flush=True)
                t_addo = time.time()
                try:
                    import rasterio as _rio_o
                    from rasterio.enums import Resampling as _Res_o
                    with _rio_o.open(str(warped), "r+") as ds_o:
                        ds_o.build_overviews(overview_levels, _Res_o.gauss)
                        ds_o.update_tags(ns="rio_overview", resampling="gauss")
                    print(f"  Overviews OK ({_hms(time.time()-t_addo)})")
                except Exception as _e_ovw:
                    print(f"  WARNING overviews : {_e_ovw} — tuilage natif")

        # ── 3. Bbox warped (EPSG:3857) ──────────────────────────────────────
        # Priorité : -te calculé lors du warp courant (pas besoin de proj.db).
        # Fallback mode cache : recalculer depuis bb_src avec pyproj/approx.
        if te_xmin is not None:
            bb_w = (te_xmin, te_ymin, te_xmax, te_ymax)
        elif warp_deja_fait and bb_src is not None:
            # Warped réutilisé : reconstruire la bbox Mercator depuis bb_src
            try:
                _t2 = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:3857")
                _rx0, _ry0 = _t2.transform(bb_src[0], bb_src[1])
                _rx1, _ry1 = _t2.transform(bb_src[2], bb_src[3])
            except Exception:
                _rx0, _ry0 = _lamb93_to_merc(bb_src[0], bb_src[1])
                _rx1, _ry1 = _lamb93_to_merc(bb_src[2], bb_src[3])
            bb_w = (min(_rx0, _rx1), min(_ry0, _ry1),
                    max(_rx0, _rx1), max(_ry0, _ry1))
        else:
            bb_w = _bbox_depuis_gdalinfo(warped, env)
        if bb_w is None:
            print(f"  ERROR: bbox not found for {lbl}")
            continue
        xmin_w, ymin_w, xmax_w, ymax_w = bb_w

        # ── 4. Tiling direct via rasterio ────────────────────────────────
        # Lecture directe du warped TIF par rasterio — pas de gdal_translate,
        # pas de fichiers temporaires, pas de proj.db requis pour les coords pixel.
        import rasterio as _rio
        from rasterio.windows import Window as _Win
        import numpy as _np

        batch = []
        BATCH = 500
        rangees_done = 0
        total_rangees_tr = max(1, sum(
            merc_to_tile(xmax_w, ymin_w, z)[1] -
            merc_to_tile(xmin_w, ymax_w, z)[1] + 1
            for z in range(zoom_min, zoom_max + 1)
        ))

        with _rio.open(str(warped)) as _ds:
            _w_orig_x = _ds.transform.c   # xmin Mercator
            _w_orig_y = _ds.transform.f   # ymax Mercator
            _w_res    = _ds.transform.a   # résolution pixel (m/px)
            _w_width  = _ds.width
            _w_height = _ds.height
            _w_count  = _ds.count         # nb bandes

            for z in range(zoom_min, zoom_max + 1):
                tx0, ty0 = merc_to_tile(xmin_w, ymax_w, z)
                tx1, ty1 = merc_to_tile(xmax_w, ymin_w, z)
                nb_cols  = tx1 - tx0 + 1
                band_w   = nb_cols * TILE_SIZE

                # Résolution de cette tuile par rapport au warped (qui est à zoom_max)
                zoom_factor = 2 ** (zoom_max - z)

                for ty in range(ty0, ty1 + 1):
                    bx0_t, _, _, by1_t = tile_bounds(tx0, ty, z)
                    _,     _, bx1_t, _ = tile_bounds(tx1, ty, z)

                    # Coordonnées pixel dans le warped TIF
                    px_off = int((bx0_t - _w_orig_x) / _w_res)
                    py_off = int((_w_orig_y - by1_t) / _w_res)
                    px_sz  = int(band_w * zoom_factor)
                    py_sz  = int(TILE_SIZE * zoom_factor)

                    # Clip aux limites du TIF
                    px_clip = max(0, px_off)
                    py_clip = max(0, py_off)
                    px_end  = min(_w_width,  px_off + px_sz)
                    py_end  = min(_w_height, py_off + py_sz)

                    if px_end <= px_clip or py_end <= py_clip:
                        # Rangée entièrement hors du TIF
                        pct = int(rangees_done / total_rangees_tr * 100)
                        elapsed = int(time.time() - t_tile)
                        sfx = f"  {_hms(elapsed)}" if elapsed % 30 == 0 else ""
                        print(f"\r  z{zoom_min}-{zoom_max} [" +
                              "█" * int(pct/100*30) +
                              "░" * (30 - int(pct/100*30)) +
                              f"] {pct:3d}%  {total_insere} tiles  {_hms(elapsed)}{sfx}",
                              end="", flush=True)
                        continue

                    try:
                        # Lire la fenêtre directement à la résolution tuile
                        # (rasterio redimensionne via out_shape — évite les grandes allocations)
                        win_w = px_end - px_clip
                        win_h = py_end - py_clip
                        out_w = max(1, int(win_w / zoom_factor))
                        out_h = max(1, int(win_h / zoom_factor))
                        win = _Win(px_clip, py_clip, win_w, win_h)
                        arr = _ds.read(window=win,
                                       out_shape=(_w_count, out_h, out_w),
                                       resampling=_rio.enums.Resampling.bilinear)

                        # Canvas à la taille de la bande de tuiles
                        dst_x = max(0, int((px_clip - px_off) / zoom_factor))
                        dst_y = max(0, int((py_clip - py_off) / zoom_factor))
                        canvas = _np.zeros(
                            (_w_count, TILE_SIZE, band_w), dtype=_np.uint8)
                        canvas[:, dst_y:dst_y+arr.shape[1],
                                  dst_x:dst_x+arr.shape[2]] = arr

                        # Convertir en image PIL — monobande conservée en
                        # mode "L" (pas de triplication RGB : _encode_tile
                        # en tire des PNG grayscale 2-3× plus petits ; les
                        # JPEG sont convertis RGB à l'encodage).
                        if _w_count >= 3:
                            img_arr = _np.moveaxis(canvas[:3], 0, 2)
                        else:
                            img_arr = canvas[0]

                        band_img = Image.fromarray(img_arr.astype(_np.uint8))
                        # Pas de resize — rasterio a déjà lu à la bonne résolution

                    except Exception as _e_read:
                        nb_echecs_tr += 1
                        if nb_echecs_tr <= 3:
                            print(f"\n  ⚠ rasterio read failure z{z} ty={ty}: "
                                  f"{_e_read}", flush=True)
                        pct = int(rangees_done / total_rangees_tr * 100)
                        elapsed = int(time.time() - t_tile)
                        print(f"\r  z{zoom_min}-{zoom_max} [" +
                              "█" * int(pct/100*30) +
                              "░" * (30 - int(pct/100*30)) +
                              f"] {pct:3d}%  {total_insere} tiles  {_hms(elapsed)}",
                              end="", flush=True)
                        continue

                    # Découper en tuiles individuelles puis encoder en parallèle
                    # (Pillow libère le GIL pendant JPEG/PNG save → ThreadPool donne
                    # un vrai parallélisme. Sur petites bandes le pool overhead l'emporte ;
                    # on bascule sur séquentiel sous _MIN_PAR_TILES tuiles.)
                    _tiles_args = []
                    for i, tx in enumerate(range(tx0, tx1 + 1)):
                        left = i * TILE_SIZE
                        tile = band_img.crop((left, 0, left + TILE_SIZE, TILE_SIZE))
                        if tile.getbbox() is None:
                            continue
                        _tiles_args.append((tile, z, tx, ty))

                    if _pool is not None and len(_tiles_args) >= _MIN_PAR_TILES:
                        for _res in _pool.map(_encode_tile, _tiles_args):
                            batch.append(_res)
                            total_insere += 1
                    else:
                        for _args in _tiles_args:
                            batch.append(_encode_tile(_args))
                            total_insere += 1

                    band_img.close()

                rangees_done += 1
                pct  = int(rangees_done / total_rangees_tr * 100)
                bars = int(pct / 100 * 30)
                elapsed = int(time.time() - t_tile)
                sfx = f"  [{i_tr+1}/{len(tranches)}]" if len(tranches) > 1 else ""
                print(f"\r  z{zoom_min}-{zoom_max} [" +
                      "█"*bars + "░"*(30-bars) +
                      f"] {pct:3d}%  {total_insere} tiles  {_hms(elapsed)}{sfx}",
                      end="", flush=True)

                if len(batch) >= BATCH:
                    cur.executemany(
                        "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                    con.commit()
                    batch.clear()

        if batch:
            cur.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con.commit()
            batch.clear()

        # warped conservé dans dossier_ville/ pour réutilisation future
        taille_w = warped.stat().st_size / 1e6 if warped.exists() else 0
        print(f"  Tiling cache kept: {warped.name}  ({taille_w:.0f} MB)"
              f"  — supprimez-le manuellement si inutile")

    con.close()
    if _pool is not None:
        _pool.shutdown(wait=True)
    elapsed = int(time.time() - t0)
    taille_mb = mbtiles.stat().st_size / 1e6 if mbtiles.exists() else 0
    print("\n  z" + str(zoom_min) + "-" + str(zoom_max) + " 100%  " + str(total_insere) + " tiles  " + _hms(elapsed))
    if nb_echecs_tr > 0:
        print(f"  ⚠ {nb_echecs_tr} rasterio rows failed (missing tiles)")
    print(f"  {mbtiles.name} : {total_insere} tiles  ({taille_mb:.0f} MB)")
    # Détection d'échec silencieux : 0 tuiles depuis une source non-triviale
    # indique typiquement un TIF source partiellement écrit (exception dans
    # un chunk SVF non détectée) ou une reprojection EPSG:3857 hors-bbox.
    # tif_source = paramètre de la fonction (chemin du TIF source).
    src_size_mb = tif_source.stat().st_size / 1e6 if tif_source.exists() else 0
    if total_insere == 0 and src_size_mb > 1:
        print(f"  ⚠ WARNING: 0 tiles generated from {src_size_mb:.0f} MB source.")
        print(f"    The source file may be partially written or badly georeferenced.")
        print(f"    Delete {tif_source.name} and relaunch to force recompute.")
    return mbtiles


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


# Cache GetCapabilities WMTS en session : (layer_id, apikey_requis) → (zoom_min, zoom_max) | None
_wmts_caps_cache: dict = {}
_wmts_caps_lock  = threading.Lock()   # protège les lectures/écritures concurrentes


# Plafonds (zoom_min, zoom_max) pour les couches XYZ sans GetCapabilities.
# Signature recherchée dans le template d'URL → limites. USGSImageryOnly = naip.
_XYZ_ZOOM_LIMITS = (
    ("USGSImageryOnly", (0, 16)),
)


def _lire_zoom_limites_wmts(layer, apikey_requis, apikey=""):
    """
    Interroge GetCapabilities WMTS IGN et retourne (zoom_min, zoom_max) réels
    pour la couche *layer* dans le TileMatrixSet PM.
    Résultat mis en cache pour la session ; retourne None si inaccessible.
    """
    # Couches XYZ (USGS Imagery, etc.) : pas de GetCapabilities WMTS IGN. On
    # plafonne via une table de limites connues (réutilise le clamp ci-dessous
    # comme pour l'IGN). USGSImageryOnly (naip) : LODs 0-16 au national ; au-delà
    # de z16, le cache ArcGIS renvoie des 204 → flot d'absences qui déclenche le
    # garde-fou « hors couverture » à tort. Sans limite connue → None (le 204
    # reste le filet de sécurité).
    if layer.startswith("XYZ:"):
        for _sig, _lim in _XYZ_ZOOM_LIMITS:
            if _sig in layer:
                return _lim
        return None
    cache_key = (layer, bool(apikey_requis))

    # Lecture du cache — verrou court, pas de réseau dedans
    with _wmts_caps_lock:
        if cache_key in _wmts_caps_cache:
            return _wmts_caps_cache[cache_key]

    # Requête réseau hors du verrou (évite de bloquer les autres threads)
    base = WMTS_URL if apikey_requis else WMTS_URL_PUB
    url  = f"{base}?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0"
    if apikey_requis and apikey:
        url += f"&apikey={apikey}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        print(f"  ⚠ WMTS GetCapabilities unreachable ({type(e).__name__}: {e}) — zoom capping skipped")
        with _wmts_caps_lock:
            _wmts_caps_cache[cache_key] = None
        return None

    _NS = {
        "wmts": "http://www.opengis.net/wmts/1.0",
        "ows":  "http://www.opengis.net/ows/1.1",
    }
    try:
        root = _ET.fromstring(xml_bytes)
    except Exception as e:   # xml.etree.ElementTree.ParseError — pas importé directement
        print(f"  ⚠ GetCapabilities parsing failed ({e})")
        with _wmts_caps_lock:
            _wmts_caps_cache[cache_key] = None
        return None

    for lyr in root.findall(".//wmts:Layer", _NS):
        ident = lyr.findtext("ows:Identifier", namespaces=_NS)
        if ident != layer:
            continue
        for link in lyr.findall("wmts:TileMatrixSetLink", _NS):
            if link.findtext("wmts:TileMatrixSet", namespaces=_NS) != "PM":
                continue
            limits = link.find("wmts:TileMatrixSetLimits", _NS)
            if limits is None:
                break
            zooms = []
            for tml in limits.findall("wmts:TileMatrixLimits", _NS):
                tm = tml.findtext("wmts:TileMatrix", namespaces=_NS)
                if tm is not None:
                    try: zooms.append(int(tm))
                    except ValueError: pass
            if zooms:
                result = (min(zooms), max(zooms))
                with _wmts_caps_lock:
                    _wmts_caps_cache[cache_key] = result
                return result
        break

    with _wmts_caps_lock:
        _wmts_caps_cache[cache_key] = None
    return None


def deg_to_tile(lat_deg, lon_deg, zoom):
    """Coordonnées WGS84 → tuile XYZ (convention Google/OSM, y=0 en haut)."""
    n = 2 ** zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    lat_r = math.radians(lat_deg)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi)
            / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max, zoom_min, zoom_max):
    """
    Retourne la liste de toutes les tuiles (z, x, y) couvrant la bbox WGS84
    pour tous les zooms demandés.
    """
    tuiles = []
    for z in range(zoom_min, zoom_max + 1):
        x0, y0 = deg_to_tile(lat_max, lon_min, z)   # coin NW (y petit)
        x1, y1 = deg_to_tile(lat_min, lon_max, z)   # coin SE (y grand)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                tuiles.append((z, x, y))
    return tuiles


def estimer_taille(nb_tuiles, format_img="jpeg"):
    """Estimation grossière : ~15 Ko/tuile JPEG Scan25, ~30 Ko ortho."""
    ko_par_tuile = 30 if format_img != "jpeg" else 15
    return nb_tuiles * ko_par_tuile // 1024   # Mo

# ============================================================
# CONSTRUCTION URL WMTS
# ============================================================

def construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """
    Construit l'URL de tuile (z, x, y).
    - WMTS IGN : TileMatrix=z, TileCol=x, TileRow=y (XYZ standard).
    - Source XYZ (layer == "XYZ:<template>", ex. USGS Imagery / NAIP) : substitue
      {z}/{x}/{y} dans le template ArcGIS/XYZ (même schéma Mercator, y top-origine).
    """
    if layer.startswith("XYZ:"):
        tmpl = layer[4:]
        return (tmpl.replace("{z}", str(z))
                    .replace("{x}", str(x))
                    .replace("{y}", str(y)))
    base = WMTS_URL if apikey_requis else WMTS_URL_PUB
    params = {
        "SERVICE":      "WMTS",
        "REQUEST":      "GetTile",
        "Version":      "1.0.0",
        "Layer":        layer,
        "Style":        style,
        "TileMatrixSet":"PM",
        "FORMAT":       fmt,
        "TileMatrix":   str(z),
        "TileCol":      str(x),
        "TileRow":      str(y),
    }
    if apikey_requis:
        params["apikey"] = apikey
    return base + "?" + urllib.parse.urlencode(params)

# ============================================================
# TÉLÉCHARGEMENT D'UNE TUILE
# ============================================================



# ── Connexions keep-alive pour le download WMTS ───────────────────────────────
# urllib.request.urlopen rouvre une connexion TCP+TLS par tuile (~90 ms de
# poignée de main perdus à chaque fois ; benchmark IGN planign : ~2x plus lent
# qu'une connexion réutilisée). Les tuiles d'un batch tapent toutes le même hôte
# (data.geopf.fr) : on garde une connexion HTTP/1.1 keep-alive par worker
# (thread-local), réutilisée d'une tuile à l'autre, avec reconnexion auto si le
# serveur ferme. Fermeture en fin de batch (generer_mbtiles_wmts).
import http.client

_wmts_conn_tl    = threading.local()
_wmts_conns      = []                  # connexions ouvertes (fermées en fin de batch)
_wmts_conns_lock = threading.Lock()


def _wmts_get_conn(scheme, host):
    cache = getattr(_wmts_conn_tl, "by_host", None)
    if cache is None:
        cache = {}; _wmts_conn_tl.by_host = cache
    conn = cache.get(host)
    if conn is None:
        cls = (http.client.HTTPSConnection if scheme == "https"
               else http.client.HTTPConnection)
        conn = cls(host, timeout=15)
        cache[host] = conn
        with _wmts_conns_lock:
            _wmts_conns.append(conn)
    return conn


def _wmts_drop_conn(host):
    cache = getattr(_wmts_conn_tl, "by_host", None)
    if cache and host in cache:
        try: cache[host].close()
        except Exception: pass
        del cache[host]


def _wmts_close_all_conns():
    """À appeler en fin de batch WMTS pour libérer les sockets keep-alive."""
    with _wmts_conns_lock:
        for c in _wmts_conns:
            try: c.close()
            except Exception: pass
        _wmts_conns.clear()


def _wmts_fetch(url):
    """GET via la connexion keep-alive thread-local (réutilisée d'une tuile à
    l'autre). Retourne (status, content_type, data). Une reconnexion si la
    connexion persistante a été fermée par le serveur."""
    parts = urllib.parse.urlsplit(url)
    host  = parts.netloc
    path  = parts.path + (("?" + parts.query) if parts.query else "")
    last_exc = None
    for _essai in (1, 2):
        conn = _wmts_get_conn(parts.scheme, host)
        try:
            conn.request("GET", path, headers=WMTS_HEADERS)
            resp = conn.getresponse()
            data = resp.read()        # lecture complète = condition de réutilisation
            return resp.status, resp.headers.get("content-type", ""), data
        except (http.client.HTTPException, OSError) as e:
            last_exc = e
            _wmts_drop_conn(host)     # connexion morte → on en recrée une au prochain tour
    raise last_exc if last_exc else IOError("WMTS fetch failed")


def telecharger_tuile(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """
    Télécharge une tuile et retourne les bytes, ou None si absente/erreur.
    Réessaie MAX_TENTATIVES fois avec délai exponentiel. Réutilise une connexion
    keep-alive par worker (cf. _wmts_fetch), ~2x plus rapide que urlopen/tuile.
    """
    url = construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis)
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            status, ct, data = _wmts_fetch(url)
            if status == 404:
                return None
            if not (200 <= status < 300):
                raise IOError(f"HTTP {status}")
            ct = (ct or "").lower()
            if "xml" in ct or "html" in ct:
                return None   # réponse d'erreur serveur
            if len(data) < 500:
                return None   # tuile vide / 204 (mer, hors couverture)
            return data
        except KeyboardInterrupt:
            # Propagation au handler top-level (sys.exit(130)) qui sait
            # nettoyer (lockfile, tmp). sys.exit(0) ici tuerait juste le
            # worker, masquerait l'interruption et casserait le code retour.
            raise
        except (urllib.error.URLError, IOError, OSError, http.client.HTTPException):
            if tentative < MAX_TENTATIVES:
                time.sleep(DELAI_RETRY * tentative)
            else:
                return None   # échec définitif, on ignore
    return None

# ============================================================
# GÉNÉRATION MBTILES
# ============================================================

def generer_mbtiles_wmts(chemin, tuiles_iter, total, nom_zone, fmt_ext,
                    zoom_min, zoom_max, layer, style, img_fmt,
                    apikey, apikey_requis, workers,
                    bbox_wgs84=None, jpeg_quality=None,
                    dossier_cache=None, ecraser_tuiles=False, ecraser_dalles=False):
    """
    Télécharge toutes les tuiles et les insère dans un fichier MBTiles.

    Convention MBTiles : y en TMS (y=0 en bas) → inversion depuis XYZ.

    jpeg_quality   : si défini et img_fmt est PNG, convertit PNG→JPEG à cette
                     qualité (gain ×3-5 sans double compression).
    dossier_cache  : si défini, les tuiles sont mises en cache sur disque
                     sous dossier_cache/<z>/<x>/<y>.<ext> et réutilisées
                     sans retélécharger lors des runs suivants.
    """

    if chemin.exists() and not ecraser_tuiles:
        print(f"  {chemin.name} → already present")
        return chemin
    if chemin.exists() and ecraser_tuiles:
        chemin.unlink()
        print(f"  {chemin.name} → overwrite")

    chemin.parent.mkdir(parents=True, exist_ok=True)

    # Calculer _convert_png ici — utilisé pour _meta_fmt et dans _dl
    _convert_png = (jpeg_quality is not None
                    and img_fmt.lower() in ("image/png", "png"))
    _meta_fmt    = "jpeg" if _convert_png else fmt_ext

    con = sqlite3.connect(str(chemin))
    con.execute("PRAGMA journal_mode=WAL;")   # écritures concurrentes sans lock global
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER,
                            tile_row INTEGER, tile_data BLOB);
        CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
    """)

    for k, v in [
        ("name",        chemin.stem),
        ("type",        "overlay"),
        ("version",     "1.0"),
        ("description", f"IGN {layer}"),
        ("format",      _meta_fmt),
        ("minzoom",     str(zoom_min)),
        ("maxzoom",     str(zoom_max)),
    ]:
        cur.execute("INSERT INTO metadata VALUES (?,?)", (k, v))

    # bounds requis par Locus : "left,bottom,right,top" en degrés WGS84
    if bbox_wgs84 is not None:
        _lon0, _lat0, _lon1, _lat1 = bbox_wgs84
        _bounds = f"{_lon0:.6f},{_lat0:.6f},{_lon1:.6f},{_lat1:.6f}"
        _cx = (_lon0 + _lon1) / 2
        _cy = (_lat0 + _lat1) / 2
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("bounds", _bounds))
        cur.execute("INSERT INTO metadata VALUES (?,?)",
                    ("center", f"{_cx:.6f},{_cy:.6f},{zoom_max}"))
    con.commit()

    BATCH       = BATCH_MBTILES_INSERT
    FENETRE     = workers * 4   # nb de futures en vol simultané — équilibre RAM/débit
    batch       = []
    done        = 0
    ok          = 0
    absentes    = 0    # 204 No Content (tuile hors couverture) — état IGN normal
    erreurs     = 0    # exceptions worker (timeout, 401, 5xx, parsing) — diagnostic
    err_consec  = 0    # erreurs consécutives — utile pour détection panne globale
    abort_msg   = None # set si on abort à mi-parcours (clé expirée, etc.)
    # Seuil d'abandon : au-delà de SEUIL_ERR_CONSEC erreurs consécutives,
    # on assume une panne systémique (clé API expirée, IGN down, réseau coupé)
    # et on n'écrit pas un MBTiles tronqué qui aurait l'apparence d'un succès.
    largeur     = 30
    t0          = time.time()

    _base_wmts = WMTS_URL if apikey_requis else WMTS_URL_PUB
    # Couches XYZ (USGS Imagery…) : pas un WMTS IGN → logger le vrai template.
    if layer.startswith("XYZ:"):
        _log_req(layer[4:], "XYZ tiles")
    else:
        _log_req(f"{_base_wmts}?SERVICE=WMTS&LAYER={layer}&...", "WMTS IGN")
    print(f"  Downloading {total:,} tiles -> {chemin.name}...", flush=True)

    _fmt_out = "jpeg" if _convert_png else fmt_ext   # format réel inséré

    # Quand on re-encode PNG→JPEG avec une qualité explicite, le binaire stocké
    # dépend de jpeg_quality. Sans versionner, un changement de --qualite-image
    # réutiliserait silencieusement les tuiles de l'ancienne qualité.
    # Si img_fmt est nativement JPEG (pas de re-encode), le cache ne dépend
    # pas de jpeg_quality (data IGN brute).
    _cache_qual_seg = (f"q{int(jpeg_quality)}"
                       if _convert_png and jpeg_quality is not None else "")

    def _cache_path(z, x, y):
        base = dossier_cache / str(z) / str(x)
        if _cache_qual_seg:
            base = base / _cache_qual_seg
        return base / f"{y}.{_fmt_out}"

    def _dl(args_t):
        z, x, y = args_t
        data = None
        # Lire depuis le cache si disponible
        if dossier_cache is not None and not ecraser_dalles:
            _cache_file = _cache_path(z, x, y)
            if _cache_file.exists():
                data = _cache_file.read_bytes()
        if data is None:
            data = telecharger_tuile(z, x, y, layer, style, img_fmt,
                                     apikey, apikey_requis)
            if data and _convert_png:
                try:
                    from PIL import Image as _PILImg
                    img = _PILImg.open(io.BytesIO(data)).convert("RGB")
                    buf = io.BytesIO()
                    img.save(buf, "JPEG", quality=jpeg_quality, optimize=True)
                    data = buf.getvalue()
                except Exception:
                    pass  # fallback : garder le PNG original
            # Écrire dans le cache
            if data and dossier_cache is not None:
                _cache_file = _cache_path(z, x, y)
                _cache_file.parent.mkdir(parents=True, exist_ok=True)
                _cache_file.write_bytes(data)
                _creer_fichier(_cache_file)
        return z, x, y, data

    def _afficher(done, total, ok, absentes, erreurs, z_courant, t0):
        pct     = done * 100 // max(total, 1)
        bars    = pct * largeur // 100
        elapsed = int(time.time() - t0)
        eta_s   = int(elapsed * (total - done) / max(done, 1))
        eta_str = f"  ETA {_hms(eta_s)}" if done > 10 and eta_s > 5 else ""
        err_str = f"  err:{erreurs}" if erreurs else ""
        print(f"\r  z{z_courant} [{'#'*bars}{'-'*(largeur-bars)}]"
              f" {pct:3d}%  {done:,}/{total:,}  ok:{ok:,}  abs:{absentes}{err_str}"
              f"  {_hms(elapsed)}{eta_str}",
              end="", flush=True)

    tuiles_list = list(tuiles_iter)   # déjà une liste, mais on s'assure
    z_courant   = tuiles_list[0][0] if tuiles_list else zoom_min

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Soumission par fenêtre glissante : on ne soumet FENETRE tâches à la fois
            # → la barre démarre immédiatement, RAM bornée même sur 100k tuiles
            pending = {}
            idx     = 0
            n       = len(tuiles_list)

            # Remplir la fenêtre initiale
            while idx < n and len(pending) < FENETRE:
                t = tuiles_list[idx]
                pending[pool.submit(_dl, t)] = t
                idx += 1

            # Boucle principale : on attend qu'au moins une future termine, puis
            # on draine TOUTES les futures terminées avant de re-remplir la fenêtre.
            # Performance : wait() enregistre ses callbacks UNE fois par appel,
            # contrairement à next(as_completed(pending)) en boucle qui réenregistre
            # des callbacks sur toutes les futures à chaque itération
            # (complexité O(N × FENETRE) → O(N) en surcharge bookkeeping).
            # Sur 100k tuiles dept-scale : gagne plusieurs minutes de CPU pur overhead.
            while pending:
                if _stop_event.is_set() or abort_msg is not None:
                    # Cancellation propre : annuler les futures non démarrées,
                    # laisser les actives finir leur HTTP courant.
                    for f in list(pending.keys()):
                        f.cancel()
                    break

                done_set, _ = wait(pending, return_when=FIRST_COMPLETED)

                # Drainer tout ce qui est terminé (peut être plusieurs en concurrent)
                for done_future in done_set:
                    del pending[done_future]

                    try:
                        z, x, y, data = done_future.result()
                    except Exception as _exc_dl:
                        # Une exception worker n'est PAS une absence (204 IGN normal).
                        # On la compte distinctement pour diagnostiquer panne réseau,
                        # 401/403 (clé expirée), 5xx persistants, etc. Si trop d'erreurs
                        # consécutives, on assume une panne systémique et on abort.
                        done       += 1
                        erreurs    += 1
                        err_consec += 1
                        if err_consec >= SEUIL_ERR_CONSEC and abort_msg is None:
                            abort_msg = (f"{err_consec} erreurs consécutives "
                                         f"(dernière : {type(_exc_dl).__name__}: {_exc_dl}). "
                                         f"Probable panne réseau / clé API / IGN. "
                                         f"MBTiles non finalisé pour éviter un fichier tronqué.")
                        _afficher(done, total, ok, absentes, erreurs, z_courant, t0)
                        if idx < n:
                            t = tuiles_list[idx]
                            pending[pool.submit(_dl, t)] = t
                            idx += 1
                        continue

                    done      += 1
                    z_courant  = z

                    if data:
                        y_tms = (1 << z) - 1 - y
                        batch.append((z, x, y_tms, data))
                        ok += 1
                        err_consec = 0   # succès : reset
                    else:
                        absentes += 1
                        # 204 No Content (data=None) — pas une erreur réseau, pas
                        # de reset du compteur consécutif (on ne veut pas que
                        # 100 tuiles hors couverture entrecoupées masquent une
                        # panne transitoire qui revient).
                        # Garde-fou couverture : si AUCUNE tuile n'est dans la
                        # couche après un échantillon significatif, la zone est
                        # hors couverture — typiquement bbox hors zone, ou ordre
                        # --zone-bbox inversé (W,S,E,N = longitude d'abord). On
                        # abort tôt au lieu de tenter 100k tuiles vides en silence.
                        if (absentes >= SEUIL_HORS_COUVERTURE
                                and ok * 50 < absentes and abort_msg is None):
                            abort_msg = (
                                f"{absentes} tuiles hors couverture (204) pour "
                                f"seulement {ok} dans la couche. Zone hors de la "
                                f"couche, ou ordre de --zone-bbox inversé : il attend "
                                f"W,S,E,N (longitude d'abord, ex. -5.0,47.8,-2.6,49.0).")

                    if len(batch) >= BATCH:
                        cur.executemany(
                            "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                        con.commit()
                        batch.clear()

                    _afficher(done, total, ok, absentes, erreurs, z_courant, t0)

                    # Soumettre la prochaine tâche pour maintenir la fenêtre pleine
                    if idx < n:
                        t = tuiles_list[idx]
                        pending[pool.submit(_dl, t)] = t
                        idx += 1

        if batch:
            cur.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con.commit()
    finally:
        # Toujours fermer la connexion, même sur exception non capturée
        # (KeyboardInterrupt, MemoryError, OSError disque plein…).
        # Sans ça la WAL reste ouverte, le .mbtiles-wal/-shm traîne.
        try: con.close()
        except Exception: pass
        _wmts_close_all_conns()   # libérer les connexions keep-alive du batch

    # Garde-fou couverture (petites zones sous le seuil mi-parcours) : aucune
    # tuile dans la couche → même diagnostic. Évite un MBTiles vide "0 tiles"
    # présenté comme un succès.
    if (abort_msg is None and not _stop_event.is_set()
            and absentes > 0 and ok * 50 < absentes):
        abort_msg = (f"{ok} tuile(s) dans la couverture pour {absentes} hors couche "
                     f"(204). Zone hors de la couche, ou ordre de --zone-bbox inversé "
                     f": il attend W,S,E,N (longitude d'abord, ex. -5.0,47.8,-2.6,49.0).")

    if abort_msg is not None:
        # MBTiles removed: un fichier vide-presque ferait croire à un succès.
        # Si l'utilisateur veut analyser le partiel, il rejouera et verra les
        # logs.
        try: chemin.unlink(missing_ok=True)
        except Exception: pass
        print(f"\n  ✗ ABANDON : {abort_msg}")
        raise RuntimeError(f"WMTS abort : {abort_msg}")

    if _stop_event.is_set():
        # Manifeste partiel : signaler à l'utilisateur que l'écriture est incomplète
        elapsed = int(time.time() - t0)
        taille_mo = chemin.stat().st_size / 1e6 if chemin.exists() else 0.0
        print(f"\n  Interrupted - {ok} tiles written before stop  ({taille_mo:.0f} MB)")
        raise KeyboardInterrupt("MBTiles WMTS interrompu par utilisateur")

    elapsed = int(time.time() - t0)
    taille_mo = chemin.stat().st_size / 1e6
    err_str = f"  ({erreurs} erreurs)" if erreurs else ""
    print(f"\n  100%  {ok} tiles  ({absentes} missing){err_str}  {_hms(elapsed)}")
    print(f"  {chemin.name} : {ok} tiles  ({taille_mo:.0f} MB)")
    return chemin

# ============================================================
# GÉNÉRATION RMAP
# ============================================================

# ── Helpers LE ────────────────────────────────────────────────────────────────
def _wi(v):  return struct.pack('<i', v)   # int32 little-endian signé
def _wl(v):  return struct.pack('<q', v)   # int64 little-endian signé

def _tile_to_geo(tx, ty_xyz, z):
    """Retourne (lon_min, lat_min, lon_max, lat_max) pour la tuile XYZ."""
    n = 2 ** z
    lon_min = tx / n * 360.0 - 180.0
    lon_max = (tx + 1) / n * 360.0 - 180.0
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty_xyz / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty_xyz + 1) / n))))
    return lon_min, lat_min, lon_max, lat_max

def _empty_jpeg_256():
    """Génère un JPEG 256×256 gris (tuile vide pour positions sans données)."""
    try:
        from PIL import Image
        img = Image.new('RGB', (256, 256), (180, 180, 180))
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=50)
        return buf.getvalue()
    except Exception:
        # Fallback : JPEG minimal valide 1×1 px gris
        # (séquence SOI + APP0 + DQT + SOF0 + DHT + SOS + EOI)
        return (b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
                b'\xff\xdb\x00C\x00\x10\x0b\x0c\x0e\x0c\n\x10\x0e\r\x0e\x12\x11\x10'
                b'\x13\x18(\x1a\x18\x16\x16\x18\x310#$\x1d(=3<9\x10\x11\x11\x16\x13'
                b'\x16)\x1a\x1a)>\x1e\x1e\x1e=<<=>>><>@@@?BBB?BBBBBBBBBBBBBBBBBB'
                b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
                b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
                b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
                b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
                b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa'
                b'\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br'
                b'\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJ'
                b'STUVWXYZ\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf8k\xff\xd9')

# ── Fonction principale ────────────────────────────────────────────────────────

def generer_rmap_depuis_mbtiles(mbtiles_path, ecraser=False):
    """
    Génère un fichier .rmap (format binaire CompeGPS/TwoNav) depuis un .mbtiles.

    Format RMAP — reverse-engineered depuis MOBAC TwoNavRMAP.java (GPL v2) :

    FILE HEADER (offset 0, little-endian) :
      "CompeGPSRasterImage"    19 bytes ASCII (magic)
      int32  10 · int32  7 · int32  0
      int32  width_max · int32  -height_max
      int32  24 (bpp) · int32  1
      int32  256 (tileW) · int32  256 (tileH)
      int64  mapDataOffset
      int32  0 · int32  nZooms
      int64 × nZooms  zoom_header_offsets

    ZOOM HEADER (à zoom_header_offsets[n]) :
      int32  width · int32  -height
      int32  xTiles · int32  yTiles
      int64 × (xTiles × yTiles)  tile_offsets
        ordre : y outer, x inner → jpegOffsets[x][y]

    TILE (à tile_offsets[tx][ty]) :
      int32  7 (tag) · int32  len(jpeg) · bytes jpeg

    MAP INFO (à mapDataOffset) :
      int32  1 (tag) · int32  len(text) · bytes text (CompeGPS MAP format ASCII)

    Contrainte RMAP : tous les zoom levels doivent couvrir la même zone géo.
    Convention y : XYZ (y=0 haut, Nord), inverse du TMS stocké dans MBTiles.
    """

    rmap = mbtiles_path.with_suffix(".rmap")
    if rmap.exists() and not ecraser:
        print(f"  {rmap.name} → already present")
        return rmap
    if rmap.exists() and ecraser:
        rmap.unlink()
    if not mbtiles_path.exists():
        print(f"  ERROR: {mbtiles_path.name} not found")
        return None

    print(f"  RMAP ← {mbtiles_path.name}...", flush=True)
    t0 = time.time()

    EMPTY_JPEG = _empty_jpeg_256()
    TILE_SZ    = 256

    con = sqlite3.connect(str(mbtiles_path))
    try:
        # ── Phase 1 : inventaire par zoom ─────────────────────────────────────
        zooms = [r[0] for r in con.execute(
            "SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level DESC").fetchall()]
        if not zooms:
            print("  ERROR: MBTiles empty")
            return None

        # Étendue (x, y XYZ) par zoom
        zm = {}
        for z in zooms:
            r = con.execute(
                "SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
                "FROM tiles WHERE zoom_level=?", (z,)).fetchone()
            xmin_c, xmax_c, ymin_tms, ymax_tms = r
            n = 1 << z
            # TMS → XYZ : y_xyz = (n-1) - y_tms
            y0_xyz = (n - 1) - ymax_tms   # petit y_tms = grand y_xyz (Nord)
            y1_xyz = (n - 1) - ymin_tms
            nx = xmax_c - xmin_c + 1
            ny = y1_xyz - y0_xyz + 1
            zm[z] = {'x0': xmin_c, 'y0': y0_xyz, 'nx': nx, 'ny': ny,
                      'w': nx * TILE_SZ, 'h': ny * TILE_SZ}

        # Zoom le plus détaillé = index 0 dans RMAP
        z_max   = zooms[0]
        w_max   = zm[z_max]['w']
        h_max   = zm[z_max]['h']
        n_zooms = len(zooms)

        # Coordonnées géo depuis zoom max
        zd     = zm[z_max]
        lon_min, lat_min, lon_max, lat_max = _tile_to_geo(
            zd['x0'], zd['y0'] + zd['ny'] - 1, z_max)
        lon_max = _tile_to_geo(zd['x0'] + zd['nx'] - 1, zd['y0'], z_max)[2]
        lat_max = _tile_to_geo(zd['x0'], zd['y0'], z_max)[3]

        total_tiles = sum(zm[z]['nx'] * zm[z]['ny'] for z in zooms)
        print(f"  {n_zooms} zoom(s), {total_tiles:,} tile positions", flush=True)

        # ── Phase 2 : écriture séquentielle — offsets enregistrés à la volée ──
        tile_off = {}
        zoom_hdr_offset = {}

        largeur = 30
        done    = 0

        try:
            with open(str(rmap), 'wb') as f:

                # --- FILE HEADER placeholder ---
                f.write(b'CompeGPSRasterImage')
                f.write(_wi(10)); f.write(_wi(7)); f.write(_wi(0))
                f.write(_wi(w_max)); f.write(_wi(-h_max))
                f.write(_wi(24)); f.write(_wi(1))
                f.write(_wi(TILE_SZ)); f.write(_wi(TILE_SZ))
                map_data_off_pos = f.tell()
                f.write(_wl(0))
                f.write(_wi(0))
                f.write(_wi(n_zooms))
                zoom_off_arr_pos = f.tell()
                for _ in zooms:
                    f.write(_wl(0))

                # --- ZOOM HEADERS + TILE DATA ---
                for z in zooms:
                    zd = zm[z]

                    # Pré-chargement des tuiles de ce zoom en mémoire : une seule
                    # requête au lieu de nx×ny SELECTs (gain ×100 à ×1000 sur les
                    # gros MBTiles). Mémoire bornée par le zoom courant — libérée
                    # avant de passer au zoom suivant.
                    tuiles_z = {
                        (col, row): data
                        for col, row, data in con.execute(
                            "SELECT tile_column, tile_row, tile_data FROM tiles "
                            "WHERE zoom_level=?", (z,))
                    }

                    zoom_hdr_offset[z] = f.tell()
                    f.write(_wi(zd['w'])); f.write(_wi(-zd['h']))
                    f.write(_wi(zd['nx'])); f.write(_wi(zd['ny']))
                    tile_hdr_pos = f.tell()
                    for _ in range(zd['nx'] * zd['ny']):
                        f.write(_wl(0))

                    tile_off[z] = {}

                    for tx in range(zd['nx']):
                        for ty in range(zd['ny']):
                            col     = zd['x0'] + tx
                            y_xyz   = zd['y0'] + ty
                            y_tms   = (1 << z) - 1 - y_xyz

                            jpeg = tuiles_z.get((col, y_tms), EMPTY_JPEG)

                            tile_off[z][(tx, ty)] = f.tell()
                            f.write(_wi(7))
                            f.write(_wi(len(jpeg)))
                            f.write(jpeg)

                            done += 1
                            if done % 500 == 0 or done == total_tiles:
                                pct  = done * 100 // max(total_tiles, 1)
                                bars = pct * largeur // 100
                                elapsed = int(time.time() - t0)
                                print(f"\r  RMAP z{z} [{'█'*bars}{'░'*(largeur-bars)}]"
                                      f" {pct:3d}%  {done:,}/{total_tiles:,}"
                                      f"  {_hms(elapsed)}",
                                      end="", flush=True)

                    # Libérer la mémoire des tuiles de ce zoom avant le suivant
                    tuiles_z = None

                    # --- RÉÉCRIRE le zoom header avec les vrais offsets ---
                    pos_after = f.tell()
                    f.seek(tile_hdr_pos)
                    for ty in range(zd['ny']):
                        for tx in range(zd['nx']):
                            f.write(_wl(tile_off[z][(tx, ty)]))
                    f.seek(pos_after)

                # --- MAP INFO ---
                map_data_offset = f.tell()
                map_text = _build_map_info(
                    mbtiles_path.name, w_max, h_max,
                    lon_min, lat_min, lon_max, lat_max)
                map_bytes = map_text.encode('ascii')
                f.write(_wi(1))
                f.write(_wi(len(map_bytes)))
                f.write(map_bytes)

                # --- RÉÉCRIRE FILE HEADER avec vrais offsets ---
                f.seek(map_data_off_pos)
                f.write(_wl(map_data_offset))

                f.seek(zoom_off_arr_pos)
                for z in zooms:
                    f.write(_wl(zoom_hdr_offset[z]))

        except Exception as e:
            print(f"\n  ERREUR RMAP : {e}")
            import traceback; traceback.print_exc()
            rmap.unlink(missing_ok=True)
            return None

        elapsed   = int(time.time() - t0)
        taille_mo = rmap.stat().st_size / 1e6
        print(f"\n  {rmap.name} : {taille_mo:.0f} MB  {_hms(elapsed)}")
        return rmap
    finally:
        # Garantit la fermeture de la connexion SQLite même sur exception
        # non capturée (KeyboardInterrupt, MemoryError, disque plein…).
        try: con.close()
        except Exception: pass


def generer_sqlitedb_depuis_mbtiles(mbtiles_path, ecraser=False):
    """
    Génère un fichier .sqlitedb (format natif Locus Map) depuis un .mbtiles.

    Schéma SQLiteDB (format interne Locus / RMaps Android) :
      CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB)
      CREATE TABLE android_metadata (locale TEXT)
      CREATE TABLE info (minzoom INT, maxzoom INT)

    Coordonnées : x=col, y=row XYZ (y=0 en haut/Nord), z=zoom, s=0 (inutilisé).
    Conversion TMS→XYZ : y_xyz = (2^z - 1) - tile_row_tms.

    C'est le format que Locus utilise en interne pour son cache de cartes en ligne.
    Zéro risque de compatibilité, auto-load et Quick map switch fonctionnent.
    """

    sqlitedb = mbtiles_path.with_suffix(".sqlitedb")
    if sqlitedb.exists() and not ecraser:
        print(f"  {sqlitedb.name} → already present")
        return sqlitedb
    if sqlitedb.exists() and ecraser:
        sqlitedb.unlink()
    if not mbtiles_path.exists():
        print(f"  ERROR: {mbtiles_path.name} not found")
        return None

    con_mb = sqlite3.connect(str(mbtiles_path))
    con_db = None
    try:
        meta = {}
        try:
            meta = dict(con_mb.execute("SELECT name, value FROM metadata").fetchall())
        except Exception:
            pass
        zoom_min = int(meta.get("minzoom", 0))
        zoom_max = int(meta.get("maxzoom", 17))
        total = con_mb.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]

        print(f"  SQLiteDB ← {mbtiles_path.name}  ({total:,} tuiles)...", flush=True)
        t0 = time.time()

        con_db = sqlite3.connect(str(sqlitedb))
        con_db.execute("PRAGMA journal_mode=WAL;")   # écritures concurrentes sans lock global
        con_db.executescript("""
            CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB);
            CREATE TABLE android_metadata (locale TEXT);
            CREATE TABLE info (minzoom INT, maxzoom INT);
            CREATE UNIQUE INDEX idx_tiles ON tiles (x, y, z, s);
        """)
        con_db.execute("INSERT INTO android_metadata VALUES (?)", ("fr_FR",))
        con_db.execute("INSERT INTO info VALUES (?, ?)", (zoom_min, zoom_max))
        con_db.commit()

        BATCH   = BATCH_SQLITEDB_INSERT
        batch   = []
        done    = 0
        largeur = 30

        try:
            for zoom_level, tile_column, tile_row, tile_data in con_mb.execute(
                    "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles"):
                y_xyz = (1 << zoom_level) - 1 - tile_row   # TMS → XYZ
                batch.append((tile_column, y_xyz, zoom_level, 0, tile_data))
                done += 1
                if len(batch) >= BATCH:
                    con_db.executemany(
                        "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?,?)", batch)
                    con_db.commit()
                    batch.clear()
                    pct  = done * 100 // max(total, 1)
                    bars = pct * largeur // 100
                    elapsed = int(time.time() - t0)
                    print(f"\r  SQLiteDB [{'█'*bars}{'░'*(largeur-bars)}]"
                          f" {pct:3d}%  {done:,}/{total:,}  {_hms(elapsed)}",
                          end="", flush=True)
            if batch:
                con_db.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?,?)", batch)
                con_db.commit()
        except Exception as e:
            print(f"\n  ERREUR SQLiteDB : {e}")
            sqlitedb.unlink(missing_ok=True)
            return None

        elapsed   = int(time.time() - t0)
        taille_mo = sqlitedb.stat().st_size / 1e6
        print(f"\n  {sqlitedb.name} : {done:,} tiles  ({taille_mo:.0f} MB)"
              f"  {_hms(elapsed)}          ")
        return sqlitedb
    finally:
        # Toujours fermer les deux connexions, même sur exception non capturée.
        try: con_mb.close()
        except Exception: pass
        if con_db is not None:
            try: con_db.close()
            except Exception: pass


def _build_map_info(bitmap_name, width, height, lon_min, lat_min, lon_max, lat_max):
    """Génère le bloc texte CompeGPS MAP (calibration géographique)."""
    lines = [
        "CompeGPS MAP File\r\n",
        "<Header>\r\n",
        "Version=2\r\n",
        "VerCompeGPS=MOBAC\r\n",
        "Projection=2,Mercator,\r\n",
        "Coordinates=1\r\n",
        "Datum=WGS 84\r\n",
        "</Header>\r\n",
        "<Map>\r\n",
        f"Bitmap={bitmap_name}\r\n",
        "BitsPerPixel=0\r\n",
        f"BitmapWidth={width}\r\n",
        f"BitmapHeight={height}\r\n",
        "Type=10\r\n",
        "</Map>\r\n",
        "<Calibration>\r\n",
        f"P0=0,0,A,{lon_min:.8f},{lat_max:.8f}\r\n",
        f"P1={width-1},0,A,{lon_max:.8f},{lat_max:.8f}\r\n",
        f"P2={width-1},{height-1},A,{lon_max:.8f},{lat_min:.8f}\r\n",
        f"P3=0,{height-1},A,{lon_min:.8f},{lat_min:.8f}\r\n",
        "</Calibration>\r\n",
        "<MainPolygonBitmap>\r\n",
        "M0=0,0\r\n",
        f"M1={width},0\r\n",
        f"M2={width},{height}\r\n",
        f"M3=0,{height}\r\n",
        "</MainPolygonBitmap>\r\n",
    ]
    return "".join(lines)


def _java_opts_extra():
    """Options JVM additionnelles à passer à osmosis.

    Mode frozen : pointe `user.home` vers BUNDLE_DIR (sans `.openstreetmap/`)
    pour empêcher osmosis de scanner `%USERPROFILE%\\.openstreetmap\\osmosis\\plugins\\`.
    Sinon le plugin mapwriter serait chargé deux fois (CLASSPATH bundlé +
    plugins dir utilisateur) → OsmosisRuntimeException "Task type already exists".
    """
    if not getattr(sys, "frozen", False):
        return ""
    fake_home = str(BUNDLE_DIR).replace("\\", "/")
    # Quoter pour gérer les espaces dans le chemin (cmd + osmosis.bat).
    return f' "-Duser.home={fake_home}"'


def _preparer_osmosis(dossier_hint=None):
    """
    Vérifie mapwriter, trouve java + osmosis, retourne (osmosis_exe, java_home).
    Retourne (None, None) en cas d'échec.
    dossier_hint : Path optionnel pour la recherche de tagmapping-min.xml (non utilisé ici).
    """
    if not _verifier_mapwriter():
        print("  ERROR: mapwriter plugin missing - .map map impossible.")
        return None, None
    _java_exe = _trouver_java()
    if not _java_exe:
        return None, None
    _osmosis_exe = _trouver_osmosis()
    if not _osmosis_exe:
        print("  ERROR: osmosis not found")
        return None, None
    _java_home = str(Path(_java_exe).parent.parent)
    return _osmosis_exe, _java_home


# Tokens d'intérêt : seules les lignes qui contiennent un de ces marqueurs
# sont AFFICHÉES en live. Le reste est silencieux (le terminal reste propre,
# comme avant l'étape 5 quand on faisait capture_output=True).
# Les lignes silencieuses sont quand même conservées dans stderr_diag pour
# le diagnostic en cas de returncode != 0.
# Couvre Java util.logging FR/EN, exceptions, et causes chaînées.
_OSMOSIS_INTERESSANT = (
    "ERROR", "SEVERE", "FATAL", "Exception", "Caused by",
    "WARNING", "AVERTISSEMENT", "WARN ",
)


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
    import threading as _th

    proc = subprocess.Popen(
        cmd_or_str,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=shell, env=env,
    )

    # Buffer borné des dernières lignes stderr (collections.deque pour O(1) ops)
    from collections import deque
    stderr_tail = deque(maxlen=500)
    affichees = [0]   # nb de lignes vraiment affichées (pour ajouter \n initial)
    lock = _th.Lock()

    def _reader(stream, is_stderr):
        try:
            for raw in iter(stream.readline, b""):
                try:
                    line = raw.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    continue
                if not line:
                    continue
                if is_stderr:
                    stderr_tail.append(line)
                # Whitelist : afficher seulement si la ligne contient un marqueur
                # d'erreur ou d'avertissement explicite. Tout le reste est silent.
                if not any(tok in line for tok in _OSMOSIS_INTERESSANT):
                    continue
                with lock:
                    if affichees[0] == 0:
                        print()  # newline avant la 1ère ligne intéressante
                    affichees[0] += 1
                    print(f"  {line}", flush=True)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    th_out = _th.Thread(target=_reader, args=(proc.stdout, False), daemon=True)
    th_err = _th.Thread(target=_reader, args=(proc.stderr, True),  daemon=True)
    th_out.start(); th_err.start()

    proc.wait()
    th_out.join(timeout=5)
    th_err.join(timeout=5)

    return proc.returncode, "\n".join(stderr_tail)


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
    import tempfile as _tf
    tmp = Path(_tf.gettempdir())
    if not tmp.exists():
        return 0, 0

    cutoff = time.time() - min_age_s
    nb, bytes_freed = 0, 0
    for pattern in ("idxNodes*.tmp", "idxWays*.tmp"):
        for f in tmp.glob(pattern):
            try:
                st = f.stat()
                if st.st_mtime > cutoff:
                    continue   # trop récent, peut-être en cours d'utilisation
                size = st.st_size
                f.unlink()
                nb += 1
                bytes_freed += size
            except (OSError, PermissionError):
                pass   # verrouillé ou disparu — best-effort
    if nb and verbose:
        print(f"  ✓ Cleaned {nb} orphan osmosis temp file(s) "
              f"({bytes_freed/1e6:.0f} MB)")
    return nb, bytes_freed


def generer_carte_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                      osm_tags=None, export_geojson=True, ecraser_tuiles=False,
                      skip_bbox=False, geojson_formats=None):
    """
    Génère une carte Mapsforge (.map) via osmosis — format natif Locus Map.
    Nécessite osmosis + tagmapping-min.xml dans le même dossier que le script.

    geojson_formats : liste des formats à produire pour l'export GeoJSON.
                      ["gz"] (défaut), ["geojson"], ou ["gz", "geojson"].
    """
    import shutil as _sh

    if geojson_formats is None:
        geojson_formats = ["gz"]

    # Nettoyage des fichiers d'index osmosis orphelins (< 5 min ignorés pour
    # ne pas tirer dans le pied d'un osmosis concurrent). Best-effort, ne
    # bloque jamais la suite.
    if WINDOWS:
        _nettoyer_osmosis_temp_orphelins(verbose=True)

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    chemin_map     = dossier_ville / f"{nom_zone}.map"
    chemin_map_tmp = dossier_ville / f"{nom_zone}.map.tmp"

    # Nettoyer un éventuel .map.tmp laissé par une exécution précédente interrompue
    chemin_map_tmp.unlink(missing_ok=True)

    # Vérifier la présence des GeoJSON selon les formats DEMANDÉS, pas
    # selon le premier qu'on trouve. Si on demande "gz geojson" et qu'on
    # n'a que le .gz, il faut quand même regénérer le .geojson manquant.
    chemin_geojson_gz  = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_geojson_raw = dossier_ville / f"{nom_zone}_osm.geojson"
    _need_gz   = "gz"      in geojson_formats
    _need_raw  = "geojson" in geojson_formats
    geojson_present = ((not _need_gz  or chemin_geojson_gz.exists())
                       and (not _need_raw or chemin_geojson_raw.exists()))

    if chemin_map.exists() and ecraser_tuiles:
        chemin_map.unlink()
        print(f"  Carte OSM : overwrite {chemin_map.name}")
        # Supprimer aussi les geojson pour les recalculer
        for _gf in [chemin_geojson_gz, chemin_geojson_raw]:
            if _gf.exists(): _gf.unlink()
    if chemin_map.exists() and not ecraser_tuiles:
        if not export_geojson or geojson_present:
            print(f"  OSM map already present: {chemin_map.name} - skipped")
            return chemin_map
        else:
            # .map ok mais .geojson(.gz) manquant
            # Utiliser le PBF filtré (déjà extrait par osmosis) si disponible
            print(f"  OSM map already present: {chemin_map.name} - GeoJSON missing, exporting...")
            chemin_pbf_filtre = dossier_ville / f"{nom_zone}_filtered.pbf"
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            if pbf_src == chemin_pbf_filtre:
                print(f"  Existing filtered PBF: {chemin_pbf_filtre.name}")
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src,
                                osm_tags=osm_tags, ecraser_tuiles=ecraser_tuiles,
                                formats=geojson_formats)
            return chemin_map

    if not _verifier_mapwriter():
        print("  ERROR: mapwriter plugin missing - .map map impossible.")
        return None

    _osmosis_exe, _java_home = _preparer_osmosis()
    if not _osmosis_exe:
        return None
    _env_osm = os.environ.copy()
    _env_osm["JAVA_HOME"] = _java_home
    # JAVA_OPTS : heap max 6g — nécessaire pour le PBF France (~5 Go)
    # JAVACMD_OPTIONS : variable lue par osmosis.bat pour passer les options JVM
    _java_extra = _java_opts_extra()
    _env_osm["JAVA_OPTS"]       = "-Xmx6g" + _java_extra
    _env_osm["JAVACMD_OPTIONS"] = "-Xmx6g" + _java_extra

    # tagmapping-min.xml : chercher à côté du script puis dans le dossier dalles
    # En mode frozen, le fichier est bundlé dans sys._MEIPASS (BUNDLE_DIR).
    _tagmapping = None
    for cand in [
        DOSSIER_TRAVAIL / "tagmapping-min.xml",
        BUNDLE_DIR      / "tagmapping-min.xml",
        Path(str(osm_pbf)).parent / "tagmapping-min.xml",
        dossier_ville / "tagmapping-min.xml",
    ]:
        if cand.exists():
            _tagmapping = str(cand)
            break
    if not _tagmapping:
        print("  WARNING: tagmapping-min.xml not found - using osmosis default")

    t0 = time.time()
    print(f"  osmosis → {chemin_map.name}...", flush=True)

    if osm_tags is None:
        osm_tags = ["highway=*", "waterway=*", "boundary=administrative",
                    "natural=water", "natural=coastline",
                    "waterway=river", "waterway=stream", "waterway=canal"]
    osm_tags = list(dict.fromkeys(osm_tags))
    print(f"  Tags : {' '.join(osm_tags)}", flush=True)

    chemin_pbf_filtre = dossier_ville / f"{nom_zone}_filtered.pbf"

    cmd = [_osmosis_exe, "--read-pbf", f"file={osm_pbf}"]
    if not skip_bbox:
        cmd += [
            "--bounding-box",
            f"left={lon_min:.4f}", f"right={lon_max:.4f}",
            f"top={lat_max:.4f}", f"bottom={lat_min:.4f}",
        ]
    cmd += ["--tf", "accept-ways"]
    cmd += osm_tags
    cmd += [
        "--used-node",
        "--tee", "2",
        "--mapfile-writer",
        f"file={chemin_map_tmp}",
        "zoom-interval-conf=7,0,7,11,8,11,14,12,21",
        "tag-values=true", "polygon-clipping=true",
        "way-clipping=true", "label-position=true",
        "type=hd",   # HDTileBasedDataProcessor : écrit sur disque → pas de OutOfMemoryError
    ]
    if _tagmapping:
        cmd.append(f"tag-conf-file={_tagmapping}")
    cmd += ["--write-pbf", f"file={chemin_pbf_filtre}"]

    # Injecter JAVA_HOME dans l'env avant de lancer
    _shell = WINDOWS and str(_osmosis_exe).endswith(".bat")
    if _shell:
        cmd_str = " ".join(
            f'"{a}"' if (" " in str(a) or "=" in str(a)) else str(a)
            for a in cmd
        )
    _log_req(cmd)
    rc, stderr_diag = _run_osmosis_streaming(
        cmd_str if _shell else cmd,
        shell=_shell, env=_env_osm,
    )

    if rc == 0 and chemin_map_tmp.exists() and chemin_map_tmp.stat().st_size > 0:
        chemin_map_tmp.replace(chemin_map)
        taille_b = chemin_map.stat().st_size
        if taille_b < 1_000_000:
            print(f"  {chemin_map.name} : {taille_b // 1024} Ko  {_hms(time.time()-t0)}")
        else:
            print(f"  {chemin_map.name} : {taille_b / 1e6:.1f} MB  {_hms(time.time()-t0)}")
        if export_geojson:
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src,
                                osm_tags=osm_tags, formats=geojson_formats)
        return chemin_map
    else:
        chemin_map_tmp.unlink(missing_ok=True)
        print(f"  ERREUR osmosis mapfile-writer (code {rc})")
        if stderr_diag:
            # stderr_diag contient les 500 dernières lignes (toutes confondues).
            # On extrait celles qui contiennent un marqueur d'erreur/warning.
            lignes_err = [l for l in stderr_diag.splitlines()
                          if any(tok in l for tok in _OSMOSIS_INTERESSANT)]
            if lignes_err:
                print("  osmosis detail:")
                for _l in lignes_err[:20]:
                    print(f"    {_l}")
            else:
                # Pas de marqueur connu → afficher la queue brute
                print(f"  {stderr_diag.strip()[-600:]}")
        return None

def main():
    import argparse
    t_debut = time.time()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lidar2map.py
  python lidar2map.py --lidar --zone-city gareoult --download --shadings multi slope --file-formats mbtiles
  python lidar2map.py --lidar --zone-department 83 --download --shadings multi --file-formats mbtiles
  python lidar2map.py --osm --zone-city gareoult
        """
    )
    parser.add_argument("--version", action="version",
                        version="lidar2map 1.10.0 (2026-06) — multi-provider")
    parser.add_argument("--lidar", "--ignlidar", action="store_true", dest="ignlidar",
                        help="IGN LiDAR DEM mode")

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
    grp_priori.add_argument("--split-radius", "--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative: split into ~KM km squares.")
    grp_priori.add_argument("--cleanup", "--nettoyage", action="store_true", dest="nettoyage",
                            help="Delete intermediate tiles + TIFs after each chunk. "
                                 "Essential for large areas (a whole department).")
    grp_priori.add_argument("--min-free-gb", "--min-disque-go", type=float, default=0.0, metavar="GB",
                            dest="min_free_gb",
                            help="Stop cleanly before a chunk if free disk space drops below GB "
                                 "(0 = disabled). Set it ABOVE one chunk's peak footprint "
                                 "(intermediates + tile pyramid). Exits with code 3 so a shell "
                                 "loop can tell a resumable disk-stop from a real error.")

    # Localisation + zone
    _ajouter_args_zone(
        parser,
        rayon_default=None,
        bbox_metavar="X1,Y1,X2,Y2",
        bbox_help="Lambert 93 bbox in metres, e.g. 880000,6210000,1080000,6360000",
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
                        help="LiDAR provider (default: fr-ign). Available codes: "
                             "fr-ign, nl-ahn, ch-swisstopo, no-kartverket, us-3dep. "
                             "See providers/")
    parser.add_argument("--api-key", "--apikey", default="", metavar="KEY", dest="apikey",
                        help="Provider API key when required. For us-3dep: "
                             "https://portal.opentopography.org/myopentopo. "
                             "For IGN scan*: cartes.gouv.fr pro account (see --raster). "
                             "Can also be set via env IGN_APIKEY or "
                             "OPENTOPOGRAPHY_API_KEY depending on the provider.")
    parser.add_argument("--workers",  type=int,   default=NB_WORKERS, metavar="N",
                        help=f"Parallel connections (default: {NB_WORKERS})")
    parser.add_argument("--download-compress", "--telechargement-compresser", action="store_true",
                        dest="telechargement_compresser",
                        help="Compress cached tiles (DEFLATE, ~x5)")
    parser.add_argument("--download-force", "--telechargement-forcer", action="store_true",
                        dest="telechargement_forcer",
                        help="Re-download tiles already present")

    # Ombrages
    parser.add_argument("--shadings", "--ombrages", metavar="TYPE", nargs="+", dest="ombrages",
                        choices=["315", "045", "135", "225", "multi", "slope",
                                 "svf", "opos", "oneg", "lrm", "rrim", "tous", "aucun"],
                        help=(
                            "Shadings to generate (default: interactive). "
                            "Values: 315 045 135 225 multi slope svf opos oneg lrm rrim tous(all) aucun(none). "
                            "opos/oneg = openness positive/negative (Yokoyama 2002, rayon/gamma du SVF). "
                            "SVF is tuned via --svf-conv / --svf-dist / --svf-gamma / --svf-sweep. "
                            "svf/lrm/rrim: computed with numpy/scipy (scipy auto-installed). "
                            "Ex: --shadings multi slope svf rrim"
                        ))
    parser.add_argument("--shading", metavar="TYPE[:k=v,...]", action="append",
                        dest="shading_specs", default=None,
                        help=(
                            "Parameterized shading instance, repeatable. "
                            "Each occurrence yields ONE output with ITS params "
                            "(encoded in the filename, no collision): "
                            "--shading svf:dist=20,gamma=2 --shading svf:dist=100 "
                            "--shading oneg:dist=20,gamma=1.5 --shading 315:elevation=20 "
                            "--shading lrm:sigma=10. "
                            "Params: 315/045/135/225/multi=elevation ; "
                            "svf=conv,dist,gamma ; opos/oneg=dist,gamma ; "
                            "lrm/rrim=sigma(m) ; slope=none. "
                            "Unset params inherit --svf-* / --shading-elevation. "
                            "Combines with --shadings (a type listed in --shading "
                            "is not re-generated at default params)."
                        ))
    parser.add_argument("--shading-preset",
                        choices=["auto", "micro", "standard", "landscape"],
                        default=None, dest="shading_preset",
                        help=("Resolution-tuned shading stack (opt-in, params in "
                              "metres): adds svf + opos + lrm sized for the DEM "
                              "resolution, plus multi + slope. 'auto' picks micro "
                              "(<=0.75 m) / standard (~1 m) / landscape (>=5 m) from "
                              "the active provider. Off by default; when set it takes "
                              "precedence over --shadings default params."))
    parser.add_argument("--svf-conv", choices=["flux", "rvt"], default="flux",
                        dest="svf_conv",
                        help=("SVF convention: flux = cos²γ (compressed near 1, "
                              "contrast to the eye); rvt = 1−sin γ (Kokalj/Hesse, "
                              "archaeology standard/openness). Default: flux."))
    parser.add_argument("--svf-dist", type=float, default=20.0, metavar="M",
                        dest="svf_dist",
                        help=("SVF radius in metres (10–200). Default: 20 "
                              "(micro-relief). 100 = enclosures/roads."))
    parser.add_argument("--shading-elevation", "--ombrages-elevation", type=int, default=None, metavar="DEG",
                        dest="ombrages_elevation",
                        help=(f"Sun angle of directional hillshades in degrees "
                              f"(default: {ELEVATION_SOLEIL}°, archaeology optimal). "
                              f"General use: 45°. Archaeology: 20-30°."))
    parser.add_argument("--svf-gamma", type=float, default=None, metavar="G",
                        dest="svf_gamma",
                        help=(f"SVF gamma after percentile stretch (default: "
                              f"{SVF_GAMMA}). <1 lightens (√), 1 = linear, >1 "
                              f"darkens. Ex: --svf-gamma 0.7 for lighter."))

    # Mode non-interactif
    parser.add_argument("--download", "--telechargement", action="store_true", dest="telechargement",
                        help="Download missing IGN tiles.")
    parser.add_argument("--tiles-purge-invalid", "--dalles-purger-invalides", action="store_true",
                        dest="dalles_purger_invalides",
                        help="Delete cache tiles < 2 MB (sea tiles, partial errors). "
                             "Omit --download to purge without re-downloading.")
    parser.add_argument("--tiles-migrate", "--dalles-migrer", action="store_true", dest="dalles_migrer",
                        help="Reorganise existing tiles into per-column-X subfolders "
                             "(e.g. D:/Lidar/Dalles/0958/LHD_FXX_0958_....tif). "
                             "Run once to migrate the old flat structure.")
    parser.add_argument("--tiles-rename", "--dalles-renommer", action="store_true", dest="dalles_renommer",
                        help="Rename tiles from the old convention (x2, e.g. 0456_3107) "
                             "to the new one (x1, e.g. 0912_6214). Run once.")
    parser.add_argument("--tiles-purge-out-of-zone", "--dalles-purger-hors-zone", action="store_true",
                        dest="dalles_purger_hors_zone",
                        help="Delete from cache the tiles outside the current zone (bbox/department). "
                             "Useful to free space taken by tiles of other departments. "
                             "Requires --zone-department, --zone-bbox, --zone-city or --zone-gps.")
    parser.add_argument("--shadings-compress", "--ombrages-compresser",  action="store_true",
                        dest="ombrages_compresser", help="Compress existing raw shadings (DEFLATE)")
    parser.add_argument("--download-overwrite", "--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Overwrite existing downloaded tiles")
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
                        choices=["mbtiles","rmap","sqlitedb","map","gz","geojson"],
                        default=[], metavar="FMT",
                        help="Output file formats: mbtiles rmap sqlitedb (multi-value).")
    parser.add_argument("--source", metavar="PATH", default=None,
                        help="Existing source file (standalone mode, no zone required). "
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

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal
    _valider_zooms(args, parser)

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
        print(f"  Preset ombrages '{_pname}' (res {RESOLUTION_M:g} m) : "
              f"svf/opos rayon {_pd:g} m, lrm sigma {_ps:g} m, soleil "
              f"{args.ombrages_elevation}°")

    # Propage --apikey au provider actif s'il en utilise une (us-3dep, etc.).
    if hasattr(PROVIDER, "set_apikey"):
        PROVIDER.set_apikey(args.apikey)

    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    # Si le pipeline crashe, l'entrée reste → diagnostic facile.
    _historique_debut()

    _osm_seul = args.osm and not args.telechargement and not args.ombrages and not args.mbtiles

    print("=" * 55)
    if _osm_seul:
        print("  Carte OSM vectorielle")
    else:
        print(f"  LiDAR : {PROVIDER.NAME}")
        print("  Pipeline rasterio + numpy (numba for SVF)")
    print("=" * 55)
    print(f"  Dossier : {args.dossier or str(DOSSIER_TRAVAIL / LIDAR_SUBDIR)}")
    print()

    # ── --source : mode autonome selon l'extension + CRS ────────────────────────
    # .mbtiles → RMAP (requiert --rmap, exit immédiat)
    # .pbf     → OSM  (requiert --osm, injecté dans args.source pour usage ultérieur)
    # .tif     → MBTiles/RMAP (CRS auto-détecté : 3857=tuilage direct, autre=warp)
    #            nécessite une zone pour la bbox → pas d'exit immédiat
    if args.source:
        src_path = Path(args.source)
        if not src_path.exists():
            ext_src = Path(args.source).suffix.lower()
            if ext_src in (".tif", ".tiff"):
                # TIF cache absent (warped removed) → ignorer, on recalcule depuis les dalles
                print(f"  WARNING: source TIF not found : {Path(args.source).name}")
                print(f"  Recompute from tiles...")
                args.source = None
            else:
                print(f"  ERROR: source file not found: {args.source}")
                sys.exit(1)
        ext = Path(args.source).suffix.lower() if args.source else ""

        if ext == ".mbtiles":
            # Conversion directe MBTiles → RMAP/SQLiteDB (exit immédiat, pas de zone requise)
            if not args.rmap and not args.sqlitedb:
                print("  ERROR: --rmap or --sqlitedb required for MBTiles conversion.")
                print(f"  Ex: --source {src_path.name} --rmap")
                sys.exit(1)
            if args.rmap:
                generer_rmap_depuis_mbtiles(src_path, ecraser=args.tuiles_ecraser)
            if args.sqlitedb:
                generer_sqlitedb_depuis_mbtiles(src_path, ecraser=args.tuiles_ecraser)
            sys.exit(0)

        elif ext in (".pbf", ".osm"):
            # Source OSM : traitée plus loin dans la section --osm
            if not args.osm:
                print("  ERROR: --osm required with a .pbf source.")
                print(f"  E.g.: --source {src_path.name} --zone-city gareoult --osm")
                sys.exit(1)
            # args.source est déjà défini, sera lu dans la section OSM

        elif ext in (".tif", ".tiff"):
            # Source TIF : détection CRS via rasterio
            try:
                import rasterio as _rio_src
                with _rio_src.open(str(src_path)) as _ds_src:
                    _epsg = _ds_src.crs.to_epsg() if _ds_src.crs else None
                if _epsg == 3857:
                    # Déjà en Mercator → tuilage direct, warp inutile
                    args._source_already_warped = True
                    print(f"  Source TIF EPSG:3857 detected -> direct tiling (no warp)")
                else:
                    args._source_already_warped = False
                    print(f"  Source TIF EPSG:{_epsg} -> L93->Mercator warp required")
            except Exception as _e_crs:
                print(f"  WARNING CRS not detected ({_e_crs}) — warp applied by default")
                args._source_already_warped = False
        else:
            print(f"  ERROR: unrecognised extension for --source: {ext}")
            print("  Accepted extensions: .tif .tiff .mbtiles .pbf")
            sys.exit(1)

    # -------------------------------------------------------
    # Sélection de zone → liste de dalles
    # -------------------------------------------------------
    # Si --dalles-migrer sans aucune info de zone : pas besoin de géocodage
    _migrer_seul = (getattr(args, 'dalles_migrer', False) and
                    not args.telechargement and not args.ombrages and
                    not args.mbtiles)

    # --source .tif nécessite une zone pour la bbox
    _source_tif_sans_zone = (
        args.source and Path(args.source).suffix.lower() in (".tif", ".tiff") and
        not args.zone_departement and not args.zone_bbox and
        not args.zone_ville and not args.zone_gps and
        not getattr(args, "zone_region", None))
    if _source_tif_sans_zone:
        print("  ERROR: --source TIF requires a zone: --zone-city/--zone-radius, --zone-bbox, --zone-department or --zone-region")
        sys.exit(1)
    if _migrer_seul and not args.zone_departement and not args.zone_bbox and not args.zone_ville and not args.zone_gps and not getattr(args, "zone_region", None):
        # Mode migration pure : on n'a besoin que de dossier_dalles
        racine        = Path(args.dossier).resolve() if args.dossier else Path(str(DOSSIER_TRAVAIL / LIDAR_SUBDIR))
        dossier_dalles = Path(args.dossier_dalles).resolve() if args.dossier_dalles else DOSSIER_TRAVAIL / "cache" / LIDAR_SUBDIR
        dossier_dalles.mkdir(parents=True, exist_ok=True)
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]
        if not a_migrer:
            print("  No tile to migrate (root folder already empty or structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} tile(s) -> subfolders by column X...")
            migres = erreurs = 0
            for f in sorted(a_migrer):
                m2 = re.match(r"LHD_FXX_(\d+)_", f.name)
                if not m2:
                    continue
                dest_dir = dossier_dalles / m2.group(1)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f.name
                if dest.exists():
                    f.unlink()
                else:
                    for _t in range(5):
                        try:
                            f.replace(dest)
                            break
                        except PermissionError:
                            time.sleep(0.2)
                    else:
                        erreurs += 1
                        continue
                migres += 1
                if migres % 500 == 0:
                    pct_mig = migres * 100 // max(len(a_migrer), 1)
                    print(f"\r  Migration : {pct_mig:3d}%  {migres}/{len(a_migrer)}...",
                          end="", flush=True)
            print(f"\r  Migration done: {migres} tiles moved, {erreurs} errors.")
        sys.exit(0)

    cx = cy = 0.0
    dalles = []
    if getattr(args, "zone_region", None):
        slug = args.zone_region.strip().lower()
        # Nom automatique : le slug région ex "provence_alpes_cote_d_azur"
        nom_auto = normaliser_nom(slug)
        nom_zone  = normaliser_nom(args.zone_nom) if args.zone_nom else nom_auto
        if _osm_seul:
            # OSM-seul : le PBF Geofabrik EST déjà la région — on le traite en
            # entier (skip_bbox). Inutile de géocoder ses 6 départements pour une
            # bbox de découpe dont on ne se sert pas → zéro appel Overpass.
            # La section OSM utilisera une bbox "monde" ; ce sentinel n'est jamais lu.
            if slug not in _regions_disponibles():
                print(f"  ERROR: region '{slug}' unknown.")
                print(f"  Available regions: {', '.join(_regions_disponibles())}")
                sys.exit(1)
            dalles, bbox = [], (0.0, 0.0, 0.0, 0.0)
            print(f"  Dossier : {nom_zone}")
        else:
            # raster / vecteur / lidar : bbox = union des bbox des départements.
            nom_reg, bx1, by1, bx2, by2 = geocoder_region(slug)
            if nom_reg is None:
                sys.exit(1)
            dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
            print(f"  Dossier : {nom_zone}  |  {len(dalles)} dalles")

    elif args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        if _osm_seul:
            dalles, bbox = [], (bx1, by1, bx2, by2)
        else:
            dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
        # Nom automatique : ex "var_83"
        nom_auto = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        nom_zone  = normaliser_nom(args.zone_nom) if args.zone_nom else nom_auto
        print(f"  Dossier : {nom_zone}" + ("" if _osm_seul else f"  |  {len(dalles)} dalles"))

    elif args.zone_bbox:
        try:
            parts = [float(v.strip()) for v in args.zone_bbox.split(",")]
            bx1, by1, bx2, by2 = parts
        except (ValueError, IndexError):
            print("  Format BBox invalide. Exemple : --bbox 880000,6210000,1080000,6360000")
            sys.exit(1)
        if _osm_seul:
            dalles, bbox = [], (bx1, by1, bx2, by2)
        else:
            dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
        surface_km2 = (bx2-bx1)/1000 * (by2-by1)/1000
        print(f"  BBox {PROVIDER.CRS_NATIF} : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Area: ~{surface_km2:.0f} km²" + ("" if _osm_seul else f"  |  {len(dalles)} dalles"))
        if args.zone_nom:
            nom_zone = normaliser_nom(args.zone_nom)
        elif args.oui:
            print("  ERROR: --zone-name required with --zone-bbox when non-interactive (no terminal)")
            sys.exit(1)
        else:
            nom_zone = normaliser_nom(input("  Nom du dossier de sortie : ").strip())
        if not nom_zone:
            sys.exit(1)

    elif args.zone_gps:
        try:
            parts = [p.strip() for p in args.zone_gps.replace(";", ",").split(",")]
            lat, lon = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            print("  Format GPS invalide. Exemple : 43.3156,6.0423")
            sys.exit(1)
        if args.zone_nom:
            nom_zone = normaliser_nom(args.zone_nom)
        elif args.oui:
            print("  ERROR: --zone-name required with --zone-gps when non-interactive (no terminal)")
            sys.exit(1)
        else:
            nom_zone = normaliser_nom(input("  Nom du dossier de sortie : ").strip())
        if not nom_zone:
            sys.exit(1)
        # BUGFIX : la conversion GPS→L93 doit se faire dans TOUS les cas, pas
        # uniquement quand --telechargement est absent. Sans cela, cx=cy=0.0
        # (init ligne 5056) et la grille calculée par calculer_grille() est
        # centrée sur l'origine Lambert 93 (au large du Maroc), produisant
        # une bbox Mercator vide et un MBTiles à 0 tuiles.
        print(f"  GPS -> lat={lat:.5f}, lon={lon:.5f}")
        try:
            t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
            cx, cy = t.transform(lon, lat)
        except ImportError:
            cx, cy = wgs84_to_lamb93_approx(lon, lat)
            print("  (pyproj absent, conversion approchee)")
        print(f"  {PROVIDER.CRS_NATIF} -> X={cx:.0f}, Y={cy:.0f}")

    elif args.zone_ville:
        nom_zone = normaliser_nom(args.zone_nom or args.zone_ville)
        print(f"  Geocodage de '{args.zone_ville}'...")
        cx, cy = geocoder_ville_l93(args.zone_ville)
        if cx is None:
            sys.exit(1)

    else:
        # Mode interactif
        print("  Mode de saisie :")
        print("  [1] Nom de ville")
        print("  [2] GPS coordinates (lat, lon)")
        mode = input("  Choix [1] : ").strip() or "1"
        if mode == "2":
            gps = input("  GPS (ex: 43.3156, 6.0423) : ").strip()
            try:
                parts = [p.strip() for p in gps.replace(";", ",").split(",")]
                lat, lon = float(parts[0]), float(parts[1])
            except (ValueError, IndexError):
                print("  Format invalide.")
                sys.exit(1)
            nom_zone = normaliser_nom(input("  Nom du dossier de sortie : ").strip())
            if not nom_zone: sys.exit(1)
            # BUGFIX : conversion GPS→L93 dans tous les cas (cf. fix ci-dessus)
            print(f"  GPS -> lat={lat:.5f}, lon={lon:.5f}")
            try:
                t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
                cx, cy = t.transform(lon, lat)
            except ImportError:
                cx, cy = wgs84_to_lamb93_approx(lon, lat)
                print("  (pyproj absent, conversion approchee)")
            print(f"  {PROVIDER.CRS_NATIF} -> X={cx:.0f}, Y={cy:.0f}")
        else:
            ville_saisie = input("  Nom de la ville : ").strip()
            if not ville_saisie:
                sys.exit(1)
            nom_zone = normaliser_nom(args.zone_nom or ville_saisie)
            # BUGFIX : geocodage ville→L93 dans tous les cas (cf. fix ci-dessus)
            print(f"\n  Geocodage de '{ville_saisie}'...")
            cx, cy = geocoder_ville_l93(ville_saisie)
            if cx is None:
                sys.exit(1)

    # Rayon + grille (modes ville / gps / interactif — pas bbox, dept, région, france)
    if not args.zone_bbox and not args.zone_departement and not getattr(args, "zone_region", None):
        if args.zone_rayon:
            rayon = args.zone_rayon
        else:
            rayon_str = input("  Rayon en km [10] : ").strip()
            try:
                rayon = float(rayon_str) if rayon_str else 10.0
            except ValueError:
                rayon = 10.0
        dalles, bbox = calculer_grille(cx, cy, rayon)

    # ── A-priori splitting: traitement séquentiel morceau par morceau ────────
    _cols_pr  = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr  = getattr(args, "rows_decoupe", 0) or 0
    _rayon_pr = getattr(args, "rayon_decoupe", 0.0) or 0.0
    if ((_cols_pr > 0 and _rows_pr > 0) or _rayon_pr > 0) and not _osm_seul:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            bbox[0], bbox[1], bbox[2], bbox[3],
            0, _rayon_pr, unite_m=True, n_cols=_cols_pr, n_rows=_rows_pr)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR)
            manifeste = Manifeste(racine_pr / nom_zone / "manifeste.json")
            n_total   = len(sous_zones)
            nb_done   = sum(1 for z in sous_zones
                            if manifeste.deja_traite(f"{z[0]+1:03d}x{z[1]+1:03d}"))
            print(f"\n  ══ A-priori splitting: {mode_desc} ══")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Resume: {nb_done}/{n_total} chunks already done")

            nb_ok = 0
            for i_z, (i_lat, i_lon, bx1_z, by1_z, bx2_z, by2_z) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} — already done")
                    nb_ok += 1
                    continue

                _garde_disque(racine_pr, getattr(args, "min_free_gb", 0.0) or 0.0,
                              cle, nb_ok, n_total)

                surface = (bx2_z-bx1_z)/1000 * (by2_z-by1_z)/1000
                print(f"\n  ── Chunk {cle}  ({i_z+1}/{n_total})  {nom_z} ──")
                print(f"     BBox L93 : {bx1_z:.0f},{by1_z:.0f} → "
                      f"{bx2_z:.0f},{by2_z:.0f}  (~{surface:.0f} km²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_lidar(args, (bx1_z, by1_z, bx2_z, by2_z),
                                        nom_z, nom_zone, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] ✓ Done in {_hms(int(time.time() - t0_z))}")
                    _n_done, _eta = manifeste.eta_global(n_total)
                    if _eta:
                        print(f"  [{cle}] {_n_done}/{n_total} done — "
                              f"ETA ~{_hms(_eta)} remaining (coarse)")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        # Si le chunk a produit un mbtiles vide OU aucun mbtiles
                        # (chunk en mer hors couverture IGN, ou bug à diagnostiquer),
                        # on conserve les .tif intermédiaires pour permettre
                        # l'inspection — sinon l'utilisateur perd le contexte.
                        _dossier_chunk = (
                            (Path(args.dossier).resolve() if args.dossier
                             else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR)
                            / nom_z)
                        _mbts = list(_dossier_chunk.glob("*.mbtiles"))
                        _has_empty = (not _mbts) or any(
                            not _mbtiles_est_complete(mbt) for mbt in _mbts)
                        if _has_empty:
                            print(f"  [{cle}] mbtiles empty or missing - cleanup skipped (intermediates kept for inspection)")
                        else:
                            _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] ✗ ERROR: {_e_z} - relaunch to resume")
                    raise

            elapsed = int(time.time() - t_debut)
            print(f"\n  ══ A-priori splitting done: {nb_ok}/{n_total} chunks ==")
            print(f"  Total time: {_hms(elapsed)}")
            return
        print("  A-priori splitting: zone too small -> single pass")

    nb = len(dalles)
    octets_par_dalle = (PX_PAR_DALLE * PX_PAR_DALLE * 4) + 513
    taille_brut = nb * octets_par_dalle // (1024 * 1024)
    taille_comp = taille_brut // 5

    etapes_total = sum([bool(args.telechargement),
                        bool(args.ombrages),
                        bool(args.mbtiles),
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
        print("ETAPE:" + str(etape_cur[0]) + "/" + str(etapes_total) + " " + nom, flush=True)

    if args.telechargement:
        print_etape("Téléchargement dalles")
    if not _osm_seul and not (not args.telechargement and not args.ombrages):
        print(f"\n  Grid: {nb} tile(s) of {DALLE_KM}x{DALLE_KM} km  (~{nb} km²)")
        print(f"  Space: ~{taille_brut} MB raw  /  ~{taille_comp} MB compressed")
    if args.telechargement_forcer:
        print(f"  Update: existing tiles re-downloaded")
    if args.workers != NB_WORKERS:
        print(f"  Workers : {args.workers}")

    # Compression
    if args.telechargement_compresser:
        compresser = True
    elif args.oui or not args.telechargement:
        compresser = False  # pas de compression si téléchargement non demandé
    else:
        print(f"\n  Cache compression:")
        print(f"  [1] No  -> fast,  ~{taille_brut} Mo")
        print(f"  [2] Oui  -> lent,    ~{taille_comp} Mo")
        compresser = (input("  Choix [1] : ").strip() or "1") == "2"
    if args.telechargement:
        print(f"  -> {'Compression enabled' if compresser else 'Raw storage'}")

    if not args.oui and args.telechargement:
        if input(f"\n  Lancer le téléchargement ? [O/n] : ").strip().lower() == "n":
            sys.exit(0)

    racine        = Path(args.dossier).resolve() if args.dossier else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR
    dossier_dalles = Path(args.dossier_dalles).resolve() if args.dossier_dalles else DOSSIER_TRAVAIL / "cache" / LIDAR_SUBDIR
    dossier_ville  = racine
    _sans_telechargement = not getattr(args, "telechargement", False)
    _sans_ombrages = not getattr(args, "ombrages", None)
    if not _osm_seul and not (_sans_telechargement and _sans_ombrages):
        try:
            dossier_dalles.mkdir(parents=True, exist_ok=True)
        except (FileNotFoundError, OSError) as _e_dd:
            print(f"  ERROR: tiles folder inaccessible: {dossier_dalles}")
            print(f"  ({_e_dd})")
            print(f"  Check that the disk is connected and relaunch.")
            sys.exit(1)
    if not _osm_seul:
        dossier_ville.mkdir(parents=True, exist_ok=True)
    print(f"\n  Racine  : {racine}")
    if not _osm_seul:
        print(f"  Dalles  : {dossier_dalles}")
        print(f"  Zone    : {dossier_ville}")

    # -------------------------------------------------------
    # Renommage dalles ancienne convention → nouvelle
    # -------------------------------------------------------
    if getattr(args, 'renommer_dalles', False) and dossier_dalles.exists():
        renommes = 0; ignores = 0
        tous = _rglob_tif_robuste(dossier_dalles)
        print(f"  {len(tous)} .tif files found in {dossier_dalles}")
        if tous:
            print(f"  Exemple : {tous[0].name}")
        for f in sorted(tous):
            m = re.match(
                r'LHD_FXX_(\d+)_(\d+)_(MNT_O_0M50_LAMB93.*)', f.name)
            if not m:
                continue
            x_old, y_old = int(m.group(1)), int(m.group(2))
            reste = m.group(3)
            # Détecter l'ancienne convention : x_old < 600 (max Lambert93/2000≈600)
            # Dans la nouvelle convention x_old > 600 (coordonnées km réelles)
            if x_old >= 600:
                ignores += 1
                continue
            x_new = x_old * 2
            y_new = y_old * 2
            nouveau = f.parent / f"LHD_FXX_{x_new:04d}_{y_new:04d}_{reste}"
            if not nouveau.exists():
                f.replace(nouveau)
                renommes += 1
            else:
                f.unlink()  # doublon
                renommes += 1
        print(f"  Renaming: {renommes} tiles renamed, {ignores} skipped")

    # -------------------------------------------------------
    # Migration dalles à plat → sous-dossiers par colonne X
    # -------------------------------------------------------
    if getattr(args, 'migrer_dalles', False) and dossier_dalles.exists():
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]  # uniquement racine
        if not a_migrer:
            print("  No tile to migrate (root folder already empty or structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} tile(s) -> subfolders by column X...")
            migres = erreurs = 0
            for f in sorted(a_migrer):
                m = re.match(r"LHD_FXX_(\d+)_", f.name)
                if not m:
                    continue
                dest_dir = dossier_dalles / m.group(1)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f.name
                if dest.exists():
                    f.unlink()
                else:
                    for _tentative in range(5):
                        try:
                            f.replace(dest)
                            break
                        except PermissionError:
                            time.sleep(0.2)  # attendre que l'AV relâche
                        except Exception:
                            erreurs += 1
                            break
                    else:
                        erreurs += 1
                        continue
                migres += 1
                if migres % 500 == 0:
                    pct_mig = migres * 100 // max(len(a_migrer), 1)
                    print(f"\r  Migration : {pct_mig:3d}%  {migres}/{len(a_migrer)}...",
                          end="", flush=True)
            print(f"  Migration done: {migres} tiles moved, {erreurs} errors.")

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
                  f" ({len(noms_zone_purge)} dalles zone)")
        else:
            print(f"  ERROR out-of-zone purge: {dalles_zone_txt.name} not found.")
            print(f"  Relaunch with --download to rebuild the list.")
            sys.exit(1)
        toutes = _rglob_tif_robuste(dossier_dalles)
        hors_zone = [f for f in toutes if f.name not in noms_zone_purge]
        if hors_zone:
            taille_go = sum(f.stat().st_size for f in hors_zone) / 1e9
            print(f"\n  Out-of-zone purge: {len(hors_zone)} tile(s) - {taille_go:.1f} Go")
            if not args.oui:
                rep = input("  Confirmer la suppression ? [o/N] : ").strip().lower()
                if rep != "o":
                    print("  Purge cancelled.")
                    hors_zone = []
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
        _lon1, _lat1 = _t_wgs.transform(bbox[0], bbox[1])
        _lon2, _lat2 = _t_wgs.transform(bbox[2], bbox[3])
        bbox_wgs = (min(_lon1, _lon2) - 0.05, min(_lat1, _lat2) - 0.05,
                    max(_lon1, _lon2) + 0.05, max(_lat1, _lat2) + 0.05)
        # Cache per-provider : schemas incompatibles (TMS dict vs GeoJSON, etc.).
        cache_discover = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
        # discover_dalles : None = échec réseau/endpoint, {} = pas de couverture.
        # On distingue les deux (sinon une panne de portail ressemble à "rien
        # ici") et on protège l'appel : un provider qui lève ne doit pas casser
        # tout le run, juste signaler la zone comme indisponible.
        try:
            _d = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover)
            if _d is None:
                print("  ⚠ Découverte des dalles indisponible (réseau/endpoint),"
                      " zone ignorée, réessayez.", flush=True)
        except Exception as _e_disc:
            print(f"  ⚠ Découverte des dalles échouée ({type(_e_disc).__name__}:"
                  f" {_e_disc}), zone ignorée, réessayez.", flush=True)
            _d = None
        dalles_dict = _d or {}
        noms_attendus = set(dalles_dict.keys())

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
                print("\n  WARNING: --download missing but no tile found.")
                print(f"  Dossier dalles : {dossier_dalles}")
                print("  Add --download to fetch the missing tiles.")
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
                    print(f"\n  ATTENTION : {len(dalles_existantes)} tile(s) in cache,")
                    print(f"              but NONE covers the requested zone.")
                    print(f"  Cache global : {dossier_dalles}")
                    libelle_zone = args.zone_ville or nom_zone
                    print(f"  Requested zone: {len(noms_attendus)} tile(s) around "
                          f"{libelle_zone}")
                    print(f"  Add --download to fetch the missing tiles.")
                    sys.exit(1)
                print(f"\n  Download skipped "
                      f"({len(dalles_zone_cache)}/{len(noms_attendus)} dalle(s) de la zone trouvées en cache)")
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
    TOUS_OMBRAGES = ["315", "045", "135", "225", "multi", "slope",
                     "svf", "opos", "oneg", "lrm", "rrim"]

    # Dalles disponibles pour les ombrages :
    # 1. Seulement les dalles de la zone courante (filtre par nom)
    # 2. Seulement les fichiers valides (≥ 50 MB)
    # Le dossier dalles est global — sans filtrage par zone, le VRT couvrirait
    # tous les départements présents et le hillshade serait énorme ou en erreur.
    if dossier_dalles.exists():
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        noms_zone = set()  # initialisé ici — peut rester vide en mode OSM seul
        if dalles_zone_txt.exists():
            # Vérifier que la bbox en entête correspond à la zone courante
            _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
            _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
            _bbox_fichier  = _lignes[0].strip() if _lignes else ""
            if _bbox_fichier != _bbox_courante:
                print(f"  Zone changed - rebuilding {dalles_zone_txt.name} from cache...")
                print(f"    Ancienne bbox : {_bbox_fichier}")
                print(f"    Nouvelle bbox : {_bbox_courante}")
                # Reconstruire depuis le cache disque sans retélécharger.
                # noms_attendus vient de PROVIDER.discover_dalles (provider-agnostique).
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_attendus and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    dalles_zone_txt.write_text(
                        _bbox_courante + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  {dalles_zone_txt.name} rebuilt: {len(noms_zone)} tile(s) in cache")
                else:
                    dalles_zone_txt.unlink(missing_ok=True)
                    print(f"  No tile in cache for this zone - use --download")
                    noms_zone = set()
            else:
                noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
                print(f"  Zone tiles list: {dalles_zone_txt.name} ({len(noms_zone)} dalles)")
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
                    _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
                    dalles_zone_txt.write_text(
                        _bbox_hdr + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  dalles_zone.txt rebuilt: {len(noms_zone)} tile(s) found on disk")
                else:
                    print(f"  ERROR: no tile of the zone found in {dossier_dalles}")
                    print(f"  Relaunch with --download to fetch the tiles.")
                    sys.exit(1)
        else:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # mode OSM seul — pas besoin de dalles
            else:
                print(f"\n  ERROR: {dalles_zone_txt.name} not found in {dossier_ville}/")
                print(f"  This file is created automatically during download.")
                print(f"  Relaunch with --download to rebuild it.")
                print(f"  (Tiles already present on disk will be skipped, ~a few seconds)")
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
            print("  ERROR: rasterio absent — pip install rasterio")
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
                    chemin_tmp  = chemin_out.with_suffix(".tmp.tif")
                    chemin_out.replace(chemin_tmp)
                    t0_cmp = time.time()
                    try:
                        with _rio_cmp.open(str(chemin_tmp)) as src:
                            profile = src.profile.copy()
                            profile.update({
                                "compress":   "deflate",
                                "predictor":  2,
                                "tiled":      True,
                                "blockxsize": 512,
                                "blockysize": 512,
                                "BIGTIFF":    "IF_SAFER",
                            })
                            with _rio_cmp.open(str(chemin_out), "w", **profile) as dst:
                                # Copier bande par bande avec windowed reads
                                # pour borner la RAM (un ombrage 50000×50000 px
                                # uint8 = 2.5 Go en mémoire — trop gros).
                                for ji, window in src.block_windows(1):
                                    for b in range(1, src.count + 1):
                                        dst.write(src.read(b, window=window),
                                                  b, window=window)
                        elap = time.time() - t0_cmp
                        chemin_tmp.unlink(missing_ok=True)
                        taille_cmp = chemin_out.stat().st_size / 1e6
                        gain = int((1 - taille_cmp / taille_brut) * 100)
                        print("  " + chemin_out.name.ljust(56) +
                              str(round(taille_brut)).rjust(6) + " MB -> " +
                              str(round(taille_cmp)).rjust(5) + " MB  (-" +
                              str(gain) + "%)  " + _hms(elap))
                    except Exception as _e_cmp:
                        print(f"  ERREUR compression {chemin_out.name} : {_e_cmp}")
                        chemin_tmp.replace(chemin_out)

    spec_insts = getattr(args, "shading_instances", None) or []
    if dalles_ombrages and args.ombrages:
        if "aucun" in args.ombrages:
            choix_ombrages = []
            spec_insts = []
        elif "tous" in args.ombrages:
            choix_ombrages = TOUS_OMBRAGES
        else:
            choix_ombrages = args.ombrages
        # Types couverts par une instance --shading explicite : ne pas les
        # re-générer aux params par défaut (l'instance porte SES params).
        if spec_insts:
            _spec_types = {t for t, _ in spec_insts}
            choix_ombrages = [c for c in choix_ombrages if c not in _spec_types]
    elif dalles_ombrages and not args.ombrages and not args.oui:
        # Mode interactif — pas de --ombrages, pas de
        print(f"\n  Shadings to generate:")
        print(f"  [1] Rapide      : multi + slope                                   (~1 min)")
        print(f"  [2] Archaeo     : 315 + 045 + multi + slope                       (~2 min)")
        print(f"  [3] VAT (archéo, recommandé) : SVF + openness + slope, 1 image    (~20 min)")
        print(f"  [4] Archaeo+SVF : multi + slope + SVF (flux 20m)                   (~20 min)")
        print(f"  [5] Archaeo+LRM : multi + slope + LRM gaussien                     (~8 min)")
        print(f"  [6] Archaeo+RRIM: multi + slope + RRIM (colour composite)         (~25 min)")
        print(f"  [7] Complet     : 315 045 135 225 multi slope svf lrm rrim        (~60 min)")
        print(f"  [8] None")
        print(f"  [9] Choix manuel  ex: multi slope svf rrim vat")
        print(f"  SVF/openness/LRM/RRIM/VAT : numpy/scipy/numba (auto-installés si besoin)")
        rep = input("  Choix [1] : ").strip() or "1"
        if   rep == "1": choix_ombrages = ["multi", "slope"]
        elif rep == "2": choix_ombrages = ["315", "045", "multi", "slope"]
        elif rep == "3": choix_ombrages = ["vat"]
        elif rep == "4": choix_ombrages = ["multi", "slope", "svf"]
        elif rep == "5": choix_ombrages = ["multi", "slope", "lrm"]
        elif rep == "6": choix_ombrages = ["multi", "slope", "rrim"]
        elif rep == "7": choix_ombrages = TOUS_OMBRAGES
        elif rep == "8": choix_ombrages = []
        elif rep == "9":
            saisie = input("  Types : ").strip().lower().split()
            choix_ombrages = [s for s in saisie if s in _SHADING_TYPES]
        else:             choix_ombrages = ["multi", "slope"]
    else:
        choix_ombrages = []  # sans --ombrages → pas d'ombrage

    if choix_ombrages or spec_insts:
        surface_km2 = len(dalles_ombrages)  # ~1 dalle = 1 km²
        _libelles = choix_ombrages + [
            t + (":" + ",".join(f"{k}={v:g}" if isinstance(v, float) else f"{k}={v}"
                                for k, v in p.items()) if p else "")
            for t, p in spec_insts]
        print_etape("Ombrages " + ", ".join(_libelles))
        print(f"  Ombrages : {', '.join(_libelles)}")
        elev = args.ombrages_elevation if args.ombrages_elevation is not None else ELEVATION_SOLEIL
        print(f"  Angle solaire : {elev}°")
        print(f"  Area: ~{surface_km2} km²  — Estimated duration:"
              f" {'5-10 min' if surface_km2 < 100 else '15-45 min' if surface_km2 < 500 else '1h+'}"
              f" (selon le type d'ombrage et la machine)", flush=True)
        generer_ombrages(dalles_ombrages, dossier_ville, choix_ombrages,
                         elevation_soleil=elev, nom_zone=nom_zone,
                         ecraser_ombrages=args.ombrages_ecraser,
                         use_sweep=args.sweep_horizon,
                         svf_gamma=args.svf_gamma,
                         svf_conv=args.svf_conv, svf_dist=args.svf_dist,
                         bbox_natif=tuple(bbox),
                         instances=spec_insts or None)

    # ── MBTiles + RMAP ─────────────────────────────────────────────────────────
    if args.mbtiles or args.rmap or args.sqlitedb:
        # Source : --source .tif ou ombrages générés dans dossier_ville
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff"):
            # --source explicite
            _tif_src = Path(args.source).resolve()
            print_etape(f"{'RMAP' if args.rmap and not args.mbtiles else 'MBTiles'} depuis {_tif_src.name}")
            print(f"  Source : {_tif_src}")
            print(f"  Zone   : bbox L93 {bbox[0]:.0f},{bbox[1]:.0f} → {bbox[2]:.0f},{bbox[3]:.0f}")
            # Nom basé sur nom_zone + type d'ombrage détecté dans le nom du fichier
            _SUFFIXES = {
                "multi_ombrage": "multi_ombrage",
                "315_ombrage":  "315_ombrage",
                "045_ombrage":  "045_ombrage",
                "135_ombrage":  "135_ombrage",
                "225_ombrage":  "225_ombrage",
                "slope_ombrage":   "slope_ombrage",
                "svf_ombrage":     "svf_ombrage",
                "svf_100m_ombrage":"svf_100m_ombrage",
                "lrm_ombrage":     "lrm_ombrage",
                "rrim_ombrage":    "rrim_ombrage",
            }
            _sfx = next((v for k, v in _SUFFIXES.items() if k in _tif_src.stem), _tif_src.stem)
            _nom_base = f"{nom_zone}_{_sfx}"   # sans zoom — ajouté par generer_mbtiles_lidar
            _nom_mbt  = f"{_nom_base}_z{args.zoom_min}-{args.zoom_max}"
            # Générer MBTiles si demandé explicitement, ou si nécessaire pour RMAP/SQLiteDB
            _mbt_path = dossier_ville / f"{_nom_mbt}.mbtiles"
            _ecraser_l = args.tuiles_ecraser
            _mbt_requis = _mbtiles_a_regenerer(_mbt_path, _ecraser_l)
            _mbt_out = None
            if _mbt_requis:
                _mbt_out = generer_mbtiles_lidar(_tif_src, dossier_ville, _nom_base,
                                           zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                                           format_tuiles=args.formats_image,
                                           jpeg_quality=args.qualite_image,
                                           bbox_l93=bbox,
                                           source_already_warped=getattr(args, "_source_already_warped", False),
                                           ecraser_tuiles=_ecraser_l,
                                           tile_workers=args.workers)
            elif _mbt_path.exists():
                print(f"  Existing MBTiles: {_mbt_path.name} — direct split/conversion")
                _mbt_out = _mbt_path
            _convertir_formats(_mbt_out, args, mbtiles_neuf=_mbt_requis)
        else:
            # Ombrages présents dans dossier_ville
            # Exclure les fichiers de cache de tuilage (`<nom>_tuilage_z<N>.tif`)
            # qui sont produits par generer_mbtiles_lidar comme cache du warp
            # rasterio. Sans ce filtre, le loop suivant tente de régénérer un
            # MBTiles à partir du cache, qui devient sa propre source — boucle
            # infinie en pratique (test_refactor_svf_ombrage_tuilage_z16_tuilage_z16.tif…).
            ombrages_tifs = [
                t for t in sorted(dossier_ville.glob("*.tif"))
                if not t.name.startswith("_")
                and not re.search(r'_tuilage_z\d+\.tif$', t.name)
            ]
            if ombrages_tifs:
                print_etape("MBTiles")
                _LABELS = {
                    "hillshade_315": "Hillshade 315°",
                    "hillshade_045": "Hillshade 045°",
                    "hillshade_135": "Hillshade 135°",
                    "hillshade_225": "Hillshade 225°",
                    "hillshade_multi": "Hillshade multi",
                    "slope":          "Pente",
                    "svf":            "SVF",
                    "svf_100m":       "SVF 100m",
                    "lrm":            "LRM",
                    "rrim":           "RRIM",
                }
                for tif in sorted(ombrages_tifs):
                    print("  " + tif.name)
                    stem = tif.stem
                    # Retirer le suffixe de cache _tuilage_z* si présent
                    stem = re.sub(r'_tuilage_z\d+$', '', stem)
                    suffix = stem[len(nom_zone) + 1:] if stem.startswith(nom_zone + "_") else stem
                    nom_base = f"{nom_zone}_{suffix}"
                    _mbt_path2 = dossier_ville / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
                    _ecraser_l = args.tuiles_ecraser
                    if _mbt_path2.exists() and not _ecraser_l:
                        print(f"  Existing MBTiles: {_mbt_path2.name} — direct split/conversion")
                        _convertir_formats(_mbt_path2, args, mbtiles_neuf=False)
                        continue
                    _mbt_out = generer_mbtiles_lidar(tif, dossier_ville, nom_base,
                                               zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                                               format_tuiles=args.formats_image,
                                               jpeg_quality=args.qualite_image,
                                               bbox_l93=bbox,
                                               ecraser_tuiles=_ecraser_l,
                                               tile_workers=args.workers)
                    _convertir_formats(_mbt_out, args, mbtiles_neuf=True)
            else:
                print("  No shading found for MBTiles (generate --shadings first)")

    # ── Carte OSM vectorielle de superposition ───────────────────────────────
    dossier_osm = None   # défini si on arrive jusqu'au generer_carte_osm
    if args.osm:
        print_etape("Carte OSM vectorielle")

        # Table département → URL Geofabrik : voir _GEOFABRIK au niveau module

        # Résoudre le PBF source
        pbf = None
        if args.source and Path(args.source).suffix.lower() in (".pbf", ".osm"):
            pbf = Path(args.source)
            if not pbf.exists():
                print(f"  ERROR: PBF file not found: {pbf}")
                pbf = None
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
                        req_rev = urllib.request.Request(
                            url_rev,
                            headers={"User-Agent": _HTTP_UA})
                        with urllib.request.urlopen(req_rev, timeout=10) as resp_rev:
                            data_rev = json.loads(resp_rev.read())
                        if data_rev:
                            num_dep = data_rev[0].get("codeDepartement")
                            print(f"  Department detected: {num_dep}", flush=True)
                    except Exception as e_rev:
                        print(f"  Reverse geocoding failed ({e_rev})")

                region_slug = _GEOFABRIK.get(num_dep) if num_dep else None
            if not region_slug:
                print(f"  Department {num_dep} not found in the Geofabrik table.")
                print(f"  Falling back to the national France PBF (~4 GB).")
                url_pbf = f"{_GEOFABRIK_BASE_URL_ROOT}/france-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / "france-latest.osm.pbf"
            else:
                url_pbf = f"{_GEOFABRIK_BASE_URL}/{region_slug}-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / f"{region_slug}-latest.osm.pbf"

            # Téléchargement PBF commun (national ou régional)
            _SEUIL_PBF = 1_000_000  # 1 MB minimum — PBF vide ou tronqué → re-télécharger
            if pbf.exists() and pbf.stat().st_size >= _SEUIL_PBF:
                print(f"  PBF existant : {pbf.name}  "
                      f"({pbf.stat().st_size/1e9:.1f} Go)")
            else:
                if pbf.exists():
                    print(f"  Truncated PBF ({pbf.stat().st_size} bytes) - re-downloading.")
                    pbf.unlink()
                _log_req(str(url_pbf), 'Geofabrik')
                print(f"  Downloading {url_pbf}...")
                print(f"  Destination : {pbf}", flush=True)
                try:
                    taille_dl = 0
                    t0_dl = time.time()
                    req = urllib.request.Request(url_pbf,
                                      headers={"User-Agent": _HTTP_UA})
                    _pct_last = -1
                    with urllib.request.urlopen(req) as resp, \
                         open(pbf, "wb") as f_out:
                        total_size = int(
                            resp.headers.get("content-length", 0))
                        chunk = 65536
                        while True:
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
                    # Vérifier que le fichier n'est pas vide/tronqué
                    if taille_dl < _SEUIL_PBF:
                        print(f"  ERROR: downloaded PBF too small ({taille_dl} octets)"
                              f" — téléchargement échoué (réseau ? accès Geofabrik ?).")
                        pbf.unlink(missing_ok=True)
                        pbf = None
                except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e_dl:
                    print(f"\n  ERROR downloading PBF ({type(e_dl).__name__}) : {e_dl}")
                    pbf.unlink(missing_ok=True)
                    pbf = None

        if pbf and pbf.exists():
            _region_mode = bool(getattr(args, "zone_region", None))
            if _region_mode:
                # Region : on traite TOUT le PBF régional. bbox "monde" → le .map
                # ignore la bbox (skip_bbox) et l'export geojson ne découpe rien.
                bbox_wgs = (-180.0, -90.0, 180.0, 90.0)
            else:
                # Bbox en WGS84 depuis la bbox Lambert 93 de la zone
                try:
                    lon1, lat1 = lamb93_to_wgs84_approx(bbox[0], bbox[1])
                    lon2, lat2 = lamb93_to_wgs84_approx(bbox[2], bbox[3])
                    bbox_wgs = (min(lon1,lon2), min(lat1,lat2),
                                max(lon1,lon2), max(lat1,lat2))
                except (ValueError, TypeError, ImportError) as e:
                    print(f"  ERREUR conversion bbox WGS84 ({type(e).__name__}) : {e}")
                    bbox_wgs = None
            if bbox_wgs:
                # Dossier dédié OSM — pas le dossier LiDAR
                dossier_osm = (Path(args.dossier).resolve() if args.dossier
                               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "osm_vecteur")
                dossier_osm.mkdir(parents=True, exist_ok=True)
                # Liste des formats GeoJSON demandés (parmi "gz" et "geojson")
                _gj_formats = [f for f in ("gz", "geojson") if f in args.formats_fichier]
                # Mode région : traiter tout le PBF régional sans re-clip
                # (le PBF EST déjà la région — c'est le gain vs boucle départements).
                generer_carte_osm(bbox_wgs, dossier_osm, nom_zone, pbf,
                                  osm_tags=(args.couche
                                            if getattr(args, 'couche', None)
                                            else getattr(args, 'osm_tags', None)),
                                  export_geojson=bool(_gj_formats),
                                  ecraser_tuiles=args.tuiles_ecraser,
                                  skip_bbox=_region_mode,
                                  geojson_formats=_gj_formats or ["gz"])

    if etape_cur[0] > 0:
        elap  = int(time.time() - etape_t0[0])
        cumul = int(time.time() - t_debut)
        print(f"  ✓ Step {etape_cur[0]} finished in {_hms(elap)}  (cumulative {_hms(cumul)})")
    total = int(time.time() - t_debut)
    m, s  = divmod(total, 60)
    print(f"\n  Done! Folder: {dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville}")
    print(f"  Total time: {m}m{s:02d}s")
    dossier_res = str(dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville)
    _historique_depuis_argv(total, dossier_res)


# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================


# ============================================================
# DÉCOUPAGE À PRIORI — FONCTIONS UTILITAIRES
# ============================================================


def _calculer_sous_zones_priori(x1, y1, x2, y2, n_morceaux, rayon_km, unite_m=True,
                                n_cols=0, n_rows=0):
    """
    Divise une bbox en sous-zones pour le découpage à priori.

    unite_m=True  : bbox en mètres  (Lambert 93)  — retourne (i_lat, i_lon, x1, y1, x2, y2)
    unite_m=False : bbox en degrés  (WGS84)        — retourne (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n)

    Priorité des modes (du plus explicite au plus implicite) :
      1. grille explicite n_cols × n_rows — respecte l'intention EXACTE de
         l'utilisateur (un produit premier comme 1×7 reste 1×7, pas refactorisé).
      2. rayon_km — carrés ~KM uniformes : taille de chunk BORNÉE quelle que soit
         l'étendue. Méthode recommandée pour les grandes couvertures (le pic
         RAM/disque par chunk ne dérive pas avec la bbox totale).
      3. n_morceaux — compte seul → grille refactorisée par ratio d'aspect
         (peut dégénérer en lanière si le compte est premier).
      4. zone entière.
    """
    largeur = x2 - x1
    hauteur = y2 - y1

    if n_cols > 0 and n_rows > 0:
        dx = largeur / n_cols
        dy = hauteur / n_rows
        mode_desc = f"{n_cols * n_rows} morceaux ({n_rows}×{n_cols}, grille explicite)"
    elif rayon_km > 0:
        if unite_m:
            dy = dx = rayon_km * 1000
        else:
            lat_c = (y1 + y2) / 2
            dy = rayon_km / 111.0
            dx = rayon_km / (111.0 * math.cos(math.radians(lat_c)))
        n_rows = max(1, int(math.ceil(hauteur / dy)))
        n_cols = max(1, int(math.ceil(largeur / dx)))
        mode_desc = f"~{rayon_km:.0f} km/morceau ({n_rows}×{n_cols})"
    elif n_morceaux > 1:
        best = (1, n_morceaux); best_ratio = float('inf')
        for r in range(1, int(math.sqrt(n_morceaux)) + 1):
            if n_morceaux % r == 0:
                c = n_morceaux // r
                ratio = abs((r / c) - (hauteur / max(largeur, 1e-9)))
                if ratio < best_ratio:
                    best_ratio = ratio; best = (r, c)
        n_rows, n_cols = best
        dx = largeur / n_cols
        dy = hauteur / n_rows
        mode_desc = f"{n_morceaux} morceaux ({n_rows}×{n_cols})"
    else:
        n_rows = n_cols = 1
        dx = largeur
        dy = hauteur
        mode_desc = "1 morceau (zone entière)"

    sous_zones = []
    for i_lat in range(n_rows):
        y_s = y1 + i_lat * dy
        y_n = min(y_s + dy, y2)
        for i_lon in range(n_cols):
            x_w = x1 + i_lon * dx
            x_e = min(x_w + dx, x2)
            sous_zones.append((i_lat, i_lon, x_w, y_s, x_e, y_n))
    return sous_zones, mode_desc

def _lister_dalles_zone(noms_attendus, dossier_dalles, dossier_ville, bbox):
    """Retourne la liste des Path des dalles valides présentes sur disque
    pour cette zone. Source de vérité : dalles_zone.txt si bbox match,
    sinon le set `noms_attendus` (issu de PROVIDER.discover_dalles).

    noms_attendus : iterable de noms de dalles attendus pour la zone
                    (typiquement les keys du dict retourné par discover_dalles).
    """
    # Un SEUL scan disque + un SEUL stat() par fichier, mémorisés dans
    # {nom: (path, size)}. Sur un cache départemental (milliers de .tif) ×
    # des centaines de chunks à priori, le coût énumération+stat dominait
    # (avant : _rglob_tif_robuste ×2, stat() jusqu'à 3×/dalle).
    _index = {}
    for d in _rglob_tif_robuste(dossier_dalles):
        try:
            _index[d.name] = (d, d.stat().st_size)
        except OSError:
            continue

    noms_zone = set()
    dalles_zone_txt = dossier_ville / "dalles_zone.txt"
    if dalles_zone_txt.exists():
        _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
        _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
        if _lignes and _lignes[0].strip() == _bbox_courante:
            noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
    if not noms_zone:
        noms_attendus_set = set(noms_attendus)
        noms_zone = {nom for nom, (_d, _sz) in _index.items()
                     if nom in noms_attendus_set and _sz > SEUIL_DALLE_VALIDE}

    dalles_ombrages = sorted(
        _d for nom, (_d, _sz) in _index.items()
        if nom in noms_zone and _sz > SEUIL_DALLE_VALIDE)
    return dalles_ombrages


def _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args):
    """Télécharge en parallèle les dalles d'un dict {nom: url} (issu de
    PROVIDER.discover_dalles). Pure orchestration : la découverte et le
    fallback grille sont entièrement délégués au provider.

    dalles_dict : {nom_dalle: url_telechargement_complet}
    bbox        : (x_min, y_min, x_max, y_max) en CRS natif (informatif, pour
                  le header de dalles_zone.txt)
    """
    compresser = getattr(args, "telechargement_compresser", False)
    ok = skip = absent = erreur = 0
    a_telecharger = []

    for nom, url in dalles_dict.items():
        if args.telechargement_forcer:
            chemin_dalle(dossier_dalles, nom).unlink(missing_ok=True)
        cd = chemin_dalle(dossier_dalles, nom)
        if not cd.exists() or cd.stat().st_size < SEUIL_DALLE_VALIDE:
            a_telecharger.append((nom, url))
        else:
            skip += 1

    nb_total = len(a_telecharger)
    largeur  = 30
    done = 0
    t0_dl = time.time()

    def _afficher_barre(done, nb_total, t0_dl):
        pct  = int(done * 100 / max(nb_total, 1))
        bars = int(done * largeur / max(nb_total, 1))
        elap = int(time.time() - t0_dl)
        barre = "█" * bars + "░" * (largeur - bars)
        print(f"\r  Dalles LIDAR [{barre}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
              end="", flush=True)

    # Providers servant de grandes mosaïques COG (ca-nrcan…) : lecture fenêtrée
    # /vsicurl/ sur la bbox zone au lieu de rapatrier le COG entier.
    _cog_windowed = getattr(PROVIDER, "COG_WINDOWED", False)
    if a_telecharger:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            if _cog_windowed:
                futures = {ex.submit(telecharger_cog_fenetre, nom, url, dossier_dalles,
                                     bbox, args.telechargement_ecraser): (nom,)
                           for nom, url in a_telecharger}
            else:
                futures = {ex.submit(telecharger_dalle_directe, nom, url, dossier_dalles,
                                     args.telechargement_ecraser): (nom,)
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
        print()  # fin barre
        print(f"  Downloaded: {ok}  Cache: {skip}  Missing: {absent}  Errors: {erreur}")

    # Persister dalles_zone.txt — utile pour --dalles-purger-hors-zone et la
    # reprise (cf. _lister_dalles_zone qui lit ce fichier).
    noms_persistance = [nom for nom in dalles_dict.keys()
                        if chemin_dalle(dossier_dalles, nom).exists()
                        and chemin_dalle(dossier_dalles, nom).stat().st_size > SEUIL_DALLE_VALIDE]
    if noms_persistance:
        _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        dalles_zone_txt.write_text(
            _bbox_hdr + "\n" + "\n".join(sorted(set(noms_persistance))), encoding="utf-8")
        _creer_fichier(dalles_zone_txt)

    # Enregistrer toutes les dalles utilisées par ce chunk dans le manifest
    # pour permettre --nettoyage de les supprimer en fin de chunk. Le
    # téléchargement parallèle ne propage pas _manifest_ctx (threading.local)
    # → registration explicite depuis le main thread.
    for _nom in noms_persistance:
        _cd = chemin_dalle(dossier_dalles, _nom)
        if _cd.exists():
            _creer_fichier(_cd)


def _mbtiles_est_complete(mbt_path):
    """Vérification silencieuse : True si le mbtiles existe, est un SQLite
    lisible et contient >0 tuiles. Aucun side-effect, aucun print — utilisable
    pour les checks de garde-fou dans les boucles de reprise (chunk-level
    manifeste skip), où on veut savoir si un mbtiles "supposé fait" est
    réellement utilisable."""
    if not mbt_path.exists():
        return False
    try:
        with sqlite3.connect(f"file:{mbt_path}?mode=ro", uri=True) as _c:
            return _c.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] > 0
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return False


def _mbtiles_a_regenerer(mbt_path, ecraser):
    """Détermine si un mbtiles doit être (re)généré.

    Retourne True si :
    - le fichier n'existe pas,
    - --tuiles-ecraser est passé,
    - le fichier existe mais contient 0 tuiles (artefact d'un run interrompu),
    - le fichier existe mais est corrompu (SQLite unreadable).

    Sinon retourne False (mbtiles valide, on le réutilise). Logue la raison
    de la regenerating pour éviter les disparitions silencieuses.
    """
    if not mbt_path.exists() or ecraser:
        return True
    # Distinguer fichier illisible vs vide pour un log clair
    try:
        with sqlite3.connect(f"file:{mbt_path}?mode=ro", uri=True) as _c:
            _n = _c.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as _e:
        print(f"  {mbt_path.name} → SQLite unreadable ({type(_e).__name__}), regenerating", flush=True)
        return True
    if _n == 0:
        print(f"  {mbt_path.name} → exists but empty (0 tiles), regenerating", flush=True)
        return True
    return False


def _traiter_bbox_lidar(args, bbox_l93, nom_z, nom_zone_base, manifeste, cle):
    """
    Traite un morceau LiDAR directement en Python (sans subprocess).
    Appelé par la boucle à priori dans main().
    nom_zone_base : nom du projet parent (ex: gareoult2).
    nom_z         : nom du morceau   (ex: gareoult2_001x001).
    """
    bx1, by1, bx2, by2 = bbox_l93

    # Sauvegarder / restaurer les args modifiés temporairement
    _bbox_orig = args.zone_bbox
    _nom_orig  = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom  = nom_z

    try:
        with _contexte_manifeste(manifeste, cle):
            bbox = (bx1, by1, bx2, by2)
            # Structure : <racine>/<nom_zone_base>/ign_lidar/<nom_z>/
            # (tous les morceaux sont sous-dossiers du même projet parent)
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / LIDAR_SUBDIR)
            racine = racine_base
            dossier_dalles = (Path(args.dossier_dalles).resolve() if args.dossier_dalles
                              else DOSSIER_TRAVAIL / "cache" / LIDAR_SUBDIR)
            dossier_ville = racine / nom_z
            dossier_ville.mkdir(parents=True, exist_ok=True)
            dossier_dalles.mkdir(parents=True, exist_ok=True)

            # Découverte des dalles via le provider — retourne {nom: url} en
            # combinant index officiel (TMS pour FR, JSON pour NL, etc.) et
            # éventuel fallback grille interne au provider. Le pipeline reste
            # provider-agnostique : il ne suppose ni grille (x_km, y_km) ni
            # protocole d'accès particulier.
            _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
            _lon1, _lat1 = _t.transform(bx1, by1)
            _lon2, _lat2 = _t.transform(bx2, by2)
            bbox_wgs = (min(_lon1, _lon2) - 0.05, min(_lat1, _lat2) - 0.05,
                        max(_lon1, _lon2) + 0.05, max(_lat1, _lat2) + 0.05)
            cache_discover = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
            # discover_dalles : None = échec réseau/endpoint, {} = pas de
            # couverture (distinguer + protéger l'appel, cf. _traiter_zone).
            try:
                _d = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover)
                if _d is None:
                    print("  ⚠ Découverte des dalles indisponible (réseau/endpoint),"
                          " zone ignorée, réessayez.", flush=True)
            except Exception as _e_disc:
                print(f"  ⚠ Découverte des dalles échouée ({type(_e_disc).__name__}:"
                      f" {_e_disc}), zone ignorée, réessayez.", flush=True)
                _d = None
            dalles_dict = _d or {}

            if args.telechargement:
                _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args)

            if args.ombrages:
                TOUS = ["315","045","135","225","multi","slope","svf","opos","oneg","lrm","rrim"]
                choix = (TOUS if "tous" in args.ombrages
                         else [] if "aucun" in args.ombrages
                         else args.ombrages)
                _spec_i = getattr(args, "shading_instances", None) or []
                if "aucun" in args.ombrages:
                    _spec_i = []
                if _spec_i:
                    _spec_types = {t for t, _ in _spec_i}
                    choix = [c for c in choix if c not in _spec_types]
                if choix or _spec_i:
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

            if args.mbtiles or args.rmap or args.sqlitedb:
                # Filtre identique à la fonction main : exclure les caches de
                # tuilage `_tuilage_z<N>.tif` qui sont produits par le warp
                # rasterio dans `generer_mbtiles_lidar`. Sans ce filtre,
                # un re-run avec --tuiles-ecraser tente de retuiler le cache
                # qui devient sa propre source.
                ombrages_tifs = [t for t in sorted(dossier_ville.glob("*.tif"))
                                 if not t.name.startswith("_")
                                 and not re.search(r'_tuilage_z\d+\.tif$', t.name)]
                for tif in ombrages_tifs:
                    stem   = re.sub(r'_tuilage_z\d+$', '', tif.stem)
                    suffix = stem[len(nom_z)+1:] if stem.startswith(nom_z+"_") else stem
                    nom_base = f"{nom_z}_{suffix}"
                    mbt_path = (dossier_ville
                                / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles")
                    _mbt_neuf = _mbtiles_a_regenerer(mbt_path, args.tuiles_ecraser)
                    if _mbt_neuf:
                        mbt_out = generer_mbtiles_lidar(
                            tif, dossier_ville, nom_base,
                            zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                            format_tuiles=args.formats_image,
                            jpeg_quality=args.qualite_image,
                            bbox_l93=bbox,
                            ecraser_tuiles=args.tuiles_ecraser,
                            tile_workers=args.workers)
                    else:
                        mbt_out = mbt_path
                    _convertir_formats(mbt_out, args, decoupe_sortie=False,
                                       mbtiles_neuf=_mbt_neuf)
    finally:
        args.zone_bbox = _bbox_orig
        args.zone_nom  = _nom_orig


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
    try:
        with _contexte_manifeste(manifeste, cle):
            zoom_min = min(args.zoom_min, args.zoom_max)
            zoom_max = max(args.zoom_min, args.zoom_max)
            tuiles = calculer_grille_xyz(lat_s, lon_w, lat_n, lon_e, zoom_min, zoom_max)
            # Structure : <racine>/<nom_zone_base>/raster/<nom_z>/
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / "raster")
            dossier = racine_base / nom_z
            dossier.mkdir(parents=True, exist_ok=True)
            nom_fichier    = f"{nom_z}_{args.couche}_z{zoom_min}-{zoom_max}"
            chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
            dossier_cache  = DOSSIER_TRAVAIL / "cache" / "ign_raster"
            dossier_cache.mkdir(parents=True, exist_ok=True)
            _jpeg_q = (args.qualite_image
                       if img_fmt.lower() in ("image/png", "png") else None)
            _mbt_neuf = _mbtiles_a_regenerer(chemin_mbtiles, args.tuiles_ecraser)
            if _mbt_neuf:
                generer_mbtiles_wmts(
                    chemin=chemin_mbtiles,
                    tuiles_iter=tuiles,
                    total=len(tuiles),
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
                _convertir_formats(chemin_mbtiles, args, decoupe_sortie=False,
                                   mbtiles_neuf=_mbt_neuf)
    finally:
        args.zone_nom = _nom_orig


def decouper_mbtiles(src_mbtiles, rayon_km=0.0, n_morceaux=1, n_cols=0, n_rows=0,
                     dossier=None, ecraser=False):
    """
    Découpe un MBTiles source en sous-MBTiles.

    Modes (par ordre de priorité) :
      - n_cols > 0 et n_rows > 0 : grille explicite cols×rows (depuis la GUI).
      - n_morceaux > 1            : N morceaux, grille auto la plus carrée.
      - rayon_km  > 0             : carrés de ~rayon_km km.
      - sinon                     : retourne [src_mbtiles] sans découpe.

    Nommage des sorties : {stem}_{ligne:03d}x{col:03d}.mbtiles
    Retourne la liste des Path créés.
    """
    import sqlite3 as _sq

    if n_cols > 0 and n_rows > 0:
        # Grille explicite — on force n_morceaux cohérent pour la suite
        n_morceaux = n_cols * n_rows
    if n_morceaux <= 1 and rayon_km <= 0:
        return [src_mbtiles]

    if not src_mbtiles.exists():
        print(f"  ERROR splitting: {src_mbtiles.name} not found")
        return []

    out_dir = dossier or src_mbtiles.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    con = _sq.connect(str(src_mbtiles))
    meta = dict(con.execute("SELECT name, value FROM metadata").fetchall())
    fmt      = meta.get("format", "jpeg")
    zoom_min = int(meta.get("minzoom", 0))
    zoom_max = int(meta.get("maxzoom", 17))

    # Lire la bbox globale depuis metadata ou calculer depuis les tuiles
    if "bounds" in meta:
        lon0, lat0, lon1, lat1 = [float(v) for v in meta["bounds"].split(",")]
    else:
        rows = con.execute(
            "SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
            "FROM tiles WHERE zoom_level=?", (zoom_max,)).fetchone()
        if not rows or rows[0] is None:
            print(f"  ERROR: MBTiles empty")
            con.close()
            return []
        n = 2 ** zoom_max
        lon0 = rows[0] / n * 360.0 - 180.0
        lon1 = (rows[1] + 1) / n * 360.0 - 180.0
        y_n = n - 1 - rows[2]
        y_s = n - 1 - rows[3]
        def _tile_to_lat(y, n):
            return math.degrees(math.atan(math.sinh(math.pi * (1 - 2*y/n))))
        lat1 = _tile_to_lat(y_n,     n)
        lat0 = _tile_to_lat(y_s + 1, n)

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
            lon0, lat0, lon1, lat1, n_morceaux, rayon_km, unite_m=False)

    if len(sous_zones) <= 1:
        print(f"  Splitting: zone too small -> single file")
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

        if chemin_z.exists():
            if not ecraser:
                print(f"  Existing chunk: {chemin_z.name} - skipped")
                sorties.append(chemin_z)
                continue
            chemin_z.unlink()

        con_z = _sq.connect(str(chemin_z))
        con_z.executescript("""
            CREATE TABLE metadata (name TEXT, value TEXT);
            CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER,
                                tile_row INTEGER, tile_data BLOB);
            CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
        """)

        cx = (lon_w + lon_e) / 2
        cy = (lat_s + lat_n) / 2
        for k, v in [
            ("name",        nom_z),
            ("type",        meta.get("type", "overlay")),
            ("version",     meta.get("version", "1.0")),
            ("description", meta.get("description", "")),
            ("format",      fmt),
            ("minzoom",     str(zoom_min)),
            ("maxzoom",     str(zoom_max)),
            ("bounds",      f"{lon_w:.6f},{lat_s:.6f},{lon_e:.6f},{lat_n:.6f}"),
            ("center",      f"{cx:.6f},{cy:.6f},{zoom_max}"),
        ]:
            con_z.execute("INSERT INTO metadata VALUES (?,?)", (k, v))
        con_z.commit()

        # Copier les tuiles in the bbox
        n_tuiles = 0
        batch    = []
        BATCH    = 500
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
            rows = con.execute(
                "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles "
                "WHERE zoom_level=? AND tile_column BETWEEN ? AND ? "
                "AND tile_row BETWEEN ? AND ?",
                (z, x0, x1, row0, row1)
            ).fetchall()
            batch.extend(rows)
            n_tuiles += len(rows)
            if len(batch) >= BATCH:
                con_z.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                con_z.commit()
                batch = []
        if batch:
            con_z.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con_z.commit()
        con_z.close()

        if n_tuiles == 0:
            chemin_z.unlink()
            print(f"  Sub-zone [{i_lat},{i_lon}]: empty - skipped")
            continue

        print(f"  Sub-zone [{i_lat},{i_lon}] : {n_tuiles:,} tuiles → {chemin_z.name}")
        sorties.append(chemin_z)

    con.close()
    return sorties


def _convertir_un_mbtiles(sf, args, mbtiles_neuf=True):
    """Génère RMAP/SQLiteDB depuis un MBTiles.

    mbtiles_neuf=True : MBTiles fraîchement généré dans cette exécution.
        S'il n'a pas été demandé via --formats-fichier, il est traité comme
        intermédiaire et removed après conversion.
    mbtiles_neuf=False : MBTiles préexistant sur disque (run précédent ou
        copié manuellement). JAMAIS removed — on respecte le travail de
        l'utilisateur, même si seul --rmap/--sqlitedb a été demandé.
    """
    if args.rmap:     generer_rmap_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if args.sqlitedb: generer_sqlitedb_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if mbtiles_neuf and not args.mbtiles and sf.exists():
        sf.unlink()
        print(f"  MBTiles removed: {sf.name}")


def _convertir_formats(mbt_out, args, decoupe_sortie=True, mbtiles_neuf=True):
    """
    Applique le découpage (grille cols×rows ou rayon_decoupe) puis génère
    RMAP/SQLiteDB pour chaque fichier résultant.
    Supprime le MBTiles source uniquement s'il a été généré dans cette
    exécution (mbtiles_neuf=True) ET non demandé via --formats-fichier.
    decoupe_sortie=False → saute le découpage (mode morceau à priori).
    """
    if not mbt_out:
        return

    r_dec  = getattr(args, "rayon_decoupe", 0.0)
    n_cols = getattr(args, "cols_decoupe",  0)
    n_rows = getattr(args, "rows_decoupe",  0)

    # En mode morceau à priori : pas de re-découpage
    if not decoupe_sortie:
        _convertir_un_mbtiles(mbt_out, args, mbtiles_neuf=mbtiles_neuf)
        return

    if n_cols > 0 and n_rows > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, n_cols=n_cols, n_rows=n_rows,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            # Découpage effectif : la source globale n'est gardée que si l'utilisateur
            # l'a demandée OU si elle préexistait. Les sous-fichiers, eux, sont
            # toujours frais (sortie du découpage).
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  Source MBTiles removed: {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args, mbtiles_neuf=True)
    elif r_dec > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, rayon_km=r_dec,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  Source MBTiles removed: {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args, mbtiles_neuf=True)
    else:
        # Pas de découpage : on convertit directement le fichier passé
        _convertir_un_mbtiles(mbt_out, args, mbtiles_neuf=mbtiles_neuf)


def _ajouter_args_zone(parser, *, rayon_default, bbox_metavar, bbox_help=None,
                        avec_dossier=False, avec_help_full=False):
    """Ajoute les flags --zone-{ville,gps,bbox,departement,rayon,nom}
    au parser fourni, en factorisant la duplication entre main(),
    main_wmts(), main_wfs(). Les divergences réelles sont :

    - rayon_default : main() utilisait None (resolved to 10 plus tard),
      main_wmts/wfs utilisent 10.0 dès le parser.
    - bbox_metavar  : main() = "X1,Y1,X2,Y2" Lambert 93 en mètres ;
      main_wmts/wfs = "W,S,E,N" WGS84 en degrés.
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

    parser.add_argument("--zone-radius", "--zone-rayon", type=float, default=rayon_default,
                        metavar="KM", dest="zone_rayon",
                        help=f"Radius in km around the point "
                             f"(default: {rayon_default if rayon_default is not None else 10})")
    parser.add_argument("--zone-name", "--zone-nom", metavar="NAME", default=None, dest="zone_nom",
                        help="Output folder name for the processed zone. "
                             "Required for --zone-gps and --zone-bbox.")
    if avec_dossier:
        parser.add_argument("--output-dir", "--dossier", metavar="PATH", default=None, dest="dossier",
                            help="Root output folder.")
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
        lon_min, lat_min = _lamb93_to_wgs84_safe(bx1, by1)
        lon_max, lat_max = _lamb93_to_wgs84_safe(bx2, by2)

    elif args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        if not nom_zone:
            nom_zone = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        # geocoder_departement retourne du Lambert 93 — reconvertir en WGS84 pour le WFS
        lon_min, lat_min = _lamb93_to_wgs84_safe(bx1, by1)
        lon_max, lat_max = _lamb93_to_wgs84_safe(bx2, by2)

    elif args.zone_bbox:
        try:
            parts = [float(v.strip()) for v in args.zone_bbox.split(",")]
            lon_min, lat_min, lon_max, lat_max = parts
        except (ValueError, IndexError):
            print("  Invalid bbox format. Example: --zone-bbox 5.9,43.1,6.6,43.8")
            sys.exit(1)
        if not nom_zone:
            if getattr(args, 'oui', False):
                print("  ERROR: --zone-name required with --zone-bbox when non-interactive (no terminal)")
                sys.exit(1)
            nom_zone = normaliser_nom(input("  Nom de la zone : ").strip())

    elif args.zone_gps:
        try:
            parts = [p.strip() for p in args.zone_gps.replace(";", ",").split(",")]
            lat_c, lon_c = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            print("  Invalid GPS format. Example: --zone-gps 43.3156,6.0423")
            sys.exit(1)
        if not nom_zone:
            if getattr(args, 'oui', False):
                print("  ERROR: --zone-name required with --zone-gps when non-interactive (no terminal)")
                sys.exit(1)
            nom_zone = normaliser_nom(input("  Nom de la zone : ").strip())
        r     = args.zone_rayon / 111.0
        r_lon = args.zone_rayon / (111.0 * math.cos(math.radians(lat_c)))
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    elif args.zone_ville:
        nom_zone = nom_zone or normaliser_nom(args.zone_ville)
        print(f"  Geocoding '{args.zone_ville}'...")
        lat_c, lon_c = geocoder_ville_wgs84(args.zone_ville)
        if lat_c is None:
            sys.exit(1)
        r     = args.zone_rayon / 111.0
        r_lon = args.zone_rayon / (111.0 * math.cos(math.radians(lat_c)))
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    else:
        if getattr(args, 'oui', False):
            print("  ERROR: a zone option is required when non-interactive (no terminal)")
            sys.exit(1)
        ville = input("  Ville (ou laisser vide pour GPS) : ").strip()
        if ville:
            nom_zone = nom_zone or normaliser_nom(ville)
            lat_c, lon_c = geocoder_ville_wgs84(ville)
            if lat_c is None:
                sys.exit(1)
        else:
            gps = input("  GPS (lat,lon) : ").strip()
            parts = [p.strip() for p in gps.split(",")]
            lat_c, lon_c = float(parts[0]), float(parts[1])
            nom_zone = nom_zone or normaliser_nom(input("  Nom de la zone : ").strip())
        rayon_str = input("  Rayon km [10] : ").strip()
        rayon = float(rayon_str) if rayon_str else 10.0
        r     = rayon / 111.0
        r_lon = rayon / (111.0 * math.cos(math.radians(lat_c)))
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    if not nom_zone:
        sys.exit(1)

    return lon_min, lat_min, lon_max, lat_max, nom_zone


def main_decouper():
    """
    Mode --decouper : découpe a posteriori un MBTiles existant.
    Usage : lidar2map.py --decouper --source fichier.mbtiles
            [--cols C --rows R | --rayon-decoupe KM]
            [--formats-fichier mbtiles rmap sqlitedb]
            [--tuiles-ecraser]
    """
    import argparse
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
    parser.add_argument("--split-radius", "--rayon-decoupe", type=float, default=0.0, metavar="KM",
                        dest="rayon_decoupe", help="Split into ~KM km squares.")
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["mbtiles", "rmap", "sqlitedb"], default=["mbtiles"],
                        metavar="FMT")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser")
    args = parser.parse_args()
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal
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

    print("=" * 55)
    print("  Raster MBTiles splitting")
    print("=" * 55)
    print(f"  Source  : {src}")
    print(f"  Formats : {' '.join(_ff)}")
    if args.cols > 0 and args.rows > 0:
        print(f"  Grille  : {args.cols} cols × {args.rows} lignes")
    elif args.rayon_decoupe:
        print(f"  Radius  : {args.rayon_decoupe} km/chunk")

    sorties = decouper_mbtiles(src, rayon_km=args.rayon_decoupe,
                               n_cols=args.cols, n_rows=args.rows,
                               ecraser=args.tuiles_ecraser)
    for sf in sorties:
        if args.rmap:     generer_rmap_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
        if args.sqlitedb: generer_sqlitedb_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
        if not args.mbtiles and sf != src and sf.exists():
            sf.unlink()
    print("\n  Splitting done.")


def main_wmts():
    import argparse
    t_debut = time.time()

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
                        version="lidar2map 1.10.0 (2026-06) — multi-provider")
    parser.add_argument("--raster", "--ignraster", action="store_true", dest="ignraster",
                        help="IGN raster mode via WMTS. "
                             "Use --layer for the layer (default: scan25). "
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
    grp_priori.add_argument("--split-radius", "--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative: split into ~KM km squares.")
    grp_priori.add_argument("--cleanup", "--nettoyage", action="store_true", dest="nettoyage",
                            help="Delete intermediate tiles + TIFs after each chunk. "
                                 "Essential for large areas (a whole department).")
    grp_priori.add_argument("--min-free-gb", "--min-disque-go", type=float, default=0.0, metavar="GB",
                            dest="min_free_gb",
                            help="Stop cleanly before a chunk if free disk space drops below GB "
                                 "(0 = disabled). Set it ABOVE one chunk's peak footprint "
                                 "(intermediates + tile pyramid). Exits with code 3 so a shell "
                                 "loop can tell a resumable disk-stop from a real error.")

    # Zone
    _ajouter_args_zone(
        parser,
        rayon_default=10.0,
        bbox_metavar="W,S,E,N",
        bbox_help="WGS84 bbox: lon_min,lat_min,lon_max,lat_max",
    )

    # Couche + clé
    parser.add_argument("--layer", "--couche",  default="planign", dest="couche",
                        choices=list(COUCHES.keys()),
                        help="WMTS layer (default: planign, public, no key). "
                             "Restricted pro layers: scan25 scan25tour scan100 scanoaci.")
    parser.add_argument("--api-key", "--apikey",  default="", metavar="KEY", dest="apikey",
                        help="IGN API key for restricted layers (scan25, scan100…). "
                             "⚠ Professional access only (cartes.gouv.fr account + SIRET). "
                             "Individuals must use the public layers (planign, ortho…). "
                             "Can also be set via the IGN_APIKEY env variable.")

    # Zooms
    parser.add_argument("--zoom-min", type=int, default=10, metavar="N")
    parser.add_argument("--zoom-max", type=int, default=16, metavar="N")

    # Sorties
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
    parser.add_argument("--workers",       type=int, default=NB_WORKERS, metavar="N")
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

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal
    _valider_zooms(args, parser)
    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    _historique_debut()

    # ── --source : conversion autonome MBTiles → RMAP (exit immédiat) ────────
    if args.source:
        p = Path(args.source)
        if not p.exists():
            print(f"  ERROR: file not found: {args.source}")
            sys.exit(1)
        if p.suffix.lower() != ".mbtiles":
            print(f"  ERROR: --source expects a .mbtiles (got: {p.suffix})")
            sys.exit(1)
        if not args.rmap and not args.sqlitedb:
            print("  ERROR: --rmap or --sqlitedb required.")
            print(f"  Ex: --source {p.name} --rmap")
            print(f"  Ex: --source {p.name} --sqlitedb")
            sys.exit(1)
        if args.rmap:
            generer_rmap_depuis_mbtiles(p, ecraser=args.tuiles_ecraser)
        if args.sqlitedb:
            generer_sqlitedb_depuis_mbtiles(p, ecraser=args.tuiles_ecraser)
        sys.exit(0)

    # ── Normalisation des sorties ────────────────────────────────────────────
    # Si aucune sortie explicite → MBTiles par défaut
    if not args.mbtiles and not args.rmap and not args.sqlitedb:
        args.mbtiles = True

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

    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    # ── A-priori splitting: traitement séquentiel morceau par morceau ────────
    _cols_pr  = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr  = getattr(args, "rows_decoupe", 0) or 0
    _rayon_pr = getattr(args, "rayon_decoupe", 0.0) or 0.0
    if (_cols_pr > 0 and _rows_pr > 0) or _rayon_pr > 0:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            lon_min, lat_min, lon_max, lat_max,
            0, _rayon_pr, unite_m=False, n_cols=_cols_pr, n_rows=_rows_pr)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / "raster")
            manifeste = Manifeste(racine_pr / nom_zone / "manifeste.json")
            n_total   = len(sous_zones)
            nb_done   = sum(1 for z in sous_zones
                            if manifeste.deja_traite(f"{z[0]+1:03d}x{z[1]+1:03d}"))
            print(f"\n  ══ A-priori splitting: {mode_desc} ══")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Resume: {nb_done}/{n_total} chunks already done")

            nb_ok = 0
            for i_z, (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} — already done")
                    nb_ok += 1
                    continue

                _garde_disque(racine_pr, getattr(args, "min_free_gb", 0.0) or 0.0,
                              cle, nb_ok, n_total)

                surface_km2 = ((lon_e-lon_w)*111*math.cos(math.radians((lat_s+lat_n)/2))) * \
                              ((lat_n-lat_s)*111)
                print(f"\n  ── Chunk {cle}  ({i_z+1}/{n_total})  {nom_z} ──")
                print(f"     BBox WGS84 : {lon_w:.4f},{lat_s:.4f} → "
                      f"{lon_e:.4f},{lat_n:.4f}  (~{surface_km2:.0f} km²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_wmts(args, (lon_w, lat_s, lon_e, lat_n),
                                       nom_z, nom_zone, layer, style, img_fmt, fmt_ext,
                                       apikey_requis, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] ✓ Done in {_hms(int(time.time() - t0_z))}")
                    _n_done, _eta = manifeste.eta_global(n_total)
                    if _eta:
                        print(f"  [{cle}] {_n_done}/{n_total} done — "
                              f"ETA ~{_hms(_eta)} remaining (coarse)")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        # Cf. boucle LiDAR : si chunk vide ou aucun mbtiles, on
                        # conserve les intermédiaires pour inspection plutôt que
                        # de tout supprimer silencieusement.
                        _dossier_chunk = (
                            (Path(args.dossier).resolve() if args.dossier
                             else DOSSIER_TRAVAIL / "Projets" / nom_zone / "raster")
                            / nom_z)
                        _mbts = list(_dossier_chunk.glob("*.mbtiles"))
                        _has_empty = (not _mbts) or any(
                            not _mbtiles_est_complete(mbt) for mbt in _mbts)
                        if _has_empty:
                            print(f"  [{cle}] mbtiles empty or missing - cleanup skipped (intermediates kept for inspection)")
                        else:
                            _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] ✗ ERROR: {_e_z} - relaunch to resume")
                    raise

            elapsed = int(time.time() - t_debut)
            print(f"\n  ══ A-priori splitting done: {nb_ok}/{n_total} chunks ==")
            print(f"  Total time: {_hms(elapsed)}")
            return
        print("  A-priori splitting: zone too small -> single pass")

    # ── Calcul de la grille ───────────────────────────────────────────────────
    zoom_min = min(args.zoom_min, args.zoom_max)
    zoom_max = max(args.zoom_min, args.zoom_max)

    # ── Plafonnement selon capacités réelles de la couche ────────────────────
    # IGN : GetCapabilities WMTS. XYZ (naip…) : table _XYZ_ZOOM_LIMITS.
    _limites_reel = _lire_zoom_limites_wmts(
        layer, apikey_requis, apikey=getattr(args, "apikey", ""))
    if _limites_reel:
        _src_caps = "service" if layer.startswith("XYZ:") else "IGN"
        _zmin_reel, _zmax_reel = _limites_reel
        if zoom_max > _zmax_reel:
            print(f"  ⚠ Layer {args.couche}: {_src_caps} max zoom = {_zmax_reel} "
                  f"— zoom_max ramené de {zoom_max} à {_zmax_reel}.")
            zoom_max = _zmax_reel
            zoom_min = min(zoom_min, zoom_max)
        if zoom_min < _zmin_reel:
            print(f"  ⚠ Layer {args.couche}: {_src_caps} min zoom = {_zmin_reel} "
                  f"— zoom_min ramené de {zoom_min} à {_zmin_reel}.")
            zoom_min = _zmin_reel
            zoom_max = max(zoom_max, zoom_min)

    tuiles = calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max,
                                 zoom_min, zoom_max)
    total  = len(tuiles)
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

    if not args.oui:
        rep = input("\n  Lancer le téléchargement ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    # ── Dossier de sortie ─────────────────────────────────────────────────────
    racine  = Path(args.dossier).resolve() if args.dossier \
              else DOSSIER_TRAVAIL / "Projets" / nom_zone / "raster"
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    nom_fichier = f"{nom_zone}_{args.couche}_z{zoom_min}-{zoom_max}"
    chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
    # Cache tuiles : cache/ign_raster/<z>/<x>/<y>.<ext>. Le dossier de SORTIE est
    # provider-neutre (raster/), mais le cache garde le nom legacy "ign_raster"
    # pour ne pas orpheliner les tuiles WMTS déjà téléchargées des users FR.
    # naip (US) et IGN (FR) y cohabitent sans collision (x/y disjoints).
    dossier_cache = DOSSIER_TRAVAIL / "cache" / "ign_raster"
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
    _native_png = img_fmt.lower() in ("image/png", "png")
    if _native_png and args.formats_image != "png":
        _jpeg_q = args.qualite_image
    else:
        _jpeg_q = None

    # Le MBTiles source doit être (re)généré si :
    #   - il n'existe pas encore
    #   - OU écraser est demandé explicitement
    # Dans tous les autres cas (fichier existant, pas d'écraser) on l'utilise tel quel
    # pour la conversion / le découpage.
    _ecraser   = args.tuiles_ecraser
    _mbtiles_requis = _mbtiles_a_regenerer(chemin_mbtiles, _ecraser)

    if not _mbtiles_requis and chemin_mbtiles.exists():
        print(f"  Existing MBTiles: {chemin_mbtiles.name} — direct split/conversion")

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
    if chemin_mbtiles.exists():
        _convertir_formats(chemin_mbtiles, args, mbtiles_neuf=_mbtiles_requis)

    # ── Résumé ────────────────────────────────────────────────────────────────
    elapsed = int(time.time() - t_debut)
    print(f"\n  Done in {_hms(elapsed)}")
    print(f"  Files in: {dossier}")
    _historique_depuis_argv(elapsed, str(dossier))


# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================


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


def telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                    nom_zone, dossier_sortie, ecraser_telechargement=False,
                    formats=None):
    """Télécharge des features WFS IGN sur une bbox WGS84 → fichier .geojson.

    Pagination automatique (COUNT + STARTINDEX) jusqu'à épuisement.
    formats : liste parmi ("gz", "geojson") — formats à produire (défaut ["gz"]).
              Si plusieurs sont demandés, le téléchargement n'a lieu que si au
              moins un est manquant ; les fichiers manquants sont reconstruits
              à partir du premier disponible (sans re-télécharger).
    Retourne le Path du fichier principal créé (gz si présent, sinon geojson),
    ou None en cas d'erreur.
    """

    dossier_sortie = Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)

    if formats is None:
        formats = ["gz"]
    formats = [f.lower() for f in formats if f.lower() in ("gz", "geojson")]
    if not formats:
        formats = ["gz"]
    ecrire_gz      = "gz"      in formats
    ecrire_geojson = "geojson" in formats

    layer_short = typename.split(":")[-1].lower()
    sortie    = dossier_sortie / f"{nom_zone}_ign_{layer_short}.geojson"
    sortie_gz = Path(str(sortie) + ".gz")

    # Écrasement explicite : supprimer toutes les sorties existantes pour
    # repartir clean.
    if ecraser_telechargement:
        for p in (sortie_gz, sortie):
            if p.exists():
                p.unlink()
                print(f"  {p.name} -> overwrite")

    # Vérification par format demandé : on ne skip que si TOUS sont présents.
    # Sinon, si l'un est présent, on reconstruit les manquants à partir de
    # lui (lecture/écriture locale, pas de re-téléchargement WFS).
    if not ecraser_telechargement:
        manque_gz  = ecrire_gz      and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie
            print(f"  {present.name} -> already present")
            return present
        # Reconstruction locale si une source existe
        if (sortie_gz.exists() or sortie.exists()):
            try:
                if manque_raw and sortie_gz.exists():
                    _gunzip_vers_fichier(sortie_gz, sortie)
                    print(f"  {sortie.name} -> rebuilt from {sortie_gz.name}")
                if manque_gz and sortie.exists():
                    _gzip_depuis_fichier(sortie, sortie_gz)
                    print(f"  {sortie_gz.name} -> rebuilt from {sortie.name}")
                return sortie_gz if sortie_gz.exists() else sortie
            except OSError as e:
                print(f"  ⚠ Local rebuild failed ({e}) - WFS re-download")

    print(f"  WFS {typename}...", flush=True)
    _log_req(f"{WFS_URL}?SERVICE=WFS&TYPENAMES={typename}&...", "WFS IGN")

    startindex    = 0
    n_features    = 0   # compteur — pas d'accumulation Python
    total_attendu = None
    t0 = time.time()

    # ── Pré-requête RESULTTYPE=hits : total sans télécharger les données ──────
    _params_hits = {
        "SERVICE":      "WFS",
        "VERSION":      "2.0.0",
        "REQUEST":      "GetFeature",
        "TYPENAMES":    typename,
        "RESULTTYPE":   "hits",
        "COUNT":        "0",
        "BBOX":         f"{lon_min},{lat_min},{lon_max},{lat_max},EPSG:4326",
    }
    try:
        _url_hits = WFS_URL + "?" + urllib.parse.urlencode(_params_hits)
        _req_hits = urllib.request.Request(
            _url_hits, headers={"User-Agent": _HTTP_UA})
        with urllib.request.urlopen(_req_hits, timeout=15) as _r:
            _d = json.loads(_r.read())
        _nm = _d.get("numberMatched", _d.get("totalFeatures"))
        if _nm is not None:
            total_attendu = int(_nm)
            n_pages = max(1, (total_attendu + WFS_PAGE - 1) // WFS_PAGE)
            print(f"  WFS {typename.split(':')[-1]} : {total_attendu} features attendues "
                  f"({n_pages} page{'s' if n_pages > 1 else ''})", flush=True)
    except Exception:
        pass  # hits non critique — on continuera sans total connu

    # ── Écriture streamée : on ouvre le .gz et on écrit les features au fil
    # de la pagination, sans jamais accumuler en RAM. Sur un dept-scale (>1M
    # features), la version précédente faisait peser plusieurs Go en RAM.
    sortie_gz_tmp = sortie_gz.with_suffix(sortie_gz.suffix + ".tmp")
    sortie_gz_tmp.parent.mkdir(parents=True, exist_ok=True)
    crs_obj = {"type": "name",
               "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(layer_short, ensure_ascii=False)
        + ',"crs":' + json.dumps(crs_obj, ensure_ascii=False, separators=(",", ":"))
        + ',"features":['
    ).encode("utf-8")

    out_fh = None
    try:
        out_fh = gzip.open(sortie_gz_tmp, "wb", compresslevel=6)
        out_fh.write(header)
        first_feat = True

        while True:
            if _stop_event.is_set():
                if n_features:
                    print(f"  WFS interrupted - {n_features} features retrieved (partial .gz output)")
                # Pas de finalisation : on supprime le tmp pour ne pas garder
                # un .gz tronqué qui aurait l'air valide.
                raise KeyboardInterrupt(f"WFS {typename} interrompu")

            params = {
                "SERVICE":      "WFS",
                "VERSION":      "2.0.0",
                "REQUEST":      "GetFeature",
                "TYPENAMES":    typename,
                "OUTPUTFORMAT": "application/json",
                "SRSNAME":      "EPSG:4326",
                "BBOX":         f"{lon_min},{lat_min},{lon_max},{lat_max},EPSG:4326",
                "COUNT":        str(WFS_PAGE),
                "STARTINDEX":   str(startindex),
            }
            url = WFS_URL + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(
                url, headers={"User-Agent": _HTTP_UA})

            data = None
            for tentative in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        data = json.loads(resp.read())
                    break
                except (urllib.error.URLError, urllib.error.HTTPError,
                        json.JSONDecodeError, TimeoutError, OSError) as e:
                    if tentative < 2:
                        time.sleep(3)
                    else:
                        print(f"\n  ERREUR WFS ({typename}) : {type(e).__name__}: {e}")
                        data = None

            if data is None:
                if n_features:
                    print(f"  Partial result: {n_features} features")
                    # On finalise avec ce qu'on a (le client a écrit n_features
                    # valides, on les conserve plutôt que de tout perdre).
                    break
                else:
                    raise OSError(f"WFS {typename} : aucune page récupérée")

            page = data.get("features", [])

            # Fallback si hits a échoué : capturer numberMatched à la 1re page
            if total_attendu is None:
                _nm = data.get("numberMatched", data.get("totalFeatures"))
                if _nm is not None:
                    try:
                        total_attendu = int(_nm)
                    except (ValueError, TypeError):
                        pass

            # Écriture streamée des features de cette page
            for feat in page:
                if not first_feat:
                    out_fh.write(b",")
                first_feat = False
                out_fh.write(json.dumps(feat, ensure_ascii=False,
                                         separators=(",", ":")).encode("utf-8"))
                n_features += 1

            elapsed = int(time.time() - t0)
            n_page  = startindex // WFS_PAGE + 1
            if total_attendu:
                pct = min(n_features * 100 // total_attendu, 99)
                bar = ("█" * (pct // 5)).ljust(20)
                print(f"  WFS  [{bar}] {pct:3d}%  "
                      f"{n_features}/{total_attendu}  "
                      f"page {n_page}  {_hms(elapsed)}", flush=True)
            else:
                print(f"  WFS  page {n_page}  {n_features} features  {_hms(elapsed)}",
                      flush=True)

            if len(page) < WFS_PAGE:
                break
            startindex += WFS_PAGE
            time.sleep(0.2)

        out_fh.write(b"]}")
        out_fh.close()
        out_fh = None
    except BaseException:
        # Toute exception (KeyboardInterrupt, OSError, etc.) → cleanup tmp
        if out_fh is not None:
            try: out_fh.close()
            except Exception: pass
        sortie_gz_tmp.unlink(missing_ok=True)
        raise

    # Promotion atomique du .gz
    sortie_gz_tmp.replace(sortie_gz)

    chemin_principal = None
    if ecrire_gz:
        taille_ko = sortie_gz.stat().st_size // 1024
        print(f"  {sortie_gz.name} : {n_features} features  ({taille_ko} Ko)"
              f"  {_hms(int(time.time()-t0))}")
        chemin_principal = sortie_gz
    if ecrire_geojson:
        # Décompresser en streaming vers le .geojson raw
        _gunzip_vers_fichier(sortie_gz, sortie)
        taille_ko = sortie.stat().st_size // 1024
        print(f"  {sortie.name} : {n_features} features  ({taille_ko} Ko)")
        if chemin_principal is None:
            chemin_principal = sortie
    if not ecrire_gz and sortie_gz.exists():
        # On a écrit le .gz comme intermédiaire — utilisateur ne le voulait pas
        sortie_gz.unlink()
    return chemin_principal


# ============================================================
# CONVERSION GEOJSON IGN → OSM XML → MAPSFORGE .map
# ============================================================

# Correspondance typename WFS IGN → tags OSM pour mapwriter
_IGN_LAYER_TAGS = {
    # hydrographie — rendu bleu natif dans tous les thèmes
    "cours_d_eau":              {"waterway": "river"},
    "troncon_hydrographique":   {"waterway": "stream"},
    "plan_d_eau":               {"natural": "water"},
    "detail_hydrographique":    {"natural": "spring"},
    # bâti / structures
    "batiment":                 {"building": "yes"},
    "construction_surfacique":  {"building": "wall"},
    "cimetiere":                {"landuse": "cemetery"},
    # transport
    "troncon_de_route":         {"highway": "unclassified"},
    "itineraire_autre":         {"highway": "track"},
    # orographie
    "ligne_orographique":       {"natural": "ridge"},
    "detail_orographique":      {"natural": "rock"},
    # végétation / milieu
    "foret_publique":           {"landuse": "forest"},
    "parc_ou_reserve":          {"leisure": "nature_reserve"},
    # cadastre/admin : barrier=fence → trait fin sans remplissage dans tous les thèmes,
    # sémantiquement juste (limite de propriété) et non conflictuel avec landuse OSM
    "commune":                  {"boundary": "administrative", "admin_level": "8"},
    "parcelle":                 {"barrier": "fence"},
    # lieux-dits
    "lieu_dit_non_habite":      {"place": "locality"},
    # RPG
    "parcelles_graphiques":     {"landuse": "farmland"},
}


def _tags_pour_layer(layer_short: str) -> dict:
    """Retourne les tags OSM à appliquer pour un layer WFS IGN (nom court)."""
    for k, v in _IGN_LAYER_TAGS.items():
        if k in layer_short:
            return v
    return {"note": layer_short}


def _coords_flat(geom):
    """Retourne un itérateur de coordonnées [lon, lat, ?] pour tout type GeoJSON."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Point":
        if coords: yield coords
    elif gtype in ("MultiPoint", "LineString"):
        yield from coords
    elif gtype in ("MultiLineString", "Polygon"):
        for ring in coords:
            yield from ring
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                yield from ring
    elif gtype == "GeometryCollection":
        for sub in geom.get("geometries", []):
            yield from _coords_flat(sub)


def _douglas_peucker(coords, epsilon):
    """
    Simplifie une liste de coordonnées [lon, lat] avec l'algorithme Douglas-Peucker.
    epsilon en degrés (~0.00015 ≈ 15 m).
    Conserve toujours le premier et le dernier point.
    """
    if len(coords) <= 2:
        return coords
    # Distance perpendiculaire d'un point à la droite (p1, p2)
    def _perp_dist(p, p1, p2):
        x0, y0 = p[0], p[1]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1)
        t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(x0 - (x1 + t * dx), y0 - (y1 + t * dy))

    def _rdp(pts):
        if len(pts) <= 2:
            return pts
        dmax, idx = 0.0, 0
        for i in range(1, len(pts) - 1):
            d = _perp_dist(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > epsilon:
            left  = _rdp(pts[:idx + 1])
            right = _rdp(pts[idx:])
            return left[:-1] + right
        return [pts[0], pts[-1]]

    return _rdp(list(coords))


# Tolérance de simplification pour la conversion IGN → OSM XML (en degrés).
# 0.00015° ≈ 15 m — réduit la densité IGN (~1 pt/3 m) de 80 %
# sans impact visuel sur une carte Mapsforge à l'échelle département.
_IGN_SIMPLIFY_EPSILON = 0.00015


def _epsilon_depuis_surface_km2(surface_km2: float) -> float:
    """
    Calcule automatiquement l'epsilon de simplification Douglas-Peucker
    en fonction de la surface de la zone, en degrés WGS84.

    Surface        Epsilon    Contexte typique
    < 200 km²      3 m        Zone locale, rayon ~8 km
    < 1 000 km²    8 m        Arrondissement
    < 15 000 km²   15 m       Un département
    < 100 000 km²  25 m       Plusieurs départements
    ≥ 100 000 km²  40 m       Region entière
    """
    # Conversion mètres → degrés : 1° ≈ 111 000 m
    _M_PAR_DEG = 111_000.0
    if surface_km2 < 200:
        metres = 3.0
    elif surface_km2 < 1_000:
        metres = 8.0
    elif surface_km2 < 15_000:
        metres = 15.0
    elif surface_km2 < 100_000:
        metres = 25.0
    else:
        metres = 40.0
    return metres / _M_PAR_DEG

def geojson_ign_vers_osm_xml(geojson_path, osm_xml_path, epsilon=None):
    """
    Convertit un GeoJSON IGN (produit par telecharger_wfs / fusionner_geojson)
    en fichier OSM XML lisible par osmosis + mapwriter.

    Stratégie :
      - Points   → <node>
      - Lignes   → <way> avec <nd ref=…> (nœuds interpolés)
      - Polygones→ <way> fermé (outer ring uniquement pour MultiPolygon)

    Les tags OSM sont déduits du nom de couche (propriété 'source' ou nom fichier).
    Identifiants négatifs (convention OSM pour données non-officielles).

    Streaming : lit le GeoJSON via ijson (pas de json.load() qui ferait OOM
    sur 1 Go de données dept-scale). Écrit nodes et ways dans un fichier
    XML body temporaire au fil de l'eau, puis compose header + bounds + body
    + footer. Bounds calculés en passe unique (pas 4× _coords_flat).
    Format XML bit-fidèle à ElementTree (osmosis est un parseur Java strict).
    """
    from xml.sax.saxutils import escape as _xml_escape
    import decimal as _dec
    import traceback as _tb

    # Valeur d'attribut XML : délimitée par " → il faut aussi échapper les
    # guillemets doubles (saxutils.escape ne gère que & < >). Sinon un nom IGN
    # contenant " (ex: 'Circuit "le Serre Sommet"') casse le XML et osmosis
    # échoue au parsing. On échappe aussi ' par sûreté.
    def _xml_attr(s):
        return _xml_escape(str(s), {'"': "&quot;", "'": "&apos;"})

    geojson_path = Path(geojson_path)
    osm_xml_path = Path(osm_xml_path)
    _eps = epsilon if epsilon is not None else _IGN_SIMPLIFY_EPSILON
    _TS  = "1970-01-01T00:00:00Z"   # timestamp factice — requis par osmosis 0.6

    # ── Itérateur features (streaming si ijson dispo, fallback sinon) ────────
    def _iter_features():
        try:
            import ijson
        except ImportError:
            print("  ⚠ ijson missing - full RAM load of the GeoJSON")
            try:
                if geojson_path.suffix == ".gz":
                    with gzip.open(geojson_path, "rt", encoding="utf-8") as f:
                        gj = json.load(f)
                else:
                    gj = json.loads(geojson_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"  ERREUR lecture GeoJSON ({type(e).__name__}) : {e}")
                return
            yield from gj.get("features", [])
            return

        try:
            opener = ((lambda: gzip.open(geojson_path, "rb"))
                      if geojson_path.suffix == ".gz"
                      else (lambda: open(geojson_path, "rb")))
            with opener() as f:
                yield from ijson.items(f, "features.item")
        except (OSError, ValueError) as e:
            print(f"  ERREUR streaming GeoJSON ({type(e).__name__}) : {e}")
            return

    # ── Helpers d'écriture XML brute (bien plus rapide qu'ElementTree) ───────
    def _f(v):
        """Convertit Decimal (ijson) → float ; passe-plat sinon."""
        return float(v) if isinstance(v, _dec.Decimal) else v

    def _emit_node(out, nid, lat, lon, tags=None):
        # Format reproduit ElementTree : ordre id/lat/lon/version/timestamp/visible,
        # self-closing avec espace avant slash, pas d'indentation.
        attrs = (f'id="{nid}" lat="{lat:.7f}" lon="{lon:.7f}" '
                 f'version="1" timestamp="{_TS}" visible="true"')
        if tags:
            out.write(f'<node {attrs}>')
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_attr(k)}" v="{_xml_attr(v)}" />')
            out.write('</node>')
        else:
            out.write(f'<node {attrs} />')

    def _emit_way(out, wid, nd_refs, tags):
        out.write(f'<way id="{wid}" version="1" timestamp="{_TS}" visible="true">')
        for r in nd_refs:
            out.write(f'<nd ref="{r}" />')
        if tags:
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_attr(k)}" v="{_xml_attr(v)}" />')
        out.write('</way>')

    # ── Compteurs et bounds (passe unique, sans _coords_flat × 4) ────────────
    state = {"node_id": -1, "way_id": -1, "nb_nodes": 0, "nb_ways": 0,
             "lon_min":  float("inf"),  "lon_max": float("-inf"),
             "lat_min":  float("inf"),  "lat_max": float("-inf"),
             "bounds_valid": False,
             "nb_inner_skipped": 0}   # rings intérieurs (trous) non émis

    def _track_bounds(lon, lat):
        if lon < state["lon_min"]: state["lon_min"] = lon
        if lon > state["lon_max"]: state["lon_max"] = lon
        if lat < state["lat_min"]: state["lat_min"] = lat
        if lat > state["lat_max"]: state["lat_max"] = lat
        state["bounds_valid"] = True

    def _emit_node_track(out_nodes, lat, lon, tags=None):
        nid = state["node_id"]
        _emit_node(out_nodes, nid, lat, lon, tags)
        _track_bounds(lon, lat)
        state["nb_nodes"] += 1
        state["node_id"] -= 1
        return nid

    def _emit_linestring(out_nodes, out_ways, raw_coords, osm_tags):
        # Convertir Decimal→float : _douglas_peucker utilise math.hypot et
        # max(0.0, ...) qui ne supportent pas le mixage Decimal/float.
        coords = [(_f(c[0]), _f(c[1])) for c in raw_coords]
        coords = _douglas_peucker(coords, _eps)
        if len(coords) < 2:
            return
        nd_refs = [_emit_node_track(out_nodes, c[1], c[0]) for c in coords]
        wid = state["way_id"]
        _emit_way(out_ways, wid, nd_refs, osm_tags)
        state["nb_ways"] += 1
        state["way_id"] -= 1

    def _emit_ring(out_nodes, out_ways, raw_coords, osm_tags):
        coords = [(_f(c[0]), _f(c[1])) for c in raw_coords]
        coords = _douglas_peucker(coords, _eps)
        if len(coords) < 2:
            return
        nd_refs = [_emit_node_track(out_nodes, c[1], c[0]) for c in coords]
        if nd_refs[0] != nd_refs[-1]:
            nd_refs.append(nd_refs[0])
        wid = state["way_id"]
        _emit_way(out_ways, wid, nd_refs, osm_tags)
        state["nb_ways"] += 1
        state["way_id"] -= 1

    # ── Passe unique : streaming features → 2 fichiers temporaires ───────────
    # OSM XML impose strictement l'ordre nodes → ways → relations (osmosis
    # plante sinon). On écrit donc nodes et ways dans des fichiers séparés
    # puis on les concatène dans l'ordre.
    nodes_tmp = osm_xml_path.parent / (osm_xml_path.name + ".nodes.tmp")
    ways_tmp  = osm_xml_path.parent / (osm_xml_path.name + ".ways.tmp")
    nodes_tmp.parent.mkdir(parents=True, exist_ok=True)

    out_nodes = None
    out_ways  = None
    try:
        out_nodes = open(nodes_tmp, "w", encoding="utf-8")
        out_ways  = open(ways_tmp,  "w", encoding="utf-8")
        for feat in _iter_features():
            if _stop_event.is_set():
                raise KeyboardInterrupt("Interrompu par utilisateur")
            props = feat.get("properties") or {}
            geom  = feat.get("geometry")
            if not geom:
                continue

            # Déduire le layer depuis la propriété 'source' (ex: "gareoult_ign_cours_d_eau")
            src = props.get("source", "")
            layer_short = ""
            for k in _IGN_LAYER_TAGS:
                if k in src:
                    layer_short = k
                    break
            osm_tags = _tags_pour_layer(layer_short)
            # Ajouter le nom si disponible
            for name_key in ("nom", "name", "toponyme", "libelle", "NOM"):
                if props.get(name_key):
                    osm_tags = dict(osm_tags)
                    osm_tags["name"] = str(props[name_key])
                    break

            gtype = geom.get("type", "")
            coords = geom.get("coordinates", [])

            if gtype == "Point":
                _emit_node_track(out_nodes, _f(coords[1]), _f(coords[0]), osm_tags)
            elif gtype == "MultiPoint":
                for pt in coords:
                    _emit_node_track(out_nodes, _f(pt[1]), _f(pt[0]), osm_tags)
            elif gtype == "LineString":
                _emit_linestring(out_nodes, out_ways, coords, osm_tags)
            elif gtype == "MultiLineString":
                for line in coords:
                    _emit_linestring(out_nodes, out_ways, line, osm_tags)
            elif gtype == "Polygon":
                if coords:
                    _emit_ring(out_nodes, out_ways, coords[0], osm_tags)
                    state["nb_inner_skipped"] += max(0, len(coords) - 1)
            elif gtype == "MultiPolygon":
                for poly in coords:
                    if poly:
                        _emit_ring(out_nodes, out_ways, poly[0], osm_tags)
                        state["nb_inner_skipped"] += max(0, len(poly) - 1)
            elif gtype == "GeometryCollection":
                for sub in geom.get("geometries", []):
                    sub_coords = sub.get("coordinates", [])
                    sub_type   = sub.get("type", "")
                    if sub_type == "Point":
                        _emit_node_track(out_nodes, _f(sub_coords[1]),
                                                    _f(sub_coords[0]), osm_tags)
                    elif sub_type == "LineString":
                        _emit_linestring(out_nodes, out_ways, sub_coords, osm_tags)
                    elif sub_type == "MultiLineString":
                        for line in sub_coords:
                            _emit_linestring(out_nodes, out_ways, line, osm_tags)
                    elif sub_type == "Polygon" and sub_coords:
                        _emit_ring(out_nodes, out_ways, sub_coords[0], osm_tags)
                        state["nb_inner_skipped"] += max(0, len(sub_coords) - 1)
                    elif sub_type == "MultiPolygon":
                        for poly in sub_coords:
                            if poly:
                                _emit_ring(out_nodes, out_ways, poly[0], osm_tags)
                                state["nb_inner_skipped"] += max(0, len(poly) - 1)
        out_nodes.close(); out_nodes = None
        out_ways.close();  out_ways  = None
    except KeyboardInterrupt:
        if out_nodes: out_nodes.close()
        if out_ways:  out_ways.close()
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        raise
    except Exception:
        print("\n  ERROR in geojson_ign_vers_osm_xml:")
        _tb.print_exc()
        if out_nodes: out_nodes.close()
        if out_ways:  out_ways.close()
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    if state["nb_nodes"] == 0:
        print("  Empty GeoJSON - nothing to convert.")
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    # ── Composition du XML final : header + bounds + nodes + ways + footer ───
    # Format reproduit fidèlement ElementTree.write(xml_declaration=True) :
    # prologue avec apostrophes simples, encoding utf-8 minuscule.
    try:
        with open(osm_xml_path, "w", encoding="utf-8") as out:
            out.write("<?xml version='1.0' encoding='utf-8'?>\n")
            out.write('<osm version="0.6" generator="lidar2map">')
            if state["bounds_valid"]:
                # <bounds> requis par mapsforge mapwriter pour initialiser le tile store
                out.write(
                    f'<bounds minlat="{state["lat_min"]:.7f}"'
                    f' minlon="{state["lon_min"]:.7f}"'
                    f' maxlat="{state["lat_max"]:.7f}"'
                    f' maxlon="{state["lon_max"]:.7f}" />'
                )
            # Concat des bodies en chunks de 64 KB (pas de read() global)
            for tmp in (nodes_tmp, ways_tmp):
                with open(tmp, "r", encoding="utf-8") as src:
                    while True:
                        chunk = src.read(1 << 16)
                        if not chunk:
                            break
                        out.write(chunk)
            out.write('</osm>')
    finally:
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)

    sz = osm_xml_path.stat().st_size / 1e6
    print(f"  OSM XML: {state['nb_nodes']} nodes, {state['nb_ways']} ways "
          f"→ {osm_xml_path.name} ({sz:.1f} MB)")
    if state["nb_inner_skipped"]:
        # Mapsforge mapwriter ne supporte pas les multi-polygones avec trous via
        # OSM XML (il faut des relations type=multipolygon, hors scope ici).
        # On documente la perte plutôt que de la cacher.
        print(f"  ⚠ {state['nb_inner_skipped']} inner ring(s) skipped "
              f"(trous de polygones — non supportés en sortie .map)")
    return True

def generer_map_depuis_geojson_ign(geojson_src, dossier_ville, nom_zone,
                                    bbox_wgs84, ecraser=False, epsilon=None):
    """
    Pipeline complet : GeoJSON IGN → OSM XML → osmosis+mapwriter → .map Mapsforge.
    Réutilise _verifier_mapwriter(), _trouver_osmosis(), _trouver_java() du mode OSM.
    """

    dossier_ville = Path(dossier_ville)
    chemin_osm_xml = dossier_ville / f"{nom_zone}_ign.osm"
    chemin_map     = dossier_ville / f"{nom_zone}_ign.map"

    if chemin_map.exists() and not ecraser:
        if chemin_map.stat().st_size == 0:
            print(f"  IGN .map exists but empty - forced regeneration.")
            chemin_map.unlink()
        else:
            print(f"  IGN .map already present: {chemin_map.name} - skipped")
            return chemin_map

    if chemin_map.exists() and ecraser:
        chemin_map.unlink()
        print(f"  Carte IGN .map : overwrite {chemin_map.name}")

    # ── Étape 1 : GeoJSON → OSM XML ──────────────────────────────────────────
    print(f"  Conversion GeoJSON → OSM XML...", flush=True)
    ok = geojson_ign_vers_osm_xml(geojson_src, chemin_osm_xml, epsilon=epsilon)
    if not ok:
        return None

    # ── Étape 2 : OSM XML → .map via osmosis + mapwriter ─────────────────────
    _osmosis_exe, _java_home = _preparer_osmosis()
    if not _osmosis_exe:
        chemin_osm_xml.unlink(missing_ok=True)
        return None
    _env_map = os.environ.copy()
    _env_map["JAVA_HOME"] = _java_home
    if "JAVA_OPTS" not in _env_map:
        _env_map["JAVA_OPTS"] = "-Xmx4g" + _java_opts_extra()

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    t0 = time.time()
    print(f"  osmosis → {chemin_map.name}...", flush=True)

    cmd = [
        _osmosis_exe,
        "--read-xml", f"file={chemin_osm_xml}",
        "--mapfile-writer",
        f"file={chemin_map}",
        f"bbox={lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}",
        "zoom-interval-conf=7,0,7,11,8,11,14,12,21",
        "tag-values=true", "polygon-clipping=true",
        "way-clipping=true", "label-position=true",
        # type=hd retiré : bug HDTileBasedDataProcessor sur gros volumes
    ]

    _shell = WINDOWS and str(_osmosis_exe).endswith(".bat")
    if _shell:
        cmd_str = " ".join(
            f'"{a}"' if (" " in str(a) or "=" in str(a)) else str(a)
            for a in cmd
        )
    _log_req(cmd)
    rc, stderr_diag = _run_osmosis_streaming(
        cmd_str if _shell else cmd,
        shell=_shell, env=_env_map,
    )

    if chemin_map.exists() and chemin_map.stat().st_size > 0:
        chemin_osm_xml.unlink(missing_ok=True)  # succès seulement
        taille_b = chemin_map.stat().st_size
        if taille_b < 1_000_000:
            print(f"  {chemin_map.name} : {taille_b // 1024} Ko  {_hms(time.time()-t0)}")
        else:
            print(f"  {chemin_map.name} : {taille_b / 1e6:.1f} MB  {_hms(time.time()-t0)}")
        return chemin_map
    elif chemin_map.exists() and chemin_map.stat().st_size == 0:
        chemin_map.unlink(missing_ok=True)
        print(f"  ⚠ {chemin_map.name} created but empty - no feature recognised by mapwriter.")
        print(f"  {chemin_osm_xml.name} kept for diagnostics.")
        return None
    else:
        print(f"  ERREUR osmosis mapfile-writer IGN (code {rc})")
        if stderr_diag:
            print(f"  {stderr_diag.strip()[:2000]}")
        print(f"  {chemin_osm_xml.name} kept - rerun osmosis after fixing.")
        return None


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


def _decouvrir_url_bdtopo_gpkg(num_dep):
    """Retourne (url_7z, nom_ressource) pour le dernier GPKG BD TOPO du département.
    Les fichiers IGN sont packagés en .7z contenant un .gpkg.
    """
    dep_padded = str(num_dep).zfill(3)
    zone = f"D{dep_padded}"

    # 1. Requête API Atom — retourne du XML Atom, pas du JSON
    try:
        api_url = (f"{BDTOPO_API_URL}?zone={zone}&format=GPKG"
                   f"&crs=LAMB93&page=1&limit=5")
        req = urllib.request.Request(api_url,
                                     headers={"User-Agent": _HTTP_UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
        # Parser le XML Atom pour extraire les noms de ressources
        root = _ET.fromstring(xml_bytes)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        # Les entrées Atom ont un <id> ou <title> contenant le nom de ressource
        noms = []
        for entry in root.findall(".//atom:entry", ns):
            title = entry.findtext("atom:title", namespaces=ns) or ""
            nid   = entry.findtext("atom:id",    namespaces=ns) or ""
            for candidate in (title, nid):
                if f"GPKG_LAMB93_{zone}" in candidate:
                    # Extraire le nom de la ressource depuis l'URL ou le titre
                    parts = candidate.strip("/").split("/")
                    for p in parts:
                        if f"GPKG_LAMB93_{zone}" in p:
                            noms.append(p.replace(".7z", "").replace(".gpkg", ""))
                            break
        if noms:
            # Trier par (date, version_tuple) pour prendre le plus récent.
            # Les noms ont la forme :
            #   BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D083_2024-12-15
            # Un sort lexicographique simple est trompeur dès que la version
            # mineure passe à 2 chiffres ('3-10' < '3-5' en lex).
            _re_meta = re.compile(
                r"BDTOPO_(\d+)-(\d+)_.*_(\d{4}-\d{2}-\d{2})$")
            def _key(nom):
                m = _re_meta.search(nom)
                if not m:
                    return (("",), (0, 0))   # noms non-standard en queue
                maj, mineur, date = m.groups()
                return (date, (int(maj), int(mineur)))
            noms.sort(key=_key, reverse=True)
            nom = noms[0]
            url = f"{BDTOPO_DL_BASE}/{nom}/{nom}.7z"
            print(f"  BD TOPO {zone} GPKG : {nom}", flush=True)
            return url, nom
    except Exception as e:
        print(f"  ⚠ API IGN ({type(e).__name__}: {e}) — essai dates connues")

    # 2. Fallback : dates trimestrielles (YYYY-03/06/09/12-15) sur 2 ans
    import datetime as _dt
    today = _dt.date.today()
    candidates = []
    for delta_q in range(8):
        y, q = today.year, ((today.month - 1) // 3) - delta_q
        while q < 0:
            q += 4; y -= 1
        candidates.append(f"{y}-{[3, 6, 9, 12][q % 4]:02d}-15")

    # Versions IGN à tester. Tuples (major, minor) — le tri par tuple gère
    # correctement les versions mineures à plusieurs chiffres (3-10 > 3-9 > 3-5),
    # contrairement à un tri lex sur la chaîne "3-X". Ajouter une nouvelle
    # version IGN ici en cas de release.
    _versions = sorted(
        [(3, 5), (3, 4), (3, 3)],
        reverse=True,
    )
    for maj, mineur in _versions:
        version = f"{maj}-{mineur}"
        for date_str in candidates:
            nom = f"BDTOPO_{version}_TOUSTHEMES_GPKG_LAMB93_{zone}_{date_str}"
            url = f"{BDTOPO_DL_BASE}/{nom}/{nom}.7z"
            try:
                req_h = urllib.request.Request(url, method="HEAD",
                                               headers={"User-Agent": _HTTP_UA})
                with urllib.request.urlopen(req_h, timeout=10):
                    print(f"  BD TOPO {zone} : {nom}", flush=True)
                    return url, nom
            except Exception:
                continue

    print(f"  ERROR: BD TOPO GPKG archive not found for {num_dep}")
    return None, None


def _telecharger_bdtopo_gpkg(num_dep, url, nom_ressource):
    """Télécharge et extrait le .7z BD TOPO, met le .gpkg en cache. Retourne Path ou None."""
    dep_padded = str(num_dep).zfill(3)
    cache_dir  = DOSSIER_TRAVAIL / "cache" / "bdtopo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = cache_dir / f"{nom_ressource}.gpkg"

    if gpkg_path.exists() and gpkg_path.stat().st_size > 10_000_000:
        print(f"  Cache GPKG : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} MB) — réutilisé", flush=True)
        return gpkg_path

    # ── Vérifier que py7zr est disponible pour l'extraction ──────────────────
    try:
        import py7zr as _py7zr
    except ImportError:
        print("  Installing py7zr for .7z extraction...", flush=True)
        try:
            r_pip = subprocess.run(
                [sys.executable, "-m", "pip", "install", "py7zr", "-q"],
                capture_output=True, timeout=600)
        except subprocess.TimeoutExpired:
            print("  ERROR: py7zr install timeout (>600s) - cannot extract the IGN .7z")
            return None
        if r_pip.returncode != 0:
            print("  ERROR: py7zr not installable - cannot extract the IGN .7z")
            return None
        import py7zr as _py7zr

    # ── Téléchargement du .7z ────────────────────────────────────────────────
    sz_path = cache_dir / f"{nom_ressource}.7z"
    print(f"  Downloading BD TOPO D{dep_padded} (~200-800 MB)...", flush=True)
    _log_req(url, "IGN bulk GPKG")
    tmp = cache_dir / f"{nom_ressource}.7z.tmp"
    t0 = time.time()
    try:
        try:
            resp = _urlopen(url, timeout=120)
        except urllib.error.HTTPError as _e:
            print(f"  ERREUR HTTP {_e.code} — {url}")
            return None
        # `with` ferme la connexion HTTP même sur exception (pas de FD leak).
        with resp:
            total = int(resp.headers.get("content-length") or 0)
            done = 0
            # Throttle d'affichage : on actualise au max toutes les 0.5s pour
            # éviter de noyer la GUI (Popen/PIPE) avec un print() tous les 1 MB.
            _last_print = 0.0
            with open(tmp, "wb") as f:
                while True:
                    if _stop_event.is_set():
                        tmp.unlink(missing_ok=True); return None
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk); done += len(chunk)
                    now = time.time()
                    if now - _last_print < 0.5:
                        continue
                    _last_print = now
                    elapsed = int(now - t0)
                    if total:
                        pct = min(done * 100 // total, 99)
                        bar = ("█" * (pct // 5)).ljust(20)
                        sys.stdout.write(
                            f"\r  [{bar}] {pct:3d}%  "
                            f"{done/1e6:.0f}/{total/1e6:.0f} MB  {_hms(elapsed)}   ")
                    else:
                        sys.stdout.write(
                            f"\r  {done/1e6:.0f} MB  {_hms(elapsed)}   ")
                    sys.stdout.flush()
        sys.stdout.write("\r" + " " * 70 + "\r"); sys.stdout.flush()
        tmp.replace(sz_path)
        print(f"  ✓ {sz_path.name}  ({sz_path.stat().st_size/1e6:.0f} MB)  "
              f"{_hms(int(time.time()-t0))}", flush=True)
    except (OSError, urllib.error.URLError) as e:
        tmp.unlink(missing_ok=True)
        print(f"  ERROR downloading ({type(e).__name__}): {e}")
        return None

    # ── Extraction du .gpkg depuis le .7z ────────────────────────────────────
    print(f"  Extracting GPKG from {sz_path.name}...", flush=True)
    try:
        with _py7zr.SevenZipFile(sz_path, mode="r") as z:
            # Trouver le .gpkg dans l'archive
            gpkg_names = [n for n in z.getnames() if n.lower().endswith(".gpkg")]
            if not gpkg_names:
                print("  ERROR: no .gpkg in the 7z archive")
                sz_path.unlink(missing_ok=True)
                return None
            # Extraire uniquement le .gpkg (peut être dans un sous-dossier)
            z.extract(targets=gpkg_names, path=cache_dir)

        # Trouver le fichier extrait (py7zr peut placer le .gpkg dans un sous-dossier
        # du cache_dir selon la structure interne de l'archive 7z).
        # gpkg_path lui-même n'existe pas à ce stade (return early plus haut),
        # donc tout .gpkg trouvé est forcément le résultat de l'extraction.
        extracted = next(cache_dir.rglob("*.gpkg"), None)
        if extracted is None:
            print("  ERROR: .gpkg not found after extraction")
            return None
        if extracted != gpkg_path:
            extracted.replace(gpkg_path)
            # Nettoyer le sous-dossier laissé par py7zr s'il est devenu vide
            try:
                if extracted.parent != cache_dir and not any(extracted.parent.iterdir()):
                    extracted.parent.rmdir()
            except OSError:
                pass

        sz_path.unlink(missing_ok=True)   # libérer l'espace du .7z
        print(f"  ✓ GPKG extrait : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} MB)", flush=True)
        return gpkg_path

    except Exception as e:
        print(f"  ERREUR extraction .7z ({type(e).__name__}): {e}")
        sz_path.unlink(missing_ok=True)
        return None


def _streamer_geojson_ajout_source(src_geojson, dst_gz, source_name):
    """
    Streame src_geojson (FeatureCollection) → dst_gz en ajoutant
    'source'=source_name à chaque feature.

    Utilise ijson pour lecture incrémentale : ne charge JAMAIS l'intégralité
    du GeoJSON en RAM. Critique pour les couches BD TOPO dept-scale qui
    peuvent dépasser 1 Go en JSON (= 3-4 Go en RAM Python sans streaming).

    Le format de sortie est identique à celui produit par _ecrire_geojson_gz :
    JSON compact (separators=(",", ":")), gzip niveau 6, CRS84.

    Retourne le nombre de features écrites (0 si fichier source vide).
    """
    import decimal as _dec

    def _enc_default(o):
        # ijson retourne des decimal.Decimal pour les nombres → reconvertir en float
        if isinstance(o, _dec.Decimal):
            return float(o)
        raise TypeError(f"Type non-sérialisable : {type(o).__name__}")

    dst_gz = Path(dst_gz)
    if not str(dst_gz).endswith(".gz"):
        dst_gz = Path(str(dst_gz) + ".gz")
    dst_gz.parent.mkdir(parents=True, exist_ok=True)

    try:
        import ijson
    except ImportError:
        # Fallback non-streaming (peut faire OOM sur dept-scale — averti)
        print("  ⚠ ijson missing - full RAM load (OOM risk at dept-scale)")
        with open(src_geojson, encoding="utf-8") as f:
            gj = json.load(f)
        feats = gj.get("features", [])
        for feat in feats:
            props = feat.get("properties") or {}
            props.setdefault("source", source_name)
            feat["properties"] = props
        gj["features"] = feats
        data_bytes = json.dumps(gj, ensure_ascii=False,
                                 separators=(",", ":"),
                                 default=_enc_default).encode("utf-8")
        with gzip.open(dst_gz, "wb", compresslevel=6) as f:
            f.write(data_bytes)
        return len(feats)

    # ── Streaming feature par feature ────────────────────────────────────────
    n = 0
    crs_obj = {"type": "name",
               "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(source_name, ensure_ascii=False)
        + ',"crs":' + json.dumps(crs_obj, ensure_ascii=False, separators=(",", ":"))
        + ',"features":['
    )
    # Écriture binaire dans gzip pour éviter le double encoding text→bytes
    with gzip.open(dst_gz, "wb", compresslevel=6) as out:
        out.write(header.encode("utf-8"))
        with open(src_geojson, "rb") as src:
            for feat in ijson.items(src, "features.item"):
                props = feat.get("properties") or {}
                props.setdefault("source", source_name)
                feat["properties"] = props
                if n > 0:
                    out.write(b",")
                out.write(json.dumps(feat, ensure_ascii=False,
                                      separators=(",", ":"),
                                      default=_enc_default).encode("utf-8"))
                n += 1
        out.write(b"]}")
    return n


def _extraire_couche_bdtopo(gpkg_path, layer_name, sortie_gz,
                             bbox_l93=None, ecraser=False, formats=None):
    """
    Extrait une couche GPKG → GeoJSON(.gz) via fiona (streaming, reprojection WGS84).
    bbox_l93 : (xmin, ymin, xmax, ymax) pour clipper, ou None = département entier.
    formats  : liste parmi ("gz","geojson") — formats à produire (défaut ["gz"]).

    Étape 7 du refactor : remplace ogr2ogr CLI par fiona+pyproj.
    Streaming feature par feature pour borner la RAM (un département entier
    peut faire 200-800 MB en JSON, soit 1-3 Go pic RAM avec json.load()).
    """
    sortie_gz  = Path(sortie_gz)
    sortie_raw = Path(str(sortie_gz)[:-3]) if str(sortie_gz).endswith(".gz") \
                 else Path(str(sortie_gz) + ".geojson")  # fallback inattendu

    if formats is None:
        formats = ["gz"]
    formats = [f.lower() for f in formats if f.lower() in ("gz", "geojson")]
    if not formats:
        formats = ["gz"]
    ecrire_gz      = "gz"      in formats
    ecrire_geojson = "geojson" in formats

    if ecraser:
        for p in (sortie_gz, sortie_raw):
            if p.exists():
                p.unlink()
                print(f"  {p.name} -> overwrite")

    if not ecraser:
        manque_gz  = ecrire_gz      and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie_raw.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie_raw
            print(f"  {present.name} → already present")
            return present
        # Reconstruction locale entre formats — évite de relire le GPKG (lent).
        if (sortie_gz.exists() or sortie_raw.exists()):
            try:
                if manque_raw and sortie_gz.exists():
                    _gunzip_vers_fichier(sortie_gz, sortie_raw)
                    print(f"  {sortie_raw.name} -> rebuilt from {sortie_gz.name}")
                if manque_gz and sortie_raw.exists():
                    _gzip_depuis_fichier(sortie_raw, sortie_gz)
                    print(f"  {sortie_gz.name} -> rebuilt from {sortie_raw.name}")
                return sortie_gz if sortie_gz.exists() else sortie_raw
            except OSError as e:
                print(f"  ⚠ Local rebuild failed ({e}) — extraction GPKG")

    try:
        import fiona
        from fiona.transform import transform_geom as _xform_geom
    except ImportError:
        print("  ERROR: fiona absent — pip install fiona")
        return None

    tmp_geojson = sortie_gz.parent / (sortie_gz.name.replace(".geojson.gz", "_tmp.geojson"))

    t0 = time.time()
    try:
        # Construire le filtre bbox au format fiona si bbox_l93 fourni.
        # bbox doit être en CRS source (EPSG:2154) — fiona accepte directement.
        bbox_filter = None
        if bbox_l93:
            xmin, ymin, xmax, ymax = bbox_l93
            bbox_filter = (xmin, ymin, xmax, ymax)

        # Streaming feature par feature → fichier GeoJSON temp.
        # On reprojete chaque géométrie via fiona.transform (Pyproj sous-jacent).
        with fiona.open(str(gpkg_path), layer=layer_name) as src:
            src_crs = src.crs
            n_total = 0
            with open(tmp_geojson, "w", encoding="utf-8") as out:
                out.write('{"type":"FeatureCollection","features":[\n')
                first = True
                # Itération : si bbox fournie, fiona filtre nativement.
                # Sans bbox : tout le département.
                iterator = src.filter(bbox=bbox_filter) if bbox_filter else src
                for feat in iterator:
                    geom = feat["geometry"]
                    if geom is None:
                        continue
                    # Reprojection en EPSG:4326 (WGS84)
                    geom_4326 = _xform_geom(src_crs, "EPSG:4326", geom)
                    props = dict(feat["properties"]) if feat.get("properties") else {}
                    if not first:
                        out.write(",\n")
                    first = False
                    json.dump({
                        "type":       "Feature",
                        "geometry":   geom_4326,
                        "properties": props,
                    }, out, ensure_ascii=False)
                    n_total += 1
                out.write("\n]}\n")
    except Exception as e:
        print(f"  ERREUR fiona extraction {layer_name} : {type(e).__name__} : {e}")
        tmp_geojson.unlink(missing_ok=True)
        return None

    if not tmp_geojson.exists() or tmp_geojson.stat().st_size == 0 or n_total == 0:
        print(f"  ⚠ {layer_name}: no feature")
        tmp_geojson.unlink(missing_ok=True); return None

    try:
        # _streamer_geojson_ajout_source écrit toujours en .gz — on le génère
        # systématiquement (fichier de travail), puis on dérive .geojson si demandé.
        src_name = sortie_gz.name.replace(".geojson.gz", "")
        n = _streamer_geojson_ajout_source(tmp_geojson, sortie_gz, src_name)
        if n == 0:
            print(f"  ⚠ {layer_name}: 0 features after streaming")
            sortie_gz.unlink(missing_ok=True)
            return None
        chemin_principal = None
        if ecrire_gz:
            print(f"  {sortie_gz.name} : {n} features  ({sortie_gz.stat().st_size//1024} Ko)  "
                  f"{_hms(int(time.time()-t0))}", flush=True)
            chemin_principal = sortie_gz
        if ecrire_geojson:
            _gunzip_vers_fichier(sortie_gz, sortie_raw)
            print(f"  {sortie_raw.name} : {n} features  ({sortie_raw.stat().st_size//1024} Ko)")
            if chemin_principal is None:
                chemin_principal = sortie_raw
        # Si seulement .geojson est demandé, supprimer le .gz intermédiaire
        if not ecrire_gz and sortie_gz.exists():
            sortie_gz.unlink()
        return chemin_principal
    finally:
        tmp_geojson.unlink(missing_ok=True)


def _telecharger_bdtopo_bulk(num_dep, couches_resolues, nom_zone,
                              dossier_sortie, bbox_l93=None, ecraser=False,
                              formats=None):
    """
    Pipeline bulk BD TOPO pour un département entier.
    formats : liste parmi ("gz","geojson") — propagé à _extraire_couche_bdtopo.
    Retourne list[Path] des GeoJSON(.gz) créés, ou None si échec critique.
    """
    print(f"  Bulk BD TOPO GPKG department {num_dep} "
          f"(WFS serait trop lent à cette échelle)", flush=True)
    url, nom = _decouvrir_url_bdtopo_gpkg(num_dep)
    if not url:
        return None
    gpkg_path = _telecharger_bdtopo_gpkg(num_dep, url, nom)
    if not gpkg_path:
        return None

    sorties = []
    for typename, desc in couches_resolues:
        layer_name = typename.split(":")[-1].lower()
        gpkg_layer = _BDTOPO_GPKG_LAYER.get(layer_name, layer_name)
        sortie_gz  = Path(dossier_sortie) / f"{nom_zone}_ign_{layer_name}.geojson.gz"
        print(f"\n  [{desc}]")
        res = _extraire_couche_bdtopo(gpkg_path, gpkg_layer, sortie_gz,
                                      bbox_l93=bbox_l93, ecraser=ecraser,
                                      formats=formats)
        if res:
            sorties.append(res)
    return sorties


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
             "  python lidar2map.py --vector --zone-city gareoult --zone-radius 5",
             "  python lidar2map.py --vector --layer batiments routes --zone-city gareoult",
             "  python lidar2map.py --vector --layer cadastre --zone-department 83",
            ]
        )
    )
    parser.add_argument("--version", action="version",
                        version="lidar2map 1.10.0 (2026-06) — multi-provider")
    parser.add_argument("--vector", "--ignvecteur", action="store_true", dest="ignvecteur")
    parser.add_argument("--layer", "--couche", metavar="NAME", nargs="+", default=["cadastre"], dest="couche",
                        help="WFS layer(s) to download (default: cadastre). "
                             "Short alias or full typename. "
                             "Multiple layers separated by spaces.")

    # Zone — même logique que --ignraster
    _ajouter_args_zone(
        parser,
        rayon_default=10.0,
        bbox_metavar="W,S,E,N",
    )
    parser.add_argument("--output-dir", "--dossier",     metavar="PATH", default=None, dest="dossier",
                        help="Output folder (default: ./ign_vecteur/)")
    parser.add_argument("--workers",  type=int, default=4, metavar="N",
                        help="Parallel WFS connections (default: 4)")
    parser.add_argument("--download-overwrite", "--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Overwrite existing GeoJSON (force re-download)")
    parser.add_argument("--file-formats", "--formats-fichier", nargs="+", dest="formats_fichier",
                        choices=["geojson","gz","map"],
                        default=["gz"], metavar="FMT",
                        help="Output formats: geojson gz map (default: gz). "
                             "map generates a Mapsforge map via osmosis.")
    parser.add_argument("--tiles-overwrite", "--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Overwrite existing .map")
    parser.add_argument("--vector-simplify", "--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Douglas-Peucker simplification epsilon in metres. "
                             "Without it, computed automatically from the area "
                             "(<200 km²→3 m, <1000→8 m, <15000→15 m, <100000→25 m, else→40 m).")
    args = parser.parse_args()
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal
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

    if not args.oui:
        rep = input("\n  Lancer ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    # ── Téléchargement ────────────────────────────────────────────────────────
    sorties = []

    # Pour --zone-departement : basculer sur le bulk GPKG IGN si disponible
    _num_dep = getattr(args, "zone_departement", None)
    _bulk_tente = False
    if _num_dep:
        _bulk_tente = True
        sorties_bulk = _telecharger_bdtopo_bulk(
            num_dep          = _num_dep,
            couches_resolues = couches_resolues,
            nom_zone         = nom_zone,
            dossier_sortie   = dossier,
            bbox_l93         = None,   # département entier — pas de clip bbox
            ecraser          = args.telechargement_ecraser,
            formats          = _gj_formats,
        )
        if sorties_bulk is not None:
            sorties = sorties_bulk
        else:
            print("  Falling back to WFS pagination...")

    if not _bulk_tente or not sorties:
        # WFS standard (zone locale ou repli bulk échoué)
        def _dl(args_tuple):
            typename, desc = args_tuple
            print(f"\n  [{desc}]")
            return telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                                   nom_zone, dossier,
                                   ecraser_telechargement=args.telechargement_ecraser,
                                   formats=_gj_formats)

        if args.workers > 1 and len(couches_resolues) > 1:
            with ThreadPoolExecutor(max_workers=min(args.workers,
                                                    len(couches_resolues))) as ex:
                for f in ex.map(_dl, couches_resolues):
                    if f: sorties.append(f)
        else:
            for typename, desc in couches_resolues:
                f = _dl((typename, desc))
                if f: sorties.append(f)

    # ── Fusion des couches ────────────────────────────────────────────────────
    _geojson_fusionne = None
    if len(sorties) > 1:
        sortie_fusion = dossier / f"{nom_zone}_ign.geojson"
        # main_wfs connaît déjà la bbox (lon_min/lat_min/...) — pas besoin
        # du retour bbox du fusionner_geojson, on prend le compat wrapper.
        _geojson_fusionne = _fusionner_geojson_compat(sorties, sortie_fusion)

    # ── Génération Mapsforge .map si demandé ──────────────────────────────────
    _ff = getattr(args, "formats_fichier", ["gz"])
    if "map" in _ff and sorties:
        # Déterminer la source GeoJSON
        if len(sorties) > 1:
            _src_geojson = _geojson_fusionne  # None si fusion vide
        else:
            _src_geojson = sorties[0]

        if _src_geojson is None or not Path(_src_geojson).exists():
            print("\n  ⚠ Map generation skipped: no feature available.")
        else:
            # Epsilon : paramètre explicite ou calcul automatique depuis surface bbox
            if getattr(args, "simplification_vecteur", None):
                _eps_m = args.simplification_vecteur
                print(f"\n  Vector simplification: epsilon={_eps_m:.1f} m (forced)")
            else:
                _surf = (lon_max - lon_min) * (lat_max - lat_min) * (111_000 ** 2) / 1e6
                _eps_m = _epsilon_depuis_surface_km2(_surf) * 111_000
                print(f"\n  Vector simplification: epsilon={_eps_m:.0f} m (auto, surface≈{_surf:.0f} km²)")
            _eps_deg = _eps_m / 111_000.0
            print("  Generating Mapsforge map (.map) from IGN GeoJSON...")
            generer_map_depuis_geojson_ign(
                geojson_src   = _src_geojson,
                dossier_ville = dossier,
                nom_zone      = nom_zone,
                bbox_wgs84    = (lon_min, lat_min, lon_max, lat_max),
                ecraser       = args.tuiles_ecraser,
                epsilon       = _eps_deg,
            )

    # ── Bilan ─────────────────────────────────────────────────────────────────
    elapsed = int(time.time() - t_debut)
    print(f"\n  Done in {_hms(elapsed)} — {len(sorties)}/{len(couches_resolues)} couches")
    for s in sorties:
        print(f"  → {s}")
    _historique_depuis_argv(elapsed, str(dossier))


# ============================================================
# EXPORT GEOJSON DEPUIS PBF OSM (ogr2ogr)
# ============================================================

def generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                        osm_tags=None, ecraser_tuiles=False, formats=None):
    """
    Exporte le PBF OSM filtré par bbox en GeoJSON via PyOsmium.
    Produit un fichier global ``<nom>_osm.geojson(.gz)`` + un fichier par clé
    thématique ``<nom>_osm_<cle>.geojson(.gz)``.
    Chaque feature reçoit ``source='OSM'``.

    Paramètre `formats` : liste indiquant les formats à produire :
      - ["gz"]                 → .geojson.gz uniquement (défaut, compact)
      - ["geojson"]            → .geojson uniquement (lisible direct)
      - ["gz", "geojson"]      → les deux

    Étape 7bis du refactor : remplace l'ancien pipeline ogr2ogr+osmconf.ini
    par PyOsmium, lib Python pure (binding C++ libosmium) sans dépendance
    GDAL système. Wheels précompilés disponibles pour Python 3.10-3.13 sur
    Windows/macOS/Linux.

    Avantages :
      - Maintenu activement (releases régulières)
      - Wheels précompilés cp312/win_amd64 (~2 MB)
      - Pas de compilation Cython au runtime (contrairement à pyrosm)
      - API GeoJSONFactory directement utilisable

    Limites :
      - Le filtre bbox n'est pas natif côté libosmium : on filtre les nodes
        à la lecture, et on garde uniquement les ways/areas dont au moins
        un node est in the bbox (équivalent --spat de ogr2ogr).
      - Les relations non-multipolygon (route, boundary admin, etc.) ne
        produisent pas de géométrie GeoJSON directement (limitation libosmium).

    Retourne le Path du fichier fusionné principal (.gz si demandé sinon
    .geojson), ou None en cas d'échec.
    """
    # Formats à produire : par défaut .gz uniquement (compatibilité)
    if formats is None:
        formats = ["gz"]
    formats = [f.lower() for f in formats]
    ecrire_gz      = "gz"      in formats
    ecrire_geojson = "geojson" in formats
    if not (ecrire_gz or ecrire_geojson):
        # Cas dégradé : aucun format reconnu, on tombe sur .gz
        ecrire_gz = True

    # Cache check : on ne court-circuite que si TOUS les formats demandés
    # sont already presents. Si l'utilisateur demande à la fois .gz et .geojson,
    # et qu'on n'a que le .gz, il faut quand même regénérer le .geojson.
    chemin_gz_attendu  = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_raw_attendu = dossier_ville / f"{nom_zone}_osm.geojson"
    formats_manquants = []
    if ecrire_gz and not chemin_gz_attendu.exists():
        formats_manquants.append("gz")
    if ecrire_geojson and not chemin_raw_attendu.exists():
        formats_manquants.append("geojson")

    if not formats_manquants and not ecraser_tuiles:
        # Tous les formats demandés sont déjà là
        present = chemin_gz_attendu if chemin_gz_attendu.exists() else chemin_raw_attendu
        print(f"  OSM GeoJSON already present: {present.name} - skipped")
        return present

    if ecraser_tuiles:
        # Mode overwrite : supprimer les sorties existantes pour repartir clean
        for p in (chemin_gz_attendu, chemin_raw_attendu):
            if p.exists():
                p.unlink()
                print(f"  GeoJSON OSM : overwrite {p.name}")
        # Aussi supprimer les fichiers thématiques existants (per-clé)
        for p in dossier_ville.glob(f"{nom_zone}_osm_*.geojson*"):
            try:
                p.unlink()
            except OSError:
                pass

    try:
        import osmium as _osm
    except ImportError:
        print("  ERROR: osmium absent — pip install osmium")
        print("          (official libosmium Python binding, ~2 MB, precompiled wheel)")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    t0 = time.time()
    chemin_principal = chemin_gz_attendu if ecrire_gz else chemin_raw_attendu
    print(f"  PyOsmium → {chemin_principal.name}...", flush=True)

    # Clés thématiques demandées par l'utilisateur (osm_tags="highway=*,waterway=*"
    # → ["highway","waterway"]). Si rien : ensemble par défaut adapté outdoor.
    _cles = []
    if osm_tags:
        for _t in osm_tags:
            _k = _t.split("=")[0].strip()
            if _k and _k not in _cles:
                _cles.append(_k)
    if not _cles:
        _cles = ["highway", "waterway", "natural", "boundary",
                 "landuse", "building", "railway", "leisure"]

    cles_set = set(_cles)
    _crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}

    # GeoJSONFactory produit du GeoJSON-string ; on parse en dict pour
    # construire les features avec leurs propriétés.
    fab = _osm.geom.GeoJSONFactory()

    # Helper : retourne la clé thématique d'un objet (la 1ère trouvée dans cles_set)
    # et la valeur associée. None si aucune clé thématique.
    def _cle_obj(tags):
        for _k in cles_set:
            if _k in tags:
                return _k, tags[_k]
        return None, None

    # Helper : test si une géométrie GeoJSON intersecte la bbox demandée.
    # On fait un test simple bounding-box vs bounding-box (rapide). Suffisant
    # pour notre usage : le PBF est déjà pré-filtré par osmosis sur la bbox.
    def _geom_intersect_bbox(geom_dict):
        if geom_dict is None:
            return False
        coords = geom_dict.get("coordinates")
        if coords is None:
            return False
        # Calcul de la bbox de la géométrie en parcourant les coordonnées
        def _flatten(c):
            if isinstance(c, (list, tuple)):
                if c and isinstance(c[0], (int, float)):
                    yield c
                else:
                    for sub in c:
                        yield from _flatten(sub)
        try:
            xs = []; ys = []
            for pt in _flatten(coords):
                xs.append(pt[0]); ys.append(pt[1])
            if not xs:
                return False
            g_xmin, g_xmax = min(xs), max(xs)
            g_ymin, g_ymax = min(ys), max(ys)
            return not (g_xmax < lon_min or g_xmin > lon_max
                        or g_ymax < lat_min or g_ymin > lat_max)
        except Exception:
            return False

    # Streaming : on ouvre un .gz temporaire par clé thématique et on y écrit
    # les features au fil de la passe PyOsmium. Pas d'accumulation en RAM —
    # un département peut produire plusieurs millions de features.
    _streams       = {}   # cle → file handle gzip ouvert
    _streams_paths = {}   # cle → (path_tmp_gz, path_final_gz, path_final_raw)
    _first_feat    = {}   # cle → bool (1ère feature non encore écrite)
    _counts_par_cle = {}  # cle → nombre de features écrites
    nb_total = [0]
    nb_kept  = [0]

    def _ouvrir_stream_cle(cle):
        """Ouvre paresseusement le .gz tmp pour cette clé (1ère feature)."""
        if cle in _streams:
            return _streams[cle]
        base = dossier_ville / f"{nom_zone}_osm_{cle}.geojson"
        path_gz = Path(str(base) + ".gz")
        path_tmp = path_gz.with_suffix(path_gz.suffix + ".tmp")
        path_tmp.parent.mkdir(parents=True, exist_ok=True)
        fh = gzip.open(path_tmp, "wb", compresslevel=6)
        header = (
            '{"type":"FeatureCollection","name":'
            + json.dumps(f"{nom_zone}_osm_{cle}", ensure_ascii=False)
            + ',"crs":' + json.dumps(_crs, ensure_ascii=False, separators=(",", ":"))
            + ',"features":['
        ).encode("utf-8")
        fh.write(header)
        _streams[cle]       = fh
        _streams_paths[cle] = (path_tmp, path_gz, base)
        _first_feat[cle]    = True
        _counts_par_cle[cle] = 0
        return fh

    def _fermer_streams_partiels():
        """Cleanup en cas d'exception : fermer + supprimer les tmp."""
        for fh in _streams.values():
            try: fh.close()
            except Exception: pass
        for path_tmp, _, _ in _streams_paths.values():
            try: path_tmp.unlink(missing_ok=True)
            except Exception: pass

    # Itération via FileProcessor moderne (PyOsmium 4.x)
    # - with_locations() : nécessaire pour reconstruire les linestrings (ways)
    # - with_areas()     : nécessaire pour reconstruire les multipolygons
    try:
        fp = _osm.FileProcessor(str(osm_pbf)).with_locations().with_areas()
        for o in fp:
            nb_total[0] += 1
            tags = dict(o.tags) if o.tags else {}
            if not tags:
                continue
            cle, val = _cle_obj(tags)
            if cle is None:
                continue

            # Création de la géométrie selon le type d'objet
            try:
                if o.is_node():
                    geom_str = fab.create_point(o)
                elif o.is_way() and not o.is_closed():
                    # Way ouvert → linestring
                    geom_str = fab.create_linestring(o)
                elif o.is_area():
                    # Area (way fermé ou relation multipolygon) → multipolygon
                    geom_str = fab.create_multipolygon(o)
                else:
                    # Relations non-multipolygon : pas de géométrie directe
                    continue
            except Exception:
                # Géométrie invalide (area mal fermée, etc.) — on ignore
                continue

            try:
                geom = json.loads(geom_str)
            except Exception:
                continue

            if not _geom_intersect_bbox(geom):
                continue

            # Construction de la feature GeoJSON, écriture incrémentale
            tags["source"] = "OSM"
            tags["_cle"]   = cle
            feat = {"type": "Feature", "geometry": geom, "properties": tags}

            fh = _ouvrir_stream_cle(cle)
            if not _first_feat[cle]:
                fh.write(b",")
            _first_feat[cle] = False
            fh.write(json.dumps(feat, ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8"))
            _counts_par_cle[cle] += 1
            nb_kept[0] += 1
    except BaseException as e_proc:
        _fermer_streams_partiels()
        if isinstance(e_proc, KeyboardInterrupt):
            raise
        print(f"  ERREUR PyOsmium: {type(e_proc).__name__} : {e_proc}")
        return None

    # Finaliser chaque stream par-clé : footer ']}' puis close puis replace atomique
    for cle, fh in list(_streams.items()):
        try:
            fh.write(b"]}")
            fh.close()
        except Exception:
            try: fh.close()
            except Exception: pass
            _streams_paths[cle][0].unlink(missing_ok=True)
            continue
        path_tmp, path_gz, _ = _streams_paths[cle]
        path_tmp.replace(path_gz)

    print(f"  PyOsmium: {nb_total[0]} objects scanned, {nb_kept[0]} in the bbox", flush=True)

    if nb_kept[0] == 0:
        # Aucune feature retenue — nettoyer les .gz vides éventuels et sortir
        for _, path_gz, _ in _streams_paths.values():
            try: path_gz.unlink(missing_ok=True)
            except Exception: pass
        print("  No OSM feature exported")
        return None

    # Dériver les .geojson raw par-clé si demandé (depuis le .gz, en streaming)
    for cle, (_, path_gz, base) in _streams_paths.items():
        n_cle = _counts_par_cle.get(cle, 0)
        if ecrire_gz:
            print(f"  {path_gz.name} : {n_cle} features")
        if ecrire_geojson:
            _gunzip_vers_fichier(path_gz, base)
            print(f"  {base.name} : {n_cle} features")
        if not ecrire_gz:
            try: path_gz.unlink()
            except Exception: pass

    # Fichier fusionné global : concaténer en streaming les fichiers par-clé
    base_global = dossier_ville / f"{nom_zone}_osm.geojson"
    chemin_global_gz  = Path(str(base_global) + ".gz")
    chemin_global_raw = base_global

    chemin_principal = None
    # On reconstruit le .gz global à partir des .gz par-clé. Pas via
    # `_par_cle` qui n'existe plus — on ré-ouvre chaque fichier par-clé en
    # ijson pour itérer ses features et les ré-injecter dans le global.
    # Si ijson absent, fallback : json.load() — accepté en dégradé sur cas
    # extrêmes (le département entier OSM tient < 2 Go en JSON typiquement).
    try:
        import ijson as _ijson_g
        _has_ijson_g = True
    except ImportError:
        _has_ijson_g = False

    def _iter_feats_par_cle():
        for cle, (_, path_gz, base) in _streams_paths.items():
            src = path_gz if path_gz.exists() else base
            if not src.exists():
                continue
            opener = ((lambda s=src: gzip.open(s, "rb"))
                      if str(src).endswith(".gz")
                      else (lambda s=src: open(s, "rb")))
            if _has_ijson_g:
                try:
                    with opener() as fh:
                        for feat in _ijson_g.items(fh, "features.item"):
                            yield feat
                    continue
                except (OSError, ValueError):
                    pass
            # Fallback non-streaming (cas ijson cassé / absent)
            try:
                with opener() as fh:
                    payload = fh.read()
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8", errors="replace")
                gj = json.loads(payload)
            except Exception:
                continue
            for feat in gj.get("features", []):
                yield feat

    if ecrire_gz or ecrire_geojson:
        chemin_global_gz_tmp = chemin_global_gz.with_suffix(
            chemin_global_gz.suffix + ".tmp")
        try:
            with gzip.open(chemin_global_gz_tmp, "wb", compresslevel=6) as out_g:
                header_g = (
                    '{"type":"FeatureCollection","name":'
                    + json.dumps(f"{nom_zone}_osm", ensure_ascii=False)
                    + ',"crs":' + json.dumps(_crs, ensure_ascii=False, separators=(",", ":"))
                    + ',"features":['
                ).encode("utf-8")
                out_g.write(header_g)
                first_g = True
                import decimal as _dec_g
                def _enc_def(o):
                    if isinstance(o, _dec_g.Decimal): return float(o)
                    raise TypeError(f"Type non-sérialisable : {type(o).__name__}")
                for feat in _iter_feats_par_cle():
                    if not first_g:
                        out_g.write(b",")
                    first_g = False
                    out_g.write(json.dumps(feat, ensure_ascii=False,
                                            separators=(",", ":"),
                                            default=_enc_def).encode("utf-8"))
                out_g.write(b"]}")
            chemin_global_gz_tmp.replace(chemin_global_gz)
        except BaseException:
            chemin_global_gz_tmp.unlink(missing_ok=True)
            raise

        if ecrire_gz:
            taille = chemin_global_gz.stat().st_size // 1024
            print(f"  {chemin_global_gz.name} : {nb_kept[0]} features"
                  f"  ({taille} Ko)  {_hms(int(time.time()-t0))}")
            chemin_principal = chemin_global_gz
        if ecrire_geojson:
            _gunzip_vers_fichier(chemin_global_gz, chemin_global_raw)
            taille = chemin_global_raw.stat().st_size // 1024
            print(f"  {chemin_global_raw.name} : {nb_kept[0]} features"
                  f"  ({taille} Ko)  {_hms(int(time.time()-t0))}")
            if chemin_principal is None:
                chemin_principal = chemin_global_raw
        if not ecrire_gz:
            try: chemin_global_gz.unlink()
            except Exception: pass

    return chemin_principal


# ============================================================
# PIPELINE FUSION GEOJSON
# ============================================================

def _ecrire_geojson_gz(data_dict, chemin, compresser=True):
    """
    Écrit un dict GeoJSON sur disque.
    - compresser=True (défaut)  : produit `<chemin>.geojson.gz` (gzip niveau 6)
    - compresser=False           : produit `<chemin>.geojson` (texte brut)
    Le paramètre `chemin` peut se terminer par .geojson ou .geojson.gz —
    la sortie respectera le mode demandé indépendamment du suffixe d'entrée.
    Retourne le Path du fichier créé.
    """
    p = Path(chemin)
    # Normaliser le chemin selon le mode
    if compresser:
        if not str(p).endswith(".gz"):
            p = Path(str(p) + ".gz")
    else:
        # Mode non compressed : retirer le .gz éventuel
        if str(p).endswith(".gz"):
            p = Path(str(p)[:-3])
    p.parent.mkdir(parents=True, exist_ok=True)
    data_bytes = json.dumps(data_dict, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
    if compresser:
        with gzip.open(p, "wb", compresslevel=6) as f:
            f.write(data_bytes)
    else:
        p.write_bytes(data_bytes)
    return p


def _lire_geojson(chemin):
    """Lit un .geojson ou .geojson.gz — retourne le dict."""
    p = Path(chemin)
    if str(p).endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(p.read_text(encoding="utf-8"))


def fusionner_geojson(fichiers, sortie):
    """
    Fusionne plusieurs GeoJSON en un seul FeatureCollection — STREAMING.

    Lecture incrémentale via ijson (fallback json.load si ijson absent),
    écriture incrémentale dans le .gz au fil de l'eau. La bbox WGS84 est
    calculée pendant la passe d'écriture (pas de re-lecture nécessaire).

    fichiers : liste de Path ou str
    sortie   : Path de sortie
    Retourne (Path créé, bbox|None) — bbox = (lon_min, lat_min, lon_max, lat_max),
    ou (None, None) si aucune feature à fusionner.
    """
    import decimal as _dec
    try:
        import ijson
        _has_ijson = True
    except ImportError:
        _has_ijson = False

    sortie = Path(sortie)
    # Sortie .gz si l'extension dit .gz, sinon raw. _ecrire_geojson_gz
    # respectait déjà cette convention ; on la conserve ici.
    compresser = str(sortie).endswith(".gz")
    if compresser and not str(sortie).endswith(".geojson.gz"):
        # Cas .gz pur : rajouter .geojson au-dessus
        if not str(sortie).endswith(".gz"):
            sortie = Path(str(sortie) + ".gz")

    sortie.parent.mkdir(parents=True, exist_ok=True)
    tmp = sortie.with_suffix(sortie.suffix + ".tmp")

    def _enc_default(o):
        if isinstance(o, _dec.Decimal):
            return float(o)
        raise TypeError(f"Type non-sérialisable : {type(o).__name__}")

    # Header GeoJSON
    name_out = sortie.name.replace(".geojson.gz", "").replace(".geojson", "")
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(name_out, ensure_ascii=False)
        + ',"crs":{"type":"name","properties":'
          '{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}}'
        + ',"features":['
    ).encode("utf-8")

    # Bounds calculés au passage. On évite _coords_flat (récursif Python pour
    # chaque feature) au profit d'une boucle inline plus rapide.
    state = {
        "lon_min": float("inf"),  "lon_max": float("-inf"),
        "lat_min": float("inf"),  "lat_max": float("-inf"),
        "valid":   False,
    }
    def _track(lon, lat):
        if lon < state["lon_min"]: state["lon_min"] = lon
        if lon > state["lon_max"]: state["lon_max"] = lon
        if lat < state["lat_min"]: state["lat_min"] = lat
        if lat > state["lat_max"]: state["lat_max"] = lat
        state["valid"] = True

    def _track_geom(geom):
        if not geom:
            return
        gt = geom.get("type", "")
        c = geom.get("coordinates", [])
        if gt == "Point" and c:
            _track(float(c[0]), float(c[1]))
        elif gt in ("MultiPoint", "LineString"):
            for pt in c: _track(float(pt[0]), float(pt[1]))
        elif gt in ("MultiLineString", "Polygon"):
            for ring in c:
                for pt in ring: _track(float(pt[0]), float(pt[1]))
        elif gt == "MultiPolygon":
            for poly in c:
                for ring in poly:
                    for pt in ring: _track(float(pt[0]), float(pt[1]))
        elif gt == "GeometryCollection":
            for sub in geom.get("geometries", []):
                _track_geom(sub)

    def _iter_features_streame(p):
        """Yield (source, feat) pour chaque feature de p."""
        source = p.stem.replace(".geojson", "")
        if _has_ijson:
            opener = ((lambda: gzip.open(p, "rb")) if str(p).endswith(".gz")
                      else (lambda: open(p, "rb")))
            try:
                with opener() as fh:
                    for feat in ijson.items(fh, "features.item"):
                        yield source, feat
                return
            except (OSError, ValueError) as e:
                print(f"  WARNING: {p.name} streaming failed ({e}) - RAM fallback")
        # Fallback non-streaming
        try:
            data = _lire_geojson(p)
        except Exception as e:
            print(f"  WARNING: {p.name} illisible ({e}) - skipped")
            return
        for feat in data.get("features", []):
            yield source, feat

    n_total = 0
    n_par_fichier = {}
    out_fh = None
    try:
        if compresser:
            out_fh = gzip.open(tmp, "wb", compresslevel=6)
        else:
            out_fh = open(tmp, "wb")
        out_fh.write(header)
        first_feat = True

        for f in fichiers:
            p = Path(f)
            if not p.exists() and not str(p).endswith(".gz"):
                p_gz = Path(str(p) + ".gz")
                if p_gz.exists():
                    p = p_gz
            if not p.exists():
                print(f"  WARNING: {p.name} not found - skipped")
                continue

            n_fichier = 0
            for source, feat in _iter_features_streame(p):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("Fusion interrompue")
                # Convertir Decimal éventuels (ijson)
                props = feat.get("properties") or {}
                if not isinstance(props, dict):
                    props = {}
                props.setdefault("source", source)
                feat["properties"] = props
                geom = feat.get("geometry")
                _track_geom(geom)

                if not first_feat:
                    out_fh.write(b",")
                first_feat = False
                out_fh.write(json.dumps(feat, ensure_ascii=False,
                                         separators=(",", ":"),
                                         default=_enc_default).encode("utf-8"))
                n_fichier += 1
            n_total += n_fichier
            n_par_fichier[p.name] = n_fichier
            print(f"  {p.name} : {n_fichier} features")

        out_fh.write(b"]}")
        out_fh.close()
        out_fh = None
    except BaseException:
        # Fermer + nettoyer le tmp en cas d'interruption ou d'erreur
        if out_fh is not None:
            try: out_fh.close()
            except Exception: pass
        tmp.unlink(missing_ok=True)
        raise

    if n_total == 0:
        tmp.unlink(missing_ok=True)
        print("  No feature to merge")
        return None, None

    tmp.replace(sortie)
    taille = sortie.stat().st_size // 1024
    print(f"  → {sortie.name} : {n_total} features  ({taille} Ko)")

    bbox = None
    if state["valid"]:
        bbox = (state["lon_min"], state["lat_min"],
                state["lon_max"], state["lat_max"])
    return sortie, bbox


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
                        metavar="FMT", help="gz geojson map")
    parser.add_argument("--vector-simplify", "--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Douglas-Peucker epsilon in metres (default: auto from area).")
    args, _ = parser.parse_known_args()  # ignorer --zone-* et autres args globaux
    args.oui = not sys.stdin.isatty()   # non-interactif auto si pas de terminal

    # Crash-safe : sauver l'entrée 'en cours' AVANT toute opération longue.
    _historique_debut()

    # Résoudre les globs éventuels
    import glob as _glob
    fichiers = []
    for pattern in args.source:
        matches = _glob.glob(pattern)
        if matches:
            fichiers.extend(sorted(matches))
        else:
            fichiers.append(pattern)  # sera signalé not found à la fusion

    if not fichiers:
        print("  ERROR: no source file found")
        sys.exit(1)

    # Sortie par défaut
    if args.sortie:
        sortie = Path(args.sortie)
    else:
        if args.dossier:
            dossier = Path(args.dossier)
        else:
            # Utiliser le dossier du premier fichier source comme base
            dossier = Path(fichiers[0]).parent
        # Nom dérivé du premier fichier source
        base = Path(fichiers[0]).stem.split(".")[0]  # gère .geojson.gz
        ext_out = ".geojson" if getattr(args, "no_gz", False) else ".geojson.gz"
        sortie = dossier / f"{base}_fusion{ext_out}"

    print("=" * 52)
    print("  Fusion GeoJSON")
    print("=" * 52)
    for f in fichiers:
        print(f"  + {f}")
    print(f"  → {sortie}")

    if not args.oui:
        rep = input("\n  Lancer ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    fusion_result = fusionner_geojson(fichiers, sortie)
    if fusion_result and fusion_result[0] is not None:
        result, bbox = fusion_result
        fmts = [f.lower() for f in args.formats_fichier]
        # Générer le .map Mapsforge si demandé
        if "map" in fmts:
            nom_zone = sortie.stem.split(".")[0]
            dossier_sortie = sortie.parent
            try:
                # bbox arrive déjà calculée par fusionner_geojson — pas de relecture.
                if getattr(args, 'simplification_vecteur', None):
                    _eps_deg = args.simplification_vecteur / 111_000.0
                    print(f"  Vector simplification: epsilon={args.simplification_vecteur:.1f} m (forced)")
                elif bbox:
                    _surf = (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]) * (111_000**2) / 1e6
                    _eps_deg = _epsilon_depuis_surface_km2(_surf)
                    print(f"  Vector simplification: epsilon={_eps_deg*111000:.0f} m (auto, surface≈{_surf:.0f} km²)")
                else:
                    _eps_deg = _IGN_SIMPLIFY_EPSILON
                generer_map_depuis_geojson_ign(result, dossier_sortie, nom_zone,
                                               bbox_wgs84=bbox, ecraser=True,
                                               epsilon=_eps_deg)
            except Exception as _e:
                print(f"  ERROR generating .map: {_e}")
        print(f"\n  Done in {_hms(int(time.time()-t_debut))}")
    _historique_depuis_argv(int(time.time()-t_debut))


# ── Persistence d'historique 'crash-safe' ──────────────────────────────────
# Sauver l'entrée AU DÉBUT du run garantit qu'elle existe même si le process
# crashe (NameError, SIGKILL, panne courant, Ctrl+C brutal). À la fin, on
# UPDATE cette entrée pour ajouter durée + statut. Identifiant : run_id
# (timestamp ms + pid, hérité via env LIDAR2MAP_HIST_RUN_ID en mode GUI).
_HIST_RUN_ID    = ""
_HIST_T_DEBUT   = 0.0
_HIST_FINALIZED = False


def _hist_disabled() -> bool:
    """Désactivé pendant le smoketest (pollue de 5+ entrées par run)."""
    return bool(os.environ.get("LIDAR2MAP_SKIP_HIST"))


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

    return {
        # Provider — pris du global déjà résolu (PROVIDER.CODE), car _load_provider
        # a strippé --provider de sys.argv ; _arg("--provider") ne le verrait plus.
        "provider": PROVIDER.CODE,
        # Zone
        "type":    t,
        "mode":    mode,
        "nom":     _arg("--zone-name", "--zone-nom"),
        "dossier": _arg("--output-dir", "--dossier"),
        "dep":     _arg("--zone-department", "--zone-departement"),
        "region":  _arg("--zone-region"),
        "ville":   _arg("--zone-city", "--zone-ville"),
        "gps":     _arg("--zone-gps"),
        "bbox":    _arg("--zone-bbox"),
        "rayon":   _arg_float("--zone-radius", "--zone-rayon", default=10.0),
        # LiDAR
        "tel":           _flag("--download", "--telechargement"),
        "comp":          _flag("--download-compress", "--telechargement-compresser"),
        "ecraser_tel":   _flag("--download-overwrite", "--telechargement-ecraser"),
        "workers_l":     _arg_int("--workers", default=8),
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
        "rayon_decoupe_l": _arg_float("--split-radius", "--rayon-decoupe", default=0.0),
        "nettoyage":     _flag("--cleanup", "--nettoyage"),
        # IGN Raster
        "couche":        _arg("--layer", "--couche"),
        "zoom_min_s":    _arg_int("--zoom-min", default=12),
        "zoom_max_s":    _arg_int("--zoom-max", default=16),
        "mbtiles_s":     "mbtiles" in fmts,
        "rmap_s":        "rmap"    in fmts,
        "sqlitedb_s":    "sqlitedb" in fmts,
        "qualite_s":     _arg_int("--image-quality", "--qualite-image", default=85),
        "workers_s":     _arg_int("--workers", default=8),
        # OSM
        "osm_tags_sel":  _args_after("--layer", "--couche") if t == "osm" else [],
        "workers_osm":   _arg_int("--workers", default=4),
        # IGN Vectoriel
        "wfs_couches_sel": _args_after("--layer", "--couche") if t == "vecteur" else [],
        "workers_v":     _arg_int("--workers", default=4),
        # Argv complet pour debug
        "argv":    " ".join(argv),
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

def lancer_gui():
    """
    GUI PyWebView — fenêtre native affichant un formulaire HTML/CSS/JS.
    Communication bidirectionnelle via l'objet Api exposé à JavaScript.
    """
    import threading, queue

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
                "regions":    _regions_disponibles(),
                "lang":       _lire_prefs().get("lang"),   # None = auto-détection JS
                "ui_zoom":    _lire_prefs().get("ui_zoom"),  # None = 1.0
            }

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

        def pick_dir(self):
            w = self._get_window()
            if not w: return ""
            try:
                r = w.create_file_dialog(webview.FOLDER_DIALOG)
                return r[0] if r else ""
            except Exception as e:
                print(f"  pick_dir erreur : {e}")
                return ""

        def pick_file(self, multiple=False, save=False, exts=None):
            w = self._get_window()
            if not w: return [] if multiple else ""
            types = tuple(exts) if exts else ()
            try:
                if save:
                    r = w.create_file_dialog(webview.SAVE_DIALOG, file_types=types)
                else:
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

            # Provider (multi-pays) — propagé au subprocess
            if cfg.get("provider") and cfg["provider"] != PROVIDER.CODE:
                cmd += ["--provider", cfg["provider"]]
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
                if cfg.get("rayon") is not None and cfg["rayon"] != "":
                    cmd += ["--zone-radius", str(cfg["rayon"])]
                if cfg.get("nom"):
                    cmd += ["--zone-name", cfg["nom"]]
                if cfg.get("dossier"):
                    cmd += ["--output-dir", cfg["dossier"]]

            # ── LiDAR ────────────────────────────────────────────────────
            if t == "lidar":
                cmd.append("--lidar")
                if cfg.get("tel"):      cmd.append("--download")
                if cfg.get("comp"):     cmd.append("--download-compress")
                if cfg.get("ecraser_tel"): cmd.append("--download-overwrite")
                if cfg.get("dossier_dalles"):
                    cmd += ["--tiles-dir", cfg["dossier_dalles"]]
                if cfg.get("workers_l"):
                    cmd += ["--workers", str(cfg["workers_l"])]
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
                    # BooleanOptionalAction : émettre explicitement on/off
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
                    _cols = cfg.get("cols_decoupe", 1) or 1
                    _rows = cfg.get("rows_decoupe", 1) or 1
                    if _cols > 1 and _rows > 1:
                        cmd += ["--split-cols", str(_cols),
                                "--split-rows", str(_rows)]
                    elif cfg.get("rayon_decoupe_l", 0) > 0:
                        cmd += ["--split-radius", str(cfg["rayon_decoupe_l"])]
                    if cfg.get("nettoyage"): cmd.append("--cleanup")
                    if cfg.get("min_free_gb", 0) > 0:
                        cmd += ["--min-free-gb", str(cfg["min_free_gb"])]
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
                    _cols = cfg.get("cols_decoupe_s", 0) or 0
                    _rows = cfg.get("rows_decoupe_s", 0) or 0
                    if _cols > 0 and _rows > 0:
                        cmd += ["--split-cols", str(_cols),
                                "--split-rows", str(_rows)]
                    elif cfg.get("rayon_decoupe_s", 0) > 0:
                        cmd += ["--split-radius", str(cfg["rayon_decoupe_s"])]
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
                fmts = []
                if cfg.get("fusion_gz", True):  fmts.append("gz")
                if cfg.get("fusion_gz_raw"):     fmts.append("geojson")
                if not fmts: fmts = ["gz"]  # défaut si rien coché
                if cfg.get("tuiles_v"): fmts.append("map")
                cmd += ["--file-formats"] + fmts
                if cfg.get("tuiles_v") and cfg.get("ecraser_tuil_v"):
                    cmd.append("--tiles-overwrite")
                if cfg.get("tuiles_v") and cfg.get("simplif_v"):
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
                base = Path(cfg["dossier"]) if cfg.get("dossier") else DOSSIER_TRAVAIL / "Projets"
                sortie_dir = base / nom / "fusion"
                cmd += ["--output-file", str(sortie_dir / f"{nom}_fusion{ext}")]
                fmts = []
                if cfg.get("fusion_gz2", True):   fmts.append("gz")
                if cfg.get("fusion_gz2_raw"):      fmts.append("geojson")
                if cfg.get("fusion_map"):          fmts.append("map")
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
                elif cfg.get("rayon_decoupe_d", 0) > 0:
                    cmd += ["--split-radius", str(cfg["rayon_decoupe_d"])]
                fmts_d = []
                if cfg.get("mbtiles_d"):  fmts_d.append("mbtiles")
                if cfg.get("rmap_d"):     fmts_d.append("rmap")
                if cfg.get("sqlitedb_d"): fmts_d.append("sqlitedb")
                if fmts_d: cmd += ["--file-formats"] + fmts_d
                if cfg.get("ecraser_d"):  cmd.append("--tiles-overwrite")


            return cmd

        # ── Lancement ────────────────────────────────────────────────────
        def launch(self, cfg):
            if self._process and self._process.poll() is None:
                return {"error": "Un processus est déjà en cours."}
            cmd = self._build_cmd(cfg)
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
            else:
                self._result_dir = str(base / nom_slug / _type_dir.get(t, t)) if nom_slug else str(base)
            while not self._log_queue.empty():
                try: self._log_queue.get_nowait()
                except queue.Empty: break

            def run():
                self._log_queue.put({"line": "$ " + " ".join(str(c) for c in cmd) + "\n\n",
                                     "tag": "dim"})
                try:
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
                    # Créer un nouveau groupe de processus pour pouvoir tuer toute la hiérarchie
                    if WINDOWS:
                        # Note : CREATE_NEW_PROCESS_GROUP est nécessaire pour que
                        # Ctrl+C puisse tuer le child et ses descendants. Mais
                        # sur certaines configurations Windows + WebView2, cette
                        # flag semble causer un blocage du pipe stdout — les
                        # données restent dans le buffer du child et n'arrivent
                        # jamais au parent. Test sans la flag :
                        self._process = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            bufsize=0, env=env)
                    else:
                        self._process = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            bufsize=0, env=env,
                            start_new_session=True)
                    buf = ""
                    pct_re = re.compile(r"(\d+)%")
                    # Reset des buffers de diagnostic (init dans __init__).
                    # Lock pour cohérence avec poll_log / get_last_error.
                    with self._lock:
                        self._err_lines  = []
                        self._tail_lines = []
                    for chunk in iter(lambda: self._process.stdout.read(64), b""):
                        for ch in chunk.decode("utf-8", errors="replace"):
                            if ch == "\r":
                                # Sur Windows, les print() Python terminent les
                                # lignes par \r\n. Ne traiter le \r comme une
                                # mise à jour de barre de progression QUE si
                                # le buffer contient un pourcentage. Sinon,
                                # c'est juste un CR avant un LF — on l'ignore
                                # et le \n qui suit déclenchera l'envoi normal
                                # de la ligne (path "elif ch == '\\n'").
                                m = pct_re.search(buf)
                                if m:
                                    pct = int(m.group(1))
                                    if buf.strip():
                                        self._log_queue.put({"pct": pct, "label": buf.strip()})
                                    buf = ""
                                # Sinon : ignorer ce \r (CRLF Windows), garder buf intact
                            elif ch == "\n":
                                if buf.strip():
                                    is_err = _classify_err(buf)
                                    tag = "err" if is_err else "ok"
                                    with self._lock:
                                        if is_err and len(self._err_lines) < 20:
                                            self._err_lines.append(buf.strip())
                                        # Buffer circulaire des 10 dernières lignes
                                        # non-vides : fallback si retcode≠0 sans
                                        # ligne marquée "ERREUR".
                                        self._tail_lines.append(buf.strip())
                                        if len(self._tail_lines) > 10:
                                            self._tail_lines.pop(0)
                                    self._log_queue.put({"line": buf + "\n", "tag": tag})
                                buf = ""
                            else:
                                buf += ch
                    # Drain final : la boucle for-chunk a vu EOF, mais le buffer
                    # interne `buf` peut contenir une dernière ligne sans \n
                    # final (ex : print() Python sans flush avant sys.exit).
                    # Sans ça, ces lignes sont perdues sur Windows quand le
                    # child exit en moins de 100ms.
                    if buf.strip():
                        is_err = _classify_err(buf)
                        with self._lock:
                            if is_err and len(self._err_lines) < 20:
                                self._err_lines.append(buf.strip())
                            self._tail_lines.append(buf.strip())
                            if len(self._tail_lines) > 10:
                                self._tail_lines.pop(0)
                        self._log_queue.put({"line": buf + "\n",
                                             "tag": "err" if is_err else "ok"})
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
                                is_err = _classify_err(line)
                                with self._lock:
                                    if is_err and len(self._err_lines) < 20:
                                        self._err_lines.append(line.strip())
                                    self._tail_lines.append(line.strip())
                                    if len(self._tail_lines) > 10:
                                        self._tail_lines.pop(0)
                                self._log_queue.put({
                                    "line": line + "\n",
                                    "tag": "err" if is_err else "ok",
                                })
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

            threading.Thread(target=run, daemon=True).start()
            return {"cmd": " ".join(str(c) for c in cmd)}

        def stop(self):
            if self._process and self._process.poll() is None:
                try:
                    if WINDOWS:
                        # Tuer tout le groupe de processus Windows
                        subprocess.call(["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.killpg(os.getpgid(self._process.pid), _signal.SIGKILL)
                except Exception:
                    self._process.terminate()
                self._log_queue.put({"line": "\n⚠ Arrêté\n", "tag": "err"})
                self._done = True

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
                    _statut = "ok" if self._retcode == 0 else "ko"
                    _result = getattr(self, "_result_dir", "") if self._retcode == 0 else ""
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
                    items.append({"line": f"  ERREUR historique : {_he}\n", "tag": "err"})

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
    _w, _h = 1300, 850
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            _r = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(_r), 0)  # SPI_GETWORKAREA
            _wa_w, _wa_h = _r.right - _r.left, _r.bottom - _r.top
            if _wa_h > 0:
                _h = max(600, min(_h, _wa_h - 48))
                _w = max(1000, min(_w, _wa_w - 48))
    except Exception:
        pass

    win = webview.create_window(
        "lidar2map — Cartes offline LiDAR / raster / OSM",
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

    # Activable via flag --debug (clic droit → Inspect dans la fenêtre webview,
    # ou F12, pour ouvrir les DevTools et voir la console JS).
    _wv_debug = "--debug" in sys.argv
    webview.start(debug=_wv_debug)


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
            _ns_pre, _ = _pre.parse_known_args()

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
            # Transparent pour argparse, qui accepte déjà les deux formes.
            _argv_norm = []
            for _a in sys.argv:
                if _a.startswith(("--zone-departement=", "--zone-department=")):
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
                _sep = "═" * 55
                # Détecter --zone-nom explicite : sera suffixé par _<dep> pour éviter
                # que les sorties multi-département s'écrasent mutuellement.
                _nom_idx = None
                _nom_base = None
                for _i, _a in enumerate(_argv_base):
                    if _a == "--zone-nom" and _i + 1 < len(_argv_base):
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
                        print(f"  ✗ Departement {_dep} echoue : "
                              f"{type(_e_dep).__name__}: {_e_dep} — on continue.")
                if _deps_ko:
                    print(f"\n  ⚠ Departements en echec : {','.join(_deps_ko)} "
                          f"(relance la commande pour les reprendre)")
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
            sys.stdout.close()
            sys.stdout = sys.stdout._terminal if hasattr(sys.stdout, "_terminal") else sys.__stdout__
