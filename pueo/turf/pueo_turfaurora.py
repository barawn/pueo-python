from ..common.bf import bf
from ..common.dev_submod import dev_submod

from enum import Enum

# Module structure (referenced from base)
# 0x0000 - 0x3FFF : Control/status space
# 0x4000 - 0x4FFF : DRP 0
# 0x5000 - 0x5FFF : DRP 1
# 0x6000 - 0x6FFF : DRP 2
# 0x7000 - 0x7FFF : DRP 3
#
# Because we have this 'mixed' structure
# we just have functions take which Aurora link
# to poke at.

class PueoTURFAurora(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)

    def linkstat(self, linkno):
        return self.read(0x1000*linkno + 0x4)

    # DRP read of drpaddr from Aurora idx aur
    def drpread(self, aur, drpaddr):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.read(addr)

    # DRP write of value to drpaddr at Aurora idx aur
    def drpwrite(self, aur, drpaddr, value):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.write(addr, value)

    # DRP read-modify-write of value to drpaddr given mask at Aurora idx aur
    def drprmw(self, aur, drpaddr, value, mask):
        val = self.drpread(aur, drpaddr)
        val = (val & ~mask) | (value & mask)
        return self.drpwrite(aur, drpaddr, val)
