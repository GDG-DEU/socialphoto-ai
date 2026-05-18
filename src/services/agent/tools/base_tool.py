from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with keyword arguments and return the result."""

    def to_gemini_declaration(self) -> dict[str, Any]:
        """Convert tool metadata to a Gemini function declaration."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
