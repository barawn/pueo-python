from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, bitfield_ro, register, register_ro
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

################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
    rxclk_disable    =    bitfield(0x000, 24,       0x00FF, "Disable RXCLK to specified SURF")
    surf_live        = bitfield_ro(0x010,  0,       0x007F, "SURF has been marked live.")
    surf_misaligned  = bitfield_ro(0x010, 16,       0x007F, "SURF data is misaligned.")
    livedet_reset    =    bitfield(0x010, 31,       0x0001, "Reset the SURF live/trainin/trainout status")
    train_in_req     = bitfield_ro(0x014,  0,       0x007F, "SURF is requesting training.")
    autotrain        =    bitfield(0x014, 16,       0x007F, "Enable autotrain for specified SURF")
    train_out_rdy    = bitfield_ro(0x018,  0,       0x007F, "SURF outputs are ready to be trained on")
    train_complete   =    bitfield(0x01C,  0,       0x007F, "SURF training is complete")
    boot_seen        = bitfield_ro(0x01C, 16,       0x007F, "SURF boot has been seen")
    cout_offset      =    bitfield(0x020,  0,       0x000F, "Offset in cycles expected on COUT")
        
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
