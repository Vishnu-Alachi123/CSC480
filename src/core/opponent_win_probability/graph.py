"""
graph.py
--------
Single matplotlib window with three panels:

  [Top-left]  Opponent hand distribution — coloured by win/tie/loss vs agent
  [Top-right] Agent hand probability distribution — across simulated boards
  [Right]     Info panel — hole cards, hand ranks, decision reasoning, stack
"""

import matplotlib
matplotlib.use("MacOSX")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from src.core.hand_evaluator import HandRank

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

_BG_DARK  = "#16213e"
_BG_PANEL = "#1a1a2e"
_BORDER   = "#2a2a4a"

_fig      = None
_ax_opp   = None   # top-left:  opponent distribution
_ax_agent = None   # top-right: agent distribution
_ax_info  = None   # right:     info panel


def plot_simulation_result(
    opp_hand_counts: dict,
    player_rank: HandRank,           # projected most-likely rank (from simulations)
    win_probability: float,
    street: str,
    round_num: int,
    hole_cards: list,                # card strings e.g. ["SA", "H9"]
    decision: str,                   # "raise", "call", "fold"
    decision_reason: str,
    agent_stack: int,
    current_rank: HandRank = None,   # best hand from currently known cards
    player_hand_counts: dict = None, # distribution of agent's hand across simulations
):
    global _fig, _ax_opp, _ax_agent, _ax_info

    # ── Build or reuse figure ─────────────────────────────────────────────────
    if _fig is None or not plt.fignum_exists(_fig.number):
        _fig = plt.figure(figsize=(16, 7))
        _fig.canvas.manager.set_window_title("Monte Carlo — Agent Decision Analysis")
        gs = gridspec.GridSpec(
            1, 3,
            figure=_fig,
            width_ratios=[2.5, 2.5, 1],
            wspace=0.35,
        )
        _ax_opp   = _fig.add_subplot(gs[0, 0])
        _ax_agent = _fig.add_subplot(gs[0, 1])
        _ax_info  = _fig.add_subplot(gs[0, 2])
    else:
        _ax_opp.cla()
        _ax_agent.cla()
        _ax_info.cla()

    _fig.patch.set_facecolor(_BG_DARK)

    # ── Shared calculations ───────────────────────────────────────────────────
    opp_total  = sum(opp_hand_counts.values()) or 1
    opp_pcts   = [opp_hand_counts.get(r, 0) / opp_total * 100 for r in _ALL_RANKS]

    most_likely_opp     = max(opp_hand_counts, key=opp_hand_counts.get) if opp_hand_counts else HandRank.HIGH_CARD
    most_likely_opp_pct = opp_hand_counts.get(most_likely_opp, 0) / opp_total * 100

    winning_hands     = [r for r in _ALL_RANKS if r > player_rank]
    winning_pct       = sum(opp_hand_counts.get(r, 0) for r in winning_hands) / opp_total * 100
    winning_hands_str = "\n  ".join(
        f"{r.name.replace('_',' ')} ({opp_hand_counts.get(r,0)/opp_total*100:.1f}%)"
        for r in winning_hands if opp_hand_counts.get(r, 0) > 0
    ) or "None"

    proj_idx    = _ALL_RANKS.index(player_rank)
    current_idx = _ALL_RANKS.index(current_rank) if current_rank else None

    decision_color = {"raise": "#27ae60", "call": "#f39c12", "fold": "#c0392b"}.get(decision, "white")

    def _style_ax(ax, title, ylabel):
        ax.set_facecolor(_BG_PANEL)
        ax.tick_params(colors="white", labelsize=7)
        ax.yaxis.label.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor(_BORDER)
        ax.set_title(title, fontsize=10, pad=8, color="white")
        ax.set_ylabel(ylabel, color="white", fontsize=8)

    def _bar_labels(ax, bars, pcts):
        for bar, pct in zip(bars, pcts):
            if pct > 0.8:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f"{pct:.1f}%",
                    ha="center", va="bottom", fontsize=7, color="white"
                )

    # ── Panel 1: Opponent hand distribution ───────────────────────────────────
    opp_colors = [
        "#c0392b" if r > player_rank else ("#f39c12" if r == player_rank else "#27ae60")
        for r in _ALL_RANKS
    ]
    bars1 = _ax_opp.bar(_LABELS, opp_pcts, color=opp_colors, edgecolor="white", linewidth=0.5)
    _ax_opp.axvline(x=proj_idx, color="white", linewidth=1.5, linestyle="--", alpha=0.8)
    _bar_labels(_ax_opp, bars1, opp_pcts)
    _style_ax(_ax_opp, f"Opponent hand distribution\nRound {round_num} | {street.upper()}", "% of simulated opp hands")
    _ax_opp.set_ylim(0, max(opp_pcts) * 1.3 + 3)
    _ax_opp.legend(
        handles=[
            mpatches.Patch(color="#27ae60", label="Agent wins"),
            mpatches.Patch(color="#f39c12", label="Tie"),
            mpatches.Patch(color="#c0392b", label="Opp wins"),
        ],
        facecolor=_BG_PANEL, labelcolor="white", fontsize=8, loc="upper right"
    )

    # ── Panel 2: Agent hand probability distribution ──────────────────────────
    if player_hand_counts and len(player_hand_counts) > 0:
        player_total = sum(player_hand_counts.values()) or 1
        player_pcts  = [player_hand_counts.get(r, 0) / player_total * 100 for r in _ALL_RANKS]

        agent_colors = []
        for r in _ALL_RANKS:
            if current_rank and r == current_rank:
                agent_colors.append("#f39c12")   # gold — current hand
            elif r == player_rank:
                agent_colors.append("#3498db")   # blue — projected most likely
            else:
                agent_colors.append("#4a4a6a")   # muted

        bars2 = _ax_agent.bar(_LABELS, player_pcts, color=agent_colors, edgecolor="white", linewidth=0.5)
        _bar_labels(_ax_agent, bars2, player_pcts)

        if current_idx is not None:
            _ax_agent.axvline(x=current_idx, color="#f39c12", linewidth=1.5, linestyle="--",
                              label=f"Current: {current_rank.name.replace('_',' ')}")
        _ax_agent.axvline(x=proj_idx, color="#3498db", linewidth=1.5, linestyle=":",
                          label=f"Projected: {player_rank.name.replace('_',' ')}")

        _style_ax(_ax_agent,
                  f"Agent hand distribution  ({' '.join(hole_cards)})\n{player_total:,} simulated boards",
                  "% of simulated boards")
        _ax_agent.set_ylim(0, max(player_pcts) * 1.3 + 3)
        _ax_agent.legend(facecolor=_BG_PANEL, labelcolor="white", fontsize=8, loc="upper right")
    else:
        _ax_agent.set_facecolor(_BG_PANEL)
        _ax_agent.text(0.5, 0.5, "No simulation data\n(preflop)", transform=_ax_agent.transAxes,
                       ha="center", va="center", color="white", fontsize=11)
        _style_ax(_ax_agent, f"Agent hand distribution  ({' '.join(hole_cards)})", "% of simulated boards")

    # ── Panel 3: Info panel ───────────────────────────────────────────────────
    _ax_info.set_facecolor(_BG_PANEL)
    for spine in _ax_info.spines.values():
        spine.set_edgecolor(_BORDER)
    _ax_info.set_xticks([])
    _ax_info.set_yticks([])

    hole_str = "  ".join(hole_cards) if hole_cards else "—"

    info_lines = [
        ("HOLE CARDS",      hole_str,                                                                   "white"),
        ("CURRENT HAND",    (current_rank or player_rank).name.replace("_", " "),                      "#f39c12"),
        ("PROJECTED HAND",  player_rank.name.replace("_", " "),                                        "#3498db"),
        ("MOST LIKELY OPP", f"{most_likely_opp.name.replace('_',' ')}\n({most_likely_opp_pct:.1f}%)",  "#ff9999"),
        ("OPP BEATS AGENT", f"{winning_pct:.1f}% of sims",                                             "#c0392b"),
        ("  →",             winning_hands_str,                                                          "#c0392b"),
        ("WIN PROB",        f"{win_probability * 100:.1f}%",                                            "#27ae60"),
        ("AGENT STACK",     f"${agent_stack:,}",                                                        "#FFD700"),
        ("DECISION",        decision.upper(),                                                           decision_color),
        ("REASON",          decision_reason,                                                            "white"),
    ]

    y = 0.97
    for label, value, color in info_lines:
        if label == "  →":
            for line in value.split("\n"):
                _ax_info.text(0.05, y, f"  {line}", transform=_ax_info.transAxes,
                              fontsize=7, color=color, va="top")
                y -= 0.042
        else:
            _ax_info.text(0.05, y, label, transform=_ax_info.transAxes,
                          fontsize=7, color="#888888", va="top", fontstyle="italic")
            y -= 0.036
            # wrap long values (reason text)
            words = value.split()
            line, lines = "", []
            for w in words:
                if len(line) + len(w) + 1 > 22:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            for i, l in enumerate(lines):
                _ax_info.text(0.05, y, l, transform=_ax_info.transAxes,
                              fontsize=8 if i == 0 else 7,
                              color=color, va="top",
                              fontweight="bold" if i == 0 else "normal")
                y -= 0.042
            y -= 0.01

    plt.tight_layout()
    plt.pause(0.001)
