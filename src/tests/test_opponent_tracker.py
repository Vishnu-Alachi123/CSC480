from src.core.opponent_tracker import OpponentTracker

def test_tracks_preflop_raise_and_flop_bet():
    tracker = OpponentTracker()

    player = "player_1"

    tracker.record_action(
        {"player_uuid": player, "action": "raise", "amount": 50},
        {"street": "preflop"}
    )

    tracker.record_action(
        {"player_uuid": player, "action": "raise", "amount": 100},
        {"street": "flop"}
    )

    assert tracker.is_showing_strength_this_hand(player) == True

def test_does_not_show_strength_without_flop_bet():
    tracker = OpponentTracker()

    player = "player_1"

    tracker.record_action(
        {"player_uuid": player, "action": "raise", "amount": 50},
        {"street": "preflop"}
    )

    assert tracker.is_showing_strength_this_hand(player) == False

def test_aggression_score():
    tracker = OpponentTracker()

    player = "player_1"

    tracker.record_action(
        {"player_uuid": player, "action": "raise", "amount": 50},
        {"street": "preflop"}
    )

    tracker.record_action(
        {"player_uuid": player, "action": "call", "amount": 50},
        {"street": "flop"}
    )

    assert tracker.aggression_score(player) == 0.5