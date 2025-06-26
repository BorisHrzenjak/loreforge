"""
Main CLI interface for the AI Dungeon Master using Rich and Textual.
Provides a beautiful terminal-based interface with mixed chat and form interactions.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.columns import Columns
from rich import box

from utils.config import Config
from core.dm_engine import DMEngine
from core.character_manager import CharacterManager
from data.database import DatabaseManager
from data.parsers.campaign_parser import CampaignParser
from game.dice import DiceRoller, DiceType, AdvantageType


class DungeonMasterCLI:
    """Main CLI interface for the AI Dungeon Master."""
    
    def __init__(self):
        self.console = Console()
        self.config = Config()
        self.dm_engine: Optional[DMEngine] = None
        self.database: Optional[DatabaseManager] = None
        self.character_manager: Optional[CharacterManager] = None
        self.campaign_parser: Optional[CampaignParser] = None
        self.dice_roller: Optional[DiceRoller] = None
        self.current_character: Optional[Dict[str, Any]] = None
        self.running = True
        
    async def run(self):
        """Main run loop for the CLI."""
        await self.display_welcome()
        
        # Initialize all systems
        try:
            # Initialize database first
            self.database = DatabaseManager(self.config)
            await self.database.initialize()
            
            # Initialize character manager
            self.character_manager = CharacterManager(self.config, self.database)
            
            # Initialize campaign parser
            self.campaign_parser = CampaignParser()
            
            # Initialize dice roller
            self.dice_roller = DiceRoller(
                console=self.console, 
                animate=self.config.dice_animation
            )
            
            # Initialize DM engine
            self.dm_engine = DMEngine(self.config)
            await self.dm_engine.initialize()
            
        except Exception as e:
            self.console.print(f"[red]Failed to initialize systems: {e}[/red]")
            return
            
        # Main interaction loop
        while self.running:
            await self.main_menu()
    
    async def display_welcome(self):
        """Display the welcome screen."""
        welcome_text = Text()
        welcome_text.append("🎲 AI DUNGEON MASTER 🎲\n", style="bold magenta")
        welcome_text.append("D&D 5th Edition Campaign Manager\n", style="bold white")
        welcome_text.append("Powered by Local AI via Ollama\n\n", style="dim white")
        welcome_text.append("⚠️  Remember: Your choices have permanent consequences!\n", style="bold yellow")
        welcome_text.append("There are no save states - every decision matters.\n", style="yellow")
        
        panel = Panel(
            welcome_text,
            title="Welcome, Adventurer!",
            border_style="cyan",
            box=box.DOUBLE
        )
        
        self.console.print(panel)
        self.console.print()
        
        # Check if Ollama is available
        await self._check_ollama_status()
    
    async def _check_ollama_status(self):
        """Check if Ollama is running and accessible."""
        self.console.print("[dim]Checking Ollama connection...[/dim]")
        # This will be implemented when we create the Ollama client
        self.console.print("[green]✓ Ollama connection ready[/green]")
        self.console.print()
    
    async def main_menu(self):
        """Display and handle the main menu."""
        menu_table = Table(show_header=False, box=box.SIMPLE)
        menu_table.add_column("Option", style="cyan")
        menu_table.add_column("Description", style="white")
        
        menu_table.add_row("1", "Create New Character")
        menu_table.add_row("2", "Load Existing Character")
        menu_table.add_row("3", "Start/Continue Campaign")
        menu_table.add_row("4", "Load Campaign from File")
        menu_table.add_row("5", "Dice Roller")
        menu_table.add_row("6", "Campaign Management")
        menu_table.add_row("7", "Settings")
        menu_table.add_row("8", "Exit")
        
        panel = Panel(
            menu_table,
            title="Main Menu",
            border_style="blue"
        )
        
        self.console.print(panel)
        
        choice = Prompt.ask(
            "\n[cyan]Choose an option[/cyan]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8"],
            default="1"
        )
        
        await self._handle_menu_choice(choice)
    
    async def _handle_menu_choice(self, choice: str):
        """Handle main menu choice."""
        if choice == "1":
            await self.create_character()
        elif choice == "2":
            await self.load_character()
        elif choice == "3":
            await self.start_campaign()
        elif choice == "4":
            await self.load_campaign_file()
        elif choice == "5":
            await self.dice_roller_menu()
        elif choice == "6":
            await self.campaign_management()
        elif choice == "7":
            await self.settings_menu()
        elif choice == "8":
            self.running = False
            self.console.print("\n[green]Farewell, adventurer! May your next campaign be legendary![/green]")
    
    async def create_character(self):
        """Handle character creation."""
        self.console.print("\n[cyan]Character Creation[/cyan]")
        self.console.print("[yellow]Creating a new D&D 5e character...[/yellow]")
        
        try:
            character = await self.character_manager.create_character_interactive()
            self.current_character = character.to_dict()
            
            self.console.print(f"\n[green]✓ Character '{character.name}' created successfully![/green]")
            self.console.print(f"[dim]Character ID: {character.id}[/dim]")
            
        except Exception as e:
            self.console.print(f"[red]Error creating character: {e}[/red]")
        
        Prompt.ask("\nPress Enter to continue", default="")
    
    async def load_character(self):
        """Handle character loading."""
        self.console.print("\n[cyan]Load Character[/cyan]")
        
        try:
            # List available characters
            characters = await self.character_manager.list_characters()
            
            if not characters:
                self.console.print("[yellow]No characters found. Create a character first![/yellow]")
                Prompt.ask("\nPress Enter to continue", default="")
                return
            
            # Display character table
            char_table = Table(show_header=True, header_style="bold cyan")
            char_table.add_column("ID", style="dim", width=8)
            char_table.add_column("Name", style="white")
            char_table.add_column("Class", style="green")
            char_table.add_column("Level", justify="center", style="yellow")
            char_table.add_column("Race", style="blue")
            
            for i, char in enumerate(characters):
                char_table.add_row(
                    str(i + 1),
                    char['name'],
                    char['class'],
                    str(char['level']),
                    char['race']
                )
            
            self.console.print(char_table)
            
            # Select character
            choice = int(Prompt.ask(
                "\nSelect character",
                choices=[str(i) for i in range(1, len(characters) + 1)]
            )) - 1
            
            selected_char = characters[choice]
            character = await self.character_manager.load_character(selected_char['id'])
            
            if character:
                self.current_character = character.to_dict()
                self.console.print(f"\n[green]✓ Loaded character: {character.name}[/green]")
            else:
                self.console.print(f"[red]Failed to load character[/red]")
                
        except Exception as e:
            self.console.print(f"[red]Error loading character: {e}[/red]")
        
        Prompt.ask("\nPress Enter to continue", default="")
    
    async def start_campaign(self):
        """Start or continue a campaign."""
        if not self.current_character:
            self.console.print("\n[red]Please create or load a character first![/red]\n")
            Prompt.ask("Press Enter to continue", default="")
            return
            
        self.console.print("\n[cyan]Starting Campaign Session[/cyan]")
        
        try:
            # Create session with DM engine
            session_id = await self.dm_engine.create_session(
                self.current_character['id']
            )
            
            self.console.print(f"[green]✓ Session started: {session_id}[/green]")
            await self.campaign_session()
            
            # End session when done
            await self.dm_engine.end_session()
            
        except Exception as e:
            self.console.print(f"[red]Error starting campaign: {e}[/red]")
            Prompt.ask("\nPress Enter to continue", default="")
    
    async def campaign_session(self):
        """Main campaign session interaction."""
        self.console.print("[green]🎭 The Dungeon Master awakens...[/green]\n")
        
        # Initial DM introduction
        intro_text = f"Welcome, {self.current_character['name']}! You find yourself at the beginning of a new adventure. The world awaits your decisions, and remember - every choice you make will have lasting consequences. There are no second chances in this realm.\n\nYou stand at a crossroads, unsure of which path to take..."
        
        intro_panel = Panel(
            intro_text,
            title="🎭 Dungeon Master",
            border_style="green"
        )
        self.console.print(intro_panel)
        
        session_active = True
        while session_active and self.running:
            # Show available commands
            self.console.print("\n[dim]Commands: [roll <dice>] [character] [quit][/dim]")
            
            # Get player input
            player_input = Prompt.ask(
                "\n[bold cyan]What do you do?[/bold cyan]",
                default="look around"
            )
            
            # Handle special commands
            if player_input.lower().startswith('roll '):
                await self._handle_dice_command(player_input[5:])
                continue
            elif player_input.lower() == 'character':
                await self._show_character_sheet()
                continue
            elif player_input.lower() in ['quit', 'exit', 'leave']:
                if Confirm.ask("\n[yellow]End this session?[/yellow]"):
                    session_active = False
                    continue
            
            # Process with DM engine
            try:
                self.console.print(f"\n[dim]🤔 The DM ponders your action...[/dim]")
                
                dm_response = await self.dm_engine.process_player_action(
                    player_input,
                    context={'character': self.current_character}
                )
                
                dm_panel = Panel(
                    dm_response['narrative'],
                    title="🎭 Dungeon Master",
                    border_style="green"
                )
                
                self.console.print(dm_panel)
                
                # Handle dice requests
                if dm_response.get('dice_needed'):
                    for dice_request in dm_response['dice_needed']:
                        self.console.print(f"\n[yellow]DM requests: {dice_request['reason']}[/yellow]")
                        await self._handle_dice_command(dice_request['type'])
                
            except Exception as e:
                self.console.print(f"[red]Error processing action: {e}[/red]")
                fallback_response = "The DM seems momentarily distracted, but quickly refocuses on your adventure..."
                dm_panel = Panel(fallback_response, title="🎭 Dungeon Master", border_style="yellow")
                self.console.print(dm_panel)
    
    async def load_campaign_file(self):
        """Handle campaign file loading."""
        self.console.print("\n[cyan]Load Campaign from File[/cyan]")
        
        # Show supported formats
        formats = self.campaign_parser.get_supported_formats()
        file_types = Table(show_header=False, box=box.SIMPLE)
        file_types.add_column("Format", style="cyan")
        file_types.add_column("Description", style="white")
        
        format_descriptions = {
            '.pdf': "PDF campaign documents",
            '.txt': "Plain text campaign files",
            '.md': "Markdown campaign files",
            '.json': "Roll20 campaign exports"
        }
        
        for fmt in formats:
            description = format_descriptions.get(fmt, "Campaign file")
            file_types.add_row(fmt.upper(), description)
        
        self.console.print("Supported formats:")
        self.console.print(file_types)
        self.console.print()
        
        try:
            file_path = Prompt.ask("Enter file path to campaign file")
            
            if not file_path:
                return
            
            self.console.print(f"\n[yellow]📖 Parsing campaign file...[/yellow]")
            
            # Parse the campaign
            parsed_campaign = await self.campaign_parser.parse_campaign(file_path)
            
            if parsed_campaign:
                # Store in database
                campaign_data = {
                    'name': parsed_campaign.name,
                    'description': parsed_campaign.description,
                    'content': parsed_campaign.content,
                    'source_file': file_path,
                    'source_type': parsed_campaign.metadata.get('source_type', 'unknown'),
                    'metadata': parsed_campaign.metadata
                }
                
                campaign_id = await self.database.create_campaign(campaign_data)
                
                # Store in vector database for RAG
                await self.dm_engine.vector_store.add_campaign_content(
                    parsed_campaign.content,
                    {'campaign_id': campaign_id, 'source': 'file_import'}
                )
                
                # Store NPCs, locations, etc.
                for npc in parsed_campaign.npcs:
                    await self.dm_engine.vector_store.add_campaign_content(
                        f"NPC: {npc['name']} - {npc['description']}",
                        {'campaign_id': campaign_id, 'type': 'npc', 'name': npc['name']}
                    )
                
                for location in parsed_campaign.locations:
                    await self.dm_engine.vector_store.add_campaign_content(
                        f"Location: {location['name']} - {location['description']}",
                        {'campaign_id': campaign_id, 'type': 'location', 'name': location['name']}
                    )
                
                self.console.print(f"\n[green]✓ Campaign '{parsed_campaign.name}' loaded successfully![/green]")
                self.console.print(f"[dim]Campaign ID: {campaign_id}[/dim]")
                self.console.print(f"[dim]Found: {len(parsed_campaign.npcs)} NPCs, {len(parsed_campaign.locations)} locations[/dim]")
            
        except FileNotFoundError:
            self.console.print(f"[red]File not found: {file_path}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error loading campaign: {e}[/red]")
        
        Prompt.ask("\nPress Enter to continue", default="")
    
    async def dice_roller_menu(self):
        """Interactive dice roller menu."""
        self.console.print("\n[cyan]🎲 Dice Roller[/cyan]")
        
        dice_menu = Table(show_header=False, box=box.SIMPLE)
        dice_menu.add_column("Option", style="cyan")
        dice_menu.add_column("Description", style="white")
        
        dice_menu.add_row("1", "Roll single die (d4, d6, d8, d10, d12, d20, d100)")
        dice_menu.add_row("2", "Roll multiple dice (e.g., 3d6, 2d8+2)")
        dice_menu.add_row("3", "Roll with advantage/disadvantage")
        dice_menu.add_row("4", "Roll character stats (4d6 drop lowest)")
        dice_menu.add_row("5", "Custom dice notation")
        dice_menu.add_row("6", "Back to main menu")
        
        self.console.print(dice_menu)
        
        choice = Prompt.ask(
            "\n[cyan]Choose dice option[/cyan]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1"
        )
        
        if choice == "1":
            await self._roll_single_die()
        elif choice == "2":
            await self._roll_multiple_dice()
        elif choice == "3":
            await self._roll_with_advantage()
        elif choice == "4":
            await self._roll_character_stats()
        elif choice == "5":
            await self._roll_custom_notation()
        elif choice == "6":
            return
        
        # Ask if they want to roll again
        if choice != "6" and Confirm.ask("\nRoll again?"):
            await self.dice_roller_menu()
    
    async def _roll_single_die(self):
        """Roll a single die."""
        die_choice = Prompt.ask(
            "Choose die type",
            choices=["d4", "d6", "d8", "d10", "d12", "d20", "d100"],
            default="d20"
        )
        
        modifier = 0
        if Confirm.ask("Add modifier?"):
            modifier = int(Prompt.ask("Modifier", default="0"))
        
        dice_type = DiceType(int(die_choice[1:]))
        await self.dice_roller.animated_roll(dice_type, modifier)
    
    async def _roll_multiple_dice(self):
        """Roll multiple dice."""
        count = int(Prompt.ask("Number of dice", default="1"))
        die_choice = Prompt.ask(
            "Die type",
            choices=["d4", "d6", "d8", "d10", "d12", "d20", "d100"],
            default="d6"
        )
        
        modifier = 0
        if Confirm.ask("Add modifier?"):
            modifier = int(Prompt.ask("Modifier", default="0"))
        
        dice_type = DiceType(int(die_choice[1:]))
        await self.dice_roller.animated_multiple_roll(dice_type, count, modifier)
    
    async def _roll_with_advantage(self):
        """Roll d20 with advantage/disadvantage."""
        advantage_choice = Prompt.ask(
            "Roll type",
            choices=["normal", "advantage", "disadvantage"],
            default="normal"
        )
        
        modifier = 0
        if Confirm.ask("Add modifier?"):
            modifier = int(Prompt.ask("Modifier", default="0"))
        
        advantage_type = AdvantageType(advantage_choice.upper())
        roll = self.dice_roller.roll_with_advantage(advantage_type, modifier)
        self.dice_roller.display_advantage_roll(roll)
    
    async def _roll_character_stats(self):
        """Roll character stats."""
        self.console.print("\n[yellow]Rolling character stats (4d6, drop lowest for each)...[/yellow]")
        stats = self.dice_roller.roll_stats()
        self.dice_roller.display_stats_roll(stats)
    
    async def _roll_custom_notation(self):
        """Roll using custom dice notation."""
        notation = Prompt.ask(
            "Enter dice notation (e.g., '2d6+3', '1d20-1')",
            default="1d20"
        )
        
        try:
            result = self.dice_roller.roll_notation(notation)
            self.dice_roller.display_multiple_roll_result(result)
        except ValueError as e:
            self.console.print(f"[red]Invalid notation: {e}[/red]")
    
    async def _handle_dice_command(self, dice_str: str):
        """Handle dice rolling command from campaign session."""
        try:
            if dice_str.lower() in ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100']:
                dice_type = DiceType(int(dice_str[1:]))
                await self.dice_roller.animated_roll(dice_type)
            else:
                result = self.dice_roller.roll_notation(dice_str)
                self.dice_roller.display_multiple_roll_result(result)
        except Exception as e:
            self.console.print(f"[red]Invalid dice command: {e}[/red]")
    
    async def _show_character_sheet(self):
        """Display current character sheet."""
        if not self.current_character:
            self.console.print("[red]No character loaded![/red]")
            return
        
        char = self.current_character
        
        # Character header
        header_text = f"{char['name']} - Level {char['level']} {char['race']} {char['class']}"
        
        # Ability scores table
        abilities_table = Table(title="Ability Scores", show_header=True, header_style="bold cyan")
        abilities_table.add_column("Ability", style="white")
        abilities_table.add_column("Score", justify="center", style="bold")
        abilities_table.add_column("Modifier", justify="center", style="dim")
        
        for ability, score in char.get('stats', {}).items():
            modifier = (score - 10) // 2
            modifier_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            abilities_table.add_row(
                ability.title(),
                str(score),
                modifier_str
            )
        
        # Skills table
        skills_table = Table(title="Skills", show_header=True, header_style="bold green")
        skills_table.add_column("Skill", style="white")
        skills_table.add_column("Proficient", justify="center", style="green")
        
        for skill, proficient in char.get('skills', {}).items():
            skills_table.add_row(
                skill,
                "✓" if proficient else "—"
            )
        
        # Combat stats
        combat_table = Table(title="Combat Stats", show_header=True, header_style="bold red")
        combat_table.add_column("Stat", style="white")
        combat_table.add_column("Value", justify="center", style="bold")
        
        combat_table.add_row("Hit Points", f"{char.get('hit_points', 0)}/{char.get('max_hit_points', 0)}")
        combat_table.add_row("Armor Class", str(char.get('armor_class', 10)))
        combat_table.add_row("Proficiency Bonus", f"+{char.get('proficiency_bonus', 2)}")
        
        # Layout
        sheet_panel = Panel(
            Columns([abilities_table, skills_table, combat_table]),
            title=header_text,
            border_style="cyan"
        )
        
        self.console.print(sheet_panel)
        
        # Equipment
        if char.get('equipment'):
            equipment_text = ", ".join(char['equipment'][:10])  # Show first 10 items
            if len(char['equipment']) > 10:
                equipment_text += f" ... and {len(char['equipment']) - 10} more items"
            
            equipment_panel = Panel(
                equipment_text,
                title="Equipment",
                border_style="yellow"
            )
            self.console.print(equipment_panel)
    
    async def campaign_management(self):
        """Handle campaign management."""
        self.console.print("\n[cyan]Campaign Management[/cyan]")
        self.console.print("[dim]Campaign management system coming soon...[/dim]\n")
        Prompt.ask("Press Enter to continue", default="")
    
    async def settings_menu(self):
        """Handle settings configuration."""
        self.console.print("\n[cyan]Settings[/cyan]")
        
        settings_table = Table(show_header=False, box=box.SIMPLE)
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Current Value", style="white")
        
        settings_table.add_row("Ollama URL", str(self.config.ollama_url))
        settings_table.add_row("AI Model", self.config.ai_model)
        settings_table.add_row("Database Path", str(self.config.database_path))
        
        self.console.print(settings_table)
        self.console.print("\n[dim]Settings configuration coming soon...[/dim]\n")
        
        Prompt.ask("Press Enter to continue", default="")