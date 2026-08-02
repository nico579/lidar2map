# rlidar2map : utiliser lidar2map sur une VM Ubuntu

`rlidar2map_GUI` et `rlidar2map_CLI` sont deux clients distants distincts. Ils
prennent en charge les VM x86-64 sous Ubuntu 24.04 LTS et Ubuntu 26.04 LTS,
quel que soit leur fournisseur, y compris une VM locale.

- `rlidar2map_GUI` installe un bureau XFCE accessible par RDP et permet
  d'utiliser l'interface graphique complète de lidar2map.
- `rlidar2map_CLI` lance des calculs sans bureau dans `tmux`, les surveille et
  recopie progressivement les résultats sur l'ordinateur local.

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

## rlidar2map_GUI : bureau XFCE et RDP

### Depuis un exécutable GitHub

Lancer `rlidar2map_GUI` puis saisir l'adresse IP de la VM. C'est la seule
question avec les valeurs par défaut :

- compte administrateur SSH : `root` ;
- compte Linux/RDP créé : `userlidar` ;
- mot de passe initial : `userlidar` ;
- clé SSH : clé OpenSSH par défaut de l'ordinateur local.

Le client supprime automatiquement l'ancienne empreinte SSH associée à cette
adresse IP, accepte la nouvelle empreinte, copie le script de préparation puis
l'exécute. Il installe XFCE, xrdp, Xorg, les bibliothèques Qt/XCB, la dernière
release lidar2map et un raccourci de bureau sécurisé. Sur Ubuntu 26.04, il
applique aussi l'isolation des bibliothèques de compatibilité Qt nécessaires à
la saisie clavier.

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
l'utilisateur n'a ni à le télécharger ni à le lancer manuellement.

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

## Construction et publication GitHub

La matrice de `.github/workflows/release.yml` construit les deux clients avec
PyInstaller sur leurs systèmes natifs. Chaque release contient :

- Windows x86-64 : `rlidar2map_GUI-windows-x86_64.zip` et
  `rlidar2map_CLI-windows-x86_64.zip` ;
- Linux x86-64 : `rlidar2map_GUI-linux-x86_64.tar.gz` et
  `rlidar2map_CLI-linux-x86_64.tar.gz` ;
- macOS Apple Silicon : `rlidar2map_GUI-macos-arm64.zip` et
  `rlidar2map_CLI-macos-arm64.zip` ;
- macOS Intel : `rlidar2map_GUI-macos-x86_64.zip` et
  `rlidar2map_CLI-macos-x86_64.zip`.

La page de release affiche la somme SHA-256 de chaque archive.
