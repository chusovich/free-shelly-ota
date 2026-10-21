"""Minimal Shelly RPC client over HTTP, with optional digest authentication (RFC 7616)."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .builder import OtaError

_PARAM = re.compile(r'(\w+)=(?:"([^"]*)"|([^,\s]+))')


class RpcError(OtaError):
    """The device answered but refused: an HTTP error status or an RPC "error" object.

    `code` and `device_message` are what the device reported (Shelly sends {"code": -109, "message": "..."}).
    The code alone is not enough to tell refusals apart: -109 is used for several of them.
    """

    def __init__(self, message: str, *, status: int | None = None, code: int | None = None,
                 device_message: str = "", method: str = ""):
        super().__init__(message)
        self.status = status
        self.code = code
        self.device_message = device_message
        self.method = method


class DeviceUnreachable(OtaError):
    """No answer from the device at all (wrong address, powered off, or no longer running the Shelly firmware)."""


def _target(url: str) -> str:
    """The part of a request URL that is worth showing: the RPC method, without the query (it can hold a long URL)."""
    path = urllib.parse.urlsplit(url).path
    return path[len("/rpc/"):] if path.startswith("/rpc/") else (path or url)


def _split_error_body(raw: str) -> tuple[int | None, str]:
    """(code, message) of a Shelly error body {"code": ..., "message": ...}; (None, raw text) for anything else."""
    try:
        obj = json.loads(raw)
    except ValueError:
        return None, raw
    if isinstance(obj, dict) and isinstance(obj.get("message"), str):
        code = obj.get("code")
        return (code if isinstance(code, int) else None), obj["message"]
    return None, raw


def _digest_header(challenge: str, method: str, url: str, user: str, password: str) -> str:
    params = {k: (q or u) for k, q, u in _PARAM.findall(challenge)}
    algo = params.get("algorithm", "MD5").upper()
    hash_fn = {"SHA-256": hashlib.sha256, "MD5": hashlib.md5}.get(algo)
    if hash_fn is None:
        raise OtaError(f"Unsupported digest algorithm {algo!r}.")

    def h(text: str) -> str:
        return hash_fn(text.encode()).hexdigest()

    parts = urllib.parse.urlsplit(url)
    uri = parts.path + (f"?{parts.query}" if parts.query else "")
    nc, cnonce = "00000001", os.urandom(8).hex()
    ha1 = h(f"{user}:{params['realm']}:{password}")
    ha2 = h(f"{method}:{uri}")
    response = h(f"{ha1}:{params['nonce']}:{nc}:{cnonce}:auth:{ha2}")
    fields = [f'username="{user}"', f'realm="{params["realm"]}"', f'nonce="{params["nonce"]}"', f'uri="{uri}"',
              f"algorithm={algo}", f'response="{response}"', "qop=auth", f"nc={nc}", f'cnonce="{cnonce}"']
    if "opaque" in params:
        fields.append(f'opaque="{params["opaque"]}"')
    return "Digest " + ", ".join(fields)


def request(url: str, *, data: bytes | None = None, user: str | None = None, password: str | None = None,
            timeout: float = 10) -> bytes:
    """GET (or POST with data) and return the body. Answers a 401 digest challenge if credentials are given."""
    method = "POST" if data is not None else "GET"
    headers = {"Content-Type": "application/json"} if data is not None else {}
    try:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers),
                                        timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            challenge = e.headers.get("WWW-Authenticate", "")
            if e.code != 401 or not challenge.lower().startswith("digest"):
                raise
            if not (user and password):
                raise OtaError("The device requires a password: use --user and --password.") from e
            headers["Authorization"] = _digest_header(challenge, method, url, user, password)
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers),
                                        timeout=timeout) as resp:
                return resp.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read(300).decode(errors="replace").strip()
        except OSError:
            detail = ""
        code, message = _split_error_body(detail) if detail else (None, "")
        text = f"HTTP {e.code} from {_target(url)}" + (f": {message}" if message else "")
        if code is not None:
            text += f" (code {code})"
        raise RpcError(text, status=e.code, code=code, device_message=message, method=_target(url)) from e
    except http.client.HTTPException as e:   # BadStatusLine, IncompleteRead, ...: these are not OSErrors
        raise OtaError(f"Unexpected answer from {urllib.parse.urlsplit(url).netloc} ({_target(url)}): {e!r}") from e
    except OSError as e:
        raise DeviceUnreachable(f"No answer from {urllib.parse.urlsplit(url).netloc} ({_target(url)}): {e}") from e


def call(addr: str, method: str, params: dict | None = None, **auth) -> dict:
    """Call an RPC method (POST /rpc) and return its result."""
    body = json.dumps({"id": 1, "method": method, "params": params or {}}).encode()
    try:
        reply = json.loads(request(f"http://{addr}/rpc", data=body, **auth))
    except ValueError as e:
        raise OtaError(f"{method}: the device did not answer with JSON.") from e
    if not isinstance(reply, dict):
        raise OtaError(f"{method}: unexpected answer from the device.")
    if "error" in reply:
        err = reply["error"]
        code = err.get("code") if isinstance(err, dict) and isinstance(err.get("code"), int) else None
        message = err.get("message") if isinstance(err, dict) else None
        message = message if isinstance(message, str) else str(err)
        raise RpcError(f"{method} failed: {message}" + (f" (code {code})" if code is not None else ""),
                       code=code, device_message=message, method=method)
    return reply.get("result", {})
