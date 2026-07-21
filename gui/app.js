
// ── État ─────────────────────────────────────────────────────────────────────
let fusionFiles = [];
let fusionSel = -1;
let polling = null;
let _initialized = false;
// Résolution native (m/px) du provider actif, mise à jour via get_init_data et au
// changement de provider. Sert au défaut LRM/RRIM = 15 px (cf. sigma_defaut_m
// côté pipeline), pour pré-remplir le champ σ à la bonne valeur selon le provider.
let _resolutionM = 0.5;
const sigmaDefautM = () => Math.round(15 * _resolutionM * 100) / 100;
// Formate une résolution (m/px) pour affichage : virgule décimale en FR.
const fmtRes = (r) => (_lang === 'fr' ? String(r).replace('.', ',') : String(r)) + ' m';

// ── i18n ───────────────────────────────────────────────────────────────────────
// Pattern web standard : dico inline par locale + attribut data-i18n sur les
// nœuds. Zéro dépendance, pas de gettext (l'enclume pour 2 langues mono-mainteneur).
// Le texte FR en dur dans le HTML reste le FALLBACK si une clé manque : pas de
// page cassée. Variantes d'attribut : data-i18n (textContent), data-i18n-placeholder,
// data-i18n-title. Détection : navigator.language (l'OS, via QtWebEngine) ;
// override manuel persisté côté Python (pywebview.api.set_lang), appliqué dans
// initAsync après get_init_data.
// On ne tague que les chaînes qui DIFFÈRENT entre fr et en. Les tokens
// identiques (cols ×, km, m, JPEG, GPS, SVF, MBTiles, multi, 315°…) ne sont
// pas dans le dico ni taggés : t() renvoie alors le fallback fr (= le texte
// en dur), donc rien ne change. data-i18n-title pour les infobulles.
const I18N = {
  fr: {
    "btn.run":"▶ Lancer", "btn.stop":"■ Arrêter", "btn.hist":"⏱ Historique", "btn.log":"📋 Logs",
    "btn.share":"📲 Téléphone", "tip.share":"Envoyer les cartes générées sur le téléphone via QR (même WiFi).", "share.title":"📲 Envoyer au téléphone", "share.hint":"Même WiFi. Scanne un fichier, télécharge, puis « Ouvrir avec » OsmAnd ou Locus.", "share.close":"Fermer",
    "btn.help":"❓ Aide", "tip.help":"Aide : modes et paramètres de la ligne de commande.", "help.title":"❓ Aide — ligne de commande", "help.empty":"Aide indisponible.",
    "btn.usage":"📊 Usage", "tip.usage":"Usage disque : tailles des dossiers cache / production / projets (lecture seule).", "usage.title":"📊 Usage disque", "usage.refresh":"↻ Rafraîchir", "usage.open":"ouvrir", "usage.absent":"(absent)", "usage.empty":"Rien à afficher.", "usage.hint":"Lecture seule. Le ménage est manuel : « ouvrir » ce que tu veux vider dans l'explorateur.",
    "tip.projlist":"Projets existants (remplit le champ Nom)",
    "proj.pick":"↻ projet existant…",
    // Projet
    "sec.projet":"Projet", "f.name":"Nom *", "f.outdir":"Dossier sortie",
    "f.cachedir":"Dossier cache", "ph.cachedir":"(auto)",
    "f.proddir":"Dossier production", "ph.proddir":"(auto)",
    "tip.pickdir":"Choisir le dossier (le sélecteur s'ouvre sur le dossier courant / auto)",
    "loading":"Chargement...", "apikey":"Clé API :",
    "tip.provider":"Source LiDAR, par pays. La liste est filtrée par le type de surface choisi au-dessus.",
    "sec.source":"Source des données", "f.provider":"Provider", "f.surface":"Surface",
    "f.service":"Service", "f.themes":"Thèmes", "f.couches":"Couches",
    "tip.listedispo":"Entrées disponibles. Sélectionnez puis + (ou double-clic) pour ajouter.",
    "tip.listechoisi":"Entrées retenues. Double-clic pour retirer.",
    "tip.listeadd":"Ajouter la sélection", "tip.listedel":"Retirer la sélection",
    "svc.osm":"Geofabrik — extrait PBF régional",
    "svc.wfs":"IGN Géoplateforme — WFS",
    "svc.wmts.fr":"IGN Géoplateforme — WMTS",
    "svc.wmts.us":"USGS National Map — tuiles XYZ",
    "f.surf.mnt":"MNT (raster)", "f.surf.laz":"LAZ (nuage)",
    "f.surf.nolaz":"aucune source pour ce pays",
    "z.pays":"Pays",
    "f.laz":"Mode LAZ — structures debout (nuage classé, expérimental)",
    "f.zoomcap":"z%d = résolution native (%s) — au-delà, agrandissement sans information",
    "f.dlcap":"↓ %d max en parallèle (gros nuages LAZ)",
    "f.lazh":"hauteur (m)", "f.lazc":"classes LAS",
    "f.lazg":"socle", "f.lazg.classes":"classes sol", "f.lazg.csf":"tissu CSF (~3 min/dalle)",
    "f.lazt":"seuil (m)", "f.lazr":"maille (m)", "f.lazrg":"terrain",
    "f.lazrg.1":"pentu (1)", "f.lazrg.2":"relief doux (2)", "f.lazrg.3":"plat (3)",
    "tip.laz":"Reconstruit le modèle depuis le nuage de points classé (LAZ ~205 Mo/km²) : peut réintroduire les retours compatibles avec des ruines/murs debout que le MNT efface (candidats, pas une classification : le maquis revient aussi — mouchetis vs lignes continues). Socle « classes sol » : 2/9/66 = terrain, les autres classes sont réinjectées dans les trous du sol, filtrées par la tranche de hauteur. Socle « tissu CSF » : un tissu simulé (Zhang 2016) sépare sol et sursol sans les classes ; fond plus propre, ~3 min/dalle, réglages propres seuil/maille/terrain (hauteur/classes ignorés). Zone petite conseillée.",
    // Zone
    "sec.zone":"Zone géographique",
    "z.mode":"Zone", "mode.fronly":"France uniquement",
    "mode.ville":"Ville", "mode.gps":"GPS", "mode.bbox":"BBox", "mode.dep":"Department", "mode.region":"Région",
    "z.ville":"Ville", "z.rayonkm":"Rayon km", "z.gps":"GPS lat,lon", "z.bbox":"BBox W,S,E,N",
    "z.deps":"Department(s)",
    // Type de traitement
    "sec.type":"Type de traitement de carte",
    "t.lidar":"LiDAR", "t.raster":"Raster", "t.vect":"Vectoriel",
    // t.vecteur / t.osm restent : ils nomment les deux TRAITEMENTS dans
    // l'historique et la file d'attente, même si l'onglet est unique.
    "t.vecteur":"IGN Vectoriel", "t.osm":"OSM Vectoriel",
    "vsrc.ign":"IGN Géoplateforme (WFS)", "vsrc.osm":"OSM / Geofabrik (PBF)",
    "t.fusion":"Fusion vectorielle", "t.decoupe":"Découpage raster",
    // Étapes communes
    "split0":"0 — Découpage à priori (grandes zones)",
    "grid":"Grille :", "rows":"lignes", "orradius":"ou rayon", "rows_orradius":"lignes  ou rayon",
    "clean":"Nettoyage intermédiaires",
    "minfree":"min disque", "tip.minfree":"Arrêt propre avant un chunk si disque libre < seuil (0 = désactivé)",
    "split.hint":"1×1 = pas de découpage — reprise automatique via manifeste.json",
    "dl":"1 — Télécharger",
    "ovr":"Écraser le fichier résultat", "ovr.short":"Écraser",
    "workers":"Workers :", "compress":"Compresser",
    // Un seul nom pour l'étape de production : les sorties sont hétérogènes
    // (tuiles raster mbtiles/rmap/sqlitedb, carte vecteur Mapsforge, GeoJSON).
    // « Calculer les tuiles » n'était exact que pour les sorties raster.
    "map2":"2 — Générer la carte", "map3":"3 — Générer la carte",
    "fmt.mapsforge":"Mapsforge (.map)", "fmt.natif":"(natif)",
    "tip.natif":"Écrit directement par le téléchargement WFS : au moins un des deux GeoJSON est toujours produit, et c'est l'Écraser du cadre « Télécharger » qui le régit.",
    "omb2":"2 — Calculer les ombrages archéologiques",
    "zoom":"Zoom :", "imgfmt":"Format de l'image :", "jpegq":"Qualité Jpeg :", "filefmt":"Format du fichier :",
    // SVF
    "tip.svf":"Sky-View Factor — ouverture de l'hémisphère céleste. Options à droite.",
    "tip.elev":"Angle solaire des hillshades directionnels. 25° = archéo (micro-relief) ; 45° = usage général.",
    // IGN Raster
    "couche":"Couche :",
    // OSM / Vecteur / Fusion
    "tip.max4":"Le WFS IGN limite les requêtes concurrentes : au-delà de 4, les couches commencent à échouer.",
    "geojson.raw":".geojson (non compressed)",
    "simplif":"Simplification vecteur",
    "simplif.hint1":"m  (vide = auto : 3 m local → 40 m région)", "simplif.hint2":"m  (vide = auto)",
    "sec.fusion":"Fichiers GeoJSON à fusionner",
    "add":"＋ Ajouter…", "remove":"－ Supprimer", "clear":"✕ Vider",
    "extsel":"Sélection étendue (Shift/Ctrl)", "fmt":"Format :",
    // Découpage raster
    "sec.src":"Fichier source", "sec.split":"Découpage",
    // Placeholders
    "ph.optopo":"clé OpenTopography", "ph.ignpro":"clé pro IGN",
    "ph.mbtilespath":"chemin vers le fichier .mbtiles",
    // Dynamiques (JS) — {x} = placeholders remplacés par tf()
    "copied":"✓ copié dans le presse-papier", "copyfail":"✗ copie échouée",
    "apiunavail":"API non disponible", "initerr":"Erreur init : ",
    "hist.empty":"Aucun traitement enregistré.",
    "hist.alreadyempty":"L'historique est déjà vide.",
    "hist.confirm":"Supprimer {n} entrée(s) de l'historique ?\n\nCette action est définitive — les commandes passées ne pourront plus être rappelées.",
    "hist.cleared":"✓ Historique vidé ({n} entrée(s) removede(s))",
    "hist.recalled":"Paramètres rappelés : {nom} ({date})",
    "del.error":"Erreur lors de la suppression : ", "del.unknown":"inconnue",
    "zoom.inverted":"⚠ Zooms d'historique inversés — corrigés au chargement",
    "update.dispo":"⬆ {tag} disponible : notes de version",
    "fusion.ignored":"Ignoré(s) : {files}\nSeuls .geojson et .geojson.gz sont acceptés.",
    "req.name":"Le nom du projet est obligatoire.",
    "req.source":"Le fichier source MBTiles est obligatoire.",
    "req.field":"Le champ « {f} » est obligatoire.",
    "btn.queue":"＋ File", "tip.queue":"Ajouter la configuration courante à la file d'attente",
    "run.queue":"▶ Lancer la file ({n})",
    "queue.count":"File ({n}) :", "queue.remove":"Retirer", "queue.clear":"× tout vider",
    "queue.running":"File {i}/{n} : {label}",
    "queue.done":"✓ File terminée : {ok} ok, {ko} échec(s)",
    "running":"En cours...", "done":"✓ Terminé", "stopped":"⚠ Arrêté",
    "err.code":"✗ Erreur (code {c})",
    "fail.detail":"Le traitement a échoué (code {c}).\n\n{msg}\n\n(détails complets dans le panneau de log ci-dessous)",
    "fail.generic":"Le traitement a échoué (code {c}).\n\nVoir le panneau de log ci-dessous pour les détails.",
    // HTML riche (innerHTML) + infobulles SVF
    "warn.scanpro":"⚠ Cette couche est réservée aux <strong>professionnels</strong> (CGU IGN).<br>Une clé API est requise — compte <a href='https://cartes.gouv.fr' target='_blank' style='color:#e07070'>cartes.gouv.fr</a> avec SIRET.<br>Les particuliers doivent utiliser <strong>planign</strong> ou <strong>ortho</strong> (pas de clé requise).",
    "dep.syntax":"Syntaxe : <code>83</code> &nbsp;·&nbsp; <code>83,06,13</code> &nbsp;·&nbsp; <code>1-10</code> &nbsp;·&nbsp; <code>1-3,75,83</code> &nbsp;·&nbsp; DOM : <code>2A</code> <code>971</code> &nbsp;—&nbsp; Multi-département : un fichier par département",
    "region.hint":"Region Geofabrik = bbox englobante de ses départements. &nbsp;—&nbsp; OSM : une seule carte régionale (PBF complet, sans re-découpe).",
    "tip.sun":"Angle solaire des hillshades directionnels (multi/315/045/135/225). Sans effet sur le SVF.",
    "tip.svftype":"Flux cos²γ : tassé près de 1, contraste à l'œil. RVT 1−sin γ (Kokalj/Hesse) : standard archéo / openness, sensibilité linéaire aux faibles angles.",
    "tip.svfconv":"Flux cos²γ : contraste à l'œil. RVT 1−sin γ : standard archéo / openness.",
    "tip.svfdist":"Rayon d'horizon du SVF en mètres. 20 = micro-relief (fossés, murs) ; 100 = enceintes/voiries. Plus grand = plus lent.",
    "tip.svfgamma":"Gamma après stretch percentile. <1 éclaircit (√), 1 = linéaire, >1 assombrit. ~2.0 optimal pour flux, ~1.0 pour RVT.",
    "tip.svfsweep":"Kernel sweep-horizon (running max sur deque) : ×2-3 à 20 m, ×15+ à 100 m. Léger aliasing NN imperceptible pour structures > 1-2 px.",
    // Libellés dynamiques d'ombrage (OMB_DEFS), rendus via t()
    "omb.gamma":"γ (1 clair, 2 foncé)", "omb.gamma.mirror":"γ miroir (1 clair, 2 foncé)",
    "omb.sigma":"rayon (σ, m)",
    "tip.ombsigma":"Rayon du lissage gaussien (LRM/RRIM). Défaut = 15 px de la résolution native (≈ 7,5 m à 0,5 m/px). Petit = détails fins (fossés), grand = structures larges (terrasses). Vider = auto.",
    // Infobulles de grille
    "tip.deps":"Un ou plusieurs départements\nExemples : 83 | 83,06,13 | 1-10 | 1-3,75,83 | 2A | 971",
    "tip.colsew":"Colonnes Est-Ouest", "tip.rowsns":"Lignes Nord-Sud",
    "tip.colsew2":"Colonnes (Est-Ouest)", "tip.rowsns2":"Lignes (Nord-Sud)",
    "tip.radiuschunk1":"Rayon km par morceau (alternative à la grille)", "tip.radiuschunk2":"Rayon km par morceau",
    "tip.epsilon":"Epsilon Douglas-Peucker en mètres. Vide = auto depuis surface.",
    // Panneaux historique / log
    "hist.title":"Historique des traitements", "clear":"🗑 Vider", "log.copy":"⎘ Copier",
    "tip.logresize":"Redimensionner verticalement", "tip.logcopy":"Copier le log dans le presse-papier",
    "tip.logclear":"Effacer le contenu du log",
    "tip.loghide":"Masquer le panneau (ré-affichable via le bouton Logs en haut)",
    "status.running":"en cours",
  },
  en: {
    "btn.run":"▶ Run", "btn.stop":"■ Stop", "btn.hist":"⏱ History", "btn.log":"📋 Logs",
    "btn.share":"📲 Phone", "tip.share":"Send the generated maps to the phone via QR (same WiFi).", "share.title":"📲 Send to phone", "share.hint":"Same WiFi. Tap a file, download, then \"Open with\" OsmAnd or Locus.", "share.close":"Close",
    "btn.help":"❓ Help", "tip.help":"Help: command-line modes and parameters.", "help.title":"❓ Help — command line", "help.empty":"Help unavailable.",
    "btn.usage":"📊 Usage", "tip.usage":"Disk usage: cache / production / project folder sizes (read-only).", "usage.title":"📊 Disk usage", "usage.refresh":"↻ Refresh", "usage.open":"open", "usage.absent":"(missing)", "usage.empty":"Nothing to show.", "usage.hint":"Read-only. Cleanup is manual: 'open' whatever you want to empty in the file explorer.",
    "tip.projlist":"Existing projects (fills the Name field)",
    "proj.pick":"↻ existing project…",
    "sec.projet":"Project", "f.name":"Name *", "f.outdir":"Output folder",
    "f.cachedir":"Cache folder", "ph.cachedir":"(auto)",
    "f.proddir":"Production folder", "ph.proddir":"(auto)",
    "tip.pickdir":"Pick the folder (dialog opens at the current / auto folder)",
    "loading":"Loading...", "apikey":"API key:",
    "tip.provider":"LiDAR source, per country. The list is filtered by the surface type chosen above.",
    "sec.source":"Data source", "f.provider":"Provider", "f.surface":"Surface",
    "f.service":"Service", "f.themes":"Themes", "f.couches":"Layers",
    "tip.listedispo":"Available entries. Select then + (or double-click) to add.",
    "tip.listechoisi":"Selected entries. Double-click to remove.",
    "tip.listeadd":"Add the selection", "tip.listedel":"Remove the selection",
    "svc.osm":"Geofabrik — regional PBF extract",
    "svc.wfs":"IGN Géoplateforme — WFS",
    "svc.wmts.fr":"IGN Géoplateforme — WMTS",
    "svc.wmts.us":"USGS National Map — XYZ tiles",
    "f.surf.mnt":"DTM (raster)", "f.surf.laz":"LAZ (cloud)",
    "f.surf.nolaz":"no source for this country",
    "z.pays":"Country",
    "f.laz":"LAZ mode — standing structures (classified cloud, experimental)",
    "f.zoomcap":"z%d = native resolution (%s) — beyond that, upscaling with no extra information",
    "f.dlcap":"↓ %d max parallel (large LAZ clouds)",
    "f.lazh":"height (m)", "f.lazc":"LAS classes",
    "f.lazg":"ground base", "f.lazg.classes":"ground classes", "f.lazg.csf":"CSF cloth (~3 min/tile)",
    "f.lazt":"threshold (m)", "f.lazr":"cloth cell (m)", "f.lazrg":"terrain",
    "f.lazrg.1":"steep (1)", "f.lazrg.2":"gentle relief (2)", "f.lazrg.3":"flat (3)",
    "tip.laz":"Rebuilds the model from the classified point cloud (LAZ ~205 MB/km²): can re-introduce returns compatible with standing ruins/walls that the DTM erases (candidates, not a classifier — scrub comes back too: speckle vs continuous lines). \"ground classes\" base: 2/9/66 = terrain, other classes are re-injected into ground gaps, filtered by the height band. \"CSF cloth\" base: a simulated cloth (Zhang 2016) splits ground from off-ground without the classes; cleaner background, ~3 min/tile, its own threshold/cloth-cell/terrain settings (height/classes ignored). Keep the area small.",
    "sec.zone":"Geographic area",
    "z.mode":"Zone", "mode.fronly":"France only",
    "mode.ville":"City", "mode.gps":"GPS", "mode.bbox":"BBox", "mode.dep":"Department", "mode.region":"Region",
    "z.ville":"City", "z.rayonkm":"Radius km", "z.gps":"GPS lat,lon", "z.bbox":"BBox W,S,E,N",
    "z.deps":"Department(s)",
    "sec.type":"Map processing type",
    "t.lidar":"LiDAR", "t.raster":"Raster", "t.vect":"Vector",
    "t.vecteur":"IGN Vector", "t.osm":"OSM Vector",
    "vsrc.ign":"IGN Géoplateforme (WFS)", "vsrc.osm":"OSM / Geofabrik (PBF)",
    "t.fusion":"Vector merge", "t.decoupe":"Raster split",
    "split0":"0 — A priori split (large areas)",
    "grid":"Grid:", "rows":"rows", "orradius":"or radius", "rows_orradius":"rows  or radius",
    "clean":"Clean intermediates",
    "minfree":"min free disk", "tip.minfree":"Stop cleanly before a chunk if free disk < threshold (0 = off)",
    "split.hint":"1×1 = no split — automatic resume via manifeste.json",
    "dl":"1 — Download",
    "ovr":"Overwrite output file", "ovr.short":"Overwrite",
    "workers":"Workers:", "compress":"Compress",
    "map2":"2 — Generate the map", "map3":"3 — Generate the map",
    "fmt.mapsforge":"Mapsforge (.map)", "fmt.natif":"(native)",
    "tip.natif":"Written directly by the WFS download: at least one of the two GeoJSON files is always produced, and the \"Overwrite\" box of the Download frame governs it.",
    "omb2":"2 — Compute archaeological shadings",
    "zoom":"Zoom:", "imgfmt":"Image format:", "jpegq":"Jpeg quality:", "filefmt":"File format:",
    "tip.svf":"Sky-View Factor — openness of the celestial hemisphere. Options on the right.",
    "tip.elev":"Sun angle of the directional hillshades. 25° = archaeology (micro-relief); 45° = general use.",
    "couche":"Layer:",
    "tip.max4":"The IGN WFS limits concurrent requests: past 4, layers start failing.",
    "geojson.raw":".geojson (uncompressed)",
    "simplif":"Vector simplification",
    "simplif.hint1":"m  (empty = auto: 3 m local → 40 m region)", "simplif.hint2":"m  (empty = auto)",
    "sec.fusion":"GeoJSON files to merge",
    "add":"＋ Add…", "remove":"－ Remove", "clear":"✕ Clear",
    "extsel":"Extended selection (Shift/Ctrl)", "fmt":"Format:",
    "sec.src":"Source file", "sec.split":"Split",
    "ph.optopo":"OpenTopography key", "ph.ignpro":"IGN pro key",
    "ph.mbtilespath":"path to .mbtiles file",
    "copied":"✓ copied to clipboard", "copyfail":"✗ copy failed",
    "apiunavail":"API unavailable", "initerr":"Init error: ",
    "hist.empty":"No saved run.",
    "hist.alreadyempty":"History is already empty.",
    "hist.confirm":"Delete {n} history entry(ies)?\n\nThis is permanent — past commands can no longer be recalled.",
    "hist.cleared":"✓ History cleared ({n} entry(ies) removed)",
    "hist.recalled":"Parameters recalled: {nom} ({date})",
    "del.error":"Error while deleting: ", "del.unknown":"unknown",
    "zoom.inverted":"⚠ History zooms inverted — fixed on load",
    "update.dispo":"⬆ {tag} available: release notes",
    "fusion.ignored":"Ignored: {files}\nOnly .geojson and .geojson.gz are accepted.",
    "req.name":"Project name is required.",
    "req.source":"Source MBTiles file is required.",
    "req.field":"The « {f} » field is required.",
    "btn.queue":"＋ Queue", "tip.queue":"Add the current configuration to the queue",
    "run.queue":"▶ Run queue ({n})",
    "queue.count":"Queue ({n}):", "queue.remove":"Remove", "queue.clear":"× clear all",
    "queue.running":"Queue {i}/{n}: {label}",
    "queue.done":"✓ Queue done: {ok} ok, {ko} failed",
    "running":"Running...", "done":"✓ Done", "stopped":"⚠ Stopped",
    "err.code":"✗ Error (code {c})",
    "fail.detail":"Processing failed (code {c}).\n\n{msg}\n\n(full details in the log panel below)",
    "fail.generic":"Processing failed (code {c}).\n\nSee the log panel below for details.",
    "warn.scanpro":"⚠ This layer is restricted to <strong>professionals</strong> (IGN terms of use).<br>An API key is required — a <a href='https://cartes.gouv.fr' target='_blank' style='color:#e07070'>cartes.gouv.fr</a> account with a SIRET.<br>Individuals must use <strong>planign</strong> or <strong>ortho</strong> (no key required).",
    "dep.syntax":"Syntax: <code>83</code> &nbsp;·&nbsp; <code>83,06,13</code> &nbsp;·&nbsp; <code>1-10</code> &nbsp;·&nbsp; <code>1-3,75,83</code> &nbsp;·&nbsp; Overseas: <code>2A</code> <code>971</code> &nbsp;—&nbsp; Multi-department: one file per department",
    "region.hint":"Geofabrik region = bounding box of its departments. &nbsp;—&nbsp; OSM: a single regional map (full PBF, no re-split).",
    "tip.sun":"Sun angle of the directional hillshades (multi/315/045/135/225). No effect on SVF.",
    "tip.svftype":"Flux cos²γ: compressed near 1, contrast to the eye. RVT 1−sin γ (Kokalj/Hesse): archaeology standard / openness, linear sensitivity at low angles.",
    "tip.svfconv":"Flux cos²γ: contrast to the eye. RVT 1−sin γ: archaeology standard / openness.",
    "tip.svfdist":"SVF horizon radius in metres. 20 = micro-relief (ditches, walls); 100 = enclosures/roads. Larger = slower.",
    "tip.svfgamma":"Gamma after percentile stretch. <1 lightens (√), 1 = linear, >1 darkens. ~2.0 optimal for flux, ~1.0 for RVT.",
    "tip.svfsweep":"Sweep-horizon kernel (running max on deque): ×2-3 at 20 m, ×15+ at 100 m. Slight NN aliasing imperceptible for structures > 1-2 px.",
    "omb.gamma":"γ (1 light, 2 dark)", "omb.gamma.mirror":"γ mirror (1 light, 2 dark)",
    "omb.sigma":"radius (σ, m)",
    "tip.ombsigma":"Gaussian smoothing radius (LRM/RRIM). Default = 15 px of native resolution (≈ 7.5 m at 0.5 m/px). Small = fine detail (ditches), large = broad structures (terraces). Clear = auto.",
    "tip.deps":"One or more departments\nExamples: 83 | 83,06,13 | 1-10 | 1-3,75,83 | 2A | 971",
    "tip.colsew":"Columns East-West", "tip.rowsns":"Rows North-South",
    "tip.colsew2":"Columns (East-West)", "tip.rowsns2":"Rows (North-South)",
    "tip.radiuschunk1":"Radius km per chunk (alternative to the grid)", "tip.radiuschunk2":"Radius km per chunk",
    "tip.epsilon":"Douglas-Peucker epsilon in metres. Empty = auto from area.",
    "hist.title":"Processing history", "clear":"🗑 Clear", "log.copy":"⎘ Copy",
    "tip.logresize":"Resize vertically", "tip.logcopy":"Copy the log to the clipboard",
    "tip.logclear":"Clear the log content",
    "tip.loghide":"Hide the panel (re-show via the Logs button at the top)",
    "status.running":"running",
  },
};
let _lang = 'fr';
function t(k){ return (I18N[_lang] && I18N[_lang][k]) || I18N.fr[k] || k; }
function tf(k, v){ let s = t(k); for (const p in (v||{})) s = s.split('{'+p+'}').join(v[p]); return s; }
function detectLang(){ return (navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en'; }
function applyI18n(){
  document.documentElement.lang = _lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const v = t(el.dataset.i18n); if (v) el.textContent = v; });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const v = t(el.dataset.i18nPlaceholder); if (v) el.placeholder = v; });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const v = t(el.dataset.i18nTitle); if (v) el.title = v; });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const v = t(el.dataset.i18nHtml); if (v) el.innerHTML = v; });  // contenu statique de confiance
  document.querySelectorAll('[data-lang-btn]').forEach(b =>
    b.classList.toggle('active', b.dataset.langBtn === _lang));
  // Le badge de source DFM est posé dynamiquement (pas de data-i18n) → le
  // rafraîchir dans la nouvelle langue.
  if (typeof updateLazUI === 'function') updateLazUI();
}
function setLang(code, persist){
  _lang = (code === 'en') ? 'en' : 'fr';
  applyI18n();
  // applyI18n a réécrit le header couche depuis sa clé générique : ré-applique
  // la variante conscient-du-pays (IGN vs USGS Imagery) dans la nouvelle langue.
  // Elle suit la COUCHE choisie → c'est le listener de f-couche qui la pose.
  document.getElementById('f-couche')?.dispatchEvent(new Event('change'));
  // Les listes Pays et Provider portent des noms de pays traduits : les
  // reconstruire pour qu'elles suivent la langue (sélections préservées).
  if (_allProviders.length) {
    const _p = _paysActif();
    buildPays(_allProviders, document.getElementById('f-provider')?.value || 'fr-ign');
    const _zs = document.getElementById('f-pays');
    if (_zs) _zs.value = _p;
    onSurfaceChange();
    filtrerCouchesParPays();
    _majSourcesVecteur();
    _majModesDisponibles();   // les libellés Department/Région portent un suffixe
  }
  // Le placeholder du select projets est créé dynamiquement (hors applyI18n) :
  // re-peupler pour le traduire. No-op silencieux si l'API n'est pas prête.
  refreshProjets();
  // applyI18n a réécrit btn-run depuis sa clé « btn.run » : ré-applique le
  // libellé « Lancer la file (N) » si la file a des items en attente.
  renderFile();
  if (persist && window.pywebview && pywebview.api && pywebview.api.set_lang) {
    pywebview.api.set_lang(_lang).catch(e => console.error('set_lang error:', e));
  }
}

