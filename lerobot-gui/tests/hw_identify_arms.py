#!/usr/bin/env python
"""Sonde materielle LECTURE SEULE : quel bras est branche sur quelle carte ?

Aucune ecriture de registre, aucun couple active. Pour chaque port de
SO101Config, lit par moteur : tension d'alimentation, etat du couple,
position brute.

Lecture : ~5 V -> alim du leader, ~12 V -> alim du follower.

Usage (depuis lerobot-gui/) :
    python tests/hw_identify_arms.py            # instantane
    python tests/hw_identify_arms.py --watch 8  # bouge UN bras pendant 8 s
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.diagnostic import SO101Config  # ajoute aussi lerobot/src au path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
PORTS = {"FOLLOWER_PORT": SO101Config.FOLLOWER_PORT, "LEADER_PORT": SO101Config.LEADER_PORT}


def open_bus(port: str) -> FeetechMotorsBus:
    motors = {name: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, name in enumerate(MOTOR_NAMES)}
    bus = FeetechMotorsBus(port=port, motors=motors)
    bus.connect(handshake=False)  # ouvre le port, aucune ecriture
    return bus


def safe_read(bus: FeetechMotorsBus, register: str, motor: str):
    try:
        return bus.read(register, motor, normalize=False, num_retry=2)
    except Exception as e:  # moteur absent / trame corrompue
        return f"ERR({type(e).__name__})"


def read_positions(bus: FeetechMotorsBus) -> dict:
    return {m: safe_read(bus, "Present_Position", m) for m in MOTOR_NAMES}


def snapshot(label: str, bus: FeetechMotorsBus) -> None:
    print(f"\n=== {label}  ({bus.port})")
    print(f"{'moteur':<14}{'tension':>9}{'couple':>8}{'position':>10}")
    volts = []
    for m in MOTOR_NAMES:
        v = safe_read(bus, "Present_Voltage", m)
        t = safe_read(bus, "Torque_Enable", m)
        p = safe_read(bus, "Present_Position", m)
        v_str = f"{v / 10:.1f} V" if isinstance(v, int) else v
        if isinstance(v, int):
            volts.append(v / 10)
        print(f"{m:<14}{v_str:>9}{str(t):>8}{str(p):>10}")
    if volts:
        avg = sum(volts) / len(volts)
        guess = "LEADER (alim ~5 V)" if avg < 8 else "FOLLOWER (alim ~12 V)"
        print(f"-> tension moyenne {avg:.1f} V : ce bras est probablement le {guess}")
    else:
        print("-> aucun moteur ne repond (alim coupee ? cable moteur debranche ?)")


def watch(buses: dict, seconds: float) -> None:
    print(f"\nBouge UN seul bras pendant {seconds:.0f} s...")
    start = {label: read_positions(bus) for label, bus in buses.items()}
    deltas = {label: 0 for label in buses}
    end = time.time() + seconds
    while time.time() < end:
        for label, bus in buses.items():
            for m, p in read_positions(bus).items():
                p0 = start[label][m]
                if isinstance(p, int) and isinstance(p0, int):
                    deltas[label] = max(deltas[label], abs(p - p0))
        time.sleep(0.1)
    for label, d in deltas.items():
        print(f"{label:<14} deplacement max = {d} pas {'<- BOUGE' if d > 50 else ''}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--watch", type=float, default=0, help="duree (s) de detection de mouvement")
    args = parser.parse_args()

    buses = {}
    for label, port in PORTS.items():
        if not Path(port).exists():
            print(f"\n=== {label}  ({port})\n-> port absent : carte non branchee en USB")
            continue
        buses[label] = open_bus(port)

    try:
        for label, bus in buses.items():
            snapshot(label, bus)
        if args.watch and buses:
            watch(buses, args.watch)
    finally:
        for bus in buses.values():
            bus.disconnect(disable_torque=False)  # aucune ecriture a la fermeture
    return 0


if __name__ == "__main__":
    sys.exit(main())
