import array
import rp2

from time     import sleep_ms
from random   import randint
from machine  import Pin
from neopixel import ws2812
class led_panel:
    def __init__(self, pin, width, height, statemachine=0):
        # Create the StateMachine with the ws2812 program
        self._sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(pin))
        self._sm.active(1)

        # Initialise the LED array to all off
        self._width  = width
        self._height = height
        self._strip  = array.array("I", [0 for _ in range(width * height)]) # GRB colour order
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
        fade_r         = 224 * fade # How quickly the redness fades
        fade_g         = 192 * fade # How quickly the greenness fades
        fade_b         = 128 * fade # How quickly the blueness fades
        leds_per_block = 64
        blocks         = (self._width * self._height) // leds_per_block

        strip = self._strip

        # First fade everything out slightly
        for led in range(len(strip)):
            # Read the current colour
            R = (strip[led] >>  8) & 0xff
            G = (strip[led] >> 16) & 0xff
            B = (strip[led] >>  0) & 0xff
            
            # Fade it a little bit
            R = (R * fade_r) >> 16 
            G = (G * fade_g) >> 16
            B = (B * fade_b) >> 16

            # Write the colour back to the strip
            strip[led] = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)

        # Occasionally brighten some blocks up
        if (randint(0,255) <= speed):

            # Only brighten about three-quarters of the blocks each time
            for block in range(blocks * 3 // 4):

                # Pick a block at random
                start_led = randint(0,blocks-1) * leds_per_block
                end_led   = start_led + leds_per_block

                # Pick a random intensity and colour for each block
                R = randint(red//8,               red)              # Must be at least half of Red
                G = randint(min(R//16, green//4), min(R//8, green)) # Can't be more than half of R
                B = randint(min(G//16, blue//4),  min(G//8, blue))  # Can't be more than an eighth of G

                # Apply the master brightness factor
                R = (R * brightness) >> 8
                G = (G * brightness) >> 8
                B = (B * brightness) >> 8

                for led in range(start_led, end_led):
                    strip[led] = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)
                    
    def fill(self, brightness, red, green, blue):
        """ Fill the entire LED panel with a single colour

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
        for led in range(len(self._strip)):
            self._strip[led] = value

    def beacon(self, brightness, red, green, blue, speed, stripe):
        # Merge the overall brightness into the RGB values
        R = int(red   * brightness/255)
        G = int(green * brightness/255)
        B = int(blue  * brightness/255)
        value = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)

        # Increment the count
        self._count += speed * 4
            
        offset = (self._count // 255) % self._width
        if offset == 0:
            self._count = 0

        # Convert the stripe width from 0-255 into 1-width
        stripe = ((stripe * self._width) // 255) +1

        # Set all of the LEDs to the calculated colour
        for led in range(len(self._strip)):
            column = led // self._height

            if (column + offset) % self._width < stripe:
                self._strip[led] = value
            else:
                self._strip[led] = 0

    def strobe(self, brightness, red, green, blue, speed1, speed2):

        # Increment the count
        self._count += 1
        if self._count > (speed1 + speed2)/8:
            self._count = 0

        if self._count < speed1/8:
            # Merge the overall brightness into the RGB values
            R = int(red   * brightness/255)
            G = int(green * brightness/255)
            B = int(blue  * brightness/255)
            value = (B & 0xff) + ((R & 0xff) << 8) + ((G & 0xff) << 16)
        else:
            value = 0

        # Set all of the LEDs to the calculated colour
        for led in range(len(self._strip)):
            self._strip[led] = value

    def update(self):
        self._sm.put(self._strip, 8)
        sleep_ms(10) # Make sure there is some dead time before re-triggering the PIO