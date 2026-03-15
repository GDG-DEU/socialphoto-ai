from __future__ import annotations
import asyncio
import logging
from typing import List

from src.models.schemas import UpsertItem, UpsertResponse
from src.services.sim_search.encoder import Encoder
from src.services.pinecone_service import PineconeService
from src.utils.image_fetcher import fetch_cloudinary_image

logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(self, pc_service: PineconeService, encoder: Encoder | None = None):
        self.encoder = encoder or Encoder()
        self.pc_service = pc_service

    async def upsert_items(self, items: List[UpsertItem]) -> UpsertResponse:
        """Encodes each item's image and upserts the resulting vectors to Pinecone.

        Items that fail encoding are skipped and logged.  The upsert is attempted
        with whatever vectors were successfully built.
        """
        tasks = [self._build_vector(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        vectors = []
        for item, result in zip(items, results):
            if isinstance(result, Exception):
                logger.error("Failed to build vector for post %s: %s", item.post_id, result)
            else:
                vectors.append(result)

        if not vectors:
            return UpsertResponse(status="failed", count=0)

        success = await asyncio.to_thread(self.pc_service.upsert_vectors, vectors=vectors)

        if success:
            return UpsertResponse(status="success", count=len(vectors))
        else:
            return UpsertResponse(status="failed", count=0)

    async def _build_vector(self, item: UpsertItem) -> tuple:
        """Fetches the image, encodes it, and returns a Pinecone-ready (id, vector, metadata) tuple."""
        img = await fetch_cloudinary_image(item.cloudinary_public_id)
        embedding = await asyncio.to_thread(self.encoder.encode_image, img)
        vector_id = item.cloudinary_public_id
        metadata = {
            "post_id": item.post_id,
            "cloudinary_public_id": item.cloudinary_public_id,
        }
        return (vector_id, embedding, metadata)

