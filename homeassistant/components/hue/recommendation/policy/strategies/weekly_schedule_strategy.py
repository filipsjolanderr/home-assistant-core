from __future__ import annotations

import logging

from ...context import HomeContext
from homeassistant.components.hue.recommendation.scene_catalog import (
    get_scenes_for_schedule_period,
)
from .strategy import IStrategy, StrategyResult

_LOGGER = logging.getLogger(__name__)


class WeeklyScheduleStrategy(IStrategy):
    """Strategy that uses Home Assistant schedule entities to determine scene preferences.

    Users can create schedules in Home Assistant with specific naming conventions:
    - schedule.hue_morning
    - schedule.hue_work
    - schedule.hue_evening
    - schedule.hue_night
    """

    # Map schedule periods to generic keywords
    PERIOD_KEYWORDS = {
        "morning": [
            "morning",
            "dawn",
            "wake",
            "breakfast",
        ],
        "work": [
            "work",
            "focus",
            "concentrate",
            "day",
            "bright",
        ],
        "evening": [
            "evening",
            "relax",
            "dinner",
            "sunset",
        ],
        "night": [
            "night",
            "sleep",
            "dim",
            "bedtime",
            "dusk",
        ],
    }

    @property
    def strategy_id(self) -> str:
        """Return strategy identifier."""
        return "weekly_schedule"

    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Score candidates based on active Home Assistant schedules."""
        # Get active period from context
        active_period = context.schedule.active_period

        _LOGGER.debug(
            "WeeklyScheduleStrategy: scoring %s with active_period=%s, "
            "available_periods=%s, has_active_schedule=%s",
            candidates,
            active_period,
            context.schedule.available_periods,
            context.schedule.has_active_schedule,
        )

        if not active_period:
            # No schedule active - return neutral scores, let other strategies decide
            scene_scores = dict.fromkeys(candidates, 0.5)
            _LOGGER.debug(
                "WeeklyScheduleStrategy: no active period, neutral scores=%s",
                scene_scores,
            )
            return StrategyResult(
                scene_scores=scene_scores,
                metadata={
                    "active_period": None,
                    "has_active_schedule": False,
                    "available_periods": context.schedule.available_periods,
                },
            )

        scene_scores = self._score_scenes(candidates, active_period)

        return StrategyResult(
            scene_scores=scene_scores,
            metadata={
                "active_period": active_period,
                "preferred_keywords": self.PERIOD_KEYWORDS.get(active_period, []),
                "sun_elevation": context.sun.elevation,
                "has_active_schedule": context.schedule.has_active_schedule,
                "available_periods": context.schedule.available_periods,
            },
        )

    def _score_scenes(
        self, candidates: list[str], active_period: str
    ) -> dict[str, float]:
        """Score candidate scenes based on the active period."""
        scene_scores: dict[str, float] = {}
        preferred_keywords = list(self.PERIOD_KEYWORDS.get(active_period, []))

        # Augment keywords with scenes mapped from the static JSON for
        # this schedule period. This ensures concrete scene names only
        # live in the JSON, not in strategy code.
        preferred_keywords.extend(
            name.lower() for name in get_scenes_for_schedule_period(active_period)
        )

        _LOGGER.debug(
            "WeeklyScheduleStrategy: active_period=%s, preferred_keywords=%s",
            active_period,
            preferred_keywords,
        )

        for scene_id in candidates:
            scene_name_lower = scene_id.lower()
            score = 0.1  # Default score

            # Check for preferred keywords (exact match)
            for keyword in preferred_keywords:
                if keyword in scene_name_lower:
                    score = 1.0
                    break

            # Check for partial matches from other periods (lower score)
            if score == 0.1:
                for period_keywords in self.PERIOD_KEYWORDS.values():
                    for keyword in period_keywords:
                        if keyword in scene_name_lower:
                            score = 0.3
                            break
                    if score > 0.1:
                        break

            scene_scores[scene_id] = score

        _LOGGER.debug(
            "WeeklyScheduleStrategy: scene_scores for period %s: %s",
            active_period,
            scene_scores,
        )

        return scene_scores
