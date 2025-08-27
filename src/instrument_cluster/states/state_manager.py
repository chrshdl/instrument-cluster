# state_manager.py
from typing import List, Optional

from ..states.state import State


class StateManager:
    running = False

    def __init__(self, initial_state: Optional[State] = None):
        self._stack: List[State] = []
        if initial_state is not None:
            self.push_state(initial_state)

    @property
    def current_state(self) -> Optional[State]:
        return self._stack[-1] if self._stack else None

    # --- Replacement (keeps your old API/semantics) ---
    def change_state(self, new_state: State):
        """Replace the top state with a new one (old: exit, new: enter)."""
        if self._stack:
            top = self._stack.pop()
            try:
                top.exit()
            except Exception:
                pass
        self.push_state(new_state)

    # --- Stack operations (for modals/overlays) ---
    def push_state(self, state: State):
        """Push a new state on top. We exit the previous top to free resources."""
        top = self.current_state
        if top is not None:
            try:
                top.exit()
            except Exception:
                pass
        state.state_manager = self
        self._stack.append(state)
        state.enter()

    def pop_state(self):
        """Pop the top state. Re-enter the new top so it can refresh."""
        if not self._stack:
            return
        top = self._stack.pop()
        try:
            top.exit()
        except Exception:
            pass
        if self._stack:
            # Re-enter previous state so it can refresh UI/status
            self._stack[-1].enter()

    def handle_event(self, event) -> bool:
        """
        Deliver to states from top-most down. Stop at the first consumer.
        Return True if any state consumed the event.
        """
        for state in reversed(self._stack):
            if bool(state.handle_event(event)):
                return True
        return False

    def update(self, dt):
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self, surface):
        if self._stack:
            self._stack[-1].draw(surface)
