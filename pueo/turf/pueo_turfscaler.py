from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFScaler(dev_submod):
    """ Scaler core. """
    map = { 'SCAL_BASE' : 0x00,
            'GATE_CTRL' : 0x80,
            'GATE_EN'   : 0x84,
            'L2_BASE'   : 0xA0 }

    # Note that the leveltwo map starts at offset 0xA0+4*the index here
    leveltwo_map = {
        0 : 'H SURF Sect 0',
        1 : 'H SURF Sect 1',
        2 : 'H SURF Sect 2',
        3 : 'H SURF Sect 3',
        4 : 'H SURF Sect 4',
        5 : 'H SURF Sect 5',
        6 : 'H SURF Sect 6',
        7 : 'H SURF Sect 7',
        8 : 'H SURF Sect 8',
        9 : 'H SURF Sect 9',
        10 : 'H SURF Sect 10',
        11 : 'H SURF Sect 11',
        12 : 'V SURF Sect 0',
        13 : 'V SURF Sect 1',
        14 : 'V SURF Sect 2',
        15 : 'V SURF Sect 3',
        16 : 'V SURF Sect 4',
        17 : 'V SURF Sect 5',
        18 : 'V SURF Sect 6',
        19 : 'V SURF Sect 7',
        20 : 'V SURF Sect 8',
        21 : 'V SURF Sect 9',
        22 : 'V SURF Sect 10',
        23 : 'V SURF Sect 11'
    }
    
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
#                                  0x07C,                   "32 total 16-bit scalers.")
    gate_sel         =    bitfield(0x080,  0,       0x0007, "Gate source input select.")
    pps_gatelen      =    bitfield(0x080, 16,       0xFFFF, "Length in 8 ns clocks of PPS-based gate")
    gate_en          =    register(0x084,                   "Enable gate for selected scaler inputs")    
#   leveltwo         =      memory(0x0A0,
#                                     FC,                   "24 total 16-bit L2 scalers.")

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
        return self.read(idx)

    
    def leveltwos(self, verbose=False):
        """ Return all the L2 scalers. To access one see the leveltwo() method """
        r = []
        for i in range(24):
            d = self.read(0xA0 + 4 * i)
            r.append(d)
        # create a map number to name inside f string --> say what it is
        if verbose:
            for i in range(12):
                print(f'{self.leveltwo_map[2*i]}: {r[2*i]}\t\t\t{self.leveltwo_map[2*i+1]}: {r[2*i+1]}')
        return r

    def leveltwo(self, idx):
        """ Returns a single L2 scaler. """
        return self.read(0xA0 + 4*idx)

    

    
