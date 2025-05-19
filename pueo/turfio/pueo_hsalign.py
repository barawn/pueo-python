# Reworked generic high-speed align and biterr module.
# This is the base module. The TURFIO subclasses this out
# in to pueo_hsdout and pueo_hscout.
# Note that some of the functions here are actually 'common'
# between the two - for instance, the train enable (which
# controls the output, not the inputs) sets on both.
from ..common.dev_submod import dev_submod
import time

class PueoHSAlign(dev_submod):
    # maps are here for convenience
    
    # the top bit here is actually the dout
    # capture phase.
    BW8_MAP = { 0xD4 : 7,
                0xA9 : 6,
                0x53 : 5,
                0xA6 : 4,
                0x4D : 3,
                0x9A : 2,
                0x35 : 1,
                0x6A : 0 }

    BW32_MAP = { 0xa55a6996 : 0,
                 0x55a6996a : 4,
                 0x5a69965a : 8,
                 0xa6996a55 : 12,
                 0x6996a55a : 16,
                 0x996a55a6 : 20,
                 0x96a55a69 : 24,
                 0x6a55a699 : 28,

                 0x52AD34CB : 1,
                 0x2AD34CB5 : 5,
                 0xAD34CB52 : 9,
                 0xD34CB52A : 13,
                 0x34CB52AD : 17,
                 0x4CB52AD3 : 21,
                 0xCB52AD34 : 25,
                 0xB52AD34C : 29,
                 
                 0xA9569A65 : 2,
                 0x9569A65A : 6,
                 0x569A65A9 : 10,
                 0x69A65A95 : 14,
                 0x9A65A956 : 18,
                 0xA65A9569 : 22,
                 0x65A9569A : 26,
                 0x5A9569A6 : 30,
                 
                 0xD4AB4D32 : 3,
                 0x4AB4D32D : 7,
                 0xAB4D32D4 : 11,
                 0xB4D32D4A : 15,
                 0x4D32D4AB : 19,
                 0xD32D4AB4 : 23,
                 0x32D4AB4D : 27,
                 0x2D4AB4D3 : 31 }
                
    # the map is for convenient lookup but I don't
    # use them in the module functions for speed
    map = { 'CTLRESET' : 0x0,
            'IDELAY' : 0x4,
            'BITERR' : 0x8,
            'BITSLP' : 0xC }

    def __init__(self, dev, base,
                 bit_width = 32,
                 max_idelay_taps = 63,
                 eye_tap_width = 26,
                 train_map = None):
        if train_map is None:
            raise Exception("must provide a training map of values to slips")

        self.bit_width = bit_width
        self.max_taps = max_idelay_taps
        self.eye_tap_width = eye_tap_width
        self.train_map = train_map

        super().__init__(dev, base)

    # These are the scan processing functions.
    @classmethod
    def process_eyescan_edge(cls, scan, verbose=False):
        """
        Takes an eyescan - a tuple of (# errors, offset value)
        and returns tuples of the value borders.
        """
        edges = []
        start = None
        stop = None
        cur_bitno = None
        for i in range(len(scan)):
            val = scan[i]
            if val[0] == 0 and val[1] is not None:
                # data OK
                if cur_bitno is None:
                    cur_bitno = val[1]
                    start = i
                elif val[1] != cur_bitno:
                    stop = i
                    edge = (start, stop)
                    if verbose:
                        print("edge at", edge)
                    edges.append(edge)
                    start = None
                    stop = None
                    cur_bitno = None
                else:
                    start = i
        if len(edges) == 0:
            return None
        return edges

    @classmethod
    def process_eyescan_eyes(cls, scan, eye_width=26, verbose=False):
        edges = cls.process_eyescan_edge(scan, verbose=verbose)
        if edges is None:
            return edges
        max_width = len(scan)
        eyes = {}
        for edge in edges:
            edge_val = int((edge[0] + edge[1])/2)
            eye_center = edge_val - (eye_width//2)
            if eye_center > 0 and scan[eye_center] is not None:
                eyes[scan[eye_center][1]] = eye_center
        last_eye_center = edge_val + (eye_width//2)
        if last_eye_center < max_width and scan[last_eye_center] is not None:
            eyes[scan[last_eye_center][1]] = last_eye_center
        return eyes

    @property
    def idelay(self):
        r = self.read(4)
        if self.max_taps > 32:
            if r & 32:
                r = (r & 63) - 1
        return r

    @idelay.setter
    def idelay(self, value):
        if self.max_taps > 32:
            value = value + 1 if value & 32 else value
        self.write(0x4, value)

    @property
    def iserdes_reset(self):
        return (self.read(0) >> 2) & 0x1

    @iserdes_reset.setter
    def iserdes_reset(self, value):
        rv = self.read(0) & 0xFFFFFFFB
        rv |= 0x4 if value else 0
        self.write(0, rv)

    @property
    def train_enable(self):
        return (self.read(0) >> 10) & 0x1

    @train_enable.setter
    def train_enable(self, value):
        rv = self.read(0) & 0xfffffbff
        rv |= 0x400 if value else 0
        self.write(0, rv)

    def bitslip(self, n):
        """
        Performs 'n' bitslips.
        """
        for i in range(n):
            self.write(0xC, 1)
        
    def eyescan(self, slptime=0.01, get_bitno=True, cntclks=131072):
        self.write(0x8, cntclks)
        sc = []
        for i in range(self.max_taps):
            self.idelay = i
            time.sleep(slptime)
            biterr = self.read(0x8)
            if get_bitno:
                if biterr == 0:
                    test = self.read(0xC)
                    nb = self.train_map[test] if test in self.train_map else None
                    sc.append((biterr, nb))
                else:
                    sc.append((biterr, None))
            else:
                sc.append(biterr)
        return sc
        
    def find_alignment(self, do_reset=True, verbose=False):
        """
        Find the eyes in a link. Returns a dictionary
        of eye values to tap number.
        Raises exception if no eyes found.
        """
        if do_reset:
            self.iserdes_reset = 1
            self.iserdes_reset = 0

        delay = None
        slip = None
    
        sc = self.eyescan()
        eyes = self.process_eyescan_eyes(sc,
                                         eye_width=self.eye_tap_width,
                                         verbose=verbose)
        if eyes is None:
            raise IOError("Cannot find eyes: check training status")

        return eyes

    def apply_alignment(self, eye, verbose=False):
        """
        Applies an eye alignment to a link.
        Eye is a tuple of (delay, #bitslips)
        """
        self.idelay = eye[0]
        slipFix = eye[1]
        if verbose:
            print(f'Performing {slipFix} bit slips')
        self.bitslip(slipFix)
        test = self.read(0xC)
        nb = self.train_map[test] if test in self.train_map else None
        if test != 0:
            raise IOError(f'Alignment procedure failed: {hex(test)} maps to {nb} not 0')
        if verbose:
            print(f'Alignment succeeded.')
        return True
    
