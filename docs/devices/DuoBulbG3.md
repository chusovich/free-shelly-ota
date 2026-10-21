# Shelly Duo Bulb Gen3

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: partly checked](https://img.shields.io/badge/state-partly%20checked-yellow.svg?style=flat-square)
![Chip: ESP32-C3](https://img.shields.io/badge/chip-ESP32--C3-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

The owner reports the same main board as the Multicolor Bulb with a different lamp module. The Duo's stock firmware has no I2C code: it drives the LEDs with PWM (LEDC), so the LED driver config of the [Multicolor Bulb](RGBCCTBulbG3.md) does not apply. The pins are known (below) from the owner's UART-flashed config.

| Fact | Value |
| --- | --- |
| Profile | `DuoBulbG3` |
| Flash | 8 MB |
| Official package | 2.0.1 |
| Partition table | `0x10000` |
| App slot size | `0x280000` |

> [!NOTE]
> **Partly checked:** the OTA package builds and verifies, but this tool has not flashed it. The ESPHome config itself runs on the owner's bulb (flashed over UART).

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back; the bulb has a non-isolated mains supply, see the warning below ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/DuoBulbG3-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`.

```yaml
esp32:
  variant: ESP32C3
  board: esp32-c3-devkitm-1
  flash_size: 8MB
  partitions: DuoBulbG3-stock.csv        # copy from partitions/ in this repository
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

## Pins

| Function | Pin |
| --- | --- |
| Warm white (LEDC PWM) | GPIO4 (module pad `MTMS`) |
| Cold white (LEDC PWM) | GPIO5 (module pad `MTDI`) |
| BOOT (download mode, low-active) | GPIO9 |

Source: the owner's Shelly Duo Bulb E27 Gen3 page, prepared for the ESPHome device database (not published there yet), flashed over UART, with a
`cwww` light and `constant_brightness: true`. The pins also match the stock firmware (two LEDC channels, warm on GPIO4, cold on GPIO5). No energy meter
chip is known.

> [!WARNING]
> The bulb has a **non-isolated mains supply**. Never connect a serial adapter while it is in the socket; take it out and power it from the adapter's 3.3 V.

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch DuoBulbG3 --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build DuoBulbG3 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send DuoBulbG3 out/DuoBulbG3-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** (the log goes to a file with `--log-file`):

   ```
   python ota.py send DuoBulbG3 out/DuoBulbG3-app-<date>.zip --ip <device IP> --log-file
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

`send` shows these lines at the default log level, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore DuoBulbG3` first |
| 2 | `Device: The bootloader will be replaced ...` (raw log: `Boot: cur ... min ... update? 1`) | The installer will write ESPHome's bootloader. `WARNING: ESPHome's bootloader was NOT written` (`update? 0`) means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | The progress (`Update: ... %`, one line that updates in place) up to 100 %, then `Done: update installed, the device confirmed it` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

The OTA chain should work the same way as on the Multicolor Bulb, but it has not been run. The profile sets `boot_min_version: 1.0.9` because the Multicolor Bulb
(same main board) runs loader 1.0.3 after a return to stock, which the default 1.0.3 would skip. Please report the file written by `--log-file`, especially the line `Boot: cur ... min ... update?`.

## Way back

`python ota.py restore DuoBulbG3` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
