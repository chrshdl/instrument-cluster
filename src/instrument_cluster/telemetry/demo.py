import math
import time

from .models import TelemetryFrame


class DemoReader:
    def __init__(self):
        self._t0 = time.perf_counter()

    def start(self) -> None:
        pass

    def latest(self) -> TelemetryFrame:
        t = time.perf_counter() - self._t0
        speed = max(0.0, 35.0 + 15.0 * math.sin(2 * math.pi * (t / 6.0)))
        rpm = int(6500 + 2000 * math.sin(2 * math.pi * (t / 3.0)))
        gear = 3 + int((t // 7) % 4)
        return TelemetryFrame(
            received_time=time.time_ns(),
            car_speed=speed,
            engine_rpm=rpm,
            current_gear=gear,
            throttle=max(0.0, math.sin(t) * 0.5 + 0.5),
            brake=max(0.0, math.sin(t + 1.8) * -0.4),
            steering=math.sin(t / 2.0) * 0.3,
            lap=1 + int(t // 90),
        )

    def stop(self) -> None:
        pass
