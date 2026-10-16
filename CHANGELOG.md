# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- `ROADMAP.md`: what is planned (now, next, later) and where testers can help; linked from the README.
- `docs/assets/social-preview.png` (1280×640): the image for GitHub's social preview (Settings → General → Social preview; it cannot be set from the repository).
- `tests/test_readme.py`: every profile is in the README device table, the "N profiles: ✅ … 🟡 … 🧪 …" line above it matches the table, the state symbols of the README and of
  `docs/devices/README.md` agree, and every relative link, anchor and image of the README exists.
- `tests/test_readme.py` also checks that no tracked picture lies outside `docs/assets/` (the logo and the social preview): device photos belong on the ESPHome device pages.
- `fetch` and `build --download` take `--from-version VER`: the update API answers per installed version (header `Shelly-Info`, found in the firmware), e.g. `--from-version 1.4.4` returns the stable 2.0.1 for the H&T Gen3 while the plain query returns only a beta.
- `fetch` and `build --download` take `--channel beta` to download the beta release from the update API (`stable` stays the default). A non-stable channel always asks the API unless `--version` is given.

### Fixed
- `build --dry-run` no longer touches an existing package. It built to the real output path and deleted it afterwards, so a dry run to check another config on the same day (same
  automatic name `<Device>-firmware.ota-<date>.zip`, as ESPHome always names the app `firmware.ota.bin`) replaced and removed the package that had just been built and flashed, and left its
  `.sha256` and `.report.json` behind. The dry run now builds in a scratch directory and prints `DRY RUN, nothing written`. Reported with a Plug M Gen3 build.

### Changed
- `build` stops when the automatically named output already exists (`--force` replaces it; `--tag LABEL` or `-o ZIP` give another name). A second build on the same day used to replace the
  first package silently, which may already be on a device. A name given with `-o` is still replaced without `--force`. `build --dry-run` reports it as a note instead of stopping.
- Shelly's stable 2.1.0 (built 2026-10-14) checked for the Mini 1PM Gen3, Mini 1PM Gen4 (and Zigbee), PM Mini Gen3, Plug M, Plug PM, Plug S, Power Strip (and Zigbee) and Pro 3EM
  by comparing the packages with the cached 2.0.1 ones: bootloader, partition table and filesystem image are identical, `boot.min_version` is still 1.0.2, and the app grows by about
  7.5 kB (the Pro 3EM app shrinks by 68 kB). No profile changes. The `Official package` row of those device pages says 2.1.0 now; the hardware runs were made with 2.0.1. The
  Plug M app fills 98.8 % of its slot in 2.1.0, about 33 kB are left.
- H&T Gen3 page: Shelly's update API lists only the beta `2.2.0-beta1` for this device (the 2.0.1 release is no longer served). The page fetches it with `--channel beta`, builds
  with `--version 2.2.0-beta1`, and says that the beta has the same partition table and bootloader header as 2.0.1 but was not flashed with this tool.
