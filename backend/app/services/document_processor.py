"""
Document processing service
Handles PDF, TXT, MD, JSON, CSV, and Excel files
Based on gocustomai patterns for CSV/Excel processing
"""
import os
import json
import logging
from typing import List, Dict, Union
from pathlib import Path
import PyPDF2
from docx import Document
import pandas as pd
from tabulate import tabulate
import xlrd
from app.services.ocr import extract_text_from_image

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process various document types"""
    
    @staticmethod
    def process_pdf(file_path: str) -> List[Dict[str, str]]:
        """Extract text from PDF file"""
        chunks = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        chunks.append({
                            'text': text,
                            'metadata': {
                                'source_type': 'pdf',
                                'source': os.path.basename(file_path),
                                'page': page_num + 1
                            }
                        })
                
                logger.info(f"Processed PDF: {len(chunks)} pages extracted")
                return chunks
                
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise
    
    @staticmethod
    def process_txt(file_path: str) -> List[Dict[str, str]]:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                
                chunks = [{
                    'text': text,
                    'metadata': {
                        'source_type': 'txt',
                        'source': os.path.basename(file_path)
                    }
                }]
                
                logger.info(f"Processed TXT file: {len(text)} characters")
                return chunks
                
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {e}")
            raise
    
    @staticmethod
    def process_md(file_path: str) -> List[Dict[str, str]]:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                
                chunks = [{
                    'text': text,
                    'metadata': {
                        'source_type': 'markdown',
                        'source': os.path.basename(file_path)
                    }
                }]
                
                logger.info(f"Processed Markdown file: {len(text)} characters")
                return chunks
                
        except Exception as e:
            logger.error(f"Error processing Markdown {file_path}: {e}")
            raise
    
    @staticmethod
    def process_docx(file_path: str) -> List[Dict[str, str]]:
        """Extract text from DOCX file"""
        chunks = []
        try:
            doc = Document(file_path)
            
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
            if text.strip():
                chunks.append({
                    'text': text,
                    'metadata': {
                        'source_type': 'docx',
                        'source': os.path.basename(file_path)
                    }
                })
            
            logger.info(f"Processed DOCX file: {len(text)} characters")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {e}")
            raise
    
    @staticmethod
    def process_json(file_path: str) -> List[Dict[str, str]]:
        """Extract text from JSON file"""
        chunks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                # Convert JSON to text representation
                if isinstance(data, dict):
                    text = json.dumps(data, indent=2)
                elif isinstance(data, list):
                    # Process each item in the list
                    for idx, item in enumerate(data):
                        item_text = json.dumps(item, indent=2)
                        chunks.append({
                            'text': item_text,
                            'metadata': {
                                'source_type': 'json',
                                'source': os.path.basename(file_path),
                                'record_id': str(idx)
                            }
                        })
                    return chunks
                else:
                    text = str(data)
                
                chunks.append({
                    'text': text,
                    'metadata': {
                        'source_type': 'json',
                        'source': os.path.basename(file_path)
                    }
                })
                
                logger.info(f"Processed JSON file: {len(chunks)} records")
                return chunks
                
        except Exception as e:
            logger.error(f"Error processing JSON {file_path}: {e}")
            raise
    
    @staticmethod
    def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess a dataframe to clean and prepare it for analysis.
        Based on gocustomai's CSVHandler.preprocess_sheet pattern
        
        Args:
            df: The dataframe to preprocess
            
        Returns:
            The preprocessed dataframe
        """
        # Remove completely empty rows
        df = df[~df.apply(lambda row: all(pd.isna(val) or str(val).strip() == '' for val in row), axis=1)]
        
        if df.empty:
            return df
        
        # Remove columns where more than 50% of the values are empty
        def count_valid(col):
            return col.apply(lambda x: pd.notna(x) and str(x).strip() != '').sum()
        
        def count_invalid(col):
            return col.apply(lambda x: pd.isna(x) or str(x).strip() == '').sum()
        
        cols_to_keep = [
            col for col in df.columns
            if count_valid(df[col]) > count_invalid(df[col])
        ]
        
        if not cols_to_keep:
            return pd.DataFrame()  # Return empty dataframe if no valid columns
        
        df = df[cols_to_keep]
        
        # Remove rows until a valid header is found
        max_iterations = 10  # Prevent infinite loop
        iteration = 0
        while len(df) > 0 and iteration < max_iterations:
            iteration += 1
            if any(str(col).startswith('Unnamed') or str(col).isspace() or str(col) == '' for col in df.columns):
                if len(df) > 0:
                    new_columns = [
                        f'Unnamed: {i}' if pd.isna(val) or str(val).isspace() or str(val) == '' else str(val).strip()
                        for i, val in enumerate(df.iloc[0])
                    ]
                    df.columns = new_columns
                    if len(df) > 1:
                        df = df.iloc[1:].reset_index(drop=True)
                    else:
                        break
                else:
                    break
            else:
                break
        
        if df.empty:
            return df
        
        # Remove rows where all values are the same as the column names
        df = df[~df.apply(lambda row: all(str(row[col]).strip() == str(col).strip() for col in df.columns), axis=1)]
        
        return df
    
    @staticmethod
    def process_csv(file_path: str) -> List[Dict[str, str]]:
        """
        Extract text from CSV file and convert to Markdown table.
        Based on gocustomai's CSVExtractor pattern
        Returns chunks with metadata needed for row-based chunking later.
        """
        chunks = []
        try:
            logger.info(f"Processing CSV file: {file_path}")
            
            # Read CSV with error handling - try different encodings
            df = None
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, encoding_errors="ignore", on_bad_lines='skip')
                    logger.info(f"Successfully read CSV with encoding: {encoding}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to read CSV with encoding {encoding}: {e}")
                    continue
            
            if df is None or df.empty:
                raise ValueError(f"Could not read CSV file {file_path} or file is empty")
            
            logger.info(f"CSV file read: {len(df)} rows, {len(df.columns)} columns")
            
            # Preprocess the dataframe
            df = DocumentProcessor.preprocess_dataframe(df)
            
            if df.empty:
                logger.warning(f"CSV file {file_path} is empty after preprocessing")
                return chunks
            
            # Drop columns with all NaN values
            df = df.dropna(axis=1, how="all")
            # Replace NaN with spaces
            df = df.fillna(value=" ")
            
            # Store the dataframe as raw data for row-based chunking in ingestion
            chunks.append({
                'text': None,  # Will be populated during chunking
                'dataframe': df,  # Store the dataframe for row-based chunking
                'metadata': {
                    'source_type': 'csv',
                    'source': os.path.basename(file_path),
                    'rows': len(df),
                    'columns': len(df.columns)
                }
            })
            
            logger.info(f"Processed CSV: {len(df)} rows, {len(df.columns)} columns")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def process_excel(file_path: str) -> List[Dict[str, str]]:
        """
        Extract text from Excel file (XLS, XLSX) and convert to Markdown tables.
        Handles multiple sheets. Based on gocustomai's CSVHandler pattern
        Stores dataframes for row-based chunking during ingestion.
        """
        chunks = []
        try:
            logger.info(f"Processing Excel file: {file_path}")
            
            # Handle .xls files - xlrd is needed for .xls files
            if file_path.endswith('.xls'):
                try:
                    import xlrd
                    logger.info("Using xlrd for .xls file")
                except ImportError:
                    logger.warning("xlrd not available, may have issues with .xls files")
            
            # Read Excel file
            try:
                excel_file = pd.ExcelFile(file_path, engine=None)  # Let pandas choose engine
                logger.info(f"Excel file opened: {len(excel_file.sheet_names)} sheets found")
            except Exception as e:
                # Try with specific engines
                try:
                    if file_path.endswith('.xlsx'):
                        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
                    elif file_path.endswith('.xls'):
                        excel_file = pd.ExcelFile(file_path, engine='xlrd')
                    else:
                        excel_file = pd.ExcelFile(file_path)
                    logger.info(f"Excel file opened with specific engine: {len(excel_file.sheet_names)} sheets found")
                except Exception as e2:
                    logger.error(f"Failed to open Excel file {file_path}: {e2}")
                    raise
            
            for sheet_name in excel_file.sheet_names:
                try:
                    logger.info(f"Processing sheet: {sheet_name}")
                    
                    # Read sheet - try different engines if needed
                    try:
                        if file_path.endswith('.xlsx'):
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                        elif file_path.endswith('.xls'):
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')
                        else:
                            df = pd.read_excel(file_path, sheet_name=sheet_name)
                    except Exception as e:
                        logger.warning(f"Failed to read sheet '{sheet_name}' with default engine: {e}")
                        # Try with openpyxl as fallback
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                        except:
                            logger.error(f"Failed to read sheet '{sheet_name}': {e}")
                            continue
                    
                    if df.empty:
                        logger.warning(f"Sheet '{sheet_name}' is empty")
                        continue
                    
                    logger.info(f"Sheet '{sheet_name}' read: {len(df)} rows, {len(df.columns)} columns")
                    
                    # Preprocess the dataframe
                    processed_df = DocumentProcessor.preprocess_dataframe(df)
                    
                    if processed_df.empty:
                        logger.warning(f"Sheet '{sheet_name}' in {file_path} is empty after preprocessing")
                        continue
                    
                    # Drop columns with all NaN values
                    processed_df = processed_df.dropna(axis=1, how="all")
                    # Replace NaN with spaces
                    processed_df = processed_df.fillna(value=" ")
                    
                    # Store the dataframe for row-based chunking in ingestion
                    chunks.append({
                        'text': None,  # Will be populated during chunking
                        'dataframe': processed_df,  # Store the dataframe for row-based chunking
                        'metadata': {
                            'source_type': 'excel',
                            'source': os.path.basename(file_path),
                            'sheet_name': sheet_name,
                            'rows': len(processed_df),
                            'columns': len(processed_df.columns)
                        }
                    })
                    
                    logger.info(f"Processed Excel sheet '{sheet_name}': {len(processed_df)} rows, {len(processed_df.columns)} columns")
                    
                except Exception as e:
                    logger.warning(f"Error processing sheet '{sheet_name}' in {file_path}: {e}", exc_info=True)
                    continue
            
            if not chunks:
                raise ValueError("No valid data found in any sheet")
            
            logger.info(f"Processed Excel file: {len(chunks)} sheets extracted")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing Excel {file_path}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def process_file(file_path: str) -> List[Dict[str, str]]:
        """Process file based on extension"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return DocumentProcessor.process_pdf(file_path)
        elif file_ext == '.txt':
            return DocumentProcessor.process_txt(file_path)
        elif file_ext in ['.md', '.markdown']:
            return DocumentProcessor.process_md(file_path)
        elif file_ext == '.docx':
            return DocumentProcessor.process_docx(file_path)
        elif file_ext == '.json':
            return DocumentProcessor.process_json(file_path)
        elif file_ext == '.csv':
            return DocumentProcessor.process_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            return DocumentProcessor.process_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    @staticmethod
    def process_json_from_data(data: any, source_name: str) -> List[Dict[str, str]]:
        """Process JSON data directly (not from file)"""
        chunks = []
        try:
            # Convert JSON to text representation
            if isinstance(data, dict):
                text = json.dumps(data, indent=2)
                chunks.append({
                    'text': text,
                    'metadata': {
                        'source_type': 'json',
                        'source': source_name
                    }
                })
            elif isinstance(data, list):
                # Process each item in the list
                for idx, item in enumerate(data):
                    item_text = json.dumps(item, indent=2)
                    chunks.append({
                        'text': item_text,
                        'metadata': {
                            'source_type': 'json',
                            'source': source_name,
                            'record_id': str(idx)
                        }
                    })
            else:
                text = str(data)
                chunks.append({
                    'text': text,
                    'metadata': {
                        'source_type': 'json',
                        'source': source_name
                    }
                })
            
            logger.info(f"Processed JSON data: {len(chunks)} records")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}")
            raise
    
    @staticmethod
    def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Split text into chunks with overlap"""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        return text_splitter.split_text(text)
    
    @staticmethod
    def chunk_csv_by_rows(df: pd.DataFrame, rows_per_chunk: int = 20, max_chunk_size: int = 25000) -> List[str]:
        """
        Chunk CSV data by rows instead of characters.
        Ensures table structure is preserved and each chunk includes headers.
        
        Args:
            df: The dataframe to chunk
            rows_per_chunk: Number of rows per chunk
            max_chunk_size: Maximum characters per chunk (default OpenAI embedding limit safety)
            
        Returns:
            List of markdown table chunks with headers
        """
        chunks = []
        total_rows = len(df)
        
        if total_rows == 0:
            return chunks
        
        # Start with the target rows per chunk
        current_rows_per_chunk = rows_per_chunk
        
        for start_idx in range(0, total_rows, current_rows_per_chunk):
            end_idx = min(start_idx + current_rows_per_chunk, total_rows)
            chunk_df = df.iloc[start_idx:end_idx].copy()
            
            # Convert chunk to markdown table
            markdown_table = tabulate(chunk_df, tablefmt="pipe", headers="keys", showindex=False)
            
            # If chunk is still too large, reduce rows and retry
            if len(markdown_table) > max_chunk_size:
                # Recursively chunk with fewer rows
                reduced_chunks = DocumentProcessor.chunk_csv_by_rows(
                    chunk_df,
                    rows_per_chunk=max(1, current_rows_per_chunk // 2),
                    max_chunk_size=max_chunk_size
                )
                chunks.extend(reduced_chunks)
            else:
                chunks.append(markdown_table)
        
        return chunks
    
    @staticmethod
    def chunk_excel_by_rows(df: pd.DataFrame, sheet_name: str, rows_per_chunk: int = 20, 
                           max_chunk_size: int = 25000) -> List[str]:
        """
        Chunk Excel sheet data by rows instead of characters.
        Ensures table structure is preserved and each chunk includes headers.
        
        Args:
            df: The dataframe to chunk
            sheet_name: Name of the sheet
            rows_per_chunk: Number of rows per chunk
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of markdown table chunks with headers
        """
        chunks = []
        total_rows = len(df)
        
        if total_rows == 0:
            return chunks
        
        current_rows_per_chunk = rows_per_chunk
        
        for start_idx in range(0, total_rows, current_rows_per_chunk):
            end_idx = min(start_idx + current_rows_per_chunk, total_rows)
            chunk_df = df.iloc[start_idx:end_idx].copy()
            
            # Convert chunk to markdown table with sheet header
            markdown_table = tabulate(chunk_df, tablefmt="pipe", headers="keys", showindex=False)
            
            # Add sheet header and row range info for clarity
            sheet_header = f"## Sheet: {sheet_name} (Rows {start_idx + 1}-{end_idx})\n\n"
            full_chunk = sheet_header + markdown_table
            
            # If chunk is still too large, reduce rows and retry
            if len(full_chunk) > max_chunk_size:
                reduced_chunks = DocumentProcessor.chunk_excel_by_rows(
                    chunk_df,
                    sheet_name=sheet_name,
                    rows_per_chunk=max(1, current_rows_per_chunk // 2),
                    max_chunk_size=max_chunk_size
                )
                chunks.extend(reduced_chunks)
            else:
                chunks.append(full_chunk)
        
        return chunks

