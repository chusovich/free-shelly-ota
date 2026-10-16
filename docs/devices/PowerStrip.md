# Shelly Power Strip 4 Gen4

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: partly checked](https://img.shields.io/badge/state-partly%20checked-yellow.svg?style=flat-square)
![Chip: ESP32-C6](https://img.shields.io/badge/chip-ESP32--C6-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

Gen4 / ESP32-C6. A full example config with all pins is in [`configs/shelly-power-strip-gen4/`](../../configs/shelly-power-strip-gen4).

| Fact | Value |
| --- | --- |
| Profile | `PowerStrip` |
| Flash | 8 MB |
| Official package | 2.0.1 |
| Partition table | `0x10000` |
| App slot size | `0x300000` |
| Bootloader `min_version` | `1.0.9` (set in the profile) |
| ESPHome device page | [Shelly Power Strip 4 Gen4](https://devices.esphome.io/devices/shelly-power-strip-4-gen4/): pins and an example config |

> [!NOTE]
> **Partly checked:** ESPHome boots and joins Wi-Fi/Home Assistant (UART log). Outlets and metering not checked here.

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] The strip runs Shelly firmware 2.0.1: from stock 1.7.99 a direct `send` did not work, so update once with Shelly first or run `python ota.py restore PowerStrip` (see Notes).
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/PowerStrip-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`.

```yaml
esp32:
  variant: ESP32C6
  board: esp32-c6-devkitc-1
  flash_size: 8MB
  partitions: PowerStrip-stock.csv        # copy from partitions/ in this repository
  framework:
    type: esp-idf
    sdkconfig_options:
      COMPILER_OPTIMIZATION_SIZE: y
      CONFIG_PARTITION_TABLE_OFFSET: "0x10000"
    advanced:
      enable_ota_rollback: false

ota:
  - platform: esphome
```

Add this under `esphome:` (the C6 needs the 80 MHz flash header, otherwise `build` refuses):

```yaml
esphome:
  platformio_options:
    board_build.flash_mode: dio
    board_build.f_flash: 80000000L
    board_build.flash_size: 8MB
```

> [!TIP]
> The [ESPHome device page](https://devices.esphome.io/devices/shelly-power-strip-4-gen4/) has the pins and an example config. Replace its `esp32:` block with the one above, or `build` refuses it.

## Pins

| Function | Pin | Source |
| --- | --- | --- |
| SPI MISO / MOSI / SCLK | GPIO12 / GPIO11 / GPIO13 | stock boot log (`SPI2 init ok`) |
| ADE7953 chip select (outlets 1+2 / 3+4) | GPIO15 / GPIO10 | stock boot log (`CS0/1/2: 15/10/-1`) |
| ADE7953 IRQ (chip 0 / chip 1) | GPIO6 / GPIO7 | in use on the owner's device |
| Relays 1 to 4 | GPIO4 / GPIO2 / GPIO3 / GPIO1 | in use on the owner's device |
| Buttons 1 to 4 (pull-up, inverted) | GPIO20 / GPIO22 / GPIO23 / GPIO21 | in use on the owner's device |
| LED ring (WS2812, 12 LEDs, 3 per outlet) | GPIO18 | in use on the owner's device |

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch PowerStrip --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build PowerStrip app.ota.bin --esphome-factory app.factory.bin --esphome-yaml shelly-power-strip-gen4.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send PowerStrip out/PowerStrip-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** and watch the log:

   ```
   python ota.py send PowerStrip out/PowerStrip-app-<date>.zip --ip <device IP> --watch 120
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore PowerStrip` first |
| 2 | `Boot: cur ... min ... update? 1` | The installer will write ESPHome's bootloader. `update? 0` means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | `ota_progress` up to 95 %, then `ota_success` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

- **Stock 1.7.99:** a direct `send` did not work: the installer wrote to slot 1 and the old app in `app_0` started again,
  although the update reported success. `send` now reads the target slot first and refuses; after one official update to
  2.0.1 (or `ota.py restore PowerStrip`) a new `send` targeted slot 0 and ESPHome started
  ([slot rule](../bootloader-and-slots.md#the-app-must-land-in-slot-0)). The 1.7.99 installer also left the old partition
  table (no `scratch`); after 2.0.1 it was the new one.
- **`min_version`:** with `1.0.9` the installer wrote ESPHome's bootloader (hardware-confirmed).
- **After a good install** the UART log shows `ESP-IDF ... 2nd stage bootloader`, `ota data partition invalid and no factory,
  will try all partitions` (expected) and `Loaded app from partition at offset 0x20000`.
- **OTA encryption:** the owner's build requires it (`Encryption: required`); the example config has no `encryption:` entry.

## Way back

`python ota.py restore PowerStrip` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
