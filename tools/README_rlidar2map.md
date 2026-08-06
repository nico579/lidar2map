# rlidar2map : utiliser lidar2map sur une VM Ubuntu

`rlidar2map_GUI` et `rlidar2map_CLI` sont deux clients distants distincts. Ils
prennent en charge les VM x86-64 sous Ubuntu 24.04 LTS et Ubuntu 26.04 LTS,
quel que soit leur fournisseur, y compris une VM locale.

- `rlidar2map_GUI` installe un bureau XFCE accessible par RDP et permet
  d'utiliser l'interface graphique complète de lidar2map.
- `rlidar2map_CLI` lance des calculs sans bureau dans `tmux`, les surveille et
  recopie progressivement les résultats sur l'ordinateur local.

Depuis leur intégration, les deux clients sont embarqués dans l'exécutable
lidar2map : plus d'archive séparée à télécharger. `lidar2map --remote-gui` et
`lidar2map --remote-cli` acceptent exactement les mêmes arguments que les
exemples ci-dessous (remplacer `rlidar2map_GUI`/`rlidar2map_CLI` par
`lidar2map --remote-gui`/`lidar2map --remote-cli`). Les binaires autonomes
`rlidar2map_GUI`/`rlidar2map_CLI` restent utilisables en standalone à partir
des sources (`python tools/rlidar2map_CLI.py ...`) pour le développement.

Les exécutables autonomes publiés dans les releases GitHub embarquent Python.
Pour exécuter les sources, utiliser Python 3.8 ou plus récent.

## Prérequis communs

La VM doit être neuve ou dans un état cohérent, joignable en SSH et disposer
d'un accès Internet. L'ordinateur Windows, Linux ou macOS doit fournir le
client OpenSSH `ssh`; le mode GUI
utilise aussi `scp` et `ssh-keygen`.

L'authentification SSH peut utiliser le mot de passe du compte administrateur
ou une clé privée. Une clé SSH est recommandée pour éviter plusieurs demandes
de mot de passe. Les commandes d'installation sont exécutées avec `root`, ou
avec un compte disposant de `sudo` sans interaction.

Autoriser uniquement les ports nécessaires dans le pare-feu :

- TCP 22 pour SSH dans les deux modes ;
- TCP 3389 pour RDP dans le mode GUI, de préférence limité à l'adresse IP de
  l'ordinateur utilisateur.

### Préparer une clé SSH selon la plateforme

Le plus simple est d'ajouter la clé publique de l'ordinateur au moment de la
création de la VM (la plupart des fournisseurs cloud le proposent). Sur une
VM déjà en service, la préparation dépend de la plateforme d'où `rlidar2map_GUI`
ou `rlidar2map_CLI` sont lancés.

**Windows** : le client OpenSSH utilise par défaut la clé du profil
utilisateur, généralement `%USERPROFILE%\.ssh\id_ed25519`. Si elle n'existe pas
encore :

```powershell
ssh-keygen -t ed25519
```

**WSL (Ubuntu sous Windows)** : filesystem séparé de l'hôte Windows, la clé
Windows n'y est pas visible directement. La copier dans le filesystem natif de
WSL, pas juste la référencer via `/mnt/c/...` dont les permissions NTFS sont
trop ouvertes pour SSH (erreur « UNPROTECTED PRIVATE KEY FILE ») :

