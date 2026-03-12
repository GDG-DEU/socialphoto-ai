import asyncio
import io
import torch
import logging
from transformers import pipeline
from PIL import Image

logger = logging.getLogger(__name__)

class NSFWService:
    def __init__(self):
        self.model_id = "AdamCodd/vit-base-nsfw-detector"

        self.device = 0 if torch.cuda.is_available() else -1

        try:
            logger.info(f"Model is being loaded: {self.model_id} (Device: {'GPU' if self.device == 0 else 'CPU'})")
            self.classifier = pipeline(
                "image-classification",
                model=self.model_id,
                device=self.device
            )
            logger.info("Model has been loaded successfully.")
        except Exception as e:
            logger.error(f"Model loading error: {e}")
            raise

    def predict(self, image: Image.Image) -> dict:
        """
        Görüntüyü analiz eder ve ham skorları döner.
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