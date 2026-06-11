from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation

SUIT_MAP = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'D': Suit.DIAMONDS, 'C': Suit.CLUBS}
RANK_MAP = {
    '2': Rank.TWO,  '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE,
    '6': Rank.SIX,  '7': Rank.SEVEN, '8': Rank.EIGHT,'9': Rank.NINE,
    'T': Rank.TEN,  'J': Rank.JACK,  'Q': Rank.QUEEN,'K': Rank.KING, 'A': Rank.ACE,
}

def parse_card(card_str):
    return Card(RANK_MAP[card_str[1].upper()], SUIT_MAP[card_str[0].upper()])

RAISE_WIN_PCT = 60
CALL_WIN_PCT = 40


class MCOpponentAgent(BasePokerPlayer):
    # deals random cards to opponents in each sim so we get actual win probability
    # against the field rather than just measuring hand strength in isolation.
    # no behavior tracking or danger scoring here, those come in later agents.

    def __init__(self):
        super().__init__()
        self.my_name = ""

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
        win_pct = win_probability * 100

        if win_pct >= RAISE_WIN_PCT and raise_action:
            return "raise", raise_action["amount"]["min"]
        if win_pct >= CALL_WIN_PCT:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_round_start_message(self, r, h, s): pass
    def receive_street_start_message(self, s, rs): pass
    def receive_game_update_message(self, a, rs): pass
    def receive_round_result_message(self, w, h, rs): pass
