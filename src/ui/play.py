"""
ui/play.py
Run a poker game with the pygame UI.

To plug in your own agent, swap it into the agents list at the bottom.
Your agent only needs to implement declare_action() — everything else is handled.

Run from the repo root:
    python -m src.ui.play
"""

import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer
from pypokerengine.api.game import setup_config, start_poker

from src.ui.poker_ui import PokerUI
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation

_SUIT_MAP = {
    'S': Suit.SPADES,
    'H': Suit.HEARTS,
    'D': Suit.DIAMONDS,
    'C': Suit.CLUBS,
}
_RANK_MAP = {
    '2': Rank.TWO,   '3': Rank.THREE, '4': Rank.FOUR,  '5': Rank.FIVE,
    '6': Rank.SIX,   '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
    'T': Rank.TEN,   'J': Rank.JACK,  'Q': Rank.QUEEN, 'K': Rank.KING,
    'A': Rank.ACE,
}

def _parse_card(card_str: str) -> Card:
    """Convert a PyPokerEngine card string like 'SA' or 'H9' to a core Card."""
    suit = _SUIT_MAP[card_str[0].upper()]
    rank = _RANK_MAP[card_str[1].upper()]
    return Card(rank, suit)

def _hand_name(hole_strs: list, community_strs: list) -> str:
    """
    Use src.core.hand_evaluator.evaluate() to get the best 5-card hand name
    from a player's hole cards + community cards.
    Returns a readable string like "Full House".
    """
    all_cards = [_parse_card(c) for c in hole_strs + community_strs]
    if len(all_cards) < 5:
        return ""

    # Try all 5-card combinations and return the best hand
    from itertools import combinations
    best = HandRank.HIGH_CARD
    for combo in combinations(all_cards, 5):
        result = evaluate(list(combo))
        if result > best:
            best = result

    return best.name.replace("_", " ").title()


# Simple baseline bots 

class RandomAgent(BasePokerPlayer):
    """Picks a random valid action."""
    def declare_action(self, valid_actions, hole_card, round_state):
        action = random.choice(valid_actions)
        if action["action"] == "raise":
            mn, mx = action["amount"]["min"], action["amount"]["max"]
            return "raise", random.randint(mn, mx) if mx > mn else mn
        return action["action"], action["amount"]
    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass


class CallAgent(BasePokerPlayer):
    """Always calls."""
    def declare_action(self, valid_actions, hole_card, round_state):
        call = valid_actions[1]
        return call["action"], call["amount"]
    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass


# Hole card registry
# All agents store their cards here at round start so the showdown can reveal them.
# Maps player name -> list of card strings.
_hole_card_registry: dict = {}

# Players whose cards are hidden face-down during live play (AI agents).
# Their cards are still stored in the registry and revealed at showdown.
_hidden_during_hand: set = set()


def _ui_update(ui, hole_cards, round_state):
    """Update the UI. AI agents' cards are hidden during the hand (shown only at showdown)."""
    # only show cards for players NOT in the hidden set (i.e. the human player)
    visible_cards = {
        name: cards
        for name, cards in _hole_card_registry.items()
        if name not in _hidden_during_hand
    }
    ui.update(
        hole_cards      = hole_cards,
        community_cards = round_state.get("community_card", []),
        seats           = round_state.get("seats", []),
        pot             = round_state.get("pot", {}).get("main", {}).get("amount", 0),
        street          = round_state.get("street", "preflop"),
        round_num       = round_state.get("round_count", 0),
        all_hole_cards  = visible_cards,
    )


# Human agent 