// ── Panneau de log ───────────────────────────────────────────────────────────
function ajouterLigneLog(text, tag) {
  const c = document.getElementById('log-content');
  if (!c) return;
  // Sémantique \r du terminal : la ligne de progression temporaire (barres
  // de download/tuilage) est remplacée par la première vraie ligne qui suit
  // (qui est sa version finale émise au \n).
  const prog = document.getElementById('log-progress-line');
  if (prog) prog.remove();
  const span = document.createElement('span');
  span.className = 'log-' + (tag || 'ok');
  span.textContent = text;
  c.appendChild(span);
  // Auto-scroll si l'utilisateur est déjà en bas (à 30 px près)
  const isAtBottom = (c.scrollHeight - c.scrollTop - c.clientHeight) < 30;
  if (isAtBottom) c.scrollTop = c.scrollHeight;
  // Limiter à ~5000 lignes pour éviter de saturer le DOM sur les longs runs
  while (c.children.length > 5000) c.removeChild(c.firstChild);
}

// Ligne de progression "en place" dans le panneau de log : équivalent du \r
// terminal. Sans elle, pendant un long download le panneau paraît figé (la
// barre ne vivait que dans le footer) : constaté sur un download Lyon de 3 min.
function majLigneProgression(label) {
  const c = document.getElementById('log-content');
  if (!c || !label) return;
  let el = document.getElementById('log-progress-line');
  const atBottom = (c.scrollHeight - c.scrollTop - c.clientHeight) < 30;
  if (!el) {
    el = document.createElement('span');
    el.id = 'log-progress-line';
    el.className = 'log-ok';
    c.appendChild(el);
  }
  el.textContent = label;
  if (atBottom) c.scrollTop = c.scrollHeight;
}

function viderLog() {
  const c = document.getElementById('log-content');
  if (c) c.innerHTML = '';
  document.getElementById('log-status').textContent = '';
  setLogProgress(0, '');
}

function copierLog() {
  // navigator.clipboard.writeText ne fonctionne pas dans WebView2/pywebview
  // hors contexte sécurisé (pas de HTTPS) : la méthode existe mais throw
  // silencieusement « NotAllowedError » ou ne fait rien selon les versions.
  // On essaie d'abord l'API moderne puis on retombe sur execCommand qui,
  // bien que déprécié, reste fonctionnel partout — y compris dans WebView2.
  const c = document.getElementById('log-content');
  if (!c) return;
  const text = c.textContent || '';

  function _flash() {
    const st = document.getElementById('log-status');
    if (!st) return;
    const orig = st.textContent;
    st.textContent = t('copied');
    setTimeout(() => { st.textContent = orig; }, 1500);
  }

  function _flashErr() {
    const st = document.getElementById('log-status');
    if (!st) return;
    const orig = st.textContent;
    st.textContent = t('copyfail');
    setTimeout(() => { st.textContent = orig; }, 2500);
  }

  function _fallback() {
    // Méthode universelle : textarea hors-écran + execCommand('copy').
    // Doit être attaché au DOM et sélectionné AVANT execCommand.
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    // Position fixed visible 1×1 px : execCommand exige que l'élément soit
    // dans le viewport (sinon il refuse silencieusement sur certains
    // chromiums embarqués). Opacité 0 plutôt que display:none.
    ta.style.position  = 'fixed';
    ta.style.top       = '0';
    ta.style.left      = '0';
    ta.style.width     = '1px';
    ta.style.height    = '1px';
    ta.style.padding   = '0';
    ta.style.border    = 'none';
    ta.style.outline   = 'none';
    ta.style.boxShadow = 'none';
    ta.style.background = 'transparent';
    ta.style.opacity   = '0';
    document.body.appendChild(ta);

    // Mémoriser la sélection courante pour la restaurer après
    const sel = document.getSelection();
    const ranges = [];
    if (sel) {
      for (let i = 0; i < sel.rangeCount; i++) ranges.push(sel.getRangeAt(i));
    }

    let ok = false;
    try {
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, text.length);
      ok = document.execCommand('copy');
    } catch (e) {
      console.error('execCommand copy:', e);
    }
    document.body.removeChild(ta);

    // Restaurer la sélection que l'utilisateur avait avant
    if (sel && ranges.length) {
      sel.removeAllRanges();
      ranges.forEach(r => sel.addRange(r));
    }
    return ok;
  }

  // Tentative API moderne, fallback synchrone si KO/absente
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(_flash).catch(e => {
      console.warn('clipboard API failed, fallback execCommand:', e);
      if (_fallback()) _flash(); else _flashErr();
    });
  } else {
    if (_fallback()) _flash(); else _flashErr();
  }
}

function toggleLogPanel() {
  const p = document.getElementById('panneau-log');
  const m = document.getElementById('main');
  const b = document.getElementById('btn-log');
  if (!p) return;
  // On active la transition CSS uniquement pour le toggle, pas pour le
  // drag de redimensionnement (sinon effet d'inertie pendant le mousemove).
  p.classList.add('animating');
  setTimeout(() => p.classList.remove('animating'), 200);
  p.classList.toggle('hidden');
  const visible = !p.classList.contains('hidden');
  if (m) m.classList.toggle('log-visible', visible);
  if (b) b.classList.toggle('active', visible);
}

// ── Drag de la poignée de redimensionnement du panneau de log ─────────────
// Pattern classique : mousedown sur la poignée → on enregistre Y de départ
// + hauteur de départ ; mousemove document → recalcule height ; mouseup
// document → cleanup. Le clamp respecte min-height (60) et 85vh.
// Persistance de la hauteur en localStorage : `log-h-px` — stable entre
// sessions sans nécessiter d'aller-retour Python.
(function _initLogResize(){
  const HANDLE_ID = 'log-resize-handle';
  const PANEL_ID  = 'panneau-log';
  const KEY       = 'lidar2map.log-height';
  const MIN_PX    = 60;
  const MAX_FRAC  = 0.85;   // 85vh

  function _maxPx(){ return Math.floor(window.innerHeight * MAX_FRAC); }
  function _clamp(h){ return Math.max(MIN_PX, Math.min(_maxPx(), h)); }

  function _appliquerHauteur(h){
    const p = document.getElementById(PANEL_ID);
    if (!p) return;
    p.style.height = _clamp(h) + 'px';
  }

  // Restaurer la hauteur au chargement (si persistée)
  try {
    const saved = parseInt(localStorage.getItem(KEY) || '', 10);
    if (!isNaN(saved) && saved >= MIN_PX) _appliquerHauteur(saved);
  } catch(e) { /* localStorage indispo (privacy mode) — non critique */ }

  function _attacher(){
    const handle = document.getElementById(HANDLE_ID);
    const panel  = document.getElementById(PANEL_ID);
    if (!handle || !panel) return;
    if (handle.dataset.bound === '1') return;   // idempotent
    handle.dataset.bound = '1';

    let dragStartY = 0;
    let dragStartH = 0;
    let dragging   = false;

    function onMouseMove(ev){
      if (!dragging) return;
      // dY positif quand on descend ; le panneau est ancré en bas, donc
      // descendre la souris RÉDUIT la hauteur. Inverser.
      const dy = ev.clientY - dragStartY;
      _appliquerHauteur(dragStartH - dy);
      ev.preventDefault();
    }
    function onMouseUp(){
      if (!dragging) return;
      dragging = false;
      handle.classList.remove('dragging');
      document.body.classList.remove('log-resizing');
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      // Persister la hauteur finale
      try {
        const h = parseInt(panel.style.height, 10);
        if (!isNaN(h)) localStorage.setItem(KEY, String(h));
      } catch(e) {}
    }
    handle.addEventListener('mousedown', function(ev){
      if (ev.button !== 0) return;   // bouton gauche uniquement
      dragging   = true;
      dragStartY = ev.clientY;
      dragStartH = panel.getBoundingClientRect().height;
      handle.classList.add('dragging');
      document.body.classList.add('log-resizing');
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup',   onMouseUp);
      ev.preventDefault();
    });

    // Re-clamp si la fenêtre rétrécit (max passe sous la hauteur courante)
    window.addEventListener('resize', function(){
      const h = parseInt(panel.style.height, 10);
      if (!isNaN(h)) _appliquerHauteur(h);
    });
  }

  // Le panneau-log est dans le DOM dès le départ (pas créé dynamiquement),
  // mais on attend DOMContentLoaded pour être robuste si l'ordre change.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _attacher);
  } else {
    _attacher();
  }
})();

function setLogProgress(pct, cls) {
  const bar = document.getElementById('log-progress-bar');
  if (!bar) return;
  bar.style.width = (pct >= 0 && pct <= 100 ? pct : 0) + '%';
  bar.className = '';
  if (cls) bar.classList.add(cls);
}

// ── Init ─────────────────────────────────────────────────────────────────────
// bindAll() est appelé immédiatement au DOMContentLoaded pour l'état initial
// (sections visibles/cachées selon checkboxes). L'init async (couches, config)
// est lancée séparément dès que pywebview.api est disponible.
document.addEventListener('DOMContentLoaded', () => {
  setLang(detectLang(), false);   // langue OS immédiate ; override sauvé appliqué dans initAsync
  bindAll();
  _acInstaller();
  // pywebview émet 'pywebviewready' sur window quand le bridge JS↔Python est
  // établi. C'est plus fiable que le polling seul (qui peut timeout en
  // debug=False sur certaines configs WebView2 lentes).
  if (window.pywebview && window.pywebview.api) {
    initAsync();
  } else {
    window.addEventListener('pywebviewready', initAsync, { once: true });
    waitForApi();   // fallback polling (au cas où l'event soit raté)
  }
});

function waitForApi(tries=0) {
  if (window.pywebview && window.pywebview.api &&
      typeof window.pywebview.api.get_init_data === 'function') {
    initAsync();
  } else if (tries < 600) {   // 600×50ms = 30s (au lieu de 10s)
    setTimeout(() => waitForApi(tries+1), 50);
  } else {
    document.getElementById('footer-status').textContent = t('apiunavail');
  }
}

async function initAsync() {
  if (_initialized) return;
  _initialized = true;
  try {
    const d = await pywebview.api.get_init_data();
    if (d.resolution_m) _resolutionM = d.resolution_m;   // défaut σ LRM/RRIM (provider actif)
    if (d.lang === 'fr' || d.lang === 'en') setLang(d.lang, false);  // override manuel sauvé
    if (d.ui_zoom) applyUiZoom(d.ui_zoom, false);   // zoom UI sauvé
    // buildCouches AVANT buildProviders : ce dernier appelle applyProviderCountry
    // qui filtre le dropdown des couches → il doit déjà être peuplé.
    buildCouches(d.couches);
    // buildPays AVANT buildProviders : le pays filtre la liste de providers.
    buildPays(d.providers || [], d.active_provider || 'fr-ign');
    buildProviders(d.providers || [], d.active_provider || 'fr-ign');
    filtrerCouchesParPays();
    _majSourcesVecteur();
    _majModesDisponibles();
    buildRegions(d.regions || []);
    buildWfsCouches(d.wfs);
    buildOsmTags(d.osm_tags);
    // Datalist des projets existants : peuplée dès l'init (le refresh au focus
    // seul arrive trop tard : la popup de suggestions déjà ouverte au moment du
    // focus ne se met pas à jour avec les options ajoutées après coup).
    refreshProjets();
    document.getElementById('f-apikey').value = d.apikey_def || '';
    // Charger l'historique via appel dédié
    pywebview.api.get_historique().then(hist => {
      if (hist && hist.length) {
        buildHistorique(hist);
        // Préremplissage : la plus récente entrée lancée depuis le GUI
        // (id suffixé '-gui') = snapshot complet du formulaire (getConfig).
        // Une entrée CLI n'a que les clés déductibles d'argv (~la moitié) :
        // l'utiliser laisserait le reste du formulaire aux défauts HTML.
        // Fallback hist[0] si l'historique est 100 % CLI (mieux que rien).
        const last = hist.find(e => e.params && String(e.id || '').endsWith('-gui'))
                     || hist[0];
        if (last && last.params) loadConfig(last.params);
      }
    }).catch(e => console.error('get_historique init error:', e));
    // Notification de mise à jour : 1 requête GitHub non bloquante,
    // silencieuse hors ligne. Bandeau discret et fermable en bas à droite.
    pywebview.api.check_update().then(r => {
      if (r && r.update) afficherBandeauUpdate(r.latest, r.url);
    }).catch(() => {});
  } catch(e) {
    console.error('initAsync error:', e);
    document.getElementById('footer-status').textContent = t('initerr') + e;
  }
}

// ── Bandeau de mise à jour ────────────────────────────────────────────────────
// Affiché quand Api.check_update() signale une release GitHub plus récente.
// Clic sur le texte : ouvre les notes de version dans le navigateur système
// (Api.open_url, restreinte au repo). Croix : ferme pour la session.
function afficherBandeauUpdate(tag, url) {
  if (document.getElementById('update-banner')) return;
  const b = document.createElement('div');
  b.id = 'update-banner';
  // Haut-centre : seule zone toujours visible et libre (le bas de la fenêtre
  // peut être rogné par la barre des tâches, le haut-droit porte FR/EN).
  b.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);' +
    'z-index:60;padding:6px 12px;border:1px solid var(--bd);border-radius:6px;' +
    'background:var(--bg2,#1c2733);font-size:12px;display:flex;gap:10px;' +
    'align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.35)';
  const txt = document.createElement('span');
  txt.textContent = tf('update.dispo', {tag: tag});
  txt.style.cursor = 'pointer';
  txt.onclick = () => pywebview.api.open_url(url);
  const x = document.createElement('span');
  x.textContent = '✕';
  x.style.cssText = 'color:var(--dim);cursor:pointer';
  x.onclick = () => b.remove();
  b.appendChild(txt); b.appendChild(x);
  document.body.appendChild(b);
}

