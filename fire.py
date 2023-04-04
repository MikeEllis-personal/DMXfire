import array
from time import sleep
from random import seed, randint
from machine import Pin
import rp2                            # type: ignore
from neopixel import ws2812


class led_panel:
    def __init__(self, pin, leds, statemachine=0):
        # Create the StateMachine with the ws2812 program, outputting on Pin(22).
        self._sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(pin))
        self._sm.active(1)
        self._strip = array.array("I", [0 for _ in range(leds)]) # GRB colour order

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
        fade_r         = 0.8  # How quickly the redness fades
        fade_g         = 0.5  # How quickly the greenness fades
        fade_b         = 0.3  # How quickly the blueness fades
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

        # Next sometimes brighten some blocks up again
        if (randint(0,255) <= speed):
            leds_per_block = int(len(strip)/blocks)
            for block in range(blocks - dim):
                start_led = randint(0,blocks-1) * leds_per_block
                end_led   = start_led + leds_per_block

                # Set an intensity for each LED in the block
                for led in range(start_led, end_led):
                    red   = randint(warmth,    255)
                    green = randint(warmth//2, (red   * warmth) // 100)
                    blue  = randint(0,         (green * coolth) // 100)

                    red   = int(red   * brightness / 255)
                    green = int(green * brightness / 255)
                    blue  = int(blue  * brightness / 255)
                    strip[led] = (green << 16) + (red << 8) + blue

    @staticmethod
    def fill(strip, r, g, b):
        value = (b & 0xff) + (r & 0xff) << 8 + (g & 0xff) << 16
        for led in range(len(strip)):
            strip[led] = value

    def update(self, r=0, g=0, b=0, brightness=0, fade=255, speed=0, blocks=8, dim=3):
        if r>0 or g>0 or b>0:
            # If any of RGB are non-zero, create a simple colour wash as specified
            led_panel.fill(self._strip, r, g, b)
        else:
            # Create a fire-like effect
            led_panel.firelight(self._strip, brightness, fade, speed, blocks, dim)

        self._sm.put(self._strip, 8)

"""

leds           = 256
glow           = 40
cycletime      = 6    # Number of loops between brightenings
wait           = 0.01 # Pause between cycles

def fade(strip):
    # Fade all LEDs a bit

    for i in range(len(strip)):
        red   = (strip[i] >>  8) & 0xff
        green = (strip[i] >> 16) & 0xff
        blue  = (strip[i] >>  0) & 0xff
        
        red   = int(red   * fade_r)
        green = int(green * fade_g)
        blue  = int(blue  * fade_b)
        
        strip[i] = (green << 16) + (red << 8) + blue 

def brighten(strip):
    for block in range(blocks - dimblocks):
        start_led = randint(0,blocks-1) * leds_per_block
        end_led   = start_led + leds_per_block

        # Set an intensity for each LED in the block
        for led in range(start_led, end_led):
            red   = randint(warmth,    255)
            green = randint(warmth//2, (red   * warmth) // 100)
            blue  = randint(0,         (green * coolth) // 100)
            value = (green << 16) + (red << 8) + blue
            
            strip[led] = value
            
            #print(f"{led:3}:{inten:3}+{shift:2} = {red}/{green}/{blue} = {value} = {strip[led]}")

def fill(strip, value):
    for led in range(len(strip)):
        strip[led] = value
       
def fire_effect(sm):
    strip = array.array("I", [0 for _ in range(leds)])             # GRB

    while True:
        brightphase = randint(0, cycletime)
    
        for loop in range(cycletime):
            fade(strip)
    
            if loop == brightphase:
                brighten(strip)
        
            sm.put(strip, 8)
        
            sleep(wait)

def selftest(sm):
    strip = array.array("I", [0 for _ in range(leds)])             # GRB

    # Initialise test - flash Red, Green and Blue for one second each
    fill(strip, 0x0000ff00)
    sm.put(strip, 8)
    sleep(1)
    fill(strip, 0x00ff0000)
    sm.put(strip, 8)
    sleep(1)
    fill(strip, 0x000000ff)
    sm.put(strip, 8)
    sleep(1)
    
# Create the StateMachine with the ws2812 program, outputting on Pin(22).
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(22))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

selftest(sm)
fire_effect(sm)
"""