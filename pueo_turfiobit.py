# This class is used IN THE TURF because it's
# AN INPUT BIT from a TURFIO

from enum import Enum
from bf import bf
from dev_submod import dev_submod
import time
import pueo_utils

# Each TURFIO input bit has an 8-bit address space.
# It's partitioned up to make the logic easier: anything
# in the top half accesses data in a different clock domain.
# So things might seem organized a bit weird.
class PueoTURFIOBit(dev_submod):

    map = { 'BITCTRL' : 0x0,   # overall control register
            'BITERR' : 0x4,    # bit error count
            'PDLYCNTA' : 0x80, # primary delay count A (first delay val)
            'PDLYCNTB' : 0x84, # primary delay count B (second delay val)
            'MDLYCNTA' : 0x88, # monitor delay count A (first delay val)
            'MDLYCNTB' : 0x8C, # monitor delay count B (second delay val)
            'BITSLIP' : 0xC0,  # capture and bitslip register
            'INTERVAL' : 0xE0  # bit error interval count
            }
        
    def __init__(self, dev, base):
        super().__init__(dev, base)

    # So dumb.
    # Each eye is fundamentally 2 ns wide. We only have a total "guaranteed
    # max" delay of around 2.2 ns so we *stupidly* need to do the whole thing.
    # We have a *total* range of 1022 but a *functional* range of
    # less than that because of the Align_Delay.
    # The way that *we* do the eyescan is different than at the TURFIO
    # because we've got finer steps.
    # So, for instance, if we discover the eye transition at
    # "562", to center the data, we determine the Align_Delay
    # and the ps_per_tap and then we step back or forward 1 ns.
    # We ALSO fundamentally want to stay the HELL away from the Align_Delay
    # because of Xilinx's weirdo warning. Whatever.
    # So we use the IDELAY as the *base* delay.
    # So if we measure (as an example):
    # eye transition: 562
    # Align_Delay: 58 
    # ps_per_tap: 3.097
    # Then we want to move back to 239 taps. Because 239 is less than 511,
    # we set PDLYCNTA = 239
    #        PDLYCNTB = 0

    # coarse eye scan
    def coarse_eyescan(self):
        Align_Delay, ps_per_tap = self.getParameters()
        # Because the eyes are so wide open, finding
        # the transition point is tough. So we do a very coarse
        # scan first in 200 ps steps (11 total, over a full eye)
        # set the error count interval (~1 millisecond)
        self.write(self.map['INTERVAL'], 131072)
        # What we're looking for is a change in the bit number.
        # Just do the scan first
        sc = []
        for i in range(11):
            bitno = None
            self.setDelay(200.0*i, Align_Delay, ps_per_tap)
            time.sleep(0.002)
            errcnt = self.read(self.map['BITERR'])
            if errcnt == 0:
                val = self.read(self.map['BITSLIP'])
                bitno = pueo_utils.check_eye(val)
                if bitno is not None:
                    bitno = bitno % 4
                sc.append((i, errcnt, bitno))
            else:
                sc.append((i, errcnt, None))
        return sc

    def getParameters(self):
        # The monitor delay is "close enough" to the
        # cell above it that we can use it as the basis.
        # MDLYCNTA is Align_Delay + (700.0/ps_per_tap)
        # MDLYCNTB is (700.0/ps_per_tap)        
        madly = self.read(self.map['MDLYCNTA'])
        mbdly = self.read(self.map['MDLYCNTB'])
        return (madly-mbdly, 700.0/mbdly)

    # target here is in **time**
    def setDelay(self, target, Align_Delay = None, ps_per_tap = None):
        if Align_Delay is None or ps_per_tap is None:
            Align_Delay, ps_per_tap = self.getParameters()
        # ok now figure out how to distribute this stuff
        totdly = round(target/ps_per_tap) + Align_Delay
        pdlya = totdly
        pdlyb = 0
        if pdlya > 511:
            pdlyb = pdlya-511
            pdlya = 511
                        
        # disable VTC
        self.write(self.map['BITCTRL'], 2)
        self.write(self.map['PDLYCNTA'], pdlya)
        while self.read(self.map['PDLYCNTA']) != pdlya:
            pass
        self.write(self.map['PDLYCNTB'], pdlyb)
        while self.read(self.map['PDLYCNTB']) != pdlyb:
            pass
        
        # enable VTC
        self.write(self.map['BITCTRL'], 0)
            
