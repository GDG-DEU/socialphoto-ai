from transformers import pipeline
from PIL import Image
import io

class NSFWService:
    def __init__(self):
        # Model ve pipeline kurulumu
        self.model_id = "AdamCodd/vit-base-nsfw-detector"
        self.classifier = pipeline("image-classification", model=self.model_id)

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