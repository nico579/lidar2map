# archeo_terrain.py — Prospection LiDAR archéologique & cartes offline pour Locus Map Pro
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
archeo_terrain.py — Prospection archéologique LiDAR & cartes offline
======================================================================

Script unifié 5 modes pour Locus Map Pro / OsmAnd / TwoNav.

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
  --zone-departement NUM      Département français (ex: 83)
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
    --ombrages TYPE...          Ombrages à générer :
                                  315 045 135 225 multi slope svf svf100 lrm rrim
                                  tous | aucun
    --ombrages-elevation DEG    Angle solaire en degrés (défaut: 25)
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
    Ombrage RRIM (SVF + slope)         : ~8 min
    MBTiles z8-18 (495 tuiles)         : ~5 s
    MBTiles z8-18 (zone 400 km²)       : ~5-10 min

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE --ignraster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Télécharge des tuiles WMTS IGN dans un MBTiles.
  Cache tuiles dans ign_raster/<nom>/dalles/<z>/<x>/<y>.<ext>.

  Couches disponibles :
    planign     Plan IGN v2 (png, public, z6-18)              ← recommandé particuliers
    etatmajor40 État-Major 1/40000 (jpeg, public, z6-15)
    etatmajor10 État-Major 1/10000 (jpeg, public, z8-16)
    pentes      Carte des pentes (png, public, z6-14)
    ortho       Orthophotos (jpeg, public, z10-20)
    cadastre    Parcellaire express (png, public, z12-19)
    ombrage     Ombrage IGN (png, public, z6-14)
    scan25      Scan 25 000 (jpeg, z8-18)    ⚠ PRO — clé API requise
    scan25tour  Scan 25 Tourisme (jpeg, z8-18) ⚠ PRO — clé API requise
    scan100     Scan 100 000 (jpeg, z6-14)   ⚠ PRO — clé API requise
    scanoaci    Scan OACI (jpeg, z6-15)       ⚠ PRO — clé API requise

  Note : scan25 au-delà de z16 → IGN bascule automatiquement vers planIGN.
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
      ign_raster/
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
  --oui                 Mode non-interactif (pas de questions)
  --nettoyage           Supprimer les fichiers intermédiaires après chaque
                          morceau (dalles, TIF ombrages, TIF warpé).
                          Conserve les sorties finales (.mbtiles .rmap .sqlitedb).
                          Indispensable pour les grandes zones (département entier).
  --version             Afficher la version

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

  Python 3.8+  Dépendances auto-installées : Pillow, rasterio,
               numpy, scipy, mapbox-vector-tile
  GDAL         Téléchargé automatiquement dans bin/gdal/ (Windows)
               ou via OSGeo4W/système (Linux/macOS)
  osmosis      Téléchargé automatiquement dans bin/osmosis/
  JRE Temurin  Téléchargé automatiquement dans bin/jre/
  mapwriter    Téléchargé automatiquement dans ~/.openstreetmap/osmosis/plugins/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXEMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

  # LiDAR : depuis TIF existant → RMAP uniquement
  python lidar2map.py --ignlidar --zone-ville gareoult --zone-rayon 1 \
      --zone-nom aa --source ign_lidar/aa/_warped_aa_multi_ombrage_z18.tif \
      --formats-fichier rmap --zoom-min 8 --zoom-max 18 --oui

  # IGN Raster public (pas de clé requise)
  python lidar2map.py --ignraster --zone-ville gareoult --zone-rayon 10 \
      --zone-nom aa --couche planign \
      --formats-fichier mbtiles rmap --zoom-min 8 --zoom-max 18 --oui

  # IGN Raster Scan 25 (professionnel uniquement — clé API requise)
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

  # Zone par département entier (Var)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --workers 8 --ombrages multi --formats-fichier mbtiles --oui

  # Découpage à priori : grande zone en 4×4 morceaux avec nettoyage disque
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage --oui

  # Reprise après interruption (même commande — les morceaux terminés sont ignorés)
  python lidar2map.py --ignlidar --zone-departement 83 \
      --telechargement --ombrages multi svf lrm --formats-fichier mbtiles \
      --cols-decoupe 4 --rows-decoupe 4 --nettoyage --oui
"""
import os
import re
import sys
import queue
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
import platform
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Vérification version Python
if sys.version_info < (3, 8):
    print("ERREUR : Python 3.8 minimum requis (version actuelle : "
          + str(sys.version_info.major) + "." + str(sys.version_info.minor) + ")")
    print("Téléchargez Python 3.8+ sur https://www.python.org/downloads/")
    sys.exit(1)

# ============================================================
# INSTALLATION AUTOMATIQUE DES DÉPENDANCES
# ============================================================

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
        print("  pip installé.")
    except Exception as e:
        print(f"  ERREUR bootstrap pip : {e}")
        print("  Installez pip manuellement : https://pip.pypa.io/en/stable/installation/")
        sys.exit(1)

_bootstrap_pip()

def _installer_deps():
    deps = []
    for mod, pkg in [
        ("PIL",       "Pillow"),
        ("pyproj",    "pyproj"),
        ("numpy",     "numpy"),
        ("scipy",     "scipy"),
    ]:
        try:
            __import__(mod)
        except ImportError:
            deps.append(pkg)
    # Numba est optionnel (~500 Mo) — accélère SVF ×15-50 mais pas critique
    try:
        import numba  # noqa
    except ImportError:
        print("  INFO : numba absent — SVF utilisera numpy (plus lent mais fonctionnel).")
        print("         Pour activer l'accélération : pip install numba  (~500 Mo)")
    if deps:
        print(f"  Installation : {', '.join(deps)}...")
        cmd = [sys.executable, "-m", "pip", "install"] + deps + ["-q"]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            # Fallback --user si env géré extérieurement (PEP 668 / Linux)
            r2 = subprocess.run(cmd + ["--user"], capture_output=True)
            if r2.returncode != 0:
                print(f"  AVERTISSEMENT : installation partielle ({', '.join(deps)})")
                print("  Installez manuellement : pip install " + " ".join(deps))


_installer_deps()

# ============================================================
# LOGGING
# ============================================================

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
        try:
            self._terminal.write(msg)
        except UnicodeEncodeError:
            self._terminal.write(msg.encode(self._terminal.encoding or "cp1252",
                                             errors="replace").decode(
                                             self._terminal.encoding or "cp1252"))
        if "\r" in msg:
            self._terminal.flush()

        # ── Log ──────────────────────────────────────────────────────────────
        # Traiter caractère par caractère pour gérer \r et \n proprement
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

    def flush(self):
        self._terminal.flush()
        self._log.flush()

    def close(self):
        # Flush des buffers résiduels
        remaining = self._buf or self._cr_buf
        if remaining:
            self._log_line(remaining)
        self._log.close()

def _activer_log():
    import atexit
    log_dir = Path(__file__).resolve().parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _probe = log_dir / ".write_test"
        _probe.touch()
        _probe.unlink()
    except OSError:
        # logs/ inaccessible → log console uniquement, pas de fichier système
        print("  AVERTISSEMENT : dossier logs/ inaccessible, log console uniquement.")
        return
    nom = "lidar_" + time.strftime("%Y%m%d_%H%M%S") + ".log"
    log_path = log_dir / nom
    tee = _TeeLogger(log_path)
    sys.stdout = tee
    sys.stderr = tee   # stderr → même log (tracebacks, warnings)
    atexit.register(lambda: (sys.stdout.close()
                    if isinstance(sys.stdout, _TeeLogger) else None))
    # ── Intercepter les exceptions non gérées → log avant exit ───────────────
    import traceback as _tb
    def _excepthook(exc_type, exc_value, exc_tb):
        print("\nEXCEPTION NON GÉRÉE :")
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
# _enregistrer_fichier() fonctionne via un context manager thread-local —
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
            except Exception:
                pass
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

    def _sauver(self):
        try:
            self.path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass


@_contextmanager
def _contexte_manifeste(manifeste, cle: str):
    """Active le tracking des fichiers créés pour ce morceau dans le thread courant."""
    _manifest_ctx.manifeste = manifeste
    _manifest_ctx.cle = cle
    try:
        yield
    finally:
        _manifest_ctx.manifeste = None
        _manifest_ctx.cle = None


def _creer_fichier(path, intermediaire=True):
    """
    Déclare un fichier créé dans le pipeline.

    intermediaire=True  (défaut) : fichier intermédiaire — enregistré dans le
        manifest du morceau courant → supprimé par --nettoyage après le morceau.
        Ex: dalles, TIF ombrages, TIF warpé, VRT, data.bin, tuiles WMTS...

    intermediaire=False : fichier de sortie final — NON enregistré → conservé.
        Ex: .mbtiles, .rmap, .sqlitedb, .geojson(.gz)

    Silencieux si aucun contexte manifeste n'est actif (hors boucle à priori).
    """
    if not intermediaire:
        return  # sortie finale : jamais supprimée par --nettoyage
    m = getattr(_manifest_ctx, "manifeste", None)
    if m is None:
        return
    cle = getattr(_manifest_ctx, "cle", "global")
    m.enregistrer_fichier(path, cle)


def _enregistrer_fichier(path):
    """Alias de compatibilité → _creer_fichier(path, intermediaire=True)."""
    _creer_fichier(path, intermediaire=True)


def _supprimer_fichiers(fichiers: list):
    """
    Supprime tous les fichiers créés par un morceau (--nettoyage).
    Cela inclut : dalles LiDAR, tuiles WMTS, TIF ombrages, TIF warpé.
    Conserve uniquement les sorties finales (.mbtiles, .rmap, .sqlitedb).

    But : permettre le traitement d'une grande BBox sans saturer le disque —
    chaque morceau libère son espace avant que le suivant démarre.

    Seuls les fichiers créés/téléchargés PAR ce morceau (enregistrés dans le
    manifest via _enregistrer_fichier) sont supprimés. Les fichiers déjà
    présents avant le début du morceau ne sont pas touchés.
    """
    suppr = 0
    dirs_a_verifier = set()
    for chemin in fichiers:
        p = Path(chemin)
        # Tous les fichiers du manifest sont intermédiaires (intermediaire=True).
        # Les sorties finales ne sont jamais enregistrées → jamais ici.
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
        print(f"  Nettoyage : {suppr} fichier(s) intermédiaire(s) supprimé(s)")

# ============================================================
# CONFIGURATION
# ============================================================

# ── Chemins ─────────────────────────────────────────────────────────────────
DOSSIER_TRAVAIL = Path(__file__).resolve().parent

# ── LiDAR IGN — géométrie des dalles ─────────────────────────────────────────
RESOLUTION_M       = 0.5          # résolution native des MNT LiDAR HD IGN (m/px)
DALLE_KM           = 1            # côté d'une dalle IGN (km)
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)  # → 2000 px
SEUIL_DALLE_VALIDE = 2_000_000    # octets — en dessous : dalle mer/hors-zone, ignorée

# ── Réseau — tentatives et délais ─────────────────────────────────────────────
MAX_TENTATIVES = 3    # essais avant abandon d'un téléchargement
DELAI_RETRY    = 5    # secondes entre deux tentatives
NB_WORKERS     = 8    # workers parallèles par défaut (téléchargement dalles/tuiles)

# ── URLs IGN ─────────────────────────────────────────────────────────────────
WMS_URL   = "https://data.geopf.fr/wms-r"
WMS_LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"
WFS_URL   = "https://data.geopf.fr/wfs/ows"

# ── Rendu archéologique ───────────────────────────────────────────────────────
ELEVATION_SOLEIL = 25   # degrés — 25° révèle micro-reliefs ; 45° usage général

# Événement d'arrêt propre — positionné par Ctrl+C en mode CLI.
# Vérifié dans les boucles longues (pagination WFS, WMTS, etc.)
# pour interrompre entre deux requêtes sans laisser de thread zombie.
_stop_event = threading.Event()

import signal as _signal
def _on_sigint(sig, frame):
    _stop_event.set()
    print("\n\nInterrompu.")
    sys.exit(0)
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

# ============================================================
# GÉOCODAGE
# ============================================================

def geocoder_ville_wgs84(nom_ville):
    """Géocode une ville et retourne (lat, lon) en WGS84. Retourne (None, None) si échec."""
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(nom_ville + ', France')}"
        "&format=json&limit=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "lidar-mnt-downloader/1.0 (outil SIG personnel)"})
    _log_req(url, "Nominatim")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            OSError, TimeoutError) as e:
        print(f"  ERREUR geocodage ({type(e).__name__}) : {e}")
        return None, None
    if not data:
        print(f"  Ville non trouvée : {nom_ville}")
        return None, None
    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    print(f"  {nom_ville} -> lat={lat:.5f}, lon={lon:.5f}")
    return lat, lon


def geocoder_ville_l93(nom_ville):
    """Géocode une ville et retourne (x, y) en Lambert 93 (pour le pipeline LiDAR). Retourne (None, None) si échec."""
    lat, lon = geocoder_ville_wgs84(nom_ville)
    if lat is None:
        return None, None
    try:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
        x, y = t.transform(lon, lat)
    except ImportError:
        x, y = wgs84_to_lamb93_approx(lon, lat)
        print("  (pyproj absent, conversion approchée)")
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
        print(f"  Département {num_dep} — {c['nom']} (cache local)", flush=True)
        print(f"  BBox WGS84 : {c['lon_min']:.4f},{c['lat_min']:.4f} → "
              f"{c['lon_max']:.4f},{c['lat_max']:.4f}")
        try:
            from pyproj import Transformer
            t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
            bx1, by1 = t.transform(c['lon_min'], c['lat_min'])
            bx2, by2 = t.transform(c['lon_max'], c['lat_max'])
        except ImportError:
            bx1, by1 = wgs84_to_lamb93_approx(c['lon_min'], c['lat_min'])
            bx2, by2 = wgs84_to_lamb93_approx(c['lon_max'], c['lat_max'])
        MARGE = 500
        bx1 -= MARGE; by1 -= MARGE; bx2 += MARGE; by2 += MARGE
        surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
        print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Surface estimée : ~{surface_km2:.0f} km²")
        return c['nom'], bx1, by1, bx2, by2

    # Overpass : relation administrative de niveau département, identifiée par ref:INSEE
    query = (
        f'[out:json];'
        f'relation["boundary"="administrative"]["admin_level"="6"]["ref:INSEE"="{num_dep}"];'
        f'out bb;'
    )
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "lidar-mnt-downloader/1.0 (outil SIG personnel)"})

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
                print(f"  Overpass indisponible ({type(e).__name__}: {e}) — retry {_tentative_ovp+1}/3...",
                      flush=True)
                time.sleep(5)
            else:
                print(f"  ERREUR Overpass : {type(e).__name__}: {e}")

    if lat_min is None:
        print(f"  ERREUR : impossible de géocoder le département {num_dep}.")
        print(f"  Overpass API indisponible. Utilisez --bbox X1,Y1,X2,Y2 (Lambert 93).")
        print(f"  Exemple Var 83 : --bbox 905000,6214000,1040000,6322000")
        return None, None, None, None, None

    # ── Sauvegarde dans le cache ──────────────────────────────────────────────
    _cache[num_dep] = {
        "nom": nom, "lat_min": lat_min, "lat_max": lat_max,
        "lon_min": lon_min, "lon_max": lon_max
    }
    try:
        _cache_path.write_text(json.dumps(_cache, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception:
        pass  # cache non critique

    print(f"  Département {num_dep} — {nom}")
    print(f"  BBox WGS84 : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")

    try:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
        bx1, by1 = t.transform(lon_min, lat_min)
        bx2, by2 = t.transform(lon_max, lat_max)
    except ImportError:
        bx1, by1 = wgs84_to_lamb93_approx(lon_min, lat_min)
        bx2, by2 = wgs84_to_lamb93_approx(lon_max, lat_max)
        print("  (pyproj absent, conversion approchée)")

    # Marge de 500 m pour ne pas couper les dalles en bordure
    MARGE = 500
    bx1 -= MARGE; by1 -= MARGE
    bx2 += MARGE; by2 += MARGE

    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
    print(f"  Surface estimée : ~{surface_km2:.0f} km²")
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
    """Retourne (dalles, bbox) depuis une BBox Lambert 93."""
    step = DALLE_KM * 1000
    x_start = int(x1 // step)
    x_end   = int(x2 // step)
    y_start = int(y1 // step)
    y_end   = int(y2 // step)
    dalles = [
        (x_km, y_km)
        for x_km in range(x_start, x_end + 1)
        for y_km in range(y_start, y_end + 1)
    ]
    return dalles, (x1, y1, x2, y2)


def calculer_grille(cx, cy, rayon_km):
    """Retourne (dalles, bbox) depuis un centre Lambert 93 et un rayon en km."""
    r = rayon_km * 1000
    return calculer_grille_bbox(cx - r, cy - r, cx + r, cy + r)


def nom_dalle(x_km, y_km):
    return f"LHD_FXX_{x_km:04d}_{y_km:04d}_MNT_O_0M50_LAMB93_IGN69.tif"


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
                print(f"  AVERTISSEMENT : dossier inaccessible {sous_dossier.name} ({_e}) — ignoré")
    except OSError as _e:
        print(f"  AVERTISSEMENT : dossier dalles inaccessible ({_e})")
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
    # Extraire XXXX depuis LHD_FXX_XXXX_YYYY_...tif
    m = re.match(r"LHD_FXX_(\d+)_", nom)
    if m:
        sous_dossier = dossier_dalles / m.group(1)
        return sous_dossier / nom
    return chemin_racine  # fallback si nom non reconnu



def construire_url_wms(x_km, y_km):
    # Le WMS IGN 1.3.0 retourne les pixels centrés sur la grille dalles.
    # L'offset ±0.25 m (demi-pixel à 0.5 m/px) compense la convention
    # "coin supérieur gauche" du WMS pour aligner les dalles sans chevauchement.
    # xmin : on recule d'un demi-pixel vers l'ouest (coin gauche de la dalle)
    # ymin : on avance d'un demi-pixel vers le nord (coin bas = nord pour BBOX WMS 1.3)
    xmin = x_km * DALLE_KM * 1000 - 0.25
    xmax = xmin + DALLE_KM * 1000
    ymin = y_km * DALLE_KM * 1000 + 0.25
    ymax = ymin + DALLE_KM * 1000
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": WMS_LAYER, "FORMAT": "image/geotiff", "STYLES": "",
        "CRS": "EPSG:2154",
        "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": PX_PAR_DALLE, "HEIGHT": PX_PAR_DALLE,
        "FILENAME": nom_dalle(x_km, y_km),
    }
    return WMS_URL + "?" + urllib.parse.urlencode(params)


def _lon_lat_to_tile(lon, lat, z):
    """Convertit lon/lat WGS84 en coordonnées tuile TMS (x, y) au zoom z."""
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y


def interroger_tms_dalles(lon_min, lat_min, lon_max, lat_max, bbox_l93=None):
    """
    Interroge le TMS vectoriel IGN (tuiles PBF) pour obtenir la liste des dalles
    MNT LiDAR HD disponibles ET intersectant la bbox L93 demandée.

    Source : https://data.geopf.fr/tms/1.0.0/IGNF_MNT-LIDAR-HD-produit/{z}/{x}/{y}.pbf
    C'est la même source que cartes.gouv.fr/telechargement — plus exhaustive que le WFS.

    bbox_l93 : (x_min, y_min, x_max, y_max) en Lambert 93 — filtre les features
               par intersection avec la zone demandée. Sans ce filtre, toutes les
               dalles de la tuile TMS (~40×40 km) seraient retournées.

    Retourne un dict {nom_dalle: url_wms} ou None si erreur totale.
    """
    # Auto-install mapbox-vector-tile si absent
    try:
        import mapbox_vector_tile as _mvt
    except ImportError:
        print("  Installation mapbox-vector-tile...", flush=True)
        r = subprocess.run([sys.executable, "-m", "pip", "install",
                      "mapbox-vector-tile", "-q"], capture_output=True)
        if r.returncode != 0:
            subprocess.run([sys.executable, "-m", "pip", "install",
                      "mapbox-vector-tile", "-q", "--user"], capture_output=True)
        try:
            import mapbox_vector_tile as _mvt
        except ImportError:
            print("  ERREUR : mapbox-vector-tile non installable — repli WFS")
            return None

    TMS_URL  = "https://data.geopf.fr/tms/1.0.0/IGNF_MNT-LIDAR-HD-produit"
    ZOOM     = 12   # zoom suffisant pour avoir toutes les dalles 1km×1km
    WORKERS  = 16   # requêtes parallèles
    CACHE_PATH = DOSSIER_TRAVAIL / "cache" / "tms_dalles_cache.json"

    # Calcul de la plage de tuiles couvrant la bbox
    tx0, ty0 = _lon_lat_to_tile(lon_min, lat_max, ZOOM)   # NW
    tx1, ty1 = _lon_lat_to_tile(lon_max, lat_min, ZOOM)   # SE
    tuiles = [(tx, ty) for tx in range(tx0, tx1 + 1) for ty in range(ty0, ty1 + 1)]
    nb_tuiles = len(tuiles)
    print(f"  TMS : {nb_tuiles} tuiles à interroger (zoom {ZOOM}, "
          f"x={tx0}..{tx1}, y={ty0}..{ty1})...", flush=True)

    # ── Cache tuiles brutes (sans filtre bbox) ────────────────────────────────
    # Les tuiles TMS ne changent que rarement — on les met en cache JSON.
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    except Exception:
        cache = {}

    tuiles_a_fetcher = [(tx, ty) for tx, ty in tuiles
                        if f"{tx}/{ty}" not in cache]
    if tuiles_a_fetcher:
        print(f"  TMS cache : {nb_tuiles - len(tuiles_a_fetcher)} tuiles en cache, "
              f"{len(tuiles_a_fetcher)} à télécharger...", flush=True)

    def _fetch_tuile(tx, ty):
        url = f"{TMS_URL}/{ZOOM}/{tx}/{ty}.pbf"
        _log_req(url, "TMS")
        req = urllib.request.Request(
            url, headers={"User-Agent": "lidar-mnt-downloader/1.0 (outil SIG personnel)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pbf_data = resp.read()
            tile = _mvt.decode(pbf_data)
            entries = []
            for layer in tile.values():
                for feat in layer.get("features", []):
                    props = feat.get("properties", {})
                    nom   = props.get("name_download") or props.get("name")
                    url_dl = props.get("url")
                    bbox_s = props.get("bbox")
                    if nom and url_dl:
                        if not nom.endswith(".tif"):
                            nom += ".tif"
                        entries.append((nom, url_dl, bbox_s))
            return (tx, ty, entries, None)
        except Exception as _e:
            return (tx, ty, [], str(_e))

    # Fetch parallèle des tuiles manquantes
    nb_erreurs = 0
    done_fetch = 0
    if tuiles_a_fetcher:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {pool.submit(_fetch_tuile, tx, ty): (tx, ty)
                    for tx, ty in tuiles_a_fetcher}
            for fut in as_completed(futs):
                tx, ty, entries, err = fut.result()
                done_fetch += 1
                if err:
                    nb_erreurs += 1
                    cache[f"{tx}/{ty}"] = []
                else:
                    cache[f"{tx}/{ty}"] = entries
                if done_fetch % 20 == 0 or done_fetch == len(tuiles_a_fetcher):
                    pct = done_fetch * 100 // max(len(tuiles_a_fetcher), 1)
                    print(f"\r  TMS : {pct:3d}%  {done_fetch}/{len(tuiles_a_fetcher)} "
                          f"nouvelles tuiles...", end="", flush=True)
        if tuiles_a_fetcher:
            print()
        # Sauvegarder le cache (seulement les entrées sans erreur)
        try:
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False),
                                  encoding="utf-8")
        except Exception:
            pass

    # ── Appliquer filtre bbox L93 sur les résultats ───────────────────────────
    dalles = {}
    for tx, ty in tuiles:
        for entry in cache.get(f"{tx}/{ty}", []):
            nom, url_dl, bbox_s = entry if len(entry) == 3 else (*entry, None)
            if bbox_l93 is not None and bbox_s:
                try:
                    _fx0, _fy0, _fx1, _fy1 = map(float, str(bbox_s).split(","))
                    _zx0, _zy0, _zx1, _zy1 = bbox_l93
                    if _fx1 < _zx0 or _fx0 > _zx1 or _fy1 < _zy0 or _fy0 > _zy1:
                        continue
                except Exception:
                    pass
            dalles[nom] = url_dl

    if nb_erreurs == nb_tuiles:
        print("  ERREUR TMS : toutes les tuiles ont échoué")
        return None
    if nb_erreurs:
        print(f"  TMS : {nb_erreurs}/{nb_tuiles} tuiles en erreur (ignorées)")

    print(f"  TMS : {len(dalles)} dalle(s) disponibles dans la bbox")
    return dalles


def _download_to_tmp(url, chemin_tmp, timeout=60):
    """
    Télécharge url vers chemin_tmp (streaming).
    Retourne le nombre d'octets écrits, ou lève une exception.
    Gère les réponses WMS XML/HTML d'erreur → retourne 0 (dalle absente).
    timeout : tuple (connexion_s, lecture_s) ou entier.
    """
    _log_req(url, "WMS")
    # Timeout lecture : prendre la valeur max si tuple (connect, read).
    _timeout = max(timeout) if isinstance(timeout, tuple) else timeout
    try:
        resp = _urlopen(url, timeout=_timeout)
    except urllib.error.HTTPError as _e:
        if _e.code == 404:
            return 0
        raise IOError(f"HTTP {_e.code}") from _e
    ct = resp.headers.get("content-type", "")
    if "xml" in ct or "html" in ct:
        resp.close(); return 0
    buf_size = 0
    with open(chemin_tmp, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
            buf_size += len(chunk)
    return buf_size


def telecharger_dalle_directe(nom, url_wms, dossier):
    """Télécharge une dalle depuis son URL WMS fournie par le TMS IGN."""
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        return "skip"
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
            chemin_tmp.rename(chemin)
            _enregistrer_fichier(chemin)
            return "ok"
        except KeyboardInterrupt:
            chemin_tmp.unlink(missing_ok=True)
            print("\n\nInterrompu.")
            sys.exit(0)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as _e:
            chemin_tmp.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR {nom} ({type(_e).__name__}, tentative {tentative}) : {_e}")
                return "erreur"
    return "erreur"


def telecharger_dalle(x_km, y_km, dossier, compresser=False):
    nom    = nom_dalle(x_km, y_km)
    chemin = chemin_dalle(dossier, nom)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    if chemin.exists() and chemin.stat().st_size > SEUIL_DALLE_VALIDE:
        return "skip"

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
                gdal_tr = _trouver_gdal_translate()
                if gdal_tr:
                    cmd_c = [gdal_tr, "-of", "GTiff",
                             "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
                             "-co", "TILED=YES", "-co", "BLOCKXSIZE=256", "-co", "BLOCKYSIZE=256",
                             str(chemin_tmp), str(chemin)]
                    _log_req(cmd_c)
                    r = subprocess.run(cmd_c, capture_output=True, env=_env_gdaldem())
                    chemin_tmp.unlink(missing_ok=True)
                    if r.returncode != 0:
                        return "erreur"
                else:
                    chemin_tmp.rename(chemin)
            else:
                chemin_tmp.rename(chemin)

            _enregistrer_fichier(chemin)
            return "ok"

        except KeyboardInterrupt:
            chemin_tmp.unlink(missing_ok=True)
            print("\n\nInterrompu.")
            sys.exit(0)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as _e:
            chemin_tmp.unlink(missing_ok=True)
            if tentative < MAX_TENTATIVES:
                time.sleep(DELAI_RETRY)
            else:
                print(f"\n  ERREUR {nom} ({type(_e).__name__}, tentative {tentative}) : {_e}")
                return "erreur"

    return "erreur"

# ============================================================
# ASSEMBLAGE COG (rasterio)
# ============================================================


def _telecharger_gdal_local():
    """
    Télécharge les binaires GDAL depuis GISInternals dans gdal/bin/.
    Version fixée à GDAL 3.8.5 (PROJ 9.3 → proj.db v4) pour compatibilité
    avec les packages Python courants (pyproj 3.7.x, rasterio 1.3.x).
    """
    import zipfile

    BASE    = "https://download.gisinternals.com/sdk/downloads/"
    # GDAL 3.8.5 = PROJ 9.3.1 = proj.db v4 — compatible pyproj/rasterio courants
    GDAL_ZIP = "release-1930-x64-gdal-3-8-5-mapserver-8-0-1.zip"
    GDAL_DIR = DOSSIER_TRAVAIL / "bin" / "gdal"
    BIN_DIR  = GDAL_DIR / "bin"

    if (BIN_DIR / "gdaldem.exe").exists():
        return str(BIN_DIR / "gdaldem.exe")

    url = BASE + GDAL_ZIP
    print(f"  GDAL : {GDAL_ZIP}")
    print(f"  URL  : {url}")

    GDAL_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = GDAL_DIR / "gdal.zip"

    print("  Téléchargement binaires GDAL (~40 Mo)...", flush=True)
    try:
        def _prog(n, bs, total):
            if total > 0:
                print("  " + str(min(n*bs*100//total, 100)).rjust(3) + "%", end="\r", flush=True)
        urllib.request.urlretrieve(url, zip_path, reporthook=_prog)
        print()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERREUR téléchargement GDAL : {type(e).__name__}: {e}")
        print("  Téléchargez manuellement : https://www.gisinternals.com/release.php")
        return None

    print(f"  Extraction dans {BIN_DIR}...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        noms = z.namelist()
        # Détecter le dossier racine contenant gdaldem.exe
        racine = ""
        for n in noms:
            if n.endswith("gdaldem.exe"):
                racine = n[: n.rfind("/") + 1]
                break
        for membre in noms:
            nom_fichier = membre.split("/")[-1]
            if not nom_fichier:
                continue
            ext = ("." + nom_fichier.rsplit(".", 1)[-1]).lower() if "." in nom_fichier else ""
            # Tous les .dll → BIN_DIR/
            if ext == ".dll":
                dest = BIN_DIR / nom_fichier
                with z.open(membre) as s, open(dest, "wb") as d:
                    d.write(s.read())
                continue
            # .exe + données depuis le dossier racine
            if not membre.startswith(racine):
                continue
            chemin_rel = membre[len(racine):]
            if not chemin_rel:
                continue
            dest = BIN_DIR / chemin_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not membre.endswith("/"):
                with z.open(membre) as s, open(dest, "wb") as d:
                    d.write(s.read())

    zip_path.unlink(missing_ok=True)

    if (BIN_DIR / "gdaldem.exe").exists():
        print(f"  GDAL installé dans {BIN_DIR}")
        return str(BIN_DIR / "gdaldem.exe")
    print("  ERREUR : gdaldem.exe introuvable après extraction.")
    return None


def _telecharger_osmosis_local():
    """
    Télécharge osmosis dans ./osmosis/ depuis GitHub releases.
    osmosis est un JAR Java autonome — nécessite Java installé.
    """
    import zipfile

    OSMOSIS_DIR = DOSSIER_TRAVAIL / "bin" / "osmosis"
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
    print("  Téléchargement osmosis (~35 Mo)...", flush=True)
    try:
        def _prog(n, bs, total):
            if total > 0:
                print("  " + str(min(n*bs*100//total, 100)).rjust(3) + "%",
                      end="\r", flush=True)
        urllib.request.urlretrieve(URL, zip_path, reporthook=_prog)
        print("  100%")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  ERREUR téléchargement osmosis : {type(e).__name__}: {e}")
        return None

    print(f"  Extraction osmosis...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(OSMOSIS_DIR)
    zip_path.unlink(missing_ok=True)

    # Le ZIP extrait dans un sous-dossier versionné (ex: osmosis-0.49.2/)
    # On cherche le binaire par rglob plutôt qu'un chemin fixe
    pattern = "osmosis.bat" if WINDOWS else "osmosis"
    for candidate in sorted(OSMOSIS_DIR.rglob(pattern)):
        if candidate.is_file() and "bin" in candidate.parts:
            if not WINDOWS:
                import stat as _stat
                candidate.chmod(candidate.stat().st_mode | _stat.S_IEXEC)
            print(f"  osmosis installé : {candidate}")
            return str(candidate)
    print("  ERREUR : osmosis introuvable après extraction.")
    return None


def _telecharger_jre_local():
    """
    Télécharge le JRE Temurin (Eclipse Adoptium) dans ./jre/ — portable,
    sans installation système, sans droits admin.
    Fonctionne sur Windows (zip), Linux et macOS (tar.gz), x64 et arm64.
    """
    import tarfile, zipfile

    JRE_DIR = DOSSIER_TRAVAIL / "bin" / "jre"

    # Détection OS
    sys = _pf.system().lower()
    if sys == "windows":
        os_str, ext, java_bin = "windows", "zip",    "bin/java.exe"
    elif sys == "darwin":
        os_str, ext, java_bin = "mac",     "tar.gz", "bin/java"
    else:
        os_str, ext, java_bin = "linux",   "tar.gz", "bin/java"

    # Détection architecture
    machine = _pf.machine().lower()
    arch_str = "aarch64" if machine in ("arm64", "aarch64") else "x64"

    # URL stable Adoptium API — JRE 21 LTS
    URL = (f"https://api.adoptium.net/v3/binary/latest/21/ga"
           f"/{os_str}/{arch_str}/jre/hotspot/normal/eclipse")

    archive = JRE_DIR / f"jre.{ext}"
    JRE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  URL  : {URL}")
    print(f"  Téléchargement JRE Temurin 21 ({os_str}/{arch_str}, ~50 Mo)...",
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
        print(f"  ERREUR téléchargement JRE : {type(e).__name__}: {e}")
        return None

    print("  Extraction JRE...", flush=True)
    if ext == "zip":
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(JRE_DIR)
    else:
        with tarfile.open(archive, "r:gz") as t:
            t.extractall(JRE_DIR)
    archive.unlink(missing_ok=True)

    # Le JRE est extrait dans un sous-dossier au nom variable (ex: jdk-21+35-jre)
    # On cherche le binaire java dans n'importe quel sous-dossier
    for candidate in sorted(JRE_DIR.rglob(java_bin)):
        if candidate.exists():
            if not WINDOWS:
                import stat as _stat
                candidate.chmod(candidate.stat().st_mode | _stat.S_IEXEC)
            print(f"  JRE installé : {candidate}")
            return str(candidate)

    print("  ERREUR : binaire java introuvable après extraction.")
    return None


def _trouver_java():
    """
    Retourne le chemin vers le binaire java local (./jre/).
    Télécharge le JRE Temurin si absent. Jamais le Java système.
    """

    java_bin = "java.exe" if WINDOWS else "java"

    # Chercher le binaire dans l'installation locale
    for candidate in sorted((DOSSIER_TRAVAIL / "bin" / "jre").rglob(java_bin)):
        if candidate.exists():
            return str(candidate)

    # Absent : téléchargement automatique
    java = _telecharger_jre_local()
    if not java:
        print("  ERREUR : impossible d'obtenir un JRE.")
        print("  Installez Java manuellement : https://adoptium.net/")
    return java


def _trouver_osmosis():
    """Retourne le chemin vers osmosis (installation locale ou téléchargement).
    Même logique que GDAL : pas de fallback PATH système.
    Prérequis : appeler _trouver_java() avant (responsabilité de l'appelant)."""
    local_bat = DOSSIER_TRAVAIL / "bin" / "osmosis" / "bin" / "osmosis.bat"
    local_sh  = DOSSIER_TRAVAIL / "bin" / "osmosis" / "bin" / "osmosis"
    if WINDOWS and local_bat.exists():
        return str(local_bat)
    if not WINDOWS and local_sh.exists():
        return str(local_sh)

    # Absent : téléchargement automatique
    return _telecharger_osmosis_local()




def _trouver_outil_gdal(nom):
    """Cherche un executable GDAL uniquement dans l'installation locale du script.
    Ne jamais utiliser QGIS/OSGeo4W/PATH — incompatibilités PROJ garanties.
    Si introuvable : télécharge GDAL sur Windows, installe via apt/brew sur Linux/macOS."""
    exe = nom + (".exe" if WINDOWS else "")
    local = DOSSIER_TRAVAIL / "bin" / "gdal" / "bin" / exe
    if local.exists():
        return str(local)
    # Linux/macOS : PATH système acceptable (GDAL installé via apt/brew)
    if not WINDOWS:
        import shutil as _shutil
        p = _shutil.which(nom)
        if p:
            return p
    # Auto-install
    if WINDOWS:
        _telecharger_gdal_local()
    else:
        _installer_gdal_systeme()
    # Retry après installation
    if local.exists():
        return str(local)
    if not WINDOWS:
        import shutil as _shutil
        p = _shutil.which(nom)
        if p:
            return p
    return None


def _trouver_gdaldem():
    """Cherche gdaldem, installe automatiquement si introuvable."""
    p = _trouver_outil_gdal("gdaldem")
    if p:
        return p
    if WINDOWS:
        print("  gdaldem introuvable — téléchargement automatique GISInternals...")
        return _telecharger_gdal_local()
    ok = _installer_gdal_systeme()
    if ok:
        p = _trouver_outil_gdal("gdaldem")
        if p:
            return p
    cmd = "sudo apt install gdal-bin" if LINUX else "brew install gdal"
    print(f"  ERREUR : installation échouée. Installez manuellement : {cmd}")
    return None


def _env_gdaldem():
    """
    Retourne un env dict pour les outils GDAL.
    - Installation locale gdal/bin : configure PATH + GDAL_DATA + PROJ_LIB
    - OSGeo4W détecté : configure GDAL_DATA + PROJ_LIB depuis OSGeo4W
    - Sinon : retourne None (env hérité)
    """
    import glob as _g
    local_bin = DOSSIER_TRAVAIL / "bin" / "gdal" / "bin"
    if not (local_bin / ("gdaldem.exe" if WINDOWS else "gdaldem")).exists():
        # Pas d'installation locale — chercher OSGeo4W pour fixer GDAL_DATA/PROJ_LIB
        if WINDOWS:
            osgeo_candidates = [
                Path.home() / "AppData" / "Local" / "Programs" / "OSGeo4W",
                Path("C:/OSGeo4W"),
                Path("C:/OSGeo4W64"),
            ]
            qgis_hits = _g.glob("C:/Program Files/QGIS*/apps/gdal")
            for h in qgis_hits:
                osgeo_candidates.append(Path(h).parent.parent)
            for base in osgeo_candidates:
                if not base.exists():
                    continue
                # Chercher proj.db récursivement — emplacement exact
                proj_db_hits = list(base.rglob("proj.db"))
                proj_lib = proj_db_hits[0].parent if proj_db_hits else None
                # GDAL_DATA
                gdal_data = None
                for candidate in [base / "apps" / "gdal" / "share",
                                  base / "apps" / "gdal" / "data",
                                  base / "share" / "gdal"]:
                    if candidate.exists():
                        gdal_data = candidate
                        break
                if proj_lib:
                    env = os.environ.copy()
                    env["PROJ_LIB"] = str(proj_lib)
                    if gdal_data:
                        env["GDAL_DATA"] = str(gdal_data)
                    return env
        return None  # env hérité suffisant

    env = os.environ.copy()
    # Mettre gdal/bin EN PREMIER dans le PATH pour charger les bonnes DLL
    env["PATH"] = str(local_bin) + os.pathsep + env.get("PATH", "")
    env.setdefault("GDAL_NUM_THREADS", "ALL_CPUS")
    env.setdefault("GDAL_CACHEMAX", "512")

    # GDAL_DATA : chercher osmconf.ini dans gdal/bin, gdal/bin/gdal-data, etc.
    for d in [local_bin, local_bin / "gdal-data", local_bin / "data",
              local_bin.parent / "gdal-data", local_bin.parent / "share" / "gdal"]:
        if (d / "osmconf.ini").exists():
            env["GDAL_DATA"] = str(d)
            break
    else:
        for d in [local_bin / "gdal-data", local_bin / "data",
                  local_bin.parent / "gdal-data"]:
            if d.exists():
                env["GDAL_DATA"] = str(d)
                break

    # PROJ_LIB : chercher proj.db compatible avec la DLL proj_X_Y.dll locale
    if WINDOWS and "PROJ_LIB" not in env:
        import glob as _gproj, sqlite3 as _sq
        def _proj_db_ver(p):
            try:
                con = _sq.connect(str(p))
                row = con.execute(
                    "SELECT value FROM metadata WHERE key='DATABASE.LAYOUT.VERSION.MINOR'"
                ).fetchone()
                con.close()
                return int(row[0]) if row else 0
            except Exception:
                return 0

        _proj_dlls = sorted(_gproj.glob(str(local_bin / "proj_*.dll")))
        _target = 4
        for _dll in reversed(_proj_dlls):
            _m = re.search(r"proj_(\d+)_(\d+)\.dll", Path(_dll).name)
            if _m:
                _target = 6 if (int(_m.group(1)), int(_m.group(2))) >= (9, 4) else 4
                break

        _best_db, _best_ver = None, 0
        for _pkg in ("rasterio", "pyproj"):
            try:
                _mod = __import__(_pkg)
                _dbs = []
                if _pkg == "rasterio":
                    for _sub in ["proj_data", "proj_dir/share/proj"]:
                        _db = Path(_mod.__file__).parent / _sub / "proj.db"
                        if _db.exists(): _dbs.append(_db); break
                else:
                    _db = Path(_mod.datadir.get_data_dir()) / "proj.db"
                    if _db.exists(): _dbs.append(_db)
                for _db in _dbs:
                    _ver = _proj_db_ver(_db)
                    if _ver == _target:
                        _best_db, _best_ver = _db, _ver; break
                    elif _ver > _best_ver:
                        _best_db, _best_ver = _db, _ver
            except Exception:
                pass
            if _best_ver == _target:
                break

        if _best_db:
            env["PROJ_LIB"]  = str(_best_db.parent)
            env["PROJ_DATA"] = str(_best_db.parent)

    return env


def _run_gdal_avec_jauge(cmd, nom_fichier, env, largeur=30):
    """Lance un subprocess gdal et affiche la progression 0...10...20... en jauge.
    Sur Windows, gdaldem envoie la progression sur stdout ; sur Linux sur stderr.
    On lit les deux en parallèle via threads pour couvrir les deux cas.
    Affiche le pourcentage, le temps écoulé et l'ETA estimée.
    """
    _log_req(cmd)
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=0, env=env)

    pct_max = 0; erreur_lines = []; t0 = time.time()
    label = ("  " + nom_fichier).ljust(56)
    _pct_re = re.compile(r"(?<![\d])([1-9]?\d|100)(?=\.\.\.|\.\s|\s|$)")
    q = queue.Queue()

    def _lire_flux(flux, nom):
        for ch in iter(lambda: flux.read(1), ""):
            q.put((nom, ch))
        q.put((nom, None))  # signal fin

    t_out = threading.Thread(target=_lire_flux, args=(proc.stdout, "out"), daemon=True)
    t_err = threading.Thread(target=_lire_flux, args=(proc.stderr, "err"), daemon=True)
    t_out.start(); t_err.start()

    finis = set(); buf_pct = ""; buf_line = ""
    while len(finis) < 2:
        nom, ch = q.get()
        if ch is None:
            finis.add(nom)
            continue
        # Accumulation ligne complète pour capture d'erreurs
        if ch in ("\n", "\r"):
            line = buf_line.strip()
            if line and ("ERROR" in line.upper() or "FAILED" in line.upper()
                         or "UNABLE" in line.upper()):
                erreur_lines.append(line)
            buf_line = ""
        else:
            buf_line += ch
        # Accumulation mot par mot pour la jauge de progression
        if ch in (".", " ", "\n", "\r"):
            m = _pct_re.search(buf_pct)
            if m:
                v = int(m.group(1))
                if 0 <= v <= 100 and v > pct_max:
                    pct_max = v
                    bars  = int(v / 100 * largeur)
                    barre = "\u2588" * bars + "\u2591" * (largeur - bars)
                    elapsed = int(time.time() - t0)
                    if v > 0:
                        eta_s = int(elapsed * (100 - v) / v)
                        eta_str = (f"  ETA {eta_s//3600}h{(eta_s%3600)//60:02d}m"
                                   if eta_s >= 3600
                                   else f"  ETA {eta_s//60}m{eta_s%60:02d}s")
                    else:
                        eta_str = ""
                    print("\r" + label + " [" + barre + "] " +
                          str(v).rjust(3) + "%" + _hms(elapsed).rjust(8) + eta_str,
                          end="", flush=True)
            buf_pct = ""
        else:
            buf_pct += ch

    # Dernière ligne sans \n
    if buf_line.strip():
        line = buf_line.strip()
        if "ERROR" in line.upper() or "FAILED" in line.upper():
            erreur_lines.append(line)

    proc.wait()
    return proc.returncode, int(time.time()-t0), erreur_lines


