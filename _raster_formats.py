"""Conversions des cartes MBTiles vers RMAP et SQLiteDB.

Le module contient les algorithmes de conversion et leur orchestration. Les
services de publication atomique et les façades historiques sont injectés par
``lidar2map``, ce qui garde ce module indépendant du monolithe.
"""

from __future__ import annotations

import io
import math
import sqlite3
import struct
import time
import unicodedata


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

def _blob_vers_jpeg(blob, quality=85):
    """Convertit un blob de tuile en JPEG si besoin. Le format RMAP CompeGPS/
    TwoNav ne stocke QUE du JPEG (offsets nommés jpegOffsets, tag 7) : recopier
    un PNG (reliefs LRM/SVF/RRIM) tel quel produit un RMAP illisible (R2#7).

    - déjà JPEG (magic FF D8 FF) → renvoyé inchangé (chemin rapide, pas de
      décodage : les sources JPEG scan25/ortho ne paient rien) ;
    - PNG/autre → décodé via PIL puis ré-encodé ; l'alpha est aplati sur le gris
      des tuiles vides (JPEG n'a pas de canal alpha) ;
    - indécodable → None (l'appelant substitue la tuile vide).
    """
    if blob[:3] == b'\xff\xd8\xff':       # déjà JPEG : rien à faire
        return blob
    try:
        from PIL import Image as _Img
        img = _Img.open(io.BytesIO(blob))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            fond = _Img.new("RGB", img.size, (180, 180, 180))
            fond.paste(img, mask=img.split()[-1])   # alpha comme masque
            img = fond
        else:
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return None


# ── Fonction principale ────────────────────────────────────────────────────────

