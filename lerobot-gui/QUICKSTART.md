# 🚀 Guide de Démarrage Rapide - LeRobot GUI

## Démarrage Express

### 1️⃣ Installer Nix

Nix avec les flakes activés suffit : il fournit Python, LeRobot 0.6.0, NiceGUI et toutes les dépendances. Pas de `requirements.txt`, pas de venv.

Sur NixOS, activez de préférence le module `services.lerobot` (voir le [README principal](../README.md)) : il règle les permissions série et l'autosuspend USB, et fixe les ports des bras.

### 2️⃣ Démarrer le GUI

Depuis la racine du dépôt :

```bash
nix run .
```

Ou sans cloner :

```bash
nix run github:bdv89/lerobot-nix-laboratory
```

### 3️⃣ Ouvrir dans le navigateur

L'interface sera disponible sur : **http://localhost:8080** (le navigateur s'ouvre normalement tout seul).

---

## ⚡ Workflow SO101 Recommandé

### Étape 1 : Diagnostic (5 min)

1. Allez dans l'onglet **🔧 Diagnostic**
2. Cliquez sur **"Scanner les ports"** → vérifiez que deux ports `/dev/serial/by-id/usb-1a86_…` sont présents
3. Testez la connexion avec **"Test Rapide"** :
   - `so101_follower` sur le port follower
   - `so101_leader` sur le port leader
4. Le résultat doit afficher 6 moteurs OK par bras
5. Si les bras ne sont pas encore calibrés : **"Lancer la calibration"** pour chacun

### Étape 2 : Téléopération (test)

1. Allez dans l'onglet **🔁 Répétition** → **Téléopération**
2. Cliquez sur **"Demarrer"**, bougez le leader : le follower doit suivre
3. Si c'est le leader qui bouge ou se tord, les ports sont inversés (voir plus bas)

### Étape 3 : Enregistrement

1. **🔁 Répétition** → **Enregistrer**
2. Renseignez :
   - Nom du dataset (ex : `user/pick_cube`)
   - Nombre d'épisodes
   - Tâche à accomplir
3. Cliquez sur **"Demarrer enregistrement"**
4. Effectuez la tâche avec le bras leader, le follower suit
5. Utilisez **Valider episode**, **Recommencer episode** ou **Terminer enregistrement**

### Étape 4 : Replay

1. **🔁 Répétition** → **Rejouer**
2. Sélectionnez le dataset et l'épisode
3. Cliquez sur **"Demarrer replay"**
4. Le robot reproduit la séquence !

### Étape 5 : Entraînement et exécution autonome

1. Onglet **🧠 Entraînement** : choisissez le dataset et la politique (`act`), puis **"Lancer entrainement"** (long sur CPU)
2. Onglet **▶️ Autonome** : choisissez le checkpoint produit, une durée en secondes, puis **"Lancer execution"**

---

## 🔧 Configuration par Défaut SO101

Les valeurs par défaut viennent des variables d'environnement (posées par le module NixOS) :

- **Follower** : `so101_follower` sur `$LEROBOT_FOLLOWER_PORT`
- **Leader** : `so101_leader` sur `$LEROBOT_LEADER_PORT`
- **Caméra** : `$LEROBOT_CAMERA` (défaut `/dev/lerobot_cam`), 640x480@30fps
- **Dataset** : `user/so101-demo`

Sans variables de ports, la GUI prend les deux alias `/dev/serial/by-id/usb-1a86_*` dans l'ordre alphabétique (premier = follower). Vérifiez toujours avec le Diagnostic.

Pour fixer les ports hors NixOS :

```bash
LEROBOT_FOLLOWER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00 \
LEROBOT_LEADER_PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00 \
nix run .
```

Toutes les variables sont listées dans la section Configuration du [README](./README.md).

---

## 🆘 Problèmes Courants

### ❌ "Aucun port serie detecte"
- Vérifiez que les robots sont branchés en USB et alimentés
- `ls -l /dev/serial/by-id/` doit lister deux cartes `usb-1a86_…`
- Essayez de débrancher/rebrancher

### ❌ "Permission denied"
- Sur NixOS : activez `services.lerobot` avec votre utilisateur, puis rouvrez la session
- Hors NixOS : ajoutez-vous au groupe `dialout` et rouvrez la session

### ❌ "Connection failed"
- Vérifiez que le bon port est sélectionné
- Vérifiez que les moteurs sont alimentés
- Fermez tout autre programme qui utilise le port

### ❌ Le leader se tord / le mauvais bras bouge
- Les ports follower et leader sont inversés : fixez `LEROBOT_FOLLOWER_PORT` et `LEROBOT_LEADER_PORT`

### ❌ Le GUI ne démarre pas
- Le port 8080 est peut-être pris : `LEROBOT_GUI_PORT=8081 nix run .`

---

## 📊 Indicateurs de Status

| Couleur | Signification |
|---------|---------------|
| Vert | Opération réussie |
| Rouge | Erreur, ou enregistrement en cours |
| Orange | En cours... |

---

## 🎯 Conseils Pro

1. **Toujours commencer par Diagnostic** pour vérifier la connexion
2. **Fixez les ports by-id** une fois pour toutes (module NixOS ou variables)
3. **Nommez vos datasets clairement** (ex : `user/pick_red_cube`)
4. **Testez avec 1 épisode** avant de faire une longue série
5. **Surveillez les logs** en bas de chaque page pour débugger

---

## 📚 Ressources

- [Documentation LeRobot](https://github.com/huggingface/lerobot)
- [README complet](./README.md)
- [README du flake Nix](../README.md)
- [Issues GitHub LeRobot](https://github.com/huggingface/lerobot/issues)

---

**Bon robotage ! 🤖✨**
