"""
agent/mc_tracker_agent.py — MCTrackerAgent
Full MC win-probability + OpponentTracker behavioral adjustment.

Combines MCOppAgent's win_pct signal with opponent behavioral history:
raises/call thresholds tighten against aggressive opponents and relax
against passive ones. No danger score (that's MCDangerAgent).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
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


RAISE_WIN_PCT = 60
CALL_WIN_PCT  = 40


class MCTrackerAgent(BasePokerPlayer):
    """
    MC + OpponentTracker: adjusts raise/call thresholds based on how
    aggressively opponents have been playing this session.
    """
    verbose = True

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
        win_pct = win_prob * 100

        opp_uuids = [s.get("uuid", "") for s in opp_seats]
        opp_aggression  = max((self.tracker.aggression_score(u) for u in opp_uuids), default=1.0)
        opp_threatening = any(self.tracker.is_showing_strength_this_hand(u) for u in opp_uuids)

        eff_raise = RAISE_WIN_PCT
        eff_call  = CALL_WIN_PCT

        if opp_threatening:
            eff_raise += 15
            eff_call  += 10
        elif opp_aggression > 1.5:
            eff_raise += 10
            eff_call  +=  5
        elif opp_aggression < 0.5:
            eff_raise = max(50, RAISE_WIN_PCT - 10)
            eff_call  = max(30, CALL_WIN_PCT  - 10)

        if win_pct >= eff_raise and raise_action:
            return "raise", raise_action["amount"]["min"]
        if win_pct >= eff_call:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_street_start_message(self, s, rs): pass
