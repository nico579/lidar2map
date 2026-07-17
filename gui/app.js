
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
    "tip.projlist":"Projets existants (remplit le champ Nom)",
    "proj.pick":"↻ projet existant…",
    // Projet
    "sec.projet":"Projet", "f.name":"Nom *", "f.outdir":"Dossier sortie",
    "loading":"Chargement...", "apikey":"Clé API :",
    "tip.provider":"Source LiDAR (par pays). L'onglet raster s'adapte au provider (IGN pour FR, USGS Imagery pour US) ; l'onglet IGN Vecteur reste FR uniquement.",
    "f.dfm":"Mode LAZ — structures debout (nuage classé, expérimental)",
    "f.src.mnt":"Source : MNT (raster)", "f.src.laz":"Source : nuage LAZ",
    "f.dlcap":"↓ %d max en parallèle (gros nuages LAZ)",
    "f.dfmh":"hauteur (m)", "f.dfmc":"classes LAS",
    "f.dfmg":"socle", "f.dfmg.classes":"classes IGN", "f.dfmg.csf":"tissu CSF (~3 min/dalle)",
    "f.dfmt":"seuil (m)", "f.dfmr":"maille (m)", "f.dfmrg":"terrain",
    "f.dfmrg.1":"pentu (1)", "f.dfmrg.2":"relief doux (2)", "f.dfmrg.3":"plat (3)",
    "tip.dfm":"Reconstruit le modèle depuis le nuage de points classé (LAZ ~205 Mo/km²) : peut réintroduire les retours compatibles avec des ruines/murs debout que le MNT efface (candidats, pas une classification : le maquis revient aussi — mouchetis vs lignes continues). Socle « classes IGN » : 2/9/66 = terrain, les autres classes sont réinjectées dans les trous du sol, filtrées par la tranche de hauteur. Socle « tissu CSF » : un tissu simulé (Zhang 2016) sépare sol et sursol sans les classes ; fond plus propre, ~3 min/dalle, réglages propres seuil/maille/terrain (hauteur/classes ignorés). Zone petite conseillée.",
    // Zone
    "sec.zone":"Zone géographique",
    "mode.ville":"Ville", "mode.gps":"GPS", "mode.bbox":"BBox", "mode.dep":"Department", "mode.region":"Région",
    "z.ville":"Ville", "z.rayonkm":"Rayon km", "z.gps":"GPS lat,lon", "z.bbox":"BBox W,S,E,N",
    "z.deps":"Department(s)",
    // Type de traitement
    "sec.type":"Type de traitement de carte",
    "t.lidar":"LiDAR MNT", "t.vecteur":"IGN Vectoriel", "t.osm":"OSM Vectoriel",
    "t.fusion":"Fusion Vectoriel", "t.decoupe":"Découpage raster",
    // Étapes communes
    "split0":"0 — Découpage à priori (grandes zones)",
    "grid":"Grille :", "rows":"lignes", "orradius":"ou rayon", "rows_orradius":"lignes  ou rayon",
    "clean":"Nettoyage intermédiaires",
    "minfree":"min disque", "tip.minfree":"Arrêt propre avant un chunk si disque libre < seuil (0 = désactivé)",
    "split.hint":"1×1 = pas de découpage — reprise automatique via manifeste.json",
    "dl":"1 — Télécharger", "dl.lidar":"1 — Télécharger les dalles LiDAR HD IGN",
    "ovr":"Écraser le fichier résultat", "ovr.short":"Écraser",
    "workers":"Workers :", "compress":"Compresser", "extcache":"Cache externe :",
    "tiles2":"2 — Calculer les tuiles", "tiles3":"3 — Calculer les tuiles",
    "omb2":"2 — Calculer les ombrages archéologiques",
    "zoom":"Zoom :", "imgfmt":"Format de l'image :", "jpegq":"Qualité Jpeg :", "filefmt":"Format du fichier :",
    // SVF
    "tip.svf":"Sky-View Factor — ouverture de l'hémisphère céleste. Options à droite.",
    "tip.elev":"Angle solaire des hillshades directionnels. 25° = archéo (micro-relief) ; 45° = usage général.",
    // IGN Raster
    "sec.couche":"Couche IGN", "sec.couche.us":"Couche USGS Imagery", "couche":"Couche :",
    // OSM / Vecteur / Fusion
    "pbfpar":"(parallélisme téléchargement PBF)", "max4":"(max 4 recommandé)",
    "geojson.raw":".geojson (non compressed)",
    "gen.map":"2 — Générer carte Mapsforge (.map)",
    "simplif":"Simplification vecteur",
    "simplif.hint1":"m  (vide = auto : 3 m local → 40 m région)", "simplif.hint2":"m  (vide = auto)",
    "sec.fusion":"Fichiers GeoJSON à fusionner",
    "add":"＋ Ajouter…", "remove":"－ Supprimer", "clear":"✕ Vider",
    "extsel":"Sélection étendue (Shift/Ctrl)", "fmt":"Format :",
    // Découpage raster
    "sec.src":"Fichier source", "sec.split":"Découpage",
    // Placeholders
    "ph.optopo":"clé OpenTopography", "ph.ignpro":"clé pro IGN",
    "ph.cacheauto":"(cache auto)", "ph.mbtilespath":"chemin vers le fichier .mbtiles",
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
    "tip.projlist":"Existing projects (fills the Name field)",
    "proj.pick":"↻ existing project…",
    "sec.projet":"Project", "f.name":"Name *", "f.outdir":"Output folder",
    "loading":"Loading...", "apikey":"API key:",
    "tip.provider":"LiDAR source (per country). The raster tab adapts to the provider (IGN for FR, USGS Imagery for US); the IGN Vector tab stays FR-only.",
    "f.dfm":"LAZ mode — standing structures (classified cloud, experimental)",
    "f.src.mnt":"Source: DTM (raster)", "f.src.laz":"Source: LAZ point cloud",
    "f.dlcap":"↓ %d max parallel (large LAZ clouds)",
    "f.dfmh":"height (m)", "f.dfmc":"LAS classes",
    "f.dfmg":"ground base", "f.dfmg.classes":"IGN classes", "f.dfmg.csf":"CSF cloth (~3 min/tile)",
    "f.dfmt":"threshold (m)", "f.dfmr":"cloth cell (m)", "f.dfmrg":"terrain",
    "f.dfmrg.1":"steep (1)", "f.dfmrg.2":"gentle relief (2)", "f.dfmrg.3":"flat (3)",
    "tip.dfm":"Rebuilds the model from the classified point cloud (LAZ ~205 MB/km²): can re-introduce returns compatible with standing ruins/walls that the DTM erases (candidates, not a classifier — scrub comes back too: speckle vs continuous lines). \"IGN classes\" base: 2/9/66 = terrain, other classes are re-injected into ground gaps, filtered by the height band. \"CSF cloth\" base: a simulated cloth (Zhang 2016) splits ground from off-ground without the classes; cleaner background, ~3 min/tile, its own threshold/cloth-cell/terrain settings (height/classes ignored). Keep the area small.",
    "sec.zone":"Geographic area",
    "mode.ville":"City", "mode.gps":"GPS", "mode.bbox":"BBox", "mode.dep":"Department", "mode.region":"Region",
    "z.ville":"City", "z.rayonkm":"Radius km", "z.gps":"GPS lat,lon", "z.bbox":"BBox W,S,E,N",
    "z.deps":"Department(s)",
    "sec.type":"Map processing type",
    "t.lidar":"LiDAR DEM", "t.vecteur":"IGN Vector", "t.osm":"OSM Vector",
    "t.fusion":"Vector merge", "t.decoupe":"Raster split",
    "split0":"0 — A priori split (large areas)",
    "grid":"Grid:", "rows":"rows", "orradius":"or radius", "rows_orradius":"rows  or radius",
    "clean":"Clean intermediates",
    "minfree":"min free disk", "tip.minfree":"Stop cleanly before a chunk if free disk < threshold (0 = off)",
    "split.hint":"1×1 = no split — automatic resume via manifeste.json",
    "dl":"1 — Download", "dl.lidar":"1 — Download IGN LiDAR HD tiles",
    "ovr":"Overwrite output file", "ovr.short":"Overwrite",
    "workers":"Workers:", "compress":"Compress", "extcache":"External cache:",
    "tiles2":"2 — Compute tiles", "tiles3":"3 — Compute tiles",
    "omb2":"2 — Compute archaeological shadings",
    "zoom":"Zoom:", "imgfmt":"Image format:", "jpegq":"Jpeg quality:", "filefmt":"File format:",
    "tip.svf":"Sky-View Factor — openness of the celestial hemisphere. Options on the right.",
    "tip.elev":"Sun angle of the directional hillshades. 25° = archaeology (micro-relief); 45° = general use.",
    "sec.couche":"IGN layer", "sec.couche.us":"USGS Imagery layer", "couche":"Layer:",
    "pbfpar":"(PBF download parallelism)", "max4":"(max 4 recommended)",
    "geojson.raw":".geojson (uncompressed)",
    "gen.map":"2 — Generate Mapsforge map (.map)",
    "simplif":"Vector simplification",
    "simplif.hint1":"m  (empty = auto: 3 m local → 40 m region)", "simplif.hint2":"m  (empty = auto)",
    "sec.fusion":"GeoJSON files to merge",
    "add":"＋ Add…", "remove":"－ Remove", "clear":"✕ Clear",
    "extsel":"Extended selection (Shift/Ctrl)", "fmt":"Format:",
    "sec.src":"Source file", "sec.split":"Split",
    "ph.optopo":"OpenTopography key", "ph.ignpro":"IGN pro key",
    "ph.cacheauto":"(auto cache)", "ph.mbtilespath":"path to .mbtiles file",
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
  if (typeof updateDfmUI === 'function') updateDfmUI();
}
function setLang(code, persist){
  _lang = (code === 'en') ? 'en' : 'fr';
  applyI18n();
  // applyI18n a réécrit le header couche depuis sa clé générique : ré-applique
  // la variante conscient-du-pays (IGN vs USGS Imagery) dans la nouvelle langue.
  const _prov = document.getElementById('f-provider');
  if (_prov && _prov.dataset.country) applyProviderCountry(_prov.dataset.country);
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
    buildProviders(d.providers || [], d.active_provider || 'fr-ign');
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
  _allProviders = providers.slice();     // liste complète (restaurée si on décoche LAZ)
  sel.innerHTML = providers.map(_providerOption).join('');
  // Capacité "mode DFM" par provider (jumeau *_dfm côté Python). Les DÉFAUTS
  // des réglages viennent du module Python (source de vérité unique).
  _dfmByCode = {};
  providers.forEach(p => { if (p.dfm) _dfmByCode[p.code] = p.dfm; });
  sel.value = activeCode;
  const opt = sel.options[sel.selectedIndex];
  const country = (opt && opt.dataset.country) || 'fr';
  sel.dataset.country = country;
  if (opt && opt.dataset.res) _resolutionM = parseFloat(opt.dataset.res);   // défaut σ selon provider
  applyProviderCountry(country);
  applyProviderApiKey(opt);
  applyProviderDfm(sel.value);
  sel.addEventListener('change', () => {
    _applyProviderSelection();
    ombShowParams();   // rafraîchit le champ σ ouvert avec le nouveau défaut
  });
}

