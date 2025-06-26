"""
Database management for the AI Dungeon Master.
Handles SQLite operations for persistent storage.
"""

import aiosqlite
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from utils.config import Config


class DatabaseManager:
    """Manages SQLite database operations for the AI Dungeon Master."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.database_path
        self.logger = logging.getLogger("database")
        
    async def initialize(self):
        """Initialize the database and create tables."""
        self.logger.info(f"Initializing database at {self.db_path}")
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
            
        self.logger.info("Database initialization complete")
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all necessary database tables."""
        
        # Characters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                race TEXT NOT NULL,
                background TEXT,
                stats TEXT,  -- JSON of ability scores
                skills TEXT, -- JSON of skills
                equipment TEXT, -- JSON of equipment
                spells TEXT, -- JSON of spells
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Campaigns table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                source_file TEXT, -- Path to original campaign file
                source_type TEXT, -- pdf, txt, roll20, etc.
                content TEXT, -- Processed campaign content
                metadata TEXT, -- JSON metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sessions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                campaign_id TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                session_notes TEXT,
                FOREIGN KEY (character_id) REFERENCES characters (id),
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
            )
        """)
        
        # Actions table - stores all player actions and DM responses
        await db.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_type TEXT NOT NULL, -- 'player_action' or 'dm_response'
                content TEXT NOT NULL,
                context TEXT, -- JSON context data
                dice_rolls TEXT, -- JSON of any dice rolls
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        
        # NPCs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS npcs (
                id TEXT PRIMARY KEY,
                campaign_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                stats TEXT, -- JSON of NPC stats
                relationship TEXT, -- Relationship with party
                location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
            )
        """)
        
        # Locations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                campaign_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                map_data TEXT, -- JSON map information
                connections TEXT, -- JSON of connected locations
                encounters TEXT, -- JSON of possible encounters
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
            )
        """)
        
        # Items table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL, -- weapon, armor, consumable, etc.
                description TEXT,
                stats TEXT, -- JSON item stats
                rarity TEXT,
                value INTEGER, -- Gold piece value
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Character inventory junction table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS character_inventory (
                character_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                equipped BOOLEAN DEFAULT FALSE,
                notes TEXT,
                PRIMARY KEY (character_id, item_id),
                FOREIGN KEY (character_id) REFERENCES characters (id),
                FOREIGN KEY (item_id) REFERENCES items (id)
            )
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_character ON sessions (character_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_actions_session ON actions (session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions (timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_npcs_campaign ON npcs (campaign_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_locations_campaign ON locations (campaign_id)")
    
    # Character methods
    async def create_character(self, character_data: Dict[str, Any]) -> str:
        """Create a new character."""
        character_id = character_data.get('id') or f"char_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO characters (
                    id, name, class, level, race, background, 
                    stats, skills, equipment, spells, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                character_id,
                character_data.get('name', ''),
                character_data.get('class', ''),
                character_data.get('level', 1),
                character_data.get('race', ''),
                character_data.get('background', ''),
                json.dumps(character_data.get('stats', {})),
                json.dumps(character_data.get('skills', {})),
                json.dumps(character_data.get('equipment', {})),
                json.dumps(character_data.get('spells', {})),
                character_data.get('notes', '')
            ))
            await db.commit()
        
        return character_id
    
    async def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM characters WHERE id = ?", (character_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    character = dict(row)
                    # Parse JSON fields
                    for field in ['stats', 'skills', 'equipment', 'spells']:
                        if character[field]:
                            character[field] = json.loads(character[field])
                    return character
                return None
    
    async def update_character(self, character_id: str, updates: Dict[str, Any]):
        """Update character data."""
        # Prepare JSON fields
        json_fields = ['stats', 'skills', 'equipment', 'spells']
        for field in json_fields:
            if field in updates and isinstance(updates[field], dict):
                updates[field] = json.dumps(updates[field])
        
        # Build update query
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [character_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE characters 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            await db.commit()
    
    async def list_characters(self) -> List[Dict[str, Any]]:
        """List all characters."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, class, level, race, created_at FROM characters ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # Campaign methods
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> str:
        """Create a new campaign."""
        campaign_id = campaign_data.get('id') or f"camp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO campaigns (
                    id, name, description, source_file, source_type, content, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_id,
                campaign_data.get('name', ''),
                campaign_data.get('description', ''),
                campaign_data.get('source_file', ''),
                campaign_data.get('source_type', ''),
                campaign_data.get('content', ''),
                json.dumps(campaign_data.get('metadata', {}))
            ))
            await db.commit()
        
        return campaign_id
    
    async def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    campaign = dict(row)
                    if campaign['metadata']:
                        campaign['metadata'] = json.loads(campaign['metadata'])
                    return campaign
                return None
    
    # Session methods
    async def create_session(self, character_id: str, campaign_id: Optional[str] = None) -> str:
        """Create a new game session."""
        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO sessions (id, character_id, campaign_id)
                VALUES (?, ?, ?)
            """, (session_id, character_id, campaign_id))
            await db.commit()
        
        return session_id
    
    async def end_session(self, session_id: str):
        """End a session by setting the end time."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET end_time = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (session_id,))
            await db.commit()
    
    async def get_recent_sessions(self, character_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for a character."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sessions 
                WHERE character_id = ? 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (character_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # Action methods
    async def log_action(self, session_id: str, player_action: str, dm_response: str, 
                        context: Optional[Dict[str, Any]] = None, 
                        dice_rolls: Optional[List[Dict[str, Any]]] = None):
        """Log a player action and DM response."""
        async with aiosqlite.connect(self.db_path) as db:
            # Log player action
            await db.execute("""
                INSERT INTO actions (session_id, action_type, content, context, dice_rolls)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, 
                'player_action', 
                player_action,
                json.dumps(context or {}),
                json.dumps(dice_rolls or [])
            ))
            
            # Log DM response
            await db.execute("""
                INSERT INTO actions (session_id, action_type, content, context)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                'dm_response',
                dm_response,
                json.dumps(context or {})
            ))
            
            await db.commit()
    
    async def get_session_actions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all actions for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM actions 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,)) as cursor:
                rows = await cursor.fetchall()
                
                actions = []
                for row in rows:
                    action = dict(row)
                    if action['context']:
                        action['context'] = json.loads(action['context'])
                    if action['dice_rolls']:
                        action['dice_rolls'] = json.loads(action['dice_rolls'])
                    actions.append(action)
                
                return actions
    
    # Utility methods
    async def cleanup_old_data(self, days_old: int = 30):
        """Clean up old session data."""
        async with aiosqlite.connect(self.db_path) as db:
            # Delete old actions first (foreign key constraint)
            await db.execute("""
                DELETE FROM actions 
                WHERE session_id IN (
                    SELECT id FROM sessions 
                    WHERE start_time < datetime('now', '-{} days')
                )
            """.format(days_old))
            
            # Delete old sessions
            await db.execute("""
                DELETE FROM sessions 
                WHERE start_time < datetime('now', '-{} days')
            """.format(days_old))
            
            await db.commit()
    
    async def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            tables = ['characters', 'campaigns', 'sessions', 'actions', 'npcs', 'locations', 'items']
            
            for table in tables:
                async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                    count = await cursor.fetchone()
                    stats[table] = count[0]
        
        return stats