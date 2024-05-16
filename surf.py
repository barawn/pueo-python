# SURF device and methods.
# Note that this is NOT the Overlay module that runs on Pynq!
# That module configures and programs the hardware and sets
# it up to be commanded by *this* module.
# That module is called surf6, this module is called PueoSURF
# to match PueoTURFIO/PueoTURF.
#
# Like the TURFIO, it has multiple access methods:
# direct serial, or TURFIO bridged (which itself can be
# TURF bridged).

from serialcobsdevice import SerialCOBSDevice

class PueoSURF:
    class AccessType(Enum):
        SERIAL = 'Serial'

    def __init__(self, accessInfo, type=AccessType.SERIAL):
        if type == self.AccessType.SERIAL:
            # need to think about a way to spec the address here?
            self.dev = SerialCOBSDevice(accessInfo,
                                        baudrate=1000000,
                                        addrbytes=3,
                                        devAddress=0)
            self.reset = self.dev.reset
            self.read = self.dev.read
            self.write = self.dev.write
            self.writeto = self.dev.writeto

            self.reset()
            
