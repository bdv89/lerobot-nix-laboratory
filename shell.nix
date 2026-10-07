# Compatibilité `nix-shell` : renvoie vers le devShell du flake (même environnement
# que `nix develop`, figé par flake.lock). L'ancien shell pip/.venv est remplacé.
(builtins.getFlake (toString ./.)).devShells.${builtins.currentSystem}.default
