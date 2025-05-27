from ..common.bf import bf
from ..common.dev_submod import dev_submod

class PueoTURFTrig(dev_submod):
    """ Trigger core. """
    map = { 'RUNCMD' : 0x0,
            'FWU' : 0x4 }

    RUNCMD_NOOP_LIVE = 0
    RUNCMD_SYNC = 1
    RUNCMD_RESET = 2
    RUNCMD_STOP = 3
    
    def __init__(self, dev, base):
        super().__init__(dev, base)

    def runcmd(self, val):
        self.write(0, val)

    def fwu_data(self, data):
        self.write(0x4, data)

    def fwu_mark(self, buffer):
        self.write(0x4, (buffer & 0x1) | (1<<31))

    @property
    def mask(self):
        """ SURF trigger bitmask (28 bits) """
        return self.read(0x100)

    @mask.setter
    def mask(self, value):
        self.write(0x100, value)

    @property
    def latency(self):
        """
        Time from when trigger physically occurs to when it is read out.
        This time needs to be large enough to absorb the trigger latency
        from the SURF.
        """
        return self.read(0x104) & 0xFFFF

    @latency.setter
    def latency(self, value):
        r = self.read(0x104) & 0xFFFF0000
        r |= value & 0xFFFF
        self.write(0x104, r)

    @property
    def offset(self):
        """
        Negative offset in clocks applied to all trigger times.
        This adjusts the location of the trigger in the readout window.
        Note this is applied to ALL triggers. Compensating for relative
        delays (with PPS/EXT for instance) has to happen IN ADDITION
        to this.
        """
        return (self.read(0x104) >> 16) & 0xFFFF

    @offset.setter
    def offset(self, value):
        r = self.read(0x104) & 0xFFFF
        r |= (value & 0xFFFF) << 16
        self.write(0x104, r)

    def soft_trig(self):
        """ value doesn't matter """
        self.write(0x110, 1)

    
