"""Sun provider for fetching sun.sun state."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType

from ..home_context import HomeContext, SunContext
from .provider import IContextProvider


class SunProvider(IContextProvider):
    """Provider that fetches sun position from sun.sun entity."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize sun provider."""
        self.hass = hass
        self._entity_id = "sun.sun"

    @property
    def provider_id(self) -> str:
        """Return provider identifier."""
        return "sun"

    async def fetch(self, context: HomeContext) -> HomeContext:
        """Fetch sun state from Home Assistant."""
        state = self.hass.states.get(self._entity_id)

        if state:
            attributes = state.attributes
            context.sun = SunContext(
                elevation=attributes.get("elevation", 0.0),
                azimuth=attributes.get("azimuth", 0.0),
                state=state.state,
            )
        else:
            # Default to below horizon if sun entity not available
            context.sun = SunContext(
                elevation=-90.0,
                azimuth=0.0,
                state="below_horizon",
            )

        return context
