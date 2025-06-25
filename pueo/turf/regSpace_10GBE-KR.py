from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro
from .pueo_turfscaler import PueoTURFScaler

from enum import Enum

## PATRICK I HAVE NO IDEA WHAT I AM DOING <3

class Pueo10GBEKR(dev_submod):
    """ Trigger core. """
    map = { 'CONFIG_10GBE_KR' : 0x0004,
            'CTRL'   : 0x016D }


################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
#   runcmd                function(0x000,                   "Send desired run command.")
#   fwu_data/fwu_mark     function(0x004,                   "Send FWU data or mark buffer.")
    CONFIG_AN_ABILITY  =    register(0x00F8,                "CONFIGURATION_AN_ABILITY")
    CONFIG_AN_CONTROL_REG1 =register(0x00E0,                "CONFIGURATION_AN_CONTROL_REG1")
    CONFIG_LT_CONTROL_REG1 =register(0x0100,                "CONFIGURATION_LT_CONTROL_REG1")
    CONFIG_LT_TRAINED_REG = register(0x0104,                "CONFIGURATION_LT_TRAINED_REG")
    CONFIG_LT_SEED_REG0 =   register(0x0110,                "CONFIGURATION_LT_SEED_REG0")
    CONFIG_LT_COEFF_REG0 =  register(0x0130,                "CONFIGURATION_LT_COEFFICIENT_REG0")
    RESET_REG =             register(0x0004,                "RESET_REG")
    STAT_AN_STATUS =        register(0x0458,                "STAT_AN_STATUS")