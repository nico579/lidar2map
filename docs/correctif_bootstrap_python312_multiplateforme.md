# Correctif proposé — runtime Python 3.12 autogéré et venv multi-plateforme

Date : 2026-07-28  
Statut : spécification technique, non implémentée  
Périmètre : exécution de `lidar2map.py` depuis les sources

## Résumé

Le correctif doit faire de `lidar2map.py` l'unique propriétaire de son runtime
Python et de son environnement virtuel.

Le comportement cible est :

1. un Python « lanceur » quelconque démarre `lidar2map.py` ;
2. le script cherche d'abord un venv lidar2map sain en Python 3.12 ;
3. s'il existe, le script se relance immédiatement dedans ;
4. sinon, il trouve ou installe localement un CPython 3.12 ;
5. il crée un venv Python 3.12, y installe les dépendances puis le valide ;
6. il se relance dans ce venv ;
7. les lancements suivants réutilisent le venv, y compris hors ligne.

Le Python système n'est jamais remplacé ou modifié.

Ce correctif résout notamment le cas :

```text
Ubuntu 24.04 / Python 3.12  -> wheel Fiona cp312 -> OK
Ubuntu 26.04 / Python 3.14  -> pas de wheel Fiona cp314 -> KO actuel
                                      |
                                      +-> correctif : runtime privé 3.12 -> OK
```

Il ne faut pas tenter de « convertir » un venv Python 3.14 en Python 3.12.
Un venv est lié à l'interpréteur qui l'a créé et ses extensions natives portent
l'ABI de cette version de Python.

## Ce que le correctif peut et ne peut pas garantir

### Garantie réaliste

Après une première installation réussie, l'exécution source devient indépendante
de la version du Python système sur les plateformes explicitement testées :

- Windows 10/11 x86-64 ;
- macOS Intel et Apple Silicon dans la plage de versions retenue par le projet ;
- Linux glibc x86-64 et arm64, notamment Ubuntu 24.04 et 26.04.

Un Python système 3.9, 3.12, 3.14 ou plus récent peut alors ne servir que de
« Python lanceur ». Le calcul réel est toujours effectué par le venv Python 3.12.

### Limites incompressibles d'un fichier `.py`

La promesse ne peut pas être « tout OS et tout Python » au sens absolu :

- sans aucun Python installé, un fichier `.py` ne peut pas commencer à
  s'exécuter ;
- le Python lanceur doit être assez récent pour parser le fichier entier ;
- Python 2 ou un Python antérieur au minimum syntaxique ne peut pas exécuter le
  bootstrap ;
- une architecture sans distribution CPython 3.12 compatible ne peut pas être
  autogérée ;
- le premier lancement nécessite du réseau, du disque et une validation TLS
  fonctionnelle ;
- un proxy bloquant, une machine hors ligne au premier lancement ou un OS trop
  ancien doivent produire une erreur claire, pas une boucle de relance ;
- les extensions optionnelles restent limitées par leurs wheels. Par exemple,
  `cloth-simulation-filter` ne fournit pas aujourd'hui une matrice complète pour
  toutes les combinaisons OS/architecture.

Si l'objectif devient « fonctionne même sans Python préinstallé », il faut un
lanceur natif par plateforme :

- `.exe` ou PowerShell amorceur sous Windows ;
- `.command`, application ou binaire amorceur sous macOS ;
- shell ou petit binaire amorceur sous Linux.

Le bundle remplit déjà ce rôle.

## Pourquoi le bundle n'a pas ce problème

Le bundle PyInstaller embarque :

- son propre interpréteur Python ;
- les modules Python ;
- les extensions natives ;
- Fiona, Rasterio, CSF, Qt et les autres dépendances intégrées au build.

Dans `lidar2map.py`, le mode `sys.frozen` court-circuite le bootstrap venv/pip.
Le bundle ne dépend donc ni du `python3` de l'OS, ni de la disponibilité d'une
wheel correspondant à ce Python système.

Il conserve cependant des contraintes binaires :

- un bundle x86-64 ne fonctionne pas sur arm64 ;
- le bundle Linux dépend d'une version minimale de glibc ;
- un bundle construit sur une distribution trop récente peut demander une
  glibc absente d'une distribution plus ancienne ;
