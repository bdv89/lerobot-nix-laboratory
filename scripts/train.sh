#!/usr/bin/env bash
# Script d'entraînement de politique pour SO-101
# Usage: ./train.sh [nom_dataset] [policy] [steps]

set -euo pipefail

# Charger la config centralisée
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# Paramètres
DATASET_NAME="${1:-${DEFAULT_DATASET}}"
POLICY="${2:-${DEFAULT_POLICY}}"
STEPS="${3:-${DEFAULT_STEPS}}"

# Repo ID et dossier de sortie
REPO_ID="${HF_USER}/${DATASET_NAME}"
OUTPUT_DIR="${SCRIPT_DIR}/../outputs/${DATASET_NAME}-${POLICY}"

echo "=== Entraînement de politique SO-101 ==="
echo "Dataset: ${REPO_ID}"
echo "Politique: ${POLICY}"
echo "Steps: ${STEPS}"
echo "Batch size: ${BATCH_SIZE}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# Vérification du dataset
check_dataset "${DATASET_NAME}" || { echo "Enregistrez d'abord des démonstrations avec ./record.sh"; exit 1; }

# lerobot-train crée le dossier lui-même et refuse d'écraser un run existant
if [[ -e "${OUTPUT_DIR}" ]]; then
    echo "ERREUR: ${OUTPUT_DIR} existe déjà (le supprimer ou changer de nom)"
    exit 1
fi

# Lancement de l'entraînement
lerobot-train \
    --policy.type "${POLICY}" \
    --policy.push_to_hub false \
    --dataset.repo_id "${REPO_ID}" \
    --dataset.root "${HF_CACHE}/${REPO_ID}" \
    --batch_size "${BATCH_SIZE}" \
    --steps "${STEPS}" \
    --save_freq "${SAVE_FREQ}" \
    --log_freq "${LOG_FREQ}" \
    --output_dir "${OUTPUT_DIR}"

echo ""
echo "=== Entraînement terminé ==="
echo "Modèle sauvegardé dans: ${OUTPUT_DIR}/checkpoints/"