// ── Sélecteur de région ───────────────────────────────────────────────────────
// Peuple le <select id="f-region"> avec les slugs Geofabrik (mode zone "Région").
function buildRegions(regions) {
  const sel = document.getElementById('f-region');
  if (!sel) return;
  sel.innerHTML = regions.map(r => `<option value="${r}">${r}</option>`).join('');
}

// ── Provider selector ────────────────────────────────────────────────────────
// Peuple le <select id="f-provider"> avec la liste des providers disponibles
// et règle la visibilité des onglets FR-only selon le pays du provider actif.
function buildProviders(providers, activeCode) {
  const sel = document.getElementById('f-provider');
  if (!sel) return;
  // Dossier providers/ absent (liste vide) : masquer label + select + apikey,
  // et rester silencieusement actif en fr-ign (provider de fallback côté Python).
  if (!providers.length) {
    const apiKeyGroup = document.getElementById('lidar-apikey-group');
    if (apiKeyGroup) apiKeyGroup.style.display = 'none';
    document.querySelectorAll('label').forEach(lbl => {
      if (lbl.textContent.trim() === 'Provider') lbl.style.display = 'none';
    });
    sel.style.display = 'none';
    sel.value = 'fr-ign';
    sel.dataset.country = 'fr';
    applyProviderCountry('fr');
    return;
  }
  _allProviders = providers.slice();     // liste complète (restaurée en surface MNT)
  sel.innerHTML = _providerOptionsHtml(providers);
  // Capacité "mode LAZ" par provider (jumeau *_laz côté Python). Les DÉFAUTS
  // des réglages viennent du module Python (source de vérité unique).
  _lazByCode = {};
  providers.forEach(p => { if (p.laz) _lazByCode[p.code] = p.laz; });
  sel.value = activeCode;
  const opt = sel.options[sel.selectedIndex];
  const country = (opt && opt.dataset.country) || 'fr';
  sel.dataset.country = country;
  if (opt && opt.dataset.res) _resolutionM = parseFloat(opt.dataset.res);   // défaut σ selon provider
  applyProviderCountry(country);
  applyProviderApiKey(opt);
  applyProviderLaz(sel.value);
  applyZoomCap();
  sel.addEventListener('change', () => {
    _applyProviderSelection();
    ombShowParams();   // rafraîchit le champ σ ouvert avec le nouveau défaut
  });
  // Le zoom natif dépend aussi de la latitude (156543·cos φ) : recalculer quand
  // la zone change. Les modes ville/dep/region n'ont pas de latitude sans
  // géocodage → _latZone retombe sur 45°, ce qui ne décale le résultat que
  // d'un niveau aux extrêmes.
  ['f-gps', 'f-bbox'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', applyZoomCap);
  });
  // Saisie manuelle du zoom max : c'est le NOUVEAU souhait de l'utilisateur,
  // qu'on re-mémorise pour pouvoir le restaurer si un provider plus fin
  // redonne de la marge.
  document.getElementById('f-zoom-max-l')?.addEventListener('change', function () {
    this.dataset.preCap = this.value;
  });
}

// Un <option> à partir d'un descriptor provider (factorisé : buildProviders +
// onSurfaceChange produisent la même chose). Résolution apposée seulement si
// absente du nom officiel (ex. "DEM 5m" ne la duplique pas).
function _providerOption(p) {
  const hasRes = /\d[\d.,]*\s?(m|cm)\b/i.test(p.name);
  const label = hasRes ? p.name : `${p.name} (${fmtRes(p.resolution_m ?? 0.5)})`;
  return `<option value="${p.code}" data-country="${p.country}" data-apikey-requise="${p.apikey_requise?1:0}" data-res="${p.resolution_m ?? 0.5}">${_acEsc(label)}</option>`;
}

// Liste de providers GROUPÉE PAR PAYS (<optgroup>). Avec 25+ pays et plusieurs
// sources pour certains (11 Länder allemands…), une liste à plat est illisible.
// L'ordre des pays vient de providers.common.COUNTRY_NAMES via country_rank
// (même ordre que les READMEs et la carte de couverture — une seule table), et
// les sources sont triées par nom à l'intérieur d'un pays.
function _providerOptionsHtml(list) {
  const parGroupe = new Map();
  list.forEach(p => {
    const cle = p.country || '';
    if (!parGroupe.has(cle)) parGroupe.set(cle, []);
    parGroupe.get(cle).push(p);
  });
  const nomPays = p => (_lang === 'en' ? p.country_en : p.country_fr)
                    || (p.country || '').toUpperCase();
  return Array.from(parGroupe.values())
    .sort((a, b) => (a[0].country_rank ?? 9999) - (b[0].country_rank ?? 9999))
    .map(grp => {
      const opts = grp.slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(_providerOption).join('');
      return `<optgroup label="${_acEsc(nomPays(grp[0]))}">${opts}</optgroup>`;
    }).join('');
}

// Effets de bord d'un changement de provider (pays, résolution σ, clé API,
// capacité LAZ, zoom natif). Partagé par le listener 'change' et
// onSurfaceChange.
function _applyProviderSelection() {
  const sel = document.getElementById('f-provider');
  const o = sel.options[sel.selectedIndex];
  const c = (o && o.dataset.country) || 'fr';
  sel.dataset.country = c;
  if (o && o.dataset.res) _resolutionM = parseFloat(o.dataset.res);
  applyProviderCountry(c);
  applyProviderApiKey(o);
  applyProviderLaz(sel.value);
  applyZoomCap();
}

// ── Pays de la zone ───────────────────────────────────────────────────────
// Peuplé depuis les pays réellement couverts par un provider (liste et ordre =
// providers.common.COUNTRY_NAMES, la même table que les READMEs et la carte).
// PAS d'entrée « tous pays » : lidar2map est un outil LiDAR, et l'OSM comme le
// raster y sont des COMPLÉMENTS du LiDAR. Un pays sans provider LiDAR n'a donc
// rien à faire ici — pour de l'OSM seul, MOBAC fait le travail. La liste des
// pays est ainsi exactement le périmètre de l'outil.
function buildPays(providers, activeCode) {
  const sel = document.getElementById('f-pays');
  if (!sel) return;
  const vus = new Map();
  providers.forEach(p => {
    if (p.country && !vus.has(p.country)) vus.set(p.country, p);
  });
  const tries = Array.from(vus.values())
    .sort((a, b) => (a.country_rank ?? 9999) - (b.country_rank ?? 9999));
  const nom = p => (_lang === 'en' ? p.country_en : p.country_fr)
                || (p.country || '').toUpperCase();
  sel.innerHTML = tries
    .map(p => `<option value="${p.country}">${_acEsc(nom(p))}</option>`).join('');
  // Défaut = pays du provider actif, pour ne rien changer à l'ouverture.
  const actif = providers.find(p => p.code === activeCode);
  sel.value = (actif && actif.country) || 'fr';
}

function _paysActif() {
  return document.getElementById('f-pays')?.value || '';
}

// Mode de saisie de la zone (liste « Zone »). Ex-radios name=mode : une liste
// tient sur la ligne des champs, cinq boutons non.
function _modeActif() {
  return document.getElementById('f-mode')?.value || 'ville';
}

// Un seul point d'entrée pour le changement de mode : bascule des champs,
// et recalcul du zoom natif (la latitude change avec GPS/BBox).
function onModeChange() {
  if (typeof window.applyMode === 'function') window.applyMode();
  applyZoomCap();
}

// Department et Région sont des découpages FRANÇAIS : _GEOFABRIK mappe des
// codes INSEE, et geocoder_departement/geocoder_region rendent du Lambert 93.
// Il n'existe aucun équivalent pour les 26 autres pays — la liste des régions
// ne pouvait donc pas « suivre le pays », il fallait retirer les modes.
// Même traitement que l'option LAZ : désactivés, motif dans leur libellé.
const _MODES_FR = { dep: 'mode.dep', region: 'mode.region' };
function _majModesDisponibles() {
  const sel = document.getElementById('f-mode');
  if (!sel) return;
  const fr = _paysActif() === 'fr';
  Object.entries(_MODES_FR).forEach(([val, cle]) => {
    const o = sel.querySelector(`option[value="${val}"]`);
    if (!o) return;
    o.disabled = !fr;
    o.textContent = t(cle) + (fr ? '' : ' — ' + t('mode.fronly'));
  });
  if (!fr && _MODES_FR[sel.value]) sel.value = 'ville';
  onModeChange();
}

// ── Onglet Vectoriel : source IGN (WFS) ou OSM (Geofabrik) ────────────────
// Le radio porte directement la valeur de cfg.type ('vecteur' | 'osm') : rien
// à traduire, getConfig la lit telle quelle et _build_cmd ne voit aucun
// changement.
function _vecteurSource() {
  return document.querySelector('input[name=vsrc]:checked')?.value || 'vecteur';
}

// Invariant du pipeline WFS : au moins un GeoJSON sort toujours (_build_cmd
// retombe sur "gz" si rien n'est coché). Plutôt que d'afficher une case cochée
// grisée — qui prétendrait à tort qu'un format PRÉCIS est imposé, alors que le
// choix compressé/non compressé est libre — on tient l'invariant : décocher le
// dernier des deux recoche l'autre. L'UI applique la même règle que le backend.
function _garantirGeojson(source) {
  const gz  = document.getElementById('f-fusion-gz');
  const raw = document.getElementById('f-fusion-gz-raw');
  if (!gz || !raw || gz.checked || raw.checked) return;
  (source === gz ? raw : gz).checked = true;
}

function onVecteurSource() {
  const osm = _vecteurSource() === 'osm';
  document.querySelectorAll('#sec-vecteur .v-ign')
    .forEach(el => el.classList.toggle('hidden', osm));
  document.querySelectorAll('#sec-vecteur .v-osm')
    .forEach(el => el.classList.toggle('hidden', !osm));
  // Pas de recoloration selon la source : IGN et OSM sont deux sources du même
  // onglet, la couleur reste celle de l'onglet Vectoriel.
}

// Source IGN (WFS) = France uniquement → on MASQUE le radio IGN hors de France
// (le WFS IGN ne sert que la métropole). Il ne reste qu'OSM. Si IGN était
// sélectionné, on bascule sur OSM. Même schéma que _majModesDisponibles.
function _majSourcesVecteur() {
  const fr = _paysActif() === 'fr';
  const ign    = document.getElementById('v-ign');
  const ignLbl = document.querySelector('label[for="v-ign"]');
  if (ign)    ign.style.display    = fr ? '' : 'none';
  if (ignLbl) ignLbl.style.display = fr ? '' : 'none';
  if (!fr && ign && ign.checked) {
    const osm = document.getElementById('v-osm');
    if (osm) osm.checked = true;
  }
  onVecteurSource();
}

// Changer de pays recadre ce qui dépend RÉELLEMENT du pays : le géocodage des
// villes (via _acRequete), la liste des providers LiDAR, et les couches raster
// (IGN = FR, USGS = US). On ne masque aucun onglet : un pays sans couche raster
// affiche une liste vide et le dit, plutôt que de faire disparaître l'onglet
// sous les pieds de l'utilisateur.
function onPaysChange() {
  onSurfaceChange();          // refiltre les providers (pays × surface)
  filtrerCouchesParPays();    // + masque l'onglet Raster si pas de couche
  _majSourcesVecteur();       // masque la source IGN hors de France
  _majModesDisponibles();     // Department / Région : France uniquement
  const inp = document.getElementById('f-ville');
  if (inp) inp.value = '';    // une ville d'un autre pays n'a plus de sens
  _acFermer();
}

// Couches raster du pays courant. '' (Tous) = aucune restriction.
function filtrerCouchesParPays() {
  const sel = document.getElementById('f-couche');
  if (!sel) return;
  const pays = _paysActif();
  let premiere = null;
  Array.from(sel.options).forEach(o => {
    const ok = !pays || (o.dataset.pays || 'fr') === pays;
    o.hidden = !ok;
    o.disabled = !ok;
    if (ok && !premiere) premiere = o;
  });
  Array.from(sel.getElementsByTagName('optgroup')).forEach(g => {
    g.hidden = !Array.from(g.children).some(o => !o.hidden);
  });
  const cur = sel.selectedOptions[0];
  if (premiere && (!cur || cur.hidden)) {
    sel.value = premiere.value;
    sel.dispatchEvent(new Event('change'));
  }
  // Pas de couche raster pour ce pays (ni IGN, ni USGS) → on MASQUE l'onglet
  // Raster plutôt que d'afficher une liste vide. Si l'onglet était actif, on
  // bascule sur LiDAR (sinon on resterait sur un onglet invisible).
  const _hasRaster = premiere !== null;
  const _lbl = document.getElementById('lbl-raster');
  const _rad = document.getElementById('t-scan');
  if (_lbl) _lbl.style.display = _hasRaster ? '' : 'none';
  if (_rad) {
    _rad.style.display = _hasRaster ? '' : 'none';
    if (!_hasRaster && _rad.checked) {
      const _li = document.getElementById('t-lidar');
      if (_li) { _li.checked = true; _li.dispatchEvent(new Event('change')); }
    }
  }
}

// Surface active. Le contrôle est un radio MNT/LAZ, mais le CONTRAT de config
// reste le booléen `dfm` (→ --laz côté CLI) : les configs sauvegardées et la
// file d'attente sont inchangées. Source unique de vérité pour tout le fichier.
function lazActif() {
  return document.getElementById('f-surface')?.value === 'laz';
}

// Choisir la surface AVANT le provider : "LAZ" réduit le dropdown aux sources
// LAZ-capables (celles qui ont un jumeau *_laz), "MNT" restaure la liste
// complète. Le provider courant est conservé s'il figure dans la nouvelle liste.
// C'est l'ordre chronologique réel : type de surface → sources possibles →
// résolution → zoom natif.
let _allProviders = [];
function onSurfaceChange() {
  const sel = document.getElementById('f-provider');
  if (!sel) return;
  const pays = _paysActif();
  const duPays = p => !pays || p.country === pays;
  // Un pays peut avoir des providers sans qu'aucun soit LAZ-capable : la
  // combinaison pays × LAZ serait alors vide. On désactive l'option LAZ plutôt
  // que d'afficher une liste vide, on retombe sur MNT, et le motif s'affiche
  // DANS le libellé de l'option (plus de mention séparée sur la ligne).
  const optLaz = document.querySelector('#f-surface option[value="laz"]');
  const dispoLaz = _allProviders.some(p => p.laz && duPays(p));
  if (optLaz) {
    optLaz.disabled = !dispoLaz;
    optLaz.textContent = t('f.surf.laz') + (dispoLaz ? '' : ' — ' + t('f.surf.nolaz'));
    const ssel = document.getElementById('f-surface');
    if (!dispoLaz && ssel && ssel.value === 'laz') ssel.value = 'mnt';
  }
  const laz  = lazActif();
  const keep = sel.value;
  const list = _allProviders.filter(p => duPays(p) && (!laz || p.laz));
  sel.innerHTML = _providerOptionsHtml(list);
  sel.value = list.some(p => p.code === keep) ? keep
            : ((list[0] && list[0].code) || keep);
  _applyProviderSelection();
  ombShowParams();
  updateLazUI();
}

// Capacité LAZ du provider actif : préremplit les réglages LAZ avec les défauts
// du jumeau Python (hmin/hmax/classes/CSF). En surface MNT il n'y a rien à
// préremplir — la ligne de réglages est masquée par updateLazUI.
let _lazByCode = {};
function applyProviderLaz(code) {
  const cap = _lazByCode[code];
  if (!cap) { updateLazUI(); return; }
  const hmin = document.getElementById('f-laz-hmin');
  const hmax = document.getElementById('f-laz-hmax');
  const cls  = document.getElementById('f-laz-classes');
  const grd  = document.getElementById('f-laz-ground');
  const cthr = document.getElementById('f-laz-csf-threshold');
  const cres = document.getElementById('f-laz-csf-resolution');
  const crig = document.getElementById('f-laz-csf-rigidness');
  if (hmin) { hmin.value = cap.hmin; hmin.dataset.def = cap.hmin; }
  if (hmax) { hmax.value = cap.hmax; hmax.dataset.def = cap.hmax; }
  if (cls)  { cls.value  = cap.classes; cls.dataset.def = cap.classes; }
  if (grd)  { grd.value  = cap.ground || 'classes'; grd.dataset.def = cap.ground || 'classes'; }
  if (cthr) { cthr.value = cap.csf_threshold ?? 0.5;  cthr.dataset.def = cthr.value; }
  if (cres) { cres.value = cap.csf_resolution ?? 0.5; cres.dataset.def = cres.value; }
  if (crig) { crig.value = cap.csf_rigidness ?? 1;    crig.dataset.def = crig.value; }
  updateLazUI();
}

function updateLazUI() {
  const params = document.getElementById('laz-params');
  if (params) params.style.display = lazActif() ? 'flex' : 'none';
  // Socle CSF : le tissu ignore la tranche de hauteur et les classes → on
  // ÉCHANGE les groupes de réglages (les valeurs cachées restent posées,
  // ré-affichées si on rebascule).
  const grd = document.getElementById('f-laz-ground');
  const csf = grd && grd.value === 'csf';
  const pc = document.getElementById('laz-params-classes');
  const px = document.getElementById('laz-params-csf');
  if (pc) pc.style.display = csf ? 'none' : 'inline-flex';
  if (px) px.style.display = csf ? 'inline-flex' : 'none';
  const laz = lazActif();
  // Champ Workers : en mode LAZ le download est plafonné (gros nuages, sinon
  // throttle serveur). On BORNE le champ (max + valeur) à la valeur du provider
  // (source unique, pas de 3 en dur) et on la restaure à la sortie. Le tuilage/
  // ombrage d'une zone LAZ est négligeable (petites zones), donc borner le champ
  // ne coûte rien. Le cap backend (_telecharger_dalles_zone) reste en défense
  // pour les runs CLI. Une note dit le pourquoi.
  const code = document.getElementById('f-provider')?.value;
  const capN = laz && _lazByCode[code] ? _lazByCode[code].download_workers_max : 0;
  const wl = document.getElementById('f-workers-l');
  if (wl) {
    if (capN) {
      if (wl.dataset.preLaz === undefined) {      // entrée mode LAZ : mémoriser
        wl.dataset.preLaz = wl.value;
        wl.dataset.preLazMax = wl.max || '32';
      }
      wl.max = capN;
      if ((parseInt(wl.value) || 0) > capN) wl.value = capN;
    } else if (wl.dataset.preLaz !== undefined) { // sortie : restaurer
      wl.max = wl.dataset.preLazMax || '32';
      wl.value = wl.dataset.preLaz;
      delete wl.dataset.preLaz;
      delete wl.dataset.preLazMax;
    }
  }
  // Pas de mention visible : le plafond est déjà porté par le `max` du champ.
  // Le motif vit dans l'infobulle, comme pour le bridage du zoom.
  if (wl) wl.title = capN ? t('f.dlcap').replace('%d', capN) : '';
}

// ── Zoom natif du provider ────────────────────────────────────────────────
// Une tuile Web Mercator 256 px au zoom z couvre 156543,03·cos(φ)/2^z m/px.
// Le zoom NATIF est le premier z dont la tuile est au moins aussi fine que la
// source : au-delà, on ne fabrique que de l'agrandissement (×4 de tuiles par
// niveau pour zéro information), et OsmAnd comme Locus agrandissent déjà
// nativement la tuile la plus profonde disponible.
//   0,25 m → z19 · 0,5 m → z18 · 1 m → z17 · 2 m → z16 · 5 m → z15  (φ ≈ 45°)
// Symétrie avec l'onglet raster, qui plafonne DÉJÀ le zoom aux capacités
// réelles de la couche (_lire_zoom_limites_wmts / _XYZ_ZOOM_LIMITS côté
// Python). L'onglet LiDAR n'avait pas d'équivalent alors que la résolution du
// provider donne la réponse directement.
function zoomNatif(resM, latDeg) {
  // NB : pas de `latDeg || 45` — la latitude 0 (équateur) est une valeur
  // légitime et falsy, elle retomberait à tort sur le défaut.
  const lat = Math.abs(Number.isFinite(latDeg) ? latDeg : 45);
  const mpp = 156543.033928 * Math.cos(lat * Math.PI / 180);
  return Math.max(1, Math.min(22, Math.ceil(Math.log2(mpp / (resM || 0.5)))));
}

// Latitude représentative de la zone, quand elle est lisible sans géocodage
// (GPS ou BBox saisis). Sinon 45° : à 0,5 m ça donne z18, qui reste juste de
// l'équateur (z19) au cercle polaire (z17) à un niveau près.
function _latZone() {
  const mode = _modeActif();
  if (mode === 'gps') {
    const v = (document.getElementById('f-gps')?.value || '').split(',');
    const la = parseFloat(v[0]);
    if (!isNaN(la)) return la;
  } else if (mode === 'bbox') {
    const v = (document.getElementById('f-bbox')?.value || '').split(',').map(parseFloat);
    if (v.length === 4 && !isNaN(v[1]) && !isNaN(v[3])) return (v[1] + v[3]) / 2;
  }
  return 45;
}

