from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank
from collections import defaultdict
from itertools import combinations
import random

"""
monte_carlo_simulation: runs simulations to get the probability of opponents possible hands
                        based on seen cards of hole and community cards
Args:
    deck: contains list of unseen cards
    hole_cards: cards that the agent is dealt
    community_cards: list of cards visible to all players
    num_sims: number of simulations to run, added to be able to tune the simulation for time and accuracy
    num_opp: number of players, this changes how many cards should be removed from the deck for each simulation

Returns:
    win_probability:  float 0–1, fraction of simulations the player wins (ties count as 0.5)
    player_rank:      HandRank — the best hand the player can make from currently known cards
    opp_hand_counts:  dict[HandRank, int] — distribution of opponent hand ranks across all simulations
"""
def monte_carlo_simulation(deck: Deck, hole_cards: list[Card], community_cards: list[Card], num_opp: int = 2, num_sims: int = 10000):

    board_cards_needed = 5 - len(community_cards)
    deck_cards = deck.cards
    opp_hand_counts = defaultdict(int)

    wins  = 0
    ties  = 0
    total = 0
    player_rank_counts = defaultdict(int)  # track distribution of player's hand across simulations

    known_cards = hole_cards + community_cards
    if len(known_cards) >= 7:
        player_rank = max(evaluate(list(c)) for c in combinations(known_cards, 5))
    else:
        player_rank = None  

    if board_cards_needed == 0:
        # River is dealt — board is complete, evaluate everything exactly
        for opp_cards in combinations(deck_cards, 2 * num_opp):

            opp_hands = [opp_cards[i*2:i*2+2] for i in range(num_opp)]

            opp_ranks = [
                max(evaluate(list(c)) for c in combinations(list(opp_hand) + community_cards, 5))
                for opp_hand in opp_hands
            ]

            for r in opp_ranks:
                opp_hand_counts[r] += 1

            best_opp = max(opp_ranks)

            player_rank = max(evaluate(list(c)) for c in combinations(list(hole_cards) + community_cards,5))
            if player_rank > best_opp:
                wins += 1
            elif player_rank == best_opp:
                ties += 1
            total += 1

    else:
        # Pre-river — sample random completions of the board
        cards_needed = (num_opp * 2) + board_cards_needed

        for _ in range(num_sims):
            sample_cards = random.sample(deck_cards, cards_needed)

            # Opponent hole cards are first, remaining cards complete the board
            board = community_cards + list(sample_cards[num_opp * 2:])

            # Evaluate player on the same completed board for a fair comparison
            sim_player_rank = max(evaluate(list(c)) for c in combinations(hole_cards + board, 5))
            player_rank_counts[sim_player_rank] += 1

            opp_ranks = [
                max(evaluate(list(c)) for c in combinations(list(sample_cards[i*2:i*2+2]) + board, 5))
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

        # Most likely hand the player ends up with across all simulated boards
        player_rank = max(player_rank_counts, key=player_rank_counts.get)
        top_player_rank = max(player_rank_counts.keys())
        print("top hand", top_player_rank)

    win_probability = (wins + ties * 0.5) / total

    return win_probability, player_rank, dict(opp_hand_counts)
