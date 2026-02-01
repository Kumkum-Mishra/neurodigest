# services/embeddings.py
"""
Embedding utilities for MSNRR scoring components (KMS, UPMS).
Uses sentence-transformers for semantic similarity.
"""
import os
from typing import List, Optional
import numpy as np

# Optional import for Vercel deployment (sentence-transformers is too large)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    EMBEDDINGS_AVAILABLE = False

# Global model instance (lazy loaded)
_embedding_model: Optional[object] = None


def get_embedding_model():
    """Lazy load the embedding model. Returns None if embeddings not available."""
    global _embedding_model
    if not EMBEDDINGS_AVAILABLE:
        return None
    if _embedding_model is None:
        # Use a lightweight, fast model for embeddings
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_product / (norm1 * norm2))


def embed_text(text: str) -> np.ndarray:
    """Get embedding vector for text. Returns zero vector if embeddings not available."""
    if not text or not text.strip():
        return np.zeros(384)  # Default dimension for all-MiniLM-L6-v2
    model = get_embedding_model()
    if model is None:
        # Return zero vector if embeddings not available (Vercel deployment)
        return np.zeros(384)
    return model.encode(text, convert_to_numpy=True)


def keyword_match_score(article_text: str, user_keywords: List[str]) -> float:
    """
    Compute Keyword Match Score (KMS) using cosine similarity.
    Returns value in [0, 1].
    """
    if not user_keywords:
        return 0.5  # Neutral score if no keywords
    
    article_embedding = embed_text(article_text)
    keywords_text = " ".join(user_keywords)
    keywords_embedding = embed_text(keywords_text)
    
    similarity = compute_cosine_similarity(article_embedding, keywords_embedding)
    # Normalize to [0, 1] (cosine similarity is already in [-1, 1], but typically [0, 1])
    return max(0.0, min(1.0, (similarity + 1) / 2))


def user_preference_match_score(article_text: str, article_url: str, 
                                user_keywords: List[str], user_sources: List[str]) -> float:
    """
    Compute User Preference Match Score (UPMS).
    Combines keyword matching and source matching.
    """
    scores = []
    
    # Keyword matching (embedding-based)
    if user_keywords:
        kms = keyword_match_score(article_text, user_keywords)
        scores.append(kms)
    
    # Source matching (exact match)
    if user_sources:
        url_lower = article_url.lower()
        source_match = any(src.lower() in url_lower for src in user_sources)
        scores.append(1.0 if source_match else 0.0)
    
    if not scores:
        return 0.5  # Neutral if no preferences
    
    return float(np.mean(scores))


