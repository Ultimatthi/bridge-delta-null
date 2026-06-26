from endplay.types import Deal
from endplay.dealer import generate_deal

CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
CARD_SUITS = ["diamonds", "clubs", "hearts", "spades"]

class Play:
    
    def __init__(self, player, card_suit, card_value, trick_number, trick_winner, original_turn):
        
        self.player = player
        self.card_suit = card_suit
        self.card_value = card_value
        self.trick_number = trick_number
        self.trick_winner = trick_winner
        self.original_turn =  original_turn

playing_history = [
    Play("south", "spades", "A", 1, None, None),
    Play("south", "spades", "Q", 1, None, None),
    Play("north", "clubs", "2", 4, None, None),
    Play("north", "clubs", "3", 5, None, None),
]


def create_predeal_from_history(playing_history):
    
    predeal = Deal()
    
    # Alle Spieler bestimmen, die Karten gespielt haben
    players = {p.player for p in playing_history}
    
    for player in players:
        # 1. Hole alle Karten dieses Spielers
        p_plays = [p for p in playing_history if p.player == player]
        
        # 2. Baue den PBN-String (Spades, Hearts, Diamonds, Clubs) in einer einzigen Zeile
        pbn = ".".join(
            "".join(sorted((p.card_value for p in p_plays if p.card_suit == s), key=CARD_VALUES.index, reverse=True))
            for s in ["spades", "hearts", "diamonds", "clubs"]
        )
        
        # 3. Dem Spieler zuweisen (funktioniert mit String oder Enum)
        setattr(predeal, str(player).split(".")[-1].lower(), pbn)
        
    return predeal


predeal = create_predeal_from_history(playing_history)


deal = generate_deal(predeal=predeal)
deal.pprint()

















