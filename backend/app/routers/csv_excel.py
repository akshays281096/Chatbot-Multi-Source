"""
CSV and Excel file upload endpoints (non-RAG)
Handles CSV, XLS, and XLSX files without vector database ingestion
Based on excel_agent.py pattern
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import os
import aiofiles
import logging
from app.config import settings
from app.services.csv_excel_handler import CSVExcelHandler

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage of loaded dataframe handlers
# Format: {source_name: CSVExcelHandler}
loaded_files: dict = {}


@router.post("/upload/csv-excel")
async def upload_csv_excel(
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None)
):
    """
    Upload a CSV or Excel file (XLS/XLSX) for data analysis
    File is NOT added to RAG pipeline, instead stored for direct querying
    
    Args:
        file: CSV, XLS, or XLSX file
        source_name: Optional name for the file (defaults to filename)
    
    Returns:
        File info including sheets (for Excel) and data summary
    """
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed types: CSV, XLS, XLSX"
            )
        
        # Save uploaded file temporarily
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Load and preprocess the file
        handler = CSVExcelHandler(file_path)
        try:
            handler.load_and_preprocess_data()
        except Exception as e:
            logger.error(f"Error loading file {file.filename}: {e}", exc_info=True)
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"Error loading file: {str(e)}"
            )
        
        # Store the handler for later use
        source_key = source_name or file.filename
        loaded_files[source_key] = handler
        
        # Prepare response
        sheets = handler.list_sheets()
        current_sheet = handler.current_sheet
        df = handler.get_current_df()
        
        logger.info(f"Loaded file: {file.filename}, sheets: {sheets}, current: {current_sheet}")
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' loaded successfully",
            "source_name": source_key,
            "file_type": handler.file_type,
            "sheets": sheets,
            "current_sheet": current_sheet,
            "rows": len(df),
            "columns": list(df.columns),
            "data_preview": CSVExcelHandler.sanitize_for_json(df.head(5))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/csv-excel")
async def query_csv_excel(
    source_name: str,
    sheet_name: Optional[str] = None,
    query: Optional[str] = None
):
    """
    Query or get data from a loaded CSV/Excel file
    Similar to excel_agent.py run_excel_query but returns data instead of agent response
    
    Args:
        source_name: Name of the loaded file
        sheet_name: Optional sheet name (for Excel files)
        query: Optional query to find relevant data
    
    Returns:
        Data from the file or sheet, or relevant sheets for query
    """
    try:
        if source_name not in loaded_files:
            raise HTTPException(
                status_code=404,
                detail=f"File '{source_name}' not loaded. Please upload first."
            )
        
        handler = loaded_files[source_name]
        
        # If query provided, find relevant sheets
        if query:
            relevant_sheets = handler.find_most_relevant_sheets(query, top_n=3)
            
            return {
                "status": "success",
                "source_name": source_name,
                "query": query,
                "relevant_sheets": relevant_sheets,
                "message": f"Found {len(relevant_sheets)} relevant sheet(s) for your query"
            }
        
        # Switch to specified sheet if provided
        if sheet_name:
            try:
                handler.switch_sheet(sheet_name)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Return current dataframe data
        df = handler.get_current_df()
        
        return {
            "status": "success",
            "source_name": source_name,
            "current_sheet": handler.current_sheet,
            "rows": len(df),
            "columns": list(df.columns),
            "data": CSVExcelHandler.sanitize_for_json(df)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/csv-excel")
async def list_loaded_files():
    """
    List all loaded CSV/Excel files
    
    Returns:
        List of loaded files and their details
    """
    try:
        files_info = []
        
        for source_name, handler in loaded_files.items():
            df = handler.get_current_df()
            files_info.append({
                "source_name": source_name,
                "file_type": handler.file_type,
                "sheets": handler.list_sheets(),
                "current_sheet": handler.current_sheet,
                "rows": len(df),
                "columns": len(df.columns)
            })
        
        return {
            "status": "success",
            "loaded_files": files_info,
            "count": len(files_info)
        }
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/csv-excel/{source_name}")
async def unload_file(source_name: str):
    """
    Unload a CSV/Excel file from memory
    
    Args:
        source_name: Name of the file to unload
    
    Returns:
        Success message
    """
    try:
        if source_name not in loaded_files:
            raise HTTPException(
                status_code=404,
                detail=f"File '{source_name}' not found"
            )
        
        del loaded_files[source_name]
        
        logger.info(f"Unloaded file: {source_name}")
        
        return {
            "status": "success",
            "message": f"File '{source_name}' unloaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
