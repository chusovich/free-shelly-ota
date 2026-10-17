# Credential check

[← README](../README.md) · [Documentation](README.md) · [Commands](commands.md#build)

An ESPHome image stores Wi-Fi SSID/password, API keys and similar values **in plain text**, and so does every package built
from it.

> [!CAUTION]
> Never share, upload or commit such a ZIP. A package for others should come from a config without credentials (for example a
> Wi-Fi setup config).

`build` therefore compares the image (and the `--esphome-factory` image) with the values from your ESPHome config and its
`secrets.yaml`: `wifi.ssid`, `wifi.password`, `wifi.ap.password`, `api.encryption.key`, `api.password`, `ota[].password`,
`web_server.auth.password`, `mqtt.password` and every other value in `secrets.yaml`.

| Situation | What happens |
| --- | --- |
| A value is found in the image | `build` prints a warning with the **names** of the matches (never the values), writes them to `<zip>.report.json` as `contains_secrets`, and `send`/`inspect` warn again |
| `--fail-on-secrets` | The warning becomes an error |
| No `--esphome-yaml` or `--secrets` | Nothing can be compared; the build says so |
| The output file lies in a git work tree where it is not ignored | `build` warns |

---

[`build` options](commands.md#build) · [Troubleshooting](troubleshooting.md) · [Versions](versions.md)
