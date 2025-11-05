# Trigger Configuration Guide

This document explains how to configure triggers and the limitations that apply.

## Overview

Triggers are the "when" part of rules - they determine what card or card sequence activates a rule. Proper configuration ensures rules work correctly and don't cause unintended behavior.

## Valid Card Values and Suits

**Card Values:** `A`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `J`, `Q`, `K`

**Suits:** `Hearts`, `Diamonds`, `Clubs`, `Spades`

## Trigger Types and Configuration

### 1. CardValueTrigger

**Purpose:** Triggers on any card with a specific value (any suit)

**Configuration:**
```python
from core.rulebook_design import CardValueTrigger

# Any 8 of any suit
trigger = CardValueTrigger(value='8')

# Any Ace
trigger = CardValueTrigger(value='A')
```

**Limitations:**
- ✅ Value must be exactly one valid card value
- ✅ Cannot match multiple values in one trigger (create multiple rules instead)
- ✅ Most common trigger type for MAO rules
- ❌ Cannot specify suit (use SingleCardTrigger instead)

**Validation:**
- Value is validated against valid card values list
- Invalid values raise `ValueError` immediately

**Examples:**
```python
# ✓ Valid - common MAO rules
CardValueTrigger(value='8')   # Skip rule
CardValueTrigger(value='A')   # Reverse rule
CardValueTrigger(value='7')   # Typing rule

# ✗ Invalid - will raise ValueError
CardValueTrigger(value='15')  # Not a valid card value
CardValueTrigger(value='')    # Empty value not allowed
```

---

### 2. SingleCardTrigger

**Purpose:** Triggers on a specific card (both value and suit, or just one)

**Configuration:**
```python
from core.rulebook_design import SingleCardTrigger

# Specific card: 8 of Spades only
trigger = SingleCardTrigger(value='8', suit='Spades')

# Any card of a value (but CardValueTrigger is preferred)
trigger = SingleCardTrigger(value='8', suit=None)

# Any card of a suit
trigger = SingleCardTrigger(value=None, suit='Hearts')
```

**Limitations:**
- ✅ At least one of `value` or `suit` MUST be specified
- ✅ Both value and suit are validated if provided
- ⚠️ `(None, None)` is invalid - would match every card
- 💡 Prefer `CardValueTrigger` for value-only matches
- 💡 Prefer `CardSuitTrigger` (when implemented) for suit-only matches

**Validation:**
- Raises `ValueError` if both value and suit are None
- Validates value against valid card values
- Validates suit against valid suits

**Examples:**
```python
# ✓ Valid configurations
SingleCardTrigger(value='8', suit='Spades')     # Specific card
SingleCardTrigger(value='8', suit=None)         # Any 8 (but prefer CardValueTrigger)
SingleCardTrigger(value=None, suit='Hearts')    # Any Heart

# ✗ Invalid - will raise ValueError
SingleCardTrigger(value=None, suit=None)       # Matches everything - too broad
SingleCardTrigger(value='15', suit='Spades')   # Invalid value
SingleCardTrigger(value='8', suit='Diamonds')  # Wait, this is valid if 'Diamonds' is correct
```

---

### 3. SuitPatternTrigger

**Purpose:** Triggers on cards matching a suit pattern (e.g., all red cards, all black cards)

**Configuration:**
```python
from core.rulebook_design import SuitPatternTrigger

# All red cards (Hearts or Diamonds)
trigger = SuitPatternTrigger(pattern='red')

# All black cards (Clubs or Spades)
trigger = SuitPatternTrigger(pattern='black')

# Custom combination of suits
trigger = SuitPatternTrigger(pattern=['Hearts', 'Spades'])
```

**Limitations:**
- ✅ Pattern must be 'red', 'black', or a list of valid suits
- ✅ List cannot be empty
- ✅ All suits in list must be valid suits
- ✅ 'red' automatically means Hearts or Diamonds
- ✅ 'black' automatically means Clubs or Spades

**Validation:**
- Validates pattern is valid ('red', 'black', or valid suit/list)
- Validates all suits in list are from valid suits

**Examples:**
```python
# ✓ Valid configurations
SuitPatternTrigger(pattern='red')   # All red cards
SuitPatternTrigger(pattern='black')  # All black cards
SuitPatternTrigger(pattern=['Hearts', 'Spades'])  # Custom

# ✗ Invalid - will raise ValueError
SuitPatternTrigger(pattern='blue')  # Invalid pattern
SuitPatternTrigger(pattern=[])      # Empty list
SuitPatternTrigger(pattern=['InvalidSuit'])  # Invalid suit
```

---

### 4. SequenceTrigger

**Purpose:** Triggers when multiple cards of the same value are played consecutively

**Configuration:**
```python
from core.rulebook_design import SequenceTrigger

# Two 7s in a row
trigger = SequenceTrigger(value='7', count=2)

# Three 8s in a row
trigger = SequenceTrigger(value='8', count=3)
```

