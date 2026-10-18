# Shelly Plug S Gen3

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: confirmed](https://img.shields.io/badge/state-confirmed-brightgreen.svg?style=flat-square)
![Chip: ESP32-C3](https://img.shields.io/badge/chip-ESP32--C3-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

| Fact | Value |
| --- | --- |
| Profile | `PlugSG3` |
| Flash | 8 MB |
| Official package | 2.1.0 (stable since 2026-10-14; Bootloader, partition table and filesystem are the same as in 2.0.1; the hardware runs were made with 2.0.1) |
| Partition table | `0x10000` |
| App slot size | `0x2a0000` |
| ESPHome device page | [Shelly Plug S Gen3](https://devices.esphome.io/devices/shelly-plug-s-gen3/): pins and a full config |

> [!NOTE]
> **Confirmed:** the whole chain ran on a real device. The package route was confirmed with a minimal config (Wi-Fi, API and OTA
> only): `send` with `--esphome-factory` ran and ESPHome runs. The owner also runs the full ESPHome device-database config (relay,
> metering, LED) on these plugs.

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/PlugSG3-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`.

```yaml
esp32:
  variant: ESP32C3
  board: esp32-c3-devkitm-1
  flash_size: 8MB
  partitions: PlugSG3-stock.csv        # copy from partitions/ in this repository
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

> [!TIP]
> Start from the config on the [ESPHome device page](https://devices.esphome.io/devices/shelly-plug-s-gen3/) (relay, BL0942 metering,
> temperature, LED, button) and replace its `esp32:` block with the one above.

## Pins

| Function | Pin |
| --- | --- |
| Relay | GPIO4 |
| Button (pull-up, inverted) | GPIO18 |
| BL0942 power meter (UART1, 9600 baud) | ESP **RX GPIO6**, ESP **TX GPIO7** |
| Internal temperature (NTC) | GPIO3 |
| LED: addressable, WS2812, 4 pixels | GPIO5 |

Source: the owner's config on the ESPHome device page, which the owner runs on real plugs. The firmware agrees: it sets up UART1 with
RX 6 / TX 7, a button on GPIO18 and an RMT LED on GPIO5 with 4 pixels.

> [!NOTE]
> The device database labels GPIO6 "BL0942 TX" and GPIO7 "BL0942 RX". That is the BL0942's point of view: in ESPHome, `rx_pin` is
> GPIO6 and `tx_pin` is GPIO7.

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch PlugSG3 --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build PlugSG3 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send PlugSG3 out/PlugSG3-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** and watch the log:

   ```
   python ota.py send PlugSG3 out/PlugSG3-app-<date>.zip --ip <device IP> --watch 120
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this package, reads
the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore PlugSG3` first |
| 2 | `Boot: cur ... min ... update? 1` | The installer will write ESPHome's bootloader. `update? 0` means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | `ota_progress` up to 95 %, then `ota_success` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

- The profile sets `boot_min_version: 1.0.9`. The official 2.0.1 package carries the same bootloader as the Plug M Gen3 package (the files are
  byte-identical), which reports Shelly OS loader 1.0.3 once installed. A plug that already runs it (restored from the package, or shipped with it)
  would skip the default 1.0.3, and later ESPHome OTAs would not take effect. The run on a real Plug S Gen3 used the default and the plug had loader 1.0.2;
  the change is not run on a Plug S Gen3 yet. Check the `--watch` log for `Boot: cur ... update? 1`.

## Way back

`python ota.py restore PlugSG3` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
