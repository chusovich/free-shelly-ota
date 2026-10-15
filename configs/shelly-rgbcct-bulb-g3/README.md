# Shelly Multicolor Bulb E27 Gen3 (RGBCCT) - ESPHome notes and config

Status: **runs on a real bulb.** `ota.py send` with `--esphome-factory` ran through and ESPHome runs (owner, 2026-10-06). The owner tested the light on
2026-10-11 with an RGBW light: the channel order below is confirmed. Not measured: colour accuracy, the lowest dimming steps, the driver currents
and the power consumption. **New (not yet flashed):** the config now uses a light with a colour temperature mode and the stock RGB white balance, see "Light".

Files: `shelly-rgbcct-bulb-g3.yaml` (config), the LED driver and the light live in their own repository, https://github.com/oxynatOr/esphome-kp18058 (components `kp18058` and `rgbw_ct_table`), `RGBCCTBulbG3-stock.csv` (Shelly's partition table from the
official 2.0.1 package), `secrets.yaml.example`.

## What is known

| What | Value | Source |
|---|---|---|
| Chip | ESP32-C3, 8 MB flash, partition table at `0x10000` | boot log, official package |
| I2C bus | **SDA = GPIO4, SCL = GPIO5, 100 kHz** | the firmware's own boot log: `I2C0: init ok (SDA: 4, SCL: 5, freq: 100000)` |
| LED driver | **KP18068** (Kiwi Instruments, 5-channel I2C LED driver) | marking `KP18068ESP` read on the board by the owner; the frame below matches the KP18058 family |
| Light component in Shelly OS | `rgbcct:0` | boot log |

## The frame Shelly OS sends (read from the firmware code, not measured on the bus)

The firmware writes **13 bytes** over its hardware I2C bus to a 7-bit address that depends on the state:

- address **`0x70`** (wire byte `0xE0`) when at least one channel is on, **`0x40`** (wire byte `0x80`) when all channels are off
  (standby).

```
byte  0      0x00
byte  1      0x0A when on, 0x03 when off            = (RGB current 5 << 1) | parity, or the fixed standby value
byte  2      0x56                                    = bit 6 set | (CW current 11 << 1) | parity
bytes 3..12  five channels, two bytes each, in this order of bytes: high part, then low part
             high = ((v >> 5) & 0x1F) << 1 | parity      low = (v & 0x1F) << 1 | parity     (v = 10-bit value, 0..1023)
```

Every byte carries an even-parity bit in bit 0.

**Channel order** (read from two places in the firmware: the function that builds the frame from the colour parameters, and
the start-up routine that lights the three colours one after the other; both put the first colour value on OUT2, the second on
OUT3 and the third on OUT1): **OUT1 = blue, OUT2 = red, OUT3 = green.** That the three values are R, G, B in this order is
inferred from the start-up order, not proven. **Tested on the bulb (owner, 2026-10-11): OUT1 = blue, OUT2 = red, OUT3 = green, OUT4 = warm (yellowish) white, OUT5 = nothing visible on its own; the white has a fixed colour temperature.** In every mode **OUT4 and OUT5 get the same value**, so the bulb
has RGB plus one white LED. The config drives OUT4 and OUT5 together from one template output. The 13-byte length, the standby bytes `0x00 0x03`, the parity bits and the 5-bit halves all match the KP18058/KP18068
protocol as implemented by the OpenBeken project (which sends the low half first and a slightly different third byte; the
differences may be a chip variant, they were not checked).

## Light (what the stock firmware does, from its code)

Read from the 2.0.1 firmware (`__Idea/reference/rgbcct-bulb-stock-firmware.md` has addresses and the full audit). Two exclusive modes, like the Color and White tabs of the web UI:

- **RGB:** level of each colour = colour/255 * brightness, linear (no gamma), then multiplied by a fixed white balance: **red 0.856, green 0.701, blue 0.749**. White is off.
- **Colour temperature 2700-6500 K:** there is only one (warm) white LED. The firmware makes the other temperatures from a 9-point table of 10-bit levels for blue, red, green and white,
  linearly interpolated, times brightness (the white-balance factors are not applied here):

