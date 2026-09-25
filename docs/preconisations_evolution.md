# Préconisations d'évolution

*Document de travail pour les mainteneurs · [Index de la documentation](README.fr.md)*

Rédigé le 25 septembre 2026 sur `main` à `1ba929c`, juste après la fusion de la
PR #4. Dernière release publiée : `v1.50.4`. Chaque constat a été revérifié
dans le code à ce commit. Les numéros de ligne sont indicatifs : ils dériveront,
les noms de fonctions font foi.

## Mode d'emploi pour la session qui reprend ce document

1. Choisir un lot dans la section [Lots proposés](#lots-proposés). Un lot = une
   branche et une PR.
2. Chaque item donne : le constat vérifié, le correctif proposé, les tests
   d'acceptation et les pièges connus.
3. Les items marqués **décision** changent le produit : les soumettre au
   propriétaire avant d'écrire du code.
4. Une fois un item traité, le cocher ici (`✅ PR #n`) plutôt que de supprimer
   sa section : le constat sert d'historique.

Conventions du dépôt à respecter :

- **Tests** : `python tests/run_tests.py fast` pendant le travail, `all`
  (19 suites, dont les tests scientifiques) avant de pousser, et
  `ruff check .`. Un test qui cible un bug doit échouer sur l'ancien code.
- **Livraison** : un fichier `_*.py` ou une spec modifiés imposent une
  reconstruction des exe via `release.yml` (`deploy.py --new-tag`, voir
  `deploy.is_rebuild_file`). `lidar2map.py`, `providers/`, `gui/` et `tools/`
  sont patchables par `update_app.py`, mais une release qui mélange les deux
  exige la reconstruction.
- **Documentation** : guides utilisateur en anglais et en français
  (`*.md` + `*.fr.md`), documents de travail en français.
- **Workflows** : modifier `.github/workflows/*` peut exiger que le
  propriétaire pousse lui-même, selon les droits du jeton utilisé.
- **Commits** : thématiques, messages en français.

## Synthèse

Effort : **XS** quelques lignes · **S** un module et ses tests · **M** plusieurs
modules ou la CI · **L** restructuration.

| ID | Sujet | Priorité | Effort | Livraison |
|---|---|---|---|---|
| [R0](#r0-publier-la-version-et-la-valider-sur-de-vraies-machines) | Publier la PR #4 et la valider sur de vraies machines (✅ publiée en v1.51.0, validation manuelle à faire) | P0 | S | reconstruction |
| [S1](#s1-requêtes-get-déclenchées-par-dautres-sites) | Requêtes GET déclenchées par d'autres sites (✅ v1.51.1) | P1 | S | reconstruction |
| [S2](#s2-open_folder-ouvre-nimporte-quel-chemin) | `open_folder` ouvre n'importe quel chemin (✅ v1.51.1) | P1 | XS | patch |
| [D1](#d1-tester-lexécutable-construit-dans-releaseyml) | Tester l'exécutable construit dans `release.yml` (✅ v1.51.1, non bloquant jusqu'à un premier passage sur les 4 runners) | P1 | M | CI |
| [S4](#s4-json-avec-bom-lu-comme-corrompu) | JSON avec BOM lu comme corrompu (✅ v1.51.1) | P2 | XS | reconstruction |
| [S5](#s5-contexte-tls-sans-vérification-dans-le-provider-finlandais) | Contexte TLS sans vérification (Finlande) (✅ v1.51.1) | P2 | XS | reconstruction |
| [Doc1](#doc1-test-de-cohérence-entre-options-cli-et-documentation) | Test de cohérence options CLI ↔ doc (✅ v1.51.1) | P2 | S | tests |
| [Doc2](#doc2-dérives-documentaires-connues) | Dérives documentaires connues (✅ v1.51.1) | P2 | XS | doc et CI |
| [C1](#c1-reliquats-pywebview-dans-le-gui-web) | Reliquats pywebview dans le GUI web (✅ v1.51.1) | P3 | M | patch et reconstruction |
| [C2](#c2-entrées-mortes-du-bootstrap) | Entrées mortes du bootstrap (✅ v1.51.1) | P3 | XS | reconstruction |
| [P1–P4](#p1p4-parallélisation--travaux-restants) | Parallélisation : travaux restants | P3 | M | reconstruction |
| [S3](#s3-accès-distant-sans-authentification) | Accès distant sans authentification | **décision** | M | reconstruction |
| [D2](#d2-architecture-lanceur--bundle--patch) | Architecture lanceur + bundle + patch | **décision** | L | reconstruction |
| [M1](#m1-statut--expérimental--pour-les-sources-instables) | Statut « expérimental » des sources instables | **décision** | M | reconstruction probable |
| [C3](#c3-façades-et-dataclasses-de-dépendances) | Façades et dataclasses de dépendances | long terme | L | reconstruction |
| [C4](#c4-commentaires) | Commentaires qui racontent l'histoire | continu | — | — |

## Lots proposés

| Lot | Items | Remarque |
|---|---|---|
| A. Sécurité | S1, S2, S4, S5 | Une PR, puis intégrer à la release R0 si elle n'est pas encore faite. |
| B. CI de distribution | D1, et la partie `release.yml` de Doc2 | Touche les workflows. |
| C. Documentation | Doc1, Doc2 | Sans risque pour le code. |
| D. Nettoyage du GUI | C1, C2 | Tester le GUI à la main dans un navigateur. |
| E. Performance | P1 à P4 | Suivre le dossier de parallélisation. |
| Décisions | S3, D2, M1 | À trancher avec le propriétaire avant tout code. |

---

## R0. Publier la version et la valider sur de vraies machines

**Statut.** ✅ Étapes 1 et 2 : publiée en v1.51.0 le 25 septembre 2026. Reste
l'étape 3, la validation manuelle ci-dessous par le propriétaire.

**Constat.** `main` contient la PR #4, qui n'est dans aucune release.
`VERSION` vaut encore `"1.50.4"` (`lidar2map.py`, ligne ~1286). La PR modifie
les specs Windows, le bloc lanceur et des modules compilés (`_serve_web.py`,
`_autostart.py`, `_mbtiles_lidar.py`, `_merge_mbtiles.py`) : un patch par
`update_app.py` ne suffit pas.

**À faire.**

1. Passer `VERSION` à `1.51.0`. Version mineure : la PR ajoute des
   fonctionnalités (instances parallèles, accès distant sans `--bind`,
   `--new-instance`).
2. Publier via `python deploy.py -m "..." --new-tag`, qui déclenche
   `release.yml`.
3. Valider à la main ce que la CI ne couvre pas (voir D1) :

| OS | Vérification | Attendu |
|---|---|---|
| Windows | Double-clic sur `lidar2map.exe` après une extraction déjà faite | Aucune console, le navigateur s'ouvre. |
| Windows | Premier lancement ou mise à jour | Console visible pendant l'extraction, puis masquée. |
| Windows | `lidar2map.exe --help` dans un terminal | Aide affichée dans ce terminal, qui reste visible. |
| Windows | Traitement lancé puis « Arrêter » dans le GUI | Arrêt propre, pas de processus orphelin (`CTRL_BREAK_EVENT` a besoin de la console masquée). |
| 3 OS | Menu « Redémarrer » de l'icône de la zone de notification | Le serveur redémarre sur le même port. |
| Windows | Après « Redémarrer », lancer un traitement puis l'arrêter | Arrêt propre : le serveur relancé tourne avec `CREATE_NO_WINDOW`, jamais testé avec l'arrêt par `CTRL_BREAK_EVENT`. |
| 3 OS | Deuxième double-clic | Onglet avec la question « Continuer avec cette instance » ou « ➕ Nouvelle instance ». |
| 3 OS | Case « Démarrer à l'ouverture de session », puis déconnexion et reconnexion | Serveur démarré, mêmes projets et préférences qu'un lancement manuel (`LIDAR2MAP_WORK_DIR`). |
| 3 OS | Hôte de confiance renseigné (adresse Tailscale) | Page joignable depuis le téléphone sur `http://<adresse>:8766/`, toujours sur `127.0.0.1` en local. |
| Ubuntu 24.04 | `--remote-gui` vers une VM préparée par `rlidar2map_GUI_vm.sh` | Firefox (deb Mozilla) s'ouvre dans la session xrdp. |

**Piège.** `hide_console="hide-early"` ne masque que la console dont le
programme est propriétaire. Si le double-clic montre quand même une console,
vérifier que le lanceur (onefile) et l'exe interne sont bien construits avec
PyInstaller ≥ 6.

---

## S1. Requêtes GET déclenchées par d'autres sites

**Statut.** ✅ v1.51.1. `Handler.requete_inter_sites()` refuse (403) toute
route `/api/*`, GET comme POST, quand `Sec-Fetch-Site` vaut autre chose que
`same-origin` ou `none` ; les fichiers statiques ne sont pas concernés.
Tests : `FetchMetadataTests` dans `tests/test_serve_web.py`, en échec sur
l'ancien code. Le complément `X-Lidar2map` n'a pas été retenu.

**Constat.** `_serve_web.Handler.hote_autorise()` (ligne ~51) vérifie `Host`,
l'adresse du client et `Origin` quand elle est présente. Or un navigateur
n'envoie pas `Origin` sur un GET simple venu d'un autre site
(`<img src>`, `fetch(url, {mode: "no-cors"})`). N'importe quelle page ouverte
dans le navigateur de l'utilisateur peut donc **déclencher** les routes GET de
`/api/*` sur `127.0.0.1:8766`.

Elle **ne peut pas lire** les réponses : le serveur n'envoie aucun en-tête
CORS, et le contrôle de `Host` bloque le DNS rebinding. Le risque réel tient
aux effets de bord des routes GET (`main_serve_gui`, dictionnaire
`api_routes`, ligne ~6490) :

| Route | Effet déclenchable à l'aveugle |
|---|---|
| `/api/poll-log` | Vide la file du journal : les lignes d'un traitement en cours disparaissent du GUI. |
| `/api/usage?cache_dir=/` | Parcourt récursivement n'importe quel dossier : forte charge disque. |
| `/api/check-update` | Requête vers l'API GitHub, qui peut consommer le quota. |
| `/api/autocomplete-ville` | Requête vers le géocodeur externe. |

Les routes POST sont protégées : un POST inter-sites porte toujours `Origin`.

> Correction d'une affirmation antérieure : j'avais écrit qu'une page tierce
> pouvait « lire le journal ou parcourir vos dossiers ». C'est faux pour la
> lecture ; seuls les effets ci-dessus sont possibles.

**Correctif proposé.** Dans `do_GET` et `do_POST`, pour toute route `/api/*` :
refuser (403) si l'en-tête `Sec-Fetch-Site` est présent et vaut autre chose que
`same-origin` ou `none`. Tous les navigateurs actuels l'envoient (Chrome 76+,
Firefox 90+, Safari 16.4+). Les clients hors navigateur ne l'envoient pas et
restent acceptés, notamment `_instance_existante()` (`lidar2map.py`,
ligne ~6165) et les anciennes versions qui cherchent une instance existante.
Les fichiers statiques (`/`, `/app.js`…) ne sont pas concernés : l'onglet
ouvert par « ➕ Nouvelle instance » navigue vers un autre port, ce qui est
`same-site` et doit rester permis pour `/`.

Complément facultatif pour les navigateurs anciens : un en-tête personnalisé
(`X-Lidar2map: 1`) ajouté par `gui/web_bridge.js` à tous les `fetch` et exigé
sur `/api/*`. Il force un pré-vol CORS que le serveur ne satisfait pas. Il
faut alors l'ajouter aussi dans `_instance_existante()`, et accepter qu'une
ancienne version ne détecte plus une instance récente : elle en démarrerait
une seconde sur le port suivant.

**Tests d'acceptation** (`tests/test_serve_web.py`) :

- GET `/api/poll-log` avec `Sec-Fetch-Site: cross-site` → 403, et la file
  n'est pas vidée ;
- idem avec `same-site` → 403 ;
- GET avec `same-origin`, avec `none` ou sans l'en-tête → 200 ;
- GET `/` avec `same-site` → 200 ;
- POST inchangés.

---

## S2. `open_folder` ouvre n'importe quel chemin

**Statut.** ✅ v1.51.1. Dossier existant exigé ; sous Windows, chemin réseau
refusé avant tout accès disque (le simple `is_dir()` contacterait l'hôte en
SMB) ; application macOS (`.app`, un dossier que `open` lancerait) refusée.
L'erreur est renvoyée et affichée : alerte dans « Usage », ligne de journal
après un traitement. Limite : un dossier configuré en chemin UNC brut ne
s'ouvre plus depuis le GUI, une lettre de lecteur réseau reste acceptée.
Tests : `OpenFolderTests` dans `tests/test_serve_web.py`.

**Constat.** `Api.open_folder()` (`lidar2map.py`, ligne ~7972) passe le chemin
reçu tel quel à `explorer` (Windows), `open` (macOS) ou `xdg-open` (Linux).
Rien ne vérifie qu'il s'agit d'un dossier. Avec un fichier, le système l'ouvre
avec son application associée ; un exécutable se lance. Sous Windows, un
chemin UNC (`\\hôte\partage\x.exe`) désigne un fichier distant.
`_valider_cfg_web()` ne s'applique pas à cette route.

**Exposition.** La route est en POST, donc protégée contre les sites tiers.
Restent les clients autorisés : les processus locaux, qui ont déjà les droits
de l'utilisateur, et **tout pair qui joint l'hôte de confiance** (voir S3).

**Correctif proposé.**

- Résoudre le chemin, puis refuser s'il ne désigne pas un dossier existant
  (`Path.is_dir()`) ;
- sous Windows, refuser les chemins UNC (`\\` ou `//` en tête) ;
- renvoyer `{"ok": False, "error": ...}` au lieu de `{"ok": True}`
  inconditionnel (`_open_folder` dans `main_serve_gui`), et l'afficher dans le
  GUI.

**Tests.** Un fichier existant, un chemin inexistant et un chemin UNC sont
refusés sans appel à `subprocess.Popen` (mocké) ; un dossier est accepté.

---

## S3. Accès distant sans authentification

**Décision.** Il faut l'accord du propriétaire : `_valider_cfg_web()` cite sa
consigne « reste simple ».

**Constat.** Dans `hote_autorise()`, `tunnel_direct` accepte **n'importe
quelle adresse client** dès que l'en-tête `Host` vaut l'hôte de confiance.
Depuis la PR #4, `_serve_web.EcouteHoteConfiance` écoute sur cette adresse
dès qu'elle est renseignée. Tout appareil qui joint cette adresse (tout le
tailnet Tailscale, y compris les nœuds partagés) a donc un contrôle complet :

- lancer des traitements qui écrivent n'importe où, hors dossiers système ;
- ouvrir des fichiers (S2) ;
- modifier l'hôte de confiance ;
- activer le démarrage automatique.

**Proposition minimale.** Un jeton aléatoire (`secrets.token_urlsafe(24)`),
stocké dans les préférences, exigé seulement des clients qui ne sont pas en
boucle locale :

1. première visite : `http://<hôte>:8766/?cle=<jeton>` pose un cookie
   `HttpOnly; SameSite=Strict` ;
2. le dialogue « 🌐 Accès distant » affiche l'URL complète, et si possible un
   QR code, pour l'ouvrir sur le téléphone ;
3. un bouton régénère le jeton, ce qui révoque les appareils connectés.

L'usage local reste inchangé.

**Alternative si le propriétaire refuse.** Documenter clairement dans
`docs/getting-started*.md` (section 2.5) que tout pair du VPN a le contrôle
complet.

---

## S4. JSON avec BOM lu comme corrompu

**Statut.** ✅ v1.51.1. `lire_json` lit en `utf-8-sig`. Test ajouté à la
section 9 de `tests/_test_robustesse.py`, en échec sur l'ancien code.

**Constat.** `_atomic_files.lire_json()` (ligne ~20) lit en `utf-8`. Un
fichier qui commence par un BOM fait échouer `json.loads`, et la fonction
renvoie la valeur par défaut, comme pour un fichier corrompu. C'est le cas de
`preferences.json` ou `historique.json` enregistrés par le Bloc-notes de
Windows 10 avant 1903 ou par `Out-File -Encoding utf8` de PowerShell 5.1.
Conséquences :

- toutes les préférences semblent perdues : langue, hôte de confiance,
  démarrage automatique ;
- la prochaine écriture (`_ecrire_pref`) réécrit le fichier avec **une seule
  clé**, et les autres sont réellement effacées.

**Correctif.** Lire en `encoding="utf-8-sig"`, qui accepte le fichier avec ou
sans BOM. Une ligne à changer.

**Test.** Un fichier `{"lang": "fr", "trusted_host": "x"}` précédé d'un BOM
est lu correctement, et `_ecrire_pref("zoom", 1)` conserve les deux autres
clés.

---

## S5. Contexte TLS sans vérification dans le provider finlandais

**Statut.** ✅ v1.51.1. `_SSL_CTX` supprimé : le certificat du serveur
(autorité Telia) passe la validation stricte, vérifié le 25 septembre 2026.
`_fetch_provider_shadings()` utilise le contexte vérifié par défaut. Tests :
contrat sur `providers/*.py` (`_test_corrections.py`, S5) et
`test_provider_shading_ignores_provider_tls_context`
(`_test_atomic_downloads.py`).

**Constat.** `providers/fi_maanmittauslaitos.py` (lignes ~18–29) définit
`_SSL_CTX` avec `check_hostname = False` et `CERT_NONE`, au motif d'un
certificat auto-signé. Ce contexte n'est lu que par
`_ombrages_provider._fetch_provider_shadings()` (ligne ~216), le chemin des
ombrages précalculés. Or seul `be_flanders` déclare `PROVIDES_SHADINGS`. Les
téléchargements finlandais passent par `providers/common.py`, avec le
contexte vérifié par certifi (`_CTX`), et le test de fumée hebdomadaire
(`smoke.yml`, secret `FI_NLS_API_KEY`) les valide.

> Correction d'une affirmation antérieure : j'avais écrit que la vérification
> TLS était désactivée « pour les ombrages » finlandais. En réalité ce
> contexte n'est jamais utilisé aujourd'hui. C'est un piège latent : ajouter
> `PROVIDES_SHADINGS` à ce provider désactiverait la vérification en silence,
> clé API comprise dans l'URL.

**Correctif.**

1. Supprimer `_SSL_CTX` et son commentaire dans le provider finlandais.
2. Dans `_fetch_provider_shadings()`, ne plus lire de contexte fourni par le
   provider : utiliser le contexte vérifié commun (certifi).

**Test.** Un test de contrat qui échoue si un provider définit un contexte
avec `CERT_NONE` (parcours de `providers/*.py`).

---

## D1. Tester l'exécutable construit dans `release.yml`

**Statut.** ✅ v1.51.1. `tests/exe_smoke.py` (stdlib seule, dossier personnel
isolé) couvre les étapes 1 à 4 et tourne après « Package » sur les 4 runners.
Validé en local sur l'archive Windows de la v1.51.0. Non bloquant
(`continue-on-error`) jusqu'à un premier passage sur les 4 runners, bloquant
ensuite. Écarts : l'étape 2 vérifie la commande de `_commande_relance()`, pas
le menu « Redémarrer » lui-même (pas d'icône sur un runner) ; les MBTiles de
test sont écrits par le script (PNG en stdlib) plutôt que par un
`tests/fixtures_exe.py`.

**Constat.** Tous les tests tournent en mode source. `release.yml` construit,
empaquette et publie les 4 archives sans jamais les lancer. Les bugs de la
PR #4 sur le menu « Redémarrer » et le démarrage automatique n'existaient
qu'en mode figé : un test du binaire construit les aurait trouvés dès la
1.50.0. `--smoketest` existe, mais il exige le réseau et plusieurs minutes de
téléchargement : ce n'est pas un test de CI.

**Proposition.** Une étape après « Package », sur les 4 runners, qui
échoue la release si :

1. **Démarrage** : l'archive extraite dans un dossier temporaire, lancer le
   binaire (`lidar2map.exe`, `./lidar2map`, ou
   `LIDAR2MAP.app/Contents/MacOS/...`) avec
   `--serve-gui --no-browser --no-tray --port 18766`. Interroger
   `http://127.0.0.1:18766/api/init` jusqu'à obtenir `"app": "lidar2map"`
   (délai de 180 s, à cause de la première extraction), puis vérifier
   `/api/help`.
2. **Relance** : lancer l'exe interne extrait avec la sentinelle
   `--__lidar2map_inner__` et les mêmes options sur un autre port. C'est la
   commande de `_commande_relance()` : ce test aurait détecté le bug de
   « Redémarrer ».
3. **Traitement hors réseau** : fusionner deux petits MBTiles de test avec
   `--merge` (alias `--fusionner`), ce qui exerce sqlite, Pillow et la composition alpha dans le
   binaire. Générer les fixtures avec un script du dépôt, par exemple
   `tests/fixtures_exe.py`, à partir des générateurs déjà présents dans
   `_test_refactor_contracts.py`.
4. **Arrêt** : tuer l'arbre de processus (`taskkill /T /F` sous Windows,
   `kill` du groupe ailleurs), puis vérifier qu'aucune donnée utilisateur
   (historique, préférences, `Projets/`) n'a été écrite dans le dossier
   d'extraction : elles doivent aller à côté du binaire
   (`LIDAR2MAP_WORK_DIR`).

Écrire la logique dans un script Python du dépôt (`tests/exe_smoke.py`),
appelé par le workflow : il reste lisible et testable localement.

**Piège.** Sous macOS sans signature, lancer le binaire depuis le shell du
runner ne passe pas par Gatekeeper. Le test ne prouve donc rien sur la
quarantaine.

---

## D2. Architecture lanceur + bundle + patch

**Décision.** C'est un choix de produit.

**Constat chiffré.**

- Distribution actuelle : un lanceur PyInstaller *onefile*, un
  `lidar2map_bundle.zip` qui contient l'exe *onedir*, extrait au premier
  lancement dans `%LOCALAPPDATA%`, `~/Library/Application Support` ou
  `~/.local/share`, et `_loader.py` qui exécute `_internal/lidar2map.py` en
  texte pour permettre le patch.
- Le bloc lanceur fait environ 330 lignes au début de `lidar2map.py`
  (lignes ~618–948). `update_app.py` fait 617 lignes, `deploy.py` 671.
- Il y a 68 modules `_*.py` compilés : tout changement de l'un d'eux impose la
  reconstruction.
- **Les 13 dernières releases (v1.45.0 → v1.50.4) ont toutes exigé une
  reconstruction**, selon `deploy.is_rebuild_file` appliqué au diff entre
  tags. Le patch sans reconstruction n'a servi à aucune d'elles.
- Par commit sur `main` : en juin–juillet, 7 commits sur 211 touchant l'appli
  exigeaient une reconstruction ; en août–septembre, 39 sur 79.
- Les bugs de « Redémarrer » (`argv[0]` remplacé par `_loader.py`) et du
  démarrage automatique (`LIDAR2MAP_WORK_DIR` absent) venaient de cette
  dualité lanceur / exe interne.

**Options.**

| Option | Contenu | Pour | Contre |
|---|---|---|---|
| A. Statu quo assumé | Garder l'architecture, corriger ce qui annonce un patch toujours possible (Doc2) | Aucun risque | La complexité reste, et D1 devient indispensable. |
| B. Retirer le patch | Supprimer `update_app.py`, `update.yml` et le patch de `deploy.py` ; garder lanceur et bundle | Moins de code et de tests de contrat | Un correctif de provider seul exigera aussi 90 min de build sur 4 OS. |
| C. Exe *onedir* classique | Archive = dossier de l'exe ; plus de lanceur, d'extraction, de sentinelle ni de `_loader.py` ; données utilisateur dans un dossier d'application fixe | Supprime la cause des deux bugs et environ 1 000 lignes, plus leurs tests. Les exe *onefile* sont souvent plus signalés par les antivirus. | Archive de ~1,2 Go en milliers de fichiers, extraction plus lente par l'Explorateur Windows. Migration des données vers le nouveau dossier. |

**Recommandation.**

1. Faire **A** tout de suite : c'est Doc2.
2. Réévaluer entre **B** et **C** après deux ou trois mois de releases, avec
   D1 en place. Si la proportion de releases qui exigent une reconstruction
   reste proche de 100 %, le patch ne vaut plus son coût.
3. Pour **C**, mesurer d'abord sur Windows la taille de l'archive, la durée
   d'extraction par l'Explorateur et la réaction de Defender, avant de décider.

---

## Doc1. Test de cohérence entre options CLI et documentation

**Statut.** ✅ v1.51.1. `tests/test_cli_docs.py` lit les 7 parsers
(`_construire_parser_*`, dont 4 extraits de `main_decouper`, `main_fusionner`,
`main_serve` et `main_serve_gui`) et les options lues hors parser : 111
options distinctes, toutes documentées dans les deux langues. Les formes
négatives des alias français, générées par argparse, ont été documentées
plutôt qu'exclues. Vérifié : retirer `--tiles-overwrite` de `cli.fr.md` fait
échouer le test.

**Constat.** Le GUI web, mode par défaut depuis la 1.49, n'était documenté
nulle part avant la PR #4. Aujourd'hui, les options sont à jour : un relevé
des chaînes `--option` du code contre `docs/*.md` ne trouve que des options
internes (osmosis, pip, `systemctl`) et les alias français de
`--no-download` / `--no-download-compress`. Rien n'empêche la dérive de
revenir.

**Proposition.** Ajouter à `tests/_test_docs_links.py`, ou dans une nouvelle
suite, un test qui :

- construit les vrais parsers (`_terrain_cli`, `_raster_cli`, `_vector_cli`,
  `main_serve_gui`…) et collecte `parser._actions` plutôt qu'une regex, sans
  lancer de traitement. Certains parsers sont construits à l'intérieur de
  leur fonction `main*` : extraire d'abord leur construction dans une
  fonction dédiée ;
- vérifie que chaque option apparaît dans `docs/cli.md` **et**
  `docs/cli.fr.md` ;
- tient une liste d'exclusions explicite et commentée pour les options
  internes (`--__lidar2map_inner__`, alias français).

Le test doit échouer si l'on retire une option de `docs/cli.fr.md`.

---

## Doc2. Dérives documentaires connues

**Statut.** ✅ v1.51.1. Les six dérives sont corrigées ; tailles mesurées sur
la v1.51.0 (bundle Windows 253 Mio, 642 Mio extrait) ; en-tête de
`plan_refonte.fr.md` écrit sans version figée ; phase 17 réécrite autour de
`Api` et `main_serve_gui` ; description du dépôt passée à 27 pays.

| Fichier | Dérive | Correction |
|---|---|---|
| `.github/workflows/release.yml`, en-tête | « JRE + osmosis + Qt/QtWebEngine », tailles onedir ~1,2 Go et bundle ~450 Mo mesurées avec Qt | Retirer Qt, remesurer les tailles sur la prochaine release. |
| `release.yml`, corps de la release | « Mise à jour du script sans rebuild via `update_app.py` » | Préciser que le patch ne vaut que pour une release sans module compilé modifié (voir D2). |
| `_loader.py`, en-tête | « Remplacer lidar2map.py — aucun rebuild, aucun accès Mac nécessaire » | Même précision. |
| `docs/plan_refonte.fr.md`, en-tête | « Dernier lot de bundles déployé : 26 août 2026, v1.48.2 » | Dernière release : v1.50.4 du 24 septembre, bientôt 1.51.0. |
| `docs/plan_refonte.fr.md`, phase 17 | « déplacement de `lancer_gui` » : la fonction n'existe plus depuis le retrait de pywebview | Réécrire la phase autour de `main_serve_gui` et `_serve_web`, ou la déclarer sans objet. |
| Description du dépôt GitHub | « 22 countries » | 27 pays et 66 sources (`CODE` des providers). Se modifie dans les réglages du dépôt, pas dans un fichier. |

---

## C1. Reliquats pywebview dans le GUI web

**Statut.** ✅ v1.51.1. Pont renommé `window.api`, sans alias : `app.js` et
`web_bridge.js` sont toujours livrés ensemble et servis sans en-tête de
cache. Gardes et alertes « API indisponible » devenues impossibles
supprimées (celles qui signalent une vraie panne réseau restent), attente de
`pywebviewready` supprimée, `index.html` porte ses balises et `send_index()`
le sert tel quel. Vérifié dans Edge headless sur une instance isolée :
initialisation, aide, usage, projets, langue, zoom, refus S2 affiché, aucune
erreur JavaScript.

**Constat.** pywebview est retiré depuis la 1.49, mais le GUI garde son modèle :

- `gui/web_bridge.js` recrée `window.pywebview.api` ;
- `gui/app.js` contient 51 mentions de `pywebview`, dont des gardes
  `if (window.pywebview && pywebview.api && ...)`, 17 `alert(t('apiunavail'))`
  devenus impossibles, et l'attente de l'événement `pywebviewready` ;
- `_serve_web.Handler.send_index()` remplace à chaque requête les marqueurs
  d'inlining de `index.html` (`<style>/*__LIDAR2MAP_CSS__*/</style>`,
  `<script>//__LIDAR2MAP_JS__</script>`) par des balises ordinaires.

**Proposition.**

1. Renommer l'objet du pont, par exemple `window.api`, garder
   `window.pywebview` comme alias pendant la transition, puis le retirer.
2. Supprimer les gardes et les alertes `apiunavail`.
3. Écrire directement les balises `<link>` et `<script>` dans `index.html`,
   et servir le fichier tel quel.

**Pièges.**

- L'ordre de chargement change : `web_bridge.js` doit rester chargé avant
  `app.js`.
- Des tests de contrat lisent `index.html` et `app.js`, notamment
  `test_serve_web.py` : les adapter dans le même commit.

---

## C2. Entrées mortes du bootstrap

**Statut.** ✅ v1.51.1. Entrées retirées ; les tests du point d'extension
`gui_deps_plateforme` déclarent eux-mêmes leurs paquets d'exemple.

**Constat.** `_bootstrap_runtime.MODULE_PAR_PAQUET` (lignes ~20–42) associe
encore `pywebview`, `PyQt6`, `PyQt6-WebEngine`, `qtpy` et
`pyobjc-framework-WebKit/Cocoa` à leur module d'import, alors qu'aucune liste
d'installation ne les demande plus.

**Correctif.** Vérifier par `grep` qu'aucune liste de paquets ne les référence,
puis retirer ces entrées. Les `excludes` PyQt des specs PyInstaller restent
utiles : ils empêchent une inclusion accidentelle par une dépendance.

---

## P1–P4. Parallélisation : travaux restants

Détaillés dans [le dossier de parallélisation](correctif_parallelisation_warp_overviews_mbtiles.md),
section « Reste à faire » :

- **P1** : option `--gdal-threads N`, pour réduire le nombre de threads GDAL
  aujourd'hui fixé au nombre de CPU.
- **P2** : niveau des overviews non vérifié quand un cache warpé est
  réutilisé avec un autre `zoom_min`. Le rendu reste juste, les bas zooms sont
  lents.
- **P3** : verrou `<warped>.lock` par fichier cible, pour que deux processus
  ne recalculent pas le même warp. Nécessaire maintenant que les instances
  parallèles existent.
- **P4** : benchmark sur la VM de production, qui fixera le défaut de P1.

Commencer par P4 : les autres réglages en dépendent.

---

## M1. Statut « expérimental » pour les sources instables

**Décision.** Le propriétaire doit choisir le critère et l'affichage.

**Constat.** 66 sources dans 27 pays, pour un seul mainteneur. `smoke.yml`
teste chaque lundi une dalle par source. Certaines sont déjà exclues ou
connues pour échouer : `es-icgc` limite les IP cloud, `us-tnm` est instable,
les variantes LAZ sont trop lourdes pour la CI. Rien ne prévient
l'utilisateur qu'une source est fragile.

**Proposition.**

- Un attribut `STATUT = "experimental"` facultatif dans le provider, lu par
  le catalogue ;
- affiché dans le GUI (badge dans la liste des sources) et dans la liste CLI ;
- critère proposé : au moins deux échecs de `smoke.yml` sur les huit
  dernières semaines.

Cela transforme une panne de source en limite annoncée plutôt qu'en bug
signalé.

---

## C3. Façades et dataclasses de dépendances

**Constat.** 57 dataclasses `Dependances…` et de nombreuses façades existent
surtout pour que les anciens remplacements de fonctions dans les tests
continuent de marcher. `tests/_test_refactor_contracts.py` fait 12 526
lignes. Cela protège les extractions, mais chaque changement coûte cher et le
code se lit mal.

**Recommandation.** Ne pas lancer de chantier dédié : c'est le périmètre de
[`plan_refonte.fr.md`](plan_refonte.fr.md). Y ajouter une règle de sortie :
quand une façade n'a plus d'appelant hors tests, migrer ces tests vers le
module extrait, puis supprimer la façade. Mesurer à chaque phase le nombre de
façades et de dataclasses, et viser sa baisse plutôt que la seule taille de
`lidar2map.py`.

---

## C4. Commentaires

**Constat.** Beaucoup de commentaires racontent l'histoire du code (« avant…,
retiré…, vécu le… ») au lieu de dire ce qu'il fait et pourquoi. Certains
deviennent faux. Des exemples ont été corrigés dans la PR #4 : « 0 = tous les
CPUs » alors que GDAL lit 0 comme un seul thread, et les mentions de Qt.
L'histoire a déjà sa place : les messages de commit et `docs/`.

**Règle proposée, à appliquer au fil de l'eau.** Pour chaque fichier modifié :
réduire les commentaires historiques à une ligne et une référence (commit,
section de doc), et garder les avertissements « vécu le… » qui expliquent une
contrainte encore vraie.

---

## Annexe : vérifier les chiffres de ce document

```bash
# Nombre de modules compilés, de sources et de pays
ls _*.py | wc -l
grep -h '^CODE\s*=' providers/*.py | wc -l
grep -ho '^COUNTRY\s*=\s*"[a-z]*"' providers/*.py | sort -u | wc -l

# Releases qui ont exigé une reconstruction (après git fetch --tags)
python - <<'EOF'
import importlib.util, subprocess
spec = importlib.util.spec_from_file_location("deploy", "deploy.py")
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
tags = [t for t in subprocess.run(["git", "tag", "--sort=creatordate"],
        capture_output=True, text=True).stdout.split() if t.startswith("v")][-14:]
for a, b in zip(tags, tags[1:]):
    fichiers = subprocess.run(["git", "diff", "--name-only", a, b],
                              capture_output=True, text=True).stdout.split()
    print(a, "->", b, "reconstruction" if any(map(d.is_rebuild_file, fichiers)) else "patch")
EOF
```
