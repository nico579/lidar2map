#!/bin/bash
#
# rlidar2map_GUI_vm.sh
# Prépare une VM Ubuntu 24.04 ou 26.04 avec un bureau XFCE accessible en RDP,
# quel que soit l'hébergeur (cloud, serveur dédié ou VM locale).
# Depuis Windows, utiliser "Connexion Bureau à distance" (mstsc), pas un
# client VNC. À exécuter en root juste après création de la VM :
#   sudo bash rlidar2map_GUI_vm.sh
#
# GUI vs CLI, les deux options :
#  - GUI  (ce script)        : bureau distant RDP, on lance lidar2map à la souris.
#  - CLI  (exécutable rlidar2map_CLI) : calcul HEADLESS sans bureau, installé
#                               et lancé depuis l'ordinateur via SSH/tmux. Pour un
#                               serveur de calcul, choisir ce mode.
#
# Ce script (option GUI) :
#  - actualise la liste des paquets (mise à niveau complète optionnelle)
#  - crée un utilisateur non-root avec sudo + accès SSH par clé
#  - installe XFCE + xrdp + xorgxrdp (bureau distant RDP)
#  - installe les libs Qt/XCB nécessaires à la GUI lidar2map
#  - télécharge, vérifie et installe la dernière release lidar2map (binaire)
#  - crée un raccourci sur le bureau
#
# Adapte les variables ci-dessous si besoin avant de lancer.

set -Eeuo pipefail

trap 'echo "ERREUR ligne ${LINENO} : la préparation a échoué." >&2' ERR

# ---------- Variables à adapter ----------
# Le client multiplateforme peut surcharger USERNAME, sinon "userlidar" est utilisé.
USERNAME="${USERNAME:-userlidar}"
# Modes : "default" = mot de passe initial userlidar, "yes" = invite passwd
# distante, "stdin" = mot de passe fourni par le client via l'entrée standard
# SSH, "no" = ne pas configurer de mot de passe.
SET_RDP_PASSWORD="${SET_RDP_PASSWORD:-default}"
DEFAULT_RDP_PASSWORD="${DEFAULT_RDP_PASSWORD:-userlidar}"
# Le client ne met pas à niveau tout Ubuntu par défaut : c'est long et non
# requis pour installer xrdp. UPGRADE_SYSTEM=yes l'active explicitement.
UPGRADE_SYSTEM="${UPGRADE_SYSTEM:-no}"
GITHUB_REPO="nico579/lidar2map"
LIDAR2MAP_ARCHIVE="lidar2map-linux-x86_64.tar.gz"
# La version, l'URL de téléchargement et le checksum SHA256 sont récupérés
# automatiquement depuis la dernière release GitHub (voir étape 6).
# ------------------------------------------

if [[ $EUID -ne 0 ]]; then
  echo "Ce script doit être lancé en root (sudo bash $0)." >&2
  exit 1
fi

