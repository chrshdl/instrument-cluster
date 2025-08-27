from __future__ import annotations

import pygame

from ..addons.installer import (
    DEFAULT_TARBALL_URL,
    InstallResult,
    install_from_url,
    service_status,
)
from ..config import ConfigManager
from ..core.events import (
    BACK_TO_MENU_PRESSED,
    BACK_TO_MENU_RELEASED,
    INSTALL_PRESSED,
    INSTALL_RELEASED,
)
from ..core.utils import FontFamily, load_font
from ..telemetry.mode import TelemetryMode
from ..widgets.base.button import Button, ButtonGroup
from ..widgets.base.colors import Color
from ..widgets.base.label import Label
from ..widgets.base.textfield import TextField
from .state import State


class EnterURLState(State):
    """
    Enter the granturismo tarball URL and install it.

    - TextField prefilled with DEFAULT_TARBALL_URL
    - 'Download' and 'Cancel' buttons
    - On Download:
        * downloads/extracts tarball into /opt/granturismo
        * installer writes /etc/default/simdash-proxy and enables/starts the unit
          (on macOS, service control is 'unavailable' but install still succeeds)
        * telemetry mode switched to UDP, then return to Settings
    """

    def __init__(self, state_manager):
        super().__init__(state_manager)
        self._error: str | None = None
        self._status: str | None = None

        surf = pygame.display.get_surface()
        self._w, self._h = surf.get_width(), surf.get_height()

        self.title_label = Label(
            text="Install Proxy Tarball",
            font=load_font(size=64, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.BLUE.rgb(),
            pos=(48, 38),
            center=False,
        )

        # Text input
        self.textfield = TextField(
            text=DEFAULT_TARBALL_URL,
            font=load_font(size=24, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(self._w // 2 - 420, self._h // 4),
            width=840,
            height=60,
            border_color=Color.GREY.rgb(),
        )

        self.download_button = Button(
            rect=(self._w // 2 - 220, self._h - 120, 200, 70),
            text="Download",
            text_visible=True,
            font=load_font(40, name=FontFamily.PIXEL_TYPE),
            antialias=True,
            event_type_pressed=INSTALL_PRESSED,
            event_type_released=INSTALL_RELEASED,
        )
        self.cancel_button = Button(
            rect=(self._w // 2 + 40, self._h - 120, 180, 70),
            text="Cancel",
            text_visible=True,
            font=load_font(40, name=FontFamily.PIXEL_TYPE),
            antialias=True,
            event_type_pressed=BACK_TO_MENU_PRESSED,
            event_type_released=BACK_TO_MENU_RELEASED,
        )

        self.btns = ButtonGroup()
        self.btns.add(self.download_button)
        self.btns.add(self.cancel_button)

    def handle_event(self, event) -> bool:
        self.btns.handle_event(event)
        self.textfield.handle_event(event)

        if event.type == BACK_TO_MENU_RELEASED:
            from .settings_state import SettingsState

            self.state_manager.change_state(SettingsState(self.state_manager))
            return True

        # Download clicked (from button event) OR keyboard Enter
        if event.type == INSTALL_RELEASED:
            self._perform_install()
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._perform_install()
            return True

        # Also accept direct mouse-up in case your ButtonGroup doesn't consume it
        if event.type == pygame.MOUSEBUTTONUP:
            if self.download_button.rect.collidepoint(event.pos):
                self._perform_install()
                return True

        return False

    def _perform_install(self):
        # Read URL and PS IP from config
        url = (self.textfield.text or "").strip() or DEFAULT_TARBALL_URL
        cfg = ConfigManager.get_config()
        ps_ip = (getattr(cfg, "playstation_ip", "") or "").strip()
        if not ps_ip:
            self._error = "PS5 IP not set. Enter it first."
            return

        try:
            self._status = "Downloading and installing…"
            res: InstallResult = install_from_url(
                url=url,
                ps_ip=ps_ip,
                sha256=None,
                jsonl_output="udp://127.0.0.1:5600",
            )
        except Exception as e:
            self._error = f"Install failed: {e}"
            self._status = None
            return

        if not res.ok:
            self._error = res.message or "Install failed."
            self._status = None
            return

        # Success -> set mode to UDP and go back to Settings
        ConfigManager.set_telemetry_mode(TelemetryMode.UDP)
        self._status = f"Installed. Proxy status: {service_status()}"

        from .settings_state import SettingsState  # local import avoids cycles

        self.state_manager.change_state(SettingsState(self.state_manager))

    def update(self, dt):
        super().update(dt)
        self.textfield.update(dt)

    def draw(self, surface):
        surface.fill(Color.BLACK.rgb())
        self.title_label.draw(surface)

        self.textfield.draw(surface)
        self.btns.draw(surface)

        if self._status:
            s_font = load_font(size=28, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            s_txt = s_font.render(self._status, False, Color.WHITE.rgb())
            s_rect = s_txt.get_rect(
                center=(self._w // 2, self.textfield.rect.bottom + 40)
            )
            surface.blit(s_txt, s_rect.topleft)

        if self._error:
            e_font = load_font(size=28, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            e_txt = e_font.render(self._error, False, Color.DARK_RED.rgb())
            e_rect = e_txt.get_rect(
                center=(self._w // 2, self.textfield.rect.bottom + 80)
            )
            surface.blit(e_txt, e_rect.topleft)
