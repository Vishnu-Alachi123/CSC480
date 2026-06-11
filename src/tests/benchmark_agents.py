"""
benchmark_agents.py

Runs all agents against each other and plots the results.

Two modes:
  simple — 3-way: StupidAgent vs CallAgent vs PokerAgent 
  combination — all 9 agents showing how each feature contributes

  python -m src.tests.benchmark_agents
  python -m src.tests.benchmark_agents combination 50
"""

import os, sys
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pypokerengine.api.game import setup_config, start_poker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agent.call_agent import CallAgent
from src.agent.stupid_agent import StupidAgent
from src.agent.hand_rank_agent import HandRankAgent
from src.agent.mc_hand_agent import MCHandAgent
from src.agent.mc_opponent_agent import MCOpponentAgent
from src.agent.behavior_agent import BehaviorAgent
from src.agent.mc_behavior_agent import MCBehaviorAgent
from src.agent.mc_danger_agent import MCDangerAgent
from src.agent.poker_agent import PokerAgent

AGENT_COLORS = {
    "StupidAgent": "#7f8c8d",
    "CallAgent": "#2ecc71",
    "HandRankAgent": "#3498db",
    "MCHandAgent": "#9b59b6",
    "MCOpponentAgent": "#e67e22",
    "BehaviorAgent": "#1abc9c",
    "MCBehaviorAgent": "#f39c12",
    "MCDangerAgent": "#d35400",
    "PokerAgent": "#c0392b",
}

VERBOSE_AGENT_CLASSES = [MCBehaviorAgent, PokerAgent]


def silence_agents():
    for cls in VERBOSE_AGENT_CLASSES:
        cls.verbose = False


def restore_verbose():
    for cls in VERBOSE_AGENT_CLASSES:
        cls.verbose = True


def build_agent_set(mode):
    if mode == "simple":
        return {
            "StupidAgent": StupidAgent(),
            "CallAgent": CallAgent(),
            "PokerAgent": PokerAgent(),
        }
    if mode == "components":
        return {
            "HandRankAgent": HandRankAgent(),
            "MCOpponentAgent": MCOpponentAgent(),
            "BehaviorAgent": BehaviorAgent(),
            "PokerAgent": PokerAgent(),
        }
    if mode == "top":
        return {
            "PokerAgent": PokerAgent(),
            "MCOpponentAgent": MCOpponentAgent(),
            "MCDangerAgent": MCDangerAgent(),
            "BehaviorAgent": BehaviorAgent(),
        }
    # combination — all 9 agents
    return {
        "StupidAgent": StupidAgent(),
        "CallAgent": CallAgent(),
        "HandRankAgent": HandRankAgent(),
        "MCHandAgent": MCHandAgent(),
        "MCOpponentAgent": MCOpponentAgent(),
        "BehaviorAgent": BehaviorAgent(),
        "MCBehaviorAgent": MCBehaviorAgent(),
        "MCDangerAgent": MCDangerAgent(),
        "PokerAgent": PokerAgent(),
    }


def setup_game(agents, max_rounds, initial_stack, small_blind):
    config = setup_config(max_round=max_rounds, initial_stack=initial_stack, small_blind_amount=small_blind)
    for name, agent in agents.items():
        config.register_player(name=name, algorithm=agent)
    return config


def run_single_game(config):
    result = start_poker(config, verbose=0)
    return {player["name"]: player["stack"] for player in result["players"]}


def benchmark(num_games=30, mode="simple"):
    initial_stack = 1000
    max_rounds = 15 if mode in ("combination", "all") else 20

    silence_agents()

    agent_names = list(build_agent_set(mode).keys())
    profit_log = {name: [] for name in agent_names}
    win_counts = {name: 0 for name in agent_names}

    for game_num in range(1, num_games + 1):
        agents = build_agent_set(mode)
        config = setup_game(agents, max_rounds, initial_stack, small_blind=10)
        final_stacks = run_single_game(config)

        for name, stack in final_stacks.items():
            profit_log[name].append(stack - initial_stack)

        winner = max(final_stacks, key=final_stacks.get)
        win_counts[winner] += 1

        if game_num % 10 == 0:
            print(f"  Completed {game_num}/{num_games} games")

    restore_verbose()
    return profit_log, win_counts