if [[ ! "${USERNAME}" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo "Nom d'utilisateur invalide : ${USERNAME}" >&2
  exit 1
fi

if [[ "${SET_RDP_PASSWORD}" != "default" && \
      "${SET_RDP_PASSWORD}" != "yes" && \
      "${SET_RDP_PASSWORD}" != "stdin" && \
      "${SET_RDP_PASSWORD}" != "no" ]]; then
  echo "SET_RDP_PASSWORD doit valoir 'default', 'yes', 'stdin' ou 'no'." >&2
  exit 1
fi

# Lire immédiatement le secret envoyé par le client, avant toute commande apt
# susceptible d'hériter de stdin. La variable n'est pas exportée aux processus.
RDP_PASSWORD_STDIN=""
if [[ "${SET_RDP_PASSWORD}" == "stdin" ]]; then
  if ! IFS= read -r RDP_PASSWORD_STDIN || [[ -z "${RDP_PASSWORD_STDIN}" ]]; then
    echo "Mot de passe RDP absent sur l'entrée standard." >&2
    exit 1
  fi
fi

if [[ "${UPGRADE_SYSTEM}" != "yes" && "${UPGRADE_SYSTEM}" != "no" ]]; then
  echo "UPGRADE_SYSTEM doit valoir 'yes' ou 'no'." >&2
  exit 1
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    echo "ATTENTION : script prévu pour Ubuntu (détecté : ${PRETTY_NAME:-inconnu})."
  elif [[ "${VERSION_ID:-}" != "24.04" && "${VERSION_ID:-}" != "26.04" ]]; then
    echo "ATTENTION : versions prises en charge : Ubuntu 24.04 et 26.04 " \
         "(détecté : ${PRETTY_NAME:-inconnu})."
  fi
fi

APT_LOG="/var/log/rlidar2map_GUI_apt.log"
: > "${APT_LOG}"
run_apt() {
  local label="$1"
  shift
  printf '   %s... ' "${label}"
  if DEBIAN_FRONTEND=noninteractive apt-get -qq "$@" \
      >> "${APT_LOG}" 2>&1; then
    echo "OK"
  else
    echo "ÉCHEC"
    echo "Dernières lignes du journal APT (${APT_LOG}) :" >&2
    tail -n 80 "${APT_LOG}" >&2
    return 1
  fi
}

echo "=== 1/7 : Actualisation des paquets ==="
run_apt "Liste des paquets" update
if [[ "${UPGRADE_SYSTEM}" == "yes" ]]; then
  run_apt "Mise à niveau complète d'Ubuntu" upgrade -y
else
  echo "Mise à niveau complète ignorée (option --upgrade-system pour l'activer)."
fi

echo "=== 2/7 : Création de l'utilisateur ${USERNAME} ==="
if id "${USERNAME}" &>/dev/null; then
  echo "L'utilisateur ${USERNAME} existe déjà, on continue."
else
  adduser --disabled-password --gecos "" "${USERNAME}"
fi
usermod -aG sudo "${USERNAME}"

# Autoriser les mêmes clés publiques que pour le compte SSH ayant lancé sudo
# (ubuntu, debian, admin...) ou root. Ne jamais copier tout ~/.ssh : il pourrait
# contenir des clés privées.
USER_HOME="$(getent passwd "${USERNAME}" | cut -d: -f6)"
SSH_SOURCE_USER="${SUDO_USER:-root}"
if ! id "${SSH_SOURCE_USER}" &>/dev/null; then
  SSH_SOURCE_USER="root"
fi
SSH_SOURCE_HOME="$(getent passwd "${SSH_SOURCE_USER}" | cut -d: -f6)"
SSH_AUTHORIZED_KEYS="${SSH_SOURCE_HOME}/.ssh/authorized_keys"

if [[ -s "${SSH_AUTHORIZED_KEYS}" ]]; then
  install -d -m 700 -o "${USERNAME}" -g "${USERNAME}" "${USER_HOME}/.ssh"
  touch "${USER_HOME}/.ssh/authorized_keys"
  while IFS= read -r ssh_key; do
    [[ -z "${ssh_key}" ]] && continue
    grep -qxF -- "${ssh_key}" "${USER_HOME}/.ssh/authorized_keys" || \
      printf '%s\n' "${ssh_key}" >> "${USER_HOME}/.ssh/authorized_keys"
  done < "${SSH_AUTHORIZED_KEYS}"
  chown "${USERNAME}:${USERNAME}" "${USER_HOME}/.ssh/authorized_keys"
  chmod 600 "${USER_HOME}/.ssh/authorized_keys"
else
  echo "ATTENTION : aucune clé trouvée dans ${SSH_AUTHORIZED_KEYS}."
fi

PASSWORD_STATUS="$(passwd -S "${USERNAME}" | awk '{print $2}')"
if [[ "${SET_RDP_PASSWORD}" == "default" ]]; then
  printf '%s:%s\n' "${USERNAME}" "${DEFAULT_RDP_PASSWORD}" | chpasswd
  echo "Identifiants Linux/RDP configurés : ${USERNAME}/${DEFAULT_RDP_PASSWORD}"
elif [[ "${SET_RDP_PASSWORD}" == "stdin" ]]; then
  printf '%s:%s\n' "${USERNAME}" "${RDP_PASSWORD_STDIN}" | chpasswd
  unset RDP_PASSWORD_STDIN
  echo "Mot de passe Linux/RDP configuré pour ${USERNAME}."
elif [[ "${PASSWORD_STATUS}" != "P" ]]; then
  if [[ "${SET_RDP_PASSWORD}" == "yes" ]]; then
    echo ""
    echo ">>> Définis le mot de passe Linux de ${USERNAME}, nécessaire pour RDP :"
    passwd "${USERNAME}"
  else
    echo "ATTENTION : mot de passe RDP non configuré pendant cette exécution."
    echo "Après l'installation : ssh -t ${USERNAME}@<IP_DU_SERVEUR> passwd"
  fi
else
  echo "Le compte ${USERNAME} possède déjà un mot de passe ; il est conservé."
fi

echo "=== 3/7 : Installation du bureau XFCE + xrdp/Xorg ==="

# Réparer une VM laissée incomplète par une ancienne version du script :
# Ubuntu 26.04 a publié un conflit entre lxqt-panel et lxqt-branding-debian.
# Les nouvelles installations utilisent XFCE et ne rencontrent pas ce conflit.
LXQT_BRANDING_STATUS="$(
  dpkg-query -W -f='${Status}' lxqt-branding-debian 2>/dev/null || true
)"
if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "26.04" && \
      "${LXQT_BRANDING_STATUS}" == "install ok "* ]]; then
  echo "Réparation du conflit lxqt-panel/lxqt-branding-debian d'Ubuntu 26.04..."
  dpkg --remove --force-depends lxqt 2>/dev/null || true
  dpkg --remove --force-depends lxqt-branding-debian
  run_apt "Réparation des paquets" --fix-broken install -y \
    --no-install-recommends
