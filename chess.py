import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame


# --- Basics ---
WIDTH, HEIGHT = 720, 760  # 8x8 board + status area
FPS = 60
SQUARE = 80

LIGHT = (238, 238, 210)
DARK = (118, 150, 86)
HL = (246, 246, 105)
MOVE_HL = (187, 203, 43)
CHECK_HL = (255, 120, 120)
UI = (25, 30, 40)
TEXT = (245, 245, 245)


# Piece encoding: uppercase = White, lowercase = Black
# 'KQRB N P' (spaces just for clarity)


@dataclass
class Move:
    start: Tuple[int, int]
    end: Tuple[int, int]
    promotion: Optional[str] = None  # 'Q','R','B','N' (uppercase for white, lowercase for black)
    is_en_passant: bool = False
    is_castle: bool = False


class Board:
    def __init__(self) -> None:
        # Starting position
        self.board: List[List[str]] = [
            list("rnbqkbnr"),
            list("pppppppp"),
            list("........"),
            list("........"),
            list("........"),
            list("........"),
            list("PPPPPPPP"),
            list("RNBQKBNR"),
        ]
        self.white_to_move = True
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.en_passant_target: Optional[Tuple[int, int]] = None
        self.castling_rights = {
            'K': True,  # white king-side
            'Q': True,  # white queen-side
            'k': True,  # black king-side
            'q': True,  # black queen-side
        }
        self.history: List[Tuple[Move, Optional[str], dict]] = []  # (move, captured_piece, castling_rights_copy)

    # --- Helpers ---
    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    def get(self, r: int, c: int) -> str:
        return self.board[r][c]

    def set(self, r: int, c: int, v: str) -> None:
        self.board[r][c] = v

    def color(self, p: str) -> Optional[str]:
        if p == '.':
            return None
        return 'w' if p.isupper() else 'b'

    def king_pos(self, white: bool) -> Tuple[int, int]:
        k = 'K' if white else 'k'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == k:
                    return (r, c)
        return (-1, -1)

    # --- Move generation (pseudo legal) ---
    def gen_moves(self, white: bool) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == '.' or (p.isupper() != white):
                    continue
                if p.upper() == 'P':
                    self._gen_pawn(r, c, moves)
                elif p.upper() == 'N':
                    self._gen_knight(r, c, moves)
                elif p.upper() == 'B':
                    self._gen_slider(r, c, moves, [(-1, -1), (-1, 1), (1, -1), (1, 1)])
                elif p.upper() == 'R':
                    self._gen_slider(r, c, moves, [(-1, 0), (1, 0), (0, -1), (0, 1)])
                elif p.upper() == 'Q':
                    self._gen_slider(r, c, moves, [
                        (-1, -1), (-1, 1), (1, -1), (1, 1),
                        (-1, 0), (1, 0), (0, -1), (0, 1)
                    ])
                elif p.upper() == 'K':
                    self._gen_king(r, c, moves)
        # filter to legal
        legal: List[Move] = []
        for m in moves:
            if self._legal_after(m):
                legal.append(m)
        return legal

    def _gen_pawn(self, r: int, c: int, moves: List[Move]) -> None:
        p = self.get(r, c)
        white = p.isupper()
        dir = -1 if white else 1
        start_row = 6 if white else 1
        last_row = 0 if white else 7
        # forward one
        nr, nc = r + dir, c
        if self.in_bounds(nr, nc) and self.get(nr, nc) == '.':
            self._add_pawn_move(r, c, nr, nc, last_row, moves)
            # forward two
            nr2 = r + 2 * dir
            if r == start_row and self.get(nr2, nc) == '.':
                moves.append(Move((r, c), (nr2, nc)))
        # captures
        for dc in (-1, 1):
            nr, nc = r + dir, c + dc
            if self.in_bounds(nr, nc):
                target = self.get(nr, nc)
                if target != '.' and self.color(target) != self.color(p):
                    self._add_pawn_move(r, c, nr, nc, last_row, moves)
        # en passant
        if self.en_passant_target is not None:
            epr, epc = self.en_passant_target
            if epr == r + dir and abs(epc - c) == 1:
                moves.append(Move((r, c), (epr, epc), is_en_passant=True))

    def _add_pawn_move(self, r: int, c: int, nr: int, nc: int, last_row: int, moves: List[Move]) -> None:
        if nr == last_row:
            for promo in ('Q', 'R', 'B', 'N'):
                promo_piece = promo if self.get(r, c).isupper() else promo.lower()
                moves.append(Move((r, c), (nr, nc), promotion=promo_piece))
        else:
            moves.append(Move((r, c), (nr, nc)))

    def _gen_knight(self, r: int, c: int, moves: List[Move]) -> None:
        p = self.get(r, c)
        white = p.isupper()
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            t = self.get(nr, nc)
            if t == '.' or (t.isupper() != white):
                moves.append(Move((r, c), (nr, nc)))

    def _gen_slider(self, r: int, c: int, moves: List[Move], dirs: List[Tuple[int, int]]) -> None:
        p = self.get(r, c)
        white = p.isupper()
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                t = self.get(nr, nc)
                if t == '.':
                    moves.append(Move((r, c), (nr, nc)))
                else:
                    if t.isupper() != white:
                        moves.append(Move((r, c), (nr, nc)))
                    break
                nr += dr
                nc += dc

    def _gen_king(self, r: int, c: int, moves: List[Move]) -> None:
        p = self.get(r, c)
        white = p.isupper()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not self.in_bounds(nr, nc):
                    continue
                t = self.get(nr, nc)
                if t == '.' or (t.isupper() != white):
                    moves.append(Move((r, c), (nr, nc)))
        # castling
        if white:
            if self.castling_rights['K'] and self.get(7, 5) == '.' and self.get(7, 6) == '.':
                if not self._square_attacked((7, 4), True) and not self._square_attacked((7, 5), True) and not self._square_attacked((7, 6), True):
                    moves.append(Move((7, 4), (7, 6), is_castle=True))
            if self.castling_rights['Q'] and self.get(7, 3) == '.' and self.get(7, 2) == '.' and self.get(7, 1) == '.':
                if not self._square_attacked((7, 4), True) and not self._square_attacked((7, 3), True) and not self._square_attacked((7, 2), True):
                    moves.append(Move((7, 4), (7, 2), is_castle=True))
        else:
            if self.castling_rights['k'] and self.get(0, 5) == '.' and self.get(0, 6) == '.':
                if not self._square_attacked((0, 4), False) and not self._square_attacked((0, 5), False) and not self._square_attacked((0, 6), False):
                    moves.append(Move((0, 4), (0, 6), is_castle=True))
            if self.castling_rights['q'] and self.get(0, 3) == '.' and self.get(0, 2) == '.' and self.get(0, 1) == '.':
                if not self._square_attacked((0, 4), False) and not self._square_attacked((0, 3), False) and not self._square_attacked((0, 2), False):
                    moves.append(Move((0, 4), (0, 2), is_castle=True))

    # --- Attack detection ---
    def _square_attacked(self, sq: Tuple[int, int], white_sq: bool) -> bool:
        r, c = sq
        # pawns
        for dc in (-1, 1):
            nr = r + (1 if white_sq else -1)
            nc = c + dc
            if self.in_bounds(nr, nc):
                p = self.get(nr, nc)
                if p == ("P" if not white_sq else "p"):
                    return True
        # knights
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc):
                p = self.get(nr, nc)
                if p == ("N" if not white_sq else "n"):
                    return True
        # sliders
        def scan(dirs: List[Tuple[int, int]], attackers: str) -> bool:
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while self.in_bounds(nr, nc):
                    p = self.get(nr, nc)
                    if p != '.':
                        if p in attackers:
                            return True
                        break
                    nr += dr
                    nc += dc
            return False

        if scan([(-1, -1), (-1, 1), (1, -1), (1, 1)], "BQ" if not white_sq else "bq"):
            return True
        if scan([(-1, 0), (1, 0), (0, -1), (0, 1)], "RQ" if not white_sq else "rq"):
            return True
        # kings
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    p = self.get(nr, nc)
                    if p == ("K" if not white_sq else "k"):
                        return True
        return False

    # --- Make/Unmake and legality ---
    def _make_move(self, m: Move) -> Optional[str]:
        (sr, sc), (er, ec) = m.start, m.end
        piece = self.get(sr, sc)
        captured: Optional[str] = None
        # Save state
        castling_copy = self.castling_rights.copy()
        self.history.append((m, None, castling_copy))

        # en passant capture
        if m.is_en_passant:
            captured = self.get(sr, ec)
            self.set(sr, ec, '.')
        else:
            captured = self.get(er, ec)

        # move piece
        self.set(er, ec, piece)
        self.set(sr, sc, '.')

        # promotion
        if m.promotion is not None:
            self.set(er, ec, m.promotion)

        # update en passant target
        self.en_passant_target = None
        if piece.upper() == 'P' and abs(er - sr) == 2:
            mid = (sr + er) // 2
            self.en_passant_target = (mid, ec)

        # castling rook move
        if piece == 'K':
            self.castling_rights['K'] = False
            self.castling_rights['Q'] = False
            if m.is_castle:
                if (er, ec) == (7, 6):
                    # move rook h1->f1
                    self.set(7, 5, 'R')
                    self.set(7, 7, '.')
                elif (er, ec) == (7, 2):
                    # rook a1->d1
                    self.set(7, 3, 'R')
                    self.set(7, 0, '.')
        elif piece == 'k':
            self.castling_rights['k'] = False
            self.castling_rights['q'] = False
            if m.is_castle:
                if (er, ec) == (0, 6):
                    self.set(0, 5, 'r')
                    self.set(0, 7, '.')
                elif (er, ec) == (0, 2):
                    self.set(0, 3, 'r')
                    self.set(0, 0, '.')

        # rook moved or captured updates rights
        if (sr, sc) == (7, 0) or (er, ec) == (7, 0):
            self.castling_rights['Q'] = False
        if (sr, sc) == (7, 7) or (er, ec) == (7, 7):
            self.castling_rights['K'] = False
        if (sr, sc) == (0, 0) or (er, ec) == (0, 0):
            self.castling_rights['q'] = False
        if (sr, sc) == (0, 7) or (er, ec) == (0, 7):
            self.castling_rights['k'] = False

        # store captured in history
        self.history[-1] = (m, captured, castling_copy)
        # side to move
        self.white_to_move = not self.white_to_move
        return captured

    def _unmake_last(self) -> None:
        if not self.history:
            return
        m, captured, castling_copy = self.history.pop()
        (sr, sc), (er, ec) = m.start, m.end
        piece = self.get(er, ec)
        # revert side to move
        self.white_to_move = not self.white_to_move
        # undo promotion
        if m.promotion is not None:
            piece = 'P' if m.promotion.isupper() else 'p'
        self.set(sr, sc, piece)
        # undo capture/en passant
        if m.is_en_passant:
            # restore captured pawn behind
            self.set(sr, ec, 'p' if piece.isupper() else 'P')
            self.set(er, ec, '.')
        else:
            self.set(er, ec, captured if captured is not None else '.')

        # undo rook moves for castling
        if piece == 'K' and m.is_castle:
            if (er, ec) == (7, 6):
                self.set(7, 7, 'R')
                self.set(7, 5, '.')
            elif (er, ec) == (7, 2):
                self.set(7, 0, 'R')
                self.set(7, 3, '.')
        if piece == 'k' and m.is_castle:
            if (er, ec) == (0, 6):
                self.set(0, 7, 'r')
                self.set(0, 5, '.')
            elif (er, ec) == (0, 2):
                self.set(0, 0, 'r')
                self.set(0, 3, '.')

        # restore EP and castling rights (en passant can be recomputed simply to None)
        self.en_passant_target = None
        self.castling_rights = castling_copy

    def _legal_after(self, m: Move) -> bool:
        captured = self._make_move(m)
        kpos = self.king_pos(not self.white_to_move)  # after move, opponent to move; we check mover's king
        illegal = self._square_attacked(kpos, (not self.white_to_move))
        self._unmake_last()
        return not illegal

    # Public make move used by UI (assumes already legal)
    def push(self, m: Move) -> None:
        self._make_move(m)

    def legal_moves_from(self, r: int, c: int) -> List[Move]:
        return [m for m in self.gen_moves(self.white_to_move) if m.start == (r, c)]

    def in_check(self, white: bool) -> bool:
        k = self.king_pos(white)
        return self._square_attacked(k, white)

    def outcome(self) -> Optional[str]:
        moves = self.gen_moves(self.white_to_move)
        if moves:
            return None
        if self.in_check(self.white_to_move):
            return 'checkmate'
        return 'stalemate'


