"""Planification et orchestration des ombrages terrain."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class DependancesGenererOmbrages:
    """Coutures applicatives relues par la façade avant chaque génération."""

    provider: object
    elevation_soleil: float
    resolution_m: float
    svf_gamma: float
    shading_types: object
    fetch_provider_shadings: Callable
    resoudre_instances_ombrages: Callable
    chemin_part: Callable
    creer_fichier: Callable
    build_vrt_xml: Callable
    formater_duree: Callable
    source_a_des_donnees: Callable
    publier_tif_atomique: Callable
    hillshade_chunked_multi: Callable
    stop_event: object
    svf_chunked: Callable
    svf_numpy: Callable
    sauver_array_georef: Callable
    lire_dem_rasterio: Callable
    lrm_array: Callable
    lrm_chunked: Callable
    hillshade_chunked: Callable
    rrim_chunked: Callable
    svf_opos_chunked: Callable
    vat_compose: Callable
    mstp_chunked: Callable
    e4mstp_compose: Callable
    normaliser_nom: Callable
    time_module: object
    imprimer: Callable = print


def resoudre_instances_ombrages(
    choix,
    instances,
    *,
    elevation_soleil,
    svf_gamma,
    svf_conv,
    svf_dist,
    resolution_m,
    elevation_defaut,
    shading_types,
    imprimer: Callable = print,
):
    """Résout paramètres, suffixes et collisions dans l'ordre historique."""
    sigma_defaut_m = 15 * resolution_m

    def resoudre_params(typ, parametres):
        resolved = dict(parametres or {})
        if typ in ("315", "045", "135", "225", "multi"):
            resolved.setdefault("elevation", float(elevation_soleil))
        if typ == "svf":
            resolved.setdefault(
                "conv", "rvt" if str(svf_conv).lower() == "rvt" else "flux"
            )
        if typ in ("svf", "opos", "oneg"):
            resolved.setdefault("dist", float(svf_dist))
            resolved.setdefault("gamma", float(svf_gamma))
        if typ == "vat":
            resolved.setdefault("dist", float(svf_dist))
            resolved.setdefault("gamma", float(svf_gamma))
        if typ == "e4mstp":
            resolved.setdefault("dist", float(svf_dist))
            resolved.setdefault("gamma", 0.8)
        if typ in ("lrm", "rrim"):
            resolved.setdefault("sigma", float(sigma_defaut_m))
        return resolved

    def tag(value):
        return f"{value:g}".replace(".", "p").replace("-", "m")

    def suffixe_instance(typ, parametres, resolved):
        if typ == "slope":
            return "slope_ombrage"
        if typ in ("315", "045", "135", "225", "multi"):
            if (
                "elevation" in (parametres or {})
                and resolved["elevation"] != elevation_defaut
            ):
                return f"{typ}_e{tag(resolved['elevation'])}_ombrage"
            return f"{typ}_ombrage"
        if typ in ("svf", "opos", "oneg"):
            gamma_tag = f"{resolved['gamma']:.1f}".replace(".", "p")
            base = f"svf_{resolved['conv']}" if typ == "svf" else typ
            return (
                f"{base}_{int(round(resolved['dist']))}m_"
                f"g{gamma_tag}_ombrage"
            )
        if typ in ("vat", "e4mstp"):
            if parametres:
                gamma_tag = f"{resolved['gamma']:.1f}".replace(".", "p")
                return (
                    f"{typ}_{int(round(resolved['dist']))}m_"
                    f"g{gamma_tag}_ombrage"
                )
            return f"{typ}_ombrage"
        if "sigma" in (parametres or {}):
            return f"{typ}_s{tag(resolved['sigma'])}m_ombrage"
        return f"{typ}_ombrage"

    resolved_instances = []
    seen = {}
    for typ, parametres in (
        [(typ, {}) for typ in choix] + list(instances or [])
    ):
        if typ not in shading_types:
            imprimer(f"  ⚠ unknown shading type ignored: {typ}")
            continue
        resolved = resoudre_params(typ, parametres)
        suffix = suffixe_instance(typ, parametres, resolved)
        if suffix in seen:
            if seen[suffix] != (typ, resolved):
                imprimer(
                    f"  ⚠ shading '{typ}' {parametres} collapses to the same "
                    f"name '{suffix}' as an earlier setting; keeping the "
                    "first, ignoring this one"
                )
            continue
        seen[suffix] = (typ, resolved)
        resolved_instances.append((typ, resolved, suffix))
    return resolved_instances


