"""
Bridge: Client
"""

import arcade
from arcade.future.light import Light, LightLayer
import socket
import threading
import pickle
import time
import numpy as np
import random
import arcade.gui
import pyperclip

# ──[ Parameters ]─────────────────────────────────────────────────────────────

# Set consistent random seed
# random.seed(42)

# Window dimensions
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
SCREEN_TITLE = 'Bridge: Card Game'

# Scaling parameters
SCALE = min(SCREEN_HEIGHT/1080, SCREEN_WIDTH/1920)
CARD_SCALE = 1.0 * SCALE
TILE_SCALE = 1.0 * SCALE

# Layout dimensions
MARGIN_OUTER = 30 * SCALE
MARGIN_INNER = 60 * SCALE
TABLE_X = SCREEN_WIDTH / 2
TABLE_Y = SCREEN_HEIGHT / 2

# Game constants
PLAYER_POSITIONS = ["north", "east", "south", "west"]
BID_TYPES = ["pass", "double", "normal"]
CARD_WIDTH = 140 * CARD_SCALE
CARD_HEIGHT = 190 * CARD_SCALE
CARD_VALUES = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
CARD_SUITS = ["diamonds", "clubs", "hearts", "spades"]
SUITS = ["clubs", "diamonds", "hearts", "spades", "notrump"]
CARD_ENLARGE = 1.1
HCP = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}

# Bidding constants
TILE_LEVELS = [1, 2, 3, 4, 5, 6, 7]
TILE_SUITS = ["clubs", "diamonds", "hearts", "spades", "notrump"]

# Light configuration
LIGHT_RADIUS = SCREEN_WIDTH * 0.9

# Lobby dimensions
LOBBY_WIDTH = 1280
LOBBY_HEIGHT = 720
LOBBY_TITLE = "Bridge: Lobby"

# Lobby scaling paramters
LOBBY_SCALE = min(LOBBY_HEIGHT/1080, LOBBY_WIDTH/1920)

# ──[ Classes ]────────────────────────────────────────────────────────────────

class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, suit, value, facing, owner, location, trick, scale=1):
        """ Card constructor """

        # Attributes
        self.suit = suit
        self.value = value
        self.facing = facing # up, down, wrapped
        self.owner = owner
        self.location = location # deck, table, hand, dummy, tricks
        self.trick = trick
        self.hcp = HCP.get(value, 0)

        # Image to use for the sprite when face up
        self.image = f":resources:images/cards/card{self.suit}{self.value}.png"
        
        # Call the parent
        super().__init__(self.image, scale, hit_box_algorithm="None")
        
    def face_down(self):
        """ Turn card face-down """
        self.texture = arcade.load_texture(":resources:images/cards/cardBack_red2.png")
        
    def face_down_wrapped(self):
        """ Wraps card in band """
        self.texture = arcade.load_texture(r'assets/images/cardBack_wrapped.png')
        
    def face_up(self):
        """ Turn card face-up """
        self.texture = arcade.load_texture(self.image)



class Tile(arcade.Sprite):
    """ Bid sprite """
    
    def __init__(self, suit, level, bid_type, scale):
        
        # Attributes
        self.level = level
        self.suit = suit
        self.type = bid_type
        
        # Image
        if bid_type == "normal":
            self.image = r"assets/images/tile.selection.png"
        else:
            self.image = r"assets/images/tile.selection.2.png"
        
        # Call the parent
        super().__init__(self.image, scale, hit_box_algorithm="None")
     
        
        
class Bid:
    
    def __init__(self, player, bid_type, level, suit):
        
        self.player = player
        self.type = bid_type
        self.level = level
        self.suit = suit
        
        
        
class BoardElement(arcade.Sprite):
    """ Sector sprite """

    def __init__(self, image_path, scale):
        """ Board element constructor """
        
        # Image to use for the sprite
        self.image_file_name = image_path

        # Call the parent
        super().__init__(self.image_file_name, scale, hit_box_algorithm = 'None')
        
        

class Player():
    """ Player class """
    
    def __init__(self, name, position):
        """ Player constructor """
        
        # Attributes
        self.name = name
        self.position = position
        self.team = self.allocate_team(position)
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



# ──[ Game View ]─────────────────────────────────────────────────────────────

