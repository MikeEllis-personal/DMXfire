from dmx import DMX_RX
from led_panel import led_panel
import _thread
import gc

brightness = 0
red        = 1
green      = 2
blue       = 3
fade       = 4
speed      = 5
thread_running = True

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
        firelight.update(brightness = 255, fade = 64, speed = 64)

def firelight():
    # Initialise the firelight effect
    firelight = led_panel(pin=27, leds=256)

    while thread_running:
        print(f"Perform  fader:{brightness}  R:{red} G:{green} B:{blue}")
        firelight.update(brightness = brightness, red = red, green=green, blue=blue, fade=fade, speed=speed)
        #gc.collect()
    print("Thread exiting")

def test_both():
    # Initialise the DMX receiver
    dmx_start = 140

    dmx_in  = DMX_RX(pin=28) # DMX data should be presented to GPIO28 (Pico pin 34)
    dmx_in.start()
    last_frame = -1

    try:
        # Start the firelight as a second thread
        _thread.start_new_thread(firelight, ())

        while True:
            global brightness
            global red
            global green
            global blue
            global fade
            global speed

            brightness = dmx_in.channels[dmx_start + 0]
            red        = dmx_in.channels[dmx_start + 1]
            green      = dmx_in.channels[dmx_start + 2]
            blue       = dmx_in.channels[dmx_start + 3]
            fade       = dmx_in.channels[dmx_start + 4]
            speed      = dmx_in.channels[dmx_start + 5]

            current_frame = dmx_in.frames_received

            if current_frame != last_frame:
                last_frame = current_frame
                print(f"Received fader:{brightness}  R:{red} G:{green} B:{blue}")
    except:
        global thread_running
        thread_running = False    