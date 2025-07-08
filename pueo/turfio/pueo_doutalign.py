from .pueo_hsalign import PueoHSAlign
from ..common.dev_submod import bitfield, bitfield_ro, register, register_ro

class PueoDOUTAlign(PueoHSAlign):

    def __init__(self, dev, base):
        super().__init__(dev, base,
                         bit_width=8,
                         max_idelay_taps=63,
                         eye_tap_width=26,
                         train_map=PueoHSAlign.BW8_MAP)

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
    dout_capture_phase =  bitfield(0x000,  7,       0x0001, "Determines which of the 2 clock cycles DOUT is captured in")
    enable           =    bitfield(0x000,  8,       0x0001, "Output data is enabled")

    def apply_alignment(self, eye, verbose=False):
        bs = eye[1]
        capturePhase = 0
        if bs & 4:
            bs = bs & 0x3
            capturePhase = 1
        self.dout_capture_phase = capturePhase
        return super().apply_alignment((eye[0], bs), verbose=verbose)
        
