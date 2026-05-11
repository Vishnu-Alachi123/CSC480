"""
ui/play.py
----------
Run a poker game with the pygame UI.

To plug in your own agent, just swap it in the `agents` list below.
Your agent only needs to implement decide_action() — everything else is handled.

Run from the repo root:
    python -m src.ui.play
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer
from pypokerengine.api.game import setup_config, start_poker

from src.ui.poker_ui import PokerUI
from src.environment.game import RandomAgent, CallAgent

# ── Config ────────────────────────────────────────────────────────────────────
MAX_ROUNDS    = 15
INITIAL_STACK = 1000
SMALL_BLIND   = 10


# ── Human agent — reads from the UI ──────────────────────────────────────────
class HumanAgent(BasePokerPlayer):
    """Lets a human play via the pygame buttons."""

    def __init__(self, ui: PokerUI):
        self.ui = ui

    def declare_action(self, valid_actions, hole_card, round_state):
        self.ui.update(
            hole_cards      = hole_card,
            community_cards = round_state.get("community_card", []),
            seats           = round_state.get("seats", []),
            pot             = round_state.get("pot", {}).get("main", {}).get("amount", 0),
            street          = round_state.get("street", "preflop"),
            round_num       = round_state.get("round_count", 0),
        )
        self.ui.log_action("Your turn")
        return self.ui.ask_human(valid_actions)

    def receive_game_start_message(self, g):   pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs):  pass
    def receive_game_update_message(self, action, round_state):
        # Log every action so the human can see what opponents did
        name   = action.get("player_uuid", "?")
        act    = action.get("action", "")
        amount = action.get("amount", 0)
        for seat in round_state.get("seats", []):
            if seat.get("uuid") == name:
                name = seat.get("name", name)
                break
        self.ui.log_action(f"{name}: {act} {amount or ''}")
        self.ui.update(
            hole_cards      = [],
            community_cards = round_state.get("community_card", []),
            seats           = round_state.get("seats", []),
            pot             = round_state.get("pot", {}).get("main", {}).get("amount", 0),
            street          = round_state.get("street", "preflop"),
            round_num       = round_state.get("round_count", 0),
        )
        self.ui.draw()

    def receive_round_result_message(self, winners, hand_info, round_state):
        for w in winners:
            self.ui.show_winner(f"{w.get('name','?')} wins  +{w.get('amount',0):,}")


# ── Watcher agent — shows an AI game in the UI ───────────────────────────────
class WatcherAgent(BasePokerPlayer):
    """
    Wraps any agent and mirrors its game state to the UI so you can watch.
    The wrapped agent still makes all the decisions.
    """

    def __init__(self, ui: PokerUI, agent: BasePokerPlayer, is_focus: bool = False):
        self.ui       = ui
        self.agent    = agent
        self.is_focus = is_focus   # if True, show this agent's hole cards face-up

    def declare_action(self, valid_actions, hole_card, round_state):
        if self.is_focus:
            self.ui.update(
                hole_cards      = hole_card,
                community_cards = round_state.get("community_card", []),
                seats           = round_state.get("seats", []),
                pot             = round_state.get("pot", {}).get("main", {}).get("amount", 0),
                street          = round_state.get("street", "preflop"),
                round_num       = round_state.get("round_count", 0),
            )
            self.ui.draw()
        return self.agent.declare_action(valid_actions, hole_card, round_state)

    def receive_game_start_message(self, g):
        self.agent.receive_game_start_message(g)

    def receive_round_start_message(self, r, h, s):
        self.agent.receive_round_start_message(r, h, s)

    def receive_street_start_message(self, s, rs):
        self.ui.update(
            hole_cards      = [],
            community_cards = rs.get("community_card", []),
            seats           = rs.get("seats", []),
            pot             = rs.get("pot", {}).get("main", {}).get("amount", 0),
            street          = rs.get("street", "preflop"),
            round_num       = rs.get("round_count", 0),
        )
        self.ui.draw()
        self.agent.receive_street_start_message(s, rs)

    def receive_game_update_message(self, action, round_state):
        name   = action.get("player_uuid", "?")
        act    = action.get("action", "")
        amount = action.get("amount", 0)
        for seat in round_state.get("seats", []):
            if seat.get("uuid") == name:
                name = seat.get("name", name)
                break
        self.ui.log_action(f"{name}: {act} {amount or ''}")
        self.ui.draw()
        self.agent.receive_game_update_message(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        for w in winners:
            self.ui.show_winner(f"{w.get('name','?')} wins  +{w.get('amount',0):,}")
        self.agent.receive_round_result_message(winners, hand_info, round_state)


# ── Entry point ───────────────────────────────────────────────────────────────

def run_with_ui(agents, max_rounds=MAX_ROUNDS, initial_stack=INITIAL_STACK, small_blind=SMALL_BLIND):
    """
    Run a game. agents is a list of (name, agent_instance) tuples.
    The first agent in the list is treated as the 'focus' player (cards shown face-up).
    """
    config = setup_config(
        max_round=max_rounds,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )
    for name, agent in agents:
        config.register_player(name=name, algorithm=agent)

    result = start_poker(config, verbose=0)
    return result


if __name__ == "__main__":
    ui = PokerUI("Texas Hold'em")

    # ── Swap agents here ──────────────────────────────────────────────────────
    #
    # Option A: Human vs bots
    agents = [
        ("You",       HumanAgent(ui)),
        ("RandomBot", RandomAgent()),
        ("CallBot",   CallAgent()),
    ]
    #
    # Option B: Watch two AI agents play (first one shown face-up)
    # agents = [
    #     ("MyAgent",   WatcherAgent(ui, YourAgent(), is_focus=True)),
    #     ("CallBot",   WatcherAgent(ui, CallAgent())),
    # ]
    # ─────────────────────────────────────────────────────────────────────────

    result = run_with_ui(agents)

    # Final standings
    standings = "  |  ".join(f"{p['name']}: {p['stack']:,}" for p in result["players"])
    ui.show_winner(standings, pause_seconds=5)
    ui.quit()