// Borne le champ « Zoom max » au zoom natif du provider, sur le modèle du
// clamp Workers : on mémorise la saisie de l'utilisateur et on la restaure si
// un provider plus fin redonne de la marge. Le backend, lui, reste permissif
// (il avertit sans refuser) pour ne pas casser un run CLI délibéré.
function applyZoomCap() {
  const zl = document.getElementById('f-zoom-max-l');
  if (!zl) return;
  const zn = zoomNatif(_resolutionM, _latZone());
  if (zl.dataset.preCap === undefined) zl.dataset.preCap = zl.value;
  zl.max = zn;
  const voulu = parseInt(zl.dataset.preCap) || zn;
  zl.value = Math.min(voulu, zn);
  const zmin = document.getElementById('f-zoom-min-l');
  if (zmin && (parseInt(zmin.value) || 0) > zn) zmin.value = zn;
  // Pas de mention visible sur la ligne : le bridage est déjà porté par le
  // `max` du champ. L'explication vit dans l'infobulle, disponible sans
  // encombrer une ligne qui porte déjà zoom, format image, qualité et formats.
  zl.title = t('f.zoomcap').replace('%d', zn).replace('%s', fmtRes(_resolutionM));
}

function applyProviderApiKey(opt) {
  // Affiche le champ "Clé API" à côté de la dropdown provider si le provider
  // actif l'exige (data-apikey-requise="1"). Sinon caché.
  const group = document.getElementById('lidar-apikey-group');
  if (!group) return;
  const needs = opt && opt.dataset.apikeyRequise === '1';
  group.style.display = needs ? 'inline-flex' : 'none';
}

// Le provider LiDAR ne pilote PLUS l'onglet raster ni l'onglet IGN Vectoriel
// (découplé 2026-07-20). C'était un artefact GUI : le pipeline raster résout sa
// zone en WGS84 pur (_resoudre_zone_wgs84), il n'a jamais eu besoin du provider
// LiDAR. Choisir une source suisse ne doit donc pas faire disparaître les
// couches IGN. Le pays d'un run raster découle désormais de la COUCHE choisie,
// et l'onglet IGN Vectoriel est FR par nature : toujours visible.
//
// Reste ici ce qui dépend RÉELLEMENT du provider LiDAR : le pays utilisé pour
// géocoder les villes (Nominatim countrycodes=<pays>).
function applyProviderCountry(country) {
  const sel = document.getElementById('f-provider');
  if (sel) sel.dataset.country = country || 'fr';
}

let _historique = [];

function buildHistorique(hist) {
  _historique = hist || [];
  const list = document.getElementById('hist-list');
  if (!list) return;
  if (!_historique.length) {
    list.innerHTML = '<div style="color:var(--dim);font-size:12px">' + t('hist.empty') + '</div>';
    return;
  }
  const LABELS = {lidar:'LiDAR',scan:'Raster',osm:t('t.osm'),
                  vecteur:t('t.vecteur'),fusion:t('t.fusion'),decoupe:t('t.decoupe')};
  // Marqueur visuel du statut : ✓ ok (vert), ✗ ko (rouge), ⚠ en cours (orange,
  // process probablement crashé — l'entrée n'a pas été finalisée).
  const BADGES = {
    'ok':       ['✓', '#3b9d3b'],
    'ko':       ['✗', '#c44'],
    'en cours': ['⚠', '#e08000'],
  };
  list.innerHTML = _historique.map((e, i) => {
    // _acEsc sur les valeurs venant de l'utilisateur (nom de projet, ville) :
    // injectées en innerHTML, un nom contenant du HTML casserait le panneau.
    const zone = e.dep  ? `Dep ${_acEsc(e.dep)}` :
                 e.ville ? _acEsc(e.ville)        :
                 e.bbox  ? 'BBox'                 :
                 e.gps   ? 'GPS'                  : '';
    const st = e.statut || 'ok';  // entrées pré-v2 : pas de statut → 'ok' implicite
    const [sym, col] = BADGES[st] || ['', 'var(--dim)'];
    return `<div style="border:1px solid var(--bd);border-radius:4px;padding:8px;
                        margin-bottom:6px;cursor:pointer;font-size:12px"
                 onclick="rappelHistorique(${i})">
      <div style="display:flex;justify-content:space-between">
        <strong><span style="color:${col}">${sym}</span> ${LABELS[e.type]||e.type} — ${_acEsc(e.nom||'?')}</strong>
        <span style="color:var(--dim)">${e.date}</span>
      </div>
      <div style="color:var(--dim);margin-top:3px">${zone}${zone?' · ':''}${e.duree || (st === 'en cours' ? t('status.running') : st)}</div>
    </div>`;
  }).join('');
}

function toggleHistorique() {
  const p = document.getElementById('panneau-hist');
  if (p) p.classList.toggle('hidden');
}

async function viderHistorique() {
  const n = (_historique || []).length;
  if (n === 0) {
    alert(t('hist.alreadyempty'));
    return;
  }
  if (!confirm(tf('hist.confirm', {n}))) {
    return;
  }
  try {
    const r = await pywebview.api.clear_historique();
    if (r && r.ok) {
      _historique = [];
      buildHistorique([]);
      const fs = document.getElementById('footer-status');
      if (fs) fs.textContent = tf('hist.cleared', {n});
    } else {
      alert(t('del.error') + ((r && r.error) || t('del.unknown')));
    }
  } catch (e) {
    alert(t('del.error') + e);
  }
}

function rappelHistorique(i) {
  const e = _historique[i];
  if (!e || !e.params) return;
  loadConfig(e.params);
  toggleHistorique();
  document.getElementById('footer-status').textContent =
    tf('hist.recalled', {nom: e.nom||'', date: e.date});
}

// Propriétaire d'une couche raster, par pays : sert de libellé d'<optgroup> et
// de titre de section. C'est la seule notion de "provider raster" qui existe —
// l'inventaire réel est ~21 couches IGN + 1 couche USGS, donc une 2e dropdown
// de providers aurait un groupe à une entrée. L'optgroup dit la même chose sans
// widget supplémentaire.
const _RASTER_OWNER = { fr: 'IGN (France)', us: 'USGS (USA)' };

function buildCouches(couches) {
  const sel = document.getElementById('f-couche');
  // Groupées PAR PROPRIÉTAIRE, toutes visibles : la liste ne dépend plus du
  // provider LiDAR (cf. applyProviderCountry). Le pays du run raster découle
  // de la couche choisie.
  const parPays = new Map();
  couches.forEach(c => {
    const p = c.pays || 'fr';
    if (!parPays.has(p)) parPays.set(p, []);
    parPays.get(p).push(c);
  });
  parPays.forEach((liste, pays) => {
    const grp = document.createElement('optgroup');
    grp.label = _RASTER_OWNER[pays] || pays.toUpperCase();
    liste.forEach(c => {
      const o = document.createElement('option');
      o.value = c.code; o.textContent = c.label;
      o.dataset.zmin = c.zoom_min; o.dataset.zmax = c.zoom_max;
      o.dataset.restreinte = c.restreinte ? '1' : '0';
      o.dataset.pays = pays;
      grp.appendChild(o);
    });
    sel.appendChild(grp);
  });
  const updateWarning = () => {
    const o = sel.selectedOptions[0];
    const warn = document.getElementById('scan-restriction-warning');
    const apikeyGroup = document.getElementById('apikey-group');
    if (o) {
      document.getElementById('f-zoom-min-s').value = o.dataset.zmin;
      document.getElementById('f-zoom-max-s').value = o.dataset.zmax;
      const restricted = o.dataset.restreinte === '1';
      if (warn) warn.classList.toggle('hidden', !restricted);
      if (apikeyGroup) apikeyGroup.style.display = restricted ? 'flex' : 'none';
      // L'onglet s'appelle « Raster » tout court : il porte des couches de
      // plusieurs fournisseurs (IGN, USGS), le nommer d'après l'un d'eux était
      // faux. C'est la ligne Service du bloc Source qui dit lequel est actif.
      const pays = o.dataset.pays || 'fr';
      const svc = document.getElementById('hd-couche');
      if (svc) svc.textContent = t(pays === 'us' ? 'svc.wmts.us' : 'svc.wmts.fr');
    }
  };
  sel.addEventListener('change', updateWarning);
  updateWarning();
}

// ── Shuttle « disponibles ↔ choisis » ─────────────────────────────────────
// Pour les sélections SANS paramètre par entrée (couches WFS, thèmes OSM).
// Le shuttle des ombrages garde sa propre machinerie : lui porte des instances
// paramétrées (SVF 20 m + SVF 100 m coexistent), ce qui n'a pas d'équivalent
// ici — d'où l'absence de panneau de réglages.
// L'état vit dans _shuttleData et les deux <select> sont RE-RENDUS depuis lui :
// pas de déplacement d'<option> à la main, donc pas de désynchronisation
// possible entre ce qui est affiché et ce que getConfig lira.
const _SHUTTLES = {
  wfs: {dispo: 'wfs-dispo', liste: 'wfs-liste'},
  osm: {dispo: 'osm-dispo', liste: 'osm-liste'},
};
const _shuttleData = {};      // clé -> {items:[{value,label}], choisis:[value]}

function shuttleInit(cle, items, defauts) {
  _shuttleData[cle] = {
    items: items,
    choisis: (defauts || []).filter(v => items.some(i => i.value === v)),
  };
  shuttleRender(cle);
}

function shuttleRender(cle) {
  const d = _shuttleData[cle], ids = _SHUTTLES[cle];
  if (!d || !ids) return;
  const opt = it => `<option value="${_acEsc(it.value)}">${_acEsc(it.label)}</option>`;
  const pris = new Set(d.choisis);
  const dispo = document.getElementById(ids.dispo);
  const liste = document.getElementById(ids.liste);
  if (dispo) dispo.innerHTML = d.items.filter(i => !pris.has(i.value)).map(opt).join('');
  if (liste) liste.innerHTML = d.choisis
    .map(v => opt(d.items.find(i => i.value === v) || {value: v, label: v})).join('');
}

function listeAdd(cle) {
  const d = _shuttleData[cle];
  const v = document.getElementById(_SHUTTLES[cle]?.dispo)?.value;
  if (!d || !v || d.choisis.includes(v)) return;
  d.choisis.push(v);
  shuttleRender(cle);
}

function listeDel(cle) {
  const d = _shuttleData[cle];
  const v = document.getElementById(_SHUTTLES[cle]?.liste)?.value;
  if (!d || !v) return;
  d.choisis = d.choisis.filter(x => x !== v);
  shuttleRender(cle);
}

function shuttleValeurs(cle) { return (_shuttleData[cle]?.choisis || []).slice(); }

function shuttleSet(cle, valeurs) {
  const d = _shuttleData[cle];
  if (!d) return;
  const v = typeof valeurs === 'string' ? valeurs.split(' ') : (valeurs || []);
  d.choisis = v.filter(x => d.items.some(i => i.value === x));
  shuttleRender(cle);
}

function buildWfsCouches(wfs) {
  shuttleInit('wfs', wfs.map(w => ({value: w.alias, label: w.label})), ['cadastre']);
}

function buildOsmTags(tags) {
  shuttleInit('osm', tags.map(t => ({value: t.tag, label: t.label})),
              ['highway=*', 'waterway=*', 'boundary=administrative', 'natural=water']);
}

// ── Autocomplete ville (API Adresse data.gouv.fr / BAN, via proxy Python) ───
// On passe par pywebview.api.autocomplete_ville plutôt qu'un fetch() direct :
// la page est chargée via NavigateToString → origin "null" → WebView2 bloque
// le CORS de la BAN. Le proxy Python n'a pas ce problème.
// Échec silencieux : si l'API tombe, le champ reste un input texte normal.
const _AC_DEBOUNCE = 250;
const _AC_MINLEN  = 3;   // Geoplateforme exige >= 3 caractères (HTTP 400 sinon)
let _acTimer   = null;
let _acReqId   = 0;          // sérialise les réponses async (annule les vieilles)
let _acResults = [];
let _acIndex   = -1;
const _acCache = new Map();   // prefix.toLowerCase() -> array of items

function _acEsc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function _acFermer() {
  const dd = document.getElementById('f-ville-ac');
  if (dd) dd.classList.add('hidden');
  _acIndex = -1;
}

function _acRendre(items) {
  const dd = document.getElementById('f-ville-ac');
  if (!dd) return;
  if (!items || items.length === 0) { _acFermer(); return; }
  _acResults = items;
  _acIndex   = -1;
  dd.innerHTML = '';
  items.forEach((it, i) => {
    const div = document.createElement('div');
    div.className = 'ac-item';
    div.setAttribute('role', 'option');
    div.dataset.idx = i;
    div.innerHTML = _acEsc(it.label) +
      (it.context ? ' <span class="ac-meta">' + _acEsc(it.context) + '</span>' : '');
    // mousedown plutôt que click : se déclenche AVANT le blur de l'input,
    // évitant la fermeture prématurée du dropdown.
    div.addEventListener('mousedown', (e) => {
      e.preventDefault();
      _acChoisir(i);
    });
    dd.appendChild(div);
  });
  dd.classList.remove('hidden');
}

function _acChoisir(idx) {
  if (idx < 0 || idx >= _acResults.length) return;
  const it = _acResults[idx];
  const inp = document.getElementById('f-ville');
  if (inp) inp.value = it.label;
  _acFermer();
}

function _acSurleve(delta) {
  if (!_acResults.length) return;
  _acIndex = (_acIndex + delta + _acResults.length) % _acResults.length;
  const dd = document.getElementById('f-ville-ac');
  if (!dd) return;
  Array.from(dd.children).forEach((el, i) => {
    el.classList.toggle('active', i === _acIndex);
  });
  const cur = dd.children[_acIndex];
  if (cur) cur.scrollIntoView({block:'nearest'});
}

async function _acRequete(prefix) {
  // Pays DÉCLARÉ DANS LA ZONE : pilote BAN (FR) vs Nominatim (autre). Lu sur le
  // provider LiDAR auparavant, ce qui scopait le géocodage d'un run OSM ou
  // raster selon une source qu'ils n'utilisent pas.
  const country = _paysActif();
  // Clé de cache incluant le pays : sinon les résultats FR seraient renvoyés
  // pour la même saisie en NL après switch de provider.
  const key = country + '|' + prefix.toLowerCase();
  if (_acCache.has(key)) { _acRendre(_acCache.get(key)); return; }
  const myId = ++_acReqId;
  try {
    if (!(window.pywebview && window.pywebview.api &&
          typeof window.pywebview.api.autocomplete_ville === 'function')) {
      _acFermer();
      return;
    }
    const items = await pywebview.api.autocomplete_ville(prefix, country);
    if (myId !== _acReqId) return;
    const list = Array.isArray(items) ? items : [];
    _acCache.set(key, list);
    if (_acCache.size > 50) {
      _acCache.delete(_acCache.keys().next().value);
    }
    _acRendre(list);
  } catch(e) {
    if (myId === _acReqId) _acFermer();
  }
}

function _acDeclencher() {
  const inp = document.getElementById('f-ville');
  if (!inp) return;
  const v = inp.value.trim();
  if (v.length < _AC_MINLEN) { _acFermer(); return; }
  _acRequete(v);
}

function _acInstaller() {
  const inp = document.getElementById('f-ville');
  if (!inp) return;
  inp.addEventListener('input', () => {
    if (_acTimer) clearTimeout(_acTimer);
    _acTimer = setTimeout(_acDeclencher, _AC_DEBOUNCE);
  });
  inp.addEventListener('keydown', (e) => {
    const dd = document.getElementById('f-ville-ac');
    const visible = dd && !dd.classList.contains('hidden');
    if (e.key === 'ArrowDown') {
      if (!visible) _acDeclencher();
      else { _acSurleve(1); e.preventDefault(); }
    } else if (e.key === 'ArrowUp') {
      if (visible) { _acSurleve(-1); e.preventDefault(); }
    } else if (e.key === 'Enter') {
      if (visible && _acIndex >= 0) {
        _acChoisir(_acIndex);
        e.preventDefault();
      }
    } else if (e.key === 'Escape') {
      if (visible) { _acFermer(); e.preventDefault(); }
    } else if (e.key === 'Tab') {
      if (visible && _acIndex >= 0) _acChoisir(_acIndex);
      else _acFermer();
    }
  });
  // Délai sur blur pour laisser le mousedown sur un item passer
  inp.addEventListener('blur', () => setTimeout(_acFermer, 150));
  inp.addEventListener('focus', () => {
    const v = inp.value.trim();
    if (v.length >= _AC_MINLEN) _acDeclencher();
  });
}

function bindAll() {
  // Mode zone — appliquer l'état initial immédiatement
  // Même problème que pour 'type' : sr() coche le radio sans tirer 'change',
  // donc loadConfig() doit appeler applyMode() après sr('mode', ...).
  window.applyMode = function() {
    const cur = _modeActif();
    ['ville','gps','bbox','dep','region'].forEach(m => {
      const z = document.getElementById('z-'+m);
      if (z) z.classList.toggle('hidden', cur !== m);
    });
    // Aides de saisie hors ligne : seulement pour le mode concerné.
    [['dep','z-dep-hint'], ['region','z-region-hint']].forEach(([m, id]) => {
      const h = document.getElementById(id);
      if (h) h.classList.toggle('hidden', cur !== m);
    });
  };
  window.applyMode();
  // Type carte — appliquer l'état initial immédiatement
  // Fonction réutilisable : sync sections visibles + body class avec le
  // radio name=type actuellement coché. Appelée :
  //   - sur événement 'change' du radio (clic utilisateur)
  //   - une fois au démarrage (depuis bindAll)
  //   - depuis loadConfig() après avoir coché un radio par programme
  //     (parce que el.checked = true ne tire PAS l'événement 'change')
  window.applyType = function() {
    const cur = document.querySelector('input[name=type]:checked')?.value || 'lidar';
    // 'osm' n'a plus de section propre : il vit dans l'onglet Vectoriel, dont
    // le radio vaut 'vecteur'. Le sous-bloc actif est choisi par onVecteurSource.
    ['lidar','scan','vecteur','fusion','decoupe'].forEach(t => {
      const sec = document.getElementById('sec-'+t);
      if (sec) sec.classList.toggle('hidden', t !== cur);
    });
    document.body.className = 'type-' + cur;
    if (cur === 'vecteur') onVecteurSource();   // repose la classe body + blocs
    const secZone = document.querySelector('.sec-zone');
    if (secZone) secZone.classList.toggle('hidden', cur === 'decoupe');
  };
  document.querySelectorAll('input[name=type]').forEach(r => {
    r.addEventListener('change', window.applyType);
  });
  // Appliquer l'état initial
  window.applyType();
  // Toggle sections avec checkbox
  // Même problème que pour les radios : modifier el.checked par programme
  // (depuis loadConfig) ne tire PAS l'événement 'change'. Donc on expose
  // window.applyToggles() pour que loadConfig puisse forcer la synchro.
  const toggles = [
    ['f-priori',    'body-priori'],
    ['f-priori-s',  'body-priori-s'],
    ['f-carte-v',   'body-map-v'],
    ['f-tel',       'body-tel'],
    ['f-no-omb',    'body-omb'],
    ['f-mbtiles-l', 'body-mbt'],
    ['f-tel-s',     'body-tel-s'],
    ['f-tuiles-s',  'body-tuil-s'],
    ['f-tel-osm',   'body-tel-osm'],
    ['f-tuiles-osm','body-tuil-osm'],
    ['f-tel-v',     'body-tel-v'],
    // Vecteur : le corps de l'étape 2 est TOUJOURS visible (le pipeline émet
    // toujours au moins du .geojson.gz). Seul le détail propre au Mapsforge
    // (chaîne de conversion + simplification) suit la case .map.
    ['f-tuiles-v',  'map-v-detail'],
    ['f-fusion-map','row-simplif-fusion'],
  ];
  window.applyToggles = function() {
    toggles.forEach(([cbId, bodyId]) => {
      const cb = document.getElementById(cbId);
      const body = document.getElementById(bodyId);
      if (!cb || !body) return;
      body.classList.toggle('hidden', !cb.checked);
    });
  };
  toggles.forEach(([cbId, bodyId]) => {
    const cb = document.getElementById(cbId);
    if (!cb) return;
    cb.addEventListener('change', window.applyToggles);
  });
  window.applyToggles();
  // Format image LiDAR / IGN raster : masque "Qualité Jpeg" quand PNG est sélectionné.
  window.applyFmtL = function() {
    const cur = document.querySelector('input[name=fmt-l]:checked')?.value || 'jpeg';
    const wrap = document.getElementById('wrap-qualite-l');
    if (wrap) wrap.classList.toggle('hidden', cur !== 'jpeg');
  };
  document.querySelectorAll('input[name=fmt-l]').forEach(r => {
    r.addEventListener('change', window.applyFmtL);
  });
  window.applyFmtL();
  window.applyFmtS = function() {
    const cur = document.querySelector('input[name=fmt-s]:checked')?.value || 'jpeg';
    const wrap = document.getElementById('wrap-qualite-s');
    if (wrap) wrap.classList.toggle('hidden', cur !== 'jpeg');
  };
  document.querySelectorAll('input[name=fmt-s]').forEach(r => {
    r.addEventListener('change', window.applyFmtS);
  });
  window.applyFmtS();
}

