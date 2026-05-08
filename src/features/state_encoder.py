"""
features/state_encoder.py
--------------------------
Converts a raw PyPokerEngine game state into a flat numeric feature vector
that can be fed directly into a neural network or Q-table.

Feature vector layout (total: ~30 floats, all normalized to [0, 1]):
    [0]     street (0=preflop, 0.33=flop, 0.67=turn, 1.0=river)
    [1]     pot / initial_stack  (normalized pot size)
    [2]     call_amount / my_stack  (how much it costs relative to my stack)
    [3]     pot_odds  (call / (pot + call))
    [4]     my_stack / initial_stack
    [5]     my_position  (0=early, 0.5=middle, 1=late/dealer)
    [6]     players_remaining / total_players
    [7]     hand_strength  (0–1, from treys evaluator)
    [8]     hand_potential  (0–1, from Monte Carlo equity estimate)
    [9-18]  community cards, each as (rank/12, suit/3) — 5 cards × 2 = 10 values
    [19-22] hole cards, each as (rank/12, suit/3) — 2 cards × 2 = 4 values
    [23-26] opponent aggression (raise_count / total_actions) per seat (up to 4 opp)
    [27]    stack_to_pot ratio (my_stack / pot), capped at 1.0
    [28]    round_count / max_rounds (how far into the game we are)
    [29]    active_opponents / (total_players - 1)
"""

import math
from treys import Card, Evaluator

# ── Card parsing ──────────────────────────────────────────────────────────────

RANK_MAP = {
    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4,
    '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9,
    'Q': 10, 'K': 11, 'A': 12,
}

SUIT_MAP = {
    'S': 0,   # spades
    'H': 1,   # hearts
    'D': 2,   # diamonds
    'C': 3,   # clubs
}

STREET_MAP = {
    'preflop': 0.0,
    'flop':    0.33,
    'turn':    0.67,
    'river':   1.0,
}


def parse_card_str(card_str: str) -> tuple[float, float]:
    """
    Parse a PyPokerEngine card string like 'CA', 'D5', 'HT' into
    a normalized (rank, suit) pair in [0, 1].

    PyPokerEngine format: suit-first, e.g. 'CA' = Ace of Clubs
    """
    suit_char = card_str[0].upper()
    rank_char = card_str[1].upper()
    rank_norm = RANK_MAP.get(rank_char, 0) / 12.0
    suit_norm = SUIT_MAP.get(suit_char, 0) / 3.0
    return rank_norm, suit_norm


def card_str_to_treys(card_str: str) -> int:
    """
    Convert PyPokerEngine card string ('CA', 'D5') to a treys Card int.
    Treys format: rank-first, e.g. 'Ac', '5d'
    """
    suit_char = card_str[0].upper()
    rank_char = card_str[1].upper()
    treys_suit = suit_char.lower()   # 's', 'h', 'd', 'c'
    treys_rank = rank_char           # '2'..'9', 'T', 'J', 'Q', 'K', 'A'
    return Card.new(treys_rank + treys_suit)


# ── Hand strength & equity ─────────────────────────────────────────────────

_evaluator = Evaluator()


def compute_hand_strength(hole_cards: list[str], community_cards: list[str]) -> float:
    """
    Compute a normalized hand strength score in [0, 1] using treys.
    1.0 = Royal Flush, 0.0 = worst possible hand.
    Only meaningful on the flop or later (needs ≥3 community cards).
    Returns 0.5 (neutral) preflop.
    """
    if len(community_cards) < 3:
        return 0.5  # Can't evaluate preflop meaningfully

    try:
        board = [card_str_to_treys(c) for c in community_cards]
        hand  = [card_str_to_treys(c) for c in hole_cards]
        score = _evaluator.evaluate(board, hand)
        # treys: 1 = best (royal flush), 7462 = worst. Invert and normalize.
        return 1.0 - (score - 1) / 7461.0
    except Exception:
        return 0.5


def compute_equity_monte_carlo(
    hole_cards: list[str],
    community_cards: list[str],
    num_opponents: int,
    num_simulations: int = 200,
) -> float:
    """
    Estimate win probability via Monte Carlo rollout.
    Randomly completes the board and deals opponents hands, counts wins.

    Args:
        hole_cards: your 2 hole cards as PyPokerEngine strings
        community_cards: 0–5 community cards as PyPokerEngine strings
        num_opponents: number of active opponents
        num_simulations: how many rollouts to run (200 is fast and decent)

    Returns:
        win probability in [0, 1]
    """
    import random

    # Build the full deck (suit+rank format to match PyPokerEngine)
    suits = ['S', 'H', 'D', 'C']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    full_deck = [s + r for s in suits for r in ranks]

    # Remove known cards from the deck
    known = set(hole_cards + community_cards)
    remaining_deck = [c for c in full_deck if c not in known]

    wins = 0
    for _ in range(num_simulations):
        deck_copy = remaining_deck[:]
        random.shuffle(deck_copy)

        # Complete the community cards to 5
        num_to_deal = 5 - len(community_cards)
        simulated_board = community_cards + deck_copy[:num_to_deal]
        deck_copy = deck_copy[num_to_deal:]

        # Deal 2 cards to each opponent
        try:
            board_treys = [card_str_to_treys(c) for c in simulated_board]
            my_hand     = [card_str_to_treys(c) for c in hole_cards]
            my_score    = _evaluator.evaluate(board_treys, my_hand)

            best_opp_score = None
            for i in range(num_opponents):
                opp_hand = [card_str_to_treys(deck_copy[i*2]), card_str_to_treys(deck_copy[i*2+1])]
                opp_score = _evaluator.evaluate(board_treys, opp_hand)
                if best_opp_score is None or opp_score < best_opp_score:
                    best_opp_score = opp_score

            # Lower score = better hand in treys
            if my_score < best_opp_score:
                wins += 1
            elif my_score == best_opp_score:
                wins += 0.5  # tie counts as half win
        except Exception:
            continue

    return wins / num_simulations if num_simulations > 0 else 0.5


