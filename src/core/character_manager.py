"""
Character management system for D&D 5e characters.
Handles character creation, progression, and management.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from data.database import DatabaseManager
from game.dice import DiceRoller, DiceType
from utils.config import Config


class CharacterClass(Enum):
    """D&D 5e character classes."""
    BARBARIAN = "Barbarian"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    FIGHTER = "Fighter"
    MONK = "Monk"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    ROGUE = "Rogue"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"


class CharacterRace(Enum):
    """D&D 5e character races."""
    HUMAN = "Human"
    ELF = "Elf"
    DWARF = "Dwarf"
    HALFLING = "Halfling"
    DRAGONBORN = "Dragonborn"
    GNOME = "Gnome"
    HALF_ELF = "Half-Elf"
    HALF_ORC = "Half-Orc"
    TIEFLING = "Tiefling"


class Background(Enum):
    """D&D 5e character backgrounds."""
    ACOLYTE = "Acolyte"
    CRIMINAL = "Criminal"
    FOLK_HERO = "Folk Hero"
    NOBLE = "Noble"
    SAGE = "Sage"
    SOLDIER = "Soldier"
    CHARLATAN = "Charlatan"
    ENTERTAINER = "Entertainer"
    GUILD_ARTISAN = "Guild Artisan"
    HERMIT = "Hermit"
    OUTLANDER = "Outlander"
    SAILOR = "Sailor"


@dataclass
class AbilityScores:
    """Character ability scores."""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    def get_modifier(self, ability: str) -> int:
        """Get ability modifier."""
        score = getattr(self, ability.lower())
        return (score - 10) // 2
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Character:
    """Complete D&D 5e character."""
    id: str
    name: str
    race: CharacterRace
    character_class: CharacterClass
    background: Background
    level: int = 1
    ability_scores: AbilityScores = None
    hit_points: int = 0
    max_hit_points: int = 0
    armor_class: int = 10
    proficiency_bonus: int = 2
    skills: Dict[str, bool] = None
    equipment: List[str] = None
    spells: Dict[str, List[str]] = None
    notes: str = ""
    experience_points: int = 0
    
    def __post_init__(self):
        if self.ability_scores is None:
            self.ability_scores = AbilityScores()
        if self.skills is None:
            self.skills = {}
        if self.equipment is None:
            self.equipment = []
        if self.spells is None:
            self.spells = {}
    
    def get_proficiency_bonus(self) -> int:
        """Get proficiency bonus based on level."""
        return 2 + ((self.level - 1) // 4)
    
    def get_skill_bonus(self, skill: str, ability: str) -> int:
        """Get skill bonus (ability modifier + proficiency if proficient)."""
        modifier = self.ability_scores.get_modifier(ability)
        proficient = self.skills.get(skill, False)
        
        bonus = modifier
        if proficient:
            bonus += self.get_proficiency_bonus()
        
        return bonus
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for storage."""
        return {
            'id': self.id,
            'name': self.name,
            'race': self.race.value,
            'class': self.character_class.value,
            'background': self.background.value,
            'level': self.level,
            'stats': self.ability_scores.to_dict(),
            'hit_points': self.hit_points,
            'max_hit_points': self.max_hit_points,
            'armor_class': self.armor_class,
            'skills': self.skills,
            'equipment': self.equipment,
            'spells': self.spells,
            'notes': self.notes,
            'experience_points': self.experience_points
        }


