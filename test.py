from dmx import DMX_RX
from time import sleep_ms

def dmx_fire():
    # Initialise the DMX receiver
    dmx_start_channel = 130
    dmx_in  = DMX_RX(pin=28, irqpin=2) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()
    
    while True:
        print(f"Ch:{dmx_start_channel} Rx:{dmx_in.channels[dmx_start_channel]:3} {dmx_in.channels[dmx_start_channel+1]:3} {dmx_in.channels[dmx_start_channel+2]:3} IRQ:{dmx_in.irq_count}")
        sleep_ms(100)
