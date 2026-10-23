# Shelly Mini 1PM Gen4

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: DevKit-tested](https://img.shields.io/badge/state-devkit%20tested-blueviolet.svg?style=flat-square)
![Chip: ESP32-C6](https://img.shields.io/badge/chip-ESP32--C6-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

Gen4 / ESP32-C6.

| Fact | Value |
| --- | --- |
| Profile | `Mini1PMG4`, `Mini1PMG4ZB` |
| Flash | 8 MB |
| Official package | 2.1.0 (stable since 2026-10-14, also for the Zigbee variant; Bootloader, partition table and filesystem are the same as in 2.0.1) |
| Partition table | `0x10000` |
| App slot size | `0x300000` |
| Bootloader `min_version` | `1.0.9` (set in the profile) |

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/Mini1PMG4-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`.

```yaml
esp32:
  variant: ESP32C6
  board: esp32-c6-devkitc-1
  flash_size: 8MB
  partitions: Mini1PMG4-stock.csv        # copy from partitions/ in this repository
  framework:
    type: esp-idf
    sdkconfig_options:
      COMPILER_OPTIMIZATION_SIZE: y
      CONFIG_PARTITION_TABLE_OFFSET: "0x10000"
    advanced:
      enable_ota_rollback: false

ota:
  - platform: esphome
    allow_partition_access: true
```

The C6 needs the 80 MHz flash header, otherwise `build` refuses to replace the bootloader. If it complains, add under `esphome:`:

```yaml
esphome:
  platformio_options:
    board_build.flash_mode: dio
    board_build.f_flash: 80000000L
    board_build.flash_size: 8MB
```

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch Mini1PMG4 --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build Mini1PMG4 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send Mini1PMG4 out/Mini1PMG4-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** (the log goes to a file with `--log-file`):

   ```
   python ota.py send Mini1PMG4 out/Mini1PMG4-app-<date>.zip --ip <device IP> --log-file
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

`send` shows these lines at the default log level, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore Mini1PMG4` first |
| 2 | `Device: The bootloader will be replaced ...` (raw log: `Boot: cur ... min ... update? 1`) | The installer will write ESPHome's bootloader. `WARNING: ESPHome's bootloader was NOT written` (`update? 0`) means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | The progress (`Update: ... %`, one line that updates in place) up to 100 %, then `Done: update installed, the device confirmed it` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

Played through on a dev board with the DevKit image on 2026-10-23 (see [Seen on a board](../devkit.md#seen-on-a-board)); not on the real device yet. Please report the `--watch` log of a real device, especially the lines `Update target slot`, `Boot: cur ... update?` and `Will write to slot`.

## Zigbee variant

`Mini1PMG4ZB` is the Zigbee firmware variant of the same hardware (listed under `alt` in the update reply of `Mini1PMG4`; its profile has `parent: Mini1PMG4`). Use the same config and flash it with `python ota.py send Mini1PMG4ZB ...` after building with `build Mini1PMG4ZB`. Played through on a dev board as well (2026-10-23, see [Seen on a board](../devkit.md#seen-on-a-board)); not on the real device.

## Way back

`python ota.py restore Mini1PMG4` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