def generer_rmap_depuis_mbtiles(
    mbtiles_path,
    ecraser=False,
    *,
    chemin_part,
    formater_duree,
    seuil_rmap_padding,
    pack_int32,
    pack_int64,
    tile_to_geo,
    empty_jpeg,
    blob_vers_jpeg,
    build_map_info,
):
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
    # Pas d'unlink de l'ancien rmap ici : rmap_part.replace(rmap) l'écrase
    # atomiquement en fin de génération. Le supprimer maintenant ferait perdre
    # le livrable précédent si la régénération échoue (le .part est jeté).
    if not mbtiles_path.exists():
        print(f"  ERROR: {mbtiles_path.name} not found")
        return None

    print(f"  RMAP ← {mbtiles_path.name}...", flush=True)
    t0 = time.time()

    # Écriture via .part + rename : un .rmap présent est toujours complet
    # (un Ctrl+C mi-écriture laissait un binaire tronqué "already present").
    rmap_part = chemin_part(rmap)

    EMPTY_JPEG = empty_jpeg()
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
        lon_min, lat_min, lon_max, lat_max = tile_to_geo(
            zd['x0'], zd['y0'] + zd['ny'] - 1, z_max)
        lon_max = tile_to_geo(zd['x0'] + zd['nx'] - 1, zd['y0'], z_max)[2]
        lat_max = tile_to_geo(zd['x0'], zd['y0'], z_max)[3]

        total_tiles = sum(zm[z]['nx'] * zm[z]['ny'] for z in zooms)

        # R2#9 — garde-fou couverture clairsemée : le format RMAP impose une
        # grille rectangulaire DENSE (chaque position du rectangle min-max
        # existe, remplie par EMPTY_JPEG). Sur une couverture clairsemée
        # (département en diagonale, bande côtière, couche historique), nx*ny
        # explose en positions quasi-vides : l'array d'offsets et le header
        # sont alloués en 8*nx*ny octets (pic RAM), et des millions de tuiles
        # vides sont écrites (disque + temps mur). Ce n'est PAS rendable
        # clairsemé sans casser le format. On refuse quand le remplissage est
        # pathologique (beaucoup de vide ET moins de la moitié réelle) et on
        # renvoie vers .mbtiles / .sqlitedb qui, eux, ne stockent que le réel.
        n_reel = con.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        n_vide = total_tiles - n_reel
        if n_vide >= seuil_rmap_padding and n_reel * 2 < total_tiles:
            _go = n_vide * (len(EMPTY_JPEG) + 8) / 1e9
            print(f"\n  ✗ RMAP refused: coverage too sparse ({n_reel:,} real "
                  f"tiles for {total_tiles:,} rectangle positions). RMAP needs a "
                  f"dense grid: it would pad {n_vide:,} empty tiles "
                  f"(~{_go:.1f} GB). Use .mbtiles or .sqlitedb (they store only "
                  f"real tiles), or tighten --zone-bbox.", flush=True)
            return None

        print(f"  {n_zooms} zoom(s), {total_tiles:,} tile positions", flush=True)

        # ── Phase 2 : écriture séquentielle — offsets enregistrés à la volée ──
        zoom_hdr_offset = {}
        _n_reenc     = 0   # tuiles PNG ré-encodées en JPEG (R2#7)
        _n_illisible = 0   # tuiles indécodables remplacées par la tuile vide

        largeur = 30
        done    = 0

        try:
            with open(str(rmap_part), 'wb') as f:

                # --- FILE HEADER placeholder ---
                f.write(b'CompeGPSRasterImage')
                f.write(pack_int32(10)); f.write(pack_int32(7)); f.write(pack_int32(0))
                f.write(pack_int32(w_max)); f.write(pack_int32(-h_max))
                f.write(pack_int32(24)); f.write(pack_int32(1))
                f.write(pack_int32(TILE_SZ)); f.write(pack_int32(TILE_SZ))
                map_data_off_pos = f.tell()
                f.write(pack_int64(0))
                f.write(pack_int32(0))
                f.write(pack_int32(n_zooms))
                zoom_off_arr_pos = f.tell()
                for _ in zooms:
                    f.write(pack_int64(0))

                # --- ZOOM HEADERS + TILE DATA ---
                from array import array as _array
                for z in zooms:
                    zd = zm[z]
                    nx, ny = zd['nx'], zd['ny']

                    # FUSION SÉQUENTIELLE curseur SQL ↔ balayage de grille :
                    # l'ordre d'écriture (tx externe, ty interne = colonne
                    # ascendante, y_xyz ascendant = tile_row TMS DESCENDANT)
                    # correspond exactement à ORDER BY tile_column, tile_row
                    # DESC. Remplace le dict {(col,row): blob} qui chargeait
                    # TOUS les JPEG du zoom en RAM (plusieurs Go au niveau
                    # départemental z18) — désormais un seul blob à la fois.
                    cur_t = con.execute(
                        "SELECT tile_column, tile_row, tile_data FROM tiles "
                        "WHERE zoom_level=? "
                        "ORDER BY tile_column ASC, tile_row DESC", (z,))
                    suivant = cur_t.fetchone()

                    zoom_hdr_offset[z] = f.tell()
                    f.write(pack_int32(zd['w'])); f.write(pack_int32(-zd['h']))
                    f.write(pack_int32(zd['nx'])); f.write(pack_int32(zd['ny']))
                    tile_hdr_pos = f.tell()
                    for _ in range(nx * ny):
                        f.write(pack_int64(0))

                    # Offsets en array('q') indexé tx*ny+ty : ~8 octets par
                    # position au lieu d'un dict {(tx,ty): int} (~200 octets
                    # par entrée, ~150 Mo au niveau départemental).
                    offs = _array("q", bytes(8 * nx * ny))

                    for tx in range(nx):
                        col = zd['x0'] + tx
                        for ty in range(ny):
                            y_xyz = zd['y0'] + ty
                            y_tms = (1 << z) - 1 - y_xyz

                            # Défensif : sauter d'éventuelles lignes "derrière"
                            # le balayage (ne devrait pas arriver, l'étendue
                            # couvre toutes les tuiles du zoom).
                            while suivant is not None and (
                                    suivant[0] < col
                                    or (suivant[0] == col and suivant[1] > y_tms)):
                                suivant = cur_t.fetchone()
                            if (suivant is not None and suivant[0] == col
                                    and suivant[1] == y_tms):
                                _blob = suivant[2]
                                suivant = cur_t.fetchone()
                                # RMAP = JPEG uniquement : un PNG (relief) doit
                                # être ré-encodé, sinon TwoNav ne lit pas (R2#7).
                                if _blob[:3] == b'\xff\xd8\xff':
                                    jpeg = _blob
                                else:
                                    jpeg = blob_vers_jpeg(_blob)
                                    if jpeg is None:
                                        jpeg = EMPTY_JPEG
                                        _n_illisible += 1
                                    else:
                                        _n_reenc += 1
                            else:
                                jpeg = EMPTY_JPEG

                            offs[tx * ny + ty] = f.tell()
                            f.write(pack_int32(7))
                            f.write(pack_int32(len(jpeg)))
                            f.write(jpeg)

                            done += 1
                            if done % 500 == 0 or done == total_tiles:
                                pct  = done * 100 // max(total_tiles, 1)
                                bars = pct * largeur // 100
                                elapsed = int(time.time() - t0)
                                print(f"\r  RMAP z{z} [{'█'*bars}{'░'*(largeur-bars)}]"
                                      f" {pct:3d}%  {done:,}/{total_tiles:,}"
                                      f"  {formater_duree(elapsed)}",
                                      end="", flush=True)

                    # --- RÉÉCRIRE le zoom header avec les vrais offsets ---
                    pos_after = f.tell()
                    f.seek(tile_hdr_pos)
                    for ty in range(ny):
                        for tx in range(nx):
                            f.write(pack_int64(offs[tx * ny + ty]))
                    f.seek(pos_after)

                # --- MAP INFO ---
                map_data_offset = f.tell()
                map_text = build_map_info(
                    mbtiles_path.name, w_max, h_max,
                    lon_min, lat_min, lon_max, lat_max)
                # 'replace' en défense : _build_map_info translittère déjà le
                # nom (R2#10), le bloc restant est 100 % ASCII littéral + chiffres.
                map_bytes = map_text.encode('ascii', 'replace')
                f.write(pack_int32(1))
                f.write(pack_int32(len(map_bytes)))
                f.write(map_bytes)

                # --- RÉÉCRIRE FILE HEADER avec vrais offsets ---
                f.seek(map_data_off_pos)
                f.write(pack_int64(map_data_offset))

                f.seek(zoom_off_arr_pos)
                for z in zooms:
                    f.write(pack_int64(zoom_hdr_offset[z]))

        except Exception as e:
            print(f"\n  ERROR RMAP: {e}")
            import traceback; traceback.print_exc()
            rmap_part.unlink(missing_ok=True)
            return None

        rmap_part.replace(rmap)
        elapsed   = int(time.time() - t0)
        taille_mo = rmap.stat().st_size / 1e6
        print(f"\n  {rmap.name} : {taille_mo:.0f} MB  {formater_duree(elapsed)}")
        if _n_reenc:
            print(f"  Note: {_n_reenc:,} PNG tile(s) re-encoded to JPEG "
                  f"(RMAP is a JPEG-only format; some quality loss expected)")
        if _n_illisible:
            print(f"  WARNING: {_n_illisible:,} undecodable tile(s) replaced by blank")
        return rmap
    finally:
        # Garantit la fermeture de la connexion SQLite même sur exception
        # non capturée (KeyboardInterrupt, MemoryError, disque plein…).
        try: con.close()
        except Exception: pass

