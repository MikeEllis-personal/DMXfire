from dmx       import DMX_RX
from led_panel import led_panel
import _thread
import gc

# DMX channel allocation
start_address = 140

# Shared variables to communicate from the DMX receiver in one thread (only writing) to the effect functions in another (only reading)
brightness    = 0 
red           = 0 
green         = 0 
blue          = 0 
effect        = 0 
speed1        = 0
speed2        = 0
red2          = 0
green2        = 0
blue2         = 0

thread_running = True

def run_effect_as_thread():
    # Start the firelight as a second thread
    print("Starting effect thread")
    _thread.start_new_thread(run_effect, ())

def run_effect():
    panel = led_panel(pin=27, width=32, height=32)

    while thread_running:
        update_effect(panel)
    print("Thread exiting")

def update_effect(panel):
    if effect < 64:     # Solid colour
        panel.fill(brightness, red, green, blue) 
    elif effect < 128:  # Beacon
        panel.beacon(brightness, red, green, blue, speed1, speed2)
    elif effect < 192:  # Strobe
        panel.strobe(brightness, red, green, blue, speed1, speed2)
    else:               # Firelight 
        panel.firelight(brightness, red, green, blue, speed1, speed2)

    panel.update()

def test_effect(f, r, g, b, e, s1, s2, r2, g2, b2):
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
    global red2
    global green2
    global blue2

    brightness = f
    red        = r
    green      = g
    blue       = b
    effect     = e
    speed1     = s1
    speed2     = s2
    red2       = r2
    green2     = g2
    blue2      = b2

    panel = led_panel(pin=27, width=32, height=32)

    for i in range(500):
        update_effect(panel)

    brightness = 0
    effect = 0
    update_effect(panel)

def start_effect(dmx_start):
    # Initialise the DMX receiver
    dmx_in  = DMX_RX(pin=28) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()
    last_frame = -1

    try:
        run_effect_as_thread()

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
            global red2
            global green2
            global blue2

            # Copy the current DMX values into the global parameters read by the other thread
            brightness = dmx_in.channels[start_address + 0]
            red        = dmx_in.channels[start_address + 1]
            green      = dmx_in.channels[start_address + 2]
            blue       = dmx_in.channels[start_address + 3]
            effect     = dmx_in.channels[start_address + 4]
            speed1     = dmx_in.channels[start_address + 5]
            speed2     = dmx_in.channels[start_address + 6]
            red2       = dmx_in.channels[start_address + 7]
            green2     = dmx_in.channels[start_address + 8]
            blue2      = dmx_in.channels[start_address + 9]

            #current_frame = dmx_in.frames_received

            #if current_frame != last_frame:
            #    last_frame = current_frame
            #    print(f"D{brightness}", end="")
            #    print(f"Frame {last_frame}  Fade:{brightness} R:{red} G:{green} B:{blue} Effect:{effect} Sp1:{speed1} Sp2:{speed2}")

    except Exception as e: # If anything goes wrong, kill the thread and re-raise the exception.
        global thread_running
        thread_running = False 
        raise e   