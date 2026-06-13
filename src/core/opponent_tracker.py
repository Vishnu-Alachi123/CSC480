from collections import defaultdict


class OpponentTracker:
    # keeps track of how each opponent has been playing across multiple hands. stores every
    # action per street and uses it to compute an aggression score (raises+bets / calls+1)
    # and a "showing strength" flag that fires when someone raised preflop and continued on
    # the flop. that combo usually means a real hand or a committed bluff either way.

    def __init__(self):
        # current_hand tracks actions in the current round only, cleared each hand
        self.current_hand = defaultdict(list)

        # stats accumulates lifetime data for each opponent UUID
        self.stats = defaultdict(lambda: {
            "hands_seen": 0,
            "folds": 0,
            "calls": 0,
            "raises": 0,
            "bets": 0,
            "total_raise_amount": 0,
        })

    def new_round(self):
        self.current_hand.clear()

    def record_action(self, action: dict, round_state: dict):
        # pulls uuid, action type, amount, and street out of the dicts pypokerengine passes around
        player_uuid = action.get("player_uuid")
        action_type = action.get("action")
        amount      = action.get("amount", 0)
        street      = round_state.get("street", "unknown")

        if player_uuid is None:
            return

        self.current_hand[player_uuid].append({
            "street": street,
            "action": action_type,
            "amount": amount,
        })

        # update lifetime stats
        if action_type == "fold":
            self.stats[player_uuid]["folds"] += 1
        elif action_type == "call":
            self.stats[player_uuid]["calls"] += 1
        elif action_type == "raise":
            self.stats[player_uuid]["raises"] += 1
            self.stats[player_uuid]["total_raise_amount"] += amount
        elif action_type == "bet":
            self.stats[player_uuid]["bets"] += 1

    def is_showing_strength_this_hand(self, player_uuid: str) -> bool:
        # true if this player raised preflop and then bet or raised on the flop.
        # that usually means a real hand or a committed bluff, either way we want
        # to play cautiously against them.
        actions = self.current_hand[player_uuid]

        raised_preflop  = any(a["street"] == "preflop" and a["action"] == "raise" for a in actions)
        aggressive_flop = any(a["street"] == "flop"    and a["action"] in ("bet", "raise") for a in actions)

        return raised_preflop and aggressive_flop

    def finish_round(self, player_uuids: list):
        for uuid in player_uuids:
            self.stats[uuid]["hands_seen"] += 1

    def aggression_score(self, player_uuid: str) -> float:
        # (raises + bets) / (calls + 1). above ~1.5 is aggressive, below ~0.5 is passive.
        # the +1 just prevents dividing by zero for players who haven't called yet.
        s = self.stats[player_uuid]
        aggressive_actions = s["raises"] + s["bets"]
        passive_actions    = s["calls"] + 1   # +1 so we never divide by zero
        return aggressive_actions / passive_actions