fi

# XFCE est indépendant de Qt mais exécute parfaitement les applications Qt.
# Il est stable avec xrdp sur les différentes versions Ubuntu prises en charge.
run_apt "Bureau XFCE et serveur RDP" install -y --no-install-recommends \
  xfce4 xfce4-terminal xterm dbus-x11 gvfs xdg-utils wmctrl \
  xdg-desktop-portal xdg-desktop-portal-gtk \
  xrdp xorgxrdp xserver-xorg-core

echo "=== 4/7 : Installation des libs Qt/XCB pour lidar2map ==="
run_apt "Bibliothèques Qt/XCB" install -y \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 \
  wget curl jq ca-certificates

# Ubuntu 26.04 fournit libxkbcommon 1.13, qui provoque un segfault lors de la
# saisie clavier avec la version de Qt embarquée par lidar2map. On extrait les
# bibliothèques 1.6 d'Ubuntu 24.04 dans un répertoire isolé : aucun paquet
# système n'est rétrogradé et seules les exécutions de lidar2map les utilisent.
QT_COMPAT_DIR=""
if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "26.04" ]]; then
  QT_COMPAT_DIR="/opt/lidar2map-qt-compat/usr/lib/x86_64-linux-gnu"
  QT_COMPAT_ROOT="/opt/lidar2map-qt-compat"
  XKB_CORE_DEB="$(mktemp /tmp/libxkbcommon0-lidar.XXXXXX.deb)"
  XKB_X11_DEB="$(mktemp /tmp/libxkbcommon-x11-lidar.XXXXXX.deb)"

  wget -qO "${XKB_CORE_DEB}" \
    "https://archive.ubuntu.com/ubuntu/pool/main/libx/libxkbcommon/libxkbcommon0_1.6.0-1build1_amd64.deb"
  wget -qO "${XKB_X11_DEB}" \
    "https://archive.ubuntu.com/ubuntu/pool/main/libx/libxkbcommon/libxkbcommon-x11-0_1.6.0-1build1_amd64.deb"
  printf '%s  %s\n' \
    "2b9caeb423efb540296a1cb20b872cc630c23908407ecb5c1c787a617622d664" \
    "${XKB_CORE_DEB}" | sha256sum -c -
  printf '%s  %s\n' \
    "3befe840ce612ddfc0998d8610c6eed295726722a78e75cd08520bbd75065a23" \
    "${XKB_X11_DEB}" | sha256sum -c -

  install -d -m 755 "${QT_COMPAT_ROOT}"
  dpkg-deb -x "${XKB_CORE_DEB}" "${QT_COMPAT_ROOT}"
  dpkg-deb -x "${XKB_X11_DEB}" "${QT_COMPAT_ROOT}"
  rm -f "${XKB_CORE_DEB}" "${XKB_X11_DEB}"
fi

echo "=== 5/7 : Configuration de la session graphique (${USERNAME}) ==="
# Les répertoires XDG doivent appartenir à l'utilisateur. `install -d` sur un
# ancien sous-dossier (ex. ~/.config/lxqt) pouvait laisser ~/.config à root,
# ce qui empêchait XFCE de créer sa session et provoquait le mode failsafe.
install -d -m 700 -o "${USERNAME}" -g "${USERNAME}" \
  "${USER_HOME}/.config" "${USER_HOME}/.cache"

cat > "${USER_HOME}/.xsession" << 'EOF'
#!/bin/sh
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
export XDG_SESSION_TYPE=x11
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
exec dbus-launch --exit-with-session startxfce4
EOF

chown "${USERNAME}:${USERNAME}" "${USER_HOME}/.xsession"
chmod 700 "${USER_HOME}/.xsession"

