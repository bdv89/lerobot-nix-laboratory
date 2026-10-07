# Changelog - LeRobot GUI

## v2.2 — 2026-10-07 — Migration Nix flake / LeRobot 0.6

La GUI n'utilise plus d'environnement pip/venv ni de clone local de LeRobot : elle est empaquetée par le flake Nix à la racine du dépôt, qui fournit **LeRobot 0.6.0 de nixpkgs** (avant : clone `lerobot/` v0.4.1, `shell.nix` + `.venv`, et auparavant Windows).

### Modifié
- **Lancement** : `nix run .` (ou `nix run github:bdv89/lerobot-nix-laboratory`), ou `nix develop -c python lerobot-gui/main.py` pour développer. Plus de `requirements.txt` à installer, plus de shell Nix classique ni de `.venv`, plus de lanceur Windows.
- **Ports des bras** : lus dans `LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT` (posées par le module NixOS `services.lerobot.followerPort` / `leaderPort`), sinon auto-détection des alias `/dev/serial/by-id/usb-1a86_*` (premier = follower, second = leader). Plus de port en dur.
- **Caméra** : `LEROBOT_CAMERA`, défaut `/dev/lerobot_cam` (lien créé par le module si `camera.usbId` est défini).
- **Serveur** : port HTTP via `LEROBOT_GUI_PORT` (défaut 8080), adresse d'écoute via `LEROBOT_GUI_HOST` (défaut `127.0.0.1`).
- **Dossier de travail** (`outputs/`, `trained/`) : `LEROBOT_WORKDIR`, défaut `~/lerobot`.
- **Permissions** : accès série (groupe `dialout`), règles udev et autosuspend USB gérés par le module NixOS `modules/lerobot.nix`. Plus de `sudo` ni de `chmod` manuels.
- **Onglet Autonome** : utilise `lerobot-rollout --strategy.type=base` (durée en secondes, sans enregistrement de dataset `eval_`). Les boutons « Episode suivant » / « Terminer » de cet onglet sont retirés.
- **Onglet Entraînement** : `lerobot-train --policy.type=… --steps --batch_size --save_freq --output_dir=outputs/train/<politique>_<dataset>_<date>`.

### Corrigé
- **Onglet Enregistrement** : les boutons Valider / Recommencer / Terminer fonctionnent via le fichier de contrôle `/tmp/lerobot_control`, lu par LeRobot grâce au patch Nix `pkgs/lerobot-control-file.patch` (variable `LEROBOT_CONTROL_FILE`).

## 2026-09-22 - Ports série stables

### Corrigé
- **Le bras leader se tordait au lancement de la téléopération** : `SO101Config` utilisait `/dev/ttyACM0/1` en dur, qui s'inversent après un rebranchement, et le driver follower pilotait alors le leader. Les ports passent aux alias stables `/dev/serial/by-id/` (follower `XXXXXXXXXX`, leader `YYYYYYYYYY`).
- `RobotDiagnostic.pre_connection_check` résout les liens `by-id` (`os.path.realpath`) : un chemin `by-id` n'est plus déclaré « port absent ».

### Ajouté
- `tests/test_ports.py` : tests unitaires sans matériel (`python -m unittest tests.test_ports -v`).
- `tests/hw_identify_arms.py` : sonde matérielle en lecture seule (aucun couple activé). Lit tension, couple et position par port ; ~5,5 V = leader, ~12,5 V = follower. Option `--watch N` pour détecter le bras qu'on bouge.

## v2.0.0 - 2025-10-31 🎉 MAJOR UPDATE

### 🚀 Connexion Asynchrone avec Progression

**Remplacement complet du système de connexion**

#### Nouvelles Fonctionnalités
- ✅ **Connexion asynchrone** : Ne bloque plus l'interface GUI
- ✅ **Feedback progressif** : Affiche chaque étape en temps réel
  - Vérification pré-connexion
  - Ouverture port série
  - Ping de chaque moteur individuellement (1/6, 2/6, etc.)
  - Vérification firmware
  - Configuration moteurs
- ✅ **Dialogue de progression** : Modal avec barre de progression + log
- ✅ **Deux modes de test** :
  - ⚡ **Test Rapide** : Sans calibration (5-10s)
  - 🔍 **Test Complet** : Avec calibration (15-30s)
- ✅ **Diagnostic automatique** : En cas d'échec, affiche:
  - Étape exacte de l'échec
  - Moteurs qui ont échoué avec leurs IDs
  - Causes probables
  - Solutions suggérées étape par étape

#### Améliorations Techniques
- ✅ **Pre-connection checks** : Vérifie port avant connexion
  - Port existe
  - Port accessible
  - Port non occupé
