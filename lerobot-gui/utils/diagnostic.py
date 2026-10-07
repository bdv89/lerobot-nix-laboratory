"""
Diagnostic utilities for robot connection and motor detection.
Version 2.0 - Async connection with progress feedback
"""

import os
import sys
import asyncio
import threading
import queue
from pathlib import Path
from typing import Optional, List, Dict, Callable
import serial
import serial.tools.list_ports


def _default_port(env_var: str, rank: int) -> str:
    """Port d'un bras : variable d'environnement, sinon n-ieme CH340 vu dans /dev/serial/by-id."""
    if os.environ.get(env_var):
        return os.environ[env_var]
    found = sorted(Path("/dev/serial/by-id").glob("usb-1a86_*")) if Path("/dev/serial/by-id").is_dir() else []
    return str(found[rank]) if len(found) > rank else ""


class RobotDiagnostic:
    """Diagnostic tools for robot connection with async support."""

    @staticmethod
    def _create_robot_config(robot_type: str, port: str):
        """
        Helper method to create the appropriate robot config based on type.
        """
        if robot_type == "so101_follower":
            from lerobot.robots.so101_follower import SO101FollowerConfig
            return SO101FollowerConfig(port=port)
        elif robot_type == "so101_leader":
            from lerobot.teleoperators.so101_leader import SO101LeaderConfig
            return SO101LeaderConfig(port=port)
        elif robot_type == "so100_follower":
            from lerobot.robots.so100_follower import SO100FollowerConfig
            return SO100FollowerConfig(port=port)
        elif robot_type == "so100_leader":
            from lerobot.teleoperators.so100_leader import SO100LeaderConfig
            return SO100LeaderConfig(port=port)
        elif robot_type == "koch_follower":
            from lerobot.robots.koch_follower import KochFollowerConfig
            return KochFollowerConfig(port=port)
        else:
            raise ValueError(f"Robot type '{robot_type}' not supported in diagnostic yet")

    @staticmethod
    def scan_serial_ports() -> List[Dict[str, str]]:
        """
        Scan for available serial ports.
        Returns a list of port info dicts.
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'manufacturer': port.manufacturer or 'Unknown',
                'product': port.product or 'Unknown',
                'serial_number': port.serial_number or 'N/A',
            })
        return ports

    @staticmethod
    def pre_connection_check(port: str) -> Dict[str, any]:
        """
        Pre-flight checks before attempting robot connection.
        """
        result = {
            'all_checks_passed': False,
            'checks': {
                'port_exists': False,
                'port_accessible': False,
                'port_not_busy': False,
            },
            'details': {}
        }

        # Check 1: Port exists
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        # Resout les liens /dev/serial/by-id/ vers /dev/ttyACMx
        result['checks']['port_exists'] = os.path.realpath(port) in available_ports
        result['details']['available_ports'] = available_ports

        if not result['checks']['port_exists']:
            return result

        # Check 2: Port accessible and not busy
        try:
            test_serial = serial.Serial(port, baudrate=1000000, timeout=0.5)
            result['checks']['port_accessible'] = True
            result['checks']['port_not_busy'] = True
            test_serial.close()
        except serial.SerialException as e:
            error_str = str(e).lower()
            if "permission denied" in error_str:
                result['checks']['port_accessible'] = False
                result['details']['error'] = "Permission denied"
            elif "already open" in error_str or "in use" in error_str or "access denied" in error_str:
                result['checks']['port_not_busy'] = False
                result['details']['error'] = "Port already in use"
            else:
                result['details']['error'] = str(e)
        except Exception as e:
            result['details']['error'] = str(e)

        # All checks must pass
        result['all_checks_passed'] = all(result['checks'].values())

        return result

    @staticmethod
    def connect_robot_async(
        robot_type: str,
        port: str,
        progress_callback: Optional[Callable[[str, float, Dict], None]] = None,
        skip_calibration: bool = True,
        timeout_seconds: float = 30.0
    ) -> Dict[str, any]:
        """
        Connect to robot with progress feedback (blocking but with callbacks).

        Args:
            robot_type: Type of robot (e.g. "so101_follower")
            port: Serial port (e.g. "COM4")
            progress_callback: Callback(stage_name, progress_0_to_1, details_dict)
            skip_calibration: Skip calibration for faster connection
            timeout_seconds: Total timeout

        Returns:
            dict with 'success', 'robot', 'error', 'stage', 'motor_statuses'
        """

        result = {
            'success': False,
            'robot': None,
            'error': None,
            'stage': 'initializing',
            'motor_statuses': {}
        }

        def update_progress(stage: str, progress: float, details: Dict = None):
            result['stage'] = stage
            if progress_callback:
                progress_callback(stage, progress, details or {})

        try:
            # Stage 0: Pre-checks (5%)
            update_progress("Vérification pré-connexion...", 0.05)
            pre_check = RobotDiagnostic.pre_connection_check(port)

            if not pre_check['all_checks_passed']:
                failed_checks = [k for k, v in pre_check['checks'].items() if not v]
                raise ConnectionError(
                    f"Pre-check failed: {', '.join(failed_checks)}. "
                    f"Details: {pre_check.get('details', {})}"
                )

            # Stage 1: Configuration (10%)
            update_progress("Création configuration...", 0.10)
            config = RobotDiagnostic._create_robot_config(robot_type, port)

            # Stage 2: Robot creation (15%)
            update_progress("Initialisation robot...", 0.15)
            from lerobot.robots import make_robot_from_config
            robot = make_robot_from_config(config)

            # Stage 3: Opening port (20%)
            update_progress("Ouverture port série...", 0.20)
            if not robot.bus.port_handler.openPort():
                raise OSError(f"Échec ouverture port '{port}'")

            # Stage 4: Set baudrate (25%)
            update_progress("Configuration baudrate...", 0.25)
            robot.bus.port_handler.setBaudRate(1000000)

            # Stage 5: Ping motors individually (30-60%)
            motor_count = len(robot.bus.motors)
            motor_names = list(robot.bus.motors.keys())

            for idx, motor_name in enumerate(motor_names):
                motor = robot.bus.motors[motor_name]
                progress = 0.30 + (0.30 * (idx / motor_count))

                update_progress(
                    f"Ping moteur {motor_name} ({idx+1}/{motor_count})...",
                    progress,
                    {'motor_id': motor.id, 'motor_name': motor_name}
                )

                try:
                    model_number = robot.bus.ping(motor.id, num_retry=2)
                    result['motor_statuses'][motor_name] = {
                        'id': motor.id,
                        'found': model_number is not None,
                        'model': model_number,
                        'expected_model': motor.model
                    }

                    if model_number is None:
                        raise RuntimeError(
                            f"Moteur {motor_name} (ID {motor.id}) ne répond pas"
                        )

                    if motor.model != str(model_number):
                        result['motor_statuses'][motor_name]['warning'] = (
                            f"Model mismatch: expected {motor.model}, got {model_number}"
                        )

                except Exception as e:
                    result['motor_statuses'][motor_name] = {
                        'id': motor.id,
                        'found': False,
                        'error': str(e)
                    }
                    raise

            # Stage 6: Firmware check (65%)
            update_progress("Vérification firmware...", 0.65)
            try:
                robot.bus._assert_same_firmware()
            except Exception as e:
                # Non-fatal, just warn
                result['firmware_warning'] = str(e)

            # Stage 7: Set timeout (70%)
            update_progress("Configuration timeouts...", 0.70)
            robot.bus.set_timeout()

            # Stage 8: Calibration check (75%)
            if not skip_calibration:
                update_progress("Vérification calibration...", 0.75)
                if not robot.bus.is_calibrated:
                    # Load existing calibration if available
                    calib_path = robot.bus.calibration_path
                    if calib_path and calib_path.exists():
                        robot.bus._load_calibration()
                    else:
                        result['calibration_warning'] = "No calibration file found"
            else:
                update_progress("Calibration ignorée (mode rapide)...", 0.75)

            # Stage 9: Motor configuration (85%)
            update_progress("Configuration moteurs...", 0.85)
            robot.configure()

            # Stage 10: Final checks (95%)
            update_progress("Vérifications finales...", 0.95)
            # Could add additional checks here

            # Success (100%)
            update_progress("Connexion réussie!", 1.0)
            result['success'] = True
            result['robot'] = robot
            result['stage'] = 'connected'

        except ValueError as e:
            result['error'] = f"Configuration error: {str(e)}"
            result['stage'] = 'config_error'
        except ConnectionError as e:
            result['error'] = str(e)
            result['stage'] = 'pre_check_failed'
        except OSError as e:
            result['error'] = f"Port error: {str(e)}"
            result['stage'] = 'port_error'
        except RuntimeError as e:
            result['error'] = f"Motor error: {str(e)}"
            result['stage'] = 'motor_error'
        except Exception as e:
            result['error'] = f"Unexpected error at stage '{result['stage']}': {str(e)}"

        return result

    @staticmethod
    def diagnose_connection_failure(port: str, error: str, stage: str, motor_statuses: Dict) -> Dict[str, any]:
        """
        Analyze connection failure and suggest fixes.
        """
        diagnosis = {
            'error_type': stage,
            'error_message': error,
            'likely_causes': [],
            'suggested_fixes': [],
            'failed_motors': []
        }

        error_lower = error.lower()

        # Analyze based on stage and error
        if stage == 'pre_check_failed':
            if 'port_exists' in error_lower or 'not found' in error_lower:
                diagnosis['likely_causes'].extend([
                    "Port COM inexistant",
                    "Câble USB déconnecté",
                    "Driver USB-UART non installé"
                ])
                diagnosis['suggested_fixes'].extend([
                    "Vérifier connexion USB physique",
                    "Scanner les ports disponibles",
                    "Installer driver CH340/CP2102/FTDI",
                    "Essayer un autre port USB du PC"
                ])
            elif 'permission' in error_lower:
                diagnosis['likely_causes'].append("Permissions insuffisantes")
                diagnosis['suggested_fixes'].extend([
                    "Windows: Exécuter en administrateur",
                    "Linux: sudo usermod -a -G dialout $USER (puis reboot)",
                    "Fermer autres programmes utilisant le port"
                ])
            elif 'busy' in error_lower or 'in use' in error_lower:
                diagnosis['likely_causes'].extend([
                    "Port déjà utilisé par un autre programme",
                    "Instance précédente non fermée"
                ])
                diagnosis['suggested_fixes'].extend([
                    "Fermer autres programmes (Arduino IDE, Putty, etc.)",
                    "Redémarrer le GUI",
                    "Débrancher/rebrancher le câble USB"
                ])

        elif stage == 'port_error':
            diagnosis['likely_causes'].extend([
                "Échec d'ouverture du port série",
                "Baudrate non supporté",
                "Driver défectueux"
            ])
            diagnosis['suggested_fixes'].extend([
                "Vérifier que le driver est à jour",
                "Essayer un autre câble USB",
                "Tester avec un baudrate différent"
            ])

        elif stage == 'motor_error' or 'ping' in stage:
            # Analyze which motors failed
            for motor_name, status in motor_statuses.items():
                if not status.get('found', False):
                    diagnosis['failed_motors'].append({
                        'name': motor_name,
                        'id': status.get('id'),
                        'error': status.get('error', 'No response')
                    })

            if diagnosis['failed_motors']:
                motor_ids = [m['id'] for m in diagnosis['failed_motors']]
                diagnosis['likely_causes'].extend([
                    f"Moteur(s) ID {motor_ids} non alimenté(s)",
                    "Câble daisy-chain défectueux",
                    "Moteur en mode erreur/bloqué",
                    "Mauvais baudrate configuré sur moteur"
                ])
                diagnosis['suggested_fixes'].extend([
                    "Vérifier alimentation 12V des moteurs",
                    f"Tester moteur(s) {motor_ids} individuellement",
                    "Vérifier câblage daisy-chain entre moteurs",
                    "Utiliser FeetechDebugger pour scanner IDs réels",
                    "Réinitialiser moteur avec FD Tool"
                ])
            else:
                diagnosis['likely_causes'].extend([
                    "Timeout de communication",
                    "Interférences électromagnétiques",
                    "Câble trop long"
                ])
                diagnosis['suggested_fixes'].extend([
                    "Utiliser câble blindé court (<1m)",
                    "S'éloigner de sources d'interférence",
                    "Vérifier connexions électriques"
                ])

        elif 'firmware' in error_lower:
            diagnosis['likely_causes'].extend([
                "Versions firmware différentes entre moteurs",
                "Firmware corrompu"
            ])
            diagnosis['suggested_fixes'].extend([
                "Mettre à jour firmware avec FD Tool",
                "S'assurer que tous les moteurs ont la même version"
            ])

        elif 'timeout' in error_lower:
            diagnosis['likely_causes'].extend([
                "Opération trop longue",
                "Communication instable",
                "Moteur bloqué"
            ])
            diagnosis['suggested_fixes'].extend([
                "Augmenter timeout",
                "Vérifier que les moteurs bougent librement",
                "Réduire le nombre d'opérations"
            ])

        return diagnosis

    @staticmethod
    def scan_motors(robot_type: str, port: str, baudrate: int = 1000000) -> Dict[str, any]:
        """
        Quick scan for motors (simplified version using async connection).
        """
        result = {
            'success': False,
            'error': None,
            'motors': [],
        }

        try:
            # Use async connection with skip_calibration
            conn_result = RobotDiagnostic.connect_robot_async(
                robot_type=robot_type,
                port=port,
                skip_calibration=True,
                timeout_seconds=15.0
            )

            if conn_result['success']:
                robot = conn_result['robot']
                # Extract motor IDs
                motor_ids = [motor.id for motor in robot.bus.motors.values()]
                result['motors'] = sorted(motor_ids)
                result['motor_details'] = conn_result['motor_statuses']
                result['success'] = True

                # Disconnect
                robot.disconnect()
            else:
                result['error'] = conn_result['error']

        except Exception as e:
            result['error'] = f"Motor scan failed: {str(e)}"

        return result

    @staticmethod
    def get_motor_status(robot_type: str, port: str, motor_ids: List[int]) -> Dict[str, any]:
        """
        Get detailed status for specific motors.
        """
        result = {
            'success': False,
            'error': None,
            'motors_status': [],
        }

        try:
            # Connect
            conn_result = RobotDiagnostic.connect_robot_async(
                robot_type=robot_type,
                port=port,
                skip_calibration=True,
                timeout_seconds=15.0
            )

            if not conn_result['success']:
                result['error'] = conn_result['error']
                return result

            robot = conn_result['robot']
            motor_bus = robot.bus

            # Get motor names mapping
            motor_names = {}
            for name, motor in robot.bus.motors.items():
                if motor.id in motor_ids:
                    motor_names[motor.id] = name

            motors_status = []
            for motor_id in motor_ids:
                try:
                    motor_name = motor_names.get(motor_id, f"motor_{motor_id}")

                    # Read various parameters
                    status = {'id': motor_id, 'name': motor_name, 'error': None}

                    try:
                        status['position'] = motor_bus.read("Present_Position", motor_name)
                    except:
                        status['position'] = "N/A"

                    try:
                        status['temperature'] = motor_bus.read("Present_Temperature", motor_name)
                    except:
                        status['temperature'] = "N/A"

                    try:
                        status['voltage'] = motor_bus.read("Present_Voltage", motor_name)
                    except:
                        status['voltage'] = "N/A"

                    try:
                        status['current'] = motor_bus.read("Present_Current", motor_name)
                    except:
                        status['current'] = "N/A"

                    motors_status.append(status)

                except Exception as e:
                    motors_status.append({
                        'id': motor_id,
                        'name': motor_names.get(motor_id, f"motor_{motor_id}"),
                        'error': str(e),
                        'position': 'N/A',
                        'temperature': 'N/A',
                        'voltage': 'N/A',
                        'current': 'N/A',
                    })

            robot.disconnect()

            result['success'] = True
            result['motors_status'] = motors_status

        except Exception as e:
            result['error'] = f"Failed to read motor status: {str(e)}"

        return result

    @staticmethod
    def launch_calibration_gui(robot_type: str, port: str):
        """
        Launch the LeRobot calibration GUI.
        """
        import subprocess

        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_calibrate",
            f"--robot.type={robot_type}",
            f"--robot.port={port}",
        ]

        # Launch in background
        process = subprocess.Popen(cmd)
        return process


class SO101Config:
    """Pre-configured settings for SO101 robots."""

    FOLLOWER_TYPE = "so101_follower"
    LEADER_TYPE = "so101_leader"

    # Default ports : LEROBOT_FOLLOWER_PORT / LEROBOT_LEADER_PORT (alias by-id stables),
    # posees par le module NixOS. Sans elles : auto-detection, a verifier dans Diagnostic.
    FOLLOWER_PORT = _default_port("LEROBOT_FOLLOWER_PORT", 0)
    LEADER_PORT = _default_port("LEROBOT_LEADER_PORT", 1)
    CAMERA = os.environ.get("LEROBOT_CAMERA", "/dev/lerobot_cam")

    # Default IDs (must match calibration filenames without .json)
    FOLLOWER_ID = "None"
    LEADER_ID = "None"

    # Default camera config
    DEFAULT_CAMERA_CONFIG = {
        "cam": {
            "type": "opencv",
            "index_or_path": 4,
            "width": 640,
            "height": 480,
            "fps": 30
        }
    }

    # Motor IDs for SO101
    MOTOR_IDS = list(range(1, 7))  # 6 motors per arm

    @classmethod
    def get_default_record_config(cls) -> dict:
        """Get default recording configuration for SO101."""
        return {
            'robot_type': cls.FOLLOWER_TYPE,
            'robot_port': cls.FOLLOWER_PORT,
            'robot_id': cls.FOLLOWER_ID,
            'teleop_type': cls.LEADER_TYPE,
            'teleop_port': cls.LEADER_PORT,
            'teleop_id': cls.LEADER_ID,
            'dataset_name': 'user/so101_dataset',
            'num_episodes': 1,
            'task_name': 'Grab the cube',
            'episode_time_s': 60,
            'camera_config': cls.DEFAULT_CAMERA_CONFIG,
        }

    @classmethod
    def get_default_replay_config(cls) -> dict:
        """Get default replay configuration for SO101."""
        return {
            'robot_type': cls.FOLLOWER_TYPE,
            'robot_port': cls.FOLLOWER_PORT,
            'robot_id': cls.FOLLOWER_ID,
            'dataset_name': 'user/so101_dataset',
            'episode': 0,
        }
