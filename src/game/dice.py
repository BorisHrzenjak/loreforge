"""
Dice rolling system for the AI Dungeon Master.
Provides D&D dice rolling with visualization and animation.
"""

import random
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box


class DiceType(Enum):
    """Standard D&D dice types."""
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20
    D100 = 100


class AdvantageType(Enum):
    """Types of advantage/disadvantage for D20 rolls."""
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


@dataclass
class DiceRoll:
    """Represents a single dice roll result."""
    dice_type: DiceType
    result: int
    is_critical_success: bool = False
    is_critical_failure: bool = False
    modifier: int = 0
    total: int = 0
    
    def __post_init__(self):
        self.total = self.result + self.modifier
        
        # Check for critical hits/failures (only on d20)
        if self.dice_type == DiceType.D20:
            self.is_critical_success = self.result == 20
            self.is_critical_failure = self.result == 1


@dataclass
class MultiDiceRoll:
    """Represents multiple dice rolled together."""
    dice_type: DiceType
    count: int
    results: List[int]
    modifier: int = 0
    total: int = 0
    individual_totals: List[int] = None
    
    def __post_init__(self):
        if self.individual_totals is None:
            self.individual_totals = self.results.copy()
        self.total = sum(self.results) + self.modifier


@dataclass
class AdvantageRoll:
    """Represents a D20 roll with advantage/disadvantage."""
    advantage_type: AdvantageType
    rolls: List[int]
    selected_roll: int
    modifier: int = 0
    total: int = 0
    is_critical_success: bool = False
    is_critical_failure: bool = False
    
    def __post_init__(self):
        self.total = self.selected_roll + self.modifier
        self.is_critical_success = self.selected_roll == 20
        self.is_critical_failure = self.selected_roll == 1