class HumanAgent(BasePokerPlayer):
    """Lets a human play via the pygame buttons."""

    def __init__(self, ui: PokerUI, name: str = "You"):
        self.ui    = ui
        self._name = name

    def declare_action(self, valid_actions, hole_card, round_state):
        _ui_update(self.ui, hole_card, round_state)
        self.ui.log_action("Your turn")
        return self.ui.ask_human(valid_actions)

    def receive_game_start_message(self, g): pass

    def receive_round_start_message(self, r, hole_card, s):
        _hole_card_registry[self._name] = hole_card

    def receive_street_start_message(self, s, rs): pass

    def receive_game_update_message(self, action, round_state):
        name   = action.get("player_uuid", "?")
        act    = action.get("action", "")
        amount = action.get("amount", 0)
        for seat in round_state.get("seats", []):
            if seat.get("uuid") == name:
                name = seat.get("name", name)
                break
        self.ui.log_action(f"{name}: {act} {amount or ''}")
        _ui_update(self.ui, [], round_state)
        self.ui.draw()

    def receive_round_result_message(self, winners, hand_info, round_state):
        winner_name = winners[0].get("name", "?") if winners else "?"
        _show_showdown(self.ui, hand_info, round_state, winner_name)


# Watcher agent

class WatcherAgent(BasePokerPlayer):
    """
    Wraps any agent and mirrors its game state to the UI.
    The wrapped agent still makes all the decisions.
    Set is_focus=True to show that agent's hole cards face-up.
    """

    def __init__(self, ui: PokerUI, agent: BasePokerPlayer, name: str, is_focus: bool = False):
        self.ui       = ui
        self.agent    = agent
        self._name    = name
        self.is_focus = is_focus

    def set_uuid(self, uuid):
        # pypokerengine sets uuid on the wrapper but the inner agent also needs it
        # so that receive_game_start_message can look up its own name from game_info
        super().set_uuid(uuid)
        self.agent.set_uuid(uuid)

    def declare_action(self, valid_actions, hole_card, round_state):
        if self.is_focus:
            _ui_update(self.ui, [], round_state)
            self.ui.draw()
        return self.agent.declare_action(valid_actions, hole_card, round_state)

    def receive_game_start_message(self, g):
        self.agent.receive_game_start_message(g)

    def receive_round_start_message(self, r, hole_card, s):
        _hole_card_registry[self._name] = hole_card   # kept for showdown reveal
        _hidden_during_hand.add(self._name)            # hidden face-down during play
        self.agent.receive_round_start_message(r, hole_card, s)

    def receive_street_start_message(self, s, rs):
        _ui_update(self.ui, [], rs)
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
        winner_name = winners[0].get("name", "?") if winners else "?"
        _show_showdown(self.ui, hand_info, round_state, winner_name)
        self.agent.receive_round_result_message(winners, hand_info, round_state)


# Showdown 

def _show_showdown(ui, hand_info, round_state, winner_name):
    """
    Reveal all players' hole cards and evaluate their hands using
    src.core.hand_evaluator, then display the showdown screen.
    """
    seats     = round_state.get("seats", [])
    community = round_state.get("community_card", [])

    player_hands = []
    for seat in seats:
        name  = seat.get("name", "?")
        cards = _hole_card_registry.get(name, [])
        # Use our own hand evaluator to get the hand name
        hand_label = _hand_name(cards, community) if cards else ""
        player_hands.append({
            "name":      name,
            "cards":     cards,
            "hand_name": hand_label,
        })

    ui.show_showdown(player_hands, community, winner_name, pause_seconds=4)


# Game runner

def run_with_ui(agents, max_rounds=15, initial_stack=1000, small_blind=10):
    config = setup_config(
        max_round=max_rounds,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )
    for name, agent in agents:
        config.register_player(name=name, algorithm=agent)
    return start_poker(config, verbose=0)


# Entry point

if __name__ == "__main__":
    ui = PokerUI("Texas Hold'em")

    from src.agent.poker_agent import PokerAgent
    agents = [
        ("You",         HumanAgent(ui, name="You")),
        ("PokerAgent",  WatcherAgent(ui, PokerAgent(), name="PokerAgent", is_focus=True))
    ]

    result = run_with_ui(agents)

    standings = "  |  ".join(f"{p['name']}: {p['stack']:,}" for p in result["players"])
    ui.show_winner(standings, pause_seconds=5)
    ui.quit()
