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
    python311Packages.flask-cors # Flask-CORS
    ffmpeg # FFmpeg
    cpulimit # cpulimit
    vscode # Visual Studio Code
    xdotool # Add xdotool for keystroke simulation
  ];

  shellHook = ''
    export FLASK_ENV=development
    echo "Starting VS Code and triggering build..."
    code . # Launch VS Code in the background
    xdotool search --sync --onlyvisible --class "Code" windowactivate
    sleep 5 # Wait for VS Code to open (adjust as needed)
    xdotool search --sync --onlyvisible --class "Code" windowactivate key ctrl+shift+b
  '';
}
