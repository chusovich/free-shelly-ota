# Shelly Pro 3EM (Gen2)

[Back to the README](../../README.md) · [All commands](../commands.md)

Not tested on hardware. A classic ESP32 like the [Plus Plug S](PlusPlugS.md): partition table at the ESP-IDF default `0x8000`, bootloader at `0x1000`, 80 MHz flash frequency. Unlike the other profiles it has **16 MB** flash and a large `emdata` partition.

| | |
| --- | --- |
| Profile | `Pro3EM` |
| Chip | **ESP32** (classic, Gen2), 16 MB flash (bootloader header and partition table) |
| Official package | 2.0.1 (stable channel) |
| Partition table | **`0x8000`** (ESP-IDF default) |
| Bootloader address | `0x1000` |
| App slot size | `0x200000` |
| State | 🧪 builds and verifies; not flashed |

## ESPHome config

```yaml
esp32:
  variant: ESP32
  board: esp32dev
  flash_size: 16MB                       # the bootloader header says 16 MB: with 4MB `build --esphome-factory` refuses
  partitions: Pro3EM-stock.csv           # copy from partitions/ in this repository
  framework:
    type: esp-idf
    sdkconfig_options:
      COMPILER_OPTIMIZATION_SIZE: y
      CONFIG_PARTITION_TABLE_OFFSET: "0x8000"
      CONFIG_ESPTOOLPY_FLASHFREQ_80M: "y"   # without it `build` refuses: the bootloader header says 80 MHz
    advanced:
      enable_ota_rollback: false

ota:
  - platform: esphome
```

## Flash it

```
pip install -r requirements.txt
python ota.py fetch Pro3EM --insecure
python ota.py build Pro3EM app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
python ota.py send Pro3EM out/Pro3EM-app-<date>.zip --ip <device IP> --dry-run
python ota.py send Pro3EM out/Pro3EM-app-<date>.zip --ip <device IP> --watch 120
```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

1. `Update target slot: 0 ...` from `send` (the slot check; if it says anything else, run `python ota.py restore Pro3EM` first).
2. `Boot: cur ... min ... update? 1`: the installer will write ESPHome's bootloader. `update? 0` means it will not: build again
   with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)).
3. `ota_progress` up to 95 %, then `ota_success`. The device restarts into ESPHome.

The package wipes NVS: Wi-Fi and settings are gone, ESPHome opens its own access point or joins the Wi-Fi from your config.
If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

**Pins.** Not known. The ESPHome device database has no page for the Pro 3EM (checked 2026-10-12). Its page for the original
Shelly 3EM (Gen1) warns that the energy meter's calibration data must be saved before flashing ESPHome. Whether the Pro 3EM
keeps such data in flash has not been checked here: take a **full flash backup** first.

**`emdata`.** The stock partition table has an extra data partition `emdata` (`0x510000`, `0xaec000` bytes, about 11 MB) after the
second app slot. It is in `Pro3EM-stock.csv` so ESPHome builds against the real layout; the update package does not touch it.

**Bootloader `min_version`.** The official package carries Shelly OS loader 1.0.2. The profile sets `boot_min_version: 1.0.9`, the
default of the newer profiles, because a unit that Shelly has already updated can report 1.0.3 and would then skip a package with
1.0.3. The loader of a real Pro 3EM has not been seen yet.

**Pro Sensor Addon.** Shelly's update API lists the Pro 3EM with the Pro Sensor Addon as a package of its own, `Pro3EMProAddon`,
and the `Pro3EM` package names it in its `compatible` field. This profile covers only `Pro3EM`. `send` reads that field as one
pattern, so a unit that reports the app `Pro3EMProAddon` would stop at the model check unless you add `--force`.

**The slot.** The Plus Plug S, the other Gen2 device, first received the app in slot 1 and needed `restore` once; `send` checks
the target slot for you ([why](../bootloader-and-slots.md#the-app-must-land-in-slot-0)).

Please report the `--watch` log, especially the lines `Update target slot`, `Boot: cur ... update?` and `Will write to slot`.

## Way back

`python ota.py restore Pro3EM` sends the official firmware back while Shelly firmware still runs. Once ESPHome with
ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
([Recovery over UART](../recovery-uart.md)): take a flash backup first.
