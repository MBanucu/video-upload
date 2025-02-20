# shell.nix
{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs # for npm and vite
    python311 # Python 3.11 for Flask
    python311Packages.flask
  ];

  shellHook = ''
    export FLASK_ENV=development
    code .
  '';
}
