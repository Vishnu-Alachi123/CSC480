"""
ui/play.py
----------
Launch a human-vs-bots poker game with the pygame UI.

Run from the repo root:
    python -m src.ui.play

Controls:
    Fold / Call / Raise buttons — click to act
    ← → arrow keys or mouse wheel — adjust raise amount
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ui.poker_ui import PokerUI
from src.ui.human_agent import HumanAgent
from src.environment.game import run_game, RandomAgent, CallAgent

MAX_ROUNDS    = 15
INITIAL_STACK = 1000
SMALL_BLIND   = 10


def main():
    ui    = PokerUI(title="Texas Hold'em — Human vs Bots")
    human = HumanAgent(ui, initial_stack=INITIAL_STACK, max_rounds=MAX_ROUNDS)

    agents = [
        ("You",       human),
        ("RandomBot", RandomAgent()),
        ("CallBot",   CallAgent()),
    ]

    def play():
        result = run_game(
            agents,
            max_rounds=MAX_ROUNDS,
            initial_stack=INITIAL_STACK,
            small_blind=SMALL_BLIND,
            verbose=0,
        )
        # Show final standings
        standings = "  |  ".join(
            f"{p['name']}: {p['stack']:,}" for p in result["players"]
        )
        ui.set_winner(standings)

    ui.run(game_thread_fn=play)


if __name__ == "__main__":
    main()
