import subprocess
from typing import Optional

import pygame

from ..addons.installer import InstallResult, install_from_url
from ..config import ConfigManager
from ..core.backlight import Backlight
from ..core.events import (
    BACK_TO_MENU_PRESSED,
    BACK_TO_MENU_RELEASED,
    BRIGHTNESS_DOWN_PRESSED,
    BRIGHTNESS_DOWN_RELEASED,
    BRIGHTNESS_UP_PRESSED,
    BRIGHTNESS_UP_RELEASED,
    DEMO_TOGGLE_PRESSED,
    DEMO_TOGGLE_RELEASED,
    INSTALL_PRESSED,
    INSTALL_RELEASED,
)
from ..core.utils import FontFamily, load_font
from ..telemetry.mode import TelemetryMode
from ..widgets.base.button import Button, ButtonGroup
from ..widgets.base.colors import Color
from ..widgets.base.container import Container
from ..widgets.base.label import Label
from .state import State
from .state_manager import StateManager


class SettingsState(State):
    STEP_PERCENT = 10

    def __init__(self, state_manager):
        super().__init__()
        self.state_manager: StateManager = state_manager

        self._mode: Optional[TelemetryMode] = None

        self.title_label = Label(
            text="System settings",
            font=load_font(size=64, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.BLUE.rgb(),
            pos=(48, 38),
            center=False,
        )

        self.back_button = Button(
            rect=(pygame.display.get_surface().get_width() - 90, 20, 70, 70),
            text="x",
            text_visible=False,
            text_gap=0,
            event_type_pressed=BACK_TO_MENU_PRESSED,
            event_type_released=BACK_TO_MENU_RELEASED,
            font=load_font(50, name=FontFamily.PIXEL_TYPE),
            antialias=True,
        )
        self.nav_group = ButtonGroup()
        self.nav_group.add(self.back_button)

        surf = pygame.display.get_surface()
        center_x = surf.get_width() // 2
        y = 280

        self.brightness_label = Label(
            text="Brightness",
            font=load_font(size=44, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(320, 220),
            center=True,
        )

        self.minus_button = Button(
            rect=(center_x - 180, y, 80, 80),
            text="-",
            icon="\ue15b",
            icon_size=46,
            icon_position="center",
            text_visible=False,
            event_type_pressed=BRIGHTNESS_DOWN_PRESSED,
            event_type_released=BRIGHTNESS_DOWN_RELEASED,
            font=load_font(76, name=FontFamily.PIXEL_TYPE),
            text_color=Color.WHITE.rgb(),
            antialias=True,
        )
        self.plus_button = Button(
            rect=(center_x + 60, y, 80, 80),
            text="+",
            icon="\ue145",
            icon_size=46,
            icon_position="center",
            text_visible=False,
            event_type_pressed=BRIGHTNESS_UP_PRESSED,
            event_type_released=BRIGHTNESS_UP_RELEASED,
            font=load_font(76, name=FontFamily.PIXEL_TYPE),
            text_color=Color.WHITE.rgb(),
            antialias=True,
        )

        self.brightness_group = ButtonGroup()
        self.brightness_group.add(self.minus_button)
        self.brightness_group.add(self.plus_button)

        self.brightness_container = Container(is_visible=True)
        self.brightness_container.add(self.brightness_label, self.brightness_group)

        self._backlight = Backlight()
        self._brightness_percent: Optional[int] = None
        self._error: Optional[str] = None

        # ---- Telemetry UI (Demo toggle) ----

        # baseline Y for brightness was 280; place telemetry controls below it
        self.telemetry_label = Label(
            text="Telemetry",
            font=load_font(size=44, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(100, 450),
            center=False,
        )

        self.demo_button = Button(
            rect=(center_x - 80, 420, 240, 80),
            text="",
            icon=None,
            text_visible=True,
            event_type_pressed=DEMO_TOGGLE_PRESSED,
            event_type_released=DEMO_TOGGLE_RELEASED,
            font=load_font(38, name=FontFamily.PIXEL_TYPE),
            text_color=Color.WHITE.rgb(),
            antialias=True,
        )

        self.telemetry_group = ButtonGroup()
        self.telemetry_group.add(self.demo_button)

        # cached state
        self._demo_enabled: Optional[bool] = None

        # --- Proxy: Install from URL ---
        self.proxy_label = Label(
            text="Proxy (granturismo)",
            font=load_font(size=44, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(100, 136),
            center=False,
        )

        self.install_button = Button(
            rect=(center_x - 80, 110, 340, 80),
            text="Install from URL",
            text_visible=True,
            font=load_font(36, name=FontFamily.PIXEL_TYPE),
            antialias=True,
            event_type_pressed=INSTALL_PRESSED,
            event_type_released=INSTALL_RELEASED,
        )

        self.proxy_group = ButtonGroup()
        self.proxy_group.add(self.install_button)

        # status text
        self._proxy_status: Optional[str] = None

    def enter(self):
        super().enter()

        if self._backlight.available():
            cur = self._backlight.get_percent()
            if cur is not None:
                self._brightness_percent = cur
                self._error = None
            else:
                self._brightness_percent = None
                self._error = "Failed to read backlight value."
        else:
            self._brightness_percent = None
            self._error = "No backlight device found."

        # Container visibility is driven by availability
        self.brightness_container.is_visible = self._backlight.available()

        # Load demo mode from config and refresh button
        cfg = ConfigManager.get_config()
        self._mode = TelemetryMode(cfg.telemetry_mode)
        self._refresh_demo_button()

        ip = cfg.playstation_ip or ""
        if ip:
            out = subprocess.check_output(
                ["/bin/systemctl", "is-active", f"simdash-proxy@{ip}.service"],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
            self._proxy_status = f"Proxy status: {out}"
        else:
            self._proxy_status = "Proxy status: PS5 IP not set"

    def _refresh_demo_button(self):
        if self._mode is TelemetryMode.DEMO:
            self.demo_button.text = "Demo"
        else:
            self.demo_button.text = "UDP"

    def handle_event(self, event):
        self.nav_group.handle_event(event)
        self.brightness_container.handle_event(event)
        self.telemetry_group.handle_event(event)

        if event.type == BACK_TO_MENU_RELEASED:
            return self.on_back_released(event)

        if self.brightness_container.is_visible and self._backlight.available():
            if event.type == BRIGHTNESS_DOWN_RELEASED:
                self._adjust_brightness(-self.STEP_PERCENT)
            elif event.type == BRIGHTNESS_UP_RELEASED:
                self._adjust_brightness(+self.STEP_PERCENT)
        # Toggle demo on release
        if event.type == DEMO_TOGGLE_RELEASED:
            self._mode = (
                TelemetryMode.UDP
                if self._mode is TelemetryMode.DEMO
                else TelemetryMode.DEMO
            )
            ConfigManager.set_telemetry_mode(self._mode)
            self._refresh_demo_button()

        self.proxy_group.handle_event(event)

        if event.type == pygame.MOUSEBUTTONUP:
            if self.install_button.rect.collidepoint(event.pos):
                # go to EnterURLState and run installer on submit
                def _submit(url: str, sha: Optional[str]):
                    cfg = ConfigManager.get_config()
                    if not cfg.playstation_ip:
                        raise RuntimeError("Set PS5 IP in Network settings first.")
                    res: InstallResult = install_from_url(
                        url, cfg.playstation_ip, sha256=sha
                    )
                    if not res.ok:
                        raise RuntimeError(res.message)

                from .enter_url_state import EnterURLState

                self.state_manager.change_state(
                    EnterURLState(self.state_manager, "Install Proxy from URL", _submit)
                )

    def _adjust_brightness(self, delta_percent: int):
        if self._brightness_percent is None:
            cur = self._backlight.get_percent()
            if cur is None:
                self._error = "Backlight not available."
                return
            self._brightness_percent = cur

        target = max(10, min(100, self._brightness_percent + delta_percent))
        if self._backlight.set_percent(target):
            self._brightness_percent = target
            self._error = None
        else:
            self._error = "Failed to write brightness."

    def draw(self, surface):
        surface.fill(Color.BLACK.rgb())

        self.title_label.draw(surface)
        self.nav_group.draw(surface)

        self.brightness_container.draw(surface)

        # telemetry label + button
        self.telemetry_label.draw(surface)
        self.telemetry_group.draw(surface)

        if (
            self.brightness_container.is_visible
            and self._brightness_percent is not None
        ):
            value_x = (self.minus_button.rect.right + self.plus_button.rect.left) // 2
            center_y = self.minus_button.rect.centery
            val_font = load_font(size=46, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            pct_txt = val_font.render(
                f"{self._brightness_percent} %", False, Color.WHITE.rgb()
            )
            pct_rect = pct_txt.get_rect(center=(value_x, center_y))
            surface.blit(pct_txt, pct_rect.topleft)

        # Error text:
        # - If visible: show it UNDER the buttons
        # - If hidden: still show the message where the controls would be
        if self._error:
            err_font = load_font(size=46, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            err_txt = err_font.render(self._error, False, Color.DARK_RED.rgb())

            # Place below the buttons (or where they'd be)
            if self.brightness_container.is_visible:
                y_under = (
                    max(self.minus_button.rect.bottom, self.plus_button.rect.bottom)
                    + 24
                )
                value_x = (
                    self.minus_button.rect.right + self.plus_button.rect.left
                ) // 2
                err_rect = err_txt.get_rect(midtop=(value_x, y_under))
            else:
                # Fallback position if controls are hidden
                surf = pygame.display.get_surface()
                value_x = surf.get_width() // 2
                y_under = 300  # roughly where controls would start
                err_rect = err_txt.get_rect(midtop=(value_x, y_under))
            surface.blit(err_txt, err_rect.topleft)

        # --- Proxy controls ---
        self.proxy_label.draw(surface)
        self.proxy_group.draw(surface)

        if self._proxy_status:
            stat_font = load_font(size=32, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            stat_txt = stat_font.render(self._proxy_status, False, Color.WHITE.rgb())
            center_x = pygame.display.get_surface().get_width() // 2
            stat_rect = stat_txt.get_rect(
                midtop=(center_x + 60, self.install_button.rect.bottom + 12)
            )
            surface.blit(stat_txt, stat_rect.topleft)

    def on_back_released(self, event):
        from ..states.main_menu_state import MainMenuState

        self.state_manager.change_state(MainMenuState(self.state_manager))

    def update(self, dt):
        super().update(dt)

        # Keep container visibility in sync with hardware state
        avail = self._backlight.available()
        if avail:
            cur = self._backlight.get_percent()
            if cur is not None:
                self._brightness_percent = cur
        self.brightness_container.is_visible = avail
