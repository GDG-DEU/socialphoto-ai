from transformers import pipeline
from PIL import Image
import io

class NSFWService:
    def __init__(self):
        # Model ve pipeline kurulumu
        self.model_id = "AdamCodd/vit-base-nsfw-detector"
        self.classifier = pipeline("image-classification", model=self.model_id)
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
    def predict(self, image_bytes):
        try:
            # Byte verisini görsel nesnesine çevir
            img = Image.open(io.BytesIO(image_bytes))

            # Kanal uyumsuzluklarını önlemek için RGB'ye zorla
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Sınıflandırma yap
            results = self.classifier(img)

            # Sadece {'label': score} sözlüğünü dön
            return {res['label']: res['score'] for res in results}

        except Exception as e:
            return {"error": str(e)}