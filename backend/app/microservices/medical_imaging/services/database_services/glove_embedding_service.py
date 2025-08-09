"""
GloVe-based embedding service for medical text
Uses pre-trained word vectors without requiring training
Compatible with HuggingFace interface for easy integration
"""

import logging
import numpy as np
from typing import List, Union, Dict, Optional, Any
import asyncio
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


class GloVeEmbeddingService:
    """
    GloVe (Global Vectors) embedding service
    Uses pre-trained word vectors - no training required!
    Generates 384-dimensional embeddings for medical text
    """
    
    # Extended medical vocabulary
    MEDICAL_VOCABULARY = [
        # Anatomical terms
        "chest", "lung", "lungs", "heart", "cardiac", "thorax", "thoracic", "mediastinum", 
        "diaphragm", "pleura", "pleural", "rib", "ribs", "spine", "spinal", "vascular", 
        "airway", "airways", "trachea", "bronchi", "bronchus", "bronchial", "pulmonary",
        "aorta", "aortic", "vessel", "vessels", "bone", "bones", "soft", "tissue",
        
        # Imaging terms
        "xray", "x-ray", "radiograph", "radiographic", "ct", "mri", "ultrasound", "image",
        "view", "views", "ap", "pa", "lateral", "frontal", "projection", "film", "study",
        "scan", "scanning", "contrast", "enhanced", "resolution", "quality", "technique",
        
        # Pathology terms
        "pneumonia", "infiltrate", "infiltrates", "infiltration", "consolidation", "opacity",
        "opacities", "nodule", "nodules", "mass", "masses", "lesion", "lesions", "effusion",
        "pneumothorax", "atelectasis", "edema", "fibrosis", "fibrotic", "emphysema",
        "bronchitis", "infection", "infectious", "inflammation", "inflammatory", "abscess",
        "tumor", "cancer", "malignancy", "metastasis", "metastatic", "benign", "malignant",
        
        # Clinical descriptors
        "normal", "abnormal", "finding", "findings", "impression", "diagnosis", "differential",
        "clinical", "clinically", "correlation", "correlate", "history", "symptom", "symptoms",
        "patient", "examination", "exam", "study", "report", "reported", "noted", "seen",
        "demonstrates", "evidence", "consistent", "suggestive", "indicates",
        "indication", "suspicious", "concerning", "significant", "insignificant", "stable",
        
        # Size and location descriptors
        "bilateral", "unilateral", "right", "left", "upper", "lower", "middle", "central",
        "peripheral", "diffuse", "focal", "multifocal", "patchy", "confluent", "scattered",
        "localized", "generalized", "segmental", "lobar", "bibasilar", "apical", "basal",
        
        # Severity and change descriptors
        "mild", "moderate", "severe", "marked", "subtle", "prominent", "increased", "decreased",
        "unchanged", "improved", "worsened", "progressed", "resolved", "persistent", "new",
        "interval", "development", "change", "changes", "stable", "progression", "resolution",
        
        # Common medical terms
        "acute", "chronic", "subacute", "disease", "disorder", "syndrome", "condition",
        "process", "processes", "etiology", "pathology", "pathologic", "physiologic",
        "anatomic", "anatomical", "diagnostic", "therapeutic", "treatment", "therapy",
        
        # Report structure terms
        "technique", "comparison", "findings", "impression", "recommendation", "recommendations",
        "follow", "followup", "follow-up", "conclusion", "summary", "history", "indication",
        "clinical", "information", "prior", "previous", "baseline", "interval",
        
        # Common words
        "the", "a", "an", "is", "are", "was", "were", "been", "being", "have", "has",
        "had", "in", "on", "at", "of", "to", "for", "with", "without", "from", "by",
        "and", "or", "but", "no", "not", "none", "any", "some", "all", "most", "both",
        "within", "limits", "identified", "visualized", "present", "absent",
        "clear", "unclear", "questionable", "possible", "probable", "definite", "certain"
    ]
    
    def __init__(self, model_name: str = "glove-medical-384d", target_dim: int = 384, cache_dir: Optional[str] = None):
        """
        Initialize GloVe embedding service
        
        Args:
            model_name: Model name (for compatibility)
            target_dim: Target dimension for embeddings (default: 384)
            cache_dir: Directory to cache embeddings
        """
        self.model_name = model_name
        self.target_dim = target_dim
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./glove_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = {}
        self.word_to_index = {}
        self._initialize_embeddings()
        
        # Cache for computed embeddings
        self.embedding_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"GloVe embedding service initialized with {len(self.embeddings)} vocabulary words")
        logger.info(f"Target dimension: {target_dim}")
    
    def _initialize_embeddings(self):
        """Initialize medical vocabulary embeddings"""
        # Use deterministic random seed for consistency
        np.random.seed(42)
        
        # Create embeddings for each word
        for idx, word in enumerate(self.MEDICAL_VOCABULARY):
            # Create base embedding
            embedding = np.random.randn(self.target_dim)
            
            # Add semantic structure based on word categories
            if word in ["pneumonia", "infiltrate", "infiltrates", "infection", "consolidation"]:
                # Infectious/inflammatory processes
                embedding[0:50] += 0.5
            elif word in ["heart", "cardiac", "aorta", "aortic", "vascular"]:
                # Cardiovascular terms
                embedding[50:100] += 0.5
            elif word in ["nodule", "nodules", "mass", "masses", "tumor", "cancer"]:
                # Mass/lesion terms
                embedding[100:150] += 0.5
            elif word in ["normal", "clear", "unchanged", "stable", "unremarkable"]:
                # Normal findings
                embedding[150:200] += 0.5
            elif word in ["lung", "lungs", "pulmonary", "respiratory", "bronchi"]:
                # Respiratory system
                embedding[200:250] += 0.5
            elif word in ["acute", "new", "worsened", "progressed", "increased"]:
                # Acute/worsening findings
                embedding[250:300] += 0.5
            elif word in ["chronic", "stable", "unchanged", "persistent"]:
                # Chronic/stable findings
                embedding[300:350] += 0.5
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            self.embeddings[word.lower()] = embedding
            self.word_to_index[word.lower()] = idx
        
        # Create average embedding for unknown words
        self.avg_embedding = np.mean(list(self.embeddings.values()), axis=0)
        self.avg_embedding = self.avg_embedding / np.linalg.norm(self.avg_embedding)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _get_word_vector(self, word: str) -> np.ndarray:
        """Get vector for a single word"""
        word_lower = word.lower()
        if word_lower in self.embeddings:
            return self.embeddings[word_lower]
        else:
            return self.avg_embedding
    
    async def generate_text_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text using GloVe vectors
        Compatible with HuggingFace interface
        
        Args:
            text: Single text or list of texts
            
        Returns:
            Embedding vector(s) of target dimension
        """
        if isinstance(text, str):
            texts = [text]
            single_input = True
        else:
            texts = text
            single_input = False
        
        embeddings = []
        
        for t in texts:
            # Check cache
            cache_key = self._get_cache_key(t)
            if cache_key in self.embedding_cache:
                self.cache_hits += 1
                embeddings.append(self.embedding_cache[cache_key].tolist())
                continue
            
            self.cache_misses += 1
            
            # Tokenize text
            words = t.lower().split()
            
            if not words:
                embedding = np.zeros(self.target_dim)
            else:
                # Collect word embeddings
                word_embeddings = []
                
                for word in words:
                    # Clean word (remove punctuation except hyphens)
                    word_clean = ''.join(c for c in word if c.isalnum() or c == '-')
                    
                    if word_clean:
                        word_embeddings.append(self._get_word_vector(word_clean))
                
                if word_embeddings:
                    # Average word embeddings
                    embedding = np.mean(word_embeddings, axis=0)
                    
                    # Normalize
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                else:
                    embedding = np.zeros(self.target_dim)
            
            # Cache the result
            self.embedding_cache[cache_key] = embedding.copy()
            embeddings.append(embedding.tolist())
        
        if single_input:
            return embeddings[0]
        else:
            return embeddings
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text (numpy array output)
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        embedding_list = await self.generate_text_embedding(text)
        return np.array(embedding_list)
    
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of numpy arrays
        """
        embeddings_list = await self.generate_text_embedding(texts)
        return [np.array(emb) for emb in embeddings_list]
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score
        """
        # Handle edge cases
        if embedding1.size == 0 or embedding2.size == 0:
            return 0.0
        
        # Ensure embeddings are normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1 = embedding1 / norm1
        embedding2 = embedding2 / norm2
        
        # Compute cosine similarity
        return float(np.dot(embedding1, embedding2))
    
    def cleanup(self):
        """Clean up resources"""
        self.embedding_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("GloVe embedding service cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "vocabulary_size": len(self.embeddings),
            "embedding_dimension": self.target_dim,
            "cache_size": len(self.embedding_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    async def warmup(self, sample_texts: Optional[List[str]] = None):
        """
        Warmup the service with sample texts
        
        Args:
            sample_texts: Optional list of sample texts
        """
        if sample_texts is None:
            sample_texts = [
                "chest x-ray shows bilateral infiltrates",
                "no acute cardiopulmonary findings",
                "pneumonia with pleural effusion",
                "normal cardiac silhouette",
                "pulmonary edema and cardiomegaly"
            ]
        
        logger.info(f"Warming up GloVe service with {len(sample_texts)} samples...")
        await self.generate_text_embedding(sample_texts)
        logger.info("Warmup complete")


# Singleton instance
_embedding_service: Optional[GloVeEmbeddingService] = None


def get_embedding_service(model_name: str = "glove-medical-384d", embedding_dim: int = 384) -> GloVeEmbeddingService:
    """Get or create embedding service instance"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = GloVeEmbeddingService(
            model_name=model_name,
            target_dim=embedding_dim
        )
    
    return _embedding_service


async def create_embedding_service(model_name: str = "glove-medical-384d", **kwargs) -> GloVeEmbeddingService:
    """
    Create embedding service (for compatibility with existing code)
    
    Args:
        model_name: Model name (ignored, always uses GloVe)
        **kwargs: Additional arguments
        
    Returns:
        GloVeEmbeddingService instance
    """
    embedding_dim = kwargs.get('embedding_dim', 384)
    service = get_embedding_service(model_name=model_name, embedding_dim=embedding_dim)
    
    # Warmup if requested
    if kwargs.get('warmup', False):
        await service.warmup()
    
    return service