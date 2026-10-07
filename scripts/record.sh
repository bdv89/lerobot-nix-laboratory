#!/usr/bin/env bash
# Script d'enregistrement de démonstrations pour SO-101
# Usage: ./record.sh [nom_dataset] [tache] [nb_episodes]

set -euo pipefail

# Charger la config centralisée
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Paramètres (avec valeurs par défaut de config.sh)
DATASET_NAME="${1:-${DEFAULT_DATASET}}"
TASK="${2:-${DEFAULT_TASK}}"
NUM_EPISODES="${3:-${DEFAULT_NUM_EPISODES}}"

# Repo ID local
REPO_ID="${HF_USER}/${DATASET_NAME}"

echo "=== Enregistrement de démonstrations SO-101 ==="
echo "Dataset: ${REPO_ID}"
echo "Tâche: ${TASK}"
echo "Épisodes: ${NUM_EPISODES}"
echo "Leader: ${LEADER_PORT}"
echo "Follower: ${FOLLOWER_PORT}"
echo "Caméra: ${CAMERA_INDEX} (${CAMERA_WIDTH}x${CAMERA_HEIGHT}@${CAMERA_FPS}fps)"
echo ""

# Vérification des ports série
check_port "${LEADER_PORT}" "Leader" || exit 1
check_port "${FOLLOWER_PORT}" "Follower" || exit 1

# Lancement de l'enregistrement
lerobot-record \
    --robot.type so101_follower \
    --robot.port "${FOLLOWER_PORT}" \
    --robot.cameras "$(get_camera_config)" \
    --teleop.type so101_leader \
    --teleop.port "${LEADER_PORT}" \
    --dataset.repo_id "${REPO_ID}" \
    --dataset.single_task "${TASK}" \
    --dataset.num_episodes "${NUM_EPISODES}" \
    --dataset.push_to_hub false

echo ""
echo "=== Enregistrement terminé ==="
echo "Dataset sauvegardé dans: ${HF_CACHE}/${REPO_ID}/"
