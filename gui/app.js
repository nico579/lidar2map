
// ── État ─────────────────────────────────────────────────────────────────────
let fusionFiles = [];
let fusionSel = -1;
let polling = null;
let _initialized = false;

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
    // Projet
    "sec.projet":"Projet", "f.name":"Nom *", "f.outdir":"Dossier sortie",
    "loading":"Chargement...", "apikey":"Clé API :",
    "tip.provider":"Source LiDAR (par pays). L'onglet raster s'adapte au provider (IGN pour FR, USGS Imagery pour US) ; l'onglet IGN Vecteur reste FR uniquement.",
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
    "sec.projet":"Project", "f.name":"Name *", "f.outdir":"Output folder",
    "loading":"Loading...", "apikey":"API key:",
    "tip.provider":"LiDAR source (per country). The raster tab adapts to the provider (IGN for FR, USGS Imagery for US); the IGN Vector tab stays FR-only.",
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
}
function setLang(code, persist){
  _lang = (code === 'en') ? 'en' : 'fr';
  applyI18n();
  // applyI18n a réécrit le header couche depuis sa clé générique : ré-applique
  // la variante conscient-du-pays (IGN vs USGS Imagery) dans la nouvelle langue.
  const _prov = document.getElementById('f-provider');
  if (_prov && _prov.dataset.country) applyProviderCountry(_prov.dataset.country);
  if (persist && window.pywebview && pywebview.api && pywebview.api.set_lang) {
    pywebview.api.set_lang(_lang).catch(e => console.error('set_lang error:', e));
  }
}

