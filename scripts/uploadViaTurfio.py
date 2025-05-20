from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO
from pueo.surf import PueoSURF
from HskSerial import HskEthernet, HskPacket

# TURFIOs and SURFs MUST BE CONFIGURED
# AND ALIGNED. This uses the commanding path.
# No alignment = no commanding path!

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("filename")
args = parser.parse_args()

# I SHOULD TAKE A JSON FILE TO CONFIGURE THIS
# I NEED:
# TURFIO SLOT #, HSK ADDRESS
# SURF SLOT #[s], HSK ADDRESS[es]
tios = (0, 0x40)

surfs = [ (0, 0x81),
          (5, 0xA3) ]

# get the housekeeping path
hsk = HskEthernet()
# make sure crate housekeeping is enabled
hsk.send(HskPacket(tios[1], 'eEnable', data=[0x40, 0x40]))
pkt = hsk.receive()

# get the TURFIO
dev = PueoTURF(None, 'Ethernet')
tio = PueoTURFIO((dev, tios[0]), 'TURFGTP')
# get the SURFs and put in download mode
surfList = []
surfAddrDict = {}
for s in surfs:
    s = PueoSURF((tio, s[0]), 'TURFIO')
    s.firmware_loading = 1
    hsk.send(HskPacket(s[1], 'eDownloadMode', data=[1]))
    surfList.append(s)
    surfAddrDict[s] = s[1]
try:
    tio.surfturf.uploader.upload(surfList, args.filename)
except:
    print("caught an exception during upload??")

for s in surfList:
    hsk.send(HskPacket(surfAddrDict[s], 'eDownloadMode', data=[0]))
    s.firmware_loading = 0

