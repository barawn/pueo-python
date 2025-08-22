from ..common.bf import bf
from ..common.dev_submod import dev_submod

from .pueo_turfif import PueoTURFIF

from enum import Enum
import time

class PueoTURFCTL(dev_submod):
    map = { 'CONTROL' : 0x0
           }
    
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.tio = []
        for i in range(4):
            self.tio.append(PueoTURFIF(dev, base + 0x4000 + 0x1000*i))

    def reset(self):
        print("Performing global TURFCTL reset")
        # The global reset procedure is pretty awkward.
        rv = bf(self.read(self.map['CONTROL']))
        # set MMCM0/1 reset to stop clocks
        rv[0] = 1
        rv[1] = 1
        print("Stopping clocks: ", end='')
        self.write(self.map['CONTROL'], int(rv))
        rv = bf(self.read(self.map['CONTROL']))
        if rv[8] or rv[9]:
            print(f'failed?? ({int(rv)}) - aborting')            
            return
        print("OK")
        print("Issuing reset: ", end='')
        # now issue resets since clock is stopped
        rv[2] = 1 # idelay67 reset
        rv[3] = 1 # idelay68 reset
        rv[4] = 1 # bank67 reset
        rv[5] = 1 # bank68 reset
        self.write(self.map['CONTROL'], int(rv))
        rv = bf(self.read(self.map['CONTROL']))
        if rv[10] or rv[11]:
            print(f'failed?? ({int(rv)}) - aborting')
            return
        print("OK")
        # now restart clocks and check for lock
        print("Restarting clocks: ", end='')
        rv[0] = 0
        rv[1] = 0
        self.write(self.map['CONTROL'], int(rv))
        # give some time to lock
        time.sleep(0.001)
        rv = bf(self.read(self.map['CONTROL']))
        if not rv[8] or not rv[9]:
            print(f'failed?? ({int(rv)}) - aborting')
            return
        print("OK")
        # now release IDELAY reset and then IDELAYCTRL
        print("Restarting IDELAY and IDELAYCTRL: ", end='')
        # IDELAY first...
        rv[4] = 0
        rv[5] = 0
        self.write(self.map['CONTROL'], int(rv))
        # give some time for reset to complete
        time.sleep(0.001)
        # then IDELAYCTRL
        rv[2] = 0
        rv[3] = 0
        self.write(self.map['CONTROL'], int(rv))
        # give time to go to ready
        time.sleep(0.001)
        rv = bf(self.read(self.map['CONTROL']))
        # NOTE: This can fail if you're an IDIOT and
        # forget to reset all the disable VTCs to 0.
        # So DON'T DO THAT
        if not rv[10] or not rv[11]:
            print(f'failed?? {int(rv)} - aborting')
            return
        print("OK")
        print("Restart complete")
        
