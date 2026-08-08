*[English](data-licenses.md) | **Français** · [Catalogue des fournisseurs](providers.fr.md) · [Index de la documentation](README.fr.md)*

# Sources de données, licences et remerciements

lidar2map associe son propre code sous GPL à des données publiques
altimétriques, photographiques et vectorielles publiées sous leurs conditions
respectives. Les licences des sources restent applicables aux données
téléchargées et peuvent imposer une attribution lors de la redistribution des
données ou de produits dérivés.

Cette page centralise les remerciements actuellement portés par le projet. Le
[catalogue des providers](providers.fr.md) précise accès et couverture pour
chaque source ; chaque module provider porte aussi les métadonnées `LICENSE` et
`DOC_URL`. Pour une redistribution ou un usage professionnel, toujours
vérifier les conditions à jour auprès du producteur.

## Code lidar2map

lidar2map est distribué sous **GNU General Public License v3.0** ; voir
[LICENSE](../LICENSE).

Vous pouvez utiliser, modifier et redistribuer le logiciel selon les termes de
la GPL v3. En particulier, si vous redistribuez une version modifiée, vous devez
fournir le code source modifié sous la même licence.

## Sources de données

- **IGN** (Institut national de l'information géographique et forestière) :
  LiDAR HD, BD ORTHO incluant les versions historiques 1950–1995 et BD TOPO,
  sous licence Etalab 2.0.
- **AHN** (Actueel Hoogtebestand Nederland) : AHN4/5 0,5 m, Pays-Bas,
  CC BY 4.0.
- **swisstopo** (Office fédéral de topographie) : swissALTI3D 0,5 m, Suisse,
  open data gratuit © swisstopo.
- **Kartverket** : Nasjonal Høydemodell 1 m, Norvège, CC BY 4.0.
- **Geobasis NRW · LDBV Bayern · LGLN Niedersachsen · TLBG Thüringen** :
  DGM 1 m (1–2 m en Thuringe), Allemagne, Datenlizenz Deutschland
  Namensnennung 2.0.
- **Land Tirol** (tiris) : DGM 0,5 m, Autriche/Tyrol, CC BY 4.0.
- **Environment Agency** (Angleterre) et **DataMapWales / Natural Resources
  Wales** : LIDAR Composite DTM 1 m, Royaume-Uni, Open Government Licence v3.
- **Scottish Government / JNCC** (Scottish Remote Sensing Portal) : LiDAR
  secteur public écossais DTM 0,5 m, Écosse, Open Government Licence v3.
- **ACT** (Administration du Cadastre et de la Topographie) : BD-L-Lidar 2024
  MNT 0,5 m, Luxembourg, CC0.
- **USGS** : 3DEP / The National Map 1 m, USA, domaine public.
- **GSI** (Autorité de l'information géospatiale du Japon) : tuiles d'altitude
  DEM5A 5 m, Japon, conditions GSI.
- **Digitaal Vlaanderen** : DHMV II DTM/SVF/Hillshade, Flandre, Open Data
  Licentie Vlaanderen.
- **Maanmittauslaitos** : modèle d'élévation 2 m, Finlande, CC BY 4.0.
- **Klimadatastyrelsen / Datafordeler** : DHM DTM 0,4 m, Danemark, CC BY.
- **Geological Survey Ireland** : LiDAR DTM 1 m, Irlande, CC BY 4.0.
- **Natural Resources Canada** : HRDEM Mosaic 1 m, Canada, Open Government
  Licence.
- **ČÚZK** (office tchèque de cartographie et du cadastre) : DMR 5G 1 m,
  Tchéquie, Open Data.
- **IGN España / CNIG** : MDT 5 m, Espagne, CC BY 4.0.
- **ICGC** (Institut Cartogràfic i Geològic de Catalunya) : MET LiDAR 50 cm,
  Catalogne, CC BY 4.0.
- **GUGiK** (office polonais de géodésie et de cartographie) : NMT 1 m LiDAR
  ISOK, Pologne, données ouvertes.
- **LINZ** (Land Information New Zealand) : DEM 1 m, Nouvelle-Zélande,
  CC BY 4.0.
- **QSpatial** (State of Queensland) et **Spatial Services NSW** : DEM 0,5 m /
  5 m, Australie, CC BY 4.0.
- **Geoscience Australia** : DEM australien dérivé LiDAR 5 m, couverture
  nationale dispersée, CC BY 4.0.
- **Contributeurs OpenStreetMap** : données vectorielles sous
  [Open Database License](https://www.openstreetmap.org/copyright), distribuées
  en extraits régionaux par Geofabrik.

## Moteur de carte vectorielle

- **Apache JMapsforge / mapsforge-map-writer** fournit le moteur de rendu et
  d'écriture des cartes vectorielles hors ligne.

## Figures scientifiques

Le guide des visualisations conserve ses figures scientifiques localement afin
de rester lisible hors connexion. Source, auteur, modification et licence de
chaque figure sont consignés dans
[Sources et licences des figures](images/shadings/README.md).

## Outils intégrés et dépendances d'exécution

L'application distribuée utilise ou embarque :

- GDAL
- osmosis
- py7zr
- pyproj
- NumPy
- SciPy
- Pillow
- ijson
- pywebview

Ces projets conservent leurs propres droits d'auteur et conditions de licence.
Leur inclusion ne les replace pas sous la notice GPL de lidar2map.
