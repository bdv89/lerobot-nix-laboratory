# 🎉 LeRobot GUI v2.0 - Notes de Version

> **Note historique** : ces notes décrivent la v2.0 (octobre 2025, sous Windows avec ports COM et LeRobot 0.4). Les commandes et chemins ci-dessous ne sont plus d'actualité : pour l'installation et l'usage actuels (flake Nix, LeRobot 0.6), voir le [README](./README.md) et le [CHANGELOG](./CHANGELOG.md).

## 🚀 Mise à Jour Majeure : Connexion Asynchrone

La version 2.0 résout complètement le problème **"connection lost"** avec un système de connexion entièrement repensé.

---

## 🎯 Problèmes Résolus

### ❌ Avant (v1.x)
```
Utilisateur clique "Tester connexion"
   ↓
Interface GUI freeze pendant 30 secondes
   ↓
Aucun feedback sur ce qui se passe
   ↓
Erreur générique: "connection lost"
   ↓
Utilisateur ne sait pas quoi faire
```

### ✅ Après (v2.0)
```
Utilisateur clique "⚡ Test Rapide"
   ↓
Dialogue modal s'ouvre
   ↓
Affichage en temps réel:
  [5%] Vérification pré-connexion... ✓
  [20%] Ouverture port série... ✓
  [35%] Ping moteur shoulder_pan (1/6)... ✓
  [45%] Ping moteur shoulder_lift (2/6)... ✓
  [50%] Ping moteur elbow_flex (3/6)... ❌ TIMEOUT
   ↓
Diagnostic automatique:
  ⚠️ Moteur en échec: elbow_flex (ID 3)
  📋 Causes probables:
    • Moteur non alimenté
    • Câble daisy-chain défectueux
  🔧 Solutions:
    • Vérifier alimentation 12V
    • Tester câblage moteur 3
   ↓
Utilisateur sait exactement quoi faire !
```

---

## 📋 Changements Principaux

### 1. Nouvelle Fonction `connect_robot_async()`

**Localisation** : `utils/diagnostic.py`

**Caractéristiques** :
- ✅ Connexion avec feedback progressif via callbacks
- ✅ Pre-checks automatiques (port existe, accessible, non occupé)
- ✅ Ping de chaque moteur individuellement avec retry
- ✅ Mode rapide (skip calibration) pour test en 5-10s
- ✅ Mode complet (avec calibration) en 15-30s
- ✅ Gestion d'erreur robuste avec diagnostic automatique

**Signature** :
```python
def connect_robot_async(
    robot_type: str,              # "so101_follower"
    port: str,                     # "COM4"
    progress_callback: Callable,   # Fonction appelée à chaque étape
    skip_calibration: bool = True, # Mode rapide par défaut
    timeout_seconds: float = 30.0  # Timeout global
) -> Dict[str, any]
```

**Retour** :
```python
{
    'success': bool,
    'robot': Robot | None,
    'error': str | None,
    'stage': str,  # Étape actuelle ou échec
    'motor_statuses': {
        'shoulder_pan': {'id': 1, 'found': True, 'model': '3215'},
        'shoulder_lift': {'id': 2, 'found': False, 'error': 'Timeout'},
        # ...
    }
}
```

### 2. Nouvelle Fonction `pre_connection_check()`

Vérifie avant de tenter connexion :
- ✅ Port COM existe dans la liste des ports disponibles
- ✅ Port est accessible (pas de permission denied)
- ✅ Port n'est pas déjà utilisé par un autre programme

### 3. Nouvelle Fonction `diagnose_connection_failure()`

Analyse post-échec intelligente :
- Identifie le type d'erreur (port, permission, moteur, timeout, firmware)
- Liste les moteurs qui ont échoué avec leurs IDs
- Fournit causes probables contextuelles
- Suggère solutions spécifiques étape par étape

### 4. Interface GUI Améliorée

**Nouveaux boutons** :
- **⚡ Test Rapide** : Sans calibration (5-10s) - Recommandé pour diagnostic
- **🔍 Test Complet** : Avec calibration (15-30s) - Pour validation finale

**Dialogue de progression** :
- Barre de progression 0-100%
- Label de l'étape en cours
- Log scrollable des étapes passées
- Se ferme automatiquement en cas de succès ou échec

**Affichage résultats** :
- En cas de succès : Status de chaque moteur (✅ ID, nom, status)
- En cas d'échec : Diagnostic complet avec causes et solutions

---

## 📚 Nouvelle Documentation

### TROUBLESHOOTING.md

Guide de dépannage complet avec :

