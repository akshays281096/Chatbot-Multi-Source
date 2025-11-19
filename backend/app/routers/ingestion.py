"""
Document ingestion endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
import os
import aiofiles
import logging
from app.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.csv_excel_handler import CSVExcelHandler
from app.services.vector_store import VectorStore
from app.services.web_scraper import scrape_and_store
from app.services.website_crawler import crawl_and_store_website
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest/document")
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None)
):
    """Ingest a document into appropriate pipeline:
    - PDF, TXT, MD, DOCX: RAG pipeline (chunked, vectorized, stored in DB)
    - CSV, XLS, XLSX: CSV/Excel handler (loaded in memory, direct query)
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.txt', '.md', '.markdown', '.docx', '.csv', '.xls', '.xlsx']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Check if it's a CSV/Excel file
        is_csv_file = file_ext == '.csv'
        is_excel_file = file_ext in ['.xls', '.xlsx']
        
        # Handle CSV/Excel files separately (non-RAG)
        if is_csv_file or is_excel_file:
            try:
                handler = CSVExcelHandler(file_path)
                handler.load_and_preprocess_data()
                
                # Store the handler in memory
                from app.routers.csv_excel import loaded_files
                source_key = source_name or file.filename
                loaded_files[source_key] = handler
                
                # Prepare response
                sheets = handler.list_sheets()
                current_sheet = handler.current_sheet
                df = handler.get_current_df()
                
                logger.info(f"Loaded CSV/Excel file: {file.filename}, sheets: {sheets}")
                
                # Clean up temporary file
                try:
                    os.remove(file_path)
                except:
                    pass
                
                return {
                    "status": "success",
                    "message": f"File '{file.filename}' loaded successfully (CSV/Excel handler)",
                    "source_name": source_key,
                    "file_type": handler.file_type,
                    "sheets": sheets,
                    "current_sheet": current_sheet,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "data_preview": CSVExcelHandler.sanitize_for_json(df.head(5))
                }
                
            except Exception as e:
                logger.error(f"Error loading CSV/Excel file {file.filename}: {e}", exc_info=True)
                try:
                    os.remove(file_path)
                except:
                    pass
                raise HTTPException(
                    status_code=400,
                    detail=f"Error loading CSV/Excel file: {str(e)}"
                )
        
        # Handle other file types with RAG pipeline (PDF, TXT, MD, DOCX)
        processor = DocumentProcessor()
        try:
            chunks = processor.process_file(file_path)
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}", exc_info=True)
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(e)}. Please check if the file is valid and not corrupted."
            )
        
        # Get vector store for RAG documents
        vector_store: VectorStore = request.app.state.vector_store
        
        # Process chunks for RAG
        all_chunks = []
        all_metadatas = []
        
        for chunk in chunks:
            # For text-based files, use standard character-based chunking
            split_texts = processor.split_text(
                chunk['text'],
                chunk_size=1000,
                chunk_overlap=200
            )
            
            for idx, text in enumerate(split_texts):
                metadata = chunk['metadata'].copy()
                metadata['source'] = source_name or file.filename
                metadata['chunk_index'] = idx
                metadata['chunking_strategy'] = 'character-based'
                all_chunks.append(text)
                all_metadatas.append(metadata)
        
        # Store in vector database
        ids = await vector_store.add_documents(
            texts=all_chunks,
            metadatas=all_metadatas
        )
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        logger.info(f"Ingested RAG document: {file.filename}, {len(all_chunks)} chunks")
        
        return {
            "status": "success",
            "message": f"Document '{file.filename}' ingested successfully (RAG pipeline)",
            "chunks_stored": len(all_chunks),
            "ids": ids[:5]  # Return first 5 IDs as sample
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/web")
async def ingest_web_page(
    request: Request,
    url: str = Form(...),
    crawl_website: bool = Form(False)
):
    """
    Ingest a web page or crawl an entire website
    
    Args:
        url: The URL to ingest (homepage if crawl_website=True)
        crawl_website: If True, crawl the entire website starting from this URL
    """
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format. URL must start with http:// or https://"
            )
        
        vector_store: VectorStore = request.app.state.vector_store
        
        if crawl_website:
            # Crawl entire website
            result = await crawl_and_store_website(
                homepage_url=url,
                vector_store=vector_store,
                max_depth=2,  # Crawl up to 2 levels deep
                max_pages=50  # Maximum 50 pages
            )
            logger.info(f"Crawled website: {url}, {result['pages_crawled']} pages")
        else:
            # Scrape single page
            result = await scrape_and_store(url, vector_store)
            logger.info(f"Ingested web page: {url}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting web page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/json")
async def ingest_json(
    request: Request,
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None)
):
    """Ingest a JSON file"""
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400,
                detail="File must be a JSON file"
            )
        
        # Read JSON content
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        # Process JSON
        processor = DocumentProcessor()
        chunks = processor.process_json_from_data(data, source_name or file.filename)
        
        # Store in vector database
        vector_store: VectorStore = request.app.state.vector_store
        
        all_chunks = []
        all_metadatas = []
        
        for chunk in chunks:
            # Split if needed
            split_texts = processor.split_text(
                chunk['text'],
                chunk_size=1000,
                chunk_overlap=200
            )
            
            for idx, text in enumerate(split_texts):
                metadata = chunk['metadata'].copy()
                metadata['chunk_index'] = idx
                all_chunks.append(text)
                all_metadatas.append(metadata)
        
        ids = await vector_store.add_documents(
            texts=all_chunks,
            metadatas=all_metadatas
        )
        
        logger.info(f"Ingested JSON: {file.filename}, {len(all_chunks)} chunks")
        
        return {
            "status": "success",
            "message": f"JSON file '{file.filename}' ingested successfully",
            "chunks_stored": len(all_chunks),
            "ids": ids[:5]
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

