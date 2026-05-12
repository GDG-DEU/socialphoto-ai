from __future__ import annotations

import logging
from typing import Any

from src.services.providers.vision_provider import VisionProvider

logger = logging.getLogger(__name__)



class AnalyzeService:
    """Calls AI providers to produce structured analysis results for a photo."""

    def __init__(self, providers: list[VisionProvider]) -> None:
        if not providers:
            raise ValueError("At least one VisionProvider must be provided.")
        self._providers = providers

    async def analyze(self, cloudinary_public_id: str, language: str = "en") -> dict[str, Any]:
        """Fetch *cloudinary_public_id* and run AI analysis sequentially using available providers.

        Returns a dict with structured analysis matching AnalyzeResult.

        Raises the last encountered exception if all providers fail.
        """
        last_exception = None
        for provider in self._providers:
            try:
                logger.info("Attempting analysis using provider: %s", provider.name)
                result = await provider.analyze_image(cloudinary_public_id, language)
                logger.info("Analysis successful using provider: %s", provider.name)
                return result
            except Exception as e:
                logger.warning(
                    "Provider '%s' failed for image '%s': %s. Attempting to use the fallback provider.",
                    provider.name,
                    cloudinary_public_id,
                    str(e),
                    exc_info=True
                )
                last_exception = e
        
        logger.error("All AI providers failed for image '%s'", cloudinary_public_id)
        raise last_exception or Exception("No AI providers available.")