def generer_ombrages(cogs, dossier_ville, choix=None, elevation_soleil=None, nom_zone=None, ecraser_ombrages=False, ecraser_tuiles=False, use_sweep=False, svf_gamma=None, svf_conv=None, svf_dist=None, bbox_natif=None, instances=None, *, dependances):
    """
    Génère les ombrages depuis le VRT/COG source (MNT EPSG:2154).

    Types gdaldem  : 315, 045, 135, 225, multi, slope
    Types numpy/scipy (sans WhiteboxTools) :
        svf  — Sky-View Factor paramétrique (conv flux cos²γ / rvt 1−sin γ,
               distance svf_dist, gamma svf_gamma) : micro-relief, fossés, murs
        opos — Openness positive (Yokoyama 2002, rayon/gamma du SVF) : crêtes
        oneg — Openness négative inversée : fossés/chemins creux sombres
        rrim — Red Relief Image Map  : composite RGB couleur (R=pente, G=B=LRM)
        lrm  — Local Relief Model    : SLRM = DEM − gaussienne(σ auto 15 pixels
               natifs, ou valeur explicite en mètres) — scipy requis
        vat  — Visualization for Archaeological Topography : variante VAT-style
               en niveaux de gris, SVF + openness positif + pente
        e4mstp — Multiscale Topographic Position, enhanced version 4 : variante
               lidar2map multi-échelle (SVF, O+/O−, pente, MSTP et deux SLRM)

    Deux chemins d'entrée, cumulables :
      choix     : liste de TYPES (--shadings, GUI historique) — chaque type
                  devient une instance aux paramètres GLOBAUX ci-dessous ;
      instances : liste (type, params explicites) du flag répétable
                  --shading TYPE:cle=val,... (cf. parser_shading_spec) —
                  permet plusieurs instances du même type (svf 20 m + 100 m).
    Les suffixes de fichier sont normalisés et certains paramètres sont arrondis.
    Si deux instances aboutissent au même nom, la première sortie est conservée.

    elevation_soleil : angle solaire des hillshades directionnels (défaut: 25°).
    svf_conv  : "flux" (cos²γ, contraste) ou "rvt" (1−sin γ, archéo).  Défaut flux.
    svf_dist  : rayon SVF/openness en mètres (GUI : 10–200).  Défaut 20.
    svf_gamma : gamma après stretch (défaut: SVF_GAMMA ; miroir pour oneg).
    use_sweep : kernel sweep-horizon (SVF uniquement).
    SVF/LRM/RRIM : implémentés en numpy/scipy — aucun outil externe requis.
    """

    PROVIDER = dependances.provider
    ELEVATION_SOLEIL = dependances.elevation_soleil
    RESOLUTION_M = dependances.resolution_m
    SVF_GAMMA = dependances.svf_gamma
    _SHADING_TYPES = dependances.shading_types
    _fetch_provider_shadings = dependances.fetch_provider_shadings
    _resoudre_instances_ombrages = dependances.resoudre_instances_ombrages
    _chemin_part = dependances.chemin_part
    _creer_fichier = dependances.creer_fichier
    _build_vrt_xml = dependances.build_vrt_xml
    _hms = dependances.formater_duree
    _source_a_des_donnees = dependances.source_a_des_donnees
    _publier_tif_atomique = dependances.publier_tif_atomique
    _hillshade_chunked_multi = dependances.hillshade_chunked_multi
    _stop_event = dependances.stop_event
    _svf_chunked = dependances.svf_chunked
    _svf_numpy = dependances.svf_numpy
    _sauver_array_georef = dependances.sauver_array_georef
    _lire_dem_rasterio = dependances.lire_dem_rasterio
    _lrm_array = dependances.lrm_array
    _lrm_chunked = dependances.lrm_chunked
    _hillshade_chunked = dependances.hillshade_chunked
    _rrim_chunked = dependances.rrim_chunked
    _svf_opos_chunked = dependances.svf_opos_chunked
    _vat_compose = dependances.vat_compose
    _mstp_chunked = dependances.mstp_chunked
    _e4mstp_compose = dependances.e4mstp_compose
    normaliser_nom = dependances.normaliser_nom
    time = dependances.time_module
    print = dependances.imprimer

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
        print("  ⚠ No tile available in this chunk "
              "(outside LiDAR coverage or downloads failed), "
              "shadings skipped.", flush=True)
        return []

    # Ombrages precalcules fournis par le provider (PROVIDES_SHADINGS) :
    # telecharges directement depuis le WCS du provider (ex. Digitaal Vlaanderen
    # SVF/Hillshade 25cm) AVANT la resolution en instances, pour que les cles
    # ainsi servies soient retirees de choix et NON recalculees localement.
    # Seules les instances "par defaut" (issues de choix) sont servies — une
    # instance --shading aux params explicites est toujours calculee localement.
    _cles_provider = []   # clés servies par le provider (pour la liste des cibles)
    if bbox_natif is not None and hasattr(PROVIDER, "PROVIDES_SHADINGS") and choix:
        _choix_avant = list(choix)
        choix = list(choix)
        _fetch_provider_shadings(
            choix, bbox_natif, dossier_ville, nom_zone, ecraser_ombrages,
            PROVIDER.PROVIDES_SHADINGS
        )
        _cles_provider = [c for c in _choix_avant if c not in choix]

    # ── Résolution en instances (typ, params_explicites, params_résolus, suffixe)
    # Le suffixe encode un param uniquement s'il est EXPLICITE et différent du
    # défaut canonique : les noms historiques (multi_ombrage, lrm_ombrage…)
    # restent inchangés aux réglages par défaut → caches préservés.
    insts = _resoudre_instances_ombrages(
        choix,
        instances,
        elevation_soleil=elevation_soleil,
        svf_gamma=svf_gamma,
        svf_conv=svf_conv,
        svf_dist=svf_dist,
        resolution_m=RESOLUTION_M,
        elevation_defaut=ELEVATION_SOLEIL,
        shading_types=_SHADING_TYPES,
        imprimer=print,
    )
    horn_types = ("315", "045", "135", "225", "multi", "slope")
    horn_insts  = [i for i in insts if i[0] in horn_types]
    numpy_insts = [i for i in insts if i[0] not in horn_types]

    # ── Construction VRT global (seamless, évite jointures gdaldem) ─────────
    # VRT dans un dossier de transaction unique finissant par .part sous
    # dossier_ville : la synchronisation distante ignore tout le chantier.
    import shutil as _shutil_vrt
    _vrt_tmpdir = None
    # ── Merge des dalles via rasterio (remplace gdalbuildvrt + gdal_translate) ──
    # Au lieu de produire un VRT puis de le convertir en GeoTIFF avec
    # gdal_translate, on fait un merge direct rasterio en GeoTIFF compressed.
    # Avantages : un seul passage, plus de dépendance à GDAL CLI, sortie
    # immédiatement utilisable par numpy (les hillshades sont calculés ensuite
    # en numpy, cf. étape ombrage).
    if len(cogs) > 1:
        _vrt_tmpdir = _chemin_part(dossier_ville / "_tmp")
        _vrt_tmpdir.mkdir(parents=True, exist_ok=True)
        # VRT XML : vue logique sur les dalles, ~200 o/dalle, construction <1 s.
        # Évite la matérialisation d'une mosaïque physique multi-Go (le merge
        # rasterio sur 2000+ dalles avec compression deflate est pathologique).
        # rasterio lit le VRT transparemment via libgdal — les calculs chunked
        # en aval reçoivent leurs fenêtres comme depuis un raster ordinaire.
        vrt_path      = _vrt_tmpdir / "_mnt_complet.vrt"
        filelist_path = _vrt_tmpdir / "_dalles.txt"
        try:
            filelist_path.write_text(
                "\n".join(str(c) for c in cogs), encoding="utf-8")
            _creer_fichier(filelist_path)
            print(f"  Building VRT ({len(cogs)} tiles)...", flush=True)
            _t0_vrt = time.time()
            _build_vrt_xml(cogs, vrt_path, RESOLUTION_M)
            _creer_fichier(vrt_path)
            print(f"  VRT OK  ({_hms(time.time()-_t0_vrt)}, "
                  f"{vrt_path.stat().st_size // 1024} Ko)", flush=True)
            sources = [vrt_path]
        except BaseException as e:
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
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

    # Garde-fou zone tout-nodata : si le DEM assemble n'a aucun pixel d'altitude
    # valide, tous les kernels sont inutiles (et le SVF planterait sur un
    # percentile de tableau vide). On saute les ombrages avec un message clair
    # plutot qu'un traceback. Vider les listes suffit : les deux boucles ne
    # s'executent pas et le nettoyage de fin a quand meme lieu.
    if (horn_insts or numpy_insts) and not _source_a_des_donnees(source):
        print("  WARNING: no valid elevation data in the zone "
              "(tiles are entirely nodata).")
        print("  Likely cause: no LiDAR data published here yet, or the tile "
              "index was unavailable at download time (empty tiles fetched).")
        print("  Shadings skipped.")
        horn_insts  = []
        numpy_insts = []

    # Chaque sortie demandée est d'abord écrite dans un nom unique finissant
    # par .part. Le final éventuellement présent reste lisible pendant tout le
    # recalcul et n'est remplacé qu'après fermeture + validation.
    _parts_ombrages_actifs = {}
    _sorties_a_regenerer = set()

    def _preparer_sortie_ombrage(chemin_final):
        chemin_part = _chemin_part(chemin_final)
        _parts_ombrages_actifs[chemin_part] = chemin_final
        _sorties_a_regenerer.add(chemin_final)
        return chemin_part

    def _abandonner_sortie_ombrage(chemin_part):
        chemin_final = _parts_ombrages_actifs.pop(chemin_part, None)
        if chemin_part.exists():
            chemin_part.unlink(missing_ok=True)
            nom_affiche = chemin_final.name if chemin_final else chemin_part.name
            print(f"  Partial file removed: {nom_affiche}")

    def _publier_sortie_ombrage(chemin_part, chemin_final):
        _publier_tif_atomique(chemin_part, chemin_final)
        _parts_ombrages_actifs.pop(chemin_part, None)
        _sorties_a_regenerer.discard(chemin_final)

    try:
        # ── Hillshades numpy chunked (RAM bornée — voir _hillshade_chunked_multi)
        # Traitement par fenêtres 2048×2048 px avec halo 1 px (Horn 3x3).
        # Tous les types demandés sont calculés en UNE passe de lecture :
        # sur une grande zone le coût dominant est l'I/O + décompression
        # deflate des dalles derrière le VRT, pas les kernels.
        if horn_insts:
            jobs_h = []
            publications_h = []
            for typ_h, p_h, sfx_h in horn_insts:
                nom_fichier = nom_base + "_" + sfx_h + ".tif"
                chemin_out  = dossier_ville / nom_fichier
                if chemin_out.exists() and not ecraser_ombrages:
                    print("  " + nom_fichier.ljust(56) + " -> already present")
                    continue
                chemin_part = _preparer_sortie_ombrage(chemin_out)
                publications_h.append((chemin_part, chemin_out))
                if typ_h == "multi":
                    jobs_h.append(("hillshade_multi",
                                   {"altitude_deg": float(p_h["elevation"])},
                                   chemin_part))
                elif typ_h == "slope":
                    jobs_h.append(("slope", {}, chemin_part))
                else:
                    jobs_h.append(("hillshade",
                                   {"azimuth_deg":  float(int(typ_h)),
                                    "altitude_deg": float(p_h["elevation"])},
                                   chemin_part))

            if jobs_h:
                print(f"  Hillshades chunked: {len(jobs_h)} type(s),"
                      f" single read pass...", flush=True)
                t0_hill = time.time()
                try:
                    ok_h = _hillshade_chunked_multi(
                        Path(str(source)), jobs_h,
                        dx=RESOLUTION_M, dy=RESOLUTION_M)
                    if not ok_h:
                        raise RuntimeError("chunked failed (rasterio absent ?)")
                    for chemin_part, chemin_out in publications_h:
                        _publier_sortie_ombrage(chemin_part, chemin_out)
                        _creer_fichier(chemin_out)
                        print(f"  {chemin_out.name.ljust(56)}"
                              f"  {_hms(int(time.time() - t0_hill))}"
                              f"  {chemin_out.stat().st_size / 1e6:.0f} Mo")
                except BaseException as e_hill:
                    # Fichiers partiellement écrits (structurellement valides
                    # mais incomplets) → supprimer, sinon ils seraient pris
                    # pour des caches sains au prochain lancement (même
                    # logique que le SVF).
                    for chemin_part, _chemin_out in publications_h:
                        _abandonner_sortie_ombrage(chemin_part)
                    if isinstance(e_hill, (KeyboardInterrupt, SystemExit)):
                        raise
                    print(f"\n  ERROR hillshades chunked: {e_hill}")

        # ── SVF / openness / LRM / RRIM — numpy/scipy ────────────────────────
        # NB : rasterio.merge (étape 2 du refactor) produit déjà un GeoTIFF
        # directement utilisable par numpy/PIL/rasterio en aval. Plus aucune
        # conversion intermédiaire VRT→GTiff nécessaire.
        src_str = str(source)

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
            chemin_part = _preparer_sortie_ombrage(chemin_out)

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
                        dst_path     = chemin_part,
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
                        # Garde OOM : le fallback charge le DEM entier + plusieurs
                        # tableaux pleine taille par direction (ThreadPool). Au-delà
                        # d'un seuil on refuse plutôt que de risquer l'OOM sur une
                        # grande zone sans numba.
                        _MAX_SVF_FULLMEM_PX = 6000 * 6000   # ~36 Mpx (~3 km à 0,5 m)
                        try:
                            import rasterio as _rio_sz
                            with _rio_sz.open(src_str) as _dsz:
                                _npx = _dsz.width * _dsz.height
                        except Exception:
                            _npx = 0
                        if _npx > _MAX_SVF_FULLMEM_PX:
                            print(f"  SVF: numba unavailable and zone too large "
                                  f"({_npx / 1e6:.0f} Mpx) for the full-memory "
                                  f"fallback. Install numba, or split the zone "
                                  f"with --split-cols/--split-rows.", flush=True)
                            continue
                        print("  SVF chunked KO → fallback to full memory", flush=True)
                        dem_arr, _nd = _lire_dem_rasterio(src_str)
                        arr_svf = _svf_numpy(dem_arr, max_dist_px, n_directions,
                                             RESOLUTION_M, use_sweep=_sweep_i,
                                             conv=conv, nodata=_nd)
                        # > 0 strict : les nodata valent exactement 0.0 et
                        # tireraient p2 vers 0 (stretch délavé).
                        svf_valid = arr_svf[arr_svf > 0]
                        if svf_valid.size == 0:
                            print("  SVF: no valid pixel (nodata zone), shading skipped")
                            continue
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
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_part)
                except Exception as e_svf:
                    import traceback as _tb
                    print(f"  ERROR SVF: {e_svf}")
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
                    _abandonner_sortie_ombrage(chemin_part)
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
                    src_path = Path(src_str),
                    dst_path = chemin_part,
                    sigma_px = sigma_px,
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
                        _sauver_array_georef(arr_u8, Path(src_str), chemin_part)
                        _lrm_ok = True
                        print(f"  LRM scipy (full memory): σ={sigma_px} px, {clip_info}")
                    except ImportError:
                        print("  scipy missing - LRM skipped (pip install scipy)", flush=True)
                        continue
                    except Exception as e_scipy:
                        print(f"  ERROR scipy LRM: {e_scipy}")
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
                print("  RRIM: Red Relief Image Map (slope × LRM)"
                      ", may take 5-10 min...", flush=True)

                sigma_rrim = _sigma_px   # défaut 15 px ; --shading rrim:sigma=M en mètres

                # Slope temporaire (réutilisé si already present)
                slope_rrim_path = dossier_ville / (nom_base + "_slope_ombrage.tif")
                slope_tmp_path  = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp")
                )
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
                            Path(src_str), _slope_src, chemin_part,
                            sigma_px=sigma_rrim)
                    except Exception as e_rrim:
                        print(f"  ERROR composite RRIM: {e_rrim}")
                        # Fichier partiellement écrit → supprimer (sinon pris
                        # pour un cache sain au prochain lancement).
                        _abandonner_sortie_ombrage(chemin_part)
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
                            _sauver_array_georef(rgb, Path(src_str), chemin_part)
                            print(f"  RRIM (full memory): {chemin_out.name}"
                                  f" — RGB 3 canaux")
                        except Exception as e_rrim:
                            print(f"  ERROR composite RRIM: {e_rrim}")
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
                print(f"  VAT: composite SVF + openness + slope"
                      f" (radius {_vat_dist_px * RESOLUTION_M:.0f} m)"
                      f", may take 10-20 min...", flush=True)
                _svf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_svf_tmp"))
                _opos_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_opos_tmp"))
                _slope_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp"))
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
                        print("  VAT: components unavailable (numba required for"
                              " SVF/openness), shading skipped.", flush=True)
                        continue
                    if not _vat_compose(_svf_t, _opos_t, _slope_t, chemin_part,
                                        gamma=_vat_gamma):
                        _abandonner_sortie_ombrage(chemin_part)
                        continue
                except Exception as e_vat:
                    print(f"  ERROR composite VAT: {e_vat}")
                    _abandonner_sortie_ombrage(chemin_part)
                    continue
                finally:
                    for _t in (_svf_t, _opos_t, _slope_t):
                        if _t.exists():
                            _t.unlink(missing_ok=True)

            elif cle == "e4mstp":
                # ── Variante lidar2map inspirée de l'e4MSTP publié (Kokalj
                # 2025/RVT), sans reproduire son preset exact. Même patron que
                # VAT : composantes en temp, blend, nettoie. Combine la couleur
                # multi-échelle du MSTP et la netteté du SVF. Lourd (openness
                # pos+neg + SVF + slope + 2 LRM + MSTP) ; réservé aux zones et
                # chunks, pas le défaut.
                _e4_dist_px = max(1, int(round(p_i["dist"] / RESOLUTION_M)))
                _e4_gamma   = float(p_i["gamma"])
                _slrm_fine_px = max(1, int(round(1.5 / RESOLUTION_M)))  # micro-relief
                _slrm_path_px = max(1, int(round(8.0 / RESOLUTION_M)))  # échelle chemin
                print(f"  e4MSTP-style (lidar2map variant):"
                      f" composite MSTP + coloured relief + SVF"
                      f" (radius {_e4_dist_px * RESOLUTION_M:.0f} m)"
                      f", may take 15-30 min...", flush=True)
                _svf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_svf_tmp"))
                _opos_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_opos_tmp"))
                _oneg_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_oneg_tmp"))
                _slope_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slope_tmp"))
                _mstp_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_mstp_tmp"))
                _slf_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slf_tmp"))
                _slp_t = _chemin_part(
                    dossier_ville / nom_fichier.replace(".tif", "_slp_tmp"))
                _e4_tmps = (_svf_t, _opos_t, _oneg_t, _slope_t, _mstp_t, _slf_t, _slp_t)
                try:
                    _ok = (
                        _svf_opos_chunked(Path(src_str), _svf_t, _opos_t,
                                          _e4_dist_px, 16, RESOLUTION_M, 1.0)
                        and _svf_chunked(Path(src_str), _oneg_t, _e4_dist_px, 16,
                                         RESOLUTION_M, 1.0, False, 3)
                        and _hillshade_chunked(Path(src_str), _slope_t, "slope",
                                               {}, dx=RESOLUTION_M, dy=RESOLUTION_M)
                        and _mstp_chunked(Path(src_str), _mstp_t, res=RESOLUTION_M)
                        and _lrm_chunked(Path(src_str), _slf_t, _slrm_fine_px)
                        and _lrm_chunked(Path(src_str), _slp_t, _slrm_path_px))
                    if not _ok:
                        print("  e4MSTP: components unavailable (numba/scipy"
                              " required), shading skipped.", flush=True)
                        continue
                    if not _e4mstp_compose(_mstp_t, _svf_t, _opos_t, _oneg_t,
                                           _slope_t, _slf_t, _slp_t, chemin_part,
                                           gamma=_e4_gamma):
                        _abandonner_sortie_ombrage(chemin_part)
                        continue
                except Exception as e_e4:
                    print(f"  ERROR composite e4MSTP: {e_e4}")
                    _abandonner_sortie_ombrage(chemin_part)
                    continue
                finally:
                    for _t in _e4_tmps:
                        if _t.exists():
                            _t.unlink(missing_ok=True)

            if not chemin_part.exists():
                print(f"  ERROR {nom_fichier}: no complete temporary output")
                continue
            try:
                _publier_sortie_ombrage(chemin_part, chemin_out)
            except Exception as e_publication:
                print(f"  ERROR publishing {nom_fichier}: {e_publication}")
                _abandonner_sortie_ombrage(chemin_part)
                continue
            _creer_fichier(chemin_out)
            taille = chemin_out.stat().st_size / 1e6
            elap_numpy = int(time.time() - t0_numpy)
            print(f"  {nom_fichier.ljust(56)}  {_hms(elap_numpy)}  {taille:.0f} Mo")

    finally:
        # Couvre aussi les ``continue`` précoces et Ctrl+C : seule la version
        # temporaire de ce processus est supprimée, jamais l'ancien final.
        for _chemin_part_actif in tuple(_parts_ombrages_actifs):
            _abandonner_sortie_ombrage(_chemin_part_actif)
        # Suppression du dossier transactionnel .part (VRT + dalles.txt).
        if _vrt_tmpdir and _vrt_tmpdir.exists():
            _shutil_vrt.rmtree(_vrt_tmpdir, ignore_errors=True)

    print("\n  Shadings in: " + str(dossier_ville))
    # Fichiers cibles de CE run (instances + pré-calculés provider) : permet à
    # l'étape MBTiles de ne tuiler QUE les ombrages demandés au lieu de tout le
    # dossier projet (sinon --tiles-overwrite re-tuile aussi les anciens).
    #
    # R2#23 : ne pas rendre de chemins théoriques. On lève aussi quand une
    # régénération demandée a échoué mais qu'un ancien final existe encore :
    # l'ancien reste volontairement intact pour la sécurité atomique, sans pour
    # autant masquer l'échec du recalcul.
    _cibles = [dossier_ville / f"{nom_base}_{sfx}.tif" for _t, _p, sfx in insts]
    _manquants = [
        p.name for p in _cibles
        if not p.exists() or p in _sorties_a_regenerer
    ]
    if _manquants:
        raise RuntimeError(
            "shading(s) failed"
            " (previous complete output preserved when present): "
            + ", ".join(_manquants) + " - rerun to complete"
        )
    _prov = [dossier_ville / f"{nom_base}_{c}_ombrage.tif" for c in _cles_provider]
    return _cibles + [p for p in _prov if p.exists()]