- All device pages (16 profiles on 15 pages, the Mini 1PM Gen4 page covers two) have a new layout: badges for state and chip, quick links with icons, a `Fact | Value` table
- All device pages (17 profiles on 16 pages, the Mini 1PM Gen4 page covers two) have a new layout: badges for state and chip, quick links with icons, a `Fact | Value` table
  (the state and the chip are only in the badges), a "Before you start" checklist, callouts (NOTE for what was confirmed or checked, IMPORTANT for the partition table,
  TIP to start from the ESPHome device page, WARNING for the way back, TIP to send a device report), "Flash it" as numbered steps and the log lines of "What to expect" as
  a table. The device-specific text (config, pins, notes, way back) is the same; two lines moved: the first sentence of the intro on untested pages ("Not tested on
  hardware") is now the badge, and the links to the device database in the pin sources are plain text, because the link is in the table. `docs/devices/README.md`
  describes the layout.
- Device pages link the ESPHome device page where one exists: Plug S Gen3, H&T Gen3, The Pill, Plus Plug S, Power Strip 4 Gen4, PM Mini Gen3, Mini 1PM Gen3 (the database calls it
  "Shelly 1PM Mini Gen3") and Mini 1 Gen3 ("Shelly 1 Mini Gen3"). The Plug M Gen3, Plug PM Gen3, Duo Bulb Gen3, Multicolor Bulb, Mini 1PM Gen4, Plus Uni and Pro 3EM have none (sitemap checked 2026-10-16).
- `tests/test_readme.py` also checks the device pages: the standard sections in order, the state badge against the README, the profile in the commands, and all
  relative links and anchors.
- README reworked. The device table has a `Note` column (the `State` column holds only the symbol) and a third state, 🟡 = flashed on a real device, but part of the chain
  or of the function is not checked: Plug PM Gen3 (readings), Power Strip (outlets) and Duo Bulb Gen3 (OTA not run) move there from ✅/🧪; the legend and the State lines of
  `docs/devices/README.md` and those three device pages follow. The non-affiliation text is a NOTE next to the WARNING instead of part of it, the Quick start goes
  in working order (config, compile, `fetch`/`build`/`send`), explains `--insecure`, uses `--ip` (the default `192.168.33.1` is only right on the Shelly's own access point),
  says to copy the partition CSV next to the YAML, adds the web-server note to the CAUTION and comes before "Another device?". The intro lists the three commands instead of one long
  sentence, says "no UART needed to install" next to "keep UART ready as your way back" and has a small diagram (Mermaid) of what goes into `build` and what `send` delivers.
  A summary line above the device table counts the states. The header has the logo (`docs/assets/logo.png`) in front of the title, the tagline below, then
  the badges and a row of links to the main sections; the badges are status, version, issues and license in a flat style (stars and forks removed, `WIP` in the title replaced
  by the status badge).
- `ota.py -h` and the help of every command are easier to scan. The top-level help lists the commands in the groups of `docs/commands.md` (Prepare, Build, Deploy,
  Tools), a typical run, what to know before flashing and the device names once. Each command has a short usage line, and its options are grouped by topic (`send`:
  the Shelly, this PC, what to do; `build`: app and bootloader, secrets, output, parts, base firmware). Long option texts are shorter and point to
  `docs/commands.md`. Options, defaults and behaviour are unchanged; `--color` shows `WHEN` in the usage. `tests/test_help.py` checks that every command is in a group, has a
  working `-h` and that no help line is wider than the terminal.
- Multicolor Bulb E27 Gen3 example config (`configs/shelly-rgbcct-bulb-g3/`): the light is now `rgbw_ct_table` (component of `oxynatOr/esphome-kp18058`) instead of `rgbw`: an RGB mode and a
  colour temperature mode 2700-6500 K (exclusive, like the stock web UI) with the stock firmware's 9-point table and RGB white balance (red 0.856, green 0.701, blue 0.749), linear brightness
  (`gamma_correct: 1.0`) and a 3 s default fade, all read from the 2.0.1 firmware. The packages daylight, daylight_sun, scenes, night, night_sun and wakeup use colour temperature instead of
  mixing RGB with the white (the white-mixing modes are gone); dimrange is only needed with gamma 2.8. The YAML pulls the component from `oxynatOr/esphome-kp18058@main`, where `rgbw_ct_table` has been published since 2026-10-15. Flashed on the bulb, it runs (owner, 2026-10-16); the colours were not compared with the stock firmware.
- Profile `PlugSG3` (revision 2): `boot_min_version: 1.0.9`. The Plug S Gen3 package carries the same bootloader as the Plug M Gen3 package (byte-identical, loader 1.0.3),
  so a plug that already runs it would skip the default 1.0.3 and silently keep Shelly's bootloader. The earlier run used the default on a plug with loader 1.0.2; the new
  value is not run on a Plug S Gen3 yet.
- Plug PM Gen3: flashed over OTA with this tool on a real plug (owner report, 2026-10-12). The device page, `docs/devices/README.md` and the README row go from 🧪 to ✅
  with "readings not checked"; the log lines (`Boot: cur ... update?`) and the BL0942 readings are not recorded yet.
- Profile `PlugMG3` (revision 2): `boot_min_version: 1.0.9`. The official package carries Shelly OS loader 1.0.3, so a Plug M restored from it
  would skip the default 1.0.3 and silently keep Shelly's bootloader (same cause as on the H&T and the Plug PM Gen3).
- Profile `RGBCCTBulbG3` (revision 2): `boot_min_version: 1.0.9`. After a return to stock the Multicolor Bulb runs Shelly OS loader 1.0.3, so the default
  1.0.3 would be skipped; with 1.0.9 the ESPHome bootloader was written (hardware-confirmed on a real bulb, 2026-10-11).
- Profile `DuoBulbG3` (revision 2): `boot_min_version: 1.0.9`, like the other Gen3 devices that needed it (Multicolor Bulb, same main board, loader 1.0.3 after a return to stock).
  Without it the installer may skip ESPHome's bootloader. Not run on a Duo Bulb yet.
- Recovery over UART: the ESP32-C3 command for the Plug M Gen3 (restored from ESPHome, boot log reviewed), and a note that pushing the
  official app image over ESPHome OTA is not a way back (the Shelly app cannot read ESP-IDF's `otadata`).
- Power Strip example config (`configs/shelly-power-strip-gen4/`): README and YAML name this tool instead of "ShellyOTA", the build command is relative to the
  repository root, and the slot-0 note links the Power Strip device page and "The app must land in slot 0" instead of a README section that is gone.
- Device pages: pin tables for Plug S Gen3, Duo Bulb Gen3, H&T Gen3, The Pill and Plus Plug S, taken from the ESPHome device database pages of the owner
  (and bobkersten for the Plus Plug S) and checked against the firmware where possible. The Plug S Gen3 state is plain ✅ now; the Duo Bulb pages say
  the ESPHome config runs (UART) while the OTA path is not run.
- `docs/commands.md` documents `add-device`, `inspect`, `clean` and `partition-csv`.
- README: "Another device?" is a section of its own (request it, make a profile yourself, send a device report) instead of one
  sentence under the device table.

### Fixed
- Without `--version`, `build`, `send`, `restore`, `fetch` and `partition-csv` took the highest cached version, and a downloaded pre-release such as `2.2.0-beta1`
  sorted above the stable `2.0.1`, so the beta would have been used silently. The default is now the newest stable cached version; a pre-release needs
  `--version`, or is used only when it is all that is cached.
- `send` read the package's `compatible` value as one pattern, so a comma separated list never matched. The Pro 3EM package says
  `Pro3EM,Pro3EMProAddon`, and a unit that reports `Pro3EMProAddon` stopped at the model check. The value is split at the commas now and every pattern is
  tried; such a unit gets the note "matches the package's compatible pattern" and goes on. No separate `Pro3EMProAddon` profile (not needed for this).

### Removed
- The `configs/` folder (example ESPHome configs for the Power Strip 4 Gen4 and the Multicolor Bulb E27 Gen3, with the light packages and pin notes; added in 0.3.0): device
  configs belong to the ESPHome device pages and to [`oxynatOr/esphome-configs`](https://github.com/oxynatOr/esphome-configs), not to the tool that installs the firmware.
  The Power Strip and Multicolor Bulb pages and `docs/README.md` no longer point into this repository. The files stay in the git history and in the tags `v0.3.0` and
  `v0.3.1`. The device pages carry no photos either: pictures belong on the ESPHome device page (`docs/devices/README.md` says so).
- Profile `Cury` (Shelly Cury), its partition CSV and device page (added in 0.3.1): the device has an NFC reader, regulated heaters and a
  voltage doubler that ESPHome cannot drive, and its pins are not decoded, so it is not a useful target. It is parked outside the repository.

### Added
- `send` (and `restore`) ask the device to fetch `http://<this PC>:<port>/` itself (RPC `HTTP.GET`) before they send. `--dry-run` fails with the device's
  `Connection error` if it cannot reach this PC, a real `send` prints a warning and goes on, and a device without `HTTP.GET` only gets a note. Suggested by [imsandli](https://github.com/imsandli) in the
  first device report (PM Mini Gen3), where the Shelly sat in an IoT VLAN that could not reach the PC and the plain run would have ended in the 300 s timeout.
  Not run on a real device yet: the exact error reply of the device is known from the report only.
- Profiles `PlusUni` (Shelly Plus Uni) and `Pro3EM` (Shelly Pro 3EM), both classic ESP32 (Gen2) made from the official 2.0.1 packages, with partition CSVs
  and device pages. The Pro 3EM has 16 MB flash (app slot `0x200000`, extra `emdata` partition), the Plus Uni 4 MB (`0x190000`). Both set
  `boot_min_version: 1.0.9` (the packages carry loader 1.0.2; the loader of a real unit has not been seen). Packages build and verify; not tested on
  hardware. No pin tables: the ESPHome device database has no page for either device. `Pro3EMProAddon` (Pro 3EM with Pro Sensor Addon) has no profile.
- Profile `Mini1G3` (Shelly Mini 1 Gen3, the Mini 1PM Gen3 without the power meter; partition table at `0xf000`, `boot_min_version: 1.0.9`) with partition CSV and a device page. Package builds and verifies; not tested on hardware.
- Profile `PlugPMG3` (Shelly Plug PM Gen3, S3PL-30116EU; it only measures, there is no relay) with its partition CSV, generated from the official
  2.0.1 package (app slots `0x280000`, smaller than the Plug M / Plug S). The profile sets `boot_min_version: 1.0.9`: the device runs Shelly OS
  loader 1.0.3, so the default 1.0.3 was skipped and later ESPHome OTAs did not take effect. The hardware result of the package route is not
  recorded here yet, so the state is 🧪.
- Device page `docs/devices/PlugPMG3.md` and a README row for the Plug PM Gen3: ESPHome `esp32:` block, pin table (read from the stock 2.0.1 firmware,
  not verified in a running ESPHome), commands and a UART restore command derived from the package manifest (not run on this plug).
- Index pages: `docs/README.md` (where to start, all pages, what to read when something goes wrong), `docs/devices/README.md` (all device pages with partition
  table offset and app slot size, where devices differ, what a page contains), `devices/README.md` (the profiles, the profile keys, how to change a profile)
  and `configs/README.md` (the example configs and how to use one).
- GitHub issue form **Request a new device** (model, `app` name, firmware, chip, whether you can test it; no dumps or secrets). The README links to it.
- GitHub issue forms: **Device report** (device, tool and Shelly version, method, result, `send --watch` output, with a reminder to remove
  secrets and the device cloud key) and **Bug or wrong message**. The README links to the device report.
- Multicolor Bulb E27 Gen3 example config (`configs/shelly-rgbcct-bulb-g3/`): eight optional packages (daylight by time and by the real sun, scenes,
  wake-up alarm, over-temperature protection, night light by time and by sun, dim range), each with its settings in its header. The per-channel test
  lights are gone: the channel order (OUT1 blue, OUT2 red, OUT3 green, OUT4 warm white) is tested on the bulb (2026-10-11). The main file gets the
  Home Assistant time component, an `id` on the light and `color_interlock: false`. The README and the device page mark the bulb as ✅ now; the folder
  README says what is tested.
- Profile `MiniPMG3` (Shelly PM Mini Gen3, S3PM-001PCEU16; measures only, no relay) with partition CSV and device page, made from the official 2.1.0 package (partition table `0xf000`, app slot
  `0x280000`, `boot_min_version: 1.0.9`). Hardware-confirmed by the first external device report ([imsandli](https://github.com/imsandli)): `send` from stock 2.0.1 with ESPHome's bootloader (loader 1.0.2 replaced), ESPHome OTAs
  afterwards, BL0942 readings. The page documents the BL0942 UART pins, the RX pull-up it needs and a voltage calibration. This is not the Mini 1PM Gen3 (`Mini1PMG3`), which stays untested.
- `CREDITS.md`: the projects the tool learned from (as in the README), the people who tested devices and sent reports (imsandli, bobkersten), Shelly and the tooling, and how to get on or off the list. The README links to it.

## [0.3.1] - 2026-10-06

### Added
- Profile `Cury` (Shelly Cury) with partition CSV and a device page. Package builds and verifies; not tested on hardware.
- Profile `Pill` (Shelly The Pill) with partition CSV and a device page. Package builds and verifies; not tested on hardware. Reported: the USB-C port exposes USB Serial/JTAG, so it can be flashed and recovered with esptool.
- Profile `Mini1PMG3` (Shelly Mini 1PM Gen3, partition table at `0xf000`) with partition CSV and a device page. Package builds and verifies; not tested on hardware.
- Profiles `Mini1PMG4` and `Mini1PMG4ZB` (Shelly Mini 1PM Gen4, Zigbee variant via `parent:`) with partition CSVs and a device page. Package builds and verifies; not tested on hardware.

## [0.3.0] - 2026-10-06

### Added
- `PlugSG3` (Plug S Gen3) is hardware-confirmed: `send` with `--esphome-factory`, ESPHome runs (base config without relay or metering).
- `RGBCCTBulbG3` (Multicolor Bulb Gen3): `send` with `--esphome-factory` ran through and ESPHome runs. The light itself is not confirmed.
- `PowerStrip` is hardware-confirmed (ESPHome boots with ESPHome's bootloader). Its profile sets `boot_min_version: 1.0.9`.
- Profile `PlusPlugS` (Shelly Plus Plug S, classic ESP32, Gen2) with partition CSV. Support for the classic ESP32: chip id 0,
  bootloader at `0x1000` (from the manifest), partition table at ESP-IDF's default `0x8000` (the ESPHome offset option may stay
  unset). Hardware-confirmed on a Plus Plug S V2 without UART: `restore`, then `send` (target slot 0), ESPHome booted and an
  ESPHome OTA took effect. UART recovery from the official package brought the bricked unit back to Shelly OS beforehand.
- README: "Recovery over UART".
- `send` checks the update target slot before sending a package that replaces the bootloader: it reads the device's
  `Storing core dumps to app_N` log line (briefly switching on the UDP log), refuses if N is not 0 (ESPHome's bootloader starts
  `app_0`) and points to `ota.py restore`; `--ignore-slot` overrides. Also shown by `--dry-run`.
- README: Plus Plug S (Gen2) install notes: the installer wrote the app to slot 1, ESPHome's bootloader started `app_0`, and
  `ota.py restore` (official package) put Shelly's bootloader back over OTA, after which the next `send` targeted slot 0. A UART
  `otadata` entry that selects `app_1` is documented as a fallback. Also: the ESPHome build must use the 80 MHz flash header
  (`CONFIG_ESPTOOLPY_FLASHFREQ_80M`), otherwise `build` refuses to replace the bootloader.
- Colored messages (`shelly_ota/ui.py`): yellow warnings, orange critical warnings, red errors, green success, cyan notes, dimmed
  device log lines. Only in a terminal; `NO_COLOR` and `--color auto|always|never` (before the command) control it. The
  words WARNING/NOTE/Error/OK stay in the text.
- Versions you can tell apart (`shelly_ota/buildinfo.py`): `--version` and a first line `free-shelly-ota <version (branch, git
  describe, date)>` on every command; the build report records the tool state, the profile name and revision and the build options
  (flags only); `send` prints the package's origin and notes a profile that changed since the build.
- Profile revisions: each `devices/*.yaml` has a `revision:`; `devices/profiles.lock` and the new `ota.py profiles` command (with
  `--update-lock`) guard against changing a profile without raising it; `list` shows the revision; `add-device` writes
  `revision: 1`.
- Documentation: the README is short now (device table, quick start, links); the rest moved to `docs/` with one page per
  device (`docs/devices/<Profile>.md`: ESPHome config, commands, log lines, pitfalls) and pages for commands, bootloader and
  slots, troubleshooting, recovery over UART, credential check and versions.

### Changed
- `send` notes that ESPHome's bootloader starts `app_0`, so the installer must write to slot 0 (`Will write to slot 0` in the
  `--watch` log); README documents the failure seen on the Power Strip Gen4 (stock 1.7.99 wrote to slot 1) and the fix (one
  official update first).
- `build` errors about the ESPHome bootloader header, the partition layout, a `.factory.bin` from another build, a wrong chip and
  an app that is too big now show both values in plain words (for example "4 MB, 40 MHz (0x20)" against "4 MB, 80 MHz (0x2f)")
  and a "Fix:" line naming the ESPHome setting that worked on the tested devices.
- README status lists the six hardware-confirmed devices.
- Messages checked for Gen2/Gen3/Gen4: removed the `slot 0` warning in `send` (it was wrong for H&T and Plus Plug S and clashed
  with the target-slot check; `send` now prints "reported slot" instead); the bootloader notes no longer say "confirmed on the
  Plug M Gen3 only"; the plain-package hint explains Shelly's uncommitted-boot counter instead of "keep UART ready";
  `--boot-min-version` help names the profile default and the `Boot: cur ... update?` log line; `list` says `app size`
  (it printed `slot=` for a size); `model=None` is shown as `n/a`; docstrings and README intro name Gen2/3/4.

## [0.2.0] - 2026-10-05

### Added
- `partition-csv` command and `partitions/<Device>-stock.csv` for every profile: the stock partition table as ESPHome
  `partitions:` CSV (so the README's Quick start works without extra files).
- Profile `HTG3` (Shelly H&T Gen3), hardware-confirmed with `--esphome-factory`.
- Optional profile key `pt_offset` (partition table address, default `0x10000`); `add-device` reads it from the package.
  The H&T Gen3 keeps its table at `0xf000`.

- Optional profile key `boot_min_version`: default for `--boot-min-version` with `--esphome-factory`. `HTG3` sets `1.0.9`:
  the H&T Gen3 installer reports an installed bootloader 1.0.3, so the generic "one patch above the package" (1.0.3) was
  skipped and Shelly's loader stayed. With 1.0.9 the bootloader is written (hardware-confirmed).

### Changed
- README: notes on the web server exposure during `send`, the UDP firewall for `--watch`, and the eFuse write errors seen on
  the H&T Gen3; the HTG3 row now covers an ESPHome OTA after the package install (confirmed).
- README: how to check that the bootloader was really replaced (installer log `Boot: cur ... min ...`, UART boot log) and
  the UART fix.

### Removed
- Profiles `PlugUSG4` and `PlugUSG4ZB` (Plug US Gen4): cannot be tested by the maintainer. `add-device` still creates
  profiles for them. The variant tests now use `PowerStrip` / `PowerStripZB`.

### Fixed
- `--esphome-yaml` check no longer hard-codes the partition table offset 0x10000; it uses the profile's `pt_offset`.
- RPC errors now include the device's answer (e.g. `OTA not allowed (Battery below 30 percent. )`) instead of only the HTTP code.

## [0.1.0] - 2026-10-04
First release (experimental).

### Added
- `build`, `send`, `restore`, `log`, `fetch`, `add-device`, `inspect`, `list`, `clean`; profiles for 8 Shelly Gen3/Gen4 devices
  (hardware-confirmed: Plug M Gen3 only).
- `--esphome-factory` / `--boot-min-version`: ship ESPHome's bootloader and a clean `otadata` in the package.
- Credential check: `build` compares the image with the ESPHome config and `secrets.yaml`, warns with the names of matches,
  records them in the report; `--secrets FILE`, `--fail-on-secrets`; `send` and `inspect` warn again.
- `ota.py --version`, `tool_version` in the build report.

### Changed
- Help texts and post-flash messages describe the bootloader options and their risk; the follow-up "update the bootloader"
  note and the `allow_partition_access` warning no longer appear when the package already carries ESPHome's bootloader.
- `send` says when it could not check whether the bootloader is replaced (no cached official ZIP).
