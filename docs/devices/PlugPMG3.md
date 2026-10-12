# Shelly Plug PM Gen3

[Back to the README](../../README.md) · [All commands](../commands.md)

Flashed over OTA with this tool on a real plug (reported by the owner, 2026-10-12); the log lines and the readings are not recorded here yet. This plug **only measures**: Shelly lists the Plug PM Gen3 as a monitoring device, and there is no relay in it. Do not confuse it with the [Plug M Gen3](PlugMG3.md), which switches.

| | |
| --- | --- |
| Profile | `PlugPMG3` |
| Model | S3PL-30116EU |
| Chip | ESP32-C3, 8 MB flash |
| Official package | 2.0.1 |
| Partition table | `0x10000` |
| App slot size | `0x280000` (smaller than the Plug M and Plug S, `0x2a0000`) |
| State | ✅ flashed over OTA (`send` with `--esphome-factory`); readings not checked |

## ESPHome config

```yaml
esp32:
  variant: ESP32C3
  board: esp32-c3-devkitm-1
  flash_size: 8MB
  partitions: PlugPMG3-stock.csv        # copy from partitions/ in this repository
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

Use this device's own `PlugPMG3-stock.csv`. The Plug M and Plug S tables have bigger app slots and different file system offsets, and `build --esphome-yaml` refuses a config whose
slot size does not match the profile.

## Pins

Read from the stock 2.0.1 firmware (a flash dump and the boot log of a real plug). **Not verified against the plug**: nobody has reported readings from a running ESPHome on it yet.

| Function | Pin |
| --- | --- |
| BL0942 power meter (UART1, 9600 8N1) | ESP **RX GPIO6**, ESP **TX GPIO7** |
| Button (polarity assumed: pull-up, inverted) | GPIO18 |
| LED: addressable, 4 pixels (RMT, 20 MHz); chip type and colour order are copied from the Plug S, not read | GPIO5 |
| BL0942 CF/ZX pin (see below) | GPIO10 |
| Relay | none |
| Temperature (NTC) | none found |

- The boot log names the meter (BL0942) and its calibration. The stock firmware sets it up with register `0x19` (MODE) = `0x8F` and `0x14` = `0x33`; ESPHome's `bl0942` does not
  expose these, so the no-load behaviour can differ from stock.
- **GPIO10** is the multiplexed CF/ZX pin of the BL0942. Stock firmware uses it as a falling-edge interrupt input. After a reset the pin carries the energy pulse (CF); it follows the
  zero crossings only if register `OT_FUNX` (`0x18`) is set to 2. The Plug PM image has no zero-cross code and no caller that selects mode 2, so the pin most likely stays on CF.
  This was not measured. ESPHome's `bl0942` does not use the pin.
- No ADC pin was found in the firmware, so there is probably no NTC. Apart from the UART transmit pin and the LED data line, the app configures no output pin.
- The calibration values in the device's `shelly` partition (voltage, current, power, energy scale) are not used by a plain `bl0942` config. Compare the readings with a reference meter and
  adjust.

## Flash it

```
pip install -r requirements.txt
python ota.py fetch PlugPMG3 --insecure
python ota.py build PlugPMG3 app.ota.bin --esphome-factory app.factory.bin --esphome-yaml app.yaml
python ota.py send PlugPMG3 out/PlugPMG3-app-<date>.zip --ip <device IP> --dry-run
python ota.py send PlugPMG3 out/PlugPMG3-app-<date>.zip --ip <device IP> --watch 120
```

`app.ota.bin` and `app.factory.bin` are the two files ESPHome compiles. `--dry-run` only checks the device and, for this
package, reads the update target slot. Command reference: [Commands](../commands.md).

`fetch` needs Shelly's update API to answer with a download URL for `PlugPMG3`. The profile's `update_id` is the app name found in the image; it is assumed, not confirmed, that the update API
uses the same name. If `fetch` fails with "No https 'url' in update API reply", get the official 2.0.1 package another way and give it to `build` with `--official <ZIP>`.

## What to expect

In the `--watch` log look for these lines, in this order:

1. `Update target slot: 0 ...` from `send` (the slot check; if it says anything else, run `python ota.py restore PlugPMG3` first).
2. `Boot: cur ... min ... update? 1`: the installer will write ESPHome's bootloader. `update? 0` means it will not: build again
   with a higher `--boot-min-version` ([why](../bootloader-and-slots.md#is-the-new-bootloader-really-written-min_version)).
3. `ota_progress` up to 95 %, then `ota_success`. The device restarts into ESPHome.

The package wipes NVS: Wi-Fi and settings are gone, ESPHome opens its own access point or joins the Wi-Fi from your config.
If nothing comes up, power-cycle the device ([Troubleshooting](../troubleshooting.md#esphome-does-not-start-after-the-update)).

Please report what you see, also when it works: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml). The lines `Update target slot`,
`Boot: cur ... update?` and `Will write to slot` are the ones that matter, and whether the plug measures voltage, current and power afterwards.

## Notes for this device

- The profile sets `boot_min_version: 1.0.9`. The plug runs Shelly OS loader 1.0.3 (boot log), so the default (one patch above the official loader, 1.0.3) would be skipped by the
  installer, and later ESPHome OTAs would not take effect. Same cause as on the [H&T Gen3](HTG3.md) and the [Plug M Gen3](PlugMG3.md).
- No relay means nothing in the config switches a load. The button can only be a binary sensor.
- Check the app name (`PlugPMG3`) and the model (S3PL-30116EU) before you use this page: the Plug M Gen3 (`PlugMG3`, S3PL-30110EU) looks similar but has a relay and other partition sizes.

## Way back

`python ota.py restore PlugPMG3` sends the official firmware back while Shelly firmware still runs. Once ESPHome with
ESPHome's bootloader is running, `restore` gets no answer and only UART brings Shelly OS back
([Recovery over UART](../recovery-uart.md)): take a flash backup first if you can.

The UART steps on that page were run on a Plus Plug S and a Plug M Gen3. For this plug the parts and addresses come from the official package's manifest and
`partitions/PlugPMG3-stock.csv`; the command below is derived from them and **has not been run on a Plug PM Gen3**. The only difference to the Plug M command is the file system, which sits at
`0x2a0000` here (`0x2c0000` on the Plug M):

```
esptool --chip esp32c3 --port COM4 --baud 460800 erase-region 0x14000 0xc000
esptool --chip esp32c3 --port COM4 --baud 460800 write-flash --flash-mode keep --flash-size keep --flash-freq keep 0x0 bootloader.bin 0x10000 partition-table.bin 0x11000 boot_state.bin 0x20000 PlugPMG3.bin 0x2a0000 fs.img
```

Do not write the `shelly` partition (`0x7f0000`): it holds the model name and the calibration of this plug, and no package contains it. A plug restored this way reports loader 1.0.3
afterwards, which is why the profile sets `boot_min_version: 1.0.9`.
