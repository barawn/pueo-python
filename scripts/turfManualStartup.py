# this script assumes you're talking to the TURF via Ethernet
# ONLY DO THIS SCRIPT IF THE TURF STARTUP STATE MACHINE IS NOT DOING IT
#
# These commands CANNOT be repeated!! They're once-and-done!

from pueo.turf import PueoTURF
from pueo.turfio import PueoTURFIO

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--turfio", type=str, default="0,1,2,3",
                    help="comma-separated list of TURFIOs to initialize")

args = parser.parse_args()
validTios = [0,1,2,3]
tioList = list(map(int,args.turfio.split(',')))
for tio in tioList:
    if tio not in validTios:
        print("TURFIOs can only be one of", validTios)
        sys.exit(1)

dev = PueoTURF(None, 'Ethernet')

enabled_turfios = []

for tionum in tioList:
    print(f'Trying to initialize TURFIO#{tionum}')
    if not (dev.aurora.linkstat(tionum) & 0x1):
        print(f'Lane not up, skipping.')
        continue
    tio = PueoTURFIO((dev, tionum), 'TURFGTP')
    tio.program_sysclk(tio.ClockSource.TURF)
    while not ((tio.read(0xC) & 0x1)):
        print(f'Waiting for clock on TURFIO#{tionum}...')
    print(f'Aligning RXCLK->SYSCLK transition on TURFIO#{tionum}...')
    tap = tio.calign[0].align_rxclk()
    print(f'TURFIO#{tionum} - tap is {tap}')
    print(f'Aligning CIN on TURFIO#{tionum}...')    
    dev.ctl.tio[tionum].train_enable(True)
    pv = tio.calign[0].align(doReset=True)
    if not pv:
        print(f'CIN alignment failed on TURFIO#{tionum}!!') 
        continue
    tio.calign[0].enable(True)
    tio.calign[0].train_enable(False)
    print(f'CIN is running on TURFIO#{tionum}')
    tio.sync_offset = 8
    tio.extsync = True
    enabled_turfios.append(tio)
    
dev.trig.runcmd(dev.trig.RUNCMD_SYNC)
for tio in enabled_turfios:
    tio.extsync = False

print(f'TURFIO sync complete')