// Un <option> à partir d'un descriptor provider (factorisé : buildProviders +
// onLazToggle produisent la même chose). Résolution apposée seulement si absente
// du nom officiel (ex. "DEM 5m" ne la duplique pas).
function _providerOption(p) {
  const hasRes = /\d[\d.,]*\s?(m|cm)\b/i.test(p.name);
  const label = hasRes ? p.name : `${p.name} (${fmtRes(p.resolution_m ?? 0.5)})`;
  return `<option value="${p.code}" data-country="${p.country}" data-apikey-requise="${p.apikey_requise?1:0}" data-res="${p.resolution_m ?? 0.5}">${label}</option>`;
}

// Effets de bord d'un changement de provider (pays, résolution σ, clé API,
// capacité DFM). Partagé par le listener 'change' et onLazToggle.
function _applyProviderSelection() {
  const sel = document.getElementById('f-provider');
  const o = sel.options[sel.selectedIndex];
  const c = (o && o.dataset.country) || 'fr';
  sel.dataset.country = c;
  if (o && o.dataset.res) _resolutionM = parseFloat(o.dataset.res);
  applyProviderCountry(c);
  applyProviderApiKey(o);
  applyProviderDfm(sel.value);
}

// Cocher "Mode LAZ" RÉDUIT le dropdown aux providers DFM-capables (ceux qui ont
// un jumeau *_dfm) : on ne voit que les sources dont on peut tirer les
// structures debout depuis le nuage de points. Décocher restaure la liste
// complète, en gardant le provider courant s'il y figure.
let _allProviders = [];
function onLazToggle() {
  const sel = document.getElementById('f-provider');
  const cb  = document.getElementById('f-dfm');
  if (!sel || !cb) return;
  const keep = sel.value;
  const list = cb.checked ? _allProviders.filter(p => p.dfm) : _allProviders;
  sel.innerHTML = list.map(_providerOption).join('');
  sel.value = list.some(p => p.code === keep) ? keep
            : ((list[0] && list[0].code) || keep);
  _applyProviderSelection();
  ombShowParams();
  updateDfmUI();
}

