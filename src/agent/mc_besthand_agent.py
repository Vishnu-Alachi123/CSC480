"""
agent/mc_besthand_agent.py — MCBestHandAgent
Monte Carlo using kicker-aware hand_score() for accurate tie resolution.

Improves on MCOppAgent by replacing HandRank enum comparison with
hand_score() tuples, so ties are resolved by kickers (e.g. A-high flush
beats K-high flush). No tracker, no danger score.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.best_hand_probability.mc_besthand import monte_carlo_best_hand
from src.core.hand_evaluator import HandRank

_SUIT_MAP = {
    'S': Suit.SPADES, 'H': Suit.HEARTS,
    'D': Suit.DIAMONDS, 'C': Suit.CLUBS,
}
_RANK_MAP = {
    '2': Rank.TWO,   '3': Rank.THREE, '4': Rank.FOUR,  '5': Rank.FIVE,
    '6': Rank.SIX,   '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
    'T': Rank.TEN,   'J': Rank.JACK,  'Q': Rank.QUEEN, 'K': Rank.KING,
    'A': Rank.ACE,
}

def _parse(card_str: str) -> Card:
    return Card(_RANK_MAP[card_str[1].upper()], _SUIT_MAP[card_str[0].upper()])


RAISE_WIN_PCT = 60
CALL_WIN_PCT  = 40


class MCBestHandAgent(BasePokerPlayer):
    """
    Kicker-aware MC agent. Uses hand_score() for accurate tiebreaking so
    equal-rank hands are resolved correctly by their kicker cards.
    No tracker, no danger score.
    """

    def __init__(self):
        super().__init__()
        self._my_name = ""

    def receive_game_start_message(self, game_info):
        self._my_name = getattr(self, "name", "")

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        seats     = round_state.get("seats", [])

        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost    = call_action["amount"]

        parsed_hole      = [_parse(c) for c in hole_card]
        parsed_community = [_parse(c) for c in community]

        deck = Deck()
        deck.remove(parsed_hole + parsed_community)

        opp_seats = [
            s for s in seats
            if s.get("name") != self._my_name
            and s.get("state") == "participating"
        ]
        num_opp = max(len(opp_seats), 1)

        win_prob = monte_carlo_best_hand(
            hole_cards      = parsed_hole,
            community_cards = parsed_community,
            num_opponents   = num_opp,
            num_iterations  = 150,
            remaining_cards = deck.cards,
        )
        win_pct = win_prob * 100

        if win_pct >= RAISE_WIN_PCT and raise_action:
            return "raise", raise_action["amount"]["min"]
        if win_pct >= CALL_WIN_PCT:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