- chaque famille OS nécessite son propre artefact.

Pour couvrir Ubuntu 24.04 et 26.04, le bundle Linux doit être construit sur la
plus ancienne base Linux officiellement supportée et testé sur les deux LTS.

## État actuel du bootstrap source

Les points concernés se trouvent principalement dans `lidar2map.py` :

- garde de version Python vers les lignes 924-932 ;
- `_bootstrap_venv_si_besoin()` vers la ligne 1100 ;
- détection du venv existant vers les lignes 1226-1239 ;
- création avec `sys.executable` vers les lignes 1241-1266 ;
- installation pip vers les lignes 1277-1328 ;
- `_relancer_dans_venv()` vers la ligne 1331 ;
- `_bootstrap_environnement()` vers la ligne 1593 ;
- appel top-level du bootstrap vers la ligne 1655.

Le défaut déterminant est actuellement :

```python
subprocess.run(
    [sys.executable, "-m", "venv", str(venv_path)],
    check=True,
)
```

Sur Ubuntu 26.04, `sys.executable` est Python 3.14. Le nouveau venv est donc
nécessairement un venv 3.14.

Le venv existant est par ailleurs validé uniquement par l'import des
dépendances. Sa version Python n'est pas vérifiée explicitement.

Dans le script distant intégré à `tools/rlidar2map_CLI.py`, le contrôleur
possède encore une partie du cycle de vie du venv :

```bash
_venv="$HOME/.lidar2map/venv"
if [ -d "$_venv" ] &&
   ! "$_venv/bin/python3" -m pip --version >/dev/null 2>&1
then
  rm -rf "$_venv"
fi
```

Cette responsabilité doit être retirée du lanceur pour éviter deux propriétaires
concurrents.

## Décisions de conception

### 1. Runtime de calcul fixé à CPython 3.12

Définir une source de vérité unique, tôt dans `lidar2map.py` :

```python
_RUNTIME_IMPLEMENTATION = "cpython"
_RUNTIME_VERSION = (3, 12)
_RUNTIME_REQUEST = "3.12"
```

Le choix porte sur la version mineure, pas sur un patch figé. Le gestionnaire
installe le dernier patch 3.12 disponible et conserve la version exacte dans un
manifest local.

Raisons :

- wheels Fiona disponibles ;
- wheels `cloth-simulation-filter` disponibles sur les plateformes actuellement
  couvertes par ce paquet ;
- compatibilité des autres dépendances majeures ;
- parité avec Ubuntu 24.04, déjà validé en production ;
- indépendance vis-à-vis des changements du Python par défaut de l'OS.

Cette décision devra être réévaluée avant la fin du support sécurité de
Python 3.12.

### 2. Distinguer Python lanceur et Python de calcul

La garde actuelle « Python 3.9 minimum » ne doit pas interdire à Python 3.14 de
jouer le rôle de lanceur.

Deux notions doivent être séparées :

- **minimum du lanceur** : version minimale capable de parser et d'exécuter le
  bootstrap ;
- **runtime géré** : Python 3.12 exact pour le venv de calcul.

Le code de bootstrap placé avant la relance doit rester compatible avec le
minimum annoncé. Les API ou syntaxes plus récentes ne doivent être utilisées
qu'après l'entrée dans le venv 3.12.

### 3. Ne pas créer un deuxième environnement arbitraire

Le script doit continuer à posséder un seul venv actif.

Chemin canonique recommandé :

```text
~/.lidar2map/venvs/cpython-3.12/
```

Le chemin versionné présente plusieurs avantages :

- un ancien venv 3.14 n'est pas supprimé pendant qu'un processus pourrait
  encore l'utiliser ;
- une migration peut être préparée et validée à côté de l'ancien environnement ;
- une création interrompue ne corrompt pas un venv sain ;
- une future migration Python 3.13 ou 3.14 devient explicite.

Compatibilité avec le chemin historique :

```text
~/.lidar2map/venv/
```

- s'il s'agit d'un venv Python 3.12 sain, le réutiliser sans réinstallation ;
- s'il est incomplet ou utilise une autre version, l'ignorer ;
- ne pas le supprimer automatiquement pendant la migration ;
- `--desinstaller` devra supprimer l'ancien et le nouveau chemin.

