from ..common.bf import bf
from ..common.dev_submod import dev_submod
from ..common.uspeyescan import USPEyeScan

from enum import Enum
from functools import partial
import time

# Module structure (referenced from base)
# 0x0000 - 0x0FFF : DRP 0
# 0x1000 - 0x1FFF : DRP 1


# DO NOT mess around with this module via the GbE link!!
# This is for pyturfHskd only!!

class PueoTURFGBE(dev_submod):
    """ Combined 10GbE Ethernet core: status + DRP paths """
    map = { 'STAT0' : 0x00,
            'STAT1' : 0x04 }

    def __init__(self, dev, base):
        super().__init__(dev, base)
        # use the factored-out eye scan functions
        self.scanner = []
        for i in range(2):
            # partial is more appropriate here as we're in a loop
            self.scanner.append(USPEyeScan( partial(self.drpread, i),
                                            partial(self.drpwrite, i),
                                            partial(self.eyescanreset, i),
                                            partial(self.up, i),
                                            "10GBE"+str(i)))

    
            
    def enableEyeScan(self, waittime=1):
        if not self.scanner[0].enable or not self.scanner[1].enable:
            """ Enable the eye scan functionality. This WILL reset GBE link!! """        
            self.scanner[0].enable = True
            self.scanner[1].enable = True
            self.reset()
            time.sleep(waittime)
            self.scanner[0].setup()
            self.scanner[1].setup()

    def eyescanreset(self, linkno, onoff):
        rv = bf(self.read(0x4*linkno))
        rv[4] = 1 if onoff else 0
        self.write(0x4*linkno, int(rv))

    def up(self, linkno):
        return self.read(linkno*0x4) & 0x4
        
    def status(self):
        s0 = bf(self.read(0x0))
        s1 = bf(self.read(0x4))
        print("QPLL0 Lock:", s0[1])
        print("SFP0 Block Lock:", s0[2])
        print("SFP0 High BER:", s0[3])
        print("SFP1 Block Lock:", s1[2])
        print("SFP1 High BER:", s1[3])        

    def reset(self):
        rv = bf(self.read(0x0))
        rv[0] = 1
        self.write(0, int(rv))
        rv[0] = 0
        self.write(0, int(rv))    

    def pretty_eyescan(self,
                       linkno,
                       prescale = 9,
                       verts = [ -96, -48, 0, 48, 96 ],
                       horzs = [ -0.375, -0.1875, 0, 0.1875, 0.375 ]):
        res = []
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
                r = self.scanner[linkno].results()
                res.append(r)
                thisBer = ber(r)
                # this makes the eye stand out more
                if thisBer:
                    print("%.1e\t" % thisBer, end='')
                else:
                    print(".......\t", end='')

            print("")
        return res

    # DRP read of drpaddr from GBE idx gbe
    def drpread(self, gbe, drpaddr):
        addr = gbe*(0x1000) + 0x2000 + (drpaddr << 2)
        return self.read(addr)

    # DRP write of value to drpaddr at GBE idx gbe
    def drpwrite(self, gbe, drpaddr, value):
        addr = gbe*(0x1000) + 0x2000 + (drpaddr << 2)
        return self.write(addr, value)
    
