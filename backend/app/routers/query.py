"""
Query endpoints for chatbot interactions with RAG pipeline
Implements multi-source document retrieval similar to Node.js weam pattern
Also supports CSV/Excel files loaded via ingestion endpoint
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Literal
import logging
from app.services.langgraph_service import query_chatbot
from app.services.vector_store import VectorStore
from app.services.rag_pipeline import RAGPipeline
from app.services.csv_excel_handler import CSVExcelHandler
from app.config import settings
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

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
        # Check if CSV/Excel files are loaded
        from app.routers.csv_excel import loaded_files
        
        # If CSV/Excel files are available, prioritize them
        if loaded_files:
            logger.info(f"CSV/Excel files found: {list(loaded_files.keys())}")
            
            # Try to answer using CSV/Excel data with pandas agent
            csv_response = await _query_with_csv_context(
                query=query_request.query,
                csv_context="",  # Not used, pandas agent uses actual dataframe
                llm_provider=query_request.llm_provider,
                model=query_request.model,
                conversation_history=query_request.conversation_history
            )
            
            # If we got a response without error, return it
            if csv_response.status == "success":
                return csv_response
        
        # Fall back to RAG pipeline if no CSV files or query couldn't be answered from CSV
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


# Helper functions for CSV/Excel queries

def _build_csv_context(query: str, loaded_files: dict) -> str:
    """
    Build context from CSV/Excel files for the given query.
    Finds relevant sheets and builds text context from the data.
    
    Args:
        query: The user's query
        loaded_files: Dictionary of loaded CSVExcelHandler objects
        
    Returns:
        Context string built from CSV/Excel data, or empty string if no relevant data
    """
    context_parts = []
    
    for source_name, handler in loaded_files.items():
        try:
            # Find relevant sheets for this query
            relevant_sheets = handler.find_most_relevant_sheets(query, top_n=1)
            
            if relevant_sheets:
                sheet_name = relevant_sheets[0]
                handler.switch_sheet(sheet_name)
                df = handler.get_current_df()
                
                # Build context from the dataframe
                if not df.empty:
                    context_text = f"Data from '{source_name}' (sheet: {sheet_name}):\n"
                    context_text += f"Columns: {', '.join(df.columns)}\n"
                    context_text += f"Total rows: {len(df)}\n"
                    context_text += f"Sample data:\n{df.head(10).to_string()}\n"
                    context_parts.append(context_text)
                    
                    logger.info(f"Built CSV context from {source_name} sheet {sheet_name}")
        except Exception as e:
            logger.warning(f"Error building context from {source_name}: {e}")
            continue
    
    return "\n".join(context_parts) if context_parts else ""


async def _query_with_csv_context(
    query: str,
    csv_context: str,
    llm_provider: Optional[str] = None,
    model: Optional[str] = None,
    conversation_history: Optional[List[dict]] = None
) -> QueryResponse:
    """
    Query using pandas dataframe agent with CSV/Excel data.
    Uses create_pandas_dataframe_agent for accurate data analysis.
    Based on excel_agent.py pattern - tries multiple sheets if needed.
    
    Args:
        query: The user's query
        csv_context: Not used directly, for reference
        llm_provider: LLM provider to use
        model: Model name to use
        conversation_history: Conversation history for context
        
    Returns:
        QueryResponse with answer based on CSV data analysis
    """
    from app.services.llm_factory import LLMFactory
    from app.routers.csv_excel import loaded_files
    
    try:
        # Use provided LLM provider or default
        llm_provider = llm_provider or settings.DEFAULT_LLM_PROVIDER
        model = model or settings.DEFAULT_MODEL
        
        # Create LLM instance
        llm = LLMFactory.create_llm(llm_provider, model)
        
        # Find all relevant sheets across all loaded files
        sheets_to_try = []
        
        for source_name, handler in loaded_files.items():
            try:
                # Get all relevant sheets sorted by relevance (like excel_agent.py)
                relevant_sheets = handler.find_most_relevant_sheets(query, top_n=len(handler.dfs))
                
                for sheet_name in relevant_sheets:
                    sheets_to_try.append({
                        'source_name': source_name,
                        'handler': handler,
                        'sheet_name': sheet_name,
                        'relevance': handler.calculate_sheet_relevance(query, sheet_name)
                    })
            except Exception as e:
                logger.warning(f"Error getting relevant sheets from {source_name}: {e}")
                continue
        
        # Sort by relevance score (highest first)
        sheets_to_try.sort(key=lambda x: x['relevance'], reverse=True)
        
        if not sheets_to_try:
            raise HTTPException(
                status_code=400,
                detail="No CSV/Excel data available"
            )
        
        # Try each relevant sheet until we get a good answer (like excel_agent.py)
        last_error = None
        
        for sheet_info in sheets_to_try:
            try:
                handler = sheet_info['handler']
                sheet_name = sheet_info['sheet_name']
                source_name = sheet_info['source_name']
                
                logger.info(f"Trying sheet '{sheet_name}' from '{source_name}' (relevance: {sheet_info['relevance']:.2f})")
                
                # Switch to the sheet
                handler.switch_sheet(sheet_name)
                df = handler.get_current_df()
                
                if df.empty:
                    logger.warning(f"Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                # Create pandas dataframe agent for accurate analysis (like excel_agent.py)
                agent = create_pandas_dataframe_agent(
                    llm=llm,
                    df=df,
                    agent_type="tool-calling",
                    verbose=False,
                    early_stopping_method="generate",
                    allow_dangerous_code=True,
                )
                
                # Run the agent with the user's query
                result = await agent.ainvoke({"input": query})
                response_text = result.get("output", "No response generated")
                
                # Convert response to string - handle different response formats
                if isinstance(response_text, list):
                    # Handle Anthropic's list of content blocks format
                    text_parts = []
                    for item in response_text:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        else:
                            text_parts.append(str(item))
                    response_text = " ".join(text_parts)
                elif isinstance(response_text, dict):
                    # Handle single dict response
                    if 'text' in response_text:
                        response_text = response_text['text']
                    else:
                        response_text = str(response_text)
                else:
                    response_text = str(response_text)
                
                # Clean up whitespace
                response_text = response_text.strip() if response_text else ""
                
                # Check if response indicates success (like excel_agent.py does)
                if (
                    response_text
                    and "error" not in response_text.lower()
                    and "not found" not in response_text.lower()
                    and "no relevant" not in response_text.lower()
                ):
                    logger.info(f"Query answered successfully from {source_name} sheet {sheet_name}")
                    
                    return QueryResponse(
                        response=response_text,
                        references=[f"{source_name} (sheet: {sheet_name})"],
                        status="success"
                    )
                else:
                    # Record this error and try next sheet
                    last_error = response_text
                    logger.info(f"Response from {sheet_name} was not conclusive, trying next sheet")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error with sheet {sheet_name}: {e}")
                last_error = str(e)
                continue
        
        # If we got here, no sheet provided a good answer
        error_msg = f"Could not find relevant data to answer your question."
        if last_error:
            error_msg += f" Last error: {last_error}"
        
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying with CSV context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))