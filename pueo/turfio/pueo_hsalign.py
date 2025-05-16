# Generic high-speed align and biterr module.
from ..common.bf import bf
from ..common.dev_submod import dev_submod

from enum import Enum
import time

# Support module for PUEO high speed serial alignment.
#
# We support 2 types of highspeed align: 8 bit and 32 bit
# Each has their own specific train value and max number
# of bitslips.
# Right now this is JUST for the TURFIO<->SURF interface.
# The UltraScales work a bit different, but we'll probably
# refactor this so that the methods are common at some point.
# We also might merge in the RXCLK alignment as well,
# making a base class or something. Who knows.

# sigh, just force the RXCLK alignment here for the
# caligns as an option.
class PueoHSAlign(dev_submod):
    map = { 'CTLRESET' : 0x0,
            'IDELAY' : 0x4,
            'BITERR' : 0x8,
            'BITSLP' : 0xC,
            'SYSERR' : 0x1C }

    class BitWidth(Enum):
        BITWIDTH_8 = 8
        BITWIDTH_32 = 32
        

    # OK, the map is so much more complicated now.
    # We have 2 things we need to derive: number of bitslips
    # and the capture phase. But we'll 'encode' that
    # in the top bit, so 7/6/5/4 need capture phase 1,
    # and 3/2/1/0 need capture phase 0.
    # You can only determine this map after a reset of the ISERDES
    # and when you're in capture phase 0!
    # Once you bitslip you don't really 'know' where you are!
    
    # 0xD4 => 7 BITSLIPS NEEDED
    # 0x9A => 6 BITSLIPS NEEDED
    # 0x35 => 5 BITSLIPS NEEDED
    # 0xA6 => 4 BITSLIPS NEEDED
    # 0x4D => 3 BITSLIPS NEEDED
    # 0xA9 => 2 BITSLIPS NEEDED
    # 0x53 => 1 BITSLIP NEEDED
    # 0x6A => 0 BITSLIPS NEEDED    
    BW8_MAP = { 0xD4 : 7,
                0x9A : 6,
                0x35 : 5,
                0xA6 : 4,
                0x4D : 3,
                0xA9 : 2,
                0x53 : 1,
                0x6A : 0 }

    # LOCK_REQ is either a lock request (if lockable) or enable
    # TRAINEN enables training on the associated output interface
    class CtlReset(Enum):
        ISERDES_RST = 2
        OSERDES_RST = 4
        LOCK_RST = 3
        LOCK_REQ = 8
        LOCKED = 9
        TRAINEN = 10

    # train value used in high-speed alignment
    trainVal = { BitWidth.BITWIDTH_8 : 0x6A,
                 BitWidth.BITWIDTH_32 : 0xA55A6996 }

    # maximum number of bitslips (SERDES width)
    maxSlips = { BitWidth.BITWIDTH_8 : 8,
                 BitWidth.BITWIDTH_32 : 4 }
    
        
    # static function
    # This returns either None (incorrect eye value)
    # or the number of bit-slips required to match up.
    # Training pattern is 0xA55A6996. The bit-slipped
    # versions of that are:
    # 0xA55A6996 (0 bitslips needed)
    # 0x52AD34CB (1 bitslip  needed)
    # 0xA9569A65 (2 bitslips needed)
    # 0xD4AB4D32 (3 bitslips needed)
    # GODDAMNIT JUST MAKE A LOOKUP TABLE
    @classmethod
    def check_eye(cls, eye_val, bw=32, trainValue=trainVal[BitWidth.BITWIDTH_32]):   
        testVal = int(eye_val)
        # just hardcode this check for now!!!
        if (bw == 8):
            return cls.BW8_MAP[testVal] if testVal in cls.BW8_MAP else None
        def rightRotate(n, d):
            return (n>>d)|(n<<(bw-d)) & (2 ** bw - 1)
        for i in range(bw):
            if testVal == rightRotate(trainValue, i):
                return i
        return None    

    # bw is an Enum of the bit widths
    # maxTaps is the number of taps available in the IDELAY
    # eyeInTaps is the width of the data eye in units of taps (78.125 ps tap width, 2 ns eye width = 25.6
    def __init__(self, dev, base,
                 lockable=False,
                 bw=BitWidth.BITWIDTH_32,
                 maxTaps=32,
                 eyeInTaps=26):
        self.bw = bw
        self.lockable = lockable
        self.maxTaps = maxTaps
        self.eyeInTaps = eyeInTaps
        super().__init__(dev, base)

    @staticmethod
    def edges_to_eyes(scan, edges, maxWidth=32, eyeWidth=26):
        eyes = {}
        for edge in edges:
            edgeVal = int((edge[0] + edge[1])/2)
            eyeCenter = edgeVal - (eyeWidth//2)
            if eyeCenter > 0 and scan[eyeCenter] is not None:
                eyes[scan[eyeCenter][1]] = eyeCenter
        lastEyeCenter = edgeVal + (eyeWidth//2)
        if lastEyeCenter < maxWidth and scan[lastEyeCenter] is not None:
            eyes[scan[lastEyeCenter][1]] = lastEyeCenter
        return eyes
        
    # Find the edges of an eyescan
    @staticmethod
    def process_eyescan_edge(scan, width=32, verbose=False, allEdges=False):
        edges = []
        start = None
        stop = None
        curBitno = None
        for i in range(width):
            val = scan[i]
            if val[0] == 0 and val[1] is not None:
                # no errors, data OK
                if curBitno is None:
                    curBitno = val[1]
                    start = i
                elif val[1] != curBitno:
                    stop = i
                    if verbose:
                        print("edge at (", start, ",", stop, ")")
                    if not allEdges:
                        return (start, stop)
                    edges.append((start,stop))
                    start = None
                    stop = None
                    curBitno = None
                else:
                    start = i
        if len(edges) == 0:
            return None
        return edges

    # This method is used for the RXCLK eyescan.
    @staticmethod
    def process_eyescan(scan, width=32):
        # We start off by assuming we're not in an eye.
        in_eye = False
        eye_start = 0
        eyes = []
        for i in range(width):
            if scan[i] == 0 and not in_eye:
                eye_start = i
                in_eye = True
            elif scan[i] > 0 and in_eye:
                eye = [ int(eye_start+(i-eye_start)/2), i-eye_start ]
                eyes.append(eye)
                in_eye = False
        # we exited the loop without finding the end of the eye
        if in_eye:
            eye = [ int(eye_start+(width-eye_start)/2), width-eye_start ]
            eyes.append( eye )

        return eyes
    
    # convenience function for setting delay
    # Might end up subclassing the HSAlign for the UltraScale/7 series differences
    def set_delay(self, delayVal):
        # if we have more than 32 taps, we're cascaded
        # and our cascade sleaze is that when we jump into the second
        # IDELAY we need to add 1.
        if self.maxTaps > 32:
            delayVal = delayVal+1 if delayVal & 32 else delayVal
        self.write(self.map['IDELAY'], delayVal)
    
    def eyescan(self, slptime=0.01, getBitno=True):
        sc = []
        for i in range(self.maxTaps):
            self.set_delay(i)
            time.sleep(slptime)
            biterr = self.read(self.map['BITERR'])
            if getBitno:
                if biterr == 0:
                    testVal = self.read(self.map['BITSLP'])
                    nbits = self.check_eye(testVal, self.bw.value, self.trainVal[self.bw])
                    if nbits != None:
                        sc.append((biterr, nbits % self.maxSlips[self.bw]))
                    else:
                        sc.append((biterr, None))
                else:
                    sc.append((biterr, None))
            else:
                sc.append(biterr)
        return sc

    # rxclk eyescan for the rxclk-capable
    def eyescan_rxclk(self, period=1024):
        slptime = period*8E-9
        sc = []
        self.rxclk_phase = 0
        self.write(0x1C, period)
        for i in range(448):
            self.rxclk_phase = i
            time.sleep(slptime)
            sc.append(self.read(0x1C))
        return sc

    @property
    def rxclk_phase(self):
        return self.read(0)>>16
    
    @rxclk_phase.setter
    def rxclk_phase(self, value):
        rv = self.read(0) & 0xFFFF
        rv |= (value & 0xFFFF) << 16
        self.write(0, rv)        

    @property
    def dout_mask(self):
        return (self.read(0)>>15) & 0x1

    @dout_mask.setter
    def dout_mask(self, value):
        rv = self.read(0) & 0xFFFF7FFF
        rv |= 0x8000 if value else 0
        self.write(0, rv)

    @property
    def iserdes_reset(self):
        return (self.read(0) >> 2) & 0x1

    @iserdes_reset.setter
    def iserdes_reset(self, value):
        rv = self.read(0) & 0xFFFFFFFB
        rv |= 0x4 if value else 0
        self.write(0, rv)

    # enable training on output interface
    def trainEnable(self, onOff):
        rv = bf(self.read(self.map['CTLRESET']))
        rv[self.CtlReset.TRAINEN.value] = int(onOff)
        self.write(self.map['CTLRESET'], int(rv))
    
    # enable or lock.
    def enable(self, onOff, verbose=False):
        if onOff:
            # enable
            rv = bf(self.read(self.map['CTLRESET']))
            rv[self.CtlReset.LOCK_REQ.value] = 1
            self.write(self.map['CTLRESET'], int(rv))
            rv = bf(self.read(self.map['CTLRESET']))
            # locked is either a copy of LOCK_REQ or the status
            if rv[self.CtlReset.LOCKED.value]:
                if verbose:
                    print("Interface enabled and running.")
                return True
            else:
                raise Exception("Interface did not enable")
        else:
            # disable
            if self.lockable:
                rv = bf(self.read(self.map['CTLRESET']))
                rv[self.CtlReset.LOCK_RST.value] = 1
                self.write(self.map['CTLRESET'], int(rv))
            else:
                rv = bf(self.read(self.map['CTLRESET']))
                rv[self.CtlReset.LOCK_REQ.value] = 0
                self.write(self.map['CTLRESET'], int(rv))
            return True

    # OK: we now return a dict of eyes.
    # That way in startup, we can get dicts for each of the
    # devices, and then use Python's bitwise-and functions
    # for lists to find a common eye between all of them.
    # So no more individual sync offsets!
    def find_alignment(self, doReset=True, verbose=False):
        if (doReset):
            self.iserdes_reset = 1
            self.iserdes_reset = 0

        delayVal = None
        slipFix = None

        # set the biterr time and select our input
        self.write(self.map['BITERR'], 131072)
        sc = self.eyescan()
        # Find ALL edges
        edge = self.process_eyescan_edge(sc, width=self.maxTaps, allEdges=True)
        if edge is None:
            raise IOError("Cannot find eye transition: check training status")

        return self.edges_to_eyes(sc, edge,
                                  maxWidth=self.maxTaps,
                                  eyeWidth=self.eyeInTaps)

    # now this function takes a tuple of (eye, bitslips)
    def apply_alignment(self, eye, verbose=False):
        self.set_delay(eye[0])
        slipFix = eye[1]
        if verbose:
            print("Performing", slipFix, "bit slips")
        for i in range(slipFix):
            self.write(self.map['BITSLP'], 1)

        val = self.read(self.map['BITSLP'])
        checkVal = self.check_eye(val, self.bw.value, self.trainVal[self.bw])
        if checkVal % self.maxSlips[self.bw]:
            raise IOError("Alignment procedure failed: still need %d slips??" % (checkVal % self.maxSlips[self.bw]))
        else:
            if verbose:
                print("Alignment succeeded")
            return True
    
    # Alignment method for RXCLK (for the TURF CALIGN)
    def align_rxclk(self, verbose=False):
        if verbose:
            print("Scanning RXCLK->SYSCLK transition.")
        rxsc = self.eyescan_rxclk()
        eyes = self.process_eyescan(rxsc, 448)
        bestEye = None
        for eye in eyes:
            if bestEye is not None:
                if verbose:
                    print(f'Second RXCLK->SYSCLK eye found at {eye[0]}, possible glitch')
                if eye[1] > bestEye[1]:
                    if verbose:
                        print(f'Eye at {eye[0]} has width {eye[1]}, better than {bestEye[1]}')
                    bestEye = eye
                else:
                    if verbose:
                        print(f'Eye at {eye[0]} has width {eye[1]}, worse than {bestEye[1]}, skipping')
            else:
                if verbose:
                    print(f'First eye at {eye[0]} width {eye[1]}')
                bestEye = eye
        if bestEye is None:
            raise IOError("No valid RXCLK->SYSCLK eye found!!")
        if verbose:
            print(f'Using eye at {eye[0]}')
        self.rxclk_phase = eye[0]
        return bestEye[0]
    
                        
