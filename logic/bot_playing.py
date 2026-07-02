# Add modules
from endplay.types import Deal, Player, Card, Rank, Denom
from endplay.dealer import generate_deals
from endplay.dds import solve_board
from collections import defaultdict

# Card constants
VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["spades", "hearts", "diamonds", "clubs"]

# Table constants
POSITIONS = ["north", "east", "south", "west"]

# Number of monte carlo runs
N = 100




def play_card(card_list, playing_history, trump_suit, player_position, dummy_position):
    
    # Create predeal
    predeal = create_predeal(card_list, playing_history, player_position, dummy_position)
    
    # Create constraints
    constraints = create_constraints(playing_history, player_position, dummy_position)

    # Init score
    scores = defaultdict(list)
    
    # Find first player
    if len(playing_history) == 0:
        first_player = player_position
    else:
        first_player = playing_history[0].player
    
    # Generate N deals
    deals = generate_deals(*constraints, predeal=predeal, produce = N)
    
    # Monte carlo simulation
    for deal in deals:
    
        # Set attributes
        deal.trump = Denom["nt" if trump_suit == "notrump" else trump_suit]
        deal.first = Player[first_player]
        
        # Remove played cards
        for play in playing_history:
            card = play.card_suit[0].upper() + play.card_value
            deal.play(card)
            
        # Calculate score per card
        for card, tricks in solve_board(deal):
            scores[str(card)].append(tricks)
    
    # Selected card with best average score
    avg_scores = {c: sum(v)/len(v) for c, v in scores.items()}
    best_card = max(avg_scores, key=avg_scores.get)
    
    # Return card
    card_suit = {'♠': 'spades', '♥': 'hearts', '♦': 'diamonds', '♣': 'clubs'}[best_card[0]]
    card_value =  best_card[1]
    return card_suit, card_value

    

def create_predeal(card_list, playing_history, player_position, dummy_position):
    
    # Init PBN-strings (PBN-format S.H.D.C)
    pbn_strings = {}

    # Fill PBN-strings
    for player in ["north", "east", "south", "west"]:
        
            # Case 1: Dummy not yet visible (first trick)
            if player == dummy_position and len(playing_history) == 0:
                pbn_strings[player] = "..."
                
            # Case 2: Player and dummy player (visible information)
            elif player in [player_position, dummy_position]:
                pbn_strings[player] = ".".join(
                    "".join(sorted(
                        (c.value for c in card_list if c.owner == player and c.suit == s),
                        key=VALUES.index,
                        reverse=True
                    ))
                    for s in SUITS
                )
                
            # Case 3: Other players (only played cards are known)
            else:
                pbn_strings[player] = ".".join(
                    "".join(sorted(
                        (p.card_value for p in playing_history if p.player == player and p.card_suit == s),
                        key=VALUES.index,
                        reverse=True
                    ))
                    for s in SUITS
                )
        
    # Create predeal 
    predeal = Deal()
    predeal.north = pbn_strings["north"]
    predeal.east  = pbn_strings["east"]
    predeal.south = pbn_strings["south"]
    predeal.west  = pbn_strings["west"]
    
    return predeal


def create_constraints(playing_history, player_position, dummy_position):
    
    # Init directory containing suit shapes
    shapes = {p: {s: "x" for s in SUITS} for p in POSITIONS}
    
    for position in POSITIONS:
        
        if position in (player_position, dummy_position):
            continue
    
        # Find voids
        for play in playing_history:
            
            i = (play.trick_number - 1) * 4
            orig_suit = playing_history[i].card_suit
            
            if play.player != position:
                continue
            
            if play.card_suit == orig_suit:
                continue
                
            shapes[position][orig_suit] = 0
            
        # Fill with initial card in void
        for play in playing_history:
            
            if play.player != position:
                continue
                
            if shapes[position][play.card_suit] == "x":
                continue
                
            shapes[position][play.card_suit] += 1
            
    shape_strings = [
        f"shape({p}, {''.join(str(shapes[p][s]) for s in SUITS)})"
        for p in POSITIONS
    ]
    
    return shape_strings







