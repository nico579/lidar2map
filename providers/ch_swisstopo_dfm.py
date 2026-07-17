# providers/ch_swisstopo_dfm.py — Suisse, DFM « structures debout » 0,5 m
# depuis le nuage classé swissSURFACE3D (swisstopo, LAZ)
#
# POURQUOI : comme le MNT IGN, swissALTI3D (fr-ign / ch-swisstopo) est un modèle
#   de TERRAIN : les structures debout (murs de ruine…) y sont effacées. Ce
#   jumeau reconstruit un modèle façon DFM depuis le nuage de points classé
#   swissSURFACE3D, qui contient TOUS les retours (sol + végétation + bâti).
#
# JUMEAU de fr-ign-dfm : toute la machinerie DFM (réglages hmin/hmax/classes +
#   tissu CSF, nommage injectif, variant_tag, hooks pre_download/post_fetch) est
#   dans common.DfmProvider. Ce module ne porte que les spécificités suisses :
#     - CRS EPSG:2056 (LV95), préfixe ch_dfm05 ;
#     - découverte STAC swisstopo (collection swisssurface3d) via le helper
#       mutualisé common.swisstopo_stac_dalles (partagé avec ch-swisstopo) ;
#     - bornes nominales par COIN SW (convention swisstopo, ≠ Ymax de l'IGN) ;
#     - download = **ZIP** `.las.zip` (magic PK) → post_fetch dézippe (zipped=True) ;
#     - socle par DÉFAUT = **CSF** : les codes de classification swisstopo ne sont
#       pas garantis identiques à l'IGN (2=sol est standard ASPRS, mais 66 =
#       points virtuels IGN n'existe pas), et le tissu CSF ignore les classes →
#       zéro dépendance au schéma suisse. Le mode `classes` reste disponible
#       (--dfm-ground classes) avec un jeu ASPRS raisonnable, à valider.
#
# COÛT : une tuile swissSURFACE3D = ~125 Mo (.las.zip), 1 km², densité élevée.
#   Conversion ~3 min/dalle en CSF (défaut). Prospection ciblée, pas de grandes
#   cartes. VALIDATION TERRAIN requise (site suisse connu) avant confiance.
#
# Self-contained : stdlib uniquement (laspy/lazrs/CSF/rasterio requis au runtime).

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Suisse — DFM ruines/structures 0,5 m (swissSURFACE3D LAZ, expérimental)"
CODE       = "ch-swisstopo-dfm"
COUNTRY    = "ch"
LICENSE    = "Free (BGDI Bundesgeodaten-Verordnung) — © swisstopo"
DOC_URL    = "https://www.swisstopo.admin.ch/en/height-model-swisssurface3d"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2056"          # CH1903+ / LV95
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000              # GeoTIFF 2000² DEFLATE après conversion

COLLECTION_PC = "ch.swisstopo.swisssurface3d"   # nuage de points (assets .las.zip)


# ── Bornes nominales (convention swisstopo : nom = COIN SW en km) ─────────────
def _bounds_nominaux(e_km, n_km):
    """swisssurface3d_<année>_<E_km>-<N_km>_... couvre [E*1000, E*1000+1000] ×
    [N*1000, N*1000+1000]. Passées à las_to_dfm pour une grille alignée au km
    (anti-couture VRT). ATTENTION : coin SW, PAS la convention Ymax de l'IGN."""
    e, n = int(e_km), int(n_km)
    return (e * 1000, n * 1000, e * 1000 + 1000, n * 1000 + 1000)


# ── Découverte (STAC swisstopo, helper mutualisé) ────────────────────────────
def _asset_laszip(nom, ass):
    """Sélectionne l'asset nuage de points (.las.zip, type laszip)."""
    return (ass.get("type", "") == "application/vnd.laszip"
            or nom.lower().endswith(".las.zip"))


def _discover(bbox_wgs84, bbox_natif, cache_path, workers=1):
    candidats = common.swisstopo_stac_dalles(
        COLLECTION_PC, "swisssurface3d", _asset_laszip,
        bbox_wgs84, bbox_natif, cache_path)
    if candidats is None:
        return None
    dalles = {dalle_filename(e, n): href
              for (e, n), (_y, _nom, href) in candidats.items()}
    if dalles:
        print(f"  CH DFM (swissSURFACE3D LAZ): {len(dalles)} tile(s) in the bbox "
              f"(~{len(dalles) * 125} MB of point cloud to download!)")
    else:
        print("  CH DFM: no swissSURFACE3D point-cloud tile here")
    return dalles


# ── Machinerie DFM (mutualisée) ──────────────────────────────────────────────
# Préfixe « ch_dfm05 » = MÉTHODE de conversion actuelle (bumper si l'algo change).
# Socle possible ASPRS (2=sol, 9=eau) ; défaut ground=csf (voir en-tête).
_P = common.DfmProvider(
    prefix="ch_dfm05", crs_epsg=2056, resolution=RESOLUTION_M,
    socle_possible=(2, 9),
    defaults=(0.4, 2.5, (1, 2, 3, 4, 9), "csf"),
    csf_defaults=(0.5, 0.5, 1),
    bounds_fn=_bounds_nominaux, discover_fn=_discover,
    zipped=True, tile_mb=125, log_tag="DFM")

# Défauts exposés (lus par le cœur pour préremplir la GUI + par les tests)
DFM_HMIN           = _P.def_hmin
DFM_HMAX           = _P.def_hmax
DFM_CLASSES        = _P.def_classes
DFM_GROUND         = _P.def_ground
DFM_CSF_THRESHOLD  = _P.def_csf_threshold
DFM_CSF_RESOLUTION = _P.def_csf_resolution
DFM_CSF_RIGIDNESS  = _P.def_csf_rigidness

# Contrat provider : delegators vers l'instance partagée
set_dfm_params   = _P.set_params
dalle_filename   = _P.dalle_filename
dalle_subdir     = _P.dalle_subdir
subdir_from_name = _P.subdir_from_name
variant_tag      = _P.variant_tag
discover_dalles  = _P.discover_dalles
pre_download     = _P.pre_download
post_fetch       = _P.post_fetch
dfm_defaults     = _P.defaults_dict
# Internes exposés pour les tests
_socle           = _P.socle
_reinjectees     = _P.reinjectees
_laz_filename    = _P.laz_filename


def dalle_url(x_km, y_km):
    raise NotImplementedError("ch-swisstopo-dfm : URL via STAC → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("ch-swisstopo-dfm : index STAC → discover_dalles()")
