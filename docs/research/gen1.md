# Research: Shelly Gen1 (ESP8266)

[← README](../../README.md) · [Documentation](../README.md) · [Roadmap](../../ROADMAP.md)

Working notes for [issue #47](https://github.com/oxynatOr/free-shelly-ota/issues/47) (Shelly 1, Gen1). Nothing here is built or tested on a device:
it is what the official package and public sources show, and what is still open. Not a promise, and not part of the supported devices.

## Why it matters

Gen1 devices (Shelly 1, 1PM, 2.5, Plug S, Dimmer, Bulb, ...) are old, many are in the wall, and their owners cannot solder or hold pogo pins on a PCB.
An OTA route would help exactly those people. If it works, the README could say "all Shelly generations" instead of "Gen2 to Gen4".
That sentence only becomes true when one Gen1 device has run the whole chain.

## What the official Shelly 1 package contains

`http://firmware.shelly.cloud/gen1/SHSW-1.zip` (880 214 bytes, build `20230913-112003/v1.14.0-gcb84623`) holds one folder `switch1-1.0/`:

| File | Size | Part in `manifest.json` |
| --- | --- | --- |
| `rboot.bin` | 2 320 | `boot`, address `0x0`, **`update: false`** |
| (none) | 4 096 | `boot_cfg`, address `0x1000`, filled with `0xFF` (the rboot config: which slot starts) |
| `switch1.bin` | 613 504 | `fw`, address `0x8000` and `addr1` `0x108000` (two app slots) |
| `fs.bin` | 262 144 | `fs`, address `0xBB000` and `addr1` `0x1BB000` |
| (none) | 4 096 | `rf_cal_data`, address `0x1FB000` |
| `esp_init_data_default_v08.bin` | 128 | `sys_params`, address `0x1FC000` |

`platform` is `esp8266`, manifest `version` is `1.0`. So the layout is a 2 MB flash with **rboot** and two app slots of `0xB3000` (733 184 bytes) each; the stock app
uses 613 504 of them. There is no `otadata` and no ESP-IDF partition table.

The app image starts with `0xEA` (rboot's flash-mapped format, 4 segments); `rboot.bin` itself starts with `0xE9`.

## How the update works (read from the app)

The Shelly app is **Mongoose OS** (paths such as `/mongoose-os/platforms/esp8266/src/esp_flash_writer.c`, `ota-common/src/esp8266/esp_ota_backend.c` and
`shelly-common/shelly_update.c` are in its strings). The strings show:

- The device fetches a ZIP from a URL (`http://<ip>/ota?url=...`) with its HTTP client and reads `manifest.json` first:
  `{name, platform, version, build_id, parts}` are required, `Invalid manifest` / `Nothing interesting in the update (wrong platform?)` otherwise.
- Each file is checked against `size` and `cs_sha1` / `cs_sha256` of the manifest, then written to the slot that is **not** running, `boot_cfg` is updated and the
  device restarts. A failed start reverts (`Update failed, reverting to ROM %d`); a new app has to commit itself (`Previous update has not been committed yet`).
- The manifest can carry signatures (`sig0` ... `sig7`, strings `Signature verified` / `Want sig ..., have ...` / `Key %d: no signature`). The stock package has none.
  **Not known:** whether the stock firmware enforces them. Third-party ZIPs are known to be accepted on stock firmware (see below), but not on 1.14 specifically.
- `Version is the same as current` aborts an update, `will not update %s with %.*s` (shelly_update.c) is a name check whose rule is not known.
- The Gen1 API is plain HTTP (`/shelly`, `/status`, `/settings`, `/ota`, `/ota/check`), not the RPC of Gen2 and later. There is no `Shelly.Update`, no `Shelly.GetDeviceInfo`.

## Precedents

- **[mgos-to-tasmota](https://github.com/yaourdt/mgos-to-tasmota)** (GPL-3.0, last push 2023-02, maintainer stopped, its download server is not guaranteed): `http://<ip>/ota?url=...zip` installs
  a small **Mongoose OS stub**. The stub then downloads Tasmota and writes it over the bootloader. So third-party ZIPs are accepted by stock Gen1 firmware, and the
  working route for a foreign firmware is **two stages**, not a direct swap of the app slot. The author warns that overwriting the bootloader over OTA can brick a device.
- **[shelly-homekit](https://github.com/juangamnik/shelly-homekit)**: a Mongoose OS firmware for Gen1, installed through the same `/ota?url=` on stock firmware. It stays inside rboot's layout.
- The reverse, Tasmota back to stock, also exists (`tasmota-to-mgos`).

## What the tool does today, and what Gen1 needs

| Area | Today (Gen2 to Gen4) | Gen1 |
| --- | --- | --- |
| Chip | ESP32, ESP32-C3, ESP32-C6 (`esp_image` checks chip id, segments) | ESP8266: other image format (`0xE9` / `0xEA`), no chip id in the header |
| Package | `manifest.json` with `boot`, `pt`, `otadata`, `nvs`, `app`, `fs` | `boot`, `boot_cfg`, `fw` (two addresses), `fs`, `rf_cal_data`, `sys_params`; sha1 **and** sha256 |
| Partition table | ESP-IDF table, `partitions/<Profile>-stock.csv` for ESPHome | none; ESPHome on ESP8266 uses Arduino's layout |
| Send | RPC `Shelly.Update?url=`, slot probe over the UDP log, progress, confirmation | HTTP `/ota?url=`; log and progress probably not available |
| Device check | `Shelly.GetDeviceInfo` (model must match) | `GET /shelly` (`type`, `fw`) |
| Way back | `restore` while Shelly firmware runs; UART | same idea with the Gen1 ZIP; UART |

## Open questions (each one needs an experiment)

1. **Can an ESPHome image run from an rboot slot?** ESPHome for ESP8266 is an Arduino build: its `firmware.bin` is made for flash address `0x0` with eboot, and its own OTA copies a new image over it.
   Whether rboot can start it from `0x8000` (it is position-dependent in the flash mapping) is not known. Test on an ESP8266 board with 2 MB flash and Shelly's `rboot.bin` and `boot_cfg`, like the DevKit image does for Gen2 and later.
2. **Is the `boot` part writable?** The stock manifest says `update: false`. If the updater honours `update: true`, a package could replace rboot with ESPHome's boot code, as the Gen2 route does. If it does not, only the two-stage route of mgos-to-tasmota is left.
3. **Signatures on 1.14.** Does the current stock firmware accept an unsigned third-party manifest? `shelly-homekit` and `mgos-to-tasmota` say yes for older firmware.
4. **Size.** An ESPHome image for a Shelly 1 has to fit into `0xB3000` (733 184 bytes) minus what ESPHome's own OTA needs afterwards. It was not measured here.
5. **Later ESPHome OTAs.** After the first install, ESPHome's OTA on ESP8266 needs free flash next to the sketch; whether the rboot layout leaves it is open.
6. **Gen1 ZIP rules.** `will not update %s with %.*s` and the manifest `name` (`switch1`): what must match.
7. **Log.** Gen1 has a debug setting; whether it can send the log over UDP like Gen2 does (for progress and the slot) is not known.

## A possible plan

1. **Bench first, no device at risk.** ESP8266 board with 2 MB, Shelly's `rboot.bin`, `boot_cfg` and a stock slot (question 1 and 2): does ESPHome start from a slot, and does the stock updater write a package that this tool builds?
2. **A Gen1 package builder** for one profile (Shelly 1), `fw` part replaced, hashes fixed, optional `boot` swap if question 2 says yes.
3. **A Gen1 sender** over `/ota?url=` with the model check and a clear warning that there is no progress.
4. **One real device** (the reporter of #47 has a Shelly 1 and UART access) before anything is listed as supported.
5. **Other Gen1 models** as profiles, once the first one is confirmed.

If question 1 and 2 are both "no", the only route left is a two-stage stub as in mgos-to-tasmota: much more work, a GPL-3.0 starting point and a binary that has to be hosted somewhere.

## Reproduce

The numbers above come from unpacking `SHSW-1.zip` (SHA-256 `2490c3f6a9b9f243fe9e00112f22baa36f9e240cb8c9e6dca5be58d946ad146f`) and reading `switch1-1.0/manifest.json`, the image header of `switch1.bin` and the strings of the app.
The package is Shelly's file and is not part of this repository.
