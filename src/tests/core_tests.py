import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from card import Card, Rank, Suit
from hand_evaluator import (
    is_straight, is_flush, is_pair, is_two_pair,
    is_three_of_a_kind, is_full_house, is_four_of_a_kind,
    is_straight_flush, is_royal_flush, evaluate, HandRank
)
# ── Helpers to build hands quickly ──────────────────────────────────────────

def make_hand(*args):
    """make_hand((Rank.ACE, Suit.SPADES), ...) -> list[Card]"""
    return [Card(rank, suit) for rank, suit in args]

# ── is_straight ──────────────────────────────────────────────────────────────

def test_straight_normal():
    hand = make_hand(
        (Rank.FIVE, Suit.HEARTS),
        (Rank.SIX, Suit.SPADES),
        (Rank.SEVEN, Suit.DIAMONDS),
        (Rank.EIGHT, Suit.CLUBS),
        (Rank.NINE, Suit.HEARTS),
    )
    assert is_straight(hand) == True

def test_straight_wheel():
    # A-2-3-4-5
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.TWO, Suit.HEARTS),
        (Rank.THREE, Suit.DIAMONDS),
        (Rank.FOUR, Suit.CLUBS),
        (Rank.FIVE, Suit.SPADES),
    )
    assert is_straight(hand) == True

def test_straight_false():
    hand = make_hand(
        (Rank.TWO, Suit.SPADES),
        (Rank.THREE, Suit.HEARTS),
        (Rank.FOUR, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),   # gap — not consecutive
    )
    assert is_straight(hand) == False

# ── is_flush ─────────────────────────────────────────────────────────────────

def test_flush_true():
    hand = make_hand(
        (Rank.TWO, Suit.HEARTS),
        (Rank.FIVE, Suit.HEARTS),
        (Rank.SEVEN, Suit.HEARTS),
        (Rank.NINE, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS),
    )
    assert is_flush(hand) == True

def test_flush_false():
    hand = make_hand(
        (Rank.TWO, Suit.HEARTS),
        (Rank.FIVE, Suit.HEARTS),
        (Rank.SEVEN, Suit.SPADES),   # different suit
        (Rank.NINE, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS),
    )
    assert is_flush(hand) == False

# ── is_pair ───────────────────────────────────────────────────────────────────

def test_pair_true():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.THREE, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_pair(hand) == True

def test_pair_false():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.KING, Suit.HEARTS),
        (Rank.THREE, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_pair(hand) == False

# ── is_two_pair ───────────────────────────────────────────────────────────────

def test_two_pair_true():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.KING, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_two_pair(hand) == True

def test_two_pair_false():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_two_pair(hand) == False

# ── is_three_of_a_kind ────────────────────────────────────────────────────────

def test_three_of_a_kind_true():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_three_of_a_kind(hand) == True

def test_three_of_a_kind_false():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_three_of_a_kind(hand) == False

# ── is_full_house ─────────────────────────────────────────────────────────────

def test_full_house_true():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.KING, Suit.CLUBS),
        (Rank.KING, Suit.SPADES),
    )
    assert is_full_house(hand) == True

def test_full_house_false():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.KING, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),   # three of a kind, not full house
    )
    assert is_full_house(hand) == False

# ── is_four_of_a_kind ─────────────────────────────────────────────────────────

def test_four_of_a_kind_true():
    hand = make_hand(
        (Rank.ACE, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.ACE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert is_four_of_a_kind(hand) == True

# ── is_straight_flush & is_royal_flush ───────────────────────────────────────

def test_straight_flush_true():
    hand = make_hand(
        (Rank.FIVE, Suit.HEARTS),
        (Rank.SIX, Suit.HEARTS),
        (Rank.SEVEN, Suit.HEARTS),
        (Rank.EIGHT, Suit.HEARTS),
        (Rank.NINE, Suit.HEARTS),
    )
    assert is_straight_flush(hand) == True

def test_royal_flush_true():
    hand = make_hand(
        (Rank.TEN, Suit.SPADES),
        (Rank.JACK, Suit.SPADES),
        (Rank.QUEEN, Suit.SPADES),
        (Rank.KING, Suit.SPADES),
        (Rank.ACE, Suit.SPADES),
    )
    assert is_royal_flush(hand) == True

# ── evaluate ──────────────────────────────────────────────────────────────────

def test_evaluate_returns_correct_rank():
    royal = make_hand(
        (Rank.TEN, Suit.SPADES), (Rank.JACK, Suit.SPADES),
        (Rank.QUEEN, Suit.SPADES), (Rank.KING, Suit.SPADES),
        (Rank.ACE, Suit.SPADES),
    )
    assert evaluate(royal) == HandRank.ROYAL_FLUSH

    pair = make_hand(
        (Rank.ACE, Suit.SPADES), (Rank.ACE, Suit.HEARTS),
        (Rank.THREE, Suit.DIAMONDS), (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.SPADES),
    )
    assert evaluate(pair) == HandRank.PAIR

# ── Run all tests ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")