1. **Arbre de décision** : Navigation rapide vers le bon diagnostic
2. **6 sections de problèmes** :
   - Section A : Problèmes de Port
   - Section B : Problèmes de Permissions
   - Section C : Port Déjà Utilisé
   - Section D : Problèmes de Moteurs
   - Section E : Problèmes de Communication
   - Section F : Problèmes de Firmware
3. **Commandes de test rapide** : Scripts Python prêts à l'emploi
4. **Checklist finale** : Si rien ne fonctionne
5. **Table de référence** : Erreur → Solution rapide

---

## 🧪 Comment Tester v2.0

### Test 1 : Connexion Réussie

**Prérequis** :
- Bras SO101 Follower branché sur COM4
- Moteurs alimentés en 12V
- Aucun autre programme n'utilise le port

**Procédure** :
1. Lancer le GUI : `python main.py`
2. Aller dans onglet "🔧 Diagnostic"
3. Vérifier :
   - Type : `so101_follower`
   - Port : `COM4`
4. Cliquer **"⚡ Test Rapide"**

**Résultat attendu** :
```
Dialogue s'ouvre
├─ Barre de progression monte progressivement
├─ Chaque étape s'affiche en temps réel
├─ Ping de chaque moteur visible (1/6, 2/6, etc.)
└─ Dialogue se ferme

Affichage :
✅ Robot connecté avec succès!

📊 Status des Moteurs
✅ shoulder_pan (ID 1): OK
✅ shoulder_lift (ID 2): OK
✅ elbow_flex (ID 3): OK
✅ wrist_flex (ID 4): OK
✅ wrist_roll (ID 5): OK
✅ gripper (ID 6): OK
```

### Test 2 : Moteur Débranché (Diagnostic)

**Setup** :
- Débrancher physiquement un moteur (ex: moteur ID 3)

**Procédure** :
1. Cliquer **"⚡ Test Rapide"**

**Résultat attendu** :
```
Dialogue s'ouvre
├─ [35%] Ping moteur shoulder_pan (1/6)... ✓
├─ [45%] Ping moteur shoulder_lift (2/6)... ✓
├─ [50%] Ping moteur elbow_flex (3/6)... ❌
└─ Dialogue se ferme

Affichage :
❌ Échec: Motor error: Moteur elbow_flex (ID 3) ne répond pas

🔍 Diagnostic
Étape d'échec: motor_error

⚠️ Moteurs en échec:
  • elbow_flex (ID 3): Moteur ne répond pas

📋 Causes probables:
  • Moteur(s) ID [3] non alimenté(s)
  • Câble daisy-chain défectueux
  • Moteur en mode erreur/bloqué

🔧 Solutions suggérées:
  • Vérifier alimentation 12V des moteurs
  • Tester moteur(s) [3] individuellement
  • Vérifier câblage daisy-chain entre moteurs
```

### Test 3 : Port Inexistant

**Setup** :
- Changer port à `COM99` (inexistant)

**Procédure** :
1. Port : `COM99`
2. Cliquer **"⚡ Test Rapide"**

**Résultat attendu** :
```
❌ Échec: Pre-check failed: port_exists

🔍 Diagnostic
📋 Causes probables:
  • Port COM inexistant
  • Câble USB déconnecté

🔧 Solutions suggérées:
  • Scanner les ports disponibles
  • Vérifier connexion USB physique
```

### Test 4 : Port Occupé

**Setup** :
- Ouvrir FeetechDebugger ou Arduino IDE sur COM4
- Garder ouvert pendant le test

**Procédure** :
1. Port : `COM4`
2. Cliquer **"⚡ Test Rapide"**

**Résultat attendu** :
```
❌ Échec: Pre-check failed: port_not_busy

🔍 Diagnostic
📋 Causes probables:
  • Port déjà utilisé par un autre programme

🔧 Solutions suggérées:
  • Fermer autres programmes (Arduino IDE, Putty, etc.)
  • Redémarrer le GUI
```

---

## 🆚 Comparaison v1.x vs v2.0

| Aspect | v1.x | v2.0 |
|--------|------|------|
| **Temps connexion** | 30s (bloquant) | 5-10s (non-bloquant) |
| **Feedback visuel** | ❌ Aucun | ✅ Temps réel |
| **Diagnostic erreur** | "connection lost" | Détaillé + solutions |
| **Identification moteur** | ❌ Non | ✅ Moteur exact + ID |
| **Pre-checks** | ❌ Non | ✅ Oui |
| **Retry moteur** | ❌ Non | ✅ 2 tentatives |
| **Mode rapide** | ❌ Non | ✅ Skip calibration |
| **Interface freeze** | ✅ Oui | ❌ Non |
| **Logs détaillés** | ❌ Non | ✅ Scrollable |

