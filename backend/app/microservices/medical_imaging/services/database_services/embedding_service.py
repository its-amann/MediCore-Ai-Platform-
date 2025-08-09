"""
Embedding Service for Medical Imaging
Handles text embedding generation using Google's Gemini API
"""

import logging
import os
from typing import List, Optional
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
import time

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using Google's Gemini API
    """
    
    EMBEDDING_MODEL = "models/embedding-001"
    EMBEDDING_DIMENSIONS = 768
    MAX_BATCH_SIZE = 100
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the embedding service
        
        Args:
            api_key: Google API key. If not provided, reads from GEMINI_EMBEDDING_API_KEY or GEMINI_API_KEY env var
        """
        self.api_key = api_key or os.getenv("GEMINI_EMBEDDING_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_EMBEDDING_API_KEY or GEMINI_API_KEY not found in environment or provided")
        
        # Configure the API key
        genai.configure(api_key=self.api_key)
        
        logger.info(f"Embedding service initialized with model: {self.EMBEDDING_MODEL}")
    
    async def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                # Use the embedding model
                result = genai.embed_content(
                    model=self.EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                
                embedding = result['embedding']
                
                # Verify dimensions
                if len(embedding) != self.EMBEDDING_DIMENSIONS:
                    logger.warning(
                        f"Unexpected embedding dimensions: {len(embedding)} "
                        f"(expected {self.EMBEDDING_DIMENSIONS})"
                    )
                
                logger.debug(f"Generated embedding for text of length {len(text)}")
                return embedding
                
            except Exception as e:
                logger.error(f"Error generating embedding (attempt {attempt + 1}): {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    raise Exception(f"Failed to generate embedding after {self.RETRY_ATTEMPTS} attempts: {e}")
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors
            
        Raises:
            Exception: If embedding generation fails
        """
        if not texts:
            return []
        
        # Validate inputs
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
            else:
                logger.warning(f"Skipping empty text at index {i}")
        
        if not valid_texts:
            raise ValueError("No valid texts provided for embedding generation")
        
        embeddings = []
        
        # Process in batches to respect API limits
        for i in range(0, len(valid_texts), self.MAX_BATCH_SIZE):
            batch = valid_texts[i:i + self.MAX_BATCH_SIZE]
            batch_embeddings = []
            
            for text in batch:
                try:
                    embedding = await self.generate_text_embedding(text)
                    batch_embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text: {text[:100]}... Error: {e}")
                    # Return None for failed embeddings to maintain list alignment
                    batch_embeddings.append(None)
            
            embeddings.extend(batch_embeddings)
            
            # Add small delay between batches to avoid rate limiting
            if i + self.MAX_BATCH_SIZE < len(valid_texts):
                time.sleep(0.1)
        
        # Filter out None values and log the count
        successful_embeddings = [emb for emb in embeddings if emb is not None]
        if len(successful_embeddings) < len(texts):
            logger.warning(
                f"Generated {len(successful_embeddings)} embeddings out of {len(texts)} texts"
            )
        
        return embeddings
    
    def get_model_info(self) -> dict:
        """
        Get information about the embedding model
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.EMBEDDING_MODEL,
            "dimensions": self.EMBEDDING_DIMENSIONS,
            "max_batch_size": self.MAX_BATCH_SIZE
        }
    
    async def verify_connection(self) -> bool:
        """
        Verify that the API connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to generate a simple embedding
            test_embedding = await self.generate_text_embedding("test connection")
            return len(test_embedding) == self.EMBEDDING_DIMENSIONS
        except Exception as e:
            logger.error(f"Failed to verify API connection: {e}")
            return False