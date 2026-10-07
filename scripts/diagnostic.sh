#!/usr/bin/env bash
# Script de diagnostic complet pour SO-101
# Usage: ./diagnostic.sh

set -euo pipefail

# Charger la config
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Diagnostic SO-101 LeRobot                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# === 1. Ports série ===
echo "┌─ Ports série ─────────────────────────────────────────────────"
echo "│"

if [[ -e "${LEADER_PORT}" ]]; then
    echo "│  ✓ Leader:   ${LEADER_PORT}"
else
    echo "│  ✗ Leader:   ${LEADER_PORT} (NON TROUVÉ)"
    ERRORS=$((ERRORS + 1))
fi

if [[ -e "${FOLLOWER_PORT}" ]]; then
    echo "│  ✓ Follower: ${FOLLOWER_PORT}"
else
    echo "│  ✗ Follower: ${FOLLOWER_PORT} (NON TROUVÉ)"
    ERRORS=$((ERRORS + 1))
fi

# Liste tous les ports série disponibles
echo "│"
echo "│  Ports disponibles:"
for port in /dev/serial/by-id/* /dev/ttyACM* /dev/ttyUSB*; do
    if [[ -e "$port" ]]; then
        echo "│    - $port"
    fi
done || echo "│    (aucun)"
echo "│"

# === 2. Calibrations ===
echo "├─ Calibrations ────────────────────────────────────────────────"
echo "│"

CALIB_FOLLOWER=$(get_calibration_path "robot" "so101_follower")
CALIB_LEADER=$(get_calibration_path "teleoperator" "so101_leader")

if [[ -f "${CALIB_FOLLOWER}" ]]; then
    echo "│  ✓ Follower: ${CALIB_FOLLOWER}"
else
    echo "│  ✗ Follower: NON CALIBRÉ"
    echo "│    → lerobot-calibrate --robot.type so101_follower --robot.port ${FOLLOWER_PORT}"
    ERRORS=$((ERRORS + 1))
fi

if [[ -f "${CALIB_LEADER}" ]]; then
    echo "│  ✓ Leader:   ${CALIB_LEADER}"
else
    echo "│  ✗ Leader:   NON CALIBRÉ"
    echo "│    → lerobot-calibrate --teleop.type so101_leader --teleop.port ${LEADER_PORT}"
    ERRORS=$((ERRORS + 1))
fi
echo "│"

# === 3. Caméra ===
echo "├─ Caméra ──────────────────────────────────────────────────────"
echo "│"
echo "│  Config: ${CAMERA_INDEX} (${CAMERA_WIDTH}x${CAMERA_HEIGHT}@${CAMERA_FPS}fps)"
echo "│"

# Test rapide de la caméra
CAMERA_OK=$(python - "${CAMERA_INDEX}" <<'PY' 2>/dev/null || echo "error"
import sys, cv2
cam = sys.argv[1]
cap = cv2.VideoCapture(int(cam) if cam.isdigit() else cam)
if cap.isOpened():
    ret, _ = cap.read()
    cap.release()
    print('ok' if ret else 'no_frame')
else:
    print('no_open')
PY
)

case "${CAMERA_OK}" in
    "ok")
        echo "│  ✓ Caméra ${CAMERA_INDEX} fonctionnelle"
        ;;
    "no_frame")
        echo "│  ✗ Caméra ${CAMERA_INDEX} ouverte mais pas de frame"
        ERRORS=$((ERRORS + 1))
        ;;
    "no_open")
        echo "│  ✗ Caméra ${CAMERA_INDEX} non accessible"
        echo "│    → Exécuter ./find_cameras.sh puis définir LEROBOT_CAMERA (ou services.lerobot.camera)"
        ERRORS=$((ERRORS + 1))
        ;;
    *)
        echo "│  ? Erreur lors du test caméra (OpenCV non disponible?)"
        ;;
esac
echo "│"

# === 4. Datasets existants ===
echo "├─ Datasets ────────────────────────────────────────────────────"
echo "│"

DATASETS_DIR="${HF_CACHE}/${HF_USER}"
if [[ -d "${DATASETS_DIR}" ]]; then
    DATASETS=$(ls -1 "${DATASETS_DIR}" 2>/dev/null || true)
    if [[ -n "${DATASETS}" ]]; then
        while IFS= read -r ds; do
            EPISODES=$(ls -1 "${DATASETS_DIR}/${ds}/data" 2>/dev/null | wc -l || echo "?")
            echo "│  • ${ds} (${EPISODES} fichiers)"
        done <<< "${DATASETS}"
    else
        echo "│  (aucun dataset)"
    fi
else
    echo "│  (aucun dataset)"
fi
echo "│"

# === 5. Modèles entraînés ===
echo "├─ Modèles entraînés ───────────────────────────────────────────"
echo "│"

OUTPUTS_DIR="${SCRIPT_DIR}/../outputs"
if [[ -d "${OUTPUTS_DIR}" ]]; then
    for model_dir in "${OUTPUTS_DIR}"/*/; do
        if [[ -d "${model_dir}checkpoints" ]]; then
            MODEL_NAME=$(basename "${model_dir}")
            CHECKPOINTS=$(ls -1 "${model_dir}checkpoints" 2>/dev/null | tail -1 || echo "aucun")
            echo "│  • ${MODEL_NAME} (dernier: ${CHECKPOINTS})"
        fi
    done
    if [[ ! -d "${OUTPUTS_DIR}"/*/checkpoints ]]; then
        echo "│  (aucun modèle)"
    fi
else
    echo "│  (aucun modèle)"
fi
echo "│"

# === 6. Moteurs (si ports disponibles) ===
echo "├─ Test moteurs ────────────────────────────────────────────────"
echo "│"

if [[ -e "${FOLLOWER_PORT}" ]]; then
    MOTORS=$(python -c "
from lerobot.motors.feetech import FeetechMotorsBus
try:
    result = FeetechMotorsBus.scan_port('${FOLLOWER_PORT}')
    if result:
        for baud, ids in result.items():
            print(f'  Baudrate {baud}: moteurs {ids}')
    else:
        print('  Aucun moteur détecté')
except Exception as e:
    print(f'  Erreur: {e}')
" 2>/dev/null || echo "  (scan non disponible)")
    echo "│  Follower (${FOLLOWER_PORT}):"
    echo "${MOTORS}" | while read line; do echo "│  ${line}"; done
else
    echo "│  Follower: port non connecté"
fi
echo "│"

# === Résumé ===
echo "└─────────────────────────────────────────────────────────────────"
echo ""

if [[ ${ERRORS} -eq 0 ]]; then
    echo "✓ Tout est prêt!"
else
    echo "✗ ${ERRORS} problème(s) détecté(s)"
fi
