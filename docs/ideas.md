##### missing features:

* main: constrained sampling
* main: import pbn files
* main: save game state (and reload)
* main: proper session finish
* gameoverview: download pbn after game
* gameoverview: actual score/bidding
* gameoverview: new background from inkscape

##### general:

* replace "\_elements" with "\_list"
* remove unused functions and variables
* use PEP8 format style

##### connection

* fix data transfer when rejoining

##### scoring:

* show scoring report

##### get available attributes of an object:

* print("Available attributes:", \[attr for attr in dir(self.object)])

##### unsolved errors:

* switching back to menu view after wrong IP address:
  # Connect to socket
  try:
  self.socket = socket.socket(socket.AF\_INET, socket.SOCK\_STREAM)
  self.socket.connect((self.host, self.port))
  except:
  print('No connection possible')
  menu\_view = MenuView()
  self.window.set\_size(LOBBY\_WIDTH, LOBBY\_HEIGHT)
  self.window.set\_caption(LOBBY\_TITLE)
  self.window.show\_view(menu\_view)
  time.sleep(0.5)
  return
