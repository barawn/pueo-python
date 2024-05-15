from genshift import GenShiftGPIO
from universal-i2c-bitbang import I2CAccess

class PueoTURFIOI2C:
    def __init__(self, dev):
        self.i2c = I2CAccess(scl=GenShiftGPIO(dev,6),
                             sda=GenShiftGPIO(dev,5))
        self.write = self.i2c.write
        self.read = self.i2c.read
        self.i2c.stop()
        
