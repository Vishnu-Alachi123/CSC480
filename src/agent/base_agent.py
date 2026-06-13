# backward compatibility — the agent was renamed from SimpleAgent to PokerAgent
from src.agent.poker_agent import PokerAgent as SimpleAgent  # noqa: F401

__all__ = ["SimpleAgent"]
