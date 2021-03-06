# Constants for the various Transfer REQuest sources
TREQ_PIO0_TX    = 0
TREQ_PIO1_TX    = 1
TREQ_PIO2_TX    = 2
TREQ_PIO3_TX    = 3
TREQ_PIO4_TX    = 8
TREQ_PIO5_TX    = 9
TREQ_PIO6_TX    = 10
TREQ_PIO7_TX    = 11

TREQ_PIO0_RX    = 4
TREQ_PIO1_RX    = 5
TREQ_PIO2_RX    = 6
TREQ_PIO3_RX    = 7
TREQ_PIO4_RX    = 12
TREQ_PIO5_RX    = 13
TREQ_PIO6_RX    = 14
TREQ_PIO7_RX    = 15

TREQ_SPI0_TX    = 16
TREQ_SPI0_RX    = 17
TREQ_SPI1_TX    = 18
TREQ_SPI1_RX    = 19

TREQ_UART0_TX   = 20
TREQ_UART0_RX   = 21
TREQ_UART1_TX   = 22
TREQ_UART1_RX   = 23

TREQ_PWM0       = 24
TREQ_PWM1       = 25
TREQ_PWM2       = 26
TREQ_PWM3       = 27
TREQ_PWM4       = 28
TREQ_PWM5       = 29
TREQ_PWM6       = 30
TREQ_PWM7       = 31

TREQ_I2C0_TX    = 32
TREQ_I2C0_RX    = 33
TREQ_I2C1_TX    = 34
TREQ_I2C1_RX    = 35

TREQ_ADC        = 36
TREQ_XIP_STREAM = 37
TREQ_XIP_SSITX  = 38
TREQ_XIP_SSIRX  = 39

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
        ptr = ptr32(self.WriteRegister)
        ptr[0] = address
        #self.WriteAddress = address
        
    @micropython.viper
    def SetReadAddress(self, address: uint):
        ptr = ptr32(self.ReadRegister)
        ptr[0] = address
        #self.ReadAddress = address
        
    @micropython.viper
    def SetTransferCount(self, count: uint):
        ptr = ptr32(self.TransferCountRegister)
        ptr[0] = count
        #self.TransferCount = count
        
    @micropython.viper
    def SetControlRegister(self, controlValue: uint):
        ptr = ptr32(self.ControlRegister)
        ptr[0] = controlValue
        self.ControlValue = controlValue
        
    @micropython.viper
    def SetTriggerControlRegister(self, controlValue: uint):
        ptr = ptr32(self.TriggerControlRegister)
        ptr[0] = controlValue
        self.ControlValue = controlValue
    
    @micropython.viper
    def TriggerChannel(self):
        ptr= ptr32(self.TriggerControlRegister)
        ptr[0] = uint(self.ControlValue)
        
    def SetChainTo(self, chainNumber : uint):
        self.ControlValue  &= ~ 0x7800
        self.ControlValue |= (chainNumber <<11)
        
    def SetByteTransfer(self):
        self.ControlValue  &= ~ 0xC
        
    def SetHalfWordTransfer(self):
        self.ControlValue  &= ~ 0xC
        self.ControlValue |= 0x4
        
    def SetWordTransfer(self):
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

        if trigger:
            ctrl_ptr    = ptr32(self.TriggerControlRegister)
            ctrl_ptr[0] = uint(self.ControlValue)
