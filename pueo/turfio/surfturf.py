from ..common.bf import bf
from ..common.dev_submod import dev_submod

import os
import struct

# implements the SURFTURF class
# right now just debugging + rxclk enabling
class SURFTURF(dev_submod):
    BANKLEN = 49152
    
    def __init__(self, dev, base):
        super().__init__(dev, base)

    def mark(self, bank):
        rv = bf(self.read(0x0))
        if bank == 0:
            rv[9:8] = 1
        else:
            rv[9:8] = 2
            
        self.write(0x0, int(rv))
        rv = bf(self.read(0x0))
        while rv[9:8]:
            rv = bf(self.read(0x0))

    @staticmethod
    def fwupdHeader(fn):
        hdr = bytearray(b'PYFW')
        flen = os.path.getsize(fn)
        hdr += struct.pack(">I", flen)
        hdr += fn.encode()
        hdr += b'\x00'
        hdr += (256 - (sum(hdr) % 256)).to_bytes(1, 'big')
        return (hdr, flen)

    # upload through the SURFTURF common.
    # probably not the smart way to do it.
    # this already assumes you've put the SURF in
    # eDownloadMode (which means addr(0xC)[7] = 1)
    # returns the bank that it ended up in.
    # "surf" here can be an individual SURF or all of 'em
    # if you want to be pedantic.
    def upload(self, surf, fn, bank=0, verbose=False):
        if not isinstance(surf, list):
            surf = [surf]
        # ALL OF THIS could be done ahead of time, like you
        # literally break the entire file up into bank chunks.
        # But whatever. We'll see. Through the TURFIO
        # this is obviously going to be slow.
        if not os.path.isfile(fn):
            raise ValueError("%s is not a regular file" % fn)
        hdr, flen = self.fwupdHeader(fn)
        toRead = self.BANKLEN - len(hdr)
        toRead = flen if flen < toRead else toRead
        print("Header is %d bytes, reading %d bytes from file" % (len(hdr), toRead))
        # these are here to make the loop work
        d = hdr
        written = 0
        with open(fn, "rb") as f:
            while written < flen:
                if verbose:
                    print("%s : writing %d bytes into bank %d, %d written" %
                          (fn, toRead, bank, written))
                d += f.read(toRead)
                padBytes = len(d) % 4
                d += padBytes*b'\x00'
                fmt = ">%dI" % (len(d) // 4)
                il = struct.unpack(fmt, d)
                # check to see if that bank is ready
                testIdx = bank + 6
                for s in surf:
                    rv = bf(s.read(0xC))
                    while not rv[testIdx]:
                        rv = bf(s.read(0xC))
                for val in il:
                    self.fwupd(val)
                self.mark(bank)
                bank = bank ^ 1
                written += toRead
                remain = flen - written
                toRead = remain if remain < self.BANKLEN else self.BANKLEN
        return bank
    
    # need to add runmode/trigger            
    def fwupd(self, val):
        self.write(0x4, val)

    def rxclk(self, enable):
        rv = bf(self.read(0x0))
        if enable:
            rv[31] = 0
        else:
            rv[31] = 1
        self.write(0x0, int(rv))
