"""Strategy that prefers arrival scenes when someone arrives home."""

from __future__ import annotations

from ...context import HomeContext
from .strategy import IStrategy, StrategyResult


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

        scene_scores: dict[str, float] = {}

        # If transition away->home, prefer scenes that look like 'arrival' or 'welcome'
        if is_anyone_home:
            preferred_keywords = ["arrival", "welcome", "home", "arrive"]
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

        return StrategyResult(
            scene_scores=scene_scores,
            metadata={"is_anyone_home": is_anyone_home},
        )
