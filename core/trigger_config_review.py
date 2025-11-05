"""
Trigger Configuration Review and Limitations

This document outlines how to properly configure triggers and the limitations
that should be enforced to ensure rule correctness and game integrity.
"""

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

# Valid card values in a standard deck
VALID_CARD_VALUES = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

# Valid suits in a standard deck
VALID_SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']

# Face cards (could be useful for pattern triggers)
FACE_CARDS = ['J', 'Q', 'K']

# Number cards (not face cards, not ace)
NUMBER_CARDS = ['2', '3', '4', '5', '6', '7', '8', '9', '10']

# ============================================================================
# TRIGGER CONFIGURATION PATTERNS
# ============================================================================

class TriggerConfigError(Exception):
    """Exception raised for invalid trigger configuration"""
    pass

def validate_card_value(value: str) -> bool:
    """
    Validate that a card value is valid
    
    Args:
        value: Card value to validate
        
    Returns:
        True if valid, raises TriggerConfigError if invalid
    """
    if value not in VALID_CARD_VALUES:
        raise TriggerConfigError(
            f"Invalid card value: '{value}'. Must be one of {VALID_CARD_VALUES}"
        )
    return True

def validate_suit(suit: str) -> bool:
    """
    Validate that a suit is valid
    
    Args:
        suit: Suit to validate
        
    Returns:
        True if valid, raises TriggerConfigError if invalid
    """
    if suit not in VALID_SUITS:
        raise TriggerConfigError(
            f"Invalid suit: '{suit}'. Must be one of {VALID_SUITS}"
        )
    return True

def validate_sequence_count(count: int, min_count: int = 2, max_count: int = 52) -> bool:
    """
    Validate sequence count for sequence triggers
    
    Args:
        count: The sequence count to validate
        min_count: Minimum allowed count (default 2, since 1 is just a regular card)
        max_count: Maximum allowed count (default 52, full deck)
        
    Returns:
        True if valid, raises TriggerConfigError if invalid
    """
    if not isinstance(count, int):
        raise TriggerConfigError(f"Sequence count must be an integer, got {type(count)}")
    
    if count < min_count:
        raise TriggerConfigError(
            f"Sequence count must be at least {min_count} (got {count}). "
            "Use a regular CardValueTrigger for single cards."
        )
    
    if count > max_count:
        raise TriggerConfigError(
            f"Sequence count cannot exceed {max_count} (got {count})"
        )
    
    return True

# ============================================================================
# ENHANCED TRIGGER CLASSES WITH VALIDATION
# ============================================================================

from typing import List, Optional, Dict, Any, Set
from abc import ABC, abstractmethod

class Trigger(ABC):
    """Base class for rule triggers with validation"""
    
    def __init__(self):
        self._validate()
    
    @abstractmethod
    def _validate(self):
        """Validate trigger configuration"""
        pass
    
    @abstractmethod
    def matches(self, card, game_state: Dict[str, Any]) -> bool:
        """Check if trigger matches"""
        pass
    
    @abstractmethod
    def get_config_summary(self) -> str:
        """Get a human-readable summary of trigger configuration"""
        pass

# ============================================================================
# CONFIGURATION EXAMPLES AND LIMITATIONS
# ============================================================================

