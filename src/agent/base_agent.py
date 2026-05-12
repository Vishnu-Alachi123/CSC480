"""
agent/base_agent.py
-------------------
A simple rule-based poker agent that uses src.core.hand_evaluator
to make decisions based on hand strength.

Decision logic:
    - Evaluate the best 5-card hand from hole cards + community cards
    - Map the hand rank to a threshold:
        strong hand  (Full House+)  → raise
        decent hand  (Straight+)    → call
        weak hand    (Two Pair-)    → fold if it costs chips, else check
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from itertools import combinations
from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank

# ── Card string parser (same as play.py) ─────────────────────────────────────

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


def best_hand_rank(hole_cards: list, community_cards: list) -> HandRank:
    """
    Try every 5-card combination from hole + community cards and
    return the best HandRank using src.core.hand_evaluator.evaluate().
    Falls back to HIGH_CARD if fewer than 5 cards are available.
    """
    all_cards = [_parse(c) for c in hole_cards + community_cards]

    if len(all_cards) < 5:
        # Preflop / early streets — not enough cards to evaluate properly.
        # Do a rough preflop estimate based on hole card ranks instead.
        return _preflop_estimate(hole_cards)

    best = HandRank.HIGH_CARD
    for combo in combinations(all_cards, 5):
        result = evaluate(list(combo))
        if result > best:
            best = result
    return best


def _preflop_estimate(hole_cards: list) -> HandRank:
    """
    Rough preflop hand quality without community cards.
    Pocket pair → PAIR, high cards (A/K/Q) → HIGH_CARD with a bump, Same suit → FLUSH
    everything else → HIGH_CARD.
    """
    if len(hole_cards) < 2:
        return HandRank.HIGH_CARD

    r1 = _RANK_MAP[hole_cards[0][1].upper()]
    r2 = _RANK_MAP[hole_cards[1][1].upper()]

    if r1 == r2:
        return HandRank.PAIR   # pocket pair

    # Treat high-card hands (A, K, Q in hole) as slightly above HIGH_CARD
    high_ranks = {Rank.ACE, Rank.KING, Rank.QUEEN}
    if r1 in high_ranks or r2 in high_ranks:
        return HandRank.HIGH_CARD  # still HIGH_CARD but caller can check rank

    if _SUIT_MAP[hole_cards[0][0]] == _SUIT_MAP[hole_cards[1][0]]:
        return HandRank.FLUSH

    return HandRank.HIGH_CARD


# ── Decision thresholds ───────────────────────────────────────────────────────
#
# You can tune these to change how aggressive the agent is.
#
#   RAISE_THRESHOLD  — hand rank at or above this → raise
#   CALL_THRESHOLD   — hand rank at or above this → call
#   below CALL_THRESHOLD → fold (or check if free)

RAISE_THRESHOLD = HandRank.FULL_HOUSE      # Full House, Four of a Kind, SF, RF
CALL_THRESHOLD  = HandRank.STRAIGHT        # Straight, Flush, Full House, ...


class SimpleAgent(BasePokerPlayer):
    """
    Rule-based agent that uses src.core.hand_evaluator to decide actions.

    Preflop:  plays pocket pairs and high cards, folds junk
    Postflop: raises strong hands, calls decent hands, folds weak ones
    """

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        rank      = best_hand_rank(hole_card, community)

        # valid_actions is always [fold, call, raise]
        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None

        call_cost = call_action["amount"]

        # ── Decision ──────────────────────────────────────────────────────────
        if rank >= RAISE_THRESHOLD and raise_action:
            # Strong hand — raise the minimum
            raise_min = raise_action["amount"]["min"]
            return "raise", raise_min

        elif rank >= CALL_THRESHOLD:
            # Decent hand — call (or check if free)
            return call_action["action"], call_cost

        else:
            # Weak hand
            if call_cost == 0:
                # Free to check — always take it
                return call_action["action"], 0
            else:
                # Costs chips — fold
                return fold_action["action"], 0

    # ── Lifecycle (nothing needed for a rule-based agent) ─────────────────────
    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
