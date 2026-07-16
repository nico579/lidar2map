# providers/fr_ign_dfm.py — France, DFM « ruines/structures debout » 0,5 m
# depuis le nuage classé LiDAR HD IGN (COPC LAZ)
#
# POURQUOI : le MNT IGN (fr-ign) efface PAR CONSTRUCTION les murs encore debout
#   au-delà d'environ 1 m : la chaîne IGN_AUTO les classe « végétation » (4) ou
#   « non classé » (1), et le MNT (classes 2/9/66 + TIN) interpole au travers.
#   Paradoxe documenté (spec DC_LiDAR_HD) : un muret de 40 cm survit, une ruine
#   de 1,5 m disparaît. Ce provider reconstruit un modèle façon **DFM** (Digital
#   Feature Model — le CONCEPT vient de Štular et al. 2021 ; la SÉLECTION
#   automatique des points est une heuristique maison, cf. common.las_to_dfm,
#   là où la littérature reclassifie (semi-)manuellement) : le terrain + les
#   structures debout, en réinjectant les retours bas non-sol (0,4-2,5 m,
#   classes 1/3/4) dans les trous de la classe sol. Tous les ombrages (LRM,
#   VAT…) fonctionnent ensuite tels quels. Le maquis revient aussi (mouchetis) :
#   murs = lignes continues, buissons = tavelures — l'œil discrimine (Kokalj &
#   Hesse : jamais une seule visualisation).
#
# COÛT (à savoir avant de lancer) : une dalle COPC = ~205 Mo (vs 16 Mo de MNT),
#   ~34 M de points, conversion ~20-30 s/dalle, ~1 Go de RAM. Outil de
#   PROSPECTION CIBLÉE (quelques km²), pas de grandes cartes. Pour l'analyse
#   fine d'un site : tools/dfm_ruines.py (GeoTIFF à draper dans QGIS).
#
# Paradigme : index WFS `IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle` (chaque dalle
#   1 km porte son `url` de download direct, comme fr-reunion/fr-guadeloupe ;
#   découverte mutualisée common.ign_lidar_hd_dalles) → COPC LAZ → post_fetch
#   common.las_to_dfm → GeoTIFF 0,5 m EPSG:2154.
#   Licence : Licence Ouverte 2.0 (Etalab) — © IGN.
#
# Self-contained : stdlib uniquement (laspy/lazrs/rasterio requis au runtime).

import re


# ── Identification ───────────────────────────────────────────────────────────
NAME       = "France — DFM ruines/structures 0,5 m (LiDAR HD LAZ, expérimental)"
CODE       = "fr-ign-dfm"
COUNTRY    = "fr"
LICENSE    = "Licence Ouverte 2.0 (Etalab) — © IGN"
DOC_URL    = "https://geoservices.ign.fr/lidarhd"


# ── Géométrie ────────────────────────────────────────────────────────────────
CRS_NATIF          = "EPSG:2154"          # Lambert-93
RESOLUTION_M       = 0.5
DALLE_KM           = 1
PX_PAR_DALLE       = int(DALLE_KM * 1000 / RESOLUTION_M)   # 2000
SEUIL_DALLE_VALIDE = 500_000              # GeoTIFF 2000² DEFLATE après conversion

# Tranche de hauteur réintroduite (au-dessus du sol local) et classes LAS
# concernées. Défauts éprouvés sur ruines du Var (murs ~1,5 m) : 0,4-2,5 m,
# classes 1 (non classé — la spec IGN le prévoit pour les murs « plus hauts que
# larges ») et 3/4 (végétation basse/moyenne — mesuré ~70% des points de mur sur
# le site test). NB : ~30% des points de la tranche murs y étaient en classe 5
# (végétation haute) → hors défaut ; tester --dfm-classes 1,3,4,5 si les murs
# sortent incomplets. Ajustables au cas par cas : CLI --dfm-hmin/--dfm-hmax/
# --dfm-classes, ou réglages GUI (case DFM), les deux via set_dfm_params().
_DFM_DEFAUTS       = (0.4, 2.5, (1, 3, 4))
DFM_HMIN, DFM_HMAX = _DFM_DEFAUTS[0], _DFM_DEFAUTS[1]
DFM_CLASSES        = _DFM_DEFAUTS[2]


def set_dfm_params(hmin=None, hmax=None, classes=None):
    """Réglages DFM du run courant (appelé par _load_provider depuis les
    pré-flags --dfm-*). Les valeurs ≠ défauts sont ENCODÉES dans le nom des
    dalles (pattern des ombrages paramétrés) : pas de collision de cache entre
    essais, et le LAZ gardé en cache permet de reconvertir sans retélécharger
    (cf. pre_download)."""
    global DFM_HMIN, DFM_HMAX, DFM_CLASSES
    if hmin is not None:
        DFM_HMIN = float(hmin)
    if hmax is not None:
        DFM_HMAX = float(hmax)
    if classes is not None:
        DFM_CLASSES = tuple(sorted(int(c) for c in classes))
    if DFM_HMIN >= DFM_HMAX:
        raise ValueError(f"dfm-hmin ({DFM_HMIN}) doit être < dfm-hmax ({DFM_HMAX})")


