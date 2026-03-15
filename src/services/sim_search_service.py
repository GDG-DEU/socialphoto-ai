from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import asyncio

from src.models.schemas import SimSearchRequest, SimSearchResponse
from src.services.sim_search.encoder import Encoder
from src.services.sim_search.fusion import FusionEmbedding
from src.services.pinecone_service import PineconeService
from src.utils.image_fetcher import fetch_cloudinary_image


class SimSearchService:
    def __init__(self, pc_service: PineconeService, encoder: Encoder):
        # dim will be updated later to match real Pinecone index dimension
        self.encoder = encoder
        self.fusion = FusionEmbedding()
        self.pc_service = pc_service
        if not self.pc_service.index:
            raise ValueError("Pinecone service not initialized in SimSearchService constructor")
    
    async def search(self, req: SimSearchRequest) -> SimSearchResponse:
        # 1) Validate
        has_text = bool(req.query_text and str(req.query_text).strip())
        has_image = bool(req.cloudinary_public_id and str(req.cloudinary_public_id).strip())

        if not has_text and not has_image:
            raise ValueError("Provide at least one of: query_text or cloudinary_public_id")
        if req.top_k <= 0 or req.top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        
        # 2) Encode (thread pool içinde paralel)
        tasks = []
        if has_text:
            tasks.append(asyncio.to_thread(self.encoder.encode_text, req.query_text))
        if has_image:
            tasks.append(self._fetch_and_encode_image(req.cloudinary_public_id))

        encoded_results = await asyncio.gather(*tasks)

        idx = 0
        v_text = None
        v_image = None

        if has_text:
            v_text = encoded_results[idx]
            idx += 1
        
        if has_image:
            v_image = encoded_results[idx]

        # 3) Fuse
        v_query = self.fusion.fuse_text_image(v_text=v_text, v_image=v_image, w=req.w)
        
        # 4) Query Pinecone (thread pool)
        matches = await asyncio.to_thread(self.pc_service.query_vectors, vector=v_query, top_k=req.top_k)

        results: SimSearchResponse = []
        for m in matches:
            md = (m.get("metadata") or {}) if isinstance(m, dict) else {}
            results.append(
                {
                    "cloudinary_public_id": md.get("cloudinary_public_id"),
                    "sim_score": m.get("score"),
                }
            )

        return SimSearchResponse(results=results)

    async def _fetch_and_encode_image(self, public_id: str) -> List[float]:
        img = await fetch_cloudinary_image(public_id)
        return await asyncio.to_thread(self.encoder.encode_image, img)