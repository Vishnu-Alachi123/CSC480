"""
ui/poker_ui.py
--------------
Pygame-based renderer for a PyPokerEngine game.

Displays:
  - Community cards (flop / turn / river)
  - Each player's hole cards (face-up for human, face-down for bots)
  - Pot size, player stacks, current street
  - Hand strength + equity bars (for the human player)
  - Action log (last N actions)
  - Action buttons: Fold / Call / Raise  (used by HumanAgent)

Usage (standalone demo):
    python -m src.ui.poker_ui
"""

import sys
import threading
import pygame

# ── Colour palette ────────────────────────────────────────────────────────────
BG          = (  7,  99,  36)   # felt green
CARD_WHITE  = (255, 255, 255)
CARD_BACK   = ( 30,  60, 150)
RED         = (200,  30,  30)
BLACK       = ( 20,  20,  20)
GOLD        = (212, 175,  55)
CHIP_YELLOW = (240, 200,  50)
TEXT_LIGHT  = (230, 230, 230)
TEXT_DIM    = (160, 160, 160)
BTN_FOLD    = (180,  40,  40)
BTN_CALL    = ( 40, 140,  40)
BTN_RAISE   = ( 40,  80, 180)
BTN_HOVER   = (255, 255, 255, 60)
BAR_BG      = ( 50,  50,  50)
BAR_GREEN   = ( 50, 200,  80)
BAR_BLUE    = ( 50, 120, 220)
PANEL_BG    = (  0,   0,   0, 140)

# ── Layout constants ──────────────────────────────────────────────────────────
WIN_W, WIN_H = 1100, 720
CARD_W, CARD_H = 60, 88
CARD_RADIUS    = 6
FONT_LARGE     = 28
FONT_MED       = 20
FONT_SMALL     = 15

SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
SUIT_COLORS  = {'S': BLACK, 'H': RED, 'D': RED, 'C': BLACK}

RANK_DISPLAY = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9', 'T': '10',
    'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A',
}

STREET_LABELS = {
    'preflop': 'PRE-FLOP',
    'flop':    'FLOP',
    'turn':    'TURN',
    'river':   'RIVER',
    'showdown':'SHOWDOWN',
}


# ── Card drawing ──────────────────────────────────────────────────────────────

def _draw_card(surface, x, y, card_str, font_big, font_small, face_up=True):
    """Draw a single card at (x, y). card_str e.g. 'CA', 'H9'."""
    rect = pygame.Rect(x, y, CARD_W, CARD_H)

    if not face_up:
        # Card back
        pygame.draw.rect(surface, CARD_BACK, rect, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, GOLD, rect, 2, border_radius=CARD_RADIUS)
        # Simple pattern
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, (20, 40, 120), inner, border_radius=4)
        return

    # Card face
    pygame.draw.rect(surface, CARD_WHITE, rect, border_radius=CARD_RADIUS)
    pygame.draw.rect(surface, (180, 180, 180), rect, 1, border_radius=CARD_RADIUS)

    suit_char = card_str[0].upper()
    rank_char = card_str[1].upper()
    symbol    = SUIT_SYMBOLS.get(suit_char, suit_char)
    rank_txt  = RANK_DISPLAY.get(rank_char, rank_char)
    color     = SUIT_COLORS.get(suit_char, BLACK)

    # Top-left rank + suit
    r_surf = font_small.render(rank_txt, True, color)
    s_surf = font_small.render(symbol,   True, color)
    surface.blit(r_surf, (x + 4, y + 3))
    surface.blit(s_surf, (x + 4, y + 3 + r_surf.get_height()))

    # Centre big suit symbol
    big_sym = font_big.render(symbol, True, color)
    cx = x + CARD_W // 2 - big_sym.get_width() // 2
    cy = y + CARD_H // 2 - big_sym.get_height() // 2
    surface.blit(big_sym, (cx, cy))

    # Bottom-right (rotated) rank + suit — simulated by mirroring
    r2 = font_small.render(rank_txt, True, color)
    s2 = font_small.render(symbol,   True, color)
    surface.blit(r2, (x + CARD_W - r2.get_width() - 4,
                      y + CARD_H - r2.get_height() - s2.get_height() - 3))
    surface.blit(s2, (x + CARD_W - s2.get_width() - 4,
                      y + CARD_H - s2.get_height() - 3))


