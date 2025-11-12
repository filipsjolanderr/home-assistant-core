"""Tests for weights and parameters."""

import pytest

from homeassistant.components.hue.recommendation.policy.weights import (
    WeightsAndParams,
)


def test_weights_and_params_defaults() -> None:
    """Test WeightsAndParams has correct defaults."""
    weights = WeightsAndParams()

    assert weights.strategy_weights == {}
    assert weights.inertia_boost == 0.2
    assert weights.switch_delta_min == 0.1
    assert weights.min_dwell_seconds == 300


def test_weights_and_params_custom_values() -> None:
    """Test WeightsAndParams accepts custom values."""
    weights = WeightsAndParams(
        strategy_weights={"strategy1": 2.0, "strategy2": 1.5},
        inertia_boost=0.3,
        switch_delta_min=0.2,
        min_dwell_seconds=600,
    )

    assert weights.strategy_weights["strategy1"] == 2.0
    assert weights.strategy_weights["strategy2"] == 1.5
    assert weights.inertia_boost == 0.3
    assert weights.switch_delta_min == 0.2
    assert weights.min_dwell_seconds == 600


def test_weights_and_params_get_strategy_weight() -> None:
    """Test get_strategy_weight returns correct weight."""
    weights = WeightsAndParams(
        strategy_weights={"strategy1": 2.0, "strategy2": 1.5}
    )

    assert weights.get_strategy_weight("strategy1") == 2.0
    assert weights.get_strategy_weight("strategy2") == 1.5
    assert weights.get_strategy_weight("unknown") == 1.0  # default
