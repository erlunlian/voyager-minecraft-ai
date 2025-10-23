# Voyager Minecraft AI

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/erlunlian/voyager-minecraft-ai)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A complete implementation of the Voyager Minecraft AI agent using LangGraph, Mineflayer, ChromaDB, and Azure OpenAI.

> 🎮 **Live Demo**: Watch the AI agent autonomously explore, learn, and build in Minecraft!

## Quick Start

```bash
# Clone and setup
git clone https://github.com/erlunlian/voyager-minecraft-ai.git
cd voyager-minecraft-ai

# Setup environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && npm install && npm run build

# Start databases
docker-compose up -d

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Run the agent
python src/main.py
```

## Architecture

Voyager is an autonomous Minecraft agent that:
- **Proposes tasks** using a Curriculum Agent based on exploration progress
- **Generates code** using an Action Agent with access to a skill library
- **Executes code** in Minecraft via Mineflayer bot
- **Evaluates success** using a Critic Agent
- **Learns skills** by storing successful code in a vector database

### Components

1. **Curriculum Agent**: Proposes progressive tasks based on bot state
2. **Action Agent**: Generates JavaScript code to accomplish tasks
3. **Critic Agent**: Evaluates task completion and provides feedback
4. **Skill Manager**: ChromaDB-based semantic search for relevant skills
5. **Session Manager**: PostgreSQL-based persistence for resumable sessions
6. **LangGraph State Machine**: Orchestrates the agent loop with checkpointing

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Minecraft Java Edition server
- Azure OpenAI API access

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/erlunlian/voyager-minecraft-ai.git
cd voyager-minecraft-ai
```

2. **Create and activate Python virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Install Node.js dependencies and build TypeScript**
```bash
npm install
npm run build  # Compiles TypeScript to JavaScript
```

4. **Start databases with Docker Compose**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432) - for session state
- ChromaDB (port 8000) - for skill embeddings

5. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# Database (default values work with docker-compose)
POSTGRES_USER=voyager
POSTGRES_PASSWORD=voyager_pass
POSTGRES_DB=voyager_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Minecraft Server
MINECRAFT_HOST=localhost
MINECRAFT_PORT=25565
MINECRAFT_USERNAME=VoyagerBot
```

6. **Start Minecraft Server**

You need a running Minecraft Java Edition server. For local testing:
- Download Minecraft server from minecraft.net
- Run: `java -Xmx1024M -Xms1024M -jar server.jar nogui`
- Set `server.properties`: `online-mode=false` for local testing

## Usage

### Run Voyager Agent

```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the agent
python src/main.py
```

The agent will:
1. Connect to the Minecraft server
2. Initialize all components (agents, skill library, session)
3. Start the autonomous exploration loop
4. Propose tasks → Generate code → Execute → Evaluate → Learn

### Resume Previous Session

If you stop the agent, it automatically saves its state. When you restart, you'll be prompted to resume:

```
Found active session: 123
Resume this session? (y/n):
```

Choose 'y' to continue from where you left off.

### Monitor Progress

The agent prints detailed logs:
- Task proposals
- Code generation
- Execution results
- Critic evaluations
- Skills learned

Session statistics are displayed at the end:
```
Session Stats:
  Total tasks: 45
  Successful: 32
  Failed: 13
  Skills learned: 28
```

## Project Structure

```
voyager-minecraft-ai/
├── src/
│   ├── models.py              # Shared type definitions
│   ├── agents/
│   │   ├── types.py           # Agent-specific types
│   │   ├── curriculum.py      # Proposes tasks
│   │   ├── action.py          # Generates code
│   │   └── critic.py          # Evaluates success
│   ├── skills/
│   │   ├── skill_manager.py   # ChromaDB skill library
│   │   └── primitives.py      # Base skills
│   ├── graph/
│   │   ├── types.py           # Graph state types
│   │   └── voyager_graph.py   # LangGraph orchestration
│   ├── minecraft/
│   │   ├── bot.ts             # Mineflayer bot (TypeScript)
│   │   └── executor.py        # Python-Node.js bridge
│   ├── session/
│   │   ├── types.py           # Session types
│   │   └── manager.py         # Session persistence
│   └── main.py                # Entry point
├── dist/                      # Compiled TypeScript (git-ignored)
│   └── minecraft/
│       └── bot.js             # Compiled JavaScript
├── data/                      # Persistent data (git-ignored)
│   ├── chroma/               # Skill embeddings
│   └── postgres/             # Session database
├── docker-compose.yml        # Database services
├── tsconfig.json            # TypeScript config
├── requirements.txt          # Python deps
├── package.json             # Node.js deps
└── .env                     # Configuration
```

