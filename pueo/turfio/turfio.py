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
from ..common.genspi import GenSPI
from ..common import pueo_utils

from .pueo_hsalign import PueoHSAlign
from .surfbridge import SURFBridge
from .turfio_i2c_bb import PueoTURFIOI2C
from .surfturf import SURFTURF

from enum import Enum
import time
import glob

class PueoTURFIO:
    # the TURFIO debug interface has to muck around to get the upper bits (bits 24-21).
    # Note the SURF space is actually 24-22, so upper address handling can be tested
    # purely at the TURFIO by reading (1<<21) (0x20_0000)
    dbgUpperMask = (0xF << 21)
    # Bit to set to swap in upper bits.
    dbgUpperBit = (1<<21)
    # Bit to set to burst
    dbgBurstBit = (1<<22)
    
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
            # WE GO EVEN FASTER NOW
            self.dev = SerialCOBSDevice(accessInfo, 2500000, 3)
            self.reset = self.dev.reset
            self.read = self._dbgRead
            self.write = self._dbgWrite
            # NOTE: THERE IS NO UPPER ADDRESS HANDLING IN WRITETO!
            # DO IT YOURSELF!!
            self.writeto = self.dev.writeto
            # NOTE: THERE IS NO UPPER ADDRESS HANDLING IN MULTIWRITE!
            # DO IT YOURSELF!!
            self.multiwrite = self.dev.multiwrite
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
            # not implemented now
            self.multiwrite = None
            self.writeto = self.dev.writeto
            # Test the bridge. Issue a read.
            id = self.read(0)
            # Now check to see if the read completed.
            st = turf.read(turf.map['BRIDGESTAT'])
            if st != 0:
                raise Exception("TURFIO bridge error: %8.8x" % st)
        elif type == self.AccessType.HSK:
            raise Exception("HSK connection is a Work In Progress")
        else:
            raise Exception("type must be one of",
                            [e.value for e in self.AccessType])

        self.genshift = GenShift(self, 0x1000)
        self.SHIFT_JTAG_DEV = 0
        self.SHIFT_LMK_DEV = 1
        self.SHIFT_SPI_DEV = 2
        self.SHIFT_TCTRLB_GPIO = 0
        self.SHIFT_JTAGOE_GPIO = 1
        self.SHIFT_LMKLE_GPIO = 2
        self.SHIFT_LMKOE_GPIO = 3
        self.SHIFT_SPICSB_GPIO = 4

        self.i2c = PueoTURFIOI2C(self.genshift)

        self.genspi = GenSPI(self.genshift,
                             self.SHIFT_SPI_DEV,
                             self.SHIFT_SPICSB_GPIO,
                             prescale=2)
        
        # set up the HSAligns
        # first, the COUTs. I don't know why these were marked as
        # non-lockable, of course they are??
        self.calign = []
        for i in range(8):
            self.calign.append(PueoHSAlign(self, self.map['SURFTURF']+0x40*i,
                                           lockable=True,
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
        self.surfturf = SURFTURF(self, self.map['SURFTURFCOMMON'])
        
            
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
        rv = bf(self.read(self.map['CTRLSTAT']))
        print("Crate Power Enable:", rv[2])
        print("RACK 3.3V Enable:", rv[3])
        print("Crate I2C Ready:", rv[4])
        print("Local HSKBUS Override:", rv[5])
        print("HSKBUS Crate Bridge Enable:", rv[6])
        print("Housekeeping RX Byte Count:", rv[23:16])
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
        # and now pull sysclk out of reset
        r = bf(self.read(0xC))
        r[7] = 0
        self.write(0xC, int(r))

    def enable_rxclk(self, on=True):
        rv = bf(self.read(self.map['SURFTURFCOMMON']))
        if on is True:
            on = 0xFF
        if on is False:
            on = 0x0
        rv[31:24] = (~on & 0xFF)
        self.write(self.map['SURFTURFCOMMON'], int(rv))

    # All of the eye alignment stuff is now in the HSAlign.

    @property
    def syncdelay(self):
        return self.read(0x10) & 0xFF

    @syncdelay.setter
    def syncdelay(self, value):
        r = self.read(0x10) & 0xFFFFFF00
        r |= value & 0xFF
        self.write(0x10, r)

    @property
    def extsync(self):
        return self.read(0x10) >> 8

    @extsync.setter
    def extsync(self, value):
        r = self.read(0x10) & ~0x100
        if value:
            r |= 0x100
        self.write(0x10, r)
        
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

    def updateTurfioFirmware(self, turfionum, firmvers=None, mcs_loc='/home/pueo/imgs/'):
        """
        function to update TURFIO firmware after files have been copied into computer

        Parameters
        ----------
        turfionum: int
            TURFIO # to link [1,2,4, or 5]
        firmverse: string (optional)
            if specified, use TURFIO firmware version # [of form v_r_p_]
        mcs_loc: string (defaults to /home/pueo/imgs/)
            specifies where TURFIO firmware is located
        """
        dev = self.find_serial_devices(int(turfionum))[0][0]

        print("Linked to TURFIO "+turfionum)
        
        if firmvers is None:
            mcs_list = glob.glob(mcs_loc+'pueo_turfio_*.mcs').sort()[-1]
            vers_list = []
            for vers in mcs_list:
                curr_vers = vers.split(mcs_loc+'pueo_turfio_')[1].split('.mcs')[0]
                vers_list.append(curr_vers)
            mcs_vers = mcs_loc+'pueo_turfio_'+vers_list[-1]+'.mcs'
            
        else:
            mcs_vers = mcs_loc+'pueo_turfio_'+firmvers+'.mcs'

        print("Using TURFIO firmware "+mcs_vers)

        with dev.genspi as spi: 
            spi.program_mcs(mcs_vers)   

    # class method to locate all USB-connected TURFIOs and return ttys/sns
    # only works if you have pyusb installed and are on Linux and have
    @classmethod
    def find_serial_devices(cls, board = -1, verbose=False):
        return SerialCOBSDevice.find_serial_devices(board, 'TI', verbose)
