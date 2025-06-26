"""
Campaign parsing system for various file formats.
Supports PDF, plain text, and Roll20 campaign exports.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json
import re
from abc import ABC, abstractmethod

import PyPDF2
from bs4 import BeautifulSoup


@dataclass
class ParsedCampaign:
    """Represents a parsed campaign with structured data."""
    name: str
    description: str
    content: str
    npcs: List[Dict[str, Any]]
    locations: List[Dict[str, Any]]
    encounters: List[Dict[str, Any]]
    items: List[Dict[str, Any]]
    plot_hooks: List[str]
    metadata: Dict[str, Any]


class BaseCampaignParser(ABC):
    """Base class for campaign parsers."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"parser.{self.__class__.__name__}")
    
    @abstractmethod
    async def parse(self, file_path: Path) -> ParsedCampaign:
        """Parse a campaign file and return structured data."""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    def _extract_npcs(self, text: str) -> List[Dict[str, Any]]:
        """Extract NPC information from text."""
        npcs = []
        
        # Common NPC patterns
        npc_patterns = [
            r'(?:NPC|Character):\s*([A-Z][a-zA-Z\s]+)',
            r'([A-Z][a-zA-Z\s]+)(?:\s*\([^)]+\))?\s*(?:is|was|works|lives)',
            r'(?:meet|encounter|find)\s+([A-Z][a-zA-Z\s]+)',
        ]
        
        for pattern in npc_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 50:  # Reasonable name length
                    # Extract context around the name
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 200)
                    context = text[start:end].strip()
                    
                    npcs.append({
                        'name': name,
                        'description': context,
                        'type': 'npc'
                    })
        
        # Remove duplicates based on name similarity
        unique_npcs = []
        for npc in npcs:
            if not any(npc['name'].lower() in existing['name'].lower() or 
                      existing['name'].lower() in npc['name'].lower() 
                      for existing in unique_npcs):
                unique_npcs.append(npc)
        
        return unique_npcs[:20]  # Limit to 20 NPCs
    
    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """Extract location information from text."""
        locations = []
        
        # Location patterns
        location_patterns = [
            r'(?:Location|Place|Area|Room|Town|City|Village|Dungeon):\s*([A-Z][a-zA-Z\s]+)',
            r'(?:in|at|near|the)\s+([A-Z][a-zA-Z\s]+(?:Tower|Castle|Inn|Tavern|Forest|Mountain|Cave|Temple|Ruins))',
            r'([A-Z][a-zA-Z\s]+(?:Hall|Chamber|Corridor|Bridge|Gate|Square|Market))',
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 50:
                    # Extract context
                    start = max(0, match.start() - 150)
                    end = min(len(text), match.end() + 250)
                    context = text[start:end].strip()
                    
                    locations.append({
                        'name': name,
                        'description': context,
                        'type': 'location'
                    })
        
        # Remove duplicates
        unique_locations = []
        for loc in locations:
            if not any(loc['name'].lower() in existing['name'].lower() or 
                      existing['name'].lower() in loc['name'].lower() 
                      for existing in unique_locations):
                unique_locations.append(loc)
        
        return unique_locations[:15]  # Limit to 15 locations
    
    def _extract_encounters(self, text: str) -> List[Dict[str, Any]]:
        """Extract encounter information from text."""
        encounters = []
        
        # Encounter patterns
        encounter_patterns = [
            r'(?:Encounter|Combat|Fight|Battle):\s*([^\n]+)',
            r'(?:CR|Challenge Rating)\s*(\d+)',
            r'(\d+)\s*(?:x\s*)?([A-Z][a-zA-Z\s]+)(?:\s*\(CR\s*\d+\))?',
        ]
        
        encounter_sections = re.split(r'(?:Encounter|Combat|Fight|Battle)', text, flags=re.IGNORECASE)
        
        for i, section in enumerate(encounter_sections[1:], 1):  # Skip first empty split
            # Take first 300 characters of section
            encounter_text = section[:300].strip()
            if encounter_text:
                encounters.append({
                    'name': f'Encounter {i}',
                    'description': encounter_text,
                    'type': 'encounter'
                })
        
        return encounters[:10]  # Limit to 10 encounters
    
    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract magic items and treasure from text."""
        items = []
        
        # Item patterns
        item_patterns = [
            r'(?:Item|Treasure|Magic Item|Weapon|Armor):\s*([A-Z][a-zA-Z\s]+)',
            r'([A-Z][a-zA-Z\s]+)(?:\s*\+\d+)?(?:\s*\([^)]+\))?(?:\s*of\s+[A-Z][a-zA-Z\s]+)?',
        ]
        
        # Look for sections that might contain items
        item_sections = re.findall(r'(?:treasure|loot|items?|equipment).*?(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        
        for section in item_sections:
            for pattern in item_patterns:
                matches = re.finditer(pattern, section, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip()
                    if len(name) > 2 and len(name) < 50:
                        # Get surrounding context
                        start = max(0, match.start() - 50)
                        end = min(len(section), match.end() + 100)
                        context = section[start:end].strip()
                        
                        items.append({
                            'name': name,
                            'description': context,
                            'type': 'item'
                        })
        
        # Remove duplicates
        unique_items = []
        for item in items:
            if not any(item['name'].lower() == existing['name'].lower() for existing in unique_items):
                unique_items.append(item)
        
        return unique_items[:20]  # Limit to 20 items
    
    def _extract_plot_hooks(self, text: str) -> List[str]:
        """Extract plot hooks and adventure hooks from text."""
        hooks = []
        
        # Look for hook sections
        hook_patterns = [
            r'(?:Plot Hook|Adventure Hook|Hook):\s*([^\n]+)',
            r'(?:The party|Players|Characters)\s+(?:must|should|need to|are asked to)\s+([^\n.]+)',
        ]
        
        for pattern in hook_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                hook = match.group(1).strip()
                if len(hook) > 10:  # Reasonable hook length
                    hooks.append(hook)
        
        return hooks[:10]  # Limit to 10 hooks


class PDFCampaignParser(BaseCampaignParser):
    """Parser for PDF campaign files."""
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        return file_path.suffix.lower() == '.pdf'
    
    async def parse(self, file_path: Path) -> ParsedCampaign:
        """Parse PDF campaign file."""
        self.logger.info(f"Parsing PDF campaign: {file_path}")
        
        try:
            # Read PDF content
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._extract_pdf_text, file_path)
            
            # Extract structured data
            name = file_path.stem.replace('_', ' ').title()
            
            npcs = self._extract_npcs(text)
            locations = self._extract_locations(text)
            encounters = self._extract_encounters(text)
            items = self._extract_items(text)
            plot_hooks = self._extract_plot_hooks(text)
            
            # Generate description from first paragraph
            paragraphs = text.split('\n\n')
            description = next((p.strip() for p in paragraphs if len(p.strip()) > 50), "")[:500]
            
            return ParsedCampaign(
                name=name,
                description=description,
                content=text,
                npcs=npcs,
                locations=locations,
                encounters=encounters,
                items=items,
                plot_hooks=plot_hooks,
                metadata={
                    'source_type': 'pdf',
                    'source_file': str(file_path),
                    'page_count': len(text.split('\f')),  # Approximate page count
                    'word_count': len(text.split())
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        
        return text


class TextCampaignParser(BaseCampaignParser):
    """Parser for plain text campaign files."""
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if file is plain text."""
        return file_path.suffix.lower() in ['.txt', '.md', '.rst']
    
    async def parse(self, file_path: Path) -> ParsedCampaign:
        """Parse text campaign file."""
        self.logger.info(f"Parsing text campaign: {file_path}")
        
        try:
            # Read text content
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            # Extract structured data
            name = file_path.stem.replace('_', ' ').replace('-', ' ').title()
            
            npcs = self._extract_npcs(text)
            locations = self._extract_locations(text)
            encounters = self._extract_encounters(text)
            items = self._extract_items(text)
            plot_hooks = self._extract_plot_hooks(text)
            
            # Generate description
            lines = text.split('\n')
            description = next((line.strip() for line in lines if len(line.strip()) > 50), "")[:500]
            
            return ParsedCampaign(
                name=name,
                description=description,
                content=text,
                npcs=npcs,
                locations=locations,
                encounters=encounters,
                items=items,
                plot_hooks=plot_hooks,
                metadata={
                    'source_type': 'text',
                    'source_file': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'line_count': len(lines),
                    'word_count': len(text.split())
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse text file {file_path}: {e}")
            raise


class Roll20CampaignParser(BaseCampaignParser):
    """Parser for Roll20 campaign exports."""
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if file is a Roll20 export."""
        if file_path.suffix.lower() == '.json':
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    # Check for Roll20-specific fields
                    return 'campaign' in data or 'characters' in data or 'handouts' in data
            except:
                return False
        return False
    
    async def parse(self, file_path: Path) -> ParsedCampaign:
        """Parse Roll20 campaign export."""
        self.logger.info(f"Parsing Roll20 campaign: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Extract campaign info
            campaign_info = data.get('campaign', {})
            name = campaign_info.get('name', file_path.stem.title())
            description = campaign_info.get('description', '')
            
            # Extract NPCs from characters
            npcs = []
            for char in data.get('characters', []):
                if not char.get('controlledby', '').strip():  # NPCs typically have no controller
                    npcs.append({
                        'name': char.get('name', 'Unknown NPC'),
                        'description': char.get('bio', ''),
                        'stats': char.get('attributes', {}),
                        'type': 'npc'
                    })
            
            # Extract locations from handouts and pages
            locations = []
            for handout in data.get('handouts', []):
                if any(keyword in handout.get('name', '').lower() 
                      for keyword in ['location', 'map', 'area', 'place']):
                    locations.append({
                        'name': handout.get('name', 'Unknown Location'),
                        'description': handout.get('notes', ''),
                        'type': 'location'
                    })
            
            # Extract encounters from handouts
            encounters = []
            for handout in data.get('handouts', []):
                if any(keyword in handout.get('name', '').lower() 
                      for keyword in ['encounter', 'combat', 'fight', 'battle']):
                    encounters.append({
                        'name': handout.get('name', 'Unknown Encounter'),
                        'description': handout.get('notes', ''),
                        'type': 'encounter'
                    })
            
            # Combine all text for content
            all_text = []
            all_text.append(description)
            
            for handout in data.get('handouts', []):
                all_text.append(handout.get('notes', ''))
            
            content = '\n\n'.join(filter(None, all_text))
            
            # Extract additional data from combined content
            items = self._extract_items(content)
            plot_hooks = self._extract_plot_hooks(content)
            
            return ParsedCampaign(
                name=name,
                description=description,
                content=content,
                npcs=npcs,
                locations=locations,
                encounters=encounters,
                items=items,
                plot_hooks=plot_hooks,
                metadata={
                    'source_type': 'roll20',
                    'source_file': str(file_path),
                    'character_count': len(data.get('characters', [])),
                    'handout_count': len(data.get('handouts', [])),
                    'export_version': data.get('version', 'unknown')
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse Roll20 file {file_path}: {e}")
            raise


class CampaignParser:
    """Main campaign parser that delegates to specific parsers."""
    
    def __init__(self):
        self.parsers = [
            PDFCampaignParser(),
            Roll20CampaignParser(),  # Check Roll20 before generic text
            TextCampaignParser(),
        ]
        self.logger = logging.getLogger("campaign_parser")
    
    async def parse_campaign(self, file_path: Union[str, Path]) -> Optional[ParsedCampaign]:
        """Parse a campaign file using the appropriate parser."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Campaign file not found: {file_path}")
        
        # Find appropriate parser
        for parser in self.parsers:
            if parser.can_parse(file_path):
                self.logger.info(f"Using {parser.__class__.__name__} for {file_path}")
                return await parser.parse(file_path)
        
        raise ValueError(f"No parser available for file type: {file_path.suffix}")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return ['.pdf', '.txt', '.md', '.rst', '.json']