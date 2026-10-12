# Example configs

[Back to the README](../README.md) · [Device pages](../docs/devices/README.md) · [Commands](../docs/commands.md)

Complete ESPHome configs that go with the OTA profiles in [`devices/`](../devices/README.md). They show what this tool needs from
a config (Shelly's stock partition table, its offset, the `ota:` block) together with the pins and components of the device.
The other devices have a config snippet on their [device page](../docs/devices/README.md) instead.

## Configs

| Folder | Device | Profile | State |
| --- | --- | --- | --- |
| [`shelly-power-strip-gen4/`](shelly-power-strip-gen4) | Power Strip 4 Gen4 | [`PowerStrip`](../docs/devices/PowerStrip.md) | The author's own config runs on a real strip. This published version was cleaned up and **not compiled** in this form; outlets, buttons, LEDs and metering are not confirmed here |
| [`shelly-rgbcct-bulb-g3/`](shelly-rgbcct-bulb-g3) | Multicolor Bulb E27 Gen3 | [`RGBCCTBulbG3`](../docs/devices/RGBCCTBulbG3.md) | The OTA ran and ESPHome runs on a real bulb, and the light was tested (owner, 2026-10-11): channel order and fixed warm white. Colour accuracy, the lowest dimming steps and the driver currents are **not measured** |

Each folder has its own `README.md` with the pins, how they were found and what is still open.

## What is in a folder

| File | What it is |
| --- | --- |
| `<name>.yaml` | The ESPHome config |
| `<Profile>-stock.csv` | Shelly's partition table for ESPHome's `partitions:`. A copy of [`partitions/<Profile>-stock.csv`](../partitions), kept next to the config because ESPHome looks for it there |
| `secrets.yaml.example` | Copy it to `secrets.yaml` and fill it in: `wifi_ssid`, `wifi_password`, `ap_password`, `api_key`. `secrets.yaml` is git-ignored |
| `README.md` | Pins with their source, the state of the config, what differs from the author's own |

## Use a config

1. Copy `secrets.yaml.example` to `secrets.yaml` in the folder and fill it in.
2. Compile it with ESPHome. You need two files of the same build: the `.ota.bin` and the `.factory.bin`.
3. From the root of this repository, build the package and send it (example for the Power Strip):

```
python ota.py build PowerStrip app.ota.bin --esphome-factory app.factory.bin --esphome-yaml configs/shelly-power-strip-gen4/shelly-power-strip-gen4.yaml
python ota.py send PowerStrip out/<file>.zip --dry-run
python ota.py send PowerStrip out/<file>.zip --watch 60
```

`--esphome-yaml` makes `build` compare the partition offset and the CSV of the config with the profile, and run the
[credential check](../docs/credential-check.md). The page of the device lists the log lines to look for.

> [!CAUTION]
> A package built from one of these configs contains your Wi-Fi password and API key. Never share or commit it, and keep
> your `secrets.yaml` out of the repository.

## Adding a config

- One folder per device, named after the device, with the four files above.
- Set `partitions:` to the stock CSV and `CONFIG_PARTITION_TABLE_OFFSET` to the `pt_offset` of the profile
  (`0x10000` unless the profile says otherwise). `build --esphome-yaml` refuses a config that does not match.
- Write the CSV with `python ota.py partition-csv <Profile> -o configs/<folder>/<Profile>-stock.csv`.
- Say in the folder's README what was confirmed on a real device and what was not.