Une variante plus invasive consisterait à remplacer en place
`~/.lidar2map/venv`. Elle est déconseillée car elle rend plus difficile la
publication atomique et la coexistence avec un processus déjà lancé.

### 4. Appliquer l'autogestion uniquement au mode `auto`

La sémantique existante doit être conservée :

- `--bootstrap=auto` : sélection/installation de Python 3.12 et gestion du venv ;
- `--bootstrap=pip` : utiliser l'environnement courant choisi par l'utilisateur ;
- `--bootstrap=none` : aucun téléchargement, aucune installation, aucune
  suppression ;
- mode frozen : aucun venv et aucun pip ;
- environnement Conda/venv externe actif : conserver le garde-fou actuel, sauf
  si l'environnement actif est précisément le venv lidar2map cible.

Le correctif ne doit jamais télécharger Python 3.12 en mode `pip` ou `none`.

### 5. Prévoir un override administrateur

Ajouter :

```text
LIDAR2MAP_PYTHON=/chemin/vers/python3.12
LIDAR2MAP_RUNTIME_DOWNLOAD=0
```

`LIDAR2MAP_PYTHON` permet de fournir un interpréteur approuvé par
l'administrateur. Il est toujours validé avant usage.

`LIDAR2MAP_RUNTIME_DOWNLOAD=0` interdit tout téléchargement automatique. Si
aucun venv ni Python 3.12 compatible n'existe, le script s'arrête avec les
commandes à exécuter manuellement.

## Machine d'états proposée

```text
START
  |
  +-- frozen ? ------------------------------> continuer sans bootstrap
  |
  +-- mode none ? ----------------------------> vérifier imports, continuer/KO
  |
  +-- mode pip ? -----------------------------> environnement courant
  |
  +-- déjà dans le venv lidar2map ?
  |      |
  |      +-- Python 3.12 ----------------------> continuer
  |      |
  |      +-- autre version -------------------> erreur sûre, pas d'auto-suppression
  |
  +-- venv historique/canonique sain 3.12 ? --> exec dans ce venv
  |
  +-- prendre le verrou bootstrap
         |
         +-- revérifier le venv
         |
         +-- chercher Python 3.12 existant
         |      1. LIDAR2MAP_PYTHON
         |      2. sys.executable s'il est en 3.12
         |      3. python3.12/python3.12.exe dans PATH
         |      4. runtime géré déjà téléchargé
         |
         +-- absent et download autorisé ?
         |      |
         |      +-- non ----------------------> erreur documentée
         |      +-- oui ----------------------> installer runtime 3.12
         |
         +-- créer venv dans un dossier temporaire
         +-- installer les dépendances
         +-- valider version + imports
         +-- publier atomiquement
         +-- libérer le verrou
         +-- exec dans le venv
```

Il n'est pas nécessaire de relancer d'abord tout le script sous le Python 3.12
de base. Le Python lanceur peut appeler directement :

```text
/chemin/python3.12 -m venv <venv-temporaire>
```

Puis le script se relance une seule fois avec le Python du venv validé.

## Fonctions à introduire

Les noms ci-dessous sont indicatifs.

### `_version_python(executable)`

Exécute l'interpréteur candidat sans l'importer dans le processus courant :

```python
def _version_python(executable):
    code = (
        "import json, platform, sys; "
        "print(json.dumps({"
        "'version': list(sys.version_info[:3]), "
        "'implementation': platform.python_implementation(), "
        "'prefix': sys.prefix, "
        "'base_prefix': getattr(sys, 'base_prefix', sys.prefix)"
        "}))"
    )
    ...
```

Contraintes :

- timeout court, par exemple 15 secondes ;
- chemin passé comme élément de liste, jamais concaténé dans un shell ;
- retour `None` si exécutable absent, cassé ou de mauvaise architecture ;
- vérifier CPython et `(major, minor) == (3, 12)`.

### `_venv_runtime_sain(venv_python, verifier_deps=True)`

Vérifie :

