"""Support for Hue button platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .bridge import HueConfigEntry
from .recommendation.platforms.button import async_setup_entry as setup_recommendation_buttons


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up button entities."""
    bridge = config_entry.runtime_data
    if bridge.api_version == 1:
        return

    await setup_recommendation_buttons(hass, config_entry, async_add_entities)
