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
        self._sm.put(self._strip, 8)

        # Initialise a counter for the beacon and strobe functions
        self._count = 0

    def __del__(self):
        # TODO - tidy up the state machine
        pass

    def __repr__(self):
        # TODO - encode the class state - including which PIO
        pass

    def __str__(self):
        # Convert the state to a string
        pass

    def firelight(self, brightness, red, green, blue, speed, fade):
        """ Create a fire-like effect on an LED panel """
        fade_r         = 0.96  # How quickly the redness fades
        fade_g         = 0.60  # How quickly the greenness fades
        fade_b         = 0.36  # How quickly the blueness fades
        blocks         = 8     # 

        strip = self._strip

        # First fade everything out slightly
        for led in range(len(strip)):
            # Read the current colour
            R = (strip[led] >>  8) & 0xff
            G = (strip[led] >> 16) & 0xff
            B = (strip[led] >>  0) & 0xff
            
            # Fade it a little bit
            R = int(R * fade_r * fade / 255)
            G = int(G * fade_g * fade / 255)
            B = int(B * fade_b * fade / 255)
            strip[led] = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)

        # Occasionally brighten some blocks up
        if (randint(0,255) <= speed):
            leds_per_block = int(len(strip)/blocks)
            for block in range(blocks - dim):
                start_led = randint(0,blocks-1) * leds_per_block
                end_led   = start_led + leds_per_block

                # Set a random intensity and colour for each LED in the block
                for led in range(start_led, end_led):
                    R = randint(red//2,  red)         # Must be at least half of Red
                    G = randint(0,  max(R//2, green)) # Can't be more than half of R
                    B = randint(0,  max(G//2, blue))  # Can't be more than half of G

                    # Apply the master brightness factor
                    R = int(R * brightness / 255)
                    G = int(G * brightness / 255)
                    B = int(B * brightness / 255)
                    strip[led] = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)

    def fill(self, brightness, red, green, blue):
        """ Fill the entire LED panel with a single colout

        Args:
            strip (array of ints): The LED array to fill
            brightness (int): An overall brightness in the range 0...255
            r (int): The amount of red in the range 0...255
            g (int): The amount of green in the range 0...255
            b (int): The amount of blue in the range 0...255
        """
        # Merge the overall brightness into the RGB values
        R = int(red   * brightness/255)
        G = int(green * brightness/255)
        B = int(blue  * brightness/255)

        # Set all of the LEDs to the calculated colour
        value = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)
        for led in range(len(strip)):
            self._strip[led] = value

    def update(self):
        self._sm.put(self._strip, 8)