> 📘 **Type Organization**: See [TYPE_ORGANIZATION.md](TYPE_ORGANIZATION.md) for details on how types are organized by scope to reduce coupling.

## How It Works

### Agent Loop

```
┌─────────────────┐
│ Propose Task    │ ← Curriculum Agent analyzes bot state
└────────┬────────┘
         ↓
┌─────────────────┐
│ Generate Code   │ ← Action Agent retrieves skills & writes code
└────────┬────────┘
         ↓
┌─────────────────┐
│ Execute Code    │ ← Mineflayer bot runs in Minecraft
└────────┬────────┘
         ↓
┌─────────────────┐
│ Evaluate        │ ← Critic compares before/after states
└────────┬────────┘
         ↓
    Success?
    ↓     ↓
   Yes    No
    ↓     ↓
Update   Retry
Skills   (max 2)
    ↓
Next Task
```

### Skill Learning

Successful task code is automatically added to the skill library:
- **Storage**: ChromaDB with Azure OpenAI embeddings
- **Retrieval**: Semantic search finds relevant skills for new tasks
- **Evolution**: Skills compound over time as the bot learns

### Session Persistence

Everything is saved to PostgreSQL:
- Current task and progress
- Bot state history
- Task completion/failure records
- Learned skills

LangGraph's `PostgresSaver` checkpoints the state machine, allowing seamless resume after crashes or manual stops.

## Primitive Skills

The bot starts with 10 primitive skills:

1. `collectWood` - Gather wood from trees
2. `craftItem` - Craft items with recipes
3. `mineBlock` - Mine specific block types
4. `goToPosition` - Navigate to coordinates
5. `placeBlock` - Place blocks
6. `equipItem` - Equip items from inventory
7. `followEntity` - Follow players/mobs
8. `eatFood` - Consume food
9. `attackEntity` - Combat hostile mobs
10. `exploreArea` - Random exploration

These are used as building blocks for more complex learned skills.

## Customization

### Adjust Task Difficulty

Edit `src/agents/curriculum.py` to modify task progression logic.

### Add Custom Primitive Skills

Edit `src/skills/primitives.py` to add new base skills.

### Change Retry Logic

Edit `src/graph/voyager_graph.py` `_should_continue_or_end()` method.

### Modify LLM Parameters

Each agent instantiates `AzureChatOpenAI` - adjust temperature, model, etc.

## Troubleshooting

### Bot can't connect to Minecraft
- Ensure server is running and accessible
- Check `MINECRAFT_HOST` and `MINECRAFT_PORT` in `.env`
- For local servers, set `online-mode=false` in `server.properties`

### Database connection errors
- Run `docker-compose up -d` to start databases
- Check containers: `docker-compose ps`
- View logs: `docker-compose logs postgres` or `docker-compose logs chromadb`

### ChromaDB errors
- Ensure ChromaDB container is running: `docker-compose restart chromadb`
- Check port 8000 is not in use

### Azure OpenAI errors
- Verify API key and endpoint in `.env`
- Check API quota and rate limits
- Ensure model `gpt-4` is deployed in your Azure resource

## Development

### Reset Everything

```bash
# Stop and remove containers + data
docker-compose down -v

# Remove data directories
rm -rf data/

# Restart
docker-compose up -d
python src/main.py
```

### Database Inspection

```bash
# PostgreSQL
docker exec -it voyager-postgres psql -U voyager -d voyager_db

# Useful queries:
SELECT * FROM sessions;
SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10;
SELECT * FROM learned_skills;
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

Based on the Voyager paper: "Voyager: An Open-Ended Embodied Agent with Large Language Models"

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/erlunlian/voyager-minecraft-ai/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/erlunlian/voyager-minecraft-ai/discussions)
- 📧 **Contact**: [Create an issue](https://github.com/erlunlian/voyager-minecraft-ai/issues/new) for questions

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=erlunlian/voyager-minecraft-ai&type=Date)](https://star-history.com/#erlunlian/voyager-minecraft-ai&Date)