def plot_results(profit_log, win_counts, mode="simple"):
    agent_names = list(profit_log.keys())
    profit_data = [profit_log[n] for n in agent_names]
    num_games = len(profit_data[0])
    num_agents = len(agent_names)

    fig_width = 20 if num_agents > 5 else 16
    fig, axes = plt.subplots(1, 3, figsize=(fig_width, 6))
    fig.suptitle(f"Benchmark — {num_games} games, {num_agents} agents", fontsize=13, fontweight="bold")

    ax = axes[0]
    for name in agent_names:
        running_total = 0
        cumulative = [0]
        for profit in profit_log[name]:
            running_total += profit
            cumulative.append(running_total)
        ax.plot(range(0, num_games + 1), cumulative, marker="o", markersize=2,
                label=name, color=AGENT_COLORS.get(name, "gray"))
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Cumulative Profit")
    ax.set_xlabel("Game #")
    ax.set_ylabel("Total Profit (chips)")
    ax.legend(fontsize=7 if num_agents > 5 else 9)

    ax = axes[1]
    bp = ax.boxplot(profit_data, tick_labels=agent_names, showmeans=True, patch_artist=True)
    for patch, name in zip(bp["boxes"], agent_names):
        patch.set_facecolor(AGENT_COLORS.get(name, "gray"))
        patch.set_alpha(0.6)
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_title("Per-Game Profit Distribution")
    ax.set_ylabel("Profit (chips)")
    ax.tick_params(axis="x", rotation=35, labelsize=7 if num_agents > 5 else 9)

    ax = axes[2]
    win_rates = [win_counts[n] / num_games * 100 for n in agent_names]
    bars = ax.bar(agent_names, win_rates, color=[AGENT_COLORS.get(n, "gray") for n in agent_names])
    for bar, rate in zip(bars, win_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{rate:.1f}%", ha="center", va="bottom", fontsize=7 if num_agents > 5 else 9)
    ax.set_ylim(0, 100)
    baseline = 100 / num_agents
    ax.axhline(y=baseline, color="gray", linewidth=0.8, linestyle="--", label=f"random ({baseline:.0f}%)")
    ax.set_title("Win Rate")
    ax.set_ylabel("Win Rate (%)")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=35, labelsize=7 if num_agents > 5 else 9)

    plt.tight_layout()
    out = f"benchmark_results_{mode}.png"
    plt.savefig(out, dpi=120)
    print(f"Saved {out}")
    plt.show()


def print_summary(profit_log, win_counts):
    num_games = len(next(iter(profit_log.values())))
    print(f"\n{'='*68}")
    print(f"Benchmark summary ({num_games} games)")
    print(f"{'='*68}")
    ranked = sorted(profit_log.items(), key=lambda kv: mean(kv[1]), reverse=True)
    for name, profits in ranked:
        win_rate = win_counts[name] / num_games * 100
        print(f"{name:20s}  avg={mean(profits):+7.1f}  best={max(profits):+6.0f}  worst={min(profits):+6.0f}  win_rate={win_rate:.1f}%")


if __name__ == "__main__":
    args = sys.argv[1:]
    if any(a in ("all", "combination") for a in args):
        mode = "combination"
    elif "components" in args:
        mode = "components"
    elif "top" in args:
        mode = "top"
    else:
        mode = "simple"
    games = next((int(a) for a in args if a.isdigit()), 30)

    print(f"Running {games} games in '{mode}' mode ...")
    results, wins = benchmark(num_games=games, mode=mode)
    print_summary(results, wins)
    plot_results(results, wins, mode=mode)
