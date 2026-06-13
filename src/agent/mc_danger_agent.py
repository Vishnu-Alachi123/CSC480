from itertools import combinations
from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank, evaluate
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.pot_tracker import PotTracker

SUIT_MAP = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
RANK_MAP = {
    '2': Rank.TWO,  '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX,  '7': Rank.SEVEN, '8': Rank.EIGHT,'9': Rank.NINE,
    'T': Rank.TEN,  'J': Rank.JACK,  'Q': Rank.QUEEN,'K': Rank.KING, 'A': Rank.ACE,
}

def parse_card(card_str):
    return Card(RANK_MAP[card_str[1].upper()], SUIT_MAP[card_str[0].upper()])

def best_hand_rank(parsed_hole, parsed_community):
    all_cards = parsed_hole + parsed_community
    if len(all_cards) < 5:
        if len(all_cards) >= 2 and all_cards[0].rank == all_cards[1].rank:
            return HandRank.PAIR
        return HandRank.HIGH_CARD
    return max(evaluate(list(c)) for c in combinations(all_cards, 5))

DANGER_FOLD_THRESHOLD = 65


class MCDangerAgent(BasePokerPlayer):
    # MC plus a danger score. danger is just 1 - win_probability so when we're losing
    # most sims we treat it as high danger and fold hands that might technically be
    # worth calling on pot odds alone.

    def __init__(self):
        super().__init__()
        self.my_name = ""
        self.pot_stats = PotTracker()

    def receive_game_start_message(self, game_info):
        self.my_name = next((s["name"] for s in game_info.get("seats", []) if s.get("uuid") == self.uuid), "")

    def declare_action(self, valid_actions, hole_card, round_state):
        community_cards = round_state.get("community_card", [])
        seats = round_state.get("seats", [])
        fold_action = valid_actions[0]
        call_action = valid_actions[1]
        raise_action = valid_actions[2] if len(valid_actions) > 2 else None
        call_cost = call_action["amount"]

        hole = [parse_card(c) for c in hole_card]
        board = [parse_card(c) for c in community_cards]
        deck = Deck()
        deck.remove(hole + board)

        active_opponents = [s for s in seats if s.get("name") != self.my_name and s.get("state") == "participating"]
        num_opponents = max(len(active_opponents), 1)

        win_probability, *_ = monte_carlo_simulation(
            deck=deck,
            hole_cards=hole,
            community_cards=board,
            num_opp=num_opponents,
            num_sims=150,
        )
        danger_score = self.pot_stats.danger_score(win_probability)
        hand_rank = best_hand_rank(hole, board)

        if hand_rank >= HandRank.FULL_HOUSE:
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if hand_rank >= HandRank.TWO_PAIR and raise_action:
            if danger_score < 60:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if danger_score < DANGER_FOLD_THRESHOLD:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
