# Shelly Plus Uni (Gen2)

[Back to the README](../../README.md) · [All commands](../commands.md)

Not tested on hardware. A classic ESP32 like the [Plus Plug S](PlusPlugS.md): partition table at the ESP-IDF default `0x8000`, bootloader at `0x1000`, and the ESPHome build needs the 80 MHz flash frequency.

| | |
| --- | --- |
| Profile | `PlusUni` |
| Chip | **ESP32** (classic, Gen2), 4 MB flash (bootloader header and partition table) |
| Official package | 2.0.1 |
| Partition table | **`0x8000`** (ESP-IDF default) |
| Bootloader address | `0x1000` |
| App slot size | `0x190000` |
| State | 🧪 builds and verifies; not flashed |

## ESPHome config

```yaml
esp32:
  variant: ESP32
  board: esp32dev
  flash_size: 4MB
  partitions: PlusUni-stock.csv        # copy from partitions/ in this repository
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
python ota.py fetch PlusUni --insecure
python ota.py build PlusUni app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
python ota.py send PlusUni out/PlusUni-app-<date>.zip --ip <device IP> --dry-run
python ota.py send PlusUni out/PlusUni-app-<date>.zip --ip <device IP> --watch 120
```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

1. `Update target slot: 0 ...` from `send` (the slot check; if it says anything else, run `python ota.py restore PlusUni` first).
2. `Boot: cur ... min ... update? 1`: the installer will write ESPHome's bootloader. `update? 0` means it will not: build again
   with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)).
3. `ota_progress` up to 95 %, then `ota_success`. The device restarts into ESPHome.

The package wipes NVS: Wi-Fi and settings are gone, ESPHome opens its own access point or joins the Wi-Fi from your config.
If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

**Pins.** Not known. The ESPHome device database has no page for the Plus Uni (checked 2026-10-12); its page for the original
Shelly Uni is Gen1 hardware (ESP8266) and does not apply.

**Bootloader `min_version`.** The official package carries Shelly OS loader 1.0.2. The profile sets `boot_min_version: 1.0.9`, the
default of the newer profiles, because a unit that Shelly has already updated can report 1.0.3 and would then skip a package with
1.0.3. The loader of a real Plus Uni has not been seen yet.

**The slot.** The Plus Plug S, the other Gen2 device, first received the app in slot 1 and needed `restore` once; `send` checks
the target slot for you ([why](../bootloader-and-slots.md#the-app-must-land-in-slot-0)).

Please report the `--watch` log, especially the lines `Update target slot`, `Boot: cur ... update?` and `Will write to slot`.

## Way back

`python ota.py restore PlusUni` sends the official firmware back while Shelly firmware still runs. Once ESPHome with
ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
([Recovery over UART](../recovery-uart.md)): take a flash backup first if you can.
