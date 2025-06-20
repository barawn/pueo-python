from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, register, bitfield_ro, register_ro

class PueoTURFTime(dev_submod):
    """
    TURF time core. Register values here are offsets from the base value.
    
    CTRL register (0x00):
         Bit 0 : enable internal PPS.
         Bit 1 : use external PPS.
         Bits 31:16 : external PPS holdoff (also pulse length to PS)
    TRIM register (0x04):
         16-bit signed value to adjust internal PPS length by. Trim up
         reduces the internal PPS, trim down increases the internal PPS.
    SECOND register (0x08):
         Current second.
    LAST register (0x0C, read only):
         Value of the cycle timer at the last PPS. Cycle timer is reset
         at run start. Only captured when SECOND register is read.
    LLAST register (0x10, read only):
         Value of the cycle timer at the PPS before last PPS. Cycle timer
         is reset at run start. Only captured when SECOND register is read.

    PPS holdoff and TRIM adjustments should be done only when the
    respective PPS is not in use or is inactive.

    The LAST and LLAST registers are both captured when the SECOND
    register is read, so if you want them you read SECOND, then
    LAST, then LLAST, and they're guaranteed to all be from the
    same moment in time.
    """
    
    map = { 'CTRL' : 0x00,
            'TRIM' : 0x04,
            'SECOND'  : 0x08,
            'LAST' : 0x0C,
            'LLAST' : 0x10 }

#################################################################################################################
#  REGISTER SPACE                                                                                               #
#  +------------------+------------+------+-----+------------+-------------------------------------------------+
#  |                  |            |      |start|            |                                                 |
#  | name             |    type    | addr | bit |     mask   | description                                     |
#  +------------------+------------+------+-----+------------+-------------------------------------------------+    
    en_int_pps        =    bitfield(0x000,  0,       0x0001, "Enable the internal PPS counter")
    use_ext_pps       =    bitfield(0x000,  1,       0x0001, "Use the external PPS source")
    pps_holdoff       =    bitfield(0x000, 16,       0xFFFF, "Set holdoff/pulse length for ext. PPS in 32.768us units")
    internal_pps_trim =    bitfield(0x004,  0,       0xFFFF, "Adjust internal PPS counter (pos = longer, neg=shorter)", signed=True)
    current_second    =    register(0x008,                   "Current second")
    last_pps          = register_ro(0x00C,                   "Cycles @ last PPS. Read current_second to capture w/llast_pps")
    llast_pps         = register_ro(0x010,                   "Cycles @ PPS prior to last. Read current second to capture w/last_pps")
