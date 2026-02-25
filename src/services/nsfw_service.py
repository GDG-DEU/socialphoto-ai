from transformers import pipeline
from PIL import Image
import io

class NSFWService:
    def __init__(self):
        self.model_id = "AdamCodd/vit-base-nsfw-detector"
        self.classifier = pipeline("image-classification", model=self.model_id)

    def predict(self, image_bytes):
        img = Image.open(io.BytesIO(image_bytes))
        results = self.classifier(img)

        formatted_results = {res['label']: res['score'] for res in results}

        is_nsfw = formatted_results.get('nsfw', 0) > 0.7

        return {
            "is_nsfw": is_nsfw,
            "scores": formatted_results
        }