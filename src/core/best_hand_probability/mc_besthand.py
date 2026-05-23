from src.core.card import Card, Deck
from src.core.hand_evaluator import hand_score, HandRank
from itertools import combinations
import random

def monte_carlo_best_hand(hole_cards: list[Card],
                          community_cards: list[Card],
                          num_opponents: int,
                          num_iterations: int = 1000) -> float:
    """
    Estimate win probability (equity) using Monte Carlo simulation.
    Deals random runouts and opponent hands, evaluating all 5-card
    combinations using hand_score for kicker-aware comparison.

    Args:
        hole_cards:      the player's two private cards
        community_cards: visible board cards (0–5)
        num_opponents:   number of opponents to simulate
        num_iterations:  number of random simulations to run

    Returns:
        float between 0.0 and 1.0; ties counted as 1/(1 + tied_opponents)
    """

    wins = 0
    ties = 0

    for _ in range(num_iterations):

        # fresh deck
        deck = Deck()

        # remove known cards
        deck.remove(hole_cards + community_cards)

        # shuffle remaining deck
        random.shuffle(deck.cards)

        # complete board
        cards_needed = 5 - len(community_cards)
        runout = community_cards + deck.cards[:cards_needed]

        remaining = deck.cards[cards_needed:]

        # deal opponents
        opponent_hands = []
        for i in range(num_opponents):
            opp_hole = remaining[i * 2 : i * 2 + 2]
            opponent_hands.append(opp_hole)

        # evaluate our best hand
        our_best = max(
            hand_score(list(combo))
            for combo in combinations(hole_cards + runout, 5)
        )

        # compare against opponents
        result = "win"
        tied_opps = 0

        for opp_hole in opponent_hands:

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
                ties += 1 / (1 + tied_opps)

    return (wins + ties) / num_iterations