from ..common.bf import bf
from ..common.dev_submod import dev_submod

# implements the SURFTURF class
# right now just debugging + rxclk enabling
class SURFTURF(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)

    def mark(self):
        rv = bf(self.read(0x0))
        rv[8] = 1
        self.write(0x0, int(rv))
        rv = bf(self.read(0x0))
        while rv[8]:
            rv = bf(self.read(0x0))

    # need to add runmode/trigger
            
    def fwupd(self, val):
        self.write(0x4, val)

    def rxclk(self, enable):
        rv = bf(self.read(0x0))
        if enable:
            rv[31] = 0
        else:
            rv[31] = 1
        self.write(0x0, int(rv))
