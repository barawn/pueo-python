from ..common.bf import bf
from ..common.dev_submod import dev_submod

class PueoTURFEvent(dev_submod):
    """ Event control and statistics core """
    map = { 'CTRL' : 0x0,
            'NDWORDS0' : 0x10,
            'NDWORDS1' : 0x14,
            'NDWORDS2' : 0x18,
            'NDWORDS3' : 0x1C,
            'OUTQWORDS': 0x20,
            'OUTEVENTS': 0x24}

    def __init__(self, dev, base):
        super().__init__(dev, base)

    def statistics(self, verbose=True):
        b = self.map['NDWORDS0']
        s = []
        for i in range(4):
            r = self.read(b+0x4*i)
            if verbose:
                print(f'TURFIO{i} : {4*r} bytes received')
            s.append(4*r)
        r = self.read(self.map['OUTQWORDS'])
        t = self.read(self.map['OUTEVENTS'])
        if verbose:
            print(f'OUT : {8*r} bytes sent in {t} frames')
        s.append(r)
        s.append(t)
        return s

    def reset(self):
        rv = bf(self.read(0))
        rv[0] = 1
        self.write(0, int(rv))
        rv[0] = 0
        self.write(0, int(rv))

    @property
    def mask(self):
        rv = bf(self.read(0))
        return rv[12:8]

    @mask.setter
    def mask(self, value):
        value = value & 0xF
        rv = bf(self.read(0))
        rv[12:8] = value
        self.write(0, int(rv))