class Game(arcade.View):
    """ Main application class. """

    def __init__(self, username='anonymous', server='localhost', position=None):
        super().__init__()
        
        # Transfer parameters
        self.player_name = username
        host_str, port_str = server.split(":")
        self.host = host_str
        self.port = int(port_str)
        self.player_position = position if position is not None else "north"

        # Play mat colour
        self.background_color = arcade.color.ARSENIC
        
        # Sound effects
        self.sound_slide = arcade.load_sound(r'assets/effects/slide.mp3')
        self.sound_cash = arcade.load_sound(r'assets/effects/cash.mp3')
        self.sound_drop = arcade.load_sound(r'assets/effects/drop.mp3')
        self.sound_lock = arcade.load_sound(r'assets/effects/lock.mp3')
        
        # Fonts
        arcade.load_font("assets/fonts/CourierNewBold.ttf")
        
    def setup(self):
        """ Set up the game here. Call this function to restart the game. """
        
        # Set game phase
        self.game_phase = "bidding"
        
        # Visibility of last trick
        self.last_trick_visible = False
        
        # Set bidding history
        self.bidding_history = []
        
        # Mouse position
        self.mouse_x = 0
        self.mouse_y = 0
        
        # Set modifier
        self.ctrl_held = False
        
        # Allocate team
        self.team = self.allocate_team(self.player_position)
        
        # Bid
        self.bid_suit = None
        self.bid_level = None
        self.bid_type = None
        
        # List with all the players
        self.player_list = []
        
        # Sprite list with all the cards, no matter what pile they are in
        self.card_list = arcade.SpriteList()
        
        # Sprite list with all the tile elements
        self.tile_list = arcade.SpriteList()
        
        # Board element list with all the board elements
        self.board_elements = arcade.SpriteList()
        
        # Board element list with all the bidding elements
        self.bidding_elements = arcade.SpriteList()
        
        # Board element list with all the texture elements
        self.texture_elements = arcade.SpriteList()
        
        # Layer to handle light sources
        self.light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Set background of light layer
        self.light_layer.set_background_color(self.background_color)
        
        # Init game state
        self.current_turn = None
        self.original_turn = None
        self.current_sound = None
        self.contract_suit = None
        self.contract_level = None
        self.contract_doubled = "no"
        self.contract_team = None
        self.score = 0
        self.current_game = None
        self.total_games = None
        self.vulnerability = "none"
        self.dummy_position = None
        self.declarer_position = None
        
        # Hovered card
        self.hover_card = None
        
        # Hovered tile
        self.hover_tile = None
        
        # Thread
        self.running = True

        # Create every card
        for card_suit in CARD_SUITS:
            for card_value in CARD_VALUES:
                card = Card(card_suit, card_value, "up", None, None, CARD_SCALE)
                card.position = SCREEN_WIDTH/2, SCREEN_HEIGHT/2
                card.angle = random.uniform(-5, 5)
                self.card_list.append(card)
                
        # Create every normal tile
        for i, tile_suit in enumerate(TILE_SUITS):
            for j, tile_level in enumerate(TILE_LEVELS):
                tile = Tile(tile_suit, tile_level, "normal", TILE_SCALE)
                tile.center_x = SCREEN_WIDTH / 2 - 150*SCALE + i * 75*SCALE
                tile.center_y = SCREEN_HEIGHT / 2 - 85*SCALE + j * 50*SCALE
                self.tile_list.append(tile)
                
        # Create pass tile
        tile = Tile(None, None, "pass", TILE_SCALE)
        tile.center_x = SCREEN_WIDTH / 2 - 112.5*SCALE
        tile.center_y = SCREEN_HEIGHT / 2 - 135*SCALE
        self.tile_list.append(tile)  
        
        # Create double tile
        tile = Tile(None, None, "double", TILE_SCALE)
        tile.center_x = SCREEN_WIDTH / 2 + 112.5*SCALE
        tile.center_y = SCREEN_HEIGHT / 2 - 135*SCALE
        self.tile_list.append(tile)  
        
        # Create every player
        for position in PLAYER_POSITIONS:
            name = str(position) + "(Bot)"
            player = Player(name, position)
            self.player_list.append(player)
            
        # Create board elements: Border 
        image_path = r'assets/images/board.border.png'
        self.board_border = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2
        y = SCREEN_HEIGHT/2
        self.board_border.position = x, y
              
        # Create board elements: Scoring area
        image_path = r'assets/images/board.scoring.png'
        self.board_scoring = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH - MARGIN_INNER - self.board_scoring.width/2
        y = SCREEN_HEIGHT - MARGIN_INNER - self.board_scoring.height/2
        self.board_scoring.position = x, y
        
        # Create board elements: Contract area
        image_path = r'assets/images/board.contract.png'
        self.board_contract = BoardElement(image_path, SCALE)
        x = MARGIN_INNER + self.board_contract.width/2
        y = SCREEN_HEIGHT - MARGIN_INNER - self.board_contract.height/2
        self.board_contract.position = x, y
        
        # Create board elements: Trick area (won)
        image_path = r'assets/images/board.tricks.won.png'
        self.board_tricks_won = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH - MARGIN_INNER - self.board_tricks_won.width/2
        y = MARGIN_INNER + self.board_tricks_won.height/2
        self.board_tricks_won.position = x, y

        # Create board elements: Trick area (lost)
        image_path = r'assets/images/board.tricks.lost.png'
        self.board_tricks_lost = BoardElement(image_path, SCALE)
        x = MARGIN_INNER + self.board_tricks_lost.width/2
        y = MARGIN_INNER + self.board_tricks_lost.height/2
        self.board_tricks_lost.position = x, y
          
        # Add to board element list
        self.board_elements.append(self.board_border)
        self.board_elements.append(self.board_scoring)
        self.board_elements.append(self.board_contract)
        self.board_elements.append(self.board_tricks_won)
        self.board_elements.append(self.board_tricks_lost)
        
        # Create texture element: Texture
        image_path =  r'assets/images/board.texture.png'
        self.board_texture = BoardElement(image_path, SCALE)
        self.board_texture.position = SCREEN_WIDTH/2, SCREEN_HEIGHT/2
        self.texture_elements.append(self.board_texture)
        
        # Create bidding elements: Grid
        image_path = r'assets/images/bidding.grid.png'
        self.bidding_grid = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2
        y = SCREEN_HEIGHT/2 + 40*SCALE
        self.bidding_grid.position = x, y
        
        # Create bidding elements: Strips
        image_path = r'assets/images/bidding.strip.png'
        self.bidding_strip_bottom = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2
        y = SCREEN_HEIGHT/2 - 260*SCALE
        self.bidding_strip_bottom.position = x, y
        
        # Create bidding elements: Strips
        image_path = r'assets/images/bidding.strip.png'
        self.bidding_strip_top = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2
        y = SCREEN_HEIGHT/2 + 330*SCALE
        self.bidding_strip_top.position = x, y
        
        # Create bidding elements: Strips
        image_path = r'assets/images/bidding.strip.png'
        self.bidding_strip_left = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2 - 530*SCALE
        y = SCREEN_HEIGHT/2
        self.bidding_strip_left.position = x, y
        
        # Create bidding elements: Strips
        image_path = r'assets/images/bidding.strip.png'
        self.bidding_strip_right = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2 + 530*SCALE
        y = SCREEN_HEIGHT/2
        self.bidding_strip_right.position = x, y
        
        # Create bidding elements: HCP pad
        image_path = r'assets/images/hcp.overlay.png'
        self.hcp_overlay = BoardElement(image_path, SCALE)
        x = SCREEN_WIDTH/2
        y = 30*SCALE
        self.hcp_overlay.position = x, y
        
        # Add to bidding element list
        self.bidding_elements.append(self.bidding_grid)
        self.bidding_elements.append(self.hcp_overlay)
        self.bidding_elements.append(self.bidding_strip_bottom)
        self.bidding_elements.append(self.bidding_strip_top)
        self.bidding_elements.append(self.bidding_strip_left)
        self.bidding_elements.append(self.bidding_strip_right)

        # Create main light source
        self.center_light = Light(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                             radius=LIGHT_RADIUS,
                             color=arcade.color.BEIGE,
                             mode='soft')
        
        # Add light sources to light layer
        self.light_layer.add(self.center_light)
        
        # Connect to socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        
        # Send player data to server
        data = {
            "player_position": self.player_position,
            "player_name": self.player_name
        }
        self.socket.sendall(pickle.dumps(data))
        
        # Start thread to receive messages
        self.recv_thread = threading.Thread(target=self.receive_state, daemon=True)
        self.recv_thread.start()

        
        
    def on_update(self, delta_time):
        """Update sprites. """
        
        # Shrink previous enlarged card
        for card in self.card_list:
            if card != self.hover_card and card.scale != CARD_SCALE:
                card.scale = CARD_SCALE
            elif card.location != "hand" and card.scale != CARD_SCALE:
                card.scale = CARD_SCALE
        
        # Enlarge card we are hovering above
        if (self.hover_card != None):
            if self.hover_card.location == "hand":
                self.hover_card.scale = CARD_SCALE*CARD_ENLARGE
                
        # Adjust card facing
        for card in self.card_list:
            if card.facing == "down":
                card.face_down()
            elif card.facing == "wrapped":
                card.face_down_wrapped()
            else:
                card.face_up()
                
        # Reset highlighted tile
        for tile in self.tile_list:
            if tile != self.hover_tile:
                tile.color = [255, 255, 255, 0]
                
        # Highlight tile we are hovering above
        if (self.hover_tile != None):
            self.hover_tile.color = [255, 255, 255, 80]
            
        # Get ordinal of current contract
        contract_ordinal = self.get_bid_ordinal(self.contract_level, self.contract_suit)
        
        # Grey out tile that are no longer biddable
        for tile in self.tile_list:
            bid_ordinal = self.get_bid_ordinal(tile.level, tile.suit)
            if bid_ordinal <= contract_ordinal and tile.type == "normal":
                tile.color = arcade.color.ARSENIC
        
                
        
    def on_draw(self):
        """ Render the screen. """
        
        # Clear the screen
        self.clear()
        
        with self.light_layer:
            
            # Draw board elements
            self.board_elements.draw()
            
            # Color cards
            self.color_cards()
            
            # Draw the cards
            self.card_list.draw()
            
            # Draw bidding elements
            if self.game_phase == "bidding":
                
                # Draw bidding elements
                self.bidding_elements.draw()
                
                # Draw bidding tiles
                self.tile_list.draw()
                
                # Annotations
                self.annotate_bidding()
            
            # Annotations
            self.annotate()
            
            # Texture overlay
            self.texture_elements.draw()
            
        self.light_layer.draw()
        


    def review_trick(self, held_card):
        
        # Get cards on trick pile
        tricks = [card for card in self.card_list if card.location == "tricks"]
        
        # Check if any tricks
        if len(tricks) == 0:
            return
        
        # Check if clicked on last trick
        if held_card != tricks[-1]:
            return
        
        # Get last trick
        last_trick = tricks[-4:]
        
        # Sort display order
        position_priority = {"left": 0, "top": 1, "right": 2, "bottom": 3}
        sorted_last_trick = sorted(
            last_trick,
            key=lambda c: position_priority[self.get_display_position(self.player_position, c.owner)]
        )
        
        # Play sound
        self.play_sound("review_trick")

        if self.last_trick_visible == False:
            
            # Turn cards face up and move them radially
            for card in sorted_last_trick:
                
                # Get relative position of card owner
                rel_position = self.get_display_position(self.player_position, card.owner)
                
                # Offset
                offset_x = 50 * SCALE
                offset_y = 50 * SCALE
                
                # Set new position for radial spread
                if rel_position == "bottom":
                    card.center_y -= offset_y
                    card.angle = 5
                elif rel_position == "left":
                    card.center_x -= offset_x
                    card.angle = -10
                elif rel_position == "top":
                    card.center_y += offset_y
                    card.angle = -5
                elif rel_position == "right":
                    card.center_x += offset_x
                    card.angle = 10
                            
                # Pull to top
                self.pull_to_top(card)
    
                # Turn card face up
                card.facing = "up"
                
            self.last_trick_visible = True
                
        else:
            
            # Turn cards face down and return to original positions
            self.adjust_card_position()
                
            self.last_trick_visible = False
            
            
        
    def pull_to_top(self, card: arcade.Sprite):
        """ Pull card to top of rendering order (last to render, looks on-top) """

        # Remove, and append to the end
        self.card_list.remove(card)
        self.card_list.append(card)

    def on_mouse_press(self, x, y, button, key_modifiers):
        """ Called when the user presses a mouse button. """

        # Get list of cards we've clicked on
        cards = arcade.get_sprites_at_point((x, y), self.card_list)

        # Have we clicked on a card?
        if len(cards) > 0:

            # Might be a stack of cards, get the top one
            held_card = cards[-1]
            
            # Play card
            if held_card.location == "hand":
                self.play_card(held_card)
            
            # Take trick
            if held_card.location == "table":
                self.take_trick()
                
            if held_card.location == "tricks":
                self.review_trick(held_card)
                
        # Get list of tiles we've clicked on
        tiles = arcade.get_sprites_at_point((x, y), self.tile_list)
        
        # Have we clicked on a card?
        if len(tiles) > 0:
            
            # Might be a stack of cards, get the top one
            held_tile = tiles[-1]
            
            self.make_bid(held_tile)

            
                
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """ Called when the user scrolls the mouse wheel. """
                
        pass



    def make_bid(self, held_tile):
        """ Check if bid is valid """
        
        # Check game phase
        if self.game_phase != "bidding":
            return
        
        # Check if it's this player's turn
        if self.player_position != self.current_turn:
            return
        
        # Check if doubling is allowed
        if ((self.contract_doubled == "yes" or 
             self.contract_team == self.team or 
             len(self.bidding_history) < 1) and 
            held_tile.type == "double"):
            return
                
        # Get ordinal (strictly increasing) number of bid and current highest bid (contract)
        bid_ordinal = self.get_bid_ordinal(held_tile.level, held_tile.suit)
        contract_ordinal = self.get_bid_ordinal(self.contract_level, self.contract_suit)
        
        # Check if bid is higher than current contract
        if bid_ordinal < contract_ordinal and held_tile.type == "normal":
            return
        
        # Set bid
        self.bid_level = held_tile.level
        self.bid_suit = held_tile.suit
        self.bid_type = held_tile.type
            
        # Lock bid
        self.lock_bid()
            

    def lock_bid(self):
        
        # Create action for server
        action = {
            "type": "lock_bid",
            "bid_level": self.bid_level,
            "bid_suit": self.bid_suit,
            "bid_type": self.bid_type
        }
        
        # Send action to server
        try:
            self.socket.sendall(pickle.dumps(action))
        except Exception as e:
            print(f"Error sending to server: {e}")
        
        # Play sound
        self.play_sound("lock")
        
        
    def get_bid_ordinal(self, bid_level, bid_suit):
        """ Calculate stricly increasing value of a bid """
        
        if bid_level is None:
            ordinal = -1
        else:
            ordinal = SUITS.index(bid_suit) + (bid_level-1)*5
       
        return(ordinal)
        
        
        
        
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """ User moves mouse """
        
        # Update mouse position
        self.mouse_x = x
        self.mouse_y = y
        
        # Get cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        # Get cards on trick pile
        tricks = [card for card in self.card_list if card.location == "tricks"]
        
        # Get list of cards we'are hovering above
        cards = arcade.get_sprites_at_point((x, y), self.card_list)
        
        # Declare top card as hovered card
        if len(cards) > 0:
            self.hover_card = cards[-1]
        else:
            self.hover_card = None
            
        # Get list of tiles we'are hovering above
        tiles = arcade.get_sprites_at_point((x, y), self.tile_list)
        
        # Declare top tile as hovered tile
        if len(tiles) > 0:
            self.hover_tile = tiles[-1]
        else:
            self.hover_tile = None
        
        # Set cursor type to default
        cursor_type = self.window.CURSOR_DEFAULT
                
        # Set cursor type to "hand" if hovering card above hand card
        if len(cards) > 0:
            if cards[-1].location == "hand" and cards[-1].owner == self.player_position:
                cursor_type = self.window.CURSOR_HAND
                
        # Check if it is player's turn (or player's dummy) to take a trick
        player_turn = True
        if self.current_turn != self.player_position:
            if not (
                self.current_turn == self.dummy_position 
                and self.player_position == self.declarer_position
            ):
                player_turn = False
                
        # Set cursor type to "hand" if hovering card above trick ready to take
        if len(cards) > 0 and player_turn:
            if len(table) == 4 and cards[-1].location == "table":
                cursor_type = self.window.CURSOR_HAND
                
        # Set cursor type to "hand" if hovering over a card of the last trick taken
        if len(cards) > 0 and len(tricks) > 0:
            if cards[-1] == tricks[-1]:
                cursor_type = self.window.CURSOR_HAND
                
        # Set cursor
        self.window.set_mouse_cursor(self.window.get_system_mouse_cursor(cursor_type))
                
        
    def on_key_press(self, key, _modifiers):
        """ Handle keypresses. """
        
        # Set modifier
        if key == arcade.key.LCTRL:
            self.ctrl_held = True
            
        # Leave game
        if key == arcade.key.ESCAPE:
            
            # Set running to False to stop thread
            self.running = False
            
            # Send action to server
            action = {"type": "leave_game"}
            
            # Disconnect
            try:
                self.socket.sendall(pickle.dumps(action))
            except Exception:
                pass
            finally:
                self.socket.shutdown(socket.SHUT_RDWR)
                
            # Switch to Lobby
            menu_view = MenuView()
            self.window.set_size(LOBBY_WIDTH, LOBBY_HEIGHT)
            self.window.set_caption(LOBBY_TITLE)
            self.window.show_view(menu_view)
            
            
    def on_key_release(self, key, _modifiers):
        """ Handle keypresses. """
        
        # Set modifier
        if key == arcade.key.LCTRL:
            self.ctrl_held = False
            
            
    def play_card(self, card):
        """Send play card action to server"""

        # Create action for server
        action = {
            "type": "play_card",
            "card_suit": card.suit,
            "card_value": card.value
        }
        
        # Send action to server
        try:
            self.socket.sendall(pickle.dumps(action))
        except Exception as e:
            print(f"Error sending to server: {e}")
            
            
            
    def take_trick(self):
        """Send take trick action to server"""
            
        # Create action for server
        action = {"type": "take_trick"}
        
        # Send action to server
        try:
            self.socket.sendall(pickle.dumps(action))
        except Exception as e:
            print(f"Fehler beim Serialisieren der Aktion: {e}")
            
            

    def order_hand(self):
        """Order cards in hand by suit and value"""
        
        self.card_list.sort(key=lambda card: (CARD_SUITS.index(card.suit), CARD_VALUES.index(card.value)))


    def receive_state(self):
        """Receive game state from server"""
        
        while self.running:
            try:
                data = self.socket.recv(4096)
                self.update_state(data)
            except:
                print("Connection lost")
                time.sleep(0.1)
                continue
                
            
    def update_state(self, data):
        """Update game state from server data"""
        
        # Load game state
        game_state = pickle.loads(data)
        
        # Update game state variables
        self.game_phase = game_state.get("game_phase")
        self.current_turn = game_state.get("current_turn")
        self.original_turn = game_state.get("original_turn")
        self.contract_suit = game_state.get("contract_suit")
        self.contract_level = game_state.get("contract_level")
        self.contract_doubled = game_state.get("contract_doubled")
        self.contract_team = game_state.get("contract_team")
        self.score = game_state.get("score")
        self.current_game = game_state.get("current_game")
        self.total_games = game_state.get("total_games")
        self.vulnerability = game_state.get("vulnerability")
        self.dummy_position = game_state.get("dummy_position")
        self.declarer_position = game_state.get("declarer_position")
        
        # Play sound
        sound = game_state.get("sound")
        self.play_sound(sound)
        
        # Get player/bot  info
        player_list = game_state.get("players")
        
        # Setup map for fast access
        player_map = {player.position: player for player in self.player_list}
        
        # Update player variables with clients
        for server_player in player_list:
            # Get player
            position = server_player["position"]
            player = player_map[position]
            # Fill in attributes
            player.name = server_player["name"]
            player.team = server_player["team"]
            player.bid_suit = server_player["bid_suit"]
            player.bid_level = server_player["bid_level"]
            player.bid_type = server_player["bid_type"]
            
        # Get logical card variables
        logical_card_list = game_state.get("cards")
        
        # Setup map for fast access
        card_map = {(card.suit, card.value): card for card in self.card_list}
        
        # Update card variables
        for logical_card in logical_card_list:
            key = (logical_card["suit"], logical_card["value"])
            if key in card_map:
                card = card_map[key]
                card.facing = logical_card["facing"]
                card.owner = logical_card["owner"]
                card.location = logical_card["location"]
                card.trick = logical_card["trick"]

        # Update card position
        self.adjust_card_position()
        
        # Reorder cards after new draw
        hand_count = sum(1 for card in self.card_list if card.location == "hand")
        if hand_count == 52:
            self.order_hand()
            
        # Clear bidding history
        self.bidding_history.clear()
        
        # Refill bidding history
        for bid_info in game_state["bidding_history"]:
            bid = Bid(
                player=bid_info["player"],
                bid_type=bid_info["type"],
                level=bid_info["level"],
                suit=bid_info["suit"]
            )
            self.bidding_history.append(bid)
            
            

    def play_sound(self, sound):
        
        if sound == 'play_card':
            arcade.play_sound(self.sound_slide)
        elif sound == 'take_trick':
            arcade.play_sound(self.sound_cash)
        elif sound == 'review_trick':
            arcade.play_sound(self.sound_cash)
        elif sound == 'bid':
            arcade.play_sound(self.sound_drop)
        elif sound == 'lock':
            arcade.play_sound(self.sound_lock)
            
            
        
    def adjust_card_position(self):
        """Position the card based on location"""
        
        # Order cards and delete bidding after every game
        if self.game_phase == "resetting":
            self.sort_cards()
            self.bid_level = None
            self.bid_suit = None
            self.bid_type = None
            
        # Order cards in different locations
        self.arrange_player_cards()
        self.arrange_table_cards()
        self.arrange_stack_cards()
        self.arrange_dummy_cards()
        
    def arrange_player_cards(self):
        """Order cards in player's hand"""

        for position in ("south", "north", "west", "east"):
            # Get cards of that hand
            hand = [
                card for card in self.card_list 
                if card.owner == position and card.location == "hand"
            ]
            
            # Check if there are any cards in the hand
            n = len(hand)
            if n == 0:
                continue
            
            # Get relative board position of that player (relative to this player)
            rel_position = self.get_display_position(self.player_position, position)
    
            # Offset
            max_cards = 13
            offset = (max_cards - n) / 2
    
            for i, card in enumerate(hand):
                
                # Index as if card would be in full hand
                virtual_i = i + offset
                t = (virtual_i - (max_cards - 1) / 2)
    
                # Find position and angle
                if rel_position == "bottom":
                    x = SCREEN_WIDTH / 2 + t * 60 * SCALE
                    y = CARD_HEIGHT / 2 - abs(t) ** 2 * 2.25 * SCALE
                    angle = t / max_cards * 60  
                elif rel_position == "top":
                    x = SCREEN_WIDTH/2 + t * 40 * SCALE
                    y = SCREEN_HEIGHT - CARD_HEIGHT/8 + abs(t) ** 2 * 3 * SCALE
                    angle = -t / max_cards * 80
                elif rel_position == "left":
                    x = CARD_HEIGHT/8 - abs(t) ** 2 * 3 * SCALE
                    y = SCREEN_HEIGHT/2 + t * 40 * SCALE
                    angle = (-t / max_cards * 80) - 90
                elif rel_position == "right":
                    x = SCREEN_WIDTH - CARD_HEIGHT/8 + abs(t) ** 2 * 3 * SCALE
                    y = SCREEN_HEIGHT/2 + t * 40 * SCALE
                    angle = (t / max_cards * 80) + 90
    
                # Set position and angle
                card.position = (x, y)
                card.angle = angle
                
                # Set facing and size
                if self.player_position != card.owner:
                    card.facing = "down"
                else:
                    card.facing = "up"
            
    def arrange_table_cards(self):
        """Order cards on table"""
        
        # Get cards on table
        table = [card for card in self.card_list if card.location == "table"]
        
        # Order cards on table [horizontally]
        for card in table:
            # Get relative board position of that owner (relative to this player)
            rel_owner = self.get_display_position(self.player_position, card.owner)
            if rel_owner == 'bottom':
                card.position = TABLE_X, TABLE_Y - CARD_HEIGHT*0.6
                card.angle = 7
            elif rel_owner == 'left':
                card.position = TABLE_X - CARD_WIDTH*0.6, TABLE_Y
                card.angle = -30
            elif rel_owner == 'top':
                card.position = TABLE_X, TABLE_Y + CARD_HEIGHT*0.6
                card.angle = -5
            else:
                card.position = TABLE_X + CARD_WIDTH*0.6, TABLE_Y
                card.angle = 40
            # Calculate dummy offset
            dummy_position = self.get_display_position(self.player_position, self.dummy_position)
            if dummy_position == "bottom":
                card.center_y += CARD_HEIGHT/4
            elif dummy_position == "top":
                card.center_y -= CARD_HEIGHT/4
            else:
                pass
                
        # Order cards on table [vertically]
        current_index = PLAYER_POSITIONS.index(self.original_turn)  # <== statt self.current_turn
        # Sort by player position (clockwise from original turn)
        sorted_positions = PLAYER_POSITIONS[current_index:] + PLAYER_POSITIONS[:current_index]
        # Build sort order dict
        sort_order = {pos: i for i, pos in enumerate(sorted_positions)}
        # Sort cards on table accordingly
        table.sort(key=lambda card: sort_order.get(card.owner, 999))
        # Update drawing order
        for card in table:
            self.card_list.remove(card)
            self.card_list.append(card)
            
    def arrange_stack_cards(self):
        """Order cards in trick stacks"""
        
        # Order cards on stack
        stack_team = [
            card for card in self.card_list 
            if card.location == "tricks" 
            and card.trick == self.team
        ]
        stack_opponent = [
            card for card in self.card_list 
            if card.location == "tricks" 
            and card.trick != self.team
        ]
        sets = [(stack_team, self.board_tricks_won), (stack_opponent, self.board_tricks_lost)]
        for stack, board in sets:
            for i, card in enumerate(stack):
                card.angle = 0
                card.facing = "down"
                batch = int(np.floor(i/4))
                if len(stack) <= 20:
                    x = board.left + CARD_HEIGHT/2 + batch*26*SCALE
                else:
                    if i < 24:
                        x = board.left + CARD_HEIGHT/2
                        card.facing = "wrapped"
                    else:
                        x = board.left + CARD_HEIGHT/2 + batch*26*SCALE
                y = board.bottom + CARD_WIDTH/2 + 50*SCALE
                card.position = x, y
            
    def arrange_dummy_cards(self):
        """Order cards in dummy"""
        
        # Get cards in dummy's hand
        dummy_cards = [
            card for card in self.card_list 
            if card.owner == self.dummy_position
            and card.location == "hand"
        ]
        
        # Get cards in hand
        hand_cards = [card for card in self.card_list if card.location == "hand"]
        
        # Check if game phase is playing
        if self.game_phase != "playing":
            return
        
        # Check if first card is already played
        if len(hand_cards) == 52:
            return

        # Position cards by suit
        for suit_index, suit in enumerate(CARD_SUITS):
            # Get a stack of card for each suit
            suit_cards = [card for card in dummy_cards if card.suit == suit]
            # Iterate through each stack
            for card_index, card in enumerate(suit_cards):
                # Calculate horizontal and vertical position based on suit
                dummy_position = self.get_display_position(self.player_position, self.dummy_position)
                if dummy_position == "left":
                    x = MARGIN_INNER + (2*suit_index+1)/2*CARD_WIDTH + suit_index*10*SCALE
                    y = SCREEN_HEIGHT/3*2 - CARD_HEIGHT/2 - card_index*CARD_HEIGHT/5
                elif dummy_position == "right":
                    x = SCREEN_WIDTH - MARGIN_INNER - (2*(3-suit_index)+1)/2*CARD_WIDTH - (3-suit_index)*10*SCALE
                    y = SCREEN_HEIGHT/3*2 - CARD_HEIGHT/2 - card_index*CARD_HEIGHT/5
                elif dummy_position == "top":
                    x = SCREEN_WIDTH/2 + ((2*suit_index+1)/2 - 2)*CARD_WIDTH + (suit_index*10 - 15)*SCALE
                    y = SCREEN_HEIGHT - MARGIN_INNER - CARD_HEIGHT/2 - card_index*CARD_HEIGHT/5
                else:
                    x = SCREEN_WIDTH/2 + ((2*suit_index+1)/2 - 2)*CARD_WIDTH + (suit_index*10 - 15)*SCALE
                    y = MARGIN_INNER + CARD_HEIGHT/2 + card_index*CARD_HEIGHT/5
                card.position = x, y
                card.angle = 0
                card.facing = "up"
                
                
                
    def color_cards(self):
        """Color all cards that are trump"""
        
        for card in self.card_list:
            if card.suit == self.contract_suit and card.facing == "up":
                card.color = arcade.color.ANTIQUE_WHITE
            else:
                card.color = arcade.color.WHITE
                
                
            
    def annotate(self):
        
        # HCP overlay
        if self.game_phase == "bidding":
            hcp_count = sum(card.hcp for card in self.card_list if card.owner == self.player_position)
            label = str(hcp_count) + " HCP"
            x = self.hcp_overlay.center_x
            y = self.hcp_overlay.center_y
            text = self.annotate_text(label, x, y, 0, 18)
            text.draw()
            
        # Number of cards in hands
        hand_cards = sum(1 for card in self.card_list if card.location == "hand")
        
        # Player names
        for player in self.player_list:
            
            # Check if this is the dummy player
            is_dummy = player.position == self.dummy_position and hand_cards < 52
            
            # Get relative board position
            rel_position = self.get_display_position(self.player_position, player.position)
            
            # Define annotation position
            if rel_position == 'bottom':
                x = SCREEN_WIDTH / 2
                y = MARGIN_OUTER if is_dummy else CARD_HEIGHT / 8 * 9
                a = 0
            elif rel_position == 'left':
                x = MARGIN_OUTER if is_dummy else CARD_HEIGHT / 4 * 3
                y = SCREEN_HEIGHT / 2
                a = -90
            elif rel_position == 'top':
                x = SCREEN_WIDTH / 2
                y = SCREEN_HEIGHT - MARGIN_OUTER if is_dummy else SCREEN_HEIGHT - CARD_HEIGHT / 4 * 3
                a = 0
            else:  # 'right'
                x = SCREEN_WIDTH - MARGIN_OUTER if is_dummy else SCREEN_WIDTH - CARD_HEIGHT / 4 * 3
                y = SCREEN_HEIGHT / 2
                a = 90
                
            # Define label
            if player.position == self.current_turn:
                label = "▸"  + player.name.upper() + "◂"
            else:
                label = player.name.upper()
            
            # Write player name
            text = arcade.Text(
                label,
                x=x, y=y,
                color=arcade.color.WHITE,
                font_size=22.5*SCALE, font_name="Courier New",
                anchor_x="center", anchor_y="center",
                align="center", rotation=a
            )
            text.draw()
            
        # Contract: Team
        x = self.board_contract.right - 55*SCALE
        y = self.board_contract.bottom + 175*SCALE
        text = self.annotate_state_text(self.contract_team, 17, x, y, 0, 22*SCALE)  # self.contract_team
        text.draw()
        
        # Contract: Bid
        x = self.board_contract.right - 55*SCALE
        y = self.board_contract.bottom + 120*SCALE
        symbol = self.get_suit_symbol(self.contract_suit)
        value = f"{self.contract_level} of [{symbol}]"
        text = self.annotate_state_text(value, 18, x, y, 0, 22*SCALE) # self.contract_level/bid
        text.draw()
        
        # Contract: Bid
        x = self.board_contract.right - 55*SCALE
        y = self.board_contract.bottom + 65*SCALE
        text = self.annotate_state_text(self.contract_doubled, 15, x, y, 0, 22*SCALE)
        text.draw()
        
        # Scoring: Points
        x = self.board_scoring.right - 55*SCALE
        y = self.board_scoring.bottom + 175*SCALE
        value = self.score
        text = self.annotate_state_text(value, 15, x, y, 0, 22*SCALE)
        text.draw()
        
        # Scoring: Games
        x = self.board_scoring.right - 55*SCALE
        y = self.board_scoring.bottom + 120*SCALE
        value = f"{self.current_game}/{self.total_games}"
        text = self.annotate_state_text(value, 16, x, y, 0, 22*SCALE)
        text.draw()
        
        # Scoring: Vulnerability
        x = self.board_scoring.right - 55*SCALE
        y = self.board_scoring.bottom + 65*SCALE
        value = self.vulnerability
        text = self.annotate_state_text(value, 17, x, y, 0, 22*SCALE)
        text.draw()
        
        
        
    def annotate_bidding(self):
            
        # Bidding text
        for player in self.player_list:
            
            # Init 3 diffently colored texts that are stacked to one single text later
            label_white = ""
            label_red = ""
            label_beige = ""
            
            # Create text for each player
            for bid in self.bidding_history:
                if bid.player == player.position:
                    symbol = self.convert_bid_to_symbol(bid)
                    
                    # Add delimiter
                    if label_white + label_red + label_beige != "":
                        label_white += "·"
                        label_red += " "
                        label_beige += " "
            
                    # Add symbol
                    if bid.suit in ["clubs", "spades"] or bid.type == "pass":
                        label_white += symbol
                        label_red += " " * len(symbol)
                        label_beige += " " * len(symbol)
                    elif bid.suit in ["diamonds", "hearts"] or bid.type == "double":
                        label_white += " " * len(symbol)
                        label_red += symbol
                        label_beige += " " * len(symbol)
                    else:
                        label_white += " " * len(symbol)
                        label_red += " " * len(symbol)
                        label_beige += symbol
                    
            # Get relative board position
            rel_position = self.get_display_position(self.player_position, player.position)
            # Set bidding location
            if rel_position == "bottom":
                x = self.bidding_strip_bottom.center_x
                y = self.bidding_strip_bottom.center_y
            elif rel_position == "top":
                x = self.bidding_strip_top.center_x
                y = self.bidding_strip_top.center_y
            elif rel_position == "left":
                x = self.bidding_strip_left.center_x
                y = self.bidding_strip_left.center_y
            elif rel_position == "right":
                x = self.bidding_strip_right.center_x
                y = self.bidding_strip_right.center_y
            # Draw bidding text
            text_white = self.annotate_text(label_white, x, y, 0, 30, [255, 255, 255])
            text_red = self.annotate_text(label_red, x, y, 0, 30, [173, 54, 50])
            text_beige = self.annotate_text(label_beige, x, y, 0, 30, [255, 204, 170])
            text_white.draw()
            text_red.draw()
            text_beige.draw()


            
    def convert_bid_to_symbol(self, bid):
        
        # Transform bid to string
        if bid.type is None:
            symbol = ""
        elif bid.type == "pass":
            symbol = "P"
        elif bid.type == "double":
            symbol = "X"
        else:
            suit_symbol = self.get_suit_symbol(bid.suit)
            symbol = f"{bid.level}{suit_symbol}"
        
        # Return
        return(symbol)
    
    
    
    def annotate_state_text(self, value, width, x, y, angle, size):
        
        # Set to "" if None
        value = "TBD" if value is None else value
        
        # Transfrom to int (if a number)
        try:
            value = int(value)
        except (ValueError, TypeError):
            pass
        
        # Transform to string
        value = str(value)
        
        # Add dots
        label = '.' * (width - len(value) - 1) + " " + value
        
        # Text object
        text = arcade.Text(
            label.upper(),
            x=x, y=y,
            color=arcade.color.WHITE,
            font_size=size, font_name="Courier New",
            anchor_x="right", anchor_y="center",
            align="right", rotation=angle
        )
        
        # Return
        return(text)
    
    
      
    def annotate_text(self, label, x, y, angle, size, color=arcade.color.WHITE):
        
        # Set to "" if None
        label = "" if label is None else label
        
        # Transfrom to int (if a number)
        try:
            label = int(label)
        except (ValueError, TypeError):
            pass
        
        # Transform to string
        label = str(label)
        
        # Text object
        text = arcade.Text(
            label.upper(),
            x=x, y=y,
            color=color,
            font_size=size*SCALE, font_name="Courier New",
            anchor_x="center", anchor_y="center",
            align="center", rotation=angle
        )
        
        # Return
        return(text)
            
            
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
        
        
        
    def get_display_position(self, bottom_position, position):
        """Finds board position for display purposes"""
    
        player_positions = ["north", "east", "south", "west"]
        display_positions = ["bottom", "left", "top", "right"]
    
        bottom_index = player_positions.index(bottom_position)
        position_index = player_positions.index(position)
        distance = (position_index - bottom_index) % 4
    
        return display_positions[distance]
    
    
    
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
    
    
    def sort_cards(self):
        """ Sort card list in the original order """

        self.card_list.sort(key=self.card_sort_key)
        
    def card_sort_key(self, card):
        
        suit_index = CARD_SUITS.index(card.suit)
        value_index = CARD_VALUES.index(card.value)
        return (suit_index, value_index)
        


