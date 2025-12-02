"""Candidate scenes enumeration."""

from __future__ import annotations

from ..context import HomeContext


class CandidateScenes:
    """Enumerates candidate scenes from context."""

    @staticmethod
    def enumerate(context: HomeContext) -> list[str]:
        """Get list of candidate scene IDs from context.

        Args:
            context: Home context with lighting information

        Returns:
            List of scene IDs that are candidates for recommendation
        """
        return list(context.lighting.available_scenes)
