from itertools import combinations
from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank

SUIT_MAP = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
RANK_MAP = {
    '2': Rank.TWO,  '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX,  '7': Rank.SEVEN, '8': Rank.EIGHT,'9': Rank.NINE,
    'T': Rank.TEN,  'J': Rank.JACK,  'Q': Rank.QUEEN,'K': Rank.KING, 'A': Rank.ACE,
}

def parse_card(card_str):
    return Card(RANK_MAP[card_str[1].upper()], SUIT_MAP[card_str[0].upper()])

def best_hand_rank(hole_cards, community_cards):
    all_cards = [parse_card(c) for c in hole_cards + community_cards]
    if len(all_cards) < 2:
        return HandRank.HIGH_CARD
    if len(all_cards) < 5:
        return HandRank.PAIR if all_cards[0].rank == all_cards[1].rank else HandRank.HIGH_CARD
    return max(evaluate(list(combo)) for combo in combinations(all_cards, 5))


class HandRankAgent(BasePokerPlayer):
    # baseline that only looks at hand rank, no simulation. 
    # it raises on full house or better, calls straights and flushes,
    # and checks or folds everything below two pair.

    def declare_action(self, valid_actions, hole_card, round_state):
        community_cards = round_state.get("community_card", [])
        fold_action = valid_actions[0]
        call_action = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost = call_action["amount"]

        rank = best_hand_rank(hole_card, community_cards)

        if rank >= HandRank.FULL_HOUSE:
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if rank >= HandRank.STRAIGHT:
            return call_action["action"], call_cost

        if rank >= HandRank.TWO_PAIR:
            if call_cost == 0:
                return call_action["action"], 0
            return fold_action["action"], 0

        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_game_start_message(self, g): pass
    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
