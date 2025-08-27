from typing import Optional

import pygame

from ..core.events import BACK_TO_MENU_PRESSED, BACK_TO_MENU_RELEASED
from ..core.utils import FontFamily, load_font
from ..widgets.base.button import Button, ButtonGroup
from ..widgets.base.colors import Color
from ..widgets.base.label import Label
from .state import State
from .state_manager import StateManager


class EnterURLState(State):
    def __init__(self, state_manager: StateManager, title: str, on_submit):
        super().__init__(state_manager)
        self._on_submit = on_submit
        self._text = ""
        self._error: Optional[str] = None

        surf = pygame.display.get_surface()
        self._w, self._h = surf.get_width(), surf.get_height()

        self.title_label = Label(
            text=title,
            font=load_font(size=52, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.BLUE.rgb(),
            pos=(self._w // 2, 60),
            center=True,
        )
        self.hint_label = Label(
            text="Enter URL:",
            font=load_font(size=32, dir="pixeltype", name=FontFamily.PIXEL_TYPE),
            color=Color.WHITE.rgb(),
            pos=(self._w // 2, 120),
            center=True,
        )

        self.submit_button = Button(
            rect=(self._w // 2 - 160, self._h - 120, 140, 70),
            text="OK",
            text_visible=True,
            font=load_font(40, name=FontFamily.PIXEL_TYPE),
            antialias=True,
            event_type_pressed=None,
            event_type_released=None,
        )
        self.cancel_button = Button(
            rect=(self._w // 2 + 20, self._h - 120, 180, 70),
            text="Cancel",
            text_visible=True,
            font=load_font(40, name=FontFamily.PIXEL_TYPE),
            antialias=True,
            event_type_pressed=BACK_TO_MENU_PRESSED,
            event_type_released=BACK_TO_MENU_RELEASED,
        )
        self.btns = ButtonGroup()
        self.btns.add(self.submit_button)
        self.btns.add(self.cancel_button)

    def handle_event(self, event):
        self.btns.handle_event(event)

        if event.type == BACK_TO_MENU_RELEASED:
            self.on_back_released(event)

    def draw(self, surface):
        surface.fill(Color.BLACK.rgb())
        self.title_label.draw(surface)
        self.hint_label.draw(surface)

        # simple input box
        font = load_font(size=34, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
        box_rect = pygame.Rect(self._w // 2 - 420, self._h // 2 - 30, 840, 60)
        pygame.draw.rect(surface, Color.WHITE.rgb(), box_rect, width=2)
        txt = font.render(self._text, False, Color.WHITE.rgb())
        surface.blit(txt, (box_rect.x + 12, box_rect.y + 14))

        self.btns.draw(surface)

        if self._error:
            err_font = load_font(size=30, dir="pixeltype", name=FontFamily.PIXEL_TYPE)
            err_txt = err_font.render(self._error, False, Color.DARK_RED.rgb())
            err_rect = err_txt.get_rect(center=(self._w // 2, box_rect.bottom + 40))
            surface.blit(err_txt, err_rect.topleft)

    def update(self, dt):
        super().update(dt)

    def on_back_released(self, event):
        from ..states.settings_state import SettingsState

        self.state_manager.change_state(SettingsState(self.state_manager))
