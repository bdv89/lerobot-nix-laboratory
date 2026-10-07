#!/usr/bin/env bash
# Configuration centralisée pour les scripts SO-101
# Sourcer ce fichier : source "$(dirname "$0")/config.sh"

# Lancer les scripts dans l'environnement du flake :  nix develop -c ./scripts/record.sh

# === Ports série ===
# Toujours des alias /dev/serial/by-id (numéro de série du CH340, stable) : l'ordre
# des /dev/ttyACM* s'inverse au rebranchement. Le module NixOS pose ces variables ;
# sinon : auto-détection (à vérifier avec ./diagnostic.sh ou lerobot-find-port).
_by_id() { { ls -1 /dev/serial/by-id/usb-1a86_* 2>/dev/null || true; } | sed -n "$1p"; }
FOLLOWER_PORT="${LEROBOT_FOLLOWER_PORT:-$(_by_id 1)}"
LEADER_PORT="${LEROBOT_LEADER_PORT:-$(_by_id 2)}"

# === Caméra ===
# Chemin (/dev/lerobot_cam, créé par le module NixOS) ou index OpenCV.
# Exécuter ./find_cameras.sh pour le trouver.
CAMERA_INDEX="${LEROBOT_CAMERA:-/dev/lerobot_cam}"
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_FPS=30

# === Dataset ===
DEFAULT_DATASET="so101-demo"
DEFAULT_TASK="Grab the cube"
DEFAULT_NUM_EPISODES=10
HF_CACHE="${HOME}/.cache/huggingface/lerobot"

# === Entraînement ===
DEFAULT_POLICY="act"
DEFAULT_STEPS=50000
BATCH_SIZE=8
SAVE_FREQ=10000
LOG_FREQ=100

# === Utilisateur HuggingFace ===
HF_USER="${HF_USER:-user}"

# === USB autosuspend ===
# Sans ça, Linux suspend les périphériques après 2 s et coupe le signal.
# Sur NixOS, le module services.lerobot le désactive déjà par règle udev ;
# cette fonction ne sert que sur une autre distribution.
disable_usb_autosuspend() {
    for dev in /sys/bus/usb/devices/*/; do
        if [ -f "$dev/product" ]; then
            prod=$(cat "$dev/product" 2>/dev/null)
            if echo "$prod" | grep -qiE "Serial|CAM"; then
                echo "on" | sudo tee "$dev/power/control" > /dev/null 2>&1
                echo "Autosuspend desactive pour: $prod"
            fi
        fi
    done
}

# === Fonctions utilitaires ===

# Construit la config caméra JSON
get_camera_config() {
    local cam="${CAMERA_INDEX}"
    [[ "${cam}" =~ ^[0-9]+$ ]] || cam="\"${cam}\""
    echo "{\"cam\": {\"type\": \"opencv\", \"index_or_path\": ${cam}, \"width\": ${CAMERA_WIDTH}, \"height\": ${CAMERA_HEIGHT}, \"fps\": ${CAMERA_FPS}}}"
}

# Vérifie qu'un port série existe
check_port() {
    local port="$1"
    local name="$2"
    if [[ -z "${port}" || ! -e "${port}" ]]; then
        echo "ERREUR: ${name} non trouvé sur ${port}"
        return 1
    fi
    return 0
}

# Vérifie qu'un dataset existe
check_dataset() {
    local dataset="$1"
    local path="${HF_CACHE}/${HF_USER}/${dataset}"
    if [[ ! -d "${path}" ]]; then
        echo "ERREUR: Dataset non trouvé dans ${path}"
        return 1
    fi
    return 0
}

# Vérifie qu'un checkpoint existe
check_checkpoint() {
    local checkpoint="$1"
    if [[ ! -d "${checkpoint}" ]]; then
        echo "ERREUR: Checkpoint non trouvé dans ${checkpoint}"
        return 1
    fi
    return 0
}

# Chemin de calibration
get_calibration_path() {
    local type="$1"  # "robot" ou "teleoperator"
    local name="$2"  # "so101_follower" ou "so101_leader"
    if [[ "${type}" == "robot" ]]; then
        echo "${HF_CACHE}/calibration/robots/${name}/None.json"
    else
        echo "${HF_CACHE}/calibration/teleoperators/${name}/None.json"
    fi
}
