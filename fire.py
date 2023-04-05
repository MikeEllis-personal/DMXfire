import array
import rp2

from time     import sleep
from random   import seed, randint
from machine  import Pin
from neopixel import ws2812
class led_panel:
    def __init__(self, pin, leds, statemachine=0):
        # Create the StateMachine with the ws2812 program
        self._sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(pin))
        self._sm.active(1)

        # Initialise the LED array to all off
        self._strip = array.array("I", [0 for _ in range(leds)]) # GRB colour order
        self._sm.put(self._strip, shift=8)

    def __del__(self):
        # TODO - tidy up the state machine
        pass

    def __repr__(self):
        # TODO - encode the class state - including which PIO
        pass

    def __str__(self):
        # Convert the state to a string
        pass

    @staticmethod
    def firelight(strip, brightness, fade, speed, blocks, dim):
        """ Create a fire-like effect on an LED panel

        Args:
            strip (array of Int): The LEDs
            brightness (Int): Overall brightness in the range 0-255
            fade (Int): Speed of the fade in the range 0-255
            speed (Int): Speed of brightening in the range 0-255
            blocks (Int): The number of blocks to break the array into (should be a power of 2 less than the number of LEDs for a good effect)
            dim (Int): The number of blocks NOT to brighten (should be less than blocks)
        """        """"""
        fade_r         = 0.96  # How quickly the redness fades
        fade_g         = 0.60  # How quickly the greenness fades
        fade_b         = 0.36  # How quickly the blueness fades
        warmth         = 60   # Maximum percentage component of green
        coolth         = 5    # Maximum percentage component of blue

        # First fade everything out slightly
        for led in range(len(strip)):
            # Read the current colour
            red   = (strip[led] >>  8) & 0xff
            green = (strip[led] >> 16) & 0xff
            blue  = (strip[led] >>  0) & 0xff
            
            # Fade it a little bit
            red   = int(red   * fade_r * fade / 255)
            green = int(green * fade_g * fade / 255)
            blue  = int(blue  * fade_b * fade / 255)
            strip[led] = (green << 16) + (red << 8) + blue

        # Occasionally brighten some blocks up
        if (randint(0,255) <= speed):
            leds_per_block = int(len(strip)/blocks)
            for block in range(blocks - dim):
                start_led = randint(0,blocks-1) * leds_per_block
                end_led   = start_led + leds_per_block

                # Set a random intensity and colour for each LED in the block
                for led in range(start_led, end_led):
                    red   = randint(warmth,    255)
                    green = randint(warmth//2, (red   * warmth) // 100)
                    blue  = randint(0,         (green * coolth) // 100)

                    # Apply the master brightness factor
                    red   = int(red   * brightness / 255)
                    green = int(green * brightness / 255)
                    blue  = int(blue  * brightness / 255)
                    strip[led] = (green << 16) + (red << 8) + blue

    @staticmethod
    def fill(strip, brightness, r, g, b):
        """ Fill the entire LED panel with a single colout

        Args:
            strip (array of ints): The LED array to fill
            brightness (int): An overall brightness in the range 0...255
            r (int): The amount of red in the range 0...255
            g (int): The amount of green in the range 0...255
            b (int): The amount of blue in the range 0...255
        """
        # Merge the overall brightness into the RGB values
        r = int(r * brightness/255)
        g = int(g * brightness/255)
        b = int(b * brightness/255)

        # Set all of the LEDs to the calculated colour
        value = (b & 0xff) + (r & 0xff) << 8 + (g & 0xff) << 16
        for led in range(len(strip)):
            strip[led] = value

    def update(self, r=0, g=0, b=0, brightness=255, fade=255, speed=0, blocks=8, dim=3):
        if r>0 or g>0 or b>0:
            # If any of RGB are non-zero, create a simple colour wash as specified
            led_panel.fill(self._strip, brightness, r, g, b)
        else:
            # Create a fire-like effect
            led_panel.firelight(self._strip, brightness, fade, speed, blocks, dim)

        self._sm.put(self._strip, 8)