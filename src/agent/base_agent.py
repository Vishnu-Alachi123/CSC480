"""
agent/base_agent.py
A simple rule-based poker agent that uses hand_evaluator
to make decisions based on hand strength.

Decision logic:
    - Evaluate the best 5-card hand from hole cards + community cards
    - Map the hand rank to a threshold:
        strong hand (Full House+) -> raise
        decent hand (Straight+) -> call
        weak hand (Two Pair-) -> fold if it costs chips, else check
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from itertools import combinations
from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.opponent_win_probability.graph import plot_simulation_result


# Card string parser

_SUIT_MAP = {
    'S': Suit.SPADES, 'H': Suit.HEARTS,
    'D': Suit.DIAMONDS, 'C': Suit.CLUBS,
}

_RANK_MAP = {
    '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE,
    'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 'K': Rank.KING,
    'A': Rank.ACE,
}

def _parse(card_str: str) -> Card:
    return Card(_RANK_MAP[card_str[1].upper()], _SUIT_MAP[card_str[0].upper()])

_parse_card = _parse


def best_hand_rank(hole_cards: list, community_cards: list) -> HandRank:
    all_cards = [_parse(c) for c in hole_cards + community_cards]

    if len(all_cards) < 5:
        return _preflop_estimate(hole_cards)

    best = HandRank.HIGH_CARD
    for combo in combinations(all_cards, 5):
        result = evaluate(list(combo))
        if result > best:
            best = result
    return best


def _preflop_estimate(hole_cards: list) -> HandRank:
    if len(hole_cards) < 2:
        return HandRank.HIGH_CARD

    r1 = _RANK_MAP[hole_cards[0][1].upper()]
    r2 = _RANK_MAP[hole_cards[1][1].upper()]

    if r1 == r2:
        return HandRank.PAIR

    high_ranks = {Rank.ACE, Rank.KING, Rank.QUEEN}
    if r1 in high_ranks or r2 in high_ranks:
        return HandRank.HIGH_CARD

    if _SUIT_MAP[hole_cards[0][0]] == _SUIT_MAP[hole_cards[1][0]]:
        return HandRank.FLUSH

    return HandRank.HIGH_CARD


def opponent_danger(sim_result: float):
    return (1 - sim_result) * 100


RAISE_THRESHOLD  = HandRank.TWO_PAIR
CALL_THRESHOLD   = HandRank.HIGH_CARD
DANGER_THRESHOLD = 70


class SimpleAgent(BasePokerPlayer):

    def __init__(self):
        super().__init__()
        self.decision_history = []

    def declare_action(self, valid_actions, hole_card, round_state):

        community = round_state.get("community_card", [])
        seats = round_state.get("seats", [])
        rank = best_hand_rank(hole_card, community)

        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None

        call_cost = call_action["amount"]

        parsed_hole      = [_parse_card(c) for c in hole_card]
        parsed_community = [_parse_card(c) for c in community]

        deck = Deck()
        deck.remove(parsed_hole + parsed_community)

        num_opp = len([
            s for s in seats
            if s.get("name") != getattr(self, "_name", "")
            and s.get("state") == "participating"
        ])

        street = round_state.get("street", "preflop")
        round_num = round_state.get("round_count", 0)

        sim_result, current_rank, projected_rank, opp_hand_counts, player_hand_counts = monte_carlo_simulation(
            deck=deck,
            hole_cards=parsed_hole,
            community_cards=parsed_community,
            num_opp=max(num_opp, 1),
            num_sims=500,
        )

        danger = opponent_danger(sim_result)

        # pot tracking
        pot = round_state.get("pot", {}).get("main", {}).get("amount", 0)

        # simple EV 
        ev_proxy = (sim_result * pot) - ((1 - sim_result) * call_cost)

        # DECISION LOGIC
        if rank >= RAISE_THRESHOLD and raise_action:
            if danger < 60:
                action, amount = "raise", raise_action["amount"]["min"]
                reason = f"Strong hand + low danger ({danger:.0f})"
            else:
                action, amount = call_action["action"], call_cost
                reason = f"Strong hand but high danger ({danger:.0f})"

        elif rank >= CALL_THRESHOLD:
            if danger < DANGER_THRESHOLD:
                action, amount = call_action["action"], call_cost
                reason = f"Decent hand, ok danger ({danger:.0f})"
            else:
                if call_cost == 0:
                    action, amount = call_action["action"], 0
                    reason = "Free check"
                else:
                    action, amount = fold_action["action"], 0
                    reason = "Too risky → fold"

        else:
            if call_cost == 0:
                action, amount = call_action["action"], 0
                reason = "Weak hand but free check"
            else:
                action, amount = fold_action["action"], 0
                reason = "Weak hand → fold"

        agent_stack = next(
            (s.get("stack", 0) for s in seats if s.get("name") == getattr(self, "_name", "")),
            0
        )

        # STORE LEARNING DATA
        self.decision_history.append({
            "round": round_num,
            "ev": ev_proxy,
            "danger": danger,
            "action": action,
            "sim_result": sim_result
        })

        print(f"\n{'='*50}")
        print(f"[Round {round_num} | {street.upper()}]")
        print(f"  Win prob   : {sim_result * 100:.1f}%")
        print(f"  Pot        : {pot}")
        print(f"  EV proxy   : {ev_proxy:.2f}")
        print(f"  Danger     : {danger:.0f}/100")
        print(f"  Decision   : {action.upper()}")
        print(f"  Reason     : {reason}")
        print(f"{'='*50}\n")

        plot_simulation_result(
            opp_hand_counts=opp_hand_counts,
            player_rank=projected_rank,
            win_probability=sim_result,
            street=street,
            round_num=round_num,
            hole_cards=hole_card,
            decision=action,
            decision_reason=reason,
            agent_stack=agent_stack,
            current_rank=current_rank,
            player_hand_counts=player_hand_counts,
        )

        debug = False
        if debug:
            input("Press Enter to continue...\n")

        return action, amount

    def receive_round_result_message(self, w, h, rs):

        if not self.decision_history:
            return

        last = self.decision_history.pop()

        won = any(
            winner.get("name") == getattr(self, "_name", "")
            for winner in w
        )

        expected_win = last["sim_result"] > 0.5
        mismatch = expected_win != won

        print("\n" + "="*50)
        print("FEEDBACK LOOP")
        print(f"Action   : {last['action']}")
        print(f"EV proxy : {last['ev']:.2f}")
        print(f"Outcome  : {'WIN' if won else 'LOSS'}")
        print(f"Match    : {'MISMATCH' if mismatch else 'OK'}")
        print("="*50 + "\n")

    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
