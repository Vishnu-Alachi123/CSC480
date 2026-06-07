"""
graph.py — Monte Carlo Agent Decision Analysis
----------------------------------------------
Five-panel layout:

  [Top-left]     Opponent hand distribution  (coloured by win/tie/loss)
  [Top-right]    Agent hand distribution     (current vs projected)
  [Bottom-left]  Opponent behavioral tracking (aggression scores)
  [Bottom-right] Win probability + pot dashboard (gauges)
  [Far-right]    Info panel                  (all key numbers at a glance)
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

_BG_DARK  = "#0d1117"
_BG_PANEL = "#161b22"
_BORDER   = "#30363d"
_TEXT_DIM = "#8b949e"
_TEXT     = "#e6edf3"

_CLR_WIN   = "#2ea043"   # green
_CLR_TIE   = "#d29922"   # amber
_CLR_LOSS  = "#da3633"   # red
_CLR_RAISE = "#3fb950"
_CLR_CALL  = "#d29922"
_CLR_FOLD  = "#f85149"
_CLR_BLUE  = "#58a6ff"
_CLR_GOLD  = "#e3b341"

# ── Persistent figure state ───────────────────────────────────────────────────
_fig      = None
_axes     = {}   # keyed by name


def _build_figure():
    global _fig, _axes
    _fig = plt.figure(figsize=(20, 9), layout="constrained")
    _fig.patch.set_facecolor(_BG_DARK)
    _fig.canvas.manager.set_window_title("Monte Carlo — Agent Decision Analysis")

    gs = gridspec.GridSpec(
        2, 3,
        figure       = _fig,
        width_ratios  = [2.2, 2.2, 1.4],
        height_ratios = [1, 1],
    )
    _axes["opp"]     = _fig.add_subplot(gs[0, 0])
    _axes["agent"]   = _fig.add_subplot(gs[0, 1])
    _axes["tracker"] = _fig.add_subplot(gs[1, 0])
    _axes["gauge"]   = _fig.add_subplot(gs[1, 1])
    _axes["info"]    = _fig.add_subplot(gs[:, 2])


def _style_ax(ax, title, ylabel=""):
    ax.set_facecolor(_BG_PANEL)
    ax.tick_params(colors=_TEXT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)
    ax.set_title(title, fontsize=9, pad=6, color=_TEXT, fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel, color=_TEXT_DIM, fontsize=7)


def _bar_pct_labels(ax, bars, pcts, threshold=0.8):
    for bar, pct in zip(bars, pcts):
        if pct > threshold:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{pct:.1f}%",
                ha="center", va="bottom", fontsize=6.5, color=_TEXT
            )


def _win_color(pct: float) -> str:
    if pct >= 60:  return _CLR_WIN
    if pct >= 40:  return _CLR_TIE
    return _CLR_LOSS


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def plot_simulation_result(
    opp_hand_counts: dict,
    player_rank: HandRank,
    win_probability: float,
    street: str,
    round_num: int,
    hole_cards: list,
    decision: str,
    decision_reason: str,
    agent_stack: int,
    current_rank: HandRank = None,
    player_hand_counts: dict = None,
    # ── new parameters ────────────────────────────────────────────────────────
    opp_tracker_info: list = None,   # [(name, aggression_score, is_threatening), ...]
    pot_size: int = 0,
    call_cost: int = 0,
):
    """
    Render the 5-panel decision analysis window.

    opp_tracker_info: list of (display_name, aggression_score, is_threatening)
                      for each active opponent. Pass empty list if no tracker.
    pot_size:         total chips in the pot this street.
    call_cost:        chips required to call (0 = check available).
    """
    global _fig, _axes

    if _fig is None or not plt.fignum_exists(_fig.number):
        _build_figure()
    else:
        for ax in _axes.values():
            ax.cla()

    _fig.patch.set_facecolor(_BG_DARK)

    win_pct  = win_probability * 100
    danger   = 100.0 - win_pct
    proj_idx = _ALL_RANKS.index(player_rank)
    cur_idx  = _ALL_RANKS.index(current_rank) if current_rank else None

    opp_total  = sum(opp_hand_counts.values()) or 1
    opp_pcts   = [opp_hand_counts.get(r, 0) / opp_total * 100 for r in _ALL_RANKS]

    most_likely_opp     = max(opp_hand_counts, key=opp_hand_counts.get) if opp_hand_counts else HandRank.HIGH_CARD
    most_likely_opp_pct = opp_hand_counts.get(most_likely_opp, 0) / opp_total * 100

    winning_hands = [r for r in _ALL_RANKS if r > player_rank]
    beating_pct   = sum(opp_hand_counts.get(r, 0) for r in winning_hands) / opp_total * 100

    dec_color = {
        "raise": _CLR_RAISE, "call": _CLR_CALL, "fold": _CLR_FOLD
    }.get(decision, _TEXT)

    # ── Panel 1: Opponent hand distribution ───────────────────────────────────
    ax = _axes["opp"]
    colors1 = [
        _CLR_LOSS if r > player_rank else (_CLR_TIE if r == player_rank else _CLR_WIN)
        for r in _ALL_RANKS
    ]
    bars1 = ax.bar(_LABELS, opp_pcts, color=colors1, edgecolor="#21262d", linewidth=0.5)
    ax.axvline(x=proj_idx, color=_TEXT, linewidth=1.2, linestyle="--", alpha=0.7,
               label=f"Agent: {player_rank.name.replace('_',' ')}")
    _bar_pct_labels(ax, bars1, opp_pcts)
    _style_ax(ax,
              f"Opponent Hand Distribution — Round {round_num} | {street.upper()}",
              "% of simulated opp hands")
    ax.set_ylim(0, max(opp_pcts or [1]) * 1.35 + 2)
    ax.legend(
        handles=[
            mpatches.Patch(color=_CLR_WIN,  label="Agent wins"),
            mpatches.Patch(color=_CLR_TIE,  label="Tie"),
            mpatches.Patch(color=_CLR_LOSS, label="Opp wins"),
        ],
        facecolor=_BG_PANEL, labelcolor=_TEXT, fontsize=7, loc="upper right"
    )

    # ── Panel 2: Agent hand distribution ─────────────────────────────────────
    ax = _axes["agent"]
    if player_hand_counts and len(player_hand_counts) > 0:
        pl_total = sum(player_hand_counts.values()) or 1
        pl_pcts  = [player_hand_counts.get(r, 0) / pl_total * 100 for r in _ALL_RANKS]

        agent_colors = []
        for r in _ALL_RANKS:
            if current_rank and r == current_rank:
                agent_colors.append(_CLR_GOLD)
            elif r == player_rank:
                agent_colors.append(_CLR_BLUE)
            else:
                agent_colors.append("#2d333b")

        bars2 = ax.bar(_LABELS, pl_pcts, color=agent_colors, edgecolor="#21262d", linewidth=0.5)
        _bar_pct_labels(ax, bars2, pl_pcts)

        if cur_idx is not None:
            ax.axvline(x=cur_idx, color=_CLR_GOLD, linewidth=1.5, linestyle="--",
                       label=f"Now: {current_rank.name.replace('_',' ')}")
        ax.axvline(x=proj_idx, color=_CLR_BLUE, linewidth=1.5, linestyle=":",
                   label=f"Projected: {player_rank.name.replace('_',' ')}")
        ax.set_ylim(0, max(pl_pcts or [1]) * 1.35 + 2)
        ax.legend(facecolor=_BG_PANEL, labelcolor=_TEXT, fontsize=7, loc="upper right")
        _style_ax(ax, f"Agent Hand Distribution  ({' '.join(hole_cards)})\n{pl_total:,} board simulations",
                  "% of simulated boards")
    else:
        ax.set_facecolor(_BG_PANEL)
        ax.text(0.5, 0.5, "No simulation data\n(preflop)", transform=ax.transAxes,
                ha="center", va="center", color=_TEXT, fontsize=11)
        _style_ax(ax, f"Agent Hand Distribution  ({' '.join(hole_cards)})")

    # ── Panel 3: Opponent behavioral tracking ─────────────────────────────────
    ax = _axes["tracker"]
    ax.set_facecolor(_BG_PANEL)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)

    if opp_tracker_info and len(opp_tracker_info) > 0:
        names_t  = [t[0] for t in opp_tracker_info]
        scores   = [t[1] for t in opp_tracker_info]
        threats  = [t[2] for t in opp_tracker_info]

        bar_colors = []
        for score, threat in zip(scores, threats):
            if threat:
                bar_colors.append(_CLR_LOSS)
            elif score > 1.5:
                bar_colors.append("#d97706")
            elif score < 0.5:
                bar_colors.append(_CLR_WIN)
            else:
                bar_colors.append(_CLR_TIE)

        y_pos = range(len(names_t))
        bars3 = ax.barh(list(y_pos), scores, color=bar_colors, edgecolor="#21262d",
                        linewidth=0.6, height=0.55)

        # mark threatening opponents
        for i, (bar, threat, score) in enumerate(zip(bars3, threats, scores)):
            label = f"{score:.2f}"
            if threat:
                label += "  ⚠ STRONG"
            ax.text(max(score + 0.04, 0.1), i, label,
                    va="center", ha="left", fontsize=7.5, color=_TEXT)

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(names_t, fontsize=8, color=_TEXT)
        ax.axvline(x=1.0, color=_TEXT_DIM, linewidth=1.0, linestyle="--", alpha=0.6,
                   label="baseline (1.0)")
        ax.set_xlim(0, max(max(scores or [0]) * 1.4 + 0.3, 2.0))
        ax.set_xlabel("Aggression Score  (raises+bets) / (calls+1)", color=_TEXT_DIM, fontsize=7)
        ax.tick_params(colors=_TEXT, labelsize=7)
        ax.legend(facecolor=_BG_PANEL, labelcolor=_TEXT, fontsize=7, loc="lower right")
        ax.set_title("Opponent Behavioral Tracking", fontsize=9, pad=6, color=_TEXT, fontweight="bold")

        # legend for colors
        legend_handles = [
            mpatches.Patch(color=_CLR_LOSS, label="Showing strength ⚠"),
            mpatches.Patch(color="#d97706", label="Aggressive (>1.5)"),
            mpatches.Patch(color=_CLR_TIE,  label="Moderate"),
            mpatches.Patch(color=_CLR_WIN,  label="Passive (<0.5)"),
        ]
        ax.legend(handles=legend_handles, facecolor=_BG_PANEL, labelcolor=_TEXT,
                  fontsize=6.5, loc="lower right")
    else:
        ax.text(0.5, 0.5, "No opponent tracking data\n(tracker not active or no history)",
                transform=ax.transAxes, ha="center", va="center",
                color=_TEXT_DIM, fontsize=9)
        ax.set_title("Opponent Behavioral Tracking", fontsize=9, pad=6, color=_TEXT, fontweight="bold")

    # ── Panel 4: Win probability + pot dashboard ──────────────────────────────
    ax = _axes["gauge"]
    ax.set_facecolor(_BG_PANEL)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 4.5)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(colors=_TEXT, labelsize=7)
    ax.set_title("Win Probability & Pot Dashboard", fontsize=9, pad=6, color=_TEXT, fontweight="bold")

    # Row 0 — Win probability gauge
    ax.text(-1, 3.85, "WIN PROB", color=_TEXT_DIM, fontsize=7, va="center", ha="right")
    ax.barh([3.6], [100], height=0.45, color="#21262d", left=0)
    ax.barh([3.6], [win_pct], height=0.45, color=_win_color(win_pct), left=0)
    ax.text(win_pct + 0.5 if win_pct < 85 else win_pct - 0.5,
            3.6, f"{win_pct:.1f}%",
            ha="left" if win_pct < 85 else "right",
            va="center", fontsize=9, fontweight="bold", color=_TEXT)

    # Row 1 — Danger score gauge (red = high danger, green = low danger)
    _danger_clr = _CLR_LOSS if danger > 60 else _CLR_TIE if danger > 40 else _CLR_WIN
    ax.text(-1, 2.85, "DANGER", color=_TEXT_DIM, fontsize=7, va="center", ha="right")
    ax.barh([2.6], [100], height=0.45, color="#21262d", left=0)
    ax.barh([2.6], [danger], height=0.45, color=_danger_clr, left=0)
    ax.text(danger + 0.5 if danger < 85 else danger - 0.5,
            2.6, f"{danger:.1f}/100",
            ha="left" if danger < 85 else "right",
            va="center", fontsize=9, fontweight="bold", color=_danger_clr)

    # Row 2 — Pot equity (how much of pot is ours to claim)
    if pot_size + call_cost > 0:
        pot_equity_req = (call_cost / (pot_size + call_cost)) * 100 if call_cost > 0 else 0
        ax.text(-1, 1.85, "POT EQUITY\nREQUIRED", color=_TEXT_DIM, fontsize=7, va="center", ha="right")
        ax.barh([1.6], [100], height=0.45, color="#21262d", left=0)
        ax.barh([1.6], [pot_equity_req], height=0.45, color="#58a6ff", left=0)
        equity_ok = win_pct > pot_equity_req
        ax.text(pot_equity_req + 0.5, 1.6, f"{pot_equity_req:.1f}%",
                ha="left", va="center", fontsize=9, fontweight="bold", color=_CLR_BLUE)
        # reference line: where win_pct sits on the equity gauge
        ax.axvline(x=win_pct, ymin=0.28, ymax=0.58, color=_CLR_WIN if equity_ok else _CLR_LOSS,
                   linewidth=2, linestyle="--", label="Win% ref")

    # Row 3 — Stack vs pot ratio
    if agent_stack > 0:
        spr = pot_size / agent_stack * 100 if pot_size > 0 else 0
        spr_capped = min(spr, 100)
        ax.text(-1, 0.85, "POT/STACK\nRATIO %", color=_TEXT_DIM, fontsize=7, va="center", ha="right")
        ax.barh([0.6], [100], height=0.45, color="#21262d", left=0)
        ax.barh([0.6], [spr_capped], height=0.45, color="#8b949e", left=0)
        ax.text(spr_capped + 0.5, 0.6, f"{spr:.1f}%",
                ha="left", va="center", fontsize=9, color=_TEXT_DIM)

    ax.set_yticklabels([])
    ax.set_yticks([])

    # Pot / stack text summary below gauges
    summary = (
        f"Pot: ${pot_size:,}   Call: ${call_cost:,}   Stack: ${agent_stack:,}"
    )
    ax.text(50, -0.3, summary, ha="center", va="top", fontsize=7.5, color=_TEXT_DIM)

    # ── Panel 5: Info panel ───────────────────────────────────────────────────
    ax = _axes["info"]
    ax.set_facecolor(_BG_PANEL)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)
    ax.set_xticks([])
    ax.set_yticks([])

    def _section(ax, y, header):
        ax.text(0.05, y, header, transform=ax.transAxes,
                fontsize=7, color=_TEXT_DIM, va="top",
                fontweight="bold", fontstyle="italic")
        # draw a thin separator line in axes-fraction coords using a Line2D
        line = plt.Line2D([0.04, 0.96], [y - 0.018, y - 0.018],
                          transform=ax.transAxes, color=_BORDER, linewidth=0.5)
        ax.add_line(line)
        return y - 0.038

    def _row(ax, y, label, value, vcolor=_TEXT, bold=False):
        ax.text(0.05, y, f"{label}:", transform=ax.transAxes,
                fontsize=7, color=_TEXT_DIM, va="top")
        ax.text(0.98, y, value, transform=ax.transAxes,
                fontsize=8 if bold else 7.5, color=vcolor, va="top",
                ha="right", fontweight="bold" if bold else "normal")
        return y - 0.055

    def _wrap_text(ax, y, text, color=_TEXT, max_chars=24):
        words = text.split()
        line, lines = "", []
        for w in words:
            if len(line) + len(w) + 1 > max_chars:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            lines.append(line)
        for i, l in enumerate(lines):
            ax.text(0.05, y, l, transform=ax.transAxes,
                    fontsize=7.5 if i == 0 else 7, color=color, va="top",
                    fontweight="bold" if i == 0 else "normal")
            y -= 0.046
        return y - 0.008

    y = 0.98

    # Header
    ax.text(0.5, y, f"Round {round_num}  •  {street.upper()}", transform=ax.transAxes,
            fontsize=9, color=_TEXT, va="top", ha="center", fontweight="bold")
    y -= 0.06

    # ── Cards & hand ─────────────────────────────────────────────────────────
    y = _section(ax, y, "CARDS & HAND")
    y = _row(ax, y, "Hole",     " ".join(hole_cards))
    y = _row(ax, y, "Current",  (current_rank or player_rank).name.replace("_", " "), _CLR_GOLD, bold=True)
    y = _row(ax, y, "Projected",player_rank.name.replace("_", " "), _CLR_BLUE)
    y -= 0.01

    # ── Probability ───────────────────────────────────────────────────────────
    y = _section(ax, y, "PROBABILITY")
    y = _row(ax, y, "Win Prob", f"{win_pct:.1f}%", _win_color(win_pct), bold=True)
    y = _row(ax, y, "Danger",   f"{danger:.1f}/100",
             _CLR_LOSS if danger > 60 else _CLR_TIE if danger > 40 else _CLR_WIN)
    y = _row(ax, y, "Opp best", f"{most_likely_opp.name.replace('_',' ')} ({most_likely_opp_pct:.1f}%)",
             "#ff9999")
    y = _row(ax, y, "Opp beats",f"{beating_pct:.1f}% of sims", _CLR_LOSS if beating_pct > 40 else _TEXT)
    y -= 0.01

    # ── Stack & pot ───────────────────────────────────────────────────────────
    y = _section(ax, y, "STACK & POT")
    y = _row(ax, y, "Agent stack", f"${agent_stack:,}", _CLR_GOLD, bold=True)
    y = _row(ax, y, "Pot size",    f"${pot_size:,}", _TEXT)
    y = _row(ax, y, "Call cost",   f"${call_cost:,}", _TEXT)
    if pot_size + call_cost > 0 and call_cost > 0:
        pot_eq = call_cost / (pot_size + call_cost) * 100
        eq_ok  = win_pct > pot_eq
        y = _row(ax, y, "Pot equity",
                 f"{pot_eq:.1f}% ({'✓ favourable' if eq_ok else '✗ unfavourable'})",
                 _CLR_WIN if eq_ok else _CLR_LOSS)
    y -= 0.01

    # ── Opponent tracking ─────────────────────────────────────────────────────
    y = _section(ax, y, "OPPONENT TRACKING")
    if opp_tracker_info:
        any_threat = any(t[2] for t in opp_tracker_info)
        max_agg    = max(t[1] for t in opp_tracker_info)
        y = _row(ax, y, "Max aggression", f"{max_agg:.2f}",
                 _CLR_LOSS if max_agg > 1.5 else _CLR_TIE if max_agg > 0.5 else _CLR_WIN)
        y = _row(ax, y, "Threat active",
                 "YES — tighten up" if any_threat else "No",
                 _CLR_LOSS if any_threat else _CLR_WIN)
        for name, score, threat in opp_tracker_info:
            label = f"● {name[:12]}"
            val   = f"{score:.2f}{'  ⚠' if threat else ''}"
            y = _row(ax, y, label, val, _CLR_LOSS if threat else (_CLR_TIE if score > 1.0 else _CLR_WIN))
    else:
        ax.text(0.05, y, "  (no tracker data)", transform=ax.transAxes,
                fontsize=7, color=_TEXT_DIM, va="top")
        y -= 0.05
    y -= 0.01

    # ── Decision ─────────────────────────────────────────────────────────────
    y = _section(ax, y, "DECISION")
    y = _row(ax, y, "Action", decision.upper(), dec_color, bold=True)
    ax.text(0.05, y, "Reason:", transform=ax.transAxes,
            fontsize=7, color=_TEXT_DIM, va="top")
    y -= 0.046
    y = _wrap_text(ax, y, decision_reason, color=_TEXT)

    plt.pause(0.001)
