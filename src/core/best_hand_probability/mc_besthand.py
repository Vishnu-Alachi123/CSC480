from src.core.card import Card
from src.core.hand_evaluator import hand_score
from itertools import combinations
import random


def monte_carlo_best_hand(hole_cards: list,
                          community_cards: list,
                          num_opponents: int,
                          num_iterations: int = 200,
                          remaining_cards: list = None) -> float:
    # same idea as the main MC but uses hand_score instead of just HandRank so kickers
    # actually matter, an ace-high flush beats a king-high flush properly here. ties
    # get partial credit (1 / 1+tied opponents) instead of counting as a full win or loss.
    if remaining_cards is None:
        from src.core.card import Deck
        d = Deck()
        d.remove(hole_cards + community_cards)
        remaining_cards = d.cards

    num_opponents = min(num_opponents, 8)
    cards_needed  = 5 - len(community_cards)
    wins = 0.0

    for _ in range(num_iterations):
        sample = list(remaining_cards)
        random.shuffle(sample)

        runout    = community_cards + sample[:cards_needed]
        hand_pool = sample[cards_needed:]

        # deal opponent hands from the same shuffled pool
        opponent_hands = [
            hand_pool[i * 2: i * 2 + 2]
            for i in range(min(num_opponents, len(hand_pool) // 2))
        ]

        our_best = max(
            hand_score(list(combo))
            for combo in combinations(hole_cards + runout, 5)
        )

        result = "win"
        tied   = 0
        for opp_hole in opponent_hands:
            if len(opp_hole) < 2:
                continue
            opp_best = max(
                hand_score(list(combo))
                for combo in combinations(opp_hole + runout, 5)
            )
            if opp_best > our_best:
                result = "loss"
                break
            elif opp_best == our_best:
                tied += 1

        if result != "loss":
            wins += 1 / (1 + tied) if tied else 1

    return wins / num_iterations if num_iterations else 0.0
