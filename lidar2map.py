# lidar2map.py â€” Prospection LiDAR archÃ©ologique & cartes offline pour Locus Map / OsmAnd
# Copyright (C) 2025 Nicolas Martin
#
# Ce logiciel a Ã©tÃ© conÃ§u, architecturÃ© et dirigÃ© par Nicolas Martin.
# Le code source a Ã©tÃ© dÃ©veloppÃ© avec l'assistance de Claude (Anthropic),
# utilisÃ© comme outil de dÃ©veloppement.
#
# Licence : GNU General Public License v3.0
# https://www.gnu.org/licenses/gpl-3.0.html
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou
# le modifier selon les termes de la GNU GPL telle que publiÃ©e par la
# Free Software Foundation (version 3 ou toute version ultÃ©rieure).
#
# Ce programme est distribuÃ© dans l'espoir qu'il sera utile, mais SANS
# AUCUNE GARANTIE, sans mÃªme la garantie implicite de COMMERCIALISATION
# ou d'ADÃ‰QUATION Ã€ UN USAGE PARTICULIER.
#
"""
lidar2map.py â€” Prospection archÃ©ologique LiDAR & cartes offline
======================================================================

Script unifiÃ© 5 modes pour Locus Map / OsmAnd / TwoNav.
Plateformes : Windows 10+, macOS 11+, Linux (Debian/Ubuntu testÃ©s).

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  CONCEPT ET WORKFLOW
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Les 4 types de cartes sont INDÃ‰PENDANTS et complÃ©mentaires :

  â‘  LiDAR MNT   Fond principal d'analyse archÃ©ologique. On commence par
                 ici : tÃ©lÃ©chargement des dalles, calcul des ombrages
                 (multi-directionnel, SVF, LRM, RRIMâ€¦), export en MBTiles.
                 On expÃ©rimente dans Locus, on identifie les manques.

  â‘¡ IGN Raster  Fond alternatif ou de recalage (Scan 25, orthophotosâ€¦).
                 Peut remplacer le LiDAR quand les donnÃ©es manquent, ou
                 servir de fond de rÃ©fÃ©rence topographique pour complÃ©ter
                 l'analyse. Se superpose aux overlays vectoriels.

  â‘¢ IGN Vecteur Overlay de prÃ©cision : cadastre, hydrographie, cheminsâ€¦
                 TÃ©lÃ©chargÃ© en GeoJSON, chargÃ© en superposition dans Locus
                 sur le fond LiDAR ou IGN Raster pour enrichir l'analyse.

  â‘£ OSM Vecteur Overlay polyvalent : routes, cours d'eau, patrimoineâ€¦
                 GÃ©nÃ©rÃ© en Mapsforge (.map) et/ou GeoJSON, utilisable en
                 superposition sur n'importe quel fond raster.

  â‘¤ Fusion      Outil utilitaire : fusionne plusieurs GeoJSON (IGN + OSM)
                 en un seul overlay unifiÃ© avec traÃ§abilitÃ© de la source.

  Flux typique :
    1. GÃ©nÃ©rer le LiDAR â†’ charger dans Locus
    2. Selon les besoins : ajouter overlay IGN Vecteur et/ou OSM
    3. Si couverture LiDAR insuffisante : gÃ©nÃ©rer IGN Raster (Scan 25/Ortho)
    4. Fusionner les GeoJSON si besoin d'un overlay unique combinÃ©

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODES
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  --ignlidar      Dalles LiDAR HD IGN (WMS) â†’ ombrages â†’ MBTiles/RMAP/SQLiteDB
  --ignraster     Tuiles WMTS IGN (Scan 25, Orthoâ€¦) â†’ MBTiles/RMAP/SQLiteDB
  --ignvecteur    WFS IGN (cadastre, hydrographieâ€¦) â†’ GeoJSON(.gz)
  --osm           PBF Geofabrik â†’ carte Mapsforge (.map) + GeoJSON(.gz)
  --fusionner     Fusion de GeoJSON/GeoJSON.gz en un seul fichier

  Sans argument   â†’ GUI pywebview (interface HTML/JS)

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  ZONE GÃ‰OGRAPHIQUE (commune Ã  tous les modes)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  --zone-ville NOM            GÃ©ocodage Nominatim (ex: gareoult)
  --zone-gps   LAT,LON        CoordonnÃ©es WGS84  (ex: 43.3156,6.0423)
  --zone-bbox  W,S,E,N        BBox WGS84 en degrÃ©s
  --zone-departement NUM      DÃ©partement franÃ§ais (ex: 83)
  --zone-rayon KM             Rayon autour du point (dÃ©faut: 10)
  --zone-nom   NOM            Nom du dossier de sortie (ex: aa)

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  FORMATS DE SORTIE (communs)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  --formats-fichier FMT...    Formats de fichiers de sortie (multi-valeurs) :
                                ignlidar/ignraster : mbtiles rmap sqlitedb
                                osm                : map geojson gz
                                ignvecteur/fusion  : geojson gz
  --formats-image   FMT       Format des images dans les tuiles (ignlidar/ignraster) :
                                auto (dÃ©faut) | jpeg | png
  --qualite-image   Q         QualitÃ© JPEG des images (1-100, dÃ©faut: 85)
                                75 = -35% taille, quasi invisible

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODE --ignlidar
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Pipeline :
    1. Dalles IGN LiDAR HD (WMS, cache permanent dans --dossier-dalles)
       â†’ dalles_zone.txt (liste bbox-versionnÃ©e, reconstruite si zone change)
    2. gdalbuildvrt â†’ VRT global temporaire (EPSG:2154, < 1 s)
    3. gdaldem / numpy/scipy â†’ TIF ombrages (Ã©tape "ombrage")
       â†’ <nom>_multi_ombrage.tif, <nom>_slope_ombrage.tifâ€¦
    4. gdalwarp + gdaladdo + tuilage Pillow â†’ MBTiles/RMAP/SQLiteDB
       â†’ <nom>_multi_ombrage_tuilage_z18.tif (cache Mercator, rÃ©utilisable)
       â†’ <nom>_multi_ombrage_z8-18.mbtiles
       â†’ <nom>_multi_ombrage_z8-18.rmap
       â†’ <nom>_multi_ombrage_z8-18.sqlitedb

  ParamÃ¨tres spÃ©cifiques :
    --telechargement            TÃ©lÃ©charger les dalles manquantes
    --telechargement-forcer     Re-tÃ©lÃ©charger mÃªme les dalles existantes
    --telechargement-compresser Compresser les dalles tÃ©lÃ©chargÃ©es (DEFLATE)
    --dossier-dalles CHEMIN     Cache dalles sÃ©parÃ© (dÃ©faut: ign_lidar/dalles/)
    --workers N                 Connexions parallÃ¨les (dÃ©faut: 8)
    --ombrages TYPE...          Ombrages Ã  gÃ©nÃ©rer :
                                  315 045 135 225 multi slope svf svf100 lrm rrim
                                  tous | aucun
    --ombrages-elevation DEG    Angle solaire en degrÃ©s (dÃ©faut: 25)
    --ombrages-compresser       Compresser les TIF ombrages existants (DEFLATE)
    --zoom-min N                Zoom minimum MBTiles (dÃ©faut: 13 â€” inclut z8-12 via --zoom-min 8)
    --zoom-max N                Zoom maximum MBTiles (dÃ©faut: 18)
    --cols-decoupe N            DÃ©coupe le MBTiles final en N colonnes (avec --rows-decoupe)
    --rows-decoupe N            DÃ©coupe le MBTiles final en N lignes   (avec --cols-decoupe)
    --rayon-decoupe KM          Alternative : dÃ©coupe en carrÃ©s de ~KM km
    --source CHEMIN             Source alternative :
                                  .tif   â†’ ombrage existant â†’ tuilage direct
                                  .mbtiles â†’ conversion â†’ RMAP/SQLiteDB
    --osm                       GÃ©nÃ©rer overlay OSM vectoriel (standalone ou aprÃ¨s LiDAR)

  Arborescence de sortie :
    Projets/<nom>/
      ign_lidar/
        dalles_zone.txt             liste dalles (# bbox:x1,y1,x2,y2 en tÃªte)
        manifeste.json              Ã©tat de reprise (dÃ©coupage Ã  priori)
        <nom>_multi_ombrage.tif     ombrage L93, 0.5 m/px
        <nom>_multi_ombrage_tuilage_z18.tif  cache Mercator (rÃ©utilisable)
        <nom>_multi_ombrage_z8-18.mbtiles
        <nom>_multi_ombrage_z8-18.rmap
        <nom>_multi_ombrage_z8-18.sqlitedb
    cache/ign_lidar/                cache dalles IGN permanent (partagÃ©)

  Temps indicatifs (zone 4 kmÂ², i3-8130U) :
    TÃ©lÃ©chargement (9-12 dalles)       : ~30 s
    Ombrage multi (gdaldem)            : ~5-10 s
    Ombrage SVF (numpy, 4 kmÂ²)         : ~5 min
    Ombrage LRM (scipy)                : ~2 min
    Ombrage RRIM (SVF + slope)         : ~8 min
    MBTiles z8-18 (495 tuiles)         : ~5 s
    MBTiles z8-18 (zone 400 kmÂ²)       : ~5-10 min

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODE --ignraster
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  TÃ©lÃ©charge des tuiles WMTS IGN dans un MBTiles.
  Cache tuiles dans ign_raster/<nom>/dalles/<z>/<x>/<y>.<ext>.

  Couches disponibles :
    planign     Plan IGN v2 (png, public, z6-18)              â† recommandÃ© particuliers
    etatmajor40 Ã‰tat-Major 1/40000 (jpeg, public, z6-15)
    etatmajor10 Ã‰tat-Major 1/10000 (jpeg, public, z8-16)
    pentes      Carte des pentes (png, public, z6-14)
    ortho       Orthophotos actuelles (jpeg, public, z10-20)
    ortho_1950  Orthos historiques 1950-1965 (png, z10-18)    â† archÃ©o, exploration
    ortho_1965  Orthos historiques 1965-1980 (png, z10-18)
    ortho_1980  Orthos historiques 1980-1995 (png, z10-18)
    ortho_irc   Orthos infrarouge couleur (jpeg, z10-19)      â† vÃ©gÃ©tation, humiditÃ© sol
    pleiades    Satellite PlÃ©iades 50cm 2024 (jpeg, z10-19)
    spot        Satellite SPOT 1.5m 2024 (jpeg, z8-16)
    cadastre    Parcellaire express (png, public, z12-19)
    ombrage     Ombrage IGN (png, public, z6-14)
    edugeo_marseille_*  Orthos historiques Marseille-Martigues
                  (1969, 1980, 1987, 1988, 2010 â€” emprise urbaine restreinte)
    edugeo_toulon_1972  Ortho historique Toulon-HyÃ¨res 1972 (emprise urbaine)
    scan25      Scan 25 000 (jpeg, z8-18)    âš  PRO â€” clÃ© API requise
    scan25tour  Scan 25 Tourisme (jpeg, z8-18) âš  PRO â€” clÃ© API requise
    scan100     Scan 100 000 (jpeg, z6-14)   âš  PRO â€” clÃ© API requise
    scanoaci    Scan OACI (jpeg, z6-15)       âš  PRO â€” clÃ© API requise

  Note : scan25 au-delÃ  de z16 â†’ IGN bascule automatiquement vers planIGN.
  Note : orthos historiques â€” couverture variable selon dÃ©partement/pÃ©riode.
    Pour la PACA : 1950-1965 et 1965-1980 gÃ©nÃ©ralement disponibles, mais
    tester d'abord sur petite zone. Si la couche est vide Ã  votre date sur
    votre dÃ©partement, le tÃ©lÃ©chargement renverra des tuiles transparentes.
  âš  Les couches Scan sont rÃ©servÃ©es aux professionnels (CGU IGN).
    Compte sur cartes.gouv.fr avec SIRET requis. Les particuliers doivent
    utiliser planign ou ortho, accessibles sans clÃ©.

  ParamÃ¨tres spÃ©cifiques :
    --couche NOM        Couche WMTS (dÃ©faut: scan25)
    --apikey CLE        ClÃ© API IGN â€” rÃ©servÃ©e aux professionnels (scan* uniquement)
                          Vide par dÃ©faut. Variable d'env IGN_APIKEY aussi acceptÃ©e.
    --zoom-min N        Zoom minimum (dÃ©faut: selon couche)
    --zoom-max N        Zoom maximum (dÃ©faut: selon couche)
    --workers N         Connexions parallÃ¨les (dÃ©faut: 8)
    --cols-decoupe N    DÃ©coupe le MBTiles final en N colonnes (avec --rows-decoupe)
    --rows-decoupe N    DÃ©coupe le MBTiles final en N lignes   (avec --cols-decoupe)
    --rayon-decoupe KM  Alternative : dÃ©coupe en carrÃ©s de ~KM km
    --source CHEMIN     .mbtiles existant â†’ conversion RMAP/SQLiteDB directe

  Arborescence de sortie :
    Projets/<nom>/
      ign_raster/
        <nom>_scan25_z8-18.mbtiles
        <nom>_scan25_z8-18.rmap
        <nom>_scan25_z8-18.sqlitedb
    cache/ign_raster/               cache tuiles WMTS permanent (partagÃ©)

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODE --ignvecteur
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  TÃ©lÃ©charge des couches WFS IGN vers GeoJSON(.gz).

  Couches disponibles :
    cadastre          Parcelles cadastrales
    cours_eau         Cours d'eau (hydrographie)
    detail_hydro      Hydrographie dÃ©taillÃ©e
    bati              BÃ¢timents (BDTOPO)
    voie_ferre        Voies ferrÃ©es
    (typename complet acceptÃ© directement)

  ParamÃ¨tres :
    --couche NOM...     Couche(s) Ã  tÃ©lÃ©charger (multi-valeurs)
    --workers N         Connexions parallÃ¨les (dÃ©faut: 4)
    --formats-fichier   geojson | gz (dÃ©faut: gz)

  Arborescence de sortie :
    ign_vecteur/
      <nom>/
        <nom>_cadastre.geojson.gz
        <nom>_cours_eau.geojson.gz

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODE --osm
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  PBF Geofabrik â†’ carte Mapsforge (.map) + GeoJSON de superposition.
  Utilise osmosis + plugin mapwriter (tÃ©lÃ©chargÃ©s automatiquement).
  Le PBF filtrÃ© <nom>_filtered.pbf est conservÃ© pour la rÃ©utilisation.

  ParamÃ¨tres :
    --source CHEMIN     PBF source (tÃ©lÃ©chargÃ© depuis Geofabrik si absent)
    --couche TAGS       Tags OSM inclus (dÃ©faut: rando)
                          ex: "highway=* waterway=* natural=water"
    --formats-fichier   map geojson gz (dÃ©faut: map gz)

  Arborescence de sortie :
    osm_vecteur/
      provence-alpes-cote-d-azur-latest.osm.pbf   (cache rÃ©gional)
      <nom>/
        <nom>.map                  carte Mapsforge
        <nom>_filtered.pbf         PBF filtrÃ© (rÃ©utilisable)
        <nom>_osm.geojson.gz       GeoJSON de superposition

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  MODE --fusionner
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Fusionne plusieurs GeoJSON(.gz) en un seul fichier.
  Ajoute la propriÃ©tÃ© 'source' = nom du fichier source.

  ParamÃ¨tres :
    --source FICHIER...   Fichiers GeoJSON/.gz Ã  fusionner (glob acceptÃ©)
    --sortie FICHIER      Fichier de sortie (dÃ©faut: dossier du 1er fichier)
    --formats-fichier     geojson | gz (dÃ©faut: gz)

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  PARAMÃˆTRES COMMUNS
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  --dossier CHEMIN      Racine de sortie (dÃ©faut: Projets/<nom>/)
  --oui                 Mode non-interactif (pas de questions)
  --nettoyage           Supprimer les fichiers intermÃ©diaires aprÃ¨s chaque
                          morceau (dalles, TIF ombrages, TIF warpÃ©).
                          Conserve les sorties finales (.mbtiles .rmap .sqlitedb).
                          Indispensable pour les grandes zones (dÃ©partement entier).
  --version             Afficher la version

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  GUI (mode interactif sans arguments)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Lancer sans argument : python lidar2map.py
  Onglets : LiDAR MNT, IGN Raster, IGN Vecteur, OSM Vecteur, Fusion, DÃ©coupage.

  FonctionnalitÃ©s :
    â€¢ Historique : 50 derniÃ¨res commandes, rappel par clic, vidable
    â€¢ Zoom interface : Ctrl+molette (Windows/macOS), Ctrl++/Ctrl+-
    â€¢ Annulation : 1er Ctrl+C demande l'arrÃªt propre, 2nd force la sortie
    â€¢ Logs en temps rÃ©el + erreurs en boÃ®te de dialogue Ã  la fin
    â€¢ Validation des paramÃ¨tres : zoom_min â‰¤ zoom_max, etc.

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  DÃ‰COUPAGE Ã€ PRIORI (--ignlidar et --ignraster uniquement)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Modes raster uniquement. Les modes vectoriels (--ignvecteur, --osm,
  --fusionner) n'en ont pas besoin : leurs donnÃ©es sont lÃ©gÃ¨res et ne
  saturent pas la RAM ni le disque.

  Principe : traitement sÃ©quentiel morceau par morceau avec reprise
  automatique. Un fichier manifeste.json enregistre l'Ã©tat de chaque
  morceau. En cas d'interruption, relancer la mÃªme commande reprend
  exactement lÃ  oÃ¹ le traitement s'est arrÃªtÃ©.

  --cols-decoupe N      Colonnes de la grille (Est-Ouest)
  --rows-decoupe N      Lignes de la grille (Nord-Sud)
                          Ce mÃªme paramÃ¨tre sert Ã  la fois au dÃ©coupage
                          Ã  priori (traitement sÃ©quentiel par morceaux)
                          et au dÃ©coupage des fichiers de sortie.
  --nettoyage           Supprimer dalles + TIF intermÃ©diaires aprÃ¨s chaque
                          morceau. Indispensable pour les grandes zones
                          (dÃ©partement entier).

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  DÃ‰PENDANCES
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  Python 3.8+    Python 3.12+ recommandÃ© pour les patches sÃ©curitÃ© tarfile.
                 DÃ©pendances pip auto-installÃ©es au 1er lancement :
                   Pillow, pyproj, numpy, scipy, ijson, certifi
                 Optionnelles (auto-installÃ©es Ã  la demande) :
                   numba (accÃ©lÃ©ration SVF ~15Ã—), py7zr (BD TOPO bulk),
                   mapbox-vector-tile (lecture vector tiles)

  GDAL           Plus de dÃ©pendance GDAL systÃ¨me requise depuis le refactor
                 rasterio (Ã©tapes 1-7). Tous les outils (gdalinfo, gdalwarp,
                 gdaldem, gdalbuildvrt, gdal_translate, gdaladdo, ogr2ogr)
                 sont remplacÃ©s par rasterio.warp / rasterio.merge / numpy /
                 fiona, dont les wheels pip embarquent leur propre libgdal.
                 â†’ Plus aucun `brew install gdal` ni GISInternals Ã  tÃ©lÃ©charger.

  osmosis        TÃ©lÃ©chargÃ© dans ~/.lidar2map/osmosis/ (toutes plateformes)
                 PartagÃ© entre tous les dossiers oÃ¹ le script est lancÃ©.
  JRE Temurin 21 TÃ©lÃ©chargÃ© dans ~/.lidar2map/jre/
                   Windows x64 : zip   |   macOS x64/arm64 : tar.gz
                   Linux x64/arm64 : tar.gz
                 Pour nettoyer complÃ¨tement le runtime : rm -rf ~/.lidar2map
  mapwriter      TÃ©lÃ©chargÃ© automatiquement (plugin osmosis)

  GUI (mode sans arguments) :
                 Windows : WebView2 natif (prÃ©installÃ© Win10+)
                 macOS   : PyQt6 + PyQt6-WebEngine + qtpy (auto-installÃ©s)
                           pyobjc-framework-WebKit (backend natif, optionnel)
                 Linux   : PyQt6 + PyQt6-WebEngine + qtpy (auto-installÃ©s via pip)
                           PrÃ©-requis systÃ¨me (Ubuntu/Debian, une seule fois) :
                             sudo apt install python3-venv
                           voir messages au dÃ©marrage si import Ã©choue)

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
  EXEMPLES
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

  # Mode GUI
  python lidar2map.py

  # LiDAR : zone 1 km, ombrage multi, MBTiles + RMAP + SQLiteDB
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 1 \
      --zone-nom aa --telechargement --ombrages multi \
      --formats-fichier mbtiles rmap sqlitedb --zoom-min 8 --zoom-max 18 --oui

  # LiDAR : zone 10 km, plusieurs ombrages
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 10 \
      --zone-nom gareoult --telechargement --ombrages multi slope svf lrm \
      --formats-fichier mbtiles rmap --qualite-image 75 --oui

  # LiDAR : depuis TIF existant â†’ RMAP uniquement
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 1 \
      --zone-nom aa --source ign_lidar/aa/_warped_aa_multi_ombrage_z18.tif \
      --formats-fichier rmap --zoom-min 8 --zoom-max 18 --oui

  # IGN Raster public (pas de clÃ© requise)
  python lidar2map.py --ignraster --zone-ville gareoult --zone-rayon 10 \
      --zone-nom aa --couche planign \
      --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18 --oui

  # IGN Raster Scan 25 (professionnel uniquement â€” clÃ© API requise)
  # python lidar2map.py --ignraster --zone-ville gareoult --zone-rayon 10 \
  #     --zone-nom aa --couche scan25 --apikey VOTRE_CLE_PRO \
  #     --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18 --oui

  # Vecteur IGN : cadastre + hydrographie
  python lidar2map.py --ignvecteur --zone-ville gareoult --zone-rayon 5 \
      --zone-nom aa --couche cadastre cours_eau detail_hydro --oui

  # OSM : carte rando + GeoJSON
  python lidar2map.py --osm --zone-ville gareoult --zone-rayon 10 \
      --zone-nom aa --couche "highway=* waterway=* natural=water" \
      --formats-fichier map gz --oui

  # Fusion GeoJSON
  python lidar2map.py --fusionner \
      --source ign_vecteur/aa/*.geojson.gz osm_vecteur/aa/*.geojson.gz \
      --formats-fichier gz --oui

  # Zone par dÃ©partement entier (Var)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --workers 8 --ombrages multi --formats-fichier mbtiles --oui

  # DÃ©coupage Ã  priori : grande zone en 4Ã—4 morceaux avec nettoyage disque
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage --oui

  # Reprise aprÃ¨s interruption (mÃªme commande â€” les morceaux terminÃ©s sont ignorÃ©s)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage --oui

  # Linux/macOS : la commande est identique, sauf 'python' â†’ 'python3'
  python3 lidar2map.py --ignlidar --zone-ville Gareoult --zone-rayon 1 \
      --ombrages svf --formats-fichier mbtiles --oui
"""
import os
import re
import sys
import ssl

# certifi fournit un bundle de certificats CA Ã  jour, indispensable sur
# Windows 11 et macOS oÃ¹ les certificats systÃ¨me sont parfois absents ou
# pÃ©rimÃ©s (erreur "certificate verify failed" sur les API IGN).
#
# ProblÃ¨me d'Å“uf/poule : cet import arrive AVANT _bootstrap_environnement()
# (ligne ~1088), donc avant que l'auto-installeur ait pu installer certifi.
# On protÃ¨ge donc l'import par un try/except :
#   â€¢ certifi dÃ©jÃ  installÃ© (cas normal aprÃ¨s le 1er lancement)  â†’ setup complet
#   â€¢ certifi absent (tout 1er lancement, Python nu)             â†’ fallback propre
#     Le bootstrap installe certifi juste aprÃ¨s, puis re-exÃ©cute le script
#     (mode auto/venv) ou l'import rÃ©ussira dÃ¨s le prochain appel (mode pip).
try:
    import certifi as _certifi
    os.environ['SSL_CERT_FILE']       = _certifi.where()
    os.environ['REQUESTS_CA_BUNDLE']  = _certifi.where()
except ImportError:
    # certifi absent : on laisse Python utiliser ses certificats systÃ¨me.
    # Sur macOS, cela peut provoquer "certificate verify failed" pour les API
    # IGN, mais uniquement lors du tout premier lancement (avant l'install).
    # Le patch ssl._create_default_https_context ci-dessous sert de filet
    # de sÃ©curitÃ© dans ce cas transitoire.
    pass

# Patch SSL de dernier recours : certaines bibliothÃ¨ques ignorent les
# variables d'environnement SSL_CERT_FILE. Ce patch remplace le contexte
# SSL par dÃ©faut de Python par un contexte non-vÃ©rifiant, ce qui garantit
# que les tÃ©lÃ©chargements pip (bootstrap) rÃ©ussissent mÃªme si les certificats
# systÃ¨me sont pÃ©rimÃ©s. Il sera surchargÃ© par certifi une fois installÃ©.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


# Forcer stdout/stderr en UTF-8 dÃ¨s le dÃ©marrage. Sur Windows la code page
# console est cp1252 par dÃ©faut ; sans cette reconfigure, les caractÃ¨res
# accentuÃ©s et symboles (Ã©, âœ“, â†’) sont Ã©crits en cp1252 et apparaissent en
# mojibake quand la sortie est capturÃ©e par un pipe parent qui dÃ©code en UTF-8
# (cas du mode frozen GUI â†’ CLI subprocess). PYTHONIOENCODING=utf-8 ne suffit
# pas toujours dans un exe PyInstaller. Doit s'exÃ©cuter AVANT le premier print.
for _std in ("stdout", "stderr"):
    _s = getattr(sys, _std, None)
    if _s is not None and getattr(_s, "encoding", "").lower() != "utf-8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MODE LAUNCHER (build onefile)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Le mÃªme lidar2map.py est buildÃ© en DEUX versions :
#   1) onedir (lidar2map_win.spec)        : la vraie app, ~617 Mo, lente Ã  packager
#      mais rapide Ã  lancer. C'est ce qui tourne au final.
#   2) onefile (lidar2map_win_launcher.spec) : un petit launcher qui contient le onedir
#      zippÃ© en ressource. Ã€ l'exÃ©cution il extrait dans %LOCALAPPDATA%\lidar2map
#      (avec contrÃ´le SHA pour dÃ©tecter les mises Ã  jour), puis spawn le vrai exe
#      onedir avec une sentinelle pour qu'il saute ce bloc.
#
# Le launcher se distingue Ã  l'exÃ©cution :
#   - PyInstaller onefile : sys._MEIPASS contient lidar2map_bundle.zip
#   - L'inner spawnÃ© a la sentinelle _INNER_FLAG dans sys.argv
_INNER_FLAG = "--__lidar2map_inner__"
if getattr(sys, "frozen", False):
    if _INNER_FLAG in sys.argv:
        # On est l'exe interne : retirer la sentinelle puis continuer normalement
        sys.argv.remove(_INNER_FLAG)
    else:
        # On est peut-Ãªtre le launcher : vÃ©rifier la prÃ©sence du bundle
        import hashlib, zipfile, platform as _platform
        from pathlib import Path as _Path

        # Ordre de recherche du bundle :
        #   1. Ã€ cÃ´tÃ© de l'exe / dans Contents/Resources/ (bundle fichier sÃ©parÃ©)
        #   2. Dans sys._MEIPASS (bundle embarquÃ©, fallback ancienne archi)
        _exe = _Path(sys.executable).resolve()
        _sys = _platform.system()   # une seule dÃ©tection, rÃ©utilisÃ©e partout

        if _sys == "Darwin" and ".app" in str(_exe):
            _bundle = _exe.parent.parent / "Resources" / "lidar2map_bundle.zip"
        else:
            _bundle = _exe.parent / "lidar2map_bundle.zip"

        # Fallback _MEIPASS â€” uniquement si non vide (Path("") = cwd, ambigu)
        if not _bundle.exists():
            _meipass_str = getattr(sys, "_MEIPASS", None)
            if _meipass_str:
                _bundle = _Path(_meipass_str) / "lidar2map_bundle.zip"

        if _bundle.exists():
            # Dossier d'extraction : chemins systÃ¨me standard par OS.
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

            # â”€â”€ --desinstaller interceptÃ© dans le launcher â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # TraitÃ© ici AVANT tout calcul de SHA ou extraction.
            # Le launcher supprime tout directement (venv, osmosis, jre, bundle
            # extrait) sans re-spawner â€” Ã©vite l'infinite loop.
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
                print("  â”€â”€ DÃ©sinstallation lidar2map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
                print()
                _total_u = 0
                for _c_u, _label_u in _cibles_u:
                    if _c_u.exists():
                        _taille_u = sum(
                            f.stat().st_size for f in _c_u.rglob("*") if f.is_file()
                        )
                        _total_u += _taille_u
                        print(f"  Suppression {_label_u} ({_taille_u / 1e6:.0f} Mo)")
                        print(f"    {_c_u}")
                        _sh_u.rmtree(_c_u, ignore_errors=True)
                        print(f"    {'âœ“ supprimÃ©' if not _c_u.exists() else 'âš  partiel'}")
                    else:
                        print(f"  {_label_u} : absent ({_c_u})")
                print()
                print(f"  {_total_u / 1e6:.0f} Mo libÃ©rÃ©s.")
                print()
                print("  Note : lidar2map.py, le .app/.exe et le zip ne sont pas supprimÃ©s.")
                print("  Supprimez-les manuellement si nÃ©cessaire.")
                sys.exit(0)

            def _bundle_sha():
                h = hashlib.sha256()
                with open(_bundle, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                return h.hexdigest()

            # â”€â”€ DÃ©tection de mise Ã  jour avec cache mtime â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Calculer le SHA256 d'un zip de 300 Mo prend ~0.5-1 s Ã  chaque
            # lancement. On stocke le mtime du bundle dans le fichier SHA pour
            # Ã©viter ce calcul quand le bundle n'a pas changÃ©.
            # Format de _sha_file : "sha256hex\nmtime_float"
            _need_extract = True
            if _sha_file.exists() and _inner_exe.exists() and not _inner_exe.is_dir():
                try:
                    _sha_lines     = _sha_file.read_text(encoding="utf-8").strip().split("\n")
                    _saved_sha     = _sha_lines[0]
                    _saved_mtime   = float(_sha_lines[1]) if len(_sha_lines) > 1 else 0.0
                    _current_mtime = _bundle.stat().st_mtime
                    if abs(_current_mtime - _saved_mtime) < 0.01:
                        # mtime identique â†’ bundle inchangÃ© â†’ pas d'extraction
                        _need_extract = False
                    else:
                        # mtime changÃ© â†’ vÃ©rifier SHA pour confirmer
                        _expected_sha = _bundle_sha()
                        _need_extract = (_expected_sha != _saved_sha)
                except Exception:
                    _need_extract = True   # sha_file corrompu â†’ rÃ©-extraire

            if _need_extract:
                _expected_sha = _bundle_sha()   # calcul SHA si pas encore fait

            # DÃ©tection robuste : si le zip a Ã©tÃ© crÃ©Ã© avec --keepParent,
            # l'extraction crÃ©e un sous-dossier lidar2map/ â†’ l'exe est un niveau
            # plus bas. On corrige automatiquement.
            def _resolve_exe(exe):
                if exe.exists() and exe.is_dir():
                    deeper = exe / exe.name
                    if deeper.exists() and not deeper.is_dir():
                        return deeper
                return exe

            if _need_extract:
                # Lockfile contre les extractions simultanÃ©es (double-clic)
                import time as _time
                if _lock.exists():
                    print("Installation en cours dans une autre instance â€” attente...",
                          flush=True)
                    for _ in range(60):
                        _time.sleep(1)
                        if not _lock.exists():
                            break
                    # Re-vÃ©rifier que l'autre instance a bien terminÃ© : un
                    # crash mid-extraction laisserait un _inner_exe absent ou
                    # un _sha_file manquant. Si l'Ã©tat n'est pas sain, on
                    # abandonne plutÃ´t que de spawner un binaire incomplet.
                    _inner_check = _resolve_exe(_inner_exe)
                    if _inner_check.exists() and _sha_file.exists():
                        _need_extract = False
                    else:
                        print("  âš  Installation concurrente incomplÃ¨te ou Ã©chouÃ©e.",
                              flush=True)
                        print("  Supprimez le lockfile et relancez :",
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
                        print(f"Premier lancement â€” installation ({_bundle_size // 1_000_000} Mo)...",
                              flush=True)
                        # Suivi : ditto sur Mac prÃ©serve les permissions
                        # exÃ©cutables, mais zipfile.extractall (utilisÃ© par le
                        # fallback Darwin et le chemin Linux) les perd â†’ on
                        # remet le bit +x sur l'exe aprÃ¨s extraction si on est
                        # passÃ© par zipfile.
                        _used_zipfile = False
                        if _sys == "Darwin":
                            import subprocess as _sp_d
                            _r = _sp_d.run(["ditto", "-x", "-k",
                                            str(_bundle), str(_app_dir)],
                                           capture_output=True)
                            if _r.returncode != 0:
                                # Fallback zipfile si ditto Ã©choue : validation
                                # dÃ©fensive contre zip-slip (le bundle est
                                # notre artefact, mais on dÃ©fend par principe).
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
                            # Validation dÃ©fensive contre zip-slip.
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
                                    # rÃ©applique â†’ prÃ©serve +x sur tous les
                                    # binaires bundlÃ©s (QtWebEngineProcess,
                                    # JRE java, osmosis, â€¦).
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

                        # Filet de sÃ©curitÃ© : si le zip a Ã©tÃ© crÃ©Ã© sans
                        # permissions POSIX (external_attr == 0, ex: Windows),
                        # forcer au moins +x sur l'exe interne pour qu'il
                        # puisse Ãªtre spawnÃ©.
                        if _used_zipfile and _sys != "Windows":
                            import stat as _stat
                            _inner_exe_resolved = _resolve_exe(_inner_exe)
                            if _inner_exe_resolved.exists():
                                _inner_exe_resolved.chmod(
                                    _inner_exe_resolved.stat().st_mode
                                    | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)

                        # VÃ©rifier que l'exe interne existe avant d'Ã©crire le SHA
                        # (ditto peut retourner 0 avec une extraction incomplÃ¨te)
                        _inner_resolved = _resolve_exe(_inner_exe)
                        if not _inner_resolved.exists():
                            raise RuntimeError(
                                f"Extraction incomplÃ¨te : {_inner_exe} introuvable")

                        _sha_file.write_text(
                            f"{_expected_sha}\n{_bundle.stat().st_mtime}",
                            encoding="utf-8")
                        print("Installation terminÃ©e.", flush=True)
                    except Exception as _e_extract:
                        print(f"\n  âš  Erreur d'extraction : {_e_extract}", flush=True)
                        print("  Relancez l'application pour rÃ©essayer.", flush=True)
                        sys.exit(1)
                    finally:
                        _lock.unlink(missing_ok=True)

            # RÃ©soudre le vrai chemin de l'exe (gÃ¨re --keepParent)
            _inner_exe = _resolve_exe(_inner_exe)

            # â”€â”€ LIDAR2MAP_WORK_DIR : dossier contenant le .app/.exe â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Sur macOS, sys.executable est dans .app/Contents/MacOS/ â†’
            # remonter jusqu'au dossier parent du .app pour que les fichiers
            # utilisateur (Projets/, logs/, cache/) soient crÃ©Ã©s Ã  cÃ´tÃ© du .app.
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
        # Pas de bundle.zip â†’ exe onedir lancÃ© directement â†’ continuer.

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

# VÃ©rification version Python
if sys.version_info < (3, 8):
    print("ERREUR : Python 3.8 minimum requis (version actuelle : "
          + str(sys.version_info.major) + "." + str(sys.version_info.minor) + ")")
    print("TÃ©lÃ©chargez Python 3.8+ sur https://www.python.org/downloads/")
    sys.exit(1)

# ============================================================
# INSTALLATION AUTOMATIQUE DES DÃ‰PENDANCES
# ============================================================

def _resoudre_mode_bootstrap():
    """DÃ©termine le mode de bootstrap (auto|pip|none) et nettoie sys.argv.

    Source de vÃ©ritÃ© unique pour le mode â€” appelÃ©e par _bootstrap_environnement
    avant tout autre travail d'init. Avant ce refactor le mode Ã©tait rÃ©solu
    en interne dans _bootstrap_venv_si_besoin, ce qui empÃªchait l'orchestrateur
    de conditionner les autres appels (pip, install_deps) sur ce mode.

    PrioritÃ© (du plus faible au plus fort) :
      1. DÃ©faut          : "auto"
      2. Variable d'env  : LIDAR2MAP_BOOTSTRAP={auto|pip|none}
      3. Argument CLI    : --bootstrap={auto|pip|none}
      4. Aliases legacy  : --no-bootstrap â†’ none, --venv â†’ auto, --no-venv â†’ pip

    Effet de bord : retire de sys.argv tous les flags consommÃ©s (pour qu'ils
    n'arrivent pas Ã  argparse plus loin).
    """
    mode = "auto"   # dÃ©faut

    # Variable d'env (prioritÃ© basse)
    env_mode = os.environ.get("LIDAR2MAP_BOOTSTRAP", "").lower().strip()
    if env_mode in ("auto", "pip", "none"):
        mode = env_mode

    # Argument CLI (prioritÃ© haute) â€” supporte --bootstrap=X et --bootstrap X
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

    # CompatibilitÃ© descendante avec les anciens flags
    if "--no-bootstrap" in sys.argv:
        mode = "none"
    if "--venv" in sys.argv:
        mode = "auto"  # = venv (qui est dÃ©sormais le dÃ©faut)
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
    """Retourne les dÃ©pendances GUI spÃ©cifiques Ã  la plateforme.

    pywebview a besoin d'un backend graphique natif selon l'OS :

      Windows  WebView2 natif (EdgeHTML/Chromium), prÃ©-installÃ© depuis Win10.
               Aucune dÃ©pendance pip supplÃ©mentaire.

      macOS    Backend natif Cocoa/WebKit via pyobjc (lÃ©ger, ~20 Mo).
               pyobjc est inclus avec Python installÃ© depuis python.org, mais
               PAS avec Homebrew, conda, pyenv ou miniforge. Dans ce cas,
               pywebview ne trouve pas de backend et plante au lancement.
               â†’ On installe pyobjc-framework-WebKit en prioritÃ© (natif).
               â†’ Si pyobjc est dÃ©jÃ  prÃ©sent, rien n'est installÃ© (pas de Qt).
               â†’ Qt (PyQt6) est en fallback uniquement si pyobjc Ã©choue
                 (cas rare : macOS trÃ¨s ancien, architecture non supportÃ©e).

      Linux    Pas de backend natif. Qt (PyQt6 + PyQt6-WebEngine + qtpy) est
               le seul backend disponible via pip de faÃ§on fiable.
               GTK est une alternative thÃ©orique mais ses wheels pip sont
               inexistants ou cassÃ©s â€” on l'Ã©vite.

    Retourne (critiques, optionnelles) :
      critiques    : installÃ©es systÃ©matiquement, bloquantes si Ã©chec total
      optionnelles : tentÃ©es une par une, non bloquantes si Ã©chec
    """
    _sys = platform.system()
    if _sys == "Darwin":
        # macOS : on installe TOUJOURS les deux backends.
        # â€¢ pyobjc (Cocoa/WebKit natif) : lÃ©ger, fonctionne sur Mac avec display
        # â€¢ PyQt6 : requis quand la machine est headless (VM SSH, Scaleway M1)
        #   NB : on ne peut pas savoir au moment du bootstrap si le Mac aura
        #   un display au moment de l'exÃ©cution â€” donc on installe Qt
        #   systÃ©matiquement plutÃ´t que de le laisser en fallback optionnel.
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
        # Windows : WebView2 natif, rien Ã  installer.
        return ([], [])


def _verifier_venv_linux():
    """Sur Linux/Ubuntu, vÃ©rifie que le module venv est disponible.

    Sur Debian/Ubuntu, python3-venv est un paquet systÃ¨me SÃ‰PARÃ‰ de python3
    (dÃ©cision de packaging Debian). Il est donc absent sur un Python nu, ce
    qui fait planter la crÃ©ation de venv sans message clair.

    Cette fonction est appelÃ©e AVANT toute tentative de crÃ©ation de venv.
    Elle dÃ©tecte l'absence du module et imprime les instructions apt.
    """
    if platform.system() != "Linux":
        return
    try:
        import venv as _venv_test  # noqa: F401
        return  # module prÃ©sent, tout va bien
    except ImportError:
        pass
    # DÃ©tecter aussi via subprocess pour couvrir les cas oÃ¹ le module
    # est prÃ©sent mais pas importable depuis le Python courant.
    r = subprocess.run(
        [sys.executable, "-m", "venv", "--help"],
        capture_output=True)
    if r.returncode == 0:
        return  # disponible
    # Module absent : message clair et arrÃªt propre
    _py = f"python{sys.version_info.major}.{sys.version_info.minor}"
    print()
    print("  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—")
    print("  â•‘  ERREUR : module Python 'venv' absent                        â•‘")
    print("  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
    print()
    print("  Sur Ubuntu/Debian, ce module est dans un paquet sÃ©parÃ©.")
    print("  Installez-le avec (une seule fois) :")
    print()
    print(f"    sudo apt install python3-venv")
    print(f"    # ou, si vous utilisez Python {sys.version_info.major}.{sys.version_info.minor} explicitement :")
    print(f"    sudo apt install {_py}-venv")
    print()
    print("  Puis relancez le script.")
    sys.exit(1)


def _bootstrap_venv_si_besoin():
    """Bootstrap automatique d'un environnement Python isolÃ©.

    Comportement par dÃ©faut : crÃ©e un venv dans ``~/.lidar2map/`` (Mac/Linux)
    ou ``%USERPROFILE%\\.lidar2map\\`` (Windows) au 1er lancement, y installe
    les dÃ©pendances, et y relance le script. Comportement uniforme sur les 3 OS.

    Avantages du venv par dÃ©faut sur toutes plateformes :
      - Isolation : zÃ©ro pollution du Python systÃ¨me
      - DÃ©sinstallation propre : suppression d'un dossier suffit
      - CohÃ©rent avec la bonne pratique Python (un venv par projet)
      - Ã‰vite les conflits de versions de modules avec d'autres outils
      - Contourne PEP 668 sur Mac/Linux rÃ©cents nativement

    Flags utilisateur (lus directement depuis sys.argv pour bypasser argparse
    qui n'est pas encore initialisÃ© Ã  ce stade du dÃ©marrage) :

      --bootstrap=auto    : venv automatique (dÃ©faut, recommandÃ©)
      --bootstrap=pip     : install directe dans l'env Python courant
                            (utilise --break-system-packages si PEP 668)
      --bootstrap=none    : pas d'install â€” vÃ©rifie les imports et plante
                            avec un message clair si manquants. Utile pour
                            ceux qui gÃ¨rent leur propre env (conda, venv
                            manuel, install systÃ¨me contrÃ´lÃ©e).
      --help-bootstrap    : affiche cette aide et quitte

    Variables d'environnement Ã©quivalentes :
      LIDAR2MAP_BOOTSTRAP=auto|pip|none

    Suppression du venv Ã  tout moment :
      rm -rf ~/.lidar2map                       (Mac/Linux)
      rmdir /s /q %USERPROFILE%\\.lidar2map     (Windows)
    Le script en recrÃ©era un au prochain lancement si besoin.
    """
    mode = _resoudre_mode_bootstrap()

    # Deps rÃ©ellement critiques pour le pipeline LiDAR principal.
    # numba et osmium sont optionnelles (numba accÃ©lÃ¨re SVF, osmium pour
    # OSMâ†’GeoJSON) â€” leur absence ne doit pas planter le bootstrap.
    deps_critiques = ["PIL", "pyproj", "numpy", "scipy", "ijson",
                      "rasterio", "fiona", "certifi"]

    # â”€â”€ Mode "none" : juste vÃ©rifier les imports, planter clairement si KO â”€
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
            print("  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—")
            print("  â•‘  Mode --bootstrap=none : auto-install dÃ©sactivÃ©              â•‘")
            print("  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
            print(f"  Modules Python manquants : {', '.join(manquantes)}")
            print()
            print("  Installez-les vous-mÃªme via votre mÃ©thode prÃ©fÃ©rÃ©e :")
            print(f"    pip install {' '.join(pkgs_pip)} pywebview")
            print(f"    # ou : conda install -c conda-forge {' '.join(pkgs_pip)} pywebview")
            print()
            sys.exit(1)
        return

    # â”€â”€ Mode "pip" : install dans l'env Python courant â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # DÃ©lÃ©guÃ© Ã  _installer_deps() plus bas (avec stratÃ©gie 3 niveaux :
    # standard â†’ --break-system-packages â†’ --user)
    if mode == "pip":
        return  # rien Ã  faire ici, _installer_deps() prend le relais

    # â”€â”€ Mode "auto" : crÃ©er/utiliser un venv â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Tout le runtime lidar2map (venv Python, JRE Java, osmosis, etc.) est
    # centralisÃ© dans ~/.lidar2map/ â€” un seul dossier Ã  supprimer pour
    # un nettoyage complet, et partagÃ© entre tous les dossiers de travail.
    is_windows  = platform.system() == "Windows"
    lidar_home  = Path.home() / ".lidar2map"
    venv_path   = lidar_home / "venv"

    # DÃ©tecter si on est dÃ©jÃ  dans le bon venv (rÃ©-entrance aprÃ¨s os.execv)
    try:
        if Path(sys.prefix).resolve() == venv_path.resolve():
            return
    except Exception:
        pass

    # NB : on ne shortcut PAS sur "deps importables dans le Python courant".
    # Avant ce refactor, la prÃ©sence des deps quelque part dans le sys.path
    # courant (systÃ¨me, conda, autre venv) faisait que ~/.lidar2map/venv
    # n'Ã©tait jamais crÃ©Ã© â†’ comportement non-dÃ©terministe selon l'historique
    # de la machine. Maintenant, le mode "auto" crÃ©e toujours le venv.
    # Pour utiliser un autre env, passer explicitement par :
    #   --bootstrap=pip   (install dans l'env Python courant)
    #   --bootstrap=none  (assume que tout est dÃ©jÃ  lÃ )

    # Sous Windows : Scripts/ au lieu de bin/
    venv_bin    = venv_path / ("Scripts" if is_windows else "bin")
    venv_python = venv_bin / ("python.exe" if is_windows else "python")
    venv_pip    = venv_bin / ("pip.exe"    if is_windows else "pip")

    # Si le venv existe dÃ©jÃ  avec les dÃ©ps : juste re-exÃ©cuter dedans
    if venv_python.exists():
        check_cmd = [str(venv_python), "-c",
                     "import " + ", ".join(deps_critiques)]
        r_check = subprocess.run(check_cmd, capture_output=True)
        if r_check.returncode == 0:
            print(f"  Relance dans le venv : {venv_path}")
            _relancer_dans_venv(venv_python, is_windows)
            # Ne retourne pas â€” soit os.execv (Unix), soit sys.exit (Windows)

    # CrÃ©er le venv s'il n'existe pas encore
    if not venv_python.exists():
        # Sur Linux/Ubuntu : vÃ©rifier python3-venv AVANT de tenter la crÃ©ation
        _verifier_venv_linux()
        suppr_cmd = ("rmdir /s /q %USERPROFILE%\\.lidar2map" if is_windows
                     else "rm -rf ~/.lidar2map")
        print()
        print("  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—")
        print("  â•‘  Premier lancement â€” crÃ©ation d'un environnement Python      â•‘")
        print("  â•‘  isolÃ© (~50 Mo une fois les dÃ©ps installÃ©es). Cet env est    â•‘")
        print("  â•‘  local au projet et ne touche pas votre Python systÃ¨me.      â•‘")
        print("  â•‘                                                              â•‘")
        print(f"  â•‘  Pour le supprimer : {suppr_cmd}".ljust(63) + " â•‘")
        print("  â•‘                                                              â•‘")
        print("  â•‘  Pour passer en install directe (sans venv) :                â•‘")
        print("  â•‘    python lidar2map.py --bootstrap=pip                       â•‘")
        print("  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
        print(f"  CrÃ©ation du venv {venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True)
        except subprocess.CalledProcessError as e:
            print(f"  ERREUR crÃ©ation venv : {e}")
            print("  Installez Python 3.8+ avec module venv.")
            sys.exit(1)

    # DÃ©ps installÃ©es dans le venv. numba est inclus systÃ©matiquement :
    # il accÃ©lÃ¨re le calcul SVF de Ã—15 Ã  Ã—50. osmium est inclus pour le
    # pipeline OSM â†’ GeoJSON (sans, ce pipeline n'est pas disponible).
    # Si l'install d'une dep optionnelle (osmium, numba) Ã©choue, on retry
    # sans elle plutÃ´t que de bloquer tout le script.
    #
    # Deps GUI : spÃ©cifiques Ã  la plateforme (Qt sur macOS/Linux).
    # TraitÃ©es comme optionnelles au sens du retry (si PyQt6 Ã©choue, on
    # continue â€” la GUI sera non fonctionnelle mais le CLI marchera).
    _gui_crit, _gui_opt = _gui_deps_plateforme()
    deps_critiques  = ["Pillow", "pyproj", "numpy", "scipy", "ijson",
                       "rasterio", "fiona", "pywebview", "certifi"] + _gui_crit
    deps_optionnelles = ["osmium", "numba"] + _gui_opt
    deps_pip = deps_critiques + deps_optionnelles
    print(f"  Installation des dÃ©pendances dans le venv (3-5 min)...")

    def _pip_install(pkgs):
        """Tente pip install. Retourne (success, stderr_msg)."""
        try:
            r = subprocess.run(
                [str(venv_pip), "install", "-q",
                 "--disable-pip-version-check"] + pkgs,
                capture_output=True, text=True)
            return r.returncode == 0, (r.stderr or "")[-500:]
        except subprocess.CalledProcessError as e:
            return False, str(e)

    install_ok, err_msg = _pip_install(deps_pip)
    if not install_ok:
        # Retry sans les deps optionnelles : si l'une d'elles est cassÃ©e
        # (cas pyrosm 0.6.2 sur Python 3.12), on garde au moins le pipeline
        # principal (LiDAR + raster).
        print(f"  Install groupÃ©e Ã©chouÃ©e, retry sans les optionnelles...")
        install_ok, err_msg = _pip_install(deps_critiques)
        if install_ok:
            # Tenter ensuite chaque optionnelle individuellement.
            print(f"  Deps critiques installÃ©es. Tentative deps optionnelles une par une...")
            opt_failed = []
            for opt in deps_optionnelles:
                ok_one, _ = _pip_install([opt])
                if not ok_one:
                    opt_failed.append(opt)
                    print(f"    âš  {opt} : install Ã©chouÃ©e â€” pipeline associÃ© indisponible")
                else:
                    print(f"    âœ“ {opt} : OK")
            if opt_failed:
                print(f"  âš  Optionnelles non installÃ©es : {', '.join(opt_failed)}")
                print(f"     Retry manuel possible : {venv_pip} install {' '.join(opt_failed)}")
        else:
            print(f"  ERREUR installation dÃ©ps critiques dans le venv :")
            print(f"  {err_msg}")
            print(f"  VÃ©rifiez votre connexion internet, puis essayez :")
            print(f"    {venv_pip} install {' '.join(deps_critiques)}")
            sys.exit(1)
    print(f"  âœ“ DÃ©pendances installÃ©es.")

    # Relancer le script avec le Python du venv
    print(f"  Relance dans le venv...")
    _relancer_dans_venv(venv_python, is_windows)


def _relancer_dans_venv(venv_python, is_windows):
    """Relance le script avec le Python du venv, comportement OS-spÃ©cifique.

    Unix : os.execv remplace le process courant â€” le shell ne rÃ©cupÃ¨re
           la main qu'aprÃ¨s terminaison du child. C'est le comportement
           attendu, Ã©conomique en RAM (pas de double process).

    Windows : os.execv y a un comportement diffÃ©rent de Unix â€” le parent
              termine immÃ©diatement et le child tourne en arriÃ¨re-plan, ce
              qui fait que le shell affiche son prompt avant la sortie du
              child. Pour Ã©viter cette confusion d'affichage, on utilise
              subprocess.run + sys.exit : on attend la fin du child et on
              propage son code retour avant de rendre la main au shell.

              IMPORTANT : on passe explicitement stdout=sys.stdout et
              stderr=sys.stderr au child, sinon quand le parent est lancÃ©
              par la GUI avec stdout=PIPE, le pipe ne se propage pas au
              child venv, et la GUI ne voit jamais rien des messages que
              le child Ã©crit. Sans ce flush du parent au prÃ©alable, les
              traces "[trace]" et "[init]" du parent se mÃ©langent avec
              celles du child Ã  cause du buffering.
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
    """S'assure que pip est disponible via ensurepip si nÃ©cessaire."""
    r = subprocess.run([sys.executable, "-m", "pip", "--version"],
                       capture_output=True)
    if r.returncode == 0:
        return  # pip dÃ©jÃ  disponible
    print("  pip absent â€” bootstrap via ensurepip...")
    try:
        import ensurepip
        ensurepip.bootstrap(upgrade=True)
        print("  pip installÃ©.")
    except Exception as e:
        print(f"  ERREUR bootstrap pip : {e}")
        print("  Installez pip manuellement : https://pip.pypa.io/en/stable/installation/")
        sys.exit(1)


def _installer_deps():
    """VÃ©rifie et installe les dÃ©pendances Python requises au dÃ©marrage.

    StratÃ©gie d'installation, par ordre d'essai :
    1. ``pip install <deps>`` standard
    2. ``pip install --break-system-packages <deps>`` (PEP 668 â€” Linux rÃ©cent,
       Homebrew Mac rÃ©cent)
    3. ``pip install --user <deps>`` (fallback derniÃ¨re chance)

    Si toutes Ã©chouent, on s'arrÃªte PROPREMENT avec un message clair plutÃ´t
    que de continuer pour planter sur le premier ``import pyproj`` venu.
    """
    # Deps GUI spÃ©cifiques Ã  la plateforme (Qt sur macOS/Linux, rien sur Windows)
    _gui_crit, _gui_opt = _gui_deps_plateforme()

    # find_spec ne charge pas le module â€” beaucoup plus rapide que __import__
    # pour les modules lourds (rasterio, scipy, PIL, PyQt6 prennent 200-500 ms
    # chacun Ã  l'import). Gain typique au dÃ©marrage Ã  froid : 2-3 s.
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
        ("certifi",   "certifi"),     # bundle CA Ã  jour (fix SSL Windows 11 / macOS)
        ("webview",   "pywebview"),   # GUI (mode sans arguments)
        ("osmium",    "osmium"),      # parseur PBF OSM (remplace ogr2ogr OSM)
        ("numba",     "numba"),       # accÃ©lÃ©ration SVF Ã—15-50 (LLVM JIT)
    ]:
        if not _module_present(mod):
            deps.append(pkg)

    # Ajouter les deps GUI plateforme non encore installÃ©es
    for pkg in _gui_crit + _gui_opt:
        # Correspondance pkg pip â†’ nom de module importable
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
    # deps optionnelles (utiles pour certains pipelines spÃ©cifiques).
    # Les deps optionnelles ne doivent pas bloquer si elles Ã©chouent Ã 
    # s'installer â€” sinon un wheel buggÃ© empÃªcherait toute utilisation
    # du script (cas vÃ©cu avec pyrosm 0.6.2 cassÃ© sur Python 3.12).
    # Les deps GUI optionnelles (pyobjc sur macOS) sont aussi dans ce set.
    DEPS_OPTIONNELLES = ({"osmium", "numba", "py7zr", "mapbox-vector-tile"}
                         | set(_gui_opt))
    deps_crit = [d for d in deps if d not in DEPS_OPTIONNELLES]
    deps_opt  = [d for d in deps if d in DEPS_OPTIONNELLES]

    print(f"  Installation des dÃ©pendances : {', '.join(deps)}...")

    # DÃ©tecter si on est dans un venv. Dans un venv, --user n'a aucun sens
    # (pip refuse) â€” il faut juste tenter l'install standard.
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
            r = subprocess.run(cmd, capture_output=True, text=True)
        except (OSError, FileNotFoundError) as e:
            last_stderr = f"pip introuvable : {e}"
            continue
        if r.returncode == 0:
            # VÃ©rifier que les imports critiques fonctionnent.
            # Les deps optionnelles ne sont PAS dans cette vÃ©rification â€”
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
            # VÃ©rifier aussi les GUI deps critiques plateforme
            for pkg in _gui_crit:
                if pkg in deps_crit:
                    _mod_map = {"PyQt6": "PyQt6", "PyQt6-WebEngine": "PyQt6.QtWebEngineWidgets",
                                "qtpy": "qtpy"}
                    try:
                        __import__(_mod_map.get(pkg, pkg))
                    except ImportError:
                        rates.append(pkg)
            if not rates:
                print(f"  âœ“ Installation rÃ©ussie ({label})")
                install_ok = True
                break
            print(f"  Tentative {label} : pip OK mais imports critiques Ã©chouent ({', '.join(rates)})")
            last_stderr = f"installation faite mais imports {rates} indisponibles"
        else:
            last_stderr = (r.stderr or r.stdout or "").strip()
            if last_stderr:
                last_stderr = last_stderr.split("\n")[-3:]
                last_stderr = "\n  ".join(last_stderr)

    # Si install groupÃ©e a Ã©chouÃ©, retry avec deps_crit seules (sans les
    # optionnelles qui peuvent Ãªtre en cause). Cas typique : osmium Cython
    # cassÃ© sur Python 3.12 â†’ l'install groupÃ©e plante, mais les autres
    # deps critiques s'installent trÃ¨s bien seules.
    if not install_ok and deps_opt and deps_crit:
        print(f"  Retry sans les deps optionnelles ({', '.join(deps_opt)})...")
        cmd_crit_only = base_cmd + deps_crit
        if in_venv:
            try:
                r = subprocess.run(cmd_crit_only, capture_output=True, text=True)
            except (OSError, FileNotFoundError):
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
                    print(f"  âœ“ Deps critiques installÃ©es (sans : {', '.join(deps_opt)})")
                    print(f"  âš  Deps optionnelles non installÃ©es : pipelines associÃ©s indisponibles")
                    print(f"     - osmium : --osm --formats-fichier geojson")
                    print(f"     - numba  : SVF lent (Ã—15 fois plus)")
                    install_ok = True

    if install_ok:
        return

    # Toutes les tentatives ont Ã©chouÃ© â€” on arrÃªte ici avec un message clair.
    import platform as _plat
    _is_mac   = _plat.system() == "Darwin"
    _is_linux = _plat.system() == "Linux"
    print()
    print("  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—")
    print("  â•‘  ERREUR : impossible d'installer les dÃ©pendances Python      â•‘")
    print("  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
    print(f"  Modules manquants : {', '.join(deps_crit)}")
    if last_stderr:
        print(f"  Dernier message pip :\n  {last_stderr}")
    print()
    print("  Solutions possibles :")
    if _is_mac:
        print("    1. Installer dans un venv :")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps_crit)}")
        print("       Puis relancer : python lidar2map.py --bootstrap=none")
        print()
        print("    2. Forcer l'install systÃ¨me (dÃ©conseillÃ©) :")
        print(f"       pip install --break-system-packages {' '.join(deps)}")
    elif _is_linux:
        print("    1. Installer via le gestionnaire de paquets :")
        print(f"       sudo apt install python3-{' python3-'.join(d.lower() for d in deps)}")
        print()
        print("    2. Utiliser un venv :")
        print("       python3 -m venv ~/mon-venv-lidar")
        print("       source ~/mon-venv-lidar/bin/activate")
        print(f"       pip install {' '.join(deps)}")
    else:
        print(f"    pip install {' '.join(deps)}")
    print()
    sys.exit(1)


def _bootstrap_environnement():
    """Orchestrateur unique du dÃ©marrage : mode â†’ venv â†’ pip â†’ install deps.

    Avant ce refactor, trois appels top-level se succÃ©daient sans qu'aucun
    point du code ne dÃ©cide globalement de la stratÃ©gie. RÃ©sultat :
    `_bootstrap_pip()` Ã©tait systÃ©matiquement exÃ©cutÃ© mÃªme en mode `auto`
    oÃ¹ il est inutile (le venv post-re-exec garantit pip), et mÃªme en mode
    `none` oÃ¹ c'est en contradiction avec l'intention de l'utilisateur ("je
    gÃ¨re mes deps moi-mÃªme").

    Maintenant : un seul point d'entrÃ©e, qui dÃ©cide en fonction du mode :
      - "auto" : crÃ©e un venv si nÃ©cessaire (re-exec) puis install deps via
                 le pip du venv (forcÃ©ment prÃ©sent, _bootstrap_pip inutile).
      - "pip"  : pas de venv, mais on n'a pas la garantie que pip soit
                 dispo (Python systÃ¨me nu, distrib exotique) â†’ bootstrap pip
                 via ensurepip puis install deps.
      - "none" : ni venv ni install. _bootstrap_venv_si_besoin se charge
                 lui-mÃªme de vÃ©rifier les imports critiques et d'avorter
                 proprement avec un message si manquants. Pas d'appel Ã 
                 _installer_deps qui forcerait une install non voulue.

    Quand cette fonction retourne, les imports critiques sont garantis pour
    les modes auto et pip. Pour none, soit les imports marchent, soit on a
    dÃ©jÃ  sys.exit(1) avec un message clair.
    """
    # En mode frozen (PyInstaller), toutes les deps Python sont dÃ©jÃ  embarquÃ©es
    # dans le bundle â€” pas de venv ni de pip Ã  exÃ©cuter.
    if getattr(sys, "frozen", False):
        return
    mode = _resoudre_mode_bootstrap()
    _bootstrap_venv_si_besoin_avec_mode(mode)
    if mode == "pip":
        _bootstrap_pip()
    if mode != "none":
        _installer_deps()


# Petit wrapper pour conserver _bootstrap_venv_si_besoin sans paramÃ¨tre cÃ´tÃ©
# usage (notamment l'aide accessible via __doc__) tout en Ã©vitant la double
# rÃ©solution du mode quand il est appelÃ© depuis l'orchestrateur.
def _bootstrap_venv_si_besoin_avec_mode(mode):
    """Appelle _bootstrap_venv_si_besoin avec un mode prÃ©-rÃ©solu.

    On stocke le mode dans une variable d'environnement temporaire que la
    fonction lira en prioritÃ©, court-circuitant sa propre rÃ©solution.
    Solution moins invasive que de modifier la signature publique de
    _bootstrap_venv_si_besoin (qui est documentÃ©e et stable).
    """
    os.environ["LIDAR2MAP_BOOTSTRAP"] = mode
    try:
        _bootstrap_venv_si_besoin()
    finally:
        # Nettoyer pour ne pas laisser fuir le mode dans les sub-processes
        # ou le venv post-re-exec qui ferait sa propre rÃ©solution.
        os.environ.pop("LIDAR2MAP_BOOTSTRAP", None)


_INSTALL_ALL_DEPS   = "--installer-deps"     in sys.argv
_DESINSTALLER       = "--desinstaller"       in sys.argv
_TELECHARGER_OUTILS = "--telecharger-outils" in sys.argv  # exÃ©cutÃ© aprÃ¨s _trouver_java
_SMOKETEST          = "--smoketest"          in sys.argv  # exÃ©cutÃ© aprÃ¨s bootstrap

_bootstrap_environnement()

# â”€â”€ --installer-deps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Force l'installation de TOUTES les dÃ©pendances (critiques + optionnelles +
# lazy) puis quitte. UtilisÃ© par les scripts setup_build_*.
# Le flag est prÃ©servÃ© dans sys.argv lors du re-exec dans le venv, ce qui
# garantit que l'install complÃ¨te se fait bien DANS le venv cible.
if _INSTALL_ALL_DEPS:
    print("  Installation complÃ¨te de toutes les dÃ©pendances...")
    _pip_base = [sys.executable, "-m", "pip", "install", "-q"]
    _toutes_deps = [
        # Critiques
        "Pillow", "pyproj", "numpy", "scipy", "ijson",
        "rasterio", "fiona", "certifi", "pywebview",
        # GUI selon plateforme
        *([p for p in ["PyQt6", "PyQt6-WebEngine", "qtpy"]
           if __import__("platform").system() in ("Darwin", "Linux")]),
        # Optionnelles / lazy (non installÃ©es par le bootstrap standard)
        "osmium", "numba", "laspy", "py7zr", "mapbox-vector-tile",
    ]
    import subprocess as _sp_id
    # Table de correspondance explicite pkg pip â†’ nom de module importable.
    # La dÃ©rivation automatique (split("-")[0]) Ã©choue sur plusieurs packages :
    #   mapbox-vector-tile â†’ "mapbox" (faux), PyQt6-WebEngine â†’ "pyqt6" (faux)
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
        "py7zr":              "py7zr",
        "mapbox-vector-tile": "mapbox_vector_tile",
    }
    for _pkg in _toutes_deps:
        _mod = _pkg_to_mod.get(_pkg, _pkg.replace("-", "_").lower())
        try:
            __import__(_mod)
            print(f"    âœ“ {_pkg} (dÃ©jÃ  installÃ©)")
        except ImportError:
            r = _sp_id.run(_pip_base + [_pkg], capture_output=True)
            if r.returncode == 0:
                print(f"    âœ“ {_pkg}")
            else:
                print(f"    âš  {_pkg} (optionnel â€” ignorÃ©)")
    print("  Toutes les dÃ©pendances installÃ©es.")
    sys.exit(0)

# â”€â”€ --desinstaller â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Supprime le venv (~/.lidar2map/venv) et le dossier d'extraction du bundle
# (~/Library/Application Support/lidar2map/ sur macOS, etc.).
# Ne supprime PAS le script lui-mÃªme ni le .app/.exe.
if _DESINSTALLER:
    import shutil as _sh_uninst
    import platform as _plat_uninst
    from pathlib import Path as _P_uninst

    _sys_u  = _plat_uninst.system()
    _home_u = _P_uninst.home()

    _lidar2map_home = _home_u / ".lidar2map"

    # Dossier d'extraction du bundle (mÃªme logique que le launcher)
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
    print("  â”€â”€ DÃ©sinstallation lidar2map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    print()

    _total = 0
    for _chemin, _label in _cibles:
        if _chemin.exists():
            # Calculer la taille avant suppression
            _taille = sum(f.stat().st_size for f in _chemin.rglob("*") if f.is_file())
            _total += _taille
            print(f"  Suppression {_label} ({_taille / 1e6:.0f} Mo)")
            print(f"    {_chemin}")
            _sh_uninst.rmtree(_chemin, ignore_errors=True)
            # MÃªmes Ã©tats âœ“/âš  que le bloc launcher pour cohÃ©rence
            print(f"    {'âœ“ supprimÃ©' if not _chemin.exists() else 'âš  partiel'}")
        else:
            print(f"  {_label} : absent ({_chemin})")
    print()
    print(f"  {_total / 1e6:.0f} Mo libÃ©rÃ©s.")
    print()
    print("  Note : lidar2map.py, le .app/.exe et le zip ne sont pas supprimÃ©s.")
    print("  Supprimez-les manuellement si nÃ©cessaire.")
    print()
    sys.exit(0)

# â”€â”€ --smoketest â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ExÃ©cute les 5 modes du pipeline sur une petite zone (GarÃ©oult 1 km) et
# vÃ©rifie que les outputs existent + non-vides. PrÃ©sent dans le bundle â†’
# testable post-dÃ©ploiement sur la machine de l'utilisateur.
#
# Le test invoque le SAME binaire (sys.executable en frozen, ou `python <ce
# script>` sinon) pour chaque mode via subprocess. LIDAR2MAP_WORK_DIR est
# hÃ©ritÃ© dans l'env â†’ outputs dans <DOSSIER_TRAVAIL>/Projets/smoke/.
#
# DurÃ©e typique : ~1 min sur Windows (caches PBF/dalles prÃ©sents), ~5 min
# au premier run (DL Geofabrik 400 Mo).
if _SMOKETEST:
    import shutil as _smk_sh
    from pathlib import Path as _smk_Path

    # Calcul de DOSSIER_TRAVAIL en local (la constante globale n'est dÃ©finie
    # qu'Ã  la ligne ~1880, aprÃ¨s ce bloc).
    if getattr(sys, "frozen", False):
        _smk_work = _smk_Path(os.environ.get("LIDAR2MAP_WORK_DIR")
                              or _smk_Path(sys.executable).resolve().parent)
        # En frozen, sys.executable EST le binaire â†’ on le rÃ©-invoque
        _smk_cmd_base = [sys.executable]
    else:
        _smk_work = _smk_Path(__file__).resolve().parent
        _smk_cmd_base = [sys.executable, str(_smk_Path(__file__).resolve())]

    _smk_nom     = "smoke"
    _smk_projets = _smk_work / "Projets" / _smk_nom
    _smk_zone    = ["--zone-ville", "Gareoult", "--zone-rayon", "1",
                    "--zone-nom",   _smk_nom, "--oui"]

    # (nom, args supplÃ©mentaires, outputs attendus relatifs Ã  _smk_projets)
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
         ["ign_raster/smoke_planign_z12-14.mbtiles"]),
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

    # EmpÃªcher chaque sous-test de polluer l'historique de 5+ entrÃ©es.
    # _historique_debut/_sauver_historique respectent cet env var.
    _smk_env = os.environ.copy()
    _smk_env["LIDAR2MAP_SKIP_HIST"] = "1"

    def _smk_run(name, extra, expected, timeout=600):
        print(f"\nâ”â”â” {name} â”â”â”", flush=True)
        t0 = time.time()
        try:
            rc = subprocess.run(_smk_cmd_base + _smk_zone + extra,
                                timeout=timeout, env=_smk_env).returncode
        except subprocess.TimeoutExpired:
            print(f"  âœ— TIMEOUT (> {timeout}s)")
            return False
        dur = time.time() - t0
        if rc != 0:
            print(f"  âœ— exit={rc} en {dur:.0f}s")
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
            print(f"  âœ— outputs KO en {dur:.0f}s :")
            for m in missing:
                print(f"      {m}")
            return False
        print(f"  âœ“ {dur:.0f}s  ({', '.join(sizes)})")
        return True

    def _smk_fusion(timeout=120):
        """Fusion utilise l'output OSM prÃ©cÃ©dent comme input."""
        src = _smk_projets / "osm_vecteur" / "smoke_osm_highway.geojson.gz"
        out = _smk_projets / "fusion"      / "smoke_fusion.geojson.gz"
        print(f"\nâ”â”â” Fusion â”â”â”", flush=True)
        if not src.exists():
            print(f"  âŠ˜ SKIP : input OSM absent ({src.name})")
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            rc = subprocess.run(_smk_cmd_base + ["--fusionner", "--source", str(src),
                                                 "--sortie", str(out),
                                                 "--formats-fichier", "gz", "--oui"],
                                timeout=timeout, env=_smk_env).returncode
        except subprocess.TimeoutExpired:
            print(f"  âœ— TIMEOUT (> {timeout}s)")
            return False
        dur = time.time() - t0
        if rc == 0 and out.exists() and out.stat().st_size > 0:
            print(f"  âœ“ {dur:.0f}s  ({_smk_size(out.stat().st_size)})")
            return True
        print(f"  âœ— exit={rc} en {dur:.0f}s")
        return False

    print(f"â”â”â” Smoke test : GarÃ©oult 1 km â”â”â”")
    print(f"  Binaire : {' '.join(_smk_cmd_base)}")
    print(f"  Outputs : {_smk_projets}")
    # Wipe Projets/smoke pour isoler les tests (caches dalles/tuiles prÃ©servÃ©s)
    if _smk_projets.exists():
        _smk_sh.rmtree(_smk_projets, ignore_errors=True)

    _smk_results = []
    for _smk_name, _smk_extra, _smk_expected in _smk_tests:
        _smk_results.append((_smk_name,
                             _smk_run(_smk_name, _smk_extra, _smk_expected)))
    _smk_results.append(("Fusion", _smk_fusion()))

    print(f"\nâ”â”â” RÃ‰SULTATS â”â”â”")
    _smk_ok   = sum(1 for _, ok in _smk_results if ok is True)
    _smk_fail = sum(1 for _, ok in _smk_results if ok is False)
    _smk_skip = sum(1 for _, ok in _smk_results if ok is None)
    for _smk_name, ok in _smk_results:
        sym = "âœ“" if ok is True else ("âŠ˜" if ok is None else "âœ—")
        print(f"  {sym} {_smk_name}")
    print(f"\n{_smk_ok}/{len(_smk_results)} OK"
          + (f"  ({_smk_skip} skipped)" if _smk_skip else "")
          + (f"  ({_smk_fail} Ã©chec)"   if _smk_fail else ""))
    sys.exit(0 if _smk_fail == 0 else 1)

# â”€â”€ suite du script â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class _TeeLogger:
    """
    Duplique stdout vers un fichier log avec horodatage.

    Gestion des \r : les barres de progression terminent par \r (pas \n).
    Pour le terminal, \r Ã©crase la ligne courante â€” comportement normal.
    Pour le log, on ne conserve que le dernier Ã©tat de chaque ligne \r
    (la valeur finale), en ignorant les mises Ã  jour intermÃ©diaires.
    """
    def __init__(self, log_path):
        self._terminal = sys.stdout
        self._log = open(log_path, "w", encoding="utf-8", buffering=1)
        self._buf = ""          # buffer jusqu'au prochain \n
        self._cr_buf = ""       # dernier contenu de ligne \r (Ã©crase les prÃ©cÃ©dents)

    def _log_line(self, line):
        """Ã‰crit une ligne dans le fichier log avec horodatage."""
        # Nettoyer les sÃ©quences \r rÃ©siduelles dans la ligne
        if "\r" in line:
            line = line.split("\r")[-1]
        line = line.strip()
        if line:
            ts = time.strftime("%H:%M:%S")
            self._log.write(f"[{ts}] {line}\n")

    def write(self, msg):
        # â”€â”€ Terminal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Toutes les opÃ©rations sont dÃ©fensives parce que cette mÃ©thode est
        # appelÃ©e par Python lui-mÃªme au shutdown. Si un de ses appels lÃ¨ve
        # une exception, Windows retourne le code 120 (ERROR_CALL_NOT_IMPLEMENTED)
        # Ã  la place du code passÃ© Ã  sys.exit().
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
            # bufferisÃ©es dans le pipe quand stdout est redirigÃ© (cas de la
            # GUI qui lance le script comme subprocess). ConsÃ©quence : les
            # messages n'arrivent au parent qu'au moment du wait() final,
            # ce qui rend le panneau de log inutile en temps rÃ©el.
            if "\r" in msg or "\n" in msg:
                self._terminal.flush()
        except Exception:
            pass

        # â”€â”€ Log â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Traiter caractÃ¨re par caractÃ¨re pour gÃ©rer \r et \n proprement
        try:
            for ch in msg:
                if ch == "\r":
                    # \r : Ã©crase le contenu de la ligne courante (barre de progression)
                    # On garde le dernier Ã©tat dans _cr_buf ; on ne loggue rien encore
                    self._cr_buf = self._buf
                    self._buf = ""
                elif ch == "\n":
                    # \n : fin de ligne â€” logguer le contenu final
                    # Si la ligne Ã©tait prÃ©cÃ©dÃ©e de \r, prendre le dernier \r
                    line = self._buf or self._cr_buf
                    self._log_line(line)
                    self._buf = ""
                    self._cr_buf = ""
                else:
                    self._buf += ch
        except Exception:
            pass

    def flush(self):
        # DÃ©fensif : flush() est appelÃ© par Python au shutdown, aprÃ¨s que
        # close() a peut-Ãªtre dÃ©jÃ  fermÃ© self._log. Sans try/except, l'erreur
        # "I/O operation on closed file" remonte â†’ code retour Windows = 120.
        try:
            self._terminal.flush()
        except Exception:
            pass
        try:
            self._log.flush()
        except Exception:
            pass

    def close(self):
        # Flush des buffers rÃ©siduels â€” dÃ©fensif : pendant le shutdown
        # Python, sys.stdout/sys.stderr peuvent Ãªtre dans un Ã©tat partiel,
        # et toute exception ici peut polluer le code retour du process
        # (Windows retourne 120 si l'atexit handler Ã©choue).
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
    # En mode frozen, __file__ est dans le bundle temporaire â€” on veut les
    # logs Ã  cÃ´tÃ© de l'exe (dossier utilisateur, persistant).
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
        # logs/ inaccessible â†’ log console uniquement, pas de fichier systÃ¨me
        print("  AVERTISSEMENT : dossier logs/ inaccessible, log console uniquement.")
        return
    nom = "lidar_" + time.strftime("%Y%m%d_%H%M%S") + ".log"
    log_path = log_dir / nom
    tee = _TeeLogger(log_path)
    sys.stdout = tee
    sys.stderr = tee   # stderr â†’ mÃªme log (tracebacks, warnings)
    # atexit : fonction nommÃ©e robuste plutÃ´t qu'un lambda. Toute exception
    # ici peut faire que Windows retourne le code 120 (ERROR_CALL_NOT_IMPLEMENTED)
    # au lieu du code passÃ© Ã  sys.exit() â€” Ã§a casse Ã  la fois le contrat CLI
    # et le mÃ©canisme d'erreur modale GUI qui se base sur retcode != 0.
    def _close_tee_safely():
        try:
            if isinstance(sys.stdout, _TeeLogger):
                sys.stdout.close()
        except Exception:
            pass
    atexit.register(_close_tee_safely)
    # â”€â”€ Intercepter les exceptions non gÃ©rÃ©es â†’ log avant exit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    import traceback as _tb
    def _excepthook(exc_type, exc_value, exc_tb):
        print("\nEXCEPTION NON GÃ‰RÃ‰E :")
        print("".join(_tb.format_exception(exc_type, exc_value, exc_tb)))
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _excepthook
    # â”€â”€ En-tÃªte avec paramÃ¨tres de lancement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ts  = time.strftime("%Y-%m-%d %H:%M:%S")
    cmd = " ".join(sys.argv)
    tee._log.write("=" * 60 + "\n")
    tee._log.write(f"  lidar2map.py â€” dÃ©marrage {ts}\n")
    tee._log.write(f"  Commande : {cmd}\n")
    tee._log.write("=" * 60 + "\n")
    print(f"  Log : {log_path}")

_activer_log()

# â”€â”€ RequÃªtes HTTP via urllib (stdlib, zÃ©ro dÃ©pendance) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_HTTP_UA = "lidar2map/1.0 (IGN WMTS/WMS)"


def _urlopen(url, headers=None, timeout=15):
    """Ouvre une URL avec urllib, retourne la rÃ©ponse. GÃ¨re User-Agent par dÃ©faut."""
    hdrs = {"User-Agent": _HTTP_UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    return urllib.request.urlopen(req, timeout=timeout)


def _hms(seconds):
    """Formate une durÃ©e en secondes â†’ h:mm:ss ou m:ss ou Xs."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


# Outils GDAL dont les appels subprocess sont affichÃ©s dans le terminal
def _log_req(url_or_cmd, label=""):
    """Log une requÃªte externe (HTTP ou subprocess) â€” toujours via print/TeeLogger."""
    if isinstance(url_or_cmd, list):
        exe      = Path(url_or_cmd[0]).name if url_or_cmd else ""
        args_str = " ".join(str(a) for a in url_or_cmd[1:]
                            if not str(a).startswith("--config"))
        print(f"  $ {exe} {args_str}", flush=True)
    else:
        print(f"  â†’ {label + ' ' if label else ''}{url_or_cmd}", flush=True)

# ============================================================
# PLATEFORME
# ============================================================

WINDOWS = platform.system() == "Windows"
LINUX   = platform.system() == "Linux"
MACOS   = platform.system() == "Darwin"

# â”€â”€ Manifest de fichiers crÃ©Ã©s (dÃ©coupage Ã  priori) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Classe Manifeste : JSON local au projet, universel LiDAR/WMTS.
# _creer_fichier() fonctionne via un context manager thread-local â€”
# silencieux en dehors d'un contexte actif.

import threading as _threading
from contextlib import contextmanager as _contextmanager

_manifest_ctx = _threading.local()   # .manifeste et .cle par thread


class Manifeste:
    """Manifeste JSON local au projet â€” reprise et nettoyage des morceaux."""

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
                print(f"  âš  Manifeste {self.path.name} : structure inattendue "
                      f"(type={type(d).__name__}) â€” rÃ©initialisation")
            except (OSError, json.JSONDecodeError) as e:
                # Manifeste corrompu (crash disque, Ã©criture interrompue) : on
                # repart d'un Ã©tat vierge mais on prÃ©vient l'utilisateur â€” la
                # progression prÃ©cÃ©dente sera perdue, pas rÃ©initialisÃ©e silencieusement.
                print(f"  âš  Manifeste {self.path.name} illisible ({type(e).__name__}: {e}) "
                      f"â€” rÃ©initialisation (progression antÃ©rieure perdue)")
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

    _warned_save_failed = False    # class-level : un seul warn par run

    def _sauver(self):
        try:
            _ecrire_json_atomique(self.path, self._data, indent=2)
        except Exception as e:
            # Le manifeste est best-effort : si le disque est saturÃ© ou
            # si les permissions changent, on n'interrompt pas le pipeline
            # principal â€” mais on prÃ©vient une fois (par run) pour que
            # l'utilisateur sache que la reprise sera incohÃ©rente.
            if not Manifeste._warned_save_failed:
                Manifeste._warned_save_failed = True
                print(f"  âš  Manifeste {self.path.name} : Ã©chec d'Ã©criture "
                      f"({type(e).__name__}: {e}). "
                      f"Reprise potentiellement incohÃ©rente.")


@_contextmanager
def _contexte_manifeste(manifeste, cle: str):
    """Active le tracking des fichiers crÃ©Ã©s pour ce morceau dans le thread courant.

    Supporte l'imbrication : sauvegarde le contexte prÃ©cÃ©dent Ã  l'entrÃ©e et
    le restaure Ã  la sortie, plutÃ´t que d'Ã©craser avec None (ce qui ferait
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
    DÃ©clare un fichier intermÃ©diaire crÃ©Ã© dans le pipeline.

    EnregistrÃ© dans le manifest du morceau courant â†’ supprimÃ© par --nettoyage
    aprÃ¨s le morceau (dalles, TIF ombrages, TIF warpÃ©, VRT, data.bin, tuiles
    WMTS, etc.).

    Les sorties finales (.mbtiles, .rmap, .sqlitedb, .geojson(.gz)) NE doivent
    PAS Ãªtre dÃ©clarÃ©es via cette fonction â€” elles sont conservÃ©es d'office.

    Silencieux si aucun contexte manifeste n'est actif (hors boucle Ã  priori).
    """
    m = getattr(_manifest_ctx, "manifeste", None)
    if m is None:
        return
    cle = getattr(_manifest_ctx, "cle", "global")
    m.enregistrer_fichier(path, cle)


def _supprimer_fichiers(fichiers: list):
    """
    Supprime tous les fichiers crÃ©Ã©s par un morceau (--nettoyage).
    Cela inclut : dalles LiDAR, tuiles WMTS, TIF ombrages, TIF warpÃ©.
    Conserve uniquement les sorties finales (.mbtiles, .rmap, .sqlitedb).

    But : permettre le traitement d'une grande BBox sans saturer le disque â€”
    chaque morceau libÃ¨re son espace avant que le suivant dÃ©marre.

    Seuls les fichiers crÃ©Ã©s/tÃ©lÃ©chargÃ©s PAR ce morceau (enregistrÃ©s dans le
    manifest via _creer_fichier) sont supprimÃ©s. Les fichiers dÃ©jÃ 
    prÃ©sents avant le dÃ©but du morceau ne sont pas touchÃ©s.
    """
    suppr = 0
    dirs_a_verifier = set()
    for chemin in fichiers:
        p = Path(chemin)
        # Tous les fichiers du manifest sont intermÃ©diaires.
        # Les sorties finales (.mbtiles, .rmapâ€¦) ne sont jamais enregistrÃ©es
        # via _creer_fichier â†’ elles ne se retrouvent jamais ici.
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
        print(f"  Nettoyage : {suppr} fichier(s) intermÃ©diaire(s) supprimÃ©(s)")

# ============================================================
# CONFIGURATION
# ============================================================

# â”€â”€ Chemins â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# En mode frozen (PyInstaller) : __file__ pointe dans le bundle temporaire
# (sys._MEIPASS sous --onefile). On utilise sys.executable pour que les
# Projets/, cache/, logs/ etc. soient crÃ©Ã©s Ã  cÃ´tÃ© de l'exe (cwd utilisateur).
# _MEIPASS reste utilisable sÃ©parÃ©ment pour retrouver les ressources bundlÃ©es
# (tagmapping-min.xml).
if getattr(sys, "frozen", False):
    # LIDAR2MAP_WORK_DIR transmis par le launcher onefile : pointe vers le
    # dossier oÃ¹ l'utilisateur a posÃ© l'exe. Sinon, fallback sur le dossier
    # de l'exe courant (cas exe onedir lancÃ© directement).
    DOSSIER_TRAVAIL = Path(os.environ.get("LIDAR2MAP_WORK_DIR")
                           or Path(sys.executable).resolve().parent)
    BUNDLE_DIR      = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    DOSSIER_TRAVAIL = Path(__file__).resolve().parent
    BUNDLE_DIR      = DOSSIER_TRAVAIL

# ~/.lidar2map/ : dossier de runtime partagÃ© entre tous les dossiers de travail.
# Contient venv/, jre/, osmosis/. Permet de ne tÃ©lÃ©charger qu'une fois ces
# dÃ©pendances mÃªme si le script est lancÃ© depuis plusieurs emplacements.
# Pour nettoyer complÃ¨tement lidar2map :  rm -rf ~/.lidar2map
LIDAR2MAP_HOME = Path.home() / ".lidar2map"

# â”€â”€ Provider LiDAR (par dÃ©faut : France IGN HD) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# POC d'abstraction : tout ce qui est spÃ©cifique Ã  une source nationale
# (URLs, CRS, nommage des dalles, gÃ©omÃ©trie) vit dans providers/<pays>.py.
# Le reste du pipeline (SVF, ombrages, MBTiles) reste agnostique.
#
# SÃ©lection : --provider <code> en CLI, ou variable d'env LIDAR2MAP_PROVIDER.
# Codes disponibles : fr-ign (dÃ©faut), nl-ahn (POC).
import importlib as _importlib
import os as _os

def _discover_providers():
    """Liste les providers disponibles dans providers/*.py.

    Retourne une liste de dicts {code, name, country} (sans erreur si un
    module est cassÃ©). UtilisÃ© par la GUI pour peupler son sÃ©lecteur de
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
            print(f"  [provider scan] {f.name} ignorÃ© : {type(e).__name__}: {e}",
                  file=sys.stderr)
    return result


def _load_provider():
    code = None
    # CLI scan lÃ©ger (sans dÃ©pendre d'argparse qui n'est pas encore configurÃ©)
    if "--provider" in sys.argv:
        _i = sys.argv.index("--provider")
        if _i + 1 < len(sys.argv):
            code = sys.argv[_i + 1]
    code = code or _os.environ.get("LIDAR2MAP_PROVIDER") or "fr-ign"
    # Mapping code â†’ module (kebab-case â†’ snake_case)
    module_name = code.replace("-", "_")
    try:
        return _importlib.import_module(f"providers.{module_name}")
    except ImportError as e:
        print(f"ERREUR : provider '{code}' introuvable "
              f"(providers/{module_name}.py absent) : {e}", file=sys.stderr)
        print(f"Provider FR_IGN par dÃ©faut.", file=sys.stderr)
        from providers import fr_ign
        return fr_ign

PROVIDER = _load_provider()

# Sous-dossier provider-spÃ©cifique pour cache et Projets (rÃ©trocompat : si le
# user a un ancien cache/ign_lidar/ ou Projets/<zone>/ign_lidar/, ils ne sont
# plus utilisÃ©s automatiquement â€” migration manuelle requise).
# Convention : "lidar/<country>" pour disambigÃ¼er par pays
# (cache/lidar/fr/, cache/lidar/nl/, ...).
LIDAR_SUBDIR = f"lidar/{PROVIDER.COUNTRY}"

# Re-exports pour compat avec le code existant â€” Ã©viter de toucher des
# centaines de call sites en aval pendant ce POC.
RESOLUTION_M       = PROVIDER.RESOLUTION_M
DALLE_KM           = PROVIDER.DALLE_KM
PX_PAR_DALLE       = PROVIDER.PX_PAR_DALLE
SEUIL_DALLE_VALIDE = PROVIDER.SEUIL_DALLE_VALIDE

# â”€â”€ RÃ©seau â€” tentatives et dÃ©lais â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MAX_TENTATIVES = 3    # essais avant abandon d'un tÃ©lÃ©chargement
DELAI_RETRY    = 5    # secondes entre deux tentatives
NB_WORKERS     = 8    # workers parallÃ¨les par dÃ©faut (tÃ©lÃ©chargement dalles/tuiles)

# â”€â”€ MBTiles / WMTS â€” paramÃ¨tres de batch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SEUIL_ERR_CONSEC      = 30   # erreurs consÃ©cutives â†’ abandon WMTS (panne systÃ©mique)
BATCH_MBTILES_INSERT  = 500  # tuiles par INSERT executemany dans MBTiles WMTS
BATCH_SQLITEDB_INSERT = 2000 # tuiles par batch lors de la conversion vers .sqlitedb
HTTP_CHUNK_SIZE       = 65536  # taille de lecture par chunk HTTP (tÃ©lÃ©chargement dalles)

# â”€â”€ URLs IGN (re-exports du provider) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# getattr avec fallback : tous les providers n'ont pas forcÃ©ment ces attributs.
# Ex: AHN expose WCS_URL au lieu de WFS_URL â€” les chemins de code qui utilisent
# WFS_URL retomberont sur None et devront Ãªtre adaptÃ©s (BDTOPO, etc.).
WMS_URL   = getattr(PROVIDER, "WMS_URL",   None)
WMS_LAYER = getattr(PROVIDER, "WMS_LAYER", None)
WFS_URL   = getattr(PROVIDER, "WFS_URL",   None)

# â”€â”€ Geofabrik : dÃ©partement â†’ rÃ©gion (URL slug) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Table statique (135 entrÃ©es) construite une seule fois Ã  l'import au lieu
# d'Ãªtre recrÃ©Ã©e Ã  chaque appel d'`if args.osm:` dans main().
_GEOFABRIK = {
    # Auvergne-RhÃ´ne-Alpes
    "01": "auvergne-rhone-alpes",  # Ain
    "03": "auvergne-rhone-alpes",  # Allier
    "07": "auvergne-rhone-alpes",  # ArdÃ¨che
    "15": "auvergne-rhone-alpes",  # Cantal
    "26": "auvergne-rhone-alpes",  # DrÃ´me
    "38": "auvergne-rhone-alpes",  # IsÃ¨re
    "42": "auvergne-rhone-alpes",  # Loire
    "43": "auvergne-rhone-alpes",  # Haute-Loire
    "63": "auvergne-rhone-alpes",  # Puy-de-DÃ´me
    "69": "auvergne-rhone-alpes",  # RhÃ´ne
    "73": "auvergne-rhone-alpes",  # Savoie
    "74": "auvergne-rhone-alpes",  # Haute-Savoie
    # Bourgogne-Franche-ComtÃ©
    "21": "bourgogne-franche-comte",  # CÃ´te-d'Or
    "25": "bourgogne-franche-comte",  # Doubs
    "39": "bourgogne-franche-comte",  # Jura
    "58": "bourgogne-franche-comte",  # NiÃ¨vre
    "70": "bourgogne-franche-comte",  # Haute-SaÃ´ne
    "71": "bourgogne-franche-comte",  # SaÃ´ne-et-Loire
    "89": "bourgogne-franche-comte",  # Yonne
    "90": "bourgogne-franche-comte",  # Territoire de Belfort
    # Bretagne
    "22": "bretagne",  # CÃ´tes-d'Armor
    "29": "bretagne",  # FinistÃ¨re
    "35": "bretagne",  # Ille-et-Vilaine
    "56": "bretagne",  # Morbihan
    # Centre-Val de Loire
    "18": "centre-val-de-loire",  # Cher
    "28": "centre-val-de-loire",  # Eure-et-Loir
    "36": "centre-val-de-loire",  # Indre
    "37": "centre-val-de-loire",  # Indre-et-Loire
    "41": "centre-val-de-loire",  # Loir-et-Cher
    "45": "centre-val-de-loire",  # Loiret
    # Corse
    "2A": "corse",  # Corse-du-Sud
    "2B": "corse",  # Haute-Corse
    # Grand Est
    "08": "grand-est",  # Ardennes
    "10": "grand-est",  # Aube
    "51": "grand-est",  # Marne
    "52": "grand-est",  # Haute-Marne
    "54": "grand-est",  # Meurthe-et-Moselle
    "55": "grand-est",  # Meuse
    "57": "grand-est",  # Moselle
    "67": "grand-est",  # Bas-Rhin
    "68": "grand-est",  # Haut-Rhin
    "88": "grand-est",  # Vosges
    # Hauts-de-France
    "02": "hauts-de-france",  # Aisne
    "59": "hauts-de-france",  # Nord
    "60": "hauts-de-france",  # Oise
    "62": "hauts-de-france",  # Pas-de-Calais
    "80": "hauts-de-france",  # Somme
    # ÃŽle-de-France
    "75": "ile-de-france",  # Paris
    "77": "ile-de-france",  # Seine-et-Marne
    "78": "ile-de-france",  # Yvelines
    "91": "ile-de-france",  # Essonne
    "92": "ile-de-france",  # Hauts-de-Seine
    "93": "ile-de-france",  # Seine-Saint-Denis
    "94": "ile-de-france",  # Val-de-Marne
    "95": "ile-de-france",  # Val-d'Oise
    # Normandie
    "14": "normandie",  # Calvados
    "27": "normandie",  # Eure
    "50": "normandie",  # Manche
    "61": "normandie",  # Orne
    "76": "normandie",  # Seine-Maritime
    # Nouvelle-Aquitaine
    "16": "nouvelle-aquitaine",  # Charente
    "17": "nouvelle-aquitaine",  # Charente-Maritime
    "19": "nouvelle-aquitaine",  # CorrÃ¨ze
    "23": "nouvelle-aquitaine",  # Creuse
    "24": "nouvelle-aquitaine",  # Dordogne
    "33": "nouvelle-aquitaine",  # Gironde
    "40": "nouvelle-aquitaine",  # Landes
    "47": "nouvelle-aquitaine",  # Lot-et-Garonne
    "64": "nouvelle-aquitaine",  # PyrÃ©nÃ©es-Atlantiques
    "79": "nouvelle-aquitaine",  # Deux-SÃ¨vres
    "86": "nouvelle-aquitaine",  # Vienne
    "87": "nouvelle-aquitaine",  # Haute-Vienne
    # Occitanie
    "09": "occitanie",  # AriÃ¨ge
    "11": "occitanie",  # Aude
    "12": "occitanie",  # Aveyron
    "30": "occitanie",  # Gard
    "31": "occitanie",  # Haute-Garonne
    "32": "occitanie",  # Gers
    "34": "occitanie",  # HÃ©rault
    "46": "occitanie",  # Lot
    "48": "occitanie",  # LozÃ¨re
    "65": "occitanie",  # Hautes-PyrÃ©nÃ©es
    "66": "occitanie",  # PyrÃ©nÃ©es-Orientales
    "81": "occitanie",  # Tarn
    "82": "occitanie",  # Tarn-et-Garonne
    # Pays de la Loire
    "44": "pays-de-la-loire",  # Loire-Atlantique
    "49": "pays-de-la-loire",  # Maine-et-Loire
    "53": "pays-de-la-loire",  # Mayenne
    "72": "pays-de-la-loire",  # Sarthe
    "85": "pays-de-la-loire",  # VendÃ©e
    # Provence-Alpes-CÃ´te d'Azur
    "04": "provence-alpes-cote-d-azur",  # Alpes-de-Haute-Provence
    "05": "provence-alpes-cote-d-azur",  # Hautes-Alpes
    "06": "provence-alpes-cote-d-azur",  # Alpes-Maritimes
    "13": "provence-alpes-cote-d-azur",  # Bouches-du-RhÃ´ne
    "83": "provence-alpes-cote-d-azur",  # Var
    "84": "provence-alpes-cote-d-azur",  # Vaucluse
    # DOM/TOM (extraits Geofabrik sÃ©parÃ©s)
    "971": "guadeloupe",
    "972": "martinique",
    "973": "guyane",
    "974": "reunion",
    "976": "mayotte",
}
_GEOFABRIK_BASE_URL      = "https://download.geofabrik.de/europe/france"
_GEOFABRIK_BASE_URL_ROOT = "https://download.geofabrik.de/europe"

# â”€â”€ Rendu archÃ©ologique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ELEVATION_SOLEIL = 25   # degrÃ©s â€” 25Â° rÃ©vÃ¨le micro-reliefs ; 45Â° usage gÃ©nÃ©ral


def _valider_zooms(args, parser):
    """VÃ©rifie zoom_min â‰¤ zoom_max avant lancement du pipeline.

    Sans ce check, l'utilisateur qui saisit `--zoom-min 18 --zoom-max 13`
    voit un calculer_grille_xyz() vide et un MBTiles Ã  0 tuile sans message
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
            f"Inversez les valeurs ou retirez l'un des deux pour utiliser le dÃ©faut."
        )
    if zmin < 0 or zmax > 22:
        parser.error(
            f"Zoom hors plage : --zoom-min={zmin} --zoom-max={zmax} "
            f"(valeurs valides : 0 Ã  22)."
        )


# Cache des Transformer pyproj : leur crÃ©ation prend ~10 ms (lecture proj.db,
# parsing CRS, init de la chaÃ®ne d'opÃ©rations). Inutile de les recrÃ©er Ã  chaque
# appel â€” ils sont thread-safe et rÃ©utilisables.
# 5 sites du code crÃ©aient le mÃªme Transformer 4326â†”2154 ; gain marginal mais
# code plus propre. On utilise functools.lru_cache pour mÃ©moriser par paire
# (src_crs, dst_crs).
import functools as _functools

@_functools.lru_cache(maxsize=8)
def _get_transformer(src_crs, dst_crs, always_xy=True):
    """Retourne un pyproj Transformer mÃ©morisÃ© pour la paire (src, dst).

    Utilisation :
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        x_l93, y_l93 = t.transform(lon, lat)

    Note : ne pas appeler avec always_xy=False et always_xy=True alternativement
    sur la mÃªme paire â€” le cache verra Ã§a comme deux entrÃ©es distinctes (correct).
    """
    from pyproj import Transformer
    return Transformer.from_crs(src_crs, dst_crs, always_xy=always_xy)


def _ecrire_json_atomique(path, data, indent=None):
    """Ã‰crit data en JSON dans path de faÃ§on atomique.

    Pattern : sÃ©rialiser en RAM, Ã©crire dans path.tmp, fsync, replace path.
    Garantit que path est soit l'ancienne version, soit la nouvelle complÃ¨te,
    jamais une troncature. Critique pour les caches (manifeste, dep_bbox,
    TMS) oÃ¹ une corruption silencieuse fait perdre l'Ã©tat entre runs.

    En cas d'OSError (disque plein, permission, etc.), le tmp est nettoyÃ©
    et l'exception remonte. Pas de swallow silencieux comme l'ancien
    `except Exception: pass` du Manifeste.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        # SÃ©rialisation en RAM d'abord (un seul write atomique sur le tmp)
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
                pass  # fsync indisponible (ramdisk, certains FS) â€” non critique
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _safe_zip_extractall(zf, target):
    """zipfile.extractall(target) protÃ©gÃ© contre les chemins absolus et
    les traversÃ©es ``..`` (zip-slip).

    Python 3.12+ a ``filter='data'`` pour zipfile mais notre minimum est
    3.8 â†’ on valide manuellement. Pour les tarfiles on utilise dÃ©jÃ 
    ``filter='data'`` natif (cf. ``_telecharger_jre_local``).
    """
    target = Path(target).resolve()
    for m in zf.infolist():
        # Refuser absolu (Windows drive + Unix slash absolu) et drive letter
        if m.filename.startswith(("/", "\\")) or ":" in m.filename[:3]:
            raise ValueError(f"Chemin absolu dans le zip : {m.filename!r}")
        dest = (target / m.filename).resolve()
        # dest doit Ãªtre sous target (ou exactement target pour un nom vide)
        if dest != target and target not in dest.parents:
            raise ValueError(f"Chemin sortant du dossier cible : {m.filename!r}")
    zf.extractall(target)


def _gunzip_vers_fichier(src_gz, dst_raw, chunk=1 << 20):
    """DÃ©compresse src_gz â†’ dst_raw en streaming (1 Mo Ã  la fois).

    Remplace le pattern `fout.write(fin.read())` qui charge intÃ©gralement
    en RAM. Sur un GeoJSON dept-scale (1-3 Go en clair), la version naÃ¯ve
    fait peser 1-3 Go de RAM Python pour zÃ©ro raison ; la version streamÃ©e
    travaille avec ~1 Mo en pic.

    Ã‰criture atomique via .tmp + replace : si la dÃ©compression est interrompue,
    le fichier final n'est jamais en Ã©tat partiel.
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
    """Compresse src_raw â†’ dst_gz en streaming (1 Mo Ã  la fois).

    Pendant Ã©crite, le contenu va dans dst_gz.tmp puis replace : un Ctrl+C
    en cours de compression ne laisse pas un .gz tronquÃ© Ã  la place de
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


# Ã‰vÃ©nement d'arrÃªt propre â€” positionnÃ© par Ctrl+C en mode CLI.
# VÃ©rifiÃ© dans les boucles longues (pagination WFS, WMTS, etc.)
# pour interrompre entre deux requÃªtes sans laisser de thread zombie.
_stop_event = threading.Event()

import signal as _signal
def _on_sigint(sig, frame):
    """Soft cancel : 1er Ctrl+C demande l'arrÃªt, 2nd force la sortie.

    Pattern standard Unix (git, rsync, etc.) : on laisse l'opÃ©ration en cours
    finir proprement (cleanup .tmp, fermeture sqlite, etc.) plutÃ´t que de
    couper sec. Si l'utilisateur insiste avec un 2nd Ctrl+C, on quitte direct.

    Limites connues :
    - Subprocess fils (osmosis, ogr2ogr) ne sont PAS tuÃ©s â€” ils tournent
      jusqu'au bout de leur opÃ©ration courante (Java buffer flush, etc.)
    - Kernel Numba (SVF, RRIM) est intuable pendant son exÃ©cution.
      L'interruption est respectÃ©e APRÃˆS le kernel courant, entre directions
      sur le fallback numpy uniquement.
    """
    if _stop_event.is_set():
        # 2Ã¨me Ctrl+C â†’ sortie immÃ©diate (code 128+SIGINT par convention POSIX)
        print("\n\nForÃ§age â€” sortie immÃ©diate.", flush=True)
        sys.exit(130)
    _stop_event.set()
    print("\n\nInterruption demandÃ©e â€” finition de l'opÃ©ration en cours.", flush=True)
    print("  Pressez Ctrl+C Ã  nouveau pour forcer la sortie.", flush=True)
_signal.signal(_signal.SIGINT, _on_sigint)

# ============================================================
# UTILITAIRES
# ============================================================

def normaliser_nom(texte):
    """'garÃ©oult' -> 'gareoult'"""
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
    rho0 = 6055612.050   # a*F*t(Ï†0)^n  Ï†0=46.5Â° â€” identique Ã  la conversion inverse
    lam0 = math.radians(3.0)
    lam  = math.radians(lon)
    phi  = math.radians(lat)
    e_sin = e * math.sin(phi)
    t = math.tan(math.pi/4 - phi/2) / ((1 - e_sin)/(1 + e_sin))**(e/2)
    rho   = F * t**n  # F inclut dÃ©jÃ  a (= a Ã— F_adim)
    theta = n * (lam - lam0)
    x = 700000 + rho * math.sin(theta)
    y = 6600000 + rho0 - rho * math.cos(theta)
    return x, y


def lamb93_to_wgs84_approx(x, y):
    """Conversion Lambert 93 â†’ WGS84 approx. (Â±50 m) â€” sans dÃ©pendance externe.
    Constantes IGN officielles : n, F*a, rho0 calculÃ©es depuis GRS80 + Ï†0=46.5Â°.
    """
    n    = 0.7256077650
    F    = 11754255.426  # a * F (F dimensionless Ã— demi-grand axe GRS80)
    rho0 = 6055612.050   # a * F * t(Ï†0)^n  avec Ï†0=46.5Â°
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
    """Lambert 93 â†’ WGS84 avec pyproj si dispo, fallback sur l'approximation.

    Retourne (lon, lat) en degrÃ©s. UtilisÃ©e partout oÃ¹ pyproj peut manquer
    (ex: bootstrap, environnement minimal) pour garantir un rÃ©sultat mÃªme
    sans proj.db. PrÃ©cision pyproj < 1 m, approximation < 50 m.
    """
    try:
        _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
        return _t.transform(x, y)
    except Exception:
        return lamb93_to_wgs84_approx(x, y)

# ============================================================
# GÃ‰OCODAGE
# ============================================================

def geocoder_ville_wgs84(nom_ville):
    """GÃ©ocode une ville et retourne (lat, lon) en WGS84. Retourne (None, None) si Ã©chec.

    Filtre le rÃ©sultat sur le champ ``addresstype`` Nominatim pour rejeter les
    correspondances "fuzzy" non-administratives (POI, commerces, hameaux
    incertains). Sans Ã§a, Nominatim renvoie n'importe quoi pour une chaÃ®ne
    non-existante : "yyyy" â†’ un POI au milieu des Deux-SÃ¨vres, "xxxxx" â†’ un
    nom de cheval dans un haras, etc.

    En mode --oui, lÃ¨ve une erreur claire si le rÃ©sultat n'est pas un lieu
    administratif/habitÃ© reconnu. En mode interactif, demande confirmation.
    """
    # Le code pays vient du provider actif. Nominatim filtre par ISO code
    # (countrycodes=fr/nl/etc.) â€” Ã©vite "Amsterdam" â†’ "ÃŽle d'Amsterdam (TAAF, FR)"
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
        print(f"  ERREUR : ville non trouvÃ©e : {nom_ville}")
        return None, None

    # Validation du type de lieu retournÃ©
    # Lieux acceptÃ©s sans question : entitÃ©s administratives ou habitÃ©es clairement
    # nommÃ©es. "locality" et "isolated_dwelling" sont OSM-spÃ©cifiques et marquent
    # respectivement un hameau non-officiel et une habitation isolÃ©e â€” acceptÃ©s
    # mais avec un avertissement.
    TYPES_OK    = {"city", "town", "village", "municipality", "administrative",
                   "suburb", "quarter", "neighbourhood"}
    TYPES_DOUTE = {"hamlet", "locality", "isolated_dwelling", "farm"}

    addrtype = (data[0].get("addresstype") or "").lower()
    display  = data[0].get("display_name", "(?)")
    cat      = (data[0].get("class") or "").lower()

    # Rejet immÃ©diat si pas un lieu (boutique, restaurant, route, etc.)
    if cat not in ("place", "boundary", "landuse"):
        msg = (f"  ERREUR : lieu '{nom_ville}' non reconnu comme ville/village.\n"
               f"  Nominatim a renvoyÃ© : {display} (type={cat}/{addrtype}).\n"
               f"  PrÃ©cisez le nom de la commune.")
        print(msg)
        return None, None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    # Type non-administratif â†’ demander confirmation (ou rejeter en mode --oui)
    if addrtype not in TYPES_OK:
        if addrtype in TYPES_DOUTE:
            # Lieu-dit ou hameau : signaler mais accepter
            print(f"  âš  '{nom_ville}' rÃ©solu en {display} (type={addrtype}).")
            print(f"  VÃ©rifiez que c'est bien le lieu attendu.")
        else:
            # Type complÃ¨tement inattendu (industrial, retail, etc.) : rejeter
            print(f"  ERREUR : lieu '{nom_ville}' ambigu â€” Nominatim a renvoyÃ© "
                  f"{display} (type={addrtype}).")
            print(f"  PrÃ©cisez le nom complet (commune, pas POI).")
            return None, None

    print(f"  {nom_ville} -> lat={lat:.5f}, lon={lon:.5f}")
    return lat, lon


def geocoder_ville_l93(nom_ville):
    """GÃ©ocode une ville et retourne (x, y) en Lambert 93 (pour le pipeline LiDAR). Retourne (None, None) si Ã©chec."""
    lat, lon = geocoder_ville_wgs84(nom_ville)
    if lat is None:
        return None, None
    try:
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        x, y = t.transform(lon, lat)
    except ImportError:
        x, y = wgs84_to_lamb93_approx(lon, lat)
        print("  (pyproj absent, conversion approchÃ©e)")
    print(f"  Lambert 93 -> X={x:.0f}, Y={y:.0f}")
    return x, y


def geocoder_departement(num_dep):
    """
    Retourne (nom, bx1, by1, bx2, by2) en Lambert 93 via Overpass API OSM.
    RequÃªte par ref:INSEE + admin_level=6 (dÃ©partement franÃ§ais) â†’ bounds exact.
    RÃ©sultat mis en cache dans dep_bbox_cache.json Ã  cÃ´tÃ© du script.
    Si Overpass indisponible et cache existant â†’ utilise le cache.
    """
    # â”€â”€ Cache local â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        print(f"  DÃ©partement {num_dep} â€” {c['nom']} (cache local)", flush=True)
        print(f"  BBox WGS84 : {c['lon_min']:.4f},{c['lat_min']:.4f} â†’ "
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
        print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} â†’ {bx2:.0f},{by2:.0f}")
        print(f"  Surface estimÃ©e : ~{surface_km2:.0f} kmÂ²")
        return c['nom'], bx1, by1, bx2, by2

    # Overpass : relation administrative de niveau dÃ©partement, identifiÃ©e par ref:INSEE
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
                print(f"  Overpass indisponible ({type(e).__name__}: {e}) â€” retry {_tentative_ovp+1}/3...",
                      flush=True)
                time.sleep(5)
            else:
                print(f"  ERREUR Overpass : {type(e).__name__}: {e}")

    if lat_min is None:
        print(f"  ERREUR : impossible de gÃ©ocoder le dÃ©partement {num_dep}.")
        print(f"  Overpass API indisponible. Utilisez --bbox X1,Y1,X2,Y2 (Lambert 93).")
        print(f"  Exemple Var 83 : --bbox 905000,6214000,1040000,6322000")
        return None, None, None, None, None

    # â”€â”€ Sauvegarde dans le cache â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _cache[num_dep] = {
        "nom": nom, "lat_min": lat_min, "lat_max": lat_max,
        "lon_min": lon_min, "lon_max": lon_max
    }
    try:
        _ecrire_json_atomique(_cache_path, _cache, indent=2)
    except Exception:
        pass  # cache non critique

    print(f"  DÃ©partement {num_dep} â€” {nom}")
    print(f"  BBox WGS84 : {lon_min:.4f},{lat_min:.4f} â†’ {lon_max:.4f},{lat_max:.4f}")

    try:
        t = _get_transformer("EPSG:4326", PROVIDER.CRS_NATIF)
        bx1, by1 = t.transform(lon_min, lat_min)
        bx2, by2 = t.transform(lon_max, lat_max)
    except ImportError:
        bx1, by1 = wgs84_to_lamb93_approx(lon_min, lat_min)
        bx2, by2 = wgs84_to_lamb93_approx(lon_max, lat_max)
        print("  (pyproj absent, conversion approchÃ©e)")

    # Marge de 500 m pour ne pas couper les dalles en bordure
    MARGE = 500
    bx1 -= MARGE; by1 -= MARGE
    bx2 += MARGE; by2 += MARGE

    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} â†’ {bx2:.0f},{by2:.0f}")
    print(f"  Surface estimÃ©e : ~{surface_km2:.0f} kmÂ²")
    return nom, bx1, by1, bx2, by2

def _parser_departements(valeur: str) -> list:
    """
    Parse --zone-departement : valeur simple ou liste/plage.

    Formats acceptÃ©s (combinables) :
      83            â†’ ['83']
      30,35,75      â†’ ['30', '35', '75']
      1-10          â†’ ['01', '02', ..., '10']
      1-3,75,83     â†’ ['01', '02', '03', '75', '83']

    Les codes non entiers (DOM/TOM : 2A, 2B, 971, 972â€¦) sont passÃ©s tels quels.
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
                # ZÃ©ro-padding cohÃ©rent avec geo.api.gouv.fr (01â€¦09)
                codes.append(str(n).zfill(2) if n < 10 else str(n))
        elif re.match(r'^[0-9]+$', token):
            # NumÃ©rique simple : zÃ©ro-padding si chiffre seul
            codes.append(token.zfill(2) if len(token) == 1 else token)
        else:
            codes.append(token)   # 2A, 2B, 971, 972, etc.
    return codes


# ============================================================
# GRILLE DE DALLES
# ============================================================

def calculer_grille_bbox(x1, y1, x2, y2):
    """Retourne (dalles, bbox) depuis une BBox dans le CRS natif du provider.

    Si le provider n'utilise pas de grille rÃ©guliÃ¨re (systÃ¨me kaartblad
    alphanumÃ©rique pour NL AHN, etc.), retourne une liste vide â€” le
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
    """rglob("*.tif") avec gestion des erreurs d'accÃ¨s disque (WinError 121)."""
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
                print(f"  AVERTISSEMENT : dossier inaccessible {sous_dossier.name} ({_e}) â€” ignorÃ©")
    except OSError as _e:
        print(f"  AVERTISSEMENT : dossier dalles inaccessible ({_e})")
    return resultats


def chemin_dalle(dossier_dalles, nom):
    """
    Retourne le Path complet d'une dalle dans la structure sous-dossiers.
    Les dalles sont organisÃ©es par colonne X : dossier_dalles/XXXX/nom.tif
    ex: D:/Lidar/Dalles/0958/LHD_FXX_0958_6279_MNT_O_0M50_LAMB93_IGN69.tif

    Fallback transparent : si la dalle existe Ã  la racine (ancienne structure),
    retourne le chemin racine. Sinon retourne le chemin sous-dossier.
    """
    # Chemin racine (ancienne structure)
    chemin_racine = dossier_dalles / nom
    if chemin_racine.exists():
        return chemin_racine
    # DÃ©lÃ©gation au provider pour extraire le sous-dossier depuis le nom
    sub = PROVIDER.subdir_from_name(nom)
    if sub:
        return dossier_dalles / sub / nom
    return chemin_racine  # fallback si nom non reconnu


def construire_url_wms(x_km, y_km):
    """DÃ©lÃ©gation au provider â€” la logique URL/CRS/format dÃ©pend de la source."""
    return PROVIDER.dalle_url(x_km, y_km)


def _lon_lat_to_tile(lon, lat, z):
    """Convertit lon/lat WGS84 en coordonnÃ©es tuile XYZ (x, y) au zoom z.

    Convention Google/OSM : y=0 en haut. Alias historique de deg_to_tile
    (ordre des arguments : lon, lat).
    """
    return deg_to_tile(lat, lon, z)


def interroger_tms_dalles(lon_min, lat_min, lon_max, lat_max, bbox_l93=None):
    """Wrapper vers PROVIDER.discover_dalles â€” voir providers/fr_ign.py.
    Retourne {nom_dalle: url_wms} ou None si erreur totale."""
    cache_path = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
    return PROVIDER.discover_dalles(
        (lon_min, lat_min, lon_max, lat_max), bbox_l93, cache_path)


def _download_to_tmp(url, chemin_tmp, timeout=60):
    """
    TÃ©lÃ©charge url vers chemin_tmp (streaming).
    Retourne le nombre d'octets Ã©crits, ou lÃ¨ve une exception.
    GÃ¨re les rÃ©ponses WMS XML/HTML d'erreur â†’ retourne 0 (dalle absente).
    timeout : tuple (connexion_s, lecture_s) ou entier.

    Protection contre les coupures TCP silencieuses (typiques sur VM/macOS) :
    si le serveur annonce Content-Length, on vÃ©rifie que la taille reÃ§ue
    correspond exactement â€” sinon on lÃ¨ve IOError pour dÃ©clencher le retry.
    Sur Windows, urllib/WinINet lÃ¨ve une exception dans ce cas ; sur macOS/Linux
    la socket BSD renvoie b"" sans erreur, ce qui sans cette garde produirait
    un fichier tronquÃ© acceptÃ© silencieusement comme valide.
    """
    # Pas de _log_req(url) ici : cette fonction est appelÃ©e des centaines Ã 
    # milliers de fois en parallÃ¨le (1 par dalle WMS) â†’ le spam URL noie la
    # console. La progress bar de _telecharger_dalles_zone suffit ; les
    # erreurs sont loguÃ©es par le code de retry des callers.
    # Timeout lecture : prendre la valeur max si tuple (connect, read).
    _timeout = max(timeout) if isinstance(timeout, tuple) else timeout
    try:
        resp = _urlopen(url, timeout=_timeout)
    except urllib.error.HTTPError as _e:
        if _e.code == 404:
            return 0
        raise IOError(f"HTTP {_e.code}") from _e

    # `with` ferme la connexion HTTP mÃªme sur exception â†’ pas de fuite de FD
    # (cas observÃ© avec 8 workers parallÃ¨les Ã— centaines de dalles).
    with resp:
        ct = resp.headers.get("content-type", "")
        if "xml" in ct or "html" in ct:
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

    # VÃ©rification d'intÃ©gritÃ© : si Content-Length Ã©tait annoncÃ© et ne correspond
    # pas, la connexion a Ã©tÃ© coupÃ©e silencieusement â†’ le fichier est tronquÃ©.
    # On lÃ¨ve une IOError pour que l'appelant dÃ©clenche le retry automatique.
    if content_length > 0 and buf_size != content_length:
        raise IOError(
            f"Transfert tronquÃ© : reÃ§u {buf_size} octets, "
            f"attendu {content_length} (Content-Length)"
        )
    return buf_size


def _valider_tif_dalle(chemin):
    """
    VÃ©rifie qu'un fichier TIF tÃ©lÃ©chargÃ© est un GeoTIFF valide et lisible.

    Deux niveaux de vÃ©rification :
      1. Magic bytes (rapide, sans dÃ©pendance) : les 4 premiers octets d'un
         TIFF sont toujours 49 49 2A 00 (little-endian) ou 4D 4D 00 2A
         (big-endian). Un fichier tronquÃ© au milieu du transfert n'aura pas
         ces octets, ou aura un IFD invalide.
      2. Ouverture rasterio (si disponible) : tente de lire les mÃ©tadonnÃ©es
         (width, height, CRS) pour dÃ©tecter les TIF dont le header est intact
         mais dont les donnÃ©es sont corrompues ou tronquÃ©es.

    Retourne True si le fichier est valide, False sinon.
    Ne lÃ¨ve jamais d'exception.
    """
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
        # TIFF magic = II/MM (byte order) + 42 ou 43 (BigTIFF, supportÃ© par
        # rasterio/GDAL). BigTIFF est utilisÃ© par certains COG (ex: AHN PDOK)
        # mÃªme pour des fichiers < 4 Go. Refuser BigTIFF = faux nÃ©gatif.
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

    # VÃ©rification approfondie via rasterio si disponible
    try:
        import rasterio as _rio_v
        with _rio_v.open(str(chemin)) as ds:
            if ds.width == 0 or ds.height == 0:
                return False
            # Lire 1 bloc pour dÃ©tecter une troncature des donnÃ©es
            ds.read(1, window=_rio_v.windows.Window(
                0, 0, min(64, ds.width), min(64, ds.height)))
    except Exception:
        # rasterio non disponible ou erreur de lecture â†’ on se fie au magic seul
        pass

    return True


def telecharger_dalle_directe(nom, url_wms, dossier, ecraser=False):
    """TÃ©lÃ©charge une dalle depuis son URL WMS fournie par le TMS IGN."""
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        if not ecraser:
            return "skip"
        # Mode Ã©crasement : supprimer l'existant pour forcer le retÃ©lÃ©chargement.
        # On Ã©vite de tirer dans une dalle valide qui pourrait servir de fallback
        # en cas d'Ã©chec â€” mais c'est explicitement ce que l'utilisateur demande.
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
            if not _valider_tif_dalle(chemin):
                chemin.unlink(missing_ok=True)
                raise IOError("GeoTIFF invalide aprÃ¨s Ã©criture (fichier tronquÃ© ou corrompu)")
            # Hook post-download : permet Ã  un provider de transformer le tile
            # (ex: us-3dep reprojette NAD83 -> EPSG:3857 ici).
            if hasattr(PROVIDER, "post_download"):
                try:
                    PROVIDER.post_download(chemin)
                except Exception as _e_pd:
                    print(f"  âš  post_download {nom} : {type(_e_pd).__name__}: {_e_pd}",
                          flush=True)
            _creer_fichier(chemin)
            return "ok"
        except KeyboardInterrupt:
            chemin_tmp.unlink(missing_ok=True)
            # Propagation au handler top-level (sys.exit(130)) qui finalise
            # le cleanup global (manifeste, lockfilesâ€¦). sys.exit(0) ici
            # masquerait l'interruption derriÃ¨re un code de succÃ¨s.
            raise
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, IOError) as _e:
            chemin_tmp.unlink(missing_ok=True)
            chemin.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                # Retry silencieux : IGN renvoie 502/400/timeouts en rafale en
                # journÃ©e, chaque retry print bourrait la console. Seul l'Ã©chec
                # final (3/3) reste visible â€” la progress bar montre l'avancÃ©e.
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR {nom} ({type(_e).__name__}, tentative {tentative}) : {_e}")
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

            if not _valider_tif_dalle(chemin):
                chemin.unlink(missing_ok=True)
                raise IOError("GeoTIFF invalide aprÃ¨s Ã©criture (fichier tronquÃ© ou corrompu)")
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
                # Cf. telecharger_dalle_directe : retry silencieux pour Ã©viter
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
    TÃ©lÃ©charge osmosis dans ./osmosis/ depuis GitHub releases.
    osmosis est un JAR Java autonome â€” nÃ©cessite Java installÃ©.
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
    print("  TÃ©lÃ©chargement osmosis (~35 Mo)...", flush=True)
    try:
        def _prog(n, bs, total):
            if total > 0:
                print("  " + str(min(n*bs*100//total, 100)).rjust(3) + "%",
                      end="\r", flush=True)
        urllib.request.urlretrieve(URL, zip_path, reporthook=_prog)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERREUR tÃ©lÃ©chargement osmosis : {type(e).__name__}: {e}")
        return None

    print(f"  Extraction osmosis...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        _safe_zip_extractall(z, OSMOSIS_DIR)
    zip_path.unlink(missing_ok=True)

    # Le ZIP extrait dans un sous-dossier versionnÃ© (ex: osmosis-0.49.2/)
    # On cherche le binaire par rglob plutÃ´t qu'un chemin fixe
    pattern = "osmosis.bat" if WINDOWS else "osmosis"
    for candidate in sorted(OSMOSIS_DIR.rglob(pattern)):
        if candidate.is_file() and "bin" in candidate.parts:
            if not WINDOWS:
                import stat as _stat
                candidate.chmod(candidate.stat().st_mode | _stat.S_IEXEC)
            print(f"  osmosis installÃ© : {candidate}")
            return str(candidate)
    print("  ERREUR : osmosis introuvable aprÃ¨s extraction.")
    return None


def _telecharger_jre_local():
    """
    TÃ©lÃ©charge le JRE Temurin (Eclipse Adoptium) dans ./jre/ â€” portable,
    sans installation systÃ¨me, sans droits admin.
    Fonctionne sur Windows (zip), Linux et macOS (tar.gz), x64 et arm64.
    """
    import tarfile, zipfile

    JRE_DIR = LIDAR2MAP_HOME / "jre"

    # DÃ©tection OS
    sys_os = platform.system().lower()
    if sys_os == "windows":
        os_str, ext, java_bin = "windows", "zip",    "bin/java.exe"
    elif sys_os == "darwin":
        os_str, ext, java_bin = "mac",     "tar.gz", "bin/java"
    else:
        os_str, ext, java_bin = "linux",   "tar.gz", "bin/java"

    # DÃ©tection architecture
    machine = platform.machine().lower()
    arch_str = "aarch64" if machine in ("arm64", "aarch64") else "x64"

    # URL stable Adoptium API â€” JRE 21 LTS
    URL = (f"https://api.adoptium.net/v3/binary/latest/21/ga"
           f"/{os_str}/{arch_str}/jre/hotspot/normal/eclipse")

    archive = JRE_DIR / f"jre.{ext}"
    JRE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  URL  : {URL}")
    print(f"  TÃ©lÃ©chargement JRE Temurin 21 ({os_str}/{arch_str}, ~50 Mo)...",
          flush=True)
    try:
        # L'API Adoptium fait une redirection 302 vers GitHub.
        # GitHub exige un User-Agent â€” urlretrieve seul renvoie 403.
        # On rÃ©sout d'abord l'URL finale, puis on tÃ©lÃ©charge avec headers.
        _headers = {"User-Agent": "lidar2map/1.0 (JRE bootstrap)",
                    "Accept":     "application/octet-stream"}

        # RÃ©solution de la redirection
        _req = urllib.request.Request(URL, headers=_headers)
        with urllib.request.urlopen(_req, timeout=30) as _resp:
            _final_url = _resp.url  # URL finale aprÃ¨s redirection(s)

        # TÃ©lÃ©chargement avec progression
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
        print(f"  ERREUR tÃ©lÃ©chargement JRE : {type(e).__name__}: {e}")
        return None

    print("  Extraction JRE...", flush=True)
    if ext == "zip":
        with zipfile.ZipFile(archive, "r") as z:
            _safe_zip_extractall(z, JRE_DIR)
    else:
        with tarfile.open(archive, "r:gz") as t:
            # Python 3.12+ : filter='data' requis pour bloquer les exploits
            # (chemins absolus, traversÃ©e ../, liens symboliques sortants).
            # Python 3.11- : pas de support du paramÃ¨tre â†’ fallback.
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
            print(f"  JRE installÃ© : {candidate}")
            return str(candidate)

    print("  ERREUR : binaire java introuvable aprÃ¨s extraction.")
    return None


def _trouver_java():
    """
    Retourne le chemin vers le binaire java local (~/.lidar2map/jre/).
    TÃ©lÃ©charge le JRE Temurin si absent. Jamais le Java systÃ¨me.

    Mode frozen : cherche d'abord dans BUNDLE_DIR/jre/ (JRE embarquÃ©).
    """

    java_bin = "java.exe" if WINDOWS else "java"

    # 1) Mode frozen : JRE bundlÃ© dans l'exe
    if getattr(sys, "frozen", False):
        for candidate in sorted((BUNDLE_DIR / "jre").rglob(java_bin)):
            if candidate.exists():
                return str(candidate)

    # 2) Installation locale persistante (~/.lidar2map/jre/)
    for candidate in sorted((LIDAR2MAP_HOME / "jre").rglob(java_bin)):
        if candidate.exists():
            return str(candidate)

    # 3) Absent : tÃ©lÃ©chargement automatique
    java = _telecharger_jre_local()
    if not java:
        print("  ERREUR : impossible d'obtenir un JRE.")
        print("  Installez Java manuellement : https://adoptium.net/")
    return java


def _trouver_osmosis():
    """Retourne le chemin vers osmosis (installation locale ou tÃ©lÃ©chargement).
    MÃªme logique que GDAL : pas de fallback PATH systÃ¨me.
    PrÃ©requis : appeler _trouver_java() avant (responsabilitÃ© de l'appelant).

    Mode frozen : cherche d'abord dans BUNDLE_DIR/osmosis/ (osmosis embarquÃ©,
    avec le plugin mapwriter prÃ©-installÃ© dans son lib/)."""
    # 1) Mode frozen : osmosis bundlÃ© dans l'exe
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

    # 3) Absent : tÃ©lÃ©chargement automatique
    return _telecharger_osmosis_local()


_MAPWRITER_VERSION = "0.25.0"
_MAPWRITER_JAR     = f"mapsforge-map-writer-{_MAPWRITER_VERSION}-jar-with-dependencies.jar"
_MAPWRITER_URL     = (
    f"https://repo1.maven.org/maven2/org/mapsforge/mapsforge-map-writer"
    f"/{_MAPWRITER_VERSION}/{_MAPWRITER_JAR}"
)


def _verifier_mapwriter():
    """
    VÃ©rifie que le plugin mapsforge-map-writer est installÃ© dans le dossier
    plugins d'osmosis. TÃ©lÃ©charge automatiquement si absent.

    Dossier plugins (toutes plateformes) :
      Windows  : %USERPROFILE%\\.openstreetmap\\osmosis\\plugins\\
      Linux    : ~/.openstreetmap/osmosis/plugins/
      macOS    : ~/.openstreetmap/osmosis/plugins/

    Mode frozen : le plugin est embarquÃ© dans osmosis/lib/ (osmosis.bat
    bundlÃ© inclut le jar dans son CLASSPATH) â€” rien Ã  vÃ©rifier ici.
    """
    # Mode frozen : plugin dÃ©jÃ  sur le classpath d'osmosis, court-circuit.
    if getattr(sys, "frozen", False):
        return True

    plugins_dir = Path.home() / ".openstreetmap" / "osmosis" / "plugins"
    jar_path    = plugins_dir / _MAPWRITER_JAR

    if jar_path.exists():
        return True

    print(f"  URL  : {_MAPWRITER_URL}")
    print(f"  Plugin mapwriter absent â€” tÃ©lÃ©chargement ({_MAPWRITER_JAR})...",
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
        print(f"  ERREUR tÃ©lÃ©chargement mapwriter : {type(e).__name__}: {e}")
        print(f"  TÃ©lÃ©chargez manuellement :\n    {_MAPWRITER_URL}")
        print(f"  et copiez-le dans :\n    {plugins_dir}")
        return False

    print(f"  Plugin installÃ© : {jar_path}")
    return True


# â”€â”€ --telecharger-outils â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PlacÃ© ici car nÃ©cessite _trouver_java() et _trouver_osmosis() dÃ©finis
# ci-dessus. Le flag est dÃ©tectÃ© tÃ´t (avant bootstrap) pour passer dans
# le re-exec venv, mais exÃ©cutÃ© ici pour que les fonctions soient disponibles.
if _TELECHARGER_OUTILS:
    print()
    print("  â”€â”€ TÃ©lÃ©chargement des outils (osmosis + JRE + mapwriter) â”€â”€â”€â”€â”€â”€")
    print()
    _java = _trouver_java()
    if _java:
        print(f"  âœ“ JRE dÃ©jÃ  prÃ©sent : {_java}")
    else:
        print("  âš  JRE : Ã©chec du tÃ©lÃ©chargement")
    _osmo = _trouver_osmosis()
    if _osmo:
        print(f"  âœ“ osmosis dÃ©jÃ  prÃ©sent : {_osmo}")
    else:
        print("  âš  osmosis : Ã©chec du tÃ©lÃ©chargement")
    # Plugin mapsforge-map-writer : indispensable pour gÃ©nÃ©rer les .map OSM.
    # Sans lui, osmosis Ã©choue avec "Task type mapfile-writer doesn't exist".
    # Le spec PyInstaller le rÃ©cupÃ¨re depuis ~/.openstreetmap/osmosis/plugins/
    # pour le bundler dans osmosis/lib/ du .app/.exe.
    if _verifier_mapwriter():
        print(f"  âœ“ mapwriter prÃ©sent : ~/.openstreetmap/osmosis/plugins/{_MAPWRITER_JAR}")
    else:
        print("  âš  mapwriter : Ã©chec du tÃ©lÃ©chargement â€” la gÃ©nÃ©ration .map Ã©chouera")
    print()
    sys.exit(0)


def _trouver_outil_gdal(nom):
    """[DEPRECATED aprÃ¨s refactor rasterio] Cherche un exe GDAL CLI.

    Cette fonction est conservÃ©e pour compatibilitÃ© avec les variables
    encore initialisÃ©es dans le code (gdaldem, gdalwarp, gdalbuildvrt etc.),
    mais aprÃ¨s le refactor rasterio (Ã©tapes 1-7) ces exes ne sont plus
    appelÃ©s. La fonction retourne maintenant None sans dÃ©clencher
    d'auto-installation systÃ¨me de GDAL.

    Si une future version a vraiment besoin d'un outil GDAL CLI (peu probable),
    il faudra restaurer la stratÃ©gie 1+2+3+4 d'origine.
    """
    return None


def _geoinfo_depuis_gdalinfo(src_tif, env=None):
    """
    Retourne (geotransform_str, srs_wkt) pour src_tif via rasterio.

    geotransform_str : 6 valeurs sÃ©parÃ©es par virgules (xmin, xres, 0, ymax, 0, -yres)

    Le paramÃ¨tre `env` est conservÃ© pour compatibilitÃ© historique mais n'est
    plus utilisÃ© : rasterio embarque sa propre libgdal/proj.db via le wheel pip.
    Pas besoin de PROJ_LIB ou GDAL_DATA externes.
    """
    try:
        import rasterio
        with rasterio.open(str(src_tif)) as ds:
            tr = ds.transform   # affine: a, b, c, d, e, f
            # tr.a = xres, tr.b = 0 (pas de rotation), tr.c = xmin
            # tr.d = 0, tr.e = -yres (nÃ©gatif pour y descend), tr.f = ymax
            gt = [tr.c, tr.a, tr.b, tr.f, tr.d, tr.e]  # ordre GDAL classique
            srs_wkt = ds.crs.to_wkt() if ds.crs else ""
            return ",".join(str(v) for v in gt), srs_wkt
    except Exception:
        return None, None


def _sauver_array_georef(arr, src_tif, dst_tif, gdal_translate_exe=None, env=None):
    """
    Sauvegarde un numpy array uint8 (2D niveaux de gris ou 3D RGB) en GeoTIFF
    en copiant le gÃ©orÃ©fÃ©rencement de src_tif via rasterio.

    arr   : numpy uint8 shape (H,W) pour L, (H,W,3) pour RGB

    Les paramÃ¨tres `gdal_translate_exe` et `env` sont conservÃ©s pour compatibilitÃ©
    historique mais ne sont plus utilisÃ©s (rasterio est dÃ©sormais une dÃ©pendance
    obligatoire â€” voir _installer_deps).
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
    # Supprimer les clÃ©s incompatibles Ã©ventuelles
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


# â”€â”€ Helpers lecture DEM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _lire_dem_rasterio(src_path):
    """
    Lit un GeoTIFF DEM (bande 1) et retourne un numpy float32.

    Utilise rasterio en prioritÃ© (gestion native du nodata, DEFLATE, BigTIFF).
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
        print(f"  AVERTISSEMENT rasterio read ({e_rio}) â€” repli PIL", flush=True)

    from PIL import Image as _Img
    return np.array(_Img.open(str(src_path)), dtype=np.float32), None


# â”€â”€ Hillshade et slope numpy (remplacent gdaldem CLI) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Cache des kernels Numba (compilation paresseuse au 1er appel, partagÃ©e entre
# tous les modes â€” Ã©vite la double compilation entre _svf_numpy et _svf_chunked,
# et entre les variantes hillshade/multi/slope).
_NUMBA_KERNELS_CACHE = {}


def _get_numba_horn_kernels():
    """Compile et cache les kernels Numba pour Horn (hillshade, multi, slope).

    Une seule passe sur le DEM par kernel : gradient Horn 3x3 + projection
    solaire + Ã©criture uint8 directement, sans buffers intermÃ©diaires float32
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
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    g2 = dz_dx * dz_dx + dz_dy * dz_dy
                    # Forme analytique Ã©vitant atan/atan2 :
                    # cos(slope)=1/sqrt(1+gÂ²), sin(slope)*cos(aspect)=-dz_dx/sqrt(1+gÂ²),
                    # sin(slope)*sin(aspect)=dz_dy/sqrt(1+gÂ²)
                    # â†’ hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) / sqrt(1+gÂ²)
                    inv_sqrt = 1.0 / _math.sqrt(1.0 + g2)
                    hs = (cos_z + sin_z * (-cos_a * dz_dx + sin_a * dz_dy)) * inv_sqrt
                    if hs < 0.0:
                        hs = 0.0
                    elif hs > 1.0:
                        hs = 1.0
                    v = int(hs * 254.0 + 1.0)
                    if has_nodata and dem[row, col] == nodata:
                        v = 0
                    out[row, col] = v
            return out

        @_nb.njit(parallel=True, fastmath=True)
        def _multi_kernel(dem, dx, dy, zen_rad, nodata, has_nodata):
            h, w = dem.shape
            out = _np.empty((h, w), dtype=_np.uint8)
            cos_z = _math.cos(zen_rad)
            sin_z = _math.sin(zen_rad)
            inv_8dx = 1.0 / (8.0 * dx)
            inv_8dy = 1.0 / (8.0 * dy)
            # Azimuts GDAL : 225, 270, 315, 360 â†’ az_math = 360 - az + 90
            # â†’ 225, 180, 135, 90
            az0_c = _math.cos(_math.radians(225.0)); az0_s = _math.sin(_math.radians(225.0))
            az1_c = _math.cos(_math.radians(180.0)); az1_s = _math.sin(_math.radians(180.0))
            az2_c = _math.cos(_math.radians(135.0)); az2_s = _math.sin(_math.radians(135.0))
            az3_c = _math.cos(_math.radians( 90.0)); az3_s = _math.sin(_math.radians( 90.0))
            for row in _nb.prange(h):
                rm = row - 1 if row > 0 else 0
                rp = row + 1 if row < h - 1 else h - 1
                for col in range(w):
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
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
                    # 4 azimuts dÃ©roulÃ©s
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
                    v = int(hs_avg * 254.0 + 1.0)
                    if has_nodata and dem[row, col] == nodata:
                        v = 0
                    out[row, col] = v
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
                    cm = col - 1 if col > 0 else 0
                    cp = col + 1 if col < w - 1 else w - 1
                    a = dem[rm, cm]; b = dem[rm, col]; c = dem[rm, cp]
                    d = dem[row, cm];                  f = dem[row, cp]
                    g = dem[rp, cm]; hv = dem[rp, col]; i = dem[rp, cp]
                    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) * inv_8dx
                    dz_dy = ((g + 2.0 * hv + i) - (a + 2.0 * b + c)) * inv_8dy
                    slope_deg = _math.degrees(_math.atan(_math.sqrt(dz_dx * dz_dx + dz_dy * dz_dy)))
                    if slope_deg < 0.0:
                        slope_deg = 0.0
                    elif slope_deg > 90.0:
                        slope_deg = 90.0
                    v = int(slope_deg)
                    if has_nodata and dem[row, col] == nodata:
                        v = 0
                    out[row, col] = v
            return out

        kernels = (_hillshade_kernel, _multi_kernel, _slope_kernel)
        _NUMBA_KERNELS_CACHE["horn"] = kernels
        return kernels
    except ImportError:
        _NUMBA_KERNELS_CACHE["horn"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernels Horn : erreur compilation ({_e}) â€” fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["horn"] = None
        return None


def _get_numba_svf_kernel():
    """Compile et cache le kernel Numba SVF (ray-casting horizon avec interp
    bilinÃ©aire). RÃ©utilisÃ© par _svf_numpy et _svf_chunked â€” Ã©vite la double
    compilation initiale (~20 s Ã— 2).
    """
    if "svf" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_kernel(dem, n_dir, max_r, res):
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
                        for r in range(1, max_r + 1):
                            rr = row + ddy * r
                            cc = col + ddx * r
                            r0i = int(_math.floor(rr))
                            c0i = int(_math.floor(cc))
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
                            fr = rr - _math.floor(rr)
                            fc = cc - _math.floor(cc)
                            zn = (dem[r0i, c0i] * (1 - fr) * (1 - fc) +
                                  dem[r0i, c1i] * (1 - fr) *      fc  +
                                  dem[r1i, c0i] *      fr  * (1 - fc) +
                                  dem[r1i, c1i] *      fr  *      fc)
                            dist_m = r * res
                            tan_a  = (zn - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a
                        mt = max_tan if max_tan > 0.0 else 0.0
                        svf_sum += 1.0 / (1.0 + mt * mt)
                    out[row, col] = svf_sum / n_dir
            return out

        _NUMBA_KERNELS_CACHE["svf"] = _svf_kernel
        return _svf_kernel
    except ImportError:
        _NUMBA_KERNELS_CACHE["svf"] = None
        return None
    except Exception as _e:
        print(f"  Numba kernel SVF : erreur compilation ({_e}) â€” fallback numpy", flush=True)
        _NUMBA_KERNELS_CACHE["svf"] = None
        return None


def _get_numba_svf_sweep_kernel():
    """Sweep-horizon SVF avec running max sur deque (upper convex hull).

    Algorithme :
    - Pour chaque direction Î¸, balayage de lignes parallÃ¨les grid-aligned
      Ã  travers la grille
    - Chaque pixel visitÃ© exactement une fois par direction
    - Maintient une deque des points "skyline" passÃ©s (upper convex hull)
    - Pop arriÃ¨re les points dominÃ©s Ã  l'ajout (prÃ©serve la propriÃ©tÃ© de hull)
    - Pop avant les points hors fenÃªtre max_r (cap distance)
    - Horizon angle = scan du hull, query en O(hull_size) amorti

    ComplexitÃ© : O(WÂ·HÂ·N + WÂ·HÂ·hull_size_moyen)
    au lieu de O(WÂ·HÂ·NÂ·max_r) du ray-cast classique.

    Pour terrain naturel (hull_size ~5-10), speedup vs ray-cast bilinÃ©aire :
        max_r=40    (SVF 20m)   â†’ ~Ã—5-15
        max_r=200   (SVF 100m)  â†’ ~Ã—30-50
        max_r=40000 (SVF 20km)  â†’ ~Ã—500+

    Trade-off : nearest-neighbor pixel access le long de la scan-line (pas
    d'interp bilinÃ©aire sub-pixel). Aliasing nÃ©gligeable pour structures
    > 1-2 px sur DEM 0.5 m/px.

    âš  SÃ©mantique des directions : ce kernel balaie en direction (ddx, ddy) et
    accumule l'horizon depuis les pixels passÃ©s sur la scan-line, qui sont
    donc en direction -Î¸ par rapport au pixel courant. Pour SVF la somme sur
    N directions Ã©qui-rÃ©parties est invariante par cette permutation (-Î¸_k
    â‰¡ Î¸_{N-k} mod 2Ï€) â€” rÃ©sultat numÃ©rique correct. Ã€ NE PAS rÃ©utiliser tel
    quel pour un calcul asymÃ©trique single-direction (ex: horizon Ã  un
    azimut donnÃ©, ombre solaire) : inverser le sens du balayage ou
    rÃ©interprÃ©ter k.
    """
    if "svf_sweep" in _NUMBA_KERNELS_CACHE:
        return _NUMBA_KERNELS_CACHE["svf_sweep"]
    try:
        import numba as _nb
        import numpy as _np
        import math as _math

        @_nb.njit(parallel=True, fastmath=True)
        def _svf_sweep_kernel(dem, n_dir, max_r, res):
            h, w = dem.shape
            PI2 = 2.0 * _math.pi
            out = _np.zeros((h, w), dtype=_np.float32)
            # CapacitÃ© deque : max_r + petite marge pour gÃ©rer push avant pop
            DEQ_CAP = max_r + 8

            for k_dir in range(n_dir):
                angle = k_dir * PI2 / n_dir
                ddx =  _math.sin(angle)
                ddy = -_math.cos(angle)
                abs_dx = abs(ddx)
                abs_dy = abs(ddy)

                if abs_dx >= abs_dy:
                    # â”€â”€ Direction x-dominante : scan-lines balaient en x â”€â”€â”€â”€â”€â”€
                    sx = 1 if ddx > 0 else -1
                    slope_y = ddy / abs_dx  # |slope_y| <= 1
                    step_dist = res * _math.sqrt(1.0 + slope_y * slope_y)
                    # max_steps = nombre max de steps scan-line correspondant Ã  max_r px le long du rayon
                    max_steps_back = int(max_r / _math.sqrt(1.0 + slope_y * slope_y) + 0.5)
                    if max_steps_back < 1:
                        max_steps_back = 1
                    # slope appliquÃ© dans le sens du balayage
                    slope_y_signed = slope_y if sx > 0 else -slope_y
                    # Couverture des seed_y0 : chaque pixel (r, c) est sur seed_y0 = round(r - c_progress * slope)
                    # oÃ¹ c_progress = c si sx>0 sinon (w-1-c). Etendre la plage pour couvrir tout.
                    extra = int(_math.ceil(abs(slope_y) * w)) + 2
                    y0_min = -extra
                    y0_max = h + extra

                    for seed_y0 in _nb.prange(y0_min, y0_max + 1):
                        # Buffers deque (per-scan-line, allouÃ©s par numba dans la prange)
                        deque_step = _np.empty(DEQ_CAP, dtype=_np.int32)
                        deque_z    = _np.empty(DEQ_CAP, dtype=_np.float32)
                        head = 0
                        tail = 0

                        # ItÃ©ration en x dans le sens sx
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

                            # Pop avant : points hors fenÃªtre max_r
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

                            # Pop arriÃ¨re : maintien upper convex hull
                            # Tant qu'on a >= 2 points en queue, vÃ©rifier si l'avant-dernier
                            # est sous la droite (avant-avant-dernier â†’ new). Si oui, pop.
                            while True:
                                # Taille deque
                                sz = (tail - head + DEQ_CAP) % DEQ_CAP
                                if sz < 2:
                                    break
                                tm1 = (tail - 1) % DEQ_CAP
                                tm2 = (tail - 2) % DEQ_CAP
                                s2 = deque_step[tm1]; z2 = deque_z[tm1]
                                s1 = deque_step[tm2]; z1 = deque_z[tm2]
                                # Upper hull : s2 doit Ãªtre au-DESSUS de la droite (s1,z1)â†’(step_idx,z_curr)
                                # i.e. (z2 - z1) * (step_idx - s1) > (s2 - s1) * (z_curr - z1)
                                lhs = (z2 - z1) * (step_idx - s1)
                                rhs = (s2 - s1) * (z_curr - z1)
                                if lhs <= rhs:
                                    # s2 sous la droite â†’ dominÃ©, pop
                                    tail = tm1
                                else:
                                    break

                            # Push (step_idx, z_curr)
                            deque_step[tail] = step_idx
                            deque_z[tail]    = z_curr
                            tail = (tail + 1) % DEQ_CAP

                            # Accumulation SVF
                            out[r, c] += 1.0 / (1.0 + max_tan * max_tan)
                else:
                    # â”€â”€ Direction y-dominante : scan-lines balaient en y â”€â”€â”€â”€â”€â”€
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

                            out[r, c] += 1.0 / (1.0 + max_tan * max_tan)

            # Normalisation : moyenne sur n_dir
            inv_n = 1.0 / n_dir
            for r in range(h):
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


def _calc_slope_aspect(dem, dx=0.5, dy=0.5):
    """Calcule slope (radians) et aspect (radians) d'un DEM via la formule Horn 1981.

    Horn 1981 utilise une fenÃªtre 3x3 avec pondÃ©ration centrale 2Ã— pour
    limiter le bruit. C'est la formule par dÃ©faut de gdaldem.

    dx, dy : taille du pixel en mÃ¨tres (X et Y, identiques pour LiDAR)

    Retourne (slope_rad, aspect_rad) en arrays float32 mÃªme shape que dem.
    """
    import numpy as np

    # Convolution 3x3 manuelle via padding + slicing â€” beaucoup plus rapide
    # que scipy.ndimage.convolve sur ces matrices simples
    dem = dem.astype(np.float32)
    pad = np.pad(dem, 1, mode="edge")  # edge replication (compat GDAL)
    a = pad[0:-2, 0:-2]; b = pad[0:-2, 1:-1]; c = pad[0:-2, 2:  ]
    d = pad[1:-1, 0:-2];                       f = pad[1:-1, 2:  ]
    g = pad[2:  , 0:-2]; h = pad[2:  , 1:-1]; i = pad[2:  , 2:  ]

    # dz/dx (Horn) : ((c + 2f + i) - (a + 2d + g)) / (8 * dx)
    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) / (8.0 * dx)
    # dz/dy (Horn) : ((g + 2h + i) - (a + 2b + c)) / (8 * dy)
    # Note : dans GDAL, l'axe Y est inversÃ© (origine en haut-gauche), donc le
    # signe de dy peut diffÃ©rer selon les conventions. On garde la convention
    # Horn standard ici.
    dz_dy = ((g + 2.0 * h + i) - (a + 2.0 * b + c)) / (8.0 * dy)

    # Slope (radians) : atan(sqrt(dz_dxÂ² + dz_dyÂ²))
    slope = np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))

    # Aspect (radians) : atan2(dz_dy, -dz_dx)
    # Convention GDAL : aspect = 0 vers le Nord (Y+ haut), augmente sens horaire
    aspect = np.arctan2(dz_dy, -dz_dx)

    return slope.astype(np.float32), aspect.astype(np.float32)


def _hillshade_numpy(dem, azimuth_deg, altitude_deg, z_factor=1.0, dx=0.5, dy=0.5,
                     nodata=None):
    """Hillshade directionnel â€” formule GDAL standard.

    Reproduit la formule de gdaldem hillshade (-alt -az) :
        hillshade = 255 * (cos(zenith) * cos(slope)
                         + sin(zenith) * sin(slope) * cos(azimuth - aspect))

    azimuth_deg : direction du soleil en degrÃ©s (0=N, 90=E, 180=S, 270=W)
    altitude_deg : hauteur du soleil au-dessus de l'horizon, en degrÃ©s
    z_factor : multiplicateur d'exagÃ©ration verticale (1.0 = pas d'exagÃ©ration)

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    Retourne un array uint8 (0-255) mÃªme shape que dem.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    if z_factor != 1.0:
        dem_f = dem_f * np.float32(z_factor)

    zenith_rad  = math.radians(90.0 - altitude_deg)
    az_math_rad = math.radians(360.0 - azimuth_deg + 90.0)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        hs_kernel, _, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return hs_kernel(dem_f, float(dx), float(dy),
                         az_math_rad, zenith_rad, nd_val, nodata is not None)

    # â”€â”€ Fallback numpy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    slope, aspect = _calc_slope_aspect(dem_f, dx, dy)
    hs = (np.cos(zenith_rad) * np.cos(slope)
          + np.sin(zenith_rad) * np.sin(slope) * np.cos(az_math_rad - aspect))
    hs = np.clip(hs, 0.0, 1.0)
    hs_u8 = (hs * 254.0 + 1.0).astype(np.uint8)
    if nodata is not None:
        hs_u8[dem_f == nodata] = 0
    return hs_u8


def _hillshade_multi_numpy(dem, altitude_deg=45.0, z_factor=1.0, dx=0.5, dy=0.5,
                           nodata=None):
    """Hillshade multidirectionnel â€” formule GDAL `-multidirectional`.

    Calcule 4 hillshades Ã  225Â°, 270Â°, 315Â°, 360Â° et combine via une moyenne
    pondÃ©rÃ©e par sinÂ²(diff) pour Ã©viter les "stripes" du hillshade simple.

    C'est la mÃ©thode "Multidirectional Hillshade" de Mark 1992 / Tait 2010
    qu'utilise GDAL avec --multidirectional.

    Moteur Numba (1 passe, 4 azimuts dÃ©roulÃ©s) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    if z_factor != 1.0:
        dem_f = dem_f * np.float32(z_factor)

    zenith_rad = math.radians(90.0 - altitude_deg)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, multi_kernel, _ = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return multi_kernel(dem_f, float(dx), float(dy),
                            zenith_rad, nd_val, nodata is not None)

    # â”€â”€ Fallback numpy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    slope, aspect = _calc_slope_aspect(dem_f, dx, dy)
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
    if nodata is not None:
        hs_u8[dem_f == nodata] = 0
    return hs_u8


def _slope_numpy(dem, z_factor=1.0, dx=0.5, dy=0.5, scale=1.0, nodata=None):
    """Slope en degrÃ©s â€” formule GDAL standard.

    Renvoie un array uint8 oÃ¹ chaque pixel est l'angle de pente en degrÃ©s
    (0-90), clampÃ© Ã  90.

    Moteur Numba (1 passe, uint8 direct) si dispo, sinon fallback numpy.
    """
    import numpy as np

    dem_f = dem.astype(np.float32, copy=False)
    if z_factor != 1.0:
        dem_f = dem_f * np.float32(z_factor)

    kernels = _get_numba_horn_kernels()
    if kernels is not None:
        _, _, slope_kernel = kernels
        nd_val = float(nodata) if nodata is not None else 0.0
        return slope_kernel(dem_f, float(dx), float(dy),
                            nd_val, nodata is not None)

    # â”€â”€ Fallback numpy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    slope, _ = _calc_slope_aspect(dem_f, dx, dy)
    slope_deg = np.degrees(slope)
    slope_u8 = np.clip(slope_deg, 0.0, 90.0).astype(np.uint8)
    if nodata is not None:
        slope_u8[dem_f == nodata] = 0
    return slope_u8


def _build_vrt_xml(cogs, vrt_path, target_res):
    """
    Construit un VRT GDAL (XML) rÃ©fÃ©renÃ§ant N dalles GeoTIFF, sans matÃ©rialiser
    de mosaÃ¯que physique. Le fichier produit est de l'ordre de quelques 100 Ko
    (â‰ˆ 200 octets/dalle) et la construction prend < 1 s mÃªme pour 10 000 dalles.

    Rasterio lit le VRT transparemment : pour chaque fenÃªtre demandÃ©e, libgdal
    dispatche les reads aux dalles concernÃ©es. Les calculs chunked en aval
    (_hillshade_chunked, _svf_chunked) fonctionnent Ã  l'identique.

    HypothÃ¨ses : toutes les dalles partagent le mÃªme CRS, dtype, nodata, et
    sont alignÃ©es sur une grille (cas standard des dalles IGN LiDAR HD).
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
    Local Relief Model calculÃ© par blocs avec overlap pour Ã©viter les artefacts
    de bord gaussien et borner la RAM indÃ©pendamment de la taille du raster.

    StratÃ©gie :
      - Taille de chunk : 2048 Ã— 2048 px
      - Overlap (marge) : 4 Ã— sigma_px (â‰ˆ 4Ïƒ garantit que l'erreur de bord < 0.1 %)
      - Chaque bloc est lu depuis le disque, filtrÃ©, puis la zone centrale
        (sans la marge) est Ã©crite dans le TIF de sortie.
      - La normalisation percentile est calculÃ©e en deux passes :
          passe 1 (Ã©chantillon)  â†’ p5 / p95 globaux sur ~5 % des pixels
          passe 2 (traitement)   â†’ applique la normalisation bloc par bloc

    Retourne True si succÃ¨s, False si fallback requis (ex: rasterio absent).
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  LRM chunked : import manquant ({_ie}) â€” repli pleine mÃ©moire", flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)   # au moins 64 px pour les petits sigma

    with _rio.open(str(src_path)) as src:
        H, W   = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    # â”€â”€ Passe 1 : estimation percentiles p5/p95 sur Ã©chantillon (~1 chunk) â”€â”€
    sample_rows = min(CHUNK, H)
    sample_cols = min(CHUNK, W)
    with _rio.open(str(src_path)) as src:
        sample = src.read(1, window=Window(0, 0, sample_cols, sample_rows)).astype(np.float32)

    _nd_mask = (sample < -9000) | (sample > 9000)
    if nodata is not None:
        _nd_mask |= (sample == nodata)
    sample_fill = np.where(_nd_mask, float(np.nanmean(sample[~_nd_mask])) if _nd_mask.any() else 0.0, sample)
    smooth_s    = _gf(sample_fill, sigma=sigma_px)
    lrm_s       = sample - smooth_s
    lrm_s[_nd_mask] = np.nan
    valid_s = lrm_s[np.isfinite(lrm_s)]
    if len(valid_s) < 100:
        return False  # raster trop petit / vide
    p1_g  = float(np.percentile(valid_s,  5))
    p99_g = float(np.percentile(valid_s, 95))
    if p99_g <= p1_g:
        p1_g, p99_g = float(np.nanmin(lrm_s)), float(np.nanmax(lrm_s))
    del sample, sample_fill, smooth_s, lrm_s, valid_s

    # â”€â”€ Profil de sortie â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Passe 2 : traitement bloc par bloc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    total_chunks = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n_done = 0
    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:

        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                # FenÃªtre centrale (sortie)
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                # FenÃªtre Ã©tendue avec marge (lecture)
                r0 = max(0, row_off - MARGIN)
                c0 = max(0, col_off - MARGIN)
                r1 = min(H, row_end + MARGIN)
                c1 = min(W, col_end + MARGIN)

                win_read  = Window(c0, r0, c1 - c0, r1 - r0)
                block     = src.read(1, window=win_read).astype(np.float32)

                nd_mask = (block < -9000) | (block > 9000)
                if nodata is not None:
                    nd_mask |= (block == nodata)
                mean_val  = float(np.nanmean(block[~nd_mask])) if nd_mask.any() else 0.0
                block_fill = np.where(nd_mask, mean_val, block)

                smooth    = _gf(block_fill, sigma=sigma_px)
                lrm_block = block - smooth
                lrm_block[nd_mask] = np.nan

                # Normalisation avec les percentiles globaux
                arr_f = np.clip((lrm_block - p1_g) / (p99_g - p1_g), 0.0, 1.0) * 255.0
                arr_u8 = arr_f.astype(np.uint8)
                arr_u8[nd_mask] = 128   # valeur neutre pour les nodata

                # DÃ©coupe de la marge (on ne garde que la zone centrale)
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

    print(f"\r  LRM chunked : terminÃ© ({total_chunks} blocs, Ïƒ={sigma_px} px)          ")
    return True


def _hillshade_chunked(src_path, dst_path, mode, params, dx=0.5, dy=0.5):
    """
    Hillshade / hillshade-multi / slope par fenÃªtres avec halo = 1 px (Horn 3x3).

    mode   : "hillshade" | "hillshade_multi" | "slope"
    params : dict â€” clÃ©s selon le mode
        hillshade        : {"azimuth_deg": float, "altitude_deg": float}
        hillshade_multi  : {"altitude_deg": float}
        slope            : {} (vide)

    Borne la RAM indÃ©pendamment de la taille du raster (chunks 2048Ã—2048 px).
    Retourne True si succÃ¨s, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  Hillshade chunked : import manquant ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = 1

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    out_profile = profile.copy()
    # Purger les clÃ©s hÃ©ritÃ©es qui pourraient interfÃ©rer :
    #  - driver : la source peut Ãªtre un VRT, on veut Ã©crire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse diffÃ©rente, GDAL choisirait au hasard
    #  - NODATA/nodata : on dÃ©sactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    total = ((H + CHUNK - 1) // CHUNK) * ((W + CHUNK - 1) // CHUNK)
    n = 0

    with _rio.open(str(src_path)) as src, \
         _rio.open(str(dst_path), "w", **out_profile) as dst:
        for row_off in range(0, H, CHUNK):
            for col_off in range(0, W, CHUNK):
                if _stop_event.is_set():
                    raise KeyboardInterrupt(f"{mode} chunked interrompu")
                row_end = min(row_off + CHUNK, H)
                col_end = min(col_off + CHUNK, W)

                r0 = max(0, row_off - HALO)
                c0 = max(0, col_off - HALO)
                r1 = min(H, row_end + HALO)
                c1 = min(W, col_end + HALO)

                win_read = Window(c0, r0, c1 - c0, r1 - r0)
                block = src.read(1, window=win_read).astype(np.float32)

                if mode == "hillshade":
                    out = _hillshade_numpy(
                        block, params["azimuth_deg"], params["altitude_deg"],
                        z_factor=1.0, dx=dx, dy=dy, nodata=nodata)
                elif mode == "hillshade_multi":
                    out = _hillshade_multi_numpy(
                        block, altitude_deg=params["altitude_deg"],
                        z_factor=1.0, dx=dx, dy=dy, nodata=nodata)
                elif mode == "slope":
                    out = _slope_numpy(
                        block, z_factor=1.0, dx=dx, dy=dy, nodata=nodata)
                else:
                    raise ValueError(f"Mode hillshade inconnu : {mode}")

                dr0 = row_off - r0
                dc0 = col_off - c0
                dr1 = dr0 + (row_end - row_off)
                dc1 = dc0 + (col_end - col_off)
                centre = out[dr0:dr1, dc0:dc1]

                win_write = Window(col_off, row_off, col_end - col_off, row_end - row_off)
                dst.write(centre[np.newaxis, :, :], window=win_write)

                n += 1
                pct = n * 100 // total
                print(f"\r  {mode} chunked : {pct:3d} % ({n}/{total} blocs)   ",
                      end="", flush=True)
    print(f"\r  {mode} chunked : terminÃ© ({total} blocs)                     ")
    return True


def _svf_chunked(src_path, dst_path, max_dist_px, n_directions=16,
                 resolution=0.5, gamma=2.0, use_sweep=False):
    """
    Sky-View Factor par fenÃªtres avec halo = max_dist_px (rayons SVF).

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~2-3Ã— plus
    rapide, lÃ©ger aliasing aux faibles gradients).

    StratÃ©gie 2 passes :
      1. Ã‰chantillon central â†’ percentiles p2/p98 globaux
      2. Traitement bloc par bloc â†’ stretch + gamma + uint8

    Borne la RAM Ã  ~(2048+2*max_dist_px)Â² Ã— 4 octets â‰ˆ 25 MB pour SVF100.
    Retourne True si succÃ¨s, False si import manquant.
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
    except ImportError as _ie:
        print(f"  SVF chunked : import manquant ({_ie})", flush=True)
        return False

    CHUNK = 2048
    HALO  = max_dist_px

    # Kernel SVF mutualisÃ© entre _svf_numpy et _svf_chunked (factory + cache).
    # Ã‰vite la double compilation Numba (~20 s Ã— 2 au premier appel).
    # Si use_sweep : variante nearest-neighbor sans bilinÃ©aire (~Ã—2-3 plus rapide).
    _kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _kernel is None:
        print("  numba absent â€” SVF chunked indisponible", flush=True)
        return False
    if use_sweep:
        print("  SVF chunked : kernel sweep-horizon (deque/upper-hull)", flush=True)

    def _svf_block(block):
        nd_mask = (block < -9000) | (block > 9000)
        block_f = block.astype(np.float32, copy=True)
        if nd_mask.any():
            mean_val = float(np.nanmean(block_f[~nd_mask])) if (~nd_mask).any() else 0.0
            block_f[nd_mask] = mean_val
        svf = _kernel(block_f, n_directions, max_dist_px, resolution)
        svf[nd_mask] = 0.0
        return svf

    with _rio.open(str(src_path)) as src:
        H, W    = src.height, src.width
        profile = src.profile.copy()

    # â”€â”€ Passe 1 : compilation Numba + percentiles globaux sur Ã©chantillon â”€â”€
    # Sample rÃ©duit Ã  256Ã—256 (+ halo) : suffit largement pour estimer p2/p98
    # de maniÃ¨re stable (~65k pixels valides au centre). Avant on calculait un
    # bloc complet (CHUNKÂ²) qui coÃ»tait ~7% du temps total â€” pure perte puisque
    # le rÃ©sultat ne sert qu'aux deux percentiles.
    print("  SVF chunked â€” compilation Numba + percentiles (sample)...", flush=True)
    SAMPLE = 256
    cy = H // 2
    cx = W // 2
    s_half = SAMPLE // 2
    s_r0 = max(0, cy - s_half - HALO)
    s_c0 = max(0, cx - s_half - HALO)
    s_r1 = min(H, cy + s_half + HALO)
    s_c1 = min(W, cx + s_half + HALO)
    with _rio.open(str(src_path)) as src:
        sample = src.read(1, window=Window(s_c0, s_r0, s_c1 - s_c0, s_r1 - s_r0)).astype(np.float32)
    svf_sample = _svf_block(sample)
    valid = svf_sample[svf_sample >= 0]
    if len(valid) < 100:
        return False
    p2_g  = float(np.percentile(valid,  2))
    p98_g = float(np.percentile(valid, 98))
    if p98_g <= p2_g:
        p2_g, p98_g = 0.0, 1.0
    del sample, svf_sample, valid
    print(f"  SVF chunked â€” p2={p2_g:.3f}  p98={p98_g:.3f}", flush=True)

    out_profile = profile.copy()
    # Purger les clÃ©s hÃ©ritÃ©es qui pourraient interfÃ©rer :
    #  - driver : la source peut Ãªtre un VRT, on veut Ã©crire un GeoTIFF
    #  - BIGTIFF/bigtiff doublons : casse diffÃ©rente, GDAL choisirait au hasard
    #  - NODATA/nodata : on dÃ©sactive nodata sur la sortie uint8
    for _k in ("driver", "BIGTIFF", "bigtiff", "NODATA", "nodata"):
        out_profile.pop(_k, None)
    out_profile.update(
        driver="GTiff",
        dtype="uint8", count=1, compress="deflate", predictor=2,
        tiled=True, blockxsize=512, blockysize=512,
        bigtiff="YES", nodata=None)

    # â”€â”€ Passe 2 : traitement bloc par bloc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
    print(f"\r  SVF chunked : terminÃ© ({total} blocs, halo={HALO} px)        ")
    return True


def _svf_numpy(dem, max_dist_px, n_directions=16, resolution=0.5, use_sweep=False):
    """
    Sky-View Factor â€” pixel-level ray casting.

    SVF(p) = (1/N) Ã— Î£_k  1 / (1 + max(tan_horizon_k, 0)Â²)

    Moteurs disponibles par ordre de prÃ©fÃ©rence :
      1. Numba njit + prange  â†’ Ã—15-50 vs numpy pur, compilation ~20s au 1er appel
      2. numpy vectorisÃ©      â†’ fallback si numba absent

    use_sweep=True : utilise le kernel sweep (nearest-neighbor, ~Ã—2-3 plus rapide,
    lÃ©ger aliasing aux faibles gradients).

    SVF faible (sombre) = creux (fossÃ©, fond de vallÃ©e)
    SVF Ã©levÃ© (clair)   = ouvert (sommet, plateau)
    """
    import numpy as np

    h, w = dem.shape
    nodata_mask = (dem < -9000) | (dem > 9000)
    dem_f = dem.astype(np.float32)
    if nodata_mask.any():
        mean_val = float(np.nanmean(dem_f[~nodata_mask]))
        dem_f[nodata_mask] = mean_val

    # â”€â”€ Tentative Numba â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Kernel mutualisÃ© via _get_numba_svf_kernel() â€” partagÃ© avec _svf_chunked
    # pour Ã©viter la double compilation (~20 s Ã— 2 au premier appel).
    _numba_ok = False
    _svf_kernel = _get_numba_svf_sweep_kernel() if use_sweep else _get_numba_svf_kernel()
    if _svf_kernel is not None:
        try:
            print("  SVF Numba JIT â€” compilation au 1er appel (~20s)...", flush=True)
            svf = _svf_kernel(dem_f, n_directions, max_dist_px, resolution)
            _numba_ok = True
            print(f"\r  SVF Numba JIT â€” terminÃ©{' ' * 30}")
        except Exception as e_nb:
            print(f"  numba erreur ({e_nb}) â€” fallback numpy", flush=True)
    else:
        print("  numba absent â€” fallback numpy vectorisÃ©", flush=True)

    # â”€â”€ Fallback numpy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if not _numba_ok:
        try:
            from scipy.ndimage import shift as _shift
            _use_scipy = True
        except ImportError:
            _use_scipy = False

        # Check prÃ©coce : si l'utilisateur a dÃ©jÃ  fait Ctrl+C avant qu'on arrive
        # ici (ex. pendant l'init Numba), on n'enchaÃ®ne pas le fallback.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu avant traitement")

        def _process_direction(k):
            angle   = k * 2.0 * np.pi / n_directions
            dx      =  np.sin(angle)
            dy      = -np.cos(angle)
            max_tan = np.full((h, w), -np.inf, dtype=np.float32)

            for r in range(1, max_dist_px + 1):
                # Check au sein du rayon : sur dept-scale, max_dist_px peut
                # atteindre 200+ et chaque shift scipy prend 1-3s â†’ permet
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
                    tan_angle = np.full((h, w), -np.inf, dtype=np.float32)
                    tan_angle[r_d0:r_d1, c_d0:c_d1] = (
                        dem_f[r_s0:r_s1, c_s0:c_s1] -
                        dem_f[r_d0:r_d1, c_d0:c_d1]
                    ) / dist_m
                np.maximum(max_tan, tan_angle, out=max_tan)

            mt = np.maximum(max_tan, 0.0)
            return (1.0 / (1.0 + mt * mt)).astype(np.float32)

        n_workers = min(n_directions, max(1, os.cpu_count() or 4))
        svf_sum   = np.zeros((h, w), dtype=np.float32)
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_process_direction, k): k
                       for k in range(n_directions)}
            done = 0
            try:
                for fut in as_completed(futures):
                    if _stop_event.is_set():
                        # Annuler les futures non encore dÃ©marrÃ©es (les autres
                        # finiront leur direction courante mais retourneront None).
                        for f in futures:
                            f.cancel()
                        # On ne raise pas tout de suite â€” on laisse les workers
                        # actifs se terminer avant de quitter le with-block,
                        # sinon ThreadPoolExecutor.__exit__ va attendre quand mÃªme.
                        break
                    res = fut.result()
                    if res is None:
                        # Worker a vu _stop_event en interne et a retournÃ© None
                        break
                    svf_sum += res
                    done += 1
                    pct_svf = done * 100 // max(n_directions, 1)
                    print(f"\r  SVF directions : {pct_svf:3d}%  {done}/{n_directions}",
                          end="", flush=True)
            except KeyboardInterrupt:
                # Signal arrivÃ© pendant l'attente du future â€” annuler ce qu'on peut
                for f in futures:
                    f.cancel()
                raise
        print()
        # Si l'utilisateur a interrompu, propager l'arrÃªt Ã  l'appelant.
        # Le rÃ©sultat partiel n'est pas utilisable (sommation incomplÃ¨te sur
        # n_directions). KeyboardInterrupt = standard Python, ne sera pas
        # capturÃ© par les `except Exception:` en aval.
        if _stop_event.is_set():
            raise KeyboardInterrupt("SVF interrompu en cours de calcul")
        svf = svf_sum / n_directions

    svf[nodata_mask] = 0.0
    return svf


def generer_ombrages(cogs, dossier_ville, choix=None, elevation_soleil=None, nom_zone=None, ecraser_ombrages=False, ecraser_tuiles=False, use_sweep=False):
    """
    GÃ©nÃ¨re les ombrages depuis le VRT/COG source (MNT EPSG:2154).

    Types gdaldem  : 315, 045, 135, 225, multi, slope
    Types numpy/scipy (sans WhiteboxTools) :
        svf    â€” Sky-View Factor 20 m  : fossÃ©s, murs, structures â‰¤ 5 m (16 dir, rayon 20 m)
        svf100 â€” Sky-View Factor 100 m : enceintes, voiries, grandes anomalies (16 dir, rayon 100 m)
        rrim   â€” Red Relief Image Map  : composite RGB couleur (R=pente, G=B=SVF)
        lrm    â€” Local Relief Model    : LRM = DEM âˆ’ gaussienne(Ïƒ 7.5 m) â€” scipy requis

    elevation_soleil : angle solaire en degrÃ©s (dÃ©faut: 25Â° archÃ©o, vs 45Â° usage gÃ©nÃ©ral).
    SVF/SVF100/LRM/RRIM : implÃ©mentÃ©s en numpy/scipy â€” aucun outil externe requis.
    """

    if elevation_soleil is None:
        elevation_soleil = ELEVATION_SOLEIL

    if choix is None:
        choix = ["315", "045", "135", "225", "multi", "slope"]

    if isinstance(cogs, Path):
        cogs = [cogs]

    # Aucune dalle valide pour ce chunk (hors couverture IGN, ou
    # tÃ©lÃ©chargements tous en Ã©chec). On retourne proprement plutÃ´t que
    # de planter sur `sources[0]` plus bas â€” la boucle des chunks
    # poursuit avec les morceaux suivants. Le chunk ne produira pas
    # de .tif d'ombrage donc pas de mbtiles non plus.
    if not cogs:
        print(f"  âš  Aucune dalle disponible dans ce chunk "
              f"(hors couverture IGN LiDAR ou tÃ©lÃ©chargement Ã©chouÃ©) â€” "
              f"ombrages skipÃ©s.", flush=True)
        return

    # Variables conservÃ©es pour compatibilitÃ© du code existant : aprÃ¨s le
    # refactor rasterio (Ã©tapes 1-7), aucun de ces exes n'est plus appelÃ©.
    # _trouver_outil_gdal renvoie toujours None (no-op), donc ces variables
    # sont toujours None â€” c'est OK puisqu'elles ne sont plus testÃ©es.
    gdaldem        = None
    gdalbuildvrt   = None
    gdal_translate = None
    env_dem        = None

    CATALOGUE_GDAL = {
        "315":   ("315_ombrage",   ["hillshade", "-b","1","-z","1.0","-s","1.0","-az","315","-alt",str(elevation_soleil)]),
        "045":   ("045_ombrage",   ["hillshade", "-b","1","-z","1.0","-s","1.0","-az", "45","-alt",str(elevation_soleil)]),
        "135":   ("135_ombrage",   ["hillshade", "-b","1","-z","1.0","-s","1.0","-az","135","-alt",str(elevation_soleil)]),
        "225":   ("225_ombrage",   ["hillshade", "-b","1","-z","1.0","-s","1.0","-az","225","-alt",str(elevation_soleil)]),
        "multi": ("multi_ombrage", ["hillshade", "-b","1","-z","1.0","-s","1.0","-multidirectional"]),
        "slope": ("slope_ombrage",           ["slope",     "-b","1","-s","1.0"]),
    }
    CATALOGUE_NUMPY = {
        # (suffix_fichier, moteur, params)
        # moteur=None â†’ traitement numpy interne (pas de WBT)
        "svf":    ("svf_ombrage",      None,
                   {"max_dist_px": 40,  "n_directions": 16}),   # 40 px = 20 m Ã  0.5 m/px
        "svf100": ("svf_100m_ombrage", None,
                   {"max_dist_px": 200, "n_directions": 16}),   # 200 px = 100 m
        "lrm":    ("lrm_ombrage",      None,
                   {"sigma_px": 15}),                            # Ïƒ=15 px = 7.5 m â€” compromise structures 4-15 m
        "rrim":   ("rrim_ombrage",     None,
                   {"max_dist_px": 40,  "n_directions": 16}),   # SVF 20m + slope
    }
    co = ["-of", "GTiff",
          "-co", "BIGTIFF=YES",
          "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
          "-co", "TILED=YES", "-co", "BLOCKXSIZE=512", "-co", "BLOCKYSIZE=512",
          "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
          "--config", "GDAL_CACHEMAX", "2048"]

    choix_gdal = [c for c in choix if c in CATALOGUE_GDAL]
    choix_numpy  = [c for c in choix if c in CATALOGUE_NUMPY]

    # NB : les "hillshades GDAL" ne sont plus calculÃ©s via gdaldem CLI depuis
    # le refactor Ã©tape 4. Ils utilisent maintenant _hillshade_numpy /
    # _hillshade_multi_numpy / _slope_numpy (numpy direct, formule Horn 1981).
    # Le nom CATALOGUE_GDAL est conservÃ© pour minimiser le diff.

    # â”€â”€ Construction VRT global (seamless, Ã©vite jointures gdaldem) â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # VRT dans _tmp/ sous dossier_ville : tous les fichiers restent dans le projet.
    import shutil as _shutil_vrt
    _vrt_tmpdir = None
    # â”€â”€ Merge des dalles via rasterio (remplace gdalbuildvrt + gdal_translate) â”€â”€
    # Au lieu de produire un VRT puis de le convertir en GeoTIFF avec
    # gdal_translate, on fait un merge direct rasterio en GeoTIFF compressÃ©.
    # Avantages : un seul passage, plus de dÃ©pendance Ã  GDAL CLI, sortie
    # immÃ©diatement utilisable par numpy (gdaldem reste pour les hillshades â€”
    # voir Ã©tape 4 du refactor).
    if len(cogs) > 1:
        _vrt_tmpdir = dossier_ville / "_tmp"
        _vrt_tmpdir.mkdir(parents=True, exist_ok=True)
        # VRT XML : vue logique sur les dalles, ~200 o/dalle, construction <1 s.
        # Ã‰vite la matÃ©rialisation d'une mosaÃ¯que physique multi-Go (le merge
        # rasterio sur 2000+ dalles avec compression deflate est pathologique).
        # rasterio lit le VRT transparemment via libgdal â€” les calculs chunked
        # en aval reÃ§oivent leurs fenÃªtres comme depuis un raster ordinaire.
        vrt_path      = _vrt_tmpdir / "_mnt_complet.vrt"
        filelist_path = _vrt_tmpdir / "_dalles.txt"
        filelist_path.write_text(
            "\n".join(str(c) for c in cogs), encoding="utf-8")
        _creer_fichier(filelist_path)
        print(f"  Construction VRT ({len(cogs)} dalles)...", flush=True)
        _t0_vrt = time.time()
        try:
            _build_vrt_xml(cogs, vrt_path, RESOLUTION_M)
            _creer_fichier(vrt_path)
            print(f"  VRT OK  ({_hms(time.time()-_t0_vrt)}, "
                  f"{vrt_path.stat().st_size // 1024} Ko)", flush=True)
            sources = [vrt_path]
        except Exception as e:
            # Hard-fail au lieu du fallback `sources = cogs` : sources[0] ne
            # garderait que la 1Ã¨re dalle, produisant un MBTiles vide.
            raise RuntimeError(
                f"Construction VRT Ã©chouÃ©e : {e}\n"
                f"  â†’ vÃ©rifier l'accÃ¨s disque sur {_vrt_tmpdir}"
            ) from e
    else:
        sources = cogs

    source   = sources[0]
    nom_base = normaliser_nom(nom_zone) if nom_zone else normaliser_nom(dossier_ville.name)

    try:
        # â”€â”€ Hillshades numpy chunked (RAM bornÃ©e â€” voir _hillshade_chunked) â”€
        # Traitement par fenÃªtres 2048Ã—2048 px avec halo 1 px (Horn 3x3).
        # Le DEM source n'est plus chargÃ© en entier en RAM : permet le
        # traitement de zones LiDAR de taille arbitraire (dÃ©partement entier).

        def _generer_un_hillshade(cle):
            suffix, args_dem = CATALOGUE_GDAL[cle]
            nom_fichier = nom_base + "_" + suffix + ".tif"
            chemin_out  = dossier_ville / nom_fichier

            if chemin_out.exists() and not ecraser_ombrages:
                return cle, nom_fichier, "skip", 0, []
            if chemin_out.exists() and ecraser_ombrages:
                chemin_out.unlink()

            try:
                mode = args_dem[0]
                if mode == "hillshade":
                    if "-multidirectional" in args_dem:
                        params = {"altitude_deg": float(elevation_soleil)}
                        ok = _hillshade_chunked(
                            Path(str(source)), chemin_out, "hillshade_multi",
                            params, dx=RESOLUTION_M, dy=RESOLUTION_M)
                    else:
                        i_az  = args_dem.index("-az")
                        i_alt = args_dem.index("-alt")
                        params = {"azimuth_deg":  float(args_dem[i_az + 1]),
                                  "altitude_deg": float(args_dem[i_alt + 1])}
                        ok = _hillshade_chunked(
                            Path(str(source)), chemin_out, "hillshade",
                            params, dx=RESOLUTION_M, dy=RESOLUTION_M)
                elif mode == "slope":
                    ok = _hillshade_chunked(
                        Path(str(source)), chemin_out, "slope", {},
                        dx=RESOLUTION_M, dy=RESOLUTION_M)
                else:
                    return cle, nom_fichier, "erreur", 0, [f"mode inconnu : {mode}"]

                if not ok:
                    return cle, nom_fichier, "erreur", 0, ["chunked failed (rasterio absent ?)"]

                _creer_fichier(chemin_out)
                return cle, nom_fichier, "ok", chemin_out.stat().st_size / 1e6, []
            except Exception as e:
                return cle, nom_fichier, "erreur", 0, [str(e)]

        if choix_gdal:
            if len(choix_gdal) == 1:
                cle, nom_fichier, statut, taille, errs = \
                    _generer_un_hillshade(choix_gdal[0])
                if statut == "skip":
                    print("  " + nom_fichier.ljust(56) + " -> dÃ©jÃ  prÃ©sent")
                elif statut == "erreur":
                    print(f"\n  ERREUR hillshade {nom_fichier}")
                    for e in errs[:10]:
                        print(f"    {e}")
            else:
                # Plusieurs types : sÃ©quentiel (chaque chunked itÃ¨re ses
                # propres windows ; parallÃ©liser ici multiplierait la pression
                # I/O sur le DEM source sans bÃ©nÃ©fice â€” le bottleneck devient
                # le disque, pas le CPU).
                print(f"  Hillshades chunked ({len(choix_gdal)} types)...",
                      flush=True)
                for cle_h in choix_gdal:
                    cle, nom_fichier, statut, taille, errs = \
                        _generer_un_hillshade(cle_h)
                    if statut == "skip":
                        print("  " + nom_fichier.ljust(56) + " -> dÃ©jÃ  prÃ©sent")
                    elif statut == "erreur":
                        print(f"\n  ERREUR hillshade {nom_fichier}")
                        for e in errs[:10]:
                            print(f"    {e}")

        # â”€â”€ SVF, LRM, RRIM â€” numpy/scipy (pas de WBT pour SVF) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if not choix_numpy:
            pass  # pas de traitement demandÃ©

        # NB : rasterio.merge (Ã©tape 2 du refactor) produit dÃ©jÃ  un GeoTIFF
        # directement utilisable par numpy/PIL/rasterio en aval. Plus aucune
        # conversion intermÃ©diaire VRTâ†’GTiff nÃ©cessaire.
        src_str = str(source)
        tmp_gtiff = None

        for cle in choix_numpy:
            # Cancellation propre entre 2 ombrages : si l'utilisateur a fait
            # Ctrl+C pendant le prÃ©cÃ©dent (kernel Numba intuable), l'ombrage
            # courant a Ã©tÃ© sauvegardÃ© mais on n'enchaÃ®ne pas le suivant.
            if _stop_event.is_set():
                print("  Interruption â€” ombrages restants ignorÃ©s.")
                break
            sous_dossier_name, outil_numpy, params_numpy = CATALOGUE_NUMPY[cle]
            nom_fichier  = nom_base + "_" + sous_dossier_name + ".tif"
            chemin_out   = dossier_ville / nom_fichier

            if chemin_out.exists() and not ecraser_ombrages:
                print("  " + nom_fichier.ljust(56) + " -> dÃ©jÃ  prÃ©sent")
                continue
            # Si on Ã©crase, supprimer l'ancien : Ã©vite que rasterio_write
            # tombe sur un fichier figÃ© (Windows file locking) ou demi-Ã©crit.
            if chemin_out.exists() and ecraser_ombrages:
                chemin_out.unlink()

            t0_numpy = time.time()

            if cle in ("svf", "svf100"):
                # â”€â”€ Sky-View Factor chunked (RAM bornÃ©e) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                # Traitement par fenÃªtres 2048Ã—2048 avec halo = max_dist_px.
                # Permet de traiter des zones de dÃ©partement entier sans OOM.
                max_dist_px  = params_numpy["max_dist_px"]
                n_directions = params_numpy["n_directions"]
                dist_m = max_dist_px * RESOLUTION_M
                print(f"  SVF chunked ({n_directions} dir, rayon {dist_m:.0f} m"
                      f" = {max_dist_px} px)...", flush=True)
                try:
                    ok = _svf_chunked(
                        src_path     = Path(src_str),
                        dst_path     = chemin_out,
                        max_dist_px  = max_dist_px,
                        n_directions = n_directions,
                        resolution   = RESOLUTION_M,
                        gamma        = 2.0,
                        use_sweep    = use_sweep,
                    )
                    if not ok:
                        # Repli pleine mÃ©moire (numba absent ou Ã©chantillon
                        # trop petit) â€” limitÃ© aux zones modestes.
                        import numpy as np
                        print("  SVF chunked KO â†’ repli pleine mÃ©moire", flush=True)
                        dem_arr, _nd = _lire_dem_rasterio(src_str)
                        arr_svf = _svf_numpy(dem_arr, max_dist_px, n_directions,
                                             RESOLUTION_M, use_sweep=use_sweep)
                        svf_valid = arr_svf[arr_svf >= 0]
                        p2  = float(np.percentile(svf_valid, 2))
                        p98 = float(np.percentile(svf_valid, 98))
                        if p98 > p2:
                            arr_stretched = np.clip((arr_svf - p2) / (p98 - p2), 0, 1)
                        else:
                            arr_stretched = np.clip(arr_svf, 0, 1)
                        arr_u8 = (arr_stretched ** 2.0 * 255).astype(np.uint8)
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_out)
                except Exception as e_svf:
                    import traceback as _tb
                    print(f"  ERREUR SVF : {e_svf}")
                    print("  --- traceback complÃ¨te ---")
                    _tb.print_exc()
                    print("  ---------------------------")
                    # Supprimer le fichier partiellement Ã©crit : _svf_chunked
                    # Ã©crit chunk par chunk via rasterio. Si une exception
                    # survient au milieu, le TIF rÃ©sultant est incomplet (ex :
                    # 109 Mo au lieu de 300 Mo) mais structurellement valide.
                    # Sans suppression, le tuileur l'accepte et produit 0 tuile
                    # silencieusement. Sur le prochain lancement, le fichier
                    # "dÃ©jÃ  prÃ©sent" est rÃ©utilisÃ© â†’ bug persistant.
                    if chemin_out.exists():
                        chemin_out.unlink()
                        print(f"  Fichier partiel supprimÃ© : {chemin_out.name}")
                    continue

            elif cle == "lrm":
                # â”€â”€ Local Relief Model â€” filtre gaussien â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                # LRM = DEM âˆ’ gaussienne(Ïƒ) â†’ normalisation p5-p95 â†’ uint8 (128=plat)
                # Traitement par blocs avec overlap pour borner la RAM :
                #   chemin 1 : _lrm_chunked() si rasterio + scipy disponibles
                #   chemin 2 : pleine mÃ©moire (fallback)
                sigma_px = params_numpy["sigma_px"]  # 50 px = 25 m Ã  0.5 m/px
                print(f"  LRM gaussien (Ïƒ={sigma_px} px = {sigma_px * RESOLUTION_M:.0f} m)"
                      f" â€” peut prendre 3-7 min...", flush=True)

                # â”€â”€ Chemin 1 : traitement chunkÃ© (RAM bornÃ©e) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                _lrm_ok = _lrm_chunked(
                    src_path         = Path(src_str),
                    dst_path         = chemin_out,
                    sigma_px         = sigma_px,
                    gdal_translate_exe = gdal_translate,
                    env_dem          = env_dem,
                )

                if not _lrm_ok:
                    # â”€â”€ Chemin 2 : fallback pleine mÃ©moire â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    try:
                        import numpy as np
                        from scipy.ndimage import gaussian_filter as _gf
                        dem_arr, _nd_val = _lire_dem_rasterio(src_str)
                        nodata_mask = (dem_arr < -9000) | (dem_arr > 9000)
                        if _nd_val is not None:
                            nodata_mask |= (dem_arr == _nd_val)
                        dem_arr[nodata_mask] = np.nan
                        dem_fill = np.where(nodata_mask, np.nanmean(dem_arr), dem_arr)
                        smooth = _gf(dem_fill, sigma=sigma_px)
                        lrm = dem_arr - smooth
                        lrm[nodata_mask] = np.nan
                        lrm_valid = lrm[np.isfinite(lrm)]
                        p1  = float(np.percentile(lrm_valid,  5))
                        p99 = float(np.percentile(lrm_valid, 95))
                        if p99 > p1:
                            arr_f     = np.clip((lrm - p1) / (p99 - p1), 0, 1) * 255
                            clip_info = f"p5={p1:.2f}m p95={p99:.2f}m"
                        else:
                            clip_val  = max(0.1, 2.0 * float(np.nanstd(lrm)))
                            arr_f     = (np.clip(lrm, -clip_val, clip_val) + clip_val) / (2 * clip_val) * 255
                            clip_info = f"Â±{clip_val:.2f}m (Ïƒ fallback)"
                        arr_u8 = arr_f.astype(np.uint8)
                        arr_u8[nodata_mask] = 128
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_out)
                        _lrm_ok = True
                        print(f"  LRM scipy (pleine mÃ©moire) : Ïƒ={sigma_px} px, {clip_info}")
                    except ImportError:
                        print("  scipy absent â€” LRM ignorÃ© (pip install scipy)", flush=True)
                        continue
                    except Exception as e_scipy:
                        print(f"  ERREUR scipy LRM : {e_scipy}")
                        continue

            elif cle == "rrim":
                # â”€â”€ Red Relief Image Map (RRIM) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                # Composite RGB couleur :
                #   R = pente normalisÃ©e [0Â°..45Â°] â†’ [0..255]  (relief en amplitude)
                #   G = B = SVF normalisÃ© [0..1] â†’ [0..255]    (ouverture / micro-formes)
                # RÃ©vÃ¨le simultanÃ©ment creux ET bosses â€” optimal prospection terrain.
                # Technique : Chiba et al. (2008), standard archÃ©o-LiDAR europÃ©en.
                print("  RRIM â€” Red Relief Image Map (slope Ã— LRM)"
                      " â€” peut prendre 5-10 min...", flush=True)

                # Slope temporaire (rÃ©utilisÃ© si dÃ©jÃ  prÃ©sent)
                slope_rrim_path = dossier_ville / (nom_base + "_slope_ombrage.tif")
                slope_tmp_path  = dossier_ville / (nom_fichier.replace(".tif","_slope_tmp.tif"))
                _slope_src = None
                if slope_rrim_path.exists():
                    _slope_src = slope_rrim_path
                    print("  RRIM : slope existant rÃ©utilisÃ©", flush=True)
                else:
                    # Slope numpy (remplace gdaldem slope CLI)
                    try:
                        import rasterio as _rio_sl
                        with _rio_sl.open(src_str) as _ds_sl:
                            _dem_sl    = _ds_sl.read(1).astype("float32")
                            _nd_sl_in  = _ds_sl.nodata
                            _profile_sl = _ds_sl.profile.copy()
                        _slope_u8 = _slope_numpy(_dem_sl, dx=RESOLUTION_M,
                                                 dy=RESOLUTION_M, nodata=_nd_sl_in)
                        _profile_sl.update({
                            "dtype":      "uint8",
                            "count":      1,
                            "compress":   "deflate",
                            "predictor":  2,
                            "tiled":      True,
                            "blockxsize": 512,
                            "blockysize": 512,
                            "BIGTIFF":    "YES",
                        })
                        for _k in ("nodata",):
                            _profile_sl.pop(_k, None)
                        with _rio_sl.open(str(slope_tmp_path), "w", **_profile_sl) as _dst_sl:
                            _dst_sl.write(_slope_u8, 1)
                        _slope_src = slope_tmp_path
                    except Exception as _e_sl:
                        print(f"  ERREUR slope numpy pour RRIM : {_e_sl}")
                        continue

                # Ã‰tape 3 : composite RGB numpy/PIL
                # RRIM modifiÃ© pour terrain ouvert (Var) :
                #   R = pente gamma 0.7 (relief gÃ©nÃ©ral)
                #   G = B = LRM normalisÃ© (micro-relief local, variance >> SVF)
                # Le LRM a beaucoup plus de variance que SVF sur terrain ouvert
                # oÃ¹ SVF â‰ˆ 0.97 partout â†’ G/B â‰ˆ 255 constant â†’ dominance bleue.
                try:
                    import numpy as np
                    from scipy.ndimage import gaussian_filter as _gf2

                    slope_arr, _nd_sl = _lire_dem_rasterio(str(_slope_src))

                    # Calcul LRM interne pour RRIM (sigma identique au LRM standalone)
                    dem_rrim, _nd_rr  = _lire_dem_rasterio(src_str)
                    nodata_r = (dem_rrim < -9000) | (dem_rrim > 9000)
                    if _nd_rr is not None:
                        nodata_r |= (dem_rrim == _nd_rr)
                    dem_fill_r = np.where(nodata_r, float(np.nanmean(dem_rrim[~nodata_r])), dem_rrim)
                    sigma_rrim = 15  # px = 7.5 m
                    lrm_r = dem_rrim - _gf2(dem_fill_r, sigma=sigma_rrim)
                    lrm_r[nodata_r] = np.nan

                    # Aligner dimensions
                    h = min(slope_arr.shape[0], lrm_r.shape[0])
                    w = min(slope_arr.shape[1], lrm_r.shape[1])
                    slope_arr = slope_arr[:h, :w]
                    lrm_r     = lrm_r[:h, :w]

                    def _norm_pct(arr, p_lo=5, p_hi=95):
                        valid = arr[np.isfinite(arr)]
                        if len(valid) == 0:
                            return np.zeros_like(arr)
                        lo = float(np.percentile(valid, p_lo))
                        hi = float(np.percentile(valid, p_hi))
                        if hi > lo:
                            return np.clip((arr - lo) / (hi - lo), 0, 1)
                        return np.zeros_like(arr)

                    # R = pente gamma 0.7
                    slope_n = np.clip(slope_arr / 45.0, 0, 1)
                    r_chan  = (_norm_pct(slope_n) ** 0.7 * 255).astype(np.uint8)

                    # G = B = LRM normalisÃ© p5-p95, gamma 0.8
                    # LRM > 0 = Ã©lÃ©vation â†’ clair ; LRM < 0 = creux â†’ foncÃ©
                    lrm_n  = _norm_pct(lrm_r)
                    gb_chan = (lrm_n ** 0.8 * 255).astype(np.uint8)

                    rgb = np.stack([r_chan, gb_chan, gb_chan], axis=2)
                    _sauver_array_georef(rgb, Path(src_str), chemin_out)
                    print(f"  RRIM : {chemin_out.name} â€” RGB 3 canaux")
                except Exception as e_rrim:
                    print(f"  ERREUR composite RRIM : {e_rrim}")
                    continue
                finally:
                    if slope_tmp_path.exists():
                        slope_tmp_path.unlink(missing_ok=True)

            if chemin_out.exists():
                _creer_fichier(chemin_out)
                taille = chemin_out.stat().st_size / 1e6
                elap_numpy = int(time.time() - t0_numpy)
                print(f"  {nom_fichier.ljust(56)}  {_hms(elap_numpy)}  {taille:.0f} Mo")

        # Nettoyage du GeoTIFF temporaire crÃ©Ã© pour WhiteboxTools
        if tmp_gtiff and tmp_gtiff.exists():
            tmp_gtiff.unlink(missing_ok=True)

    finally:
        # Suppression du dossier _tmp/ projet (VRT, dalles.txt, numpy_source_tmp)
        if _vrt_tmpdir and _vrt_tmpdir.exists():
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)

    print("\n  Ombrages dans : " + str(dossier_ville))


def _bbox_depuis_gdalinfo(chemin, env=None):
    """Retourne (xmin, ymin, xmax, ymax) en unitÃ©s natives du fichier via rasterio.

    Le paramÃ¨tre `env` est conservÃ© pour compatibilitÃ© mais n'est plus utilisÃ©
    (rasterio embarque sa propre libgdal â€” pas besoin de PROJ_LIB).
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
    Pipeline MBTiles â€” source unique, pyramide GDAL, tuilage par bandes.

    1. gdalwarp  : tif_source (EPSG:2154) â†’ warped_3857.tif (EPSG:3857)
                   Ã  la rÃ©solution native de zoom_max, DEFLATE+TILED.
    2. gdaladdo  : overviews gauss pour zoom_min..zoom_max-1.
    3. Tiling    : rangÃ©es de tuiles via gdal_translate + Pillow
                   â†’ INSERT OR REPLACE SQLite.

    format_tuiles : 'auto' (JPEG pour hillshades, PNG pour SVF/LRM/RRIM),
                    'jpeg' ou 'png'.
    JPEG Ã  Q=85 divise la taille par 5-8 sur les hillshades sans perte visible.
    PNG conservÃ© pour les analyses Ã  gradient fin (SVF, LRM) et RRIM couleur.
    """
    import sqlite3, shutil
    from PIL import Image

    # VÃ©rification anticipÃ©e de rasterio â€” Ã©vite d'attendre la fin du gdalwarp
    try:
        import rasterio as _rio_check  # noqa
    except ImportError:
        print("  ERREUR : rasterio absent â€” requis pour le tuilage MBTiles.")
        print("  Installez-le : pip install rasterio")
        return None

    Image.MAX_IMAGE_PIXELS = None

    # DÃ©terminer le format de tuile effectif
    _nom_lower = tif_source.stem.lower()
    _types_png = ("svf", "lrm", "rrim")   # gradients fins â†’ PNG sans perte
    if format_tuiles == "auto":
        _use_jpeg = not any(t in _nom_lower for t in _types_png)
    elif format_tuiles == "jpeg":
        _use_jpeg = True
    else:
        _use_jpeg = False
    _tile_fmt  = "JPEG" if _use_jpeg else "PNG"
    _tile_ext  = "jpg"  if _use_jpeg else "png"
    print(f"  Format tuiles : {_tile_fmt}"
          f"{'  Q=' + str(jpeg_quality) if _use_jpeg else '  lossless'}", flush=True)

    EARTH_CIRC = 20037508.3427892
    TILE_SIZE  = 256

    # Nom de base : utiliser nom_ville si fourni (ex: "aa_hillshade_multi"),
    # sinon stem du TIF source
    nom_base = nom_ville if nom_ville else tif_source.stem
    mbtiles  = dossier_ville / (nom_base + f"_z{zoom_min}-{zoom_max}.mbtiles")

    if mbtiles.exists() and not ecraser_tuiles:
        print(f"  {mbtiles.name} â†’ dÃ©jÃ  prÃ©sent")
        return mbtiles
    if mbtiles.exists() and ecraser_tuiles:
        mbtiles.unlink()
        print(f"  {mbtiles.name} â†’ Ã©crasement")

    # Variables conservÃ©es pour compatibilitÃ© â€” aprÃ¨s refactor rasterio
    # (Ã©tapes 1-7), gdalwarp/gdal_translate/gdal_addo ne sont plus appelÃ©s
    # comme CLI. Le warp est fait par rasterio.warp plus bas.
    env       = None
    gdalwarp  = None
    gdal_tr   = None
    gdal_addo = None

    # NB : avec rasterio, la base proj.db est gÃ©rÃ©e en interne par le wheel
    # rasterio (livrÃ©e dans rasterio/proj_data/). Plus besoin de configurer
    # PROJ_LIB ou GDAL_DATA externes â€” c'Ã©tait nÃ©cessaire avec GDAL CLI mais
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

    # â”€â”€ Seuil de dÃ©coupage automatique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Si la zone est grande, warp par bandes horizontales pour Ã©viter un
    # fichier intermÃ©diaire > SEUIL_WARP_GO en temp.
    # Overlap d'une tuile (res_max Ã— 256) entre bandes â†’ pas de jointure visible.
    # Ã€ 20Ã—20 km / z18 : ~160 Mo warpÃ© â†’ seuil jamais atteint.
    # Protection transparente pour les zones > ~35Ã—35 km.
    SEUIL_WARP_GO = 0.8   # Go non-compressÃ© estimÃ©

    res_max = 2 * EARTH_CIRC / (TILE_SIZE * 2 ** zoom_max)

    # Bbox source en Lambert93 â€” fournie directement par main() si connue
    # (Ã©vite gdalinfo qui peut Ã©chouer sans proj.db sur certaines installations)
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
        print(f"  Taille estimÃ©e : ~{taille_go_est:.1f} Go â†’ warp unique"
              f" (GDAL streaming)", flush=True)

    # Warp unique â€” GDAL gÃ¨re le streaming en interne, pas besoin de banding
    # Le banding causait des artefacts car la conversion Lambert93â†’Mercator
    # des limites de bandes n'Ã©tait pas cohÃ©rente avec le tuilage Pillow.
    tranches = [(None, None, "unique")]

    # Niveaux gdaladdo â€” gauss > average pour hillshades (rendu 8 bits)
    overview_levels = [2 ** (zoom_max - z)
                       for z in range(zoom_max - 1, zoom_min - 1, -1)]

    # â”€â”€ MBTiles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    mbtiles.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(mbtiles))
    con.execute("PRAGMA journal_mode=WAL;")   # Ã©critures concurrentes sans lock global
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
    # "left,bottom,right,top" en degrÃ©s WGS84
    if bbox_l93 is not None:
        _lon0, _lat0 = _lamb93_to_wgs84_safe(bbox_l93[0], bbox_l93[1])
        _lon1, _lat1 = _lamb93_to_wgs84_safe(bbox_l93[2], bbox_l93[3])
        _bounds = f"{min(_lon0,_lon1):.6f},{min(_lat0,_lat1):.6f},{max(_lon0,_lon1):.6f},{max(_lat0,_lat1):.6f}"
        _cx = (min(_lon0,_lon1) + max(_lon0,_lon1)) / 2
        _cy = (min(_lat0,_lat1) + max(_lat0,_lat1)) / 2
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("bounds", _bounds))
        cur.execute("INSERT INTO metadata VALUES (?,?)",
                    ("center", f"{_cx:.6f},{_cy:.6f},{zoom_max}"))
    con.commit()

    total_insere = 0
    t_tile = time.time()
    # InitialisÃ© avant la boucle pour rester accessible mÃªme si le warp
    # plante avant d'atteindre la phase de tuilage (cf. bloc plus bas
    # qui le dÃ©crÃ©mente puis affiche un rÃ©capitulatif).
    nb_echecs_tr = 0

    # â”€â”€ Pool d'encodage des tuiles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Pillow libÃ¨re le GIL pendant JPEG/PNG save, donc un ThreadPool donne du vrai
    # parallÃ©lisme. Le pool est crÃ©Ã© une fois pour toute la pyramide et fermÃ©
    # Ã  la fin. Sur petites bandes (<_MIN_PAR_TILES tuiles), on bypass le pool
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
            _tile.convert("RGB").save(_buf, "PNG",
                                       optimize=False, compress_level=1)
        _y_tms = (2 ** _z - 1) - _ty
        return (_z, _tx, _y_tms, _buf.getvalue())

    for i_tr, (y0_l, y1_l, nom_tr) in enumerate(tranches):
        # Fichier warped persistant dans dossier_ville â€” prÃ©fixe _ pour
        # Ãªtre ignorÃ© par le glob MBTiles (not t.name.startswith("_")).
        # Nom dÃ©terministe : source + zoom_max â†’ rÃ©utilisable si on relance
        # avec des zooms diffÃ©rents sur le mÃªme TIF source.
        warped = dossier_ville / f"{tif_source.stem}_tuilage_z{zoom_max}.tif"
        lbl    = warped.name

        # Si la source est dÃ©jÃ  en EPSG:3857 (ex: _warped_*.tif rÃ©utilisÃ©),
        # pas besoin de re-warper â€” on l'utilise directement comme warped.
        if source_already_warped:
            warped = tif_source
            warp_deja_fait = True
            print(f"  Source dÃ©jÃ  en EPSG:3857 â€” warp ignorÃ©", flush=True)
        else:
            warp_deja_fait = warped.exists() and warped.stat().st_size > 1_000_000 and not ecraser_tuiles
            if warp_deja_fait:
                print(f"  Warped cache : {warped.name}  "
                      f"({warped.stat().st_size/1e6:.0f} Mo) â€” rÃ©utilisÃ©", flush=True)

        # â”€â”€ 1. Warp via rasterio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Plus de cmd_warp gdalwarp Ã  construire â€” voir bloc rasterio.warp
        # plus bas. On garde le calcul de te_xmin/etc. pour la bbox cible.
        # â”€â”€ Calcul de l'Ã©tendue cible en Web Mercator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        te_xmin = te_ymin = te_xmax = te_ymax = None
        # Conversion Lambert 93 â†’ WGS84 â†’ Web Mercator en Python pur.
        def _lamb93_to_merc(x, y):
            lon, lat = lamb93_to_wgs84_approx(x, y)
            mx = math.radians(lon) * 6378137.0
            my = math.log(math.tan(math.pi/4 + math.radians(lat)/2)) * 6378137.0
            return mx, my

        if bb_src is not None:
            x0, y0_bb, x1, y1_bb = bb_src
            # En mode banding : restreindre Ã  la tranche courante
            _y0 = y0_l if y0_l is not None else y0_bb
            _y1 = y1_l if y1_l is not None else y1_bb
            try:
                _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:3857")
                te_xmin, te_ymin = _t.transform(x0, _y0)
                te_xmax, te_ymax = _t.transform(x1, _y1)
            except Exception:
                te_xmin, te_ymin = _lamb93_to_merc(x0, _y0)
                te_xmax, te_ymax = _lamb93_to_merc(x1, _y1)
        elif y0_l is not None:
            te_xmin, te_ymin = _lamb93_to_merc(bb_src[0], y0_l)
            te_xmax, te_ymax = _lamb93_to_merc(bb_src[2], y1_l)

        if not warp_deja_fait:
            # â”€â”€ 1. Warp via rasterio (remplace gdalwarp CLI â€” Ã©tape 5) â”€â”€â”€â”€â”€â”€
            # Lambert 93 (EPSG:2154) â†’ Web Mercator (EPSG:3857) avec
            # rÃ©Ã©chantillonnage bilinÃ©aire et rÃ©solution cible res_max.
            # Conserve le -te (target extent) calculÃ© ci-dessus pour ne pas
            # dÃ©pendre de proj.db pour la conversion d'Ã©tendue.
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
                    # Sinon : calculate_default_transform calcule l'Ã©tendue
                    # automatiquement Ã  partir des bounds de la source.
                    if te_xmin is not None:
                        # Dimensions cible Ã  partir de la bbox + rÃ©solution
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
                print("  " + lbl.ljust(36) + " [" + "â–ˆ"*30 +
                      f"] 100%  {_hms(elap)}  {taille_w:.0f} Mo")
            except Exception as _e_warp:
                print(f"  ERREUR rasterio.warp {nom_tr} : {_e_warp}")
                continue

            # â”€â”€ 2. Diagnostic dimensions warped (rasterio) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            bb_diag = _bbox_depuis_gdalinfo(warped)
            if bb_diag:
                try:
                    import rasterio as _rio_dx
                    with _rio_dx.open(str(warped)) as ds_diag:
                        _sz = (ds_diag.width, ds_diag.height)
                    print(f"  warped dims : {_sz[0]} Ã— {_sz[1]} px  "
                          f"bbox merc : {bb_diag[0]:.0f},{bb_diag[1]:.0f}"
                          f" â†’ {bb_diag[2]:.0f},{bb_diag[3]:.0f}", flush=True)
                except Exception:
                    print(f"  warped bbox : {bb_diag}", flush=True)

            # â”€â”€ 3. Overviews via rasterio (remplace gdaladdo â€” Ã©tape 6) â”€â”€â”€â”€â”€â”€
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
                    print(f"  AVERTISSEMENT overviews : {_e_ovw} â€” tuilage natif")

        # â”€â”€ 3. Bbox warped (EPSG:3857) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # PrioritÃ© : -te calculÃ© lors du warp courant (pas besoin de proj.db).
        # Fallback mode cache : recalculer depuis bb_src avec pyproj/approx.
        if te_xmin is not None:
            bb_w = (te_xmin, te_ymin, te_xmax, te_ymax)
        elif warp_deja_fait and bb_src is not None:
            # Warped rÃ©utilisÃ© : reconstruire la bbox Mercator depuis bb_src
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
            print(f"  ERREUR : bbox introuvable pour {lbl}")
            continue
        xmin_w, ymin_w, xmax_w, ymax_w = bb_w

        # â”€â”€ 4. Tiling direct via rasterio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Lecture directe du warped TIF par rasterio â€” pas de gdal_translate,
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
            _w_res    = _ds.transform.a   # rÃ©solution pixel (m/px)
            _w_width  = _ds.width
            _w_height = _ds.height
            _w_count  = _ds.count         # nb bandes

            for z in range(zoom_min, zoom_max + 1):
                tx0, ty0 = merc_to_tile(xmin_w, ymax_w, z)
                tx1, ty1 = merc_to_tile(xmax_w, ymin_w, z)
                nb_cols  = tx1 - tx0 + 1
                band_w   = nb_cols * TILE_SIZE

                # RÃ©solution de cette tuile par rapport au warped (qui est Ã  zoom_max)
                zoom_factor = 2 ** (zoom_max - z)

                for ty in range(ty0, ty1 + 1):
                    bx0_t, _, _, by1_t = tile_bounds(tx0, ty, z)
                    _,     _, bx1_t, _ = tile_bounds(tx1, ty, z)

                    # CoordonnÃ©es pixel dans le warped TIF
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
                        # RangÃ©e entiÃ¨rement hors du TIF
                        pct = int(rangees_done / total_rangees_tr * 100)
                        elapsed = int(time.time() - t_tile)
                        sfx = f"  {_hms(elapsed)}" if elapsed % 30 == 0 else ""
                        print(f"\r  z{zoom_min}-{zoom_max} [" +
                              "â–ˆ" * int(pct/100*30) +
                              "â–‘" * (30 - int(pct/100*30)) +
                              f"] {pct:3d}%  {total_insere} tuiles  {_hms(elapsed)}{sfx}",
                              end="", flush=True)
                        continue

                    try:
                        # Lire la fenÃªtre directement Ã  la rÃ©solution tuile
                        # (rasterio redimensionne via out_shape â€” Ã©vite les grandes allocations)
                        win_w = px_end - px_clip
                        win_h = py_end - py_clip
                        out_w = max(1, int(win_w / zoom_factor))
                        out_h = max(1, int(win_h / zoom_factor))
                        win = _Win(px_clip, py_clip, win_w, win_h)
                        arr = _ds.read(window=win,
                                       out_shape=(_w_count, out_h, out_w),
                                       resampling=_rio.enums.Resampling.bilinear)

                        # Canvas Ã  la taille de la bande de tuiles
                        dst_x = max(0, int((px_clip - px_off) / zoom_factor))
                        dst_y = max(0, int((py_clip - py_off) / zoom_factor))
                        canvas = _np.zeros(
                            (_w_count, TILE_SIZE, band_w), dtype=_np.uint8)
                        canvas[:, dst_y:dst_y+arr.shape[1],
                                  dst_x:dst_x+arr.shape[2]] = arr

                        # Convertir en image PIL et redimensionner si zoom < zoom_max
                        if _w_count >= 3:
                            img_arr = _np.moveaxis(canvas[:3], 0, 2)
                        else:
                            img_arr = _np.stack(
                                [canvas[0]] * 3, axis=2)

                        band_img = Image.fromarray(img_arr.astype(_np.uint8))
                        # Pas de resize â€” rasterio a dÃ©jÃ  lu Ã  la bonne rÃ©solution

                    except Exception as _e_read:
                        nb_echecs_tr += 1
                        if nb_echecs_tr <= 3:
                            print(f"\n  âš  rasterio read Ã©chec z{z} ty={ty}: "
                                  f"{_e_read}", flush=True)
                        pct = int(rangees_done / total_rangees_tr * 100)
                        elapsed = int(time.time() - t_tile)
                        print(f"\r  z{zoom_min}-{zoom_max} [" +
                              "â–ˆ" * int(pct/100*30) +
                              "â–‘" * (30 - int(pct/100*30)) +
                              f"] {pct:3d}%  {total_insere} tuiles  {_hms(elapsed)}",
                              end="", flush=True)
                        continue

                    # DÃ©couper en tuiles individuelles puis encoder en parallÃ¨le
                    # (Pillow libÃ¨re le GIL pendant JPEG/PNG save â†’ ThreadPool donne
                    # un vrai parallÃ©lisme. Sur petites bandes le pool overhead l'emporte ;
                    # on bascule sur sÃ©quentiel sous _MIN_PAR_TILES tuiles.)
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
                      "â–ˆ"*bars + "â–‘"*(30-bars) +
                      f"] {pct:3d}%  {total_insere} tuiles  {_hms(elapsed)}{sfx}",
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

        # warped conservÃ© dans dossier_ville/ pour rÃ©utilisation future
        taille_w = warped.stat().st_size / 1e6 if warped.exists() else 0
        print(f"  Cache tuilage conservÃ© : {warped.name}  ({taille_w:.0f} Mo)"
              f"  â€” supprimez-le manuellement si inutile")

    con.close()
    if _pool is not None:
        _pool.shutdown(wait=True)
    elapsed = int(time.time() - t0)
    taille_mb = mbtiles.stat().st_size / 1e6 if mbtiles.exists() else 0
    print("\n  z" + str(zoom_min) + "-" + str(zoom_max) + " 100%  " + str(total_insere) + " tuiles  " + _hms(elapsed))
    if nb_echecs_tr > 0:
        print(f"  âš  {nb_echecs_tr} rangÃ©es rasterio Ã©chouÃ©es (tuiles manquantes)")
    print(f"  {mbtiles.name} : {total_insere} tuiles  ({taille_mb:.0f} Mo)")
    # DÃ©tection d'Ã©chec silencieux : 0 tuiles depuis une source non-triviale
    # indique typiquement un TIF source partiellement Ã©crit (exception dans
    # un chunk SVF non dÃ©tectÃ©e) ou une reprojection EPSG:3857 hors-bbox.
    # tif_source = paramÃ¨tre de la fonction (chemin du TIF source).
    src_size_mb = tif_source.stat().st_size / 1e6 if tif_source.exists() else 0
    if total_insere == 0 and src_size_mb > 1:
        print(f"  âš  AVERTISSEMENT : 0 tuiles gÃ©nÃ©rÃ©es depuis {src_size_mb:.0f} Mo source.")
        print(f"    Le fichier source est peut-Ãªtre partiellement Ã©crit ou mal gÃ©orÃ©fÃ©rencÃ©.")
        print(f"    Supprimez {tif_source.name} et relancez pour forcer le recalcul.")
    return mbtiles


# ============================================================
# PIPELINE WMTS â€” SCAN 25 / ORTHO
# ============================================================

WMTS_URL     = "https://data.geopf.fr/private/wmts"
WMTS_URL_PUB = "https://data.geopf.fr/wmts"
# ClÃ© API IGN â€” chargÃ©e depuis lidar2map.env si prÃ©sent, sinon valeur par dÃ©faut.
# Pour utiliser votre propre clÃ©, crÃ©ez lidar2map.env (non versionnÃ©) avec :
#   IGN_APIKEY=votre_cle
_apikey_env_path = DOSSIER_TRAVAIL / "lidar2map.env"
if _apikey_env_path.exists():
    for _line in _apikey_env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line.startswith("IGN_APIKEY=") and not _line.startswith("#"):
            os.environ.setdefault("IGN_APIKEY", _line.split("=", 1)[1].strip())
            break
APIKEY_DEFAUT = os.environ.get("IGN_APIKEY", "")
# âš  Les couches Scan (scan25, scan25tour, scan100, scanoaci) sont rÃ©servÃ©es aux
# professionnels (CGU IGN). Leur clÃ© d'accÃ¨s n'est pas distribuable aux particuliers.
# Source : rÃ©ponse IGN du 31/03/2026 â€” geoplateforme@ign.fr
# Les couches publiques (planign, ortho, cadastreâ€¦) ne nÃ©cessitent aucune clÃ©.
WMTS_HEADERS  = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/49.0"}

# Couches WMTS IGN â€” (identifiant_layer, style, format, clÃ©_privÃ©e_requise)
# Endpoint public  : https://data.geopf.fr/wmts
# Endpoint privÃ©   : https://data.geopf.fr/private/wmts
# âš  Les couches avec clÃ©_privÃ©e_requise=True nÃ©cessitent une clÃ© API professionnelle.
COUCHES = {
    # â”€â”€ Cartes topographiques (public, sans clÃ©) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "planign":       ("GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2",         "normal", "image/png",  False),
    "etatmajor40":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR40",       "normal", "image/jpeg", False),
    "etatmajor10":   ("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR10",       "normal", "image/jpeg", False),
    "pentes":        ("GEOGRAPHICALGRIDSYSTEMS.SLOPES.MOUNTAIN",   "normal", "image/png",  False),
    # â”€â”€ Imagerie (public, sans clÃ©) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "ortho":         ("ORTHOIMAGERY.ORTHOPHOTOS",                  "normal", "image/jpeg", False),
    # Orthophotographies historiques mÃ©tropole â€” clÃ© pour archÃ©o et exploration
    # (restanques avant dÃ©prise, anciens chemins encore parcourus, cabanons).
    # Couverture variable selon les dÃ©partements : tester avant de se fier dessus.
    "ortho_1950":    ("ORTHOIMAGERY.ORTHOPHOTOS.1950-1965",        "normal", "image/png",  False),
    "ortho_1965":    ("ORTHOIMAGERY.ORTHOPHOTOS.1965-1980",        "normal", "image/png",  False),
    "ortho_1980":    ("ORTHOIMAGERY.ORTHOPHOTOS.1980-1995",        "normal", "image/png",  False),
    # Infrarouge couleur â€” distingue feuillus/rÃ©sineux, repÃ¨re humiditÃ© du sol
    # (utile pour trouver d'anciens drainages, fossÃ©s, cours d'eau dÃ©voyÃ©s).
    "ortho_irc":     ("ORTHOIMAGERY.ORTHOPHOTOS.IRC",              "normal", "image/jpeg", False),
    # Imagerie satellitaire (vrai satellite, pas avion)
    "pleiades":      ("ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2024",      "normal", "image/jpeg", False),
    "spot":          ("ORTHOIMAGERY.ORTHO-SAT.SPOT.2024",          "normal", "image/jpeg", False),
    # Orthos EDUGEO PACA â€” emprises locales restreintes aux centres urbains.
    # Tester d'abord la couverture pour Toulon-HyÃ¨res ou Marseille-Martigues
    # selon ta zone (GarÃ©oult/Mazaugues est entre les deux, hors emprises).
    "edugeo_marseille_1969": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1969", "normal", "image/png", False),
    "edugeo_marseille_1980": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1980", "normal", "image/png", False),
    "edugeo_marseille_1987": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1987", "normal", "image/png", False),
    "edugeo_marseille_1988": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES1988", "normal", "image/png", False),
    "edugeo_marseille_2010": ("ORTHOIMAGERY.EDUGEO.MARSEILLE-MARTIGUES2010", "normal", "image/png", False),
    "edugeo_toulon_1972":    ("ORTHOIMAGERY.EDUGEO.TOULON-HYERES1972",      "normal", "image/png", False),
    # â”€â”€ DonnÃ©es thÃ©matiques (public, sans clÃ©) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "cadastre":      ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS",      "normal", "image/png",  False),
    "ombrage":       ("ELEVATION.ELEVATIONGRIDCOVERAGE.SHADOW",    "normal", "image/png",  False),
    # â”€â”€ Cartes topographiques â€” RÃ‰SERVÃ‰ES AUX PROFESSIONNELS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # AccÃ¨s restreint : compte pro sur cartes.gouv.fr + SIRET requis
    "scan25":        ("GEOGRAPHICALGRIDSYSTEMS.MAPS",              "normal", "image/jpeg", True),
    "scan25tour":    ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN25TOUR",   "normal", "image/jpeg", True),
    "scan100":       ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN100",      "normal", "image/jpeg", True),
    "scanoaci":      ("GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN-OACI",    "normal", "image/jpeg", True),
}


# Cache GetCapabilities WMTS en session : (layer_id, apikey_requis) â†’ (zoom_min, zoom_max) | None
_wmts_caps_cache: dict = {}
_wmts_caps_lock  = threading.Lock()   # protÃ¨ge les lectures/Ã©critures concurrentes


def _lire_zoom_limites_wmts(layer, apikey_requis, apikey=""):
    """
    Interroge GetCapabilities WMTS IGN et retourne (zoom_min, zoom_max) rÃ©els
    pour la couche *layer* dans le TileMatrixSet PM.
    RÃ©sultat mis en cache pour la session ; retourne None si inaccessible.
    """
    cache_key = (layer, bool(apikey_requis))

    # Lecture du cache â€” verrou court, pas de rÃ©seau dedans
    with _wmts_caps_lock:
        if cache_key in _wmts_caps_cache:
            return _wmts_caps_cache[cache_key]

    # RequÃªte rÃ©seau hors du verrou (Ã©vite de bloquer les autres threads)
    base = WMTS_URL if apikey_requis else WMTS_URL_PUB
    url  = f"{base}?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0"
    if apikey_requis and apikey:
        url += f"&apikey={apikey}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _HTTP_UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        print(f"  âš  GetCapabilities WMTS inaccessible ({type(e).__name__}: {e}) â€” plafonnement zoom ignorÃ©")
        with _wmts_caps_lock:
            _wmts_caps_cache[cache_key] = None
        return None

    _NS = {
        "wmts": "http://www.opengis.net/wmts/1.0",
        "ows":  "http://www.opengis.net/ows/1.1",
    }
    try:
        root = _ET.fromstring(xml_bytes)
    except Exception as e:   # xml.etree.ElementTree.ParseError â€” pas importÃ© directement
        print(f"  âš  Parsing GetCapabilities Ã©chouÃ© ({e})")
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
    """CoordonnÃ©es WGS84 â†’ tuile XYZ (convention Google/OSM, y=0 en haut)."""
    n = 2 ** zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    lat_r = math.radians(lat_deg)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi)
            / 2.0 * n)
    return x, max(0, min(n - 1, y))


def calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max, zoom_min, zoom_max):
    """
    Retourne la liste de toutes les tuiles (z, x, y) couvrant la bbox WGS84
    pour tous les zooms demandÃ©s.
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
    """Estimation grossiÃ¨re : ~15 Ko/tuile JPEG Scan25, ~30 Ko ortho."""
    ko_par_tuile = 30 if format_img != "jpeg" else 15
    return nb_tuiles * ko_par_tuile // 1024   # Mo

# ============================================================
# CONSTRUCTION URL WMTS
# ============================================================

def construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """
    Construit l'URL WMTS IGN pour la tuile (z, x, y).
    Convention WMTS : TileMatrix=z, TileCol=x, TileRow=y (XYZ standard).
    """
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
# TÃ‰LÃ‰CHARGEMENT D'UNE TUILE
# ============================================================



def telecharger_tuile(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """
    TÃ©lÃ©charge une tuile et retourne les bytes, ou None si absente/erreur.
    RÃ©essaie MAX_TENTATIVES fois avec dÃ©lai exponentiel.
    """
    url = construire_url_wmts(z, x, y, layer, style, fmt, apikey, apikey_requis)
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            try:
                resp = _urlopen(url, headers=WMTS_HEADERS, timeout=15)
            except urllib.error.HTTPError as _e:
                if _e.code == 404:
                    return None
                raise IOError(f"HTTP {_e.code}") from _e
            # `with` ferme le socket mÃªme sur exception â†’ pas de FD leak.
            with resp:
                ct = resp.headers.get("content-type", "")
                if "xml" in ct or "html" in ct:
                    return None   # rÃ©ponse d'erreur serveur
                data = resp.read()
            if len(data) < 500:
                return None   # tuile vide (mer, hors couverture)
            return data
        except KeyboardInterrupt:
            # Propagation au handler top-level (sys.exit(130)) qui sait
            # nettoyer (lockfile, tmp). sys.exit(0) ici tuerait juste le
            # worker, masquerait l'interruption et casserait le code retour.
            raise
        except (urllib.error.URLError, IOError, OSError):
            if tentative < MAX_TENTATIVES:
                time.sleep(DELAI_RETRY * tentative)
            else:
                return None   # Ã©chec dÃ©finitif, on ignore
    return None

# ============================================================
# GÃ‰NÃ‰RATION MBTILES
# ============================================================

def generer_mbtiles_wmts(chemin, tuiles_iter, total, nom_zone, fmt_ext,
                    zoom_min, zoom_max, layer, style, img_fmt,
                    apikey, apikey_requis, workers,
                    bbox_wgs84=None, jpeg_quality=None,
                    dossier_cache=None, ecraser_tuiles=False, ecraser_dalles=False):
    """
    TÃ©lÃ©charge toutes les tuiles et les insÃ¨re dans un fichier MBTiles.

    Convention MBTiles : y en TMS (y=0 en bas) â†’ inversion depuis XYZ.

    jpeg_quality   : si dÃ©fini et img_fmt est PNG, convertit PNGâ†’JPEG Ã  cette
                     qualitÃ© (gain Ã—3-5 sans double compression).
    dossier_cache  : si dÃ©fini, les tuiles sont mises en cache sur disque
                     sous dossier_cache/<z>/<x>/<y>.<ext> et rÃ©utilisÃ©es
                     sans retÃ©lÃ©charger lors des runs suivants.
    """

    if chemin.exists() and not ecraser_tuiles:
        print(f"  {chemin.name} â†’ dÃ©jÃ  prÃ©sent")
        return chemin
    if chemin.exists() and ecraser_tuiles:
        chemin.unlink()
        print(f"  {chemin.name} â†’ Ã©crasement")

    chemin.parent.mkdir(parents=True, exist_ok=True)

    # Calculer _convert_png ici â€” utilisÃ© pour _meta_fmt et dans _dl
    _convert_png = (jpeg_quality is not None
                    and img_fmt.lower() in ("image/png", "png"))
    _meta_fmt    = "jpeg" if _convert_png else fmt_ext

    con = sqlite3.connect(str(chemin))
    con.execute("PRAGMA journal_mode=WAL;")   # Ã©critures concurrentes sans lock global
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

    # bounds requis par Locus : "left,bottom,right,top" en degrÃ©s WGS84
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
    FENETRE     = workers * 4   # nb de futures en vol simultanÃ© â€” Ã©quilibre RAM/dÃ©bit
    batch       = []
    done        = 0
    ok          = 0
    absentes    = 0    # 204 No Content (tuile hors couverture) â€” Ã©tat IGN normal
    erreurs     = 0    # exceptions worker (timeout, 401, 5xx, parsing) â€” diagnostic
    err_consec  = 0    # erreurs consÃ©cutives â€” utile pour dÃ©tection panne globale
    abort_msg   = None # set si on abort Ã  mi-parcours (clÃ© expirÃ©e, etc.)
    # Seuil d'abandon : au-delÃ  de SEUIL_ERR_CONSEC erreurs consÃ©cutives,
    # on assume une panne systÃ©mique (clÃ© API expirÃ©e, IGN down, rÃ©seau coupÃ©)
    # et on n'Ã©crit pas un MBTiles tronquÃ© qui aurait l'apparence d'un succÃ¨s.
    largeur     = 30
    t0          = time.time()

    _base_wmts = WMTS_URL if apikey_requis else WMTS_URL_PUB
    _log_req(f"{_base_wmts}?SERVICE=WMTS&LAYER={layer}&...", "WMTS IGN")
    print(f"  TÃ©lÃ©chargement {total:,} tuiles â†’ {chemin.name}...", flush=True)

    _fmt_out = "jpeg" if _convert_png else fmt_ext   # format rÃ©el insÃ©rÃ©

    # Quand on re-encode PNGâ†’JPEG avec une qualitÃ© explicite, le binaire stockÃ©
    # dÃ©pend de jpeg_quality. Sans versionner, un changement de --qualite-image
    # rÃ©utiliserait silencieusement les tuiles de l'ancienne qualitÃ©.
    # Si img_fmt est nativement JPEG (pas de re-encode), le cache ne dÃ©pend
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
            # Ã‰crire dans le cache
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

    tuiles_list = list(tuiles_iter)   # dÃ©jÃ  une liste, mais on s'assure
    z_courant   = tuiles_list[0][0] if tuiles_list else zoom_min

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Soumission par fenÃªtre glissante : on ne soumet FENETRE tÃ¢ches Ã  la fois
            # â†’ la barre dÃ©marre immÃ©diatement, RAM bornÃ©e mÃªme sur 100k tuiles
            pending = {}
            idx     = 0
            n       = len(tuiles_list)

            # Remplir la fenÃªtre initiale
            while idx < n and len(pending) < FENETRE:
                t = tuiles_list[idx]
                pending[pool.submit(_dl, t)] = t
                idx += 1

            # Boucle principale : on attend qu'au moins une future termine, puis
            # on draine TOUTES les futures terminÃ©es avant de re-remplir la fenÃªtre.
            # Performance : wait() enregistre ses callbacks UNE fois par appel,
            # contrairement Ã  next(as_completed(pending)) en boucle qui rÃ©enregistre
            # des callbacks sur toutes les futures Ã  chaque itÃ©ration
            # (complexitÃ© O(N Ã— FENETRE) â†’ O(N) en surcharge bookkeeping).
            # Sur 100k tuiles dept-scale : gagne plusieurs minutes de CPU pur overhead.
            while pending:
                if _stop_event.is_set() or abort_msg is not None:
                    # Cancellation propre : annuler les futures non dÃ©marrÃ©es,
                    # laisser les actives finir leur HTTP courant.
                    for f in list(pending.keys()):
                        f.cancel()
                    break

                done_set, _ = wait(pending, return_when=FIRST_COMPLETED)

                # Drainer tout ce qui est terminÃ© (peut Ãªtre plusieurs en concurrent)
                for done_future in done_set:
                    del pending[done_future]

                    try:
                        z, x, y, data = done_future.result()
                    except Exception as _exc_dl:
                        # Une exception worker n'est PAS une absence (204 IGN normal).
                        # On la compte distinctement pour diagnostiquer panne rÃ©seau,
                        # 401/403 (clÃ© expirÃ©e), 5xx persistants, etc. Si trop d'erreurs
                        # consÃ©cutives, on assume une panne systÃ©mique et on abort.
                        done       += 1
                        erreurs    += 1
                        err_consec += 1
                        if err_consec >= SEUIL_ERR_CONSEC and abort_msg is None:
                            abort_msg = (f"{err_consec} erreurs consÃ©cutives "
                                         f"(derniÃ¨re : {type(_exc_dl).__name__}: {_exc_dl}). "
                                         f"Probable panne rÃ©seau / clÃ© API / IGN. "
                                         f"MBTiles non finalisÃ© pour Ã©viter un fichier tronquÃ©.")
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
                        err_consec = 0   # succÃ¨s : reset
                    else:
                        absentes += 1
                        # 204 No Content (data=None) â€” pas une erreur rÃ©seau, pas
                        # de reset du compteur consÃ©cutif (on ne veut pas que
                        # 100 tuiles hors couverture entrecoupÃ©es masquent une
                        # panne transitoire qui revient).

                    if len(batch) >= BATCH:
                        cur.executemany(
                            "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                        con.commit()
                        batch.clear()

                    _afficher(done, total, ok, absentes, erreurs, z_courant, t0)

                    # Soumettre la prochaine tÃ¢che pour maintenir la fenÃªtre pleine
                    if idx < n:
                        t = tuiles_list[idx]
                        pending[pool.submit(_dl, t)] = t
                        idx += 1

        if batch:
            cur.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con.commit()
    finally:
        # Toujours fermer la connexion, mÃªme sur exception non capturÃ©e
        # (KeyboardInterrupt, MemoryError, OSError disque pleinâ€¦).
        # Sans Ã§a la WAL reste ouverte, le .mbtiles-wal/-shm traÃ®ne.
        try: con.close()
        except Exception: pass

    if abort_msg is not None:
        # MBTiles supprimÃ© : un fichier vide-presque ferait croire Ã  un succÃ¨s.
        # Si l'utilisateur veut analyser le partiel, il rejouera et verra les
        # logs.
        try: chemin.unlink(missing_ok=True)
        except Exception: pass
        print(f"\n  âœ— ABANDON : {abort_msg}")
        raise RuntimeError(f"WMTS abort : {abort_msg}")

    if _stop_event.is_set():
        # Manifeste partiel : signaler Ã  l'utilisateur que l'Ã©criture est incomplÃ¨te
        elapsed = int(time.time() - t0)
        taille_mo = chemin.stat().st_size / 1e6 if chemin.exists() else 0.0
        print(f"\n  Interrompu â€” {ok} tuiles Ã©crites avant arrÃªt  ({taille_mo:.0f} Mo)")
        raise KeyboardInterrupt("MBTiles WMTS interrompu par utilisateur")

    elapsed = int(time.time() - t0)
    taille_mo = chemin.stat().st_size / 1e6
    err_str = f"  ({erreurs} erreurs)" if erreurs else ""
    print(f"\n  100%  {ok} tuiles  ({absentes} absentes){err_str}  {_hms(elapsed)}")
    print(f"  {chemin.name} : {ok} tuiles  ({taille_mo:.0f} Mo)")
    return chemin

# ============================================================
# GÃ‰NÃ‰RATION RMAP
# ============================================================

# â”€â”€ Helpers LE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _wi(v):  return struct.pack('<i', v)   # int32 little-endian signÃ©
def _wl(v):  return struct.pack('<q', v)   # int64 little-endian signÃ©

def _tile_to_geo(tx, ty_xyz, z):
    """Retourne (lon_min, lat_min, lon_max, lat_max) pour la tuile XYZ."""
    n = 2 ** z
    lon_min = tx / n * 360.0 - 180.0
    lon_max = (tx + 1) / n * 360.0 - 180.0
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty_xyz / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty_xyz + 1) / n))))
    return lon_min, lat_min, lon_max, lat_max

def _empty_jpeg_256():
    """GÃ©nÃ¨re un JPEG 256Ã—256 gris (tuile vide pour positions sans donnÃ©es)."""
    try:
        from PIL import Image
        img = Image.new('RGB', (256, 256), (180, 180, 180))
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=50)
        return buf.getvalue()
    except Exception:
        # Fallback : JPEG minimal valide 1Ã—1 px gris
        # (sÃ©quence SOI + APP0 + DQT + SOF0 + DHT + SOS + EOI)
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

# â”€â”€ Fonction principale â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generer_rmap_depuis_mbtiles(mbtiles_path, ecraser=False):
    """
    GÃ©nÃ¨re un fichier .rmap (format binaire CompeGPS/TwoNav) depuis un .mbtiles.

    Format RMAP â€” reverse-engineered depuis MOBAC TwoNavRMAP.java (GPL v2) :

    FILE HEADER (offset 0, little-endian) :
      "CompeGPSRasterImage"    19 bytes ASCII (magic)
      int32  10 Â· int32  7 Â· int32  0
      int32  width_max Â· int32  -height_max
      int32  24 (bpp) Â· int32  1
      int32  256 (tileW) Â· int32  256 (tileH)
      int64  mapDataOffset
      int32  0 Â· int32  nZooms
      int64 Ã— nZooms  zoom_header_offsets

    ZOOM HEADER (Ã  zoom_header_offsets[n]) :
      int32  width Â· int32  -height
      int32  xTiles Â· int32  yTiles
      int64 Ã— (xTiles Ã— yTiles)  tile_offsets
        ordre : y outer, x inner â†’ jpegOffsets[x][y]

    TILE (Ã  tile_offsets[tx][ty]) :
      int32  7 (tag) Â· int32  len(jpeg) Â· bytes jpeg

    MAP INFO (Ã  mapDataOffset) :
      int32  1 (tag) Â· int32  len(text) Â· bytes text (CompeGPS MAP format ASCII)

    Contrainte RMAP : tous les zoom levels doivent couvrir la mÃªme zone gÃ©o.
    Convention y : XYZ (y=0 haut, Nord), inverse du TMS stockÃ© dans MBTiles.
    """

    rmap = mbtiles_path.with_suffix(".rmap")
    if rmap.exists() and not ecraser:
        print(f"  {rmap.name} â†’ dÃ©jÃ  prÃ©sent")
        return rmap
    if rmap.exists() and ecraser:
        rmap.unlink()
    if not mbtiles_path.exists():
        print(f"  ERREUR : {mbtiles_path.name} introuvable")
        return None

    print(f"  RMAP â† {mbtiles_path.name}...", flush=True)
    t0 = time.time()

    EMPTY_JPEG = _empty_jpeg_256()
    TILE_SZ    = 256

    con = sqlite3.connect(str(mbtiles_path))
    try:
        # â”€â”€ Phase 1 : inventaire par zoom â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        zooms = [r[0] for r in con.execute(
            "SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level DESC").fetchall()]
        if not zooms:
            print("  ERREUR : MBTiles vide")
            return None

        # Ã‰tendue (x, y XYZ) par zoom
        zm = {}
        for z in zooms:
            r = con.execute(
                "SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
                "FROM tiles WHERE zoom_level=?", (z,)).fetchone()
            xmin_c, xmax_c, ymin_tms, ymax_tms = r
            n = 1 << z
            # TMS â†’ XYZ : y_xyz = (n-1) - y_tms
            y0_xyz = (n - 1) - ymax_tms   # petit y_tms = grand y_xyz (Nord)
            y1_xyz = (n - 1) - ymin_tms
            nx = xmax_c - xmin_c + 1
            ny = y1_xyz - y0_xyz + 1
            zm[z] = {'x0': xmin_c, 'y0': y0_xyz, 'nx': nx, 'ny': ny,
                      'w': nx * TILE_SZ, 'h': ny * TILE_SZ}

        # Zoom le plus dÃ©taillÃ© = index 0 dans RMAP
        z_max   = zooms[0]
        w_max   = zm[z_max]['w']
        h_max   = zm[z_max]['h']
        n_zooms = len(zooms)

        # CoordonnÃ©es gÃ©o depuis zoom max
        zd     = zm[z_max]
        lon_min, lat_min, lon_max, lat_max = _tile_to_geo(
            zd['x0'], zd['y0'] + zd['ny'] - 1, z_max)
        lon_max = _tile_to_geo(zd['x0'] + zd['nx'] - 1, zd['y0'], z_max)[2]
        lat_max = _tile_to_geo(zd['x0'], zd['y0'], z_max)[3]

        total_tiles = sum(zm[z]['nx'] * zm[z]['ny'] for z in zooms)
        print(f"  {n_zooms} zoom(s), {total_tiles:,} positions de tuiles", flush=True)

        # â”€â”€ Phase 2 : Ã©criture sÃ©quentielle â€” offsets enregistrÃ©s Ã  la volÃ©e â”€â”€
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

                    # PrÃ©-chargement des tuiles de ce zoom en mÃ©moire : une seule
                    # requÃªte au lieu de nxÃ—ny SELECTs (gain Ã—100 Ã  Ã—1000 sur les
                    # gros MBTiles). MÃ©moire bornÃ©e par le zoom courant â€” libÃ©rÃ©e
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
                                print(f"\r  RMAP z{z} [{'â–ˆ'*bars}{'â–‘'*(largeur-bars)}]"
                                      f" {pct:3d}%  {done:,}/{total_tiles:,}"
                                      f"  {_hms(elapsed)}",
                                      end="", flush=True)

                    # LibÃ©rer la mÃ©moire des tuiles de ce zoom avant le suivant
                    tuiles_z = None

                    # --- RÃ‰Ã‰CRIRE le zoom header avec les vrais offsets ---
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

                # --- RÃ‰Ã‰CRIRE FILE HEADER avec vrais offsets ---
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
        print(f"\n  {rmap.name} : {taille_mo:.0f} Mo  {_hms(elapsed)}")
        return rmap
    finally:
        # Garantit la fermeture de la connexion SQLite mÃªme sur exception
        # non capturÃ©e (KeyboardInterrupt, MemoryError, disque pleinâ€¦).
        try: con.close()
        except Exception: pass


def generer_sqlitedb_depuis_mbtiles(mbtiles_path, ecraser=False):
    """
    GÃ©nÃ¨re un fichier .sqlitedb (format natif Locus Map) depuis un .mbtiles.

    SchÃ©ma SQLiteDB (format interne Locus / RMaps Android) :
      CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB)
      CREATE TABLE android_metadata (locale TEXT)
      CREATE TABLE info (minzoom INT, maxzoom INT)

    CoordonnÃ©es : x=col, y=row XYZ (y=0 en haut/Nord), z=zoom, s=0 (inutilisÃ©).
    Conversion TMSâ†’XYZ : y_xyz = (2^z - 1) - tile_row_tms.

    C'est le format que Locus utilise en interne pour son cache de cartes en ligne.
    ZÃ©ro risque de compatibilitÃ©, auto-load et Quick map switch fonctionnent.
    """

    sqlitedb = mbtiles_path.with_suffix(".sqlitedb")
    if sqlitedb.exists() and not ecraser:
        print(f"  {sqlitedb.name} â†’ dÃ©jÃ  prÃ©sent")
        return sqlitedb
    if sqlitedb.exists() and ecraser:
        sqlitedb.unlink()
    if not mbtiles_path.exists():
        print(f"  ERREUR : {mbtiles_path.name} introuvable")
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

        print(f"  SQLiteDB â† {mbtiles_path.name}  ({total:,} tuiles)...", flush=True)
        t0 = time.time()

        con_db = sqlite3.connect(str(sqlitedb))
        con_db.execute("PRAGMA journal_mode=WAL;")   # Ã©critures concurrentes sans lock global
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
                y_xyz = (1 << zoom_level) - 1 - tile_row   # TMS â†’ XYZ
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
                    print(f"\r  SQLiteDB [{'â–ˆ'*bars}{'â–‘'*(largeur-bars)}]"
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
        print(f"\n  {sqlitedb.name} : {done:,} tuiles  ({taille_mo:.0f} Mo)"
              f"  {_hms(elapsed)}          ")
        return sqlitedb
    finally:
        # Toujours fermer les deux connexions, mÃªme sur exception non capturÃ©e.
        try: con_mb.close()
        except Exception: pass
        if con_db is not None:
            try: con_db.close()
            except Exception: pass


def _build_map_info(bitmap_name, width, height, lon_min, lat_min, lon_max, lat_max):
    """GÃ©nÃ¨re le bloc texte CompeGPS MAP (calibration gÃ©ographique)."""
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
    """Options JVM additionnelles Ã  passer Ã  osmosis.

    Mode frozen : pointe `user.home` vers BUNDLE_DIR (sans `.openstreetmap/`)
    pour empÃªcher osmosis de scanner `%USERPROFILE%\\.openstreetmap\\osmosis\\plugins\\`.
    Sinon le plugin mapwriter serait chargÃ© deux fois (CLASSPATH bundlÃ© +
    plugins dir utilisateur) â†’ OsmosisRuntimeException "Task type already exists".
    """
    if not getattr(sys, "frozen", False):
        return ""
    fake_home = str(BUNDLE_DIR).replace("\\", "/")
    # Quoter pour gÃ©rer les espaces dans le chemin (cmd + osmosis.bat).
    return f' "-Duser.home={fake_home}"'


def _preparer_osmosis(dossier_hint=None):
    """
    VÃ©rifie mapwriter, trouve java + osmosis, retourne (osmosis_exe, java_home).
    Retourne (None, None) en cas d'Ã©chec.
    dossier_hint : Path optionnel pour la recherche de tagmapping-min.xml (non utilisÃ© ici).
    """
    if not _verifier_mapwriter():
        print("  ERREUR : plugin mapwriter manquant â€” carte .map impossible.")
        return None, None
    _java_exe = _trouver_java()
    if not _java_exe:
        return None, None
    _osmosis_exe = _trouver_osmosis()
    if not _osmosis_exe:
        print("  ERREUR : osmosis introuvable")
        return None, None
    _java_home = str(Path(_java_exe).parent.parent)
    return _osmosis_exe, _java_home


# Tokens d'intÃ©rÃªt : seules les lignes qui contiennent un de ces marqueurs
# sont AFFICHÃ‰ES en live. Le reste est silencieux (le terminal reste propre,
# comme avant l'Ã©tape 5 quand on faisait capture_output=True).
# Les lignes silencieuses sont quand mÃªme conservÃ©es dans stderr_diag pour
# le diagnostic en cas de returncode != 0.
# Couvre Java util.logging FR/EN, exceptions, et causes chaÃ®nÃ©es.
_OSMOSIS_INTERESSANT = (
    "ERROR", "SEVERE", "FATAL", "Exception", "Caused by",
    "WARNING", "AVERTISSEMENT", "WARN ",
)


def _run_osmosis_streaming(cmd_or_str, shell, env):
    """Lance osmosis en streaming live.

    Remplace `subprocess.run(capture_output=True)` qui buffer toute la sortie
    en RAM (problÃ¨me sur dept-scale oÃ¹ Java peut produire des Mo de logs).

    StratÃ©gie de filtrage : whitelist. Seules les lignes contenant un marqueur
    de _OSMOSIS_INTERESSANT (ERROR, WARNING, Exception, AVERTISSEMENTâ€¦) sont
    affichÃ©es en temps rÃ©el. Les lignes ordinaires (timestamps Java, classes
    org.mapsforge, INFO, SLF4J, etc.) sont silencieuses â€” comportement
    identique Ã  l'ancien capture_output=True en cas de succÃ¨s.

    Garde les 500 derniÃ¨res lignes stderr (accumulation totale, pas filtrÃ©e)
    pour diagnostic en cas d'Ã©chec. Buffer bornÃ©, ~50 Ko max.

    Returns: (returncode, stderr_diagnostic_string)
    """
    import threading as _th

    proc = subprocess.Popen(
        cmd_or_str,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=shell, env=env,
    )

    # Buffer bornÃ© des derniÃ¨res lignes stderr (collections.deque pour O(1) ops)
    from collections import deque
    stderr_tail = deque(maxlen=500)
    affichees = [0]   # nb de lignes vraiment affichÃ©es (pour ajouter \n initial)
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
                        print()  # newline avant la 1Ã¨re ligne intÃ©ressante
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
    parce que la JVM ne libÃ¨re pas tous ses handles Ã  la fermeture. Ces
    fichiers s'accumulent au fil des runs OSM (jusqu'Ã  plusieurs Go).

    SÃ©curitÃ©s :
      - On ne touche pas les fichiers modifiÃ©s dans les ``min_age_s`` derniÃ¨res
        secondes (dÃ©faut 5 min) â€” ils peuvent appartenir Ã  un osmosis en
        cours d'exÃ©cution dans une autre instance.
      - ``PermissionError`` swallow silencieusement (fichier verrouillÃ© par
        un processus encore actif) â€” on retentera au prochain run.

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
                    continue   # trop rÃ©cent, peut-Ãªtre en cours d'utilisation
                size = st.st_size
                f.unlink()
                nb += 1
                bytes_freed += size
            except (OSError, PermissionError):
                pass   # verrouillÃ© ou disparu â€” best-effort
    if nb and verbose:
        print(f"  âœ“ NettoyÃ© {nb} fichier(s) temp osmosis orphelin(s) "
              f"({bytes_freed/1e6:.0f} Mo)")
    return nb, bytes_freed


def generer_carte_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                      osm_tags=None, export_geojson=True, ecraser_tuiles=False,
                      skip_bbox=False, geojson_formats=None):
    """
    GÃ©nÃ¨re une carte Mapsforge (.map) via osmosis â€” format natif Locus Map.
    NÃ©cessite osmosis + tagmapping-min.xml dans le mÃªme dossier que le script.

    geojson_formats : liste des formats Ã  produire pour l'export GeoJSON.
                      ["gz"] (dÃ©faut), ["geojson"], ou ["gz", "geojson"].
    """
    import shutil as _sh

    if geojson_formats is None:
        geojson_formats = ["gz"]

    # Nettoyage des fichiers d'index osmosis orphelins (< 5 min ignorÃ©s pour
    # ne pas tirer dans le pied d'un osmosis concurrent). Best-effort, ne
    # bloque jamais la suite.
    if WINDOWS:
        _nettoyer_osmosis_temp_orphelins(verbose=True)

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    chemin_map     = dossier_ville / f"{nom_zone}.map"
    chemin_map_tmp = dossier_ville / f"{nom_zone}.map.tmp"

    # Nettoyer un Ã©ventuel .map.tmp laissÃ© par une exÃ©cution prÃ©cÃ©dente interrompue
    chemin_map_tmp.unlink(missing_ok=True)

    # VÃ©rifier la prÃ©sence des GeoJSON selon les formats DEMANDÃ‰S, pas
    # selon le premier qu'on trouve. Si on demande "gz geojson" et qu'on
    # n'a que le .gz, il faut quand mÃªme regÃ©nÃ©rer le .geojson manquant.
    chemin_geojson_gz  = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_geojson_raw = dossier_ville / f"{nom_zone}_osm.geojson"
    _need_gz   = "gz"      in geojson_formats
    _need_raw  = "geojson" in geojson_formats
    geojson_present = ((not _need_gz  or chemin_geojson_gz.exists())
                       and (not _need_raw or chemin_geojson_raw.exists()))

    if chemin_map.exists() and ecraser_tuiles:
        chemin_map.unlink()
        print(f"  Carte OSM : Ã©crasement {chemin_map.name}")
        # Supprimer aussi les geojson pour les recalculer
        for _gf in [chemin_geojson_gz, chemin_geojson_raw]:
            if _gf.exists(): _gf.unlink()
    if chemin_map.exists() and not ecraser_tuiles:
        if not export_geojson or geojson_present:
            print(f"  Carte OSM dÃ©jÃ  prÃ©sente : {chemin_map.name} â€” ignorÃ©e")
            return chemin_map
        else:
            # .map ok mais .geojson(.gz) manquant
            # Utiliser le PBF filtrÃ© (dÃ©jÃ  extrait par osmosis) si disponible
            print(f"  Carte OSM dÃ©jÃ  prÃ©sente : {chemin_map.name} â€” GeoJSON manquant, export...")
            chemin_pbf_filtre = dossier_ville / f"{nom_zone}_filtered.pbf"
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            if pbf_src == chemin_pbf_filtre:
                print(f"  PBF filtrÃ© existant : {chemin_pbf_filtre.name}")
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src,
                                osm_tags=osm_tags, ecraser_tuiles=ecraser_tuiles,
                                formats=geojson_formats)
            return chemin_map

    if not _verifier_mapwriter():
        print("  ERREUR : plugin mapwriter manquant â€” carte .map impossible.")
        return None

    _osmosis_exe, _java_home = _preparer_osmosis()
    if not _osmosis_exe:
        return None
    _env_osm = os.environ.copy()
    _env_osm["JAVA_HOME"] = _java_home
    # JAVA_OPTS : heap max 6g â€” nÃ©cessaire pour le PBF France (~5 Go)
    # JAVACMD_OPTIONS : variable lue par osmosis.bat pour passer les options JVM
    _java_extra = _java_opts_extra()
    _env_osm["JAVA_OPTS"]       = "-Xmx6g" + _java_extra
    _env_osm["JAVACMD_OPTIONS"] = "-Xmx6g" + _java_extra

    # tagmapping-min.xml : chercher Ã  cÃ´tÃ© du script puis dans le dossier dalles
    # En mode frozen, le fichier est bundlÃ© dans sys._MEIPASS (BUNDLE_DIR).
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
        print("  AVERTISSEMENT : tagmapping-min.xml introuvable â€” utilisation dÃ©faut osmosis")

    t0 = time.time()
    print(f"  osmosis â†’ {chemin_map.name}...", flush=True)

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
        "type=hd",   # HDTileBasedDataProcessor : Ã©crit sur disque â†’ pas de OutOfMemoryError
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
            print(f"  {chemin_map.name} : {taille_b / 1e6:.1f} Mo  {_hms(time.time()-t0)}")
        if export_geojson:
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src,
                                osm_tags=osm_tags, formats=geojson_formats)
        return chemin_map
    else:
        chemin_map_tmp.unlink(missing_ok=True)
        print(f"  ERREUR osmosis mapfile-writer (code {rc})")
        if stderr_diag:
            # stderr_diag contient les 500 derniÃ¨res lignes (toutes confondues).
            # On extrait celles qui contiennent un marqueur d'erreur/warning.
            lignes_err = [l for l in stderr_diag.splitlines()
                          if any(tok in l for tok in _OSMOSIS_INTERESSANT)]
            if lignes_err:
                print("  DÃ©tail osmosis :")
                for _l in lignes_err[:20]:
                    print(f"    {_l}")
            else:
                # Pas de marqueur connu â†’ afficher la queue brute
                print(f"  {stderr_diag.strip()[-600:]}")
        return None

def main():
    import argparse
    t_debut = time.time()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python lidar2map.py
  python lidar2map.py --ignlidar --zone-ville gareoult --telechargement --ombrages multi slope --mbtiles --oui
  python lidar2map.py --ignlidar --zone-departement 83 --telechargement --ombrages multi --mbtiles --oui
  python lidar2map.py --osm --zone-ville gareoult --oui
        """
    )
    parser.add_argument("--version", action="version",
                        version="lidar2map 1.2.0 (2026-05) â€” multi-provider")
    parser.add_argument("--lidar", "--ignlidar", action="store_true", dest="ignlidar",
                        help="Mode LiDAR MNT IGN")

    # â”€â”€ DÃ©coupage Ã  priori (raster uniquement) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    grp_priori = parser.add_argument_group(
        "DÃ©coupage Ã  priori â€” --ignlidar uniquement",
        "Traitement sÃ©quentiel par morceaux avec reprise automatique (manifeste.json).\n"
        "Les mÃªme paramÃ¨tres contrÃ´lent aussi le dÃ©coupage des fichiers de sortie.")
    grp_priori.add_argument("--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Nombre de colonnes de la grille (Est-Ouest).")
    grp_priori.add_argument("--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Nombre de lignes de la grille (Nord-Sud).")
    grp_priori.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative : dÃ©coupe en carrÃ©s de ~KM km.")
    grp_priori.add_argument("--nettoyage", action="store_true",
                            help="Supprimer dalles + TIF intermÃ©diaires aprÃ¨s chaque morceau. "
                                 "Indispensable pour les grandes zones (dÃ©partement entier).")

    # Localisation + zone
    _ajouter_args_zone(
        parser,
        rayon_default=None,
        bbox_metavar="X1,Y1,X2,Y2",
        bbox_help="BBox Lambert 93 en mÃ¨tres ex: 880000,6210000,1080000,6360000",
        avec_help_full=True,
    )

    # Chemins
    parser.add_argument("--dossier", metavar="CHEMIN", default=None,
                        help="Dossier racine de sortie (dÃ©faut: <script>/ign_lidar/). "
                             "Peut Ãªtre un disque externe.")
    parser.add_argument("--dossier-dalles", metavar="CHEMIN", default=None,
                        help="Dossier cache des dalles IGN (dÃ©faut: <dossier>/dalles/). "
                             "Utile pour sÃ©parer cache et sorties sur disques diffÃ©rents.")

    # TÃ©lÃ©chargement
    parser.add_argument("--provider", default=None, metavar="CODE",
                        help="Provider LiDAR (dÃ©faut: fr-ign). Codes disponibles : "
                             "fr-ign, nl-ahn, ch-swisstopo, no-kartverket, us-3dep. "
                             "Voir providers/")
    parser.add_argument("--apikey", default="", metavar="CLE",
                        help="ClÃ© API du provider quand requise. Pour us-3dep : "
                             "https://portal.opentopography.org/myopentopo. "
                             "Pour IGN scan*: compte pro cartes.gouv.fr (cf. --ignraster). "
                             "Peut aussi Ãªtre dÃ©finie via env IGN_APIKEY ou "
                             "OPENTOPOGRAPHY_API_KEY selon le provider.")
    parser.add_argument("--workers",  type=int,   default=NB_WORKERS, metavar="N",
                        help=f"Connexions parallÃ¨les (dÃ©faut: {NB_WORKERS})")
    parser.add_argument("--telechargement-compresser", action="store_true",
                        help="Compresser les dalles du cache (DEFLATE, ~x5)")
    parser.add_argument("--telechargement-forcer", action="store_true",
                        help="Re-tÃ©lÃ©charger les dalles dÃ©jÃ  prÃ©sentes")

    # Ombrages
    parser.add_argument("--ombrages", metavar="TYPE", nargs="+",
                        choices=["315", "045", "135", "225", "multi", "slope",
                                 "svf", "svf100", "lrm", "rrim", "tous", "aucun"],
                        help=(
                            "Ombrages Ã  gÃ©nÃ©rer (dÃ©faut: interactif). "
                            "Valeurs : 315 045 135 225 multi slope svf svf100 lrm rrim tous aucun. "
                            "svf/svf100/lrm/rrim : calculÃ©s en numpy/scipy (scipy auto-installÃ©). "
                            "Ex: --ombrages multi slope svf rrim"
                        ))
    parser.add_argument("--ombrages-elevation", type=int, default=None, metavar="DEG",
                        help=(f"Angle solaire des hillshades directionnels en degrÃ©s "
                              f"(dÃ©faut: {ELEVATION_SOLEIL}Â° â€” archÃ©o optimal). "
                              f"Usage gÃ©nÃ©ral : 45Â°. ArchÃ©ologie : 20-30Â°."))

    # Mode non-interactif
    parser.add_argument("--oui", action="store_true",
                        help="RÃ©pondre Oui Ã  toutes les questions (non-interactif)")
    parser.add_argument("--telechargement", action="store_true",
                        help="TÃ©lÃ©charger les dalles IGN manquantes.")
    parser.add_argument("--dalles-purger-invalides", action="store_true",
                        help="Supprimer les dalles < 2 Mo du cache (dalles en mer, erreurs partielles). "
                             "Omettre --telechargement pour purger sans re-tÃ©lÃ©charger.")
    parser.add_argument("--dalles-migrer", action="store_true",
                        help="RÃ©organiser les dalles existantes en sous-dossiers par colonne X "
                             "(ex: D:/Lidar/Dalles/0958/LHD_FXX_0958_....tif). "
                             "Ã€ lancer une seule fois pour migrer l'ancienne structure Ã  plat.")
    parser.add_argument("--dalles-renommer", action="store_true",
                        help="Renommer les dalles de l'ancienne convention (x2, ex: 0456_3107) "
                             "vers la nouvelle (x1, ex: 0912_6214). A lancer une seule fois.")
    parser.add_argument("--dalles-purger-hors-zone", action="store_true",
                        help="Supprimer du cache les dalles hors de la zone courante (bbox/dÃ©partement). "
                             "Utile pour libÃ©rer l'espace occupÃ© par des dalles d'autres dÃ©partements. "
                             "Requiert --departement, --bbox, --ville ou --gps.")
    parser.add_argument("--ombrages-compresser",  action="store_true", help="Compresser les ombrages bruts existants (DEFLATE)")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Ã‰craser les dalles tÃ©lÃ©chargÃ©es existantes")
    parser.add_argument("--ombrages-ecraser", action="store_true", dest="ombrages_ecraser",
                        help="Ã‰craser les ombrages existants")
    parser.add_argument("--sweep-horizon", action="store_true", dest="sweep_horizon",
                        help="Kernel SVF sweep-horizon avec running max sur deque "
                             "(upper convex hull). ComplexitÃ© O(WÂ·HÂ·N) au lieu de "
                             "O(WÂ·HÂ·NÂ·max_r). Speedup ~Ã—5-15 pour SVF20m, ~Ã—30-50 "
                             "pour SVF100m, plusieurs centaines pour grands rayons. "
                             "LÃ©ger aliasing NN aux faibles gradients, imperceptible "
                             "pour structures > 1-2 px.")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Ã‰craser les tuiles/MBTiles/.map existants")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles","rmap","sqlitedb","map","gz","geojson"],
                        default=[], metavar="FMT",
                        help="Formats de fichiers de sortie : mbtiles rmap sqlitedb (multi-valeurs).")
    parser.add_argument("--source", metavar="CHEMIN", default=None,
                        help="Fichier source existant â€” mode autonome, zone non requise. "
                             ".tif/.tiff : ombrage existant â†’ MBTiles/RMAP "
                             "            (CRS auto-dÃ©tectÃ© : 3857=tuilage direct, autre=warp). "
                             ".mbtiles   : conversion â†’ RMAP (requiert --rmap). "
                             ".pbf       : donnÃ©es OSM â†’ carte (requiert --osm). "
                             "Ex: --source var_83_hillshade_multi.tif --zone-bbox ... --mbtiles --rmap "
                             "Ex: --source provence-alpes-cote-d-azur-latest.osm.pbf --osm")
    parser.add_argument("--zoom-min", type=int, default=13, metavar="N",
                        help="Zoom minimum des tuiles MBTiles (dÃ©faut: 13)")
    parser.add_argument("--zoom-max", type=int, default=18, metavar="N",
                        help="Zoom maximum des tuiles MBTiles (dÃ©faut: 18)")
    parser.add_argument("--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="QualitÃ© JPEG des images dans les tuiles (dÃ©faut: 85). "
                             "75 = -35%% taille, quasi invisible. 60 = -55%%, lÃ©ger flou.")
    parser.add_argument("--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format des images dans les tuiles : auto, jpeg ou png (dÃ©faut: auto).")
    parser.add_argument("--osm", action="store_true",
                        help="GÃ©nÃ©rer un MBTiles vectoriel de superposition OSM "
                             "(chemins, toponymie, hydrographie, sites historiques). "
                             "Le PBF Geofabrik est tÃ©lÃ©chargÃ© automatiquement si absent.")
    parser.add_argument("--couche", metavar="TAGS", nargs="+", default=None,
                        help="Pour --osm : tags OSM Ã  inclure. "
                             "Ex: --couche highway=* waterway=* natural=water")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    _valider_zooms(args, parser)

    # Propage --apikey au provider actif s'il en utilise une (us-3dep, etc.).
    if hasattr(PROVIDER, "set_apikey"):
        PROVIDER.set_apikey(args.apikey)

    # RÃ©solution --formats-fichier â†’ flags boolÃ©ens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    # Crash-safe : sauver l'entrÃ©e 'en cours' AVANT toute opÃ©ration longue.
    # Si le pipeline crashe, l'entrÃ©e reste â†’ diagnostic facile.
    _historique_debut()

    _osm_seul = args.osm and not args.telechargement and not args.ombrages and not args.mbtiles

    print("=" * 55)
    if _osm_seul:
        print("  Carte OSM vectorielle")
    else:
        print(f"  LiDAR : {PROVIDER.NAME}")
        print("  Pipeline rasterio + numpy (numba pour SVF)")
    print("=" * 55)
    print(f"  Dossier : {args.dossier or str(DOSSIER_TRAVAIL / LIDAR_SUBDIR)}")
    print()

    # â”€â”€ --source : mode autonome selon l'extension + CRS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # .mbtiles â†’ RMAP (requiert --rmap, exit immÃ©diat)
    # .pbf     â†’ OSM  (requiert --osm, injectÃ© dans args.source pour usage ultÃ©rieur)
    # .tif     â†’ MBTiles/RMAP (CRS auto-dÃ©tectÃ© : 3857=tuilage direct, autre=warp)
    #            nÃ©cessite une zone pour la bbox â†’ pas d'exit immÃ©diat
    if args.source:
        src_path = Path(args.source)
        if not src_path.exists():
            ext_src = Path(args.source).suffix.lower()
            if ext_src in (".tif", ".tiff"):
                # TIF cache absent (warped supprimÃ©) â†’ ignorer, on recalcule depuis les dalles
                print(f"  AVERTISSEMENT : source TIF introuvable : {Path(args.source).name}")
                print(f"  Recalcul depuis les dalles...")
                args.source = None
            else:
                print(f"  ERREUR : fichier source introuvable : {args.source}")
                sys.exit(1)
        ext = Path(args.source).suffix.lower() if args.source else ""

        if ext == ".mbtiles":
            # Conversion directe MBTiles â†’ RMAP/SQLiteDB (exit immÃ©diat, pas de zone requise)
            if not args.rmap and not args.sqlitedb:
                print("  ERREUR : --rmap ou --sqlitedb requis pour la conversion MBTiles.")
                print(f"  Ex: --source {src_path.name} --rmap")
                sys.exit(1)
            if args.rmap:
                generer_rmap_depuis_mbtiles(src_path, ecraser=args.tuiles_ecraser)
            if args.sqlitedb:
                generer_sqlitedb_depuis_mbtiles(src_path, ecraser=args.tuiles_ecraser)
            sys.exit(0)

        elif ext in (".pbf", ".osm"):
            # Source OSM : traitÃ©e plus loin dans la section --osm
            if not args.osm:
                print("  ERREUR : --osm requis avec une source .pbf.")
                print(f"  Ex: --source {src_path.name} --zone-ville gareoult --osm")
                sys.exit(1)
            # args.source est dÃ©jÃ  dÃ©fini, sera lu dans la section OSM

        elif ext in (".tif", ".tiff"):
            # Source TIF : dÃ©tection CRS via rasterio
            try:
                import rasterio as _rio_src
                with _rio_src.open(str(src_path)) as _ds_src:
                    _epsg = _ds_src.crs.to_epsg() if _ds_src.crs else None
                if _epsg == 3857:
                    # DÃ©jÃ  en Mercator â†’ tuilage direct, warp inutile
                    args._source_already_warped = True
                    print(f"  Source TIF EPSG:3857 dÃ©tectÃ© â†’ tuilage direct (pas de warp)")
                else:
                    args._source_already_warped = False
                    print(f"  Source TIF EPSG:{_epsg} â†’ warp L93â†’Mercator requis")
            except Exception as _e_crs:
                print(f"  AVERTISSEMENT CRS non dÃ©tectÃ© ({_e_crs}) â€” warp appliquÃ© par dÃ©faut")
                args._source_already_warped = False
        else:
            print(f"  ERREUR : extension non reconnue pour --source : {ext}")
            print("  Extensions acceptÃ©es : .tif .tiff .mbtiles .pbf")
            sys.exit(1)

    # -------------------------------------------------------
    # SÃ©lection de zone â†’ liste de dalles
    # -------------------------------------------------------
    # Si --dalles-migrer sans aucune info de zone : pas besoin de gÃ©ocodage
    _migrer_seul = (getattr(args, 'dalles_migrer', False) and
                    not args.telechargement and not args.ombrages and
                    not args.mbtiles)

    # --source .tif nÃ©cessite une zone pour la bbox
    _source_tif_sans_zone = (
        args.source and Path(args.source).suffix.lower() in (".tif", ".tiff") and
        not args.zone_departement and not args.zone_bbox and
        not args.zone_ville and not args.zone_gps)
    if _source_tif_sans_zone:
        print("  ERREUR : --source TIF nÃ©cessite une zone : --zone-ville/--zone-rayon, --zone-bbox ou --zone-departement")
        sys.exit(1)
    if _migrer_seul and not args.zone_departement and not args.zone_bbox and not args.zone_ville and not args.zone_gps:
        # Mode migration pure : on n'a besoin que de dossier_dalles
        racine        = Path(args.dossier).resolve() if args.dossier else Path(str(DOSSIER_TRAVAIL / LIDAR_SUBDIR))
        dossier_dalles = Path(args.dossier_dalles).resolve() if args.dossier_dalles else DOSSIER_TRAVAIL / "cache" / LIDAR_SUBDIR
        dossier_dalles.mkdir(parents=True, exist_ok=True)
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]
        if not a_migrer:
            print("  Aucune dalle Ã  migrer (dossier racine dÃ©jÃ  vide ou structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} dalle(s) â†’ sous-dossiers par colonne X...")
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
            print(f"\r  Migration terminÃ©e : {migres} dalles dÃ©placÃ©es, {erreurs} erreurs.")
        sys.exit(0)

    cx = cy = 0.0
    dalles = []
    if args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
        nb_dalles = len(dalles)
        # Nom automatique : ex "var_83"
        nom_auto = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        nom_zone  = normaliser_nom(args.zone_nom) if args.zone_nom else nom_auto
        print(f"  Dossier : {nom_zone}  |  {nb_dalles} dalles")

    elif args.zone_bbox:
        try:
            parts = [float(v.strip()) for v in args.zone_bbox.split(",")]
            bx1, by1, bx2, by2 = parts
        except (ValueError, IndexError):
            print("  Format BBox invalide. Exemple : --bbox 880000,6210000,1080000,6360000")
            sys.exit(1)
        dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
        surface_km2 = (bx2-bx1)/1000 * (by2-by1)/1000
        print(f"  BBox {PROVIDER.CRS_NATIF} : {bx1:.0f},{by1:.0f} â†’ {bx2:.0f},{by2:.0f}")
        print(f"  Surface : ~{surface_km2:.0f} kmÂ²  |  {len(dalles)} dalles")
        if args.zone_nom:
            nom_zone = normaliser_nom(args.zone_nom)
        elif args.oui:
            print("  ERREUR : --nom requis avec --bbox en mode --oui")
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
            print("  ERREUR : --nom requis avec --gps en mode --oui")
            sys.exit(1)
        else:
            nom_zone = normaliser_nom(input("  Nom du dossier de sortie : ").strip())
        if not nom_zone:
            sys.exit(1)
        # BUGFIX : la conversion GPSâ†’L93 doit se faire dans TOUS les cas, pas
        # uniquement quand --telechargement est absent. Sans cela, cx=cy=0.0
        # (init ligne 5056) et la grille calculÃ©e par calculer_grille() est
        # centrÃ©e sur l'origine Lambert 93 (au large du Maroc), produisant
        # une bbox Mercator vide et un MBTiles Ã  0 tuiles.
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
        print("  [2] CoordonnÃ©es GPS (lat, lon)")
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
            # BUGFIX : conversion GPSâ†’L93 dans tous les cas (cf. fix ci-dessus)
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
            # BUGFIX : geocodage villeâ†’L93 dans tous les cas (cf. fix ci-dessus)
            print(f"\n  Geocodage de '{ville_saisie}'...")
            cx, cy = geocoder_ville_l93(ville_saisie)
            if cx is None:
                sys.exit(1)

    # Rayon + grille (modes ville / gps / interactif â€” pas bbox, dept, france)
    if not args.zone_bbox and not args.zone_departement:
        if args.zone_rayon:
            rayon = args.zone_rayon
        else:
            rayon_str = input("  Rayon en km [10] : ").strip()
            try:
                rayon = float(rayon_str) if rayon_str else 10.0
            except ValueError:
                rayon = 10.0
        dalles, bbox = calculer_grille(cx, cy, rayon)

    # â”€â”€ DÃ©coupage Ã  priori : traitement sÃ©quentiel morceau par morceau â”€â”€â”€â”€â”€â”€â”€â”€
    _cols_pr = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr = getattr(args, "rows_decoupe", 0) or 0
    if _cols_pr > 0 and _rows_pr > 0:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            bbox[0], bbox[1], bbox[2], bbox[3],
            _cols_pr * _rows_pr, 0.0, unite_m=True)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR)
            manifeste = Manifeste(racine_pr / nom_zone / "manifeste.json")
            n_total   = len(sous_zones)
            nb_done   = sum(1 for z in sous_zones
                            if manifeste.deja_traite(f"{z[0]+1:03d}x{z[1]+1:03d}"))
            print(f"\n  â•â• DÃ©coupage Ã  priori : {mode_desc} â•â•")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Reprise : {nb_done}/{n_total} morceaux dÃ©jÃ  terminÃ©s")

            nb_ok = 0
            for i_z, (i_lat, i_lon, bx1_z, by1_z, bx2_z, by2_z) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} â€” dÃ©jÃ  terminÃ©")
                    nb_ok += 1
                    continue

                surface = (bx2_z-bx1_z)/1000 * (by2_z-by1_z)/1000
                print(f"\n  â”€â”€ Morceau {cle}  ({i_z+1}/{n_total})  {nom_z} â”€â”€")
                print(f"     BBox L93 : {bx1_z:.0f},{by1_z:.0f} â†’ "
                      f"{bx2_z:.0f},{by2_z:.0f}  (~{surface:.0f} kmÂ²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_lidar(args, (bx1_z, by1_z, bx2_z, by2_z),
                                        nom_z, nom_zone, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] âœ“ TerminÃ© en {_hms(int(time.time() - t0_z))}")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        # Si le chunk a produit un mbtiles vide OU aucun mbtiles
                        # (chunk en mer hors couverture IGN, ou bug Ã  diagnostiquer),
                        # on conserve les .tif intermÃ©diaires pour permettre
                        # l'inspection â€” sinon l'utilisateur perd le contexte.
                        _dossier_chunk = (
                            (Path(args.dossier).resolve() if args.dossier
                             else DOSSIER_TRAVAIL / "Projets" / nom_zone / LIDAR_SUBDIR)
                            / nom_z)
                        _mbts = list(_dossier_chunk.glob("*.mbtiles"))
                        _has_empty = (not _mbts) or any(
                            not _mbtiles_est_complete(mbt) for mbt in _mbts)
                        if _has_empty:
                            print(f"  [{cle}] mbtiles vide ou absent â€” nettoyage skipÃ© (intermÃ©diaires conservÃ©s pour inspection)")
                        else:
                            _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] âœ— ERREUR : {_e_z} â€” relancez pour reprendre")
                    raise

            print(f"\n  â•â• DÃ©coupage Ã  priori terminÃ© : {nb_ok}/{n_total} morceaux â•â•")
            return
        print("  DÃ©coupage Ã  priori : zone trop petite â†’ traitement unique")

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
        # Cancellation au passage entre 2 Ã©tapes : si l'utilisateur a fait
        # Ctrl+C pendant l'Ã©tape prÃ©cÃ©dente, on finit le print de bilan
        # mais on raise avant d'imprimer le marqueur de la suivante.
        # Le KeyboardInterrupt remonte au main() qui peut faire son cleanup.
        if etape_cur[0] > 0:
            elap  = int(time.time() - etape_t0[0])
            cumul = int(time.time() - t_debut)
            print(f"  âœ“ Ã‰tape {etape_cur[0]} terminÃ©e en {_hms(elap)}  (cumul {_hms(cumul)})")
        if _stop_event.is_set():
            raise KeyboardInterrupt("Interruption demandÃ©e â€” Ã©tapes restantes ignorÃ©es")
        etape_cur[0] += 1
        etape_t0[0] = time.time()
        print("ETAPE:" + str(etape_cur[0]) + "/" + str(etapes_total) + " " + nom, flush=True)

    if args.telechargement:
        print_etape("TÃ©lÃ©chargement dalles")
    if not _osm_seul and not (not args.telechargement and not args.ombrages):
        print(f"\n  Grille : {nb} dalle(s) de {DALLE_KM}x{DALLE_KM} km  (~{nb} kmÂ²)")
        print(f"  Espace : ~{taille_brut} Mo brut  /  ~{taille_comp} Mo compressÃ©")
    if args.telechargement_forcer:
        print(f"  Mise Ã  jour : dalles existantes re-tÃ©lÃ©chargÃ©es")
    if args.workers != NB_WORKERS:
        print(f"  Workers : {args.workers}")

    # Compression
    if args.telechargement_compresser:
        compresser = True
    elif args.oui or not args.telechargement:
        compresser = False  # pas de compression si tÃ©lÃ©chargement non demandÃ©
    else:
        print(f"\n  Compression du cache :")
        print(f"  [1] Non  -> rapide,  ~{taille_brut} Mo")
        print(f"  [2] Oui  -> lent,    ~{taille_comp} Mo")
        compresser = (input("  Choix [1] : ").strip() or "1") == "2"
    if args.telechargement:
        print(f"  -> {'Compression activÃ©e' if compresser else 'Stockage brut'}")

    if not args.oui and args.telechargement:
        if input(f"\n  Lancer le tÃ©lÃ©chargement ? [O/n] : ").strip().lower() == "n":
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
            print(f"  ERREUR : dossier dalles inaccessible : {dossier_dalles}")
            print(f"  ({_e_dd})")
            print(f"  VÃ©rifiez que le disque est connectÃ© et relancez.")
            sys.exit(1)
    if not _osm_seul:
        dossier_ville.mkdir(parents=True, exist_ok=True)
    print(f"\n  Racine  : {racine}")
    if not _osm_seul:
        print(f"  Dalles  : {dossier_dalles}")
        print(f"  Zone    : {dossier_ville}")

    # -------------------------------------------------------
    # Renommage dalles ancienne convention â†’ nouvelle
    # -------------------------------------------------------
    if getattr(args, 'renommer_dalles', False) and dossier_dalles.exists():
        renommes = 0; ignores = 0
        tous = _rglob_tif_robuste(dossier_dalles)
        print(f"  {len(tous)} fichiers .tif trouvÃ©s dans {dossier_dalles}")
        if tous:
            print(f"  Exemple : {tous[0].name}")
        for f in sorted(tous):
            m = re.match(
                r'LHD_FXX_(\d+)_(\d+)_(MNT_O_0M50_LAMB93.*)', f.name)
            if not m:
                continue
            x_old, y_old = int(m.group(1)), int(m.group(2))
            reste = m.group(3)
            # DÃ©tecter l'ancienne convention : x_old < 600 (max Lambert93/2000â‰ˆ600)
            # Dans la nouvelle convention x_old > 600 (coordonnÃ©es km rÃ©elles)
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
        print(f"  Renommage : {renommes} dalles renommÃ©es, {ignores} ignorÃ©es")

    # -------------------------------------------------------
    # Migration dalles Ã  plat â†’ sous-dossiers par colonne X
    # -------------------------------------------------------
    if getattr(args, 'migrer_dalles', False) and dossier_dalles.exists():
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]  # uniquement racine
        if not a_migrer:
            print("  Aucune dalle Ã  migrer (dossier racine dÃ©jÃ  vide ou structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} dalle(s) â†’ sous-dossiers par colonne X...")
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
                            time.sleep(0.2)  # attendre que l'AV relÃ¢che
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
            print(f"  Migration terminÃ©e : {migres} dalles dÃ©placÃ©es, {erreurs} erreurs.")

    # -------------------------------------------------------
    # Purge des dalles invalides (< 2 Mo = mer, erreurs)
    # -------------------------------------------------------
    if args.dalles_purger_invalides and dossier_dalles.exists():
        SEUIL_VALIDE = SEUIL_DALLE_VALIDE
        invalides = [f for f in _rglob_tif_robuste(dossier_dalles)
                     if f.stat().st_size < SEUIL_VALIDE]
        if invalides:
            print(f"\n  Purge invalides : {len(invalides)} dalle(s) < 2 Mo...")
            for f in invalides:
                f.unlink()
            print(f"  Purge terminÃ©e. {len(invalides)} fichiers supprimÃ©s.")
        else:
            print("  Aucune dalle invalide trouvÃ©e (toutes â‰¥ 50 Mo).")

    # -------------------------------------------------------
    # Purge des dalles hors zone courante
    # -------------------------------------------------------
    if args.dalles_purger_hors_zone and dossier_dalles.exists():
        # Source de vÃ©ritÃ© : dalles_zone.txt (gÃ©nÃ©rÃ© par le WFS)
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        if dalles_zone_txt.exists():
            noms_zone_purge = set(dalles_zone_txt.read_text(encoding="utf-8").splitlines())
            noms_zone_purge = {n.strip() for n in noms_zone_purge if n.strip()}
            print(f"  Purge hors-zone : rÃ©fÃ©rence {dalles_zone_txt.name}"
                  f" ({len(noms_zone_purge)} dalles zone)")
        else:
            print(f"  ERREUR purge-hors-zone : {dalles_zone_txt.name} introuvable.")
            print(f"  Relancez avec --telechargement pour reconstruire la liste.")
            sys.exit(1)
        toutes = _rglob_tif_robuste(dossier_dalles)
        hors_zone = [f for f in toutes if f.name not in noms_zone_purge]
        if hors_zone:
            taille_go = sum(f.stat().st_size for f in hors_zone) / 1e9
            print(f"\n  Purge hors-zone : {len(hors_zone)} dalle(s) â€” {taille_go:.1f} Go")
            if not args.oui:
                rep = input("  Confirmer la suppression ? [o/N] : ").strip().lower()
                if rep != "o":
                    print("  Purge annulÃ©e.")
                    hors_zone = []
            for f in hors_zone:
                f.unlink()
            if hors_zone:
                print(f"  {len(hors_zone)} dalles supprimÃ©es, {taille_go:.1f} Go libÃ©rÃ©s.")
        else:
            print("  Aucune dalle hors zone trouvÃ©e.")

    # -------------------------------------------------------
    # DÃ©couverte des dalles via le provider â€” source de vÃ©ritÃ© unifiÃ©e
    # -------------------------------------------------------
    # CalculÃ© une fois ici, utilisÃ© par la cache-check ET le download.
    # Pour FR : TMS + fallback grille â†’ dict {nom: url}.
    # Pour NL : index JSON kaartbladen â†’ dict {nom: url}.
    # Provider-agnostique : aucune hypothÃ¨se sur la gÃ©omÃ©trie des tuiles.
    _t_wgs = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
    _lon1, _lat1 = _t_wgs.transform(bbox[0], bbox[1])
    _lon2, _lat2 = _t_wgs.transform(bbox[2], bbox[3])
    bbox_wgs = (min(_lon1, _lon2) - 0.05, min(_lat1, _lat2) - 0.05,
                max(_lon1, _lon2) + 0.05, max(_lat1, _lat2) + 0.05)
    # Cache per-provider : schemas incompatibles (TMS dict vs GeoJSON, etc.).
    cache_discover = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
    dalles_dict = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover) or {}
    noms_attendus = set(dalles_dict.keys())

    # -------------------------------------------------------
    # DÃ©tecter si on peut sauter le tÃ©lÃ©chargement
    # -------------------------------------------------------
    sauter_telechargement = False

    # Si seul --osm est demandÃ© (pas --ignlidar, pas d'ombrages, pas de mbtiles LiDAR)
    # on peut passer directement Ã  la partie OSM sans vÃ©rifier les dalles
    if _osm_seul:
        sauter_telechargement = True

    # Tuiles seules (pas de tÃ©lÃ©chargement, pas d'ombrages) : pas besoin des dalles
    if not args.telechargement and not args.ombrages:
        sauter_telechargement = True

    if not sauter_telechargement and not args.telechargement:
        # --source .tif ou .mbtiles : pas besoin des dalles IGN
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff", ".mbtiles"):
            sauter_telechargement = True
        else:
            dalles_existantes = _rglob_tif_robuste(dossier_dalles) if dossier_dalles.exists() else []
            if not dalles_existantes:
                print("\n  ATTENTION : --telechargement absent mais aucune dalle trouvÃ©e.")
                print(f"  Dossier dalles : {dossier_dalles}")
                print("  Ajoutez --telechargement pour tÃ©lÃ©charger les dalles manquantes.")
                sys.exit(1)
            # VÃ©rification zone-spÃ©cifique : parmi les dalles du cache, combien
            # couvrent rÃ©ellement la zone demandÃ©e ? Le cache peut contenir des
            # dalles d'autres zones (autres tests prÃ©cÃ©dents). Si aucune dalle
            # ne couvre la zone, on plante avec un message clair plutÃ´t que de
            # laisser le pipeline continuer puis Ã©chouer plus loin.
            if noms_attendus:  # discover_dalles a retournÃ© une liste non-vide
                dalles_zone_cache = [d for d in dalles_existantes
                                     if d.name in noms_attendus
                                     and d.stat().st_size > SEUIL_DALLE_VALIDE]
                if not dalles_zone_cache:
                    print(f"\n  ATTENTION : {len(dalles_existantes)} dalle(s) dans le cache,")
                    print(f"              mais AUCUNE ne couvre la zone demandÃ©e.")
                    print(f"  Cache global : {dossier_dalles}")
                    libelle_zone = args.zone_ville or nom_zone
                    print(f"  Zone demandÃ©e : {len(noms_attendus)} dalle(s) autour de "
                          f"{libelle_zone}")
                    print(f"  Ajoutez --telechargement pour tÃ©lÃ©charger les dalles manquantes.")
                    sys.exit(1)
                print(f"\n  TÃ©lÃ©chargement ignorÃ© "
                      f"({len(dalles_zone_cache)}/{len(noms_attendus)} dalle(s) de la zone trouvÃ©es en cache)")
            else:
                # Provider sans index pour cette bbox (cas dÃ©gradÃ©) : juste compter
                print(f"\n  TÃ©lÃ©chargement ignorÃ© ({len(dalles_existantes)} dalle(s) en cache)")
            sauter_telechargement = True

    # -------------------------------------------------------
    # TÃ©lÃ©chargement + assemblage (pivotÃ© sur PROVIDER.discover_dalles)
    # -------------------------------------------------------
    if not sauter_telechargement:
        # dalles_dict a dÃ©jÃ  Ã©tÃ© calculÃ© plus haut via PROVIDER.discover_dalles.
        # Orchestration download + persistance via le helper provider-agnostique.
        _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args)

    # -------------------------------------------------------
    # Ombrages
    # -------------------------------------------------------
    TOUS_OMBRAGES = ["315", "045", "135", "225", "multi", "slope",
                     "svf", "svf100", "lrm", "rrim"]

    # Dalles disponibles pour les ombrages :
    # 1. Seulement les dalles de la zone courante (filtre par nom)
    # 2. Seulement les fichiers valides (â‰¥ 50 Mo)
    # Le dossier dalles est global â€” sans filtrage par zone, le VRT couvrirait
    # tous les dÃ©partements prÃ©sents et le hillshade serait Ã©norme ou en erreur.
    if dossier_dalles.exists():
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        noms_zone = set()  # initialisÃ© ici â€” peut rester vide en mode OSM seul
        if dalles_zone_txt.exists():
            # VÃ©rifier que la bbox en entÃªte correspond Ã  la zone courante
            _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
            _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
            _bbox_fichier  = _lignes[0].strip() if _lignes else ""
            if _bbox_fichier != _bbox_courante:
                print(f"  Zone modifiÃ©e â€” reconstruction {dalles_zone_txt.name} depuis le cache...")
                print(f"    Ancienne bbox : {_bbox_fichier}")
                print(f"    Nouvelle bbox : {_bbox_courante}")
                # Reconstruire depuis le cache disque sans retÃ©lÃ©charger.
                # noms_attendus vient de PROVIDER.discover_dalles (provider-agnostique).
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_attendus and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    dalles_zone_txt.write_text(
                        _bbox_courante + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  {dalles_zone_txt.name} reconstruit : {len(noms_zone)} dalle(s) en cache")
                else:
                    dalles_zone_txt.unlink(missing_ok=True)
                    print(f"  Aucune dalle en cache pour cette zone â€” utilisez --telechargement")
                    noms_zone = set()
            else:
                noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
                print(f"  Liste dalles zone : {dalles_zone_txt.name} ({len(noms_zone)} dalles)")
        elif not args.telechargement and noms_attendus:
            # Si seul --osm demandÃ©, pas besoin des dalles
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # on ne cherche pas les dalles
            else:
                # dalles_zone.txt absent mais liste attendue connue â†’ reconstruction
                # depuis le cache disque (la vÃ©rification en amont garantit qu'on
                # trouvera au moins une dalle).
                print(f"  Reconstruction de {dalles_zone_txt.name} depuis le cache disque...")
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_attendus and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
                    dalles_zone_txt.write_text(
                        _bbox_hdr + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  dalles_zone.txt reconstruit : {len(noms_zone)} dalle(s) trouvÃ©es sur disque")
                else:
                    print(f"  ERREUR : aucune dalle de la zone trouvÃ©e dans {dossier_dalles}")
                    print(f"  Relancez avec --telechargement pour tÃ©lÃ©charger les dalles.")
                    sys.exit(1)
        else:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # mode OSM seul â€” pas besoin de dalles
            else:
                print(f"\n  ERREUR : {dalles_zone_txt.name} introuvable dans {dossier_ville}/")
                print(f"  Ce fichier est crÃ©Ã© automatiquement lors du tÃ©lÃ©chargement.")
                print(f"  Relancez avec --telechargement pour le reconstruire.")
                print(f"  (Les dalles dÃ©jÃ  prÃ©sentes sur disque seront skippÃ©es, ~quelques secondes)")
                sys.exit(1)
        toutes_dalles    = sorted(_rglob_tif_robuste(dossier_dalles))
        dalles_zone      = [d for d in toutes_dalles if d.name in noms_zone]
        dalles_ombrages  = [d for d in dalles_zone   if d.stat().st_size > SEUIL_DALLE_VALIDE]
        nb_hors_zone     = len(toutes_dalles) - len(dalles_zone)
        nb_invalides     = len(dalles_zone)   - len(dalles_ombrages)
        if not _osm_seul:
            if nb_hors_zone:
                print(f"  {nb_hors_zone} dalle(s) hors zone ignorÃ©es (autres dÃ©partements)")
            if nb_invalides:
                print(f"  {nb_invalides} dalle(s) invalides ignorÃ©es (< 2 Mo â€” mer ou hors couverture)")
            print(f"  {len(dalles_ombrages)} dalle(s) retenues pour les ombrages")
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
            print("  ERREUR : rasterio absent â€” pip install rasterio")
        else:
            tifs_bruts = [
                t for t in dossier_ville.glob("*.tif")
                if not t.name.startswith("_")
                and not re.search(r'_tuilage_z\d+\.tif$', t.name)
            ]
            # Filtrer ceux non compressÃ©s (taille > seuil heuristique : >500 Mo)
            tifs_a_compresser = [t for t in tifs_bruts if t.stat().st_size > 500e6]
            if not tifs_a_compresser:
                print("  Aucun ombrage brut trouvÃ© (> 500 Mo) Ã  compresser.")
            else:
                print(f"  {len(tifs_a_compresser)} fichier(s) Ã  compresser :")
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
                                # pour borner la RAM (un ombrage 50000Ã—50000 px
                                # uint8 = 2.5 Go en mÃ©moire â€” trop gros).
                                for ji, window in src.block_windows(1):
                                    for b in range(1, src.count + 1):
                                        dst.write(src.read(b, window=window),
                                                  b, window=window)
                        elap = time.time() - t0_cmp
                        chemin_tmp.unlink(missing_ok=True)
                        taille_cmp = chemin_out.stat().st_size / 1e6
                        gain = int((1 - taille_cmp / taille_brut) * 100)
                        print("  " + chemin_out.name.ljust(56) +
                              str(round(taille_brut)).rjust(6) + " Mo -> " +
                              str(round(taille_cmp)).rjust(5) + " Mo  (-" +
                              str(gain) + "%)  " + _hms(elap))
                    except Exception as _e_cmp:
                        print(f"  ERREUR compression {chemin_out.name} : {_e_cmp}")
                        chemin_tmp.replace(chemin_out)

    if dalles_ombrages and args.ombrages:
        if "aucun" in args.ombrages:
            choix_ombrages = []
        elif "tous" in args.ombrages:
            choix_ombrages = TOUS_OMBRAGES
        else:
            choix_ombrages = args.ombrages
    elif dalles_ombrages and not args.ombrages and not args.oui:
        # Mode interactif â€” pas de --ombrages, pas de --oui
        print(f"\n  Ombrages Ã  gÃ©nÃ©rer :")
        print(f"  [1] Rapide     : multi + slope                                    (~1 min)")
        print(f"  [2] ArchÃ©o     : 315 + 045 + multi + slope                        (~2 min)")
        print(f"  [3] ArchÃ©o+SVF : multi + slope + SVF (20m) + SVF100 (100m)        (~35 min)")
        print(f"  [4] ArchÃ©o+LRM : multi + slope + LRM gaussien                     (~8 min)")
        print(f"  [5] ArchÃ©o+RRIM: multi + slope + RRIM (composite couleur)         (~25 min)")
        print(f"  [6] Complet    : 315 045 135 225 multi slope svf svf100 lrm rrim  (~80 min)")
        print(f"  [7] Aucun")
        print(f"  [8] Choix manuel  ex: multi slope svf rrim")
        print(f"  SVF/LRM/RRIM : numpy/scipy (scipy auto-installÃ© si absent)")
        rep = input("  Choix [1] : ").strip() or "1"
        if   rep == "1": choix_ombrages = ["multi", "slope"]
        elif rep == "2": choix_ombrages = ["315", "045", "multi", "slope"]
        elif rep == "3": choix_ombrages = ["multi", "slope", "svf", "svf100"]
        elif rep == "4": choix_ombrages = ["multi", "slope", "lrm"]
        elif rep == "5": choix_ombrages = ["multi", "slope", "rrim"]
        elif rep == "6": choix_ombrages = TOUS_OMBRAGES
        elif rep == "7": choix_ombrages = []
        elif rep == "8":
            saisie = input("  Types : ").strip().lower().split()
            choix_ombrages = [s for s in saisie if s in TOUS_OMBRAGES]
        else:             choix_ombrages = ["multi", "slope"]
    else:
        choix_ombrages = []  # --oui sans --ombrages â†’ pas d'ombrage

    if choix_ombrages:
        surface_km2 = len(dalles_ombrages)  # ~1 dalle = 1 kmÂ²
        print_etape("Ombrages " + ", ".join(choix_ombrages))
        print(f"  Ombrages : {', '.join(choix_ombrages)}")
        elev = args.ombrages_elevation if args.ombrages_elevation is not None else ELEVATION_SOLEIL
        print(f"  Angle solaire : {elev}Â°")
        print(f"  Surface : ~{surface_km2} kmÂ²  â€” DurÃ©e estimÃ©e :"
              f" {'5-10 min' if surface_km2 < 100 else '15-45 min' if surface_km2 < 500 else '1h+'}"
              f" (selon le type d'ombrage et la machine)", flush=True)
        generer_ombrages(dalles_ombrages, dossier_ville, choix_ombrages,
                         elevation_soleil=elev, nom_zone=nom_zone,
                         ecraser_ombrages=args.ombrages_ecraser,
                         use_sweep=args.sweep_horizon)

    # â”€â”€ MBTiles + RMAP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.mbtiles or args.rmap or args.sqlitedb:
        # Source : --source .tif ou ombrages gÃ©nÃ©rÃ©s dans dossier_ville
        if args.source and Path(args.source).suffix.lower() in (".tif", ".tiff"):
            # --source explicite
            _tif_src = Path(args.source).resolve()
            print_etape(f"{'RMAP' if args.rmap and not args.mbtiles else 'MBTiles'} depuis {_tif_src.name}")
            print(f"  Source : {_tif_src}")
            print(f"  Zone   : bbox L93 {bbox[0]:.0f},{bbox[1]:.0f} â†’ {bbox[2]:.0f},{bbox[3]:.0f}")
            # Nom basÃ© sur nom_zone + type d'ombrage dÃ©tectÃ© dans le nom du fichier
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
            _nom_base = f"{nom_zone}_{_sfx}"   # sans zoom â€” ajoutÃ© par generer_mbtiles_lidar
            _nom_mbt  = f"{_nom_base}_z{args.zoom_min}-{args.zoom_max}"
            # GÃ©nÃ©rer MBTiles si demandÃ© explicitement, ou si nÃ©cessaire pour RMAP/SQLiteDB
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
                print(f"  MBTiles existant : {_mbt_path.name} â€” dÃ©coupage/conversion directe")
                _mbt_out = _mbt_path
            _convertir_formats(_mbt_out, args, mbtiles_neuf=_mbt_requis)
        else:
            # Ombrages prÃ©sents dans dossier_ville
            # Exclure les fichiers de cache de tuilage (`<nom>_tuilage_z<N>.tif`)
            # qui sont produits par generer_mbtiles_lidar comme cache du warp
            # rasterio. Sans ce filtre, le loop suivant tente de rÃ©gÃ©nÃ©rer un
            # MBTiles Ã  partir du cache, qui devient sa propre source â€” boucle
            # infinie en pratique (test_refactor_svf_ombrage_tuilage_z16_tuilage_z16.tifâ€¦).
            ombrages_tifs = [
                t for t in sorted(dossier_ville.glob("*.tif"))
                if not t.name.startswith("_")
                and not re.search(r'_tuilage_z\d+\.tif$', t.name)
            ]
            if ombrages_tifs:
                print_etape("MBTiles")
                _LABELS = {
                    "hillshade_315": "Hillshade 315Â°",
                    "hillshade_045": "Hillshade 045Â°",
                    "hillshade_135": "Hillshade 135Â°",
                    "hillshade_225": "Hillshade 225Â°",
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
                    # Retirer le suffixe de cache _tuilage_z* si prÃ©sent
                    stem = re.sub(r'_tuilage_z\d+$', '', stem)
                    suffix = stem[len(nom_zone) + 1:] if stem.startswith(nom_zone + "_") else stem
                    nom_base = f"{nom_zone}_{suffix}"
                    _mbt_path2 = dossier_ville / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles"
                    _ecraser_l = args.tuiles_ecraser
                    if _mbt_path2.exists() and not _ecraser_l:
                        print(f"  MBTiles existant : {_mbt_path2.name} â€” dÃ©coupage/conversion directe")
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
                print("  Aucun ombrage trouvÃ© pour MBTiles (gÃ©nÃ©rez d'abord --ombrages)")

    # â”€â”€ Carte OSM vectorielle de superposition â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dossier_osm = None   # dÃ©fini si on arrive jusqu'au generer_carte_osm
    if args.osm:
        print_etape("Carte OSM vectorielle")

        # Table dÃ©partement â†’ URL Geofabrik : voir _GEOFABRIK au niveau module

        # RÃ©soudre le PBF source
        pbf = None
        if args.source and Path(args.source).suffix.lower() in (".pbf", ".osm"):
            pbf = Path(args.source)
            if not pbf.exists():
                print(f"  ERREUR : fichier PBF introuvable : {pbf}")
                pbf = None
        else:
            # TÃ©lÃ©chargement automatique â€” dÃ©tecter le dÃ©partement depuis le centre
            num_dep = getattr(args, "zone_departement", None)

            if not num_dep:
                # Modes ville/gps/bbox : cx, cy sont en Lambert 93
                # â†’ convertir en WGS84 â†’ requÃªte geo.api.gouv.fr reverse
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
                        print(f"  DÃ©partement dÃ©tectÃ© : {num_dep}", flush=True)
                except Exception as e_rev:
                    print(f"  GÃ©ocodage inverse Ã©chouÃ© ({e_rev})")

            region_slug = _GEOFABRIK.get(num_dep) if num_dep else None
            if not region_slug:
                print(f"  DÃ©partement {num_dep} non trouvÃ© dans la table Geofabrik.")
                print(f"  Repli sur le PBF national France (~4 Go).")
                url_pbf = f"{_GEOFABRIK_BASE_URL_ROOT}/france-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / "france-latest.osm.pbf"
            else:
                url_pbf = f"{_GEOFABRIK_BASE_URL}/{region_slug}-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / f"{region_slug}-latest.osm.pbf"

            # TÃ©lÃ©chargement PBF commun (national ou rÃ©gional)
            _SEUIL_PBF = 1_000_000  # 1 Mo minimum â€” PBF vide ou tronquÃ© â†’ re-tÃ©lÃ©charger
            if pbf.exists() and pbf.stat().st_size >= _SEUIL_PBF:
                print(f"  PBF existant : {pbf.name}  "
                      f"({pbf.stat().st_size/1e9:.1f} Go)")
            else:
                if pbf.exists():
                    print(f"  PBF tronquÃ© ({pbf.stat().st_size} octets) â€” re-tÃ©lÃ©chargement.")
                    pbf.unlink()
                _log_req(str(url_pbf), 'Geofabrik')
                print(f"  TÃ©lÃ©chargement {url_pbf}...")
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
                                    line = f"  {mb:.0f} / {tot:.0f} Mo  {pct}%"
                                    # \r sur le terminal, nouvelle ligne dans le log
                                    sys.stdout.write(f"\r{line}")
                                    sys.stdout.flush()
                    # Effacer la ligne de progression
                    sys.stdout.write("\r" + " " * 40 + "\r")
                    print(f"  Telecharge : {pbf.name}  "
                          f"({taille_dl/1e6:.0f} Mo)  "
                          f"{_hms(time.time()-t0_dl)}")
                    # VÃ©rifier que le fichier n'est pas vide/tronquÃ©
                    if taille_dl < _SEUIL_PBF:
                        print(f"  ERREUR : PBF tÃ©lÃ©chargÃ© trop petit ({taille_dl} octets)"
                              f" â€” tÃ©lÃ©chargement Ã©chouÃ© (rÃ©seau ? accÃ¨s Geofabrik ?).")
                        pbf.unlink(missing_ok=True)
                        pbf = None
                except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e_dl:
                    print(f"\n  ERREUR tÃ©lÃ©chargement PBF ({type(e_dl).__name__}) : {e_dl}")
                    pbf.unlink(missing_ok=True)
                    pbf = None

        if pbf and pbf.exists():
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
                # Dossier dÃ©diÃ© OSM â€” pas le dossier LiDAR
                dossier_osm = (Path(args.dossier).resolve() if args.dossier
                               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "osm_vecteur")
                dossier_osm.mkdir(parents=True, exist_ok=True)
                # Liste des formats GeoJSON demandÃ©s (parmi "gz" et "geojson")
                _gj_formats = [f for f in ("gz", "geojson") if f in args.formats_fichier]
                generer_carte_osm(bbox_wgs, dossier_osm, nom_zone, pbf,
                                  osm_tags=(args.couche
                                            if getattr(args, 'couche', None)
                                            else getattr(args, 'osm_tags', None)),
                                  export_geojson=bool(_gj_formats),
                                  ecraser_tuiles=args.tuiles_ecraser,
                                  skip_bbox=False,
                                  geojson_formats=_gj_formats or ["gz"])

    if etape_cur[0] > 0:
        elap  = int(time.time() - etape_t0[0])
        cumul = int(time.time() - t_debut)
        print(f"  âœ“ Ã‰tape {etape_cur[0]} terminÃ©e en {_hms(elap)}  (cumul {_hms(cumul)})")
    total = int(time.time() - t_debut)
    m, s  = divmod(total, 60)
    print(f"\n  TerminÃ© ! Dossier : {dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville}")
    print(f"  DurÃ©e totale : {m}m{s:02d}s")
    dossier_res = str(dossier_osm if (_osm_seul and dossier_osm is not None) else dossier_ville)
    _historique_depuis_argv(total, dossier_res)


# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================


# ============================================================
# DÃ‰COUPAGE Ã€ PRIORI â€” FONCTIONS UTILITAIRES
# ============================================================


def _calculer_sous_zones_priori(x1, y1, x2, y2, n_morceaux, rayon_km, unite_m=True):
    """
    Divise une bbox en sous-zones pour le dÃ©coupage Ã  priori.

    unite_m=True  : bbox en mÃ¨tres  (Lambert 93)  â€” retourne (i_lat, i_lon, x1, y1, x2, y2)
    unite_m=False : bbox en degrÃ©s  (WGS84)        â€” retourne (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n)

    n_morceaux prime sur rayon_km.
    """
    largeur = x2 - x1
    hauteur = y2 - y1

    if n_morceaux > 1:
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
        mode_desc = f"{n_morceaux} morceaux ({n_rows}Ã—{n_cols})"
    elif rayon_km > 0:
        if unite_m:
            dy = dx = rayon_km * 1000
        else:
            lat_c = (y1 + y2) / 2
            dy = rayon_km / 111.0
            dx = rayon_km / (111.0 * math.cos(math.radians(lat_c)))
        n_rows = max(1, int(math.ceil(hauteur / dy)))
        n_cols = max(1, int(math.ceil(largeur / dx)))
        mode_desc = f"~{rayon_km:.0f} km/morceau ({n_rows}Ã—{n_cols})"
    else:
        n_rows = n_cols = 1
        dx = largeur
        dy = hauteur
        mode_desc = "1 morceau (zone entiÃ¨re)"

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
    """Retourne la liste des Path des dalles valides prÃ©sentes sur disque
    pour cette zone. Source de vÃ©ritÃ© : dalles_zone.txt si bbox match,
    sinon le set `noms_attendus` (issu de PROVIDER.discover_dalles).

    noms_attendus : iterable de noms de dalles attendus pour la zone
                    (typiquement les keys du dict retournÃ© par discover_dalles).
    """
    noms_zone = set()
    dalles_zone_txt = dossier_ville / "dalles_zone.txt"
    if dalles_zone_txt.exists():
        _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
        _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
        if _lignes and _lignes[0].strip() == _bbox_courante:
            noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
    if not noms_zone:
        noms_attendus_set = set(noms_attendus)
        toutes = _rglob_tif_robuste(dossier_dalles)
        noms_zone = {d.name for d in toutes
                     if d.name in noms_attendus_set and d.stat().st_size > SEUIL_DALLE_VALIDE}
    toutes_dalles   = sorted(_rglob_tif_robuste(dossier_dalles))
    dalles_zone     = [d for d in toutes_dalles if d.name in noms_zone]
    dalles_ombrages = [d for d in dalles_zone   if d.stat().st_size > SEUIL_DALLE_VALIDE]
    return dalles_ombrages


def _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args):
    """TÃ©lÃ©charge en parallÃ¨le les dalles d'un dict {nom: url} (issu de
    PROVIDER.discover_dalles). Pure orchestration : la dÃ©couverte et le
    fallback grille sont entiÃ¨rement dÃ©lÃ©guÃ©s au provider.

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
        barre = "â–ˆ" * bars + "â–‘" * (largeur - bars)
        print(f"\r  Dalles LIDAR [{barre}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
              end="", flush=True)

    if a_telecharger:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
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
        print(f"  TÃ©lÃ©chargÃ©es : {ok}  Cache : {skip}  Absent : {absent}  Erreurs : {erreur}")

    # Persister dalles_zone.txt â€” utile pour --dalles-purger-hors-zone et la
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

    # Enregistrer toutes les dalles utilisÃ©es par ce chunk dans le manifest
    # pour permettre --nettoyage de les supprimer en fin de chunk. Le
    # tÃ©lÃ©chargement parallÃ¨le ne propage pas _manifest_ctx (threading.local)
    # â†’ registration explicite depuis le main thread.
    for _nom in noms_persistance:
        _cd = chemin_dalle(dossier_dalles, _nom)
        if _cd.exists():
            _creer_fichier(_cd)


def _mbtiles_est_complete(mbt_path):
    """VÃ©rification silencieuse : True si le mbtiles existe, est un SQLite
    lisible et contient >0 tuiles. Aucun side-effect, aucun print â€” utilisable
    pour les checks de garde-fou dans les boucles de reprise (chunk-level
    manifeste skip), oÃ¹ on veut savoir si un mbtiles "supposÃ© fait" est
    rÃ©ellement utilisable."""
    if not mbt_path.exists():
        return False
    try:
        with sqlite3.connect(f"file:{mbt_path}?mode=ro", uri=True) as _c:
            return _c.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] > 0
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return False


def _mbtiles_a_regenerer(mbt_path, ecraser):
    """DÃ©termine si un mbtiles doit Ãªtre (re)gÃ©nÃ©rÃ©.

    Retourne True si :
    - le fichier n'existe pas,
    - --tuiles-ecraser est passÃ©,
    - le fichier existe mais contient 0 tuiles (artefact d'un run interrompu),
    - le fichier existe mais est corrompu (SQLite illisible).

    Sinon retourne False (mbtiles valide, on le rÃ©utilise). Logue la raison
    de la rÃ©gÃ©nÃ©ration pour Ã©viter les disparitions silencieuses.
    """
    if not mbt_path.exists() or ecraser:
        return True
    # Distinguer fichier illisible vs vide pour un log clair
    try:
        with sqlite3.connect(f"file:{mbt_path}?mode=ro", uri=True) as _c:
            _n = _c.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as _e:
        print(f"  {mbt_path.name} â†’ SQLite illisible ({type(_e).__name__}), rÃ©gÃ©nÃ©ration", flush=True)
        return True
    if _n == 0:
        print(f"  {mbt_path.name} â†’ existant mais vide (0 tuiles), rÃ©gÃ©nÃ©ration", flush=True)
        return True
    return False


def _traiter_bbox_lidar(args, bbox_l93, nom_z, nom_zone_base, manifeste, cle):
    """
    Traite un morceau LiDAR directement en Python (sans subprocess).
    AppelÃ© par la boucle Ã  priori dans main().
    nom_zone_base : nom du projet parent (ex: gareoult2).
    nom_z         : nom du morceau   (ex: gareoult2_001x001).
    """
    bx1, by1, bx2, by2 = bbox_l93

    # Sauvegarder / restaurer les args modifiÃ©s temporairement
    _bbox_orig = args.zone_bbox
    _nom_orig  = args.zone_nom
    args.zone_bbox = f"{bx1:.2f},{by1:.2f},{bx2:.2f},{by2:.2f}"
    args.zone_nom  = nom_z

    try:
        with _contexte_manifeste(manifeste, cle):
            bbox = (bx1, by1, bx2, by2)
            # Structure : <racine>/<nom_zone_base>/ign_lidar/<nom_z>/
            # (tous les morceaux sont sous-dossiers du mÃªme projet parent)
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / LIDAR_SUBDIR)
            racine = racine_base
            dossier_dalles = (Path(args.dossier_dalles).resolve() if args.dossier_dalles
                              else DOSSIER_TRAVAIL / "cache" / LIDAR_SUBDIR)
            dossier_ville = racine / nom_z
            dossier_ville.mkdir(parents=True, exist_ok=True)
            dossier_dalles.mkdir(parents=True, exist_ok=True)

            # DÃ©couverte des dalles via le provider â€” retourne {nom: url} en
            # combinant index officiel (TMS pour FR, JSON pour NL, etc.) et
            # Ã©ventuel fallback grille interne au provider. Le pipeline reste
            # provider-agnostique : il ne suppose ni grille (x_km, y_km) ni
            # protocole d'accÃ¨s particulier.
            _t = _get_transformer(PROVIDER.CRS_NATIF, "EPSG:4326")
            _lon1, _lat1 = _t.transform(bx1, by1)
            _lon2, _lat2 = _t.transform(bx2, by2)
            bbox_wgs = (min(_lon1, _lon2) - 0.05, min(_lat1, _lat2) - 0.05,
                        max(_lon1, _lon2) + 0.05, max(_lat1, _lat2) + 0.05)
            cache_discover = DOSSIER_TRAVAIL / "cache" / f"discover_{PROVIDER.CODE}.json"
            dalles_dict = PROVIDER.discover_dalles(bbox_wgs, bbox, cache_discover) or {}

            if args.telechargement:
                _telecharger_dalles_zone(dalles_dict, bbox, dossier_dalles, dossier_ville, args)

            if args.ombrages:
                TOUS = ["315","045","135","225","multi","slope","svf","svf100","lrm","rrim"]
                choix = (TOUS if "tous" in args.ombrages
                         else [] if "aucun" in args.ombrages
                         else args.ombrages)
                if choix:
                    dalles_ombrages = _lister_dalles_zone(dalles_dict.keys(), dossier_dalles,
                                                          dossier_ville, bbox)
                    elev = (args.ombrages_elevation if args.ombrages_elevation is not None
                            else ELEVATION_SOLEIL)
                    generer_ombrages(dalles_ombrages, dossier_ville, choix,
                                     elevation_soleil=elev, nom_zone=nom_z,
                                     ecraser_ombrages=args.ombrages_ecraser,
                                     use_sweep=args.sweep_horizon)

            if args.mbtiles or args.rmap or args.sqlitedb:
                # Filtre identique Ã  la fonction main : exclure les caches de
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
    AppelÃ© par la boucle Ã  priori dans main_wmts().
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
            # Structure : <racine>/<nom_zone_base>/ign_raster/<nom_z>/
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / "ign_raster")
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
    DÃ©coupe un MBTiles source en sous-MBTiles.

    Modes (par ordre de prioritÃ©) :
      - n_cols > 0 et n_rows > 0 : grille explicite colsÃ—rows (depuis la GUI).
      - n_morceaux > 1            : N morceaux, grille auto la plus carrÃ©e.
      - rayon_km  > 0             : carrÃ©s de ~rayon_km km.
      - sinon                     : retourne [src_mbtiles] sans dÃ©coupe.

    Nommage des sorties : {stem}_{ligne:03d}x{col:03d}.mbtiles
    Retourne la liste des Path crÃ©Ã©s.
    """
    import sqlite3 as _sq

    if n_cols > 0 and n_rows > 0:
        # Grille explicite â€” on force n_morceaux cohÃ©rent pour la suite
        n_morceaux = n_cols * n_rows
    if n_morceaux <= 1 and rayon_km <= 0:
        return [src_mbtiles]

    if not src_mbtiles.exists():
        print(f"  ERREUR dÃ©coupage : {src_mbtiles.name} introuvable")
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
            print(f"  ERREUR : MBTiles vide")
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

    # â”€â”€ Calcul de la grille via la fonction unifiÃ©e â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if n_cols > 0 and n_rows > 0:
        # Grille explicite colsÃ—rows
        r_lat = (lat1 - lat0) / n_rows
        r_lon = (lon1 - lon0) / n_cols
        r_lat_km = r_lat * 111.0
        r_lon_km = r_lon * 111.0 * math.cos(math.radians(lat_c))
        mode_desc = (f"{n_rows}Ã—{n_cols} grille"
                     f" (~{r_lat_km:.0f}Ã—{r_lon_km:.0f} km/morceau)")
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
        print(f"  DÃ©coupage : zone trop petite â†’ fichier unique")
        con.close()
        return [src_mbtiles]

    print(f"  DÃ©coupage : {mode_desc}")

    # Nom de base : garder le suffixe _z{min}-{max} pour que les morceaux l'incluent
    stem_base = src_mbtiles.stem  # ex: 83_multi_ombrage_z8-18

    # Compter lignes/colonnes pour le padding
    n_lats = i_lat
    n_lons = i_lon
    pad = max(3, len(str(max(n_lats, n_lons))))

    sorties = []

    for i_lat, i_lon, lon_w, lat_s, lon_e, lat_n in sous_zones:
        sfx   = f"_{(i_lat+1):0{pad}d}x{(i_lon+1):0{pad}d}"
        nom_z    = f"{stem_base}{sfx}"
        chemin_z = out_dir / f"{nom_z}.mbtiles"

        if chemin_z.exists():
            if not ecraser:
                print(f"  Morceau existant : {chemin_z.name} â€” ignorÃ©")
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

        # Copier les tuiles dans la bbox
        n_tuiles = 0
        batch    = []
        BATCH    = 500
        for z in range(zoom_min, zoom_max + 1):
            n  = 2 ** z
            # bbox WGS84 â†’ colonnes/lignes XYZ
            x0 = int((lon_w + 180) / 360 * n)
            x1 = int((lon_e + 180) / 360 * n)
            lat_n_r = math.radians(lat_n)
            lat_s_r = math.radians(lat_s)
            y0 = int((1 - math.log(math.tan(lat_n_r) + 1/math.cos(lat_n_r))/math.pi) / 2 * n)
            y1 = int((1 - math.log(math.tan(lat_s_r) + 1/math.cos(lat_s_r))/math.pi) / 2 * n)
            # TMS : tile_row = n-1-y_xyz
            row0 = n - 1 - y1   # lat_s â†’ y_xyz max â†’ tms min
            row1 = n - 1 - y0   # lat_n â†’ y_xyz min â†’ tms max
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
            print(f"  Sous-zone [{i_lat},{i_lon}] : vide â€” ignorÃ©e")
            continue

        print(f"  Sous-zone [{i_lat},{i_lon}] : {n_tuiles:,} tuiles â†’ {chemin_z.name}")
        sorties.append(chemin_z)

    con.close()
    return sorties


def _convertir_un_mbtiles(sf, args, mbtiles_neuf=True):
    """GÃ©nÃ¨re RMAP/SQLiteDB depuis un MBTiles.

    mbtiles_neuf=True : MBTiles fraÃ®chement gÃ©nÃ©rÃ© dans cette exÃ©cution.
        S'il n'a pas Ã©tÃ© demandÃ© via --formats-fichier, il est traitÃ© comme
        intermÃ©diaire et supprimÃ© aprÃ¨s conversion.
    mbtiles_neuf=False : MBTiles prÃ©existant sur disque (run prÃ©cÃ©dent ou
        copiÃ© manuellement). JAMAIS supprimÃ© â€” on respecte le travail de
        l'utilisateur, mÃªme si seul --rmap/--sqlitedb a Ã©tÃ© demandÃ©.
    """
    if args.rmap:     generer_rmap_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if args.sqlitedb: generer_sqlitedb_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if mbtiles_neuf and not args.mbtiles and sf.exists():
        sf.unlink()
        print(f"  MBTiles supprimÃ© : {sf.name}")


def _convertir_formats(mbt_out, args, decoupe_sortie=True, mbtiles_neuf=True):
    """
    Applique le dÃ©coupage (grille colsÃ—rows ou rayon_decoupe) puis gÃ©nÃ¨re
    RMAP/SQLiteDB pour chaque fichier rÃ©sultant.
    Supprime le MBTiles source uniquement s'il a Ã©tÃ© gÃ©nÃ©rÃ© dans cette
    exÃ©cution (mbtiles_neuf=True) ET non demandÃ© via --formats-fichier.
    decoupe_sortie=False â†’ saute le dÃ©coupage (mode morceau Ã  priori).
    """
    if not mbt_out:
        return

    r_dec  = getattr(args, "rayon_decoupe", 0.0)
    n_cols = getattr(args, "cols_decoupe",  0)
    n_rows = getattr(args, "rows_decoupe",  0)

    # En mode morceau Ã  priori : pas de re-dÃ©coupage
    if not decoupe_sortie:
        _convertir_un_mbtiles(mbt_out, args, mbtiles_neuf=mbtiles_neuf)
        return

    if n_cols > 0 and n_rows > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, n_cols=n_cols, n_rows=n_rows,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            # DÃ©coupage effectif : la source globale n'est gardÃ©e que si l'utilisateur
            # l'a demandÃ©e OU si elle prÃ©existait. Les sous-fichiers, eux, sont
            # toujours frais (sortie du dÃ©coupage).
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  MBTiles source supprimÃ© : {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args, mbtiles_neuf=True)
    elif r_dec > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, rayon_km=r_dec,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  MBTiles source supprimÃ© : {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args, mbtiles_neuf=True)
    else:
        # Pas de dÃ©coupage : on convertit directement le fichier passÃ©
        _convertir_un_mbtiles(mbt_out, args, mbtiles_neuf=mbtiles_neuf)


def _ajouter_args_zone(parser, *, rayon_default, bbox_metavar, bbox_help=None,
                        avec_dossier=False, avec_help_full=False):
    """Ajoute les flags --zone-{ville,gps,bbox,departement,rayon,nom}
    au parser fourni, en factorisant la duplication entre main(),
    main_wmts(), main_wfs(). Les divergences rÃ©elles sont :

    - rayon_default : main() utilisait None (rÃ©solu en 10 plus tard),
      main_wmts/wfs utilisent 10.0 dÃ¨s le parser.
    - bbox_metavar  : main() = "X1,Y1,X2,Y2" Lambert 93 en mÃ¨tres ;
      main_wmts/wfs = "W,S,E,N" WGS84 en degrÃ©s.
    - bbox_help     : help textuel propre Ã  chaque mode.
    - avec_dossier  : si True, ajoute aussi --dossier (uniquement pour main()
      qui le mÃ©lange avec --dossier-dalles ; les autres l'ajoutent Ã  part).
    - avec_help_full : si True, help dÃ©taillÃ© (mode CLI top-level main()).

    Retourne le mutually exclusive group, au cas oÃ¹ l'appelant veut y ajouter
    d'autres flags.
    """
    loc = parser.add_mutually_exclusive_group()
    if avec_help_full:
        loc.add_argument("--zone-ville",  metavar="NOM",
                         help="Nom de la ville (gÃ©ocodage Nominatim)")
        loc.add_argument("--zone-gps",    metavar="LAT,LON",
                         help="CoordonnÃ©es GPS ex: 43.3156,6.0423")
        loc.add_argument("--zone-bbox",   metavar=bbox_metavar,
                         help=bbox_help or "")
        loc.add_argument("--zone-departement", metavar="NUM",
                         help="NumÃ©ro de dÃ©partement ex: 83, 2A, 971. "
                              "RÃ©cupÃ¨re automatiquement la bbox depuis geo.api.gouv.fr. "
                              "Le nom du dossier est dÃ©fini automatiquement (ex: var_83).")
    else:
        loc.add_argument("--zone-ville",       metavar="NOM")
        loc.add_argument("--zone-gps",         metavar="LAT,LON")
        if bbox_help:
            loc.add_argument("--zone-bbox",    metavar=bbox_metavar, help=bbox_help)
        else:
            loc.add_argument("--zone-bbox",    metavar=bbox_metavar)
        loc.add_argument("--zone-departement", metavar="NUM")

    parser.add_argument("--zone-rayon", type=float, default=rayon_default,
                        metavar="KM",
                        help=f"Rayon en km autour du point "
                             f"(dÃ©faut: {rayon_default if rayon_default is not None else 10})")
    parser.add_argument("--zone-nom", metavar="NOM", default=None,
                        help="Nom du dossier de sortie pour la zone traitÃ©e. "
                             "Obligatoire pour --zone-gps et --zone-bbox.")
    if avec_dossier:
        parser.add_argument("--dossier", metavar="CHEMIN", default=None,
                            help="Dossier racine de sortie.")
    return loc


def _resoudre_zone_wgs84(args):
    """
    RÃ©sout la zone gÃ©ographique depuis les arguments CLI â†’ bbox WGS84 + nom_zone.
    Commun Ã  main_wmts() et main_wfs().
    Retourne (lon_min, lat_min, lon_max, lat_max, nom_zone).
    """
    lat_min = lon_min = lat_max = lon_max = None
    # Normalisation systÃ©matique dÃ¨s l'entrÃ©e : Ã©limine les diffÃ©rences
    # de casse et d'accentuation entre pipelines (--ignraster, --ignvecteur,
    # --fusionner) quel que soit ce que l'utilisateur a saisi.
    _zone_nom_raw = getattr(args, 'zone_nom', None)
    nom_zone = normaliser_nom(_zone_nom_raw) if _zone_nom_raw else None

    if args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        if not nom_zone:
            nom_zone = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        # geocoder_departement retourne du Lambert 93 â€” reconvertir en WGS84 pour le WFS
        lon_min, lat_min = _lamb93_to_wgs84_safe(bx1, by1)
        lon_max, lat_max = _lamb93_to_wgs84_safe(bx2, by2)

    elif args.zone_bbox:
        try:
            parts = [float(v.strip()) for v in args.zone_bbox.split(",")]
            lon_min, lat_min, lon_max, lat_max = parts
        except (ValueError, IndexError):
            print("  Format bbox invalide. Exemple : --zone-bbox 5.9,43.1,6.6,43.8")
            sys.exit(1)
        if not nom_zone:
            if getattr(args, 'oui', False):
                print("  ERREUR : --zone-nom requis avec --zone-bbox en mode --oui")
                sys.exit(1)
            nom_zone = normaliser_nom(input("  Nom de la zone : ").strip())

    elif args.zone_gps:
        try:
            parts = [p.strip() for p in args.zone_gps.replace(";", ",").split(",")]
            lat_c, lon_c = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            print("  Format GPS invalide. Exemple : --zone-gps 43.3156,6.0423")
            sys.exit(1)
        if not nom_zone:
            if getattr(args, 'oui', False):
                print("  ERREUR : --zone-nom requis avec --zone-gps en mode --oui")
                sys.exit(1)
            nom_zone = normaliser_nom(input("  Nom de la zone : ").strip())
        r     = args.zone_rayon / 111.0
        r_lon = args.zone_rayon / (111.0 * math.cos(math.radians(lat_c)))
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    elif args.zone_ville:
        nom_zone = nom_zone or normaliser_nom(args.zone_ville)
        print(f"  GÃ©ocodage de '{args.zone_ville}'...")
        lat_c, lon_c = geocoder_ville_wgs84(args.zone_ville)
        if lat_c is None:
            sys.exit(1)
        r     = args.zone_rayon / 111.0
        r_lon = args.zone_rayon / (111.0 * math.cos(math.radians(lat_c)))
        lat_min, lat_max = lat_c - r,     lat_c + r
        lon_min, lon_max = lon_c - r_lon, lon_c + r_lon

    else:
        if getattr(args, 'oui', False):
            print("  ERREUR : une option de zone est requise en mode --oui")
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
    Mode --decouper : dÃ©coupe a posteriori un MBTiles existant.
    Usage : lidar2map.py --decouper --source fichier.mbtiles
            [--cols C --rows R | --rayon-decoupe KM]
            [--formats-fichier mbtiles rmap sqlitedb]
            [--tuiles-ecraser]
    """
    import argparse
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --decouper",
        description="DÃ©coupage a posteriori d'un MBTiles existant.")
    parser.add_argument("--decouper", action="store_true")
    parser.add_argument("--source", required=True, metavar="CHEMIN",
                        help="Fichier .mbtiles source Ã  dÃ©couper.")
    parser.add_argument("--cols", type=int, default=0, metavar="N",
                        help="Nombre de colonnes de la grille (Est-Ouest).")
    parser.add_argument("--rows", type=int, default=0, metavar="N",
                        help="Nombre de lignes de la grille (Nord-Sud).")
    parser.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                        dest="rayon_decoupe", help="DÃ©coupe en carrÃ©s de ~KM km.")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles", "rmap", "sqlitedb"], default=["mbtiles"],
                        metavar="FMT")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser")
    parser.add_argument("--oui", action="store_true")
    args = parser.parse_args()
    _valider_zooms(args, parser)
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff

    src = Path(args.source)
    if not src.exists():
        print(f"  ERREUR : fichier introuvable : {src}"); sys.exit(1)
    if src.suffix.lower() != ".mbtiles":
        print(f"  ERREUR : --source attend un .mbtiles (reÃ§u : {src.suffix})"); sys.exit(1)

    print("=" * 55)
    print("  DÃ©coupage raster MBTiles")
    print("=" * 55)
    print(f"  Source  : {src}")
    print(f"  Formats : {' '.join(_ff)}")
    if args.cols > 0 and args.rows > 0:
        print(f"  Grille  : {args.cols} cols Ã— {args.rows} lignes")
    elif args.rayon_decoupe:
        print(f"  Rayon   : {args.rayon_decoupe} km/morceau")

    sorties = decouper_mbtiles(src, rayon_km=args.rayon_decoupe,
                               n_cols=args.cols, n_rows=args.rows,
                               ecraser=args.tuiles_ecraser)
    for sf in sorties:
        if args.rmap:     generer_rmap_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
        if args.sqlitedb: generer_sqlitedb_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
        if not args.mbtiles and sf != src and sf.exists():
            sf.unlink()
    print("\n  DÃ©coupage terminÃ©.")


def main_wmts():
    import argparse
    t_debut = time.time()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python lidar2map.py --ignraster --zone-ville gareoult --zoom-min 12 --zoom-max 16 --mbtiles --oui
  python lidar2map.py --ignraster --couche ORTHOIMAGERY.ORTHOPHOTOS --zone-departement 83 --zoom-min 14 --zoom-max 17 --mbtiles --oui
  python lidar2map.py --ignraster --couche GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2 --zone-ville gareoult --zoom-min 10 --zoom-max 16 --mbtiles --oui
  python lidar2map.py --osm --couche "highway=* waterway=* natural=water" --zone-ville gareoult --oui
  python lidar2map.py --ignraster --source gareoult_scan25_z12-16.mbtiles --rmap
        """
    )
    parser.add_argument("--version", action="version",
                        version="lidar2map 1.2.0 (2026-05) â€” multi-provider")
    parser.add_argument("--ignraster", action="store_true",
                        help="Mode raster IGN via WMTS. "
                             "Utiliser --couche pour la couche (dÃ©faut: scan25). "
                             "Ex: --ignraster --couche GEOGRAPHICALGRIDSYSTEMS.MAPS")

    # â”€â”€ DÃ©coupage Ã  priori (raster uniquement) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    grp_priori = parser.add_argument_group(
        "DÃ©coupage Ã  priori â€” --ignraster uniquement",
        "Traitement sÃ©quentiel par morceaux avec reprise automatique (manifeste.json).\n"
        "Les mÃªme paramÃ¨tres contrÃ´lent aussi le dÃ©coupage des fichiers de sortie.")
    grp_priori.add_argument("--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Nombre de colonnes de la grille (Est-Ouest).")
    grp_priori.add_argument("--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Nombre de lignes de la grille (Nord-Sud).")
    grp_priori.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative : dÃ©coupe en carrÃ©s de ~KM km.")
    grp_priori.add_argument("--nettoyage", action="store_true",
                            help="Supprimer dalles + TIF intermÃ©diaires aprÃ¨s chaque morceau. "
                                 "Indispensable pour les grandes zones (dÃ©partement entier).")

    # Zone
    _ajouter_args_zone(
        parser,
        rayon_default=10.0,
        bbox_metavar="W,S,E,N",
        bbox_help="BBox WGS84 : lon_min,lat_min,lon_max,lat_max",
    )

    # Couche + clÃ©
    parser.add_argument("--couche",  default="planign",
                        choices=list(COUCHES.keys()),
                        help="Couche WMTS (dÃ©faut: planign â€” public, sans clÃ©). "
                             "Couches pro restreintes : scan25 scan25tour scan100 scanoaci.")
    parser.add_argument("--apikey",  default="", metavar="CLE",
                        help="ClÃ© API IGN pour les couches restreintes (scan25, scan100â€¦). "
                             "âš  AccÃ¨s professionnel uniquement (compte cartes.gouv.fr + SIRET). "
                             "Les particuliers doivent utiliser les couches publiques (planign, orthoâ€¦). "
                             "Peut aussi Ãªtre dÃ©finie via la variable d'env IGN_APIKEY.")

    # Zooms
    parser.add_argument("--zoom-min", type=int, default=10, metavar="N")
    parser.add_argument("--zoom-max", type=int, default=16, metavar="N")

    # Sorties
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles","rmap","sqlitedb"],
                        default=[], metavar="FMT",
                        help="Formats de fichiers de sortie : mbtiles rmap sqlitedb (multi-valeurs).")
    parser.add_argument("--source",   metavar="CHEMIN", default=None,
                        help="Fichier .mbtiles existant â†’ conversion RMAP "
                             "(mode autonome, zone non requise). Requiert --rmap. "
                             "Ex: --source gareoult_scan25_z12-16.mbtiles --rmap")
    parser.add_argument("--dossier",  metavar="CHEMIN", default=None,
                        help="Dossier de sortie (dÃ©faut: ./ign_raster/)")

    # Comportement
    parser.add_argument("--workers",       type=int, default=NB_WORKERS, metavar="N")
    parser.add_argument("--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format des images dans les tuiles : auto, jpeg ou png (dÃ©faut: auto).")
    parser.add_argument("--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="QualitÃ© JPEG des images dans les tuiles (dÃ©faut: 85).")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Ã‰craser les tuiles en cache (re-tÃ©lÃ©chargement forcÃ©)")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Ã‰craser les MBTiles existants")
    parser.add_argument("--oui",           action="store_true")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    _valider_zooms(args, parser)
    # RÃ©solution --formats-fichier â†’ flags boolÃ©ens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    # Crash-safe : sauver l'entrÃ©e 'en cours' AVANT toute opÃ©ration longue.
    _historique_debut()

    # â”€â”€ --source : conversion autonome MBTiles â†’ RMAP (exit immÃ©diat) â”€â”€â”€â”€â”€â”€â”€â”€
    if args.source:
        p = Path(args.source)
        if not p.exists():
            print(f"  ERREUR : fichier introuvable : {args.source}")
            sys.exit(1)
        if p.suffix.lower() != ".mbtiles":
            print(f"  ERREUR : --source attend un .mbtiles (reÃ§u : {p.suffix})")
            sys.exit(1)
        if not args.rmap and not args.sqlitedb:
            print("  ERREUR : --rmap ou --sqlitedb requis.")
            print(f"  Ex: --source {p.name} --rmap")
            print(f"  Ex: --source {p.name} --sqlitedb")
            sys.exit(1)
        if args.rmap:
            generer_rmap_depuis_mbtiles(p, ecraser=args.tuiles_ecraser)
        if args.sqlitedb:
            generer_sqlitedb_depuis_mbtiles(p, ecraser=args.tuiles_ecraser)
        sys.exit(0)

    # â”€â”€ Normalisation des sorties â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Si aucune sortie explicite â†’ MBTiles par dÃ©faut
    if not args.mbtiles and not args.rmap and not args.sqlitedb:
        args.mbtiles = True

    # â”€â”€ RÃ©solution de la couche â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # --couche peut Ãªtre un alias court (planign) ou un identifiant complet
    # (GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2). Si absent â†’ planign par dÃ©faut.
    if not args.couche:
        args.couche = "planign"
    # RÃ©soudre alias court â†’ identifiant complet si besoin
    if args.couche in COUCHES:
        layer, style, img_fmt, apikey_requis = COUCHES[args.couche]
    else:
        # Identifiant complet passÃ© directement â€” dÃ©tection format/clÃ©
        layer = args.couche
        style = "normal"
        img_fmt = "image/jpeg" if any(x in layer for x in
                  ["MAPS", "ORTHOIMAGERY", "ETATMAJOR"]) else "image/png"
        apikey_requis = any(x in layer for x in ["MAPS", "SCAN"])
        print(f"  Couche : {layer} (identifiant direct)")
    # img_fmt = format DEMANDÃ‰ AU SERVEUR (URL WMTS). DOIT rester sur le
    # format natif que l'IGN sert pour cette couche â€” sinon : HTTP 400
    # "Format image/X unknown" (planign ne sert PAS en JPEG, ortho ne sert
    # PAS en PNG, etc.).
    # L'argument --formats-image contrÃ´le UNIQUEMENT le format de sortie
    # dans le MBTiles via re-encodage cÃ´tÃ© client (cf. _jpeg_q ci-dessous).
    fmt_ext = "jpg" if "jpeg" in img_fmt else "png"

    # â”€â”€ RÃ©solution de la zone â†’ bbox WGS84 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    # â”€â”€ DÃ©coupage Ã  priori : traitement sÃ©quentiel morceau par morceau â”€â”€â”€â”€â”€â”€â”€â”€
    _cols_pr = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr = getattr(args, "rows_decoupe", 0) or 0
    if _cols_pr > 0 and _rows_pr > 0:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            lon_min, lat_min, lon_max, lat_max,
            _cols_pr * _rows_pr, 0.0, unite_m=False)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_raster")
            manifeste = Manifeste(racine_pr / nom_zone / "manifeste.json")
            n_total   = len(sous_zones)
            nb_done   = sum(1 for z in sous_zones
                            if manifeste.deja_traite(f"{z[0]+1:03d}x{z[1]+1:03d}"))
            print(f"\n  â•â• DÃ©coupage Ã  priori : {mode_desc} â•â•")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Reprise : {nb_done}/{n_total} morceaux dÃ©jÃ  terminÃ©s")

            nb_ok = 0
            for i_z, (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} â€” dÃ©jÃ  terminÃ©")
                    nb_ok += 1
                    continue

                surface_km2 = ((lon_e-lon_w)*111*math.cos(math.radians((lat_s+lat_n)/2))) * \
                              ((lat_n-lat_s)*111)
                print(f"\n  â”€â”€ Morceau {cle}  ({i_z+1}/{n_total})  {nom_z} â”€â”€")
                print(f"     BBox WGS84 : {lon_w:.4f},{lat_s:.4f} â†’ "
                      f"{lon_e:.4f},{lat_n:.4f}  (~{surface_km2:.0f} kmÂ²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_wmts(args, (lon_w, lat_s, lon_e, lat_n),
                                       nom_z, nom_zone, layer, style, img_fmt, fmt_ext,
                                       apikey_requis, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] âœ“ TerminÃ© en {_hms(int(time.time() - t0_z))}")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        # Cf. boucle LiDAR : si chunk vide ou aucun mbtiles, on
                        # conserve les intermÃ©diaires pour inspection plutÃ´t que
                        # de tout supprimer silencieusement.
                        _dossier_chunk = (
                            (Path(args.dossier).resolve() if args.dossier
                             else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_raster")
                            / nom_z)
                        _mbts = list(_dossier_chunk.glob("*.mbtiles"))
                        _has_empty = (not _mbts) or any(
                            not _mbtiles_est_complete(mbt) for mbt in _mbts)
                        if _has_empty:
                            print(f"  [{cle}] mbtiles vide ou absent â€” nettoyage skipÃ© (intermÃ©diaires conservÃ©s pour inspection)")
                        else:
                            _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] âœ— ERREUR : {_e_z} â€” relancez pour reprendre")
                    raise

            elapsed = int(time.time() - t_debut)
            print(f"\n  â•â• DÃ©coupage Ã  priori terminÃ© : {nb_ok}/{n_total} morceaux â•â•")
            print(f"  DurÃ©e totale : {_hms(elapsed)}")
            return
        print("  DÃ©coupage Ã  priori : zone trop petite â†’ traitement unique")

    # â”€â”€ Calcul de la grille â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    zoom_min = min(args.zoom_min, args.zoom_max)
    zoom_max = max(args.zoom_min, args.zoom_max)

    # â”€â”€ Plafonnement selon capacitÃ©s rÃ©elles IGN (GetCapabilities WMTS) â”€â”€â”€â”€â”€â”€
    _limites_reel = _lire_zoom_limites_wmts(
        layer, apikey_requis, apikey=getattr(args, "apikey", ""))
    if _limites_reel:
        _zmin_reel, _zmax_reel = _limites_reel
        if zoom_max > _zmax_reel:
            print(f"  âš  Couche {args.couche} : zoom max IGN = {_zmax_reel} "
                  f"â€” zoom_max ramenÃ© de {zoom_max} Ã  {_zmax_reel}.")
            zoom_max = _zmax_reel
            zoom_min = min(zoom_min, zoom_max)
        if zoom_min < _zmin_reel:
            print(f"  âš  Couche {args.couche} : zoom min IGN = {_zmin_reel} "
                  f"â€” zoom_min ramenÃ© de {zoom_min} Ã  {_zmin_reel}.")
            zoom_min = _zmin_reel
            zoom_max = max(zoom_max, zoom_min)

    tuiles = calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max,
                                 zoom_min, zoom_max)
    total  = len(tuiles)
    taille_est = estimer_taille(total, fmt_ext)

    print("=" * 55)
    print(f"  Carte IGN â€” {args.couche} ({layer})")
    print("=" * 55)
    print(f"  Zone    : {nom_zone}")
    print(f"  BBox    : {lon_min:.4f},{lat_min:.4f} â†’ {lon_max:.4f},{lat_max:.4f}")
    print(f"  Zooms   : {zoom_min}â€“{zoom_max}")
    print(f"  Tuiles  : {total:,}  (~{taille_est} Mo estimÃ©s)")
    print(f"  Workers : {args.workers}")

    if not args.oui:
        rep = input("\n  Lancer le tÃ©lÃ©chargement ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    # â”€â”€ Dossier de sortie â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    racine  = Path(args.dossier).resolve() if args.dossier \
              else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_raster"
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    nom_fichier = f"{nom_zone}_{args.couche}_z{zoom_min}-{zoom_max}"
    chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
    # Cache tuiles : dossier/dalles/<z>/<x>/<y>.<ext>
    dossier_cache = DOSSIER_TRAVAIL / "cache" / "ign_raster"
    dossier_cache.mkdir(parents=True, exist_ok=True)
    print(f"  Cache dalles : {dossier_cache}")

    # â”€â”€ GÃ©nÃ©ration MBTiles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # _jpeg_q : quand non-None, dÃ©clenche un re-encodage PNG â†’ JPEG cÃ´tÃ©
    # client dans generer_mbtiles_wmts. SÃ©mantique :
    #   - JPEG natif (ortho, scan*, etc.) : _jpeg_q = None (dÃ©jÃ  JPEG)
    #   - PNG natif + --formats-image png  : _jpeg_q = None (l'utilisateur
    #     refuse explicitement la conversion â†’ on garde le PNG natif)
    #   - PNG natif + --formats-image jpeg/auto : _jpeg_q = qualitÃ© demandÃ©e
    #     â†’ conversion PNG â†’ JPEG (gain ~3-5Ã— sur la taille MBTiles)
    _native_png = img_fmt.lower() in ("image/png", "png")
    if _native_png and args.formats_image != "png":
        _jpeg_q = args.qualite_image
    else:
        _jpeg_q = None

    # Le MBTiles source doit Ãªtre (re)gÃ©nÃ©rÃ© si :
    #   - il n'existe pas encore
    #   - OU Ã©craser est demandÃ© explicitement
    # Dans tous les autres cas (fichier existant, pas d'Ã©craser) on l'utilise tel quel
    # pour la conversion / le dÃ©coupage.
    _ecraser   = args.tuiles_ecraser
    _mbtiles_requis = _mbtiles_a_regenerer(chemin_mbtiles, _ecraser)

    if not _mbtiles_requis and chemin_mbtiles.exists():
        print(f"  MBTiles existant : {chemin_mbtiles.name} â€” dÃ©coupage/conversion directe")

    if _mbtiles_requis:
        # â”€â”€ GÃ©nÃ©ration d'un seul MBTiles complet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Le dÃ©coupage Ã©ventuel est dÃ©lÃ©guÃ© Ã  _convertir_formats via decouper_mbtiles
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

    # â”€â”€ DÃ©coupage + RMAP + SQLiteDB â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if chemin_mbtiles.exists():
        _convertir_formats(chemin_mbtiles, args, mbtiles_neuf=_mbtiles_requis)

    # â”€â”€ RÃ©sumÃ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elapsed = int(time.time() - t_debut)
    print(f"\n  TerminÃ© en {_hms(elapsed)}")
    print(f"  Fichiers dans : {dossier}")
    _historique_depuis_argv(elapsed, str(dossier))


# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================


# ============================================================
# PIPELINE WFS IGN â€” VECTEUR (GeoJSON)
# ============================================================

COUCHES_WFS = {
    # â”€â”€ Cadastre â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "cadastre":        ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle",
                        "Parcelles cadastrales (PCI)"),
    # â”€â”€ Hydrographie â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "cours_eau":       ("BDTOPO_V3:cours_d_eau",
                        "Cours d'eau BD TOPO V3"),
    "troncons_eau":    ("BDTOPO_V3:troncon_hydrographique",
                        "TronÃ§ons hydrographiques BD TOPO V3"),
    "plans_eau":       ("BDTOPO_V3:plan_d_eau",
                        "Plans d'eau BD TOPO V3"),
    "detail_hydro":    ("BDTOPO_V3:detail_hydrographique",
                        "DÃ©tails hydrographiques (sources, cascadesâ€¦)"),
    # â”€â”€ BÃ¢ti / structures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "batiments":       ("BDTOPO_V3:batiment",
                        "BÃ¢timents BD TOPO V3"),
    "constructions":   ("BDTOPO_V3:construction_surfacique",
                        "Constructions surfaciques (murets, terrasses, enclos)"),
    "cimetieres":      ("BDTOPO_V3:cimetiere",
                        "CimetiÃ¨res"),
    # â”€â”€ Transport â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "routes":          ("BDTOPO_V3:troncon_de_route",
                        "TronÃ§ons de routes BD TOPO V3"),
    "chemins":         ("BDTOPO_V3:itineraire_autre",
                        "Chemins et itinÃ©raires anciens"),
    # â”€â”€ Relief / orographie â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "lignes_orog":     ("BDTOPO_V3:ligne_orographique",
                        "Lignes orographiques (talwegs, crÃªtes)"),
    "detail_orog":     ("BDTOPO_V3:detail_orographique",
                        "DÃ©tails orographiques (rochers, grottes)"),
    # â”€â”€ VÃ©gÃ©tation / milieu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "forets":          ("BDTOPO_V3:foret_publique",
                        "ForÃªts publiques"),
    "reserves":        ("BDTOPO_V3:parc_ou_reserve",
                        "Parcs et rÃ©serves naturelles"),
    # â”€â”€ Toponymie / lieux â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "lieux_dits":      ("BDTOPO_V3:lieu_dit_non_habite",
                        "Lieux-dits non habitÃ©s (toponymie historique)"),
    # â”€â”€ Admin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "communes":        ("BDTOPO_V3:commune",
                        "Limites communales"),
    # â”€â”€ Agriculture â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "rpg":             ("RPG.LATEST:parcelles_graphiques",
                        "Registre Parcellaire Graphique (cultures)"),
}

WFS_PAGE = 1000   # features par requÃªte (limite serveur IGN â€” WFS_URL dÃ©fini ligne ~1274)


def telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                    nom_zone, dossier_sortie, ecraser_telechargement=False,
                    formats=None):
    """TÃ©lÃ©charge des features WFS IGN sur une bbox WGS84 â†’ fichier .geojson.

    Pagination automatique (COUNT + STARTINDEX) jusqu'Ã  Ã©puisement.
    formats : liste parmi ("gz", "geojson") â€” formats Ã  produire (dÃ©faut ["gz"]).
              Si plusieurs sont demandÃ©s, le tÃ©lÃ©chargement n'a lieu que si au
              moins un est manquant ; les fichiers manquants sont reconstruits
              Ã  partir du premier disponible (sans re-tÃ©lÃ©charger).
    Retourne le Path du fichier principal crÃ©Ã© (gz si prÃ©sent, sinon geojson),
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

    # Ã‰crasement explicite : supprimer toutes les sorties existantes pour
    # repartir clean.
    if ecraser_telechargement:
        for p in (sortie_gz, sortie):
            if p.exists():
                p.unlink()
                print(f"  {p.name} -> Ã©crasement")

    # VÃ©rification par format demandÃ© : on ne skip que si TOUS sont prÃ©sents.
    # Sinon, si l'un est prÃ©sent, on reconstruit les manquants Ã  partir de
    # lui (lecture/Ã©criture locale, pas de re-tÃ©lÃ©chargement WFS).
    if not ecraser_telechargement:
        manque_gz  = ecrire_gz      and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie
            print(f"  {present.name} -> dÃ©jÃ  prÃ©sent")
            return present
        # Reconstruction locale si une source existe
        if (sortie_gz.exists() or sortie.exists()):
            try:
                if manque_raw and sortie_gz.exists():
                    _gunzip_vers_fichier(sortie_gz, sortie)
                    print(f"  {sortie.name} -> reconstruit depuis {sortie_gz.name}")
                if manque_gz and sortie.exists():
                    _gzip_depuis_fichier(sortie, sortie_gz)
                    print(f"  {sortie_gz.name} -> reconstruit depuis {sortie.name}")
                return sortie_gz if sortie_gz.exists() else sortie
            except OSError as e:
                print(f"  âš  Reconstruction locale Ã©chouÃ©e ({e}) â€” re-tÃ©lÃ©chargement WFS")

    print(f"  WFS {typename}...", flush=True)
    _log_req(f"{WFS_URL}?SERVICE=WFS&TYPENAMES={typename}&...", "WFS IGN")

    startindex    = 0
    n_features    = 0   # compteur â€” pas d'accumulation Python
    total_attendu = None
    t0 = time.time()

    # â”€â”€ PrÃ©-requÃªte RESULTTYPE=hits : total sans tÃ©lÃ©charger les donnÃ©es â”€â”€â”€â”€â”€â”€
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
        pass  # hits non critique â€” on continuera sans total connu

    # â”€â”€ Ã‰criture streamÃ©e : on ouvre le .gz et on Ã©crit les features au fil
    # de la pagination, sans jamais accumuler en RAM. Sur un dept-scale (>1M
    # features), la version prÃ©cÃ©dente faisait peser plusieurs Go en RAM.
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
                    print(f"  WFS interrompu â€” {n_features} features rÃ©cupÃ©rÃ©es (sortie .gz partielle)")
                # Pas de finalisation : on supprime le tmp pour ne pas garder
                # un .gz tronquÃ© qui aurait l'air valide.
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
                    print(f"  RÃ©sultat partiel : {n_features} features")
                    # On finalise avec ce qu'on a (le client a Ã©crit n_features
                    # valides, on les conserve plutÃ´t que de tout perdre).
                    break
                else:
                    raise OSError(f"WFS {typename} : aucune page rÃ©cupÃ©rÃ©e")

            page = data.get("features", [])

            # Fallback si hits a Ã©chouÃ© : capturer numberMatched Ã  la 1re page
            if total_attendu is None:
                _nm = data.get("numberMatched", data.get("totalFeatures"))
                if _nm is not None:
                    try:
                        total_attendu = int(_nm)
                    except (ValueError, TypeError):
                        pass

            # Ã‰criture streamÃ©e des features de cette page
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
                bar = ("â–ˆ" * (pct // 5)).ljust(20)
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
        # Toute exception (KeyboardInterrupt, OSError, etc.) â†’ cleanup tmp
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
        # DÃ©compresser en streaming vers le .geojson raw
        _gunzip_vers_fichier(sortie_gz, sortie)
        taille_ko = sortie.stat().st_size // 1024
        print(f"  {sortie.name} : {n_features} features  ({taille_ko} Ko)")
        if chemin_principal is None:
            chemin_principal = sortie
    if not ecrire_gz and sortie_gz.exists():
        # On a Ã©crit le .gz comme intermÃ©diaire â€” utilisateur ne le voulait pas
        sortie_gz.unlink()
    return chemin_principal


# ============================================================
# CONVERSION GEOJSON IGN â†’ OSM XML â†’ MAPSFORGE .map
# ============================================================

# Correspondance typename WFS IGN â†’ tags OSM pour mapwriter
_IGN_LAYER_TAGS = {
    # hydrographie â€” rendu bleu natif dans tous les thÃ¨mes
    "cours_d_eau":              {"waterway": "river"},
    "troncon_hydrographique":   {"waterway": "stream"},
    "plan_d_eau":               {"natural": "water"},
    "detail_hydrographique":    {"natural": "spring"},
    # bÃ¢ti / structures
    "batiment":                 {"building": "yes"},
    "construction_surfacique":  {"building": "wall"},
    "cimetiere":                {"landuse": "cemetery"},
    # transport
    "troncon_de_route":         {"highway": "unclassified"},
    "itineraire_autre":         {"highway": "track"},
    # orographie
    "ligne_orographique":       {"natural": "ridge"},
    "detail_orographique":      {"natural": "rock"},
    # vÃ©gÃ©tation / milieu
    "foret_publique":           {"landuse": "forest"},
    "parc_ou_reserve":          {"leisure": "nature_reserve"},
    # cadastre/admin : barrier=fence â†’ trait fin sans remplissage dans tous les thÃ¨mes,
    # sÃ©mantiquement juste (limite de propriÃ©tÃ©) et non conflictuel avec landuse OSM
    "commune":                  {"boundary": "administrative", "admin_level": "8"},
    "parcelle":                 {"barrier": "fence"},
    # lieux-dits
    "lieu_dit_non_habite":      {"place": "locality"},
    # RPG
    "parcelles_graphiques":     {"landuse": "farmland"},
}


def _tags_pour_layer(layer_short: str) -> dict:
    """Retourne les tags OSM Ã  appliquer pour un layer WFS IGN (nom court)."""
    for k, v in _IGN_LAYER_TAGS.items():
        if k in layer_short:
            return v
    return {"note": layer_short}


def _coords_flat(geom):
    """Retourne un itÃ©rateur de coordonnÃ©es [lon, lat, ?] pour tout type GeoJSON."""
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
    Simplifie une liste de coordonnÃ©es [lon, lat] avec l'algorithme Douglas-Peucker.
    epsilon en degrÃ©s (~0.00015 â‰ˆ 15 m).
    Conserve toujours le premier et le dernier point.
    """
    if len(coords) <= 2:
        return coords
    # Distance perpendiculaire d'un point Ã  la droite (p1, p2)
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


# TolÃ©rance de simplification pour la conversion IGN â†’ OSM XML (en degrÃ©s).
# 0.00015Â° â‰ˆ 15 m â€” rÃ©duit la densitÃ© IGN (~1 pt/3 m) de 80 %
# sans impact visuel sur une carte Mapsforge Ã  l'Ã©chelle dÃ©partement.
_IGN_SIMPLIFY_EPSILON = 0.00015


def _epsilon_depuis_surface_km2(surface_km2: float) -> float:
    """
    Calcule automatiquement l'epsilon de simplification Douglas-Peucker
    en fonction de la surface de la zone, en degrÃ©s WGS84.

    Surface        Epsilon    Contexte typique
    < 200 kmÂ²      3 m        Zone locale, rayon ~8 km
    < 1 000 kmÂ²    8 m        Arrondissement
    < 15 000 kmÂ²   15 m       Un dÃ©partement
    < 100 000 kmÂ²  25 m       Plusieurs dÃ©partements
    â‰¥ 100 000 kmÂ²  40 m       RÃ©gion entiÃ¨re
    """
    # Conversion mÃ¨tres â†’ degrÃ©s : 1Â° â‰ˆ 111 000 m
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

    StratÃ©gie :
      - Points   â†’ <node>
      - Lignes   â†’ <way> avec <nd ref=â€¦> (nÅ“uds interpolÃ©s)
      - Polygonesâ†’ <way> fermÃ© (outer ring uniquement pour MultiPolygon)

    Les tags OSM sont dÃ©duits du nom de couche (propriÃ©tÃ© 'source' ou nom fichier).
    Identifiants nÃ©gatifs (convention OSM pour donnÃ©es non-officielles).

    Streaming : lit le GeoJSON via ijson (pas de json.load() qui ferait OOM
    sur 1 Go de donnÃ©es dept-scale). Ã‰crit nodes et ways dans un fichier
    XML body temporaire au fil de l'eau, puis compose header + bounds + body
    + footer. Bounds calculÃ©s en passe unique (pas 4Ã— _coords_flat).
    Format XML bit-fidÃ¨le Ã  ElementTree (osmosis est un parseur Java strict).
    """
    from xml.sax.saxutils import escape as _xml_escape
    import decimal as _dec
    import traceback as _tb

    geojson_path = Path(geojson_path)
    osm_xml_path = Path(osm_xml_path)
    _eps = epsilon if epsilon is not None else _IGN_SIMPLIFY_EPSILON
    _TS  = "1970-01-01T00:00:00Z"   # timestamp factice â€” requis par osmosis 0.6

    # â”€â”€ ItÃ©rateur features (streaming si ijson dispo, fallback sinon) â”€â”€â”€â”€â”€â”€â”€â”€
    def _iter_features():
        try:
            import ijson
        except ImportError:
            print("  âš  ijson absent â€” chargement RAM intÃ©gral du GeoJSON")
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

    # â”€â”€ Helpers d'Ã©criture XML brute (bien plus rapide qu'ElementTree) â”€â”€â”€â”€â”€â”€â”€
    def _f(v):
        """Convertit Decimal (ijson) â†’ float ; passe-plat sinon."""
        return float(v) if isinstance(v, _dec.Decimal) else v

    def _emit_node(out, nid, lat, lon, tags=None):
        # Format reproduit ElementTree : ordre id/lat/lon/version/timestamp/visible,
        # self-closing avec espace avant slash, pas d'indentation.
        attrs = (f'id="{nid}" lat="{lat:.7f}" lon="{lon:.7f}" '
                 f'version="1" timestamp="{_TS}" visible="true"')
        if tags:
            out.write(f'<node {attrs}>')
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_escape(k)}" v="{_xml_escape(str(v))}" />')
            out.write('</node>')
        else:
            out.write(f'<node {attrs} />')

    def _emit_way(out, wid, nd_refs, tags):
        out.write(f'<way id="{wid}" version="1" timestamp="{_TS}" visible="true">')
        for r in nd_refs:
            out.write(f'<nd ref="{r}" />')
        if tags:
            for k, v in tags.items():
                out.write(f'<tag k="{_xml_escape(k)}" v="{_xml_escape(str(v))}" />')
        out.write('</way>')

    # â”€â”€ Compteurs et bounds (passe unique, sans _coords_flat Ã— 4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    state = {"node_id": -1, "way_id": -1, "nb_nodes": 0, "nb_ways": 0,
             "lon_min":  float("inf"),  "lon_max": float("-inf"),
             "lat_min":  float("inf"),  "lat_max": float("-inf"),
             "bounds_valid": False,
             "nb_inner_skipped": 0}   # rings intÃ©rieurs (trous) non Ã©mis

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
        # Convertir Decimalâ†’float : _douglas_peucker utilise math.hypot et
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

    # â”€â”€ Passe unique : streaming features â†’ 2 fichiers temporaires â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # OSM XML impose strictement l'ordre nodes â†’ ways â†’ relations (osmosis
    # plante sinon). On Ã©crit donc nodes et ways dans des fichiers sÃ©parÃ©s
    # puis on les concatÃ¨ne dans l'ordre.
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

            # DÃ©duire le layer depuis la propriÃ©tÃ© 'source' (ex: "gareoult_ign_cours_d_eau")
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
        print("\n  ERREUR dans geojson_ign_vers_osm_xml :")
        _tb.print_exc()
        if out_nodes: out_nodes.close()
        if out_ways:  out_ways.close()
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    if state["nb_nodes"] == 0:
        print("  GeoJSON vide â€” rien Ã  convertir.")
        nodes_tmp.unlink(missing_ok=True)
        ways_tmp.unlink(missing_ok=True)
        return False

    # â”€â”€ Composition du XML final : header + bounds + nodes + ways + footer â”€â”€â”€
    # Format reproduit fidÃ¨lement ElementTree.write(xml_declaration=True) :
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
    print(f"  OSM XML : {state['nb_nodes']} nÅ“uds, {state['nb_ways']} ways "
          f"â†’ {osm_xml_path.name} ({sz:.1f} Mo)")
    if state["nb_inner_skipped"]:
        # Mapsforge mapwriter ne supporte pas les multi-polygones avec trous via
        # OSM XML (il faut des relations type=multipolygon, hors scope ici).
        # On documente la perte plutÃ´t que de la cacher.
        print(f"  âš  {state['nb_inner_skipped']} ring(s) intÃ©rieur(s) ignorÃ©(s) "
              f"(trous de polygones â€” non supportÃ©s en sortie .map)")
    return True

def generer_map_depuis_geojson_ign(geojson_src, dossier_ville, nom_zone,
                                    bbox_wgs84, ecraser=False, epsilon=None):
    """
    Pipeline complet : GeoJSON IGN â†’ OSM XML â†’ osmosis+mapwriter â†’ .map Mapsforge.
    RÃ©utilise _verifier_mapwriter(), _trouver_osmosis(), _trouver_java() du mode OSM.
    """

    dossier_ville = Path(dossier_ville)
    chemin_osm_xml = dossier_ville / f"{nom_zone}_ign.osm"
    chemin_map     = dossier_ville / f"{nom_zone}_ign.map"

    if chemin_map.exists() and not ecraser:
        if chemin_map.stat().st_size == 0:
            print(f"  Carte IGN .map existante vide â€” rÃ©gÃ©nÃ©ration forcÃ©e.")
            chemin_map.unlink()
        else:
            print(f"  Carte IGN .map dÃ©jÃ  prÃ©sente : {chemin_map.name} â€” ignorÃ©e")
            return chemin_map

    if chemin_map.exists() and ecraser:
        chemin_map.unlink()
        print(f"  Carte IGN .map : Ã©crasement {chemin_map.name}")

    # â”€â”€ Ã‰tape 1 : GeoJSON â†’ OSM XML â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"  Conversion GeoJSON â†’ OSM XML...", flush=True)
    ok = geojson_ign_vers_osm_xml(geojson_src, chemin_osm_xml, epsilon=epsilon)
    if not ok:
        return None

    # â”€â”€ Ã‰tape 2 : OSM XML â†’ .map via osmosis + mapwriter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
    print(f"  osmosis â†’ {chemin_map.name}...", flush=True)

    cmd = [
        _osmosis_exe,
        "--read-xml", f"file={chemin_osm_xml}",
        "--mapfile-writer",
        f"file={chemin_map}",
        f"bbox={lat_min:.6f},{lon_min:.6f},{lat_max:.6f},{lon_max:.6f}",
        "zoom-interval-conf=7,0,7,11,8,11,14,12,21",
        "tag-values=true", "polygon-clipping=true",
        "way-clipping=true", "label-position=true",
        # type=hd retirÃ© : bug HDTileBasedDataProcessor sur gros volumes
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
        chemin_osm_xml.unlink(missing_ok=True)  # succÃ¨s seulement
        taille_b = chemin_map.stat().st_size
        if taille_b < 1_000_000:
            print(f"  {chemin_map.name} : {taille_b // 1024} Ko  {_hms(time.time()-t0)}")
        else:
            print(f"  {chemin_map.name} : {taille_b / 1e6:.1f} Mo  {_hms(time.time()-t0)}")
        return chemin_map
    elif chemin_map.exists() and chemin_map.stat().st_size == 0:
        chemin_map.unlink(missing_ok=True)
        print(f"  âš  {chemin_map.name} crÃ©Ã© mais vide â€” aucune feature reconnue par mapwriter.")
        print(f"  {chemin_osm_xml.name} conservÃ© pour diagnostic.")
        return None
    else:
        print(f"  ERREUR osmosis mapfile-writer IGN (code {rc})")
        if stderr_diag:
            print(f"  {stderr_diag.strip()[:2000]}")
        print(f"  {chemin_osm_xml.name} conservÃ© â€” relancez osmosis aprÃ¨s correction.")
        return None


# ============================================================
# TÃ‰LÃ‰CHARGEMENT BULK BD TOPO IGN (dÃ©partement entier)
# ============================================================
# Pour --zone-departement : l'API IGN fournit un GPKG complet par dÃ©partement
# (~1-2 Go, 1 seule requÃªte HTTP). Beaucoup plus rapide que la pagination WFS
# (415 requÃªtes pour le Var).
# Pipeline : API discovery â†’ GPKG streamÃ© (cache) â†’ ogr2ogr par couche â†’ GeoJSON.gz
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
    """Retourne (url_7z, nom_ressource) pour le dernier GPKG BD TOPO du dÃ©partement.
    Les fichiers IGN sont packagÃ©s en .7z contenant un .gpkg.
    """
    dep_padded = str(num_dep).zfill(3)
    zone = f"D{dep_padded}"

    # 1. RequÃªte API Atom â€” retourne du XML Atom, pas du JSON
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
        # Les entrÃ©es Atom ont un <id> ou <title> contenant le nom de ressource
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
            # Trier par (date, version_tuple) pour prendre le plus rÃ©cent.
            # Les noms ont la forme :
            #   BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D083_2024-12-15
            # Un sort lexicographique simple est trompeur dÃ¨s que la version
            # mineure passe Ã  2 chiffres ('3-10' < '3-5' en lex).
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
        print(f"  âš  API IGN ({type(e).__name__}: {e}) â€” essai dates connues")

    # 2. Fallback : dates trimestrielles (YYYY-03/06/09/12-15) sur 2 ans
    import datetime as _dt
    today = _dt.date.today()
    candidates = []
    for delta_q in range(8):
        y, q = today.year, ((today.month - 1) // 3) - delta_q
        while q < 0:
            q += 4; y -= 1
        candidates.append(f"{y}-{[3, 6, 9, 12][q % 4]:02d}-15")

    # Versions IGN Ã  tester. Tuples (major, minor) â€” le tri par tuple gÃ¨re
    # correctement les versions mineures Ã  plusieurs chiffres (3-10 > 3-9 > 3-5),
    # contrairement Ã  un tri lex sur la chaÃ®ne "3-X". Ajouter une nouvelle
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

    print(f"  ERREUR : archive BD TOPO GPKG introuvable pour {num_dep}")
    return None, None


def _telecharger_bdtopo_gpkg(num_dep, url, nom_ressource):
    """TÃ©lÃ©charge et extrait le .7z BD TOPO, met le .gpkg en cache. Retourne Path ou None."""
    dep_padded = str(num_dep).zfill(3)
    cache_dir  = DOSSIER_TRAVAIL / "cache" / "bdtopo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = cache_dir / f"{nom_ressource}.gpkg"

    if gpkg_path.exists() and gpkg_path.stat().st_size > 10_000_000:
        print(f"  Cache GPKG : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} Mo) â€” rÃ©utilisÃ©", flush=True)
        return gpkg_path

    # â”€â”€ VÃ©rifier que py7zr est disponible pour l'extraction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        import py7zr as _py7zr
    except ImportError:
        print("  Installation py7zr pour extraction .7z...", flush=True)
        r_pip = subprocess.run(
            [sys.executable, "-m", "pip", "install", "py7zr", "-q"],
            capture_output=True)
        if r_pip.returncode != 0:
            print("  ERREUR : py7zr non installable â€” impossible d'extraire le .7z IGN")
            return None
        import py7zr as _py7zr

    # â”€â”€ TÃ©lÃ©chargement du .7z â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sz_path = cache_dir / f"{nom_ressource}.7z"
    print(f"  TÃ©lÃ©chargement BD TOPO D{dep_padded} (~200-800 Mo)...", flush=True)
    _log_req(url, "IGN bulk GPKG")
    tmp = cache_dir / f"{nom_ressource}.7z.tmp"
    t0 = time.time()
    try:
        try:
            resp = _urlopen(url, timeout=120)
        except urllib.error.HTTPError as _e:
            print(f"  ERREUR HTTP {_e.code} â€” {url}")
            return None
        # `with` ferme la connexion HTTP mÃªme sur exception (pas de FD leak).
        with resp:
            total = int(resp.headers.get("content-length") or 0)
            done = 0
            # Throttle d'affichage : on actualise au max toutes les 0.5s pour
            # Ã©viter de noyer la GUI (Popen/PIPE) avec un print() tous les 1 Mo.
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
                        bar = ("â–ˆ" * (pct // 5)).ljust(20)
                        sys.stdout.write(
                            f"\r  [{bar}] {pct:3d}%  "
                            f"{done/1e6:.0f}/{total/1e6:.0f} Mo  {_hms(elapsed)}   ")
                    else:
                        sys.stdout.write(
                            f"\r  {done/1e6:.0f} Mo  {_hms(elapsed)}   ")
                    sys.stdout.flush()
        sys.stdout.write("\r" + " " * 70 + "\r"); sys.stdout.flush()
        tmp.replace(sz_path)
        print(f"  âœ“ {sz_path.name}  ({sz_path.stat().st_size/1e6:.0f} Mo)  "
              f"{_hms(int(time.time()-t0))}", flush=True)
    except (OSError, urllib.error.URLError) as e:
        tmp.unlink(missing_ok=True)
        print(f"  ERREUR tÃ©lÃ©chargement ({type(e).__name__}): {e}")
        return None

    # â”€â”€ Extraction du .gpkg depuis le .7z â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"  Extraction GPKG depuis {sz_path.name}...", flush=True)
    try:
        with _py7zr.SevenZipFile(sz_path, mode="r") as z:
            # Trouver le .gpkg dans l'archive
            gpkg_names = [n for n in z.getnames() if n.lower().endswith(".gpkg")]
            if not gpkg_names:
                print("  ERREUR : aucun .gpkg dans l'archive 7z")
                sz_path.unlink(missing_ok=True)
                return None
            # Extraire uniquement le .gpkg (peut Ãªtre dans un sous-dossier)
            z.extract(targets=gpkg_names, path=cache_dir)

        # Trouver le fichier extrait (py7zr peut placer le .gpkg dans un sous-dossier
        # du cache_dir selon la structure interne de l'archive 7z).
        # gpkg_path lui-mÃªme n'existe pas Ã  ce stade (return early plus haut),
        # donc tout .gpkg trouvÃ© est forcÃ©ment le rÃ©sultat de l'extraction.
        extracted = next(cache_dir.rglob("*.gpkg"), None)
        if extracted is None:
            print("  ERREUR : .gpkg introuvable aprÃ¨s extraction")
            return None
        if extracted != gpkg_path:
            extracted.replace(gpkg_path)
            # Nettoyer le sous-dossier laissÃ© par py7zr s'il est devenu vide
            try:
                if extracted.parent != cache_dir and not any(extracted.parent.iterdir()):
                    extracted.parent.rmdir()
            except OSError:
                pass

        sz_path.unlink(missing_ok=True)   # libÃ©rer l'espace du .7z
        print(f"  âœ“ GPKG extrait : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} Mo)", flush=True)
        return gpkg_path

    except Exception as e:
        print(f"  ERREUR extraction .7z ({type(e).__name__}): {e}")
        sz_path.unlink(missing_ok=True)
        return None


def _streamer_geojson_ajout_source(src_geojson, dst_gz, source_name):
    """
    Streame src_geojson (FeatureCollection) â†’ dst_gz en ajoutant
    'source'=source_name Ã  chaque feature.

    Utilise ijson pour lecture incrÃ©mentale : ne charge JAMAIS l'intÃ©gralitÃ©
    du GeoJSON en RAM. Critique pour les couches BD TOPO dept-scale qui
    peuvent dÃ©passer 1 Go en JSON (= 3-4 Go en RAM Python sans streaming).

    Le format de sortie est identique Ã  celui produit par _ecrire_geojson_gz :
    JSON compact (separators=(",", ":")), gzip niveau 6, CRS84.

    Retourne le nombre de features Ã©crites (0 si fichier source vide).
    """
    import decimal as _dec

    def _enc_default(o):
        # ijson retourne des decimal.Decimal pour les nombres â†’ reconvertir en float
        if isinstance(o, _dec.Decimal):
            return float(o)
        raise TypeError(f"Type non-sÃ©rialisable : {type(o).__name__}")

    dst_gz = Path(dst_gz)
    if not str(dst_gz).endswith(".gz"):
        dst_gz = Path(str(dst_gz) + ".gz")
    dst_gz.parent.mkdir(parents=True, exist_ok=True)

    try:
        import ijson
    except ImportError:
        # Fallback non-streaming (peut faire OOM sur dept-scale â€” averti)
        print("  âš  ijson absent â€” chargement RAM intÃ©gral (risque OOM sur dept-scale)")
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

    # â”€â”€ Streaming feature par feature â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    n = 0
    crs_obj = {"type": "name",
               "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(source_name, ensure_ascii=False)
        + ',"crs":' + json.dumps(crs_obj, ensure_ascii=False, separators=(",", ":"))
        + ',"features":['
    )
    # Ã‰criture binaire dans gzip pour Ã©viter le double encoding textâ†’bytes
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
    Extrait une couche GPKG â†’ GeoJSON(.gz) via fiona (streaming, reprojection WGS84).
    bbox_l93 : (xmin, ymin, xmax, ymax) pour clipper, ou None = dÃ©partement entier.
    formats  : liste parmi ("gz","geojson") â€” formats Ã  produire (dÃ©faut ["gz"]).

    Ã‰tape 7 du refactor : remplace ogr2ogr CLI par fiona+pyproj.
    Streaming feature par feature pour borner la RAM (un dÃ©partement entier
    peut faire 200-800 Mo en JSON, soit 1-3 Go pic RAM avec json.load()).
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
                print(f"  {p.name} -> Ã©crasement")

    if not ecraser:
        manque_gz  = ecrire_gz      and not sortie_gz.exists()
        manque_raw = ecrire_geojson and not sortie_raw.exists()
        if not manque_gz and not manque_raw:
            present = sortie_gz if sortie_gz.exists() else sortie_raw
            print(f"  {present.name} â†’ dÃ©jÃ  prÃ©sent")
            return present
        # Reconstruction locale entre formats â€” Ã©vite de relire le GPKG (lent).
        if (sortie_gz.exists() or sortie_raw.exists()):
            try:
                if manque_raw and sortie_gz.exists():
                    _gunzip_vers_fichier(sortie_gz, sortie_raw)
                    print(f"  {sortie_raw.name} â†’ reconstruit depuis {sortie_gz.name}")
                if manque_gz and sortie_raw.exists():
                    _gzip_depuis_fichier(sortie_raw, sortie_gz)
                    print(f"  {sortie_gz.name} â†’ reconstruit depuis {sortie_raw.name}")
                return sortie_gz if sortie_gz.exists() else sortie_raw
            except OSError as e:
                print(f"  âš  Reconstruction locale Ã©chouÃ©e ({e}) â€” extraction GPKG")

    try:
        import fiona
        from fiona.transform import transform_geom as _xform_geom
    except ImportError:
        print("  ERREUR : fiona absent â€” pip install fiona")
        return None

    tmp_geojson = sortie_gz.parent / (sortie_gz.name.replace(".geojson.gz", "_tmp.geojson"))

    t0 = time.time()
    try:
        # Construire le filtre bbox au format fiona si bbox_l93 fourni.
        # bbox doit Ãªtre en CRS source (EPSG:2154) â€” fiona accepte directement.
        bbox_filter = None
        if bbox_l93:
            xmin, ymin, xmax, ymax = bbox_l93
            bbox_filter = (xmin, ymin, xmax, ymax)

        # Streaming feature par feature â†’ fichier GeoJSON temp.
        # On reprojete chaque gÃ©omÃ©trie via fiona.transform (Pyproj sous-jacent).
        with fiona.open(str(gpkg_path), layer=layer_name) as src:
            src_crs = src.crs
            n_total = 0
            with open(tmp_geojson, "w", encoding="utf-8") as out:
                out.write('{"type":"FeatureCollection","features":[\n')
                first = True
                # ItÃ©ration : si bbox fournie, fiona filtre nativement.
                # Sans bbox : tout le dÃ©partement.
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
        print(f"  âš  {layer_name} : aucune feature")
        tmp_geojson.unlink(missing_ok=True); return None

    try:
        # _streamer_geojson_ajout_source Ã©crit toujours en .gz â€” on le gÃ©nÃ¨re
        # systÃ©matiquement (fichier de travail), puis on dÃ©rive .geojson si demandÃ©.
        src_name = sortie_gz.name.replace(".geojson.gz", "")
        n = _streamer_geojson_ajout_source(tmp_geojson, sortie_gz, src_name)
        if n == 0:
            print(f"  âš  {layer_name} : 0 features aprÃ¨s streaming")
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
        # Si seulement .geojson est demandÃ©, supprimer le .gz intermÃ©diaire
        if not ecrire_gz and sortie_gz.exists():
            sortie_gz.unlink()
        return chemin_principal
    finally:
        tmp_geojson.unlink(missing_ok=True)


def _telecharger_bdtopo_bulk(num_dep, couches_resolues, nom_zone,
                              dossier_sortie, bbox_l93=None, ecraser=False,
                              formats=None):
    """
    Pipeline bulk BD TOPO pour un dÃ©partement entier.
    formats : liste parmi ("gz","geojson") â€” propagÃ© Ã  _extraire_couche_bdtopo.
    Retourne list[Path] des GeoJSON(.gz) crÃ©Ã©s, ou None si Ã©chec critique.
    """
    print(f"  Bulk BD TOPO GPKG dÃ©partement {num_dep} "
          f"(WFS serait trop lent Ã  cette Ã©chelle)", flush=True)
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
    """Point d'entrÃ©e mode --ignvecteur."""
    import argparse

    t_debut = time.time()

    parser = argparse.ArgumentParser(
        prog="lidar2map.py --ignvecteur",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            ["Couches disponibles :"] +
            [f"  {k:<16} {v[1]}" for k, v in COUCHES_WFS.items()] +
            ["",
             "Exemples :",
             "  python lidar2map.py --ignvecteur --zone-ville gareoult --zone-rayon 5 --oui",
             "  python lidar2map.py --ignvecteur --couche batiments routes --zone-ville gareoult --oui",
             "  python lidar2map.py --ignvecteur --couche cadastre --zone-departement 83 --oui",
            ]
        )
    )
    parser.add_argument("--version", action="version",
                        version="lidar2map 1.2.0 (2026-05) â€” multi-provider")
    parser.add_argument("--ignvecteur", action="store_true")
    parser.add_argument("--couche", metavar="NOM", nargs="+", default=["cadastre"],
                        help="Couche(s) WFS Ã  tÃ©lÃ©charger (dÃ©faut: cadastre). "
                             "Alias court ou typename complet. "
                             "Plusieurs couches sÃ©parÃ©es par des espaces.")

    # Zone â€” mÃªme logique que --ignraster
    _ajouter_args_zone(
        parser,
        rayon_default=10.0,
        bbox_metavar="W,S,E,N",
    )
    parser.add_argument("--dossier",     metavar="CHEMIN", default=None,
                        help="Dossier de sortie (dÃ©faut: ./ign_vecteur/)")
    parser.add_argument("--workers",  type=int, default=4, metavar="N",
                        help="Connexions parallÃ¨les WFS (dÃ©faut: 4)")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Ã‰craser les GeoJSON existants (re-tÃ©lÃ©chargement forcÃ©)")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["geojson","gz","map"],
                        default=["gz"], metavar="FMT",
                        help="Formats de sortie : geojson gz map (dÃ©faut: gz). "
                             "map gÃ©nÃ¨re une carte Mapsforge via osmosis.")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Ã‰craser la carte .map existante")
    parser.add_argument("--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Epsilon de simplification Douglas-Peucker en mÃ¨tres. "
                             "Sans ce paramÃ¨tre, calculÃ© automatiquement depuis la surface "
                             "(<200 kmÂ²â†’3 m, <1000â†’8 m, <15000â†’15 m, <100000â†’25 m, sinonâ†’40 m).")
    parser.add_argument("--oui",         action="store_true",
                        help="Mode non-interactif")

    args = parser.parse_args()
    _ff = getattr(args, "formats_fichier", ["gz"])
    # Formats GeoJSON Ã  produire (filtre "map" qui est traitÃ© plus loin)
    _gj_formats = [f for f in _ff if f in ("gz", "geojson")] or ["gz"]

    # Crash-safe : sauver l'entrÃ©e 'en cours' AVANT toute opÃ©ration longue.
    _historique_debut()

    # â”€â”€ RÃ©solution des couches â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    couches_resolues = []
    for c in args.couche:
        if c in COUCHES_WFS:
            couches_resolues.append(COUCHES_WFS[c])
        else:
            # typename complet passÃ© directement
            couches_resolues.append((c, c))

    # â”€â”€ RÃ©solution de la zone â†’ bbox WGS84 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    racine  = (Path(args.dossier).resolve() if args.dossier
               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_vecteur")
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    # â”€â”€ RÃ©sumÃ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("=" * 56)
    print("  Vecteur IGN WFS â†’ GeoJSON")
    print("=" * 56)
    print(f"  Zone     : {nom_zone}")
    print(f"  BBox     : {lon_min:.4f},{lat_min:.4f} â†’ {lon_max:.4f},{lat_max:.4f}")
    print(f"  Couche(s): {', '.join(c[1] for c in couches_resolues)}")
    print(f"  Sortie   : {dossier}")

    if not args.oui:
        rep = input("\n  Lancer ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    # â”€â”€ TÃ©lÃ©chargement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            bbox_l93         = None,   # dÃ©partement entier â€” pas de clip bbox
            ecraser          = args.telechargement_ecraser,
            formats          = _gj_formats,
        )
        if sorties_bulk is not None:
            sorties = sorties_bulk
        else:
            print("  Repli sur WFS pagination...")

    if not _bulk_tente or not sorties:
        # WFS standard (zone locale ou repli bulk Ã©chouÃ©)
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

    # â”€â”€ Fusion des couches â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _geojson_fusionne = None
    if len(sorties) > 1:
        sortie_fusion = dossier / f"{nom_zone}_ign.geojson"
        # main_wfs connaÃ®t dÃ©jÃ  la bbox (lon_min/lat_min/...) â€” pas besoin
        # du retour bbox du fusionner_geojson, on prend le compat wrapper.
        _geojson_fusionne = _fusionner_geojson_compat(sorties, sortie_fusion)

    # â”€â”€ GÃ©nÃ©ration Mapsforge .map si demandÃ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _ff = getattr(args, "formats_fichier", ["gz"])
    if "map" in _ff and sorties:
        # DÃ©terminer la source GeoJSON
        if len(sorties) > 1:
            _src_geojson = _geojson_fusionne  # None si fusion vide
        else:
            _src_geojson = sorties[0]

        if _src_geojson is None or not Path(_src_geojson).exists():
            print("\n  âš  GÃ©nÃ©ration .map ignorÃ©e : aucun feature disponible.")
        else:
            # Epsilon : paramÃ¨tre explicite ou calcul automatique depuis surface bbox
            if getattr(args, "simplification_vecteur", None):
                _eps_m = args.simplification_vecteur
                print(f"\n  Simplification vecteur : epsilon={_eps_m:.1f} m (forcÃ©)")
            else:
                _surf = (lon_max - lon_min) * (lat_max - lat_min) * (111_000 ** 2) / 1e6
                _eps_m = _epsilon_depuis_surface_km2(_surf) * 111_000
                print(f"\n  Simplification vecteur : epsilon={_eps_m:.0f} m (auto, surfaceâ‰ˆ{_surf:.0f} kmÂ²)")
            _eps_deg = _eps_m / 111_000.0
            print("  GÃ©nÃ©ration carte Mapsforge (.map) depuis GeoJSON IGN...")
            generer_map_depuis_geojson_ign(
                geojson_src   = _src_geojson,
                dossier_ville = dossier,
                nom_zone      = nom_zone,
                bbox_wgs84    = (lon_min, lat_min, lon_max, lat_max),
                ecraser       = args.tuiles_ecraser,
                epsilon       = _eps_deg,
            )

    # â”€â”€ Bilan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elapsed = int(time.time() - t_debut)
    print(f"\n  TerminÃ© en {_hms(elapsed)} â€” {len(sorties)}/{len(couches_resolues)} couches")
    for s in sorties:
        print(f"  â†’ {s}")
    _historique_depuis_argv(elapsed, str(dossier))


# ============================================================
# EXPORT GEOJSON DEPUIS PBF OSM (ogr2ogr)
# ============================================================

def generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                        osm_tags=None, ecraser_tuiles=False, formats=None):
    """
    Exporte le PBF OSM filtrÃ© par bbox en GeoJSON via PyOsmium.
    Produit un fichier global ``<nom>_osm.geojson(.gz)`` + un fichier par clÃ©
    thÃ©matique ``<nom>_osm_<cle>.geojson(.gz)``.
    Chaque feature reÃ§oit ``source='OSM'``.

    ParamÃ¨tre `formats` : liste indiquant les formats Ã  produire :
      - ["gz"]                 â†’ .geojson.gz uniquement (dÃ©faut, compact)
      - ["geojson"]            â†’ .geojson uniquement (lisible direct)
      - ["gz", "geojson"]      â†’ les deux

    Ã‰tape 7bis du refactor : remplace l'ancien pipeline ogr2ogr+osmconf.ini
    par PyOsmium, lib Python pure (binding C++ libosmium) sans dÃ©pendance
    GDAL systÃ¨me. Wheels prÃ©compilÃ©s disponibles pour Python 3.10-3.13 sur
    Windows/macOS/Linux.

    Avantages :
      - Maintenu activement (releases rÃ©guliÃ¨res)
      - Wheels prÃ©compilÃ©s cp312/win_amd64 (~2 Mo)
      - Pas de compilation Cython au runtime (contrairement Ã  pyrosm)
      - API GeoJSONFactory directement utilisable

    Limites :
      - Le filtre bbox n'est pas natif cÃ´tÃ© libosmium : on filtre les nodes
        Ã  la lecture, et on garde uniquement les ways/areas dont au moins
        un node est dans la bbox (Ã©quivalent --spat de ogr2ogr).
      - Les relations non-multipolygon (route, boundary admin, etc.) ne
        produisent pas de gÃ©omÃ©trie GeoJSON directement (limitation libosmium).

    Retourne le Path du fichier fusionnÃ© principal (.gz si demandÃ© sinon
    .geojson), ou None en cas d'Ã©chec.
    """
    # Formats Ã  produire : par dÃ©faut .gz uniquement (compatibilitÃ©)
    if formats is None:
        formats = ["gz"]
    formats = [f.lower() for f in formats]
    ecrire_gz      = "gz"      in formats
    ecrire_geojson = "geojson" in formats
    if not (ecrire_gz or ecrire_geojson):
        # Cas dÃ©gradÃ© : aucun format reconnu, on tombe sur .gz
        ecrire_gz = True

    # Cache check : on ne court-circuite que si TOUS les formats demandÃ©s
    # sont dÃ©jÃ  prÃ©sents. Si l'utilisateur demande Ã  la fois .gz et .geojson,
    # et qu'on n'a que le .gz, il faut quand mÃªme regÃ©nÃ©rer le .geojson.
    chemin_gz_attendu  = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_raw_attendu = dossier_ville / f"{nom_zone}_osm.geojson"
    formats_manquants = []
    if ecrire_gz and not chemin_gz_attendu.exists():
        formats_manquants.append("gz")
    if ecrire_geojson and not chemin_raw_attendu.exists():
        formats_manquants.append("geojson")

    if not formats_manquants and not ecraser_tuiles:
        # Tous les formats demandÃ©s sont dÃ©jÃ  lÃ 
        present = chemin_gz_attendu if chemin_gz_attendu.exists() else chemin_raw_attendu
        print(f"  GeoJSON OSM deja present : {present.name} â€” ignore")
        return present

    if ecraser_tuiles:
        # Mode Ã©crasement : supprimer les sorties existantes pour repartir clean
        for p in (chemin_gz_attendu, chemin_raw_attendu):
            if p.exists():
                p.unlink()
                print(f"  GeoJSON OSM : Ã©crasement {p.name}")
        # Aussi supprimer les fichiers thÃ©matiques existants (per-clÃ©)
        for p in dossier_ville.glob(f"{nom_zone}_osm_*.geojson*"):
            try:
                p.unlink()
            except OSError:
                pass

    try:
        import osmium as _osm
    except ImportError:
        print("  ERREUR : osmium absent â€” pip install osmium")
        print("          (binding Python officiel libosmium, ~2 Mo, wheel prÃ©compilÃ©)")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    t0 = time.time()
    chemin_principal = chemin_gz_attendu if ecrire_gz else chemin_raw_attendu
    print(f"  PyOsmium â†’ {chemin_principal.name}...", flush=True)

    # ClÃ©s thÃ©matiques demandÃ©es par l'utilisateur (osm_tags="highway=*,waterway=*"
    # â†’ ["highway","waterway"]). Si rien : ensemble par dÃ©faut adaptÃ© outdoor.
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
    # construire les features avec leurs propriÃ©tÃ©s.
    fab = _osm.geom.GeoJSONFactory()

    # Helper : retourne la clÃ© thÃ©matique d'un objet (la 1Ã¨re trouvÃ©e dans cles_set)
    # et la valeur associÃ©e. None si aucune clÃ© thÃ©matique.
    def _cle_obj(tags):
        for _k in cles_set:
            if _k in tags:
                return _k, tags[_k]
        return None, None

    # Helper : test si une gÃ©omÃ©trie GeoJSON intersecte la bbox demandÃ©e.
    # On fait un test simple bounding-box vs bounding-box (rapide). Suffisant
    # pour notre usage : le PBF est dÃ©jÃ  prÃ©-filtrÃ© par osmosis sur la bbox.
    def _geom_intersect_bbox(geom_dict):
        if geom_dict is None:
            return False
        coords = geom_dict.get("coordinates")
        if coords is None:
            return False
        # Calcul de la bbox de la gÃ©omÃ©trie en parcourant les coordonnÃ©es
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

    # Streaming : on ouvre un .gz temporaire par clÃ© thÃ©matique et on y Ã©crit
    # les features au fil de la passe PyOsmium. Pas d'accumulation en RAM â€”
    # un dÃ©partement peut produire plusieurs millions de features.
    _streams       = {}   # cle â†’ file handle gzip ouvert
    _streams_paths = {}   # cle â†’ (path_tmp_gz, path_final_gz, path_final_raw)
    _first_feat    = {}   # cle â†’ bool (1Ã¨re feature non encore Ã©crite)
    _counts_par_cle = {}  # cle â†’ nombre de features Ã©crites
    nb_total = [0]
    nb_kept  = [0]

    def _ouvrir_stream_cle(cle):
        """Ouvre paresseusement le .gz tmp pour cette clÃ© (1Ã¨re feature)."""
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

    # ItÃ©ration via FileProcessor moderne (PyOsmium 4.x)
    # - with_locations() : nÃ©cessaire pour reconstruire les linestrings (ways)
    # - with_areas()     : nÃ©cessaire pour reconstruire les multipolygons
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

            # CrÃ©ation de la gÃ©omÃ©trie selon le type d'objet
            try:
                if o.is_node():
                    geom_str = fab.create_point(o)
                elif o.is_way() and not o.is_closed():
                    # Way ouvert â†’ linestring
                    geom_str = fab.create_linestring(o)
                elif o.is_area():
                    # Area (way fermÃ© ou relation multipolygon) â†’ multipolygon
                    geom_str = fab.create_multipolygon(o)
                else:
                    # Relations non-multipolygon : pas de gÃ©omÃ©trie directe
                    continue
            except Exception:
                # GÃ©omÃ©trie invalide (area mal fermÃ©e, etc.) â€” on ignore
                continue

            try:
                geom = json.loads(geom_str)
            except Exception:
                continue

            if not _geom_intersect_bbox(geom):
                continue

            # Construction de la feature GeoJSON, Ã©criture incrÃ©mentale
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
        print(f"  ERREUR PyOsmium : {type(e_proc).__name__} : {e_proc}")
        return None

    # Finaliser chaque stream par-clÃ© : footer ']}' puis close puis replace atomique
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

    print(f"  PyOsmium : {nb_total[0]} objets parcourus, {nb_kept[0]} dans la bbox", flush=True)

    if nb_kept[0] == 0:
        # Aucune feature retenue â€” nettoyer les .gz vides Ã©ventuels et sortir
        for _, path_gz, _ in _streams_paths.values():
            try: path_gz.unlink(missing_ok=True)
            except Exception: pass
        print("  Aucun feature OSM exportÃ©")
        return None

    # DÃ©river les .geojson raw par-clÃ© si demandÃ© (depuis le .gz, en streaming)
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

    # Fichier fusionnÃ© global : concatÃ©ner en streaming les fichiers par-clÃ©
    base_global = dossier_ville / f"{nom_zone}_osm.geojson"
    chemin_global_gz  = Path(str(base_global) + ".gz")
    chemin_global_raw = base_global

    chemin_principal = None
    # On reconstruit le .gz global Ã  partir des .gz par-clÃ©. Pas via
    # `_par_cle` qui n'existe plus â€” on rÃ©-ouvre chaque fichier par-clÃ© en
    # ijson pour itÃ©rer ses features et les rÃ©-injecter dans le global.
    # Si ijson absent, fallback : json.load() â€” acceptÃ© en dÃ©gradÃ© sur cas
    # extrÃªmes (le dÃ©partement entier OSM tient < 2 Go en JSON typiquement).
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
            # Fallback non-streaming (cas ijson cassÃ© / absent)
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
                    raise TypeError(f"Type non-sÃ©rialisable : {type(o).__name__}")
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
    Ã‰crit un dict GeoJSON sur disque.
    - compresser=True (dÃ©faut)  : produit `<chemin>.geojson.gz` (gzip niveau 6)
    - compresser=False           : produit `<chemin>.geojson` (texte brut)
    Le paramÃ¨tre `chemin` peut se terminer par .geojson ou .geojson.gz â€”
    la sortie respectera le mode demandÃ© indÃ©pendamment du suffixe d'entrÃ©e.
    Retourne le Path du fichier crÃ©Ã©.
    """
    p = Path(chemin)
    # Normaliser le chemin selon le mode
    if compresser:
        if not str(p).endswith(".gz"):
            p = Path(str(p) + ".gz")
    else:
        # Mode non compressÃ© : retirer le .gz Ã©ventuel
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
    """Lit un .geojson ou .geojson.gz â€” retourne le dict."""
    p = Path(chemin)
    if str(p).endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(p.read_text(encoding="utf-8"))


def fusionner_geojson(fichiers, sortie):
    """
    Fusionne plusieurs GeoJSON en un seul FeatureCollection â€” STREAMING.

    Lecture incrÃ©mentale via ijson (fallback json.load si ijson absent),
    Ã©criture incrÃ©mentale dans le .gz au fil de l'eau. La bbox WGS84 est
    calculÃ©e pendant la passe d'Ã©criture (pas de re-lecture nÃ©cessaire).

    fichiers : liste de Path ou str
    sortie   : Path de sortie
    Retourne (Path crÃ©Ã©, bbox|None) â€” bbox = (lon_min, lat_min, lon_max, lat_max),
    ou (None, None) si aucune feature Ã  fusionner.
    """
    import decimal as _dec
    try:
        import ijson
        _has_ijson = True
    except ImportError:
        _has_ijson = False

    sortie = Path(sortie)
    # Sortie .gz si l'extension dit .gz, sinon raw. _ecrire_geojson_gz
    # respectait dÃ©jÃ  cette convention ; on la conserve ici.
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
        raise TypeError(f"Type non-sÃ©rialisable : {type(o).__name__}")

    # Header GeoJSON
    name_out = sortie.name.replace(".geojson.gz", "").replace(".geojson", "")
    header = (
        '{"type":"FeatureCollection","name":'
        + json.dumps(name_out, ensure_ascii=False)
        + ',"crs":{"type":"name","properties":'
          '{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}}'
        + ',"features":['
    ).encode("utf-8")

    # Bounds calculÃ©s au passage. On Ã©vite _coords_flat (rÃ©cursif Python pour
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
                print(f"  AVERTISSEMENT : {p.name} streaming Ã©chouÃ© ({e}) â€” fallback RAM")
        # Fallback non-streaming
        try:
            data = _lire_geojson(p)
        except Exception as e:
            print(f"  AVERTISSEMENT : {p.name} illisible ({e}) â€” ignorÃ©")
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
                print(f"  AVERTISSEMENT : {p.name} introuvable â€” ignorÃ©")
                continue

            n_fichier = 0
            for source, feat in _iter_features_streame(p):
                if _stop_event.is_set():
                    raise KeyboardInterrupt("Fusion interrompue")
                # Convertir Decimal Ã©ventuels (ijson)
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
        print("  Aucun feature Ã  fusionner")
        return None, None

    tmp.replace(sortie)
    taille = sortie.stat().st_size // 1024
    print(f"  â†’ {sortie.name} : {n_total} features  ({taille} Ko)")

    bbox = None
    if state["valid"]:
        bbox = (state["lon_min"], state["lat_min"],
                state["lon_max"], state["lat_max"])
    return sortie, bbox


def _fusionner_geojson_compat(fichiers, sortie):
    """Compat avec l'ancienne signature : retourne juste le Path (pas la bbox).

    ConservÃ© pour les sites qui n'ont pas besoin de la bbox (ex.
    main_wfs/main_decouper). PrÃ©fÃ©rer fusionner_geojson() directement quand
    on veut Ã©viter une 2e passe pour calculer la bbox.
    """
    res = fusionner_geojson(fichiers, sortie)
    if res is None or res == (None, None):
        return None
    chemin, _bbox = res
    return chemin


def main_fusionner():
    """Point d'entrÃ©e mode --fusionner."""
    import argparse

    t_debut = time.time()
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --fusionner",
        description="Fusionne plusieurs fichiers GeoJSON en un seul.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python lidar2map.py --fusionner \\
      --source cadastre.geojson cours_eau.geojson osm_gareoult.geojson \\
      --sortie gareoult_fusion.geojson

  python lidar2map.py --fusionner \\
      --source ign_vecteur/gareoult_*.geojson \\
      --sortie gareoult_complet.geojson
        """
    )
    parser.add_argument("--fusionner", action="store_true")
    parser.add_argument("--source", nargs="+", metavar="FICHIER",
                        required=True,
                        help="Fichiers GeoJSON Ã  fusionner (glob acceptÃ©)")
    parser.add_argument("--sortie", metavar="FICHIER", default=None,
                        help="Fichier de sortie .geojson")
    parser.add_argument("--dossier", metavar="CHEMIN", default=None)
    parser.add_argument("--no-gz", action="store_true",
                        help="Sortie .geojson non compressÃ© (dÃ©faut : .geojson.gz)")
    parser.add_argument("--formats-fichier", nargs="+", default=["gz"],
                        metavar="FMT", help="gz geojson map")
    parser.add_argument("--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Epsilon Douglas-Peucker en mÃ¨tres (dÃ©faut: auto depuis surface).")
    parser.add_argument("--oui", action="store_true")

    args, _ = parser.parse_known_args()  # ignorer --zone-* et autres args globaux

    # Crash-safe : sauver l'entrÃ©e 'en cours' AVANT toute opÃ©ration longue.
    _historique_debut()

    # RÃ©soudre les globs Ã©ventuels
    import glob as _glob
    fichiers = []
    for pattern in args.source:
        matches = _glob.glob(pattern)
        if matches:
            fichiers.extend(sorted(matches))
        else:
            fichiers.append(pattern)  # sera signalÃ© introuvable Ã  la fusion

    if not fichiers:
        print("  ERREUR : aucun fichier source trouvÃ©")
        sys.exit(1)

    # Sortie par dÃ©faut
    if args.sortie:
        sortie = Path(args.sortie)
    else:
        if args.dossier:
            dossier = Path(args.dossier)
        else:
            # Utiliser le dossier du premier fichier source comme base
            dossier = Path(fichiers[0]).parent
        # Nom dÃ©rivÃ© du premier fichier source
        base = Path(fichiers[0]).stem.split(".")[0]  # gÃ¨re .geojson.gz
        ext_out = ".geojson" if getattr(args, "no_gz", False) else ".geojson.gz"
        sortie = dossier / f"{base}_fusion{ext_out}"

    print("=" * 52)
    print("  Fusion GeoJSON")
    print("=" * 52)
    for f in fichiers:
        print(f"  + {f}")
    print(f"  â†’ {sortie}")

    if not args.oui:
        rep = input("\n  Lancer ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    fusion_result = fusionner_geojson(fichiers, sortie)
    if fusion_result and fusion_result[0] is not None:
        result, bbox = fusion_result
        fmts = [f.lower() for f in args.formats_fichier]
        # GÃ©nÃ©rer le .map Mapsforge si demandÃ©
        if "map" in fmts:
            nom_zone = sortie.stem.split(".")[0]
            dossier_sortie = sortie.parent
            try:
                # bbox arrive dÃ©jÃ  calculÃ©e par fusionner_geojson â€” pas de relecture.
                if getattr(args, 'simplification_vecteur', None):
                    _eps_deg = args.simplification_vecteur / 111_000.0
                    print(f"  Simplification vecteur : epsilon={args.simplification_vecteur:.1f} m (forcÃ©)")
                elif bbox:
                    _surf = (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]) * (111_000**2) / 1e6
                    _eps_deg = _epsilon_depuis_surface_km2(_surf)
                    print(f"  Simplification vecteur : epsilon={_eps_deg*111000:.0f} m (auto, surfaceâ‰ˆ{_surf:.0f} kmÂ²)")
                else:
                    _eps_deg = _IGN_SIMPLIFY_EPSILON
                generer_map_depuis_geojson_ign(result, dossier_sortie, nom_zone,
                                               bbox_wgs84=bbox, ecraser=True,
                                               epsilon=_eps_deg)
            except Exception as _e:
                print(f"  ERREUR gÃ©nÃ©ration .map : {_e}")
        print(f"\n  TerminÃ© en {_hms(int(time.time()-t_debut))}")
    _historique_depuis_argv(int(time.time()-t_debut))


# â”€â”€ Persistence d'historique 'crash-safe' â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Sauver l'entrÃ©e AU DÃ‰BUT du run garantit qu'elle existe mÃªme si le process
# crashe (NameError, SIGKILL, panne courant, Ctrl+C brutal). Ã€ la fin, on
# UPDATE cette entrÃ©e pour ajouter durÃ©e + statut. Identifiant : run_id
# (timestamp ms + pid, hÃ©ritÃ© via env LIDAR2MAP_HIST_RUN_ID en mode GUI).
_HIST_RUN_ID    = ""
_HIST_T_DEBUT   = 0.0
_HIST_FINALIZED = False


def _hist_disabled() -> bool:
    """DÃ©sactivÃ© pendant le smoketest (pollue de 5+ entrÃ©es par run)."""
    return bool(os.environ.get("LIDAR2MAP_SKIP_HIST"))


def _cfg_depuis_argv() -> dict:
    """Construit le cfg JSON depuis sys.argv. ClÃ©s attendues par loadConfig() JS."""
    argv = sys.argv[1:]

    def _arg(flag, default=""):
        try: return argv[argv.index(flag) + 1]
        except (ValueError, IndexError): return default

    def _arg_int(flag, default=0):
        v = _arg(flag, "")
        try: return int(v) if v else default
        except ValueError: return default

    def _arg_float(flag, default=0.0):
        v = _arg(flag, "")
        try: return float(v) if v else default
        except ValueError: return default

    def _flag(flag): return flag in argv

    def _args_after(flag):
        """Retourne tous les args aprÃ¨s flag jusqu'au prochain -- ou fin."""
        try:
            i = argv.index(flag) + 1
        except ValueError:
            return []
        result = []
        while i < len(argv) and not argv[i].startswith("--"):
            result.append(argv[i])
            i += 1
        return result

    t = ("lidar"   if "--ignlidar"   in argv else
         "scan"    if "--ignraster"  in argv else
         "vecteur" if "--ignvecteur" in argv else
         "osm"     if "--osm"        in argv else
         "fusion"  if "--fusionner"  in argv else
         "decoupe" if "--decouper"   in argv else "lidar")

    mode = ("dep"  if "--zone-departement" in argv else
            "gps"  if "--zone-gps"         in argv else
            "bbox" if "--zone-bbox"         in argv else "ville")

    fmts = _args_after("--formats-fichier")
    ombs = _args_after("--ombrages")

    return {
        # Zone
        "type":    t,
        "mode":    mode,
        "nom":     _arg("--zone-nom"),
        "dossier": _arg("--dossier"),
        "dep":     _arg("--zone-departement"),
        "ville":   _arg("--zone-ville"),
        "gps":     _arg("--zone-gps"),
        "bbox":    _arg("--zone-bbox"),
        "rayon":   _arg_float("--zone-rayon", 10.0),
        # LiDAR
        "tel":           _flag("--telechargement"),
        "comp":          _flag("--telechargement-compresser"),
        "ecraser_tel":   _flag("--telechargement-ecraser"),
        "workers_l":     _arg_int("--workers", 8),
        "dossier_dalles":_arg("--dossier-dalles"),
        "no_omb":        bool(ombs) or _flag("--ombrages"),
        "ombrages":      ombs,
        "elevation":     _arg_int("--ombrages-elevation", 25),
        "sweep_horizon": _flag("--sweep-horizon"),
        "ecraser_omb":   _flag("--ombrages-ecraser"),
        "mbtiles_l":     "mbtiles" in fmts,
        "rmap":          "rmap"    in fmts,
        "sqlitedb":      "sqlitedb" in fmts,
        "zoom_min_l":    _arg_int("--zoom-min", 8),
        "zoom_max_l":    _arg_int("--zoom-max", 18),
        "qualite_l":     _arg_int("--qualite-image", 85),
        "ecraser_mbt":   _flag("--tuiles-ecraser"),
        "cols_decoupe":  _arg_int("--cols-decoupe", 1),
        "rows_decoupe":  _arg_int("--rows-decoupe", 1),
        "rayon_decoupe_l": _arg_float("--rayon-decoupe", 0.0),
        "nettoyage":     _flag("--nettoyage"),
        # IGN Raster
        "couche":        _arg("--couche"),
        "zoom_min_s":    _arg_int("--zoom-min", 12),
        "zoom_max_s":    _arg_int("--zoom-max", 16),
        "mbtiles_s":     "mbtiles" in fmts,
        "rmap_s":        "rmap"    in fmts,
        "sqlitedb_s":    "sqlitedb" in fmts,
        "qualite_s":     _arg_int("--qualite-image", 85),
        "workers_s":     _arg_int("--workers", 8),
        # OSM
        "osm_tags_sel":  _args_after("--couche") if t == "osm" else [],
        "workers_osm":   _arg_int("--workers", 4),
        # IGN Vectoriel
        "wfs_couches_sel": _args_after("--couche") if t == "vecteur" else [],
        "workers_v":     _arg_int("--workers", 4),
        # Argv complet pour debug
        "argv":    " ".join(argv),
    }


def _historique_debut() -> str:
    """
    Sauvegarde une entrÃ©e 'en cours' AU DÃ‰BUT du traitement.

    But : si le process crashe (NameError, OSError, SIGKILL, panne courant,
    Ctrl+C brutal), l'entrÃ©e reste avec statut='en cours' â†’ on voit les
    paramÃ¨tres exacts du run cassÃ© pour debug.

    Si LIDAR2MAP_HIST_RUN_ID est dÃ©fini (cas GUI : id gÃ©nÃ©rÃ© cÃ´tÃ© GUI pour
    pouvoir mettre Ã  jour l'entrÃ©e plus tard depuis poll_log), rÃ©utilise cet
    id. Sinon, gÃ©nÃ¨re un nouvel id horodatÃ© + pid.
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
        # Ne JAMAIS planter le pipeline parce que l'historique a Ã©chouÃ©.
        print(f"  Historique 'en cours' non sauvegardÃ© : {e}", flush=True)
    return run_id


def _historique_fin_crash():
    """
    Finalise l'entrÃ©e 'en cours' avec statut='ko' depuis le handler crash
    de __main__. No-op si pas de debut, ou si dÃ©jÃ  finalisÃ© (succÃ¨s rÃ©cent
    dans une boucle multi-dÃ©partement par exemple).
    """
    if not _HIST_RUN_ID or _HIST_FINALIZED or _hist_disabled():
        return
    duree = int(time.time() - _HIST_T_DEBUT) if _HIST_T_DEBUT else 0
    try:
        _sauver_historique(_cfg_depuis_argv(), duree, "",
                           run_id=_HIST_RUN_ID, statut="ko")
    except Exception as e:
        print(f"  Historique 'ko' non sauvegardÃ© : {e}", flush=True)


def _historique_depuis_argv(duree_s: int, dossier_resultat: str = "",
                             run_id: str = "", statut: str = "ok"):
    """
    Sauvegarde finale depuis CLI. Si run_id non fourni, utilise _HIST_RUN_ID
    posÃ© par _historique_debut() au dÃ©but du traitement (update de l'entrÃ©e
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
_HISTORIQUE_MAX  = 50   # nombre max d'entrÃ©es conservÃ©es


def _sauver_historique(cfg: dict, duree_s: int, dossier_resultat: str = "",
                       run_id: str = "", statut: str = "ok"):
    """
    Sauvegarde une entrÃ©e d'historique. Conserve _HISTORIQUE_MAX entrÃ©es.

    SÃ©mantique :
      - Si run_id correspond Ã  une entrÃ©e existante : UPDATE en place,
        date de dÃ©but prÃ©servÃ©e, date_fin posÃ©e.
      - Sinon : INSERT en tÃªte.

    statut :
      - 'en cours' : sauvegarde au DÃ‰BUT du traitement. Reste lÃ  si le
        process crashe â†’ diagnostique facile.
      - 'ok' / 'ko' : sauvegarde finale (succÃ¨s / Ã©chec).
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
    # Update si entrÃ©e existante (mÃªme run_id), sinon insert en tÃªte.
    idx = -1
    if run_id:
        for i, e in enumerate(historique):
            if e.get("id") == run_id:
                idx = i
                break
    if idx >= 0:
        # PrÃ©server la date de dÃ©but ; poser date_fin si finalisation.
        entree["date"] = historique[idx].get("date", now_str)
        if statut in ("ok", "ko"):
            entree["date_fin"] = now_str
        historique[idx] = entree
    else:
        historique.insert(0, entree)
    historique = historique[:_HISTORIQUE_MAX]
    try:
        _ecrire_json_atomique(_HISTORIQUE_PATH, historique, indent=2)
        # Log discret au dÃ©but (l'utilisateur n'a pas besoin de savoir), plus
        # explicite Ã  la fin pour confirmer la sauvegarde finale.
        if statut == "en cours":
            print(f"  Historique : entrÃ©e '{entree['id']}' (en cours)", flush=True)
        else:
            print(f"  Historique sauvegardÃ© : {_HISTORIQUE_PATH}  ({len(historique)} entrÃ©es)", flush=True)
    except Exception as e:
        print(f"  Historique non sauvegardÃ© : {e}", flush=True)


def _lire_historique() -> list:
    """Retourne la liste des entrÃ©es d'historique (liste vide si absent/corrompu)."""
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
    GUI PyWebView â€” fenÃªtre native affichant un formulaire HTML/CSS/JS.
    Communication bidirectionnelle via l'objet Api exposÃ© Ã  JavaScript.
    """
    import threading, queue

    # â”€â”€ SÃ©lection du backend GUI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # macOS : forcer le backend Qt (PyQt6) avant l'import de webview.
    # Le backend Cocoa (dÃ©faut) plante en session SSH mÃªme avec VNC actif,
    # car NSScreen.mainScreen() ne voit pas la session VNC depuis SSH.
    # Qt se connecte directement au serveur de fenÃªtres macOS et fonctionne.
    # PYWEBVIEW_GUI doit Ãªtre posÃ© AVANT import webview (lu Ã  l'import).
    if platform.system() == "Darwin":
        os.environ["PYWEBVIEW_GUI"] = "qt"

    try:
        import webview
    except ImportError:
        print("  PyWebView absent â€” installation automatique...")
        # PyWebView nÃ©cessite un backend natif :
        #   Windows : WebView2 (prÃ©installÃ© Win10+)         â†’ "pywebview"
        #   macOS   : Cocoa WebKit (prÃ©installÃ©)            â†’ "pywebview"
        #   Linux   : QtWebEngine via PyQt6 (recommandÃ©)    â†’ "pywebview[qt6]"
        #             alternative : GTK via pygobject       â†’ "pywebview[gtk]"
        #
        # Sur Linux, sans extra, pywebview lÃ¨ve RuntimeError au dÃ©marrage
        # ("No suitable backend found"). On utilise [qt6] (et non [qt] qui
        # fait du PyQt5 dans pywebview < 6.0) pour rester cohÃ©rent avec
        # _installer_deps + lidar2map_mac.spec qui sont sur PyQt6.
        # [gtk] nÃ©cessiterait des paquets systÃ¨me (libgirepository1.0-dev,
        # gir1.2-webkit2-4.0â€¦) et n'est donc pas le dÃ©faut.
        if LINUX:
            pkg = "pywebview[qt6]"
        else:
            pkg = "pywebview"
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=True)
        except subprocess.CalledProcessError:
            # Fallback : tenter sans --break-system-packages (envs Conda/venv)
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                           check=True)
        try:
            import webview
        except ImportError:
            if LINUX:
                print("  ERREUR : pywebview installÃ© mais sans backend fonctionnel.")
                print("  Sur Linux, installez aussi les paquets systÃ¨me requis :")
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

    # â”€â”€ Table zooms pour la sÃ©lection de couche â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # NB : _lire_zoom_limites_wmts() interroge GetCapabilities au runtime et
    # corrige automatiquement ces valeurs si elles diffÃ¨rent de la rÃ©alitÃ©.
    # Cette table sert seulement Ã  prÃ©-remplir la GUI.
    _ZOOMS_GUI = {
        "scan25": (8, 16), "scan25tour": (8, 16), "scan100": (6, 14),
        "scanoaci": (6, 15), "planign": (6, 18), "etatmajor40": (6, 15),
        "etatmajor10": (8, 16), "pentes": (6, 14), "ortho": (10, 20),
        "cadastre": (12, 19), "ombrage": (6, 14),
        # Orthos historiques mÃ©tropole (rÃ©solution dÃ©gradÃ©e vs ortho actuelle)
        "ortho_1950": (10, 18), "ortho_1965": (10, 18), "ortho_1980": (10, 18),
        # Infrarouge couleur (couverture identique Ã  ortho)
        "ortho_irc": (10, 19),
        # Satellite : rÃ©solution plus faible que aÃ©rien â†’ zoom max plus bas
        "pleiades": (10, 19), "spot": (8, 16),
        # EDUGEO : couverture restreinte aux centres urbains, zooms Ã©levÃ©s
        "edugeo_marseille_1969": (12, 18), "edugeo_marseille_1980": (12, 18),
        "edugeo_marseille_1987": (12, 18), "edugeo_marseille_1988": (12, 18),
        "edugeo_marseille_2010": (12, 18), "edugeo_toulon_1972": (12, 18),
    }

    # â”€â”€ DonnÃ©es statiques exposÃ©es au formulaire â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _COUCHES_PRIVEES = {"scan25", "scan25tour", "scan100", "scanoaci"}
    _COUCHES_DATA = [
        {"code": k,
         "label": f"{'âš  [PRO] ' if k in _COUCHES_PRIVEES else ''}{k}  ({v[0]})",
         "zoom_min":  _ZOOMS_GUI.get(k, (8, 16))[0],
         "zoom_max":  _ZOOMS_GUI.get(k, (8, 16))[1],
         "restreinte": k in _COUCHES_PRIVEES}
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
        {"tag": "building=*",             "label": "BÃ¢timents"},
        {"tag": "historic=*",             "label": "Historique"},
    ]

    # â”€â”€ Classe API exposÃ©e Ã  JavaScript â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _classify_err(line: str) -> bool:
        """True si la ligne ressemble Ã  une erreur (ERREUR/Error/Traceback/argparse).

        UtilisÃ© par les 3 sites de drain stdout du subprocess pour rester
        synchronisÃ©s â€” sans cette factorisation, une Ã©volution du heuristique
        ne se propageait qu'Ã  un site sur trois.
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
            self.window     = None  # injectÃ© par pywebview au dÃ©marrage
            # Lock pour les attributs partagÃ©s entre le thread d'Ã©coute du
            # subprocess (run) et le thread main (poll_log, get_last_error).
            # Le GIL protÃ¨ge les opÃ©rations atomiques ; le lock protÃ¨ge la
            # cohÃ©rence multi-attributs (ex: lire _retcode et _modal_error_msg
            # ensemble doit voir l'Ã©tat stable d'un mÃªme moment).
            self._lock = threading.Lock()
            self._err_lines       = []
            self._tail_lines      = []
            self._modal_error_msg = ""

        # â”€â”€ DonnÃ©es initiales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def get_init_data(self):
            return {
                "couches":    _COUCHES_DATA,
                "wfs":        _WFS_DATA,
                "osm_tags":   _OSM_TAGS_DATA,
                "apikey_def": APIKEY_DEFAUT,
                "historique": _lire_historique(),
                "providers":  _discover_providers(),
                "active_provider": PROVIDER.CODE,
            }

        def get_historique(self):
            """Retourne la liste historique â€” appelable depuis JS Ã  tout moment."""
            return _lire_historique()

        def clear_historique(self):
            """Vide intÃ©gralement l'historique (action destructive â€” la confirmation
            est gÃ©rÃ©e cÃ´tÃ© JS via confirm() avant l'appel)."""
            try:
                _ecrire_json_atomique(_HISTORIQUE_PATH, [], indent=2)
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        # â”€â”€ AutocomplÃ©tion ville (proxy BAN pour FR, Nominatim sinon) â”€â”€â”€â”€
        # CÃ´tÃ© JS, fetch() depuis NavigateToString a un Origin "null" que
        # WebView2 traite mal vis-Ã -vis du CORS â€” on relaie ici en Python.
        # FR : Geoplateforme BAN (rapide, prÃ©cis pour communes franÃ§aises)
        # Hors FR : Nominatim avec countrycodes=<pays> pour scoper Ã  un pays
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

        # â”€â”€ Dialogs fichiers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Construction de la commande CLI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def _build_cmd(self, cfg):
            # Frozen : l'exe est self-launching, on n'y prÃ©pose pas sys.executable.
            cmd = ([str(SCRIPT)] if getattr(sys, "frozen", False)
                   else [sys.executable, str(SCRIPT)])
            t = cfg.get("type", "lidar")

            # Provider (multi-pays) â€” propagÃ© au subprocess
            if cfg.get("provider") and cfg["provider"] != PROVIDER.CODE:
                cmd += ["--provider", cfg["provider"]]
            # ClÃ© API LiDAR (us-3dep / OpenTopography). Champ saisi dans la GUI
            # Ã  cÃ´tÃ© de la dropdown provider, visible quand APIKEY_REQUISE=True.
            if cfg.get("lidar_apikey"):
                cmd += ["--apikey", cfg["lidar_apikey"]]

            # Zone (pas pour fusion / dÃ©coupe)
            if t != "fusion" and t != "decoupe":
                mode = cfg.get("mode", "ville")
                if mode == "ville"  and cfg.get("ville"):
                    cmd += ["--zone-ville", cfg["ville"]]
                elif mode == "gps"  and cfg.get("gps"):
                    cmd += ["--zone-gps", cfg["gps"]]
                elif mode == "bbox" and cfg.get("bbox"):
                    cmd += ["--zone-bbox", cfg["bbox"]]
                elif mode == "dep"  and cfg.get("dep"):
                    cmd += ["--zone-departement", cfg["dep"]]
                if cfg.get("rayon") is not None and cfg["rayon"] != "":
                    cmd += ["--zone-rayon", str(cfg["rayon"])]
                if cfg.get("nom"):
                    cmd += ["--zone-nom", cfg["nom"]]
                if cfg.get("dossier"):
                    cmd += ["--dossier", cfg["dossier"]]

            # â”€â”€ LiDAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if t == "lidar":
                cmd.append("--ignlidar")
                if cfg.get("tel"):      cmd.append("--telechargement")
                if cfg.get("comp"):     cmd.append("--telechargement-compresser")
                if cfg.get("ecraser_tel"): cmd.append("--telechargement-ecraser")
                if cfg.get("dossier_dalles"):
                    cmd += ["--dossier-dalles", cfg["dossier_dalles"]]
                if cfg.get("workers_l"):
                    cmd += ["--workers", str(cfg["workers_l"])]
                if cfg.get("no_omb"):
                    ombs = cfg.get("ombrages", [])
                    if ombs: cmd += ["--ombrages"] + ombs
                    if cfg.get("elevation"):
                        cmd += ["--ombrages-elevation", str(cfg["elevation"])]
                    if cfg.get("ecraser_omb"): cmd.append("--ombrages-ecraser")
                    if cfg.get("sweep_horizon"): cmd.append("--sweep-horizon")
                fmts = []
                if cfg.get("mbtiles_l"): fmts.append("mbtiles")
                if cfg.get("rmap"):      fmts.append("rmap")
                if cfg.get("sqlitedb"):  fmts.append("sqlitedb")
                if fmts:
                    cmd += ["--formats-fichier"] + fmts
                    if cfg.get("zoom_min_l"): cmd += ["--zoom-min", str(cfg["zoom_min_l"])]
                    if cfg.get("zoom_max_l"): cmd += ["--zoom-max", str(cfg["zoom_max_l"])]
                    if cfg.get("fmt_l") and cfg["fmt_l"] != "auto":
                        cmd += ["--formats-image", cfg["fmt_l"]]
                    if cfg.get("qualite_l"): cmd += ["--qualite-image", str(cfg["qualite_l"])]
                    if cfg.get("ecraser_mbt"): cmd.append("--tuiles-ecraser")
                    _cols = cfg.get("cols_decoupe", 1) or 1
                    _rows = cfg.get("rows_decoupe", 1) or 1
                    if _cols > 1 and _rows > 1:
                        cmd += ["--cols-decoupe", str(_cols),
                                "--rows-decoupe", str(_rows)]
                    elif cfg.get("rayon_decoupe_l", 0) > 0:
                        cmd += ["--rayon-decoupe", str(cfg["rayon_decoupe_l"])]
                    if cfg.get("nettoyage"): cmd.append("--nettoyage")
                if cfg.get("purger_inv"):  cmd.append("--dalles-purger-invalides")
                if cfg.get("purger_zone"): cmd.append("--dalles-purger-hors-zone")

            # â”€â”€ IGN Raster â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif t == "scan":
                cmd.append("--ignraster")
                couche = cfg.get("couche", "scan25")
                cmd += ["--couche", couche]
                if cfg.get("apikey"): cmd += ["--apikey", cfg["apikey"]]
                if cfg.get("tel_s"):
                    if cfg.get("workers_s"):
                        cmd += ["--workers", str(cfg["workers_s"])]
                    if cfg.get("ecraser_tel_s"): cmd.append("--telechargement-ecraser")
                if cfg.get("tuiles_s"):
                    fmts = []
                    if cfg.get("mbtiles_s"): fmts.append("mbtiles")
                    if cfg.get("rmap_s"):    fmts.append("rmap")
                    if cfg.get("sqlitedb_s"):fmts.append("sqlitedb")
                    if fmts: cmd += ["--formats-fichier"] + fmts
                    cmd += ["--zoom-min", str(cfg.get("zoom_min_s", 12)),
                            "--zoom-max", str(cfg.get("zoom_max_s", 16))]
                    if cfg.get("fmt_s") and cfg["fmt_s"] != "auto":
                        cmd += ["--formats-image", cfg["fmt_s"]]
                    if cfg.get("qualite_s"):
                        cmd += ["--qualite-image", str(cfg["qualite_s"])]
                    if cfg.get("ecraser_tuil_s"): cmd.append("--tuiles-ecraser")
                    _cols = cfg.get("cols_decoupe_s", 0) or 0
                    _rows = cfg.get("rows_decoupe_s", 0) or 0
                    if _cols > 0 and _rows > 0:
                        cmd += ["--cols-decoupe", str(_cols),
                                "--rows-decoupe", str(_rows)]
                    elif cfg.get("rayon_decoupe_s", 0) > 0:
                        cmd += ["--rayon-decoupe", str(cfg["rayon_decoupe_s"])]
                    if cfg.get("nettoyage"): cmd.append("--nettoyage")

            # â”€â”€ OSM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif t == "osm":
                cmd.append("--osm")
                tags = cfg.get("osm_tags_sel", [])
                if tags: cmd += ["--couche"] + tags
                if cfg.get("tel_osm"):
                    if cfg.get("workers_osm", 4) != 4: cmd += ["--workers", str(cfg["workers_osm"])]
                    if cfg.get("ecraser_tel_osm"): cmd.append("--telechargement-ecraser")
                if cfg.get("tuiles_osm"):
                    fmts = []
                    if cfg.get("map"):        fmts.append("map")
                    if cfg.get("osm_geojson"):     fmts.append("gz")
                    if cfg.get("osm_geojson_raw"): fmts.append("geojson")
                    if fmts: cmd += ["--formats-fichier"] + fmts
                    if cfg.get("ecraser_tuil_osm"): cmd.append("--tuiles-ecraser")

            # â”€â”€ IGN Vectoriel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif t == "vecteur":
                cmd.append("--ignvecteur")
                couches = cfg.get("wfs_couches_sel", [])
                if couches: cmd += ["--couche"] + couches
                if cfg.get("tel_v"):
                    cmd += ["--workers", str(cfg.get("workers_v", 4))]
                    if cfg.get("ecraser_tel_v"): cmd.append("--telechargement-ecraser")
                fmts = []
                if cfg.get("fusion_gz", True):  fmts.append("gz")
                if cfg.get("fusion_gz_raw"):     fmts.append("geojson")
                if not fmts: fmts = ["gz"]  # dÃ©faut si rien cochÃ©
                if cfg.get("tuiles_v"): fmts.append("map")
                cmd += ["--formats-fichier"] + fmts
                if cfg.get("tuiles_v") and cfg.get("ecraser_tuil_v"):
                    cmd.append("--tuiles-ecraser")
                if cfg.get("tuiles_v") and cfg.get("simplif_v"):
                    cmd += ["--simplification-vecteur", str(cfg["simplif_v"])]

            # â”€â”€ Fusion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif t == "fusion":
                cmd.append("--fusionner")
                fichiers = cfg.get("fusion_fichiers", [])
                if fichiers: cmd += ["--source"] + fichiers
                nom = cfg.get("nom", "fusion") or "fusion"
                # Extension du GeoJSON intermÃ©diaire
                ext = ".geojson" if cfg.get("fusion_gz2_raw") and not cfg.get("fusion_gz2", True) else ".geojson.gz"
                # Dossier de sortie automatique : <Projets>/<nom>/fusion
                base = Path(cfg["dossier"]) if cfg.get("dossier") else DOSSIER_TRAVAIL / "Projets"
                sortie_dir = base / nom / "fusion"
                cmd += ["--sortie", str(sortie_dir / f"{nom}_fusion{ext}")]
                fmts = []
                if cfg.get("fusion_gz2", True):   fmts.append("gz")
                if cfg.get("fusion_gz2_raw"):      fmts.append("geojson")
                if cfg.get("fusion_map"):          fmts.append("map")
                if not fmts: fmts = ["gz"]
                cmd += ["--formats-fichier"] + fmts
                if cfg.get("fusion_map") and cfg.get("simplif_fusion"):
                    cmd += ["--simplification-vecteur", str(cfg["simplif_fusion"])]

            # â”€â”€ DÃ©coupage raster (Ã  posteriori) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif t == "decoupe":
                cmd.append("--decouper")
                src_d = cfg.get("source_decoupe", "")
                if src_d: cmd += ["--source", src_d]
                if cfg.get("cols_decoupe_d", 0) > 0 and cfg.get("rows_decoupe_d", 0) > 0:
                    cmd += ["--cols", str(cfg["cols_decoupe_d"]),
                            "--rows", str(cfg["rows_decoupe_d"])]
                elif cfg.get("rayon_decoupe_d", 0) > 0:
                    cmd += ["--rayon-decoupe", str(cfg["rayon_decoupe_d"])]
                fmts_d = []
                if cfg.get("mbtiles_d"):  fmts_d.append("mbtiles")
                if cfg.get("rmap_d"):     fmts_d.append("rmap")
                if cfg.get("sqlitedb_d"): fmts_d.append("sqlitedb")
                if fmts_d: cmd += ["--formats-fichier"] + fmts_d
                if cfg.get("ecraser_d"):  cmd.append("--tuiles-ecraser")


            cmd.append("--oui")
            return cmd

        # â”€â”€ Lancement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def launch(self, cfg):
            if self._process and self._process.poll() is None:
                return {"error": "Un processus est dÃ©jÃ  en cours."}
            cmd = self._build_cmd(cfg)
            self._done = False
            self._retcode = None
            self._t_launch = time.time()
            self._cfg_launch = cfg
            # run_id partagÃ© GUI â†” subprocess via env LIDAR2MAP_HIST_RUN_ID :
            # le subprocess sauve 'en cours' au dÃ©but (crash-safe), puis 'ok'/'ko'
            # Ã  la fin. poll_log cÃ´tÃ© GUI peut alors mettre Ã  jour la MÃŠME entrÃ©e
            # avec le cfg complet (qui contient des champs absents de l'argv :
            # tel_v, ecraser_tel_v, etc.) pour rappel exact via loadConfig().
            self._hist_run_id = f"{int(time.time()*1000)}-{os.getpid()}-gui"
            self._hist_saved  = False
            # Calculer le dossier rÃ©sultat attendu
            t    = cfg.get("type", "lidar")
            nom  = cfg.get("nom", "")
            # Le pipeline CLI normalise le nom (slug ASCII minuscule) pour le
            # nom de dossier : "GarÃ©oult" â†’ "gareoult". Sans cette normalisation
            # ici, open_folder() pointerait vers un chemin inexistant.
            nom_slug = normaliser_nom(nom) if nom else ""
            base = Path(cfg["dossier"]) if cfg.get("dossier") else DOSSIER_TRAVAIL / "Projets"
            # Le subprocess utilise --provider <code> â†’ ecrit dans lidar/<country>.
            # On reconstruit le meme path ici sinon open_folder pointe ailleurs.
            _cfg_provider = cfg.get("provider", PROVIDER.CODE)
            _cfg_country = "fr"
            for _p in _discover_providers():
                if _p["code"] == _cfg_provider:
                    _cfg_country = _p.get("country", "fr")
                    break
            _lidar_subdir_cfg = f"lidar/{_cfg_country}"
            _type_dir = {"lidar":_lidar_subdir_cfg, "scan":"ign_raster", "osm":"osm_vecteur",
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
                    # SUR la mÃªme entrÃ©e que celle finalisÃ©e par poll_log cÃ´tÃ© GUI.
                    env["LIDAR2MAP_HIST_RUN_ID"] = self._hist_run_id
                    # Forcer UTF-8 sur stdout/stderr du child Python.
                    # Sans Ã§a, sur Windows le child utilise cp850 ou cp1252 par
                    # dÃ©faut, et les caractÃ¨res accentuÃ©s (Ã©, â†’, âš , âœ“, etc.)
                    # arrivent corrompus dans le pipe. Ã‡a casse Ã  la fois le
                    # log lisible cÃ´tÃ© GUI ET la dÃ©tection regex de mots-clÃ©s
                    # comme "ERREUR" qui contient un Ã‰ (devient un ? si dÃ©codÃ©
                    # en cp850 puis lu en utf-8).
                    env["PYTHONIOENCODING"] = "utf-8"
                    # CrÃ©er un nouveau groupe de processus pour pouvoir tuer toute la hiÃ©rarchie
                    if WINDOWS:
                        # Note : CREATE_NEW_PROCESS_GROUP est nÃ©cessaire pour que
                        # Ctrl+C puisse tuer le child et ses descendants. Mais
                        # sur certaines configurations Windows + WebView2, cette
                        # flag semble causer un blocage du pipe stdout â€” les
                        # donnÃ©es restent dans le buffer du child et n'arrivent
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
                    # Lock pour cohÃ©rence avec poll_log / get_last_error.
                    with self._lock:
                        self._err_lines  = []
                        self._tail_lines = []
                    for chunk in iter(lambda: self._process.stdout.read(64), b""):
                        for ch in chunk.decode("utf-8", errors="replace"):
                            if ch == "\r":
                                # Sur Windows, les print() Python terminent les
                                # lignes par \r\n. Ne traiter le \r comme une
                                # mise Ã  jour de barre de progression QUE si
                                # le buffer contient un pourcentage. Sinon,
                                # c'est juste un CR avant un LF â€” on l'ignore
                                # et le \n qui suit dÃ©clenchera l'envoi normal
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
                                        # Buffer circulaire des 10 derniÃ¨res lignes
                                        # non-vides : fallback si retcodeâ‰ 0 sans
                                        # ligne marquÃ©e "ERREUR".
                                        self._tail_lines.append(buf.strip())
                                        if len(self._tail_lines) > 10:
                                            self._tail_lines.pop(0)
                                    self._log_queue.put({"line": buf + "\n", "tag": tag})
                                buf = ""
                            else:
                                buf += ch
                    # Drain final : la boucle for-chunk a vu EOF, mais le buffer
                    # interne `buf` peut contenir une derniÃ¨re ligne sans \n
                    # final (ex : print() Python sans flush avant sys.exit).
                    # Sans Ã§a, ces lignes sont perdues sur Windows quand le
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
                    # encore des donnÃ©es aprÃ¨s que le child ait exit. Sans ce
                    # drain, les derniÃ¨res lignes (souvent les plus importantes :
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
                        # En cas d'erreur de lecture finale (pipe dÃ©jÃ  fermÃ©),
                        # on continue silencieusement avec ce qu'on a.
                        pass

                    sym = "âœ“" if self._retcode == 0 else "âœ—"
                    self._log_queue.put({"line": f"\n{sym} TerminÃ© (code {self._retcode})\n",
                                         "tag": "ok" if self._retcode == 0 else "err"})
                    # Si Ã©chec : prÃ©parer le message modal rÃ©capitulatif.
                    # PrioritÃ© 1 : lignes marquÃ©es comme "ERREUR" (si dÃ©tectÃ©es).
                    # PrioritÃ© 2 : 10 derniÃ¨res lignes non-vides (fallback gÃ©nÃ©rique
                    # pour les cas oÃ¹ sys.exit(1) suit un print() libre que le filtre
                    # n'a pas reconnu comme erreur).
                    # On le stocke Ã  la fois dans la queue ET sur l'instance, car
                    # les dictionnaires complexes peuvent Ãªtre mal sÃ©rialisÃ©s par
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
                                    f"Le traitement a Ã©chouÃ© (code {self._retcode})",
                                    "Aucun message d'erreur n'a Ã©tÃ© capturÃ©.",
                                    "VÃ©rifiez le panneau de log pour les dÃ©tails.",
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
                    # Marquer la durÃ©e pour la sauvegarde historique (faite
                    # dans poll_log). MesurÃ© dans tous les cas â€” y compris
                    # Ã©chec â€” pour que l'entrÃ©e 'ko' soit horodatÃ©e correctement.
                    self._duree_run = int(time.time() - getattr(self, "_t_launch", time.time()))
                except Exception as e:
                    self._log_queue.put({"line": f"\nErreur : {e}\n", "tag": "err"})
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
                self._log_queue.put({"line": "\nâš  ArrÃªtÃ©\n", "tag": "err"})
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
            """Retourne le message d'erreur du dernier run (ou chaÃ®ne vide).

            Permet au JS de rÃ©cupÃ©rer ce message **aprÃ¨s** avoir constatÃ©
            que `done=True && code!=0`, sans dÃ©pendre de la transmission par
            la queue (que pywebview/WebView2 sÃ©rialise parfois mal pour les
            dicts Ã  plusieurs clÃ©s).

            Lecture sous lock pour voir un snapshot cohÃ©rent (msg + retcode
            Ã©crits ensemble dans run()).
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
            # Sauvegarde finale de l'historique cÃ´tÃ© GUI (thread-safe via
            # poll_log). MET Ã€ JOUR l'entrÃ©e 'en cours' crÃ©Ã©e par le subprocess
            # via le mÃªme run_id (env LIDAR2MAP_HIST_RUN_ID). Sauvegarde sur
            # succÃ¨s ET Ã©chec : sans Ã§a, un crash du pipeline laissait l'entrÃ©e
            # 'en cours' indÃ©finiment.
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
                    items.append({"line": f"  Historique sauvegardÃ© : {_HISTORIQUE_PATH}\n",
                                  "tag": "ok"})
                except Exception as _he:
                    items.append({"line": f"  ERREUR historique : {_he}\n", "tag": "err"})

            result_dir = getattr(self, "_result_dir", None) if (self._done and self._retcode == 0) else None
            return {"items": items, "done": self._done, "code": self._retcode,
                    "result_dir": result_dir}

    # â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    # â”‚  HTML / CSS / JS  â€” Ã©diter ici avec un Ã©diteur supportant le HTML  â”‚
    # â”‚  Sections : <style> L+8  â”‚  <body> L+120  â”‚  <script> L+518       â”‚
    # â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>lidar2map</title>
<!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• CSS â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
<style>
:root{--bg:#12121f;--bg2:#1a1a30;--bg3:#1f1f3a;--bd:#2a2a50;
  --ac:#7070cc;--ac2:#e07060;--fg:#ececec;--dim:#a0a0d0;
  --green:#60cc80;--red:#cc6060;--fnt:"Segoe UI",system-ui,sans-serif;
  /* Couleurs par type de carte */
  --lidar:  #5b8a6e;  /* vert forÃªt */
  --scan:   #7a6fa0;  /* violet doux */
  --osm:    #7a9abf;  /* bleu acier */
  --vecteur:#b07840;  /* ocre */
  --fusion: #606878;  /* gris bleu */
  --decoupe:#8a6870;  /* rose-gris */
  --projet: #4a6080;  /* bleu nuit */
  --zone:   #3a7070;  /* teal */
}
*{box-sizing:border-box;margin:0;padding:0}
.hidden{display:none!important}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);font:13px var(--fnt)}
#main{padding:10px 24px}
#form-inner{max-width:900px;width:100%;margin:0 auto;
  display:flex;flex-direction:column;gap:8px}
#btn-bar{max-width:900px;margin:8px auto;padding:0;display:flex;gap:8px;align-items:center}
/* Form elements */
.section{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;
  overflow:hidden}
.section-hd{padding:5px 10px;font-size:11px;font-weight:600;
  color:rgba(255,255,255,.85);text-transform:uppercase;letter-spacing:.6px;
  display:flex;align-items:center;gap:6px}
.section-hd label{display:flex;align-items:center;gap:5px;cursor:pointer;
  font-size:11px;color:rgba(255,255,255,.9);font-weight:600;
  text-transform:none;letter-spacing:0}
/* Bandeau Projet */
.sec-projet .section-hd{background:var(--projet)}
/* Bandeau Zone */
.sec-zone .section-hd{background:var(--zone)}
/* Bandeau Type */
.sec-type .section-hd{background:var(--projet)}
/* Bandeaux LiDAR */
#sec-lidar .section-hd{background:var(--lidar)}
/* Bandeaux IGN Raster */
#sec-scan .section-hd{background:var(--scan)}
/* Bandeaux OSM */
#sec-osm .section-hd{background:var(--osm)}
/* Bandeaux IGN Vectoriel */
#sec-vecteur .section-hd{background:var(--vecteur)}
/* Fond pastel des sections par type */
.section.sec-projet,.section.sec-projet .section-body{background:rgba(74,96,128,.18)!important;border-color:rgba(74,96,128,.4)!important}
.section.sec-zone,.section.sec-zone .section-body    {background:rgba(58,112,112,.18)!important;border-color:rgba(58,112,112,.4)!important}
.section.sec-type,.section.sec-type .section-body    {background:rgba(74,96,128,.18)!important;border-color:rgba(74,96,128,.4)!important}
#sec-lidar   .section{background:rgba(91,138,110,.14)!important;border-color:rgba(91,138,110,.35)!important}
#sec-scan    .section{background:rgba(122,111,160,.14)!important;border-color:rgba(122,111,160,.35)!important}
#sec-osm     .section{background:rgba(122,154,191,.14)!important;border-color:rgba(122,154,191,.35)!important}
#sec-vecteur .section{background:rgba(176,120,64,.14)!important;border-color:rgba(176,120,64,.35)!important}
#sec-fusion  .section{background:rgba(96,104,120,.14)!important;border-color:rgba(96,104,120,.35)!important}
.section-body{padding:8px 10px;display:flex;flex-direction:column;gap:6px}
.section-body.hidden{display:none}
.row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.row label{font-size:11px;color:var(--dim);white-space:nowrap;min-width:110px}
.row label.wide{min-width:140px}
input[type=text],input[type=number],select{
  background:var(--bg3);border:1px solid var(--bd);border-radius:4px;
  color:var(--fg);padding:3px 7px;font:12px var(--fnt);outline:none;
  flex:1;min-width:0}
input[type=text]:focus,input[type=number]:focus,select:focus{
  border-color:var(--ac)}
input[type=number]{width:60px;flex:none}
.inp-short{width:54px!important;flex:none!important}
select{cursor:pointer}
.cb-group{display:flex;flex-wrap:wrap;gap:4px 14px;max-width:100%}
.cb-group label{display:flex;align-items:center;gap:4px;font-size:11px;
  cursor:pointer;color:var(--fg);white-space:nowrap}
.seg{display:flex;border:1px solid var(--bd);border-radius:4px;overflow:hidden}
.seg input{display:none}
.seg label{padding:3px 10px;font-size:11px;cursor:pointer;
  background:var(--bg3);color:var(--dim);white-space:nowrap}
.seg input:checked+label{background:var(--ac);color:#fff}
.btn{padding:4px 14px;border:none;border-radius:4px;cursor:pointer;
  font:12px var(--fnt);font-weight:600;letter-spacing:.3px}
.btn-run{background:var(--ac);color:#fff;padding:6px 20px}
.btn-stop{background:var(--bg3);color:var(--ac2);border:1px solid var(--ac2)}
.btn-sm{background:var(--bg3);color:var(--dim);border:1px solid var(--bd);
  padding:2px 8px;font-size:11px}
.btn:disabled{opacity:.4;cursor:default}
.hint{font-size:10px;color:var(--dim)}
.priori-zone{display:none}
body.type-lidar .priori-zone, body.type-scan .priori-zone{display:inline-flex!important}
/* type selector */
#type-sel{display:flex;gap:6px;flex-wrap:wrap}
#type-sel input{display:none}
#type-sel label{padding:5px 16px;border:2px solid var(--bd);border-radius:4px;
  cursor:pointer;font-size:12px;background:var(--bg3);color:var(--dim);
  font-weight:600}
#t-lidar:checked   +label{border-color:var(--lidar);color:var(--lidar);background:var(--bg2)}
#t-scan:checked    +label{border-color:var(--scan);color:var(--scan);background:var(--bg2)}
#t-osm:checked     +label{border-color:var(--osm);color:var(--osm);background:var(--bg2)}
#t-vecteur:checked +label{border-color:var(--vecteur);color:var(--vecteur);background:var(--bg2)}
#t-fusion:checked  +label{border-color:var(--fusion);color:var(--fusion);background:var(--bg2)}
#t-decoupe:checked +label{border-color:var(--decoupe);color:var(--decoupe);background:var(--bg2)}
/* Couleur btn-run selon type actif */
body.type-lidar   #btn-run{background:var(--lidar)}
body.type-scan    #btn-run{background:var(--scan)}
body.type-osm     #btn-run{background:var(--osm)}
body.type-vecteur #btn-run{background:var(--vecteur)}
body.type-fusion  #btn-run{background:var(--fusion)}
body.type-decoupe #btn-run{background:var(--decoupe)}
/* Bandeaux DÃ©coupage raster */
#sec-decoupe .section-hd{background:var(--decoupe)}
#sec-decoupe .section{background:rgba(138,104,112,.14)!important;border-color:rgba(138,104,112,.35)!important}
/* listbox fusion */
#fusion-list{background:var(--bg3);border:1px solid var(--bd);border-radius:4px;
  min-height:60px;max-height:100px;overflow-y:auto;padding:4px;font-size:11px}
#fusion-list div{padding:2px 4px;border-radius:3px;cursor:pointer}
#fusion-list div:hover{background:var(--bd)}
#fusion-list div.sel{background:var(--ac);color:#fff}
/* â•â•â• PANNEAU DE LOG â•â•â• */
#panneau-log{
  position:fixed;left:0;right:0;bottom:0;
  height:200px; min-height:60px; max-height:85vh;
  background:var(--bg2);border-top:2px solid var(--bd);
  display:flex;flex-direction:column;z-index:50;
  /* Pas de transition .15s sur height : Ã§a lutte avec le drag de la
     poignÃ©e et provoque un effet d'inertie/saccade pendant le mousemove.
     ConservÃ© seulement pour le toggle ouvert/fermÃ© via JS qui ajoute la
     classe `animating` le temps de la transition. */
}
#panneau-log.animating{ transition:height .15s ease; }
/* PoignÃ©e de redimensionnement vertical : 6 px sur le bord supÃ©rieur,
   dÃ©bordant 3 px au-dessus pour faciliter le clic (zone de hit plus
   gÃ©nÃ©reuse que la bordure visible). Cursor ns-resize est explicite. */
#log-resize-handle{
  position:absolute; left:0; right:0; top:-3px;
  height:6px;
  cursor:ns-resize;
  z-index:51;
  background:transparent;
}
#log-resize-handle:hover,
#log-resize-handle.dragging{
  background:var(--ac);
  opacity:.6;
}
/* Pendant le drag : dÃ©sactiver toute sÃ©lection de texte sur la page
   pour Ã©viter de surligner le contenu en bougeant la souris. */
body.log-resizing,
body.log-resizing *{
  user-select:none !important;
  cursor:ns-resize !important;
}
/* CachÃ© par dÃ©faut, ouvert au clic sur le bouton Logs */
#panneau-log.hidden{display:none}
#log-header{
  display:flex;align-items:center;gap:8px;
  padding:6px 12px;background:var(--bg3);
  border-bottom:1px solid var(--bd);
  user-select:none;
  font-size:12px;
}
#log-header strong{color:var(--ac);font-weight:600}
#log-header .log-actions{margin-left:auto;display:flex;gap:6px}
#log-header button{
  background:transparent;border:1px solid var(--bd);color:var(--dim);
  padding:2px 8px;border-radius:3px;cursor:pointer;font-size:11px;
}
#log-header button:hover{background:var(--bd);color:var(--fg)}
#log-content{
  flex:1;overflow-y:auto;overflow-x:auto;
  padding:6px 12px;
  font-family:Consolas,"Courier New",monospace;
  font-size:11px;line-height:1.4;
  color:var(--fg);background:#0a0a14;
  white-space:pre-wrap;word-wrap:break-word;
}
#log-content .log-ok  {color:#c8c8d4}
#log-content .log-err {color:#ff7060;font-weight:500}
#log-content .log-dim {color:#7575a0;font-style:italic}
#log-content .log-cmd {color:#80a0d0;font-style:italic;border-bottom:1px dashed var(--bd);
                       padding-bottom:4px;margin-bottom:6px}
/* Compenser la hauteur du panneau dans le main quand il est visible */
#main.log-visible{padding-bottom:210px}
/* Bouton Logs actif (panneau visible) â€” bordure plus claire */
#btn-log.active{background:var(--ac)!important;color:#fff!important}
/* Barre de progression */
#log-progress{
  height:3px;background:var(--bg3);position:relative;
}
#log-progress-bar{
  position:absolute;top:0;left:0;height:100%;
  background:var(--ac);transition:width .2s;
  width:0%;
}
#log-progress-bar.err{background:var(--red)}
#log-progress-bar.ok{background:var(--green)}
/* â”€â”€ Autocomplete ville (API BAN data.gouv.fr) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
/* La section zone doit laisser dÃ©passer le dropdown â€” sinon clipping par
   .section { overflow:hidden } (ligne ~9945) qui sert aux coins arrondis. */
.section.sec-zone{overflow:visible}
.section.sec-zone .section-hd{border-radius:6px 6px 0 0}
.ac-wrap{position:relative;display:inline-flex;flex:1;min-width:0;max-width:180px}
.ac-wrap > input[type=text]{width:100%}
.ac-dropdown{
  position:absolute;top:calc(100% + 2px);left:0;
  min-width:100%;width:max-content;max-width:380px;
  background:var(--bg3);border:1px solid var(--bd);border-radius:4px;
  box-shadow:0 4px 12px rgba(0,0,0,.4);
  z-index:1000;max-height:240px;overflow-y:auto;
}
.ac-item{
  padding:5px 8px;cursor:pointer;font-size:12px;color:var(--fg);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  border-bottom:1px solid var(--bd);
}
.ac-item:last-child{border-bottom:none}
.ac-item:hover,.ac-item.active{background:var(--bg2);color:var(--ac)}
.ac-item .ac-meta{color:var(--dim);font-size:11px;margin-left:6px}
</style>
</head>
<!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• HTML â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
<body>
<div id="main">
<div id="btn-bar">
 <button class="btn btn-run" id="btn-run" onclick="lancer()">â–¶ Lancer</button>
 <button class="btn btn-stop" id="btn-stop" onclick="arreter()" disabled>â–  ArrÃªter</button>
 <button class="btn" id="btn-hist" onclick="toggleHistorique()"
         style="background:var(--bg3);border:1px solid var(--ac);color:var(--fg);margin-left:12px">â± Historique</button>
 <button class="btn" id="btn-log" onclick="toggleLogPanel()"
         style="background:var(--bg3);border:1px solid var(--ac);color:var(--fg);margin-left:6px">ðŸ“‹ Logs</button>
 <span id="footer-status" style="font-size:11px;color:var(--dim);margin-left:8px"></span>
</div>
<div id="form-inner">

  <!-- Projet -->
  <div class="section sec-projet">
   <div class="section-hd">Projet</div>
   <div class="section-body">
     <div class="row">
      <label style="min-width:auto;margin-right:4px">Nom *</label>
      <input type="text" id="f-nom" placeholder="ex: gareoult" style="flex:1">
      <label style="min-width:auto;margin-left:12px">Dossier sortie</label>
      <input type="text" id="f-dossier" placeholder="(auto)" style="flex:3">
      <button class="btn btn-sm" onclick="pickDir('f-dossier')">â€¦</button>
      <label style="min-width:auto;margin-left:12px"
             title="Source LiDAR (par pays). Le choix masque les onglets IGN Raster/Vecteur pour les providers non-FR.">Provider</label>
      <select id="f-provider" style="min-width:200px">
       <option value="fr-ign">Chargement...</option>
      </select>
      <span id="lidar-apikey-group" style="display:none;align-items:center;gap:4px;margin-left:8px">
       <span style="color:var(--dim)">ClÃ© API :</span>
       <input type="text" id="f-lidar-apikey" style="margin-left:4px;max-width:160px"
              placeholder="clÃ© OpenTopography">
      </span>
     </div>
   </div>
  </div>

  <!-- Zone gÃ©ographique -->
  <div class="section sec-zone">
   <div class="section-hd">Zone gÃ©ographique</div>
   <div class="section-body">
    <div class="row">
     <div class="seg">
      <input type="radio" name="mode" id="m-ville" value="ville" checked>
      <label for="m-ville">Ville</label>
      <input type="radio" name="mode" id="m-gps" value="gps">
      <label for="m-gps">GPS</label>
      <input type="radio" name="mode" id="m-bbox" value="bbox">
      <label for="m-bbox">BBox</label>
      <input type="radio" name="mode" id="m-dep" value="dep">
      <label for="m-dep">DÃ©partement</label>
     </div>
    </div>
    <div class="row z-zone" id="z-ville"><label>Ville</label>
     <div class="ac-wrap">
       <input type="text" id="f-ville" placeholder="ex: GarÃ©oult" autocomplete="off">
       <div id="f-ville-ac" class="ac-dropdown hidden" role="listbox"></div>
     </div>
     <label style="min-width:auto;margin-left:8px">Rayon km</label>
     <input type="number" id="f-rayon" value="10" min="0" max="500" class="inp-short"></div>
    <div class="row hidden z-zone" id="z-gps"><label>GPS lat,lon</label>
     <input type="text" id="f-gps" placeholder="43.3156,6.0423" style="max-width:160px">
     <label style="min-width:auto;margin-left:8px">Rayon km</label>
     <input type="number" id="f-rayon-gps" value="10" min="0" max="500" class="inp-short"></div>
    <div class="row hidden z-zone" id="z-bbox"><label>BBox W,S,E,N</label>
     <input type="text" id="f-bbox" placeholder="5.9,43.1,6.6,43.8" style="max-width:200px"></div>
    <div class="hidden z-zone" id="z-dep">
     <div class="row">
      <label>DÃ©partement(s)</label>
      <input type="text" id="f-dep" placeholder="83" style="width:220px;flex:none"
             title="Un ou plusieurs dÃ©partements&#10;Exemples : 83 | 83,06,13 | 1-10 | 1-3,75,83 | 2A | 971">
     </div>
     <div class="hint" style="margin-top:3px;margin-left:0">
      Syntaxe : <code>83</code> &nbsp;Â·&nbsp;
      <code>83,06,13</code> &nbsp;Â·&nbsp;
      <code>1-10</code> &nbsp;Â·&nbsp;
      <code>1-3,75,83</code> &nbsp;Â·&nbsp;
      DOM : <code>2A</code> <code>971</code>
      &nbsp;â€”&nbsp; Multi-dÃ©partement : un fichier par dÃ©partement
     </div>
    </div>
   </div>
  </div>

  <!-- Type de carte -->
  <div class="section sec-type">
   <div class="section-hd">Type de traitement de carte</div>
   <div class="section-body">
    <div id="type-sel">
     <input type="radio" name="type" id="t-lidar"   value="lidar"   checked>
     <label for="t-lidar">LiDAR MNT</label>
     <input type="radio" name="type" id="t-scan"    value="scan">
     <label for="t-scan" data-fr-only="1">IGN Raster</label>
     <input type="radio" name="type" id="t-vecteur" value="vecteur">
     <label for="t-vecteur" data-fr-only="1">IGN Vectoriel</label>
     <input type="radio" name="type" id="t-osm"     value="osm">
     <label for="t-osm">OSM Vectoriel</label>
     <input type="radio" name="type" id="t-fusion"  value="fusion">
     <label for="t-fusion">Fusion Vectoriel</label>
     <input type="radio" name="type" id="t-decoupe" value="decoupe">
     <label for="t-decoupe">DÃ©coupage raster</label>
    </div>
   </div>
  </div>

  <!-- â•â•â• LIDAR â•â•â• -->
  <div id="sec-lidar">
   <div class="section">
    <div class="section-hd">
     <label>0 â€” DÃ©coupage Ã  priori (grandes zones)</label>
    </div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-priori-cols" value="1" min="1" max="50" class="inp-short" title="Colonnes Est-Ouest">
      <span class="hint" style="margin:0 4px">cols Ã—</span>
      <input type="number" id="f-priori-rows" value="1" min="1" max="50" class="inp-short" title="Lignes Nord-Sud">
      <span class="hint" style="margin:0 4px">lignes</span>
      <span class="hint" style="margin:0 6px;color:var(--dim)">ou rayon</span>
      <input type="number" id="f-rayon-priori-l" value="0" min="0" step="10" class="inp-short" title="Rayon km par morceau (alternative Ã  la grille)">
      <span class="hint" style="margin-left:4px">km</span>
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-nettoyage"> Nettoyage intermÃ©diaires</label>
     </div>
     <div class="row" style="color:var(--dim);font-size:11px;padding-top:0">
      <span style="padding-left:calc(var(--label-w) + 4px)">1Ã—1 = pas de dÃ©coupage â€” reprise automatique via manifeste.json</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel" checked> 1 â€” TÃ©lÃ©charger les dalles LiDAR HD IGN</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tel">
     <div class="row">
      <label>Workers :</label>
      <input type="number" id="f-workers-l" value="8" min="1" max="32" class="inp-short">
      <label style="min-width:auto"><input type="checkbox" id="f-comp"> Compresser</label>
      <label style="min-width:auto;margin-left:12px">Cache externe :</label>
      <input type="text" id="f-dossier-dalles" placeholder="(cache auto)">
      <button class="btn btn-sm" onclick="pickDir('f-dossier-dalles')">â€¦</button>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-no-omb" checked> 2 â€” Calculer les ombrages archÃ©ologiques</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-omb">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-omb">
     <div class="row">
      <div class="cb-group">
       <label><input type="checkbox" name="omb" value="multi" checked> multi</label>
       <label><input type="checkbox" name="omb" value="slope"> slope</label>
       <label><input type="checkbox" name="omb" value="315"> 315Â°</label>
       <label><input type="checkbox" name="omb" value="045"> 045Â°</label>
       <label><input type="checkbox" name="omb" value="135"> 135Â°</label>
       <label><input type="checkbox" name="omb" value="225"> 225Â°</label>
       <label><input type="checkbox" name="omb" value="svf"> SVF</label>
       <label><input type="checkbox" name="omb" value="svf100"> SVF100</label>
       <label><input type="checkbox" name="omb" value="lrm"> LRM</label>
       <label><input type="checkbox" name="omb" value="rrim"> RRIM</label>
      </div>
      <span style="margin-left:12px;color:var(--dim)">â˜€</span>
      <input type="number" id="f-elevation" value="25" min="5" max="60" class="inp-short">
      <span style="color:var(--dim)">Â°</span>
      <label style="margin-left:16px" title="Kernel SVF sweep-horizon avec running max sur deque (upper convex hull). Speedup Ã—2-3 pour SVF20m, Ã—15+ pour SVF100m. LÃ©ger aliasing NN aux faibles gradients, imperceptible pour structures > 1-2 px. RecommandÃ© pour SVF100m et RRIM.">
       <input type="checkbox" id="f-sweep-horizon"> sweep-horizon (Ã—15 pour SVF100m)
      </label>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-mbtiles-l" checked> 3 â€” Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-mbt">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body hidden" id="body-mbt">
     <div class="row">
      <label>Zoom :</label>
      <input type="number" id="f-zoom-min-l" value="8" min="8" max="20" class="inp-short">
      <span style="color:var(--dim)">â€“</span>
      <input type="number" id="f-zoom-max-l" value="18" min="8" max="20" class="inp-short">
      <span style="margin-left:12px;color:var(--dim)">Format de l'image :</span>
      <div class="seg" style="margin-left:6px">
       <input type="radio" name="fmt-l" id="fl-jpeg" value="jpeg" checked><label for="fl-jpeg">JPEG</label>
       <input type="radio" name="fmt-l" id="fl-png"  value="png"><label for="fl-png">PNG</label>
      </div>
      <span id="wrap-qualite-l">
       <span style="margin-left:8px;color:var(--dim)">QualitÃ© Jpeg :</span>
       <input type="number" id="f-qualite-l" value="85" min="50" max="95" class="inp-short" style="margin-left:4px">
      </span>
     </div>
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-mbtiles" checked> MBTiles</label>
       <label><input type="checkbox" id="f-rmap"> RMAP</label>
       <label><input type="checkbox" id="f-sqlitedb"> SQLiteDB</label>
      </div>
     </div>
    </div>
   </div>
  </div>

  <!-- â•â•â• SCAN â•â•â• -->
  <div id="sec-scan" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label>0 â€” DÃ©coupage Ã  priori (grandes zones)</label>
    </div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-priori-cols-s" value="1" min="1" max="50" class="inp-short" title="Colonnes Est-Ouest">
      <span class="hint" style="margin:0 4px">cols Ã—</span>
      <input type="number" id="f-priori-rows-s" value="1" min="1" max="50" class="inp-short" title="Lignes Nord-Sud">
      <span class="hint" style="margin:0 4px">lignes</span>
      <span class="hint" style="margin:0 6px;color:var(--dim)">ou rayon</span>
      <input type="number" id="f-rayon-priori-s" value="0" min="0" step="10" class="inp-short" title="Rayon km par morceau">
      <span class="hint" style="margin-left:4px">km</span>
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-nettoyage-s"> Nettoyage intermÃ©diaires</label>
     </div>
     <div class="row" style="color:var(--dim);font-size:11px;padding-top:0">
      <span style="padding-left:calc(var(--label-w) + 4px)">1Ã—1 = pas de dÃ©coupage â€” reprise automatique via manifeste.json</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">Couche IGN</div>
    <div class="section-body">
     <div class="row">
      <label>Couche :</label>
      <select id="f-couche"></select>
      <span id="apikey-group" style="display:none;align-items:center;gap:4px;margin-left:8px"><span style="color:var(--dim)">ClÃ© API :</span><input type="text" id="f-apikey" style="margin-left:4px;max-width:140px" placeholder="clÃ© pro IGN"></span>
     </div>
     <div id="scan-restriction-warning" class="hidden" style="margin-top:4px;padding:6px 8px;background:rgba(204,96,96,.15);border:1px solid rgba(204,96,96,.4);border-radius:4px;font-size:11px;color:#e07070">
      âš  Cette couche est rÃ©servÃ©e aux <strong>professionnels</strong> (CGU IGN).<br>
      Une clÃ© API est requise â€” compte <a href="https://cartes.gouv.fr" target="_blank" style="color:#e07070">cartes.gouv.fr</a> avec SIRET.<br>
      Les particuliers doivent utiliser <strong>planign</strong> ou <strong>ortho</strong> (pas de clÃ© requise).
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-s" checked> 1 â€” TÃ©lÃ©charger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-s">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tel-s">
     <div class="row"><label>Workers :</label>
      <input type="number" id="f-workers-s" value="8" min="1" max="32" class="inp-short"></div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-s" checked> 2 â€” Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-s">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tuil-s">
     <div class="row">
      <label>Zoom :</label>
      <input type="number" id="f-zoom-min-s" value="12" min="1" max="20" class="inp-short">
      <span style="color:var(--dim)">â€“</span>
      <input type="number" id="f-zoom-max-s" value="16" min="1" max="20" class="inp-short">
      <span style="margin-left:12px;color:var(--dim)">Format de l'image :</span>
      <div class="seg" style="margin-left:6px">
       <input type="radio" name="fmt-s" id="fs-jpeg" value="jpeg" checked><label for="fs-jpeg">JPEG</label>
       <input type="radio" name="fmt-s" id="fs-png"  value="png"><label for="fs-png">PNG</label>
      </div>
      <span id="wrap-qualite-s">
       <span style="margin-left:8px;color:var(--dim)">QualitÃ© Jpeg :</span>
       <input type="number" id="f-qualite-s" value="85" min="50" max="95" class="inp-short" style="margin-left:4px">
      </span>
     </div>
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-mbtiles-s" checked> MBTiles</label>
       <label><input type="checkbox" id="f-rmap-s"> RMAP</label>
       <label><input type="checkbox" id="f-sqlitedb-s"> SQLiteDB</label>
      </div>
     </div>
    </div>
   </div>
  </div>

  <!-- â•â•â• OSM â•â•â• -->
  <div id="sec-osm" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-osm" checked> 1 â€” TÃ©lÃ©charger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-osm">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tel-osm">
     <div class="cb-group" id="osm-tag-checks"></div>
     <div class="row" style="margin-top:4px">
      <label>Workers :</label>
      <input type="number" id="f-workers-osm" value="4" min="1" max="16" class="inp-short">
      <span class="hint" style="margin-left:6px">(parallÃ©lisme tÃ©lÃ©chargement PBF)</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-osm" checked> 2 â€” Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-osm">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tuil-osm">
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-map" checked> Mapsforge (.map)</label>
       <label><input type="checkbox" id="f-osm-geojson" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-osm-geojson-raw"> .geojson (non compressÃ©)</label>
      </div>
     </div>
    </div>
   </div>
  </div>

  <!-- â•â•â• VECTEUR IGN â•â•â• -->
  <div id="sec-vecteur" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-v" checked> 1 â€” TÃ©lÃ©charger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-v">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body" id="body-tel-v">
     <div class="cb-group" id="wfs-checks"></div>
     <div class="row" style="margin-top:4px">
      <label>Workers :</label>
      <input type="number" id="f-workers-v" value="4" min="1" max="16" class="inp-short">
      <span class="hint" style="margin-left:6px">(max 4 recommandÃ©)</span>
     </div>
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-fusion-gz" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-fusion-gz-raw"> .geojson (non compressÃ©)</label>
      </div>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-v"> 2 â€” GÃ©nÃ©rer carte Mapsforge (.map)</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-v">  Ã‰craser le fichier rÃ©sultat</label>
    </div>
    <div class="section-body hidden" id="body-map-v">
     <span class="hint">GeoJSON IGN â†’ OSM XML â†’ osmosis+mapwriter â†’ .map</span>
     <div class="row" id="row-simplif-v" class="hidden" style="margin-top:6px">
      <label>Simplification vecteur</label>
      <input type="number" id="f-simplif-v" min="1" max="200" step="1" placeholder="auto"
             style="width:80px" title="Epsilon Douglas-Peucker en mÃ¨tres. Vide = auto depuis surface.">
      <span class="hint" style="margin-left:6px">m  (vide = auto : 3 m local â†’ 40 m rÃ©gion)</span>
     </div>
    </div>
   </div>
  </div>

  <!-- â•â•â• FUSION â•â•â• -->
  <div id="sec-fusion" class="hidden">
   <div class="section">
    <div class="section-hd">Fichiers GeoJSON Ã  fusionner</div>
    <div class="section-body">
     <div id="fusion-list"></div>
     <div class="row" style="margin-top:4px">
      <button class="btn btn-sm" onclick="fusionAjouter()">ï¼‹ Ajouterâ€¦</button>
      <button class="btn btn-sm" onclick="fusionSupprimer()">ï¼ Supprimer</button>
      <button class="btn btn-sm" onclick="fusionVider()">âœ• Vider</button>
      <span class="hint" style="margin-left:8px">SÃ©lection Ã©tendue (Shift/Ctrl)</span>
     </div>
     <div class="row">
      <label>Format :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-fusion-gz2" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-fusion-gz2-raw"> .geojson (non compressÃ©)</label>
       <label><input type="checkbox" id="f-fusion-map"> Mapsforge (.map)</label>
      </div>
     </div>
     <div class="row" id="row-simplif-fusion" class="hidden" style="margin-top:6px">
      <label>Simplification vecteur</label>
      <input type="number" id="f-simplif-fusion" min="1" max="200" step="1" placeholder="auto"
             style="width:80px" title="Epsilon Douglas-Peucker en mÃ¨tres. Vide = auto depuis surface.">
      <span class="hint" style="margin-left:6px">m  (vide = auto)</span>
     </div>
    </div>
   </div>
  </div>


  <!-- â•â•â• DÃ‰COUPAGE RASTER â•â•â• -->
  <div id="sec-decoupe" class="hidden">
   <div class="section">
    <div class="section-hd">Fichier source</div>
    <div class="section-body">
     <div class="row">
      <label>Source MBTiles</label>
      <input type="text" id="f-source-decoupe" placeholder="chemin vers le fichier .mbtiles">
      <button class="btn btn-sm" onclick="pickFile('f-source-decoupe',false,[])">â€¦</button>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">DÃ©coupage</div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-cols-decoupe" value="1" min="1" max="50" class="inp-short" title="Colonnes (Est-Ouest)">
      <span class="hint" style="margin:0 4px">cols Ã—</span>
      <input type="number" id="f-rows-decoupe" value="1" min="1" max="50" class="inp-short" title="Lignes (Nord-Sud)">
      <span class="hint" style="margin:0 4px">lignes  ou rayon</span>
      <input type="number" id="f-rayon-decoupe-d" value="0" min="0" step="10" class="inp-short">
      <span class="hint" style="margin-left:4px">km</span>
     </div>
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-mbtiles-d" checked> MBTiles</label>
       <label><input type="checkbox" id="f-rmap-d"> RMAP</label>
       <label><input type="checkbox" id="f-sqlitedb-d"> SQLiteDB</label>
      </div>
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-ecraser-d">  Ã‰craser</label>
     </div>
    </div>
   </div>
  </div>


 </div><!-- /form-inner -->
</div><!-- /main -->
<!-- â•â•â• PANNEAU HISTORIQUE â•â•â• -->
<div id="panneau-hist" class="hidden"
     style="position:fixed;top:0;right:0;width:420px;height:100%;background:var(--bg2);
            border-left:1px solid var(--bd);overflow-y:auto;z-index:100;padding:12px;box-sizing:border-box">
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
  <strong>Historique des traitements</strong>
  <div style="display:flex;gap:6px;align-items:center">
   <button class="btn" onclick="viderHistorique()"
           style="background:transparent;border:1px solid var(--red);color:var(--red);
                  font-size:11px;padding:3px 10px;cursor:pointer">ðŸ—‘ Vider</button>
   <button class="btn" onclick="toggleHistorique()"
           style="background:transparent;border:none;font-size:16px;cursor:pointer">âœ•</button>
  </div>
 </div>
 <div id="hist-list"></div>
<!-- panneau-hist end -->
</div>

<!-- â•â•â• PANNEAU DE LOG â•â•â• -->
<div id="panneau-log" class="hidden">
  <div id="log-resize-handle" title="Redimensionner verticalement"></div>
  <div id="log-header">
    <strong>ðŸ“‹ Log</strong>
    <span id="log-status" style="color:var(--dim)"></span>
    <div class="log-actions">
      <button onclick="copierLog()" title="Copier le log dans le presse-papier">âŽ˜ Copier</button>
      <button onclick="viderLog()" title="Effacer le contenu du log">ðŸ—‘ Vider</button>
      <button onclick="toggleLogPanel()" title="Masquer le panneau (rÃ©-affichable via le bouton Logs en haut)">âœ•</button>
    </div>
  </div>
  <div id="log-progress"><div id="log-progress-bar"></div></div>
  <div id="log-content"></div>
</div>

<!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• JS â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
<script>
// â”€â”€ Ã‰tat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
let fusionFiles = [];
let fusionSel = -1;
let polling = null;
let _initialized = false;

// â”€â”€ Panneau de log â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function ajouterLigneLog(text, tag) {
  const c = document.getElementById('log-content');
  if (!c) return;
  const span = document.createElement('span');
  span.className = 'log-' + (tag || 'ok');
  span.textContent = text;
  c.appendChild(span);
  // Auto-scroll si l'utilisateur est dÃ©jÃ  en bas (Ã  30 px prÃ¨s)
  const isAtBottom = (c.scrollHeight - c.scrollTop - c.clientHeight) < 30;
  if (isAtBottom) c.scrollTop = c.scrollHeight;
  // Limiter Ã  ~5000 lignes pour Ã©viter de saturer le DOM sur les longs runs
  while (c.children.length > 5000) c.removeChild(c.firstChild);
}

function viderLog() {
  const c = document.getElementById('log-content');
  if (c) c.innerHTML = '';
  document.getElementById('log-status').textContent = '';
  setLogProgress(0, '');
}

function copierLog() {
  // navigator.clipboard.writeText ne fonctionne pas dans WebView2/pywebview
  // hors contexte sÃ©curisÃ© (pas de HTTPS) : la mÃ©thode existe mais throw
  // silencieusement Â« NotAllowedError Â» ou ne fait rien selon les versions.
  // On essaie d'abord l'API moderne puis on retombe sur execCommand qui,
  // bien que dÃ©prÃ©ciÃ©, reste fonctionnel partout â€” y compris dans WebView2.
  const c = document.getElementById('log-content');
  if (!c) return;
  const text = c.textContent || '';

  function _flash() {
    const st = document.getElementById('log-status');
    if (!st) return;
    const orig = st.textContent;
    st.textContent = 'âœ“ copiÃ© dans le presse-papier';
    setTimeout(() => { st.textContent = orig; }, 1500);
  }

  function _flashErr() {
    const st = document.getElementById('log-status');
    if (!st) return;
    const orig = st.textContent;
    st.textContent = 'âœ— copie Ã©chouÃ©e';
    setTimeout(() => { st.textContent = orig; }, 2500);
  }

  function _fallback() {
    // MÃ©thode universelle : textarea hors-Ã©cran + execCommand('copy').
    // Doit Ãªtre attachÃ© au DOM et sÃ©lectionnÃ© AVANT execCommand.
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    // Position fixed visible 1Ã—1 px : execCommand exige que l'Ã©lÃ©ment soit
    // dans le viewport (sinon il refuse silencieusement sur certains
    // chromiums embarquÃ©s). OpacitÃ© 0 plutÃ´t que display:none.
    ta.style.position  = 'fixed';
    ta.style.top       = '0';
    ta.style.left      = '0';
    ta.style.width     = '1px';
    ta.style.height    = '1px';
    ta.style.padding   = '0';
    ta.style.border    = 'none';
    ta.style.outline   = 'none';
    ta.style.boxShadow = 'none';
    ta.style.background = 'transparent';
    ta.style.opacity   = '0';
    document.body.appendChild(ta);

    // MÃ©moriser la sÃ©lection courante pour la restaurer aprÃ¨s
    const sel = document.getSelection();
    const ranges = [];
    if (sel) {
      for (let i = 0; i < sel.rangeCount; i++) ranges.push(sel.getRangeAt(i));
    }

    let ok = false;
    try {
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, text.length);
      ok = document.execCommand('copy');
    } catch (e) {
      console.error('execCommand copy:', e);
    }
    document.body.removeChild(ta);

    // Restaurer la sÃ©lection que l'utilisateur avait avant
    if (sel && ranges.length) {
      sel.removeAllRanges();
      ranges.forEach(r => sel.addRange(r));
    }
    return ok;
  }

  // Tentative API moderne, fallback synchrone si KO/absente
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(_flash).catch(e => {
      console.warn('clipboard API failed, fallback execCommand:', e);
      if (_fallback()) _flash(); else _flashErr();
    });
  } else {
    if (_fallback()) _flash(); else _flashErr();
  }
}

function toggleLogPanel() {
  const p = document.getElementById('panneau-log');
  const m = document.getElementById('main');
  const b = document.getElementById('btn-log');
  if (!p) return;
  // On active la transition CSS uniquement pour le toggle, pas pour le
  // drag de redimensionnement (sinon effet d'inertie pendant le mousemove).
  p.classList.add('animating');
  setTimeout(() => p.classList.remove('animating'), 200);
  p.classList.toggle('hidden');
  const visible = !p.classList.contains('hidden');
  if (m) m.classList.toggle('log-visible', visible);
  if (b) b.classList.toggle('active', visible);
}

// â”€â”€ Drag de la poignÃ©e de redimensionnement du panneau de log â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Pattern classique : mousedown sur la poignÃ©e â†’ on enregistre Y de dÃ©part
// + hauteur de dÃ©part ; mousemove document â†’ recalcule height ; mouseup
// document â†’ cleanup. Le clamp respecte min-height (60) et 85vh.
// Persistance de la hauteur en localStorage : `log-h-px` â€” stable entre
// sessions sans nÃ©cessiter d'aller-retour Python.
(function _initLogResize(){
  const HANDLE_ID = 'log-resize-handle';
  const PANEL_ID  = 'panneau-log';
  const KEY       = 'lidar2map.log-height';
  const MIN_PX    = 60;
  const MAX_FRAC  = 0.85;   // 85vh

  function _maxPx(){ return Math.floor(window.innerHeight * MAX_FRAC); }
  function _clamp(h){ return Math.max(MIN_PX, Math.min(_maxPx(), h)); }

  function _appliquerHauteur(h){
    const p = document.getElementById(PANEL_ID);
    if (!p) return;
    p.style.height = _clamp(h) + 'px';
  }

  // Restaurer la hauteur au chargement (si persistÃ©e)
  try {
    const saved = parseInt(localStorage.getItem(KEY) || '', 10);
    if (!isNaN(saved) && saved >= MIN_PX) _appliquerHauteur(saved);
  } catch(e) { /* localStorage indispo (privacy mode) â€” non critique */ }

  function _attacher(){
    const handle = document.getElementById(HANDLE_ID);
    const panel  = document.getElementById(PANEL_ID);
    if (!handle || !panel) return;
    if (handle.dataset.bound === '1') return;   // idempotent
    handle.dataset.bound = '1';

    let dragStartY = 0;
    let dragStartH = 0;
    let dragging   = false;

    function onMouseMove(ev){
      if (!dragging) return;
      // dY positif quand on descend ; le panneau est ancrÃ© en bas, donc
      // descendre la souris RÃ‰DUIT la hauteur. Inverser.
      const dy = ev.clientY - dragStartY;
      _appliquerHauteur(dragStartH - dy);
      ev.preventDefault();
    }
    function onMouseUp(){
      if (!dragging) return;
      dragging = false;
      handle.classList.remove('dragging');
      document.body.classList.remove('log-resizing');
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      // Persister la hauteur finale
      try {
        const h = parseInt(panel.style.height, 10);
        if (!isNaN(h)) localStorage.setItem(KEY, String(h));
      } catch(e) {}
    }
    handle.addEventListener('mousedown', function(ev){
      if (ev.button !== 0) return;   // bouton gauche uniquement
      dragging   = true;
      dragStartY = ev.clientY;
      dragStartH = panel.getBoundingClientRect().height;
      handle.classList.add('dragging');
      document.body.classList.add('log-resizing');
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup',   onMouseUp);
      ev.preventDefault();
    });

    // Re-clamp si la fenÃªtre rÃ©trÃ©cit (max passe sous la hauteur courante)
    window.addEventListener('resize', function(){
      const h = parseInt(panel.style.height, 10);
      if (!isNaN(h)) _appliquerHauteur(h);
    });
  }

  // Le panneau-log est dans le DOM dÃ¨s le dÃ©part (pas crÃ©Ã© dynamiquement),
  // mais on attend DOMContentLoaded pour Ãªtre robuste si l'ordre change.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _attacher);
  } else {
    _attacher();
  }
})();

function setLogProgress(pct, cls) {
  const bar = document.getElementById('log-progress-bar');
  if (!bar) return;
  bar.style.width = (pct >= 0 && pct <= 100 ? pct : 0) + '%';
  bar.className = '';
  if (cls) bar.classList.add(cls);
}

// â”€â”€ Init â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// bindAll() est appelÃ© immÃ©diatement au DOMContentLoaded pour l'Ã©tat initial
// (sections visibles/cachÃ©es selon checkboxes). L'init async (couches, config)
// est lancÃ©e sÃ©parÃ©ment dÃ¨s que pywebview.api est disponible.
document.addEventListener('DOMContentLoaded', () => {
  bindAll();
  _acInstaller();
  // pywebview Ã©met 'pywebviewready' sur window quand le bridge JSâ†”Python est
  // Ã©tabli. C'est plus fiable que le polling seul (qui peut timeout en
  // debug=False sur certaines configs WebView2 lentes).
  if (window.pywebview && window.pywebview.api) {
    initAsync();
  } else {
    window.addEventListener('pywebviewready', initAsync, { once: true });
    waitForApi();   // fallback polling (au cas oÃ¹ l'event soit ratÃ©)
  }
});

function waitForApi(tries=0) {
  if (window.pywebview && window.pywebview.api &&
      typeof window.pywebview.api.get_init_data === 'function') {
    initAsync();
  } else if (tries < 600) {   // 600Ã—50ms = 30s (au lieu de 10s)
    setTimeout(() => waitForApi(tries+1), 50);
  } else {
    document.getElementById('footer-status').textContent = 'API non disponible';
  }
}

async function initAsync() {
  if (_initialized) return;
  _initialized = true;
  try {
    const d = await pywebview.api.get_init_data();
    buildProviders(d.providers || [], d.active_provider || 'fr-ign');
    buildCouches(d.couches);
    buildWfsCouches(d.wfs);
    buildOsmTags(d.osm_tags);
    document.getElementById('f-apikey').value = d.apikey_def || '';
    // Charger l'historique via appel dÃ©diÃ©
    pywebview.api.get_historique().then(hist => {
      if (hist && hist.length) {
        buildHistorique(hist);
        const last = hist[0];
        if (last && last.params) loadConfig(last.params);
      }
    }).catch(e => console.error('get_historique init error:', e));
  } catch(e) {
    console.error('initAsync error:', e);
    document.getElementById('footer-status').textContent = 'Erreur init: ' + e;
  }
}

// â”€â”€ Provider selector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Peuple le <select id="f-provider"> avec la liste des providers disponibles
// et rÃ¨gle la visibilitÃ© des onglets FR-only selon le pays du provider actif.
function buildProviders(providers, activeCode) {
  const sel = document.getElementById('f-provider');
  if (!sel) return;
  if (!providers.length) {
    sel.innerHTML = '<option value="fr-ign">fr-ign (dÃ©faut)</option>';
    sel.value = 'fr-ign';
    sel.dataset.country = 'fr';
    applyProviderCountry('fr');
    return;
  }
  sel.innerHTML = providers.map(p =>
    `<option value="${p.code}" data-country="${p.country}" data-apikey-requise="${p.apikey_requise?1:0}">${p.name}</option>`
  ).join('');
  sel.value = activeCode;
  const opt = sel.options[sel.selectedIndex];
  const country = (opt && opt.dataset.country) || 'fr';
  sel.dataset.country = country;
  applyProviderCountry(country);
  applyProviderApiKey(opt);
  sel.addEventListener('change', () => {
    const o = sel.options[sel.selectedIndex];
    const c = (o && o.dataset.country) || 'fr';
    sel.dataset.country = c;
    applyProviderCountry(c);
    applyProviderApiKey(o);
  });
}

function applyProviderApiKey(opt) {
  // Affiche le champ "ClÃ© API" Ã  cÃ´tÃ© de la dropdown provider si le provider
  // actif l'exige (data-apikey-requise="1"). Sinon cachÃ©.
  const group = document.getElementById('lidar-apikey-group');
  if (!group) return;
  const needs = opt && opt.dataset.apikeyRequise === '1';
  group.style.display = needs ? 'inline-flex' : 'none';
}

function applyProviderCountry(country) {
  // Cache les onglets/labels marquÃ©s data-fr-only="1" si le pays n'est pas FR.
  const elts = document.querySelectorAll('[data-fr-only="1"]');
  elts.forEach(el => {
    el.style.display = (country === 'fr') ? '' : 'none';
    // Cacher aussi le radio input associÃ© si c'est un <label for="...">
    const forId = el.getAttribute('for');
    if (forId) {
      const inp = document.getElementById(forId);
      if (inp) {
        inp.style.display = (country === 'fr') ? '' : 'none';
        // Si l'onglet courant devient invisible, basculer sur LiDAR
        if (country !== 'fr' && inp.checked) {
          const lidarRadio = document.getElementById('t-lidar');
          if (lidarRadio) { lidarRadio.checked = true; lidarRadio.dispatchEvent(new Event('change')); }
        }
      }
    }
  });
}

let _historique = [];

function buildHistorique(hist) {
  _historique = hist || [];
  const list = document.getElementById('hist-list');
  if (!list) return;
  if (!_historique.length) {
    list.innerHTML = '<div style="color:var(--dim);font-size:12px">Aucun traitement enregistrÃ©.</div>';
    return;
  }
  const LABELS = {lidar:'LiDAR',scan:'IGN Raster',osm:'OSM Vectoriel',
                  vecteur:'IGN Vectoriel',fusion:'Fusion',decoupe:'DÃ©coupage'};
  // Marqueur visuel du statut : âœ“ ok (vert), âœ— ko (rouge), âš  en cours (orange,
  // process probablement crashÃ© â€” l'entrÃ©e n'a pas Ã©tÃ© finalisÃ©e).
  const BADGES = {
    'ok':       ['âœ“', '#3b9d3b'],
    'ko':       ['âœ—', '#c44'],
    'en cours': ['âš ', '#e08000'],
  };
  list.innerHTML = _historique.map((e, i) => {
    const zone = e.dep  ? `Dep ${e.dep}`  :
                 e.ville ? e.ville         :
                 e.bbox  ? 'BBox'          :
                 e.gps   ? 'GPS'           : '';
    const st = e.statut || 'ok';  // entrÃ©es prÃ©-v2 : pas de statut â†’ 'ok' implicite
    const [sym, col] = BADGES[st] || ['', 'var(--dim)'];
    return `<div style="border:1px solid var(--bd);border-radius:4px;padding:8px;
                        margin-bottom:6px;cursor:pointer;font-size:12px"
                 onclick="rappelHistorique(${i})">
      <div style="display:flex;justify-content:space-between">
        <strong><span style="color:${col}">${sym}</span> ${LABELS[e.type]||e.type} â€” ${e.nom||'?'}</strong>
        <span style="color:var(--dim)">${e.date}</span>
      </div>
      <div style="color:var(--dim);margin-top:3px">${zone}${zone?' Â· ':''}${e.duree||st}</div>
    </div>`;
  }).join('');
}

function toggleHistorique() {
  const p = document.getElementById('panneau-hist');
  if (p) p.classList.toggle('hidden');
}

async function viderHistorique() {
  const n = (_historique || []).length;
  if (n === 0) {
    alert('L\'historique est dÃ©jÃ  vide.');
    return;
  }
  if (!confirm(`Supprimer ${n} entrÃ©e(s) de l'historique ?\n\n`
             + `Cette action est dÃ©finitive â€” les commandes passÃ©es ne pourront plus `
             + `Ãªtre rappelÃ©es.`)) {
    return;
  }
  try {
    const r = await pywebview.api.clear_historique();
    if (r && r.ok) {
      _historique = [];
      buildHistorique([]);
      const fs = document.getElementById('footer-status');
      if (fs) fs.textContent = `âœ“ Historique vidÃ© (${n} entrÃ©e(s) supprimÃ©e(s))`;
    } else {
      alert('Erreur lors de la suppression : ' + ((r && r.error) || 'inconnue'));
    }
  } catch (e) {
    alert('Erreur lors de la suppression : ' + e);
  }
}

function rappelHistorique(i) {
  const e = _historique[i];
  if (!e || !e.params) return;
  loadConfig(e.params);
  toggleHistorique();
  document.getElementById('footer-status').textContent =
    `ParamÃ¨tres rappelÃ©s : ${e.nom||''} (${e.date})`;
}

function buildCouches(couches) {
  const sel = document.getElementById('f-couche');
  couches.forEach(c => {
    const o = document.createElement('option');
    o.value = c.code; o.textContent = c.label;
    o.dataset.zmin = c.zoom_min; o.dataset.zmax = c.zoom_max;
    o.dataset.restreinte = c.restreinte ? '1' : '0';
    sel.appendChild(o);
  });
  const updateWarning = () => {
    const o = sel.selectedOptions[0];
    const warn = document.getElementById('scan-restriction-warning');
    const apikeyGroup = document.getElementById('apikey-group');
    if (o) {
      document.getElementById('f-zoom-min-s').value = o.dataset.zmin;
      document.getElementById('f-zoom-max-s').value = o.dataset.zmax;
      const restricted = o.dataset.restreinte === '1';
      if (warn) warn.classList.toggle('hidden', !restricted);
      if (apikeyGroup) apikeyGroup.style.display = restricted ? 'flex' : 'none';
    }
  };
  sel.addEventListener('change', updateWarning);
  updateWarning();
}

function buildWfsCouches(wfs) {
  const c = document.getElementById('wfs-checks');
  wfs.forEach(w => {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" name="wfs" value="${w.alias}"${w.alias==='cadastre'?' checked':''}> ${w.label}`;
    c.appendChild(l);
  });
}

function buildOsmTags(tags) {
  const c = document.getElementById('osm-tag-checks');
  const defaults = new Set(['highway=*','waterway=*','boundary=administrative','natural=water']);
  tags.forEach(t => {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" name="osm_tag" value="${t.tag}"${defaults.has(t.tag)?' checked':''}> ${t.label}`;
    c.appendChild(l);
  });
}

// â”€â”€ Autocomplete ville (API Adresse data.gouv.fr / BAN, via proxy Python) â”€â”€â”€
// On passe par pywebview.api.autocomplete_ville plutÃ´t qu'un fetch() direct :
// la page est chargÃ©e via NavigateToString â†’ origin "null" â†’ WebView2 bloque
// le CORS de la BAN. Le proxy Python n'a pas ce problÃ¨me.
// Ã‰chec silencieux : si l'API tombe, le champ reste un input texte normal.
const _AC_DEBOUNCE = 250;
const _AC_MINLEN  = 3;   // Geoplateforme exige >= 3 caractÃ¨res (HTTP 400 sinon)
let _acTimer   = null;
let _acReqId   = 0;          // sÃ©rialise les rÃ©ponses async (annule les vieilles)
let _acResults = [];
let _acIndex   = -1;
const _acCache = new Map();   // prefix.toLowerCase() -> array of items

function _acEsc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function _acFermer() {
  const dd = document.getElementById('f-ville-ac');
  if (dd) dd.classList.add('hidden');
  _acIndex = -1;
}

function _acRendre(items) {
  const dd = document.getElementById('f-ville-ac');
  if (!dd) return;
  if (!items || items.length === 0) { _acFermer(); return; }
  _acResults = items;
  _acIndex   = -1;
  dd.innerHTML = '';
  items.forEach((it, i) => {
    const div = document.createElement('div');
    div.className = 'ac-item';
    div.setAttribute('role', 'option');
    div.dataset.idx = i;
    div.innerHTML = _acEsc(it.label) +
      (it.context ? ' <span class="ac-meta">' + _acEsc(it.context) + '</span>' : '');
    // mousedown plutÃ´t que click : se dÃ©clenche AVANT le blur de l'input,
    // Ã©vitant la fermeture prÃ©maturÃ©e du dropdown.
    div.addEventListener('mousedown', (e) => {
      e.preventDefault();
      _acChoisir(i);
    });
    dd.appendChild(div);
  });
  dd.classList.remove('hidden');
}

function _acChoisir(idx) {
  if (idx < 0 || idx >= _acResults.length) return;
  const it = _acResults[idx];
  const inp = document.getElementById('f-ville');
  if (inp) inp.value = it.label;
  _acFermer();
}

function _acSurleve(delta) {
  if (!_acResults.length) return;
  _acIndex = (_acIndex + delta + _acResults.length) % _acResults.length;
  const dd = document.getElementById('f-ville-ac');
  if (!dd) return;
  Array.from(dd.children).forEach((el, i) => {
    el.classList.toggle('active', i === _acIndex);
  });
  const cur = dd.children[_acIndex];
  if (cur) cur.scrollIntoView({block:'nearest'});
}

async function _acRequete(prefix) {
  // Pays du provider actif : pilote BAN (FR) vs Nominatim (autre)
  const psel = document.getElementById('f-provider');
  const country = (psel && psel.dataset.country) || 'fr';
  // ClÃ© de cache incluant le pays : sinon les rÃ©sultats FR seraient renvoyÃ©s
  // pour la mÃªme saisie en NL aprÃ¨s switch de provider.
  const key = country + '|' + prefix.toLowerCase();
  if (_acCache.has(key)) { _acRendre(_acCache.get(key)); return; }
  const myId = ++_acReqId;
  try {
    if (!(window.pywebview && window.pywebview.api &&
          typeof window.pywebview.api.autocomplete_ville === 'function')) {
      _acFermer();
      return;
    }
    const items = await pywebview.api.autocomplete_ville(prefix, country);
    if (myId !== _acReqId) return;
    const list = Array.isArray(items) ? items : [];
    _acCache.set(key, list);
    if (_acCache.size > 50) {
      _acCache.delete(_acCache.keys().next().value);
    }
    _acRendre(list);
  } catch(e) {
    if (myId === _acReqId) _acFermer();
  }
}

function _acDeclencher() {
  const inp = document.getElementById('f-ville');
  if (!inp) return;
  const v = inp.value.trim();
  if (v.length < _AC_MINLEN) { _acFermer(); return; }
  _acRequete(v);
}

function _acInstaller() {
  const inp = document.getElementById('f-ville');
  if (!inp) return;
  inp.addEventListener('input', () => {
    if (_acTimer) clearTimeout(_acTimer);
    _acTimer = setTimeout(_acDeclencher, _AC_DEBOUNCE);
  });
  inp.addEventListener('keydown', (e) => {
    const dd = document.getElementById('f-ville-ac');
    const visible = dd && !dd.classList.contains('hidden');
    if (e.key === 'ArrowDown') {
      if (!visible) _acDeclencher();
      else { _acSurleve(1); e.preventDefault(); }
    } else if (e.key === 'ArrowUp') {
      if (visible) { _acSurleve(-1); e.preventDefault(); }
    } else if (e.key === 'Enter') {
      if (visible && _acIndex >= 0) {
        _acChoisir(_acIndex);
        e.preventDefault();
      }
    } else if (e.key === 'Escape') {
      if (visible) { _acFermer(); e.preventDefault(); }
    } else if (e.key === 'Tab') {
      if (visible && _acIndex >= 0) _acChoisir(_acIndex);
      else _acFermer();
    }
  });
  // DÃ©lai sur blur pour laisser le mousedown sur un item passer
  inp.addEventListener('blur', () => setTimeout(_acFermer, 150));
  inp.addEventListener('focus', () => {
    const v = inp.value.trim();
    if (v.length >= _AC_MINLEN) _acDeclencher();
  });
}

function bindAll() {
  // Mode zone â€” appliquer l'Ã©tat initial immÃ©diatement
  // MÃªme problÃ¨me que pour 'type' : sr() coche le radio sans tirer 'change',
  // donc loadConfig() doit appeler applyMode() aprÃ¨s sr('mode', ...).
  window.applyMode = function() {
    const cur = document.querySelector('input[name=mode]:checked')?.value || 'ville';
    ['ville','gps','bbox','dep'].forEach(m => {
      const z = document.getElementById('z-'+m);
      if (z) z.classList.toggle('hidden', cur !== m);
    });
  };
  document.querySelectorAll('input[name=mode]').forEach(r => {
    r.addEventListener('change', window.applyMode);
  });
  window.applyMode();
  // Type carte â€” appliquer l'Ã©tat initial immÃ©diatement
  // Fonction rÃ©utilisable : sync sections visibles + body class avec le
  // radio name=type actuellement cochÃ©. AppelÃ©e :
  //   - sur Ã©vÃ©nement 'change' du radio (clic utilisateur)
  //   - une fois au dÃ©marrage (depuis bindAll)
  //   - depuis loadConfig() aprÃ¨s avoir cochÃ© un radio par programme
  //     (parce que el.checked = true ne tire PAS l'Ã©vÃ©nement 'change')
  window.applyType = function() {
    const cur = document.querySelector('input[name=type]:checked')?.value || 'lidar';
    ['lidar','scan','osm','vecteur','fusion','decoupe'].forEach(t => {
      const sec = document.getElementById('sec-'+t);
      if (sec) sec.classList.toggle('hidden', t !== cur);
    });
    document.body.className = 'type-' + cur;
    const secZone = document.querySelector('.sec-zone');
    if (secZone) secZone.classList.toggle('hidden', cur === 'decoupe');
  };
  document.querySelectorAll('input[name=type]').forEach(r => {
    r.addEventListener('change', window.applyType);
  });
  // Appliquer l'Ã©tat initial
  window.applyType();
  // Toggle sections avec checkbox
  // MÃªme problÃ¨me que pour les radios : modifier el.checked par programme
  // (depuis loadConfig) ne tire PAS l'Ã©vÃ©nement 'change'. Donc on expose
  // window.applyToggles() pour que loadConfig puisse forcer la synchro.
  const toggles = [
    ['f-tel',       'body-tel'],
    ['f-no-omb',    'body-omb'],
    ['f-mbtiles-l', 'body-mbt'],
    ['f-tel-s',     'body-tel-s'],
    ['f-tuiles-s',  'body-tuil-s'],
    ['f-tel-osm',   'body-tel-osm'],
    ['f-tuiles-osm','body-tuil-osm'],
    ['f-tel-v',     'body-tel-v'],
    ['f-tuiles-v',  'body-map-v'],
    ['f-tuiles-v',  'row-simplif-v'],
    ['f-fusion-map','row-simplif-fusion'],
  ];
  window.applyToggles = function() {
    toggles.forEach(([cbId, bodyId]) => {
      const cb = document.getElementById(cbId);
      const body = document.getElementById(bodyId);
      if (!cb || !body) return;
      body.classList.toggle('hidden', !cb.checked);
    });
  };
  toggles.forEach(([cbId, bodyId]) => {
    const cb = document.getElementById(cbId);
    if (!cb) return;
    cb.addEventListener('change', window.applyToggles);
  });
  window.applyToggles();
  // Format image LiDAR / IGN raster : masque "QualitÃ© Jpeg" quand PNG est sÃ©lectionnÃ©.
  window.applyFmtL = function() {
    const cur = document.querySelector('input[name=fmt-l]:checked')?.value || 'jpeg';
    const wrap = document.getElementById('wrap-qualite-l');
    if (wrap) wrap.classList.toggle('hidden', cur !== 'jpeg');
  };
  document.querySelectorAll('input[name=fmt-l]').forEach(r => {
    r.addEventListener('change', window.applyFmtL);
  });
  window.applyFmtL();
  window.applyFmtS = function() {
    const cur = document.querySelector('input[name=fmt-s]:checked')?.value || 'jpeg';
    const wrap = document.getElementById('wrap-qualite-s');
    if (wrap) wrap.classList.toggle('hidden', cur !== 'jpeg');
  };
  document.querySelectorAll('input[name=fmt-s]').forEach(r => {
    r.addEventListener('change', window.applyFmtS);
  });
  window.applyFmtS();
}

// â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function getConfig() {
  const g = id => document.getElementById(id);
  const mode = document.querySelector('input[name=mode]:checked')?.value || 'ville';
  const type = document.querySelector('input[name=type]:checked')?.value || 'lidar';
  const rayonId = mode === 'gps' ? 'f-rayon-gps' : 'f-rayon';

  const cfg = {
    type, mode,
    provider: g('f-provider')?.value || 'fr-ign',
    lidar_apikey: g('f-lidar-apikey')?.value.trim(),
    nom:    g('f-nom')?.value.trim(),
    dossier:g('f-dossier')?.value.trim(),
    ville:  g('f-ville')?.value.trim(),
    gps:    g('f-gps')?.value.trim(),
    bbox:   g('f-bbox')?.value.trim(),
    dep:    g('f-dep')?.value.trim(),
    rayon:  parseFloat(g(rayonId)?.value ?? 10),
    // LiDAR
    tel:           g('f-tel')?.checked,
    comp:          g('f-comp')?.checked,
    ecraser_tel:   g('f-ecraser-tel')?.checked,
    workers_l:     parseInt(g('f-workers-l')?.value) || 8,
    dossier_dalles:g('f-dossier-dalles')?.value.trim(),
    no_omb:        g('f-no-omb')?.checked,
    ombrages:      [...document.querySelectorAll('input[name=omb]:checked')].map(c=>c.value),
    elevation:     parseInt(g('f-elevation')?.value) || 25,
    sweep_horizon: g('f-sweep-horizon')?.checked,
    ecraser_omb:   g('f-ecraser-omb')?.checked,
    mbtiles_l:     g('f-mbtiles-l')?.checked && g('f-mbtiles')?.checked,
    rmap:          g('f-mbtiles-l')?.checked && g('f-rmap')?.checked,
    sqlitedb:      g('f-mbtiles-l')?.checked && g('f-sqlitedb')?.checked,
    zoom_min_l:    parseInt(g('f-zoom-min-l')?.value) || 8,
    zoom_max_l:    parseInt(g('f-zoom-max-l')?.value) || 18,
    fmt_l:         document.querySelector('input[name=fmt-l]:checked')?.value || 'jpeg',
    qualite_l:     parseInt(g('f-qualite-l')?.value) || 85,
    ecraser_mbt:   g('f-ecraser-mbt')?.checked,
    cols_decoupe:  parseInt(g('f-priori-cols')?.value)   || 0,
    rows_decoupe:  parseInt(g('f-priori-rows')?.value)   || 0,
    cols_decoupe_s:parseInt(g('f-priori-cols-s')?.value) || 0,
    rows_decoupe_s:parseInt(g('f-priori-rows-s')?.value) || 0,
    rayon_decoupe_l: parseFloat(g('f-rayon-priori-l')?.value) || 0,
    rayon_decoupe_s: parseFloat(g('f-rayon-priori-s')?.value) || 0,
    nettoyage:     g('f-nettoyage')?.checked || g('f-nettoyage-s')?.checked || false,
    purger_inv:    false, purger_zone: false,
    // Scan
    couche:        g('f-couche')?.value,
    apikey:        g('f-apikey')?.value.trim(),
    tel_s:         g('f-tel-s')?.checked,
    workers_s:     parseInt(g('f-workers-s')?.value) || 8,
    ecraser_tel_s: g('f-ecraser-tel-s')?.checked,
    tuiles_s:      g('f-tuiles-s')?.checked,
    zoom_min_s:    parseInt(g('f-zoom-min-s')?.value) || 12,
    zoom_max_s:    parseInt(g('f-zoom-max-s')?.value) || 16,
    mbtiles_s:     g('f-mbtiles-s')?.checked,
    rmap_s:        g('f-rmap-s')?.checked,
    sqlitedb_s:    g('f-sqlitedb-s')?.checked,
    fmt_s:         document.querySelector('input[name=fmt-s]:checked')?.value || 'jpeg',
    qualite_s:     parseInt(g('f-qualite-s')?.value) || 85,
    ecraser_tuil_s:g('f-ecraser-tuil-s')?.checked,
    // OSM
    tel_osm:       g('f-tel-osm')?.checked,
    workers_osm:   parseInt(g('f-workers-osm')?.value) || 4,
    osm_tags_sel:  [...document.querySelectorAll('input[name=osm_tag]:checked')].map(c=>c.value),
    ecraser_tel_osm: g('f-ecraser-tel-osm')?.checked,
    tuiles_osm:    g('f-tuiles-osm')?.checked,
    map:           g('f-map')?.checked,
    osm_geojson:     g('f-osm-geojson')?.checked,
    osm_geojson_raw: g('f-osm-geojson-raw')?.checked,
    ecraser_tuil_osm: g('f-ecraser-tuil-osm')?.checked,
    // Vecteur
    tel_v:         g('f-tel-v')?.checked,
    wfs_couches_sel:[...document.querySelectorAll('input[name=wfs]:checked')].map(c=>c.value),
    workers_v:     parseInt(g('f-workers-v')?.value) || 4,
    ecraser_tel_v: g('f-ecraser-tel-v')?.checked,
    fusion_gz:      g('f-fusion-gz')?.checked,
    fusion_gz_raw:  g('f-fusion-gz-raw')?.checked,
    tuiles_v:      g('f-tuiles-v')?.checked,
    ecraser_tuil_v:g('f-ecraser-tuil-v')?.checked,
    // Fusion
    fusion_fichiers: fusionFiles,
    fusion_gz2:    g('f-fusion-gz2')?.checked,
    fusion_gz2_raw:g('f-fusion-gz2-raw')?.checked,
    fusion_map:    g('f-fusion-map')?.checked,
    simplif_v:     parseFloat(g('f-simplif-v')?.value) || null,
    simplif_fusion:parseFloat(g('f-simplif-fusion')?.value) || null,
    // DÃ©coupage raster (Ã  posteriori)
    source_decoupe:  g('f-source-decoupe')?.value.trim(),
    cols_decoupe_d:  parseInt(g('f-cols-decoupe')?.value) || 1,
    rows_decoupe_d:  parseInt(g('f-rows-decoupe')?.value) || 1,
    rayon_decoupe_d: parseFloat(g('f-rayon-decoupe-d')?.value) || 0,
    mbtiles_d:       g('f-mbtiles-d')?.checked,
    rmap_d:          g('f-rmap-d')?.checked,
    sqlitedb_d:      g('f-sqlitedb-d')?.checked,
    ecraser_d:       g('f-ecraser-d')?.checked,
  };
  // Remap scan rmap/sqlitedb
  // Remap scan : unifier les clÃ©s de format pour _build_cmd
  // (supprimÃ© â€” _build_cmd lit directement mbtiles_s/rmap_s/sqlitedb_s)
  return cfg;
}

function loadConfig(cfg) {
  const s  = (id, val) => { const el = document.getElementById(id);
    if (!el || val === undefined || val === null) return;
    if (el.type === 'checkbox') el.checked = !!val; else el.value = val; };
  const sr = (name, val) => { const r = document.querySelector(`input[name=${name}][value="${val}"]`);
    if (r) r.checked = true; };

  // Normaliser les zooms hÃ©ritÃ©s d'un historique antÃ©rieur Ã  _valider_zooms.
  // Si min > max sur n'importe quelle paire (LiDAR / Raster / DÃ©coupe), on
  // swap silencieusement et on prÃ©vient via le footer. Sans Ã§a, un clic sur
  // une vieille entrÃ©e recharge des valeurs que le pipeline refusera.
  let _swapped = false;
  for (const [kmin, kmax] of [
    ['zoom_min_l', 'zoom_max_l'],
    ['zoom_min_s', 'zoom_max_s'],
    ['zoom_min_d', 'zoom_max_d'],
  ]) {
    const a = cfg[kmin], b = cfg[kmax];
    if (typeof a === 'number' && typeof b === 'number' && a > b) {
      cfg[kmin] = b; cfg[kmax] = a;
      _swapped = true;
    }
  }
  if (_swapped) {
    const fs = document.getElementById('footer-status');
    if (fs) fs.textContent = 'âš  Zooms d\'historique inversÃ©s â€” corrigÃ©s au chargement';
  }

  // Zone
  if (cfg.mode) sr('mode', cfg.mode);
  if (cfg.type) sr('type', cfg.type);
  // (window.applyMode/applyType seront rappelÃ©es en fin de loadConfig
  //  pour synchroniser les sections visibles avec les radios cochÃ©s)

  // Provider (multi-pays) â€” restaurÃ© depuis l'historique si prÃ©sent
  if (cfg.provider) {
    const psel = document.getElementById('f-provider');
    if (psel && psel.querySelector(`option[value="${cfg.provider}"]`)) {
      psel.value = cfg.provider;
      psel.dispatchEvent(new Event('change'));
    }
  }

  // Projet
  s('f-nom',     cfg.nom);
  s('f-dossier', cfg.dossier);

  // Zone gÃ©o
  s('f-ville',   cfg.ville);
  s('f-gps',     cfg.gps);
  s('f-bbox',    cfg.bbox);
  s('f-dep',     cfg.dep);
  s('f-rayon',     cfg.rayon);
  s('f-rayon-gps', cfg.rayon);


  // LiDAR
  s('f-tel',            cfg.no_tel !== undefined ? !cfg.no_tel : cfg.tel);
  s('f-comp',           cfg.comp);
  s('f-ecraser-tel',    cfg.ecraser_tel);          // FIX: Ã©tait cfg.ecraser_tel_l
  s('f-workers-l',      cfg.workers_l);
  s('f-dossier-dalles', cfg.dossier_dalles);
  s('f-no-omb',         cfg.no_omb);
  s('f-elevation',      cfg.elevation);
  s('f-sweep-horizon',  cfg.sweep_horizon);
  s('f-ecraser-omb',    cfg.ecraser_omb);          // FIX: Ã©tait cfg.ecraser_omb_l
  // FIX: f-mbtiles-l (section "calculer les tuiles") n'Ã©tait jamais restaurÃ©
  s('f-mbtiles-l',      cfg.mbtiles_l || cfg.rmap || cfg.sqlitedb || false);
  s('f-mbtiles',        cfg.mbtiles_l !== undefined ? cfg.mbtiles_l : (cfg.mbtiles !== undefined ? cfg.mbtiles : false));
  s('f-rmap',           cfg.rmap);
  s('f-sqlitedb',       cfg.sqlitedb);
  s('f-zoom-min-l',     cfg.zoom_min_l);
  s('f-zoom-max-l',     cfg.zoom_max_l);
  if (cfg.fmt_l) sr('fmt-l', cfg.fmt_l);
  s('f-qualite-l',      cfg.qualite_l);
  s('f-ecraser-mbt',    cfg.ecraser_mbt);          // FIX: Ã©tait cfg.ecraser_mbt_l
  s('f-priori-cols',   cfg.cols_decoupe);
  s('f-priori-rows',   cfg.rows_decoupe);
  s('f-priori-cols-s', cfg.cols_decoupe_s);
  s('f-priori-rows-s', cfg.rows_decoupe_s);
  s('f-rayon-priori-l', cfg.rayon_decoupe_l);
  s('f-rayon-priori-s', cfg.rayon_decoupe_s);
  // FIX: f-nettoyage et f-nettoyage-s n'Ã©taient jamais restaurÃ©s
  s('f-nettoyage',   cfg.nettoyage);
  s('f-nettoyage-s', cfg.nettoyage);

  // ClÃ© API LiDAR (us-3dep) â€” persistÃ©e sÃ©parÃ©ment de l'IGN scan
  s('f-lidar-apikey',   cfg.lidar_apikey);

  // Scan IGN raster
  s('f-couche',         cfg.couche);
  s('f-apikey',         cfg.apikey);
  s('f-tel-s',          cfg.tel_s !== undefined ? cfg.tel_s : true);
  s('f-workers-s',      cfg.workers_s);
  s('f-ecraser-tel-s',  cfg.ecraser_tel_s);
  s('f-tuiles-s',       cfg.tuiles_s !== undefined ? cfg.tuiles_s : true);
  s('f-zoom-min-s',     cfg.zoom_min_s);
  s('f-zoom-max-s',     cfg.zoom_max_s);
  s('f-mbtiles-s',      cfg.mbtiles_s !== undefined ? cfg.mbtiles_s : true);
  s('f-rmap-s',         cfg.rmap_s);               // FIX: Ã©tait cfg.rmap (clÃ© LiDAR !)
  s('f-sqlitedb-s',     cfg.sqlitedb_s);            // FIX: Ã©tait cfg.sqlitedb (clÃ© LiDAR !)
  if (cfg.fmt_s) sr('fmt-s', cfg.fmt_s);
  s('f-qualite-s',      cfg.qualite_s);
  s('f-ecraser-tuil-s', cfg.ecraser_tuil_s);

  // OSM
  s('f-tel-osm',          cfg.tel_osm !== undefined ? cfg.tel_osm : true);
  s('f-workers-osm',      cfg.workers_osm);         // FIX: n'Ã©tait jamais restaurÃ©
  s('f-ecraser-tel-osm',  cfg.ecraser_tel_osm);
  s('f-tuiles-osm',       cfg.tuiles_osm !== undefined ? cfg.tuiles_osm : true);
  s('f-map',              cfg.map !== undefined ? cfg.map : true);
  s('f-osm-geojson',      cfg.osm_geojson !== undefined ? cfg.osm_geojson : true);
  s('f-osm-geojson-raw',  cfg.osm_geojson_raw);
  s('f-ecraser-tuil-osm', cfg.ecraser_tuil_osm);
  // FIX: Ã©tait cfg.osm_tags â€” la clÃ© sauvÃ©e par getConfig est osm_tags_sel
  if (cfg.osm_tags_sel) {
    const tagSet = new Set(typeof cfg.osm_tags_sel === 'string'
      ? cfg.osm_tags_sel.split(' ') : cfg.osm_tags_sel);
    document.querySelectorAll('input[name=osm_tag]').forEach(c => {
      c.checked = tagSet.has(c.value);
    });
  }

  // IGN Vectoriel
  s('f-tel-v',          cfg.tel_v !== undefined ? cfg.tel_v : true);
  s('f-workers-v',      cfg.workers_v);
  s('f-ecraser-tel-v',  cfg.ecraser_tel_v);
  s('f-fusion-gz',      cfg.fusion_gz !== undefined ? cfg.fusion_gz : true);
  s('f-fusion-gz-raw',  cfg.fusion_gz_raw);
  s('f-tuiles-v',       cfg.tuiles_v);
  s('f-ecraser-tuil-v', cfg.ecraser_tuil_v);
  // FIX: Ã©tait cfg.wfs_couches â€” la clÃ© sauvÃ©e par getConfig est wfs_couches_sel
  if (cfg.wfs_couches_sel) {
    const wfsSet = new Set(typeof cfg.wfs_couches_sel === 'string'
      ? cfg.wfs_couches_sel.split(' ') : cfg.wfs_couches_sel);
    document.querySelectorAll('input[name=wfs]').forEach(c => {
      c.checked = wfsSet.has(c.value);
    });
  }

  // Fusion
  s('f-fusion-gz2',     cfg.fusion_gz2 !== undefined ? cfg.fusion_gz2 : true);
  s('f-fusion-gz2-raw', cfg.fusion_gz2_raw);        // FIX: n'Ã©tait jamais restaurÃ©
  s('f-fusion-map',     cfg.fusion_map);             // FIX: n'Ã©tait jamais restaurÃ©
  if (cfg.simplif_v     != null) { const el=g('f-simplif-v');     if(el) el.value=cfg.simplif_v; }
  if (cfg.simplif_fusion!= null) { const el=g('f-simplif-fusion');if(el) el.value=cfg.simplif_fusion; }
  if (cfg.fusion_fichiers) {
    fusionFiles = cfg.fusion_fichiers;
    renderFusionList();
  }

  // DÃ©coupage raster
  s('f-source-decoupe',  cfg.source_decoupe);
  s('f-cols-decoupe',  cfg.cols_decoupe_d);
  s('f-rows-decoupe',  cfg.rows_decoupe_d);
  s('f-rayon-decoupe-d', cfg.rayon_decoupe_d);
  s('f-mbtiles-d',       cfg.mbtiles_d !== undefined ? cfg.mbtiles_d : true);
  s('f-rmap-d',          cfg.rmap_d);
  s('f-sqlitedb-d',      cfg.sqlitedb_d);
  s('f-ecraser-d',       cfg.ecraser_d);

  // Ombrages
  if (cfg.ombrages) {
    const ombSet = new Set(Array.isArray(cfg.ombrages)
      ? cfg.ombrages : Object.keys(cfg.ombrages).filter(k => cfg.ombrages[k]));
    document.querySelectorAll('input[name=omb]').forEach(c => {
      c.checked = ombSet.has(c.value);
    });
  }

  // Re-dÃ©clencher les toggles et l'Ã©tat initial.
  // NB : les fonctions window.apply* sont dÃ©finies par bindAll() et appelÃ©es
  // directement (au lieu d'un dispatchEvent('change') qui peut Ã©chouer
  // silencieusement selon le timing async d'attache des listeners pywebview).
  if (typeof window.applyMode    === 'function') window.applyMode();
  if (typeof window.applyType    === 'function') window.applyType();
  if (typeof window.applyToggles === 'function') window.applyToggles();
  if (typeof window.applyFmtL    === 'function') window.applyFmtL();
  if (typeof window.applyFmtS    === 'function') window.applyFmtS();
}

// â”€â”€ Dialogs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function pickDir(fieldId) {
  const p = await pywebview.api.pick_dir();
  if (p) document.getElementById(fieldId).value = p;
}
async function pickFile(fieldId, multiple, exts) {
  const p = await pywebview.api.pick_file(multiple, false, exts);
  if (p) document.getElementById(fieldId).value = Array.isArray(p) ? p.join(';') : p;
}
async function pickFileSave(fieldId) {
  const p = await pywebview.api.pick_file(false, true, []);
  if (p) document.getElementById(fieldId).value = p;
}
async function fusionAjouter() {
  const files = await pywebview.api.pick_file(true, false, []);
  if (!files) return;
  const all = Array.isArray(files) ? files : [files];
  const valid = all.filter(f => f.endsWith('.geojson') || f.endsWith('.gz'));
  const invalid = all.filter(f => !f.endsWith('.geojson') && !f.endsWith('.gz'));
  if (invalid.length) alert(`IgnorÃ©(s) : ${invalid.map(f=>f.split(/[\\/]/).pop()).join(', ')}\nSeuls .geojson et .geojson.gz sont acceptÃ©s.`);
  valid.forEach(f => { if (!fusionFiles.includes(f)) fusionFiles.push(f); });
  renderFusionList();
}
function fusionSupprimer() {
  if (fusionSel >= 0) { fusionFiles.splice(fusionSel, 1); fusionSel = -1; renderFusionList(); }
}
function fusionVider() { fusionFiles = []; fusionSel = -1; renderFusionList(); }
function renderFusionList() {
  const c = document.getElementById('fusion-list');
  c.innerHTML = fusionFiles.map((f,i) =>
    `<div class="${i===fusionSel?'sel':''}" onclick="fusionSelect(${i})">${f.split(/[\\/]/).pop()}</div>`
  ).join('');
}
function fusionSelect(i) { fusionSel = i; renderFusionList(); }

// â”€â”€ Lancement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function setFormLocked(locked) {
  const els = document.getElementById('main')
    .querySelectorAll('input,select,button:not(#btn-stop):not(#btn-log)');
  els.forEach(el => { el.disabled = locked; });
}

async function lancer() {
  const nom = document.getElementById('f-nom').value.trim();
  if (!nom) { alert('Le nom du projet est obligatoire.'); return; }
  const cfg = getConfig();
  if (cfg.type === 'decoupe' && !cfg.source_decoupe) {
    alert('Le fichier source MBTiles est obligatoire.');
    return;
  }
  // Valider que la zone gÃ©ographique est renseignÃ©e (sauf Fusion et DÃ©coupage raster)
  if (cfg.type !== 'fusion' && cfg.type !== 'decoupe') {
    const zoneOk = (cfg.mode === 'ville'  && cfg.ville) ||
                   (cfg.mode === 'gps'    && cfg.gps)   ||
                   (cfg.mode === 'bbox'   && cfg.bbox)  ||
                   (cfg.mode === 'dep'    && cfg.dep)   ||
                    false;
    if (!zoneOk) {
      const labels = {ville:'Ville', gps:'GPS', bbox:'BBox', dep:'DÃ©partement'};
      alert(`Le champ "${labels[cfg.mode] || cfg.mode}" est obligatoire.`);
      return;
    }
  }
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  document.getElementById('footer-status').textContent = 'En cours...';
  setFormLocked(true);

  // Vider le panneau de log et prÃ©parer la barre de progression
  viderLog();
  document.getElementById('log-status').textContent = 'En cours...';
  setLogProgress(0, '');

  const res = await pywebview.api.launch(cfg);
  if (res && res.error) { alert(res.error); btnReset(); return; }

  // Afficher la commande lancÃ©e dans le footer
  // (elle est aussi mise dans la log queue cÃ´tÃ© Python, ne pas dupliquer ici)
  document.getElementById('footer-status').textContent = 'â–¶ ' + (res.cmd || '').split(' ').slice(-3).join(' ') + 'â€¦';

  polling = setInterval(async () => {
    const r = await pywebview.api.poll_log();
    if (r.items) {
      r.items.forEach(item => {
        // Lignes de texte â†’ panneau de log avec colorisation par tag
        if (item.line !== undefined) {
          ajouterLigneLog(item.line, item.tag || 'ok');
        }
        // Pourcentage (carriage return du child) â†’ barre de progression + footer
        if (item.pct !== undefined && item.pct >= 0) {
          setLogProgress(item.pct, '');
          document.getElementById('footer-status').textContent =
            item.pct + '%  ' + (item.label || '').substring(0, 80);
        }
        // Label seul (action en cours sans pct) â†’ footer
        if (item.pct === -1 && item.label) {
          document.getElementById('footer-status').textContent =
            item.label.substring(0, 100);
        }
      });
    }
    if (r.done) {
      clearInterval(polling); polling = null;
      document.getElementById('footer-status').textContent =
        r.code === 0 ? 'âœ“ TerminÃ©' : `âœ— Erreur (code ${r.code})`;
      document.getElementById('log-status').textContent =
        r.code === 0 ? 'âœ“ TerminÃ©' : `âœ— Erreur (code ${r.code})`;
      setLogProgress(100, r.code === 0 ? 'ok' : 'err');
      // RÃ©cap d'erreur en fin de run via API dÃ©diÃ©e (plus fiable que
      // le passage par poll_log : pywebview/WebView2 peut perdre des
      // clÃ©s non-standard dans les dicts complexes sÃ©rialisÃ©s).
      if (r.code !== 0) {
        // Erreur â†’ ouvrir automatiquement le panneau de log s'il est cachÃ©,
        // sinon le message "voir le panneau" est inutile.
        const p = document.getElementById('panneau-log');
        if (p && p.classList.contains('hidden')) {
          toggleLogPanel();
        }
        try {
          const err = await pywebview.api.get_last_error();
          if (err && err.msg) {
            alert(`Le traitement a Ã©chouÃ© (code ${err.retcode}).\n\n`
                + err.msg
                + `\n\n(dÃ©tails complets dans le panneau de log ci-dessous)`);
          } else {
            // Fallback gÃ©nÃ©rique si _modal_error_msg n'a pas Ã©tÃ© rempli
            alert(`Le traitement a Ã©chouÃ© (code ${r.code}).\n\n`
                + `Voir le panneau de log ci-dessous pour les dÃ©tails.`);
          }
        } catch (e) {
          console.error('get_last_error:', e);
          alert(`Le traitement a Ã©chouÃ© (code ${r.code}).\n\n`
              + `Voir le panneau de log ci-dessous pour les dÃ©tails.`);
        }
      }
      if (r.code === 0) {
        // Recharger l'historique via appel dÃ©diÃ© (plus fiable que poll_log)
        pywebview.api.get_historique().then(hist => {
          if (hist && hist.length) {
            buildHistorique(hist);
            const last = hist[0];
            if (last && last.params) loadConfig(last.params);
          }
        }).catch(e => console.error('get_historique error:', e));
        if (r.result_dir) pywebview.api.open_folder(r.result_dir);
      }
      btnReset();
    }
  }, 250);
}

async function arreter() {
  await pywebview.api.stop();
  if (polling) { clearInterval(polling); polling = null; }
  document.getElementById('footer-status').textContent = 'âš  ArrÃªtÃ©';
  btnReset();
}

function btnReset() {
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  setFormLocked(false);
}
  // â”€â”€ Zoom Ctrl+molette â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Fonctionne sur tous les OS et clients VNC (RealVNC Windows â†’ macOS VM).
  // Ctrl+molette haut = zoom in, Ctrl+molette bas = zoom out.
  // Pinch-to-zoom trackpad fonctionne nativement via le navigateur embarquÃ©.
  (function() {
    let _zoomLevel = 1.0;
    const _ZOOM_STEP = 0.1;
    const _ZOOM_MIN  = 0.5;
    const _ZOOM_MAX  = 2.5;
    document.addEventListener('wheel', function(e) {
      if (!e.ctrlKey) return;
      e.preventDefault();
      _zoomLevel += e.deltaY < 0 ? _ZOOM_STEP : -_ZOOM_STEP;
      _zoomLevel  = Math.min(_ZOOM_MAX, Math.max(_ZOOM_MIN, _zoomLevel));
      document.body.style.zoom = _zoomLevel;
    }, { passive: false });
    // Ctrl+0 pour rÃ©initialiser le zoom
    document.addEventListener('keydown', function(e) {
      if (e.ctrlKey && (e.key === '0' || e.key === 'NumPad0')) {
        e.preventDefault();
        _zoomLevel = 1.0;
        document.body.style.zoom = 1.0;
      }
    });
  })();
</script>
</body>
</html>"""

    api = Api()

    # Profile WebView2 isolÃ© par instance â€” Ã©vite les conflits quand plusieurs
    # GUI tournent simultanÃ©ment ou si une instance prÃ©cÃ©dente n'a pas relÃ¢chÃ©
    # son contexte. Chaque PID a son propre user_data_folder dans %TEMP%/
    # lidar2map_wv2_<pid>/, nettoyÃ© Ã  la sortie.
    # SymptÃ´me typique sans cette isolation : "API non disponible" aprÃ¨s 10s
    # parce que pywebview.api n'arrive pas Ã  s'attacher au navigator (conflit).
    if WINDOWS:
        import atexit, tempfile
        _wv2_profile = Path(tempfile.gettempdir()) / f"lidar2map_wv2_{os.getpid()}"
        _wv2_profile.mkdir(parents=True, exist_ok=True)
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(_wv2_profile)
        def _cleanup_wv2_profile():
            try:
                import shutil
                shutil.rmtree(_wv2_profile, ignore_errors=True)
            except Exception:
                pass
        atexit.register(_cleanup_wv2_profile)

    win = webview.create_window(
        "lidar2map â€” Cartes offline LiDAR/IGN/OSM",
        html=HTML,
        js_api=api,
        width=1300, height=850,
        min_size=(1000, 600),
        zoomable=True,   # active Ctrl+molette (Edge WebView2 sur Windows)
    )
    # Assigner la fenÃªtre immÃ©diatement â€” disponible dÃ¨s create_window
    api.window = win

    # Workaround pywebview/WebView2 : la couche AccessibilityObject de WebView2
    # peut entrer en rÃ©cursion infinie cÃ´tÃ© Python lors de l'inspection de
    # l'arbre accessibility (cycles Empty.Empty.Empty...). Limite par dÃ©faut
    # 1000 = insuffisant. 10000 Ã©vite le crash sans risque pratique.
    sys.setrecursionlimit(100000)

    # Activable via flag --debug (clic droit â†’ Inspect dans la fenÃªtre webview,
    # ou F12, pour ouvrir les DevTools et voir la console JS).
    _wv_debug = "--debug" in sys.argv
    webview.start(debug=_wv_debug)


def _normaliser_argv_valeurs_negatives():
    """Recolle les valeurs nÃ©gatives Ã  leur flag pour qu'argparse les accepte.

    Argparse considÃ¨re par dÃ©faut tout token commenÃ§ant par '-' comme un nouveau
    flag, ce qui casse les commandes du type :
        --zone-bbox -108.5,37.18,-108.48,37.20
    car '-108.5,...' est vu comme un flag inconnu.

    Solution : pour chaque flag connu qui prend une valeur, si le token suivant
    commence par '-' et contient une virgule (pattern typique bbox/gps), on
    fusionne avec '=' (forme acceptÃ©e nativement par argparse).
    """
    FLAGS_VALEUR = (
        "--zone-bbox", "--zone-gps",
        "--bbox",   # alias historique Ã©ventuels
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
        # --debug (DevTools WebView2) est un flag GUI-only. On le dÃ©tecte tÃ´t
        # pour qu'il ne perturbe pas argparse en aval (qui ne le reconnaÃ®t pas).
        # Lu directement dans sys.argv par lancer_gui() avant strip.
        _is_only_debug = (len(sys.argv) == 2 and sys.argv[1] == "--debug")
        if len(sys.argv) == 1 or _is_only_debug:
            lancer_gui()
        else:
            # â”€â”€ DÃ©tection du mode via un PRÃ‰-PARSER argparse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Au lieu de `if "--decouper" in sys.argv: ...` (grep, susceptible
            # de matcher dans la valeur d'un autre argument), on utilise un
            # parser dÃ©diÃ© Ã  1 seul argument actif Ã  la fois. Les flags d'origine
            # sont prÃ©servÃ©s tels quels (compat ascendante des commandes
            # partagÃ©es sur les forums).
            #
            # Note : `argparse` avec parse_known_args() consomme uniquement le
            # mode et laisse intact le reste de sys.argv pour le sub-main.
            _DISPATCH = {
                "decouper":   main_decouper,
                "ignraster":  main_wmts,
                "ignvecteur": main_wfs,
                "fusionner":  main_fusionner,
                # Tous les autres modes (--ignlidar, --osm, ou cumulÃ©s) tombent
                # sur main() qui sait les gÃ©rer.
            }
            _pre = argparse.ArgumentParser(add_help=False)
            for _flag in _DISPATCH:
                _pre.add_argument(f"--{_flag}", action="store_true",
                                  dest=f"_mode_{_flag}")
            _ns_pre, _ = _pre.parse_known_args()

            def _dispatch():
                # PrioritÃ© ordonnÃ©e : on prend le 1er mode trouvÃ© dans la liste.
                # Cet ordre matche celui de l'ancien dispatcher (decouper avant
                # ignraster, etc.) pour prÃ©server le comportement.
                for _flag, _fn in _DISPATCH.items():
                    if getattr(_ns_pre, f"_mode_{_flag}", False):
                        return _fn()
                return main()    # --ignlidar / --osm / par dÃ©faut

            # â”€â”€ RÃ©solution multi-dÃ©partement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # --zone-departement accepte : 83 | 30,35,75 | 1-10 | 1-3,75,83
            _dep_idx = None
            for _i, _a in enumerate(sys.argv):
                if _a == "--zone-departement" and _i + 1 < len(sys.argv):
                    _dep_idx = _i + 1
                    break

            _deps = _parser_departements(sys.argv[_dep_idx]) if _dep_idx else None

            if _deps and len(_deps) > 1:
                _argv_base = sys.argv[:]
                _sep = "â•" * 55
                # DÃ©tecter --zone-nom explicite : sera suffixÃ© par _<dep> pour Ã©viter
                # que les sorties multi-dÃ©partement s'Ã©crasent mutuellement.
                _nom_idx = None
                _nom_base = None
                for _i, _a in enumerate(_argv_base):
                    if _a == "--zone-nom" and _i + 1 < len(_argv_base):
                        _nom_idx  = _i + 1
                        _nom_base = _argv_base[_nom_idx]
                        break
                for _n, _dep in enumerate(_deps, 1):
                    print()
                    print(_sep)
                    print(f"  DÃ©partement {_dep}  ({_n}/{len(_deps)})")
                    print(_sep)
                    sys.argv = _argv_base[:]
                    sys.argv[_dep_idx] = _dep
                    # Suffixer le nom explicite avec le numÃ©ro de dÃ©partement
                    if _nom_idx is not None:
                        sys.argv[_nom_idx] = f"{_nom_base}_{_dep}"
                    _dispatch()
            else:
                _dispatch()
    except KeyboardInterrupt:
        # Cancellation propre : raisÃ©e par print_etape() ou _svf_numpy()
        # quand _stop_event a Ã©tÃ© set par Ctrl+C. Le finally restaure stdout
        # avant que Python imprime un message synthÃ©tique.
        _historique_fin_crash()   # marque l'entrÃ©e 'en cours' comme 'ko'
        print("\n\n  Traitement interrompu par l'utilisateur.", flush=True)
        sys.exit(130)
    except SystemExit as _e_sysexit:
        # sys.exit() avec code != 0 = Ã©chec â†’ marquer l'entrÃ©e 'en cours' 'ko'.
        # (code 0 ou None = succÃ¨s â†’ ne rien faire ; succÃ¨s est dÃ©jÃ  gÃ©rÃ© par
        # _historique_depuis_argv dans chaque main_*())
        if _e_sysexit.code not in (None, 0):
            _historique_fin_crash()
        raise
    except BaseException:
        # Toute autre exception non rattrapÃ©e par les main_*() : marquer 'ko'
        # avant de laisser Python imprimer la traceback.
        _historique_fin_crash()
        raise
    finally:
        if isinstance(sys.stdout, _TeeLogger):
            sys.stdout.close()
            sys.stdout = sys.stdout._terminal if hasattr(sys.stdout, "_terminal") else sys.__stdout__