# Example using PIO to drive a set of WS2812 LEDs.

import array, time
from machine import Pin
import rp2

# Configure the number of WS2812 LEDs.
NUM_LEDS = 256


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

print("Creating state machine")

# Create the StateMachine with the ws2812 program, outputting on Pin(22).
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(22))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(NUM_LEDS)])

ar[0] = 0x9f000000 # Green
ar[1] = 0x009f0000 # Red
ar[2] = 0x00009f00 # Blue
ar[3] = 0x9f9f0000 # Yellow
ar[4] = 0x009f9f00 # Magenta
ar[5] = 0x9f009f00 # Cyan
ar[6] = 0x00202000 # Dim magenta
print(ar)
sm.put(ar)
time.sleep_ms(1000)
    
# Cycle colours.
while True:
    for i in range(4 * NUM_LEDS):
        for j in range(NUM_LEDS):
            r = j * 100 // (NUM_LEDS - 1)
            b = 100 - j * 100 // (NUM_LEDS - 1)
            if j != i % NUM_LEDS:
                r >>= 3
                b >>= 3
            ar[j] = r << 16 | b
        print(f"Bright {i}")
        sm.put(ar, 8)  # Shift left by 8 bits so the value is taken from bytes 2..0 not 3..1
        time.sleep_ms(5)

    # Fade out.
    for i in range(24):
        for j in range(NUM_LEDS):
            ar[j] = 1 << i
        print(f"Flash {i}")
        sm.put(ar, 8)
        time.sleep_ms(5)
