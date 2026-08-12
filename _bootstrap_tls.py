"""Configuration TLS précoce et sans dépendance applicative de lidar2map.

Le module ne modifie rien à l'import. Les fonctions reçoivent explicitement
l'environnement et le module ``ssl`` afin de rester testables avant que les
dépendances tierces aient été installées.
"""

from __future__ import annotations


class CertifiIndisponible(ImportError):
    """Signale que le paquet ``certifi`` lui-même n'est pas installé."""


def _charger_certifi():
    try:
        import certifi
    except ModuleNotFoundError as exc:
        if exc.name == "certifi":
            raise CertifiIndisponible("certifi n'est pas installé") from exc
        raise
    return certifi


def _chemin_ca_personnalise(environnement):
    return (
        environnement.get("SSL_CERT_FILE")
        or environnement.get("REQUESTS_CA_BUNDLE")
        or None
    )


def _fabrique_contexte(contexte):
    # Partagé par choix : recharger le bundle CA pour chaque tuile HTTPS serait
    # coûteux. urllib peut y répéter ses réglages ALPN/PHA idempotents ; aucun
    # appelant ne doit affaiblir verify_mode ni check_hostname.
    def creer_contexte():
        return contexte

    return creer_contexte


def _activer_ca_stricte(*, environnement, module_ssl, chemin_ca):
    """Valide puis publie atomiquement une configuration CA stricte."""
    chemin_ca = str(chemin_ca)
    contexte = module_ssl.create_default_context(cafile=chemin_ca)
    fabrique = _fabrique_contexte(contexte)

    # Ne publier l'environnement et la fabrique qu'après validation complète.
    # Une CA explicitement fournie par l'utilisateur garde toujours priorité.
    if not environnement.get("SSL_CERT_FILE"):
        environnement["SSL_CERT_FILE"] = chemin_ca
    if not environnement.get("REQUESTS_CA_BUNDLE"):
        environnement["REQUESTS_CA_BUNDLE"] = chemin_ca
    module_ssl._create_default_https_context = fabrique
    return contexte


def _retablir_fabrique_systeme_stricte(module_ssl):
    """Rétablit le contexte système vérifié, sans fallback non sécurisé."""
    module_ssl._create_default_https_context = module_ssl.create_default_context


def initialiser_tls(
    *,
    environnement,
    module_ssl,
    charger_certifi=_charger_certifi,
):
    """Configure le TLS strict avant le bootstrap et retourne un contexte témoin.

    Une CA utilisateur est prioritaire. Sans CA personnalisée, ``certifi`` est
    utilisé s'il est déjà installé. Lors d'un tout premier lancement sans
    ``certifi``, la fabrique stricte du système reste active : aucun contexte
    HTTPS non vérifiant n'est jamais installé.
    """
    chemin_ca = _chemin_ca_personnalise(environnement)
    if chemin_ca is None:
        try:
            certifi = charger_certifi()
        except CertifiIndisponible:
            _retablir_fabrique_systeme_stricte(module_ssl)
            return None
        chemin_ca = certifi.where()
    return _activer_ca_stricte(
        environnement=environnement,
        module_ssl=module_ssl,
        chemin_ca=chemin_ca,
    )


def restaurer_tls_strict(
    *,
    environnement,
    module_ssl,
    charger_certifi=_charger_certifi,
):
    """Rétablit un TLS strict après l'installation éventuelle de ``certifi``.

    La fonction est idempotente en résultat : chaque appel republie une fabrique
    sûre. Le contexte strict est partagé pour ne pas recharger le bundle CA à
    chaque connexion HTTPS. Si ``certifi`` reste absent et qu'aucune CA utilisateur
    n'est définie, le contexte système strict est conservé.
    """
    return initialiser_tls(
        environnement=environnement,
        module_ssl=module_ssl,
        charger_certifi=charger_certifi,
    )
