"""
Query endpoints for chatbot interactions with RAG pipeline
Implements multi-source document retrieval similar to Node.js weam pattern
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Literal
import logging
from app.services.langgraph_service import query_chatbot
from app.services.vector_store import VectorStore
from app.services.rag_pipeline import RAGPipeline
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Query request model"""
    query: str
    llm_provider: Optional[Literal["OPENAI", "ANTHROPIC", "GEMINI"]] = None
    model: Optional[str] = None
    use_rag: bool = True  # Default to True for backward compatibility
    selected_documents: Optional[List[str]] = None  # List of document IDs to use for RAG
    conversation_history: Optional[List[dict]] = None


class QueryResponse(BaseModel):
    """Query response model"""
    response: str
    references: List[str]
    status: str


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: Request,
    query_request: QueryRequest
):
    """Query the chatbot and get a response with references"""
    try:
        # Get vector store
        vector_store: VectorStore = request.app.state.vector_store
        
        # Use provided LLM provider or default
        llm_provider = query_request.llm_provider or settings.DEFAULT_LLM_PROVIDER
        model = query_request.model or settings.DEFAULT_MODEL
        
        # Query chatbot
        result = await query_chatbot(
            query=query_request.query,
            vector_store=vector_store if query_request.use_rag else None,
            llm_provider=llm_provider,
            model=model,
            conversation_history=query_request.conversation_history,
            use_rag=query_request.use_rag,
            selected_documents=query_request.selected_documents
        )
        
        # Log query
        logger.info(f"Query processed: {query_request.query[:100]}...")
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents(request: Request):
    """Get all ingested documents"""
    try:
        vector_store: VectorStore = request.app.state.vector_store
        
        # Get all documents from vector store
        documents = await vector_store.get_all_documents()
        
        logger.info(f"Retrieved {len(documents)} documents")
        
        return {
            "status": "success",
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(request: Request, document_id: str):
    """Delete a document and all its chunks from the vector store"""
    try:
        vector_store: VectorStore = request.app.state.vector_store
        
        # Delete document by ID (source name or source#sheet_name)
        deleted_count = await vector_store.delete_document_by_source(document_id)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found"
            )
        
        # Also delete associated dataframe if it exists
        await vector_store.delete_dataframe(document_id)
        
        logger.info(f"Deleted document: {document_id}, {deleted_count} chunks removed")
        
        return {
            "status": "success",
            "message": f"Document '{document_id}' deleted successfully",
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_available_sources(request: Request):
    """Get all available document sources grouped by type (mimics brains concept)"""
    try:
        vector_store: VectorStore = request.app.state.vector_store
        rag_pipeline = RAGPipeline(vector_store)
        
        sources_by_type = await rag_pipeline.get_available_sources()
        
        return {
            "status": "success",
            "sources": sources_by_type,
            "total_types": len(sources_by_type),
            "total_documents": sum(len(docs) for docs in sources_by_type.values())
        }
        
    except Exception as e:
        logger.error(f"Error getting available sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_rag_stats(request: Request):
    """Get RAG pipeline statistics"""
    try:
        vector_store: VectorStore = request.app.state.vector_store
        rag_pipeline = RAGPipeline(vector_store)
        
        stats = await rag_pipeline.get_document_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RetrieveRequest(BaseModel):
    """Request model for document retrieval"""
    query: str
    k: Optional[int] = 5
    filter_sources: Optional[List[str]] = None
    filter_source_type: Optional[str] = None


class RetrieveResponse(BaseModel):
    """Response model for document retrieval"""
    context: str
    references: List[str]
    documents_count: int
    status: str


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_documents(request: Request, retrieve_request: RetrieveRequest):
    """Retrieve relevant documents from the RAG pipeline without calling LLM"""
    try:
        vector_store: VectorStore = request.app.state.vector_store
        rag_pipeline = RAGPipeline(vector_store)
        
        # Validate filter sources
        filter_sources = await rag_pipeline.validate_filter_sources(
            retrieve_request.filter_sources
        )
        
        # Retrieve and rank documents
        context, references, documents = await rag_pipeline.retrieve_and_rank(
            query=retrieve_request.query,
            k=retrieve_request.k,
            filter_sources=filter_sources if filter_sources else None
        )
        
        return RetrieveResponse(
            context=context,
            references=references,
            documents_count=len(documents),
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))