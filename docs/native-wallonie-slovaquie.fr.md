# Wallonie et Slovaquie : qualification des sources natives

Tests du 3 octobre 2026. **Les deux MNT natifs conviennent à la prospection archéologique des formes du terrain, avec des limites. La Slovaquie peut être proposée en provider automatique natif ; l'accès wallon reste à préparer.** Aucun contrôle archéologique sur des vestiges connus ni levé de terrain indépendant n'a été réalisé ici.

| Source | Grille et qualité documentée | Avis pour lidar2map | Accès natif testé |
|---|---|---|---|
| SPW Wallonie, MNT 2021–2022 | 0,5 m ; précision altimétrique absolue annoncée d'environ 0,12 m ; couverture non lissée | Bon candidat pour talus, fossés, terrasses, chemins et autres microformes du sol. La classification et les lacunes locales restent déterminantes. | GeoTIFF officiel récupéré partiellement ; lecture et calculs réussis. Provider automatique **non prêt**. |
| ÚGKK Slovaquie, DMR 5.0 | 1 m ; contrôle publié de 0,05 m pour Bratislava et 0,06 m pour Banská Štiavnica ; densités moyennes des derniers retours de 21 et 40 points/m² dans ces secteurs | Exploitable pour les formes de plusieurs mètres. Le pas de 1 m limite la restitution des structures étroites, même si le contrôle altimétrique est bon. | WCS officiel anonyme ; téléchargement par le moteur lidar2map, raccords et ombrages réussis. Candidat **prêt à soumettre à validation**. |

