"""
Modular Rule Book Design for MAO

Core Concept:
- Rules consist of a TRIGGER (what card/sequence activates it) and an ACTION/EFFECT (what happens)
- This separation allows for flexible rule composition and easy extension

TRIGGER Types:
1. Single Card Trigger: Specific value and/or suit
2. Sequence Trigger: Multiple cards in sequence (e.g., three 7s in a row)
3. Pattern Trigger: Card matching a pattern (e.g., any face card)
4. Conditional Trigger: Depends on game state (e.g., when hand size is 0)

ACTION/EFFECT Types:
1. Skip Action: Skip next player(s)
2. Reverse Action: Reverse turn order
3. Draw Action: Force player(s) to draw cards
4. Typing Action: Require phrase input with time limit
5. Custom Action: Game-specific behavior
6. Compound Action: Multiple effects in sequence

Design Benefits:
- Rules can be added/removed dynamically
- Actions can be reused with different triggers
- Easy to serialize rules for network play
- Supports rule variations and house rules
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# ============================================================================
# TRIGGER SYSTEM
# ============================================================================

class TriggerType(Enum):
    """Types of triggers that can activate rules"""
    SINGLE_CARD = "single_card"        # Specific card (value and/or suit)
    CARD_VALUE = "card_value"          # Any card with this value (e.g., all 7s)
    CARD_SUIT = "card_suit"            # Any card with this suit
    SUIT_PATTERN = "suit_pattern"      # Multiple suits (e.g., all red cards)
    SEQUENCE = "sequence"               # Multiple cards in sequence (up to 3)
    PATTERN = "pattern"                 # Pattern matching (e.g., face cards)
    CONDITIONAL = "conditional"        # Based on game state

class Trigger(ABC):
    """Base class for rule triggers with validation support"""
    
    @abstractmethod
    def _validate(self):
        """Validate trigger configuration. Called during initialization."""
        pass
    
    @abstractmethod
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        """
        Check if this trigger matches the given card and game state
        
        Args:
            card: The card to check
            game_state: Current game state (top card, players, etc.)
        
        Returns:
            True if trigger matches, False otherwise
        """
        pass
    
    def get_config_summary(self) -> str:
        """
        Get a human-readable summary of trigger configuration
        
        Returns:
            String describing the trigger configuration
        """
        return f"{self.__class__.__name__}"
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize trigger to dictionary for storage/network"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trigger':
        """Deserialize trigger from dictionary"""
        pass

class SingleCardTrigger(Trigger):
    """
    Trigger for a specific card (value AND/OR suit)
    
    CONFIGURATION:
        - value: Card value (None = any value)
        - suit: Card suit (None = any suit)
    
    LIMITATIONS:
        - At least one of value or suit MUST be specified (both None is invalid)
        - Value must be in valid card values list
        - Suit must be in valid suits list
        - Use CardValueTrigger for value-only matches (more explicit)
        - Use CardSuitTrigger for suit-only matches (when implemented)
    """
    
    # Valid values for validation
    VALID_VALUES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    VALID_SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    
    def __init__(self, value: Optional[str] = None, suit: Optional[str] = None):
        self.value = value  # None means any value
        self.suit = suit    # None means any suit
        self._validate()
    
    def _validate(self):
        """Validate trigger configuration"""
        # At least one must be specified
        if self.value is None and self.suit is None:
            raise ValueError(
                "SingleCardTrigger: At least one of 'value' or 'suit' must be specified. "
                "Both None would match every card, which is likely unintended. "
                "Use CardValueTrigger for value-only matches."
            )
        
        # Validate value if provided
        if self.value is not None and self.value not in self.VALID_VALUES:
            raise ValueError(
                f"SingleCardTrigger: Invalid value '{self.value}'. "
                f"Must be one of {self.VALID_VALUES}"
            )
        
        # Validate suit if provided
        if self.suit is not None and self.suit not in self.VALID_SUITS:
            raise ValueError(
                f"SingleCardTrigger: Invalid suit '{self.suit}'. "
                f"Must be one of {self.VALID_SUITS}"
            )
    
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        value_match = self.value is None or card.value == self.value
        suit_match = self.suit is None or card.suit == self.suit
        return value_match and suit_match
    
    def get_config_summary(self) -> str:
        parts = []
        if self.value:
            parts.append(f"value={self.value}")
        if self.suit:
            parts.append(f"suit={self.suit}")
        return f"SingleCardTrigger({', '.join(parts)})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': TriggerType.SINGLE_CARD.value,
            'value': self.value,
            'suit': self.suit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SingleCardTrigger':
        return cls(value=data.get('value'), suit=data.get('suit'))

class CardValueTrigger(Trigger):
    """
    Trigger for any card with a specific value (any suit)
    
    CONFIGURATION:
        - value: Card value (required, must be valid)
    
    LIMITATIONS:
        - Value must be exactly one valid card value
        - Cannot match multiple values (create multiple rules instead)
        - Most common trigger type for MAO rules
    """
    
    VALID_VALUES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, value: str):
        self.value = value
        self._validate()
    
    def _validate(self):
        """Validate trigger configuration"""
        if self.value not in self.VALID_VALUES:
            raise ValueError(
                f"CardValueTrigger: Invalid value '{self.value}'. "
                f"Must be one of {self.VALID_VALUES}"
            )
    
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        return card.value == self.value
    
    def get_config_summary(self) -> str:
        return f"CardValueTrigger(value={self.value})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': TriggerType.CARD_VALUE.value,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CardValueTrigger':
        return cls(value=data['value'])

class CardSuitTrigger(Trigger):
    """
    Trigger for any card with a specific suit (any value)
    
    CONFIGURATION:
        - suit: Card suit (required, must be valid)
    
    LIMITATIONS:
        - Suit must be exactly one valid suit
        - Cannot match multiple suits (use SuitPatternTrigger instead)
    
    EXAMPLES:
        - CardSuitTrigger(suit='Hearts')  # Any Heart
        - CardSuitTrigger(suit='Spades')  # Any Spade
    """
    
    VALID_SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    
    def __init__(self, suit: str):
        self.suit = suit
        self._validate()
    
    def _validate(self):
        """Validate trigger configuration"""
        if self.suit not in self.VALID_SUITS:
            raise ValueError(
                f"CardSuitTrigger: Invalid suit '{self.suit}'. "
                f"Must be one of {self.VALID_SUITS}"
            )
    
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        return card.suit == self.suit
    
    def get_config_summary(self) -> str:
        return f"CardSuitTrigger(suit={self.suit})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': TriggerType.CARD_SUIT.value,
            'suit': self.suit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CardSuitTrigger':
        return cls(suit=data['suit'])

class SuitPatternTrigger(Trigger):
    """
    Trigger for cards matching a suit pattern (e.g., all red cards, all black cards)
    
    CONFIGURATION:
        - pattern: Pattern type ('red', 'black', or list of specific suits)
    
    LIMITATIONS:
        - Pattern must be 'red', 'black', or a list of valid suits
        - 'red' means Hearts or Diamonds
        - 'black' means Clubs or Spades
        - Custom list must contain valid suits
    
    EXAMPLES:
        - SuitPatternTrigger(pattern='red')  # Hearts or Diamonds
        - SuitPatternTrigger(pattern='black')  # Clubs or Spades
        - SuitPatternTrigger(pattern=['Hearts', 'Spades'])  # Custom combination
    """
    
    VALID_SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    RED_SUITS = ['Hearts', 'Diamonds']
    BLACK_SUITS = ['Clubs', 'Spades']
    VALID_PATTERNS = ['red', 'black']
    
    def __init__(self, pattern: Union[str, List[str]]):
        """
        Create a suit pattern trigger
        
        Args:
            pattern: Either 'red', 'black', a single suit name, or a list of suit names
        """
        self.pattern = pattern
        self._validate()
        self._resolve_pattern()
    
    def _resolve_pattern(self):
        """Resolve pattern string to list of suits"""
        if self.pattern == 'red':
            self.suits = self.RED_SUITS
        elif self.pattern == 'black':
            self.suits = self.BLACK_SUITS
        elif isinstance(self.pattern, list):
            self.suits = self.pattern
        else:
            self.suits = [self.pattern]  # Single suit as string
    
    def _validate(self):
        """Validate trigger configuration"""
        if self.pattern == 'red' or self.pattern == 'black':
            return  # Built-in patterns are valid
        
        if isinstance(self.pattern, list):
            if not self.pattern:
                raise ValueError(
                    "SuitPatternTrigger: Pattern list cannot be empty"
                )
            for suit in self.pattern:
                if suit not in self.VALID_SUITS:
                    raise ValueError(
                        f"SuitPatternTrigger: Invalid suit '{suit}' in pattern. "
                        f"Must be one of {self.VALID_SUITS}"
                    )
        elif self.pattern not in self.VALID_SUITS:
            raise ValueError(
                f"SuitPatternTrigger: Invalid pattern '{self.pattern}'. "
                f"Must be 'red', 'black', a valid suit, or a list of valid suits"
            )
    
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        return card.suit in self.suits
    
    def get_config_summary(self) -> str:
        if isinstance(self.pattern, list):
            suits_str = ', '.join(self.pattern)
            return f"SuitPatternTrigger(suits=[{suits_str}])"
        return f"SuitPatternTrigger(pattern={self.pattern})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': TriggerType.SUIT_PATTERN.value,
            'pattern': self.pattern
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuitPatternTrigger':
        return cls(pattern=data['pattern'])

class SequenceTrigger(Trigger):
    """
    Trigger for a sequence of cards (e.g., two or three 7s in a row)
    
    CONFIGURATION:
        - value: Card value to look for in sequence
        - count: Number of consecutive cards needed (must be 2 or 3)
    
    LIMITATIONS:
        - Count must be >= 2 and <= 3 (use CardValueTrigger for single cards)
        - Maximum sequence length is 3 cards
        - Value must be valid card value
        - Requires game_state['recent_cards'] list to track history
        - Sequence resets when a different card value is played
    
    EXAMPLES:
        - SequenceTrigger(value='7', count=2)  # Two 7s in a row
        - SequenceTrigger(value='8', count=3)  # Three 8s in a row
    """
    
    VALID_VALUES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    MIN_COUNT = 2
    MAX_COUNT = 3  # Maximum sequence length allowed
    RECOMMENDED_MAX = 3
    
    def __init__(self, value: str, count: int):
        """
        Create a sequence trigger
        
        Args:
            value: Card value to look for (e.g., '7')
            count: Number of consecutive cards needed (2 or 3)
        """
        self.value = value  # The card value to look for
        self.count = count  # How many in a row needed
        self._validate()
    
    def _validate(self):
        """Validate trigger configuration"""
        # Validate value
        if self.value not in self.VALID_VALUES:
            raise ValueError(
                f"SequenceTrigger: Invalid value '{self.value}'. "
                f"Must be one of {self.VALID_VALUES}"
            )
        
        # Validate count
        if not isinstance(self.count, int):
            raise ValueError(
                f"SequenceTrigger: Count must be an integer, got {type(self.count)}"
            )
        
        if self.count < self.MIN_COUNT:
            raise ValueError(
                f"SequenceTrigger: Count must be at least {self.MIN_COUNT} "
                f"(got {self.count}). Use CardValueTrigger for single cards."
            )
        
        if self.count > self.MAX_COUNT:
            raise ValueError(
                f"SequenceTrigger: Count {self.count} exceeds maximum allowed sequence length {self.MAX_COUNT}. "
                f"Sequences are limited to 3 cards maximum."
            )
    
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        if card.value != self.value:
            return False
        
        # Check recent card history
        recent_cards = game_state.get('recent_cards', [])
        
        # Count how many consecutive cards match
        consecutive = 1  # Current card counts as 1
        for prev_card in recent_cards:
            if prev_card.value == self.value:
                consecutive += 1
            else:
                break  # Sequence broken
        
        return consecutive >= self.count
    
    def get_config_summary(self) -> str:
        return f"SequenceTrigger(value={self.value}, count={self.count})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': TriggerType.SEQUENCE.value,
            'value': self.value,
            'count': self.count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SequenceTrigger':
        return cls(
            value=data['value'],
            count=data['count']
        )

# ============================================================================
# ACTION SYSTEM
# ============================================================================

class ActionType(Enum):
    """Types of actions that can be executed"""
    SKIP = "skip"
    REVERSE = "reverse"
    DRAW = "draw"
    TYPING = "typing"
    CUSTOM = "custom"
    COMPOUND = "compound"

class Action(ABC):
    """Base class for rule actions/effects"""
    
    @abstractmethod
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        """
        Execute the action and return updated game state
        
        Args:
            game_state: Current game state
            player: The player who triggered this
            card: The card that triggered this
        
        Returns:
            Updated game state dictionary
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize action to dictionary"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Deserialize action from dictionary"""
        pass

