# SURF device and methods.
# This module can run on either the SURF or remotely:
# if it runs on the SURF, it needs the wbspi module.
#
# Like the TURFIO, it has multiple access methods:
# direct serial (to be deprecated), SPI, or TURFIO
# bridged (which itself can be TURF bridged).

from ..common.serialcobsdevice import SerialCOBSDevice
from ..common import pueo_utils
from ..common.bf import bf
from enum import Enum
import time


class PueoSURF:
    class DateVersion:
        def __init__(self, val):
            self.major = (val >> 12) & 0xF
            self.minor = (val >> 8) & 0xF
            self.rev = (val & 0xFF)
            self.day = (val >> 16) & 0x1F
            self.mon = (val >> 21) & 0xF
            # SURF trims the first bit of
            # year to handle boardrev
            # god help me if this matters in 2064
            self.year = (val >> 25) & 0x3F
            self.brev = (val >> 31) & 0x1
            
        def __str__(self):
            return "v%d.%d.%d %d/%d/%d boardrev %c" % (self.major, self.minor, self.rev, self.mon, self.day, self.year, 'B' if self.brev else 'A')
            
        def __repr__(self):
            val = (self.brev << 31) | (self.year << 25) | (self.mon << 21) | (self.day << 16) | (self.major<<12) | (self.minor<<8) | self.rev
            return "SURF.DateVersion(%d)" % val        
                        
    # subclassing from str and Enum allows passing the string
    class AccessType(str, Enum):
        SERIAL = 'SERIAL'
        TURFIO = 'TURFIO'
        SPI = 'SPI'

    map = { 'FPGA_ID' : 0x0,
            'FPGA_DATEVERSION' : 0x4,
            'DNA' : 0x8,
            'CTRLSTAT' : 0xC,
            'ACLKMON' : 0x40,
            'GTPCLKMON' : 0x44,
            'RXCLKMON' : 0x48,
            'CLK300MON' : 0x4C,
            'IFCLKMON' : 0x50,
            'RACKCLKMON' : 0x54,
            'TIOCTRL' : 0x800,
            'TIORXERR' : 0x840,
            'TIOCAPTURE': 0x844,
            'TIOBITERR': 0x848,
            'TIOPDLYCNTA' : 0x880,
            'TIOPDLYCNTB' : 0x884,
            'TIOMDLYCNTA' : 0x888,
            'TIOMDLYCNTB' : 0x88C}
        
    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SPI:
            from ..common.wbspi import WBSPI
            
            self.dev = WBSPI(path=accessInfo,
                             speed=10000000)
            self.read = self.dev.read
            self.write = self.dev.write                             
        elif type == self.AccessType.SERIAL:
            # need to think about a way to spec the address here?
            self.dev = SerialCOBSDevice(accessInfo,
                                        baudrate=1000000,
                                        addrbytes=3,
                                        devAddress=0)
            self.reset = self.dev.reset
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto

            self.reset()
        elif type == self.AccessType.TURFIO:
            turfio = accessInfo[0]
            slot = accessInfo[1]
            # I dunno, test something here.
            # Probably check the errors or something
            self.dev = turfio.surfbridge[slot]
            self.read = self.dev.read
            self.write = self.dev.write
            # CRAP I MIGHT NEED TO IMPLEMENT WRITETO OR SOMETHING??
        else:
            raise Exception("type must be one of",
                            [e.value for e in self.AccessType])
            
        # clock monitor calibration
        self.clockMonValue = 100000000
        self.write(self.map['ACLKMON'], self.clockMonValue)
        time.sleep(0.1)        
            
    def dna(self):
        self.write(self.map['DNA'], 0x80000000)
        dnaval=0
        for i in range(57):
            r = self.read(self.map['DNA'])
            val = r & 0x1
            dnaval = (dnaval << 1) | val
        return dnaval

    def identify(self):
        def str4(num):
            id = str(chr((num>>24)&0xFF))
            id += chr((num>>16) & 0xFF)
            id += chr((num>>8) & 0xFF)
            id += chr(num & 0xFF)
            return id

        fid = str4(self.read(self.map['FPGA_ID']))
        print("FPGA:", fid, end=' ')
        if fid == "SURF":
            fdv = self.DateVersion(self.read(self.map['FPGA_DATEVERSION']))
            print(fdv, end=' ')
            dna = self.dna()
            print(hex(dna))
        else:
            print('')
            
    def status(self):
        self.identify()
        print("ACLK:", self.read(self.map['ACLKMON']))
        print("GTPCLK:", self.read(self.map['GTPCLKMON']))
        print("RXCLK:", self.read(self.map['RXCLKMON']))
        print("CLK300:", self.read(self.map['CLK300MON']))
        print("IFCLK:", self.read(self.map['IFCLKMON']))
        print("RACKCLK:", self.read(self.map['RACKCLKMON']))
        
    def getDelayParameters(self):
        # the '700.0' here is the value we spec'd
        # in the HDL for the fixed delay
        # We return the value of Align_Delay and
        # ps_per_tap
        madly = self.read(self.map['TIOMDLYCNTA'])
        mbdly = self.read(self.map['TIOMDLYCNTB'])
        return (madly-mbdly, 700.0/mbdly)

    def rxclkShift(self, phaseValue):
        if phaseValue > 671:
            print("phaseValue must be less than 672!")
            return
        r = bf(self.read(self.map['TIOCTRL']))
        r[30:16] = phaseValue
        self.write(self.map['TIOCTRL'], int(r))
        ntrials = 100
        while ntrials > 0:
            if self.read(self.map['TIOCTRL']) & (1<<31):
                ntrials = ntrials - 1
            else:
                break
        if ntrials == 0:
            print("IDELAYCTRL never became ready?!?")
            return
    
    # Which eye we pick for RXCLK alignment *does not matter*
    # so long as it's the *same* for all of the SURFs and
    # the skew between all of the SURFs is small enough.
    # So we just *randomly* pick the first eye.
    # returns measured skew or None on error
    # After we find the eye, we have to align IFCLK
    # to RXCLK as well. We do that by forcibly
    # resetting the PLL until it aligns properly.
    def align_rxclk(self, userSkew=None, verbose=False):
        if userSkew is None:
            sc = self.eyescan_rxclk()
            eyes = self.process_eyescan(sc)
            if len(sc) == 0:
                if verbose:
                    print("RXCLK alignment failed, no eyes found!")
                    return None
            thisEye =  eyes[0]
            if verbose:
                print("Eyes:", eyes)
                print("Choosing eye at",thisEye[0],"with width",thisEye[1])
            self.rxclkShift(thisEye[0])
            # wtf does this even do???
            shift = thisEye[0] if abs(thisEye[0]-672)>thisEye[0] else (thisEye[0]-672)
            if shift != thisEye[0]:
                print("WARNING: WE FELL INTO THE WEIRD IF CLAUSE")
                print("WARNING: thisEye[0]: %d" % thisEye[0])
                print("WARNING: shift: %d" % shift)
                print("WARNING: eyes:", eyes)
            skew = (shift/672)*8
        else:
            self.rxclkShift(int(userSkew*672/8))
        # Now we need to check the alignment
        r = bf(self.read(self.map['TIOCTRL']))
        nreset = 0
        while r[15]:
            if verbose:
                print("IFCLK/RXCLK are misaligned, resetting PLLs")
            r[13] = 1
            self.write(self.map['TIOCTRL'], int(r))
            r[13] = 0
            self.write(self.map['TIOCTRL'], int(r))
            r = bf(self.read(self.map['TIOCTRL']))
            nreset = nreset + 1
        if verbose:
            print("RXCLK alignment complete after", nreset,
            "resets" if nreset != 1 else "reset",
            "skew:", skew)
        return skew     
    
    def eyescan_rxclk(self, period=1024):
        slptime = period*10E-9
        sc = []
        self.rxclkShift(0)
        self.write(self.map['TIORXERR'], period)
        for i in range(672):
            self.rxclkShift(i)
            time.sleep(slptime)
            sc.append(self.read(self.map['TIORXERR']))
        return sc
            
    @staticmethod
    def process_eyescan(scan, width=672, wraparound=True):
        in_eye = False
        eye_start = 0
        eyes = []
        for i in range(width):
            if scan[i] == 0 and not in_eye:
                eye_start = i
                in_eye = True
            elif scan[i] > 0 and in_eye:
                eye = [ int(eye_start + (i-eye_start)/2), i-eye_start]
                eyes.append(eye)
                in_eye = False
        if in_eye:
            if wraparound:
                if scan[0] != 0:
                    # this is the end anyway
                    eye = [ int(eye_start + (672-eye_start)/2), 672-eye_start]
                    eyes.append(eye)
                else:
                    # the two parameters are the middle and the width.
                    # so to fix the wraparound, the width gets the end point
                    stop = eyes[0][1]
                    start = eye_start - 672
                    width = stop - start
                    mid = (stop+start)/2
                    if mid < 0:
                        mid = mid + 672
                    mid = int(mid)
                    eyes[0] = [mid, width]
            else:
                eye = [ int(eye_start+(width-eye_start)/2),width-eye_start]
                eyes.append(eye)
        return eyes
        
    def turfioReset(self):
        # reset shift just to be careful
        # later firmware does this automatically on MMCM reset
        self.rxclkShift(0)
        # force it
        self.vtc(True)
        self.mmcmReset(True)
        self.cinReset(True)
        self.idelayctrlReset(True)
        
        # release MMCM
        self.mmcmReset(False)
        # wait to become ready
        ntrials = 100
        while ntrials > 0:
            if self.read(self.map['TIOCTRL']) & (1<<5):
                break
            else:
                ntrials = ntrials - 1
        if ntrials == 0:
            print("MMCM never became ready?!?")
            return
        # release CIN
        self.cinReset(False)
        # release IDELAYCTRL
        self.idelayctrlReset(False)
        # wait for ready
        ntrials = 100
        while ntrials > 0:
            if self.read(self.map['TIOCTRL']) & (1<<3):
                break
            else:
                ntrials = ntrials - 1
        if ntrials == 0:
            print("IDELAYCTRL never became ready?!?")
            return
        # done
        
    def mmcmReset(self, enable):
        r = bf(self.read(self.map['TIOCTRL']))
        r[4] = 1 if enable else 0
        self.write(self.map['TIOCTRL'], int(r))
        
    def idelayctrlReset(self, enable):
        r = bf(self.read(self.map['TIOCTRL']))
        r[2] = 1 if enable else 0
        self.write(self.map['TIOCTRL'], int(r))
        
    def cinReset(self, enable):
        r = bf(self.read(self.map['TIOCTRL']))
        r[0] = 1 if enable else 0
        self.write(self.map['TIOCTRL'], int(r))
    
    def vtc(self, enable):
        # this is a DISABLE bit
        r = bf(self.read(self.map['TIOCTRL']))
        r[1] = 0 if enable else 1
        self.write(self.map['TIOCTRL'], int(r))
        
    def setDelay(self, target, Align_Delay = None, ps_per_tap = None, useRaw = False):
        totdly = target
        if not useRaw:
            if Align_Delay is None or ps_per_tap is None:
                Align_Delay, ps_per_tap = self.getDelayParameters()
            totdly = round(target/ps_per_tap) + Align_Delay
        # You only need to split the delay equally when specifying a delay.
        # When loading a delay, you can do it however you want.
        pdlya = totdly
        pdlyb = 0
        if pdlya > 511:
            pdlyb = pdlya - 511
            pdlya = 511
            
        # disable VTC
        self.vtc(False)
        self.write(self.map['TIOPDLYCNTA'], pdlya)
        while self.read(self.map['TIOPDLYCNTA']) != pdlya:
            pass
        self.write(self.map['TIOPDLYCNTB'], pdlyb)
        while self.read(self.map['TIOPDLYCNTB']) != pdlyb:
            pass
        # reenable VTC
        self.vtc(True)

    # zip through the range of delays to find boundaries
    def coarse_eyescan(self):
        Align_Delay, ps_per_tap = self.getDelayParameters()
        self.write(self.map['TIOBITERR'], 131072)
        sc = []
        for i in range(12):
            bitno = None
            self.setDelay(200*i, Align_Delay, ps_per_tap)
            time.sleep(0.002)
            errcnt = self.read(self.map['TIOBITERR'])
            if errcnt == 0:
                val = self.read(self.map['TIOCAPTURE'])
                bitno = pueo_utils.check_eye(val)
                if bitno is not None:
                    bitno = bitno % 4
                sc.append((i, errcnt, bitno))
            else:
                sc.append((i, errcnt, None))
        return sc
    
    # locate the boundaries
    @staticmethod
    def process_coarse(scan, verbose=False):
        start = None
        stop = None
        curBitno = None
        for val in scan:
            if val[1] == 0 and val[2] is not None:
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
        if verbose:
            print("no start and stop found!")
        return None
    
    # Fine scan. At this point we know there's a transition
    # between these 2 points, so locate the ideal point.
    # Here instead of stepping over delays, we're going
    # tap by tap.
    def fine_eyescan(self, start, stop):
        Align_Delay, ps_per_tap = self.getDelayParameters()
        startIdx = Align_Delay + round(start/ps_per_tap)
        stopIdx = Align_Delay + round(stop/ps_per_tap)
        sc = []
        self.write(self.map['TIOBITERR'], 1024)
        for i in range(startIdx, stopIdx):
            self.setDelay(i, useRaw=True)
            time.sleep(0.001)
            sc.append(self.read(self.map['TIOBITERR']))
        return sc
    
    # sleazeball
    # I should probably get all of the possible maxes
    # and average it or something
    @staticmethod
    def find_eyeedge(scan, verbose=True):
        mx = max(scan)
        st = scan.index(mx)
        if scan.count(mx) > 1:
            if verbose:
                print("there are", scan.count(mx), "max points")
            scan.reverse()
            sp = len(scan) - scan.index(mx)
            scan.reverse()
            mid = round((st+sp)/2)
            if verbose:
                print("first:", st, "last:", sp, "avg:", mid)
            return mid
        else:
            return st
    
    def locate_eyecenter(self, verbose=True):
        pars = self.getDelayParameters()
        sc = self.coarse_eyescan()
        ss = self.process_coarse(sc, verbose=verbose)
        if ss is None:
            if verbose:
                print("Eye scan failed!")
                print("Coarse scan:")
                print(sc)
            return None
        coarseEdge = ((ss[0]+ss[1])/2)*200.0
        if verbose:
            print("Coarse eye edge is at", coarseEdge)
        fs = self.fine_eyescan(coarseEdge-200.0, coarseEdge+200.0)
        fineEdgeIdx = self.find_eyeedge(fs)
        fineEdge = (coarseEdge-200.0)+(fineEdgeIdx*pars[1])
        if verbose:
            print("Fine eye edge is at", fineEdge, end='')
        eye = []
        if fineEdge < 1000.0:
            # move into the stop-side eye
            eye = (fineEdge + 1000.0, sc[ss[1]][2])
        else:
            eye = (fineEdge - 1000.0, sc[ss[0]][2])
        if verbose:
            print("sample center is at", eye[0], "with bit offset", eye[1])
        return eye

    # these are all of the simple controls
    @property
    def turfio_lock_req(self):
        return (self.read(0x800) >> 11) & 0x1

    @turfio_lock_req.setter
    def turfio_lock_req(self, value):
        r = bf(self.read(0x800))
        r[11] = 1 if value else 0
        self.write(0x800, int(r))

    @property
    def turfio_locked_or_running(self):
        return (self.read(0x800) >> 12) & 0x1

    @property
    def turfio_cin_active(self):
        return (self.read(0x800) >> 7) & 0x1

    # trying to write *anything* to this resets it
    @turfio_cin_active.setter
    def turfio_cin_active(self, value):
        r = self.read(0x800) & ~0x80
        self.write(0x800, r)
    
    @property
    def turfio_train_enable(self):
        return (self.read(0x800) >> 6) & 0x1

    @turfio_train_enable.setter
    def turfio_train_enable(self, value):
        r = bf(self.read(0x800))
        r[6] = 1 if value else 0
        self.write(0x800, int(r))

    @property
    def sync_offset(self):
        return (self.read(0xC) >> 16) & 0x1F

    @sync_offset.setter
    def sync_offset(self, value):
        r = bf(self.read(0xC))
        value &= 0x1F
        r[20:16] = value
        self.write(0xC, int(r))
    
    # set the bit offset to a value
    def turfioSetOffset(self, val):
        # both bitslip reset and bitslip are flags
        # so don't need to clear them
        r = bf(self.read(self.map['TIOCTRL']))
        r[8] = 1
        self.write(self.map['TIOCTRL'], int(r))
        r[8] = 0
        r[9] = 1
        for i in range(val):
            self.write(self.map['TIOCTRL'], int(r))
            
