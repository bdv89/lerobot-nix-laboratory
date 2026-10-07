"""
LeRobot GUI - Interface graphique pour contrôler LeRobot SO-101
3 modes : Répétition, Entraînement, Autonome
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import cv2
from nicegui import ui, app
from utils.lerobot_wrapper import LeRobotWrapper, disable_usb_autosuspend
from utils.diagnostic import RobotDiagnostic, SO101Config
from utils.dataset_utils import scan_available_datasets, extract_dataset_id_from_path

# Initialize
lerobot = LeRobotWrapper()
diagnostic = RobotDiagnostic()
so101 = SO101Config()

# Global state
current_process: Optional[object] = None


# ==================== STYLES ====================
CARD_STYLE = "background-color: #1e1e1e; padding: 20px; border-radius: 8px;"
BUTTON_PRIMARY = "background-color: #4CAF50; color: white;"
BUTTON_DANGER = "background-color: #f44336; color: white;"
BUTTON_INFO = "background-color: #2196F3; color: white;"
BUTTON_WARN = "background-color: #FF9800; color: white;"
INFO_BOX = "background-color: #1a3a5a; padding: 15px; border-left: 4px solid #2196F3;"


# ==================== HELPERS ====================
async def monitor_process(process, output_log, status_label, success_msg="Terminé"):
    """Monitor a subprocess and stream output to a log widget."""
    loop = asyncio.get_event_loop()

    while process.poll() is None:
        if process.stdout:
            try:
                line = await loop.run_in_executor(None, process.stdout.readline)
                if line:
                    output_log.push(line.strip())
            except Exception:
                break
        await asyncio.sleep(0.05)

    # Remaining output
    if process.stdout:
        remaining = process.stdout.read()
        if remaining:
            for line in remaining.strip().split('\n'):
                if line.strip():
                    output_log.push(line.strip())

    if process.returncode == 0:
        status_label.text = f'{success_msg}'
        status_label.style('color: #4CAF50')
    elif process.returncode == -15:
        status_label.text = 'Arrete'
        status_label.style('color: #FF9800')
    else:
        status_label.text = f'Erreur (code {process.returncode})'
        status_label.style('color: #f44336')


def stop_process(status_label, output_log):
    """Stop the current global process."""
    global current_process
    if current_process:
        try:
            current_process.terminate()
            status_label.text = 'Processus arrete'
            status_label.style('color: #FF9800')
            output_log.push('Arrete par utilisateur')
        except Exception:
            pass


# Global camera state
import time as _time
import threading
from starlette.responses import StreamingResponse

_camera_cap = None
_camera_active = False
_camera_lock = threading.Lock()


def _parse_cam_value(value: str):
    """Parse camera value: return int if numeric, else string path."""
    value = str(value).strip()
    try:
        return int(value)
    except ValueError:
        return value


def _open_camera(cam_id, width: int = 640, height: int = 480):
    """Open camera capture. cam_id: int index or string path (e.g. /dev/lerobot_cam)."""
    global _camera_cap, _camera_active
    stop_camera_stream()
    with _camera_lock:
        _camera_cap = cv2.VideoCapture(cam_id)
        _camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        _camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        _camera_cap.set(cv2.CAP_PROP_FPS, 30)
        _camera_active = _camera_cap.isOpened()
    return _camera_active


def stop_camera_stream():
    """Stop the camera stream."""
    global _camera_cap, _camera_active
    _camera_active = False
    with _camera_lock:
        if _camera_cap:
            _camera_cap.release()
            _camera_cap = None


def _mjpeg_generator():
    """Yield JPEG frames as MJPEG multipart stream."""
    while _camera_active:
        with _camera_lock:
            if not _camera_cap or not _camera_cap.isOpened():
                break
            ret, frame = _camera_cap.read()
        if not ret:
            break
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
        )


@app.get('/api/camera')
def camera_feed():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame',
    )


def start_camera_stream(image_widget, cam_id, width: int = 640, height: int = 480):
    """Start camera and point image widget to MJPEG stream."""
    if _open_camera(cam_id, width, height):
        # Cache-busting: timestamp forces browser to re-fetch on restart
        image_widget.set_source(f'/api/camera?t={_time.time()}')
    else:
        image_widget.set_source('')


# ==================== DIAGNOSTIC PAGE ====================
def create_diagnostic_page():
    """Diagnostic : ports serie, moteurs, calibration."""
    with ui.column().classes('w-full gap-4 p-4'):
        ui.label('Diagnostic Robot').classes('text-3xl font-bold mb-4')

        # --- Ports serie ---
        with ui.card().style(CARD_STYLE):
            ui.label('Ports Serie').classes('text-xl font-semibold mb-4')
            ports_container = ui.column().classes('w-full gap-2')

            async def scan_ports():
                ports_container.clear()
                try:
                    ports = diagnostic.scan_serial_ports()
                    with ports_container:
                        if not ports:
                            ui.label('Aucun port serie detecte').classes('text-yellow-500')
                        else:
                            for port in ports:
                                with ui.expansion(f"{port['device']}", icon='usb').classes('w-full'):
                                    with ui.column().classes('gap-1 p-2'):
                                        ui.label(f"Description: {port['description']}").classes('text-sm')
                                        ui.label(f"Fabricant: {port['manufacturer']}").classes('text-sm')
                                        ui.label(f"N. serie: {port['serial_number']}").classes('text-sm text-gray-400')
                    ui.notify(f'{len(ports)} port(s) detecte(s)', type='positive')
                except Exception as e:
                    with ports_container:
                        ui.label(f'Erreur: {str(e)}').classes('text-red-500')

            ui.button('Scanner les ports', on_click=scan_ports).style(BUTTON_INFO)

        # --- Test connexion ---
        with ui.card().style(CARD_STYLE):
            ui.label('Test de Connexion').classes('text-xl font-semibold mb-4')

            with ui.row().classes('w-full gap-4'):
                test_robot_type = ui.input(label='Type de robot', value='so101_follower').classes('flex-grow')
                test_robot_port = ui.input(label='Port', value=so101.FOLLOWER_PORT).classes('flex-grow')

            connection_status = ui.label('').classes('text-lg mt-2')
            results_container = ui.column().classes('w-full gap-2 mt-4')

            async def test_connection(skip_calibration=True):
                connection_status.text = 'Connexion en cours...'
                connection_status.style('color: #FF9800')
                results_container.clear()

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: diagnostic.connect_robot_async(
                        robot_type=test_robot_type.value,
                        port=test_robot_port.value,
                        skip_calibration=skip_calibration,
                        timeout_seconds=30.0
                    )
                )

                results_container.clear()
                with results_container:
                    if result['success']:
                        connection_status.text = 'Robot connecte !'
                        connection_status.style('color: #4CAF50')
                        with ui.card().style('background-color: #1a3a1a; padding: 15px;'):
                            ui.label('Status des Moteurs').classes('font-bold mb-2')
                            for motor_name, status in result.get('motor_statuses', {}).items():
                                if status.get('found'):
                                    ui.label(f"OK - {motor_name} (ID {status['id']})").classes('text-sm')
                                else:
                                    ui.label(f"ERREUR - {motor_name} (ID {status['id']}): {status.get('error', '')}").classes('text-sm text-red-400')
                        if result['robot']:
                            result['robot'].disconnect()
                    else:
                        connection_status.text = f"Echec: {result['error']}"
                        connection_status.style('color: #f44336')

            with ui.row().classes('gap-2'):
                ui.button('Test Rapide (sans calibration)', on_click=lambda: test_connection(True)).style(BUTTON_PRIMARY)
                ui.button('Test Complet (avec calibration)', on_click=lambda: test_connection(False)).style(BUTTON_INFO)

        # --- Calibration ---
        with ui.card().style(CARD_STYLE):
            ui.label('Calibration').classes('text-xl font-semibold mb-4')
            with ui.row().classes('w-full gap-4'):
                calib_robot_type = ui.input(label='Type de robot', value='so101_follower').classes('flex-grow')
                calib_robot_port = ui.input(label='Port', value=so101.FOLLOWER_PORT).classes('flex-grow')
            calib_status = ui.label('').classes('text-lg mt-2')

            def launch_calibration():
                try:
                    diagnostic.launch_calibration_gui(calib_robot_type.value, calib_robot_port.value)
                    calib_status.text = 'GUI de calibration lance !'
                    calib_status.style('color: #4CAF50')
                except Exception as e:
                    calib_status.text = f'Erreur: {str(e)}'
                    calib_status.style('color: #f44336')

            ui.button('Lancer la calibration', on_click=launch_calibration).style(BUTTON_PRIMARY)


# ==================== REPETITION PAGE ====================
def create_repetition_page():
    """Mode Repetition : teleoperation live, enregistrement, replay."""
    with ui.column().classes('w-full gap-4 p-4'):
        ui.label('Repetition').classes('text-3xl font-bold mb-4')

        # Sub-tabs pour les 3 sous-modes
        with ui.tabs().classes('w-full') as sub_tabs:
            tab_teleop = ui.tab('Teleoperation')
            tab_record = ui.tab('Enregistrer')
            tab_replay = ui.tab('Rejouer')

        with ui.tab_panels(sub_tabs, value=tab_teleop).classes('w-full'):

            # --- TELEOPERATION ---
            with ui.tab_panel(tab_teleop):
                with ui.column().classes('w-full gap-4'):
                    with ui.card().style(INFO_BOX):
                        ui.label('Le follower reproduit en temps reel les mouvements du leader. Pas d\'enregistrement.').classes('text-sm')

                    with ui.row().classes('w-full gap-4'):
                        # Colonne gauche : config + log
                        with ui.column().classes('flex-grow gap-4'):
                            with ui.card().style(CARD_STYLE):
                                ui.label('Configuration').classes('text-xl font-semibold mb-2')

                                with ui.row().classes('w-full gap-4'):
                                    teleop_follower_port = ui.input(label='Port follower', value=so101.FOLLOWER_PORT).classes('flex-grow')
                                    teleop_leader_port = ui.input(label='Port leader', value=so101.LEADER_PORT).classes('flex-grow')

                                with ui.row().classes('w-full gap-4 items-center'):
                                    teleop_camera = ui.switch('Camera live', value=True).classes('text-lg')
                                    teleop_cam_path = ui.input(label='Camera (index ou /dev/...)', value=so101.CAMERA).classes('w-64')

                            teleop_status = ui.label('').classes('text-lg')
                            teleop_log = ui.log(max_lines=15).classes('w-full h-40 font-mono')

                        # Colonne droite : flux camera
                        with ui.column().classes('items-center'):
                            teleop_cam_feed = ui.image('').classes('w-96 h-72 rounded border border-gray-600')
                            ui.label('Flux camera').classes('text-sm text-gray-400')

                    async def start_teleop():
                        global current_process
                        teleop_status.text = 'Teleoperation active...'
                        teleop_status.style('color: #4CAF50')
                        teleop_log.clear()
                        teleop_log.push('Demarrage teleoperation...')
                        disable_usb_autosuspend()

                        try:
                            # Teleoperation sans camera (pas besoin pour teleop)
                            current_process = lerobot.teleoperate(
                                robot_type=so101.FOLLOWER_TYPE,
                                robot_port=teleop_follower_port.value,
                                teleop_type=so101.LEADER_TYPE,
                                teleop_port=teleop_leader_port.value,
                                robot_id=so101.FOLLOWER_ID,
                                teleop_id=so101.LEADER_ID,
                            )
                            teleop_log.push('Processus lance - bougez le leader !')
                            asyncio.create_task(monitor_process(current_process, teleop_log, teleop_status, 'Teleoperation terminee'))

                            # Flux camera dans la GUI
                            if teleop_camera.value:
                                start_camera_stream(teleop_cam_feed, _parse_cam_value(teleop_cam_path.value))
                        except Exception as e:
                            teleop_status.text = f'Erreur: {str(e)}'
                            teleop_status.style('color: #f44336')

                    def stop_teleop():
                        stop_camera_stream()
                        stop_process(teleop_status, teleop_log)
                        teleop_cam_feed.set_source('')

                    with ui.row().classes('gap-4'):
                        ui.button('Demarrer', on_click=start_teleop).style(BUTTON_PRIMARY).classes('text-lg px-6 py-3')
                        ui.button('Arreter', on_click=stop_teleop).style(BUTTON_DANGER).classes('text-lg px-6 py-3')

            # --- ENREGISTREMENT ---
            with ui.tab_panel(tab_record):
                with ui.column().classes('w-full gap-4'):
                    with ui.card().style(INFO_BOX):
                        ui.label('Enregistre les demonstrations du leader pour replay ou entrainement.').classes('text-sm')
                        ui.label('Valider, recommencer ou terminer un episode avec les boutons ci-dessous').classes('text-sm font-bold mt-1')

                    with ui.row().classes('w-full gap-4'):
                        # Colonne gauche : config + log
                        with ui.column().classes('flex-grow gap-4'):
                            with ui.card().style(CARD_STYLE):
                                ui.label('Configuration').classes('text-xl font-semibold mb-2')

                                rec_dataset = ui.input(label='Dataset (user/nom)', value='user/so101-demo', placeholder='user/mon_dataset').classes('w-full')

                                with ui.row().classes('w-full gap-4'):
                                    rec_task = ui.input(label='Tache', value='Grab the cube').classes('flex-grow')
                                    rec_episodes = ui.number(label='Nb episodes', value=50, min=1, max=200).classes('flex-grow')
                                    rec_time = ui.number(label='Duree max (s)', value=60, min=10, max=600).classes('flex-grow')

                                with ui.row().classes('w-full gap-4 items-center'):
                                    rec_camera = ui.switch('Camera', value=True).classes('text-lg')
                                    rec_cam_path = ui.input(label='Camera (index ou /dev/...)', value=so101.CAMERA).classes('w-64')

                            rec_status = ui.label('').classes('text-lg')
                            rec_log = ui.log(max_lines=15).classes('w-full h-40 font-mono')

                        # Colonne droite : flux camera
                        with ui.column().classes('items-center'):
                            rec_cam_feed = ui.image('').classes('w-96 h-72 rounded border border-gray-600')
                            ui.label('Flux camera').classes('text-sm text-gray-400')

                    async def start_recording():
                        global current_process
                        dataset_val = (rec_dataset.value or '').strip()
                        if '/' not in dataset_val:
                            ui.notify('Format dataset invalide. Utilisez user/nom', type='negative')
                            return

                        rec_status.text = 'Enregistrement en cours...'
                        rec_status.style('color: #f44336')
                        rec_log.clear()

                        disable_usb_autosuspend()
                        try:
                            episode_time = float(rec_time.value or 60)
                            if not lerobot.supports_episode_time_limit:
                                episode_time = None

                            # Auto-detect resume
                            if lerobot._dataset_can_resume(dataset_val):
                                rec_log.push(f'Dataset existant detecte, reprise automatique')
                            elif lerobot._dataset_exists_but_empty(dataset_val):
                                rec_log.push(f'Dataset vide detecte, recreation')

                            # Build camera config for LeRobot (recording needs it for dataset)
                            cam_config = None
                            if rec_camera.value:
                                cam_config = {
                                    "cam": {
                                        "type": "opencv",
                                        "index_or_path": _parse_cam_value(rec_cam_path.value),
                                        "width": 640,
                                        "height": 480,
                                        "fps": 30,
                                        "fourcc": "MJPG",
                                    }
                                }

                            current_process = lerobot.record(
                                robot_type=so101.FOLLOWER_TYPE,
                                robot_port=so101.FOLLOWER_PORT,
                                robot_id=so101.FOLLOWER_ID,
                                dataset_repo_id=dataset_val,
                                num_episodes=int(rec_episodes.value),
                                single_task=rec_task.value,
                                episode_time_s=episode_time,
                                cameras_config=cam_config,
                                teleop_type=so101.LEADER_TYPE,
                                teleop_port=so101.LEADER_PORT,
                                teleop_id=so101.LEADER_ID,
                                display_data=False,
                                push_to_hub=False,
                            )
                            rec_log.push(f'Dataset: {dataset_val}')
                            rec_log.push(f'Tache: {rec_task.value}')
                            rec_log.push(f'Episodes: {int(rec_episodes.value)}')
                            if cam_config:
                                rec_log.push(f'Camera: {rec_cam_path.value}')
                            rec_log.push('---')
                            asyncio.create_task(monitor_process(current_process, rec_log, rec_status, 'Enregistrement termine'))

                            # Pas de flux camera GUI pendant l'enregistrement :
                            # LeRobot ouvre deja la camera dans son sous-processus,
                            # ouvrir une 2e fois cause un conflit d'acces.
                        except Exception as e:
                            rec_status.text = f'Erreur: {str(e)}'
                            rec_status.style('color: #f44336')

                    def stop_recording():
                        stop_camera_stream()
                        stop_process(rec_status, rec_log)
                        rec_cam_feed.set_source('')

                    with ui.row().classes('gap-4'):
                        ui.button('Demarrer enregistrement', on_click=start_recording).style(BUTTON_PRIMARY).classes('text-lg px-6 py-3')
                        ui.button('Arreter', on_click=stop_recording).style(BUTTON_DANGER).classes('text-lg px-6 py-3')

                    # Episode control buttons (write to /tmp/lerobot_control)
                    with ui.card().style('background-color: #2a2a2a; padding: 15px; border-radius: 8px; border: 1px solid #444;').classes('w-full mt-2'):
                        ui.label('Controle episode en cours').classes('text-lg font-semibold mb-2')

                        def send_control(cmd):
                            from pathlib import Path
                            Path('/tmp/lerobot_control').write_text(cmd)
                            rec_log.push(f'Commande: {cmd}')

                        with ui.row().classes('gap-4 w-full justify-center'):
                            ui.button('Valider episode', on_click=lambda: send_control('next')).style(BUTTON_PRIMARY).classes('text-lg px-8 py-4')
                            ui.button('Recommencer episode', on_click=lambda: send_control('redo')).style(BUTTON_WARN).classes('text-lg px-8 py-4')
                            ui.button('Terminer enregistrement', on_click=lambda: send_control('stop')).style(BUTTON_DANGER).classes('text-lg px-8 py-4')

            # --- REPLAY ---
            with ui.tab_panel(tab_replay):
                with ui.column().classes('w-full gap-4'):
                    with ui.card().style(INFO_BOX):
                        ui.label('Le follower reproduit exactement les mouvements enregistres (pas d\'IA).').classes('text-sm')

                    with ui.card().style(CARD_STYLE):
                        ui.label('Configuration').classes('text-xl font-semibold mb-2')

                        base_path_replay = Path.home() / '.cache/huggingface/lerobot'

                        with ui.row().classes('w-full gap-2'):
                            replay_dataset = ui.select(
                                label='Dataset',
                                options=[],
                                value=None,
                                with_input=True,
                            ).classes('flex-grow')

                            def refresh_replay_ds():
                                new_ds = scan_available_datasets(base_path_replay)
                                replay_dataset.options = new_ds
                                replay_dataset.update()
                                if new_ds and not replay_dataset.value:
                                    replay_dataset.value = new_ds[0]
                                ui.notify(f'{len(new_ds)} dataset(s) trouve(s)', type='info')

                            ui.button('Rafraichir', on_click=refresh_replay_ds).props('flat').style(BUTTON_INFO)

                        # Auto-refresh au chargement
                        refresh_replay_ds()

                        replay_episode = ui.number(label='Episode', value=0, min=0).classes('w-full mt-2')

                    replay_status = ui.label('').classes('text-lg')
                    replay_log = ui.log(max_lines=20).classes('w-full h-48 font-mono')

                    async def start_replay():
                        global current_process
                        # Refresh dataset list
                        refresh_replay_ds()

                        ds_val = replay_dataset.value
                        if not ds_val or '/' not in str(ds_val):
                            ui.notify(f'Dataset invalide: "{ds_val}". Selectionnez un dataset valide (user/nom)', type='negative')
                            return

                        replay_status.text = 'Replay en cours...'
                        replay_status.style('color: #2196F3')
                        replay_log.clear()

                        try:
                            current_process = lerobot.replay(
                                robot_type=so101.FOLLOWER_TYPE,
                                robot_port=so101.FOLLOWER_PORT,
                                robot_id=so101.FOLLOWER_ID,
                                dataset_repo_id=ds_val,
                                episode=int(replay_episode.value),
                            )
                            replay_log.push(f'Dataset: {ds_val}')
                            replay_log.push(f'Replay episode {int(replay_episode.value)}...')
                            asyncio.create_task(monitor_process(current_process, replay_log, replay_status, 'Replay termine'))
                        except Exception as e:
                            replay_status.text = f'Erreur: {str(e)}'
                            replay_status.style('color: #f44336')

                    with ui.row().classes('gap-4'):
                        ui.button('Demarrer replay', on_click=start_replay).style(BUTTON_PRIMARY).classes('text-lg px-6 py-3')
                        ui.button('Arreter', on_click=lambda: stop_process(replay_status, replay_log)).style(BUTTON_DANGER).classes('text-lg px-6 py-3')


# ==================== TRAINING PAGE ====================
def create_training_page():
    """Mode Entrainement : entrainer une politique sur un dataset."""
    with ui.column().classes('w-full gap-4 p-4'):
        ui.label('Entrainement').classes('text-3xl font-bold mb-4')

        with ui.card().style(INFO_BOX):
            ui.label('Entraine un modele (politique) a partir de demonstrations enregistrees.').classes('text-sm')
            ui.label('Necessite un dataset avec des episodes enregistres.').classes('text-sm mt-1')

        with ui.card().style(CARD_STYLE):
            ui.label('Dataset').classes('text-xl font-semibold mb-2')

            base_path_train = Path.home() / '.cache/huggingface/lerobot'

            with ui.row().classes('w-full gap-2'):
                train_dataset = ui.select(
                    label='Dataset',
                    options=[],
                    value=None,
                    with_input=True,
                ).classes('flex-grow')

                def refresh_train_ds():
                    new_ds = scan_available_datasets(base_path_train)
                    train_dataset.options = new_ds
                    train_dataset.update()
                    if new_ds and not train_dataset.value:
                        train_dataset.value = new_ds[0]
                    ui.notify(f'{len(new_ds)} dataset(s) trouve(s)', type='info')

                ui.button('Rafraichir', on_click=refresh_train_ds).props('flat').style(BUTTON_INFO)

            # Auto-refresh au chargement
            refresh_train_ds()

        with ui.card().style(CARD_STYLE):
            ui.label('Configuration').classes('text-xl font-semibold mb-2')

            with ui.row().classes('w-full gap-4'):
                train_policy = ui.select(
                    label='Politique',
                    options=['act', 'diffusion', 'tdmpc', 'vqbet'],
                    value='act',
                ).classes('flex-grow')

                train_steps = ui.number(label='Nombre de steps', value=50000, min=1000, max=500000, step=1000).classes('flex-grow')

            with ui.row().classes('w-full gap-4'):
                train_batch = ui.number(label='Batch size', value=8, min=1, max=64).classes('flex-grow')
                train_save_freq = ui.number(label='Save freq (steps)', value=10000, min=1000, max=100000, step=1000).classes('flex-grow')

            # Infos politiques
            with ui.expansion('Aide : politiques disponibles').classes('w-full mt-2'):
                ui.html('''
                <table style="width:100%; font-size:0.85em;">
                <tr><td><b>act</b></td><td>Action Chunking Transformer - manipulation fine (recommande)</td></tr>
                <tr><td><b>diffusion</b></td><td>Diffusion Policy - taches complexes</td></tr>
                <tr><td><b>tdmpc</b></td><td>TD-MPC - controle dynamique</td></tr>
                <tr><td><b>vqbet</b></td><td>VQ-BeT - alternative a ACT</td></tr>
                </table>
                ''')

        train_status = ui.label('').classes('text-lg')
        train_log = ui.log(max_lines=30).classes('w-full h-64 font-mono')

        async def start_training():
            global current_process
            train_status.text = 'Entrainement en cours...'
            train_status.style('color: #FF9800')
            train_log.clear()

            try:
                current_process = lerobot.train(
                    dataset_repo_id=train_dataset.value,
                    policy=train_policy.value,
                    steps=int(train_steps.value),
                    batch_size=int(train_batch.value),
                    save_freq=int(train_save_freq.value),
                )
                train_log.push(f'Dataset: {train_dataset.value}')
                train_log.push(f'Politique: {train_policy.value}')
                train_log.push(f'Steps: {int(train_steps.value)}')
                train_log.push(f'Batch: {int(train_batch.value)}')
                train_log.push('---')
                asyncio.create_task(monitor_process(current_process, train_log, train_status, 'Entrainement termine'))
            except Exception as e:
                train_status.text = f'Erreur: {str(e)}'
                train_status.style('color: #f44336')

        with ui.row().classes('gap-4'):
            ui.button('Lancer entrainement', on_click=start_training).style(BUTTON_PRIMARY).classes('text-lg px-6 py-3')
            ui.button('Arreter', on_click=lambda: stop_process(train_status, train_log)).style(BUTTON_DANGER).classes('text-lg px-6 py-3')


# ==================== AUTONOMOUS PAGE ====================
def create_autonomous_page():
    """Mode Autonome : executer une politique entrainee."""
    with ui.column().classes('w-full gap-4 p-4'):
        ui.label('Mode Autonome').classes('text-3xl font-bold mb-4')

        with ui.card().style(INFO_BOX):
            ui.label('Le robot execute une politique entrainee de maniere autonome.').classes('text-sm')
            ui.label('Necessite un checkpoint issu de l\'entrainement (lerobot-rollout, sans enregistrement).').classes('text-sm mt-1')

        with ui.card().style(CARD_STYLE):
            ui.label('Checkpoint').classes('text-xl font-semibold mb-2')

            # List available checkpoints
            checkpoints = lerobot.list_checkpoints()
            checkpoint_options = [cp['name'] for cp in checkpoints] if checkpoints else []

            with ui.row().classes('w-full gap-2'):
                auto_checkpoint = ui.select(
                    label='Checkpoint entraine',
                    options=checkpoint_options if checkpoint_options else ['(aucun checkpoint)'],
                    value=checkpoint_options[0] if checkpoint_options else '(aucun checkpoint)',
                    with_input=True,
                ).classes('flex-grow')

                def refresh_checkpoints():
                    cps = lerobot.list_checkpoints()
                    opts = [cp['name'] for cp in cps] if cps else ['(aucun checkpoint)']
                    auto_checkpoint.options = opts
                    ui.notify(f'{len(cps)} checkpoint(s) trouve(s)', type='info')

                ui.button('Rafraichir', on_click=refresh_checkpoints).props('flat').style(BUTTON_INFO)

            auto_checkpoint_path = ui.input(
                label='Ou chemin complet du checkpoint',
                placeholder='outputs/train/mon_run/checkpoints/050000',
            ).classes('w-full mt-2')

        with ui.card().style(CARD_STYLE):
            ui.label('Configuration').classes('text-xl font-semibold mb-2')
            auto_robot_port = ui.input(label='Port follower', value=so101.FOLLOWER_PORT).classes('w-full')
            with ui.row().classes('w-full gap-4'):
                auto_task = ui.input(label='Tache', value='Grab the cube').classes('flex-grow')
                auto_time = ui.number(label='Duree (s)', value=30, min=5, max=3600).classes('flex-grow')
            with ui.row().classes('w-full gap-4 items-center'):
                auto_camera = ui.switch('Camera', value=True).classes('text-lg')
                auto_cam_path = ui.input(label='Camera (index ou /dev/...)', value=so101.CAMERA).classes('w-64')

        auto_status = ui.label('').classes('text-lg')
        auto_log = ui.log(max_lines=20).classes('w-full h-48 font-mono')

        async def start_autonomous():
            global current_process
            # Determine checkpoint path
            cp_path = (auto_checkpoint_path.value or '').strip()
            if cp_path:
                # Accepte aussi le dossier checkpoint parent de pretrained_model/
                if (Path(cp_path) / 'pretrained_model').is_dir():
                    cp_path = str(Path(cp_path) / 'pretrained_model')
            else:
                # Use selected checkpoint from list
                selected = auto_checkpoint.value
                if selected == '(aucun checkpoint)':
                    ui.notify('Selectionnez un checkpoint ou entrez un chemin', type='negative')
                    return
                # Find full path
                cps = lerobot.list_checkpoints()
                for cp in cps:
                    if cp['name'] == selected:
                        cp_path = cp['path']
                        break

            if not cp_path or not (Path(cp_path) / 'config.json').exists():
                ui.notify('Checkpoint introuvable (config.json absent)', type='negative')
                return

            cam_config = None
            if auto_camera.value:
                # La cle 'cam' doit correspondre a celle du dataset d'entrainement
                cam_config = {
                    "cam": {
                        "type": "opencv",
                        "index_or_path": _parse_cam_value(auto_cam_path.value),
                        "width": 640,
                        "height": 480,
                        "fps": 30,
                        "fourcc": "MJPG",
                    }
                }

            auto_status.text = 'Execution autonome...'
            auto_status.style('color: #FF9800')
            auto_log.clear()

            disable_usb_autosuspend()
            try:
                current_process = lerobot.rollout(
                    robot_type=so101.FOLLOWER_TYPE,
                    robot_port=auto_robot_port.value,
                    robot_id=so101.FOLLOWER_ID,
                    policy_path=cp_path,
                    task=auto_task.value,
                    duration_s=float(auto_time.value or 30),
                    cameras_config=cam_config,
                )
                auto_log.push(f'Checkpoint: {cp_path}')
                auto_log.push(f'Robot: {auto_robot_port.value}')
                auto_log.push('---')
                asyncio.create_task(monitor_process(current_process, auto_log, auto_status, 'Execution terminee'))
            except Exception as e:
                auto_status.text = f'Erreur: {str(e)}'
                auto_status.style('color: #f44336')

        with ui.row().classes('gap-4'):
            ui.button('Lancer execution', on_click=start_autonomous).style(BUTTON_PRIMARY).classes('text-lg px-6 py-3')
            ui.button('Arreter (urgence)', on_click=lambda: stop_process(auto_status, auto_log)).style(BUTTON_DANGER).classes('text-lg px-6 py-3')


# ==================== MAIN APP ====================
@ui.page('/')
def main_page():
    """Page principale avec navigation par onglets."""
    ui.dark_mode().enable()

    with ui.header().classes('items-center justify-between bg-gray-900'):
        ui.label('LeRobot SO-101').classes('text-2xl font-bold')
        ui.label('v2.0').classes('text-sm text-gray-400')

    with ui.tabs().classes('w-full') as tabs:
        tab_diagnostic = ui.tab('Diagnostic')
        tab_repetition = ui.tab('Repetition')
        tab_training = ui.tab('Entrainement')
        tab_autonomous = ui.tab('Autonome')

    with ui.tab_panels(tabs, value=tab_diagnostic).classes('w-full'):
        with ui.tab_panel(tab_diagnostic):
            create_diagnostic_page()

        with ui.tab_panel(tab_repetition):
            create_repetition_page()

        with ui.tab_panel(tab_training):
            create_training_page()

        with ui.tab_panel(tab_autonomous):
            create_autonomous_page()


# ==================== RUN ====================
def main():
    import os
    ui.run(
        title='LeRobot SO-101',
        host=os.environ.get('LEROBOT_GUI_HOST', '127.0.0.1'),
        port=int(os.environ.get('LEROBOT_GUI_PORT', '8080')),
        reload=False,
        show=os.environ.get('LEROBOT_GUI_SHOW', '1') == '1',
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
