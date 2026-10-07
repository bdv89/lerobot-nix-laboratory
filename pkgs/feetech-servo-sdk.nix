# SDK Python officiel des servomoteurs Feetech STS3215 (ceux du SO-101).
# Absent de nixpkgs : on l'empaquette depuis le sdist PyPI, vérifié par son hash.
{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  pyserial,
}:

buildPythonPackage rec {
  pname = "feetech-servo-sdk";
  version = "1.0.0";
  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-1NODLksbIqgiITOkFNufhoIkwvtjlCahsR2W3f6E5pw=";
  };

  build-system = [ setuptools ];
  dependencies = [ pyserial ];

  pythonImportsCheck = [ "scservo_sdk" ];

  meta = {
    description = "Python SDK for FEETECH serial bus servos";
    homepage = "https://github.com/Adam-Software/FEETECH-Servo-Python-SDK";
    license = lib.licenses.unlicense;
  };
}
