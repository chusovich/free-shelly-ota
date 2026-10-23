"""Bluetooth RPC of a Shelly: the framing, the chunking and the Wi-Fi step, against a fake connection (no Bluetooth needed).

Run from ShellyOTA/: python -m unittest discover tests
"""

import asyncio
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ota  # noqa: E402
from shelly_ota import ble, builder  # noqa: E402


class FakeShelly:
    """The device side of the channel: collects the request (length in tx_ctl, bytes in data), then offers the answer."""

    def __init__(self, handler, read_size=100, silent=False):
        self.handler, self.read_size, self.silent = handler, read_size, silent
        self.expect = 0
        self.request = b""
        self.answer = b""
        self.sent = 0
        self.writes = []

    async def write(self, char, data):
        self.writes.append((char, bytes(data)))
        if char == ble.TX_CTL:
            self.expect = int.from_bytes(data, "big")
            self.request = b""
        elif char == ble.DATA:
            self.request += data
            if len(self.request) >= self.expect and not self.silent:
                req = json.loads(self.request)
                self.answer = json.dumps({"id": req["id"], "src": "fake", "dst": req["src"],
                                          **self.handler(req)}).encode()
                self.sent = 0

    async def read(self, char):
        if char == ble.RX_CTL:
            return len(self.answer).to_bytes(4, "big")
        part = self.answer[self.sent:self.sent + self.read_size]
        self.sent += len(part)
        return part


class FramingTests(unittest.TestCase):
    def test_the_uuids_are_the_ascii_text_of_the_firmware(self):
        self.assertEqual(str(ble.SERVICE), "5f6d4f53-5f52-5043-5f53-56435f49445f")
        self.assertEqual(str(ble.DATA), "5f6d4f53-5f52-5043-5f64-6174615f5f5f")
        self.assertEqual(str(ble.TX_CTL), "5f6d4f53-5f52-5043-5f74-785f63746c5f")
        self.assertEqual(str(ble.RX_CTL), "5f6d4f53-5f52-5043-5f72-785f63746c5f")

    def test_request_length_and_chunks(self):
        payload = ble.encode_request("Wifi.SetConfig", {"config": {"sta": {"ssid": "x"}}})
        self.assertEqual(json.loads(payload)["method"], "Wifi.SetConfig")
        self.assertNotIn(b" ", payload)
        self.assertEqual(ble.parse_length(ble.frame_length(70000)), 70000)
        self.assertEqual(ble.parse_length(b"\x00\x01"), 0x00010000)       # a short read is padded, not an error
        self.assertEqual(b"".join(ble.chunks(payload, 20)), payload)
        self.assertTrue(all(len(c) <= 20 for c in ble.chunks(payload, 20)))

    def test_chunk_size_follows_the_mtu_within_limits(self):
        self.assertEqual(ble.chunk_size(None), 20)
        self.assertEqual(ble.chunk_size(247), 240)
        self.assertEqual(ble.chunk_size(100), 97)

    def test_an_error_answer_becomes_a_ble_error(self):
        with self.assertRaises(ble.BleError) as ctx:
            ble.decode_answer("Wifi.SetConfig", b'{"id":1,"error":{"code":-103,"message":"bad ssid"}}')
        self.assertIn("bad ssid", str(ctx.exception))
        with self.assertRaises(ble.BleError):
            ble.decode_answer("X", b"not json")
        self.assertEqual(ble.decode_answer("X", b'{"id":1,"result":{"a":1}}'), {"a": 1})


class ExchangeTests(unittest.TestCase):
    def run_exchange(self, shelly, payload, chunk=20, timeout=2.0):
        return asyncio.run(ble.exchange(shelly, payload, chunk=chunk, timeout=timeout, poll=0.01))

    def test_a_long_request_and_a_long_answer_go_through_in_pieces(self):
        long_name = "n" * 300
        shelly = FakeShelly(lambda req: {"result": {"echo": req["params"]["name"], "pad": "p" * 500}}, read_size=64)
        payload = ble.encode_request("Test", {"name": long_name})
        body = self.run_exchange(shelly, payload, chunk=20)
        result = ble.decode_answer("Test", body)
        self.assertEqual(result["echo"], long_name)
        self.assertEqual(len(result["pad"]), 500)
        sent = [c for c, _ in shelly.writes]
        self.assertEqual(sent[0], ble.TX_CTL)                               # the length first, then only data
        self.assertTrue(all(c == ble.DATA for c in sent[1:]))
        self.assertTrue(all(len(d) <= 20 for c, d in shelly.writes if c == ble.DATA))

    def test_no_answer_is_an_error_with_a_hint(self):
        with self.assertRaises(ble.BleError) as ctx:
            self.run_exchange(FakeShelly(lambda r: {}, silent=True), ble.encode_request("X"), timeout=0.2)
        self.assertIn("no answer", str(ctx.exception))

    def test_an_answer_that_stops_is_an_error(self):
        shelly = FakeShelly(lambda r: {"result": {"a": "b" * 50}})

        async def short_read(char):
            if char == ble.RX_CTL:
                return len(shelly.answer).to_bytes(4, "big")
            if shelly.sent >= 10:
                return b""
            shelly.sent += 10
            return shelly.answer[:10]
        shelly.read = short_read
        with self.assertRaises(ble.BleError) as ctx:
            self.run_exchange(shelly, ble.encode_request("X"), timeout=0.3)
        self.assertIn("stopped", str(ctx.exception))