1. l'exécutable existe ;
2. il démarre ;
3. il s'agit de CPython 3.12 ;
4. `sys.prefix` correspond au venv attendu ;
5. `pyvenv.cfg` existe ;
6. pip répond ;
7. les imports critiques fonctionnent si `verifier_deps=True`.

La version doit être testée avant les imports. Un venv 3.14 avec pip fonctionnel
est incompatible même si quelques paquets s'importent.

### `_trouver_python_runtime()`

Ordre de recherche :

1. `LIDAR2MAP_PYTHON` ;
2. `sys.executable` ;
3. `python3.12` sous Unix ;
4. `python3.12.exe`, `py -3.12` et chemins usuels sous Windows ;
5. runtime géré dans `~/.lidar2map/runtime/`.

Chaque candidat est validé par `_version_python`.

Sous Windows, `py -3.12` est une commande avec arguments et doit être représenté
comme une liste, pas comme un faux chemin d'exécutable.

### `_installer_python_runtime()`

Solution recommandée : utiliser `uv` et ses distributions
`python-build-standalone`.

Organisation locale :

```text
~/.lidar2map/
  runtime/
    bin/uv
    python/
    runtime.json
  cache/
    uv/
  venvs/
    cpython-3.12/
```

Variables passées à `uv` :

```text
UV_PYTHON_INSTALL_DIR=~/.lidar2map/runtime/python
UV_CACHE_DIR=~/.lidar2map/cache/uv
UV_NO_MODIFY_PATH=1
```

Commandes logiques :

```text
uv python install 3.12
uv python find --managed-python 3.12
```

Le script ne doit pas modifier le `PATH`, les profils shell ou le Python
système.

#### Amorçage de `uv`

Deux options sont possibles.

Option A, préférable pour un produit distribué :

- épingler une version de `uv` ;
- maintenir une table URL + SHA-256 par OS/architecture ;
- télécharger le binaire officiel ;
- vérifier le hash avant extraction ;
- publier le binaire atomiquement dans `runtime/bin/`.

Option B, acceptable pour une première implémentation :

- télécharger l'installateur officiel correspondant à l'OS ;
- demander une installation non gérée dans `runtime/bin/` ;
- désactiver toute modification du profil shell ;
- épingler la version de l'installateur ;
- journaliser l'URL et la version.

Il ne faut pas exécuter silencieusement un `curl | sh` non versionné.

Le téléchargement du runtime ne doit jamais utiliser le fallback TLS non
vérifié défini avant le bootstrap actuel. HTTPS vérifié et contrôle SHA-256 sont
obligatoires.

### `_creer_venv_transactionnel(python_base, cible)`

Créer dans un chemin unique :

```text
~/.lidar2map/venvs/.cpython-3.12.tmp-<pid>-<nonce>/
```

Étapes :

1. `python_base -m venv <temp>` ;
2. `<temp>/bin/python -m pip --version` ;
3. installation des dépendances ;
4. vérification des imports critiques ;
5. écriture d'un manifest :

   ```json
   {
     "implementation": "cpython",
     "python": "3.12.x",
     "created_at": "...",
     "dependency_profile": "runtime-v1"
   }
   ```

6. renommage atomique du temporaire vers la cible ;
7. suppression best-effort des temporaires orphelins anciens.

En cas d'erreur ou de `Ctrl+C`, le venv cible sain existant n'est jamais touché.

### `_relancer_dans_venv()`

La fonction actuelle peut être conservée :

- Unix : `os.execv` ;
- Windows : `subprocess.run`, attente du processus enfant et propagation du
  code retour.

Ajouter avant la relance :

- vérification finale CPython 3.12 ;
- compteur de relances ;
- affichage du chemin exact choisi.

Sentinelle proposée :

```text
LIDAR2MAP_RUNTIME_REEXEC_COUNT
```

Refuser une valeur supérieure à 2. Cette limite transforme une erreur de logique
en message explicite au lieu d'une boucle infinie.

Attention : sous Unix, le code placé dans un `finally` après `os.execv` ne sera
pas exécuté si l'`exec` réussit. Les variables temporaires doivent donc être
consommées ou écrasées explicitement par le processus suivant.

## Verrou interprocessus

