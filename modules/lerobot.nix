# Module NixOS : tout ce qu'il faut au système pour un bras SO-101,
# déclaré une fois (udev, groupes, service) au lieu d'être bricolé à la main.
{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.lerobot;
  usbId = lib.types.strMatching "[0-9a-f]{4}:[0-9a-f]{4}";
  vendor = id: lib.head (lib.splitString ":" id);
  product = id: lib.last (lib.splitString ":" id);
in
{
  options.services.lerobot = {
    enable = lib.mkEnableOption "LeRobot SO-101 (udev, permissions, GUI)";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.lerobot-gui;
      defaultText = lib.literalExpression "pkgs.lerobot-gui";
      description = "Paquet de la GUI LeRobot.";
    };

    user = lib.mkOption {
      type = lib.types.str;
      example = "alice";
      description = "Utilisateur qui pilote le robot (ajouté à dialout et video).";
    };

    followerPort = lib.mkOption {
      type = lib.types.str;
      default = "";
      example = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_XXXXXXXXXX-if00";
      description = ''
        Port série du bras follower. Préférer l'alias /dev/serial/by-id (numéro de série du CH340,
        stable) à /dev/ttyACM* qui change d'ordre au rebranchement. Vide : auto-détection.
      '';
    };

    leaderPort = lib.mkOption {
      type = lib.types.str;
      default = "";
      example = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_YYYYYYYYYY-if00";
      description = "Port série du bras leader (voir followerPort).";
    };

    armUsbId = lib.mkOption {
      type = usbId;
      default = "1a86:55d3";
      description = "vendor:product USB des cartes contrôleur des bras (CH340 de la carte Waveshare/Feetech).";
    };

    camera = {
      usbId = lib.mkOption {
        type = lib.types.nullOr usbId;
        default = null;
        example = "05a3:9230";
        description = "Caméra USB à exposer en /dev/lerobot_cam (null : utiliser un index OpenCV).";
      };
      device = lib.mkOption {
        type = lib.types.str;
        default = if cfg.camera.usbId != null then "/dev/lerobot_cam" else "0";
        defaultText = lib.literalExpression ''"/dev/lerobot_cam" si camera.usbId, sinon "0"'';
        description = "Caméra proposée par défaut dans la GUI (chemin ou index OpenCV).";
      };
    };

    gui = {
      autostart = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Lancer la GUI au démarrage (service systemd de l'utilisateur).";
      };
      port = lib.mkOption {
        type = lib.types.port;
        default = 8080;
        description = "Port HTTP de la GUI.";
      };
      openFirewall = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Rendre la GUI accessible depuis le réseau local (écoute sur 0.0.0.0).";
      };
      workdir = lib.mkOption {
        type = lib.types.str;
        default = "/home/${cfg.user}/lerobot";
        defaultText = lib.literalExpression ''"/home/''${user}/lerobot"'';
        description = "Dossier des entraînements (outputs/) et checkpoints (trained/).";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];

    users.users.${cfg.user}.extraGroups = [
      "dialout"
      "video"
    ];

    # Accès aux bras + autosuspend USB désactivé (sinon le bus Feetech décroche en pleine trajectoire).
    services.udev.extraRules = ''
      SUBSYSTEM=="tty", ATTRS{idVendor}=="${vendor cfg.armUsbId}", ATTRS{idProduct}=="${product cfg.armUsbId}", MODE="0660", GROUP="dialout"
      ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="${vendor cfg.armUsbId}", ATTR{idProduct}=="${product cfg.armUsbId}", ATTR{power/control}="on"
    ''
    + lib.optionalString (cfg.camera.usbId != null) ''
      ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="${vendor cfg.camera.usbId}", ATTR{idProduct}=="${product cfg.camera.usbId}", ATTR{power/control}="on"
      SUBSYSTEM=="video4linux", ATTRS{idVendor}=="${vendor cfg.camera.usbId}", ATTRS{idProduct}=="${product cfg.camera.usbId}", ATTR{index}=="0", SYMLINK+="lerobot_cam", GROUP="video"
    '';

    environment.sessionVariables = {
      LEROBOT_FOLLOWER_PORT = cfg.followerPort;
      LEROBOT_LEADER_PORT = cfg.leaderPort;
      LEROBOT_CAMERA = cfg.camera.device;
      LEROBOT_GUI_PORT = toString cfg.gui.port;
      LEROBOT_WORKDIR = cfg.gui.workdir;
    };

    networking.firewall.allowedTCPPorts = lib.mkIf cfg.gui.openFirewall [ cfg.gui.port ];

    systemd.services.lerobot-gui = lib.mkIf cfg.gui.autostart {
      description = "LeRobot SO-101 GUI";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];
      environment = {
        LEROBOT_FOLLOWER_PORT = cfg.followerPort;
        LEROBOT_LEADER_PORT = cfg.leaderPort;
        LEROBOT_CAMERA = cfg.camera.device;
        LEROBOT_GUI_PORT = toString cfg.gui.port;
        LEROBOT_GUI_HOST = if cfg.gui.openFirewall then "0.0.0.0" else "127.0.0.1";
        LEROBOT_GUI_SHOW = "0";
        LEROBOT_WORKDIR = cfg.gui.workdir;
      };
      serviceConfig = {
        ExecStart = lib.getExe cfg.package;
        User = cfg.user;
        WorkingDirectory = "~";
        SupplementaryGroups = [
          "dialout"
          "video"
        ];
        Restart = "on-failure";
        RestartSec = 3;
      };
    };
  };
}
