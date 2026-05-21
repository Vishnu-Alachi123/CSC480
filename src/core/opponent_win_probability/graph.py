"""
graph.py
--------
Plots the opponent hand distribution from a Monte Carlo simulation.

Shows:
  - Bar chart of opponent hand rank distribution (green = agent wins, gold = tie, red = agent loses)
  - Agent's hole cards
  - Agent's current best hand
  - The most likely opponent hand
  - Which hands would beat the agent
  - Decision reasoning and agent stack
"""

import matplotlib
matplotlib.use("MacOSX")   # non-blocking backend for macOS

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from src.core.hand_evaluator import HandRank

# Ordered list of all hand ranks from weakest to strongest
_ALL_RANKS = [
    HandRank.HIGH_CARD,
    HandRank.PAIR,
    HandRank.TWO_PAIR,
    HandRank.THREE_OF_A_KIND,
    HandRank.STRAIGHT,
    HandRank.FLUSH,
    HandRank.FULL_HOUSE,
    HandRank.FOUR_OF_A_KIND,
    HandRank.STRAIGHT_FLUSH,
    HandRank.ROYAL_FLUSH,
]

_LABELS = [r.name.replace("_", "\n") for r in _ALL_RANKS]

# Keep a reference to the figure so we reuse the same window each call
_fig = None
_ax_bar  = None
_ax_info = None


