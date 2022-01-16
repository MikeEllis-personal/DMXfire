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
#
# DMX timing: https://support.etcconnect.com/ETC/FAQ/DMX_Speed


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_HIGH, fifo_join=rp2.PIO.JOIN_RX, in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=False)
#@rp2.asm_pio(fifo_join=rp2.PIO.JOIN_RX, in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=False)
def dmx_in():
    # Look for the BREAK - minimum 90us low time
    #set(x, 29)            .side(0)
    label("break_reset")
    set(x, 29)                 .side(0)               # Setup a counter to count the iterations on break_loop
    label("break_loop")                       # Break loop lasts for 8us. The entire break must be minimum 30*3us = 90us
    jmp(pin, "break_reset")                   # Go back to start if pin goes high during the break
    jmp(x_dec, "break_loop")            [1]   # Keep waiting until 90us has elapsed TODO - why the one wait here? Counting to a higher value would be better (faster)

    # Now wait for the mark after break
    wait(1, pin, 0)                           # Stall until line goes high for the Mark-After-Break (MAB) TODO - minimum MAB value is 12us, not checked

    # Now we just need a simple 8N2 UART
    wrap_target()

    # Start bit
    wait(0, pin, 0)        .side(1)                   # Stall until start bit is asserted
    set(x, 7)                           [4]   # Load the bit counter (expecting 8 bits) then delay 6us (wait + set + 4 delay) until halfway through the first bit

    # 8 data bits
    label("bitloop")
    in_(pins, 1)                              # Shift data bit into ISR
    jmp(x_dec, "bitloop")               [2]   # Loop 8 times, each loop iteration is 4us (in + jmp + 2 delay)

    # Look for the stop bit: TODO - not yet implemented correctly
    #     if we get a stop bit, store the value just received to the RX FIFO and thus trigger a DMA
    #     if we DON'T get a stop bit, the last thing we received was actually the start of the next BREAK - send an IRQ to reset the DMA controller
    #wait(1, pin, 0)                           # Wait for pin to go high for stop bits
    jmp(pin, "got_stopbit")                    # Check to see if we got the stop bit 
    irq(block, rel(0))                               # TODO Hard coded as PIO relative IRQ0 at the moment
    jmp("break_reset")                        # No stop bit - must be a BREAK! TODO will need to assert an interrupt here eventually and block
    
    label("got_stopbit")
    push(noblock)                                    # DMA will read a byte from +3, so no need to shift
    wrap()

# TODO input PIO code doesn't signal the start of frame to the DMA controller, it just locks up until the next transition is detected
# This will cause problems if the received universe is not the expected length (both too short and too long will be challenging)
# One option might be to detect the Break, and whilst the break is still present, push() out any missing channels as zeroes, with the DMA set to
# auto loop (can this be a ring - with 513 bytes, probably not). Alternatively raise an IRQ during the Break to get the main code to reset
# everything?

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

    """ Interface to a DMX universe for sending using a PIO module.
    Quick theory of operation:

    DMX basics:
        DMX data frames comprise a long (176us) "break" as a logic low, followed by a 16us "MarkAfterBreak" as a logic high, 
        then a series of bytes in 8N2 MSB-first format at 4us/bit. Each data frame is known as a Universe and comprises a 
        single-byte Start Code (0 for DMX) followed by between 1 and 512 data bytes, one byte per lighting channel

    Class basics:
        Put simply, the class sets up the DMA and PIO and then provides a convenient interface to the bytearray used by the
        DMA controller. Setting or reading individual channels is permitted, as is reading/writing the entire Universe. When 
        used as a transmitter, the class uses DMA and PIO to repeatedly send the universe. When used as a receiver, each received
        universe is copied and made available to the user as soon as it is received.

    DMA Channel and PIO allocations:
        It is not possible to check the hardware to see if a DMA channel or PIO statemachine is already in use. No extra locking
        has been added in this software, thus clashes need to be avoided by the user code.
    """

class DMX_TX:
    """ Interface to a DMX universe for sending using a PIO module.
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
    """

    def __init__(self, pin, universe_size=512, statemachine=0, dmachannel=0):
        """ Initialisation of the DMX controller PIO statemachine and DMA channel

        Args:
            pin (numeric):                  Pin number to use
            universe_size (int, optional):  Size of the DMX universe to interface to. Defaults to 512.
            statemachine (int, optional):   Which PIO statemachine should be used. Defaults to 0.
            dmachannel (int, optional):     Which DMA channel should be used. Defaults to 0.

        Raises:
            ValueError: Any invalid parameters are reported as exceptions
        """
        if universe_size < 1 or universe_size > 512:
            raise ValueError("DMX universes must have 1...512 channels")
        
        self.channels       = bytearray([0 for _ in range(universe_size+1)]) # +1 because DMX-0 is the start code, with channels 1-512 behind it

        self._pin           = Pin(pin, Pin.OUT, Pin.PULL_UP)
        self._sm            = rp2.StateMachine(statemachine, dmx_out, freq=1_000_000, sideset_base=self._pin, out_base=self._pin)
        self._dma           = dma.DmaChannel(dmachannel)

        # Set up the DMA controller
        self._dma.NoWriteIncr()
        self._dma.SetTREQ(0) # TODO - hard coded as PIO0 TX0

    def __del__(self):
        # TODO - tidy up the state machine and DMA channels
        pass
        
    #def __repr__(self):
        # TODO - encode the class state - including which PIO and DMA channel are in use
        pass

    def __str__(self):
        for chan in range(len(self.channels)):
            if chan % 20 == 1:
                result += f"\n{chan:03}:"                      # Start a new line with the channel number every 20 lines
            
            if chan % 5 == 1:
                result += "  "                                 # Put spaces into the line every five channels
            
            if chan == 0:
                result = f"Start code: {self.channels[chan]}"  # The start code ("channel zero") is formatted differently
            else:
                result += f" {self.channels[chan]:3}"
            
            if chan % 100 == 0:                                # Blank line every 100 channels
                result += "\n"
        
        result += "\n"
        return result
    
    def pause(self):
        self.t.deinit()
        self._sm.active(0)

    def restart(self, t):
        self._sm.active(1)
        self._sm.restart()
        self._dma.SetChannelData(addressof(self.channels), 0x50200010, len(self.channels), True) # TODO Hard coded as PIO0 for now

    def start(self):
        self.t = Timer(period=50, callback=self.restart) # TODO make the period configurable

