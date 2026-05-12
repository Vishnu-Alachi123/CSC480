# Poker AI — CSC480

A Texas Hold'em environment for building and testing poker agents. The project provides a hand evaluator, a game state model, a rule-based agent, and a pygame table to watch games play out.

---

## Setup

**Requirements:** Python 3.11+

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the game

```bash
python -m src.ui.play
```

This opens a pygame window with you playing against **SimpleAgent** (your hand-evaluator bot) and **RandomBot**.

### Updating requirements.txt

If you install new packages, regenerate the file with:

```bash
pip freeze > requirements.txt
```

---

## Project Structure

```
src/
├── core/               # Card primitives and hand evaluation — your logic
│   ├── card.py
│   ├── hand_evaluator.py
│   └── game_state.py
├── agent/              # Poker agents
│   └── base_agent.py
├── tests/
│   └── core_tests.py   # Unit tests for the hand evaluator
└── ui/                 # Pygame table (not covered here)
```

---

## `src/core/`

This is the foundation of the project. Everything here is pure Python with no external dependencies.

### `card.py`

Defines the building blocks for a deck of cards.

**`Suit`** — an enum with four values: `SPADES`, `HEARTS`, `DIAMONDS`, `CLUBS`.

**`Rank`** — an enum mapping card names to integer values (TWO=2 through ACE=14). The integer values matter for straight detection — higher number means higher rank.

**`Card`** — holds a `Rank` and a `Suit`. Supports equality comparison and hashing so cards can be stored in sets and used as dict keys.

```python
from src.core.card import Card, Rank, Suit

card = Card(Rank.ACE, Suit.SPADES)
print(card)  # ACE of SPADES
```

**`Deck`** — generates all 52 cards on init. Has a `remove(cards)` method to deal cards out.

```python
deck = Deck()
deck.remove([Card(Rank.ACE, Suit.SPADES)])  # remove a specific card
```

---

### `hand_evaluator.py`

Classifies a 5-card hand into one of ten hand ranks. This is the core logic of the project.

**`HandRank`** — an `IntEnum` ranking hands from weakest to strongest:

| Value | Name |
|---|---|
| 1 | HIGH_CARD |
| 2 | PAIR |
| 3 | TWO_PAIR |
| 4 | THREE_OF_A_KIND |
| 5 | STRAIGHT |
| 6 | FLUSH |
| 7 | FULL_HOUSE |
| 8 | FOUR_OF_A_KIND |
| 9 | STRAIGHT_FLUSH |
| 10 | ROYAL_FLUSH |

Because `HandRank` is an `IntEnum`, ranks can be compared directly with `>`, `<`, `==`.

**Detection functions** — each takes a `list[Card]` and returns `bool`:

| Function | What it checks |
|---|---|
| `is_straight(cards)` | Five consecutive ranks (handles ace-low A-2-3-4-5) |
| `is_flush(cards)` | All five cards share the same suit |
| `get_rank_count(cards)` | Returns a `dict` of `{rank_value: count}` — used internally |
| `is_pair(cards)` | At least one rank appears exactly twice |
| `is_two_pair(cards)` | Exactly two different ranks each appear twice |
| `is_three_of_a_kind(cards)` | One rank appears exactly three times |
| `is_full_house(cards)` | Three of one rank and two of another |
| `is_four_of_a_kind(cards)` | One rank appears four times |
| `is_straight_flush(cards)` | Both a straight and a flush |
| `is_royal_flush(cards)` | A flush with 10-J-Q-K-A |

**`evaluate(cards: list[Card]) -> HandRank`**

The main function. Checks each hand type from strongest to weakest and returns the first match. Always pass exactly 5 cards.

```python
from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank

hand = [
    Card(Rank.ACE,   Suit.SPADES),
    Card(Rank.ACE,   Suit.HEARTS),
    Card(Rank.ACE,   Suit.DIAMONDS),
    Card(Rank.KING,  Suit.CLUBS),
    Card(Rank.KING,  Suit.SPADES),
]
result = evaluate(hand)
print(result)        # HandRank.FULL_HOUSE
print(result.name)   # FULL_HOUSE
print(result > HandRank.FLUSH)  # True
```

To find the best hand from 7 cards (2 hole + 5 community), try all 5-card combinations:

```python
from itertools import combinations

all_cards = hole_cards + community_cards   # list of 7 Card objects
best = max(evaluate(list(combo)) for combo in combinations(all_cards, 5))
```

---

### `game_state.py`

A data class that describes the information available to an agent when it needs to make a decision. Currently a skeleton — intended to be filled in as the agent becomes more sophisticated.

| Field | Type | Description |
|---|---|---|
| `hole_cards` | `list[Card]` | The agent's two private cards |
| `community_cards` | `list[Card]` | Shared board cards (0–5) |
| `pot` | `float` | Total chips in the pot |
| `call_amount` | `float` | How much it costs to call |
| `num_opponents` | `int` | Number of active opponents |
| `stack` | `float` | Agent's current chip count |
| `position` | `str` | Seat position (e.g. "early", "late") |

---

## `src/agent/`

### `base_agent.py`

A rule-based agent called `SimpleAgent` that uses `hand_evaluator.evaluate()` to decide what action to take each turn. This is the starting point for building a smarter agent.

#### How it works

1. Takes the hole cards and community cards from the game state
2. Converts them from PyPokerEngine's string format (e.g. `"SA"` = Ace of Spades) to `Card` objects
3. Tries every 5-card combination and finds the best `HandRank`
4. Compares the rank against two thresholds to decide the action

#### Decision thresholds

```python
RAISE_THRESHOLD = HandRank.FULL_HOUSE   # Full House or better → raise
CALL_THRESHOLD  = HandRank.STRAIGHT     # Straight or better  → call
                                        # Below Straight      → fold (or check if free)
```

These are defined at the top of the file and easy to tune.

#### Preflop behaviour

Before the flop there are fewer than 5 cards, so `evaluate()` can't run. Instead `_preflop_estimate()` does a rough assessment:
- Pocket pair → treated as `PAIR`
- Ace, King, or Queen in hand → `HIGH_CARD` (calls if cheap)
- Everything else → `HIGH_CARD` (folds if it costs chips)

#### Building your own agent

Subclass `BasePokerPlayer` from PyPokerEngine and implement `declare_action`. The only method you must return a value from is `declare_action` — the rest can be left as `pass`.

```python
from pypokerengine.players import BasePokerPlayer
from src.core.hand_evaluator import evaluate, HandRank
from src.agent.base_agent import best_hand_rank

class MyAgent(BasePokerPlayer):
    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        rank = best_hand_rank(hole_card, community)

        # Your logic here
        if rank >= HandRank.TWO_PAIR:
            return "call", valid_actions[1]["amount"]
        return "fold", 0

    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
```

Then plug it into `src/ui/play.py`:

```python
from src.agent.my_agent import MyAgent

agents = [
    ("MyAgent", WatcherAgent(ui, MyAgent(), name="MyAgent", is_focus=True)),
    ("CallBot",  WatcherAgent(ui, CallAgent(), name="CallBot")),
]
```

---

## Running the tests

```bash
python -m src.tests.core_tests
```

Tests cover all detection functions and `evaluate()` across all ten hand ranks.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `PyPokerEngine` | 1.0.1 | Game engine — deals cards, manages betting, calls agent callbacks |
| `pygame` | 2.6.1 | Visual table display |
| `treys` | 0.1.8 | Used by `src/features/state_encoder.py` for Monte Carlo equity estimation |
