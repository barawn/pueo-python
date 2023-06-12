import struct
import sys
import time

#
# This is the Bitfield (bf) module
# surf.py, tisc.py and spi.py need to import this module

# Bitfield manipulation. Note that ordering
# can be Python (smallest first) or Verilog
# (largest first) for easy compatibility
#

class bf(object):
    def __init__(self, value=0):
        self._d = int(value)
    
    def __getitem__(self, index):
        if type(index) is slice:
            return self.__getslice__(index.start, index.stop)
        return (self._d >> index) & 1
    
    def __setitem__(self,index,value):
        if type(index) is slice:
            self.__setslice__(index.start, index.stop, value)
            return
        value = (value & 1)<<index
        mask = (1)<<index
        self._d = (self._d & ~mask) | value
    
    def __getslice__(self, start, end):
        if start > end:
            tmp = end
            end = start
            start = tmp
        mask = (((1)<<(end+1))-1) >> start
        return (self._d >> start) & mask
    
    def __setslice__(self, start, end, value):
        if start > end:
            tmp = end
            end = start
            start = tmp
        mask = (((1)<<(end+1))-1) >> start
        value = (value & mask) << start
        mask = mask << start
        self._d = (self._d & ~mask) | value
        return (self._d >> start) & mask
    
    def __int__(self):
        return self._d