Sources : [fiche SPW](https://geoportail.wallonie.be/catalogue/a004e570-99d6-4fe5-b83d-49b774409278.html), [tableau officiel des contrôles slovaques](https://www.gku.sk/files/geoportal/zbgis/lls/parametre-lokality-zberu-udajov-lls-1-cyklus.pdf).

Les densités citées concernent les derniers retours, **pas uniquement les points sol sous forêt**. Les contrôles slovaques portent sur des surfaces ouvertes et stabilisées : ces chiffres ne garantissent pas la même précision sous un couvert dense. Les vols majoritairement hivernaux et la classification des points sol favorisent la prospection ; ils ne garantissent pas la détection de chaque vestige. Voir les [spécifications du premier cycle](https://www.gku.sk/geoportal/zbgis/lls/1-cyklus/).

Ces sources sont des **MNT officiels dérivés du LiDAR**, donc déjà classifiés, interpolés et, pour la Slovaquie, mosaïqués par le producteur. Leur accès direct évite les transformations supplémentaires de Mapterhorn. Les bâtiments et la végétation sont retirés : un mur classé comme bâtiment peut disparaître. Pour reprendre la classification ou rechercher des vestiges ambigus, les nuages de points restent préférables.

## Slovaquie : provider natif préparé

Le [service WCS publié par GKÚ](https://www.gku.sk/geoportal/inspire/ukladacie-sluzby/) expose `el__EL.GridCoverage`, identifié comme le DMR 5.0. Le candidat [sk_ugkk.py](../tools/provider_candidates/sk_ugkk.py) utilise directement `inspirews.skgeodesy.sk`. Il remplace notre ancien prototype Mapterhorn et demeure hors du catalogue actif.

L'extraction conserve la grille officielle de 1 m en EPSG:3046, avec une bande Float32 et son NoData. Les requêtes ne demandent ni changement de CRS, ni mise à l'échelle, ni interpolation. Les bornes entières sont nécessaires : le premier essai avec des demi-pixels donnait 399 × 399 pixels et un décalage. Ce comportement a été corrigé dans le candidat, puis contrôlé.

**Référence verticale : hauteurs ellipsoïdales ETRS89**, en mètres. Ce sont les altitudes de la distribution officielle ETRS89, différentes des altitudes Bpv de l'autre distribution native. Il ne faut pas les mélanger pour une comparaison altimétrique absolue. Les métadonnées et le fichier TFW de l'archive originale correspondent à la grille du WCS ; ces petits membres ZIP ont été extraits avec vérification de leur CRC.

Tests réalisés sur deux zones de 400 × 400 m, près de Bratislava et de Banská Štiavnica :

- Six dalles natives téléchargées par le moteur existant de lidar2map, puis recompressées sans perte.
- Deux comparaisons entre la mosaïque recadrée et une extraction WCS indépendante de la même zone : **320 000 altitudes identiques bit pour bit**, alignement compris.
- LRM et SVF générés par l'orchestrateur existant ; fichiers non vides et résolutions natives conservées.
- Tests de refus des images RGB, du mauvais CRS, du pas incorrect, du décalage, des altitudes incohérentes et du NoData manquant.

L'égalité des extractions recoupées prouve la conservation des pixels dans le téléchargement, la recompression et l'assemblage testés. Ce n'est pas une comparaison pixel par pixel avec l'immense TIFF national, ni une mesure de précision sur le terrain.

## Wallonie : donnée compatible, accès automatique non qualifié

Le GeoTIFF natif de la province du Brabant wallon est en EPSG:3812, à 0,5 m, Float32, NoData −9999 ; les altitudes sont référencées au Deuxième Nivellement Général. Le téléchargement provincial annoncé fait 13 Go. L'URL publique testée répond HTTP 200 en ignorant la demande HTTP Range : lire une zone arbitraire dans ce ZIP n'est donc pas possible par cette méthode.

Le test a récupéré seulement les **32 premiers Mio** de cette archive officielle. Après décompression bornée, les strips TIFF complets permettent un échantillon valide de 256 × 256 pixels, soit 128 × 128 m, près de 4,749439° E / 50,806357° N. Son recadrage conserve les altitudes bit pour bit ; les calculs LRM et SVF réussissent. Le CRC global de l'archive n'a pas été vérifié, puisqu'elle n'a pas été téléchargée entièrement. Cet échantillon confirme la compatibilité technique, pas la qualité archéologique de toute la Wallonie.

Le WCS GeoServer examiné propose 45 couvertures d'orthophotos et aucun MNT. Le service ArcGIS du MNT expose la visualisation, sans extension WCS publiée. Le téléchargement personnalisé du catalogue demande une connexion et annonce une livraison par e-mail sous 48 heures. Cette voie nécessite donc une étape utilisateur, ou la préparation d'un cache natif local ; elle n'a pas été présentée comme un téléchargement automatique déjà opérationnel.

Le fichier expérimental `be_wallonie.py` reste une ancienne piste Mapterhorn signalée comme non candidate à l'intégration. Aucun provider wallon automatique natif n'est proposé comme prêt sur la seule base de ces tests.

## DMR 6 slovaque : plus fin, accès distinct

Le [deuxième cycle](https://www.gku.sk/geoportal/zbgis/lls/2-cyklus/) propose un MNT de 0,5 m, avec une exigence de densité d'au moins 15 points/m² et de précision verticale du nuage de 0,10 m. Ce dernier chiffre concerne le nuage, pas une garantie de précision du MNT sous forêt. La [distribution](https://www.gku.sk/geoportal/zbgis/lls/poskytovanie/) couvre certaines localités et propose des ZIP ou des extractions MAPKA livrées par e-mail.

L'index ZIP du LOT04 a été testé sans téléchargement global : il contient un TIFF de secteur compressé, pas de petites dalles accessibles indépendamment. Le WCS testé expose uniquement le DMR 5.0. Le candidat préparé ne prétend donc pas fournir le DMR 6, ni le remplacer par un DMR 5 rééchantillonné à 50 cm.

## Résultats et reproduction

Les [résultats JSON](native-wallonie-slovaquie.results.json) contiennent les URL, empreintes SHA-256, propriétés des GeoTIFF et résultats des comparaisons. Les réponses HTTP et les entrées restent dans `cache/native-provider-validation/`. Les [aperçus](native-wallonie-slovaquie-apercus.png) illustrent les trois échantillons techniques ; ils ne constituent pas un contrôle de vestiges.

```powershell
rtk proxy python -X utf8 tools/provider_candidates/test_native_access.py wallonia_prefix
rtk proxy python -X utf8 tools/provider_candidates/validate_native_providers.py
rtk proxy python -X utf8 -m unittest discover -s tools/provider_candidates/tests
```

La validation utilise les candidats uniquement dans son propre processus. Le catalogue actif conserve ses 66 providers ; aucun fichier des providers existants n'a été modifié. L'ajout actif reste soumis à la validation explicite demandée par l'utilisateur.
