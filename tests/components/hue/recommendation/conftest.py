"""Test fixtures for Hue recommendation engine."""

from unittest.mock import Mock

import pytest

from homeassistant.core import HomeAssistant

from ..conftest import create_mock_bridge


@pytest.fixture
def mock_hue_bridge_v2(hass: HomeAssistant) -> Mock:
    """Create a mock Hue bridge V2 for recommendation tests."""
    return create_mock_bridge(hass, api_version=2)


@pytest.fixture
def mock_sun_state(hass: HomeAssistant) -> Mock:
    """Mock sun.sun entity state."""
    sun_state = Mock()
    sun_state.state = "above_horizon"
    sun_state.attributes = {
        "elevation": 45.0,
        "azimuth": 180.0,
    }
    return sun_state
