# Poker UI — Code Documentation

## Overview

The `src/ui` package adds a pygame-based graphical interface to the PyPokerEngine project. It lets a human player sit at a virtual poker table, see their cards and the community cards, track all player stacks and actions, and make decisions by clicking buttons. It also exposes a clean API so AI-vs-AI games can be visualised without any changes to the existing game or agent code.

---

## File Structure

```
src/
├── environment/
│   └── game.py            # PyPokerEngine game runner and base agent (pre-existing)
├── features/
│   └── state_encoder.py   # Numeric feature encoder and hand evaluator (pre-existing)
└── ui/
    ├── __init__.py         # Package exports
    ├── poker_ui.py         # Pygame renderer — the visual table
    ├── human_agent.py      # PokerAgent subclass for human play
    └── play.py             # Entry-point script: You vs RandomBot + CallBot
```

---

## `src/ui/__init__.py`

A minimal package init that re-exports the two main public classes so callers can write:

```python
from src.ui import PokerUI, HumanAgent
```

---

## `src/ui/poker_ui.py`

The core renderer. Everything visual lives here.

### Constants and configuration

At the top of the file, all visual parameters are defined as module-level constants so they are easy to tweak in one place:

| Group | Constants | Purpose |
|---|---|---|
| Colours | `BG`, `GOLD`, `BTN_FOLD`, `BTN_CALL`, `BTN_RAISE`, … | RGB tuples for every UI element |
| Layout | `WIN_W`, `WIN_H`, `CARD_W`, `CARD_H` | Window and card dimensions in pixels |
| Fonts | `FONT_LARGE`, `FONT_MED`, `FONT_SMALL` | Font sizes |
| Card data | `SUIT_SYMBOLS`, `SUIT_COLORS`, `RANK_DISPLAY` | Maps PyPokerEngine card codes to display strings |
| Street labels | `STREET_LABELS` | Maps engine street names to display text |

### Module-level drawing helpers

These are plain functions, not methods, because they do not need any UI state.

#### `_draw_card(surface, x, y, card_str, font_big, font_small, face_up=True)`

Draws a single playing card at pixel position `(x, y)`.

- **Face-up**: white rounded rectangle with the rank and suit symbol in the top-left corner, a large suit symbol centred on the card, and a mirrored rank/suit in the bottom-right corner. Red for hearts/diamonds, black for spades/clubs.
- **Face-down**: blue rounded rectangle with a gold border and a darker inner rectangle as a simple pattern.
- `card_str` uses PyPokerEngine's suit-first format, e.g. `"CA"` = Ace of Clubs, `"H9"` = Nine of Hearts.

#### `_draw_card_placeholder(surface, x, y)`

Draws a dark green empty slot for community cards that have not been dealt yet.

#### `_draw_bar(surface, x, y, w, h, value, color, label, font)`

Draws a horizontal progress bar. `value` is a float in `[0, 1]`. Used for the hand strength and equity HUD bars. The label and percentage are rendered above the bar.

### `Button` class

A lightweight clickable button.

- `__init__(rect, label, color, font)` — stores position, label text, background colour, and font.
- `draw(surface)` — renders the button with a gold border. Brightens the background colour when `self.hovered` is `True`.
- `handle_event(event) -> bool` — updates hover state on `MOUSEMOTION` and returns `True` on a left-click inside the button's rect.

### `PokerUI` class

The main class. Owns the pygame window, all rendering logic, and the thread-synchronisation primitives that let the game thread and the UI thread communicate safely.

#### Threading model

pygame must run on the main thread (a macOS and SDL requirement). The game engine runs in a background thread. The two threads share state through a `threading.Lock` and a `threading.Event`:

- `_state_lock` — a `threading.Lock` that guards all shared game-state fields. The game thread acquires it in `set_state()` and `add_action_log()`; the render thread acquires it briefly at the start of `_render()` to snapshot the state, then releases it before drawing.
- `_action_event` — a `threading.Event`. When it is the human's turn, `wait_for_action()` clears the event and blocks the game thread with `event.wait()`. When the human clicks a button, `_handle_event()` sets `_chosen_action` and calls `event.set()`, which unblocks the game thread.

