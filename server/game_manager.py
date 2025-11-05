import uuid
import sys
import os
from typing import Dict, Optional

#Add project root to path for imports
if __name__ == "__main__" or not __package__:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.game_instance import GameInstance

class GameManager:
    """
    Manages multiple game instances. For now, manages a single game per server.
    In future versions, can manage multiple concurrent games.
    """
    
    def __init__(self):
        self.games: Dict[str, GameInstance] = {}
        self.default_game: Optional[GameInstance] = None
    
    def create_game(self, password: Optional[str] = None, turn_timeout: int = 20) -> str:
        """
        Create a new game instance. Returns the game_id.
        For now, we only support one game per server.
        """
        #Generate unique game ID
        game_id = str(uuid.uuid4())
        
        #Create game instance
        game = GameInstance(game_id, password, turn_timeout)
        game.initialize_deck()
        
        #Store game
        self.games[game_id] = game
        self.default_game = game
        
        return game_id
    
    def get_game(self, game_id: Optional[str] = None) -> Optional[GameInstance]:
        """
        Get a game instance by ID. If game_id is None, returns the default game.
        """
        if game_id is None:
            return self.default_game
        
        return self.games.get(game_id)
    
    def get_or_create_default_game(self) -> GameInstance:
        """
        Get the default game, creating it if it doesn't exist.
        """
        if self.default_game is None:
            self.create_game()
        
        return self.default_game

