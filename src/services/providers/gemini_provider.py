import asyncio
import base64
import logging
from io import BytesIO
from typing import Any

from google import genai
from google.genai import types

from src.config import get_settings
from src.models.schemas import AnalyzeResult
from src.utils.image_fetcher import fetch_cloudinary_image
from src.services.providers.vision_provider import VisionProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider(VisionProvider):
    def __init__(self) -> None:
        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        model_name = settings.gemini_model_name
        if not model_name or not model_name.strip():
            raise ValueError("GEMINI_MODEL_NAME is not set")

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._config = types.GenerateContentConfig(
            system_instruction=settings.analyze_system_instruction,
            response_mime_type="application/json",
            response_schema=AnalyzeResult,
            temperature=0.0,
        )

    @property
    def name(self) -> str:
        return "gemini"

    async def analyze_image(self, cloudinary_public_id: str, language: str) -> dict[str, Any]:
        image = await fetch_cloudinary_image(cloudinary_public_id)

        rgb_image = image.convert("RGB")
        
        # Downsize if it exceeds HD resolution
        if rgb_image.width > settings.res_threshold or rgb_image.height > settings.res_threshold:
            rgb_image.thumbnail((settings.max_image_size, settings.max_image_size))
            
        buffer = BytesIO()
        rgb_image.save(buffer, format="JPEG")
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        contents = [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_data}},
                    {"text": settings.analyze_prompt_template.format(language=language)},
                ],
            }
        ]

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model_name,
            contents=contents,
            config=self._config,
        )

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            logger.debug(
                "Gemini usage - prompt_tokens: %s, candidate_tokens: %s, total_tokens: %s",
                usage.prompt_token_count,
                usage.candidates_token_count,
                usage.total_token_count,
            )

        result = response.parsed
        if result is None:
            response_text = getattr(response, "text", None)
            error_message = (
                f"Failed to parse structured response from provider={self.name}, "
                f"model={self._model_name}"
            )
            if response_text:
                error_message = f"{error_message}. Raw response: {response_text}"
                
            raise ValueError(error_message)

        return result.model_dump()
