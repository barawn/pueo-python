# Generic high-speed align and biterr module.
from bf import bf
from enum import Enum
from dev_submod import dev_submod
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
class PueoHSAlign(dev_submod):
    map = { 'CTLRESET' : 0x0,
            'IDELAY' : 0x4,
            'BITERR' : 0x8,
            'BITSLP' : 0xC }

    class BitWidth(Enum):
        BITWIDTH_8 = 8
        BITWIDTH_32 = 32

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
    # Note that we ALSO need to check all the nybble-rotated
    # versions of this
    @staticmethod
    def check_eye(eye_val, bw=32, trainValue=trainVal[BitWidth.BITWIDTH_32]):
        testVal = int(eye_val)
        def rightRotate(n, d):
            return (n>>d)|(n<<(bw-d)) & (2 ** bw - 1)
        for i in range(bw):
            if testVal == rightRotate(trainValue, i):
                return i
        return None    

    # bw is an Enum of the bit widths
    # maxTaps is the number of taps available in the IDELAY
    # eyeInTaps is the width of the data eye in units of taps (78.125 ps tap width, 2 ns eye width = 25.6
    def __init__(self, dev, base, lockable=False,bw=BitWidth.BITWIDTH_32, maxTaps=32, eyeInTaps=26):
        self.bw = bw
        self.lockable = lockable
        self.maxTaps = maxTaps
        self.eyeInTaps = eyeInTaps
        super().__init__(dev, base)

    # Find the edges of an eyescan
    @staticmethod
    def process_eyescan_edge(scan, width=32, verbose=False):
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
                    break
                else:
                    start = i
        if start is not None and stop is not None:
            if verbose:
                print("start is", start, "stop is", stop)
            return (start, stop)
        return None

    # convenience function for setting delay
    # Might end up subclassing the HSAlign for the UltraScale/7 series differences
    def set_delay(self, delayVal):
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

    # Run the alignment procedure using new-style alignment (search for bit transition)
    def align(self, doReset=True, verbose=False):
        if (doReset):
            rv = bf(self.read(self.map['CTLRESET']))
            rv[self.CtlReset.ISERDES_RST.value] = 1
            self.write(self.map['CTLRESET'], int(rv))
            rv[self.CtlReset.ISERDES_RST.value] = 0
            self.write(self.map['CTLRESET'], int(rv))

        delayVal = None
        slipFix = None

        # set the biterr time and select our input
        self.write(self.map['BITERR'], 131072)
        sc = self.eyescan()
        edge = self.process_eyescan_edge(sc)
        if edge is None:
            raise Exception("Cannot find eye transition: check training status")

        transition = round((edge[0]+edge[1])/2.)
        # okay, so here's the logic.
        # we have self.maxTaps of delay
        # the eye is self.eyeInTaps wide
        # we *want* to step back round(self.eyeInTaps/2)
        eyeCenterOffset = round(self.eyeInTaps/2)
        # if we're too close to zero, center on the other side of the transition
        # this works for us right now because we have more than a full bit period
        # in the full delay range.
        if transition < eyeCenterOffset:
            delayVal = transition + eyeCenterOffset
        else:
            delayVal = transition - eyeCenterOffset
        if verbose:
            print("Eye transition at", transition,": using tap", delayVal)            

        self.set_delay(delayVal)
        slipFix = sc[delayVal][1]
        if verbose:
            print("Performing", slipFix, "bit slips")
        for i in range(slipFix):
            self.write(self.map['BITSLP'], 1)

        val = self.read(self.map['BITSLP'])
        checkVal = self.check_eye(val, self.bw.value, self.trainVal[self.bw])
        if checkVal % self.maxSlips[self.bw]:
            raise Exception("Alignment procedure failed: still need %d slips??" % (checkVal % self.maxSlips[self.bw]))
        else:
            if verbose:
                print("Alignment succeeded")
            return True
    
            
    