def plot_simulation_result(
    opp_hand_counts: dict,
    player_rank: HandRank,
    win_probability: float,
    street: str,
    round_num: int,
    hole_cards: list,        # list of card strings e.g. ["SA", "H9"]
    decision: str,           # e.g. "raise", "call", "fold"
    decision_reason: str,    # human-readable explanation
    agent_stack: int,
):
    """
    Render a bar chart of opponent hand distribution plus an info panel.

    Args:
        opp_hand_counts:  dict[HandRank, int] from monte_carlo_simulation
        player_rank:      HandRank — the agent's best current hand
        win_probability:  float 0–1
        street:           e.g. "preflop", "flop", "turn", "river"
        round_num:        current round number
        hole_cards:       list of raw card strings the agent holds
        decision:         action the agent chose
        decision_reason:  why the agent chose it
        agent_stack:      agent's current chip count
    """
    global _fig, _ax_bar, _ax_info

    total = sum(opp_hand_counts.values()) or 1
    percentages = [opp_hand_counts.get(r, 0) / total * 100 for r in _ALL_RANKS]
    player_idx  = _ALL_RANKS.index(player_rank)

    # Most likely opponent hand
    most_likely_rank = max(opp_hand_counts, key=opp_hand_counts.get) if opp_hand_counts else HandRank.HIGH_CARD
    most_likely_pct  = opp_hand_counts.get(most_likely_rank, 0) / total * 100

    # Hands that beat the agent
    winning_hands = [r for r in _ALL_RANKS if r > player_rank]
    winning_pct   = sum(opp_hand_counts.get(r, 0) for r in winning_hands) / total * 100

    # Bar colours: green = agent wins, gold = tie, red = agent loses
    colors = []
    for r in _ALL_RANKS:
        if r > player_rank:
            colors.append("#c0392b")
        elif r == player_rank:
            colors.append("#f39c12")
        else:
            colors.append("#27ae60")

    # Build or reuse figure with two subplots: bar chart + info panel
    if _fig is None or not plt.fignum_exists(_fig.number):
        _fig, (_ax_bar, _ax_info) = plt.subplots(
            1, 2,
            figsize=(14, 6),
            gridspec_kw={"width_ratios": [3, 1]}
        )
        _fig.canvas.manager.set_window_title("Monte Carlo — Agent Decision Analysis")
    else:
        _ax_bar.cla()
        _ax_info.cla()

    # ── Bar chart ─────────────────────────────────────────────────────────────
    bars = _ax_bar.bar(_LABELS, percentages, color=colors, edgecolor="white", linewidth=0.6)

    # Vertical line at agent's hand
    _ax_bar.axvline(
        x=player_idx, color="white", linewidth=2, linestyle="--",
        label=f"Agent hand: {player_rank.name.replace('_', ' ')}"
    )

    # Percentage labels on bars
    for bar, pct in zip(bars, percentages):
        if pct > 0.5:
            _ax_bar.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.4,
                f"{pct:.1f}%",
                ha="center", va="bottom", fontsize=8, color="white"
            )

    legend_patches = [
        mpatches.Patch(color="#27ae60", label="Agent wins"),
        mpatches.Patch(color="#f39c12", label="Tie"),
        mpatches.Patch(color="#c0392b", label="Opponent wins"),
    ]
    _ax_bar.set_facecolor("#1a1a2e")
    _ax_bar.tick_params(colors="white", labelsize=8)
    _ax_bar.yaxis.label.set_color("white")
    _ax_bar.title.set_color("white")
    for spine in _ax_bar.spines.values():
        spine.set_edgecolor("#444")
    _ax_bar.set_title(
        f"Round {round_num}  |  {street.upper()}  |  Win probability: {win_probability * 100:.1f}%",
        fontsize=13, pad=12, color="white"
    )
    _ax_bar.set_ylabel("% of simulated opponent hands", color="white")
    _ax_bar.set_ylim(0, max(percentages) * 1.2 + 5)
    _ax_bar.legend(handles=legend_patches, facecolor="#1a1a2e", labelcolor="white", fontsize=9)

    # ── Info panel ────────────────────────────────────────────────────────────
    _ax_info.set_facecolor("#1a1a2e")
    for spine in _ax_info.spines.values():
        spine.set_edgecolor("#444")
    _ax_info.set_xticks([])
    _ax_info.set_yticks([])

    # Format hole cards nicely
    hole_str = "  ".join(hole_cards) if hole_cards else "—"

    # Winning hands list (only those with >0% probability)
    winning_hands_with_prob = [
        f"{r.name.replace('_', ' ')} ({opp_hand_counts.get(r,0)/total*100:.1f}%)"
        for r in winning_hands
        if opp_hand_counts.get(r, 0) > 0
    ]
    winning_str = "\n  ".join(winning_hands_with_prob) if winning_hands_with_prob else "None"

    # Decision colour
    decision_color = {
        "raise": "#27ae60",
        "call":  "#f39c12",
        "fold":  "#c0392b",
    }.get(decision, "white")

    info_lines = [
        ("HOLE CARDS",        hole_str,                                    "white"),
        ("AGENT BEST HAND",   player_rank.name.replace("_", " "),         "#f39c12"),
        ("MOST LIKELY OPP",   f"{most_likely_rank.name.replace('_',' ')} ({most_likely_pct:.1f}%)", "#aaaaff"),
        ("HANDS THAT BEAT",   f"{winning_pct:.1f}% of sims",              "#c0392b"),
        ("  →",               winning_str,                                 "#c0392b"),
        ("WIN PROBABILITY",   f"{win_probability * 100:.1f}%",            "#27ae60"),
        ("AGENT STACK",       f"${agent_stack:,}",                        "#FFD700"),
        ("DECISION",          decision.upper(),                            decision_color),
        ("REASON",            decision_reason,                             "white"),
    ]

    y = 0.97
    for label, value, color in info_lines:
        if label == "  →":
            # Multi-line value for winning hands list
            for line in value.split("\n"):
                _ax_info.text(0.05, y, f"  {line}", transform=_ax_info.transAxes,
                              fontsize=8, color=color, va="top", wrap=True)
                y -= 0.045
        else:
            _ax_info.text(0.05, y, label, transform=_ax_info.transAxes,
                          fontsize=8, color="#888888", va="top", fontstyle="italic")
            y -= 0.04
            _ax_info.text(0.05, y, value, transform=_ax_info.transAxes,
                          fontsize=9, color=color, va="top", fontweight="bold")
            y -= 0.055

    _fig.patch.set_facecolor("#16213e")
    plt.tight_layout()
    plt.pause(0.001)
