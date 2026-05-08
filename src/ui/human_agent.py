"""
ui/human_agent.py
-----------------
A PokerAgent subclass that drives the pygame UI and lets a human play.

Usage:
    from src.ui.human_agent import HumanAgent
    from src.ui.poker_ui import PokerUI
    from src.environment.game import run_game, RandomAgent

    ui    = PokerUI()
    human = HumanAgent(ui)

    agents = [("You", human), ("Bot", RandomAgent())]

    # run_game must be called from a background thread so the UI can run on main
    import threading
    def play():
        result = run_game(agents, max_rounds=10, initial_stack=1000, small_blind=10, verbose=0)
        # Show final stacks
        lines = ["  ".join(f"{p['name']} {p['stack']}" for p in result["players"])]
        ui.set_winner(lines[0])

    ui.run(game_thread_fn=play)
"""

import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.environment.game import PokerAgent
from src.features.state_encoder import compute_hand_strength, compute_equity_monte_carlo


class HumanAgent(PokerAgent):
    """
    Poker agent that renders the game state via PokerUI and waits for the
    human to click Fold / Call / Raise before returning an action.

    Args:
        ui: a PokerUI instance (must be running on the main thread)
        initial_stack: used for normalising the state encoder bars
        max_rounds: used for normalising the round-progress bar
    """

    def __init__(self, ui, initial_stack: int = 1000, max_rounds: int = 20):
        super().__init__()
        self.ui            = ui
        self.initial_stack = initial_stack
        self.max_rounds    = max_rounds
        self.my_uuid: str  = ""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def receive_game_start_message(self, game_info):
        self.initial_stack = game_info.get("player_num", 2) and self.initial_stack
        # PyPokerEngine doesn't pass our UUID here; we grab it in round_start

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Grab our UUID from the seats list by matching the name we registered with
        # (PyPokerEngine sets uuid on the player object after game start)
        if hasattr(self, "uuid"):
            self.my_uuid = self.uuid

    def receive_street_start_message(self, street, round_state):
        self._push_state(round_state, waiting=False)

    def receive_game_update_message(self, action, round_state):
        name   = action.get("player_uuid", "?")
        act    = action.get("action", "?")
        amount = action.get("amount", 0)
        # Try to resolve uuid -> name
        for seat in round_state.get("seats", []):
            if seat.get("uuid") == name:
                name = seat.get("name", name)
                break
        self.ui.add_action_log(f"{name}: {act} {amount if amount else ''}")
        self._push_state(round_state, waiting=False)

    def receive_round_result_message(self, winners, hand_info, round_state):
        for w in winners:
            name   = w.get("name", "?")
            amount = w.get("amount", 0)
            self.ui.set_winner(f"{name} wins  +{amount:,} chips")
        self._push_state(round_state, waiting=False)

    # ── Action ────────────────────────────────────────────────────────────────

    def decide_action(self, valid_actions, hole_card, round_state):
        # Grab our UUID (available after game start via self.uuid)
        if hasattr(self, "uuid") and not self.my_uuid:
            self.my_uuid = self.uuid

        # Compute hand metrics
        community = round_state.get("community_card", [])
        strength  = compute_hand_strength(hole_card, community)
        num_opp   = max(
            len([s for s in round_state.get("seats", []) if s.get("state") == "participating"]) - 1,
            1,
        )
        equity = compute_equity_monte_carlo(hole_card, community, num_opponents=num_opp,
                                            num_simulations=150)

        # Raise bounds
        raise_min, raise_max = 0, 0
        for a in valid_actions:
            if a["action"] == "raise":
                raise_min = a["amount"].get("min", 0)
                raise_max = a["amount"].get("max", 0)

        # Push state to UI and wait for click
        self.ui.set_state(
            round_state=round_state,
            hole_cards=hole_card,
            hand_strength=strength,
            equity=equity,
            human_uuid=self.my_uuid,
            valid_actions=valid_actions,
            raise_min=raise_min,
            raise_max=raise_max,
        )
        self.ui.add_action_log("Your turn — choose an action")

        action_str, amount = self.ui.wait_for_action()
        return action_str, amount

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _push_state(self, round_state, waiting=False):
        """Push a state update without blocking for input."""
        community = round_state.get("community_card", [])
        self.ui.set_state(
            round_state=round_state,
            hole_cards=[],          # hole cards not available outside declare_action
            hand_strength=0.5,
            equity=0.5,
            human_uuid=self.my_uuid,
        )
