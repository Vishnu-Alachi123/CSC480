"""
agent/base_agent.py — backward compatibility shim.
The main agent has been renamed to PokerAgent in poker_agent.py.
SimpleAgent is kept as an alias for imports that haven't been updated.
"""
from src.agent.poker_agent import PokerAgent as SimpleAgent  # noqa: F401

__all__ = ["SimpleAgent"]
