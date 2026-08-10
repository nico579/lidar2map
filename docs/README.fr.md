*[English](README.md) | **Français***

# Documentation de lidar2map

Le [README principal](../README.fr.md) présente l’intérêt de lidar2map et mène
rapidement à une première carte. Cet index indique la page canonique de chaque
sujet. Une information technique ne doit être maintenue qu’à un seul endroit ;
les autres pages y renvoient au lieu de la recopier.

## Bien démarrer

| Besoin | Guide canonique |
|---|---|
| Installer lidar2map et créer une première carte | [Bien démarrer](getting-started.fr.md) |
| Utiliser tous les workflows en ligne de commande | [Référence CLI](cli.fr.md) |
| Choisir une visualisation du relief | [Ombrages LiDAR](shadings.fr.md) |
| Choisir le bon format pour le téléphone ou le SIG | [Formats et applications](formats.fr.md) |
| Vérifier les pays, résolutions, comptes et clés | [Fournisseurs et couverture](providers.fr.md) |
| Lancer, reprendre ou arrêter un traitement sur une VM Ubuntu | [Exécution distante](remote.fr.md) |

## Utilisation avancée

| Sujet | Guide |
|---|---|
| Structures en élévation et nuages de points classés | [DFM, LAZ et CSF](dfm.fr.md) |
| Construire, empaqueter, mettre à jour et dépanner l’application | [Build et déploiement](../BUILD.md) |
| Sources d’altitude évaluées, y compris celles écartées | [Roadmap des fournisseurs LiDAR](lidar_providers_roadmap.md) *(anglais)* |
| Sources de données, licences et remerciements | [Licences des données](data-licenses.fr.md) |

## Contribuer

- [Ajouter ou maintenir un fournisseur LiDAR](contributing-providers.fr.md)
- [Ouvrir une issue](https://github.com/nico579/lidar2map/issues) pour un bug,
  une zone non couverte ou un problème de documentation.
- Le code est distribué sous [GNU GPL v3](../LICENSE).

## Dossiers d’ingénierie

Les pages suivantes conservent les revues de conception et investigations
techniques. Elles sont utiles aux mainteneurs, mais ne constituent pas des
instructions utilisateur actuelles :

- [Journal des revues LAZ / DFM / CSF](dfm_reviews.md)
- [Plan de refonte de `lidar2map.py` et tests de non-régression](plan_refonte.fr.md)
- [Conception de l’unification de l’exécution distante](evolution_execution_distante.md)
- [Investigation du bootstrap Python 3.12](correctif_bootstrap_python312_multiplateforme.md)
- [Investigation de la parallélisation warp/overviews/MBTiles](correctif_parallelisation_warp_overviews_mbtiles.md)

En cas de contradiction, les guides utilisateur et l’aide du programme actuel
font foi.
