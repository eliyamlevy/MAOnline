# Message Protocol Design

All messages are JSON objects sent over WebSocket connections.

## Client → Server Messages

### `join_game`
Client requests to join a game lobby.

```json
{
  "type": "join_game",
  "game_id": "optional-uuid-or-empty-for-new-game",
  "password": "optional-password-if-required",
  "player_name": "Alice"
}
```

**Response:** Server sends `join_success` or `join_failed`

---

### `play_card`
Client plays a card from their hand.

```json
{
  "type": "play_card",
  "card_index": 3
}
```

**Note:** `card_index` is 1-indexed (matches current `playCard` implementation)

**Response:** Server processes move and broadcasts `game_state` and/or `card_played` to all clients. If invalid, sends `error`.

---

### `draw_card`
Client draws a card from the draw pile.

```json
{
  "type": "draw_card"
}
```

**Response:** Server sends `card_drawn` to the acting client, `your_hand` (updated), and broadcasts `game_state` to all clients.

---

### `ready`
Client indicates they are ready to start the game. Game starts when all players have sent `ready`.

```json
{
  "type": "ready"
}
```

**Response:** Server sends `ready_received` to the client, and when all players are ready, sends `game_started` to all clients.

---

### `typing_rule_response`
Client's response to the typing rule challenge (when a 7 is played).

```json
{
  "type": "typing_rule_response",
  "response": "have a nice day"
}
```

**Response:** Server validates the response and time, then either accepts (game continues) or penalizes (player draws a card).

---

### `ping`
Keep-alive message (optional, WebSocket may handle this automatically).

```json
{
  "type": "ping"
}
```

**Response:** Server responds with `pong` (optional).

---

## Server → Client Messages

### `join_success`
Confirmation that player successfully joined the game.

```json
{
  "type": "join_success",
  "game_id": "uuid-here",
  "player_name": "Alice",
  "game_state": {
    "players": [
      {
        "name": "Alice",
        "hand_size": 7,
        "is_connected": true,
        "is_current_turn": false
      },
      {
        "name": "Bob",
        "hand_size": 7,
        "is_connected": true,
        "is_current_turn": true
      }
    ],
    "top_card": {
      "suit": "Hearts",
      "value": "7"
    },
    "game_status": "playing"
  }
}
```

---

### `join_failed`
Player failed to join the game.

```json
{
  "type": "join_failed",
  "reason": "invalid_password" | "game_full" | "game_not_found" | "name_taken" | "game_already_started"
}
```

---

### `game_state`
Full game state update sent to all players when game state changes.

```json
{
  "type": "game_state",
  "game_id": "uuid-here",
  "players": [
    {
      "name": "Alice",
      "hand_size": 5,
      "is_connected": true,
      "is_current_turn": true,
      "disconnected_turns": 0
    },
    {
      "name": "Bob",
      "hand_size": 7,
      "is_connected": false,
      "is_current_turn": false,
      "disconnected_turns": 1
    },
    {
      "name": "Charlie",
      "hand_size": 6,
      "is_connected": true,
      "is_current_turn": false,
      "disconnected_turns": 0
    }
  ],
  "top_card": {
    "suit": "Spades",
    "value": "8"
  },
  "draw_pile_size": 42,
  "game_status": "playing",
  "turn_direction": "forward",
  "current_player": "Alice"
}
```

**Fields:**
- `players`: Array of all players in turn order
- `top_card`: Current card on the place pile
- `draw_pile_size`: Number of cards remaining in the draw pile
- `game_status`: `"waiting"` | `"playing"` | `"finished"`
- `turn_direction`: `"forward"` | `"reverse"`
- `current_player`: Name of player whose turn it is

**Note:** Client's own hand is sent separately in `your_hand` message (see below).

---

### `your_hand`
Sent only to the player, contains their actual hand. Automatically sent whenever the hand is updated.

```json
{
  "type": "your_hand",
  "cards": [
    {"suit": "Hearts", "value": "7"},
    {"suit": "Spades", "value": "A"},
    {"suit": "Diamonds", "value": "K"},
    {"suit": "Clubs", "value": "8"},
    {"suit": "Hearts", "value": "3"}
  ]
}
```

