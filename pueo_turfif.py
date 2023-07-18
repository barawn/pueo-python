from enum import Enum
from bf import bf
from dev_submod import dev_submod
from pueo_turfiobit import PueoTURFIOBit

# This is a single PUEO TURFIO interface.
# Global controls
class PueoTURFIF(dev_submod):
    map = { 'CONTROL' : 0x0
           }
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.bit = []
        for i in range(8):
            self.bit.append(PueoTURFIOBit(dev, base + 0x800 + 0x100*i))

    def train_enable(self, enable):
        rv = bf(self.read(self.map['CONTROL']))
        if enable:
            rv[0] = 1
        else:
            rv[0] = 0
        self.write(self.map['CONTROL'], int(rv))
        
            
