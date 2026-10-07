# 🔌 Guide de Connexion des Robots SO101

## 📋 Prérequis

- 2 bras SO101 (Leader et Follower)
- 2 câbles USB (données, pas seulement charge)
- Alimentation pour les bras
- Linux x86_64 avec Nix (flakes activés) ; idéalement NixOS avec le module `services.lerobot` (voir le [README principal](../README.md))

Sous Linux, aucun driver à installer : les cartes CH340 des bras sont reconnues par le noyau.

---

## 🔧 Étape 1 : Connexion Physique

### 1. **Brancher l'alimentation**
- Connectez l'alimentation électrique à chaque bras
- ⚠️ **Vérifiez que les bras sont alimentés avant de brancher l'USB**

### 2. **Brancher les câbles USB**
1. **Bras Leader** → Port USB de votre ordinateur
2. **Bras Follower** → Port USB de votre ordinateur

### 3. **Vérifier la détection**
```bash
ls -l /dev/serial/by-id/
```
Vous devriez voir 2 entrées `usb-1a86_…`, une par bras :
```
usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00 -> ../../ttyACM0
usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00 -> ../../ttyACM1
```

---

## 🖥️ Étape 2 : Identifier les Ports

⚠️ **Utilisez toujours les alias `/dev/serial/by-id/…`.** Les noms `/dev/ttyACM*` vers lesquels ils pointent s'inversent au rebranchement : le follower recevrait alors les consignes destinées au leader, et c'est le leader qui se tord.

### Méthode 1 : `lerobot-find-port`

```bash
nix develop -c lerobot-find-port
```
L'outil demande de débrancher un bras et indique le port qui a disparu.

### Méthode 2 : Via le GUI LeRobot 🎯

1. Lancez le GUI : `nix run .` (à la racine du dépôt)
2. Allez dans l'onglet **🔧 Diagnostic**
3. Cliquez sur **"Scanner les ports"**
4. Notez les ports détectés et leur numéro de série

### Méthode 3 : Sonde en lecture seule

Depuis `lerobot-gui/`, sans activer le couple des moteurs :
```bash
nix develop -c python tests/hw_identify_arms.py            # ≈ 5 V = leader, ≈ 12 V = follower
nix develop -c python tests/hw_identify_arms.py --watch 8  # bougez UN bras pendant 8 s
```

---

## 🎯 Étape 3 : Fixer la Configuration

### Sur NixOS (recommandé)

```nix
services.lerobot = {
  enable = true;
  user = "alice";
  followerPort = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00";
  leaderPort   = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00";
  camera.usbId = "05a3:9230";   # optionnel : crée /dev/lerobot_cam
};
```

Le module pose `LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT`, règle les permissions (groupe `dialout`) et désactive l'autosuspend USB des bras. Après `nixos-rebuild switch`, fermez et rouvrez la session.

### Ailleurs

```bash
export LEROBOT_FOLLOWER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00
export LEROBOT_LEADER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00
nix run .
```

Sans ces variables, la GUI prend les deux alias `usb-1a86_*` dans l'ordre alphabétique (premier = follower), ce qui ne correspond pas forcément à vos bras.

### Configuration Typique

| Bras | Type | Port |
|------|------|------|
| **Leader** (vous bougez) | `so101_leader` | `$LEROBOT_LEADER_PORT` |
| **Follower** (qui suit) | `so101_follower` | `$LEROBOT_FOLLOWER_PORT` |

---

## ✅ Étape 4 : Tester la Connexion et les Moteurs

### Via le GUI (Méthode Facile)

1. Dans l'onglet **🔧 Diagnostic**
2. Section **Test de Connexion** :
   - Type: `so101_follower`
   - Port: le port du follower (pré-rempli)
3. Cliquez sur **"Test Rapide (sans calibration)"**
4. ✅ Résultat attendu : "Robot connecte !" et **6 moteurs OK** (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper)

5. Répétez pour le Leader :
   - Type: `so101_leader`
   - Port: le port du leader

En cas d'échec, le message indique l'étape et, le cas échéant, le moteur qui ne répond pas.

---

## 📐 Étape 5 : Calibration

Si les bras n'ont jamais été calibrés sur cette machine :

