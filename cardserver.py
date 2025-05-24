"""
Bridge: Server
"""

import socket
import threading
import pickle
import time
import random
import logic.scoring as sc
import logic.rotation as rot



# ──[ Parameter ]──────────────────────────────────────────────────────────────

# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
CARD_SUITS = ["diamonds", "clubs", "hearts", "spades"]

# Notwenidge Spielerzahl
FULL_TABLE = 2

# Player positions
PLAYER_POSITIONS = ["north", "east", "south", "west"]

# Biddable suits
SUITS = ["clubs", "diamonds", "hearts", "spades", "notrump"]

# Logic parameters
IDLE_TIME_PLAY = 0.5
IDLE_TIME_TRICK = 1.0
FPS = 20



# ──[ Classes ]────────────────────────────────────────────────────────────────

class ServerCard:
    """ Simplified card for server logics """
    
    def __init__(self, suit, value):
        
        self.suit = suit
        self.value = value
        self.ordinal = CARD_VALUES.index(value)
        self.facing = "up"
        self.location = "deck"  # deck, table, hand, dummy, tricks
        self.owner = None
        self.trick = None
        
        
        
class Client:
    
    def __init__(self, socket, name, position):
        
        # Identity
        self.socket = socket
        self.name = name
        self.position = position
        
        # Team
        self.team = self.allocate_team(self.position)

        # Bidding
        self.bid_suit = None
        self.bid_level = None
        self.bid_type = None # pass, double, normal
    
    def allocate_team(self, position):
        """Allocate team based on player's position"""
        
        team_by_player = {
            "north": "northsouth",
            "south": "northsouth",
            "east": "eastwest",
            "west": "eastwest"
        }
        team = team_by_player[position]
        return(team)
    
    
    
class Bid:
    
    def __init__(self, player, bid_type, level=None, suit=None):
        
        self.player = player
        self.type = bid_type  # "normal", "pass", "double"
        self.level = level
        self.suit = suit
        
        # Team
        self.team = self.allocate_team(self.player)
        
    def allocate_team(self, position):
        """Allocate team based on player's position"""
        
        team_by_player = {
            "north": "northsouth",
            "south": "northsouth",
            "east": "eastwest",
            "west": "eastwest"
        }
        team = team_by_player[position]
        return(team)