def _draw_card_placeholder(surface, x, y):
    """Draw an empty card slot."""
    rect = pygame.Rect(x, y, CARD_W, CARD_H)
    pygame.draw.rect(surface, (30, 80, 50), rect, border_radius=CARD_RADIUS)
    pygame.draw.rect(surface, (60, 110, 70), rect, 1, border_radius=CARD_RADIUS)


# ── Bar drawing ───────────────────────────────────────────────────────────────

def _draw_bar(surface, x, y, w, h, value, color, label, font):
    pygame.draw.rect(surface, BAR_BG, (x, y, w, h), border_radius=3)
    fill_w = int(w * max(0.0, min(1.0, value)))
    if fill_w > 0:
        pygame.draw.rect(surface, color, (x, y, fill_w, h), border_radius=3)
    lbl = font.render(f"{label}: {value*100:.0f}%", True, TEXT_LIGHT)
    surface.blit(lbl, (x, y - lbl.get_height() - 2))


# ── Button ────────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect, label, color, font):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.font  = font
        self.hovered = False

    def draw(self, surface):
        c = tuple(min(v + 30, 255) for v in self.color) if self.hovered else self.color
        pygame.draw.rect(surface, c, self.rect, border_radius=8)
        pygame.draw.rect(surface, GOLD, self.rect, 2, border_radius=8)
        txt = self.font.render(self.label, True, CARD_WHITE)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# ── Main UI class ─────────────────────────────────────────────────────────────

