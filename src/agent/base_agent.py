"""
agent/base_agent.py
Decision logic: run Monte Carlo to get win probability, then:
  win_pct >= RAISE_WIN_PCT  →  raise
  win_pct >= CALL_WIN_PCT   →  call (or check)
  win_pct <  CALL_WIN_PCT   →  fold (or check for free)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.opponent_win_probability.graph import plot_simulation_result

DEBUG = False  # set True to print per-decision diagnostics

RAISE_WIN_PCT = 60   # raise when winning > 60% of simulations
CALL_WIN_PCT  = 40   # call  when winning > 40%; fold below (unless free)

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


def check_pot_odds(call_amount: int, pot: int, win_percentage: float, street: str) -> bool:
    if street.upper() == "PREFLOP":
        return True
    if pot + call_amount == 0:
        return True
    pot_equity = (100 * call_amount) / (pot + call_amount)
    return win_percentage > pot_equity


class SimpleAgent(BasePokerPlayer):
    """
    Monte Carlo-based poker agent.

    Set SimpleAgent.verbose = False before benchmarking to suppress
    per-decision prints and matplotlib plots.
    """
    verbose = True

    def __init__(self):
        super().__init__()
        self._my_name = ""

    def receive_game_start_message(self, game_info):
        # pypokerengine sets self.name when the player is registered
        self._my_name = getattr(self, "name", "")

    def declare_action(self, valid_actions, hole_card, round_state):
        community = round_state.get("community_card", [])
        seats     = round_state.get("seats", [])
        street    = round_state.get("street", "preflop")
        round_num = round_state.get("round_count", 0)

        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost    = call_action["amount"]

        parsed_hole      = [_parse(c) for c in hole_card]
        parsed_community = [_parse(c) for c in community]

        deck = Deck()
        deck.remove(parsed_hole + parsed_community)

        # exclude self and eliminated players
        num_opp = len([
            s for s in seats
            if s.get("name") != self._my_name
            and s.get("state") == "participating"
        ])

        sim_result, current_rank, projected_rank, opp_hand_counts, player_hand_counts = monte_carlo_simulation(
            deck            = deck,
            hole_cards      = parsed_hole,
            community_cards = parsed_community,
            num_opp         = max(num_opp, 1),
            num_sims        = 200,
        )

        win_pct = sim_result * 100
        pot     = round_state.get("pot", {}).get("main", {}).get("amount", 0)

        if win_pct >= RAISE_WIN_PCT and raise_action:
            action, amount = "raise", raise_action["amount"]["min"]
            reason = f"Win prob {win_pct:.1f}% — raising for value."

        elif win_pct >= CALL_WIN_PCT or check_pot_odds(call_cost, pot, win_pct, street):
            action, amount = call_action["action"], call_cost
            reason = f"Win prob {win_pct:.1f}% — calling."

        else:
            if call_cost == 0:
                action, amount = call_action["action"], 0
                reason = f"Win prob {win_pct:.1f}% — checking for free."
            else:
                action, amount = fold_action["action"], 0
                reason = f"Win prob {win_pct:.1f}% — folding, not worth the cost."

        if DEBUG:
            print(f"[DEBUG] name={self._my_name!r}, seats={[s['name'] for s in seats]}, "
                  f"num_opp={num_opp}, sim_result={sim_result:.3f}, action={action}")

        if self.__class__.verbose:
            agent_stack = next(
                (s.get("stack", 0) for s in seats if s.get("name") == self._my_name),
                0
            )
            print(f"\n{'='*50}")
            print(f"[Round {round_num} | {street.upper()}]")
            print(f"  Hole cards      : {hole_card}")
            print(f"  Current hand    : {current_rank.name.replace('_', ' ')}")
            print(f"  Projected hand  : {projected_rank.name.replace('_', ' ')}")
            print(f"  Win prob        : {win_pct:.1f}%")
            print(f"  Num opponents   : {num_opp}")
            print(f"  Agent stack     : ${agent_stack:,}")
            print(f"  Decision        : {action.upper()}")
            print(f"  Reason          : {reason}")
            print(f"{'='*50}\n")

            plot_simulation_result(
                opp_hand_counts    = opp_hand_counts,
                player_rank        = projected_rank,
                win_probability    = sim_result,
                street             = street,
                round_num          = round_num,
                hole_cards         = hole_card,
                decision           = action,
                decision_reason    = reason,
                agent_stack        = agent_stack,
                current_rank       = current_rank,
                player_hand_counts = player_hand_counts,
            )

        return action, amount

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
