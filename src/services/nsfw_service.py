import asyncio
import io
import logging
from pathlib import Path

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification, pipeline
from PIL import Image

from src.config import get_settings

logger = logging.getLogger(__name__)

class NSFWService:
    def __init__(self):
        self.model_id = "AdamCodd/vit-base-nsfw-detector"

        settings = get_settings()
        self.model_cache_dir = settings.ml_models_dir
        Path(self.model_cache_dir).mkdir(parents=True, exist_ok=True)

        self.device = 0 if torch.cuda.is_available() else -1

        try:
            logger.info(f"Model is being loaded: {self.model_id} (Device: {'GPU' if self.device == 0 else 'CPU'})")
            image_processor = AutoImageProcessor.from_pretrained(
                self.model_id,
                cache_dir=self.model_cache_dir,
            )
            model = AutoModelForImageClassification.from_pretrained(
                self.model_id,
                cache_dir=self.model_cache_dir,
            )
            self.classifier = pipeline(
                "image-classification",
                model=model,
                image_processor=image_processor,
                device=self.device,
            )
            logger.info("Model has been loaded successfully.")
        except Exception as e:
            logger.error(f"Model loading error: {e}")
            raise

    def predict(self, image: Image.Image) -> dict:
        """
        Görüntüyü analiz eder ve ham skorları döner.
        DİKKAT: sync çalışır, async için predict_async kullanılması önerilir.
        """
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            results = self.classifier(image)

            return {res['label']: res['score'] for res in results}

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e)}

    async def predict_async(self, image: Image.Image) -> dict:
        """Runs predict() in a thread pool so the event loop is not blocked."""
        return await asyncio.to_thread(self.predict, image)