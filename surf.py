# SURF device and methods.
# Note that this is NOT the Overlay module that runs on Pynq!
# That module configures and programs the hardware and sets
# it up to be commanded by *this* module.
# That module is called surf6, this module is called PueoSURF
# to match PueoTURFIO/PueoTURF.
#
# Like the TURFIO, it has multiple access methods:
# direct serial, or TURFIO bridged (which itself can be
# TURF bridged).

from serialcobsdevice import SerialCOBSDevice
from enum import Enum

import time
from bf import bf

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
                        
    class AccessType(Enum):
        SERIAL = 'Serial'

    map = { 'FPGA_ID' : 0x0,
            'FPGA_DATEVERSION' : 0x4,
            'DNA' : 0x8,
            'ACLKMON' : 0x40,
            'GTPCLKMON' : 0x44,
            'RXCLKMON' : 0x48,
            'CLK300MON' : 0x4C,
            'IFCLKMON' : 0x50,
            'TIOCTRL' : 0x800,
            'TIORXERR' : 0x840,
            'TIOPDLYCNTA' : 0x880,
            'TIOPDLYCNTB' : 0x884,
            'TIOMDLYCNTA' : 0x888,
            'TIOMDLYCNTB' : 0x88C}
        
    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
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
    def align_rxclk(self, verbose=False):
        sc = self.eyescan_rxclk()
        eyes = self.process_eyescan(sc)
        if len(sc) == 0:
            if verbose:
                print("RXCLK alignment failed, no eyes found!")
                return None
        thisEye =  eyes[0]
        self.rxclkShift(thisEye[0])
        shift = thisEye[0] if abs(thisEye[0]-672)>thisEye[0] else (thisEye[0]-672)
        skew = (shift/672)*8
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
        