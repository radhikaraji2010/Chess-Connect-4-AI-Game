import sys
import math
from typing import List, Optional, Tuple

import pygame


# Game constants
ROWS: int = 6
COLUMNS: int = 7
CONNECT_N: int = 4

CELL_SIZE: int = 100
PADDING: int = 20
PIECE_RADIUS: int = CELL_SIZE // 2 - 8

BOARD_WIDTH: int = COLUMNS * CELL_SIZE
BOARD_HEIGHT: int = (ROWS + 1) * CELL_SIZE  # extra row on top for hover

BACKGROUND_COLOR = (18, 24, 33)
BOARD_COLOR = (25, 38, 52)
GRID_COLOR = (34, 48, 67)
PLAYER1_COLOR = (239, 83, 80)     # red
PLAYER2_COLOR = (66, 165, 245)    # blue
HOVER_COLOR = (255, 241, 118)     # yellow
TEXT_COLOR = (232, 238, 246)


def create_board() -> List[List[int]]:
    return [[0 for _ in range(COLUMNS)] for _ in range(ROWS)]


def find_next_open_row(board: List[List[int]], col: int) -> Optional[int]:
    for r in reversed(range(ROWS)):
        if board[r][col] == 0:
            return r
    return None


def drop_piece(board: List[List[int]], row: int, col: int, player: int) -> None:
    board[row][col] = player


def is_valid_location(board: List[List[int]], col: int) -> bool:
    return board[0][col] == 0


def winning_move(board: List[List[int]], player: int) -> bool:
    # Horizontal
    for r in range(ROWS):
        for c in range(COLUMNS - 3):
            if all(board[r][c + i] == player for i in range(CONNECT_N)):
                return True

    # Vertical
    for c in range(COLUMNS):
        for r in range(ROWS - 3):
            if all(board[r + i][c] == player for i in range(CONNECT_N)):
                return True

    # Positive slope diagonals
    for r in range(ROWS - 3):
        for c in range(COLUMNS - 3):
            if all(board[r + i][c + i] == player for i in range(CONNECT_N)):
                return True

    # Negative slope diagonals
    for r in range(3, ROWS):
        for c in range(COLUMNS - 3):
            if all(board[r - i][c + i] == player for i in range(CONNECT_N)):
                return True

    return False


def board_full(board: List[List[int]]) -> bool:
    return all(board[0][c] != 0 for c in range(COLUMNS))


# ---------------------- AI (Minimax with Alpha-Beta) ----------------------
AI_PLAYER: int = 2
HUMAN_PLAYER: int = 1
AI_SEARCH_DEPTH: int = 4


def get_valid_columns(board: List[List[int]]) -> List[int]:
    return [c for c in range(COLUMNS) if is_valid_location(board, c)]


def copy_board(board: List[List[int]]) -> List[List[int]]:
    return [row[:] for row in board]


def is_terminal_node(board: List[List[int]]) -> bool:
    return winning_move(board, HUMAN_PLAYER) or winning_move(board, AI_PLAYER) or board_full(board)


def score_window(window: List[int], player: int) -> int:
    score = 0
    opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER
    count_player = window.count(player)
    count_empty = window.count(0)
    count_opponent = window.count(opponent)

    if count_player == 4:
        score += 10000
    elif count_player == 3 and count_empty == 1:
        score += 100
    elif count_player == 2 and count_empty == 2:
        score += 10

    if count_opponent == 3 and count_empty == 1:
        score -= 90

    return score