class PokerUI:
    """
    Pygame poker table renderer.

    Thread-safe: game logic runs in its own thread; the UI runs on the main
    thread (required by pygame / macOS).  Use `set_state()` to push updates
    from the game thread, and `wait_for_action()` to block the game thread
    until the human clicks a button.
    """

    def __init__(self, title="Poker — PyPokerEngine"):
        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock  = pygame.time.Clock()

        # Fonts
        self.font_lg  = pygame.font.SysFont("Arial", FONT_LARGE,  bold=True)
        self.font_med = pygame.font.SysFont("Arial", FONT_MED)
        self.font_sm  = pygame.font.SysFont("Arial", FONT_SMALL)
        self.font_card_big   = pygame.font.SysFont("Arial", 30, bold=True)
        self.font_card_small = pygame.font.SysFont("Arial", 13, bold=True)

        # Game state (updated by set_state)
        self._state_lock   = threading.Lock()
        self._game_state   = {}          # latest round_state dict
        self._hole_cards   = []          # human's hole cards
        self._community    = []          # community cards
        self._street       = "preflop"
        self._pot          = 0
        self._seats        = []          # list of seat dicts
        self._hand_strength = 0.5
        self._equity        = 0.5
        self._action_log    = []         # list of strings
        self._valid_actions = []
        self._human_uuid    = None
        self._round_count   = 0
        self._winner_msg    = ""

        # Action result (set when human clicks a button)
        self._action_event  = threading.Event()
        self._chosen_action = None       # ("fold"|"call"|"raise", amount)
        self._waiting       = False      # True while waiting for human input
        self._raise_amount  = 0
        self._raise_min     = 0
        self._raise_max     = 0

        # Buttons
        bw, bh = 140, 48
        by = WIN_H - 70
        self._btn_fold  = Button((WIN_W//2 - bw*2 - 20, by, bw, bh), "FOLD",  BTN_FOLD,  self.font_med)
        self._btn_call  = Button((WIN_W//2 - bw//2,     by, bw, bh), "CALL",  BTN_CALL,  self.font_med)
        self._btn_raise = Button((WIN_W//2 + bw + 20,   by, bw, bh), "RAISE", BTN_RAISE, self.font_med)

        self._running = True

    # ── Public API (called from game thread) ──────────────────────────────────

    def set_state(
        self,
        round_state: dict,
        hole_cards: list,
        hand_strength: float = 0.5,
        equity: float = 0.5,
        human_uuid: str = None,
        valid_actions: list = None,
        raise_min: int = 0,
        raise_max: int = 0,
    ):
        """Push a new game state to the renderer. Thread-safe."""
        with self._state_lock:
            self._game_state    = round_state
            self._hole_cards    = hole_cards or []
            self._community     = round_state.get("community_card", [])
            self._street        = round_state.get("street", "preflop")
            self._pot           = round_state.get("pot", {}).get("main", {}).get("amount", 0)
            self._seats         = round_state.get("seats", [])
            self._hand_strength = hand_strength
            self._equity        = equity
            self._round_count   = round_state.get("round_count", 0)
            if human_uuid is not None:
                self._human_uuid = human_uuid
            if valid_actions is not None:
                self._valid_actions = valid_actions
                self._raise_min = raise_min
                self._raise_max = raise_max
                self._raise_amount = raise_min

    def add_action_log(self, message: str):
        """Append a line to the action log. Thread-safe."""
        with self._state_lock:
            self._action_log.append(message)
            if len(self._action_log) > 12:
                self._action_log.pop(0)

    def set_winner(self, message: str):
        """Display a winner banner. Thread-safe."""
        with self._state_lock:
            self._winner_msg = message

    def wait_for_action(self) -> tuple:
        """
        Block the calling (game) thread until the human clicks a button.
        Returns (action_str, amount).
        """
        self._action_event.clear()
        self._waiting = True
        self._action_event.wait()
        self._waiting = False
        return self._chosen_action

    def close(self):
        self._running = False

    # ── Main loop (call from main thread) ────────────────────────────────────

    def run(self, game_thread_fn=None):
        """
        Start the pygame event loop.  If `game_thread_fn` is provided it is
        launched in a background thread so the UI stays responsive.
        """
        if game_thread_fn:
            t = threading.Thread(target=game_thread_fn, daemon=True)
            t.start()

        while self._running:
            self.clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    # Unblock any waiting game thread
                    if self._waiting:
                        self._chosen_action = ("fold", 0)
                        self._action_event.set()
                self._handle_event(event)

            self._render()
            pygame.display.flip()

        pygame.quit()

    # ── Event handling ────────────────────────────────────────────────────────

    def _handle_event(self, event):
        if not self._waiting:
            return

        # Raise slider: left/right arrow keys
        if event.type == pygame.KEYDOWN:
            step = max(1, (self._raise_max - self._raise_min) // 20)
            if event.key == pygame.K_LEFT:
                self._raise_amount = max(self._raise_min, self._raise_amount - step)
            elif event.key == pygame.K_RIGHT:
                self._raise_amount = min(self._raise_max, self._raise_amount + step)

        if self._btn_fold.handle_event(event):
            self._chosen_action = ("fold", 0)
            self._action_event.set()
        elif self._btn_call.handle_event(event):
            call_amount = 0
            for a in self._valid_actions:
                if a["action"] == "call":
                    call_amount = a["amount"]
            self._chosen_action = ("call", call_amount)
            self._action_event.set()
        elif self._btn_raise.handle_event(event):
            if self._raise_max > 0:
                self._chosen_action = ("raise", self._raise_amount)
            else:
                self._chosen_action = ("call", 0)
            self._action_event.set()

        # Mouse wheel adjusts raise amount
        if event.type == pygame.MOUSEWHEEL and self._raise_max > self._raise_min:
            step = max(1, (self._raise_max - self._raise_min) // 20)
            self._raise_amount = max(
                self._raise_min,
                min(self._raise_max, self._raise_amount + event.y * step)
            )

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self):
        with self._state_lock:
            # Snapshot state to avoid holding lock during draw
            community    = list(self._community)
            hole_cards   = list(self._hole_cards)
            street       = self._street
            pot          = self._pot
            seats        = list(self._seats)
            strength     = self._hand_strength
            equity       = self._equity
            log          = list(self._action_log)
            waiting      = self._waiting
            valid_acts   = list(self._valid_actions)
            raise_amt    = self._raise_amount
            raise_min    = self._raise_min
            raise_max    = self._raise_max
            human_uuid   = self._human_uuid
            round_count  = self._round_count
            winner_msg   = self._winner_msg

        self.screen.fill(BG)

        # ── Table oval ──────────────────────────────────────────────────────
        table_rect = pygame.Rect(80, 80, WIN_W - 160, WIN_H - 220)
        pygame.draw.ellipse(self.screen, (10, 80, 30), table_rect)
        pygame.draw.ellipse(self.screen, GOLD, table_rect, 4)

        # ── Street label ────────────────────────────────────────────────────
        street_lbl = self.font_lg.render(
            STREET_LABELS.get(street, street.upper()), True, GOLD
        )
        self.screen.blit(street_lbl, street_lbl.get_rect(centerx=WIN_W // 2, y=90))

        # ── Round counter ───────────────────────────────────────────────────
        if round_count:
            rc = self.font_sm.render(f"Round {round_count}", True, TEXT_DIM)
            self.screen.blit(rc, (WIN_W - rc.get_width() - 12, 8))

        # ── Community cards ─────────────────────────────────────────────────
        total_comm_w = 5 * CARD_W + 4 * 10
        cx_start = WIN_W // 2 - total_comm_w // 2
        cy = WIN_H // 2 - CARD_H // 2 - 10
        for i in range(5):
            x = cx_start + i * (CARD_W + 10)
            if i < len(community):
                _draw_card(self.screen, x, cy, community[i],
                           self.font_card_big, self.font_card_small, face_up=True)
            else:
                _draw_card_placeholder(self.screen, x, cy)

        # ── Pot ─────────────────────────────────────────────────────────────
        pot_surf = self.font_med.render(f"POT  {pot:,}", True, CHIP_YELLOW)
        self.screen.blit(pot_surf, pot_surf.get_rect(centerx=WIN_W // 2, y=cy - 36))

        # ── Players ─────────────────────────────────────────────────────────
        self._draw_players(seats, human_uuid, hole_cards)

        # ── HUD: hand strength + equity bars ────────────────────────────────
        if hole_cards:
            _draw_bar(self.screen, 20, 180, 160, 14, strength, BAR_GREEN,
                      "Strength", self.font_sm)
            _draw_bar(self.screen, 20, 220, 160, 14, equity, BAR_BLUE,
                      "Equity", self.font_sm)

        # ── Action log ──────────────────────────────────────────────────────
        self._draw_log(log)

        # ── Action buttons ───────────────────────────────────────────────────
        if waiting:
            self._draw_action_panel(valid_acts, raise_amt, raise_min, raise_max)

        # ── Winner banner ────────────────────────────────────────────────────
        if winner_msg:
            self._draw_winner_banner(winner_msg)

    def _draw_players(self, seats, human_uuid, hole_cards):
        """Position players around the table oval."""
        n = len(seats)
        if n == 0:
            return

        import math
        cx, cy = WIN_W // 2, WIN_H // 2 - 10
        rx, ry = WIN_W // 2 - 120, WIN_H // 2 - 80

        for i, seat in enumerate(seats):
            # Angle: human at bottom (270°), others spread around
            angle_deg = 270 + (360 / n) * i
            angle_rad = math.radians(angle_deg)
            px = int(cx + rx * math.cos(angle_rad))
            py = int(cy + ry * math.sin(angle_rad))

            is_human = seat.get("uuid") == human_uuid
            is_active = seat.get("state") == "participating"

            # Name plate
            name  = seat.get("name", f"P{i}")
            stack = seat.get("stack", 0)
            color = GOLD if is_human else (TEXT_LIGHT if is_active else TEXT_DIM)

            name_surf  = self.font_sm.render(name, True, color)
            stack_surf = self.font_sm.render(f"${stack:,}", True, CHIP_YELLOW if is_active else TEXT_DIM)

            plate_w = max(name_surf.get_width(), stack_surf.get_width()) + 16
            plate_h = name_surf.get_height() + stack_surf.get_height() + 10
            plate_x = px - plate_w // 2
            plate_y = py - plate_h // 2

            # Background plate
            plate_surf = pygame.Surface((plate_w, plate_h), pygame.SRCALPHA)
            plate_surf.fill((0, 0, 0, 160))
            self.screen.blit(plate_surf, (plate_x, plate_y))
            if is_human:
                pygame.draw.rect(self.screen, GOLD,
                                 (plate_x, plate_y, plate_w, plate_h), 2, border_radius=4)

            self.screen.blit(name_surf,  (plate_x + 8, plate_y + 4))
            self.screen.blit(stack_surf, (plate_x + 8, plate_y + 4 + name_surf.get_height() + 2))

            # Cards next to player
            card_x = px + plate_w // 2 + 6
            card_y = py - CARD_H // 2

            if is_human and hole_cards:
                for j, card in enumerate(hole_cards):
                    _draw_card(self.screen, card_x + j * (CARD_W + 4), card_y,
                               card, self.font_card_big, self.font_card_small, face_up=True)
            elif is_active:
                # Show face-down cards for bots
                for j in range(2):
                    _draw_card(self.screen, card_x + j * (CARD_W + 4), card_y,
                               "XX", self.font_card_big, self.font_card_small, face_up=False)

    def _draw_log(self, log):
        """Draw the action log panel on the right side."""
        panel_x, panel_y = WIN_W - 220, 80
        panel_w, panel_h = 210, 300

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 130))
        self.screen.blit(panel, (panel_x, panel_y))
        pygame.draw.rect(self.screen, GOLD, (panel_x, panel_y, panel_w, panel_h), 1)

        hdr = self.font_sm.render("ACTION LOG", True, GOLD)
        self.screen.blit(hdr, (panel_x + 8, panel_y + 6))

        for i, line in enumerate(log[-10:]):
            color = TEXT_LIGHT if i == len(log) - 1 else TEXT_DIM
            surf = self.font_sm.render(line[:28], True, color)
            self.screen.blit(surf, (panel_x + 6, panel_y + 28 + i * 26))

    def _draw_action_panel(self, valid_acts, raise_amt, raise_min, raise_max):
        """Draw fold/call/raise buttons and raise slider."""
        # Update call button label with amount
        call_amount = 0
        for a in valid_acts:
            if a["action"] == "call":
                call_amount = a["amount"]
        self._btn_call.label = f"CALL  {call_amount:,}" if call_amount else "CHECK"

        self._btn_fold.draw(self.screen)
        self._btn_call.draw(self.screen)

        # Only show raise if it's a valid action
        can_raise = any(a["action"] == "raise" for a in valid_acts)
        if can_raise and raise_max > 0:
            self._btn_raise.label = f"RAISE  {raise_amt:,}"
            self._btn_raise.draw(self.screen)

            # Raise slider bar
            slider_x = WIN_W // 2 + 170
            slider_y = WIN_H - 56
            slider_w = 200
            slider_h = 10
            pygame.draw.rect(self.screen, BAR_BG, (slider_x, slider_y, slider_w, slider_h), border_radius=4)
            if raise_max > raise_min:
                ratio = (raise_amt - raise_min) / (raise_max - raise_min)
                fill  = int(slider_w * ratio)
                pygame.draw.rect(self.screen, BTN_RAISE, (slider_x, slider_y, fill, slider_h), border_radius=4)
            hint = self.font_sm.render("← → or scroll to adjust", True, TEXT_DIM)
            self.screen.blit(hint, (slider_x, slider_y + 14))

    def _draw_winner_banner(self, message):
        """Overlay a semi-transparent winner banner."""
        banner = pygame.Surface((600, 80), pygame.SRCALPHA)
        banner.fill((0, 0, 0, 200))
        self.screen.blit(banner, (WIN_W // 2 - 300, WIN_H // 2 - 40))
        pygame.draw.rect(self.screen, GOLD, (WIN_W // 2 - 300, WIN_H // 2 - 40, 600, 80), 3)
        txt = self.font_lg.render(message, True, GOLD)
        self.screen.blit(txt, txt.get_rect(center=(WIN_W // 2, WIN_H // 2)))


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    ui = PokerUI("Poker UI — Demo")

    def demo_game():
        """Simulate a few state updates so you can see the UI."""
        time.sleep(0.5)

        # Fake round state
        fake_state = {
            "street": "flop",
            "round_count": 3,
            "pot": {"main": {"amount": 240}},
            "community_card": ["HK", "D7", "C2"],
            "seats": [
                {"uuid": "human-1", "name": "You",       "stack": 760, "state": "participating"},
                {"uuid": "bot-1",   "name": "RandomBot", "stack": 500, "state": "participating"},
                {"uuid": "bot-2",   "name": "CallBot",   "stack": 740, "state": "participating"},
            ],
            "action_histories": {},
            "dealer_btn": 0,
        }

        ui.set_state(
            round_state=fake_state,
            hole_cards=["SA", "HQ"],
            hand_strength=0.78,
            equity=0.65,
            human_uuid="human-1",
            valid_actions=[
                {"action": "fold",  "amount": 0},
                {"action": "call",  "amount": 40},
                {"action": "raise", "amount": {"min": 80, "max": 760}},
            ],
            raise_min=80,
            raise_max=760,
        )
        ui.add_action_log("RandomBot raised 80")
        ui.add_action_log("CallBot called 80")
        ui.add_action_log("Your turn!")

        # Wait for human to act
        action = ui.wait_for_action()
        ui.add_action_log(f"You: {action[0]} {action[1]}")
        time.sleep(0.5)

        # River
        fake_state["street"] = "river"
        fake_state["community_card"] = ["HK", "D7", "C2", "S5", "DA"]
        fake_state["pot"]["main"]["amount"] = 480
        ui.set_state(
            round_state=fake_state,
            hole_cards=["SA", "HQ"],
            hand_strength=0.85,
            equity=0.72,
            human_uuid="human-1",
        )
        ui.add_action_log("Dealt river: A♦")
        time.sleep(2)

        ui.set_winner("You win!  +480 chips")
        time.sleep(3)
        ui.close()

    ui.run(game_thread_fn=demo_game)
