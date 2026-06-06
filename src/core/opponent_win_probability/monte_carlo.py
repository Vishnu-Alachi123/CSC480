from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank
from collections import defaultdict
from itertools import combinations
from math import comb
import random

DEBUG = False


def _best_hand(hole: list, board: list) -> HandRank:
    cards = hole + board
    if len(cards) < 5:
        return HandRank.HIGH_CARD
    return max(evaluate(list(c)) for c in combinations(cards, 5))


def monte_carlo_simulation(
    deck: Deck,
    hole_cards: list,
    community_cards: list,
    num_opp: int = 2,
    num_sims: int = 200,
    workers=None,  # kept for backwards compat, ignored
) -> tuple:
    """
    Run Monte Carlo simulations to estimate win probability.

    Returns:
        (win_probability, current_rank, projected_rank, opp_hand_counts, player_rank_counts)
    """
    assert len(hole_cards) == 2, f"Expected 2 hole cards, got {len(hole_cards)}"
    assert len(community_cards) in (0, 3, 4, 5), f"Expected 0/3/4/5 community cards, got {len(community_cards)}"
    assert 1 <= num_opp <= 8, f"Expected 1–8 opponents, got {num_opp}"

    # more sims at preflop where there is the most uncertainty
    if len(community_cards) == 0:
        num_sims = max(num_sims, 500)

    board_cards_needed = 5 - len(community_cards)
    deck_cards = deck.cards

    known_cards = hole_cards + community_cards
    if len(known_cards) >= 5:
        current_rank = max(evaluate(list(c)) for c in combinations(known_cards, 5))
    elif len(known_cards) > 0:
        current_rank = evaluate(known_cards)
    else:
        current_rank = HandRank.HIGH_CARD

    wins = ties = total = 0
    opp_hand_counts: dict = defaultdict(int)
    player_rank_counts: dict = defaultdict(int)

    # ── River: board is complete ──────────────────────────────────────────────
    if board_cards_needed == 0:
        projected_rank = current_rank
        num_combos = comb(len(deck_cards), 2 * num_opp)

        if num_combos <= 10_000:
            for opp_cards in combinations(deck_cards, 2 * num_opp):
                opp_ranks = [
                    _best_hand(list(opp_cards[i * 2: i * 2 + 2]), community_cards)
                    for i in range(num_opp)
                ]
                for r in opp_ranks:
                    opp_hand_counts[r] += 1
                best_opp = max(opp_ranks)
                if current_rank > best_opp:
                    wins += 1
                elif current_rank == best_opp:
                    ties += 1
                total += 1
        else:
            for _ in range(num_sims):
                opp_cards = random.sample(deck_cards, 2 * num_opp)
                opp_ranks = [
                    _best_hand(opp_cards[i * 2: i * 2 + 2], community_cards)
                    for i in range(num_opp)
                ]
                for r in opp_ranks:
                    opp_hand_counts[r] += 1
                best_opp = max(opp_ranks)
                if current_rank > best_opp:
                    wins += 1
                elif current_rank == best_opp:
                    ties += 1
                total += 1

        # normalize opp counts to a per-opponent basis
        opp_hand_counts = {k: v / num_opp for k, v in opp_hand_counts.items()}
        win_probability = (wins + ties * 0.5) / total

        if DEBUG:
            print(f"[monte_carlo RIVER] num_opp={num_opp}, deck={len(deck_cards)}, "
                  f"wins={wins}, ties={ties}, total={total}, "
                  f"win_prob={win_probability:.3f}, current={current_rank}, projected={projected_rank}")

        return win_probability, current_rank, projected_rank, opp_hand_counts, {}

    # ── Pre-river: single-threaded Monte Carlo ────────────────────────────────
    cards_needed = (num_opp * 2) + board_cards_needed

    for _ in range(num_sims):
        sample_cards = random.sample(deck_cards, cards_needed)
        board = community_cards + sample_cards[num_opp * 2:]

        sim_player_rank = _best_hand(hole_cards, board)
        player_rank_counts[sim_player_rank] += 1

        opp_ranks = [
            _best_hand(sample_cards[i * 2: i * 2 + 2], board)
            for i in range(num_opp)
        ]
        for r in opp_ranks:
            opp_hand_counts[r] += 1

        best_opp = max(opp_ranks)
        if sim_player_rank > best_opp:
            wins += 1
        elif sim_player_rank == best_opp:
            ties += 1
        total += 1

    projected_rank = max(player_rank_counts, key=player_rank_counts.get)
    win_probability = (wins + ties * 0.5) / total

    if DEBUG:
        print(f"[monte_carlo PRE-RIVER] num_opp={num_opp}, deck={len(deck_cards)}, "
              f"wins={wins}, ties={ties}, total={total}, "
              f"win_prob={win_probability:.3f}, current={current_rank}, projected={projected_rank}")

    return win_probability, current_rank, projected_rank, dict(opp_hand_counts), dict(player_rank_counts)
