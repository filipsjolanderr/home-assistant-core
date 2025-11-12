"""Context provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..home_context import HomeContext


class IContextProvider(ABC):
    """Interface for context providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return unique identifier for this provider."""

    @abstractmethod
    async def fetch(self, context: HomeContext) -> HomeContext:
        """Fetch and merge context data.

        Args:
            context: Current context to merge into

        Returns:
            Updated context with provider's data merged in
        """
