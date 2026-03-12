import os
from pinecone import Pinecone
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
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
                        logger.info(f"Pinecone initialized with index: {self.index_name}")
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
            self.index.upsert(vectors=vectors)
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
            self.index.delete(ids=[vector_id])
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
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )
            
            matches = []
            for match in results['matches']:
                matches.append({
                    "id": match['id'],
                    "score": match['score'],
                    "metadata": match['metadata']
                })
            return matches
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

pinecone_service = PineconeService()
