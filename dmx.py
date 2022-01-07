import rp2
from machine import Pin, Timer
import time

from uctypes import addressof

import dma

# DMX in C++ with PIO and DMA: https://github.com/jostlowe/Pico-DMX
#
# MicroPython SDK: https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf
# RP2 MicroPython documentation: https://docs.micropython.org/en/latest/library/rp2.html
# RP2040 datasheet: https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
#
# PIO and DMA: https://pythonrepo.com/repo/benevpi-RP2040_micropython_dma-python-programming-with-hardware or https://github.com/benevpi/RP2040_micropython_dma?ref=pythonrepo.com
# DMA discussions on the MicroPython forum and other websites:
#   * https://forum.micropython.org/viewtopic.php?f=21&t=10717
#   * https://forum.micropython.org/viewtopic.php?f=21&t=9697
#   * https://www.instructables.com/Arbitrary-Wave-Generator-With-the-Raspberry-Pi-Pic/


@rp2.asm_pio(fifo_join=rp2.PIO.JOIN_RX, in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=False)
def dmx_in():
    label("break_reset")
    set(x, 29)                                # Setup a counter to count the iterations on break_loop
    label("break_loop")                       # Break loop lasts for 8us. The entire break must be minimum 30*3us = 90us
    jmp(pin, "break_reset")                   # Go back to start if pin goes high during the break
    jmp(x_dec, "break_loop")            [1]   # Decrease the counter and go back to break loop if x>0 so that the break is not done
    wait(1, pin, 0)                           # Stall until line goes high for the Mark-After-Break (MAB) 
    wrap_target()
    wait(0, pin, 0)                           # Stall until start bit is asserted
                                              # TODO - If it doesn't go low soon, it's the end of the universe - how do we signal thus
    set(x, 7)                           [4]   # Load the bit counter - expecting 8 bits, then delay until halfway through the first bit
    label("bitloop")
    in_(pins, 1)                              # Shift data bit into ISR
    jmp(x_dec, "bitloop")               [2]   # Loop 8 times, each loop iteration is 4us
    wait(1, pin, 0)                           # Wait for pin to go high for stop bits
                                              # TODO - if it's doesn't go high soon, it's BREAK - how do we signal this?
    in_(null, 24)                             # Push 24 more bits into the ISR so that our one byte is at the position where the DMA expects it
    push()                                    # Should probably do error checking on the stop bits some time in the future....
    wrap()

# TODO input PIO code doesn't signal the start of frame to the DMA controller, it just locks up until the next transition is detected
# This will cause problems if the received universe is not the expected length (both too short and too long will be challenging)

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_HIGH, autopull=False, out_init=rp2.PIO.OUT_HIGH, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def dmx_out():
    pull()                  .side(1)          # Stall with line IDLE until the DMA transfer begins
    set(x, 21)              .side(0)          # Assert BREAK for 176us (=22*(1+7)us)
    label("breakloop")                         
    jmp(x_dec, "breakloop")             [7]    

    nop()                   .side(1)    [7]   # Assert MAB. 1+7+1+7 cycles = 16us
    nop()                               [7]

    wrap_target()                             # Send data frame - OSR already has the first byte in it from earlier
    set(x, 7)               .side(0)    [3]   # Send START bit (4us) and load the bit counter

    label("bitloop")                          
    out(pins, 1)                              # Shift 1 bit (4us) from OSR to the line
    jmp(x_dec, "bitloop")               [2]   

    pull()                  .side(1)    [7]   # Send 2 STOP bits (8us), or stall with line in idle state
    wrap()

