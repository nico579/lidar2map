// Pont entre l'interface (app.js) et le serveur HTTP de lidar2map
// (_serve_web.py) : chaque méthode de window.api appelle une route /api/*
// et rend une promesse. index.html le charge avant app.js.
//
// window.api remplace l'objet qu'injectait pywebview (retiré en 1.49). Pas
// d'alias sous l'ancien nom : ce fichier et app.js sont toujours livrés
// ensemble et servis sans en-tête de cache.
// pick_dir/pick_file n'y figurent plus : remplacés par browseOuvrir()
// (app.js), qui appelle /api/browse-dir directement.
function _post(route, payload) {
  return fetch(route, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  }).then(r => r.json());
}

window.api = {
  get_init_data: () => fetch('/api/init').then(r => r.json()),
  get_historique: () => fetch('/api/historique').then(r => r.json()),
  get_help: () => fetch('/api/help').then(r => r.json()),
  get_last_error: () => fetch('/api/last-error').then(r => r.json()),
  check_update: () => fetch('/api/check-update').then(r => r.json()),
  poll_log: () => fetch('/api/poll-log').then(r => r.json()),

  get_usage: (cfg) => {
    const params = new URLSearchParams();
    if (cfg && cfg.cache_dir) params.set('cache_dir', cfg.cache_dir);
    if (cfg && cfg.production_dir) params.set('production_dir', cfg.production_dir);
    const qs = params.toString();
    return fetch('/api/usage' + (qs ? '?' + qs : '')).then(r => r.json());
  },
  get_projets: (dossier) => {
    const qs = dossier ? '?dossier=' + encodeURIComponent(dossier) : '';
    return fetch('/api/projets' + qs).then(r => r.json());
  },
  autocomplete_ville: (prefix, country) => {
    const params = new URLSearchParams({ prefix: prefix || '', country: country || 'fr' });
    return fetch('/api/autocomplete-ville?' + params.toString()).then(r => r.json());
  },

  launch: (cfg) => _post('/api/launch', cfg),
  stop: (stopRemote, purgeRemote) => _post('/api/stop', {
    stop_remote: !!stopRemote, purge_remote: !!purgeRemote,
  }),
  clear_historique: () => _post('/api/clear-historique'),
  set_lang: (code) => _post('/api/set-lang', { code }),
  set_ui_zoom: (z) => _post('/api/set-ui-zoom', { z }),
  set_trusted_host: (host) => _post('/api/set-trusted-host', { host }),
  set_autostart: (actif) => _post('/api/set-autostart', { actif }),
  start_share: (cfg) => _post('/api/start-share', cfg),
  stop_share: () => _post('/api/stop-share'),
  open_folder: (path) => _post('/api/open-folder', { path }),
  new_instance: () => _post('/api/new-instance'),

  // Pas de route serveur : le navigateur ouvre déjà des URL nativement.
  open_url: (url) => { window.open(url, '_blank'); },
};
