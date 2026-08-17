"""Export OSM PBF vers un ensemble GeoJSON publié atomiquement."""

from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import time


@dataclass(frozen=True)
class DependancesExportOsm:
    osm_filtre_cles: object
    osm_cle_match: object
    chemin_part: object
    gunzip_vers_fichier: object
    publier_groupe_atomique: object
    formater_duree: object


def generer_geojson_osm(bbox_wgs84, dossier_ville, nom_zone, osm_pbf,
                        osm_tags=None, ecraser_tuiles=False, formats=None, *,
                        dependances):
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
        # Ne pas supprimer les sorties existantes avant le traitement : elles
        # restent utilisables si PyOsmium, gzip ou la fusion échoue.
        for p in (chemin_gz_attendu, chemin_raw_attendu):
            if p.exists():
                print(f"  GeoJSON OSM : overwrite {p.name}")

    try:
        import osmium as _osm
    except ImportError:
        print("  ERROR: osmium missing, run pip install osmium")
        print("          (official libosmium Python binding, ~2 MB, precompiled wheel)")
        return None

    lon_min, lat_min, lon_max, lat_max = bbox_wgs84
    t0 = time.time()
    chemin_principal = chemin_gz_attendu if ecrire_gz else chemin_raw_attendu
    print(f"  PyOsmium → {chemin_principal.name}...", flush=True)

    # Clés thématiques + valeurs demandées (grammaire osmosis, ordre = priorité
    # de couche déterministe, R2#28). Extrait en helper module pour testabilité.
    _cles, _vals_par_cle = dependances.osm_filtre_cles(osm_tags)
    _crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}

    # GeoJSONFactory produit du GeoJSON-string ; on parse en dict pour
    # construire les features avec leurs propriétés.
    fab = _osm.geom.GeoJSONFactory()

    # Helper : (clé, valeur) du 1er filtre satisfait (cf. dependances.osm_cle_match, R2#28).
    def _cle_obj(tags):
        return dependances.osm_cle_match(tags, _cles, _vals_par_cle)

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
    _streams_paths = {}   # cle → (path_part_gz, path_final_gz, path_final_raw)
    _first_feat    = {}   # cle → bool (1ère feature non encore écrite)
    _counts_par_cle = {}  # cle → nombre de features écrites
    nb_total = [0]
    nb_kept  = [0]

    def _ouvrir_stream_cle(cle):
        """Ouvre paresseusement le staging .gz pour cette clé (1ère feature)."""
        if cle in _streams:
            return _streams[cle]
        base = dossier_ville / f"{nom_zone}_osm_{cle}.geojson"
        path_gz = Path(str(base) + ".gz")
        path_part = dependances.chemin_part(path_gz)
        path_part.parent.mkdir(parents=True, exist_ok=True)
        fh = gzip.open(path_part, "wb", compresslevel=6)
        header = (
            '{"type":"FeatureCollection","name":'
            + json.dumps(f"{nom_zone}_osm_{cle}", ensure_ascii=False)
            + ',"crs":' + json.dumps(_crs, ensure_ascii=False, separators=(",", ":"))
            + ',"features":['
        ).encode("utf-8")
        fh.write(header)
        _streams[cle]       = fh
        _streams_paths[cle] = (path_part, path_gz, base)
        _first_feat[cle]    = True
        _counts_par_cle[cle] = 0
        return fh

    def _fermer_streams_partiels():
        """Cleanup en cas d'exception : fermer + supprimer les .part."""
        for fh in _streams.values():
            try: fh.close()
            except Exception: pass
        for path_part, _, _ in _streams_paths.values():
            try: path_part.unlink(missing_ok=True)
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
        print(f"  ERROR PyOsmium: {type(e_proc).__name__}: {e_proc}")
        return None

    # Finaliser chaque stream par-clé, mais garder tous les résultats en .part
    # jusqu'à ce que les sorties thématiques ET globale soient validées.
    try:
        for cle, fh in list(_streams.items()):
            fh.write(b"]}")
            fh.close()
    except BaseException as e_close:
        _fermer_streams_partiels()
        if not isinstance(e_close, Exception):
            raise
        print(f"  ERROR finalizing OSM GeoJSON: "
              f"{type(e_close).__name__}: {e_close}")
        return None

    print(f"  PyOsmium: {nb_total[0]} objects scanned, {nb_kept[0]} in the bbox", flush=True)

    if nb_kept[0] == 0:
        _fermer_streams_partiels()
        print("  No OSM feature exported")
        return None

    # Fichier fusionné global : concaténer en streaming les fichiers par-clé
    base_global = dossier_ville / f"{nom_zone}_osm.geojson"
    chemin_global_gz  = Path(str(base_global) + ".gz")
    chemin_global_raw = base_global

    # Les sorties raw sont elles aussi préparées sous des noms .part. Ainsi une
    # décompression/fusion interrompue ne touche aucun ancien fichier final.
    _raw_parts = {}
    chemin_global_gz_part = None
    chemin_global_raw_part = None

    def _nettoyer_publication_osm():
        _fermer_streams_partiels()
        for p in _raw_parts.values():
            p.unlink(missing_ok=True)
        if chemin_global_gz_part is not None:
            chemin_global_gz_part.unlink(missing_ok=True)
        if chemin_global_raw_part is not None:
            chemin_global_raw_part.unlink(missing_ok=True)

    # On reconstruit le .gz global à partir des .gz thématiques encore en
    # staging. Toute erreur de lecture est fatale : réutiliser un ancien final
    # masquerait une publication partielle.
    try:
        import ijson as _ijson_g
        _has_ijson_g = True
    except ImportError:
        _has_ijson_g = False

    def _iter_feats_par_cle():
        for _, (path_part, _, _) in _streams_paths.items():
            if _has_ijson_g:
                with gzip.open(path_part, "rb") as fh:
                    yield from _ijson_g.items(fh, "features.item")
                continue
            # Fallback non-streaming si ijson est absent.
            with gzip.open(path_part, "rt", encoding="utf-8") as fh:
                gj = json.load(fh)
            for feat in gj.get("features", []):
                yield feat

    try:
        # Dériver d'abord tous les raw thématiques, toujours vers des .part.
        if ecrire_geojson:
            for cle, (path_part, _, base) in _streams_paths.items():
                raw_part = dependances.chemin_part(base)
                _raw_parts[cle] = raw_part
                dependances.gunzip_vers_fichier(path_part, raw_part)
                if not raw_part.exists() or raw_part.stat().st_size == 0:
                    raise OSError(f"empty staged GeoJSON: {base.name}")

        chemin_global_gz_part = dependances.chemin_part(chemin_global_gz)
        with gzip.open(chemin_global_gz_part, "wb", compresslevel=6) as out_g:
            header_g = (
                '{"type":"FeatureCollection","name":'
                + json.dumps(f"{nom_zone}_osm", ensure_ascii=False)
                + ',"crs":' + json.dumps(_crs, ensure_ascii=False, separators=(",", ":"))
                + ',"features":['
            ).encode("utf-8")
            out_g.write(header_g)
            first_g = True
            n_global = 0
            import decimal as _dec_g

            def _enc_def(o):
                if isinstance(o, _dec_g.Decimal):
                    return float(o)
                raise TypeError(f"Type non-sérialisable : {type(o).__name__}")

            for feat in _iter_feats_par_cle():
                if not first_g:
                    out_g.write(b",")
                first_g = False
                out_g.write(json.dumps(feat, ensure_ascii=False,
                                       separators=(",", ":"),
                                       default=_enc_def).encode("utf-8"))
                n_global += 1
            out_g.write(b"]}")

        if n_global != nb_kept[0]:
            raise OSError(
                f"incomplete global GeoJSON: {n_global}/{nb_kept[0]} features"
            )
        if (not chemin_global_gz_part.exists()
                or chemin_global_gz_part.stat().st_size == 0):
            raise OSError("empty staged global GeoJSON gzip")

        if ecrire_geojson:
            chemin_global_raw_part = dependances.chemin_part(chemin_global_raw)
            dependances.gunzip_vers_fichier(
                chemin_global_gz_part, chemin_global_raw_part
            )
            if (not chemin_global_raw_part.exists()
                    or chemin_global_raw_part.stat().st_size == 0):
                raise OSError("empty staged global GeoJSON")

        # Toutes les transformations sont maintenant validées. Publier le
        # groupe en une transaction avec restauration de tous les anciens
        # fichiers si une seule promotion échoue. Le global reste en dernier.
        _publications = []
        for cle, (path_part, path_gz, base) in _streams_paths.items():
            if ecrire_geojson:
                _publications.append((_raw_parts[cle], base))
            if ecrire_gz:
                _publications.append((path_part, path_gz))

        if ecrire_geojson:
            _publications.append((chemin_global_raw_part, chemin_global_raw))
        if ecrire_gz:
            _publications.append((chemin_global_gz_part, chemin_global_gz))
        dependances.publier_groupe_atomique(_publications)

        for cle, (_, path_gz, base) in _streams_paths.items():
            n_cle = _counts_par_cle.get(cle, 0)
            if ecrire_gz:
                print(f"  {path_gz.name} : {n_cle} features")
            if ecrire_geojson:
                print(f"  {base.name} : {n_cle} features")

        chemin_principal = (
            chemin_global_gz if ecrire_gz else chemin_global_raw
        )
        taille = chemin_principal.stat().st_size // 1024
        print(f"  {chemin_principal.name} : {nb_kept[0]} features"
              f"  ({taille} Ko)  {dependances.formater_duree(int(time.time()-t0))}")
        return chemin_principal
    except BaseException as e_pub:
        if not isinstance(e_pub, Exception):
            raise
        print(f"  ERROR publishing OSM GeoJSON: "
              f"{type(e_pub).__name__}: {e_pub}")
        return None
    finally:
        _nettoyer_publication_osm()