// Capacité DFM du provider actif : affiche la ligne "mode DFM" et préremplit
// les réglages avec les défauts du jumeau Python (hmin/hmax/classes).
let _dfmByCode = {};
function applyProviderDfm(code) {
  const row = document.getElementById('dfm-row');
  if (!row) return;
  const cap = _dfmByCode[code];
  row.style.display = cap ? 'flex' : 'none';
  if (!cap) {
    const cb = document.getElementById('f-dfm');
    if (cb) cb.checked = false;
    updateDfmUI();
    return;
  }
  const hmin = document.getElementById('f-dfm-hmin');
  const hmax = document.getElementById('f-dfm-hmax');
  const cls  = document.getElementById('f-dfm-classes');
  const grd  = document.getElementById('f-dfm-ground');
  const cthr = document.getElementById('f-dfm-csf-threshold');
  const cres = document.getElementById('f-dfm-csf-resolution');
  const crig = document.getElementById('f-dfm-csf-rigidness');
  if (hmin) { hmin.value = cap.hmin; hmin.dataset.def = cap.hmin; }
  if (hmax) { hmax.value = cap.hmax; hmax.dataset.def = cap.hmax; }
  if (cls)  { cls.value  = cap.classes; cls.dataset.def = cap.classes; }
  if (grd)  { grd.value  = cap.ground || 'classes'; grd.dataset.def = cap.ground || 'classes'; }
  if (cthr) { cthr.value = cap.csf_threshold ?? 0.5;  cthr.dataset.def = cthr.value; }
  if (cres) { cres.value = cap.csf_resolution ?? 0.5; cres.dataset.def = cres.value; }
  if (crig) { crig.value = cap.csf_rigidness ?? 1;    crig.dataset.def = crig.value; }
  updateDfmUI();
}

