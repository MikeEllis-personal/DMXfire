# DMX Controlled lighting effect

A simple DMX controlled lighting effect, capable of simulating firelight, a strobe, or a lightning effect using an array of WS2812 RGB LEDs.

A lot of the hard work is based upon information gleaned from

* Pico DMX in C++ with PIO and DMA: https://github.com/jostlowe/Pico-DMX
* The Pico MicroPython SDK: https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf
* RP2 MicroPython documentation: https://docs.micropython.org/en/latest/library/rp2.html
* RP2040 datasheet: https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf

* PIO and DMA: https://pythonrepo.com/repo/benevpi-RP2040_micropython_dma-python-programming-with-hardware or https://github.com/benevpi/RP2040_micropython_dma?ref=pythonrepo.com
* Micropython forum discussions:
  * https://forum.micropython.org/viewtopic.php?f=21&t=10717
  * https://forum.micropython.org/viewtopic.php?f=21&t=9697
* Instructibles articles: https://www.instructables.com/Arbitrary-Wave-Generator-With-the-Raspberry-Pi-Pic/


# DMX control

Channel 1: Brightness
Channel 2: Speed
Channel 3: Effect
* 0-63: Off
* 64-127: Firelight
* 128-191: Strobe
* 192-255: Lightning

# dmx.py
This class provides a simpe interface to a DMX universe for reading or writing using a PIO module.

### DMX basics
DMX data frames comprise a long (176us) "break" as a logic low, followed by a 16us "MarkAfterBreak" as a logic high, then a series of bytes in 8N2 MSB-first format at 4us/bit. Each data frame is known as a Universe and comprises a single-byte Start Code (0 for DMX) followed by between 1 and 512 data bytes, one byte per lighting channel.

### Transmission
A DMA channel is set up to copy a bytearray (address automatically incrementing on each transfer) into the PIO FIFO (at a fixed address). When this transfer completes, the DMA channel raises an interrupt and the handler resets both the PIO and the DMA channel. When restarted, the PIO first ensures that the DMX "break" is sent, then the MarkAfterBreak, before streaming out the bytes as sent by the DMA into its FIFO. As the PIO completes each byte, a Data Request (DREQ) interrupt is raised to start the next DMA transfer. The need to send the Break and MAB by resetting the PIO are the reason we can't just chain two DMA channels together where the second channel simply reloads the first.

1. PIO sends Break and half of the MAB - the second half of the MAB comes from the stop bits which are sent next
1. PIO then pulls data from the DMA, triggering a DREQ, and sends the stop bits (8us), the start bit (4us), then 8 data bits. 
1. Upon receipt of the DREQ, DMA sends the next byte to the PIO input FIFO
1. When the entire Universe has been DMA'd, the DMA raises a processor interrupt
1. When the DMA interrupt is received, the processor resets the PIO and restarts the DMA 

TODO: Need to make sure that the last few values aren't lost in the FIFO before the PIO has chance to send them

### Reception
A PIO is constantly watching the DMX input pin. Once a valid Break and MarkAfterBreak are observed, subsequent 8N2 bytes are passed to the PIO FIFO which is read by the DMA channel and copied into the bytearray.

1. The PIO waits for a very long run of zeros (176us or more - Break)
1. The PIO waits for a one (any length - MAB) - there is no check that this is the correct length (16us)
1. The PIO waits for a zero (start bit) and starts to sample the data ~6us later - the start bit should be 4us long
1. The PIO captures 8 bits, one every 4us, and shifts these into the ISR
1. The PIO waits for a one (stop bit), and sends the ISR to the DMA
1. The PIO then loops back to step 3 - there is no check that the stop bit is the correct length (8us)
1. The DMA accepts the byte from the PIO and stores it in memory
1. When the DMA has accepted the correct number of bytes, it triggers a processor interrupt
1. When the DMA interrupt is received, the processors resets the PIO and restarts the DMA

### Class basics
Put simply, the class sets up the DMA and PIO and then provides a convenient interface to the bytearray used by the DMA controller. Setting or reading individual channels is permitted, as is reading/writing the entire Universe. When used as a transmitter, the class uses DMA and PIO to repeatedly send the universe. When used as a receiver, each received universe is copied and made available to the user as soon as it is received.

### DMA Channel and PIO allocations
It is not possible to check the hardware to see if a DMA channel or PIO statemachine is already in use. No extra locking has been added in this software, thus clashes need to be avoided by the user code.

# dma.py
The Pico port of Micropython doesn't include a DMA controller, hence a very limited one is created using Viper to access memory mapped registers.