1. Dans **🔧 Diagnostic** → **Calibration**
2. Type et port du bras, puis **"Lancer la calibration"**
3. Suivez les instructions dans le terminal qui a lancé la GUI

Ou en ligne de commande :
```bash
nix develop -c lerobot-calibrate --robot.type=so101_follower --robot.port=$LEROBOT_FOLLOWER_PORT
nix develop -c lerobot-calibrate --teleop.type=so101_leader --teleop.port=$LEROBOT_LEADER_PORT
```

Les calibrations sont stockées dans `~/.cache/huggingface/lerobot/calibration/`.

---

## 🎮 Étape 6 : Test de Téléopération

### Méthode 1 : Via le GUI

1. Allez dans **🔁 Répétition** → **Téléopération**
2. Vérifiez les ports follower et leader
3. Cliquez sur **"Demarrer"**

**Bougez le bras Leader** → Le Follower doit suivre en temps réel ! ✨

### Méthode 2 : Via Terminal

```bash
nix develop -c lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=$LEROBOT_FOLLOWER_PORT \
  --teleop.type=so101_leader \
  --teleop.port=$LEROBOT_LEADER_PORT
```

---

## ❌ Problèmes Courants

### "Aucun port detecte"

**Solutions** :
- ✅ Vérifiez que les bras sont **allumés** (alimentation)
- ✅ Débranchez/rebranchez les câbles USB
- ✅ Essayez d'autres ports USB de votre PC, ou un autre câble
- ✅ Regardez `sudo dmesg -w` pendant le branchement

### "Permission denied"

**Solutions** :
- ✅ NixOS : activez `services.lerobot` avec votre utilisateur, puis rouvrez la session
- ✅ Autre distribution : `sudo usermod -a -G dialout $USER`, puis rouvrez la session

### "Connection failed: timeout"

**Solutions** :
- ✅ Vérifiez que vous utilisez le **bon port**
- ✅ Vérifiez que les **moteurs sont alimentés**
- ✅ Fermez tout autre logiciel qui pourrait utiliser le port série
- ✅ Essayez de réduire le baudrate (rare)

### "Robot type 'XXX' not supported"

**Solutions** :
- ✅ Vérifiez l'orthographe : `so101_follower` (pas `so-101` ou `SO101`)
- ✅ Types supportés par le Diagnostic : `so101_follower`, `so101_leader`, `so100_follower`, `so100_leader`, `koch_follower`

### Les ports changent à chaque branchement

**Solution** :
- C'est le cas des noms `/dev/ttyACM*`. Utilisez les alias `/dev/serial/by-id/…`, qui sont liés au numéro de série de chaque carte et ne changent pas.

### Le leader se tord / le Follower ne bouge pas pendant la téléopération

**Solutions** :
- ✅ Les ports sont probablement **inversés** : identifiez les bras (Étape 2, méthode 3) et fixez les ports (Étape 3)
- ✅ Vérifiez que les **moteurs ne sont pas en mode torque désactivé**
- ✅ Essayez de calibrer les bras : Diagnostic → **Lancer la calibration**

---

## 📝 Checklist de Connexion Rapide

- [ ] Bras Leader branché en USB
- [ ] Bras Follower branché en USB
- [ ] Les 2 bras sont alimentés électriquement
- [ ] Deux alias `usb-1a86_…` visibles dans `/dev/serial/by-id/`
- [ ] Ports follower et leader fixés (module NixOS ou variables)
- [ ] Test de connexion réussi pour Leader
- [ ] Test de connexion réussi pour Follower (6 moteurs OK)
- [ ] Téléopération fonctionne (Follower suit le Leader)

✅ **Si toutes les cases sont cochées, vous êtes prêt à enregistrer !** 🎉

---

## 🆘 Besoin d'Aide ?

1. **Vérifiez les logs** dans le terminal où le GUI tourne (ou `journalctl -u lerobot-gui` pour le service)
2. **Regardez les détails d'erreur** dans le GUI
3. **Consultez [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**
4. **Consultez la documentation LeRobot** : https://github.com/huggingface/lerobot
5. **Ouvrez une issue** si le problème persiste

---

**Bon robotage ! 🤖✨**
