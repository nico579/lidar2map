"""Producteur MBTiles pour les rasters LiDAR (ombrages/analyses) déjà générés.

Le module contient le warp rasterio (Lambert93 → Web Mercator), la pyramide
d'overviews, le tuilage par bandes et la publication SQLite atomique du
MBTiles. Trois helpers purs (bbox source, validation d'un warpé en cache,
parallélisme d'encodage par défaut) l'accompagnent : ils n'ont pas de couture
avec l'application et sont réexportés tels quels par ``lidar2map``. Le
producteur lui-même reçoit ses coutures applicatives (fraîcheur, publication
atomique, arrêt coopératif, transformations géographiques, fournisseur actif)
par une structure de dépendances injectée à chaque appel, reconstruite par la
façade de ``lidar2map`` — c'est ce qui garde vivants les monkeypatches des
suites de tests historiques (`PROVIDER`, `_creer_fichier`,
`_bbox_enveloppe_transform`, etc. sont substitués sur le module principal, pas
ici).
"""

from __future__ import annotations

import io
import math
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _DependancesMbtilesLidar:
    """Coutures entre le producteur LiDAR et l'application."""

    chemin_part: Callable
    nettoyer_sqlite_part: Callable
    valider_sqlite_part: Callable
    mbtiles_a_regenerer: Callable
    creer_fichier: Callable
    formater_duree: Callable
    stop_event: object
    get_transformer: Callable
    natif_vers_wgs84: Callable
    bbox_enveloppe_transform: Callable
    batch_insert: int
    crs_natif: str


def _bbox_depuis_gdalinfo(chemin):
    """Retourne (xmin, ymin, xmax, ymax) en unités natives du fichier via rasterio."""
    try:
        import rasterio
        with rasterio.open(str(chemin)) as ds:
            b = ds.bounds   # BoundingBox(left, bottom, right, top)
            return (b.left, b.bottom, b.right, b.top)
    except Exception:
        return None


def _warped_3857_valide(chemin):
    """True si `chemin` est un GeoTIFF EPSG:3857 lisible (dims > 0, 1 bloc lu).

    Garde-fou du cache de warp : un warpé partiel laissé par une interruption
    (jadis écrit directement dans son chemin final) pouvait dépasser 1 Mo et
    être plus récent que la source, donc réutilisé à tort comme valide. On
    l'ouvre pour vérifier CRS + dimensions + une lecture. Ne lève jamais."""
    try:
        import rasterio as _rio_v
        with _rio_v.open(str(chemin)) as _d:
            if _d.width == 0 or _d.height == 0:
                return False
            if _d.crs is None or _d.crs.to_epsg() != 3857:
                return False
            _d.read(1, window=_rio_v.windows.Window(
                0, 0, min(64, _d.width), min(64, _d.height)))
        return True
    except Exception:
        return False


def _tile_workers_defaut():
    """Parallélisme de l'encodage de tuiles (JPEG/PNG, Pillow libère le GIL,
    cf. le pool dans generer_mbtiles_lidar) : DÉCOUPLÉ de --workers, qui
    plafonne les téléchargements réseau (throttle IGN ~3 en simultané, cf.
    --laz-parallel pour la même logique côté conversion LAZ). L'encodage est
    100% CPU local, sans lien avec ce plafond réseau : le limiter au nombre
    de workers de download le bridait sans raison (ex. --workers 3 sur une
    VM à 16 vCPU = 13 coeurs inutilisés pendant tout le tuilage)."""
    return os.cpu_count() or 4


