"""Fusion a posteriori de plusieurs magasins MBTiles en un seul."""

from dataclasses import dataclass
import io
import sqlite3
import sys


def _a_de_la_transparence(image):
    """Vrai si l'image décodée porte au moins un pixel non opaque."""
    if image.mode not in ("RGBA", "LA", "PA") and "transparency" not in image.info:
        return False
    alpha = image.convert("RGBA").getchannel("A")
    return alpha.getextrema()[0] < 255


def composer_tuiles(dessous, dessus):
    """Octets de la tuile fusionnée quand deux sources ont le même (z, x, y).

    Le tuileur LiDAR émet volontairement les tuiles de bord et de bas zoom
    d'un bloc en PNG à alpha nul hors emprise (R1#7), pour qu'elles se
    COMPOSENT avec celles du bloc voisin. Remplacer l'une par l'autre
    (INSERT OR REPLACE) trouait la fusion le long de chaque frontière de
    bloc, et ne gardait qu'un fragment par tuile aux bas zooms.

    ``dessus`` (source plus loin dans la liste) est donc posé par-dessus
    ``dessous`` quand il porte de la transparence. Opaque, illisible (ou
    Pillow absent) : règle historique, la dernière source gagne.
    """
    try:
        from PIL import Image
    except ImportError:
        return dessus
    try:
        with Image.open(io.BytesIO(dessus)) as image_haut:
            if not _a_de_la_transparence(image_haut):
                return dessus
            haut = image_haut.convert("RGBA")
        with Image.open(io.BytesIO(dessous)) as image_bas:
            bas = image_bas.convert("RGBA")
    except Exception:
        return dessus
    if bas.size != haut.size:
        return dessus
    bas.alpha_composite(haut)
    tampon = io.BytesIO()
    bas.save(tampon, "PNG", optimize=False, compress_level=6)
    return tampon.getvalue()


@dataclass(frozen=True)
class DependancesFusionMbtiles:
    """Coutures runtime injectées par la façade historique."""

    chemin_part: object
    nettoyer_sqlite_part: object
    valider_sqlite_part: object
    sqlite_connect: object = sqlite3.connect