function updateDfmUI() {
  const cb = document.getElementById('f-dfm');
  const params = document.getElementById('dfm-params');
  if (params) params.style.display = (cb && cb.checked) ? 'inline-flex' : 'none';
  // Socle CSF : le tissu ignore la tranche de hauteur et les classes → on
  // ÉCHANGE les groupes de réglages (les valeurs cachées restent posées,
  // ré-affichées si on rebascule).
  const grd = document.getElementById('f-dfm-ground');
  const csf = grd && grd.value === 'csf';
  const pc = document.getElementById('dfm-params-classes');
  const px = document.getElementById('dfm-params-csf');
  if (pc) pc.style.display = csf ? 'none' : 'inline-flex';
  if (px) px.style.display = csf ? 'inline-flex' : 'none';
  // Badge de source : cocher bascule MNT (raster) → LAZ (nuage de points).
  const laz = cb && cb.checked;
  const src = document.getElementById('dfm-source');
  if (src) {
    src.textContent = laz ? t('f.src.laz') : t('f.src.mnt');
    src.style.background = laz ? '#dcfce7' : '#e2e8f0';
    src.style.color = laz ? '#166534' : '#475569';
  }
  // Champ Workers : en mode LAZ le download est plafonné (gros nuages, sinon
  // throttle serveur). On BORNE le champ (max + valeur) à la valeur du provider
  // (source unique, pas de 3 en dur) et on la restaure à la sortie. Le tuilage/
  // ombrage d'une zone LAZ est négligeable (petites zones), donc borner le champ
  // ne coûte rien. Le cap backend (_telecharger_dalles_zone) reste en défense
  // pour les runs CLI. Une note dit le pourquoi.
  const code = document.getElementById('f-provider')?.value;
  const capN = laz && _dfmByCode[code] ? _dfmByCode[code].download_workers_max : 0;
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
  const note = document.getElementById('dfm-workers-note');
  if (note) {
    if (capN) {
      note.textContent = t('f.dlcap').replace('%d', capN);
      note.style.display = 'inline';
    } else {
      note.style.display = 'none';
    }
  }
}