```bash
mkdir -p ~/.ssh
cp /mnt/c/Users/<utilisateur>/.ssh/id_ed25519     ~/.ssh/id_ed25519
cp /mnt/c/Users/<utilisateur>/.ssh/id_ed25519.pub ~/.ssh/id_ed25519.pub
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

**macOS / Linux natif** : machine physiquement distincte, préférer une
nouvelle clé à la copie d'une clé privée existante d'un ordinateur à l'autre :

```bash
ssh-keygen -t ed25519
ssh-copy-id root@<IP_DE_LA_VM>
```

`ssh-copy-id` fonctionne directement si le mot de passe root est encore actif
sur la VM (il le demande une fois). S'il a été désactivé, ajouter la clé
publique depuis un ordinateur déjà approuvé par la VM :

```bash
ssh root@<IP_DE_LA_VM> "echo '<contenu de id_ed25519.pub>' >> ~/.ssh/authorized_keys"
```

Dans les trois cas, une fois la clé en place à son emplacement par défaut,
`rlidar2map_GUI`/`rlidar2map_CLI` la détectent automatiquement sans argument
supplémentaire ; `--identity` ne sert que pour une clé à un autre emplacement.

## rlidar2map_GUI : bureau XFCE et RDP

### Depuis un exécutable GitHub

Lancer `rlidar2map_GUI` puis saisir l'adresse IP de la VM. C'est la seule
question avec les valeurs par défaut :

- compte administrateur SSH : `root` ;
- compte Linux/RDP créé : `userlidar` ;
- mot de passe initial : `userlidar` ;
- clé SSH : clé OpenSSH par défaut de l'ordinateur local.

Dès le démarrage, toutes les sorties sont ajoutées au fichier
`rlidar2map_GUI.log` placé à côté de l'exécutable. Ce journal contient aussi les
messages de `ssh`, `scp` et du programme d'installation Ubuntu. Sous Windows,
la fenêtre reste ouverte après une erreur afin de laisser le temps de lire le
diagnostic et l'emplacement du journal.

Le client supprime automatiquement l'ancienne empreinte SSH associée à cette
adresse IP, accepte la nouvelle empreinte, copie le script de préparation puis
l'exécute. Il installe XFCE, xrdp, Xorg, les bibliothèques Qt/XCB, la dernière
release lidar2map et un raccourci de bureau sécurisé. Sur Ubuntu 26.04, il
applique aussi l'isolation des bibliothèques de compatibilité Qt nécessaires à
la saisie clavier.

Le raccourci utilise la notification de démarrage XFCE : après un double-clic,
le pointeur affiche l'état occupé jusqu'à l'apparition de la fenêtre Qt (ou
jusqu'au délai de sécurité du bureau si l'application ne démarre pas).

À la fin, il ouvre automatiquement le client RDP :

- Windows : Connexion Bureau à distance (`mstsc`) ;
- Linux : FreeRDP, ou Remmina si FreeRDP est absent ;
- macOS : Windows App via un fichier `.rdp`.

Le compte initial est `userlidar/userlidar`. Changer son mot de passe après le
premier accès :

```bash
ssh -t userlidar@192.0.2.10 passwd
```

Options avancées :

```text
rlidar2map_GUI --help
rlidar2map_GUI --ip 192.0.2.10 --identity ~/.ssh/id_ed25519
rlidar2map_GUI --ip 192.0.2.10 --upgrade-system
rlidar2map_GUI --ip 192.0.2.10 --no-rdp
```

`--upgrade-system` est facultatif : la liste APT est toujours actualisée, mais
la mise à niveau complète d'Ubuntu n'est pas nécessaire à l'installation.

Le build `rlidar2map_GUI` embarque le script interne
`rlidar2map_GUI_vm.sh`. Il l'extrait temporairement puis le copie sur la VM :
l'utilisateur n'a ni à le télécharger ni à le lancer manuellement. Avant la
copie, le client impose systématiquement les fins de ligne Unix `LF`, y compris
si l'archive a été construite sur Windows.

Le journal APT détaillé est enregistré sur la VM dans
`/var/log/rlidar2map_GUI_apt.log`.

## rlidar2map_CLI : calcul distant sans bureau

Le mode CLI n'installe ni XFCE ni xrdp et n'ouvre pas le port 3389. Au premier
lancement, il installe seulement les outils manquants avec APT (`tmux`, et
selon le mode `git`, `python3`, `python3-venv`, `curl` ou `rsync`). Il exécute
`apt-get update`, mais jamais une mise à niveau complète d'Ubuntu.

Lancer un calcul avec le bundle Linux publié :

```bash
rlidar2map_CLI --bundle --session paris root@192.0.2.10 -- \
  --ignlidar --zone-ville Paris --zone-width 5 --telechargement \
  --ombrages lrm --shading lrm:sigma=3 --formats-fichier mbtiles
```

Tous les arguments lidar2map doivent être placés séparément après `--`. Le
contrôleur réserve `--output-dir` afin d'isoler et de synchroniser les sorties.

Modes disponibles :

- `--bundle` télécharge le bundle Linux x86-64 de la dernière release ;
- `--source` clone ou actualise les sources, puis initialise leur environnement
  Python ; c'est le mode par défaut.

Les résultats sont copiés sous
`vm-results/<hôte>/<session>/<run-id>/`. `rsync` est utilisé quand il est
disponible des deux côtés; sinon le client utilise un flux SSH incrémental avec
vérification SHA-256.

Interrompre le client avec `Ctrl-C` n'arrête pas le calcul distant. Pour
reprendre la surveillance sans créer un second calcul :

```bash
rlidar2map_CLI --bundle --session paris root@192.0.2.10
```

Pour recycler une adresse IP dont l'empreinte SSH a changé :

```bash
rlidar2map_CLI --reset-host-key --bundle --session paris \
  root@192.0.2.10 -- --ignlidar --zone-ville Paris
