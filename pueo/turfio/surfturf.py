from ..common.bf import bf
from ..common.dev_submod import dev_submod
from ..common.uploader import Uploader
import os
import struct

# implements the SURFTURF class
class SURFTURF(dev_submod):
    BANKLEN = 49152
    map = { 'CTRL' : 0x0,
            'FWUPDATE' : 0x4,
            'RUNCMD' : 0x8,
            'TRIG' : 0xC,
            'LIVE' : 0x10,
            'TRAININ' : 0x14,
            'TRAINOUT' : 0x18,
            'TRAINCMPL' : 0x1C,
            'COUTCTRL' : 0x20 }
    
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.uploader = Uploader(self.fwupd,
                                 self.mark)

    @property
    def autotrain(self):
        return (self.read(0x14) >> 16) & 0x1FF

    @autotrain.setter
    def autotrain(self, value):
        r = self.read(0x14) & 0xFFFF
        r |= (value & 0x01FF) << 16
        self.write(0x14, r)

    @property
    def train_complete(self):
        return self.read(0x1C) & 0x1FF

    @train_complete.setter
    def train_complete(self, value):
        r = self.read(0x1C) & 0xFFFFFE00
        r |= (value & 0x1FF)
        self.write(0x1C, r)

    @property
    def train_out_rdy(self):
        return self.read(0x18) & 0x1FF

    @property
    def train_in_req(self):
        return self.read(0x14) & 0x1FF

    @property
    def surf_live(self):
        return self.read(0x10) & 0x1FF

    @property
    def surf_misaligned(self):
        return (self.read(0x10) >> 16) & 0x1FF
        
    @property
    def rxclk_disable(self):
        return (self.read(0x0) >> 24) & 0xFF

    @rxclk_disable.setter
    def rxclk_disable(self, value):
        r = self.read(0) & 0x00FFFFFF
        r |= (value << 24)
        self.write(0, r)        

    @property
    def cout_offset(self):
        return self.read(0x20) & 0xF

    @cout_offset.setter
    def cout_offset(self, value):
        r = self.read(0x20) & 0xFFFFFFF0
        r |= value & 0xF
        self.write(0x20, r)        
        
    def mark(self, bank):
        rv = bf(self.read(0x0))
        if bank == 0:
            rv[9:8] = 1
        else:
            rv[9:8] = 2
            
        self.write(0x0, int(rv))
        rv = bf(self.read(0x0))
        while rv[9:8]:
            rv = bf(self.read(0x0))
            
    # need to add runmode/trigger            
    def fwupd(self, val):
        self.write(0x4, val)
