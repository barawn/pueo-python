from ..common.serialcobsdevice import SerialCOBSDevice
from ..common.bf import bf
from ..common.dev_submod import dev_submod

from .pueo_turfctl import PueoTURFCTL
from .pueo_turfaurora import PueoTURFAurora
from .pueo_cratebridge import PueoCrateBridge

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
        MEM = 'Memory'

    DEVMEM_PATH = "/dev/mem"
    DT_PATH = "/sys/firmware/devicetree/base/axi/"
    BRIDGE_GLOB = "axilite_bridge@*"
    REG_PATH = "reg"
    
    @classmethod
    def axilite_bridge(cls):
        for br in Path(DT_PATH).glob(BRIDGE_GLOB):
            brp = br
        rp = brp / REG_PATH
        vals = rp.read_bytes()
        base , = struct.unpack(">Q", vals[0:8])
        size , = struct.unpack(">Q", vals[8:16])
        return (base, size, DEVMEM_PATH)
        
    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
            self.dev = SerialCOBSDevice(accessInfo, 115200, addrbytes=4)
            self.reset = self.dev.reset
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto
            self.dev.reset()
        elif type == self.AccessType.MEM:
            # oh I am so going to regret this
            # these are searchable:
            # for br in Path("/sys/firmware/devicetree/base/axi/").glob("axilite_bridge@*"):
            #     brp = br
            # rp = brp / "reg"
            # vals = rp.read_bytes()
            # base ,  = struct.unpack(">Q", vals[0:8])
            # size ,  = struct.unpack(">Q", vals[8:16])            
            base = accessInfo[0]
            size = accessInfo[1]
            fn = accessInfo[2]

            devt = ( None, None )
            devt[0] = os.open(fn, os.O_RDWR | os.O_SYNC )
            devt[1] = mmap.mmap(devt[0], size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset = base)
            # lololol
            self.dev = devt
            self.read = lambda x : struct.unpack("<I", self.dev[1][x:x+4])[0]
            self.write = lambda x, y : self.dev[1].__setitem__(slice(x, x+4, None), struct.pack("<I", y))
            self.reset = lambda : None
            self.writeto = self.write
            
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
            