class SkipAction(Action):
    """Action that skips the next player(s)"""
    
    def __init__(self, skip_count: int = 1):
        self.skip_count = skip_count
    
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        game_state['skip_next'] = self.skip_count
        return game_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': ActionType.SKIP.value,
            'skip_count': self.skip_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkipAction':
        return cls(skip_count=data.get('skip_count', 1))

class ReverseAction(Action):
    """Action that reverses turn order"""
    
    def __init__(self, also_skip: bool = False):
        self.also_skip = also_skip
    
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        # Toggle reverse direction
        game_state['reverse'] = not game_state.get('reverse', False)
        if self.also_skip:
            game_state['skip_next'] = 1
        return game_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': ActionType.REVERSE.value,
            'also_skip': self.also_skip
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReverseAction':
        return cls(also_skip=data.get('also_skip', False))

class DrawAction(Action):
    """Action that forces player(s) to draw cards"""
    
    def __init__(self, card_count: int = 1, target: str = "next"):
        """
        Args:
            card_count: Number of cards to draw
            target: "next" (next player), "current" (triggering player), "all" (all players)
        """
        self.card_count = card_count
        self.target = target
    
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        game_state['draw_cards'] = {
            'count': self.card_count,
            'target': self.target
        }
        return game_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': ActionType.DRAW.value,
            'card_count': self.card_count,
            'target': self.target
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawAction':
        return cls(
            card_count=data.get('card_count', 1),
            target=data.get('target', 'next')
        )