# ── Opponent behavior tracking ─────────────────────────────────────────────

def extract_opponent_aggression(action_histories: dict, my_uuid: str, num_opp_slots: int = 4) -> list[float]:
    """
    For each opponent slot, compute raise_count / total_actions.
    Returns a list of `num_opp_slots` floats in [0, 1].
    Unknown/missing slots are filled with 0.5 (neutral prior).
    """
    aggression: dict[str, list] = {}  # uuid -> [total_actions, raise_count]

    for street_actions in action_histories.values():
        for event in street_actions:
            uuid   = event.get("uuid", "")
            action = event.get("action", "")
            if uuid == my_uuid:
                continue
            if uuid not in aggression:
                aggression[uuid] = [0, 0]
            if action not in ("SMALLBLIND", "BIGBLIND"):
                aggression[uuid][0] += 1
                if action == "RAISE":
                    aggression[uuid][1] += 1

    scores = []
    for uuid, (total, raises) in aggression.items():
        scores.append(raises / total if total > 0 else 0.5)

    # Pad or truncate to fixed size
    scores = scores[:num_opp_slots]
    while len(scores) < num_opp_slots:
        scores.append(0.5)

    return scores


# ── Main encoder ──────────────────────────────────────────────────────────────

def encode_state(
    valid_actions: list[dict],
    hole_card: list[str],
    round_state: dict,
    my_uuid: str,
    initial_stack: int = 1000,
    max_rounds: int = 100,
    run_equity: bool = True,
) -> list[float]:
    """
    Convert a raw PyPokerEngine game state into a normalized feature vector.

    Args:
        valid_actions: from declare_action()
        hole_card:     from declare_action(), e.g. ["CA", "D5"]
        round_state:   from declare_action()
        my_uuid:       your player's uuid (from receive_game_start_message)
        initial_stack: starting stack size (for normalization)
        max_rounds:    total rounds in game (for normalization)
        run_equity:    if True, runs Monte Carlo equity estimate (adds ~5ms)

    Returns:
        List of ~30 floats, all normalized to roughly [0, 1]
    """

    features = []

    # ── [0] Street ──────────────────────────────────────────────────────────
    street = round_state.get("street", "preflop")
    features.append(STREET_MAP.get(street, 0.0))

    # ── [1] Pot size ────────────────────────────────────────────────────────
    pot = round_state.get("pot", {}).get("main", {}).get("amount", 0)
    features.append(min(pot / initial_stack, 1.0))

    # ── [2] Call amount & [3] Pot odds ─────────────────────────────────────
    call_amount = valid_actions[1]["amount"] if len(valid_actions) > 1 else 0
    my_stack = _get_my_stack(round_state, my_uuid)
    features.append(min(call_amount / (my_stack + 1e-9), 1.0))  # [2]

    pot_odds = call_amount / (pot + call_amount + 1e-9)
    features.append(pot_odds)  # [3]

    # ── [4] My stack ────────────────────────────────────────────────────────
    features.append(min(my_stack / initial_stack, 1.0))

    # ── [5] My position ─────────────────────────────────────────────────────
    seats = round_state.get("seats", [])
    dealer_btn = round_state.get("dealer_btn", 0)
    my_position = _compute_position(seats, my_uuid, dealer_btn)
    features.append(my_position)

    # ── [6] Players remaining ───────────────────────────────────────────────
    active = [s for s in seats if s.get("state") == "participating"]
    total  = max(len(seats), 1)
    features.append(len(active) / total)

    # ── [7] Hand strength ───────────────────────────────────────────────────
    community = round_state.get("community_card", [])
    strength = compute_hand_strength(hole_card, community)
    features.append(strength)

    # ── [8] Equity estimate ─────────────────────────────────────────────────
    num_opp = max(len(active) - 1, 1)
    if run_equity:
        equity = compute_equity_monte_carlo(hole_card, community, num_opponents=num_opp)
    else:
        equity = strength  # fallback: use hand strength directly
    features.append(equity)

    # ── [9–18] Community cards (5 × 2 = 10 values) ─────────────────────────
    for i in range(5):
        if i < len(community):
            rank_n, suit_n = parse_card_str(community[i])
        else:
            rank_n, suit_n = 0.0, 0.0  # padding for missing cards
        features.append(rank_n)
        features.append(suit_n)

    # ── [19–22] Hole cards (2 × 2 = 4 values) ──────────────────────────────
    for i in range(2):
        if i < len(hole_card):
            rank_n, suit_n = parse_card_str(hole_card[i])
        else:
            rank_n, suit_n = 0.0, 0.0
        features.append(rank_n)
        features.append(suit_n)

    # ── [23–26] Opponent aggression (4 slots) ───────────────────────────────
    action_histories = round_state.get("action_histories", {})
    aggression = extract_opponent_aggression(action_histories, my_uuid, num_opp_slots=4)
    features.extend(aggression)

    # ── [27] Stack-to-pot ratio (capped at 1.0) ─────────────────────────────
    spr = my_stack / (pot + 1e-9)
    features.append(min(spr / 10.0, 1.0))  # normalize assuming ~10 SPR is "deep"

    # ── [28] Round progress ─────────────────────────────────────────────────
    round_count = round_state.get("round_count", 1)
    features.append(min(round_count / max_rounds, 1.0))

    # ── [29] Active opponent ratio ──────────────────────────────────────────
    features.append((len(active) - 1) / max(total - 1, 1))

    return features


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_my_stack(round_state: dict, my_uuid: str) -> float:
    for seat in round_state.get("seats", []):
        if seat.get("uuid") == my_uuid:
            return float(seat.get("stack", 0))
    return 0.0


