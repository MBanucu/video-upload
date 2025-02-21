# shell.nix
{
  pkgs ?
    import <nixpkgs> {
      config = {
        allowUnfree = true;
      };
    },
}:
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs # for npm and vite
    python311 # Python 3.11
    python311Packages.flask # Flask
    python311Packages.flask-cors # Add Flask-CORS
    ffmpeg # Add FFmpeg
    cpulimit # Add cpulimit
    vscode # Add Visual Studio Code
  ];

  shellHook = ''
    export FLASK_ENV=development
    code .
    echo "press ctrl+shift+B in VSCode to build and run the project"
  '';
}
