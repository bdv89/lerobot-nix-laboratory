# Correction: Ajout des IDs Robot et Téléop

> **Note historique** : notes de correction d'octobre 2025 (Windows, ports COM, LeRobot 0.4). Le code et les commandes cités ont évolué depuis : voir le [README](./README.md) et le [CHANGELOG](./CHANGELOG.md).

## Problème identifié

Le bouton "Démarrer l'enregistrement" lançait le processus mais **les mouvements du bras leader ne provoquaient ni la réaction du bras follower, ni l'enregistrement**.

### Cause racine

La commande CLI qui fonctionne:
```bash
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=COM4 \
    --robot.id=my_follower \
    --teleop.type=so101_leader \
    --teleop.port=COM3 \
    --teleop.id=my_leader
```

Le wrapper GUI générait:
```bash
python -m lerobot.scripts.lerobot_record \
    --robot.type=so101_follower \
    --robot.port=COM4 \
    --teleop.type=so101_leader \
    --teleop.port=COM3
    # ❌ MANQUE: --robot.id et --teleop.id
```

**Sans les IDs:**
- LeRobot ne peut pas charger la calibration depuis `.cache/calibration/so101_follower-my_follower.json`
- Les moteurs ne sont pas configurés avec les bons paramètres de calibration
- Le système ne sait pas quelle configuration de robot utiliser
- Les positions lues du leader ne correspondent pas aux positions attendues par le follower

## Solutions implémentées

### 1. Ajout des paramètres `robot_id` et `teleop_id` au wrapper

**Fichier:** `utils/lerobot_wrapper.py`

**Fonction `record()` (lignes 25-71):**
```python
def record(
    self,
    robot_type: str,
    robot_port: str,
    dataset_repo_id: str,
    num_episodes: int = 1,
    single_task: str = "",
    cameras_config: Optional[dict] = None,
    teleop_type: Optional[str] = None,
    teleop_port: Optional[str] = None,
    robot_id: Optional[str] = None,      # ✅ AJOUTÉ
    teleop_id: Optional[str] = None,     # ✅ AJOUTÉ
    display_data: bool = True,
) -> subprocess.Popen:
    # ...
    if robot_id:
        cmd.append(f"--robot.id={robot_id}")
    # ...
    if teleop_id:
        cmd.append(f"--teleop.id={teleop_id}")
```

**Fonction `replay()` (lignes 84-106):**
```python
def replay(
    self,
    robot_type: str,
    robot_port: str,
    dataset_repo_id: str,
    episode: int = 0,
    robot_id: Optional[str] = None,      # ✅ AJOUTÉ
) -> subprocess.Popen:
    # ...
    if robot_id:
        cmd.append(f"--robot.id={robot_id}")
```

### 2. Ajout des IDs dans la configuration SO101

**Fichier:** `utils/diagnostic.py`

**Nouvelles constantes (lignes 545-547):**
```python
# Default IDs (used for calibration and identification)
FOLLOWER_ID = "my_follower"
LEADER_ID = "my_leader"
```

**Config d'enregistrement mise à jour (lignes 564-577):**
```python
@classmethod
def get_default_record_config(cls) -> dict:
    return {
        'robot_type': cls.FOLLOWER_TYPE,
        'robot_port': cls.FOLLOWER_PORT,
        'robot_id': cls.FOLLOWER_ID,           # ✅ AJOUTÉ
        'teleop_type': cls.LEADER_TYPE,
        'teleop_port': cls.LEADER_PORT,
        'teleop_id': cls.LEADER_ID,            # ✅ AJOUTÉ
        'dataset_name': 'user/so101_dataset',
        'num_episodes': 1,
        'task_name': 'Pick and place',
        'camera_config': cls.DEFAULT_CAMERA_CONFIG,
    }
```

**Config de replay mise à jour (lignes 579-588):**
```python
@classmethod
def get_default_replay_config(cls) -> dict:
    return {
        'robot_type': cls.FOLLOWER_TYPE,
        'robot_port': cls.FOLLOWER_PORT,
        'robot_id': cls.FOLLOWER_ID,           # ✅ AJOUTÉ
        'dataset_name': 'user/so101_dataset',
        'episode': 0,
    }
```

### 3. Ajout des champs ID dans l'interface d'enregistrement

**Fichier:** `main.py`

**Bouton de chargement config mis à jour (lignes 43-54):**
```python
def load_so101_config():
    config = so101_config.get_default_record_config()
    robot_type.value = config['robot_type']
    robot_port.value = config['robot_port']
    robot_id.value = config['robot_id']              # ✅ AJOUTÉ
    teleop_type.value = config['teleop_type']
    teleop_port.value = config['teleop_port']
    teleop_id.value = config['teleop_id']            # ✅ AJOUTÉ
    dataset_name.value = config['dataset_name']
    task_name.value = config['task_name']
    camera_config.value = json.dumps(config['camera_config'], indent=2)
    ui.notify('✅ Configuration SO101 chargée!', type='positive')
```

**Nouveaux champs dans l'interface (lignes 71-94):**
```python
with ui.row().classes('w-full gap-4'):
    robot_type = ui.input(...)
    robot_port = ui.input(...)
    robot_id = ui.input(                             # ✅ AJOUTÉ
        label='ID du robot',
        placeholder='my_follower',
        value='my_follower'
    ).classes('flex-grow')

with ui.row().classes('w-full gap-4'):
    teleop_type = ui.input(...)
    teleop_port = ui.input(...)
    teleop_id = ui.input(                            # ✅ AJOUTÉ
        label='ID téléopération (optionnel)',
        placeholder='my_leader',
        value='my_leader'
    ).classes('flex-grow')
```