def _suffix():
    """Encodage des réglages ≠ défauts dans le nom de dalle. '' si défauts.
    Ex. hmin=0.3,hmax=3.0 → 'h03-30_' ; classes=(1,3,4,6) → 'c1346_'."""
    s = ""
    if (DFM_HMIN, DFM_HMAX) != _DFM_DEFAUTS[:2]:
        s += f"h{round(DFM_HMIN * 10):02d}-{round(DFM_HMAX * 10):02d}_"
    if DFM_CLASSES != _DFM_DEFAUTS[2]:
        s += "c" + "".join(str(c) for c in DFM_CLASSES) + "_"
    return s


# ── Nommage ──────────────────────────────────────────────────────────────────
_NOM_RE = re.compile(r"fr_dfm05_(?:h[\d-]+_)?(?:c\d+_)?(\d+)_(\d+)\.tif$")


def dalle_filename(x_km, y_km):
    return f"fr_dfm05_{_suffix()}{int(x_km)}_{int(y_km)}.tif"


def _laz_filename(x_km, y_km):
    """Nom du nuage LAZ gardé en cache — SANS réglages (partagé entre essais)."""
    return f"fr_dfm05_{int(x_km)}_{int(y_km)}.laz"


def dalle_subdir(x_km):
    return f"{int(x_km)}"


def subdir_from_name(nom):
    m = _NOM_RE.match(nom)
    return m.group(1) if m else None


def dalle_url(x_km, y_km):
    raise NotImplementedError("fr-ign-dfm : URL via WFS dalle → discover_dalles()")


def dalles_pour_bbox(x1, y1, x2, y2):
    raise NotImplementedError("fr-ign-dfm : index WFS → discover_dalles()")


# ── Découverte (WFS IGN LiDAR HD, mutualisée — typename NUAGES-DE-POINTS) ────
def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    from providers import common
    dalles = common.ign_lidar_hd_dalles(
        bbox_natif, 2154, dalle_filename,
        typename="IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle")
    if dalles is None:
        return None
    if dalles:
        print(f"  FR DFM (LiDAR HD LAZ): {len(dalles)} tile(s) in the bbox "
              f"(~{len(dalles) * 205} MB of point cloud to download!)")
    else:
        print("  FR DFM: no LiDAR HD point-cloud tile here (not flown yet?)")
    return dalles


# ── Hooks : LAZ persistant + conversion DFM ──────────────────────────────────
def pre_download(chemin):
    """Hook cœur (avant réseau) : si le nuage LAZ de cette dalle est déjà en
    cache (gardé par post_fetch), reconvertir en ~20-30 s au lieu de
    retélécharger ~205 Mo — c'est ce qui rend les réglages DFM ajustables au
    cas par cas sans coût réseau. Retourne True si la dalle a été produite."""
    from pathlib import Path as _P
    chemin = _P(chemin)
    m = _NOM_RE.match(chemin.name)
    if not m:
        return False
    laz = chemin.parent / _laz_filename(m.group(1), m.group(2))
    if not laz.exists() or laz.stat().st_size < 1_000_000:
        return False
    from providers import common
    print(f"  DFM {chemin.name}: rebuilding from cached point cloud "
          f"({laz.name}, no re-download)...", flush=True)
    common.las_to_dfm(laz, chemin, crs_epsg=2154,
                      resolution=RESOLUTION_M,
                      hmin=DFM_HMIN, hmax=DFM_HMAX,
                      classes_low=DFM_CLASSES)
    return True


def post_fetch(chemin):
    """Le download est un COPC LAZ (magic LASF), écrit sous un nom .tif par le
    cœur. Conversion DFM via common.las_to_dfm (binning sol + réinjection des
    retours bas non-sol dans les trous), ~20-30 s/dalle, ~1 Go RAM. Le LAZ est
    GARDÉ en cache (~205 Mo/dalle) pour reconvertir à réglages différents sans
    retélécharger (cf. pre_download) — le supprimer à la main libère l'espace."""
    from pathlib import Path as _P
    chemin = _P(chemin)
    try:
        with open(chemin, "rb") as fh:
            magic = fh.read(4)
    except OSError:
        return
    if magic != b"LASF":
        return  # déjà un GeoTIFF (ou erreur → validateur)

    from providers import common
    m = _NOM_RE.match(chemin.name)
    laz = (chemin.parent / _laz_filename(m.group(1), m.group(2)) if m
           else chemin.with_suffix(".laz"))
    chemin.replace(laz)
    print(f"  DFM {chemin.name}: converting ~34M-pt cloud (~20-30 s)...",
          flush=True)
    common.las_to_dfm(laz, chemin, crs_epsg=2154,
                      resolution=RESOLUTION_M,
                      hmin=DFM_HMIN, hmax=DFM_HMAX,
                      classes_low=DFM_CLASSES)
