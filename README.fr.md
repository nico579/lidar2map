*[English](README.md) | **Français***

# lidar2map

**Transformez les données LiDAR publiques en cartes de relief prêtes pour le terrain.**

Choisissez une zone. lidar2map récupère les données d’altitude disponibles,
produit des visualisations qui font ressortir les microreliefs, puis exporte
des cartes pour Locus Map, OsmAnd, TwoNav ou un logiciel SIG. L’application
autonome propose une interface graphique et une CLI sans environnement Python
ni chaîne SIG à installer.

Terrasses, fossés, chemins creux, talus et enceintes peuvent ainsi apparaître
là où la photographie aérienne et les cartes classiques montrent peu de
choses. lidar2map ne détecte **pas** automatiquement des sites archéologiques :
il produit des reliefs destinés à l’interprétation humaine.

![La même zone en photographie aérienne, dans OpenStreetMap et en SVF LiDAR](screenshots/LIDAR_Samples/relief_3views.jpg)

*La photographie aérienne et OpenStreetMap masquent l’essentiel du microrelief.
Le Sky-View Factor calculé depuis le LiDAR révèle les terrasses et les anciens
chemins.*

**[Télécharger la dernière version](https://github.com/nico579/lidar2map/releases/latest)** ·
**[Créer une première carte](docs/getting-started.fr.md)** ·
**[Vérifier la couverture LiDAR](#couverture-lidar)** ·
**[Parcourir la documentation](docs/README.fr.md)**

## D’une zone à une carte de terrain

| 1. Choisir une zone | 2. Révéler le relief | 3. Emporter la carte |
|---|---|---|
| Saisissez une commune, un point GPS, une emprise WGS84, un département français ou une région. | lidar2map sélectionne une source publique, télécharge les données manquantes et calcule une ou plusieurs visualisations du relief. | Exportez en MBTiles, SQLiteDB, RMAP, Mapsforge ou GeoJSON pour un téléphone ou un logiciel SIG. |

La première récupération des données nécessite une connexion réseau. Les
sources téléchargées sont mises en cache et les fichiers valides sont
réutilisés ; la carte produite peut ensuite être utilisée hors connexion sur le
terrain.

Les usages typiques comprennent la prospection archéologique et paysagère, la
comparaison avec l’imagerie historique avant que les traces ne disparaissent
sous des usages du sol plus récents, la cartographie IGN hors connexion pour la
randonnée en France, ainsi que la création de fonds précis pour la spéléologie
ou l’exploration hors de la couverture des applications généralistes.

## Couverture LiDAR

[![Couverture LiDAR disponible dans lidar2map](coverage.fr.png)](coverage.geojson)

lidar2map propose un même parcours de traitement au-dessus de sources
d’altitude nationales et régionales de nombreux pays. La résolution, la
couverture exacte, les identifiants requis et la disponibilité du DFM varient
selon la source. Les États-Unis et le Canada sont pris en charge, mais ne sont
pas dessinés comme des polygones nationaux : leur couverture haute résolution
n’est pas continue sur tout le territoire.

- [Ouvrir la carte de couverture interactive](coverage.geojson)
- [Voir toutes les sources, résolutions, authentifications et contraintes](docs/providers.fr.md)
- [Consulter les sources évaluées mais non intégrées](docs/lidar_providers_roadmap.md) *(anglais)*

Les traitements raster IGN et vectoriels BD TOPO restent propres à la France.
Les cartes vectorielles OSM peuvent être produites à l’international ; la
sélection Geofabrik automatique couvre actuellement la France, tandis qu’un
autre pays peut être traité à partir d’un fichier PBF fourni.

## Démarrage rapide

### Interface graphique

1. Téléchargez l’archive Windows, Ubuntu ou macOS depuis la page
   [Releases](https://github.com/nico579/lidar2map/releases/latest).
2. Décompressez-la en gardant le lanceur à côté de
   `lidar2map_bundle.zip`.
3. Lancez lidar2map sans argument.
4. Choisissez une petite zone, laissez **Télécharger les données manquantes**
   activé et effectuez un premier rendu LRM avant d’agrandir la zone ou
   d’ajouter d’autres visualisations.

Aucune installation de Python n’est nécessaire. Les procédures par système,
les dossiers du premier lancement, l’installation depuis les sources, la file
d’attente, l’historique, l’arrêt propre, la planche d’assemblage et la
désinstallation sont détaillés dans **[Bien démarrer](docs/getting-started.fr.md)**.

![Traitement LiDAR dans l’interface graphique](screenshots/GUI/lidar_dtm.PNG)

### Ligne de commande

Un traitement LiDAR demande un workflow, un provider et une zone explicites.
Une commune ou un point GPS exige aussi la largeur du carré à traiter :

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2
```

Sur un cache vide, cette commande télécharge les données manquantes, calcule un
LRM et crée une carte MBTiles. Les données valides existantes ne sont jamais
téléchargées à nouveau, sauf avec `--download-force` ou
`--download-overwrite`.

Le comportement normal réutilise déjà toutes les sources valides du cache et
ne télécharge que celles qui manquent. Utilisez `--no-download` pour interdire
le téléchargement des données sources et exiger un cache déjà rempli ; les
sources absentes ne seront pas récupérées. Les projets GPS ou définis par une
emprise reçoivent automatiquement un nom stable ; `--zone-name` reste
disponible pour choisir un nom lisible.

La **[référence CLI complète](docs/cli.fr.md)** décrit chaque workflow, valeur
par défaut, interaction entre paramètres, action de maintenance et exemple
reproductible.

## Ce que lidar2map peut produire

### Reliefs LiDAR adaptés à la prospection

Toutes les sources alimentent le même pipeline de calcul. Pour commencer :

| Visualisation | À choisir en premier lorsque… |
|---|---|
| **LRM** | Vous voulez une première lecture rapide des anomalies locales. C’est le défaut de l’interface et de la CLI. |
| **SVF** | Vous recherchez des fossés, terrasses, enceintes ou chemins creux sous la végétation. |
| **Ombrage multidirectionnel** | Vous voulez un relief intuitif qui ne dépende pas d’une seule direction d’éclairage. |

Pente, openness positif ou négatif, RRIM, VAT, e4MSTP, ombrages directionnels,
instances paramétrées et préréglages adaptés à la résolution sont également
disponibles. Leur histoire, leurs formules, paramètres, schémas, avantages,
limites et méthode de comparaison sont regroupés dans
**[Choisir les visualisations LiDAR](docs/shadings.fr.md)**.

Les MNT de sol nu retirent volontairement de nombreuses structures encore en
élévation. Lorsque la source publie un nuage de points classé suffisamment
dense, le traitement alternatif DFM/LAZ peut réintroduire des murs candidats
à partir des classes du producteur ou d’un filtre de simulation de tissu. Ce
traitement est volumineux, destiné à de petites zones ciblées et exige toujours
une interprétation humaine et une validation de terrain. Voir
**[DFM, LAZ et CSF](docs/dfm.fr.md)**.

### Cartes de contexte

- **Raster classique :** Plan IGN, orthophotographies actuelles et historiques,
  État-Major, Pléiades et autres couches françaises ; imagerie USGS NAIP aux
  États-Unis.
- **Vectoriel :** OSM en Mapsforge ou GeoJSON, ou IGN BD TOPO en France.
- **Surcouche vectorielle transparente :** chemins, routes, rivières et autres
  objets sélectionnés, rasterisés au-dessus du LiDAR dans OsmAnd.
- **Post-traitement :** fusionner des exports GeoJSON voisins ou
  complémentaires ; redécouper un MBTiles en grille ou en cellules de largeur
  fixe, puis convertir chaque partie indépendamment.

Toutes les couches, contraintes des applications, conversions et procédures
d’import sont regroupées dans
**[Formats de sortie et applications mobiles](docs/formats.fr.md)**.

## Emporter le résultat sur un téléphone

| Cible | Sortie lidar2map recommandée |
|---|---|
| Locus Map / OruxMaps | MBTiles pour le relief raster ; `.map` Mapsforge pour le vectoriel |
| OsmAnd | `.sqlitedb` pour une carte raster ou une surcouche transparente |
| TwoNav / CompeGPS | RMAP |
| QGIS et logiciels SIG | MBTiles, GeoTIFF intermédiaires ou GeoJSON |

Après un traitement, le bouton 📲 de l’interface partage le projet sur le réseau
Wi-Fi local et affiche un QR code. Aucun fichier n’est envoyé vers Internet.
L’équivalent CLI est `--serve --zone-name NOM_DU_PROJET`.

Exemple de rendu sur Locus et OsmAnd :

<p align="center">
  <img src="screenshots/LIDAR_Samples/Svf_LocusMap.jpg" alt="Relief SVF dans Locus Map" width="320">
  <img src="screenshots/LIDAR_Samples/LRM_OSMAND_Transparent.jpg" alt="Surcouche LRM dans OsmAnd" width="320">
</p>

## Grands traitements, automatisation et VM distantes

- Les grandes zones sont parcourues morceau par morceau au lieu d’être chargées
  entièrement en mémoire. Le SVF et l’openness restent gourmands à l’échelle de
  chaque morceau.
- Un manifeste enregistre les morceaux terminés pour permettre un arrêt propre
  et une reprise.
- `--split-width`, la découpe en grille, le nettoyage, le seuil d’espace disque
  et les planches d’assemblage rendent les gros livrables maîtrisables.
- La file d’attente de l’interface traite plusieurs zones sans surveillance ;
  l’échec d’un élément n’arrête pas les suivants.
- Lidar2map peut préparer une VM Ubuntu 24.04/26.04, lancer un
  traitement sans bureau dans une session isolée, le surveiller, se reconnecter
  et synchroniser progressivement les résultats.
- `--block i/M` répartit une même emprise entre plusieurs VM.

Arrêter la surveillance locale n’oblige pas à arrêter le traitement sur la VM.
Lorsqu’une session distante précise est arrêtée, ses fichiers sont conservés
par défaut afin de permettre l’analyse ou la reprise. La purge constitue une
action séparée et explicite ; elle ne supprime jamais le cache des sources ni le
cache de production partagés.

Voir **[Exécution distante et gestion des sessions](docs/remote.fr.md)** et la
**[référence CLI](docs/cli.fr.md)**.

## Documentation

| Sujet | Page canonique |
|---|---|
| Installation, première carte, interface, file, historique, planche | [Bien démarrer](docs/getting-started.fr.md) |
| Tous les paramètres CLI, défauts, exemples et actions de maintenance | [Référence CLI](docs/cli.fr.md) |
| Méthodes de relief et références scientifiques | [Visualisations LiDAR](docs/shadings.fr.md) |
| DFM/LAZ/CSF et structures en élévation | [Guide DFM](docs/dfm.fr.md) |
| Formats, applications, transfert téléphone, raster et vectoriel | [Formats et applications](docs/formats.fr.md) |
| Pays, couverture, identifiants et contraintes des sources | [Sources et couverture](docs/providers.fr.md) |
| VM, sessions, reprise, arrêt, purge et répartition multi-VM | [Exécution distante](docs/remote.fr.md) |
| Build, bundle, déploiement et dépannage | [BUILD.md](BUILD.md) |
| Développement d’une nouvelle source | [Ajouter un fournisseur](docs/contributing-providers.fr.md) |
| Sources de données, licences et remerciements | [Licences des données](docs/data-licenses.fr.md) |

L’[index documentaire](docs/README.fr.md) identifie également les dossiers
d’ingénierie historiques afin qu’ils ne soient pas confondus avec les
instructions utilisateur actuelles.

## État du projet et usage responsable

lidar2map est un projet indépendant, largement testé sous Windows 10/11. Les
exécutables Linux et macOS sont pris en charge mais ont reçu moins de tests de
terrain ; les cas connus par plateforme sont recensés dans
[BUILD.md](BUILD.md). Les retours et rapports reproductibles sont les bienvenus
dans les [issues GitHub](https://github.com/nico579/lidar2map/issues).

Utilisez le LiDAR et l’imagerie historique de manière responsable, dans le
respect des règles locales sur le patrimoine, l’accès, la vie privée et les
licences. lidar2map n’est pas destiné à guider la détection de métaux ni la
publication de coordonnées archéologiques sensibles.

## Licence, auteur et crédits

Le code est distribué sous **GNU General Public License v3.0** ; voir
[LICENSE](LICENSE). Toute redistribution modifiée doit fournir le code source
correspondant sous la même licence.

Conçu et architecturé par **Nicolas Martin**
([@nico579](https://github.com/nico579)). Code développé avec l’assistance de
Claude (Anthropic) comme outil de développement.

Les agences cartographiques nationales, OpenStreetMap/Geofabrik, les auteurs
scientifiques et les outils libres embarqués sont crédités avec leurs licences
dans **[Licences des données et remerciements](docs/data-licenses.fr.md)**.
