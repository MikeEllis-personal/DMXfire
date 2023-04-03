#type: ignore

import rp2

@rp2.asm_pio(sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_HIGH),
             in_shiftdir=rp2.PIO.SHIFT_RIGHT, 
             autopush=False)
def dmx_in():
    # Two sideset pins are used for debugging:
    #     Side(0) - "Idle"
    #     Side(1) - Receiving a data bit
    #     Side(2) - Checking length of BREAK - set to zero as soon as minimum BREAK length exceeded

    # Read the expected frame length into the OSR - later loaded into the Y scratch register
    # This is only read once and re-used over and over and over again
    pull()
    # Look for the BREAK - minimum 90us (29 loops at 3us/loop + 5 instructions) low time
    label("break_reset") 
    set(x, 29)                    .side(3)                 # DEBUG - Mark Before Break / Interframe spacing 
    
    label("break_loop") 
    # Restart the (full) time if pin goes high during the (suspected) break - some sort of framing error
    jmp(pin, "break_reset")                      [1]       
    jmp(x_dec, "break_loop")      .side(2)                 # DEBUG - Found a BREAK

    # BREAK (low) minimum length exceeded - definitely a start of frame. 

    # Load the expected frame length
    mov(y, osr)                   .side(0)                 # DEBUG - minimum BREAK exceeded - waiting for MAB

    # Stall until pin goes high for the Mark-After-Break (MAB) 
    wait(1, pin, 0) 
    # TODO - minimum MAB value is 12us, not checked. Just 1us would be enough to qualify.

    # Now we just need a simple 8N2 UART
    label("get_next_byte")
          
    # Stall until the Start bit (low) is detected
    wait(0, pin, 0)                              [2] 
    
    # Load the bit counter (expecting 8 bits) then delay 6us (wait + set + 2 + 2 delay) until halfway through the first bit
    set(x, 7)                                    [2] 

    # Read 8 data bits - each loop iteration is 4us (in + jmp + 2 delay)
    label("bitloop") 
    in_(pins, 1)                  .side(1)                 # DEBUG - reading a data byte
    jmp(x_dec, "bitloop")                        [2] 

    # What happened after the 8 data bits? If PIN is high, we got the STOP bit we needed 
    jmp(pin, "got_stopbit") 
    
    # PIN stayed low - looks like the start of a BREAK - raise IRQ to tell the processor to reset the DMA channel
    irq(rel(0)) 

    # There is an annoying race condition here - if the BREAK being received is close to the minimum length, the 
    # processor may not have serviced the interrupt and reset the DMA channel before the next frame starts, causing
    # corruption in the data received
    
    # Already had 44us of the BREAK - go and wait for the rest of the it
    set(x, 15)
    jmp("break_loop") 

    # STOP bit received when expected - pass the byte to the DMA handler: DMA will read a byte from +3, so no need to shift
    label("got_stopbit") 
    push(noblock)                 .side(0)                 # DEBUG - got a byte

    # If we've not received all the bytes we're expecting, go back and wait for some more
    jmp(y_dec, "get_next_byte")  

    # Full frame received - tell the processor (interrupt) and set up for the next one right now
    irq(rel(0))
    jmp("break_reset")


@staticmethod
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_HIGH, 
             autopull=False, 
             out_init=rp2.PIO.OUT_HIGH, 
             out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def dmx_out():
    # Stall with line IDLE until the DMA transfer begins
    pull()                  .side(1)         
    
    # Assert BREAK for 176us (=22*(1+7)us)
    set(x, 21)              .side(0)         
    
    label("breakloop")                         
    jmp(x_dec, "breakloop")             [7]    
    
    # Assert MAB. 1+7+1+7 cycles = 16us
    nop()                   .side(1)    [7]  
    nop()                               [7]   
    
    # Send data frame - OSR already has the first byte in it from earlier PULL
    wrap_target()                            
    
    # Send START bit (4us) and load the bit counter
    set(x, 7)               .side(0)    [3]  
    
    # Shift 8 bits (4us/bit) from OSR to the line
    label("bitloop")                          
    out(pins, 1)                             
    jmp(x_dec, "bitloop")               [2]

    # Send 2 STOP bits (8us), or stall with line in idle state
    pull()                  .side(1)    [7]  
    wrap()                                    
