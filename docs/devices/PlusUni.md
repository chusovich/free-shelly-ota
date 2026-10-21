# Shelly Plus Uni (Gen2)

[← README](../../README.md) · [All devices](README.md) · [Commands](../commands.md)

![State: partly checked](https://img.shields.io/badge/state-partly%20checked-yellow.svg?style=flat-square)
![Chip: ESP32](https://img.shields.io/badge/chip-ESP32-blue.svg?style=flat-square)

[🧰 Before you start](#before-you-start) · [⚙️ Config](#esphome-config) · [📍 Pins](#pins) · [⚡ Flash it](#flash-it) · [👀 What to expect](#what-to-expect) · [↩️ Way back](#way-back)

A classic ESP32 like the [Plus Plug S](PlusPlugS.md): partition table at the ESP-IDF default `0x8000`, bootloader at `0x1000`, and the ESPHome build needs the 80 MHz flash frequency. Thanks to [yasdfgr](https://github.com/yasdfgr) for the device report (October 2026, [#46](https://github.com/oxynatOr/free-shelly-ota/issues/46)).

| Fact | Value |
| --- | --- |
| Profile | `PlusUni` |
| Model | SNSN-0043X (device id `shellyplusuni-...`) |
| SoC | ESP32-U4WDH (Shelly's knowledge base) |
| Flash | 4 MB (bootloader header and partition table; the knowledge base says 4 MB too) |
| Official package | 2.0.1 |
| Partition table | **`0x8000`** (ESP-IDF default) |
| Bootloader address | `0x1000` |
| App slot size | `0x190000` |
| Bootloader `min_version` | `1.0.9` (set in the profile) |
| Power supply | 8-24 VAC, 9-28 VDC (terminals `VAC1`, `VAC2`) or 5 VDC (terminals `+5 VDC`, `GND`); low voltage, no mains |
| Shelly documentation | [Shelly Plus Uni](https://kb.shelly.cloud/knowledge-base/shelly-plus-uni) (Knowledge Base) |

> [!NOTE]
> **Partly checked:** flashed over OTA on a real Plus Uni (stock 2.0.1, `send` with `--esphome-factory`, October 2026). The tester reports that ESPHome runs and that one later ESPHome OTA took effect; further ones did not (the unit keeps starting the old image). His package had `min_version` 1.0.3 instead of this profile's 1.0.9, so the installer skipped ESPHome's bootloader (`update? 0`, see the notes): that step is not checked on this model. The pins of the inputs and outputs are not known.

## Before you start

- [ ] The device runs Shelly's own firmware, not ESPHome yet.
- [ ] You know its IP address (`--ip`), or this PC is connected to the device's own access point (the default, `192.168.33.1`).
- [ ] This PC can be reached from the device: same network, and nothing blocks port 8000 (`--port`).
- [ ] Your ESPHome config uses the partition table below and is compiled.
- [ ] A UART adapter is at hand as your way back ([Recovery over UART](../recovery-uart.md); the UART header is under [Pins](#pins)).

## ESPHome config

> [!IMPORTANT]
> `build` refuses a config without Shelly's partition table. Copy `partitions/PlusUni-stock.csv` from this repository next to your
> YAML and keep `CONFIG_PARTITION_TABLE_OFFSET: "0x8000"`.

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
    allow_partition_access: true
```

## Pins

**UART header.** [Shelly's knowledge base](https://kb.shelly.cloud/knowledge-base/shelly-plus-uni) shows a 7-pin header at the edge of the board, in the picture under "Addon interface" (Shelly calls it a proprietary serial interface). From the end marked 1:

| Pin | Signal | For flashing over UART |
| --- | --- | --- |
| 1 | `ESP_DBG_UART` | not used (purpose unknown) |
| 2 | `U0TXD` | the Shelly's TX: to the adapter's RX |
| 3 | `U0RXD` | the Shelly's RX: to the adapter's TX |
| 4 | `+3.3_ESP` | 3.3 V of the ESP |
| 5 | `RESET` | to GND for a reset |
| 6 | `GPIO0` | to GND while resetting: download mode |
| 7 | `GND` | ground |

> [!WARNING]
> The order is read from Shelly's drawing, not from a board. Check with a multimeter that pin 7 is connected to the `GND` terminal before you apply 3.3 V. The board has a coating film (the pads may need cleaning), and every other supply (8-24 VAC, 9-28 VDC, 5 VDC) must be disconnected while the adapter is connected. Steps: [Recovery over UART](../recovery-uart.md).

**Inputs and outputs.** The GPIOs are not known. The ESPHome device database has no page for the Plus Uni (checked 2026-10-12); its page for the original
Shelly Uni is Gen1 hardware (ESP8266) and does not apply. Shelly's names for the connections are `ANALOG IN`, `DATA` (1-Wire), `COUNT IN` (pulse counter), `IN1`, `IN2`, `SENSOR VCC` and the two potential-free solid-state relay outputs `OUT1` and `OUT2`.

## Flash it

1. **Install the requirements** (once):

   ```
   pip install -r requirements.txt
   ```

2. **Fetch** the official package:

   ```
   python ota.py fetch PlusUni --insecure
   ```

3. **Build:** put your app into it; the ZIP goes to `out/`:

   ```
   python ota.py build PlusUni app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
   ```

4. **Check the device** first. Nothing is sent:

   ```
   python ota.py send PlusUni out/PlusUni-app-<date>.zip --ip <device IP> --dry-run
   ```

5. **Flash it** (the log goes to a file with `--log-file`):

   ```
   python ota.py send PlusUni out/PlusUni-app-<date>.zip --ip <device IP> --log-file
   ```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

## What to expect

`send` shows these lines at the default log level, in this order:

| # | Log line | Meaning |
| --- | --- | --- |
| 1 | `Update target slot: 0 ...` | The slot check of `send`. Anything else: run `python ota.py restore PlusUni` first |
| 2 | `Device: The bootloader will be replaced ...` (raw log: `Boot: cur ... min ... update? 1`) | The installer will write ESPHome's bootloader. `WARNING: ESPHome's bootloader was NOT written` (`update? 0`) means it will not: build again with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)) |
| 3 | The progress (`Update: ... %`, one line that updates in place) up to 100 %, then `Done: update installed, the device confirmed it` | The device restarts into ESPHome |

> [!NOTE]
> The package wipes NVS: Wi-Fi and settings are gone. ESPHome opens its own access point or joins the Wi-Fi from your config.
> If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

The reported run, from stock 2.0.1 (the first line comes from `send`, the rest from the device):

```
Update target slot: 0 (the slot ESPHome's bootloader starts).
  log| shelly_update.cpp:511   Incoming fw signatures: 00
  log| 2xx_ota_backend.cpp:409 Will write to slot 0
  log| 2xx_ota_backend.cpp:689 Boot: cur 010003ff, new 00000000, min 010003ff, update? 0
  log| shelly_update.cpp:604   FW signatures: want 07 got 00
  log| efuse                   BURN BLOCK3
  log| efuse                   BURN BLOCK3 - OK (all write block bits are set)
  log| efuse                   BURN BLOCK3
  log| efuse                   BURN BLOCK3 - OK (all write block bits are set)
  log| shos_system.c:66        Rebooting in 1000 ms
```

## Notes for this device

**Bootloader `min_version`.** The official package carries Shelly OS loader 1.0.2, but the unit in the report ran **1.0.3** on stock 2.0.1
(`Boot: cur 010003ff`), the first loader seen on a Plus Uni. The profile sets `boot_min_version: 1.0.9`, so the installer writes
ESPHome's bootloader on such a unit. The tester's package had `min 010003ff` (the default, one patch above the official 1.0.2;
this profile was probably not used), which is not higher than the installed loader, hence `update? 0`
([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)). Shelly's loader stayed; ESPHome started anyway, and one later ESPHome OTA took effect. After that, further OTAs were written but
never started: the unit kept running the old image (the tester's follow-up; no UART, so the loader's state could not be read). That is how the
loader works: it switches slots once, during its countdown, and then stays on the slot it committed
([why](../bootloader-and-slots.md#without-esphomes-bootloader-plain-package)). A run with this profile (`update? 1`) is still open.

**eFuse.** After `FW signatures: want 07 got 00` the log shows `BURN BLOCK3 - OK` twice, not the `EFUSE write error` of the H&T and PM Mini.
Whether the eFuse changed on this unit was not checked ([eFuse note](../troubleshooting.md#efuse)).

**The slot.** The Plus Plug S, the other Gen2 device, first received the app in slot 1 and needed `restore` once; `send` checks
the target slot for you ([why](../bootloader-and-slots.md#the-app-must-land-in-slot-0)). Here the target was slot 0 from the start.

**ESPHome warnings.** The ESPHome log of a Plus Uni shows `Chip rev >= 3.0 detected. Set minimum_chip_revision: "3.1" ...` and
`Bootloader supports SRAM1 as IRAM ... Set sram1_as_iram: true ...`. Leave both out of the config you build the package from:
`build` refuses a bootloader whose header differs from Shelly's ([why](../troubleshooting.md#build-refuses-to-replace-the-bootloader)).
Once ESPHome runs they can be added with an ESPHome OTA, which replaces only the app. Read the chip revision of the unit from its boot
log first: an app built for a higher minimum revision than the chip has does not start.

Still open: the GPIOs of the inputs and outputs, the UART header on a real board, and a run with this profile. Please report the file written by `--log-file`, especially the lines `Update target slot`, `Boot: cur ... update?` and `Will write to slot`.

## Way back

`python ota.py restore PlusUni` sends the official firmware back while Shelly firmware still runs.

> [!WARNING]
> Once ESPHome with ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
> ([Recovery over UART](../recovery-uart.md)). Take a flash backup first if you can.

---

> [!TIP]
> **Flashed this device?** Tell us how it went, also when it worked: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).

[Bootloader and slots](../bootloader-and-slots.md) · [Troubleshooting](../troubleshooting.md) · [Recovery over UART](../recovery-uart.md)
