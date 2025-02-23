from ..common.bf import bf
from ..common.dev_submod import dev_submod

from enum import Enum

# Module structure (referenced from base)
# 0x0000 - 0x3FFF : Control/status space
# 0x4000 - 0x4FFF : DRP 0
# 0x5000 - 0x5FFF : DRP 1
# 0x6000 - 0x6FFF : DRP 2
# 0x7000 - 0x7FFF : DRP 3
#
# Because we have this 'mixed' structure
# we just have functions take which Aurora link
# to poke at.

class PueoTURFAurora(dev_submod):
    # these are primarily the values needed for eyescan
    # and emphasis/compensation adjustment
    drp = {
        'RXWIDTH' : 0x03,
        'RXRATE' : 0x63,
        'ES_CONTROL' : 0x3C,
        'ES_SDATA_MASK' : [ 0x49, 0x4A, 0x4B, 0x4C, 0x4D,
                            0xF1, 0xF2, 0xF3, 0xF4, 0xF5 ],
        'ES_QUAL_MASK' : [ 0x44, 0x45, 0x46, 0x47, 0x48,
                           0xEC, 0xED, 0xEE, 0xEF, 0xF0 ],
        'ES_VERT_OFFSET' : 0x97,
        'ES_HORZ_OFFSET' : 0x4F,
        'es_error_count' : 0x251,
        'es_sample_count' : 0x252,
        'es_control_status' : 0x253
        }
    dwidth = {
        2 : 16,
        3 : 20,
        4 : 32,
        5 : 40,
        6 : 64,
        7 : 80,
        8 : 128,
        9 : 160 }
    
    def __init__(self, dev, base):
        super().__init__(dev, base)
        # Eye scan stuff isn't setup by default.
        # I can change that forcibly in the post-place stuff.
        self.rxr = None
        self.rxw = None
        self.prescale = None

    def linkstat(self, linkno):
        return self.read(0x1000*linkno + 0x4)

    def reset(self):
        rv = bf(self.read(0))
        rv[0] = 1
        self.write(0, int(rv))
        rv[0] = 0
        self.write(0, int(rv))

    # hoff is "normal-ish", it just goes from -32*rxrate to +32*rxrate
    # voff seems "weird". let's see what other software does
    # they take a max_vert_offset and vert_step_size and then
    # adjust max to a multiple of vert_step_size that's less than 127
    # note this is STRICT less than 127 so if you set 127 and step size
    # 1 it'll step back to 126. this seems just bullshit dumb but it's Xilinx
    # it's probably just a bug though
    # if in LPM mode, it sets UT_SIGN to 0 always.
    # if in DFE mode, it samples BOTH UT_SIGN=1 and UT_SIGN=0.
    # the horiz offset phase unification stuff is just stupid, ignore it.
    def eyescan_set_offset(self, linkno, voff, hoff, utsign=0, vrange=0):
        # bounds check
        if abs(hoff) > 512:
            raise ValueError("hoff must be between -512 and +512")
        if abs(voff) > 127:
            raise ValueError("voff must be between -127 and +127")
        if utsign not in [0, 1]:
            raise ValueError("utsign must be 0 or 1")
        if vrange not in [0, 1, 2, 3]:
            raise ValueError("vrange must be 0, 1, 2, or 3")

        # construct the weirdo voff encoding
        v = bf(0)
        v[1:0] = vrange
        v[8:2] = abs(voff)
        v[9] = utsign
        v[10] = 1 if voff < 0 else 0
        # hoffset doesn't need any encoding:
        # because we restrict to -512 to +512 it's automatically
        # encoded correctly with the "phase unification" crap
        
        # construct the proper voff crap.
        self.drprmw(linkno,
                    self.drp['ES_VERT_OFFSET'],
                    int(v),
                    0x7FF)
        self.drprmw(linkno,
                    self.drp['ES_HORZ_OFFSET'],
                    (hoff << 4) & 0xFFF0,
                    0xFFF0)

    def eyescan_start(self, linkno):
        self.drprmw(linkno,
                    self.drp['ES_CONTROL'],
                    0x1 << 10,
                    0x3F << 10)

    def eyescan_complete(self, linkno):
        return ((self.drpread(linkno,
                              self.drp['es_control_status']) & 0xF) == 0x5)

    # automatically move eyescan engine to wait after this
    def eyescan_read_results(self, linkno):
        errvals = (self.drpread(linkno, self.drp['es_error_count']),
                   self.drpread(linkno, self.drp['es_sample_count']))
        self.drprmw(linkno,
                    self.drp['ES_CONTROL'],
                    0x0 << 10,
                    0x3F << 10)
        return errvals
    
    def eyescan_get_rxrate(self, linkno):
        return (2**(bf(self.drpread(linkno, self.drp['RXRATE']))[3:0]))

    def eyescan_get_dwidth(self, linkno):
        return self.dwidth[bf(self.drpread(linkno, self.drp['RXWIDTH']))[8:5]]

    # full silly eyescan procedure
    # I should put a timeout or something here!!!
    def run_eyescan(self, linkno, voff, hoff):
        if self.rxr is None:
            raise Exception("eye scanning has not been enabled")
        self.eyescan_set_offset(linkno, voff, hoff)
        self.eyescan_start(linkno)
        while not self.eyescan_complete(linkno):
            pass
        return self.eyescan_read_results(linkno)
    
    # This is the FULL eye-scan procedure.
    # This needs to get integrated into a state machine in the housekeeping
    # for eLinkStatus.
    # After mucking around, it looks like the right offsets are:
    # Let's try vert offsets of -96, -48, 0, 48, 96 (5)
    #       and horz offsets of -24, -12, 0, 12, 24 (5)
    # A first test gives us BERs of
    # 5.5E-2   1.3E-6    0     2.4E-7     7.0E-2
    # 6.6E-3   0         0     0          8.8E-3
    # 2.9E-5   0         0     0          3.2E-5
    # 8.7E-3   0         0     0          9.8E-3
    # 6.2E-2   1.8E-6    0     1.9E-6     6.1E-2
    #
    # yup that looks sweet
    def pretty_eyescan(self, linkno):
        def ber(v):
            return (v[0])/(v[1]*self.prescale)
        verts = [ -96, -48, 0, 48, 96 ]
        horzs = [ -24, -12, 0, 12, 24 ]
        for v in verts:
            for h in horzs:
                thisBer = ber(self.run_eyescan(linkno, v, h))
                # this makes the eye stand out more
                if thisBer:
                    print("%.1e\t" % thisBer, end='')
                else:
                    print(".......\t", end='')

            print("")
    
    # kinda think 16 should be okay, it's basically a millisecond I think
    # ((2^17)*40)/6.4E9 is like 0.8 ms
    # uh yeah no, i dunno what I'm doing wrong, but it's MACROSCOPICALLY big (like a minute)
    # OH DUH IT HAS TO RUN FOR 65536 IN THE CASE OF NO ERRORS!!
    # 1 ms would be virtually *no* prescale at all.
    # Let's try more like half a second per sample. We'll have to state machine
    # this thing anyway. That's a prescale of 1220, so we can use 1024 (2^10) or
    # a default prescale value of 9.
    def eyescan_setup(self, es_prescale=9):
        rxr = []
        rxw = []
        for linkno in [0,1,2,3]:
            rxr.append(self.eyescan_get_rxrate(linkno))
            rxw.append(self.eyescan_get_dwidth(linkno))
            self.drpwrite(linkno, self.drp['ES_CONTROL'], 0x300 | es_prescale)
        self.reset()
        # I really only know how to do this up to 80...
        for linkno in [0,1,2,3]:
            v = [0xFFFF]*10
            # 16 bits
            v[4] = 0x0
            # add 4 more if 20
            if rxr[linkno] == 20:
                v[3] = 0x0FFF
            # or add 16 more if 32+
            if rxr[linkno] > 20:
                v[3] = 0x0000
            # add 8 more if 40
            if rxr[linkno] == 40:
                v[2] = 0x00FF
            # or add 16 more if 64+
            if rxr[linkno] > 40:
                v[2] = 0x0
                v[1] = 0x0
            # or add all of 'em if 80
            if rxr[linkno] == 80:
                v[0] = 0x0
            for wordidx in range(10):
                self.drpwrite(linkno, self.drp['ES_SDATA_MASK'][wordidx], v[wordidx])
            for addr in self.drp['ES_QUAL_MASK']:
                self.drpwrite(linkno, addr, 0xFFFF)
        # EYESCAN IS READY FOR EVERYONE
        self.rxr = rxr
        self.rxw = rxw
        self.prescale = (2**(es_prescale+1))*rxw[0]
    
    # DRP read of drpaddr from Aurora idx aur
    def drpread(self, aur, drpaddr):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.read(addr)

    # DRP write of value to drpaddr at Aurora idx aur
    def drpwrite(self, aur, drpaddr, value):
        addr = aur*(0x1000) + 0x4000 + (drpaddr << 2)
        return self.write(addr, value)

    # DRP read-modify-write of value to drpaddr given mask at Aurora idx aur
    def drprmw(self, aur, drpaddr, value, mask):
        val = self.drpread(aur, drpaddr)
        val = (val & ~mask) | (value & mask)
        return self.drpwrite(aur, drpaddr, val)
