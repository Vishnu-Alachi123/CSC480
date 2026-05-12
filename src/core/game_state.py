class GameState:
    hole_cards: list[Cards]
    community_cards: list[Cards]
    pot: float
    call_amount: float
    num_opponents: int
    stack: float
    position: str

    