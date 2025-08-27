from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, Optional

import pygame

from ..config import ConfigManager
from ..core.events import (
    BACK_TO_MENU_PRESSED,
    BACK_TO_MENU_RELEASED,
    ENTER_IP_DEL_BUTTON_PRESSED,
    ENTER_IP_DEL_BUTTON_RELEASED,
    ENTER_IP_KEYPAD_BUTTON_PRESSED,
    ENTER_IP_KEYPAD_BUTTON_RELEASED,
    ENTER_IP_OK_BUTTON_PRESSED,
    ENTER_IP_OK_BUTTON_RELEASED,
)
from ..core.ipv4 import get_ip_prefill
from ..core.utils import FontFamily, load_font
from ..widgets.base.button import Button, ButtonGroup
from ..widgets.base.colors import Color
from ..widgets.base.label import Label
from ..widgets.base.textfield import TextField
from .enter_url_state import EnterURLState
from .settings_state import SettingsState
from .state import State

if TYPE_CHECKING:
    pass

BUTTONS_PER_ROW = 3
BUTTON_DIMENSIONS = (114, 74)
BUTTON_MARGIN = 7
BUTTON_GRID_OFFSET = (
    BUTTON_DIMENSIONS[0] + BUTTON_MARGIN,
    BUTTON_DIMENSIONS[1] + BUTTON_MARGIN,
)
NUMPAD_OFFSET = (62, 228)

RECENT_BUTTONS_PER_ROW = 1
RECENT_BUTTONS_DIMENSIONS = (260, 70)
RECENT_BUTTONS_MARGIN = 7
RECENT_BUTTONS_GRID_OFFSET = (
    RECENT_BUTTONS_DIMENSIONS[0] + RECENT_BUTTONS_MARGIN,
    RECENT_BUTTONS_DIMENSIONS[1] + RECENT_BUTTONS_MARGIN,
)
RECENT_BUTTONS_OFFSET = (680, 210)


