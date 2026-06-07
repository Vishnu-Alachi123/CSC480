"""
agent/mc_simple_agent.py — MCSimpleAgent
Monte Carlo simulation of own hand strength only — no opponent hands dealt.

Runs random board completions and measures P(own rank >= TWO_PAIR) as a
proxy for hand quality. Ignores what opponents might hold: a limitation
that MCOppAgent fixes by explicitly dealing opponent cards.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import random
from collections import defaultdict
from itertools import combinations
from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
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


def _mc_own_hand(hole_cards: list, community_cards: list, deck_cards: list,
                 num_sims: int = 200) -> tuple:
    """
    Simulate random board completions. Return:
      (p_good, p_pair) where p_good = P(rank >= TWO_PAIR), p_pair = P(rank >= PAIR)
    No opponent cards dealt.
    """
    board_needed = 5 - len(community_cards)
    good = 0
    has_pair = 0

    for _ in range(num_sims):
        sample = list(deck_cards)
        random.shuffle(sample)
        board = list(community_cards) + sample[:board_needed]
        all_cards = hole_cards + board
        if len(all_cards) >= 5:
            rank = max(evaluate(list(c)) for c in combinations(all_cards, 5))
        else:
            rank = HandRank.HIGH_CARD
        if rank >= HandRank.TWO_PAIR:
            good += 1
        if rank >= HandRank.PAIR:
            has_pair += 1

    return good / num_sims, has_pair / num_sims


# Raise when TWO_PAIR+ happens ≥ 45% of runouts
RAISE_GOOD_PCT = 0.45
# Call when at least a PAIR happens ≥ 60% of runouts
CALL_PAIR_PCT  = 0.60


class MCSimpleAgent(BasePokerPlayer):
    """
    MC for own hand only. Decisions based on how often we'd end up with
    a strong hand after random board runouts — opponents not modelled.
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

        p_good, p_pair = _mc_own_hand(parsed_hole, parsed_community, deck.cards)

        if p_good >= RAISE_GOOD_PCT and raise_action:
            return "raise", raise_action["amount"]["min"]
        if p_pair >= CALL_PAIR_PCT:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
