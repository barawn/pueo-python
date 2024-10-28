import spi
from pathlib import Path

# to autofind: call with WBSPI(WBSPI.find_device(compat_str)) where
# compat_str is the compatibility string in the device tree
# this assumes a 32-bit space with 22-bit byte addressing (20 real bits)
class WBSPI(spi.SPI)
    def __init__(self, path='/dev/spidev2.0', speed=10000000):
        super().__init__(path)
        self.mode = self.MODE_0
        self.bits_per_word = 8
        self.speed = 10000000

    def read(self, address):
        txn = self._buildtxn(address)
        txn[2] |= 0x8
        return int.from_bytes(self.transfer(txn)[-4:], 'big')

    # mask is a 16-bit write disable
    def write(self, address, value, mask=0):
        txn = self._buildtxn(address, value, mask)
        self.transfer(txn)

    @staticmethod
    def _buildtxn(address, data=0, mask=0):
        address = (((address & 0x3FFFFF) >> 2) << 4 | ((mask & 0x3) << 1)
        return address.to_bytes(3, 'big') + data.to_bytes(4, 'big')
        
    @staticmethod
    def find_device(compatstr):
        for dev in Path('/sys/bus/spi/devices').glob('*'):
            fullCompatible = (dev / 'of_node' / 'compatible').read_text().rstrip('\x00')
            if fullCompatible == compatstr:
                if ( dev / 'driver' ).exists():
                    ( dev / 'driver' / 'unbind' ).write_text(dev.name)
                (dev / 'driver_override').write_text('spidev')
                Path('/sys/bus/spi/drivers/spidev/bind').write_text(dev.name)
                devname = "/dev/spidev"+dev.name[3:]
                return devname
        return None
