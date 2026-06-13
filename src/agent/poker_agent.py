from itertools import combinations
from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank, evaluate
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.opponent_win_probability.graph import plot_simulation_result
from src.core.opponent_tracker import OpponentTracker
from src.core.pot_tracker import PotTracker

# raise/call cutoffs tuned for heads-up, adaptive_thresholds scales them down for bigger games
BASE_RAISE_THRESHOLD = 62
BASE_CALL_THRESHOLD = 38

# preflop cutoffs based on heads-up MC equity
PREFLOP_RAISE_STRONG = 72   # JJ+ (~75% equity heads-up)
PREFLOP_RAISE_MED = 60      # AK, AQ, 99, 88, suited broadways (~60-67%)
PREFLOP_MIN_CALL = 48       # anything with above-average equity
PREFLOP_MAX_LIMP_BB = 2.5   # fold speculative hands if price is more than 2.5x BB

SUIT_MAP = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
RANK_MAP = {
    '2': Rank.TWO,  '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX,  '7': Rank.SEVEN, '8': Rank.EIGHT,'9': Rank.NINE,
    'T': Rank.TEN,  'J': Rank.JACK,  'Q': Rank.QUEEN,'K': Rank.KING, 'A': Rank.ACE,
}

def parse_card(card_str):
    return Card(RANK_MAP[card_str[1].upper()], SUIT_MAP[card_str[0].upper()])


def preflop_strength(hole_card):
    # runs a heads-up MC sim with no board to get actual equity for the starting hand.
    # we use num_opp=1 here specifically to avoid the multiway noise. the adaptive
    # thresholds handle adjusting for more players at the table.
    if len(hole_card) < 2:
        return 0
    hole = [parse_card(c) for c in hole_card]
    deck = Deck()
    deck.remove(hole)
    win_prob, *_ = monte_carlo_simulation(
        deck=deck, hole_cards=hole, community_cards=[], num_opp=1, num_sims=500
    )
    return win_prob * 100


def adaptive_thresholds(num_opponents):
    # with more opponents your expected win rate just drops, so we scale thresholds down
    # by 3% per extra player. fixed thresholds make the agent way too tight in bigger games.
    drop = (num_opponents - 1) * 3
    raise_threshold = max(44, BASE_RAISE_THRESHOLD - drop)
    call_threshold = max(18, BASE_CALL_THRESHOLD - drop)
    return raise_threshold, call_threshold


