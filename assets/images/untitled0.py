import arcade
import math
import time

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Sanft driftende Kamera"

class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        # Kamera-Setup
        self.camera = arcade.camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Tisch-Textur (z. B. Holz oder grün)
        self.table_color = arcade.color.DARK_GREEN
        self.drift_amplitude = 10  # Wie weit die Kamera wandert
        self.drift_speed = 0.3     # Wie schnell die Drift oszilliert
        self.start_time = time.time()

    def on_draw(self):
        arcade.start_render()

        # Kamera aktivieren
        self.camera.use()

        # Tischfläche zeichnen
        arcade.draw_rectangle_filled(
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 2,
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            self.table_color
        )

        # Ein paar Deko-Elemente
        arcade.draw_text("♠  ♥  ♦  ♣", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                         arcade.color.WHITE, font_size=30, anchor_x="center", anchor_y="center")

    def on_update(self, delta_time):
        # Berechne die Drift anhand der Zeit
        elapsed = time.time() - self.start_time
        offset_x = math.sin(elapsed * self.drift_speed) * self.drift_amplitude
        offset_y = math.cos(elapsed * self.drift_speed) * self.drift_amplitude

        # Kamera leicht verschieben
        self.camera.move_to((offset_x, offset_y), speed=1.0)  # "speed" = smoothing-Effekt

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    game = GameView()
    window.show_view(game)
    arcade.run()

if __name__ == "__main__":
    main()
