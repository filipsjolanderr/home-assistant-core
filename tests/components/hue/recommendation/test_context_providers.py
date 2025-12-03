"""Tests for context providers."""

from homeassistant.components.hue.recommendation.context import (
    HomeContext,
    ScheduleContext,
)
from homeassistant.components.hue.recommendation.context.providers.schedule_provider import (
    ScheduleProvider,
)
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


# ScheduleProvider Tests


async def test_schedule_provider_provider_id(hass: HomeAssistant) -> None:
    """Test ScheduleProvider has correct provider ID."""
    provider = ScheduleProvider(hass)
    assert provider.provider_id == "schedule"


async def test_schedule_provider_get_active_period_returns_active(
    hass: HomeAssistant,
) -> None:
    """Test getting single active schedule period."""
    hass.states.async_set("schedule.hue_morning", "on")
    hass.states.async_set("schedule.hue_work", "off")
    hass.states.async_set("schedule.hue_evening", "off")
    hass.states.async_set("schedule.hue_night", "off")
    await hass.async_block_till_done()

    provider = ScheduleProvider(hass)
    active = provider._get_active_period()

    assert active == "morning"


async def test_schedule_provider_get_active_period_returns_none_when_no_active(
    hass: HomeAssistant,
) -> None:
    """Test when no schedules are active."""
    hass.states.async_set("schedule.hue_morning", "off")
    hass.states.async_set("schedule.hue_work", "off")
    hass.states.async_set("schedule.hue_evening", "off")
    hass.states.async_set("schedule.hue_night", "off")
    await hass.async_block_till_done()

    provider = ScheduleProvider(hass)
    active = provider._get_active_period()

    assert active is None


async def test_schedule_provider_get_available_periods_returns_all(
    hass: HomeAssistant,
) -> None:
    """Test available periods list includes all existing entities."""
    hass.states.async_set("schedule.hue_morning", "on")
    hass.states.async_set("schedule.hue_work", "off")
    hass.states.async_set("schedule.hue_evening", "on")
    hass.states.async_set("schedule.hue_night", "off")
    await hass.async_block_till_done()

    provider = ScheduleProvider(hass)
    available = provider._get_available_periods()

    assert "morning" in available
    assert "work" in available
    assert "evening" in available
    assert "night" in available
    assert len(available) == 4


async def test_schedule_provider_get_available_periods_returns_empty(
    hass: HomeAssistant,
) -> None:
    """Test available periods when no schedules exist."""
    # Don't set any schedule entities

    provider = ScheduleProvider(hass)
    available = provider._get_available_periods()

    assert available == []


async def test_schedule_provider_fetch_merges_context(
    hass: HomeAssistant,
) -> None:
    """Test fetch properly merges schedule data into context."""
    hass.states.async_set("schedule.hue_morning", "on")
    hass.states.async_set("schedule.hue_work", "off")
    await hass.async_block_till_done()

    provider = ScheduleProvider(hass)
    context = HomeContext()
    result = await provider.fetch(context)

    assert result.schedule.active_period == "morning"
    assert "morning" in result.schedule.available_periods
    assert "work" in result.schedule.available_periods
    assert result.schedule.has_active_schedule is True
    # Verify it's a ScheduleContext
    assert isinstance(result.schedule, ScheduleContext)
