# Connect 4 (Pygame)

## Setup (Windows PowerShell)

```powershell
cd "C:\Users\KanasaniR\Documents\Workspaces\Cursor\DemoProject"
py -m venv .venv
. .venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```powershell
python connect4.py
```

- Mouse to place pieces.
- R to restart a finished game.

## Notes
- Window size: 700x700 (fits 7x6 board with a top hover row).
- Two local players alternating turns; highlights winner or tie.

---

# Snakes & Ladders (Pygame)

## Run

```powershell
python snakes_ladders.py
```

- SPACE to roll dice (with quick roll animation)
- R to restart after a win
- Two players alternate turns automatically

Board: standard 1–100 with several snakes and ladders; first to 100 wins.

---

# Chess (Text-based, Human vs AI)

## Run in IDLE (Windows)

1. Open IDLE.
2. File → Open… and select `chess_game.py`.
3. Run → Run Module (F5).

Or via PowerShell:

```powershell
python chess_game.py
```

Usage:
- Enter moves in long algebraic: `e2e4`, `g1f3`, `e7e8q` (promotion).
- Legal-move validation, check, castling, en passant, checkmate/stalemate.
- Black is an AI with a simple minimax (depth 2 by default).

