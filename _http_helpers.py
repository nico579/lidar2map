"""Primitives HTTP communes, sans politique propre aux fournisseurs."""

from __future__ import annotations

import urllib.error
import urllib.request


def ouvrir_url(url, headers=None, timeout=15, *, user_agent, request_cls=None,
               urlopen=None):
    """Ouvre une URL en complétant les en-têtes avec le User-Agent commun."""
    request_cls = request_cls or urllib.request.Request
    urlopen = urlopen or urllib.request.urlopen
    entetes = {"User-Agent": user_agent}
    if headers:
        entetes.update(headers)
    requete = request_cls(url, headers=entetes)
    return urlopen(requete, timeout=timeout)


def telecharger_vers_tmp(url, chemin_tmp, timeout=60, *, ouvrir_url,
                         taille_bloc):
    """Télécharge une ressource en streaming et vérifie sa taille annoncée.

    Un HTTP 404 représente une ressource absente et retourne zéro. Les autres
    erreurs HTTP, les réponses XML/HTML et les transferts tronqués sont des
    erreurs visibles afin que l'appelant puisse appliquer sa politique de retry.
    """
    timeout_effectif = max(timeout) if isinstance(timeout, tuple) else timeout
    try:
        reponse = ouvrir_url(url, timeout=timeout_effectif)
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            return 0
        raise IOError(f"HTTP {erreur.code}") from erreur

    with reponse:
        content_type = reponse.headers.get("content-type", "").lower()
        if not content_type.startswith("multipart") and (
                "xml" in content_type or "html" in content_type):
            raise IOError(
                f"server error response ({content_type or 'no content-type'})"
            )

        try:
            content_length = int(reponse.headers.get("content-length", 0))
        except (ValueError, TypeError):
            content_length = 0

        taille = 0
        with open(chemin_tmp, "wb") as fichier:
            while True:
                bloc = reponse.read(taille_bloc)
                if not bloc:
                    break
                fichier.write(bloc)
                taille += len(bloc)

    if content_length > 0 and taille != content_length:
        raise IOError(
            f"Transfert tronqué : reçu {taille} octets, "
            f"attendu {content_length} (Content-Length)"
        )
    return taille
