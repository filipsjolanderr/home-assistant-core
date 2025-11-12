"""Tests for context providers."""

import pytest

from homeassistant.components.hue.recommendation.context import HomeContext
from homeassistant.components.hue.recommendation.context.providers.sun_provider import (
    SunProvider,
)
from homeassistant.core import HomeAssistant


async def test_sun_provider_fetch_with_sun_entity(hass: HomeAssistant) -> None:
    """Test SunProvider fetches sun state correctly."""
    # Set up sun entity state
    hass.states.async_set(
        "sun.sun",
        "above_horizon",
        {"elevation": 45.0, "azimuth": 180.0},
    )
    await hass.async_block_till_done()

    provider = SunProvider(hass)
    context = HomeContext()
    result = await provider.fetch(context)

    assert result.sun.elevation == 45.0
    assert result.sun.azimuth == 180.0
    assert result.sun.state == "above_horizon"


async def test_sun_provider_fetch_without_sun_entity(hass: HomeAssistant) -> None:
    """Test SunProvider handles missing sun entity gracefully."""
    provider = SunProvider(hass)
    context = HomeContext()
    result = await provider.fetch(context)

    assert result.sun.elevation == -90.0
    assert result.sun.state == "below_horizon"


async def test_sun_provider_provider_id(hass: HomeAssistant) -> None:
    """Test SunProvider has correct provider ID."""
    provider = SunProvider(hass)
    assert provider.provider_id == "sun"


async def test_sun_provider_fetch_below_horizon(hass: HomeAssistant) -> None:
    """Test SunProvider handles below horizon state."""
    # Set up sun entity state
    hass.states.async_set(
        "sun.sun",
        "below_horizon",
        {"elevation": -10.0, "azimuth": 0.0},
    )
    await hass.async_block_till_done()

    provider = SunProvider(hass)
    context = HomeContext()
    result = await provider.fetch(context)

    assert result.sun.elevation == -10.0
    assert result.sun.state == "below_horizon"
