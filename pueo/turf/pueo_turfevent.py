from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFEvent(dev_submod):
    """ Event control and statistics core """
    map = { 'CTRL' : 0x0,
            'NDWORDS0' : 0x10,
            'NDWORDS1' : 0x14,
            'NDWORDS2' : 0x18,
            'NDWORDS3' : 0x1C,
            'OUTQWORDS': 0x20,
            'OUTEVENTS': 0x24}

    def __init__(self, dev, base):
        super().__init__(dev, base)

################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
    event_reset      =    bitfield(0x000,  0,       0x0001, "Force event core into reset.")
    event_in_reset   = bitfield_ro(0x000,  1,       0x0001, "Event path is currently in reset.")
    mask             =    bitfield(0x000,  8,       0x000F, "TURFIO event mask - if set data from TURFIO is ignored")
    ndwords0         = register_ro(0x010,                   "Number of dwords received from TURFIO 0")
    ndwords1         = register_ro(0x014,                   "Number of dwords received from TURFIO 1")
    ndwords2         = register_ro(0x018,                   "Number of dwords received from TURFIO 2")
    ndwords3         = register_ro(0x01C,                   "Number of dwords received from TURFIO 3")
    outqwords        = register_ro(0x020,                   "Number of qwords sent to Ethernet")
    outevents        = register_ro(0x024,                   "Number of events sent to Ethernet")
    ack_count        =    bitfield(0x028,  0,       0x0FFF, "Number of available DDR storage slots")
    allow_count      =    bitfield(0x028, 16,       0x01FF, "Current number of remaining allowed events in flight")

    def statistics(self, verbose=True):
        """ Get event statistics """
        s = [4*self.ndwords0,
             4*self.ndwords1,
             4*self.ndwords2,
             4*self.ndwords3]
        if verbose:
            for i in range(4):
                print(f'TURFIO{i} : {s[i]} bytes received')
        r = 8*self.outqwords
        t = self.outevents
        if verbose:
            print(f'OUT : {r} bytes sent in {t} frames')
        s.append(r)
        s.append(t)
        return s

    def reset(self):
        """ Reset the event path """
        self.event_reset = 1
        self.event_reset = 0

