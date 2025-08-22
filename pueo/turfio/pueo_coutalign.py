from .pueo_hsalign import PueoHSAlign
from ..common.dev_submod import bitfield, bitfield_ro, register, register_ro

class PueoCOUTAlign(PueoHSAlign):

    def __init__(self, dev, base):
        super().__init__(dev, base,
                         bit_width=32,
                         max_idelay_taps=63,
                         eye_tap_width=26,
                         train_map=PueoHSAlign.BW32_MAP)

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
    enable           =    bitfield(0x000,  8,       0x0001, "Enable the COUT interface.")
    