Deux lancements SSH peuvent aujourd'hui atteindre le bootstrap simultanément,
car le contrôleur distant vérifie la session tmux après le bootstrap.

Protéger ensemble :

- l'installation de `uv` ;
- l'installation de Python 3.12 ;
- la création du venv ;
- l'installation pip ;
- la publication du venv.

Chemin du verrou :

```text
~/.lidar2map/.runtime-bootstrap.lock
```

Le verrou doit vivre hors du dossier remplacé.

Le projet contient déjà une logique de lockfile avec détection d'un verrou
périmé pour l'extraction du bundle. Elle peut servir de modèle, mais la durée
maximale doit tenir compte d'un premier `pip install` pouvant dépasser
plusieurs minutes.

Comportement attendu :

1. acquisition atomique ;
2. si verrou occupé, attendre en affichant un message ;
3. revérifier régulièrement si un venv sain a été publié ;
4. identifier les verrous réellement orphelins ;
5. après timeout, sortir avec une erreur et le chemin du verrou ;
6. toujours libérer le verrou lors des sorties normales et exceptions.

## Gestion des dépendances

Fixer Python 3.12 résout le défaut Fiona actuel, mais ne remplace pas une
politique de dépendances reproductible.

### Correctif minimal

Conserver les listes actuelles, mais exécuter pip avec le Python du venv :

```text
<venv-python> -m pip install ...
```

Éviter l'appel direct à `venv/bin/pip`, moins portable.

### Durcissement recommandé

1. Ajouter un fichier de contraintes Python 3.12 testé.
2. Épingler les versions critiques.
3. Exiger des wheels pour les extensions natives :

   ```text
   --only-binary=:all:
   ```

4. Échouer rapidement si une wheel manque au lieu de compiler implicitement
   Fiona, GDAL ou Qt sur une VM minimale.
5. Conserver l'erreur pip complète dans :

   ```text
   ~/.lidar2map/bootstrap.log
   ```

6. Ne plus tronquer stderr aux 500 derniers caractères.

### Dépendances trop largement critiques

Deux améliorations restent souhaitables même avec Python 3.12 :

- rendre Fiona paresseuse pour les seuls pipelines qui l'utilisent ;
- ne pas installer PyQt6/WebEngine comme dépendances critiques d'un lancement
  CLI headless.

Cela réduit le temps, le volume et la surface d'échec du bootstrap.

### Cas CSF

Avant d'annoncer une compatibilité multi-plateforme complète, construire une
matrice réelle des wheels `cloth-simulation-filter` :

| Plateforme | Architecture | Python 3.12 | Attendu |
|---|---:|---:|---|
| Windows | x86-64 | wheel disponible | CSF activable |
| Linux glibc | x86-64 | wheel disponible | CSF activable |
| macOS | arm64 | wheel disponible | CSF activable |
| Linux | arm64 | à confirmer | fallback `classes` ou erreur claire |
| Windows | arm64 | à confirmer | fallback `classes` ou erreur claire |
| macOS | x86-64 | à confirmer | fallback `classes` ou erreur claire |

Le pipeline principal ne doit pas être déclaré en panne parce qu'une extension
optionnelle n'a pas de wheel pour une architecture donnée.

## Traitement de `--version` et préparation explicite

Aujourd'hui, `python3 lidar2map.py --version` déclenche toute l'installation avant
qu'argparse affiche la version. Le script distant de `rlidar2map_CLI.py`
exploite implicitement cet effet de bord comme commande de préparation.

Il est préférable de séparer les deux usages :

```text
python3 lidar2map.py --version
python3 lidar2map.py --prepare-runtime
```

Comportement proposé :

- `--version` : afficher la version sans réseau ni installation ;
- `--prepare-runtime` : installer/valider Python 3.12, le venv et les
  dépendances critiques, afficher le diagnostic puis quitter ;
- lancement normal : préparer automatiquement si nécessaire.

Le script distant intégré à `tools/rlidar2map_CLI.py` utilisera alors :

```bash
( cd "$DIR" && python3 lidar2map.py --prepare-runtime )
```

Il ne devra plus lire, supprimer ou réparer directement le venv.

## Changements précis dans le script distant de `rlidar2map_CLI.py`

