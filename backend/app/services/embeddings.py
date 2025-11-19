"""
Embedding service for generating document embeddings
"""
from langchain_openai import OpenAIEmbeddings
from typing import List, Union
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class ChromaDBEmbeddingFunction:
    """Wrapper to adapt LangChain embeddings to ChromaDB's embedding function interface"""
    
    def __init__(self, embeddings):
        self.embeddings = embeddings
    
    def __call__(self, input: Union[List[str], str]) -> List[List[float]]:
        """
        ChromaDB embedding function interface
        Args:
            input: Single string or list of strings to embed
        Returns:
            List of embedding vectors
        """
        if isinstance(input, str):
            input = [input]
        
        # Validate input sizes - OpenAI embeddings have a token limit
        # (~8000 tokens ≈ 32k chars, but we use 30k as safe limit)
        MAX_CHUNK_SIZE = 30000
        
        for i, text in enumerate(input):
            if len(text) > MAX_CHUNK_SIZE:
                logger.error(f"Text chunk {i} is too large ({len(text)} chars). Max allowed: {MAX_CHUNK_SIZE}")
                raise ValueError(
                    f"Text chunk exceeds maximum size ({len(text)} > {MAX_CHUNK_SIZE} chars). "
                    "Please split large chunks before embedding."
                )
        
        # Use LangChain's embed_documents method
        try:
            return self.embeddings.embed_documents(input)
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            logger.error(f"Input lengths: {[len(t) for t in input]}")
            raise


def get_embedding_function():
    """Get the embedding function for ChromaDB"""
    try:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for embeddings")
        
        # Use langchain_openai.OpenAIEmbeddings (recommended, non-deprecated)
        # This works with the newer OpenAI SDK versions
        langchain_embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Wrap it in ChromaDB-compatible interface
        return ChromaDBEmbeddingFunction(langchain_embeddings)
    except Exception as e:
        logger.error(f"Failed to create embedding function: {e}")
        raise