def _sqlitedb_schema_courant(path):
    """True si le .sqlitedb a le schéma courant (colonne info.tilenumbering,
    ajoutée avec le fix OsmAnd). Un fichier illisible ou plus ancien → False,
    donc régénéré. Sert à ne pas laisser un overlay périmé après mise à jour."""
    try:
        con = sqlite3.connect(str(path))
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(info)")]
        finally:
            con.close()
        return "tilenumbering" in cols
    except Exception:
        return False


def generer_sqlitedb_depuis_mbtiles(
    mbtiles_path,
    ecraser=False,
    *,
    chemin_part,
    nettoyer_sqlite_part,
    valider_sqlite_part,
    batch_sqlitedb_insert,
    formater_duree,
    schema_courant,
):
    """
    Génère un fichier .sqlitedb (cible OsmAnd) depuis un .mbtiles.

    Schéma SQLiteDB (variante OsmAnd : schéma RMaps + colonne tilenumbering) :
      CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB)
      CREATE TABLE android_metadata (locale TEXT)
      CREATE TABLE info (minzoom INT, maxzoom INT, tilenumbering TEXT)

    Coordonnées : x=col, y=row XYZ (y=0 en haut/Nord), z=zoom, s=0 (inutilisé).
    Conversion TMS→XYZ : y_xyz = (2^z - 1) - tile_row_tms.

    CIBLE OsmAnd, pas Locus. Locus attend la numérotation RMaps et refuse ce
    fichier (entrée grisée dans le gestionnaire de cartes) : pour Locus on livre
    le MBTiles (universel, lu nativement).

    tilenumbering='simple' : indispensable pour OsmAnd. Quand la colonne est
    absente, OsmAnd (SQLiteTileSource) suppose le schéma BigPlanet à zoom
    INVERSÉ (z' = 17 - z) et ne trouve donc jamais nos tuiles (couche
    sélectionnable mais vide). 'simple' = numérotation XYZ normale.
    """

    sqlitedb = mbtiles_path.with_suffix(".sqlitedb")
    if sqlitedb.exists() and not ecraser:
        # Ne pas garder un fichier au schéma périmé : un sqlitedb généré AVANT le
        # fix tilenumbering serait "already present" et jamais remplacé, laissant
        # l'utilisateur avec un overlay vide dans OsmAnd après mise à jour. On
        # régénère si la colonne info.tilenumbering manque (migration transparente,
        # sans exiger "Écraser" ni supprimer le fichier à la main).
        if schema_courant(sqlitedb):
            print(f"  {sqlitedb.name} → already present")
            return sqlitedb
        print(f"  {sqlitedb.name} → stale schema (no tilenumbering), regenerating")
    # Pas d'unlink de l'ancien sqlitedb ici (schéma périmé OU écrasement) :
    # sqlitedb_part.replace(sqlitedb) l'écrase atomiquement en fin de
    # génération. Le supprimer maintenant perdrait le livrable si la
    # régénération échoue (le .part est jeté).
    if not mbtiles_path.exists():
        print(f"  ERROR: {mbtiles_path.name} not found")
        return None

    # Écriture via .part + rename : un .sqlitedb présent est toujours complet.
    sqlitedb_part = chemin_part(sqlitedb)

    con_mb = sqlite3.connect(str(mbtiles_path))
    con_db = None
    try:
        meta = {}
        try:
            meta = dict(con_mb.execute("SELECT name, value FROM metadata").fetchall())
        except Exception:
            pass
        total = con_mb.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        # R2#11 : ne PAS publier un sqlitedb VIDE comme un succès. 0 tuile =
        # overlay grisé/vide dans OsmAnd sous couvert d'un « ok » (et livrable
        # trompeur). On refuse ; le finally ferme con_mb.
        if total == 0:
            print(f"  ERROR: {mbtiles_path.name} has 0 tiles - empty sqlitedb not written")
            return None
        # R2#11 : zooms LUS des tuiles quand les métadonnées manquent. Avant :
        # 0/17 arbitraire → OsmAnd déclare une plage inexistante et ne trouve
        # jamais les tuiles (couche sélectionnable mais vide).
        if "minzoom" in meta and "maxzoom" in meta:
            zoom_min = int(meta["minzoom"]); zoom_max = int(meta["maxzoom"])
        else:
            _zr = con_mb.execute(
                "SELECT MIN(zoom_level), MAX(zoom_level) FROM tiles").fetchone()
            zoom_min, zoom_max = int(_zr[0]), int(_zr[1])

        print(f"  SQLiteDB ← {mbtiles_path.name}  ({total:,} tiles)...", flush=True)
        t0 = time.time()

        con_db = sqlite3.connect(str(sqlitedb_part))
        con_db.execute("PRAGMA journal_mode=MEMORY;")
        con_db.execute("PRAGMA synchronous=OFF;")    # .part jeté sur échec
        con_db.executescript("""
            CREATE TABLE tiles (x INT, y INT, z INT, s INT, image BLOB);
            CREATE TABLE android_metadata (locale TEXT);
            CREATE TABLE info (minzoom INT, maxzoom INT, tilenumbering TEXT);
            CREATE UNIQUE INDEX idx_tiles ON tiles (x, y, z, s);
        """)
        con_db.execute("INSERT INTO android_metadata VALUES (?)", ("fr_FR",))
        con_db.execute("INSERT INTO info VALUES (?, ?, ?)",
                       (zoom_min, zoom_max, "simple"))
        con_db.commit()

        BATCH   = batch_sqlitedb_insert
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
                          f" {pct:3d}%  {done:,}/{total:,}  {formater_duree(elapsed)}",
                          end="", flush=True)
            if batch:
                con_db.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?,?)", batch)
                con_db.commit()
        except Exception as e:
            print(f"\n  ERROR SQLiteDB: {e}")
            # Fermer AVANT unlink : sous Windows, supprimer un fichier SQLite
            # encore ouvert lève PermissionError et masquerait l'erreur d'origine.
            try: con_db.close()
            except Exception: pass
            nettoyer_sqlite_part(sqlitedb_part)
            return None

        elapsed   = int(time.time() - t0)
        # Fermer puis rouvrir en lecture seule pour valider le staging complet.
        try: con_db.close()
        except Exception: pass
        valider_sqlite_part(
            sqlitedb_part,
            {"tiles": total, "android_metadata": 1, "info": 1},
        )
        sqlitedb_part.replace(sqlitedb)
        taille_mo = sqlitedb.stat().st_size / 1e6
        print(f"\n  {sqlitedb.name} : {done:,} tiles  ({taille_mo:.0f} MB)"
              f"  {formater_duree(elapsed)}          ")
        return sqlitedb
    finally:
        # Toujours fermer les deux connexions, même sur exception non capturée.
        try: con_mb.close()
        except Exception: pass
        if con_db is not None:
            try: con_db.close()
            except Exception: pass
        # Sur exception/interruption ou retour d'échec, seul le staging existe.
        # Après succès replace() l'a déplacé, donc ce nettoyage est un no-op.
        nettoyer_sqlite_part(sqlitedb_part)