Conserver :

- installation de `git` et `tmux` ;
- installation d'un `python3` minimal capable de lancer le bootstrap ;
- clone/pull ;
- lancement tmux.

Retirer :

- la suppression de `~/.lidar2map/venv` ;
- toute sélection directe de Python 3.12 ;
- toute connaissance de la structure interne du runtime.

Remplacer :

```bash
python3 lidar2map.py --version
```

par :

```bash
python3 lidar2map.py --prepare-runtime
```

Le lanceur reste alors générique et `lidar2map.py` se comporte de la même façon
hors SSH.

Déplacer également le test « session tmux déjà active » avant la préparation
afin qu'un second appel ne tente pas une migration pendant un calcul existant.

## Désinstallation

Mettre à jour les deux chemins de désinstallation pour supprimer :

```text
~/.lidar2map/venv/                  # historique
~/.lidar2map/venvs/
~/.lidar2map/runtime/
~/.lidar2map/cache/uv/
~/.lidar2map/.runtime-bootstrap.lock
```

Ne supprimer aucun Python système et aucune installation `uv` externe fournie
par l'utilisateur.

Afficher séparément la taille libérée pour :

- venv ;
- CPython géré ;
- cache de téléchargement ;
- JRE ;
- osmosis.

## Messages utilisateur

Premier lancement sous Ubuntu 26.04 :

```text
System Python : CPython 3.14.x
Required lidar2map runtime : CPython 3.12
No compatible lidar2map environment found.
Installing private CPython 3.12 in ~/.lidar2map/runtime/...
Creating isolated environment ~/.lidar2map/venvs/cpython-3.12/...
Installing binary dependencies...
Runtime ready.
Relaunching with Python 3.12...
```

Second lancement :

```text
Using lidar2map runtime: CPython 3.12.x
Environment: ~/.lidar2map/venvs/cpython-3.12
```

Mode hors ligne sans runtime :

```text
ERROR: lidar2map requires its managed CPython 3.12 runtime.
No compatible runtime is installed and downloads are disabled/unavailable.

Provide one with:
  LIDAR2MAP_PYTHON=/path/to/python3.12 python3 lidar2map.py ...

Or allow the automatic runtime download and relaunch.
```

Plateforme non supportée :

```text
ERROR: no managed CPython 3.12 build is configured for:
  OS=<...>, architecture=<...>

Use --bootstrap=pip with a compatible environment, or use a native bundle.
```

## Tests à ajouter

### Tests unitaires sans réseau

Mock de `subprocess.run`, des chemins et du téléchargeur :

- venv historique sain en 3.12 : réutilisé ;
- venv canonique sain en 3.12 : réutilisé ;
- venv 3.14 avec pip fonctionnel : refusé ;
- venv sans `pyvenv.cfg` : refusé ;
- venv dont l'exécutable ne démarre plus : refusé ;
- `sys.executable` en 3.12 : choisi ;
- `sys.executable` en 3.14 + `python3.12` présent : 3.12 choisi ;
- aucun Python 3.12 + téléchargement permis : installateur appelé ;
- aucun Python 3.12 + téléchargement interdit : erreur claire ;
- hash runtime incorrect : archive rejetée ;
- échec de création : cible saine préservée ;
- interruption pendant pip : temporaire ignoré au prochain lancement ;
- compteur de ré-exec dépassé : arrêt ;
- conservation exacte de `sys.argv`.

### Modes

- `auto` : gestion complète ;
- `pip` : aucun téléchargement et aucune suppression ;
- `none` : aucun téléchargement et aucune suppression ;
- aliases historiques `--venv`, `--no-venv`, `--no-bootstrap` ;
- priorité argument CLI sur variable d'environnement ;
- Conda actif ;
- venv externe actif ;
- mode frozen ;
- `--version` sans bootstrap ;
- `--prepare-runtime` avec bootstrap ;
- `--desinstaller`.

### Concurrence et reprise

- deux processus démarrent simultanément sur le même `HOME` ;
- le second attend puis réutilise le venv publié par le premier ;
- interruption pendant le téléchargement de Python ;
- interruption pendant la création du venv ;
- interruption pendant pip ;
- verrou orphelin ;
- temporaire orphelin ;
- aucune cible partiellement publiée.

