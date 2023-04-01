import dmx
import fire

# Initialise the DMX receiver
dmx_start_channel = 130
dmx_in  = DMX_RX(pin = 28) # DMX data should be presented to GPIO28 (Pico pin 34)
dmx_in.start()

# Initialise the fire effect

while True:
    # Read latest DMX values and adjust fire flicker parameters appropriately

    # Update the firelight
    pass