def score_position(board: List[List[int]], player: int) -> int:
    score = 0

    # Prefer center column
    center_col = [board[r][COLUMNS // 2] for r in range(ROWS)]
    score += center_col.count(player) * 6

    # Horizontal
    for r in range(ROWS):
        row_array = [board[r][c] for c in range(COLUMNS)]
        for c in range(COLUMNS - 3):
            window = row_array[c:c + 4]
            score += score_window(window, player)

    # Vertical
    for c in range(COLUMNS):
        col_array = [board[r][c] for r in range(ROWS)]
        for r in range(ROWS - 3):
            window = col_array[r:r + 4]
            score += score_window(window, player)

    # Positive diagonals
    for r in range(ROWS - 3):
        for c in range(COLUMNS - 3):
            window = [board[r + i][c + i] for i in range(4)]
            score += score_window(window, player)

    # Negative diagonals
    for r in range(3, ROWS):
        for c in range(COLUMNS - 3):
            window = [board[r - i][c + i] for i in range(4)]
            score += score_window(window, player)

    return score


def minimax(board: List[List[int]], depth: int, alpha: int, beta: int, maximizing: bool) -> Tuple[Optional[int], int]:
    if depth == 0 or is_terminal_node(board):
        if winning_move(board, AI_PLAYER):
            return None, 10_000_000
        if winning_move(board, HUMAN_PLAYER):
            return None, -10_000_000
        return None, score_position(board, AI_PLAYER)

    valid_columns = get_valid_columns(board)
    if not valid_columns:
        return None, 0

    # Order moves: try center first for better pruning
    valid_columns.sort(key=lambda c: abs(c - COLUMNS // 2))

    best_col = valid_columns[0]
    if maximizing:
        value = -math.inf
        for col in valid_columns:
            row = find_next_open_row(board, col)
            if row is None:
                continue
            temp = copy_board(board)
            drop_piece(temp, row, col, AI_PLAYER)
            _, new_score = minimax(temp, depth - 1, alpha, beta, False)
            if new_score > value:
                value = new_score
                best_col = col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return best_col, int(value)
    else:
        value = math.inf
        for col in valid_columns:
            row = find_next_open_row(board, col)
            if row is None:
                continue
            temp = copy_board(board)
            drop_piece(temp, row, col, HUMAN_PLAYER)
            _, new_score = minimax(temp, depth - 1, alpha, beta, True)
            if new_score < value:
                value = new_score
                best_col = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return best_col, int(value)


def draw_board(screen: pygame.Surface, board: List[List[int]], hover_col: Optional[int]) -> None:
    screen.fill(BACKGROUND_COLOR)

    # Top hover row background
    top_rect = pygame.Rect(0, 0, BOARD_WIDTH, CELL_SIZE)
    pygame.draw.rect(screen, BOARD_COLOR, top_rect)

    # Hover piece
    if hover_col is not None:
        cx = hover_col * CELL_SIZE + CELL_SIZE // 2
        cy = CELL_SIZE // 2
        pygame.draw.circle(screen, HOVER_COLOR, (cx, cy), PIECE_RADIUS)

    # Board grid
    board_rect = pygame.Rect(0, CELL_SIZE, BOARD_WIDTH, ROWS * CELL_SIZE)
    pygame.draw.rect(screen, BOARD_COLOR, board_rect)

    for r in range(ROWS):
        for c in range(COLUMNS):
            cell_center = (c * CELL_SIZE + CELL_SIZE // 2, (r + 1) * CELL_SIZE + CELL_SIZE // 2)
            pygame.draw.circle(screen, GRID_COLOR, cell_center, PIECE_RADIUS + 4)
            val = board[r][c]
            if val == 1:
                pygame.draw.circle(screen, PLAYER1_COLOR, cell_center, PIECE_RADIUS)
            elif val == 2:
                pygame.draw.circle(screen, PLAYER2_COLOR, cell_center, PIECE_RADIUS)


def draw_text_center(screen: pygame.Surface, text: str, y: int, size: int = 36) -> None:
    font = pygame.font.SysFont(None, size, bold=True)
    surf = font.render(text, True, TEXT_COLOR)
    rect = surf.get_rect(center=(BOARD_WIDTH // 2, y))
    screen.blit(surf, rect)


def game_loop(vs_ai: bool = True) -> None:
    pygame.init()
    pygame.display.set_caption("Connect 4")
    screen = pygame.display.set_mode((BOARD_WIDTH, BOARD_HEIGHT))
    clock = pygame.time.Clock()

    board = create_board()
    current_player = HUMAN_PLAYER
    game_over = False
    hover_col: Optional[int] = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.MOUSEMOTION:
                x, _ = event.pos
                hover_col = max(0, min(COLUMNS - 1, x // CELL_SIZE))

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over and (not vs_ai or current_player == HUMAN_PLAYER):
                x, _ = event.pos
                col = x // CELL_SIZE
                if 0 <= col < COLUMNS and is_valid_location(board, col):
                    row = find_next_open_row(board, col)
                    if row is not None:
                        drop_piece(board, row, col, current_player)

                        if winning_move(board, current_player):
                            game_over = True
                        elif board_full(board):
                            game_over = True
                            current_player = 0  # tie
                        else:
                            current_player = AI_PLAYER if current_player == HUMAN_PLAYER else HUMAN_PLAYER

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Reset
                    board = create_board()
                    current_player = 1
                    game_over = False

        # AI move when it's AI's turn
        if vs_ai and not game_over and current_player == AI_PLAYER:
            pygame.time.delay(250)
            col, _ = minimax(board, AI_SEARCH_DEPTH, -math.inf, math.inf, True)
            if col is not None and is_valid_location(board, col):
                row = find_next_open_row(board, col)
                if row is not None:
                    drop_piece(board, row, col, AI_PLAYER)
                    if winning_move(board, AI_PLAYER):
                        game_over = True
                    elif board_full(board):
                        game_over = True
                        current_player = 0
                    else:
                        current_player = HUMAN_PLAYER

        draw_board(screen, board, hover_col)

        # Status text
        if game_over:
            if current_player == 0:
                draw_text_center(screen, "It's a tie! Press R to restart", 28, 28)
            else:
                draw_text_center(screen, f"Player {current_player} wins! Press R to restart", 28, 28)
        else:
            if vs_ai and current_player == AI_PLAYER:
                draw_text_center(screen, "AI is thinking...", 28, 28)
            else:
                draw_text_center(screen, f"Player {current_player}'s turn", 28, 28)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    game_loop(vs_ai=True)


