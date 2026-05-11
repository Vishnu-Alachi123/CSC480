# Poker UI — Code Documentation

## Overview

The `src/ui` package adds a pygame-based graphical interface to the PyPokerEngine project. The goal is to keep the UI as simple as possible — it just draws the game state. All the interesting logic lives in your agent.

---

## File Structure

```
src/
├── environment/
│   └── game.py            # PyPokerEngine game runner and base agent (pre-existing)
├── features/
│   └── state_encoder.py   # Numeric feature encoder and hand evaluator (pre-existing)
└── ui/
    ├── __init__.py         # Package export
    ├── poker_ui.py         # Pygame renderer — the visual table
    └── play.py             # Entry point + plug-in patterns for agents
```

---

## How to run

From the repo root:

```bash
source .venv/bin/activate
python -m src.ui.play
```

Or without activating the venv:

```bash
.venv/bin/python -m src.ui.play
```

---

## `src/ui/poker_ui.py`

The entire visual layer. One class, five public methods. It knows nothing about agents or game logic — it just draws whatever state you push into it.

### `PokerUI` class

#### `__init__(title="Poker")`

Creates the pygame window (900×600), sets up fonts, and initialises empty state. Call this once before starting the game.

#### `update(hole_cards, community_cards, seats, pot, street, round_num)`

Push the latest game state to the renderer. Call this whenever something changes. Nothing is drawn until you call `draw()`.

| Argument | Type | Example |
|---|---|---|
| `hole_cards` | `list[str]` | `["SA", "HQ"]` |
| `community_cards` | `list[str]` | `["HK", "D7", "C2"]` |
| `seats` | `list[dict]` | PyPokerEngine `seats` list |
| `pot` | `int` | `240` |
| `street` | `str` | `"flop"` |
| `round_num` | `int` | `3` |

Card strings use PyPokerEngine's suit-first format: `"CA"` = Ace of Clubs, `"H9"` = Nine of Hearts.

#### `draw()`

Renders one frame to the screen. Also processes the quit event (closing the window raises `SystemExit`). Call this in your game loop to keep the display live.

#### `log_action(message)`

Appends a line to the on-screen action log. The last 8 lines are shown. Use this to display what each player did.

```python
ui.log_action("RandomBot: raise 80")
```

#### `ask_human(valid_actions) -> (str, int)`

Shows Fold / Call / Raise buttons at the bottom of the screen and blocks until the human clicks one. Returns `(action_str, amount)` in the format PyPokerEngine expects.

`valid_actions` is passed straight from PyPokerEngine's `declare_action` callback — no transformation needed.

#### `show_winner(message, pause_seconds=3)`

Overlays a banner with the winner message for a few seconds, then returns. Good for end-of-round and end-of-game announcements.

#### `quit()`

Shuts down pygame cleanly. Call this after the game loop ends.

---

## `src/ui/play.py`

The entry point. This is the only file you need to edit to plug in your agent.

### Plug-in patterns

#### Option A — Human plays

```python
agents = [
    ("You",       HumanAgent(ui)),
    ("RandomBot", RandomAgent()),
    ("CallBot",   CallAgent()),
]
```

`HumanAgent` wraps the UI's `ask_human()` method. When it's the human's turn, buttons appear and the game waits for a click.

#### Option B — Watch your AI agent

```python
agents = [
    ("MyAgent", WatcherAgent(ui, YourAgent(), is_focus=True)),
    ("CallBot",  WatcherAgent(ui, CallAgent())),
]
```

`WatcherAgent` is a thin wrapper that passes every call straight through to your real agent. It mirrors the game state to the UI so you can watch the agent play. Your agent doesn't need to know the UI exists.

Set `is_focus=True` on the agent whose hole cards you want shown face-up.

### `HumanAgent`

A `BasePokerPlayer` subclass that reads decisions from the UI.

- `declare_action` — calls `ui.update()` then `ui.ask_human()` and returns the result to the engine.
- `receive_game_update_message` — logs each opponent action and refreshes the display.
- `receive_round_result_message` — calls `ui.show_winner()`.

### `WatcherAgent`

A `BasePokerPlayer` subclass that wraps any other agent and mirrors its state to the UI.

- Every lifecycle callback is forwarded to the wrapped agent.
- `declare_action` — calls `ui.update()` and `ui.draw()` before delegating to the wrapped agent.
- `receive_street_start_message` — refreshes the board when new community cards are dealt.
- `receive_game_update_message` — logs the action and redraws.
- `receive_round_result_message` — shows the winner banner.

### `run_with_ui(agents, max_rounds, initial_stack, small_blind)`

Thin wrapper around PyPokerEngine's `setup_config` / `start_poker`. Takes the same `(name, agent)` tuple list as `run_game` in `game.py`.

---

## What gets drawn

| Element | Description |
|---|---|
| Table | Dark green oval with a gold border |
| Street + round | Centred at the top of the table |
| Community cards | 5 slots in the centre; undealt cards show as empty slots |
| Pot | Chip amount above the community cards |
| Player seats | Name and stack positioned around the oval; seat 0 (focus player) shown in gold |
| Hole cards | Face-up for the focus player, face-down for all others |
| Action log | Last 8 actions, top-right corner |
| Action buttons | Fold / Call / Raise — only shown during `ask_human()` |
| Winner banner | Semi-transparent overlay shown by `show_winner()` |

---

## Controls (human play)

| Input | Action |
|---|---|
| Click **FOLD** | Fold the hand |
| Click **CALL** | Call the current bet (shows "CHECK" if free) |
| Click **RAISE** | Raise by the minimum raise amount |
| Close window | Exits the game |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pygame` | 2.6.1 | Window, rendering, event handling |
| `PyPokerEngine` | 1.0.1 | Game engine and agent lifecycle |
| `treys` | 0.1.8 | Hand strength evaluation (used by `state_encoder.py`) |

Install all dependencies:

```bash
pip install -r requirements.txt
```
