import core.cardgamecore as cardGameCore
import asyncio
from typing import Dict, List, Optional, Callable
from collections import deque

#work in progress
ruleDict = {
    'A': "reverse",
    '8': "skip",
    '7': "have a nice day"
}

class GameInstance:
    """
    Manages a single game instance with all game logic, state, and player connections.
    Event-driven design - no blocking I/O, all actions trigger callbacks.
    """
    
    def __init__(self, game_id: str, password: Optional[str], turn_timeout: int = 20):
        self.game_id = game_id
        self.password = password
        self.turn_timeout = turn_timeout
        
        #Game state
        self.status = "waiting"  # "waiting", "playing", "finished"
        
        #Players and connections
        self.players: List[cardGameCore.Player] = []
        self.player_connections: Dict[str, any] = {}  # player_name -> WebSocket
        self.player_ready: Dict[str, bool] = {}  # player_name -> ready status
        self.player_disconnected_turns: Dict[str, int] = {}  # player_name -> consecutive missed turns
        
        #Decks
        self.drawPile = cardGameCore.Deck()
        self.placePile = cardGameCore.Deck()
        self.topCard: Optional[cardGameCore.Card] = None
        
        #Turn management
        self.current_player_index = 0
        self.reverse = False
        self.skip = False
        self.revSkip = False
        
        #Typing rule state
        self.active_typing_challenge: Optional[str] = None  # player_name who has active challenge
        self.typing_challenge_start_time: Optional[float] = None
        self.typing_challenge_timer: Optional[asyncio.Task] = None
        
        #Turn timer
        self.turn_timer: Optional[asyncio.Task] = None
        
        #Callbacks for broadcasting messages (deprecated - messaging handled in server layer)
        self.broadcast_callback: Optional[Callable] = None
        self.send_to_player_callback: Optional[Callable] = None
        
        #Pending events for server to handle
        self.pending_timeout_broadcast: Optional[dict] = None
        self.last_timeout_player: Optional[str] = None
        self.last_timeout_card: Optional[cardGameCore.Card] = None
        self.last_card_drawn: Optional[dict] = None
        self.last_card_played: Optional[dict] = None
        self.last_typing_result: Optional[dict] = None
        self.last_player_forfeited: Optional[dict] = None
        self.last_game_won: Optional[dict] = None
        
    def initialize_deck(self):
        """Initialize a full 52-card deck and shuffle it."""
        #Add cards to draw pile
        for suit in ["Clubs", "Spades", "Diamonds", "Hearts"]:
            for value in range(1, 14):
                if value == 1:
                    cardVal = 'A'
                elif value == 11:
                    cardVal = 'J'
                elif value == 12:
                    cardVal = 'Q'
                elif value == 13:
                    cardVal = 'K'
                else:
                    cardVal = str(value)
                self.drawPile.placeCardOnBottom(cardGameCore.Card(suit, cardVal))
        #shuffle pile
        self.drawPile.shuffleDeck()
    
    def add_player(self, player_name: str, websocket) -> bool:
        """
        Add a player to the game. Returns True if successful, False if name already taken.
        """
        #Check if name is taken
        for player in self.players:
            if player.name == player_name:
                return False
        
        #Add player
        player = cardGameCore.Player(player_name)
        self.players.append(player)
        self.player_connections[player_name] = websocket
        self.player_ready[player_name] = False
        self.player_disconnected_turns[player_name] = 0
        return True
    
    def remove_player_connection(self, player_name: str):
        """Remove a player's connection (on disconnect)."""
        if player_name in self.player_connections:
            del self.player_connections[player_name]
    
    def remove_player_from_game(self, player_name: str):
        """Completely remove a player from the game (before game starts)."""
        #Remove player from players list
        player_to_remove = None
        for player in self.players:
            if player.name == player_name:
                player_to_remove = player
                break
        
        if player_to_remove:
            self.players.remove(player_to_remove)
        
        #Remove from all tracking dictionaries
        if player_name in self.player_connections:
            del self.player_connections[player_name]
        if player_name in self.player_ready:
            del self.player_ready[player_name]
        if player_name in self.player_disconnected_turns:
            del self.player_disconnected_turns[player_name]
    
    def set_player_connection(self, player_name: str, websocket):
        """Set or update a player's connection."""
        self.player_connections[player_name] = websocket
        #Reset disconnect counter if player reconnects
        if player_name in self.player_disconnected_turns:
            self.player_disconnected_turns[player_name] = 0
    
    def is_player_connected(self, player_name: str) -> bool:
        """Check if a player is currently connected."""
        return player_name in self.player_connections and self.player_connections[player_name] is not None
    
    def set_player_ready(self, player_name: str) -> bool:
        """
        Mark a player as ready. Returns True if all players are now ready and game should start.
        """
        if player_name not in self.player_ready:
            return False
        
        self.player_ready[player_name] = True
        
        #Check if all players are ready
        if all(self.player_ready.values()) and len(self.players) > 0:
            return True
        return False
    
    def start_game(self):
        """Initialize and start the game - deal cards and place first card."""
        if self.status != "waiting":
            return
        
        self.status = "playing"
        
        #Deal out cards (7 per player)
        for player in self.players:
            for i in range(7):
                player.giveCard(self.drawPile.getTopCard())
        
        #Place first card on place pile
        self.topCard = self.drawPile.getTopCard()
        self.placePile.placeCardOnTop(self.topCard)
        
        #Start first player's turn
        self.current_player_index = 0
        self.start_player_turn()
    
    def get_current_player(self) -> Optional[cardGameCore.Player]:
        """Get the current player whose turn it is."""
        if len(self.players) == 0:
            return None
        
        #Calculate player index based on reverse direction
        if self.reverse:
            player_index = len(self.players) - 1 - self.current_player_index
        else:
            player_index = self.current_player_index
        
        if 0 <= player_index < len(self.players):
            return self.players[player_index]
        return None
    
    def start_player_turn(self):
        """Start the current player's turn and set up timer."""
        #Cancel any existing turn timer
        if self.turn_timer:
            self.turn_timer.cancel()
        
        player = self.get_current_player()
        if not player:
            return
        
        #Check if player is disconnected
        if not self.is_player_connected(player.name):
            #Increment disconnect counter
            self.player_disconnected_turns[player.name] = self.player_disconnected_turns.get(player.name, 0) + 1
            
            #If disconnected for 2+ turns, forfeit
            if self.player_disconnected_turns[player.name] >= 2:
                self.forfeit_player(player.name)
                #Move to next player
                self.advance_to_next_player()
                return
        
        #Start turn timer
        self.turn_timer = asyncio.create_task(self.handle_turn_timeout())
        
        #Note: Hand and turn notifications are sent from server layer
        #This ensures proper async handling
    
    async def handle_turn_timeout(self):
        """Handle when a player's turn times out."""
        try:
            await asyncio.sleep(self.turn_timeout)
            
            #Only process if still this player's turn
            player = self.get_current_player()
            if player:
                #Auto-draw card
                if not self.drawPile.empty():
                    drawn_card = self.drawPile.getTopCard()
                    player.giveCard(drawn_card)
                    
                    #Note: Hand and timeout notifications are sent from server layer
                    #Store timeout info for server to broadcast
                    self.last_timeout_player = player.name
                    self.last_timeout_card = drawn_card
                
                #Broadcast timeout (server will handle async)
                #Store timeout info for server to broadcast
                self.pending_timeout_broadcast = {
                    "player_name": player.name,
                    "action": "auto_draw_card"
                }
                
                #Advance to next player
                self.advance_to_next_player()
        except asyncio.CancelledError:
            #Turn was cancelled (normal when player makes a move)
            pass
    
    def advance_to_next_player(self):
        """Move to the next player's turn."""
        #Cancel turn timer
        if self.turn_timer:
            self.turn_timer.cancel()
            self.turn_timer = None
        
        #Move to next player (always increment index, get_current_player handles reverse)
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        #Handle skip
        if self.skip:
            self.skip = False
            #Skip this player - move to next again
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        #Start next player's turn
        self.start_player_turn()
    
    def check_draw_pile(self):
        """Check if draw pile is empty and redistribute if needed."""
        if self.drawPile.empty():
            #Keep top card, redistribute the rest
            top = self.placePile.getTopCard()
            while not self.placePile.empty():
                self.drawPile.placeCardOnTop(self.placePile.getTopCard())
            self.drawPile.shuffleDeck()
            #Put top card back
            self.placePile.placeCardOnTop(top)
    
    def handle_draw_card(self, player_name: str) -> Optional[dict]:
        """
        Handle a player drawing a card. Returns error dict if invalid, None if successful.
        """
        player = self.get_current_player()
        if not player or player.name != player_name:
            return {"error_code": "NOT_YOUR_TURN", "message": "It is not your turn"}
        
        #Check draw pile
        self.check_draw_pile()
        
        if self.drawPile.empty():
            return {"error_code": "DRAW_PILE_EMPTY", "message": "Draw pile is empty"}
        
        #Draw card
        drawn_card = self.drawPile.getTopCard()
        player.giveCard(drawn_card)
        
        #Note: Messaging is handled in server layer
        #Store card_drawn info for server notification
        self.last_card_drawn = {
            "player_name": player_name,
            "card": drawn_card
        }
        
        #Advance to next player
        self.advance_to_next_player()
        
        return None
    
    def handle_play_card(self, player_name: str, card_index: int) -> Optional[dict]:
        """
        Handle a player playing a card. Returns error dict if invalid, None if successful.
        """
        player = self.get_current_player()
        if not player or player.name != player_name:
            return {"error_code": "NOT_YOUR_TURN", "message": "It is not your turn"}
        
        #Validate card index
        if card_index < 1 or card_index > len(player.hand):
            return {"error_code": "INVALID_CARD_INDEX", "message": "Invalid card index"}
        
        #Check draw pile
        self.check_draw_pile()
        
        #Get the chosen card
        card_chosen = player.playCard(card_index)
        
        #Check if card matches top card
        if card_chosen.suit != self.topCard.suit and card_chosen.value != self.topCard.value:
            #Invalid move - penalty
            #House rule: give player top card and draw a card
            if not self.placePile.empty():
                stupidity_card = self.placePile.getTopCard()
                player.giveCard(stupidity_card)
            
            if not self.drawPile.empty():
                penalty_card = self.drawPile.getTopCard()
                player.giveCard(penalty_card)
                
                #Note: Messaging is handled in server layer
                #Store card_drawn info for server notification
                self.last_card_drawn = {
                    "player_name": player_name,
                    "card": penalty_card
                }
            
            #Player loses turn
            self.advance_to_next_player()
            
            return {"error_code": "INVALID_MOVE", "message": "Card doesn't match top card"}
        
        #Valid move - place card
        self.placePile.placeCardOnTop(card_chosen)
        self.topCard = card_chosen
        
        #Check for win condition
        if len(player.hand) == 0:
            self.status = "finished"
            self.last_game_won = {"winner": player_name}
            return None
        
        #Check for special card effects
        effect = None
        if card_chosen.value == '8':
            self.skip = True
            effect = "skip"
        elif card_chosen.value == 'A':
            self.reverse = not self.reverse
            self.skip = True
            effect = "reverse"
        elif card_chosen.value == '7':
            #Trigger typing rule challenge
            effect = "typing_rule"
            self.start_typing_challenge(player_name)
        
        #Broadcast card played (server will handle async)
        self.last_card_played = {
            "player_name": player_name,
            "card": {"suit": card_chosen.suit, "value": card_chosen.value},
            "effect": effect
        }
        
        #Note: Hand updates are sent in the server handler AFTER advance_to_next_player
        #because advance_to_next_player changes the current player, and we need to
        #send the hand to the player who just played (player_name), not the new current player
        
        #If not a typing rule, advance to next player
        if card_chosen.value != '7':
            self.advance_to_next_player()
        
        return None
    
    def start_typing_challenge(self, player_name: str):
        """Start the typing rule challenge for a player who played a 7."""
        self.active_typing_challenge = player_name
        import time
        self.typing_challenge_start_time = time.time()
        
        #Send challenge to player
        if self.send_to_player_callback:
            self.send_to_player_callback("typing_rule_challenge", {
                "player_name": player_name,
                "phrase": "have a nice day",
                "time_limit": 7
            }, player_name)
        
        #Start 7-second timer
        self.typing_challenge_timer = asyncio.create_task(self.handle_typing_challenge_timeout())
    
    async def handle_typing_challenge_timeout(self):
        """Handle typing challenge timeout."""
        try:
            await asyncio.sleep(7)
            
            #If challenge is still active, player failed
            if self.active_typing_challenge:
                player_name = self.active_typing_challenge
                self.handle_typing_challenge_failure(player_name, "timeout")
        except asyncio.CancelledError:
            #Challenge was completed
            pass
    
    def handle_typing_response(self, player_name: str, response: str):
        """Handle a player's response to the typing challenge."""
        if self.active_typing_challenge != player_name:
            return
        
        #Cancel timeout timer
        if self.typing_challenge_timer:
            self.typing_challenge_timer.cancel()
            self.typing_challenge_timer = None
        
        import time
        time_taken = time.time() - self.typing_challenge_start_time
        
        #Check if response is correct and within time limit
        if time_taken > 7 or response.lower() != "have a nice day":
            self.handle_typing_challenge_failure(player_name, "incorrect_phrase" if response.lower() != "have a nice day" else "timeout")
        else:
            #Success
            self.active_typing_challenge = None
            self.typing_challenge_start_time = None
            
            if self.send_to_player_callback:
                self.send_to_player_callback("typing_rule_result", {
                    "player_name": player_name,
                    "success": True,
                    "time_taken": time_taken
                }, player_name)
            
            #Advance to next player
            self.advance_to_next_player()
    
    def handle_typing_challenge_failure(self, player_name: str, reason: str):
        """Handle typing challenge failure - player draws a card."""
        player = None
        for p in self.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return
        
        #Draw penalty card
        self.check_draw_pile()
        if not self.drawPile.empty():
            penalty_card = self.drawPile.getTopCard()
            player.giveCard(penalty_card)
            
            #Store updates for server to send
            self.last_typing_result = {
                "player_name": player_name,
                "success": False,
                "reason": reason
            }
            self.last_card_drawn = {
                "player_name": player_name,
                "card": penalty_card
            }
        
        #Clear challenge state
        self.active_typing_challenge = None
        self.typing_challenge_start_time = None
        
        #Advance to next player
        self.advance_to_next_player()
    
    def forfeit_player(self, player_name: str):
        """Forfeit a player - return their hand to draw pile and remove them."""
        player = None
        for p in self.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return
        
        #Return all cards to draw pile
        for card in player.hand:
            self.drawPile.placeCardOnBottom(card)
        player.hand.clear()
        
        #Remove player
        self.players.remove(player)
        if player_name in self.player_connections:
            del self.player_connections[player_name]
        if player_name in self.player_ready:
            del self.player_ready[player_name]
        if player_name in self.player_disconnected_turns:
            del self.player_disconnected_turns[player_name]
        
        #Store forfeit event for server to broadcast
        self.last_player_forfeited = {
            "player_name": player_name,
            "reason": "disconnected_for_two_turns"
        }
        
        #Adjust current player index if needed
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
    
    def get_game_state(self) -> dict:
        """Get the current game state as a dictionary."""
        players_data = []
        for i, player in enumerate(self.players):
            is_current = (i == self.current_player_index) if not self.reverse else (i == len(self.players) - 1 - self.current_player_index)
            #Get hand size directly from player object to ensure accuracy
            hand_size = len(player.hand)
            players_data.append({
                "name": player.name,
                "hand_size": hand_size,
                "is_connected": self.is_player_connected(player.name),
                "is_current_turn": is_current,
                "disconnected_turns": self.player_disconnected_turns.get(player.name, 0)
            })
        
        return {
            "game_id": self.game_id,
            "players": players_data,
            "top_card": {"suit": self.topCard.suit, "value": self.topCard.value} if self.topCard else None,
            "draw_pile_size": len(self.drawPile.cards),
            "game_status": self.status,
            "turn_direction": "reverse" if self.reverse else "forward",
            "current_player": self.get_current_player().name if self.get_current_player() else None
        }
    
    def get_player_hand(self, player_name: str) -> Optional[list]:
        """Get a player's hand as a list of card dicts."""
        for player in self.players:
            if player.name == player_name:
                #Return hand directly from player object to ensure accuracy
                return [{"suit": c.suit, "value": c.value} for c in player.hand]
        return None
    
    def get_player_hand_size(self, player_name: str) -> int:
        """Get a player's hand size directly."""
        for player in self.players:
            if player.name == player_name:
                return len(player.hand)
        return 0
    
    def get_lobby_state(self) -> dict:
        """Get the lobby state (players and ready status) for waiting phase."""
        players_data = []
        for player in self.players:
            players_data.append({
                "name": player.name,
                "is_connected": self.is_player_connected(player.name),
                "is_ready": self.player_ready.get(player.name, False)
            })
        
        return {
            "game_id": self.game_id,
            "players": players_data,
            "players_ready": sum(1 for ready in self.player_ready.values() if ready),
            "total_players": len(self.players)
        }

