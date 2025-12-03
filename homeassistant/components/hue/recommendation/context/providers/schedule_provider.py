"""Schedule provider for Home Assistant schedule entities."""

from __future__ import annotations

from dataclasses import replace
import logging
from typing import TYPE_CHECKING

from ..home_context import HomeContext, ScheduleContext
from .provider import IContextProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ScheduleProvider(IContextProvider):
    """Provides access to Home Assistant schedule entities."""

    def __init__(
        self, hass: HomeAssistant, schedule_prefix: str = "schedule.hue_"
    ) -> None:
        """Initialize the schedule provider."""
        self._hass = hass
        self._schedule_prefix = schedule_prefix
        self._periods = ["morning", "work", "evening", "night"]

    @property
    def provider_id(self) -> str:
        """Return unique identifier for this provider."""
        return "schedule"

    async def fetch(self, context: HomeContext) -> HomeContext:
        """Fetch and merge schedule context data.

        Args:
            context: Current context to merge into

        Returns:
            Updated context with schedule data merged in
        """
        active = self._get_active_period()
        available = self._get_available_periods()

        _LOGGER.debug(
            "ScheduleProvider: active_period=%s, available_periods=%s using prefix=%s",
            active,
            available,
            self._schedule_prefix,
        )

        schedule_context = ScheduleContext(
            active_period=active,
            available_periods=available,
            has_active_schedule=active is not None,
        )

        return replace(context, schedule=schedule_context)

    def _get_active_period(self) -> str | None:
        """Get the currently active schedule period."""
        for period in self._periods:
            entity_id = f"{self._schedule_prefix}{period}"
            state = self._hass.states.get(entity_id)

            if state and state.state == "on":
                _LOGGER.debug(
                    "ScheduleProvider: active schedule %s=%s", entity_id, state.state
                )
                return period

        return None

    def _get_available_periods(self) -> list[str]:
        """Get list of available schedule periods (schedules that exist)."""
        available = []
        for period in self._periods:
            entity_id = f"{self._schedule_prefix}{period}"
            if self._hass.states.get(entity_id) is not None:
                available.append(period)
        return available
