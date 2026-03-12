import os
from pinecone import Pinecone

key = os.getenv("PINECONE_API_KEY")
print("Key var mı?:", bool(key))
print("Key prefix:", (key[:5] + "…") if key else None)

pc = Pinecone(api_key=key)
print("Indexes:", pc.list_indexes())
