from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.services.sim_search.encoder import Encoder, EncoderConfig
from src.services.sim_search.fusion import fuse_text_image
from src.services.pinecone_service import pinecone_service


@dataclass
class SimSearchRequest:
    text: Optional[str] = None
    image: Optional[str] = None  # for now: URL/path/base64 string
    w: float = 0.5
    top_k: int = 10


class SimSearchService:
    def __init__(self, encoder: Optional[Encoder] = None):
        # dim will be updated later to match real Pinecone index dimension
        self.encoder = encoder or Encoder(EncoderConfig(dim=512))
    async def search(
        self,
        query_text: Optional[str],
        image_url: Optional[str],
        w: float = 0.5,
        top_k: int = 10,
        ) -> List[Dict[str, Any]]:
        # 1) Validate
        has_text = bool(query_text and str(query_text).strip())
        has_image = bool(image_url and str(image_url).strip())
        if not has_text and not has_image:
            raise ValueError("Provide at least one of: query_text or image_url")

        if top_k <= 0 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        # 2) Encode
        v_text = self.encoder.encode_text(query_text) if has_text else None
        v_image = self.encoder.encode_image(image_url) if has_image else None

        # 3) Fuse
        v_query = fuse_text_image(v_text=v_text, v_image=v_image, w=w)
        # 4) Query Pinecone (captain'ın servisindeki fonksiyon adı query_vectors)
        matches = pinecone_service.query_vectors(vector=v_query, top_k=top_k)

        # 5) Normalize output for API
        results: List[Dict[str, Any]] = []
        for m in matches:
            md = (m.get("metadata") or {}) if isinstance(m, dict) else {}
            results.append(
                {
                    "post_id": md.get("post_id"),
                    "image_url": md.get("image_url"),
                    "sim_score": m.get("score") if isinstance(m, dict) else None,
                }
            )

        return results


    def run(self, req: SimSearchRequest) -> Dict[str, Any]:
        # Validate minimal input
        has_text = bool(req.text and req.text.strip())
        has_image = bool(req.image and str(req.image).strip())
        if not has_text and not has_image:
            raise ValueError("Provide at least one of: text or image")

        if req.top_k <= 0 or req.top_k > 100:
            raise ValueError("top_k must be between 1 and 100")

        # Encode
        v_text = self.encoder.encode_text(req.text) if has_text else None
        v_image = self.encoder.encode_image(req.image) if has_image else None

        # Fuse
        v_query = fuse_text_image(v_text=v_text, v_image=v_image, w=req.w)

        # Query Pinecone
        results = pinecone_service.query_vectors(
            vector=v_query,
            top_k=req.top_k,
        )


        return {
            "query": {
                "w": req.w,
                "top_k": req.top_k,
                "has_text": has_text,
                "has_image": has_image,
            },
            "results": results,
        }


sim_search_service = SimSearchService()
