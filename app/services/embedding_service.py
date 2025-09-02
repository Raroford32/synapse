"""Embedding Service using OpenAI API"""
import logging
from typing import List, Optional, Union
import numpy as np
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimension = settings.R2R_VECTOR_DIMENSION
        
    async def generate_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text using OpenAI"""
        
        if not text:
            return [] if isinstance(text, list) else []
        
        model = model or self.model
        
        try:
            # Handle both single text and batch
            if isinstance(text, str):
                text = [text]
                single_input = True
            else:
                single_input = False
            
            # OpenAI has a limit on batch size
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(text), batch_size):
                batch = text[i:i + batch_size]
                
                response = await self._get_embeddings(batch, model)
                
                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            # Return single embedding if single input
            if single_input:
                return all_embeddings[0] if all_embeddings else []
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _get_embeddings(self, texts: List[str], model: str):
        """Get embeddings from OpenAI with retry logic"""
        
        return await self.client.embeddings.create(
            model=model,
            input=texts
        )
    
    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings"""
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def batch_cosine_similarity(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]]
    ) -> List[float]:
        """Calculate cosine similarity between query and multiple embeddings"""
        
        if not embeddings:
            return []
        
        query_vec = np.array(query_embedding)
        embedding_matrix = np.array(embeddings)
        
        # Compute dot products
        dot_products = np.dot(embedding_matrix, query_vec)
        
        # Compute norms
        query_norm = np.linalg.norm(query_vec)
        embedding_norms = np.linalg.norm(embedding_matrix, axis=1)
        
        # Avoid division by zero
        valid_indices = (embedding_norms != 0) & (query_norm != 0)
        similarities = np.zeros(len(embeddings))
        
        if query_norm != 0:
            similarities[valid_indices] = dot_products[valid_indices] / (
                embedding_norms[valid_indices] * query_norm
            )
        
        return similarities.tolist()
    
    async def find_similar(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]],
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[tuple[int, float]]:
        """Find most similar embeddings to query"""
        
        similarities = self.batch_cosine_similarity(query_embedding, embeddings)
        
        # Get indices and scores above threshold
        indexed_scores = [
            (i, score) for i, score in enumerate(similarities)
            if score >= threshold
        ]
        
        # Sort by similarity score (descending)
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        return indexed_scores[:top_k]