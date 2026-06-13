import random
from itertools import combinations
from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import evaluate, HandRank

SUIT_MAP = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
RANK_MAP = {
    '2': Rank.TWO,  '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX,  '7': Rank.SEVEN, '8': Rank.EIGHT,'9': Rank.NINE,
    'T': Rank.TEN,  'J': Rank.JACK,  'Q': Rank.QUEEN,'K': Rank.KING, 'A': Rank.ACE,
}

def parse_card(card_str):
    return Card(RANK_MAP[card_str[1].upper()], SUIT_MAP[card_str[0].upper()])

# raise when we hit two pair or better in 45%+ of random runouts
RAISE_THRESHOLD = 0.45
# call when we hit at least a pair in 60%+ of random runouts
CALL_THRESHOLD = 0.60

def simulate_own_hand(hole_cards, community_cards, remaining_deck, num_sims=200):
    # fills out the board randomly and checks how often we end up with a strong hand.
    # opponents are completely ignored here - the point is to show what pure hand
    # strength simulation looks like before adding opponent cards into the mix.
    cards_needed = 5 - len(community_cards)
    strong_count = 0
    pair_count = 0

    for _ in range(num_sims):
        sample = list(remaining_deck)
        random.shuffle(sample)
        full_board = list(community_cards) + sample[:cards_needed]
        all_cards = hole_cards + full_board
        if len(all_cards) >= 5:
            best_rank = max(evaluate(list(c)) for c in combinations(all_cards, 5))
        else:
            best_rank = HandRank.HIGH_CARD
        if best_rank >= HandRank.TWO_PAIR:
            strong_count += 1
        if best_rank >= HandRank.PAIR:
            pair_count += 1

    return strong_count / num_sims, pair_count / num_sims


class MCHandAgent(BasePokerPlayer):
    # only simulates our own hand, no opponent cards. raises if we'd hit two pair or
    # better in 45% of runouts, calls if we'd pair up in 60%. the obvious flaw is that
    # hand strength doesn't matter if someone else has better, which MCOpponentAgent fixes.

    def __init__(self):
        super().__init__()
        self.my_name = ""

    def receive_game_start_message(self, game_info):
        self.my_name = next((s["name"] for s in game_info.get("seats", []) if s.get("uuid") == self.uuid), "")

    def declare_action(self, valid_actions, hole_card, round_state):
        community_cards = round_state.get("community_card", [])
        fold_action = valid_actions[0]
        call_action = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost = call_action["amount"]

        hole = [parse_card(c) for c in hole_card]
        board = [parse_card(c) for c in community_cards]
        deck = Deck()
        deck.remove(hole + board)

        p_strong, p_pair = simulate_own_hand(hole, board, deck.cards)

        if p_strong >= RAISE_THRESHOLD and raise_action:
            return "raise", raise_action["amount"]["min"]
        if p_pair >= CALL_THRESHOLD:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
