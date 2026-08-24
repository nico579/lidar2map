"""Préchargement asynchrone d'un morceau terrain, sans dépendance au monolithe."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DependancesPrefetchDalles:
    """Coutures tardives utilisées par :class:`PrefetchDalles`."""

    espace_libre_go: Callable
    decouvrir_et_telecharger_ombrage: Callable
    thread_factory: Callable
    imprimer: Callable = print


class PrefetchDalles:
    """Précharge au plus un morceau d'avance, sans modifier le manifeste.

    Les erreurs du travail de fond restent best-effort : le résultat devient
    ``None`` afin que le chemin synchrone normal reprenne le téléchargement.
    """

    def __init__(self, dependances):
        self._dependances = dependances
        self._thread = None
        self._cle = None
        self._resultat = None

    def lancer(self, args, manifeste, racine_pr, nom_zone, sz, cle):
        if self._thread is not None:
            return
        seuil = getattr(args, "min_free_gb", 0.0) or 0.0
        if seuil > 0 and self._dependances.espace_libre_go(racine_pr) < 2 * seuil:
            return
        nom_z = f"{nom_zone}_{cle}"
        bbox = tuple(sz[2:])

        def _travail():
            try:
                self._resultat = (
                    self._dependances.decouvrir_et_telecharger_ombrage(
                        args,
                        bbox,
                        nom_z,
                        nom_zone,
                        manifeste,
                        cle,
                        quiet=True,
                    )
                )
            except Exception as exc:
                self._dependances.imprimer(
                    f"  ⚠ Prefetch {cle}: {type(exc).__name__}: {exc} "
                    f"(ignoré, retéléchargement normal à son tour)"
                )
                self._resultat = None

        self._cle = cle
        self._resultat = None
        self._thread = self._dependances.thread_factory(
            target=_travail, daemon=True
        )
        self._thread.start()

    def recuperer(self, cle):
        """Attend et consomme le résultat correspondant à ``cle``."""
        if self._thread is None or self._cle != cle:
            return None
        self._thread.join()
        resultat = self._resultat
        self._reinitialiser()
        return resultat

    def purger(self):
        """Attend puis oublie un éventuel travail résiduel en fin de run."""
        if self._thread is not None:
            self._thread.join()
            self._reinitialiser()

    def _reinitialiser(self):
        self._thread = None
        self._cle = None
        self._resultat = None
