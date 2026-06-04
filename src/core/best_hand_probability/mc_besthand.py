from src.core.card import Card, Deck
from src.core.hand_evaluator import hand_score, HandRank
from itertools import combinations
import random

def monte_carlo_best_hand(hole_cards: list[Card],
                          community_cards: list[Card],
                          deck: Deck,
                          num_opponents: int,
                          num_iterations: int = 1000) -> float:
    """
    Estimate win probability (equity) using Monte Carlo simulation.
    Deals random runouts and opponent hands, evaluating all 5-card
    combinations using hand_score for kicker-aware comparison.

    Args:
        hole_cards:      the player's two private cards
        community_cards: visible board cards (0–5)
        deck: contains list of unseen cards
        num_opponents:   number of opponents to simulate
        num_iterations:  number of random simulations to run

    Returns:
        float between 0.0 and 1.0; ties counted as 1/(1 + tied_opponents)
    """

    wins = 0

    cards_needed = 5 - len(community_cards)

    # total cards randomly drawn each simulation
    sample_size = cards_needed + (num_opponents * 2)

    for _ in range(num_iterations):
        # complete board
        sample = random.sample(deck.cards, sample_size)

        # first part of sample completes the community board
        runout = community_cards + sample[:cards_needed]

        # rest of sample is used for opponent hole cards
        opponent_cards = sample[cards_needed:]

        # evaluate our best hand
        our_best = max(
            hand_score(list(combo))
            for combo in combinations(hole_cards + runout, 5)
        )

        # compare against opponents
        result = "win"
        tied_opps = 0

        for i in range(num_opponents):
            # each opponent gets 2 cards
            opp_hole = opponent_cards[i * 2 : i * 2 + 2]

            opp_best = max(
                hand_score(list(combo))
                for combo in combinations(opp_hole + runout, 5)
            )

            if opp_best > our_best:
                result = "loss"
                break

            elif opp_best == our_best:
                tied_opps += 1

        if result != "loss":
            if tied_opps == 0:
                wins += 1
            else:
                wins += 1 / (1 + tied_opps)

    return wins / num_iterations