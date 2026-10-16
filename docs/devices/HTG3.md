# Shelly H&T Gen3

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: confirmed](https://img.shields.io/badge/state-confirmed-brightgreen.svg?style=flat-square)
![Chip: ESP32-C3](https://img.shields.io/badge/chip-ESP32--C3-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

A battery device. The partition table is at `0xf000`, so a default ESPHome build does not match and `build` refuses it.

| Fact | Value |
| --- | --- |
| Profile | `HTG3` |
| Flash | 8 MB |
| Official package | 2.0.1 |
| Partition table | **`0xf000`** (not `0x10000`) |
| App slot size | `0x280000` |
| Bootloader `min_version` | `1.0.9` (set in the profile) |
| ESPHome device page | [Shelly H&T Gen3](https://devices.esphome.io/devices/shelly-ht-gen3/): pins and an example config |

> [!NOTE]
> **Confirmed:** the whole chain ran on a real device: `send` from stock 2.0.1 (slot 0) with `--esphome-factory`; ESPHome boots and ESPHome OTAs take effect.

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] The batteries are charged (the stock updater refuses below 30 %) and the device is awake ([Troubleshooting](../troubleshooting.md#battery-devices-ht-gen3)).
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/HTG3-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0xf000"`.

```yaml
esp32:
  variant: ESP32C3
  board: esp32-c3-devkitm-1
  flash_size: 8MB
  partitions: HTG3-stock.csv        # copy from partitions/ in this repository
  framework:
    type: esp-idf
    sdkconfig_options:
      COMPILER_OPTIMIZATION_SIZE: y
      CONFIG_PARTITION_TABLE_OFFSET: "0xf000"
    advanced:
      enable_ota_rollback: false

ota:
  - platform: esphome
```

> [!TIP]
> The [ESPHome device page](https://devices.esphome.io/devices/shelly-ht-gen3/) has the pins and an example config. Replace its `esp32:` block with the one above, or `build` refuses it.

## Pins

| GPIO | Function |
| --- | --- |
| GPIO0 | Button (external pull-up, deep-sleep wake-up) |
| GPIO1 / GPIO3 | I2C SDA / SCL (100 kHz): SHT31 at `0x44`, UC8119 e-paper segment display at `0x50` |
| GPIO2 | Power rail ADC (regulated 3.3 V rail, not the battery) |
| GPIO4 | Battery ADC (voltage divider, enabled with GPIO18) |
| GPIO5 | Battery presence (HIGH when batteries are connected) |
| GPIO6 / GPIO7 | UC8119 BUSY_N / RESET_N |
| GPIO8 | USB detect (HIGH = USB) |
| GPIO10 | UC8119 enable (display power gate) |
| GPIO18 | Battery power enable |

Source: the owner's Shelly H&T Gen3 page in the ESPHome device database, with a full config. The UART pads
on the board are bare test points: pogo pins or test clips work, or solder temporary wires.

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch HTG3 --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build HTG3 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send HTG3 out/HTG3-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** and watch the log:

   ```
   python ota.py send HTG3 out/HTG3-app-<date>.zip --ip <device IP> --watch 120
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

In the `--watch` log look for these lines, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore HTG3` first |
| 2 | `Boot: cur ... min ... update? 1` | The installer will write ESPHome's bootloader. `update? 0` means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | `ota_progress` up to 95 %, then `ota_success` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

## Notes for this device

- **Battery:** the stock updater refuses to start below 30 %: HTTP 500, `OTA not allowed (Battery below 30 percent. )`. Charge
  first and keep the device awake ([Troubleshooting](../troubleshooting.md#battery-devices-ht-gen3)).
- **`min_version`:** this device reports an installed loader 1.0.3, so the default (1.0.3) was skipped; with 1.0.9 the installer
  wrote ESPHome's bootloader ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)).
- **eFuse:** the log shows `FW signatures: want 07 got 00` and refused eFuse writes ("Bits are not empty"). The update still
  succeeded ([eFuse note](../troubleshooting.md#efuse)).

## Way back

`python ota.py restore HTG3` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
