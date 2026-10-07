#!/usr/bin/env bash
# Script pour détecter les caméras disponibles
# Usage: ./find_cameras.sh

set -euo pipefail

echo "=== Détection des caméras ==="
echo ""

# Méthode 1: LeRobot (si disponible)
echo "1. Via LeRobot:"
lerobot-find-cameras opencv 2>/dev/null || echo "   (non disponible)"
echo ""

# Méthode 2: v4l2-ctl
echo "2. Via v4l2-ctl:"
if command -v v4l2-ctl &> /dev/null; then
    v4l2-ctl --list-devices 2>/dev/null || echo "   Aucun périphérique vidéo"
else
    echo "   (v4l2-ctl non installé)"
fi
echo ""

# Méthode 3: Liste des périphériques /dev/video*
echo "3. Périphériques /dev/video*:"
ls -la /dev/video* 2>/dev/null || echo "   Aucun périphérique vidéo"
echo ""

# Méthode 4: Test OpenCV
echo "4. Test OpenCV (indices 0-5):"
python -c "
import cv2
found = False
for i in range(6):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f'   Index {i}: {w}x{h} @ {fps:.0f} fps')
            found = True
        cap.release()
if not found:
    print('   Aucune caméra détectée')
" 2>/dev/null || echo "   (erreur OpenCV)"

echo ""
echo "=== Fin de la détection ==="
echo "Utilisez l'index trouvé dans CAMERA_INDEX des scripts"
