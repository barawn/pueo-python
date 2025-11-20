from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro
from .pueo_turfscaler import PueoTURFScaler

from enum import Enum

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
            'OCCUPANCY' : 0x114,
            'HOLDOFF_ERR' : 0x118,
            'EVENT_COUNT' : 0x11C }

    RUNCMD_NOOP_LIVE = 0
    RUNCMD_SYNC = 1
    RUNCMD_RESET = 2
    RUNCMD_STOP = 3

    class GpiSelect(int, Enum):
        """ select identifiers for ext_trig_select/gate_select. PPS is pointless for ext_trig_select """
        NONE = 0
        TIN0 = 1
        TIN1 = 2
        TURFIO0 = 3
        TURFIO1 = 4
        TURFIO2 = 5
        TURFIO3 = 6
        PPS = 7
    
    def __init__(self, dev, base):
        super().__init__(dev, base)

        self.scaler = PueoTURFScaler(self.dev, base+0x300)
        
################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
#   runcmd                function(0x000,                   "Send desired run command.")
#   fwu_data/fwu_mark     function(0x004,                   "Send FWU data or mark buffer.")
    cratepps_enable  =    bitfield(0x008,  0,       0x0001, "Enable sending the PPS to the crates")
    rundly           =    bitfield(0x008,  8,       0x000F, "Delay for internal run start/stop on top of base 33-clock delay")
    hpol_notch0      =    bitfield(0x010,  0,       0x0FFF, "HPOL notch 0 state")
    vpol_notch0      =    bitfield(0x010, 16,       0x0FFF, "VPOL notch 0 state")
    hpol_notch1      =    bitfield(0x014,  0,       0x0FFF, "HPOL notch 1 state")
    vpol_notch1      =    bitfield(0x014, 16,       0x0FFF, "VPOL notch 1 state")
    notch_time       = register_ro(0x018,                   "Time at which the notch update was applied")     
#   notch_update     =    function(0x01C,                   "Write anything to send desired notch state")    
    mask             =    register(0x100,                   "Trigger mask for individual SURFs")
    latency          =    bitfield(0x104,  0,       0xFFFF, "Time from desired trigger time to readout")
    offset           =    bitfield(0x104, 16,       0xFFFF, "Negative adjustment to input trigger time", signed=True)
    pps_trig_enable  =    bitfield(0x108,  0,       0x0001, "Enable for the PPS trigger")
    pps_offset       =    bitfield(0x108, 16,       0xFFFF, "Negative adjustment to PPS trigger time", signed=True)
    ext_trig_enable  =    bitfield(0x10C,  0,       0x0001, "Enable for the EXT trigger")
    ext_trig_edge    =    bitfield(0x10C,  1,       0x0001, "External trigger edge polarity (1=falling, 0=rising)")
    ext_trig_select  =    bitfield(0x10C,  8,       0x0007, "Select the source for the EXT trigger")
    ext_offset       =    bitfield(0x10C, 16,       0xFFFF, "Negative adjustment to EXT trigger time", signed=True)
#   soft_trig             function(0x110,                   "Write anything to this address for soft trigger")
    running          = bitfield_ro(0x110, 16,       0x0001, "Master trigger run status (1 = active, 0 = inactive)")
    occupancy        = register_ro(0x114,                   "Buffer occupancy from last second")
    holdoff          =    bitfield(0x118,  0,       0xFFFF, "Minimum time (in 4 ns cycles) between triggers")
    surf_err         =    bitfield(0x118, 16,       0x0001, "Set when SURF/TURFIO sends unknown event")
    turf_err         =    bitfield(0x118, 17,       0x0001, "Set when TURF issues trigger when dead")
    leveltwo_logic   =    bitfield(0x118, 24,       0x0001, "0 = AND of SURF sectors, 1 = OR of SURF sectors")   
    rf_trig_en       =    bitfield(0x118, 25,       0x0001, "1 = enable RF triggers, 0 = stop rf triggers")
    trigger_count    = register_ro(0x11C,                   "Number of triggers since run start")
    ext_prescale     =    register(0x120,                   "External trigger prescale (every N+1)")
    photo_prescale   =    bitfield(0x124,  0,       0x00FF, "Every N+1 triggers send a photoshutter to GPS")
    photo_en         =    bitfield(0x124, 16,       0x0001, "Enable the photoshutter output")

    def notch_update(self, 
                     notch0_hpol = None,
                     notch0_vpol = None,
                     notch1_hpol = None,
                     notch1_vpol = None):
        # this is all silliness for Python.
        # You could update the notch registers all at once
        # if you wanted. They can be freely read/written,
        # they just won't update until register 0x01C
        # is written to.
        if notch0_hpol:
            self.hpol_notch0 = notch0_hpol
        if notch0_vpol:
            self.vpol_notch0 = notch0_vpol
        if notch1_hpol:
            self.hpol_notch1 = notch1_hpol
        if notch1_vpol:
            self.vpol_notch1 = notch1_vpol
        # literally anything written to this register will do it
        self.write(0x1c, 1)
    
    def runcmd(self, val):
        self.write(0, val)

    def fwu_data(self, data):
        self.write(0x4, data)

    def fwu_mark(self, buffer):
        self.write(0x4, (buffer & 0x1) | (1<<31))
    
    def soft_trig(self):
        """ value doesn't matter """
        self.write(0x110, 1)

    
