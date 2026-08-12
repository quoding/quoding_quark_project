#!/usr/bin/env python3
"""QUARK host helper — runs directly on the mini PC host (outside Docker).

Exposes two privileged operations that quark-api cannot perform from inside
its container: rebooting the host, and broadcasting Wake-on-LAN magic packets
onto the LAN (Docker's bridge NAT drops broadcast traffic, so this must run
with real LAN access).

Binds to the quark-internal Docker bridge gateway IP only — reachable from
quark-api's container and the host itself, never from the LAN/internet.
Requests must also carry a shared-secret bearer token (defense in depth).
"""
from __future__ import annotations

import json
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BIND_PORT = 8999
TOKEN_PATH = Path("/home/muya98/quoding/secrets/host_helper_token")
TOKEN = TOKEN_PATH.read_text().strip()


def _detect_bind_host() -> str:
    """Look up quark-internal's current gateway IP via the Docker CLI.

    User-defined bridge networks get a fresh subnet whenever they're
    recreated (e.g. `docker compose down && up`), so the gateway IP isn't
    stable across the network's lifetime. Resolving it at startup instead of
    hardcoding it keeps this helper reachable from quark-api regardless.
    """
    try:
        result = subprocess.run(
            [
                "docker", "network", "inspect", "quoding_quark-internal",
                "--format", "{{(index .IPAM.Config 0).Gateway}}",
            ],
            capture_output=True, text=True, timeout=5, check=True,
        )
        gateway = result.stdout.strip()
        if gateway:
            return gateway
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "172.18.0.1"


BIND_HOST = _detect_bind_host()


def send_magic_packet(mac: str) -> None:
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError(f"invalid MAC address: {mac!r}")
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, ("255.255.255.255", 9))


class Handler(BaseHTTPRequestHandler):
    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def _reply(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if not self._authorized():
            self._reply(401, {"error": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""

        if self.path == "/reboot":
            subprocess.Popen(["sudo", "/usr/sbin/reboot"])
            self._reply(200, {"ok": True})
            return

        if self.path == "/wol":
            try:
                mac = json.loads(raw or b"{}").get("mac", "")
                send_magic_packet(mac)
            except (ValueError, json.JSONDecodeError) as exc:
                self._reply(400, {"error": str(exc)})
                return
            self._reply(200, {"ok": True})
            return

        self._reply(404, {"error": "not_found"})

    def log_message(self, fmt: str, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler).serve_forever()
