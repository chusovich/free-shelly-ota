{
  description = "Dev shell for free-shelly-ota (Shelly Gen2/3/4 ESP32 OTA flashing tool)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          pyyaml
          bleak
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          name = "free-shelly-ota";

          buildInputs = with pkgs; [
            pythonEnv
            esphome
            esptool
          ];

          shellHook = ''
            echo "=== free-shelly-ota (nix develop) ==="
            echo "Python:   $(python --version 2>&1)"
            echo "esphome:  $(esphome version 2>&1 | head -n1)"
            echo "esptool:  $(esptool.py version 2>&1 | head -n1)"
            echo "Packages: pyyaml, bleak"
            echo ""
            echo "Quick start (repo root):"
            echo "  1. esphome compile my-plug.yaml"
            echo "  2. python ota.py fetch <Profile> --insecure"
            echo "  3. python ota.py build <Profile> app.ota.bin --esphome-factory app.factory.bin --esphome-yaml my-plug.yaml"
            echo "  4. python ota.py send <Profile> out/<zip> --ip <device-ip>"
            echo ""
            echo "BLE Wi-Fi setup (if needed): python ota.py ble wifi <SSID> -"
            echo "======================================="
          '';
        };
      }
    );
}
