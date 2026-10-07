#!/usr/bin/env bash
# Script de téléopération simple (sans enregistrement)
# Usage: ./teleoperate.sh

set -euo pipefail

# Charger la config
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

echo "=== Téléopération SO-101 ==="
echo "Leader: ${LEADER_PORT}"
echo "Follower: ${FOLLOWER_PORT}"
echo ""
echo "Ctrl+C pour arrêter"
echo ""

# Vérification des ports
check_port "${LEADER_PORT}" "Leader" || exit 1
check_port "${FOLLOWER_PORT}" "Follower" || exit 1

# Lancement de la téléopération
lerobot-teleoperate \
    --robot.type so101_follower \
    --robot.port "${FOLLOWER_PORT}" \
    --teleop.type so101_leader \
    --teleop.port "${LEADER_PORT}"
