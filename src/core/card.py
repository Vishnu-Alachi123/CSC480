from enum import Enum
import random

class Suit(Enum):
    SPADES = "SPADES"
    HEARTS = "HEARTS"
    DIAMONDS = "DIAMONDS"
    CLUBS = "CLUBS"

class Rank(Enum):
    TWO   = 2
    THREE = 3
    FOUR  = 4
    FIVE  = 5
    SIX   = 6
    SEVEN = 7
    EIGHT = 8
    NINE  = 9
    TEN   = 10
    JACK  = 11
    QUEEN = 12
    KING  = 13
    ACE   = 14 

class Card: 
    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit 

    def __repr__(self):
        return f"{self.rank.name} of {self.suit.name}"

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in Rank for suit in Suit]
    
    def remove(self, cards: list[Card]):
        for card in cards:
            self.cards.remove(card)

    


