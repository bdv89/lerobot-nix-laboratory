# Test d'intégration : une VM NixOS active le module, le service démarre et la GUI répond.
{ pkgs, module }:

pkgs.testers.runNixOSTest {
  name = "lerobot-gui";
  # Le module ajoute son overlay à nixpkgs, comme sur une vraie machine
  node.pkgsReadOnly = false;
  nodes.machine = {
    imports = [ module ];
    virtualisation.memorySize = 4096;
    users.users.alice.isNormalUser = true;
    services.lerobot = {
      enable = true;
      user = "alice";
      gui.autostart = true;
    };
  };
  testScript = ''
    machine.wait_for_unit("lerobot-gui.service")
    machine.wait_until_succeeds("curl -sf http://127.0.0.1:8080 | grep -q 'LeRobot SO-101'", timeout=300)
    machine.succeed("id alice | grep -q dialout")
    machine.succeed("test -d /home/alice/lerobot")
  '';
}
