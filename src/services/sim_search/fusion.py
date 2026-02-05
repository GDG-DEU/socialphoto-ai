from __future__ import annotations
from typing import List, Optional
import numpy as np


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v if norm == 0 else (v / norm)


def fuse_text_image(
    v_text: Optional[List[float]],
    v_image: Optional[List[float]],
    w: float,
) -> List[float]:
    """
    Multimodal fusion for similarity search.

    - text + image: v = w * v_text + (1 - w) * v_image
    - text only:    v = v_text
    - image only:   v = v_image
    """

    if not (0.0 <= w <= 1.0):
        raise ValueError("w must be between 0 and 1")

    if v_text is None and v_image is None:
        raise ValueError("At least one of v_text or v_image must be provided")

    if v_text is not None and v_image is not None:
        if len(v_text) != len(v_image):
            raise ValueError("Embeddings must have the same dimension")

        vt = np.asarray(v_text, dtype=np.float32)
        vi = np.asarray(v_image, dtype=np.float32)

        vt = _l2_normalize(vt)
        vi = _l2_normalize(vi)

        vq = (w * vt) + ((1.0 - w) * vi)

    elif v_text is not None:
        vq = np.asarray(v_text, dtype=np.float32)

    else:  # v_image is not None
        vq = np.asarray(v_image, dtype=np.float32)

    vq = _l2_normalize(vq)
    return vq.tolist()