def _installer_gdal_systeme():
    """Installe gdal-bin via apt (Linux) ou brew (macOS)."""
    if LINUX:
        print("  Installation gdal-bin via apt...")
        r = subprocess.run(["sudo", "apt", "install", "-y", "gdal-bin"])
        return r.returncode == 0
    if MACOS:
        print("  Installation gdal via brew...")
        r = subprocess.run(["brew", "install", "gdal"])
        return r.returncode == 0
    return False


def _trouver_gdal(nom):
    """Cherche un outil GDAL par nom, installe GDAL si introuvable."""
    p = _trouver_outil_gdal(nom)
    if p:
        return p
    if WINDOWS:
        _telecharger_gdal_local()
    else:
        _installer_gdal_systeme()
    return _trouver_outil_gdal(nom)



def _trouver_gdal_translate():
    return _trouver_gdal("gdal_translate")


def _geoinfo_depuis_gdalinfo(src_tif, env):
    """
    Retourne (geotransform_str, srs_wkt) lus depuis gdalinfo -json.
    geotransform_str : 6 valeurs séparées par virgules (xmin, xres, 0, ymax, 0, -yres)
    """
    gdalinfo = _trouver_outil_gdal("gdalinfo")
    if not gdalinfo:
        return None, None
    r = subprocess.run([gdalinfo, "-json", str(src_tif)],
                       capture_output=True, text=True, env=env)
    try:
        info = json.loads(r.stdout)
        gt   = info.get("geoTransform")       # [xmin, xres, 0, ymax, 0, -yres]
        srs  = (info.get("coordinateSystem") or {}).get("wkt", "")
        if gt and len(gt) == 6:
            return ",".join(str(v) for v in gt), srs
    except Exception:
        pass
    return None, None


