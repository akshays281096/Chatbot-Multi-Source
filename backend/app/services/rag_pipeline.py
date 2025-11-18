"""
Enhanced RAG (Retrieval-Augmented Generation) Pipeline Service
Based on Node.js RAG patterns with improvements for multi-source document handling
"""
import logging
from typing import List, Dict, Optional, Tuple
from app.services.vector_store import VectorStore
from app.config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Enhanced RAG pipeline that implements:
    1. Multi-source document organization (similar to "brains" in Node.js)
    2. Document filtering and retrieval with metadata
    3. Intelligent context ranking and deduplication
    4. Support for structured (CSV/Excel) and unstructured (PDF/TXT) data
    """
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.retrieval_config = {
            'default_k': 5,
            'max_k': 20,
            'similarity_threshold': 0.3,  # Cosine similarity threshold
        }
    
    async def retrieve_relevant_documents(
        self,
        query: str,
        k: int = None,
        filter_sources: Optional[List[str]] = None,
        filter_source_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant documents from the vector store with advanced filtering
        
        Args:
            query: User query text
            k: Number of results to retrieve (defaults to config)
            filter_sources: List of source document IDs to filter by
            filter_source_type: Filter by source type (pdf, csv, excel, etc.)
        
        Returns:
            List of relevant documents with metadata and relevance scores
        """
        try:
            if k is None:
                k = self.retrieval_config['default_k']
            
            # Build metadata filter for ChromaDB
            where_filter = None
            if filter_sources or filter_source_type:
                where_filter = {}
                if filter_sources:
                    where_filter['source'] = {"$in": filter_sources}
                if filter_source_type:
                    where_filter['source_type'] = filter_source_type
            
            # Search vector store
            results = await self.vector_store.search(
                query=query,
                n_results=k,
                filter_metadata=where_filter
            )
            
            # Filter by similarity threshold and rank by relevance
            filtered_results = [
                r for r in results 
                if r.get('distance') is None or (1 - r['distance']) >= self.retrieval_config['similarity_threshold']
            ]
            
            logger.info(f"Retrieved {len(filtered_results)} relevant documents for query: {query[:100]}")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    async def get_document_context(
        self,
        documents: List[Dict],
        max_context_length: int = 3000
    ) -> Tuple[str, List[str]]:
        """
        Build context string from retrieved documents
        
        Args:
            documents: List of retrieved documents
            max_context_length: Maximum length of context string
        
        Returns:
            Tuple of (context_string, source_references)
        """
        try:
            context_parts = []
            references = set()
            total_length = 0
            
            for doc in documents:
                source = doc['metadata'].get('source', 'Unknown')
                text = doc['text']
                
                # Truncate if adding this document would exceed max length
                if total_length + len(text) > max_context_length:
                    remaining_space = max_context_length - total_length
                    if remaining_space > 100:  # Only add if meaningful amount of space left
                        text = text[:remaining_space] + "..."
                    else:
                        break
                
                # Format document with metadata
                context_parts.append(f"[Source: {source}]\n{text}\n")
                references.add(source)
                total_length += len(text)
            
            context_string = "\n".join(context_parts)
            source_references = list(references)
            
            logger.info(f"Built context ({len(context_string)} chars) from {len(documents)} documents")
            
            return context_string, source_references
            
        except Exception as e:
            logger.error(f"Error building document context: {e}")
            return "", []
    
    async def retrieve_and_rank(
        self,
        query: str,
        k: int = 5,
        filter_sources: Optional[List[str]] = None,
    ) -> Tuple[str, List[str], List[Dict]]:
        """
        Combined retrieval and ranking operation
        
        Args:
            query: User query
            k: Number of results
            filter_sources: List of source document IDs to filter by
        
        Returns:
            Tuple of (context_string, source_references, raw_documents)
        """
        try:
            # Retrieve documents
            documents = await self.retrieve_relevant_documents(
                query=query,
                k=k,
                filter_sources=filter_sources
            )
            
            if not documents:
                logger.warning(f"No relevant documents found for query: {query}")
                return "", [], []
            
            # Build context and get references
            context, references = await self.get_document_context(documents)
            
            return context, references, documents
            
        except Exception as e:
            logger.error(f"Error in retrieve_and_rank: {e}")
            return "", [], []
    
    async def get_available_sources(self) -> Dict[str, List[Dict]]:
        """
        Get all available document sources grouped by type
        Mimics the "brains" concept from Node.js
        
        Returns:
            Dictionary mapping source types to list of documents
        """
        try:
            all_documents = await self.vector_store.get_all_documents()
            
            # Group by source type
            sources_by_type = {}
            for doc in all_documents:
                source_type = doc.get('source_type', 'unknown')
                if source_type not in sources_by_type:
                    sources_by_type[source_type] = []
                sources_by_type[source_type].append(doc)
            
            logger.info(f"Available sources: {len(all_documents)} documents across {len(sources_by_type)} types")
            
            return sources_by_type
            
        except Exception as e:
            logger.error(f"Error getting available sources: {e}")
            return {}
    
    async def validate_filter_sources(
        self,
        filter_sources: Optional[List[str]]
    ) -> List[str]:
        """
        Validate that requested filter sources exist
        
        Args:
            filter_sources: List of source IDs to filter by
        
        Returns:
            Validated list of source IDs (only those that exist)
        """
        try:
            if not filter_sources:
                return []
            
            available_docs = await self.vector_store.get_all_documents()
            available_ids = set(doc['id'] for doc in available_docs)
            
            # Filter to only existing sources
            valid_sources = [s for s in filter_sources if s in available_ids]
            
            if len(valid_sources) < len(filter_sources):
                removed = len(filter_sources) - len(valid_sources)
                logger.warning(f"Removed {removed} non-existent source filters")
            
            return valid_sources
            
        except Exception as e:
            logger.error(f"Error validating filter sources: {e}")
            return filter_sources or []
    
    async def get_document_stats(self) -> Dict:
        """Get statistics about ingested documents"""
        try:
            all_documents = await self.vector_store.get_all_documents()
            collection_stats = await self.vector_store.get_collection_stats()
            
            # Count by type
            type_counts = {}
            for doc in all_documents:
                source_type = doc.get('source_type', 'unknown')
                type_counts[source_type] = type_counts.get(source_type, 0) + 1
            
            # Count by chunking strategy
            strategy_counts = {}
            collection = self.vector_store.collection
            all_results = collection.get()
            for metadata in (all_results.get('metadatas') or []):
                if metadata:
                    strategy = metadata.get('chunking_strategy', 'unknown')
                    strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            return {
                'unique_documents': len(all_documents),
                'total_chunks': collection_stats.get('total_documents', 0),
                'by_type': type_counts,
                'by_chunking_strategy': strategy_counts,
                'sources': all_documents
            }
            
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return {
                'unique_documents': 0,
                'total_chunks': 0,
                'by_type': {},
                'by_chunking_strategy': {},
                'sources': []
            }
    
    def get_retrieval_config(self) -> Dict:
        """Get current retrieval configuration"""
        return self.retrieval_config.copy()
    
    def update_retrieval_config(self, **kwargs):
        """
        Update retrieval configuration
        
        Args:
            **kwargs: Configuration parameters to update
                - default_k: Default number of results
                - max_k: Maximum number of results
                - similarity_threshold: Minimum similarity score
        """
        for key in ['default_k', 'max_k', 'similarity_threshold']:
            if key in kwargs:
                self.retrieval_config[key] = kwargs[key]
        
        logger.info(f"Updated retrieval config: {self.retrieval_config}")
