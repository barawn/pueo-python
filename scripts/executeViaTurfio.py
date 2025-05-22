from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO
from pueo.surf import PueoSURF
from HskSerial import HskEthernet, HskPacket

from hashlib import md5
import time

def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()

def file_as_blockiter(afile, blocksize=65536):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)
            
def filemd5(fn):
    return hash_bytestr_iter(file_as_blockiter(open(fn, 'rb')),
                             md5(),
                             ashexstr=True)

# TURFIOs and SURFs MUST BE CONFIGURED
# AND ALIGNED. This uses the commanding path.
# No alignment = no commanding path!

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("filename")
args = parser.parse_args()

print(f'Sending {args.filename} to be executed! : MD5 {filemd5(args.filename)}')

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
    surf = PueoSURF((tio, s[0]), 'TURFIO')
    surf.firmware_loading = 1
    hsk.send(HskPacket(s[1], 'eDownloadMode', data=[1]))
    pkt = hsk.receive()
    print("eDownloadMode response:", pkt.pretty())
    surfList.append(surf)
    surfAddrDict[surf] = s[1]

try:
    tio.surfturf.uploader.execute(surfList, args.filename)
except Exception as e:
    print("caught an exception during execute??")
    print(repr(e))
    
time.sleep(0.1)
for s in surfList:
    hsk.send(HskPacket(surfAddrDict[s], 'eJournal', data="-u pyfwupd -o cat -n 1"))
    pkt = hsk.receive()
    print("eJournal:", pkt.pretty(asString=True))
    
for s in surfList:
    hsk.send(HskPacket(surfAddrDict[s], 'eDownloadMode', data=[0]))
    pkt = hsk.receive()
    print("eDownloadMode response:", pkt.pretty())
    s.firmware_loading = 0

