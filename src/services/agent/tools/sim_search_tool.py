from __future__ import annotations

from typing import Any, ClassVar, Optional

from src.services.agent.tools.base_tool import BaseTool
from src.services.sim_search.sim_search_service import SimSearchService


class SimSearchTool(BaseTool):
    """Tool wrapper for the existing similarity search service."""

    name: ClassVar[str] = "search_similar_images"
    description: ClassVar[str] = (
        "Search for visually or semantically similar photos. "
        "Use when the user asks to find images, search photos, or discover "
        "content similar to a description or a specific image."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query_text": {
                "type": "string",
                "description": "Text description used to search for similar photos.",
            },
            "cloudinary_public_id": {
                "type": "string",
                "description": "Cloudinary image public ID used as visual query.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return.",
                "default": 5,
                "minimum": 1,
            },
        },
    }

    def __init__(self, sim_search_service: SimSearchService) -> None:
        """Initialize with the existing similarity search service."""
        self._sim_search_service = sim_search_service

    async def execute(
        self,
        query_text: Optional[str] = None,
        cloudinary_public_id: Optional[str] = None,
        top_k: int = 5,
        **_: Any,
    ) -> dict[str, Any]:
        """Execute similarity search through the existing service implementation."""
        results = await self._sim_search_service.search(
            query_text=query_text,
            image_url=cloudinary_public_id,
            top_k=top_k,
        )
        return {"results": results}
