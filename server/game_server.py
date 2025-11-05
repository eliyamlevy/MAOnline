from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import json
import argparse
import asyncio
import sys
import os
from typing import Dict, Optional

#Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.game_manager import GameManager
from server.game_instance import GameInstance

#Global game manager
game_manager = GameManager()

#Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}  # player_name -> WebSocket

#Game will be created with server configuration in __main__ block

async def send_to_player(player_name: str, message_type: str, data: dict):
    """Send a message to a specific player."""
    if player_name in active_connections:
        try:
            websocket = active_connections[player_name]
            message = {"type": message_type, **data}
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending to {player_name}: {e}")

async def broadcast_to_game_async(game: GameInstance, message_type: str, data: dict):
    """Async version of broadcast - sends to all connected players in a game."""
    tasks = []
    for player_name, websocket in active_connections.items():
        #Check if player is in this game
        player_in_game = any(p.name == player_name for p in game.players)
        if player_in_game:
            try:
                message = {"type": message_type, **data}
                tasks.append(websocket.send_json(message))
            except Exception as e:
                print(f"Error broadcasting to {player_name}: {e}")
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def check_and_handle_pending_events(game: GameInstance):
    """Check for pending events from game instance and handle them."""
    #Handle timeout broadcast
    if game.pending_timeout_broadcast:
        #Send hand and card_drawn to timed-out player if they're still connected
        if game.last_timeout_player and game.is_player_connected(game.last_timeout_player):
            player = None
            for p in game.players:
                if p.name == game.last_timeout_player:
                    player = p
                    break
            
            if player:
                hand = [{"suit": c.suit, "value": c.value} for c in player.hand]
                await send_to_player(game.last_timeout_player, "your_hand", {"cards": hand})
                
                if game.last_timeout_card:
                    await send_to_player(game.last_timeout_player, "card_drawn", {
                        "card": {"suit": game.last_timeout_card.suit, "value": game.last_timeout_card.value}
                    })
        
        #Broadcast timeout event
        await broadcast_to_game_async(game, "turn_timeout", game.pending_timeout_broadcast)
        
        #Broadcast updated game state
        game_state = game.get_game_state()
        await broadcast_to_game_async(game, "game_state", game_state)
        
        #Send player turn to new current player
        current_player = game.get_current_player()
        if current_player:
            current_hand = game.get_player_hand(current_player.name)
            if current_hand:
                await send_to_player(current_player.name, "your_hand", {"cards": current_hand})
            
            await broadcast_to_game_async(game, "player_turn", {
                "player_name": current_player.name,
                "time_limit": game.turn_timeout
            })
        
        game.pending_timeout_broadcast = None
        game.last_timeout_player = None
        game.last_timeout_card = None
    
    #Handle game won
    if game.last_game_won:
        await broadcast_to_game_async(game, "game_won", game.last_game_won)
        game.last_game_won = None
    
    #Handle player forfeited
    if game.last_player_forfeited:
        await broadcast_to_game_async(game, "player_forfeited", game.last_player_forfeited)
        game.last_player_forfeited = None

