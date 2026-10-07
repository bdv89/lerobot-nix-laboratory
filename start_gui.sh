#!/usr/bin/env bash
# Lance la GUI LeRobot (http://localhost:8080) depuis le flake de ce dépôt
set -euo pipefail
exec nix run "$(cd "$(dirname "$0")" && pwd)" -- "$@"
