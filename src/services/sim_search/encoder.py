from pathlib import Path

from huggingface_hub import hf_hub_download
import onnxruntime as ort
from transformers import CLIPProcessor
from typing import List
import numpy as np
from PIL import Image

from src.config import get_settings


class Encoder:
    """
    - encode_text: text -> embedding
    - encode_image: image bytes/url -> embedding
    """
    def __init__(self):
        repo_id = "sayantan47/clip-vit-b32-onnx"
        model_cache_dir = get_settings().ml_models_dir
        Path(model_cache_dir).mkdir(parents=True, exist_ok=True)

        onnx_model_path = hf_hub_download(
            repo_id=repo_id,
            filename="onnx/model.onnx",
            cache_dir=model_cache_dir,
        )
        self.session = ort.InferenceSession(onnx_model_path, providers=["CPUExecutionProvider"])
        self.processor = CLIPProcessor.from_pretrained(repo_id, cache_dir=model_cache_dir)

    def encode_text(self, text: str) -> List[float]:
        # Model is a combined graph — needs both text and image inputs.
        # Pass a dummy blank image for the unused image branch.
        dummy_image = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
        inputs = self.processor(text=[text], images=dummy_image, return_tensors="np", padding=True)
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
            "pixel_values": inputs["pixel_values"],
        }
        text_emb = self.session.run(["text_embeds"], onnx_inputs)[0]
        return text_emb[0].tolist()

    def encode_image(self, image: Image.Image) -> List[float]:
        # Model is a combined graph — needs both text and image inputs.
        # Pass a dummy empty string for the unused text branch.
        img = image.convert("RGB")
        inputs = self.processor(text=[""], images=img, return_tensors="np", padding=True)
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
            "pixel_values": inputs["pixel_values"],
        }
        image_emb = self.session.run(["image_embeds"], onnx_inputs)[0]
        return image_emb[0].tolist()