---

## 📦 Fichiers Modifiés

```
lerobot-gui/
├── utils/diagnostic.py         [RÉÉCRITURE COMPLÈTE - 580 lignes]
├── main.py                      [MODIFIÉ - Section diagnostic]
├── CHANGELOG.md                 [MIS À JOUR]
├── TROUBLESHOOTING.md           [NOUVEAU - Guide complet]
└── RELEASE_NOTES_v2.0.md        [NOUVEAU - Ce fichier]
```

---

## ⚙️ Configuration Avancée

### Ajuster Timeouts

Si vos moteurs répondent lentement, vous pouvez ajuster les timeouts :

**Dans `utils/diagnostic.py`, ligne ~119** :
```python
def connect_robot_async(
    # ...
    timeout_seconds: float = 30.0  # Augmenter à 60.0 si nécessaire
)
```

### Ajuster Retries

**Dans `utils/diagnostic.py`, ligne ~192** :
```python
model_number = robot.bus.ping(motor.id, num_retry=2)  # Augmenter à 3 ou 5
```

### Skip Firmware Check

Si vos moteurs ont des firmwares différents (intentionnellement) :

**Dans `utils/diagnostic.py`, ligne ~218-224** :
```python
# Commenter ces lignes pour skip firmware check
# update_progress("Vérification firmware...", 0.65)
# try:
#     robot.bus._assert_same_firmware()
# except Exception as e:
#     result['firmware_warning'] = str(e)
```

---

## 🐛 Problèmes Connus v2.0

### 1. Première Connexion Peut Être Plus Longue
**Symptôme** : Premier test prend 15-20s au lieu de 5-10s

**Cause** : Initialisation Python/imports

**Solution** : Normal, les tests suivants seront rapides

### 2. Dialogue Ne Se Ferme Pas Sur Certains Systèmes
**Symptôme** : Dialogue reste ouvert même après succès/échec

**Cause** : Bug NiceGUI sur certaines versions

**Solution** : Cliquer en dehors du dialogue pour le fermer manuellement

---

## 🔄 Migration depuis v1.x

### Pas de Breaking Changes

v2.0 est **100% rétro-compatible**. Toutes les autres fonctionnalités (Enregistrement, Datasets, Replay) fonctionnent exactement pareil.

### Changements Visibles

1. **Bouton "Tester connexion"** remplacé par **"⚡ Test Rapide"** et **"🔍 Test Complet"**
2. **Nouveau dialogue de progression** apparaît pendant le test
3. **Affichage diagnostic** en cas d'échec plus détaillé

### Aucune Action Requise

Relancez simplement le GUI :
```bash
cd lerobot-gui
python main.py
```

---

## 📞 Support

### En Cas de Problème

1. **Consulter TROUBLESHOOTING.md** : Guide de dépannage complet
2. **Vérifier CONNECT_ROBOTS.md** : Guide de connexion des robots
3. **Regarder les logs** : Le dialogue affiche les logs détaillés
4. **Ouvrir une issue** : https://github.com/huggingface/lerobot/issues

### Informations à Fournir

Quand vous signalez un bug v2.0, incluez :
```
1. Version OS
2. Logs du dialogue de progression (copier/coller)
3. Message d'erreur exact
4. Résultat du diagnostic automatique
5. Résultat de "Scanner les ports"
```

---

## 🎓 Pour les Développeurs

### Utiliser `connect_robot_async()` dans Votre Code

```python
from utils.diagnostic import RobotDiagnostic

def my_progress_callback(stage: str, progress: float, details: dict):
    print(f"[{int(progress*100)}%] {stage}")

result = RobotDiagnostic.connect_robot_async(
    robot_type="so101_follower",
    port="COM4",
    progress_callback=my_progress_callback,
    skip_calibration=True,
    timeout_seconds=30.0
)

if result['success']:
    robot = result['robot']
    # Utiliser robot...
    robot.disconnect()
else:
    print(f"Échec: {result['error']}")
    # Diagnostic
    diagnosis = RobotDiagnostic.diagnose_connection_failure(
        port="COM4",
        error=result['error'],
        stage=result['stage'],
        motor_statuses=result['motor_statuses']
    )
    print(diagnosis)
```

---

## 🙏 Remerciements

- Équipe LeRobot / HuggingFace
- Communauté Feetech
- Testeurs beta v2.0

---

**Profitez de LeRobot GUI v2.0 ! 🤖✨**
