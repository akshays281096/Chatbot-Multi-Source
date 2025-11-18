"""
Multi-Source Chatbot API
Main FastAPI application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import ingestion, query, health
from app.services.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Multi-Source Chatbot API...")
    logger.info(f"Default LLM Provider: {settings.DEFAULT_LLM_PROVIDER}")
    logger.info(f"Default Model: {settings.DEFAULT_MODEL}")
    
    # Initialize vector database
    from app.services.vector_store import VectorStore
    vector_store = VectorStore()
    await vector_store.initialize()
    app.state.vector_store = vector_store
    
    yield
    
    # Shutdown
    logger.info("Shutting down Multi-Source Chatbot API...")


app = FastAPI(
    title="Multi-Source Chatbot API",
    description="A production-ready chatbot system with RAG, multi-LLM support, and multi-source ingestion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
app.include_router(query.router, prefix="/api", tags=["Query"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

