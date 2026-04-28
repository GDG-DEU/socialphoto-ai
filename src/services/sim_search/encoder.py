from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import hashlib
import numpy as np
import urllib.request
import logging
import io
from PIL import Image

logger = logging.getLogger(__name__)


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
        
        # Download the image content to generate a hash based on actual bytes, not the URL
        try:
            req = urllib.request.Request(image_ref, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                image_bytes = response.read()
                
                # Create a perceptual vector: resize to 16x32 grayscale (512 pixels)
                img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((16, 32))
                pixels = np.array(img, dtype=np.float32).flatten()
                
                # Normalize
                norm = np.linalg.norm(pixels)
                if norm > 0:
                    pixels = pixels / norm
                    
                return pixels.tolist()
        except Exception as e:
            logger.warning(f"Could not fetch image for encoding ({image_ref}): {e}")
            # Fallback to text hash if fetch fails
            return self._stable_vector(seed_text=f"image::{image_ref}")


    def _stable_vector(self, seed_text: str) -> List[float]:
        # Deterministic seed from input so the same input gives same vector
        h = hashlib.sha256(seed_text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "little", signed=False)

        rng = np.random.default_rng(seed)
        v = rng.normal(size=self.config.dim).astype(np.float32)

        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm

        return v.tolist()


