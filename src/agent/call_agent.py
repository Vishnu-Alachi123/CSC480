import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pypokerengine.players import BasePokerPlayer


class CallAgent(BasePokerPlayer):
    """Always calls whenever a call action is available."""

    def declare_action(self, valid_actions, hole_card, round_state):
        # valid_actions is typically [fold, call, raise]
        for action in valid_actions:
            if action["action"] == "call":
                return action["action"], action["amount"]

        # If a call is not available, fall back to check / fold / min raise.
        for action in valid_actions:
            if action["action"] == "check":
                return action["action"], action["amount"]
            if action["action"] == "raise":
                amount = action["amount"]["min"]
                return action["action"], amount

        return valid_actions[0]["action"], valid_actions[0]["amount"]

    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        pass
