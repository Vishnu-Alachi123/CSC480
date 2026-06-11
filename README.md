# Poker AI — CSC 480

A Texas Hold'em AI project built on `pypokerengine`. Includes a Monte Carlo win probability engine, opponent behavior tracking, pot odds analysis, and an combination study showing how each feature contributes to performance.

---

## Setup

**Requirements:** Python 3.11+

```bash
# create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

All commands below should be run from the project root with the virtual environment active.

---

## Running Things

### Play against the agent (pygame UI)

```bash
python -m src.ui.play
```

Opens a pygame window where you play against `PokerAgent`. Your cards are shown face-up, the agent's cards are hidden and only revealed at showdown. The agent's Monte Carlo visualization pops up after each of its decisions.

To change which agents you play against, edit the `agents` list at the bottom of `src/ui/play.py`.

### Run the benchmark

```bash
# 3-way game: StupidAgent vs CallAgent vs PokerAgent (30 games)
python -m src.tests.benchmark_agents

# 3-way with more games for a more reliable result
python -m src.tests.benchmark_agents simple 50

# Full combination study — all 9 agents against each other (30 games)
python -m src.tests.benchmark_agents combination

# combination with more games
python -m src.tests.benchmark_agents combination 50
```

Saves a chart to `benchmark_results_simple.png` or `benchmark_results_combination.png`.

### Run the unit tests

```bash
# hand evaluator tests
python -m src.tests.core_tests

# opponent tracker tests
python -m pytest src/tests/test_opponent_tracker.py
```

---

## Project Structure

```
src/
├── agent/
│   ├── poker_agent.py          the full agent — uses everything
│   ├── hand_rank_agent.py      baseline: hand rank thresholds only
│   ├── mc_hand_agent.py        adds MC for own hand (no opponent modeling)
│   ├── mc_opponent_agent.py    adds MC with opponent hand simulation
│   ├── behavior_agent.py       adds opponent behavior tracking (no MC)
│   ├── mc_behavior_agent.py    MC + behavior tracking
│   ├── mc_danger_agent.py      MC + danger/pot scoring
│   ├── call_agent.py           always calls (baseline opponent)
│   └── stupid_agent.py         always raises minimum (baseline opponent)
│
├── core/
│   ├── card.py                 Card, Rank, Suit, Deck
│   ├── hand_evaluator.py       evaluate() and hand_score()
│   ├── opponent_tracker.py     tracks opponent aggression across hands
│   ├── pot_tracker.py          pot odds, danger score, EV calculations
│   ├── opponent_win_probability/
│   │   ├── monte_carlo.py      main MC simulation
│   │   └── graph.py            decision visualization (shown during play)
│   └── best_hand_probability/
│       └── mc_besthand.py      kicker-aware MC using hand_score()
│
├── tests/
│   ├── benchmark_agents.py     runs all agents and plots results
│   ├── core_tests.py           hand evaluator unit tests
│   └── test_opponent_tracker.py
│
└── ui/
    ├── play.py                 game runner + WatcherAgent wrapper
    └── poker_ui.py             pygame table
```

---

## Agents

The agents are designed as an combination study — each one adds exactly one feature so you can see what each contributes.

| Agent | What it adds |
|---|---|
| `HandRankAgent` | Baseline — hand rank thresholds, no simulation |
| `MCHandAgent` | MC for own hand only — no opponent modeling |
| `MCOpponentAgent` | MC that deals random cards to opponents and compares |
| `BehaviorAgent` | Opponent behavior tracking without MC |
| `MCBehaviorAgent` | MC + behavior tracking (tighter vs aggressive opponents) |
| `MCDangerAgent` | MC + danger score (folds when opponents are likely strong) |
| `PokerAgent` | Everything — preflop chart, MC, adaptive thresholds, pot odds, c-betting, tracking, danger score |

`CallAgent` (always calls) and `StupidAgent` (always raises) are the baseline opponents.

---

## Swapping the Agent in the UI

Edit the bottom of `src/ui/play.py`:

```python
from src.agent.poker_agent import PokerAgent

agents = [
    ("You",        HumanAgent(ui, name="You")),
    ("PokerAgent", WatcherAgent(ui, PokerAgent(), name="PokerAgent", is_focus=True)),
]
```

Replace `PokerAgent()` with any agent from `src/agent/`. The `is_focus=True` flag tells the UI to update during that agent's decision and show the visualization.

---

## Other Files

- `ARCHITECTURE.md` — full breakdown of every module and design decision
- `TRACKERS.md` — detailed explanation of how OpponentTracker and PotTracker work
- `requirements.txt` — pinned dependencies (`pip install -r requirements.txt` to install)

To regenerate `requirements.txt` after installing new packages:
```bash
pip freeze > requirements.txt
```
