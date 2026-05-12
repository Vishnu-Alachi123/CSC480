from dataclasses import dataclass
from enum import IntEnum, Enum  
from itertools import combinations
from src.core.card import Card, Rank, Suit

class HandRank(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10 

def is_straight(cards: list[Card]) -> bool:

    ranks = sorted(set(card.rank.value for card in cards))

    for i in range (len(ranks) - 4): 
        window = ranks[i: i+5]
        if window[-1] - window[0] == 4: 
            return True
        
    if {14,2,3,4,5}.issubset(set(ranks)):
        return True

    else:
        return False

def is_flush(cards: list[Card]) -> bool:
    flush = True
    suit = None
    for card in cards:
        if suit == None:
            suit = card.suit
        elif card.suit != suit:
            flush = False
            return flush
        else:
            continue

    return flush

def get_rank_count(cards : list[Card]) -> dict:
    count = {}
    for card in cards:
        count[card.rank.value] = count.get(card.rank.value,0) + 1
    return count

def is_pair(cards : list[Card]) -> bool:
    counts = get_rank_count(cards)
    return 2 in counts.values()

def is_two_pair(cards : list[Card]) -> bool:
    counts = get_rank_count(cards)
    return list(counts.values()).count(2) == 2

def is_three_of_a_kind(cards : list[Card]) -> bool:
    counts = get_rank_count(cards)
    return 3 in counts.values()

def is_full_house(cards: list[Card]) -> bool:
    counts = get_rank_count(cards)
    return 3 in counts.values() and 2 in counts.values()

def is_four_of_a_kind(cards: list[Card]) -> bool:
    counts = get_rank_count(cards)
    return 4 in counts.values()

def is_straight_flush(cards: list[Card]) -> bool:
    return is_straight(cards) and is_flush(cards)

def is_royal_flush(cards: list[Card]) -> bool:
    ranks = set(card.rank.value for card in cards)
    return is_flush(cards) and {10, 11, 12, 13, 14}.issubset(ranks)

def evaluate(cards: list[Card]) -> HandRank:
    if is_royal_flush(cards):   return HandRank.ROYAL_FLUSH
    if is_straight_flush(cards): return HandRank.STRAIGHT_FLUSH
    if is_four_of_a_kind(cards): return HandRank.FOUR_OF_A_KIND
    if is_full_house(cards):     return HandRank.FULL_HOUSE
    if is_flush(cards):          return HandRank.FLUSH
    if is_straight(cards):       return HandRank.STRAIGHT
    if is_three_of_a_kind(cards): return HandRank.THREE_OF_A_KIND
    if is_two_pair(cards):       return HandRank.TWO_PAIR
    if is_pair(cards):           return HandRank.PAIR
    return HandRank.HIGH_CARD

