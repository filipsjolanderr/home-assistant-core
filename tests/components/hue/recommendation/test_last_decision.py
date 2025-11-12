"""Tests for last decision store."""

from datetime import UTC, datetime, timedelta

from homeassistant.components.hue.recommendation.policy.last_decision import (
    LastDecisionStore,
)


def test_last_decision_store_initial_state() -> None:
    """Test LastDecisionStore initial state."""
    store = LastDecisionStore()

    assert store.scene_id is None
    assert store.score == 0.0
    assert store.timestamp is None


def test_last_decision_store_update() -> None:
    """Test LastDecisionStore.update updates values."""
    store = LastDecisionStore()

    store.update("scene1", 1.5)

    assert store.scene_id == "scene1"
    assert store.score == 1.5
    assert store.timestamp is not None
    assert isinstance(store.timestamp, datetime)


def test_last_decision_store_get_age_seconds_no_timestamp() -> None:
    """Test get_age_seconds returns infinity when no timestamp."""
    store = LastDecisionStore()

    age = store.get_age_seconds()

    assert age == float("inf")


def test_last_decision_store_get_age_seconds() -> None:
    """Test get_age_seconds returns correct age."""
    store = LastDecisionStore()

    # Set timestamp to 100 seconds ago
    store.timestamp = datetime.now(UTC) - timedelta(seconds=100)
    store.scene_id = "scene1"
    store.score = 1.0

    age = store.get_age_seconds()

    # Should be approximately 100 seconds (allow some tolerance)
    assert 99 <= age <= 101
