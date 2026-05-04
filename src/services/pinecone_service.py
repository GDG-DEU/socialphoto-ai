from pinecone import Pinecone
import logging
from typing import List, Dict, Any, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.pinecone_api_key
        self.index_name = settings.pinecone_index_name
        self.namespace = settings.pinecone_namespace
        self.pc = None
        self.index = None
        
        if self.api_key:
            try:
                self.pc = Pinecone(api_key=self.api_key)
                if self.index_name:
                    # Check if index exists
                    existing_indexes = [i.name for i in self.pc.list_indexes()]
                    if self.index_name in existing_indexes:
                        self.index = self.pc.Index(self.index_name)
                        logger.info(
                            "Pinecone initialized with index=%s namespace=%s",
                            self.index_name,
                            self.namespace or "<default>",
                        )
                    else:
                        logger.warning(f"Index '{self.index_name}' not found. Available indexes: {existing_indexes}")
                else:
                    logger.warning("PINECONE_INDEX_NAME not set")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
        else:
            logger.warning("PINECONE_API_KEY not set")

    def upsert_vectors(self, vectors: List[tuple]) -> bool:
        """Upserts vectors to Pinecone.

        Args:
            vectors: List of tuples containing (vector_id, vector, metadata).  
                vector_id: str - Unique identifier for the vector: .  
                vector: List[float] - List of floats representing the vector: .  
                metadata: Optional[Dict[str, Any]] - Optional metadata dictionary.  

        Returns:
            bool: True if upsert succeeds, False otherwise.
        """
        if not self.index:
            logger.error("Pinecone index not initialized")
            return False
            
        try:
            formatted = [
                {
                    "id": str(v[0]),
                    "values": v[1].tolist() if hasattr(v[1], "tolist") else list(v[1]),
                    "metadata": v[2] if len(v) > 2 and isinstance(v[2], dict) else {},
                }
                for v in vectors
            ]

            if not formatted:
                logger.warning("No vectors were provided for Pinecone upsert")
                return False

            upsert_kwargs = {"vectors": formatted}
            if self.namespace:
                upsert_kwargs["namespace"] = self.namespace

            response = self.index.upsert(**upsert_kwargs)

            upserted_count: Optional[int] = None
            if hasattr(response, "upserted_count"):
                upserted_count = getattr(response, "upserted_count")
            elif isinstance(response, dict):
                upserted_count = response.get("upserted_count")

            if not isinstance(upserted_count, int):
                logger.error("Pinecone upsert response missing valid upserted_count: %r", response)
                return False

            if upserted_count != len(formatted):
                logger.error(
                    "Pinecone upsert count mismatch. expected=%d actual=%d response=%r",
                    len(formatted),
                    upserted_count,
                    response,
                )
                return False

            logger.info(
                "Pinecone upsert succeeded. count=%d index=%s namespace=%s",
                upserted_count,
                self.index_name,
                self.namespace or "<default>",
            )

            return True
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False

    def delete_vector(self, vector_id: str) -> bool:
        """
        Deletes a vector from Pinecone.
        """
        if not self.index:
            logger.error("Pinecone index not initialized")
            return False
            
        try:
            delete_kwargs = {"ids": [vector_id]}
            if self.namespace:
                delete_kwargs["namespace"] = self.namespace
            self.index.delete(**delete_kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector {vector_id}: {e}")
            return False

    def query_vectors(self, vector: List[float], top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Queries Pinecone for similar vectors.
        """
        if not self.index:
            logger.error("Pinecone index not initialized")
            return []
            
        try:
            query_kwargs = {
                "vector": vector,
                "top_k": top_k,
                "include_metadata": True,
                "filter": filter,
            }
            if self.namespace:
                query_kwargs["namespace"] = self.namespace

            results = self.index.query(**query_kwargs)
            
            matches = []
            for match in results.matches:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata or {},
                })
            return matches
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []


pinecone_service = PineconeService()

