"""Talk to a Shelly over Bluetooth LE (its RPC channel): scan, call a method, give it a Wi-Fi.

Devices that come without Wi-Fi (the Zigbee firmware has no access point, the log says `WiFi mode: off`) cannot be reached by
`send`. Their Bluetooth RPC is on, and `Wifi.SetConfig` over it gives them a network. Needs the `bleak` package (optional,
imported when a function here runs, so the other commands do not depend on it).

The channel (Shelly's documented BLE RPC): one service with three characteristics. Their UUIDs are ASCII text in the firmware
(`_mOS_RPC_SVC_ID_` ...), so they are built from it here.
  tx_ctl <- 4 bytes big endian: length of the request;   data <- the request in chunks
  rx_ctl -> 4 bytes big endian: length of the answer;    data -> the answer in chunks
"""

from __future__ import annotations

import asyncio
import json
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from .builder import OtaError

SERVICE = uuid.UUID(bytes=b"_mOS_RPC_SVC_ID_")
DATA = uuid.UUID(bytes=b"_mOS_RPC_data___")
TX_CTL = uuid.UUID(bytes=b"_mOS_RPC_tx_ctl_")
RX_CTL = uuid.UUID(bytes=b"_mOS_RPC_rx_ctl_")

MIN_CHUNK, MAX_CHUNK = 20, 240
SOURCE = "free-shelly-ota"


class BleError(OtaError):
    pass


class GattIO(Protocol):
    """What `exchange` needs from a connection; the tests use a fake, `_BleakIO` is the real one."""

    async def write(self, char: uuid.UUID, data: bytes) -> None: ...

    async def read(self, char: uuid.UUID) -> bytes: ...


@dataclass(frozen=True)
class Found:
    address: str
    name: str
    rssi: int


def _bleak():
    try:
        import bleak
    except ImportError as e:
        raise BleError("Bluetooth needs the 'bleak' package: pip install bleak (or pip install -r requirements-ble.txt). "
                       "It also needs a Bluetooth LE adapter in this PC.") from e
    return bleak


def encode_request(method: str, params: dict | None = None, *, req_id: int = 1) -> bytes:
    request: dict = {"id": req_id, "src": SOURCE, "method": method}
    if params is not None:
        request["params"] = params
    return json.dumps(request, separators=(",", ":")).encode()


def frame_length(n: int) -> bytes:
    return struct.pack(">I", n)


def parse_length(raw: bytes) -> int:
    return struct.unpack(">I", bytes(raw)[:4].ljust(4, b"\0"))[0]


def chunks(payload: bytes, size: int) -> list[bytes]:
    return [payload[i:i + size] for i in range(0, len(payload), size)]


def chunk_size(mtu: int | None) -> int:
    return max(MIN_CHUNK, min((mtu or 23) - 3, MAX_CHUNK))


def decode_answer(method: str, body: bytes) -> dict:
    """The `result` of an answer; a Shelly error or a broken answer becomes a BleError."""
    try:
        answer = json.loads(body.decode())
    except (UnicodeDecodeError, ValueError) as e:
        raise BleError(f"{method}: the answer is not JSON ({e}).") from e
    if "error" in answer:
        error = answer["error"]
        text = error.get("message", error) if isinstance(error, dict) else error
        raise BleError(f"{method}: the device answered with an error: {text}")
    result = answer.get("result", {})
    return result if isinstance(result, dict) else {"result": result}


async def exchange(io: GattIO, payload: bytes, *, chunk: int, timeout: float, poll: float = 0.2) -> bytes:
    """Send one request and return the raw answer."""
    loop = asyncio.get_running_loop()
    await io.write(TX_CTL, frame_length(len(payload)))
    for part in chunks(payload, chunk):
        await io.write(DATA, part)
    deadline = loop.time() + timeout
    length = 0
    while loop.time() < deadline:
        length = parse_length(await io.read(RX_CTL))
        if length:
            break
        await asyncio.sleep(poll)
    if not length:
        raise BleError(f"The device gave no answer within {timeout:.0f} s (is BLE RPC on? is it too far away?).")
    body = b""
    while len(body) < length and loop.time() < deadline:
        part = bytes(await io.read(DATA))
        if not part:
            await asyncio.sleep(0.1)
            continue
        body += part
    if len(body) < length:
        raise BleError(f"The answer stopped after {len(body)} of {length} bytes.")
    return body[:length]


class _BleakIO:
    def __init__(self, client):
        self.client = client

    async def write(self, char: uuid.UUID, data: bytes) -> None:
        await self.client.write_gatt_char(char, data, response=True)

    async def read(self, char: uuid.UUID) -> bytes:
        return bytes(await self.client.read_gatt_char(char))


async def _scan(seconds: float) -> list[Found]:
    bleak = _bleak()
    seen = await bleak.BleakScanner.discover(timeout=seconds, return_adv=True)
    out = []
    for address, (device, adv) in seen.items():
        name = adv.local_name or device.name or ""
        advertises = str(SERVICE) in [s.lower() for s in adv.service_uuids]
        if name.lower().startswith("shelly") or advertises:
            out.append(Found(address, name, adv.rssi))
    return sorted(out, key=lambda f: -f.rssi)


def scan(seconds: float = 8.0) -> list[Found]:
    """The Shellies in range, the strongest first."""
    try:
        return asyncio.run(_scan(seconds))
    except OSError as e:
        raise BleError(f"Bluetooth is not available: {e}") from e


def find_device(seconds: float = 8.0) -> Found:
    found = scan(seconds)
    if not found:
        raise BleError("No Shelly found over Bluetooth. Is it powered and close by, and is BLE RPC on?")
    return found[0]


async def _rpc(address: str, method: str, params: dict | None, timeout: float) -> dict:
    bleak = _bleak()
    async with bleak.BleakClient(address, timeout=20.0) as client:
        body = await exchange(_BleakIO(client), encode_request(method, params),
                              chunk=chunk_size(getattr(client, "mtu_size", None)), timeout=timeout)
    return decode_answer(method, body)


def rpc(address: str, method: str, params: dict | None = None, *, timeout: float = 15.0) -> dict:
    """One RPC call over one connection; returns the `result`."""
    try:
        return asyncio.run(_rpc(address, method, params, timeout))
    except BleError:
        raise
    except (OSError, asyncio.TimeoutError, TimeoutError) as e:
        raise BleError(f"{method}: Bluetooth connection failed: {e}") from e


def provision_wifi(address: str, ssid: str, password: str = "", *, wait: float = 40.0, interval: float = 3.0,
                   call: Callable[..., dict] = rpc, sleep: Callable[[float], None] = time.sleep,
                   clock: Callable[[], float] = time.monotonic) -> str | None:
    """Wifi.SetConfig (station), then wait for an IP. Returns it, or None when wait is 0."""
    station: dict = {"ssid": ssid, "enable": True}
    if password:
        station["pass"] = password
    call(address, "Wifi.SetConfig", {"config": {"sta": station}})
    if wait <= 0:
        return None
    deadline = clock() + wait
    while True:
        status = call(address, "Wifi.GetStatus")
        if status.get("status") == "got ip" and status.get("sta_ip"):
            return status["sta_ip"]
        if clock() >= deadline:
            raise BleError(f"The device did not get an IP within {wait:.0f} s (last status: {status.get('status')!r}). "
                           "Check the SSID and the password.")
        sleep(interval)
