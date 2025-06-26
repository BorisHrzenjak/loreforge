#!/usr/bin/env python3
"""
LoreForge - Main Entry Point
A CLI-based D&D 5e campaign manager with AI dungeon master capabilities.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import version
from version import __version__

from ui.cli_interface import DungeonMasterCLI


def show_version():
    """Display the version information of LoreForge."""
    print(f"LoreForge v{__version__}")


async def main():
    """Main entry point for LoreForge."""
    try:
        cli = DungeonMasterCLI()
        await cli.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye, adventurer! May your next campaign be epic!")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LoreForge - AI-powered D&D 5e Dungeon Master")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")
    args = parser.parse_args()
    
    if args.version:
        show_version()
    else:
        asyncio.run(main())