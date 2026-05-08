"""
environment/game.py
-------------------
Sets up and runs a PyPokerEngine game.
Provides a base agent class your AI agent can subclass.
"""

from pypokerengine.players import BasePokerPlayer
from pypokerengine.api.game import setup_config, start_poker
from pypokerengine.api.emulator import Emulator
from pypokerengine.utils.game_state_utils import restore_game_state


# ─────────────────────────────────────────────
# Base Agent — subclass this for your AI agent
# ─────────────────────────────────────────────

class PokerAgent(BasePokerPlayer):
    """
    Base class for all poker agents in this project.
    Subclass this and override `decide_action` with your logic.

    The agent lifecycle (called by PyPokerEngine automatically):
        1. receive_game_start_message  — once at the start
        2. receive_round_start_message — start of each hand
        3. receive_street_start_message — each street (preflop/flop/turn/river)
        4. declare_action              — YOUR AGENT ACTS HERE
        5. receive_game_update_message — after every action by any player
        6. receive_round_result_message — end of hand
    """

    def declare_action(self, valid_actions, hole_card, round_state):
        """
        Called when it's this agent's turn to act.

        Args:
            valid_actions: list of dicts, e.g.:
                [
                  {"action": "fold",  "amount": 0},
                  {"action": "call",  "amount": 10},
                  {"action": "raise", "amount": {"min": 20, "max": 200}}
                ]
            hole_card: list of 2 card strings, e.g. ["CA", "D5"]
            round_state: full game state dict (see state_encoder.py)

        Returns:
            (action_str, amount) tuple, e.g. ("call", 10) or ("raise", 40)
        """
        action, amount = self.decide_action(valid_actions, hole_card, round_state)
        return action, amount

    def decide_action(self, valid_actions, hole_card, round_state):
        """Override this in subclasses. Default: always call."""
        call = valid_actions[1]
        return call["action"], call["amount"]

    # ── Lifecycle hooks (override as needed) ──

    def receive_game_start_message(self, game_info):
        """Called once. game_info has player_num, max_round, blind amounts."""
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        """Called at the start of each hand."""
        pass

    def receive_street_start_message(self, street, round_state):
        """Called at preflop, flop, turn, river."""
        pass

    def receive_game_update_message(self, action, round_state):
        """Called after every player action. Useful for tracking opponents."""
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        """Called at end of hand. winners is a list of winner dicts."""
        pass


# ─────────────────────────────────────────────
# Example baseline agents
# ─────────────────────────────────────────────

class RandomAgent(PokerAgent):
    """Picks a random valid action. Useful as a training baseline."""

    def decide_action(self, valid_actions, hole_card, round_state):
        import random
        chosen = random.choice(valid_actions)
        action = chosen["action"]

        if action == "raise":
            min_r = chosen["amount"]["min"]
            max_r = chosen["amount"]["max"]
            # Raise a random amount between min and max
            amount = random.randint(min_r, max_r) if max_r > min_r else min_r
        else:
            amount = chosen["amount"]

        return action, amount


class CallAgent(PokerAgent):
    """Always calls. The simplest possible baseline."""

    def decide_action(self, valid_actions, hole_card, round_state):
        call = valid_actions[1]
        return call["action"], call["amount"]


# ─────────────────────────────────────────────
# Game runner
# ─────────────────────────────────────────────

def run_game(
    agents: list,               # list of (name, PokerAgent instance) tuples
    max_rounds: int = 20,
    initial_stack: int = 1000,
    small_blind: int = 10,
    verbose: int = 1,           # 0=silent, 1=round summary, 2=full log
) -> dict:
    """
    Run a full poker game between the given agents.

    Args:
        agents: list of (name, agent_instance) tuples
        max_rounds: how many hands to play
        initial_stack: starting chips for each player
        small_blind: small blind amount
        verbose: 0 = silent, 1 = round results, 2 = all actions

    Returns:
        game_result dict with final stacks and winner info
    """
    config = setup_config(
        max_round=max_rounds,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )

    for name, agent in agents:
        config.register_player(name=name, algorithm=agent)

    result = start_poker(config, verbose=verbose)
    return result


def make_emulator(num_players: int, max_rounds: int, small_blind: int, ante: int = 0):
    """
    Create a PyPokerEngine Emulator for training/rollouts.
    The emulator lets you fast-forward game states without a full game loop —
    useful for computing expected value in your RL agent.

    Usage:
        emulator = make_emulator(num_players=2, max_rounds=100, small_blind=10)
        # Then: emulator.apply_action(game_state, action)
        #       emulator.run_until_round_finish(game_state)
    """
    emulator = Emulator()
    emulator.set_game_rule(num_players, max_rounds, small_blind, ante)
    return emulator


# ─────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Running 5-round game: CallAgent vs RandomAgent")
    print("=" * 50)

    agents = [
        ("CallBot",   CallAgent()),
        ("RandomBot", RandomAgent()),
    ]

    result = run_game(agents, max_rounds=5, initial_stack=500, small_blind=10, verbose=1)

    print("\n── Final Result ──")
    for player in result["players"]:
        print(f"  {player['name']:12s}  final stack: {player['stack']:>6} chips")