function applyProviderApiKey(opt) {
  // Affiche le champ "Clé API" à côté de la dropdown provider si le provider
  // actif l'exige (data-apikey-requise="1"). Sinon caché.
  const group = document.getElementById('lidar-apikey-group');
  if (!group) return;
  const needs = opt && opt.dataset.apikeyRequise === '1';
  group.style.display = needs ? 'inline-flex' : 'none';
}

// Libellé de l'onglet raster selon le pays propriétaire des couches.
const _RASTER_TAB_LABEL = { fr: 'IGN Raster', us: 'USGS Imagery' };

function _bascullerVersLidar(inp) {
  // Si l'onglet courant devient invisible, basculer sur LiDAR.
  if (inp && inp.checked) {
    const lidarRadio = document.getElementById('t-lidar');
    if (lidarRadio) { lidarRadio.checked = true; lidarRadio.dispatchEvent(new Event('change')); }
  }
}

function filterCouchesByCountry(country) {
  // N'affiche que les couches du pays courant dans le dropdown raster.
  const sel = document.getElementById('f-couche');
  if (!sel) return false;
  let firstVisible = null;
  Array.from(sel.options).forEach(o => {
    const match = (o.dataset.pays || 'fr') === country;
    o.hidden = !match;
    o.disabled = !match;
    if (match && !firstVisible) firstVisible = o;
  });
  // Si la couche sélectionnée n'est plus du bon pays, prendre la 1re visible.
  const cur = sel.selectedOptions[0];
  if (firstVisible && (!cur || cur.hidden)) {
    sel.value = firstVisible.value;
    sel.dispatchEvent(new Event('change'));
  }
  return firstVisible !== null;   // true si le pays a au moins une couche raster
}

