import asyncio
import websockets
import json
import sys

class GameClient:
    """
    Terminal-based client for MAOnline game.
    Connects to server via WebSocket and handles user input/output.
    """
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws"):
        self.server_url = server_url
        self.websocket = None
        self.player_name = None
        self.game_state = None
        self.my_hand = []
        self.running = True
    
    async def connect(self):
        """Connect to the game server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"Connected to server at {self.server_url}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            sys.exit(1)
    
    async def send_message(self, message_type: str, data: dict = None):
        """Send a message to the server."""
        if data is None:
            data = {}
        message = {"type": message_type, **data}
        await self.websocket.send(json.dumps(message))
    
    async def handle_message(self, message: dict):
        """Handle incoming messages from the server."""
        msg_type = message.get("type")
        
        if msg_type == "join_success":
            print(f"\n✓ Successfully joined game as {message.get('player_name')}")
            self.player_name = message.get("player_name")
            
            #Check if we have lobby_state (waiting) or game_state (playing)
            lobby_state = message.get("lobby_state")
            if lobby_state:
                print_lobby(lobby_state)
                print("\n💡 Type 'ready' or 'r' when you're ready to start!")
            else:
                self.game_state = message.get("game_state")
                print_game_state(self.game_state)
        
        elif msg_type == "join_failed":
            reason = message.get("reason")
            print(f"Failed to join game: {reason}")
            self.running = False
        
        elif msg_type == "ready_received":
            ready_count = message.get("players_ready")
            total_players = message.get("total_players")
            print(f"Ready confirmed! ({ready_count}/{total_players} players ready)")
        
        elif msg_type == "lobby_update":
            #Clear screen and show updated lobby
            import os
            os.system('clear' if os.name != 'nt' else 'cls')
            print(f"\n=== LOBBY ===")
            print_lobby(message)
            print("\n💡 Type 'ready' or 'r' when you're ready to start!")
        
        elif msg_type == "game_state":
            self.game_state = message
            #Clear and refresh game state display
            import os
            os.system('clear' if os.name != 'nt' else 'cls')
            print("\n=== GAME STATE ===")
            #Always include hand in game state display
            print_game_state(self.game_state, hand=self.my_hand)
        
        elif msg_type == "your_hand":
            self.my_hand = message.get("cards", [])
            #Refresh display with updated hand
            if self.game_state:
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                print("\n=== GAME STATE ===")
                print_game_state(self.game_state, hand=self.my_hand)
            else:
                #Just show hand if no game state yet
                print("\n--- Your Hand ---")
                print_hand(self.my_hand)
        
        elif msg_type == "game_started":
            #Clear screen for game start
            import os
            os.system('clear' if os.name != 'nt' else 'cls')
            starting_card = message.get("starting_card")
            first_player = message.get("first_player")
            print(f"\n=== GAME STARTED ===")
            print(f"Starting card: {starting_card['value']} of {starting_card['suit']}")
            print(f"First player: {first_player}\n")
            #Show hand if we have it (will be shown in next game_state update)
            if self.my_hand:
                print("--- Your Hand ---")
                print_hand(self.my_hand)
        
        elif msg_type == "player_turn":
            player_name = message.get("player_name")
            time_limit = message.get("time_limit")
            if player_name == self.player_name:
                #Refresh display with hand on your turn (hand should be updated by now)
                if self.game_state:
                    import os
                    os.system('clear' if os.name != 'nt' else 'cls')
                    print("\n=== GAME STATE ===")
                    print_game_state(self.game_state, hand=self.my_hand)
                    print(f"\n>>> YOUR TURN! ({time_limit} seconds)")
                elif self.my_hand:
                    print("\n--- Your Hand ---")
                    print_hand(self.my_hand)
                    print(f"\n>>> YOUR TURN! ({time_limit} seconds)")
            else:
                print(f"\n>>> {player_name}'s turn ({time_limit} seconds)")
        
        elif msg_type == "card_played":
            player_name = message.get("player_name")
            card = message.get("card")
            effect = message.get("effect")
            effect_str = f" ({effect})" if effect else ""
            print(f"{player_name} played {card['value']} of {card['suit']}{effect_str}")
            #Refresh display to show updated hand if it was our card
            if player_name == self.player_name and self.game_state:
                #Clear and refresh
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                print("\n=== GAME STATE ===")
                print_game_state(self.game_state, hand=self.my_hand)
        
        elif msg_type == "card_drawn":
            card = message.get("card")
            print(f"You drew: {card['value']} of {card['suit']}")
            #Refresh display to show updated hand
            if self.game_state:
                #Clear and refresh
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                print("\n=== GAME STATE ===")
                print_game_state(self.game_state, hand=self.my_hand)
        
        elif msg_type == "turn_timeout":
            player_name = message.get("player_name")
            print(f"{player_name}'s turn timed out - auto-drawing card")
            #Refresh display to show updated game state
            if self.game_state:
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                print("\n=== GAME STATE ===")
                print_game_state(self.game_state, hand=self.my_hand)
        
        elif msg_type == "typing_rule_challenge":
            phrase = message.get("phrase")
            time_limit = message.get("time_limit")
            print(f"\n!!! TYPING RULE CHALLENGE !!!")
            print(f"Type '{phrase}' within {time_limit} seconds!")
            print("Enter your response: ", end="", flush=True)
        
        elif msg_type == "typing_rule_result":
            success = message.get("success")
            if success:
                time_taken = message.get("time_taken")
                print(f"\n✓ Success! Time: {time_taken:.2f} seconds")
            else:
                reason = message.get("reason")
                print(f"\n✗ Failed: {reason}")
        
        elif msg_type == "player_left_lobby":
            player_name = message.get("player_name")
            print(f"\n{player_name} left the lobby")
        
        elif msg_type == "player_disconnected":
            player_name = message.get("player_name")
            print(f"{player_name} disconnected")
        
        elif msg_type == "player_forfeited":
            player_name = message.get("player_name")
            print(f"{player_name} forfeited (disconnected for 2+ turns)")
        
        elif msg_type == "game_won":
            winner = message.get("winner")
            print(f"\n=== {winner} WON THE GAME! ===")
            self.running = False
        
        elif msg_type == "error":
            error_msg = message.get("message")
            error_code = message.get("error_code")
            print(f"Error: {error_msg} ({error_code})")
        
        elif msg_type == "pong":
            pass  # Ignore pong responses
        
        else:
            print(f"Unknown message type: {msg_type}")
    
    async def listen_for_messages(self):
        """Listen for messages from the server."""
        try:
            while self.running:
                message_text = await self.websocket.recv()
                try:
                    message = json.loads(message_text)
                    if message and isinstance(message, dict):
                        await self.handle_message(message)
                    else:
                        print(f"Received invalid message: {message_text}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON message: {e}")
                    print(f"Message was: {message_text}")
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.running = False
        except Exception as e:
            import traceback
            print(f"Error receiving message: {e}")
            traceback.print_exc()
            self.running = False
    
    async def handle_user_input(self):
        """Handle user input from terminal."""
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                #Wait for user input (non-blocking)
                user_input = await loop.run_in_executor(None, input, "> ")
                user_input = user_input.strip().lower()
                
                if not user_input:
                    continue
                
                #Parse commands
                if user_input == "quit" or user_input == "q":
                    #Close websocket properly to notify server
                    self.running = False
                    if self.websocket:
                        await self.websocket.close()
                    break
                
                elif user_input == "ready" or user_input == "r":
                    await self.send_message("ready")
                
                elif user_input == "draw" or user_input == "d":
                    await self.send_message("draw_card")
                
                elif user_input.startswith("play ") or user_input.startswith("p "):
                    try:
                        card_index = int(user_input.split()[1])
                        await self.send_message("play_card", {"card_index": card_index})
                    except (ValueError, IndexError):
                        print("Invalid card number. Usage: play <card_number>")
                
                elif user_input.startswith("type ") or user_input.startswith("t "):
                    #Handle typing rule response
                    response = user_input.split(" ", 1)[1] if " " in user_input else ""
                    await self.send_message("typing_rule_response", {"response": response})
                
                elif user_input == "hand" or user_input == "h":
                    #Show hand (refresh full display)
                    if self.game_state:
                        import os
                        os.system('clear' if os.name != 'nt' else 'cls')
                        print("\n=== GAME STATE ===")
                        print_game_state(self.game_state, hand=self.my_hand)
                    else:
                        print("\n--- Your Hand ---")
                        print_hand(self.my_hand)
                
                elif user_input == "state" or user_input == "s":
                    #Show game state
                    if self.game_state:
                        import os
                        os.system('clear' if os.name != 'nt' else 'cls')
                        print("\n=== GAME STATE ===")
                        print_game_state(self.game_state, hand=self.my_hand)
                    else:
                        print("No game state available")
                
                elif user_input == "help":
                    print_help()
                
                else:
                    #Check if it might be a typing rule response (just the phrase)
                    if user_input == "have a nice day":
                        await self.send_message("typing_rule_response", {"response": user_input})
                    else:
                        print("Unknown command. Type 'help' for commands.")
            
            except EOFError:
                #Ctrl+D pressed
                self.running = False
                break
            except KeyboardInterrupt:
                #Ctrl+C pressed
                self.running = False
                break
    
    async def run(self, player_name: str, game_id: str = None, password: str = None):
        """Run the client - connect and handle communication."""
        await self.connect()
        
        #Join game
        join_data = {"player_name": player_name}
        if game_id:
            join_data["game_id"] = game_id
        if password:
            join_data["password"] = password
        
        await self.send_message("join_game", join_data)
        
        #Start listening for messages
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        #Start handling user input
        input_task = asyncio.create_task(self.handle_user_input())
        
        #Wait for either task to complete
        await asyncio.gather(listen_task, input_task, return_exceptions=True)
        
        #Close connection
        if self.websocket:
            await self.websocket.close()

def print_hand(cards):
    """Print a hand of cards."""
    if not cards:
        print("(No cards in hand)")
        return
    
    print(f"Cards ({len(cards)}):")
    for i, card in enumerate(cards, 1):
        print(f"  {i}. {card['value']} of {card['suit']}")

def print_game_state(state, hand=None):
    """Print the current game state."""
    if not state:
        return
    
    print(f"\nGame Status: {state.get('game_status', 'unknown')}")
    
    #Handle top_card which may be None before game starts
    top_card = state.get('top_card')
    if top_card:
        print(f"Top Card: {top_card.get('value', '?')} of {top_card.get('suit', '?')}")
    else:
        print("Top Card: (Game not started)")
    
    print(f"Draw Pile: {state.get('draw_pile_size', 0)} cards")
    print(f"Turn Direction: {state.get('turn_direction', 'forward')}")
    print(f"Current Player: {state.get('current_player', '?')}")
    print("\nPlayers:")
    for player in state.get('players', []):
        status = "✓" if player.get('is_connected') else "✗"
        turn = " <-- YOUR TURN" if player.get('is_current_turn') else ""
        print(f"  {status} {player.get('name')}: {player.get('hand_size')} cards{turn}")
    
    #Always show hand if provided
    if hand:
        print("\n--- Your Hand ---")
        print_hand(hand)

def print_lobby(lobby_state):
    """Print the lobby state (players and ready status)."""
    if not lobby_state:
        return
    
    players_ready = lobby_state.get("players_ready", 0)
    total_players = lobby_state.get("total_players", 0)
    
    print(f"\nPlayers in lobby ({players_ready}/{total_players} ready):")
    for player in lobby_state.get("players", []):
        status = "✓" if player.get("is_connected") else "✗"
        ready = " [READY]" if player.get("is_ready") else ""
        print(f"  {status} {player.get('name')}{ready}")

def print_help():
    """Print help message."""
    print("\nCommands:")
    print("  ready, r          - Mark yourself as ready to start")
    print("  draw, d           - Draw a card")
    print("  play <n>, p <n>   - Play card number n")
    print("  type <text>, t <text> - Response to typing rule")
    print("  hand, h           - Show your hand")
    print("  state, s          - Show game state")
    print("  help              - Show this help")
    print("  quit, q           - Quit the game")
    print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MAOnline Game Client")
    parser.add_argument("--server", type=str, default="ws://localhost:8000/ws", help="Server WebSocket URL")
    parser.add_argument("--name", type=str, required=True, help="Your player name")
    parser.add_argument("--game-id", type=str, default=None, help="Game ID (optional)")
    parser.add_argument("--password", type=str, default=None, help="Game password (optional)")
    
    args = parser.parse_args()
    
    client = GameClient(server_url=args.server)
    
    try:
        asyncio.run(client.run(args.name, args.game_id, args.password))
    except KeyboardInterrupt:
        print("\nDisconnecting...")

