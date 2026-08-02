# Évolution envisagée : unifier les modes local et distant

Statut : **proposition à terme, non implémentée**.

Aujourd'hui, deux points d'entrée coexistent :

- `lidar2map.py` exécute directement un calcul sur la machine locale ;
- `tools/rlidar2map_CLI.py` déploie le calcul sur une VM, le maintient dans `tmux`,
  le surveille et synchronise ses résultats.

L'évolution proposée consiste à offrir une interface unique dans
`lidar2map.py`, tout en conservant le moteur d'exécution distante dans un
module séparé.

## Objectif utilisateur

Le pipeline métier et ses paramètres resteraient identiques. Seul le lieu
d'exécution changerait.

```bash
# Mode local actuel
python lidar2map.py --ignlidar --zone-ville gareoult --zone-width 5 \
    --zone-nom gareoult_lrm3 --telechargement --ombrages lrm \
    --shading lrm:sigma=3 --formats-fichier mbtiles

# Syntaxe distante envisagée — elle n'est pas encore implémentée
python lidar2map.py --remote root@192.0.2.10 \
    --remote-session gareoult-lrm3 \
    --ignlidar --zone-ville gareoult --zone-width 5 \
    --zone-nom gareoult_lrm3 --telechargement --ombrages lrm \
    --shading lrm:sigma=3 --formats-fichier mbtiles
```

Sans `--remote`, l'exécution resterait locale. Ce comportement par défaut ne
doit pas changer.

## Interface distante proposée

Toutes les options d'orchestration seraient préfixées par `--remote-` pour ne
pas les confondre avec les paramètres du calcul lidar2map.

| Option proposée | Rôle | Défaut envisagé |
|---|---|---|
| `--remote HOST` | Active le mode distant et désigne la cible SSH | absent : mode local |
| `--remote-session NOM` | Identifiant persistant du run et nom du `tmux` | `lidar` |
| `--remote-mode source\|bundle` | Déploiement du checkout ou du bundle publié | `source` |
| `--remote-local-dir DOSSIER` | Racine de synchronisation sur l'ordinateur local | `vm-results/<hôte>/<session>` |
| `--remote-interval SECONDES` | Fréquence de surveillance et de synchronisation | `30` |
| `--remote-sync-method MÉTHODE` | `auto`, `rsync` ou flux SSH incrémental | `auto` |
| `--remote-identity FICHIER` | Clé privée SSH explicite | configuration SSH normale |
| `--remote-ssh-timeout SECONDES` | Délai maximal d'une commande SSH | `10` |
| `--remote-ssh-option KEY=VALUE` | Option OpenSSH supplémentaire, répétable | aucune |
| `--remote-reset-host-key` | Accepte le remplacement volontaire d'une VM gardant son IP | désactivé |
| `--remote-max-ssh-errors N` | Erreurs SSH consécutives tolérées | `3` |
| `--remote-detach` | Lance ou retrouve le run puis rend la main | désactivé |
| `--remote-once` | Effectue un contrôle et une synchronisation | désactivé |
| `--remote-restart` | Archive un run terminé puis relance la session | désactivé |
| `--remote-purge` | Synchronise puis purge le run distant terminé | désactivé |
| `--remote-no-bell` | Désactive l'alerte sonore finale | désactivé |

Les noms définitifs devront être validés avant développement. Le préfixe
`--remote-` est recommandé parce qu'il rend immédiatement visible quelles
options concernent l'orchestration plutôt que le traitement LiDAR.

## Architecture recommandée

L'intégration doit porter sur l'interface, pas consister à copier le contrôleur
distant dans le gros fichier principal.

```text
lidar2map.py
│
├── sans --remote
│   └── pipeline local actuel
│
└── avec --remote HOST
    └── remote_runner
        ├── déploiement source ou bundle
        ├── lancement dans tmux
        ├── état persistant du run
        ├── surveillance et notifications
        ├── synchronisation atomique
        └── purge distante sécurisée
             │
             └── lidar2map exécuté localement sur la VM
```

Le futur module `remote_runner` reprendrait le code actuellement validé dans
`tools/rlidar2map_CLI.py`. Il devrait rester utilisable avec la seule bibliothèque
standard Python : déclencher un calcul distant ne doit pas charger Rasterio,
NumPy, GDAL ou les autres dépendances lourdes sur le poste contrôleur.

`tools/rlidar2map_CLI.py` resterait le point d'entrée public et importerait ce
module interne.

## Séquence d'exécution

1. Un pré-analyseur léger détecte `--remote` avant le bootstrap des dépendances
   scientifiques.
2. Sans `--remote`, lidar2map suit exactement son chemin local actuel.
3. Avec `--remote`, les options `--remote-*` sont consommées localement.
4. Les seuls arguments métier lidar2map sont transmis à la VM.
5. Le contrôleur déploie la source ou le bundle, puis lance lidar2map dans
   `tmux`.
