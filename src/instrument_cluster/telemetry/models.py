from pydantic import BaseModel


class TelemetryFrame(BaseModel):
    received_time: float
    car_speed: float = 0.0
    engine_rpm: int = 0
    current_gear: int = 0
    throttle: float = 0.0
    brake: float = 0.0
    steering: float = 0.0

    lap_count: int | None = 0
