"""
Bridge: Server
"""

import socket
import threading
import pickle
import time
import random
import logic.scoring
import logic.dealing
import logic.bot_bidding
import logic.bot_playing


# ──[ Parameter ]──────────────────────────────────────────────────────────────

# Card constants
CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
CARD_SUITS = ["diamonds", "clubs", "hearts", "spades"]

# Player positions
PLAYER_POSITIONS = ["north", "east", "south", "west"]

# Biddable suits
SUITS = ["clubs", "diamonds", "hearts", "spades", "notrump"]

# Logic parameters
IDLE_TIME_PLAY = 0.5
IDLE_TIME_TRICK = 1.0
IDLE_TIME_PHASE = 0.5
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
        self.trick_number = None
        
        
        
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
    
    
    
class Play:
    
    def __init__(self, player, card_suit, card_value, trick_number, trick_winner, original_turn):
        
        self.player = player
        self.card_suit = card_suit
        self.card_value = card_value
        self.trick_number = trick_number
        self.trick_winner = trick_winner
        self.original_turn =  original_turn



class GameServer:
    
    def __init__(self):
        self.game_phase = "setup"
        self.broadcast_timer = 0.0
        self.client_list = []
        self.bot_list = []
        self.current_turn = "north"
        self.original_turn = "north"
        self.current_sound = None
        self.contract_suit = None
        self.contract_level = None
        self.contract_doubled = "no"
        self.contract_team = None
        self.score = 0 # Positive: Northsouth, negative: Eastwest
        self.current_game = 0
        self.current_trick = 0
        self.vulnerability = "none" # none, both, northsouth, eastwest
        self.dummy_position = None
        self.declarer_position = None
        
        # Game session with all boards
        self.session = []
        
        # Sprite list with all the cards
        self.card_list = []
        
        # Bidding history
        self.bidding_history = []
        
        # Playing history
        self.playing_history = []
        
        # Number of human players
        self.full_table = None
        
        # Pre-moves
        self.pre_moves = {} # {player_position: action_data}
        
        # Number of player's ready for next round
        self.players_ready = {"north": 0, "east": 0, "south": 0, "west": 0}
        
        # Thread lock (to avoid race conditions)
        self.lock = threading.Lock()
        


    def start_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set ip adress
        host = "0.0.0.0"
        
        # Set port (user input)
        port_input = input("Enter port (press Enter for default 55556): ").strip()
        port = 55556 if not port_input else int(port_input)
        
        # Set total number of games (user input)
        total_games_input = input("Enter total number of deals for this session (press Enter for default 16): ").strip()
        self.total_games = 16 if not total_games_input else int(total_games_input)
        
        # Set number of human player
        full_table_input = input("Enter number of human players (press Enter for default 4): ").strip()
        self.full_table = 4 if not full_table_input else int(full_table_input)
        
        # Create boards
        self.session = logic.dealing.create_session(self.total_games)
        # logic.dealing.write_pbn_file(self.session, 'test.txt')
        
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
            name = "Bot"
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
                    
                    with self.lock:
                    
                        # Dodge position if already taken
                        player_position = self.assign_player_position(player_position)
                        
                        # Decline if table is full
                        if player_position is None:
                            continue
                        
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



    def assign_player_position(self, player_position):
        """ Assign available board position """
        
        # Find taken positions
        taken = {client.position for client in self.client_list}
        
        # Find available positions
        available = [pos for pos in PLAYER_POSITIONS if pos not in taken]

        # Assign position
        if player_position in available:
            return player_position
        elif available:
            return random.choice(available)
        else:
            return None



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
        
        # Update time since last broadcast
        self.broadcast_timer += delta_time
        
        # Send heartbeat to all clients
        if self.broadcast_timer > 2.0:
            # Reset timer
            self.broadcast_timer = 0.0
            # Set sound to silent
            original_sound = self.current_sound
            self.current_sound = None
            # Send hearbeat
            self.broadcast()
            # Reset sound
            self.current_sound = original_sound
        
        # Check if required number of players are on server
        if len(self.client_list) < self.full_table:
            return
        
        # Start game
        if self.game_phase == "setup":
            self.game_phase = "dealing"
            self.broadcast()
        
        # Check if maximum number of games is reached
        if self.current_game == self.total_games:
            if self.game_phase != "finished":
                self.game_phase = "finished"
                self.broadcast()
        
        # Start respective game logic
        
        if self.game_phase == "dealing":
            self.deal_cards()
        
        if self.game_phase == "bidding":
            self.bidding_logic()
            
        if self.game_phase == "playing":
            self.play_premove()
            self.playing_logic()
            
        if self.game_phase == "scoring":
            self.scoring_logic()
            
        if self.game_phase == "reviewing":
            self.review_logic()
            
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
            time.sleep(IDLE_TIME_PHASE)
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
            self.session[self.current_game].score = 0
            if self.current_game+1 == self.total_games:
                self.game_phase = "finished"
            else:
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
        
        # Save opener of turn
        if len(table) == 0:
            self.original_turn = self.current_turn
            
        # Check if bot should act
        is_human_player = any(client.position == self.current_turn for client in self.client_list)
        is_human_declarer = any(client.position == self.declarer_position for client in self.client_list)
        is_dummy = self.dummy_position == self.current_turn
        bot_should_act = not is_human_player and not (is_human_declarer and is_dummy)
        
        if len(table) < 4:
            
            # Let bot play if no player in that position
            if bot_should_act:
                self.opponent_play()
                self.broadcast()
        
        else:
            
            # Allocate trick
            self.allocate_trick()
            
            # Let bot take trick if no player in that position
            if bot_should_act:
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
        score = logic.scoring.chicago_score(
                    contract_level = self.contract_level,
                    contract_suit = self.contract_suit,
                    doubled = doubled,
                    declarer_vulnerable = declarer_vulnerable,
                    tricks_made = tricks_made
                )
        
        # Update scoring baord (pov: northsouth)
        self.score += score.get("total") * (1 if self.contract_team == "northsouth" else -1)
        self.session[self.current_game].score = self.score
        
        # Update session
        delta_tricks = int(tricks_made - self.contract_level - 6)
        self.session[self.current_game].contract = (
            f"{self.contract_level}"
            f"{self.get_suit_symbol(self.contract_suit)}"
            f"{self.declarer_position[0].upper()}"
            f"{doubled.lower() if doubled else ''}"
            f"{'=' if delta_tricks == 0 else delta_tricks}"
        )
        
        # Broadcast state
        self.broadcast()
    
        # Advance game
        self.game_phase = "reviewing"
            
           
            
    def review_logic(self):
        
        # Move all cards back to players' hands
        if any(card.location == "tricks" for card in self.card_list):
            
            for card in self.card_list:
                card.location = "hand"
                card.facing = "up"
            
            self.broadcast()
        
        # Check if all players are ready for next round
        if sum(self.players_ready.values()) != self.full_table:
            return
        
        # Advance game
        if self.current_game+1 == self.total_games:
            self.game_phase = "finished"
        else:
            self.game_phase = "resetting"
            
        
        
    def resetting_logic(self):
        
        # Reset game state for next game
        self.contract_level = None
        self.contract_suit = None
        self.contract_doubled = "no"
        self.contract_team = None
        self.bidding_history = []
        self.playing_history = []
        self.dummy_position = None
        self.declarer_position = None
        self.players_ready = {"north": 0, "east": 0, "south": 0, "west": 0}
        
        # Reset bids
        for player in self.client_list + self.bot_list:
            player.bid_suit = None
            player.bid_level = None
            player.bid_type = None # pass, double, normal
            
        # Reset pre-moves
        self.pre_moves = {}
              
        # Increase current game by 1
        self.current_game += 1
        
        # Set trick count to 0
        self.current_trick = 0
            
        # Rotate dealer
        self.current_turn = self.session[self.current_game].dealer
        
        # Rotate vulnerability
        self.vulnerability = self.session[self.current_game].vul
        
        # Advance game
        self.game_phase = "dealing"
        
        # Broadcast state
        self.broadcast()
                
                

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
            
        # Advance game
        if action_type == "finish_review":
            self.finish_review(player_position)
            
        # Remove player
        if action_type == "leave_game":
            self.remove_player(player_position)
            
        if action_type == "lock_bid":
            self.lock_bid(action, player_position)
            
            
            
    def play_premove(self):
        
        # Play pre-move (if available)
        action = self.pre_moves.get(self.current_turn)
        if action:
            self.current_sound = None
            self.take_trick(self.current_turn) # Attempt
            self.play_card(action, self.current_turn)
            self.pre_moves.pop(self.current_turn, None)
            self.broadcast()
            
            
            
    def play_card(self, action, player_position):
        """Move cards from table to trick stack"""
        
        # Check if it's playing phase
        if self.game_phase != "playing":
            return
        
        # Check if player can pre-move this card
        card_owner = action.get("card_owner")
        if card_owner == self.current_turn:
            can_pre_move = False
        else:
            can_pre_move = (player_position == card_owner) or \
                           (player_position == self.declarer_position and card_owner == self.dummy_position)
                                        
        # Store pre-move
        existing_pre_move = self.pre_moves.get(card_owner)
        if can_pre_move:
            if existing_pre_move == action:
                self.pre_moves.pop(card_owner, None)
            else:
                self.pre_moves[card_owner] = action
        
        # Determine actual playing side
        if (player_position == self.declarer_position and
            self.current_turn == self.dummy_position):
            acting_position = self.dummy_position
        else:
            acting_position = player_position
        
        # Only allow play if it's the correct turn
        if acting_position != self.current_turn:
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
            and card.owner == self.current_turn
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
        if card.location != "hand" or card.owner != self.current_turn:
            return
            
        # Move card to table (owner stays to track who played)
        card.location = "table"
        
        # Move card on top
        self.card_list.remove(card)
        self.card_list.append(card)
        
        # Set sound
        self.current_sound = 'play_card'
        
        print(f"Player {player_position} played {card_value} of {card_suit}")
        
        # Find current trick number
        tricks = [card for card in self.card_list if card.location == "tricks"]
        trick_number = int(len(tricks) / 4) + 1
        
        # Update playing history
        play = Play(card.owner, card.suit, card.value, trick_number, None, self.original_turn)
        self.playing_history.append(play)
        
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
        
        # Check game phase
        if self.game_phase != "playing":
            return
        
        # Check if it is player's turn (or player's dummy)
        if self.current_turn != player_position:
            if not (self.current_turn == self.dummy_position and player_position == self.declarer_position):
                return
            
        # Get cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        # Check if 4 cards on table
        if len(table) != 4:
            return
        
        # Find current trick number
        tricks = [card for card in self.card_list if card.location == "tricks"]
        trick_number = int(len(tricks) / 4) + 1
                
        # Move cards to trick stack
        for card in table:
            card.facing = "down"
            card.location = "tricks"
            card.trick_number = trick_number
            if self.current_turn in ["north", "south"]:
                card.trick = "northsouth"
            else:
                card.trick = "eastwest"
                
        # Increment trick count
        self.current_trick += 1
                
        # Mark winner
        for play in self.playing_history:
            if play.trick_number == self.current_trick:
                play.trick_winner = self.current_turn
                
        # Set sound
        self.current_sound = 'take_trick'
        
        

    def finish_review(self, player_position):
        """Mark player as ready/unready for next round"""
        
        self.players_ready[player_position] = 1 - self.players_ready.get(player_position, 0)
        
        

    def lock_bid(self, action, player_position):
        """ Move cards from table to trick stack """
        
        # Check game phase
        if self.game_phase != "bidding":
            return

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
        
        # Set sound
        self.current_sound = 'bid'
        
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
        
        # Start timer
        start = time.perf_counter()

        # Select card to play
        card_suit, card_value = logic.bot_playing.play_card(self.card_list, self.playing_history, self.contract_suit, self.current_turn, self.dummy_position)
        
        # Find card in card list
        for card in self.card_list:
            if card.suit == card_suit and card.value == card_value:
                selected_card = card
        
        # Move card from hand to table
        selected_card.location = "table"
        
        # Move card on top
        self.card_list.remove(selected_card)
        self.card_list.append(selected_card)
        
        # Set sound
        self.current_sound = 'play_card'
        
        # Find current trick number
        tricks = [card for card in self.card_list if card.location == "tricks"]
        trick_number = int(len(tricks) / 4) + 1
        
        # Update playing history
        play = Play(selected_card.owner, selected_card.suit, selected_card.value, trick_number, None, self.original_turn)
        self.playing_history.append(play)
        
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
            
        # Delay bot to make it play more natural
        end = time.perf_counter()
        elapsed = end - start
        delay = max(0, IDLE_TIME_PLAY - elapsed)
        time.sleep(delay)
        
        
        
    def opponent_bid(self):
        
        time.sleep(IDLE_TIME_PLAY)
        
        # Select client
        bot = next(bot for bot in self.bot_list 
                      if bot.position == self.current_turn)

        # Get call from call
        call = logic.bot_bidding.make_call(bot.position, self.card_list, self.bidding_history)
        
        # Set bid
        if call == "P":
            bot.bid_suit = None
            bot.bid_level = None
            bot.bid_type = "pass"
        elif call == "X":
            bot.bid_suit = None
            bot.bid_level = None
            bot.bid_type = "double"
        else:
            bot.bid_suit = [suit for suit in SUITS if suit.startswith(call[1].lower())][0]
            bot.bid_level = int(call[0])
            bot.bid_type = "normal"
            
        # Set game contract
        if call not in ("P", "X"):
            self.contract_level = bot.bid_level
            self.contract_suit = bot.bid_suit
            self.contract_team = bot.team
            self.contract_doubled = "no"
            
        # Set doubled contract
        if call == "X":
           self.contract_doubled = "yes" 
            
        # Update bidding history
        bid = Bid(bot.position, bot.bid_type, bot.bid_level, bot.bid_suit)
        self.bidding_history.append(bid)
        
        # Advance turn
        self.advance_turn()
            
        
        
    def deal_cards(self):
        """Distribute cards among players"""
        
        # Shuffle cards
        # random.shuffle(self.card_list)
        
        # Generate random deal
        # deal = logic.dealing.generate_deal(0)
        
        # Select deal from session
        deal = self.session[self.current_game].deal
        
        # Parse deal
        deal_dict = self.pbn_to_deal_dict(deal)
        
        # Allocate cards according to deal
        for i, card in enumerate(self.card_list):
            card.facing = "up"
            card.location = "hand"
            card.owner = deal_dict[(card.suit, card.value)]
            
        # Advance game
        self.game_phase = "bidding"
            
        # Send board state to clients
        self.broadcast()
        
        
        
    def pbn_to_deal_dict(self, pbn_string):
        """Converts a PBN hand string into a dictionary mapping card to position"""
         
        # N: am Anfang entfernen und Hände splitten
        hands = pbn_string.split(':', 1)[1].split()

        positions = ['north', 'east', 'south', 'west']
        suits = ['spades', 'hearts', 'diamonds', 'clubs']

        deal_dict = {}

        for pos, hand in zip(positions, hands):
            suit_parts = hand.split('.')

            for suit, cards in zip(suits, suit_parts):
                for card in cards:
                    deal_dict[(suit, card)] = pos

        return deal_dict         
    
    
    def get_suit_symbol(self, suit):
        
        # Dictionary
        dictionary = {
            "clubs": "♣",
            "diamonds": "♦", 
            "hearts": "♥",
            "spades": "♠",
            "notrump": "NT",
            None: ""
        }
        
        symbol = dictionary[suit]
        return(symbol)
     
    
    def broadcast(self):
        """Send game state to all connected clients"""
        
        for client in self.client_list:
            
            # Create a personalized game state for this player
            game_state = {
                "cards": [],
                "players": [],
                "bidding_history": [],
                "playing_history": [],
                "game_phase": self.game_phase,
                "current_turn": self.current_turn,
                "original_turn": self.original_turn,
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
                "declarer_position": self.declarer_position,
                "players_ready": self.players_ready,
                "session": self.session
            }
            
            # Add card information with appropriate visibility
            for card in self.card_list:
                card_info = {
                    "suit": card.suit,
                    "value": card.value,
                    "facing": card.facing,
                    "location": card.location,
                    "owner": card.owner,
                    "trick": card.trick,
                    "trick_number": card.trick_number
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
                
            # Add playing history
            for play in self.playing_history:
                play_info = {
                    "player": play.player,
                    "card_suit": play.card_suit,
                    "card_value": play.card_value,
                    "trick_number": play.trick_number,
                    "trick_winner": play.trick_winner,
                    "original_turn": play.original_turn
                }
                game_state["playing_history"].append(play_info)
                
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
            except Exception:
                print(f"Error sending to {client.position}")
                self.remove_player(client.position)



# ──[ Main ]───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = GameServer()
    server.start_server()


