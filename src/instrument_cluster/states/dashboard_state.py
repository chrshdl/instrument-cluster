from typing import Optional

from ..config import ConfigManager
from ..core.events import BACK_TO_MENU_RELEASED
from ..core.logger import Logger
from ..states.state_manager import StateManager
from ..telemetry.mode import TelemetryMode
from ..telemetry.source import TelemetrySource
from ..widgets.base.colors import Color
from ..widgets.base.widget_group import WidgetGroup
from ..widgets.button_bar import ButtonBar
from ..widgets.gear import GearLabel
from ..widgets.graphical_rpm import GraphicalRPM
from ..widgets.lap import EstimatedLap
from ..widgets.shift_lights import ShiftLights
from ..widgets.speed import SpeedLabel
from .state import State


class DashboardState(State):
    def __init__(
        self, state_manager: StateManager, telemetry: Optional[TelemetrySource] = None
    ):
        super().__init__(state_manager)
        self.logger = Logger(__class__.__name__).get()
        # receive-only telemetry source (defaults to Demo if not provided)
        if telemetry is None:
            cfg = ConfigManager.get_config()
            mode = TelemetryMode(cfg.telemetry_mode)
            self.telemetry = TelemetrySource(
                mode=mode,
                host=cfg.udp_host,
                port=cfg.udp_port,
            )
        else:
            self.telemetry = telemetry

        self.packet = None

        # Create ECU-side model for learning curves
        shift_lights = ShiftLights(
            anchor=lambda size: (size[0] // 2, size[1] // 16),
            step_thresholds=[0.62, 0.78, 0.92, 0.985],
            color_thresholds=(0.5, 0.8),
        )
        # la widget tree
        self.widgets = WidgetGroup(
            [
                GraphicalRPM(
                    alert_min=5500,
                    alert_max=9000,
                    max_rpm=9000,
                    redline_rpm=7500,
                ),
                GearLabel(
                    anchor=lambda wh: (wh[0] // 2, wh[1] // 2 + 78),
                ),
                SpeedLabel(anchor=lambda wh: (wh[0] // 2, wh[1] // 5)),
                ButtonBar(
                    on_events={BACK_TO_MENU_RELEASED: self.on_back},
                ),
                EstimatedLap(
                    anchor=lambda size: (size[0] - 150, size[1] // 2 + 160),
                    size=(260, 120),
                    sample_hz=10.0,
                    grid_m=0.25,
                ),
            ]
        )
        # self.widgets.add(shift_lights)

    def enter(self):
        super().enter()
        # start receive-only source (Demo by default; UDP if configured)
        self.telemetry.start()
        self.widgets.enter()

    def exit(self):
        try:
            self.telemetry.stop()
        except Exception:
            pass
        self.widgets.exit()
        super().exit()

    def handle_event(self, event):
        self.widgets.handle_event(event)

    def update(self, dt):
        super().update(dt)
        try:
            self.packet = self.telemetry.latest()
            if self.packet:
                self.widgets.update(self.packet, dt)
        except Exception as e:
            self.logger.info({"telemetry error": str(e)})

    def draw(self, surface):
        surface.fill(Color.BLACK.rgb())
        self.widgets.draw(surface)

    def on_back(self, event=None):
        from ..states.main_menu_state import MainMenuState

        self.state_manager.change_state(MainMenuState(self.state_manager))
