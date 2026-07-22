# providers/ch_swisstopo.py — Suisse, swissALTI3D via swisstopo STAC API
#
# Source : Bundesamt für Landestopografie swisstopo (data.geo.admin.ch).
# Distribution : STAC API (Spatial Temporal Asset Catalog) — paradigme
# encore différent de FR (TMS PBF) et NL (ATOM JSON statique).
#
# Différences architecturales vs FR/NL :
#   - CRS natif EPSG:2056 (CH1903+ / LV95 Mercator suisse)
#   - Découverte via STAC API REST (collection + bbox query → items JSON)
#   - Chaque "item" a 4 assets (COG 0.5m, COG 2m, XYZ 0.5m, XYZ 2m)
#     → on filtre sur le COG 0.5m EPSG:2056
#   - Nommage : swissalti3d_<year>_<E_km>-<N_km>_0.5_2056_<elev>.tif
#     où l'élévation suffixe (5728, etc.) est metadata par tuile, non
#     dérivable de (x, y) seul → URL impossible à construire sans STAC
#
# Status POC : provider validé live contre swisstopo STAC. discover_dalles
# fonctionne, retourne les URLs COG signées. Téléchargement direct OK.

from providers import common


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "Suisse — swissALTI3D (swisstopo)"
CODE       = "ch-swisstopo"
COUNTRY    = "ch"
LICENSE    = "Free (BGDI Bundesgeodaten-Verordnung)"
DOC_URL    = "https://www.swisstopo.admin.ch/en/height-model-swissalti3d"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2056"       # CH1903+ / LV95 (Swiss Mercator)
RESOLUTION_M       = 0.5
DALLE_KM           = 1                 # tuiles 1×1 km en LV95
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000 px
SEUIL_DALLE_VALIDE = 2_000_000         # COG 0.5m ~2-10 Mo (terrain Swiss)


# ── Endpoints ────────────────────────────────────────────────────────────────
COLLECTION  = "ch.swisstopo.swissalti3d"


# ── Nommage des dalles ───────────────────────────────────────────────────────
# Le nommage Swiss inclut une "élévation" suffixe propre à chaque tuile,
# non dérivable de (E_km, N_km) seuls. discover_dalles est obligatoire.

def dalle_filename(x_km, y_km):
    raise NotImplementedError(
        "swissALTI3D nomme par swissalti3d_<year>_<E>-<N>_<res>_<crs>_<elev>.tif "
        "— l'élévation n'est connue que via STAC API. Utiliser discover_dalles().")


def subdir_from_name(nom):
    return None


def dalle_url(x_km, y_km):
    raise NotImplementedError("Voir dalle_filename : STAC requis.")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError(
        "swissALTI3D : utiliser discover_dalles() — pas de grille dérivable.")


# ── Découverte via STAC API ──────────────────────────────────────────────────
def _asset_cog_05m(nom, ass):
    """Sélectionne le COG 0.5 m EPSG:2056 (asset *_0.5_2056_*.tif)."""
    return (nom.endswith(".tif") and "_0.5_2056_" in nom
            and ass.get("type", "").startswith("image/tiff"))


def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Interroge la STAC API swisstopo (helper mutualisé common.swisstopo_stac_
    dalles, partagé avec le jumeau ch-swisstopo-dfm) pour swissALTI3D, filtre le
    COG 0.5 m EPSG:2056 et construit {nom_asset: url}. Le nom d'asset porte une
    élévation propre à chaque tuile (non dérivable de E/N) → on le garde comme
    clé. Filtre bbox natif LV95 (la caller élargit la bbox WGS de ±0.05°) et
    dédup au dernier millésime : faits dans le helper.

    Retourne {nom_fichier: url} ou None si erreur réseau."""
    candidats = common.swisstopo_stac_dalles(
        COLLECTION, "swissalti3d", _asset_cog_05m,
        bbox_wgs84, bbox_natif, cache_path)
    if candidats is None:
        return None
    return {nom: href for (_y, nom, href) in candidats.values()}
