#!/usr/bin/env python3
"""
Granturismo → gt7-simdash proxy (receive from PS5, forward plain JSON to localhost UDP).
- Runs as a separate process.
- Requires third-party 'granturismo' package (not bundled with simdash).
- Sends one JSON object per UDP packet using the gt7-simdash/v1 schema.
"""

import argparse
import json
import signal
import socket
import sys
import time
from typing import Any

# Import the third-party feed (installed by the user)
try:
    from granturismo.intake.feed import Feed  # type: ignore
except Exception as e:
    print(
        "ERROR: 'granturismo' package not installed or import failed:",
        e,
        file=sys.stderr,
    )
    sys.exit(2)

RUN = True


def _sigterm(signum, frame):
    global RUN
    RUN = False


signal.signal(signal.SIGINT, _sigterm)
signal.signal(signal.SIGTERM, _sigterm)


def g(obj: Any, name: str, default: Any = 0):
    """Safe getattr with default and None handling."""
    val = getattr(obj, name, None)
    return default if val is None else val


def map_packet(pkt: Any) -> dict:
    """
    Map an arbitrary granturismo Packet to gt7-simdash/v1 fields (SI units).
    We keep this tolerant since different libs name fields differently.
    """
    car_speed = float(g(pkt, "car_speed", g(pkt, "speed_mps", g(pkt, "speed", 0.0))))
    engine_rpm = int(g(pkt, "engine_rpm", g(pkt, "rpm", 0)))
    gear = int(g(pkt, "gear", 0))
    throttle = float(g(pkt, "throttle", g(pkt, "accelerator", 0.0)))
    brake = float(g(pkt, "brake", 0.0))

    return {
        "received_time": time.time_ns(),
        "car_speed": car_speed,
        "engine_rpm": engine_rpm,
        "gear": gear,
        "throttle": throttle,
        "brake": brake,
    }


def main():
    ap = argparse.ArgumentParser(description="Granturismo → gt7-simdash UDP proxy")
    ap.add_argument(
        "--ps5-ip", required=True, help="PlayStation 5 IP shown in GT7 settings"
    )
    ap.add_argument("--out-host", default="127.0.0.1")
    ap.add_argument("--out-port", type=int, default=5600)
    ap.add_argument(
        "--max-fps", type=float, default=60.0, help="Max send rate (frames/sec)"
    )
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.out_host, args.out_port)

    # Construct the Feed (signature tolerant)
    try:
        try:
            feed = Feed(args.ps5_ip)  # common signature
        except TypeError:
            feed = Feed(ip=args.ps5_ip)  # alternate signature
    except Exception as e:
        print("ERROR: could not create granturismo Feed:", e, file=sys.stderr)
        return 2

    print(f"[proxy] sending to udp://{args.out_host}:{args.out_port} (CTRL+C to stop)")
    last_send = 0.0
    min_dt = 1.0 / max(1.0, args.max_fps)

    try:
        while RUN:
            pkt = None
            # Non-blocking if available
            try:
                pkt = feed.get_nowait()  # type: ignore[attr-defined]
            except AttributeError:
                # Fallback to blocking with a small timeout if feed implements it
                try:
                    pkt = feed.get(timeout=0.05)  # type: ignore[attr-defined]
                except Exception:
                    pkt = None
            except Exception:
                pkt = None

            now = time.perf_counter()
            if pkt is not None and (now - last_send) >= min_dt:
                frame = map_packet(pkt)
                try:
                    sock.sendto(json.dumps(frame).encode("utf-8"), dest)
                except Exception:
                    pass
                last_send = now
            else:
                # avoid spinning
                time.sleep(0.002)
    finally:
        try:
            if hasattr(feed, "close"):
                feed.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