function applyProviderCountry(country) {
  // Cache les onglets/labels marqués data-fr-only="1" si le pays n'est pas FR.
  const elts = document.querySelectorAll('[data-fr-only="1"]');
  elts.forEach(el => {
    el.style.display = (country === 'fr') ? '' : 'none';
    // Cacher aussi le radio input associé si c'est un <label for="...">
    const forId = el.getAttribute('for');
    if (forId) {
      const inp = document.getElementById(forId);
      if (inp) {
        inp.style.display = (country === 'fr') ? '' : 'none';
        if (country !== 'fr') _bascullerVersLidar(inp);
      }
    }
  });

  // Onglet raster : conscient du pays. Visible si le provider a des couches
  // raster (FR → IGN, US → USGS Imagery), masqué sinon. Le libellé s'adapte.
  const hasRaster = filterCouchesByCountry(country);
  const lblRaster = document.getElementById('lbl-raster');
  const inpRaster = document.getElementById('t-scan');
  if (lblRaster) {
    lblRaster.style.display = hasRaster ? '' : 'none';
    if (hasRaster) lblRaster.textContent = _RASTER_TAB_LABEL[country] || 'Raster';
  }
  if (inpRaster) {
    inpRaster.style.display = hasRaster ? '' : 'none';
    if (!hasRaster) _bascullerVersLidar(inpRaster);
  }
  // Titre de la section couche : "Couche IGN" (FR) / "Couche USGS Imagery" (US),
  // dans la langue courante. Survit aux changements de langue (setLang ré-appelle).
  const hdCouche = document.getElementById('hd-couche');
  if (hdCouche && hasRaster) {
    hdCouche.textContent = t(country === 'us' ? 'sec.couche.us' : 'sec.couche');
  }
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

function buildCouches(couches) {
  const sel = document.getElementById('f-couche');
  couches.forEach(c => {
    const o = document.createElement('option');
    o.value = c.code; o.textContent = c.label;
    o.dataset.zmin = c.zoom_min; o.dataset.zmax = c.zoom_max;
    o.dataset.restreinte = c.restreinte ? '1' : '0';
    o.dataset.pays = c.pays || 'fr';
    sel.appendChild(o);
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
    }
  };
  sel.addEventListener('change', updateWarning);
  updateWarning();
}

function buildWfsCouches(wfs) {
  const c = document.getElementById('wfs-checks');
  wfs.forEach(w => {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" name="wfs" value="${w.alias}"${w.alias==='cadastre'?' checked':''}> ${w.label}`;
    c.appendChild(l);
  });
}

function buildOsmTags(tags) {
  const c = document.getElementById('osm-tag-checks');
  const defaults = new Set(['highway=*','waterway=*','boundary=administrative','natural=water']);
  tags.forEach(t => {
    const l = document.createElement('label');
    l.innerHTML = `<input type="checkbox" name="osm_tag" value="${t.tag}"${defaults.has(t.tag)?' checked':''}> ${t.label}`;
    c.appendChild(l);
  });
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
  // Pays du provider actif : pilote BAN (FR) vs Nominatim (autre)
  const psel = document.getElementById('f-provider');
  const country = (psel && psel.dataset.country) || 'fr';
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
    const cur = document.querySelector('input[name=mode]:checked')?.value || 'ville';
    ['ville','gps','bbox','dep','region'].forEach(m => {
      const z = document.getElementById('z-'+m);
      if (z) z.classList.toggle('hidden', cur !== m);
    });
  };
  document.querySelectorAll('input[name=mode]').forEach(r => {
    r.addEventListener('change', window.applyMode);
  });
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
    ['lidar','scan','osm','vecteur','fusion','decoupe'].forEach(t => {
      const sec = document.getElementById('sec-'+t);
      if (sec) sec.classList.toggle('hidden', t !== cur);
    });
    document.body.className = 'type-' + cur;
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
    ['f-tel',       'body-tel'],
    ['f-no-omb',    'body-omb'],
    ['f-mbtiles-l', 'body-mbt'],
    ['f-tel-s',     'body-tel-s'],
    ['f-tuiles-s',  'body-tuil-s'],
    ['f-tel-osm',   'body-tel-osm'],
    ['f-tuiles-osm','body-tuil-osm'],
    ['f-tel-v',     'body-tel-v'],
    ['f-tuiles-v',  'body-map-v'],
    ['f-tuiles-v',  'row-simplif-v'],
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

// ── Config ────────────────────────────────────────────────────────────────────
function getConfig() {
  const g = id => document.getElementById(id);
  const mode = document.querySelector('input[name=mode]:checked')?.value || 'ville';
  const type = document.querySelector('input[name=type]:checked')?.value || 'lidar';
  const rayonId = mode === 'gps' ? 'f-rayon-gps' : 'f-rayon';

  const cfg = {
    type, mode,
    provider: g('f-provider')?.value || 'fr-ign',
    lidar_apikey: g('f-lidar-apikey')?.value.trim(),
    // Mode DFM (structures debout) : la case + réglages ≠ défauts uniquement
    // (les défauts vivent côté Python, dataset.def posé par applyProviderDfm).
    dfm: g('f-dfm')?.checked || false,
    dfm_hmin:    (g('f-dfm-hmin')?.value    && g('f-dfm-hmin').value    !== g('f-dfm-hmin').dataset.def)    ? g('f-dfm-hmin').value    : '',
    dfm_hmax:    (g('f-dfm-hmax')?.value    && g('f-dfm-hmax').value    !== g('f-dfm-hmax').dataset.def)    ? g('f-dfm-hmax').value    : '',
    dfm_classes: (g('f-dfm-classes')?.value && g('f-dfm-classes').value !== g('f-dfm-classes').dataset.def) ? g('f-dfm-classes').value.trim() : '',
    dfm_ground:  (g('f-dfm-ground')?.value  && g('f-dfm-ground').value  !== g('f-dfm-ground').dataset.def)  ? g('f-dfm-ground').value  : '',
    dfm_csf_threshold:  (g('f-dfm-csf-threshold')?.value  && g('f-dfm-csf-threshold').value  !== g('f-dfm-csf-threshold').dataset.def)  ? g('f-dfm-csf-threshold').value  : '',
    dfm_csf_resolution: (g('f-dfm-csf-resolution')?.value && g('f-dfm-csf-resolution').value !== g('f-dfm-csf-resolution').dataset.def) ? g('f-dfm-csf-resolution').value : '',
    dfm_csf_rigidness:  (g('f-dfm-csf-rigidness')?.value  && g('f-dfm-csf-rigidness').value  !== g('f-dfm-csf-rigidness').dataset.def)  ? g('f-dfm-csf-rigidness').value  : '',
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
    dossier_dalles:g('f-dossier-dalles')?.value.trim(),
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
    osm_tags_sel:  [...document.querySelectorAll('input[name=osm_tag]:checked')].map(c=>c.value),
    ecraser_tel_osm: g('f-ecraser-tel-osm')?.checked,
    tuiles_osm:    g('f-tuiles-osm')?.checked,
    map:           g('f-map')?.checked,
    osm_geojson:     g('f-osm-geojson')?.checked,
    osm_geojson_raw: g('f-osm-geojson-raw')?.checked,
    osm_transparent: g('f-osm-transparent')?.checked,
    ecraser_tuil_osm: g('f-ecraser-tuil-osm')?.checked,
    // Vecteur
    tel_v:         g('f-tel-v')?.checked,
    wfs_couches_sel:[...document.querySelectorAll('input[name=wfs]:checked')].map(c=>c.value),
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
  if (cfg.mode) sr('mode', cfg.mode);
  if (cfg.type) sr('type', cfg.type);
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
  s('f-dossier-dalles', cfg.dossier_dalles);
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
  // FIX: était cfg.osm_tags — la clé sauvée par getConfig est osm_tags_sel
  if (cfg.osm_tags_sel) {
    const tagSet = new Set(typeof cfg.osm_tags_sel === 'string'
      ? cfg.osm_tags_sel.split(' ') : cfg.osm_tags_sel);
    document.querySelectorAll('input[name=osm_tag]').forEach(c => {
      c.checked = tagSet.has(c.value);
    });
  }

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
  if (cfg.wfs_couches_sel) {
    const wfsSet = new Set(typeof cfg.wfs_couches_sel === 'string'
      ? cfg.wfs_couches_sel.split(' ') : cfg.wfs_couches_sel);
    document.querySelectorAll('input[name=wfs]').forEach(c => {
      c.checked = wfsSet.has(c.value);
    });
  }

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
  // provider → couche → zooms dans cet ordre, après tout le reste, pour que les
  // valeurs sauvées gagnent quel que soit l'ordre d'init (démarrage vs panneau).
  if (cfg.provider) {
    const psel = document.getElementById('f-provider');
    if (psel && psel.querySelector(`option[value="${cfg.provider}"]`)) {
      psel.value = cfg.provider;
      psel.dispatchEvent(new Event('change'));   // applyProviderCountry + filtre couches
    }
  }
  // Mode DFM : restauré APRÈS le provider (le change ci-dessus repose les
  // défauts via applyProviderDfm ; on ré-applique ensuite les valeurs sauvées).
  if (cfg.dfm !== undefined) {
    const cb = document.getElementById('f-dfm');
    if (cb) cb.checked = !!cfg.dfm;
    if (cfg.dfm_hmin)    s('f-dfm-hmin',    cfg.dfm_hmin);
    if (cfg.dfm_hmax)    s('f-dfm-hmax',    cfg.dfm_hmax);
    if (cfg.dfm_classes) s('f-dfm-classes', cfg.dfm_classes);
    if (cfg.dfm_ground)  s('f-dfm-ground',  cfg.dfm_ground);
    if (cfg.dfm_csf_threshold)  s('f-dfm-csf-threshold',  cfg.dfm_csf_threshold);
    if (cfg.dfm_csf_resolution) s('f-dfm-csf-resolution', cfg.dfm_csf_resolution);
    if (cfg.dfm_csf_rigidness)  s('f-dfm-csf-rigidness',  cfg.dfm_csf_rigidness);
    if (typeof updateDfmUI === 'function') updateDfmUI();
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
async function pickDir(fieldId) {
  const p = await pywebview.api.pick_dir();
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