class TypingAction(Action):
    """Action that requires typing a phrase within time limit"""
    
    def __init__(self, phrase: str, time_limit: float, penalty_cards: int = 1):
        """
        Args:
            phrase: The phrase that must be typed
            time_limit: Time limit in seconds
            penalty_cards: Cards to draw if failed
        """
        self.phrase = phrase
        self.time_limit = time_limit
        self.penalty_cards = penalty_cards
    
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        import time
        
        print(f"You have {self.time_limit} seconds to type: '{self.phrase}'")
        start_time = time.time()
        response = input("Type now: ")
        elapsed = time.time() - start_time
        
        if elapsed > self.time_limit or response.lower().strip() != self.phrase.lower():
            print(f"Failed! You took {elapsed:.2f} seconds. Drawing {self.penalty_cards} card(s).")
            game_state['draw_cards'] = {
                'count': self.penalty_cards,
                'target': 'current'
            }
        else:
            print(f"Success! You typed it in {elapsed:.2f} seconds.")
        
        return game_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': ActionType.TYPING.value,
            'phrase': self.phrase,
            'time_limit': self.time_limit,
            'penalty_cards': self.penalty_cards
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypingAction':
        return cls(
            phrase=data['phrase'],
            time_limit=data['time_limit'],
            penalty_cards=data.get('penalty_cards', 1)
        )

