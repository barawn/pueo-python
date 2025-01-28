from .spiflash import SPIFlash

# wrapper for a SPIFlash object using
# the GenShift module
# the SPIFlash object expects
# a 'command' which takes 
#
# command( val, num_dummy_bytes, num_read_bytes, data_in_bytes )
# genshift gives us
# shift(self, val, auxVal=0, bitOrder=BitOrder.LSB_FIRST, numBits=8)
# so it's pretty much just multiple shift commands
#
# this is going to end up being pretty slow bc without the
# magic speedup provided by bursts since we're sending 4x the data
# note you need to do enable() first
class GenSPI:
    def __init__(self, genshift, ifnum, cspin, prescale=0, invertcs=True):
        self.dev = genshift
        self.shift = self.dev.shift

        # I *THINK* our "INVERT_GPIO" parameter in genshift
        # isn't actually implemented so do it here
        if invertcs:
            high = genshift.GpioState.GPIO_LOW
            low = genshift.GpioState.GPIO_HIGH
        else:
            high = genshift.GpioState.GPIO_HIGH
            low = genshift.GpioState.GPIO_LOW
        self.chipselect = lambda v : self.dev.gpio(cspin,
                                                   high if v else low)
        en = self.dev.enable
        dis = self.dev.disable
        
        self.enable = lambda v : en(ifnum, prescale) if (v) else dis()        

    def __enter__(self):
        self.enable(True)
        return SPIFlash(self)

    def __exit__(self, type, value, traceback):
        self.enable(False)
        return None

    # we seriously need to speed this up if we're
    # in serial mode.
    # we can speed it up by a factor of 2 or more
    # by adding a shiftin() command to genshift
    # which bypasses the read return
    # for faster than that we need to set up
    # burst writes.
    def command(self,
                val,
                num_dummy_bytes, num_read_bytes, data_in_bytes=bytes()):
        order = self.dev.BitOrder.MSB_FIRST
        self.chipselect(True)
        # first send command
        self.dev.shift(val, bitOrder=order)
        # next send data_in_bytes
        for b in data_in_bytes:
            self.dev.shift(b, bitOrder=order)
        # next send dummy bytes
        for d in range(num_dummy_bytes):
            self.dev.shift(0x00, bitOrder=order)
        # next send bytes to read
        rv = []
        for r in range(num_read_bytes):
            rv.append(self.dev.shift(0x00, bitOrder=order))
        self.chipselect(False)
        return rv
    