```

Après la fin et la synchronisation, supprimer uniquement les données de ce run
sur la VM :

```bash
rlidar2map_CLI --session paris --purge-remote root@192.0.2.10
```

### Calculs longs, reprise et exécution parallèle

Les arguments lidar2map sont fournis séparément après `--`. La surveillance est
active par défaut : le client attend la fin du calcul dans `tmux`, signale le
succès ou l'échec après une dernière synchronisation, et recopie progressivement
les résultats. `Ctrl-C` n'arrête que le moniteur local. Relancer la même commande,
ou simplement `rlidar2map_CLI --bundle --session paris root@192.0.2.10`, relit
l'état distant sans lancer un second calcul. Une session terminée n'est jamais
relancée implicitement : utiliser un nouveau `--session`, ou `--restart` avec de
nouveaux arguments.

Les résultats sont placés sous `vm-results/<hôte>/<session>/<run-id>/`.
`--local-dir` change cette racine, `--interval` règle la fréquence de surveillance
et `--detach` lance le calcul puis rend immédiatement la main. Si le moniteur est
fermé, `tmux` conserve l'état final et la prochaine reconnexion effectue la copie
finale en attente. Le wrapper publie un état atomique (identifiant, statut, code
de sortie et horodatages) ; les fichiers `.part` sont ignorés, les transferts sont
vérifiés par SHA-256 et le journal est copié à l'état terminal.

Utiliser un `--session` différent pour chaque calcul concurrent sur une même VM.
Le contrôleur isole les résultats et les journaux avec `--output-dir`. Pour une
adresse IP réattribuée à une autre VM, utiliser explicitement `--reset-host-key`.
L'authentification par clé SSH est recommandée quel que soit le fournisseur.

Pour répartir une zone sur plusieurs machines, `--block i/M` sélectionne le
`i`-ème bloc parmi `M` blocs géographiques sans recouvrement :

```bash
rlidar2map_CLI vm1 -- --lidar --laz --zone-department 83 --block 1/3 --download --split-width 5 --cleanup --min-free-gb 20 --shading lrm:sigma=4 --file-formats mbtiles
rlidar2map_CLI vm2 -- --lidar --laz --zone-department 83 --block 2/3 --download --split-width 5 --cleanup --min-free-gb 20 --shading lrm:sigma=4 --file-formats mbtiles
rlidar2map_CLI vm3 -- --lidar --laz --zone-department 83 --block 3/3 --download --split-width 5 --cleanup --min-free-gb 20 --shading lrm:sigma=4 --file-formats mbtiles
```

Chaque machine traite son bloc et synchronise ses fichiers sous `vm-results/`.
`--block` se combine avec `--split-width` : chaque machine peut encore découper
son propre bloc pour limiter l'espace disque. Des IP distinctes permettent aussi
de multiplier les téléchargements parallèles lorsque le portail national limite
le débit par adresse.

### RAM et taille des chunks (--split-cols/--split-rows/--split-width)

Sur un `--lidar` grande zone (département entier), le pic de RAM du calcul
d'ombrage (SVF, openness) suit approximativement la surface d'un chunk après
découpage. Constaté : un chunk d'environ 1150 km² (découpage 3×3 sur un
département) peut atteindre ~31 Go de RSS avec SVF+openness séparés,
suffisant pour déclencher l'OOM killer sur une VM à 32 Go. Repère empirique,
pas une formule garantie (le composite VAT/e4MSTP, qui fusionne SVF+openness
en un seul passage, tolère mieux le même découpage) :

| RAM de la VM | Taille de chunk visée |
|---|---|
| 32 Go | ≤ ~600 km² (découpage plus fin, ex. 4×4 pour un département) |
| 64 Go | ~1150 km² (le 3×3 par défaut passe généralement) |

Un découpage plus fin coûte du temps (passes TMS/VRT/percentiles et coutures
répétées par chunk en plus), pas seulement de la marge RAM — c'est un
compromis, pas un réglage à mettre au maximum par défaut.

## Construction et publication GitHub

`rlidar2map_CLI.py` et `rlidar2map_GUI.py` sont importés par `lidar2map.py`
(dispatch `--remote-cli`/`--remote-gui`, avant le bootstrap et les imports
lourds) et embarqués dans les mêmes specs PyInstaller que lidar2map lui-même
(`lidar2map_win.spec`, `lidar2map_mac.spec`, réutilisée pour Linux). La
matrice de `.github/workflows/release.yml` ne construit donc plus qu'un seul
exécutable par OS/arch ; l'exécution distante est incluse d'office dans
chaque archive `lidar2map-<os>-<arch>.<zip|tar.gz>`.

Les deux `.spec` dédiés (`tools/rlidar2map_CLI.spec`, `tools/rlidar2map_GUI.spec`)
restent disponibles pour builder un binaire standalone en développement, mais
ne sont plus invoqués par la release.

L'icône commune `lidar2map_icon.png` est intégrée à l'exécutable Windows et
macOS, et installée automatiquement sur le raccourci du bureau XFCE par
`rlidar2map_GUI`.

La page de release affiche la somme SHA-256 de chaque archive.
