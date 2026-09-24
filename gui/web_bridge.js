// Shim pour le mode navigateur (--serve-gui) : remplace l'objet
// pywebview.api (avant, injecté par pywebview - retiré) par des appels
// fetch() vers le serveur HTTP. Chargé UNIQUEMENT par la page servie via
// --serve-gui (voir _serve_web.py, send_index) ; jamais référencé par
// index.html sur disque.
//
// app.js appelle pywebview.api.* sans savoir que c'est ce shim qui répond
// (waitForApi() y détecte juste que get_init_data est une fonction).
// pick_dir/pick_file n'y figurent plus : remplacés par browseOuvrir()
// (app.js), qui appelle /api/browse-dir directement, sans passer par cet
// objet (aucun équivalent pywebview à imiter pour ce nouveau mécanisme).
function _post(route, payload) {
  return fetch(route, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  }).then(r => r.json());
}

window.pywebview = window.pywebview || {
  api: {
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
  },
};
