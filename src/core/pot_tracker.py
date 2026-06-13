from collections import defaultdict


class PotTracker:
    # handles danger scoring, pot odds, and EV checks. the danger score flips win
    # probability around so we're asking "how likely is it someone beats us" rather
    # than "how often do we win". both MCDangerAgent and PokerAgent use this instead
    # of doing the pot math inline everywhere.

    def __init__(self):
        # track pot sizes across decisions so we can see how big pots have been
        self.pot_history = []

    def record_pot(self, pot_size: int):
        self.pot_history.append(pot_size)

    def average_pot(self) -> float:
        if not self.pot_history:
            return 0.0
        return sum(self.pot_history) / len(self.pot_history)

    # static helpers below, no instance state needed

    @staticmethod
    def danger_score(win_probability: float) -> float:
        # just (1 - win_probability) * 100. 70% win rate = danger 30, 25% win rate = danger 75.
        # used to fold medium hands even when pot odds technically justify calling.
        return (1.0 - win_probability) * 100.0

    @staticmethod
    def pot_equity_needed(call_cost: int, pot_size: int) -> float:
        # standard pot odds formula: call / (pot + call). if the pot is 100 and calling
        # costs 20 you only need to win 16.7% of the time to break even. returns 0 on a free check.
        total = pot_size + call_cost
        if total <= 0 or call_cost <= 0:
            return 0.0
        return (call_cost / total) * 100.0

    @staticmethod
    def is_ev_positive(win_pct: float, call_cost: int, pot_size: int,
                       min_win_pct: float = 15.0) -> bool:
        # true if win percentage beats pot odds and clears the minimum floor. the floor stops
        # us calling super marginal spots even when the math works out, variance is brutal below 15%.
        if call_cost <= 0:
            return True
        needed = PotTracker.pot_equity_needed(call_cost, pot_size)
        return win_pct > needed and win_pct >= min_win_pct

    @staticmethod
    def is_danger_high(win_probability: float, threshold: float = 65.0) -> bool:
        # true when we're losing more than (100 - threshold)% of sims. default 65 means
        # we flag danger when win probability drops below 35%, used to fold marginal hands.
        return PotTracker.danger_score(win_probability) > threshold
