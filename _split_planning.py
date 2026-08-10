"""Planification pure des traitements découpés.

Ce module définit la géométrie de la grille, les identifiants stables des
chunks et la signature de reprise. Il ne connaît ni les runners, ni le
manifeste, ni les téléchargements.
"""

from __future__ import annotations

import hashlib
import json
import math
import re


_SIGNATURE_FIELDS = (
    "zoom_min",
    "zoom_max",
    "formats_image",
    "qualite_image",
    "mbtiles",
    "rmap",
    "sqlitedb",
    "shading_specs",
    "shading_preset",
    "svf_gamma",
    "svf_conv",
    "svf_dist",
    "sweep_horizon",
    "layer",
    "style",
    "source",
    "dfm",
    "dfm_ground",
    "elevation_soleil",
)


def _parse_block(spec: str):
    """Parse ``i/M`` en un index et un nombre total de blocs validés."""
    spec = (spec or "").strip()
    if not spec:
        return None
    match = re.match(r"^(\d+)\s*/\s*(\d+)$", spec)
    if not match:
        raise ValueError(
            f"--block attend le format 'i/M' (ex: 1/3), reçu : {spec!r}"
        )
    index, total = int(match.group(1)), int(match.group(2))
    if total < 1 or not 1 <= index <= total:
        raise ValueError(
            f"--block {spec} : il faut 1 ≤ i ≤ M et M ≥ 1"
        )
    return index, total


def _cle_chunk(index_ligne: int, index_colonne: int) -> str:
    """Construit l'identifiant 1-based stable ``LLLxCCC`` d'un chunk."""
    return f"{index_ligne + 1:03d}x{index_colonne + 1:03d}"


def _identite_chunk(nom_zone: str, index_ligne: int, index_colonne: int):
    """Retourne ``(clé, nom de zone suffixé)`` pour un chunk."""
    cle = _cle_chunk(index_ligne, index_colonne)
    return cle, f"{nom_zone}_{cle}"


def _calculer_sous_zones_priori(
    x1,
    y1,
    x2,
    y2,
    n_morceaux,
    cote_km,
    unite_m=True,
    n_cols=0,
    n_rows=0,
):
    """Divise une bbox en sous-zones ordonnées ligne puis colonne.

    Priorité : grille explicite, côté kilométrique borné, nombre de morceaux,
    puis zone entière. Une sous-zone vaut
    ``(index_ligne, index_colonne, x_min, y_min, x_max, y_max)``.
    """
    largeur = x2 - x1
    hauteur = y2 - y1

    if n_cols > 0 and n_rows > 0:
        dx = largeur / n_cols
        dy = hauteur / n_rows
        mode_desc = (
            f"{n_cols * n_rows} morceaux "
            f"({n_rows}×{n_cols}, grille explicite)"
        )
    elif cote_km > 0:
        if unite_m:
            dy = dx = cote_km * 1000
        else:
            latitude_centrale = (y1 + y2) / 2
            dy = cote_km / 111.0
            dx = cote_km / (
                111.0
                * max(0.01, math.cos(math.radians(latitude_centrale)))
            )
        n_rows = max(1, int(math.ceil(hauteur / dy)))
        n_cols = max(1, int(math.ceil(largeur / dx)))
        mode_desc = f"~{cote_km:.0f} km/morceau ({n_rows}×{n_cols})"
    elif n_morceaux > 1:
        meilleure_grille = (1, n_morceaux)
        meilleur_ratio = float("inf")
        for lignes in range(1, int(math.sqrt(n_morceaux)) + 1):
            if n_morceaux % lignes == 0:
                colonnes = n_morceaux // lignes
                ratio = abs(
                    (lignes / colonnes)
                    - (hauteur / max(largeur, 1e-9))
                )
                if ratio < meilleur_ratio:
                    meilleur_ratio = ratio
                    meilleure_grille = (lignes, colonnes)
        n_rows, n_cols = meilleure_grille
        dx = largeur / n_cols
        dy = hauteur / n_rows
        mode_desc = f"{n_morceaux} morceaux ({n_rows}×{n_cols})"
    else:
        n_rows = n_cols = 1
        dx = largeur
        dy = hauteur
        mode_desc = "1 morceau (zone entière)"

    sous_zones = []
    for index_ligne in range(n_rows):
        y_min = y1 + index_ligne * dy
        y_max = min(y_min + dy, y2)
        for index_colonne in range(n_cols):
            x_min = x1 + index_colonne * dx
            x_max = min(x_min + dx, x2)
            sous_zones.append(
                (
                    index_ligne,
                    index_colonne,
                    x_min,
                    y_min,
                    x_max,
                    y_max,
                )
            )
    return sous_zones, mode_desc


def _signature_config(args, sous_zones, provider=None):
    """Calcule la signature stable de géométrie et de contenu d'un split."""
    x_min = min(zone[2] for zone in sous_zones)
    y_min = min(zone[3] for zone in sous_zones)
    pas_x = max(zone[4] - zone[2] for zone in sous_zones)
    pas_y = max(zone[5] - zone[3] for zone in sous_zones)
    grille = [
        round(x_min, 3),
        round(y_min, 3),
        round(pas_x, 3),
        round(pas_y, 3),
    ]
    contenu = {
        champ: getattr(args, champ, None) for champ in _SIGNATURE_FIELDS
    }
    code_provider = getattr(provider, "CODE", None) or getattr(
        provider,
        "__name__",
        None,
    )
    payload = {
        "grille": grille,
        "contenu": contenu,
        "provider": str(code_provider),
    }
    serialise = json.dumps(
        payload,
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    return hashlib.md5(serialise.encode("utf-8")).hexdigest()[:16]


__all__ = (
    "_calculer_sous_zones_priori",
    "_cle_chunk",
    "_identite_chunk",
    "_parse_block",
    "_signature_config",
)