// ── Projets existants (select déroulant à côté du champ Nom) ────────────────
// Combo : saisie libre dans l'input, liste complète via le select (récents
// d'abord) qui remplit le champ à la sélection. Peuplé à l'init et après
// chaque run réussi (pas au focus : les options ajoutées pendant l'ouverture
// de la popup n'y apparaîtraient pas).
function refreshProjets() {
  if (!(window.pywebview && pywebview.api && pywebview.api.get_projets)) return;
  const dossier = document.getElementById('f-dossier')?.value.trim() || null;
  pywebview.api.get_projets(dossier).then(list => {
    const sel = document.getElementById('f-nom-liste');
    if (!sel) return;
    sel.innerHTML = '';
    const ph = document.createElement('option');          // placeholder textuel
    ph.value = ''; ph.textContent = t('proj.pick');
    sel.appendChild(ph);
    (list || []).forEach(n => {
      const o = document.createElement('option');
      o.value = n; o.textContent = n;
      sel.appendChild(o);
    });
  }).catch(() => {});
}
function choisirProjet(sel) {
  if (!sel.value) return;
  const inp = document.getElementById('f-nom');
  if (inp) inp.value = sel.value;
  sel.selectedIndex = 0;   // re-sélectionnable, et la flèche reste neutre
}

// ── Partage vers le téléphone (QR + serveur LAN) ────────────────────────────
function partagerTelephone() {
  if (!(window.pywebview && pywebview.api && pywebview.api.start_share)) { alert(t('apiunavail')); return; }
  pywebview.api.start_share(getConfig()).then(r => {
    if (!r || !r.ok) { alert((r && r.error) || t('apiunavail')); return; }
    document.getElementById('share-url').textContent = r.url;
    renderQR(r.url, document.getElementById('share-qr'));
    document.getElementById('share-files').innerHTML =
      (r.fichiers || []).map(f => '• ' + f).join('<br>');
    document.getElementById('share-modal').style.display = 'flex';
  }).catch(e => alert(String(e)));
}
function fermerPartage() {
  document.getElementById('share-modal').style.display = 'none';
  if (window.pywebview && pywebview.api && pywebview.api.stop_share)
    pywebview.api.stop_share().catch(() => {});
}

// ── Aide ────────────────────────────────────────────────────────────────────
// Contenu = get_help() côté Python (docstring du module = source UNIQUE). On
// n'écrit aucun texte d'aide ici : le <pre> est rempli par la réponse.
function afficherAide() {
  const pre = document.getElementById('help-text');
  const modal = document.getElementById('help-modal');
  if (!modal || !pre) return;
  pre.textContent = t('loading');
  modal.style.display = 'flex';
  if (window.pywebview && pywebview.api && pywebview.api.get_help) {
    pywebview.api.get_help()
      .then(txt => { pre.textContent = txt || t('help.empty'); })
      .catch(() => { pre.textContent = t('help.empty'); });
  } else {
    pre.textContent = t('apiunavail');
  }
}
function fermerAide() {
  const modal = document.getElementById('help-modal');
  if (modal) modal.style.display = 'none';
}

