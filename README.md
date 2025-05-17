# Bridge

**HCP Harmony** is a multiplayer bridge card game project developed with Python and the Python Arcade Library. It features turn-based client synchronization over sockets, threaded communication, and custom-designed card assets. Key feature of the program is an even distribution of high card points (HCP) across a game session (but not necessarily within a single game).

## Project Structure

```
bridge/
├── assets/      # Finalized images, sounds, and media files used directly in the game
├── sources/     # Working files (e.g., Inkscape .svg files and other editable sources)
├── docs/        # Documentation, concept notes, and related materials
├── server.py    # Server-side script
└── client.py    # Client-side script
```

## Getting Started

### Prerequisites

- Python 3.x
- Python library: Arcade 3.1
- Python library: NumPy 2.2
- Python library: Pyperclip 1.9

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/bridge.git
   ```
2. Install a Python runtime environment :
   ```bash21:03 27/04/2025
   https://www.python.org/
   ```
3. Install required dependencies:
   ```bash
   pip install arcade
   pip install nump
   pip install pyperclip
   ```
4. Start the server (once):
   ```bash
   python server.py
   ```
5. Start client (one to four times):
   ```bash
   python main.py
   ```

## Contributing

Contributions, bug reports, and feature suggestions are welcome!

---

*Made with ❤️ using Python and Arcade.*

