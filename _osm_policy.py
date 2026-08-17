"""Politiques pures de filtrage et de cache du domaine OSM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


OSM_TAG_RE = re.compile(
    r"^[\w:][\w:.\-*/+ ]*(=[\w:.\-*/+, ]*)?$",
    re.UNICODE,
)


def valider_osm_tags(osm_tags):
    """Retourne le premier filtre hors grammaire Osmosis, sinon ``None``."""
    for token in osm_tags:
        if not OSM_TAG_RE.match(str(token)):
            return token
    return None


def osm_filtre_cles(osm_tags):
    """Parse les filtres en clés ordonnées et ensembles de valeurs admises."""
    cles = []
    valeurs = {}
    for token in osm_tags or ():
        token = str(token)
        if "=" in token:
            cle, valeur = token.split("=", 1)
            cle = cle.strip()
            ensemble = {item.strip() for item in valeur.split(",") if item.strip()}
        else:
            cle, ensemble = token.strip(), None
        if not cle:
            continue
        if cle not in valeurs:
            cles.append(cle)
            valeurs[cle] = set()
        if ensemble is None or "*" in ensemble:
            valeurs[cle] = None
        elif valeurs[cle] is not None:
            valeurs[cle] |= ensemble
    if not cles:
        cles = [
            "highway", "waterway", "natural", "boundary", "landuse",
            "building", "railway", "leisure", "place", "historic",
        ]
        valeurs = {cle: None for cle in cles}
    return cles, valeurs


def osm_cle_match(tags, cles, valeurs_par_cle):
    """Retourne la première paire clé/valeur qui satisfait les filtres."""
    for cle in cles:
        if cle in tags:
            valeurs = valeurs_par_cle.get(cle)
            if valeurs is None or tags[cle] in valeurs:
                return cle, tags[cle]
    return None, None


def hash_config(payload):
    """Construit le hash MD5 court historique d'un payload JSON."""
    contenu = json.dumps(
        payload, sort_keys=True, default=str, ensure_ascii=False,
    )
    return hashlib.md5(contenu.encode("utf-8")).hexdigest()[:16]


def sig_sidecar_stale(chemin, signature):
    """Indique si un sidecar présent diffère de la signature attendue."""
    sidecar = Path(str(chemin) + ".sig")
    try:
        return sidecar.read_text(encoding="utf-8").strip() != signature
    except OSError:
        return False


def sig_sidecar_ecrire(chemin, signature, *, ecrire_texte_atomique):
    """Écrit un sidecar de signature en best-effort."""
    try:
        ecrire_texte_atomique(Path(str(chemin) + ".sig"), signature)
    except OSError:
        pass


def signature_osm(
    bbox_wgs84, osm_tags, osm_pbf, skip_bbox, *, hash_configurer=hash_config,
):
    """Signe les entrées déterminant le contenu d'une carte OSM."""
    return hash_configurer({
        "bbox": (
            None if skip_bbox
            else [round(float(coord), 6) for coord in bbox_wgs84]
        ),
        "tags": sorted(osm_tags) if osm_tags else None,
        "pbf": Path(osm_pbf).name if osm_pbf else None,
    })
