# 🎲 LoreForge v0.1.0

A comprehensive AI-powered D&D 5th Edition campaign manager with intelligent dungeon master capabilities. Run complete campaigns with persistent memory, character management, and campaign parsing - all through a beautiful command-line interface.

![intro_image](https://github.com/user-attachments/assets/57a2457e-4828-4094-a7c9-2ec93954482f)


## ✨ Features

### 🎭 AI Dungeon Master
- **Local AI Integration**: Powered by Ollama for complete privacy and control
- **Intelligent Responses**: Context-aware DM responses using RAG (Retrieval-Augmented Generation)
- **Permanent Consequences**: No save states - every decision matters and shapes your story
- **Memory System**: Remembers every interaction, NPC, location, and plot development

### 🎲 Complete D&D 5e Support
- **Character Creation**: Full interactive character builder with all D&D 5e classes, races, and backgrounds
- **Dice Rolling**: Animated dice with advantage/disadvantage, custom notation, and visual feedback
- **Character Progression**: Level up system with hit point rolling and stat tracking
- **Equipment & Inventory**: Comprehensive item and equipment management

### 📚 Campaign Management
- **Multi-Format Support**: Load campaigns from PDF, text files, and Roll20 exports
- **Smart Parsing**: Automatically extracts NPCs, locations, encounters, and items
- **Vector Search**: Find relevant campaign information instantly
- **Context Awareness**: AI understands your campaign world and maintains consistency

### 🖥️ Beautiful CLI Interface
- **Rich Terminal UI**: Modern interface with colors, tables, and panels
- **Interactive Menus**: Easy navigation through all features
- **Real-time Feedback**: Visual dice rolling and status updates
- **Character Sheets**: Detailed character display with stats, skills, and equipment

## 🛠️ Requirements

### System Requirements
- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- 4GB+ RAM recommended for larger campaigns

### AI Models
The system works with any Ollama-compatible model. Recommended models:
- **llama3.1** (default): Good balance of performance and quality
- **mistral**: Faster responses, good for quick interactions
- **codellama**: Enhanced logical reasoning for complex scenarios

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd loreforge
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Ollama
Download and install Ollama from [https://ollama.ai/](https://ollama.ai/)

### 4. Pull an AI Model
```bash
ollama pull llama3.1
```

### 5. Run the Application
```bash
python main.py
```
Or if installed via pip:
```bash
loreforge
```

## 📖 Quick Start Guide

### First Run
1. **Start the application**: `python main.py` or `loreforge`
2. **Create a character**: Choose option 1 from the main menu
3. **Load a campaign** (optional): Choose option 4 to import a campaign file
4. **Start your adventure**: Choose option 3 to begin a campaign session

### Character Creation
The system guides you through:
- Choosing race, class, and background
- Rolling or assigning ability scores
- Selecting skills and equipment
- Calculating hit points and armor class

### Campaign Session
During gameplay:
- Type actions in natural language
- Use `roll <dice>` for dice rolls (e.g., `roll d20`, `roll 3d6+2`)
- Type `character` to view your character sheet
- Type `quit` to end the session

### Campaign Import
Supported formats:
- **PDF**: Adventure modules and campaign books
- **Text/Markdown**: Plain text campaigns and notes
- **JSON**: Roll20 campaign exports

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
OLLAMA_URL=http://localhost:11434
AI_MODEL=llama3.1
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### Configuration File
Create `config.yaml` for advanced settings:
```yaml
# AI Configuration
ollama_url: "http://localhost:11434"
ai_model: "llama3.1"
temperature: 0.7
max_context_length: 4096

# Game Settings
dice_animation: true
show_dice_details: true
confirm_dangerous_actions: true

# Paths (auto-created if they don't exist)
database_path: "data/loreforge.db"
vector_db_path: "data/chroma_db"
campaigns_dir: "campaigns"
characters_dir: "characters"
```

## 🎯 Usage Examples

### Basic Gameplay
```
> What do you do?
I want to investigate the mysterious door

🎭 Dungeon Master:
You approach the ancient wooden door. Its surface is carved with intricate 
runes that seem to shimmer in the torchlight. Make an Investigation check 
to examine it more closely.

> roll d20+3
🎲 d20: 15 + 3 = 18

🎭 Dungeon Master:
With your keen eye, you notice that one of the runes is slightly raised...
```

### Character Sheet
```
> character

┌─ Thorin Ironbeard - Level 3 Dwarf Fighter ─┐
│ ┌─ Ability Scores ─┐ ┌─ Skills ─────┐ ┌─ Combat Stats ─┐ │
│ │ Strength    16 +3│ │ Athletics  ✓ │ │ Hit Points 28/28│ │
│ │ Dexterity   12 +1│ │ Insight    ✓ │ │ Armor Class  18 │ │
│ │ Constitution 15 +2│ │ History    — │ │ Prof. Bonus  +2 │ │
│ └──────────────────┘ └──────────────┘ └─────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Dice Rolling
```
🎲 Dice Roller Menu:
1. Roll single die (d4, d6, d8, d10, d12, d20, d100)
2. Roll multiple dice (e.g., 3d6, 2d8+2)
3. Roll with advantage/disadvantage
4. Roll character stats (4d6 drop lowest)
5. Custom dice notation

> 3d6+2
🎲 Rolling 3d6... 
┌─ Multiple Dice Roll - Total: 14 ─┐
│ #1  4                            │
│ #2  6                            │
│ #3  2                            │
│ Total: 12 + 2 = 14               │
└──────────────────────────────────┘
```

## 🏗️ Architecture

### Core Components
- **DMEngine**: Coordinates AI responses and game state
- **CharacterManager**: Handles D&D 5e character creation and progression
- **DiceRoller**: Provides animated dice rolling with D&D mechanics
- **CampaignParser**: Extracts structured data from various file formats
- **VectorStore**: ChromaDB-based RAG system for campaign memory

### Database Design
- **SQLite**: Stores characters, campaigns, sessions, and actions
- **ChromaDB**: Vector embeddings for intelligent content retrieval
- **Automatic Backups**: Session data preserved with permanent consequences

### AI Integration
- **Ollama Client**: Manages local AI model communication
- **Context Building**: Constructs rich prompts with campaign history
- **Response Parsing**: Extracts structured information from AI responses

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a virtual environment: `python -m venv venv`
3. Install development dependencies: `pip install -r requirements.txt`
4. Run tests: `pytest`

### Code Style
- Follow PEP 8 for Python code
- Use type hints for all functions
- Document classes and methods with docstrings
- Format code with Black: `black src/`

### Adding Features
1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement with tests
3. Update documentation
4. Submit pull request

## 📋 Roadmap

### Phase 1: Core Features ✅
- [x] Character creation and management
- [x] AI DM integration with Ollama
- [x] Dice rolling system
- [x] Campaign file parsing
- [x] Vector-based memory system

### Phase 2: Advanced Features 🚧
- [ ] Combat encounter management
- [ ] Spell system integration
- [ ] Custom rule modifications
- [ ] Session replay and analysis

### Phase 3: Enhanced Experience 📅
- [ ] Multiplayer support
- [ ] Voice integration
- [ ] Map visualization
- [ ] Campaign sharing community

## 🐛 Troubleshooting

### Common Issues

**Ollama Connection Failed**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

**Model Not Found**
```bash
# Pull the required model
ollama pull llama3.1

# List available models
ollama list
```

**Database Errors**
```bash
# Reset database (WARNING: deletes all data)
rm -rf data/
python main.py  # Will recreate database
```

**Import Errors**
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Performance Tips
- Use smaller models for faster responses: `ollama pull mistral`
- Reduce context length in config for memory-constrained systems
- Disable dice animations for faster gameplay: `dice_animation: false`

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama Team**: For providing excellent local AI infrastructure
- **D&D 5e SRD**: System Reference Document for game mechanics
- **Rich Library**: For beautiful terminal interfaces
- **ChromaDB**: Vector database for intelligent retrieval

---

**Ready to embark on your LoreForge adventure?** 🎲⚔️🏰

Start with `python main.py` or `loreforge` and let your imagination run wild!