class GameServer:
    
    def __init__(self):
        self.game_phase = "dealing"
        self.client_list = []
        self.bot_list = []
        self.current_turn = "north"
        self.current_sound = None
        self.contract_suit = None
        self.contract_level = None
        self.contract_doubled = "no"
        self.contract_team = None
        self.score = 0 # Positive: Northsouth, negative: Eastwest
        self.current_game = 0
        self.total_games = 16
        self.vulnerability = "none" # none, both, northsouth, eastwest
        self.dummy_position = None
        self.declarer_position = None
        
        # Sprite list with all the cards
        self.card_list = []
        
        # Bidding history
        self.bidding_history = []
        


    def start_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = "0.0.0.0"
        port = 55556
        s.bind((host, port))
        s.listen(5)
        s.settimeout(5.0)
        
        print(f'Server runs on {host}:{port}')
        
        # Create every card
        for card_suit in CARD_SUITS:
            for card_value in CARD_VALUES:
                card = ServerCard(card_suit, card_value)
                self.card_list.append(card)
                
        # Create every player
        for position in PLAYER_POSITIONS:
            name = str(position) + "(Bot)"
            bot = Client(None, name, position)
            self.bot_list.append(bot)
        
        # Start update loop in seperate thread
        threading.Thread(target=self.update_loop, daemon=True).start()

        try:
            while True:
                try:
                    c, addr = s.accept()
                    data = c.recv(1024)
                    player_data = pickle.loads(data)
                    player_position = player_data.get("player_position")
                    player_name = player_data.get("player_name")
                    print(f"Connection accepted from {addr} with username {player_name}")
                    
                    # Add to client list
                    client = Client(c, player_name, player_position)
                    self.client_list.append(client)
                    
                    # Remove from bot list
                    for bot in self.bot_list:
                        if bot.position == client.position:
                            self.bot_list.remove(bot)
                    
                    # Set sound to none
                    self.current_sound = None
                    
                    # Send board state
                    self.broadcast()
                    
                    # Starte a new thread for each client
                    client_thread = threading.Thread(target=self.handle_client, args=(c, player_position, player_name), daemon=True)
                    client_thread.start()
                except:
                    pass
        except KeyboardInterrupt:
            print('Server stopping...')
        finally:
            s.close()
            print('Server closed')



    def update_loop(self):
        
        # Init reference time
        last_time = time.time()
        
        while True:
            
            # Calcualte delta time
            now = time.time()
            delta_time = now - last_time
            last_time = now
    
            # Call update function
            self.on_update(delta_time)
    
            # 60 FPS-Update-Loop
            time.sleep(1/FPS)  
            
            
            
    def on_update(self, delta_time):
        
        # Check if required number of players are on server
        if len(self.client_list) < FULL_TABLE:
            return
        
        # Start respective game logic
        
        if self.game_phase == "dealing":
            self.deal_cards()
        
        if self.game_phase == "bidding":
            self.bidding_logic()
            
        if self.game_phase == "playing":
            self.playing_logic()
            
        if self.game_phase == "scoring":
            self.scoring_logic()
            
        if self.game_phase == "resetting":
            self.resetting_logic()
            
            
            
    def bidding_logic(self):
        
        # Check if bidding phase ended
        bidding_ended = (
            len(self.bidding_history) >= 4
            and all(bid.type == "pass" for bid in self.bidding_history[-3:])
            and self.contract_level is not None
        )
        
        # End bidding phase
        if bidding_ended:
            # Find original bid of contract suit
            declarer_bid = next(
                bid for bid in self.bidding_history
                if bid.suit == self.contract_suit 
                and bid.team == self.contract_team
            )
            # Get player of that bid
            declarer = next(
                player for player in self.client_list + self.bot_list
                if player.position == declarer_bid.player
            )
            # Set dummy and declarer position
            self.declarer_position = declarer.position
            self.dummy_position = PLAYER_POSITIONS[(PLAYER_POSITIONS.index(declarer.position)+2) % 4]
            # Set game info
            self.game_phase = "playing"
            self.current_turn = PLAYER_POSITIONS[(PLAYER_POSITIONS.index(declarer.position)+1) % 4]
            self.broadcast()
            return

        # Check no bid round
        no_bid_round = (
            len(self.bidding_history) >= 4 
            and all(bid.type == "pass" for bid in self.bidding_history[-4:])
        )
        
        # # Iterate new game round
        if no_bid_round:
            self.game_phase = "resetting"
            return
        
        # Let computer bid if no player in that position
        is_human_player = any(client.position == self.current_turn for client in self.client_list)
        if not is_human_player:
            self.opponent_bid()
            self.broadcast()

        
        
    def playing_logic(self):
        
        # Count cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        if len(table) < 4:
                    
            # Let computer play if no player in that position
            is_human_player = any(client.position == self.current_turn for client in self.client_list)
            if not is_human_player:
                self.opponent_play()
                self.broadcast()
        
        else:
            
            # Allocate trick
            self.allocate_trick()
            
            # Let computer take trick if no player in that position
            is_human_player = any(client.position == self.current_turn for client in self.client_list)
            if not is_human_player:
                self.take_trick(self.current_turn)
                time.sleep(IDLE_TIME_TRICK)
                self.broadcast()
                
        # Count cards on trick pile
        tricks = [card for card in self.card_list if card.location == "tricks"]
        
        # Advance game 
        if len(tricks) == 52:
            self.game_phase = "scoring"



    def scoring_logic(self):
        
        # Count tricks of contract team
        tricks_made = sum(1 for card in self.card_list if card.trick == self.contract_team)/4
        
        print(tricks_made)
        
        # Was declearer vulnerable?
        if self.vulnerability in ["both", self.contract_team]:
            declarer_vulnerable = True
        else:
            declarer_vulnerable = False
            
        # Is contract doubled?
        if self.contract_doubled == "yes":
            doubled = "X"
        else:
            doubled = ""
        
        # Calculate score
        score = sc.chicago_score(
                    contract_level = self.contract_level,
                    contract_suit = self.contract_suit,
                    doubled = doubled,
                    declarer_vulnerable = declarer_vulnerable,
                    tricks_made = tricks_made
                )
        
        # Update scoring baord
        self.score += score.get("total") * (1 if self.contract_team == "northsouth" else -1)
        
        # Broadcast state
        self.broadcast()
        time.sleep(1.0)
    
        # Advance game
        self.game_phase = "resetting"
        
        
        
    def resetting_logic(self):
        
        # Reset game state for next game
        self.contract_level = None
        self.contract_suit = None
        self.contract_doubled = "no"
        self.contract_team = None
        self.bidding_history = []
        self.dummy_position = None
        self.declarer_position = None
        
        # Reset bids
        for player in self.client_list + self.bot_list:
            player.bid_suit = None
            player.bid_level = None
            player.bid_type = None # pass, double, normal
            
        # Broadcast state
        self.broadcast()
            
        # Advance game
        self.game_phase = "dealing"
        
        # Rotate dealer and vulnerability
        self.current_turn, self.vulnerability = rot.chicago_rotate(self.current_game+1)
                
                

    def handle_client(self, c, player_position, player_name):

        while True:
            
            try:
                # Receive data
                data = c.recv(4096)
                
                if data:
                    
                    # Reset sound
                    self.current_sound = None
                    
                    # Process client action
                    action = pickle.loads(data)
                    self.process_action(action, player_position)
                
                    # Sende updated game state to all clients
                    self.broadcast()
                    
            except:
                pass



    def process_action(self, action, player_position):
        
        # Get action type
        action_type = action.get("type")
        
        # Play card action
        if action_type == "play_card":
            self.play_card(action, player_position)
            
        # Take trick
        if action_type == "take_trick":
            self.take_trick(player_position)
            
        # Remove player
        if action_type == "leave_game":
            self.remove_player(player_position)
            
        if action_type == "lock_bid":
            self.lock_bid(action, player_position)



    def play_card(self, action, player_position):
        """Move cards from table to trick stack"""
        
        # Check if it's bidding phase
        if self.game_phase != "playing":
            return
        
        # Check if it's this player's turn
        if player_position != self.current_turn:
            return
        
        # Get cards on table
        table = [
            card for card in self.card_list 
            if card.location == "table"
        ]
        
        # Get cards in player's hand
        hand = [
            card for card in self.card_list 
            if card.location == "hand"
            and card.owner == player_position
        ]
        
        # Check if last trick was taken
        if len(table) == 4:
            return
        
        # Find suit and value of played card
        card_suit = action.get("card_suit")
        card_value = action.get("card_value")
        
        # Check if player can follow suit
        if len(table) == 0:
            follows_suit = False
        else:
            follows_suit = any(card.suit == table[0].suit for card in hand)
        
        # Check if player follows suit
        if len(table) > 0:
            if follows_suit:
                if card_suit not in table[0].suit:
                    return
        
        # Find the card in the server's deck
        card = self.find_card(card_suit, card_value)
        
        # Check if card is in hand
        if card.location != "hand" or card.owner != player_position:
            return
            
        # Move card to table (owner stays to track who played)
        card.location = "table"
        
        # Move card on top
        self.card_list.remove(card)
        self.card_list.append(card)
        
        # Set sound
        self.current_sound = 'play_card'
        
        print(f"Player {player_position} played {card_value} of {card_suit}")
        
        # Get cards on table
        table = [
            card for card in self.card_list 
            if card.location == "table"
        ]
        
        # Advance turn
        if len(table) < 4:
            self.advance_turn()
        else:
            self.allocate_trick()
            
    def take_trick(self, player_position):
        """Move cards from table to trick stack"""
        
        # Check if it is player's turn (or player's dummy)
        if self.current_turn != player_position:
            if not (self.current_turn == self.dummy_position and player_position == self.declarer_position):
                return
                
        # Get cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        # Check if 4 cards on table
        if len(table) != 4:
            return
                
        # Move cards to trick stack
        for card in table:
            card.facing = "down"
            card.location = "tricks"
            if self.current_turn in ["north", "south"]:
                card.trick = "northsouth"
            else:
                card.trick = "eastwest"
                
        # Set sound
        self.current_sound = 'take_trick'
        
        

    def lock_bid(self, action, player_position):
        """ Move cards from table to trick stack """
        
        # Check if it's this player's turn
        if player_position != self.current_turn:
            return
        
        # Transform action back to bid
        bid_level = action.get("bid_level")
        bid_suit = action.get("bid_suit")
        bid_type = action.get("bid_type")
        
        # Check validity of bid
        bid_ordinal = self.get_bid_ordinal(bid_level, bid_suit)
        contract_ordinal = self.get_bid_ordinal(self.contract_level, self.contract_suit)
        if bid_ordinal <= contract_ordinal:
            if bid_type not in ["pass", "double"]:
                return
            
        # Check if doubling is allowed
        if bid_type == "double":
            # No doubling before any normal bid
            if self.contract_level is None:
                return
            # No doubling of already doubled bid
            elif self.contract_doubled == "yes":
                return
            # No doubling of partner's bid
            elif (
                len(self.bidding_history) >= 2 
                and self.bidding_history[-1].type == "pass" 
                and self.bidding_history[-2].type == "normal"
            ):
                return
        
        # Find client
        client = next(client for client in self.client_list if client.position == self.current_turn)
        
        # Set bid of that client
        client.bid_level = action.get("bid_level")
        client.bid_suit = action.get("bid_suit")
        client.bid_type = action.get("bid_type")
        
        print(f"Player {player_position} bid")
        
        # Set contract
        if bid_type == "normal":
            self.contract_level = client.bid_level
            self.contract_suit = client.bid_suit
            self.contract_team = client.team
            # Reset double
            self.contract_doubled = "no"
            
        # Doubling contract
        if bid_type == "double":
            self.contract_doubled = "yes"
            
        # Update bidding history
        bid = Bid(client.position, bid_type, bid_level, bid_suit)
        self.bidding_history.append(bid)
        
        # Advance turn
        self.advance_turn()
        
        
        
    def get_bid_ordinal(self, bid_level, bid_suit):
        """ Calculate stricly increasing value of a bid """
        
        if bid_level is None:
            ordinal = -1
        else:
            ordinal = SUITS.index(bid_suit) + (bid_level-1)*5
       
        return(ordinal)



    def allocate_trick(self):
        
        # Get cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        # Check if 4 cards on table
        if len(table) != 4:
            return
        
        # Find highests card on table
        highcard = table[0]
        for card in table:
            if card.suit == highcard.suit and card.ordinal >= highcard.ordinal:
                highcard = card
            elif card.suit == self.contract_suit and highcard.suit != self.contract_suit:
                highcard = card
                
        # Set next lead
        self.current_turn = highcard.owner


    def remove_player(self, player_position):
        """Removes client from game"""
    
        # Find socket
        for client in self.client_list:
            if client.position == player_position:
                self.remove_client(client.socket, client.position)


    
    def remove_client(self, client_socket, player_position):
        """Removes client from game"""
        
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        finally:
            client_socket.close()
        
        
        client = next((client for client in self.client_list if client.position == player_position), None)
        self.client_list.remove(client)
        print(f"Client {player_position} was removed from the game")



    def find_card(self, suit, value):
        """Find a card in the deck by suit and value"""
        
        for card in self.card_list:
            if card.suit == suit and card.value == value:
                return card
        return None
    


    def advance_turn(self):
        """Move to next player in turn order"""
    
        # Set current_turn to next player
        index_0 = PLAYER_POSITIONS.index(self.current_turn)
        index_1 = (index_0 + 1) % 4
        self.current_turn = PLAYER_POSITIONS[index_1]

        

    def opponent_play(self):
        """Play card for non-player opponent"""
        
        time.sleep(IDLE_TIME_PLAY)
        
        # Init selected card
        selected_card = None
        
        # Get cards on table
        table = [
            card for card in self.card_list 
            if card.location == "table"
        ]
            
        # Select opponent's card
        hand = [
            card for card in self.card_list 
            if card.location == "hand"
            and card.owner == self.current_turn
        ]
        
        # Select card by following suit
        if len(table) > 0:
            for card in hand:
                if card.suit == table[0].suit:
                    selected_card = card
                    break
        
        # If no card of the required suit was found, use the first card in hand
        if selected_card is None and hand:
            selected_card = hand[0]
        
        # Move card from hand to table
        selected_card.location = "table"
        
        # Move card on top
        self.card_list.remove(selected_card)
        self.card_list.append(selected_card)
        
        # Set sound
        self.current_sound = 'play_card'
        
        # Get cards on table
        table = [
            card for card in self.card_list 
            if card.location == "table"
        ]
        
        # Advance turn
        if len(table) < 4:
            self.advance_turn()
        else:
            self.allocate_trick()
        
        
        
    def opponent_bid(self):
        
        time.sleep(IDLE_TIME_PLAY)
        
        # Select client
        bot = next(bot for bot in self.bot_list 
                      if bot.position == self.current_turn)
        
        # Randomly choose if bot passes or bids
        choice = random.choice(["pass", "bid"])

        # Bot bids
        if choice == "bid":
            if self.contract_level is None:
                bot.bid_suit = "clubs"
                bot.bid_level = 1
                bot.bid_type = "normal"
            elif self.contract_level < 4:
                index = (SUITS.index(self.contract_suit) + 1) % 5
                bot.bid_level = self.contract_level + (index==0)
                bot.bid_suit = SUITS[index]
                bot.bid_type = "normal"
            else:
                choice = "pass"
            
        # Bot passes
        if choice == "pass":
            bot.bid_suit = None
            bot.bid_level = None
            bot.bid_type = "pass"
            
        # Set game contract
        if choice == "bid":
            self.contract_level = bot.bid_level
            self.contract_suit = bot.bid_suit
            self.contract_team = bot.team
            self.contract_doubled = "no"
            
        # Update bidding history
        bid = Bid(bot.position, bot.bid_type, bot.bid_level, bot.bid_suit)
        self.bidding_history.append(bid)
        
        # Advance turn
        self.advance_turn()
            
            
            
    def deal_cards(self):
        """Distribute cards among players"""
        
        # Shuffle cards
        random.shuffle(self.card_list)
        
        # Allocate cards evenly -- 13 cards per player
        for i, card in enumerate(self.card_list):
            card.facing = "up"
            card.location = "hand"
            card.owner = PLAYER_POSITIONS[i // 13]
            
        # Increate current game by 1
        self.current_game += 1
        
        # Advance game
        self.game_phase = "bidding"
            
        # Send board state to clients
        self.broadcast()
        


    def broadcast(self):
        """Send game state to all connected clients"""
        
        for client in self.client_list:
            
            # Create a personalized game state for this player
            game_state = {
                "cards": [],
                "players": [],
                "bidding_history": [],
                "game_phase": self.game_phase,
                "current_turn": self.current_turn,
                "sound": self.current_sound,
                "contract_suit": self.contract_suit,
                "contract_level": self.contract_level,
                "contract_doubled": self.contract_doubled,
                "contract_team": self.contract_team,
                "score": self.score,
                "current_game": self.current_game,
                "total_games": self.total_games,
                "vulnerability": self.vulnerability,
                "dummy_position": self.dummy_position,
                "declarer_position": self.declarer_position
            }
            
            # Add card information with appropriate visibility
            for card in self.card_list:
                card_info = {
                    "suit": card.suit,
                    "value": card.value,
                    "facing": card.facing,
                    "location": card.location,
                    "owner": card.owner,
                    "trick": card.trick
                }
                game_state["cards"].append(card_info)
                
            # Add bidding history
            for bid in self.bidding_history:
                bid_info = {
                    "player": bid.player,
                    "type": bid.type,
                    "level": bid.level,
                    "suit": bid.suit,
                    "team": bid.team
                }
                game_state["bidding_history"].append(bid_info)
                
            # Add player info
            for player in self.client_list + self.bot_list:
                player_info = {
                    "name": player.name,
                    "position": player.position,
                    "team": player.team,
                    "bid_suit": player.bid_suit,
                    "bid_level": player.bid_level,
                    "bid_type": player.bid_type
                }
                game_state["players"].append(player_info)
            
            # Send game state to client
            try:
                size = pickle.dumps(game_state)
                print(f"Sending game state ({len(size)} bytes)")
                client.socket.sendall(pickle.dumps(game_state))
            except Exception as e:
                print(f"Error sending to {client.position}: {e}")



# ──[ Main ]───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = GameServer()
    server.start_server()


