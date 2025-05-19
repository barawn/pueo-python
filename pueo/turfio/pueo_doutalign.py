from .pueo_hsalign import PueoHSAlign

class PueoDOUTAlign(PueoHSAlign):

    def __init__(self, dev, base):
        super().__init__(dev, base,
                         bit_width=8,
                         max_idelay_taps=63,
                         eye_tap_width=26,
                         train_map=PueoHSAlign.BW8_MAP)

    # NOTE NOTE NOTE
    # THIS $#!+ IS DUMB - MERGE INTO ONE PROPERTY
    # IF DOUT IS NOT ENABLED, IT SHOULD BE MASKED (DUH)
    
    @property
    def dout_mask(self):
        return (self.read(0)>>15) & 0x1

    @dout_mask.setter
    def dout_mask(self, value):
        rv = self.read(0) & 0xFFFF7FFF
        rv |= 0x8000 if value else 0
        self.write(0, rv)

    @property
    def dout_capture_phase(self):
        return (self.read(0) >> 7) & 0x1

    @dout_capture_phase.setter
    def dout_capture_phase(self, value):
        rv = self.read(0) & 0xFFFFFF7F
        rv |= 0x80 if value else 0
        self.write(0, rv)

    @property
    def enable(self):
        return (self.read(0) >> 8) & 0x1

    @enable.setter
    def enable(self, value):
        r = self.read(0) & 0xFFFFFEFF
        r |= 0x10 if value else 0
        self.write(0, r)

    def apply_alignment(self, eye, verbose=False):
        bs = eye[1]
        capturePhase = 0
        if bs & 4:
            bs = bs & 0x3
            capturePhase = 1
        self.dout_capture_phase = capturePhase
        return super().apply_alignment((eye[0], bs), verbose=verbose)
        
