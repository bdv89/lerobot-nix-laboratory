#!/usr/bin/env bash
# Script de replay d'épisode enregistré pour SO-101
# Usage: ./replay.sh [nom_dataset] [numero_episode]

set -euo pipefail

# Charger la config centralisée
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Paramètres
DATASET_NAME="${1:-${DEFAULT_DATASET}}"
EPISODE="${2:-0}"

# Repo ID
REPO_ID="${HF_USER}/${DATASET_NAME}"

echo "=== Replay d'épisode SO-101 ==="
echo "Dataset: ${REPO_ID}"
echo "Épisode: ${EPISODE}"
echo "Follower: ${FOLLOWER_PORT}"
echo ""

# Vérifications
check_port "${FOLLOWER_PORT}" "Follower" || exit 1
check_dataset "${DATASET_NAME}" || { echo "Enregistrez d'abord des démonstrations avec ./record.sh"; exit 1; }

# Lancement du replay
lerobot-replay \
    --robot.type so101_follower \
    --robot.port "${FOLLOWER_PORT}" \
    --dataset.repo_id "${REPO_ID}" \
    --dataset.root "${HF_CACHE}/${REPO_ID}" \
    --dataset.episode "${EPISODE}"

echo ""
echo "=== Replay terminé ==="
