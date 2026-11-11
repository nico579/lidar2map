# Pays absents de lidar2map et disponibles chez Mapterhorn

Bilan du 3 octobre 2026 pour la prospection archéologique. Le catalogue actif
contient **66 providers dans 27 pays**. Le catalogue Mapterhorn consulté contient
151 sources, rattachées à 32 pays. Leur différence donne **sept pays** : Slovaquie,
Roumanie, Chypre, Islande, Israël, Rwanda et Taïwan. Le fond mondial GLO-30 est
exclu de ce décompte : sa disponibilité mondiale ne constitue pas une couverture
LiDAR fine. Les territoires ultramarins sont regroupés avec leur pays.

**Trois candidats méritent une qualification ; quatre sources sont trop
grossières pour le microrelief recherché.** Aucun provider n'a été ajouté ou
activé. Le classement ci-dessous évalue les données et leur documentation,
sans certifier la précision du produit Mapterhorn au sol.

| Pays / source Mapterhorn | Résolution et couverture | Qualité utile à lidar2map | Avis |
| --- | --- | --- | --- |
| **Slovaquie — `sk`, DMR 5.0** | MNT LiDAR **1 m**, couverture nationale annoncée | Source, classement du sol et contrôles documentés ; acquisition généralement sans feuilles | **Premier candidat à qualifier**. Préférer le MNT officiel natif quand l'accès le permet. [GKÚ](https://www.gku.sk/geoportal/zbgis/lls/1-cyklus/) |
| **Roumanie — `ro`, LAKI II** | **1 m vérifié sur une dalle archivée**, malgré les **0,5 m annoncés** ; emprise archivée ≈ **28 000 km²** dans l'ouest et le centre-ouest | Véritable LiDAR ; densités différentes selon les zones | **Candidat régional**, avec qualification par zone. [CNC](https://cartografie.ro/index.php/ro/domenii/csiis/item/247-informatii-geografice-pentru-mediu-schimbari-climatice-si-integrare-ue-laki-ii-laki-ii-land-administration-knowledge-improvement), [fiche Mapterhorn](https://github.com/mapterhorn/mapterhorn/blob/main/source-catalog/ro/metadata.json) |
| **Chypre — `cy`, DTM 2019** | **1 m nominal** ; emprise archivée ≈ **5 970 km²**, essentiellement les zones contrôlées par la République | Campagne 2019 associant LiDAR et photos aériennes ; garanties du MNT moins complètes que celles de Slovaquie | **Candidat crédible, à documenter et comparer au natif**. [DLS / rapport national 2023, p. 5](https://icaci.org/files/documents/national_reports/2019-2023/Cyprus-2023.pdf#page=6) |
| **Islande — `is`, ÍslandsDEM 1.0** | **10 m** chez Mapterhorn, alors que le modèle original existe aussi à 2 m | Principalement stéréoscopie satellitaire ArcticDEM, avec autres données et LiDAR local | **Écarter pour le microrelief**. Intérêt pour un fond de relief. [Métadonnées officielles](https://gatt.lmi.is/geonetwork/srv/api/records/e6712430-a63c-4ae5-9158-c89d16da6361/formatters/xml) |
| **Israël — `isr10`** | **10 m annoncés**, origine ASTER à un pas d'environ **30 m** | Altimétrie satellitaire ; absence de source LiDAR déclarée | **Écarter du catalogue LiDAR archéologique**. La grille à 10 m ne prouve pas un détail à 10 m. [Provenance déclarée](https://github.com/mapterhorn/mapterhorn/blob/main/source-catalog/isr10/metadata.json), [NASA](https://asterweb.jpl.nasa.gov/GDEM.asp) |
| **Rwanda — `rw`** | DEM national **10 m** | Origine NLA/WASAC ; mode de levé et précision non établis par la documentation consultée | **Écarter pour le microrelief**. [WASAC](https://github.com/WASAC/rwanda-dem) |
| **Taïwan — `aatw`** | DTM **20 m**, île principale et certaines îles périphériques | Produit officiel explicitement destiné à l'affichage du relief et à une analyse sommaire | **Écarter pour la prospection fine**. [Portail gouvernemental](https://data.gov.tw/en/datasets/169807) |

Pour la **Slovaquie**, le DMR 5.0 provient de la classe sol d'un nuage LiDAR
aéroporté acquis durant le cycle 2017–2023. Le cahier des charges demande au
moins **5 points/m² de scan**, une précision verticale du nuage ≤ **0,15 m**,
et du MNT ≤ **0,20 m en hauteur ellipsoïdale / 0,25 m en Bpv**. Ce sont des
critères contractuels ; les résultats diffèrent selon les secteurs. Les
contrôles absolus utilisent des surfaces ouvertes et stabilisées : ces chiffres
ne garantissent pas la même précision sous forêt. Le MNT est intéressant pour
fossés, talus, plateformes et tumulus, avec les limites d'une maille de 1 m.
Le classement élimine certaines constructions, ce qui peut effacer des murs
encore debout. [Spécification GKÚ](https://www.gku.sk/geoportal/zbgis/lls/1-cyklus/)

Pour la **Roumanie**, le CNC distingue **8 points/m²** dans la zone occidentale
à risque d'inondation, **2 points/m²** dans les autres grandes zones, et
**16 points/m²** dans les chefs-lieux. Il indique une distribution gratuite
sur environ 30 000 km² correspondant à Arad, Bihor, Hunedoara et Alba ; cela
ne signifie pas que tout le projet de 50 000 km² figure chez Mapterhorn.
[Bilan technique CNC, actualisé en 2025](https://cartografie.ro/index.php/ro/domenii/csiis/item/247-informatii-geografice-pentru-mediu-schimbari-climatice-si-integrare-ue-laki-ii-laki-ii-land-administration-knowledge-improvement)

La notice ANCPI de la zone Arad/Bihor décrit un MNT à **1 × 1 m**, issu de
LiDAR de 2017–2018, avec **0,30 m de précision altimétrique** et **0,20 m
planimétrique**. Le mode statistique n'y est pas précisé et ces chiffres ne
s'étendent pas automatiquement à toute l'emprise. [Notice officielle ANCPI](https://geoportal.ancpi.ro/portal/sharing/rest/content/items/4c820fcf2111417cb062acdcf7f6fef1/data)

La dalle `files/T28193.tif`, lue dans le début de l'archive Mapterhorn `ro.tar`,
possède réellement un pas de **1 m en EPSG:3844**. L'annonce « LAKI II MNT
0.5m » n'est donc pas corroborée par ce sondage. Cela ne démontre pas la
résolution de chaque fichier ; cela suffit à refuser la qualification générale
« LiDAR 0,5 m » sur la seule étiquette du catalogue. La faible densité de scan
de certaines zones rend aussi la qualité sous végétation plus incertaine.
Mon avis est favorable à une étude régionale, avec sélection des secteurs
et comparaison des mêmes reliefs au natif officiel.

Pour **Chypre**, le rapport national DLS confirme un DTM à 1 m sur les zones
contrôlées par la République et un DSM urbain à 0,5 m associé au levé LiDAR de
2019. Le catalogue Mapterhorn télécharge les rasters officiels du répertoire
`2019_DTM`. Ces éléments soutiennent le rattachement à cette campagne, mais
ne remplacent pas une fiche de qualité de chaque dalle.
[Rapport national DLS](https://icaci.org/files/documents/national_reports/2019-2023/Cyprus-2023.pdf#page=6),
[liste des fichiers Mapterhorn](https://github.com/mapterhorn/mapterhorn/blob/main/source-catalog/cy/file_list.txt)

Une contribution du DLS au rapport EuroSDR documente **10 points/m²** et
**20 cm de précision en hauteur** pour le nuage LiDAR des **550 km² urbains**.
Ces valeurs ne sont pas une garantie nationale de précision du MNT rural ni
une mesure de précision après transformation par Mapterhorn.
[DLS / EuroSDR 2021, p. 8](https://www.eurosdr.net/sites/default/files/uploaded_files/eurosdr_annual_report_2021.pdf#page=9)

La dalle chypriote `ETRS89_1500_3700.tif` archivée par Mapterhorn est en
EPSG:4258, avec un pas d'environ 0,000009988° dans les deux directions. Au
centre de cette dalle, cela représente **0,91 m est-ouest × 1,11 m nord-sud**.
« 1 m » est donc ici une résolution nominale, pas une maille carrée métrique
exacte. Le candidat mérite un contrôle de classification et de microrelief
sur des parcelles boisées et ouvertes avant toute validation.

Pour **l'Islande**, les métadonnées officielles de la version 1.0 décrivent
une mosaïque d'ArcticDEM, recalée et complétée notamment par GLO-30 et des
levés LiDAR de glaciers. Elles annoncent une précision meilleure que **2 m
en XY et 0,5 m en Z**, évaluée sur des points de référence. Ce modèle composite
ne constitue pas un MNT LiDAR du sol homogène. La version à 10 m choisie par
Mapterhorn est de toute façon trop grossière pour le besoin du projet.
[Métadonnées officielles de la version 1.0](https://gatt.lmi.is/geonetwork/srv/api/records/e6712430-a63c-4ae5-9158-c89d16da6361/formatters/xml),
[choix du fichier Mapterhorn](https://github.com/mapterhorn/mapterhorn/blob/main/source-catalog/is/file_list.txt)

Pour **Israël**, Mapterhorn attribue la source à ASTER, retraité par 4cast avec
VTbuilder. La NASA décrit ASTER GDEM comme issu de couples stéréoscopiques,
avec un pas de 30 m. Un rééchantillonnage à 10 m est l'explication cohérente
avec ces deux descriptions ; c'est une déduction de provenance, et non une
mesure comparative des rasters. Aucun document consulté ne justifie une
origine LiDAR ou une finesse archéologique de 10 m.
[Fiche Mapterhorn](https://github.com/mapterhorn/mapterhorn/blob/main/source-catalog/isr10/metadata.json),
[description NASA d'ASTER](https://asterweb.jpl.nasa.gov/GDEM.asp)

Pour le **Rwanda**, le dépôt WASAC établit un DEM NLA à 10 m, mais ne décrit
pas le capteur, les classes sol, la densité au sol ni une précision verticale
chiffrée. L'origine LiDAR reste non démontrée. Pour **Taïwan**, le producteur
précise que les dates de production varient selon les feuilles ; l'édition
2024 ne signifie pas un levé uniforme de 2024. Même une excellente précision
verticale ne compenserait pas leurs mailles de 10 et 20 m pour détecter de
petits fossés ou des talus.
[WASAC](https://github.com/WASAC/rwanda-dem),
[description du DTM taïwanais](https://data.gov.tw/en/datasets/169807)

Les licences déclarées par Mapterhorn sont **CC BY 4.0** pour Slovaquie,
Chypre, Islande et Rwanda ; **OGL-ROU-1.0** pour Roumanie ; **Open Government
Data License 1.0** pour Taïwan ; « ASTER GDEM Public Domain » pour Israël.
Il s'agit des mentions du catalogue, sans audit juridique complémentaire.
[Catalogue de sources Mapterhorn](https://github.com/mapterhorn/mapterhorn/tree/main/source-catalog)

**Vérifications réalisées.** L'inventaire utilise le même chargeur local de
providers que la carte de couverture. Pour chacun des sept jeux, un sondage
croise le polygone de source du catalogue MVT avec le point choisi, puis
télécharge et décode une tuile Terrarium de 512 × 512 pixels. Les sept sondages
confirment la présence de la source spécifique, au-delà du fond GLO-30.

| Source | Point sondé | Zoom téléchargé | Pixel de la tuile au sol à cette latitude |
| --- | --- | --- | --- |
| `sk` | Forêt au nord de Bratislava | 16 | 0,80 m |
| `ro` | Arad | 16 | 0,83 m |
| `cy` | Larnaca | 16 | 0,98 m |
| `is` | Reykjavík | 12 | 8,33 m |
| `isr10` | Jérusalem | 13 | 8,12 m |
| `rw` | Kigali | 13 | 9,55 m |
| `aatw` | Taipei | 12 | 17,31 m |

La taille de ces pixels dépend de la latitude et du zoom. Elle ne mesure ni
la résolution effective de la source ni sa précision. Le zoom 17 roumain
et le zoom 13 islandais ont renvoyé 404 aux points sondés ; les niveaux
ci-dessus répondent. Les emprises de Roumanie et Chypre ont été calculées
sur les polygones généralisés contenus dans les archives, sans garantie de
couverture pixel par pixel.

Les en-têtes GeoTIFF ont été lus dans des téléchargements limités aux
16 premiers Mio de `ro.tar` et aux 10 premiers Mio de `cy.tar`. Le serveur
ignorant Range lors de ces sondages, la lecture a été bornée puis la connexion
fermée. Les archives complètes de plusieurs dizaines de Go n'ont pas été
téléchargées. Les réponses, dates, empreintes SHA-256 et fichiers de source
sont conservés dans `cache/mapterhorn-countries/`. Les données officielles
roumaines n'étaient pas directement accessibles depuis cet environnement
(résolution DNS du géoportail en échec) ; leurs notices indexées et le stock
Mapterhorn ont pu être examinés.

Le résultat est reproductible avec :

```powershell
rtk proxy python -X utf8 tools/provider_candidates/audit_mapterhorn_countries.py --inspect-archives
```

Les métadonnées HTTP identifient la date de consultation ; les années d'accès
2025/2026 du catalogue ne sont pas les années de levé. Le fichier
[résultats de l'inventaire](mapterhorn-pays-manquants.results.json) conserve
les références et valeurs des sondages.

**Décision proposée :** qualifier d'abord la Slovaquie, puis des secteurs
roumains et chypriotes. Pour chacun, privilégier l'accès au MNT officiel
natif et comparer le microrelief conservé dans les tuiles Mapterhorn.
La [comparaison déjà faite avec IGN LiDAR HD](mapterhorn-ign-comparaison/README.fr.md)
a mis en évidence une atténuation de structures fines sur les sites français
testés ; son amplitude ne peut pas être extrapolée à ces trois pays.
Les quatre autres sources conviennent à un contexte topographique plus
large, pas à la qualification LiDAR fine demandée pour lidar2map.
