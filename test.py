from dmx import DMX_RX
from fire import led_panel
from time import sleep_ms

def dmx_test():
    # Initialise the DMX receiver
    dmx_start_channel = 128
    dmx_in  = DMX_RX(pin=28) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()

    last_frame = -1

    while True:
        current_frame = dmx_in.frames_received

        if current_frame != last_frame:
            print(f"Ch:{dmx_start_channel} Rx:", end="")
            for n in range(5):
                print(f"{dmx_in.channels[dmx_start_channel+n]:3}  ", end="")
            print(f" Frames Rxd:{current_frame}")
            last_frame = current_frame

def fire_test():
    # Initialise the firelight effect
    firelight = led_panel(pin=27, leds=256)

    while True:
        firelight.update(brightness = 255, 
                         fade       = 64,
                         speed      = 64)