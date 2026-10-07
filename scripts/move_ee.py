#!/usr/bin/env python
"""Move the SO-101 follower gripper by a relative Cartesian offset (base frame, metres).

Usage (depuis la racine du depot, dans `nix develop`) :
    python scripts/move_ee.py --dz 0.01            # monte de 1 cm
    python scripts/move_ee.py --dx 0.02 --dry-run  # calcule sans bouger

Axes (repere base URDF) : x vers l'avant, y vers la gauche, z vers le haut.
L'orientation de la pince est conservee au mieux (priorite a la position).

Necessite `placo` (cinematique inverse), qui n'est pas encore empaquete dans nixpkgs :
ce script ne tourne donc pas tel quel dans le flake.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

from lerobot.model.kinematics import RobotKinematics
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

ROOT = Path(__file__).resolve().parent.parent
URDF = ROOT / "urdf/SO101/so101_new_calib.urdf"
FOLLOWER_PORT = os.environ.get("LEROBOT_FOLLOWER_PORT", "")  # alias /dev/serial/by-id
ARM_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]

# Garde-fous
MAX_DELTA_M = 0.05  # deplacement max par appel
MAX_IK_ERR_M = 0.005  # au-dela : cible jugee hors d'atteinte
MAX_JOINT_TRAVEL_DEG = 45.0  # rotation max d'une articulation par appel
IK_ITERS = 20  # le solveur placo fait un pas par appel


def solve_ik(kin: RobotKinematics, q_start: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
    """Iterate IK from q_start until the position error is below 0.1 mm."""
    q = q_start
    for _ in range(IK_ITERS):
        q = kin.inverse_kinematics(q, target, orientation_weight=0.01)
        err = float(np.linalg.norm(kin.forward_kinematics(q)[:3, 3] - target[:3, 3]))
        if err < 1e-4:
            break
    return q, err


def read_arm(robot: SO101Follower) -> np.ndarray:
    obs = robot.get_observation()
    return np.array([obs[f"{j}.pos"] for j in ARM_JOINTS], dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dx", type=float, default=0.0, help="metres, vers l'avant")
    parser.add_argument("--dy", type=float, default=0.0, help="metres, vers la gauche")
    parser.add_argument("--dz", type=float, default=0.0, help="metres, vers le haut")
    parser.add_argument("--steps", type=int, default=30, help="nb de points de trajectoire (30 = 1 s)")
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche, n'envoie rien")
    parser.add_argument("--port", default=FOLLOWER_PORT)
    parser.add_argument("--id", default="None", help="nom du fichier de calibration (sans .json)")
    args = parser.parse_args()

    delta = np.array([args.dx, args.dy, args.dz])
    if np.linalg.norm(delta) > MAX_DELTA_M:
        print(f"Refus : deplacement {np.linalg.norm(delta)*100:.1f} cm > {MAX_DELTA_M*100:.0f} cm max par appel")
        return 1

    kin = RobotKinematics(str(URDF), "gripper_frame_link", ARM_JOINTS)
    # max_relative_target : aucun moteur ne peut sauter de plus de 5 deg en une commande
    # disable_torque_on_disconnect=False : le bras tient sa position apres le script
    # (sinon il retombe) ; couper l'alim moteurs pour le relacher
    robot = SO101Follower(
        SO101FollowerConfig(
            port=args.port,
            id=args.id,
            use_degrees=True,
            max_relative_target=5.0,
            disable_torque_on_disconnect=False,
        )
    )
    if args.dry_run:
        robot.bus.connect()  # lecture seule : pas de configure(), donc couple inchange
    else:
        robot.connect(calibrate=False)
    if not robot.is_calibrated:
        print(f"Refus : calibration '{args.id}' absente ou differente de celle des moteurs")
        robot.disconnect()
        return 1

    try:
        q0 = read_arm(robot)
        T0 = kin.forward_kinematics(q0)
        print(f"Articulations (deg) : {np.round(q0, 1)}")
        print(f"Pince xyz (m)       : {np.round(T0[:3, 3], 4)}")

        # Trajectoire : interpolation lineaire en cartesien, IK a chaque pas
        waypoints = []
        q = q0
        for i in range(1, args.steps + 1):
            T = T0.copy()
            T[:3, 3] += delta * i / args.steps
            q, err = solve_ik(kin, q, T)
            if err > MAX_IK_ERR_M:
                print(f"Refus : cible hors d'atteinte (erreur IK {err*1000:.1f} mm au pas {i})")
                return 1
            waypoints.append(q)

        travel = np.abs(waypoints[-1] - q0)
        print(f"Cible xyz (m)       : {np.round(T0[:3, 3] + delta, 4)}")
        print(f"Articulations cible : {np.round(waypoints[-1], 1)}")
        print(f"Rotation (deg)      : {dict(zip(ARM_JOINTS, np.round(travel, 1)))}")
        if travel.max() > MAX_JOINT_TRAVEL_DEG:
            print(f"Refus : une articulation tournerait de {travel.max():.0f} deg > {MAX_JOINT_TRAVEL_DEG:.0f}")
            return 1

        if args.dry_run:
            print("Dry-run : rien envoye.")
            return 0

        # La pince n'est pas envoyee : elle garde sa position.
        # La cible finale est repetee 0,5 s : le bridage a 5 deg se calcule depuis la
        # position mesuree, un moteur en retard verrait sinon son dernier pas raccourci.
        for q in waypoints + [waypoints[-1]] * 15:
            robot.send_action({f"{j}.pos": float(v) for j, v in zip(ARM_JOINTS, q)})
            time.sleep(1 / 30)

        reached = kin.forward_kinematics(read_arm(robot))[:3, 3]
        err = np.linalg.norm(reached - (T0[:3, 3] + delta))
        print(f"Atteint xyz (m)     : {np.round(reached, 4)}  (ecart {err*1000:.1f} mm)")
        return 0
    finally:
        robot.disconnect()


if __name__ == "__main__":
    sys.exit(main())
