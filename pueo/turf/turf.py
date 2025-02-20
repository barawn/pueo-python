from ..common.serialcobsdevice import SerialCOBSDevice
from ..common.bf import bf
from ..common.dev_submod import dev_submod

from .pueo_turfctl import PueoTURFCTL
from .pueo_turfaurora import PueoTURFAurora
from .pueo_cratebridge import PueoCrateBridge

from ..common.pyaxibridge import PyAXIBridge

import mmap
import struct
import os
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
            'BRIDGECTRL' : 0x1000,
            'BRIDGESTAT' : 0x1004}

    class AccessType(Enum):
        SERIAL = 'Serial'
        ETH = 'Ethernet'
        AXI = 'AXI'

    # search device tree nodes to grab base/size
    DT_PATH = "/sys/firmware/devicetree/base/axi/"
    BRIDGE_GLOB = "axilite_bridge@*"
    REG_PATH = "reg"
    
    @classmethod
    def axilite_bridge(cls):
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
        elif type == self.AccessType.MEM:
            self.dev = PyAXIBridge(accessInfo[0], accessInfo[1])
            self.reset = lambda : None
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto
                        
        self.ctl = PueoTURFCTL(self.dev, 0x10000)
        self.aurora = PueoTURFAurora(self.dev, 0x8000)
        self.crate = PueoCrateBridge(self.dev, (1<<27))

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
            print(fdv)
        else:
            print('')
            
