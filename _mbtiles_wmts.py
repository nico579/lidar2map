"""Producteur MBTiles pour les couches raster WMTS/XYZ.

Le module contient le téléchargement concurrent, le cache disque par couche,
l'encodage et la publication SQLite atomique du MBTiles. Ses coutures avec
l'application (téléchargement d'une tuile, publication atomique, arrêt
coopératif, constantes de seuil) sont injectées à chaque appel par la façade
``lidar2map``, ce qui évite l'import circulaire et conserve les monkeypatches
historiques des suites de tests.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _DependancesMbtilesWMTS:
    """Coutures entre le producteur WMTS et l'application."""

    chemin_part: Callable
    nettoyer_sqlite_part: Callable
    valider_sqlite_part: Callable
    telecharger_tuile: Callable
    est_image_valide: Callable
    fermer_connexions_wmts: Callable
    log_req: Callable
    formater_duree: Callable
    stop_event: object
    zone_hors_couverture: type
    endpoint_prive: str
    endpoint_public: str
    batch_insert: int
    seuil_err_consec: int
    seuil_hors_couverture: int


def generer_mbtiles_wmts(chemin, tuiles_iter, total, nom_zone, fmt_ext,
                    zoom_min, zoom_max, layer, style, img_fmt,
                    apikey, apikey_requis, workers,
                    bbox_wgs84=None, jpeg_quality=None,
                    dossier_cache=None, ecraser_tuiles=False, ecraser_dalles=False,
                    *, dependances):
    """
    Télécharge toutes les tuiles et les insère dans un fichier MBTiles.

    Convention MBTiles : y en TMS (y=0 en bas) → inversion depuis XYZ.

    jpeg_quality   : si défini et img_fmt est PNG, convertit PNG→JPEG à cette
                     qualité (gain ×3-5 sans double compression).
    dossier_cache  : si défini, les tuiles sont mises en cache sur disque
                     sous dossier_cache/<z>/<x>/<y>.<ext> et réutilisées
                     sans retélécharger lors des runs suivants.
    """
    _chemin_part = dependances.chemin_part
    _nettoyer_sqlite_part = dependances.nettoyer_sqlite_part
    _valider_sqlite_part = dependances.valider_sqlite_part
    telecharger_tuile = dependances.telecharger_tuile
    _est_image_valide = dependances.est_image_valide
    _wmts_close_all_conns = dependances.fermer_connexions_wmts
    _log_req = dependances.log_req
    _hms = dependances.formater_duree
    _stop_event = dependances.stop_event
    WMTS_URL = dependances.endpoint_prive
    WMTS_URL_PUB = dependances.endpoint_public
    BATCH_MBTILES_INSERT = dependances.batch_insert
    SEUIL_ERR_CONSEC = dependances.seuil_err_consec
    SEUIL_HORS_COUVERTURE = dependances.seuil_hors_couverture

    if chemin.exists() and not ecraser_tuiles:
        print(f"  {chemin.name} → already present")
        return chemin
    if chemin.exists() and ecraser_tuiles:
        # Pas d'unlink ici : chemin_part.replace(chemin) écrase atomiquement à
        # la fin. Le supprimer maintenant perdrait le mbtiles précédent si le
        # nouveau run échoue (le .part est jeté).
        print(f"  {chemin.name} → overwrite")

    chemin.parent.mkdir(parents=True, exist_ok=True)

    # Écriture dans un .part renommé à la toute fin : un .mbtiles présent est
    # TOUJOURS complet. Sans ça, un run interrompu (Ctrl+C, stop GUI) laissait
    # un fichier partiel avec >0 tuiles que _mbtiles_a_regenerer prenait pour
    # un fichier valide à la reprise.
    chemin_part = _chemin_part(chemin)

    # Calculer _convert_png ici — utilisé pour _meta_fmt et dans _dl
    _convert_png = (jpeg_quality is not None
                    and img_fmt.lower() in ("image/png", "png"))
    # Downgrade PROPRE si Pillow est absent : garder le PNG natif ET l'étiqueter
    # png (cohérent), au lieu de télécharger tout puis rater chaque conversion.
    # Le cas SYSTÉMATIQUE est neutralisé ici ; il ne reste dans _dl que l'échec
    # SPORADIQUE (une tuile corrompue), qui doit lever et non mentir (R2#15).
    if _convert_png:
        try:
            from PIL import Image as _PILchk  # noqa: F401
        except ImportError:
            print("  WARNING: Pillow unavailable, PNG->JPEG conversion disabled "
                  "(tiles kept as PNG, metadata stays consistent).")
            _convert_png = False
    _meta_fmt    = "jpeg" if _convert_png else fmt_ext

    con = sqlite3.connect(str(chemin_part))
    # Une seule connexion insère les résultats des workers. Le journal reste en
    # mémoire : la base entière est un .part jetable et aucun -wal/-shm ne doit
    # être nécessaire au livrable final.
    con.execute("PRAGMA journal_mode=MEMORY;")
    # synchronous=OFF sans risque : la cible est un .part jeté sur échec.
    con.execute("PRAGMA synchronous=OFF;")
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
    abort_hors_couv = False  # True si l'abort est un hors-couverture (que des 204),
                             # False si panne I/O systémique — pilote le type d'exception.
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

    # ── Namespace du cache par COUCHE (fix collision inter-couches) ───────────
    # Le cache disque cache/ign_raster/ est PARTAGÉ par toutes les couches ;
    # l'ancienne clé était z/x/y(+qualité) SANS layer/style/endpoint/format
    # source. Deux couches au même format sur la même zone (ex. planIGN et
    # cadastre, toutes deux PNG) écrivaient donc le MÊME fichier → tuiles
    # croisées servies en silence. On insère un segment de namespace stable
    # dérivé de (endpoint, layer, style, format serveur). Les tuiles déjà en
    # cache sous l'ancien chemin ne sont pas migrables (on ignore de quelle
    # couche elles viennent, c'est le bug) : elles deviennent orphelines et
    # sont re-téléchargées une fois par couche — coût accepté pour ne plus
    # servir de données fausses. Racine "ign_raster" conservée (legacy).
    _hl_ns = hashlib
    _endpoint = WMTS_URL if apikey_requis else WMTS_URL_PUB
    _ns_key = f"{_endpoint}|{layer}|{style}|{img_fmt}".encode("utf-8")
    _ns_hint = re.sub(r"[^a-z0-9]+", "",
                      ("xyz" if layer.startswith("XYZ:")
                       else layer.split(":")[-1]).lower())[:16] or "layer"
    _cache_ns = f"{_ns_hint}_{_hl_ns.md5(_ns_key).hexdigest()[:8]}"

    # Quand on re-encode PNG→JPEG avec une qualité explicite, le binaire stocké
    # dépend de jpeg_quality. Sans versionner, un changement de --qualite-image
    # réutiliserait silencieusement les tuiles de l'ancienne qualité.
    # Si img_fmt est nativement JPEG (pas de re-encode), le cache ne dépend
    # pas de jpeg_quality (data IGN brute).
    _cache_qual_seg = (f"q{int(jpeg_quality)}"
                       if _convert_png and jpeg_quality is not None else "")

    def _cache_path(z, x, y):
        base = dossier_cache / _cache_ns / str(z) / str(x)
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
                # Cache d'un run buggé : un blob PNG écrit sous un nom .jpeg
                # (ancien fallback silencieux) mentait sur le format. On le
                # rejette pour re-télécharger+convertir proprement (R2#15).
                if _convert_png and data[:3] != b'\xff\xd8\xff':
                    data = None
                # Cache antérieur au garde magic : un blob non-image (HTML/JSON
                # d'erreur mis en cache par un vieux run) serait inséré tel quel
                # → re-télécharger au lieu de le lire (R2#16).
                elif not _est_image_valide(data):
                    data = None
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
                except Exception as _e_conv:
                    # Ne PAS garder le PNG sous un contrat jpeg (métadonnées
                    # format=jpeg + cache .jpeg) : tuile mal étiquetée illisible
                    # pour un lecteur strict. On lève → comptée en 'erreurs'
                    # (drop honnête). Le cas systématique (Pillow absent) est
                    # déjà neutralisé en amont, ne reste que le sporadique (R2#15).
                    raise IOError(f"PNG->JPEG conversion failed for tile "
                                  f"{z}/{x}/{y}: {type(_e_conv).__name__}: "
                                  f"{_e_conv}") from _e_conv
            # Écrire dans le cache — écriture ATOMIQUE (temp + os.replace).
            # Une écriture interrompue (Ctrl+C, crash, disque plein) ne doit pas
            # laisser une tuile tronquée : au run suivant _cache_file.exists()
            # serait vrai et read_bytes() relirait les octets partiels comme une
            # tuile valide → pavé corrompu inséré dans le MBTiles. Miroir du
            # .part + rename du chemin LiDAR (dalles). Pas de collision entre
            # workers : chaque (z,x,y) n'est soumis qu'une fois.
            if data and dossier_cache is not None:
                _cache_file = _cache_path(z, x, y)
                _cache_file.parent.mkdir(parents=True, exist_ok=True)
                # Suffixe PID : le cache est PARTAGÉ entre projets, et deux
                # process lidar2map parallèles peuvent télécharger la même
                # tuile. Un .part de nom fixe serait alors écrit par les deux
                # (l'un tronque pendant que l'autre rename = corruption
                # persistante, exactement ce que l'atomique doit empêcher).
                _cache_tmp = _chemin_part(_cache_file)
                try:
                    _cache_tmp.write_bytes(data)
                    os.replace(_cache_tmp, _cache_file)
                except BaseException:
                    _cache_tmp.unlink(missing_ok=True)
                    raise
                # NB : pas de _creer_fichier ici. Le cache WMTS est PERMANENT
                # par design (partagé entre projets) : --cleanup ne doit pas
                # le vider. L'ancien appel était de toute façon un no-op
                # silencieux (_manifest_ctx est thread-local et _dl tourne
                # dans un worker du pool, jamais dans le main thread).
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

    # Consommation au fil de l'eau : tuiles_iter peut être un générateur
    # (calculer_grille_xyz) — on ne matérialise JAMAIS la liste (dept-scale
    # z18 = millions de tuples). `total` est fourni par l'appelant
    # (compter_tuiles_xyz) pour la barre de progression.
    _tuiles_it = iter(tuiles_iter)
    z_courant  = zoom_min

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Soumission par fenêtre glissante : on ne soumet FENETRE tâches à la fois
            # → la barre démarre immédiatement, RAM bornée même sur 100k tuiles
            pending = {}

            # Remplir la fenêtre initiale
            while len(pending) < FENETRE:
                t = next(_tuiles_it, None)
                if t is None:
                    break
                pending[pool.submit(_dl, t)] = t

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
                        t = next(_tuiles_it, None)
                        if t is not None:
                            pending[pool.submit(_dl, t)] = t
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
                        # couche, la zone est hors couverture — typiquement bbox
                        # hors zone, ou ordre --zone-bbox inversé (W,S,E,N =
                        # longitude d'abord). On abort tôt au lieu de tenter 100k
                        # tuiles vides en silence. R2#17 : critère ok==0 (et non
                        # ok*50<absentes = couverture <2 %) pour NE PAS abandonner
                        # une couverture clairsemée mais RÉELLE (île, bande
                        # côtière, couche historique) ; et on ne fail-fast qu'une
                        # fois la moitié de la grille balayée (total//2), sinon on
                        # risquait d'abort avant d'atteindre une couverture tardive
                        # dans l'ordre de balayage.
                        if (ok == 0 and abort_msg is None
                                and absentes >= max(SEUIL_HORS_COUVERTURE,
                                                    total // 2)):
                            abort_hors_couv = True
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
                    t = next(_tuiles_it, None)
                    if t is not None:
                        pending[pool.submit(_dl, t)] = t

        if batch:
            cur.executemany(
                "INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)", batch)
            con.commit()
    finally:
        # sys.exc_info() reste renseigné pendant un finally traversé par une
        # exception : après fermeture on peut alors jeter tout le chantier sans
        # masquer KeyboardInterrupt/MemoryError/l'erreur d'origine.
        _wmts_exception_active = sys.exc_info()[0] is not None
        # Toujours fermer la connexion, même sur exception non capturée
        # (KeyboardInterrupt, MemoryError, OSError disque plein…).
        try: con.close()
        except Exception: pass
        _wmts_close_all_conns()   # libérer les connexions keep-alive du batch
        if _wmts_exception_active:
            _nettoyer_sqlite_part(chemin_part)

    # Garde-fou couverture (fin de scan) : AUCUNE tuile dans la couche → bbox
    # hors zone / inversée. R2#17 : critère ok==0 (et non ok*50<absentes) pour ne
    # pas discarder une couverture clairsemée réelle. Évite aussi un MBTiles vide
    # "0 tiles" présenté comme un succès.
    if (abort_msg is None and not _stop_event.is_set()
            and absentes > 0 and ok == 0):
        abort_hors_couv = True
        abort_msg = (f"{ok} tuile(s) dans la couverture pour {absentes} hors couche "
                     f"(204). Zone hors de la couche, ou ordre de --zone-bbox inversé "
                     f": il attend W,S,E,N (longitude d'abord, ex. -5.0,47.8,-2.6,49.0).")

    if abort_msg is not None:
        # .part removed: un fichier vide-presque ferait croire à un succès.
        # Si l'utilisateur veut analyser le partiel, il rejouera et verra les
        # logs.
        _nettoyer_sqlite_part(chemin_part)
        if abort_hors_couv:
            # Ligne neutre et factuelle : en chunk de grille la boucle de split
            # ajoute « skipped » (pas d'alarme « ✗ ABANDON ... bbox inversé »
            # trompeuse sur une cellule mer légitime). Le hint bbox complet
            # reste dans l'exception, donc un run simple à bbox erronée le voit.
            print(f"\n  ⊘ {absentes} tiles out of coverage (204) for {ok} in layer.")
        else:
            print(f"\n  ✗ ABANDON : {abort_msg}")
        _exc_cls = (dependances.zone_hors_couverture
                    if abort_hors_couv else RuntimeError)
        raise _exc_cls(f"WMTS abort : {abort_msg}")

    if _stop_event.is_set():
        # Partiel supprimé : sans valeur de reprise (les tuiles déjà reçues
        # sont dans le cache disque), et un .mbtiles ne doit exister que
        # complet.
        elapsed = int(time.time() - t0)
        taille_mo = chemin_part.stat().st_size / 1e6 if chemin_part.exists() else 0.0
        _nettoyer_sqlite_part(chemin_part)
        print(f"\n  Interrupted - {ok} tiles written before stop  "
              f"({taille_mo:.0f} MB, partial file removed; cached tiles kept)")
        raise KeyboardInterrupt("MBTiles WMTS interrompu par utilisateur")

    # Erreurs de téléchargement éparses (sous le seuil du circuit-breaker) :
    # NE PAS publier un MBTiles troué — l'invariant "artefact présent =
    # complet" tomberait, et le re-run dirait "already present" au lieu de
    # réparer. Les tuiles réussies sont dans le cache disque : le re-run ne
    # retélécharge que les manquantes.
    if erreurs > 0:
        _nettoyer_sqlite_part(chemin_part)
        print(f"\n  ✗ {erreurs} download error(s) - MBTiles not finalized "
              f"({ok} tiles cached; rerun to complete)")
        raise RuntimeError(f"WMTS : {erreurs} erreur(s) de téléchargement, "
                           f"MBTiles non finalisé (relancer pour compléter)")

    # Validation après fermeture : schéma, nombre exact de tuiles, aucun
    # sidecar requis. Une erreur conserve l'ancien final.
    try:
        _valider_sqlite_part(
            chemin_part, {"metadata": None, "tiles": ok}
        )
    except BaseException:
        _nettoyer_sqlite_part(chemin_part)
        raise

    # Publication atomique : rename après le close (fait dans le finally ;
    # Windows refuse de renommer un fichier encore ouvert).
    chemin_part.replace(chemin)
    elapsed = int(time.time() - t0)
    taille_mo = chemin.stat().st_size / 1e6
    err_str = f"  ({erreurs} erreurs)" if erreurs else ""
    print(f"\n  100%  {ok} tiles  ({absentes} missing){err_str}  {_hms(elapsed)}")
    print(f"  {chemin.name} : {ok} tiles  ({taille_mo:.0f} MB)")
    return chemin
