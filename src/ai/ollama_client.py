"""
Ollama API client for AI interactions.
Handles communication with local Ollama instance for generating DM responses.
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from urllib.parse import urljoin

from utils.config import Config


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.ollama_url.rstrip('/')
        self.model = config.ai_model
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("ollama_client")
        
    async def initialize(self):
        """Initialize the Ollama client and check connection."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes for longer responses
        )
        
        try:
            # Check if Ollama is running
            await self._check_connection()
            
            # Check if model is available
            await self._ensure_model_available()
            
            self.logger.info(f"Ollama client initialized with model: {self.model}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama client: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def _check_connection(self):
        """Check if Ollama server is accessible."""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    raise ConnectionError(f"Ollama server returned status {response.status}")
                
                data = await response.json()
                self.logger.info(f"Connected to Ollama. Available models: {len(data.get('models', []))}")
                
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
    
    async def _ensure_model_available(self):
        """Ensure the specified model is available, pull if necessary."""
        available_models = await self.list_models()
        
        if not any(model['name'].startswith(self.model) for model in available_models):
            self.logger.info(f"Model {self.model} not found locally. Attempting to pull...")
            await self.pull_model(self.model)
        else:
            self.logger.info(f"Model {self.model} is available")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        async with self.session.get(f"{self.base_url}/api/tags") as response:
            if response.status != 200:
                raise Exception(f"Failed to list models: {response.status}")
            
            data = await response.json()
            return data.get('models', [])
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        self.logger.info(f"Pulling model: {model_name}")
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to pull model: {response.status}")
                
                # Stream the pull progress
                async for line in response.content:
                    if line:
                        try:
                            progress = json.loads(line.decode())
                            if 'status' in progress:
                                self.logger.info(f"Pull progress: {progress['status']}")
                        except json.JSONDecodeError:
                            continue
                
                self.logger.info(f"Successfully pulled model: {model_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the AI model."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_ctx": kwargs.get("max_tokens", self.config.max_context_length),
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error {response.status}: {error_text}")
                
                data = await response.json()
                return data.get('response', '').strip()
                
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            raise
    
    async def generate_streaming_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the AI model."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_ctx": kwargs.get("max_tokens", self.config.max_context_length),
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error {response.status}: {error_text}")
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode())
                            if 'response' in data:
                                yield data['response']
                            
                            # Check if generation is complete
                            if data.get('done', False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
        except Exception as e:
            self.logger.error(f"Failed to generate streaming response: {e}")
            raise
    
    async def generate_dm_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a specialized DM response with structured output."""
        
        # Enhanced prompt for DM-specific responses
        dm_prompt = self._build_dm_prompt(prompt, context)
        
        try:
            # Generate the response
            response = await self.generate_response(dm_prompt)
            
            # Parse and structure the response
            structured_response = self._parse_dm_response(response)
            
            return structured_response
            
        except Exception as e:
            self.logger.error(f"Failed to generate DM response: {e}")
            return {
                "narrative": "The DM pauses, deep in thought...",
                "action_required": False,
                "dice_needed": [],
                "metadata": {"error": str(e)}
            }
    
    def _build_dm_prompt(self, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build an enhanced prompt for DM responses."""
        prompt_parts = [
            "You are an expert Dungeon Master for D&D 5th Edition. You create immersive, engaging narratives and follow the rules accurately.",
            "",
            "Response Format:",
            "- Provide vivid, descriptive narrative",
            "- If dice rolls are needed, specify them clearly (e.g., 'Roll a d20 for Investigation')",
            "- Keep responses engaging but not overly long",
            "- Follow D&D 5e rules precisely",
            "- Remember that player choices have permanent consequences",
            "",
        ]
        
        if context:
            if context.get('character'):
                prompt_parts.append(f"Player Character: {context['character']}")
            if context.get('location'):
                prompt_parts.append(f"Current Location: {context['location']}")
            if context.get('recent_events'):
                prompt_parts.append(f"Recent Events: {context['recent_events']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            f"Player Action/Question: {user_prompt}",
            "",
            "Provide your DM response:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_dm_response(self, response: str) -> Dict[str, Any]:
        """Parse DM response and extract structured information."""
        # Basic parsing - can be enhanced with more sophisticated NLP
        
        # Check for dice roll requests
        dice_patterns = [
            "roll a d", "make a", "roll for", "d20", "d12", "d10", "d8", "d6", "d4"
        ]
        
        dice_needed = []
        for pattern in dice_patterns:
            if pattern.lower() in response.lower():
                # Extract dice information (simplified)
                if "d20" in response.lower():
                    dice_needed.append({"type": "d20", "reason": "skill check or attack"})
                break
        
        # Check if immediate action is required
        action_required = any(keyword in response.lower() for keyword in [
            "roll", "choose", "decide", "what do you", "make a"
        ])
        
        return {
            "narrative": response.strip(),
            "action_required": action_required,
            "dice_needed": dice_needed,
            "metadata": {
                "model": self.model,
                "length": len(response),
                "has_dice_request": len(dice_needed) > 0
            }
        }
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("Ollama client session closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()