from ..common.serialcobsdevice import SerialCOBSDevice
from ..common.bf import bf
from ..common.dev_submod import dev_submod

from .pueo_turfctl import PueoTURFCTL
from .pueo_turfaurora import PueoTURFAurora
from .pueo_turfgbe import PueoTURFGBE
from .pueo_cratebridge import PueoCrateBridge

from ..common.pyaxibridge import PyAXIBridge

import mmap
import struct
import os
import time
from enum import Enum

class PueoTURF:
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
            return f'TURF.DateVersion({val})'

    map = { 'FPGA_ID' : 0x0,
            'FPGA_DATEVERSION' : 0x4,
            'DNA' : 0x8,
            'SYSCLKMON' : 0x800,
            'GBECLKMON' : 0x804,
            'DDR0CLKMON' : 0x808,
            'DDR1CLKMON' : 0x80C,
            'AURCLKMON' : 0x810,
            'GRXCLKMON' : 0x814,
            'GTXCLKMON' : 0x818,
            'BRIDGECTRL' : 0x1000,
            'BRIDGESTAT' : 0x1004}

    # subclassing from str and Enum allows passing the string    
    class AccessType(str, Enum):
        SERIAL = 'Serial'
        ETH = 'Ethernet'
        AXI = 'AXI'

    # search device tree nodes to grab base/size
    DT_PATH = "/sys/firmware/devicetree/base/axi/"
    BRIDGE_GLOB = "axilite_bridge@*"
    REG_PATH = "reg"
    
    @classmethod
    def axilite_bridge(cls):
        from pathlib import Path
        
        for br in Path(cls.DT_PATH).glob(cls.BRIDGE_GLOB):
            brp = br
        rp = brp / cls.REG_PATH
        vals = rp.read_bytes()
        base , = struct.unpack(">Q", vals[0:8])
        size , = struct.unpack(">Q", vals[8:16])
        return (base, size)
        
    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
            self.dev = SerialCOBSDevice(accessInfo, 115200, addrbytes=4)
            self.reset = self.dev.reset
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto
            self.dev.reset()
        elif type == self.AccessType.AXI:
            self.dev = PyAXIBridge(accessInfo[0], accessInfo[1])
            self.reset = lambda : None
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.write
        elif type == self.AccessType.ETH:
            raise Exception("Ethernet is a Work in Progress")
        else:
            raise Exception("type must be one of",
                            [e.value for e in self.AccessType])
            
        self.ctl = PueoTURFCTL(self.dev, 0x10000)
        self.aurora = PueoTURFAurora(self.dev, 0x8000)
        self.gbe = PueoTURFGBE(self.dev, 0x4000)
        self.crate = PueoCrateBridge(self.dev, (1<<27))

        self.clockMonValue = 100000000
        self.write(self.map['SYSCLKMON'], self.clockMonValue)
        time.sleep(0.1)
        
    def dna(self):
        self.write(self.map['DNA'], 0x80000000)
        dnaval = 0
        for i in range(57):
            r = self.read(self.map['DNA'])
            val = r & 0x1
            dnaval = (dnaval << 1) | val
        return dnaval

    def status(self):
        self.identify()
        print("SYSCLK:", self.read(self.map['SYSCLKMON']))
        print("GBECLK:", self.read(self.map['GBECLKMON']))
        print("DDR0CLK:", self.read(self.map['DDR0CLKMON']))
        print("DDR1CLK:", self.read(self.map['DDR1CLKMON']))
        print("AURCLK:", self.read(self.map['AURCLKMON']))
        print("GRXCLK:", self.read(self.map['GRXCLKMON']))
        print("GTXCLK:", self.read(self.map['GTXCLKMON']))
        
    def identify(self):
        def str4(num):
            id = str(chr((num>>24)&0xFF))
            id += chr((num>>16)&0xFF)
            id += chr((num>>8)&0xFF)
            id += chr(num & 0xFF)
            return id

        fid = str4(self.read(self.map['FPGA_ID']))
        print("FPGA:", fid, end=' ')
        if fid == "TURF":
            fdv = self.DateVersion(self.read(self.map['FPGA_DATEVERSION']))
            print(fdv, end=' ')
            dna = self.dna()
            print(hex(dna))
        else:
            print('')
            
