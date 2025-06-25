from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFScaler(dev_submod):
    """ Scaler core. """
    map = { 'SCAL_BASE' : 0x00,
            'GATE_CTRL' : 0x80,
            'GATE_EN'   : 0x84 }

    scaler_map = {
            0  : 'TFIO0 Slot 0',
            1  : 'TFIO0 Slot 1',
            2  : 'TFIO0 Slot 2',
            3  : 'TFIO0 Slot 3',
            4  : 'TFIO0 Slot 4',
            5  : 'TFIO0 Slot 5',
            6  : 'TFIO0 Slot 6',
            7  : 'SOFT',
            8  : 'TFIO1 Slot 0',
            9  : 'TFIO1 Slot 1',
            10 : 'TFIO1 Slot 2',
            11 : 'TFIO1 Slot 3',
            12 : 'TFIO1 Slot 4',
            13 : 'TFIO1 Slot 5',
            14 : 'TFIO1 Slot 6',
            15 : 'PPS',
            16 : 'TFIO2 Slot 0',
            17 : 'TFIO2 Slot 1',
            18 : 'TFIO2 Slot 2',
            19 : 'TFIO2 Slot 3',
            20 : 'TFIO2 Slot 4',
            21 : 'TFIO2 Slot 5',
            22 : 'N/A SURF',
            23 : 'EXT',
            24 : 'TFIO3 Slot 0',
            25 : 'TFIO3 Slot 1',
            26 : 'TFIO3 Slot 2',
            27 : 'TFIO3 Slot 3',
            28 : 'TFIO3 Slot 4',
            29 : 'TFIO3 Slot 5',
            30 : 'N/A SURF',
            31 : 'Reserved'
            }
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
        for i in range(32):
            d = self.read(4 * i)
            r.append(d)
        # create a map number to name inside f string --> say what it is
        if verbose:
            for i in range(16):
                print(f'{self.scaler_map[2*i]}: {r[2*i]}\t\t\t{self.scaler_map[2*i+1]}: {r[2*i+1]}')
        return r

    def scaler(self, idx):
        """ Returns a single scaler. """
        d = self.read(idx//2)
        shift = (idx % 2)*16
        return (d>>shift) & 0xFFFF

    