# xrdp doit pouvoir lire sa clé TLS (/etc/ssl/private/ssl-cert-snakeoil.key).
usermod -aG ssl-cert xrdp
systemctl enable xrdp
systemctl restart xrdp
if ! systemctl is-active --quiet xrdp; then
  echo "Le service xrdp n'a pas démarré. Diagnostic :" >&2
  systemctl --no-pager --full status xrdp >&2 || true
  exit 1
fi

echo "=== 6/7 : Récupération de la dernière release lidar2map sur GitHub ==="

RELEASE_JSON=$(curl -fsSL \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")

LIDAR2MAP_VERSION=$(jq -er '.tag_name' <<< "${RELEASE_JSON}")
LIDAR2MAP_URL=$(jq -er --arg name "${LIDAR2MAP_ARCHIVE}" \
  '.assets[] | select(.name==$name) | .browser_download_url' \
  <<< "${RELEASE_JSON}" || true)

if [[ -z "${LIDAR2MAP_URL}" || "${LIDAR2MAP_URL}" == "null" ]]; then
  echo "Impossible de trouver l'asset ${LIDAR2MAP_ARCHIVE} dans la dernière release. Abandon." >&2
  exit 1
fi

# Le SHA256 attendu est publié dans le texte de la release (tableau de téléchargements) ;
# on l'extrait au mieux, sans bloquer le script si le format venait à changer.
LIDAR2MAP_SHA256=$(jq -r '.body // ""' <<< "${RELEASE_JSON}" \
  | grep -iF "${LIDAR2MAP_ARCHIVE}" \
  | grep -oE '[a-f0-9]{64}' \
  | head -n1 || true)

echo "Version détectée : ${LIDAR2MAP_VERSION}"
echo "URL de téléchargement : ${LIDAR2MAP_URL}"

echo "=== 6b/7 : Téléchargement ==="
su - "${USERNAME}" -c "
  set -e
  cd ~
  wget -q --https-only '${LIDAR2MAP_URL}' -O '${LIDAR2MAP_ARCHIVE}'
"

if [[ -n "${LIDAR2MAP_SHA256}" ]]; then
  echo "=== 6c/7 : Vérification du checksum ==="
  ACTUAL_SHA256=$(su - "${USERNAME}" -c "sha256sum ~/${LIDAR2MAP_ARCHIVE} | awk '{print \$1}'")
  if [[ "${ACTUAL_SHA256}" != "${LIDAR2MAP_SHA256}" ]]; then
    echo "ERREUR : checksum invalide !" >&2
    echo "  Attendu : ${LIDAR2MAP_SHA256}" >&2
    echo "  Obtenu  : ${ACTUAL_SHA256}" >&2
    exit 1
  fi
  echo "Checksum OK."
else
  echo "Checksum non trouvé automatiquement dans la release, vérification ignorée."
  echo "Tu peux comparer manuellement avec la valeur publiée sur :"
  echo "https://github.com/${GITHUB_REPO}/releases/tag/${LIDAR2MAP_VERSION}"
fi

echo "=== 6d/7 : Extraction ==="
INSTALL_DIR="${USER_HOME}/lidar2map-linux-x86_64"
su - "${USERNAME}" -c "
  set -e
  cd ~
  tar xzf '${LIDAR2MAP_ARCHIVE}'
  rm '${LIDAR2MAP_ARCHIVE}'
"

if [[ ! -x "${INSTALL_DIR}/lidar2map" ]]; then
  echo "ERREUR : exécutable lidar2map absent après extraction." >&2
  exit 1
fi

echo "=== 7/7 : Création du raccourci bureau ==="
install -d -m 700 -o "${USERNAME}" -g "${USERNAME}" \
  "${USER_HOME}/Desktop" \
  "${USER_HOME}/.local" \
  "${USER_HOME}/.local/bin" \
  "${USER_HOME}/.local/share" \
  "${USER_HOME}/.config/autostart"

cat > "${USER_HOME}/Desktop/lidar2map.desktop" << EOF
[Desktop Entry]
Type=Application
Name=lidar2map
Exec=${USER_HOME}/.local/bin/lidar2map-gui
Path=${INSTALL_DIR}
Terminal=false
Categories=Utility;
EOF

cat > "${USER_HOME}/.local/bin/lidar2map-gui" << EOF
#!/bin/sh
if [ -n "${QT_COMPAT_DIR}" ]; then
  export LD_LIBRARY_PATH="${QT_COMPAT_DIR}:\${LD_LIBRARY_PATH:-}"
fi
# La taille Linux par défaut de lidar2map (1300x1000) dépasse souvent la
# résolution d'une session RDP. Ajuster sa géométrie à l'écran, sans la laisser
# maximisée, garde la barre de titre et le panneau de logs dans la zone visible.
(
  sleep 2
  screen="\$(xrandr --current 2>/dev/null | awk '/\*/ {print \$1; exit}')"
  screen_w="\${screen%x*}"
  screen_h="\${screen#*x}"
  case "\${screen_w}:\${screen_h}" in
    *[!0-9:]*|:*) screen_w=1364; screen_h=768 ;;
  esac
  window_w=\$((screen_w - 80))
  window_h=\$((screen_h - 140))
  [ "\${window_w}" -lt 1000 ] && window_w=1000
  [ "\${window_h}" -lt 600 ] && window_h=600
  wmctrl -r "lidar2map v" -b remove,maximized_vert,maximized_horz || true
  wmctrl -r "lidar2map v" -e "0,40,60,\${window_w},\${window_h}" || true
) >/dev/null 2>&1 &
exec "${INSTALL_DIR}/lidar2map" "\$@"
EOF