#### `__init__(title)`

Initialises pygame, creates the window (`1100 × 720`), loads five font sizes, and sets up all shared state fields and the three action buttons (Fold, Call, Raise) positioned at the bottom centre of the window.

#### Public API (called from the game thread)

| Method | Purpose |
|---|---|
| `set_state(round_state, hole_cards, hand_strength, equity, human_uuid, valid_actions, raise_min, raise_max)` | Push a complete game state snapshot to the renderer. All fields are extracted from the PyPokerEngine `round_state` dict. Thread-safe. |
| `add_action_log(message)` | Append a line to the action log. Keeps the last 12 entries. Thread-safe. |
| `set_winner(message)` | Set the winner banner text. Thread-safe. |
| `wait_for_action() -> (str, int)` | Block the game thread until the human clicks a button. Returns `(action, amount)`. |
| `close()` | Signal the event loop to exit. |

#### `run(game_thread_fn=None)`

The main event loop. Must be called from the main thread. If `game_thread_fn` is provided, it is launched as a daemon thread before the loop starts. The loop runs at 30 FPS, processes events, calls `_render()`, and flips the display buffer.

#### `_handle_event(event)`

Only active when `_waiting` is `True` (i.e. it is the human's turn).

- **Left/right arrow keys** — adjust the raise amount by 1/20th of the raise range per keypress.
- **Mouse wheel** — same step, driven by scroll direction.
- **Button clicks** — resolved by delegating to each `Button.handle_event()`. On a hit, `_chosen_action` is set and `_action_event` is signalled.

#### `_render()`

Called every frame. Snapshots the shared state under the lock, then draws all layers in order:

1. **Background** — solid felt-green fill.
2. **Table oval** — darker green ellipse with a gold border.
3. **Street label** — current street (PRE-FLOP / FLOP / TURN / RIVER) centred at the top.
4. **Round counter** — top-right corner.
5. **Community cards** — five card slots centred on the table. Dealt cards are drawn face-up; undealt slots show a placeholder.
6. **Pot** — chip amount above the community cards.
7. **Players** — delegated to `_draw_players()`.
8. **HUD bars** — hand strength (green) and equity (blue) on the left, only shown when hole cards are available.
9. **Action log** — delegated to `_draw_log()`.
10. **Action buttons** — delegated to `_draw_action_panel()`, only shown when waiting for input.
11. **Winner banner** — delegated to `_draw_winner_banner()`, only shown when `_winner_msg` is set.

#### `_draw_players(seats, human_uuid, hole_cards)`

Positions player name plates around the table oval using trigonometry. Players are evenly spaced around a full 360° circle, with the human player anchored at the bottom (270°). For each seat:

- A semi-transparent black name plate shows the player's name and stack.
- The human's plate has a gold border to distinguish it.
- Active players (state = `"participating"`) are shown in full brightness; eliminated players are dimmed.
- The human's hole cards are drawn face-up next to their plate.
- Bot players show two face-down cards while they are still active.

#### `_draw_log(log)`

Renders the action log in a semi-transparent panel on the right side of the screen. Shows the last 10 entries. The most recent entry is rendered in full white; older entries are dimmed.

#### `_draw_action_panel(valid_acts, raise_amt, raise_min, raise_max)`

Draws the three action buttons at the bottom of the screen. The Call button label is updated dynamically to show the exact call amount (or "CHECK" if the amount is zero). The Raise button is only shown if raising is a valid action. When raise is available, a horizontal slider bar to the right of the buttons shows the current raise amount relative to the min/max range, with a keyboard hint below it.

#### `_draw_winner_banner(message)`

Overlays a semi-transparent black banner with a gold border in the centre of the screen, displaying the winner message in large gold text.

---

## `src/ui/human_agent.py`

### `HumanAgent` class

Subclasses `PokerAgent` from `src/environment/game.py`. It bridges the PyPokerEngine lifecycle callbacks to the `PokerUI` renderer, and blocks the engine thread when it is the human's turn to act.

#### `__init__(ui, initial_stack, max_rounds)`

Stores a reference to the `PokerUI` instance and configuration values used for normalising the hand-strength bars.

#### Lifecycle callbacks

These are called automatically by PyPokerEngine at the appropriate moments:

| Callback | What it does |
|---|---|
| `receive_game_start_message(game_info)` | Stores the initial stack size. |
| `receive_round_start_message(round_count, hole_card, seats)` | Captures `self.uuid` (assigned by the engine after game start) into `self.my_uuid`. |
| `receive_street_start_message(street, round_state)` | Pushes a state update to the UI so the board refreshes when a new street begins. |
| `receive_game_update_message(action, round_state)` | Resolves the acting player's UUID to their display name, appends a line to the action log, and refreshes the UI. |
| `receive_round_result_message(winners, hand_info, round_state)` | Calls `ui.set_winner()` with the winner's name and chip gain. |

#### `decide_action(valid_actions, hole_card, round_state)`

This is the core method — called by the engine when it is the human's turn.

1. Ensures `self.my_uuid` is populated.
2. Calls `compute_hand_strength()` from `state_encoder.py` to get a normalised hand strength score (0–1) using the treys evaluator.
3. Calls `compute_equity_monte_carlo()` from `state_encoder.py` with 150 simulations to estimate win probability.
4. Extracts the raise min/max bounds from `valid_actions`.
5. Calls `ui.set_state()` to push all of this to the renderer.
6. Calls `ui.wait_for_action()` to block until the human clicks a button.
7. Returns the chosen `(action, amount)` tuple to the engine.

#### `_push_state(round_state, waiting=False)`

A convenience helper that calls `ui.set_state()` with neutral hand metrics (0.5) for lifecycle callbacks where hole cards are not available (outside of `decide_action`).

---

## `src/ui/play.py`

The entry-point script. Run it with:

```bash
python -m src.ui.play
```

It sets up a three-player game — the human, a `RandomAgent`, and a `CallAgent` — with 15 rounds, 1000-chip starting stacks, and a 10-chip small blind. The game runs in a background thread via `ui.run(game_thread_fn=play)`. When all rounds are complete, the final chip counts for all players are displayed in the winner banner.

---

## How the pieces connect

```
Main thread                          Game thread (daemon)
───────────────────────────────      ──────────────────────────────────────
ui.run(game_thread_fn=play)   ──▶   run_game(agents, ...)
  │                                    │
  │  pygame event loop (30 FPS)        │  PyPokerEngine calls agent callbacks
  │  _render() every frame             │
  │                                    │  HumanAgent.receive_*() 
  │  ◀── ui.set_state() ───────────────┤    calls ui.set_state()
  │  ◀── ui.add_action_log() ──────────┤    calls ui.add_action_log()
  │                                    │
  │                                    │  HumanAgent.decide_action()
  │  ◀── ui.wait_for_action() ─────────┤    blocks game thread
  │                                    │    (threading.Event.wait)
  │  human clicks button               │
  │  _handle_event() sets              │
  │    _chosen_action                  │
  │    _action_event.set() ───────────▶│  unblocks, returns action to engine
  │                                    │
```

The `threading.Lock` ensures `set_state()` and `_render()` never read/write shared fields at the same time. The `threading.Event` provides the blocking/unblocking mechanism for human input without busy-waiting.

---

## Controls

| Input | Action |
|---|---|
| Click **FOLD** | Fold the hand |
| Click **CALL** | Call the current bet (or check if free) |
| Click **RAISE** | Raise by the currently selected amount |
| **← →** arrow keys | Decrease / increase raise amount |
| **Mouse wheel** | Decrease / increase raise amount |
| Close window | Folds the current hand and exits |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pygame` | 2.6.1 | Window, rendering, event handling |
| `pypokerengine` | (existing) | Game engine and agent lifecycle |
| `treys` | (existing) | Hand strength evaluation |

Install pygame into the project venv:

```bash
pip install pygame==2.6.1
```
