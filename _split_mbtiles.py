"""Découpage postérieur d'un magasin MBTiles en morceaux autonomes."""

from dataclasses import dataclass
import math
import sqlite3


@dataclass(frozen=True)
class DependancesDecoupageMbtiles:
    """Coutures runtime injectées par la façade historique."""

    calculer_sous_zones_priori: object
    chemin_part: object
    nettoyer_sqlite_part: object
    valider_sqlite_part: object
    sqlite_connect: object = sqlite3.connect


def decouper_mbtiles(src_mbtiles, cote_km=0.0, n_morceaux=1, n_cols=0, n_rows=0,
                     dossier=None, ecraser=False, *, dependances):
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

    con = dependances.sqlite_connect(str(src_mbtiles))
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
        sous_zones, mode_desc = dependances.calculer_sous_zones_priori(
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
        chemin_z_part = dependances.chemin_part(chemin_z)
        con_z = dependances.sqlite_connect(str(chemin_z_part))
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
            dependances.nettoyer_sqlite_part(chemin_z_part)
            print(f"  Sub-zone [{i_lat},{i_lon}]: empty - skipped")
            continue

        try:
            dependances.valider_sqlite_part(
                chemin_z_part, {"metadata": None, "tiles": n_tuiles}
            )
        except BaseException:
            dependances.nettoyer_sqlite_part(chemin_z_part)
            raise
        chemin_z_part.replace(chemin_z)
        print(f"  Sub-zone [{i_lat},{i_lon}]: {n_tuiles:,} tiles → {chemin_z.name}")
        sorties.append(chemin_z)

    con.close()
    return sorties
