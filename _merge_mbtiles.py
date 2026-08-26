"""Fusion a posteriori de plusieurs magasins MBTiles en un seul."""

from dataclasses import dataclass
import sqlite3
import sys


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
    sources (zones qui se chevauchent) : la DERNIÈRE source de la liste
    gagne (même règle que le découpage post-hoc, INSERT OR REPLACE).

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
            # Dernière source gagne sur collision (zones qui se chevauchent).
            con_out.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", rows)
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