class CharacterManager:
    """Manages character creation and progression."""
    
    def __init__(self, config: Config, database: DatabaseManager):
        self.config = config
        self.database = database
        self.dice_roller = DiceRoller(animate=config.dice_animation)
        self.logger = logging.getLogger("character_manager")
        
        # D&D 5e data
        self.class_hit_dice = {
            CharacterClass.BARBARIAN: DiceType.D12,
            CharacterClass.FIGHTER: DiceType.D10,
            CharacterClass.PALADIN: DiceType.D10,
            CharacterClass.RANGER: DiceType.D10,
            CharacterClass.BARD: DiceType.D8,
            CharacterClass.CLERIC: DiceType.D8,
            CharacterClass.DRUID: DiceType.D8,
            CharacterClass.MONK: DiceType.D8,
            CharacterClass.ROGUE: DiceType.D8,
            CharacterClass.WARLOCK: DiceType.D8,
            CharacterClass.SORCERER: DiceType.D6,
            CharacterClass.WIZARD: DiceType.D6
        }
        
        self.class_skills = {
            CharacterClass.BARBARIAN: ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
            CharacterClass.BARD: ["Deception", "History", "Investigation", "Persuasion", "Performance", "Sleight of Hand"],
            CharacterClass.CLERIC: ["History", "Insight", "Medicine", "Persuasion", "Religion"],
            CharacterClass.DRUID: ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
            CharacterClass.FIGHTER: ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
            CharacterClass.MONK: ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
            CharacterClass.PALADIN: ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
            CharacterClass.RANGER: ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
            CharacterClass.ROGUE: ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
            CharacterClass.SORCERER: ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
            CharacterClass.WARLOCK: ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
            CharacterClass.WIZARD: ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"]
        }
        
        # Skill to ability mapping
        self.skill_abilities = {
            "Acrobatics": "dexterity",
            "Animal Handling": "wisdom",
            "Arcana": "intelligence",
            "Athletics": "strength",
            "Deception": "charisma",
            "History": "intelligence",
            "Insight": "wisdom",
            "Intimidation": "charisma",
            "Investigation": "intelligence",
            "Medicine": "wisdom",
            "Nature": "intelligence",
            "Perception": "wisdom",
            "Performance": "charisma",
            "Persuasion": "charisma",
            "Religion": "intelligence",
            "Sleight of Hand": "dexterity",
            "Stealth": "dexterity",
            "Survival": "wisdom"
        }
    
    async def create_character_interactive(self) -> Character:
        """Create a character through interactive prompts."""
        from rich.prompt import Prompt, Confirm
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # Character name
        name = Prompt.ask("Character name")
        
        # Character race
        console.print("\n[cyan]Available Races:[/cyan]")
        race_table = Table(show_header=False)
        race_table.add_column("Number", style="cyan")
        race_table.add_column("Race", style="white")
        
        races = list(CharacterRace)
        for i, race in enumerate(races, 1):
            race_table.add_row(str(i), race.value)
        
        console.print(race_table)
        
        race_choice = int(Prompt.ask(
            "Choose race",
            choices=[str(i) for i in range(1, len(races) + 1)]
        )) - 1
        race = races[race_choice]
        
        # Character class
        console.print("\n[cyan]Available Classes:[/cyan]")
        class_table = Table(show_header=False)
        class_table.add_column("Number", style="cyan")
        class_table.add_column("Class", style="white")
        class_table.add_column("Hit Die", style="dim")
        
        classes = list(CharacterClass)
        for i, char_class in enumerate(classes, 1):
            hit_die = self.class_hit_dice[char_class]
            class_table.add_row(str(i), char_class.value, f"d{hit_die.value}")
        
        console.print(class_table)
        
        class_choice = int(Prompt.ask(
            "Choose class",
            choices=[str(i) for i in range(1, len(classes) + 1)]
        )) - 1
        character_class = classes[class_choice]
        
        # Background
        console.print("\n[cyan]Available Backgrounds:[/cyan]")
        bg_table = Table(show_header=False)
        bg_table.add_column("Number", style="cyan")
        bg_table.add_column("Background", style="white")
        
        backgrounds = list(Background)
        for i, bg in enumerate(backgrounds, 1):
            bg_table.add_row(str(i), bg.value)
        
        console.print(bg_table)
        
        bg_choice = int(Prompt.ask(
            "Choose background",
            choices=[str(i) for i in range(1, len(backgrounds) + 1)]
        )) - 1
        background = backgrounds[bg_choice]
        
        # Generate character ID
        import datetime
        char_id = f"char_{name.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create character
        character = Character(
            id=char_id,
            name=name,
            race=race,
            character_class=character_class,
            background=background
        )
        
        # Generate ability scores
        if Confirm.ask("\nRoll ability scores? (Otherwise use standard array)"):
            stats = self.dice_roller.roll_stats()
            character.ability_scores = AbilityScores(**{
                k.lower().replace(' ', '_'): v for k, v in stats.items()
            })
            console.print("\n[green]Rolled ability scores:[/green]")
            self.dice_roller.display_stats_roll(stats)
        else:
            # Standard array: 15, 14, 13, 12, 10, 8
            console.print("\n[cyan]Assign standard array [15, 14, 13, 12, 10, 8] to abilities:[/cyan]")
            standard_scores = [15, 14, 13, 12, 10, 8]
            abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
            
            assigned_scores = {}
            available_scores = standard_scores.copy()
            
            for ability in abilities:
                console.print(f"\nAvailable scores: {available_scores}")
                score_choice = int(Prompt.ask(
                    f"Assign score to {ability.title()}",
                    choices=[str(s) for s in available_scores]
                ))
                assigned_scores[ability] = score_choice
                available_scores.remove(score_choice)
            
            character.ability_scores = AbilityScores(**assigned_scores)
        
        # Calculate hit points
        character.max_hit_points = self._calculate_hit_points(character, 1)
        character.hit_points = character.max_hit_points
        
        # Calculate armor class (base 10 + Dex modifier)
        character.armor_class = 10 + character.ability_scores.get_modifier("dexterity")
        
        # Select skills
        await self._select_skills(character, console)
        
        # Starting equipment (simplified)
        character.equipment = self._get_starting_equipment(character_class)
        
        # Save character
        await self.database.create_character(character.to_dict())
        
        console.print(f"\n[green]Character '{name}' created successfully![/green]")
        return character
    
    async def _select_skills(self, character: Character, console):
        """Select character skills."""
        from rich.prompt import Prompt
        
        available_skills = self.class_skills[character.character_class]
        
        # Number of skill proficiencies varies by class
        skill_count = 2
        if character.character_class in [CharacterClass.BARD, CharacterClass.RANGER, CharacterClass.ROGUE]:
            skill_count = 4
        elif character.character_class in [CharacterClass.DRUID]:
            skill_count = 2
        
        console.print(f"\n[cyan]Choose {skill_count} skill proficiencies:[/cyan]")
        
        for i, skill in enumerate(available_skills, 1):
            ability = self.skill_abilities[skill]
            modifier = character.ability_scores.get_modifier(ability)
            console.print(f"{i:2}. {skill} ({ability.title()}: {modifier:+d})")
        
        selected_skills = []
        for i in range(skill_count):
            while True:
                choice = int(Prompt.ask(
                    f"Choose skill {i+1}",
                    choices=[str(j) for j in range(1, len(available_skills) + 1)]
                )) - 1
                
                skill = available_skills[choice]
                if skill not in selected_skills:
                    selected_skills.append(skill)
                    character.skills[skill] = True
                    break
                else:
                    console.print("[red]Skill already selected![/red]")
    
    def _calculate_hit_points(self, character: Character, level: int) -> int:
        """Calculate hit points for character at given level."""
        hit_die = self.class_hit_dice[character.character_class]
        con_modifier = character.ability_scores.get_modifier("constitution")
        
        # First level: max hit die + CON modifier
        if level == 1:
            return hit_die.value + con_modifier
        
        # Additional levels: average of hit die + CON modifier per level
        base_hp = hit_die.value + con_modifier
        additional_hp = (level - 1) * ((hit_die.value // 2) + 1 + con_modifier)
        
        return base_hp + additional_hp
    
    def _get_starting_equipment(self, character_class: CharacterClass) -> List[str]:
        """Get starting equipment for character class."""
        equipment = ["Backpack", "Rations (2 days)", "Waterskin", "Bedroll", "Mess kit", "Tinderbox", "10 torches", "10 days of rations", "50 feet of hempen rope"]
        
        class_equipment = {
            CharacterClass.FIGHTER: ["Chain mail", "Shield", "Longsword", "Light crossbow", "20 bolts"],
            CharacterClass.WIZARD: ["Dagger", "Spellbook", "Component pouch", "Scholar's pack"],
            CharacterClass.ROGUE: ["Leather armor", "Shortsword", "Shortbow", "20 arrows", "Thieves' tools"],
            CharacterClass.CLERIC: ["Scale mail", "Shield", "Warhammer", "Light crossbow", "20 bolts", "Holy symbol"],
            CharacterClass.BARBARIAN: ["Greataxe", "Handaxe (2)", "Javelin (4)", "Explorer's pack"],
            CharacterClass.BARD: ["Leather armor", "Dagger", "Rapier", "Lute", "Entertainer's pack"],
            CharacterClass.DRUID: ["Leather armor", "Shield", "Scimitar", "Dart (4)", "Herbalism kit"],
            CharacterClass.MONK: ["Shortsword", "Dart (10)", "Dungeoneer's pack"],
            CharacterClass.PALADIN: ["Chain mail", "Shield", "Longsword", "Javelin (5)", "Holy symbol"],
            CharacterClass.RANGER: ["Scale mail", "Shortsword (2)", "Longbow", "20 arrows", "Explorer's pack"],
            CharacterClass.SORCERER: ["Light crossbow", "20 bolts", "Dagger (2)", "Component pouch", "Dungeoneer's pack"],
            CharacterClass.WARLOCK: ["Light armor", "Simple weapon", "Light crossbow", "20 bolts", "Component pouch"]
        }
        
        equipment.extend(class_equipment.get(character_class, []))
        return equipment
    
    async def load_character(self, character_id: str) -> Optional[Character]:
        """Load character from database."""
        char_data = await self.database.get_character(character_id)
        if not char_data:
            return None
        
        # Convert database data back to Character object
        character = Character(
            id=char_data['id'],
            name=char_data['name'],
            race=CharacterRace(char_data['race']),
            character_class=CharacterClass(char_data['class']),
            background=Background(char_data['background']),
            level=char_data['level'],
            ability_scores=AbilityScores(**char_data['stats']),
            hit_points=char_data.get('hit_points', 0),
            max_hit_points=char_data.get('max_hit_points', 0),
            armor_class=char_data.get('armor_class', 10),
            skills=char_data.get('skills', {}),
            equipment=char_data.get('equipment', []),
            spells=char_data.get('spells', {}),
            notes=char_data.get('notes', ''),
            experience_points=char_data.get('experience_points', 0)
        )
        
        return character
    
    async def save_character(self, character: Character):
        """Save character to database."""
        await self.database.update_character(character.id, character.to_dict())
    
    async def level_up_character(self, character: Character) -> Character:
        """Level up a character."""
        if character.level >= 20:
            self.logger.warning(f"Character {character.name} is already at max level")
            return character
        
        character.level += 1
        
        # Increase hit points
        hit_die = self.class_hit_dice[character.character_class]
        con_modifier = character.ability_scores.get_modifier("constitution")
        
        # Roll for hit points or take average
        from rich.prompt import Confirm
        if Confirm.ask(f"Roll for hit points (d{hit_die.value} + {con_modifier}) or take average ({(hit_die.value // 2) + 1 + con_modifier})?"):
            hp_roll = self.dice_roller.roll_die(hit_die, con_modifier)
            hp_gained = max(1, hp_roll.total)  # Minimum 1 HP per level
            self.dice_roller.display_roll_result(hp_roll)
        else:
            hp_gained = (hit_die.value // 2) + 1 + con_modifier
        
        character.max_hit_points += hp_gained
        character.hit_points += hp_gained
        
        # Update proficiency bonus
        character.proficiency_bonus = character.get_proficiency_bonus()
        
        # Save changes
        await self.save_character(character)
        
        self.logger.info(f"Character {character.name} leveled up to level {character.level}")
        return character
    
    async def list_characters(self) -> List[Dict[str, Any]]:
        """List all characters."""
        return await self.database.list_characters()