// ── Panneau de log ───────────────────────────────────────────────────────────
function ajouterLigneLog(text, tag) {
  const c = document.getElementById('log-content');
  if (!c) return;
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
    if (d.lang === 'fr' || d.lang === 'en') setLang(d.lang, false);  // override manuel sauvé
    if (d.ui_zoom) applyUiZoom(d.ui_zoom, false);   // zoom UI sauvé
    // buildCouches AVANT buildProviders : ce dernier appelle applyProviderCountry
    // qui filtre le dropdown des couches → il doit déjà être peuplé.
    buildCouches(d.couches);
    buildProviders(d.providers || [], d.active_provider || 'fr-ign');
    buildRegions(d.regions || []);
    buildWfsCouches(d.wfs);
    buildOsmTags(d.osm_tags);
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
  sel.innerHTML = providers.map(p =>
    `<option value="${p.code}" data-country="${p.country}" data-apikey-requise="${p.apikey_requise?1:0}">${p.name}</option>`
  ).join('');
  sel.value = activeCode;
  const opt = sel.options[sel.selectedIndex];
  const country = (opt && opt.dataset.country) || 'fr';
  sel.dataset.country = country;
  applyProviderCountry(country);
  applyProviderApiKey(opt);
  sel.addEventListener('change', () => {
    const o = sel.options[sel.selectedIndex];
    const c = (o && o.dataset.country) || 'fr';
    sel.dataset.country = c;
    applyProviderCountry(c);
    applyProviderApiKey(o);
  });
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
    const zone = e.dep  ? `Dep ${e.dep}`  :
                 e.ville ? e.ville         :
                 e.bbox  ? 'BBox'          :
                 e.gps   ? 'GPS'           : '';
    const st = e.statut || 'ok';  // entrées pré-v2 : pas de statut → 'ok' implicite
    const [sym, col] = BADGES[st] || ['', 'var(--dim)'];
    return `<div style="border:1px solid var(--bd);border-radius:4px;padding:8px;
                        margin-bottom:6px;cursor:pointer;font-size:12px"
                 onclick="rappelHistorique(${i})">
      <div style="display:flex;justify-content:space-between">
        <strong><span style="color:${col}">${sym}</span> ${LABELS[e.type]||e.type} — ${e.nom||'?'}</strong>
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
const OMB_DEFS = {
  multi: {label:'multi',  fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  slope: {label:'slope',  fields:{}},
  '315': {label:'315°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '045': {label:'045°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '135': {label:'135°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  '225': {label:'225°',   fields:{elevation:{lbl:'☀ élévation (°)', def:25,  min:5,   max:60,  step:1}}},
  svf:   {label:'SVF',    fields:{conv :{lbl:'type',         def:'flux', opts:['flux','rvt']},
                                  dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                  gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1},
                                  sweep:{lbl:'sweep-horizon', def:1, bool:true}}},
  opos:  {label:'O+ openness', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                       gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1}}},
  oneg:  {label:'O− openness', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                       gamma:{lbl:'omb.gamma.mirror', def:2.0, min:0.3, max:3.0, step:0.1}}},
  lrm:   {label:'LRM',    fields:{sigma:{lbl:'σ (m)', def:'', min:1, max:100, step:0.5, opt:true}}},
  rrim:  {label:'RRIM',   fields:{sigma:{lbl:'σ (m)', def:'', min:1, max:100, step:0.5, opt:true}}},
  vat:   {label:'VAT (composite)', fields:{dist :{lbl:'distance (m)', def:20,  min:10,  max:200, step:5},
                                           gamma:{lbl:'omb.gamma', def:2.0, min:0.3, max:3.0, step:0.1}}},
};
let ombInstances = [{type:'multi', params:{elevation:25}}];   // défaut = multi

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
      if (f.opt) inp.placeholder = 'auto';
      inp.onchange = () => {
        const v = inp.value;
        if (v === '') delete inst.params[k];
        else inst.params[k] = parseFloat(v);
        ombRender(i);
      };
    }
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
// Rendu initial (défaut multi) — re-rendu par la restauration de cfg ensuite.
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
  if (p) document.getElementById(fieldId).value = p;
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
  const valid = all.filter(f => f.endsWith('.geojson') || f.endsWith('.gz'));
  const invalid = all.filter(f => !f.endsWith('.geojson') && !f.endsWith('.gz'));
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

async function lancer() {
  const nom = document.getElementById('f-nom').value.trim();
  if (!nom) { alert(t('req.name')); return; }
  const cfg = getConfig();
  if (cfg.type === 'decoupe' && !cfg.source_decoupe) {
    alert(t('req.source'));
    return;
  }
  // Valider que la zone géographique est renseignée (sauf Fusion et Découpage raster)
  if (cfg.type !== 'fusion' && cfg.type !== 'decoupe') {
    const zoneOk = (cfg.mode === 'ville'  && cfg.ville)  ||
                   (cfg.mode === 'gps'    && cfg.gps)    ||
                   (cfg.mode === 'bbox'   && cfg.bbox)   ||
                   (cfg.mode === 'dep'    && cfg.dep)    ||
                   (cfg.mode === 'region' && cfg.region) ||
                    false;
    if (!zoneOk) {
      const labels = {ville:t('mode.ville'), gps:t('mode.gps'), bbox:t('mode.bbox'), dep:t('mode.dep'), region:t('mode.region')};
      alert(tf('req.field', {f: labels[cfg.mode] || cfg.mode}));
      return;
    }
  }
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').disabled = false;
  document.getElementById('footer-status').textContent = t('running');
  setFormLocked(true);

  // Vider le panneau de log et préparer la barre de progression
  viderLog();
  document.getElementById('log-status').textContent = t('running');
  setLogProgress(0, '');

  const res = await pywebview.api.launch(cfg);
  if (res && res.error) { alert(res.error); btnReset(); return; }

  // Afficher la commande lancée dans le footer
  // (elle est aussi mise dans la log queue côté Python, ne pas dupliquer ici)
  document.getElementById('footer-status').textContent = '▶ ' + (res.cmd || '').split(' ').slice(-3).join(' ') + '…';

  polling = setInterval(async () => {
    const r = await pywebview.api.poll_log();
    if (r.items) {
      r.items.forEach(item => {
        // Lignes de texte → panneau de log avec colorisation par tag
        if (item.line !== undefined) {
          ajouterLigneLog(item.line, item.tag || 'ok');
        }
        // Pourcentage (carriage return du child) → barre de progression + footer
        if (item.pct !== undefined && item.pct >= 0) {
          setLogProgress(item.pct, '');
          document.getElementById('footer-status').textContent =
            item.pct + '%  ' + (item.label || '').substring(0, 80);
        }
        // Label seul (action en cours sans pct) → footer
        if (item.pct === -1 && item.label) {
          document.getElementById('footer-status').textContent =
            item.label.substring(0, 100);
        }
      });
    }
    if (r.done) {
      clearInterval(polling); polling = null;
      document.getElementById('footer-status').textContent =
        r.code === 0 ? t('done') : tf('err.code', {c: r.code});
      document.getElementById('log-status').textContent =
        r.code === 0 ? t('done') : tf('err.code', {c: r.code});
      setLogProgress(100, r.code === 0 ? 'ok' : 'err');
      // Récap d'erreur en fin de run via API dédiée (plus fiable que
      // le passage par poll_log : pywebview/WebView2 peut perdre des
      // clés non-standard dans les dicts complexes sérialisés).
      if (r.code !== 0) {
        // Erreur → ouvrir automatiquement le panneau de log s'il est caché,
        // sinon le message "voir le panneau" est inutile.
        const p = document.getElementById('panneau-log');
        if (p && p.classList.contains('hidden')) {
          toggleLogPanel();
        }
        try {
          const err = await pywebview.api.get_last_error();
          if (err && err.msg) {
            alert(tf('fail.detail', {c: err.retcode, msg: err.msg}));
          } else {
            // Fallback générique si _modal_error_msg n'a pas été rempli
            alert(tf('fail.generic', {c: r.code}));
          }
        } catch (e) {
          console.error('get_last_error:', e);
          alert(tf('fail.generic', {c: r.code}));
        }
      }
      if (r.code === 0) {
        // Recharger l'historique via appel dédié (plus fiable que poll_log)
        pywebview.api.get_historique().then(hist => {
          if (hist && hist.length) {
            buildHistorique(hist);
            const last = hist[0];
            if (last && last.params) loadConfig(last.params);
          }
        }).catch(e => console.error('get_historique error:', e));
        if (r.result_dir) pywebview.api.open_folder(r.result_dir);
      }
      btnReset();
    }
  }, 250);
}

async function arreter() {
  await pywebview.api.stop();
  if (polling) { clearInterval(polling); polling = null; }
  document.getElementById('footer-status').textContent = t('stopped');
  btnReset();
}

function btnReset() {
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  setFormLocked(false);
}
  // ── Zoom Ctrl+molette ────────────────────────────────────────────────
  // Fonctionne sur tous les OS et clients VNC (RealVNC Windows → macOS VM).
  // Ctrl+molette haut = zoom in, Ctrl+molette bas = zoom out.
  // Pinch-to-zoom trackpad fonctionne nativement via le navigateur embarqué.
  (function() {
    let _zoomLevel = 1.0;
    const _ZOOM_STEP = 0.1;
    const _ZOOM_MIN  = 0.5;
    const _ZOOM_MAX  = 2.5;
    document.addEventListener('wheel', function(e) {
      if (!e.ctrlKey) return;
      e.preventDefault();
      _zoomLevel += e.deltaY < 0 ? _ZOOM_STEP : -_ZOOM_STEP;
      _zoomLevel  = Math.min(_ZOOM_MAX, Math.max(_ZOOM_MIN, _zoomLevel));
      document.body.style.zoom = _zoomLevel;
    }, { passive: false });
    // Ctrl+0 pour réinitialiser le zoom
    document.addEventListener('keydown', function(e) {
      if (e.ctrlKey && (e.key === '0' || e.key === 'NumPad0')) {
        e.preventDefault();
        _zoomLevel = 1.0;
        document.body.style.zoom = 1.0;
      }
    });
  })();
