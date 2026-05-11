from abc import ABC, abstractmethod
from typing import Any

class VisionProvider(ABC):
    """Abstract base class for vision model providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'gemini', 'openai')"""
        pass

    @abstractmethod
    async def analyze_image(self, cloudinary_public_id: str, language: str) -> dict[str, Any]:
        """Analyzes an image and returns a structured dictionary matching AnalyzeResult schema."""
        pass