- ✅ **Ping avec retry** : 2 tentatives par moteur
- ✅ **Timeouts intelligents** : Timeout par étape au lieu de global
- ✅ **Status moteur détaillé** : Affiche ID, nom, status pour chaque moteur
- ✅ **Gestion d'erreur robuste** : Catch et diagnostique toutes les erreurs

#### Nouveaux Fichiers
- ✅ **`utils/diagnostic.py` v2.0** : Réécriture complète (580 lignes)
  - `connect_robot_async()` : Connexion avec callbacks
  - `pre_connection_check()` : Vérifications préliminaires
  - `diagnose_connection_failure()` : Analyse post-échec
- ✅ **`TROUBLESHOOTING.md`** : Guide complet de dépannage
  - Arbre de décision
  - 6 sections de problèmes courants
  - Commandes de test rapide
  - Checklist finale

### 📊 Expérience Utilisateur

**Avant v2.0** :
```
[Clic] "Tester connexion"
[Attente... 30s de freeze]
❌ "Connection lost"
```

**Après v2.0** :
```
[Clic] "⚡ Test Rapide"

Dialogue modal:
├─ [5%]  Vérification pré-connexion... ✓
├─ [20%] Ouverture port série... ✓
├─ [35%] Ping moteur shoulder_pan (1/6)... ✓
├─ [45%] Ping moteur shoulder_lift (2/6)... ✓
├─ [50%] Ping moteur elbow_flex (3/6)... ✓
├─ [55%] Ping moteur wrist_flex (4/6)... ✓
├─ [60%] Ping moteur wrist_roll (5/6)... ✓
├─ [63%] Ping moteur gripper (6/6)... ✓
├─ [70%] Configuration timeouts... ✓
└─ [100%] Connexion réussie! ✓

Résultat:
📊 Status des Moteurs
✅ shoulder_pan (ID 1): OK
✅ shoulder_lift (ID 2): OK
✅ elbow_flex (ID 3): OK
✅ wrist_flex (ID 4): OK
✅ wrist_roll (ID 5): OK
✅ gripper (ID 6): OK
```

**Si échec sur moteur 3** :
```
❌ Échec à l'étape "motor_error"

🔍 Diagnostic
Étape d'échec: motor_error

⚠️ Moteurs en échec:
  • elbow_flex (ID 3): Timeout

📋 Causes probables:
  • Moteur(s) ID [3] non alimenté(s)
  • Câble daisy-chain défectueux
  • Moteur en mode erreur/bloqué

🔧 Solutions suggérées:
  • Vérifier alimentation 12V des moteurs
  • Tester moteur(s) [3] individuellement
  • Vérifier câblage daisy-chain entre moteurs
  • Utiliser FeetechDebugger pour scanner IDs réels
```

### 📝 Documentation
- ✅ Guide de dépannage complet (TROUBLESHOOTING.md)
- ✅ Exemples de tests rapides Python
- ✅ Arbre de décision pour diagnostic
- ✅ Table de référence erreurs communes

---

## v1.0.1 - 2025-10-31

### 🐛 Corrections

- **Diagnostic** : Correction de l'import `make_robot` → `make_robot_from_config`
- **Diagnostic** : Utilisation de `RobotConfig` pour créer les configurations robot
- **Diagnostic** : Méthode `scan_motors` utilise maintenant le robot connecté au lieu de scanner directement
- **Diagnostic** : Méthode `get_motor_status` utilise le bus moteur du robot

### 📝 Détails Techniques

#### Import corrigé
```python
# ❌ Ancien (ne fonctionne pas)
from lerobot.robots import make_robot

# ✅ Nouveau (fonctionne)
from lerobot.robots import make_robot_from_config, RobotConfig
```

#### Configuration robot
```python
# Création d'une config
config = RobotConfig(type=robot_type, port=port)

# Création du robot
robot = make_robot_from_config(config)
robot.connect()
```

---

## v1.0.0 - 2025-10-31

### 🎉 Version Initiale

#### Fonctionnalités
- ✅ Interface web avec NiceGUI
- ✅ Page de diagnostic complète
- ✅ Page d'enregistrement
- ✅ Page de gestion des datasets
- ✅ Page de combinaison de datasets
- ✅ Page de replay
- ✅ Configuration SO101 pré-remplie
- ✅ Mode sombre

#### Diagnostic
- Scan des ports série
- Test de connexion robot
- Scan des moteurs
- Status des moteurs (position, température, voltage, courant)
- Lancement de la calibration

#### Enregistrement
- Configuration robot (type, port)
- Configuration téléopération
- Configuration dataset
- Configuration caméras JSON
- Bouton "Charger config SO101"

#### Datasets
- Liste des datasets
- Visualisation
- Suppression

#### Combinaison
- Sélection multiple de datasets
- Agrégation en un seul dataset

#### Replay
- Sélection dataset et épisode
- Replay sur le robot