def generer_mbtiles_lidar(tif_source, dossier_ville, nom_ville,
                    zoom_min=13, zoom_max=17, format_tuiles="auto",
                    jpeg_quality=85, bbox_natif=None, tampon_coin_max_m=0,
                    source_already_warped=False, ecraser_tuiles=False,
                    tile_workers=8, *, dependances):
    """
    Pipeline MBTiles : source unique, pyramide rasterio, tuilage par bandes.

    1. rasterio.warp : tif_source (EPSG:2154) → warped_3857.tif (EPSG:3857)
                       à la résolution native de zoom_max, DEFLATE+TILED.
    2. build_overviews : overviews gauss pour zoom_min..zoom_max-1.
    3. Tiling : rangées de tuiles via lecture fenêtrée rasterio + Pillow
                → INSERT OR REPLACE SQLite.

    format_tuiles : 'auto' (JPEG pour hillshades, PNG pour SVF/LRM/RRIM),
                    'jpeg' ou 'png'.
    JPEG à Q=85 divise la taille par 5-8 sur les hillshades sans perte visible.
    PNG conservé pour les analyses à gradient fin (SVF, LRM) et RRIM couleur.
    """
    _chemin_part = dependances.chemin_part
    _nettoyer_sqlite_part = dependances.nettoyer_sqlite_part
    _valider_sqlite_part = dependances.valider_sqlite_part
    _mbtiles_a_regenerer = dependances.mbtiles_a_regenerer
    _creer_fichier = dependances.creer_fichier
    _hms = dependances.formater_duree
    _stop_event = dependances.stop_event
    _get_transformer = dependances.get_transformer
    _natif_vers_wgs84 = dependances.natif_vers_wgs84
    _bbox_enveloppe_transform = dependances.bbox_enveloppe_transform
    BATCH_MBTILES_INSERT = dependances.batch_insert
    _crs_natif_actif = dependances.crs_natif

    from PIL import Image

    # Vérification anticipée de rasterio — évite d'attendre la fin du warp
    try:
        import rasterio as _rio_check  # noqa
    except ImportError:
        print("  ERROR: rasterio missing - required for MBTiles tiling.")
        print("  Install it: pip install rasterio")
        return None

    Image.MAX_IMAGE_PIXELS = None

    # Contrôle dtype AVANT le warp (fail-fast, R2#19) : le tuileur écrit chaque
    # fenêtre dans un canvas uint8 (`_np.zeros(..., uint8)`). Une source 16 bits
    # ou flottante (MNT brut passé via --source) y serait COULÉE sans
    # normalisation — valeurs 0-65535 ou flottantes tronquées mod 256 = tuiles
    # aberrantes, publiées en silence. gdal2tiles refuse pareillement une source
    # non-Byte. Les ombrages produits par lidar2map sont déjà uint8 : ce garde
    # ne vise que les rasters --source bruts. On échoue tôt avec le remède.
    try:
        import rasterio as _rio_dt
        with _rio_dt.open(str(tif_source)) as _dsrc:
            _src_dtypes = set(_dsrc.dtypes)
    except Exception:
        _src_dtypes = set()   # illisible ici : le warp échouera avec son message
    if _src_dtypes and _src_dtypes != {"uint8"}:
        print(f"  ERROR: source dtype {sorted(_src_dtypes)} - the tiler needs "
              f"8-bit (Byte); values would be truncated silently.")
        print(f"  Rescale first, e.g.:  gdal_translate -ot Byte -scale "
              f"{tif_source.name} scaled_8bit.tif")
        return None

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
    print(f"  Base tile format: {_tile_fmt}"
          f"{'  Q=' + str(jpeg_quality) if _use_jpeg else '  lossless'}", flush=True)

    EARTH_CIRC = 20037508.3427892
    TILE_SIZE  = 256

    # Nom de base : utiliser nom_ville si fourni (ex: "aa_hillshade_multi"),
    # sinon stem du TIF source
    nom_base = nom_ville if nom_ville else tif_source.stem
    mbtiles  = dossier_ville / (nom_base + f"_z{zoom_min}-{zoom_max}.mbtiles")

    # MÊME décideur que les call sites (_mbtiles_a_regenerer) : fraîcheur vs
    # TIF source incluse. L'ancien gate `exists and not ecraser` court-circuitait
    # la décision du caller ("older than ... regenerating" suivi d'un
    # "already present" → l'ancien rendu restait servi).
    # source=tif_source TOUJOURS, y compris already-warped (R2#22) : dans ce cas
    # le tuilage lit tif_source DIRECTEMENT (warped = tif_source, cf. plus bas),
    # donc c'est la bonne référence de fraîcheur. L'ancien `None if
    # source_already_warped` désactivait la comparaison → un mbtiles plus vieux
    # qu'un TIF source ré-exporté passait pour "already present" (l'appelant
    # décidait pourtant regen, mais ce check interne l'annulait).
    if not _mbtiles_a_regenerer(mbtiles, ecraser_tuiles, source=tif_source):
        print(f"  {mbtiles.name} → already present")
        return mbtiles
    if mbtiles.exists():
        # Pas d'unlink : mbtiles_part.replace(mbtiles) écrase atomiquement à la
        # fin. Le supprimer maintenant perdrait l'ancien rendu si ce run échoue.
        print(f"  {mbtiles.name} → overwrite")

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

    res_max = 2 * EARTH_CIRC / (TILE_SIZE * 2 ** zoom_max)

    # Bbox source dans le CRS natif du provider, fournie directement par
    # main() si connue (évite gdalinfo qui peut échouer sans proj.db sur
    # certaines installations)
    if bbox_natif is not None:
        bb_src = bbox_natif
    else:
        bb_src = _bbox_depuis_gdalinfo(tif_source)
    if bb_src:
        w_src_px = (bb_src[2] - bb_src[0]) / res_max
        h_src_px = (bb_src[3] - bb_src[1]) / res_max
        taille_go_est = w_src_px * h_src_px / 1e9
    else:
        taille_go_est = 0.0

    if taille_go_est > 0:
        print(f"  Estimated size: ~{taille_go_est:.1f} Go -> single warp"
              f" (rasterio streaming)", flush=True)

    # Niveaux d'overviews — gauss > average pour hillshades (rendu 8 bits)
    overview_levels = [2 ** (zoom_max - z)
                       for z in range(zoom_max - 1, zoom_min - 1, -1)]

    # ── MBTiles ───────────────────────────────────────────────────────────────
    mbtiles.parent.mkdir(parents=True, exist_ok=True)
    # Écriture dans un .part renommé à la fin : un .mbtiles présent est
    # TOUJOURS complet (même garantie que generer_mbtiles_wmts). Sans ça, un
    # run interrompu laissait un partiel que _mbtiles_a_regenerer validait.
    mbtiles_part = _chemin_part(mbtiles)
    con = sqlite3.connect(str(mbtiles_part))
    # Une seule connexion écrit. Un journal MEMORY est plus cohérent qu'un WAL
    # persistant : toute la base est déjà jetable sous .part jusqu'au replace,
    # et aucun sidecar ne doit accompagner le fichier publié.
    con.execute("PRAGMA journal_mode=MEMORY;")
    con.execute("PRAGMA synchronous=OFF;")
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles   (zoom_level INTEGER, tile_column INTEGER,
                              tile_row   INTEGER, tile_data   BLOB);
        CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
    """)
    # NB : la métadonnée "format" est insérée APRÈS le tuilage (R1#7), une fois
    # connu si le run a émis des tuiles PNG-alpha (bas zoom / bord) en plus des
    # JPEG intérieures — le format déclaré doit refléter le contenu réel.
    for k, v in [("name", mbtiles.stem), ("type", "overlay"), ("version", "1.0"),
                 ("description", nom_ville),
                 ("minzoom", str(zoom_min)), ("maxzoom", str(zoom_max))]:
        cur.execute("INSERT INTO metadata VALUES (?,?)", (k, v))

    # bounds : requis par la spec MBTiles et par Locus pour positionner la carte
    # "left,bottom,right,top" en degrés WGS84
    if bbox_natif is not None:
        # Enveloppe des 4 coins : un rectangle dans le CRS natif ne reste pas
        # axis-aligné après reprojection, min/max sur 2 coins opposés
        # sous-estimerait l'emprise.
        _pts4 = [_natif_vers_wgs84(cx4, cy4)
                 for cx4, cy4 in ((bbox_natif[0], bbox_natif[1]),
                                  (bbox_natif[2], bbox_natif[1]),
                                  (bbox_natif[2], bbox_natif[3]),
                                  (bbox_natif[0], bbox_natif[3]))]
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

    # R1#7 : le format de tuile est décidé PAR TUILE. Une tuile qui déborde de
    # l'emprise couverte (bas zoom : tuile >> chunk ; frange de bord) porte du
    # padding hors-source. En JPEG ce padding est NOIR OPAQUE → tuile bas zoom
    # noire, et en découpé/sharding (1 mbtiles par chunk que Locus empile) la
    # tuile opaque d'un bloc MASQUE la pastille du bloc voisin au même (z,x,y).
    # Fix : les tuiles à padding sortent en PNG alpha=0 (composables entre
    # blocs) ; les tuiles PLEINES gardent le format de base (JPEG = gain taille
    # là où le padding est absent, càd la masse des hauts zooms intérieurs).
    _emitted_partial = False   # ≥1 tuile PNG-alpha émise dans un run base-JPEG

    # ── Pool d'encodage des tuiles ────────────────────────────────────────
    # Pillow libère le GIL pendant JPEG/PNG save, donc un ThreadPool donne du vrai
    # parallélisme. Le pool est créé une fois pour toute la pyramide et fermé
    # à la fin. Sur petites bandes (<_MIN_PAR_TILES tuiles), on bypass le pool
    # car l'overhead submit/wait l'emporte sur le gain d'encodage.
    _MIN_PAR_TILES = 8
    _pool = ThreadPoolExecutor(max_workers=tile_workers) if tile_workers > 1 else None

    def _encode_tile(args):
        _tile, _alpha, _z, _tx, _ty = args
        _buf = io.BytesIO()
        if _alpha is not None:
            # R1#7 : tuile partielle → PNG avec canal alpha (0 hors emprise) pour
            # composer entre chunks/blocs empilés dans Locus/OsmAnd. RGBA (et non
            # LA) pour la compat maximale des décodeurs Android.
            _rgba = _tile.convert("RGBA")
            _rgba.putalpha(_alpha)
            _rgba.save(_buf, "PNG", optimize=False, compress_level=6)
        elif _use_jpeg:
            _tile.convert("RGB").save(_buf, "JPEG",
                                       quality=jpeg_quality, optimize=False)
        else:
            # PNG : conserver le mode natif — une source monobande (SVF, LRM)
            # part en niveaux de gris ("L"), ~2-3× plus petit que le même
            # contenu tripliqué en RGB. PNG grayscale = standard, lu par
            # Locus/OsmAnd/TwoNav. compress_level=6 (défaut zlib) : artefact
            # final écrit une fois, lu mille fois — le niveau 1 économisait
            # quelques secondes d'encodage contre ~20-30 % de taille.
            # RGBA gardé pour PNG : préserver l'alpha d'une source --source RGBA
            # (R2#19) ; L/RGB inchangés ; autres modes (P, LA…) → RGB.
            _img = _tile if _tile.mode in ("L", "RGB", "RGBA") else _tile.convert("RGB")
            _img.save(_buf, "PNG", optimize=False, compress_level=6)
        _y_tms = (2 ** _z - 1) - _ty
        return (_z, _tx, _y_tms, _buf.getvalue())

    def _tuiler_source():
        # Warp → overviews → tuilage de la source. Fonction locale : les
        # `return` court-circuitent le tuilage en cas d'échec du warp ou de
        # bbox introuvable (remplace l'ancienne boucle banding à tranche
        # unique et ses `continue` ; le banding a été retiré car il créait
        # des artefacts de jointure Lambert93/Mercator).
        nonlocal total_insere, nb_echecs_tr, _emitted_partial
        # Fichier warped persistant dans dossier_ville — préfixe _ pour
        # être ignoré par le glob MBTiles (not t.name.startswith("_")).
        # Nom déterministe : source + zoom_max → réutilisable si on relance
        # avec des zooms différents sur le même TIF source.
        warped = dossier_ville / f"{tif_source.stem}_tuilage_z{zoom_max}.tif"
        lbl    = warped.name
        # Masque de couverture séparé (cf. bloc de reproject plus bas) :
        # un rectangle du CRS natif (ex. Lambert93) ne reste pas axis-aligné
        # une fois reprojeté en Web Mercator, donc warped lui-même contient
        # des coins hors de la vraie empreinte, remplis à 0 par le warp faute
        # de nodata. Fichier séparé (pas une bande de plus dans warped) pour
        # ne pas perturber la détection RGBA existante basée sur _w_count.
        warped_cov = dossier_ville / f"{tif_source.stem}_tuilage_z{zoom_max}_cov.tif"

        # Si la source est déjà en EPSG:3857 (ex: _warped_*.tif réutilisé),
        # pas besoin de re-warper — on l'utilise directement comme warped.
        if source_already_warped:
            warped = tif_source
            warp_deja_fait = True
            print("  Source already in EPSG:3857 - warp skipped", flush=True)
        else:
            # Fraîcheur : un cache warpé plus VIEUX que le TIF source signifie
            # que l'ombrage a été régénéré (--shadings-overwrite) → re-warper,
            # sinon les tuiles resserviraient l'ancien rendu. + validation du
            # cache (CRS 3857 + dims + lecture) : sinon un warpé tronqué mais
            # récent était réutilisé comme valide (#4).
            # warped_cov.exists() : un cache warpé écrit AVANT ce fix (masque
            # de couverture séparé) n'a pas de fichier _cov → sans ce test,
            # il serait réutilisé tel quel, coins noirs jamais corrigés.
            warp_deja_fait = (warped.exists() and warped.stat().st_size > 1_000_000
                              and not ecraser_tuiles
                              and warped.stat().st_mtime >= tif_source.stat().st_mtime
                              and _warped_3857_valide(warped)
                              and warped_cov.exists())
            if warp_deja_fait:
                print(f"  Warped cache: {warped.name}  "
                      f"({warped.stat().st_size/1e6:.0f} MB) reused", flush=True)

        # ── 1. Warp via rasterio ───────────────────────────────────────────
        # Plus de cmd_warp gdalwarp à construire — voir bloc rasterio.warp
        # plus bas. On garde le calcul de te_xmin/etc. pour la bbox cible.
        # ── Calcul de l'étendue cible en Web Mercator ────────────────────
        te_xmin = te_ymin = te_xmax = te_ymax = None
        # Repli CRS natif → WGS84 → Web Mercator en Python pur (fallback du
        # transformer pyproj ci-dessous). _natif_vers_wgs84 borne la France :
        # hors pyproj et hors France il lève, plutôt que de projeter du natif
        # étranger avec les formules Lambert 93.
        def _natif_to_merc(x, y):
            lon, lat = _natif_vers_wgs84(x, y)
            mx = math.radians(lon) * 6378137.0
            my = math.log(math.tan(math.pi/4 + math.radians(lat)/2)) * 6378137.0
            return mx, my

        if bb_src is not None:
            x0, _y0, x1, _y1 = bb_src
            # Un rectangle dans le CRS natif du provider ne reste pas
            # axis-aligné après reprojection (la grille tourne légèrement) :
            # chaque côté devient une ligne très légèrement inclinée en
            # Mercator. Milieu de CHAQUE côté (moyenne des 2 coins qui le
            # bornent), PAS min/max des 4 coins du bloc : l'enveloppe min/max
            # publiait systématiquement plus que le rectangle nominal sur
            # chaque côté (~265 m mesuré sur un bloc 5 km à cette latitude,
            # cf. gdalwarp -te, conservateur par design pour une zone isolée).
            # Deux blocs voisins directs (même rangée ou même colonne)
            # partagent EXACTEMENT les 2 coins de leur frontière commune :
            # ils moyennent les 2 mêmes points → même frontière des deux
            # côtés, aucune incidence pour une zone seule.
            #
            # ESSAYÉ ET ABANDONNÉ : faire porter cette moyenne sur l'étendue
            # de la zone ENTIÈRE (pas les bornes propres du bloc) pour aussi
            # réconcilier le coin partagé par 4 blocs (diagonaux, découpage
            # à priori) — supprime bien le petit trou/carré blanc au centre,
            # MAIS pour un bloc loin du bord opposé de la zone (ex. rangée
            # nord utilisant le bord sud de la zone), la droite obtenue
            # dérive du bord LOCAL réel du bloc suffisamment pour que le
            # pixel de destination corresponde, une fois reprojeté en sens
            # inverse, à une coordonnée hors de la couverture de la dalle
            # source de CE bloc → vraies zones sans données (triangle noir,
            # mesuré 2026-08-05 : ~90 m de dérive dès le bord nord d'un bloc
            # 5 km, largement au-delà du sous-pixel). Pire que le défaut que
            # ça devait corriger. Reverti : le petit trou au coin partagé par
            # 4 blocs (borné, ~265 m, un point isolé) reste un residu connu,
            # préférable à une perte de données réelle.
            try:
                _t = _get_transformer(_crs_natif_actif, "EPSG:3857")
                _tr = _t.transform
            except Exception:
                _tr = _natif_to_merc
            corners = [(x0, _y0), (x1, _y0), (x1, _y1), (x0, _y1)]  # SO SE NE NO
            p_so, p_se, p_ne, p_no = [_tr(cx, cy) for cx, cy in corners]
            te_xmin = (p_so[0] + p_no[0]) / 2   # côté ouest
            te_xmax = (p_se[0] + p_ne[0]) / 2   # côté est
            te_ymin = (p_so[1] + p_se[1]) / 2   # côté sud
            te_ymax = (p_no[1] + p_ne[1]) / 2   # côté nord
            if tampon_coin_max_m:
                # Ferme le petit trou qui reste au coin partagé par 4 blocs
                # (découpage à priori) : le milieu de bord ci-dessus rend
                # chaque frontière exacte avec les voisins directs, mais le
                # coin diagonal reste calculé différemment par chacun des 4
                # blocs (cf. discussion). PAS de retour à un calcul
                # zone-globale (tenté et reverti : dérive au-delà de la
                # dalle source, nodata) : ici on élargit juste la fenêtre
                # publiée par CE bloc, en pixels RÉELS, pas inventés —
                # l'appelant garantit une couverture d'au moins
                # tampon_coin_max_m au-delà de cette bbox (marge de
                # téléchargement fixe pour --block, ou VRT avec les vrais
                # voisins sinon).
                #
                # Tampon CALCULÉ, pas une constante à ajuster à la main :
                # l'écart au coin dépend de la latitude et de la taille du
                # bloc (via le cisaillement de la reprojection), et l'outil
                # gère des providers du monde entier avec des tailles de
                # bloc au choix de l'utilisateur — une constante calée sur
                # un seul cas (mesuré 2026-08-05 : ~192-265 m en France,
                # blocs 5 km) serait tantôt trop courte tantôt inutilement
                # large ailleurs. Dérivation : pour un bloc voisin direct
                # partageant EXACTEMENT 2 de mes coins, son propre calcul de
                # bord ne diffère du mien que par l'AUTRE coin qu'il moyenne
                # (le sien, à une largeur/hauteur de bloc plus loin) ; half
                # de cet écart = l'ampleur réelle du coin manquant, sans
                # avoir besoin des données du voisin, juste sa position
                # géométrique connue (grille régulière).
                largeur = x1 - x0
                hauteur = _y1 - _y0
                _pt_e = _tr(x1 + largeur, _y1)   # coin NE d'1 largeur plus loin
                _pt_n = _tr(x0, _y1 + hauteur)   # coin NO d'1 hauteur plus loin
                gap_ns = abs(p_no[1] - _pt_e[1]) / 2
                gap_ew = abs(p_so[0] - _pt_n[0]) / 2
                tampon_coin_m = min(max(gap_ns, gap_ew), tampon_coin_max_m)
                te_xmin -= tampon_coin_m
                te_xmax += tampon_coin_m
                te_ymin -= tampon_coin_m
                te_ymax += tampon_coin_m
        # Si bb_src est None, te_* restent None et le warp retombe proprement
        # sur calculate_default_transform (étendue auto depuis la source).

        if not warp_deja_fait:
            # ── 1. Warp via rasterio (remplace gdalwarp CLI — étape 5) ──────
            # Lambert 93 (EPSG:2154) → Web Mercator (EPSG:3857) avec
            # rééchantillonnage bilinéaire et résolution cible res_max.
            # Conserve le -te (target extent) calculé ci-dessus pour ne pas
            # dépendre de proj.db pour la conversion d'étendue.
            print(f"  Warp EPSG:3857  res={res_max:.3f} m/px"
                  f"  (rasterio, zoom {zoom_max})...", flush=True)

            t0_warp = time.time()
            try:
                import rasterio as _rio_w
                from rasterio.warp import calculate_default_transform as _calc_tr
                from rasterio.warp import reproject as _reproject
                from rasterio.warp import Resampling as _Resampling
                from rasterio.transform import from_origin as _from_origin

                with _rio_w.open(str(tif_source)) as src:
                    # Si te_xmin/etc. fournis : on impose la bbox cible.
                    # Sinon : calculate_default_transform calcule l'étendue
                    # automatiquement à partir des bounds de la source.
                    if te_xmin is not None:
                        # Coin haut-gauche calé sur la grille WebMercator
                        # GLOBALE (référence -EARTH_CIRC/+EARTH_CIRC, même
                        # convention que merc_to_tile/tile_bounds ci-dessus),
                        # résolution EXACTEMENT res_max, arrondi VERS
                        # L'EXTÉRIEUR (équivalent de gdalwarp -tap, target
                        # aligned pixels). Avant ce calage, dst_width/height
                        # étaient arrondis indépendamment par bloc puis
                        # from_bounds() répartissait l'écart d'arrondi sur
                        # toute la largeur : la résolution réelle dérivait
                        # légèrement d'un bloc à l'autre et deux blocs voisins
                        # (découpage à priori) n'avaient plus la garantie que
                        # leurs grilles de pixels coïncident à la jonction →
                        # couture visible dans le MBTiles, identique quel que
                        # soit l'ombrage (lrm ET multi affectés, TIF source
                        # intact).
                        snap_x0 = -EARTH_CIRC + math.floor(
                            (te_xmin + EARTH_CIRC) / res_max) * res_max
                        snap_y1 = EARTH_CIRC - math.floor(
                            (EARTH_CIRC - te_ymax) / res_max) * res_max
                        dst_width  = int(math.ceil((te_xmax - snap_x0) / res_max))
                        dst_height = int(math.ceil((snap_y1 - te_ymin) / res_max))
                        dst_transform = _from_origin(
                            snap_x0, snap_y1, res_max, res_max)
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

                    # Écriture dans <warped>.part validé puis replace (#4) :
                    # une interruption ne laisse plus un warpé tronqué que le
                    # run suivant réutiliserait comme cache valide.
                    warped_part = _chemin_part(warped)
                    with _rio_w.open(str(warped_part), "w", **dst_profile) as dst:
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

                    # Masque de couverture (cf. commentaire à la définition de
                    # warped_cov) : reprojette une source constante à 255 avec
                    # EXACTEMENT le même transform/CRS que les bandes réelles
                    # ci-dessus, dst_nodata=0 — capture la vraie empreinte
                    # pivotée (GDAL sait la calculer, nous non sans réinventer
                    # la géométrie de reprojection). Fichier à part : ne
                    # change pas le nombre de bandes de warped_3857.tif, donc
                    # ne perturbe pas la détection RGBA existante (_w_count).
                    import numpy as _np_cov
                    cov_part = _chemin_part(warped_cov)
                    cov_profile = dst_profile.copy()
                    cov_profile.update(count=1, dtype="uint8", nodata=None,
                                       compress="deflate", predictor=1)
                    with _rio_w.open(str(cov_part), "w", **cov_profile) as dst_cov:
                        _cov_src = _np_cov.full((src.height, src.width), 255,
                                                dtype=_np_cov.uint8)
                        _reproject(
                            source        = _cov_src,
                            destination   = _rio_w.band(dst_cov, 1),
                            src_transform = src.transform,
                            src_crs       = src.crs,
                            dst_transform = dst_transform,
                            dst_crs       = "EPSG:3857",
                            dst_nodata    = 0,
                            resampling    = _Resampling.nearest,
                            num_threads   = 0)
                    cov_part.replace(warped_cov)
                # Les overviews font partie du fichier : les construire sur le
                # .part avant publication. Une interruption ne peut alors pas
                # altérer l'ancien cache final.
                if zoom_max > zoom_min and overview_levels:
                    print(f"  Overviews (gauss) {overview_levels}...", flush=True)
                    t_addo = time.time()
                    try:
                        import rasterio as _rio_o
                        from rasterio.enums import Resampling as _Res_o
                        with _rio_o.open(str(warped_part), "r+") as ds_o:
                            ds_o.build_overviews(overview_levels, _Res_o.gauss)
                            ds_o.update_tags(
                                ns="rio_overview", resampling="gauss"
                            )
                        print(f"  Overviews OK ({_hms(time.time()-t_addo)})")
                    except Exception as _e_ovw:
                        warped_part.unlink(missing_ok=True)
                        raise RuntimeError(
                            f"overview construction failed: {_e_ovw}"
                        ) from _e_ovw
                if not _warped_3857_valide(warped_part):
                    warped_part.unlink(missing_ok=True)
                    raise RuntimeError("warpé invalide après écriture "
                                       "(CRS/dimensions/lecture)")
                warped_part.replace(warped)
                _creer_fichier(warped)
                taille_w = warped.stat().st_size / 1e6
                elap = time.time() - t0_warp
                print("  " + lbl.ljust(36) + " [" + "█"*30 +
                      f"] 100%  {_hms(elap)}  {taille_w:.0f} Mo")
            except Exception as _e_warp:
                print(f"  ERROR rasterio.warp: {_e_warp}")
                return

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
            # Overviews already built on ``warped_part`` before publication.

        # ── 3. Bbox warped (EPSG:3857) ──────────────────────────────────────
        # Priorité : -te calculé lors du warp courant (pas besoin de proj.db).
        # Fallback mode cache : recalculer depuis bb_src avec pyproj/approx.
        if te_xmin is not None:
            bb_w = (te_xmin, te_ymin, te_xmax, te_ymax)
        elif warp_deja_fait and bb_src is not None:
            # Warped réutilisé : reconstruire la bbox Mercator depuis bb_src.
            # Enveloppe des 4 coins, comme le -te du warp frais : à 2 coins,
            # les rangées de tuiles en bordure étaient rognées de quelques px
            # uniquement sur le chemin cache (rendu dépendant du cache).
            try:
                _t2 = _get_transformer(_crs_natif_actif, "EPSG:3857")
                bb_w = _bbox_enveloppe_transform(_t2.transform, *bb_src)
            except Exception:
                bb_w = _bbox_enveloppe_transform(_natif_to_merc, *bb_src)
        else:
            bb_w = _bbox_depuis_gdalinfo(warped)
        if bb_w is None:
            print(f"  ERROR: bbox not found for {lbl}")
            return
        xmin_w, ymin_w, xmax_w, ymax_w = bb_w

        # ── 4. Tiling direct via rasterio ────────────────────────────────
        # Lecture directe du warped TIF par rasterio — pas de gdal_translate,
        # pas de fichiers temporaires, pas de proj.db requis pour les coords pixel.
        import rasterio as _rio
        from rasterio.windows import Window as _Win
        import numpy as _np

        batch = []
        BATCH = BATCH_MBTILES_INSERT   # constante partagée (drift : 500 local)
        # Largeur de traitement bornée : l'ancien tuileur allouait une bande
        # couvrant TOUTES les colonnes d'une rangée (mémoire ∝ largeur de la
        # zone). On traite par fenêtres de _COL_WIN tuiles ; le warp étant déjà
        # en Mercator, une fenêtre de colonnes est une simple tranche
        # horizontale (offset entier depuis le début de rangée → pas de couture).
        _COL_WIN = 48
        rangees_done = 0
        total_rangees_tr = max(1, sum(
            merc_to_tile(xmax_w, ymin_w, z)[1] -
            merc_to_tile(xmin_w, ymax_w, z)[1] + 1
            for z in range(zoom_min, zoom_max + 1)
        ))

        # Masque de couverture optionnel (absent si source_already_warped, ou
        # cache écrit avant ce fix mais alors warp_deja_fait=False donc
        # régénéré) : ouvert à part de `with _ds` pour ne pas réindenter toute
        # la boucle de tuilage dans un bloc `with` imbriqué ; fermé
        # explicitement après (cf. `_ds_cov.close()` en sortie de boucle).
        _ds_cov = None
        if warped_cov.exists():
            try:
                _ds_cov = _rio.open(str(warped_cov))
            except Exception:
                _ds_cov = None

        with _rio.open(str(warped)) as _ds:
            _w_orig_x = _ds.transform.c   # xmin Mercator
            _w_orig_y = _ds.transform.f   # ymax Mercator
            _w_res    = _ds.transform.a   # résolution pixel (m/px)
            _w_width  = _ds.width
            _w_height = _ds.height
            _w_count  = _ds.count         # nb bandes

            def _progress_rangee():
                pct  = int(rangees_done / total_rangees_tr * 100)
                bars = int(pct / 100 * 30)
                elapsed = int(time.time() - t_tile)
                print(f"\r  z{zoom_min}-{zoom_max} ["
                      + "█" * bars + "░" * (30 - bars)
                      + f"] {pct:3d}%  {total_insere} tiles  {_hms(elapsed)}",
                      end="", flush=True)

            for z in range(zoom_min, zoom_max + 1):
                tx0, ty0 = merc_to_tile(xmin_w, ymax_w, z)
                tx1, ty1 = merc_to_tile(xmax_w, ymin_w, z)
                # Résolution de cette tuile par rapport au warped (qui est à zoom_max)
                zoom_factor = 2 ** (zoom_max - z)
                _tile_px = TILE_SIZE * zoom_factor   # largeur d'1 tuile en px warped

                for ty in range(ty0, ty1 + 1):
                    # Soft-cancel : le 1er Ctrl+C / bouton Arrêter pose
                    # _stop_event — sans ce check (présent chez le jumeau
                    # WMTS), l'étape tuilage était ininterruptible et la GUI
                    # escaladait en kill forcé après 15 s.
                    if _stop_event.is_set():
                        raise KeyboardInterrupt("LiDAR tiling interrupted")

                    # Vertical (identique pour toutes les colonnes de la rangée)
                    _, _, _, by1_t = tile_bounds(tx0, ty, z)
                    py_off  = int((_w_orig_y - by1_t) / _w_res)
                    py_clip = max(0, py_off)
                    py_end  = min(_w_height, py_off + int(_tile_px))
                    if py_end <= py_clip:
                        # Rangée entièrement hors du TIF (verticalement)
                        rangees_done += 1
                        _progress_rangee()
                        continue
                    out_h = max(1, int((py_end - py_clip) / zoom_factor))
                    dst_y = max(0, int((py_clip - py_off) / zoom_factor))

                    # Offset px du début de rangée (colonne tx0), puis fenêtres
                    # de colonnes contiguës par pas entier de tuiles.
                    px_off_row = int((tile_bounds(tx0, ty, z)[0] - _w_orig_x) / _w_res)

                    for cwx0 in range(tx0, tx1 + 1, _COL_WIN):
                        cwx1 = min(cwx0 + _COL_WIN - 1, tx1)
                        cw_ncols  = cwx1 - cwx0 + 1
                        cw_band_w = cw_ncols * TILE_SIZE
                        px_off = px_off_row + int((cwx0 - tx0) * _tile_px)
                        px_clip = max(0, px_off)
                        px_end  = min(_w_width, px_off + int(cw_band_w * zoom_factor))
                        if px_end <= px_clip:
                            continue   # fenêtre de colonnes hors du TIF (bord)

                        try:
                            # Lecture directe à la résolution tuile (out_shape).
                            win_w = px_end - px_clip
                            out_w = max(1, int(win_w / zoom_factor))
                            win = _Win(px_clip, py_clip, win_w, py_end - py_clip)
                            arr = _ds.read(window=win,
                                           out_shape=(_w_count, out_h, out_w),
                                           resampling=_rio.enums.Resampling.bilinear)
                            dst_x = max(0, int((px_clip - px_off) / zoom_factor))
                            canvas = _np.zeros(
                                (_w_count, TILE_SIZE, cw_band_w), dtype=_np.uint8)
                            canvas[:, dst_y:dst_y+arr.shape[1],
                                      dst_x:dst_x+arr.shape[2]] = arr
                            # R1#7 : masque de couverture (255 = pixel issu de la
                            # source, 0 = padding hors emprise). Il décide par
                            # tuile JPEG plein vs PNG transparent, et fournit le
                            # canal alpha des tuiles partielles.
                            if _w_count >= 4:
                                # Source RGBA : son propre alpha porte DÉJÀ la
                                # géométrie (canvas parti de zéros → padding = 0),
                                # inutile de le recombiner avec le masque.
                                alpha_band = canvas[3]
                            else:
                                alpha_band = _np.zeros(
                                    (TILE_SIZE, cw_band_w), dtype=_np.uint8)
                                alpha_band[dst_y:dst_y+arr.shape[1],
                                           dst_x:dst_x+arr.shape[2]] = 255
                            if _ds_cov is not None:
                                # Coins hors de la vraie empreinte pivotée
                                # (cf. warped_cov) : intersection avec le
                                # masque ci-dessus, PAS un remplacement — les
                                # deux exclusions (géométrie de fenêtre, hors
                                # empreinte réelle) sont indépendantes.
                                _cov_arr = _ds_cov.read(
                                    1, window=win, out_shape=(out_h, out_w),
                                    resampling=_rio.enums.Resampling.nearest)
                                _cov_canvas = _np.zeros(
                                    (TILE_SIZE, cw_band_w), dtype=_np.uint8)
                                _cov_canvas[dst_y:dst_y+_cov_arr.shape[0],
                                           dst_x:dst_x+_cov_arr.shape[1]] = _cov_arr
                                alpha_band = _np.minimum(alpha_band, _cov_canvas)
                            # Contenu SANS alpha : monobande conservée en "L" (PNG
                            # grayscale 2-3× plus petit), sinon RGB. Plus de
                            # composite gris JPEG pour la source RGBA : une tuile
                            # partielle sort désormais en PNG alpha, une tuile
                            # pleine est opaque (rien à composer).
                            if _w_count >= 3:
                                band_img = Image.fromarray(
                                    _np.moveaxis(canvas[:3], 0, 2))
                            else:
                                band_img = Image.fromarray(canvas[0])
                            alpha_img = Image.fromarray(alpha_band, "L")
                        except Exception as _e_read:
                            nb_echecs_tr += 1
                            if nb_echecs_tr <= 3:
                                print(f"\n  ⚠ rasterio read failure z{z} ty={ty}"
                                      f" cols {cwx0}-{cwx1}: {_e_read}", flush=True)
                            continue

                        # Découpe + encodage (Pillow libère le GIL → ThreadPool ;
                        # séquentiel sous _MIN_PAR_TILES tuiles). R1#7 : une tuile
                        # dont la couverture ne remplit pas les 256×256 sort en
                        # PNG alpha (padding transparent) ; une tuile pleine garde
                        # le format de base. Le cull getbbox (tuile entièrement
                        # vide) est inchangé.
                        _tiles_args = []
                        for i, tx in enumerate(range(cwx0, cwx1 + 1)):
                            left = i * TILE_SIZE
                            tile = band_img.crop((left, 0, left + TILE_SIZE, TILE_SIZE))
                            if tile.getbbox() is None:
                                continue
                            atile = alpha_img.crop(
                                (left, 0, left + TILE_SIZE, TILE_SIZE))
                            if atile.getextrema()[0] < 255:
                                _tiles_args.append((tile, atile, z, tx, ty))
                                if _use_jpeg:
                                    _emitted_partial = True
                            else:
                                _tiles_args.append((tile, None, z, tx, ty))

                        if _pool is not None and len(_tiles_args) >= _MIN_PAR_TILES:
                            for _res in _pool.map(_encode_tile, _tiles_args):
                                batch.append(_res)
                                total_insere += 1
                        else:
                            for _args in _tiles_args:
                                batch.append(_encode_tile(_args))
                                total_insere += 1
                        band_img.close()
                        alpha_img.close()

                        if len(batch) >= BATCH:
                            cur.executemany(
                                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
                            con.commit()
                            batch.clear()

                    # Fin de RANGÉE : progression par rangée (comme avant).
                    rangees_done += 1
                    _progress_rangee()

        if batch:
            cur.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con.commit()
            batch.clear()

        if _ds_cov is not None:
            _ds_cov.close()

        # warped conservé dans dossier_ville/ pour réutilisation future
        taille_w = warped.stat().st_size / 1e6 if warped.exists() else 0
        print(f"  Tiling cache kept: {warped.name}  ({taille_w:.0f} MB)"
              f", delete it manually if not needed")

    try:
        _tuiler_source()
    except BaseException:
        # Miroir du finally du jumeau WMTS (ce chemin n'en avait pas) : sur
        # exception/interruption, fermer la connexion AVANT unlink (Windows
        # verrouille un fichier ouvert), jeter le .part (un .mbtiles ne doit
        # exister que complet) et libérer le pool d'encodage.
        try: con.close()
        except Exception: pass
        if _pool is not None:
            _pool.shutdown(wait=True)
        _nettoyer_sqlite_part(mbtiles_part)
        raise

    # R1#7 : métadonnée "format" décidée APRÈS coup. Base PNG → 'png'. Base JPEG
    # sans tuile partielle → 'jpg'. Base JPEG AVEC tuiles PNG-alpha (bas zoom /
    # bord) → 'png' : le fichier est mixte, on déclare le format alpha-capable.
    # Les lecteurs reconnaissent chaque tuile à ses octets magiques (Locus via
    # BitmapFactory, OsmAnd) ; la conversion RMAP ré-encode par sniff et
    # SQLiteDB recopie tel quel — le champ n'est qu'un indice de contenu.
    _fmt_final = "png" if (not _use_jpeg or _emitted_partial) else "jpg"
    try:
        cur.execute("INSERT INTO metadata VALUES ('format', ?)", (_fmt_final,))
        con.commit()
        con.close()
    except BaseException:
        try: con.close()
        except Exception: pass
        if _pool is not None:
            _pool.shutdown(wait=True)
        _nettoyer_sqlite_part(mbtiles_part)
        raise
    if _pool is not None:
        _pool.shutdown(wait=True)

    # #3 — invariant "artefact présent = complet" (miroir WMTS) : NE PAS publier
    # un mbtiles troué (rangées rasterio en échec) ni vide depuis une source non
    # triviale (warp raté ou bbox introuvable laissent 0 tuile ; source
    # demi-écrite ; reprojection hors-bbox). On jette le .part et on retourne
    # None -> le caller ne convertit pas, le cache de warp est conservé, un
    # re-run reprend sans re-warper.
    src_size_mb = tif_source.stat().st_size / 1e6 if tif_source.exists() else 0
    if nb_echecs_tr > 0 or (total_insere == 0 and src_size_mb > 1):
        _nettoyer_sqlite_part(mbtiles_part)
        _cause = (f"{nb_echecs_tr} row(s) failed" if nb_echecs_tr
                  else f"0 tiles from {src_size_mb:.0f} MB source")
        print(f"\n  ✗ MBTiles not finalized: {_cause}. "
              f"Rerun to complete (warp cache kept).")
        return None

    # Réouvrir en lecture seule après le close : valide le schéma, le compte
    # exact et l'absence de dépendance à un journal annexe avant publication.
    try:
        _valider_sqlite_part(
            mbtiles_part, {"metadata": None, "tiles": total_insere}
        )
    except BaseException:
        _nettoyer_sqlite_part(mbtiles_part)
        raise

    # Publication atomique après le close (Windows refuse de renommer un handle
    # ouvert et l'ancien livrable doit rester intact jusqu'ici).
    mbtiles_part.replace(mbtiles)
    elapsed = int(time.time() - t0)
    taille_mb = mbtiles.stat().st_size / 1e6 if mbtiles.exists() else 0
    print("\n  z" + str(zoom_min) + "-" + str(zoom_max) + " 100%  " + str(total_insere) + " tiles  " + _hms(elapsed))
    print(f"  {mbtiles.name} : {total_insere} tiles  ({taille_mb:.0f} MB)")
    return mbtiles
