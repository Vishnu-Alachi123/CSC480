from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit, Deck
from src.core.hand_evaluator import HandRank
from src.core.opponent_win_probability.monte_carlo import monte_carlo_simulation
from src.core.opponent_tracker import OpponentTracker

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


class MCBehaviorAgent(BasePokerPlayer):
    # MC sims combined with opponent tracking. if someone's been aggressive or is
    # showing strength this hand we tighten up our thresholds, and against passive
    # tables we loosen them a bit.
    verbose = True

    def __init__(self):
        super().__init__()
        self.my_name = ""
        self.tracker = OpponentTracker()

    def receive_game_start_message(self, game_info):
        self.my_name = next((s["name"] for s in game_info.get("seats", []) if s.get("uuid") == self.uuid), "")

    def receive_round_start_message(self, round_count, hole_card, seats):
        self.tracker.new_round()

    def receive_game_update_message(self, action, round_state):
        self.tracker.record_action(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        all_uuids = [s["uuid"] for s in round_state.get("seats", []) if "uuid" in s]
        self.tracker.finish_round(all_uuids)

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

        opponent_uuids = [s.get("uuid", "") for s in active_opponents]
        max_aggression = max((self.tracker.aggression_score(u) for u in opponent_uuids), default=1.0)
        opponent_is_scary = any(self.tracker.is_showing_strength_this_hand(u) for u in opponent_uuids)

        raise_threshold = RAISE_WIN_PCT
        call_threshold = CALL_WIN_PCT

        if opponent_is_scary:
            raise_threshold += 15
            call_threshold += 10
        elif max_aggression > 1.5:
            raise_threshold += 10
            call_threshold += 5
        elif max_aggression < 0.5:
            raise_threshold = max(50, RAISE_WIN_PCT - 10)
            call_threshold = max(30, CALL_WIN_PCT - 10)

        if win_pct >= raise_threshold and raise_action:
            return "raise", raise_action["amount"]["min"]
        if win_pct >= call_threshold:
            return call_action["action"], call_cost
        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_street_start_message(self, s, rs): pass