class DiceRoller:
    """Main dice rolling system with visualization."""
    
    def __init__(self, console: Optional[Console] = None, animate: bool = True):
        self.console = console or Console()
        self.animate = animate
        self.rng = random.Random()
        
    def roll_die(self, dice_type: DiceType, modifier: int = 0) -> DiceRoll:
        """Roll a single die."""
        result = self.rng.randint(1, dice_type.value)
        return DiceRoll(
            dice_type=dice_type,
            result=result,
            modifier=modifier
        )
    
    def roll_multiple(self, dice_type: DiceType, count: int, modifier: int = 0) -> MultiDiceRoll:
        """Roll multiple dice of the same type."""
        results = [self.rng.randint(1, dice_type.value) for _ in range(count)]
        return MultiDiceRoll(
            dice_type=dice_type,
            count=count,
            results=results,
            modifier=modifier
        )
    
    def roll_with_advantage(self, advantage_type: AdvantageType, modifier: int = 0) -> AdvantageRoll:
        """Roll a D20 with advantage, disadvantage, or normal."""
        if advantage_type == AdvantageType.NORMAL:
            rolls = [self.rng.randint(1, 20)]
            selected_roll = rolls[0]
        else:
            rolls = [self.rng.randint(1, 20), self.rng.randint(1, 20)]
            if advantage_type == AdvantageType.ADVANTAGE:
                selected_roll = max(rolls)
            else:  # DISADVANTAGE
                selected_roll = min(rolls)
        
        return AdvantageRoll(
            advantage_type=advantage_type,
            rolls=rolls,
            selected_roll=selected_roll,
            modifier=modifier
        )
    
    def parse_dice_notation(self, notation: str) -> Tuple[int, DiceType, int]:
        """Parse standard dice notation like '2d6+3' or '1d20-1'."""
        notation = notation.lower().replace(' ', '')
        
        # Handle modifier
        modifier = 0
        if '+' in notation:
            parts = notation.split('+')
            notation = parts[0]
            modifier = int(parts[1])
        elif '-' in notation:
            parts = notation.split('-')
            notation = parts[0]
            modifier = -int(parts[1])
        
        # Parse dice
        if 'd' not in notation:
            raise ValueError(f"Invalid dice notation: {notation}")
        
        dice_parts = notation.split('d')
        count = int(dice_parts[0]) if dice_parts[0] else 1
        dice_value = int(dice_parts[1])
        
        # Map to DiceType
        dice_type_map = {
            4: DiceType.D4,
            6: DiceType.D6,
            8: DiceType.D8,
            10: DiceType.D10,
            12: DiceType.D12,
            20: DiceType.D20,
            100: DiceType.D100
        }
        
        if dice_value not in dice_type_map:
            raise ValueError(f"Unsupported dice type: d{dice_value}")
        
        return count, dice_type_map[dice_value], modifier
    
    def roll_notation(self, notation: str) -> MultiDiceRoll:
        """Roll dice using standard notation."""
        count, dice_type, modifier = self.parse_dice_notation(notation)
        return self.roll_multiple(dice_type, count, modifier)
    
    async def animated_roll(self, dice_type: DiceType, modifier: int = 0) -> DiceRoll:
        """Roll a die with animation."""
        if not self.animate:
            return self.roll_die(dice_type, modifier)
        
        # Animation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Rolling d{dice_type.value}...", total=None)
            
            # Show rolling animation
            for _ in range(10):
                temp_result = self.rng.randint(1, dice_type.value)
                progress.update(task, description=f"Rolling d{dice_type.value}... {temp_result}")
                await asyncio.sleep(0.1)
        
        # Final roll
        result = self.roll_die(dice_type, modifier)
        self.display_roll_result(result)
        return result
    
    async def animated_multiple_roll(self, dice_type: DiceType, count: int, modifier: int = 0) -> MultiDiceRoll:
        """Roll multiple dice with animation."""
        if not self.animate:
            return self.roll_multiple(dice_type, count, modifier)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Rolling {count}d{dice_type.value}...", total=None)
            
            # Animation
            for _ in range(15):
                temp_results = [self.rng.randint(1, dice_type.value) for _ in range(count)]
                temp_total = sum(temp_results) + modifier
                progress.update(task, description=f"Rolling {count}d{dice_type.value}... Total: {temp_total}")
                await asyncio.sleep(0.08)
        
        # Final roll
        result = self.roll_multiple(dice_type, count, modifier)
        self.display_multiple_roll_result(result)
        return result
    
    def display_roll_result(self, roll: DiceRoll):
        """Display a single dice roll result."""
        # Color based on result
        if roll.is_critical_success:
            color = "bright_green"
            symbol = "🎯"
        elif roll.is_critical_failure:
            color = "bright_red"
            symbol = "💥"
        elif roll.dice_type == DiceType.D20 and roll.result >= 15:
            color = "green"
            symbol = "🎲"
        elif roll.dice_type == DiceType.D20 and roll.result <= 5:
            color = "yellow"
            symbol = "🎲"
        else:
            color = "white"
            symbol = "🎲"
        
        result_text = Text()
        result_text.append(f"{symbol} d{roll.dice_type.value}: ", style="bold")
        result_text.append(f"{roll.result}", style=f"bold {color}")
        
        if roll.modifier != 0:
            modifier_text = f" + {roll.modifier}" if roll.modifier > 0 else f" - {abs(roll.modifier)}"
            result_text.append(modifier_text, style="dim")
            result_text.append(f" = {roll.total}", style="bold")
        
        # Add special annotations
        if roll.is_critical_success:
            result_text.append(" CRITICAL SUCCESS!", style="bold bright_green")
        elif roll.is_critical_failure:
            result_text.append(" CRITICAL FAILURE!", style="bold bright_red")
        
        panel = Panel(
            result_text,
            title="Dice Roll",
            border_style=color,
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def display_multiple_roll_result(self, roll: MultiDiceRoll):
        """Display multiple dice roll results."""
        # Create table for individual results
        table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
        table.add_column("Die", style="dim")
        table.add_column("Result", justify="center")
        
        for i, result in enumerate(roll.results, 1):
            color = "green" if result == roll.dice_type.value else "white"
            table.add_row(f"#{i}", f"[{color}]{result}[/{color}]")
        
        # Summary
        summary_text = Text()
        summary_text.append(f"🎲 {roll.count}d{roll.dice_type.value}: ", style="bold")
        summary_text.append(f"{sum(roll.results)}", style="bold white")
        
        if roll.modifier != 0:
            modifier_text = f" + {roll.modifier}" if roll.modifier > 0 else f" - {abs(roll.modifier)}"
            summary_text.append(modifier_text, style="dim")
            summary_text.append(f" = {roll.total}", style="bold cyan")
        
        panel = Panel(
            table if roll.count <= 10 else summary_text,  # Show table only for reasonable number of dice
            title=f"Multiple Dice Roll - Total: {roll.total}",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def display_advantage_roll(self, roll: AdvantageRoll):
        """Display advantage/disadvantage roll result."""
        # Create display for both rolls
        rolls_text = Text()
        
        for i, roll_value in enumerate(roll.rolls):
            if i > 0:
                rolls_text.append(" | ")
            
            if roll_value == roll.selected_roll:
                # This is the selected roll
                color = "bright_green" if roll.is_critical_success else "bright_red" if roll.is_critical_failure else "bold white"
                rolls_text.append(f"{roll_value}", style=color)
            else:
                # This roll was discarded
                rolls_text.append(f"{roll_value}", style="dim strike")
        
        # Advantage type indicator
        if roll.advantage_type == AdvantageType.ADVANTAGE:
            advantage_text = "⬆️ ADVANTAGE"
            border_color = "green"
        elif roll.advantage_type == AdvantageType.DISADVANTAGE:
            advantage_text = "⬇️ DISADVANTAGE"
            border_color = "red"
        else:
            advantage_text = "➡️ NORMAL"
            border_color = "white"
        
        # Build final text
        result_text = Text()
        result_text.append(f"🎲 d20 ({advantage_text}): ", style="bold")
        result_text.append(rolls_text)
        
        if roll.modifier != 0:
            modifier_text = f" + {roll.modifier}" if roll.modifier > 0 else f" - {abs(roll.modifier)}"
            result_text.append(modifier_text, style="dim")
            result_text.append(f" = {roll.total}", style="bold")
        
        # Add critical annotations
        if roll.is_critical_success:
            result_text.append(" CRITICAL SUCCESS!", style="bold bright_green")
        elif roll.is_critical_failure:
            result_text.append(" CRITICAL FAILURE!", style="bold bright_red")
        
        panel = Panel(
            result_text,
            title="D20 Roll with Advantage/Disadvantage",
            border_style=border_color,
            box=box.ROUNDED
        )
        
        self.console.print(panel)
    
    def roll_stats(self) -> Dict[str, int]:
        """Roll D&D character stats (6 stats, 4d6 drop lowest each)."""
        stats = {}
        stat_names = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        
        for stat in stat_names:
            # Roll 4d6, drop lowest
            rolls = [self.rng.randint(1, 6) for _ in range(4)]
            rolls.sort(reverse=True)
            stat_value = sum(rolls[:3])  # Sum the highest 3
            stats[stat] = stat_value
        
        return stats
    
    def display_stats_roll(self, stats: Dict[str, int]):
        """Display character stat rolls."""
        table = Table(title="🎭 Character Stats", show_header=True, header_style="bold magenta")
        table.add_column("Ability", style="cyan", width=12)
        table.add_column("Score", justify="center", style="bold white")
        table.add_column("Modifier", justify="center", style="dim")
        
        for stat, score in stats.items():
            modifier = (score - 10) // 2
            modifier_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            
            # Color based on score
            if score >= 16:
                score_color = "bright_green"
            elif score >= 14:
                score_color = "green"
            elif score >= 12:
                score_color = "white"
            elif score >= 10:
                score_color = "yellow"
            else:
                score_color = "red"
            
            table.add_row(
                stat,
                f"[{score_color}]{score}[/{score_color}]",
                modifier_str
            )
        
        self.console.print(table)