class EnterIPState(State):
    def __init__(
        self,
        state_manager=None,
        recent_connected: list[str] | None = None,
        on_submit: Optional[Callable[[str], None]] = None,  # kept for compatibility
    ):
        super().__init__()
        self.state_manager = state_manager
        self._on_submit = on_submit
        recent_connected = recent_connected or []
        self.button_group: ButtonGroup = ButtonGroup()
        labels = list("123456789#0.")

        back_button = Button(
            rect=(pygame.display.get_surface().get_width() - 90, 20, 70, 70),
            text="x",
            text_visible=False,
            text_gap=0,
            event_type_pressed=BACK_TO_MENU_PRESSED,
            event_type_released=BACK_TO_MENU_RELEASED,
            font=load_font(50, name=FontFamily.PIXEL_TYPE),
            antialias=True,
        )
        del_button = Button(
            rect=(416, 142, 100, 76),
            text="<",
            text_visible=False,
            text_gap=0,
            event_type_pressed=ENTER_IP_DEL_BUTTON_PRESSED,
            event_type_released=ENTER_IP_DEL_BUTTON_RELEASED,
            font=load_font(36, name=FontFamily.PIXEL_TYPE),
            text_color=Color.LIGHT_RED.rgb(),
            antialias=True,
            icon="\ue14a",
            icon_size=46,
            icon_position="center",
            icon_gap=0,
            padding=(0, 0),
            icon_cell_width=36,
        )

        ok_button = Button(
            rect=(424, 400, 100, 144),
            text="OK",
            text_visible=False,
            text_gap=0,
            event_type_pressed=ENTER_IP_OK_BUTTON_PRESSED,
            event_type_released=ENTER_IP_OK_BUTTON_RELEASED,
            font=load_font(50, name=FontFamily.PIXEL_TYPE),
            text_color=Color.GREEN.rgb(),
            antialias=True,
            icon="\ue5ca",
            icon_size=46,
            icon_position="center",
            icon_gap=0,
            padding=(0, 0),
            icon_cell_width=36,
        )

        self.button_group.extend(
            self._button_grid_generator(
                labels,
                BUTTONS_PER_ROW,
                BUTTON_GRID_OFFSET,
                NUMPAD_OFFSET,
                BUTTON_DIMENSIONS,
            )
        )

        self.button_group.extend(
            self._button_grid_generator(
                recent_connected[0:3],
                RECENT_BUTTONS_PER_ROW,
                RECENT_BUTTONS_GRID_OFFSET,
                RECENT_BUTTONS_OFFSET,
                RECENT_BUTTONS_DIMENSIONS,
            )
        )
        self.button_group.add(back_button)
        self.button_group.add(del_button)
        self.button_group.add(ok_button)

        self.border_thickness = 2
        self.border_radius = 4

        self.title_label = Label(
            text="Enter Playstation IP",
            font=load_font(size=64, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.BLUE.rgb(),
            pos=(48, 42),
            center=False,
        )

        self.recent_label = Label(
            text="Recent connections",
            font=load_font(size=42, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(810, 180),
            center=True,
        )
        self.textfield = TextField(
            text=get_ip_prefill(),
            font=load_font(size=36, dir="noto_sans", name=FontFamily.NOTOSANS_REGULAR),
            color=Color.WHITE.rgb(),
            pos=(62, 142),
            width=356,
            height=76,
            border_color=Color.GREY.rgb(),
        )

    def draw(self, surface):
        surface.fill(Color.BLACK.rgb())
        self.title_label.draw(surface)
        self.recent_label.draw(surface)
        self.textfield.draw(surface)
        self.button_group.draw(surface)

    def handle_event(self, event):
        self.button_group.handle_event(event)
        self.textfield.handle_event(event)

        if event.type == BACK_TO_MENU_RELEASED:
            self.on_back_released(event)
        elif event.type in (
            ENTER_IP_KEYPAD_BUTTON_RELEASED,
            ENTER_IP_DEL_BUTTON_RELEASED,
        ):
            self.on_keypad_released(event)
        elif event.type == ENTER_IP_OK_BUTTON_RELEASED:
            self.on_ok_released()

    def on_back_released(self, event):
        # Return to Settings
        from .settings_state import SettingsState

        self.state_manager.change_state(SettingsState(self.state_manager))

    def on_ok_released(self):
        ip = self.textfield.text.strip()
        if not self.is_valid_ipv4(ip):
            return  # ignore invalid; the keypad view remains visible

        # Persist IP in config
        cfg = ConfigManager.get_config()
        setattr(cfg, "playstation_ip", ip)
        try:
            setter = getattr(ConfigManager, "set_playstation_ip", None)
            if callable(setter):
                setter(ip)
            else:
                ConfigManager.save_config(cfg)
        except Exception:
            # best-effort persistence
            pass

        # If a custom callback was provided elsewhere, allow it (back-compat)
        if self._on_submit is not None:
            try:
                self._on_submit(ip)
            finally:
                # go back to previous state
                self.state_manager.change_state(SettingsState(self.state_manager))
            return

        # Next: open the URL input state to install the proxy tarball
        self.state_manager.change_state(EnterURLState(self.state_manager))

    def on_keypad_released(self, event):
        label = getattr(event, "label", None)
        if not label:
            return

        if label == ".":
            if (
                self.textfield.text.count(".") < 3
                and "." not in self.textfield.text[-1:]
            ):
                self.textfield.text += "."
        elif label == "#":
            pass
        elif label == "<":
            self.textfield.text = self.textfield.text[:-1]
        else:
            if len(label) >= 7:
                self.textfield.text = label
                self.on_ok_released()
            else:
                self.textfield.text += label

    def is_valid_ipv4(self, ip_str):
        parts = ip_str.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if part == "":
                return False
            if len(part) > 1 and part.startswith("0"):
                return False
            try:
                num = int(part)
            except ValueError:
                return False
            if num < 0 or num > 255:
                return False
        return True

    def update(self, dt):
        super().update(dt)
        self.textfield.update(dt)

    def _button_grid_generator(
        self,
        labels: Iterable[str],
        buttons_per_row: int,
        grid_offset: tuple[int, int],
        global_offset: tuple[int, int],
        button_size: tuple[int, int],
    ) -> list[Button]:
        return [
            Button(
                rect=(
                    i % buttons_per_row * grid_offset[0] + global_offset[0],
                    i // buttons_per_row * grid_offset[1] + global_offset[1],
                    button_size[0],
                    button_size[1],
                ),
                text=val,
                icon=None,
                event_type_pressed=ENTER_IP_KEYPAD_BUTTON_PRESSED,
                event_type_released=ENTER_IP_KEYPAD_BUTTON_RELEASED,
                event_data={"label": val},
                font=load_font(
                    size=34, dir="noto_sans", name=FontFamily.NOTOSANS_REGULAR
                ),
                antialias=True,
            )
            for i, val in enumerate(labels or [])
        ]
