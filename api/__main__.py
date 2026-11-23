"""Run EquityPilot on this computer only (loopback), for both IPv4 and IPv6:  python -m api [--port 8000]

Why both: browsers on Windows resolve "localhost" to the IPv6 address ::1 first. When the server listens only on
127.0.0.1, every new connection waits for the IPv6 attempt to fail (measured: ~0.21 s per connection) before falling
back to IPv4. Listening on both loopback addresses removes that wait without exposing the server to the network.
`python -m uvicorn api.main:app` still works as before (IPv4 only).
"""
from __future__ import annotations

import argparse
import socket


def loopback_sockets(port: int) -> list[socket.socket]:
    socks = []
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        s = socket.socket(family, socket.SOCK_STREAM)
        try:
            if family == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((host, port))
        except OSError as exc:
            s.close()
            if family == socket.AF_INET:
                raise SystemExit(f"Port {port} is not available on 127.0.0.1 ({exc}). Is EquityPilot already running?")
            print(f"Note: IPv6 loopback (::1) unavailable ({exc}); serving on 127.0.0.1 only.")
            continue
        s.set_inheritable(True)
        socks.append(s)
    return socks


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m api", description="Start the EquityPilot AI server on this computer.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--log-level", default="warning")
    args = ap.parse_args()
    import uvicorn
    socks = loopback_sockets(args.port)
    uvicorn.Server(uvicorn.Config("api.main:app", log_level=args.log_level)).run(sockets=socks)


if __name__ == "__main__":
    main()
