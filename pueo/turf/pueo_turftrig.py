from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFTrig(dev_submod):
    """ Trigger core. """
    map = { 'RUNCMD' : 0x0,
            'FWU'    : 0x4,
            'CTRL'   : 0x8,
            'TRIGMASK'   : 0x100,
            'LATENCY_OFFSET' : 0x104,
            'PPS_TRIGGER' : 0x108,
            'EXT_TRIGGER' : 0x10C,
            'SOFT_TRIGGER' : 0x110,
            'HOLDOFF' : 0x118,
            'EVENT_COUNT' : 0x11C }

    RUNCMD_NOOP_LIVE = 0
    RUNCMD_SYNC = 1
    RUNCMD_RESET = 2
    RUNCMD_STOP = 3
    
    def __init__(self, dev, base):
        super().__init__(dev, base)

################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
#   runcmd                function(0x000,                   "Send desired run command.")
#   fwu_data/fwu_mark     function(0x004,                   "Send FWU data or mark buffer.")
    cratepps_enable  =    bitfield(0x008,  0,       0x0001, "Enable sending the PPS to the crates")
    mask             =    register(0x100,                   "Trigger mask for individual SURFs")
    latency          =    bitfield(0x104,  0,       0xFFFF, "Time from desired trigger time to readout")
    offset           =    bitfield(0x104, 16,       0xFFFF, "Negative adjustment to input trigger time")    
    pps_trig_enable  =    bitfield(0x108,  0,       0x0001, "Enable for the PPS trigger")
    pps_offset       =    bitfield(0x108, 16,       0xFFFF, "Negative adjustment to PPS trigger time")
    ext_trig_enable  =    bitfield(0x10C,  0,       0x0001, "Enable for the EXT trigger")
    ext_trig_select  =    bitfield(0x10C,  8,       0x0007, "Select the source for the EXT trigger")
    ext_offset       =    bitfield(0x10C, 16,       0xFFFF, "Negative adjustment to EXT trigger time")
#   soft_trig             function(0x110,                   "Write anything to this address for soft trigger")
    holdoff          =    bitfield(0x118,  0,       0xFFFF, "Minimum time (in 4 ns cycles) between triggers")
    event_count      = register_ro(0x11C,                   "Number of events since run start")

    def runcmd(self, val):
        self.write(0, val)

    def fwu_data(self, data):
        self.write(0x4, data)

    def fwu_mark(self, buffer):
        self.write(0x4, (buffer & 0x1) | (1<<31))
    
    def soft_trig(self):
        """ value doesn't matter """
        self.write(0x110, 1)

    
