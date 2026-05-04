from __future__ import annotations

from typing import Any, ClassVar

import httpx

from src.config import get_settings
from src.services.agent.tools.base_tool import BaseTool


class UserContextTool(BaseTool):
    """Tool for fetching a user's profile and recent context from backend service."""

    name: ClassVar[str] = "get_user_context"
    description: ClassVar[str] = (
        "Fetch the user's profile info and recent posts. "
        "Use when personalizing recommendations or when the user asks "
        "about their own content, stats, or upload history."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The user's unique identifier.",
            }
        },
        "required": ["user_id"],
    }

    async def execute(self, user_id: str, **_: Any) -> Any:
        """Fetch user context from Node.js internal endpoint."""
        settings = get_settings()
        backend_url = settings.backend_url
        api_key = settings.api_key

        if not backend_url:
            raise ValueError("BACKEND_URL is not set")
        if not api_key:
            raise ValueError("API_KEY is not set")

        url = f"{backend_url.rstrip('/')}/internal/users/{user_id}/context"
        headers = {"X-API-Key": api_key}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
