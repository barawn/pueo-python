# TURFIO device and methods.
#
# Note that at the moment this just accesses the TURFIO through the
# debug serial port. Eventually we'll add methods to access it through
# either the TURF or the housekeeping serial. Note that the TURF may
# have multiple access methods, not sure about that yet.
#
from serialcobsdevice import SerialCOBSDevice
from enum import Enum
import time
from bf import bf
from genshift import GenShift

class PueoTURFIO:
    class DateVersion:
        def __init__(self, val):
            self.major = (val >> 12) & 0xF
            self.minor = (val >> 8) & 0xF
            self.rev = (val & 0xFF)
            self.day = (val >> 16) & 0x1F
            self.mon = (val >> 21) & 0xF
            self.year = (val >> 25) & 0x7F
            
        def __str__(self):
            return f'v{self.major}.{self.minor}.{self.rev} {self.mon}/{self.day}/{self.year}'

        def __repr__(self):
            val = (self.year << 25) | (self.mon << 21) | (self.day << 16) | (self.major<<12) | (self.minor<<8) | self.rev
            return f'TURFIO.DateVersion({val})'

    map = { 'FPGA_ID' : 0x0,
            'FPGA_DATEVERSION' : 0x4,
            'DNA' : 0x8,
            'CTRLSTAT' : 0xC,
            'SYSCLKMON' : 0x40,
            'GTPCLKMON' : 0x44,
            'RXCLKMON' : 0x48,
            'HSRXCLKMON' : 0x4C,
            'CLK200MON' : 0x50 }
        
    class AccessType(Enum):
        SERIAL = 'Serial'
        TURFGTP = 'TURF GTP'
        TURFCTL = 'TURF CTL'
        HSK = 'Housekeeping'

    class Position(Enum):
        LV = 'Left Vpol'
        RV = 'Right Vpol'
        LH = 'Left Hpol'
        RH = 'Right Hpol'
        
    class ClockSource(Enum):
        INTERNAL = 0
        TURF = 1
        
    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
            self.dev = SerialCOBSDevice(accessInfo, 115200)
            self.reset = self.dev.reset
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto

            self.dev.reset()
        elif type == self.AccessType.TURFGTP:
            raise Exception("TURF GTP connection is a Work In Progress")
        elif type == self.AccessType.TURFCTL:
            raise Exception("TURF CTL connection is a Work In Progress")
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
        
        # Clock monitor calibration value is now just
        # straight frequency thanks to silly DSP tricks.
        self.clockMonValue = 40000000
        self.write(self.map['SYSCLKMON'], self.clockMonValue)
        time.sleep(0.1)
        # Set up the LMK interface as permanently driven.
        self.genshift.setup(disableTris=(1<<self.SHIFT_LMK_DEV))
        
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

    def program_lmk(self, reg):
        order=self.genshift.BitOrder.MSB_FIRST
        self.genshift.shift(reg[31:24], bitOrder=order)
        self.genshift.shift(reg[23:16], bitOrder=order)
        self.genshift.shift(reg[15:8], bitOrder=order)
        self.genshift.shift(reg[7:0], bitOrder=order)
        self.genshift.gpio(self.SHIFT_LMKLE_GPIO, self.genshift.GpioState.GPIO_HIGH)
        self.genshift.gpio(self.SHIFT_LMKLE_GPIO, self.genshift.GpioState.GPIO_LOW)

        
    def program_sysclk(self, source=ClockSource.TURF):        
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
        
        
        
        
        
    
