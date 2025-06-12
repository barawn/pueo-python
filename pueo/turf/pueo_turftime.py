from ..common.bf import bf
from ..common.dev_submod import dev_submod

class PueoTURFTime(dev_submod):
    """
    TURF time core. Register values here are offsets from the base value.
    
    CTRL register (0x00):
         Bit 0 : enable internal PPS.
         Bit 1 : use external PPS.
         Bits 31:16 : external PPS holdoff (also pulse length to PS)
    TRIM register (0x04):
         16-bit signed value to adjust internal PPS length by.
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

    @property
    def en_int_pps(self):
        return self.read(0) & 0x1

    @en_int_pps.setter
    def en_int_pps(self, value):
        """ Start up the internal PPS. """
        r = self.read(0) & 0xFFFFFFFE
        r |= 0x1 if value else 0
        self.write(0, r)

    @property
    def use_ext_pps(self):
        """ Use external PPS. """
        return (self.read(0) >> 1) & 0x1

    @use_ext_pps.setter
    def use_ext_pps(self, value):
        r = self.read(0) & 0xFFFFFFFD
        r |= 0x2 if value else 0
        self.write(0, r)

    @property
    def pps_holdoff(self):
        """ Number of cycles to hold off a new PPS. Also pulse length to PS. """
        return (self.read(0) >> 16) & 0xFFFF

    @pps_holdoff.setter
    def pps_holdoff(self, value):
        r = self.read(0) & 0xFFFF
        r |= (value << 16)
        self.write(0, r)

    @property
    def internal_pps_trim(self):
        """ Adjusts the internal PPS by this (signed) value. """
        return (self.read(0x4) ^ 0x8000) - 0x8000

    @internal_pps_trim.setter
    def internal_pps_trim(self, value):
        self.write(0x4, value & 0xFFFF)        
        
    @property
    def current_second(self):
        """ Current second. """
        return self.read(0x8)

    @current_second.setter
    def current_second(self, value):
        self.write(0x8, value)

    @property
    def last_pps(self, value):
        """
        Value of the cycle counter (reset at run start) at the last PPS.
        Must read current_second first to capture this and llast_pps.
        """
        return self.read(0xC)

    @property
    def llast_pps(self, value):
        """
        Value of the cycle counter (reset at run start) at the PPS before
        the last PPS. Must read current second first to capture this
        and last_pps.
        """
        return self.read(0x10)
    
