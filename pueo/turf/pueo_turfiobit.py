# This class is used IN THE TURF because it's
# AN INPUT BIT from a TURFIO

from ..common.bf import bf
from ..common.dev_submod import dev_submod
from ..common import pueo_utils

from enum import Enum
import time

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

    # process a coarse eyescan
    @staticmethod
    def process_coarse(scan, verbose=False):
        # A coarse eyescan gives you a list of triplets:
        # index, number of errors, and bit offset #
        # We need to process it to find where the bit changes
        start = None
        stop = None
        curBitno = None
        for val in scan:
            if val[1] == 0 and val[2] is not None:
                # no errors
                if curBitno is None:
                    curBitno = val[2]
                    start = val[0]
                elif val[2] != curBitno:
                    stop = val[0]
                    break
                else:
                    start = val[0]
        if start is not None and stop is not None:
            if verbose:
                print("start is", start, "stop is", stop)
            return (start, stop)
        return None

    # coarse eye scan
    def coarse_eyescan(self):
        Align_Delay, ps_per_tap = self.getParameters()
        # Because the eyes are so wide open, finding
        # the transition point is tough. So we do a very coarse
        # scan first in 200 ps steps (12 total, over a full eye)
        # set the error count interval (~1 millisecond)
        self.write(self.map['INTERVAL'], 131072)
        # What we're looking for is a change in the bit number.
        # Just do the scan first
        sc = []
        # This goes up to the full guaranteed max (2200 ps)
        for i in range(12):
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

    # Fine scan. This only returns the biterrs, and it runs fast.
    # Start/stop is in time here, but we step over index.
    def fine_eyescan(self, start, stop):
        Align_Delay, ps_per_tap = self.getParameters()
        startIdx = Align_Delay + round(start/ps_per_tap)
        stopIdx = Align_Delay + round(stop/ps_per_tap)
        sc = []
        self.write(self.map['INTERVAL'], 1024)
        for i in range(startIdx, stopIdx):
            self.setDelay(i, useRaw=True)
            time.sleep(0.001)
            sc.append(self.read(self.map['BITERR']))
        return sc    

    # good enough!!
    # So the overall procedure is
    # sc = coarse_eyescan()
    # ss = process_coarse()
    # coarseCenter = ((ss[0]+ss[1])/2)*200.0
    # fs = fine_eyescan(coarseCenter-200.0, coarseCenter + 200.0)
    # fineCenter = find_eyeedge(fs)
    # targetValue = (coarseCenter-200.0)+(fineCenter*ps_per_tap)-1000.0
    # if this takes you below 1000.0 add 1000.0 instead
    @staticmethod
    def find_eyeedge(scan):
        return scan.index(max(scan))

    def locate_eyecenter(self, verbose=False):
        pars = self.getParameters()
        sc = self.coarse_eyescan()
        ss = self.process_coarse(sc)
        if ss is None:
            print("Eye scan failed!")
            print("Coarse scan:")
            print(sc)
            return
        coarseEdge = ((ss[0] + ss[1])/2)*200.0
        if verbose:
            print("Coarse eye edge is at", coarseEdge)
        
        if coarseEdge < 200:
            print('Coarse edge too close to zero. Setting min scan to zero')
            minScan = 0
        else:
            minScan = coarseEdge - 200
        fs = self.fine_eyescan(minScan, coarseEdge+200.0)
        fineEdgeIdx = self.find_eyeedge(fs)
        fineEdge = (coarseEdge-200.0)+(fineEdgeIdx*pars[1])
        if verbose:            
            print("Fine eye edge is at", fineEdge, end='')        
        eye = []
        if fineEdge < 1000.0:
            # move into the stop-side eye
            eye = (fineEdge+1000.0, sc[ss[1]][2])
        else:
            eye = (fineEdge-1000.0, sc[ss[0]][2])
        if verbose:
            print("sample center is at", eye[0], "with bit offset", eye[1])
        return eye
            
    def apply_eye(self, eye):
        self.setDelay(eye[0])
        for i in range(eye[1]):
            self.write(0xC0, 1)
        r = self.read(0xC0)
        if r != pueo_utils.train32:
            raise IOError(f'Readback {hex(r)} not {hex(pueo_utils.train32)} after applying eye!')        
    
    def getParameters(self):
        # The monitor delay is "close enough" to the
        # cell above it that we can use it as the basis.
        # MDLYCNTA is Align_Delay + (700.0/ps_per_tap)
        # MDLYCNTB is (700.0/ps_per_tap)        
        madly = self.read(self.map['MDLYCNTA'])
        mbdly = self.read(self.map['MDLYCNTB'])
        return (madly-mbdly, 700.0/mbdly)

    # target here is in **time**
    def setDelay(self, target, Align_Delay = None, ps_per_tap = None, useRaw=False):
        totdly = target
        if not useRaw:
            if Align_Delay is None or ps_per_tap is None:
                Align_Delay, ps_per_tap = self.getParameters()            
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

    # note note note: enable SHOULD NOT be set until
    # AFTER the SURFs exit training on CIN *or*
    # you don't enable triggers until afterwards too.
    @property
    def enable(self):
        return (self.read(0) >> 4) & 0x1

    @enable.setter
    def enable(self, value):
        r = self.read(0) & 0xFFFFFFEF
        r |= 0x10 if value else 0
        self.write(0, r)
        
        
