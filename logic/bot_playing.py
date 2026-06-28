# Add modules
from endplay.types import Deal, Player, Card, Rank, Denom
from endplay.dealer import generate_deal
from endplay.dds import solve_board
from collections import defaultdict

# Card constants
VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["spades", "hearts", "diamonds", "clubs"]

# Number of monte carlo runs
N = 50

def play_card(card_list, playing_history, trump_suit, player_position, dummy_position):
    
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
    
    # Init score
    scores = defaultdict(list)
    
    # Find first player
    if len(playing_history) == 0:
        first_player = player_position
    else:
        first_player = playing_history[0].player
    
    # Monte carlo simulation
    for _ in range(N):
    
        # Generate possible hand
        deal = generate_deal(predeal=predeal)
        deal.trump = Denom[trump_suit]
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







