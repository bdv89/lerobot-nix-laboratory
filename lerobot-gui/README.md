# 🤖 LeRobot GUI

Interface graphique web pour piloter un bras LeRobot SO-101 sans passer par le terminal.

La GUI est empaquetée par le flake Nix à la racine du dépôt (voir le [README principal](../README.md)) : Python, PyTorch, OpenCV, NiceGUI et **LeRobot 0.6.0** (celui de nixpkgs) sont fournis par Nix. Il n'y a rien à installer avec pip.

## ✨ Fonctionnalités

L'interface comporte quatre onglets :

- **🔧 Diagnostic** : scanner les ports série, tester la connexion d'un bras (test rapide ou complet), lancer la calibration
- **🔁 Répétition** :
  - *Téléopération* : le follower reproduit en temps réel les mouvements du leader, avec flux caméra optionnel (pas d'enregistrement)
  - *Enregistrer* : enregistrer des démonstrations dans un dataset local, avec boutons Valider / Recommencer / Terminer
  - *Rejouer* : rejouer un épisode enregistré sur le follower
- **🧠 Entraînement** : entraîner une politique (`act`, `diffusion`, `tdmpc`, `vqbet`) sur un dataset local
- **▶️ Autonome** : exécuter une politique entraînée sur le follower pendant une durée donnée
- **🌐 Interface Web** : accessible via navigateur (localhost, ou réseau local si activé)

## 📋 Prérequis

- Linux x86_64 avec [Nix](https://nixos.org/download) et les flakes activés
- Deux bras SO-101 (leader et follower) branchés en USB (cartes CH340)
- Recommandé : NixOS avec le module `services.lerobot`, qui règle les permissions série, l'autosuspend USB et le lien caméra

## 🚀 Lancement

Depuis la racine du dépôt (le dossier qui contient `flake.nix`) :

```bash
nix run .
```

Ou directement depuis GitHub, sans cloner :

```bash
nix run github:bdv89/lerobot-nix-laboratory
```

Pour développer la GUI (le code de `lerobot-gui/` est lu directement, sans reconstruire le paquet) :

```bash
nix develop -c python lerobot-gui/main.py
```

Le serveur démarre sur `http://localhost:8080`.

### Accès depuis un autre appareil

Par défaut, la GUI n'écoute que sur `127.0.0.1`. Pour l'ouvrir au réseau local :

```bash
LEROBOT_GUI_HOST=0.0.0.0 nix run .
```

Puis ouvrez `http://<votre-ip>:8080` dans un navigateur. Avec le module NixOS, l'option `services.lerobot.gui.openFirewall = true;` fait la même chose pour le service (`gui.autostart`) et ouvre le port dans le pare-feu.

## ⚙️ Configuration

Tout se règle par variables d'environnement. Sur NixOS, le module `services.lerobot` les pose pour vous.

| Variable | Rôle | Défaut |
|---|---|---|
| `LEROBOT_FOLLOWER_PORT` | Port série du bras follower | auto-détection (voir ci-dessous) |
| `LEROBOT_LEADER_PORT` | Port série du bras leader | auto-détection |
| `LEROBOT_CAMERA` | Caméra par défaut (chemin ou index OpenCV) | `/dev/lerobot_cam` |
| `LEROBOT_GUI_PORT` | Port HTTP de la GUI | `8080` |
| `LEROBOT_GUI_HOST` | Adresse d'écoute | `127.0.0.1` |
| `LEROBOT_GUI_SHOW` | Ouvrir le navigateur au lancement (`1` / `0`) | `1` |
| `LEROBOT_WORKDIR` | Dossier des entraînements (`outputs/`) et checkpoints (`trained/`) | `~/lerobot` |

### Ports des bras

Utilisez les alias stables `/dev/serial/by-id/usb-1a86_…`, jamais les noms `/dev/ttyACM*` directs, dont l'ordre s'inverse au rebranchement (le follower recevrait alors les consignes du leader).

Avec le module NixOS :

```nix
services.lerobot = {
  enable = true;
  user = "alice";
  followerPort = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00";
  leaderPort   = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00";
  camera.usbId = "05a3:9230";   # crée /dev/lerobot_cam
};
```

Sans ces variables, la GUI prend les alias `/dev/serial/by-id/usb-1a86_*` triés par nom : le premier pour le follower, le second pour le leader. **Cet ordre n'a aucune raison de correspondre à vos bras** : vérifiez-le dans l'onglet Diagnostic, ou fixez les variables.

Pour trouver les identifiants :

```bash
ls -l /dev/serial/by-id/
nix develop -c lerobot-find-port
```

### Caméra

Le champ « Caméra » accepte un chemin (`/dev/lerobot_cam`, `/dev/video0`…) ou un index OpenCV (`0`, `1`…). Le lien `/dev/lerobot_cam` n'existe que si `services.lerobot.camera.usbId` est défini ; sinon, indiquez un index ou un `/dev/videoN` (`v4l2-ctl --list-devices`, disponible dans `nix develop`).

### Dossiers de données

- **Datasets** : `~/.cache/huggingface/lerobot/<user>/<nom>` (emplacement standard de LeRobot)
- **Entraînements** : `$LEROBOT_WORKDIR/outputs/train/<politique>_<dataset>_<date>/`
- **Checkpoints** proposés dans l'onglet Autonome : tout dossier `pretrained_model/` sous `$LEROBOT_WORKDIR/outputs/` ou `$LEROBOT_WORKDIR/trained/`

## 📖 Guide d'utilisation

### 🔧 Diagnostic

1. Allez dans l'onglet **"Diagnostic"**
2. **Scanner les ports** : liste les ports série détectés (description, fabricant, numéro de série)
3. **Test de connexion** : saisissez le type (`so101_follower` ou `so101_leader`) et le port, puis :
   - **Test Rapide (sans calibration)**
   - **Test Complet (avec calibration)**

   Le résultat affiche l'état de chacun des 6 moteurs.
4. **Lancer la calibration** : lance `lerobot-calibrate` pour le type et le port indiqués (l'interaction se fait dans le terminal qui a lancé la GUI)

**Astuce** : commencez toujours par ici pour vérifier quel port correspond à quel bras.

### 🎮 Téléopération

1. Onglet **"Répétition"** → **"Téléopération"**
2. Vérifiez les ports follower et leader (pré-remplis depuis la configuration)
3. Activez ou non la caméra live
4. Cliquez sur **"Demarrer"**, puis bougez le leader : le follower suit

### 📹 Enregistrer des démonstrations

1. Onglet **"Répétition"** → **"Enregistrer"**
2. Renseignez :
   - Dataset (format `user/nom`, ex : `user/so101-demo`)
   - Tâche (ex : `Grab the cube`)
   - Nombre d'épisodes et durée max par épisode
   - Caméra (optionnelle)
3. Cliquez sur **"Demarrer enregistrement"**
4. Pendant l'enregistrement, utilisez les boutons :
   - **Valider episode** : sauvegarde l'épisode et passe au suivant
   - **Recommencer episode** : rejette l'épisode et le refait
   - **Terminer enregistrement** : arrête proprement

Ces boutons écrivent `next`, `redo` ou `stop` dans le fichier de contrôle `/tmp/lerobot_control`, lu par LeRobot grâce au patch Nix [`pkgs/lerobot-control-file.patch`](../pkgs/lerobot-control-file.patch) (variable `LEROBOT_CONTROL_FILE` côté LeRobot, même valeur par défaut). Ils fonctionnent donc même sans clavier ni terminal.

L'enregistrement utilise les ports par défaut (`LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT` ou auto-détection). Si un dataset du même nom contient déjà des épisodes, l'enregistrement le reprend ; s'il est vide ou incomplet, il est recréé. Les datasets restent locaux (pas d'envoi sur le Hub).

### ▶️ Rejouer un épisode

1. Onglet **"Répétition"** → **"Rejouer"**
2. Choisissez un dataset local (bouton **"Rafraichir"** pour mettre à jour la liste) et le numéro d'épisode
3. Cliquez sur **"Demarrer replay"** : le follower reproduit exactement les mouvements enregistrés (pas d'IA)

### 🧠 Entraîner une politique

1. Onglet **"Entraînement"**
2. Choisissez le dataset, la politique (`act` recommandé), le nombre de steps, le batch size et la fréquence de sauvegarde
3. Cliquez sur **"Lancer entrainement"**

La GUI lance, dans `$LEROBOT_WORKDIR` :

```bash
lerobot-train --dataset.repo_id=<user>/<dataset> --policy.type=<politique> --policy.push_to_hub=false \
              --steps=<N> --batch_size=<B> --save_freq=<F> \
              --output_dir=outputs/train/<politique>_<dataset>_<date>
```

LeRobot est en version CPU par défaut (voir les limites dans le [README principal](../README.md)) : un entraînement complet peut être très long.

### 🤖 Mode autonome

1. Onglet **"Autonome"**
2. Choisissez un checkpoint dans la liste, ou indiquez le chemin complet d'un dossier `pretrained_model/`
3. Vérifiez le port follower, la tâche, la durée (en secondes) et la caméra
4. Cliquez sur **"Lancer execution"** ; **"Arreter (urgence)"** stoppe le processus

La GUI lance `lerobot-rollout --strategy.type=base --policy.path=… --duration=…` : le robot exécute la politique pendant la durée indiquée, **sans enregistrer de dataset**. La caméra doit correspondre à celle utilisée à l'entraînement.

> Les checkpoints entraînés avec LeRobot 0.4.x peuvent nécessiter une conversion pour LeRobot 0.6.

## 🛠️ Structure du projet

```
lerobot-gui/
├── main.py                     # Application principale NiceGUI (4 onglets)
├── README.md                   # Ce fichier
├── utils/
│   ├── lerobot_wrapper.py      # Lance les commandes LeRobot (record, replay, teleoperate, train, rollout)
│   ├── diagnostic.py           # Ports, test de connexion, calibration, config SO101 par défaut
│   ├── dataset_utils.py        # Recherche des datasets locaux
│   └── folder_picker.py
└── tests/
    ├── test_ports.py           # Tests unitaires sans matériel
    └── hw_identify_arms.py     # Sonde matérielle en lecture seule (leader/follower)
```

Le paquet Nix est décrit dans [`../pkgs/lerobot-gui.nix`](../pkgs/lerobot-gui.nix). Les tests unitaires tournent avec `nix flake check` à la racine du dépôt, ou à la main depuis `lerobot-gui/` : `nix develop -c python -m unittest tests.test_ports -v`.

## 🐛 Résolution des problèmes

Voir aussi [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) et [CONNECT_ROBOTS.md](./CONNECT_ROBOTS.md).

### Le leader se tord / le mauvais bras bouge

Les ports follower et leader sont inversés. Fixez `LEROBOT_FOLLOWER_PORT` / `LEROBOT_LEADER_PORT` (ou `services.lerobot.followerPort` / `leaderPort`) avec les alias `by-id`. Pour savoir quel bras est lequel sans activer le couple, depuis `lerobot-gui/` : `nix develop -c python tests/hw_identify_arms.py` (≈ 5 V = leader, ≈ 12 V = follower).

### Erreur de port série (« Permission denied »)

- Sur NixOS avec le module : vérifiez que votre utilisateur est bien `services.lerobot.user`, puis fermez et rouvrez la session (ajout au groupe `dialout`)
- Hors NixOS : ajoutez-vous au groupe propriétaire du port (`ls -l /dev/serial/by-id/`, généralement `dialout`), puis rouvrez la session

### Erreur de caméra

- Vérifiez le chemin ou l'index (`ls /dev/video*`, `v4l2-ctl --list-devices`)
- `/dev/lerobot_cam` n'existe que si `services.lerobot.camera.usbId` est défini
- Vérifiez que la caméra n'est pas utilisée par une autre application (pendant l'enregistrement, la GUI n'ouvre pas son propre flux pour laisser la caméra à LeRobot)

## 📝 TODO / Améliorations futures

- [ ] Graphiques de visualisation des données d'épisodes
- [ ] Édition avancée des datasets (supprimer des frames, etc.)
- [ ] Statistiques détaillées des datasets
- [ ] Sauvegarde de configurations de robot favorites
- [ ] Logs détaillés avec téléchargement

## 📄 Licence

Apache-2.0, comme LeRobot. Le projet utilise :
- **NiceGUI** : MIT License
- **LeRobot** : Apache 2.0 License

## 🤝 Contribution

N'hésitez pas à ouvrir des issues ou proposer des améliorations !

## 📧 Support

Pour toute question sur LeRobot, consultez la [documentation officielle](https://github.com/huggingface/lerobot).
