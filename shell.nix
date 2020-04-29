{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    (pkgs.python3.withPackages (ps: [
      (ps.toPythonModule (
        pkgs.dtc.override {
          pythonSupport = true;
          python = pkgs.python3;
        }))
    ]))
  ];
}
