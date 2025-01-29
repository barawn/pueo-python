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
        self.cspin = cspin

        if self.dev.dev.multiwrite:
            self.burst = True
        else:
            self.burst = False
        # I *THINK* our "INVERT_GPIO" parameter in genshift
        # isn't actually implemented so do it here
        if invertcs:
            self.high = genshift.GpioState.GPIO_LOW
            self.highint = 0
            self.low = genshift.GpioState.GPIO_HIGH
            self.lowint = 1
        else:
            self.high = genshift.GpioState.GPIO_HIGH
            self.highint = 1
            self.low = genshift.GpioState.GPIO_LOW
            self.lowint = 0

        en = self.dev.enable
        dis = self.dev.disable
        
        self.enable = lambda v : en(ifnum, prescale) if (v) else dis()        

    # gpio_prep is used with enter/exit because the assumption is nothing
    # else will use it between then and we can use Fast Stuff
    def chipselect(self, v):
        if self.gpio_prep:
            self.dev.set_gpio(self.gpio_prep, self.cspin,
                              self.highint if v else self.lowint)
        else:
            self.dev.gpio(self.cspin,
                          self.high if v else self.low)
        
    def __enter__(self):
        self.enable(True)
        self.gpio_prep = self.dev.prepare_set_gpio(self.cspin)
        # shift once pointlessly
        self.prep = self.dev.shiftin(0x00,
                                     0x00,
                                     bitOrder=self.dev.BitOrder.MSB_FIRST,
                                     numBits=8)                    
        return SPIFlash(self)

    def __exit__(self, type, value, traceback):
        self.enable(False)
        self.gpio_prep = None
        self.prep = None
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
        if self.burst:
            if num_read_bytes < 2:
                self.chipselect(True)
                txd = data_in_bytes
                txd += bytes(num_dummy_bytes + num_read_bytes)
                self.dev.blockshiftin(val, txd)
                self.chipselect(False)
                if (num_read_bytes > 0):
                    return [self.dev.blocklastout()]
                else:
                    return []
            else:
                self.chipselect(True)
                rv = []
                txd = data_in_bytes
                txd += bytes(num_dummy_bytes + 1)
                self.dev.blockshiftin(val, txd)
                rv.append(self.dev.blocklastout())
                num_read_bytes = num_read_bytes - 1
                while num_read_bytes > 0:
                    self.dev.blockshiftin(0, b'')
                    rv.append(self.dev.blocklastout())
                    num_read_bytes = num_read_bytes - 1
                self.chipselect(False)
                return rv
        else:
            order = self.dev.BitOrder.MSB_FIRST
            # le sigh
            self.chipselect(True)
            # first send command
            self.dev.shiftin(val, bitOrder=order)
            # next send data_in_bytes
            for b in data_in_bytes:
                self.dev.shiftin(b, bitOrder=order)
            # next send dummy bytes
            for d in range(num_dummy_bytes):
                self.dev.shiftin(0x00, bitOrder=order)
            # next send bytes to read
            rv = []
            for r in range(num_read_bytes):
                rv.append(self.dev.shift(0x00, bitOrder=order))
            self.chipselect(False)
            return rv           

        