# XFCE ne considère pas forcément un fichier .desktop comme fiable avec le
# seul bit exécutable. Il mémorise aussi le SHA-256 du fichier dans les
# métadonnées GVFS. Ces métadonnées nécessitent la session D-Bus graphique :
# un petit autostart les crée donc à la première connexion, puis se supprime.
cat > "${USER_HOME}/.local/bin/trust-lidar2map-launcher" << 'EOF'
#!/bin/sh
launcher="${HOME}/Desktop/lidar2map.desktop"
[ -f "${launcher}" ] || exit 0

checksum="$(sha256sum "${launcher}" | awk '{print $1}')"
if gio set -t string "${launcher}" metadata::xfce-exe-checksum "${checksum}"; then
  rm -f "${HOME}/.config/autostart/lidar2map-trust.desktop"
  rm -f "$0"
  xfdesktop --reload >/dev/null 2>&1 || true
fi
EOF

cat > "${USER_HOME}/.config/autostart/lidar2map-trust.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Validation du raccourci lidar2map
Exec=${USER_HOME}/.local/bin/trust-lidar2map-launcher
OnlyShowIn=XFCE;
NoDisplay=true
Terminal=false
EOF

chown "${USERNAME}:${USERNAME}" \
  "${USER_HOME}/Desktop/lidar2map.desktop" \
  "${USER_HOME}/.local/bin/lidar2map-gui" \
  "${USER_HOME}/.local/bin/trust-lidar2map-launcher" \
  "${USER_HOME}/.config/autostart/lidar2map-trust.desktop"
chmod 755 \
  "${USER_HOME}/Desktop/lidar2map.desktop" \
  "${USER_HOME}/.local/bin/lidar2map-gui" \
  "${USER_HOME}/.local/bin/trust-lidar2map-launcher"
chmod 600 "${USER_HOME}/.config/autostart/lidar2map-trust.desktop"

echo ""
echo "=================================================="
echo " Configuration terminée."
echo ""
echo " - Connexion SSH : ssh ${USERNAME}@<IP_DU_SERVEUR>"
echo " - Connexion RDP : mstsc -> <IP_DU_SERVEUR>:3389"
if [[ "${SET_RDP_PASSWORD}" == "default" ]]; then
  echo "                    compte par défaut : ${USERNAME}/${DEFAULT_RDP_PASSWORD}"
else
  echo "                    utilisateur ${USERNAME} + son mot de passe Linux"
fi
echo "                    choisir la session Xorg si xrdp le demande"
echo " - lidar2map installé dans : ${INSTALL_DIR}"
echo " - Pour changer le mot de passe :"
echo "   ssh -t ${USERNAME}@<IP_DU_SERVEUR> passwd"
echo ""
echo " Alternative sans exposer 3389 (tunnel depuis un terminal local) :"
echo "   ssh -N -L 13389:localhost:3389 ${USERNAME}@<IP_DU_SERVEUR>"
echo "   puis mstsc -> localhost:13389 (le mot de passe RDP reste requis)"
echo ""
echo " Rappel : configure le pare-feu du fournisseur ou de la VM pour autoriser"
echo " TCP 22 (SSH) et TCP 3389 (RDP), si possible uniquement depuis"
echo " l'adresse IP de ton ordinateur. Sur un réseau local, vérifie aussi le routage."
echo "=================================================="
