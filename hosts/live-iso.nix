# Clé USB live : on démarre, l'écran affiche directement la GUI LeRobot.
# Rien à installer, rien à télécharger : tout le système est dans l'image.
{
  lib,
  pkgs,
  modulesPath,
  ...
}:

let
  kiosk = pkgs.writeShellScript "lerobot-kiosk" ''
    # Attendre que la GUI réponde avant d'ouvrir le navigateur plein écran.
    until ${lib.getExe pkgs.curl} -sf http://127.0.0.1:8080 >/dev/null; do sleep 1; done
    exec ${lib.getExe pkgs.firefox} --kiosk http://127.0.0.1:8080
  '';
in
{
  imports = [ "${modulesPath}/installer/cd-dvd/installation-cd-minimal.nix" ];

  isoImage = {
    edition = lib.mkForce "lerobot";
    squashfsCompression = "zstd -Xcompression-level 6";
  };
  image.baseName = lib.mkForce "lerobot-so101-live";

  users.users.lerobot = {
    isNormalUser = true;
  };

  services.lerobot = {
    enable = true;
    user = "lerobot";
    camera.usbId = "05a3:9230"; # à adapter à sa caméra, ou null pour un index OpenCV
    gui.autostart = true;
  };

  # Session graphique minimale : un compositeur Wayland (cage) qui n'affiche qu'une app.
  services.cage = {
    enable = true;
    user = "lerobot";
    program = kiosk;
  };
  systemd.services."cage-tty1".after = [ "lerobot-gui.service" ];

  networking.networkmanager.enable = true; # optionnel : pousser des datasets sur le HF Hub
  networking.wireless.enable = lib.mkForce false;
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  boot.zfs.forceImportRoot = false;
  # Journal aussi sur le port série : diagnostic possible sans écran
  boot.kernelParams = [
    "console=tty0"
    "console=ttyS0,115200"
  ];

  system.stateVersion = "26.05";
}
