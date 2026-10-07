"""Tests sans materiel : configuration des ports serie SO-101.

Lancer depuis lerobot-gui/ : nix develop -c python -m unittest tests.test_ports -v
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from pathlib import Path

from utils.diagnostic import RobotDiagnostic, SO101Config, _default_port

BY_ID_PREFIX = "/dev/serial/by-id/"


class TestSO101Ports(unittest.TestCase):
    def test_env_var_wins(self):
        # Le module NixOS pose les alias by-id stables dans l'environnement
        port = BY_ID_PREFIX + "usb-1a86_USB_Single_Serial_FOLLOWER-if00"
        with mock.patch.dict("os.environ", {"LEROBOT_FOLLOWER_PORT": port}):
            self.assertEqual(_default_port("LEROBOT_FOLLOWER_PORT", 0), port)

    def test_autodetect_uses_by_id_and_distinct_ports(self):
        # /dev/ttyACMx depend de l'ordre de branchement -> on ne propose que des by-id
        found = [Path(BY_ID_PREFIX + f"usb-1a86_USB_Single_Serial_{sn}-if00") for sn in ("A", "B")]
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(Path, "is_dir", return_value=True), \
                mock.patch.object(Path, "glob", return_value=iter(found)):
            follower = _default_port("LEROBOT_FOLLOWER_PORT", 0)
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(Path, "is_dir", return_value=True), \
                mock.patch.object(Path, "glob", return_value=iter(found)):
            leader = _default_port("LEROBOT_LEADER_PORT", 1)
        self.assertTrue(follower.startswith(BY_ID_PREFIX))
        self.assertTrue(leader.startswith(BY_ID_PREFIX))
        self.assertNotEqual(follower, leader)

    def test_no_arm_gives_empty_port(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(Path, "is_dir", return_value=False):
            self.assertEqual(_default_port("LEROBOT_LEADER_PORT", 1), "")


class TestPreConnectionCheck(unittest.TestCase):
    def test_by_id_symlink_is_recognized_as_existing_port(self):
        by_id = BY_ID_PREFIX + "usb-1a86_USB_Single_Serial_TEST-if00"
        fake_ports = [SimpleNamespace(device="/dev/ttyACM0")]

        with mock.patch("serial.tools.list_ports.comports", return_value=fake_ports), \
             mock.patch("os.path.realpath", return_value="/dev/ttyACM0"), \
             mock.patch("serial.Serial"):
            result = RobotDiagnostic.pre_connection_check(by_id)

        self.assertTrue(result["checks"]["port_exists"])
        self.assertTrue(result["all_checks_passed"])

    def test_missing_port_is_reported(self):
        with mock.patch("serial.tools.list_ports.comports", return_value=[]):
            result = RobotDiagnostic.pre_connection_check("/dev/ttyACM9")

        self.assertFalse(result["checks"]["port_exists"])


if __name__ == "__main__":
    unittest.main()