class SingleCardTriggerConfig:
    """
    Configuration options for SingleCardTrigger
    
    PATTERNS:
    1. Specific card: value='8', suit='Spades'
       → Only triggers on 8 of Spades
    
    2. Any card of value: value='8', suit=None
       → Triggers on any 8 (any suit)
       → NOTE: This is better done with CardValueTrigger
    
    3. Any card of suit: value=None, suit='Hearts'
       → Triggers on any Heart
       → NOTE: This is better done with CardSuitTrigger
    
    4. Wildcard: value=None, suit=None
       → Triggers on ANY card
       → USE WITH CAUTION: May cause infinite loops or unwanted behavior
    
    LIMITATIONS:
    - At least one of value or suit must be specified (None, None is discouraged)
    - Value must be in VALID_CARD_VALUES
    - Suit must be in VALID_SUITS
    """
    
    @staticmethod
    def create(value: Optional[str] = None, suit: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a validated SingleCardTrigger configuration
        
        Example:
            # Specific card
            config = SingleCardTriggerConfig.create(value='8', suit='Spades')
            
            # Any 8 (recommend CardValueTrigger instead)
            config = SingleCardTriggerConfig.create(value='8', suit=None)
        """
        if value is None and suit is None:
            raise TriggerConfigError(
                "Cannot create trigger with both value and suit as None. "
                "This would match every card. Use a more specific trigger."
            )
        
        if value is not None:
            validate_card_value(value)
        
        if suit is not None:
            validate_suit(suit)
        
        return {'value': value, 'suit': suit}

class CardValueTriggerConfig:
    """
    Configuration options for CardValueTrigger
    
    PATTERNS:
    1. Single value: value='8'
       → Triggers on any 8 of any suit
    
    2. Multiple values: NOT SUPPORTED natively (use multiple rules)
       → To trigger on multiple values, create separate rules
       → Or use PatternTrigger for groups (e.g., all face cards)
    
    LIMITATIONS:
    - Value must be exactly one string from VALID_CARD_VALUES
    - Cannot match multiple values in one trigger (create multiple rules)
    - Most common pattern for MAO rules
    """
    
    @staticmethod
    def create(value: str) -> Dict[str, Any]:
        """
        Create a validated CardValueTrigger configuration
        
        Example:
            config = CardValueTriggerConfig.create(value='A')  # Any Ace
        """
        validate_card_value(value)
        return {'value': value}

class SequenceTriggerConfig:
    """
    Configuration options for SequenceTrigger
    
    PATTERNS:
    1. Two in a row: value='7', count=2
       → Triggers when two 7s are played consecutively
    
    2. Three in a row: value='7', count=3
       → Triggers when three 7s are played consecutively
    
    LIMITATIONS:
    - Count must be >= 2 (use CardValueTrigger for single cards)
    - Count should be <= reasonable limit (e.g., 10) to avoid impossible sequences
    - Value must be valid card value
    - Sequence is based on recent card history in game_state
    - Sequence resets when a different card is played
    
    CONSIDERATIONS:
    - Higher counts (3+) are rare but possible with many decks
    - Game state must maintain 'recent_cards' list for this to work
    - Sequence checking happens in order, most recent first
    """
    
    @staticmethod
    def create(value: str, count: int, max_reasonable: int = 10) -> Dict[str, Any]:
        """
        Create a validated SequenceTrigger configuration
        
        Example:
            config = SequenceTriggerConfig.create(value='7', count=2)  # Two 7s
            config = SequenceTriggerConfig.create(value='8', count=3)  # Three 8s
        """
        validate_card_value(value)
        validate_sequence_count(count, min_count=2, max_count=max_reasonable)
        return {'value': value, 'count': count}

class PatternTriggerConfig:
    """
    Configuration options for PatternTrigger (for future implementation)
    
    PATTERNS:
    1. Face cards: pattern='face_cards'
       → Triggers on J, Q, K
    
    2. Number cards: pattern='number_cards'
       → Triggers on 2-10
    
    3. Red cards: pattern='red'
       → Triggers on Hearts or Diamonds
    
    4. Black cards: pattern='black'
       → Triggers on Clubs or Spades
    
    LIMITATIONS:
    - Pattern must be a known pattern type
    - Custom patterns require pattern matching logic
    - More complex than simple triggers
    """
    
    VALID_PATTERNS = ['face_cards', 'number_cards', 'red', 'black']
    
    @staticmethod
    def create(pattern: str) -> Dict[str, Any]:
        """
        Create a validated PatternTrigger configuration
        
        Example:
            config = PatternTriggerConfig.create(pattern='face_cards')
        """
        if pattern not in PatternTriggerConfig.VALID_PATTERNS:
            raise TriggerConfigError(
                f"Invalid pattern: '{pattern}'. Must be one of {PatternTriggerConfig.VALID_PATTERNS}"
            )
        return {'pattern': pattern}

# ============================================================================
# CONFIGURATION BEST PRACTICES
# ============================================================================

class TriggerConfigurationGuide:
    """
    Guide for configuring triggers with proper limitations
    """
    
    @staticmethod
    def get_recommended_limits() -> Dict[str, Any]:
        """
        Get recommended limits for trigger configurations
        """
        return {
            'sequence_count': {
                'min': 2,
                'max': 10,  # Reasonable maximum for most games
                'recommended_max': 4  # Most common in practice
            },
            'wildcard_usage': {
                'warning': 'Triggers matching all cards should be rare',
                'use_case': 'Only for special house rules'
            },
            'multiple_rules_per_card': {
                'allowed': True,
                'warning': 'Order matters - rules checked sequentially',
                'recommendation': 'Keep rule count per card reasonable (< 5)'
            }
        }
    
    @staticmethod
    def validate_trigger_config(trigger_type: str, config: Dict[str, Any]) -> bool:
        """
        Validate a trigger configuration based on type
        
        Example:
            config = {'value': '8', 'suit': None}
            TriggerConfigurationGuide.validate_trigger_config('card_value', config)
        """
        if trigger_type == 'single_card':
            return SingleCardTriggerConfig.create(**config) is not None
        elif trigger_type == 'card_value':
            return CardValueTriggerConfig.create(**config) is not None
        elif trigger_type == 'sequence':
            return SequenceTriggerConfig.create(**config) is not None
        elif trigger_type == 'pattern':
            return PatternTriggerConfig.create(**config) is not None
        else:
            raise TriggerConfigError(f"Unknown trigger type: {trigger_type}")
    
    @staticmethod
    def get_config_examples() -> Dict[str, List[Dict[str, Any]]]:
        """
        Get example configurations for each trigger type
        """
        return {
            'common_mao_rules': [
                {
                    'type': 'card_value',
                    'config': CardValueTriggerConfig.create(value='8'),
                    'description': 'Any 8 skips next player'
                },
                {
                    'type': 'card_value',
                    'config': CardValueTriggerConfig.create(value='A'),
                    'description': 'Any Ace reverses order'
                },
                {
                    'type': 'card_value',
                    'config': CardValueTriggerConfig.create(value='7'),
                    'description': 'Any 7 requires typing phrase'
                },
                {
                    'type': 'single_card',
                    'config': SingleCardTriggerConfig.create(value='K', suit='Hearts'),
                    'description': 'King of Hearts special rule'
                }
            ],
            'sequence_rules': [
                {
                    'type': 'sequence',
                    'config': SequenceTriggerConfig.create(value='7', count=2),
                    'description': 'Two 7s in a row triggers special effect'
                },
                {
                    'type': 'sequence',
                    'config': SequenceTriggerConfig.create(value='8', count=3),
                    'description': 'Three 8s in a row triggers special effect'
                }
            ],
            'avoid_these': [
                {
                    'type': 'single_card',
                    'config': {'value': None, 'suit': None},
                    'description': 'Wildcard matching all cards - too broad',
                    'reason': 'Will trigger on every card, likely unintended'
                },
                {
                    'type': 'sequence',
                    'config': {'value': '7', 'count': 1},
                    'description': 'Sequence of 1',
                    'reason': 'Should use CardValueTrigger instead'
                },
                {
                    'type': 'sequence',
                    'config': {'value': '7', 'count': 52},
                    'description': 'Sequence of 52',
                    'reason': 'Impossible to achieve, unreachable rule'
                }
            ]
        }

# ============================================================================
# CONFIGURATION VALIDATION CHECKLIST
# ============================================================================

def validate_trigger_configuration_checklist(trigger_type: str, config: Dict[str, Any]) -> List[str]:
    """
    Run a checklist of validations for trigger configuration
    
    Returns:
        List of warnings/errors (empty list if all pass)
    """
    issues = []
    
    # Check 1: Trigger type is valid
    valid_types = ['single_card', 'card_value', 'card_suit', 'sequence', 'pattern']
    if trigger_type not in valid_types:
        issues.append(f"Invalid trigger type: {trigger_type}")
        return issues
    
    # Check 2: Required fields present
    if trigger_type == 'single_card':
        if 'value' not in config and 'suit' not in config:
            issues.append("SingleCardTrigger requires at least value or suit")
        if config.get('value') is None and config.get('suit') is None:
            issues.append("WARNING: Both value and suit are None - will match ALL cards")
    elif trigger_type == 'card_value':
        if 'value' not in config:
            issues.append("CardValueTrigger requires 'value' field")
    elif trigger_type == 'sequence':
        if 'value' not in config:
            issues.append("SequenceTrigger requires 'value' field")
        if 'count' not in config:
            issues.append("SequenceTrigger requires 'count' field")
        elif config.get('count', 0) < 2:
            issues.append("SequenceTrigger count must be >= 2")
        elif config.get('count', 0) > 10:
            issues.append(f"WARNING: SequenceTrigger count is {config['count']}, very unlikely to occur")
    
    # Check 3: Value validation
    if 'value' in config and config['value'] is not None:
        try:
            validate_card_value(config['value'])
        except TriggerConfigError as e:
            issues.append(str(e))
    
    # Check 4: Suit validation
    if 'suit' in config and config['suit'] is not None:
        try:
            validate_suit(config['suit'])
        except TriggerConfigError as e:
            issues.append(str(e))
    
    # Check 5: Sequence count validation
    if trigger_type == 'sequence' and 'count' in config:
        try:
            validate_sequence_count(config['count'])
        except TriggerConfigError as e:
            issues.append(str(e))
    
    return issues

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("=== Trigger Configuration Review ===\n")
    
    # Example 1: Valid configuration
    print("Example 1: Valid Card Value Trigger")
    try:
        config = CardValueTriggerConfig.create(value='8')
        print(f"  ✓ Valid config: {config}")
    except TriggerConfigError as e:
        print(f"  ✗ Error: {e}")
    
    # Example 2: Invalid configuration
    print("\nExample 2: Invalid Card Value")
    try:
        config = CardValueTriggerConfig.create(value='15')
        print(f"  ✓ Valid config: {config}")
    except TriggerConfigError as e:
        print(f"  ✗ Error: {e}")
    
    # Example 3: Valid sequence
    print("\nExample 3: Valid Sequence Trigger")
    try:
        config = SequenceTriggerConfig.create(value='7', count=3)
        print(f"  ✓ Valid config: {config}")
    except TriggerConfigError as e:
        print(f"  ✗ Error: {e}")
    
    # Example 4: Invalid sequence (count = 1)
    print("\nExample 4: Invalid Sequence (count < 2)")
    try:
        config = SequenceTriggerConfig.create(value='7', count=1)
        print(f"  ✓ Valid config: {config}")
    except TriggerConfigError as e:
        print(f"  ✗ Error: {e}")
    
    # Example 5: Validation checklist
    print("\nExample 5: Validation Checklist")
    issues = validate_trigger_configuration_checklist('card_value', {'value': '8'})
    if not issues:
        print("  ✓ No issues found")
    else:
        for issue in issues:
            print(f"  ⚠ {issue}")
    
    # Example 6: Get recommended limits
    print("\nExample 6: Recommended Limits")
    limits = TriggerConfigurationGuide.get_recommended_limits()
    for key, value in limits.items():
        print(f"  {key}: {value}")
    
    # Example 7: Configuration examples
    print("\nExample 7: Common MAO Rule Configurations")
    examples = TriggerConfigurationGuide.get_config_examples()
    for category, configs in examples.items():
        print(f"\n  {category}:")
        for cfg in configs[:3]:  # Show first 3
            print(f"    - {cfg.get('description', 'N/A')}")
            if 'reason' in cfg:
                print(f"      Reason to avoid: {cfg['reason']}")


