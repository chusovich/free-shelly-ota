# Device pages

[← README](../../README.md) · [Documentation](../README.md) · [Commands](../commands.md) · [Device profiles](../../devices/README.md)

One page per device: the ESPHome config with the partition table that device needs, the pins where they are known, the exact
commands, the log lines to look for and the way back to Shelly OS. Pick your device below, then read
[Commands](../commands.md) for what the options do.

✅ = the whole chain ran on a real device, 🟡 = flashed on a real device, but part of the chain or of the function is not
checked yet, 🧪 = the package builds and verifies, but nobody has flashed it yet.

## Devices

| Device | Profile | Chip | Partition table | App slot size | State |
| --- | --- | --- | --- | --- | --- |
| Plug M Gen3 | [`PlugMG3`](PlugMG3.md) | ESP32-C3 | `0x10000` | `0x2a0000` | ✅ |
| Plug S Gen3 | [`PlugSG3`](PlugSG3.md) | ESP32-C3 | `0x10000` | `0x2a0000` | ✅ |
| Plug PM Gen3 (no relay) | [`PlugPMG3`](PlugPMG3.md) | ESP32-C3 | `0x10000` | `0x280000` | 🟡 flashed over OTA, readings not checked |
| H&T Gen3 | [`HTG3`](HTG3.md) | ESP32-C3 | **`0xf000`** | `0x280000` | ✅ |
| PM Mini Gen3 (no relay) | [`MiniPMG3`](MiniPMG3.md) | ESP32-C3 | **`0xf000`** | `0x280000` | ✅ |
| Multicolor Bulb E27 Gen3 | [`RGBCCTBulbG3`](RGBCCTBulbG3.md) | ESP32-C3 | `0x10000` | `0x280000` | ✅ |
| Duo Bulb Gen3 | [`DuoBulbG3`](DuoBulbG3.md) | ESP32-C3 | `0x10000` | `0x280000` | 🟡 OTA not run; ESPHome config runs (UART) |
| Power Strip 4 Gen4 | [`PowerStrip`](PowerStrip.md) | ESP32-C6 | `0x10000` | `0x300000` | 🟡 boots, outlets not checked |
| Power Strip 4 Gen4 (Zigbee) | [`PowerStripZB`](PowerStripZB.md) | ESP32-C6 | `0x10000` | `0x300000` | 🧪 |
| Plus Plug S (V2 hardware, Gen2) | [`PlusPlugS`](PlusPlugS.md) | **ESP32** | **`0x8000`** | `0x190000` | ✅ without UART |
| The Pill | [`Pill`](Pill.md) | ESP32-C3 | `0x10000` | `0x280000` | 🧪 |
| Mini 1 Gen3 | [`Mini1G3`](Mini1G3.md) | ESP32-C3 | **`0xf000`** | `0x2a0000` | 🧪 |
| Mini 1PM Gen3 | [`Mini1PMG3`](Mini1PMG3.md) | ESP32-C3 | **`0xf000`** | `0x2a0000` | 🧪 |
| Mini 1PM Gen4 | [`Mini1PMG4`](Mini1PMG4.md) | ESP32-C6 | `0x10000` | `0x300000` | 🧪 |
| Mini 1PM Gen4 (Zigbee) | [`Mini1PMG4ZB`](Mini1PMG4.md#zigbee-variant) | ESP32-C6 | `0x10000` | `0x300000` | 🧪 |
| Plus Uni (Gen2) | [`PlusUni`](PlusUni.md) | **ESP32** | **`0x8000`** | `0x190000` | 🟡 flashed over OTA, bootloader step not checked |
| Pro 3EM (Gen2) | [`Pro3EM`](Pro3EM.md) | **ESP32** | **`0x8000`** | `0x200000` | 🧪 |

The partition table offset goes into your ESPHome config as `CONFIG_PARTITION_TABLE_OFFSET`; `build` refuses a config that
does not match the profile. Details per device are on its page.

## Where devices differ

- **Partition table at `0xf000`:** [H&T Gen3](HTG3.md), [PM Mini Gen3](MiniPMG3.md), [Mini 1 Gen3](Mini1G3.md) and [Mini 1PM Gen3](Mini1PMG3.md). A default
  ESPHome build uses ESP-IDF's default `0x8000` and does not match.
- **Classic ESP32 (Gen2):** the [Plus Plug S](PlusPlugS.md), [Plus Uni](PlusUni.md) and [Pro 3EM](Pro3EM.md). Partition table at
  `0x8000`, bootloader at `0x1000`, and the ESPHome build needs the 80 MHz flash frequency. Flash is 4 MB, except on the Pro 3EM
  (16 MB, so `flash_size: 16MB`, and an extra `emdata` partition).
- **Gen4 / ESP32-C6:** [Power Strip](PowerStrip.md), [Power Strip (Zigbee)](PowerStripZB.md) and
  [Mini 1PM Gen4](Mini1PMG4.md) have the largest app slots (`0x300000`).
- **Bootloader `min_version` 1.0.9:** every profile sets it, because a device that runs Shelly's loader 1.0.3 would otherwise skip
  ESPHome's bootloader (the default is one patch above the official loader, 1.0.3; a test checks that no profile lacks it). Background:
  [Bootloader and slots](../bootloader-and-slots.md).
- **Variants:** `PowerStripZB` and `Mini1PMG4ZB` are the Zigbee firmware of the same hardware as `PowerStrip` and `Mini1PMG4`.
  The Power Strip variant has its own page, the Mini variant a section on the Mini 1PM Gen4 page.

## What a page contains

The pages follow the same layout, so you can jump to the part you need:

1. **Header:** badges for the state and the chip, quick links, and a table with profile, flash size, official package version, partition table, app slot size and,
   where one exists, the ESPHome device page; below it a NOTE on what was confirmed or checked (not on untested devices).
2. **Before you start:** a short checklist (stock firmware, IP address, reachability, config, UART adapter).
3. **ESPHome config:** the `esp32:` and `ota:` block to copy, with the partition CSV from `partitions/`.
4. **Pins:** what was read from the stock firmware or taken from a working config (not on every page).
5. **Flash it:** the `fetch`, `build`, `send` commands for this profile as numbered steps, including `--dry-run`.
6. **What to expect:** the log lines of `send --watch`, in order, as a table.
7. **Notes for this device:** things that only apply to this model.
8. **Way back:** how to get Shelly OS back, with `restore` or over UART.

The pages have no photos and no complete configs. Product photos, pin photos and example configs belong on the ESPHome device page that a page links
where one exists, and ready-made configs in [`oxynatOr/esphome-configs`](https://github.com/oxynatOr/esphome-configs).

## Related pages

| Page | What is in it |
| --- | --- |
| [Commands](../commands.md) | `fetch`, `build`, `send`, `restore`, `log` and the rest, with all options |
| [Bootloader and slots](../bootloader-and-slots.md) | Why ESPHome's bootloader is shipped, `min_version`, why the app must land in slot 0 |
| [Troubleshooting](../troubleshooting.md) | Header errors, empty log, battery devices, eFuse, power cycle |
| [Recovery over UART](../recovery-uart.md) | Back to Shelly OS with `esptool` |
| [Credential check](../credential-check.md) | Secrets inside images and packages |

## Your device is not listed

[Request it](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=new-device.yml), or run
`python ota.py add-device <official.zip>` to create a profile from an official package (`--parent <base device>` for a
variant). If you flashed one of the devices above, a report helps, also when it worked:
[open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml).
