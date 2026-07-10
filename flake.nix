{
  description = "DeskAgent Reproducible Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      # Define supported systems (Linux and macOS)
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      
      # Helper to generate output attributes for each system
      forEachSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f (import nixpkgs {
        inherit system;
        config.allowUnfree = true; # Allow proprietary software like some model assets
      }));
    in {
      devShells = forEachSystem (pkgs: {
        default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python310
            python310Packages.pip
            python310Packages.virtualenv
            nodejs_18
            nodePackages.npm
            git
            sqlite
          ] ++ (if pkgs.stdenv.isDarwin then [
            # macOS specific packages
            pkgs.darwin.apple_sdk.frameworks.CoreServices
            pkgs.darwin.apple_sdk.frameworks.Cocoa
          ] else [
            # Linux specific packages for Electron support
            pkgs.libuuid
            pkgs.libGL
          ]);

          shellHook = ''
            echo "===================================================="
            echo "   Welcome to DeskAgent Nix Developer Environment!  "
            echo "===================================================="
            echo "Python version: $(python --version)"
            echo "Node version: $(node --version)"
            echo "SQL Server: sqlite3 $(sqlite3 --version | cut -d' ' -f1)"
            echo "===================================================="
          '';
        };
      });
    };
}