def _build_map_info(bitmap_name, width, height, lon_min, lat_min, lon_max, lat_max):
    """Génère le bloc texte CompeGPS MAP (calibration géographique)."""
    # Le bloc MAP est écrit en ASCII (map_text.encode('ascii') côté appelant).
    # Un nom de MBTiles accentué ou non-latin (ex. "forêt", nom cyrillique) fait
    # crasher toute la génération RMAP par UnicodeEncodeError (R2#10). Le champ
    # Bitmap= n'est qu'une référence d'affichage : on le translittère en ASCII
    # (é→e via NFKD, le reste éliminé) plutôt que de perdre le livrable.
    bitmap_name = (unicodedata.normalize("NFKD", str(bitmap_name))
                   .encode("ascii", "ignore").decode("ascii")) or "map"
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

def _convertir_un_mbtiles(
    sf,
    args,
    mbtiles_neuf=True,
    *,
    generer_rmap,
    generer_sqlitedb,
):
    """Génère RMAP/SQLiteDB depuis un MBTiles.

    mbtiles_neuf=True : MBTiles fraîchement généré dans cette exécution.
        S'il n'a pas été demandé via --formats-fichier, il est traité comme
        intermédiaire et removed après conversion.
    mbtiles_neuf=False : MBTiles préexistant sur disque (run précédent ou
        copié manuellement). JAMAIS removed — on respecte le travail de
        l'utilisateur, même si seul --rmap/--sqlitedb a été demandé.

    Livrables finaux (rmap/sqlitedb) régénérés d'office : cocher le format =
    "je veux ce fichier à jour". Sinon un ancien fichier resterait "already
    present" (schéma périmé, contenu obsolète) alors que le mbtiles source a
    pu changer. Le coûteux (tuilage mbtiles) reste caché en amont
    (_mbtiles_a_regenerer) ; "Écraser le fichier résultat" ne pilote plus que lui.
    """
    # Capturer les retours : les convertisseurs renvoient None SUR ÉCHEC.
    # L'ancien code les ignorait puis supprimait le mbtiles -> sur un échec
    # de conversion l'utilisateur perdait À LA FOIS la source ET les livrables.
    ok = True
    if args.rmap:
        ok = (generer_rmap(sf, ecraser=True) is not None) and ok
    if args.sqlitedb:
        ok = (generer_sqlitedb(sf, ecraser=True) is not None) and ok
    # Ne supprimer la source que si TOUTES les conversions demandées ont réussi.
    if mbtiles_neuf and not args.mbtiles and sf.exists():
        if ok:
            sf.unlink()
            print(f"  MBTiles removed: {sf.name}")
        else:
            print(f"  MBTiles kept (conversion failed): {sf.name}")
    return ok