6. La VM exécute le pipeline normal, comme un calcul local.
7. Le contrôleur surveille l'état persistant et synchronise les fichiers
   publiés.

Les options `--remote-*` ne doivent jamais être transmises au processus lancé
sur la VM. Cette séparation empêche une récursion où la VM tenterait de lancer
une seconde VM.

## Invariants à conserver

L'intégration ne devra pas affaiblir les garanties actuelles :

- `Ctrl-C` sur l'ordinateur local n'arrête pas le calcul distant ;
- relancer la même cible et la même session reprend la surveillance ;
- une session existante ne lance jamais implicitement un second processus ;
- le résultat est déterminé par l'état persistant et le code de sortie, pas par
  l'analyse du texte du journal ;
- les fichiers et dossiers `.part` ne sont pas synchronisés ;
- les fichiers transférés sont vérifiés et publiés atomiquement en local ;
- une synchronisation finale est tentée après succès ou échec ;
- la purge refuse un run actif et ne supprime jamais les dossiers partagés
  `cache/`, `production/`, le dépôt ou le venv ;
- `--output-dir` reste contrôlé par l'orchestrateur afin d'isoler chaque run.

Le protocole distant devra rester versionné pour qu'un contrôleur récent puisse
détecter proprement une VM utilisant une ancienne version.

## Reprise et commandes sans nouveau calcul

Une commande distante avec des paramètres métier créerait un run absent :

```bash
# Syntaxe cible, non encore disponible
python lidar2map.py --remote root@192.0.2.10 \
    --remote-session gareoult-lrm3 \
    --ignlidar --zone-ville gareoult --zone-width 5 \
    --zone-nom gareoult_lrm3 --telechargement --ombrages lrm \
    --shading lrm:sigma=3 --formats-fichier mbtiles
```

La même commande sans paramètres métier reprendrait seulement le run :

```bash
python lidar2map.py --remote root@192.0.2.10 \
    --remote-session gareoult-lrm3
```

Une session terminée nécessiterait une action explicite :

```bash
# Nouveau calcul sous le même nom
python lidar2map.py --remote root@192.0.2.10 \
    --remote-session gareoult-lrm3 --remote-restart \
    --ignlidar --zone-ville gareoult --zone-width 5 \
    --zone-nom gareoult_lrm3 --telechargement --ombrages lrm \
    --shading lrm:sigma=3 --formats-fichier mbtiles

# Dernière synchronisation puis purge distante
python lidar2map.py --remote root@192.0.2.10 \
    --remote-session gareoult-lrm3 --remote-purge
```

## Intégration future au GUI

La même couche pourrait ensuite être appelée par le GUI. Un profil de VM
enregistrerait uniquement les paramètres d'orchestration :

- alias ou cible SSH ;
- clé privée éventuelle ;
- mode source ou bundle ;
- racine locale ;
- fréquence de synchronisation ;
- options SSH particulières.

Le formulaire du calcul LiDAR resterait identique. L'utilisateur choisirait
simplement « local » ou un profil de VM avant de lancer.

Les secrets et clés privées ne devront jamais être copiés dans un projet ni
enregistrés dans les journaux. Les profils devraient référencer les fichiers
de clés ou les alias de `~/.ssh/config`.

## Plan de migration

### Étape 1 — Stabiliser le contrôleur actuel

Conserver `tools/rlidar2map_CLI.py` comme référence testée et maintenir ses tests de
reprise, synchronisation, interruption, échec et purge.

### Étape 2 — Extraire le moteur

Déplacer la logique réutilisable vers un module indépendant, par exemple
`lidar2map_remote.py`, sans changer l'interface publique de
`rlidar2map_CLI.py`.

### Étape 3 — Ajouter le dispatch dans lidar2map

Ajouter le pré-analyseur `--remote`, exposer les options `--remote-*` dans
`--help`, puis transmettre uniquement les paramètres métier au processus de la
VM.

### Étape 4 — Unifier la configuration et le GUI

Ajouter des profils de VM facultatifs et présenter les runs distants dans le
GUI sans supprimer les commandes CLI.

### Étape 5 — Extensions éventuelles

Une fois le mode mono-VM stabilisé, la même abstraction pourrait piloter
plusieurs workers pour les calculs découpés. Cette extension ne doit pas
compliquer la première intégration.

## Critères d'acceptation

L'évolution sera considérée prête lorsque :

- toutes les commandes locales existantes produisent le même comportement ;
- une commande `lidar2map --remote ...` lance et surveille un run complet ;
- fermer puis relancer le contrôleur reprend la synchronisation ;
- les options distantes sont absentes de la commande exécutée sur la VM ;
- `rlidar2map_CLI.py` reste le point d'entrée public documenté ;
- les tests couvrent local, distant, reprise, échec SSH, échec lidar2map,
  synchronisation finale et purge ;
- la documentation distingue clairement les syntaxes actuelle et future.
