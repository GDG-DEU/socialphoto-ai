from pinecone import Pinecone

from src.config import get_settings

key = get_settings().pinecone_api_key
print("Key var mı?:", bool(key))
print("Key prefix:", (key[:5] + "…") if key else None)

pc = Pinecone(api_key=key)
print("Indexes:", pc.list_indexes())
