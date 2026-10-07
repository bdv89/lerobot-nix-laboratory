# LeRobot tel que packagé dans nixpkgs (binaire en cache sur cache.nixos.org),
# complété des extras nécessaires au SO-101 : feetech + hardware + dataset + training.
{
  lerobot,
  feetech-servo-sdk,
  pyserial,
  deepdiff,
  pynput,
  datasets,
  pandas,
  pyarrow,
  av,
  jsonlines,
  accelerate,
  rerun-sdk,
}:

lerobot.overridePythonAttrs (old: {
  patches = (old.patches or [ ]) ++ [
    # Contrôle de l'enregistrement par fichier (next/redo/stop) : permet à la GUI
    # de valider un épisode sans clavier ni TTY. Patch local, versionné ici.
    ./lerobot-control-file.patch
  ];

  dependencies = (old.dependencies or [ ]) ++ [
    # [feetech] / [hardware]
    feetech-servo-sdk
    pyserial
    deepdiff
    pynput
    # [dataset]
    datasets
    pandas
    pyarrow
    av
    jsonlines
    # [training]
    accelerate
    # [viz] : --display_data, lerobot-dataset-viz
    rerun-sdk
  ];
  # Les tests amont exigent réseau + matériel ; ils tournent déjà dans nixpkgs.
  doCheck = false;
})
