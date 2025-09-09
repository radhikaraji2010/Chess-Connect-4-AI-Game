import sys
import random
from typing import Dict, Tuple, List

import pygame


BOARD_SIZE = 10  # 10x10 squares, 1..100
# Base dimensions that will be scaled to fit screen
BASE_CELL = 70
BASE_MARGIN = 18
BASE_INFO_HEIGHT = 110

# Runtime-scaled dimensions (initialized later)
CELL = BASE_CELL
MARGIN = BASE_MARGIN
INFO_HEIGHT = BASE_INFO_HEIGHT
WIDTH = BOARD_SIZE * CELL + MARGIN * 2
HEIGHT = BOARD_SIZE * CELL + INFO_HEIGHT + MARGIN * 2

BACKGROUND = (18, 24, 33)
GRID = (34, 48, 67)
TEXT = (232, 238, 246)
P1 = (239, 83, 80)
P2 = (66, 165, 245)
DICE_BG = (25, 38, 52)

# Snakes and ladders mapping: start -> end
LADDERS: Dict[int, int] = {
    3: 22, 5: 8, 11: 26, 20: 29,
    27: 56, 36: 44, 51: 67, 71: 92,
}
SNAKES: Dict[int, int] = {
    17: 4, 19: 7, 21: 9, 43: 34,
    49: 30, 62: 19, 64: 60, 74: 53,
    89: 68, 95: 75, 99: 78,
}


def num_to_pos(n: int) -> Tuple[int, int]:
    # Convert board number (1..100) to grid (row, col), 0-based top-left origin
    n = max(1, min(100, n))
    row_from_bottom = (n - 1) // 10
    row = 9 - row_from_bottom
    left_to_right = row_from_bottom % 2 == 0
    col_in_row = (n - 1) % 10
    col = col_in_row if left_to_right else 9 - col_in_row
    return row, col


def cell_center(row: int, col: int) -> Tuple[int, int]:
    x = MARGIN + col * CELL + CELL // 2
    y = MARGIN + row * CELL + CELL // 2 + INFO_HEIGHT
    return x, y


def draw_board(screen: pygame.Surface, p1: int, p2: int, current: int, rolling: bool, dice_val: int, dice_button: pygame.Rect, enable_button: bool, hover_roll: bool = False) -> None:
    screen.fill(BACKGROUND)

    # Info panel
    info_rect = pygame.Rect(MARGIN, MARGIN, BOARD_SIZE * CELL, INFO_HEIGHT)
    pygame.draw.rect(screen, DICE_BG, info_rect, border_radius=12)

    font = pygame.font.SysFont(None, 28, bold=True)
    status = f"Player {current}'s turn. Click Roll to dice." if not rolling else "Rolling..."
    text = font.render(status, True, TEXT)
    screen.blit(text, (MARGIN + 16, MARGIN + 16))

    # Dice display box
    dice_display = pygame.Rect(WIDTH - MARGIN - int(1.5 * CELL), MARGIN + int(0.25 * CELL), int(1.2 * CELL), int(1.2 * CELL))
    pygame.draw.rect(screen, (50, 60, 75), dice_display, border_radius=10)
    if dice_val:
        dfont = pygame.font.SysFont(None, int(0.9 * CELL), bold=True)
        dsurf = dfont.render(str(dice_val), True, TEXT)
        drect = dsurf.get_rect(center=dice_display.center)
        screen.blit(dsurf, drect)

    # Roll button
    btn_color = (120, 185, 255) if (enable_button and hover_roll) else ((88, 160, 255) if enable_button else (80, 90, 110))
    pygame.draw.rect(screen, btn_color, dice_button, border_radius=10)
    bfont = pygame.font.SysFont(None, int(0.45 * dice_button.h), bold=True)
    blabel = bfont.render("Roll", True, (10, 14, 22))
    screen.blit(blabel, blabel.get_rect(center=dice_button.center))

    # Grid
    board_rect = pygame.Rect(MARGIN, MARGIN + INFO_HEIGHT, BOARD_SIZE * CELL, BOARD_SIZE * CELL)
    pygame.draw.rect(screen, DICE_BG, board_rect, border_radius=10)

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            rect = pygame.Rect(MARGIN + c * CELL, MARGIN + INFO_HEIGHT + r * CELL, CELL, CELL)
            pygame.draw.rect(screen, GRID, rect, 1)

            # Cell number (display only)
            row_from_bottom = (9 - r)
            left_to_right = row_from_bottom % 2 == 0
            base = row_from_bottom * 10
            num = base + (c + 1 if left_to_right else (10 - c))
            small = pygame.font.SysFont(None, 18)
            ns = small.render(str(num), True, GRID)
            screen.blit(ns, (rect.x + 4, rect.y + 4))

    # Snakes and Ladders lines (simple straight lines)
    for start, end in LADDERS.items():
        sr, sc = num_to_pos(start)
        er, ec = num_to_pos(end)
        pygame.draw.line(screen, (76, 175, 80), cell_center(sr, sc), cell_center(er, ec), 6)

    for start, end in SNAKES.items():
        sr, sc = num_to_pos(start)
        er, ec = num_to_pos(end)
        pygame.draw.line(screen, (244, 67, 54), cell_center(sr, sc), cell_center(er, ec), 6)

    # Turn indicator chip
    chip_color = P1 if current == 1 else P2
    pygame.draw.circle(screen, chip_color, (MARGIN + 24, MARGIN + 60), 10)

    # Players
    r1, c1 = num_to_pos(p1)
    r2, c2 = num_to_pos(p2)
    pygame.draw.circle(screen, P1, cell_center(r1, c1), 16)
    pygame.draw.circle(screen, P2, cell_center(r2, c2), 16)