def fusionner_mbtiles(sources, sortie, ecraser=False, *, dependances):
    """
    Fusionne plusieurs MBTiles sources en un seul fichier.

    Toutes les sources doivent partager le même format de tuile (jpeg/png/
    webp) : un mbtiles mélangeant les formats n'est pas un contrat MBTiles
    valide (le lecteur lit 'format' une fois en metadata, pas tuile par
    tuile).

    Bounds/zoom de sortie = union des sources. Tuile en collision entre deux
    sources (zones qui se chevauchent, frontières de blocs) : la DERNIÈRE
    source de la liste gagne si sa tuile est opaque ; si elle porte de la
    transparence (bord de bloc, bas zoom), elle est composée par-dessus
    l'existante (cf. composer_tuiles).

    Retourne le Path de sortie, ou None si rien à fusionner.
    """
    if not sources:
        print("  ERROR: no source file to merge")
        return None
    if len(sources) == 1:
        print("  Merging: single source -> nothing to merge")
        return sources[0]

    manquants = [s for s in sources if not s.exists()]
    if manquants:
        print("  ERROR: source(s) not found: "
              + ", ".join(str(m) for m in manquants))
        return None

    if sortie.exists() and not ecraser:
        print(f"  Existing output: {sortie.name} - skipped")
        return sortie

    metas = []
    for src in sources:
        con = dependances.sqlite_connect(str(src))
        meta = dict(con.execute("SELECT name, value FROM metadata").fetchall())
        zr = con.execute(
            "SELECT MIN(zoom_level), MAX(zoom_level) FROM tiles").fetchone()
        n_src = con.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        con.close()
        metas.append((src, meta, zr, n_src))

    formats = {meta.get("format", "jpeg") for _, meta, _, _ in metas}
    if len(formats) > 1:
        print("  ERROR: mixed tile formats across sources: "
              + ", ".join(sorted(formats)))
        return None
    fmt = formats.pop()

    zr_valides = [zr for _, _, zr, _ in metas if zr and zr[0] is not None]
    if not zr_valides:
        print("  ERROR: no source contains any tile")
        return None
    zoom_min = min(z[0] for z in zr_valides)
    zoom_max = max(z[1] for z in zr_valides)

    bounds_tous = []
    for _, meta, _, _ in metas:
        if "bounds" in meta:
            bounds_tous.append(tuple(float(v) for v in meta["bounds"].split(",")))
    if bounds_tous:
        lon0 = min(b[0] for b in bounds_tous)
        lat0 = min(b[1] for b in bounds_tous)
        lon1 = max(b[2] for b in bounds_tous)
        lat1 = max(b[3] for b in bounds_tous)
    else:
        lon0, lat0, lon1, lat1 = -180.0, -85.0, 180.0, 85.0

    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie_part = dependances.chemin_part(sortie)
    con_out = dependances.sqlite_connect(str(sortie_part))
    # Écritures rapides SANS risque : la cible est un .part, jeté sur échec
    # (au pire un crash OS laisse un .part corrompu, purgé au run suivant).
    con_out.execute("PRAGMA journal_mode=MEMORY;")
    con_out.execute("PRAGMA synchronous=OFF;")
    con_out.executescript("""
        CREATE TABLE metadata (name TEXT, value TEXT);
        CREATE TABLE tiles   (zoom_level INTEGER, tile_column INTEGER,
                              tile_row INTEGER, tile_data BLOB);
        CREATE UNIQUE INDEX idx_tiles ON tiles (zoom_level, tile_column, tile_row);
    """)

    # Métadonnées reprises de la PREMIÈRE source (attribution, licence, type
    # vecteur json...), puis surchargées par les valeurs calculées pour
    # l'union (même logique que le découpage post-hoc).
    _, meta_base, _, _ = metas[0]
    meta_fusion = dict(meta_base)
    meta_fusion.setdefault("type", "overlay")
    meta_fusion.setdefault("version", "1.0")
    meta_fusion.setdefault("description", "")
    cx = (lon0 + lon1) / 2
    cy = (lat0 + lat1) / 2
    meta_fusion.update({
        "name":    sortie.stem,
        "format":  fmt,
        "minzoom": str(zoom_min),
        "maxzoom": str(zoom_max),
        "bounds":  f"{lon0:.6f},{lat0:.6f},{lon1:.6f},{lat1:.6f}",
        "center":  f"{cx:.6f},{cy:.6f},{zoom_max}",
    })
    for k, v in meta_fusion.items():
        con_out.execute("INSERT INTO metadata VALUES (?,?)", (k, str(v)))
    con_out.commit()

    # Copie par lot (fetchmany), pas de fetchall RAM (mêmes gardes que le
    # découpage post-hoc sur un mbtiles départemental).
    BATCH = 2000
    total = sum(n for _, _, _, n in metas)
    copies = 0
    pct_precedent = -1
    for src, _, _, _ in metas:
        con_src = dependances.sqlite_connect(str(src))
        cur_src = con_src.execute(
            "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles")
        while True:
            rows = cur_src.fetchmany(BATCH)
            if not rows:
                break
            # Chemin rapide : aucune collision dans le lot (cas général, tout
            # l'intérieur des blocs) -> un seul executemany.
            curseur = con_out.executemany(
                "INSERT OR IGNORE INTO tiles VALUES (?,?,?,?)", rows)
            if curseur.rowcount != len(rows):
                # Collision(s) dans ce lot : la ligne en place diffère de la
                # ligne source exactement pour les tuiles en collision (celles
                # que ce lot vient d'insérer sont identiques).
                for z, x, y, donnees in rows:
                    (en_place,) = con_out.execute(
                        "SELECT tile_data FROM tiles WHERE zoom_level=? "
                        "AND tile_column=? AND tile_row=?", (z, x, y)).fetchone()
                    if en_place != donnees:
                        con_out.execute(
                            "UPDATE tiles SET tile_data=? WHERE zoom_level=? "
                            "AND tile_column=? AND tile_row=?",
                            (composer_tuiles(en_place, donnees), z, x, y))
            con_out.commit()
            copies += len(rows)
            # \r sur le terminal, ligne de progression "en place" dans le
            # panneau de log GUI (même contrat que le download PBF Geofabrik :
            # le lecteur de stdout du GUI reconnaît \r + un motif NN% et pilote
            # la barre de progression sans code GUI supplémentaire).
            if total:
                pct = copies * 100 // total
                if pct >= pct_precedent + 5:
                    pct_precedent = pct
                    sys.stdout.write(f"\r  {copies:,} / {total:,} tiles  {pct}%")
                    sys.stdout.flush()
        con_src.close()
    if total:
        sys.stdout.write("\r" + " " * 40 + "\r")

    n_tuiles = con_out.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    con_out.close()

    if n_tuiles == 0:
        dependances.nettoyer_sqlite_part(sortie_part)
        print("  ERROR: merge produced no tile")
        return None

    try:
        dependances.valider_sqlite_part(
            sortie_part, {"metadata": None, "tiles": n_tuiles}
        )
    except BaseException:
        dependances.nettoyer_sqlite_part(sortie_part)
        raise
    sortie_part.replace(sortie)
    print(f"  Merged {len(sources)} source(s), {n_tuiles:,} tile(s) -> {sortie.name}")
    return sortie
