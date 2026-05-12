from __future__ import annotations

import asyncio
from typing import Any

from google import genai
from google.genai import types

from src.services.agent.tools.base_tool import BaseTool
from src.config import get_settings


class GeminiClient:
    """Client wrapper around Gemini model interactions."""

    def __init__(self, tools: list[BaseTool]) -> None:
        """Configure Gemini model with tool declarations and system instructions."""
        api_key = get_settings().gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        tool_declarations = [
            types.FunctionDeclaration(**tool.to_gemini_declaration()) for tool in tools
        ]
        self._client = genai.Client(api_key=api_key)
        self._model_name = get_settings().gemini_model_name
        self._config = types.GenerateContentConfig(
            system_instruction=(
                "You are a helpful assistant for a photography social media app. Your goal is to help photographers to improve themselves and find inspiration. "
                "You can search for similar images and look up user profiles. Use the provided tools to fetch information as needed. If you don't need to use a tool, just provide a direct answer. "
                "Be concise and friendly. "
        ),
            tools=[types.Tool(function_declarations=tool_declarations)],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="AUTO")
            ),
        )

    async def generate(self, messages: list[dict[str, Any]]) -> Any:
        """Generate a response from Gemini for the given conversation content."""
        return await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model_name,
            contents=messages,
            config=self._config,
        )
