# Corrections du bouton "Démarrer" - LeRobot GUI

> **Note historique** : notes de correction d'octobre 2025 (Windows, ports COM, LeRobot 0.4). Le code et les commandes cités ont évolué depuis : voir le [README](./README.md) et le [CHANGELOG](./CHANGELOG.md).

## Problème identifié

Le bouton "▶️ Démarrer l'enregistrement" dans l'onglet "📹 Enregistrer" ne répondait pas lorsqu'on cliquait dessus.

### Cause racine

1. **Blocage de l'interface utilisateur** : La fonction `start_recording()` utilisait une boucle `while current_process.poll() is None` qui bloquait l'interface NiceGUI, empêchant toute interaction pendant l'attente.

2. **Pas de feedback visuel** : Aucun message ou log n'était affiché pendant le démarrage du processus, donnant l'impression que rien ne se passait.

3. **Pas de capture des sorties** : Les messages du subprocess `lerobot_record` (stdout/stderr) n'étaient pas capturés ni affichés, rendant le débogage impossible.

## Solutions implémentées

### 1. Monitoring asynchrone non-bloquant

**Avant :**
```python
# Monitor the process
while current_process.poll() is None:
    await asyncio.sleep(0.5)
```

**Après :**
```python
# Create async task to read process output
async def read_output():
    loop = asyncio.get_event_loop()

    while current_process.poll() is None:
        # Read stdout in non-blocking way
        if current_process.stdout:
            try:
                line = await loop.run_in_executor(None, current_process.stdout.readline)
                if line:
                    output_log.push(line.strip())
            except:
                pass

        # Read stderr in non-blocking way
        if current_process.stderr:
            try:
                line = await loop.run_in_executor(None, current_process.stderr.readline)
                if line:
                    output_log.push(f'⚠️ {line.strip()}')
            except:
                pass

        await asyncio.sleep(0.1)

    # Process finished - check return code
    return_code = current_process.returncode
    if return_code == 0:
        status_label.text = '✅ Enregistrement terminé'
        status_label.style('color: green')
    else:
        status_label.text = f'❌ Processus terminé avec erreur (code {return_code})'
        status_label.style('color: red')

# Start monitoring in background
asyncio.create_task(read_output())
```

### 2. Feedback immédiat au démarrage

Ajout de messages de confirmation dès le lancement :
```python
output_log.push('🚀 Démarrage de l\'enregistrement...')
# ... lancement du processus ...
output_log.push('✅ Processus lancé!')
output_log.push(f'📊 Configuration: {robot_type.value} sur {robot_port.value}')
output_log.push(f'📦 Dataset: {dataset_name.value}')
output_log.push(f'🎯 Tâche: {task_name.value}')
output_log.push('---')
```

### 3. Gestion des codes de retour

Le processus affiche maintenant clairement si l'enregistrement s'est terminé avec succès (code 0) ou avec une erreur (code non-zéro).

## Fichiers modifiés

- **`main.py`** (lignes 120-199) : Fonction `start_recording()` améliorée
- **`main.py`** (lignes 389-451) : Fonction `start_replay()` améliorée avec les mêmes corrections

## Comment tester

### Test 1 : Vérifier que l'interface ne se bloque plus

1. Lancez l'interface GUI :
   ```bash
   cd lerobot-gui
   python main.py
   ```

2. Allez dans l'onglet "📹 Enregistrer"

3. Cliquez sur "⚡ Charger config SO101" pour charger la configuration par défaut

4. Cliquez sur "▶️ Démarrer l'enregistrement"

5. **Vérification** :
   - Vous devriez voir immédiatement des messages dans le log
   - L'interface doit rester réactive (vous pouvez cliquer sur d'autres onglets)
   - Les sorties du processus `lerobot_record` doivent s'afficher en temps réel

### Test 2 : Vérifier la capture des erreurs

1. Modifiez le port robot pour utiliser un port invalide (ex: "COM99")

2. Cliquez sur "▶️ Démarrer l'enregistrement"

3. **Vérification** :
   - Les messages d'erreur du subprocess doivent apparaître dans le log
   - Le statut doit indiquer l'erreur clairement
   - L'interface reste utilisable

### Test 3 : Vérifier l'arrêt manuel

1. Démarrez un enregistrement avec une configuration valide

2. Attendez quelques secondes

3. Cliquez sur "⏹️ Arrêter"

4. **Vérification** :
   - Le processus doit s'arrêter immédiatement
   - Le statut doit changer pour "⏹️ Enregistrement arrêté"

## Améliorations futures possibles

1. **Barre de progression** : Afficher une barre de progression pour les épisodes multiples

2. **Statistiques en temps réel** : Afficher le nombre de frames capturées, FPS, etc.

3. **Notifications sonores** : Jouer un son quand l'enregistrement se termine

4. **Logs persistants** : Sauvegarder les logs dans un fichier pour consultation ultérieure

5. **Timeout automatique** : Arrêter automatiquement si le processus ne démarre pas dans les 10 secondes

## Notes techniques

### Pourquoi `asyncio.create_task()` ?

La fonction `asyncio.create_task()` permet de lancer une tâche asynchrone en arrière-plan sans bloquer l'exécution de la fonction principale. Cela permet à `start_recording()` de retourner immédiatement après avoir lancé le subprocess, gardant l'interface réactive.

### Pourquoi `run_in_executor()` ?

Les opérations de lecture sur `stdout` et `stderr` sont bloquantes. `run_in_executor()` les exécute dans un thread séparé, les rendant non-bloquantes pour l'event loop asyncio.

### Gestion des erreurs silencieuse

Les `except: pass` dans les blocs de lecture sont intentionnels - ils évitent que des erreurs de lecture (ex: pipe fermé) ne crashent le monitoring. Le processus de monitoring s'arrête naturellement quand `poll()` retourne un code de sortie.

## Support

Si vous rencontrez encore des problèmes :

1. Vérifiez les logs dans le terminal où vous avez lancé `python main.py`
2. Assurez-vous que les deux robots sont bien connectés (utilisez l'onglet "🔧 Diagnostic")
3. Vérifiez que les ports COM sont corrects
4. Testez d'abord la commande manuellement : `python -m lerobot.scripts.lerobot_record --help`
