#!/usr/bin/env bash
# Script d'exécution autonome d'une politique entraînée pour SO-101
# Usage: ./run_policy.sh [checkpoint_path] [duree_s] [tache]

set -euo pipefail

# Charger la config centralisée
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Paramètres
CHECKPOINT="${1:-${SCRIPT_DIR}/../outputs/${DEFAULT_DATASET}-${DEFAULT_POLICY}/checkpoints/last/pretrained_model}"
DURATION="${2:-30}"
TASK="${3:-${DEFAULT_TASK}}"

# Accepte aussi le dossier checkpoint parent de pretrained_model/
if [[ -d "${CHECKPOINT}/pretrained_model" ]]; then
    CHECKPOINT="${CHECKPOINT}/pretrained_model"
fi

echo "=== Exécution autonome SO-101 ==="
echo "Checkpoint: ${CHECKPOINT}"
echo "Durée: ${DURATION} s"
echo "Tâche: ${TASK}"
echo "Follower: ${FOLLOWER_PORT}"
echo "Caméra: ${CAMERA_INDEX}"
echo ""

# Vérifications
check_port "${FOLLOWER_PORT}" "Follower" || exit 1
check_checkpoint "${CHECKPOINT}" || { echo "Entraînez d'abord un modèle avec ./train.sh"; exit 1; }

# lerobot-rollout (LeRobot >= 0.5) : la politique pilote le robot, sans enregistrement.
# Pour enregistrer les essais : --strategy.type=episodic + --dataset.* (voir lerobot-rollout --help).
lerobot-rollout \
    --strategy.type base \
    --policy.path "${CHECKPOINT}" \
    --robot.type so101_follower \
    --robot.port "${FOLLOWER_PORT}" \
    --robot.cameras "$(get_camera_config)" \
    --task "${TASK}" \
    --duration "${DURATION}"

echo ""
echo "=== Exécution terminée ==="