### Matrice d'intégration minimale

| OS | Python système | Architecture | Premier run | Second run hors ligne |
|---|---:|---:|---:|---:|
| Ubuntu 24.04 | 3.12 | x86-64 | OK | OK |
| Ubuntu 26.04 | 3.14 | x86-64 | OK | OK |
| Ubuntu 26.04 | 3.14 | arm64 | OK hors CSF, CSF selon wheel | OK |
| Windows 11 | version différente de 3.12 | x86-64 | OK | OK |
| macOS Intel | version différente de 3.12 | x86-64 | OK | OK |
| macOS Apple Silicon | version différente de 3.12 | arm64 | OK | OK |

Pour chaque cas, vérifier dans le processus final :

```python
assert sys.version_info[:2] == (3, 12)
assert Path(sys.prefix).resolve() == expected_venv.resolve()
```

## Déploiement en étapes

### Étape 1 — validation et observabilité

- ajouter la vérification explicite de version du venv ;
- afficher Python système, Python cible et chemin du venv ;
- conserver stderr pip complet ;
- ne modifier encore aucun venv automatiquement.

### Étape 2 — chemin versionné et préparation transactionnelle

- introduire `venvs/cpython-3.12` ;
- réutiliser le venv historique s'il est déjà sain en 3.12 ;
- ajouter verrou, staging et publication atomique ;
- ajouter `--prepare-runtime`.

### Étape 3 — acquisition du Python 3.12

- chercher d'abord les interpréteurs déjà installés ;
- ajouter le runtime géré et vérifié ;
- tester Ubuntu 24.04/26.04, Windows et macOS ;
- documenter les architectures réellement couvertes.

### Étape 4 — dépendances reproductibles

- contraintes/lock Python 3.12 ;
- wheels obligatoires pour les extensions natives ;
- Fiona et GUI rendues conditionnelles ;
- matrice CSF.

### Étape 5 — bascule du lanceur VM

- remplacer `--version` par `--prepare-runtime` ;
- retirer la gestion du venv du shell ;
- déplacer le garde tmux avant le bootstrap ;
- valider sur une VM Hetzner Ubuntu 26.04 neuve.

## Critères d'acceptation

Le correctif est terminé lorsque :

1. `python3 lidar2map.py --prepare-runtime` fonctionne sur une VM Ubuntu 26.04
   neuve avec Python système 3.14 ;
2. le processus final utilise effectivement CPython 3.12 ;
3. aucun paquet Python n'est installé dans le Python système ;
4. un venv historique sain en 3.12 n'est ni supprimé ni réinstallé ;
5. un venv 3.14 n'est jamais pris pour un venv compatible ;
6. deux bootstraps concurrents ne peuvent pas publier un état partiel ;
7. le second lancement fonctionne sans réseau ;
8. `--bootstrap=none` et `--bootstrap=pip` ne changent pas de sémantique ;
9. le bundle continue à court-circuiter entièrement ce code ;
10. Ubuntu 24.04, Ubuntu 26.04, Windows et macOS passent la matrice prévue ;
11. les plateformes/architectures non couvertes échouent avec un diagnostic
    explicite ;
12. `--desinstaller` retire uniquement les runtimes appartenant à lidar2map.

## Références

- Ubuntu 26.04, passage de Python 3.12 à 3.14 :
  <https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/>
- Fiona sur PyPI :
  <https://pypi.org/project/fiona/>
- Ticket Fiona pour les wheels Python 3.14 :
  <https://github.com/Toblerity/Fiona/issues/1504>
- Compilation source de Fiona et dépendance GDAL :
  <https://fiona.readthedocs.io/en/stable/install.html>
- `cloth-simulation-filter` sur PyPI :
  <https://pypi.org/project/cloth-simulation-filter/>
- Installation d'un Python géré avec `uv` :
  <https://docs.astral.sh/uv/guides/install-python/>
- Installation autonome de `uv` :
  <https://docs.astral.sh/uv/getting-started/installation/>
- Options de l'installateur `uv` :
  <https://docs.astral.sh/uv/reference/installer/>
