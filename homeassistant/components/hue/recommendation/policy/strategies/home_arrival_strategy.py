"""Strategy that prefers arrival scenes when someone arrives home."""

from __future__ import annotations

import logging

from ...context import HomeContext
from homeassistant.components.hue.recommendation.scene_catalog import (
    get_scenes_for_arrival,
)
from .strategy import IStrategy, StrategyResult

_LOGGER = logging.getLogger(__name__)


class HomeArrivalStrategy(IStrategy):
    """Prefer arrival scenes on away->home transition."""

    @property
    def strategy_id(self) -> str:
        """Return strategy identifier."""
        return "home_arrival"

    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Score candidates based on arrival transition.

        Detect an arrival when is_anyone_home bool is changed to True.
        """
        is_anyone_home = context.presence.is_anyone_home

        _LOGGER.debug(
            "HomeArrivalStrategy: scoring %s with is_anyone_home=%s (state=%s)",
            candidates,
            is_anyone_home,
            context.presence.state,
        )

        scene_scores: dict[str, float] = {}

        # If transition away->home, prefer catalog-backed arrival scenes and
        # names that look like 'arrival' or 'welcome'.
        if is_anyone_home:
            preferred_keywords = [
                # Generic arrival-style keywords that match user scenes
                "arrival",
                "welcome",
                "home",
                "arrive",
            ]
            # Also treat catalog scenes that are part of arrival-friendly
            # sets as preferred, so concrete scene names still live in the
            # JSON catalog.
            preferred_keywords.extend(name.lower() for name in get_scenes_for_arrival())
            for scene_id in candidates:
                lowered = scene_id.lower()
                score = 0.0
                for kw in preferred_keywords:
                    if kw in lowered:
                        score = 1.0
                        break
                if score == 0.0:
                    score = 0.2
                scene_scores[scene_id] = score
        else:
            # Neutral scoring so other strategies decide
            for scene_id in candidates:
                scene_scores[scene_id] = 0.0

        _LOGGER.debug("HomeArrivalStrategy: scene_scores=%s", scene_scores)

        return StrategyResult(
            scene_scores=scene_scores,
            metadata={"is_anyone_home": is_anyone_home},
        )
