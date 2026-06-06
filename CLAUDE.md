Poker bot project. Python, pypokerengine.

Structure:
- src/agent/base_agent.py — main agent
- src/core/hand_evaluator.py — hand ranking
- src/core/card.py — Card/Deck/Rank/Suit
- src/core/opponent_win_probability/monte_carlo.py — win probability simulation
- src/benchmark.py — runs agents against each other

Known bugs being fixed:
- num_opp counts self as opponent (_my_name not set)
- check_pot_odds always returns True
- decision logic based on hand rank thresholds, replacing with win_pct from monte carlo
- monte carlo denominator uses num_sims not actual total counter

Goal: beat CallAgent and StupidAgent in benchmark (33%+ win rate)
