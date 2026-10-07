#!/usr/bin/env bash
# Script de visualisation d'un dataset enregistré
# Usage: ./visualize.sh [nom_dataset] [numero_episode]

set -euo pipefail

# Charger la config centralisée
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Paramètres
DATASET_NAME="${1:-${DEFAULT_DATASET}}"
EPISODE="${2:-0}"

# Repo ID
REPO_ID="${HF_USER}/${DATASET_NAME}"

echo "=== Visualisation dataset SO-101 ==="
echo "Dataset: ${REPO_ID}"
echo "Épisode: ${EPISODE}"
echo ""

# Vérification du dataset
check_dataset "${DATASET_NAME}" || { echo "Enregistrez d'abord des démonstrations avec ./record.sh"; exit 1; }

# Lancement de la visualisation avec Rerun
lerobot-dataset-viz \
    --repo-id "${REPO_ID}" \
    --root "${HF_CACHE}/${REPO_ID}" \
    --episode-index "${EPISODE}"

echo ""
echo "=== Visualisation terminée ==="
