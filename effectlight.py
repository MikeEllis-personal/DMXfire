from dmx       import DMX_RX
from led_panel import led_panel
import _thread
import gc

# DMX channel allocation
start_address = 140

# Shared variables to communicate from the DMX receiver to the effect functions
brightness    = 0 
red           = 0 
green         = 0 
blue          = 0 
effect        = 0 
speed1        = 0
speed2        = 0

thread_running = True

def run_effect_as_thread(panel):
    # Start the firelight as a second thread
    _thread.start_new_thread(run_effect, (panel))

def run_effect(panel):
    while thread_running:
        update_effect(panel)
        #gc.collect()
    print("Thread exiting")

def update_effect(panel):
    if effect < 64:   # Solid colour
        panel.fill(brightness, red, green, blue) 
    elif effect < 128:
        pass # Beacon
    elif effect < 192:
        pass # Strobe
    else:
        panel.firelight(brightness=brightness, red=red, green=green, blue=blue, speed=speed1, fade=speed2)

    panel.update()

def start_effect():
    # Initialise the DMX receiver
    dmx_start = 140

    dmx_in  = DMX_RX(pin=28) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()
    last_frame = -1

    # Initialise the LED panel
    panel = led_panel(pin=27, leds=256)

    try:
        run_effect_as_thread(panel)

        while True:
            global brightness # Overall brightness of the effect
            global red        # Base colour - RED
            global green      # Base colour - GREEN
            global blue       # Base colour - Blue
            global effect     # Effect
                              #    000 - 063: Solid colour - no speed control
                              #    064 - 127: Beacon       - speed1 = rotation speed, speed2 = rotation width
                              #    128 - 191: Strobe       - speed1 = on time,        speed2 = off time
                              #    192 - 254: Firelight    - speed1 = brightening,    speed2 = fade
            global speed1
            global speed2

            brightness = dmx_in.channels[start_address + 0]
            red        = dmx_in.channels[start_address + 1]
            green      = dmx_in.channels[start_address + 2]
            blue       = dmx_in.channels[start_address + 3]
            effect     = dmx_in.channels[start_address + 4]
            speed1     = dmx_in.channels[start_address + 5]
            speed2     = dmx_in.channels[start_address + 6]

            current_frame = dmx_in.frames_received

            if current_frame != last_frame:
                last_frame = current_frame
                print(f"Frame {last_frame}  Fade:{brightness} R:{red} G:{green} B:{blue} Effect:{effect} Sp1:{speed1} Sp2:{speed2}")
    except:
        global thread_running
        thread_running = False    