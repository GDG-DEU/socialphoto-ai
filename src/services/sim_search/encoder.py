from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import hashlib
import numpy as np


@dataclass
class EncoderConfig:
    """
    Placeholder encoder config.

    dim must match Pinecone index dimension.
    We'll set a default now and adjust later to the real value.
    """
    dim: int = 512


class Encoder:
    """
    Placeholder encoder.

    Later this will call a real embedding model:
    - encode_text: text -> embedding
    - encode_image: image bytes/url -> embedding

    For now we return deterministic vectors so tests are stable.
    """

    def __init__(self, config: Optional[EncoderConfig] = None):
        self.config = config or EncoderConfig()

    def encode_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("text is empty")
        return self._stable_vector(seed_text=f"text::{text}")

    def encode_image(self, image_ref: str) -> List[float]:
        """
        image_ref can be a URL, file path, or base64 string later.
        For now we just need something non-empty.
        """
        if not image_ref or not str(image_ref).strip():
            raise ValueError("image is empty")
        return self._stable_vector(seed_text=f"image::{image_ref}")

    def _stable_vector(self, seed_text: str) -> List[float]:
        # Deterministic seed from input so the same input gives same vector
        h = hashlib.sha256(seed_text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "little", signed=False)

        rng = np.random.default_rng(seed)
        v = rng.normal(size=self.config.dim).astype(np.float32)

        # normalize for cosine similarity friendliness
        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm

        return v.tolist()