**Limitations:**
- ✅ Count must be >= 2 and <= 3 (use `CardValueTrigger` for single cards)
- ✅ Maximum sequence length is **3 cards**
- ✅ Requires `game_state['recent_cards']` to track history
- ⚠️ Sequence resets when a different card value is played
- ⚠️ Three-card sequences are rare in gameplay

**Validation:**
- Validates value against valid card values
- Validates count is an integer
- Validates count >= 2
- Validates count <= 3 (maximum sequence length)

**Examples:**
```python
# ✓ Valid configurations
SequenceTrigger(value='7', count=2)   # Two 7s
SequenceTrigger(value='8', count=3)   # Three 8s (maximum)

# ✗ Invalid - will raise ValueError
SequenceTrigger(value='7', count=1)   # Use CardValueTrigger instead
SequenceTrigger(value='7', count=4)  # Exceeds maximum of 3
SequenceTrigger(value='15', count=2)  # Invalid card value
```

---

## Configuration Best Practices

### 1. Choose the Right Trigger Type

```python
# ✓ Correct: Use CardValueTrigger for value-only
CardValueTrigger(value='8')

# ⚠️ Works but less clear: SingleCardTrigger with suit=None
SingleCardTrigger(value='8', suit=None)  # Less explicit

# ✗ Wrong: Wildcard that matches everything
SingleCardTrigger(value=None, suit=None)  # Will raise error
```

### 2. Sequence Limits

```python
# ✓ Valid sequences (2 or 3 only)
SequenceTrigger(value='7', count=2)   # Two 7s
SequenceTrigger(value='8', count=3)  # Three 8s (maximum)

# ✗ Invalid
SequenceTrigger(value='7', count=1)   # Use CardValueTrigger instead
SequenceTrigger(value='7', count=4)  # Exceeds maximum of 3
```

### 3. Validation at Creation Time

All triggers validate their configuration immediately:

```python
try:
    trigger = CardValueTrigger(value='15')
except ValueError as e:
    print(f"Configuration error: {e}")
    # Output: Configuration error: CardValueTrigger: Invalid value '15'...
```

### 4. Multiple Rules Per Card

You can have multiple rules that trigger on the same card - they're checked in order:

```python
# Rule 1: Skip on 8
rule1 = Rule(CardValueTrigger('8'), SkipAction())

# Rule 2: Typing on 8 (different action)
rule2 = Rule(CardValueTrigger('8'), TypingAction("type this"))

# Both will be checked when an 8 is played
```

---

## Configuration Checklist

Before creating a trigger, verify:

- [ ] Value is one of: `A`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `J`, `Q`, `K`
- [ ] Suit (if used) is one of: `Hearts`, `Diamonds`, `Clubs`, `Spades`
- [ ] For `SingleCardTrigger`: At least one of value or suit is specified
- [ ] For `SequenceTrigger`: Count is 2 or 3 only (maximum sequence is 3 cards)
- [ ] For `SuitPatternTrigger`: Pattern is 'red', 'black', or a valid list of suits
- [ ] Trigger type matches your use case (value-only → `CardValueTrigger`, pattern → `SuitPatternTrigger`)

---

## Common Patterns

### Pattern 1: All Cards of a Value (e.g., all 7s)

```python
# All 7s (any suit)
trigger = CardValueTrigger(value='7')

# All 8s
trigger = CardValueTrigger(value='8')

# All Aces
trigger = CardValueTrigger(value='A')
```

### Pattern 2: All Cards of a Pattern (e.g., all red cards)

```python
# All red cards (Hearts or Diamonds)
trigger = SuitPatternTrigger(pattern='red')

# All black cards (Clubs or Spades)
trigger = SuitPatternTrigger(pattern='black')

# Custom combination
trigger = SuitPatternTrigger(pattern=['Hearts', 'Spades'])
```

### Pattern 3: Sequence Rules (up to 3 cards)

```python
# Two 7s in a row
trigger = SequenceTrigger(value='7', count=2)

# Three 8s in a row (maximum)
trigger = SequenceTrigger(value='8', count=3)
```

### Pattern 4: Special Card Rules

```python
# Specific card special rule
trigger = SingleCardTrigger(value='K', suit='Hearts')

# Any King
trigger = CardValueTrigger(value='K')
```

---

## Summary Table

| Trigger Type | When to Use | Required Fields | Limitations |
|--------------|-------------|-----------------|-------------|
| `CardValueTrigger` | Any card of a value (e.g., all 7s) | `value` | Single value only |
| `SuitPatternTrigger` | All cards of a pattern (e.g., all red) | `pattern` | 'red', 'black', or list of suits |
| `SequenceTrigger` | Multiple consecutive cards | `value`, `count` | Count = 2 or 3 only |
| `SingleCardTrigger` | Specific card or suit-based | `value` OR `suit` (at least one) | Cannot be `(None, None)` |

---

## Validation Example

```python
from core.trigger_config_review import validate_trigger_configuration_checklist

# Check a configuration before creating trigger
config = {'value': '8', 'suit': 'Spades'}
issues = validate_trigger_configuration_checklist('single_card', config)

if issues:
    print("Configuration issues found:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("Configuration is valid!")
```

