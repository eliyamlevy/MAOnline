# Trigger Configuration Examples

This document provides practical examples of the three main trigger patterns you mentioned.

## 1. All Red Cards

**Trigger:** Matches any red card (Hearts or Diamonds)

```python
from core.rulebook_design import SuitPatternTrigger, Rule, SkipAction

# Create trigger for all red cards
trigger = SuitPatternTrigger(pattern='red')

# Example: Skip next player when any red card is played
rule = Rule(
    trigger=trigger,
    action=SkipAction(skip_count=1),
    name="Red Card Skip"
)
```

**Alternative: Custom suit combination**
```python
# Match Hearts or Diamonds (same as 'red')
trigger = SuitPatternTrigger(pattern=['Hearts', 'Diamonds'])

# Match only Hearts and Spades
trigger = SuitPatternTrigger(pattern=['Hearts', 'Spades'])
```

## 2. All Sevens

**Trigger:** Matches any card with value 7 (any suit)

```python
from core.rulebook_design import CardValueTrigger, Rule, TypingAction

# Create trigger for all 7s
trigger = CardValueTrigger(value='7')

# Example: Typing challenge on any 7
rule = Rule(
    trigger=trigger,
    action=TypingAction(
        phrase="have a nice day",
        time_limit=7.0,
        penalty_cards=1
    ),
    name="Seven Typing Rule"
)
```

## 3. Sequence of Cards (Up to 3)

**Trigger:** Matches when 2 or 3 consecutive cards of the same value are played

```python
from core.rulebook_design import SequenceTrigger, Rule, DrawAction

# Two 8s in a row
trigger = SequenceTrigger(value='8', count=2)

rule = Rule(
    trigger=trigger,
    action=DrawAction(card_count=2, target='next'),
    name="Two 8s: Next Player Draws 2"
)

# Three 7s in a row
trigger = SequenceTrigger(value='7', count=3)

rule = Rule(
    trigger=trigger,
    action=DrawAction(card_count=5, target='current'),
    name="Three 7s: Current Player Draws 5"
)
```

## Complete Example: Multiple Rules

```python
from core.rulebook_design import (
    CardValueTrigger, SuitPatternTrigger, SequenceTrigger,
    Rule, SkipAction, ReverseAction, TypingAction, RuleBook
)

# Create rulebook
rulebook = RuleBook()

# Rule 1: All red cards skip next player
rulebook.add_rule(Rule(
    trigger=SuitPatternTrigger(pattern='red'),
    action=SkipAction(skip_count=1),
    name="Red Card Skip"
))

# Rule 2: All 8s skip next player
rulebook.add_rule(Rule(
    trigger=CardValueTrigger(value='8'),
    action=SkipAction(skip_count=1),
    name="Eight Skip"
))

# Rule 3: All Aces reverse order
rulebook.add_rule(Rule(
    trigger=CardValueTrigger(value='A'),
    action=ReverseAction(also_skip=True),
    name="Ace Reverse"
))

# Rule 4: All 7s require typing
rulebook.add_rule(Rule(
    trigger=CardValueTrigger(value='7'),
    action=TypingAction(
        phrase="have a nice day",
        time_limit=7.0,
        penalty_cards=1
    ),
    name="Seven Typing"
))

# Rule 5: Two 7s in a row - special effect
rulebook.add_rule(Rule(
    trigger=SequenceTrigger(value='7', count=2),
    action=SkipAction(skip_count=2),  # Skip 2 players
    name="Two 7s Sequence"
))

# Rule 6: Three 8s in a row - major effect
rulebook.add_rule(Rule(
    trigger=SequenceTrigger(value='8', count=3),
    action=DrawAction(card_count=10, target='current'),
    name="Three 8s: Draw 10 Cards"
))
```

## Trigger Limitations Summary

| Trigger Type | Pattern | Maximum Scope | Example |
|-------------|---------|---------------|---------|
| `CardValueTrigger` | All cards of a value | 4 cards (one per suit) | All 7s |
| `SuitPatternTrigger` | All cards of pattern | 26 cards (red/black) or custom | All red cards |
| `SequenceTrigger` | Consecutive same value | Up to 3 cards in sequence | Two or three 7s |

## Common Patterns in MAO

### Basic Value Triggers (Most Common)
```python
CardValueTrigger(value='8')  # Skip
CardValueTrigger(value='A')  # Reverse
CardValueTrigger(value='7')  # Typing
```

### Color-Based Triggers
```python
SuitPatternTrigger(pattern='red')    # All red cards
SuitPatternTrigger(pattern='black')  # All black cards
```

### Sequence Triggers (Rarer, More Powerful)
```python
SequenceTrigger(value='7', count=2)  # Two 7s
SequenceTrigger(value='8', count=3)  # Three 8s (very rare)
```

## Testing Triggers

```python
from core.cardgamecore import Card

# Test card
red_7 = Card('Hearts', '7')
black_8 = Card('Clubs', '8')

# Test red card trigger
red_trigger = SuitPatternTrigger(pattern='red')
print(red_trigger.matches(red_7, {}))    # True
print(red_trigger.matches(black_8, {}))  # False

# Test value trigger
value_trigger = CardValueTrigger(value='7')
print(value_trigger.matches(red_7, {}))    # True (any 7)
print(value_trigger.matches(black_8, {}))  # False

# Test sequence trigger (requires game state)
from collections import deque
game_state = {
    'recent_cards': deque([Card('Hearts', '7')])
}
seq_trigger = SequenceTrigger(value='7', count=2)
print(seq_trigger.matches(red_7, game_state))  # True (second 7 in sequence)
```