**Note:** Automatically sent:
- After `join_success`
- After drawing a card (in response to `draw_card`)
- After playing a card (in response to `play_card`)
- After turn timeout (if player's hand was updated)

---

### `player_turn`
Notification that a new player's turn has started.

```json
{
  "type": "player_turn",
  "player_name": "Alice",
  "time_limit": 20
}
```

---

### `card_played`
Notification that a card was played.

```json
{
  "type": "card_played",
  "player_name": "Alice",
  "card": {
    "suit": "Spades",
    "value": "8"
  },
  "effect": "skip" | "reverse" | null
}
```

**Note:** Effect is determined by game rules (e.g., 8 = skip, A = reverse).

---

### `turn_timeout`
Notification that current player's turn timed out.

```json
{
  "type": "turn_timeout",
  "player_name": "Bob",
  "action": "auto_draw_card"
}
```

---

### `player_disconnected`
Notification that a player disconnected.

```json
{
  "type": "player_disconnected",
  "player_name": "Bob",
  "can_reconnect": true,
  "disconnected_turns": 1
}
```

---

### `player_forfeited`
Notification that a player forfeited (disconnected for 2+ turns).

```json
{
  "type": "player_forfeited",
  "player_name": "Bob",
  "reason": "disconnected_for_two_turns"
}
```

---

### `player_reconnected`
Notification that a previously disconnected player reconnected.

```json
{
  "type": "player_reconnected",
  "player_name": "Bob"
}
```

---

### `card_drawn`
Notification sent to the player who drew a card, telling them what card they drew.

```json
{
  "type": "card_drawn",
  "card": {
    "suit": "Diamonds",
    "value": "5"
  }
}
```

**Note:** Sent in response to `draw_card` action, before sending `your_hand` update.

---

### `game_started`
Notification that the game has started (sent to all players when first card is placed).

```json
{
  "type": "game_started",
  "starting_card": {
    "suit": "Hearts",
    "value": "7"
  },
  "first_player": "Alice"
}
```

---

### `game_won`
Notification that a player won the game.

```json
{
  "type": "game_won",
  "winner": "Alice"
}
```

---

### `error`
Error message sent to client.

```json
{
  "type": "error",
  "message": "Invalid move: card doesn't match top card",
  "error_code": "INVALID_MOVE"
}
```

**Possible error codes:**
- `INVALID_MOVE`: Card doesn't match suit or value (player draws a card and loses turn)
- `NOT_YOUR_TURN`: Attempted move when not player's turn
- `INVALID_CARD_INDEX`: Card index out of range
- `GAME_NOT_STARTED`: Attempted move before game started
- `GAME_FINISHED`: Attempted move after game ended

---

### `ready_received`
Confirmation that server received the ready message.

```json
{
  "type": "ready_received",
  "players_ready": 2,
  "total_players": 4
}
```

---

### `typing_rule_challenge`
Notification that a 7 was played, triggering the typing rule challenge.

```json
{
  "type": "typing_rule_challenge",
  "player_name": "Alice",
  "phrase": "have a nice day",
  "time_limit": 7
}
```

**Note:** Sent to the player who played the 7. They have 7 seconds to respond with `typing_rule_response`.

---

### `typing_rule_result`
Result of the typing rule challenge.

```json
{
  "type": "typing_rule_result",
  "player_name": "Alice",
  "success": true,
  "time_taken": 3.5
}
```

or if failed:

```json
{
  "type": "typing_rule_result",
  "player_name": "Alice",
  "success": false,
  "reason": "timeout" | "incorrect_phrase"
}
```

**Note:** If failed, player automatically draws a card as penalty.

---

## Message Flow Examples

### Player Joins Game

1. Client → Server: `join_game`
2. Server → Client: `join_success` (includes `game_state` and `your_hand`)
3. Server → All Clients: `game_state` (updated player list)

### Player Draws Card

1. Client → Server: `draw_card`
2. Server processes move
3. Server → Acting Client: `card_drawn` (what card was drawn)
4. Server → Acting Client: `your_hand` (updated hand)
5. Server → All Clients: `game_state` (updated state, including draw_pile_size)
6. Server advances to next player
7. Server → All Clients: `player_turn` and `game_state`

### Player Plays Card

1. Client → Server: `play_card`
2. Server validates move
3. If valid:
   - Server → All Clients: `card_played`
   - Server → All Clients: `game_state` (updated state)
   - Server → Acting Client: `your_hand` (updated hand)
   - If effect (skip/reverse): Server → All Clients: `game_state` (updated turn order)
   - Server advances to next player
   - Server → All Clients: `player_turn` and `game_state`
4. If invalid:
   - Server → Acting Client: `error`

### Turn Timeout

1. Server timer expires
2. Server → All Clients: `turn_timeout`
3. Server auto-draws card for timed-out player
4. Server → Timed-out Client (if connected): `card_drawn` (card that was auto-drawn)
5. Server → Timed-out Client (if connected): `your_hand` (updated hand)
6. Server → All Clients: `game_state` (updated state)
7. Server advances to next player
8. Server → All Clients: `player_turn` and `game_state`

### Player Ready

1. Client → Server: `ready`
2. Server → Client: `ready_received` (with count of ready players)
3. Server checks if all players are ready
4. If all ready:
   - Server deals cards to all players
   - Server places first card on place pile
   - Server → All Clients: `game_started` (with starting card and first player)
   - Server → All Clients: `game_state` (initial game state, status = "playing")
   - Server → Each Client: `your_hand` (their hand)
   - Server → All Clients: `player_turn` (first player's turn)

### Player Plays Card (Invalid Move)

1. Client → Server: `play_card`
2. Server validates move
3. If invalid:
   - Server → Acting Client: `error` (with INVALID_MOVE code)
   - Server auto-draws card for player (penalty)
   - Server → Acting Client: `card_drawn` (penalty card)
   - Server → Acting Client: `your_hand` (updated hand)
   - Server → All Clients: `game_state` (updated state)
   - Server advances to next player (player loses turn)
   - Server → All Clients: `player_turn` and `game_state`

### Player Plays 7 (Typing Rule)

1. Client → Server: `play_card` (card_index of a 7)
2. Server validates card matches top card
3. If valid:
   - Server → All Clients: `card_played` (card with effect: "typing_rule")
   - Server → Acting Client: `typing_rule_challenge` (with phrase and 7 second timer)
   - Server starts 7-second timer
4. If client responds in time with correct phrase:
   - Server → Acting Client: `typing_rule_result` (success with time)
   - Server → All Clients: `game_state` (updated state)
   - Server advances to next player
5. If client times out or gives wrong phrase:
   - Server → Acting Client: `typing_rule_result` (failure with reason)
   - Server auto-draws card for player (penalty)
   - Server → Acting Client: `card_drawn` (penalty card)
   - Server → Acting Client: `your_hand` (updated hand)
   - Server → All Clients: `game_state` (updated state)
   - Server advances to next player

