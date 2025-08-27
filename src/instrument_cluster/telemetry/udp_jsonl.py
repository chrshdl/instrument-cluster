import json
import socket
import threading
import time
from typing import Optional, Tuple

from .models import TelemetryFrame


class UdpJsonlReader:
    def __init__(self, host: str = "127.0.0.1", port: int = 5600, bufsize: int = 4096):
        self.addr: Tuple[str, int] = (host, port)
        self.bufsize = bufsize
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._latest: TelemetryFrame = TelemetryFrame(received_time=0, car_speed=0.0)

    def start(self) -> None:
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(self.addr)  # receive-only on localhost
        self._sock.setblocking(False)
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        assert self._sock is not None
        while self._running:
            try:
                data, _ = self._sock.recvfrom(self.bufsize)
            except BlockingIOError:
                time.sleep(0.002)
                continue
            except OSError:
                break
            try:
                obj = json.loads(data.decode("utf-8"))
                self._latest = TelemetryFrame(**obj)
            except Exception as e:
                print(str(e))

    def latest(self) -> TelemetryFrame:
        return self._latest

    def stop(self) -> None:
        self._running = False
        try:
            if self._sock:
                self._sock.close()
        finally:
            self._sock = None