class ProvisionTests(unittest.TestCase):
    def calls(self, statuses):
        log = []
        states = iter(statuses)

        def call(address, method, params=None):
            log.append((method, params))
            return {"restart_required": False} if method == "Wifi.SetConfig" else next(states)
        return log, call

    def test_the_wifi_is_set_and_the_address_returned_when_it_comes_up(self):
        log, call = self.calls([{"status": "connecting"}, {"status": "got ip", "sta_ip": "192.168.1.5"}])
        ip = ble.provision_wifi("AA", "Net", "secret", call=call, sleep=lambda s: None)
        self.assertEqual(ip, "192.168.1.5")
        self.assertEqual(log[0], ("Wifi.SetConfig", {"config": {"sta": {"ssid": "Net", "enable": True, "pass": "secret"}}}))
        self.assertEqual([m for m, _ in log], ["Wifi.SetConfig", "Wifi.GetStatus", "Wifi.GetStatus"])

    def test_an_open_network_sends_no_password(self):
        log, call = self.calls([{"status": "got ip", "sta_ip": "10.0.0.2"}])
        ble.provision_wifi("AA", "Open", call=call, sleep=lambda s: None)
        self.assertNotIn("pass", log[0][1]["config"]["sta"])

    def test_wait_zero_sets_the_wifi_and_asks_nothing(self):
        log, call = self.calls([])
        self.assertIsNone(ble.provision_wifi("AA", "Net", "x", wait=0, call=call))
        self.assertEqual([m for m, _ in log], ["Wifi.SetConfig"])

    def test_no_address_in_time_is_an_error_naming_ssid_and_password(self):
        log, call = self.calls([{"status": "disconnected"}] * 20)
        now = iter(range(0, 1000, 10))
        with self.assertRaises(ble.BleError) as ctx:
            ble.provision_wifi("AA", "Net", "x", wait=25, call=call, sleep=lambda s: None, clock=lambda: next(now))
        self.assertIn("password", str(ctx.exception))


class WithoutBleakTests(unittest.TestCase):
    def test_a_missing_bleak_gives_the_install_hint(self):
        with mock.patch.dict(sys.modules, {"bleak": None}):
            with self.assertRaises(ble.BleError) as ctx:
                ble._bleak()
        self.assertIn("pip install bleak", str(ctx.exception))


class CommandTests(unittest.TestCase):
    def run_cmd(self, *argv):
        args = ota.build_parser().parse_args(["ble", *argv])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            args.func(args)
        return out.getvalue()

    def test_wifi_with_a_dash_asks_for_the_password_and_never_prints_it(self):
        with mock.patch.object(ble, "provision_wifi", return_value="192.168.1.9") as prov, \
                mock.patch("getpass.getpass", return_value="hunter2"):
            text = self.run_cmd("wifi", "Net", "-", "-a", "AA")
        prov.assert_called_once()
        self.assertEqual(prov.call_args.args[:3], ("AA", "Net", "hunter2"))
        self.assertIn("192.168.1.9", text)
        self.assertNotIn("hunter2", text)

    def test_wrong_arguments_say_what_is_needed(self):
        for argv in (("info", "x"), ("call",), ("wifi",), ("wifi", "a", "b", "c")):
            with self.assertRaises(builder.OtaError, msg=argv):
                self.run_cmd(*argv, "-a", "AA")

    def test_call_passes_the_json_params_and_prints_the_result(self):
        with mock.patch.object(ble, "rpc", return_value={"ok": True}) as rpc:
            text = self.run_cmd("call", "Zigbee.GetStatus", '{"x":1}', "-a", "AA")
        rpc.assert_called_once_with("AA", "Zigbee.GetStatus", {"x": 1}, timeout=15.0)
        self.assertEqual(json.loads(text), {"ok": True})

    def test_params_that_are_no_json_are_refused(self):
        with self.assertRaises(builder.OtaError):
            self.run_cmd("call", "X", "{oops", "-a", "AA")


if __name__ == "__main__":
    unittest.main()