def _sauver_array_georef(arr, src_tif, dst_tif, gdal_translate_exe, env):
    """
    Sauvegarde un numpy array uint8 (2D niveaux de gris ou 3D RGB) en GeoTIFF
    en copiant le géoréférencement de src_tif.

    Approche primaire : rasterio (déjà requis pour le tuilage MBTiles).
    Fallback : VRT binaire + gdal_translate si rasterio absent.

    arr   : numpy uint8 shape (H,W) pour L, (H,W,3) pour RGB
    """
    import numpy as np

    h = arr.shape[0]
    w = arr.shape[1]
    n_bands = 1 if arr.ndim == 2 else arr.shape[2]

    # ── Approche primaire : rasterio ─────────────────────────────────────────
    try:
        import rasterio
        from rasterio.transform import Affine

        with rasterio.open(str(src_tif)) as src:
            profile = src.profile.copy()

        profile.update(
            dtype    = "uint8",
            count    = n_bands,
            compress = "deflate",
            predictor= 2,
            tiled    = True,
            blockxsize = 512,
            blockysize = 512,
            bigtiff  = "IF_SAFER",
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
        return

    except ImportError:
        pass  # rasterio absent → fallback ci-dessous
    except Exception as e_rio:
        print(f"  AVERTISSEMENT rasterio write : {e_rio} — repli VRT")

    # ── Fallback : VRT binaire + gdal_translate ───────────────────────────────
    import shutil as _shutil_arr

    gt_str, srs_wkt = _geoinfo_depuis_gdalinfo(src_tif, env)
    if gt_str is None:
        from PIL import Image as _Img
        _Img.fromarray(arr).save(str(dst_tif), format="TIFF")
        print("  AVERTISSEMENT : src georef introuvable, TIF sans projection")
        return

    _arr_tmpdir = dst_tif.parent / "_tmp"
    _arr_tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        raw_path = _arr_tmpdir / "data.bin"
        vrt_path = _arr_tmpdir / "data.vrt"

        raw_path.write_bytes(arr.astype(np.uint8).tobytes())
        _creer_fichier(raw_path)
        pixel_offset = n_bands
        line_offset  = w * n_bands

        srs_elem = (f"<SRS>{srs_wkt}</SRS>" if srs_wkt else "<SRS>EPSG:2154</SRS>")
        gt_elem  = f"<GeoTransform>{gt_str}</GeoTransform>"

        color_interp = ["Red", "Green", "Blue"]
        bands_xml = ""
        for b in range(n_bands):
            ci = (f"<ColorInterp>{color_interp[b]}</ColorInterp>"
                  if n_bands == 3 else "<ColorInterp>Gray</ColorInterp>")
            bands_xml += f"""
  <VRTRasterBand dataType="Byte" band="{b+1}" subClass="VRTRawRasterBand">
    {ci}
    <SourceFilename relativeToVRT="1">data.bin</SourceFilename>
    <ImageOffset>{b}</ImageOffset>
    <PixelOffset>{pixel_offset}</PixelOffset>
    <LineOffset>{line_offset}</LineOffset>
    <ByteOrder>LSB</ByteOrder>
  </VRTRasterBand>"""

        vrt_xml = f"""<VRTDataset rasterXSize="{w}" rasterYSize="{h}">
  {srs_elem}
  {gt_elem}{bands_xml}
</VRTDataset>"""
        vrt_path.write_text(vrt_xml, encoding="utf-8")
        _creer_fichier(vrt_path)

        cmd = [
            gdal_translate_exe, "-of", "GTiff",
            "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
            "-co", "TILED=YES", "-co", "BLOCKXSIZE=512", "-co", "BLOCKYSIZE=512",
            "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
            str(vrt_path), str(dst_tif)
        ]
        _log_req(cmd)
        _t0_tr = time.time()
        r = subprocess.run(cmd, capture_output=True, env=env)
        if r.returncode != 0:
            err = r.stderr.decode("utf-8", errors="replace").strip()[:200]
            print(f"  AVERTISSEMENT : gdal_translate VRT→TIF échoué : {err}")
            from PIL import Image as _Img
            _Img.fromarray(arr).save(str(dst_tif), format="TIFF")
        else:
            print(f"  gdal_translate OK  ({_hms(time.time()-_t0_tr)})", flush=True)
    finally:
        _shutil_arr.rmtree(_arr_tmpdir, ignore_errors=True)


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
        print(f"  AVERTISSEMENT rasterio read ({e_rio}) — repli PIL", flush=True)

    from PIL import Image as _Img
    return np.array(_Img.open(str(src_path)), dtype=np.float32), None


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
          passe 1 (échantillon)  → p5 / p95 globaux sur ~5 % des pixels
          passe 2 (traitement)   → applique la normalisation bloc par bloc

    Retourne True si succès, False si fallback requis (ex: rasterio absent).
    """
    import numpy as np
    try:
        import rasterio as _rio
        from rasterio.windows import Window
        from scipy.ndimage import gaussian_filter as _gf
    except ImportError as _ie:
        print(f"  LRM chunked : import manquant ({_ie}) — repli pleine mémoire", flush=True)
        return False

    CHUNK  = 2048
    MARGIN = max(4 * sigma_px, 64)   # au moins 64 px pour les petits sigma

    with _rio.open(str(src_path)) as src:
        H, W   = src.height, src.width
        profile = src.profile.copy()
        nodata  = src.nodata

    # ── Passe 1 : estimation percentiles p5/p95 sur échantillon (~1 chunk) ──
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

    # ── Profil de sortie ────────────────────────────────────────────────────
    out_profile = profile.copy()
    out_profile.update(
        dtype      = "uint8",
        count      = 1,
        compress   = "deflate",
        predictor  = 2,
        tiled      = True,
        blockxsize = 512,
        blockysize = 512,
        bigtiff    = "IF_SAFER",
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

    print(f"\r  LRM chunked : terminé ({total_chunks} blocs, σ={sigma_px} px)          ")
    return True


def _svf_numpy(dem, max_dist_px, n_directions=16, resolution=0.5):
    """
    Sky-View Factor — pixel-level ray casting.

    SVF(p) = (1/N) × Σ_k  1 / (1 + max(tan_horizon_k, 0)²)

    Moteurs disponibles par ordre de préférence :
      1. Numba njit + prange  → ×15-50 vs numpy pur, compilation ~20s au 1er appel
      2. numpy vectorisé      → fallback si numba absent

    SVF faible (sombre) = creux (fossé, fond de vallée)
    SVF élevé (clair)   = ouvert (sommet, plateau)
    """
    import numpy as np

    h, w = dem.shape
    nodata_mask = (dem < -9000) | (dem > 9000)
    dem_f = dem.astype(np.float32)
    if nodata_mask.any():
        mean_val = float(np.nanmean(dem_f[~nodata_mask]))
        dem_f[nodata_mask] = mean_val

    # ── Tentative Numba ──────────────────────────────────────────────────────
    _numba_ok = False
    try:
        import numba as _nb

        @_nb.njit(parallel=True, cache=True, fastmath=True)
        def _svf_kernel(dem, h, w, n_dir, max_r, res):
            """
            Kernel Numba : pour chaque pixel, scan N rayons → SVF.
            prange parallélise automatiquement sur tous les cœurs.
            Interpolation bilinéaire sub-pixel sur la position exacte du rayon.
            """
            PI2 = 2.0 * math.pi
            out = np.zeros((h, w), dtype=np.float32)

            for row in _nb.prange(h):                   # parallèle
                for col in range(w):
                    z0 = dem[row, col]
                    svf_sum = 0.0

                    for k in range(n_dir):
                        angle  = k * PI2 / n_dir
                        dx     =  math.sin(angle)       # décalage colonne/px
                        dy     = -math.cos(angle)       # décalage ligne/px
                        max_tan = -1e38

                        for r in range(1, max_r + 1):
                            # Position réelle du voisin
                            rr = row + dy * r
                            cc = col + dx * r

                            # Interpolation bilinéaire
                            r0 = int(math.floor(rr))
                            c0 = int(math.floor(cc))
                            r1 = r0 + 1
                            c1 = c0 + 1

                            # Clamp aux bords
                            r0 = max(0, min(h - 1, r0))
                            r1 = max(0, min(h - 1, r1))
                            c0 = max(0, min(w - 1, c0))
                            c1 = max(0, min(w - 1, c1))

                            fr = rr - math.floor(rr)
                            fc = cc - math.floor(cc)

                            z_neighbor = (
                                dem[r0, c0] * (1 - fr) * (1 - fc) +
                                dem[r0, c1] * (1 - fr) *      fc  +
                                dem[r1, c0] *      fr  * (1 - fc) +
                                dem[r1, c1] *      fr  *      fc
                            )

                            dist_m = r * res
                            tan_a  = (z_neighbor - z0) / dist_m
                            if tan_a > max_tan:
                                max_tan = tan_a

                        # cos²(arctan(max_tan)) = 1/(1+max_tan²) si max_tan>0
                        mt = max_tan if max_tan > 0.0 else 0.0
                        svf_sum += 1.0 / (1.0 + mt * mt)

                    out[row, col] = svf_sum / n_dir

            return out

        print("  SVF Numba JIT — compilation au 1er appel (~20s)...", flush=True)
        svf = _svf_kernel(dem_f, h, w, n_directions, max_dist_px, resolution)
        _numba_ok = True
        print(f"\r  SVF Numba JIT — terminé{' ' * 30}")

    except ImportError:
        print("  numba absent — fallback numpy vectorisé", flush=True)
    except Exception as e_nb:
        print(f"  numba erreur ({e_nb}) — fallback numpy", flush=True)

    # ── Fallback numpy ───────────────────────────────────────────────────────
    if not _numba_ok:
        try:
            from scipy.ndimage import shift as _shift
            _use_scipy = True
        except ImportError:
            _use_scipy = False

        def _process_direction(k):
            angle   = k * 2.0 * np.pi / n_directions
            dx      =  np.sin(angle)
            dy      = -np.cos(angle)
            max_tan = np.full((h, w), -np.inf, dtype=np.float32)

            for r in range(1, max_dist_px + 1):
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
            for fut in as_completed(futures):
                svf_sum += fut.result()
                done += 1
                pct_svf = done * 100 // max(n_directions, 1)
                print(f"\r  SVF directions : {pct_svf:3d}%  {done}/{n_directions}",
                      end="", flush=True)
        print()
        svf = svf_sum / n_directions

    svf[nodata_mask] = 0.0
    return svf


def generer_ombrages(cogs, dossier_ville, choix=None, elevation_soleil=None, nom_zone=None, ecraser_ombrages=False, ecraser_tuiles=False):
    """
    Génère les ombrages depuis le VRT/COG source (MNT EPSG:2154).

    Types gdaldem  : 315, 045, 135, 225, multi, slope
    Types numpy/scipy (sans WhiteboxTools) :
        svf    — Sky-View Factor 20 m  : fossés, murs, structures ≤ 5 m (16 dir, rayon 20 m)
        svf100 — Sky-View Factor 100 m : enceintes, voiries, grandes anomalies (16 dir, rayon 100 m)
        rrim   — Red Relief Image Map  : composite RGB couleur (R=pente, G=B=SVF)
        lrm    — Local Relief Model    : LRM = DEM − gaussienne(σ 7.5 m) — scipy requis

    elevation_soleil : angle solaire en degrés (défaut: 25° archéo, vs 45° usage général).
    SVF/SVF100/LRM/RRIM : implémentés en numpy/scipy — aucun outil externe requis.
    """

    if elevation_soleil is None:
        elevation_soleil = ELEVATION_SOLEIL

    if choix is None:
        choix = ["315", "045", "135", "225", "multi", "slope"]

    if isinstance(cogs, Path):
        cogs = [cogs]

    gdaldem       = _trouver_gdaldem()
    gdalbuildvrt  = _trouver_gdal("gdalbuildvrt")
    gdal_translate = _trouver_gdal_translate()
    env_dem       = _env_gdaldem()

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
        # moteur=None → traitement numpy interne (pas de WBT)
        "svf":    ("svf_ombrage",      None,
                   {"max_dist_px": 40,  "n_directions": 16}),   # 40 px = 20 m à 0.5 m/px
        "svf100": ("svf_100m_ombrage", None,
                   {"max_dist_px": 200, "n_directions": 16}),   # 200 px = 100 m
        "lrm":    ("lrm_ombrage",      None,
                   {"sigma_px": 15}),                            # σ=15 px = 7.5 m — compromise structures 4-15 m
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

    if not gdaldem and choix_gdal:
        print("  ERREUR : gdaldem introuvable.")
        choix_gdal = []

    # ── Construction VRT global (seamless, évite jointures gdaldem) ─────────
    # VRT dans _tmp/ sous dossier_ville : tous les fichiers restent dans le projet.
    import shutil as _shutil_vrt
    _vrt_tmpdir = None
    if len(cogs) > 1 and gdalbuildvrt:
        _vrt_tmpdir = dossier_ville / "_tmp"
        _vrt_tmpdir.mkdir(parents=True, exist_ok=True)
        vrt_path      = _vrt_tmpdir / "_mnt_complet.vrt"
        filelist_path = _vrt_tmpdir / "_dalles.txt"
        # Écriture de la liste dans un fichier texte — évite WinError 206
        # (limite Windows de ~32 767 caractères sur la ligne de commande)
        filelist_path.write_text(
            "\n".join(str(c) for c in cogs), encoding="utf-8")
        _creer_fichier(vrt_path)
        _creer_fichier(filelist_path)
        print(f"  Construction VRT global ({len(cogs)} dalles)...", flush=True)
        _cmd_vrt = [gdalbuildvrt,
                    "-tr", str(RESOLUTION_M), str(RESOLUTION_M), "-tap",
                    "-input_file_list", str(filelist_path), str(vrt_path)]
        _log_req(_cmd_vrt)
        _t0_vrt = time.time()
        r = subprocess.run(_cmd_vrt, capture_output=True, text=True, env=env_dem)
        if r.returncode != 0:
            print("  ERREUR VRT : " + r.stderr.strip()[:200])
            print("  Repli sur dalles individuelles.")
            sources = cogs
        else:
            print(f"  VRT OK  ({_hms(time.time()-_t0_vrt)})", flush=True)
            sources = [vrt_path]
    else:
        if len(cogs) > 1:
            print("  gdalbuildvrt introuvable, traitement dalle par dalle (jointures possibles)")
        sources = cogs

    source   = sources[0]
    nom_base = normaliser_nom(nom_zone) if nom_zone else normaliser_nom(dossier_ville.name)

    try:
        # ── Ombrages gdaldem — appel direct sur le VRT global ───────────────
        # Pas de banding — gdaldem traite en streaming par blocs.
        # La RAM n'est jamais saturée quelle que soit la taille du raster.

        def _generer_un_hillshade(cle):
            suffix, args_dem = CATALOGUE_GDAL[cle]
            nom_fichier = nom_base + "_" + suffix + ".tif"
            chemin_out  = dossier_ville / nom_fichier

            if chemin_out.exists():
                return cle, nom_fichier, "skip", 0, []

            cmd = [gdaldem] + args_dem + [str(source), str(chemin_out)] + co
            code, _, errs = _run_gdal_avec_jauge(cmd, nom_fichier, env_dem)
            if code == 0:
                _enregistrer_fichier(chemin_out)
                return cle, nom_fichier, "ok", chemin_out.stat().st_size / 1e6, []
            return cle, nom_fichier, "erreur", 0, errs

        if choix_gdal:
            if len(choix_gdal) == 1:
                # Un seul type : appel direct avec barre de progression
                cle, nom_fichier, statut, taille, errs = \
                    _generer_un_hillshade(choix_gdal[0])
                if statut == "skip":
                    print("  " + nom_fichier.ljust(56) + " -> déjà présent")
                elif statut == "erreur":
                    print(f"\n  ERREUR gdaldem {nom_fichier}")
                    for e in errs[:10]:
                        print(f"    {e}")
            else:
                # Plusieurs types : parallèle (un process par type)
                print(f"  Hillshades gdaldem ({len(choix_gdal)} types)...",
                      flush=True)
                with ThreadPoolExecutor(max_workers=len(choix_gdal)) as pool:
                    futures = {pool.submit(_generer_un_hillshade, cle): cle
                               for cle in choix_gdal}
                    for fut in as_completed(futures):
                        cle, nom_fichier, statut, taille, errs = fut.result()
                        if statut == "skip":
                            print("  " + nom_fichier.ljust(56) + " -> déjà présent")
                        elif statut == "erreur":
                            print(f"\n  ERREUR gdaldem {nom_fichier}")
                            for e in errs[:10]:
                                print(f"    {e}")

        # ── SVF, LRM, RRIM — numpy/scipy (pas de WBT pour SVF) ──────────────
        if not choix_numpy:
            pass  # pas de traitement demandé

        # Pour lire le VRT avec PIL/numpy, on le convertit d'abord en GeoTIFF.
        # (PIL ne sait pas lire les VRT directement)
        src_str = str(source)
        tmp_gtiff = None
        if source.suffix.lower() == ".vrt" and choix_numpy:
            if gdal_translate:
                _tmp_base = _vrt_tmpdir if _vrt_tmpdir else dossier_ville / "_tmp"
                _tmp_base.mkdir(parents=True, exist_ok=True)
                tmp_gtiff = _tmp_base / "_numpy_source_tmp.tif"
                if not tmp_gtiff.exists():
                    print("  Conversion VRT → GeoTIFF pour lecture numpy...", flush=True)
                    cmd_conv = [
                        gdal_translate, "-of", "GTiff",
                        "-co", "COMPRESS=DEFLATE", "-co", "TILED=YES",
                        "-co", "BLOCKXSIZE=512", "-co", "BLOCKYSIZE=512",
                        "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
                        str(source), str(tmp_gtiff)
                    ]
                    code_c, _, _ = _run_gdal_avec_jauge(cmd_conv, "_numpy_source_tmp.tif", env_dem)
                    if code_c != 0:
                        print("  ERREUR conversion VRT → GTiff — SVF/LRM/RRIM ignorés")
                        choix_numpy = []
                    elif tmp_gtiff.exists():
                        _creer_fichier(tmp_gtiff)
                src_str = str(tmp_gtiff)
            else:
                print("  gdal_translate introuvable — SVF/LRM/RRIM ignorés")
                choix_numpy = []

        for cle in choix_numpy:
            sous_dossier_name, outil_numpy, params_numpy = CATALOGUE_NUMPY[cle]
            nom_fichier  = nom_base + "_" + sous_dossier_name + ".tif"
            chemin_out   = dossier_ville / nom_fichier

            if chemin_out.exists():
                print("  " + nom_fichier.ljust(56) + " -> déjà présent")
                continue

            t0_numpy = time.time()

            if cle in ("svf", "svf100"):
                # ── Sky-View Factor numpy (sans WhiteboxTools) ───────────────
                max_dist_px  = params_numpy["max_dist_px"]
                n_directions = params_numpy["n_directions"]
                dist_m = max_dist_px * RESOLUTION_M
                print(f"  SVF numpy ({n_directions} dir, rayon {dist_m:.0f} m"
                      f" = {max_dist_px} px)...", flush=True)
                try:
                    import numpy as np
                    dem_arr, _nd = _lire_dem_rasterio(src_str)
                    arr_svf = _svf_numpy(dem_arr, max_dist_px, n_directions,
                                         RESOLUTION_M)
                    # Normalisation percentile p2–p98 + gamma > 1 pour assombrir
                    # les hautes valeurs (SVF ≈ 1.0 sur terrain ouvert Var)
                    svf_valid = arr_svf[arr_svf >= 0]
                    p2  = float(np.percentile(svf_valid, 2))
                    p98 = float(np.percentile(svf_valid, 98))
                    if p98 > p2:
                        arr_stretched = np.clip((arr_svf - p2) / (p98 - p2), 0, 1)
                    else:
                        arr_stretched = np.clip(arr_svf, 0, 1)
                    # gamma 2.0 : assombrit les mi-tons, accentue les creux (SVF faible)
                    arr_u8 = (arr_stretched ** 2.0 * 255).astype(np.uint8)
                    if gdal_translate:
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_out,
                                             gdal_translate, env_dem)
                    else:
                        from PIL import Image as _Img
                        _Img.fromarray(arr_u8).save(str(chemin_out), format="TIFF")
                except Exception as e_svf:
                    print(f"  ERREUR SVF numpy : {e_svf}")
                    continue

            elif cle == "lrm":
                # ── Local Relief Model — filtre gaussien ─────────────────────
                # LRM = DEM − gaussienne(σ) → normalisation p5-p95 → uint8 (128=plat)
                # Traitement par blocs avec overlap pour borner la RAM :
                #   chemin 1 : _lrm_chunked() si rasterio + scipy disponibles
                #   chemin 2 : pleine mémoire (fallback)
                sigma_px = params_numpy["sigma_px"]  # 50 px = 25 m à 0.5 m/px
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
                            clip_info = f"±{clip_val:.2f}m (σ fallback)"
                        arr_u8 = arr_f.astype(np.uint8)
                        arr_u8[nodata_mask] = 128
                        if gdal_translate:
                            _sauver_array_georef(arr_u8, Path(src_str), chemin_out,
                                                 gdal_translate, env_dem)
                        else:
                            from PIL import Image as _Img
                            _Img.fromarray(arr_u8).save(str(chemin_out), format="TIFF")
                        _lrm_ok = True
                        print(f"  LRM scipy (pleine mémoire) : σ={sigma_px} px, {clip_info}")
                    except ImportError:
                        print("  scipy absent — LRM ignoré (pip install scipy)", flush=True)
                        continue
                    except Exception as e_scipy:
                        print(f"  ERREUR scipy LRM : {e_scipy}")
                        continue

            elif cle == "rrim":
                # ── Red Relief Image Map (RRIM) ───────────────────────────────
                # Composite RGB couleur :
                #   R = pente normalisée [0°..45°] → [0..255]  (relief en amplitude)
                #   G = B = SVF normalisé [0..1] → [0..255]    (ouverture / micro-formes)
                # Révèle simultanément creux ET bosses — optimal prospection terrain.
                # Technique : Chiba et al. (2008), standard archéo-LiDAR européen.
                print("  RRIM — Red Relief Image Map (slope × LRM)"
                      " — peut prendre 5-10 min...", flush=True)

                # Slope temporaire (réutilisé si déjà présent)
                slope_rrim_path = dossier_ville / (nom_base + "_slope_ombrage.tif")
                slope_tmp_path  = dossier_ville / (nom_fichier.replace(".tif","_slope_tmp.tif"))
                _slope_src = None
                if slope_rrim_path.exists():
                    _slope_src = slope_rrim_path
                    print("  RRIM : slope existant réutilisé", flush=True)
                else:
                    cmd_slope = [
                        gdaldem, "slope", "-b","1","-s","1.0",
                        str(source), str(slope_tmp_path),
                        "-of", "GTiff",
                        "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
                    ]
                    code_sl, _, _ = _run_gdal_avec_jauge(
                        cmd_slope, "slope_tmp.tif", env_dem)
                    if code_sl != 0 or not slope_tmp_path.exists():
                        print("  ERREUR gdaldem slope pour RRIM")
                        continue
                    _slope_src = slope_tmp_path

                # Étape 3 : composite RGB numpy/PIL
                # RRIM modifié pour terrain ouvert (Var) :
                #   R = pente gamma 0.7 (relief général)
                #   G = B = LRM normalisé (micro-relief local, variance >> SVF)
                # Le LRM a beaucoup plus de variance que SVF sur terrain ouvert
                # où SVF ≈ 0.97 partout → G/B ≈ 255 constant → dominance bleue.
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

                    # G = B = LRM normalisé p5-p95, gamma 0.8
                    # LRM > 0 = élévation → clair ; LRM < 0 = creux → foncé
                    lrm_n  = _norm_pct(lrm_r)
                    gb_chan = (lrm_n ** 0.8 * 255).astype(np.uint8)

                    rgb = np.stack([r_chan, gb_chan, gb_chan], axis=2)
                    if gdal_translate:
                        _sauver_array_georef(rgb, Path(src_str), chemin_out,
                                             gdal_translate, env_dem)
                    else:
                        from PIL import Image as _ImgRRIM
                        _ImgRRIM.fromarray(rgb).save(str(chemin_out), format="TIFF")
                    print(f"  RRIM : {chemin_out.name} — RGB 3 canaux")
                except Exception as e_rrim:
                    print(f"  ERREUR composite RRIM : {e_rrim}")
                    continue
                finally:
                    if slope_tmp_path.exists():
                        slope_tmp_path.unlink(missing_ok=True)

            if chemin_out.exists():
                _enregistrer_fichier(chemin_out)
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

    print("\n  Ombrages dans : " + str(dossier_ville))




def _bbox_depuis_gdalinfo(chemin, env):
    """Retourne (xmin, ymin, xmax, ymax) en unités natives du fichier."""
    gdalinfo = _trouver_outil_gdal("gdalinfo")
    if not gdalinfo:
        return None
    r = subprocess.run([gdalinfo, "-json", str(chemin)],
                       capture_output=True, text=True, env=env)
    try:
        info = json.loads(r.stdout)
        cc   = info["cornerCoordinates"]
        return (cc["lowerLeft"][0], cc["lowerLeft"][1],
                cc["upperRight"][0], cc["upperRight"][1])
    except Exception:
        m1 = re.search(r"Lower Left\s+\(([\d.+-]+),\s*([\d.+-]+)\)", r.stdout)
        m2 = re.search(r"Upper Right\s+\(([\d.+-]+),\s*([\d.+-]+)\)", r.stdout)
        if m1 and m2:
            return (float(m1.group(1)), float(m1.group(2)),
                    float(m2.group(1)), float(m2.group(2)))
    return None


def generer_mbtiles_lidar(tif_source, dossier_ville, nom_ville,
                    zoom_min=13, zoom_max=17, format_tuiles="auto",
                    jpeg_quality=85, bbox_l93=None,
                    source_already_warped=False, ecraser_tuiles=False):
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
        print("  ERREUR : rasterio absent — requis pour le tuilage MBTiles.")
        print("  Installez-le : pip install rasterio")
        return None

    Image.MAX_IMAGE_PIXELS = None

    # Déterminer le format de tuile effectif
    _nom_lower = tif_source.stem.lower()
    _types_png = ("svf", "lrm", "rrim")   # gradients fins → PNG sans perte
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
        print(f"  {mbtiles.name} → déjà présent")
        return mbtiles
    if mbtiles.exists() and ecraser_tuiles:
        mbtiles.unlink()
        print(f"  {mbtiles.name} → écrasement")

    env      = _env_gdaldem()
    gdalwarp = _trouver_gdal("gdalwarp")
    gdal_tr  = _trouver_gdal_translate()
    if not gdalwarp or not gdal_tr:
        print("  ERREUR : gdalwarp ou gdal_translate introuvable")
        return None
    print(f"  gdalwarp : {gdalwarp}", flush=True)

    gdal_addo = _trouver_outil_gdal("gdaladdo")

    # PROJ_LIB : fournir un proj.db compatible avec le GDAL utilisé.
    # Sur Linux, GDAL apt et proj.db système sont toujours cohérents — on ne touche pas.
    # Sur Windows, le GDAL local (GISInternals) n'inclut pas proj.db → on le fournit.
    if env is None:
        env = os.environ.copy()

    import sqlite3 as _sq
    def _proj_db_version(db_path):
        try:
            con = _sq.connect(str(db_path))
            row = con.execute(
                "SELECT value FROM metadata "
                "WHERE key='DATABASE.LAYOUT.VERSION.MINOR'"
            ).fetchone()
            con.close()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    if WINDOWS:
        # Détecter la version proj.db requise par le GDAL local
        # via la DLL proj_X_Y.dll la plus récente dans gdal/bin/
        import glob as _gproj
        _proj_dlls = sorted(_gproj.glob(
            str(DOSSIER_TRAVAIL / "bin" / "gdal" / "bin" / "proj_*.dll")))
        _PROJ_TARGET_VER = 4  # défaut GDAL 3.8.5 / PROJ 9.3
        if _proj_dlls:
            # proj_9_3.dll → PROJ 9.3 → proj.db v4
            # proj_9_4.dll → PROJ 9.4 → proj.db v6
            for _dll in reversed(_proj_dlls):
                _m = re.search(r"proj_(\d+)_(\d+)\.dll",
                                     Path(_dll).name)
                if _m:
                    _major, _minor = int(_m.group(1)), int(_m.group(2))
                    # PROJ 9.4+ → proj.db v6 ; PROJ < 9.4 → proj.db v4
                    _PROJ_TARGET_VER = 6 if (_major, _minor) >= (9, 4) else 4
                    break

        # Chercher le proj.db correspondant dans rasterio/pyproj
        _candidates_proj = []
        for _pkg in ("rasterio", "pyproj"):
            try:
                _mod = __import__(_pkg)
                if _pkg == "rasterio":
                    for _sub in ["proj_data", "proj_dir/share/proj"]:
                        _db = Path(_mod.__file__).parent / _sub / "proj.db"
                        if _db.exists():
                            _candidates_proj.append(_db); break
                else:
                    _db = Path(_mod.datadir.get_data_dir()) / "proj.db"
                    if _db.exists():
                        _candidates_proj.append(_db)
            except Exception:
                pass

        _proj_lib_found = None
        _best_ver = 0
        for _db in _candidates_proj:
            _ver = _proj_db_version(_db)
            if _ver == _PROJ_TARGET_VER:
                _proj_lib_found = _db.parent
                _best_ver = _ver
                break
            elif _ver > _best_ver:
                _best_ver = _ver
                _proj_lib_found = _db.parent

        if _proj_lib_found:
            env["PROJ_LIB"] = str(_proj_lib_found)
            match = "✓" if _best_ver == _PROJ_TARGET_VER else "⚠"
            print(f"  PROJ_LIB v{_best_ver} {match} (cible v{_PROJ_TARGET_VER}) : "
                  f"{_proj_lib_found}", flush=True)
        else:
            print("  AVERTISSEMENT : proj.db introuvable — reprojection peut échouer",
                  flush=True)

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
    # À 20×20 km / z18 : ~160 Mo warpé → seuil jamais atteint.
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
        print(f"  Taille estimée : ~{taille_go_est:.1f} Go → warp unique"
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
        try:
            from pyproj import Transformer as _Tr_bounds
            _tb = _Tr_bounds.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
            _lon0, _lat0 = _tb.transform(bbox_l93[0], bbox_l93[1])
            _lon1, _lat1 = _tb.transform(bbox_l93[2], bbox_l93[3])
        except Exception:
            _lon0, _lat0 = lamb93_to_wgs84_approx(bbox_l93[0], bbox_l93[1])
            _lon1, _lat1 = lamb93_to_wgs84_approx(bbox_l93[2], bbox_l93[3])
        _bounds = f"{min(_lon0,_lon1):.6f},{min(_lat0,_lat1):.6f},{max(_lon0,_lon1):.6f},{max(_lat0,_lat1):.6f}"
        _cx = (min(_lon0,_lon1) + max(_lon0,_lon1)) / 2
        _cy = (min(_lat0,_lat1) + max(_lat0,_lat1)) / 2
        cur.execute("INSERT INTO metadata VALUES (?,?)", ("bounds", _bounds))
        cur.execute("INSERT INTO metadata VALUES (?,?)",
                    ("center", f"{_cx:.6f},{_cy:.6f},{zoom_max}"))
    con.commit()

    total_insere = 0
    t_tile = time.time()

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
            print(f"  Source déjà en EPSG:3857 — warp ignoré", flush=True)
        else:
            warp_deja_fait = warped.exists() and warped.stat().st_size > 1_000_000 and not ecraser_tuiles
            if warp_deja_fait:
                print(f"  Warped cache : {warped.name}  "
                      f"({warped.stat().st_size/1e6:.0f} Mo) — réutilisé", flush=True)

        # ── 1. gdalwarp ──────────────────────────────────────────────────
        cmd_warp = [
            gdalwarp,
            "-s_srs", "EPSG:2154", "-t_srs", "EPSG:3857",
            "-tr",  str(res_max), str(res_max),
            "-r", "bilinear",
            "-of", "GTiff",
            "-co", "BIGTIFF=YES",
            "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
            "-co", "TILED=YES", "-co", "BLOCKXSIZE=512", "-co", "BLOCKYSIZE=512",
            "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
            "--config", "GDAL_CACHEMAX", "2048",
            "-overwrite",
        ]
        # ── Calcul de l'étendue cible en Web Mercator ────────────────────
        te_xmin = te_ymin = te_xmax = te_ymax = None
        # Toujours passer -te explicitement à gdalwarp — ainsi PROJ n'a pas
        # besoin de proj.db pour calculer l'étendue de sortie.
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
            try:
                from pyproj import Transformer as _Tr
                _t = _Tr.from_crs("EPSG:2154", "EPSG:3857", always_xy=True)
                te_xmin, te_ymin = _t.transform(x0, _y0)
                te_xmax, te_ymax = _t.transform(x1, _y1)
            except Exception:
                te_xmin, te_ymin = _lamb93_to_merc(x0, _y0)
                te_xmax, te_ymax = _lamb93_to_merc(x1, _y1)
            cmd_warp += ["-te", str(te_xmin), str(te_ymin),
                                str(te_xmax), str(te_ymax)]
        elif y0_l is not None:
            # Mode banding sans bb_src — cas dégradé, conversion approx
            # _lamb93_to_merc déjà définie plus haut dans cette portée
            te_xmin, te_ymin = _lamb93_to_merc(bb_src[0], y0_l)
            te_xmax, te_ymax = _lamb93_to_merc(bb_src[2], y1_l)
            cmd_warp += ["-te", str(te_xmin), str(te_ymin),
                                str(te_xmax), str(te_ymax)]

        if not warp_deja_fait:
            cmd_warp += proj_args + [str(tif_source), str(warped)]

            if len(tranches) > 1:
                print(f"\n  [{i_tr+1}/{len(tranches)}] Warp {nom_tr} "
                      f"res={res_max:.3f} m/px...", flush=True)
            else:
                print(f"  Warp EPSG:3857  res={res_max:.3f} m/px"
                      f"  (zoom {zoom_max})...", flush=True)

            code, elap, errs = _run_gdal_avec_jauge(cmd_warp, lbl, env)
            if code != 0 or not warped.exists():
                print(f"  ERREUR gdalwarp {nom_tr} (code {code})")
                for e in errs[:10]: print(f"    {e}")
                continue
            _enregistrer_fichier(warped)
            taille_w = warped.stat().st_size / 1e6
            print("\r  " + lbl.ljust(36) + " [" + "█"*30 +
                  f"] 100%  {_hms(elap)}  {taille_w:.0f} Mo")

            # Diagnostic dimensions warped
            bb_diag = _bbox_depuis_gdalinfo(warped, env)
            if bb_diag:
                _gti = _trouver_outil_gdal("gdalinfo")
                _r_diag = subprocess.run([_gti, "-json", str(warped)],
                                         capture_output=True, text=True, env=env)
                try:
                    _info = json.loads(_r_diag.stdout)
                    _sz = _info.get("size", [0, 0])
                    print(f"  warped dims : {_sz[0]} × {_sz[1]} px  "
                          f"bbox merc : {bb_diag[0]:.0f},{bb_diag[1]:.0f}"
                          f" → {bb_diag[2]:.0f},{bb_diag[3]:.0f}", flush=True)
                except Exception:
                    print(f"  warped bbox : {bb_diag}", flush=True)

            # ── 2. gdaladdo : overviews GAUSS ───────────────────────────────
            if gdal_addo and zoom_max > zoom_min:
                print(f"  Overviews (gauss) {overview_levels}...", flush=True)
                t_addo = time.time()
                cmd_addo = [gdal_addo, "-r", "gauss",
                            "--config", "COMPRESS_OVERVIEW", "DEFLATE",
                            "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
                            str(warped)] + [str(l) for l in overview_levels]
                _log_req(cmd_addo)
                r_addo = subprocess.run(cmd_addo, capture_output=True, env=env)
                if r_addo.returncode == 0:
                    print(f"  Overviews OK ({_hms(time.time()-t_addo)})")
                else:
                    print("  AVERTISSEMENT gdaladdo echoue - tuilage natif")
            elif not gdal_addo:
                print("  gdaladdo introuvable - tuilage natif")

        # ── 3. Bbox warped (EPSG:3857) ──────────────────────────────────────
        # Priorité : -te calculé lors du warp courant (pas besoin de proj.db).
        # Fallback mode cache : recalculer depuis bb_src avec pyproj/approx.
        if te_xmin is not None:
            bb_w = (te_xmin, te_ymin, te_xmax, te_ymax)
        elif warp_deja_fait and bb_src is not None:
            # Warped réutilisé : reconstruire la bbox Mercator depuis bb_src
            try:
                from pyproj import Transformer as _Tr2
                _t2 = _Tr2.from_crs("EPSG:2154", "EPSG:3857", always_xy=True)
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

        # ── 4. Tiling direct via rasterio ────────────────────────────────
        # Lecture directe du warped TIF par rasterio — pas de gdal_translate,
        # pas de fichiers temporaires, pas de proj.db requis pour les coords pixel.
        import rasterio as _rio
        from rasterio.windows import Window as _Win
        import numpy as _np

        batch = []
        BATCH = 500
        rangees_done = 0
        nb_echecs_tr = 0
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
                              f"] {pct:3d}%  {total_insere} tuiles  {_hms(elapsed)}{sfx}",
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

                        # Convertir en image PIL et redimensionner si zoom < zoom_max
                        if _w_count >= 3:
                            img_arr = _np.moveaxis(canvas[:3], 0, 2)
                        else:
                            img_arr = _np.stack(
                                [canvas[0]] * 3, axis=2)

                        band_img = Image.fromarray(img_arr.astype(_np.uint8))
                        # Pas de resize — rasterio a déjà lu à la bonne résolution

                    except Exception as _e_read:
                        nb_echecs_tr += 1
                        if nb_echecs_tr <= 3:
                            print(f"\n  ⚠ rasterio read échec z{z} ty={ty}: "
                                  f"{_e_read}", flush=True)
                        pct = int(rangees_done / total_rangees_tr * 100)
                        elapsed = int(time.time() - t_tile)
                        print(f"\r  z{zoom_min}-{zoom_max} [" +
                              "█" * int(pct/100*30) +
                              "░" * (30 - int(pct/100*30)) +
                              f"] {pct:3d}%  {total_insere} tuiles  {_hms(elapsed)}",
                              end="", flush=True)
                        continue

                    # Découper en tuiles individuelles
                    for i, tx in enumerate(range(tx0, tx1 + 1)):
                        left = i * TILE_SIZE
                        tile = band_img.crop((left, 0, left + TILE_SIZE, TILE_SIZE))
                        if tile.getbbox() is None:
                            continue
                        buf2 = io.BytesIO()
                        if _use_jpeg:
                            tile.convert("RGB").save(buf2, "JPEG",
                                                     quality=jpeg_quality,
                                                     optimize=False)
                        else:
                            tile.convert("RGB").save(buf2, "PNG",
                                                     optimize=False,
                                                     compress_level=1)
                        y_tms = (2 ** z - 1) - ty
                        batch.append((z, tx, y_tms, buf2.getvalue()))
                        total_insere += 1

                    band_img.close()

                rangees_done += 1
                pct  = int(rangees_done / total_rangees_tr * 100)
                bars = int(pct / 100 * 30)
                elapsed = int(time.time() - t_tile)
                sfx = f"  [{i_tr+1}/{len(tranches)}]" if len(tranches) > 1 else ""
                print(f"\r  z{zoom_min}-{zoom_max} [" +
                      "█"*bars + "░"*(30-bars) +
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

        # warped conservé dans dossier_ville/ pour réutilisation future
        taille_w = warped.stat().st_size / 1e6 if warped.exists() else 0
        print(f"  Cache tuilage conservé : {warped.name}  ({taille_w:.0f} Mo)"
              f"  — supprimez-le manuellement si inutile")

    con.close()
    elapsed = int(time.time() - t0)
    taille_mb = mbtiles.stat().st_size / 1e6 if mbtiles.exists() else 0
    print("\n  z" + str(zoom_min) + "-" + str(zoom_max) + " 100%  " + str(total_insere) + " tuiles  " + _hms(elapsed))
    if nb_echecs_tr > 0:
        print(f"  ⚠ {nb_echecs_tr} rangées rasterio échouées (tuiles manquantes)")
    print(f"  {mbtiles.name} : {total_insere} tuiles  ({taille_mb:.0f} Mo)")
    _creer_fichier(mbtiles, intermediaire=False)
    return mbtiles



# ============================================================
# PIPELINE WMTS — SCAN 25 / ORTHO
# ============================================================

WMTS_URL     = "https://data.geopf.fr/private/wmts"
WMTS_URL_PUB = "https://data.geopf.fr/wmts"
# Clé API IGN — chargée depuis lidar2map.env si présent, sinon valeur par défaut.
# Pour utiliser votre propre clé, créez lidar2map.env (non versionné) avec :
#   IGN_APIKEY=votre_cle
_apikey_env_path = Path(__file__).resolve().parent / "lidar2map.env"
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
    # ── Données thématiques (public, sans clé) ────────────────────────────────
    "cadastre":      ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS",      "normal", "image/png",  False),
    "ombrage":       ("ELEVATION.ELEVATIONGRIDCOVERAGE.SHADOW",    "normal", "image/png",  False),
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


def _lire_zoom_limites_wmts(layer, apikey_requis, apikey=""):
    """
    Interroge GetCapabilities WMTS IGN et retourne (zoom_min, zoom_max) réels
    pour la couche *layer* dans le TileMatrixSet PM.
    Résultat mis en cache pour la session ; retourne None si inaccessible.
    """
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
        req = urllib.request.Request(url, headers={"User-Agent": "lidar2map/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_bytes = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        print(f"  ⚠ GetCapabilities WMTS inaccessible ({type(e).__name__}: {e}) — plafonnement zoom ignoré")
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
        print(f"  ⚠ Parsing GetCapabilities échoué ({e})")
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
    return x, max(0, min(n - 1, y))


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
# TÉLÉCHARGEMENT D'UNE TUILE
# ============================================================

HEADERS = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/49.0"}


def telecharger_tuile(z, x, y, layer, style, fmt, apikey, apikey_requis):
    """
    Télécharge une tuile et retourne les bytes, ou None si absente/erreur.
    Réessaie MAX_TENTATIVES fois avec délai exponentiel.
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
            ct = resp.headers.get("content-type", "")
            if "xml" in ct or "html" in ct:
                resp.close(); return None   # réponse d'erreur serveur
            data = resp.read()
            if len(data) < 500:
                return None   # tuile vide (mer, hors couverture)
            return data
        except KeyboardInterrupt:
            print("\n\nInterrompu.")
            sys.exit(0)
        except (urllib.error.URLError, IOError, OSError) as e:
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
        print(f"  {chemin.name} → déjà présent")
        return chemin
    if chemin.exists() and ecraser_tuiles:
        chemin.unlink()
        print(f"  {chemin.name} → écrasement")

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

    BATCH       = 500
    FENETRE     = workers * 4   # nb de futures en vol simultané — équilibre RAM/débit
    batch       = []
    done        = 0
    ok          = 0
    absentes    = 0
    largeur     = 30
    t0          = time.time()

    _base_wmts = WMTS_URL if apikey_requis else WMTS_URL_PUB
    _log_req(f"{_base_wmts}?SERVICE=WMTS&LAYER={layer}&...", "WMTS IGN")
    print(f"  Téléchargement {total:,} tuiles → {chemin.name}...", flush=True)

    _fmt_out = "jpeg" if _convert_png else fmt_ext   # format réel inséré

    def _dl(args_t):
        z, x, y = args_t
        data = None
        # Lire depuis le cache si disponible
        if dossier_cache is not None and not ecraser_dalles:
            _cache_file = dossier_cache / str(z) / str(x) / f"{y}.{_fmt_out}"
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
                _cache_file = dossier_cache / str(z) / str(x) / f"{y}.{_fmt_out}"
                _cache_file.parent.mkdir(parents=True, exist_ok=True)
                _cache_file.write_bytes(data)
                _enregistrer_fichier(_cache_file)
        return z, x, y, data

    def _afficher(done, total, ok, absentes, z_courant, t0):
        pct     = done * 100 // max(total, 1)
        bars    = pct * largeur // 100
        elapsed = int(time.time() - t0)
        eta_s   = int(elapsed * (total - done) / max(done, 1))
        eta_str = f"  ETA {_hms(eta_s)}" if done > 10 and eta_s > 5 else ""
        print(f"\r  z{z_courant} [{'#'*bars}{'-'*(largeur-bars)}]"
              f" {pct:3d}%  {done:,}/{total:,}  ok:{ok:,}  abs:{absentes}"
              f"  {_hms(elapsed)}{eta_str}",
              end="", flush=True)

    tuiles_list = list(tuiles_iter)   # déjà une liste, mais on s'assure
    z_courant   = tuiles_list[0][0] if tuiles_list else zoom_min

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

        while pending:
            # Attendre la prochaine future terminée
            done_future = next(as_completed(pending))
            del pending[done_future]

            z, x, y, data = done_future.result()
            done      += 1
            z_courant  = z

            if data:
                y_tms = (1 << z) - 1 - y
                batch.append((z, x, y_tms, data))
                ok += 1
            else:
                absentes += 1

            if len(batch) >= BATCH:
                cur.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                con.commit()
                batch.clear()

            _afficher(done, total, ok, absentes, z_courant, t0)

            # Soumettre la prochaine tâche pour maintenir la fenêtre pleine
            if idx < n:
                t = tuiles_list[idx]
                pending[pool.submit(_dl, t)] = t
                idx += 1

    if batch:
        cur.executemany(
            "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
        con.commit()

    con.close()
    elapsed = int(time.time() - t0)
    taille_mo = chemin.stat().st_size / 1e6
    print(f"\n  100%  {ok} tuiles  ({absentes} absentes)  {_hms(elapsed)}")
    print(f"  {chemin.name} : {ok} tuiles  ({taille_mo:.0f} Mo)")
    return chemin

# ============================================================
# GÉNÉRATION RMAP
# ============================================================

# ── Helpers LE ────────────────────────────────────────────────────────────────
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
        print(f"  {rmap.name} → déjà présent")
        return rmap
    if rmap.exists() and ecraser:
        rmap.unlink()
    if not mbtiles_path.exists():
        print(f"  ERREUR : {mbtiles_path.name} introuvable")
        return None

    print(f"  RMAP ← {mbtiles_path.name}...", flush=True)
    t0 = time.time()

    EMPTY_JPEG = _empty_jpeg_256()
    TILE_SZ    = 256

    con = sqlite3.connect(str(mbtiles_path))

    # ── Phase 1 : inventaire par zoom ─────────────────────────────────────────
    zooms = [r[0] for r in con.execute(
        "SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level DESC").fetchall()]
    if not zooms:
        print("  ERREUR : MBTiles vide")
        con.close()
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
    print(f"  {n_zooms} zoom(s), {total_tiles:,} positions de tuiles", flush=True)

    # ── Phase 2 : écriture séquentielle — offsets enregistrés à la volée ──────
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
                zoom_hdr_offset[z] = f.tell()
                f.write(_wi(zd['w'])); f.write(_wi(-zd['h']))
                f.write(_wi(zd['nx'])); f.write(_wi(zd['ny']))
                tile_hdr_pos = f.tell()
                for _ in range(zd['nx'] * zd['ny']):
                    f.write(_wl(0))

                tile_off[z] = {}

                for tx in range(zd['nx']):
                    for ty in range(zd['ny']):
                        # Coordonnées tuile dans MBTiles
                        col     = zd['x0'] + tx
                        y_xyz   = zd['y0'] + ty
                        y_tms   = (1 << z) - 1 - y_xyz

                        row = con.execute(
                            "SELECT tile_data FROM tiles "
                            "WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                            (z, col, y_tms)).fetchone()
                        jpeg = row[0] if row else EMPTY_JPEG

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
        con.close()
        return None

    con.close()
    elapsed   = int(time.time() - t0)
    taille_mo = rmap.stat().st_size / 1e6
    print(f"\n  {rmap.name} : {taille_mo:.0f} Mo  {_hms(elapsed)}")
    _creer_fichier(rmap, intermediaire=False)
    return rmap


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
        print(f"  {sqlitedb.name} → déjà présent")
        return sqlitedb
    if sqlitedb.exists() and ecraser:
        sqlitedb.unlink()
    if not mbtiles_path.exists():
        print(f"  ERREUR : {mbtiles_path.name} introuvable")
        return None

    con_mb = sqlite3.connect(str(mbtiles_path))
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

    BATCH   = 2000
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
        con_mb.close(); con_db.close()
        sqlitedb.unlink(missing_ok=True)
        return None

    con_mb.close()
    con_db.close()
    elapsed   = int(time.time() - t0)
    taille_mo = sqlitedb.stat().st_size / 1e6
    print(f"\n  {sqlitedb.name} : {done:,} tuiles  ({taille_mo:.0f} Mo)"
          f"  {_hms(elapsed)}          ")
    _creer_fichier(sqlitedb, intermediaire=False)
    return sqlitedb



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
    """

    plugins_dir = Path.home() / ".openstreetmap" / "osmosis" / "plugins"
    jar_path    = plugins_dir / _MAPWRITER_JAR

    if jar_path.exists():
        return True

    print(f"  URL  : {_MAPWRITER_URL}")
    print(f"  Plugin mapwriter absent — téléchargement ({_MAPWRITER_JAR})...",
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
        print(f"  ERREUR téléchargement mapwriter : {type(e).__name__}: {e}")
        print(f"  Téléchargez manuellement :\n    {_MAPWRITER_URL}")
        print(f"  et copiez-le dans :\n    {plugins_dir}")
        return False

    print(f"  Plugin installé : {jar_path}")
    return True


def _preparer_osmosis(dossier_hint=None):
    """
    Vérifie mapwriter, trouve java + osmosis, retourne (osmosis_exe, java_home).
    Retourne (None, None) en cas d'échec.
    dossier_hint : Path optionnel pour la recherche de tagmapping-min.xml (non utilisé ici).
    """
    if not _verifier_mapwriter():
        print("  ERREUR : plugin mapwriter manquant — carte .map impossible.")
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


def generer_carte_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                      osm_tags=None, export_geojson=True, ecraser_tuiles=False,
                      skip_bbox=False):
    """
    Génère une carte Mapsforge (.map) via osmosis — format natif Locus Map.
    Nécessite osmosis + tagmapping-min.xml dans le même dossier que le script.
    """
    import shutil as _sh

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    chemin_map     = dossier_ville / f"{nom_zone}.map"
    chemin_map_tmp = dossier_ville / f"{nom_zone}.map.tmp"

    # Nettoyer un éventuel .map.tmp laissé par une exécution précédente interrompue
    chemin_map_tmp.unlink(missing_ok=True)

    # Le GeoJSON est produit en .geojson.gz — vérifier les deux extensions
    chemin_geojson_gz  = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    chemin_geojson_raw = dossier_ville / f"{nom_zone}_osm.geojson"
    geojson_present = chemin_geojson_gz.exists() or chemin_geojson_raw.exists()

    if chemin_map.exists() and ecraser_tuiles:
        chemin_map.unlink()
        print(f"  Carte OSM : écrasement {chemin_map.name}")
        # Supprimer aussi les geojson pour les recalculer
        for _gf in [chemin_geojson_gz, chemin_geojson_raw]:
            if _gf.exists(): _gf.unlink()
    if chemin_map.exists() and not ecraser_tuiles:
        if not export_geojson or geojson_present:
            print(f"  Carte OSM déjà présente : {chemin_map.name} — ignorée")
            return chemin_map
        else:
            # .map ok mais .geojson(.gz) manquant
            # Utiliser le PBF filtré (déjà extrait par osmosis) si disponible
            print(f"  Carte OSM déjà présente : {chemin_map.name} — GeoJSON manquant, export...")
            chemin_pbf_filtre = dossier_ville / f"{nom_zone}_filtered.pbf"
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            if pbf_src == chemin_pbf_filtre:
                print(f"  PBF filtré existant : {chemin_pbf_filtre.name}")
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src, osm_tags=osm_tags, ecraser_tuiles=ecraser_tuiles)
            return chemin_map

    if not _verifier_mapwriter():
        print("  ERREUR : plugin mapwriter manquant — carte .map impossible.")
        return None

    _osmosis_exe, _java_home = _preparer_osmosis()
    if not _osmosis_exe:
        return None
    _env_osm = os.environ.copy()
    _env_osm["JAVA_HOME"] = _java_home
    # JAVA_OPTS : heap max 6g — nécessaire pour le PBF France (~5 Go)
    # JAVACMD_OPTIONS : variable lue par osmosis.bat pour passer les options JVM
    _env_osm["JAVA_OPTS"]       = "-Xmx6g"
    _env_osm["JAVACMD_OPTIONS"] = "-Xmx6g"

    # tagmapping-min.xml : chercher à côté du script puis dans le dossier dalles
    _tagmapping = None
    for cand in [
        DOSSIER_TRAVAIL / "tagmapping-min.xml",
        Path(str(osm_pbf)).parent / "tagmapping-min.xml",
        dossier_ville / "tagmapping-min.xml",
    ]:
        if cand.exists():
            _tagmapping = str(cand)
            break
    if not _tagmapping:
        print("  AVERTISSEMENT : tagmapping-min.xml introuvable — utilisation défaut osmosis")

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
    r = subprocess.run(
        cmd_str if _shell else cmd,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        shell=_shell, env=_env_osm,
    )

    if r.returncode == 0 and chemin_map_tmp.exists() and chemin_map_tmp.stat().st_size > 0:
        chemin_map_tmp.rename(chemin_map)
        taille = chemin_map.stat().st_size / 1e6
        print(f"  {chemin_map.name} : {taille:.1f} Mo  {_hms(time.time()-t0)}")
        if export_geojson:
            pbf_src = chemin_pbf_filtre if chemin_pbf_filtre.exists() else osm_pbf
            generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, pbf_src, osm_tags=osm_tags)
        return chemin_map
    else:
        chemin_map_tmp.unlink(missing_ok=True)
        print(f"  ERREUR osmosis mapfile-writer (code {r.returncode})")
        if r.stderr:
            # Filtrer le bruit SLF4J/Java INFO pour exposer l'erreur réelle
            lignes_err = [l for l in r.stderr.splitlines()
                          if not any(tok in l for tok in
                                     ("SLF4J:", "INFOS:", "INFO:", "org.openstreetmap",
                                      "Osmosis Version", "StaticLoggerBinder"))]
            if lignes_err:
                print("  Détail osmosis :")
                for _l in lignes_err[:20]:
                    print(f"    {_l}")
            else:
                print(f"  {r.stderr.strip()[:600]}")
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
                        version="lidar2map 1.0.0 (2026-03)")
    parser.add_argument("--ignlidar", action="store_true",
                        help="Mode LiDAR MNT IGN")

    # ── Découpage à priori (raster uniquement) ──────────────────────────────
    grp_priori = parser.add_argument_group(
        "Découpage à priori — --ignlidar uniquement",
        "Traitement séquentiel par morceaux avec reprise automatique (manifeste.json).\n"
        "Les même paramètres contrôlent aussi le découpage des fichiers de sortie.")
    grp_priori.add_argument("--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Nombre de colonnes de la grille (Est-Ouest).")
    grp_priori.add_argument("--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Nombre de lignes de la grille (Nord-Sud).")
    grp_priori.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative : découpe en carrés de ~KM km.")
    grp_priori.add_argument("--nettoyage", action="store_true",
                            help="Supprimer dalles + TIF intermédiaires après chaque morceau. "
                                 "Indispensable pour les grandes zones (département entier).")

    # Localisation
    loc = parser.add_mutually_exclusive_group()
    loc.add_argument("--zone-ville",  metavar="NOM",
                     help="Nom de la ville (géocodage Nominatim)")
    loc.add_argument("--zone-gps",    metavar="LAT,LON",
                     help="Coordonnées GPS ex: 43.3156,6.0423")
    loc.add_argument("--zone-bbox",   metavar="X1,Y1,X2,Y2",
                     help="BBox Lambert 93 en mètres ex: 880000,6210000,1080000,6360000")
    loc.add_argument("--zone-departement", metavar="NUM",
                     help="Numéro de département ex: 83, 2A, 971. "
                          "Récupère automatiquement la bbox depuis geo.api.gouv.fr. "
                          "Le nom du dossier est défini automatiquement (ex: var_83).")

    # Zone
    parser.add_argument("--zone-rayon",    type=float, default=None, metavar="KM",
                        help="Rayon en km (défaut: 10)")

    # Chemins
    parser.add_argument("--dossier", metavar="CHEMIN", default=None,
                        help="Dossier racine de sortie (défaut: <script>/ign_lidar/). "
                             "Peut être un disque externe.")
    parser.add_argument("--dossier-dalles", metavar="CHEMIN", default=None,
                        help="Dossier cache des dalles IGN (défaut: <dossier>/dalles/). "
                             "Utile pour séparer cache et sorties sur disques différents.")
    parser.add_argument("--zone-nom", metavar="NOM", default=None,
                        help="Nom du dossier de sortie pour la zone traitée. "
                             "Obligatoire pour --gps et --bbox. "
                             "Ex: --nom plancherine  → ign_lidar/plancherine/")

    # Téléchargement
    parser.add_argument("--workers",  type=int,   default=NB_WORKERS, metavar="N",
                        help=f"Connexions parallèles (défaut: {NB_WORKERS})")
    parser.add_argument("--telechargement-compresser", action="store_true",
                        help="Compresser les dalles du cache (DEFLATE, ~x5)")
    parser.add_argument("--telechargement-forcer", action="store_true",
                        help="Re-télécharger les dalles déjà présentes")

    # Ombrages
    parser.add_argument("--ombrages", metavar="TYPE", nargs="+",
                        choices=["315", "045", "135", "225", "multi", "slope",
                                 "svf", "svf100", "lrm", "rrim", "tous", "aucun"],
                        help=(
                            "Ombrages à générer (défaut: interactif). "
                            "Valeurs : 315 045 135 225 multi slope svf svf100 lrm rrim tous aucun. "
                            "svf/svf100/lrm/rrim : calculés en numpy/scipy (scipy auto-installé). "
                            "Ex: --ombrages multi slope svf rrim"
                        ))
    parser.add_argument("--ombrages-elevation", type=int, default=None, metavar="DEG",
                        help=(f"Angle solaire des hillshades directionnels en degrés "
                              f"(défaut: {ELEVATION_SOLEIL}° — archéo optimal). "
                              f"Usage général : 45°. Archéologie : 20-30°."))

    # Mode non-interactif
    parser.add_argument("--oui", action="store_true",
                        help="Répondre Oui à toutes les questions (non-interactif)")
    parser.add_argument("--telechargement", action="store_true",
                        help="Télécharger les dalles IGN manquantes.")
    parser.add_argument("--dalles-purger-invalides", action="store_true",
                        help="Supprimer les dalles < 2 Mo du cache (dalles en mer, erreurs partielles). "
                             "Omettre --telechargement pour purger sans re-télécharger.")
    parser.add_argument("--dalles-migrer", action="store_true",
                        help="Réorganiser les dalles existantes en sous-dossiers par colonne X "
                             "(ex: D:/Lidar/Dalles/0958/LHD_FXX_0958_....tif). "
                             "À lancer une seule fois pour migrer l'ancienne structure à plat.")
    parser.add_argument("--dalles-renommer", action="store_true",
                        help="Renommer les dalles de l'ancienne convention (x2, ex: 0456_3107) "
                             "vers la nouvelle (x1, ex: 0912_6214). A lancer une seule fois.")
    parser.add_argument("--dalles-purger-hors-zone", action="store_true",
                        help="Supprimer du cache les dalles hors de la zone courante (bbox/département). "
                             "Utile pour libérer l'espace occupé par des dalles d'autres départements. "
                             "Requiert --departement, --bbox, --ville ou --gps.")
    parser.add_argument("--ombrages-compresser",  action="store_true", help="Compresser les ombrages bruts existants (DEFLATE)")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Écraser les dalles téléchargées existantes")
    parser.add_argument("--ombrages-ecraser", action="store_true", dest="ombrages_ecraser",
                        help="Écraser les ombrages existants")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Écraser les tuiles/MBTiles/.map existants")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles","rmap","sqlitedb","map","gz","geojson"],
                        default=[], metavar="FMT",
                        help="Formats de fichiers de sortie : mbtiles rmap sqlitedb (multi-valeurs).")
    parser.add_argument("--source", metavar="CHEMIN", default=None,
                        help="Fichier source existant — mode autonome, zone non requise. "
                             ".tif/.tiff : ombrage existant → MBTiles/RMAP "
                             "            (CRS auto-détecté : 3857=tuilage direct, autre=warp). "
                             ".mbtiles   : conversion → RMAP (requiert --rmap). "
                             ".pbf       : données OSM → carte (requiert --osm). "
                             "Ex: --source var_83_hillshade_multi.tif --zone-bbox ... --mbtiles --rmap "
                             "Ex: --source provence-alpes-cote-d-azur-latest.osm.pbf --osm")
    parser.add_argument("--zoom-min", type=int, default=13, metavar="N",
                        help="Zoom minimum des tuiles MBTiles (défaut: 13)")
    parser.add_argument("--zoom-max", type=int, default=18, metavar="N",
                        help="Zoom maximum des tuiles MBTiles (défaut: 18)")
    parser.add_argument("--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="Qualité JPEG des images dans les tuiles (défaut: 85). "
                             "75 = -35%% taille, quasi invisible. 60 = -55%%, léger flou.")
    parser.add_argument("--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format des images dans les tuiles : auto, jpeg ou png (défaut: auto).")
    parser.add_argument("--osm", action="store_true",
                        help="Générer un MBTiles vectoriel de superposition OSM "
                             "(chemins, toponymie, hydrographie, sites historiques). "
                             "Le PBF Geofabrik est téléchargé automatiquement si absent.")
    parser.add_argument("--couche", metavar="TAGS", nargs="+", default=None,
                        help="Pour --osm : tags OSM à inclure. "
                             "Ex: --couche highway=* waterway=* natural=water")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    _osm_seul = args.osm and not args.telechargement and not args.ombrages and not args.mbtiles

    print("=" * 55)
    if _osm_seul:
        print("  Carte OSM vectorielle")
    else:
        print("  Téléchargement MNT LiDAR HD IGN (WMS)")
        print("  GDAL (via subprocess)")
    print("=" * 55)
    print(f"  Dossier : {args.dossier or str(DOSSIER_TRAVAIL / "ign_lidar")}")
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
                # TIF cache absent (warped supprimé) → ignorer, on recalcule depuis les dalles
                print(f"  AVERTISSEMENT : source TIF introuvable : {Path(args.source).name}")
                print(f"  Recalcul depuis les dalles...")
                args.source = None
            else:
                print(f"  ERREUR : fichier source introuvable : {args.source}")
                sys.exit(1)
        ext = Path(args.source).suffix.lower() if args.source else ""

        if ext == ".mbtiles":
            # Conversion directe MBTiles → RMAP/SQLiteDB (exit immédiat, pas de zone requise)
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
            # Source OSM : traitée plus loin dans la section --osm
            if not args.osm:
                print("  ERREUR : --osm requis avec une source .pbf.")
                print(f"  Ex: --source {src_path.name} --zone-ville gareoult --osm")
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
                    print(f"  Source TIF EPSG:3857 détecté → tuilage direct (pas de warp)")
                else:
                    args._source_already_warped = False
                    print(f"  Source TIF EPSG:{_epsg} → warp L93→Mercator requis")
            except Exception as _e_crs:
                print(f"  AVERTISSEMENT CRS non détecté ({_e_crs}) — warp appliqué par défaut")
                args._source_already_warped = False
        else:
            print(f"  ERREUR : extension non reconnue pour --source : {ext}")
            print("  Extensions acceptées : .tif .tiff .mbtiles .pbf")
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
        not args.zone_ville and not args.zone_gps)
    if _source_tif_sans_zone:
        print("  ERREUR : --source TIF nécessite une zone : --zone-ville/--zone-rayon, --zone-bbox ou --zone-departement")
        sys.exit(1)
    if _migrer_seul and not args.zone_departement and not args.zone_bbox and not args.zone_ville and not args.zone_gps:
        # Mode migration pure : on n'a besoin que de dossier_dalles
        racine        = Path(args.dossier).resolve() if args.dossier else Path(str(DOSSIER_TRAVAIL / "ign_lidar"))
        dossier_dalles = Path(args.dossier_dalles).resolve() if args.dossier_dalles else DOSSIER_TRAVAIL / "cache" / "ign_lidar"
        dossier_dalles.mkdir(parents=True, exist_ok=True)
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]
        if not a_migrer:
            print("  Aucune dalle à migrer (dossier racine déjà vide ou structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} dalle(s) → sous-dossiers par colonne X...")
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
                            f.rename(dest)
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
            print(f"\r  Migration terminée : {migres} dalles déplacées, {erreurs} erreurs.")
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
        print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Surface : ~{surface_km2:.0f} km²  |  {len(dalles)} dalles")
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
        if not args.telechargement:
            print(f"  GPS -> lat={lat:.5f}, lon={lon:.5f}")
            try:
                from pyproj import Transformer
                t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
                cx, cy = t.transform(lon, lat)
            except ImportError:
                cx, cy = wgs84_to_lamb93_approx(lon, lat)
                print("  (pyproj absent, conversion approchee)")
            print(f"  Lambert 93 -> X={cx:.0f}, Y={cy:.0f}")

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
        print("  [2] Coordonnées GPS (lat, lon)")
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
            if not args.telechargement:
                print(f"  GPS -> lat={lat:.5f}, lon={lon:.5f}")
                try:
                    from pyproj import Transformer
                    t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
                    cx, cy = t.transform(lon, lat)
                except ImportError:
                    cx, cy = wgs84_to_lamb93_approx(lon, lat)
                    print("  (pyproj absent, conversion approchee)")
                print(f"  Lambert 93 -> X={cx:.0f}, Y={cy:.0f}")
        else:
            ville_saisie = input("  Nom de la ville : ").strip()
            if not ville_saisie:
                sys.exit(1)
            nom_zone = normaliser_nom(args.zone_nom or ville_saisie)
            if not args.telechargement:
                print(f"\n  Geocodage de '{ville_saisie}'...")
                cx, cy = geocoder_ville_l93(ville_saisie)
                if cx is None:
                    sys.exit(1)

    # Rayon + grille (modes ville / gps / interactif — pas bbox, dept, france)
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

    # ── Découpage à priori : traitement séquentiel morceau par morceau ────────
    _cols_pr = getattr(args, "cols_decoupe", 0) or 0
    _rows_pr = getattr(args, "rows_decoupe", 0) or 0
    if _cols_pr > 0 and _rows_pr > 0:
        sous_zones, mode_desc = _calculer_sous_zones_priori(
            bbox[0], bbox[1], bbox[2], bbox[3],
            _cols_pr * _rows_pr, 0.0, unite_m=True)
        if len(sous_zones) > 1:
            racine_pr = (Path(args.dossier).resolve() if args.dossier
                         else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_lidar")
            manifeste = Manifeste(racine_pr / nom_zone / "manifeste.json")
            n_total   = len(sous_zones)
            nb_done   = sum(1 for z in sous_zones
                            if manifeste.deja_traite(f"{z[0]+1:03d}x{z[1]+1:03d}"))
            print(f"\n  ══ Découpage à priori : {mode_desc} ══")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Reprise : {nb_done}/{n_total} morceaux déjà terminés")

            nb_ok = 0
            for i_z, (i_lat, i_lon, bx1_z, by1_z, bx2_z, by2_z) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} — déjà terminé")
                    nb_ok += 1
                    continue

                surface = (bx2_z-bx1_z)/1000 * (by2_z-by1_z)/1000
                print(f"\n  ── Morceau {cle}  ({i_z+1}/{n_total})  {nom_z} ──")
                print(f"     BBox L93 : {bx1_z:.0f},{by1_z:.0f} → "
                      f"{bx2_z:.0f},{by2_z:.0f}  (~{surface:.0f} km²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_lidar(args, (bx1_z, by1_z, bx2_z, by2_z),
                                        nom_z, nom_zone, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] ✓ Terminé en {_hms(int(time.time() - t0_z))}")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] ✗ ERREUR : {_e_z} — relancez pour reprendre")
                    raise

            print(f"\n  ══ Découpage à priori terminé : {nb_ok}/{n_total} morceaux ══")
            return
        print("  Découpage à priori : zone trop petite → traitement unique")

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
        # Afficher le temps de l'étape précédente + cumul
        if etape_cur[0] > 0:
            elap  = int(time.time() - etape_t0[0])
            cumul = int(time.time() - t_debut)
            print(f"  ✓ Étape {etape_cur[0]} terminée en {_hms(elap)}  (cumul {_hms(cumul)})")
        etape_cur[0] += 1
        etape_t0[0] = time.time()
        print("ETAPE:" + str(etape_cur[0]) + "/" + str(etapes_total) + " " + nom, flush=True)

    if args.telechargement:
        print_etape("Téléchargement dalles")
    if not _osm_seul and not (not args.telechargement and not args.ombrages):
        print(f"\n  Grille : {nb} dalle(s) de {DALLE_KM}x{DALLE_KM} km  (~{nb} km²)")
        print(f"  Espace : ~{taille_brut} Mo brut  /  ~{taille_comp} Mo compressé")
    if args.telechargement_forcer:
        print(f"  Mise à jour : dalles existantes re-téléchargées")
    if args.workers != NB_WORKERS:
        print(f"  Workers : {args.workers}")

    # Compression
    if args.telechargement_compresser:
        compresser = True
    elif args.oui or not args.telechargement:
        compresser = False  # pas de compression si téléchargement non demandé
    else:
        print(f"\n  Compression du cache :")
        print(f"  [1] Non  -> rapide,  ~{taille_brut} Mo")
        print(f"  [2] Oui  -> lent,    ~{taille_comp} Mo")
        compresser = (input("  Choix [1] : ").strip() or "1") == "2"
    if args.telechargement:
        print(f"  -> {'Compression activée' if compresser else 'Stockage brut'}")

    if not args.oui and args.telechargement:
        if input(f"\n  Lancer le téléchargement ? [O/n] : ").strip().lower() == "n":
            sys.exit(0)

    racine        = Path(args.dossier).resolve() if args.dossier else DOSSIER_TRAVAIL / "Projets" / nom_zone / "ign_lidar"
    dossier_dalles = Path(args.dossier_dalles).resolve() if args.dossier_dalles else DOSSIER_TRAVAIL / "cache" / "ign_lidar"
    dossier_ville  = racine
    _sans_telechargement = not getattr(args, "telechargement", False)
    _sans_ombrages = not getattr(args, "ombrages", None)
    if not _osm_seul and not (_sans_telechargement and _sans_ombrages):
        try:
            dossier_dalles.mkdir(parents=True, exist_ok=True)
        except (FileNotFoundError, OSError) as _e_dd:
            print(f"  ERREUR : dossier dalles inaccessible : {dossier_dalles}")
            print(f"  ({_e_dd})")
            print(f"  Vérifiez que le disque est connecté et relancez.")
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
        print(f"  {len(tous)} fichiers .tif trouvés dans {dossier_dalles}")
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
                f.rename(nouveau)
                renommes += 1
            else:
                f.unlink()  # doublon
                renommes += 1
        print(f"  Renommage : {renommes} dalles renommées, {ignores} ignorées")

    # -------------------------------------------------------
    # Migration dalles à plat → sous-dossiers par colonne X
    # -------------------------------------------------------
    if getattr(args, 'migrer_dalles', False) and dossier_dalles.exists():
        a_migrer = [f for f in dossier_dalles.glob("*.tif")]  # uniquement racine
        if not a_migrer:
            print("  Aucune dalle à migrer (dossier racine déjà vide ou structure OK).")
        else:
            print(f"  Migration : {len(a_migrer)} dalle(s) → sous-dossiers par colonne X...")
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
                            f.rename(dest)
                            break
                        except PermissionError:
                            time.sleep(0.2)  # attendre que l'AV relâche
                        except Exception as _e:
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
            print(f"  Migration terminée : {migres} dalles déplacées, {erreurs} erreurs.")

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
            print(f"  Purge terminée. {len(invalides)} fichiers supprimés.")
        else:
            print("  Aucune dalle invalide trouvée (toutes ≥ 50 Mo).")

    # -------------------------------------------------------
    # Purge des dalles hors zone courante
    # -------------------------------------------------------
    if args.dalles_purger_hors_zone and dossier_dalles.exists():
        # Source de vérité : dalles_zone.txt (généré par le WFS)
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        if dalles_zone_txt.exists():
            noms_zone_purge = set(dalles_zone_txt.read_text(encoding="utf-8").splitlines())
            noms_zone_purge = {n.strip() for n in noms_zone_purge if n.strip()}
            print(f"  Purge hors-zone : référence {dalles_zone_txt.name}"
                  f" ({len(noms_zone_purge)} dalles zone)")
        else:
            print(f"  ERREUR purge-hors-zone : {dalles_zone_txt.name} introuvable.")
            print(f"  Relancez avec --telechargement pour reconstruire la liste.")
            sys.exit(1)
        toutes = _rglob_tif_robuste(dossier_dalles)
        hors_zone = [f for f in toutes if f.name not in noms_zone_purge]
        if hors_zone:
            taille_go = sum(f.stat().st_size for f in hors_zone) / 1e9
            print(f"\n  Purge hors-zone : {len(hors_zone)} dalle(s) — {taille_go:.1f} Go")
            if not args.oui:
                rep = input("  Confirmer la suppression ? [o/N] : ").strip().lower()
                if rep != "o":
                    print("  Purge annulée.")
                    hors_zone = []
            for f in hors_zone:
                f.unlink()
            if hors_zone:
                print(f"  {len(hors_zone)} dalles supprimées, {taille_go:.1f} Go libérés.")
        else:
            print("  Aucune dalle hors zone trouvée.")

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
                print("\n  ATTENTION : --telechargement absent mais aucune dalle trouvée.")
                print(f"  Dossier dalles : {dossier_dalles}")
                print("  Ajoutez --telechargement pour télécharger les dalles manquantes.")
                sys.exit(1)
            print(f"\n  Téléchargement ignoré ({len(dalles_existantes)} dalle(s) existantes)")
            sauter_telechargement = True

    # -------------------------------------------------------
    # Téléchargement + assemblage
    # -------------------------------------------------------
    if not sauter_telechargement:
        ok = skip = absent = erreur = 0

        # ── Interrogation WFS IGN ─────────────────────────────────────────────
        tms_dalles = None
        try:
            from pyproj import Transformer as _TrWFS
            _t = _TrWFS.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
            lon1, lat1 = _t.transform(bbox[0], bbox[1])
            lon2, lat2 = _t.transform(bbox[2], bbox[3])
            lon_min_w = min(lon1, lon2) - 0.05
            lat_min_w = min(lat1, lat2) - 0.05
            lon_max_w = max(lon1, lon2) + 0.05
            lat_max_w = max(lat1, lat2) + 0.05
            print(f"  Interrogation TMS IGN (dalles disponibles)...", flush=True)
            print(f"  TMS bbox WGS84 : {lon_min_w:.4f},{lat_min_w:.4f} → "
                  f"{lon_max_w:.4f},{lat_max_w:.4f}", flush=True)
            tms_dalles = interroger_tms_dalles(lon_min_w, lat_min_w,
                                               lon_max_w, lat_max_w,
                                               bbox_l93=bbox)
            if tms_dalles is not None:
                pass  # déjà affiché dans interroger_tms_dalles
            else:
                print("  TMS indisponible — repli sur WMS dalle par dalle")
        except Exception as e_wfs:
            print(f"  TMS erreur ({e_wfs}) — repli sur WMS")

        largeur = 30; done = 0; t0_dl = time.time()

        # ── Étape 1 : WFS → liste officielle des dalles disponibles ─────────
        # ── Étape 2 : grille théorique → complète les dalles absentes du WFS ─
        # Le WFS IGN est incomplet : certaines dalles existent sur le WMS mais
        # ne sont pas référencées dans le catalogue WFS. On télécharge d'abord
        # les dalles WFS, puis on tente les cases manquantes via WMS.

        # Construire le dict complet : WFS en priorité, grille en complément
        a_telecharger_wfs  = []   # (nom, url_wfs)  — URL exacte IGN
        a_telecharger_wms  = []   # (x_km, y_km)    — grille théorique hors WFS

        noms_tms = set(tms_dalles.keys()) if tms_dalles else set()

        try:
            if tms_dalles is not None:
                for nom, url in tms_dalles.items():
                    if args.telechargement_forcer:
                        chemin_dalle(dossier_dalles, nom).unlink(missing_ok=True)
                    chemin_d = chemin_dalle(dossier_dalles, nom)
                    if not chemin_d.exists() or chemin_d.stat().st_size < SEUIL_DALLE_VALIDE:
                        a_telecharger_wfs.append((nom, url))
                    else:
                        skip += 1

            # Cases de la grille théorique absentes du WFS → tentative WMS
            for x_km, y_km in dalles:
                nom = nom_dalle(x_km, y_km)
                if nom in noms_tms:
                    continue  # déjà géré par WFS
                if args.telechargement_forcer:
                    chemin_dalle(dossier_dalles, nom).unlink(missing_ok=True)
                chemin_d = chemin_dalle(dossier_dalles, nom)
                if not chemin_d.exists() or chemin_d.stat().st_size < SEUIL_DALLE_VALIDE:
                    a_telecharger_wms.append((x_km, y_km))
                else:
                    skip += 1
        except OSError as _e_scan:
            msg = (f"Erreur accès disque dalles :\n{_e_scan}\n\n"
                   f"Vérifiez que le disque {dossier_dalles} est connecté.")
            print(f"  ERREUR : {msg}", flush=True)
            if WINDOWS:
                try:
                    import ctypes as _ct
                    _ct.windll.user32.MessageBoxW(0, msg, "lidar2map — Erreur disque", 0x10)
                except Exception:
                    pass
            sys.exit(1)

        nb_total = len(a_telecharger_wfs) + len(a_telecharger_wms)
        nb_wfs_skip = (len(noms_tms) - len(a_telecharger_wfs))
        print(f"  Dalles en cache : {nb_wfs_skip + skip}")
        if nb_total > 0:
            print(f"  À télécharger   : {nb_total}  (WFS:{len(a_telecharger_wfs)}  WMS:{len(a_telecharger_wms)})", flush=True)
        else:
            print(f"  Toutes les dalles sont déjà en cache — téléchargement ignoré", flush=True)

        def telecharger_une_wfs(a):
            i, (nom, url) = a
            res = telecharger_dalle_directe(nom, url, dossier_dalles)
            taille = 0
            if res in ("ok", "skip") and chemin_dalle(dossier_dalles, nom).exists():
                taille = chemin_dalle(dossier_dalles, nom).stat().st_size / 1e6
            return i, nom, res, taille

        def telecharger_une_wms(a):
            i, (x_km, y_km) = a
            nom = nom_dalle(x_km, y_km)
            res = telecharger_dalle(x_km, y_km, dossier_dalles, compresser)
            taille = 0
            if res == "ok" and chemin_dalle(dossier_dalles, nom).exists():
                taille = chemin_dalle(dossier_dalles, nom).stat().st_size / 1e6
            return i, nom, res, taille

        # Téléchargement WFS
        if a_telecharger_wfs:
            _log_req(WFS_URL, "WFS IGN LiDAR")
            print(f"  Phase 1/2 — WFS ({len(a_telecharger_wfs)} dalles)...", flush=True)
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(telecharger_une_wfs, (i, d)): i
                           for i, d in enumerate(a_telecharger_wfs, 1)}
                for future in as_completed(futures):
                    i, nom, res, taille = future.result()
                    done += 1
                    pct  = int(done * 100 / max(nb_total, 1))
                    bars = int(done * largeur / max(nb_total, 1))
                    barre_str = "█" * bars + "░" * (largeur - bars)
                    elap = int(time.time() - t0_dl)
                    label = "  Dalles IGN".ljust(40)
                    if res == "ok":
                        ok += 1
                        print(f"\r{label} [{barre_str}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
                              flush=True)
                        print(f"  [{done:4d}/{nb_total}] {nom} -> OK ({taille:.1f} Mo)")
                    elif res == "skip":
                        skip += 1
                    elif res == "absent":
                        absent += 1
                    else:
                        erreur += 1
                    print(f"\r{label} [{barre_str}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
                          end="", flush=True)

        # Téléchargement WMS (cases hors WFS)
        if a_telecharger_wms:
            print(f"\n  Phase 2/2 — WMS grille ({len(a_telecharger_wms)} cases)...",
                  flush=True)
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(telecharger_une_wms, (i, d)): i
                           for i, d in enumerate(a_telecharger_wms, 1)}
                for future in as_completed(futures):
                    i, nom, res, taille = future.result()
                    done += 1
                    pct  = int(done * 100 / max(nb_total, 1))
                    bars = int(done * largeur / max(nb_total, 1))
                    barre_str = "█" * bars + "░" * (largeur - bars)
                    elap = int(time.time() - t0_dl)
                    label = "  Dalles IGN".ljust(40)
                    ligne_barre = (f"\r{label} [{barre_str}] {pct:3d}%  "
                                   f"{done}/{nb_total}  {_hms(elap)}")
                    if res == "ok":
                        ok += 1
                        print(ligne_barre, flush=True)
                        print(f"  [{done:4d}/{nb_total}] {nom} -> OK ({taille:.1f} Mo)")
                    elif res == "skip":
                        skip += 1
                    elif res == "absent":
                        absent += 1
                    else:
                        erreur += 1
                    print(ligne_barre, end="", flush=True)

        if not a_telecharger_wfs and not a_telecharger_wms:
            print(f"  Toutes les dalles sont en cache ({skip} dalles) — téléchargement ignoré",
                  flush=True)

        print()  # fin de la barre (si barre affichée)

        print("\n" + "=" * 55)
        print(f"  Téléchargées    : {ok}")
        print(f"  Déjà présentes  : {skip}")
        print(f"  Non disponibles : {absent}")
        print(f"  Erreurs         : {erreur}")
        print("=" * 55)

        # ── Persistance de la liste des dalles de la zone ────────────────────
        # Inclut WFS + WMS (cases hors WFS téléchargées avec succès)
        noms_wfs_set = set(tms_dalles.keys()) if tms_dalles else set()
        noms_persistance = []
        # Dalles WFS présentes sur disque
        for nom in noms_wfs_set:
            if chemin_dalle(dossier_dalles, nom).exists() and \
                    chemin_dalle(dossier_dalles, nom).stat().st_size > SEUIL_DALLE_VALIDE:
                noms_persistance.append(nom)
        # Dalles WMS (hors WFS) présentes sur disque
        nb_wms_bonus = 0
        for x_km, y_km in dalles:
            nom = nom_dalle(x_km, y_km)
            if nom not in noms_wfs_set:
                if chemin_dalle(dossier_dalles, nom).exists() and \
                        chemin_dalle(dossier_dalles, nom).stat().st_size > SEUIL_DALLE_VALIDE:
                    noms_persistance.append(nom)
                    nb_wms_bonus += 1
        if noms_persistance:
            dalles_zone_txt = dossier_ville / "dalles_zone.txt"
            _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
            dalles_zone_txt.write_text(
                _bbox_hdr + "\n" + "\n".join(sorted(set(noms_persistance))), encoding="utf-8")
            _creer_fichier(dalles_zone_txt)
            print(f"  Liste dalles zone : {dalles_zone_txt.name}"
                  f" ({len(set(noms_persistance))} dalles"
                  f" dont {nb_wms_bonus} hors-WFS)")

    # -------------------------------------------------------
    # Ombrages
    # -------------------------------------------------------
    TOUS_OMBRAGES = ["315", "045", "135", "225", "multi", "slope",
                     "svf", "svf100", "lrm", "rrim"]

    # Dalles disponibles pour les ombrages :
    # 1. Seulement les dalles de la zone courante (filtre par nom)
    # 2. Seulement les fichiers valides (≥ 50 Mo)
    # Le dossier dalles est global — sans filtrage par zone, le VRT couvrirait
    # tous les départements présents et le hillshade serait énorme ou en erreur.
    if getattr(args, 'tif', None):
        # Mode --tif : pas besoin des dalles ni des ombrages
        dalles_ombrages = []
    elif dossier_dalles.exists():
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        noms_zone = set()  # initialisé ici — peut rester vide en mode OSM seul
        if dalles_zone_txt.exists():
            # Vérifier que la bbox en entête correspond à la zone courante
            _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
            _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
            _bbox_fichier  = _lignes[0].strip() if _lignes else ""
            if _bbox_fichier != _bbox_courante:
                print(f"  Zone modifiée — reconstruction {dalles_zone_txt.name} depuis le cache...")
                print(f"    Ancienne bbox : {_bbox_fichier}")
                print(f"    Nouvelle bbox : {_bbox_courante}")
                # Reconstruire depuis le cache disque sans retélécharger
                noms_grille = {nom_dalle(x, y) for x, y in dalles}
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_grille and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    dalles_zone_txt.write_text(
                        _bbox_courante + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  {dalles_zone_txt.name} reconstruit : {len(noms_zone)} dalle(s) en cache")
                else:
                    dalles_zone_txt.unlink(missing_ok=True)
                    print(f"  Aucune dalle en cache pour cette zone — utilisez --telechargement")
                    noms_zone = set()
            else:
                noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
                print(f"  Liste dalles zone : {dalles_zone_txt.name} ({len(noms_zone)} dalles)")
        elif not args.telechargement and dalles:
            # Si seul --osm demandé, pas besoin des dalles
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # on ne cherche pas les dalles
            else:
                # dalles_zone.txt absent mais grille connue → reconstruction depuis le cache disque
                print(f"  AVERTISSEMENT : {dalles_zone_txt.name} absent — reconstruction depuis grille bbox...")
                noms_grille = {nom_dalle(x, y) for x, y in dalles}
                toutes_dalles_dispo = _rglob_tif_robuste(dossier_dalles)
                noms_zone = {d.name for d in toutes_dalles_dispo
                             if d.name in noms_grille and d.stat().st_size > SEUIL_DALLE_VALIDE}
                if noms_zone:
                    _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
                    dalles_zone_txt.write_text(
                        _bbox_hdr + "\n" + "\n".join(sorted(noms_zone)), encoding="utf-8")
                    _creer_fichier(dalles_zone_txt)
                    print(f"  dalles_zone.txt reconstruit : {len(noms_zone)} dalle(s) trouvées sur disque")
                else:
                    print(f"  ERREUR : aucune dalle de la zone trouvée dans {dossier_dalles}")
                    print(f"  Relancez avec --telechargement pour télécharger les dalles.")
                    sys.exit(1)
        else:
            if args.osm and not args.ombrages and not args.mbtiles:
                pass  # mode OSM seul — pas besoin de dalles
            else:
                print(f"\n  ERREUR : {dalles_zone_txt.name} introuvable dans {dossier_ville}/")
                print(f"  Ce fichier est créé automatiquement lors du téléchargement.")
                print(f"  Relancez avec --telechargement pour le reconstruire.")
                print(f"  (Les dalles déjà présentes sur disque seront skippées, ~quelques secondes)")
                sys.exit(1)
        toutes_dalles    = sorted(_rglob_tif_robuste(dossier_dalles))
        dalles_zone      = [d for d in toutes_dalles if d.name in noms_zone]
        dalles_ombrages  = [d for d in dalles_zone   if d.stat().st_size > SEUIL_DALLE_VALIDE]
        nb_hors_zone     = len(toutes_dalles) - len(dalles_zone)
        nb_invalides     = len(dalles_zone)   - len(dalles_ombrages)
        if not _osm_seul:
            if nb_hors_zone:
                print(f"  {nb_hors_zone} dalle(s) hors zone ignorées (autres départements)")
            if nb_invalides:
                print(f"  {nb_invalides} dalle(s) invalides ignorées (< 2 Mo — mer ou hors couverture)")
            print(f"  {len(dalles_ombrages)} dalle(s) retenues pour les ombrages")
    else:
        dalles_ombrages = []
    # -------------------------------------------------------
    # Compression des ombrages existants
    # -------------------------------------------------------
    if args.ombrages_compresser:
        gdal_translate = _trouver_gdal_translate()
        if not gdal_translate:
            print("  ERREUR : gdal_translate introuvable.")
        else:
            env_dem = _env_gdaldem()
            tifs_bruts = [
                t for t in dossier_ville.glob("*.tif")
                if not t.name.startswith("_")
            ]
            # Filtrer ceux non compressés (taille > seuil heuristique : >500 Mo)
            tifs_a_compresser = [t for t in tifs_bruts if t.stat().st_size > 500e6]
            if not tifs_a_compresser:
                print("  Aucun ombrage brut trouvé (> 500 Mo) à compresser.")
            else:
                print(f"  {len(tifs_a_compresser)} fichier(s) à compresser :")
                for chemin_out in sorted(tifs_a_compresser):
                    taille_brut = chemin_out.stat().st_size / 1e6
                    chemin_tmp  = chemin_out.with_suffix(".tmp.tif")
                    chemin_out.rename(chemin_tmp)
                    cmd_cmp = [
                        gdal_translate, "-of", "GTiff",
                        "-co", "COMPRESS=DEFLATE", "-co", "PREDICTOR=2",
                        "-co", "TILED=YES", "-co", "BLOCKXSIZE=512", "-co", "BLOCKYSIZE=512",
                        "--config", "GDAL_NUM_THREADS", "ALL_CPUS",
                        str(chemin_tmp), str(chemin_out)
                    ]
                    code, elap, errs = _run_gdal_avec_jauge(cmd_cmp, chemin_out.name, env_dem)
                    chemin_tmp.unlink(missing_ok=True)
                    if code == 0:
                        taille_cmp = chemin_out.stat().st_size / 1e6
                        gain = int((1 - taille_cmp / taille_brut) * 100)
                        print("\r  " + chemin_out.name.ljust(56) +
                              " [" + "\u2588"*30 + "] 100%" +
                              str(round(taille_brut)).rjust(6) + " Mo -> " +
                              str(round(taille_cmp)).rjust(5) + " Mo  (-" +
                              str(gain) + "%)  " + _hms(elap))
                    else:
                        print("  ERREUR compression " + chemin_out.name)
                        for e in errs[:3]: print("    " + e)
                        chemin_tmp.rename(chemin_out)

    if dalles_ombrages and args.ombrages:
        if "aucun" in args.ombrages:
            choix_ombrages = []
        elif "tous" in args.ombrages:
            choix_ombrages = TOUS_OMBRAGES
        else:
            choix_ombrages = args.ombrages
    elif dalles_ombrages and not args.ombrages and not args.oui:
        # Mode interactif — pas de --ombrages, pas de --oui
        print(f"\n  Ombrages à générer :")
        print(f"  [1] Rapide     : multi + slope                                    (~1 min)")
        print(f"  [2] Archéo     : 315 + 045 + multi + slope                        (~2 min)")
        print(f"  [3] Archéo+SVF : multi + slope + SVF (20m) + SVF100 (100m)        (~35 min)")
        print(f"  [4] Archéo+LRM : multi + slope + LRM gaussien                     (~8 min)")
        print(f"  [5] Archéo+RRIM: multi + slope + RRIM (composite couleur)         (~25 min)")
        print(f"  [6] Complet    : 315 045 135 225 multi slope svf svf100 lrm rrim  (~80 min)")
        print(f"  [7] Aucun")
        print(f"  [8] Choix manuel  ex: multi slope svf rrim")
        print(f"  SVF/LRM/RRIM : numpy/scipy (scipy auto-installé si absent)")
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
        choix_ombrages = []  # --oui sans --ombrages → pas d'ombrage

    if choix_ombrages:
        surface_km2 = len(dalles_ombrages)  # ~1 dalle = 1 km²
        print_etape("Ombrages " + ", ".join(choix_ombrages))
        print(f"  Ombrages : {', '.join(choix_ombrages)}")
        elev = args.ombrages_elevation if args.ombrages_elevation is not None else ELEVATION_SOLEIL
        print(f"  Angle solaire : {elev}°")
        print(f"  Surface : ~{surface_km2} km²  — Durée estimée :"
              f" {'5-10 min' if surface_km2 < 100 else '15-45 min' if surface_km2 < 500 else '1h+'}"
              f" (selon le type d'ombrage et la machine)", flush=True)
        generer_ombrages(dalles_ombrages, dossier_ville, choix_ombrages,
                         elevation_soleil=elev, nom_zone=nom_zone,
                         ecraser_ombrages=args.ombrages_ecraser)

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
            _mbt_requis = not _mbt_path.exists() or _ecraser_l
            _mbt_out = None
            if _mbt_requis:
                _mbt_out = generer_mbtiles_lidar(_tif_src, dossier_ville, _nom_base,
                                           zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                                           format_tuiles=args.formats_image,
                                           jpeg_quality=args.qualite_image,
                                           bbox_l93=bbox,
                                           source_already_warped=getattr(args, "_source_already_warped", False),
                                           ecraser_tuiles=_ecraser_l)
            elif _mbt_path.exists():
                print(f"  MBTiles existant : {_mbt_path.name} — découpage/conversion directe")
                _mbt_out = _mbt_path
            _convertir_formats(_mbt_out, args)
        else:
            # Ombrages présents dans dossier_ville
            ombrages_tifs = [
                t for t in sorted(dossier_ville.glob("*.tif"))
                if not t.name.startswith("_")
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
                        print(f"  MBTiles existant : {_mbt_path2.name} — découpage/conversion directe")
                        _convertir_formats(_mbt_path2, args)
                        continue
                    _mbt_out = generer_mbtiles_lidar(tif, dossier_ville, nom_base,
                                               zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                                               format_tuiles=args.formats_image,
                                               jpeg_quality=args.qualite_image,
                                               bbox_l93=bbox,
                                               ecraser_tuiles=_ecraser_l)
                    _convertir_formats(_mbt_out, args)
            else:
                print("  Aucun ombrage trouvé pour MBTiles (générez d'abord --ombrages)")

    # ── Carte OSM vectorielle de superposition ───────────────────────────────
    if args.osm:
        print_etape("Carte OSM vectorielle")

        # Table département → URL Geofabrik
        _GEOFABRIK = {
            # Auvergne-Rhône-Alpes
            "01": "auvergne-rhone-alpes",  # Ain
            "03": "auvergne-rhone-alpes",  # Allier
            "07": "auvergne-rhone-alpes",  # Ardèche
            "15": "auvergne-rhone-alpes",  # Cantal
            "26": "auvergne-rhone-alpes",  # Drôme
            "38": "auvergne-rhone-alpes",  # Isère
            "42": "auvergne-rhone-alpes",  # Loire
            "43": "auvergne-rhone-alpes",  # Haute-Loire
            "63": "auvergne-rhone-alpes",  # Puy-de-Dôme
            "69": "auvergne-rhone-alpes",  # Rhône
            "73": "auvergne-rhone-alpes",  # Savoie
            "74": "auvergne-rhone-alpes",  # Haute-Savoie
            # Bourgogne-Franche-Comté
            "21": "bourgogne-franche-comte",  # Côte-d'Or
            "25": "bourgogne-franche-comte",  # Doubs
            "39": "bourgogne-franche-comte",  # Jura
            "58": "bourgogne-franche-comte",  # Nièvre
            "70": "bourgogne-franche-comte",  # Haute-Saône
            "71": "bourgogne-franche-comte",  # Saône-et-Loire
            "89": "bourgogne-franche-comte",  # Yonne
            "90": "bourgogne-franche-comte",  # Territoire de Belfort
            # Bretagne
            "22": "bretagne",  # Côtes-d'Armor
            "29": "bretagne",  # Finistère
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
            # Île-de-France
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
            "19": "nouvelle-aquitaine",  # Corrèze
            "23": "nouvelle-aquitaine",  # Creuse
            "24": "nouvelle-aquitaine",  # Dordogne
            "33": "nouvelle-aquitaine",  # Gironde
            "40": "nouvelle-aquitaine",  # Landes
            "47": "nouvelle-aquitaine",  # Lot-et-Garonne
            "64": "nouvelle-aquitaine",  # Pyrénées-Atlantiques
            "79": "nouvelle-aquitaine",  # Deux-Sèvres
            "86": "nouvelle-aquitaine",  # Vienne
            "87": "nouvelle-aquitaine",  # Haute-Vienne
            # Occitanie
            "09": "occitanie",  # Ariège
            "11": "occitanie",  # Aude
            "12": "occitanie",  # Aveyron
            "30": "occitanie",  # Gard
            "31": "occitanie",  # Haute-Garonne
            "32": "occitanie",  # Gers
            "34": "occitanie",  # Hérault
            "46": "occitanie",  # Lot
            "48": "occitanie",  # Lozère
            "65": "occitanie",  # Hautes-Pyrénées
            "66": "occitanie",  # Pyrénées-Orientales
            "81": "occitanie",  # Tarn
            "82": "occitanie",  # Tarn-et-Garonne
            # Pays de la Loire
            "44": "pays-de-la-loire",  # Loire-Atlantique
            "49": "pays-de-la-loire",  # Maine-et-Loire
            "53": "pays-de-la-loire",  # Mayenne
            "72": "pays-de-la-loire",  # Sarthe
            "85": "pays-de-la-loire",  # Vendée
            # Provence-Alpes-Côte d'Azur
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
        _BASE_URL      = "https://download.geofabrik.de/europe/france"
        _BASE_URL_ROOT = "https://download.geofabrik.de/europe"

        # Résoudre le PBF source
        pbf = None
        if args.source and Path(args.source).suffix.lower() in (".pbf", ".osm"):
            pbf = Path(args.source)
            if not pbf.exists():
                print(f"  ERREUR : fichier PBF introuvable : {pbf}")
                pbf = None
        else:
            # Téléchargement automatique — détecter le département depuis le centre
            num_dep = getattr(args, "zone_departement", None)

            if not num_dep:
                # Modes ville/gps/bbox : cx, cy sont en Lambert 93
                # → convertir en WGS84 → requête geo.api.gouv.fr reverse
                try:
                    clon, clat = lamb93_to_wgs84_approx(cx, cy)
                    url_rev = (f"https://geo.api.gouv.fr/communes"
                               f"?lon={clon:.5f}&lat={clat:.5f}"
                               f"&fields=codeDepartement&format=json")
                    import urllib.request as _urr
                    req_rev = urllib.request.Request(
                        url_rev,
                        headers={"User-Agent": "lidar-mnt-downloader/1.0 (outil SIG personnel)"})
                    with urllib.request.urlopen(req_rev, timeout=10) as resp_rev:
                        data_rev = json.loads(resp_rev.read())
                    if data_rev:
                        num_dep = data_rev[0].get("codeDepartement")
                        print(f"  Département détecté : {num_dep}", flush=True)
                except Exception as e_rev:
                    print(f"  Géocodage inverse échoué ({e_rev})")

            region_slug = _GEOFABRIK.get(num_dep) if num_dep else None
            if not region_slug:
                print(f"  Département {num_dep} non trouvé dans la table Geofabrik.")
                print(f"  Repli sur le PBF national France (~4 Go).")
                url_pbf = f"{_BASE_URL_ROOT}/france-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / "france-latest.osm.pbf"
            else:
                url_pbf = f"{_BASE_URL}/{region_slug}-latest.osm.pbf"
                osm_dir = DOSSIER_TRAVAIL / "cache" / "osm_vecteur"
                osm_dir.mkdir(parents=True, exist_ok=True)
                pbf = osm_dir / f"{region_slug}-latest.osm.pbf"

            # Téléchargement PBF commun (national ou régional)
            _SEUIL_PBF = 1_000_000  # 1 Mo minimum — PBF vide ou tronqué → re-télécharger
            if pbf.exists() and pbf.stat().st_size >= _SEUIL_PBF:
                print(f"  PBF existant : {pbf.name}  "
                      f"({pbf.stat().st_size/1e9:.1f} Go)")
            else:
                if pbf.exists():
                    print(f"  PBF tronqué ({pbf.stat().st_size} octets) — re-téléchargement.")
                    pbf.unlink()
                _log_req(str(url_pbf), 'Geofabrik')
                print(f"  Téléchargement {url_pbf}...")
                print(f"  Destination : {pbf}", flush=True)
                try:
                    import urllib.request as _ur
                    taille_dl = 0
                    t0_dl = time.time()
                    req = urllib.request.Request(url_pbf,
                                      headers={"User-Agent":
                                               "lidar-mnt-downloader/1.0"})
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
                    # Vérifier que le fichier n'est pas vide/tronqué
                    if taille_dl < _SEUIL_PBF:
                        print(f"  ERREUR : PBF téléchargé trop petit ({taille_dl} octets)"
                              f" — téléchargement échoué (réseau ? accès Geofabrik ?).")
                        pbf.unlink(missing_ok=True)
                        pbf = None
                except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e_dl:
                    print(f"\n  ERREUR téléchargement PBF ({type(e_dl).__name__}) : {e_dl}")
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
                # Dossier dédié OSM — pas le dossier LiDAR
                dossier_osm = (Path(args.dossier).resolve() if args.dossier
                               else DOSSIER_TRAVAIL / "Projets" / nom_zone / "osm_vecteur")
                dossier_osm.mkdir(parents=True, exist_ok=True)
                generer_carte_osm(bbox_wgs, dossier_osm, nom_zone, pbf,
                                  osm_tags=(args.couche
                                            if getattr(args, 'couche', None)
                                            else getattr(args, 'osm_tags', None)),
                                  export_geojson="gz" in args.formats_fichier or "geojson" in args.formats_fichier,
                                  ecraser_tuiles=args.tuiles_ecraser,
                                  skip_bbox=False)

    if etape_cur[0] > 0:
        elap  = int(time.time() - etape_t0[0])
        cumul = int(time.time() - t_debut)
        print(f"  ✓ Étape {etape_cur[0]} terminée en {_hms(elap)}  (cumul {_hms(cumul)})")
    total = int(time.time() - t_debut)
    m, s  = divmod(total, 60)
    print(f"\n  Terminé ! Dossier : {dossier_osm if (_osm_seul and 'dossier_osm' in dir()) else dossier_ville}")
    print(f"  Durée totale : {m}m{s:02d}s")
    dossier_res = str(dossier_osm if (_osm_seul and "dossier_osm" in dir()) else dossier_ville)
    _historique_depuis_argv(total, dossier_res)




# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================


# ============================================================
# DÉCOUPAGE À PRIORI — FONCTIONS UTILITAIRES
# ============================================================



def _calculer_sous_zones_priori(x1, y1, x2, y2, n_morceaux, rayon_km, unite_m=True):
    """
    Divise une bbox en sous-zones pour le découpage à priori.

    unite_m=True  : bbox en mètres  (Lambert 93)  — retourne (i_lat, i_lon, x1, y1, x2, y2)
    unite_m=False : bbox en degrés  (WGS84)        — retourne (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n)

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
        mode_desc = f"{n_morceaux} morceaux ({n_rows}×{n_cols})"
    else:
        if unite_m:
            dy = dx = rayon_km * 1000
        else:
            lat_c = (y1 + y2) / 2
            dy = rayon_km / 111.0
            dx = rayon_km / (111.0 * math.cos(math.radians(lat_c)))
        n_rows = max(1, int(math.ceil(hauteur / dy)))
        n_cols = max(1, int(math.ceil(largeur / dx)))
        mode_desc = f"~{rayon_km:.0f} km/morceau ({n_rows}×{n_cols})"

    sous_zones = []
    for i_lat in range(n_rows):
        y_s = y1 + i_lat * dy
        y_n = min(y_s + dy, y2)
        for i_lon in range(n_cols):
            x_w = x1 + i_lon * dx
            x_e = min(x_w + dx, x2)
            sous_zones.append((i_lat, i_lon, x_w, y_s, x_e, y_n))
    return sous_zones, mode_desc

def _lister_dalles_zone(dalles, dossier_dalles, dossier_ville, bbox):
    """
    Retourne la liste des dalles valides pour la zone courante,
    en se basant sur dalles_zone.txt ou en reconstruisant depuis le cache disque.
    """
    noms_zone = set()
    dalles_zone_txt = dossier_ville / "dalles_zone.txt"
    if dalles_zone_txt.exists():
        _lignes = dalles_zone_txt.read_text(encoding="utf-8").splitlines()
        _bbox_courante = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
        if _lignes and _lignes[0].strip() == _bbox_courante:
            noms_zone = {n.strip() for n in _lignes[1:] if n.strip() and not n.startswith("#")}
    if not noms_zone:
        noms_grille = {nom_dalle(x, y) for x, y in dalles}
        toutes = _rglob_tif_robuste(dossier_dalles)
        noms_zone = {d.name for d in toutes
                     if d.name in noms_grille and d.stat().st_size > SEUIL_DALLE_VALIDE}
    toutes_dalles   = sorted(_rglob_tif_robuste(dossier_dalles))
    dalles_zone     = [d for d in toutes_dalles if d.name in noms_zone]
    dalles_ombrages = [d for d in dalles_zone   if d.stat().st_size > SEUIL_DALLE_VALIDE]
    return dalles_ombrages


def _telecharger_dalles_zone(dalles, bbox, dossier_dalles, dossier_ville, args):
    """
    Télécharge les dalles manquantes pour une bbox donnée.
    Extrait du bloc de téléchargement de main() — réutilisable par _traiter_bbox_lidar.
    """
    tms_dalles = None
    try:
        from pyproj import Transformer as _TrWFS
        _t = _TrWFS.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
        lon1, lat1 = _t.transform(bbox[0], bbox[1])
        lon2, lat2 = _t.transform(bbox[2], bbox[3])
        lon_min_w = min(lon1, lon2) - 0.05
        lat_min_w = min(lat1, lat2) - 0.05
        lon_max_w = max(lon1, lon2) + 0.05
        lat_max_w = max(lat1, lat2) + 0.05
        tms_dalles = interroger_tms_dalles(lon_min_w, lat_min_w,
                                           lon_max_w, lat_max_w,
                                           bbox_l93=bbox)
    except Exception as e_wfs:
        print(f"  TMS erreur ({e_wfs}) — repli sur WMS")

    compresser = getattr(args, "telechargement_compresser", False)

    a_telecharger_wfs = []
    a_telecharger_wms = []
    noms_tms = set(tms_dalles.keys()) if tms_dalles else set()
    ok = skip = absent = erreur = 0

    if tms_dalles:
        for nom, url in tms_dalles.items():
            if args.telechargement_forcer:
                chemin_dalle(dossier_dalles, nom).unlink(missing_ok=True)
            cd = chemin_dalle(dossier_dalles, nom)
            if not cd.exists() or cd.stat().st_size < SEUIL_DALLE_VALIDE:
                a_telecharger_wfs.append((nom, url))
            else:
                skip += 1

    for x_km, y_km in dalles:
        nom = nom_dalle(x_km, y_km)
        if nom in noms_tms:
            continue
        if args.telechargement_forcer:
            chemin_dalle(dossier_dalles, nom).unlink(missing_ok=True)
        cd = chemin_dalle(dossier_dalles, nom)
        if not cd.exists() or cd.stat().st_size < SEUIL_DALLE_VALIDE:
            a_telecharger_wms.append((x_km, y_km))
        else:
            skip += 1

    nb_total = len(a_telecharger_wfs) + len(a_telecharger_wms)
    largeur  = 30
    done = 0
    t0_dl = time.time()

    def _afficher_barre(done, nb_total, t0_dl):
        pct  = int(done * 100 / max(nb_total, 1))
        bars = int(done * largeur / max(nb_total, 1))
        elap = int(time.time() - t0_dl)
        barre = "█" * bars + "░" * (largeur - bars)
        print(f"\r  Dalles IGN [{barre}] {pct:3d}%  {done}/{nb_total}  {_hms(elap)}",
              end="", flush=True)

    if a_telecharger_wfs:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(telecharger_dalle_directe, nom, url, dossier_dalles): (nom,)
                       for nom, url in a_telecharger_wfs}
            for fut in as_completed(futures):
                nom = futures[fut][0]
                res = fut.result()
                done += 1
                if res == "ok":   ok += 1
                elif res == "skip": skip += 1
                elif res == "absent": absent += 1
                else: erreur += 1
                _afficher_barre(done, nb_total, t0_dl)

    if a_telecharger_wms:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(telecharger_dalle, x, y, dossier_dalles, compresser): (x, y)
                       for x, y in a_telecharger_wms}
            for fut in as_completed(futures):
                res = fut.result()
                done += 1
                if res == "ok":   ok += 1
                elif res == "skip": skip += 1
                elif res == "absent": absent += 1
                else: erreur += 1
                _afficher_barre(done, nb_total, t0_dl)

    if nb_total > 0:
        print()  # fin barre
        print(f"  Téléchargées : {ok}  Cache : {skip}  Absent : {absent}  Erreurs : {erreur}")

    # Persister dalles_zone.txt
    noms_wfs_set = set(tms_dalles.keys()) if tms_dalles else set()
    noms_persistance = []
    for nom in noms_wfs_set:
        cd = chemin_dalle(dossier_dalles, nom)
        if cd.exists() and cd.stat().st_size > SEUIL_DALLE_VALIDE:
            noms_persistance.append(nom)
    for x_km, y_km in dalles:
        nom = nom_dalle(x_km, y_km)
        if nom not in noms_wfs_set:
            cd = chemin_dalle(dossier_dalles, nom)
            if cd.exists() and cd.stat().st_size > SEUIL_DALLE_VALIDE:
                noms_persistance.append(nom)
    if noms_persistance:
        _bbox_hdr = f"# bbox:{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}"
        dalles_zone_txt = dossier_ville / "dalles_zone.txt"
        dalles_zone_txt.write_text(
            _bbox_hdr + "\n" + "\n".join(sorted(set(noms_persistance))), encoding="utf-8")
        _creer_fichier(dalles_zone_txt)


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
            dalles, bbox = calculer_grille_bbox(bx1, by1, bx2, by2)
            # Structure : <racine>/<nom_zone_base>/ign_lidar/<nom_z>/
            # (tous les morceaux sont sous-dossiers du même projet parent)
            racine_base = (Path(args.dossier).resolve() if args.dossier
                           else DOSSIER_TRAVAIL / "Projets" / nom_zone_base / "ign_lidar")
            racine = racine_base
            dossier_dalles = (Path(args.dossier_dalles).resolve() if args.dossier_dalles
                              else DOSSIER_TRAVAIL / "cache" / "ign_lidar")
            dossier_ville = racine / nom_z
            dossier_ville.mkdir(parents=True, exist_ok=True)
            dossier_dalles.mkdir(parents=True, exist_ok=True)

            if args.telechargement:
                _telecharger_dalles_zone(dalles, bbox, dossier_dalles, dossier_ville, args)

            if args.ombrages:
                TOUS = ["315","045","135","225","multi","slope","svf","svf100","lrm","rrim"]
                choix = (TOUS if "tous" in args.ombrages
                         else [] if "aucun" in args.ombrages
                         else args.ombrages)
                if choix:
                    dalles_ombrages = _lister_dalles_zone(dalles, dossier_dalles,
                                                          dossier_ville, bbox)
                    elev = (args.ombrages_elevation if args.ombrages_elevation is not None
                            else ELEVATION_SOLEIL)
                    generer_ombrages(dalles_ombrages, dossier_ville, choix,
                                     elevation_soleil=elev, nom_zone=nom_z,
                                     ecraser_ombrages=args.ombrages_ecraser)

            if args.mbtiles or args.rmap or args.sqlitedb:
                ombrages_tifs = [t for t in sorted(dossier_ville.glob("*.tif"))
                                 if not t.name.startswith("_")]
                for tif in ombrages_tifs:
                    stem   = re.sub(r'_tuilage_z\d+$', '', tif.stem)
                    suffix = stem[len(nom_z)+1:] if stem.startswith(nom_z+"_") else stem
                    nom_base = f"{nom_z}_{suffix}"
                    mbt_path = (dossier_ville
                                / f"{nom_base}_z{args.zoom_min}-{args.zoom_max}.mbtiles")
                    if not mbt_path.exists() or args.tuiles_ecraser:
                        mbt_out = generer_mbtiles_lidar(
                            tif, dossier_ville, nom_base,
                            zoom_min=args.zoom_min, zoom_max=args.zoom_max,
                            format_tuiles=args.formats_image,
                            jpeg_quality=args.qualite_image,
                            bbox_l93=bbox,
                            ecraser_tuiles=args.tuiles_ecraser)
                    else:
                        mbt_out = mbt_path
                    _convertir_formats(mbt_out, args, decoupe_sortie=False)
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
            if not chemin_mbtiles.exists() or args.tuiles_ecraser:
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
                _convertir_formats(chemin_mbtiles, args, decoupe_sortie=False)
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
        print(f"  ERREUR découpage : {src_mbtiles.name} introuvable")
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
        print(f"  Découpage : zone trop petite → fichier unique")
        con.close()
        return [src_mbtiles]

    print(f"  Découpage : {mode_desc}")

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
                print(f"  Morceau existant : {chemin_z.name} — ignoré")
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
            print(f"  Sous-zone [{i_lat},{i_lon}] : vide — ignorée")
            continue

        print(f"  Sous-zone [{i_lat},{i_lon}] : {n_tuiles:,} tuiles → {chemin_z.name}")
        sorties.append(chemin_z)

    con.close()
    return sorties


def _convertir_un_mbtiles(sf, args):
    """Génère RMAP/SQLiteDB depuis un MBTiles et le supprime si non conservé."""
    if args.rmap:     generer_rmap_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if args.sqlitedb: generer_sqlitedb_depuis_mbtiles(sf, ecraser=args.tuiles_ecraser)
    if not args.mbtiles and sf.exists():
        sf.unlink()
        print(f"  MBTiles supprimé : {sf.name}")


def _convertir_formats(mbt_out, args, decoupe_sortie=True):
    """
    Applique le découpage (grille cols×rows ou rayon_decoupe) puis génère
    RMAP/SQLiteDB pour chaque fichier résultant.
    Supprime le MBTiles source si non demandé.
    decoupe_sortie=False → saute le découpage (mode morceau à priori).
    """
    if not mbt_out:
        return

    r_dec  = getattr(args, "rayon_decoupe", 0.0)
    n_cols = getattr(args, "cols_decoupe",  0)
    n_rows = getattr(args, "rows_decoupe",  0)

    # En mode morceau à priori : pas de re-découpage
    if not decoupe_sortie:
        _convertir_un_mbtiles(mbt_out, args)
        return

    if n_cols > 0 and n_rows > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, n_cols=n_cols, n_rows=n_rows,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            if not args.mbtiles:
                mbt_out.unlink()
                print(f"  MBTiles source supprimé : {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args)
    elif r_dec > 0:
        sous_fichiers = decouper_mbtiles(mbt_out, rayon_km=r_dec,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            if not args.mbtiles:
                mbt_out.unlink()
                print(f"  MBTiles source supprimé : {mbt_out.name}")
        for sf in sous_fichiers:
            _convertir_un_mbtiles(sf, args)
    else:
        # Pas de découpage
        _convertir_un_mbtiles(mbt_out, args)



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

    if args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        if not nom_zone:
            nom_zone = normaliser_nom(nom_dep) + "_" + num_dep.lower()
        # geocoder_departement retourne du Lambert 93 — reconvertir en WGS84 pour le WFS
        try:
            from pyproj import Transformer as _Tr_dep
            _t_dep = _Tr_dep.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
            lon_min, lat_min = _t_dep.transform(bx1, by1)
            lon_max, lat_max = _t_dep.transform(bx2, by2)
        except ImportError:
            lon_min, lat_min = lamb93_to_wgs84_approx(bx1, by1)
            lon_max, lat_max = lamb93_to_wgs84_approx(bx2, by2)

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
        print(f"  Géocodage de '{args.zone_ville}'...")
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
    Mode --decouper : découpe a posteriori un MBTiles existant.
    Usage : lidar2map.py --decouper --source fichier.mbtiles
            [--cols C --rows R | --rayon-decoupe KM]
            [--formats-fichier mbtiles rmap sqlitedb]
            [--tuiles-ecraser]
    """
    import argparse
    parser = argparse.ArgumentParser(
        prog="lidar2map.py --decouper",
        description="Découpage a posteriori d'un MBTiles existant.")
    parser.add_argument("--decouper", action="store_true")
    parser.add_argument("--source", required=True, metavar="CHEMIN",
                        help="Fichier .mbtiles source à découper.")
    parser.add_argument("--cols", type=int, default=0, metavar="N",
                        help="Nombre de colonnes de la grille (Est-Ouest).")
    parser.add_argument("--rows", type=int, default=0, metavar="N",
                        help="Nombre de lignes de la grille (Nord-Sud).")
    parser.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                        dest="rayon_decoupe", help="Découpe en carrés de ~KM km.")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles", "rmap", "sqlitedb"], default=["mbtiles"],
                        metavar="FMT")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser")
    parser.add_argument("--oui", action="store_true")
    args = parser.parse_args()
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff

    src = Path(args.source)
    if not src.exists():
        print(f"  ERREUR : fichier introuvable : {src}"); sys.exit(1)
    if src.suffix.lower() != ".mbtiles":
        print(f"  ERREUR : --source attend un .mbtiles (reçu : {src.suffix})"); sys.exit(1)

    print("=" * 55)
    print("  Découpage raster MBTiles")
    print("=" * 55)
    print(f"  Source  : {src}")
    print(f"  Formats : {' '.join(_ff)}")
    if args.cols > 0 and args.rows > 0:
        print(f"  Grille  : {args.cols} cols × {args.rows} lignes")
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
    print("\n  Découpage terminé.")


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
                        version="lidar2map 1.0.0 (2026-03)")
    parser.add_argument("--ignraster", action="store_true",
                        help="Mode raster IGN via WMTS. "
                             "Utiliser --couche pour la couche (défaut: scan25). "
                             "Ex: --ignraster --couche GEOGRAPHICALGRIDSYSTEMS.MAPS")

    # ── Découpage à priori (raster uniquement) ──────────────────────────────
    grp_priori = parser.add_argument_group(
        "Découpage à priori — --ignraster uniquement",
        "Traitement séquentiel par morceaux avec reprise automatique (manifeste.json).\n"
        "Les même paramètres contrôlent aussi le découpage des fichiers de sortie.")
    grp_priori.add_argument("--cols-decoupe", type=int, default=0, metavar="N",
                            dest="cols_decoupe",
                            help="Nombre de colonnes de la grille (Est-Ouest).")
    grp_priori.add_argument("--rows-decoupe", type=int, default=0, metavar="N",
                            dest="rows_decoupe",
                            help="Nombre de lignes de la grille (Nord-Sud).")
    grp_priori.add_argument("--rayon-decoupe", type=float, default=0.0, metavar="KM",
                            dest="rayon_decoupe",
                            help="Alternative : découpe en carrés de ~KM km.")
    grp_priori.add_argument("--nettoyage", action="store_true",
                            help="Supprimer dalles + TIF intermédiaires après chaque morceau. "
                                 "Indispensable pour les grandes zones (département entier).")

    # Zone
    zone = parser.add_mutually_exclusive_group()
    zone.add_argument("--zone-ville",       metavar="NOM")
    zone.add_argument("--zone-gps",         metavar="LAT,LON")
    zone.add_argument("--zone-bbox",        metavar="W,S,E,N",
                      help="BBox WGS84 : lon_min,lat_min,lon_max,lat_max")
    zone.add_argument("--zone-departement", metavar="NUM")
    parser.add_argument("--zone-rayon",  type=float, default=10.0, metavar="KM")
    parser.add_argument("--zone-nom",    metavar="NOM", default=None)

    # Couche + clé
    parser.add_argument("--couche",  default="planign",
                        choices=list(COUCHES.keys()),
                        help="Couche WMTS (défaut: planign — public, sans clé). "
                             "Couches pro restreintes : scan25 scan25tour scan100 scanoaci.")
    parser.add_argument("--apikey",  default="", metavar="CLE",
                        help="Clé API IGN pour les couches restreintes (scan25, scan100…). "
                             "⚠ Accès professionnel uniquement (compte cartes.gouv.fr + SIRET). "
                             "Les particuliers doivent utiliser les couches publiques (planign, ortho…). "
                             "Peut aussi être définie via la variable d'env IGN_APIKEY.")

    # Zooms
    parser.add_argument("--zoom-min", type=int, default=10, metavar="N")
    parser.add_argument("--zoom-max", type=int, default=16, metavar="N")

    # Sorties
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["mbtiles","rmap","sqlitedb"],
                        default=[], metavar="FMT",
                        help="Formats de fichiers de sortie : mbtiles rmap sqlitedb (multi-valeurs).")
    parser.add_argument("--source",   metavar="CHEMIN", default=None,
                        help="Fichier .mbtiles existant → conversion RMAP "
                             "(mode autonome, zone non requise). Requiert --rmap. "
                             "Ex: --source gareoult_scan25_z12-16.mbtiles --rmap")
    parser.add_argument("--dossier",  metavar="CHEMIN", default=None,
                        help="Dossier de sortie (défaut: ./ign_raster/)")

    # Comportement
    parser.add_argument("--workers",       type=int, default=NB_WORKERS, metavar="N")
    parser.add_argument("--formats-image", choices=["auto","jpeg","png"], default="auto",
                        metavar="FMT", dest="formats_image",
                        help="Format des images dans les tuiles : auto, jpeg ou png (défaut: auto).")
    parser.add_argument("--qualite-image", type=int, default=85, metavar="Q",
                        dest="qualite_image",
                        help="Qualité JPEG des images dans les tuiles (défaut: 85).")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Écraser les tuiles en cache (re-téléchargement forcé)")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Écraser les MBTiles existants")
    parser.add_argument("--oui",           action="store_true")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    # Résolution --formats-fichier → flags booléens
    _ff = args.formats_fichier
    args.mbtiles  = "mbtiles"  in _ff
    args.rmap     = "rmap"     in _ff
    args.sqlitedb = "sqlitedb" in _ff
    if not args.formats_image:
        args.formats_image = "auto"

    # ── --source : conversion autonome MBTiles → RMAP (exit immédiat) ────────
    if args.source:
        p = Path(args.source)
        if not p.exists():
            print(f"  ERREUR : fichier introuvable : {args.source}")
            sys.exit(1)
        if p.suffix.lower() != ".mbtiles":
            print(f"  ERREUR : --source attend un .mbtiles (reçu : {p.suffix})")
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
        print(f"  Couche : {layer} (identifiant direct)")
    # Forcer le format image si demandé explicitement
    if args.formats_image == "jpeg" and img_fmt != "image/jpeg":
        img_fmt = "image/jpeg"
    elif args.formats_image == "png" and img_fmt != "image/png":
        img_fmt = "image/png"
    fmt_ext = "jpg" if "jpeg" in img_fmt else "png"

    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    # ── Découpage à priori : traitement séquentiel morceau par morceau ────────
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
            print(f"\n  ══ Découpage à priori : {mode_desc} ══")
            print(f"  Manifeste : {manifeste.path}")
            if nb_done:
                print(f"  Reprise : {nb_done}/{n_total} morceaux déjà terminés")

            nb_ok = 0
            for i_z, (i_lat, i_lon, lon_w, lat_s, lon_e, lat_n) in enumerate(sous_zones):
                cle   = f"{i_lat+1:03d}x{i_lon+1:03d}"
                nom_z = f"{nom_zone}_{cle}"

                if manifeste.deja_traite(cle):
                    print(f"  [{cle}] {nom_z} — déjà terminé")
                    nb_ok += 1
                    continue

                surface_km2 = ((lon_e-lon_w)*111*math.cos(math.radians((lat_s+lat_n)/2))) * \
                              ((lat_n-lat_s)*111)
                print(f"\n  ── Morceau {cle}  ({i_z+1}/{n_total})  {nom_z} ──")
                print(f"     BBox WGS84 : {lon_w:.4f},{lat_s:.4f} → "
                      f"{lon_e:.4f},{lat_n:.4f}  (~{surface_km2:.0f} km²)")
                manifeste.debut_morceau(cle, nom_z)
                t0_z = time.time()
                try:
                    _traiter_bbox_wmts(args, (lon_w, lat_s, lon_e, lat_n),
                                       nom_z, nom_zone, layer, style, img_fmt, fmt_ext,
                                       apikey_requis, manifeste, cle)
                    manifeste.fin_morceau(cle, int(time.time() - t0_z))
                    print(f"  [{cle}] ✓ Terminé en {_hms(int(time.time() - t0_z))}")
                    nb_ok += 1
                    if getattr(args, "nettoyage", False):
                        _supprimer_fichiers(manifeste.fichiers_morceau(cle))
                except Exception as _e_z:
                    print(f"  [{cle}] ✗ ERREUR : {_e_z} — relancez pour reprendre")
                    raise

            elapsed = int(time.time() - t_debut)
            print(f"\n  ══ Découpage à priori terminé : {nb_ok}/{n_total} morceaux ══")
            print(f"  Durée totale : {_hms(elapsed)}")
            return
        print("  Découpage à priori : zone trop petite → traitement unique")

    # ── Calcul de la grille ───────────────────────────────────────────────────
    zoom_min = min(args.zoom_min, args.zoom_max)
    zoom_max = max(args.zoom_min, args.zoom_max)

    # ── Plafonnement selon capacités réelles IGN (GetCapabilities WMTS) ──────
    _limites_reel = _lire_zoom_limites_wmts(
        layer, apikey_requis, apikey=getattr(args, "apikey", ""))
    if _limites_reel:
        _zmin_reel, _zmax_reel = _limites_reel
        if zoom_max > _zmax_reel:
            print(f"  ⚠ Couche {args.couche} : zoom max IGN = {_zmax_reel} "
                  f"— zoom_max ramené de {zoom_max} à {_zmax_reel}.")
            zoom_max = _zmax_reel
            zoom_min = min(zoom_min, zoom_max)
        if zoom_min < _zmin_reel:
            print(f"  ⚠ Couche {args.couche} : zoom min IGN = {_zmin_reel} "
                  f"— zoom_min ramené de {zoom_min} à {_zmin_reel}.")
            zoom_min = _zmin_reel
            zoom_max = max(zoom_max, zoom_min)

    tuiles = calculer_grille_xyz(lat_min, lon_min, lat_max, lon_max,
                                 zoom_min, zoom_max)
    total  = len(tuiles)
    taille_est = estimer_taille(total, fmt_ext)

    print("=" * 55)
    print(f"  Carte IGN — {args.couche} ({layer})")
    print("=" * 55)
    print(f"  Zone    : {nom_zone}")
    print(f"  BBox    : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")
    print(f"  Zooms   : {zoom_min}–{zoom_max}")
    print(f"  Tuiles  : {total:,}  (~{taille_est} Mo estimés)")
    print(f"  Workers : {args.workers}")

    if not args.oui:
        rep = input("\n  Lancer le téléchargement ? [O/n] : ").strip().lower()
        if rep == "n":
            sys.exit(0)

    # ── Dossier de sortie ─────────────────────────────────────────────────────
    racine  = Path(args.dossier).resolve() if args.dossier \
              else Path(__file__).resolve().parent / "Projets" / nom_zone / "ign_raster"
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    nom_fichier = f"{nom_zone}_{args.couche}_z{zoom_min}-{zoom_max}"
    chemin_mbtiles = dossier / f"{nom_fichier}.mbtiles"
    # Cache tuiles : dossier/dalles/<z>/<x>/<y>.<ext>
    dossier_cache = DOSSIER_TRAVAIL / "cache" / "ign_raster"
    dossier_cache.mkdir(parents=True, exist_ok=True)
    print(f"  Cache dalles : {dossier_cache}")

    # ── Génération MBTiles ────────────────────────────────────────────────────
    _jpeg_q = args.qualite_image if img_fmt.lower() in ("image/png", "png") else None

    # Le MBTiles source doit être (re)généré si :
    #   - il n'existe pas encore
    #   - OU écraser est demandé explicitement
    # Dans tous les autres cas (fichier existant, pas d'écraser) on l'utilise tel quel
    # pour la conversion / le découpage.
    _ecraser   = args.tuiles_ecraser
    _mbtiles_requis = not chemin_mbtiles.exists() or _ecraser

    if not _mbtiles_requis and chemin_mbtiles.exists():
        print(f"  MBTiles existant : {chemin_mbtiles.name} — découpage/conversion directe")

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
        _convertir_formats(chemin_mbtiles, args)

    # ── Résumé ────────────────────────────────────────────────────────────────
    elapsed = int(time.time() - t_debut)
    print(f"\n  Terminé en {_hms(elapsed)}")
    print(f"  Fichiers dans : {dossier}")
    _historique_depuis_argv(elapsed, str(dossier))


# ============================================================
# INTERFACE GRAPHIQUE (tkinter)
# ============================================================




# ============================================================
# PIPELINE WFS IGN — VECTEUR (GeoJSON)
# ============================================================

COUCHES_WFS = {
    # ── Cadastre ──────────────────────────────────────────────────────────────
    "cadastre":        ("CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle",
                        "Parcelles cadastrales (PCI)"),
    # ── Hydrographie ──────────────────────────────────────────────────────────
    "cours_eau":       ("BDTOPO_V3:cours_d_eau",
                        "Cours d'eau BD TOPO V3"),
    "troncons_eau":    ("BDTOPO_V3:troncon_hydrographique",
                        "Tronçons hydrographiques BD TOPO V3"),
    "plans_eau":       ("BDTOPO_V3:plan_d_eau",
                        "Plans d'eau BD TOPO V3"),
    "detail_hydro":    ("BDTOPO_V3:detail_hydrographique",
                        "Détails hydrographiques (sources, cascades…)"),
    # ── Bâti / structures ─────────────────────────────────────────────────────
    "batiments":       ("BDTOPO_V3:batiment",
                        "Bâtiments BD TOPO V3"),
    "constructions":   ("BDTOPO_V3:construction_surfacique",
                        "Constructions surfaciques (murets, terrasses, enclos)"),
    "cimetieres":      ("BDTOPO_V3:cimetiere",
                        "Cimetières"),
    # ── Transport ─────────────────────────────────────────────────────────────
    "routes":          ("BDTOPO_V3:troncon_de_route",
                        "Tronçons de routes BD TOPO V3"),
    "chemins":         ("BDTOPO_V3:itineraire_autre",
                        "Chemins et itinéraires anciens"),
    # ── Relief / orographie ───────────────────────────────────────────────────
    "lignes_orog":     ("BDTOPO_V3:ligne_orographique",
                        "Lignes orographiques (talwegs, crêtes)"),
    "detail_orog":     ("BDTOPO_V3:detail_orographique",
                        "Détails orographiques (rochers, grottes)"),
    # ── Végétation / milieu ───────────────────────────────────────────────────
    "forets":          ("BDTOPO_V3:foret_publique",
                        "Forêts publiques"),
    "reserves":        ("BDTOPO_V3:parc_ou_reserve",
                        "Parcs et réserves naturelles"),
    # ── Toponymie / lieux ─────────────────────────────────────────────────────
    "lieux_dits":      ("BDTOPO_V3:lieu_dit_non_habite",
                        "Lieux-dits non habités (toponymie historique)"),
    # ── Admin ─────────────────────────────────────────────────────────────────
    "communes":        ("BDTOPO_V3:commune",
                        "Limites communales"),
    # ── Agriculture ───────────────────────────────────────────────────────────
    "rpg":             ("RPG.LATEST:parcelles_graphiques",
                        "Registre Parcellaire Graphique (cultures)"),
}

WFS_URL  = "https://data.geopf.fr/wfs/ows"
WFS_PAGE = 1000   # features par requête (limite serveur IGN)


def telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                    nom_zone, dossier_sortie, ecraser_telechargement=False):
    """Télécharge des features WFS IGN sur une bbox WGS84 → fichier .geojson.

    Pagination automatique (COUNT + STARTINDEX) jusqu'à épuisement.
    Retourne le Path du fichier créé, ou None en cas d'erreur.
    """

    dossier_sortie = Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)

    layer_short = typename.split(":")[-1].lower()
    sortie = dossier_sortie / f"{nom_zone}_ign_{layer_short}.geojson"
    sortie_gz = Path(str(sortie) + ".gz")

    # Vérifier .geojson.gz existant
    _existing = sortie_gz if sortie_gz.exists() else (sortie if sortie.exists() else None)
    if _existing and not ecraser_telechargement:
        print(f"  {_existing.name} -> déjà présent")
        return _existing
    if _existing and ecraser_telechargement:
        _existing.unlink()
        print(f"  {_existing.name} -> écrasement")

    print(f"  WFS {typename}...", flush=True)
    _log_req(f"{WFS_URL}?SERVICE=WFS&TYPENAMES={typename}&...", "WFS IGN")

    features      = []
    startindex    = 0
    total_attendu = None   # numberMatched capturé à la 1re page (ou via hits)
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
            _url_hits, headers={"User-Agent": "lidar2map/1.0"})
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

    while True:
        if _stop_event.is_set():
            if features:
                print(f"  WFS interrompu — {len(features)} features récupérées")
            return None

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
            url, headers={"User-Agent": "lidar2map/1.0"})

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
            if features:
                print(f"  Résultat partiel : {len(features)} features")
            else:
                return None
            break

        page = data.get("features", [])
        features.extend(page)

        # Fallback si hits a échoué : capturer numberMatched à la 1re page
        if total_attendu is None:
            _nm = data.get("numberMatched", data.get("totalFeatures"))
            if _nm is not None:
                try:
                    total_attendu = int(_nm)
                except (ValueError, TypeError):
                    pass

        elapsed = int(time.time() - t0)
        n_page  = startindex // WFS_PAGE + 1
        if total_attendu:
            pct = min(len(features) * 100 // total_attendu, 99)
            bar = ("█" * (pct // 5)).ljust(20)
            print(f"  WFS  [{bar}] {pct:3d}%  "
                  f"{len(features)}/{total_attendu}  "
                  f"page {n_page}  {_hms(elapsed)}", flush=True)
        else:
            print(f"  WFS  page {n_page}  {len(features)} features  {_hms(elapsed)}",
                  flush=True)

        if len(page) < WFS_PAGE:
            break
        startindex += WFS_PAGE
        time.sleep(0.2)

    geojson = {
        "type":     "FeatureCollection",
        "name":     layer_short,
        "crs":      {"type": "name",
                     "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    sortie_gz = _ecrire_geojson_gz(geojson, sortie)
    taille_ko = sortie_gz.stat().st_size // 1024
    print(f"\r  {sortie_gz.name} : {len(features)} features  ({taille_ko} Ko)"
          f"  {_hms(int(time.time()-t0))}          ")
    _creer_fichier(sortie_gz, intermediaire=False)
    return sortie_gz


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
    ≥ 100 000 km²  40 m       Région entière
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
    """

    geojson_path = Path(geojson_path)
    osm_xml_path = Path(osm_xml_path)

    # ── Lecture GeoJSON (.gz ou non) ─────────────────────────────────────────
    try:
        if geojson_path.suffix == ".gz":
            with gzip.open(geojson_path, "rt", encoding="utf-8") as f:
                gj = json.load(f)
        else:
            gj = json.loads(geojson_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  ERREUR lecture GeoJSON ({type(e).__name__}) : {e}")
        return False

    features = gj.get("features", [])
    if not features:
        print("  GeoJSON vide — rien à convertir.")
        return False

    # ── Construction OSM XML ─────────────────────────────────────────────────
    node_id  = -1
    way_id   = -1
    nodes    = []   # list of ET.Element
    ways     = []   # list of ET.Element

    _TS = "1970-01-01T00:00:00Z"   # timestamp factice — requis par osmosis 0.6

    def _new_node(lat, lon, tags=None):
        nonlocal node_id
        el = _ET.Element("node", id=str(node_id), lat=f"{lat:.7f}", lon=f"{lon:.7f}",
                          version="1", timestamp=_TS, visible="true")
        if tags:
            for k, v in tags.items():
                _ET.SubElement(el, "tag", k=k, v=str(v))
        nodes.append((node_id, el))
        nid = node_id
        node_id -= 1
        return nid

    def _new_way(nd_refs, tags):
        nonlocal way_id
        el = _ET.Element("way", id=str(way_id), version="1", timestamp=_TS, visible="true")
        for r in nd_refs:
            _ET.SubElement(el, "nd", ref=str(r))
        for k, v in tags.items():
            _ET.SubElement(el, "tag", k=k, v=str(v))
        ways.append(el)
        way_id -= 1

    _eps = epsilon if epsilon is not None else _IGN_SIMPLIFY_EPSILON

    def _process_ring(coords, osm_tags, close=True):
        """Crée les nœuds d'un anneau et le way correspondant."""
        coords = _douglas_peucker(coords, _eps)
        if len(coords) < 2:
            return
        nd_refs = [_new_node(c[1], c[0]) for c in coords]  # c[0]=lon c[1]=lat (ignore z)
        if close and nd_refs[0] != nd_refs[-1]:
            nd_refs.append(nd_refs[0])
        _new_way(nd_refs, osm_tags)

    def _process_linestring(coords, osm_tags):
        coords = _douglas_peucker(coords, _eps)
        if len(coords) < 2:
            return
        nd_refs = [_new_node(c[1], c[0]) for c in coords]  # c[0]=lon c[1]=lat (ignore z)
        _new_way(nd_refs, osm_tags)

    import traceback as _tb
    try:
      for feat in features:
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
            _new_node(coords[1], coords[0], osm_tags)

        elif gtype == "MultiPoint":
            for pt in coords:
                _new_node(pt[1], pt[0], osm_tags)

        elif gtype == "LineString":
            _process_linestring(coords, osm_tags)

        elif gtype == "MultiLineString":
            for line in coords:
                _process_linestring(line, osm_tags)

        elif gtype == "Polygon":
            if coords:
                _process_ring(coords[0], osm_tags, close=True)

        elif gtype == "MultiPolygon":
            for poly in coords:
                if poly:
                    _process_ring(poly[0], osm_tags, close=True)

        elif gtype == "GeometryCollection":
            for sub in geom.get("geometries", []):
                sub_coords = sub.get("coordinates", [])
                sub_type   = sub.get("type", "")
                if sub_type == "Point":
                    _new_node(sub_coords[1], sub_coords[0], osm_tags)
                elif sub_type == "LineString":
                    _process_linestring(sub_coords, osm_tags)
                elif sub_type == "MultiLineString":
                    for line in sub_coords: _process_linestring(line, osm_tags)
                elif sub_type == "Polygon" and sub_coords:
                    _process_ring(sub_coords[0], osm_tags, close=True)
                elif sub_type == "MultiPolygon":
                    for poly in sub_coords:
                        if poly: _process_ring(poly[0], osm_tags, close=True)

    except Exception as _e:
        print(f"\n  ERREUR dans geojson_ign_vers_osm_xml :")
        _tb.print_exc()
        return False

    # ── Écriture XML ─────────────────────────────────────────────────────────
    root = _ET.Element("osm", version="0.6", generator="lidar2map")
    # <bounds> requis par mapsforge mapwriter pour initialiser le tile store
    try:
        lon_min_b = min(c[0] for feat in features
                        for c in _coords_flat(feat.get("geometry") or {}))
        lon_max_b = max(c[0] for feat in features
                        for c in _coords_flat(feat.get("geometry") or {}))
        lat_min_b = min(c[1] for feat in features
                        for c in _coords_flat(feat.get("geometry") or {}))
        lat_max_b = max(c[1] for feat in features
                        for c in _coords_flat(feat.get("geometry") or {}))
        _ET.SubElement(root, "bounds",
                       minlat=f"{lat_min_b:.7f}", minlon=f"{lon_min_b:.7f}",
                       maxlat=f"{lat_max_b:.7f}", maxlon=f"{lon_max_b:.7f}")
    except Exception as _e:
        print(f"  ⚠ Calcul bounds échoué ({_e}) — bounds ignoré")
    for _, node_el in nodes:
        root.append(node_el)
    for way_el in ways:
        root.append(way_el)

    tree = _ET.ElementTree(root)
    # Pas d'indentation — osmosis n'en a pas besoin et _ET.indent()
    # est catastrophiquement lent sur les grands fichiers (8 min pour 6M éléments)
    try:
        tree.write(str(osm_xml_path), encoding="utf-8", xml_declaration=True)
    except TypeError:
        # Python < 3.9 : pas d'indent
        tree.write(str(osm_xml_path), encoding="utf-8", xml_declaration=True)

    nb_nodes = len(nodes)
    nb_ways  = len(ways)
    sz = osm_xml_path.stat().st_size / 1e6
    print(f"  OSM XML : {nb_nodes} nœuds, {nb_ways} ways → {osm_xml_path.name} ({sz:.1f} Mo)")
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
            print(f"  Carte IGN .map existante vide — régénération forcée.")
            chemin_map.unlink()
        else:
            print(f"  Carte IGN .map déjà présente : {chemin_map.name} — ignorée")
            return chemin_map

    if chemin_map.exists() and ecraser:
        chemin_map.unlink()
        print(f"  Carte IGN .map : écrasement {chemin_map.name}")

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
        _env_map["JAVA_OPTS"] = "-Xmx4g"

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
    r = subprocess.run(
        cmd_str if _shell else cmd,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        shell=_shell, env=_env_map,
    )

    if chemin_map.exists() and chemin_map.stat().st_size > 0:
        chemin_osm_xml.unlink(missing_ok=True)  # succès seulement
        taille_b = chemin_map.stat().st_size
        if taille_b < 1_000_000:
            print(f"  {chemin_map.name} : {taille_b // 1024} Ko  {_hms(time.time()-t0)}")
        else:
            print(f"  {chemin_map.name} : {taille_b / 1e6:.1f} Mo  {_hms(time.time()-t0)}")
        return chemin_map
    elif chemin_map.exists() and chemin_map.stat().st_size == 0:
        chemin_map.unlink(missing_ok=True)
        print(f"  ⚠ {chemin_map.name} créé mais vide — aucune feature reconnue par mapwriter.")
        print(f"  {chemin_osm_xml.name} conservé pour diagnostic.")
        return None
    else:
        print(f"  ERREUR osmosis mapfile-writer IGN (code {r.returncode})")
        if r.stderr:
            print(f"  {r.stderr.strip()[:2000]}")
        print(f"  {chemin_osm_xml.name} conservé — relancez osmosis après correction.")
        return None




# ============================================================
# TÉLÉCHARGEMENT BULK BD TOPO IGN (département entier)
# ============================================================
# Pour --zone-departement : l'API IGN fournit un GPKG complet par département
# (~1-2 Go, 1 seule requête HTTP). Beaucoup plus rapide que la pagination WFS
# (415 requêtes pour le Var).
# Pipeline : API discovery → GPKG streamé (cache) → ogr2ogr par couche → GeoJSON.gz
# ──────────────────────────────────────────────────────────────────────────────

BDTOPO_BULK_SEUIL = 50_000      # features — au-delà, basculer sur bulk
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
                                     headers={"User-Agent": "lidar2map/1.0"})
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
            # Trier par date (dernier segment du nom) pour prendre le plus récent
            noms.sort(reverse=True)
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

    # Versions par ordre décroissant (les plus récentes en premier)
    for version in ("3-5", "3-4", "3-3"):
        for date_str in candidates:
            nom = f"BDTOPO_{version}_TOUSTHEMES_GPKG_LAMB93_{zone}_{date_str}"
            url = f"{BDTOPO_DL_BASE}/{nom}/{nom}.7z"
            try:
                req_h = urllib.request.Request(url, method="HEAD",
                                               headers={"User-Agent": "lidar2map/1.0"})
                with urllib.request.urlopen(req_h, timeout=10):
                    print(f"  BD TOPO {zone} : {nom}", flush=True)
                    return url, nom
            except Exception:
                continue

    print(f"  ERREUR : archive BD TOPO GPKG introuvable pour {num_dep}")
    return None, None


def _telecharger_bdtopo_gpkg(num_dep, url, nom_ressource):
    """Télécharge et extrait le .7z BD TOPO, met le .gpkg en cache. Retourne Path ou None."""
    dep_padded = str(num_dep).zfill(3)
    cache_dir  = DOSSIER_TRAVAIL / "cache" / "bdtopo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = cache_dir / f"{nom_ressource}.gpkg"

    if gpkg_path.exists() and gpkg_path.stat().st_size > 10_000_000:
        print(f"  Cache GPKG : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} Mo) — réutilisé", flush=True)
        return gpkg_path

    # ── Vérifier que py7zr est disponible pour l'extraction ──────────────────
    try:
        import py7zr as _py7zr
    except ImportError:
        print("  Installation py7zr pour extraction .7z...", flush=True)
        r_pip = subprocess.run(
            [sys.executable, "-m", "pip", "install", "py7zr", "-q"],
            capture_output=True)
        if r_pip.returncode != 0:
            print("  ERREUR : py7zr non installable — impossible d'extraire le .7z IGN")
            return None
        import py7zr as _py7zr

    # ── Téléchargement du .7z ────────────────────────────────────────────────
    sz_path = cache_dir / f"{nom_ressource}.7z"
    print(f"  Téléchargement BD TOPO D{dep_padded} (~200-800 Mo)...", flush=True)
    _log_req(url, "IGN bulk GPKG")
    tmp = cache_dir / f"{nom_ressource}.7z.tmp"
    t0 = time.time()
    try:
        try:
            resp = _urlopen(url, timeout=120)
        except urllib.error.HTTPError as _e:
            print(f"  ERREUR HTTP {_e.code} — {url}")
            return None
        total = int(resp.headers.get("content-length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            while True:
                if _stop_event.is_set():
                    tmp.unlink(missing_ok=True); return None
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk); done += len(chunk)
                elapsed = int(time.time() - t0)
                if total:
                    pct = min(done * 100 // total, 99)
                    bar = ("█" * (pct // 5)).ljust(20)
                    print(f"  [{bar}] {pct:3d}%  "
                          f"{done/1e6:.0f}/{total/1e6:.0f} Mo  {_hms(elapsed)}",
                          flush=True)
                else:
                    print(f"  {done/1e6:.0f} Mo  {_hms(elapsed)}", flush=True)
        tmp.rename(sz_path)
        print(f"  ✓ {sz_path.name}  ({sz_path.stat().st_size/1e6:.0f} Mo)  "
              f"{_hms(int(time.time()-t0))}", flush=True)
    except (OSError, urllib.error.URLError) as e:
        tmp.unlink(missing_ok=True)
        print(f"  ERREUR téléchargement ({type(e).__name__}): {e}")
        return None

    # ── Extraction du .gpkg depuis le .7z ────────────────────────────────────
    print(f"  Extraction GPKG depuis {sz_path.name}...", flush=True)
    try:
        with _py7zr.SevenZipFile(sz_path, mode="r") as z:
            # Trouver le .gpkg dans l'archive
            gpkg_names = [n for n in z.getnames() if n.lower().endswith(".gpkg")]
            if not gpkg_names:
                print("  ERREUR : aucun .gpkg dans l'archive 7z")
                sz_path.unlink(missing_ok=True)
                return None
            # Extraire uniquement le .gpkg (peut être dans un sous-dossier)
            z.extract(targets=gpkg_names, path=cache_dir)

        # Trouver le fichier extrait (peut être dans un sous-dossier)
        extracted = None
        for p in cache_dir.rglob("*.gpkg"):
            if p.name not in (gpkg_path.name,):  # ignorer le cache déjà présent
                extracted = p
                break
        if not extracted:
            # Peut être déjà nommé correctement
            extracted = next(cache_dir.glob("**/*.gpkg"), None)

        if extracted and extracted != gpkg_path:
            extracted.rename(gpkg_path)
        elif not extracted:
            print("  ERREUR : .gpkg introuvable après extraction")
            return None

        sz_path.unlink(missing_ok=True)   # libérer l'espace du .7z
        print(f"  ✓ GPKG extrait : {gpkg_path.name} "
              f"({gpkg_path.stat().st_size/1e6:.0f} Mo)", flush=True)
        return gpkg_path

    except Exception as e:
        print(f"  ERREUR extraction .7z ({type(e).__name__}): {e}")
        sz_path.unlink(missing_ok=True)
        return None


def _extraire_couche_bdtopo(gpkg_path, layer_name, sortie_gz,
                             bbox_l93=None, ecraser=False):
    """
    Extrait une couche GPKG → GeoJSON.gz via ogr2ogr (reprojection WGS84).
    bbox_l93 : (xmin, ymin, xmax, ymax) pour clipper, ou None = département entier.
    """
    sortie_gz = Path(sortie_gz)
    if sortie_gz.exists() and not ecraser:
        print(f"  {sortie_gz.name} → déjà présent"); return sortie_gz
    if sortie_gz.exists() and ecraser:
        sortie_gz.unlink()

    ogr2ogr_exe = _trouver_ogr2ogr()
    if not ogr2ogr_exe:
        print("  ERREUR : ogr2ogr introuvable"); return None

    tmp_geojson = sortie_gz.parent / (sortie_gz.name.replace(".geojson.gz", "_tmp.geojson"))
    cmd = [str(ogr2ogr_exe), "-f", "GeoJSON", "-t_srs", "EPSG:4326",
           str(tmp_geojson), str(gpkg_path), layer_name]
    if bbox_l93:
        xmin, ymin, xmax, ymax = bbox_l93
        cmd += ["-spat", str(xmin), str(ymin), str(xmax), str(ymax),
                "-spat_srs", "EPSG:2154"]

    _log_req(cmd)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=_env_gdaldem())
    if r.returncode != 0:
        print(f"  ERREUR ogr2ogr {layer_name} (code {r.returncode})")
        if r.stderr: print(f"  {r.stderr.strip()[:500]}")
        tmp_geojson.unlink(missing_ok=True); return None

    if not tmp_geojson.exists() or tmp_geojson.stat().st_size == 0:
        print(f"  ⚠ {layer_name} : aucune feature")
        tmp_geojson.unlink(missing_ok=True); return None

    try:
        with open(tmp_geojson, encoding="utf-8") as f:
            gj = json.load(f)
        src_name = sortie_gz.name.replace(".geojson.gz", "")
        for feat in gj.get("features", []):
            feat.setdefault("properties", {}).setdefault("source", src_name)
        gz = _ecrire_geojson_gz(gj, sortie_gz.parent / sortie_gz.name.replace(".gz", ""))
        n = len(gj.get("features", []))
        print(f"  {gz.name} : {n} features  ({gz.stat().st_size//1024} Ko)  "
              f"{_hms(int(time.time()-t0))}", flush=True)
        _creer_fichier(gz, intermediaire=False)
        return gz
    finally:
        tmp_geojson.unlink(missing_ok=True)


def _trouver_ogr2ogr():
    """Retourne le Path d'ogr2ogr depuis le GDAL local du script ou le PATH."""
    gdal_bin = DOSSIER_TRAVAIL / "bin" / "gdal" / "bin"
    for nom in ("ogr2ogr.exe", "ogr2ogr"):
        p = gdal_bin / nom
        if p.exists(): return p
    import shutil as _shutil_ogr
    return _shutil_ogr.which("ogr2ogr")


def _telecharger_bdtopo_bulk(num_dep, couches_resolues, nom_zone,
                              dossier_sortie, bbox_l93=None, ecraser=False):
    """
    Pipeline bulk BD TOPO pour un département entier.
    Retourne list[Path] des GeoJSON.gz créés, ou None si échec critique.
    """
    print(f"  Bulk BD TOPO GPKG département {num_dep} "
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
                                      bbox_l93=bbox_l93, ecraser=ecraser)
        if res:
            sorties.append(res)
    return sorties


def main_wfs():
    """Point d'entrée mode --ignvecteur."""
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
                        version="lidar2map 1.0.0 (2026-03)")
    parser.add_argument("--ignvecteur", action="store_true")
    parser.add_argument("--couche", metavar="NOM", nargs="+", default=["cadastre"],
                        help="Couche(s) WFS à télécharger (défaut: cadastre). "
                             "Alias court ou typename complet. "
                             "Plusieurs couches séparées par des espaces.")

    # Zone — même logique que --ignraster
    zone = parser.add_mutually_exclusive_group()
    zone.add_argument("--zone-ville",       metavar="NOM")
    zone.add_argument("--zone-gps",         metavar="LAT,LON")
    zone.add_argument("--zone-bbox",        metavar="W,S,E,N")
    zone.add_argument("--zone-departement", metavar="NUM")
    parser.add_argument("--zone-rayon",  type=float, default=10.0, metavar="KM",
                        help="Rayon en km autour du point (défaut: 10)")
    parser.add_argument("--zone-nom",    metavar="NOM", default=None)
    parser.add_argument("--dossier",     metavar="CHEMIN", default=None,
                        help="Dossier de sortie (défaut: ./ign_vecteur/)")
    parser.add_argument("--workers",  type=int, default=4, metavar="N",
                        help="Connexions parallèles WFS (défaut: 4)")
    parser.add_argument("--telechargement-ecraser", action="store_true", dest="telechargement_ecraser",
                        help="Écraser les GeoJSON existants (re-téléchargement forcé)")
    parser.add_argument("--formats-fichier", nargs="+",
                        choices=["geojson","gz","map"],
                        default=["gz"], metavar="FMT",
                        help="Formats de sortie : geojson gz map (défaut: gz). "
                             "map génère une carte Mapsforge via osmosis.")
    parser.add_argument("--tuiles-ecraser", action="store_true", dest="tuiles_ecraser",
                        help="Écraser la carte .map existante")
    parser.add_argument("--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Epsilon de simplification Douglas-Peucker en mètres. "
                             "Sans ce paramètre, calculé automatiquement depuis la surface "
                             "(<200 km²→3 m, <1000→8 m, <15000→15 m, <100000→25 m, sinon→40 m).")
    parser.add_argument("--oui",         action="store_true",
                        help="Mode non-interactif")

    args = parser.parse_args()
    # Shim : --formats-fichier → args.no_gz
    _ff = getattr(args, "formats_fichier", ["gz"])
    args.no_gz = "geojson" in _ff and "gz" not in _ff

    # ── Résolution des couches ────────────────────────────────────────────────
    couches_resolues = []
    for c in args.couche:
        if c in COUCHES_WFS:
            couches_resolues.append(COUCHES_WFS[c])
        else:
            # typename complet passé directement
            couches_resolues.append((c, c))

    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    # ── Résolution de la zone → bbox WGS84 ───────────────────────────────────
    lon_min, lat_min, lon_max, lat_max, nom_zone = _resoudre_zone_wgs84(args)

    racine  = (Path(args.dossier).resolve() if args.dossier
               else Path(__file__).resolve().parent / "Projets" / nom_zone / "ign_vecteur")
    dossier = racine
    dossier.mkdir(parents=True, exist_ok=True)

    # ── Résumé ────────────────────────────────────────────────────────────────
    print("=" * 56)
    print("  Vecteur IGN WFS → GeoJSON")
    print("=" * 56)
    print(f"  Zone     : {nom_zone}")
    print(f"  BBox     : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")
    print(f"  Couche(s): {', '.join(c[1] for c in couches_resolues)}")
    print(f"  Sortie   : {dossier}")

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
        )
        if sorties_bulk is not None:
            sorties = sorties_bulk
        else:
            print("  Repli sur WFS pagination...")

    if not _bulk_tente or not sorties:
        # WFS standard (zone locale ou repli bulk échoué)
        def _dl(args_tuple):
            typename, desc = args_tuple
            print(f"\n  [{desc}]")
            return telecharger_wfs(typename, lon_min, lat_min, lon_max, lat_max,
                                   nom_zone, dossier,
                                   ecraser_telechargement=args.telechargement_ecraser)

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
        _geojson_fusionne = fusionner_geojson(sorties, sortie_fusion)

    # ── Génération Mapsforge .map si demandé ──────────────────────────────────
    _ff = getattr(args, "formats_fichier", ["gz"])
    if "map" in _ff and sorties:
        # Déterminer la source GeoJSON
        if len(sorties) > 1:
            _src_geojson = _geojson_fusionne  # None si fusion vide
        else:
            _src_geojson = sorties[0]

        if _src_geojson is None or not Path(_src_geojson).exists():
            print("\n  ⚠ Génération .map ignorée : aucun feature disponible.")
        else:
            # Epsilon : paramètre explicite ou calcul automatique depuis surface bbox
            if getattr(args, "simplification_vecteur", None):
                _eps_m = args.simplification_vecteur
                print(f"\n  Simplification vecteur : epsilon={_eps_m:.1f} m (forcé)")
            else:
                _surf = (lon_max - lon_min) * (lat_max - lat_min) * (111_000 ** 2) / 1e6
                _eps_m = _epsilon_depuis_surface_km2(_surf) * 111_000
                print(f"\n  Simplification vecteur : epsilon={_eps_m:.0f} m (auto, surface≈{_surf:.0f} km²)")
            _eps_deg = _eps_m / 111_000.0
            print("  Génération carte Mapsforge (.map) depuis GeoJSON IGN...")
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
    print(f"\n  Terminé en {_hms(elapsed)} — {len(sorties)}/{len(couches_resolues)} couches")
    for s in sorties:
        print(f"  → {s}")
    _historique_depuis_argv(elapsed, str(dossier))





# ============================================================
# EXPORT GEOJSON DEPUIS PBF OSM (ogr2ogr)
# ============================================================

def generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf, osm_tags=None, ecraser_tuiles=False):
    """
    Exporte le PBF OSM filtré par bbox en GeoJSON via ogr2ogr (GDAL).
    Produit un seul fichier fusionnant lignes + polygones + points.
    Chaque feature reçoit source='OSM'.
    Retourne le Path du .geojson, ou None en cas d'échec.
    """

    chemin_geojson = dossier_ville / f"{nom_zone}_osm.geojson.gz"
    # Compatibilité : vérifier aussi sans .gz
    _old = dossier_ville / f"{nom_zone}_osm.geojson"
    _existing_geo = chemin_geojson if chemin_geojson.exists() else (_old if _old.exists() else None)
    if _existing_geo and not ecraser_tuiles:
        print(f"  GeoJSON OSM deja present : {_existing_geo.name} — ignore")
        return _existing_geo
    if _existing_geo and ecraser_tuiles:
        _existing_geo.unlink()
        print(f"  GeoJSON OSM : écrasement {_existing_geo.name}")

    # ogr2ogr est inclus dans GDAL — téléchargement automatique si absent
    ogr2ogr = _trouver_outil_gdal("ogr2ogr")
    if not ogr2ogr:
        print("  AVERTISSEMENT : ogr2ogr introuvable — export GeoJSON OSM ignoré")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    t0 = time.time()
    print(f"  ogr2ogr → {chemin_geojson.name}...", flush=True)
    _env_ogr = _env_gdaldem() or os.environ.copy()

    # osmconf.ini — source : rasterio/gdal_data (toujours présent si rasterio installé)
    # Copié dans bin/gdal/bin/ avec [general] supprimé (incompatible GDAL < 3.10)
    _local_gdal_bin = DOSSIER_TRAVAIL / "bin" / "gdal" / "bin"
    _osmconf_local  = _local_gdal_bin / "osmconf.ini"

    if not _osmconf_local.exists():
        _osmconf_src = None
        # 1. Rasterio — source privilégiée, toujours adaptée
        try:
            import rasterio as _rio
            _c = Path(_rio.__file__).parent / "gdal_data" / "osmconf.ini"
            if _c.exists():
                _osmconf_src = _c
        except Exception:
            pass
        # 2. OSGeo4W / système en fallback
        if not _osmconf_src:
            for _c in [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/OSGeo4W/apps/gdal/share/gdal/osmconf.ini",
                Path(_env_ogr.get("GDAL_DATA", "")) / "osmconf.ini",
            ]:
                if _c.exists():
                    _osmconf_src = _c
                    break

        if _osmconf_src:
            _txt = _osmconf_src.read_text(encoding="utf-8", errors="replace")
            # Supprimer [general] — section inconnue pour GDAL < 3.10
            _txt = re.sub(r"\[general\][^\[]*", "", _txt).strip() + "\n"
            _osmconf_local.write_text(_txt, encoding="utf-8")
            print(f"  osmconf.ini → {_osmconf_local.parent} (depuis {_osmconf_src.parent.name})",
                  flush=True)
        else:
            # Fallback minimal intégré
            _osmconf_local.write_text(
                "[points]\nosm_id=yes\nattributes=name,barrier,highway,ref,place,man_made\nother_tags=yes\n\n"
                "[lines]\nosm_id=yes\nattributes=name,highway,waterway,aerialway,barrier,man_made,railway\nother_tags=yes\n\n"
                "[multipolygons]\nosm_id=yes\nattributes=name,type,aeroway,amenity,admin_level,boundary,building,landuse,leisure,natural,place,shop,tourism\nother_tags=yes\n\n"
                "[multilinestrings]\nosm_id=yes\nattributes=name,type\nother_tags=yes\n\n"
                "[other_relations]\nosm_id=yes\nattributes=name,type\nother_tags=yes\n",
                encoding="utf-8")
            print(f"  osmconf.ini minimal créé dans {_osmconf_local.parent}", flush=True)

    _env_ogr["GDAL_DATA"] = str(_osmconf_local.parent)

    # Clés thématiques depuis osm_tags (ex: ["highway=*","waterway=*"] → ["highway","waterway"])
    _cles = []
    if osm_tags:
        for _t in osm_tags:
            _k = _t.split("=")[0].strip()
            if _k and _k not in _cles:
                _cles.append(_k)
    if not _cles:
        _cles = ["highway", "waterway", "natural", "boundary",
                 "landuse", "building", "railway", "leisure"]

    _crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    features_total = []

    # ── Extraction sans filtre (3 couches géométriques) ──────────────────
    _toutes_feats = []
    for couche in ["lines", "multipolygons", "points"]:
        tmp = dossier_ville / f"_tmp_osm_{couche}.geojson"
        tmp.unlink(missing_ok=True)
        cmd = [
            ogr2ogr, "-f", "GeoJSON",
            str(tmp), str(osm_pbf), couche,
            "-spat", str(lon_min), str(lat_min), str(lon_max), str(lat_max),
            "-t_srs", "EPSG:4326",
            "-lco", "RFC7946=YES",
            "-oo", "TAGS_FORMAT=HSTORE",
        ]
        _log_req(cmd)
        r = subprocess.run(cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", env=_env_ogr)
        if r.returncode != 0:
            print(f"  ogr2ogr {couche} : code {r.returncode}"
                  + (f" — {r.stderr.strip()[:200]}" if r.stderr.strip() else ""), flush=True)
        if r.returncode == 0 and tmp.exists():
            try:
                data = json.loads(tmp.read_text(encoding="utf-8"))
                for feat in data.get("features", []):
                    feat.setdefault("properties", {})
                    feat["properties"]["source"] = "OSM"
                    _toutes_feats.append(feat)
                nb = len(data.get("features", []))
                if nb: print(f"  ogr2ogr {couche} : {nb} features", flush=True)
            except Exception as e_j:
                print(f"  ogr2ogr {couche} parse error : {e_j}")
            tmp.unlink(missing_ok=True)

    if not _toutes_feats:
        print("  Aucun feature OSM exporté")
        return None

    # ── Dispatch Python par clé thématique ───────────────────────────────
    def _val_tag(feat, key):
        props = feat.get("properties") or {}
        if props.get(key) not in (None, ""):
            return True
        ht = props.get("other_tags") or ""
        return bool(re.search('"' + key + '"', ht))

    _par_cle = {k: [] for k in _cles}
    for feat in _toutes_feats:
        for _k in _cles:
            if _val_tag(feat, _k):
                feat["properties"]["_cle"] = _k
                _par_cle[_k].append(feat)
                break

    for _k, _feats in _par_cle.items():
        if _feats:
            gc = {"type": "FeatureCollection", "name": f"{nom_zone}_osm_{_k}",
                  "crs": _crs, "features": _feats}
            gz = _ecrire_geojson_gz(gc, dossier_ville / f"{nom_zone}_osm_{_k}.geojson")
            print(f"  {gz.name} : {len(_feats)} features")
            features_total.extend(_feats)

    if not features_total:
        print("  Aucun feature OSM exporté")
        return None

    # ── Fichier fusionné toutes clés ──────────────────────────────────────
    geojson = {"type": "FeatureCollection", "name": f"{nom_zone}_osm",
               "crs": _crs, "features": features_total}
    chemin_gz = _ecrire_geojson_gz(geojson, dossier_ville / f"{nom_zone}_osm.geojson")
    taille = chemin_gz.stat().st_size // 1024
    print(f"  {chemin_gz.name} : {len(features_total)} features"
          f"  ({taille} Ko)  {_hms(int(time.time()-t0))}")
    return chemin_gz


# ============================================================
# PIPELINE FUSION GEOJSON
# ============================================================

def _ecrire_geojson_gz(data_dict, chemin):
    """
    Écrit un dict GeoJSON en .geojson.gz (compression gzip niveau 6).
    chemin peut se terminer par .geojson ou .geojson.gz — la sortie est toujours .geojson.gz.
    Retourne le Path du fichier créé.
    """
    p = Path(chemin)
    if not str(p).endswith(".gz"):
        p = Path(str(p) + ".gz")
    p.parent.mkdir(parents=True, exist_ok=True)
    data_bytes = json.dumps(data_dict, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
    with gzip.open(p, "wb", compresslevel=6) as f:
        f.write(data_bytes)
    _creer_fichier(p, intermediaire=False)
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
    Fusionne plusieurs GeoJSON en un seul FeatureCollection.
    Ajoute 'source' depuis le nom de fichier si absent.
    fichiers : liste de Path ou str
    sortie   : Path de sortie
    Retourne le Path du fichier créé, ou None.
    """

    features = []
    for f in fichiers:
        p = Path(f)
        # Accepter .geojson et .geojson.gz
        if not p.exists() and not str(p).endswith(".gz"):
            p_gz = Path(str(p) + ".gz")
            if p_gz.exists():
                p = p_gz
        if not p.exists():
            print(f"  AVERTISSEMENT : {p.name} introuvable — ignoré")
            continue
        try:
            data = _lire_geojson(p)
        except Exception as e:
            print(f"  AVERTISSEMENT : {p.name} illisible ({e}) — ignoré")
            continue
        source = p.stem.replace(".geojson", "")
        for feat in data.get("features", []):
            feat.setdefault("properties", {})
            feat["properties"].setdefault("source", source)
            features.append(feat)
        print(f"  {p.name} : {len(data.get('features', []))} features")

    if not features:
        print("  Aucun feature à fusionner")
        return None

    geojson = {
        "type": "FeatureCollection",
        "name": Path(sortie).stem.replace(".geojson", ""),
        "crs": {"type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    sortie_gz = _ecrire_geojson_gz(geojson, sortie)
    taille = sortie_gz.stat().st_size // 1024
    print(f"  → {sortie_gz.name} : {len(features)} features  ({taille} Ko)")
    _creer_fichier(sortie_gz, intermediaire=False)
    return sortie_gz


def main_fusionner():
    """Point d'entrée mode --fusionner."""
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
                        help="Fichiers GeoJSON à fusionner (glob accepté)")
    parser.add_argument("--sortie", metavar="FICHIER", default=None,
                        help="Fichier de sortie .geojson")
    parser.add_argument("--dossier", metavar="CHEMIN", default=None)
    parser.add_argument("--no-gz", action="store_true",
                        help="Sortie .geojson non compressé (défaut : .geojson.gz)")
    parser.add_argument("--formats-fichier", nargs="+", default=["gz"],
                        metavar="FMT", help="gz geojson map")
    parser.add_argument("--simplification-vecteur", type=float, default=None,
                        metavar="M", dest="simplification_vecteur",
                        help="Epsilon Douglas-Peucker en mètres (défaut: auto depuis surface).")
    parser.add_argument("--oui", action="store_true")

    args, _ = parser.parse_known_args()  # ignorer --zone-* et autres args globaux

    # Résoudre les globs éventuels
    import glob as _glob
    fichiers = []
    for pattern in args.source:
        matches = _glob.glob(pattern)
        if matches:
            fichiers.extend(sorted(matches))
        else:
            fichiers.append(pattern)  # sera signalé introuvable à la fusion

    if not fichiers:
        print("  ERREUR : aucun fichier source trouvé")
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

    result = fusionner_geojson(fichiers, sortie)
    if result:
        fmts = [f.lower() for f in args.formats_fichier]
        # Générer le .map Mapsforge si demandé
        if "map" in fmts:
            nom_zone = sortie.stem.split(".")[0]
            dossier_sortie = sortie.parent
            try:
                data = _lire_geojson(result)
                lons, lats = [], []
                for feat in data.get("features", []):
                    for coord in _coords_flat(feat.get("geometry", {})):
                        lons.append(coord[0]); lats.append(coord[1])
                if lons:
                    bbox = (min(lons), min(lats), max(lons), max(lats))
                else:
                    bbox = None
                if getattr(args, 'simplification_vecteur', None):
                    _eps_deg = args.simplification_vecteur / 111_000.0
                    print(f"  Simplification vecteur : epsilon={args.simplification_vecteur:.1f} m (forcé)")
                elif bbox:
                    _surf = (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]) * (111_000**2) / 1e6
                    _eps_deg = _epsilon_depuis_surface_km2(_surf)
                    print(f"  Simplification vecteur : epsilon={_eps_deg*111000:.0f} m (auto, surface≈{_surf:.0f} km²)")
                else:
                    _eps_deg = _IGN_SIMPLIFY_EPSILON
                generer_map_depuis_geojson_ign(result, dossier_sortie, nom_zone,
                                               bbox_wgs84=bbox, ecraser=True,
                                               epsilon=_eps_deg)
            except Exception as _e:
                print(f"  ERREUR génération .map : {_e}")
        print(f"\n  Terminé en {_hms(int(time.time()-t_debut))}")
    _historique_depuis_argv(int(time.time()-t_debut))






def _historique_depuis_argv(duree_s: int, dossier_resultat: str = ""):
    """
    Construit un cfg complet depuis sys.argv et sauvegarde dans l'historique.
    Les clés correspondent exactement à celles attendues par loadConfig() JS.
    """
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
        """Retourne tous les args après flag jusqu'au prochain -- ou fin."""
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

    cfg = {
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
    _sauver_historique(cfg, duree_s, dossier_resultat)
# ============================================================
# HISTORIQUE DES TRAITEMENTS
# ============================================================

_HISTORIQUE_PATH = DOSSIER_TRAVAIL / "historique.json"
_HISTORIQUE_MAX  = 50   # nombre max d'entrées conservées


def _sauver_historique(cfg: dict, duree_s: int, dossier_resultat: str = ""):
    """
    Ajoute une entrée à l'historique des traitements réussis.
    Conserve les _HISTORIQUE_MAX dernières entrées.
    """
    import datetime
    entree = {
        "date":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type":      cfg.get("type", ""),
        "nom":       cfg.get("nom", ""),
        "mode":      cfg.get("mode", ""),
        "dep":       cfg.get("dep", ""),
        "ville":     cfg.get("ville", ""),
        "gps":       cfg.get("gps", ""),
        "bbox":      cfg.get("bbox", ""),
        "dossier":   cfg.get("dossier", ""),
        "resultat":  dossier_resultat,
        "duree":     _hms(duree_s),
        "params":    cfg,   # cfg complet pour rappel exact
    }
    historique = []
    if _HISTORIQUE_PATH.exists():
        try:
            historique = json.loads(_HISTORIQUE_PATH.read_text(encoding="utf-8"))
        except Exception:
            historique = []
    historique.insert(0, entree)
    historique = historique[:_HISTORIQUE_MAX]
    try:
        _HISTORIQUE_PATH.write_text(
            json.dumps(historique, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"  Historique sauvegardé : {_HISTORIQUE_PATH}  ({len(historique)} entrées)", flush=True)
    except Exception as e:
        print(f"  Historique non sauvegardé : {e}", flush=True)


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
    try:
        import webview
    except ImportError:
        print("  PyWebView absent — installation automatique...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pywebview",
                 "--break-system-packages", "-q"], check=True)
        import webview

    # Supprimer les warnings internes pywebview (AccessibilityObject, COM, etc.)
    import logging as _logging
    for _name in ("pywebview", "pywebview.window", "pywebview.util",
                  "pywebview.platforms", "pywebview.js"):
        _lg = _logging.getLogger(_name)
        _lg.setLevel(_logging.CRITICAL)
        _lg.handlers.clear()
        _lg.propagate = False

    SCRIPT  = Path(__file__).resolve()

    # ── Table zooms pour la sélection de couche ───────────────────────────────
    _ZOOMS_GUI = {
        "scan25": (8, 16), "scan25tour": (8, 16), "scan100": (6, 14),
        "scanoaci": (6, 15), "planign": (6, 18), "etatmajor40": (6, 15),
        "etatmajor10": (8, 16), "pentes": (6, 14), "ortho": (10, 20),
        "cadastre": (12, 19), "ombrage": (6, 14),
    }

    # ── Données statiques exposées au formulaire ──────────────────────────────
    _COUCHES_PRIVEES = {"scan25", "scan25tour", "scan100", "scanoaci"}
    _COUCHES_DATA = [
        {"code": k,
         "label": f"{'⚠ [PRO] ' if k in _COUCHES_PRIVEES else ''}{k}  ({v[0]})",
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
        {"tag": "building=*",             "label": "Bâtiments"},
        {"tag": "historic=*",             "label": "Historique"},
    ]

    # ── Classe API exposée à JavaScript ──────────────────────────────────────
    class Api:
        def __init__(self):
            self._process   = None
            self._log_queue = queue.Queue()
            self._done      = False
            self._retcode   = None
            self.window     = None  # injecté par pywebview au démarrage

        # ── Données initiales ─────────────────────────────────────────────
        def get_init_data(self):
            return {
                "couches":    _COUCHES_DATA,
                "wfs":        _WFS_DATA,
                "osm_tags":   _OSM_TAGS_DATA,
                "apikey_def": APIKEY_DEFAUT,
                "historique": _lire_historique(),
            }

        def get_historique(self):
            """Retourne la liste historique — appelable depuis JS à tout moment."""
            return _lire_historique()

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
            cmd = [sys.executable, str(SCRIPT)]
            t = cfg.get("type", "lidar")

            # Zone
            # Zone (pas pour fusion)
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

            # ── LiDAR ────────────────────────────────────────────────────
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

            # ── IGN Raster ───────────────────────────────────────────────
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

            # ── OSM ──────────────────────────────────────────────────────
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

            # ── IGN Vectoriel ─────────────────────────────────────────────
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
                if not fmts: fmts = ["gz"]  # défaut si rien coché
                if cfg.get("tuiles_v"): fmts.append("map")
                cmd += ["--formats-fichier"] + fmts
                if cfg.get("tuiles_v") and cfg.get("ecraser_tuil_v"):
                    cmd.append("--tuiles-ecraser")
                if cfg.get("tuiles_v") and cfg.get("simplif_v"):
                    cmd += ["--simplification-vecteur", str(cfg["simplif_v"])]

            # ── Fusion ────────────────────────────────────────────────────
            elif t == "fusion":
                cmd.append("--fusionner")
                fichiers = cfg.get("fusion_fichiers", [])
                if fichiers: cmd += ["--source"] + fichiers
                nom = cfg.get("nom", "fusion") or "fusion"
                # Extension du GeoJSON intermédiaire
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

            # ── Découpage raster (à posteriori) ──────────────────────────
            elif t == "decoupe":
                cmd.append("--decouper")
                src_d = cfg.get("source_decoupe", "")
                if src_d: cmd += ["--source", src_d]
                if cfg.get("cols_decoupe", 0) > 0 and cfg.get("rows_decoupe", 0) > 0:
                    cmd += ["--cols", str(cfg["cols_decoupe"]),
                            "--rows", str(cfg["rows_decoupe"])]
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

        # ── Lancement ────────────────────────────────────────────────────
        def launch(self, cfg):
            if self._process and self._process.poll() is None:
                return {"error": "Un processus est déjà en cours."}
            cmd = self._build_cmd(cfg)
            self._done = False
            self._retcode = None
            self._t_launch = time.time()
            self._cfg_launch = cfg
            # Calculer le dossier résultat attendu
            t    = cfg.get("type", "lidar")
            nom  = cfg.get("nom", "")
            base = Path(cfg["dossier"]) if cfg.get("dossier") else DOSSIER_TRAVAIL / "Projets"
            _type_dir = {"lidar":"ign_lidar","scan":"ign_raster","osm":"osm_vecteur",
                         "vecteur":"ign_vecteur","fusion":"fusion","decoupe":""}
            if t == "decoupe" and cfg.get("source_decoupe"):
                self._result_dir = str(Path(cfg["source_decoupe"]).parent)
            else:
                self._result_dir = str(base / nom / _type_dir.get(t, t)) if nom else str(base)
            while not self._log_queue.empty():
                try: self._log_queue.get_nowait()
                except queue.Empty: break

            def run():
                self._log_queue.put({"line": "$ " + " ".join(str(c) for c in cmd) + "\n\n",
                                     "tag": "dim"})
                try:
                    env = os.environ.copy(); env["PYTHONUNBUFFERED"] = "1"
                    # Créer un nouveau groupe de processus pour pouvoir tuer toute la hiérarchie
                    if WINDOWS:
                        self._process = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            bufsize=0, env=env,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                    else:
                        self._process = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            bufsize=0, env=env,
                            start_new_session=True)
                    buf = ""
                    pct_re = re.compile(r"(\d+)%")
                    for chunk in iter(lambda: self._process.stdout.read(64), b""):
                        for ch in chunk.decode("utf-8", errors="replace"):
                            if ch == "\r":
                                m = pct_re.search(buf)
                                pct = int(m.group(1)) if m else -1
                                if buf.strip():
                                    self._log_queue.put({"pct": pct, "label": buf.strip()})
                                buf = ""
                            elif ch == "\n":
                                if buf.strip():
                                    tag = "err" if any(
                                        w in buf.upper()
                                        for w in ["ERREUR","ERROR","TRACEBACK"]
                                    ) else "ok"
                                    self._log_queue.put({"line": buf + "\n", "tag": tag})
                                buf = ""
                            else:
                                buf += ch
                    self._process.wait()
                    self._retcode = self._process.returncode
                    sym = "✓" if self._retcode == 0 else "✗"
                    self._log_queue.put({"line": f"\n{sym} Terminé (code {self._retcode})\n",
                                         "tag": "ok" if self._retcode == 0 else "err"})
                    if self._retcode == 0:
                        # Marquer la durée — sauvegarde historique faite dans poll_log
                        self._duree_run = int(time.time() - getattr(self, "_t_launch", time.time()))
                except Exception as e:
                    self._log_queue.put({"line": f"\nErreur : {e}\n", "tag": "err"})
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

        def poll_log(self):
            items = []
            try:
                while True:
                    items.append(self._log_queue.get_nowait())
            except queue.Empty:
                pass

            # Sauvegarder l'historique une seule fois, dans le contexte poll_log (thread-safe)
            if self._done and self._retcode == 0 and not getattr(self, "_hist_saved", False):
                self._hist_saved = True
                try:
                    _duree = getattr(self, "_duree_run", 0)
                    _sauver_historique(
                        getattr(self, "_cfg_launch", {}),
                        _duree,
                        getattr(self, "_result_dir", ""),
                    )
                    items.append({"line": f"  Historique sauvegardé : {_HISTORIQUE_PATH}\n",
                                  "tag": "ok"})
                except Exception as _he:
                    items.append({"line": f"  ERREUR historique : {_he}\n", "tag": "err"})

            result_dir = getattr(self, "_result_dir", None) if (self._done and self._retcode == 0) else None
            return {"items": items, "done": self._done, "code": self._retcode,
                    "result_dir": result_dir}

    # ┌─────────────────────────────────────────────────────────────────────┐
    # │  HTML / CSS / JS  — éditer ici avec un éditeur supportant le HTML  │
    # │  Sections : <style> L+8  │  <body> L+120  │  <script> L+518       │
    # └─────────────────────────────────────────────────────────────────────┘
    HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>lidar2map</title>
<!-- ═══════════════════════════════ CSS ════════════════════════════════════ -->
<style>
:root{--bg:#12121f;--bg2:#1a1a30;--bg3:#1f1f3a;--bd:#2a2a50;
  --ac:#7070cc;--ac2:#e07060;--fg:#e0e0e0;--dim:#7070aa;
  --green:#60cc80;--red:#cc6060;--fnt:"Segoe UI",system-ui,sans-serif;
  /* Couleurs par type de carte */
  --lidar:  #5b8a6e;  /* vert forêt */
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
header{background:var(--bg3);border-bottom:1px solid var(--bd);
  padding:8px 16px;display:flex;align-items:center;gap:12px}
header h1{font-size:14px;font-weight:600;color:#fff;letter-spacing:.5px}
header .ver{font-size:10px;color:var(--dim)}
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
/* Bandeaux Découpage raster */
#sec-decoupe .section-hd{background:var(--decoupe)}
#sec-decoupe .section{background:rgba(138,104,112,.14)!important;border-color:rgba(138,104,112,.35)!important}
/* listbox fusion */
#fusion-list{background:var(--bg3);border:1px solid var(--bd);border-radius:4px;
  min-height:60px;max-height:100px;overflow-y:auto;padding:4px;font-size:11px}
#fusion-list div{padding:2px 4px;border-radius:3px;cursor:pointer}
#fusion-list div:hover{background:var(--bd)}
#fusion-list div.sel{background:var(--ac);color:#fff}
</style>
</head>
<!-- ═══════════════════════════════ HTML ═══════════════════════════════════ -->
<body>
<header>
  <h1>⛰ lidar2map</h1>
  <span class="ver">Prospection LiDAR archéologique</span>
</header>
<div id="main">
<div id="btn-bar">
 <button class="btn btn-run" id="btn-run" onclick="lancer()">▶ Lancer</button>
 <button class="btn btn-stop" id="btn-stop" onclick="arreter()" disabled>■ Arrêter</button>
 <button class="btn" id="btn-hist" onclick="toggleHistorique()"
         style="background:var(--bg3);border:1px solid var(--bd);margin-left:12px">⏱ Historique</button>
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
      <input type="text" id="f-dossier" placeholder="(auto)" style="flex:4">
      <button class="btn btn-sm" onclick="pickDir('f-dossier')">…</button>
     </div>
   </div>
  </div>

  <!-- Zone géographique -->
  <div class="section sec-zone">
   <div class="section-hd">Zone géographique</div>
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
      <label for="m-dep">Département</label>
     </div>
    </div>
    <div class="row z-zone" id="z-ville"><label>Ville</label>
     <input type="text" id="f-ville" placeholder="ex: gareoult" style="max-width:180px">
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
      <label>Département(s)</label>
      <input type="text" id="f-dep" placeholder="83" style="width:220px;flex:none"
             title="Un ou plusieurs départements&#10;Exemples : 83 | 83,06,13 | 1-10 | 1-3,75,83 | 2A | 971">
     </div>
     <div class="hint" style="margin-top:3px;margin-left:0">
      Syntaxe : <code>83</code> &nbsp;·&nbsp;
      <code>83,06,13</code> &nbsp;·&nbsp;
      <code>1-10</code> &nbsp;·&nbsp;
      <code>1-3,75,83</code> &nbsp;·&nbsp;
      DOM : <code>2A</code> <code>971</code>
      &nbsp;—&nbsp; Multi-département : un fichier par département
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
     <label for="t-lidar">IGN LiDAR MNT Raster</label>
     <input type="radio" name="type" id="t-scan"    value="scan">
     <label for="t-scan">IGN Raster</label>
     <input type="radio" name="type" id="t-vecteur" value="vecteur">
     <label for="t-vecteur">IGN Vectoriel</label>
     <input type="radio" name="type" id="t-osm"     value="osm">
     <label for="t-osm">OSM Vectoriel</label>
     <input type="radio" name="type" id="t-fusion"  value="fusion">
     <label for="t-fusion">Fusion Vectoriel</label>
     <input type="radio" name="type" id="t-decoupe" value="decoupe">
     <label for="t-decoupe">Découpage raster</label>
    </div>
   </div>
  </div>

  <!-- ═══ LIDAR ═══ -->
  <div id="sec-lidar">
   <div class="section">
    <div class="section-hd">
     <label>0 — Découpage à priori (grandes zones)</label>
    </div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-priori-cols" value="1" min="1" max="50" class="inp-short" title="Colonnes Est-Ouest">
      <span class="hint" style="margin:0 4px">cols ×</span>
      <input type="number" id="f-priori-rows" value="1" min="1" max="50" class="inp-short" title="Lignes Nord-Sud">
      <span class="hint" style="margin:0 4px">lignes</span>
      <span class="hint" style="margin:0 6px;color:var(--dim)">ou rayon</span>
      <input type="number" id="f-rayon-priori-l" value="0" min="0" step="10" class="inp-short" title="Rayon km par morceau (alternative à la grille)">
      <span class="hint" style="margin-left:4px">km</span>
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-nettoyage"> Nettoyage intermédiaires</label>
     </div>
     <div class="row" style="color:var(--dim);font-size:11px;padding-top:0">
      <span style="padding-left:calc(var(--label-w) + 4px)">1×1 = pas de découpage — reprise automatique via manifeste.json</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel" checked> 1 — Télécharger les dalles LiDAR HD IGN</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tel">
     <div class="row">
      <label>Workers :</label>
      <input type="number" id="f-workers-l" value="8" min="1" max="32" class="inp-short">
      <label style="min-width:auto"><input type="checkbox" id="f-comp"> Compresser</label>
      <label style="min-width:auto;margin-left:12px">Cache externe :</label>
      <input type="text" id="f-dossier-dalles" placeholder="(cache auto)">
      <button class="btn btn-sm" onclick="pickDir('f-dossier-dalles')">…</button>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-no-omb" checked> 2 — Calculer les ombrages archéologiques</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-omb">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-omb">
     <div class="row">
      <div class="cb-group">
       <label><input type="checkbox" name="omb" value="multi" checked> multi</label>
       <label><input type="checkbox" name="omb" value="slope"> slope</label>
       <label><input type="checkbox" name="omb" value="315"> 315°</label>
       <label><input type="checkbox" name="omb" value="045"> 045°</label>
       <label><input type="checkbox" name="omb" value="135"> 135°</label>
       <label><input type="checkbox" name="omb" value="225"> 225°</label>
       <label><input type="checkbox" name="omb" value="svf"> SVF</label>
       <label><input type="checkbox" name="omb" value="svf100"> SVF100</label>
       <label><input type="checkbox" name="omb" value="lrm"> LRM</label>
       <label><input type="checkbox" name="omb" value="rrim"> RRIM</label>
      </div>
      <span style="margin-left:12px;color:var(--dim)">☀</span>
      <input type="number" id="f-elevation" value="25" min="5" max="60" class="inp-short">
      <span style="color:var(--dim)">°</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-mbtiles-l" checked> 3 — Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-mbt">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body hidden" id="body-mbt">
     <div class="row">
      <label>Zoom :</label>
      <input type="number" id="f-zoom-min-l" value="8" min="8" max="20" class="inp-short">
      <span style="color:var(--dim)">–</span>
      <input type="number" id="f-zoom-max-l" value="18" min="8" max="20" class="inp-short">
      <span style="margin-left:12px;color:var(--dim)">Format de l'image :</span>
      <div class="seg" style="margin-left:6px">
       <input type="radio" name="fmt-l" id="fl-auto" value="auto" checked><label for="fl-auto">Auto</label>
       <input type="radio" name="fmt-l" id="fl-jpeg" value="jpeg"><label for="fl-jpeg">JPEG</label>
       <input type="radio" name="fmt-l" id="fl-png"  value="png"><label for="fl-png">PNG</label>
      </div>
      <span style="margin-left:8px;color:var(--dim)">Qualité Jpeg :</span>
      <input type="number" id="f-qualite-l" value="85" min="50" max="95" class="inp-short" style="margin-left:4px">
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

  <!-- ═══ SCAN ═══ -->
  <div id="sec-scan" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label>0 — Découpage à priori (grandes zones)</label>
    </div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-priori-cols-s" value="1" min="1" max="50" class="inp-short" title="Colonnes Est-Ouest">
      <span class="hint" style="margin:0 4px">cols ×</span>
      <input type="number" id="f-priori-rows-s" value="1" min="1" max="50" class="inp-short" title="Lignes Nord-Sud">
      <span class="hint" style="margin:0 4px">lignes</span>
      <span class="hint" style="margin:0 6px;color:var(--dim)">ou rayon</span>
      <input type="number" id="f-rayon-priori-s" value="0" min="0" step="10" class="inp-short" title="Rayon km par morceau">
      <span class="hint" style="margin-left:4px">km</span>
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-nettoyage-s"> Nettoyage intermédiaires</label>
     </div>
     <div class="row" style="color:var(--dim);font-size:11px;padding-top:0">
      <span style="padding-left:calc(var(--label-w) + 4px)">1×1 = pas de découpage — reprise automatique via manifeste.json</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">Couche IGN</div>
    <div class="section-body">
     <div class="row">
      <label>Couche :</label>
      <select id="f-couche"></select>
      <span id="apikey-group" style="display:none;align-items:center;gap:4px;margin-left:8px"><span style="color:var(--dim)">Clé API :</span><input type="text" id="f-apikey" style="margin-left:4px;max-width:140px" placeholder="clé pro IGN"></span>
     </div>
     <div id="scan-restriction-warning" class="hidden" style="margin-top:4px;padding:6px 8px;background:rgba(204,96,96,.15);border:1px solid rgba(204,96,96,.4);border-radius:4px;font-size:11px;color:#e07070">
      ⚠ Cette couche est réservée aux <strong>professionnels</strong> (CGU IGN).<br>
      Une clé API est requise — compte <a href="https://cartes.gouv.fr" target="_blank" style="color:#e07070">cartes.gouv.fr</a> avec SIRET.<br>
      Les particuliers doivent utiliser <strong>planign</strong> ou <strong>ortho</strong> (pas de clé requise).
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-s" checked> 1 — Télécharger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-s">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tel-s">
     <div class="row"><label>Workers :</label>
      <input type="number" id="f-workers-s" value="8" min="1" max="32" class="inp-short"></div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-s" checked> 2 — Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-s">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tuil-s">
     <div class="row">
      <label>Zoom :</label>
      <input type="number" id="f-zoom-min-s" value="12" min="1" max="20" class="inp-short">
      <span style="color:var(--dim)">–</span>
      <input type="number" id="f-zoom-max-s" value="16" min="1" max="20" class="inp-short">
      <span style="margin-left:12px;color:var(--dim)">Format de l'image :</span>
      <div class="seg" style="margin-left:6px">
       <input type="radio" name="fmt-s" id="fs-auto" value="auto" checked><label for="fs-auto">Auto</label>
       <input type="radio" name="fmt-s" id="fs-jpeg" value="jpeg"><label for="fs-jpeg">JPEG</label>
       <input type="radio" name="fmt-s" id="fs-png"  value="png"><label for="fs-png">PNG</label>
      </div>
      <span style="margin-left:8px;color:var(--dim)">Qualité Jpeg :</span>
      <input type="number" id="f-qualite-s" value="85" min="50" max="95" class="inp-short" style="margin-left:4px">
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

  <!-- ═══ OSM ═══ -->
  <div id="sec-osm" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-osm" checked> 1 — Télécharger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-osm">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tel-osm">
     <div class="cb-group" id="osm-tag-checks"></div>
     <div class="row" style="margin-top:4px">
      <label>Workers :</label>
      <input type="number" id="f-workers-osm" value="4" min="1" max="16" class="inp-short">
      <span class="hint" style="margin-left:6px">(parallélisme téléchargement PBF)</span>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-osm" checked> 2 — Calculer les tuiles</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-osm">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tuil-osm">
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-map" checked> Mapsforge (.map)</label>
       <label><input type="checkbox" id="f-osm-geojson" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-osm-geojson-raw"> .geojson (non compressé)</label>
      </div>
     </div>
    </div>
   </div>
  </div>

  <!-- ═══ VECTEUR IGN ═══ -->
  <div id="sec-vecteur" class="hidden">
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tel-v" checked> 1 — Télécharger</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tel-v">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body" id="body-tel-v">
     <div class="cb-group" id="wfs-checks"></div>
     <div class="row" style="margin-top:4px">
      <label>Workers :</label>
      <input type="number" id="f-workers-v" value="4" min="1" max="16" class="inp-short">
      <span class="hint" style="margin-left:6px">(max 4 recommandé)</span>
     </div>
     <div class="row">
      <label>Format du fichier :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-fusion-gz" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-fusion-gz-raw"> .geojson (non compressé)</label>
      </div>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">
     <label><input type="checkbox" id="f-tuiles-v"> 2 — Générer carte Mapsforge (.map)</label>
     <label style="margin-left:auto"><input type="checkbox" id="f-ecraser-tuil-v">  Écraser le fichier résultat</label>
    </div>
    <div class="section-body hidden" id="body-map-v">
     <span class="hint">GeoJSON IGN → OSM XML → osmosis+mapwriter → .map</span>
     <div class="row" id="row-simplif-v" class="hidden" style="margin-top:6px">
      <label>Simplification vecteur</label>
      <input type="number" id="f-simplif-v" min="1" max="200" step="1" placeholder="auto"
             style="width:80px" title="Epsilon Douglas-Peucker en mètres. Vide = auto depuis surface.">
      <span class="hint" style="margin-left:6px">m  (vide = auto : 3 m local → 40 m région)</span>
     </div>
    </div>
   </div>
  </div>

  <!-- ═══ FUSION ═══ -->
  <div id="sec-fusion" class="hidden">
   <div class="section">
    <div class="section-hd">Fichiers GeoJSON à fusionner</div>
    <div class="section-body">
     <div id="fusion-list"></div>
     <div class="row" style="margin-top:4px">
      <button class="btn btn-sm" onclick="fusionAjouter()">＋ Ajouter…</button>
      <button class="btn btn-sm" onclick="fusionSupprimer()">－ Supprimer</button>
      <button class="btn btn-sm" onclick="fusionVider()">✕ Vider</button>
      <span class="hint" style="margin-left:8px">Sélection étendue (Shift/Ctrl)</span>
     </div>
     <div class="row">
      <label>Format :</label>
      <div class="cb-group">
       <label><input type="checkbox" id="f-fusion-gz2" checked> .geojson.gz</label>
       <label><input type="checkbox" id="f-fusion-gz2-raw"> .geojson (non compressé)</label>
       <label><input type="checkbox" id="f-fusion-map"> Mapsforge (.map)</label>
      </div>
     </div>
     <div class="row" id="row-simplif-fusion" class="hidden" style="margin-top:6px">
      <label>Simplification vecteur</label>
      <input type="number" id="f-simplif-fusion" min="1" max="200" step="1" placeholder="auto"
             style="width:80px" title="Epsilon Douglas-Peucker en mètres. Vide = auto depuis surface.">
      <span class="hint" style="margin-left:6px">m  (vide = auto)</span>
     </div>
    </div>
   </div>
  </div>


  <!-- ═══ DÉCOUPAGE RASTER ═══ -->
  <div id="sec-decoupe" class="hidden">
   <div class="section">
    <div class="section-hd">Fichier source</div>
    <div class="section-body">
     <div class="row">
      <label>Source MBTiles</label>
      <input type="text" id="f-source-decoupe" placeholder="chemin vers le fichier .mbtiles">
      <button class="btn btn-sm" onclick="pickFile('f-source-decoupe',false,[])">…</button>
     </div>
    </div>
   </div>
   <div class="section">
    <div class="section-hd">Découpage</div>
    <div class="section-body">
     <div class="row">
      <label>Grille :</label>
      <input type="number" id="f-cols-decoupe" value="1" min="1" max="50" class="inp-short" title="Colonnes (Est-Ouest)">
      <span class="hint" style="margin:0 4px">cols ×</span>
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
      <label style="min-width:auto;margin-left:16px"><input type="checkbox" id="f-ecraser-d">  Écraser</label>
     </div>
    </div>
   </div>
  </div>




 </div><!-- /form-inner -->
</div><!-- /main -->
<!-- ═══ PANNEAU HISTORIQUE ═══ -->
<div id="panneau-hist" class="hidden"
     style="position:fixed;top:0;right:0;width:420px;height:100%;background:var(--bg2);
            border-left:1px solid var(--bd);overflow-y:auto;z-index:100;padding:12px;box-sizing:border-box">
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
  <strong>Historique des traitements</strong>
  <button class="btn" onclick="toggleHistorique()"
          style="background:transparent;border:none;font-size:16px;cursor:pointer">✕</button>
 </div>
 <div id="hist-list"></div>
<!-- panneau-hist end --
</div>

<!-- ═══════════════════════════════ JS ═════════════════════════════════════ -->
<script>
// ── État ─────────────────────────────────────────────────────────────────────
let fusionFiles = [];
let fusionSel = -1;
let polling = null;
let _initialized = false;

// ── Init ─────────────────────────────────────────────────────────────────────
// bindAll() est appelé immédiatement au DOMContentLoaded pour l'état initial
// (sections visibles/cachées selon checkboxes). L'init async (couches, config)
// est lancée séparément dès que pywebview.api est disponible.
document.addEventListener('DOMContentLoaded', () => {
  bindAll();
  waitForApi();
});

function waitForApi(tries=0) {
  if (window.pywebview && window.pywebview.api &&
      typeof window.pywebview.api.get_init_data === 'function') {
    initAsync();
  } else if (tries < 200) {
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
    buildCouches(d.couches);
    buildWfsCouches(d.wfs);
    buildOsmTags(d.osm_tags);
    document.getElementById('f-apikey').value = d.apikey_def || '';
    // Charger l'historique via appel dédié
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

let _historique = [];

function buildHistorique(hist) {
  _historique = hist || [];
  const list = document.getElementById('hist-list');
  if (!list) return;
  if (!_historique.length) {
    list.innerHTML = '<div style="color:var(--dim);font-size:12px">Aucun traitement enregistré.</div>';
    return;
  }
  const LABELS = {lidar:'LiDAR',scan:'IGN Raster',osm:'OSM Vectoriel',
                  vecteur:'IGN Vectoriel',fusion:'Fusion',decoupe:'Découpage'};
  list.innerHTML = _historique.map((e, i) => {
    const zone = e.dep  ? `Dep ${e.dep}`  :
                 e.ville ? e.ville         :
                 e.bbox  ? 'BBox'          :
                 e.gps   ? 'GPS'           : '';
    return `<div style="border:1px solid var(--bd);border-radius:4px;padding:8px;
                        margin-bottom:6px;cursor:pointer;font-size:12px"
                 onclick="rappelHistorique(${i})">
      <div style="display:flex;justify-content:space-between">
        <strong>${LABELS[e.type]||e.type} — ${e.nom||'?'}</strong>
        <span style="color:var(--dim)">${e.date}</span>
      </div>
      <div style="color:var(--dim);margin-top:3px">${zone}${zone?' · ':''}${e.duree}</div>
    </div>`;
  }).join('');
}

function toggleHistorique() {
  const p = document.getElementById('panneau-hist');
  if (p) p.classList.toggle('hidden');
}

function rappelHistorique(i) {
  const e = _historique[i];
  if (!e || !e.params) return;
  loadConfig(e.params);
  toggleHistorique();
  document.getElementById('footer-status').textContent =
    `Paramètres rappelés : ${e.nom||''} (${e.date})`;
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

// ── Bindings dynamiques ───────────────────────────────────────────────────────
function bindAll() {
  // Mode zone — appliquer l'état initial immédiatement
  document.querySelectorAll('input[name=mode]').forEach(r => {
    r.addEventListener('change', () => {
      ['ville','gps','bbox','dep'].forEach(m => {
        document.getElementById('z-'+m).classList.toggle('hidden', r.value !== m);
      });
    });
  });
  const curMode = document.querySelector('input[name=mode]:checked')?.value || 'ville';
  ['ville','gps','bbox','dep'].forEach(m => {
    document.getElementById('z-'+m).classList.toggle('hidden', m !== curMode);
  });
  // Type carte — appliquer l'état initial immédiatement
  document.querySelectorAll('input[name=type]').forEach(r => {
    r.addEventListener('change', () => {
      ['lidar','scan','osm','vecteur','fusion','decoupe'].forEach(t => {
        document.getElementById('sec-'+t).classList.toggle('hidden', r.value !== t);
      });
      document.body.className = 'type-' + r.value;
      const secZone = document.querySelector('.sec-zone');
      if (secZone) secZone.classList.toggle('hidden', r.value === 'decoupe');
    });
  });
  // Appliquer l'état initial
  const curType = document.querySelector('input[name=type]:checked')?.value || 'lidar';
  ['lidar','scan','osm','vecteur','fusion','decoupe'].forEach(t => {
    document.getElementById('sec-'+t).classList.toggle('hidden', t !== curType);
  });
  document.body.className = 'type-' + curType;
  const _secZoneInit = document.querySelector('.sec-zone');
  if (_secZoneInit) _secZoneInit.classList.toggle('hidden', curType === 'decoupe');
  // Toggle sections avec checkbox
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
  toggles.forEach(([cbId, bodyId]) => {
    const cb = document.getElementById(cbId);
    const body = document.getElementById(bodyId);
    if (!cb || !body) return;
    const upd = () => body.classList.toggle('hidden', !cb.checked);
    cb.addEventListener('change', upd);
    upd();
  });
}

// ── Config ────────────────────────────────────────────────────────────────────
function getConfig() {
  const g = id => document.getElementById(id);
  const mode = document.querySelector('input[name=mode]:checked')?.value || 'ville';
  const type = document.querySelector('input[name=type]:checked')?.value || 'lidar';
  const rayonId = mode === 'gps' ? 'f-rayon-gps' : 'f-rayon';

  const cfg = {
    type, mode,
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
    ecraser_omb:   g('f-ecraser-omb')?.checked,
    mbtiles_l:     g('f-mbtiles-l')?.checked && g('f-mbtiles')?.checked,
    rmap:          g('f-mbtiles-l')?.checked && g('f-rmap')?.checked,
    sqlitedb:      g('f-mbtiles-l')?.checked && g('f-sqlitedb')?.checked,
    zoom_min_l:    parseInt(g('f-zoom-min-l')?.value) || 8,
    zoom_max_l:    parseInt(g('f-zoom-max-l')?.value) || 18,
    fmt_l:         document.querySelector('input[name=fmt-l]:checked')?.value || 'auto',
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
    fmt_s:         document.querySelector('input[name=fmt-s]:checked')?.value || 'auto',
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
    // Découpage raster (à posteriori)
    source_decoupe:  g('f-source-decoupe')?.value.trim(),
    cols_decoupe:    parseInt(g('f-cols-decoupe')?.value) || 1,
    rows_decoupe:    parseInt(g('f-rows-decoupe')?.value) || 1,
    rayon_decoupe_d: parseFloat(g('f-rayon-decoupe-d')?.value) || 0,
    mbtiles_d:       g('f-mbtiles-d')?.checked,
    rmap_d:          g('f-rmap-d')?.checked,
    sqlitedb_d:      g('f-sqlitedb-d')?.checked,
    ecraser_d:       g('f-ecraser-d')?.checked,
  };
  // Remap scan rmap/sqlitedb
  // Remap scan : unifier les clés de format pour _build_cmd
  // (supprimé — _build_cmd lit directement mbtiles_s/rmap_s/sqlitedb_s)
  return cfg;
}

function loadConfig(cfg) {
  const s  = (id, val) => { const el = document.getElementById(id);
    if (!el || val === undefined || val === null) return;
    if (el.type === 'checkbox') el.checked = !!val; else el.value = val; };
  const sr = (name, val) => { const r = document.querySelector(`input[name=${name}][value="${val}"]`);
    if (r) r.checked = true; };

  // Zone
  if (cfg.mode) sr('mode', cfg.mode);
  if (cfg.type) sr('type', cfg.type);

  // Projet
  s('f-nom',     cfg.nom);
  s('f-dossier', cfg.dossier);

  // Zone géo
  s('f-ville',   cfg.ville);
  s('f-gps',     cfg.gps);
  s('f-bbox',    cfg.bbox);
  s('f-dep',     cfg.dep);
  s('f-rayon',     cfg.rayon);
  s('f-rayon-gps', cfg.rayon);


  // LiDAR
  s('f-tel',            cfg.no_tel !== undefined ? !cfg.no_tel : cfg.tel);
  s('f-comp',           cfg.comp);
  s('f-ecraser-tel',    cfg.ecraser_tel);          // FIX: était cfg.ecraser_tel_l
  s('f-workers-l',      cfg.workers_l);
  s('f-dossier-dalles', cfg.dossier_dalles);
  s('f-no-omb',         cfg.no_omb);
  s('f-elevation',      cfg.elevation);
  s('f-ecraser-omb',    cfg.ecraser_omb);          // FIX: était cfg.ecraser_omb_l
  // FIX: f-mbtiles-l (section "calculer les tuiles") n'était jamais restauré
  s('f-mbtiles-l',      cfg.mbtiles_l || cfg.rmap || cfg.sqlitedb || false);
  // Forcer le toggle du body-mbt après restauration
  { const _cb = g('f-mbtiles-l'); const _bd = g('body-mbt');
    if (_cb && _bd) _bd.classList.toggle('hidden', !_cb.checked); }
  s('f-mbtiles',        cfg.mbtiles_l !== undefined ? cfg.mbtiles_l : (cfg.mbtiles !== undefined ? cfg.mbtiles : false));
  s('f-rmap',           cfg.rmap);
  s('f-sqlitedb',       cfg.sqlitedb);
  s('f-zoom-min-l',     cfg.zoom_min_l);
  s('f-zoom-max-l',     cfg.zoom_max_l);
  if (cfg.fmt_l) sr('fmt-l', cfg.fmt_l);
  s('f-qualite-l',      cfg.qualite_l);
  s('f-ecraser-mbt',    cfg.ecraser_mbt);          // FIX: était cfg.ecraser_mbt_l
  s('f-priori-cols',   cfg.cols_decoupe);
  s('f-priori-rows',   cfg.rows_decoupe);
  s('f-priori-cols-s', cfg.cols_decoupe_s);
  s('f-priori-rows-s', cfg.rows_decoupe_s);
  s('f-rayon-priori-l', cfg.rayon_decoupe_l);
  s('f-rayon-priori-s', cfg.rayon_decoupe_s);
  // FIX: f-nettoyage et f-nettoyage-s n'étaient jamais restaurés
  s('f-nettoyage',   cfg.nettoyage);
  s('f-nettoyage-s', cfg.nettoyage);

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
  s('f-rmap-s',         cfg.rmap_s);               // FIX: était cfg.rmap (clé LiDAR !)
  s('f-sqlitedb-s',     cfg.sqlitedb_s);            // FIX: était cfg.sqlitedb (clé LiDAR !)
  if (cfg.fmt_s) sr('fmt-s', cfg.fmt_s);
  s('f-qualite-s',      cfg.qualite_s);
  s('f-ecraser-tuil-s', cfg.ecraser_tuil_s);

  // OSM
  s('f-tel-osm',          cfg.tel_osm !== undefined ? cfg.tel_osm : true);
  s('f-workers-osm',      cfg.workers_osm);         // FIX: n'était jamais restauré
  s('f-ecraser-tel-osm',  cfg.ecraser_tel_osm);
  s('f-tuiles-osm',       cfg.tuiles_osm !== undefined ? cfg.tuiles_osm : true);
  s('f-map',              cfg.map !== undefined ? cfg.map : true);
  s('f-osm-geojson',      cfg.osm_geojson !== undefined ? cfg.osm_geojson : true);
  s('f-osm-geojson-raw',  cfg.osm_geojson_raw);
  s('f-ecraser-tuil-osm', cfg.ecraser_tuil_osm);
  // FIX: était cfg.osm_tags — la clé sauvée par getConfig est osm_tags_sel
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
  // FIX: était cfg.wfs_couches — la clé sauvée par getConfig est wfs_couches_sel
  if (cfg.wfs_couches_sel) {
    const wfsSet = new Set(typeof cfg.wfs_couches_sel === 'string'
      ? cfg.wfs_couches_sel.split(' ') : cfg.wfs_couches_sel);
    document.querySelectorAll('input[name=wfs]').forEach(c => {
      c.checked = wfsSet.has(c.value);
    });
  }

  // Fusion
  s('f-fusion-gz2',     cfg.fusion_gz2 !== undefined ? cfg.fusion_gz2 : true);
  s('f-fusion-gz2-raw', cfg.fusion_gz2_raw);        // FIX: n'était jamais restauré
  s('f-fusion-map',     cfg.fusion_map);             // FIX: n'était jamais restauré
  if (cfg.simplif_v     != null) { const el=g('f-simplif-v');     if(el) el.value=cfg.simplif_v; }
  if (cfg.simplif_fusion!= null) { const el=g('f-simplif-fusion');if(el) el.value=cfg.simplif_fusion; }
  if (cfg.fusion_fichiers) {
    fusionFiles = cfg.fusion_fichiers;
    renderFusionList();
  }

  // Découpage raster
  s('f-source-decoupe',  cfg.source_decoupe);
  s('f-cols-decoupe',  cfg.cols_decoupe);
  s('f-rows-decoupe',  cfg.rows_decoupe);
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

  // Re-déclencher les toggles et l'état initial
  if (cfg.mode) { const r = document.querySelector(`input[name=mode][value="${cfg.mode}"]`);
    if (r) r.dispatchEvent(new Event('change')); }
  if (cfg.type) { const r = document.querySelector(`input[name=type][value="${cfg.type}"]`);
    if (r) r.dispatchEvent(new Event('change')); }
  document.querySelectorAll('.section-hd input[type=checkbox]').forEach(cb =>
    cb.dispatchEvent(new Event('change')));
}

// ── Dialogs ───────────────────────────────────────────────────────────────────
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
  if (invalid.length) alert(`Ignoré(s) : ${invalid.map(f=>f.split(/[\\/]/).pop()).join(', ')}\nSeuls .geojson et .geojson.gz sont acceptés.`);
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

// ── Lancement ─────────────────────────────────────────────────────────────────
function setFormLocked(locked) {
  const els = document.getElementById('main')
    .querySelectorAll('input,select,button:not(#btn-stop)');
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
  // Valider que la zone géographique est renseignée (sauf Fusion et Découpage raster)
  if (cfg.type !== 'fusion' && cfg.type !== 'decoupe') {
    const zoneOk = (cfg.mode === 'ville'  && cfg.ville) ||
                   (cfg.mode === 'gps'    && cfg.gps)   ||
                   (cfg.mode === 'bbox'   && cfg.bbox)  ||
                   (cfg.mode === 'dep'    && cfg.dep)   ||
                    false;
    if (!zoneOk) {
      const labels = {ville:'Ville', gps:'GPS', bbox:'BBox', dep:'Département'};
      alert(`Le champ "${labels[cfg.mode] || cfg.mode}" est obligatoire.`);
      return;
    }
  }
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  document.getElementById('footer-status').textContent = 'En cours...';
  setFormLocked(true);

  const res = await pywebview.api.launch(cfg);
  if (res && res.error) { alert(res.error); btnReset(); return; }

  // Afficher la commande lancée
  document.getElementById('footer-status').textContent = '▶ ' + (res.cmd || '').split(' ').slice(-3).join(' ') + '…';

  polling = setInterval(async () => {
    const r = await pywebview.api.poll_log();
    if (r.items) {
      r.items.forEach(item => {
        if (item.pct !== undefined && item.pct >= 0) {
          document.getElementById('footer-status').textContent =
            item.pct + '%  ' + (item.label || '').substring(0, 80);
        }
      });
    }
    if (r.done) {
      clearInterval(polling); polling = null;
      document.getElementById('footer-status').textContent =
        r.code === 0 ? '✓ Terminé' : `✗ Erreur (code ${r.code})`;
      if (r.code === 0) {
        // Recharger l'historique via appel dédié (plus fiable que poll_log)
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
  document.getElementById('footer-status').textContent = '⚠ Arrêté';
  btnReset();
}

function btnReset() {
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  setFormLocked(false);
}
</script>
</body>
</html>"""

    api = Api()

    win = webview.create_window(
        "lidar2map — Cartes offline LiDAR/IGN/OSM",
        html=HTML,
        js_api=api,
        width=1300, height=850,
        min_size=(1000, 600),
    )
    # Assigner la fenêtre immédiatement — disponible dès create_window
    api.window = win

    webview.start(debug=False)


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            lancer_gui()
        else:
            # ── Résolution multi-département ─────────────────────────────────
            # --zone-departement accepte : 83 | 30,35,75 | 1-10 | 1-3,75,83
            _dep_idx = None
            for _i, _a in enumerate(sys.argv):
                if _a == "--zone-departement" and _i + 1 < len(sys.argv):
                    _dep_idx = _i + 1
                    break

            _deps = _parser_departements(sys.argv[_dep_idx]) if _dep_idx else None

            def _dispatch():
                if "--decouper"  in sys.argv: main_decouper()   # MBTiles a posteriori
                elif "--ignraster"  in sys.argv: main_wmts()    # WMTS IGN raster
                elif "--ignvecteur" in sys.argv: main_wfs()     # WFS IGN vectoriel
                elif "--fusionner"  in sys.argv: main_fusionner()  # fusion GeoJSON
                else:                             main()          # --ignlidar ou --osm

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
                for _n, _dep in enumerate(_deps, 1):
                    print()
                    print(_sep)
                    print(f"  Département {_dep}  ({_n}/{len(_deps)})")
                    print(_sep)
                    sys.argv = _argv_base[:]
                    sys.argv[_dep_idx] = _dep
                    # Suffixer le nom explicite avec le numéro de département
                    if _nom_idx is not None:
                        sys.argv[_nom_idx] = f"{_nom_base}_{_dep}"
                    _dispatch()
            else:
                _dispatch()
    finally:
        if isinstance(sys.stdout, _TeeLogger):
            sys.stdout.close()
            sys.stdout = sys.stdout._terminal if hasattr(sys.stdout, "_terminal") else sys.__stdout__
