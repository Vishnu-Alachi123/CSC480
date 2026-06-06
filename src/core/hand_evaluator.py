from enum import IntEnum
from src.core.card import Card


class HandRank(IntEnum):
    HIGH_CARD       = 1
    PAIR            = 2
    TWO_PAIR        = 3
    THREE_OF_A_KIND = 4
    STRAIGHT        = 5
    FLUSH           = 6
    FULL_HOUSE      = 7
    FOUR_OF_A_KIND  = 8
    STRAIGHT_FLUSH  = 9
    ROYAL_FLUSH     = 10


# Ace-low straight rank set (wheel)
_WHEEL = frozenset({14, 2, 3, 4, 5})


def evaluate(cards: list[Card]) -> HandRank:
    """
    Evaluate a 5-card hand in a single pass.
    Computes flush, straight, and rank counts once, then maps to HandRank.
    """
    ranks = [card.rank.value for card in cards]
    suits = [card.suit for card in cards]

    # flush: all suits identical 
    flush = len(set(suits)) == 1

    # straight: sort unique ranks, check consecutive window or wheel 
    unique_ranks = sorted(set(ranks))
    straight = (
        (len(unique_ranks) == 5 and unique_ranks[-1] - unique_ranks[0] == 4)
        or _WHEEL.issubset(unique_ranks)
    )

    # rank counts: build once 
    counts: dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    freq = counts.values()

    has4 = 4 in freq
    has3 = 3 in freq
    pairs = sum(1 for v in freq if v == 2)

    # evaluate in priority order
    if flush and straight:
        if frozenset(ranks) == frozenset({10, 11, 12, 13, 14}):
            return HandRank.ROYAL_FLUSH
        return HandRank.STRAIGHT_FLUSH

    if has4:
        return HandRank.FOUR_OF_A_KIND

    if has3 and pairs == 1:
        return HandRank.FULL_HOUSE

    if flush:
        return HandRank.FLUSH

    if straight:
        return HandRank.STRAIGHT

    if has3:
        return HandRank.THREE_OF_A_KIND

    if pairs == 2:
        return HandRank.TWO_PAIR

    if pairs == 1:
        return HandRank.PAIR

    return HandRank.HIGH_CARD