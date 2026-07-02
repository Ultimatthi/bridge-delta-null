# Add modules
from endplay.types import Deal, Player, Card, Rank, Denom
from endplay.dealer import generate_deal
from endplay.dds import solve_board
from collections import defaultdict


# Parameters
POSITIONS = ["north", "east", "south", "west"]
SUITS = ["spades", "hearts", "diamonds", "clubs"]

# Init directory containing suit shapes
shapes = {p: {s: "x" for s in SUITS} for p in POSITIONS}

def find_voids(playing_history):
    
    for position in POSITIONS:
    
        # Find voids
        for play in playing_history:
            
            i = play.trick_number - 1
            orig_suit = playing_history[i].suit
            
            if play.player != position:
                next
            
            if play.suit == orig_suit:
                next
                
            shapes[position][orig_suit] = 0
            
        # Fill with initial card in void
        for play in playing_history:
            
            if play.player != position:
                next
                
            if shapes[position][play.suit] == "x":
                next
                
            shapes[position][play.suit] += 1
            
shape_strings = [
    f"shape({p}, {''.join(str(shapes[p][s]) for s in SUITS)})"
    for p in POSITIONS
]
              


predeal = Deal()
predeal.east  = Hand("AKQJ...")
predeal.south = Hand("T987...")
predeal.west  = Hand("65432...")



deal = generate_deal(*shape_strings, predeal=predeal)
deal.pprint()



    
    
    