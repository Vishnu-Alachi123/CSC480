from itertools import combinations
from pypokerengine.players import BasePokerPlayer
from src.core.card import Card, Rank, Suit
from src.core.hand_evaluator import evaluate, HandRank
from src.core.opponent_tracker import OpponentTracker

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


class BehaviorAgent(BasePokerPlayer):
    # same hand rank thresholds as HandRankAgent but with opponent tracking layered on.
    # if someone raised preflop and bet the flop we back off with medium hands, and against
    # a passive table we loosen up a bit. no MC, just to isolate how much tracking alone adds.

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

        hand_rank = best_hand_rank(hole_card, community_cards)

        opponent_uuids = [s.get("uuid", "") for s in seats if s.get("name") != self.my_name and s.get("state") == "participating"]
        max_aggression = max((self.tracker.aggression_score(u) for u in opponent_uuids), default=1.0)
        opponent_is_scary = any(self.tracker.is_showing_strength_this_hand(u) for u in opponent_uuids)

        if hand_rank >= HandRank.FULL_HOUSE:
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if hand_rank >= HandRank.STRAIGHT:
            if opponent_is_scary:
                return call_action["action"], call_cost
            if raise_action:
                return "raise", raise_action["amount"]["min"]
            return call_action["action"], call_cost

        if hand_rank >= HandRank.TWO_PAIR:
            if opponent_is_scary:
                if call_cost == 0:
                    return call_action["action"], 0
                return fold_action["action"], 0
            if max_aggression < 0.8:
                return call_action["action"], call_cost
            if call_cost == 0:
                return call_action["action"], 0
            return fold_action["action"], 0

        if call_cost == 0:
            return call_action["action"], 0
        return fold_action["action"], 0

    def receive_street_start_message(self, s, rs): pass
