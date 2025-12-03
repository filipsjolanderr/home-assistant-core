"""Tests for Hue bridge config entry update listener."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.components.hue.bridge import _update_listener
from homeassistant.components.hue.const import (
    CONF_RECOMMENDATION_AUTO_APPLY,
    CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL,
)
from homeassistant.core import HomeAssistant


async def test_update_listener_skips_reload_for_recommendation_options(
    hass: HomeAssistant,
) -> None:
    """Do not reload when only recommendation auto-apply options change."""
    entry = SimpleNamespace()
    entry.entry_id = "test-entry"
    # Only recommendation-related options
    entry.options = {
        CONF_RECOMMENDATION_AUTO_APPLY: {"room1": True},
        CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL: False,
    }

    bridge = SimpleNamespace(config_entry=entry, _non_recommendation_options={})
    entry.runtime_data = bridge

    hass.config_entries.async_reload = AsyncMock()

    await _update_listener(hass, entry)  # type: ignore[arg-type]

    hass.config_entries.async_reload.assert_not_called()


async def test_update_listener_reloads_for_other_options(hass: HomeAssistant) -> None:
    """Reload when non-recommendation options change."""
    entry = SimpleNamespace()
    entry.entry_id = "test-entry"
    entry.options = {"other_option": 1}

    bridge = SimpleNamespace(
        config_entry=entry, _non_recommendation_options={"other_option": 0}
    )
    entry.runtime_data = bridge

    hass.config_entries.async_reload = AsyncMock()

    await _update_listener(hass, entry)  # type: ignore[arg-type]

    hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
