# 🔧 Guide de Dépannage - LeRobot GUI

Ce guide suppose la GUI lancée via le flake Nix (`nix run .` ou `nix develop -c python lerobot-gui/main.py`), sous Linux. Les commandes Python ci-dessous se lancent dans `nix develop`, qui fournit LeRobot 0.6.0 et le SDK Feetech (`scservo_sdk`).

Dans les exemples, `$LEROBOT_FOLLOWER_PORT` désigne le port du follower, par exemple `/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00`.

## 🎯 Arbre de Décision Rapide

```
Problème de connexion?
│
├─ "Port not found" / "Port inexistant"
│  └─> Section A: Problèmes de Port
│
├─ "Permission denied" / "Access denied"
│  └─> Section B: Problèmes de Permissions
│
├─ "Port already in use" / "Port occupé"
│  └─> Section C: Port Déjà Utilisé
│
├─ "Motor X not found" / "Moteur ne répond pas"
│  └─> Section D: Problèmes de Moteurs
│
├─ "Timeout" / "Pas de réponse"
│  └─> Section E: Problèmes de Communication
│
├─ "Firmware mismatch"
│  └─> Section F: Problèmes de Firmware
│
└─ Le mauvais bras bouge / le leader se tord
   └─> Section G: Ports Inversés
```

---

## Section A: Problèmes de Port ❌ "Port not found"

### Symptômes
- "Aucun port serie detecte"
- "Failed to open port"
- Liste des ports ne montre pas votre port

### Causes Probables
1. Câble USB déconnecté
2. Bras non alimenté
3. Mauvais chemin de port (alias `by-id` mal recopié, ou `/dev/ttyACM*` qui a changé)

### Solutions

#### 1. Vérifier Connexion Physique
```bash
# Les cartes CH340 des bras doivent apparaître ici
ls -l /dev/serial/by-id/
# usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00 -> ../../ttyACM0
# usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00 -> ../../ttyACM1

# Messages du noyau au branchement
sudo dmesg -w

# Si dispositif non visible:
- Essayer autre port USB
- Essayer autre câble USB (certains ne transportent que l'alimentation)
- Vérifier que le robot est alimenté
```

#### 2. Driver
Sous Linux, aucun driver à installer : le pilote CH340 (`cdc_acm` / `ch341`) est inclus dans le noyau.

#### 3. Scanner Ports Disponibles
Dans le GUI:
1. Onglet "🔧 Diagnostic"
2. Cliquer "Scanner les ports"
3. Noter les ports détectés et leur numéro de série

