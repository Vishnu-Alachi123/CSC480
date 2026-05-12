"""
ui/poker_ui.py
--------------
Simple pygame poker table display.

The only thing this file does is draw the current game state.
It knows nothing about agents or game logic.

Usage:
    ui = PokerUI()
    ui.update(hole_cards, community_cards, seats, pot, street, round_num)
    ui.draw()

    # When it's a human's turn, show buttons and wait for a click:
    action = ui.ask_human(valid_actions)   # returns ("fold"|"call"|"raise", amount)
"""

import pygame

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN       = (  7,  99,  36)   # felt
DARK_GREEN  = ( 10,  70,  25)   # table oval
GOLD        = (212, 175,  55)
WHITE       = (255, 255, 255)
BLACK       = ( 20,  20,  20)
RED         = (200,  30,  30)
GREY        = (160, 160, 160)
DARK_GREY   = ( 50,  50,  50)
CARD_BACK   = ( 30,  60, 150)
YELLOW      = (240, 200,  50)

# ── Sizes ─────────────────────────────────────────────────────────────────────
W, H       = 900, 600
CARD_W     = 56
CARD_H     = 80

# Card suit display helpers
SUITS  = {'S': ('♠', BLACK), 'H': ('♥', RED), 'D': ('♦', RED), 'C': ('♣', BLACK)}
RANKS  = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}   # rest are digits


