from .pueo_hsalign import PueoHSAlign

class PueoCOUTAlign(PueoHSAlign):

    def __init__(self, dev, base):
        super().__init__(dev, base,
                         bit_width=32,
                         max_idelay_taps=63,
                         eye_tap_width=26,
                         train_map=PueoHSAlign.BW32_MAP)

    @property
    def enable(self):
        return (self.read(0) >> 8) & 0x1

    @enable.setter
    def enable(self, value):
        r = self.read(0) & 0xFFFFFEFF
        r |= 0x100 if value else 0
        self.write(0, r)
