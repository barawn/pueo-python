import time

from .pueo_hsalign import PueoHSAlign
from ..common.dev_submod import bitfield, bitfield_ro, register, register_ro

class PueoCINAlign(PueoHSAlign):
    """
    High-speed alignment module for the TURF CIN on the TURFIO.
    """
    def __init__(self, dev, base):
        # Create our map.
        our_map = dict(zip(PueoHSAlign.BW32_MAP.keys(),
                           map(lambda x: x%4, PueoHSAlign.BW32_MAP.values())))        
        super().__init__(dev, base,
                         bit_width=32,
                         max_idelay_taps=63,
                         eye_tap_width=26,
                         train_map=our_map)

################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+#
########################### INHERITED FROM PueoHSAlign #########################################################
#   iserdes_reset    =    bitfield(0x000,  2,       0x0001, "ISERDES reset")
#   oserdes_reset    =    bitfield(0x000,  4,       0x0001, "OSERDES reset")
#   train_enable     =    bitfield(0x000, 10,       0x0001, "Enable training")
#   idelay_raw       =    register(0x004,                   "Raw value of the IDELAY setting.")
    rxclk_phase      =    bitfield(0x000, 16,       0x00FF, "Phase of the RXCLK clock")
    lock_req         =    bitfield(0x000,  8,       0x0001, "CIN lock request")
    lock_rst         =    bitfield(0x000,  3,       0x0001, "CIN lock reset")
    locked           = bitfield_ro(0x000,  9,       0x0001, "CIN locked status")
    
    # rxclk eyescan
    def eyescan_rxclk(self, period=1024):
        slptime = period*8E-9
        sc = []
        self.rxclk_phase = 0
        self.write(0x1C, period)
        for i in range(448):
            self.rxclk_phase = i
            time.sleep(slptime)
            sc.append(self.read(0x1C))
        return sc

    # RXCLK scan method
    @staticmethod
    def process_eyescan_rxclk(scan, width=448, wrap=True):
        scanShift = 0
        if wrap:
            if scan[0] == 0:
                scanShift = next((i for i, x in enumerate(scan[::-1]) if x), None)
                # roll the scan, then adjust back
                scan = scan[-1*scanShift:] + scan[:-1*scanShift]
                
        # We start off by assuming we're not in an eye.
        in_eye = False
        eye_start = 0
        eyes = []
        for i in range(width):
            if scan[i] == 0 and not in_eye:
                eye_start = i
                in_eye = True
            elif scan[i] > 0 and in_eye:                
                eye = [ int(eye_start+(i-eye_start)/2), i-eye_start ]
                # now adjust it
                if scanShift != 0:
                    eyePos = eye[0]
                    eyePos -= scanShift
                    if eyePos < 0:
                        eyePos += width
                    eye = [ eyePos , i-eye_start ]
                eyes.append(eye)
                in_eye = False
        # we exited the loop without finding the end of the eye
        if in_eye:
            eye = [ int(eye_start+(width-eye_start)/2), width-eye_start ]
            eyes.append( eye )

        return eyes

    # Alignment method for RXCLK.
    def align_rxclk(self, verbose=False):
        if verbose:
            print("Scanning RXCLK->SYSCLK transition.")
        rxsc = self.eyescan_rxclk()
        eyes = self.process_eyescan_rxclk(rxsc)
        bestEye = None
        for eye in eyes:
            if bestEye is not None:
                if verbose:
                    print(f'Second RXCLK->SYSCLK eye found at {eye[0]}, possible glitch')
                if eye[1] > bestEye[1]:
                    if verbose:
                        print(f'Eye at {eye[0]} has width {eye[1]}, better than {bestEye[1]}')
                    bestEye = eye
                else:
                    if verbose:
                        print(f'Eye at {eye[0]} has width {eye[1]}, worse than {bestEye[1]}, skipping')
            else:
                if verbose:
                    print(f'First eye at {eye[0]} width {eye[1]}')
                bestEye = eye
        if bestEye is None:
            raise IOError("No valid RXCLK->SYSCLK eye found!!")
        if verbose:
            print(f'Using eye at {eye[0]}')
        self.rxclk_phase = eye[0]
        return bestEye[0]
    

    def enable(self, onoff):
        self.lock_rst = 1
        self.lock_rst = 0
        if onoff:
            self.lock_req = 1
            if not self.locked:
                raise Exception("CIN did not lock on training pattern?")
        else:
            self.lock_rst = 1
            self.lock_rst = 0