En ligne de commande : `nix develop -c lerobot-find-port` (débranchez un bras quand l'outil le demande pour savoir lequel est lequel).

---

## Section B: Problèmes de Permissions ❌ "Permission denied"

### Symptômes
- "Permission denied"
- Fonctionne avec `sudo` mais pas en utilisateur normal

### Solutions

#### NixOS (recommandé)
Activez le module, qui donne l'accès aux bras au groupe `dialout` et y ajoute l'utilisateur :

```nix
services.lerobot = {
  enable = true;
  user = "alice";   # votre utilisateur
};
```

Après `nixos-rebuild switch`, **fermez et rouvrez la session** pour que l'appartenance aux groupes `dialout` et `video` soit prise en compte. Vérifiez avec `id`.

#### Autre distribution Linux
```bash
# Ajouter utilisateur au groupe dialout
sudo usermod -a -G dialout $USER

# Puis fermer et rouvrir la session (ou redémarrer)

# Vérifier permissions du port
ls -lL /dev/serial/by-id/usb-1a86_*
# Devrait montrer: crw-rw---- 1 root dialout
```

---

## Section C: Port Déjà Utilisé ❌ "Port already in use"

### Symptômes
- "Port already open"
- "Device or resource busy"
- Fonctionnait avant, plus maintenant

### Causes
1. Autre programme utilise le port
2. Instance GUI précédente non fermée (ou service `lerobot-gui` déjà lancé par `gui.autostart`)
3. Processus LeRobot (`lerobot-record`, `lerobot-teleoperate`…) resté actif

### Solutions

#### 1. Fermer Autres Programmes
Programmes à vérifier:
- Arduino IDE
- minicom / screen / picocom
- Autres GUI robotiques
- Instances précédentes du GUI LeRobot
- Le service : `systemctl status lerobot-gui`

#### 2. Trouver Process Utilisant le Port

```bash
# Trouver quel process utilise le port
nix shell nixpkgs#lsof -c lsof "$(readlink -f "$LEROBOT_FOLLOWER_PORT")"

# Tuer le process
kill [PID]
```

#### 3. Débrancher/Rebrancher
Simple mais efficace:
1. Débrancher câble USB
2. Attendre 5 secondes
3. Rebrancher
4. Réessayer

---

## Section D: Problèmes de Moteurs ❌ "Motor not found"

### Symptômes
- "Moteur shoulder_pan (ID 1) ne répond pas"
- "Missing motor IDs: [1, 2]"
- Certains moteurs trouvés, d'autres non

### Diagnostic Rapide

#### 1. Vérifier Alimentation
```
✅ Checklist:
[ ] Bloc d'alimentation branché (≈ 12 V pour le follower ; le leader est alimenté en ≈ 5 V)
[ ] LED d'alimentation allumée sur le bras
[ ] Fusible OK
```

#### 2. Identifier Moteur Problématique
En cas d'échec, le GUI indique le premier moteur qui ne répond pas :
```
Echec: Motor error: Moteur shoulder_pan (ID 1) ne répond pas
```

Quand la connexion réussit, le GUI liste l'état de chacun des 6 moteurs.

→ Problème sur moteur ID 1

#### 3. Test Individuel

**Méthode 1: Via FeetechDebugger**
1. Télécharger FeetechDebugger (FD Tool, outil Windows du fabricant)
2. Scanner IDs présents
3. Vérifier ID du moteur problématique

**Méthode 2: Via Python (avancé)**

Dans `nix develop` :

```python
import os
from scservo_sdk import *

port = os.environ["LEROBOT_FOLLOWER_PORT"]
baudrate = 1000000
PROTOCOL_VERSION = 0

portHandler = PortHandler(port)
packetHandler = PacketHandler(PROTOCOL_VERSION)

portHandler.openPort()
portHandler.setBaudRate(baudrate)

# Tester moteur ID 1
model_number, comm, error = packetHandler.ping(portHandler, 1)
print(f"Motor 1: model={model_number}, comm={comm}, error={error}")

portHandler.closePort()
```

### Solutions

#### Moteur Ne Répond Pas
1. **Vérifier câblage daisy-chain**
   - Débrancher tous moteurs sauf le premier
   - Tester le premier moteur seul
   - Ajouter moteurs un par un

2. **Vérifier ID moteur**
   - Utiliser FeetechDebugger pour scanner
   - Si ID différent, le changer avec FD Tool, ou avec `lerobot-setup-motors`

3. **Vérifier baudrate**
   - Par défaut: 1000000 (1 Mbps)
   - Tester avec baudrate 115200 si problème

4. **Moteur en erreur**
   - LED rouge clignotante = erreur
   - Débloquer mécaniquement le moteur
   - Réinitialiser avec FD Tool

---

## Section E: Problèmes de Communication ❌ "Timeout"

### Symptômes
- "Timeout de communication"
- "COMM_RX_TIMEOUT"
- Connexion instable
- Fonctionne parfois, échoue d'autres fois (souvent en pleine trajectoire)

### Causes
1. Autosuspend USB qui coupe la carte des bras
2. Interférences électromagnétiques
3. Câble trop long ou de mauvaise qualité
4. Alimentation instable

### Solutions

#### 1. Autosuspend USB
Sur NixOS, le module `services.lerobot` désactive l'autosuspend des cartes des bras (et de la caméra si `camera.usbId` est défini). La GUI tente aussi de le désactiver avant chaque téléopération, enregistrement ou exécution, mais sans le module elle n'en a généralement pas le droit (message `USB autosuspend: permission denied` dans le terminal).

```bash
# Vérifier : "on" = autosuspend désactivé
cat /sys/bus/usb/devices/*/power/control
```

#### 2. Réduire Interférences
```
❌ À éviter:
- Moteurs près d'alimentation à découpage
- Câbles parallèles à câbles secteur
- Câbles non blindés

✅ Recommandé:
- Câble USB blindé court (<1m)
- Éloigner sources d'interférence
- Ferrite sur câble USB
- Alimentation stable de qualité
```

#### 3. Tester Baudrate Réduit
Modifier dans le code (avancé, depuis un clone du dépôt, lancé avec `nix develop -c python lerobot-gui/main.py`) :
```python
# Dans utils/diagnostic.py, connect_robot_async()
robot.bus.port_handler.setBaudRate(115200)  # Au lieu de 1000000
```

#### 4. Vérifier Alimentation
```bash
# Mesurer voltage pendant opération
# Le follower doit rester stable (≈ 12 V)
# Si chute importante: alimentation insuffisante

Solution:
- Alimentation plus puissante (5A minimum)
- Câbles d'alimentation plus gros
- Vérifier connexions
```

---

## Section F: Problèmes de Firmware ❌ "Firmware mismatch"

### Symptômes
- "Motors use different firmware versions"
- Versions firmware différentes entre moteurs
- Comportement incohérent

### Vérifier Firmware
Le test de connexion du GUI vérifie que tous les moteurs ont le même firmware, mais un écart n'est pas bloquant et n'est pas affiché dans l'interface. Pour lire les versions, utilisez FD Tool.

### Solution
Mettre à jour firmware:
1. Télécharger FD Tool (Feetech Debugger)
2. Connecter moteur individuellement
3. Lire firmware actuelle
4. Flasher firmware uniforme sur tous
5. Vérifier que tous ont même version

---

## Section G: Ports Inversés ❌ "Le mauvais bras bouge"

### Symptômes
- Au lancement de la téléopération, le leader se raidit ou se tord
- Le follower ne suit pas, ou bouge tout seul

### Cause
Les ports follower et leader sont inversés. Sans `LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT`, la GUI prend les alias `/dev/serial/by-id/usb-1a86_*` dans l'ordre alphabétique, qui ne correspond pas forcément à vos bras. Les noms `/dev/ttyACM*` directs, eux, s'inversent au rebranchement.

### Solution
1. Identifier les bras sans activer le couple (lecture seule), depuis `lerobot-gui/` :
   ```bash
   nix develop -c python tests/hw_identify_arms.py            # ≈ 5 V = leader, ≈ 12 V = follower
   nix develop -c python tests/hw_identify_arms.py --watch 8  # bougez UN bras pendant 8 s
   ```
2. Fixer les ports : `services.lerobot.followerPort` / `leaderPort` sur NixOS, ou les variables `LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT`

---

## 🚀 Commandes de Test Rapide

Toutes ces commandes se lancent dans `nix develop`.

### Test 1: Vérification Basique Port
```python
import os, serial
ser = serial.Serial(os.environ["LEROBOT_FOLLOWER_PORT"], baudrate=1000000, timeout=1)
print(f"Port opened: {ser.is_open}")
ser.close()
```

### Test 2: Scan Tous les IDs
```python
import os
from scservo_sdk import *

def scan_all_ids(port, baudrate=1000000):
    portHandler = PortHandler(port)
    packetHandler = PacketHandler(0)

    portHandler.openPort()
    portHandler.setBaudRate(baudrate)

    found = []
    for id in range(1, 254):
        model, comm, error = packetHandler.ping(portHandler, id)
        if comm == COMM_SUCCESS:
            found.append((id, model))
            print(f"Found motor ID {id}: model {model}")

    portHandler.closePort()
    return found

# Utilisation
found_motors = scan_all_ids(os.environ["LEROBOT_FOLLOWER_PORT"])
print(f"Total motors found: {len(found_motors)}")
```

### Test 3: Test Connexion Minimale
```bash
python -c "
import os
from lerobot.robots.so101_follower import SO101FollowerConfig
from lerobot.robots import make_robot_from_config

config = SO101FollowerConfig(port=os.environ['LEROBOT_FOLLOWER_PORT'])
robot = make_robot_from_config(config)

# Test juste ouverture port
if robot.bus.port_handler.openPort():
    print('✅ Port opened successfully')
    robot.bus.port_handler.closePort()
else:
    print('❌ Failed to open port')
"
```

---

## 📊 Table de Dépannage Rapide

| Erreur | Cause Probable | Solution Rapide |
|--------|----------------|-----------------|
| Port not found | Câble déconnecté | Rebrancher USB, `ls /dev/serial/by-id/` |
| Permission denied | Manque droits | Module `services.lerobot` / groupe `dialout`, rouvrir la session |
| Port in use | Autre programme | Fermer autres programmes, vérifier le service `lerobot-gui` |
| Motor 1 not found | Moteur non alimenté | Vérifier alimentation |
| All motors timeout | Baudrate wrong | Utiliser FeetechDebugger |
| Random timeouts | Autosuspend USB / interférences | Module NixOS, câble blindé court |
| Firmware mismatch | Versions différentes | Mettre à jour firmware |
| Le leader se tord | Ports inversés | Fixer les ports by-id (Section G) |

---

## 🆘 Si Rien ne Fonctionne

### Checklist Finale
1. [ ] Robot alimenté (LED allumée)
2. [ ] Câble USB branché fermement
3. [ ] Carte visible dans `/dev/serial/by-id/`
4. [ ] Port correct (Scanner les ports), follower et leader non inversés
5. [ ] Aucun autre programme n'utilise le port
6. [ ] Permissions OK (groupe `dialout`, session rouverte)
7. [ ] Essayé câble USB différent
8. [ ] Essayé port USB différent du PC
9. [ ] Redémarré l'ordinateur

### Tests de Dernier Recours

#### 1. Test avec Script LeRobot Officiel
```bash
nix develop -c lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=$LEROBOT_FOLLOWER_PORT \
  --teleop.type=so101_leader \
  --teleop.port=$LEROBOT_LEADER_PORT
```

Si ça fonctionne mais pas le GUI → Problème GUI
Si ça ne fonctionne pas non plus → Problème matériel/config

#### 2. Test avec FeetechDebugger
- Utiliser FeetechDebugger officiel
- Si ça fonctionne → Problème Python/LeRobot
- Si ça ne fonctionne pas → Problème hardware

#### 3. Réinitialisation Complète
```bash
# Débrancher TOUT
1. Débrancher alimentation robot
2. Débrancher câble USB
3. Attendre 30 secondes
4. Rebrancher alimentation
5. Attendre LED stabilisée
6. Rebrancher USB
7. Réessayer
```

---

## 📞 Obtenir de l'Aide

### Informations à Fournir
Quand vous demandez de l'aide, incluez:
```
1. Système d'exploitation et version (NixOS ou autre)
2. Révision du flake (sortie de `nix flake metadata`)
3. Message d'erreur EXACT du GUI
4. Résultat du scan des ports (masquez les numéros de série si besoin)
5. Logs du test de connexion et du terminal qui a lancé la GUI
6. Résultat de FeetechDebugger (si testé)
7. Photos du câblage
```

### Ressources
- Documentation LeRobot: https://github.com/huggingface/lerobot
- Forum Feetech: http://www.feetechrc.com/
- Issues GitHub: https://github.com/huggingface/lerobot/issues

---

**Bon dépannage ! 🛠️✨**
