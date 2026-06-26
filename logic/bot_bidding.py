import os
import sys

# Da diese Datei in 'logic/' liegt, ist der Hauptordner (Bridge/) genau eine Ebene darüber
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAYC_SRC = os.path.join(BASE_DIR, "third_party", "saycbridge_kbb", "src")

# Pfad live hinzufügen, falls noch nicht geschehen
if SAYC_SRC not in sys.path:
    sys.path.insert(0, SAYC_SRC)

# Add modules
from core.hand import Hand
from core.callhistory import CallHistory
from kbb import KnowledgeBasedBidder

# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["clubs", "diamonds", "hearts", "spades"]

def make_call(position, card_list, bidding_history):
    
    # Get cards of bidder
    cards = [card for card in card_list if card.owner == position]
    
    # Create CDHS-string (e.g. "Q85.A8753.T7.K53")
    cdhs_string = ".".join(
        "".join(sorted((card.value for card in cards if card.suit == s), key=CARD_VALUES.index, reverse=True))
        for s in SUITS
    )
    
    # Create hand
    hand = Hand.from_cdhs_string(cdhs_string) 
    
    # Create history string (e.g. "1C P")
    bid_strings = []
    for bid in bidding_history:
        if bid.type == "normal":
            bid_string = str(bid.level) + bid.suit[0].upper()
        elif bid.type == "pass":
            bid_string = "P"
        elif bid.type == "double":
            bid_string = "X"
        bid_strings.append(bid_string)
    history_string = " ".join(bid_strings)
       
    # Create history
    history = CallHistory.from_string(history_string)
    
    # Make call
    bidder = KnowledgeBasedBidder()
    call = bidder.find_call_for(hand, history)
    
    if call is None:
        print(f"WARNING: 'call' was None for bot hand {hand} and bidding history {history}. Defaulting to 'P' (Pass).")
        return "P"
    
    return call.name
            




