import os
import sys
from statistics import mean

import matplotlib.pyplot as plt
from pypokerengine.api.game import setup_config, start_poker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agent.call_agent import CallAgent
from src.agent.stupid_agent import StupidAgent
from src.agent.base_agent import SimpleAgent

AGENT_COLORS = {
    "StupidAgent": "#4c72b0",
    "CallAgent":   "#55a868",
    "SimpleAgent": "#c44e52",
}


def make_config(max_rounds=20, initial_stack=1000, small_blind=10):
    config = setup_config(
        max_round=max_rounds,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )
    config.register_player(name="StupidAgent", algorithm=StupidAgent())
    config.register_player(name="CallAgent", algorithm=CallAgent())
    config.register_player(name="SimpleAgent", algorithm=SimpleAgent())
    return config


def run_game(config):
    result = start_poker(config, verbose=0)
    return {player["name"]: player["stack"] for player in result["players"]}


def benchmark(num_games=30):
    initial_stack = 1000
    # disable per-decision prints and matplotlib plots during benchmark
    SimpleAgent.verbose = False

    game_results = {"StupidAgent": [], "CallAgent": [], "SimpleAgent": []}
    win_counts   = {"StupidAgent": 0,  "CallAgent": 0,  "SimpleAgent": 0}

    for game_index in range(1, num_games + 1):
        config = make_config(max_rounds=20, initial_stack=initial_stack, small_blind=10)
        stacks = run_game(config)

        for name, stack in stacks.items():
            game_results[name].append(stack - initial_stack)

        winner = max(stacks, key=stacks.get)
        win_counts[winner] += 1

        if game_index % 10 == 0:
            print(f"Completed {game_index}/{num_games} games")

    SimpleAgent.verbose = True
    return game_results, win_counts


def plot_results(game_results, win_counts):
    names = list(game_results.keys())
    profits = [game_results[name] for name in names]
    num_games = len(profits[0])

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(f"Benchmark Results — {num_games} games", fontsize=13, fontweight="bold")

    # ── Subplot 1: Cumulative profit ──────────────────────────────────────────
    ax = axes[0]
    for name in names:
        cum = [0]   # anchor: all agents start at 0 profit before game 1
        total = 0
        for p in game_results[name]:
            total += p
            cum.append(total)
        ax.plot(range(0, num_games + 1), cum, marker="o", markersize=3,
                label=name, color=AGENT_COLORS.get(name))
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Cumulative Profit Over Games")
    ax.set_xlabel("Game #")
    ax.set_ylabel("Total Profit (chips)")
    ax.legend()

    # ── Subplot 2: Per-game profit distribution (box plot) ────────────────────
    ax = axes[1]
    bp = ax.boxplot(profits, labels=names, showmeans=True, patch_artist=True)
    for patch, name in zip(bp["boxes"], names):
        patch.set_facecolor(AGENT_COLORS.get(name, "gray"))
        patch.set_alpha(0.6)
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Per-Game Profit Distribution")
    ax.set_ylabel("Profit (chips)")

    # ── Subplot 3: Win rate ───────────────────────────────────────────────────
    ax = axes[2]
    rates = [win_counts[name] / num_games * 100 for name in names]
    bars = ax.bar(names, rates, color=[AGENT_COLORS.get(n, "gray") for n in names])
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{rate:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 100)
    ax.axhline(y=100 / len(names), color="gray", linewidth=0.8, linestyle="--",
               label=f"random baseline ({100/len(names):.0f}%)")
    ax.set_title("Win Rate")
    ax.set_ylabel("Win Rate (%)")
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig("benchmark_results.png", dpi=120)
    print("Saved benchmark_results.png")
    plt.show()


def print_summary(game_results, win_counts):
    num_games = len(next(iter(game_results.values())))
    print(f"\n{'='*55}")
    print(f"Benchmark summary ({num_games} games)")
    print(f"{'='*55}")
    for name, profits in game_results.items():
        wr = win_counts[name] / num_games * 100
        print(
            f"{name:12s}  avg={mean(profits):+7.1f}  "
            f"best={max(profits):+6.0f}  worst={min(profits):+6.0f}  "
            f"win_rate={wr:.1f}%"
        )


if __name__ == "__main__":
    games = 30
    results, wins = benchmark(num_games=games)
    print_summary(results, wins)
    plot_results(results, wins)