def _compute_position(seats: list, my_uuid: str, dealer_btn: int) -> float:
    """
    Returns a position score in [0, 1]:
        0.0 = first to act (worst position, UTG)
        1.0 = last to act (best position, on/near button)
    """
    n = len(seats)
    if n <= 1:
        return 0.5

    my_idx = next((i for i, s in enumerate(seats) if s.get("uuid") == my_uuid), 0)
    # Seats after the dealer act last (best position)
    distance_from_dealer = (my_idx - dealer_btn) % n
    return distance_from_dealer / (n - 1)


def feature_names() -> list[str]:
    """Returns human-readable names for each feature index. Useful for debugging."""
    names = [
        "street",
        "pot_norm",
        "call_cost_norm",
        "pot_odds",
        "my_stack_norm",
        "position",
        "players_remaining_ratio",
        "hand_strength",
        "equity_mc",
        "community_0_rank", "community_0_suit",
        "community_1_rank", "community_1_suit",
        "community_2_rank", "community_2_suit",
        "community_3_rank", "community_3_suit",
        "community_4_rank", "community_4_suit",
        "hole_0_rank", "hole_0_suit",
        "hole_1_rank", "hole_1_suit",
        "opp_aggression_0",
        "opp_aggression_1",
        "opp_aggression_2",
        "opp_aggression_3",
        "stack_to_pot_norm",
        "round_progress",
        "active_opp_ratio",
    ]
    return names


# ─────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from pypokerengine.players import BasePokerPlayer
    from pypokerengine.api.game import setup_config, start_poker

    class EncoderTestAgent(BasePokerPlayer):
        """Prints the feature vector on the first action, then always calls."""

        def __init__(self):
            super().__init__()
            self.my_uuid = None
            self.printed = False

        def declare_action(self, valid_actions, hole_card, round_state):
            if not self.printed:
                vec = encode_state(
                    valid_actions=valid_actions,
                    hole_card=hole_card,
                    round_state=round_state,
                    my_uuid=self.my_uuid,
                    initial_stack=500,
                    max_rounds=5,
                    run_equity=True,
                )
                print("\n── Encoded State Vector ──")
                names = feature_names()
                for i, (name, val) in enumerate(zip(names, vec)):
                    print(f"  [{i:2d}] {name:<28s} = {val:.4f}")
                print(f"\nTotal features: {len(vec)}")
                self.printed = True

            call = valid_actions[1]
            return call["action"], call["amount"]

        def receive_game_start_message(self, game_info):
            # Grab our UUID so encode_state can identify us
            pass

        def receive_round_start_message(self, round_count, hole_card, seats): pass
        def receive_street_start_message(self, street, round_state): pass
        def receive_game_update_message(self, action, round_state): pass
        def receive_round_result_message(self, winners, hand_info, round_state): pass

    from pypokerengine.players import BasePokerPlayer

    class SimpleCallAgent(BasePokerPlayer):
        def declare_action(self, valid_actions, hole_card, round_state):
            return valid_actions[1]["action"], valid_actions[1]["amount"]
        def receive_game_start_message(self, g): pass
        def receive_round_start_message(self, r, h, s): pass
        def receive_street_start_message(self, s, rs): pass
        def receive_game_update_message(self, a, rs): pass
        def receive_round_result_message(self, w, h, rs): pass

    agent = EncoderTestAgent()

    config = setup_config(max_round=2, initial_stack=500, small_blind_amount=10)
    config.register_player(name="AIAgent",   algorithm=agent)
    config.register_player(name="CallAgent", algorithm=SimpleCallAgent())

    # PyPokerEngine assigns UUIDs after setup — grab it by peeking at the config
    start_poker(config, verbose=0)