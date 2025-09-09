import copy
import math
from typing import List, Tuple, Optional, Dict
import pygame


File = int
Rank = int
Square = Tuple[Rank, File]


class ChessGame:
    def __init__(self) -> None:
        self.board: List[List[str]] = self._initial_board()
        self.white_to_move: bool = True
        self.castling_rights: Dict[str, bool] = {
            'K': True,  # White king-side
            'Q': True,  # White queen-side
            'k': True,  # Black king-side
            'q': True   # Black queen-side
        }
        self.en_passant: Optional[Square] = None  # Target square if available
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1

    def _initial_board(self) -> List[List[str]]:
        return [
            list("rnbqkbnr"),
            list("pppppppp"),
            list("........"),
            list("........"),
            list("........"),
            list("........"),
            list("PPPPPPPP"),
            list("RNBQKBNR"),
        ]

    # -------------------- Utilities --------------------
    @staticmethod
    def in_bounds(r: int, f: int) -> bool:
        return 0 <= r < 8 and 0 <= f < 8

    @staticmethod
    def is_white(piece: str) -> bool:
        return piece.isupper()

    @staticmethod
    def is_black(piece: str) -> bool:
        return piece.islower()

    def side_to_move_is_white(self) -> bool:
        return self.white_to_move

    def get_king_square(self, white: bool) -> Optional[Square]:
        target = 'K' if white else 'k'
        for r in range(8):
            for f in range(8):
                if self.board[r][f] == target:
                    return (r, f)
        return None

    # -------------------- Move generation --------------------
    def generate_legal_moves(self) -> List[Tuple[Square, Square, Optional[str]]]:
        moves: List[Tuple[Square, Square, Optional[str]]] = []
        for r in range(8):
            for f in range(8):
                piece = self.board[r][f]
                if piece == '.':
                    continue
                if self.white_to_move and not self.is_white(piece):
                    continue
                if (not self.white_to_move) and not self.is_black(piece):
                    continue
                pseudo = self._generate_pseudo_moves_for_piece((r, f), piece)
                for (r2, f2, promo) in pseudo:
                    if self._is_legal_move((r, f), (r2, f2), promo):
                        moves.append(((r, f), (r2, f2), promo))
        return moves

    def _generate_pseudo_moves_for_piece(self, sq: Square, piece: str) -> List[Tuple[int, int, Optional[str]]]:
        r, f = sq
        moves: List[Tuple[int, int, Optional[str]]] = []
        white = self.is_white(piece)
        direction = -1 if white else 1
        enemy = (self.is_black if white else self.is_white)

        if piece.upper() == 'P':
            # Single push
            r1 = r + direction
            if self.in_bounds(r1, f) and self.board[r1][f] == '.':
                if r1 == (0 if white else 7):
                    moves.extend([(r1, f, p) for p in ['Q', 'R', 'B', 'N']])
                else:
                    moves.append((r1, f, None))
                # Double push
                start_rank = 6 if white else 1
                r2 = r + 2 * direction
                if r == start_rank and self.board[r2][f] == '.':
                    moves.append((r2, f, None))
            # Captures
            for df in (-1, 1):
                rf = r + direction
                ff = f + df
                if self.in_bounds(rf, ff):
                    target = self.board[rf][ff]
                    if target != '.' and enemy(target):
                        if rf == (0 if white else 7):
                            moves.extend([(rf, ff, p) for p in ['Q', 'R', 'B', 'N']])
                        else:
                            moves.append((rf, ff, None))
            # En passant
            if self.en_passant is not None:
                er, ef = self.en_passant
                if r + direction == er and abs(f - ef) == 1:
                    moves.append((er, ef, None))

        elif piece.upper() == 'N':
            for dr, df in [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]:
                rr, ff = r + dr, f + df
                if self.in_bounds(rr, ff):
                    target = self.board[rr][ff]
                    if target == '.' or enemy(target):
                        moves.append((rr, ff, None))

        elif piece.upper() == 'B':
            moves.extend(self._sliding_moves(r, f, enemy, [(1, 1), (1, -1), (-1, 1), (-1, -1)]))

        elif piece.upper() == 'R':
            moves.extend(self._sliding_moves(r, f, enemy, [(1, 0), (-1, 0), (0, 1), (0, -1)]))

        elif piece.upper() == 'Q':
            moves.extend(self._sliding_moves(r, f, enemy, [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]))

        elif piece.upper() == 'K':
            for dr in (-1, 0, 1):
                for df in (-1, 0, 1):
                    if dr == 0 and df == 0:
                        continue
                    rr, ff = r + dr, f + df
                    if self.in_bounds(rr, ff):
                        target = self.board[rr][ff]
                        if target == '.' or enemy(target):
                            moves.append((rr, ff, None))
            # Castling
            moves.extend(self._castle_moves(white))

        return moves

    def _sliding_moves(self, r: int, f: int, enemy_pred, directions: List[Tuple[int, int]]) -> List[Tuple[int, int, Optional[str]]]:
        piece_moves: List[Tuple[int, int, Optional[str]]] = []
        for dr, df in directions:
            rr, ff = r + dr, f + df
            while self.in_bounds(rr, ff):
                target = self.board[rr][ff]
                if target == '.':
                    piece_moves.append((rr, ff, None))
                else:
                    if enemy_pred(target):
                        piece_moves.append((rr, ff, None))
                    break
                rr += dr
                ff += df
        return piece_moves

    def _castle_moves(self, white: bool) -> List[Tuple[int, int, Optional[str]]]:
        moves: List[Tuple[int, int, Optional[str]]] = []
        r = 7 if white else 0
        king_file = 4
        if white:
            if self.castling_rights['K'] and self.board[r][5] == '.' and self.board[r][6] == '.':
                if not self._square_attacked((r, 4), not white) and not self._square_attacked((r, 5), not white) and not self._square_attacked((r, 6), not white):
                    moves.append((r, 6, None))
            if self.castling_rights['Q'] and self.board[r][1] == '.' and self.board[r][2] == '.' and self.board[r][3] == '.':
                if not self._square_attacked((r, 4), not white) and not self._square_attacked((r, 3), not white) and not self._square_attacked((r, 2), not white):
                    moves.append((r, 2, None))
        else:
            if self.castling_rights['k'] and self.board[r][5] == '.' and self.board[r][6] == '.':
                if not self._square_attacked((r, 4), white) and not self._square_attacked((r, 5), white) and not self._square_attacked((r, 6), white):
                    moves.append((r, 6, None))
            if self.castling_rights['q'] and self.board[r][1] == '.' and self.board[r][2] == '.' and self.board[r][3] == '.':
                if not self._square_attacked((r, 4), white) and not self._square_attacked((r, 3), white) and not self._square_attacked((r, 2), white):
                    moves.append((r, 2, None))
        return moves

    # -------------------- Legality --------------------
    def _is_legal_move(self, src: Square, dst: Square, promo: Optional[str]) -> bool:
        game_copy = copy.deepcopy(self)
        if not game_copy._apply_move(src, dst, promo, validate=False):
            return False
        return not game_copy._in_check(white=self.white_to_move)

    def _in_check(self, white: bool) -> bool:
        king_sq = self.get_king_square(white)
        if king_sq is None:
            return True
        return self._square_attacked(king_sq, by_white=not white)

    def _square_attacked(self, sq: Square, by_white: bool) -> bool:
        r, f = sq
        for rr in range(8):
            for ff in range(8):
                piece = self.board[rr][ff]
                if piece == '.':
                    continue
                if by_white and not self.is_white(piece):
                    continue
                if (not by_white) and not self.is_black(piece):
                    continue
                for (tr, tf, promo) in self._generate_pseudo_moves_for_piece((rr, ff), piece):
                    if (tr, tf) == (r, f):
                        # Special-case pawns: ensure attacks align (they cannot attack forward)
                        if piece.upper() == 'P':
                            direction = -1 if self.is_white(piece) else 1
                            if tr == rr + direction and abs(tf - ff) == 1:
                                return True
                        else:
                            return True
        return False

    # -------------------- Apply/Make Move --------------------
    def _apply_move(self, src: Square, dst: Square, promo: Optional[str], validate: bool = True) -> bool:
        sr, sf = src
        dr, df = dst
        piece = self.board[sr][sf]
        if piece == '.':
            return False
        if validate:
            legal = self.generate_legal_moves()
            if (src, dst, promo) not in legal:
                # Allow matching promotion ignoring case in tuple equality by checking set
                if not any(m[0] == src and m[1] == dst and (m[2] == promo) for m in legal):
                    return False

        # Manage castling rights before move
        self._update_castling_rights_before_move(src, dst)

        # En passant capture
        if piece.upper() == 'P' and self.en_passant is not None and dst == self.en_passant and sf != df and self.board[dr][df] == '.':
            # Capturing pawn is behind the target square
            cap_r = dr + (1 if self.is_white(piece) else -1)
            self.board[cap_r][df] = '.'

        # Move the piece
        self.board[dr][df] = piece
        self.board[sr][sf] = '.'

        # Pawn promotion (promote to chosen or queen by default)
        if piece.upper() == 'P' and (dr == 0 or dr == 7):
            self.board[dr][df] = (promo if promo in ['Q', 'R', 'B', 'N'] else 'Q') if piece.isupper() else (promo.lower() if promo else 'q')

        # Castling rook move
        if piece.upper() == 'K' and abs(df - sf) == 2:
            r = dr
            if df == 6:  # king side
                self.board[r][5] = self.board[r][7]
                self.board[r][7] = '.'
            elif df == 2:  # queen side
                self.board[r][3] = self.board[r][0]
                self.board[r][0] = '.'

        # Set en passant target
        if piece.upper() == 'P' and abs(dr - sr) == 2:
            self.en_passant = (sr + (1 if piece.islower() else -1), sf)
        else:
            self.en_passant = None

        # Halfmove clock
        if piece.upper() == 'P' or self.board[dr][df] != '.':
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Turn and move number
        if not self.white_to_move:
            self.fullmove_number += 1
        self.white_to_move = not self.white_to_move

        return True

    def _update_castling_rights_before_move(self, src: Square, dst: Square) -> None:
        sr, sf = src
        dr, df = dst
        piece = self.board[sr][sf]
        # If king or rook moves, remove rights
        if piece == 'K':
            self.castling_rights['K'] = False
            self.castling_rights['Q'] = False
        if piece == 'k':
            self.castling_rights['k'] = False
            self.castling_rights['q'] = False
        if piece == 'R' and sr == 7 and sf == 0:
            self.castling_rights['Q'] = False
        if piece == 'R' and sr == 7 and sf == 7:
            self.castling_rights['K'] = False
        if piece == 'r' and sr == 0 and sf == 0:
            self.castling_rights['q'] = False
        if piece == 'r' and sr == 0 and sf == 7:
            self.castling_rights['k'] = False
        # If a rook is captured, remove rights accordingly
        if dr == 7 and df == 0 and self.board[dr][df] == 'r':
            self.castling_rights['Q'] = False
        if dr == 7 and df == 7 and self.board[dr][df] == 'r':
            self.castling_rights['K'] = False
        if dr == 0 and df == 0 and self.board[dr][df] == 'R':
            self.castling_rights['q'] = False
        if dr == 0 and df == 7 and self.board[dr][df] == 'R':
            self.castling_rights['k'] = False

    # -------------------- Status --------------------
    def is_checkmate(self) -> bool:
        if not self._in_check(white=self.white_to_move):
            return False
        return len(self.generate_legal_moves()) == 0

    def is_stalemate(self) -> bool:
        if self._in_check(white=self.white_to_move):
            return False
        return len(self.generate_legal_moves()) == 0

    # -------------------- I/O helpers --------------------
    def print_board(self) -> None:
        print("  +------------------------+")
        for r in range(8):
            rank_str = str(8 - r) + " | "
            for f in range(8):
                rank_str += (self.board[r][f] + ' ')
            print(rank_str + "|")
        print("  +------------------------+")
        print("    a b c d e f g h")

    @staticmethod
    def parse_move(move_str: str) -> Optional[Tuple[Square, Square, Optional[str]]]:
        s = move_str.strip().lower()
        if len(s) not in (4, 5):
            return None
        ffile = ord(s[0]) - ord('a')
        frank = 8 - int(s[1])
        tfile = ord(s[2]) - ord('a')
        trank = 8 - int(s[3])
        if not (0 <= ffile < 8 and 0 <= frank < 8 and 0 <= tfile < 8 and 0 <= trank < 8):
            return None
        promo: Optional[str] = None
        if len(s) == 5:
            promo_map = {'q': 'Q', 'r': 'R', 'b': 'B', 'n': 'N'}
            promo = promo_map.get(s[4])
        return ((frank, ffile), (trank, tfile), promo)

    # -------------------- AI --------------------
    def ai_move(self, depth: int = 2) -> Optional[Tuple[Square, Square, Optional[str]]]:
        legal = self.generate_legal_moves()
        if not legal:
            return None
        best_move = None
        best_score = -math.inf if self.white_to_move else math.inf
        alpha = -math.inf
        beta = math.inf
        for mv in legal:
            game_copy = copy.deepcopy(self)
            game_copy._apply_move(mv[0], mv[1], mv[2], validate=False)
            score = self._minimax(game_copy, depth - 1, alpha, beta)
            if self.white_to_move:
                if score > best_score:
                    best_score = score
                    best_move = mv
                alpha = max(alpha, score)
            else:
                if score < best_score:
                    best_score = score
                    best_move = mv
                beta = min(beta, score)
            if beta <= alpha:
                break
        return best_move if best_move is not None else legal[0]

    def _minimax(self, game: 'ChessGame', depth: int, alpha: float, beta: float) -> float:
        if depth == 0:
            return self._evaluate(game)
        legal = game.generate_legal_moves()
        if not legal:
            if game.is_checkmate():
                return -99999 if game.white_to_move else 99999
            return 0
        if game.white_to_move:
            value = -math.inf
            for mv in legal:
                nxt = copy.deepcopy(game)
                nxt._apply_move(mv[0], mv[1], mv[2], validate=False)
                value = max(value, self._minimax(nxt, depth - 1, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = math.inf
            for mv in legal:
                nxt = copy.deepcopy(game)
                nxt._apply_move(mv[0], mv[1], mv[2], validate=False)
                value = min(value, self._minimax(nxt, depth - 1, alpha, beta))
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    @staticmethod
    def _evaluate(game: 'ChessGame') -> float:
        values = {
            'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
            'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': 0,
            '.': 0
        }
        score = 0
        for r in range(8):
            for f in range(8):
                score += values.get(game.board[r][f], 0)
        # Side to move slight bonus
        score += 10 if game.white_to_move else -10
        return score


def main() -> None:
    print("Classic Chess (Human vs AI) - Text Mode")
    print("Input moves like e2e4, e7e8q for promotion to queen.")
    print("Type 'help' to see options, 'quit' to exit.\n")

    game = ChessGame()
    ai_depth = 2

    while True:
        game.print_board()
        if game.is_checkmate():
            print("Checkmate!", "Black" if game.white_to_move else "White", "wins.")
            break
        if game.is_stalemate():
            print("Stalemate. Draw.")
            break

        if game.white_to_move:
            print("White to move.")
            move_str = input("Your move (e2e4): ").strip()
            if move_str.lower() in ("quit", "exit"):  # exit command
                print("Goodbye!")
                break
            if move_str.lower() in ("help",):
                print("- Enter moves like e2e4 or e7e8q for promotion.")
                print("- Type 'quit' to exit.")
                print("- Moves are validated for legality including check.")
                continue
            parsed = ChessGame.parse_move(move_str)
            if parsed is None:
                print("Invalid format. Use e2e4 or e7e8q.")
                continue
            if not game._apply_move(parsed[0], parsed[1], parsed[2], validate=True):
                print("Illegal move. Try again.")
                continue
        else:
            print("Black (AI) thinking...")
            mv = game.ai_move(depth=ai_depth)
            if mv is None:
                # No legal moves
                continue
            game._apply_move(mv[0], mv[1], mv[2], validate=False)


if __name__ == "__main__":
    # Launch the GUI directly as a two-player local game.
    run_gui(vs_ai=False)

######################################################################
#                           Pygame GUI                                #
######################################################################

def piece_to_unicode(piece: str) -> str:
    mapping = {
        'K': '\u2654', 'Q': '\u2655', 'R': '\u2656', 'B': '\u2657', 'N': '\u2658', 'P': '\u2659',
        'k': '\u265A', 'q': '\u265B', 'r': '\u265C', 'b': '\u265D', 'n': '\u265E', 'p': '\u265F',
    }
    return mapping.get(piece, '')


def run_gui(vs_ai: bool = False) -> None:
    pygame.init()
    pygame.display.set_caption("Chess - Two Player")

    # Scale board to screen
    info = pygame.display.Info()
    max_w = int(info.current_w * 0.9)
    max_h = int(info.current_h * 0.9)
    base_cell = 90
    base_margin = 20
    base_status = 64
    desired_w = base_margin * 2 + base_cell * 8
    desired_h = base_margin * 2 + base_cell * 8 + base_status
    scale = min(max_w / desired_w, max_h / desired_h, 1.0)
    CELL = max(60, int(base_cell * scale))
    MARGIN = max(12, int(base_margin * scale))
    STATUS_H = max(48, int(base_status * scale))
    WIDTH = MARGIN * 2 + CELL * 8
    HEIGHT = MARGIN * 2 + CELL * 8 + STATUS_H

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Colors
    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    HIGHLIGHT = (246, 246, 105)
    MOVE_HINT = (115, 149, 82)
    STATUS_BG = (36, 46, 61)
    STATUS_TEXT = (232, 238, 246)

    piece_font = pygame.font.SysFont("Segoe UI Symbol", int(CELL * 0.8))
    status_font = pygame.font.SysFont(None, int(STATUS_H * 0.5), bold=True)

    game = ChessGame()
    ai_depth = 2  # used only if vs_ai=True
    selected: Optional[Tuple[int, int]] = None
    legal_for_selected: List[Tuple[Tuple[int, int], Tuple[int, int], Optional[str]]] = []
    status_text = "White to move"
    promotion_menu: Optional[Tuple[Tuple[int, int], Tuple[int, int], List[Tuple[str, pygame.Rect]]]] = None

    def board_to_screen(r: int, f: int) -> Tuple[int, int, int, int]:
        x = MARGIN + f * CELL
        y = MARGIN + r * CELL
        return x, y, CELL, CELL

    def draw():
        screen.fill((20, 24, 28))
        # Board
        for r in range(8):
            for f in range(8):
                x, y, w, h = board_to_screen(r, f)
                color = LIGHT if (r + f) % 2 == 0 else DARK
                pygame.draw.rect(screen, color, (x, y, w, h))

        # Highlights for selected source
        if selected is not None:
            sx, sy, w, h = board_to_screen(*selected)
            pygame.draw.rect(screen, HIGHLIGHT, (sx, sy, w, h), 6)

        # Legal destination hints
        for (_, dst, promo) in legal_for_selected:
            dx, dy, w, h = board_to_screen(*dst)
            pygame.draw.rect(screen, MOVE_HINT, (dx + 6, dy + 6, w - 12, h - 12), 4)

        # Pieces
        for r in range(8):
            for f in range(8):
                piece = game.board[r][f]
                if piece == '.':
                    continue
                x, y, w, h = board_to_screen(r, f)
                glyph = piece_to_unicode(piece)
                if not glyph:
                    continue
                surf = piece_font.render(glyph, True, (10, 10, 10))
                rect = surf.get_rect(center=(x + w // 2, y + h // 2))
                screen.blit(surf, rect)

        # Status bar
        pygame.draw.rect(screen, STATUS_BG, (0, HEIGHT - STATUS_H, WIDTH, STATUS_H))
        st = status_font.render(status_text, True, STATUS_TEXT)
        screen.blit(st, (MARGIN, HEIGHT - STATUS_H + (STATUS_H - st.get_height()) // 2))

        # Promotion menu
        if promotion_menu is not None:
            (_, _), (_, _), choices = promotion_menu
            for label, rect in choices:
                pygame.draw.rect(screen, (230, 230, 230), rect, border_radius=6)
                ls = status_font.render(label, True, (20, 20, 30))
                screen.blit(ls, ls.get_rect(center=rect.center))

        pygame.display.flip()

    def mouse_to_square(pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        mx, my = pos
        if not (MARGIN <= mx < MARGIN + 8 * CELL and MARGIN <= my < MARGIN + 8 * CELL):
            return None
        f = (mx - MARGIN) // CELL
        r = (my - MARGIN) // CELL
        return int(r), int(f)

    def compute_legal_for_selected(sel: Tuple[int, int]) -> List[Tuple[Tuple[int, int], Tuple[int, int], Optional[str]]]:
        all_legal = game.generate_legal_moves()
        return [mv for mv in all_legal if mv[0] == sel]

    def open_promotion_menu(src: Tuple[int, int], dst: Tuple[int, int]) -> None:
        nonlocal promotion_menu
        # Create small set of buttons near status bar
        labels = ['Q', 'R', 'B', 'N']
        btn_w = int(CELL * 1.0)
        btn_h = int(STATUS_H * 0.7)
        start_x = WIDTH - MARGIN - (btn_w + 12) * len(labels)
        y = HEIGHT - STATUS_H + (STATUS_H - btn_h) // 2
        rects: List[Tuple[str, pygame.Rect]] = []
        for i, lab in enumerate(labels):
            rects.append((lab, pygame.Rect(start_x + i * (btn_w + 12), y, btn_w, btn_h)))
        promotion_menu = (src, dst, rects)

    def handle_promotion_click(mx: int, my: int) -> Optional[str]:
        nonlocal promotion_menu
        if promotion_menu is None:
            return None
        (src, dst, rects) = promotion_menu
        for lab, rect in rects:
            if rect.collidepoint(mx, my):
                promotion_menu = None
                return lab
        return None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game = ChessGame()
                    selected = None
                    legal_for_selected = []
                    status_text = "White to move"
                    promotion_menu = None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # If promotion menu is open, clicks choose piece
                if promotion_menu is not None:
                    choice = handle_promotion_click(mx, my)
                    if choice is not None:
                        # Complete pending promotion move (stored inside promotion_menu as src,dst)
                        (src, dst, _) = promotion_menu if promotion_menu is not None else ((0, 0), (0, 0), [])
                        # Above line won't run as promotion_menu is set to None in handler; keep safe default
                    # Redraw after closing/opening menu
                    draw()
                    continue

                sq = mouse_to_square((mx, my))
                if sq is None:
                    selected = None
                    legal_for_selected = []
                else:
                    # If selecting source
                    if selected is None:
                        piece = game.board[sq[0]][sq[1]]
                        if piece != '.' and ((game.white_to_move and piece.isupper()) or ((not game.white_to_move) and piece.islower())):
                            selected = sq
                            legal_for_selected = compute_legal_for_selected(selected)
                    else:
                        # Try to make a move to sq
                        cand = [mv for mv in legal_for_selected if mv[1] == sq]
                        if not cand:
                            # Click elsewhere to reselect or clear
                            piece = game.board[sq[0]][sq[1]]
                            if piece != '.' and ((game.white_to_move and piece.isupper()) or ((not game.white_to_move) and piece.islower())):
                                selected = sq
                                legal_for_selected = compute_legal_for_selected(selected)
                            else:
                                selected = None
                                legal_for_selected = []
                        else:
                            src, dst, promo = cand[0]
                            # If pawn promotion move (reaching last rank) without promo specified, open menu
                            piece = game.board[src[0]][src[1]]
                            if piece.upper() == 'P' and (dst[0] == 0 or dst[0] == 7) and promo is None:
                                open_promotion_menu(src, dst)
                            else:
                                if game._apply_move(src, dst, promo, validate=True):
                                    selected = None
                                    legal_for_selected = []
                                    status_text = ("Black is thinking..." if game.white_to_move is False else "White to move")

        # Complete promotion by polling menu choice state
        if promotion_menu is not None:
            # Draw to show menu
            draw()
            mx, my = pygame.mouse.get_pos()
            pressed = pygame.mouse.get_pressed()[0]
            if pressed:
                choice = handle_promotion_click(mx, my)
                if choice is not None:
                    (src, dst, _) = promotion_menu if promotion_menu is not None else ((0, 0), (0, 0), [])
                    # Apply with chosen promotion for correct side case
                    piece = game.board[src[0]][src[1]]
                    promo_symbol = choice if piece.isupper() else choice.lower()
                    game._apply_move(src, dst, promo_symbol, validate=True)
                    selected = None
                    legal_for_selected = []
                    status_text = ("Black is thinking..." if game.white_to_move is False else "White to move")
                    promotion_menu = None

        # AI move (Black) only if enabled
        if vs_ai and (not game.white_to_move) and promotion_menu is None:
            status_text = "Black is thinking..."
            pygame.display.set_caption("Chess - Human vs AI (thinking)")
            mv = game.ai_move(depth=ai_depth)
            if mv is not None:
                game._apply_move(mv[0], mv[1], mv[2], validate=False)
            pygame.display.set_caption("Chess - Human vs AI")
            status_text = "White to move"

        # Status messages for end states
        if game.is_checkmate():
            status_text = ("Checkmate! Black wins." if game.white_to_move else "Checkmate! White wins.") + " Press R to restart."
        elif game.is_stalemate():
            status_text = "Stalemate. Press R to restart."

        draw()
        clock.tick(60)

    pygame.quit()


