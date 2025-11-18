"""
Health check endpoints
"""
from fastapi import APIRouter, Request
from app.services.vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        # Check vector store
        vector_store: VectorStore = request.app.state.vector_store
        stats = await vector_store.get_collection_stats()
        
        return {
            "status": "healthy",
            "service": "Multi-Source Chatbot API",
            "version": "1.0.0",
            "vector_store": {
                "status": "connected",
                "total_documents": stats.get("total_documents", 0)
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