class PokerUI:
    """
    Dead-simple poker table renderer.

    Call update() to push new state, then draw() each frame.
    Call ask_human() when you need a human decision.
    """

    def __init__(self, title="Poker"):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(title)
        self.clock  = pygame.time.Clock()

        self.font_lg  = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 18)
        self.font_sm  = pygame.font.SysFont("Arial", 14)

        # State — set by update()
        self.hole_cards  = []
        self.community   = []
        self.seats       = []
        self.pot         = 0
        self.street      = "preflop"
        self.round_num   = 0
        self.log         = []          # list of action strings

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, hole_cards, community_cards, seats, pot, street, round_num):
        """Push the latest game state. Call this whenever something changes."""
        self.hole_cards = hole_cards
        self.community  = community_cards
        self.seats      = seats
        self.pot        = pot
        self.street     = street
        self.round_num  = round_num

    def log_action(self, message):
        """Add a line to the on-screen action log (last 8 shown)."""
        self.log.append(message)
        if len(self.log) > 8:
            self.log.pop(0)

    def draw(self):
        """Render one frame. Call this in your game loop."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        self.screen.fill(GREEN)
        self._draw_table()
        self._draw_community()
        self._draw_pot()
        self._draw_players()
        self._draw_log()
        self._draw_street()
        pygame.display.flip()
        self.clock.tick(30)

    def ask_human(self, valid_actions):
        """
        Show Fold / Call / Raise buttons and block until the human clicks one.
        Returns (action_str, amount).

        valid_actions format (from PyPokerEngine):
            [
              {"action": "fold",  "amount": 0},
              {"action": "call",  "amount": 10},
              {"action": "raise", "amount": {"min": 20, "max": 200}},
            ]
        """
        # Build button list from whatever actions are actually available
        buttons = []
        for a in valid_actions:
            name = a["action"]
            if name == "fold":
                label, color = "FOLD", (180, 40, 40)
            elif name == "call":
                amt   = a["amount"]
                label = f"CALL  {amt}" if amt else "CHECK"
                color = (40, 140, 40)
            else:  # raise
                raise_min = a["amount"]["min"]
                label, color = f"RAISE  {raise_min}", (40, 80, 180)
            buttons.append((label, color, a))

        # Position buttons evenly at the bottom
        bw, bh = 160, 44
        total_w = len(buttons) * bw + (len(buttons) - 1) * 16
        start_x = W // 2 - total_w // 2
        rects = []
        for i in range(len(buttons)):
            x = start_x + i * (bw + 16)
            rects.append(pygame.Rect(x, H - 60, bw, bh))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(rects):
                        if rect.collidepoint(event.pos):
                            _, _, action = buttons[i]
                            name = action["action"]
                            if name == "raise":
                                amount = action["amount"]["min"]
                            else:
                                amount = action["amount"]
                            return name, amount

            # Draw the table + buttons every frame while waiting
            self.screen.fill(GREEN)
            self._draw_table()
            self._draw_community()
            self._draw_pot()
            self._draw_players()
            self._draw_log()
            self._draw_street()

            for i, (label, color, _) in enumerate(buttons):
                rect = rects[i]
                pygame.draw.rect(self.screen, color, rect, border_radius=6)
                pygame.draw.rect(self.screen, GOLD,  rect, 2, border_radius=6)
                txt = self.font_med.render(label, True, WHITE)
                self.screen.blit(txt, txt.get_rect(center=rect.center))

            pygame.display.flip()
            self.clock.tick(30)

    def show_showdown(self, player_hands, community_cards, winner_name, pause_seconds=4):
        """
        Show all players' hole cards face-up at the end of a round.

        player_hands: list of {"name": str, "cards": [str, str], "hand_name": str}
        community_cards: list of card strings (the final board)
        winner_name: name of the winner to highlight
        """
        import time
        deadline = time.time() + pause_seconds
        while time.time() < deadline:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

            self.screen.fill(GREEN)
            self._draw_table()

            # Board
            self.community = community_cards
            self._draw_community()

            # Title
            title = self.font_lg.render("SHOWDOWN", True, GOLD)
            self.screen.blit(title, title.get_rect(centerx=W // 2, y=68))

            # Each player's hand laid out in a row at the bottom half
            n = len(player_hands)
            slot_w = W // max(n, 1)
            for i, p in enumerate(player_hands):
                cx = slot_w * i + slot_w // 2
                y_name = H // 2 + CARD_H // 2 + 20

                is_winner = p["name"] == winner_name
                name_color = GOLD if is_winner else WHITE

                # Cards side by side
                cards = p.get("cards", [])
                total_cards_w = len(cards) * CARD_W + (len(cards) - 1) * 6
                card_x = cx - total_cards_w // 2
                for card_str in cards:
                    self._draw_card(card_x, H // 2 + CARD_H // 2 - 20, card_str, face_up=True)
                    card_x += CARD_W + 6

                # Name
                name_surf = self.font_med.render(p["name"], True, name_color)
                self.screen.blit(name_surf, name_surf.get_rect(centerx=cx, y=y_name + CARD_H))

                # Hand name (e.g. "TWO PAIR")
                hand_name = p.get("hand_name", "")
                if hand_name:
                    hn_surf = self.font_sm.render(hand_name, True, YELLOW if is_winner else GREY)
                    self.screen.blit(hn_surf, hn_surf.get_rect(centerx=cx, y=y_name + CARD_H + 22))

                # Winner crown marker
                if is_winner:
                    crown = self.font_lg.render("★ WINNER", True, GOLD)
                    self.screen.blit(crown, crown.get_rect(centerx=cx, y=y_name + CARD_H + 44))

            pygame.display.flip()
            self.clock.tick(30)

    def show_winner(self, message, pause_seconds=3):
        """Flash a winner message for a few seconds."""
        import time
        deadline = time.time() + pause_seconds
        while time.time() < deadline:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

            self.draw()
            banner = pygame.Surface((500, 70), pygame.SRCALPHA)
            banner.fill((0, 0, 0, 200))
            self.screen.blit(banner, (W // 2 - 250, H // 2 - 35))
            pygame.draw.rect(self.screen, GOLD, (W // 2 - 250, H // 2 - 35, 500, 70), 3)
            txt = self.font_lg.render(message, True, GOLD)
            self.screen.blit(txt, txt.get_rect(center=(W // 2, H // 2)))
            pygame.display.flip()
            self.clock.tick(30)

    def quit(self):
        pygame.quit()

    # ── Private drawing helpers ───────────────────────────────────────────────

    def _draw_table(self):
        pygame.draw.ellipse(self.screen, DARK_GREEN, (60, 60, W - 120, H - 160))
        pygame.draw.ellipse(self.screen, GOLD,       (60, 60, W - 120, H - 160), 3)

    def _draw_street(self):
        label = self.street.upper()
        if self.round_num:
            label += f"   Round {self.round_num}"
        surf = self.font_med.render(label, True, GOLD)
        self.screen.blit(surf, surf.get_rect(centerx=W // 2, y=68))

    def _draw_pot(self):
        surf = self.font_med.render(f"POT  {self.pot:,}", True, YELLOW)
        self.screen.blit(surf, surf.get_rect(centerx=W // 2, y=H // 2 - CARD_H // 2 - 28))

    def _draw_community(self):
        total_w = 5 * CARD_W + 4 * 8
        x = W // 2 - total_w // 2
        y = H // 2 - CARD_H // 2
        for i in range(5):
            if i < len(self.community):
                self._draw_card(x, y, self.community[i], face_up=True)
            else:
                self._draw_card_slot(x, y)
            x += CARD_W + 8

    def _draw_players(self):
        import math
        n = len(self.seats)
        if n == 0:
            return
        cx, cy = W // 2, H // 2
        rx, ry = W // 2 - 110, H // 2 - 70

        for i, seat in enumerate(self.seats):
            angle = math.radians(270 + (360 / n) * i)
            px = int(cx + rx * math.cos(angle))
            py = int(cy + ry * math.sin(angle))

            name   = seat.get("name", f"P{i}")
            stack  = seat.get("stack", 0)
            active = seat.get("state") == "participating"
            is_me  = i == 0   # seat 0 is always the focus player

            # Name + stack label
            color = GOLD if is_me else (WHITE if active else GREY)
            self.screen.blit(self.font_sm.render(name,          True, color),
                             (px - 30, py - 10))
            self.screen.blit(self.font_sm.render(f"${stack:,}", True, YELLOW if active else GREY),
                             (px - 30, py + 6))

            # Cards
            card_x = px + 36
            card_y = py - CARD_H // 2
            if is_me and self.hole_cards:
                for j, card in enumerate(self.hole_cards):
                    self._draw_card(card_x + j * (CARD_W + 4), card_y, card, face_up=True)
            elif active:
                for j in range(2):
                    self._draw_card(card_x + j * (CARD_W + 4), card_y, None, face_up=False)

    def _draw_log(self):
        x, y = W - 190, 80
        for line in self.log:
            surf = self.font_sm.render(line[:26], True, GREY)
            self.screen.blit(surf, (x, y))
            y += 22

    def _draw_card(self, x, y, card_str, face_up):
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        if not face_up:
            pygame.draw.rect(self.screen, CARD_BACK, rect, border_radius=5)
            pygame.draw.rect(self.screen, GOLD,      rect, 1, border_radius=5)
            return

        pygame.draw.rect(self.screen, WHITE, rect, border_radius=5)
        pygame.draw.rect(self.screen, GREY,  rect, 1, border_radius=5)

        suit_char = card_str[0].upper()
        rank_char = card_str[1].upper()
        symbol, color = SUITS.get(suit_char, ('?', BLACK))
        rank_txt = RANKS.get(rank_char, rank_char)

        self.screen.blit(self.font_sm.render(rank_txt, True, color), (x + 3,  y + 2))
        self.screen.blit(self.font_sm.render(symbol,   True, color), (x + 3,  y + 16))
        big = self.font_lg.render(symbol, True, color)
        self.screen.blit(big, big.get_rect(center=(x + CARD_W // 2, y + CARD_H // 2)))

    def _draw_card_slot(self, x, y):
        pygame.draw.rect(self.screen, (20, 70, 40),
                         (x, y, CARD_W, CARD_H), border_radius=5)
        pygame.draw.rect(self.screen, (40, 90, 55),
                         (x, y, CARD_W, CARD_H), 1, border_radius=5)
