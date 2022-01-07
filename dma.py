class DmaChannel:
    def __init__(self, channelNumber):
        offset = channelNumber * 0x40

        self.ChannelNumber          = channelNumber
        self.ReadRegister           = 0x50000000 + offset
        self.WriteRegister          = 0x50000004 + offset
        self.TransferCountRegister  = 0x50000008 + offset
        self.TriggerControlRegister = 0x5000000C + offset
        self.ControlRegister        = 0x50000010 + offset

        self.ControlValue = 0x003F8033 + (channelNumber << 11) # Enable, Hi-priority, Bytes, no chain-to, increment both read and write, no IRQs, no ring
        # Bit 31302928 27262524 23222120 19181716 15141312 11100908 07060504 03020100          
        # Val  0 0 0 0  0 0 0 0  0 0 1 1  1 1 1 1  1 X X X  X 0 0 0  0 0 1 1  0 0 1 1  <-------+-- 0x00 3F 80 33
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | |          V
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | +-    00: (1)    Enable        
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | +---    01: (1)    High priority    
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  +-+----- 03-02: (0)    Data size        - Byte (0), Halfword (1), Word (2)   
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | | +----------    04: (1)    Read increment   - No increment (0) or Auto increment (1)
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | | +------------    05: (1)    Write increment  - No increment (0) or Auto increment (1)
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | | |  | |
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | | +-+--+-+-------------- 09-06: (0)    Ring size        - Ring size of 2^value (0 => no wrap, 1=>2, 2=>4, 3=>8, ..., 15=>32768)
        #      | | | |  | | | |  | | | |  | | | |  | | | |  | +-----------------------    10: (0)    Ring select      - 0=>read-ring, 1=>write-ring
        #      | | | |  | | | |  | | | |  | | | |  | | | |  |
        #      | | | |  | | | |  | | | |  | | | |  | +-+-+--+------------------------- 14-11: (chan) CHAIN_TO         - Set to this DMA channel => no chain-to
        #      | | | |  | | | |  | | | |  | | | |  | 
        #      | | | |  | | | |  | | | +--+-+-+-+--+---------------------------------- 20-15: (0x3f) Transfer Request - 0x00-0x3a = DReq, 0x3b-0x3e Timers 0-3, 0x3f Unpaced
        #      | | | |  | | | |  | | | 
        #      | | | |  | | | |  | | +------------------------------------------------    21: (1)    IRQ_QUIET        - Disable end-of-block IRQ
        #      | | | |  | | | |  | +--------------------------------------------------    22: (0)    BSWAP            - No byte swapping
        #      | | | |  | | | |  +----------------------------------------------------    23: (0)    SNIFF_EN         - Debug sniffing disabled
        #      | | | |  | | | +-------------------------------------------------------    24: (0)    BUSY             - Read only
        #      | | | +--+-+-+--------------------------------------------------------- 28-25: (0)    Reserved
        #      | | +------------------------------------------------------------------    29: (0)    WRITE_ERROR      - Not cleared
        #      | +--------------------------------------------------------------------    30: (0)    READ_ERROR       - Not cleared
        #      +----------------------------------------------------------------------    31: (0)    AHB_ERROR        - Read only

    @micropython.viper
    def SetWriteAddress(self, address: uint):
        ptr= ptr32(self.WriteRegister)
        ptr[0] = address
        #self.WriteAddress = address
        
    @micropython.viper
    def SetReadAddress(self, address: uint):
        ptr= ptr32(self.ReadRegister)
        ptr[0] = address
        #self.ReadAddress = address
        
    @micropython.viper
    def SetTransferCount(self, count: uint):
        ptr= ptr32(self.TransferCountRegister)
        ptr[0] = count
        #self.TransferCount = count
        
    @micropython.viper
    def SetControlRegister(self, controlValue: uint):
        ptr= ptr32(self.ControlRegister)
        ptr[0] = controlValue
        self.ControlValue = controlValue
        
    @micropython.viper
    def SetTriggerControlRegister(self, controlValue: uint):
        ptr= ptr32(self.TriggerControlRegister)
        ptr[0] = controlValue
        self.ControlValue = controlValue
    
    @micropython.viper
    def TriggerChannel(self):
        rd_ptr = ptr32(self.ReadRegister)
        wr_ptr = ptr32(self.WriteRegister)
        tc_ptr = ptr32(self.TransferCountRegister)

        print(f"Trigger  Read: 0x{rd_ptr[0]:08x} Write: 0x{wr_ptr[0]:08x} Count: {tc_ptr[0]} Control: 0x{self.ControlValue:08x}")
        ptr= ptr32(self.TriggerControlRegister)
        ptr[0] = uint(self.ControlValue)
        
    #@micropython.viper
    def SetChainTo(self, chainNumber : uint):
        self.ControlValue  &= ~ 0x7800
        self.ControlValue |= (chainNumber <<11)
        #ptr= ptr32(self.ControlRegister)
        #ptr[0] =  uint(self.controlValue)
        
    def SetByteTransfer(self):
        self.ControlValue  &= ~ 0xC
        
    def SetHalfWordTransfer(self):
        self.ControlValue  &= ~ 0xC
        self.ControlValue |= 0x4
        
    def SetWordTransfer(self):
        #self.ControlValue  &= ~ 0xC
        self.ControlValue |= 0xC
    
    def SetReadIncr(self):
        # Read address increments when bit 4 of the control value is set
        self.ControlValue = self.ControlValue | (1<<4)

    def NoReadIncr(self):
        # Read address does not increment when bit 4 of the control value is clear
        self.ControlValue = self.ControlValue & ~ (1<<4)

    def SetWriteIncr(self):
        # Write address increments when bit 5 of the control value is set
        self.ControlValue = self.ControlValue | (1<<5)

    def NoWriteIncr(self):
        # Write address does not increment when bit 5 of the control value is clear
        self.ControlValue = self.ControlValue & ~ (1<<5)

    def SetTREQ(self, value):
        # Set the TReq source to the given value (bits 15-20 of the control word)
        self.ControlValue = (self.ControlValue & ~ (0x3f << 15)) | ((value & 0x3f) << 15)

    @micropython.viper
    def SetChannelData(self, readAddress : uint , writeAddress : uint, count: uint, trigger : bool):
        #print(f"Setup... Read: 0x{readAddress:08x} Write: 0x{writeAddress:08x} Count: {count}")

        # Disable the DMA channel first
        control = ptr32(self.ControlRegister)
        control[0] = 0

        # Set up the required values
        rd_ptr = ptr32(self.ReadRegister)
        wr_ptr = ptr32(self.WriteRegister)
        tc_ptr = ptr32(self.TransferCountRegister)

        rd_ptr[0] = readAddress
        wr_ptr[0] = writeAddress
        tc_ptr[0] = count

        #print(f"Readback Read: 0x{rd_ptr[0]:08x} Write: 0x{wr_ptr[0]:08x} Count: {tc_ptr[0]}")

        if trigger:
            ctrl_ptr    = ptr32(self.TriggerControlRegister)
            ctrl_ptr[0] = uint(self.ControlValue)
            #print(f"Triggered with CTRL word 0x{self.ControlValue:08x}")

        u_ptr = ptr8(readAddress)
        #print(f"Data from 0x{readAddress:08x}: {u_ptr[0]: 3} {u_ptr[1]: 3} {u_ptr[2]: 3} {u_ptr[3]: 3} {u_ptr[4]: 3} {u_ptr[5]: 3} {u_ptr[6]: 3} {u_ptr[7]: 3}")