// ── Usage disque (lecture seule) ────────────────────────────────────────────────
function _fmtOctets(n) {
  n = n || 0;
  if (n < 1024) return n + ' o';
  const u = ['Ko', 'Mo', 'Go', 'To'];
  let i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
  return n.toFixed(n < 10 ? 1 : 0) + ' ' + u[i];
}
function _usageOpen(path) {
  if (window.pywebview && pywebview.api && pywebview.api.open_folder)
    pywebview.api.open_folder(path);
}
function afficherUsage() {
  const modal = document.getElementById('usage-modal');
  const body = document.getElementById('usage-body');
  if (!modal || !body) return;
  body.textContent = t('loading');
  modal.style.display = 'flex';
  if (!(window.pywebview && pywebview.api && pywebview.api.get_usage)) {
    body.textContent = t('apiunavail');
    return;
  }
  // Racines custom du formulaire (cache/production) → refléter où sont vraiment
  // les fichiers, pas seulement les défauts.
  const cfg = { cache_dir: document.getElementById('f-cache-dir')?.value.trim(),
                production_dir: document.getElementById('f-production-dir')?.value.trim() };
  pywebview.api.get_usage(cfg)
    .then(d => renderUsage(d))
    .catch(() => { body.textContent = t('usage.empty'); });
}
function renderUsage(d) {
  const body = document.getElementById('usage-body');
  if (!body) return;
  body.innerHTML = '';
  const tiers = (d && d.tiers) || [];
  if (!tiers.length) { body.textContent = t('usage.empty'); return; }
  for (const tier of tiers) {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid var(--bd,#333)';
    const name = document.createElement('div');
    name.style.cssText = 'font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
    name.textContent = tier.label + (tier.exists ? '' : '  ' + t('usage.absent'));
    name.title = tier.path;
    const sz = document.createElement('div');
    sz.style.cssText = 'font-variant-numeric:tabular-nums;color:var(--ac);min-width:70px;text-align:right';
    sz.textContent = _fmtOctets(tier.bytes);
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm'; btn.textContent = t('usage.open');
    btn.disabled = !tier.exists;
    btn.onclick = () => _usageOpen(tier.path);
    row.append(name, sz, btn);
    body.appendChild(row);
    for (const c of (tier.children || [])) {
      const sub = document.createElement('div');
      sub.style.cssText = 'display:flex;align-items:center;gap:8px;padding:3px 0 3px 18px;color:var(--dim)';
      const cn = document.createElement('div');
      cn.style.cssText = 'flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
      cn.textContent = c.label; cn.title = c.path;
      const cs = document.createElement('div');
      cs.style.cssText = 'font-variant-numeric:tabular-nums;min-width:70px;text-align:right';
      cs.textContent = _fmtOctets(c.bytes);
      const cb = document.createElement('button');
      cb.className = 'btn btn-sm'; cb.textContent = t('usage.open');
      cb.onclick = () => _usageOpen(c.path);
      sub.append(cn, cs, cb);
      body.appendChild(sub);
    }
  }
}
function fermerUsage() {
  const modal = document.getElementById('usage-modal');
  if (modal) modal.style.display = 'none';
}

// ── Config ────────────────────────────────────────────────────────────────────
function getConfig() {
  const g = id => document.getElementById(id);
  const mode = _modeActif();
  let type = document.querySelector('input[name=type]:checked')?.value || 'lidar';
  // L'onglet Vectoriel porte deux traitements distincts côté CLI (--vector vs
  // --osm) : le type effectif vient du sélecteur de source, dont les valeurs
  // SONT déjà 'vecteur' et 'osm'.
  if (type === 'vecteur') type = _vecteurSource();
  const rayonId = mode === 'gps' ? 'f-rayon-gps' : 'f-rayon';

  const cfg = {
    type, mode,
    provider: g('f-provider')?.value || 'fr-ign',
    // Pays de la zone : cadre le géocodage et les listes. '' = aucun filtre.
    pays:     g('f-pays')?.value ?? '',
    // Dossier cache global (--cache-dir) : propriété d'installation, dans Projet.
    cache_dir: g('f-cache-dir')?.value.trim(),
    // Dossier production (--production-dir) : racine du .tif LAZ (produit).
    // Saisi dans Projet, à côté du cache ; n'a d'effet qu'en mode LAZ.
    production_dir: g('f-production-dir')?.value.trim(),
    lidar_apikey: g('f-lidar-apikey')?.value.trim(),
    // Surface LAZ (structures debout) + réglages ≠ défauts uniquement (les
    // défauts vivent côté Python, dataset.def posé par applyProviderLaz).
    // La clé reste `dfm` (→ --laz) : le contrôle est passé de case à radio
    // MNT/LAZ, pas le contrat de config.
    laz: lazActif(),
    laz_hmin:    (g('f-laz-hmin')?.value    && g('f-laz-hmin').value    !== g('f-laz-hmin').dataset.def)    ? g('f-laz-hmin').value    : '',
    laz_hmax:    (g('f-laz-hmax')?.value    && g('f-laz-hmax').value    !== g('f-laz-hmax').dataset.def)    ? g('f-laz-hmax').value    : '',
    laz_classes: (g('f-laz-classes')?.value && g('f-laz-classes').value !== g('f-laz-classes').dataset.def) ? g('f-laz-classes').value.trim() : '',
    laz_ground:  (g('f-laz-ground')?.value  && g('f-laz-ground').value  !== g('f-laz-ground').dataset.def)  ? g('f-laz-ground').value  : '',
    laz_csf_threshold:  (g('f-laz-csf-threshold')?.value  && g('f-laz-csf-threshold').value  !== g('f-laz-csf-threshold').dataset.def)  ? g('f-laz-csf-threshold').value  : '',
    laz_csf_resolution: (g('f-laz-csf-resolution')?.value && g('f-laz-csf-resolution').value !== g('f-laz-csf-resolution').dataset.def) ? g('f-laz-csf-resolution').value : '',
    laz_csf_rigidness:  (g('f-laz-csf-rigidness')?.value  && g('f-laz-csf-rigidness').value  !== g('f-laz-csf-rigidness').dataset.def)  ? g('f-laz-csf-rigidness').value  : '',
    nom:    g('f-nom')?.value.trim(),
    dossier:g('f-dossier')?.value.trim(),
    ville:  g('f-ville')?.value.trim(),
    gps:    g('f-gps')?.value.trim(),
    bbox:   g('f-bbox')?.value.trim(),
    dep:    g('f-dep')?.value.trim(),
    region: g('f-region')?.value.trim(),
    rayon:  parseFloat(g(rayonId)?.value ?? 10),
    // LiDAR
    tel:           g('f-tel')?.checked,
    comp:          g('f-comp')?.checked,
    ecraser_tel:   g('f-ecraser-tel')?.checked,
    workers_l:     parseInt(g('f-workers-l')?.value) || 8,
    no_omb:        g('f-no-omb')?.checked,
    // Shuttle list : les instances paramétrées remplacent les cases à cocher.
    // ombrages reste émis vide pour compat avec les vieux lecteurs de cfg.
    // sweep est PAR INSTANCE (svf:sweep=0|1) ; le global reste à sa valeur
    // par défaut pour les chemins legacy.
    ombrages:      [],
    shading_specs: ombToSpecs(),
    sweep_horizon: true,
    ecraser_omb:   g('f-ecraser-omb')?.checked,
    mbtiles_l:     g('f-mbtiles-l')?.checked && g('f-mbtiles')?.checked,
    rmap:          g('f-mbtiles-l')?.checked && g('f-rmap')?.checked,
    sqlitedb:      g('f-mbtiles-l')?.checked && g('f-sqlitedb')?.checked,
    zoom_min_l:    parseInt(g('f-zoom-min-l')?.value) || 8,
    zoom_max_l:    parseInt(g('f-zoom-max-l')?.value) || 18,
    fmt_l:         document.querySelector('input[name=fmt-l]:checked')?.value || 'jpeg',
    qualite_l:     parseInt(g('f-qualite-l')?.value) || 85,
    ecraser_mbt:   g('f-ecraser-mbt')?.checked,
    // Cases d'activation des cadres sans étape propre : le découpage à priori
    // (LiDAR / Raster) et la génération des dérivés vecteur. Elles gouvernent
    // l'ÉMISSION dans _build_cmd ; les valeurs saisies restent intactes pour
    // qu'un décochage/recochage ne les perde pas.
    decoupe:       g('f-priori')?.checked || false,
    decoupe_s:     g('f-priori-s')?.checked || false,
    carte_v:       g('f-carte-v')?.checked !== false,
    cols_decoupe:  parseInt(g('f-priori-cols')?.value)   || 0,
    rows_decoupe:  parseInt(g('f-priori-rows')?.value)   || 0,
    cols_decoupe_s:parseInt(g('f-priori-cols-s')?.value) || 0,
    rows_decoupe_s:parseInt(g('f-priori-rows-s')?.value) || 0,
    rayon_decoupe_l: parseFloat(g('f-rayon-priori-l')?.value) || 0,
    rayon_decoupe_s: parseFloat(g('f-rayon-priori-s')?.value) || 0,
    nettoyage:     g('f-nettoyage')?.checked || g('f-nettoyage-s')?.checked || false,
    min_free_gb:   parseFloat(g('f-min-free')?.value) || parseFloat(g('f-min-free-s')?.value) || 0,
    purger_inv:    false, purger_zone: false,
    // Scan
    couche:        g('f-couche')?.value,
    apikey:        g('f-apikey')?.value.trim(),
    tel_s:         g('f-tel-s')?.checked,
    workers_s:     parseInt(g('f-workers-s')?.value) || 8,
    ecraser_tel_s: g('f-ecraser-tel-s')?.checked,
    tuiles_s:      g('f-tuiles-s')?.checked,
    zoom_min_s:    parseInt(g('f-zoom-min-s')?.value) || 12,
    zoom_max_s:    parseInt(g('f-zoom-max-s')?.value) || 16,
    mbtiles_s:     g('f-mbtiles-s')?.checked,
    rmap_s:        g('f-rmap-s')?.checked,
    sqlitedb_s:    g('f-sqlitedb-s')?.checked,
    fmt_s:         document.querySelector('input[name=fmt-s]:checked')?.value || 'jpeg',
    qualite_s:     parseInt(g('f-qualite-s')?.value) || 85,
    ecraser_tuil_s:g('f-ecraser-tuil-s')?.checked,
    // OSM
    tel_osm:       g('f-tel-osm')?.checked,
    workers_osm:   parseInt(g('f-workers-osm')?.value) || 4,
    osm_tags_sel:  shuttleValeurs('osm'),
    ecraser_tel_osm: g('f-ecraser-tel-osm')?.checked,
    tuiles_osm:    g('f-tuiles-osm')?.checked,
    map:           g('f-map')?.checked,
    osm_geojson:     g('f-osm-geojson')?.checked,
    osm_geojson_raw: g('f-osm-geojson-raw')?.checked,
    osm_transparent: g('f-osm-transparent')?.checked,
    ecraser_tuil_osm: g('f-ecraser-tuil-osm')?.checked,
    // Vecteur
    tel_v:         g('f-tel-v')?.checked,
    wfs_couches_sel: shuttleValeurs('wfs'),
    workers_v:     parseInt(g('f-workers-v')?.value) || 4,
    ecraser_tel_v: g('f-ecraser-tel-v')?.checked,
    fusion_gz:      g('f-fusion-gz')?.checked,
    fusion_gz_raw:  g('f-fusion-gz-raw')?.checked,
    vec_transparent: g('f-vec-transparent')?.checked,
    tuiles_v:      g('f-tuiles-v')?.checked,
    ecraser_tuil_v:g('f-ecraser-tuil-v')?.checked,
    // Fusion
    fusion_fichiers: fusionFiles,
    fusion_gz2:    g('f-fusion-gz2')?.checked,
    fusion_gz2_raw:g('f-fusion-gz2-raw')?.checked,
    fusion_transparent: g('f-fusion-transparent')?.checked,
    fusion_map:    g('f-fusion-map')?.checked,
    simplif_v:     parseFloat(g('f-simplif-v')?.value) || null,
    simplif_fusion:parseFloat(g('f-simplif-fusion')?.value) || null,
    // Découpage raster (à posteriori)
    source_decoupe:  g('f-source-decoupe')?.value.trim(),
    cols_decoupe_d:  parseInt(g('f-cols-decoupe')?.value) || 1,
    rows_decoupe_d:  parseInt(g('f-rows-decoupe')?.value) || 1,
    rayon_decoupe_d: parseFloat(g('f-rayon-decoupe-d')?.value) || 0,
    mbtiles_d:       g('f-mbtiles-d')?.checked,
    rmap_d:          g('f-rmap-d')?.checked,
    sqlitedb_d:      g('f-sqlitedb-d')?.checked,
    ecraser_d:       g('f-ecraser-d')?.checked,
  };
  // Remap scan rmap/sqlitedb
  // Remap scan : unifier les clés de format pour _build_cmd
  // (removed — _build_cmd lit directement mbtiles_s/rmap_s/sqlitedb_s)
  return cfg;
}

function loadConfig(cfg) {
  const s  = (id, val) => { const el = document.getElementById(id);
    if (!el || val === undefined || val === null) return;
    if (el.type === 'checkbox') el.checked = !!val; else el.value = val; };
  const sr = (name, val) => { const r = document.querySelector(`input[name=${name}][value="${val}"]`);
    if (r) r.checked = true; };

  // Normaliser les zooms hérités d'un historique antérieur à _valider_zooms.
  // Si min > max sur n'importe quelle paire (LiDAR / Raster / Découpe), on
  // swap silencieusement et on prévient via le footer. Sans ça, un clic sur
  // une vieille entrée recharge des valeurs que le pipeline refusera.
  let _swapped = false;
  for (const [kmin, kmax] of [
    ['zoom_min_l', 'zoom_max_l'],
    ['zoom_min_s', 'zoom_max_s'],
    ['zoom_min_d', 'zoom_max_d'],
  ]) {
    const a = cfg[kmin], b = cfg[kmax];
    if (typeof a === 'number' && typeof b === 'number' && a > b) {
      cfg[kmin] = b; cfg[kmax] = a;
      _swapped = true;
    }
  }
  if (_swapped) {
    const fs = document.getElementById('footer-status');
    if (fs) fs.textContent = t('zoom.inverted');
  }

  // Zone
  // Le mode est passé du radio à une liste : on pose la valeur, applyMode()
  // est rappelée plus bas comme avant (poser .value ne tire pas 'change').
  if (cfg.mode) { const ms = document.getElementById('f-mode');
                  if (ms) ms.value = cfg.mode; }
  // cfg.type 'osm' n'a plus de radio d'onglet : il se restaure en cochant
  // l'onglet Vectoriel + la source OSM. Les configs et l'historique d'avant la
  // fusion se rechargent donc sans conversion.
  if (cfg.type) {
    if (cfg.type === 'osm' || cfg.type === 'vecteur') {
      sr('type', 'vecteur');
      sr('vsrc', cfg.type);
    } else {
      sr('type', cfg.type);
    }
  }
  // (window.applyMode/applyType seront rappelées en fin de loadConfig
  //  pour synchroniser les sections visibles avec les radios cochés)
  // NB : le provider + couche + zooms sont restaurés EN DERNIER (voir fin de
  //  fonction) car le changement de provider déclenche une cascade de 'change'
  //  (filtre des couches → updateWarning → reset des zooms) qui écraserait des
  //  valeurs restaurées trop tôt. Bug observé uniquement au démarrage, où
  //  l'ordre d'init diffère du rappel manuel via le panneau.

  // Projet
  s('f-nom',     cfg.nom);
  s('f-dossier', cfg.dossier);
  s('f-cache-dir', cfg.cache_dir);
  s('f-production-dir', cfg.production_dir);

  // Zone géo
  s('f-ville',   cfg.ville);
  s('f-gps',     cfg.gps);
  s('f-bbox',    cfg.bbox);
  s('f-dep',     cfg.dep);
  s('f-region',  cfg.region);
  s('f-rayon',     cfg.rayon);
  s('f-rayon-gps', cfg.rayon);


  // LiDAR
  s('f-tel',            cfg.no_tel !== undefined ? !cfg.no_tel : cfg.tel);
  // f-comp volontairement NON restauré : la compression est devenue le défaut
  // (case cochée dans le HTML). Toutes les entrées d'historique antérieures
  // portent comp:false (ancien défaut décoché, pas un choix) : les restaurer
  // transformerait l'ancien défaut en opt-out permanent pour tout le monde.
  s('f-ecraser-tel',    cfg.ecraser_tel);          // FIX: était cfg.ecraser_tel_l
  s('f-workers-l',      cfg.workers_l);
  s('f-no-omb',         cfg.no_omb);
  // f-elevation / f-svf-* (y compris sweep) : champs globaux remplacés par
  // les paramètres par instance (cfg.shading_specs, restaurés plus bas).
  s('f-ecraser-omb',    cfg.ecraser_omb);          // FIX: était cfg.ecraser_omb_l
  // FIX: f-mbtiles-l (section "calculer les tuiles") n'était jamais restauré
  s('f-mbtiles-l',      cfg.mbtiles_l || cfg.rmap || cfg.sqlitedb || false);
  s('f-mbtiles',        cfg.mbtiles_l !== undefined ? cfg.mbtiles_l : (cfg.mbtiles !== undefined ? cfg.mbtiles : false));
  s('f-rmap',           cfg.rmap);
  s('f-sqlitedb',       cfg.sqlitedb);
  s('f-zoom-min-l',     cfg.zoom_min_l);
  s('f-zoom-max-l',     cfg.zoom_max_l);
  if (cfg.fmt_l) sr('fmt-l', cfg.fmt_l);
  s('f-qualite-l',      cfg.qualite_l);
  s('f-ecraser-mbt',    cfg.ecraser_mbt);          // FIX: était cfg.ecraser_mbt_l
  s('f-priori',        cfg.decoupe);
  s('f-priori-s',      cfg.decoupe_s);
  s('f-carte-v',       cfg.carte_v !== undefined ? cfg.carte_v : true);
  s('f-priori-cols',   cfg.cols_decoupe);
  s('f-priori-rows',   cfg.rows_decoupe);
  s('f-priori-cols-s', cfg.cols_decoupe_s);
  s('f-priori-rows-s', cfg.rows_decoupe_s);
  s('f-rayon-priori-l', cfg.rayon_decoupe_l);
  s('f-rayon-priori-s', cfg.rayon_decoupe_s);
  // FIX: f-nettoyage et f-nettoyage-s n'étaient jamais restaurés
  s('f-nettoyage',   cfg.nettoyage);
  s('f-nettoyage-s', cfg.nettoyage);
  s('f-min-free',    cfg.min_free_gb);
  s('f-min-free-s',  cfg.min_free_gb);

  // Clé API LiDAR (us-3dep) — persistée séparément de l'IGN scan
  s('f-lidar-apikey',   cfg.lidar_apikey);

  // Scan IGN raster
  s('f-couche',         cfg.couche);
  s('f-apikey',         cfg.apikey);
  s('f-tel-s',          cfg.tel_s !== undefined ? cfg.tel_s : true);
  s('f-workers-s',      cfg.workers_s);
  s('f-ecraser-tel-s',  cfg.ecraser_tel_s);
  s('f-tuiles-s',       cfg.tuiles_s !== undefined ? cfg.tuiles_s : true);
  s('f-zoom-min-s',     cfg.zoom_min_s);
  s('f-zoom-max-s',     cfg.zoom_max_s);
  s('f-mbtiles-s',      cfg.mbtiles_s !== undefined ? cfg.mbtiles_s : true);
  s('f-rmap-s',         cfg.rmap_s);               // FIX: était cfg.rmap (clé LiDAR !)
  s('f-sqlitedb-s',     cfg.sqlitedb_s);            // FIX: était cfg.sqlitedb (clé LiDAR !)
  if (cfg.fmt_s) sr('fmt-s', cfg.fmt_s);
  s('f-qualite-s',      cfg.qualite_s);
  s('f-ecraser-tuil-s', cfg.ecraser_tuil_s);

  // OSM
  s('f-tel-osm',          cfg.tel_osm !== undefined ? cfg.tel_osm : true);
  s('f-workers-osm',      cfg.workers_osm);         // FIX: n'était jamais restauré
  s('f-ecraser-tel-osm',  cfg.ecraser_tel_osm);
  s('f-tuiles-osm',       cfg.tuiles_osm !== undefined ? cfg.tuiles_osm : true);
  s('f-map',              cfg.map !== undefined ? cfg.map : true);
  s('f-osm-geojson',      cfg.osm_geojson !== undefined ? cfg.osm_geojson : true);
  s('f-osm-geojson-raw',  cfg.osm_geojson_raw);
  s('f-osm-transparent',  cfg.osm_transparent);
  s('f-ecraser-tuil-osm', cfg.ecraser_tuil_osm);
  // FIX: était cfg.osm_tags — la clé sauvée par getConfig est osm_tags_sel.
  // shuttleSet accepte la liste ET la chaîne espacée (configs CLI héritées).
  if (cfg.osm_tags_sel) shuttleSet('osm', cfg.osm_tags_sel);

  // IGN Vectoriel
  s('f-tel-v',          cfg.tel_v !== undefined ? cfg.tel_v : true);
  s('f-workers-v',      cfg.workers_v);
  s('f-ecraser-tel-v',  cfg.ecraser_tel_v);
  s('f-fusion-gz',      cfg.fusion_gz !== undefined ? cfg.fusion_gz : true);
  s('f-fusion-gz-raw',  cfg.fusion_gz_raw);
  s('f-vec-transparent', cfg.vec_transparent);
  s('f-tuiles-v',       cfg.tuiles_v);
  s('f-ecraser-tuil-v', cfg.ecraser_tuil_v);
  // FIX: était cfg.wfs_couches — la clé sauvée par getConfig est wfs_couches_sel
  if (cfg.wfs_couches_sel) shuttleSet('wfs', cfg.wfs_couches_sel);

  // Fusion
  s('f-fusion-gz2',     cfg.fusion_gz2 !== undefined ? cfg.fusion_gz2 : true);
  s('f-fusion-gz2-raw', cfg.fusion_gz2_raw);        // FIX: n'était jamais restauré
  s('f-fusion-transparent', cfg.fusion_transparent);
  s('f-fusion-map',     cfg.fusion_map);             // FIX: n'était jamais restauré
  if (cfg.simplif_v     != null) { const el=g('f-simplif-v');     if(el) el.value=cfg.simplif_v; }
  if (cfg.simplif_fusion!= null) { const el=g('f-simplif-fusion');if(el) el.value=cfg.simplif_fusion; }
  if (cfg.fusion_fichiers) {
    fusionFiles = cfg.fusion_fichiers;
    renderFusionList();
  }

  // Découpage raster
  s('f-source-decoupe',  cfg.source_decoupe);
  s('f-cols-decoupe',  cfg.cols_decoupe_d);
  s('f-rows-decoupe',  cfg.rows_decoupe_d);
  s('f-rayon-decoupe-d', cfg.rayon_decoupe_d);
  s('f-mbtiles-d',       cfg.mbtiles_d !== undefined ? cfg.mbtiles_d : true);
  s('f-rmap-d',          cfg.rmap_d);
  s('f-sqlitedb-d',      cfg.sqlitedb_d);
  s('f-ecraser-d',       cfg.ecraser_d);

  // Ombrages : instances paramétrées (shuttle list).
  // Historique récent : cfg.shading_specs (strings 'type:k=v,...').
  // Historique ancien (cases à cocher) : cfg.ombrages + params globaux de
  // l'époque → converti en specs équivalentes.
  if (cfg.shading_specs && cfg.shading_specs.length) {
    ombFromSpecs(cfg.shading_specs);
  } else if (cfg.ombrages) {
    const arr = Array.isArray(cfg.ombrages)
      ? cfg.ombrages : Object.keys(cfg.ombrages).filter(k => cfg.ombrages[k]);
    const specs = arr.filter(t => OMB_DEFS[t]).map(t => {
      if (t === 'svf')
        return `svf:conv=${cfg.svf_conv || 'flux'},dist=${cfg.svf_dist || 20},gamma=${cfg.svf_gamma || 2},sweep=${cfg.sweep_horizon === false ? 0 : 1}`;
      if (t === 'opos' || t === 'oneg')
        return `${t}:dist=${cfg.svf_dist || 20},gamma=${cfg.svf_gamma || 2}`;
      if (['315', '045', '135', '225', 'multi'].includes(t))
        return `${t}:elevation=${cfg.elevation || 25}`;
      return t;   // slope, lrm, rrim → défauts
    });
    if (specs.length) ombFromSpecs(specs);
  }

  // Re-déclencher les toggles et l'état initial.
  // NB : les fonctions window.apply* sont définies par bindAll() et appelées
  // directement (au lieu d'un dispatchEvent('change') qui peut échouer
  // silencieusement selon le timing async d'attache des listeners pywebview).
  if (typeof window.applyMode    === 'function') window.applyMode();
  if (typeof window.applyType    === 'function') window.applyType();
  if (typeof window.applyToggles === 'function') window.applyToggles();
  if (typeof window.applyFmtL    === 'function') window.applyFmtL();
  if (typeof window.applyFmtS    === 'function') window.applyFmtS();

  // ── Restauration des champs sensibles aux cascades, EN DERNIER ────────────
  // Le changement de provider filtre les couches et déclenche updateWarning,
  // qui remet les zooms aux valeurs par défaut de la couche. On restaure donc
  // pays → provider → couche → zooms dans cet ordre, après tout le reste, pour
  // que les valeurs sauvées gagnent quel que soit l'ordre d'init (démarrage vs
  // panneau). Le pays vient EN PREMIER : il filtre la liste de providers, donc
  // le restaurer après effacerait le provider sauvé.
  if (cfg.pays !== undefined) {
    const zsel = document.getElementById('f-pays');
    if (zsel && zsel.querySelector(`option[value="${cfg.pays}"]`)) {
      zsel.value = cfg.pays;
      onSurfaceChange();
      filtrerCouchesParPays();
      _majSourcesVecteur();
      _majModesDisponibles();
    }
  }
  if (cfg.provider) {
    const psel = document.getElementById('f-provider');
    if (psel && psel.querySelector(`option[value="${cfg.provider}"]`)) {
      psel.value = cfg.provider;
      psel.dispatchEvent(new Event('change'));   // applyProviderCountry + filtre couches
    }
  }
  // Surface : restaurée APRÈS le provider (le change ci-dessus repose les
  // défauts via applyProviderLaz ; on ré-applique ensuite les valeurs sauvées).
  // Cocher un radio par programme ne tire PAS 'change' → onSurfaceChange() est
  // appelé à la main, ce qui refiltre la liste de providers en gardant le code
  // sauvé s'il est LAZ-capable.
  if (cfg.laz !== undefined) {
    const ssel = document.getElementById('f-surface');
    if (ssel) { ssel.value = cfg.laz ? 'laz' : 'mnt'; onSurfaceChange(); }
    if (cfg.laz_hmin)    s('f-laz-hmin',    cfg.laz_hmin);
    if (cfg.laz_hmax)    s('f-laz-hmax',    cfg.laz_hmax);
    if (cfg.laz_classes) s('f-laz-classes', cfg.laz_classes);
    if (cfg.laz_ground)  s('f-laz-ground',  cfg.laz_ground);
    if (cfg.laz_csf_threshold)  s('f-laz-csf-threshold',  cfg.laz_csf_threshold);
    if (cfg.laz_csf_resolution) s('f-laz-csf-resolution', cfg.laz_csf_resolution);
    if (cfg.laz_csf_rigidness)  s('f-laz-csf-rigidness',  cfg.laz_csf_rigidness);
    if (typeof updateLazUI === 'function') updateLazUI();
  }
  s('f-couche',     cfg.couche);
  s('f-zoom-min-s', cfg.zoom_min_s);
  s('f-zoom-max-s', cfg.zoom_max_s);
  s('f-zoom-min-l', cfg.zoom_min_l);
  s('f-zoom-max-l', cfg.zoom_max_l);
}

// ── Ombrages : liste d'instances paramétrées (shuttle list) ──────────────────
// Chaque instance = {type, params}. Plusieurs instances du même type avec des
// params différents coexistent (les params sont encodés dans le nom de fichier
// côté pipeline). Émission CLI : --shading TYPE:k=v,... (répétable).
// Ordre = utilité pratique (cf. _SHADING_TYPES côté pipeline) : LRM en tête
// (rapide + lisible pour un néophyte, donc défaut), puis VAT (détecteur complet),
// SVF, paire openness, RRIM, hillshades, slope en dernier.
const OMB_DEFS = {
  lrm:   {label:'LRM',    fields:{sigma:{lbl:'omb.sigma', tip:'tip.ombsigma', def:'', min:1, max:100, step:0.5, opt:true}}},
  vat:   {label:'VAT (composite)', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                           gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1}}},
  // e4mstp : gamma défaut 0.8 = ALIGNÉ sur le pipeline (PAS 2.0 comme svf/vat :
  // le composite couleur est déjà blendé, 2.0 l'écraserait en rendu très sombre ;
  // ombAdd() SÈME les défauts dans les params émis, donc ce def part au CLI).
  e4mstp:{label:'e4MSTP (composite couleur)', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                           gamma:{lbl:'omb.gamma', def:0.8, min:0.3, max:3.0, step:0.1}}},
  svf:   {label:'SVF',    fields:{conv :{lbl:'type',         def:'flux', opts:['flux','rvt']},
                                  dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                  gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1},
                                  sweep:{lbl:'sweep-horizon', def:1, bool:true}}},
  opos:  {label:'O+ openness', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                       gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1}}},
  oneg:  {label:'O− openness', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                       gamma:{lbl:'omb.gamma.mirror', def:2.0, min:0.3, max:3.0, step:0.1}}},
  rrim:  {label:'RRIM',   fields:{sigma:{lbl:'omb.sigma', tip:'tip.ombsigma', def:'', min:1, max:100, step:0.5, opt:true}}},
  multi: {label:'multi',  fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '315': {label:'315°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '045': {label:'045°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '135': {label:'135°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '225': {label:'225°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  slope: {label:'slope',  fields:{}},
};
let ombInstances = [{type:'lrm', params:{sigma: sigmaDefautM()}}];   // défaut = LRM (rapide + lisible)

function ombLabel(inst) {
  const d = OMB_DEFS[inst.type]; if (!d) return inst.type;
  const parts = Object.entries(inst.params)
    .filter(([k, v]) => v !== '' && v != null)
    .filter(([k, v]) => !(k === 'sweep' && v == 1))   // sweep=1 = défaut, pas de bruit
    .map(([k, v]) => `${k}=${v}`);
  return d.label + (parts.length ? '   [' + parts.join('  ') + ']' : '');
}
function ombRender(selIdx) {
  const sel = document.getElementById('omb-liste'); if (!sel) return;
  sel.innerHTML = '';
  ombInstances.forEach((inst, i) => {
    const o = document.createElement('option');
    o.value = i; o.textContent = ombLabel(inst);
    sel.appendChild(o);
  });
  if (selIdx != null && selIdx >= 0 && selIdx < ombInstances.length)
    sel.selectedIndex = selIdx;
  ombShowParams();
}
function ombAdd() {
  const t = document.getElementById('omb-dispo')?.value;
  if (!t || !OMB_DEFS[t]) return;
  const params = {};
  Object.entries(OMB_DEFS[t].fields).forEach(([k, f]) => {
    if (!f.opt) params[k] = f.def;
    else if (k === 'sigma') params[k] = sigmaDefautM();   // pré-remplir σ (LRM/RRIM) au défaut résolution
  });
  ombInstances.push({type: t, params});
  ombRender(ombInstances.length - 1);
}
function ombDel() {
  const i = document.getElementById('omb-liste')?.selectedIndex;
  if (i == null || i < 0) return;
  ombInstances.splice(i, 1);
  ombRender(Math.min(i, ombInstances.length - 1));
}
function ombShowParams() {
  const box = document.getElementById('omb-params'); if (!box) return;
  const i = document.getElementById('omb-liste')?.selectedIndex;
  box.innerHTML = '';
  const dimSpan = (txt) => {
    const sp = document.createElement('span');
    sp.style.color = 'var(--dim)'; sp.textContent = txt; return sp;
  };
  if (i == null || i < 0 || !ombInstances[i]) {
    box.appendChild(dimSpan('Sélectionnez une instance…')); return;
  }
  const inst = ombInstances[i], defs = OMB_DEFS[inst.type].fields;
  if (!Object.keys(defs).length) {
    box.appendChild(dimSpan('aucun paramètre')); return;
  }
  Object.entries(defs).forEach(([k, f]) => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:center;';
    row.appendChild(dimSpan(t(f.lbl)));
    let inp;
    if (f.opts) {
      inp = document.createElement('select');
      f.opts.forEach(v => {
        const o = document.createElement('option');
        o.value = v; o.textContent = v; inp.appendChild(o);
      });
      inp.value = inst.params[k] ?? f.def;
      inp.onchange = () => { inst.params[k] = inp.value; ombRender(i); };
    } else if (f.bool) {
      inp = document.createElement('input');
      inp.type = 'checkbox';
      inp.checked = (inst.params[k] ?? f.def) == 1;
      inp.onchange = () => { inst.params[k] = inp.checked ? 1 : 0; ombRender(i); };
    } else {
      inp = document.createElement('input');
      inp.type = 'number'; inp.className = 'inp-short';
      inp.min = f.min; inp.max = f.max; inp.step = f.step;
      inp.value = inst.params[k] ?? '';
      if (f.opt) inp.placeholder = 'auto (15 px)';
      inp.onchange = () => {
        const v = inp.value;
        if (v === '') delete inst.params[k];
        else inst.params[k] = parseFloat(v);
        ombRender(i);
      };
    }
    if (f.tip) inp.title = t(f.tip);
    row.appendChild(inp);
    box.appendChild(row);
  });
}
function ombToSpecs() {
  return ombInstances.map(inst => {
    const kv = Object.entries(inst.params)
      .filter(([k, v]) => v !== '' && v != null)
      .map(([k, v]) => `${k}=${v}`).join(',');
    return inst.type + (kv ? ':' + kv : '');
  });
}
function ombFromSpecs(specs) {
  ombInstances = [];
  (specs || []).forEach(s => {
    const t = s.split(':')[0];
    const rest = s.split(':').slice(1).join(':');
    if (!OMB_DEFS[t]) return;
    const params = {};
    if (rest) rest.split(',').forEach(kv => {
      const [k, v] = kv.split('=');
      if (k && v !== undefined && v !== '')
        params[k] = isNaN(parseFloat(v)) ? v : parseFloat(v);
    });
    ombInstances.push({type: t, params});
  });
  ombRender(0);
}
// Rendu initial (défaut LRM) — re-rendu par la restauration de cfg ensuite.
document.addEventListener('DOMContentLoaded', () => ombRender(0));

// ── Zoom de l'interface (persisté) ───────────────────────────────────────────
// Remplace le zoomable natif pywebview (invisible côté JS, donc impossible à
// sauvegarder). body.style.zoom est appliqué/persisté via set_ui_zoom, et
// restauré au lancement (get_init_data.ui_zoom).
let _uiZoom = 1.0;
function applyUiZoom(z, persist) {
  _uiZoom = Math.min(2.5, Math.max(0.5, Math.round(z * 20) / 20));   // pas de 5 %
  document.body.style.zoom = _uiZoom;
  if (persist && window.pywebview && pywebview.api && pywebview.api.set_ui_zoom) {
    pywebview.api.set_ui_zoom(_uiZoom).catch(() => {});
  }
}
window.addEventListener('wheel', e => {
  if (!e.ctrlKey) return;
  e.preventDefault();
  applyUiZoom(_uiZoom + (e.deltaY < 0 ? 0.05 : -0.05), true);
}, {passive: false});
window.addEventListener('keydown', e => {
  if (!e.ctrlKey) return;
  if (e.key === '+' || e.key === '=') { e.preventDefault(); applyUiZoom(_uiZoom + 0.05, true); }
  else if (e.key === '-')             { e.preventDefault(); applyUiZoom(_uiZoom - 0.05, true); }
  else if (e.key === '0')             { e.preventDefault(); applyUiZoom(1.0, true); }
});

// ── Dialogs ───────────────────────────────────────────────────────────────────
// Bouton « … » d'un champ dossier : sélecteur, positionné sur le dossier courant
// du champ ou, si « (auto) »/vide, sur la racine par défaut du tier (kind). Le
// dossier choisi remplace la valeur du champ.
async function pickDir(fieldId, kind) {
  const cur = (document.getElementById(fieldId)?.value || '').trim();
  const start = (cur && cur !== '(auto)') ? cur : '';
  const p = await pywebview.api.pick_dir(start, kind || '');
  if (p) {
    const el = document.getElementById(fieldId);
    el.value = p;
    // Une valeur posée par script ne déclenche pas onchange : dispatcher
    // l'événement comme le ferait une saisie (ex. f-dossier → refreshProjets).
    el.dispatchEvent(new Event('change'));
  }
}
async function pickFile(fieldId, multiple, exts) {
  const p = await pywebview.api.pick_file(multiple, false, exts);
  if (p) document.getElementById(fieldId).value = Array.isArray(p) ? p.join(';') : p;
}
async function pickFileSave(fieldId) {
  const p = await pywebview.api.pick_file(false, true, []);
  if (p) document.getElementById(fieldId).value = p;
}
async function fusionAjouter() {
  const files = await pywebview.api.pick_file(true, false, []);
  if (!files) return;
  const all = Array.isArray(files) ? files : [files];
  // .geojson.gz strict (pas tout .gz) : aligne le filtre sur le message
  // d'erreur ci-dessous et sur ce que la fusion sait réellement lire.
  const valid = all.filter(f => f.endsWith('.geojson') || f.endsWith('.geojson.gz'));
  const invalid = all.filter(f => !valid.includes(f));
  if (invalid.length) alert(tf('fusion.ignored', {files: invalid.map(f=>f.split(/[\\/]/).pop()).join(', ')}));
  valid.forEach(f => { if (!fusionFiles.includes(f)) fusionFiles.push(f); });
  renderFusionList();
}
function fusionSupprimer() {
  if (fusionSel >= 0) { fusionFiles.splice(fusionSel, 1); fusionSel = -1; renderFusionList(); }
}
function fusionVider() { fusionFiles = []; fusionSel = -1; renderFusionList(); }
function renderFusionList() {
  const c = document.getElementById('fusion-list');
  c.innerHTML = fusionFiles.map((f,i) =>
    `<div class="${i===fusionSel?'sel':''}" onclick="fusionSelect(${i})">${f.split(/[\\/]/).pop()}</div>`
  ).join('');
}
function fusionSelect(i) { fusionSel = i; renderFusionList(); }

// ── Lancement ─────────────────────────────────────────────────────────────────
function setFormLocked(locked) {
  const els = document.getElementById('main')
    .querySelectorAll('input,select,button:not(#btn-stop):not(#btn-log)');
  els.forEach(el => { el.disabled = locked; });
}

// ── File d'attente des traitements ────────────────────────────────────────
// La file est un simple tableau JS ; « Lancer » la traite en série via le
// MÊME moteur que le lancement simple (launch/poll_log, un subprocess à la
// fois). Continue-on-error façon `job1 ; job2` du shell : un échec n'arrête
// pas la file. Pas de persistance (la file vit le temps de la session GUI).
let fileAttente  = [];      // [{cfg, label, status}]  status: pending|running|ok|err
let arretDemande = false;   // « Arrêter » : coupe le job courant ET annule la file

const _LABELS_TYPE = {lidar:'LiDAR', scan:'Raster', osm:'OSM',
                      vecteur:'Vecteur', fusion:'Fusion', decoupe:'Découpe'};

function labelPourCfg(cfg) {
  const zone = cfg.nom || cfg.ville || cfg.dep || cfg.region || cfg.gps || cfg.bbox || '?';
  return (_LABELS_TYPE[cfg.type] || cfg.type) + ' · ' + zone;
}

// Valide le formulaire courant ; renvoie la config, ou null (avec alerte) si
// invalide. Partagé par « Lancer » (mode simple) et « Ajouter à la file ».
function validerFormulaire() {
  const nom = document.getElementById('f-nom').value.trim();
  if (!nom) { alert(t('req.name')); return null; }
  const cfg = getConfig();
  if (cfg.type === 'decoupe' && !cfg.source_decoupe) { alert(t('req.source')); return null; }
  if (cfg.type !== 'fusion' && cfg.type !== 'decoupe') {
    const zoneOk = (cfg.mode === 'ville'  && cfg.ville)  ||
                   (cfg.mode === 'gps'    && cfg.gps)    ||
                   (cfg.mode === 'bbox'   && cfg.bbox)   ||
                   (cfg.mode === 'dep'    && cfg.dep)    ||
                   (cfg.mode === 'region' && cfg.region) || false;
    if (!zoneOk) {
      const labels = {ville:t('mode.ville'), gps:t('mode.gps'), bbox:t('mode.bbox'),
                      dep:t('mode.dep'), region:t('mode.region')};
      alert(tf('req.field', {f: labels[cfg.mode] || cfg.mode}));
      return null;
    }
  }
  return cfg;
}

function ajouterFile() {
  const cfg = validerFormulaire();
  if (!cfg) return;
  fileAttente.push({cfg: cfg, label: labelPourCfg(cfg), status: 'pending'});
  renderFile();
}

function retirerFile(i) {
  if (polling) return;   // pas de réindexation pendant qu'un job tourne
  fileAttente.splice(i, 1);
  renderFile();
}

function viderFile() {
  if (polling) return;
  fileAttente = [];
  renderFile();
}

// Affiche la file (puces d'items avec statut + retrait) et relibelle « Lancer »
// en « Lancer la file (N) » selon le nombre d'items EN ATTENTE.
function renderFile() {
  const box = document.getElementById('file-attente');
  const btn = document.getElementById('btn-run');
  const pending = fileAttente.filter(it => it.status === 'pending').length;
  if (btn) btn.textContent = pending ? tf('run.queue', {n: pending}) : t('btn.run');
  if (!box) return;
  if (!fileAttente.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
  const icone   = {pending:'•', running:'⏳', ok:'✓', err:'✗'};
  const couleur = {pending:'var(--dim)', running:'var(--ac)', ok:'#4caf50', err:'#e07070'};
  box.style.display = 'block';
  box.innerHTML =
    '<span style="color:var(--dim);margin-right:8px">' +
      tf('queue.count', {n: fileAttente.length}) + '</span>' +
    fileAttente.map((it, i) =>
      '<span style="display:inline-flex;align-items:center;gap:5px;margin:2px 6px 2px 0;' +
      'padding:2px 8px;border:1px solid var(--bd);border-radius:12px">' +
      '<span style="color:' + couleur[it.status] + '">' + icone[it.status] + '</span>' +
      '<span>' + _acEsc(it.label) + '</span>' +
      '<span onclick="retirerFile(' + i + ')" title="' + _acEsc(t('queue.remove')) + '" ' +
      'style="cursor:pointer;color:var(--dim);font-weight:700">×</span></span>'
    ).join('') +
    '<a onclick="viderFile()" style="cursor:pointer;color:var(--dim);' +
      'text-decoration:underline;margin-left:4px">' + _acEsc(t('queue.clear')) + '</a>';
}

// Exécute UNE config : lance le subprocess et résout {code, result_dir} quand
// poll_log signale la fin. silent=true (mode file) supprime l'alerte bloquante
// d'échec et l'ouverture du dossier (sinon la file se figerait sur un OK à
// cliquer) ; le récap se fait alors en fin de file.
function executerCfg(cfg, silent) {
  return new Promise(resolve => {
    viderLog();
    document.getElementById('log-status').textContent = t('running');
    setLogProgress(0, '');
    // try/catch via .catch : si le bridge pywebview rejette (API bloquée),
    // la promesse doit quand même se résoudre, sinon la file se fige.
    Promise.resolve(pywebview.api.launch(cfg)).then(res => {
      if (!res || res.error) {
        const msg = (res && res.error) || t('apiunavail');
        if (!silent) alert(msg); else ajouterLigneLog('\n✗ ' + msg + '\n', 'err');
        resolve({code: -1});
        return;
      }
      document.getElementById('footer-status').textContent =
        '▶ ' + (res.cmd || '').split(' ').slice(-3).join(' ') + '…';
      polling = setInterval(async () => {
        const r = await pywebview.api.poll_log();
        if (r.items) {
          r.items.forEach(item => {
            if (item.line !== undefined) ajouterLigneLog(item.line, item.tag || 'ok');
            if (item.pct !== undefined && item.pct >= 0) {
              setLogProgress(item.pct, '');
              document.getElementById('footer-status').textContent =
                item.pct + '%  ' + (item.label || '').substring(0, 80);
              majLigneProgression(item.label);
            }
            if (item.pct === -1 && item.label) {
              document.getElementById('footer-status').textContent =
                item.label.substring(0, 100);
              majLigneProgression(item.label);
            }
          });
        }
        if (r.done) {
          clearInterval(polling); polling = null;
          setLogProgress(100, r.code === 0 ? 'ok' : 'err');
          // Footer/statut : le mode simple les pose ici ; le mode file les
          // gère dans lancerFile (ligne « File i/n » puis récap). Idem si
          // arretDemande : ne pas écraser le « ⚠ Arrêté » posé par arreter().
          if (!silent && !arretDemande) {
            const lbl = r.code === 0 ? t('done') : tf('err.code', {c: r.code});
            document.getElementById('footer-status').textContent = lbl;
            document.getElementById('log-status').textContent = lbl;
          }
          if (r.code !== 0) {
            // Erreur → ouvrir le panneau de log s'il est caché (les deux modes).
            const p = document.getElementById('panneau-log');
            if (p && p.classList.contains('hidden')) toggleLogPanel();
            if (!silent && !arretDemande) {
              try {
                const err = await pywebview.api.get_last_error();
                if (err && err.msg) alert(tf('fail.detail', {c: err.retcode, msg: err.msg}));
                else alert(tf('fail.generic', {c: r.code}));
              } catch (e) {
                console.error('get_last_error:', e);
                alert(tf('fail.generic', {c: r.code}));
              }
            }
          }
          if (r.code === 0 && !silent && !arretDemande) {
            refreshProjets();   // le run peut avoir créé un nouveau projet
            pywebview.api.get_historique().then(hist => {
              if (hist && hist.length) {
                buildHistorique(hist);
                const last = hist[0];
                if (last && last.params) loadConfig(last.params);
              }
            }).catch(e => console.error('get_historique error:', e));
            if (r.result_dir) pywebview.api.open_folder(r.result_dir);
          }
          resolve({code: r.code, result_dir: r.result_dir});
        }
      }, 250);
    }).catch(e => {
      alert(t('apiunavail') + ' : ' + e);
      resolve({code: -1});
    });
  });
}

async function lancer() {
  // Items en attente → traiter la file. Sinon → run simple du form courant.
  const pending = fileAttente.filter(it => it.status === 'pending').length;
  if (pending) return lancerFile();
  const cfg = validerFormulaire();
  if (!cfg) return;
  arretDemande = false;
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  document.getElementById('footer-status').textContent = t('running');
  setFormLocked(true);
  await executerCfg(cfg, false);
  btnReset();
}

// Traite la file en série (un job à la fois, même moteur que « Lancer »).
// Continue-on-error : un échec n'arrête pas la file. « Arrêter » pose
// arretDemande → coupe le job courant (le process tué remonte via poll_log)
// et sort de la boucle.
// Signature de ce qu'une tâche télécharge : deux tâches de même signature
// piochent EXACTEMENT les mêmes dalles dans le cache partagé. Provider et
// surface parce qu'ils déterminent le nom des dalles (fr_laz05_csf_… vs
// fr_dalle_…), zone parce qu'elle détermine lesquelles. Comparaison sur les
// champs bruts du formulaire : pas de géocodage, donc deux libellés de ville
// différents pour la même ville comptent comme deux zones — conservateur dans
// le bon sens (on ne garde jamais des dalles plus longtemps que prouvé utile).
function _signatureDalles(cfg) {
  return [cfg.provider || '', cfg.laz ? 'laz' : 'mnt', cfg.laz_ground || '',
          cfg.mode || '', cfg.ville || '', cfg.gps || '', cfg.bbox || '',
          cfg.dep || '', cfg.region || '', cfg.rayon ?? ''].join('|');
}

async function lancerFile() {
  arretDemande = false;
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  setFormLocked(true);
  let ok = 0, ko = 0;
  for (let i = 0; i < fileAttente.length; i++) {
    if (arretDemande) break;
    if (fileAttente[i].status !== 'pending') continue;   // déjà traité (re-Lancer)
    fileAttente[i].status = 'running';
    renderFile();
    document.getElementById('footer-status').textContent =
      tf('queue.running', {i: i + 1, n: fileAttente.length, label: fileAttente[i].label});
    // Nettoyage inter-tâches : si une tâche PLUS LOIN dans la file retélécharge
    // les mêmes dalles, on garde le cache pour elle (--cleanup-keep-tiles). Le
    // nettoyage inter-chunk, lui, reste actif : c'est ce qui permet de traiter
    // un département sans saturer le disque. Seule la DERNIÈRE tâche d'un
    // groupe efface réellement les dalles.
    const sig = _signatureDalles(fileAttente[i].cfg);
    const reUtilisee = fileAttente.slice(i + 1).some(
      it => it.status === 'pending' && _signatureDalles(it.cfg) === sig);
    fileAttente[i].cfg.cleanup_keep_tiles = reUtilisee;
    const r = await executerCfg(fileAttente[i].cfg, true);
    fileAttente[i].status = r.code === 0 ? 'ok' : 'err';
    if (r.code === 0) ok++; else ko++;
    renderFile();
  }
  // Récap une seule fois en fin de file (moins de churn qu'un rafraîchissement
  // par job).
  refreshProjets();
  pywebview.api.get_historique().then(hist => {
    if (hist && hist.length) buildHistorique(hist);
  }).catch(e => console.error('get_historique error:', e));
  const recap = arretDemande ? t('stopped') : tf('queue.done', {ok: ok, ko: ko});
  document.getElementById('footer-status').textContent = recap;
  document.getElementById('log-status').textContent = recap;
  btnReset();
}

async function arreter() {
  // Pose arretDemande AVANT stop() : le job courant sera tué, poll_log verra
  // r.done (code ≠ 0) et résoudra executerCfg — c'est ce qui débloque la
  // boucle de file. Ne PAS clearInterval ici : sinon la promesse reste
  // pendante et la file se fige. btnReset est fait par le done handler
  // (mode simple) ou en fin de lancerFile (mode file).
  arretDemande = true;
  await pywebview.api.stop();
  document.getElementById('footer-status').textContent = t('stopped');
}

function btnReset() {
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  setFormLocked(false);
}
// (L'ancien bloc zoom Ctrl+molette non persisté a été retiré : applyUiZoom
//  ci-dessus est l'unique gestionnaire — les deux tournaient en concurrence
//  et appliquaient chacun leur valeur de zoom au même événement.)


// ── QR code (qrcode-generator, Kazuhiko Arase, MIT) ──────────────
// Lib UMD (AMD/CommonJS) sans fallback global : on la wrappe dans un faux
// module pour exposer window.qrcode en <script> simple. Rendu SVG (createSvgTag).
window.qrcode = (function(){var module={},exports={};module.exports=exports;var qrcode=function(){var t=function(t,r){var e=t,n=g[r],o=null,i=0,a=null,u=[],f={},c=function(t,r){o=function(t){for(var r=new Array(t),e=0;e<t;e+=1){r[e]=new Array(t);for(var n=0;n<t;n+=1)r[e][n]=null}return r}(i=4*e+17),l(0,0),l(i-7,0),l(0,i-7),s(),h(),d(t,r),e>=7&&v(t),null==a&&(a=p(e,n,u)),w(a,r)},l=function(t,r){for(var e=-1;e<=7;e+=1)if(!(t+e<=-1||i<=t+e))for(var n=-1;n<=7;n+=1)r+n<=-1||i<=r+n||(o[t+e][r+n]=0<=e&&e<=6&&(0==n||6==n)||0<=n&&n<=6&&(0==e||6==e)||2<=e&&e<=4&&2<=n&&n<=4)},h=function(){for(var t=8;t<i-8;t+=1)null==o[t][6]&&(o[t][6]=t%2==0);for(var r=8;r<i-8;r+=1)null==o[6][r]&&(o[6][r]=r%2==0)},s=function(){for(var t=B.getPatternPosition(e),r=0;r<t.length;r+=1)for(var n=0;n<t.length;n+=1){var i=t[r],a=t[n];if(null==o[i][a])for(var u=-2;u<=2;u+=1)for(var f=-2;f<=2;f+=1)o[i+u][a+f]=-2==u||2==u||-2==f||2==f||0==u&&0==f}},v=function(t){for(var r=B.getBCHTypeNumber(e),n=0;n<18;n+=1){var a=!t&&1==(r>>n&1);o[Math.floor(n/3)][n%3+i-8-3]=a}for(n=0;n<18;n+=1){a=!t&&1==(r>>n&1);o[n%3+i-8-3][Math.floor(n/3)]=a}},d=function(t,r){for(var e=n<<3|r,a=B.getBCHTypeInfo(e),u=0;u<15;u+=1){var f=!t&&1==(a>>u&1);u<6?o[u][8]=f:u<8?o[u+1][8]=f:o[i-15+u][8]=f}for(u=0;u<15;u+=1){f=!t&&1==(a>>u&1);u<8?o[8][i-u-1]=f:u<9?o[8][15-u-1+1]=f:o[8][15-u-1]=f}o[i-8][8]=!t},w=function(t,r){for(var e=-1,n=i-1,a=7,u=0,f=B.getMaskFunction(r),c=i-1;c>0;c-=2)for(6==c&&(c-=1);;){for(var g=0;g<2;g+=1)if(null==o[n][c-g]){var l=!1;u<t.length&&(l=1==(t[u]>>>a&1)),f(n,c-g)&&(l=!l),o[n][c-g]=l,-1==(a-=1)&&(u+=1,a=7)}if((n+=e)<0||i<=n){n-=e,e=-e;break}}},p=function(t,r,e){for(var n=A.getRSBlocks(t,r),o=b(),i=0;i<e.length;i+=1){var a=e[i];o.put(a.getMode(),4),o.put(a.getLength(),B.getLengthInBits(a.getMode(),t)),a.write(o)}var u=0;for(i=0;i<n.length;i+=1)u+=n[i].dataCount;if(o.getLengthInBits()>8*u)throw"code length overflow. ("+o.getLengthInBits()+">"+8*u+")";for(o.getLengthInBits()+4<=8*u&&o.put(0,4);o.getLengthInBits()%8!=0;)o.putBit(!1);for(;!(o.getLengthInBits()>=8*u||(o.put(236,8),o.getLengthInBits()>=8*u));)o.put(17,8);return function(t,r){for(var e=0,n=0,o=0,i=new Array(r.length),a=new Array(r.length),u=0;u<r.length;u+=1){var f=r[u].dataCount,c=r[u].totalCount-f;n=Math.max(n,f),o=Math.max(o,c),i[u]=new Array(f);for(var g=0;g<i[u].length;g+=1)i[u][g]=255&t.getBuffer()[g+e];e+=f;var l=B.getErrorCorrectPolynomial(c),h=k(i[u],l.getLength()-1).mod(l);for(a[u]=new Array(l.getLength()-1),g=0;g<a[u].length;g+=1){var s=g+h.getLength()-a[u].length;a[u][g]=s>=0?h.getAt(s):0}}var v=0;for(g=0;g<r.length;g+=1)v+=r[g].totalCount;var d=new Array(v),w=0;for(g=0;g<n;g+=1)for(u=0;u<r.length;u+=1)g<i[u].length&&(d[w]=i[u][g],w+=1);for(g=0;g<o;g+=1)for(u=0;u<r.length;u+=1)g<a[u].length&&(d[w]=a[u][g],w+=1);return d}(o,n)};f.addData=function(t,r){var e=null;switch(r=r||"Byte"){case"Numeric":e=M(t);break;case"Alphanumeric":e=x(t);break;case"Byte":e=m(t);break;case"Kanji":e=L(t);break;default:throw"mode:"+r}u.push(e),a=null},f.isDark=function(t,r){if(t<0||i<=t||r<0||i<=r)throw t+","+r;return o[t][r]},f.getModuleCount=function(){return i},f.make=function(){if(e<1){for(var t=1;t<40;t++){for(var r=A.getRSBlocks(t,n),o=b(),i=0;i<u.length;i++){var a=u[i];o.put(a.getMode(),4),o.put(a.getLength(),B.getLengthInBits(a.getMode(),t)),a.write(o)}var g=0;for(i=0;i<r.length;i++)g+=r[i].dataCount;if(o.getLengthInBits()<=8*g)break}e=t}c(!1,function(){for(var t=0,r=0,e=0;e<8;e+=1){c(!0,e);var n=B.getLostPoint(f);(0==e||t>n)&&(t=n,r=e)}return r}())},f.createTableTag=function(t,r){t=t||2;var e="";e+='<table style="',e+=" border-width: 0px; border-style: none;",e+=" border-collapse: collapse;",e+=" padding: 0px; margin: "+(r=void 0===r?4*t:r)+"px;",e+='">',e+="<tbody>";for(var n=0;n<f.getModuleCount();n+=1){e+="<tr>";for(var o=0;o<f.getModuleCount();o+=1)e+='<td style="',e+=" border-width: 0px; border-style: none;",e+=" border-collapse: collapse;",e+=" padding: 0px; margin: 0px;",e+=" width: "+t+"px;",e+=" height: "+t+"px;",e+=" background-color: ",e+=f.isDark(n,o)?"#000000":"#ffffff",e+=";",e+='"/>';e+="</tr>"}return e+="</tbody>",e+="</table>"},f.createSvgTag=function(t,r,e,n){var o={};"object"==typeof arguments[0]&&(t=(o=arguments[0]).cellSize,r=o.margin,e=o.alt,n=o.title),t=t||2,r=void 0===r?4*t:r,(e="string"==typeof e?{text:e}:e||{}).text=e.text||null,e.id=e.text?e.id||"qrcode-description":null,(n="string"==typeof n?{text:n}:n||{}).text=n.text||null,n.id=n.text?n.id||"qrcode-title":null;var i,a,u,c,g=f.getModuleCount()*t+2*r,l="";for(c="l"+t+",0 0,"+t+" -"+t+",0 0,-"+t+"z ",l+='<svg version="1.1" xmlns="http://www.w3.org/2000/svg"',l+=o.scalable?"":' width="'+g+'px" height="'+g+'px"',l+=' viewBox="0 0 '+g+" "+g+'" ',l+=' preserveAspectRatio="xMinYMin meet"',l+=n.text||e.text?' role="img" aria-labelledby="'+y([n.id,e.id].join(" ").trim())+'"':"",l+=">",l+=n.text?'<title id="'+y(n.id)+'">'+y(n.text)+"</title>":"",l+=e.text?'<description id="'+y(e.id)+'">'+y(e.text)+"</description>":"",l+='<rect width="100%" height="100%" fill="white" cx="0" cy="0"/>',l+='<path d="',a=0;a<f.getModuleCount();a+=1)for(u=a*t+r,i=0;i<f.getModuleCount();i+=1)f.isDark(a,i)&&(l+="M"+(i*t+r)+","+u+c);return l+='" stroke="transparent" fill="black"/>',l+="</svg>"},f.createDataURL=function(t,r){t=t||2,r=void 0===r?4*t:r;var e=f.getModuleCount()*t+2*r,n=r,o=e-r;return I(e,e,(function(r,e){if(n<=r&&r<o&&n<=e&&e<o){var i=Math.floor((r-n)/t),a=Math.floor((e-n)/t);return f.isDark(a,i)?0:1}return 1}))},f.createImgTag=function(t,r,e){t=t||2,r=void 0===r?4*t:r;var n=f.getModuleCount()*t+2*r,o="";return o+="<img",o+=' src="',o+=f.createDataURL(t,r),o+='"',o+=' width="',o+=n,o+='"',o+=' height="',o+=n,o+='"',e&&(o+=' alt="',o+=y(e),o+='"'),o+="/>"};var y=function(t){for(var r="",e=0;e<t.length;e+=1){var n=t.charAt(e);switch(n){case"<":r+="&lt;";break;case">":r+="&gt;";break;case"&":r+="&amp;";break;case'"':r+="&quot;";break;default:r+=n}}return r};return f.createASCII=function(t,r){if((t=t||1)<2)return function(t){t=void 0===t?2:t;var r,e,n,o,i,a=1*f.getModuleCount()+2*t,u=t,c=a-t,g={"██":"█","█ ":"▀"," █":"▄","  ":" "},l={"██":"▀","█ ":"▀"," █":" ","  ":" "},h="";for(r=0;r<a;r+=2){for(n=Math.floor((r-u)/1),o=Math.floor((r+1-u)/1),e=0;e<a;e+=1)i="█",u<=e&&e<c&&u<=r&&r<c&&f.isDark(n,Math.floor((e-u)/1))&&(i=" "),u<=e&&e<c&&u<=r+1&&r+1<c&&f.isDark(o,Math.floor((e-u)/1))?i+=" ":i+="█",h+=t<1&&r+1>=c?l[i]:g[i];h+="\n"}return a%2&&t>0?h.substring(0,h.length-a-1)+Array(a+1).join("▀"):h.substring(0,h.length-1)}(r);t-=1,r=void 0===r?2*t:r;var e,n,o,i,a=f.getModuleCount()*t+2*r,u=r,c=a-r,g=Array(t+1).join("██"),l=Array(t+1).join("  "),h="",s="";for(e=0;e<a;e+=1){for(o=Math.floor((e-u)/t),s="",n=0;n<a;n+=1)i=1,u<=n&&n<c&&u<=e&&e<c&&f.isDark(o,Math.floor((n-u)/t))&&(i=0),s+=i?g:l;for(o=0;o<t;o+=1)h+=s+"\n"}return h.substring(0,h.length-1)},f.renderTo2dContext=function(t,r){r=r||2;for(var e=f.getModuleCount(),n=0;n<e;n++)for(var o=0;o<e;o++)t.fillStyle=f.isDark(n,o)?"black":"white",t.fillRect(n*r,o*r,r,r)},f};t.stringToBytes=(t.stringToBytesFuncs={default:function(t){for(var r=[],e=0;e<t.length;e+=1){var n=t.charCodeAt(e);r.push(255&n)}return r}}).default,t.createStringToBytes=function(t,r){var e=function(){for(var e=S(t),n=function(){var t=e.read();if(-1==t)throw"eof";return t},o=0,i={};;){var a=e.read();if(-1==a)break;var u=n(),f=n()<<8|n();i[String.fromCharCode(a<<8|u)]=f,o+=1}if(o!=r)throw o+" != "+r;return i}(),n="?".charCodeAt(0);return function(t){for(var r=[],o=0;o<t.length;o+=1){var i=t.charCodeAt(o);if(i<128)r.push(i);else{var a=e[t.charAt(o)];"number"==typeof a?(255&a)==a?r.push(a):(r.push(a>>>8),r.push(255&a)):r.push(n)}}return r}};var r,e,n,o,i,a=1,u=2,f=4,c=8,g={L:1,M:0,Q:3,H:2},l=0,h=1,s=2,v=3,d=4,w=5,p=6,y=7,B=(r=[[],[6,18],[6,22],[6,26],[6,30],[6,34],[6,22,38],[6,24,42],[6,26,46],[6,28,50],[6,30,54],[6,32,58],[6,34,62],[6,26,46,66],[6,26,48,70],[6,26,50,74],[6,30,54,78],[6,30,56,82],[6,30,58,86],[6,34,62,90],[6,28,50,72,94],[6,26,50,74,98],[6,30,54,78,102],[6,28,54,80,106],[6,32,58,84,110],[6,30,58,86,114],[6,34,62,90,118],[6,26,50,74,98,122],[6,30,54,78,102,126],[6,26,52,78,104,130],[6,30,56,82,108,134],[6,34,60,86,112,138],[6,30,58,86,114,142],[6,34,62,90,118,146],[6,30,54,78,102,126,150],[6,24,50,76,102,128,154],[6,28,54,80,106,132,158],[6,32,58,84,110,136,162],[6,26,54,82,110,138,166],[6,30,58,86,114,142,170]],e=1335,n=7973,i=function(t){for(var r=0;0!=t;)r+=1,t>>>=1;return r},(o={}).getBCHTypeInfo=function(t){for(var r=t<<10;i(r)-i(e)>=0;)r^=e<<i(r)-i(e);return 21522^(t<<10|r)},o.getBCHTypeNumber=function(t){for(var r=t<<12;i(r)-i(n)>=0;)r^=n<<i(r)-i(n);return t<<12|r},o.getPatternPosition=function(t){return r[t-1]},o.getMaskFunction=function(t){switch(t){case l:return function(t,r){return(t+r)%2==0};case h:return function(t,r){return t%2==0};case s:return function(t,r){return r%3==0};case v:return function(t,r){return(t+r)%3==0};case d:return function(t,r){return(Math.floor(t/2)+Math.floor(r/3))%2==0};case w:return function(t,r){return t*r%2+t*r%3==0};case p:return function(t,r){return(t*r%2+t*r%3)%2==0};case y:return function(t,r){return(t*r%3+(t+r)%2)%2==0};default:throw"bad maskPattern:"+t}},o.getErrorCorrectPolynomial=function(t){for(var r=k([1],0),e=0;e<t;e+=1)r=r.multiply(k([1,C.gexp(e)],0));return r},o.getLengthInBits=function(t,r){if(1<=r&&r<10)switch(t){case a:return 10;case u:return 9;case f:case c:return 8;default:throw"mode:"+t}else if(r<27)switch(t){case a:return 12;case u:return 11;case f:return 16;case c:return 10;default:throw"mode:"+t}else{if(!(r<41))throw"type:"+r;switch(t){case a:return 14;case u:return 13;case f:return 16;case c:return 12;default:throw"mode:"+t}}},o.getLostPoint=function(t){for(var r=t.getModuleCount(),e=0,n=0;n<r;n+=1)for(var o=0;o<r;o+=1){for(var i=0,a=t.isDark(n,o),u=-1;u<=1;u+=1)if(!(n+u<0||r<=n+u))for(var f=-1;f<=1;f+=1)o+f<0||r<=o+f||0==u&&0==f||a==t.isDark(n+u,o+f)&&(i+=1);i>5&&(e+=3+i-5)}for(n=0;n<r-1;n+=1)for(o=0;o<r-1;o+=1){var c=0;t.isDark(n,o)&&(c+=1),t.isDark(n+1,o)&&(c+=1),t.isDark(n,o+1)&&(c+=1),t.isDark(n+1,o+1)&&(c+=1),0!=c&&4!=c||(e+=3)}for(n=0;n<r;n+=1)for(o=0;o<r-6;o+=1)t.isDark(n,o)&&!t.isDark(n,o+1)&&t.isDark(n,o+2)&&t.isDark(n,o+3)&&t.isDark(n,o+4)&&!t.isDark(n,o+5)&&t.isDark(n,o+6)&&(e+=40);for(o=0;o<r;o+=1)for(n=0;n<r-6;n+=1)t.isDark(n,o)&&!t.isDark(n+1,o)&&t.isDark(n+2,o)&&t.isDark(n+3,o)&&t.isDark(n+4,o)&&!t.isDark(n+5,o)&&t.isDark(n+6,o)&&(e+=40);var g=0;for(o=0;o<r;o+=1)for(n=0;n<r;n+=1)t.isDark(n,o)&&(g+=1);return e+=Math.abs(100*g/r/r-50)/5*10},o),C=function(){for(var t=new Array(256),r=new Array(256),e=0;e<8;e+=1)t[e]=1<<e;for(e=8;e<256;e+=1)t[e]=t[e-4]^t[e-5]^t[e-6]^t[e-8];for(e=0;e<255;e+=1)r[t[e]]=e;var n={glog:function(t){if(t<1)throw"glog("+t+")";return r[t]},gexp:function(r){for(;r<0;)r+=255;for(;r>=256;)r-=255;return t[r]}};return n}();function k(t,r){if(void 0===t.length)throw t.length+"/"+r;var e=function(){for(var e=0;e<t.length&&0==t[e];)e+=1;for(var n=new Array(t.length-e+r),o=0;o<t.length-e;o+=1)n[o]=t[o+e];return n}(),n={getAt:function(t){return e[t]},getLength:function(){return e.length},multiply:function(t){for(var r=new Array(n.getLength()+t.getLength()-1),e=0;e<n.getLength();e+=1)for(var o=0;o<t.getLength();o+=1)r[e+o]^=C.gexp(C.glog(n.getAt(e))+C.glog(t.getAt(o)));return k(r,0)},mod:function(t){if(n.getLength()-t.getLength()<0)return n;for(var r=C.glog(n.getAt(0))-C.glog(t.getAt(0)),e=new Array(n.getLength()),o=0;o<n.getLength();o+=1)e[o]=n.getAt(o);for(o=0;o<t.getLength();o+=1)e[o]^=C.gexp(C.glog(t.getAt(o))+r);return k(e,0).mod(t)}};return n}var A=function(){var t=[[1,26,19],[1,26,16],[1,26,13],[1,26,9],[1,44,34],[1,44,28],[1,44,22],[1,44,16],[1,70,55],[1,70,44],[2,35,17],[2,35,13],[1,100,80],[2,50,32],[2,50,24],[4,25,9],[1,134,108],[2,67,43],[2,33,15,2,34,16],[2,33,11,2,34,12],[2,86,68],[4,43,27],[4,43,19],[4,43,15],[2,98,78],[4,49,31],[2,32,14,4,33,15],[4,39,13,1,40,14],[2,121,97],[2,60,38,2,61,39],[4,40,18,2,41,19],[4,40,14,2,41,15],[2,146,116],[3,58,36,2,59,37],[4,36,16,4,37,17],[4,36,12,4,37,13],[2,86,68,2,87,69],[4,69,43,1,70,44],[6,43,19,2,44,20],[6,43,15,2,44,16],[4,101,81],[1,80,50,4,81,51],[4,50,22,4,51,23],[3,36,12,8,37,13],[2,116,92,2,117,93],[6,58,36,2,59,37],[4,46,20,6,47,21],[7,42,14,4,43,15],[4,133,107],[8,59,37,1,60,38],[8,44,20,4,45,21],[12,33,11,4,34,12],[3,145,115,1,146,116],[4,64,40,5,65,41],[11,36,16,5,37,17],[11,36,12,5,37,13],[5,109,87,1,110,88],[5,65,41,5,66,42],[5,54,24,7,55,25],[11,36,12,7,37,13],[5,122,98,1,123,99],[7,73,45,3,74,46],[15,43,19,2,44,20],[3,45,15,13,46,16],[1,135,107,5,136,108],[10,74,46,1,75,47],[1,50,22,15,51,23],[2,42,14,17,43,15],[5,150,120,1,151,121],[9,69,43,4,70,44],[17,50,22,1,51,23],[2,42,14,19,43,15],[3,141,113,4,142,114],[3,70,44,11,71,45],[17,47,21,4,48,22],[9,39,13,16,40,14],[3,135,107,5,136,108],[3,67,41,13,68,42],[15,54,24,5,55,25],[15,43,15,10,44,16],[4,144,116,4,145,117],[17,68,42],[17,50,22,6,51,23],[19,46,16,6,47,17],[2,139,111,7,140,112],[17,74,46],[7,54,24,16,55,25],[34,37,13],[4,151,121,5,152,122],[4,75,47,14,76,48],[11,54,24,14,55,25],[16,45,15,14,46,16],[6,147,117,4,148,118],[6,73,45,14,74,46],[11,54,24,16,55,25],[30,46,16,2,47,17],[8,132,106,4,133,107],[8,75,47,13,76,48],[7,54,24,22,55,25],[22,45,15,13,46,16],[10,142,114,2,143,115],[19,74,46,4,75,47],[28,50,22,6,51,23],[33,46,16,4,47,17],[8,152,122,4,153,123],[22,73,45,3,74,46],[8,53,23,26,54,24],[12,45,15,28,46,16],[3,147,117,10,148,118],[3,73,45,23,74,46],[4,54,24,31,55,25],[11,45,15,31,46,16],[7,146,116,7,147,117],[21,73,45,7,74,46],[1,53,23,37,54,24],[19,45,15,26,46,16],[5,145,115,10,146,116],[19,75,47,10,76,48],[15,54,24,25,55,25],[23,45,15,25,46,16],[13,145,115,3,146,116],[2,74,46,29,75,47],[42,54,24,1,55,25],[23,45,15,28,46,16],[17,145,115],[10,74,46,23,75,47],[10,54,24,35,55,25],[19,45,15,35,46,16],[17,145,115,1,146,116],[14,74,46,21,75,47],[29,54,24,19,55,25],[11,45,15,46,46,16],[13,145,115,6,146,116],[14,74,46,23,75,47],[44,54,24,7,55,25],[59,46,16,1,47,17],[12,151,121,7,152,122],[12,75,47,26,76,48],[39,54,24,14,55,25],[22,45,15,41,46,16],[6,151,121,14,152,122],[6,75,47,34,76,48],[46,54,24,10,55,25],[2,45,15,64,46,16],[17,152,122,4,153,123],[29,74,46,14,75,47],[49,54,24,10,55,25],[24,45,15,46,46,16],[4,152,122,18,153,123],[13,74,46,32,75,47],[48,54,24,14,55,25],[42,45,15,32,46,16],[20,147,117,4,148,118],[40,75,47,7,76,48],[43,54,24,22,55,25],[10,45,15,67,46,16],[19,148,118,6,149,119],[18,75,47,31,76,48],[34,54,24,34,55,25],[20,45,15,61,46,16]],r=function(t,r){var e={};return e.totalCount=t,e.dataCount=r,e},e={};return e.getRSBlocks=function(e,n){var o=function(r,e){switch(e){case g.L:return t[4*(r-1)+0];case g.M:return t[4*(r-1)+1];case g.Q:return t[4*(r-1)+2];case g.H:return t[4*(r-1)+3];default:return}}(e,n);if(void 0===o)throw"bad rs block @ typeNumber:"+e+"/errorCorrectionLevel:"+n;for(var i=o.length/3,a=[],u=0;u<i;u+=1)for(var f=o[3*u+0],c=o[3*u+1],l=o[3*u+2],h=0;h<f;h+=1)a.push(r(c,l));return a},e}(),b=function(){var t=[],r=0,e={getBuffer:function(){return t},getAt:function(r){var e=Math.floor(r/8);return 1==(t[e]>>>7-r%8&1)},put:function(t,r){for(var n=0;n<r;n+=1)e.putBit(1==(t>>>r-n-1&1))},getLengthInBits:function(){return r},putBit:function(e){var n=Math.floor(r/8);t.length<=n&&t.push(0),e&&(t[n]|=128>>>r%8),r+=1}};return e},M=function(t){var r=a,e=t,n={getMode:function(){return r},getLength:function(t){return e.length},write:function(t){for(var r=e,n=0;n+2<r.length;)t.put(o(r.substring(n,n+3)),10),n+=3;n<r.length&&(r.length-n==1?t.put(o(r.substring(n,n+1)),4):r.length-n==2&&t.put(o(r.substring(n,n+2)),7))}},o=function(t){for(var r=0,e=0;e<t.length;e+=1)r=10*r+i(t.charAt(e));return r},i=function(t){if("0"<=t&&t<="9")return t.charCodeAt(0)-"0".charCodeAt(0);throw"illegal char :"+t};return n},x=function(t){var r=u,e=t,n={getMode:function(){return r},getLength:function(t){return e.length},write:function(t){for(var r=e,n=0;n+1<r.length;)t.put(45*o(r.charAt(n))+o(r.charAt(n+1)),11),n+=2;n<r.length&&t.put(o(r.charAt(n)),6)}},o=function(t){if("0"<=t&&t<="9")return t.charCodeAt(0)-"0".charCodeAt(0);if("A"<=t&&t<="Z")return t.charCodeAt(0)-"A".charCodeAt(0)+10;switch(t){case" ":return 36;case"$":return 37;case"%":return 38;case"*":return 39;case"+":return 40;case"-":return 41;case".":return 42;case"/":return 43;case":":return 44;default:throw"illegal char :"+t}};return n},m=function(r){var e=f,n=t.stringToBytes(r),o={getMode:function(){return e},getLength:function(t){return n.length},write:function(t){for(var r=0;r<n.length;r+=1)t.put(n[r],8)}};return o},L=function(r){var e=c,n=t.stringToBytesFuncs.SJIS;if(!n)throw"sjis not supported.";!function(){var t=n("友");if(2!=t.length||38726!=(t[0]<<8|t[1]))throw"sjis not supported."}();var o=n(r),i={getMode:function(){return e},getLength:function(t){return~~(o.length/2)},write:function(t){for(var r=o,e=0;e+1<r.length;){var n=(255&r[e])<<8|255&r[e+1];if(33088<=n&&n<=40956)n-=33088;else{if(!(57408<=n&&n<=60351))throw"illegal char at "+(e+1)+"/"+n;n-=49472}n=192*(n>>>8&255)+(255&n),t.put(n,13),e+=2}if(e<r.length)throw"illegal char at "+(e+1)}};return i},D=function(){var t=[],r={writeByte:function(r){t.push(255&r)},writeShort:function(t){r.writeByte(t),r.writeByte(t>>>8)},writeBytes:function(t,e,n){e=e||0,n=n||t.length;for(var o=0;o<n;o+=1)r.writeByte(t[o+e])},writeString:function(t){for(var e=0;e<t.length;e+=1)r.writeByte(t.charCodeAt(e))},toByteArray:function(){return t},toString:function(){var r="";r+="[";for(var e=0;e<t.length;e+=1)e>0&&(r+=","),r+=t[e];return r+="]"}};return r},S=function(t){var r=t,e=0,n=0,o=0,i={read:function(){for(;o<8;){if(e>=r.length){if(0==o)return-1;throw"unexpected end of file./"+o}var t=r.charAt(e);if(e+=1,"="==t)return o=0,-1;t.match(/^\s$/)||(n=n<<6|a(t.charCodeAt(0)),o+=6)}var i=n>>>o-8&255;return o-=8,i}},a=function(t){if(65<=t&&t<=90)return t-65;if(97<=t&&t<=122)return t-97+26;if(48<=t&&t<=57)return t-48+52;if(43==t)return 62;if(47==t)return 63;throw"c:"+t};return i},I=function(t,r,e){for(var n=function(t,r){var e=t,n=r,o=new Array(t*r),i={setPixel:function(t,r,n){o[r*e+t]=n},write:function(t){t.writeString("GIF87a"),t.writeShort(e),t.writeShort(n),t.writeByte(128),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(0),t.writeByte(255),t.writeByte(255),t.writeByte(255),t.writeString(","),t.writeShort(0),t.writeShort(0),t.writeShort(e),t.writeShort(n),t.writeByte(0);var r=a(2);t.writeByte(2);for(var o=0;r.length-o>255;)t.writeByte(255),t.writeBytes(r,o,255),o+=255;t.writeByte(r.length-o),t.writeBytes(r,o,r.length-o),t.writeByte(0),t.writeString(";")}},a=function(t){for(var r=1<<t,e=1+(1<<t),n=t+1,i=u(),a=0;a<r;a+=1)i.add(String.fromCharCode(a));i.add(String.fromCharCode(r)),i.add(String.fromCharCode(e));var f,c,g,l=D(),h=(f=l,c=0,g=0,{write:function(t,r){if(t>>>r!=0)throw"length over";for(;c+r>=8;)f.writeByte(255&(t<<c|g)),r-=8-c,t>>>=8-c,g=0,c=0;g|=t<<c,c+=r},flush:function(){c>0&&f.writeByte(g)}});h.write(r,n);var s=0,v=String.fromCharCode(o[s]);for(s+=1;s<o.length;){var d=String.fromCharCode(o[s]);s+=1,i.contains(v+d)?v+=d:(h.write(i.indexOf(v),n),i.size()<4095&&(i.size()==1<<n&&(n+=1),i.add(v+d)),v=d)}return h.write(i.indexOf(v),n),h.write(e,n),h.flush(),l.toByteArray()},u=function(){var t={},r=0,e={add:function(n){if(e.contains(n))throw"dup key:"+n;t[n]=r,r+=1},size:function(){return r},indexOf:function(r){return t[r]},contains:function(r){return void 0!==t[r]}};return e};return i}(t,r),o=0;o<r;o+=1)for(var i=0;i<t;i+=1)n.setPixel(i,o,e(i,o));var a=D();n.write(a);for(var u=function(){var t=0,r=0,e=0,n="",o={},i=function(t){n+=String.fromCharCode(a(63&t))},a=function(t){if(t<0);else{if(t<26)return 65+t;if(t<52)return t-26+97;if(t<62)return t-52+48;if(62==t)return 43;if(63==t)return 47}throw"n:"+t};return o.writeByte=function(n){for(t=t<<8|255&n,r+=8,e+=1;r>=6;)i(t>>>r-6),r-=6},o.flush=function(){if(r>0&&(i(t<<6-r),t=0,r=0),e%3!=0)for(var o=3-e%3,a=0;a<o;a+=1)n+="="},o.toString=function(){return n},o}(),f=a.toByteArray(),c=0;c<f.length;c+=1)u.writeByte(f[c]);return u.flush(),"data:image/gif;base64,"+u};return t}();qrcode.stringToBytesFuncs["UTF-8"]=function(t){return function(t){for(var r=[],e=0;e<t.length;e++){var n=t.charCodeAt(e);n<128?r.push(n):n<2048?r.push(192|n>>6,128|63&n):n<55296||n>=57344?r.push(224|n>>12,128|n>>6&63,128|63&n):(e++,n=65536+((1023&n)<<10|1023&t.charCodeAt(e)),r.push(240|n>>18,128|n>>12&63,128|n>>6&63,128|63&n))}return r}(t)},function(t){"function"==typeof define&&define.amd?define([],t):"object"==typeof exports&&(module.exports=t())}((function(){return qrcode}));;return module.exports;})();
function renderQR(url, el){
  el.innerHTML = '';
  try { var qr = qrcode(0, 'M'); qr.addData(url); qr.make();
        el.innerHTML = qr.createSvgTag({cellSize: 8, margin: 2}); }
  catch (e) { el.textContent = url; }
}
