from endplay.types import Deal, Vul, Player
from endplay.dds import par
from endplay.dealer import generate_deal
import numpy as np
import matplotlib.pyplot as plt
import random


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSITIONS = ["north", "east", "south", "west"]
VULS = ["none", "northsouth", "eastwest", "both"]

# Maps position string to (endplay Player, PBN notation)
POSITION_MAP = {
    "north": (Player.north, "N"),
    "east":  (Player.east,  "E"),
    "south": (Player.south, "S"),
    "west":  (Player.west,  "W"),
}

# Maps vulnerability string to (endplay Vul, PBN notation)
VUL_MAP = {
    "none":       (Vul.none, "None"),
    "northsouth": (Vul.ns,   "NS"),
    "eastwest":   (Vul.ew,   "EW"),
    "both":       (Vul.both, "All"),
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Board:
    """Lightweight board object used for server logic."""

    def __init__(self, number, deal, dealer, vul, contract, par_contract, score, par_score):
        self.number       = number
        self.deal         = deal
        self.dealer       = dealer
        self.vul          = vul
        self.contract     = contract
        self.par_contract = par_contract
        self.score        = score
        self.par_score    = par_score


# ---------------------------------------------------------------------------
# Board / session creation
# ---------------------------------------------------------------------------

def create_board(board_number):
    """Generate and return a Board for the given board number."""

    i = board_number - 1

    deal   = str(generate_deal())
    dealer = POSITIONS[i % 4]
    vul    = VULS[(i // 4 + i % 4) % 4]

    # Par calculation
    par_result    = par(Deal(deal), VUL_MAP[vul][0], POSITION_MAP[dealer][0])
    par_contract  = [str(p) for p in par_result]
    par_score     = par_result.score

    return Board(
        number       = board_number,
        deal         = deal,
        dealer       = dealer,
        vul          = vul,
        contract     = None,
        par_contract = par_contract,
        score        = None,
        par_score    = par_score,
    )


def create_session(n):
    """
    Generate a balanced session of n boards whose par scores sum to ~0.

    One board index is left open ('missing'); a pool of candidates is tested
    until the total session score is within ±50. If no candidate fits, the
    board with the largest absolute score is regenerated and the search
    continues.
    """

    indices        = list(range(1, n + 1))
    missing_idx    = random.choice(indices)
    sample_indices = [i for i in indices if i != missing_idx]

    # Step 1 – generate all boards except the missing one
    boards      = {i: create_board(i) for i in sample_indices}
    current_sum = sum(b.par_score for b in boards.values())

    # Step 2 – prepare a pool of candidates for the missing slot
    # 32 candidates cover virtually all common bridge scores
    candidates = [create_board(missing_idx) for _ in range(32)]

    while True:

        # Check whether any candidate brings the total close to zero
        best_candidate = min(candidates, key=lambda c: abs(current_sum + c.par_score))
        total_score    = current_sum + best_candidate.par_score

        if abs(total_score) <= 50:
            boards[missing_idx] = best_candidate
            final_list = [boards[i] for i in sorted(boards.keys())]
            print(f"Created {n} boards with a session score delta of {total_score}")
            return final_list

        # Step 3 – swap the board with the largest absolute score and retry
        idx_to_swap = max(sample_indices, key=lambda i: abs(boards[i].par_score))

        current_sum              -= boards[idx_to_swap].par_score
        boards[idx_to_swap]       = create_board(idx_to_swap)
        current_sum              += boards[idx_to_swap].par_score


# ---------------------------------------------------------------------------
# PBN export
# ---------------------------------------------------------------------------

def board_to_pbn(board):
    """Convert a Board object to a PBN block string."""

    SUIT_MAP  = str.maketrans('♠♥♦♣', 'SHDC')
    contracts = ';'.join(c.translate(SUIT_MAP) for c in board.par_contract)

    return (
        f'[Board "{board.number}"]\n'
        f'[Dealer "{POSITION_MAP[board.dealer][1]}"]\n'
        f'[Vulnerable "{VUL_MAP[board.vul][1]}"]\n'
        f'[Deal "{board.deal}"]\n'
        f'[OptimumScore "NS {board.par_score}"]\n'
        f'[ParContract "{contracts}"]'
    )


def write_pbn_file(session, filename):
    """Write a list of Board objects to a PBN file."""

    pbn_blocks = [board_to_pbn(board) for board in session]

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(pbn_blocks))


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def plot_session(session):
    """Diverging bar chart with cumulative score overlay."""

    scores     = [board.par_score for board in session]
    boards_idx = np.arange(1, len(scores) + 1)
    cumsum     = np.cumsum(scores)

    plt.figure(figsize=(12, 6))

    # Diverging bars
    for i, s in enumerate(scores):
        color = '#64B5F6' if s >= 0 else '#E57373'
        plt.bar(i + 1, s, color=color, edgecolor='black', linewidth=1.2, alpha=0.5)

    # Vertical guide lines
    for i in boards_idx:
        plt.axvline(i, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)

    # Zero baseline
    plt.axhline(0, color='black', linestyle='--', linewidth=2)

    # Cumulative score line
    plt.plot(boards_idx, cumsum, color='black', linewidth=0.5)
    plt.scatter(boards_idx, cumsum, color='black', s=40, zorder=5, label='Cumulative Score')

    # Labels and formatting
    plt.xticks(boards_idx, [str(i) for i in boards_idx])
    plt.xlabel("Board")
    plt.ylabel("Score (North-South)")
    plt.grid(axis='y', alpha=0.3)
    plt.legend(loc='best')
    plt.tight_layout()