| K | 2700 | 3000 | 3500 | 4000 | 4500 | 5000 | 5700 | 6000 | 6500 |
|---|---|---|---|---|---|---|---|---|---|
| white (OUT4 = OUT5) | 1023 | 635 | 483 | 451 | 494 | 490 | 441 | 426 | 425 |
| blue (OUT1) | 0 | 86 | 112 | 182 | 220 | 240 | 267 | 325 | 366 |
| red (OUT2) | 0 | 325 | 314 | 361 | 100 | 17 | 0 | 0 | 0 |
| green (OUT3) | 0 | 314 | 373 | 511 | 600 | 650 | 662 | 659 | 659 |

The main file does the same with the light platform `rgbw_ct_table` (red/green/blue gain for RGB mode, the table for colour temperature), `gamma_correct: 1.0` and a 3 s default fade (the stock `transition_duration`).
Not verified on the lamp: whether the colours look like the stock firmware (compare the stock web UI and this config at 2700, 4000 and 6500 K).
Two details of the stock firmware that are not copied: it sends a lower RGB current code (`0x03` instead of `0x0A`) at exactly 2700 K (only the white LED on), and it starts a transition with a timer of 20 ms steps.
The boot state is not copied either: stock turns the lamp ON at power-up, the ESPHome default for a light is OFF (set `restore_mode` on the light if you want it).

## What is missing

- **No official ESPHome component.** There is no `kp18058` page in the ESPHome documentation; the pull request
  (esphome/esphome#7685) was closed. The config uses the separate component
  [oxynatOr/esphome-kp18058](https://github.com/oxynatOr/esphome-kp18058) (2-wire bit-bang on two pins, frame as above), taken from its
  `main` branch (pin a commit for a stable build). Differences to the Shelly firmware: it sends the address byte `0xE1` (Shelly's I2C hardware sends `0xE0`), and it needs
  an ACK for every byte unless `ignore_ack: true` is set (the chip may not send one). If the light stays dark, try `ignore_ack`
  first. The first build on the bulb used an earlier version of the component than the pinned one.
- The current codes (5 for RGB and 11 for white, read from the constants) and the behaviour at full brightness are unverified.
  The channel order is tested (see above).

## Installing

Use this tool as for the other devices ([device page](../../docs/devices/RGBCCTBulbG3.md)): build with the partition table from `RGBCCTBulbG3-stock.csv` and
`CONFIG_PARTITION_TABLE_OFFSET: "0x10000"`, then `ota.py build RGBCCTBulbG3 ... --esphome-factory ...`, `ota.py send` (it
checks that the installer writes to slot 0 and tells you when to run `ota.py restore` first). Confirmed on this device (the first build used the config of this folder).
Keep UART or USB access as your way back.

## Duo Bulb

The Duo Bulb has a different lamp module (PWM, no I2C), so this config's LED driver does not apply to it. Its pins and the state of
its OTA path are on the [Duo Bulb page](../../docs/devices/DuoBulbG3.md).

## Optional extras (packages)

All untested on the bulb; each file has its settings and notes in its header. They need `id: bulb` on the light (platform `rgbw_ct_table`) and the `ha_time` time component, which the main file provides. They use the colour temperature and RGB modes of that light
(daylight, scenes, night and the second half of the sunrise are colour temperature, "Sunset", "Candle" and the first half of the sunrise are RGB). Add the ones you want:

```yaml
packages:
  daylight: !include daylight.yaml        # effect "Daylight": fixed times (warm -> cool -> warm)
  sun: !include daylight_sun.yaml         # effect "Daylight (sun)": follows the real sun; set your coordinates first
  scenes: !include scenes.yaml            # effects Relax, Reading, Focus, Energize, Sunset, Night light, Candle
  wakeup: !include wakeup.yaml            # sunrise alarm: switch "Wake alarm" + buttons "Sunrise start/stop"
  overtemp: !include overtemp.yaml        # protection: chip temperature sensor, dims above 75 degC, light off at 90 degC
  night: !include night.yaml              # effect "Night (time)": 2700 K at 5 % between night_start and night_end
  night_sun: !include night_sun.yaml      # effect "Night (sun)": same, while the sun is below -4 degrees (needs daylight_sun.yaml)
  dimrange: !include dimrange.yaml        # floor/ceiling for the outputs; only needed if you set gamma_correct back to 2.8 (the main file uses 1.0)
```

A config with all eight packages passes `esphome config` and compiles (ESPHome 2026.10.0-dev, 993 KB of the 2.5 MB slot; not flashed).
