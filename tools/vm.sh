#!/bin/bash
#
# setup-hetzner-lidar2map.sh
# À exécuter en root, juste après la création d'une VM Hetzner Ubuntu 24.04 fraîche.
# Usage : sudo bash setup-hetzner-lidar2map.sh
#
# Ce script :
#  - met à jour le système
#  - crée un utilisateur non-root avec sudo + accès SSH par clé
#  - installe LXQt + xrdp + Openbox (bureau distant)
#  - installe les libs Qt/XCB nécessaires à lidar2map
#  - télécharge, vérifie et installe la dernière release lidar2map
#  - crée un raccourci sur le bureau
#
# Adapte les variables ci-dessous si besoin avant de lancer.

set -euo pipefail

# ---------- Variables à adapter ----------
USERNAME="nico"
GITHUB_REPO="nico579/lidar2map"
LIDAR2MAP_ARCHIVE="lidar2map-linux-x86_64.tar.gz"
# La version, l'URL de téléchargement et le checksum SHA256 sont récupérés
# automatiquement depuis la dernière release GitHub (voir étape 6).
# ------------------------------------------

if [[ $EUID -ne 0 ]]; then
  echo "Ce script doit être lancé en root (sudo bash $0)." >&2
  exit 1
fi

echo "=== 1/7 : Mise à jour du système ==="
apt update && apt upgrade -y

echo "=== 2/7 : Création de l'utilisateur ${USERNAME} ==="
if id "${USERNAME}" &>/dev/null; then
  echo "L'utilisateur ${USERNAME} existe déjà, on continue."
else
  adduser --disabled-password --gecos "" "${USERNAME}"
fi
usermod -aG sudo "${USERNAME}"

# Copier les clés SSH de root vers le nouvel utilisateur, si présentes
if [[ -d /root/.ssh ]]; then
  rsync --archive --chown="${USERNAME}:${USERNAME}" /root/.ssh "/home/${USERNAME}/"
fi

echo ""
echo ">>> Définis un mot de passe pour ${USERNAME} (nécessaire pour la connexion RDP) :"
passwd "${USERNAME}"

echo "=== 3/7 : Installation du bureau LXQt + xrdp + Openbox ==="
apt install -y lxqt xterm openbox xrdp

echo "=== 4/7 : Installation des libs Qt/XCB pour lidar2map ==="
apt install -y libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 \
  wget curl jq

echo "=== 5/7 : Configuration de la session graphique (${USERNAME}) ==="
su - "${USERNAME}" -c "echo 'startlxqt' > ~/.xsession"
su - "${USERNAME}" -c "mkdir -p ~/.config/lxqt"
su - "${USERNAME}" -c "cat > ~/.config/lxqt/session.conf << 'EOF'
[General]
window_manager=openbox
EOF"

systemctl enable --now xrdp

echo "=== 6/7 : Récupération de la dernière release lidar2map sur GitHub ==="

RELEASE_JSON=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")

LIDAR2MAP_VERSION=$(echo "${RELEASE_JSON}" | jq -r '.tag_name')
LIDAR2MAP_URL=$(echo "${RELEASE_JSON}" | jq -r --arg name "${LIDAR2MAP_ARCHIVE}" '.assets[] | select(.name==$name) | .browser_download_url')

if [[ -z "${LIDAR2MAP_URL}" || "${LIDAR2MAP_URL}" == "null" ]]; then
  echo "Impossible de trouver l'asset ${LIDAR2MAP_ARCHIVE} dans la dernière release. Abandon." >&2
  exit 1
fi

# Le SHA256 attendu est publié dans le texte de la release (tableau de téléchargements) ;
# on l'extrait au mieux, sans bloquer le script si le format venait à changer.
LIDAR2MAP_SHA256=$(echo "${RELEASE_JSON}" | jq -r '.body' \
  | grep -i "${LIDAR2MAP_ARCHIVE}" \
  | grep -oE '[a-f0-9]{64}' \
  | head -n1 || true)

echo "Version détectée : ${LIDAR2MAP_VERSION}"
echo "URL de téléchargement : ${LIDAR2MAP_URL}"

echo "=== 6b/7 : Téléchargement ==="
su - "${USERNAME}" -c "
  set -e
  cd ~
  wget -q '${LIDAR2MAP_URL}' -O '${LIDAR2MAP_ARCHIVE}'
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
su - "${USERNAME}" -c "
  set -e
  cd ~
  tar xzf '${LIDAR2MAP_ARCHIVE}'
  rm '${LIDAR2MAP_ARCHIVE}'
"

echo "=== 7/7 : Création du raccourci bureau ==="
INSTALL_DIR="/home/${USERNAME}/lidar2map-linux-x86_64"
su - "${USERNAME}" -c "
  mkdir -p ~/Desktop
  cat > ~/Desktop/lidar2map.desktop << EOF
[Desktop Entry]
Type=Application
Name=lidar2map
Exec=${INSTALL_DIR}/lidar2map
Path=${INSTALL_DIR}
Terminal=false
Categories=Utility;
EOF
  chmod +x ~/Desktop/lidar2map.desktop
"

echo ""
echo "=================================================="
echo " Configuration terminée."
echo ""
echo " - Connexion SSH : ssh ${USERNAME}@<IP_DU_SERVEUR>"
echo " - Connexion RDP : mstsc -> <IP_DU_SERVEUR>, utilisateur ${USERNAME}"
echo " - lidar2map installé dans : ${INSTALL_DIR}"
echo ""
echo " Rappel : pense à créer un Firewall Hetzner autorisant"
echo " les ports TCP 22 (SSH) et TCP 3389 (RDP), et à l'appliquer"
echo " à ce serveur depuis la console Hetzner si ce n'est pas déjà fait."
echo "=================================================="
