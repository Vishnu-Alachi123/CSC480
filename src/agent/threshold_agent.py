"""
agent/threshold_agent.py — ThresholdAgent
Pure hand-rank thresholds, no Monte Carlo simulation, no opponent tracking.

This is the baseline: decisions come entirely from evaluating the best
5-card hand and comparing it against fixed cutoffs.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from itertools import combinations
from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank

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


def _best_rank(hole_cards: list, community_cards: list) -> HandRank:
    all_cards = [_parse(c) for c in hole_cards + community_cards]
    if len(all_cards) < 2:
        return HandRank.HIGH_CARD
    if len(all_cards) < 5:
        ranks = [c.rank for c in all_cards]
        return HandRank.PAIR if ranks[0] == ranks[1] else HandRank.HIGH_CARD
    return max(evaluate(list(combo)) for combo in combinations(all_cards, 5))


class ThresholdAgent(BasePokerPlayer):
    """
    Baseline agent: hand rank thresholds, no simulation.
      FULL_HOUSE+         → raise
      STRAIGHT–FLUSH      → call
      TWO_PAIR–THREE_OAK  → call if free, else fold
      PAIR or lower       → check or fold
    """

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost    = call_action["amount"]

        rank = _best_rank(hole_card, community)

        if rank >= HandRank.FULL_HOUSE:
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if rank >= HandRank.STRAIGHT:
            return call_action["action"], call_cost

        if rank >= HandRank.TWO_PAIR:
            if call_cost == 0:
                return call_action["action"], 0
            return fold_action["action"], 0

        # PAIR or worse
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
