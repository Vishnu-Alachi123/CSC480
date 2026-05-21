from collections import defaultdict

class OpponentTracker:
    def __init__(self) -> None:
        self.current_hand = defaultdict(list)
        self.stats = defaultdict(lambda: {
            "hands_seen:": 0,
            "folds": 0,
            "calls": 0,
            "raises": 0,
            "bets": 0,
            "total_raise_amount": 0,

        })

    #new round starts, so clear current hand
    def new_round(self):
        self.current_hand.clear()

    def record_action(self, action: dict, round_state: dict):
        player = action.get("player_uuid")
        act = action.get("action")
        amount = action.get("amount", 0)
        street = round_state.get("street", "unknown")

        if player is None:
            return
        
        self.current_hand[player].append({
            "street": street,
            "action": act,
            "amount": amount,
        })

        if act == "fold":
            self.stats[player]["folds"] += 1
        elif act == "call":
            self.stats[player]["calls"] += 1
        elif act == "raise":
            self.stats[player]["raises"] += 1
            self.stats[player]["total_raise_amount"] += amount
        elif act == "bet":
            self.stats[player]["bets"] += 1

    def is_showing_strength_this_hand(self, player):
        actions = self.current_hand[player]

        raised_preflop = any(
        a["street"] == "preflop" and a["action"] == "raise"
        for a in actions
    )

        bet_or_raised_flop = any(
        a["street"] == "flop" and a["action"] in ["bet", "raise"]
        for a in actions
    )

        return raised_preflop and bet_or_raised_flop

    def finish_round(self, players):
        for p in players:
            self.stats[p]["hands_seen"] += 1

    def aggression_score(self, player):
        s = self.stats[player]
        passive = s["calls"] + 1
        aggressive = s["raises"] + s["bets"]
        return aggressive / passive

            