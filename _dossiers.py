"""Dossiers de lidar2map depuis la 1.54.0 : l'état dans le dossier de données
standard de l'OS, les sorties dans un dossier visible.

L'état, ce sont les préférences, l'historique, la clé API (lidar2map.env) et
les journaux : de petits fichiers que l'utilisateur n'a pas à voir. Les
sorties, ce sont Projets, cache et production : des gigaoctets qu'il cherche,
copie et supprime lui-même, d'où Documents/lidar2map par défaut. C'est la
convention de blink2video et de watch2notif. LIDAR2MAP_HOME, s'il est fourni,
regroupe l'un et l'autre, comme le dossier du programme le faisait jusqu'à la
1.53.

Le dossier d'état s'appelle lidar2map-data et non lidar2map : sous ce nom-là,
le dossier standard est celui où le lanceur d'une version <= 1.54 extrayait
le programme, et la 1.55 le supprime au lancement (voir
_bootstrap_runtime.nettoyer_ancienne_extraction). Les réglages et
l'historique ne doivent pas partir avec lui.

Toute la logique (calcul des dossiers, reprise unique de l'état d'une version
<= 1.53) est dans nico579_commons.dossiers, la même pour les quatre
applications. Ce qui reste ici est propre à lidar2map : ses noms et ses
fichiers.
"""

from nico579_commons.dossiers import Dossiers

DOSSIERS = Dossiers(
    "lidar2map",
    nom_etat="lidar2map-data",
    nom_sorties="lidar2map",
    variable_home="LIDAR2MAP_HOME",
    preferences="preferences.json",
    cle_sorties="dossier_sorties",
    # Ce qu'une version <= 1.53 rangeait dans son dossier de travail.
    fichiers_etat=("preferences.json", "historique.json", "lidar2map.env"),
    dossiers_sorties=("Projets", "cache", "production"),
    marqueur=".lidar2map_etat_migre.json",
)
