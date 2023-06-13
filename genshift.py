from bf import bf
from enum import Enum

class GenShift:
    map = { 'MODCONF' : 0x0,
            'DEVCONF' : 0x4,
            'DATA'    : 0x8 }

    class GpioState(Enum):
        GPIO_HIGH = 'GPIO Out High'
        GPIO_LOW = 'GPIO Out Low'
        GPIO_TRI = 'GPIO Tristate'

    # this only applies to data, not aux
    class BitOrder(Enum):
        LSB_FIRST = 0
        MSB_FIRST = 1
        
    def __init__(self, dev, base):
        self.dev = dev
        self.base = base

    def write(self, addr, data):
        return self.dev.write(self.base+addr, data)

    def read(self, addr):
        return self.dev.read(self.base+addr)

    # disableTris forces specified interfaces to remain driven
    def setup(self, disableTris=0x0):
        modconf = bf(0)
        modconf[7:0] = 0
        modconf[15:8] = disableTris
        self.write(self.map['MODCONF'], int(modconf))

    def enable(self, interfaceNumber, prescale=0):
        modconf = bf(self.read(self.map['MODCONF']))
        modconf[7:0] = prescale
        self.write(self.map['MODCONF'], int(modconf))
        devconf = bf(self.read(self.map['DEVCONF']))
        devconf[7:0] = (1<<interfaceNumber)
        self.write(self.map['DEVCONF'], int(devconf))

    def disable(self):
        devconf = bf(self.read(self.map['DEVCONF']))
        devconf[7:0] = 0
        self.write(self.map['DEVCONF'], int(devconf))
        
    def shift(self, val, auxVal=0, bitOrder=BitOrder.LSB_FIRST, numBits=8):
        dat = bf(0)
        dat[26:24] = numBits-1
        dat[15:8] = auxVal
        dat[7:0] = val
        dat[30] = 1
        dat[29] = bitOrder.value
        
        self.write(self.map['DATA'], int(dat))
        ntries = 0
        dat[31:0] = self.read(self.map['DATA'])
        while (dat[31] == 1 and ntries < 100):
            dat[31:0] = self.read(self.map['DATA'])
            ntries += 1
        if ntries == 100:
            print("Sequence did not complete?!?")
            return 0
        return dat[23:16]
        
    def gpio(self, num, state):
        devconf = bf(self.read(self.map['DEVCONF']))
        
        if state == self.GpioState.GPIO_LOW:
            devconf[8+num] = 0
            devconf[24+num] = 0
            self.write(self.map['DEVCONF'], int(devconf))
            return 0
        elif state == self.GpioState.GPIO_HIGH:
            devconf[8+num] = 0
            devconf[24+num] = 1
            self.write(self.map['DEVCONF'], int(devconf))
            return 1
        elif state == self.GpioState.GPIO_TRI:
            if devconf[8+num] == 1:
                # already set
                return devconf[16+num]
            else:
                self.write(self.map['DEVCONF'], int(devconf))
                devconf[31:0] = self.read(self.map['DEVCONF'])
                return devconf[16+num]
    
            
