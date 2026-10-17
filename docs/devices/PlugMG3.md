# Shelly Plug M Gen3

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: confirmed](https://img.shields.io/badge/state-confirmed-brightgreen.svg?style=flat-square)
![Chip: ESP32-C3](https://img.shields.io/badge/chip-ESP32--C3-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

The first device this tool was confirmed on.

| Fact | Value |
| --- | --- |
| Profile | `PlugMG3` |
| Flash | 8 MB |
| Official package | 2.1.0 (stable since 2026-10-14; Bootloader, partition table and filesystem are the same as in 2.0.1; the hardware runs were made with 2.0.1) |
| Partition table | `0x10000` |
| App slot size | `0x2a0000` |

> [!NOTE]
> **Confirmed:** the whole chain ran on a real device: `send` from stock 1.8.99 (running from slot 1), then two ESPHome OTAs.

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/PlugMG3-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`.

```yaml
esp32:
  variant: ESP32C3
  board: esp32-c3-devkitm-1
  flash_size: 8MB
  partitions: PlugMG3-stock.csv        # copy from partitions/ in this repository
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

Pins read from the stock firmware and tested on a real plug:

| Function | Pin |
| --- | --- |
| Relay | GPIO0 |
| Button | GPIO7 |
| BL0942 power meter (UART, 9600 8N1) | TX GPIO4, RX GPIO5 |
| BL0942 CF/ZX pin (multiplexed: CF by default, zero-cross after a register write the stock firmware does) | GPIO3 |
| RGB LED (common anode, **active low**: `inverted: true` on every output) | red GPIO18, green GPIO10, blue GPIO19 |
| NTC (beta 3950, 10 k at 25 C) | probably GPIO1 (ADC1_CH1), the reading looks right |

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch PlugMG3 --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build PlugMG3 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send PlugMG3 out/PlugMG3-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** and watch the log:

   ```
   python ota.py send PlugMG3 out/PlugMG3-app-<date>.zip --ip <device IP> --watch 120
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore PlugMG3` first. On stock 1.8.99 you get a warning instead ([why](#notes-for-this-device)) |
| 2 | `Boot: cur ... min ... update? 1` | The installer will write ESPHome's bootloader. `update? 0` means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | `ota_progress` up to 95 %, then `ota_success` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

- On stock 1.8.99 the slot check of `send` cannot run: the device logs `Storing core dumps to scratch (0x720000)` instead of `app_N`,
  so `send` warns that the firmware does not reveal the update target slot and goes on. The installer wrote to the slot the stock
  firmware was not running from (device on slot 1, `Will write to slot 0`); look for that line with `--watch`.
- On this model ESPHome came up after a power-off of about 30 seconds; whether it would also have started without it was not tested.
- Without `--esphome-factory` ESPHome still boots, but later ESPHome OTAs only take effect after Shelly's attempt counter runs out
  ([details](../bootloader-and-slots.md#without-esphomes-bootloader-plain-package)).

## Way back

`python ota.py restore PlugMG3` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

Done once on a real plug: Shelly OS 2.0.1 with
loader 1.0.3 came back. Pushing the official app image through ESPHome OTA instead does not work (same page).

A Plug M restored this way has loader 1.0.3, which is why the profile sets `boot_min_version: 1.0.9`: a later `send` with
`--esphome-factory` still replaces the bootloader. Because Shelly then runs from slot 0, run `python ota.py restore PlugMG3`
first, otherwise `send` refuses (the installer would write to slot 1).

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
