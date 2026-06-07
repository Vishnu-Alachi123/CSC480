"""
agent/mc_danger_agent.py — MCDangerAgent
Full MC win-probability + pot-success danger score adjustment.

The danger score converts opponent win probability into a 0-100 threat level.
When danger is high (opponents likely have strong hands), the agent folds
medium-strength hands it would otherwise call. No behavioral tracking.

This implements the pot-success-tracking branch's contribution.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank, evaluate
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from itertools import combinations

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


def _best_rank(parsed_hole, parsed_community) -> HandRank:
    all_cards = parsed_hole + parsed_community
    if len(all_cards) < 5:
        if len(all_cards) >= 2 and all_cards[0].rank == all_cards[1].rank:
            return HandRank.PAIR
        return HandRank.HIGH_CARD
    return max(evaluate(list(c)) for c in combinations(all_cards, 5))


# Danger = (1 - win_prob) * 100: how likely opponents are to beat us
DANGER_THRESHOLD = 65   # fold medium hands when danger exceeds this
RAISE_RANK = HandRank.TWO_PAIR


class MCDangerAgent(BasePokerPlayer):
    """
    MC + danger score: raises strong hands only when danger is low,
    and folds medium hands when opponents look dangerous.
    No behavioral tracking (that's MCTrackerAgent).
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

        win_prob, *_ = monte_carlo_simulation(
            deck            = deck,
            hole_cards      = parsed_hole,
            community_cards = parsed_community,
            num_opp         = num_opp,
            num_sims        = 150,
        )
        danger = (1.0 - win_prob) * 100
        rank   = _best_rank(parsed_hole, parsed_community)

        if rank >= HandRank.FULL_HOUSE:
            # strong enough to raise even into danger
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if rank >= RAISE_RANK and raise_action:
            if danger < 60:
                return "raise", raise_action["amount"]["min"]
            # strong hand but high danger — slow-play
            return call_action["action"], call_cost

        if rank >= HandRank.HIGH_CARD:
            if danger < DANGER_THRESHOLD:
                return call_action["action"], call_cost
            if call_cost == 0:
                return call_action["action"], 0
            return fold_action["action"], 0

        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
