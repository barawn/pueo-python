from ..common.bf import bf
from ..common.dev_submod import dev_submod
from ..common.uspeyescan import USPEyeScan

from enum import Enum
from functools import partial
import time

# Module structure (referenced from base)
# 0x0000 - 0x3FFF : Control/status space
# 0x4000 - 0x4FFF : DRP 0
# 0x5000 - 0x5FFF : DRP 1
# 0x6000 - 0x6FFF : DRP 2
# 0x7000 - 0x7FFF : DRP 3
#
# The control/status space is further split as:
# 0x0000 - 0x07FF : Aurora 0
# 0x0800 - 0x0FFF : Aurora 1
# 0x1000 - 0x17FF : Aurora 2
# 0x1800 - 0x1FFF : Aurora 3
# 0x2000 - 0x3FFF : GT Common

class PueoTURFAurora(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.scanner = []
        for i in range(4):
            # partials are more appropriate than lambdas and avoid
            # scoping issues in a loop.
            self.scanner.append( USPEyeScan(partial(self.drpread, i),
                                            partial(self.drpwrite, i),
                                            partial(self.eyescanreset, i),
                                            partial(self.up, i),
                                            name="TURFIO"+str(i)))
            
    def enableEyeScan(self, waittime=1):
        enableWasNeeded = False
        """ Enable eye scanning on all links. Will skip over non-up links. """
        for s in self.scanner:
            if s.enable:
                s.enable = True
                enableWasNeeded = True
        if not enableWasNeeded:
            return
        self.reset()
        # It takes a while for the link to come back up.
        time.sleep(waittime)
        for s in self.scanner:
            s.setup()
            
    def linkstat(self, linkno, verbose=False):
        rv = self.read(0x800*linkno + 0x4)
        if verbose:
            r = bf(rv)
            print(f'BUFG_GT in Reset: {r[11]}')
            print(f'Frame Err: {r[10]}')
            print(f'Soft Err: {r[9]}')
            print(f'System in Reset: {r[7]}')
            print(f'Link in Reset: {r[6]}')
            print(f'RX Reset Done: {r[5]}')
            print(f'TX Reset Done: {r[4]}')
            print(f'TX Locked: {r[3]}')
            print(f'GT Power Good: {r[2]}')
            print(f'Channel Up: {r[1]}')
            print(f'Lane Up: {r[0]}')
        return rv

    def up(self, linkno):
        return self.linkstat(linkno) & 0x1
    
    def eyescanreset(self, linkno, onoff):
        rv = bf(self.read(0x800*linkno))
        rv[2] = 1 if onoff else 0
        self.write(0x800*linkno, int(rv))
    
    def reset(self):
        rv = bf(self.read(0x2000))
        rv[0] = 1
        self.write(0x2000, int(rv))
        rv[0] = 0
        self.write(0x2000, int(rv))

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
    
