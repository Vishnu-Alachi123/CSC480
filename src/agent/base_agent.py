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

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.opponent_win_probability.graph import plot_simulation_result

# Card string parser (same as play.py)

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

# alias so both names work
_parse_card = _parse


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


# Decision thresholds 
#
# You can tune these to change how aggressive the agent is.
#
#   RAISE_THRESHOLD  — hand rank at or above this → raise
#   CALL_THRESHOLD   — hand rank at or above this → call
#   below CALL_THRESHOLD → fold (or check if free)


def opponent_danger(sim_result: float):
    # sim_result is now a win probability (0.0 to 1.0)
    # convert to a 0-100 danger score: higher opponent win prob = more danger
    return (1 - sim_result) * 100

RAISE_THRESHOLD  = HandRank.TWO_PAIR       # raise with two pair or better
CALL_THRESHOLD   = HandRank.PAIR           # call with any pair or better
DANGER_THRESHOLD = 70                      # tolerate up to 70/100 danger before folding

class SimpleAgent(BasePokerPlayer):
    """
    Rule-based agent that uses src.core.hand_evaluator to decide actions.

    Preflop:  plays pocket pairs and high cards, folds junk
    Postflop: raises strong hands, calls decent hands, folds weak ones
    """

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        seats     = round_state.get("seats", [])
        rank      = best_hand_rank(hole_card, community)

        # valid_actions is always [fold, call, raise]
        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None

        call_cost = call_action["amount"]

        # parse strings -> Card objects
        parsed_hole      = [_parse_card(c) for c in hole_card]
        parsed_community = [_parse_card(c) for c in community]

        # build unseen deck 
        deck = Deck()
        deck.remove(parsed_hole + parsed_community)

        # count active opponents 
        num_opp = len([
            s for s in seats
            if s.get("name") != getattr(self, "_name", "")
            and s.get("state") == "participating"
        ])

        # run Monte Carlo simulation
        street = round_state.get("street", "preflop")
        round_num = round_state.get("round_count", 0)
        sim_result, player_rank, opp_hand_counts = monte_carlo_simulation(
            deck            = deck,
            hole_cards      = parsed_hole,
            community_cards = parsed_community,
            num_opp         = max(num_opp, 1),
            num_sims        = 500,   # keep fast; raise for more accuracy
        )

        danger = opponent_danger(sim_result)

        # Determine action and build a human-readable reason before acting
        if rank >= RAISE_THRESHOLD and raise_action:
            if danger < 60:
                action, amount = "raise", raise_action["amount"]["min"]
                reason = (f"Strong hand ({rank.name.replace('_',' ')}) with low danger "
                          f"({danger:.0f}/100). Raising to build pot.")
            else:
                action, amount = call_action["action"], call_cost
                reason = (f"Strong hand ({rank.name.replace('_',' ')}) but high danger "
                          f"({danger:.0f}/100). Slow-playing cautiously.")
        elif rank >= CALL_THRESHOLD:
            if danger < DANGER_THRESHOLD:
                action, amount = call_action["action"], call_cost
                reason = (f"Decent hand ({rank.name.replace('_',' ')}) with acceptable danger "
                          f"({danger:.0f}/100). Calling.")
            else:
                if call_cost == 0:
                    action, amount = call_action["action"], 0
                    reason = (f"Decent hand ({rank.name.replace('_',' ')}) but high danger "
                              f"({danger:.0f}/100). Checking for free.")
                else:
                    action, amount = fold_action["action"], 0
                    reason = (f"Decent hand ({rank.name.replace('_',' ')}) but danger too high "
                              f"({danger:.0f}/100) to justify call cost of {call_cost}. Folding.")
        else:
            if call_cost == 0:
                action, amount = call_action["action"], 0
                reason = (f"Weak hand ({rank.name.replace('_',' ')}). Checking for free.")
            else:
                action, amount = fold_action["action"], 0
                reason = (f"Weak hand ({rank.name.replace('_',' ')}) with call cost {call_cost}. Folding.")

        # Find agent's stack
        agent_stack = next(
            (s.get("stack", 0) for s in seats if s.get("name") == getattr(self, "_name", "")),
            0
        )

        # Print summary
        print(f"\n{'='*50}")
        print(f"[Round {round_num} | {street.upper()}]")
        print(f"  Hole cards    : {hole_card}")
        print(f"  Best hand     : {rank.name.replace('_', ' ')}")
        print(f"  Win prob      : {sim_result * 100:.1f}%")
        print(f"  Danger score  : {danger:.0f}/100")
        print(f"  Agent stack   : ${agent_stack:,}")
        print(f"  Decision      : {action.upper()}")
        print(f"  Reason        : {reason}")
        print(f"{'='*50}\n")

        # Plot and pause for analysis
        plot_simulation_result(
            opp_hand_counts  = opp_hand_counts,
            player_rank      = player_rank,
            win_probability  = sim_result,
            street           = street,
            round_num        = round_num,
            hole_cards       = hole_card,
            decision         = action,
            decision_reason  = reason,
            agent_stack      = agent_stack,
        )

        input("  ↵  Press Enter to continue...\n")

        return action, amount

    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass