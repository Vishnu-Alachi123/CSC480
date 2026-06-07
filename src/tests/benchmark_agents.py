"""
benchmark_agents.py — run all agents against each other and plot results.

Modes:
  simple    — 3-way: StupidAgent vs CallAgent vs PokerAgent (quick sanity check)
  ablation  — all 10 agents, shows how each feature contributes
  all       — alias for ablation

Usage:
  python src/tests/benchmark_agents.py                  # simple, 30 games
  python src/tests/benchmark_agents.py ablation 50     # 10-agent ablation, 50 games
  python src/tests/benchmark_agents.py all 50          # same as ablation
"""

import os
import sys
from statistics import mean

import matplotlib
matplotlib.use("Agg")   # non-interactive backend so plots render without a display
import matplotlib.pyplot as plt
from pypokerengine.api.game import setup_config, start_poker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agent.call_agent          import CallAgent
from src.agent.stupid_agent        import StupidAgent
from src.agent.threshold_agent     import ThresholdAgent
from src.agent.mc_simple_agent     import MCSimpleAgent
from src.agent.mc_opp_agent        import MCOppAgent
from src.agent.mc_besthand_agent   import MCBestHandAgent
from src.agent.opponent_agent      import OpponentAgent
from src.agent.mc_tracker_agent    import MCTrackerAgent
from src.agent.mc_danger_agent     import MCDangerAgent
from src.agent.poker_agent         import PokerAgent

# ── Color palette — each agent gets a unique color ───────────────────────────
AGENT_COLORS = {
    "StupidAgent":     "#7f8c8d",   # gray         (baseline)
    "CallAgent":       "#2ecc71",   # green        (baseline)
    "ThresholdAgent":  "#3498db",   # blue         (1: hand rank)
    "MCSimpleAgent":   "#9b59b6",   # purple       (2: MC own hand)
    "MCOppAgent":      "#e67e22",   # orange       (3: MC + opponents)
    "MCBestHandAgent": "#e74c3c",   # red          (4: kicker-aware MC)
    "OpponentAgent":   "#1abc9c",   # teal         (tracker, no MC)
    "MCTrackerAgent":  "#f39c12",   # amber        (5: MC + tracker)
    "MCDangerAgent":   "#d35400",   # burnt orange (6: MC + danger)
    "PokerAgent":      "#c0392b",   # dark red     (7: everything)
}

# ── Which agents have a verbose flag to suppress ──────────────────────────────
_VERBOSE_CLASSES = [MCTrackerAgent, PokerAgent]


def _silence():
    for cls in _VERBOSE_CLASSES:
        cls.verbose = False


def _unsilence():
    for cls in _VERBOSE_CLASSES:
        cls.verbose = True


def _make_agents(mode="simple"):
    """Return {name: instance} for the chosen mode."""
    if mode == "simple":
        return {
            "StupidAgent": StupidAgent(),
            "CallAgent":   CallAgent(),
            "PokerAgent":  PokerAgent(),
        }
    # ablation / all: full 10-agent progression
    return {
        "StupidAgent":     StupidAgent(),
        "CallAgent":       CallAgent(),
        "ThresholdAgent":  ThresholdAgent(),
        "MCSimpleAgent":   MCSimpleAgent(),
        "MCOppAgent":      MCOppAgent(),
        "MCBestHandAgent": MCBestHandAgent(),
        "OpponentAgent":   OpponentAgent(),
        "MCTrackerAgent":  MCTrackerAgent(),
        "MCDangerAgent":   MCDangerAgent(),
        "PokerAgent":      PokerAgent(),
    }


def make_config(agents: dict, max_rounds=20, initial_stack=1000, small_blind=10):
    config = setup_config(
        max_round=max_rounds,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )
    for name, algo in agents.items():
        config.register_player(name=name, algorithm=algo)
    return config


def run_game(config):
    result = start_poker(config, verbose=0)
    return {player["name"]: player["stack"] for player in result["players"]}


def benchmark(num_games=30, mode="simple"):
    initial_stack = 1000
    _silence()

    agent_names  = list(_make_agents(mode).keys())
    game_results = {n: [] for n in agent_names}
    win_counts   = {n: 0  for n in agent_names}

    max_rounds = 15 if mode in ("ablation", "all") else 20

    for game_index in range(1, num_games + 1):
        agents = _make_agents(mode)
        config = make_config(agents, max_rounds=max_rounds, initial_stack=initial_stack, small_blind=10)
        stacks = run_game(config)

        for name, stack in stacks.items():
            game_results[name].append(stack - initial_stack)

        winner = max(stacks, key=stacks.get)
        win_counts[winner] += 1

        if game_index % 10 == 0:
            print(f"  Completed {game_index}/{num_games} games")

    _unsilence()
    return game_results, win_counts


def plot_results(game_results, win_counts, mode="simple"):
    names      = list(game_results.keys())
    profits    = [game_results[n] for n in names]
    num_games  = len(profits[0])
    num_agents = len(names)

    # ablation mode: wider figure to fit all agents
    fig_w = 20 if num_agents > 5 else 16
    fig, axes = plt.subplots(1, 3, figsize=(fig_w, 6))
    fig.suptitle(
        f"Benchmark — {num_games} games, {num_agents} agents",
        fontsize=13, fontweight="bold"
    )

    # ── Subplot 1: Cumulative profit ──────────────────────────────────────────
    ax = axes[0]
    for name in names:
        cum   = [0]
        total = 0
        for p in game_results[name]:
            total += p
            cum.append(total)
        ax.plot(range(0, num_games + 1), cum, marker="o", markersize=2,
                label=name, color=AGENT_COLORS.get(name, "gray"))
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Cumulative Profit")
    ax.set_xlabel("Game #")
    ax.set_ylabel("Total Profit (chips)")
    ax.legend(fontsize=7 if num_agents > 5 else 9)

    # ── Subplot 2: Per-game profit distribution ───────────────────────────────
    ax = axes[1]
    bp = ax.boxplot(profits, tick_labels=names, showmeans=True, patch_artist=True)
    for patch, name in zip(bp["boxes"], names):
        patch.set_facecolor(AGENT_COLORS.get(name, "gray"))
        patch.set_alpha(0.6)
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Per-Game Profit Distribution")
    ax.set_ylabel("Profit (chips)")
    ax.tick_params(axis="x", rotation=35, labelsize=7 if num_agents > 5 else 9)

    # ── Subplot 3: Win rate ───────────────────────────────────────────────────
    ax = axes[2]
    rates = [win_counts[n] / num_games * 100 for n in names]
    bars  = ax.bar(names, rates, color=[AGENT_COLORS.get(n, "gray") for n in names])
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{rate:.1f}%", ha="center", va="bottom",
                fontsize=7 if num_agents > 5 else 9)
    ax.set_ylim(0, 100)
    baseline = 100 / num_agents
    ax.axhline(y=baseline, color="gray", linewidth=0.8, linestyle="--",
               label=f"random ({baseline:.0f}%)")
    ax.set_title("Win Rate")
    ax.set_ylabel("Win Rate (%)")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=35, labelsize=7 if num_agents > 5 else 9)

    plt.tight_layout()
    out = f"benchmark_results_{mode}.png"
    plt.savefig(out, dpi=120)
    print(f"Saved {out}")
    plt.show()


def print_summary(game_results, win_counts):
    num_games = len(next(iter(game_results.values())))
    print(f"\n{'='*68}")
    print(f"Benchmark summary ({num_games} games)")
    print(f"{'='*68}")
    # sort by avg profit descending
    ranked = sorted(game_results.items(), key=lambda kv: mean(kv[1]), reverse=True)
    for name, profits in ranked:
        wr = win_counts[name] / num_games * 100
        print(
            f"{name:18s}  avg={mean(profits):+7.1f}  "
            f"best={max(profits):+6.0f}  worst={min(profits):+6.0f}  "
            f"win_rate={wr:.1f}%"
        )


if __name__ == "__main__":
    args  = sys.argv[1:]
    mode  = "ablation" if any(a in ("all", "ablation") for a in args) else "simple"
    games = next((int(a) for a in args if a.isdigit()), 30)

    print(f"Running {games} games in {mode!r} mode ...")
    results, wins = benchmark(num_games=games, mode=mode)
    print_summary(results, wins)
    plot_results(results, wins, mode=mode)
