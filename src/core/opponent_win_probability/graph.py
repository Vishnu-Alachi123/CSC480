import matplotlib
matplotlib.use("MacOSX")
import matplotlib.pyplot as plt
from src.core.hand_evaluator import HandRank

ALL_RANKS = [
    HandRank.HIGH_CARD, HandRank.PAIR, HandRank.TWO_PAIR, HandRank.THREE_OF_A_KIND,
    HandRank.STRAIGHT, HandRank.FLUSH, HandRank.FULL_HOUSE, HandRank.FOUR_OF_A_KIND,
    HandRank.STRAIGHT_FLUSH, HandRank.ROYAL_FLUSH,
]
LABELS = [r.name.replace("_", " ") for r in ALL_RANKS]

_fig = None
_axes = None


def plot_simulation_result(
    opp_hand_counts, player_rank, win_probability, street, round_num,
    hole_cards, decision, decision_reason, agent_stack,
    current_rank=None, player_hand_counts=None,
    opp_tracker_info=None, pot_size=0, call_cost=0,
):
    global _fig, _axes

    if _fig is None or not plt.fignum_exists(_fig.number):
        _fig, _axes = plt.subplots(1, 3, figsize=(14, 5))
        _fig.canvas.manager.set_window_title("Monte Carlo Decision Analysis")
    else:
        for ax in _axes:
            ax.cla()

    opp_total = sum(opp_hand_counts.values()) or 1
    opp_pcts = [opp_hand_counts.get(r, 0) / opp_total * 100 for r in ALL_RANKS]

    # opponent hand distribution
    ax = _axes[0]
    ax.bar(LABELS, opp_pcts)
    ax.set_title(f"Opponent Hands  Round {round_num} | {street}")
    ax.set_ylabel("% of simulations")
    ax.tick_params(axis="x", rotation=45, labelsize=7)

    # agent projected hand distribution
    ax = _axes[1]
    if player_hand_counts:
        pl_total = sum(player_hand_counts.values()) or 1
        pl_pcts = [player_hand_counts.get(r, 0) / pl_total * 100 for r in ALL_RANKS]
        ax.bar(LABELS, pl_pcts)
    else:
        ax.text(0.5, 0.5, "No data (preflop)", transform=ax.transAxes, ha="center", va="center")
    ax.set_title(f"Agent Hand  {' '.join(hole_cards)}  Win: {win_probability * 100:.1f}%  → {decision.upper()}")
    ax.set_ylabel("% of simulations")
    ax.tick_params(axis="x", rotation=45, labelsize=7)

    # opponent behavioral tracking
    ax = _axes[2]
    if opp_tracker_info:
        names = [t[0] for t in opp_tracker_info]
        scores = [t[1] for t in opp_tracker_info]
        ax.barh(names, scores)
        ax.axvline(x=1.0, color="gray", linestyle="--", linewidth=1, label="baseline (1.0)")
        ax.set_xlabel("Aggression Score")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "No tracking data yet", transform=ax.transAxes, ha="center", va="center")
    ax.set_title("Opponent Tracker")

    plt.tight_layout()
    plt.pause(0.001)