def _convertir_formats(
    mbt_out,
    args,
    decoupe_sortie=True,
    mbtiles_neuf=True,
    *,
    decouper,
    convertir_un,
):
    """
    Applique le découpage (grille cols×rows ou split_width) puis génère
    RMAP/SQLiteDB pour chaque fichier résultant.
    Supprime le MBTiles source uniquement s'il a été généré dans cette
    exécution (mbtiles_neuf=True) ET non demandé via --formats-fichier.
    decoupe_sortie=False → saute le découpage (mode morceau à priori).
    """
    if not mbt_out:
        return False

    r_dec  = getattr(args, "split_width", 0.0)
    n_cols = getattr(args, "cols_decoupe",  0)
    n_rows = getattr(args, "rows_decoupe",  0)

    # En mode morceau à priori : pas de re-découpage
    if not decoupe_sortie:
        return convertir_un(
            mbt_out, args, mbtiles_neuf=mbtiles_neuf)

    if n_cols > 0 and n_rows > 0:
        sous_fichiers = decouper(mbt_out, n_cols=n_cols, n_rows=n_rows,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if not sous_fichiers:
            return False
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            # Découpage effectif : la source globale n'est gardée que si l'utilisateur
            # l'a demandée OU si elle préexistait. Les sous-fichiers, eux, sont
            # toujours frais (sortie du découpage).
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  Source MBTiles removed: {mbt_out.name}")
        conversions_ok = True
        for sf in sous_fichiers:
            conversions_ok = (convertir_un(
                sf, args, mbtiles_neuf=True) and conversions_ok)
        return conversions_ok
    elif r_dec > 0:
        sous_fichiers = decouper(mbt_out, cote_km=r_dec,
                                         dossier=mbt_out.parent,
                                         ecraser=args.tuiles_ecraser)
        if not sous_fichiers:
            return False
        if mbt_out.exists() and sous_fichiers and sous_fichiers != [mbt_out]:
            if mbtiles_neuf and not args.mbtiles:
                mbt_out.unlink()
                print(f"  Source MBTiles removed: {mbt_out.name}")
        conversions_ok = True
        for sf in sous_fichiers:
            conversions_ok = (convertir_un(
                sf, args, mbtiles_neuf=True) and conversions_ok)
        return conversions_ok
    else:
        # Pas de découpage : on convertit directement le fichier passé
        return convertir_un(
            mbt_out, args, mbtiles_neuf=mbtiles_neuf)


__all__ = (
    "_blob_vers_jpeg",
    "_build_map_info",
    "_convertir_formats",
    "_convertir_un_mbtiles",
    "_empty_jpeg_256",
    "_sqlitedb_schema_courant",
    "_tile_to_geo",
    "_wi",
    "_wl",
    "generer_rmap_depuis_mbtiles",
    "generer_sqlitedb_depuis_mbtiles",
)
