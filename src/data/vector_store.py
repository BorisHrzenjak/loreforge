"""
Vector store implementation using ChromaDB for RAG system.
Handles embedding and retrieval of campaign context, memories, and game state.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib
import json
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from utils.config import Config


class VectorStore:
    """Vector store for campaign context and memory management."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.vector_db_path
        self.logger = logging.getLogger("vector_store")
        
        # ChromaDB client and collections
        self.client: Optional[chromadb.Client] = None
        self.campaign_collection: Optional[chromadb.Collection] = None
        self.memory_collection: Optional[chromadb.Collection] = None
        self.character_collection: Optional[chromadb.Collection] = None
        
        # Embedding function
        self.embedding_function = None
        
    async def initialize(self):
        """Initialize ChromaDB and create collections."""
        self.logger.info(f"Initializing vector store at {self.db_path}")
        
        try:
            # Ensure directory exists
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize embedding function
            await self._initialize_embedding_function()
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collections
            await self._create_collections()
            
            self.logger.info("Vector store initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def _initialize_embedding_function(self):
        """Initialize the embedding function."""
        try:
            # Use sentence-transformers for embeddings
            # This model is good for general purpose embeddings
            model_name = "all-MiniLM-L6-v2"
            self.logger.info(f"Loading embedding model: {model_name}")
            
            # Load in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(model_name)
            )
            
            # Create embedding function
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
            
            self.logger.info("Embedding function initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding function: {e}")
            # Fallback to default
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    async def _create_collections(self):
        """Create ChromaDB collections."""
        try:
            # Campaign collection - stores campaign content, NPCs, locations, etc.
            self.campaign_collection = self.client.get_or_create_collection(
                name="campaigns",
                embedding_function=self.embedding_function,
                metadata={"description": "Campaign content and world information"}
            )
            
            # Memory collection - stores game session memories and interactions
            self.memory_collection = self.client.get_or_create_collection(
                name="memories",
                embedding_function=self.embedding_function,
                metadata={"description": "Game session memories and player interactions"}
            )
            
            # Character collection - stores character information and development
            self.character_collection = self.client.get_or_create_collection(
                name="characters",
                embedding_function=self.embedding_function,
                metadata={"description": "Character information and development"}
            )
            
            self.logger.info("Collections created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create collections: {e}")
            raise
    
    async def add_campaign_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add campaign content to the vector store."""
        try:
            # Generate unique ID
            content_id = self._generate_id(content, metadata)
            
            # Add to campaign collection
            self.campaign_collection.add(
                documents=[content],
                metadatas=[{
                    **metadata,
                    "timestamp": datetime.now().isoformat(),
                    "type": "campaign_content"
                }],
                ids=[content_id]
            )
            
            self.logger.debug(f"Added campaign content: {content_id}")
            return content_id
            
        except Exception as e:
            self.logger.error(f"Failed to add campaign content: {e}")
            raise
    
    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add a memory/interaction to the vector store."""
        try:
            # Generate unique ID
            memory_id = self._generate_id(content, metadata)
            
            # Add to memory collection
            self.memory_collection.add(
                documents=[content],
                metadatas=[{
                    **metadata,
                    "timestamp": datetime.now().isoformat(),
                    "type": "memory"
                }],
                ids=[memory_id]
            )
            
            self.logger.debug(f"Added memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")
            raise
    
    async def add_character_info(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add character information to the vector store."""
        try:
            # Generate unique ID
            char_id = self._generate_id(content, metadata)
            
            # Add to character collection
            self.character_collection.add(
                documents=[content],
                metadatas=[{
                    **metadata,
                    "timestamp": datetime.now().isoformat(),
                    "type": "character_info"
                }],
                ids=[char_id]
            )
            
            self.logger.debug(f"Added character info: {char_id}")
            return char_id
            
        except Exception as e:
            self.logger.error(f"Failed to add character info: {e}")
            raise
    
    async def get_relevant_context(self, query: str, limit: int = 5, 
                                 collection_type: str = "all") -> List[Dict[str, Any]]:
        """Get relevant context for a query."""
        try:
            results = []
            
            # Search in different collections based on type
            if collection_type in ["all", "campaign"]:
                campaign_results = self.campaign_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                results.extend(self._format_results(campaign_results, "campaign"))
            
            if collection_type in ["all", "memory"]:
                memory_results = self.memory_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                results.extend(self._format_results(memory_results, "memory"))
            
            if collection_type in ["all", "character"]:
                character_results = self.character_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                results.extend(self._format_results(character_results, "character"))
            
            # Sort by relevance (distance) and limit
            results.sort(key=lambda x: x.get("distance", float('inf')))
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get relevant context: {e}")
            return []
    
    async def get_campaign_memories(self, campaign_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories specific to a campaign."""
        try:
            results = self.memory_collection.query(
                query_texts=["campaign memories"],
                where={"campaign_id": campaign_id},
                n_results=limit
            )
            
            return self._format_results(results, "memory")
            
        except Exception as e:
            self.logger.error(f"Failed to get campaign memories: {e}")
            return []
    
    async def get_character_memories(self, character_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories specific to a character."""
        try:
            results = self.memory_collection.query(
                query_texts=["character memories"],
                where={"character_id": character_id},
                n_results=limit
            )
            
            return self._format_results(results, "memory")
            
        except Exception as e:
            self.logger.error(f"Failed to get character memories: {e}")
            return []
    
    async def search_npcs(self, query: str, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for NPCs in campaign content."""
        try:
            where_clause = {"type": "npc"}
            if campaign_id:
                where_clause["campaign_id"] = campaign_id
            
            results = self.campaign_collection.query(
                query_texts=[query],
                where=where_clause,
                n_results=10
            )
            
            return self._format_results(results, "campaign")
            
        except Exception as e:
            self.logger.error(f"Failed to search NPCs: {e}")
            return []
    
    async def search_locations(self, query: str, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for locations in campaign content."""
        try:
            where_clause = {"type": "location"}
            if campaign_id:
                where_clause["campaign_id"] = campaign_id
            
            results = self.campaign_collection.query(
                query_texts=[query],
                where=where_clause,
                n_results=10
            )
            
            return self._format_results(results, "campaign")
            
        except Exception as e:
            self.logger.error(f"Failed to search locations: {e}")
            return []
    
    def _format_results(self, results: Dict[str, Any], collection_type: str) -> List[Dict[str, Any]]:
        """Format ChromaDB results into a consistent format."""
        formatted = []
        
        if not results or not results.get('documents'):
            return formatted
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        ids = results['ids'][0] if results['ids'] else []
        
        for i, doc in enumerate(documents):
            formatted.append({
                'id': ids[i] if i < len(ids) else None,
                'content': doc,
                'metadata': metadatas[i] if i < len(metadatas) else {},
                'distance': distances[i] if i < len(distances) else None,
                'collection': collection_type
            })
        
        return formatted
    
    def _generate_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate a unique ID for content."""
        # Create a hash based on content and key metadata
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Include relevant metadata in ID
        id_parts = [content_hash, timestamp]
        
        if metadata.get('session_id'):
            id_parts.append(f"sess_{metadata['session_id'][-8:]}")
        if metadata.get('character_id'):
            id_parts.append(f"char_{metadata['character_id'][-8:]}")
        if metadata.get('campaign_id'):
            id_parts.append(f"camp_{metadata['campaign_id'][-8:]}")
        
        return "_".join(id_parts)
    
    async def update_memory(self, memory_id: str, content: str, metadata: Dict[str, Any]):
        """Update an existing memory."""
        try:
            # ChromaDB doesn't support direct updates, so we need to delete and re-add
            self.memory_collection.delete(ids=[memory_id])
            await self.add_memory(content, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to update memory {memory_id}: {e}")
            raise
    
    async def delete_memory(self, memory_id: str):
        """Delete a memory by ID."""
        try:
            self.memory_collection.delete(ids=[memory_id])
            self.logger.debug(f"Deleted memory: {memory_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete memory {memory_id}: {e}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collections."""
        try:
            stats = {}
            
            if self.campaign_collection:
                stats['campaign_count'] = self.campaign_collection.count()
            
            if self.memory_collection:
                stats['memory_count'] = self.memory_collection.count()
                
            if self.character_collection:
                stats['character_count'] = self.character_collection.count()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    async def cleanup_old_memories(self, days_old: int = 30):
        """Clean up old memories."""
        try:
            # This is a simplified cleanup - in practice, you'd want more sophisticated logic
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            # Get all memories
            all_memories = self.memory_collection.get()
            
            # Find old memories to delete
            old_ids = []
            for i, metadata in enumerate(all_memories['metadatas']):
                if metadata and metadata.get('timestamp'):
                    try:
                        mem_date = datetime.fromisoformat(metadata['timestamp']).timestamp()
                        if mem_date < cutoff_date:
                            old_ids.append(all_memories['ids'][i])
                    except:
                        continue
            
            # Delete old memories
            if old_ids:
                self.memory_collection.delete(ids=old_ids)
                self.logger.info(f"Cleaned up {len(old_ids)} old memories")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old memories: {e}")
    
    async def close(self):
        """Close the vector store."""
        # ChromaDB client doesn't need explicit closing
        self.logger.info("Vector store closed")