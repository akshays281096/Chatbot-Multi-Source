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
    """Ingest a document (PDF, TXT, MD, DOCX)"""
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
        
        # Process document
        processor = DocumentProcessor()
        try:
            chunks = processor.process_file(file_path)
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}", exc_info=True)
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file: {str(e)}. Please check if the file is valid and not corrupted."
            )
        
        # Get vector store early (needed for CSV/Excel dataframe storage)
        vector_store: VectorStore = request.app.state.vector_store
        
        # Determine if this is a CSV/Excel file - these need special handling
        file_ext = os.path.splitext(file.filename)[1].lower()
        is_csv_file = file_ext == '.csv'
        is_excel_file = file_ext in ['.xls', '.xlsx']
        
        # Process chunks
        all_chunks = []
        all_metadatas = []
        
        for chunk in chunks:
            if is_csv_file and 'dataframe' in chunk:
                # For CSV files, use row-based chunking
                logger.info(f"Using row-based chunking strategy for CSV file: {file.filename}")
                df = chunk['dataframe']
                
                # Store the dataframe for data query tool
                dataframe_key = source_name or file.filename
                await vector_store.store_dataframe(dataframe_key, df)
                
                split_texts = processor.chunk_csv_by_rows(df, rows_per_chunk=20, max_chunk_size=25000)
                
                logger.info(f"CSV chunked into {len(split_texts)} chunks using row-based strategy")
                
                for idx, text in enumerate(split_texts):
                    metadata = chunk['metadata'].copy()
                    metadata['source'] = source_name or file.filename
                    metadata['chunk_index'] = idx
                    metadata['chunking_strategy'] = 'row-based'
                    all_chunks.append(text)
                    all_metadatas.append(metadata)
                    
            elif is_excel_file and 'dataframe' in chunk:
                # For Excel files, use sheet + row-based chunking
                logger.info(f"Using sheet + row-based chunking strategy for Excel file: {file.filename}")
                df = chunk['dataframe']
                sheet_name = chunk['metadata'].get('sheet_name', 'Unknown')
                
                # Store the dataframe for data query tool (use sheet-specific key)
                dataframe_key = f"{source_name or file.filename}#{sheet_name}"
                await vector_store.store_dataframe(dataframe_key, df)
                
                split_texts = processor.chunk_excel_by_rows(df, sheet_name=sheet_name, rows_per_chunk=20, max_chunk_size=25000)
                
                logger.info(f"Excel sheet '{sheet_name}' chunked into {len(split_texts)} chunks using row-based strategy")
                
                for idx, text in enumerate(split_texts):
                    metadata = chunk['metadata'].copy()
                    metadata['source'] = source_name or file.filename
                    metadata['chunk_index'] = idx
                    metadata['chunking_strategy'] = 'row-based'
                    all_chunks.append(text)
                    all_metadatas.append(metadata)
            else:
                # For other file types, use standard character-based chunking
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
        
        logger.info(f"Ingested document: {file.filename}, {len(all_chunks)} chunks")
        
        return {
            "status": "success",
            "message": f"Document '{file.filename}' ingested successfully",
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