class DMX_RX:
    """
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

    def __init__(self, pin, statemachine=4, dmachannel=1):
        """ Initialisation of the DMX controller

        Args:
            pin (numeric):                  Pin number to use
            direction (TX or RX, optional): Is this a DMX transmitter or receiver? Defaults to RX.
            statemachine (int, optional):   Which PIO statemachine should be used. Defaults to 4.
            dmachannel (int, optional):     Which DMA channel should be used. Defaults to 1.

        Raises:
            ValueError: Any invalid parameters are reported as exceptions
        """
        self.channels   = bytearray([0 for _ in range(513)]) # DMX-0 is the start code, with channels 1-512 behind it
        
        self._pin       = Pin(pin, Pin.IN)
        self._debugpin  = Pin(15, Pin.OUT)

        self._sm = rp2.StateMachine(statemachine, dmx_in, freq=1_000_000,in_base=self._pin, jmp_pin=self._pin, sideset_base=self._debugpin)
        #self._sm = rp2.StateMachine(statemachine, dmx_in, freq=1_000_000,in_base=self._pin, jmp_pin=self._pin)
        self._sm.irq(handler=self.IRQ_from_PIO)
        self.irq_count = 0
        
        self._dma = dma.DmaChannel(dmachannel)
        self._dma.NoReadIncr()
        self._dma.SetTREQ(12) # TODO - hard coded as PIO4 TX for the moment

    def __del__(self):
        # TODO - tidy up the state machine and DMA channels
        pass
        
    def __repr__(self):
        # TODO - encode the class state - including which PIO and DMA channel are in use
        pass

    def __str__(self):
        for chan in range(len(self.channels)):
            if chan % 20 == 1:
                result += f"\n{chan:03}:"                      # Start a new line with the channel number every 20 lines
            
            if chan % 5 == 1:
                result += "  "                                 # Put spaces into the line every five channels
            
            if chan == 0:
                result = f"Start code: {self.channels[chan]}"  # The start code ("channel zero") is formatted differently
            else:
                result += f" {self.channels[chan]:3}"
            
            if chan % 100 == 0:                                # Blank line every 100 channels
                result += "\n"
        
        result += "\n"
        return result
    
    def pause(self):
        self._sm.active(0)

    def IRQ_from_PIO(self, sm):
        self._dma.SetChannelData(0x50300023, addressof(self.channels), len(self.channels), True) # TODO Hard coded as PIO4 RX
        self.irq_count += 1

    def start(self):
        self._dma.SetChannelData(0x50300023, addressof(self.channels), len(self.channels), True) # TODO Hard coded as PIO4 RX
        self._sm.restart()
        self._sm.active(1)

        #for chan in range(len(self.channels)):
        #    self.channels[chan] = self._sm.get()

def test():
    dmx_out = DMX_TX(3, 20)
    dmx_out.start()

    dmx_out.channels[1]   = 85
    dmx_out.channels[2]   = 0b0111_1111 # Should be L4us  H28us L4us  H8us
    dmx_out.channels[3]   = 0b0011_1110 # Should be L8us  H20us L8us  H8us
    dmx_out.channels[4]   = 0b0001_1100 # Should be L12us H12us L12us H8us
    dmx_out.channels[5]   = 0b0000_0001 # Should be L4us  H4us  L28us H8us
    dmx_out.channels[6]   = 0b1000_0011 # Should be L4us  H8us  L20us H12us
    dmx_out.channels[7]   = 0b1100_0111 # Should be L4us  H12us L12us H16us
    dmx_out.channels[8]   = 0b1110_1111
    dmx_out.channels[10]  = 170
    dmx_out.channels[12]  = 85
    dmx_out.channels[16]  = 250
    dmx_out.channels[17]  = 251
    dmx_out.channels[18]  = 252
    dmx_out.channels[19]  = 253
    dmx_out.channels[20]  = 85
    #dmx_out.channels[512] = 85
 
    #print(dmx_out)

    # Something should be being sent by now - let's see if we can receive it!
    dmx_in  = DMX_RX(7)
    dmx_in.start()

    last_irq_count = dmx_in.irq_count
    for n in range(50):
        dmx_out.channels[1] += 1
        print(f"{dmx_out.channels[1]}:{dmx_in.channels[1]}...", end="")
        time.sleep_ms(400)
        irq_count = dmx_in.irq_count
        print(f"{dmx_in.channels[1]} IRQ {irq_count - last_irq_count}...")
        last_irq_count = irq_count
        
    #for n in range(256):
    #    dmx_out.send(1,n)
    #    time.sleep_ms(200)
    
    #d.pause()