class DMX:
    """ Interface to a DMX universe for reading or writing using a PIO module.
    Quick theory of operation:

    DMX basics:
        DMX data frames comprise a long (176us) "break" as a logic low, followed by a 16us "MarkAfterBreak" as a logic high, 
        then a series of bytes in 8N2 MSB-first format at 4us/bit. Each data frame is known as a Universe and comprises a 
        single-byte Start Code (0 for DMX) followed by between 1 and 512 data bytes, one byte per lighting channel

    Transmission:
        A DMA channel is set up to copy a bytearray (address automatically incrementing on each transfer) into the PIO FIFO 
        (at a fixed address). When this transfer completes, the DMA channel raises an interrupt and the handler resets both the 
        PIO and the DMA channel. When restarted, the PIO first ensures that the DMX "break" is sent, then the 
        MarkAfterBreak, before streaming out the bytes as sent by the DMA into its FIFO. As the PIO completes each byte, a 
        Data Request (DREQ) interrupt is raised to start the next DMA transfer. The need to send the Break and MAB by resetting
        the PIO are the reason we can't just chain two DMA channels together where the second channel simply reloads the first.

        1. PIO sends Break and half of the MAB - the second half of the MAB comes from the stop bits which are sent next
        2. PIO then pulls data from the DMA, triggering a DREQ, and sends the stop bits (8us), the start bit (4us), then 8 data bits. 
        2. Upon receipt of the DREQ, DMA sends the next byte to the PIO input FIFO
        3. When the entire Universe has been DMA'd, the DMA raises a processor interrupt
        4. When the DMA interrupt is received, the processor resets the PIO and restarts the DMA 

        TODO: Need to make sure that the last few values aren't lost in the FIFO before the PIO has chance to send them

    Reception:
        A PIO is constantly watching the DMX input pin. Once a valid Break and MarkAfterBreak are observed, subsequent 8N2 
        bytes are passed to the PIO FIFO which is read by the DMA channel and copied into the bytearray.

        1. The PIO waits for a very long run of zeros (176us or more - Break)
        2. The PIO waits for a one (any length - MAB) - there is no check that this is the correct length (16us)
        3. The PIO waits for a zero (start bit) and starts to sample the data ~6us later - the start bit should be 4us long
        4. The PIO captures 8 bits, one every 4us, and shifts these into the ISR
        5. The PIO waits for a one (stop bit), and sends the ISR to the DMA
        6. The PIO then loops back to step 3 - there is no check that the stop bit is the correct length (8us)
        7. The DMA accepts the byte from the PIO and stores it in memory
        8. When the DMA has accepted the correct number of bytes, it triggers a processor interrupt
        9. When the DMA interrupt is received, the processors resets the PIO and restarts the DMA

    Class basics:
        Put simply, the class sets up the DMA and PIO and then provides a convenient interface to the bytearray used by the
        DMA controller. Setting or reading individual channels is permitted, as is reading/writing the entire Universe. When 
        used as a transmitter, the class uses DMA and PIO to repeatedly send the universe. When used as a receiver, each received
        universe is copied and made available to the user as soon as it is received.

    DMA Channel and PIO allocations:
        It is not possible to check the hardware to see if a DMA channel or PIO statemachine is already in use. No extra locking
        has been added in this software, thus clashes need to be avoided by the user code.
    """

    # Useful constants
    RX = 0
    TX = 1

    def __init__(self, pin, direction=RX, universe_size=512, statemachine=0, dmachannel=0):
        """ Initialisation of the DMX controller

        Args:
            pin (numeric):                  Pin number to use
            direction (TX or RX, optional): Is this a DMX transmitter or receiver? Defaults to RX.
            universe_size (int, optional):  Size of the DMX universe to interface to. Defaults to 512.
            statemachine (int, optional):   Which PIO statemachine should be used. Defaults to 0.
            dmachannel (int, optional):     Which DMA channel should be used. Defaults to 0.

        Raises:
            ValueError: Any invalid parameters are reported as exceptions
        """
        if universe_size < 1 or universe_size > 512:
            raise ValueError("DMX universes must have 1...512 channels")
        
        self._universe_size = universe_size
        self._universe = bytearray([0 for _ in range(universe_size+1)]) # +1 because DMX-0 is the start code, with channels 1-512 behind it

        if (direction == DMX.TX):
            self._pin       = Pin(pin, Pin.OUT, Pin.PULL_UP)
            self._direction = DMX.TX
            self._sm = rp2.StateMachine(statemachine, dmx_out, freq=1_000_000, sideset_base=self._pin, out_base=self._pin)
            # TODO - initialise the DMA for transmission
            self._dma = dma.DmaChannel(dmachannel)
            self._dma.NoWriteIncr()
            self._dma.SetTREQ(0) # TODO - hard coded as PIO0 TX0

        else:
            self._pin       = Pin(pin, Pin.IN)
            self._direction = DMX.RX
            # TODO - initialise the PIO state machine for reception


    def __del__(self):
        # TODO - tidy up the state machine and DMA channels
        
    #def __repr__(self):
        # TODO - encode the class state - including which PIO and DMA channel are in use
        pass

    def __str__(self):
        result = f"Start code: {self._universe[0]}"
        for chan in range(1, self._universe_size+1):
            if chan % 20 == 1:
                result += f"\n{chan:03}:"
            if chan % 5 == 1:
                result += "  "
            result += f" {self._universe[chan]:3}"
            if chan % 100 == 0:
                result += "\n"
        
        result += "\n"
        return result
        # TODO - debug readable stringification of the DMX class

    def read(self, chan):
        # TODO - read a specific channel value from the last received DMX frame
        # If this is a DMX transmitter, will return the current sending value for this channel
        return self._universe[chan]
        # TODO error checking and handling

    def send(self, chan, value):
        """Set then specifed channel to the desired value

        Args:
            chan  (numeric): Must be in the range of the universe (1-512 typically)
            value (numeric): Must be an integer in the range 0-255
        """
        if self._direction == DMX.RX:
            raise ValueError("DMX receivers cannot send values")

        if chan < 1 or chan > self._universe_size:
            raise ValueError(f"DMX channel number must be in the range 1...{self._universe_size}")

        if value < 0 or value > 255:
            raise ValueError("DMX values must be in the range 0...255")

        self._universe[chan] = value
    
    def pause(self):
        self._sm.active(0)


    def start(self, t):
        self._sm.active(1)
        self._sm.restart()
        self._dma.SetChannelData(addressof(self._universe), 0x50200010, self._universe_size +1, True)

    @property
    def universe(self):
        return self._universe

    @universe.setter
    def universe(self, values, start_chan=0):
        """ TODO - update the entire universe """
        # Must be passed an array of numeric values, with at most the correct number of values
        pass

    @staticmethod
    def test():
        d = DMX(3, DMX.TX)
        t = Timer(period=50, callback=d.start)

        #print(d)

        d.send(1,85)
        d.send(2, 0b0111_1111) # Should be L4us  H28us L4us  H8us
        d.send(3, 0b0011_1110) # Should be L8us  H20us L8us  H8us
        d.send(4, 0b0001_1100) # Should be L12us H12us L12us H8us
        d.send(5, 0b0000_0001) # Should be L4us  H4us  L28us H8us
        d.send(6, 0b1000_0011) # Should be L4us  H8us  L20us H12us
        d.send(7, 0b1100_0111) # Should be L4us  H12us L12us H16us
        d.send(8,1)
        d.send(10,170)
        d.send(12,85)
        d.send(16,250)
        d.send(17,251)
        d.send(18,252)
        d.send(19,253)
        d.send(20,85)
        d.send(512,85)

        #print(d)

        #print(d._sm)

        for n in range(256):
            d.send(1,n)
            time.sleep_ms(500)
        
        #t.deinit()

        #for n in range(200):
        #    d._sm.restart()
        #    d._sm.put(d._universe)
        #    sleep_ms(20)

        #d.pause()