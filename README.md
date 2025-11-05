# MAOnline

An online multiplayer implementation of the card game MAO, built with Python, FastAPI, and WebSockets.

## Overview

MAOnline is a client-server card game that allows multiple players to play MAO together online. The server maintains authoritative game state while clients act as UI-only interfaces, ensuring fair gameplay and preventing cheating.

### Features

- 🎮 **Real-time multiplayer gameplay** via WebSocket connections
- ⏱️ **Configurable turn timers** (default: 20 seconds)
- 🎴 **Classic MAO rules**: Ace (reverse), 8 (skip), 7 (typing challenge)
- 🔌 **Disconnect handling** with automatic forfeit after 2 missed turns
- 🔒 **Password-protected game lobbies**
- 💻 **Terminal-based client interface** with ASCII card graphics

## Quick Start

### Prerequisites

- Python 3.9+
- Conda (or Miniconda/Anaconda)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MAOnline
   ```

2. **Create conda environment**
   ```bash
   conda create -n maonline python=3.9
   conda activate maonline
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Game

1. **Start the server**
   ```bash
   ./run_server.sh --port 8000 --turn-timeout 20
   ```
   Optional: Add `--password <password>` to protect the game with a password.

2. **Start clients** (in separate terminals)
   ```bash
   ./run_client.sh
   ```
   When prompted, enter your player name and the server URL (default: `ws://localhost:8000/ws`).

3. **Play the game**
   - Type `ready` or `r` when all players have joined
   - When it's your turn, use:
     - `play <index>` or `p <index>` to play a card
     - `draw` or `d` to draw a card
     - Type `help` for all commands

## Project Structure

```
MAOnline/
├── core/
│   └── cardgamecore.py      # Core game classes (Card, Deck, Player)
├── server/
│   ├── game_server.py       # FastAPI WebSocket server
│   ├── game_manager.py       # Manages multiple game instances
│   └── game_instance.py     # Single game logic and state
├── client/
│   └── client.py            # Terminal-based client application
├── requirements.txt         # Python dependencies
├── run_server.sh            # Server launcher script
├── run_client.sh            # Client launcher script
└── MESSAGE_PROTOCOL.md      # Communication protocol documentation
```

## Documentation

- **[Technical Documentation](TECHNICAL_DOCUMENTATION.md)**: Comprehensive guide covering architecture, components, implementation details, and troubleshooting
- **[Message Protocol](MESSAGE_PROTOCOL.md)**: Detailed specification of all WebSocket messages between client and server

## How It Works

The game follows a strict client-server architecture:

1. **Server** (`game_server.py`): FastAPI application that handles WebSocket connections, validates moves, and maintains game state
2. **Game Logic** (`game_instance.py`): Manages a single game instance with all rules, turn management, and player state
3. **Client** (`client.py`): Terminal UI that connects to the server and displays game information

All game state is authoritative on the server. Clients only display information and send user actions - they never make game decisions.

## Game Rules

- **Standard Cards**: Match the top card by suit OR value
- **Ace (A)**: Reverses turn direction
- **8**: Skips the next player
- **7**: Typing challenge - type "have a nice day" within 7 seconds
- **Turn Timeout**: If a player doesn't act within the time limit, they automatically draw a card
- **Disconnect Penalty**: Players disconnected for 2 consecutive turns forfeit their hand

## Development

This project was refactored from a single-computer terminal application to a client-server model. The original single-player version (`mao.py`) is preserved for reference.

### Future Enhancements

- Multiple concurrent games with unique IDs
- Player reconnection support
- Web-based UI (replacing terminal client)
- Game state persistence
- Dynamic rule system
- Player authentication

See [Technical Documentation](TECHNICAL_DOCUMENTATION.md) for detailed architecture information and development notes.