def apply_snakes_ladders(pos: int) -> int:
    if pos in LADDERS:
        return LADDERS[pos]
    if pos in SNAKES:
        return SNAKES[pos]
    return pos


def setup_dimensions_to_fit_screen() -> None:
    """Scale global sizes to fit within current screen resolution."""
    global CELL, MARGIN, INFO_HEIGHT, WIDTH, HEIGHT
    info = pygame.display.Info()
    max_w = int(info.current_w * 0.95)
    max_h = int(info.current_h * 0.95)

    # Try scaling by the limiting factor
    desired_w = BOARD_SIZE * BASE_CELL + BASE_MARGIN * 2
    desired_h = BOARD_SIZE * BASE_CELL + BASE_INFO_HEIGHT + BASE_MARGIN * 2
    scale_w = max_w / desired_w
    scale_h = max_h / desired_h
    scale = min(scale_w, scale_h, 1.0)

    CELL = max(36, int(BASE_CELL * scale))
    MARGIN = max(12, int(BASE_MARGIN * scale))
    INFO_HEIGHT = max(80, int(BASE_INFO_HEIGHT * scale))
    WIDTH = BOARD_SIZE * CELL + MARGIN * 2
    HEIGHT = BOARD_SIZE * CELL + INFO_HEIGHT + MARGIN * 2


def game_loop(vs_ai: bool = True) -> None:
    pygame.init()
    pygame.display.set_caption("Snakes & Ladders")
    setup_dimensions_to_fit_screen()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    p1 = 1
    p2 = 1
    current = 1  # 1 = human, 2 = AI (when vs_ai)
    rolling = False
    dice_val = 0
    game_over = False

    # Dice button rect (position under info panel, right side)
    dice_button = pygame.Rect(WIDTH - MARGIN - int(1.6 * CELL), MARGIN + int(0.25 * CELL), int(1.4 * CELL), int(0.6 * CELL))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN and not game_over:
                if event.key == pygame.K_r:
                    p1, p2, current, rolling, dice_val, game_over = 1, 1, 1, False, 0, False

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    mouse_pos = event.pos
                    enable_button = (not rolling) and (not vs_ai or current == 1)
                    if enable_button and dice_button.collidepoint(mouse_pos):
                        # Human clicks Roll
                        rolling = True
                        for _ in range(12):
                            dice_val = random.randint(1, 6)
                            draw_board(screen, p1, p2, current, rolling, dice_val, dice_button, enable_button)
                            pygame.display.flip()
                            clock.tick(24)

                        rolling = False
                        steps = random.randint(1, 6)
                        dice_val = steps

                        tentative = p1 + steps
                        if tentative <= 100:
                            p1 = tentative
                            p1 = apply_snakes_ladders(p1)
                        if p1 == 100:
                            game_over = True
                        else:
                            current = 2 if vs_ai else 2

        # AI turn (auto-roll and move)
        if vs_ai and not game_over and current == 2 and not rolling:
            rolling = True
            for _ in range(12):
                dice_val = random.randint(1, 6)
                draw_board(screen, p1, p2, current, rolling, dice_val, dice_button, False)
                pygame.display.flip()
                clock.tick(24)

            rolling = False
            steps = random.randint(1, 6)
            dice_val = steps

            tentative = p2 + steps
            if tentative <= 100:
                p2 = tentative
                p2 = apply_snakes_ladders(p2)
            if p2 == 100:
                game_over = True
            else:
                current = 1

        enable_button = (not rolling) and (not game_over) and (not vs_ai or current == 1)
        hover_roll = dice_button.collidepoint(pygame.mouse.get_pos()) and enable_button
        draw_board(screen, p1, p2, current, rolling, dice_val, dice_button, enable_button, hover_roll)

        # Winner text
        if game_over:
            font = pygame.font.SysFont(None, 32, bold=True)
            winner = "Player 1" if p1 == 100 else "Player 2"
            msg = f"{winner} wins! Press R to restart"
            surf = font.render(msg, True, TEXT)
            rect = surf.get_rect(center=(WIDTH // 2, MARGIN + INFO_HEIGHT // 2))
            screen.blit(surf, rect)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    game_loop(vs_ai=True)


