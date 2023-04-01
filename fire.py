import array
from machine import Pin
import rp2
from time import sleep
from random import seed, randint

import array, time
from machine import Pin
import rp2

# Build the PIO driver for the WS2812 led array
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

fade_r         = 0.9
fade_g         = 0.5
fade_b         = 0.3
leds           = 256
blocks         = 8
dimblocks      = 3
leds_per_block = int(leds/blocks)
glow           = 40
warmth         = 60   # Maximum percentage component of green
coolth         = 5    # Maximum percentage component of blue
wait           = 0.01 # Pause between cycles
cycletime      = 6    # Number of loops between brightenings


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