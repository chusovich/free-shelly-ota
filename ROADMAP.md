# Roadmap

Where the project stands and where it goes next. This is a plan, not a promise: the order changes when a test report or a new device
shows up. State: 2026-10-16, after the tag `v0.3.1` and the unreleased changes in the [CHANGELOG](CHANGELOG.md).

## Now

- **Release 0.4.0.** Since 0.3.1: the PM Mini Gen3 profile (the first outside report), the reachability check in `send`,
  `fetch --channel` and `--from-version`, "newest stable" as the default cached firmware, the new README and device pages.
  Steps: CHANGELOG, version, `python ota.py profiles --update-lock`, tag, GitHub Release.
- **Check the new stable 2.1.0.** The update API lists 2.1.0 (built 2026-10-14) for the Mini 1PM Gen3 and the PM Mini Gen3. Compare the
  partition table and the loader with the 2.0.1 profiles, and update `Official package` on the pages where it changed.
- **Fix the model check for `compatible` lists.** The Pro 3EM package says `Pro3EM,Pro3EMProAddon`, and `send` reads that as one pattern,
  so a unit that reports `Pro3EMProAddon` stops at the model check. Split the list, then decide on a `Pro3EMProAddon` profile.
- **Decide `boot_min_version` for the Plug S Gen3.** Its official package carries the same bootloader file as the Plug M, Plug PM and
  Multicolor Bulb packages (loader 1.0.3). Those profiles set 1.0.9; the Plug S profile still uses the default, which would skip it.

## Next

- **Hardware checks** (these turn 🟡 into ✅): the Plug PM Gen3 readings (and the BL0942 RX pull-up found on the PM Mini),
  the Power Strip outlets and metering, the Duo Bulb over OTA.
- **Multicolor Bulb.** The colour temperature light (`rgbw_ct_table`, published in `oxynatOr/esphome-kp18058` since 2026-10-15) runs on the
  bulb. Still open: its colours against the stock UI at 2700, 4000 and 6500 K, the optional light packages (daylight, scenes, wake-up alarm,
  night light), and pinning a commit of the component in `configs/shelly-rgbcct-bulb-g3/` instead of `@main`.
- **Device pages on devices.esphome.io** for the Plug M, Plug PM and PM Mini (new pages) and a correction of the Plug S page, each with the
  OTA route via this tool. A page for the Multicolor Bulb can follow now that its light component is published; Duo Bulb and Mini 1 Gen3
  when their hardware is checked.
- **Tests without the firmware cache.** Many tests need the local `fw/` folder, which is not in git. Small synthetic packages as
  fixtures, then a GitHub Actions run on every pull request.
- **More devices on request.** Mini 1 Gen3 (a profile is prepared locally), Plug US Gen4 (parked), and whatever the
  "Request a new device" form brings.

## Later (ideas, not planned)

- **Tasmota support.** Pack a Tasmota image into the official package instead of an ESPHome one, the way
  [tasmota/mgos32-to-tasmota32](https://github.com/tasmota/mgos32-to-tasmota32) converts Shelly packages. Open questions: which of the
  profiles it fits (ESP32, ESP32-C3, ESP32-C6), the partition table and bootloader Tasmota needs, and the way back. Needs a device and a
  tester who runs Tasmota.
- **ESPHome back to Shelly, over the network.** A dead end so far: the Shelly app cannot read ESP-IDF's `otadata`, so pushing the
  official app image through an ESPHome OTA does not bring Shelly OS back. `restore` works only while Shelly firmware still runs;
  after that only UART helps ([Recovery over UART](docs/recovery-uart.md)). Revisit only with new findings.
- A command that prints the `esp32:` block of a profile, so the device pages can be generated and cannot drift.
- Find the device on the network (mDNS) instead of `--ip`.
- Install with `pipx` and a `pyproject.toml`.

## Help wanted

| What | Who can help | Where |
| --- | --- | --- |
| Flash a 🧪 device and report the `--watch` log | Owners of the 🧪 devices in the [table](README.md#supported-devices), 7 so far | [Device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml) |
| Plus Uni and Pro 3EM: a first hardware report, the pins | Owners | Issues [#35](https://github.com/oxynatOr/free-shelly-ota/issues/35) and [#36](https://github.com/oxynatOr/free-shelly-ota/issues/36) |
| Plug PM Gen3: readings against a reference meter | Owners | [Device report](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=device-report.yml) |
| Your device is missing | Anyone | [Request a new device](https://github.com/oxynatOr/free-shelly-ota/issues/new?template=new-device.yml) |
