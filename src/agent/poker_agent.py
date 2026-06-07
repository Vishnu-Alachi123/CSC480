"""
agent/poker_agent.py — PokerAgent
The complete agent: kicker-aware MC + OpponentTracker + danger score.

Feature stack:
  1. monte_carlo_best_hand()  — kicker-aware win probability
  2. OpponentTracker          — behavioral history tightens/loosens thresholds
  3. Danger score             — pot-success danger modifier on medium hands

Decision logic:
  Base:     raise >= RAISE_WIN_PCT,  call >= CALL_WIN_PCT
  Tracker:  +15/+10 vs threatening opponents, +10/+5 vs aggressive,
            -10/-10 vs passive
  Danger:   medium hands fold when danger > DANGER_THRESHOLD unless free
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer

from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank, evaluate
from src.core.best_hand_probability.mc_besthand import monte_carlo_best_hand
from src.core.opponent_win_probability.graph import plot_simulation_result
from src.agent.opponent_tracker import OpponentTracker
from itertools import combinations

DEBUG = False

RAISE_WIN_PCT    = 60
CALL_WIN_PCT     = 40
DANGER_THRESHOLD = 65   # fold medium hands when opponent danger exceeds this

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


class PokerAgent(BasePokerPlayer):
    """
    Full-featured agent combining:
      - Kicker-aware Monte Carlo (mc_besthand) for accurate win probability
      - OpponentTracker behavioral adjustments
      - Danger score to fold medium hands against strong-looking opponents
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
        street    = round_state.get("street", "preflop")
        round_num = round_state.get("round_count", 0)

        fold_action  = valid_actions[0]
        call_action  = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost    = call_action["amount"]

        parsed_hole      = [_parse(c) for c in hole_card]
        parsed_community = [_parse(c) for c in community]

        opp_seats = [
            s for s in seats
            if s.get("name") != self._my_name
            and s.get("state") == "participating"
        ]
        num_opp = max(len(opp_seats), 1)

        deck = Deck()
        deck.remove(parsed_hole + parsed_community)

        # ── Kicker-aware MC win probability ───────────────────────────────────
        win_prob = monte_carlo_best_hand(
            hole_cards      = parsed_hole,
            community_cards = parsed_community,
            num_opponents   = num_opp,
            num_iterations  = 150,
            remaining_cards = deck.cards,
        )
        win_pct = win_prob * 100
        danger  = (1.0 - win_prob) * 100
        rank    = _best_rank(parsed_hole, parsed_community)

        # ── OpponentTracker adjustment ────────────────────────────────────────
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

        # ── Decision with danger override ─────────────────────────────────────
        if rank >= HandRank.FULL_HOUSE:
            # monster hand: raise regardless of danger
            if raise_action and win_pct >= eff_raise:
                action, amount = "raise", raise_action["amount"]["min"]
            else:
                action, amount = call_action["action"], call_cost
            reason = f"Monster hand ({rank.name}) — danger {danger:.0f} ignored."

        elif win_pct >= eff_raise and raise_action:
            if danger < 60:
                action, amount = "raise", raise_action["amount"]["min"]
                reason = f"Win {win_pct:.1f}% ≥ {eff_raise:.0f}%, danger {danger:.0f} — raising."
            else:
                action, amount = call_action["action"], call_cost
                reason = f"Win {win_pct:.1f}% good but danger {danger:.0f} high — slow-play."

        elif win_pct >= eff_call:
            if danger > DANGER_THRESHOLD and rank < HandRank.TWO_PAIR:
                # danger score override: fold medium hands into dangerous boards
                if call_cost == 0:
                    action, amount = call_action["action"], 0
                    reason = f"Win {win_pct:.1f}% ok but danger {danger:.0f} > {DANGER_THRESHOLD} — checking free."
                else:
                    action, amount = fold_action["action"], 0
                    reason = f"Win {win_pct:.1f}% ok but danger {danger:.0f} > {DANGER_THRESHOLD} — folding."
            else:
                action, amount = call_action["action"], call_cost
                reason = f"Win {win_pct:.1f}% ≥ {eff_call:.0f}% — calling."

        else:
            if call_cost == 0:
                action, amount = call_action["action"], 0
                reason = f"Win {win_pct:.1f}% low — checking for free."
            else:
                action, amount = fold_action["action"], 0
                reason = f"Win {win_pct:.1f}% low — folding."

        if DEBUG:
            print(f"[DEBUG PokerAgent] {self._my_name!r} win={win_pct:.1f}% "
                  f"danger={danger:.0f} agg={opp_aggression:.2f} "
                  f"threat={opp_threatening} → {action}")

        if self.__class__.verbose:
            agent_stack = next(
                (s.get("stack", 0) for s in seats if s.get("name") == self._my_name), 0
            )
            pot_size  = round_state.get("pot", {}).get("main", {}).get("amount", 0)

            # build opponent tracker info for graph: (display_name, aggression, threatening)
            opp_tracker_info = []
            for s in opp_seats:
                uuid = s.get("uuid", "")
                name = s.get("name", uuid[:8])
                agg  = self.tracker.aggression_score(uuid)
                thr  = self.tracker.is_showing_strength_this_hand(uuid)
                opp_tracker_info.append((name, agg, thr))

            plot_simulation_result(
                opp_hand_counts    = {},          # mc_besthand doesn't track opp distributions
                player_rank        = rank,
                win_probability    = win_prob,
                street             = street,
                round_num          = round_num,
                hole_cards         = hole_card,
                decision           = action,
                decision_reason    = reason,
                agent_stack        = agent_stack,
                current_rank       = rank,
                player_hand_counts = {},
                opp_tracker_info   = opp_tracker_info,
                pot_size           = pot_size,
                call_cost          = call_cost,
            )

        return action, amount

    def receive_street_start_message(self, s, rs): pass
