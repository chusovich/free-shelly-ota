# Test the update on a dev board

[← README](../README.md) · [Documentation](README.md) · [Commands](commands.md#devkit) · [Recovery over UART](recovery-uart.md)

[🎯 Why](#why) · [🧰 Which board](#which-board) · [🪜 Steps](#steps) · [👀 What to look for](#what-to-look-for) · [🔁 Variations](#variations-to-play-through) · [⚠️ Limits](#limits-and-risks)

`ota.py devkit` turns a package into a flash image for a dev board. The board then boots Shelly's own loader and firmware, and `send`, the
installer, the bootloader swap and the slot logic run against it as against a device. Resetting the board takes one `esptool` call, so the same
update can be played through again and again, for every profile, also for devices you do not own.

> [!IMPORTANT]
> **Not run on a board yet.** The images are built from the packages and a test checks every profile, but nobody has flashed one. What the Shelly app does on a
> board that is not a Shelly (blank `shelly` partition, none of the hardware) is not known. Stage 1 below decides; [Seen on a board](#seen-on-a-board) records the results.

## Why

A wrong `min_version`, a package that keeps Shelly's bootloader ([issue #46](https://github.com/oxynatOr/free-shelly-ota/issues/46)), the wrong update slot, the
eFuse lines: all of it only shows when the real installer runs. On a board that costs a reset, on a device in a wall it can cost the device.
The package already holds everything the flash needs (the manifest says where each part goes), so the image is the same as the manual steps in
[Recovery over UART](recovery-uart.md), in one file and with the tool's checks.

## Which board

The chip family must match and the flash must hold the whole partition table of the device. Most ESP32-C3 dev boards have 4 MB and are too small for the Gen3 devices.

| Profile | Device | Chip | Flash needed | Board |
| --- | --- | --- | --- | --- |
| `PlusUni` | Plus Uni | ESP32 | 4 MiB | classic ESP32 board, 4 MB |
| `PlusPlugS` | Plus Plug S | ESP32 | 4 MiB | classic ESP32 board, 4 MB |
| `Pro3EM` | Pro 3EM | ESP32 | 16 MiB | classic ESP32 board with 16 MB (rare) |
| `PlugMG3` | Plug M Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `PlugSG3` | Plug S Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `PlugPMG3` | Plug PM Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `HTG3` | H&T Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `MiniPMG3` | PM Mini Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `Mini1G3` | Mini 1 Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `Mini1PMG3` | Mini 1PM Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `Pill` | The Pill | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `DuoBulbG3` | Duo Bulb Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `RGBCCTBulbG3` | Multicolor Bulb Gen3 | ESP32-C3 | 8 MiB | ESP32-C3 board with 8 MB |
| `PowerStrip` | Power Strip 4 Gen4 | ESP32-C6 | 8 MiB | ESP32-C6 board with 8 MB |
| `PowerStripZB` | Power Strip 4 Gen4 (Zigbee) | ESP32-C6 | 8 MiB | ESP32-C6 board with 8 MB |
| `Mini1PMG4` | Mini 1PM Gen4 | ESP32-C6 | 8 MiB | ESP32-C6 board with 8 MB |
| `Mini1PMG4ZB` | Mini 1PM Gen4 (Zigbee) | ESP32-C6 | 8 MiB | ESP32-C6 board with 8 MB |

`python -m esptool --port COMx flash-id` shows the flash size of a board. `--flash-size 4MB|8MB|16MB` makes `devkit` stop if the layout needs more.

## Steps

> [!WARNING]
> Use a spare board, never a device. The image overwrites the whole flash, bootloader included, and Shelly's updater burns an eFuse on it (see [Limits and risks](#limits-and-risks)).

1. **Stage 0, the starting point.** `python -m esptool --port COMx flash-id` and `python -m espefuse --chip <chip> --port COMx summary`. Keep the eFuse output: flash encryption and secure boot must be off,
   and you will compare it after the first update.
2. **Stage 1, the board boots.** Make the image and write it with the commands the tool prints:

   ```
   python ota.py fetch PlusUni --insecure
   python ota.py devkit PlusUni --flash-size 4MB
   ```

   Open a serial monitor at 115200 Bd. Expected: Shelly's loader prints its version and `Booting app 0`. Whether the Shelly app then runs and opens an access point is the open question.
3. **Stage 2, the tool reaches it.** Join the board's access point and check it:

   ```
   python ota.py send PlusUni out/<package>.zip --ip 192.168.33.1 --dry-run
   ```

   Expected: `Device ...: app=PlusUni`, the slot check and the reachability check.
4. **Stage 3, the update.** Send a package built with `--esphome-factory` and read the log (`--watch 120`, see [What to look for](#what-to-look-for)). Then read the eFuses again.
5. **Stage 4, again.** `erase-flash` and write the image once more. A run takes minutes, so the variations below are cheap.

## What to look for

| Log line | Meaning |
| --- | --- |
| `Update target slot: 0 ...` | The slot check of `send` (the Shelly app names its slot over the debug log) |
| `Boot: cur ... new ... min ... update? 1` | The installer writes the package's bootloader; `update? 0` means it keeps Shelly's |
| `Installing BL ... -> boot(0)` | The bootloader is written |
| `FW signatures: want 07 got 00` | The package is not signed by Shelly |
| `BURN BLOCK3` and `... - OK`, or `EFUSE write error` | The updater's eFuse writes (see below) |
| `ota_progress` up to 95 %, then `ota_success` | The update itself |
| `Uncommitted boot of app N (attempts 3)`, `Booting app N` | Shelly's loader (only with its bootloader) |

`espefuse summary` before and after the first update answers what the open eFuse notes in [Troubleshooting](troubleshooting.md#efuse) could not: which bits the updater changed.

## Variations to play through

- **The default (`update? 1`):** a package built with `--esphome-factory` and the profile's `boot_min_version`.
- **The bootloader is skipped:** build with `--esphome-factory --boot-min-version 1.0.3`, the value that gave `update? 0` on the Plus Uni; `send --watch` warns about it.
- **A package that keeps Shelly's bootloader:** `send` refuses it; with `--force` it reproduces [#46](https://github.com/oxynatOr/free-shelly-ota/issues/46) (three starts, then the loader goes back to the other slot; later OTAs are written but never started).
- **A second ESPHome OTA** after a full install: it takes effect.
- **The state after an install, without the installer:** `python ota.py devkit PlusUni --zip out/<your package>.zip` puts a built package on the board directly (ESPHome's bootloader and app).
- **Another version:** `--version` takes any cached official version, `--zip` any package file.

## Limits and risks

- **eFuse.** The updater logs `BURN BLOCK3` when it installs a package without Shelly's signature. That cannot be undone on that chip. Read `espefuse summary` first: on the classic ESP32, BLOCK3 may carry calibration data or a custom MAC.
- **No device data.** The partitions `shelly` and `aux` (identity and calibration) stay blank, NVS is empty. The Shelly app may start without them or may not.
- **No hardware.** There is no relay, meter or button; the app may log errors for them. Relay, LED and sensor behavior cannot be tested this way.
- **Chip and flash.** A C6 device needs a C6 board, the Pro 3EM a classic ESP32 with 16 MB. Without such a board that profile stays untested.
- **Shelly's firmware.** The image contains it. It is made locally from your cache, lies in `out/` (git-ignored) and must not be shared or uploaded; an image made with `--zip` from your own build can also hold your Wi-Fi data.

## Seen on a board

Nothing yet. Add the date, the board, the profile and what the serial monitor and `send --watch` showed, separately from what was only read from the packages.

---

> [!TIP]
> **Tried it?** Tell us what the board did: [open a device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml) or a bug.

[`devkit`](commands.md#devkit) · [Recovery over UART](recovery-uart.md) · [Bootloader and slots](bootloader-and-slots.md) · [Troubleshooting](troubleshooting.md)
