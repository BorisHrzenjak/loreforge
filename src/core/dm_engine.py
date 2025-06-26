"""
Core DM Engine - The brain of the AI Dungeon Master.
Coordinates all game systems and AI interactions.
"""

import asyncio
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

from utils.config import Config
from ai.ollama_client import OllamaClient
from data.database import DatabaseManager
from data.vector_store import VectorStore


class DMEngine:
    """Core engine that coordinates all DM functionality."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        
        # Core components (will be initialized in initialize())
        self.ollama_client: Optional[OllamaClient] = None
        self.database: Optional[DatabaseManager] = None
        self.vector_store: Optional[VectorStore] = None
        
        # Game state
        self.current_session: Optional[Dict[str, Any]] = None
        self.active_character: Optional[Dict[str, Any]] = None
        self.campaign_context: Dict[str, Any] = {}
        
        # Memory and context
        self.session_memory: List[Dict[str, Any]] = []
        self.campaign_memory: List[Dict[str, Any]] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the DM engine."""
        logger = logging.getLogger("dm_engine")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        return logger
    
    async def initialize(self):
        """Initialize all components of the DM engine."""
        self.logger.info("Initializing DM Engine...")
        
        try:
            # Initialize database
            self.database = DatabaseManager(self.config)
            await self.database.initialize()
            self.logger.info("Database initialized")
            
            # Initialize vector store
            self.vector_store = VectorStore(self.config)
            await self.vector_store.initialize()
            self.logger.info("Vector store initialized")
            
            # Initialize Ollama client
            self.ollama_client = OllamaClient(self.config)
            await self.ollama_client.initialize()
            self.logger.info("Ollama client initialized")
            
            self.logger.info("DM Engine initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DM Engine: {e}")
            raise
    
    async def create_session(self, character_id: str, campaign_id: Optional[str] = None) -> str:
        """Create a new game session."""
        self.logger.info(f"Creating session for character {character_id}")
        
        # Load character data
        self.active_character = await self.database.get_character(character_id)
        if not self.active_character:
            raise ValueError(f"Character {character_id} not found")
        
        # Load campaign if specified
        if campaign_id:
            campaign_data = await self.database.get_campaign(campaign_id)
            if campaign_data:
                self.campaign_context = campaign_data
        
        # Create session record
        session_id = await self.database.create_session(character_id, campaign_id)
        
        self.current_session = {
            'id': session_id,
            'character_id': character_id,
            'campaign_id': campaign_id,
            'start_time': asyncio.get_event_loop().time()
        }
        
        # Load relevant memories
        await self._load_session_context()
        
        return session_id
    
    async def process_player_action(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a player action and generate DM response."""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        self.logger.info(f"Processing player action: {action}")
        
        # Add action to memory
        action_entry = {
            'type': 'player_action',
            'content': action,
            'timestamp': asyncio.get_event_loop().time(),
            'context': context or {}
        }
        self.session_memory.append(action_entry)
        
        # Get relevant context from vector store
        relevant_context = await self.vector_store.get_relevant_context(
            action, 
            limit=5
        )
        
        # Generate DM response using Ollama
        dm_response = await self._generate_dm_response(action, relevant_context)
        
        # Add DM response to memory
        response_entry = {
            'type': 'dm_response',
            'content': dm_response['narrative'],
            'timestamp': asyncio.get_event_loop().time(),
            'metadata': dm_response.get('metadata', {})
        }
        self.session_memory.append(response_entry)
        
        # Store in vector database for future reference
        await self.vector_store.add_memory(
            f"Player: {action} | DM: {dm_response['narrative']}",
            metadata={
                'session_id': self.current_session['id'],
                'character_id': self.current_session['character_id'],
                'action_type': 'interaction'
            }
        )
        
        # Update database
        await self.database.log_action(
            self.current_session['id'],
            action,
            dm_response['narrative']
        )
        
        return dm_response
    
    async def _generate_dm_response(self, action: str, context: List[str]) -> Dict[str, Any]:
        """Generate DM response using Ollama."""
        if not self.ollama_client:
            return {"narrative": "The DM seems to be deep in thought...", "metadata": {}}
        
        # Build prompt with context
        prompt = self._build_dm_prompt(action, context)
        
        try:
            response = await self.ollama_client.generate_response(prompt)
            
            # Parse response (this will be expanded to handle structured responses)
            return {
                "narrative": response,
                "metadata": {
                    "model_used": self.config.ai_model,
                    "context_used": len(context)
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to generate DM response: {e}")
            return {
                "narrative": "The DM pauses, deep in thought about your action...",
                "metadata": {"error": str(e)}
            }
    
    def _build_dm_prompt(self, action: str, context: List[str]) -> str:
        """Build the prompt for the DM AI."""
        prompt_parts = []
        
        # System prompt
        prompt_parts.append("""You are an expert Dungeon Master for D&D 5th Edition. You are creative, fair, and focused on creating an engaging story. 

Key principles:
- Follow D&D 5e rules accurately
- Create vivid, immersive descriptions
- Respond to player actions meaningfully
- Ask for dice rolls when appropriate
- Keep the story moving forward
- Remember that player choices have permanent consequences

Current situation:""")
        
        # Add character context
        if self.active_character:
            prompt_parts.append(f"Player Character: {self.active_character.get('name', 'Unknown')} (Level {self.active_character.get('level', 1)} {self.active_character.get('class', 'Adventurer')})")
        
        # Add campaign context
        if self.campaign_context:
            prompt_parts.append(f"Campaign: {self.campaign_context.get('name', 'Custom Adventure')}")
        
        # Add relevant memories/context
        if context:
            prompt_parts.append("Recent events and relevant context:")
            for ctx in context[-3:]:  # Last 3 relevant contexts
                prompt_parts.append(f"- {ctx}")
        
        # Add recent session memory
        if self.session_memory:
            prompt_parts.append("\nRecent actions in this session:")
            for memory in self.session_memory[-5:]:  # Last 5 actions
                if memory['type'] == 'player_action':
                    prompt_parts.append(f"Player: {memory['content']}")
                elif memory['type'] == 'dm_response':
                    prompt_parts.append(f"DM: {memory['content']}")
        
        # Current action
        prompt_parts.append(f"\nPlayer's current action: {action}")
        prompt_parts.append("\nProvide a detailed DM response:")
        
        return "\n".join(prompt_parts)
    
    async def _load_session_context(self):
        """Load relevant context for the current session."""
        if not self.current_session:
            return
        
        # Load recent sessions for this character
        recent_sessions = await self.database.get_recent_sessions(
            self.current_session['character_id'],
            limit=5
        )
        
        # Load campaign memories if applicable
        if self.current_session.get('campaign_id'):
            campaign_memories = await self.vector_store.get_campaign_memories(
                self.current_session['campaign_id'],
                limit=10
            )
            self.campaign_memory.extend(campaign_memories)
    
    async def end_session(self):
        """End the current session and clean up."""
        if not self.current_session:
            return
        
        self.logger.info(f"Ending session {self.current_session['id']}")
        
        # Update session end time
        await self.database.end_session(self.current_session['id'])
        
        # Clear session state
        self.current_session = None
        self.active_character = None
        self.session_memory.clear()
        self.campaign_memory.clear()
        self.campaign_context.clear()
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session."""
        if not self.current_session:
            return {}
        
        return {
            'session_id': self.current_session['id'],
            'character': self.active_character.get('name', 'Unknown') if self.active_character else None,
            'actions_taken': len([m for m in self.session_memory if m['type'] == 'player_action']),
            'session_length': asyncio.get_event_loop().time() - self.current_session['start_time'],
            'campaign': self.campaign_context.get('name', 'Custom Adventure') if self.campaign_context else None
        }