# ──[ Lobby Class ]────────────────────────────────────────────────────────────

class MenuView(arcade.View):
    """Menu/lobby view class."""

    def __init__(self):
        super().__init__()
        self.toggle_list = []
        self.input_list = []
        
        # Load assets
        self.load_assets()
        
        # Set up UI elements
        self.setup_ui_styles()
        self.create_ui_elements()
        self.position_ui_elements()
        self.setup_event_handlers()

    def load_assets(self):
        """Load all required assets."""
        # Background image
        self.background = arcade.load_texture("assets/images/lobby.background.png")
        
        # Load sound effects
        self.sound_drop = arcade.load_sound("assets/effects/drop.mp3")
        
        # Load font
        arcade.load_font("assets/fonts/CourierNewBold.ttf")
        
        # Load button textures
        self.textures = {
            "north_off": arcade.load_texture("assets/images/button.north.off.png"),
            "north_on": arcade.load_texture("assets/images/button.north.on.png"),
            "east_off": arcade.load_texture("assets/images/button.east.off.png"),
            "east_on": arcade.load_texture("assets/images/button.east.on.png"),
            "south_off": arcade.load_texture("assets/images/button.south.off.png"),
            "south_on": arcade.load_texture("assets/images/button.south.on.png"),
            "west_off": arcade.load_texture("assets/images/button.west.off.png"),
            "west_on": arcade.load_texture("assets/images/button.west.on.png"),
            "random_off": arcade.load_texture("assets/images/button.random.off.png"),
            "random_on": arcade.load_texture("assets/images/button.random.on.png"),
            "join_off": arcade.load_texture("assets/images/button.join.off.png"),
            "join_on": arcade.load_texture("assets/images/button.join.on.png")
        }

    def setup_ui_styles(self):
        """Set up UI widget styles."""
        # Input text widget style - transparent background with no border
        self.input_style = arcade.gui.widgets.text.UIInputTextStyle(
            bg=(0, 0, 0, 0),
            border=None,
            border_width=0
        )
        
        # Flat button style
        self.button_style = arcade.gui.widgets.buttons.UIFlatButtonStyle(
            font_size=15,
            font_name="Courier New",
            font_color=arcade.color.WHITE,
            bg=(9, 25, 34, 255),
            border=None,
            border_width=0
        )

    def create_ui_elements(self):
        """Create all UI elements."""
        self.manager = arcade.gui.UIManager()
        
        # Create text input fields: 1
        self.username_widget = arcade.gui.UIInputText(
            text="Icarus",
            height=35 * LOBBY_SCALE, 
            width=(370 - 2 * 12) * LOBBY_SCALE,
            font_name="Courier New",
            font_size=15,
            border_width=0,
            style={state: self.input_style for state in ["normal", "hover", "focus", "press", "disabled", "invalid"]}
        )
        self.input_list.append(self.username_widget)
        
        # Create text input fields: 2
        self.server_widget = arcade.gui.UIInputText(
            text="localhost:55556",
            height=35 * LOBBY_SCALE, 
            width=(370 - 2 * 12) * LOBBY_SCALE,
            font_name="Courier New",
            font_size=15,
            border_width=0,
            style={state: self.input_style for state in ["normal", "hover", "focus", "press", "disabled", "invalid"]}
        )
        self.input_list.append(self.server_widget)
        
        # Create launch button
        self.launch_widget = arcade.gui.UITextureButton(
            height=102 * LOBBY_SCALE,
            width=412 * LOBBY_SCALE,
            texture=self.textures["join_off"],
            texture_hovered=self.textures["join_on"]
        )
        
        # Create position toggle buttons
        self.create_position_toggles()

    def create_position_toggles(self):
        """Create the position toggle buttons."""
        # Position name mapping for each toggle
        position_names = ["north", "east", "south", "west", "random"]
        self.toggle_positions = {}

        # Create all position toggles in a loop
        for position in position_names:
            toggle = arcade.gui.UITextureToggle(
                height=60 * LOBBY_SCALE, 
                width=60 * LOBBY_SCALE,
                on_texture=self.textures[f"{position}_on"],
                off_texture=self.textures[f"{position}_off"],
                value=False
            )
            self.toggle_list.append(toggle)
            self.toggle_positions[position] = toggle
            
            # Store references to specific toggles for positioning later
            setattr(self, f"{position}_widget", toggle)
            
        # Set "random" toggle to default
        self.toggle_list[4].value = True

    def position_ui_elements(self):
        """Position all UI elements on the screen."""
        # Create main anchor layout
        self.anchor = self.manager.add(arcade.gui.UIAnchorLayout())
        
        # Position username input
        self.anchor.add(
            child=self.username_widget,
            anchor_x="left", align_x=(280 + 12) * LOBBY_SCALE,
            anchor_y="bottom", align_y=(795 + 12) * LOBBY_SCALE
        )
        
        # Position server input
        self.anchor.add(
            child=self.server_widget,
            anchor_x="left", align_x=(280 + 12) * LOBBY_SCALE,
            anchor_y="bottom", align_y=(635 + 12) * LOBBY_SCALE
        )
        
        # Position launch button
        self.anchor.add(
            child=self.launch_widget,
            anchor_x="left", align_x=258 * LOBBY_SCALE,
            anchor_y="bottom", align_y=177 * LOBBY_SCALE
        )
        
        # Position toggle buttons
        self.position_toggle_buttons()

    def position_toggle_buttons(self):
        """Position the toggle buttons."""
        positions = [
            (self.north_widget, 280),
            (self.east_widget, 357.5),
            (self.south_widget, 435),
            (self.west_widget, 512.5),
            (self.random_widget, 590)
        ]
        
        for widget, x_pos in positions:
            self.anchor.add(
                child=widget,
                anchor_x="left", align_x=x_pos * LOBBY_SCALE,
                anchor_y="bottom", align_y=465 * LOBBY_SCALE
            )

    def setup_event_handlers(self):
        """Set up all event handlers for UI elements."""
        # Launch button event
        @self.launch_widget.event("on_click")
        def on_click_start_new_game_button(event):
            arcade.play_sound(self.sound_drop)
            
            # Get the selected position
            selected_position = None
            for position, toggle in self.toggle_positions.items():
                if toggle.value:
                    selected_position = position
                    break
                
            # Randomly pick a position if toggle says so
            if selected_position == "random":
                selected_position = random.choice(PLAYER_POSITIONS)
            
            # Create main view with the user inputs
            main_view = Game(
                username=self.username_widget.text,
                server=self.server_widget.text,
                position=selected_position
            )
            main_view.setup()
            
            # Open main view
            self.window.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)
            self.window.set_caption("Bridge: Client")
            self.window.show_view(main_view)
        
        # Toggle button events - only one can be selected at a time
        for toggle in self.toggle_list:
            @toggle.event("on_click")
            def handle_toggle(event, toggle=toggle):  # Default-arg-trick for closure
                for other in self.toggle_list:
                    if other != toggle:
                        other.value = False
                
                arcade.play_sound(self.sound_drop)
               
        # Text input events - only one can be selected at a time
        for widget in self.input_list:
            @widget.event("on_click")
            def handle_input(event, widget=widget):
                for other in self.input_list:
                    if other != widget:
                        other.deactivate()

    def on_show_view(self):
        """Called when this view becomes active."""
        self.manager.enable()

    def on_hide_view(self):
        """Called when this view is deactivated."""
        self.manager.disable()

    def on_draw(self):
        """Render the screen."""
        self.clear()
        
        # Draw background
        rect = arcade.LBWH(left=0, bottom=0, width=self.window.width, height=self.window.height)
        arcade.draw_texture_rect(texture=self.background,rect=rect)
        
        # Draw UI elements
        self.manager.draw()

    def on_key_press(self, key, modifiers):
        """Handle key presses, especially for clipboard operations."""
        # Handle Ctrl+V (paste)
        if key == arcade.key.V and modifiers & arcade.key.MOD_CTRL:
            
            # Get copied text
            clipboard_text = pyperclip.paste()
            
            # Add text in active widget
            for widget in self.input_list:
                if widget.active:
                    cursor_pos = widget.caret.position
                    current_text = widget.text
                    new_text = current_text[:cursor_pos] + clipboard_text + current_text[cursor_pos:]
                    widget.text = new_text
                    widget.caret.position = cursor_pos + len(clipboard_text)
                    
        # Handle Ctrl+A (select all)
        elif key == arcade.key.A and modifiers & arcade.key.MOD_CTRL:
            
            # Select text in active widget
            for widget in self.input_list:
                if widget.active:
                    widget.caret.mark = 0
                    widget.caret.position = len(widget.text)
                     
            

# ──[ Main ]───────────────────────────────────────────────────────────────────

def main():
    """ Main function """
    window = arcade.Window(LOBBY_WIDTH, LOBBY_HEIGHT, LOBBY_TITLE, resizable=False)
    menu_view = MenuView()  # Start with menu view
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()