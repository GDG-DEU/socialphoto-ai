import torch
import torch.nn.functional as F
from PIL import Image
from pathlib import Path
from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection, CLIPVisionConfig
from pinecone import Pinecone, ServerlessSpec
from src.config import get_settings

settings = get_settings()

# --- AYARLAR ---
MODEL_NAME = "openai/clip-vit-base-patch32"
IMAGES_DIR = Path("data/sample_images")

# API Key'i .env'den çekiyoruz
PINECONE_API_KEY = settings.pinecone_api_key
INDEX_NAME = settings.pinecone_index_name or "social-photo-index"  # Pinecone panelindeki ismin bu

# API Key kontrolü
if not PINECONE_API_KEY:
    raise ValueError("HATA: PINECONE_API_KEY bulunamadı! .env dosyanı kontrol et.")

device = "cuda" if torch.cuda.is_available() else "cpu"

# --- PINECONE BAĞLANTISI ---
pc = Pinecone(api_key=PINECONE_API_KEY)

# Index kontrolü ve oluşturma
if INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=512,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )

index = pc.Index(INDEX_NAME)

# --- MODEL YÜKLEME (HATA DÜZELTİLMİŞ) ---
processor = CLIPImageProcessor.from_pretrained(MODEL_NAME)
config = CLIPVisionConfig.from_pretrained(MODEL_NAME)
model = CLIPVisionModelWithProjection.from_pretrained(MODEL_NAME, config=config).to(device)
model.eval()

def image_to_embedding(image_path: Path) -> list[float]:
    img = Image.open(image_path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)
    
    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)
        emb = outputs.image_embeds 
    
    emb = F.normalize(emb, p=2, dim=-1)
    return emb[0].detach().cpu().tolist()

def main():
    if not IMAGES_DIR.exists():
        print(f"Klasör bulunamadı: {IMAGES_DIR.resolve()}")
        return

    image_paths = sorted([p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png"]])
    print(f"Toplam görsel: {len(image_paths)} | Cihaz: {device}")

    for p in image_paths:
        try:
            vec = image_to_embedding(p)
            index.upsert(vectors=[{
                "id": p.name, 
                "values": vec, 
                "metadata": {"filename": p.name}
            }])
            print(f"✅ {p.name} Pinecone'a yüklendi.")
        except Exception as e:
            print(f"❌ {p.name} hatası: {e}")

if __name__ == "__main__":
    main()