from ..common.bf import bf
from ..common.dev_submod import dev_submod
from ..common.uspeyescan import USPEyeScan

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
        self.scanner = []
        for i in range(4):
            self.scanner.append( USPEyeScan(lambda x : self.drpread(i, x),
                                            lambda x, y : self.drpwrite(i, x, y),
                                            lambda x : self.eyescanreset(i, x)) )

    def enableEyeScan(self):
        for s in self.scanner:
            s.enable(True)
        self.reset()
        for s in self.scanner:
            s.setup()
            
    def linkstat(self, linkno):
        return self.read(0x1000*linkno + 0x4)

    def eyescanreset(self, linkno, onoff):
        rv = bf(self.read(0x1000*linkno))
        rv[2] = 1 if onoff else 0
        self.write(0x1000*linkno, int(rv))
    
    def reset(self):
        rv = bf(self.read(0))
        rv[0] = 1
        self.write(0, int(rv))
        rv[0] = 0
        self.write(0, int(rv))

    def pretty_eyescan(self,
                       linkno,
                       prescale = 9,
                       verts = [ -96, -48, 0, 48, 96 ],
                       horzs = [ -0.375, -0.1875, 0, 0.1875, 0.375 ]):
        # exact numbers don't matter that much
        self.scanner[linkno].prescale = prescale
        sampleScale = self.scanner[linkno].sampleScaleValue()
        def ber(v):
            return (v[0])/((v[1]+0.5)*sampleScale)
        for v in verts:
            for h in horzs:
                self.scanner[linkno].horzoffset = h
                self.scanner[linkno].vertoffset = v
                self.scanner[linkno].start()
                while not self.scanner[linkno].complete():
                    pass
                thisBer = ber(self.scanner[linkno].results())
                # this makes the eye stand out more
                if thisBer:
                    print("%.1e\t" % thisBer, end='')
                else:
                    print(".......\t", end='')

            print("")
        

    # DRP read of drpaddr from Aurora idx aur
    def drpread(self, aur, drpaddr):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.read(addr)

    # DRP write of value to drpaddr at Aurora idx aur
    def drpwrite(self, aur, drpaddr, value):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.write(addr, value)
    