# --- UI ---
PIECE_GLYPH = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess - Pygame")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI Symbol", 56)
        self.small = pygame.font.SysFont("Segoe UI", 22)
        self.big = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.board = Board()
        self.selected: Optional[Tuple[int, int]] = None
        self.legal_from_sel: List[Move] = []
        self.status_msg = "White to move"
        self.promotion_move: Optional[Move] = None
        self.running = True

    def draw_board(self) -> None:
        for r in range(8):
            for c in range(8):
                color = LIGHT if (r + c) % 2 == 0 else DARK
                rect = pygame.Rect(c * SQUARE, r * SQUARE, SQUARE, SQUARE)
                pygame.draw.rect(self.screen, color, rect)
        # Highlights
        if self.selected is not None:
            sr, sc = self.selected
            pygame.draw.rect(self.screen, HL, (sc * SQUARE, sr * SQUARE, SQUARE, SQUARE), 4)
            for m in self.legal_from_sel:
                er, ec = m.end
                pygame.draw.rect(self.screen, MOVE_HL, (ec * SQUARE + 8, er * SQUARE + 8, SQUARE - 16, SQUARE - 16), 4)
        # Check highlight
        if self.board.in_check(self.board.white_to_move):
            kr, kc = self.board.king_pos(self.board.white_to_move)
            pygame.draw.rect(self.screen, CHECK_HL, (kc * SQUARE, kr * SQUARE, SQUARE, SQUARE), 6)
        # Pieces
        for r in range(8):
            for c in range(8):
                p = self.board.get(r, c)
                if p == '.':
                    continue
                glyph = PIECE_GLYPH[p]
                text = self.font.render(glyph, True, (30, 30, 30) if p.islower() else (10, 10, 10))
                rect = text.get_rect(center=(c * SQUARE + SQUARE // 2, r * SQUARE + SQUARE // 2))
                self.screen.blit(text, rect)

        # Status area
        pygame.draw.rect(self.screen, UI, (0, 8 * SQUARE, WIDTH, HEIGHT - 8 * SQUARE))
        msg = self.big.render(self.status_msg, True, TEXT)
        self.screen.blit(msg, (16, 8 * SQUARE + 12))

    def click_square(self, pos: Tuple[int, int]) -> None:
        x, y = pos
        if y >= 8 * SQUARE:
            return
        c = x // SQUARE
        r = y // SQUARE

        if self.promotion_move is not None:
            return  # ignore clicks during promotion selection

        p = self.board.get(r, c)
        turn_color = 'w' if self.board.white_to_move else 'b'
        if self.selected is None:
            if p != '.' and self.board.color(p) == turn_color:
                self.selected = (r, c)
                self.legal_from_sel = self.board.legal_moves_from(r, c)
        else:
            # attempt to make a move to (r, c)
            for m in self.legal_from_sel:
                if m.end == (r, c):
                    # handle promotion selection if needed
                    piece = self.board.get(self.selected[0], self.selected[1])
                    if piece.upper() == 'P' and (r == 0 or r == 7) and m.promotion is None:
                        # open promotion chooser
                        self.promotion_move = Move(m.start, m.end)
                    else:
                        self._do_move(m)
                    break
            self.selected = None
            self.legal_from_sel = []

    def _do_move(self, m: Move) -> None:
        self.board.push(m)
        outcome = self.board.outcome()
        if outcome is None:
            self.status_msg = ("White" if self.board.white_to_move else "Black") + " to move"
        elif outcome == 'checkmate':
            self.status_msg = ("Black" if self.board.white_to_move else "White") + " wins by checkmate. Press R to restart"
        else:
            self.status_msg = "Stalemate. Press R to restart"

    def draw_promotion(self) -> None:
        if self.promotion_move is None:
            return
        # Simple overlay with four options
        overlay = pygame.Surface((WIDTH, 8 * SQUARE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        choices = ['Q', 'R', 'B', 'N']
        white = self.board.white_to_move  # after selecting, side has not switched yet
        base_x = WIDTH // 2 - 2 * 90 + 45
        for i, ch in enumerate(choices):
            piece = ch if white else ch.lower()
            rect = pygame.Rect(base_x + i * 90, 8 * 40 - 140, 80, 80)
            pygame.draw.rect(self.screen, (240, 240, 240), rect, border_radius=8)
            glyph = PIECE_GLYPH[piece]
            text = self.font.render(glyph, True, (20, 20, 20))
            self.screen.blit(text, text.get_rect(center=rect.center))

    def handle_promotion_click(self, pos: Tuple[int, int]) -> None:
        if self.promotion_move is None:
            return
        base_x = WIDTH // 2 - 2 * 90 + 45
        for i, ch in enumerate(['Q', 'R', 'B', 'N']):
            rect = pygame.Rect(base_x + i * 90, 8 * 40 - 140, 80, 80)
            if rect.collidepoint(pos):
                piece = ch if self.board.white_to_move else ch.lower()
                m = Move(self.promotion_move.start, self.promotion_move.end, promotion=piece)
                self.promotion_move = None
                self._do_move(m)
                break

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if event.key == pygame.K_r:
                        self.board = Board()
                        self.selected = None
                        self.legal_from_sel = []
                        self.status_msg = "White to move"
                        self.promotion_move = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.promotion_move is not None:
                        self.handle_promotion_click(event.pos)
                    else:
                        self.click_square(event.pos)

            self.screen.fill((0, 0, 0))
            self.draw_board()
            self.draw_promotion()
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()