def sizing_for_raise(win_pct, pot_size, raise_action, is_preflop, small_blind):
    # raise bigger when we're ahead so we build the pot with strong hands
    # preflop just do a standard 3x open, postflop scale from half pot up to full
    # pot depending on how good our win probability looks.
    min_raise = raise_action["amount"]["min"]
    max_raise = raise_action["amount"]["max"]

    if is_preflop:
        target = small_blind * 6
    elif win_pct >= 82:
        target = max(pot_size, min_raise)
    elif win_pct >= 68:
        target = max(pot_size * 2 // 3, min_raise)
    elif win_pct >= 55:
        target = max(pot_size // 2, min_raise)
    else:
        return min_raise

    return max(min_raise, min(target, max_raise))


class PokerAgent(BasePokerPlayer):
    # the full agent. preflop chart to avoid the MC noise before the flop, then
    # actual MC sims postflop. layers in pot odds, opponent tracking, and dynamic
    # raise sizing all together.
    verbose = True

    def __init__(self):
        super().__init__()
        self.my_name = ""
        self.tracker = OpponentTracker()
        self.pot_stats = PotTracker()
        self.raised_preflop = False

    def receive_game_start_message(self, game_info):
        self.my_name = next((s["name"] for s in game_info.get("seats", []) if s.get("uuid") == self.uuid), "")

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.tracker.new_round()
        self.raised_preflop = False

    def receive_game_update_message(self, action, round_state):
        self.tracker.record_action(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        all_uuids = [s["uuid"] for s in round_state.get("seats", []) if "uuid" in s]
        self.tracker.finish_round(all_uuids)

    def declare_action(self, valid_actions, hole_card, round_state):
        community_cards = round_state.get("community_card", [])
        seats = round_state.get("seats", [])
        street = round_state.get("street", "preflop").upper()
        round_num = round_state.get("round_count", 0)
        small_blind = round_state.get("small_blind_amount", 10)

        fold_action = valid_actions[0]
        call_action = valid_actions[1]
        raise_action = (valid_actions[2] if len(valid_actions) > 2 and valid_actions[2]["amount"]["min"] > 0 else None)
        call_cost = call_action["amount"]

        active_opponents = [s for s in seats if s.get("name") != self.my_name and s.get("state") == "participating"]
        num_opponents = max(len(active_opponents), 1)

        opponent_uuids = [s.get("uuid", "") for s in active_opponents]
        opponent_is_scary = any(self.tracker.is_showing_strength_this_hand(u) for u in opponent_uuids)

        pot_size = round_state.get("pot", {}).get("main", {}).get("amount", 0)
        self.pot_stats.record_pot(pot_size)

        # use the preflop chart here since MC gets noisy with multiple opponents
        if street == "PREFLOP":
            action, amount, reason = self.decide_preflop(
                hole_card, fold_action, call_action, raise_action,
                call_cost, num_opponents, small_blind
            )
            win_prob = preflop_strength(hole_card) / 100.0
            current_rank = HandRank.HIGH_CARD
            projected_rank = HandRank.HIGH_CARD
            opp_hand_counts = {}
            player_hand_counts = {}

        # postflop we run the full MC simulation
        else:
            hole = [parse_card(c) for c in hole_card]
            board = [parse_card(c) for c in community_cards]
            deck = Deck()
            deck.remove(hole + board)

            (win_prob, current_rank, projected_rank,
             opp_hand_counts, player_hand_counts) = monte_carlo_simulation(
                deck=deck,
                hole_cards=hole,
                community_cards=board,
                num_opp=num_opponents,
                num_sims=200,
            )

            action, amount, reason = self.decide_postflop(
                win_prob, current_rank,
                fold_action, call_action, raise_action,
                call_cost, pot_size, num_opponents,
                opponent_is_scary, street, small_blind,
            )

        win_pct = win_prob * 100

        if self.__class__.verbose:
            agent_stack = next((s.get("stack", 0) for s in seats if s.get("name") == self.my_name), 0)
            opp_tracker_info = [
                (s.get("name", "?"), self.tracker.aggression_score(s.get("uuid", "")),
                 self.tracker.is_showing_strength_this_hand(s.get("uuid", "")))
                for s in active_opponents
            ]
            plot_simulation_result(
                opp_hand_counts=opp_hand_counts,
                player_rank=projected_rank,
                win_probability=win_prob,
                street=street,
                round_num=round_num,
                hole_cards=hole_card,
                decision=action,
                decision_reason=reason,
                agent_stack=agent_stack,
                current_rank=current_rank,
                player_hand_counts=player_hand_counts,
                opp_tracker_info=opp_tracker_info,
                pot_size=pot_size,
                call_cost=call_cost,
            )

        return action, amount

    def decide_preflop(self, hole_card, fold_action, call_action, raise_action,
                       call_cost, num_opponents, small_blind):
        big_blind = small_blind * 2
        strength = preflop_strength(hole_card)
        # tighten requirements with more opponents since the same hand wins less often
        adjusted_strength = strength - max(0, (num_opponents - 2) * 3)
        bb_multiple = call_cost / big_blind if big_blind > 0 else 0

        if adjusted_strength >= PREFLOP_RAISE_STRONG and raise_action:
            bet_size = sizing_for_raise(99, 0, raise_action, is_preflop=True, small_blind=small_blind)
            self.raised_preflop = True
            return "raise", bet_size, f"Strong hand ({adjusted_strength:.0f}) — raising preflop."

        if adjusted_strength >= PREFLOP_RAISE_MED and raise_action and bb_multiple <= 2:
            bet_size = sizing_for_raise(99, 0, raise_action, is_preflop=True, small_blind=small_blind)
            self.raised_preflop = True
            return "raise", bet_size, f"Decent hand ({adjusted_strength:.0f}) — opening."

        if adjusted_strength >= PREFLOP_RAISE_MED and bb_multiple <= 3:
            return call_action["action"], call_cost, f"Decent hand ({adjusted_strength:.0f}) — calling raise."

        if adjusted_strength >= PREFLOP_MIN_CALL and bb_multiple <= PREFLOP_MAX_LIMP_BB:
            return call_action["action"], call_cost, f"Playable hand ({adjusted_strength:.0f}) — limping."

        if call_cost == 0:
            return call_action["action"], 0, "Weak hand — checking."
        return fold_action["action"], 0, "Weak hand — folding preflop."

    def decide_postflop(self, win_prob, current_rank, fold_action, call_action, raise_action,
                        call_cost, pot_size, num_opponents, opponent_is_scary, street, small_blind):
        win_pct = win_prob * 100
        raise_threshold, call_threshold = adaptive_thresholds(num_opponents)
        calling_is_profitable = self.pot_stats.is_ev_positive(win_pct, call_cost, pot_size)

        if current_rank >= HandRank.FULL_HOUSE and raise_action:
            bet_size = sizing_for_raise(win_pct, pot_size, raise_action, False, small_blind)
            return "raise", bet_size, f"Monster hand ({current_rank.name}) — raising."

        if win_pct >= raise_threshold and raise_action:
            bet_size = sizing_for_raise(win_pct, pot_size, raise_action, False, small_blind)
            return "raise", bet_size, f"Win {win_pct:.1f}% — raising."

        # c-bet if we raised preflop and actually connected with the board
        if (self.raised_preflop and street == "FLOP"
                and current_rank >= HandRank.PAIR and raise_action
                and not opponent_is_scary):
            bet_size = sizing_for_raise(win_pct, pot_size, raise_action, False, small_blind)
            return "raise", bet_size, f"C-bet with {current_rank.name} after preflop raise."

        if win_pct >= call_threshold or calling_is_profitable:
            return call_action["action"], call_cost, f"Win {win_pct:.1f}% — calling."

        if call_cost == 0:
            return call_action["action"], 0, "Checking."
        return fold_action["action"], 0, f"Win {win_pct:.1f}% too low — folding."

    def receive_street_start_message(self, s, rs): pass
