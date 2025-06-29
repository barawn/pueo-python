from ..common.bf import bf
from ..common.dev_submod import dev_submod, bitfield, bitfield_ro, register, register_ro
from ..common.uspeyescan import USPEyeScan

from enum import Enum
from functools import partial
import time

# Module structure (referenced from base)
# 0x0000 - 0x3FFF : Control/status space
# 0x4000 - 0x4FFF : DRP 0
# 0x5000 - 0x5FFF : DRP 1
# 0x6000 - 0x6FFF : DRP 2
# 0x7000 - 0x7FFF : DRP 3
#
# The control/status space is further split as:
# 0x0000 - 0x07FF : Aurora 0
# 0x0800 - 0x0FFF : Aurora 1
# 0x1000 - 0x17FF : Aurora 2
# 0x1800 - 0x1FFF : Aurora 3
# 0x2000 - 0x3FFF : GT Common

class PueoTURFAurora(dev_submod):
    def __init__(self, dev, base):
        super().__init__(dev, base)
        self.scanner = []
        for i in range(4):
            # partials are more appropriate than lambdas and avoid
            # scoping issues in a loop.
            self.scanner.append( USPEyeScan(partial(self.drpread, i),
                                            partial(self.drpwrite, i),
                                            partial(self.eyescanreset, i),
                                            partial(self.up, i),
                                            name="TURFIO"+str(i)))


################################################################################################################
# REGISTER SPACE                                                                                               #
# +------------------+------------+------+-----+------------+-------------------------------------------------+
# |                  |            |      |start|            |                                                 |
# | name             |    type    | addr | bit |     mask   | description                                     |
# +------------------+------------+------+-----+------------+-------------------------------------------------+
    linkstat_0       = register_ro(0x0000,                   "Aurora link status for TURFIO port 0")
    linkstat_1       = register_ro(0x0800,                   "Aurora link status for TURFIO port 1")
    linkstat_2       = register_ro(0x1000,                   "Aurora link status for TURFIO port 2")
    linkstat_3       = register_ro(0x1800,                   "Aurora link status for TURFIO port 3")
    reset_all_links  =    bitfield(0x2000,   0,      0x0001, "Issue an Aurora reset to all links")
    reset_linkerr    =    bitfield(0x2000,  31,      0x0001, "Clear all sticky link errors")
    reset_user       =    bitfield(0x2000,   8,      0x0001, "Reset the user (register bridge) path")
            
    def enableEyeScan(self, waittime=1):
        enableWasNeeded = False
        """ Enable eye scanning on all links. EVEN NON-UP links """
        for s in self.scanner:
            if not s.enable:
                s.enable = True
                enableWasNeeded = True
        if enableWasNeeded:
            self.reset()
            time.sleep(waittime)
        # The issue now is that we need to know if we were setup or not.
        # We can figure that out by looking at the prescale.
        stat = []
        for s in self.scanner:
            if s.prescale != 9:
                stat.append(s.setup())
            else:
                stat.append(True)
        return stat
            
    def linkstat(self, linkno, verbose=False):
        rv = self.read(0x800*linkno + 0x4)
        if verbose:
            r = bf(rv)
            print(f'BUFG_GT in Reset: {r[11]}')
            print(f'Frame Err: {r[10]}')
            print(f'Soft Err: {r[9]}')
            print(f'System in Reset: {r[7]}')
            print(f'Link in Reset: {r[6]}')
            print(f'RX Reset Done: {r[5]}')
            print(f'TX Reset Done: {r[4]}')
            print(f'TX Locked: {r[3]}')
            print(f'GT Power Good: {r[2]}')
            print(f'Channel Up: {r[1]}')
            print(f'Lane Up: {r[0]}')
        return rv

    def linkerr_reset(self):
        """ Reset the sticky link errors on all Aurora links """
        self.reset_linkerr = 1
        self.reset_linkerr = 0
    
    def up(self, linkno):
        return self.linkstat(linkno) & 0x1
    
    def eyescanreset(self, linkno, onoff):
        rv = bf(self.read(0x800*linkno))
        rv[2] = 1 if onoff else 0
        self.write(0x800*linkno, int(rv))
    
    def reset(self):
        """ Toggle the reset on all Aurora links """
        self.reset_all_links = 1
        self.reset_all_links = 0

    def user_reset(self):
        """ Toggle the user reset to reset crate register bridge """
        self.reset_user = 1
        self.reset_user = 0
        
    def pretty_eyescan(self,
                       linkno,
                       prescale = 9,
                       verts = [ -96, -48, 0, 48, 96 ],
                       horzs = [ -0.375, -0.1875, 0, 0.1875, 0.375 ]):
        # exact numbers don't matter that much
        self.scanner[linkno].prescale = prescale
        sampleScale = self.scanner[linkno].sampleScaleValue()
        def ber(v):
            return (v[0])/((v[1]+0.5)*sampleScale)
        for v in verts:
            for h in horzs:
                self.scanner[linkno].horzoffset = h
                self.scanner[linkno].vertoffset = v
                self.scanner[linkno].start()
                while not self.scanner[linkno].complete():
                    pass
                thisBer = ber(self.scanner[linkno].results())
                # this makes the eye stand out more
                if thisBer:
                    print("%.1e\t" % thisBer, end='')
                else:
                    print(".......\t", end='')

            print("")
        

    # DRP read of drpaddr from Aurora idx aur
    def drpread(self, aur, drpaddr):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.read(addr)

    # DRP write of value to drpaddr at Aurora idx aur
    def drpwrite(self, aur, drpaddr, value):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.write(addr, value)
    
