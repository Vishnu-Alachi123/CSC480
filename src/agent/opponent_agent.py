"""
agent/opponent_agent.py — OpponentAgent
Hand-rank evaluation + OpponentTracker, no Monte Carlo.

Decision logic:
  Evaluate best current hand rank, then adjust conservatism
  based on how aggressively opponents are playing this session.

  Strong hand (FULL_HOUSE+)        → always raise
  Good hand (STRAIGHT–FOUR_OF_A_KIND):
    opp threatening this hand      → call (don't re-raise into strength)
    otherwise                      → raise
  Medium hand (TWO_PAIR–FLUSH):
    opp threatening this hand      → fold/check
    opp passive (aggression < 0.8) → call
    otherwise                      → fold/check
  Weak hand (PAIR or less):
    free check                     → check
    otherwise                      → fold
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from itertools import combinations
from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank
from src.agent.opponent_tracker import OpponentTracker

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
        # preflop / early street — evaluate what we have
        ranks = [c.rank for c in all_cards]
        if ranks[0] == ranks[1]:
            return HandRank.PAIR
        return HandRank.HIGH_CARD
    return max(evaluate(list(combo)) for combo in combinations(all_cards, 5))


class OpponentAgent(BasePokerPlayer):
    """
    Opponent-tracking agent: adjusts play style based on how aggressively
    each opponent has been playing, without running Monte Carlo simulations.
    """

    def __init__(self):
        super().__init__()
        self._my_name = ""
        self.tracker  = OpponentTracker()

    def receive_game_start_message(self, game_info):
        self._my_name = getattr(self, "name", "")

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.tracker.new_round()

    def receive_game_update_message(self, action, round_state):
        self.tracker.record_action(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        player_uuids = [s["uuid"] for s in round_state.get("seats", []) if "uuid" in s]
        self.tracker.finish_round(player_uuids)

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        seats     = round_state.get("seats", [])

        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost    = call_action["amount"]

        hand_rank = _best_rank(hole_card, community)

        # gather opponent info from tracker
        opp_uuids = [
            s.get("uuid", "")
            for s in seats
            if s.get("name") != self._my_name
            and s.get("state") == "participating"
        ]
        opp_aggression  = max((self.tracker.aggression_score(u) for u in opp_uuids), default=1.0)
        opp_threatening = any(self.tracker.is_showing_strength_this_hand(u) for u in opp_uuids)

        # ── Decision by hand strength + opponent context ──────────────────────
        if hand_rank >= HandRank.FULL_HOUSE:
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if hand_rank >= HandRank.STRAIGHT:
            if opp_threatening:
                # someone is already representing a strong hand — just call
                return call_action["action"], call_cost
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if hand_rank >= HandRank.TWO_PAIR:
            if opp_threatening:
                # back off when facing aggression with a medium hand
                if call_cost == 0:
                    return call_action["action"], 0
                return fold_action["action"], 0
            if opp_aggression < 0.8:
                # passive table — call medium hands
                return call_action["action"], call_cost
            if call_cost == 0:
                return call_action["action"], 0
            return fold_action["action"], 0

        # PAIR or HIGH_CARD — only play for free
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_street_start_message(self, s, rs): pass
