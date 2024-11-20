# TURFIO device and methods.
#
# Note that at the moment this just accesses the TURFIO through the
# debug serial port. Eventually we'll add methods to access it through
# either the TURF or the housekeeping serial. Note that the TURF may
# have multiple access methods, not sure about that yet.
#
from ..common.serialcobsdevice import SerialCOBSDevice
from ..common.bf import bf
from ..common.genshift import GenShift
from ..common import pueo_utils

from .pueo_hsalign import PueoHSAlign
from .surfbridge import SURFBridge
from .turfio_i2c_bb import PueoTURFIOI2C
from .surfturf import SURFTURF

from enum import Enum
import time

class PueoTURFIO:
    # the TURFIO debug interface has to muck around to get the upper bits (bits 24-21).
    # Note the SURF space is actually 24-22, so upper address handling can be tested
    # purely at the TURFIO by reading (1<<21) (0x20_0000)
    dbgUpperMask = (0xF << 21)
    # Bit to set to swap in upper bits.
    dbgUpperBit = (1<<21)
    
    class DateVersion:
        def __init__(self, val):
            self.major = (val >> 12) & 0xF
            self.minor = (val >> 8) & 0xF
            self.rev = (val & 0xFF)
            self.day = (val >> 16) & 0x1F
            self.mon = (val >> 21) & 0xF
            self.year = (val >> 25) & 0x7F
            
        def __str__(self):
            return "v%d.%d.%d %d/%d/%d" % (self.major, self.minor, self.rev, self.mon, self.day, self.year)
            
        def __repr__(self):
            val = (self.year << 25) | (self.mon << 21) | (self.day << 16) | (self.major<<12) | (self.minor<<8) | self.rev
            return "TURFIO.DateVersion(%d)" % val        

    map = { 'FPGA_ID' : 0x0,
            'FPGA_DATEVERSION' : 0x4,
            'DNA' : 0x8,
            'CTRLSTAT' : 0xC,
            'SYNCCTRL' : 0x10,
            'CLKOFFSET': 0x14,
            'BMDBGCTRL': 0x18,
            'SYSCLKMON' : 0x40,
            'GTPCLKMON' : 0x44,
            'RXCLKMON' : 0x48,
            'HSRXCLKMON' : 0x4C,
            'CLK200MON' : 0x50,
            # this is the base for the COUTs (includes TURF)
            'SURFTURF' : 0x2000,
            # this is the base for the DOUTs (does not include TURF)
            'SURFDOUT' : 0x2050,
            # this is the base for the surfturf common
            'SURFTURFCOMMON' : 0x2800,
            # this is the base for the SURFbridges
            'SURFBRIDGE' : 0x400000
           }

    # allow autocomparison/string generation/etc. w/o StrEnum    
    class AccessType(str, Enum):
        """
        Describes how we're accessing the TURFIO, either
        through serial ('SERIAL') or via the TURF ('TURFGTP')
        """
        
        SERIAL = 'SERIAL'
        """
        TURFIO access directly through the debug serial port.
        """
        TURFGTP = 'TURFGTP'
        """
        TURFIO access via the bridge on the TURF using the GTP.
        """

        def __str__(self) -> str:
            return self.value

    class Position(Enum):
        """
        Describes which TURFIO position this is.
        """
        LV = 'Left Vpol'
        RV = 'Right Vpol'
        LH = 'Left Hpol'
        RH = 'Right Hpol'
        
    class ClockSource(Enum):
        """
        Determines where the system clock comes from.
        """
        INTERNAL = 0
        """
        Use the TURFIO onboard clock (for testing only)
        """
        TURF = 1
        """
        Use the clock from the TURF (normal operation).
        """

    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
            self.dev = SerialCOBSDevice(accessInfo, 1000000, 3)
            self.reset = self.dev.reset
            self.read = self._dbgRead
            self.write = self._dbgWrite
            # NOTE: THERE IS NO UPPER ADDRESS HANDLING IN WRITETO!
            # DO IT YOURSELF!!
            self.writeto = self.dev.writeto
            self.dev.reset()
            self._setUpperBits(0)
            
        elif type == self.AccessType.TURFGTP:
            turf = accessInfo[0]
            ionum = accessInfo[1]
            # check to see if Aurora is up
            linkstat = turf.aurora.linkstat(ionum)
            # low 2 bits are up
            if linkstat & 0x3 != 0x3:
                raise Exception("GTP link %d is not up" % ionum)
            # configure bridge
            brctl = bf(turf.read(turf.map['BRIDGECTRL']))
            brctl[8*(ionum+1)-1:8*ionum] = 1
            turf.write(turf.map['BRIDGECTRL'], int(brctl))
            print("Bridge is: %8.8x" % turf.read(turf.map['BRIDGECTRL']))
            # reset bridge status
            turf.write(turf.map['BRIDGESTAT'], 0)

            self.dev = turf.crate.link[ionum]            
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto
            # Test the bridge. Issue a read.
            id = self.read(0)
            # Now check to see if the read completed.
            st = turf.read(turf.map['BRIDGESTAT'])
            if st != 0:
                raise Exception("TURFIO bridge error: %8.8x", st)            
        elif type == self.AccessType.HSK:
            raise Exception("HSK connection is a Work In Progress")

        self.genshift = GenShift(self.dev, 0x1000)
        self.SHIFT_JTAG_DEV = 0
        self.SHIFT_LMK_DEV = 1
        self.SHIFT_SPI_DEV = 2
        self.SHIFT_TCTRLB_GPIO = 0
        self.SHIFT_JTAGOE_GPIO = 1
        self.SHIFT_LMKLE_GPIO = 2
        self.SHIFT_LMKOE_GPIO = 3
        self.SHIFT_SPICSB_GPIO = 4

        self.i2c = PueoTURFIOI2C(self.genshift)

        # set up the HSAligns
        # first, the COUTs
        self.calign = []
        for i in range(8):
            self.calign.append(PueoHSAlign(self, self.map['SURFTURF']+0x40*i,
                                           lockable=False,
                                           bw=PueoHSAlign.BitWidth.BITWIDTH_32))
        # now the DOUTs
        self.dalign = []
        for i in range(7):
            self.dalign.append(PueoHSAlign(self, self.map['SURFDOUT']+0x40*i,
                                           lockable=False,
                                           bw=PueoHSAlign.BitWidth.BITWIDTH_8))

        # now the SURFbridges
        self.surfbridge = []
        for i in range(7):
            self.surfbridge.append(SURFBridge(self,
                                              self.map['SURFBRIDGE']+0x400000*i))        
        # and common
        self.surfturf = SURFTURF(self.dev, self.map['SURFTURFCOMMON'])
        
            
        # Clock monitor calibration value is now just
        # straight frequency thanks to silly DSP tricks.
        self.clockMonValue = 80000000
        self.write(self.map['SYSCLKMON'], self.clockMonValue)
        time.sleep(0.1)
        # Set up the LMK interface as permanently driven.
        self.genshift.setup(disableTris=(1<<self.SHIFT_LMK_DEV))

    # Private function for handling upper bits in debug mode.
    def _setUpperBits(self, upperAddr):
        self.dev.write(self.map['BMDBGCTRL'], upperAddr)
        # store it so we don't have to do it a bunch of times if it doesn't change
        self.upperBits = upperAddr & self.dbgUpperMask        

    # Private function for testing upper bits.
    def _handleUpperAddr(self, addr):
        if addr & self.dbgUpperMask:
            if self.upperBits != addr & self.dbgUpperMask:
                print("switching upper bits to", hex(addr & self.dbgUpperMask), "from", hex(self.upperBits))
                self._setUpperBits(addr)
            addr = (addr & ~self.dbgUpperMask) | self.dbgUpperBit
        return addr
    
    # Debug read function. This is needed to expand the address space.
    def _dbgRead(self, addr):
        addr = self._handleUpperAddr(addr)
        return self.dev.read(addr)

    # Debug write function. Same as above.
    def _dbgWrite(self, addr, value):
        addr = self._handleUpperAddr(addr)
        return self.dev.write(addr, value)

    # There is no dbgWriteto function.

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
        if fid == "TFIO":
            fdv = self.DateVersion(self.read(self.map['FPGA_DATEVERSION']))
            print(fdv, end=' ')
            dna = self.dna()
            print(hex(dna))
        else:
            print('') 

    def status(self):
        self.identify()
        # N.B.: These values are actually only 16 bit, but they're
        # shifted so they're read out in Hz. If you really want
        # to save space when storing the only non-zero bits are [29:14].
        print("SYSCLK:", self.read(self.map['SYSCLKMON']))
        print("GTPCLK:", self.read(self.map['GTPCLKMON']))
        print("RXCLK:", self.read(self.map['RXCLKMON']))
        print("HSRXCLK:", self.read(self.map['HSRXCLKMON']))
        print("CLK200:", self.read(self.map['CLK200MON']))

    # auxVal is for debugging, it's *totally* not needed
    # just makes it easier to check that all bits are working
    def jtag_setup(self, chainEnable, auxVal=0):
        high = self.genshift.GpioState.GPIO_HIGH
        low = self.genshift.GpioState.GPIO_LOW
        self.genshift.gpio(self.SHIFT_TCTRLB_GPIO, low)
        self.genshift.enable(self.SHIFT_JTAG_DEV, prescale=5)
        self.genshift.gpio(self.SHIFT_JTAGOE_GPIO, low)
        self.genshift.shift(chainEnable,
                            auxVal=auxVal,
                            bitOrder=self.genshift.BitOrder.MSB_FIRST)
        self.genshift.gpio(self.SHIFT_TCTRLB_GPIO, high)
        self.genshift.gpio(self.SHIFT_JTAGOE_GPIO, high)
        self.genshift.disable()

    def crate_control(self, crateOnOff):
        ctrlstat = bf(self.read(self.map['CTRLSTAT']))
        ctrlstat[2] = crateOnOff
        self.write(self.map['CTRLSTAT'], int(ctrlstat))

    def program_lmk(self, reg):
        order=self.genshift.BitOrder.MSB_FIRST
        self.genshift.shift(reg[31:24], bitOrder=order)
        self.genshift.shift(reg[23:16], bitOrder=order)
        self.genshift.shift(reg[15:8], bitOrder=order)
        self.genshift.shift(reg[7:0], bitOrder=order)
        self.genshift.gpio(self.SHIFT_LMKLE_GPIO, self.genshift.GpioState.GPIO_HIGH)
        self.genshift.gpio(self.SHIFT_LMKLE_GPIO, self.genshift.GpioState.GPIO_LOW)

        
    def program_sysclk(self, source=ClockSource.TURF, boost=True):        
        self.genshift.enable(self.SHIFT_LMK_DEV, prescale=1)
        reg = bf(0)
        reg[31] = 1
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg)
        # OK now program each one in turn
        reg[31] = 0       # no reset
        reg[18:17] = 1    # output is divided
        reg[15:8] = 8     # divide by 16
        reg[16] = 1       # enabled
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R0
        reg[3:0] = 1
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R1
        reg[3:0] = 2
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R2
        reg[3:0] = 4
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R4
        reg[3:0] = 5
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R5
        reg[3:0] = 6
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R6
        reg[3:0] = 7
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R7
        reg = bf(0)
        reg[17] = 1
        reg[16] = 1 if boost else 0
        reg[13] = 1
        reg[11] = 1
        reg[9] = 1
        reg[3:0] = 9
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg)
        reg = bf(0)
        reg[16] = 1
        reg[18:17] = 0    # bypass
        reg[3:0] = 3
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg) # R3
        reg = bf(0)
        reg[27] = 1  # global enable
        reg[30] = 1  # must be 1
        reg[29] = source.value # clock source
        reg[3:0] = 14 # register
        print("LMK program: ", hex(int(reg)))
        self.program_lmk(reg)
        self.genshift.gpio(self.SHIFT_LMKOE_GPIO, self.genshift.GpioState.GPIO_HIGH)
        self.genshift.disable()

    def enable_rxclk(self, on=True):
        rv = bf(self.read(self.map['SURFTURFCOMMON']))
        if on:
            rv[31] = 0
        else:
            rv[31] = 1
        self.write(self.map['SURFTURFCOMMON'], int(rv))
        
    # Perform an eye scan on an ISERDES: run over its IDELAY values and get bit
    # error rates. slptime needs to be larger than the acquisition interval
    # programmed in. N.B. FIX THIS TO BE AUTOMATICALLY PROGRAMMED
    #
    # The "getBitno" shifts this from "old-style" (just bit error count)
    # to "new-style" (bit error count and bit offset number)
    #
    # All the eye control stuff is aligned such that +0x4 is IDELAY, +0x8 is BITERR,
    # +0xC is BITSLP.
    def eyescan(self, slptime, base=None, getBitno=False):
        idelayAddr = base + 0x4
        biterrAddr = base + 0x8
        bitslipAddr = base + 0xC
        sc = []
        for i in range(32):
            self.write(idelayAddr, i)
            time.sleep(slptime)
            biterr = self.read(biterrAddr)
            if getBitno:
                if biterr == 0: # This is a new-style eyescan, including bitnos
                    testVal = self.read(bitslipAddr)
                    nbits = pueo_utils.check_eye(testVal)
                    sc.append((biterr, nbits % 4))
                else:
                    sc.append((biterr, None))
            else:
                sc.append(biterr)
        return sc

    def eyescan_rxclk(self, period=1024):
        slptime = period*8E-9
        sc = []
        # Reset to 0 phase shift because it makes the
        # scan quicker.
        self.write(self.map['TURFCTLRESET'], 0<<16)
        # Set the scan period
        self.write(self.map['TURFCTLSYSERR'], period)
        for i in range(448):
            self.write(self.map['TURFCTLRESET'], i<<16)
            time.sleep(slptime)
            sc.append(self.read(self.map['TURFCTLSYSERR']))
        return sc
            
    # Processes an eyescan and returns a list of putative eyes and their widths.
    # NOTE NOTE NOTE:
    #
    # This function needs a "wraparound" option so that if we are
    # passed an eyescan that fully wraps around (like a phase scan)
    # this function can "merge" eyes at the beginning/end of the scan.
    # Other scans (like delay scans) do not actually wrap around and
    # just have to treat the beginning/end of the eye scan as endings.
    # MAYBE IMPROVE THIS LATER EVEN WITH DELAY SCANS
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

    # This is the "new-style" eye-scan function. It finds the center of the
    # transition rather than the center of an eye.
    # We need to do both because when we align RXCLK we need the old method.
    @staticmethod
    def process_eyescan_edge(scan, width=32):
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
            print("start is", start, "stop is", stop)
            return (start, stop)
        return None
    
    # forcibly reset TURFCTL interface
    def reset_turfctl(self):
        rv = bf(self.read(self.map['TURFCTLRESET']))
        rv[3] = 1
        rv[8] = 0
        self.write(self.map['TURFCTLRESET'], int(rv))
        rv = bf(self.read(self.map['TURFCTLRESET']))
        rv[3] = 0
        self.write(self.map['TURFCTLRESET'], int(rv))

    # enable TURF training
    def turf_train(self, enable):
        rv = bf(self.read(self.map['TURFCTLRESET']))
        if enable:
            rv[10] = 1
        else:
            rv[10] = 0
        self.write(self.map['TURFCTLRESET'], int(rv))

    # Set up sync. By default the offset is 8 clocks,
    # which appears to put the TURF and TURFIO/SURF clocks
    # within 1 clock with a 1 meter cable.
    # Note: sync should not be LEFT enabled just in case
    # something goes horribly wrong with the TURFIO comms.
    def sync_enable(self, enable, delay=8):
        if enable:
            self.write(self.map['SYNCCTRL'], 0x100 | delay)
        else:
            self.write(self.map['SYNCCTRL'], 0)
            
    # This is the TURF->TURFIO alignment procedure
    def align_turfctl(self, oldMethod=False):
        # Check to see if the interface is already aligned.
        rv = bf(self.read(self.map['TURFCTLRESET']))
        if rv[9]:
            print("TURFCTL is already aligned, skipping.")
            return

        # It's not aligned. First, let's reset the OSERDES.
        print("Resetting OSERDES.")
        rv[4] = 1;
        self.write(self.map['TURFCTLRESET'], int(rv))
        rv[4] = 0
        self.write(self.map['TURFCTLRESET'], int(rv))
        
        # First we need to align RXCLK->SYSCLK.
        
        # This currently takes a loong time just due to
        # how slow the interface is.
        print("Scanning RXCLK->SYSCLK transition.")
        rxsc = self.eyescan_rxclk()
        eyes = self.process_eyescan(rxsc, 448)
        bestEye = None
        for eye in eyes:
            if bestEye is not None:
                print("Second RXCLK->SYSCLK eye found at", eye[0], "possible glitch")
                if eye[1] > bestEye[1]:
                    print("Eye at", eye[0], "has width", eye[1], "better than", bestEye[1])
                    bestEye = eye
                else:
                    print("Eye at", eye[0], "has width", eye[1], "worse than", bestEye[1], "skipping")
            else:
                print("First eye at", eye[0], "width", eye[1])
                bestEye = eye

        if bestEye is None:
            print("No valid RXCLK->SYSCLK eye found!! Check if clocks are present and correct frequency!")
            return
        print("Using eye at", bestEye[0])
        # n.b. this needs to be a read-modify-write register after this point!!
        self.write(self.map['TURFCTLRESET'], bestEye[0]<<16)

        # RXCLK is aligned. Now reset the ISERDES.
        print("Resetting ISERDES.")
        rv = bf(self.read(self.map['TURFCTLRESET']))
        rv[2] = 1
        self.write(self.map['TURFCTLRESET'], int(rv))
        rv[2] = 0
        self.write(self.map['TURFCTLRESET'], int(rv))
        
        # I really, really hope that we don't get a case
        # where the entire IDELAY region looks clean.

        # NOTE NOTE NOTE NOTE NOTE
        # This SHOULD BE REDONE to be more similar
        # to the TURF case
        #
        # We DO NOT WANT to try to locate the center
        # of the eye directly: we want to find the eye TRANSITION
        # from one bit to the next, and then BACK OFF
        # (or forward) by 1 ns (around 13 taps).
        # This is because we CANNOT SEE the start and stop of any
        # individual eye since the total delay length is too short.

        delayVal = None
        slipFix = None
        
        if oldMethod:
            # Eye scanning with a quick period
            # seems pretty robust.
            self.write(self.map['TURFCTLBITERR'], 131072)
            sc = self.eyescan(0.01, base=self.map['TURFCTLRESET'])            
            eyes = self.process_eyescan(sc, 32)
            # Check each of the eyes and choose the best one.
            bestEye = None
            for eye in eyes:
                self.write(self.map['TURFCTLIDELAY'], eye[0])
                testVal = self.read(self.map['TURFCTLBITSLP'])
                nbits = pueo_utils.check_eye(testVal)
                if nbits is None:
                    print("False eye at", eye[0], "skipped")
                else:
                    eye.append(nbits)
                    if bestEye is not None:
                        print("Eye at", eye[0],"read",hex(testVal),"(", eye[2] % 4, "slips) ", end='')
                        if eye[1] > bestEye[1]:
                            print("has better width (",eye[1],")")
                            bestEye = eye
                        else:
                            print("has worse width (", eye[1],"), skipped")
                    else:
                        print("First valid eye at", eye[0], "(", eye[2] % 4,"slips), width:", eye[1])
                        bestEye = eye
            if bestEye is None:
                print("No valid eyes found!! Alignment FAILED.")
                return        
            print("Using eye at", bestEye[0], "with", bestEye[2] % 4, "slips")
            delayVal = bestEye[0]
            slipFix = bestEye[2] % 4
        else:
            # New method: instead of locating the "best" eye we locate
            # the eye *boundary* and go back (or forward) to the theoretical center.
            # This method's pulled mostly from the TURF methods.
            # We need eyescans with both error count and bitno.
            # For instance, if our eyescan looks like
            # sc[12]=0, 0
            # sc[13]=29123, None
            # sc[14]=19312, None
            # sc[15]=0, 3
            # (and everything else same)
            # then our eye boundary is at 13.5. With (5/64) ns per tap and 2 ns per eye, the full
            # eye width is 25.6, so the half-width is 12.
            # Frustratingly we're trying to minimize latency *and* center the eye, and so
            # it's a bit of a tough situation here. Do we go back or forward?
            # Basically:
            # eye edge < 8 : go to edge + 12
            # 8 <= eye edge <= 12 : go to 0
            # 12 < eye edge : go to edge - 12
            # We may have to adjust this the other way depending on temp and overall stability.
            # Basically we want the alignment to be the same every freaking time.
            # So, in the end we might actually even have to just have an align call with
            # a desired eye and you go as close to the center as you can with it.

            # Quick scans seem OK.
            self.write(self.map['TURFCTLBITERR'], 131072)
            sc = self.eyescan(0.01, base=self.map['TURFCTLRESET'], getBitno=True)            
            edge = self.process_eyescan_edge(sc)
            if edge is None:
                print("Cannot find eye transition, abandoning!")
                return
            transition = round((edge[0] + edge[1])/2.)
            if transition < 8:
                print("Using", transition + 12, "since transition is too low")
                delayVal = transition + 12
            elif transition < 13:
                print("Using 0 since transition at", transition, "is far enough from 0 but too small to center")
                delayVal = 0
            else:
                print("Using", transition - 12, "as delay point")
                delayVal = transition - 12
            print("Needs", sc[delayVal][1], "slips")
            slipFix = sc[delayVal][1]
        
        self.write(self.map['TURFCTLIDELAY'], delayVal)        
        print("Performing", slipFix, "slips")
        for i in range(slipFix):
            self.write(self.map['TURFCTLBITSLP'], 1)
            
        val = self.read(self.map['TURFCTLBITSLP'])
        checkVal = pueo_utils.check_eye(val)
        print("Readback pattern is now", hex(val),"with", checkVal % 4, "slips")
        if checkVal % 4:
            print("Alignment failed?!?")
            return
        else:
            print("Alignment succeeded.")

        # Now we need to enable the interface to lock.
        st = bf(self.read(self.map['TURFCTLRESET']))
        # Set bit 8 (enable lock)
        st[8] = 1
        self.write(self.map['TURFCTLRESET'], int(st))
        # Read back to see if it actually locked. This happens almost instantly.
        rb = bf(self.read(self.map['TURFCTLRESET']))
        # actually return something indicating a failure!!
        if rb[9]:
            print("TURFIO TURFCTL interface is now locked and running.")
        else:
            print("Interface did not lock?!")
        return

    def monitor(self, verbose=True):
        self.i2c.write(0x48, [0x5])
        time.sleep(0.5)
        stat = True
        while stat:
            stat,v = self.i2c.read(0x48, 3)
        volt = (v[0] << 4) + ((v[2] & 0xF0)>>4)
        curr = (v[1] << 4) + (v[2] & 0xF)
        if verbose:
            print(hex(v[0]),hex(v[1]),hex(v[2]))
            print(volt, curr)
            print((volt/4095.)*26.35,"V",(curr*105.84/4096/0.125),"mA")
        return (volt, curr)
    
    def surfMonitor(self, addr, verbose=True):
        # this is technically only a one-time thing but WHATEVER
        r = self.i2c.write(addr, [0xd4, 0x1E, 0x07])
        if r:
            if verbose:
                print("SURF at", hex(addr),"did not ack")
            return None
        r, vinb = self.i2c.readFrom(addr, 0x88, 2)
        r, voutb = self.i2c.readFrom(addr, 0x8B, 2)
        r, ioutb = self.i2c.readFrom(addr, 0x8C, 2)
        r, tempb = self.i2c.readFrom(addr, 0x8D, 2)
        vin = vinb[0] + (vinb[1]<<8)
        vout = voutb[0] + (voutb[1]<<8)
        iout = ioutb[0] + (ioutb[1]<<8)
        temp = tempb[0] + (tempb[1]<<8)        
        if verbose:
            print("Vin:", (vin+0.5)*5.104)
            print("Vout:", (vout+0.5)*5.104)
            print("Iout:", (iout-2048)*(12.51E-6)/(4.762*0.001))
            print("Temp:", (temp*10-31880)/42)
        return (vin, vout, iout, temp)
    
    def surfReset(self, addr):
        # toggle the GPO pin on the power monitor
        r = self.i2c.write(addr, [0xD8, 0x8D, 0x1])
        if r:
            print("error resetting SURF: no I2C ack")
            return
        self.i2c.write(addr, [0xd8, 0xd, 0x1])
        self.i2c.write(addr, [0xd8, 0x8d, 0x1])
        
    # Locate a bridged SURF. Helpful if you forget.
    # This is a silly method but sometimes I am a silly person
    def getSurfSlot(self, surf):
        # loop through the surfbridges
        for i in range(len(self.surfbridge)):
            if self.surfbridge[i] == surf.dev:
                return i
        return None        

    # class method to locate all USB-connected TURFIOs and return ttys/sns
    # only works if you have pyusb installed and are on Linux and have
    @classmethod
    def find_serial_devices(cls, board = -1, verbose=False):
        try:
            import usb
        except ImportError:
            print("find_serial_devices() needs pyusb")
            return
        import os
        if os.uname().sysname != 'Linux':
            print("find_serial_devices() only works on Linux right now (need sysfs)")
            return
        
        # pathlib is super fantastic for traversing sysfs
        from pathlib import Path

        # find FT2232 devices
        devs = []
        for dev in usb.core.find(find_all=True,
                                 idVendor=0x0403,
                                 idProduct=0x6010):
            # check their serial number
            # if for some reason it's not there, pyusb throws
            # ValueError
            try:
                sn = dev.serial_number
                # we know where we stored stuff
                typeboard = sn[-6:]
                typeStr = typeboard[:-2]
                boardStr = typeboard[-2:]
                thisType = chr(int(typeStr[0:2],16))+chr(int(typeStr[2:],16))
                thisBoard = int(boardStr, 16)
                if thisType == 'TI':
                    if board == -1 or board == thisBoard:
                        devs.append((dev, thisBoard))
                        if verbose:
                            print("found TURFIO%d at bus %d dev %d" % (thisBoard, dev.bus, dev.address))
            except ValueError:
                pass
            
        # now we can zip through the ftdi_sio devices
        # and find All The Guys
        matchedDevices = []
        for p in Path('/sys/bus/usb/drivers/ftdi_sio').glob('*'):
            if (not os.path.isdir(p)) or os.path.basename(p) == 'module':
                continue
            bus = int(( p / '..' / 'busnum').read_text().rstrip('\x00\n'))
            address = int(( p / '..' / 'devnum').read_text().rstrip('\x00\n'))
            ttyPath = '/dev/' + os.path.basename( (p.glob('tty*')).__next__() )
            if verbose:
                print("path %s (tty %s) has bus %d/addr %d" % (p, ttyPath, bus, address))
            for devt in devs:
                thisDev = devt[0]
                thisBoard = devt[1]
                if thisDev.bus == bus and thisDev.address == address:
                    matchedDevices.append( (ttyPath, thisBoard) )
        return matchedDevices
