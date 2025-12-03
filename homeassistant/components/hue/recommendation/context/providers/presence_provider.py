"""Presence provider for detecting users home/away state."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..home_context import HomeContext, PresenceContext
from .provider import IContextProvider


class PresenceProvider(IContextProvider):
    """Provider that detects presence in the zone.home entity."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize presence provider."""
        self.hass = hass
        self._entity_id = "zone.home"

    @property
    def provider_id(self) -> str:
        """Return provider identifier."""
        return "presence"

    async def fetch(self, context: HomeContext) -> HomeContext:
        """Fetch presence summary and update the HomeContext.

        This provider treats zone.home state larger than 0 as someone being in the zone.
        """
        state = self.hass.states.get(self._entity_id)
        if state:
            is_anyone_home = bool(int(state.state) > 0)
            context.presence = PresenceContext(
                is_anyone_home=is_anyone_home, state=state.state
            )
        return context
