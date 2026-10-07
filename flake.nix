{
  description = "LeRobot SO-101 reproductible : environnement, GUI, module NixOS et ISO bootable";

  # Une seule source de vérité : la révision exacte de nixpkgs est figée dans flake.lock.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        overlays = [ self.overlays.default ];
      };
    in
    {
      overlays.default = final: prev: {
        pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
          (pyfinal: pyprev: {
            feetech-servo-sdk = pyfinal.callPackage ./pkgs/feetech-servo-sdk.nix { };
            lerobot = pyfinal.callPackage ./pkgs/lerobot.nix { lerobot = pyprev.lerobot; };
          })
        ];
        lerobot-gui = final.callPackage ./pkgs/lerobot-gui.nix {
          lerobot = final.python3Packages.lerobot;
        };
      };

      packages.${system} = {
        default = pkgs.lerobot-gui;
        lerobot-gui = pkgs.lerobot-gui;
        lerobot = pkgs.python3Packages.lerobot;
        feetech-servo-sdk = pkgs.python3Packages.feetech-servo-sdk;
        iso = self.nixosConfigurations.live.config.system.build.isoImage;
      };

      apps.${system}.default = {
        type = "app";
        program = "${pkgs.lerobot-gui}/bin/lerobot-gui";
        meta.description = "Interface web LeRobot SO-101 sur http://localhost:8080";
      };

      devShells.${system}.default = pkgs.mkShell {
        name = "lerobot";
        packages = [
          pkgs.lerobot-gui.pythonEnv # python + lerobot-* (record, train, rollout…)
          pkgs.ffmpeg
          pkgs.v4l-utils
        ];
        shellHook = ''
          echo "LeRobot $(python -c 'import lerobot; print(lerobot.__version__)') — nixpkgs ${nixpkgs.shortRev or "dirty"}"
          echo "Commandes : lerobot-find-port, lerobot-calibrate, lerobot-teleoperate, lerobot-record, lerobot-train, lerobot-rollout"
        '';
      };

      nixosModules.default = {
        imports = [ ./modules/lerobot.nix ];
        nixpkgs.overlays = [ self.overlays.default ];
      };

      nixosConfigurations.live = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.default
          ./hosts/live-iso.nix
        ];
      };

      checks.${system} = {
        gui = pkgs.lerobot-gui;
        imports = pkgs.runCommand "lerobot-imports" { } ''
          export HOME=$TMPDIR
          ${pkgs.lerobot-gui.pythonEnv}/bin/python -c "
          import lerobot, scservo_sdk, nicegui, cv2
          from lerobot.robots.so_follower import SO101Follower
          from lerobot.teleoperators.so_leader import SO101Leader
          from lerobot.policies.act.modeling_act import ACTPolicy
          print('lerobot', lerobot.__version__)
          "
          touch $out
        '';
        # VM NixOS : module + service + GUI qui répond
        vm = import ./tests/vm.nix {
          inherit pkgs;
          module = self.nixosModules.default;
        };
        # Tests unitaires de la GUI, sans matériel
        gui-tests = pkgs.runCommand "lerobot-gui-tests" { } ''
          export HOME=$TMPDIR
          cp -r ${pkgs.lerobot-gui}/share/lerobot-gui gui && chmod -R u+w gui && cd gui
          ${pkgs.lerobot-gui.pythonEnv}/bin/python -m unittest tests.test_ports -v
          touch $out
        '';
      };

      formatter.${system} = pkgs.nixfmt;
    };
}
