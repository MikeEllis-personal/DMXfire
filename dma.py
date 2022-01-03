class DmaChannel:
    def __init__(self, channelNumber):
        offset = channelNumber * 0x40
        self.ChannelNumber = channelNumber
        self.ReadRegister = 0x50000000 + offset
        self.WriteRegister = 0x50000004 + offset
        self.TransferCountRegister = 0x50000008 + offset
        self.TriggerControlRegister = 0x5000000C + offset
        self.ControlRegister = 0x50000010 + offset
        self.ControlValue = 0x3F8033 + (channelNumber << 11) #so that the chain value is set to itself
        
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
        
    @micropython.viper
    def SetChannelData(self, readAddress : uint , writeAddress : uint, count: uint, trigger : bool):
        ptr= ptr32(self.ReadRegister)
        ptr2= ptr32(self.WriteRegister)
        ptr3= ptr32(self.TransferCountRegister)
        ptr[0] = readAddress
        ptr2[0] = writeAddress
        ptr3[0] = count
        if trigger:
            ptr4= ptr32(self.TriggerControlRegister)
            ptr4[0] = uint(self.ControlValue)
