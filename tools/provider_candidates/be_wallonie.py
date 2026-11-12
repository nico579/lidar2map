"""Prototype non qualifié : MNT SPW 2021–2022 transformé par Mapterhorn.

Ancienne piste conservée pour la recherche, exclue du catalogue actif.
Ne pas proposer ce prototype pour intégration : priorité au MNT SPW natif.
Tests natifs et limite d'accès : docs/native-wallonie-slovaquie.fr.md.
Précision après transformation Mapterhorn non validée.

Accès anonyme par petites tuiles Terrarium z17. Masque de couverture
« bewallonie » pour écarter le fond GLO-30 hors de cette source. Reprojection
sur une grille métrique locale à 0,5 m pour les calculs de relief.
"""

from tools.provider_candidates._mapterhorn import MapterhornProvider

NAME = "Wallonie — MNT SPW 0,5 m via Mapterhorn"
CODE = "be-wallonie"
COUNTRY = "be"
LICENSE = "CC BY 4.0 — Service public de Wallonie (SPW), distribution Mapterhorn"
DOC_URL = "https://geoportail.wallonie.be/catalogue/a004e570-99d6-4fe5-b83d-49b774409278.html"
CRS_NATIF = "EPSG:3812"
SOURCE_RESOLUTION_M = 0.5
SEUIL_DALLE_VALIDE = 32
DOWNLOAD_WORKERS_MAX = 4

_provider = MapterhornProvider(prefix="be_mapterhorn_v2", source="bewallonie",
                              zoom=17, extent=(2.8, 49.45, 6.5, 50.9),
                              crs=CRS_NATIF, resolution=0.5)
RESOLUTION_M = _provider.resolution
DALLE_KM = 1  # nominal ; le tuilage réel est XYZ, pas une grille kilométrique.
PX_PAR_DALLE = 2000  # estimation pour une dalle nominale de 1 km, pas la taille WebP.
dalle_filename = _provider.dalle_filename
subdir_from_name = _provider.subdir_from_name
discover_dalles = _provider.discover_dalles
post_fetch = _provider.post_fetch
