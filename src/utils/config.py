"""
Configuration management for the AI Dungeon Master.
Handles settings, environment variables, and configuration files.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class Config(BaseModel):
    """Configuration model for the AI Dungeon Master."""
    
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    campaigns_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "campaigns")
    characters_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "characters")
    
    # Database
    database_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "dm.db")
    vector_db_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "chroma_db")
    
    # AI Configuration
    ollama_url: str = Field(default="http://localhost:11434")
    ai_model: str = Field(default="llama3.1")
    max_context_length: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    
    # Game Settings
    auto_save_frequency: int = Field(default=5)  # Save every N actions
    dice_animation: bool = Field(default=True)
    show_dice_details: bool = Field(default=True)
    
    # UI Settings
    theme: str = Field(default="dark")
    show_help_hints: bool = Field(default=True)
    confirm_dangerous_actions: bool = Field(default=True)
    
    # Advanced Settings
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    max_memory_entries: int = Field(default=1000)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_config()
        self._ensure_directories()
    
    def _load_config(self):
        """Load configuration from various sources."""
        # Load from .env file
        load_dotenv(self.project_root / ".env")
        
        # Override with environment variables
        self._load_from_env()
        
        # Load from config file if it exists
        config_file = self.project_root / "config.yaml"
        if config_file.exists():
            self._load_from_file(config_file)
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        env_mappings = {
            "OLLAMA_URL": "ollama_url",
            "AI_MODEL": "ai_model",
            "DATABASE_PATH": "database_path",
            "DEBUG_MODE": "debug_mode",
            "LOG_LEVEL": "log_level",
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle boolean values
                if config_key in ["debug_mode", "dice_animation", "show_dice_details"]:
                    value = value.lower() in ("true", "1", "yes", "on")
                # Handle integer values
                elif config_key in ["max_context_length", "auto_save_frequency", "max_memory_entries"]:
                    value = int(value)
                # Handle float values
                elif config_key in ["temperature"]:
                    value = float(value)
                # Handle Path values
                elif config_key in ["database_path", "vector_db_path"]:
                    value = Path(value)
                
                setattr(self, config_key, value)
    
    def _load_from_file(self, config_file: Path):
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                for key, value in config_data.items():
                    if hasattr(self, key):
                        # Handle Path values
                        if key.endswith("_path") or key.endswith("_dir"):
                            value = Path(value)
                        setattr(self, key, value)
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.campaigns_dir,
            self.characters_dir,
            self.vector_db_path.parent if self.vector_db_path else None
        ]
        
        for directory in directories:
            if directory and not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
    
    def save_config(self, config_file: Optional[Path] = None):
        """Save current configuration to file."""
        if config_file is None:
            config_file = self.project_root / "config.yaml"
        
        config_dict = self.model_dump()
        
        # Convert Path objects to strings for YAML serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
        
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)
        except Exception as e:
            print(f"Error saving config to {config_file}: {e}")
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama-specific configuration."""
        return {
            "url": self.ollama_url,
            "model": self.ai_model,
            "max_context_length": self.max_context_length,
            "temperature": self.temperature,
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database-specific configuration."""
        return {
            "database_path": str(self.database_path),
            "vector_db_path": str(self.vector_db_path),
        }
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return self.debug_mode or self.log_level.upper() == "DEBUG"