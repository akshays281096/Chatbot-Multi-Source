"""
Vector store service for RAG pipeline
Uses ChromaDB for vector storage and retrieval
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
import os
import pickle
from typing import List, Dict, Optional
import logging
import pandas as pd
from app.config import settings
from app.services.embeddings import get_embedding_function

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for document embeddings"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.db_path = settings.VECTOR_DB_PATH
        self.dataframes_path = os.path.join(self.db_path, "dataframes")
        self.dataframes: Dict[str, pd.DataFrame] = {}  # In-memory cache of dataframes
        
    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.db_path, exist_ok=True)
            os.makedirs(self.dataframes_path, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="documents",
                embedding_function=get_embedding_function(),
                metadata={"hnsw:space": "cosine"}
            )
            
            # Load cached dataframes from disk
            await self._load_dataframes_from_disk()
            
            logger.info(f"Vector store initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None
    ):
        """Add documents to the vector store"""
        try:
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in texts]
            
            # Validate chunk sizes before adding
            MAX_CHUNK_SIZE = 30000  # OpenAI embeddings limit
            oversized_chunks = [i for i, text in enumerate(texts) if len(text) > MAX_CHUNK_SIZE]
            
            if oversized_chunks:
                logger.warning(f"Found {len(oversized_chunks)} chunks exceeding size limit. These will be handled by the embedding function.")
            
            # Add documents in batches to avoid overwhelming the API
            batch_size = 100
            all_ids = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                try:
                    self.collection.add(
                        documents=batch_texts,
                        metadatas=batch_metadatas,
                        ids=batch_ids
                    )
                    all_ids.extend(batch_ids)
                    logger.info(f"Added batch {i//batch_size + 1}: {len(batch_texts)} documents")
                except Exception as batch_error:
                    logger.error(f"Error adding batch {i//batch_size + 1}: {batch_error}")
                    logger.error(f"Batch text lengths: {[len(t) for t in batch_texts]}")
                    # Try adding one by one to identify problematic documents
                    for j, (text, metadata, doc_id) in enumerate(zip(batch_texts, batch_metadatas, batch_ids)):
                        try:
                            self.collection.add(
                                documents=[text],
                                metadatas=[metadata],
                                ids=[doc_id]
                            )
                            all_ids.append(doc_id)
                        except Exception as doc_error:
                            logger.error(f"Failed to add document {doc_id}: {doc_error}")
                            logger.error(f"Document length: {len(text)}, preview: {text[:200]}")
                            raise
            
            logger.info(f"Successfully added {len(all_ids)} documents to vector store")
            return all_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}", exc_info=True)
            raise
    
    async def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar documents"""
        try:
            # Convert filter_metadata to ChromaDB where clause format
            where = None
            if filter_metadata:
                where = {}
                for key, value in filter_metadata.items():
                    if isinstance(value, dict) and '$in' in value:
                        # Handle $in operator for ChromaDB
                        where[key] = {"$in": value['$in']}
                    else:
                        where[key] = value
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            raise
    
    async def delete_documents(self, ids: List[str]):
        """Delete documents from the vector store"""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    async def delete_document_by_source(self, source: str) -> int:
        """Delete all chunks of a document by its source name"""
        try:
            # Get all documents first
            results = self.collection.get()
            
            # Find all chunk IDs that match this source
            ids_to_delete = []
            
            if results['ids'] and results['metadatas']:
                for i in range(len(results['ids'])):
                    metadata = results['metadatas'][i] if results['metadatas'][i] else {}
                    doc_source = metadata.get('source', '')
                    sheet_name = metadata.get('sheet_name', '')
                    
                    # Match by source name or source#sheet_name
                    if sheet_name and '#' in source:
                        # Excel with sheet - format is "source#sheet_name"
                        source_part, sheet_part = source.split('#', 1)
                        if doc_source == source_part and sheet_name == sheet_part:
                            ids_to_delete.append(results['ids'][i])
                    elif doc_source == source:
                        # Regular document - format is just "source"
                        ids_to_delete.append(results['ids'][i])
            
            # Delete all matching chunks
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted document '{source}': {len(ids_to_delete)} chunks removed")
            
            return len(ids_to_delete)
            
        except Exception as e:
            logger.error(f"Failed to delete document by source '{source}': {e}")
            raise
    
    async def delete_dataframe(self, dataframe_key: str):
        """Delete a dataframe from storage"""
        try:
            # Remove from memory cache
            if dataframe_key in self.dataframes:
                del self.dataframes[dataframe_key]
                logger.info(f"Removed dataframe from memory: {dataframe_key}")
            
            # Remove from disk storage
            df_file = os.path.join(self.dataframes_path, f"{dataframe_key}.pkl")
            if os.path.exists(df_file):
                os.remove(df_file)
                logger.info(f"Deleted dataframe file: {df_file}")
            
        except Exception as e:
            logger.error(f"Failed to delete dataframe '{dataframe_key}': {e}")
            # Don't raise - dataframe deletion failure shouldn't block document deletion
    
    async def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": "documents"
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"total_documents": 0, "collection_name": "documents"}
    
    async def get_all_documents(self) -> List[Dict]:
        """Get all unique source documents from the collection (groups chunks by source)"""
        try:
            # Get all documents - ChromaDB get() without where clause returns all
            results = self.collection.get()
            
            # Group chunks by source document to get unique documents
            documents_map = {}
            
            if results['ids'] and results['metadatas']:
                for i in range(len(results['ids'])):
                    chunk_id = results['ids'][i]
                    metadata = results['metadatas'][i] if results['metadatas'][i] else {}
                    
                    source = metadata.get('source', 'Unknown')
                    source_type = metadata.get('source_type', 'unknown')
                    
                    # Create a unique key for each source document
                    # For excel files with sheets, use source + sheet_name as key
                    if source_type == 'excel' and 'sheet_name' in metadata:
                        doc_key = f"{source}#{metadata['sheet_name']}"
                    else:
                        doc_key = source
                    
                    # If this document source hasn't been added yet, add it
                    if doc_key not in documents_map:
                        documents_map[doc_key] = {
                            'id': doc_key,  # Use doc_key as the unique ID
                            'source': source,
                            'source_type': source_type,
                        }
                        
                        # Add optional metadata fields if present
                        if 'rows' in metadata:
                            documents_map[doc_key]['rows'] = metadata['rows']
                        if 'columns' in metadata:
                            documents_map[doc_key]['columns'] = metadata['columns']
                        if 'sheet_name' in metadata:
                            documents_map[doc_key]['sheet_name'] = metadata['sheet_name']
                        if 'chunking_strategy' in metadata:
                            documents_map[doc_key]['chunking_strategy'] = metadata['chunking_strategy']
            
            documents = list(documents_map.values())
            logger.info(f"Retrieved {len(documents)} unique source documents (from {len(results.get('ids', []))} total chunks)")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []
    
    async def store_dataframe(self, dataframe_key: str, df: pd.DataFrame):
        """Store a dataframe for use in data query tool"""
        try:
            self.dataframes[dataframe_key] = df
            
            # Also save to disk for persistence
            df_file = os.path.join(self.dataframes_path, f"{dataframe_key}.pkl")
            os.makedirs(os.path.dirname(df_file), exist_ok=True)
            
            with open(df_file, 'wb') as f:
                pickle.dump(df, f)
            
            logger.info(f"Stored dataframe: {dataframe_key}")
        except Exception as e:
            logger.error(f"Failed to store dataframe {dataframe_key}: {e}")
    
    async def get_dataframes(self) -> Dict[str, pd.DataFrame]:
        """Get all stored dataframes"""
        return self.dataframes
    
    async def _load_dataframes_from_disk(self):
        """Load dataframes from disk into memory"""
        try:
            if not os.path.exists(self.dataframes_path):
                return
            
            for filename in os.listdir(self.dataframes_path):
                if filename.endswith('.pkl'):
                    df_file = os.path.join(self.dataframes_path, filename)
                    with open(df_file, 'rb') as f:
                        dataframe_key = filename[:-4]  # Remove .pkl extension
                        self.dataframes[dataframe_key] = pickle.load(f)
                        logger.info(f"Loaded dataframe from disk: {dataframe_key}")
        except Exception as e:
            logger.warning(f"Failed to load dataframes from disk: {e}")

