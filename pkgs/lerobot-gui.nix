# GUI NiceGUI : copiée dans le store, lancée par un Python dont l'environnement
# (LeRobot, torch, opencv, nicegui…) est entièrement décrit par Nix.
{
  lib,
  stdenvNoCC,
  makeWrapper,
  python3,
  lerobot,
  ffmpeg,
  v4l-utils,
}:

let
  pythonEnv = python3.withPackages (ps: [
    lerobot
    ps.nicegui
    ps.pandas
    ps.pillow
    ps.psutil
    ps.pyserial
  ]);
in
stdenvNoCC.mkDerivation {
  pname = "lerobot-gui";
  version = "2.2.0";

  src = lib.fileset.toSource {
    root = ../lerobot-gui;
    fileset = lib.fileset.fileFilter (f: f.hasExt "py") ../lerobot-gui;
  };

  nativeBuildInputs = [ makeWrapper ];

  installPhase = ''
    runHook preInstall
    mkdir -p $out/share/lerobot-gui $out/bin
    cp -r . $out/share/lerobot-gui/
    makeWrapper ${pythonEnv}/bin/python $out/bin/lerobot-gui \
      --add-flags $out/share/lerobot-gui/main.py \
      --prefix PATH : ${
        lib.makeBinPath [
          ffmpeg
          v4l-utils
        ]
      }
    runHook postInstall
  '';

  passthru = { inherit pythonEnv; };

  meta = {
    description = "Interface web (NiceGUI) pour piloter un bras LeRobot SO-101";
    license = lib.licenses.asl20;
    mainProgram = "lerobot-gui";
    platforms = lib.platforms.linux;
  };
}
