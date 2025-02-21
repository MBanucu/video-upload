# shell.nix
{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs # for npm and vite
    python311 # Python 3.11
    python311Packages.flask # Flask
    python311Packages.flask-cors # Add Flask-CORS
    ffmpeg # Add FFmpeg
  ];

  shellHook = ''
    export FLASK_ENV=development
    code .
  '';
}
