# MAOnline Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Core Components](#core-components)
5. [Libraries Used](#libraries-used)
6. [How It Works](#how-it-works)
7. [Issues and Solutions](#issues-and-solutions)
8. [Future Enhancements](#future-enhancements)

---

## Project Overview

MAOnline is a client-server implementation of the card game MAO, refactored from a single-computer terminal application to a multiplayer online game. The project uses a WebSocket-based architecture where the server maintains authoritative game state and clients act as UI-only interfaces.

### Key Features
- Real-time multiplayer gameplay via WebSocket connections
- Turn-based game with configurable timeout (default 20 seconds)
- Special card rules: Ace (reverse), 8 (skip), 7 (typing challenge "have a nice day")
- Player disconnect handling with automatic forfeit after 2 missed turns
- Password-protected game lobbies
- Terminal-based client interface

---

## Architecture

### Client-Server Model

The architecture follows a strict client-server pattern:

- **Server**: Maintains authoritative game state, validates all moves, handles game logic
- **Client**: Acts as UI only, does not store game state locally (except for display purposes)

### Communication Protocol

All communication uses JSON messages over WebSocket connections. The protocol is documented in `MESSAGE_PROTOCOL.md`.

### Key Design Decisions

1. **Event-Driven Architecture**: Game instance stores pending events that the server layer handles asynchronously
2. **Separation of Concerns**: Game logic (`GameInstance`) is separate from networking (`GameServer`)
3. **No Client-Side State**: Clients don't store authoritative game data to prevent cheating
4. **Background Event Processing**: A background task polls for pending events (timeouts, etc.) every 100ms

---

## File Structure

```
MAOnline/
├── core/
│   └── cardgamecore.py      # Core game classes (Card, Deck, Player)
├── server/
│   ├── __init__.py          # Package marker
│   ├── game_server.py       # FastAPI WebSocket server
│   ├── game_manager.py       # Manages multiple game instances
│   └── game_instance.py      # Single game logic and state
├── client/
│   ├── __init__.py          # Package marker
│   └── client.py            # Terminal-based client application
├── mao.py                   # Original single-player game (legacy)
├── requirements.txt         # Python dependencies
├── run_server.sh            # Server launcher script
├── run_client.sh            # Client launcher script
├── MESSAGE_PROTOCOL.md       # Communication protocol documentation
└── TECHNICAL_DOCUMENTATION.md # This file
```

---

## Core Components

### 1. `core/cardgamecore.py`

Contains the fundamental game classes used throughout the application.

#### Classes

**`Card`**
- Represents a single playing card
- Attributes: `suit` (Hearts, Diamonds, Clubs, Spades), `value` (A, 2-10, J, Q, K)
- Methods: `printCard()` - ASCII art representation

**`Player`**
- Represents a player in the game
- Attributes: `name` (str), `hand` (list of Cards)
- Methods:
  - `giveCard(card)` - Add a card to player's hand
  - `playCard(handIndex)` - Remove and return card at index (1-indexed)
  - `printHand()` - Pretty-print the hand with ASCII art

**`Deck`**
- Represents a stack of cards (used for draw pile, place pile)
- Uses `collections.deque` for efficient stack operations
- Methods:
  - `shuffleDeck()` - Randomize card order
  - `getTopCard()` - Remove and return top card
  - `placeCardOnTop(card)` - Add card to top
  - `placeCardOnBottom(card)` - Add card to bottom
  - `empty()` - Check if deck is empty
  - `seeTopCard()` - Peek at top card without removing

**`Rule` and `RuleBook`**
- Currently unused in the refactored version
- Placeholder for future dynamic rule system

---

### 2. `server/game_instance.py`

The heart of the game logic. Manages a single game instance with all state, players, turns, and rules.

#### Class: `GameInstance`

**Purpose**: Encapsulates all game logic for a single game session.

**Key Attributes**:
- `game_id`: Unique identifier for the game
- `password`: Optional password protection
- `turn_timeout`: Time limit per turn in seconds
- `status`: "waiting", "playing", or "finished"
- `players`: List of Player objects
- `player_connections`: Dict mapping player names to WebSocket connections
- `player_ready`: Dict tracking which players are ready
- `drawPile`, `placePile`: Deck objects for card management
- `topCard`: Current card on top of place pile
- `current_player_index`: Index of current player
- `reverse`, `skip`, `revSkip`: Turn direction flags
- `turn_timer`: Async task for turn timeout
- `active_typing_challenge`: Player name with active typing challenge
- Pending event storage: `pending_timeout_broadcast`, `last_card_drawn`, etc.

#### Major Methods

**`__init__(game_id, password, turn_timeout)`**
- Initializes game instance with given parameters
- Sets up empty decks, player lists, and state tracking

**`initialize_deck()`**
- Creates a full 52-card deck (4 suits × 13 values)
- Shuffles the deck using `shuffleDeck()`

**`add_player(player_name, websocket)`**
- Adds a new player to the game
- Returns `False` if player name is already taken
- Initializes player ready status and disconnect counter

**`remove_player_from_game(player_name)`**
- Completely removes a player from the game
- Removes from players list, connections, ready status
- Returns player's cards to draw pile (forfeit)

**`set_player_ready(player_name)`**
- Marks a player as ready
- Returns `True` if all players are now ready (game should start)

**`start_game()`**
- Transitions game from "waiting" to "playing"
- Deals 7 cards to each player
- Places first card on place pile
- Starts first player's turn

**`get_current_player()`**
- Returns the Player object whose turn it is
- Handles reverse direction logic

**`start_player_turn()`**
- Begins a player's turn
- Creates async timer task for turn timeout
- Checks for disconnected players (forfeit after 2 missed turns)
- Stores pending events for server to handle

**`handle_turn_timeout()`** (async)
- Called when a player's turn times out
- Auto-draws a card for the player
- Stores timeout event for server to broadcast
- Advances to next player

**`advance_to_next_player()`**
- Cancels current turn timer
- Advances to next player based on direction (forward/reverse)
- Handles skip logic (skip next player)
- Starts new player's turn

**`handle_draw_card(player_name)`**
- Player draws a card from draw pile
- Checks if draw pile is empty (reshuffle if needed)
- Stores card_drawn event
- Advances to next player
- Returns `None` on success, error dict on failure

**`handle_play_card(player_name, card_index)`**
- Validates the card can be played (matches suit or value)
- Places card on place pile
- Checks for win condition (empty hand)
- Handles special card effects:
  - Ace (A): Reverse turn direction
  - 8: Skip next player
  - 7: Start typing rule challenge
- Stores card_played event
- Advances to next player (unless typing challenge)
- Returns `None` on success, error dict on failure

**`check_draw_pile()`**
- Checks if draw pile is empty
- If empty, reshuffles place pile (except top card) into draw pile

**`start_typing_challenge(player_name)`**
- Starts the 7-second typing challenge when a 7 is played
- Creates async timer for 7-second limit
- Stores challenge state

**`handle_typing_response(player_name, response)`**
- Validates player's response to typing challenge
- Checks if response matches "have a nice day" (case-insensitive)
- Checks if response was within 7 seconds
- On success: Challenge passes, game continues
- On failure: Player draws penalty card, loses turn

**`handle_typing_challenge_failure(player_name, reason)`**
- Handles typing challenge timeout or incorrect response
- Draws penalty card for player
- Stores typing_result and card_drawn events

**`forfeit_player(player_name)`**
- Removes a player who has been disconnected for 2+ turns
- Returns all their cards to draw pile
- Removes from game state
- Stores forfeit event

**`get_game_state()`**
- Returns a dict with current game state for clients
- Includes: status, top card, draw pile size, turn direction, current player, all players with hand sizes

**`get_player_hand(player_name)`**
- Returns list of card dicts for a player's hand
- Used for sending hand updates to clients

**`get_lobby_state()`**
- Returns lobby information (waiting players, ready status)
- Used before game starts

---

### 3. `server/game_manager.py`

Manages multiple game instances. Currently supports a single default game per server.

#### Class: `GameManager`

**Purpose**: Factory and manager for game instances.

**Key Attributes**:
- `games`: Dict mapping game_id to GameInstance
- `default_game`: Reference to the default game instance

#### Major Methods

**`create_game(password, turn_timeout)`**
- Creates a new game instance with UUID
- Initializes the deck
- Stores game in `games` dict
- Sets as default game
- Returns game_id

**`get_game(game_id)`**
- Retrieves game by ID
- If `game_id` is None, returns default game
- Returns `None` if game doesn't exist

**`get_or_create_default_game()`**
- Gets default game, creating it if it doesn't exist
- Ensures a game is always available

---

### 4. `server/game_server.py`

The FastAPI application that handles WebSocket connections and routes messages.

#### Key Components

**FastAPI Application**
- Uses `@asynccontextmanager` for lifespan management
- Background task checks for pending events every 100ms
- Health check endpoint at `/`

**Global State**
- `game_manager`: Single `GameManager` instance
- `active_connections`: Dict mapping player_name to WebSocket

#### Major Functions

**`send_to_player(player_name, message_type, data)`** (async)
- Sends a JSON message to a specific player via WebSocket
- Handles connection errors gracefully

**`broadcast_to_game_async(game, message_type, data)`** (async)
- Broadcasts a message to all connected players in a game
- Uses `asyncio.gather()` for concurrent sends

**`check_and_handle_pending_events(game)`** (async)
- Checks for pending events from game instance
- Handles:
  - Turn timeouts: Sends hand, card_drawn, timeout event, game state, next turn
  - Game won: Broadcasts winner
  - Player forfeited: Broadcasts forfeit
- Clears pending events after processing

**`background_event_checker()`** (async)
- Background task that runs continuously
- Polls all games for pending events every 100ms
- Handles errors gracefully

**`websocket_endpoint(websocket)`** (async)
- Main WebSocket handler
- Manages connection lifecycle
- Routes messages by type:
  - `join_game`: Validates password, adds player, sends lobby/game state
  - `ready`: Marks player ready, starts game when all ready
  - `draw_card`: Processes card draw, sends updates
  - `play_card`: Validates and processes card play, sends updates
  - `typing_rule_response`: Handles typing challenge response
  - `ping`: Keep-alive response
- Handles disconnects:
  - If game not started: Complete player removal
  - If game started: Complete player removal (future: reconnection)

#### Message Handling Flow

1. Client sends message via WebSocket
2. Server parses JSON
3. Server routes to appropriate handler based on message type
4. Handler calls `GameInstance` method
5. `GameInstance` stores pending events (no direct async calls)
6. Handler checks for pending events and broadcasts
7. Server sends responses to client(s)

---

### 5. `client/client.py`

Terminal-based client application for connecting to the game server.

#### Class: `GameClient`

**Purpose**: Handles user interface and server communication.

**Key Attributes**:
- `server_url`: WebSocket URL to connect to
- `websocket`: WebSocket connection object
- `player_name`: Current player's name
- `game_state`: Current game state dict (for display only)
- `my_hand`: List of player's cards (for display only)
- `running`: Boolean flag for main loop

#### Major Methods

**`connect()`** (async)
- Establishes WebSocket connection to server
- Exits on connection failure

**`send_message(message_type, data)`** (async)
- Sends JSON message to server

**`handle_message(message)`** (async)
- Routes incoming messages by type
- Updates local state (for display)
- Clears screen and refreshes display on state changes
- Handles:
  - `join_success`: Shows lobby or game state
  - `lobby_update`: Clears screen, shows updated lobby
  - `game_state`: Clears screen, shows game state with hand
  - `your_hand`: Updates hand, refreshes display
  - `game_started`: Shows game start message
  - `player_turn`: Shows turn indicator
  - `card_played`: Shows card played, refreshes if own card
  - `card_drawn`: Shows card drawn, refreshes display
  - `turn_timeout`: Shows timeout message, refreshes display
  - `typing_rule_challenge`: Prompts for typing challenge
  - `typing_rule_result`: Shows challenge result
  - `error`: Shows error message

**`listen_for_messages()`** (async)
- Continuously receives messages from server
- Calls `handle_message()` for each message
- Handles connection errors

**`handle_user_input()`** (async)
- Processes user commands:
  - `play <index>` or `p <index>`: Play card
  - `draw` or `d`: Draw card
  - `ready` or `r`: Mark ready
  - `quit` or `q`: Disconnect
  - `state` or `s`: Show current state
  - `help` or `h`: Show help
  - Typing challenge response: Sends `typing_rule_response`

**`run()`** (async)
- Main client loop
- Runs `listen_for_messages()` and `handle_user_input()` concurrently
- Handles cleanup on exit

#### Helper Functions

**`print_hand(hand)`**
- Pretty-prints a hand of cards
- Shows card index numbers

**`print_game_state(state, hand=None)`**
- Prints formatted game state
- Shows: status, top card, draw pile size, turn direction, current player, all players with hand sizes
- Includes player's own hand if provided

**`print_lobby(lobby_state)`**
- Prints lobby information
- Shows: game ID, players, ready status

**`print_help()`**
- Displays help message with commands

---

### 6. Shell Scripts

**`run_server.sh`**
- Launcher script for server
- Auto-detects conda environment (`maonline`)
- Sets PYTHONPATH
- Passes arguments to `server/game_server.py`

**`run_client.sh`**
- Launcher script for client
- Auto-detects conda environment
- Sets PYTHONPATH
- Passes arguments to `client/client.py`

Both scripts handle conda environment detection across multiple common installation paths.

---

## Libraries Used

### Python Standard Library
- `asyncio`: Asynchronous programming, tasks, timers
- `json`: JSON serialization/deserialization
- `uuid`: Unique game ID generation
- `collections.deque`: Efficient stack operations for decks
- `random.shuffle`: Card shuffling
- `argparse`: Command-line argument parsing
- `sys`, `os`: System operations, path handling
- `typing`: Type hints for better code documentation
- `contextlib.asynccontextmanager`: FastAPI lifespan management

### Third-Party Libraries

**FastAPI (0.104.1)**
- Modern Python web framework
- WebSocket support
- Automatic API documentation
- Used for: HTTP server, WebSocket endpoint, request handling

**Uvicorn (0.24.0)**
- ASGI server for FastAPI
- High-performance async server
- Used for: Running the FastAPI application

**websockets (12.0)**
- WebSocket client library
- Used for: Client-side WebSocket connections

---

## How It Works

### Game Flow

1. **Server Startup**
   - Server starts with `run_server.sh`
   - Creates default game via `GameManager`
   - Starts FastAPI with uvicorn
   - Background event checker begins polling

2. **Client Connection**
   - Client starts with `run_client.sh`
   - Connects to server via WebSocket
   - Sends `join_game` message with player name
   - Server validates, adds player, sends lobby state

3. **Lobby Phase**
   - Players see lobby with current players
   - Players send `ready` message when ready
   - Server tracks ready status
   - When all players ready, game starts

4. **Game Start**
   - Server deals 7 cards to each player
   - Places first card on place pile
   - Sends `game_started` to all clients
   - Starts first player's turn

5. **Gameplay Loop**
   - Current player receives `player_turn` message
   - Turn timer starts (20 seconds default)
   - Player can:
     - Play a card: Sends `play_card` with card index
     - Draw a card: Sends `draw_card`
   - Server validates move
   - Server updates game state
   - Server sends updates to all clients
   - Turn advances to next player

6. **Special Rules**
   - **Ace (A)**: Reverses turn direction
   - **8**: Skips next player
   - **7**: Typing challenge - player must type "have a nice day" within 7 seconds

7. **Turn Timeout**
   - If player doesn't act within timeout:
     - Background event checker detects pending timeout
     - Player auto-draws a card
     - Timeout event broadcast to all
     - Game state updated
     - Next player's turn begins

8. **Disconnect Handling**
   - If player disconnects before game starts: Complete removal
   - If player disconnects during game:
     - Player marked as disconnected
     - If disconnected for 2 consecutive turns: Forfeit (cards returned to deck, player removed)

9. **Win Condition**
   - When a player's hand is empty after playing a card, they win
   - Server broadcasts `game_won` message
   - Game status changes to "finished"

### Data Flow

```
Client Input → WebSocket → Server (game_server.py)
                              ↓
                    GameInstance (game_instance.py)
                              ↓
                    Store Pending Events
                              ↓
                    Background Checker
                              ↓
                    Broadcast Messages
                              ↓
                    WebSocket → Client Display
```

### Event Processing

The game uses an event-driven architecture:

1. **Action Occurs**: Player draws card, plays card, timeout, etc.
2. **Game Logic Updates**: `GameInstance` methods update game state
3. **Event Stored**: Pending events stored in `GameInstance` attributes
4. **Background Polling**: `background_event_checker()` polls every 100ms
5. **Event Processing**: `check_and_handle_pending_events()` processes events
6. **Message Broadcasting**: Messages sent to clients via WebSocket
7. **Client Update**: Client receives messages and updates display

This architecture ensures:
- No blocking async calls in game logic
- Proper handling of concurrent events
- Clean separation between game logic and networking

### Turn Management

Turn order is managed by `current_player_index` and direction flags:

- **Forward**: `current_player_index` increments
- **Reverse**: `current_player_index` decrements (calculated as `len(players) - 1 - index`)
- **Skip**: Next player is skipped (advance twice)
- **Reverse Skip**: When in reverse mode, skip previous player

### Card Validation

When a player plays a card:
1. Server checks if it's player's turn
2. Server checks if card index is valid
3. Server checks if card matches top card (suit OR value)
4. If valid: Card placed, effects applied, turn advances
5. If invalid: Error returned, player draws card, loses turn

---

## Future Enhancements

### Planned Features

1. **Multiple Games**: Support multiple concurrent games with unique IDs
2. **Reconnection**: Allow players to reconnect if connection drops mid-game
3. **Web UI**: Replace terminal client with web-based interface
4. **Game Persistence**: Store game state to database for recovery
5. **Dynamic Rules**: Implement the `RuleBook` system for custom rules
6. **Player Authentication**: Add user accounts and authentication
7. **Spectator Mode**: Allow watching games without playing
8. **Game History**: Record and replay past games

### Technical Improvements

1. **Database Integration**: Add PostgreSQL or MongoDB for persistence
2. **Redis for State**: Use Redis for distributed game state management
3. **Rate Limiting**: Prevent spam/abuse with rate limiting
4. **Input Validation**: Enhanced validation for all user inputs
5. **Error Recovery**: Better error handling and recovery mechanisms
6. **Testing**: Comprehensive unit and integration tests
7. **Logging**: Structured logging with rotation
8. **Monitoring**: Metrics and health checks for production

---

## Conclusion

MAOnline successfully demonstrates a client-server card game architecture with:
- Clean separation of concerns (game logic vs. networking)
- Event-driven design for scalability
- Robust error handling and recovery
- Real-time multiplayer gameplay
- Extensible architecture for future features

The project serves as a solid foundation for an online card game platform, with room for enhancement and expansion as requirements evolve.