from .bf import bf

class USPEyeScan:
    """
    Eye Scan methods for an UltraScale+.
    >>> scanner = USPEyeScan(read_fn, write_fn, eyescanreset_fn, up_fn, name=None)
    >>> scanner.enable(True)
    # now you need to reset the GTP: this might be a global reset
    # so it's factored out.
    >>> gtp.reset()
    # now you need to call setup on the scanner. Note that THIS
    # AND THIS ALONE will disturb reception of bits!!
    >>> scanner.setup()
    # you can now call any OTHER functions you want

    read_fn : function of signature read(addr) -> int - DRP read
    write_fn : function of signature write(addr, val) -> none - DRP write
    eyescanreset_fn : function of signature reset(bool) -> none -
                      set/reset EYESCANRESET
    up_fn : function of signature up() -> bool - True if the MGT is
            receiving what is thought to be valid data.
    name : used for debugging prints
    """
    
    # DRP map
    drp = {
        'RXWIDTH' : 0x03,
        'RXRATE' : 0x63,
        'RX_INT_DATAWIDTH' : 0x66,
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

    # width code to width
    dwidthMap = {
        2 : 16,
        3 : 20,
        4 : 32,
        5 : 40,
        6 : 64,
        7 : 80,
        8 : 128,
        9 : 160 }

    # we need to compress the eyescan slightly when we store it:
    # the first 4 bytes indicate which of the remaining ones
    # have saturated errors (1) or saturated times (0).
    # then we have 25*2 bytes, so 54 total.
    # this obvs. only supports up to 32 results although I guess
    # I could extend it or some'n
    @staticmethod
    def compress_results(res):
        if len(res) > 32:
            raise ValueError("max number of results is 32")
        # first find the saturated errors
        saturatedErrors = 0
        for i in range(len(res)):
            if res[i][0] == 65535:
                saturatedErrors |= (1<<i)
        rb = saturatedErrors.to_bytes(4, 'big')
        for r in res:
            if r[0] == 65535:
                rb += r[1].to_bytes(2, 'big')
            else:
                rb += r[0].to_bytes(2, 'big')
        return rb
    

    
    def __init__(self,
                 read_fn,
                 write_fn,
                 eyescanreset_fn,
                 up_fn,
                 name="USPEyeScan"):
        self.name = name
        self.read = read_fn
        self.write = write_fn
        self.reset = eyescanreset_fn
        self.up = up_fn
        self._rxrate = None
        self._dwidth = None
        self._enabled = None

    @property
    def enable(self):
        if self._enabled is None:
            self._enabled = True if (self.read(0x3c) & 0x300) else False
        return self._enabled

    @enable.setter    
    def enable(self, value):
        """ Enable or disable the eye scanner. ** Needs GT reset after! ** """
        rv = bf(self.read(0x3C))
        rv[9:8] = 3 if value else 0
        rv[15:10] = 0
        self.write(0x3C, int(rv))
        self._enabled = True if value else False

    @property
    def rxrate(self):
        return self._rxrate or (2**(bf(self.read(0x63))[3:0]))

    @property
    def dwidth(self):
        return self._dwidth or (self.dwidthMap[bf(self.read(0x03))[8:5]])//(2**(bf(self.read(0x66))[1:0]))

    @property
    def prescale(self):
        return (self.read(0x3C) & 0x1F)

    @prescale.setter
    def prescale(self, value):
        self.write(0x3C, (self.read(0x3C) & 0xFFE0) | (value & 0x1F))

    @property
    def horzoffset(self):
        """ Horizontal offset of the eye sampler in UI. """
        return (((self.read(0x4F) & 0xFFF0) ^ 0x8000)-32768)/(1024*self.rxrate)

    @horzoffset.setter
    def horzoffset(self, value):
        # convert to units
        v = ((int(value * self.rxrate * 64) & 0xFFF) << 4)
        self.write(0x4F, (self.read(0x4F) & 0xF) | v)    

    @property
    def vertoffset(self):
        v = self.read(0x97)
        return ((v & 0x1FC) - (v & 0x200))//4

    @vertoffset.setter
    def vertoffset(self, value):
        v = abs(value)
        if v > 127:
            v = 127
        if value < 0:
            v |= 0x80
        v <<= 2
        self.write(0x97, (self.read(0x97) & 0xFC03) | v)
                
    @property
    def utsign(self):
        return 1 if (self.read(0x97) & 0x200) else 0

    @utsign.setter
    def utsign(self, value):
        v = self.read(0x97) & 0xFDFF
        if value:
            v |= 0x200
        self.write(0x97, v)

    def sampleScaleValue(self):
        """ Get the scale multiplier on the number of values """
        return (2**(self.prescale + 1))*self.dwidth

    def start(self):
        """ Move the eyescan state machine to RUN """
        self.write(0x3C, (self.read(0x3C) & 0x3FF) | 0x400)

    def complete(self):
        """ returns zero if not complete, nonzero if complete """
        return self.read(0x253) & 0x1

    def results(self):
        """ get results from complete eye scan and move to reset """
        ev = (self.read(0x251), self.read(0x252))
        self.write(0x3C, (self.read(0x3C) & 0x3FF))
        return ev
    
    def setup(self):
        """ Call after enabling and reset. ** May disturb read data!! ** """
        if not self.up():
            print(self.name, ": not up, so not enabling eye scan")
            return False
        self._rxrate = self.rxrate
        self._dwidth = self.dwidth
        v = [0xFFFF]*10
        # 16 bits
        v[4] = 0x0
        # add 4 more if 20
        if self._dwidth == 20:
            v[3] = 0x0FFF
        # or add 16 more if 32+
        if self._dwidth > 20:          
            v[3] = 0x0000
        # add 8 more if 40
        if self._dwidth == 40:
            v[2] = 0x00FF
        # or add 16 more if 64+
        if self._dwidth > 40:
            v[2] = 0x0
            v[1] = 0x0
        # or add all of 'em if 80
        if self._dwidth == 80:
            v[0] = 0x0
        # pair up the addrs and values
        vals = list(zip(self.drp['ES_SDATA_MASK'], v))
        # and iterate through
        for (addr, value) in vals:
            self.write(addr, value)
        # now we need the qual mask in order for the counter to incr
        for addr in self.drp['ES_QUAL_MASK']:
            self.write(addr, 0xFFFF)

        # ok - we NOW need to deal with the
        # #!*^*!#ing 'Realignment Sequence'
        # which is goddamn BURIED in an app note.
        # YES BURIED
        self.horzoffset = 0
        self.vertoffset = 0
        self.prescale = 5
        ntrials = 0
        while ntrials < 1000:
            self.start()
            while not self.complete():
                pass
            ev = self.results()
            if ev[0] == 0:
                break
            else:
                # This is from Xilinx AR #70872
                # There is no information on this in UG576. It's
                # just magic.
                v = self.read(0x4F) & 0xF
                self.write(0x4F, 0x8800 | v)
                self.reset(1)
                self.write(0x4F, 0x8000 | v)
                self.reset(0)
                ntrials = ntrials + 1
        if ntrials == 1000:
            print(self.name, ": Eye scan trial never had zero errors: failure!")
            return False
        self.prescale = 9
        return True