**Appel au wrapper mis à jour (lignes 149-161):**
```python
current_process = lerobot.record(
    robot_type=robot_type.value,
    robot_port=robot_port.value,
    robot_id=robot_id.value if robot_id.value else None,         # ✅ AJOUTÉ
    dataset_repo_id=dataset_name.value,
    num_episodes=int(num_episodes.value),
    single_task=task_name.value,
    cameras_config=cameras,
    teleop_type=teleop_type.value if teleop_type.value else None,
    teleop_port=teleop_port.value if teleop_port.value else None,
    teleop_id=teleop_id.value if teleop_id.value else None,      # ✅ AJOUTÉ
    display_data=True,
)
```

### 4. Ajout des champs ID dans l'interface de replay

**Fichier:** `main.py`

**Bouton de chargement config (lignes 374-383):**
```python
def load_so101_replay_config():
    config = so101_config.get_default_replay_config()
    robot_type_replay.value = config['robot_type']
    robot_port_replay.value = config['robot_port']
    robot_id_replay.value = config['robot_id']       # ✅ AJOUTÉ
    dataset_replay.value = config['dataset_name']
    episode_number.value = config['episode']
    ui.notify('✅ Configuration SO101 chargée!', type='positive')
```

**Nouveau champ dans l'interface (lignes 399-403):**
```python
robot_id_replay = ui.input(                          # ✅ AJOUTÉ
    label='ID du robot',
    placeholder='my_follower',
    value='my_follower'
).classes('flex-grow')
```

**Appel au wrapper mis à jour (lignes 432-438):**
```python
current_process = lerobot.replay(
    robot_type=robot_type_replay.value,
    robot_port=robot_port_replay.value,
    robot_id=robot_id_replay.value if robot_id_replay.value else None,  # ✅ AJOUTÉ
    dataset_repo_id=dataset_replay.value,
    episode=int(episode_number.value),
)
```

## Fichiers modifiés

1. **`utils/lerobot_wrapper.py`**
   - Ligne 25-71: Fonction `record()` avec `robot_id` et `teleop_id`
   - Ligne 84-106: Fonction `replay()` avec `robot_id`

2. **`utils/diagnostic.py`**
   - Ligne 545-547: Constantes `FOLLOWER_ID` et `LEADER_ID`
   - Ligne 569-572: IDs ajoutés à `get_default_record_config()`
   - Ligne 585: ID ajouté à `get_default_replay_config()`

3. **`main.py`**
   - Ligne 43-54: Fonction `load_so101_config()` mise à jour
   - Ligne 71-94: Champs `robot_id` et `teleop_id` ajoutés à l'interface d'enregistrement
   - Ligne 149-161: Appel `lerobot.record()` avec les nouveaux paramètres
   - Ligne 374-383: Fonction `load_so101_replay_config()` ajoutée
   - Ligne 399-403: Champ `robot_id_replay` ajouté à l'interface de replay
   - Ligne 432-438: Appel `lerobot.replay()` avec le nouveau paramètre

## Test

### Commande équivalente générée maintenant:

```bash
python -m lerobot.scripts.lerobot_record \
    --robot.type=so101_follower \
    --robot.port=COM4 \
    --robot.id=my_follower \           # ✅ MAINTENANT INCLUS
    --dataset.repo_id=user/so101_dataset \
    --dataset.num_episodes=1 \
    --dataset.single_task=Pick\ and\ place \
    --teleop.type=so101_leader \
    --teleop.port=COM3 \
    --teleop.id=my_leader \             # ✅ MAINTENANT INCLUS
    --display_data=True
```

### Pour tester:

1. **Relancez l'interface:**
   ```bash
   cd lerobot-gui
   python main.py
   ```

2. **Dans l'onglet "📹 Enregistrer":**
   - Cliquez sur "⚡ Charger config SO101"
   - Vérifiez que les champs sont remplis:
     - Robot ID: `my_follower`
     - Téléop ID: `my_leader`
   - Cliquez sur "▶️ Démarrer l'enregistrement"

3. **Vérification:**
   - ✅ Le processus démarre avec les logs visibles
   - ✅ Quand vous bougez le bras leader (COM3), le follower (COM4) doit suivre
   - ✅ Les données sont enregistrées dans le dataset

### Si ça ne fonctionne toujours pas:

Vérifiez dans les logs (fenêtre de log de l'interface) si vous voyez des messages d'erreur du type:
- `"Calibration file not found"` → Relancez la calibration pour les deux bras
- `"Motor X not responding"` → Vérifiez les connexions physiques
- `"Permission denied on COM port"` → Fermez tous les autres programmes utilisant les ports série

## Importance des IDs

Les IDs permettent à LeRobot de:

1. **Charger la bonne calibration** : Chaque robot a sa calibration unique stockée dans `.cache/calibration/<type>-<id>.json`

2. **Identifier les configurations** : Plusieurs robots du même type peuvent coexister avec des calibrations différentes

3. **Tracer les datasets** : Le dataset enregistre quel robot a été utilisé pour la collecte

4. **Reproductibilité** : Permet de rejouer un épisode sur le même robot qui l'a enregistré

Sans les IDs, LeRobot utilise des valeurs par défaut qui ne correspondent pas à vos robots calibrés, d'où l'absence de réaction du follower.