async def background_event_checker():
    """Background task to check for pending events from games."""
    while True:
        try:
            await asyncio.sleep(0.1)  #Check every 100ms
            #Check all games for pending events
            for game in game_manager.games.values():
                await check_and_handle_pending_events(game)
        except Exception as e:
            print(f"Error in background event checker: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown tasks."""
    #Start background task for checking game events
    task = asyncio.create_task(background_event_checker())
    yield
    #Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for game connections.
    Handles all client communication.
    """
    await websocket.accept()
    
    game: Optional[GameInstance] = None
    player_name: Optional[str] = None
    
    try:
        while True:
            #Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                    "error_code": "INVALID_JSON"
                })
                continue
            
            message_type = message.get("type")
            
            #Handle join_game
            if message_type == "join_game":
                if player_name:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Already joined a game",
                        "error_code": "ALREADY_JOINED"
                    })
                    continue
                
                game_id = message.get("game_id")
                password = message.get("password")
                player_name = message.get("player_name")
                
                if not player_name:
                    await websocket.send_json({
                        "type": "join_failed",
                        "reason": "missing_player_name"
                    })
                    continue
                
                #Get or create game
                game = game_manager.get_or_create_default_game()
                
                #Check password if game has one
                if game.password and game.password != password:
                    await websocket.send_json({
                        "type": "join_failed",
                        "reason": "invalid_password"
                    })
                    continue
                
                #Check if game already started
                if game.status != "waiting":
                    await websocket.send_json({
                        "type": "join_failed",
                        "reason": "game_already_started"
                    })
                    continue
                
                #Add player
                success = game.add_player(player_name, websocket)
                if not success:
                    await websocket.send_json({
                        "type": "join_failed",
                        "reason": "name_taken"
                    })
                    continue
                
                #Store connection
                active_connections[player_name] = websocket
                
                #Set up callbacks
                async def broadcast_callback(msg_type, msg_data):
                    await broadcast_to_game_async(game, msg_type, msg_data)
                
                async def send_to_player_callback(msg_type, msg_data, target_player):
                    await send_to_player(target_player, msg_type, msg_data)
                
                game.broadcast_callback = broadcast_callback
                game.send_to_player_callback = send_to_player_callback
                
                #Send join success
                if game.status == "waiting":
                    #Send lobby state for waiting phase
                    lobby_state = game.get_lobby_state()
                    await websocket.send_json({
                        "type": "join_success",
                        "game_id": game.game_id,
                        "player_name": player_name,
                        "lobby_state": lobby_state
                    })
                    
                    #Broadcast updated lobby state to all players
                    await broadcast_to_game_async(game, "lobby_update", lobby_state)
                else:
                    #Game already started - send full game state
                    game_state = game.get_game_state()
                    player_hand = game.get_player_hand(player_name)
                    
                    await websocket.send_json({
                        "type": "join_success",
                        "game_id": game.game_id,
                        "player_name": player_name,
                        "game_state": game_state
                    })
                    
                    if player_hand:
                        await websocket.send_json({
                            "type": "your_hand",
                            "cards": player_hand
                        })
                    
                    #Broadcast updated game state to all players
                    await broadcast_to_game_async(game, "game_state", game_state)
            
            #Handle ready
            elif message_type == "ready":
                if not game or not player_name:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not in a game",
                        "error_code": "NOT_IN_GAME"
                    })
                    continue
                
                all_ready = game.set_player_ready(player_name)
                
                #Send ready confirmation
                ready_count = sum(1 for ready in game.player_ready.values() if ready)
                total_players = len(game.players)
                
                await websocket.send_json({
                    "type": "ready_received",
                    "players_ready": ready_count,
                    "total_players": total_players
                })
                
                #If all ready, start game
                if all_ready:
                    game.start_game()
                    
                    #Send game_started to all
                    current_player = game.get_current_player()
                    await broadcast_to_game_async(game, "game_started", {
                        "starting_card": {
                            "suit": game.topCard.suit,
                            "value": game.topCard.value
                        },
                        "first_player": current_player.name if current_player else None
                    })
                    
                    #Send game state and hands
                    game_state = game.get_game_state()
                    await broadcast_to_game_async(game, "game_state", game_state)
                    
                    #Send each player their hand
                    for player in game.players:
                        hand = game.get_player_hand(player.name)
                        if hand:
                            await send_to_player(player.name, "your_hand", {"cards": hand})
                    
                    #Send first player turn
                    if current_player:
                        await broadcast_to_game_async(game, "player_turn", {
                            "player_name": current_player.name,
                            "time_limit": game.turn_timeout
                        })
                else:
                    #Broadcast updated lobby state
                    lobby_state = game.get_lobby_state()
                    await broadcast_to_game_async(game, "lobby_update", lobby_state)
            
            #Handle draw_card
            elif message_type == "draw_card":
                if not game or not player_name:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not in a game",
                        "error_code": "NOT_IN_GAME"
                    })
                    continue
                
                if game.status != "playing":
                    await websocket.send_json({
                        "type": "error",
                        "message": "Game not started",
                        "error_code": "GAME_NOT_STARTED"
                    })
                    continue
                
                error = game.handle_draw_card(player_name)
                if error:
                    await websocket.send_json({
                        "type": "error",
                        **error
                    })
                else:
                    #handle_draw_card calls advance_to_next_player, so current player has changed
                    #But we need to send the hand to the player who just drew (player_name)
                    #Get the player object directly to ensure we're reading the same state
                    target_player = None
                    for player in game.players:
                        if player.name == player_name:
                            target_player = player
                            break
                    
                    if target_player:
                        #Get hand directly from player object (same one used in get_game_state)
                        hand = [{"suit": c.suit, "value": c.value} for c in target_player.hand]
                        #Send hand update immediately (before game_state)
                        await send_to_player(player_name, "your_hand", {"cards": hand})
                    
                    #Send card_drawn notification if available
                    if game.last_card_drawn and game.last_card_drawn.get("player_name") == player_name:
                        card_info = game.last_card_drawn["card"]
                        await send_to_player(player_name, "card_drawn", {
                            "card": {"suit": card_info.suit, "value": card_info.value}
                        })
                        game.last_card_drawn = None
                    
                    #Check for pending events (like timeouts)
                    await check_and_handle_pending_events(game)
                    
                    #Now broadcast game state (hand count will match what we just sent)
                    #get_game_state reads from the same player objects, so sizes will match
                    game_state = game.get_game_state()
                    await broadcast_to_game_async(game, "game_state", game_state)
                    
                    #Send player turn if needed
                    current_player = game.get_current_player()
                    if current_player:
                        #Send hand to current player before their turn
                        current_hand = game.get_player_hand(current_player.name)
                        if current_hand:
                            await send_to_player(current_player.name, "your_hand", {"cards": current_hand})
                        
                        await broadcast_to_game_async(game, "player_turn", {
                            "player_name": current_player.name,
                            "time_limit": game.turn_timeout
                        })
            
            #Handle play_card
            elif message_type == "play_card":
                if not game or not player_name:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not in a game",
                        "error_code": "NOT_IN_GAME"
                    })
                    continue
                
                if game.status != "playing":
                    await websocket.send_json({
                        "type": "error",
                        "message": "Game not started",
                        "error_code": "GAME_NOT_STARTED"
                    })
                    continue
                
                card_index = message.get("card_index")
                if card_index is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing card_index",
                        "error_code": "MISSING_CARD_INDEX"
                    })
                    continue
                
                error = game.handle_play_card(player_name, card_index)
                if error:
                    await websocket.send_json({
                        "type": "error",
                        **error
                    })
                    
                    #Send hand update immediately for invalid move (player got penalty cards)
                    #Get the player object directly to ensure we're reading the same state
                    target_player = None
                    for player in game.players:
                        if player.name == player_name:
                            target_player = player
                            break
                    
                    if target_player:
                        #Get hand directly from player object (same one used in get_game_state)
                        hand = [{"suit": c.suit, "value": c.value} for c in target_player.hand]
                        await send_to_player(player_name, "your_hand", {"cards": hand})
                    
                    #Now broadcast game state (hand count will match)
                    game_state = game.get_game_state()
                    await broadcast_to_game_async(game, "game_state", game_state)
                    
                    #Send player turn
                    current_player = game.get_current_player()
                    if current_player:
                        await broadcast_to_game_async(game, "player_turn", {
                            "player_name": current_player.name,
                            "time_limit": game.turn_timeout
                        })
                else:
                    #Broadcast card_played if available
                    if game.last_card_played:
                        await broadcast_to_game_async(game, "card_played", game.last_card_played)
                        game.last_card_played = None
                    
                    #handle_play_card calls advance_to_next_player, so current player has changed
                    #But we need to send the hand to the player who just played (player_name)
                    #Get the player object directly to ensure we're reading the same state
                    target_player = None
                    for player in game.players:
                        if player.name == player_name:
                            target_player = player
                            break
                    
                    if target_player:
                        #Get hand directly from player object (same one used in get_game_state)
                        hand = [{"suit": c.suit, "value": c.value} for c in target_player.hand]
                        #Send hand update immediately (before game_state)
                        await send_to_player(player_name, "your_hand", {"cards": hand})
                    
                    #Check for pending events (like timeouts)
                    await check_and_handle_pending_events(game)
                    
                    #Now broadcast game state (hand count will match what we just sent)
                    #get_game_state reads from the same player objects, so sizes will match
                    game_state = game.get_game_state()
                    await broadcast_to_game_async(game, "game_state", game_state)
                    
                    #Send player turn if needed (unless typing challenge)
                    if game.active_typing_challenge != player_name:
                        current_player = game.get_current_player()
                        if current_player:
                            #Send hand to current player before their turn
                            current_hand = game.get_player_hand(current_player.name)
                            if current_hand:
                                await send_to_player(current_player.name, "your_hand", {"cards": current_hand})
                            
                            await broadcast_to_game_async(game, "player_turn", {
                                "player_name": current_player.name,
                                "time_limit": game.turn_timeout
                            })
            
            #Handle typing_rule_response
            elif message_type == "typing_rule_response":
                if not game or not player_name:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not in a game",
                        "error_code": "NOT_IN_GAME"
                    })
                    continue
                
                response = message.get("response", "")
                game.handle_typing_response(player_name, response)
                
                #Send typing result if available
                if game.last_typing_result:
                    await send_to_player(player_name, "typing_rule_result", game.last_typing_result)
                    
                    #Send hand if player drew a penalty card
                    if not game.last_typing_result.get("success") and game.last_card_drawn:
                        card_info = game.last_card_drawn["card"]
                        await send_to_player(player_name, "card_drawn", {
                            "card": {"suit": card_info.suit, "value": card_info.value}
                        })
                    
                    game.last_typing_result = None
                
                #Send hand update
                hand = game.get_player_hand(player_name)
                if hand:
                    await send_to_player(player_name, "your_hand", {"cards": hand})
                
                #Broadcast updated game state
                game_state = game.get_game_state()
                await broadcast_to_game_async(game, "game_state", game_state)
                
                #Send player turn if needed
                current_player = game.get_current_player()
                if current_player:
                    #Send hand to current player before their turn
                    current_hand = game.get_player_hand(current_player.name)
                    if current_hand:
                        await send_to_player(current_player.name, "your_hand", {"cards": current_hand})
                    
                    await broadcast_to_game_async(game, "player_turn", {
                        "player_name": current_player.name,
                        "time_limit": game.turn_timeout
                    })
            
            #Handle ping
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "error_code": "UNKNOWN_MESSAGE_TYPE"
                })
    
    except WebSocketDisconnect:
        #Handle disconnect
        if player_name and game:
            #If game hasn't started, completely remove the player
            if game.status == "waiting":
                #Remove player from game completely
                game.remove_player_from_game(player_name)
                if player_name in active_connections:
                    del active_connections[player_name]
                
                #Broadcast player left lobby
                await broadcast_to_game_async(game, "player_left_lobby", {
                    "player_name": player_name
                })
                
                #Broadcast updated lobby state
                lobby_state = game.get_lobby_state()
                await broadcast_to_game_async(game, "lobby_update", lobby_state)
            else:
                #Game has started - handle as disconnect
                #For now, remove player completely even during game (as per requirement)
                #In future versions, we can add reconnection logic
                game.remove_player_from_game(player_name)
                if player_name in active_connections:
                    del active_connections[player_name]
                
                #Broadcast player left
                await broadcast_to_game_async(game, "player_left_lobby", {
                    "player_name": player_name
                })
                
                #Broadcast updated game state
                game_state = game.get_game_state()
                await broadcast_to_game_async(game, "game_state", game_state)
    except Exception as e:
        print(f"Error in WebSocket connection: {e}")
        import traceback
        traceback.print_exc()
        if player_name and player_name in active_connections:
            del active_connections[player_name]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAOnline Game Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--password", type=str, default=None, help="Game password (optional)")
    parser.add_argument("--turn-timeout", type=int, default=20, help="Turn timeout in seconds (default: 20)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    #Create default game with configuration
    game_id = game_manager.create_game(password=args.password, turn_timeout=args.turn_timeout)
    print(f"Game server starting on {args.host}:{args.port}")
    print(f"Game ID: {game_id}")
    if args.password:
        print(f"Password: {args.password}")
    print(f"Turn timeout: {args.turn_timeout} seconds")
    
    import uvicorn
    import asyncio
    uvicorn.run(app, host=args.host, port=args.port)