class CompoundAction(Action):
    """Action that executes multiple actions in sequence"""
    
    def __init__(self, actions: List[Action]):
        self.actions = actions
    
    def execute(self, game_state: Dict[str, Any], player, card) -> Dict[str, Any]:
        for action in self.actions:
            game_state = action.execute(game_state, player, card)
        return game_state
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': ActionType.COMPOUND.value,
            'actions': [action.to_dict() for action in self.actions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompoundAction':
        # This would need a registry to deserialize sub-actions
        # For now, simplified
        return cls(actions=[])  # TODO: Implement proper deserialization

# ============================================================================
# RULE SYSTEM
# ============================================================================

class Rule:
    """
    A complete rule that combines a trigger with an action
    
    Example:
        rule = Rule(
            trigger=CardValueTrigger('8'),
            action=SkipAction(skip_count=1),
            name="Skip on Eight"
        )
    """
    
    def __init__(self, trigger: Trigger, action: Action, name: str = ""):
        self.trigger = trigger
        self.action = action
        self.name = name or f"{trigger.__class__.__name__} -> {action.__class__.__name__}"
        self.enabled = True
    
    def check_and_execute(self, card, game_state: Dict[str, Any], player) -> Optional[Dict[str, Any]]:
        """
        Check if trigger matches, and if so, execute action
        
        Returns:
            Updated game_state if rule was triggered, None otherwise
        """
        if not self.enabled:
            return None
        
        if self.trigger.matches(card, game_state):
            print(f"Rule triggered: {self.name}")
            return self.action.execute(game_state.copy(), player, card)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'enabled': self.enabled,
            'trigger': self.trigger.to_dict(),
            'action': self.action.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        # This would need a trigger/action registry for full deserialization
        # Simplified for now
        trigger = SingleCardTrigger.from_dict(data['trigger'])
        action = SkipAction.from_dict(data['action'])  # TODO: Proper deserialization
        rule = cls(trigger=trigger, action=action, name=data.get('name', ''))
        rule.enabled = data.get('enabled', True)
        return rule

# ============================================================================
# RULEBOOK SYSTEM
# ============================================================================

class RuleBook:
    """
    Modular rule book that manages a collection of rules
    
    Rules are checked in order, and multiple rules can trigger on the same card.
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self.enabled = True
    
    def add_rule(self, rule: Rule):
        """Add a rule to the rulebook"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a rule by name"""
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def get_rules_by_name(self, name: str) -> List[Rule]:
        """Get all rules matching a name"""
        return [r for r in self.rules if name in r.name]
    
    def check_card(self, card, game_state: Dict[str, Any], player) -> Dict[str, Any]:
        """
        Check all rules against a card and execute any that match
        
        Returns:
            Updated game state with all rule effects applied
        """
        if not self.enabled:
            return game_state
        
        result_state = game_state.copy()
        
        for rule in self.rules:
            rule_result = rule.check_and_execute(card, result_state, player)
            if rule_result:
                # Merge rule results into game state
                # Later rules can override earlier ones
                result_state.update(rule_result)
        
        return result_state
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire rulebook"""
        return {
            'enabled': self.enabled,
            'rules': [rule.to_dict() for rule in self.rules]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleBook':
        """Deserialize rulebook"""
        rulebook = cls()
        rulebook.enabled = data.get('enabled', True)
        # TODO: Proper deserialization with registry
        return rulebook

# ============================================================================
# PRESET RULES FOR MAO
# ============================================================================

def create_base_mao_rules() -> RuleBook:
    """Create a rulebook with standard MAO rules"""
    rulebook = RuleBook()
    
    # Ace: Reverse and skip
    rulebook.add_rule(Rule(
        trigger=CardValueTrigger('A'),
        action=CompoundAction([
            ReverseAction(also_skip=True),
            SkipAction(skip_count=1)
        ]),
        name="Ace: Reverse and Skip"
    ))
    
    # Eight: Skip next player
    rulebook.add_rule(Rule(
        trigger=CardValueTrigger('8'),
        action=SkipAction(skip_count=1),
        name="Eight: Skip Next Player"
    ))
    
    # Seven: Type phrase "have a nice day"
    rulebook.add_rule(Rule(
        trigger=CardValueTrigger('7'),
        action=TypingAction(
            phrase="have a nice day",
            time_limit=7.0,
            penalty_cards=1
        ),
        name="Seven: Type 'have a nice day'"
    ))
    
    return rulebook

