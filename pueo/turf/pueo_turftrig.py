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
