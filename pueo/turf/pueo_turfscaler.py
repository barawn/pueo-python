from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFScaler(dev_submod):
    """ Scaler core. """
    map = { 'SCAL_BASE' : 0x00,
            'GATE_CTRL' : 0x80,
            'GATE_EN'   : 0x84 }

    def __init__(self, dev, base):
        super().__init__(dev, base)

################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
#   scalers          =      memory(0x000,
#                                  0x03C,                   "32 total 16-bit scalers.")
    gate_sel         =    bitfield(0x080,  0,       0x0007, "Gate source input select.")
    pps_gatelen      =    bitfield(0x080, 16,       0xFFFF, "Length in 8 ns clocks of PPS-based gate")
    gate_en          =    register(0x084,                   "Enable gate for selected scaler inputs")    

    def scalers(self, verbose=False):
        """ Return all the scalers. To access one see the scaler() method """
        r = []
        for i in range(16):
            d = self.read(i)
            r.append(d & 0xFFFF)
            r.append((d>>16) & 0xFFFF)
        if verbose:
            for i in range(16):
                print(f'SCAL{2*i}: {r[2*i]}\t\tSCAL{2*i+1}: {r[2*i+1]}')
        return r

    def scaler(self, idx):
        """ Returns a single scaler. """
        d = self.read(idx//2)
        shift = (idx % 2)*16
        return (d>>shift) & 0xFFFF

    
