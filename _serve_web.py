"""Réglages de lidar2map pour le serveur web local de nico579-commons.

Tout le serveur (provenance des requêtes, routes /api/*, fichiers statiques,
réponses JSON, écoute sur l'hôte de confiance) est dans
nico579_commons.serveweb, le même pour les quatre applications. Ce qui reste
ici est propre à lidar2map : le nom de sa variable d'environnement de proxy
local, et la lecture des paramètres des quatre routes GET qui en prennent
(usage, autocomplete-ville, projets, browse-dir).
"""

from nico579_commons import serveweb


def _premier(requete: dict, nom: str, defaut=""):
    return (requete.get(nom) or [defaut])[0]


def _arguments_usage(requete: dict) -> tuple:
    cfg = {}
    for cle in ("cache_dir", "production_dir"):
        if requete.get(cle):
            cfg[cle] = requete[cle][0]
    return (cfg,)


def _arguments_autocomplete_ville(requete: dict) -> tuple:
    return _premier(requete, "prefix"), _premier(requete, "country", "fr")


def _arguments_projets(requete: dict) -> tuple:
    return (_premier(requete, "dossier", None),)


def _arguments_browse_dir(requete: dict) -> tuple:
    extensions = [e for e in _premier(requete, "exts").split(",") if e]
    return (_premier(requete, "path"), _premier(requete, "kind"), extensions,
            _premier(requete, "mode"))


class Handler(serveweb.Handler):
    variable_proxy_local = "LIDAR2MAP_TRUSTED_LOOPBACK_PROXY"
    arguments_get = {
        "usage": _arguments_usage,
        "autocomplete-ville": _arguments_autocomplete_ville,
        "projets": _arguments_projets,
        "browse-dir": _arguments_browse_dir,
    }
