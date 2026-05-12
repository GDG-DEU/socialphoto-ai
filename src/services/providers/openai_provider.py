import base64
import logging
from io import BytesIO
from typing import Any

from openai import AsyncOpenAI

from src.config import get_settings
from src.models.schemas import AnalyzeResult
from src.utils.image_fetcher import fetch_cloudinary_image
from src.services.providers.vision_provider import VisionProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAIProvider(VisionProvider):
    def __init__(self) -> None:
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        model_name = settings.openai_model_name
        if not model_name or not model_name.strip():
            raise ValueError("OPENAI_MODEL_NAME is not set")

        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name
        
    @property
    def name(self) -> str:
        return "openai"

    async def analyze_image(self, cloudinary_public_id: str, language: str) -> dict[str, Any]:
        image = await fetch_cloudinary_image(cloudinary_public_id)

        rgb_image = image.convert("RGB")
        
        # Downsize if it exceeds HD resolution
        if rgb_image.width > settings.res_threshold or rgb_image.height > settings.res_threshold:
            rgb_image.thumbnail((settings.max_image_size, settings.max_image_size))
            
        buffer = BytesIO()
        rgb_image.save(buffer, format="JPEG")
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        image_url = f"data:image/jpeg;base64,{b64_data}"

        messages = [
            {"role": "system", "content": settings.analyze_system_instruction},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": settings.analyze_prompt_template.format(language=language)},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]

        response = await self._client.beta.chat.completions.parse(
            model=self._model_name,
            messages=messages,
            response_format=AnalyzeResult,
            temperature=0.0,
        )

        if response.usage:
            logger.debug(
                "OpenAI usage - prompt_tokens: %s, completion_tokens: %s, total_tokens: %s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )

        message = response.choices[0].message
        
        if getattr(message, "parsed", None):
            return message.parsed.model_dump()
        else:
            raise ValueError("OpenAI failed to parse the structured response.")
