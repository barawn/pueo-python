from ..common.genshift import GenShiftGPIO
from ..common.i2caccess import I2cAccess

class PueoTURFIOI2C:
    def __init__(self, dev):
        self.i2c = I2cAccess(scl=GenShiftGPIO(dev,6),
                             sda=GenShiftGPIO(dev,5))
        self.write = self.i2c.write
        self.read = self.i2c.read
        self.readFrom = self.i2c.readFrom
        self.i2c.stop()
        
