from dmx import DMX_RX
from fire import led_panel
from time import sleep_ms

def dmx_test():
    # Initialise the DMX receiver
    dmx_start_channel = 128
    dmx_in  = DMX_RX(pin=28) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()

    last_irq = -1

    while True:
        irq = dmx_in.irq_count

        if irq != last_irq:
            print(f"Ch:{dmx_start_channel} Rx:", end="")
            for n in range(5):
                print(f"{dmx_in.channels[dmx_start_channel+n]:3}  ", end="")
            print(f" IRQ#:{irq}")
            last_irq = irq

def fire_test():
    # Initialise the firelight effect
    firelight = led_panel(pin=27, leds=256)

    while True:
        firelight.update(brightness = 255, 
                         fade       = 64,
                         speed      = 64)