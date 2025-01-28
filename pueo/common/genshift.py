from .bf import bf
from .dev_submod import dev_submod

from enum import Enum

class GenShift(dev_submod):
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
        super().__init__(dev, base)


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

    # shift in data, and don't care about return value
    def shiftin(self, val, auxVal=0, bitorder=BitOrder.LSB_FIRST, numBits=8):
        dat = self.prepare(val, auxVal, bitOrder, numBits)
        self.write(self.map['DATA'], int(dat))
        return dat

    # shift in and get return value
    def shift(self, val, auxVal=0, bitOrder=BitOrder.LSB_FIRST, numBits=8):
        dat = self.shiftin(val, auxVal, bitOrder, numBits)
        ntries = 0
        dat[31:0] = self.read(self.map['DATA'])
        while (dat[31] == 1 and ntries < 100):
            dat[31:0] = self.read(self.map['DATA'])
            ntries += 1
        if ntries == 100:
            print("Sequence did not complete?!?")
            return 0
        return dat[23:16]

    def prepare(self, val, auxVal, bitOrder, numBits):
        dat = bf(0)
        dat[26:24] = numBits-1
        dat[15:8] = auxVal
        dat[7:0] = val
        dat[30] = 1
        dat[29] = bitOrder.value
        return dat
    
    # shift in a block of data after a single pre-prepped command
    # ignore waits, just assume we're too slow for it to be a problem
    # ignore return data. 
    def blockshiftin(self, prepareVal, data):
        if self.dev.multiwrite is None:
            # sigh, we don't have multiwrite capability
            # so hack it ourselves
            self.write(self.map['DATA'], int(prepareVal))
            dat = bf(prepareVal)
            for b in data:
                dat[7:0] = b
                self.write(self.map['DATA'], int(dat))
        else:
            multiwriteAddr = (self.base + self.map['DATA']) | (1<<22)
            self.write(self.map['DATA'], int(prepareVal))
            self.multiwrite(multiwriteAddr, data)                
    
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
                devconf[8+num] = 1
                self.write(self.map['DEVCONF'], int(devconf))
                devconf[31:0] = self.read(self.map['DEVCONF'])
                return devconf[16+num]
    
class GenShiftGPIO:
    def __init__(self, dev, num):
        self.dev = dev
        self.num = num

    def hiz(self):
        self.dev.gpio(self.num, self.dev.GpioState.GPIO_TRI)

    def hi(self):
        self.dev.gpio(self.num, self.dev.GpioState.GPIO_HIGH)

    def lo(self):
        self.dev.gpio(self.num, self.dev.GpioState.GPIO_LOW)

    def value(self):
        return self.dev.gpio(self.num, self.dev.GpioState.GPIO_TRI)
    
